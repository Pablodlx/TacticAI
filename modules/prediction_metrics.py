"""
Métricas predictivas heurísticas a partir de MatchState (schemas).
Valores en [0, 1] salvo indicación.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from schemas.predictions import MatchState
from modules.field_orientation import orient_x_for_team, get_team_relative_zone

# Campo en metros (coherente con field_heatmap_system)
FIELD_LENGTH_M = 105.0
FIELD_WIDTH_M = 68.0


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _zone_thirds_shares(
    zone_pct: List[float],
) -> Tuple[float, float, float]:
    """Retorna (def%, mid%, off%) para layout 9 zonas thirds_lanes."""
    if not zone_pct or len(zone_pct) < 9:
        n = max(len(zone_pct), 1)
        return (1.0 / 3, 1.0 / 3, 1.0 / 3)
    d = sum(zone_pct[0:3])
    m = sum(zone_pct[3:6])
    o = sum(zone_pct[6:9])
    t = d + m + o
    if t <= 1e-6:
        return (1.0 / 3, 1.0 / 3, 1.0 / 3)
    return (d / t, m / t, o / t)


def estimate_expected_threat_proxy(state: MatchState, team_id: int) -> float:
    """
    Proxy de amenaza esperada: posesión en último tercio + progresión + presión en área.
    """
    zm = state.spatial_metrics
    fp = state.field_progress
    if state.ball_position.x_m is not None:
        x_att = orient_x_for_team(state.ball_position.x_m, team_id, state.attack_direction.model_dump())
        fp = _clamp01(x_att / FIELD_LENGTH_M)
    base = 0.45 * zm.offensive_third_share + 0.35 * fp + 0.20 * zm.penalty_area_pressure_proxy
    if state.team_in_possession == team_id:
        base += 0.05
    return _clamp01(base)


def estimate_field_tilt(state: MatchState, team_id: int) -> float:
    """
    Inclinación de campo: diferencia ofensiva vs defensiva en zona del balón.
    """
    z = state.zone_percentages_by_team.get(team_id) or state.zone_percentages_by_team.get(
        str(team_id)  # type: ignore
    )
    if not z or len(z) < 9:
        return 0.5
    d, m, o = _zone_thirds_shares([float(x) for x in z])
    # tilt hacia ataque del equipo con balón
    if state.team_in_possession == team_id:
        return _clamp01(0.5 + (o - d) * 0.9)
    return _clamp01(0.5 + (d - o) * 0.5)


def estimate_progression_rate(state: MatchState, team_id: int = 0) -> float:
    """Tasa de progresión hacia el marco rival (basada en field_progress y eventos)."""
    base = state.field_progress
    if state.ball_position.x_m is not None:
        x_att = orient_x_for_team(state.ball_position.x_m, team_id, state.attack_direction.model_dump())
        base = _clamp01(x_att / FIELD_LENGTH_M)
    pm = state.temporal_metrics
    pass_boost = min(0.25, pm.pass_chain_recent * 0.04)
    return _clamp01(base * 0.75 + pass_boost + 0.1 * min(1.0, pm.possession_segment_frames / 120.0))


def estimate_final_third_entries(state: MatchState, team_id: int) -> float:
    """Señal de entradas / presencia sostenida en último tercio."""
    z = state.zone_percentages_by_team.get(team_id) or []
    if len(z) >= 9:
        off_share = sum(float(z[i]) for i in range(6, 9)) / 100.0
        return _clamp01(off_share)
    return _clamp01(state.spatial_metrics.offensive_third_share)


def estimate_box_entry_risk(state: MatchState, team_id: int = 0) -> float:
    rel_bonus = 0.0
    if state.ball_position.x_m is not None and state.ball_position.y_m is not None:
        rel_zone = get_team_relative_zone(
            state.ball_position.x_m, state.ball_position.y_m, team_id, state.attack_direction.model_dump()
        )
        if rel_zone in {"box_zone", "pre_box_zone", "byline_zone"}:
            rel_bonus = 0.15
    return _clamp01(
        0.5 * state.spatial_metrics.penalty_area_pressure_proxy
        + 0.3 * state.field_progress
        + 0.2 * state.spatial_metrics.offensive_third_share
        + rel_bonus
    )


def estimate_shot_pressure_signal(state: MatchState, team_id: int = 0) -> float:
    m = state.spatial_metrics
    t = state.temporal_metrics
    return _clamp01(
        0.35 * m.penalty_area_pressure_proxy
        + 0.30 * m.offensive_third_share
        + 0.20 * min(1.0, t.pass_chain_recent / 8.0)
        + 0.15 * estimate_progression_rate(state, team_id)
    )


def estimate_corner_likelihood_signal(state: MatchState, team_id: int = 0) -> float:
    """
    Córner: presión ancha + profundidad sin tiro aún; banda y línea de fondo.
    """
    m = state.spatial_metrics
    wide = m.wide_left_share + m.wide_right_share
    byline_boost = 0.0
    if state.ball_position.x_m is not None and state.ball_position.y_m is not None:
        rz = get_team_relative_zone(
            state.ball_position.x_m, state.ball_position.y_m, team_id, state.attack_direction.model_dump()
        )
        if rz == "byline_zone":
            byline_boost = 0.2
    return _clamp01(
        0.40 * min(1.0, wide * 1.2)
        + 0.35 * m.offensive_third_share
        + 0.25 * estimate_wide_overload(state)
        + byline_boost
    )


def estimate_turnover_risk(state: MatchState, subject_team: int) -> float:
    """Riesgo de pérdida peligrosa en salida para el equipo subject_team."""
    ti = state.team_in_possession
    z = state.zone_percentages_by_team.get(subject_team) or []
    defensive_share = 0.33
    if len(z) >= 9:
        defensive_share = sum(float(z[i]) for i in range(0, 3)) / 100.0
    pressing = state.spatial_metrics.midfield_share
    chaos = min(1.0, state.temporal_metrics.turnover_recent * 0.15)
    if ti is None:
        return _clamp01(0.35 + 0.2 * defensive_share)
    if ti == subject_team:
        return _clamp01(0.45 * defensive_share + 0.30 * pressing + 0.25 * chaos)
    return _clamp01(0.25 + 0.35 * defensive_share)


def estimate_transition_danger(state: MatchState, attacking_team: int) -> float:
    """Peligro en transición: cambios recientes de posesión + espacio delantero."""
    tr = min(1.0, state.temporal_metrics.transition_recent * 0.15 + state.temporal_metrics.turnover_recent * 0.1)
    third = estimate_final_third_entries(state, attacking_team)
    mom = estimate_attacking_momentum(state, attacking_team)
    return _clamp01(0.45 * tr + 0.35 * third + 0.20 * mom)


def estimate_wide_overload(state: MatchState) -> float:
    m = state.spatial_metrics
    return _clamp01((m.wide_left_share + m.wide_right_share) * 0.5)


def estimate_attacking_momentum(state: MatchState, team_id: int) -> float:
    t = state.temporal_metrics
    z = state.zone_percentages_by_team.get(team_id) or []
    off = state.spatial_metrics.offensive_third_share
    if len(z) >= 9:
        off = sum(float(z[i]) for i in range(6, 9)) / 100.0
    chain = min(1.0, t.pass_chain_recent / 6.0)
    seg = min(1.0, t.possession_segment_frames / 90.0)
    return _clamp01(0.5 * off + 0.3 * chain + 0.2 * seg)


def defensive_resistance_proxy(state: MatchState, opponent_team: int) -> float:
    """Qué tan replegado / en last third está el rival (reduce prob de gol/tiro)."""
    z = state.zone_percentages_by_team.get(opponent_team) or []
    if len(z) >= 9:
        def_share = sum(float(z[i]) for i in range(0, 3)) / 100.0
        return _clamp01(def_share * 0.7 + 0.15)
    return 0.4


def compute_all_metrics(state: MatchState, team_id: int) -> Dict[str, float]:
    """Métricas usadas por el motor; claves alineadas con config weights."""
    opp = 1 - team_id if team_id in (0, 1) else 0
    return {
        "expected_threat_proxy": estimate_expected_threat_proxy(state, team_id),
        "field_tilt": estimate_field_tilt(state, team_id),
        "progression_rate": estimate_progression_rate(state, team_id),
        "final_third_entries_signal": estimate_final_third_entries(state, team_id),
        "box_entry_risk": estimate_box_entry_risk(state, team_id),
        "shot_pressure_signal": estimate_shot_pressure_signal(state, team_id),
        "corner_likelihood_signal": estimate_corner_likelihood_signal(state, team_id),
        "turnover_risk": estimate_turnover_risk(state, team_id),
        "transition_danger": estimate_transition_danger(state, team_id),
        "wide_overload": estimate_wide_overload(state),
        "attacking_momentum": estimate_attacking_momentum(state, team_id),
        "defensive_resistance": defensive_resistance_proxy(state, opp),
        "offensive_pressure": state.spatial_metrics.offensive_third_share,
    }


def sigmoid(x: float, scale: float = 1.0) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-scale * x))
    except OverflowError:
        return 1.0 if x > 0 else 0.0
