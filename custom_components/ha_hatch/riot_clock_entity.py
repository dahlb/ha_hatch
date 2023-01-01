from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
import logging
from hatch_rest_api import RestIot

from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)

class RiotClockEntity(RestEntity, LightEntity):
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_icon = "mdi:clock"

    def __init__(self, rest_device: RestIot ):
        super().__init__(rest_device, "Clock")

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        if isinstance(self.rest_device, RestIot):
            self._attr_is_on = self.rest_device.is_clock_on
        self._attr_brightness = (round(self.rest_device.clock / 100) * 255)
        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        _LOGGER.debug(f"args:{kwargs}")
        if ATTR_BRIGHTNESS in kwargs:
            # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
            # If 100 is sent to Abode, response is 99 causing an error
            brightness = (round(kwargs[ATTR_BRIGHTNESS] * 100) / 255)
        else:
            if isinstance(self.rest_device, RestIot):
                brightness = 0
            else:
                brightness = self._attr_brightness
        self.rest_device.set_clock(32768, brightness)
    
    def turn_off (self):
            _LOGGER.debug("turning off with flags = 0 and bright = 655")
            self.rest_device.set_clock(0, 655)