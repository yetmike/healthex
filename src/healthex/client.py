import httpx

BASE = "https://health.googleapis.com/v4"

# The API caps pageSize at 10000; the defaults (1440, or 25 for sleep) mean
# many more round trips than necessary.
_PAGE_SIZE = "10000"


def _rfc3339(since_iso: str) -> str:
    """The filter grammar wants an explicit zone; --since is naive local ISO."""
    return since_iso if since_iso.endswith("Z") or "+" in since_iso[10:] else f"{since_iso}Z"


class HealthClient:
    """Thin wrapper around the Google Health REST API."""

    def __init__(self, access_token: str) -> None:
        self._c = httpx.Client(
            base_url=BASE,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=30.0,
        )

    def list_steps(self, since_iso: str) -> list[dict[str, object]]:
        points: list[dict[str, object]] = []
        params: dict[str, str] = {
            "pageSize": _PAGE_SIZE,
            "filter": f'steps.interval.start_time >= "{_rfc3339(since_iso)}"',
        }
        while True:
            r = self._c.get("/users/me/dataTypes/steps/dataPoints", params=params)
            r.raise_for_status()
            body = r.json()
            for p in body.get("dataPoints", []):
                start = str(p.get("steps", {}).get("interval", {}).get("startTime", ""))
                if start >= since_iso:
                    points.append(p)
            token = body.get("nextPageToken")
            if not token:
                return points
            params["pageToken"] = str(token)

    def list_daily(self, data_type: str, since_iso: str | None = None) -> list[dict[str, object]]:
        points: list[dict[str, object]] = []
        params: dict[str, str] = {"pageSize": _PAGE_SIZE}
        if since_iso is not None:
            # daily-resting-heart-rate -> daily_resting_heart_rate.date
            member = data_type.replace("-", "_")
            params["filter"] = f'{member}.date >= "{since_iso[:10]}"'

        while True:
            r = self._c.get(f"/users/me/dataTypes/{data_type}/dataPoints", params=params)
            r.raise_for_status()
            body = r.json()
            points.extend(body.get("dataPoints", []))
            token = body.get("nextPageToken")
            if not token:
                return points
            params["pageToken"] = str(token)

    def list_sleep(self, since_iso: str) -> list[dict[str, object]]:
        points: list[dict[str, object]] = []
        # Sleep is a session type: only end_time is a filterable member, so the
        # server returns a superset (a session ending after `since` may have
        # started before it) and the start_time check below narrows it exactly.
        params: dict[str, str] = {
            "pageSize": _PAGE_SIZE,
            "filter": f'sleep.interval.end_time >= "{_rfc3339(since_iso)}"',
        }
        while True:
            r = self._c.get("/users/me/dataTypes/sleep/dataPoints", params=params)
            r.raise_for_status()
            body = r.json()
            for p in body.get("dataPoints", []):
                start = str(p.get("sleep", {}).get("interval", {}).get("startTime", ""))
                if start >= since_iso:
                    points.append(p)
            token = body.get("nextPageToken")
            if not token:
                return points
            params["pageToken"] = str(token)

    def close(self) -> None:
        self._c.close()

    def __enter__(self) -> "HealthClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
