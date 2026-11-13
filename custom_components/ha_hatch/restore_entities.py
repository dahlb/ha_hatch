"""Entities for the original Hatch Restore (Hatch product ``restore``).

The platform modules add these for Restore devices; see README.md, "Original
Restore", for what each one does and what was verified on a real device.
"""

from __future__ import annotations

import logging
from datetime import time
from typing import Any

from hatch_rest_api import Restore
from hatch_rest_api.const import (
    RESTORE_COLOR_NAMES,
    RESTORE_COLORS,
    RESTORE_SOUND_NAMES,
    RESTORE_SOUNDS,
)
from hatch_rest_api.restore import restore_alarm_wake_time
from hatch_rest_api.util import convert_to_percentage
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er

from .alarm import alarm_repeat_label, alarm_weekdays
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)

RESTORE_ALARM_UNIQUE_ID_MARKER = "_restore_alarm_"
CLOCK_MODE_ALWAYS_ON = "Always On"
CLOCK_MODE_OFF_AT_NIGHT = "Off at Night"
COLOR_IDS_BY_NAME = {name: color_id for color_id, name in RESTORE_COLORS.items()}
SOUND_IDS_BY_NAME = {name: sound_id for sound_id, name in RESTORE_SOUNDS.items()}


def brightness_to_percent(brightness: int) -> int:
    return max(1, min(100, round(brightness / 255 * 100)))


def percent_to_brightness(percent: int | None) -> int | None:
    return None if percent is None else round(percent * 255 / 100)


def parse_clock_time(value: str | None) -> time | None:
    """A shadow clock time, "HH:MM" or "HH:MM:SS"."""
    if not value:
        return None
    parts = value.split(":")
    try:
        return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0, int(parts[2]) if len(parts) > 2 else 0)
    except (ValueError, IndexError):
        return None


# ---- device controls ----------------------------------------------------------


