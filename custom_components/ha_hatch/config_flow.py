"""Config flow for the Hatch integration."""

from collections.abc import Mapping
import logging
from typing import Any

from aiohttp import ClientError
from hatch_rest_api import Hatch
from hatch_rest_api.errors import AuthError, RateError
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
import probatio

from .const import (
    CONFIG_FLOW_VERSION,
    CONFIG_NUMBERED_PRESET_SCENES,
    CONFIG_NUMBERED_PRESET_SCENES_DEFAULT,
    CONFIG_TURN_ON_DEFAULT,
    CONFIG_TURN_ON_LIGHT,
    CONFIG_TURN_ON_MEDIA,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

ERROR_AUTH = "auth"
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_RATE_LIMITED = "rate_limited"


async def _async_validate_credentials(email: str, password: str) -> dict[str, str]:
    """Log in to Hatch once to check the credentials.

    Args:
        email: Hatch account email.
        password: Hatch account password.

    Returns:
        Form errors; empty when the credentials work.
    """
    api_cloud = Hatch(rate_limit_retries=0)
    try:
        await api_cloud.login(email=email, password=password)
    except AuthError:
        return {"base": ERROR_AUTH}
    except RateError:
        return {"base": ERROR_RATE_LIMITED}
    except ClientError:
        _LOGGER.debug("Hatch login failed", exc_info=True)
        return {"base": ERROR_CANNOT_CONNECT}
    finally:
        await api_cloud.cleanup_client_session()
    return {}


class HatchOptionFlowHandler(config_entries.OptionsFlow):
    """Handle Hatch options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the hatch option flow handler."""
        self.schema = probatio.Schema(
            {
                probatio.Required(
                    CONFIG_TURN_ON_LIGHT,
                    default=config_entry.options.get(CONFIG_TURN_ON_LIGHT, CONFIG_TURN_ON_DEFAULT),
                ): bool,
                probatio.Required(
                    CONFIG_TURN_ON_MEDIA,
                    default=config_entry.options.get(CONFIG_TURN_ON_MEDIA, CONFIG_TURN_ON_DEFAULT),
                ): bool,
                probatio.Required(
                    CONFIG_NUMBERED_PRESET_SCENES,
                    default=config_entry.options.get(
                        CONFIG_NUMBERED_PRESET_SCENES,
                        CONFIG_NUMBERED_PRESET_SCENES_DEFAULT,
                    ),
                ): bool,
            }
        )

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            _LOGGER.debug("user input in option flow : %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=self.schema)


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlowHandler(config_entries.ConfigFlow):
    """Handle a Hatch config flow."""

    VERSION = CONFIG_FLOW_VERSION

    def __init__(self) -> None:
        """Initialize the config flow handler."""
        self.data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HatchOptionFlowHandler:
        """Return the options flow handler."""
        return HatchOptionFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the user step of the config flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            errors = await _async_validate_credentials(email, user_input[CONF_PASSWORD])
            if not errors:
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()
                self.data.update(user_input)
                return self.async_create_entry(title=email, data=self.data)

        return self.async_show_form(
            step_id="user",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_EMAIL): cv.string,
                    probatio.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start re-authentication after Hatch rejected the saved credentials.

        Args:
            entry_data: The config entry's data.

        Returns:
            The password form.
        """
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the account's new password, then update and reload the entry.

        Args:
            user_input: The submitted password, or None to show the form.

        Returns:
            The form, with any error, or an abort once the entry is updated.
        """
        reauth_entry = self._get_reauth_entry()
        email = reauth_entry.data[CONF_EMAIL]
        errors: dict[str, str] = {}

        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            errors = await _async_validate_credentials(email, password)
            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry, data_updates={CONF_PASSWORD: password}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=probatio.Schema({probatio.Required(CONF_PASSWORD): cv.string}),
            description_placeholders={"email": email},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the saved email or password of the same Hatch account.

        Args:
            user_input: The submitted credentials, or None to show the form.

        Returns:
            The form, with any error, or an abort once the entry is updated.
        """
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            errors = await _async_validate_credentials(email, password)
            if not errors:
                # The entry is identified by its email: a different email is a
                # different account, which needs its own entry.
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates={CONF_EMAIL: email, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_EMAIL, default=reconfigure_entry.data.get(CONF_EMAIL, "")
                    ): cv.string,
                    probatio.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )
