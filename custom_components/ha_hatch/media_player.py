import logging

from .const import DOMAIN, DATA_REST_MINIS
from .rest_mini_entity import RestMiniEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DOMAIN, [])

    rest_minis = hass.data[DOMAIN][DATA_REST_MINIS]

    rest_entities = map(lambda rest_mini : RestMiniEntity(rest_mini), rest_minis)
    async_add_entities(rest_entities)
