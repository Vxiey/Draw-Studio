import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

from DrawBot import DrawBotApp, make_plan
from PictureCustomPalette import build_picture_palette, apply_custom_rgb_sequence
from PicturePalettePlanning import active_picture_palette
from test_pixel_accurate_v1086 import opts
from test_picture_custom_palette_v10142 import Var, Mouse, Keyboard


RGB = ((32, 30, 29), (112, 115, 117), (203, 169, 146), (132, 34, 40))
FALLBACK = ((0, 0, 0), (255, 255, 255), (220, 0, 0), (128, 128, 128))


def source():
    image = Image.new('RGBA', (40, 24), 'white')
    draw = ImageDraw.Draw(image)
    for i, rgb in enumerate(RGB):
        draw.rectangle((i * 10, 0, i * 10 + 9, 23), fill=rgb + (255,))
    return image


class PicturePalettePipelineTests(unittest.TestCase):
    def test_saved_colors_come_from_source_without_standard_palette_substitution(self):
        with tempfile.TemporaryDirectory() as tmp, patch('PictureCustomPalette.data_dir', return_value=Path(tmp)):
            palette = build_picture_palette(source(), FALLBACK, max_colors=4, fidelity='Faithful')
        self.assertEqual(set(palette.colors), set(RGB))
        mouse = Mouse()
        keyboard = Keyboard()
        controls = dict(OpenCustomColor=(1, 1), RedField=(2, 2), GreenField=(3, 3),
                        BlueField=(4, 4), AddCustomColor=(5, 5), ConfirmColor=(6, 6))
        apply_custom_rgb_sequence(mouse, keyboard, controls, palette.colors, wait=lambda _: None)
        typed = [int(a[1]) for a in keyboard.actions if a[0] == 'write']
        self.assertEqual(tuple(tuple(typed[i:i+3]) for i in range(0, len(typed), 3)), palette.colors)
        self.assertEqual(mouse.actions.count(('move', 5, 5)), len(palette.colors))

    def test_pixel_and_run_plans_use_identical_prepared_rgb_and_runtime_selectors(self):
        for quality in ('Pixel Accurate', 'High likeness'):
            with self.subTest(quality=quality):
                plan = make_plan(source(), (40, 24), opts(
                    profile_name='Microsoft Paint', profile_key='microsoft-paint',
                    picture_palette_rgb=RGB, exact_color_available=True,
                    custom_color_workflow='Adaptive exact (recommended)',
                    draw_quality=quality, auto_tune=False, hybrid_mode='Manual'))
                self.assertEqual(plan['colors'], RGB)
                self.assertEqual(tuple(s['rgb'] for s in plan['color_selectors']), RGB)
                self.assertTrue(all(s['kind'] == 'custom' and s['require_exact'] for s in plan['color_selectors']))
                self.assertEqual(plan['options']['picture_palette_meta']['source'], 'prepared-picture-palette')
                if quality == 'Pixel Accurate':
                    target = np.asarray(plan['options']['_accuracy_quantized_target'])
                    self.assertTrue(np.array_equal(target, np.asarray(source().convert('RGB'))))

    def test_prepared_color_never_reuses_cached_standard_palette_method(self):
        from AdaptiveColor import method_candidates
        actions={k:(0,0) for k in ('OpenCustomColor','ConfirmColor','RedField','GreenField','BlueField')}
        methods=method_candidates({'kind':'custom','prefer_numeric':True,'require_exact':True},
                                  actions,cached_method='palette')
        self.assertEqual(methods,('numeric',))

    def test_missing_exact_capability_blocks_prepared_palette(self):
        with patch('DrawBot.resolve_image_custom_color_workflow', return_value={'available': False}):
            with self.assertRaisesRegex(ValueError, 'RGB controls'):
                make_plan(source(), (40, 24), opts(profile_name='Microsoft Paint',
                    picture_palette_rgb=RGB, exact_color_available=False))

    def test_completed_palette_invalidates_preview_and_isolated_by_image_and_profile(self):
        image = source()
        app = SimpleNamespace(game=Var('Microsoft Paint'), original=image, plan={'old': True},
                              custom_color_workflow=Var('Calibrated palette'), pending_clear_drawing=None)
        calls = []
        def stale(message):
            app.plan = None
            calls.append(message)
        app._mark_plan_stale = stale
        app.refresh_exact_color_status = lambda: calls.append('refresh-exact')
        app.save_settings = lambda: None
        app.show_previews = lambda: None
        state = dict(profile_key='microsoft-paint', image_id=id(image), colors=RGB, prepared_count=4)
        DrawBotApp._handle_event(app, 'picture_palette_complete', state)
        self.assertIsNone(app.plan)
        self.assertIn('refresh-exact', calls)
        self.assertEqual(active_picture_palette(app), RGB)
        self.assertEqual(app.custom_color_workflow.get(), 'Adaptive exact (recommended)')
        app.game.set('Other drawing app')
        self.assertEqual(active_picture_palette(app), ())
        app.game.set('Microsoft Paint'); app.original = source()
        self.assertEqual(active_picture_palette(app), ())
        app.original = image; app.picture_custom_palette_state['prepared_count'] = 3
        self.assertEqual(active_picture_palette(app), ())


if __name__ == '__main__':
    unittest.main()
