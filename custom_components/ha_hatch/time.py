from __future__ import annotations

import logging
from datetime import time
from typing import Any

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .alarm import (
    alarm_base_names,
    alarm_by_id,
    alarm_repeat_attributes,
    alarm_unique_id,
    alarm_unique_id_prefix,
    alarm_wake_time,
    remove_stale_alarm_entities,
    update_alarm_entity_names,
)
from .const import DOMAIN
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)
ALARM_WAKE_TIME_UNIQUE_ID_SUFFIX = "_wake_time"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    alarm_entities_by_unique_id: dict[str, HatchAlarmWakeTime] = {}

    async def async_reconcile_alarm_entities() -> None:
        new_alarm_entities = []
        current_alarm_unique_ids = set()
        current_alarm_names = {}
        authoritative_alarm_unique_id_prefixes = set()
        for rest_device in coordinator.rest_devices:
            if getattr(rest_device, "alarms_loaded", False):
                authoritative_alarm_unique_id_prefixes.add(
                    alarm_unique_id_prefix(rest_device.thing_name)
                )
            for alarm_id, alarm_name in alarm_base_names(
                getattr(rest_device, "alarms", [])
            ):
                unique_id = alarm_unique_id(
                    rest_device.thing_name,
                    alarm_id,
                    ALARM_WAKE_TIME_UNIQUE_ID_SUFFIX,
                )
                wake_time_name = f"{alarm_name} Wake Time"
                current_alarm_unique_ids.add(unique_id)
                current_alarm_names[unique_id] = wake_time_name
                if alarm_entity := alarm_entities_by_unique_id.get(unique_id):
                    alarm_entity.update_alarm_name(wake_time_name)
                    continue

                alarm_entity = HatchAlarmWakeTime(
                    coordinator=coordinator,
                    thing_name=rest_device.thing_name,
                    alarm_id=alarm_id,
                    alarm_name=wake_time_name,
                    unique_id=unique_id,
                )
                alarm_entities_by_unique_id[unique_id] = alarm_entity
                new_alarm_entities.append(alarm_entity)

        for unique_id in set(alarm_entities_by_unique_id) - current_alarm_unique_ids:
            alarm_entity = alarm_entities_by_unique_id.pop(unique_id)
            await alarm_entity.async_remove(force_remove=True)

        remove_stale_alarm_entities(
            hass=hass,
            config_entry=config_entry,
            domain="time",
            current_alarm_unique_ids=current_alarm_unique_ids,
            authoritative_alarm_unique_id_prefixes=authoritative_alarm_unique_id_prefixes,
            unique_id_suffix=ALARM_WAKE_TIME_UNIQUE_ID_SUFFIX,
        )
        update_alarm_entity_names(
            hass=hass,
            config_entry=config_entry,
            domain="time",
            current_alarm_names=current_alarm_names,
        )
        if new_alarm_entities:
            async_add_entities(new_alarm_entities)

    await async_reconcile_alarm_entities()
    config_entry.async_on_unload(
        coordinator.async_add_alarm_refresh_callback(async_reconcile_alarm_entities)
    )


class HatchAlarmWakeTime(HatchEntity, TimeEntity):
    entity_description = TimeEntityDescription(
        key="alarm-wake-time",
        icon="mdi:alarm",
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
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Alarm",
        )
        self._attr_unique_id = unique_id
        self._attr_has_entity_name = True
        self._attr_name = alarm_name

    def update_alarm_name(self, alarm_name: str) -> None:
        if self._attr_name == alarm_name:
            return
        self._attr_name = alarm_name
        if getattr(self, "hass", None) is not None:
            self.schedule_update_ha_state()

    @property
    def available(self) -> bool:
        return self._alarm is not None

    @property
    def native_value(self) -> time | None:
        return alarm_wake_time(self._alarm)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return alarm_repeat_attributes(self._alarm)

    async def async_set_value(self, value: time) -> None:
        set_alarm_wake_time = getattr(self.rest_device, "set_alarm_wake_time", None)
        if not callable(set_alarm_wake_time):
            raise TypeError(
                f"{self.rest_device.device_name} does not support alarm wake times"
            )
        await set_alarm_wake_time(self._alarm_id, value)
        self.schedule_update_ha_state()

    @property
    def _alarm(self) -> dict[str, Any] | None:
        return alarm_by_id(self.rest_device, self._alarm_id)
