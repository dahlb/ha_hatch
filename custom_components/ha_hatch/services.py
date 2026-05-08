from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .alarm import (
    alarm_reference_from_unique_id,
    normalize_alarm_weekdays,
)
from .const import DOMAIN
from .hatch_data_update_coordinator import HatchDataUpdateCoordinator

ATTR_WEEKDAYS = "weekdays"
SERVICE_SET_ALARM_WEEKDAYS = "set_alarm_weekdays"
ALARM_SERVICE_UNIQUE_ID_SUFFIXES = {"_switch", "_wake_time"}


def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SET_ALARM_WEEKDAYS):
        return

    async def async_set_alarm_weekdays(call: ServiceCall) -> None:
        await _async_set_alarm_weekdays(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ALARM_WEEKDAYS,
        async_set_alarm_weekdays,
        schema=vol.Schema(
            {
                vol.Required(ATTR_WEEKDAYS): _validate_weekdays,
                vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
            }
        ),
    )


def _validate_weekdays(value: Any) -> list[str]:
    try:
        return normalize_alarm_weekdays(value)
    except ValueError as error:
        raise vol.Invalid(str(error)) from error


async def _async_set_alarm_weekdays(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    coordinator = hass.data.get(DOMAIN)
    if not isinstance(coordinator, HatchDataUpdateCoordinator):
        raise HomeAssistantError("Hatch integration is not loaded")

    alarm_targets = _alarm_targets_from_service_call(hass, coordinator, call)
    if not alarm_targets:
        raise HomeAssistantError("Target at least one Hatch alarm entity")

    weekdays = call.data[ATTR_WEEKDAYS]
    for rest_device, alarm_id in alarm_targets.values():
        set_alarm_weekdays = getattr(rest_device, "set_alarm_weekdays", None)
        if not callable(set_alarm_weekdays):
            raise HomeAssistantError(
                f"{rest_device.device_name} does not support alarm weekdays"
            )
        await set_alarm_weekdays(alarm_id, weekdays)


def _alarm_targets_from_service_call(
    hass: HomeAssistant,
    coordinator: HatchDataUpdateCoordinator,
    call: ServiceCall,
) -> dict[tuple[str, str], tuple[Any, str]]:
    entity_registry = er.async_get(hass)
    targets: dict[tuple[str, str], tuple[Any, str]] = {}

    for entity_id in _service_call_entity_ids(call):
        entry = entity_registry.async_get(entity_id)
        if entry is None or entry.platform != DOMAIN:
            raise HomeAssistantError(f"{entity_id} is not a Hatch alarm entity")

        alarm_reference = alarm_reference_from_unique_id(
            entry.unique_id,
            ALARM_SERVICE_UNIQUE_ID_SUFFIXES,
        )
        if alarm_reference is None:
            raise HomeAssistantError(f"{entity_id} is not a Hatch alarm entity")

        thing_name, alarm_id = alarm_reference
        rest_device = coordinator.rest_device_by_thing_name(thing_name)
        if rest_device is None:
            raise HomeAssistantError(
                f"{entity_id} belongs to a Hatch device that is not loaded"
            )
        targets[(thing_name, alarm_id)] = (rest_device, alarm_id)

    return targets


def _service_call_entity_ids(call: ServiceCall) -> set[str]:
    entity_ids: set[str] = set()
    if entity_id := call.data.get(ATTR_ENTITY_ID):
        entity_ids.update(cv.entity_ids(entity_id))

    target = getattr(call, "target", None)
    if isinstance(target, dict) and (target_entity_id := target.get(ATTR_ENTITY_ID)):
        entity_ids.update(cv.entity_ids(target_entity_id))

    return entity_ids
