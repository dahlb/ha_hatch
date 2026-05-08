from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass, SwitchEntityDescription,
)
from hatch_rest_api import RestPlus, RestIot, RestBaby
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import DOMAIN
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)
DEFAULT_ALARM_NAME = "alarm default name"
ALARM_UNIQUE_ID_MARKER = "_alarm_"
ALARM_UNIQUE_ID_SUFFIX = "_switch"


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    entities = []
    current_alarm_unique_ids = set()
    authoritative_alarm_unique_id_prefixes = set()
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
        if getattr(rest_device, "alarms_loaded", False):
            authoritative_alarm_unique_id_prefixes.add(
                _alarm_unique_id_prefix(rest_device.thing_name)
            )
        for alarm_id, alarm_name in _alarm_switch_names(getattr(rest_device, "alarms", [])):
            unique_id = _alarm_unique_id(rest_device.thing_name, alarm_id)
            current_alarm_unique_ids.add(unique_id)
            entities.append(
                HatchAlarmSwitch(
                    coordinator=coordinator,
                    thing_name=rest_device.thing_name,
                    alarm_id=alarm_id,
                    alarm_name=alarm_name,
                    unique_id=unique_id,
                )
            )

    _remove_stale_alarm_switch_entities(
        hass=hass,
        config_entry=config_entry,
        current_alarm_unique_ids=current_alarm_unique_ids,
        authoritative_alarm_unique_id_prefixes=authoritative_alarm_unique_id_prefixes,
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


class HatchAlarmSwitch(HatchEntity, SwitchEntity):
    entity_description = SwitchEntityDescription(
        key="alarm-switch",
        icon="mdi:alarm",
        device_class=SwitchDeviceClass.SWITCH,
    )

    def __init__(
        self,
        coordinator: HatchDataUpdateCoordinator,
        thing_name: str,
        alarm_id: int | str,
        alarm_name: str,
        unique_id: str,
    ):
        self._alarm_id = alarm_id
        self._alarm_display_name = alarm_name
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Alarm",
        )
        self._attr_unique_id = unique_id
        self._attr_has_entity_name = True
        self._attr_name = alarm_name

    @property
    def available(self) -> bool:
        return self._alarm is not None

    @property
    def is_on(self) -> bool | None:
        alarm = self._alarm
        if alarm is None:
            return None
        return bool(alarm.get("enabled"))

    async def async_turn_on(self, **kwargs):
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs):
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        set_alarm_enabled = getattr(self.rest_device, "set_alarm_enabled", None)
        if not callable(set_alarm_enabled):
            raise TypeError(
                f"{self.rest_device.device_name} does not support alarm switches"
            )
        await set_alarm_enabled(self._alarm_id, enabled)
        self.async_write_ha_state()

    @property
    def _alarm(self) -> dict[str, Any] | None:
        alarm_by_id = getattr(self.rest_device, "alarm_by_id", None)
        if callable(alarm_by_id):
            return alarm_by_id(self._alarm_id)
        alarm_id_string = str(self._alarm_id)
        return next(
            (
                alarm
                for alarm in getattr(self.rest_device, "alarms", [])
                if str(alarm.get("id")) == alarm_id_string
            ),
            None,
        )


def _alarm_switch_names(alarms: list[dict[str, Any]]):
    default_alarm_count = 0
    for alarm in alarms:
        alarm_id = alarm.get("id")
        if alarm_id is None:
            continue

        alarm_name = _clean_alarm_name(alarm.get("name"))
        if _is_default_alarm_name(alarm_name):
            default_alarm_count += 1
            alarm_name = "Default" if default_alarm_count == 1 else str(default_alarm_count)

        yield alarm_id, f"Alarm - {alarm_name}"


def _clean_alarm_name(alarm_name: Any) -> str:
    if alarm_name is None:
        return ""
    return " ".join(str(alarm_name).replace("_", " ").split())


def _is_default_alarm_name(alarm_name: str) -> bool:
    return alarm_name.lower() in {"", "default", DEFAULT_ALARM_NAME}


def _alarm_unique_id(thing_name: str, alarm_id: int | str) -> str:
    return f"{_alarm_unique_id_prefix(thing_name)}{alarm_id}{ALARM_UNIQUE_ID_SUFFIX}"


def _alarm_unique_id_prefix(thing_name: str) -> str:
    return f"{thing_name}{ALARM_UNIQUE_ID_MARKER}"


def _remove_stale_alarm_switch_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    current_alarm_unique_ids: set[str],
    authoritative_alarm_unique_id_prefixes: set[str],
) -> None:
    if not authoritative_alarm_unique_id_prefixes:
        return

    entity_registry = er.async_get(hass)
    for entry in er.async_entries_for_config_entry(
        entity_registry,
        config_entry.entry_id,
    ):
        if entry.domain != "switch":
            continue
        if entry.unique_id in current_alarm_unique_ids:
            continue
        if _is_alarm_unique_id_for_authoritative_device(
            entry.unique_id,
            authoritative_alarm_unique_id_prefixes,
        ):
            entity_registry.async_remove(entry.entity_id)


def _is_alarm_unique_id_for_authoritative_device(
    unique_id: str,
    authoritative_alarm_unique_id_prefixes: set[str],
) -> bool:
    return unique_id.endswith(ALARM_UNIQUE_ID_SUFFIX) and any(
        unique_id.startswith(prefix)
        for prefix in authoritative_alarm_unique_id_prefixes
    )
