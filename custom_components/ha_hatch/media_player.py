import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_REST_MINIS, DATA_MEDIA_PlAYERS
from .rest_mini_entity import RestMiniEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hass.data.setdefault(DOMAIN, {})

    rest_minis = hass.data[DOMAIN][DATA_REST_MINIS]

    rest_entities = map(lambda rest_mini: RestMiniEntity(rest_mini), rest_minis)
    hass.data[DOMAIN][DATA_MEDIA_PlAYERS] = rest_entities
    async_add_entities(rest_entities)
