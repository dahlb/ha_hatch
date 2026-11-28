"""Entities for the original Hatch Restore (Hatch product ``restore``).

The platform modules add these for Restore devices; see README.md, "Original
Restore", for what each one does and what was verified on a real device.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
import logging
from typing import Any

from hatch_rest_api import Restore
from hatch_rest_api.const import (
    CLOCK_TURN_OFF_MODE_CUSTOM,
    CLOCK_TURN_OFF_MODE_NEVER,
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
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .alarm import alarm_repeat_label, alarm_weekdays
from .commands import translate_command_errors
from .hatch_data_update_coordinator import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity
from .restore_alarm_slots import (
    RESTORE_ALARM_UNIQUE_ID_MARKER,
    alarm_section,
    restore_alarm_unique_id,
)

_LOGGER = logging.getLogger(__name__)

CLOCK_MODE_ALWAYS_ON = "Always On"
CLOCK_MODE_OFF_AT_NIGHT = "Off at Night"
COLOR_IDS_BY_NAME = {name: color_id for color_id, name in RESTORE_COLORS.items()}
SOUND_IDS_BY_NAME = {name: sound_id for sound_id, name in RESTORE_SOUNDS.items()}


def _name_or_id(names: dict[int, str], item_id: Any) -> Any:
    """Return the name for a Hatch sound or color id, or the id itself if unknown."""
    return names.get(item_id, item_id) if isinstance(item_id, int) else item_id


def brightness_to_percent(brightness: int) -> int:
    """Convert a Home Assistant brightness (0-255) to a percentage, at least 1.

    Args:
        brightness: Home Assistant brightness.

    Returns:
        The brightness in percent, 1 to 100.
    """
    return max(1, min(100, round(brightness / 255 * 100)))


def percent_to_brightness(percent: int | None) -> int | None:
    """Convert a percentage to a Home Assistant brightness (0-255).

    Args:
        percent: Brightness in percent, or None.

    Returns:
        The Home Assistant brightness, or None.
    """
    return None if percent is None else round(percent * 255 / 100)


def parse_clock_time(value: str | None) -> time | None:
    """Parse a shadow clock time, "HH:MM" or "HH:MM:SS".

    Args:
        value: The shadow value.

    Returns:
        The time, or None if there is none or it does not parse.
    """
    if not value:
        return None
    parts = value.split(":")
    try:
        return time(
            int(parts[0]),
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2]) if len(parts) > 2 else 0,
        )
    except ValueError, IndexError:
        return None


class RestoreEntity(HatchEntity[Restore]):
    """Base for the original Restore's entities, typed to the Restore device."""

    @property
    def available(self) -> bool:
        """Whether the coordinator is up and still has this device."""
        return super().available and isinstance(self.rest_device, Restore)

    @property
    def restore(self) -> Restore:
        """The device; Home Assistant only reads state while it is available.

        Raises:
            HomeAssistantError: The device is no longer known.
        """
        device = self.rest_device
        if not isinstance(device, Restore):
            raise HomeAssistantError(f"Hatch device {self.coordinator_context} is not available")
        return device


# ---- device controls ----------------------------------------------------------


class RestoreLight(RestoreEntity, LightEntity):
    """The light. Colors are offered as effects: the device takes catalog colors, not RGB."""

    _attr_icon = "mdi:lightbulb-night"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the light.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Light")
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_effect_list = list(RESTORE_COLORS.values())

    @property
    def is_on(self) -> bool:
        """Whether the light is on."""
        return self.restore.is_light_on

    @property
    def brightness(self) -> int | None:
        """The light's brightness while it is on."""
        return percent_to_brightness(self.restore.brightness) if self.is_on else None

    @property
    def effect(self) -> str | None:
        """The light's color while it is on."""
        return self.restore.color_name if self.is_on else None

    @translate_command_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on, or change its brightness or color while it is on.

        Args:
            **kwargs: Home Assistant's light turn-on arguments.
        """
        percent = (
            brightness_to_percent(kwargs[ATTR_BRIGHTNESS]) if ATTR_BRIGHTNESS in kwargs else None
        )
        color_id = COLOR_IDS_BY_NAME.get(kwargs[ATTR_EFFECT]) if ATTR_EFFECT in kwargs else None
        device = self.restore
        if not device.is_light_on:
            await device.async_command(device.turn_light_on, color_id=color_id, brightness=percent)
            return
        if percent is not None:
            await device.async_command(device.set_light_brightness, percent)
        if color_id is not None:
            await device.async_command(device.set_light_color, color_id)

    @translate_command_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off.

        Args:
            **kwargs: Home Assistant's light turn-off arguments.
        """
        await self.restore.async_command(self.restore.turn_light_off)


