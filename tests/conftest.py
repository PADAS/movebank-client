import os
from pathlib import Path

import pytest

import pytest
from movebank_client.client import MovebankClient


@pytest.fixture
def client_settings():
    return {
        "base_url": "https://www.movebank.mpg.de",
        "username": "fake-admin-user",
        "password": "fake-admin-psw",
        "use_ssl": True,
        "max_http_retries": 10,
        "connect_timeout": 5,
        "data_timeout": 10
    }


@pytest.fixture
def movebank_client(client_settings):
    return MovebankClient(**client_settings)


@pytest.fixture
def mock_movebank_response():
    # Movebank's API doesn't return any content, just 200 OK.
    return ""


@pytest.fixture()
def tag_data_filename():
    return os.path.join(
        Path(os.path.dirname(os.path.realpath(__file__))),
        "test_data/tag_data.json"
    )


@pytest.fixture()
def permissions_filename():
    return os.path.join(
        Path(os.path.dirname(os.path.realpath(__file__))),
        "test_data/tag_data.json"
    )
