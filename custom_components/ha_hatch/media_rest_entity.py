"""Media player entity for Hatch Rest devices."""

from __future__ import annotations

import logging
from typing import Any

from hatch_rest_api import (
    REST_MINI_AUDIO_TRACKS,
    REST_PLUS_AUDIO_TRACKS,
    RestMini,
    RestMiniAudioTrack,
    RestPlus,
    RestPlusAudioTrack,
)
from homeassistant.components.media_player import MediaPlayerDeviceClass, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.const import STATE_IDLE, STATE_OFF, STATE_PLAYING

from . import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)


class MediaRestEntity(HatchEntity, MediaPlayerEntity):
    """Media rest entity."""

    _attr_media_content_type = MediaType.MUSIC
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(
        self, coordinator: HatchDataUpdateCoordinator, thing_name: str, config_turn_on_media: bool
    ) -> None:
        """Initialize the media rest entity."""
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Media Player")
        self.config_turn_on_media: bool = config_turn_on_media
        if isinstance(self.rest_device, RestMini):
            self._attr_sound_mode_list = [x.name for x in REST_MINI_AUDIO_TRACKS[1:]]
            self.none_track = RestMiniAudioTrack.NONE
            self._attr_supported_features = (
                MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.PLAY
                | MediaPlayerEntityFeature.STOP
                | MediaPlayerEntityFeature.SELECT_SOUND_MODE
                | MediaPlayerEntityFeature.VOLUME_SET
                | MediaPlayerEntityFeature.VOLUME_STEP
            )
        else:
            self._attr_sound_mode_list = [x.name for x in REST_PLUS_AUDIO_TRACKS[1:]]
            self.none_track = RestPlusAudioTrack.NONE
            self._attr_supported_features = (
                MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.PLAY
                | MediaPlayerEntityFeature.STOP
                | MediaPlayerEntityFeature.SELECT_SOUND_MODE
                | MediaPlayerEntityFeature.VOLUME_SET
                | MediaPlayerEntityFeature.VOLUME_STEP
                | MediaPlayerEntityFeature.TURN_ON
                | MediaPlayerEntityFeature.TURN_OFF
            )

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the media player state."""
        if isinstance(self.rest_device, RestMini) or self.rest_device.is_on:
            if self.rest_device.is_playing:
                return STATE_PLAYING
            return STATE_IDLE
        return STATE_OFF

    @property
    def sound_mode(self) -> str:
        """Return the current sound mode."""
        return self.rest_device.audio_track.name

    @property
    def volume_level(self) -> float | None:
        """Return the volume level (0..1)."""
        return self.rest_device.volume / 100

    def _find_track(self, sound_mode: str | None = None) -> Any:
        if sound_mode is None:
            sound_mode = self.sound_mode
        if isinstance(self.rest_device, RestMini):
            return next(
                (track for track in REST_MINI_AUDIO_TRACKS if track.name == sound_mode),
                None,
            )
        return next(
            (track for track in REST_PLUS_AUDIO_TRACKS if track.name == sound_mode),
            None,
        )

    def set_volume_level(self, volume: float) -> None:
        """Set the volume level (0..1)."""
        self.rest_device.set_volume(volume * 100)

    def media_play(self) -> None:
        """Start playback."""
        self.rest_device.set_audio_track(self.rest_device.audio_track)
        if self.config_turn_on_media:
            self.turn_on()

    def media_pause(self) -> None:
        """Pause playback."""
        self.rest_device.set_audio_track(self.none_track)

    def media_stop(self) -> None:
        """Stop playback."""
        self.rest_device.set_audio_track(self.none_track)

    def select_sound_mode(self, sound_mode: str) -> None:
        """Select a sound mode."""
        track = self._find_track(sound_mode=sound_mode)
        if track is None:
            track = self.none_track
        self.rest_device.set_audio_track(track)
        if self.config_turn_on_media:
            self.turn_on()

    def turn_off(self) -> None:
        """Turn the entity off."""
        self.media_stop()

    def turn_on(self) -> None:
        """Turn the entity on."""
        if isinstance(self.rest_device, RestPlus):
            self.rest_device.set_on(True)
