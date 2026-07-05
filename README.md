# urbanhello-remi-api

Async Python wrapper for the UrbanHello Rémi clock API.

## Installation

pip install urbanhello-remi-api

## Usage

```python
import asyncio
from urbanhello_remi_api import RemiAPI

async def main():
    api = RemiAPI("your@email.com", "yourpassword")
    await api.login()

    devices = await api.list_devices()
    for device in devices:
        print(f"{device.name}: {device.temperature}°C, volume={device.volume}")

    # Control a device
    await api.set_brightness(devices[0].object_id, 80)
    await api.turn_on(devices[0].object_id)

    # Alarms
    alarms = await api.get_alarms(devices[0].object_id)
    for alarm in alarms:
        print(f"Alarm {alarm.name} at {alarm.time}, enabled={alarm.enabled}")

    await api.logout()

asyncio.run(main())
```

## License

MIT
