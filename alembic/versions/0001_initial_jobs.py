"""initial jobs table

Revision ID: 0001_initial_jobs
Revises: 
Create Date: 2026-05-07 09:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_jobs"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_uri", sa.Text(), nullable=False),
        sa.Column("output_uri", sa.Text(), nullable=True),
        sa.Column("result_json_uri", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("jobs")

