import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    DATA_REST_DEVICES,
    DATA_MEDIA_PlAYERS,
    CONFIG_TURN_ON_MEDIA,
    CONFIG_TURN_ON_DEFAULT,
)
from .rest_media_entity import RestMediaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hass.data.setdefault(DOMAIN, {})
    config_turn_on_media = config_entry.options.get(
        CONFIG_TURN_ON_MEDIA, CONFIG_TURN_ON_DEFAULT
    )

    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]
    medie_player_entities = list(map(lambda rest_device: RestMediaEntity(rest_device, config_turn_on_media), rest_devices))
    hass.data[DOMAIN][DATA_MEDIA_PlAYERS] = medie_player_entities
    async_add_entities(medie_player_entities)
