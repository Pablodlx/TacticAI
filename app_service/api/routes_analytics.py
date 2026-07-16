import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app_service.api.deps import get_current_user, get_job_service
from app_service.providers.database.models import Match, User

router = APIRouter(prefix="/analytics", tags=["analytics"])

VALID_METRICS = {
    "possession": Match.possession_pct,
    "passes": Match.passes_total,
    "attacking_third": Match.attacking_third_pct,
}


@router.get("/overview")
def get_overview(
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    """Agregados del clubhouse: totales y medias del usuario."""
    with service.db_session_factory() as db:
        rows = db.query(Match).filter(Match.user_id == user.id).all()
        n = len(rows)
        if n == 0:
            return {
                "matches_analyzed": 0, "total_seconds_analyzed": 0,
                "avg_possession_pct": None, "avg_passes": None,
            }
        possessions = [m.possession_pct for m in rows if m.possession_pct is not None]
        passes = [m.passes_total for m in rows if m.passes_total is not None]
        return {
            "matches_analyzed": n,
            "total_seconds_analyzed": sum(m.duration_seconds or 0 for m in rows),
            "avg_possession_pct": (sum(possessions) / len(possessions)) if possessions else None,
            "avg_passes": (sum(passes) / len(passes)) if passes else None,
        }


@router.get("/trends")
def get_trends(
    metric: str = Query(default="possession"),
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    """Serie por partido (ordenada por fecha) de la métrica pedida."""
    if metric not in VALID_METRICS:
        raise HTTPException(
            status_code=400,
            detail=f"metric debe ser una de: {sorted(VALID_METRICS)}",
        )
    col = VALID_METRICS[metric]
    with service.db_session_factory() as db:
        rows = (
            db.query(Match)
            .filter(Match.user_id == user.id, col.isnot(None))
            .order_by(Match.created_at.asc())
            .all()
        )
        return {"metric": metric, "series": [
            {
                "match_id": m.id,
                "title": m.title,
                "date": (m.match_date or m.created_at).isoformat(),
                "value": getattr(m, col.key),
            }
            for m in rows
        ]}
