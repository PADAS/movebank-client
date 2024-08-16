import pytest
import httpx
import respx


@pytest.mark.asyncio
async def test_get_study(
        movebank_client,  mock_movebank_get_study_response
):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        # Mock api responses
        movebank_api_mock.get(movebank_client.direct_read_endpoint).respond(
            status_code=httpx.codes.OK,
            content=mock_movebank_get_study_response
        )
        async with movebank_client as client:
            study = await client.get_study(1234567890)
            assert len(study) == 1
            assert study[0]["id"] == "1234567890"


@pytest.mark.asyncio
async def test_get_individuals_by_study(
        movebank_client,  mock_movebank_get_individuals_by_study_response
):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        # Mock api responses
        movebank_api_mock.get(movebank_client.direct_read_endpoint).respond(
            status_code=httpx.codes.OK,
            content=mock_movebank_get_individuals_by_study_response
        )
        async with movebank_client as client:
            individuals = await client.get_individuals_by_study(1234567890)
            assert len(individuals) == 2
