"""The light entities read device state and send the expected shadow updates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

from hatch_rest_api import RestIot, RestoreIot, RestoreV5, RestPlus
from hatch_rest_api.const import CUSTOM_COLOR_ID, NO_COLOR_ID, RIOT_FLAGS_CLOCK_ON
from hatch_rest_api.restore_v5 import pack_dual_percentages
from hatch_rest_api.util import convert_from_hex, convert_from_percentage
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ATTR_RGBW_COLOR
import pytest

from custom_components.ha_hatch import light_riot_clock_entity
from custom_components.ha_hatch.light_rest_entity import LightRestEntity
from custom_components.ha_hatch.light_restoreiot_entity import LightRestoreIotEntity
from custom_components.ha_hatch.light_riot_clock_entity import LightRiotClockEntity
from custom_components.ha_hatch.light_riot_entity import LightRiotEntity

from .conftest import FakeCoordinator, StubShadowClient, build_device

THING = "thing-light"


def _light[T](
    entity_class: type[T], device_class: type, state: dict[str, Any], **kwargs: Any
) -> tuple[T, Any, StubShadowClient]:
    device, client = build_device(device_class, THING, "AA:BB:CC:DD:EE:10")
    device._update_local_state(state)
    client.published.clear()
    entity = entity_class(FakeCoordinator([device]), THING, **kwargs)  # type: ignore[call-arg]
    return entity, device, client


# ---- Rest+ ---------------------------------------------------------------------

RED_HALF = {
    "isPowered": True,
    "c": {"r": 65535, "g": 0, "b": 0, "i": 32768, "R": False, "W": False},
}


def test_rest_plus_light_state() -> None:
    """The Rest+ light reports on, brightness and color from the device."""
    light, _, _ = _light(LightRestEntity, RestPlus, RED_HALF, config_turn_on_light=True)

    assert light.is_on is True
    assert light.brightness == 128
    assert light.rgb_color == (255, 0, 0)


def test_rest_plus_light_off_at_zero_brightness() -> None:
    """A Rest+ that is on with zero brightness shows the light off."""
    state = {"isPowered": True, "c": {"r": 65535, "g": 0, "b": 0, "i": 0, "R": False, "W": False}}
    light, _, _ = _light(LightRestEntity, RestPlus, state, config_turn_on_light=True)
    assert light.is_on is False


@pytest.mark.parametrize("turn_on_power", [True, False])
async def test_rest_plus_turn_on(turn_on_power: bool) -> None:
    """Turning the light on sets the color, and powers the Rest+ on if configured."""
    light, _, client = _light(
        LightRestEntity, RestPlus, RED_HALF, config_turn_on_light=turn_on_power
    )

    await light.async_turn_on(**{ATTR_BRIGHTNESS: 255, ATTR_RGB_COLOR: (0, 0, 255)})

    color = {
        "c": {
            "r": 0,
            "g": 0,
            "b": convert_from_hex(255),
            "i": convert_from_percentage(100),
            "W": False,
            "R": False,
        }
    }
    assert client.published == ([color, {"isPowered": True}] if turn_on_power else [color])


async def test_rest_plus_turn_on_keeps_the_current_color_and_brightness() -> None:
    """With no arguments the light turns on at its current color and brightness."""
    light, _, client = _light(LightRestEntity, RestPlus, RED_HALF, config_turn_on_light=False)
    await light.async_turn_on()
    assert client.published[0]["c"]["r"] == convert_from_hex(255)
    assert client.published[0]["c"]["i"] == convert_from_percentage(50)


async def test_rest_plus_turn_off_sets_brightness_zero() -> None:
    """Turning the light off keeps the color and sets brightness to zero."""
    light, _, client = _light(LightRestEntity, RestPlus, RED_HALF, config_turn_on_light=True)
    await light.async_turn_off()
    assert client.published[0]["c"]["i"] == 0
    assert client.published[0]["c"]["r"] == convert_from_hex(255)


# ---- Rest 2nd gen ----------------------------------------------------------------

RIOT_GREEN = {
    "current": {
        "playing": "remote",
        "sound": {"id": 19998},
        "color": {"id": CUSTOM_COLOR_ID, "r": 0, "g": 65535, "b": 0, "i": 16384, "w": 0},
    }
}


def test_riot_light_state() -> None:
    """The Rest 2nd gen light reports its color and brightness."""
    light, _, _ = _light(LightRiotEntity, RestIot, RIOT_GREEN)
    assert light.is_on is True
    assert light.rgb_color == (0, 255, 0)
    assert light.brightness == 64


async def test_riot_turn_on_without_arguments_restores_the_last_color() -> None:
    """After the light was seen on, turning it on again restores that color."""
    light, device, client = _light(LightRiotEntity, RestIot, RIOT_GREEN)
    assert light.is_on  # remembers green at 25%
    device._update_local_state({"current": {"color": {"id": NO_COLOR_ID}}})
    assert light.is_on is False

    await light.async_turn_on()

    color = client.published[0]["current"]["color"]
    assert (color["r"], color["g"], color["b"]) == (0, convert_from_hex(255), 0)
    assert color["i"] == convert_from_percentage(25)


async def test_riot_turn_on_white_sets_the_white_channel() -> None:
    """Pure white also turns on the white LED."""
    light, _, client = _light(LightRiotEntity, RestIot, RIOT_GREEN)
    await light.async_turn_on(**{ATTR_RGB_COLOR: (255, 255, 255), ATTR_BRIGHTNESS: 255})
    assert client.published[0]["current"]["color"]["w"] == 65535


async def test_riot_turn_off_keeps_a_playing_sound() -> None:
    """Turning the light off with no sound playing stops remote playback."""
    light, _, client = _light(LightRiotEntity, RestIot, RIOT_GREEN)
    await light.async_turn_off()
    assert client.published == [
        {
            "current": {
                "playing": "none",
                "color": {"id": NO_COLOR_ID, "r": 0, "g": 0, "b": 0, "w": 0},
            }
        }
    ]


# ---- Restore (1st gen) -----------------------------------------------------------

RESTORE_BLUE = {
    "current": {
        "playing": "routine",
        "color": {"id": CUSTOM_COLOR_ID, "r": 0, "g": 0, "b": 65535, "w": 0, "i": 65535},
    }
}


def test_restore_iot_light_state() -> None:
    """The Restore light reports its color, including white."""
    light, _, _ = _light(LightRestoreIotEntity, RestoreIot, RESTORE_BLUE)
    assert light.is_on is True
    assert light.rgbw_color == (0, 0, 255, 0)
    assert light.brightness == 255


async def test_restore_iot_white_lifts_the_rgb_channels() -> None:
    """Adding white raises the RGB channels by the same amount, as the Hatch app does."""
    light, _, client = _light(LightRestoreIotEntity, RestoreIot, RESTORE_BLUE)

    await light.async_turn_on(**{ATTR_RGBW_COLOR: (100, 50, 0, 80), ATTR_BRIGHTNESS: 255})

    color = client.published[0]["current"]["color"]
    assert (color["r"], color["g"], color["b"]) == (
        convert_from_hex(180),
        convert_from_hex(130),
        convert_from_hex(80),
    )
    assert color["w"] == convert_from_hex(80)


async def test_restore_iot_turn_on_without_arguments_uses_the_default() -> None:
    """A light never seen on turns on at the default grey at 50%."""
    light, _, client = _light(LightRestoreIotEntity, RestoreIot, {"current": {"playing": "none"}})
    await light.async_turn_on()
    color = client.published[0]["current"]["color"]
    assert color["r"] == convert_from_hex(127)
    assert color["i"] == convert_from_percentage(50)


async def test_restore_iot_turn_off() -> None:
    """Turning the light off during a routine sends only the color."""
    light, _, client = _light(LightRestoreIotEntity, RestoreIot, RESTORE_BLUE)
    await light.async_turn_off()
    assert list(client.published[0]["current"]) == ["color"]


# ---- Clock ---------------------------------------------------------------------


async def test_single_channel_clock() -> None:
    """A Rest 2nd gen clock has one brightness, set by turning the light on."""
    clock, _, client = _light(
        LightRiotClockEntity, RestIot, {"clock": {"i": 32768, "flags": RIOT_FLAGS_CLOCK_ON}}
    )
    assert clock.is_on is True
    assert clock.brightness == 128

    await clock.async_turn_on(**{ATTR_BRIGHTNESS: 51})
    await clock.async_turn_off()

    assert client.published[0]["clock"]["i"] == convert_from_percentage(20)
    assert client.published[1]["clock"]["flags"] == 0


DUAL = {
    "clock": {
        "i": pack_dual_percentages(10, 90),
        "flags": RIOT_FLAGS_CLOCK_ON,
        "turnBrightAt": "07:00",
        "turnDimAt": "19:00",
    }
}


@pytest.mark.parametrize(
    ("hour", "shown", "packed"),
    [
        # Daytime: the slider shows and sets the daytime brightness.
        (12, 230, pack_dual_percentages(10, 40)),
        # Night: the nighttime brightness.
        (22, 26, pack_dual_percentages(40, 90)),
    ],
)
async def test_dual_channel_clock_drives_the_channel_on_display(
    hour: int, shown: int, packed: int
) -> None:
    """A Restore 3 clock shows and sets the brightness of the channel currently displayed."""
    clock, _, client = _light(LightRiotClockEntity, RestoreV5, DUAL)
    now = datetime(2026, 1, 1, hour, 0, tzinfo=UTC)
    with patch.object(light_riot_clock_entity.dt_util, "now", return_value=now):
        assert clock.brightness == shown
        await clock.async_turn_on(**{ATTR_BRIGHTNESS: 102})

    assert client.published[0]["clock"]["i"] == packed


def test_dual_channel_clock_without_a_schedule_shows_night() -> None:
    """Without bright/dim times the nighttime channel is the one on display."""
    state = {"clock": {"i": pack_dual_percentages(10, 90), "flags": RIOT_FLAGS_CLOCK_ON}}
    clock, _, _ = _light(LightRiotClockEntity, RestoreV5, state)
    assert clock.brightness == 26
