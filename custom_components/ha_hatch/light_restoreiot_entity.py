from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
)
from logging import getLogger

from . import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity

_LOGGER = getLogger(__name__)


class LightRestoreIotEntity(HatchEntity, LightEntity):
    _attr_color_mode = ColorMode.RGBW
    _attr_supported_color_modes = {ColorMode.RGBW}

    _last_light_on_colors = {
        "r": 127,
        "g": 127,
        "b": 127,
        "w": 127,
        "brightness": 50,
    }

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Light")

    @property
    def is_on(self) -> bool | None:
        if self.rest_device.is_light_on:
            self._last_light_on_colors["r"] = self.rest_device.red
            self._last_light_on_colors["g"] = self.rest_device.green
            self._last_light_on_colors["b"] = self.rest_device.blue
            self._last_light_on_colors["w"] = self.rest_device.white
            self._last_light_on_colors["brightness"] = self.rest_device.brightness
        return self.rest_device.is_light_on

    @property
    def brightness(self) -> int | None:
        return int(round(self.rest_device.brightness / 100 * 255.0, 0))

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        return (
            self.rest_device.red,
            self.rest_device.green,
            self.rest_device.blue,
            self.rest_device.white,
        )

    def turn_on(self, **kwargs):
        _LOGGER.debug(f"args:{kwargs}")
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
            offset = max(0, min(min(white, 255 - max_value), 255))
            red += offset
            green += offset
            blue += offset

        _LOGGER.debug(f"Changing light rgbw to ({red},{green},{blue},{white}) and brightness to {brightness}")
        self.rest_device.set_color(red, green, blue, white, brightness)

    def turn_off(self):
        self.rest_device.turn_light_off()
