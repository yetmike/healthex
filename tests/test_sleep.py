"""Unit tests for sleep.parse_session — no network or DB required."""

from healthex.sleep import parse_session

# Mirrors the real Google Health API v4 response shape (confirmed 2026-06-28)
SAMPLE_POINT: dict = {
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
    assert row["efficiency"] is None
    assert row["sleep_score"] is None
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
    minimal: dict = {
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
    assert row["civil_date"] == "2026-06-26"  # no offset → UTC, date is Jun 26
