"""Cuotas de horas de análisis por periodo de suscripción."""

from datetime import datetime

from sqlalchemy import func

from app_service.providers.database.models import Plan
from app_service.providers.database.models.billing import Subscription, UsageLedger


def _month_period(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Periodo mes-natural (para el plan free, sin objeto Stripe)."""
    now = now or datetime.utcnow()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


class QuotaService:
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory

    def ensure_subscription(self, user_id: str) -> "Subscription":
        """Garantiza una suscripción activa (crea la free si no hay ninguna,
        o renueva el periodo mensual de la free si expiró)."""
        now = datetime.utcnow()
        with self.db_session_factory() as db:
            sub = (
                db.query(Subscription)
                .filter(Subscription.user_id == user_id)
                .order_by(Subscription.created_at.desc())
                .first()
            )
            if sub is None:
                start, end = _month_period(now)
                sub = Subscription(
                    user_id=user_id, plan_code="free", status="active",
                    current_period_start=start, current_period_end=end,
                )
                db.add(sub)
                db.commit()
                db.refresh(sub)
            elif sub.stripe_subscription_id is None and sub.current_period_end < now:
                # Renovación del periodo del plan free (mes natural)
                start, end = _month_period(now)
                sub.current_period_start = start
                sub.current_period_end = end
                db.commit()
                db.refresh(sub)
            return sub

    def get_usage(self, user_id: str) -> dict:
        sub = self.ensure_subscription(user_id)
        with self.db_session_factory() as db:
            plan = db.get(Plan, sub.plan_code)
            quota = plan.monthly_seconds if plan else 0
            if sub.status not in ("active",):
                quota = 0  # past_due/canceled: se consulta pero no se analiza
            used = self._used_seconds(db, user_id, sub.current_period_start)
            return {
                "plan": sub.plan_code,
                "plan_name": plan.name if plan else sub.plan_code,
                "status": sub.status,
                "period_start": sub.current_period_start.isoformat(),
                "period_end": sub.current_period_end.isoformat(),
                "quota_seconds": quota,
                "used_seconds": used,
                "remaining_seconds": max(0.0, quota - used),
                "cancel_at_period_end": sub.cancel_at_period_end,
            }

    def remaining_seconds(self, user_id: str) -> float:
        return self.get_usage(user_id)["remaining_seconds"]

    def debit(self, user_id: str, job_id: str, seconds: float) -> None:
        sub = self.ensure_subscription(user_id)
        with self.db_session_factory() as db:
            db.add(UsageLedger(
                user_id=user_id, job_id=job_id, entry_type="debit",
                seconds=float(seconds), period_start=sub.current_period_start,
            ))
            db.commit()

    def refund(self, job_id: str) -> None:
        """Reembolsa el débito de un job fallido (si no se reembolsó ya)."""
        with self.db_session_factory() as db:
            debit = (
                db.query(UsageLedger)
                .filter(UsageLedger.job_id == job_id, UsageLedger.entry_type == "debit")
                .first()
            )
            if debit is None:
                return
            already = (
                db.query(UsageLedger)
                .filter(UsageLedger.job_id == job_id, UsageLedger.entry_type == "refund")
                .first()
            )
            if already is not None:
                return
            db.add(UsageLedger(
                user_id=debit.user_id, job_id=job_id, entry_type="refund",
                seconds=debit.seconds, period_start=debit.period_start,
            ))
            db.commit()

    def _used_seconds(self, db, user_id: str, period_start: datetime) -> float:
        def _sum(entry_type: str) -> float:
            val = (
                db.query(func.coalesce(func.sum(UsageLedger.seconds), 0.0))
                .filter(
                    UsageLedger.user_id == user_id,
                    UsageLedger.period_start == period_start,
                    UsageLedger.entry_type == entry_type,
                )
                .scalar()
            )
            return float(val or 0.0)

        return max(0.0, _sum("debit") - _sum("refund") - _sum("adjustment"))
