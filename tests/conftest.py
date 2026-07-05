from __future__ import annotations
import pytest
from aioresponses import aioresponses
from urbanhello_remi_api.client import ParseClient


BASE_URL = "https://remi2.urbanhello.com/parse"


@pytest.fixture
def mock_aiohttp():
    with aioresponses() as m:
        yield m


@pytest.fixture
def client():
    return ParseClient(session=None, timeout=10)
