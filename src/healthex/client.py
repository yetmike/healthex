import httpx

BASE = "https://health.googleapis.com/v4"


class HealthClient:
    """Thin wrapper around the Google Health REST API."""

    def __init__(self, access_token: str) -> None:
        self._c = httpx.Client(
            base_url=BASE,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=30.0,
        )

    def list_steps(self, since_iso: str) -> list[dict[str, object]]:
        """Return all steps dataPoints on or after *since_iso* (UTC ISO-8601)."""
        points: list[dict[str, object]] = []
        params: dict[str, str] = {"pageSize": "1000"}
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

    def _paginate(self, path: str, since_key: tuple[str, ...]) -> list[dict[str, object]]:
        """Generic paginator — yields all dataPoints where nested start >= since (unused for daily types)."""
        points: list[dict[str, object]] = []
        params: dict[str, str] = {"pageSize": "1000"}
        while True:
            r = self._c.get(path, params=params)
            r.raise_for_status()
            body = r.json()
            points.extend(body.get("dataPoints", []))
            token = body.get("nextPageToken")
            if not token:
                return points
            params["pageToken"] = str(token)

    def list_daily(self, data_type: str) -> list[dict[str, object]]:
        """Fetch all dataPoints for a daily data type (RHR, HRV). No client-side date filter needed."""
        return self._paginate(f"/users/me/dataTypes/{data_type}/dataPoints", ())

    def list_sleep(self, since_iso: str) -> list[dict[str, object]]:
        """
        Return all sleep dataPoints on or after *since_iso* (UTC ISO-8601).

        The API does not support server-side date range filters, so we paginate
        all results and filter client-side by sleep.interval.startTime.
        """
        points: list[dict[str, object]] = []
        params: dict[str, str] = {"pageSize": "50"}
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
