from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
import logging
from hatch_rest_api import RestPlus, RestIot

from .const import (
    DOMAIN,
    DATA_REST_DEVICES,
    DATA_LIGHTS,
    CONFIG_TURN_ON_LIGHT,
    CONFIG_TURN_ON_DEFAULT,
)
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    hass.data.setdefault(DOMAIN, {})
    config_turn_on_light = config_entry.options.get(
        CONFIG_TURN_ON_LIGHT, CONFIG_TURN_ON_DEFAULT
    )

    _LOGGER.debug(f"setting up hatch lights, auto turn on switch set to {config_turn_on_light}")
    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]
    light_entities = []
    for rest_device in rest_devices:
        if isinstance(rest_device, RestPlus):
            light_entities.append(HatchLightEntity(rest_device, config_turn_on_light))
        elif isinstance(rest_device, RestIot):
            light_entities.append(HatchLightEntity(rest_device, False))
    hass.data[DOMAIN][DATA_LIGHTS] = light_entities
    async_add_entities(light_entities)


class HatchLightEntity(RestEntity, LightEntity):
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, rest_device: RestIot | RestPlus, config_turn_on_light: bool):
        super().__init__(rest_device, "Light")
        self.config_turn_on_light = config_turn_on_light

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        if isinstance(self.rest_device, RestIot):
            self._attr_is_on = self.rest_device.is_light_on
        else:
            self._attr_is_on = self.is_on
        self._attr_brightness = round(self.rest_device.brightness / 100 * 255.0, 0)
        self._attr_rgb_color = (self.rest_device.red, self.rest_device.green, self.rest_device.blue)
        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        _LOGGER.debug(f"args:{kwargs}")
        if ATTR_BRIGHTNESS in kwargs:
            # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
            # If 100 is sent to Abode, response is 99 causing an error
            brightness = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255.0)
        else:
            if isinstance(self.rest_device, RestIot):
                brightness = 0
            else:
                brightness = self._attr_brightness
        if ATTR_RGB_COLOR in kwargs:
            rgb = kwargs[ATTR_RGB_COLOR]
        else:
            rgb = self._attr_rgb_color

        _LOGGER.debug(f"turning on light to {rgb} with {brightness}")
        if isinstance(self.rest_device, RestIot):
            self.rest_device.set_color(rgb[0], rgb[1], rgb[2], 0, brightness, True)
        else:
            self.rest_device.set_color(rgb[0], rgb[1], rgb[2], brightness)
        if self.config_turn_on_light:
            _LOGGER.debug(f"auto turning on the hatch power switch for the light")
            self.rest_device.set_on(True)

    def turn_off(self):
        if isinstance(self.rest_device, RestIot):
            _LOGGER.debug("turning off with rgbw = 0 and bright = 0")
            self.rest_device.set_color(0, 0, 0, 0, 0, False)
        else:
            self.rest_device.set_color(self.rest_device.red, self.rest_device.green, self.rest_device.blue, 0)
