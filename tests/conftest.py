"""Shared pytest fixtures for the urbanhello_remi_api test suite."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses

from urbanhello_remi_api.api import RemiAPI
from urbanhello_remi_api.client import ParseClient


BASE_URL = "https://remi2.urbanhello.com/parse"


@pytest.fixture
def mock_aiohttp():
    """Yield a mocked aiohttp session context."""
    with aioresponses() as m:
        yield m


@pytest.fixture
def client():
    """Return a ParseClient with no pre-existing session."""
    return ParseClient(session=None, timeout=10)


@pytest.fixture
def api():
    """Return a RemiAPI instance with test credentials."""
    return RemiAPI("user@example.com", "password", cache_duration=60)
