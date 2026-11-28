"""The Hatch config, options, reauth and reconfigure flows, driven through Home Assistant."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import AsyncMock, patch

from aiohttp import ClientError
from hatch_rest_api.errors import AuthError, RateError
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant.common import MockConfigEntry

import custom_components
import custom_components.ha_hatch as integration
from custom_components.ha_hatch import (
    config_flow,
    hatch_data_update_coordinator as coordinator_module,
)
from custom_components.ha_hatch.const import (
    CONFIG_FLOW_VERSION,
    CONFIG_NUMBERED_PRESET_SCENES,
    CONFIG_TURN_ON_LIGHT,
    CONFIG_TURN_ON_MEDIA,
    DOMAIN,
)

EMAIL = "parent@example.invalid"
PASSWORD = "correct horse"
OLD_PASSWORD = "old password"


@pytest.fixture(autouse=True, scope="module")
def restrict_custom_components_path() -> Iterator[None]:
    """Limit ``custom_components`` to this repository's real directory.

    An editable install adds a setuptools path-hook placeholder to the
    ``custom_components`` namespace path, which Home Assistant iterates while
    creating the ``hass`` fixture.

    Yields:
        None, while the restricted path is active.
    """
    components_path = str(Path(__file__).parents[1] / "custom_components")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(custom_components, "__path__", [components_path])
        yield


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load this custom integration."""


class FakeHatch:
    """Stands in for ``hatch_rest_api.Hatch`` in the config flow."""

    error: Exception | None = None
    logins: ClassVar[list[tuple[str, str]]] = []
    cleaned_up = 0
    rate_limit_retries: ClassVar[list[int]] = []

    def __init__(self, rate_limit_retries: int = 3) -> None:
        """Record the retry setting the flow asked for."""
        FakeHatch.rate_limit_retries.append(rate_limit_retries)

    async def login(self, email: str, password: str) -> str:
        """Record the login, then fail if a test asked for it."""
        FakeHatch.logins.append((email, password))
        if FakeHatch.error is not None:
            raise FakeHatch.error
        return "token"

    async def cleanup_client_session(self) -> None:
        """Count closed sessions."""
        FakeHatch.cleaned_up += 1


@pytest.fixture
def hatch() -> Iterator[type[FakeHatch]]:
    """Patch the config flow's Hatch client."""
    FakeHatch.error = None
    FakeHatch.logins = []
    FakeHatch.cleaned_up = 0
    FakeHatch.rate_limit_retries = []
    with patch.object(config_flow, "Hatch", FakeHatch):
        yield FakeHatch


@pytest.fixture
def setup_entry() -> Iterator[AsyncMock]:
    """Stub entry setup, so a reload after reauth or reconfigure doesn't log in."""
    with (
        patch.object(integration, "async_setup_entry", AsyncMock(return_value=True)) as setup,
        patch.object(integration, "async_unload_entry", AsyncMock(return_value=True)),
    ):
        yield setup


def _defaults(form: Any) -> dict[str, Any]:
    """The form fields that have a default, with that default."""
    return {
        str(key): key.default()
        for key in form["data_schema"].schema
        if callable(getattr(key, "default", None))
    }


def _entry(hass: HomeAssistant, password: str = OLD_PASSWORD) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=EMAIL,
        unique_id=EMAIL,
        version=CONFIG_FLOW_VERSION,
        data={CONF_EMAIL: EMAIL, CONF_PASSWORD: password},
    )
    entry.add_to_hass(hass)
    return entry


# ---- user step -------------------------------------------------------------------


async def test_user_flow_creates_an_entry(
    hass: HomeAssistant, hatch: type[FakeHatch], setup_entry: AsyncMock
) -> None:
    """Working credentials create an entry named and identified by the email."""
    form = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == EMAIL
    assert result["data"] == {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    assert result["result"].unique_id == EMAIL
    assert hatch.logins == [(EMAIL, PASSWORD)]
    # One login, no retries while the user waits, and the session closed.
    assert hatch.rate_limit_retries == [0]
    assert hatch.cleaned_up == 1


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (AuthError(), "auth"),
        (RateError("API rate limit exceeded."), "rate_limited"),
        (ClientError("network down"), "cannot_connect"),
    ],
)
async def test_user_flow_shows_login_errors(
    hass: HomeAssistant, hatch: type[FakeHatch], error: Exception, expected: str
) -> None:
    """A failed login shows the matching error, and the session is still closed."""
    hatch.error = error
    form = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}
    assert hatch.cleaned_up == 1


