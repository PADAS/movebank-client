from datetime import datetime, timezone

import httpx
import pytest
import respx


START = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
END = datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)


def _mock_api(movebank_api_mock, movebank_client, events_response, study_attributes_response):
    def side_effect(request):
        params = dict(request.url.params)
        if params.get("entity_type") == "study_attribute":
            return httpx.Response(200, content=study_attributes_response)
        return httpx.Response(200, content=events_response)

    return movebank_api_mock.get(movebank_client.direct_read_endpoint).mock(side_effect=side_effect)


@pytest.mark.asyncio
async def test_accessory_sensor_is_queried_with_overlap(
        movebank_client, mock_movebank_accessory_events_response, mock_movebank_study_attributes_response
):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        route = _mock_api(movebank_api_mock, movebank_client,
                          mock_movebank_accessory_events_response, mock_movebank_study_attributes_response)
        async with movebank_client as client:
            events = [e async for e in client.get_individual_events_by_time(
                study_id="12345", individual_id="111",
                timestamp_start=START, timestamp_end=END,
                sensor_type_ids=[client.SENSOR_TYPE_ACCESSORY_MEASUREMENTS],
            )]

        assert len(events) == 1
        assert events[0]["event_id"] == "200"
        event_calls = [c for c in route.calls if dict(c.request.url.params).get("entity_type") == "event"]
        assert len(event_calls) == 1
        params = dict(event_calls[0].request.url.params)
        assert params["sensor_type_id"] == "7842954"
        # 60-minute overlap: 2026-01-01T00:00 becomes 2025-12-31T23:00
        assert params["timestamp_start"] == "20251231230000000"
        assert params["attributes"] == "all"


@pytest.mark.asyncio
async def test_gps_attributes_union_study_and_common(
        movebank_client, mock_movebank_events_response, mock_movebank_study_attributes_response
):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        route = _mock_api(movebank_api_mock, movebank_client,
                          mock_movebank_events_response, mock_movebank_study_attributes_response)
        async with movebank_client as client:
            events = [e async for e in client.get_individual_events_by_time(
                study_id="12345", individual_id="111",
                timestamp_start=START, timestamp_end=END,
                sensor_type_ids=[client.SENSOR_TYPE_GPS],
            )]

        assert len(events) == 2
        event_calls = [c for c in route.calls if dict(c.request.url.params).get("entity_type") == "event"]
        params = dict(event_calls[0].request.url.params)
        attributes = set(params["attributes"].split(","))
        # Study-advertised attributes are present...
        assert {"location_lat", "location_long", "ground_speed"} <= attributes
        # ...and so is every common attribute the transform relies on.
        assert {"event_id", "individual_id", "deployment_id", "tag_id", "study_id",
                "sensor_type_id", "individual_local_identifier", "tag_local_identifier",
                "individual_taxon_canonical_name"} <= attributes
        assert params["timestamp_start"] == "20260101000000000"


@pytest.mark.asyncio
async def test_gps_attributes_default_to_all_without_study_metadata(
        movebank_client, mock_movebank_events_response
):
    empty_attributes = b'short_name,sensor_type_id\r\n'
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        route = _mock_api(movebank_api_mock, movebank_client,
                          mock_movebank_events_response, empty_attributes)
        async with movebank_client as client:
            [e async for e in client.get_individual_events_by_time(
                study_id="12345", individual_id="111",
                timestamp_start=START, timestamp_end=END,
                sensor_type_ids=[client.SENSOR_TYPE_GPS],
            )]
        event_calls = [c for c in route.calls if dict(c.request.url.params).get("entity_type") == "event"]
        assert dict(event_calls[0].request.url.params)["attributes"] == "all"


@pytest.mark.asyncio
async def test_minimum_event_id_filters_results(
        movebank_client, mock_movebank_events_response, mock_movebank_study_attributes_response
):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        _mock_api(movebank_api_mock, movebank_client,
                  mock_movebank_events_response, mock_movebank_study_attributes_response)
        async with movebank_client as client:
            events = [e async for e in client.get_individual_events_by_time(
                study_id="12345", individual_id="111",
                timestamp_start=START, timestamp_end=END,
                sensor_type_ids=[client.SENSOR_TYPE_GPS],
                minimum_event_id=101,
            )]
        assert [e["event_id"] for e in events] == ["101"]
