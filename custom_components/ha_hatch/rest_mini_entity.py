import logging

from homeassistant.components.media_player import MediaPlayerEntity, DEVICE_CLASS_SPEAKER
from homeassistant.components.media_player.const import (
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_STOP,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
    MEDIA_TYPE_MUSIC,
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
)
from hatch_rest_api import RestMini, RestMiniAudioTrack, REST_MINI_AUDIO_TRACKS
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RestMiniEntity(MediaPlayerEntity):
    _attr_should_poll = False
    _attr_media_content_type = MEDIA_TYPE_MUSIC
    _attr_device_class = DEVICE_CLASS_SPEAKER
    _attr_supported_features = (
                                    SUPPORT_PAUSE
                                    | SUPPORT_PLAY
                                    | SUPPORT_STOP
                                    | SUPPORT_SELECT_SOUND_MODE
                                    | SUPPORT_VOLUME_SET
                                    | SUPPORT_VOLUME_STEP
                                )

    def __init__(self, rest_mini: RestMini):
        self._attr_unique_id = rest_mini.thing_name
        self._attr_name = rest_mini.device_name
        self.rest_mini = rest_mini
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            manufacturer="Hatch",
            model="Rest Mini",
            name=self._attr_name,
            sw_version=self.rest_mini.firmware_version,
        )
        self._attr_sound_mode_list = list(map(lambda x : x.name, REST_MINI_AUDIO_TRACKS[1:]))

        self.rest_mini.register_callback(self._update_local_state)

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_mini}")
        if self.rest_mini.is_playing:
            self._attr_state = STATE_PLAYING
        else:
            self._attr_state = STATE_IDLE
        self._attr_sound_mode = self.rest_mini.audio_track.name
        self._attr_volume_level = self.rest_mini.volume / 100
        self._attr_device_info.update(sw_version=self.rest_mini.firmware_version)
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        if self.rest_mini.is_playing is not None:
            self._update_local_state()

    def _find_track(self, sound_mode=None):
        if sound_mode is None:
            sound_mode = self._attr_sound_mode
        return next((track for track in REST_MINI_AUDIO_TRACKS if track.name == sound_mode), None)

    def set_volume_level(self, volume):
        self.rest_mini.set_volume(volume*100)

    def media_play(self):
        self.rest_mini.set_audio_track(self.rest_mini.audio_track)

    def media_pause(self):
        self.rest_mini.set_audio_track(RestMiniAudioTrack.NONE)

    def media_stop(self):
        self.rest_mini.set_audio_track(RestMiniAudioTrack.NONE)

    def select_sound_mode(self, sound_mode: str):
        track = self._find_track(sound_mode=sound_mode)
        if track is None:
            track = REST_MINI_AUDIO_TRACKS.NONE
        self.rest_mini.set_audio_track(track)
