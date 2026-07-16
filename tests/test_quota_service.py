"""Tests del sistema de cuotas por periodo (débito, reembolso, renovación)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app_service.providers.database.models import Base, Plan, User
from app_service.providers.database.models.billing import Subscription
from app_service.services.quota import QuotaService


@pytest.fixture
def db_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add(Plan(code="free", name="Free", monthly_seconds=3600, price_eur_cents=0))
        db.add(Plan(code="starter", name="Starter", monthly_seconds=18000, price_eur_cents=999))
        db.add(User(id="u1", email="a@b.com", password_hash="x"))
        db.commit()
    return factory


@pytest.fixture
def quota(db_factory):
    return QuotaService(db_session_factory=db_factory)


class TestQuota:
    def test_free_subscription_created_automatically(self, quota):
        usage = quota.get_usage("u1")
        assert usage["plan"] == "free"
        assert usage["quota_seconds"] == 3600
        assert usage["remaining_seconds"] == 3600

    def test_debit_reduces_remaining(self, quota):
        quota.debit("u1", "job-1", 600)
        assert quota.remaining_seconds("u1") == 3000

    def test_refund_restores(self, quota):
        quota.debit("u1", "job-1", 600)
        quota.refund("job-1")
        assert quota.remaining_seconds("u1") == 3600

    def test_refund_idempotent(self, quota):
        quota.debit("u1", "job-1", 600)
        quota.refund("job-1")
        quota.refund("job-1")
        assert quota.remaining_seconds("u1") == 3600

    def test_refund_unknown_job_noop(self, quota):
        quota.refund("job-x")
        assert quota.remaining_seconds("u1") == 3600

    def test_free_period_renews(self, quota, db_factory):
        quota.debit("u1", "job-1", 3600)
        assert quota.remaining_seconds("u1") == 0
        # Simular que el periodo (y su débito) pertenecen al mes anterior
        old_start = datetime.utcnow() - timedelta(days=60)
        with db_factory() as db:
            from app_service.providers.database.models.billing import UsageLedger
            sub = db.query(Subscription).filter_by(user_id="u1").first()
            sub.current_period_start = old_start
            sub.current_period_end = datetime.utcnow() - timedelta(days=30)
            for entry in db.query(UsageLedger).filter_by(user_id="u1").all():
                entry.period_start = old_start
            db.commit()
        # El nuevo periodo mensual restablece la cuota (el débito viejo no computa)
        assert quota.remaining_seconds("u1") == 3600

    def test_paid_plan_quota(self, quota, db_factory):
        with db_factory() as db:
            sub = db.query(Subscription).filter_by(user_id="u1").first() \
                or None
        quota.ensure_subscription("u1")
        with db_factory() as db:
            sub = db.query(Subscription).filter_by(user_id="u1").first()
            sub.plan_code = "starter"
            sub.stripe_subscription_id = "sub_123"
            db.commit()
        usage = quota.get_usage("u1")
        assert usage["plan"] == "starter"
        assert usage["quota_seconds"] == 18000

    def test_past_due_blocks_analysis(self, quota, db_factory):
        quota.ensure_subscription("u1")
        with db_factory() as db:
            sub = db.query(Subscription).filter_by(user_id="u1").first()
            sub.status = "past_due"
            sub.stripe_subscription_id = "sub_123"
            db.commit()
        assert quota.remaining_seconds("u1") == 0
