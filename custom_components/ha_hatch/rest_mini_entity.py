import logging

from homeassistant.components.media_player import MediaPlayerEntity, DEVICE_CLASS_SPEAKER
from homeassistant.components.media_player.const import (
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_NEXT_TRACK,
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_STOP,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
    MEDIA_TYPE_MUSIC,
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
)
from hatch_rest_api import RestMini, RestMiniAudioTrack, REST_MINI_AUDIO_TRACKS

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
                                    | SUPPORT_VOLUME_MUTE
                                    | SUPPORT_VOLUME_SET
                                    | SUPPORT_VOLUME_STEP
#                                    | SUPPORT_PREVIOUS_TRACK
#                                    | SUPPORT_NEXT_TRACK
                                )

    def __init__(self, rest_mini: RestMini):
        self.rest_mini = rest_mini
        self.rest_mini.register_callback(self._update_local_state)

        self._attr_sound_mode_list = list(map(lambda x : x.name, REST_MINI_AUDIO_TRACKS))

    def _update_local_state(self):
        self._attr_name = self.rest_mini.thing_name
        if self.rest_mini.is_playing:
            self._attr_state = STATE_PLAYING
        else:
            self._attr_state = STATE_IDLE
        self._attr_sound_mode = self.rest_mini.audio_track.name
        self._attr_volume_level = self.rest_mini.volume / 100
#        self.rest_mini.firmware_version

    def mute_volume(self, mute):
        self.rest_mini.set_audio_track(RestMiniAudioTrack.NONE)

    def set_volume_level(self, volume):
        self.rest_mini.set_volume(volume*100)

    def media_play(self):
        self.rest_mini.set_audio_track(self.rest_mini.audio_track)

    def media_pause(self):
        self.mute_volume()

    def media_stop(self):
        self.mute_volume()

    def select_sound_mode(self, sound_mode: str):
        track = next((track for track in REST_MINI_AUDIO_TRACKS if track.name == sound_mode), REST_MINI_AUDIO_TRACKS.NONE)
        self.rest_mini.set_audio_track(track)
