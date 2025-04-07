import logging
from typing import Mapping, Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerDeviceClass, MediaPlayerState,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaType
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
)
from hatch_rest_api import RIoTAudioTrack, REST_IOT_AUDIO_TRACKS

from . import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)


class MediaRiotEntity(HatchEntity, MediaPlayerEntity):
    _attr_media_content_type = MediaType.MUSIC
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Media Player")
        self._attr_sound_mode_list = [x.name for x in REST_IOT_AUDIO_TRACKS[1:]]
        self._attr_supported_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.SELECT_SOUND_MODE
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )
        self._attr_extra_state_attributes = {}

    @property
    def state(self) -> MediaPlayerState | None:
        if self.rest_device.is_playing:
            return STATE_PLAYING
        else:
            return STATE_IDLE

    @property
    def sound_mode(self) -> str | None:
        if self.rest_device.audio_track is not None:
            return self.rest_device.audio_track.name

    @property
    def volume_level(self) -> float | None:
        return self.rest_device.volume / 100

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return {
            "current": self.rest_device.current_playing,
            "current_favorite": self.rest_device.current_id,
            "current_step": self.rest_device.current_step,
        }

    def set_volume_level(self, volume):
        self.rest_device.set_volume(volume * 100)

    def media_play(self) -> None:
        self.select_sound_mode(self._attr_sound_mode_list[0])

    def _find_track(self, track_name) -> str | None:
        if track_name is None:
            track_name = self._attr_sound_mode
        return next(
            (track for track in REST_IOT_AUDIO_TRACKS if track.name == track_name),
            None,
        )

    def select_sound_mode(self, sound_mode: str) -> None:
        track = self._find_track(track_name=sound_mode)
        if track is None:
            track = RIoTAudioTrack.NONE
        self.rest_device.set_audio_track(track)

    def media_stop(self):
        self.rest_device.set_audio_track(RIoTAudioTrack.NONE)
