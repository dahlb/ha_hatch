from enum import Enum
from datetime import timedelta
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_BATTERY_CHARGING,
    DEVICE_CLASS_PLUG,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_POWER,
)
from homeassistant.const import (
    PERCENTAGE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_TIMESTAMP,
    DEVICE_CLASS_TEMPERATURE,
    LENGTH_MILES,
    TIME_MINUTES,
    TEMP_FAHRENHEIT,
    DEVICE_CLASS_DATE,
)

# Configuration Constants
DOMAIN: str = "ha_hatch"
CONF_SCAN_INTERVAL: str = "scan_interval"
CONF_FORCE_SCAN_INTERVAL: str = "force_scan_interval"
CONF_NO_FORCE_SCAN_HOUR_START: str = "no_force_scan_hour_start"
CONF_NO_FORCE_SCAN_HOUR_FINISH: str = "no_force_scan_hour_finish"
CONF_VEHICLES: str = "vehicles"
CONF_VEHICLE_IDENTIFIER: str = "vehicle_identifier"
CONF_BRAND: str = "brand"
CONF_PIN: str = "pin"

# I have seen that many people can survive with receiving updates in every 30 minutes. Let's see how KIA will respond
DEFAULT_SCAN_INTERVAL: int = 30
# When vehicle is running/active, it will update its status regularly, so no need to force it. If it has not been running, we will force it every 240 minutes
DEFAULT_FORCE_SCAN_INTERVAL: int = 240
DEFAULT_NO_FORCE_SCAN_HOUR_START: int = 18
DEFAULT_NO_FORCE_SCAN_HOUR_FINISH: int = 6

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 2
PLATFORMS = ["media_player"]

# Home Assistant Data Storage Constants
DATA_MQTT_CONNECTION: str = "mqtt_connection"
DATA_REST_MINIS: str = "rest_minis"

# action status delay constants
INITIAL_STATUS_DELAY_AFTER_COMMAND: int = 15
RECHECK_STATUS_DELAY_AFTER_COMMAND: int = 10
ACTION_LOCK_TIMEOUT_IN_SECONDS: int = 5 * 604
REQUEST_TO_SYNC_COOLDOWN: timedelta = timedelta(minutes=15)

# Sensor Specific Constants
DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"

DYNAMIC_UNIT: str = "dynamic_unit"

CA_TEMP_RANGE = [x * 0.5 for x in range(32, 64)]
USA_TEMP_RANGE = range(62, 82)

REGION_CANADA = "Canada"
REGION_USA = "USA"
REGIONS = [REGION_USA, REGION_CANADA]

BRAND_KIA = "Kia"
BRAND_HYUNDAI = "Hyundai"
BRANDS = [BRAND_KIA, BRAND_HYUNDAI]


class VEHICLE_LOCK_ACTION(Enum):
    LOCK = "close"
    UNLOCK = "open"


BINARY_INSTRUMENTS = [
    (
        "Hood",
        "door_hood_open",
        "mdi:car",
        "mdi:car",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Trunk",
        "door_trunk_open",
        "mdi:car-back",
        "mdi:car-back",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Door - Front Left",
        "door_front_left_open",
        "mdi:car-door",
        "mdi:car-door",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Door - Front Right",
        "door_front_right_open",
        "mdi:car-door",
        "mdi:car-door",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Door - Rear Left",
        "door_back_left_open",
        "mdi:car-door",
        "mdi:car-door",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Door - Rear Right",
        "door_back_right_open",
        "mdi:car-door",
        "mdi:car-door",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Engine",
        "engine_on",
        "mdi:engine",
        "mdi:engine-off",
        DEVICE_CLASS_POWER,
    ),
    (
        "Tire Pressure - All",
        "tire_all_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "Tire Pressure - Front Left",
        "tire_front_left_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "Tire Pressure - Front Right",
        "tire_front_right_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "Tire Pressure - Rear Left",
        "tire_rear_left_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "Tire Pressure - Rear Right",
        "tire_rear_right_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "HVAC",
        "climate_hvac_on",
        "mdi:air-conditioner",
        "mdi:air-conditioner",
        DEVICE_CLASS_POWER,
    ),
    (
        "Defroster",
        "climate_defrost_on",
        "mdi:car-defrost-front",
        "mdi:car-defrost-front",
        DEVICE_CLASS_POWER,
    ),
    (
        "Rear Window Heater",
        "climate_heated_rear_window_on",
        "mdi:car-defrost-rear",
        "mdi:car-defrost-rear",
        DEVICE_CLASS_POWER,
    ),
    (
        "Side Mirror Heater",
        "climate_heated_side_mirror_on",
        "mdi:car-side",
        "mdi:car-side",
        DEVICE_CLASS_POWER,
    ),
    (
        "Steering Wheel Heater",
        "climate_heated_steering_wheel_on",
        "mdi:steering",
        "mdi:steering",
        DEVICE_CLASS_POWER,
    ),
    (
        "Seat Heater Front Right",
        "climate_heated_seat_front_right_on",
        "mdi:steering",
        "mdi:steering",
        DEVICE_CLASS_POWER,
    ),
    (
        "Seat Heater Front Left",
        "climate_heated_seat_front_left_on",
        "mdi:car-seat-heater",
        "mdi:car-seat-heater",
        DEVICE_CLASS_POWER,
    ),
    (
        "Seat Heater Rear Right",
        "climate_heated_seat_rear_right_on",
        "mdi:car-seat-heater",
        "mdi:car-seat-heater",
        DEVICE_CLASS_POWER,
    ),
    (
        "Seat Heater Rear Left",
        "climate_heated_seat_rear_left_on",
        "mdi:car-seat-heater",
        "mdi:car-seat-heater",
        DEVICE_CLASS_POWER,
    ),
    (
        "Low Fuel Light",
        "low_fuel_light_on",
        "mdi:gas-station-off",
        "mdi:gas-station",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "Charging",
        "ev_battery_charging",
        "mdi:battery-charging",
        "mdi:battery",
        DEVICE_CLASS_BATTERY_CHARGING,
    ),
    (
        "Plugged In",
        "ev_plugged_in",
        "mdi:power-plug",
        "mdi:power-plug-off",
        DEVICE_CLASS_PLUG,
    ),
]

