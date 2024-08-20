import io
import json
import logging
import httpx
import csv

from datetime import datetime, timezone
from typing import Union, List
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

    SENSOR_TYPE_GPS = 653
    SENSOR_TYPE_ACCESSORY_MEASUREMENTS = 7842954

    def __init__(self, **kwargs):
        # API settings
        self.api_version = "v1"
        self.base_url = kwargs.get("base_url", settings.MOVEBANK_API_BASE_URL)
        self.feeds_endpoint = f"{self.base_url}/movebank/service/external-feed"
        self.permissions_endpoint = f"{self.base_url}/movebank/service/external-feed"
        self.direct_read_endpoint = f"{self.base_url}/movebank/service/direct-read"
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

    async def get_token(self):
        url = self.direct_read_endpoint
        try:
            response = await self._session.get(
                url,
                auth=(self.username, self.password),
                params=(
                    ('service', 'request-token'),
                )
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MBClientError(f"HTTP Exception for {exc.request.url} - {exc}")
        else:
            if response:
                token_str = response.content.decode('utf8')
                return json.loads(token_str)
            logger.info('get_token - Aut failed')
            return ""

    async def get_study(self, study_id: int):
        url = self.direct_read_endpoint
        try:
            response = await self._session.get(
                url,
                auth=(self.username, self.password),
                params=(
                    ('entity_type', 'study'),
                    ('study_id', study_id),
                    ('i_can_see_data', 'true'),
                    ('there_are_data_which_i_cannot_see', 'false')
                )
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MBClientError(f"HTTP Exception for {exc.request.url} - {exc}")
        else:
            if response:
                study = csv.DictReader(io.StringIO(response.content.decode('utf8')), delimiter=',')
                return [row for row in study]
            logger.info('get_study - No study found')
            return []

    async def get_individuals_by_study(self, study_id: int):
        url = self.direct_read_endpoint
        try:
            response = await self._session.get(
                url,
                auth=(self.username, self.password),
                params=(
                    ('entity_type', 'individual'),
                    ('study_id', study_id)
                )
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MBClientError(f"HTTP Exception for {exc.request.url} - {exc}")
        else:
            if response:
                individuals = response.content.decode('utf8')
                return list(csv.DictReader(io.StringIO(individuals), delimiter=','))
            logger.warning(f'get_individuals_by_study: {study_id} - No Individuals Found')
            return []

    async def get_individual_events(self, *,
                                    study_id: int = None,
                                    individual_id: int = None,
                                    timestamp_start: datetime = None,
                                    timestamp_end: datetime = datetime.now(timezone.utc),
                                    sensor_types: List[int] = [SENSOR_TYPE_GPS, SENSOR_TYPE_ACCESSORY_MEASUREMENTS],
                                    minimum_event_id: int = 0):

        url = self.direct_read_endpoint
        timestamp_start = timestamp_start.strftime("%Y%m%d%H%M%S000")
        timestamp_end = timestamp_end.strftime("%Y%m%d%H%M%S000")

        for sensor_type in sensor_types:
            params = (
                ('entity_type', 'event'),
                ('study_id', study_id),
                ('individual_id', individual_id),
                ('timestamp_start', timestamp_start),
                ('timestamp_end', timestamp_end),
                ('sensor_type_id', sensor_type),
                ('attributes', 'all')
            )
            response = await self._session.get(
                url,
                auth=(self.username, self.password),
                params=params
            )
            if response:
                events = response.content.decode('utf8')
                for item in csv.DictReader(io.StringIO(events), delimiter=','):
                    if int(item.get('event_id')) >= minimum_event_id:
                        yield item

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
