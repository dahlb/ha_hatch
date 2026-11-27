"""Shared fixtures: an original Hatch Restore with its MQTT shadow and alarm API stubbed.

The device is a real hatch_rest_api Restore, so the payloads the tests see are
the ones it would send. All ids, MAC addresses and names are made up.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from concurrent.futures import Future
from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from hatch_rest_api import RestDevice, Restore
import pytest

from custom_components.ha_hatch.favorite_slots import FavoriteSlots
from custom_components.ha_hatch.hatch_data_update_coordinator import HatchDataUpdateCoordinator
from custom_components.ha_hatch.restore_alarm_slots import RestoreAlarmSlots

FAKE_AUTH_TOKEN = "token"
RESTORE_MAC = "11:22:33:44:55:66"
RESTORE_THING = "thing-restore"
RESTORE_STATE: dict[str, Any] = {
    "connected": True,
    "rssi": -44,
    "timezone": "America/New_York",
    "deviceInfo": {"f": "3.2.1", "fR": 1, "hwVersion": "R1"},
    "content": {
        "playing": "routine",
        "step": 2,
        "routineId": 501,
        "paused": False,
        "requested": {"alarms": {"ids": [1002], "status": "success", "reason": "ok"}},
    },
    "sound": {"id": 10033, "v": 19660, "enabled": True},
    "color": {"id": 218, "i": 32767, "enabled": True},
    "deviceDefaults": {"colorId": 229, "i": 32767, "soundId": 10040, "v": 0},
    "restoreClock": {
        "flags": 32768,
        "i": 2621,
        "turnOnAt": "07:00:00",
        "turnOffAt": "22:00:00",
        "turnOffMode": "never",
    },
    "alarmsDisabled": False,
    "headphones": {
        "requestedPin": "1234",
        "connectedMacAddress": "00:11:22:33:44:55",
        "stateResult": "unknown",
    },
}
RESTORE_ROUTINES: list[dict[str, Any]] = [
    {
        "id": 501,
        "type": "routine",
        "name": "Bedtime",
        "steps": [{"name": "Read"}, {"name": "Dim"}, {"name": "Sleep"}],
    }
]
SATURDAY_ALARM: dict[str, Any] = {
    "id": 1001,
    "active": True,
    "enabled": False,
    "daysOfWeek": 64,
    "time": "2026-01-03 08:30:00",
    "absoluteTime": 1767447000000,
    "color": {"duration": 1800, "i": 65535, "id": 29, "until": "duration"},
    "colorStartsEarly": True,
    "isExpiredOneOff": False,
    "macAddress": RESTORE_MAC,
    "sound": {"id": 10024, "v": 65535},
}
WEEKDAY_ALARM: dict[str, Any] = {
    **SATURDAY_ALARM,
    "id": 1002,
    "enabled": True,
    "daysOfWeek": 62,
    "time": "2026-01-05 07:00:00",
    "color": {"duration": 1800, "i": 65535, "id": 27, "until": "duration"},
}


def _done(result: Any = None) -> Future:
    """Return a future that has already resolved to ``result``.

    Args:
        result: The future's result.

    Returns:
        The resolved future.
    """
    future: Future = Future()
    future.set_result(result)
    return future


class StubShadowClient:
    """IotShadowClient stub that records each desired state.

    Like the device, it confirms every alarm id list it is sent.
    """

    def __init__(self) -> None:
        """Start with nothing published."""
        self.published: list[dict[str, Any]] = []
        self.update_callback: Callable[[Any], None] | None = None
        self.version = 1

    def subscribe_to_update_shadow_accepted(
        self, request: Any, qos: Any, callback: Callable[[Any], None]
    ) -> tuple[Future, str]:
        """Keep the update callback, to confirm alarm id lists through.

        Args:
            request: The subscription request.
            qos: The MQTT quality of service.
            callback: The device's update handler.

        Returns:
            A resolved future and the topic.
        """
        self.update_callback = callback
        return _done(), "update-topic"

    def subscribe_to_get_shadow_accepted(
        self, request: Any, qos: Any, callback: Callable[[Any], None]
    ) -> tuple[Future, str]:
        """Accept the subscription.

        Args:
            request: The subscription request.
            qos: The MQTT quality of service.
            callback: The device's get handler.

        Returns:
            A resolved future and the topic.
        """
        return _done(), "get-topic"

    def publish_get_shadow(self, request: Any, qos: Any) -> Future:
        """Accept the get request.

        Args:
            request: The get request.
            qos: The MQTT quality of service.

        Returns:
            A resolved future.
        """
        return _done(MagicMock())

    def publish_update_shadow(self, request: Any, qos: Any) -> Future:
        """Record the desired state, and confirm an alarm id list like the device.

        Args:
            request: The update request.
            qos: The MQTT quality of service.

        Returns:
            A resolved future.
        """
        desired = request.state.desired
        self.published.append(desired)
        ids = desired.get("content", {}).get("requested", {}).get("alarms", {}).get("ids")
        if ids is not None and self.update_callback is not None:
            self.version += 1
            reported = {"content": {"requested": {"alarms": {"ids": ids, "status": "success"}}}}
            self.update_callback(
                SimpleNamespace(version=self.version, state=SimpleNamespace(reported=reported))
            )
        return _done()


class FakeAlarmApi:
    """Hatch alarm API stand-in keeping a server-side alarm list."""

    def __init__(self, alarms: Iterable[dict[str, Any]]) -> None:
        """Hold a copy of ``alarms``.

        Args:
            alarms: The alarms on the server.
        """
        self.alarms = deepcopy(list(alarms))
        self.next_id = 5000

    async def restore_alarms(self, auth_token: str, mac: str, base_url: str) -> list[Any]:
        """Return the active alarms.

        Args:
            auth_token: Unused.
            mac: Unused.
            base_url: Unused.

        Returns:
            Copies of the active alarms.
        """
        return [deepcopy(alarm) for alarm in self.alarms if alarm.get("active", True)]

    async def create_restore_alarm(
        self, auth_token: str, alarm: dict[str, Any], base_url: str
    ) -> list[Any]:
        """Add an inactive copy of ``alarm`` under a new id, as Hatch does.

        Args:
            auth_token: Unused.
            alarm: The alarm to create.
            base_url: Unused.

        Returns:
            Every stored alarm.
        """
        self.alarms.append({**deepcopy(alarm), "id": self.next_id, "active": False})
        self.next_id += 1
        return deepcopy(self.alarms)

    async def update_restore_alarms(
        self, auth_token: str, alarms: list[dict[str, Any]], base_url: str
    ) -> list[Any]:
        """Apply ``alarms`` over the stored ones.

        Args:
            auth_token: Unused.
            alarms: The full alarm list.
            base_url: Unused.

        Returns:
            Copies of the active alarms.
        """
        sent = {alarm["id"]: alarm for alarm in alarms}
        self.alarms = [{**alarm, **sent.get(alarm["id"], {})} for alarm in self.alarms]
        return [deepcopy(alarm) for alarm in self.alarms if alarm.get("active", True)]


class FakeCoordinator:
    """The coordinator's real original Restore methods, without Home Assistant."""

    _restore_alarm_slots_store = None
    _favorite_slots_store = None
    favorites_by_slot = HatchDataUpdateCoordinator.favorites_by_slot
    last_update_success = True
    restore_alarms_by_slot = HatchDataUpdateCoordinator.restore_alarms_by_slot
    restore_alarm = HatchDataUpdateCoordinator.restore_alarm
    _restore_alarm_id = HatchDataUpdateCoordinator._restore_alarm_id
    _save_restore_alarm_slots = HatchDataUpdateCoordinator._save_restore_alarm_slots
    async_set_restore_alarm_enabled = HatchDataUpdateCoordinator.async_set_restore_alarm_enabled
    async_set_restore_alarm_schedule = HatchDataUpdateCoordinator.async_set_restore_alarm_schedule

    def __init__(self, rest_devices: list[RestDevice]) -> None:
        """Serve ``rest_devices``.

        Args:
            rest_devices: The account's devices.
        """
        self.rest_devices = rest_devices
        self.restore_alarm_slots = RestoreAlarmSlots()
        self.favorite_slots = FavoriteSlots()
        self.alarm_refresh_callbacks: list[Callable[[], Awaitable[None]]] = []

    def rest_device_by_thing_name(self, thing_name: str) -> RestDevice | None:
        """Return the device with this thing name.

        Args:
            thing_name: The AWS IoT thing name.

        Returns:
            The device, or None.
        """
        return next(
            (device for device in self.rest_devices if device.thing_name == thing_name), None
        )

    def async_add_alarm_refresh_callback(
        self, callback: Callable[[], Awaitable[None]]
    ) -> Callable[[], None]:
        """Keep a callback, to run after a simulated alarm refresh.

        Args:
            callback: Called after each alarm refresh.

        Returns:
            A no-op remover.
        """
        self.alarm_refresh_callbacks.append(callback)
        return lambda: None

    async def async_run_alarm_refresh_callbacks(self) -> None:
        """Run every callback, as the coordinator does after an alarm refresh."""
        for callback in self.alarm_refresh_callbacks:
            await callback()


