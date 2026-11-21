"""Config flow for the Hatch integration."""

import logging
from typing import Any

from hatch_rest_api import Hatch
from hatch_rest_api.errors import AuthError, RateError
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

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


class HatchOptionFlowHandler(config_entries.OptionsFlow):
    """Handle Hatch options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the hatch option flow handler."""
        self.schema = vol.Schema(
            {
                vol.Required(
                    CONFIG_TURN_ON_LIGHT,
                    default=config_entry.options.get(CONFIG_TURN_ON_LIGHT, CONFIG_TURN_ON_DEFAULT),
                ): bool,
                vol.Required(
                    CONFIG_TURN_ON_MEDIA,
                    default=config_entry.options.get(CONFIG_TURN_ON_MEDIA, CONFIG_TURN_ON_DEFAULT),
                ): bool,
                vol.Required(
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
        data_schema = {
            vol.Required(CONF_EMAIL): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
        }
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            api_cloud = None
            try:
                api_cloud = Hatch()
                await api_cloud.login(email=email, password=password)
                await self.async_set_unique_id(unique_id="hatch")
                self.data.update(user_input)
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=email,
                    data=self.data,
                )
            except AuthError:
                errors["base"] = "auth"
            except RateError:
                errors["base"] = "rate_limited"
            finally:
                if api_cloud is not None:
                    await api_cloud.cleanup_client_session()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )
