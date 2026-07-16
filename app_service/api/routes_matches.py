import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app_service.api.deps import get_current_user, get_job_service
from app_service.providers.database.models import Match, MatchAlert, MatchEvent, User
from app_service.services.heatmaps import HeatmapService

router = APIRouter(prefix="/matches", tags=["matches"])


def _get_owned_match(db, match_id: str, user: User) -> Match:
    match = db.get(Match, match_id)
    if not match or match.user_id != user.id:
        raise HTTPException(status_code=404, detail="match not found")
    return match


def _match_summary(m: Match) -> dict:
    return {
        "id": m.id,
        "title": m.title,
        "opponent": m.opponent,
        "match_date": m.match_date.isoformat() if m.match_date else None,
        "duration_seconds": m.duration_seconds,
        "status": m.status,
        "possession_pct": m.possession_pct,
        "passes_total": m.passes_total,
        "attacking_third_pct": m.attacking_third_pct,
        "created_at": m.created_at.isoformat(),
    }


@router.get("")
def list_matches(
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    with service.db_session_factory() as db:
        rows = (
            db.query(Match)
            .filter(Match.user_id == user.id)
            .order_by(Match.created_at.desc())
            .all()
        )
        return {"matches": [_match_summary(m) for m in rows]}


@router.get("/{match_id}")
def get_match(
    match_id: str,
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    with service.db_session_factory() as db:
        m = _get_owned_match(db, match_id, user)
        detail = _match_summary(m)
        detail["stats"] = json.loads(m.stats_json) if m.stats_json else None
        detail["ai_summary"] = m.ai_summary
        return detail


@router.patch("/{match_id}")
def update_match(
    match_id: str,
    payload: dict,
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    with service.db_session_factory() as db:
        m = _get_owned_match(db, match_id, user)
        if "title" in payload and payload["title"]:
            m.title = str(payload["title"])[:255]
        if "opponent" in payload:
            m.opponent = (str(payload["opponent"])[:255] if payload["opponent"] else None)
        db.commit()
        return _match_summary(m)


@router.delete("/{match_id}", status_code=204)
def delete_match(
    match_id: str,
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    with service.db_session_factory() as db:
        m = _get_owned_match(db, match_id, user)
        db.query(MatchEvent).filter(MatchEvent.match_id == m.id).delete()
        db.query(MatchAlert).filter(MatchAlert.match_id == m.id).delete()
        db.delete(m)
        db.commit()


@router.get("/{match_id}/events")
def get_match_events(
    match_id: str,
    type: str | None = Query(default=None),
    from_s: float | None = Query(default=None),
    to_s: float | None = Query(default=None),
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    with service.db_session_factory() as db:
        _get_owned_match(db, match_id, user)
        q = db.query(MatchEvent).filter(MatchEvent.match_id == match_id)
        if type:
            q = q.filter(MatchEvent.type == type)
        if from_s is not None:
            q = q.filter(MatchEvent.ts_seconds >= from_s)
        if to_s is not None:
            q = q.filter(MatchEvent.ts_seconds <= to_s)
        rows = q.order_by(MatchEvent.ts_seconds).all()
        return {"events": [
            {
                "type": e.type,
                "frame": e.frame,
                "ts_seconds": e.ts_seconds,
                "team": e.team,
                "from_player": e.from_player,
                "to_player": e.to_player,
            }
            for e in rows
        ]}


@router.get("/{match_id}/pass-network")
def get_pass_network(
    match_id: str,
    team: int | None = Query(default=None, ge=0, le=1),
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    """Red de pases: nodos (jugadores) y aristas (from→to con conteo)."""
    with service.db_session_factory() as db:
        _get_owned_match(db, match_id, user)
        q = db.query(MatchEvent).filter(
            MatchEvent.match_id == match_id, MatchEvent.type == "pass"
        )
        if team is not None:
            q = q.filter(MatchEvent.team == team)
        edges: dict = {}
        nodes: dict = {}
        for e in q.all():
            if e.from_player is None or e.to_player is None:
                continue
            key = (e.team, e.from_player, e.to_player)
            edges[key] = edges.get(key, 0) + 1
            for pid in (e.from_player, e.to_player):
                nodes.setdefault((e.team, pid), 0)
                nodes[(e.team, pid)] += 1
        return {
            "nodes": [
                {"team": t, "player_id": pid, "passes_involved": c}
                for (t, pid), c in nodes.items()
            ],
            "edges": [
                {"team": t, "from_player": f, "to_player": to, "count": c}
                for (t, f, to), c in edges.items()
            ],
        }


@router.get("/{match_id}/momentum")
def get_momentum(
    match_id: str,
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    """Serie temporal de dominio por batch: +1 posesión equipo 0, -1 equipo 1."""
    with service.db_session_factory() as db:
        m = _get_owned_match(db, match_id, user)
        stats = json.loads(m.stats_json) if m.stats_json else {}
    timeline = stats.get("timeline", [])
    series = []
    for item in timeline:
        team = item.get("possession_team")
        value = 1.0 if team == 0 else (-1.0 if team == 1 else 0.0)
        series.append({
            "batch_idx": item.get("batch_idx"),
            "start_frame": item.get("start_frame"),
            "value": value,
        })
    # Suavizado con media móvil (ventana 3)
    smoothed = []
    for i in range(len(series)):
        window = [s["value"] for s in series[max(0, i - 2):i + 1]]
        smoothed.append({**series[i], "momentum": sum(window) / len(window)})
    return {"momentum": smoothed}


@router.get("/{match_id}/physical")
def get_physical(
    match_id: str,
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    with service.db_session_factory() as db:
        m = _get_owned_match(db, match_id, user)
        stats = json.loads(m.stats_json) if m.stats_json else {}
    physical = stats.get("physical")
    if not physical:
        raise HTTPException(status_code=404, detail="physical metrics not available")
    return physical


@router.post("/{match_id}/ai-summary")
def generate_ai_summary(
    match_id: str,
    force: bool = Query(default=False),
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    """Genera (y cachea) el resumen táctico del entrenador vía IA."""
    from app_service.services.ai_summary import AISummaryService, AISummaryError
    with service.db_session_factory() as db:
        m = _get_owned_match(db, match_id, user)
        if m.ai_summary and not force:
            return {"ai_summary": m.ai_summary, "cached": True}
        stats = json.loads(m.stats_json) if m.stats_json else {}
        alerts = [
            {"type": a.alert_type, "severity": a.severity, "message": a.message,
             "ts_seconds": a.ts_seconds}
            for a in db.query(MatchAlert).filter(MatchAlert.match_id == match_id).all()
        ]
    try:
        summary_text = AISummaryService().generate(m.title, stats, alerts)
    except AISummaryError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    with service.db_session_factory() as db:
        row = db.get(Match, match_id)
        row.ai_summary = summary_text
        db.commit()
    return {"ai_summary": summary_text, "cached": False}


@router.get("/{match_id}/heatmap")
def get_match_heatmap(
    match_id: str,
    team: int = Query(ge=0, le=1),
    from_min: float | None = Query(default=None, ge=0),
    to_min: float | None = Query(default=None, gt=0),
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    with service.db_session_factory() as db:
        m = _get_owned_match(db, match_id, user)
        prefix = m.artifacts_prefix
    if not prefix:
        raise HTTPException(status_code=404, detail="heatmaps not available")
    result = HeatmapService(service.storage).get_heatmap(prefix, team, from_min, to_min)
    if result is None:
        raise HTTPException(status_code=404, detail="heatmaps not available")
    return result


@router.get("/{match_id}/heatmap-windows")
def get_match_heatmap_windows(
    match_id: str,
    team: int = Query(ge=0, le=1),
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    """Todas las ventanas crudas: el frontend las combina en memoria para que
    el slider de franjas responda sin más peticiones."""
    with service.db_session_factory() as db:
        m = _get_owned_match(db, match_id, user)
        prefix = m.artifacts_prefix
    if not prefix:
        raise HTTPException(status_code=404, detail="heatmaps not available")
    result = HeatmapService(service.storage).get_all_windows(prefix, team)
    if result is None:
        raise HTTPException(status_code=404, detail="heatmap windows not available")
    return result


@router.get("/{match_id}/alerts")
def get_match_alerts(
    match_id: str,
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    with service.db_session_factory() as db:
        _get_owned_match(db, match_id, user)
        rows = (
            db.query(MatchAlert)
            .filter(MatchAlert.match_id == match_id)
            .order_by(MatchAlert.ts_seconds)
            .all()
        )
        return {"alerts": [
            {
                "ts_seconds": a.ts_seconds,
                "frame": a.frame,
                "type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
            }
            for a in rows
        ]}
