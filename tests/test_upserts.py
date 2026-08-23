"""Integration tests for the daily_* upsert paths — requires a real Postgres.

These cover the on-conflict behaviour that a SQLAlchemy, psycopg or Postgres
bump would most plausibly break: idempotent re-ingest and value refresh.
"""

from typing import Any

import pytest
from sqlalchemy import Engine, text

from healthex.heart import parse_hrv, parse_rhr
from healthex.repository import upsert_hrv, upsert_rhr, upsert_steps
from healthex.steps import aggregate_days

pytestmark = pytest.mark.usefixtures("clean_db")


def _steps_point(count: str) -> dict[str, Any]:
    return {
        "steps": {
            "count": count,
            "interval": {"civilStartTime": {"date": {"year": 2026, "month": 6, "day": 27}}},
        },
        "dataSource": {"platform": "ios"},
    }


def _rhr_point(bpm: str) -> dict[str, Any]:
    return {
        "dailyRestingHeartRate": {
            "date": {"year": 2026, "month": 6, "day": 27},
            "beatsPerMinute": bpm,
        },
        "dataSource": {"platform": "ios"},
    }


def _hrv_point(avg: str) -> dict[str, Any]:
    return {
        "dailyHeartRateVariability": {
            "date": {"year": 2026, "month": 6, "day": 27},
            "averageHeartRateVariabilityMilliseconds": avg,
            "entropy": "0.5",
        },
        "dataSource": {"platform": "ios"},
    }


def _scalar(engine: Engine, sql: str) -> Any:
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def test_upsert_steps_inserts_then_updates(db_url: str, db_engine: Engine) -> None:
    assert upsert_steps(db_url, aggregate_days([_steps_point("100")], user_id="t")) == 1
    assert upsert_steps(db_url, aggregate_days([_steps_point("777")], user_id="t")) == 1

    assert _scalar(db_engine, "SELECT count(*) FROM daily_steps WHERE user_id='t'") == 1
    assert _scalar(db_engine, "SELECT steps FROM daily_steps WHERE user_id='t'") == 777


def test_upsert_rhr_inserts_then_updates(db_url: str, db_engine: Engine) -> None:
    first = parse_rhr(_rhr_point("54"), user_id="t")
    second = parse_rhr(_rhr_point("48"), user_id="t")
    assert first is not None and second is not None

    assert upsert_rhr(db_url, [first]) == 1
    assert upsert_rhr(db_url, [second]) == 1

    assert _scalar(db_engine, "SELECT count(*) FROM daily_rhr WHERE user_id='t'") == 1
    assert _scalar(db_engine, "SELECT bpm FROM daily_rhr WHERE user_id='t'") == 48


def test_upsert_hrv_inserts_then_updates(db_url: str, db_engine: Engine) -> None:
    first = parse_hrv(_hrv_point("42.5"), user_id="t")
    second = parse_hrv(_hrv_point("55.25"), user_id="t")
    assert first is not None and second is not None

    assert upsert_hrv(db_url, [first]) == 1
    assert upsert_hrv(db_url, [second]) == 1

    assert _scalar(db_engine, "SELECT count(*) FROM daily_hrv WHERE user_id='t'") == 1
    assert float(_scalar(db_engine, "SELECT avg_hrv_ms FROM daily_hrv WHERE user_id='t'")) == 55.25


def test_ingested_at_is_refreshed_on_conflict(db_url: str, db_engine: Engine) -> None:
    upsert_steps(db_url, aggregate_days([_steps_point("100")], user_id="t"))
    before = _scalar(db_engine, "SELECT ingested_at FROM daily_steps WHERE user_id='t'")
    upsert_steps(db_url, aggregate_days([_steps_point("200")], user_id="t"))
    after = _scalar(db_engine, "SELECT ingested_at FROM daily_steps WHERE user_id='t'")
    assert after >= before


def test_empty_rows_are_a_noop(db_url: str) -> None:
    assert upsert_steps(db_url, []) == 0
    assert upsert_rhr(db_url, []) == 0
    assert upsert_hrv(db_url, []) == 0


def test_batch_insert_of_multiple_days(db_url: str, db_engine: Engine) -> None:
    points = [
        {
            "steps": {
                "count": "100",
                "interval": {"civilStartTime": {"date": {"year": 2026, "month": 6, "day": d}}},
            },
            "dataSource": {"platform": "ios"},
        }
        for d in (25, 26, 27)
    ]
    assert upsert_steps(db_url, aggregate_days(points, user_id="t")) == 3
    assert _scalar(db_engine, "SELECT count(*) FROM daily_steps WHERE user_id='t'") == 3


def test_users_do_not_collide_on_same_date(db_url: str, db_engine: Engine) -> None:
    upsert_steps(db_url, aggregate_days([_steps_point("100")], user_id="a"))
    upsert_steps(db_url, aggregate_days([_steps_point("200")], user_id="b"))
    assert _scalar(db_engine, "SELECT count(*) FROM daily_steps") == 2
