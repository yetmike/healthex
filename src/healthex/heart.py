"""Parse Google Health API daily RHR and HRV dataPoints."""

from __future__ import annotations

import hashlib
from typing import Any


def parse_rhr(point: dict[str, Any], user_id: str = "me") -> dict[str, Any] | None:
    """
    Parse a daily-resting-heart-rate dataPoint.

    API shape (confirmed 2026-06-28):
      point.dailyRestingHeartRate.date           {year, month, day}
      point.dailyRestingHeartRate.beatsPerMinute  string
      point.dailyRestingHeartRate.dailyRestingHeartRateMetadata.calculationMethod
      point.dataSource.platform
    """
    data: dict[str, Any] = point.get("dailyRestingHeartRate", {})
    date_str = _date(data.get("date"))
    if not date_str:
        return None

    raw_bpm = data.get("beatsPerMinute")
    if raw_bpm is None:
        return None

    meta: dict[str, Any] = data.get("dailyRestingHeartRateMetadata", {})
    ds: Any = point.get("dataSource", {})
    source_platform = ds.get("platform") or ds.get("recordingMethod") if isinstance(ds, dict) else None

    return {
        "id": hashlib.sha256(f"{user_id}|rhr|{date_str}".encode()).hexdigest()[:32],
        "user_id": user_id,
        "rhr_date": date_str,
        "bpm": int(raw_bpm),
        "calculation_method": meta.get("calculationMethod"),
        "source_platform": source_platform,
        "raw": point,
    }


def parse_hrv(point: dict[str, Any], user_id: str = "me") -> dict[str, Any] | None:
    """
    Parse a daily-heart-rate-variability dataPoint.

    API shape (confirmed 2026-06-28):
      point.dailyHeartRateVariability.date                                         {year, month, day}
      point.dailyHeartRateVariability.averageHeartRateVariabilityMilliseconds       float
      point.dailyHeartRateVariability.nonRemHeartRateBeatsPerMinute                 string (nullable)
      point.dailyHeartRateVariability.entropy                                       float (nullable)
      point.dailyHeartRateVariability.deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds float (nullable)
    """
    data: dict[str, Any] = point.get("dailyHeartRateVariability", {})
    date_str = _date(data.get("date"))
    if not date_str:
        return None

    avg_hrv = data.get("averageHeartRateVariabilityMilliseconds")
    if avg_hrv is None:
        return None

    ds: Any = point.get("dataSource", {})
    source_platform = ds.get("platform") or ds.get("recordingMethod") if isinstance(ds, dict) else None

    non_rem_raw = data.get("nonRemHeartRateBeatsPerMinute")

    return {
        "id": hashlib.sha256(f"{user_id}|hrv|{date_str}".encode()).hexdigest()[:32],
        "user_id": user_id,
        "hrv_date": date_str,
        "avg_hrv_ms": float(avg_hrv),
        "non_rem_bpm": int(non_rem_raw) if non_rem_raw is not None else None,
        "entropy": float(data["entropy"]) if data.get("entropy") is not None else None,
        "deep_sleep_rmssd_ms": float(data["deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds"])
            if data.get("deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds") is not None else None,
        "source_platform": source_platform,
        "raw": point,
    }


def _date(d: Any) -> str | None:
    if not isinstance(d, dict):
        return None
    try:
        return f"{d['year']:04d}-{d['month']:02d}-{d['day']:02d}"
    except (KeyError, TypeError):
        return None
