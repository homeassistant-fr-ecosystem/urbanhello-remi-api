# pylint: disable=duplicate-code
"""Tests for the RemiAPI high-level wrapper."""

from __future__ import annotations

import pytest

from urbanhello_remi_api.models import Alarm, Face, RemiAPIError, RemiDevice

BASE_URL = "https://remi2.urbanhello.com/parse"

LOGIN_RESPONSE = {
    "sessionToken": "tok123",
    "remis": [{"objectId": "remi1", "name": "Rémi Chambre"}],
}

REMI_RESPONSE = {
    "objectId": "remi1",
    "name": "Rémi Chambre",
    "temp": 5,
    "luminosity": 300,
    "volume": 70,
    "light_min": 20,
    "hourFormat24": True,
    "musicMode": 0,
}

FACES_RESPONSE = {
    "results": [
        {"objectId": "f1", "name": "sleepyFace"},
        {"objectId": "f2", "name": "awakeFace"},
    ]
}

ALARM_RESPONSE = {
    "results": [
        {
            "objectId": "alarm1",
            "name": "Réveil",
            "event_time": [7, 0],
            "enabled": True,
            "recurrence": [1, 1, 1, 1, 1, 0, 0],
            "brightness": 80,
            "volume": 50,
            "cmd": 1,
            "length_min": 10,
            "lightnight": [255, 255, 255],
        }
    ]
}


async def test_login_populates_remis(api, mock_aiohttp):
    """Login should populate remis from the login response."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    await api.login()
    assert len(api.remis) == 1
    assert api.remis[0]["objectId"] == "remi1"


async def test_list_devices_returns_remi_device(api, mock_aiohttp):
    """list_devices should return typed RemiDevice objects."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    mock_aiohttp.get(
        f"{BASE_URL}/classes/Remi",
        payload={"results": [REMI_RESPONSE]},
    )
    await api.login()
    devices = await api.list_devices(refresh=True)
    assert len(devices) == 1
    assert isinstance(devices[0], RemiDevice)
    assert devices[0].object_id == "remi1"
    assert devices[0].temperature == 45  # 5 + 40


async def test_get_device_returns_remi_device(api, mock_aiohttp):
    """get_device should return a fully populated RemiDevice."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Remi/remi1", payload=REMI_RESPONSE)
    await api.login()
    device = await api.get_device("remi1", refresh=True)
    assert isinstance(device, RemiDevice)
    assert device.name == "Rémi Chambre"
    assert device.luminosity == 300


async def test_get_device_uses_cache(api, mock_aiohttp):
    """Second get_device call should hit cache without a new HTTP request."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Remi/remi1", payload=REMI_RESPONSE)
    await api.login()
    await api.get_device("remi1", refresh=True)
    # Second call should use cache — no additional HTTP mock needed
    device = await api.get_device("remi1")
    assert device.name == "Rémi Chambre"


async def test_set_brightness_sends_put(api, mock_aiohttp):
    """set_brightness should issue a PUT to the device endpoint."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    mock_aiohttp.put(f"{BASE_URL}/classes/Remi/remi1", payload={"updatedAt": "2024"})
    await api.login()
    await api.set_brightness("remi1", 75)


async def test_set_brightness_invalidates_cache(api, mock_aiohttp):
    """set_brightness should invalidate the device cache so next fetch is fresh."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Remi/remi1", payload=REMI_RESPONSE)
    mock_aiohttp.put(f"{BASE_URL}/classes/Remi/remi1", payload={"updatedAt": "2024"})
    mock_aiohttp.get(f"{BASE_URL}/classes/Remi/remi1", payload={**REMI_RESPONSE, "luminosity": 99})
    await api.login()
    await api.get_device("remi1", refresh=True)
    await api.set_brightness("remi1", 75)
    device = await api.get_device("remi1")  # cache invalidated, fetches fresh
    assert device.luminosity == 99


async def test_list_faces_returns_face_objects(api, mock_aiohttp):
    """list_faces should return typed Face objects."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    await api.login()
    faces = await api.list_faces()
    assert len(faces) == 2
    assert all(isinstance(f, Face) for f in faces)
    assert faces[0].name == "sleepyFace"


async def test_get_alarms_returns_alarm_objects(api, mock_aiohttp):
    """get_alarms should return typed Alarm objects with converted fields."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Event", payload=ALARM_RESPONSE)
    await api.login()
    alarms = await api.get_alarms("remi1", refresh=True)
    assert len(alarms) == 1
    assert isinstance(alarms[0], Alarm)
    assert alarms[0].time == "07:00"
    assert alarms[0].days == [0, 1, 2, 3, 4]


async def test_create_alarm_returns_alarm(api, mock_aiohttp):
    """create_alarm should post to the Event class and return an Alarm."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    mock_aiohttp.post(
        f"{BASE_URL}/classes/Event",
        payload={
            "objectId": "alarm2",
            "event_time": [8, 0],
            "enabled": True,
            "recurrence": [1] * 7,
        },
    )
    await api.login()
    alarm = await api.create_alarm("remi1", "08:00")
    assert isinstance(alarm, Alarm)
    assert alarm.time == "08:00"


async def test_delete_alarm_returns_true(api, mock_aiohttp):
    """delete_alarm should return True on success."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    mock_aiohttp.delete(f"{BASE_URL}/classes/Event/alarm1", payload={})
    await api.login()
    result = await api.delete_alarm("remi1", "alarm1")
    assert result is True


async def test_turn_on_uses_sleepy_face(api, mock_aiohttp):
    """turn_on should set the sleepyFace on the device."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload=LOGIN_RESPONSE)
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload=FACES_RESPONSE)
    mock_aiohttp.put(f"{BASE_URL}/classes/Remi/remi1", payload={"updatedAt": "2024"})
    await api.login()
    await api.turn_on("remi1")


async def test_turn_on_raises_if_sleepy_face_missing(api, mock_aiohttp):
    """turn_on should raise RemiAPIError when sleepyFace is not in the face list."""
    mock_aiohttp.post(f"{BASE_URL}/login", payload={"sessionToken": "tok", "remis": []})
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload={"results": []})
    mock_aiohttp.get(f"{BASE_URL}/classes/Face", payload={"results": []})
    await api.login()
    with pytest.raises(RemiAPIError, match="sleepyFace"):
        await api.turn_on("remi1")
