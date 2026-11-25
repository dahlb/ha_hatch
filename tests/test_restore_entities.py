"""Tests for the original Hatch Restore entities and their platform setup.

Every platform's setup runs against a real hatch_rest_api Restore whose MQTT
shadow and alarm API are stubbed (see conftest.py), so the assertions are on
the payloads the device would really be sent.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import time
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from hatch_rest_api.util import convert_from_percentage
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_EFFECT
from homeassistant.components.media_player import MediaPlayerState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
import pytest

from custom_components.ha_hatch import (
    binary_sensor,
    light,
    media_player,
    number,
    restore_entities,
    scene,
    select,
    sensor,
    switch,
    time as time_platform,
)
from custom_components.ha_hatch.const import DOMAIN

from .conftest import (
    RESTORE_THING,
    SATURDAY_ALARM,
    WEEKDAY_ALARM,
    FakeCoordinator,
    RestoreFixture,
    build_restore,
)

THING = RESTORE_THING
REMOTE = {"playing": "remote", "paused": False, "offset": 0, "step": 0}
PLATFORMS: dict[str, ModuleType] = {
    "binary_sensor": binary_sensor,
    "light": light,
    "media_player": media_player,
    "number": number,
    "scene": scene,
    "select": select,
    "sensor": sensor,
    "switch": switch,
    "time": time_platform,
}
Added = dict[str, list[Any]]


def _registry_patches() -> tuple[Any, Any]:
    """Patch out the entity registry the alarm reconciler prunes.

    Returns:
        Two patchers, for ``er.async_get`` and ``er.async_entries_for_config_entry``.
    """
    return (
        patch.object(restore_entities.er, "async_get", return_value=MagicMock()),
        patch.object(restore_entities.er, "async_entries_for_config_entry", return_value=[]),
    )


async def _set_up_platforms(coordinator: FakeCoordinator) -> Added:
    """Run every platform's async_setup_entry.

    Args:
        coordinator: The coordinator the platforms read devices from.

    Returns:
        The entities each platform added.
    """
    hass = SimpleNamespace(data={DOMAIN: coordinator})
    config_entry = SimpleNamespace(
        options={}, entry_id="entry-1", async_on_unload=lambda remove: None
    )
    added: Added = {}
    registry_get, registry_entries = _registry_patches()
    # The scheduled-routine alarm reconcilers prune the entity registry, and the
    # custom sounds loader reads the config directory; both need a real hass.
    with (
        registry_get,
        registry_entries,
        patch.object(media_player, "async_load_custom_sounds", AsyncMock(return_value={})),
        patch.object(switch, "remove_stale_alarm_entities"),
        patch.object(switch, "update_alarm_entity_names"),
        patch.object(sensor, "remove_stale_alarm_entities"),
        patch.object(sensor, "update_alarm_entity_names"),
        patch.object(time_platform, "remove_stale_alarm_entities"),
        patch.object(time_platform, "update_alarm_entity_names"),
    ):
        for name, platform in PLATFORMS.items():
            added[name] = []
            await platform.async_setup_entry(hass, config_entry, added[name].extend)
    return added


async def _run_alarm_refresh_callbacks(coordinator: FakeCoordinator) -> None:
    """Run the alarm reconcilers, as the coordinator does after a refresh.

    Args:
        coordinator: The coordinator holding the callbacks.
    """
    registry_get, registry_entries = _registry_patches()
    with registry_get, registry_entries:
        await coordinator.async_run_alarm_refresh_callbacks()


def _entity(added: Added, platform: str, unique_id: str) -> Any:
    """Return the entity a platform added under a unique id.

    Args:
        added: The entities by platform.
        platform: The platform.
        unique_id: The entity's unique id.

    Returns:
        The entity.
    """
    return next(entity for entity in added[platform] if entity.unique_id == unique_id)


def _unique_ids(added: Added) -> set[str]:
    """Return every added entity's unique id.

    Args:
        added: The entities by platform.

    Returns:
        The unique ids.
    """
    return {entity.unique_id for entities in added.values() for entity in entities}


@pytest.fixture
async def added(restore: RestoreFixture) -> Added:
    """Every platform set up for the Restore.

    Args:
        restore: The Restore fixture.

    Returns:
        The entities by platform.
    """
    return await _set_up_platforms(restore.coordinator)


def test_creates_the_restore_entities(added: Added) -> None:
    """Each platform creates the Restore's entities, one alarm set per alarm."""
    assert {
        platform: sorted(type(entity).__name__ for entity in entities)
        for platform, entities in added.items()
    } == {
        "binary_sensor": ["HatchOnlineSensor"],
        "light": ["RestoreClockLight", "RestoreLight"],
        "media_player": ["RestoreSound"],
        "number": [],
        "scene": [],
        "select": ["RestoreClockMode", "RestoreRoutineStep"],
        "sensor": [
            "RestoreAlarmRepeat",
            "RestoreAlarmRepeat",
            "RestoreFirmwareVersion",
            "RestorePlaying",
            "RestoreSignalStrength",
        ],
        "switch": [
            "RestoreAlarmSwitch",
            "RestoreAlarmSwitch",
            "RestoreAlarmsSwitch",
            "RestoreClock24Hour",
            "RestoreRoutineSwitch",
        ],
        "time": ["RestoreAlarmTime", "RestoreAlarmTime", "RestoreClockTime", "RestoreClockTime"],
    }


