from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)

from .alarm import (
    alarm_reference_from_unique_id,
    normalize_alarm_weekdays,
)
from .const import DOMAIN
from .hatch_data_update_coordinator import HatchDataUpdateCoordinator

ATTR_WEEKDAYS = "weekdays"
SERVICE_SET_ALARM_WEEKDAYS = "set_alarm_weekdays"
ALARM_SERVICE_UNIQUE_ID_SUFFIXES = {"_switch"}


def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SET_ALARM_WEEKDAYS):
        return

    async def async_set_alarm_weekdays(call: ServiceCall) -> None:
        await _async_set_alarm_weekdays(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ALARM_WEEKDAYS,
        async_set_alarm_weekdays,
        schema=cv.make_entity_service_schema(
            {vol.Optional(ATTR_WEEKDAYS, default=list): _validate_weekdays}
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
        raise ServiceValidationError("Target at least one Hatch alarm entity")

    for rest_device, _alarm_id in alarm_targets.values():
        if not callable(getattr(rest_device, "set_alarm_weekdays", None)):
            raise ServiceValidationError(
                f"{rest_device.device_name} does not support alarm weekdays"
            )

    weekdays = call.data[ATTR_WEEKDAYS]
    for rest_device, alarm_id in alarm_targets.values():
        await rest_device.set_alarm_weekdays(alarm_id, weekdays)


def _alarm_targets_from_service_call(
    hass: HomeAssistant,
    coordinator: HatchDataUpdateCoordinator,
    call: ServiceCall,
) -> dict[tuple[str, str], tuple[Any, str]]:
    entity_registry = er.async_get(hass)
    targets: dict[tuple[str, str], tuple[Any, str]] = {}

    selected = async_extract_referenced_entity_ids(
        hass, TargetSelection(call.data), expand_group=True
    )

    for entity_id in selected.referenced:
        target = _alarm_target_from_entity_id(
            entity_registry,
            coordinator,
            entity_id,
            raise_if_not_alarm=True,
        )
        if target is not None:
            key, value = target
            targets[key] = value

    for entity_id in selected.indirectly_referenced:
        target = _alarm_target_from_entity_id(
            entity_registry,
            coordinator,
            entity_id,
            raise_if_not_alarm=False,
        )
        if target is not None:
            key, value = target
            targets[key] = value

    return targets


def _alarm_target_from_entity_id(
    entity_registry: er.EntityRegistry,
    coordinator: HatchDataUpdateCoordinator,
    entity_id: str,
    *,
    raise_if_not_alarm: bool,
) -> tuple[tuple[str, str], tuple[Any, str]] | None:
    entry = entity_registry.async_get(entity_id)
    if entry is None or entry.platform != DOMAIN:
        if raise_if_not_alarm:
            raise ServiceValidationError(f"{entity_id} is not a Hatch alarm entity")
        return None

    alarm_reference = alarm_reference_from_unique_id(
        entry.unique_id,
        ALARM_SERVICE_UNIQUE_ID_SUFFIXES,
    )
    if alarm_reference is None:
        if raise_if_not_alarm:
            raise ServiceValidationError(f"{entity_id} is not a Hatch alarm entity")
        return None

    thing_name, alarm_id = alarm_reference
    rest_device = coordinator.rest_device_by_thing_name(thing_name)
    if rest_device is None:
        if raise_if_not_alarm:
            raise ServiceValidationError(
                f"{entity_id} belongs to a Hatch device that is not loaded"
            )
        return None

    return (thing_name, alarm_id), (rest_device, alarm_id)
