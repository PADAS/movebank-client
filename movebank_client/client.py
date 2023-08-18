import io
import json
import logging
from io import StringIO

import httpx
import csv
from typing import Union
from httpx import (
    AsyncClient,
    AsyncHTTPTransport,
    Timeout,
)
from . import settings
from .errors import MBClientError, MBValidationError
from .enums import TagDataOperations, PermissionOperations

logger = logging.getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)


class MovebankClient:
    DEFAULT_CONNECT_TIMEOUT_SECONDS = 3.1
    DEFAULT_DATA_TIMEOUT_SECONDS = 20
    DEFAULT_CONNECTION_RETRIES = 5

    def __init__(self, **kwargs):
        # API settings
        self.api_version = "v1"
        self.base_url = kwargs.get("base_url", settings.MOVEBANK_API_BASE_URL)
        self.feeds_endpoint = f"{self.base_url}/movebank/service/external-feed"
        self.permissions_endpoint = f"{self.base_url}/movebank/service/external-feed"
        # Authentication settings
        self.ssl_verify = kwargs.get("use_ssl", settings.MOVEBANK_SSL_VERIFY)
        self.username = kwargs.get("username", settings.MOVEBANK_USERNAME)
        self.password = kwargs.get("password", settings.MOVEBANK_PASSWORD)
        # Retries and timeouts settings
        self.max_retries = kwargs.get('max_http_retries', self.DEFAULT_CONNECTION_RETRIES)
        transport = AsyncHTTPTransport(retries=self.max_retries)
        connect_timeout = kwargs.get('connect_timeout', self.DEFAULT_CONNECT_TIMEOUT_SECONDS)
        data_timeout = kwargs.get('data_timeout', self.DEFAULT_DATA_TIMEOUT_SECONDS)
        timeout = Timeout(data_timeout, connect=connect_timeout, pool=connect_timeout)

        # Session
        self._session = AsyncClient(transport=transport, timeout=timeout, verify=self.ssl_verify)

    async def close(self):
        await self._session.aclose()

    # Support using this client as an async context manager.
    async def __aenter__(self):
        await self._session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._session.__aexit__()

    async def post_tag_data(
            self,
            feed_name: str,
            tag_id: str,
            json_file,
            operation: Union[TagDataOperations, str] = TagDataOperations.ADD_DATA
    ):
        url = self.feeds_endpoint
        form_data = {
            "operation": str(operation),
            "feed": feed_name,
            "tag": tag_id
        }
        try:  # Check if it's a valid json
            json_data = await json_file.read()
            json.loads(json_data)
        except json.decoder.JSONDecodeError:
            raise MBValidationError("The file must contain valid json data.")
        except Exception as e:
            raise MBClientError(f"Error parsing json data: {e}.")
        files = {
            # Notice the whole file is loaded in memory
            # Until httpx supports async file types for multipart uploads
            # https://github.com/encode/httpx/issues/1620
            "data": json_data
        }
        try:
            response = await self._session.post(
                url,
                auth=(self.username, self.password,),
                data=form_data,
                files=files
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MBClientError(f"HTTP Exception for {exc.request.url} - {exc}")
        return response.text

    async def post_permissions(
            self,
            study_name: str,
            csv_file,
            operation: Union[PermissionOperations, str] = PermissionOperations.ADD_USER_PRIVILEGES
    ):
        url = self.permissions_endpoint
        form_data = {
            "operation": str(operation),
            "study": study_name,
        }
        try:  # Check if it's a valid csv with the right delimiter and columns
            csv_data = await csv_file.read()
            csv_text = io.StringIO(csv_data.decode("utf-8"))
            reader = csv.DictReader(csv_text, delimiter=',')
        except Exception as e:
            raise MBClientError(f"Error parsing csv data: {e}.")
        else:
            expected_columns = ["login", "tag"]
            if reader.fieldnames != ["login", "tag"]:
                raise MBValidationError(f"The file must have columns: {expected_columns}")
        files = {
            # Notice the whole file is loaded in memory
            # Until httpx supports async file types for multipart uploads
            # https://github.com/encode/httpx/issues/1620
            "data": csv_data
        }
        try:
            response = await self._session.post(
                url,
                auth=(self.username, self.password,),
                data=form_data,
                files=files
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MBClientError(f"HTTP Exception for {exc.request.url} - {exc}")
        return response.text