def test_unique_ids_and_alarm_names(added: Added) -> None:
    """Unique ids are stable, and alarms are numbered by time of day."""
    assert _unique_ids(added) == {
        f"{THING}_wifi",
        f"{THING}_light",
        f"{THING}_clock",
        f"{THING}_sound",
        f"{THING}_routine_step",
        f"{THING}_clock_mode",
        f"{THING}_playing",
        f"{THING}_firmware_version",
        f"{THING}_wifi_signal",
        f"{THING}_bedtime_routine",
        f"{THING}_alarms",
        f"{THING}_clock_24-hour",
        f"{THING}_clock_turn_on_at",
        f"{THING}_clock_turn_off_at",
        *(
            f"{THING}_restore_alarm_{slot}_{suffix}"
            for slot in ("1001", "1002")
            for suffix in ("switch", "time", "repeat")
        ),
    }
    # Alarm 1 goes off first in the day.
    assert _entity(added, "switch", f"{THING}_restore_alarm_1002_switch").name == "Bedroom Alarm 1"
    assert _entity(added, "switch", f"{THING}_restore_alarm_1001_switch").name == "Bedroom Alarm 2"
    assert (
        _entity(added, "time", f"{THING}_restore_alarm_1002_time").name
        == "Bedroom Alarm 1 Wake Time"
    )


def test_light(restore: RestoreFixture, added: Added) -> None:
    """The light reports its color and brightness, and changes them while on."""
    light_entity = _entity(added, "light", f"{THING}_light")
    assert light_entity.is_on
    assert light_entity.effect == "Blue"
    assert light_entity.brightness == 128
    assert "Warm White" in light_entity.effect_list

    light_entity.turn_on(**{ATTR_BRIGHTNESS: 51, ATTR_EFFECT: "Peach"})
    light_entity.turn_off()

    assert restore.client.published == [
        {"color": {"i": convert_from_percentage(20)}},
        {"color": {"id": 208}},
        {"color": {"enabled": False}},  # the sound keeps playing
    ]


def test_light_while_idle_starts_remote_playback(restore: RestoreFixture, added: Added) -> None:
    """Turning the light on while nothing plays starts remote playback."""
    restore.device._update_local_state({"content": {"playing": "none"}})
    light_entity = _entity(added, "light", f"{THING}_light")
    assert light_entity.brightness is None

    light_entity.turn_on(**{ATTR_EFFECT: "Mint"})

    assert restore.client.published[0]["content"] == REMOTE
    assert restore.client.published[0]["color"]["id"] == 214


def test_sound(restore: RestoreFixture, added: Added) -> None:
    """The sound player reports what plays and changes volume and sound."""
    sound = _entity(added, "media_player", f"{THING}_sound")
    assert sound.state == MediaPlayerState.PLAYING
    assert sound.sound_mode == "White Noise"
    assert sound.media_title == "White Noise"
    assert sound.volume_level == pytest.approx(0.3)

    sound.set_volume_level(0.15)
    sound.select_sound_mode("Fan")
    sound.media_pause()
    sound.media_stop()

    assert restore.client.published == [
        {"sound": {"v": convert_from_percentage(15)}},
        {"sound": {"id": 10019}},
        {"sound": {"enabled": False}},  # the light stays on
        {"sound": {"enabled": False}},
    ]
    with pytest.raises(ServiceValidationError):
        sound.select_sound_mode("Not a sound")


