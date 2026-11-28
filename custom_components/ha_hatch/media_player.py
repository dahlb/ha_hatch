"""Media player platform for Hatch devices."""

from collections.abc import Mapping
import functools
import logging

from hatch_rest_api import RestBaby, RestDevice, RestIot, Restore, RestoreIot, RestoreV5
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONFIG_TURN_ON_DEFAULT, CONFIG_TURN_ON_MEDIA
from .custom_sounds import CustomSound, async_load_custom_sounds
from .hatch_data_update_coordinator import HatchConfigEntry, HatchDataUpdateCoordinator
from .media_rest_entity import MediaRestEntity
from .media_riot_entity import MediaRiotEntity
from .restore_entities import RestoreSound

_LOGGER = logging.getLogger(__name__)


def choose_media_entity(
    rest_device: RestDevice,
    config_turn_on_media: bool,
    coordinator: HatchDataUpdateCoordinator,
    custom_sounds: Mapping[str, CustomSound] | None = None,
) -> MediaRiotEntity | MediaRestEntity | RestoreSound:
    """Return the media entity for a device.

    Args:
        rest_device: Device to build the entity for.
        config_turn_on_media: Whether turning on the Rest Mini/Plus light also plays media.
        coordinator: Coordinator that owns the device.
        custom_sounds: User-defined sounds offered on riot media players.

    Returns:
        The media entity for the device.
    """
    if isinstance(rest_device, Restore):
        # Must stay before the fallback below, which builds a Rest Mini/Plus
        # player for anything not matched.
        return RestoreSound(coordinator=coordinator, thing_name=rest_device.thing_name)
    if isinstance(rest_device, RestIot | RestoreIot | RestoreV5 | RestBaby):
        return MediaRiotEntity(
            coordinator=coordinator,
            thing_name=rest_device.thing_name,
            custom_sounds=custom_sounds,
        )
    return MediaRestEntity(
        coordinator=coordinator,
        thing_name=rest_device.thing_name,
        config_turn_on_media=config_turn_on_media,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HatchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the platform from a config entry."""
    coordinator = config_entry.runtime_data
    config_turn_on_media = config_entry.options.get(CONFIG_TURN_ON_MEDIA, CONFIG_TURN_ON_DEFAULT)
    custom_sounds = await async_load_custom_sounds(hass)
    media_player_entities = list(
        filter(
            lambda media_entity: media_entity is not None,
            map(
                functools.partial(
                    choose_media_entity,
                    config_turn_on_media=config_turn_on_media,
                    coordinator=coordinator,
                    custom_sounds=custom_sounds,
                ),
                coordinator.rest_devices,
            ),
        )
    )
    async_add_entities(media_player_entities)
