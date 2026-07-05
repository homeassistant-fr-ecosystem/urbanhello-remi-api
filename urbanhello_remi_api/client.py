from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .models import RemiAPIAuthError, RemiAPIError

_LOGGER = logging.getLogger(__name__)


class ParseClient:
    """Low-level async HTTP client for the UrbanHello Parse backend."""

    BASE_URL = "https://remi2.urbanhello.com/parse"
    APP_ID = "jf1a0bADt5fq"

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        timeout: int = 15,
    ) -> None:
        self._session = session
        self._timeout = timeout
        self._session_token: str | None = None

    @property
    def session_token(self) -> str | None:
        return self._session_token

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _headers(self, include_session: bool = True) -> dict[str, str]:
        headers = {
            "X-Parse-Application-Id": self.APP_ID,
            "Content-Type": "application/json",
        }
        if include_session and self._session_token:
            headers["X-Parse-Session-Token"] = self._session_token
        return headers

    async def _parse_response(self, resp: aiohttp.ClientResponse) -> Any:
        text = await resp.text()
        if resp.status == 401:
            raise RemiAPIAuthError(f"Authentication failed: {text}")
        if resp.status >= 400:
            raise RemiAPIError(f"HTTP {resp.status}: {text}")
        try:
            return await resp.json()
        except Exception:
            return text

    async def request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        include_session: bool = True,
    ) -> Any:
        """Perform an HTTP request against the Parse backend."""
        session = await self._ensure_session()
        url = f"{self.BASE_URL}{path}"
        timeout_ctrl = aiohttp.ClientTimeout(total=self._timeout)

        try:
            async with session.request(
                method,
                url,
                headers=self._headers(include_session),
                json=json,
                timeout=timeout_ctrl,
            ) as resp:
                return await self._parse_response(resp)

        except (TimeoutError, aiohttp.ClientError) as exc:
            if method.upper() == "GET" and "/classes/" in path:
                _LOGGER.debug("GET %s timed out, retrying with POST _method=GET", url)
                fallback = (json or {}).copy()
                fallback["_method"] = "GET"
                try:
                    async with session.post(
                        url,
                        headers=self._headers(include_session),
                        json=fallback,
                        timeout=timeout_ctrl,
                    ) as resp:
                        return await self._parse_response(resp)
                except (RemiAPIError, RemiAPIAuthError):
                    raise
                except Exception as exc2:
                    raise RemiAPIError(f"Request failed: {exc2}") from exc2
            raise RemiAPIError(str(exc)) from exc

    async def login(self, username: str, password: str) -> dict:
        """Authenticate and store session token."""
        data = await self.request(
            "POST",
            "/login",
            json={"username": username, "password": password},
            include_session=False,
        )
        if not isinstance(data, dict):
            raise RemiAPIError("Unexpected response during login")
        token = data.get("sessionToken")
        if not token:
            raise RemiAPIError("Login succeeded but session token was not returned")
        self._session_token = token
        return data

    async def logout(self) -> None:
        """Invalidate session token on the server."""
        if not self._session_token:
            return
        try:
            await self.request("POST", "/logout", json={}, include_session=True)
        except RemiAPIError:
            _LOGGER.debug("Logout request failed — clearing token locally")
        finally:
            self._session_token = None
