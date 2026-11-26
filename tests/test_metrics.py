"""flatten() names every daily metric, so its naming rules are the schema."""

from healthex.metrics import daily_rows, flatten


def test_flatten_numbers_int64_strings_and_durations() -> None:
    assert flatten({"kcalSum": 2100.5, "countSum": "9321", "durationSum": "3600s"}) == {
        "kcal_sum": 2100.5,
        "count_sum": 9321.0,
        "duration_sum": 3600.0,
    }


def test_flatten_skips_enums_bools_and_time_members() -> None:
    point = {"date": {"year": 2026}, "estimated": True, "cardioFitnessLevel": "GOOD", "vo2Max": 47}
    assert flatten(point) == {"vo2_max": 47.0}


def test_flatten_keys_list_items_by_their_enum() -> None:
    zones = {
        "timeInHeartRateZones": [
            {"heartRateZone": "PEAK", "duration": "60s"},
            {"heartRateZone": "LIGHT", "duration": "1200s"},
        ]
    }
    assert flatten(zones) == {
        "time_in_heart_rate_zones_peak_duration": 60.0,
        "time_in_heart_rate_zones_light_duration": 1200.0,
    }


def test_unworn_day_yields_no_rows() -> None:
    """A rollup window with no value member means "not worn", not zero."""
    assert daily_rows([{"civilStartTime": {"date": {"year": 2026, "month": 6, "day": 27}}}]) == []


def test_daily_rows_dedupes_a_repeated_day() -> None:
    point = {
        "civilStartTime": {"date": {"year": 2026, "month": 6, "day": 27}},
        "steps": {"countSum": "10"},
    }
    rows = daily_rows([point, point], user_id="u")
    assert rows == [
        {"user_id": "u", "metric_date": "2026-06-27", "metric": "steps.count_sum", "value": 10.0}
    ]
