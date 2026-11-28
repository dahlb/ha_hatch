"""The coordinator's alarm refresh and its handling of failed logins."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from hatch_rest_api.errors import AuthError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from custom_components.ha_hatch import hatch_data_update_coordinator as coordinator_module
from custom_components.ha_hatch.hatch_data_update_coordinator import (
    AWSCRT_MISMATCH_RETRY_INTERVAL,
    DEFAULT_RETRY_INTERVAL,
    HatchDataUpdateCoordinator,
)


def _coordinator(email: str, rest_devices: list[Any] | None = None) -> HatchDataUpdateCoordinator:
    coordinator = HatchDataUpdateCoordinator.__new__(HatchDataUpdateCoordinator)
    coordinator.email = email
    coordinator.password = "hunter2"
    coordinator.hass = MagicMock()
    coordinator.rest_devices = rest_devices or []
    coordinator.mqtt_connection = None
    coordinator.expiration_time = None
    coordinator._alarm_refresh_callbacks = set()
    coordinator._alarm_refresh_lock = asyncio.Lock()
    coordinator.update_interval = None
    return coordinator


def _forget_backoff(email: str) -> None:
    for state in (
        HatchDataUpdateCoordinator._retry_backoff_until,
        HatchDataUpdateCoordinator._retry_backoff_attempts,
        HatchDataUpdateCoordinator._retry_backoff_reasons,
    ):
        state.pop(email, None)


def _alarm_device(name: str, refresh: AsyncMock | None, capable: bool = True) -> Any:
    device = MagicMock(spec=["device_name", "alarm_capable", "alarms_loaded", "refresh_alarms"])
    device.device_name = name
    device.alarm_capable = capable
    device.alarms_loaded = False
    device.refresh_alarms = refresh
    return device


# ---- alarm refresh ---------------------------------------------------------------


async def test_alarm_refresh_skips_devices_without_alarms_and_survives_failures(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Each alarm device refreshes; one failing doesn't stop the others or the callbacks."""
    ok = AsyncMock(return_value=[])
    failing = AsyncMock(side_effect=RuntimeError("Hatch is down"))
    no_alarms = AsyncMock()
    coordinator = _coordinator(
        "alarms@example.invalid",
        [
            _alarm_device("Ok", ok),
            _alarm_device("Failing", failing),
            _alarm_device("No alarms", no_alarms, capable=False),
        ],
    )
    sync_callback = MagicMock()
    async_callback = AsyncMock()
    coordinator.async_add_alarm_refresh_callback(sync_callback)
    coordinator.async_add_alarm_refresh_callback(async_callback)

    await coordinator.async_refresh_alarms()

    ok.assert_awaited_once()
    failing.assert_awaited_once()
    no_alarms.assert_not_awaited()
    sync_callback.assert_called_once_with()
    async_callback.assert_awaited_once_with()
    assert "Failed to refresh Hatch alarms for Failing" in caplog.text


async def test_alarm_refresh_without_any_success_notifies_no_one() -> None:
    """If every refresh fails, the callbacks aren't run on stale data."""
    coordinator = _coordinator(
        "alarms-fail@example.invalid",
        [_alarm_device("Failing", AsyncMock(side_effect=RuntimeError("down")))],
    )
    callback = MagicMock()
    coordinator.async_add_alarm_refresh_callback(callback)

    await coordinator.async_refresh_alarms()

    callback.assert_not_called()


