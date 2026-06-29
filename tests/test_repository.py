"""Integration tests for repository.upsert_sleep — requires a real Postgres connection.

Set DATABASE_URL env var (or use the default docker-compose one) before running.
These tests are intentionally separate from the mocked tests so CI can skip them
when no DB is available, but they run in the main CI service (see ci.yml).
"""

import pytest
from sqlalchemy import Engine

from healthex.repository import upsert_sleep
from healthex.sleep import parse_session

SAMPLE_POINT: dict[str, object] = {
    "name": "users/test/dataTypes/sleep/dataPoints/abc123",
    "sleep": {
        "interval": {
            "startTime": "2026-06-27T21:00:00Z",
            "endTime": "2026-06-28T05:00:00Z",
            "startUtcOffset": "7200s",
        },
        "type": "STAGES",
        "summary": {
            "minutesAsleep": "440",
            "minutesAwake": "40",
            "minutesInSleepPeriod": "480",
            "stagesSummary": [
                {"type": "LIGHT", "minutes": "200", "count": "5"},
                {"type": "DEEP", "minutes": "100", "count": "3"},
                {"type": "REM", "minutes": "140", "count": "4"},
                {"type": "AWAKE", "minutes": "40", "count": "6"},
            ],
        },
    },
}


@pytest.mark.usefixtures("clean_db")
def test_upsert_inserts_row(db_engine: Engine) -> None:
    import os

    db_url = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://healthex:healthex@localhost:5432/healthex"
    )
    rows = [parse_session(SAMPLE_POINT, user_id="test")]
    n = upsert_sleep(db_url, rows)
    assert n == 1


@pytest.mark.usefixtures("clean_db")
def test_upsert_is_idempotent(db_engine: Engine) -> None:
    """Running the same upsert twice must not duplicate rows."""
    import os

    from sqlalchemy import text

    db_url = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://healthex:healthex@localhost:5432/healthex"
    )
    rows = [parse_session(SAMPLE_POINT, user_id="test")]
    upsert_sleep(db_url, rows)
    upsert_sleep(db_url, rows)  # second run

    with db_engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM sleep_sessions WHERE user_id = 'test'")
        ).scalar()
    assert count == 1
