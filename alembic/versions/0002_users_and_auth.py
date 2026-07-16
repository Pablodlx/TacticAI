"""users and refresh tokens

Revision ID: 0002_users_and_auth
Revises: 0001_initial_jobs
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_users_and_auth"
down_revision = "0001_initial_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("stripe_customer_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("stripe_customer_id"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # Ownership y contabilidad de cuota en jobs
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("user_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("video_duration_seconds", sa.Float(), nullable=True))
        batch.add_column(sa.Column("charged_seconds", sa.Float(), nullable=True))
        batch.add_column(sa.Column("progress_pct", sa.Float(), nullable=True))
        batch.create_foreign_key("fk_jobs_user_id", "users", ["user_id"], ["id"])
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_constraint("fk_jobs_user_id", type_="foreignkey")
        batch.drop_column("progress_pct")
        batch.drop_column("charged_seconds")
        batch.drop_column("video_duration_seconds")
        batch.drop_column("user_id")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
