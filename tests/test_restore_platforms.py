"""The original Hatch Restore (product ``restore``) across every platform.

Runs each platform's setup against a real hatch_rest_api Restore whose MQTT
shadow client and alarm API are stubbed out. Needs homeassistant and
hatch_rest_api from requirements.txt; skipped without them, like a checkout
with no dev install. All ids, MAC addresses and names are made up.
"""

import asyncio
import sys
import unittest
from concurrent.futures import Future
from copy import deepcopy
from datetime import time
from importlib.util import find_spec
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parents[1]))

HAS_DEPENDENCIES = all(
    find_spec(name) is not None for name in ("homeassistant", "hatch_rest_api")
)

if HAS_DEPENDENCIES:
    from hatch_rest_api import RestMini, Restore
    from hatch_rest_api.util import convert_from_percentage
    from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_EFFECT
    from homeassistant.components.media_player import MediaPlayerState
    from homeassistant.helpers.entity import Entity

    from custom_components.ha_hatch import (
        binary_sensor,
        diagnostics,
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
    from custom_components.ha_hatch.hatch_data_update_coordinator import HatchDataUpdateCoordinator
    from custom_components.ha_hatch.media_rest_entity import MediaRestEntity
    from custom_components.ha_hatch.restore_alarm_slots import RestoreAlarmSlots

    PLATFORMS = {
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

MAC = "11:22:33:44:55:66"
THING = "thing-restore"
REMOTE = {"playing": "remote", "paused": False, "offset": 0, "step": 0}
STOP = {"playing": "none", "paused": False, "offset": 0, "step": 0}

RESTORE_STATE = {
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
ROUTINES = [
    {"id": 501, "type": "routine", "name": "Bedtime", "steps": [{"name": "Read"}, {"name": "Dim"}, {"name": "Sleep"}]}
]
SATURDAY_ALARM = {
    "id": 1001,
    "active": True,
    "enabled": False,
    "daysOfWeek": 64,
    "time": "2026-01-03 08:30:00",
    "absoluteTime": 1767447000000,
    "color": {"duration": 1800, "i": 65535, "id": 29, "until": "duration"},
    "colorStartsEarly": True,
    "isExpiredOneOff": False,
    "macAddress": MAC,
    "sound": {"id": 10024, "v": 65535},
}
WEEKDAY_ALARM = {
    **SATURDAY_ALARM,
    "id": 1002,
    "enabled": True,
    "daysOfWeek": 62,
    "time": "2026-01-05 07:00:00",
    "color": {"duration": 1800, "i": 65535, "id": 27, "until": "duration"},
}


def _done(result=None) -> Future:
    future: Future = Future()
    future.set_result(result)
    return future


class StubShadowClient:
    """Records each desired state; the device confirms alarm id lists."""

    def __init__(self):
        self.published = []
        self.update_callback = None
        self.version = 1

    def subscribe_to_update_shadow_accepted(self, request, qos, callback):
        self.update_callback = callback
        return _done(), "update-topic"

    def subscribe_to_get_shadow_accepted(self, request, qos, callback):
        return _done(), "get-topic"

    def publish_get_shadow(self, request, qos):
        return _done(MagicMock())

    def publish_update_shadow(self, request, qos):
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
    def __init__(self, alarms):
        self.alarms = deepcopy(alarms)
        self.next_id = 5000

    async def restore_alarms(self, auth_token, mac, base_url):
        return [deepcopy(alarm) for alarm in self.alarms if alarm.get("active", True)]

    async def create_restore_alarm(self, auth_token, alarm, base_url):
        self.alarms.append({**deepcopy(alarm), "id": self.next_id, "active": False})
        self.next_id += 1
        return deepcopy(self.alarms)

    async def update_restore_alarms(self, auth_token, alarms, base_url):
        sent = {alarm["id"]: alarm for alarm in alarms}
        self.alarms = [{**alarm, **sent.get(alarm["id"], {})} for alarm in self.alarms]
        return [deepcopy(alarm) for alarm in self.alarms if alarm.get("active", True)]


class FakeCoordinator:
    """The coordinator's Restore alarm methods, without Home Assistant."""

    _restore_alarm_slots_store = None
    last_update_success = True
    restore_alarms_by_slot = HatchDataUpdateCoordinator.restore_alarms_by_slot if HAS_DEPENDENCIES else None
    restore_alarm = HatchDataUpdateCoordinator.restore_alarm if HAS_DEPENDENCIES else None
    _restore_alarm_id = HatchDataUpdateCoordinator._restore_alarm_id if HAS_DEPENDENCIES else None
    _save_restore_alarm_slots = HatchDataUpdateCoordinator._save_restore_alarm_slots if HAS_DEPENDENCIES else None
    async_set_restore_alarm_enabled = (
        HatchDataUpdateCoordinator.async_set_restore_alarm_enabled if HAS_DEPENDENCIES else None
    )
    async_set_restore_alarm_schedule = (
        HatchDataUpdateCoordinator.async_set_restore_alarm_schedule if HAS_DEPENDENCIES else None
    )

    def __init__(self, rest_devices):
        self.rest_devices = rest_devices
        self.restore_alarm_slots = RestoreAlarmSlots()
        self.alarm_refresh_callbacks = []

    def rest_device_by_thing_name(self, thing_name):
        return next(
            (device for device in self.rest_devices if device.thing_name == thing_name),
            None,
        )

    def async_add_alarm_refresh_callback(self, callback):
        self.alarm_refresh_callbacks.append(callback)
        return lambda: None


def _device(device_class, thing_name, mac):
    client = StubShadowClient()
    device = device_class(device_name="Bedroom", thing_name=thing_name, mac=mac, shadow_client=client)
    return device, client


def _restore(alarms=(SATURDAY_ALARM, WEEKDAY_ALARM)):
    device, client = _device(Restore, THING, MAC)
    device._update_local_state(deepcopy(RESTORE_STATE))
    device.routines = deepcopy(ROUTINES)
    api = FakeAlarmApi(list(alarms))
    device.configure_alarm_api(api=api, auth_token="token", alarms=deepcopy(list(alarms)))
    return device, client, api


def _registry_patches():
    return (
        patch.object(restore_entities.er, "async_get", return_value=MagicMock()),
        patch.object(restore_entities.er, "async_entries_for_config_entry", return_value=[]),
    )


def _set_up_platforms(coordinator) -> dict[str, list]:
    """Run every platform's async_setup_entry; return the entities each added."""
    hass = SimpleNamespace(data={DOMAIN: coordinator})
    config_entry = SimpleNamespace(options={}, entry_id="entry-1", async_on_unload=lambda remove: None)
    added: dict[str, list] = {}

    async def set_up_all():
        for name, platform in PLATFORMS.items():
            added[name] = []
            await platform.async_setup_entry(hass, config_entry, added[name].extend)

    registry_get, registry_entries = _registry_patches()
    # The scheduled-routine alarm reconcilers prune the entity registry, which
    # needs a real hass.
    with (
        registry_get,
        registry_entries,
        patch.object(switch, "remove_stale_alarm_entities"),
        patch.object(switch, "update_alarm_entity_names"),
        patch.object(sensor, "remove_stale_alarm_entities"),
        patch.object(sensor, "update_alarm_entity_names"),
        patch.object(time_platform, "remove_stale_alarm_entities"),
        patch.object(time_platform, "update_alarm_entity_names"),
    ):
        asyncio.run(set_up_all())
    return added


def _by_unique_id(added, platform, unique_id):
    return next(entity for entity in added[platform] if entity.unique_id == unique_id)


@unittest.skipUnless(HAS_DEPENDENCIES, "needs homeassistant and hatch_rest_api")
class RestorePlatformSetupTest(unittest.TestCase):
    def setUp(self):
        self.restore, self.client, self.api = _restore()
        self.coordinator = FakeCoordinator([self.restore])
        self.added = _set_up_platforms(self.coordinator)

    def entity(self, platform, unique_id):
        return _by_unique_id(self.added, platform, unique_id)

    def test_creates_the_restore_entities(self):
        self.assertEqual(
            {
                platform: sorted(type(entity).__name__ for entity in entities)
                for platform, entities in self.added.items()
            },
            {
                "binary_sensor": ["HatchOnlineSensor"],
                "light": ["RestoreClockLight", "RestoreLight"],
                "media_player": ["RestoreSound"],
                "number": [],
                "scene": [],
                "select": ["RestoreClockMode", "RestoreRoutineStep"],
                "sensor": [
                    "HatchFirmwareVersion",
                    "HatchRestorePlaying",
                    "HatchSignalStrength",
                    "RestoreAlarmRepeat",
                    "RestoreAlarmRepeat",
                ],
                "switch": [
                    "HatchRestoreRoutineSwitch",
                    "RestoreAlarmSwitch",
                    "RestoreAlarmSwitch",
                    "RestoreAlarmsSwitch",
                    "RestoreClock24Hour",
                ],
                "time": ["RestoreAlarmTime", "RestoreAlarmTime", "RestoreClockTime", "RestoreClockTime"],
            },
        )

    def test_unique_ids_and_alarm_names(self):
        unique_ids = sorted(entity.unique_id for entities in self.added.values() for entity in entities)
        self.assertEqual(
            unique_ids,
            sorted(
                [
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
                ]
            ),
        )
        # Alarm 1 goes off first in the day.
        weekday = self.entity("switch", f"{THING}_restore_alarm_1002_switch")
        saturday = self.entity("switch", f"{THING}_restore_alarm_1001_switch")
        self.assertEqual(weekday.name, "Bedroom Alarm 1")
        self.assertEqual(saturday.name, "Bedroom Alarm 2")
        self.assertEqual(self.entity("time", f"{THING}_restore_alarm_1002_time").name, "Bedroom Alarm 1 Wake Time")

    def test_light(self):
        light_entity = self.entity("light", f"{THING}_light")
        self.assertTrue(light_entity.is_on)
        self.assertEqual(light_entity.effect, "Blue")
        self.assertEqual(light_entity.brightness, 128)
        self.assertIn("Warm White", light_entity.effect_list)

        light_entity.turn_on(**{ATTR_BRIGHTNESS: 51, ATTR_EFFECT: "Peach"})
        light_entity.turn_off()
        self.assertEqual(
            self.client.published,
            [
                {"color": {"i": convert_from_percentage(20)}},
                {"color": {"id": 208}},
                {"color": {"enabled": False}},  # the sound keeps playing
            ],
        )

    def test_light_while_idle_starts_remote_playback(self):
        self.restore._update_local_state({"content": {"playing": "none"}})
        self.entity("light", f"{THING}_light").turn_on(**{ATTR_EFFECT: "Mint"})
        self.assertEqual(self.client.published[0]["content"], REMOTE)
        self.assertEqual(self.client.published[0]["color"]["id"], 214)

    def test_sound(self):
        sound = self.entity("media_player", f"{THING}_sound")
        self.assertEqual(sound.state, MediaPlayerState.PLAYING)
        self.assertEqual(sound.sound_mode, "White Noise")
        self.assertAlmostEqual(sound.volume_level, 0.3)

        sound.set_volume_level(0.15)
        sound.select_sound_mode("Fan")
        sound.media_stop()
        self.assertEqual(
            self.client.published,
            [
                {"sound": {"v": convert_from_percentage(15)}},
                {"sound": {"id": 10019}},
                {"sound": {"enabled": False}},  # the light stays on
            ],
        )
        with self.assertRaises(ValueError):
            sound.select_sound_mode("Not a sound")

    def test_sound_while_idle_shows_and_uses_the_remembered_volume(self):
        self.restore._update_local_state(
            {"content": {"playing": "none"}, "sound": {"enabled": False, "v": 0}}
        )
        sound = self.entity("media_player", f"{THING}_sound")
        self.assertEqual(sound.state, MediaPlayerState.IDLE)
        self.assertAlmostEqual(sound.volume_level, 0.3)
        sound.media_play()
        self.assertEqual(
            self.client.published,
            [
                {
                    "sound": {"enabled": True, "id": 10033, "v": convert_from_percentage(30)},
                    "content": REMOTE,
                    "color": {"enabled": False},
                }
            ],
        )

    def test_routine_step(self):
        step = self.entity("select", f"{THING}_routine_step")
        self.assertEqual(step.options, ["1. Read", "2. Dim", "3. Sleep"])
        self.assertEqual(step.current_option, "2. Dim")
        step.select_option("3. Sleep")
        self.assertEqual(
            self.client.published,
            [{"content": {"playing": "routine", "paused": False, "offset": 0, "step": 3}}],
        )
        self.restore.routines = None
        self.assertFalse(step.available)

    def test_clock(self):
        clock = self.entity("light", f"{THING}_clock")
        hours_24 = self.entity("switch", f"{THING}_clock_24-hour")
        mode = self.entity("select", f"{THING}_clock_mode")
        turn_off_at = self.entity("time", f"{THING}_clock_turn_off_at")
        self.assertTrue(clock.is_on)
        self.assertEqual(clock.brightness, 10)
        self.assertFalse(hours_24.is_on)
        self.assertEqual(mode.current_option, "Always On")
        self.assertEqual(turn_off_at.native_value, time(22, 0))

        clock.turn_off()
        clock.turn_on(**{ATTR_BRIGHTNESS: 102})
        hours_24.turn_on()
        mode.select_option("Off at Night")
        turn_off_at.set_value(time(21, 30))
        self.assertEqual(
            self.client.published,
            [
                {"restoreClock": {"flags": 0}},
                {"restoreClock": {"flags": 32768, "i": convert_from_percentage(40)}},
                {"restoreClock": {"flags": 34816}},
                {"restoreClock": {"turnOffMode": "custom"}},
                {"restoreClock": {"turnOffAt": "21:30:00"}},
            ],
        )

    def test_all_alarms_switch(self):
        alarms = self.entity("switch", f"{THING}_alarms")
        self.assertTrue(alarms.is_on)
        alarms.turn_off()
        self.assertEqual(self.client.published, [{"alarmsDisabled": True}])

    def test_alarm_entities_show_the_alarm(self):
        weekday = self.entity("switch", f"{THING}_restore_alarm_1002_switch")
        self.assertTrue(weekday.is_on)
        self.assertEqual(self.entity("time", f"{THING}_restore_alarm_1002_time").native_value, time(7, 0))
        self.assertEqual(self.entity("sensor", f"{THING}_restore_alarm_1002_repeat").native_value, "Weekdays")
        attributes = weekday.extra_state_attributes
        self.assertEqual(attributes["sound"], "Beep Beep")
        self.assertEqual(attributes["sunrise_color"], "Morning Stroll")
        self.assertEqual(attributes["sunrise_minutes"], 30)
        self.assertEqual(attributes["weekdays"], ["monday", "tuesday", "wednesday", "thursday", "friday"])

    def test_alarm_switch_syncs_the_device_and_saves(self):
        saturday = self.entity("switch", f"{THING}_restore_alarm_1001_switch")
        saturday.async_write_ha_state = lambda: None

        asyncio.run(saturday.async_turn_on())

        self.assertEqual(
            self.client.published,
            [{"content": {"requested": {"alarms": {"ids": [1001, 1002]}}}}],
        )
        self.assertTrue(next(alarm for alarm in self.api.alarms if alarm["id"] == 1001)["enabled"])
        self.assertTrue(saturday.is_on)

    def test_alarm_time_edit_keeps_the_same_entities(self):
        wake_time = self.entity("time", f"{THING}_restore_alarm_1002_time")
        wake_time.async_write_ha_state = lambda: None

        asyncio.run(wake_time.async_set_value(time(6, 45)))

        # Hatch now knows the alarm as 5000, but it is still Alarm 1.
        self.assertEqual(self.coordinator.restore_alarm_slots.alarm_id(THING, "1002"), 5000)
        self.assertEqual(wake_time.native_value, time(6, 45))
        self.assertEqual(wake_time.extra_state_attributes["hatch_alarm_id"], 5000)
        before = {entity.unique_id for entities in self.added.values() for entity in entities}
        registry_get, registry_entries = _registry_patches()
        with registry_get, registry_entries:
            for callback in self.coordinator.alarm_refresh_callbacks:
                asyncio.run(callback())
        after = {entity.unique_id for entities in self.added.values() for entity in entities}
        self.assertEqual(before, after)

    def test_alarm_edited_in_the_app_keeps_its_entities(self):
        # The app saved a new time for the weekday alarm: new id, old one gone.
        self.api.alarms = [
            deepcopy(SATURDAY_ALARM),
            {**deepcopy(WEEKDAY_ALARM), "id": 7000, "time": "2026-01-05 06:30:00"},
        ]
        asyncio.run(self.restore.refresh_alarms())
        wake_time = self.entity("time", f"{THING}_restore_alarm_1002_time")
        self.assertEqual(wake_time.native_value, time(6, 30))
        self.assertTrue(wake_time.available)

    def test_set_alarm_weekdays_action_resolves_restore_alarms(self):
        try:
            from custom_components.ha_hatch import services
        except ImportError as error:  # helpers.target is newer than HA 2025.1
            self.skipTest(f"services needs a newer Home Assistant: {error}")
        registry = MagicMock()
        registry.async_get.return_value = SimpleNamespace(
            platform=DOMAIN, unique_id=f"{THING}_restore_alarm_1002_time"
        )
        target = services._alarm_target_from_entity_id(
            registry, self.coordinator, "time.bedroom_alarm_1_wake_time", raise_if_not_alarm=True
        )
        self.assertEqual(target, ((THING, "1002"), (self.restore, "1002")))

        asyncio.run(
            self.coordinator.async_set_restore_alarm_schedule(
                self.restore, "1002", weekdays=["saturday", "sunday"]
            )
        )
        self.assertEqual(self.coordinator.restore_alarm(self.restore, "1002")["daysOfWeek"], 65)

    def test_firmware_follows_onto_the_device_card(self):
        firmware = self.entity("sensor", f"{THING}_firmware_version")
        firmware.hass = MagicMock()
        firmware.device_entry = SimpleNamespace(id="device-1", sw_version=None)
        device_registry = MagicMock()
        with (
            patch.object(sensor.dr, "async_get", return_value=device_registry),
            patch.object(Entity, "async_write_ha_state"),
        ):
            firmware.async_write_ha_state()
        device_registry.async_update_device.assert_called_once_with("device-1", sw_version="3.2.1")


@unittest.skipUnless(HAS_DEPENDENCIES, "needs homeassistant and hatch_rest_api")
class RestoreAlarmsNotLoadedTest(unittest.TestCase):
    def test_no_alarm_entities_until_the_alarms_load(self):
        restore, _ = _device(Restore, THING, MAC)
        restore._update_local_state(deepcopy(RESTORE_STATE))
        restore.configure_alarm_api(api=FakeAlarmApi([WEEKDAY_ALARM]), auth_token="token", alarms=None)
        coordinator = FakeCoordinator([restore])
        added = _set_up_platforms(coordinator)
        self.assertNotIn("RestoreAlarmSwitch", [type(entity).__name__ for entity in added["switch"]])

        asyncio.run(restore.refresh_alarms())
        registry_get, registry_entries = _registry_patches()
        with registry_get, registry_entries:
            for callback in coordinator.alarm_refresh_callbacks:
                asyncio.run(callback())
        self.assertIn("RestoreAlarmSwitch", [type(entity).__name__ for entity in added["switch"]])


@unittest.skipUnless(HAS_DEPENDENCIES, "needs homeassistant and hatch_rest_api")
class RestoreMediaPlayerTest(unittest.TestCase):
    def test_restore_gets_its_own_media_player(self):
        restore, _ = _device(Restore, THING, MAC)
        rest_mini, _ = _device(RestMini, "thing-mini", "AA:BB:CC:DD:EE:FF")
        coordinator = FakeCoordinator([restore, rest_mini])

        def choose(device):
            return media_player.choose_media_entity(
                device, config_turn_on_media=True, coordinator=coordinator
            )

        self.assertIsInstance(choose(restore), restore_entities.RestoreSound)
        # The models that do fall through still get the Rest Mini/Plus player.
        self.assertIsInstance(choose(rest_mini), MediaRestEntity)


@unittest.skipUnless(HAS_DEPENDENCIES, "needs homeassistant and hatch_rest_api")
class RestoreDiagnosticsTest(unittest.TestCase):
    def test_carries_the_raw_shadow_without_headphone_secrets(self):
        restore, _ = _device(Restore, THING, MAC)
        restore._update_local_state(deepcopy(RESTORE_STATE))
        device_registry = MagicMock()
        device_registry.async_get_device.return_value = None
        hass = SimpleNamespace(data={DOMAIN: FakeCoordinator([restore])})
        config_entry = MagicMock()
        config_entry.as_dict.return_value = {"data": {}}

        with (
            patch.object(diagnostics.dr, "async_get", return_value=device_registry),
            patch.object(diagnostics.er, "async_get", return_value=MagicMock()),
        ):
            data = asyncio.run(
                diagnostics.async_get_config_entry_diagnostics(hass, config_entry)
            )

        shadow = data[THING]["shadow_state"]
        self.assertEqual(shadow["content"]["routineId"], 501)
        self.assertEqual(shadow["headphones"]["stateResult"], "unknown")
        self.assertEqual(shadow["headphones"]["requestedPin"], "**REDACTED**")
        self.assertEqual(shadow["headphones"]["connectedMacAddress"], "**REDACTED**")
        # Redacting a copy: the device keeps its real state.
        self.assertEqual(restore.shadow_state["headphones"]["requestedPin"], "1234")


if __name__ == "__main__":
    unittest.main()
