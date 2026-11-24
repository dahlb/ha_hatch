"""Data update coordinator for Hatch devices."""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, datetime, time, timedelta
from inspect import isawaitable
from logging import Logger, getLogger
import traceback
from typing import Any, ClassVar, Final

from hatch_rest_api import RestDevice, Restore, get_rest_devices
from hatch_rest_api.errors import AuthError, RateError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .restore_alarm_slots import RestoreAlarmSlots

_LOGGER: Logger = getLogger(__name__)

ALARM_REFRESH_INTERVAL: Final = timedelta(minutes=10)
MQTT_DISCONNECT_TIMEOUT: Final = 10
MQTT_UNSUBSCRIBE_TIMEOUT: Final = 10
DEFAULT_RETRY_INTERVAL: Final = timedelta(minutes=1)
RATE_LIMIT_RETRY_INTERVAL: Final = timedelta(minutes=15)
MAX_RATE_LIMIT_RETRY_INTERVAL: Final = timedelta(hours=6)
AWSCRT_MISMATCH_RETRY_INTERVAL: Final = timedelta(hours=1)
MAX_AWSCRT_MISMATCH_RETRY_INTERVAL: Final = timedelta(hours=12)
AWSCRT_MISMATCH_TRACE_FILE: Final = "awscrt/mqtt.py"
AWSCRT_MISMATCH_TRACE_NAME: Final = "connect"
AlarmRefreshCallback = Callable[[], Awaitable[None] | None]
RESTORE_ALARM_SLOTS_STORE_VERSION: Final = 1
RESTORE_ALARM_SLOTS_SAVE_DELAY: Final = 5


def restore_alarm_slots_store_key(entry_id: str) -> str:
    """Return the storage key of a config entry's original Restore alarm slots.

    Args:
        entry_id: The config entry's id.

    Returns:
        The key, under Home Assistant's ``.storage`` directory.
    """
    return f"{DOMAIN}.restore_alarm_slots.{entry_id}"


class HatchDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Coordinate Hatch device updates."""

    mqtt_connection = None
    expiration_time: float | None = None
    # Shared across coordinator instances (keyed by account email) so a retry
    # backoff survives the config entry being reloaded.
    _retry_backoff_until: ClassVar[dict[str, datetime]] = {}
    _retry_backoff_attempts: ClassVar[dict[str, int]] = {}
    _retry_backoff_reasons: ClassVar[dict[str, str]] = {}

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
        self.rest_devices: list[RestDevice] = []
        self._alarm_refresh_callbacks: set[AlarmRefreshCallback] = set()
        self._alarm_refresh_lock = asyncio.Lock()
        self._alarm_refresh_unsub: Callable[[], None] | None = None
        # The original Restore's alarms change id on every edit; slots keep
        # their entities stable. Persisted once async_load_restore_alarm_slots
        # has run.
        self.restore_alarm_slots = RestoreAlarmSlots()
        self._restore_alarm_slots_store: Store | None = None

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}-{self.email}",
            always_update=False,
        )

    async def _async_unsubscribe_shadows(self) -> None:
        # Every device holds two AWS IoT shadow subscriptions, and awscrt keeps
        # a native reference to each subscription callback. Those references are
        # invisible to Python's garbage collector, so dropping our own reference
        # to the device is not enough to reclaim it -- the device, its shadow
        # client and the TLS context underneath survive until the subscriptions
        # go away. Skipping this stranded one connection graph per reconnect,
        # which is hourly, for as long as the process ran.
        #
        # Has to happen before the disconnect below, while the connection can
        # still carry the UNSUBSCRIBE, and off the event loop because the
        # library call blocks waiting for each UNSUBACK.
        if not self.rest_devices:
            return

        rest_devices = self.rest_devices

        def _unsubscribe() -> None:
            for rest_device in rest_devices:
                rest_device.unsubscribe()

        try:
            await asyncio.wait_for(
                self.hass.async_add_executor_job(_unsubscribe),
                timeout=MQTT_UNSUBSCRIBE_TIMEOUT * 2,
            )
        except Exception as error:
            # Best effort: a failure here costs memory, not correctness, and the
            # reconnect matters more than the cleanup.
            _LOGGER.error("shadow unsubscribe failed during teardown", exc_info=error)

    async def _async_disconnect_mqtt(self) -> None:
        # disconnect() returns a future that never resolves if the connection
        # is already broken; waiting on it without a timeout on the event loop
        # freezes all of Home Assistant.
        if self.mqtt_connection is None:
            return
        mqtt_connection = self.mqtt_connection
        self.mqtt_connection = None

        def _disconnect() -> None:
            mqtt_connection.disconnect().result(timeout=MQTT_DISCONNECT_TIMEOUT)

        try:
            await asyncio.wait_for(
                self.hass.async_add_executor_job(_disconnect),
                timeout=MQTT_DISCONNECT_TIMEOUT * 2,
            )
        except Exception as error:
            _LOGGER.error("mqtt_connection disconnect failed during reconnect", exc_info=error)

    def _rest_device_unsub(self) -> None:
        for rest_device in self.rest_devices:
            rest_device.remove_callback(self.async_update_listeners)

    def async_start_alarm_refresh(self) -> None:
        """Start periodic alarm refreshes."""
        if self._alarm_refresh_unsub is not None:
            return

        self._alarm_refresh_unsub = async_track_time_interval(
            self.hass,
            self._async_handle_alarm_refresh_interval,
            ALARM_REFRESH_INTERVAL,
        )

    def async_add_alarm_refresh_callback(
        self,
        callback: AlarmRefreshCallback,
    ) -> Callable[[], None]:
        """Register a callback run after alarms are refreshed."""
        self._alarm_refresh_callbacks.add(callback)

        def remove_callback() -> None:
            self._alarm_refresh_callbacks.discard(callback)

        return remove_callback

    async def _async_handle_alarm_refresh_interval(self, now: datetime) -> None:
        try:
            await self.async_refresh_alarms()
        except Exception as error:
            _LOGGER.exception(
                "Unhandled error during scheduled Hatch alarm refresh",
                exc_info=error,
            )

    async def async_refresh_alarms(self) -> None:
        """Refresh alarms for all devices."""
        alarm_devices = [
            rest_device
            for rest_device in self.rest_devices
            if (
                getattr(rest_device, "alarm_capable", False)
                or getattr(rest_device, "alarms_loaded", False)
            )
            and callable(getattr(rest_device, "refresh_alarms", None))
        ]
        if not alarm_devices:
            return

        async with self._alarm_refresh_lock:
            refresh_results = await asyncio.gather(
                *(rest_device.refresh_alarms() for rest_device in alarm_devices),
                return_exceptions=True,
            )

        refreshed = False
        for rest_device, result in zip(alarm_devices, refresh_results, strict=True):
            if isinstance(result, Exception):
                _LOGGER.warning(
                    "Failed to refresh Hatch alarms for %s",
                    rest_device.device_name,
                    exc_info=result,
                )
                continue
            refreshed = True

        if refreshed:
            await self._async_notify_alarm_refresh_callbacks()

    async def _async_notify_alarm_refresh_callbacks(self) -> None:
        for callback in tuple(self._alarm_refresh_callbacks):
            try:
                result = callback()
                if isawaitable(result):
                    await result
            except Exception as error:
                _LOGGER.exception(
                    "Hatch alarm refresh callback failed",
                    exc_info=error,
                )

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
        raise UpdateFailed(f"Retry backoff active until {retry_at.isoformat()} for {self.email}")

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
            _LOGGER.debug("_async_update_data: %s", self.email)
            await self._async_unsubscribe_shadows()
            await self._async_disconnect_mqtt()
            self._rest_device_unsub()

            def disconnect() -> None:
                _LOGGER.debug("disconnected")

            def resumed() -> None:
                _LOGGER.debug("resumed")

            client_session = async_get_clientsession(self.hass)
            (
                _,
                self.mqtt_connection,
                self.rest_devices,
                self.expiration_time,
            ) = await get_rest_devices(
                email=self.email,
                password=self.password,
                client_session=client_session,
                on_connection_interrupted=disconnect,
                on_connection_resumed=resumed,
            )
            _LOGGER.debug(
                "credentials expire at: %s", datetime.fromtimestamp(self.expiration_time, UTC)
            )
            self.update_interval = datetime.fromtimestamp(
                self.expiration_time - 60, UTC
            ) - datetime.now(UTC)
            self._clear_retry_backoff()
            for rest_device in self.rest_devices:
                rest_device.register_callback(self.async_update_listeners)
            # Re-login replaces every RestDevice instance, so alarm-derived entities
            # must reconcile against the new objects to keep references current.
            await self._async_notify_alarm_refresh_callbacks()
            return [rest_device.__repr__() for rest_device in self.rest_devices]
        except AuthError as error:
            self._clear_retry_backoff()
            raise ConfigEntryAuthFailed("Hatch credentials rejected during setup") from error
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
            _LOGGER.exception("Failed to update Hatch devices")
            self.update_interval = DEFAULT_RETRY_INTERVAL
            raise UpdateFailed(error) from error

    async def async_shutdown(self) -> None:
        """Cancel any scheduled call, and ignore new runs."""
        if self._alarm_refresh_unsub is not None:
            self._alarm_refresh_unsub()
            self._alarm_refresh_unsub = None
        self._alarm_refresh_callbacks.clear()
        await self._async_unsubscribe_shadows()
        await self._async_disconnect_mqtt()
        self._rest_device_unsub()
        await super().async_shutdown()

    async def async_load_restore_alarm_slots(self) -> None:
        """Load the original Restore alarm slots saved for this config entry.

        Without a config entry the slots are kept in memory only.
        """
        if self.config_entry is None:
            return
        self._restore_alarm_slots_store = Store(
            self.hass,
            RESTORE_ALARM_SLOTS_STORE_VERSION,
            restore_alarm_slots_store_key(self.config_entry.entry_id),
        )
        self.restore_alarm_slots = RestoreAlarmSlots(
            await self._restore_alarm_slots_store.async_load()
        )

    def _save_restore_alarm_slots(self) -> None:
        """Queue a save of the alarm slots, once they have been loaded."""
        if self._restore_alarm_slots_store is not None:
            self._restore_alarm_slots_store.async_delay_save(
                self.restore_alarm_slots.as_dict, RESTORE_ALARM_SLOTS_SAVE_DELAY
            )

    def restore_alarms_by_slot(self, rest_device: Restore) -> dict[str, dict[str, Any]]:
        """Return an original Restore's alarms by slot key.

        Args:
            rest_device: The device.

        Returns:
            The alarms by slot key; empty until the device's alarms have loaded.
        """
        if not rest_device.restore_alarms_loaded:
            return {}
        alarms, changed = self.restore_alarm_slots.reconcile(
            rest_device.thing_name, rest_device.restore_alarms
        )
        if changed:
            self._save_restore_alarm_slots()
        return alarms

    def restore_alarm(self, rest_device: Restore | None, slot_key: str) -> dict[str, Any] | None:
        """Return the alarm in one of an original Restore's slots.

        Args:
            rest_device: The device, or None if it is gone.
            slot_key: The slot.

        Returns:
            The alarm, or None if the slot is empty.
        """
        if rest_device is None:
            return None
        return self.restore_alarms_by_slot(rest_device).get(slot_key)

    def _restore_alarm_id(self, rest_device: Restore, slot_key: str) -> int:
        """Return the id of the alarm in a slot.

        Args:
            rest_device: The device.
            slot_key: The slot.

        Returns:
            The alarm's current id.

        Raises:
            ValueError: The slot is empty.
        """
        alarm = self.restore_alarm(rest_device, slot_key)
        if alarm is None:
            raise ValueError(f"{rest_device.device_name} has no alarm in slot {slot_key}")
        return int(alarm["id"])

    async def async_set_restore_alarm_enabled(
        self, rest_device: Restore, slot_key: str, enabled: bool
    ) -> None:
        """Turn the alarm in a slot on or off.

        Args:
            rest_device: The device.
            slot_key: The slot.
            enabled: Whether the alarm goes off.
        """
        await rest_device.set_restore_alarm_enabled(
            self._restore_alarm_id(rest_device, slot_key), enabled
        )

    async def async_set_restore_alarm_schedule(
        self,
        rest_device: Restore,
        slot_key: str,
        wake_time: time | None = None,
        weekdays: Iterable[str] | None = None,
    ) -> None:
        """Change the time and/or days of the alarm in a slot.

        The edit gives the alarm a new id; the slot follows it.

        Args:
            rest_device: The device.
            slot_key: The slot.
            wake_time: The new time of day; None keeps the current one.
            weekdays: The new repeat days; None keeps the current ones.
        """
        old_alarm_id = self._restore_alarm_id(rest_device, slot_key)
        new_alarm_id = await rest_device.set_restore_alarm_schedule(
            old_alarm_id, wake_time=wake_time, weekdays=weekdays
        )
        if self.restore_alarm_slots.replace(rest_device.thing_name, old_alarm_id, new_alarm_id):
            self._save_restore_alarm_slots()

    def rest_device_by_thing_name(self, thing_name: str) -> RestDevice | None:
        """Return the Hatch device with the given thing name."""
        return next(
            (
                rest_device
                for rest_device in self.rest_devices
                if rest_device.thing_name == thing_name
            ),
            None,
        )
