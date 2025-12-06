from __future__ import annotations

import logging
from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass, SwitchEntityDescription,
)
from hatch_rest_api import RestPlus, RestIot, RestBaby
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import DOMAIN
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    entities = []
    for rest_device in coordinator.rest_devices:
        if isinstance(rest_device, RestPlus):
            entities.append(HatchPowerSwitch(coordinator=coordinator, thing_name=rest_device.thing_name))
        if isinstance(rest_device, RestIot):
            entities.append(
                HatchToddlerLockSwitch(
                    coordinator=coordinator, thing_name=rest_device.thing_name
                )
            )
        if isinstance(rest_device, RestBaby):
            entities.append(
                HatchToddlerLockSwitch(
                    coordinator=coordinator, thing_name=rest_device.thing_name
                )
            )
            entities.append(
                HatchPowerSwitch(
                    coordinator=coordinator, thing_name=rest_device.thing_name
                )
            )

    async_add_entities(entities)


class HatchPowerSwitch(HatchEntity, SwitchEntity):
    entity_description: SwitchEntityDescription(
        key="power-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Power Switch")

    @property
    def is_on(self) -> bool | None:
        return self.rest_device.is_on

    def turn_on(self, **kwargs):
        self.rest_device.set_on(True)

    def turn_off(self, **kwargs):
        self.rest_device.set_on(False)


class HatchToddlerLockSwitch(HatchEntity, SwitchEntity):
    entity_description: SwitchEntityDescription(
        key="toddler-lock",
        icon="mdi:human-child",
        device_class=SwitchDeviceClass.SWITCH,
    )

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Toddler Lock")

    @property
    def is_on(self) -> bool | None:
        return self.rest_device.toddler_lock

    def turn_on(self, **kwargs):
        self.rest_device.set_toddler_lock(True)

    def turn_off(self, **kwargs):
        self.rest_device.set_toddler_lock(False)
