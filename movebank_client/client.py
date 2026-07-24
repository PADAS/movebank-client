import backoff
import hashlib
import io
import json
import logging
import httpx
import csv
import typing

from datetime import datetime, timezone, timedelta
from typing import Union, List
from httpx import (
    AsyncClient,
    AsyncHTTPTransport,
    Timeout,
)
from movebank_client import settings
from movebank_client.errors import MBClientError, MBValidationError, MBForbiddenError, MBRateLimitError
from movebank_client.enums import TagDataOperations, PermissionOperations

logger = logging.getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)


def is_license_terms_response(response):
    try:
        return 'License Terms:' in response.content.decode('utf-8')
    except (AttributeError, UnicodeDecodeError):
        return False


async def on_licenseterms_response(details):
    """
    On predicate handler to modify the params with the license hash if needed.
    """
    # self = details['args'][0]  # Assuming the method is called on an instance
    # params = details['kwargs']['params']
    response = details['value']
    hash_digest = hashlib.md5(response.content).hexdigest()
    details['kwargs']['params'] += (('license-md5', hash_digest),)
    details['kwargs']['cookies'] = response.cookies


def parse_retry_after(response, default=15):
    """Parse Retry-After header as integer seconds, falling back to the default
    for non-integer values such as HTTP-date formats."""
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return default
    try:
        return int(retry_after)
    except ValueError:
        # Could be HTTP-date format; fall back to the default.
        logger.warning(f"Unexpected Retry-After format: {retry_after}, using default {default}s")
        return default


def on_backoff_429(details):
    wait = details.get('wait', 0)
    tries = details.get('tries', 0)
    logger.warning(f"Rate limited (429). Attempt {tries}, waiting {wait:.1f}s before retry.")


def on_giveup_429(details):
    tries = details.get('tries', 0)
    elapsed = details.get('elapsed', 0)
    message = f"Rate limit retries exhausted after {tries} attempts over {elapsed:.1f}s"
    # WARNING, not ERROR: exhausting 429 retries is an expected, recoverable
    # condition (the caller runs again later), so it should not read as a hard
    # failure. Raise a dedicated type carrying the final 429 response so callers
    # can classify it as a rate limit.
    logger.warning(message)
    # Pass the final 429 response into the constructor so callers can classify
    # this as a rate limit (e.g. response.status_code == 429).
    raise MBRateLimitError(message, response=details.get('value'))


