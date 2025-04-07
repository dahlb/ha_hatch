from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from logging import getLogger

from . import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity

_LOGGER = getLogger(__name__)


class LightRiotEntity(HatchEntity, LightEntity):
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    _last_light_on_colors = {
        "r": 127,
        "g": 127,
        "b": 127,
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
            self._last_light_on_colors["brightness"] = self.rest_device.brightness
        return self.rest_device.is_light_on

    @property
    def brightness(self) -> int | None:
        return int(round(self.rest_device.brightness / 100 * 255.0, 0))

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [int, int, int]."""
        return (
            self.rest_device.red,
            self.rest_device.green,
            self.rest_device.blue,
        )

    def turn_on(self, **kwargs):
        _LOGGER.debug(f"args:{kwargs}")
        if ATTR_BRIGHTNESS in kwargs:
            # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
            # If 100 is sent to Abode, response is 99 causing an error
            brightness = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255.0)
        else:
            brightness = round(self._attr_brightness * 100 / 255.0)
        rgb = kwargs.get(ATTR_RGB_COLOR, self._attr_rgb_color)

        if kwargs:
            _LOGGER.debug(f"Changing light rgb to {rgb} and brightness to {brightness}")
            white = 0
            if rgb[0] == 255 and rgb[1] == 255 and rgb[2] == 255:
                white = 65535
            self.rest_device.set_color(rgb[0], rgb[1], rgb[2], white, brightness)
        else:
            # Turn on the light to the last known state/default state
            self.rest_device.set_color(
                self._last_light_on_colors["r"],
                self._last_light_on_colors["g"],
                self._last_light_on_colors["b"],
                0,
                self._last_light_on_colors["brightness"],
            )

    def turn_off(self):
        self.rest_device.turn_light_off()
