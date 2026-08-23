"""Tests for heart.parse_rhr / parse_hrv — field extraction and numeric coercion."""

from typing import Any

from healthex.heart import parse_hrv, parse_rhr

RHR_POINT: dict[str, Any] = {
    "dailyRestingHeartRate": {
        "date": {"year": 2026, "month": 6, "day": 27},
        "beatsPerMinute": "54",
        "dailyRestingHeartRateMetadata": {"calculationMethod": "SLEEP_BASED"},
    },
    "dataSource": {"platform": "ios"},
}

HRV_POINT: dict[str, Any] = {
    "dailyHeartRateVariability": {
        "date": {"year": 2026, "month": 6, "day": 27},
        "averageHeartRateVariabilityMilliseconds": "42.5",
        "nonRemHeartRateBeatsPerMinute": "51",
        "entropy": "0.87",
        "deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds": "38.25",
    },
    "dataSource": {"platform": "ios"},
}


def test_parse_rhr_extracts_fields() -> None:
    row = parse_rhr(RHR_POINT, user_id="mike")
    assert row is not None
    assert row["rhr_date"] == "2026-06-27"
    assert row["bpm"] == 54
    assert isinstance(row["bpm"], int)
    assert row["calculation_method"] == "SLEEP_BASED"
    assert row["source_platform"] == "ios"
    assert row["raw"] == RHR_POINT


def test_parse_rhr_requires_date_and_bpm() -> None:
    assert parse_rhr({"dailyRestingHeartRate": {"beatsPerMinute": "54"}}) is None
    assert (
        parse_rhr({"dailyRestingHeartRate": {"date": {"year": 2026, "month": 6, "day": 27}}})
        is None
    )
    assert parse_rhr({}) is None


def test_parse_rhr_tolerates_missing_metadata() -> None:
    point: dict[str, Any] = {
        "dailyRestingHeartRate": {
            "date": {"year": 2026, "month": 6, "day": 27},
            "beatsPerMinute": 60,
        }
    }
    row = parse_rhr(point)
    assert row is not None
    assert row["calculation_method"] is None
    assert row["source_platform"] is None


def test_parse_rhr_falls_back_to_recording_method() -> None:
    point = {**RHR_POINT, "dataSource": {"recordingMethod": "AUTOMATIC"}}
    row = parse_rhr(point)
    assert row is not None and row["source_platform"] == "AUTOMATIC"


def test_parse_hrv_extracts_and_coerces() -> None:
    row = parse_hrv(HRV_POINT, user_id="mike")
    assert row is not None
    assert row["hrv_date"] == "2026-06-27"
    assert row["avg_hrv_ms"] == 42.5
    assert row["non_rem_bpm"] == 51
    assert row["entropy"] == 0.87
    assert row["deep_sleep_rmssd_ms"] == 38.25


def test_parse_hrv_optional_fields_default_to_none() -> None:
    point: dict[str, Any] = {
        "dailyHeartRateVariability": {
            "date": {"year": 2026, "month": 6, "day": 27},
            "averageHeartRateVariabilityMilliseconds": "30",
        }
    }
    row = parse_hrv(point)
    assert row is not None
    assert row["non_rem_bpm"] is None
    assert row["entropy"] is None
    assert row["deep_sleep_rmssd_ms"] is None


def test_parse_hrv_requires_date_and_average() -> None:
    assert (
        parse_hrv({"dailyHeartRateVariability": {"date": {"year": 2026, "month": 6, "day": 27}}})
        is None
    )
    assert parse_hrv({}) is None


def test_malformed_date_returns_none() -> None:
    assert (
        parse_rhr({"dailyRestingHeartRate": {"date": "2026-06-27", "beatsPerMinute": 50}}) is None
    )
    assert (
        parse_hrv(
            {
                "dailyHeartRateVariability": {
                    "date": {"year": 2026},
                    "averageHeartRateVariabilityMilliseconds": 30,
                }
            }
        )
        is None
    )


def test_rhr_and_hrv_ids_do_not_collide() -> None:
    """Same user and date, different metric -> different primary keys."""
    rhr = parse_rhr(RHR_POINT, user_id="mike")
    hrv = parse_hrv(HRV_POINT, user_id="mike")
    assert rhr is not None and hrv is not None
    assert rhr["id"] != hrv["id"]
    assert len(rhr["id"]) == 32 and len(hrv["id"]) == 32