class RestoreSound(RestoreEntity, MediaPlayerEntity):
    """The sound machine: play, stop, volume and which sound."""

    _attr_media_content_type = MediaType.MUSIC
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the sound player.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Sound")
        self._attr_sound_mode_list = list(RESTORE_SOUNDS.values())

    @property
    def state(self) -> MediaPlayerState:
        """Playing while a sound plays, else idle."""
        return MediaPlayerState.PLAYING if self.restore.is_sound_on else MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float:
        """The volume, or while idle the volume the next sound starts at."""
        # The device reports volume 0 while nothing plays; show what the next
        # sound will start at instead.
        device = self.restore
        return (device.volume if device.is_sound_on else device.last_volume) / 100

    @property
    def sound_mode(self) -> str | None:
        """The current sound."""
        return self.restore.sound_name

    @property
    def media_title(self) -> str | None:
        """The sound playing, if any."""
        return self.restore.sound_name if self.restore.is_sound_on else None

    @translate_command_errors
    async def async_media_play(self) -> None:
        """Play the current sound."""
        await self.restore.async_command(self.restore.play_sound)

    @translate_command_errors
    async def async_media_pause(self) -> None:
        """Stop the sound; the device cannot pause."""
        await self.restore.async_command(self.restore.stop_sound)

    @translate_command_errors
    async def async_media_stop(self) -> None:
        """Stop the sound."""
        await self.restore.async_command(self.restore.stop_sound)

    @translate_command_errors
    async def async_set_volume_level(self, volume: float) -> None:
        """Set the volume.

        Args:
            volume: Volume from 0 to 1.
        """
        await self.restore.async_command(self.restore.set_volume, round(volume * 100))

    @translate_command_errors
    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Play a sound from the catalog.

        Args:
            sound_mode: The sound's name.

        Raises:
            ServiceValidationError: The sound is not in the catalog.
        """
        if sound_mode not in SOUND_IDS_BY_NAME:
            raise ServiceValidationError(f"Unknown sound: {sound_mode}")
        await self.restore.async_command(self.restore.set_sound, SOUND_IDS_BY_NAME[sound_mode])


class RestoreRoutineStep(RestoreEntity, SelectEntity):
    """Start the bedtime routine at a chosen step; shows the step playing."""

    _attr_icon = "mdi:format-list-numbered"

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the routine step select.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Routine Step")

    @property
    def options(self) -> list[str]:
        """The routine's steps, numbered; empty while the routine is unknown."""
        device = self.rest_device
        if not isinstance(device, Restore):
            return []
        return [f"{number}. {name}" for number, name in enumerate(device.routine_steps, start=1)]

    @property
    def available(self) -> bool:
        """Whether the routine, and so its steps, are known."""
        return super().available and bool(self.options)

    @property
    def current_option(self) -> str | None:
        """The step playing, if the routine is."""
        device = self.restore
        options = self.options
        if device.current_playing == "routine" and 1 <= device.current_step <= len(options):
            return options[device.current_step - 1]
        return None

    @translate_command_errors
    async def async_select_option(self, option: str) -> None:
        """Start the routine at a step.

        Args:
            option: One of ``options``.
        """
        await self.restore.async_command(
            self.restore.turn_on_routine, step=self.options.index(option) + 1
        )


class RestoreRoutineSwitch(RestoreEntity, SwitchEntity):
    """Starts and stops the original Restore's bedtime routine.

    On while the Restore plays anything, including content started from the
    Hatch app, so turning it off always stops the device.
    """

    _attr_icon = "mdi:power-sleep"

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the routine switch.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(
            coordinator=coordinator, thing_name=thing_name, entity_type="Bedtime Routine"
        )

    @property
    def is_on(self) -> bool:
        """Whether anything is playing."""
        return self.restore.is_on

    @translate_command_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the routine at its first step.

        Args:
            **kwargs: Unused.
        """
        await self.restore.async_command(self.restore.turn_on_routine)

    @translate_command_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop whatever is playing.

        Args:
            **kwargs: Unused.
        """
        await self.restore.async_command(self.restore.turn_off)