@dataclass
class RestoreFixture:
    """A Restore, what it was sent, its alarm API and a coordinator serving it."""

    device: Restore
    client: StubShadowClient
    api: FakeAlarmApi
    coordinator: FakeCoordinator


def build_device(
    device_class: type[Any], thing_name: str, mac: str
) -> tuple[Any, StubShadowClient]:
    """Build a hatch_rest_api device on a stub shadow client.

    Args:
        device_class: The device class.
        thing_name: Its AWS IoT thing name.
        mac: Its MAC address.

    Returns:
        The device and its shadow client.
    """
    client = StubShadowClient()
    device = device_class(
        device_name="Bedroom", thing_name=thing_name, mac=mac, shadow_client=client
    )
    return device, client


def build_restore(alarms_loaded: bool = True) -> RestoreFixture:
    """Build a Restore that has reported RESTORE_STATE and holds two alarms.

    Args:
        alarms_loaded: False for a device whose first alarm fetch failed.

    Returns:
        The fixture.
    """
    device, client = build_device(Restore, RESTORE_THING, RESTORE_MAC)
    device._update_local_state(deepcopy(RESTORE_STATE))
    device.routines = deepcopy(RESTORE_ROUTINES)
    alarms = [deepcopy(SATURDAY_ALARM), deepcopy(WEEKDAY_ALARM)]
    api = FakeAlarmApi(alarms)
    device.configure_alarm_api(
        api=api, auth_token=FAKE_AUTH_TOKEN, alarms=deepcopy(alarms) if alarms_loaded else None
    )
    return RestoreFixture(device, client, api, FakeCoordinator([device]))


@pytest.fixture
def restore() -> RestoreFixture:
    """An original Restore with its alarms loaded.

    Returns:
        The fixture.
    """
    return build_restore()
