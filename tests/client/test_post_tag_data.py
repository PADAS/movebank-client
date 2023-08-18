import httpx
import pytest
import respx
import aiofiles
from movebank_client import MBValidationError, TagDataOperations


@pytest.mark.asyncio
async def test_post_tag_data(
        movebank_client,  mock_movebank_response, tag_data_filename
):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        # Mock api responses
        movebank_api_mock.post(movebank_client.feeds_endpoint).respond(
            status_code=httpx.codes.OK,
            content=mock_movebank_response
        )
        async with movebank_client as client:
            async with aiofiles.open(tag_data_filename, mode='rb') as tag_data:
                await client.post_tag_data(
                    feed_name="gundi/earthranger",
                    tag_id="awt.1320894.cc53b809784e406db9cfd8dcbc624985",
                    json_file=tag_data,
                    operation=TagDataOperations.ADD_DATA
                )


@pytest.mark.asyncio
async def test_tag_data_file_validations(
        movebank_client,  mock_movebank_response, bad_tag_data_filename
):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        # Mock api responses
        movebank_api_mock.post(movebank_client.feeds_endpoint).respond(
            status_code=httpx.codes.OK,
            content=mock_movebank_response
        )
        async with movebank_client as client:
            async with aiofiles.open(bad_tag_data_filename, mode='rb') as tag_data:
                with pytest.raises(MBValidationError):
                    await client.post_tag_data(
                        feed_name="gundi/earthranger",
                        tag_id="awt.1320894.cc53b809784e406db9cfd8dcbc624985",
                        json_file=tag_data
                    )
