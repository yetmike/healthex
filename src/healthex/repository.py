"""Idempotent upsert of sleep session rows into PostgreSQL."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from healthex.db import get_session
from healthex.models import DailySteps, SleepSession


def upsert_sleep(database_url: str, rows: list[dict[str, Any]]) -> int:
    """
    Upsert *rows* into sleep_sessions.

    Conflict target is (user_id, start_time).  On conflict the raw payload,
    sleep_score, efficiency, and ingested_at are refreshed.

    Returns the number of rows inserted or updated.
    """
    if not rows:
        return 0

    with get_session(database_url) as session:
        stmt = (
            insert(SleepSession)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_sleep_user_start",
                set_={
                    "raw": insert(SleepSession).excluded.raw,
                    "sleep_score": insert(SleepSession).excluded.sleep_score,
                    "efficiency": insert(SleepSession).excluded.efficiency,
                    "ingested_at": text("now()"),
                },
            )
        )
        result = session.execute(stmt.returning(SleepSession.id))
        return len(result.fetchall())


def upsert_steps(database_url: str, rows: list[dict[str, Any]]) -> int:
    """Upsert *rows* into daily_steps. Conflict target is (user_id, date)."""
    if not rows:
        return 0
    with get_session(database_url) as session:
        stmt = (
            insert(DailySteps)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_steps_user_date",
                set_={
                    "steps": insert(DailySteps).excluded.steps,
                    "raw": insert(DailySteps).excluded.raw,
                    "ingested_at": text("now()"),
                },
            )
        )
        result = session.execute(stmt.returning(DailySteps.id))
        return len(result.fetchall())
