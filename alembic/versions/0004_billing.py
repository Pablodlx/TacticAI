"""plans, subscriptions, usage ledger, stripe webhook events

Revision ID: 0004_billing
Revises: 0003_matches
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_billing"
down_revision = "0003_matches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    plans = op.create_table(
        "plans",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("monthly_seconds", sa.Integer(), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=64), nullable=True),
        sa.Column("price_eur_cents", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.bulk_insert(plans, [
        {"code": "free", "name": "Free", "monthly_seconds": 3600,
         "stripe_price_id": None, "price_eur_cents": 0, "active": True},
        {"code": "starter", "name": "Starter", "monthly_seconds": 18000,
         "stripe_price_id": None, "price_eur_cents": 999, "active": True},
        {"code": "pro", "name": "Pro", "monthly_seconds": 72000,
         "stripe_price_id": None, "price_eur_cents": 2999, "active": True},
    ])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_period_start", sa.DateTime(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plan_code"], ["plans.code"]),
        sa.UniqueConstraint("stripe_subscription_id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    op.create_table(
        "usage_ledger",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("entry_type", sa.String(length=16), nullable=False),
        sa.Column("seconds", sa.Float(), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
    )
    op.create_index("ix_usage_ledger_user_id", "usage_ledger", ["user_id"])

    op.create_table(
        "stripe_webhook_events",
        sa.Column("stripe_event_id", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("stripe_event_id"),
    )


def downgrade() -> None:
    op.drop_table("stripe_webhook_events")
    op.drop_table("usage_ledger")
    op.drop_table("subscriptions")
    op.drop_table("plans")
