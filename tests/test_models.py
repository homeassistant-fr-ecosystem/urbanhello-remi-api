"""Tests for the data model classes (Face, RemiDevice, Alarm)."""

from __future__ import annotations

from urbanhello_remi_api.models import Alarm, Face, RemiAPIAuthError, RemiAPIError, RemiDevice


def test_face_from_dict():
    """Face.from_dict should map objectId and name correctly."""
    data = {"objectId": "abc123", "name": "sleepyFace"}
    face = Face.from_dict(data)
    assert face.object_id == "abc123"
    assert face.name == "sleepyFace"


def test_face_from_dict_missing_fields():
    """Face.from_dict should default to empty strings for missing fields."""
    face = Face.from_dict({})
    assert face.object_id == ""
    assert face.name == ""


def test_remi_device_from_dict_normalizes_temperature():
    """RemiDevice.from_dict should offset raw temp by +40 and resolve the face."""
    data = {
        "objectId": "dev1",
        "name": "Rémi Chambre",
        "temp": 0,
        "luminosity": 50,
        "volume": 80,
        "light_min": 10,
        "hourFormat24": True,
        "musicMode": 1,
        "face": {"__type": "Pointer", "className": "Face", "objectId": "faceId1"},
    }
    faces_by_id = {"faceId1": "sleepyFace"}
    device = RemiDevice.from_dict(data, faces_by_id)
    assert device.object_id == "dev1"
    assert device.name == "Rémi Chambre"
    assert device.temperature == 40  # 0 + 40
    assert device.luminosity == 50
    assert device.volume == 80
    assert device.light_min == 10
    assert device.hour_format_24 is True
    assert device.music_mode == 1
    assert device.face is not None
    assert device.face.object_id == "faceId1"
    assert device.face.name == "sleepyFace"


def test_remi_device_from_dict_null_temp():
    """RemiDevice.from_dict should set temperature to None when absent."""
    data = {"objectId": "dev2", "name": "Rémi"}
    device = RemiDevice.from_dict(data, {})
    assert device.temperature is None


def test_remi_device_from_dict_negative_temp():
    """RemiDevice.from_dict should handle negative raw temp values."""
    data = {"objectId": "dev3", "name": "Rémi", "temp": -10}
    device = RemiDevice.from_dict(data, {})
    assert device.temperature == 30  # -10 + 40


def test_remi_device_raw_preserved():
    """RemiDevice.from_dict should preserve the full raw dict."""
    data = {"objectId": "dev4", "name": "Rémi", "current_firmware_version": "1.2.3"}
    device = RemiDevice.from_dict(data, {})
    assert device.raw["current_firmware_version"] == "1.2.3"


def test_alarm_from_dict_converts_recurrence_to_days():
    """Alarm.from_dict should convert recurrence list to day indices."""
    data = {
        "objectId": "alarm1",
        "name": "Réveil",
        "event_time": [7, 30],
        "enabled": True,
        "recurrence": [1, 1, 1, 1, 1, 0, 0],
        "brightness": 80,
        "volume": 50,
        "cmd": 1,
        "length_min": 15,
        "lightnight": [255, 200, 100],
    }
    alarm = Alarm.from_dict(data, {})
    assert alarm.object_id == "alarm1"
    assert alarm.time == "07:30"
    assert alarm.enabled is True
    assert alarm.days == [0, 1, 2, 3, 4]
    assert alarm.recurrence == [1, 1, 1, 1, 1, 0, 0]
    assert alarm.brightness == 80
    assert alarm.volume == 50
    assert alarm.lightnight == [255, 200, 100]


def test_alarm_from_dict_face_resolved():
    """Alarm.from_dict should resolve face pointer to a Face object."""
    data = {
        "objectId": "alarm2",
        "event_time": [8, 0],
        "face": {"objectId": "faceId1"},
    }
    faces_by_id = {"faceId1": "awakeFace"}
    alarm = Alarm.from_dict(data, faces_by_id)
    assert alarm.face is not None
    assert alarm.face.object_id == "faceId1"
    assert alarm.face.name == "awakeFace"


def test_alarm_default_time_on_empty_event_time():
    """Alarm.from_dict should default to 00:00 when event_time is absent."""
    data = {"objectId": "alarm3"}
    alarm = Alarm.from_dict(data, {})
    assert alarm.time == "00:00"


def test_remiapierror_hierarchy():
    """RemiAPIAuthError should be a subclass of RemiAPIError and Exception."""
    err = RemiAPIAuthError("bad token")
    assert isinstance(err, RemiAPIError)
    assert isinstance(err, Exception)
