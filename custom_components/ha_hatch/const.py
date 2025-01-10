from homeassistant.const import Platform

# Configuration Constants
DOMAIN: str = "ha_hatch"

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 2
CONFIG_TURN_ON_MEDIA: str = "turn_on_media"
CONFIG_TURN_ON_LIGHT: str = "turn_on_light"
CONFIG_TURN_ON_DEFAULT: bool = True
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.MEDIA_PLAYER,
    Platform.SCENE,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Home Assistant Data Storage Constants
DATA_MQTT_CONNECTION: str = "mqtt_connection"
DATA_REST_DEVICES: str = "rest_devices"
DATA_MEDIA_PlAYERS: str = "media_players"
DATA_LIGHTS: str = "lights"
DATA_BINARY_SENSORS: str = "binary_sensors"
DATA_SENSORS: str = "sensors"
DATA_SCENES: str = "scenes"
DATA_SWITCHES: str = "switches"
DATA_EXPIRATION_LISTENER: str = "expiration_listener"

DATA_ENTITIES_KEYS = [
    DATA_SWITCHES,
    DATA_SENSORS,
    DATA_SCENES,
    DATA_LIGHTS,
    DATA_BINARY_SENSORS,
    DATA_MEDIA_PlAYERS,
]
