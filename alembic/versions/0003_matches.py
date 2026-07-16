"""matches, match_events, match_alerts

Revision ID: 0003_matches
Revises: 0002_users_and_auth
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_matches"
down_revision = "0002_users_and_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "matches",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("opponent", sa.String(length=255), nullable=True),
        sa.Column("match_date", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("video_uri", sa.Text(), nullable=True),
        sa.Column("artifacts_prefix", sa.Text(), nullable=True),
        sa.Column("stats_json", sa.Text(), nullable=True),
        sa.Column("possession_pct", sa.Float(), nullable=True),
        sa.Column("passes_total", sa.Integer(), nullable=True),
        sa.Column("attacking_third_pct", sa.Float(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
    )
    op.create_index("ix_matches_user_id", "matches", ["user_id"])

    op.create_table(
        "match_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("match_id", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("frame", sa.Integer(), nullable=True),
        sa.Column("ts_seconds", sa.Float(), nullable=True),
        sa.Column("team", sa.Integer(), nullable=True),
        sa.Column("from_player", sa.Integer(), nullable=True),
        sa.Column("to_player", sa.Integer(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
    )
    op.create_index("ix_match_events_match_id", "match_events", ["match_id"])

    op.create_table(
        "match_alerts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("match_id", sa.String(length=64), nullable=False),
        sa.Column("frame", sa.Integer(), nullable=True),
        sa.Column("ts_seconds", sa.Float(), nullable=True),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
    )
    op.create_index("ix_match_alerts_match_id", "match_alerts", ["match_id"])


def downgrade() -> None:
    op.drop_table("match_alerts")
    op.drop_table("match_events")
    op.drop_table("matches")
