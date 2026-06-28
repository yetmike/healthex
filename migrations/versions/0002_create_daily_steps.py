"""create daily_steps table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_steps",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("steps", sa.Integer, nullable=False),
        sa.Column("source_platform", sa.Text, nullable=True),
        sa.Column("raw", JSONB, nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "date", name="uq_steps_user_date"),
    )
    op.create_index("idx_steps_user_date", "daily_steps", ["user_id", "date"])


def downgrade() -> None:
    op.drop_index("idx_steps_user_date", table_name="daily_steps")
    op.drop_table("daily_steps")
