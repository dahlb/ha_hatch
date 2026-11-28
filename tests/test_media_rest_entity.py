"""The Rest Mini and Rest+ media player."""

from __future__ import annotations

from typing import Any

from hatch_rest_api import RestMini, RestMiniAudioTrack, RestPlus, RestPlusAudioTrack
from hatch_rest_api.util import convert_from_percentage
from homeassistant.components.media_player import MediaPlayerState
import pytest

from custom_components.ha_hatch.media_rest_entity import MediaRestEntity

from .conftest import FakeCoordinator, StubShadowClient, build_device

THING = "thing-rest"


def _player(
    device_class: type, state: dict[str, Any], turn_on_media: bool = False
) -> tuple[MediaRestEntity, StubShadowClient]:
    device, client = build_device(device_class, THING, "AA:BB:CC:DD:EE:20")
    device._update_local_state(state)
    client.published.clear()
    return MediaRestEntity(FakeCoordinator([device]), THING, turn_on_media), client


@pytest.mark.parametrize("device_class", [RestMini, RestPlus])
def test_state_before_the_device_reports_a_sound(device_class: type) -> None:
    """Before the shadow reports a sound, volume and sound mode are unknown, not an error.

    Home Assistant can add the entity before the first shadow arrives; a
    property that raises then keeps the media player from being added at all.
    """
    player, _ = _player(device_class, {})
    assert player.sound_mode is None
    if device_class is RestMini:
        assert player.volume_level is None


def test_rest_mini_state() -> None:
    """A Rest Mini reports playing, its track and volume."""
    player, _ = _player(
        RestMini,
        {
            "current": {
                "playing": "remote",
                "sound": {"id": RestMiniAudioTrack.Ocean.value, "v": 32768},
            }
        },
    )
    assert player.state == MediaPlayerState.PLAYING
    assert player.sound_mode == "Ocean"
    assert player.volume_level == 0.5


def test_rest_plus_state() -> None:
    """A Rest+ that is off shows off; on and silent shows idle."""
    off, _ = _player(
        RestPlus, {"isPowered": False, "a": {"t": RestPlusAudioTrack.Ocean.value, "v": 0}}
    )
    idle, _ = _player(RestPlus, {"isPowered": True, "a": {"t": 0, "v": 0}})
    assert off.state == MediaPlayerState.OFF
    assert idle.state == MediaPlayerState.IDLE


async def test_rest_mini_commands() -> None:
    """Volume, sound mode, pause and stop send the Rest Mini's updates."""
    player, client = _player(RestMini, {"current": {"playing": "none", "sound": {"id": 0, "v": 0}}})

    await player.async_set_volume_level(0.4)
    await player.async_select_sound_mode("Water")
    await player.async_media_pause()
    await player.async_select_sound_mode("NotATrack")

    assert client.published[0] == {"current": {"sound": {"v": convert_from_percentage(40)}}}
    assert client.published[1]["current"]["sound"]["id"] == RestMiniAudioTrack.Water.value
    assert client.published[2] == {"current": {"playing": "none", "step": 0}}
    # An unknown sound mode stops playback.
    assert client.published[3] == {"current": {"playing": "none", "step": 0}}


@pytest.mark.parametrize("turn_on_media", [True, False])
async def test_rest_plus_play_turns_it_on_when_configured(turn_on_media: bool) -> None:
    """Playing on a Rest+ also powers it on if that option is set."""
    player, client = _player(
        RestPlus,
        {"isPowered": False, "a": {"t": RestPlusAudioTrack.Ocean.value, "v": 0}},
        turn_on_media,
    )

    await player.async_media_play()

    expected = [{"a": {"t": RestPlusAudioTrack.Ocean.value}}]
    if turn_on_media:
        expected.append({"isPowered": True})
    assert client.published == expected


async def test_rest_plus_turn_off_stops_the_sound() -> None:
    """Turning the Rest+ player off stops its sound, and turning it on powers it."""
    player, client = _player(
        RestPlus, {"isPowered": True, "a": {"t": RestPlusAudioTrack.Ocean.value, "v": 0}}
    )

    await player.async_turn_off()
    await player.async_turn_on()
    await player.async_media_stop()

    assert client.published == [
        {"a": {"t": RestPlusAudioTrack.NONE.value}},
        {"isPowered": True},
        {"a": {"t": RestPlusAudioTrack.NONE.value}},
    ]
