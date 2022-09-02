import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_REST_DEVICES, DATA_MEDIA_PlAYERS
from .rest_mini_entity import RestMiniEntity
from hatch_rest_api import RestMini

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hass.data.setdefault(DOMAIN, {})

    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]

    rest_entities = []
    for rest_device in rest_devices:
        if isinstance(rest_device, RestMini):
            rest_entities.append(RestMiniEntity(rest_device))

    hass.data[DOMAIN][DATA_MEDIA_PlAYERS] = rest_entities
    async_add_entities(rest_entities)