class RestoreClockLight(RestoreEntity, LightEntity):
    """The clock display: on/off and brightness."""

    _attr_icon = "mdi:clock-digital"
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the clock light.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Clock")
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool | None:
        """Whether the display is on."""
        return self.restore.is_clock_on

    @property
    def brightness(self) -> int | None:
        """The display's brightness."""
        return percent_to_brightness(self.restore.clock_brightness)

    @translate_command_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the display on, optionally at a brightness.

        Args:
            **kwargs: Home Assistant's light turn-on arguments.
        """
        percent = (
            brightness_to_percent(kwargs[ATTR_BRIGHTNESS]) if ATTR_BRIGHTNESS in kwargs else None
        )
        await self.restore.async_command(self.restore.set_clock, on=True, brightness=percent)

    @translate_command_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the display off.

        Args:
            **kwargs: Home Assistant's light turn-off arguments.
        """
        await self.restore.async_command(self.restore.set_clock, on=False)


class RestoreClock24Hour(RestoreEntity, SwitchEntity):
    """12-hour or 24-hour clock."""

    _attr_icon = "mdi:hours-24"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the 24-hour switch.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(
            coordinator=coordinator, thing_name=thing_name, entity_type="Clock 24-Hour"
        )

    @property
    def is_on(self) -> bool | None:
        """Whether the clock shows 24-hour time."""
        return self.restore.is_clock_24h

    @translate_command_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Show 24-hour time.

        Args:
            **kwargs: Unused.
        """
        await self.restore.async_command(self.restore.set_clock_24h, True)

    @translate_command_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Show 12-hour time.

        Args:
            **kwargs: Unused.
        """
        await self.restore.async_command(self.restore.set_clock_24h, False)


class RestoreClockMode(RestoreEntity, SelectEntity):
    """Always on, or off between the Clock Turn Off At and Turn On At times.

    The third mode the other models offer, always off, has no effect on this
    one; the Clock light turns the display off instead.
    """

    _attr_icon = "mdi:clock-time-four-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the clock mode select.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Clock Mode")
        self._attr_options = [CLOCK_MODE_ALWAYS_ON, CLOCK_MODE_OFF_AT_NIGHT]

    @property
    def current_option(self) -> str | None:
        """The current mode, if it is one of the two this model supports."""
        mode = self.restore.clock_turn_off_mode
        if mode == CLOCK_TURN_OFF_MODE_CUSTOM:
            return CLOCK_MODE_OFF_AT_NIGHT
        if mode == CLOCK_TURN_OFF_MODE_NEVER:
            return CLOCK_MODE_ALWAYS_ON
        return None

    @translate_command_errors
    async def async_select_option(self, option: str) -> None:
        """Set the mode.

        Args:
            option: One of ``options``.
        """
        await self.restore.async_command(
            self.restore.set_clock_off_at_night, option == CLOCK_MODE_OFF_AT_NIGHT
        )


