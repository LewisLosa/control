import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class BackendContractTests(unittest.TestCase):
    def test_required_environment_value_has_no_empty_default(self):
        from backend.common import required_env

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "PROWLARR_API_KEY"):
                required_env("PROWLARR_API_KEY")

    def test_music_tag_arguments_are_audio_only_and_text_only(self):
        from backend.music.pipeline import build_tag_arguments

        args = build_tag_arguments(
            {
                "title": "Track",
                "artist": "Artist",
                "album": "Album",
                "albumartist": "Artist",
                "tracknumber": "2",
                "discnumber": "1",
                "date": "2024",
                "genre": "Rock",
                "METADATA_BLOCK_PICTURE": "must not pass",
                "COVERART": "must not pass",
            }
        )

        self.assertIn("-map_metadata", args)
        self.assertIn("-1", args)
        self.assertIn("-map", args)
        self.assertNotIn("0:v", args)
        self.assertNotIn("METADATA_BLOCK_PICTURE", args)
        self.assertNotIn("COVERART", args)
        self.assertNotIn("cover.jpg", args)

    def test_missing_output_is_a_failed_task_and_cancelled_stays_cancelled(self):
        from backend.music.worker import result_status

        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "missing.opus")
            self.assertEqual(result_status("processing", missing, None), "failed")
            self.assertEqual(result_status("cancelled", missing, None), "cancelled")

    def test_tagged_music_file_is_readable_by_media_group(self):
        from backend.music.pipeline import tag_opus_file

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "track.opus"
            source.write_bytes(b"source")

            def fake_ffmpeg(command, check):
                Path(command[-1]).write_bytes(b"tagged")

            with patch("backend.music.pipeline.subprocess.run", side_effect=fake_ffmpeg):
                self.assertTrue(
                    tag_opus_file(
                        str(source),
                        title="Track",
                        artist="Artist",
                    )
                )

            self.assertEqual(source.stat().st_mode & 0o777, 0o664)

    def test_av1_backend_exposes_only_control_api(self):
        from backend.av1.api import API_PATHS

        self.assertEqual(API_PATHS, {"/api/status", "/api/enqueue"})
