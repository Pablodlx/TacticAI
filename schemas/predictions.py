"""
Modelos estructurados para predicción de eventos (capa distinta de modules.match_state.MatchState).
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class BallPosition(BaseModel):
    x_m: Optional[float] = None
    y_m: Optional[float] = None
    zone_id: Optional[int] = None
    in_attacking_third: Optional[bool] = None
    in_wide_lane: Optional[bool] = None
    projection_confidence: float = Field(0.0, ge=0.0, le=1.0)


class TeamShape(BaseModel):
    """Distribución aproximada del equipo en campo (opcional)."""

    width_m: Optional[float] = None
    depth_m: Optional[float] = None
    centroid_x_m: Optional[float] = None
    centroid_y_m: Optional[float] = None


class RecentEvent(BaseModel):
    type: str = ""
    team_id: Optional[int] = None
    frame_id: Optional[int] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class TeamStats(BaseModel):
    frames_share: float = 0.0
    passes_total: int = 0
    passes_recent_window: int = 0


class SpatialMetrics(BaseModel):
    """Métricas espaciales agregadas ya derivadas o provenientes del tracker."""

    offensive_third_share: float = 0.0
    midfield_share: float = 0.0
    defensive_third_share: float = 0.0
    wide_left_share: float = 0.0
    wide_right_share: float = 0.0
    penalty_area_pressure_proxy: float = 0.0


class TemporalMetrics(BaseModel):
    possession_segment_frames: int = 0
    pass_chain_recent: int = 0
    turnover_recent: int = 0
    transition_recent: int = 0


class PredictionEvidence(BaseModel):
    code: str
    detail: str
    value: Optional[float] = None


AttackSide = Literal["left", "right"]
OrientationMode = Literal["auto", "manual"]
OrientationSource = Literal["auto_inference", "manual_override"]


class TeamRoleContext(BaseModel):
    attacking_side: Optional[AttackSide] = None
    defending_side: Optional[AttackSide] = None
    is_attacking: bool = False
    is_defending: bool = False


class AttackDirectionState(BaseModel):
    mode: OrientationMode = "auto"
    period: int = 1
    team_0_attacks_to: Optional[AttackSide] = None
    team_1_attacks_to: Optional[AttackSide] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    source: OrientationSource = "auto_inference"


class AttackDirectionOverrideRequest(BaseModel):
    session_id: str
    period: int = 1
    team_0_attacks_to: AttackSide


class AttackDirectionResponse(BaseModel):
    session_id: str
    state: AttackDirectionState


class MatchState(BaseModel):
    """Estado del partido para el motor predictivo (serializable)."""

    timestamp_sec: float = 0.0
    frame_id: int = 0
    fps: float = 30.0
    current_period: Optional[int] = None
    team_in_possession: Optional[int] = None
    calibration_valid: bool = False

    ball_position: BallPosition = Field(default_factory=BallPosition)
    ball_zone: Optional[str] = None

    player_positions: Optional[List[Dict[str, Any]]] = None
    team_shapes: Dict[int, TeamShape] = Field(default_factory=dict)

    recent_events: List[RecentEvent] = Field(default_factory=list)
    recent_possessions: List[Dict[str, Any]] = Field(default_factory=list)

    possession_stats: Dict[str, Any] = Field(default_factory=dict)
    field_progress: float = Field(0.0, ge=0.0, le=1.0)

    spatial_metrics: SpatialMetrics = Field(default_factory=SpatialMetrics)
    temporal_metrics: TemporalMetrics = Field(default_factory=TemporalMetrics)

    zone_percentages_by_team: Dict[int, List[float]] = Field(default_factory=dict)
    zone_names: List[str] = Field(default_factory=list)
    partition_type: str = "thirds_lanes"
    attack_direction: AttackDirectionState = Field(default_factory=AttackDirectionState)
    orientation_mode: OrientationMode = "auto"
    team_context: Dict[str, TeamRoleContext] = Field(default_factory=dict)


SeverityLevel = Literal["low", "medium", "high"]


class EventPrediction(BaseModel):
    id: str
    event_type: str
    team_id: Optional[int] = None
    probability: float = Field(..., ge=0.0, le=1.0)
    severity: SeverityLevel = "low"
    time_horizon_sec: int = 6
    title: str = ""
    evidence: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    explanation: str = ""


class PredictionDispatchRecord(BaseModel):
    prediction_id: str
    event_type: str
    team_id: Optional[int]
    emitted_at_wallclock: float
    probability: float
    severity: SeverityLevel
    frame_id: int
