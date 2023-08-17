import httpx
import pytest
import respx
import aiofiles


@pytest.mark.asyncio
async def test_post_permissions(
        movebank_client,  mock_movebank_response, permissions_filename
):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        # Mock api responses
        movebank_api_mock.post(movebank_client.permissions_endpoint).respond(
            status_code=httpx.codes.OK,
            content=mock_movebank_response
        )
        async with movebank_client as client:
            async with aiofiles.open(permissions_filename, mode='rb') as perm_file:
                await client.post_permissions(
                    study_name="gundi",
                    csv_file=perm_file
                )
