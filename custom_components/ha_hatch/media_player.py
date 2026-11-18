"""Media player platform for Hatch devices."""

import functools
import logging

from hatch_rest_api import RestBaby, RestDevice, RestIot, RestoreIot, RestoreV5
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import CONFIG_TURN_ON_DEFAULT, CONFIG_TURN_ON_MEDIA, DOMAIN
from .media_rest_entity import MediaRestEntity
from .media_riot_entity import MediaRiotEntity

_LOGGER = logging.getLogger(__name__)


def choose_media_entity(
    rest_device: RestDevice,
    config_turn_on_media: bool,
    coordinator: HatchDataUpdateCoordinator,
) -> MediaRiotEntity | MediaRestEntity:
    """Return the media entity class for a device."""
    if isinstance(rest_device, RestIot | RestoreIot | RestoreV5 | RestBaby):
        return MediaRiotEntity(coordinator=coordinator, thing_name=rest_device.thing_name)
    return MediaRestEntity(
        coordinator=coordinator,
        thing_name=rest_device.thing_name,
        config_turn_on_media=config_turn_on_media,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the platform from a config entry."""
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    config_turn_on_media = config_entry.options.get(CONFIG_TURN_ON_MEDIA, CONFIG_TURN_ON_DEFAULT)
    media_player_entities = list(
        filter(
            lambda media_entity: media_entity is not None,
            map(
                functools.partial(
                    choose_media_entity,
                    config_turn_on_media=config_turn_on_media,
                    coordinator=coordinator,
                ),
                coordinator.rest_devices,
            ),
        )
    )
    async_add_entities(media_player_entities)
