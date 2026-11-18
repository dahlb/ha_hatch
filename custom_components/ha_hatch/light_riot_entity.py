"""Light entity for Hatch Rest+ (riot) devices."""

from __future__ import annotations

from logging import getLogger
from typing import ClassVar

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ColorMode, LightEntity

from . import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity

_LOGGER = getLogger(__name__)


class LightRiotEntity(HatchEntity, LightEntity):
    """Light riot entity."""

    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.RGB}

    _DEFAULT_LIGHT_ON_COLORS: ClassVar[dict[str, int]] = {
        "r": 127,
        "g": 127,
        "b": 127,
        "brightness": 50,
    }

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the light riot entity."""
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Light")
        self._last_light_on_colors: dict[str, int] = dict(self._DEFAULT_LIGHT_ON_COLORS)

    @property
    def is_on(self) -> bool | None:
        """Return whether the entity is on."""
        if self.rest_device.is_light_on:
            self._last_light_on_colors["r"] = self.rest_device.red
            self._last_light_on_colors["g"] = self.rest_device.green
            self._last_light_on_colors["b"] = self.rest_device.blue
            self._last_light_on_colors["brightness"] = self.rest_device.brightness
        return self.rest_device.is_light_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness."""
        return int(round(self.rest_device.brightness / 100 * 255.0, 0))

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [int, int, int]."""
        return (
            self.rest_device.red,
            self.rest_device.green,
            self.rest_device.blue,
        )

    def turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        _LOGGER.debug("args:%s", kwargs)
        if ATTR_BRIGHTNESS in kwargs:
            # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
            # If 100 is sent to Abode, response is 99 causing an error
            brightness = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255.0)
        else:
            brightness = round(self.brightness * 100 / 255.0)
        rgb = kwargs.get(ATTR_RGB_COLOR, self.rgb_color)

        if kwargs:
            _LOGGER.debug("Changing light rgb to %s and brightness to %s", rgb, brightness)
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

    def turn_off(self) -> None:
        """Turn the entity off."""
        self.rest_device.turn_light_off()