def test_sound_while_idle_shows_and_uses_the_remembered_volume(
    restore: RestoreFixture, added: Added
) -> None:
    """While idle, the player shows and starts at the last volume used."""
    restore.device._update_local_state(
        {"content": {"playing": "none"}, "sound": {"enabled": False, "v": 0}}
    )
    sound = _entity(added, "media_player", f"{THING}_sound")
    assert sound.state == MediaPlayerState.IDLE
    assert sound.media_title is None
    assert sound.volume_level == pytest.approx(0.3)

    sound.media_play()

    assert restore.client.published == [
        {
            "sound": {"enabled": True, "id": 10033, "v": convert_from_percentage(30)},
            "content": REMOTE,
            "color": {"enabled": False},
        }
    ]


def test_routine_step(restore: RestoreFixture, added: Added) -> None:
    """The routine step select lists the steps and starts the routine at one."""
    step = _entity(added, "select", f"{THING}_routine_step")
    assert step.options == ["1. Read", "2. Dim", "3. Sleep"]
    assert step.current_option == "2. Dim"

    step.select_option("3. Sleep")

    assert restore.client.published == [
        {"content": {"playing": "routine", "paused": False, "offset": 0, "step": 3}}
    ]
    restore.device._update_local_state({"content": {"playing": "none"}})
    assert step.current_option is None
    restore.device.routines = None
    assert not step.available


def test_routine_switch(restore: RestoreFixture, added: Added) -> None:
    """The routine switch is on while anything plays, and starts or stops it."""
    routine = _entity(added, "switch", f"{THING}_bedtime_routine")
    assert routine.is_on

    routine.turn_off()
    routine.turn_on()

    assert [desired["content"]["playing"] for desired in restore.client.published] == [
        "none",
        "routine",
    ]


def test_playing_sensor(restore: RestoreFixture, added: Added) -> None:
    """The playing sensor shows the playback mode and routine step."""
    playing = _entity(added, "sensor", f"{THING}_playing")
    assert playing.native_value == "routine"
    assert playing.icon == "mdi:play-circle-outline"
    assert playing.extra_state_attributes == {"step": 2, "routine_id": 501, "paused": False}

    restore.device._update_local_state({"content": {"playing": "none"}})

    assert playing.icon == "mdi:stop-circle-outline"


def test_diagnostic_sensors(added: Added) -> None:
    """The firmware and Wi-Fi signal sensors read the device."""
    assert _entity(added, "sensor", f"{THING}_firmware_version").native_value == "3.2.1"
    assert _entity(added, "sensor", f"{THING}_wifi_signal").native_value == -44


def test_clock(restore: RestoreFixture, added: Added) -> None:
    """The clock entities read and write the restoreClock settings."""
    clock = _entity(added, "light", f"{THING}_clock")
    hours_24 = _entity(added, "switch", f"{THING}_clock_24-hour")
    mode = _entity(added, "select", f"{THING}_clock_mode")
    turn_on_at = _entity(added, "time", f"{THING}_clock_turn_on_at")
    turn_off_at = _entity(added, "time", f"{THING}_clock_turn_off_at")
    assert clock.is_on
    assert clock.brightness == 10
    assert not hours_24.is_on
    assert mode.current_option == "Always On"
    assert turn_on_at.native_value == time(7, 0)
    assert turn_off_at.native_value == time(22, 0)

    clock.turn_off()
    clock.turn_on(**{ATTR_BRIGHTNESS: 102})
    hours_24.turn_on()
    hours_24.turn_off()
    mode.select_option("Off at Night")
    turn_on_at.set_value(time(6, 15))
    turn_off_at.set_value(time(21, 30))

    assert restore.client.published == [
        {"restoreClock": {"flags": 0}},
        {"restoreClock": {"flags": 32768, "i": convert_from_percentage(40)}},
        {"restoreClock": {"flags": 34816}},
        {"restoreClock": {"flags": 32768}},
        {"restoreClock": {"turnOffMode": "custom"}},
        {"restoreClock": {"turnOnAt": "06:15:00"}},
        {"restoreClock": {"turnOffAt": "21:30:00"}},
    ]


@pytest.mark.parametrize(
    ("mode", "option"), [("never", "Always On"), ("custom", "Off at Night"), ("always", None)]
)
def test_clock_mode_options(
    restore: RestoreFixture, added: Added, mode: str, option: str | None
) -> None:
    """Only the two modes this model supports map to an option."""
    restore.device._update_local_state({"restoreClock": {"turnOffMode": mode}})
    assert _entity(added, "select", f"{THING}_clock_mode").current_option == option


