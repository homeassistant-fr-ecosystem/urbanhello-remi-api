"""High-level async API wrapper for the UrbanHello Rémi baby monitor."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .client import ParseClient
from .models import Alarm, Face, RemiAPIError, RemiDevice

_LOGGER = logging.getLogger(__name__)

# Mapping from HA-style snake_case face names to Parse API camelCase names
FACE_NAME_MAP = {
    "sleepy_face": "sleepyFace",
    "awake_face": "awakeFace",
    "blank_face": "blankFace",
    "semi_awake_face": "semiAwakeFace",
    "smily_face": "smilyFace",
}

# Classes to try for alarm operations (Parse backend uses different class names)
ALARM_CLASSES = ["Event", "Alarm", "Schedule"]


class RemiAPI:  # pylint: disable=too-many-public-methods,too-many-instance-attributes
    """Async client for UrbanHello (Rémi) Parse-based API."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
        cache_duration: int = 60,
        request_timeout: int = 15,
    ) -> None:
        """Initialise the API wrapper with credentials and optional config."""
        self.username = username
        self.password = password
        self._client = ParseClient(session=session, timeout=request_timeout)
        self._cache_duration = float(cache_duration)

        # Device cache: objectId -> RemiDevice
        self._device_cache: dict[str, RemiDevice] = {}
        self._device_cache_expiry: dict[str, float] = {}

        # Faces cache: name -> Face
        self._faces_by_name: dict[str, Face] = {}
        self._faces_by_id: dict[str, str] = {}  # objectId -> name

        # Alarms cache: objectId -> list[Alarm]
        self._alarms_cache: dict[str, list[Alarm]] = {}

        # Raw remis list (kept for HA compatibility)
        self.remis: list[dict[str, Any]] = []

    def _is_cache_valid(self, key: str) -> bool:
        expiry = self._device_cache_expiry.get(key)
        return expiry is not None and expiry > time.time()

    def _pointer(self, class_name: str, object_id: str) -> dict[str, str]:
        return {"__type": "Pointer", "className": class_name, "objectId": object_id}

    def _invalidate_device_cache(self, object_id: str) -> None:
        self._device_cache.pop(object_id, None)
        self._device_cache_expiry.pop(object_id, None)

    async def login(self) -> None:
        """Authenticate and populate session token, devices and faces."""
        data = await self._client.login(self.username, self.password)
        self.remis = data.get("remis") or []
        if not self.remis:
            try:
                await self.list_devices(refresh=True)
            except RemiAPIError:
                _LOGGER.debug("Could not auto-refresh devices after login", exc_info=True)
        try:
            await self.list_faces(refresh=True)
        except RemiAPIError:
            _LOGGER.debug("Could not retrieve faces during login", exc_info=True)

    async def logout(self) -> None:
        """Invalidate the current session."""
        await self._client.logout()

    # -------------------------------------------------------------------------
    # Device reads
    # -------------------------------------------------------------------------

    async def list_faces(self, refresh: bool = False) -> list[Face]:
        """Retrieve available faces."""
        if self._faces_by_name and not refresh:
            return list(self._faces_by_name.values())
        result = await self._client.request("GET", "/classes/Face")
        results = result.get("results", []) if isinstance(result, dict) else []
        self._faces_by_name = {}
        self._faces_by_id = {}
        faces = []
        for item in results:
            face = Face.from_dict(item)
            if face.object_id and face.name:
                self._faces_by_name[face.name] = face
                self._faces_by_id[face.object_id] = face.name
                faces.append(face)
        return faces

    async def list_devices(self, refresh: bool = False) -> list[RemiDevice]:  # pylint: disable=unused-argument
        """List Remi devices. The refresh parameter is reserved for cache-busting."""
        result = await self._client.request("GET", "/classes/Remi")
        raw_list = result.get("results", []) if isinstance(result, dict) else []
        self.remis = raw_list
        return [RemiDevice.from_dict(d, self._faces_by_id) for d in raw_list]

    async def get_device(self, object_id: str, refresh: bool = False) -> RemiDevice:
        """Retrieve a Remi device, using cache unless refresh=True."""
        if not refresh and self._is_cache_valid(object_id):
            return self._device_cache[object_id]
        data = await self._client.request("GET", f"/classes/Remi/{object_id}")
        if not isinstance(data, dict):
            msg = "Unexpected response when fetching Remi info"
            raise RemiAPIError(msg)
        device = RemiDevice.from_dict(data, self._faces_by_id)
        self._device_cache[object_id] = device
        self._device_cache_expiry[object_id] = time.time() + self._cache_duration
        return device

    # -------------------------------------------------------------------------
    # Device control
    # -------------------------------------------------------------------------

    async def _update_device(self, object_id: str, payload: dict[str, Any]) -> None:
        await self._client.request("PUT", f"/classes/Remi/{object_id}", json=payload)
        self._invalidate_device_cache(object_id)

    async def set_brightness(self, object_id: str, brightness: int) -> None:
        """Set the screen brightness of a device."""
        await self._update_device(object_id, {"luminosity": brightness})

    async def set_night_luminosity(self, object_id: str, level: int) -> None:
        """Set the minimum night-light brightness of a device."""
        await self._update_device(object_id, {"light_min": level})

    async def set_volume(self, object_id: str, level: int) -> None:
        """Set the speaker volume of a device."""
        await self._update_device(object_id, {"volume": level})

    async def set_noise_threshold(self, object_id: str, threshold: int) -> None:
        """Set the noise detection threshold of a device."""
        await self._update_device(object_id, {"noise_threshold": threshold})

    async def set_clock_format(self, object_id: str, use_24h: bool) -> None:
        """Switch the device clock between 12h and 24h format."""
        await self._update_device(object_id, {"hourFormat24": use_24h})

    async def set_music_mode(self, object_id: str, mode: int) -> None:
        """Set the music playback mode on a device."""
        await self._update_device(object_id, {"musicMode": mode})

    async def set_face(self, object_id: str, face_name: str) -> None:
        """Set face by name (snake_case or camelCase)."""
        api_face_name = FACE_NAME_MAP.get(face_name, face_name)
        face = self._faces_by_name.get(api_face_name)
        if not face:
            await self.list_faces(refresh=True)
            face = self._faces_by_name.get(api_face_name)
        if not face:
            msg = f"Unknown face '{api_face_name}'"
            raise RemiAPIError(msg)
        await self._update_device(object_id, {"face": self._pointer("Face", face.object_id)})

    async def turn_on(self, object_id: str) -> None:
        """Turn the device on by setting the sleepy face."""
        await self.set_face(object_id, "sleepyFace")

    async def turn_off(self, object_id: str) -> None:
        """Turn the device off by setting the awake face."""
        await self.set_face(object_id, "awakeFace")

    async def play_media(self, object_id: str, sound: str, volume: int | None = None) -> None:
        """Play a sound on the device, optionally at a specific volume."""
        payload: dict[str, Any] = {"sound": sound}
        if volume is not None:
            payload["volume"] = volume
        await self._update_device(object_id, payload)

    async def stop_sound(self, object_id: str) -> None:
        """Stop any currently playing sound on a device."""
        await self._update_device(object_id, {"sound": ""})

    # -------------------------------------------------------------------------
    # Alarm management
    # -------------------------------------------------------------------------

    async def get_alarms(self, object_id: str, refresh: bool = False) -> list[Alarm]:
        """Retrieve alarms for a device."""
        if not refresh and object_id in self._alarms_cache:
            return self._alarms_cache[object_id]
        alarms: list[Alarm] = []
        try:
            where = {"remi": self._pointer("Remi", object_id)}
            result = await self._client.request("GET", "/classes/Event", json={"where": where})
            if isinstance(result, dict):
                for event in result.get("results", []):
                    try:
                        alarms.append(Alarm.from_dict(event, self._faces_by_id))
                    except (KeyError, ValueError, TypeError):
                        _LOGGER.debug("Could not parse alarm event", exc_info=True)
        except RemiAPIError as e:
            _LOGGER.warning("Failed to get alarms: %s", e)
        self._alarms_cache[object_id] = alarms
        return alarms

    def _build_alarm_payload(self, cls: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Build class-specific alarm payload from generic kwargs."""
        payload = kwargs.copy()
        if cls == "Event":
            if "time" in payload:
                parts = payload.pop("time").split(":")
                payload["event_time"] = (
                    [int(parts[0]), int(parts[1])] if len(parts) >= 2 else [0, 0]
                )
            if "days" in payload:
                recurrence = [0] * 7
                for day_index in payload.pop("days"):
                    if 0 <= day_index < 7:
                        recurrence[day_index] = 1
                payload["recurrence"] = recurrence
            if "face" in payload and isinstance(payload["face"], str):
                api_name = FACE_NAME_MAP.get(payload["face"], payload["face"])
                face = self._faces_by_name.get(api_name)
                if face:
                    payload["face"] = self._pointer("Face", face.object_id)
                else:
                    payload.pop("face")
        return payload

    async def create_alarm(self, object_id: str, alarm_time: str, **kwargs: Any) -> Alarm:
        """Create a new alarm for a Remi device."""
        parts = alarm_time.split(":")
        base_payload = {
            "remi": self._pointer("Remi", object_id),
            "event_time": [int(parts[0]), int(parts[1])] if len(parts) >= 2 else [0, 0],
            "enabled": kwargs.get("enabled", True),
            "recurrence": kwargs.get("recurrence", [1] * 7),
        }
        for cls in ALARM_CLASSES:
            try:
                result = await self._client.request(
                    "POST", f"/classes/{cls}", json=base_payload
                )
                self._alarms_cache.pop(object_id, None)
                merged = {**base_payload, **(result if isinstance(result, dict) else {})}
                return Alarm.from_dict(merged, self._faces_by_id)
            except RemiAPIError:
                continue
        msg = "Failed to create alarm"
        raise RemiAPIError(msg)

    async def update_alarm(self, object_id: str, alarm_id: str, **kwargs: Any) -> Alarm:
        """Update an existing alarm."""
        for cls in ALARM_CLASSES:
            payload = self._build_alarm_payload(cls, kwargs)
            try:
                result = await self._client.request(
                    "PUT", f"/classes/{cls}/{alarm_id}", json=payload
                )
                self._alarms_cache.pop(object_id, None)
                merged = {
                    **kwargs,
                    **(result if isinstance(result, dict) else {}),
                    "objectId": alarm_id,
                }
                return Alarm.from_dict(merged, self._faces_by_id)
            except RemiAPIError:
                continue
        msg = f"Failed to update alarm {alarm_id}"
        raise RemiAPIError(msg)

    async def delete_alarm(self, object_id: str, alarm_id: str) -> bool:
        """Delete an alarm, trying all known classes."""
        for cls in ALARM_CLASSES:
            try:
                await self._client.request("DELETE", f"/classes/{cls}/{alarm_id}")
                self._alarms_cache.pop(object_id, None)
                return True
            except RemiAPIError:
                continue
        return False

    async def enable_alarm(self, object_id: str, alarm_id: str) -> Alarm:
        """Enable a previously disabled alarm."""
        return await self.update_alarm(object_id, alarm_id, enabled=True)

    async def disable_alarm(self, object_id: str, alarm_id: str) -> Alarm:
        """Disable an alarm without deleting it."""
        return await self.update_alarm(object_id, alarm_id, enabled=False)

    async def snooze_alarm(self, object_id: str, alarm_id: str, duration: int = 9) -> Alarm:
        """Snooze an alarm for a specified duration in minutes."""
        snooze_until = (datetime.now() + timedelta(minutes=duration)).isoformat()
        return await self.update_alarm(
            object_id, alarm_id, snoozed=True, snoozeUntil=snooze_until
        )

    async def trigger_alarm(self, object_id: str, alarm_id: str) -> dict[str, Any]:
        """Manually trigger an alarm by applying its settings to the device."""
        alarms = await self.get_alarms(object_id, refresh=True)
        alarm = next((a for a in alarms if a.object_id == alarm_id), None)
        if not alarm:
            msg = f"Alarm {alarm_id} not found"
            raise RemiAPIError(msg)
        if alarm.face:
            await self.set_face(object_id, alarm.face.name)
        if alarm.volume:
            await self.set_volume(object_id, alarm.volume)
        return {"triggered": True, "alarm_id": alarm_id}

    # -------------------------------------------------------------------------
    # Backward-compat helpers used by HA integration during migration
    # -------------------------------------------------------------------------

    @property
    def faces(self) -> dict[str, str]:
        """Deprecated: use list_faces(). Returns name -> objectId for HA compatibility."""
        return {face.name: face.object_id for face in self._faces_by_name.values()}

    async def get_remi_info(self, object_id: str, refresh: bool = False) -> dict[str, Any]:
        """Deprecated: use get_device(). Returns dict for HA compatibility."""
        device = await self.get_device(object_id, refresh=refresh)
        return {
            "temperature": device.temperature,
            "luminosity": device.luminosity,
            "name": device.name,
            "face": {"objectId": device.face.object_id} if device.face else None,
            "volume": device.volume,
            "light_min": device.light_min,
            "hour_format_24": device.hour_format_24,
            "music_mode": device.music_mode,
            "raw": device.raw,
        }
