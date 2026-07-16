"""Ingesta y consulta de partidos analizados.

`MatchIngestService.ingest()` se llama desde `JobService.process_payload` al
completar un análisis (cubre tanto el modo sync como el worker): lee los
artefactos del output_dir (stats/events/npz), sube los persistentes a storage
bajo `matches/{id}/` y puebla las tablas matches / match_events / match_alerts.
"""

import glob
import json
import os
from datetime import datetime

from app_service.providers.database.models import Match, MatchAlert, MatchEvent
from app_service.providers.storage.base import StorageProvider


def _load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


class MatchIngestService:
    def __init__(self, db_session_factory, storage: StorageProvider):
        self.db_session_factory = db_session_factory
        self.storage = storage

    def ingest(
        self,
        job_id: str,
        user_id: str | None,
        output_dir: str,
        result: dict,
        video_uri: str | None = None,
        title: str | None = None,
    ) -> str | None:
        """Crea el Match a partir de los artefactos del job. Devuelve match_id."""
        if not user_id:
            return None  # jobs legacy sin dueño: no se crea match

        summary = (result or {}).get("summary", {}) or {}

        # ── Estadísticas denormalizadas ──
        possession = summary.get("possession", {})
        pct = possession.get("percent_by_team", {}) or {}
        # las claves pueden ser int o str según serialización
        possession_pct = float(pct.get(0, pct.get("0", 0.0)) or 0.0)
        passes = summary.get("passes", {}) or {}
        passes_total = int(passes.get("total", 0) or 0)
        progress = summary.get("progress", {}) or {}
        duration_seconds = float(progress.get("total_seconds", 0.0) or 0.0)

        # Zonas: % en tercio ofensivo (off_*) del equipo 0 si está disponible
        attacking_third_pct = None
        zones = self._read_zone_percentages(output_dir)
        if zones is not None:
            attacking_third_pct = zones

        # ── Timeline de posesión por batch (para momentum) ──
        timeline = self._build_possession_timeline(output_dir)

        # ── Métricas físicas desde posiciones proyectadas ──
        physical = self._compute_physical(output_dir)

        stats_json = json.dumps({
            "summary": summary,
            "timeline": timeline,
            "physical": physical,
        })

        # ── Subir artefactos persistentes ──
        artifacts_prefix = f"matches/{job_id}/"
        npz_paths = glob.glob(os.path.join(output_dir, "**", "*_heatmaps.npz"), recursive=True)
        for p in npz_paths:
            self.storage.upload_file(p, artifacts_prefix + "heatmaps.npz")

        # ── Persistir en DB ──
        with self.db_session_factory() as db:
            existing = db.get(Match, job_id)
            if existing:
                return existing.id
            match = Match(
                id=job_id,
                user_id=user_id,
                job_id=job_id,
                title=title or f"Partido {datetime.utcnow():%d/%m/%Y}",
                duration_seconds=duration_seconds,
                status="completed",
                video_uri=video_uri,
                artifacts_prefix=artifacts_prefix,
                stats_json=stats_json,
                possession_pct=possession_pct,
                passes_total=passes_total,
                attacking_third_pct=attacking_third_pct,
            )
            db.add(match)

            for ev in self._iter_events(output_dir):
                db.add(MatchEvent(
                    match_id=job_id,
                    type=str(ev.get("type", "unknown")),
                    frame=ev.get("frame"),
                    ts_seconds=ev.get("timestamp"),
                    team=ev.get("team"),
                    from_player=ev.get("from_player"),
                    to_player=ev.get("to_player"),
                    payload_json=json.dumps(ev),
                ))

            for alert in summary.get("alerts", []) or []:
                if not isinstance(alert, dict):
                    continue
                db.add(MatchAlert(
                    match_id=job_id,
                    frame=alert.get("frame"),
                    ts_seconds=alert.get("timestamp") or alert.get("ts_seconds"),
                    alert_type=str(alert.get("type", alert.get("alert_type", "unknown"))),
                    severity=str(alert.get("severity", "info")),
                    message=alert.get("message") or alert.get("description"),
                    payload_json=json.dumps(alert),
                ))

            db.commit()
        return job_id

    def _iter_events(self, output_dir: str):
        # Los batch se guardan en output_dir/{match_id}/ (save_chunk_output)
        for path in sorted(glob.glob(os.path.join(output_dir, "**", "events_batch_*.json"),
                                     recursive=True)):
            data = _load_json(path)
            if isinstance(data, list):
                for ev in data:
                    if isinstance(ev, dict):
                        yield ev

    def _build_possession_timeline(self, output_dir: str) -> list:
        """Serie por batch con posesión acumulada — base del momentum chart."""
        timeline = []
        for path in sorted(glob.glob(os.path.join(output_dir, "**", "stats_batch_*.json"),
                                     recursive=True)):
            data = _load_json(path)
            if not isinstance(data, dict):
                continue
            chunk = data.get("chunk_stats", {}) or {}
            timeline.append({
                "batch_idx": data.get("batch_idx"),
                "start_frame": data.get("start_frame"),
                "end_frame": data.get("end_frame"),
                "possession_team": chunk.get("possession_team"),
                "events_count": chunk.get("events_count", 0),
            })
        return timeline

    def _compute_physical(self, output_dir: str) -> dict:
        """Distancia recorrida y sprints por jugador desde positions_batch_*.json.

        Usa las posiciones de campo proyectadas (metros). Filtra saltos
        imposibles (>12 m/s: fallo de proyección o cambio de identidad).
        Sprint: velocidad > 5.5 m/s sostenida >= 1 s.
        """
        SPEED_MAX = 12.0
        SPRINT_SPEED = 5.5
        SPRINT_MIN_S = 1.0

        tracks: dict = {}  # player_id -> {'team': int, 'points': [(ts, x, y)]}
        for path in sorted(glob.glob(os.path.join(output_dir, "**", "positions_batch_*.json"),
                                     recursive=True)):
            data = _load_json(path)
            if not isinstance(data, list):
                continue
            for p in data:
                fp = p.get("field_position")
                if not fp or len(fp) < 2:
                    continue
                pid = p.get("player_id")
                t = tracks.setdefault(pid, {"team": p.get("team_id", -1), "points": []})
                t["points"].append((float(p.get("timestamp", 0.0)), float(fp[0]), float(fp[1])))

        players = []
        team_distance = {0: 0.0, 1: 0.0}
        for pid, t in tracks.items():
            pts = sorted(t["points"])
            if len(pts) < 2:
                continue
            distance = 0.0
            sprints = 0
            sprint_start = None
            for (t0, x0, y0), (t1, x1, y1) in zip(pts, pts[1:]):
                dt = t1 - t0
                if dt <= 0 or dt > 5.0:
                    sprint_start = None
                    continue
                d = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                speed = d / dt
                if speed > SPEED_MAX:
                    sprint_start = None
                    continue
                distance += d
                if speed > SPRINT_SPEED:
                    if sprint_start is None:
                        sprint_start = t0
                    elif t1 - sprint_start >= SPRINT_MIN_S:
                        sprints += 1
                        sprint_start = None
                else:
                    sprint_start = None
            players.append({
                "player_id": pid,
                "team": t["team"],
                "distance_m": round(distance, 1),
                "sprints": sprints,
            })
            if t["team"] in (0, 1):
                team_distance[t["team"]] += distance

        players.sort(key=lambda p: -p["distance_m"])
        return {
            "players": players,
            "team_distance_m": {k: round(v, 1) for k, v in team_distance.items()},
        }

    def _read_zone_percentages(self, output_dir: str) -> float | None:
        """% de presencia en tercio ofensivo del equipo 0, desde el npz."""
        try:
            import numpy as np
            npz_paths = glob.glob(os.path.join(output_dir, "*_heatmaps.npz"))
            if not npz_paths:
                return None
            with np.load(npz_paths[0], allow_pickle=True) as data:
                if "zone_percentages_team_0" not in data.files:
                    return None
                zp = data["zone_percentages_team_0"]
                if len(zp) != 9:
                    return None
                # zonas 'thirds_lanes': índices 6,7,8 = tercio ofensivo
                return float(zp[6] + zp[7] + zp[8])
        except Exception:
            return None
