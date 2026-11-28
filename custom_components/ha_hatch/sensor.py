"""Sensor platform for Hatch devices."""

# brightness
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import logging
from typing import Any

from hatch_rest_api import RestIot, Restore, RestoreIot, RestoreV5, RestPlus
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .alarm import (
    alarm_base_names,
    alarm_by_id,
    alarm_repeat_attributes,
    alarm_repeat_label,
    alarm_unique_id,
    alarm_unique_id_prefix,
    remove_stale_alarm_entities,
    update_alarm_entity_names,
)
from .const import DOMAIN
from .hatch_data_update_coordinator import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity
from .restore_entities import (
    RestoreAlarmRepeat,
    RestoreFirmwareVersion,
    RestorePlaying,
    RestoreSignalStrength,
    async_setup_restore_alarm_entities,
)

_LOGGER = logging.getLogger(__name__)
ALARM_REPEAT_UNIQUE_ID_SUFFIX = "_repeat"


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the platform from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    sensor_entities: list[SensorEntity] = []
    for rest_device in coordinator.rest_devices:
        if isinstance(rest_device, (RestPlus, RestIot)):
            sensor_entities.append(
                HatchBattery(coordinator=coordinator, thing_name=rest_device.thing_name)
            )
        if isinstance(rest_device, RestIot):
            sensor_entities.append(
                HatchCharging(coordinator=coordinator, thing_name=rest_device.thing_name)
            )
        if isinstance(rest_device, Restore):
            sensor_entities.extend(
                sensor_class(coordinator=coordinator, thing_name=rest_device.thing_name)
                for sensor_class in (RestorePlaying, RestoreFirmwareVersion, RestoreSignalStrength)
            )
    async_add_entities(sensor_entities)
    await async_setup_restore_alarm_entities(
        hass, config_entry, coordinator, async_add_entities, RestoreAlarmRepeat, "sensor"
    )

    alarm_entities_by_unique_id: dict[str, HatchAlarmRepeat] = {}

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
            for alarm_id, alarm_name in alarm_base_names(getattr(rest_device, "alarms", [])):
                unique_id = alarm_unique_id(
                    rest_device.thing_name,
                    alarm_id,
                    ALARM_REPEAT_UNIQUE_ID_SUFFIX,
                )
                repeat_name = f"{alarm_name} Repeat"
                current_alarm_unique_ids.add(unique_id)
                current_alarm_names[unique_id] = repeat_name
                if alarm_entity := alarm_entities_by_unique_id.get(unique_id):
                    alarm_entity.update_alarm_name(repeat_name)
                    continue

                alarm_entity = HatchAlarmRepeat(
                    coordinator=coordinator,
                    thing_name=rest_device.thing_name,
                    alarm_id=alarm_id,
                    alarm_name=repeat_name,
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
            domain="sensor",
            current_alarm_unique_ids=current_alarm_unique_ids,
            authoritative_alarm_unique_id_prefixes=authoritative_alarm_unique_id_prefixes,
            unique_id_suffix=ALARM_REPEAT_UNIQUE_ID_SUFFIX,
        )
        update_alarm_entity_names(
            hass=hass,
            config_entry=config_entry,
            domain="sensor",
            current_alarm_names=current_alarm_names,
        )
        if new_alarm_entities:
            async_add_entities(new_alarm_entities)

    await async_reconcile_alarm_entities()
    config_entry.async_on_unload(
        coordinator.async_add_alarm_refresh_callback(async_reconcile_alarm_entities)
    )


class HatchBattery(HatchEntity[RestPlus | RestIot], SensorEntity):
    """Hatch battery."""

    entity_description = SensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        icon="mdi:battery",
        native_unit_of_measurement=PERCENTAGE,
    )

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the hatch battery."""
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Battery")

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the native value."""
        return self.rest_device.battery_level


class HatchCharging(HatchEntity[RestIot], SensorEntity):
    """Hatch charging."""

    entity_description = SensorEntityDescription(
        key="charging",
        icon="mdi:power-plug",
    )

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the hatch charging."""
        super().__init__(
            coordinator=coordinator, thing_name=thing_name, entity_type="Charging Status"
        )

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the native value."""
        if self.rest_device.charging_status == 0:
            return "Not Charging"
        if self.rest_device.charging_status == 3:
            return "Charging, plugged in"
        if self.rest_device.charging_status == 5:
            return "Charging, on base"
        return None

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self._attr_native_value == "Not Charging":
            return "mdi:power-plug-off"
        return self.entity_description.icon


class HatchAlarmRepeat(HatchEntity[RestoreIot | RestoreV5], SensorEntity):
    """Hatch alarm repeat."""

    entity_description = SensorEntityDescription(
        key="alarm-repeat",
        icon="mdi:calendar-week",
    )

    def __init__(
        self,
        coordinator: HatchDataUpdateCoordinator,
        thing_name: str,
        alarm_id: int | str,
        alarm_name: str,
        unique_id: str,
    ) -> None:
        """Initialize the hatch alarm repeat."""
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
        """Update the alarm entity name."""
        if self._attr_name == alarm_name:
            return
        self._attr_name = alarm_name
        if getattr(self, "hass", None) is not None:
            self.schedule_update_ha_state()

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return self._alarm is not None

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the native value."""
        alarm = self._alarm
        if alarm is None:
            return None
        return alarm_repeat_label(alarm.get("daysOfWeek"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return alarm_repeat_attributes(self._alarm)

    @property
    def _alarm(self) -> dict[str, Any] | None:
        return alarm_by_id(self.rest_device, self._alarm_id)
