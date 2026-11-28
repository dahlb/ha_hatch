"""Clock light entity for Hatch Rest+ (riot) devices."""

from __future__ import annotations

from datetime import time as dt_time
from logging import getLogger
from typing import Any

from hatch_rest_api import RestoreV5
from hatch_rest_api.iot_device import IotDevice
from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.util import dt as dt_util

from .commands import translate_command_errors
from .hatch_data_update_coordinator import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity

_LOGGER = getLogger(__name__)


def _parse_clock_time(value: str | None) -> dt_time | None:
    """Parse a shadow clock time string ("HH:MM" or "HH:MM:SS") to a time."""
    if not value:
        return None
    parts = value.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        second = int(parts[2]) if len(parts) > 2 else 0
        return dt_time(hour, minute, second)
    except ValueError, IndexError:
        return None


def _clock_active_is_daytime(dev: RestoreV5) -> bool:
    """Return True when the device is currently showing its daytime brightness.

    The daytime channel is active between turnBrightAt and turnDimAt, the
    nighttime channel otherwise. This applies whenever the clock is on (Always
    On and Off at Night) - the mode only controls when the display turns fully
    off, not which brightness is shown.
    """
    bright_at = _parse_clock_time(dev.clock_turn_bright_at)
    dim_at = _parse_clock_time(dev.clock_turn_dim_at)
    if bright_at is None or dim_at is None:
        return False
    now = dt_util.now().time()
    if bright_at <= dim_at:
        return bright_at <= now < dim_at
    return now >= bright_at or now < dim_at


class LightRiotClockEntity(HatchEntity[IotDevice], LightEntity):
    """Light riot clock entity."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_icon = "mdi:clock"

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the light riot clock entity."""
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Clock")
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool | None:
        """Return whether the entity is on."""
        return self.rest_device.is_clock_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness."""
        dev = self.rest_device
        # The Restore 3 (and Restore 2) has separate day and night brightness.
        if isinstance(dev, RestoreV5):
            channel = dev.clock_daytime if _clock_active_is_daytime(dev) else dev.clock_nighttime
        else:
            channel = getattr(dev, "clock", None)
        return round((channel or 0.0) / 100 * 255.0)

    @translate_command_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("args:%s", kwargs)
        if ATTR_BRIGHTNESS in kwargs:
            # Convert Home Assistant brightness (0-255) to device brightness (0-100)
            brightness = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255.0)
        else:
            brightness = round((self.brightness or 0) * 100 / 255.0)
        dev = self.rest_device
        # Drive only the channel the clock is currently displaying so the slider
        # tracks what the user sees. The number entities set each independently.
        if isinstance(dev, RestoreV5):
            if _clock_active_is_daytime(dev):
                await dev.async_command(dev.set_clock, daytime_brightness=brightness)
            else:
                await dev.async_command(dev.set_clock, nighttime_brightness=brightness)
        else:
            await dev.async_command(dev.set_clock, brightness)

    @translate_command_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turn off clock")
        await self.rest_device.async_command(self.rest_device.turn_clock_off)
