"""create daily_rhr and daily_hrv tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_rhr",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("rhr_date", sa.Date, nullable=False),
        sa.Column("bpm", sa.Integer, nullable=False),
        sa.Column("calculation_method", sa.Text, nullable=True),
        sa.Column("source_platform", sa.Text, nullable=True),
        sa.Column("raw", JSONB, nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "rhr_date", name="uq_rhr_user_date"),
    )
    op.create_index("idx_rhr_user_date", "daily_rhr", ["user_id", "rhr_date"])

    op.create_table(
        "daily_hrv",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("hrv_date", sa.Date, nullable=False),
        sa.Column("avg_hrv_ms", sa.Numeric(8, 3), nullable=False),
        sa.Column("non_rem_bpm", sa.Integer, nullable=True),
        sa.Column("entropy", sa.Numeric(8, 4), nullable=True),
        sa.Column("deep_sleep_rmssd_ms", sa.Numeric(8, 3), nullable=True),
        sa.Column("source_platform", sa.Text, nullable=True),
        sa.Column("raw", JSONB, nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "hrv_date", name="uq_hrv_user_date"),
    )
    op.create_index("idx_hrv_user_date", "daily_hrv", ["user_id", "hrv_date"])


def downgrade() -> None:
    op.drop_index("idx_hrv_user_date", table_name="daily_hrv")
    op.drop_table("daily_hrv")
    op.drop_index("idx_rhr_user_date", table_name="daily_rhr")
    op.drop_table("daily_rhr")