class RestoreClockTime(RestoreEntity, TimeEntity):
    """When the clock turns on or off under its night schedule."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: HatchDataUpdateCoordinator, thing_name: str, turn_on: bool
    ) -> None:
        """Initialize the time entity.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
            turn_on: True for the turn-on time, False for the turn-off time.
        """
        self._turn_on = turn_on
        self._attr_icon = "mdi:clock-start" if turn_on else "mdi:clock-end"
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Clock Turn On At" if turn_on else "Clock Turn Off At",
        )

    @property
    def native_value(self) -> time | None:
        """The time."""
        device = self.restore
        return parse_clock_time(
            device.clock_turn_on_at if self._turn_on else device.clock_turn_off_at
        )

    @translate_command_errors
    async def async_set_value(self, value: time) -> None:
        """Set the time.

        Args:
            value: The new time.
        """
        if self._turn_on:
            await self.restore.async_command(self.restore.set_clock_schedule, turn_on_at=value)
        else:
            await self.restore.async_command(self.restore.set_clock_schedule, turn_off_at=value)


class RestoreAlarmsSwitch(RestoreEntity, SwitchEntity):
    """All alarms at once: the crossed-bell button on the device."""

    _attr_icon = "mdi:alarm-multiple"

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the all-alarms switch.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Alarms")

    @property
    def is_on(self) -> bool | None:
        """Whether alarms may go off."""
        disabled = self.restore.alarms_disabled
        return None if disabled is None else not disabled

    @translate_command_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Allow alarms to go off.

        Args:
            **kwargs: Unused.
        """
        await self.restore.async_command(self.restore.set_alarms_disabled, False)

    @translate_command_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Silence every alarm.

        Args:
            **kwargs: Unused.
        """
        await self.restore.async_command(self.restore.set_alarms_disabled, True)


class RestorePlaying(RestoreEntity, SensorEntity):
    """What the original Restore is playing: none, routine or remote.

    Plain text rather than an enum: the full set of values this model reports
    is not confirmed, and an enum sensor rejects one it was not told about.
    """

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the playing sensor.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Playing")

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """The playback mode."""
        return self.restore.current_playing

    @property
    def icon(self) -> str | None:
        """A play icon while playing, else a stop icon."""
        if self.restore.is_playing:
            return "mdi:play-circle-outline"
        return "mdi:stop-circle-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The routine step and id, and whether playback is paused."""
        device = self.restore
        return {
            "step": device.current_step,
            "routine_id": device.routine_id,
            "paused": device.paused,
        }


class RestoreFirmwareVersion(RestoreEntity, SensorEntity):
    """The firmware version, which also keeps the device card's version current."""

    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the firmware sensor.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(
            coordinator=coordinator, thing_name=thing_name, entity_type="Firmware Version"
        )

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """The firmware version."""
        return self.restore.firmware_version

    async def async_added_to_hass(self) -> None:
        """Bring the device card's firmware up to date once the entity is added."""
        await super().async_added_to_hass()
        self._async_sync_device_firmware()

    def _handle_coordinator_update(self) -> None:
        """Update the state, and the device card's firmware on the event loop.

        Device reports arrive on an awscrt thread, and the device registry may
        only be changed from the event loop.
        """
        if self.hass is not None:
            self.hass.loop.call_soon_threadsafe(self._async_sync_device_firmware)
        super()._handle_coordinator_update()

    @callback
    def _async_sync_device_firmware(self) -> None:
        """Write the reported firmware onto the device card if it differs.

        The device card's firmware is fixed when the entities are created,
        usually before the device's first report has arrived.
        """
        device = self.rest_device
        firmware = device.firmware_version if isinstance(device, Restore) else None
        if not firmware or self.hass is None or self.device_entry is None:
            return
        registry = dr.async_get(self.hass)
        device_entry = registry.async_get(self.device_entry.id)
        if isinstance(device_entry, dr.DeviceEntry) and device_entry.sw_version != firmware:
            registry.async_update_device(device_entry.id, sw_version=firmware)


class RestoreSignalStrength(RestoreEntity, SensorEntity):
    """The Wi-Fi signal strength."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the signal sensor.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
        """
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Wifi Signal")

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """The signal strength in dBm."""
        return self.restore.rssi


# ---- individual alarms ----------------------------------------------------------


def restore_alarm_attributes(alarm: dict[str, Any] | None) -> dict[str, Any]:
    """Return an alarm's settings as entity attributes.

    Args:
        alarm: An alarm from Hatch's alarm API, or None.

    Returns:
        Its time, repeat days, sound and sunrise settings; empty for no alarm.
    """
    if not alarm:
        return {}
    sound = alarm_section(alarm, "sound")
    color = alarm_section(alarm, "color")
    wake_time = restore_alarm_wake_time(alarm)
    days_of_week = alarm.get("daysOfWeek")
    return {
        "time": wake_time.strftime("%H:%M") if wake_time else None,
        "repeat": alarm_repeat_label(days_of_week),
        "weekdays": alarm_weekdays(days_of_week),
        "sound": _name_or_id(RESTORE_SOUND_NAMES, sound.get("id")),
        "volume": convert_to_percentage(int(sound["v"])) if sound.get("v") is not None else None,
        "sunrise": bool(alarm.get("colorStartsEarly")),
        "sunrise_color": _name_or_id(RESTORE_COLOR_NAMES, color.get("id")),
        "sunrise_brightness": (
            convert_to_percentage(int(color["i"])) if color.get("i") is not None else None
        ),
        "sunrise_minutes": round(color["duration"] / 60) if color.get("duration") else None,
        "hatch_alarm_id": alarm.get("id"),
    }


