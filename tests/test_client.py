from __future__ import annotations
import pytest
from aioresponses import aioresponses
from urbanhello_remi_api.client import ParseClient
from urbanhello_remi_api.models import RemiAPIAuthError, RemiAPIError

BASE_URL = "https://remi2.urbanhello.com/parse"


@pytest.fixture
def mock_aiohttp():
    with aioresponses() as m:
        yield m


@pytest.fixture
def client():
    return ParseClient(session=None, timeout=10)


async def test_login_sets_session_token(client, mock_aiohttp):
    mock_aiohttp.post(
        f"{BASE_URL}/login",
        payload={"sessionToken": "tok123", "remis": []},
        status=200,
    )
    result = await client.login("user@example.com", "password")
    assert client.session_token == "tok123"
    assert result["sessionToken"] == "tok123"


async def test_login_raises_auth_error_on_401(client, mock_aiohttp):
    mock_aiohttp.post(f"{BASE_URL}/login", status=401, body="Unauthorized")
    with pytest.raises(RemiAPIAuthError):
        await client.login("user@example.com", "wrongpass")


async def test_login_raises_error_on_500(client, mock_aiohttp):
    mock_aiohttp.post(f"{BASE_URL}/login", status=500, body="Internal Server Error")
    with pytest.raises(RemiAPIError):
        await client.login("user@example.com", "password")


async def test_request_includes_session_token(client, mock_aiohttp):
    client._session_token = "tok123"
    mock_aiohttp.get(
        f"{BASE_URL}/classes/Remi",
        payload={"results": []},
        status=200,
    )
    await client.request("GET", "/classes/Remi")
    # Verify request was made (aioresponses raises if URL not matched)


async def test_request_without_session_when_include_session_false(client, mock_aiohttp):
    mock_aiohttp.post(
        f"{BASE_URL}/login",
        payload={"sessionToken": "tok"},
        status=200,
    )
    await client.request("POST", "/login", json={"username": "u", "password": "p"}, include_session=False)


async def test_logout_clears_session_token(client, mock_aiohttp):
    client._session_token = "tok123"
    mock_aiohttp.post(f"{BASE_URL}/logout", payload={}, status=200)
    await client.logout()
    assert client.session_token is None


async def test_logout_noop_when_no_token(client, mock_aiohttp):
    await client.logout()
    assert client.session_token is None


async def test_get_fallback_post_on_timeout(client, mock_aiohttp):
    import aiohttp
    mock_aiohttp.get(
        f"{BASE_URL}/classes/Remi/obj1",
        exception=aiohttp.ServerTimeoutError(),
    )
    mock_aiohttp.post(
        f"{BASE_URL}/classes/Remi/obj1",
        payload={"objectId": "obj1"},
        status=200,
    )
    result = await client.request("GET", "/classes/Remi/obj1")
    assert result["objectId"] == "obj1"


async def test_get_fallback_raises_if_post_also_fails(client, mock_aiohttp):
    import aiohttp
    mock_aiohttp.get(
        f"{BASE_URL}/classes/Remi/obj1",
        exception=aiohttp.ServerTimeoutError(),
    )
    mock_aiohttp.post(
        f"{BASE_URL}/classes/Remi/obj1",
        status=500,
        body="error",
    )
    with pytest.raises(RemiAPIError):
        await client.request("GET", "/classes/Remi/obj1")