class MovebankClient:
    DEFAULT_CONNECT_TIMEOUT_SECONDS = 3.1
    DEFAULT_DATA_TIMEOUT_SECONDS = 20
    DEFAULT_CONNECTION_RETRIES = 5

    SENSOR_TYPE_GPS = 653
    SENSOR_TYPE_ACCESSORY_MEASUREMENTS = 7842954

    MOVEBANK_SENSOR_TYPE_LABEL_TO_ID = {
        'gps': SENSOR_TYPE_GPS,
        'accessory-measurements': SENSOR_TYPE_ACCESSORY_MEASUREMENTS
    }

    # Attributes the integrations rely on for cursoring and transforms —
    # always requested for GPS queries, in addition to study-advertised ones.
    GPS_COMMON_ATTRIBUTES = {
        'event_id',
        'individual_id',
        'deployment_id',
        'tag_id',
        'study_id',
        'sensor_type_id',
        'individual_local_identifier',
        'tag_local_identifier',
        'individual_taxon_canonical_name',
    }

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
        self.study_attributes_cache = {}

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

    @backoff.on_predicate(
        backoff.runtime,
        predicate=lambda r: r.status_code == 429,
        value=parse_retry_after,
        jitter=None,
        max_tries=3,
        max_time=120,
        on_backoff=on_backoff_429,
        on_giveup=on_giveup_429,
    )
    @backoff.on_predicate(
        backoff.constant,
        is_license_terms_response,
        max_tries=2,
        on_backoff=on_licenseterms_response
    )
    @backoff.on_exception(
        backoff.constant,
        (httpx.HTTPError, httpx.ReadTimeout, httpx.ConnectTimeout),
        max_tries=3,
        max_time=60,
        interval=10
    )
    async def _call_api(self, url: str = "", *, params: tuple = (), cookies=None) -> str:
        """
        Requests Movebank API with ((param1, value1), (param2, value2),).
        Returns the API response as-is. This is to allow on_predicate to evaluate the response.
        """
        response = await self._session.get(url, params=params, auth=(self.username, self.password), cookies=cookies)
        if httpx.codes.is_success(
                response.status_code) or response.status_code == 429:  # successful request or rate limited
            return response
        else:
            logger.error('Request failed with status code %s', response.status_code)
            response.raise_for_status()


    async def get_token(self):
        url = self.direct_read_endpoint
        try:
            response = await self._call_api(url=url, params=(
                    ('service', 'request-token'),
                )
            )
        except httpx.HTTPError as exc:
            if exc.response.status_code == 403:
                # Auth failed in MB API
                raise MBForbiddenError(f"MB API returned 403. Authentication failed - {exc}")
            raise MBClientError(f"HTTP Exception for {exc.request.url} - {exc}")
        else:
            if response:
                token_str = response.content.decode('utf8')
                return json.loads(token_str)
            logger.info('get_token - Auth failed')
            return ""

    async def get_study(self, study_id:str = None) -> list:
        url = self.direct_read_endpoint
        studies = await self._call_api(url=url, params=(('entity_type', 'study'), ('study_id', study_id)))
        if studies:
            # parse raw text to dicts
            studies = csv.DictReader(io.StringIO(studies.content.decode('utf8')), delimiter=',')
            studies = [s for s in studies if
                    s['i_can_see_data'] == 'true' and s['there_are_data_which_i_cannot_see'] == 'false']
            if studies:
                return studies[0]

        logger.warning('No info available for study ID: %s', study_id)

    async def get_study_attributes(self, study_id: str = None, sensor_type_id: str = None) -> list:
        url = self.direct_read_endpoint
        if (study_id, sensor_type_id) not in self.study_attributes_cache:
            study_sensor_attributes = await self._call_api(
                url=url,
                params=(
                    ('entity_type', 'study_attribute'),
                    ('sensor_type_id', str(sensor_type_id)),
                    ('study_id', study_id)
                )
            )

            if study_sensor_attributes:
                study_sensor_attributes = csv.DictReader(io.StringIO(
                    study_sensor_attributes.content.decode('utf8')), delimiter=','
                )
                self.study_attributes_cache[(study_id, sensor_type_id)] = [s for s in study_sensor_attributes]

        return self.study_attributes_cache.get((study_id, sensor_type_id))

    async def get_studies(self) -> list:
        url = self.direct_read_endpoint
        studies = await self._call_api(url=url, params=(('entity_type', 'study'),('i_can_see_data', 'true')))
        if studies:
            # parse raw text to dicts
            studies = csv.DictReader(io.StringIO(studies.content.decode('utf8')), delimiter=',')
            return [s for s in studies if
                    s['i_can_see_data'] == 'true' and s['there_are_data_which_i_cannot_see'] == 'false']
        logger.info('get_studies - No studies found')
        return []

    async def get_individuals_by_study(self, *, study_id: str = None) -> typing.List[dict]:
        # Fetch a list of individuals for the given study ID.
        logger.info(f'get_individuals_by_study for study_id: {study_id}')
        url = self.direct_read_endpoint
        individuals = await self._call_api(url=url, params=(('entity_type', 'individual'), ('study_id', study_id)))
        if individuals:
            individuals = individuals.content.decode('utf8')
            return list(csv.DictReader(io.StringIO(individuals), delimiter=','))
        logger.warning(f'get_individuals_by_study: {study_id} - No Individuals Found')
        return []

    async def get_individual_events_by_time(
            self, *,
            study_id: str = None,
            individual_id: str = None,
            timestamp_start: datetime = None,
            timestamp_end: datetime = None,
            sensor_type_ids: typing.List[int] = [SENSOR_TYPE_GPS],
            minimum_event_id: int = 0
    ):
        # Movebank expects timestamps as yyyyMMddHHmmssSSS
        timestamp_end_str = timestamp_end.strftime("%Y%m%d%H%M%S000") if timestamp_end else None
        url = self.direct_read_endpoint
        for sensor_type in sensor_type_ids:
            if sensor_type == self.SENSOR_TYPE_ACCESSORY_MEASUREMENTS:
                # Accessory data can arrive out of order, so query with a one-hour overlap.
                lower_bound = (timestamp_start - timedelta(minutes=60)).strftime("%Y%m%d%H%M%S000")
            else:
                lower_bound = timestamp_start.strftime("%Y%m%d%H%M%S000")

            attributes = 'all'
            if sensor_type == self.SENSOR_TYPE_GPS:
                # For GPS, narrow the attributes list using study metadata when available.
                study_attributes = await self.get_study_attributes(study_id=study_id, sensor_type_id=str(sensor_type))
                if study_attribute_names := {
                    item.get('short_name') for item in (study_attributes or [])
                    if item.get('sensor_type_id') == str(sensor_type) and item.get('short_name')
                }:
                    attributes = ','.join(sorted(study_attribute_names | self.GPS_COMMON_ATTRIBUTES))

            params = (
                ('entity_type', 'event'),
                ('study_id', study_id),
                ('individual_id', individual_id),
                ('timestamp_start', lower_bound),
                ('timestamp_end', timestamp_end_str),
                ('sensor_type_id', sensor_type),
                ('attributes', attributes),
            )
            events = await self._call_api(url=url, params=params)
            if events:
                events_csv = events.content.decode('utf8')
                for item in csv.DictReader(io.StringIO(events_csv), delimiter=','):
                    if int(item.get('event_id')) >= minimum_event_id:
                        yield item


    async def get_individual_events(
            self, *,
            study_id: int = None,
            individual_id: int = None,
            timestamp_start: datetime = None,
            timestamp_end: datetime = datetime.now(timezone.utc),
            sensor_types: List[int] = [SENSOR_TYPE_GPS, SENSOR_TYPE_ACCESSORY_MEASUREMENTS],
            minimum_event_id: int = 0
    ):

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
            response = await self._call_api(
                url=url,
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
