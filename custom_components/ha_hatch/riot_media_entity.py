import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerDeviceClass,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaType
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
)
from hatch_rest_api import RestIot, RestoreIot, RIoTAudioTrack, REST_IOT_AUDIO_TRACKS
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


class RiotMediaEntity(RestEntity, MediaPlayerEntity):
    _attr_should_poll = False
    _attr_media_content_type = MediaType.MUSIC
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(self, rest_device: RestIot | RestoreIot):
        super().__init__(rest_device, "Media Player")
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

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        if self.rest_device.is_playing:
            self._attr_state = STATE_PLAYING
        else:
            self._attr_state = STATE_IDLE
        self._attr_extra_state_attributes["current"] = self.rest_device.current_playing
        self._attr_extra_state_attributes["current_favorite"] = self.rest_device.current_id
        self._attr_extra_state_attributes["current_step"] = self.rest_device.current_step
        self._attr_sound_mode = self.rest_device.audio_track.name
        self._attr_volume_level = self.rest_device.volume / 100
        self._attr_device_info.update(sw_version=self.rest_device.firmware_version)
        self.schedule_update_ha_state()

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
