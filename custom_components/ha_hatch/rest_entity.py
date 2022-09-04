from abc import ABC, abstractmethod
from hatch_rest_api import RestPlus, RestMini
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


class RestEntity(ABC):
    def __init__(self, rest_device: RestMini | RestPlus, entity_type: str):
        self._attr_unique_id = f"{rest_device.thing_name}_{entity_type.lower().replace(' ', '_')}"
        self._attr_name = f"{rest_device.device_name} {entity_type}"
        self.rest_device = rest_device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, rest_device.thing_name)},
            manufacturer="Hatch",
            model=rest_device.__class__.__name__,
            name=rest_device.device_name,
            sw_version=self.rest_device.firmware_version,
        )
        self.rest_device.register_callback(self._update_local_state)

    def replace_rest_device(self, rest_device: RestMini | RestPlus):
        self.rest_device.remove_callback(self._update_local_state)
        self.rest_device = rest_device
        self.rest_device.register_callback(self._update_local_state)

    @abstractmethod
    def _update_local_state(self):
        pass

    async def async_added_to_hass(self):
        if self.rest_device.is_playing is not None:
            self._update_local_state()

    def turn_on(self):
        if isinstance(self.rest_device, RestMini):
            raise NotImplementedError()
        self.rest_device.set_on(True)

    def turn_off(self):
        if isinstance(self.rest_device, RestMini):
            raise NotImplementedError()
        self.rest_device.set_on(False)
