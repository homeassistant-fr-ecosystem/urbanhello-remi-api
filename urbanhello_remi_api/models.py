"""Data models for the UrbanHello Rémi API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class RemiAPIError(Exception):
    """Generic exception for RemiAPI failures."""


class RemiAPIAuthError(RemiAPIError):
    """Exception for authentication failures (HTTP 401)."""


@dataclass
class Face:
    """Represents a Rémi display face."""

    object_id: str
    name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Face:
        """Construct a Face from a Parse API dict."""
        return cls(
            object_id=data.get("objectId", ""),
            name=data.get("name", ""),
        )


@dataclass
class RemiDevice:  # pylint: disable=too-many-instance-attributes
    """Represents a physical Rémi baby-monitor device."""

    object_id: str
    name: str
    temperature: float | None
    luminosity: int | None
    volume: int | None
    light_min: int | None
    hour_format_24: bool | None
    music_mode: int | None
    face: Face | None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], faces_by_id: dict[str, str]) -> RemiDevice:
        """Construct a RemiDevice from a Parse API dict."""
        raw_temp = data.get("temp")
        temperature = (raw_temp + 40) if raw_temp is not None else None

        face: Face | None = None
        face_data = data.get("face")
        if isinstance(face_data, dict):
            face_id = face_data.get("objectId")
            if face_id:
                face_name = faces_by_id.get(face_id, "")
                face = Face(object_id=face_id, name=face_name)

        return cls(
            object_id=data.get("objectId", ""),
            name=data.get("name", ""),
            temperature=temperature,
            luminosity=data.get("luminosity"),
            volume=data.get("volume"),
            light_min=data.get("light_min"),
            hour_format_24=data.get("hourFormat24"),
            music_mode=data.get("musicMode"),
            face=face,
            raw=data,
        )


@dataclass
class Alarm:  # pylint: disable=too-many-instance-attributes
    """Represents a scheduled alarm on a Rémi device."""

    object_id: str
    name: str
    time: str
    enabled: bool
    days: list[int]
    recurrence: list[int]
    brightness: int
    volume: int
    cmd: int
    length_min: int
    face: Face | None
    lightnight: list[int]

    @classmethod
    def from_dict(cls, data: dict[str, Any], faces_by_id: dict[str, str]) -> Alarm:
        """Construct an Alarm from a Parse API dict."""
        event_time = data.get("event_time", [0, 0])
        time_str = (
            f"{event_time[0]:02d}:{event_time[1]:02d}"
            if len(event_time) >= 2
            else "00:00"
        )

        recurrence = data.get("recurrence", [0] * 7)
        days = [i for i, enabled in enumerate(recurrence) if enabled]

        face: Face | None = None
        face_data = data.get("face")
        if isinstance(face_data, dict):
            face_id = face_data.get("objectId")
            if face_id:
                face_name = faces_by_id.get(face_id, "")
                face = Face(object_id=face_id, name=face_name)

        return cls(
            object_id=data.get("objectId", ""),
            name=data.get("name", f"Event {time_str}"),
            time=time_str,
            enabled=data.get("enabled", False),
            days=days,
            recurrence=recurrence,
            brightness=data.get("brightness", 100),
            volume=data.get("volume", 0),
            cmd=data.get("cmd", 0),
            length_min=data.get("length_min", 0),
            face=face,
            lightnight=data.get("lightnight", [255, 255, 255]),
        )
