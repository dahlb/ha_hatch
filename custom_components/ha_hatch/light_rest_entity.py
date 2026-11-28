"""Light entity for Hatch Rest devices."""

from __future__ import annotations

from logging import getLogger
from typing import Any, ClassVar

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ColorMode, LightEntity

from . import HatchDataUpdateCoordinator
from .commands import translate_command_errors
from .hatch_entity import HatchEntity

_LOGGER = getLogger(__name__)


class LightRestEntity(HatchEntity, LightEntity):
    """Light rest entity."""

    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.RGB}

    def __init__(
        self, coordinator: HatchDataUpdateCoordinator, thing_name: str, config_turn_on_light: bool
    ) -> None:
        """Initialize the light rest entity."""
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Light")
        self.config_turn_on_light = config_turn_on_light

    @property
    def is_on(self) -> bool | None:
        """Return whether the entity is on."""
        return self.rest_device.is_on and self.rest_device.brightness > 0

    @property
    def brightness(self) -> int | None:
        """Return the brightness."""
        return int(round(self.rest_device.brightness / 100 * 255.0, 0))

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the RGB color."""
        return (
            self.rest_device.red,
            self.rest_device.green,
            self.rest_device.blue,
        )

    @translate_command_errors
    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        _LOGGER.debug("args:%s", kwargs)
        if ATTR_BRIGHTNESS in kwargs:
            # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
            # If 100 is sent to Abode, response is 99 causing an error
            brightness = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255.0)
        else:
            brightness = round(self.brightness * 100 / 255.0)
        rgb = kwargs.get(ATTR_RGB_COLOR, self.rgb_color)

        _LOGGER.debug("turning on light to %s with %s", rgb, brightness)
        await self.rest_device.async_command(
            self.rest_device.set_color, rgb[0], rgb[1], rgb[2], brightness
        )
        if self.config_turn_on_light:
            _LOGGER.debug("auto turning on the hatch power switch for the light")
            await self.rest_device.async_command(self.rest_device.set_on, True)

    @translate_command_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.rest_device.async_command(
            self.rest_device.set_color,
            self.rest_device.red,
            self.rest_device.green,
            self.rest_device.blue,
            0,
        )
