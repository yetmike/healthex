"""create sleep_sessions table

Revision ID: 0001
Revises:
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sleep_sessions",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("civil_date", sa.Date, nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sleep_type", sa.Text, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("minutes_asleep", sa.Integer, nullable=True),
        sa.Column("minutes_awake", sa.Integer, nullable=True),
        sa.Column("minutes_light", sa.Integer, nullable=True),
        sa.Column("minutes_deep", sa.Integer, nullable=True),
        sa.Column("minutes_rem", sa.Integer, nullable=True),
        sa.Column("efficiency", sa.Numeric(5, 2), nullable=True),
        sa.Column("sleep_score", sa.Integer, nullable=True),
        sa.Column("source_platform", sa.Text, nullable=True),
        sa.Column("raw", JSONB, nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "start_time", name="uq_sleep_user_start"),
    )
    op.create_index("idx_sleep_user_date", "sleep_sessions", ["user_id", "civil_date"])


def downgrade() -> None:
    op.drop_index("idx_sleep_user_date", table_name="sleep_sessions")
    op.drop_table("sleep_sessions")
