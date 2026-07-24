import httpx
import pytest
import respx

from movebank_client.client import parse_retry_after
from movebank_client.errors import MBClientError, MBRateLimitError


def test_parse_retry_after_integer_seconds():
    response = httpx.Response(429, headers={"Retry-After": "30"})
    assert parse_retry_after(response) == 30


def test_parse_retry_after_missing_header_uses_default():
    response = httpx.Response(429)
    assert parse_retry_after(response) == 15
    assert parse_retry_after(response, default=5) == 5


def test_parse_retry_after_http_date_falls_back_to_default():
    response = httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})
    assert parse_retry_after(response) == 15


@pytest.mark.asyncio
async def test_429_is_retried_then_succeeds(movebank_client, mock_movebank_get_individuals_by_study_response):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        route = movebank_api_mock.get(movebank_client.direct_read_endpoint).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(200, content=mock_movebank_get_individuals_by_study_response),
            ]
        )
        async with movebank_client as client:
            individuals = await client.get_individuals_by_study(study_id=1234567890)
        assert len(individuals) == 2
        assert route.call_count == 2


@pytest.mark.asyncio
async def test_429_retries_exhausted_raises(movebank_client):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        route = movebank_api_mock.get(movebank_client.direct_read_endpoint).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(429, headers={"Retry-After": "0"}),
            ]
        )
        async with movebank_client as client:
            with pytest.raises(MBRateLimitError) as exc_info:
                await client.get_individuals_by_study(study_id=1234567890)
        assert route.call_count == 3
        # Dedicated type (still a MBClientError) carrying the final 429 response,
        # so callers can classify this as a recoverable rate limit.
        assert isinstance(exc_info.value, MBClientError)
        assert exc_info.value.response.status_code == 429
