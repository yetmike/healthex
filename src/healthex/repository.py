"""Idempotent upsert of sleep session rows into PostgreSQL."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from healthex.db import get_session
from healthex.models import Base, DailyHrv, DailyRhr, DailySteps, SleepSession


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
                    "sleep_latency_minutes": insert(SleepSession).excluded.sleep_latency_minutes,
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


def upsert_rhr(database_url: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with get_session(database_url) as session:
        stmt = (
            insert(DailyRhr)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_rhr_user_date",
                set_={
                    "bpm": insert(DailyRhr).excluded.bpm,
                    "raw": insert(DailyRhr).excluded.raw,
                    "ingested_at": text("now()"),
                },
            )
        )
        return len(session.execute(stmt.returning(DailyRhr.id)).fetchall())


def upsert_hrv(database_url: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with get_session(database_url) as session:
        stmt = (
            insert(DailyHrv)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_hrv_user_date",
                set_={
                    "avg_hrv_ms": insert(DailyHrv).excluded.avg_hrv_ms,
                    "non_rem_bpm": insert(DailyHrv).excluded.non_rem_bpm,
                    "entropy": insert(DailyHrv).excluded.entropy,
                    "deep_sleep_rmssd_ms": insert(DailyHrv).excluded.deep_sleep_rmssd_ms,
                    "raw": insert(DailyHrv).excluded.raw,
                    "ingested_at": text("now()"),
                },
            )
        )
        return len(session.execute(stmt.returning(DailyHrv.id)).fetchall())


def upsert(database_url: str, model: type[Base], rows: list[dict[str, Any]]) -> int:
    """Upsert *rows* on *model*'s primary key, overwriting every other column.

    Rows must be unique by primary key and share the same keys. Batched because
    a backfill can exceed the 65535 bind parameters one statement may carry.
    """
    if not rows:
        return 0
    table = model.__table__
    pk = [c.name for c in table.primary_key]
    with get_session(database_url) as session:
        for i in range(0, len(rows), 1000):
            stmt = insert(model).values(rows[i : i + 1000])
            session.execute(
                stmt.on_conflict_do_update(
                    index_elements=pk,
                    set_={c.name: stmt.excluded[c.name] for c in table.columns if c.name not in pk},
                )
            )
    return len(rows)
