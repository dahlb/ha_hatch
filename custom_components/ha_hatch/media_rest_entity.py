from __future__ import annotations
import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerDeviceClass,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaType, MediaPlayerState,
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
    STATE_OFF,
)
from hatch_rest_api import (
    RestPlus,
    RestPlusAudioTrack,
    REST_PLUS_AUDIO_TRACKS,
    RestMini,
    RestMiniAudioTrack,
    REST_MINI_AUDIO_TRACKS,
)

from . import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)


class MediaRestEntity(HatchEntity, MediaPlayerEntity):
    _attr_media_content_type = MediaType.MUSIC
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str, config_turn_on_media: bool):
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
        if isinstance(self.rest_device, RestMini) or self.rest_device.is_on:
            if self.rest_device.is_playing:
                return STATE_PLAYING
            else:
                return STATE_IDLE
        else:
            return STATE_OFF

    @property
    def sound_mode(self) -> str:
        return self.rest_device.audio_track.name

    @property
    def volume_level(self) -> float | None:
        return self.rest_device.volume / 100

    def _find_track(self, sound_mode=None):
        if sound_mode is None:
            sound_mode = self._attr_sound_mode
        if isinstance(self.rest_device, RestMini):
            return next(
                (track for track in REST_MINI_AUDIO_TRACKS if track.name == sound_mode),
                None,
            )
        else:
            return next(
                (track for track in REST_PLUS_AUDIO_TRACKS if track.name == sound_mode),
                None,
            )

    def set_volume_level(self, volume):
        self.rest_device.set_volume(volume * 100)

    def media_play(self):
        self.rest_device.set_audio_track(self.rest_device.audio_track)
        if self.config_turn_on_media:
            self.turn_on()

    def media_pause(self):
        self.rest_device.set_audio_track(self.none_track)

    def media_stop(self):
        self.rest_device.set_audio_track(self.none_track)

    def select_sound_mode(self, sound_mode: str):
        track = self._find_track(sound_mode=sound_mode)
        if track is None:
            track = self.none_track
        self.rest_device.set_audio_track(track)
        if self.config_turn_on_media:
            self.turn_on()

    def turn_off(self):
        self.media_stop()

    def turn_on(self):
        if isinstance(self.rest_device, RestPlus):
            self.rest_device.set_on(True)
