import logging
import functools

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
from hatch_rest_api import RestIot, RestoreIot
from .rest_media_entity import RestMediaEntity

_LOGGER = logging.getLogger(__name__)

def choose_media_entity(
        rest_device,
        config_entry,
        ):
    config_turn_on_media = config_entry.options.get(
        CONFIG_TURN_ON_MEDIA, CONFIG_TURN_ON_DEFAULT
    )

    return RestMediaEntity(rest_device, config_turn_on_media)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hass.data.setdefault(DOMAIN, {})

    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]
    media_player_entities = list(
        filter(
            lambda media_entity: media_entity is not None,
            map(
                functools.partial(choose_media_entity, config_entry=config_entry),
                rest_devices,
            )
        )
    )
    hass.data[DOMAIN][DATA_MEDIA_PlAYERS] = media_player_entities
    async_add_entities(media_player_entities)