INSTRUMENTS = [
    (
        "EV Battery",
        "ev_battery_level",
        PERCENTAGE,
        "mdi:car-electric",
        DEVICE_CLASS_BATTERY,
    ),
    (
        "Range by EV",
        "ev_remaining_range_value",
        DYNAMIC_UNIT,
        "mdi:road-variant",
        None,
    ),
    (
        "Range by Fuel",
        "fuel_range_value",
        DYNAMIC_UNIT,
        "mdi:road-variant",
        None,
    ),
    (
        "Range Total",
        "total_range_value",
        DYNAMIC_UNIT,
        "mdi:road-variant",
        None,
    ),
    (
        "Estimated Current Charge Duration",
        "ev_charge_current_remaining_duration",
        TIME_MINUTES,
        "mdi:ev-station",
        None,
    ),
    (
        "Estimated Fast Charge Duration",
        "ev_charge_fast_duration",
        TIME_MINUTES,
        "mdi:ev-station",
        None,
    ),
    (
        "Estimated Portable Charge Duration",
        "ev_charge_portable_duration",
        TIME_MINUTES,
        "mdi:ev-station",
        None,
    ),
    (
        "Estimated Station Charge Duration",
        "ev_charge_station_duration",
        TIME_MINUTES,
        "mdi:ev-station",
        None,
    ),
    (
        "Target Capacity of Charge AC",
        "ev_max_ac_charge_level",
        PERCENTAGE,
        "mdi:car-electric",
        None,
    ),
    (
        "Target Capacity of Charge DC",
        "ev_max_dc_charge_level",
        PERCENTAGE,
        "mdi:car-electric",
        None,
    ),
    (
        "Target Range of Charge AC",
        "ev_max_range_ac_charge_value",
        DYNAMIC_UNIT,
        "mdi:car-electric",
        None,
    ),
    (
        "Target Range of Charge DC",
        "ev_max_range_dc_charge_value",
        DYNAMIC_UNIT,
        "mdi:car-electric",
        None,
    ),
    (
        "Odometer",
        "odometer_value",
        DYNAMIC_UNIT,
        "mdi:speedometer",
        None,
    ),
    (
        "Car Battery",
        "battery_level",
        PERCENTAGE,
        "mdi:car-battery",
        DEVICE_CLASS_BATTERY,
    ),
    (
        "Set Temperature",
        "climate_temperature_value",
        DYNAMIC_UNIT,
        None,
        DEVICE_CLASS_TEMPERATURE,
    ),
    (
        "Last Synced To Cloud",
        "last_synced_to_cloud",
        None,
        "mdi:update",
        DEVICE_CLASS_TIMESTAMP,
    ),
    (
        "Sync Age",
        "sync_age",
        TIME_MINUTES,
        "mdi:update",
        DEVICE_CLASS_DATE,
    ),
    (
        "Last Service",
        "last_service_value",
        DYNAMIC_UNIT,
        "mdi:car-wrench",
        None,
    ),
    (
        "Next Service",
        "next_service_value",
        DYNAMIC_UNIT,
        "mdi:car-wrench",
        None,
    ),
    (
        "Miles Until Next Service",
        "next_service_mile_value",
        DYNAMIC_UNIT,
        "mdi:car-wrench",
        None,
    ),
]

KIA_US_UNSUPPORTED_INSTRUMENT_KEYS = [
    "ev_max_range_ac_charge_value",
    "ev_max_range_dc_charge_value",
    "ev_charge_fast_duration",
    "ev_charge_portable_duration",
    "ev_charge_station_duration",
    "climate_heated_seat_front_right_on",
    "climate_heated_seat_front_left_on",
    "climate_heated_seat_rear_right_on",
    "climate_heated_seat_rear_left_on",
    "tire_front_right_on",
    "tire_front_left_on",
    "tire_rear_right_on",
    "tire_rear_left_on",
]

SERVICE_NAME_REQUEST_SYNC = "request_sync"
SERVICE_NAME_UPDATE = "update"
SERVICE_NAME_START_CLIMATE = "start_climate"
SERVICE_NAME_STOP_CLIMATE = "stop_climate"
SERVICE_NAME_START_CHARGE = "start_charge"
SERVICE_NAME_STOP_CHARGE = "stop_charge"
SERVICE_NAME_SET_CHARGE_LIMITS = "set_charge_limits"

SERVICE_ATTRIBUTE_TEMPERATURE = "temperature"
SERVICE_ATTRIBUTE_DEFROST = "defrost"
SERVICE_ATTRIBUTE_CLIMATE = "climate"
SERVICE_ATTRIBUTE_HEATING = "heating"
SERVICE_ATTRIBUTE_DURATION = "duration"
SERVICE_ATTRIBUTE_AC_LIMIT = "ac_limit"
SERVICE_ATTRIBUTE_DC_LIMIT = "dc_limit"