async def test_a_failing_callback_does_not_stop_the_others(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A callback that raises is logged, and the rest still run."""
    coordinator = _coordinator(
        "callbacks@example.invalid", [_alarm_device("Ok", AsyncMock(return_value=[]))]
    )
    after = MagicMock()
    coordinator.async_add_alarm_refresh_callback(MagicMock(side_effect=RuntimeError("bug")))
    coordinator.async_add_alarm_refresh_callback(after)

    await coordinator.async_refresh_alarms()

    after.assert_called_once_with()
    assert "Hatch alarm refresh callback failed" in caplog.text


async def test_removed_callback_is_not_run() -> None:
    """Removing a callback stops it being notified."""
    coordinator = _coordinator(
        "remove-callback@example.invalid", [_alarm_device("Ok", AsyncMock(return_value=[]))]
    )
    callback = MagicMock()
    remove = coordinator.async_add_alarm_refresh_callback(callback)
    remove()

    await coordinator.async_refresh_alarms()

    callback.assert_not_called()


async def test_scheduled_alarm_refresh_never_raises(caplog: pytest.LogCaptureFixture) -> None:
    """The interval handler logs an unexpected error instead of raising it."""
    coordinator = _coordinator("interval@example.invalid")
    with patch.object(
        HatchDataUpdateCoordinator, "async_refresh_alarms", AsyncMock(side_effect=RuntimeError("x"))
    ):
        await coordinator._async_handle_alarm_refresh_interval(datetime.now(UTC))
    assert "Unhandled error during scheduled Hatch alarm refresh" in caplog.text


# ---- failed logins -------------------------------------------------------------


async def _update(coordinator: HatchDataUpdateCoordinator, get_rest_devices: AsyncMock) -> None:
    with (
        patch.object(coordinator_module, "get_rest_devices", get_rest_devices),
        patch.object(coordinator_module, "async_get_clientsession", MagicMock()),
    ):
        await coordinator._async_update_data()


async def test_rejected_credentials_start_reauth_and_clear_the_backoff() -> None:
    """AuthError raises ConfigEntryAuthFailed, which makes Home Assistant start reauth."""
    email = "rejected@example.invalid"
    coordinator = _coordinator(email)
    HatchDataUpdateCoordinator._retry_backoff_attempts[email] = 2
    try:
        with pytest.raises(ConfigEntryAuthFailed):
            await _update(coordinator, AsyncMock(side_effect=AuthError()))
        assert email not in HatchDataUpdateCoordinator._retry_backoff_attempts
    finally:
        _forget_backoff(email)


async def test_an_unexpected_failure_retries_in_a_minute() -> None:
    """Any other failure is retried after DEFAULT_RETRY_INTERVAL."""
    email = "unexpected@example.invalid"
    coordinator = _coordinator(email)
    try:
        with pytest.raises(UpdateFailed):
            await _update(coordinator, AsyncMock(side_effect=RuntimeError("boom")))
        assert coordinator.update_interval == DEFAULT_RETRY_INTERVAL
    finally:
        _forget_backoff(email)


def _awscrt_connect_type_error() -> TypeError:
    """A TypeError raised from a frame that looks like awscrt/mqtt.py's connect()."""
    namespace: dict[str, Any] = {}
    exec(  # noqa: S102 - builds a frame with awscrt's file name
        compile(
            "def connect():\n    raise TypeError('connect() takes 13 positional arguments but 14 were given')\n",
            "/site-packages/awscrt/mqtt.py",
            "exec",
        ),
        namespace,
    )
    try:
        namespace["connect"]()
    except TypeError as error:
        return error
    raise AssertionError("expected a TypeError")


async def test_awscrt_version_mismatch_backs_off_for_an_hour() -> None:
    """The awscrt Python/native mismatch backs off for an hour instead of retrying each minute."""
    email = "awscrt@example.invalid"
    coordinator = _coordinator(email)
    try:
        with pytest.raises(UpdateFailed):
            await _update(coordinator, AsyncMock(side_effect=_awscrt_connect_type_error()))
        assert coordinator.update_interval == AWSCRT_MISMATCH_RETRY_INTERVAL
    finally:
        _forget_backoff(email)


async def test_other_type_errors_are_not_mistaken_for_the_awscrt_mismatch() -> None:
    """A TypeError from elsewhere is an ordinary failure."""
    email = "plain-type-error@example.invalid"
    coordinator = _coordinator(email)
    try:
        with pytest.raises(UpdateFailed):
            await _update(coordinator, AsyncMock(side_effect=TypeError("missing 1 argument")))
        assert coordinator.update_interval == DEFAULT_RETRY_INTERVAL
    finally:
        _forget_backoff(email)


async def test_a_successful_login_schedules_the_next_one_before_expiry() -> None:
    """After logging in, the next refresh is a minute before the AWS credentials expire."""
    email = "success@example.invalid"
    coordinator = _coordinator(email)
    expires = datetime.now(UTC) + timedelta(hours=1)
    try:
        await _update(
            coordinator, AsyncMock(return_value=(MagicMock(), MagicMock(), [], expires.timestamp()))
        )
        assert coordinator.update_interval is not None
        assert timedelta(minutes=58) < coordinator.update_interval <= timedelta(minutes=59)
    finally:
        _forget_backoff(email)
