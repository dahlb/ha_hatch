from datetime import timedelta, UTC, datetime
from logging import getLogger, Logger
import traceback
from typing import Final

from hatch_rest_api import RestDevice
from hatch_rest_api.errors import AuthError, RateError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.ha_hatch import DOMAIN

_LOGGER: Logger = getLogger(__name__)

DEFAULT_RETRY_INTERVAL: Final = timedelta(minutes=1)
RATE_LIMIT_RETRY_INTERVAL: Final = timedelta(minutes=15)
MAX_RATE_LIMIT_RETRY_INTERVAL: Final = timedelta(hours=6)
AWSCRT_MISMATCH_RETRY_INTERVAL: Final = timedelta(hours=1)
MAX_AWSCRT_MISMATCH_RETRY_INTERVAL: Final = timedelta(hours=12)
AWSCRT_MISMATCH_TRACE_FILE: Final = "awscrt/mqtt.py"
AWSCRT_MISMATCH_TRACE_NAME: Final = "connect"


class HatchDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    mqtt_connection = None
    rest_devices: list[RestDevice] = []
    expiration_time: float = None
    _retry_backoff_until: dict[str, datetime] = {}
    _retry_backoff_attempts: dict[str, int] = {}
    _retry_backoff_reasons: dict[str, str] = {}

    def __init__(
            self,
            hass: HomeAssistant,
            email: str,
            password: str,
            config_entry: ConfigEntry,
    ) -> None:
        """Initialize the device."""
        self.email: str = email
        self.password: str = password

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}-{self.email}",
            always_update=False,
        )

    def _disconnect_mqtt(self) -> None:
        if self.mqtt_connection is not None:
            try:
                self.mqtt_connection.disconnect().result()
            except Exception as error:
                _LOGGER.error("mqtt_connection disconnect failed during reconnect", exc_info=error)

    def _rest_device_unsub(self) -> None:
        for rest_device in self.rest_devices:
            rest_device.remove_callback(self.async_update_listeners)

    def _clear_retry_backoff(self) -> None:
        self._retry_backoff_until.pop(self.email, None)
        self._retry_backoff_attempts.pop(self.email, None)
        self._retry_backoff_reasons.pop(self.email, None)

    def _apply_retry_backoff(
            self,
            *,
            reason: str,
            error: Exception,
            base_delay: timedelta,
            maximum_delay: timedelta,
            log_message: str,
    ) -> None:
        if self._retry_backoff_reasons.get(self.email) == reason:
            attempts = self._retry_backoff_attempts.get(self.email, 0) + 1
        else:
            attempts = 1

        delay_seconds = min(
            base_delay.total_seconds() * (2 ** (attempts - 1)),
            maximum_delay.total_seconds(),
        )
        delay = timedelta(seconds=delay_seconds)
        retry_at = datetime.now(UTC) + delay

        self._retry_backoff_reasons[self.email] = reason
        self._retry_backoff_attempts[self.email] = attempts
        self._retry_backoff_until[self.email] = retry_at
        self.update_interval = delay

        _LOGGER.warning(
            "%s Retrying for %s at %s after %s consecutive %s failure(s).",
            log_message,
            self.email,
            retry_at.isoformat(),
            attempts,
            reason,
            exc_info=error,
        )

    def _raise_if_retry_backoff_active(self) -> None:
        retry_at = self._retry_backoff_until.get(self.email)
        if retry_at is None:
            return

        remaining = retry_at - datetime.now(UTC)
        if remaining <= timedelta(0):
            return

        self.update_interval = remaining
        raise UpdateFailed(
            f"Retry backoff active until {retry_at.isoformat()} for {self.email}"
        )

    def _is_awscrt_connect_signature_mismatch(self, error: Exception) -> bool:
        if not isinstance(error, TypeError) or "argument" not in str(error):
            return False

        return any(
            frame.filename.endswith(AWSCRT_MISMATCH_TRACE_FILE)
            and frame.name == AWSCRT_MISMATCH_TRACE_NAME
            for frame in traceback.extract_tb(error.__traceback__)
        )

    async def _async_update_data(self) -> list[dict]:
        self._raise_if_retry_backoff_active()
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
            self._clear_retry_backoff()
            for rest_device in self.rest_devices:
                rest_device.register_callback(self.async_update_listeners)
            return [rest_device.__repr__() for rest_device in self.rest_devices]
        except AuthError as error:
            self._clear_retry_backoff()
            raise ConfigEntryAuthFailed(
                "Hatch credentials rejected during setup"
            ) from error
        except RateError as error:
            self._apply_retry_backoff(
                reason="rate_limit",
                error=error,
                base_delay=RATE_LIMIT_RETRY_INTERVAL,
                maximum_delay=MAX_RATE_LIMIT_RETRY_INTERVAL,
                log_message=(
                    "Hatch API rate limit exceeded. Delaying future login attempts to "
                    "avoid burning additional requests."
                ),
            )
            raise UpdateFailed(error) from error
        except Exception as error:
            if self._is_awscrt_connect_signature_mismatch(error):
                self._apply_retry_backoff(
                    reason="awscrt_signature_mismatch",
                    error=error,
                    base_delay=AWSCRT_MISMATCH_RETRY_INTERVAL,
                    maximum_delay=MAX_AWSCRT_MISMATCH_RETRY_INTERVAL,
                    log_message=(
                        "Detected an awscrt Python/native MQTT signature mismatch. "
                        "Delaying retries because repeated setup attempts will keep "
                        "hitting Hatch login while this environment is broken."
                    ),
                )
                raise UpdateFailed(error) from error
            _LOGGER.exception(error)
            self.update_interval = DEFAULT_RETRY_INTERVAL
            raise UpdateFailed(error) from error

    async def async_shutdown(self) -> None:
        """Cancel any scheduled call, and ignore new runs."""
        self._disconnect_mqtt()
        self._rest_device_unsub()
        await super().async_shutdown()

    def rest_device_by_thing_name(self, thing_name: str) -> RestDevice | None:
        return next(
            (rest_device for rest_device in self.rest_devices if rest_device.thing_name == thing_name),
            None
        )
