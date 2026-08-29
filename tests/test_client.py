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
                "dataPoints": [{"sleep": {"interval": {"startTime": "2026-06-27T23:00:00Z"}}}],
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
                "dataPoints": [{"sleep": {"interval": {"startTime": "2026-06-26T23:00:00Z"}}}],
                "nextPageToken": "tok123",
            },
        ),
        httpx.Response(
            200,
            json={"dataPoints": [{"sleep": {"interval": {"startTime": "2026-06-27T23:00:00Z"}}}]},
        ),
    ]
    route = respx.get(f"{BASE}/users/me/dataTypes/sleep/dataPoints").mock(side_effect=responses)
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


@respx.mock
def test_list_steps_filters_server_side() -> None:
    """Without a filter the API returns the whole history and we discard most of it."""
    route = respx.get(f"{BASE}/users/me/dataTypes/steps/dataPoints").mock(
        return_value=httpx.Response(200, json={"dataPoints": []})
    )
    with HealthClient("t") as hc:
        hc.list_steps("2026-08-27T00:00:00")

    params = route.calls[0].request.url.params
    assert params["filter"] == 'steps.interval.start_time >= "2026-08-27T00:00:00Z"'
    assert params["pageSize"] == "10000"


@respx.mock
def test_list_sleep_filters_on_end_time() -> None:
    """start_time is not a filterable member for the sleep session type."""
    route = respx.get(f"{BASE}/users/me/dataTypes/sleep/dataPoints").mock(
        return_value=httpx.Response(200, json={"dataPoints": []})
    )
    with HealthClient("t") as hc:
        hc.list_sleep("2026-08-27T00:00:00")

    assert (
        route.calls[0].request.url.params["filter"]
        == 'sleep.interval.end_time >= "2026-08-27T00:00:00Z"'
    )


@respx.mock
def test_sleep_server_filter_is_a_superset_narrowed_client_side() -> None:
    """A session ending after `since` but starting before it must be dropped."""
    early = {"sleep": {"interval": {"startTime": "2026-08-26T22:00:00Z"}}}
    late = {"sleep": {"interval": {"startTime": "2026-08-27T22:00:00Z"}}}
    respx.get(f"{BASE}/users/me/dataTypes/sleep/dataPoints").mock(
        return_value=httpx.Response(200, json={"dataPoints": [early, late]})
    )
    with HealthClient("t") as hc:
        points = hc.list_sleep("2026-08-27T00:00:00")

    assert points == [late]


@respx.mock
def test_list_daily_filters_by_date() -> None:
    route = respx.get(f"{BASE}/users/me/dataTypes/daily-resting-heart-rate/dataPoints").mock(
        return_value=httpx.Response(200, json={"dataPoints": []})
    )
    with HealthClient("t") as hc:
        hc.list_daily("daily-resting-heart-rate", "2026-08-27T00:00:00")

    assert (
        route.calls[0].request.url.params["filter"]
        == 'daily_resting_heart_rate.date >= "2026-08-27"'
    )


@respx.mock
def test_list_daily_without_since_sends_no_filter() -> None:
    route = respx.get(f"{BASE}/users/me/dataTypes/daily-heart-rate-variability/dataPoints").mock(
        return_value=httpx.Response(200, json={"dataPoints": []})
    )
    with HealthClient("t") as hc:
        hc.list_daily("daily-heart-rate-variability")

    assert "filter" not in route.calls[0].request.url.params


@respx.mock
def test_already_zoned_since_is_not_double_suffixed() -> None:
    route = respx.get(f"{BASE}/users/me/dataTypes/steps/dataPoints").mock(
        return_value=httpx.Response(200, json={"dataPoints": []})
    )
    with HealthClient("t") as hc:
        hc.list_steps("2026-08-27T00:00:00Z")

    assert "ZZ" not in route.calls[0].request.url.params["filter"]