async def test_user_flow_aborts_for_an_account_already_set_up(
    hass: HomeAssistant, hatch: type[FakeHatch], setup_entry: AsyncMock
) -> None:
    """The same email can't be added twice."""
    _entry(hass)
    form = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---- reauth ----------------------------------------------------------------------


async def test_reauth_updates_the_password_and_reloads(
    hass: HomeAssistant, hatch: type[FakeHatch], setup_entry: AsyncMock
) -> None:
    """Reauth asks for the password, checks it, saves it and reloads the entry."""
    entry = _entry(hass)

    form = await entry.start_reauth_flow(hass)
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "reauth_confirm"
    assert form["description_placeholders"]["email"] == EMAIL

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_PASSWORD: PASSWORD}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data == {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    assert hatch.logins == [(EMAIL, PASSWORD)]
    setup_entry.assert_awaited()


async def test_reauth_with_a_wrong_password_shows_the_error(
    hass: HomeAssistant, hatch: type[FakeHatch], setup_entry: AsyncMock
) -> None:
    """A rejected password keeps the form open and leaves the entry unchanged."""
    entry = _entry(hass)
    hatch.error = AuthError()

    form = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_PASSWORD: "still wrong"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}
    assert entry.data[CONF_PASSWORD] == OLD_PASSWORD


async def test_rejected_credentials_during_setup_start_reauth(
    hass: HomeAssistant, hatch: type[FakeHatch]
) -> None:
    """The bug this fixes: AuthError at setup now starts a reauth flow that can finish.

    The coordinator raises ConfigEntryAuthFailed, which makes Home Assistant
    start a reauth flow; before this change the integration had no reauth step.
    """
    entry = _entry(hass)
    with (
        patch.object(coordinator_module, "get_rest_devices", AsyncMock(side_effect=AuthError())),
        patch.object(coordinator_module, "async_get_clientsession"),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = [
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["context"]["source"] == config_entries.SOURCE_REAUTH
    ]
    assert len(flows) == 1
    assert flows[0]["step_id"] == "reauth_confirm"

    with (
        patch.object(integration, "async_setup_entry", AsyncMock(return_value=True)),
        patch.object(integration, "async_unload_entry", AsyncMock(return_value=True)),
    ):
        result = await hass.config_entries.flow.async_configure(
            flows[0]["flow_id"], {CONF_PASSWORD: PASSWORD}
        )
        await hass.async_block_till_done()

    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == PASSWORD


# ---- reconfigure -----------------------------------------------------------------


async def test_reconfigure_updates_the_password(
    hass: HomeAssistant, hatch: type[FakeHatch], setup_entry: AsyncMock
) -> None:
    """Reconfigure shows the saved email and saves new credentials for the same account."""
    entry = _entry(hass)

    form = await entry.start_reconfigure_flow(hass)
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "reconfigure"
    assert _defaults(form)[CONF_EMAIL] == EMAIL

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}


async def test_reconfigure_to_another_account_aborts(
    hass: HomeAssistant, hatch: type[FakeHatch], setup_entry: AsyncMock
) -> None:
    """A different email is a different account, so the entry is left alone."""
    entry = _entry(hass)

    form = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_EMAIL: "someone.else@example.invalid", CONF_PASSWORD: PASSWORD}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
    assert entry.data[CONF_EMAIL] == EMAIL
    assert entry.data[CONF_PASSWORD] == OLD_PASSWORD


async def test_reconfigure_with_a_login_error_shows_it(
    hass: HomeAssistant, hatch: type[FakeHatch], setup_entry: AsyncMock
) -> None:
    """A failed login keeps the reconfigure form open."""
    entry = _entry(hass)
    hatch.error = RateError("API rate limit exceeded.")

    form = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "rate_limited"}


# ---- options -------------------------------------------------------------------


async def test_options_flow_saves_the_choices(hass: HomeAssistant, setup_entry: AsyncMock) -> None:
    """The options form starts from the defaults and saves what is chosen."""
    entry = _entry(hass)

    form = await hass.config_entries.options.async_init(entry.entry_id)
    assert form["type"] is FlowResultType.FORM
    assert _defaults(form) == {
        CONFIG_TURN_ON_LIGHT: True,
        CONFIG_TURN_ON_MEDIA: True,
        CONFIG_NUMBERED_PRESET_SCENES: False,
    }

    choices: dict[str, Any] = {
        CONFIG_TURN_ON_LIGHT: False,
        CONFIG_TURN_ON_MEDIA: True,
        CONFIG_NUMBERED_PRESET_SCENES: True,
    }
    result = await hass.config_entries.options.async_configure(form["flow_id"], choices)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == choices
