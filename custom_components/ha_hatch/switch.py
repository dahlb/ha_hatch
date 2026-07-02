from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass, SwitchEntityDescription,
)
from hatch_rest_api import RestPlus, RestIot, RestBaby, RestoreV5
from hatch_rest_api.const import RIOT_FLAGS_CLOCK_IGNORE_TAP
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
    remove_stale_alarm_entities,
    update_alarm_entity_names,
)
from .const import DOMAIN
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)
ALARM_UNIQUE_ID_SUFFIX = "_switch"


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
        # RestoreV4 subclasses RestoreV5, so this covers both.
        if isinstance(rest_device, RestoreV5):
            entities.append(
                HatchClockTapSwitch(
                    coordinator=coordinator, thing_name=rest_device.thing_name
                )
            )

    async_add_entities(entities)

    alarm_entities_by_unique_id: dict[str, HatchAlarmSwitch] = {}

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
                    ALARM_UNIQUE_ID_SUFFIX,
                )
                current_alarm_unique_ids.add(unique_id)
                current_alarm_names[unique_id] = alarm_name
                if alarm_entity := alarm_entities_by_unique_id.get(unique_id):
                    alarm_entity.update_alarm_name(alarm_name)
                    continue

                alarm_entity = HatchAlarmSwitch(
                    coordinator=coordinator,
                    thing_name=rest_device.thing_name,
                    alarm_id=alarm_id,
                    alarm_name=alarm_name,
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
            domain="switch",
            current_alarm_unique_ids=current_alarm_unique_ids,
            authoritative_alarm_unique_id_prefixes=authoritative_alarm_unique_id_prefixes,
            unique_id_suffix=ALARM_UNIQUE_ID_SUFFIX,
        )
        update_alarm_entity_names(
            hass=hass,
            config_entry=config_entry,
            domain="switch",
            current_alarm_names=current_alarm_names,
        )
        if new_alarm_entities:
            async_add_entities(new_alarm_entities)

    await async_reconcile_alarm_entities()
    config_entry.async_on_unload(
        coordinator.async_add_alarm_refresh_callback(async_reconcile_alarm_entities)
    )


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


class HatchClockTapSwitch(HatchEntity, SwitchEntity):
    _attr_icon = "mdi:gesture-tap"

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Clock Tap to Show",
        )

    @property
    def is_on(self) -> bool | None:
        flags = self.rest_device.flags
        if flags is None:
            return None
        return not (flags & RIOT_FLAGS_CLOCK_IGNORE_TAP)

    def turn_on(self, **kwargs):
        dev = self.rest_device
        dev._update({"clock": {"flags": dev.flags & ~RIOT_FLAGS_CLOCK_IGNORE_TAP}})

    def turn_off(self, **kwargs):
        dev = self.rest_device
        dev._update({"clock": {"flags": dev.flags | RIOT_FLAGS_CLOCK_IGNORE_TAP}})


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
    def is_on(self) -> bool | None:
        alarm = self._alarm
        if alarm is None:
            return None
        return bool(alarm.get("enabled"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return alarm_repeat_attributes(self._alarm)

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
        self.schedule_update_ha_state()

    @property
    def _alarm(self) -> dict[str, Any] | None:
        return alarm_by_id(self.rest_device, self._alarm_id)
