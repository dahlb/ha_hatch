import logging
from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_EMAIL,
)

from .const import (
    DOMAIN,
    CONFIG_FLOW_VERSION,
    CONFIG_TURN_ON_MEDIA,
    CONFIG_TURN_ON_LIGHT,
    CONFIG_TURN_ON_DEFAULT,
)

_LOGGER = logging.getLogger(__name__)


class HatchOptionFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self.schema = vol.Schema(
            {
                vol.Required(
                    CONFIG_TURN_ON_LIGHT,
                    default=self.config_entry.options.get(
                        CONFIG_TURN_ON_LIGHT, CONFIG_TURN_ON_DEFAULT
                    ),
                ): bool,
                vol.Required(
                    CONFIG_TURN_ON_MEDIA,
                    default=self.config_entry.options.get(
                        CONFIG_TURN_ON_MEDIA, CONFIG_TURN_ON_DEFAULT
                    ),
                ): bool,
            }
        )

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            _LOGGER.debug("user input in option flow : %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=self.schema)


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlowHandler(config_entries.ConfigFlow):

    VERSION = CONFIG_FLOW_VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    data: dict[str, Any] | None = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HatchOptionFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
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
                from hatch_rest_api import Hatch

                api_cloud = Hatch()
                await api_cloud.login(email=email, password=password)
                self.data.update(user_input)
                return self.async_create_entry(
                    title=email,
                    data=self.data,
                )
            except ConfigEntryAuthFailed:
                errors["base"] = "auth"
            finally:
                if api_cloud is not None:
                    await api_cloud.cleanup_client_session()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )
