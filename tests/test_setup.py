"""Set up the whole integration with one device of each kind, and drive it through Home Assistant.

Every platform's setup and every entity's state run against real hatch_rest_api
devices on stub shadow clients; service calls go through Home Assistant's
service layer to the devices' shadow updates.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import Future
from copy import deepcopy
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from hatch_rest_api import RestBaby, RestIot, RestMini, RestoreIot, RestoreV5, RestPlus
from hatch_rest_api.const import CUSTOM_COLOR_ID, RIOT_FLAGS_CLOCK_ON
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest
from pytest_homeassistant.common import MockConfigEntry

import custom_components
from custom_components.ha_hatch import (
    diagnostics,
    hatch_data_update_coordinator as coordinator_module,
)
from custom_components.ha_hatch.const import CONFIG_FLOW_VERSION, DOMAIN

from .conftest import FAKE_AUTH_TOKEN, StubShadowClient, build_device

EMAIL = "household@example.invalid"

ALARM = {
    "id": 9001,
    "name": "Wake up",
    "active": True,
    "enabled": True,
    "type": "alarm",
    "macAddress": "AA:00:00:00:06:00",
    "startTime": "2026-05-08T06:30:00",
    "endTime": "2026-05-08T07:00:00",
    "daysOfWeek": 62,
    "displayOrder": 1,
}


@pytest.fixture(autouse=True, scope="module")
def restrict_custom_components_path() -> Iterator[None]:
    """Limit ``custom_components`` to this repository's real directory.

    Yields:
        None, while the restricted path is active.
    """
    components_path = str(Path(__file__).parents[1] / "custom_components")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(custom_components, "__path__", [components_path])
        yield


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load this custom integration."""


