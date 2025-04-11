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
        if ATTR_BRIGHTNESS in kwargs:
            # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
            # If 100 is sent to Abode, response is 99 causing an error
            brightness = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255.0)
        else:
            brightness = round(self.brightness * 100 / 255.0)
        rgbw = kwargs.get(ATTR_RGBW_COLOR, self.rgbw_color)

        if kwargs:
            _LOGGER.debug(f"Changing light rgbw to {rgbw} and brightness to {brightness}")
            self.rest_device.set_color(rgbw[0], rgbw[1], rgbw[2], rgbw[3], brightness)
        else:
            # Turn on the light to the last known state/default state
            self.rest_device.set_color(
                self._last_light_on_colors["r"],
                self._last_light_on_colors["g"],
                self._last_light_on_colors["b"],
                self._last_light_on_colors["w"],
                self._last_light_on_colors["brightness"],
            )

    def turn_off(self):
        self.rest_device.turn_light_off()
