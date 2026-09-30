import unittest


class Av1EncodingTests(unittest.TestCase):
    def test_10_bit_sdr_uses_p010_without_hdr_sei(self):
        from backend.av1.encoding import build_vaapi_command

        command = build_vaapi_command("in.mkv", "out.mkv", {"pix_fmt": "yuv420p10le"}, 1000, 1600)
        self.assertIn("format=p010le,hwupload", command)
        self.assertNotIn("hdr", command)

    def test_pq_and_hlg_keep_color_metadata_and_hdr_sei(self):
        from backend.av1.encoding import build_vaapi_command

        for transfer in ("smpte2084", "arib-std-b67"):
            command = build_vaapi_command(
                "in.mkv",
                "out.mkv",
                {
                    "pix_fmt": "yuv420p10le",
                    "bits_per_raw_sample": "10",
                    "color_primaries": "bt2020",
                    "color_transfer": transfer,
                    "color_space": "bt2020nc",
                    "color_range": "tv",
                    "side_data_list": [{"side_data_type": "Mastering display metadata"}],
                },
                1000,
                1600,
            )
            self.assertIn("-sei", command)
            self.assertIn("hdr", command)
            self.assertIn("-color_primaries", command)
            self.assertIn("bt2020", command)
            self.assertIn("-color_trc", command)
            self.assertIn(transfer, command)

    def test_8_bit_sdr_uses_nv12(self):
        from backend.av1.encoding import build_vaapi_command

        command = build_vaapi_command("in.mkv", "out.mkv", {"pix_fmt": "yuv420p"}, 1000, 1600)
        self.assertIn("format=nv12,hwupload", command)