class FakeScheduledRoutineApi:
    """The Hatch alarm (scheduled routine) API for one Restore 3."""

    def __init__(self) -> None:
        """Start with one alarm."""
        self.alarms = [deepcopy(ALARM)]
        self.calls: list[tuple[str, Any]] = []

    async def scheduled_routines(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Return the alarms."""
        return deepcopy(self.alarms)

    async def update_scheduled_routine_alarm_enabled(
        self, *, alarm: dict[str, Any], enabled: bool, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Record an alarm being turned on or off."""
        self.calls.append(("enabled", enabled))
        self.alarms[0]["enabled"] = enabled
        return deepcopy(self.alarms)

    async def update_scheduled_routine_alarm_wake_time(
        self, *, alarm: dict[str, Any], wake_time: Any, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Record a new wake time."""
        self.calls.append(("wake_time", wake_time))
        return deepcopy(self.alarms)

    async def update_scheduled_routine_alarm_weekdays(
        self, *, alarm: dict[str, Any], weekdays: Any, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Record new repeat days."""
        self.calls.append(("weekdays", list(weekdays)))
        return deepcopy(self.alarms)


class Household:
    """One device of each kind, as get_rest_devices would return them."""

    def __init__(self) -> None:
        """Build and populate the devices."""
        self.clients: dict[str, StubShadowClient] = {}
        self.devices: list[Any] = []
        self.alarm_api = FakeScheduledRoutineApi()

        mini = self._add(RestMini, "mini", {"connected": True, "current": {"playing": "none"}})
        plus = self._add(
            RestPlus,
            "plus",
            {
                "connected": True,
                "isPowered": True,
                "deviceInfo": {"f": "2.0", "b": 80},
                "a": {"t": 3, "v": 32768},
                "c": {"r": 65535, "g": 0, "b": 0, "i": 32768, "R": False, "W": False},
            },
        )
        riot = self._add(
            RestIot,
            "riot",
            {
                "connected": True,
                "deviceInfo": {"f": "3.0", "b": 60, "powerStatus": 3},
                "toddlerLockOn": False,
                "current": {
                    "playing": "remote",
                    "sound": {"id": 10200, "v": 30000},
                    "color": {"id": CUSTOM_COLOR_ID, "r": 0, "g": 65535, "b": 0, "i": 32768},
                },
                "clock": {"i": 32768, "flags": RIOT_FLAGS_CLOCK_ON},
            },
        )
        riot.favorites = [
            {"id": 501, "lineageKey": 501, "displayOrder": 1, "steps": [{"name": "Bedtime"}]}
        ]
        baby = self._add(RestBaby, "baby", {"connected": True, "current": {"playing": "none"}})
        restore_iot = self._add(
            RestoreIot,
            "restoreiot",
            {"connected": True, "current": {"playing": "none"}, "clock": {"i": 32768, "flags": 0}},
        )
        restore_iot.configure_alarm_api(api=MagicMock(), auth_token=FAKE_AUTH_TOKEN, alarms=[])
        v5 = self._add(
            RestoreV5,
            "v5",
            {
                "connected": True,
                "current": {"playing": "none"},
                "clock": {"i": 0x19992666, "flags": RIOT_FLAGS_CLOCK_ON, "turnOffMode": "never"},
            },
        )
        v5.configure_alarm_api(
            api=self.alarm_api, auth_token=FAKE_AUTH_TOKEN, alarms=deepcopy([ALARM])
        )
        del mini, plus, baby

    def _add(self, device_class: type, name: str, state: dict[str, Any]) -> Any:
        index = len(self.devices) + 1
        device, client = build_device(device_class, f"thing-{name}", f"AA:00:00:00:0{index}:00")
        device.device_name = name.capitalize()
        device._update_local_state(state)
        client.published.clear()
        self.clients[name] = client
        self.devices.append(device)
        return device

    async def get_rest_devices(self, **kwargs: Any) -> tuple[Any, Any, list[Any], float]:
        """Return the household like hatch_rest_api.get_rest_devices."""
        disconnected: Future[dict[str, Any]] = Future()
        disconnected.set_result({})
        connection = MagicMock()
        connection.disconnect.return_value = disconnected
        return MagicMock(), connection, self.devices, 4_102_444_800.0  # 2100-01-01


@pytest.fixture
async def loaded(hass: HomeAssistant) -> tuple[MockConfigEntry, Household]:
    """The integration set up with the household."""
    household = Household()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=EMAIL,
        unique_id=EMAIL,
        version=CONFIG_FLOW_VERSION,
        data={CONF_EMAIL: EMAIL, CONF_PASSWORD: "password"},
    )
    entry.add_to_hass(hass)
    with (
        patch.object(coordinator_module, "get_rest_devices", household.get_rest_devices),
        patch.object(coordinator_module, "async_get_clientsession"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry, household


def _entity_id(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None, f"no {platform} entity {unique_id}"
    return entity_id


def _first_entity(hass: HomeAssistant, entry: MockConfigEntry, platform: str, prefix: str) -> str:
    return next(
        registry_entry.entity_id
        for registry_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if registry_entry.domain == platform and registry_entry.unique_id.startswith(prefix)
    )


async def test_every_device_gets_entities(
    hass: HomeAssistant, loaded: tuple[MockConfigEntry, Household]
) -> None:
    """The entry loads, every platform adds entities, and each has a state."""
    entry, household = loaded
    assert entry.state is ConfigEntryState.LOADED

    entries = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    platforms = {registry_entry.domain for registry_entry in entries}
    assert {
        "light",
        "media_player",
        "switch",
        "sensor",
        "binary_sensor",
        "time",
        "number",
        "select",
        "scene",
    } <= platforms
    devices_with_entities = {registry_entry.unique_id.split("_")[0] for registry_entry in entries}
    assert {device.thing_name for device in household.devices} <= devices_with_entities
    for registry_entry in entries:
        if registry_entry.disabled_by is None:
            assert hass.states.get(registry_entry.entity_id) is not None, registry_entry.entity_id


async def test_states_reflect_the_devices(
    hass: HomeAssistant, loaded: tuple[MockConfigEntry, Household]
) -> None:
    """Entity states come from the devices' reported shadows."""
    assert hass.states.get(_entity_id(hass, "light", "thing-plus_light")).state == "on"
    assert hass.states.get(_entity_id(hass, "light", "thing-riot_light")).state == "on"
    assert hass.states.get(_entity_id(hass, "light", "thing-riot_clock")).state == "on"
    assert hass.states.get(_entity_id(hass, "switch", "thing-riot_toddler_lock")).state == "off"


async def test_entities_are_named_after_their_device(
    hass: HomeAssistant, loaded: tuple[MockConfigEntry, Household]
) -> None:
    """Names keep the "<device> <entity>" form, and follow a renamed device."""
    entry, _ = loaded
    light = _entity_id(hass, "light", "thing-plus_light")
    assert light == "light.plus_light"
    assert hass.states.get(light).attributes["friendly_name"] == "Plus Light"
    assert (
        hass.states.get(_entity_id(hass, "switch", "thing-plus_power_switch")).attributes[
            "friendly_name"
        ]
        == "Plus Power Switch"
    )
    strings = json.loads(
        (Path(__file__).parents[1] / "custom_components/ha_hatch/strings.json").read_text()
    )
    for registry_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        # A key missing from strings.json would leave the entity with just the device's name.
        if registry_entry.translation_key is not None:
            assert registry_entry.translation_key in strings["entity"][registry_entry.domain], (
                registry_entry.entity_id
            )

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device_by_identifier((DOMAIN, "thing-plus"), entry.entry_id)
    assert device is not None
    device_registry.async_update_device(device.id, name_by_user="Nursery")
    await hass.async_block_till_done()

    assert hass.states.get(light).attributes["friendly_name"] == "Nursery Light"


async def test_service_calls_reach_the_devices(
    hass: HomeAssistant, loaded: tuple[MockConfigEntry, Household]
) -> None:
    """Home Assistant service calls send the matching shadow updates."""
    _, household = loaded

    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": _entity_id(hass, "light", "thing-riot_light")},
        blocking=True,
    )
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": _entity_id(hass, "switch", "thing-riot_toddler_lock")},
        blocking=True,
    )
    await hass.services.async_call(
        "media_player",
        "volume_set",
        {
            "entity_id": _entity_id(hass, "media_player", "thing-plus_media_player"),
            "volume_level": 0.5,
        },
        blocking=True,
    )
    await hass.services.async_call(
        "scene",
        "turn_on",
        {"entity_id": _first_entity(hass, loaded[0], "scene", "thing-riot")},
        blocking=True,
    )

    riot = household.clients["riot"].published
    assert riot[0]["current"]["color"]["id"] == 9998
    assert riot[1] == {"toddlerLock": {"turnOnMode": "always"}}
    assert riot[2]["current"]["srId"] == 501
    assert household.clients["plus"].published == [{"a": {"v": 32768}}]


async def test_alarm_entities_change_the_alarm(
    hass: HomeAssistant, loaded: tuple[MockConfigEntry, Household]
) -> None:
    """A Restore 3 alarm can be switched off and have its wake time and days changed."""
    _, household = loaded
    registry = er.async_get(hass)
    alarm_switch = next(
        entry.entity_id
        for entry in er.async_entries_for_config_entry(registry, loaded[0].entry_id)
        if entry.domain == "switch"
        and entry.unique_id.startswith("thing-v5")
        and "alarm" in entry.unique_id
    )
    assert hass.states.get(alarm_switch).state == "on"

    await hass.services.async_call("switch", "turn_off", {"entity_id": alarm_switch}, blocking=True)
    await hass.services.async_call(
        DOMAIN,
        "set_alarm_weekdays",
        {"entity_id": alarm_switch, "weekdays": ["monday", "friday"]},
        blocking=True,
    )

    assert ("enabled", False) in household.alarm_api.calls
    assert ("weekdays", ["monday", "friday"]) in household.alarm_api.calls


async def test_diagnostics_cover_every_device(
    hass: HomeAssistant, loaded: tuple[MockConfigEntry, Household]
) -> None:
    """Diagnostics list each device's state, with the account redacted."""
    entry, household = loaded
    data = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

    assert data["entry"]["data"][CONF_EMAIL] == "**REDACTED**"
    assert data["entry"]["data"][CONF_PASSWORD] == "**REDACTED**"
    for device in household.devices:
        assert device.thing_name in data


async def test_unload_releases_the_devices(
    hass: HomeAssistant, loaded: tuple[MockConfigEntry, Household]
) -> None:
    """Unloading the entry unloads every platform."""
    entry, _ = loaded
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_two_accounts_keep_their_own_devices(
    hass: HomeAssistant, loaded: tuple[MockConfigEntry, Household]
) -> None:
    """A second Hatch account gets its own coordinator; unloading it leaves the first."""
    first_entry, household = loaded
    other_email = "grandparents@example.invalid"
    other_mini, _ = build_device(RestMini, "thing-other-mini", "AA:00:00:00:00:99")
    other_mini.device_name = "Grandparents"
    other_mini._update_local_state({"connected": True, "current": {"playing": "none"}})

    async def get_rest_devices(**kwargs: Any) -> tuple[Any, Any, list[Any], float]:
        session, connection, devices, expires = await household.get_rest_devices(**kwargs)
        if kwargs["email"] == other_email:
            devices = [other_mini]
        return session, connection, devices, expires

    second_entry = MockConfigEntry(
        domain=DOMAIN,
        title=other_email,
        unique_id=other_email,
        version=CONFIG_FLOW_VERSION,
        data={CONF_EMAIL: other_email, CONF_PASSWORD: "password"},
    )
    second_entry.add_to_hass(hass)
    with (
        patch.object(coordinator_module, "get_rest_devices", get_rest_devices),
        patch.object(coordinator_module, "async_get_clientsession"),
    ):
        assert await hass.config_entries.async_setup(second_entry.entry_id)
        await hass.async_block_till_done()

    assert first_entry.runtime_data is not second_entry.runtime_data
    assert first_entry.runtime_data.rest_devices == household.devices
    assert second_entry.runtime_data.rest_devices == [other_mini]
    first_entity = _first_entity(hass, first_entry, "media_player", "thing-mini")
    second_entity = _first_entity(hass, second_entry, "media_player", "thing-other-mini")

    assert await hass.config_entries.async_unload(second_entry.entry_id)
    await hass.async_block_till_done()

    assert first_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(first_entity).state != "unavailable"
    assert hass.states.get(second_entity).state == "unavailable"
