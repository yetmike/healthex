"""Tests for steps.aggregate_days — source de-duplication and daily rollup."""

from typing import Any

from healthex.steps import aggregate_days


def _point(
    year: int,
    month: int,
    day: int,
    count: str | int,
    form_factor: str | None,
    platform: str = "ios",
) -> dict[str, Any]:
    ds: dict[str, Any] = {"platform": platform}
    if form_factor is not None:
        ds["device"] = {"formFactor": form_factor}
    return {
        "steps": {
            "count": count,
            "interval": {"civilStartTime": {"date": {"year": year, "month": month, "day": day}}},
        },
        "dataSource": ds,
    }


def test_sums_counts_within_one_source() -> None:
    rows = aggregate_days([_point(2026, 6, 27, 100, None), _point(2026, 6, 27, 250, None)])
    assert len(rows) == 1
    assert rows[0]["steps"] == 350
    assert rows[0]["step_date"] == "2026-06-27"


def test_healthkit_aggregate_wins_over_devices() -> None:
    """None (HealthKit) outranks WATCH and PHONE, so device totals are discarded."""
    rows = aggregate_days(
        [
            _point(2026, 6, 27, 1000, None),
            _point(2026, 6, 27, 9999, "WATCH"),
            _point(2026, 6, 27, 8888, "PHONE"),
        ]
    )
    assert len(rows) == 1
    assert rows[0]["steps"] == 1000


def test_watch_wins_over_phone_when_no_aggregate() -> None:
    rows = aggregate_days([_point(2026, 6, 27, 700, "PHONE"), _point(2026, 6, 27, 500, "WATCH")])
    assert rows[0]["steps"] == 500


def test_unknown_form_factor_loses_to_known_ones() -> None:
    rows = aggregate_days([_point(2026, 6, 27, 42, "TREADMILL"), _point(2026, 6, 27, 900, "PHONE")])
    assert rows[0]["steps"] == 900


def test_splits_by_civil_date() -> None:
    rows = aggregate_days([_point(2026, 6, 27, 100, None), _point(2026, 6, 28, 200, None)])
    assert {r["step_date"]: r["steps"] for r in rows} == {"2026-06-27": 100, "2026-06-28": 200}


def test_string_counts_are_coerced_to_int() -> None:
    """The API returns int64 fields as JSON strings."""
    rows = aggregate_days([_point(2026, 6, 27, "1234", None)])
    assert rows[0]["steps"] == 1234
    assert isinstance(rows[0]["steps"], int)


def test_missing_count_treated_as_zero() -> None:
    point = _point(2026, 6, 27, 0, None)
    del point["steps"]["count"]
    assert aggregate_days([point])[0]["steps"] == 0


def test_points_without_a_date_are_skipped() -> None:
    bad: dict[str, Any] = {"steps": {"count": "500"}, "dataSource": {}}
    assert aggregate_days([bad]) == []
    assert aggregate_days([bad, _point(2026, 6, 27, 10, None)])[0]["steps"] == 10


def test_empty_input() -> None:
    assert aggregate_days([]) == []


def test_id_is_stable_and_scoped_to_user() -> None:
    a = aggregate_days([_point(2026, 6, 27, 100, None)], user_id="mike")[0]["id"]
    b = aggregate_days([_point(2026, 6, 27, 999, None)], user_id="mike")[0]["id"]
    c = aggregate_days([_point(2026, 6, 27, 100, None)], user_id="other")[0]["id"]
    assert a == b  # same user+date -> same id, so re-ingest upserts
    assert a != c
    assert len(a) == 32


def test_date_is_zero_padded() -> None:
    assert aggregate_days([_point(2026, 1, 5, 10, None)])[0]["step_date"] == "2026-01-05"
