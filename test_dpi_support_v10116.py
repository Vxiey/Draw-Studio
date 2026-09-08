import unittest

from DpiSupport import BASE_DPI, DpiInfo, normalize_uniform_capture_mapping


class DpiSupportV10116Tests(unittest.TestCase):
    def test_uniform_4k_150_percent_mapping(self):
        sx, sy = normalize_uniform_capture_mapping((2560, 1440), (3840, 2160))
        self.assertAlmostEqual(sx, 1.5)
        self.assertAlmostEqual(sy, 1.5)

    def test_uniform_4k_200_percent_mapping(self):
        sx, sy = normalize_uniform_capture_mapping((1920, 1080), (3840, 2160))
        self.assertEqual((sx, sy), (2.0, 2.0))

    def test_non_uniform_mapping_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Mixed display scaling'):
            normalize_uniform_capture_mapping((1920, 1080), (3840, 1800))

    def test_dpi_info_scale_is_explicit(self):
        info = DpiInfo(144, 'test', 144 / BASE_DPI, (-1920, 0, 1920, 2160))
        data = info.as_dict()
        self.assertEqual(data['dpi'], 144)
        self.assertEqual(data['dpi_scale'], 1.5)
        self.assertEqual(data['monitor_rect'], (-1920, 0, 1920, 2160))


if __name__ == '__main__':
    unittest.main()
