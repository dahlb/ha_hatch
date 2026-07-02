from __future__ import annotations

import logging

from hatch_rest_api import RestoreV5
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import DOMAIN
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    entities = []
    for rest_device in coordinator.rest_devices:
        # RestoreV4 subclasses RestoreV5, so this covers both.
        if isinstance(rest_device, RestoreV5):
            entities.append(
                ClockDaytimeBrightnessNumber(
                    coordinator=coordinator,
                    thing_name=rest_device.thing_name,
                )
            )
            entities.append(
                ClockNighttimeBrightnessNumber(
                    coordinator=coordinator,
                    thing_name=rest_device.thing_name,
                )
            )
    async_add_entities(entities)


class ClockDaytimeBrightnessNumber(HatchEntity, NumberEntity):
    _attr_icon = "mdi:weather-sunny"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Clock Daytime Brightness",
        )

    @property
    def native_value(self) -> float | None:
        return self.rest_device.clock_daytime

    def set_native_value(self, value: float) -> None:
        self.rest_device.set_clock(daytime_brightness=int(value))


class ClockNighttimeBrightnessNumber(HatchEntity, NumberEntity):
    _attr_icon = "mdi:weather-night"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Clock Nighttime Brightness",
        )

    @property
    def native_value(self) -> float | None:
        return self.rest_device.clock_nighttime

    def set_native_value(self, value: float) -> None:
        self.rest_device.set_clock(nighttime_brightness=int(value))
