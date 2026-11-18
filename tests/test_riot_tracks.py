import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from hatch_rest_api import RIoTAudioTrack, TimeForBedTrack, TimeToRiseTrack
from hatch_rest_api.const import NO_SOUND_ID

RIOT_TRACKS_MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "ha_hatch"
    / "riot_tracks.py"
)


def load_riot_tracks_module() -> ModuleType:
    spec = spec_from_file_location("ha_hatch_riot_tracks", RIOT_TRACKS_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to load riot_tracks module from {RIOT_TRACKS_MODULE_PATH}"
        )

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProgramSoundsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.riot_tracks = load_riot_tracks_module()

    def test_every_track_is_offered_under_its_category_prefix(self) -> None:
        expected = {
            f"TimeToRise.{track.name}"
            for track in TimeToRiseTrack
            if track is not TimeToRiseTrack.NONE
        } | {
            f"TimeForBed.{track.name}"
            for track in TimeForBedTrack
            if track is not TimeForBedTrack.NONE
        }

        self.assertEqual(set(self.riot_tracks.PROGRAM_SOUNDS), expected)

    def test_names_do_not_collide_with_built_in_sounds(self) -> None:
        built_in_names = {track.name for track in RIoTAudioTrack}

        self.assertFalse(built_in_names & set(self.riot_tracks.PROGRAM_SOUNDS))

    def test_entries_carry_the_library_id_and_mp3_url(self) -> None:
        sound = self.riot_tracks.PROGRAM_SOUNDS["TimeToRise.YukiSaysGoodMorning"]

        self.assertEqual(
            sound,
            {
                "id": TimeToRiseTrack.YukiSaysGoodMorning.value,
                "title": "TimeToRise.YukiSaysGoodMorning",
                "mp3Url": TimeToRiseTrack.track_url_map()[
                    TimeToRiseTrack.YukiSaysGoodMorning.value
                ],
            },
        )
        for track_class, prefix in (
            (TimeToRiseTrack, "TimeToRise"),
            (TimeForBedTrack, "TimeForBed"),
        ):
            url_map = track_class.track_url_map()
            for track in track_class:
                if track is track_class.NONE:
                    continue
                with self.subTest(track=track):
                    sound = self.riot_tracks.PROGRAM_SOUNDS[f"{prefix}.{track.name}"]
                    self.assertEqual(sound["id"], track.value)
                    self.assertEqual(sound["mp3Url"], url_map[track.value])

    def test_sound_ids_map_back_to_a_single_name(self) -> None:
        ids = [sound["id"] for sound in self.riot_tracks.PROGRAM_SOUNDS.values()]

        self.assertEqual(len(ids), len(set(ids)))
        for name, sound in self.riot_tracks.PROGRAM_SOUNDS.items():
            with self.subTest(name=name):
                self.assertEqual(
                    self.riot_tracks.program_sound_name(sound["id"]), name
                )

    def test_other_sound_ids_have_no_program_name(self) -> None:
        for sound_id in (RIoTAudioTrack.Birds.value, NO_SOUND_ID, 0, None):
            with self.subTest(sound_id=sound_id):
                self.assertIsNone(self.riot_tracks.program_sound_name(sound_id))


if __name__ == "__main__":
    unittest.main()
