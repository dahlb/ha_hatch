import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_REST_MINIS
from .rest_mini_entity import RestMiniEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DOMAIN, [])

    rest_minis = hass.data[DOMAIN][DATA_REST_MINIS]

    rest_entities = map(lambda rest_mini : RestMiniEntity(rest_mini), rest_minis)
    async_add_entities(rest_entities)
#    platform = entity_platform.async_get_current_platform()
#    platform.async_register_entity_service(
#        SERVICE_UPDATE_SETTING, UPDATE_SETTING_SCHEMA, "async_update_setting"
#    )
