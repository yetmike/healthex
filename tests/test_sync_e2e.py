"""End-to-end sync test: real httpx, real parsers, real SQLAlchemy, real Postgres.

Only the OAuth handshake is stubbed. Everything else runs for real, so a
dependency bump that changes httpx request handling, JSON decoding, SQLAlchemy
upsert behaviour or Typer argument parsing fails here rather than in production.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx
from sqlalchemy import Engine, text
from typer.testing import CliRunner

from healthex.cli import app
from healthex.client import BASE
from healthex.config import settings

runner = CliRunner()
pytestmark = pytest.mark.usefixtures("clean_db")

SLEEP_POINT: dict[str, Any] = {
    "name": "users/me/dataTypes/sleep/dataPoints/abc",
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

STEPS_POINT: dict[str, Any] = {
    "steps": {
        "count": "9321",
        "interval": {
            "startTime": "2026-06-27T08:00:00Z",
            "civilStartTime": {"date": {"year": 2026, "month": 6, "day": 27}},
        },
    },
    "dataSource": {"platform": "ios"},
}

RHR_POINT: dict[str, Any] = {
    "dailyRestingHeartRate": {
        "date": {"year": 2026, "month": 6, "day": 27},
        "beatsPerMinute": "52",
        "dailyRestingHeartRateMetadata": {"calculationMethod": "SLEEP_BASED"},
    },
    "dataSource": {"platform": "ios"},
}

HRV_POINT: dict[str, Any] = {
    "dailyHeartRateVariability": {
        "date": {"year": 2026, "month": 6, "day": 27},
        "averageHeartRateVariabilityMilliseconds": "44.5",
        "nonRemHeartRateBeatsPerMinute": "50",
        "entropy": "0.91",
    },
    "dataSource": {"platform": "ios"},
}

SPO2_POINT: dict[str, Any] = {
    "dailyOxygenSaturation": {
        "date": {"year": 2026, "month": 6, "day": 27},
        "averagePercentage": 96.5,
        "lowerBoundPercentage": 93.0,
    },
}

EXERCISE_POINT: dict[str, Any] = {
    "exercise": {
        "interval": {
            "startTime": "2026-06-27T08:00:00Z",
            "endTime": "2026-06-27T08:35:00Z",
            "civilStartTime": {"date": {"year": 2026, "month": 6, "day": 27}},
        },
        "exerciseType": "RUNNING",
        "displayName": "Run",
        "activeDuration": "1800s",
        "metricsSummary": {
            "caloriesKcal": 380,
            "distanceMillimeters": 5000000,
            "steps": "6200",
            "averageHeartRateBeatsPerMinute": "148",
        },
    },
}

DISTANCE_ROLLUP: dict[str, Any] = {
    "civilStartTime": {"date": {"year": 2026, "month": 6, "day": 27}, "time": {}},
    "civilEndTime": {"date": {"year": 2026, "month": 6, "day": 28}, "time": {}},
    "distance": {"millimetersSum": "7400000"},
}

HR_BUCKET: dict[str, Any] = {
    "startTime": "2026-06-27T08:00:00Z",
    "endTime": "2026-06-27T08:05:00Z",
    "heartRate": {"beatsPerMinuteAvg": 141.2, "beatsPerMinuteMin": 120, "beatsPerMinuteMax": 160},
}


def _route_api(
    sleep: list[dict[str, Any]] | None = None,
    steps: list[dict[str, Any]] | None = None,
    rhr: list[dict[str, Any]] | None = None,
    hrv: list[dict[str, Any]] | None = None,
) -> None:
    def ok(points: list[dict[str, Any]] | None) -> httpx.Response:
        return httpx.Response(200, json={"dataPoints": points or []})

    respx.get(f"{BASE}/users/me/dataTypes/sleep/dataPoints").mock(return_value=ok(sleep))
    respx.get(f"{BASE}/users/me/dataTypes/steps/dataPoints").mock(return_value=ok(steps))
    respx.get(f"{BASE}/users/me/dataTypes/daily-resting-heart-rate/dataPoints").mock(
        return_value=ok(rhr)
    )
    respx.get(f"{BASE}/users/me/dataTypes/daily-heart-rate-variability/dataPoints").mock(
        return_value=ok(hrv)
    )
    # Everything else sync asks for: one point for the types under test, and an
    # empty answer for the rest. Registered last, so the routes above win.
    types = f"{BASE}/users/me/dataTypes"
    respx.get(f"{types}/daily-oxygen-saturation/dataPoints").mock(return_value=ok([SPO2_POINT]))
    respx.get(f"{types}/exercise/dataPoints").mock(return_value=ok([EXERCISE_POINT]))
    respx.get(url__regex=rf"{types}/[a-z0-9-]+/dataPoints(\\?.*)?$").mock(return_value=ok([]))

    def rollups(*points: dict[str, Any]) -> httpx.Response:
        return httpx.Response(200, json={"rollupDataPoints": list(points)})

    respx.post(f"{types}/distance/dataPoints:dailyRollUp").mock(
        return_value=rollups(DISTANCE_ROLLUP)
    )
    respx.post(f"{types}/heart-rate/dataPoints:rollUp").mock(return_value=rollups(HR_BUCKET))
    respx.post(url__regex=rf"{types}/[a-z0-9-]+/dataPoints:(dailyRollUp|rollUp)$").mock(
        return_value=rollups()
    )


def _fake_creds() -> MagicMock:
    creds = MagicMock()
    creds.token = "fake-access-token"
    creds.valid = True
    return creds


def _counts(engine: Engine) -> dict[str, Any]:
    with engine.connect() as conn:
        return {
            t: conn.execute(text(f"SELECT count(*) FROM {t} WHERE user_id='e2e'")).scalar()
            for t in ("sleep_sessions", "daily_steps", "daily_rhr", "daily_hrv")
        }


@respx.mock
def test_sync_writes_every_data_type_to_postgres(
    db_url: str, db_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", db_url)
    _route_api(sleep=[SLEEP_POINT], steps=[STEPS_POINT], rhr=[RHR_POINT], hrv=[HRV_POINT])

    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        result = runner.invoke(app, ["sync", "--since", "2026-06-01T00:00:00", "--user-id", "e2e"])

    assert result.exit_code == 0, result.output
    assert _counts(db_engine) == {
        "sleep_sessions": 1,
        "daily_steps": 1,
        "daily_rhr": 1,
        "daily_hrv": 1,
    }

    with db_engine.connect() as conn:
        assert (
            conn.execute(text("SELECT steps FROM daily_steps WHERE user_id='e2e'")).scalar() == 9321
        )
        metric_rows = conn.execute(
            text("SELECT metric, value FROM daily_metrics WHERE user_id='e2e' ORDER BY 1")
        ).all()
        assert [tuple(r) for r in metric_rows] == [
            ("daily_oxygen_saturation.average_percentage", 96.5),
            ("daily_oxygen_saturation.lower_bound_percentage", 93.0),
            ("distance.millimeters_sum", 7400000.0),
        ]
        run = conn.execute(
            text("SELECT exercise_type, active_seconds, distance_m, avg_bpm FROM exercises")
        ).one()
        assert tuple(run) == ("RUNNING", 1800.0, 5000.0, 148)
        assert conn.execute(text("SELECT bpm_avg FROM heart_rate")).scalar() == 141.2
        assert conn.execute(text("SELECT bpm FROM daily_rhr WHERE user_id='e2e'")).scalar() == 52


@respx.mock
def test_sync_sends_the_bearer_token(db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """A httpx bump must not drop or mangle the Authorization header."""
    monkeypatch.setattr(settings, "database_url", db_url)
    route = respx.get(f"{BASE}/users/me/dataTypes/sleep/dataPoints").mock(
        return_value=httpx.Response(200, json={"dataPoints": []})
    )
    _route_api()

    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        runner.invoke(app, ["sync", "--since", "2026-06-01T00:00:00", "--user-id", "e2e"])

    assert route.call_count == 1
    assert route.calls[0].request.headers["Authorization"] == "Bearer fake-access-token"


@respx.mock
def test_sync_is_idempotent_end_to_end(
    db_url: str, db_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running sync twice over the same window must not duplicate any row."""
    monkeypatch.setattr(settings, "database_url", db_url)
    _route_api(sleep=[SLEEP_POINT], steps=[STEPS_POINT], rhr=[RHR_POINT], hrv=[HRV_POINT])

    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        for _ in range(2):
            result = runner.invoke(
                app, ["sync", "--since", "2026-06-01T00:00:00", "--user-id", "e2e"]
            )
            assert result.exit_code == 0, result.output

    assert _counts(db_engine) == {
        "sleep_sessions": 1,
        "daily_steps": 1,
        "daily_rhr": 1,
        "daily_hrv": 1,
    }


