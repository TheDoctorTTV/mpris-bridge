from __future__ import annotations

import unittest

from mpris_bridge.schema import bridge_payload, session_payload


class SchemaTests(unittest.TestCase):
    def test_session_payload_matches_smtc_shape(self) -> None:
        payload = session_payload(
            "org.mpris.MediaPlayer2.spotify",
            {"DesktopEntry": "spotify", "Identity": "Spotify"},
            {
                "Metadata": {
                    "xesam:title": "Track",
                    "xesam:artist": ["Artist"],
                    "xesam:album": "Album",
                    "xesam:albumArtist": ["Album Artist"],
                    "xesam:genre": ["Pop"],
                    "xesam:trackNumber": 7,
                    "mpris:length": 245000000,
                },
                "PlaybackStatus": "Playing",
                "Rate": 1.0,
                "Shuffle": True,
                "LoopStatus": "Playlist",
                "Position": 120000000,
            },
            "data:image/png;base64,abc",
        )

        self.assertEqual(payload["source_app_id"], "spotify")
        self.assertEqual(payload["media_properties"]["Title"], "Track")
        self.assertEqual(payload["media_properties"]["Artist"], "Artist")
        self.assertEqual(payload["media_properties"]["Thumbnail"], "data:image/png;base64,abc")
        self.assertEqual(payload["playback_info"]["PlaybackStatus"], 4)
        self.assertEqual(payload["playback_info"]["AutoRepeatMode"], 2)
        self.assertEqual(payload["timeline_properties"]["Position"], 120000)
        self.assertEqual(payload["timeline_properties"]["EndTime"], 245000)

    def test_bridge_payload_selects_playing_session(self) -> None:
        sessions = [
            {"source_app_id": "paused", "playback_info": {"PlaybackStatus": 5}},
            {"source_app_id": "playing", "playback_info": {"PlaybackStatus": 4}},
        ]

        payload = bridge_payload(sessions, app_version="test")

        self.assertEqual(payload["app_version"], "test")
        self.assertEqual(payload["current_session_id"], "playing")
        self.assertEqual(payload["sessions"], sessions)

    def test_unknown_stream_length_maps_to_zero(self) -> None:
        payload = session_payload(
            "org.mpris.MediaPlayer2.browser",
            {},
            {
                "Metadata": {"mpris:length": 9223372036854775807},
                "PlaybackStatus": "Playing",
                "Position": 1000000,
            },
            None,
        )

        self.assertEqual(payload["timeline_properties"]["EndTime"], 0)
        self.assertEqual(payload["timeline_properties"]["MaxSeekTime"], 0)


if __name__ == "__main__":
    unittest.main()