@pytest.mark.parametrize(("value", "expected"), [("06:30", time(6, 30)), ("", None), ("x", None)])
def test_parse_clock_time(value: str, expected: time | None) -> None:
    """Shadow clock times parse with or without seconds; junk gives None."""
    assert restore_entities.parse_clock_time(value) == expected


def test_all_alarms_switch(restore: RestoreFixture, added: Added) -> None:
    """The all-alarms switch is the inverse of alarmsDisabled."""
    alarms = _entity(added, "switch", f"{THING}_alarms")
    assert alarms.is_on

    alarms.turn_off()
    alarms.turn_on()

    assert restore.client.published == [{"alarmsDisabled": True}, {"alarmsDisabled": False}]
    restore.device.alarms_disabled = None
    assert alarms.is_on is None


def test_alarm_entities_show_the_alarm(added: Added) -> None:
    """An alarm's entities show its state, time, days and settings."""
    weekday = _entity(added, "switch", f"{THING}_restore_alarm_1002_switch")
    assert weekday.is_on
    assert _entity(added, "time", f"{THING}_restore_alarm_1002_time").native_value == time(7, 0)
    assert _entity(added, "sensor", f"{THING}_restore_alarm_1002_repeat").native_value == "Weekdays"
    attributes = weekday.extra_state_attributes
    assert attributes["sound"] == "Beep Beep"
    assert attributes["volume"] == 100
    assert attributes["sunrise"] is True
    assert attributes["sunrise_color"] == "Morning Stroll"
    assert attributes["sunrise_minutes"] == 30
    assert attributes["weekdays"] == ["monday", "tuesday", "wednesday", "thursday", "friday"]


def test_alarm_attributes_of_no_alarm() -> None:
    """No alarm, no attributes."""
    assert restore_entities.restore_alarm_attributes(None) == {}


async def test_alarm_switch_syncs_the_device_and_saves(
    restore: RestoreFixture, added: Added
) -> None:
    """Turning an alarm on loads it on the device, then saves it to Hatch."""
    saturday = _entity(added, "switch", f"{THING}_restore_alarm_1001_switch")
    saturday.async_write_ha_state = lambda: None

    await saturday.async_turn_on()

    assert restore.client.published == [
        {"content": {"requested": {"alarms": {"ids": [1001, 1002]}}}}
    ]
    assert next(alarm for alarm in restore.api.alarms if alarm["id"] == 1001)["enabled"]
    assert saturday.is_on

    await saturday.async_turn_off()

    assert not saturday.is_on


async def test_alarm_time_edit_keeps_the_same_entities(
    restore: RestoreFixture, added: Added
) -> None:
    """An edit gives the alarm a new Hatch id, but the same entities."""
    wake_time = _entity(added, "time", f"{THING}_restore_alarm_1002_time")
    wake_time.async_write_ha_state = lambda: None
    before = _unique_ids(added)

    await wake_time.async_set_value(time(6, 45))
    await _run_alarm_refresh_callbacks(restore.coordinator)

    # Hatch now knows the alarm as 5000, but it is still Alarm 1.
    assert restore.coordinator.restore_alarm_slots.alarm_id(THING, "1002") == 5000
    assert wake_time.native_value == time(6, 45)
    assert wake_time.extra_state_attributes["hatch_alarm_id"] == 5000
    assert _unique_ids(added) == before


async def test_alarm_edited_in_the_app_keeps_its_entities(
    restore: RestoreFixture, added: Added
) -> None:
    """An alarm the app replaced is matched back to its slot."""
    # The app saved a new time for the weekday alarm: new id, old one gone.
    restore.api.alarms = [
        deepcopy(SATURDAY_ALARM),
        {**deepcopy(WEEKDAY_ALARM), "id": 7000, "time": "2026-01-05 06:30:00"},
    ]

    await restore.device.refresh_alarms()

    wake_time = _entity(added, "time", f"{THING}_restore_alarm_1002_time")
    assert wake_time.native_value == time(6, 30)
    assert wake_time.available


