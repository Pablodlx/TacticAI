"""Utilidades de orientación de campo relativas al equipo."""

from __future__ import annotations

from typing import Optional, Tuple

FIELD_LENGTH_M = 105.0
FIELD_WIDTH_M = 68.0


def orient_x_for_team(x: float, team_id: int, attack_direction_state: dict) -> float:
    """Devuelve x en marco atacante (0=propia portería, 105=portería rival)."""
    side = get_team_attacks_to(team_id, attack_direction_state)
    if side == "right":
        return x
    if side == "left":
        return FIELD_LENGTH_M - x
    return x


def get_team_attacks_to(team_id: int, attack_direction_state: Optional[dict]) -> Optional[str]:
    if not attack_direction_state:
        return None
    if team_id == 0:
        return attack_direction_state.get("team_0_attacks_to")
    if team_id == 1:
        return attack_direction_state.get("team_1_attacks_to")
    return None


def normalize_to_attacking_frame(
    x: float, y: float, team_id: int, attack_direction_state: dict
) -> Tuple[float, float]:
    x_att = orient_x_for_team(x, team_id, attack_direction_state)
    # y no se invierte: izquierda/derecha de banda se conserva como vista TV del sistema
    return x_att, y


def get_team_relative_zone(x: float, y: float, team_id: int, attack_direction_state: dict) -> str:
    x_att, y_att = normalize_to_attacking_frame(x, y, team_id, attack_direction_state)

    third = "middle_third"
    if x_att < FIELD_LENGTH_M / 3:
        third = "defensive_third"
    elif x_att >= 2 * FIELD_LENGTH_M / 3:
        third = "attacking_third"

    flank = "center_lane"
    if y_att < FIELD_WIDTH_M / 3:
        flank = "right_flank"
    elif y_att > 2 * FIELD_WIDTH_M / 3:
        flank = "left_flank"

    if x_att >= FIELD_LENGTH_M - 8.0:
        return "byline_zone"
    if x_att >= FIELD_LENGTH_M - 16.5 and 20.0 <= y_att <= 48.0:
        return "box_zone"
    if x_att >= FIELD_LENGTH_M - 24.0 and 16.0 <= y_att <= 52.0:
        return "pre_box_zone"

    if 20.0 <= y_att <= 30.0 or 38.0 <= y_att <= 48.0:
        # aprox half-spaces
        return f"half_space_{'right' if y_att < FIELD_WIDTH_M / 2 else 'left'}"

    return f"{third}:{flank}"


def get_team_role_for_zone(zone_name: str, team_id: int, attack_direction_state: dict) -> str:
    z = zone_name or ""
    if z.startswith("attacking_third") or z in {"box_zone", "pre_box_zone", "byline_zone"}:
        return "offensive"
    if z.startswith("defensive_third"):
        return "defensive"
    return "neutral"


def is_attacking_phase(team_id: int, match_state: dict) -> bool:
    return match_state.get("team_in_possession") == team_id


def is_defending_phase(team_id: int, match_state: dict) -> bool:
    tip = match_state.get("team_in_possession")
    return tip is not None and tip != team_id


def get_action_context(team_id: int, x: float, y: float, match_state: dict) -> dict:
    ads = match_state.get("attack_direction") or {}
    rz = get_team_relative_zone(x, y, team_id, ads)
    return {
        "relative_zone": rz,
        "phase": "attack" if is_attacking_phase(team_id, match_state) else "defense",
        "role": get_team_role_for_zone(rz, team_id, ads),
    }
