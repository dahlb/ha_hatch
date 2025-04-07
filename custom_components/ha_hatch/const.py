# Configuration Constants
from homeassistant.const import Platform

DOMAIN: str = "ha_hatch"

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 2
CONFIG_TURN_ON_MEDIA: str = "turn_on_media"
CONFIG_TURN_ON_LIGHT: str = "turn_on_light"
CONFIG_TURN_ON_DEFAULT: bool = True

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
#    Platform.MEDIA_PLAYER,
#    Platform.SCENE,
#    Platform.SENSOR,
#    Platform.SWITCH,
]
