"""Turn Google Health dataPoints into rows for daily_metrics, heart_rate, exercises.

Daily values are stored long-format and named mechanically from the API's own
field names ("distance.millimeters_sum", "daily_oxygen_saturation.average_percentage"),
so adding a data type is one entry in the tables below - no parser, no migration.
"""

from __future__ import annotations

import re
from typing import Any

# data type -> max days per dailyRollUp request (API limit: 90, or 14 for some).
DAILY_ROLLUPS: dict[str, int] = {
    "distance": 90,
    "floors": 90,
    "altitude": 90,
    "active-energy-burned": 90,
    "total-calories": 14,
    "heart-rate": 14,
    "active-minutes": 14,
    "active-zone-minutes": 90,
    "time-in-heart-rate-zone": 90,
    "sedentary-period": 90,
    "weight": 90,
    "body-fat": 90,
}

# Daily types the API only lists (no rollup); already one point per day.
DAILY_LISTS: tuple[str, ...] = (
    "daily-oxygen-saturation",
    "daily-respiratory-rate",
    "daily-sleep-temperature-derivations",
    "daily-vo2-max",
)

_TIME_KEYS = {"date", "interval", "sampleTime", "civilStartTime", "civilEndTime"}
_NUMBER = re.compile(r"-?\d+(\.\d+)?s?")  # int64s arrive as "123", durations as "60s"


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name.replace("-", "_")).lower()


def flatten(value: Any, prefix: str = "") -> dict[str, float]:
    """Every numeric leaf of *value*, keyed by its snake_case path.

    A list of {<enum>: "PEAK", <number>: ...} items (zones, activity levels) is
    keyed by the enum: {"peak_duration": 60.0}.
    """
    if isinstance(value, bool):
        return {}
    if isinstance(value, int | float):
        return {prefix: float(value)}
    if isinstance(value, str):
        return {prefix: float(value.rstrip("s"))} if _NUMBER.fullmatch(value) else {}
    join = f"{prefix}_" if prefix else ""
    out: dict[str, float] = {}
    if isinstance(value, dict):
        for k, v in value.items():
            if k not in _TIME_KEYS:
                out |= flatten(v, join + _snake(k))
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            label = next(
                (v for v in item.values() if isinstance(v, str) and not _NUMBER.fullmatch(v)), ""
            )
            for k, v in flatten(item).items():
                out[f"{join}{label.lower()}_{k}" if label else join + k] = v
    return out


def _date(d: Any) -> str | None:
    try:
        return f"{d['year']:04d}-{d['month']:02d}-{d['day']:02d}"
    except (KeyError, TypeError):
        return None


def _field(point: dict[str, Any]) -> tuple[str, Any]:
    """The one type-specific member of a dataPoint, e.g. ("heartRate", {...})."""
    skip = {"name", "dataSource", "startTime", "endTime", "civilStartTime", "civilEndTime"}
    return next(((k, v) for k, v in point.items() if k not in skip), ("", {}))


def daily_rows(points: list[dict[str, Any]], user_id: str = "me") -> list[dict[str, Any]]:
    """daily_metrics rows from dailyRollUp points or daily-* list points.

    A day the device was not worn has no value member and yields no rows.
    """
    rows: dict[tuple[str, str], dict[str, Any]] = {}  # keyed: a re-sent day must not duplicate
    for point in points:
        field, value = _field(point)
        day = _date(point.get("civilStartTime", {}).get("date")) or (
            _date(value.get("date")) if isinstance(value, dict) else None
        )
        if not day:
            continue
        for name, number in flatten(value).items():
            metric = f"{_snake(field)}.{name}"
            rows[(day, metric)] = {
                "user_id": user_id,
                "metric_date": day,
                "metric": metric,
                "value": number,
            }
    return list(rows.values())


def heart_rate_rows(points: list[dict[str, Any]], user_id: str = "me") -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for point in points:
        hr = point.get("heartRate") or {}
        if point.get("startTime") and hr.get("beatsPerMinuteAvg") is not None:
            rows[point["startTime"]] = {
                "user_id": user_id,
                "bucket_start": point["startTime"],
                "bpm_avg": float(hr["beatsPerMinuteAvg"]),
                "bpm_min": _num(hr.get("beatsPerMinuteMin")),
                "bpm_max": _num(hr.get("beatsPerMinuteMax")),
            }
    return list(rows.values())


def exercise_rows(points: list[dict[str, Any]], user_id: str = "me") -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for point in points:
        ex: dict[str, Any] = point.get("exercise", {})
        interval: dict[str, Any] = ex.get("interval", {})
        start = interval.get("startTime")
        if not start:
            continue
        m: dict[str, Any] = ex.get("metricsSummary", {})
        rows[start] = {
            "user_id": user_id,
            "start_time": start,
            "end_time": interval.get("endTime"),
            "civil_date": _date(interval.get("civilStartTime", {}).get("date")),
            "exercise_type": ex.get("exerciseType"),
            "display_name": ex.get("displayName"),
            "active_seconds": _num(ex.get("activeDuration")),
            "calories_kcal": _num(m.get("caloriesKcal")),
            "distance_m": _scaled(m.get("distanceMillimeters")),
            "steps": _int(m.get("steps")),
            "avg_bpm": _int(m.get("averageHeartRateBeatsPerMinute")),
            "active_zone_minutes": _int(m.get("activeZoneMinutes")),
            "elevation_gain_m": _scaled(m.get("elevationGainMillimeters")),
            "raw": point,
        }
    return list(rows.values())


def _num(v: Any) -> float | None:
    return None if v is None else float(str(v).rstrip("s"))


def _int(v: Any) -> int | None:
    return None if v is None else int(float(v))


def _scaled(mm: Any) -> float | None:
    return None if mm is None else float(mm) / 1000