async def test_deleted_alarm_loses_its_entities(restore: RestoreFixture, added: Added) -> None:
    """An alarm deleted in the app has its entities removed."""
    removed: list[str] = []
    for entities in added.values():
        for entity in entities:
            if "_restore_alarm_1001_" in str(entity.unique_id):

                async def remove(
                    force_remove: bool = False, unique_id: str = entity.unique_id
                ) -> None:
                    """Record the removal.

                    Args:
                        force_remove: Unused.
                        unique_id: The entity's unique id.
                    """
                    removed.append(unique_id)

                entity.async_remove = remove
    restore.api.alarms = [deepcopy(WEEKDAY_ALARM)]
    await restore.device.refresh_alarms()

    await _run_alarm_refresh_callbacks(restore.coordinator)

    assert sorted(removed) == [
        f"{THING}_restore_alarm_1001_repeat",
        f"{THING}_restore_alarm_1001_switch",
        f"{THING}_restore_alarm_1001_time",
    ]


async def test_stale_registry_entries_are_removed(restore: RestoreFixture) -> None:
    """Registry entries for slots that no longer exist are removed at setup."""
    registry = MagicMock()
    stale = SimpleNamespace(
        domain="switch", unique_id=f"{THING}_restore_alarm_999_switch", entity_id="switch.old"
    )
    with (
        patch.object(restore_entities.er, "async_get", return_value=registry),
        patch.object(restore_entities.er, "async_entries_for_config_entry", return_value=[stale]),
    ):
        await restore_entities.async_setup_restore_alarm_entities(
            MagicMock(),
            SimpleNamespace(entry_id="entry-1", async_on_unload=lambda remove: None),
            restore.coordinator,
            lambda entities: None,
            restore_entities.RestoreAlarmSwitch,
            "switch",
        )

    registry.async_remove.assert_called_once_with("switch.old")


async def test_no_alarm_entities_until_the_alarms_load() -> None:
    """Alarm entities appear once the device's alarms have loaded."""
    restore = build_restore(alarms_loaded=False)
    added = await _set_up_platforms(restore.coordinator)
    assert "RestoreAlarmSwitch" not in [type(entity).__name__ for entity in added["switch"]]

    await restore.device.refresh_alarms()
    await _run_alarm_refresh_callbacks(restore.coordinator)

    assert "RestoreAlarmSwitch" in [type(entity).__name__ for entity in added["switch"]]


def test_entities_go_unavailable_when_the_device_does(
    restore: RestoreFixture, added: Added
) -> None:
    """Without the device, entities are unavailable and refuse commands."""
    light_entity = _entity(added, "light", f"{THING}_light")
    step = _entity(added, "select", f"{THING}_routine_step")
    alarm = _entity(added, "switch", f"{THING}_restore_alarm_1002_switch")
    restore.coordinator.rest_devices = []

    assert not light_entity.available
    assert not alarm.available
    assert step.options == []
    with pytest.raises(HomeAssistantError):
        light_entity.turn_off()


def test_firmware_follows_onto_the_device_card(added: Added) -> None:
    """Reported firmware is written onto the device card, from the event loop."""
    firmware = _entity(added, "sensor", f"{THING}_firmware_version")
    firmware.hass = MagicMock()
    firmware.device_entry = SimpleNamespace(id="device-1")
    device_registry = MagicMock()
    device_registry.async_get.return_value = MagicMock(
        spec=dr.DeviceEntry, id="device-1", sw_version=None
    )

    with patch.object(restore_entities.dr, "async_get", return_value=device_registry):
        firmware._handle_coordinator_update()
        scheduled = firmware.hass.loop.call_soon_threadsafe.call_args_list[0].args[0]
        scheduled()

    device_registry.async_update_device.assert_called_once_with("device-1", sw_version="3.2.1")


def test_firmware_already_on_the_device_card(added: Added) -> None:
    """Nothing is written when the device card already has the firmware."""
    firmware = _entity(added, "sensor", f"{THING}_firmware_version")
    firmware.hass = MagicMock()
    firmware.device_entry = SimpleNamespace(id="device-1")
    device_registry = MagicMock()
    device_registry.async_get.return_value = MagicMock(spec=dr.DeviceEntry, sw_version="3.2.1")

    with patch.object(restore_entities.dr, "async_get", return_value=device_registry):
        firmware._async_sync_device_firmware()

    device_registry.async_update_device.assert_not_called()


@pytest.mark.parametrize(("brightness", "percent"), [(0, 1), (128, 50), (255, 100)])
def test_brightness_to_percent(brightness: int, percent: int) -> None:
    """Home Assistant brightness maps to 1-100 percent."""
    assert restore_entities.brightness_to_percent(brightness) == percent
