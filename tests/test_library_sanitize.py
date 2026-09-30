import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class LibrarySanitizeTests(unittest.TestCase):
    def test_apply_requires_a_backup_directory(self):
        from backend.music.library_sanitize import main

        with tempfile.TemporaryDirectory() as tmp, patch("sys.argv", ["sanitize", tmp, "--apply"]):
            with self.assertRaises(SystemExit):
                main()

    def test_inventory_reports_embedded_art_and_sidecars(self):
        from backend.music import library_sanitize

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "track.opus"
            sidecar = root / "cover.jpg"
            audio.touch()
            sidecar.touch()
            with patch.object(library_sanitize, "probe_artwork", return_value=True):
                entries = library_sanitize.inventory(root)
            self.assertEqual({entry["type"] for entry in entries}, {"embedded", "sidecar"})