class RestoreLight(HatchEntity, LightEntity):
    """The light. Colors are offered as effects: the device takes catalog colors, not RGB."""

    _attr_icon = "mdi:lightbulb-night"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = list(RESTORE_COLORS.values())

    def __init__(self, coordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Light")

    @property
    def is_on(self) -> bool:
        return self.rest_device.is_light_on

    @property
    def brightness(self) -> int | None:
        return percent_to_brightness(self.rest_device.brightness) if self.is_on else None

    @property
    def effect(self) -> str | None:
        return self.rest_device.color_name if self.is_on else None

    def turn_on(self, **kwargs: Any) -> None:
        percent = brightness_to_percent(kwargs[ATTR_BRIGHTNESS]) if ATTR_BRIGHTNESS in kwargs else None
        color_id = COLOR_IDS_BY_NAME.get(kwargs[ATTR_EFFECT]) if ATTR_EFFECT in kwargs else None
        device: Restore = self.rest_device
        if not device.is_light_on:
            device.turn_light_on(color_id=color_id, brightness=percent)
            return
        if percent is not None:
            device.set_light_brightness(percent)
        if color_id is not None:
            device.set_light_color(color_id)

    def turn_off(self, **kwargs: Any) -> None:
        self.rest_device.turn_light_off()


class RestoreSound(HatchEntity, MediaPlayerEntity):
    """The sound machine: play, stop, volume and which sound."""

    _attr_media_content_type = MediaType.MUSIC
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_sound_mode_list = list(RESTORE_SOUNDS.values())
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )

    def __init__(self, coordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Sound")

    @property
    def state(self) -> MediaPlayerState:
        return MediaPlayerState.PLAYING if self.rest_device.is_sound_on else MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float:
        # The device reports volume 0 while nothing plays; show what the next
        # sound will start at instead.
        device: Restore = self.rest_device
        return (device.volume if device.is_sound_on else device.last_volume) / 100

    @property
    def sound_mode(self) -> str | None:
        return self.rest_device.sound_name

    @property
    def media_title(self) -> str | None:
        return self.rest_device.sound_name if self.rest_device.is_sound_on else None

    def media_play(self) -> None:
        self.rest_device.play_sound()

    def media_pause(self) -> None:
        self.rest_device.stop_sound()

    def media_stop(self) -> None:
        self.rest_device.stop_sound()

    def set_volume_level(self, volume: float) -> None:
        self.rest_device.set_volume(round(volume * 100))

    def select_sound_mode(self, sound_mode: str) -> None:
        if sound_mode not in SOUND_IDS_BY_NAME:
            raise ValueError(f"Unknown sound: {sound_mode}")
        self.rest_device.set_sound(SOUND_IDS_BY_NAME[sound_mode])


class RestoreRoutineStep(HatchEntity, SelectEntity):
    """Start the bedtime routine at a chosen step; shows the step playing."""

    _attr_icon = "mdi:format-list-numbered"

    def __init__(self, coordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Routine Step")

    @property
    def options(self) -> list[str]:
        return [f"{number}. {name}" for number, name in enumerate(self.rest_device.routine_steps, start=1)]

    @property
    def available(self) -> bool:
        return super().available and bool(self.options)

    @property
    def current_option(self) -> str | None:
        device: Restore = self.rest_device
        options = self.options
        if device.current_playing == "routine" and 1 <= device.current_step <= len(options):
            return options[device.current_step - 1]
        return None

    def select_option(self, option: str) -> None:
        self.rest_device.turn_on_routine(step=self.options.index(option) + 1)


class RestoreClockLight(HatchEntity, LightEntity):
    _attr_icon = "mdi:clock-digital"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Clock")

    @property
    def is_on(self) -> bool | None:
        return self.rest_device.is_clock_on

    @property
    def brightness(self) -> int | None:
        return percent_to_brightness(self.rest_device.clock_brightness)

    def turn_on(self, **kwargs: Any) -> None:
        percent = brightness_to_percent(kwargs[ATTR_BRIGHTNESS]) if ATTR_BRIGHTNESS in kwargs else None
        self.rest_device.set_clock(on=True, brightness=percent)

    def turn_off(self, **kwargs: Any) -> None:
        self.rest_device.set_clock(on=False)


class RestoreClock24Hour(HatchEntity, SwitchEntity):
    _attr_icon = "mdi:hours-24"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Clock 24-Hour")

    @property
    def is_on(self) -> bool | None:
        return self.rest_device.is_clock_24h

    def turn_on(self, **kwargs: Any) -> None:
        self.rest_device.set_clock_24h(True)

    def turn_off(self, **kwargs: Any) -> None:
        self.rest_device.set_clock_24h(False)


class RestoreClockMode(HatchEntity, SelectEntity):
    """Always on, or off between the Clock Turn Off At and Turn On At times."""

    _attr_icon = "mdi:clock-time-four-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = [CLOCK_MODE_ALWAYS_ON, CLOCK_MODE_OFF_AT_NIGHT]

    def __init__(self, coordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Clock Mode")

    @property
    def current_option(self) -> str | None:
        mode = self.rest_device.clock_turn_off_mode
        if mode == "custom":
            return CLOCK_MODE_OFF_AT_NIGHT
        if mode == "never":
            return CLOCK_MODE_ALWAYS_ON
        return None

    def select_option(self, option: str) -> None:
        self.rest_device.set_clock_off_at_night(option == CLOCK_MODE_OFF_AT_NIGHT)


class RestoreClockTime(HatchEntity, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, thing_name: str, turn_on: bool):
        self._turn_on = turn_on
        self._attr_icon = "mdi:clock-start" if turn_on else "mdi:clock-end"
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Clock Turn On At" if turn_on else "Clock Turn Off At",
        )

    @property
    def native_value(self) -> time | None:
        device: Restore = self.rest_device
        return parse_clock_time(device.clock_turn_on_at if self._turn_on else device.clock_turn_off_at)

    def set_value(self, value: time) -> None:
        if self._turn_on:
            self.rest_device.set_clock_schedule(turn_on_at=value)
        else:
            self.rest_device.set_clock_schedule(turn_off_at=value)


class RestoreAlarmsSwitch(HatchEntity, SwitchEntity):
    """All alarms at once: the crossed-bell button on the device."""

    _attr_icon = "mdi:alarm-multiple"

    def __init__(self, coordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Alarms")

    @property
    def is_on(self) -> bool | None:
        disabled = self.rest_device.alarms_disabled
        return None if disabled is None else not disabled

    def turn_on(self, **kwargs: Any) -> None:
        self.rest_device.set_alarms_disabled(False)

    def turn_off(self, **kwargs: Any) -> None:
        self.rest_device.set_alarms_disabled(True)


# ---- individual alarms ----------------------------------------------------------


def restore_alarm_unique_id(thing_name: str, slot_key: str, suffix: str) -> str:
    return f"{thing_name}{RESTORE_ALARM_UNIQUE_ID_MARKER}{slot_key}{suffix}"


def restore_alarm_reference_from_unique_id(unique_id: str | None, suffixes: set[str]) -> tuple[str, str] | None:
    """(thing name, slot key) of a Restore alarm entity's unique id, else None."""
    for suffix in sorted(suffixes, key=len, reverse=True):
        if not unique_id or not unique_id.endswith(suffix):
            continue
        thing_name, marker, slot_key = unique_id[: -len(suffix)].rpartition(RESTORE_ALARM_UNIQUE_ID_MARKER)
        if marker and thing_name and slot_key:
            return thing_name, slot_key
    return None


def restore_alarm_attributes(alarm: dict[str, Any] | None) -> dict[str, Any]:
    if not alarm:
        return {}
    sound = alarm.get("sound") if isinstance(alarm.get("sound"), dict) else {}
    color = alarm.get("color") if isinstance(alarm.get("color"), dict) else {}
    wake_time = restore_alarm_wake_time(alarm)
    days_of_week = alarm.get("daysOfWeek")
    return {
        "time": wake_time.strftime("%H:%M") if wake_time else None,
        "repeat": alarm_repeat_label(days_of_week),
        "weekdays": alarm_weekdays(days_of_week),
        "sound": RESTORE_SOUND_NAMES.get(sound.get("id"), sound.get("id")),
        "volume": convert_to_percentage(int(sound["v"])) if sound.get("v") is not None else None,
        "sunrise": bool(alarm.get("colorStartsEarly")),
        "sunrise_color": RESTORE_COLOR_NAMES.get(color.get("id"), color.get("id")),
        "sunrise_brightness": convert_to_percentage(int(color["i"])) if color.get("i") is not None else None,
        "sunrise_minutes": round(color["duration"] / 60) if color.get("duration") else None,
        "hatch_alarm_id": alarm.get("id"),
    }


class RestoreAlarmEntity(HatchEntity):
    """One alarm, followed through its slot rather than its changing Hatch id."""

    unique_id_suffix = ""
    name_suffix = ""

    def __init__(self, coordinator, thing_name: str, slot_key: str, number: int):
        self._slot_key = slot_key
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type=f"Alarm {number}{self.name_suffix}",
        )
        self._attr_unique_id = restore_alarm_unique_id(thing_name, slot_key, self.unique_id_suffix)

    @property
    def _alarm(self) -> dict[str, Any] | None:
        return self.coordinator.restore_alarm(self.rest_device, self._slot_key)

    @property
    def available(self) -> bool:
        return super().available and self._alarm is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return restore_alarm_attributes(self._alarm)


class RestoreAlarmSwitch(RestoreAlarmEntity, SwitchEntity):
    _attr_icon = "mdi:alarm"
    unique_id_suffix = "_switch"

    @property
    def is_on(self) -> bool | None:
        alarm = self._alarm
        return None if alarm is None else bool(alarm.get("enabled"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_restore_alarm_enabled(self.rest_device, self._slot_key, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_restore_alarm_enabled(self.rest_device, self._slot_key, False)
        self.async_write_ha_state()


class RestoreAlarmTime(RestoreAlarmEntity, TimeEntity):
    _attr_icon = "mdi:alarm"
    unique_id_suffix = "_time"
    name_suffix = " Wake Time"

    @property
    def native_value(self) -> time | None:
        return restore_alarm_wake_time(self._alarm)

    async def async_set_value(self, value: time) -> None:
        await self.coordinator.async_set_restore_alarm_schedule(self.rest_device, self._slot_key, wake_time=value)
        self.async_write_ha_state()


class RestoreAlarmRepeat(RestoreAlarmEntity, SensorEntity):
    _attr_icon = "mdi:calendar-week"
    unique_id_suffix = "_repeat"
    name_suffix = " Repeat"

    @property
    def native_value(self) -> str | None:
        alarm = self._alarm
        return None if alarm is None else alarm_repeat_label(alarm.get("daysOfWeek"))


async def async_setup_restore_alarm_entities(
    hass,
    config_entry,
    coordinator,
    async_add_entities,
    entity_class: type[RestoreAlarmEntity],
    domain: str,
) -> None:
    """Add, keep and remove one entity per alarm slot, as alarms come and go."""
    entities: dict[str, RestoreAlarmEntity] = {}
    suffix = entity_class.unique_id_suffix

    async def async_reconcile() -> None:
        current: set[str] = set()
        prefixes: set[str] = set()
        new_entities = []
        for rest_device in coordinator.rest_devices:
            if not isinstance(rest_device, Restore) or not rest_device.restore_alarms_loaded:
                continue
            thing_name = rest_device.thing_name
            prefixes.add(f"{thing_name}{RESTORE_ALARM_UNIQUE_ID_MARKER}")
            for slot_key in coordinator.restore_alarms_by_slot(rest_device):
                unique_id = restore_alarm_unique_id(thing_name, slot_key, suffix)
                current.add(unique_id)
                if unique_id in entities:
                    continue
                number = coordinator.restore_alarm_slots.number(thing_name, slot_key)
                entity = entity_class(coordinator, thing_name, slot_key, number)
                entities[unique_id] = entity
                new_entities.append(entity)

        for unique_id in [
            unique_id
            for unique_id in entities
            if unique_id not in current and any(unique_id.startswith(prefix) for prefix in prefixes)
        ]:
            await entities.pop(unique_id).async_remove(force_remove=True)

        if prefixes:
            registry = er.async_get(hass)
            for entry in er.async_entries_for_config_entry(registry, config_entry.entry_id):
                if (
                    entry.domain == domain
                    and entry.unique_id.endswith(suffix)
                    and entry.unique_id not in current
                    and any(entry.unique_id.startswith(prefix) for prefix in prefixes)
                ):
                    registry.async_remove(entry.entity_id)

        if new_entities:
            async_add_entities(new_entities)

    await async_reconcile()
    config_entry.async_on_unload(coordinator.async_add_alarm_refresh_callback(async_reconcile))
