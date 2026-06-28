"""Parse and aggregate Google Health API steps dataPoints into daily rows."""

from __future__ import annotations

import hashlib
from typing import Any

# Priority order: lower index = higher priority (prefer aggregate HealthKit over device-specific)
_FORM_FACTOR_PRIORITY = {None: 0, "WATCH": 1, "PHONE": 2}


def aggregate_days(points: list[dict[str, Any]], user_id: str = "me") -> list[dict[str, Any]]:
    """
    Aggregate raw steps dataPoints (one per short interval) into one row per civil date.

    Real API shape (confirmed 2026-06-28):
      point.steps.count                          string, e.g. "25"
      point.steps.interval.civilStartTime.date   {year, month, day}
      point.dataSource.device.formFactor         "PHONE" | "WATCH" | absent (HealthKit aggregate)
      point.dataSource.recordingMethod           "PASSIVELY_MEASURED" etc.

    The API returns many sub-minute intervals per day from multiple sources
    (HealthKit aggregate, iPhone, Apple Watch) which overlap and double-count.
    Strategy: for each day, keep only the highest-priority source class.
      None (HealthKit aggregate) > WATCH > PHONE
    """
    # Group by (civil_date, form_factor)
    by_date_source: dict[str, dict[Any, dict[str, Any]]] = {}

    for point in points:
        steps_data: dict[str, Any] = point.get("steps", {})
        raw_count = steps_data.get("count")
        count = int(raw_count) if raw_count is not None else 0

        civil_date = _civil_date(steps_data)
        if civil_date is None:
            continue

        ds: Any = point.get("dataSource", {})
        form_factor = ds.get("device", {}).get("formFactor") if isinstance(ds, dict) else None
        source_platform = ds.get("platform") or ds.get("recordingMethod") if isinstance(ds, dict) else None

        if civil_date not in by_date_source:
            by_date_source[civil_date] = {}
        if form_factor not in by_date_source[civil_date]:
            by_date_source[civil_date][form_factor] = {"steps": 0, "source_platform": source_platform, "raw_sample": point}
        by_date_source[civil_date][form_factor]["steps"] += count

    rows = []
    for civil_date, sources in by_date_source.items():
        # Pick the highest-priority source available for this day
        best_ff = min(sources.keys(), key=lambda ff: _FORM_FACTOR_PRIORITY.get(ff, 99))
        data = sources[best_ff]

        row_id = hashlib.sha256(f"{user_id}|{civil_date}".encode()).hexdigest()[:32]
        rows.append({
            "id": row_id,
            "user_id": user_id,
            "step_date": civil_date,
            "steps": data["steps"],
            "source_platform": data["source_platform"],
            "raw": data["raw_sample"],
        })

    return rows


def _civil_date(steps_data: dict[str, Any]) -> str | None:
    try:
        d = steps_data["interval"]["civilStartTime"]["date"]
        return f"{d['year']:04d}-{d['month']:02d}-{d['day']:02d}"
    except (KeyError, TypeError):
        return None
