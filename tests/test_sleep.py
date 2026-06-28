"""Unit tests for sleep.parse_session — no network or DB required."""

from healthex.sleep import parse_session

SAMPLE_POINT: dict = {
    "interval": {
        "startTime": "2026-06-27T23:00:00+02:00",
        "endTime": "2026-06-28T07:00:00+02:00",
    },
    "civil_date": "2026-06-27",
    "sleepType": "stages",
    "summary": {
        "minutesAsleep": 440,
        "minutesAwake": 40,
        "efficiency": 91.5,
        "stages": {
            "light": 180,
            "deep": 90,
            "rem": 120,
        },
    },
    "dataSource": {"type": "FITBIT"},
}


def test_parse_session_basic() -> None:
    row = parse_session(SAMPLE_POINT, user_id="test_user")

    assert row["user_id"] == "test_user"
    assert row["start_time"] == "2026-06-27T23:00:00+02:00"
    assert row["end_time"] == "2026-06-28T07:00:00+02:00"
    assert row["civil_date"] == "2026-06-27"
    assert row["sleep_type"] == "stages"
    assert row["minutes_asleep"] == 440
    assert row["minutes_awake"] == 40
    assert row["efficiency"] == 91.5
    assert row["minutes_light"] == 180
    assert row["minutes_deep"] == 90
    assert row["minutes_rem"] == 120
    assert row["sleep_score"] is None  # not in sample — matches API reality
    assert row["source_platform"] == "FITBIT"
    assert row["raw"] is SAMPLE_POINT


def test_parse_session_id_is_stable() -> None:
    """Same user + start_time → same ID across calls."""
    row1 = parse_session(SAMPLE_POINT, user_id="u1")
    row2 = parse_session(dict(SAMPLE_POINT), user_id="u1")
    assert row1["id"] == row2["id"]


def test_parse_session_different_users_differ() -> None:
    row1 = parse_session(SAMPLE_POINT, user_id="alice")
    row2 = parse_session(SAMPLE_POINT, user_id="bob")
    assert row1["id"] != row2["id"]


def test_parse_session_missing_fields_are_none() -> None:
    """Minimal point with no summary — all optional fields should be None."""
    minimal: dict = {
        "interval": {
            "startTime": "2026-06-26T22:00:00+00:00",
            "endTime": "2026-06-27T06:00:00+00:00",
        },
    }
    row = parse_session(minimal)
    assert row["civil_date"] is None
    assert row["minutes_asleep"] is None
    assert row["efficiency"] is None
    assert row["sleep_score"] is None
