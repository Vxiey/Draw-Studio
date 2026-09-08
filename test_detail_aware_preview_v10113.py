import unittest
from PIL import Image, ImageDraw, ImageChops

from PreviewDetailEngine import (
    PREVIEW_DETAIL_MODES,
    detail_aware_resize,
    detail_aware_resize_gray,
    validate_preview_detail_mode,
)
from PixelData import prepare_image


class DetailAwarePreviewTests(unittest.TestCase):
    def _face_like_source(self):
        image = Image.new('RGBA', (96, 64), (230, 190, 160, 255))
        draw = ImageDraw.Draw(image)
        # Tiny high-contrast features intentionally smaller than one final preview cell.
        draw.ellipse((28, 25, 31, 28), fill=(15, 15, 15, 255))
        draw.ellipse((62, 25, 65, 28), fill=(15, 15, 15, 255))
        draw.line((45, 40, 51, 40), fill=(70, 30, 30, 255), width=1)
        return image

    def test_modes_validate(self):
        self.assertEqual(PREVIEW_DETAIL_MODES, ('Fast', 'Balanced', 'Detailed', 'Micro detail'))
        for mode in PREVIEW_DETAIL_MODES:
            self.assertEqual(validate_preview_detail_mode(mode), mode)
        with self.assertRaises(ValueError):
            validate_preview_detail_mode('Ultra face AI')

    def test_detailed_preview_recovers_tiny_dark_features(self):
        source = self._face_like_source()
        normal = source.resize((24, 16), Image.Resampling.LANCZOS).convert('L')
        meta = {}
        detailed = detail_aware_resize(source, (24, 16), 'Detailed', metadata=meta).convert('L')
        # Standard Lanczos averages the tiny eyes strongly. Detail-aware preview
        # should keep at least one much darker representative pixel.
        self.assertLess(min(detailed.getdata()), min(normal.getdata()) - 20)
        self.assertGreater(meta['preview_detail_recovered_cells'], 0)
        self.assertGreater(meta['preview_detail_recovered_percent'], 0)
        self.assertEqual(meta['preview_detail_oversample'], 2)

    def test_flat_areas_do_not_gain_false_texture(self):
        source = Image.new('RGBA', (120, 80), (124, 150, 180, 255))
        meta = {}
        out = detail_aware_resize(source, (30, 20), 'Detailed', metadata=meta)
        self.assertIsNone(ImageChops.difference(out, Image.new('RGBA', out.size, (124, 150, 180, 255))).getbbox())
        self.assertEqual(meta['preview_detail_recovered_cells'], 0)

    def test_gray_path_preserves_micro_contrast(self):
        source = self._face_like_source().convert('L')
        normal = source.resize((24, 16), Image.Resampling.LANCZOS)
        meta = {}
        detailed = detail_aware_resize_gray(source, (24, 16), 'Detailed', metadata=meta)
        self.assertLess(min(detailed.getdata()), min(normal.getdata()) - 20)
        self.assertEqual(detailed.mode, 'L')
        self.assertGreater(meta['preview_detail_recovered_cells'], 0)

    def test_prepare_image_can_enable_detail_aware_preview_only_on_request(self):
        source = self._face_like_source()
        meta = {}
        enhanced, fitted = prepare_image(
            source, (24, 16), 10, sample_limit=24, max_pixels=384,
            preview_detail_mode='Detailed', preview_detail_meta=meta)
        normal, fitted2 = prepare_image(source, (24, 16), 10, sample_limit=24, max_pixels=384)
        self.assertEqual(fitted, fitted2)
        self.assertEqual(enhanced.size, normal.size)
        self.assertGreater(meta['preview_detail_recovered_cells'], 0)
        self.assertNotEqual(enhanced.tobytes(), normal.tobytes())

    def test_cancellation_is_honored_before_heavy_resize(self):
        with self.assertRaises(InterruptedError):
            detail_aware_resize(self._face_like_source(), (24, 16), 'Detailed', cancelled=lambda: True)


if __name__ == '__main__':
    unittest.main()
