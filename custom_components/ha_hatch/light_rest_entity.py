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


class LightRestEntity(HatchEntity, LightEntity):
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str, config_turn_on_light: bool):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Light")
        self.config_turn_on_light = config_turn_on_light

    @property
    def is_on(self) -> bool | None:
        return self.rest_device.is_on and self.rest_device.brightness > 0

    @property
    def brightness(self) -> int | None:
        return int(round(self.rest_device.brightness / 100 * 255.0, 0))

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
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

        _LOGGER.debug(f"turning on light to {rgb} with {brightness}")
        self.rest_device.set_color(rgb[0], rgb[1], rgb[2], brightness)
        if self.config_turn_on_light:
            _LOGGER.debug("auto turning on the hatch power switch for the light")
            self.rest_device.set_on(True)

    def turn_off(self):
        self.rest_device.set_color(
            self.rest_device.red, self.rest_device.green, self.rest_device.blue, 0
        )
