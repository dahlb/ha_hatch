"""Light entity for Hatch Restore IoT devices."""

from __future__ import annotations

from logging import getLogger
from typing import ClassVar

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGBW_COLOR, ColorMode, LightEntity

from . import HatchDataUpdateCoordinator
from .commands import translate_command_errors
from .hatch_entity import HatchEntity

_LOGGER = getLogger(__name__)


class LightRestoreIotEntity(HatchEntity, LightEntity):
    """Light restore iot entity."""

    _attr_color_mode = ColorMode.RGBW
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.RGBW}

    _DEFAULT_LIGHT_ON_COLORS: ClassVar[dict[str, int]] = {
        "r": 127,
        "g": 127,
        "b": 127,
        "w": 127,
        "brightness": 50,
    }

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the light restore iot entity."""
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Light")
        self._last_light_on_colors: dict[str, int] = dict(self._DEFAULT_LIGHT_ON_COLORS)

    @property
    def is_on(self) -> bool | None:
        """Return whether the entity is on."""
        if self.rest_device.is_light_on:
            self._last_light_on_colors["r"] = self.rest_device.red
            self._last_light_on_colors["g"] = self.rest_device.green
            self._last_light_on_colors["b"] = self.rest_device.blue
            self._last_light_on_colors["w"] = self.rest_device.white
            self._last_light_on_colors["brightness"] = self.rest_device.brightness
        return self.rest_device.is_light_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness."""
        return int(round(self.rest_device.brightness / 100 * 255.0, 0))

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        """Return the RGBW color."""
        return (
            self.rest_device.red,
            self.rest_device.green,
            self.rest_device.blue,
            self.rest_device.white,
        )

    @translate_command_errors
    def turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        _LOGGER.debug("args:%s", kwargs)
        if not kwargs:
            # Turn on the light to the last known state/default state
            self.rest_device.set_color(
                self._last_light_on_colors["r"],
                self._last_light_on_colors["g"],
                self._last_light_on_colors["b"],
                self._last_light_on_colors["w"],
                self._last_light_on_colors["brightness"],
            )
            return

        # Convert Home Assistant brightness (0-255) to percent (0-100)
        brightness = round(kwargs.get(ATTR_BRIGHTNESS, self.brightness) / 255 * 100)
        red, green, blue, white = kwargs.get(ATTR_RGBW_COLOR, self.rgbw_color)

        # Add white offset to RGB values to prevent black display in the Hatch
        # app when setting white values. Matches Android app behavior.
        if white and white > 0:
            max_value = max(red, green, blue)
            offset = max(0, min(white, 255 - max_value, 255))
            red += offset
            green += offset
            blue += offset

        _LOGGER.debug(
            "Changing light rgbw to (%s,%s,%s,%s) and brightness to %s",
            red,
            green,
            blue,
            white,
            brightness,
        )
        self.rest_device.set_color(red, green, blue, white, brightness)

    @translate_command_errors
    def turn_off(self) -> None:
        """Turn the entity off."""
        self.rest_device.turn_light_off()