class RestoreAlarmEntity(RestoreEntity):
    """One alarm, followed through its slot rather than its changing Hatch id."""

    unique_id_suffix = ""
    name_suffix = ""

    def __init__(
        self,
        coordinator: HatchDataUpdateCoordinator,
        thing_name: str,
        slot_key: str,
        number: int,
    ) -> None:
        """Initialize the alarm entity.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
            slot_key: The alarm's slot.
            number: The N of "Alarm N".
        """
        self._slot_key = slot_key
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type=f"Alarm {number}{self.name_suffix}",
        )
        self._attr_unique_id = restore_alarm_unique_id(thing_name, slot_key, self.unique_id_suffix)

    @property
    def _alarm(self) -> dict[str, Any] | None:
        """The alarm now in this entity's slot."""
        device = self.rest_device
        return self.coordinator.restore_alarm(
            device if isinstance(device, Restore) else None, self._slot_key
        )

    @property
    def available(self) -> bool:
        """Whether the slot still holds an alarm."""
        return super().available and self._alarm is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The alarm's settings."""
        return restore_alarm_attributes(self._alarm)


class RestoreAlarmSwitch(RestoreAlarmEntity, SwitchEntity):
    """Turns one alarm on or off."""

    _attr_icon = "mdi:alarm"
    unique_id_suffix = "_switch"

    @property
    def is_on(self) -> bool | None:
        """Whether the alarm goes off."""
        alarm = self._alarm
        return None if alarm is None else bool(alarm.get("enabled"))

    @translate_command_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the alarm on.

        Args:
            **kwargs: Unused.
        """
        await self.coordinator.async_set_restore_alarm_enabled(self.restore, self._slot_key, True)
        self.async_write_ha_state()

    @translate_command_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the alarm off.

        Args:
            **kwargs: Unused.
        """
        await self.coordinator.async_set_restore_alarm_enabled(self.restore, self._slot_key, False)
        self.async_write_ha_state()


class RestoreAlarmTime(RestoreAlarmEntity, TimeEntity):
    """One alarm's wake time."""

    _attr_icon = "mdi:alarm"
    unique_id_suffix = "_time"
    name_suffix = " Wake Time"

    @property
    def native_value(self) -> time | None:
        """The wake time."""
        return restore_alarm_wake_time(self._alarm)

    @translate_command_errors
    async def async_set_value(self, value: time) -> None:
        """Change the wake time.

        Args:
            value: The new wake time.
        """
        await self.coordinator.async_set_restore_alarm_schedule(
            self.restore, self._slot_key, wake_time=value
        )
        self.async_write_ha_state()


class RestoreAlarmRepeat(RestoreAlarmEntity, SensorEntity):
    """One alarm's repeat days."""

    _attr_icon = "mdi:calendar-week"
    unique_id_suffix = "_repeat"
    name_suffix = " Repeat"

    @property
    def native_value(self) -> str | None:
        """The repeat days, as a label."""
        alarm = self._alarm
        return None if alarm is None else alarm_repeat_label(alarm.get("daysOfWeek"))


async def async_setup_restore_alarm_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    coordinator: HatchDataUpdateCoordinator,
    async_add_entities: AddEntitiesCallback,
    entity_class: type[RestoreAlarmEntity],
    domain: str,
) -> None:
    """Add, keep and remove one entity per alarm slot, as alarms come and go.

    Args:
        hass: Home Assistant instance.
        config_entry: The config entry.
        coordinator: The integration's coordinator.
        async_add_entities: The platform's add-entities callback.
        entity_class: The alarm entity to create per slot.
        domain: The platform's domain, for clearing registry entries.
    """
    entities: dict[str, RestoreAlarmEntity] = {}
    suffix = entity_class.unique_id_suffix

    async def async_reconcile() -> None:
        """Match the entities to the slots each device has now."""
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
                number = coordinator.restore_alarm_slots.number(thing_name, slot_key)
                current.add(unique_id)
                if unique_id in entities or number is None:
                    continue
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
