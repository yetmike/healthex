"""Unit tests for HealthClient — API calls mocked with respx."""

import httpx
import pytest
import respx

from healthex.client import BASE, HealthClient


@respx.mock
def test_list_sleep_single_page() -> None:
    respx.get(f"{BASE}/users/me/dataTypes/sleep/dataPoints").mock(
        return_value=httpx.Response(
            200,
            json={
                "dataPoints": [{"interval": {"startTime": "2026-06-27T23:00:00Z"}}],
            },
        )
    )
    with HealthClient("fake-token") as hc:
        points = hc.list_sleep("2026-06-01T00:00:00")
    assert len(points) == 1


@respx.mock
def test_list_sleep_paginates() -> None:
    responses = [
        httpx.Response(
            200,
            json={
                "dataPoints": [{"interval": {"startTime": "2026-06-26T23:00:00Z"}}],
                "nextPageToken": "tok123",
            },
        ),
        httpx.Response(
            200,
            json={"dataPoints": [{"interval": {"startTime": "2026-06-27T23:00:00Z"}}]},
        ),
    ]
    route = respx.get(f"{BASE}/users/me/dataTypes/sleep/dataPoints").mock(
        side_effect=responses
    )
    with HealthClient("fake-token") as hc:
        points = hc.list_sleep("2026-06-01T00:00:00")
    assert len(points) == 2
    assert route.call_count == 2


@respx.mock
def test_list_sleep_raises_on_http_error() -> None:
    respx.get(f"{BASE}/users/me/dataTypes/sleep/dataPoints").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"})
    )
    with HealthClient("bad-token") as hc, pytest.raises(httpx.HTTPStatusError):
        hc.list_sleep("2026-06-01T00:00:00")
