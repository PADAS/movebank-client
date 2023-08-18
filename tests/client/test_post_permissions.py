import httpx
import pytest
import respx
import aiofiles
from movebank_client import MBValidationError, PermissionOperations


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
                    csv_file=perm_file,
                    operation=PermissionOperations.ADD_USER_PRIVILEGES
                )


@pytest.mark.asyncio
async def test_permissions_file_validations(
        movebank_client,  mock_movebank_response, bad_permissions_filename
):
    async with respx.mock(assert_all_called=False) as movebank_api_mock:
        # Mock api responses
        movebank_api_mock.post(movebank_client.permissions_endpoint).respond(
            status_code=httpx.codes.OK,
            content=mock_movebank_response
        )
        async with movebank_client as client:
            async with aiofiles.open(bad_permissions_filename, mode='rb') as perm_file:
                with pytest.raises(MBValidationError):
                    await client.post_permissions(
                        study_name="gundi",
                        csv_file=perm_file
                    )
