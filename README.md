# urbanhello-remi-api

Async Python wrapper for the [UrbanHello Rémi](https://www.urbanhello.com/) smart baby clock API.

[![Pylint](https://github.com/homeassistant-fr-ecosystem/urbanhello-remi-api/actions/workflows/pylint.yml/badge.svg)](https://github.com/homeassistant-fr-ecosystem/urbanhello-remi-api/actions/workflows/pylint.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

## Overview

`urbanhello-remi-api` provides a fully async, typed Python client for controlling Rémi devices via the UrbanHello Parse backend. It is the library used by the [urbanhello_remi_hass](../urbanhello_remi_hass) Home Assistant integration.

Features:
- Async/await API built on `aiohttp`
- Full type annotations with typed dataclass models
- Device control (brightness, volume, face, sound)
- Alarm management (create, update, delete, enable/disable, snooze, trigger)
- In-memory device cache with configurable TTL
- Automatic GET-to-POST fallback on timeout

## Requirements

- Python 3.11+
- `aiohttp >= 3.9`

## Installation

```bash
pip install urbanhello-remi-api
```

## Quick start

```python
import asyncio
from urbanhello_remi_api import RemiAPI

async def main():
    api = RemiAPI("your@email.com", "yourpassword")
    await api.login()

    devices = await api.list_devices()
    for device in devices:
        print(f"{device.name}: {device.temperature}°C, volume={device.volume}")

    device_id = devices[0].object_id

    # Device control
    await api.set_brightness(device_id, 80)
    await api.set_volume(device_id, 50)
    await api.turn_on(device_id)   # sets sleepyFace
    await api.turn_off(device_id)  # sets awakeFace

    # Alarm management
    alarms = await api.get_alarms(device_id)
    for alarm in alarms:
        print(f"{alarm.name} at {alarm.time}, days={alarm.days}, enabled={alarm.enabled}")

    await api.logout()

asyncio.run(main())
```

## API reference

### `RemiAPI(username, password, session=None, cache_duration=60, request_timeout=15)`

Main entry point. All methods are `async`.

#### Authentication

| Method | Description |
|--------|-------------|
| `login()` | Authenticate, populate devices and faces |
| `logout()` | Invalidate the session token |

#### Device reads

| Method | Description |
|--------|-------------|
| `list_devices()` | Return all Rémi devices as `list[RemiDevice]` |
| `get_device(object_id, refresh=False)` | Fetch one device, cached by default |
| `list_faces(refresh=False)` | Return available display faces as `list[Face]` |

#### Device control

| Method | Description |
|--------|-------------|
| `set_brightness(object_id, brightness)` | Screen brightness (0–100) |
| `set_night_luminosity(object_id, level)` | Minimum night-light brightness |
| `set_volume(object_id, level)` | Speaker volume (0–100) |
| `set_noise_threshold(object_id, threshold)` | Noise detection threshold |
| `set_clock_format(object_id, use_24h)` | Switch between 12h/24h clock |
| `set_music_mode(object_id, mode)` | Music playback mode |
| `set_face(object_id, face_name)` | Set display face (snake_case or camelCase) |
| `turn_on(object_id)` | Shortcut — sets `sleepyFace` |
| `turn_off(object_id)` | Shortcut — sets `awakeFace` |
| `play_media(object_id, sound, volume=None)` | Play a sound, optionally at a given volume |
| `stop_sound(object_id)` | Stop the current sound |

#### Alarm management

| Method | Description |
|--------|-------------|
| `get_alarms(object_id, refresh=False)` | List alarms for a device |
| `create_alarm(object_id, alarm_time, **kwargs)` | Create an alarm (`alarm_time` as `"HH:MM"`) |
| `update_alarm(object_id, alarm_id, **kwargs)` | Update alarm fields |
| `delete_alarm(object_id, alarm_id)` | Delete an alarm, returns `True` on success |
| `enable_alarm(object_id, alarm_id)` | Enable a disabled alarm |
| `disable_alarm(object_id, alarm_id)` | Disable an alarm without deleting it |
| `snooze_alarm(object_id, alarm_id, duration=9)` | Snooze for `duration` minutes |
| `trigger_alarm(object_id, alarm_id)` | Manually apply alarm settings to the device |

### Data models

#### `RemiDevice`

| Field | Type | Description |
|-------|------|-------------|
| `object_id` | `str` | Parse object ID |
| `name` | `str` | Device name |
| `temperature` | `float \| None` | Ambient temperature in °C (raw value + 40 offset) |
| `luminosity` | `int \| None` | Current screen brightness |
| `volume` | `int \| None` | Current speaker volume |
| `light_min` | `int \| None` | Minimum night-light brightness |
| `hour_format_24` | `bool \| None` | `True` if 24h clock is active |
| `music_mode` | `int \| None` | Current music mode |
| `face` | `Face \| None` | Currently displayed face |
| `raw` | `dict` | Raw Parse API response |

#### `Alarm`

| Field | Type | Description |
|-------|------|-------------|
| `object_id` | `str` | Parse object ID |
| `name` | `str` | Alarm label |
| `time` | `str` | Alarm time as `"HH:MM"` |
| `enabled` | `bool` | Whether the alarm is active |
| `days` | `list[int]` | Active weekday indices (0=Mon … 6=Sun) |
| `recurrence` | `list[int]` | Raw 7-element bitmask |
| `brightness` | `int` | Screen brightness at alarm time |
| `volume` | `int` | Volume at alarm time |
| `cmd` | `int` | Alarm command type |
| `length_min` | `int` | Alarm duration in minutes |
| `face` | `Face \| None` | Face displayed at alarm time |
| `lightnight` | `list[int]` | Night-light RGB colour `[R, G, B]` |

#### `Face`

| Field | Type | Description |
|-------|------|-------------|
| `object_id` | `str` | Parse object ID |
| `name` | `str` | Face name (e.g. `sleepyFace`, `awakeFace`) |

## Face names

Built-in snake_case aliases are automatically mapped to the API camelCase names:

| Snake case | API name |
|------------|----------|
| `sleepy_face` | `sleepyFace` |
| `awake_face` | `awakeFace` |
| `blank_face` | `blankFace` |
| `semi_awake_face` | `semiAwakeFace` |
| `smily_face` | `smilyFace` |

## Development

```bash
# Create a virtual environment and install dev dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
pylint urbanhello_remi_api/ tests/
```

## License

GPL v3 — see [LICENSE](LICENSE) for details.
