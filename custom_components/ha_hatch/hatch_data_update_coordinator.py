from datetime import timedelta, UTC, datetime
from logging import getLogger, Logger
from typing import List

from hatch_rest_api import RestMini, RestPlus, RestIot, RestoreIot
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.ha_hatch import DOMAIN

_LOGGER: Logger = getLogger(__name__)


class HatchDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    mqtt_connection = None
    rest_devices: List[RestMini | RestPlus | RestIot | RestoreIot] = []
    expiration_time: float = None

    def __init__(
            self,
            hass: HomeAssistant,
            email: str,
            password: str,
    ) -> None:
        """Initialize the device."""
        self.email: str = email
        self.password: str = password

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{self.email}",
            always_update=False,
        )

    def _disconnect_mqtt(self) -> None:
        if self.mqtt_connection is not None:
            try:
                self.mqtt_connection.disconnect().result()
            except Exception as error:
                _LOGGER.error(f"mqtt_connection disconnect failed during reconnect", exc_info=error)

    def _rest_device_unsub(self) -> None:
        for rest_device in self.rest_devices:
            rest_device.remove_callback(self.async_update_listeners)

    async def _async_update_data(self) -> List[dict]:
        try:
            _LOGGER.debug(f"_async_update_data: {self.email}")
            self._disconnect_mqtt()
            self._rest_device_unsub()

            from hatch_rest_api import get_rest_devices

            def disconnect():
                _LOGGER.debug("disconnected")

            def resumed():
                _LOGGER.debug("resumed")

            client_session = async_get_clientsession(self.hass)
            _, self.mqtt_connection, self.rest_devices, self.expiration_time = await get_rest_devices(
                email=self.email,
                password=self.password,
                client_session=client_session,
                on_connection_interrupted=disconnect,
                on_connection_resumed=resumed,
            )
            _LOGGER.debug(
                f"credentials expire at: {datetime.fromtimestamp(self.expiration_time, UTC)}"
            )
            self.update_interval = datetime.fromtimestamp(self.expiration_time - 60, UTC) - datetime.now(UTC)
            for rest_device in self.rest_devices:
                rest_device.register_callback(self.async_update_listeners)
            return [rest_device.__repr__() for rest_device in self.rest_devices]
        except Exception as error:
            _LOGGER.exception(error)
            self.update_interval = timedelta(minutes=1)
            raise UpdateFailed(error) from error

    async def async_shutdown(self) -> None:
        """Cancel any scheduled call, and ignore new runs."""
        self._disconnect_mqtt()
        self._rest_device_unsub()
        await super().async_shutdown()

    def rest_device_by_thing_name(self, thing_name: str) -> None | RestMini | RestPlus | RestIot | RestoreIot:
        for rest_device in self.rest_devices:
            if rest_device.thing_name == thing_name:
                return rest_device
