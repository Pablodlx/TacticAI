"""
Construye schemas.predictions.MatchState desde el pipeline existente (bajo acoplamiento).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from schemas.predictions import (
    AttackDirectionState,
    BallPosition,
    MatchState,
    RecentEvent,
    SpatialMetrics,
    TeamRoleContext,
    TemporalMetrics,
)

logger = logging.getLogger(__name__)

FIELD_LENGTH_M = 105.0
FIELD_WIDTH_M = 68.0


def _normalize_zone_percentages(
    zone_percentages: Optional[Dict],
) -> Dict[int, List[float]]:
    out: Dict[int, List[float]] = {}
    if not zone_percentages:
        return out
    for k, v in zone_percentages.items():
        tid = int(k) if not isinstance(k, int) else k
        if isinstance(v, list):
            out[tid] = [float(x) for x in v]
    return out


def _infer_ball_zone_name(x_m: Optional[float], y_m: Optional[float]) -> Optional[str]:
    if x_m is None:
        return None
    if x_m < FIELD_LENGTH_M / 3:
        third = "defensive_third"
    elif x_m < 2 * FIELD_LENGTH_M / 3:
        third = "middle_third"
    else:
        third = "attacking_third"
    lane = None
    if y_m is not None:
        if y_m < FIELD_WIDTH_M / 3:
            lane = "right"
        elif y_m < 2 * FIELD_WIDTH_M / 3:
            lane = "center"
        else:
            lane = "left"
    return f"{third}_{lane}" if lane else third


def _spatial_metrics_from_zones(
    zone_pct: List[float],
) -> SpatialMetrics:
    if len(zone_pct) < 9:
        return SpatialMetrics()
    def_third = sum(zone_pct[0:3]) / 100.0
    mid_third = sum(zone_pct[3:6]) / 100.0
    off_third = sum(zone_pct[6:9]) / 100.0
    left_band = (zone_pct[0] + zone_pct[3] + zone_pct[6]) / 100.0
    right_band = (zone_pct[2] + zone_pct[5] + zone_pct[8]) / 100.0
    center_col = (zone_pct[1] + zone_pct[4] + zone_pct[7]) / 100.0
    penalty_proxy = (zone_pct[7] + zone_pct[8]) / 200.0 * 1.4
    return SpatialMetrics(
        offensive_third_share=_clamp(off_third),
        midfield_share=_clamp(mid_third),
        defensive_third_share=_clamp(def_third),
        wide_left_share=_clamp(left_band),
        wide_right_share=_clamp(right_band),
        penalty_area_pressure_proxy=_clamp(min(1.0, penalty_proxy + center_col * 0.2)),
    )


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _recent_events_from_list(events: Optional[List[Dict[str, Any]]]) -> List[RecentEvent]:
    out: List[RecentEvent] = []
    if not events:
        return out
    for e in events[-20:]:
        out.append(
            RecentEvent(
                type=str(e.get("type", "")),
                team_id=e.get("team") if e.get("team") is not None else e.get("team_id"),
                frame_id=e.get("frame_id"),
                meta={k: v for k, v in e.items() if k not in ("type", "team", "team_id", "frame_id")},
            )
        )
    return out


def _temporal_from_possession_timeline(
    timeline: List[Tuple[int, int, int]],
    frame_id: int,
    window: int = 45,
) -> Tuple[int, int, int]:
    """Cuenta transiciones y segmentos recientes en ventana de frames."""
    if not timeline:
        return 0, 0, 0
    start_f = max(0, frame_id - window)
    transitions = 0
    last_team = None
    for a, b, team in timeline:
        if b < start_f:
            continue
        if last_team is not None and team != last_team:
            transitions += 1
        last_team = team
    last_seg_len = 0
    if timeline:
        a, b, team = timeline[-1]
        last_seg_len = max(0, min(b, frame_id) - max(a, start_f))
    turnovers = min(transitions, 5)
    return last_seg_len, transitions, turnovers


def build_prediction_match_state(
    *,
    frame_id: int,
    fps: float,
    possession_stats: Dict[str, Any],
    spatial_stats: Optional[Dict[str, Any]] = None,
    recent_events: Optional[List[Dict[str, Any]]] = None,
    possession_timeline: Optional[List[Tuple[int, int, int]]] = None,
    ball_field_xy_m: Optional[Tuple[float, float]] = None,
    calibration_valid: bool = False,
    current_period: Optional[int] = None,
    attack_direction_state: Optional[Dict[str, Any]] = None,
) -> MatchState:
    """
    Args:
        possession_stats: frames_by_team, passes_by_team, current_team, ...
        spatial_stats: salida normalizada (zone_percentages, zone_names, ...)
        recent_events: passes etc.
        possession_timeline: del PossessionTrackerV2
        ball_field_xy_m: proyección opcional del balón (x,y metros)
    """
    ts = frame_id / max(fps, 1e-6)
    current_team = possession_stats.get("current_team")
    if current_team is not None:
        try:
            current_team = int(current_team)
        except (TypeError, ValueError):
            current_team = None

    frames_by_team = possession_stats.get("frames_by_team") or {}
    total_f = sum(int(v) for v in frames_by_team.values()) or 1
    shares: Dict[int, float] = {}
    for k, v in frames_by_team.items():
        try:
            tid = int(k)
        except (TypeError, ValueError):
            continue
        shares[tid] = int(v) / total_f

    bp = BallPosition(projection_confidence=1.0 if (calibration_valid and ball_field_xy_m) else 0.0)
    field_progress = 0.5
    if ball_field_xy_m:
        x_m, y_m = ball_field_xy_m
        bp.x_m = x_m
        bp.y_m = y_m
        field_progress = _clamp(x_m / FIELD_LENGTH_M)
        bp.in_attacking_third = x_m >= 2 * FIELD_LENGTH_M / 3
        bp.in_wide_lane = y_m < FIELD_WIDTH_M / 3 or y_m > 2 * FIELD_WIDTH_M / 3

    spatial_stats = spatial_stats or {}
    zone_pct_by_team = _normalize_zone_percentages(spatial_stats.get("zone_percentages"))
    zone_names = spatial_stats.get("zone_names") or []
    if isinstance(zone_names, dict):
        zone_names = [zone_names[i] for i in sorted(zone_names.keys())]

    sm = SpatialMetrics()
    tid_sm = current_team if current_team in (0, 1) else 0
    zp = zone_pct_by_team.get(tid_sm) or zone_pct_by_team.get(0) or []
    if len(zp) >= 9:
        sm = _spatial_metrics_from_zones(zp)

    timeline = possession_timeline or []
    seg_len, trans, _ = _temporal_from_possession_timeline(timeline, frame_id)
    recent_passes = sum(1 for e in (recent_events or []) if e.get("type") == "pass")

    tm = TemporalMetrics(
        possession_segment_frames=seg_len,
        pass_chain_recent=min(12, recent_passes),
        turnover_recent=trans,
        transition_recent=min(8, trans),
    )

    possession_payload = {
        "frames_by_team": dict(frames_by_team),
        "passes_by_team": dict(possession_stats.get("passes_by_team") or {}),
        "current_team": current_team,
        "share_by_team": shares,
    }

    ball_zone = _infer_ball_zone_name(bp.x_m, bp.y_m)

    # Periodo: pipeline actual no expone mitades → TODO
    if current_period is None:
        logger.debug("match_state_builder: current_period unknown — usando None (TODO sport clock)")

    ads = AttackDirectionState(**(attack_direction_state or {}))
    team_context: Dict[str, TeamRoleContext] = {}
    for tid in (0, 1):
        att = ads.team_0_attacks_to if tid == 0 else ads.team_1_attacks_to
        if att is None:
            def_side = None
        else:
            def_side = "left" if att == "right" else "right"
        team_context[str(tid)] = TeamRoleContext(
            attacking_side=att,
            defending_side=def_side,
            is_attacking=(current_team == tid),
            is_defending=(current_team is not None and current_team != tid),
        )

    return MatchState(
        timestamp_sec=ts,
        frame_id=frame_id,
        fps=fps,
        current_period=current_period,
        team_in_possession=current_team if current_team in (0, 1) else None,
        calibration_valid=calibration_valid,
        ball_position=bp,
        ball_zone=ball_zone,
        recent_events=_recent_events_from_list(recent_events),
        recent_possessions=[
            {"start": a, "end": b, "team": t} for a, b, t in timeline[-12:]
        ],
        possession_stats=possession_payload,
        field_progress=field_progress,
        spatial_metrics=sm,
        temporal_metrics=tm,
        zone_percentages_by_team=zone_pct_by_team,
        zone_names=list(zone_names) if zone_names else [],
        partition_type=str(spatial_stats.get("partition_type") or spatial_stats.get("zone_partition_type") or "thirds_lanes"),
        attack_direction=ads,
        orientation_mode=ads.mode,
        team_context=team_context,
    )
