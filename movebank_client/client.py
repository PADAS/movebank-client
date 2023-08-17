import logging
from httpx import (
    AsyncClient,
    AsyncHTTPTransport,
    Timeout,
)
from . import settings


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

    async def post_tag_data(self, feed_name: str, tag_id: str, json_file):
        url = self.feeds_endpoint
        form_data = {
            "operation": "add-data",
            "feed": feed_name,
            "tag": tag_id
        }
        files = {
            # Notice the whole file is loaded in memory
            # Until httpx supports async file types for multipart uploads
            # https://github.com/encode/httpx/issues/1620
            "data": await json_file.read()
        }
        response = await self._session.post(
            url,
            auth=(self.username, self.password,),
            data=form_data,
            files=files
        )
        response.raise_for_status()
        return response.text

    async def post_permissions(self, study_name: str, csv_file, append_mode=True):
        url = self.permissions_endpoint
        form_data = {
            "operation": "add-user-privileges" if append_mode else "update-user-privileges",
            "study": study_name,
        }
        files = {
            # Notice the whole file is loaded in memory
            # Until httpx supports async file types for multipart uploads
            # https://github.com/encode/httpx/issues/1620
            "data": await csv_file.read()
        }
        response = await self._session.post(
            url,
            auth=(self.username, self.password,),
            data=form_data,
            files=files
        )
        response.raise_for_status()
        return response.text