@respx.mock
def test_sync_survives_partial_api_outage(
    db_url: str, db_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Steps/RHR/HRV failures still commit sleep, but the run reports failure."""
    monkeypatch.setattr(settings, "database_url", db_url)
    respx.get(f"{BASE}/users/me/dataTypes/sleep/dataPoints").mock(
        return_value=httpx.Response(200, json={"dataPoints": [SLEEP_POINT]})
    )
    for dt_name in ("steps", "daily-resting-heart-rate", "daily-heart-rate-variability"):
        respx.get(f"{BASE}/users/me/dataTypes/{dt_name}/dataPoints").mock(
            return_value=httpx.Response(503, json={"error": "unavailable"})
        )

    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        result = runner.invoke(app, ["sync", "--since", "2026-06-01T00:00:00", "--user-id", "e2e"])

    assert result.exit_code == 1, result.output  # degraded run must be visible
    counts = _counts(db_engine)
    assert counts["sleep_sessions"] == 1  # what worked is still committed
    assert counts["daily_steps"] == 0


@respx.mock
def test_sync_days_option_computes_window(db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "database_url", db_url)
    _route_api()

    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        result = runner.invoke(app, ["sync", "--days", "7", "--user-id", "e2e"])

    assert result.exit_code == 0, result.output


def test_sync_rejects_since_and_days_together(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        result = runner.invoke(app, ["sync", "--since", "2026-06-01T00:00:00", "--days", "7"])
    assert result.exit_code != 0


@respx.mock
def test_partial_failure_exits_non_zero(db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """A scheduler must be able to tell a degraded run from a clean one."""
    monkeypatch.setattr(settings, "database_url", db_url)
    respx.get(f"{BASE}/users/me/dataTypes/sleep/dataPoints").mock(
        return_value=httpx.Response(200, json={"dataPoints": [SLEEP_POINT]})
    )
    for dt_name in ("steps", "daily-resting-heart-rate", "daily-heart-rate-variability"):
        respx.get(f"{BASE}/users/me/dataTypes/{dt_name}/dataPoints").mock(
            return_value=httpx.Response(503, json={"error": "unavailable"})
        )

    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        result = runner.invoke(app, ["sync", "--since", "2026-06-01T00:00:00", "--user-id", "e2e"])

    assert result.exit_code == 1
    assert "PARTIAL" in result.output
    assert "steps" in result.output


@respx.mock
def test_clean_run_exits_zero_with_summary(db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "database_url", db_url)
    _route_api(sleep=[SLEEP_POINT], steps=[STEPS_POINT], rhr=[RHR_POINT], hrv=[HRV_POINT])

    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        result = runner.invoke(app, ["sync", "--since", "2026-06-01T00:00:00", "--user-id", "e2e"])

    assert result.exit_code == 0
    assert "sync complete: sleep=1 steps=1 rhr=1 hrv=1" in result.output
    assert "PARTIAL" not in result.output


@respx.mock
def test_empty_api_response_is_not_a_failure(db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """A genuinely quiet day must exit 0, distinct from a fetch that failed."""
    monkeypatch.setattr(settings, "database_url", db_url)
    _route_api()

    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        result = runner.invoke(app, ["sync", "--since", "2026-06-01T00:00:00", "--user-id", "e2e"])

    assert result.exit_code == 0
    assert "sync complete: sleep=0 steps=0 rhr=0 hrv=0" in result.output
    assert "No steps data returned" in result.output


@respx.mock
def test_total_outage_exits_non_zero(db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Previously sleep failing raised an uncaught exception mid-run."""
    monkeypatch.setattr(settings, "database_url", db_url)
    for dt_name in ("sleep", "steps", "daily-resting-heart-rate", "daily-heart-rate-variability"):
        respx.get(f"{BASE}/users/me/dataTypes/{dt_name}/dataPoints").mock(
            return_value=httpx.Response(500, json={"error": "boom"})
        )

    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        result = runner.invoke(app, ["sync", "--since", "2026-06-01T00:00:00", "--user-id", "e2e"])

    assert result.exit_code == 1
    assert "sleep" in result.output


@respx.mock
def test_sync_creates_the_schema_on_a_fresh_database(
    db_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sync against an empty database must not fail on missing tables."""
    from sqlalchemy import create_engine, text

    from healthex.db import make_engine

    admin = create_engine(db_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text('DROP DATABASE IF EXISTS "sync_fresh"'))
        conn.execute(text('CREATE DATABASE "sync_fresh"'))
    fresh = db_url.rsplit("/", 1)[0] + "/sync_fresh"

    monkeypatch.setattr(settings, "database_url", fresh)
    _route_api(sleep=[SLEEP_POINT])

    with patch("healthex.cli.auth.get_credentials", return_value=_fake_creds()):
        result = runner.invoke(app, ["sync", "--since", "2026-06-01T00:00:00", "--user-id", "e2e"])

    assert result.exit_code == 0, result.output
    assert "Applied 001_init.sql" in result.output
    assert "sleep=1" in result.output

    make_engine(fresh).dispose()
    make_engine.cache_clear()
    with admin.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
                " WHERE datname = 'sync_fresh' AND pid <> pg_backend_pid()"
            )
        )
        conn.execute(text('DROP DATABASE IF EXISTS "sync_fresh"'))
    admin.dispose()
