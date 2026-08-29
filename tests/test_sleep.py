"""Unit tests for sleep.parse_session — no network or DB required."""

import pytest

from healthex.sleep import parse_session

# Mirrors the real Google Health API v4 response shape (confirmed 2026-06-28)
SAMPLE_POINT: dict[str, object] = {
    "name": "users/7426086979915171127/dataTypes/sleep/dataPoints/123",
    "dataSource": {"recordingMethod": "DERIVED", "device": {}, "platform": "FITBIT"},
    "sleep": {
        "interval": {
            "startTime": "2026-06-25T21:32:00Z",
            "startUtcOffset": "7200s",
            "endTime": "2026-06-26T06:14:00Z",
            "endUtcOffset": "7200s",
        },
        "type": "STAGES",
        "summary": {
            "minutesInSleepPeriod": "522",
            "minutesAsleep": "504",
            "minutesAwake": "18",
            "stagesSummary": [
                {"type": "AWAKE", "minutes": "17", "count": "2"},
                {"type": "LIGHT", "minutes": "363", "count": "15"},
                {"type": "DEEP", "minutes": "55", "count": "4"},
                {"type": "REM", "minutes": "86", "count": "10"},
            ],
        },
    },
}


def test_parse_session_basic() -> None:
    row = parse_session(SAMPLE_POINT)

    assert row["user_id"] == "7426086979915171127"
    assert row["start_time"] == "2026-06-25T21:32:00Z"
    assert row["end_time"] == "2026-06-26T06:14:00Z"
    assert row["civil_date"] == "2026-06-25"  # UTC+2 → local 23:32, night of Jun 25
    assert row["sleep_type"] == "STAGES"
    assert row["minutes_asleep"] == 504
    assert row["minutes_awake"] == 18
    assert row["duration_seconds"] == 522 * 60
    assert row["minutes_light"] == 363
    assert row["minutes_deep"] == 55
    assert row["minutes_rem"] == 86
    assert row["efficiency"] == pytest.approx(96.55, abs=0.1)  # 504/522*100
    assert isinstance(row["sleep_score"], int)
    assert 0 <= row["sleep_score"] <= 100
    assert row["source_platform"] == "FITBIT"
    assert row["raw"] is SAMPLE_POINT


def test_parse_session_user_id_override() -> None:
    row = parse_session(SAMPLE_POINT, user_id="custom_user")
    assert row["user_id"] == "custom_user"


def test_parse_session_id_is_stable() -> None:
    row1 = parse_session(SAMPLE_POINT)
    row2 = parse_session(dict(SAMPLE_POINT))
    assert row1["id"] == row2["id"]


def test_parse_session_missing_fields_are_none() -> None:
    minimal: dict[str, object] = {
        "name": "users/123/dataTypes/sleep/dataPoints/456",
        "sleep": {
            "interval": {
                "startTime": "2026-06-26T22:00:00Z",
                "endTime": "2026-06-27T06:00:00Z",
            }
        },
    }
    row = parse_session(minimal)
    assert row["minutes_asleep"] is None
    assert row["efficiency"] is None
    assert row["sleep_score"] is None
    assert row["civil_date"] == "2026-06-26"


STAGED_SESSION: dict[str, object] = {
    "sleep": {
        "interval": {"startTime": "2026-08-28T23:11:00Z", "startUtcOffset": "7200s"},
        "type": "STAGES",
        "summary": {"minutesToFallAsleep": "0", "minutesAsleep": "400"},
        "stages": [
            {"startTime": "2026-08-28T23:11:00Z", "type": "AWAKE"},
            {"startTime": "2026-08-28T23:21:30Z", "type": "LIGHT"},
            {"startTime": "2026-08-28T23:34:30Z", "type": "DEEP"},
        ],
    }
}


def test_latency_is_time_to_first_non_awake_stage() -> None:
    """23:11:00 -> 23:21:30 is 10.5 minutes."""
    row = parse_session(STAGED_SESSION, user_id="t")
    assert row["sleep_latency_minutes"] == 10


def test_latency_ignores_the_zero_api_field_when_stages_exist() -> None:
    """summary.minutesToFallAsleep reports 0 on some devices; stages win."""
    row = parse_session(STAGED_SESSION, user_id="t")
    assert row["sleep_latency_minutes"] != 0


def test_latency_falls_back_to_api_field_without_stages() -> None:
    point: dict[str, object] = {
        "sleep": {
            "interval": {"startTime": "2026-08-28T23:11:00Z"},
            "type": "CLASSIC",
            "summary": {"minutesToFallAsleep": "14"},
        }
    }
    assert parse_session(point, user_id="t")["sleep_latency_minutes"] == 14


def test_latency_is_none_when_api_field_is_zero_and_no_stages() -> None:
    point: dict[str, object] = {
        "sleep": {
            "interval": {"startTime": "2026-08-28T23:11:00Z"},
            "summary": {"minutesToFallAsleep": "0"},
        }
    }
    assert parse_session(point, user_id="t")["sleep_latency_minutes"] is None


def test_latency_is_none_when_every_stage_is_awake() -> None:
    point: dict[str, object] = {
        "sleep": {
            "interval": {"startTime": "2026-08-28T23:11:00Z"},
            "summary": {},
            "stages": [{"startTime": "2026-08-28T23:11:00Z", "type": "AWAKE"}],
        }
    }
    assert parse_session(point, user_id="t")["sleep_latency_minutes"] is None
