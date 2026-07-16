import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app_service.providers.database.models.core import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Match(Base):
    """Partido analizado, propiedad de un usuario. `id == job_id`."""

    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id"), nullable=False, index=True
    )
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Partido")
    opponent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    video_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifacts_prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Resumen completo denormalizado (JSON) para el detalle
    stats_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Columnas ligeras para tendencias por SQL
    possession_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    passes_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attacking_third_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MatchEvent(Base):
    __tablename__ = "match_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    match_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("matches.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    frame: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ts_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    team: Mapped[int | None] = mapped_column(Integer, nullable=True)
    from_player: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_player: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class MatchAlert(Base):
    __tablename__ = "match_alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    match_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("matches.id"), nullable=False, index=True
    )
    frame: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ts_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
