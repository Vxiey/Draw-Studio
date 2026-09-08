from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one patch anchor, found {count}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')


# 1) Microsoft Paint only: reliable held-drag delivery for Sketch/Shape/Smart paths too.
replace_once('StrokeDelivery.py',
"""        return StrokeDeliveryPolicy(
            step_px=min(requested, 4.0), min_path_delay=0.0025,
            press_settle=0.007, release_settle=0.004,
            drag_backend='cursor', native_drag_reliability=False,
            label='Microsoft Paint adaptive compatible drag', palette_click_delay=.28,
            ui_control_delay=.22, profile_key=key)
""",
"""        # RC2 Paint-only line reliability hotfix. Modern Paint can drop short
        # or sharp SetCursorPos-held gestures even when Windows reports every
        # requested endpoint. Browser canvases do not use this branch. Auto now
        # uses non-coalesced SendInput for Paint's normal line/path renderers as
        # well as Pixel Accurate. Explicit Compatible remains an escape hatch.
        drawing_mode=str(options.get('drawing_mode') or options.get('mode') or '').strip().lower()
        line_sensitive=drawing_mode in {
            'shape paths','smart paths (recommended)','lines (fastest)','lines',
        }
        return StrokeDeliveryPolicy(
            step_px=min(requested, 2.0 if line_sensitive else 2.5),
            min_path_delay=(0.0032 if line_sensitive else 0.0030),
            press_settle=0.010, release_settle=0.006,
            drag_backend='sendinput', native_drag_reliability=True,
            label=('Microsoft Paint reliable line drag' if line_sensitive else 'Microsoft Paint reliable drag'),
            palette_click_delay=.28, ui_control_delay=.22, profile_key=key)
""")

# 2) Central Paint-only capability resolver for image-driven custom colors.
replace_once('ExactColorTools.py',
"""def custom_rgb_available(profile_key,path=None):
    \"\"\"Exact-color capability via visual spectrum or numeric RGB fields.\"\"\"
    return spectrum_available(profile_key,path) or numeric_rgb_available(profile_key,path)


def eyedropper_available(profile_key,path=None):
""",
"""def custom_rgb_available(profile_key,path=None):
    \"\"\"Exact-color capability via visual spectrum or numeric RGB fields.\"\"\"
    return spectrum_available(profile_key,path) or numeric_rgb_available(profile_key,path)


def resolve_image_custom_color_workflow(profile_name, profile_key, requested_workflow, *, render_preset='Auto', path=None):
    \"\"\"Resolve automatic image-driven custom colors without widening target scope.

    Only Microsoft Paint is auto-promoted. A valid calibrated Edit colors
    spectrum or numeric RGB workflow is required. Manual render preset preserves
    an explicit ``Calibrated palette`` choice; Auto/Masterpiece/Extra fast may
    promote it to Adaptive exact so the current image's useful colors are selected
    automatically. Other targets are returned unchanged.
    \"\"\"
    requested=str(requested_workflow or 'Calibrated palette')
    key=str(profile_key or '').strip().lower()
    paint=(str(profile_name or '').strip()=='Microsoft Paint' or key=='microsoft-paint')
    if not paint:
        return {'workflow':requested,'available':False,'auto_promoted':False,'profile_key':key,'reason':'not-microsoft-paint'}
    try:
        available=bool(custom_rgb_available(key or 'microsoft-paint',path))
    except Exception:
        available=False
    manual=str(render_preset or 'Auto').strip().lower()=='manual'
    promote=bool(available and not manual and requested=='Calibrated palette')
    workflow='Adaptive exact (recommended)' if promote else requested
    return {
        'workflow':workflow,'available':available,'auto_promoted':promote,
        'profile_key':key or 'microsoft-paint',
        'reason':('calibrated-custom-color-auto' if promote else ('custom-color-ready' if available else 'custom-color-unavailable')),
    }


def eyedropper_available(profile_key,path=None):
""")

# 3) DrawBot consumes the capability in both planning and the real preflight.
replace_once('DrawBot.py',
"""from ExactColorTools import (custom_rgb_available, eyedropper_available, spectrum_available, numeric_rgb_available,
                             resolved_controls as resolve_exact_color_controls)
""",
"""from ExactColorTools import (custom_rgb_available, eyedropper_available, spectrum_available, numeric_rgb_available,
                             resolve_image_custom_color_workflow,
                             resolved_controls as resolve_exact_color_controls)
""")

replace_once('DrawBot.py',
"""    custom_color_workflow=options.get('custom_color_workflow','Calibrated palette')
    dynamic_exact=(custom_color_workflow in ('Exact custom + palette fallback','Adaptive exact (recommended)'))
""",
"""    custom_color_workflow=options.get('custom_color_workflow','Calibrated palette')
    # Paint-only: an older saved profile may still say Calibrated palette even
    # though Edit colors was calibrated later. Auto presets now discover that
    # capability from profile-local calibration and use image-driven Adaptive
    # exact planning. Manual preset deliberately preserves palette-only intent.
    custom_resolution=resolve_image_custom_color_workflow(
        options.get('profile_name'), options.get('profile_key'), custom_color_workflow,
        render_preset=options.get('render_preset','Auto'))
    custom_color_workflow=custom_resolution['workflow']
    if custom_resolution.get('available'):
        plan_options['exact_color_available']=True
    if custom_resolution.get('auto_promoted'):
        plan_options['custom_color_workflow']=custom_color_workflow
        plan_options['custom_color_auto_meta']=dict(custom_resolution)
    dynamic_exact=(custom_color_workflow in ('Exact custom + palette fallback','Adaptive exact (recommended)'))
""")

replace_once('DrawBot.py',
"""            lines=options['lines'],exact_available=bool(options.get('exact_color_available')),
""",
"""            lines=options['lines'],exact_available=bool(plan_options.get('exact_color_available')),
""")

replace_once('DrawBot.py',
"""        if bool(options.get('exact_color_available')) and grouping_mode=='Reduced palette':
""",
"""        if bool(plan_options.get('exact_color_available')) and grouping_mode=='Reduced palette':
""")

replace_once('DrawBot.py',
"""            if options.get('custom_color_workflow') in ('Exact custom + palette fallback','Adaptive exact (recommended)'):
                try:
                    exact_actions=resolve_exact_color_controls(profile_key,current_client)
""",
"""            # Paint-only real preflight: resolve stale palette-only saved
            # settings against the *actual* profile calibration before planning.
            # This is what lets Draw Studio open Edit colors automatically when
            # the current image reaches a useful custom RGB batch.
            custom_resolution=resolve_image_custom_color_workflow(
                self.game.get(), profile_key, options.get('custom_color_workflow','Calibrated palette'),
                render_preset=options.get('render_preset','Auto'))
            if custom_resolution.get('auto_promoted'):
                options['custom_color_workflow']=custom_resolution['workflow']
                options['custom_color_auto_meta']=dict(custom_resolution)
                log_event('Microsoft Paint custom-color workflow auto-promoted from calibrated palette to Adaptive exact for this image.')
            if options.get('custom_color_workflow') in ('Exact custom + palette fallback','Adaptive exact (recommended)'):
                try:
                    exact_actions=resolve_exact_color_controls(profile_key,current_client)
""")

# 4) Update old Paint input expectations: browser policies remain untouched.
replace_once('test_stroke_delivery_v1062.py',
"""    def test_paint_auto_keeps_compatible_policy_for_non_pixel_draws(self):
        policy=resolve_stroke_delivery({'profile_name':'Microsoft Paint','stroke_step_px':8},dry_run=False)
        self.assertEqual(policy.step_px,4.0)
        self.assertGreaterEqual(policy.min_path_delay,0.002)
        self.assertGreater(policy.press_settle,0)
        self.assertGreater(policy.release_settle,0)
        self.assertEqual(policy.drag_backend,'cursor')
        self.assertFalse(policy.native_drag_reliability)
""",
"""    def test_paint_auto_uses_reliable_delivery_for_non_pixel_draws(self):
        policy=resolve_stroke_delivery({'profile_name':'Microsoft Paint','stroke_step_px':8},dry_run=False)
        self.assertLessEqual(policy.step_px,2.5)
        self.assertGreaterEqual(policy.min_path_delay,0.003)
        self.assertGreaterEqual(policy.press_settle,0.010)
        self.assertGreaterEqual(policy.release_settle,0.006)
        self.assertEqual(policy.drag_backend,'sendinput')
        self.assertTrue(policy.native_drag_reliability)

    def test_paint_shape_paths_get_denser_reliable_line_policy(self):
        policy=resolve_stroke_delivery({'profile_name':'Microsoft Paint','stroke_step_px':8,'drawing_mode':'Shape paths'},dry_run=False)
        self.assertEqual(policy.step_px,2.0)
        self.assertEqual(policy.drag_backend,'sendinput')
        self.assertIn('line',policy.label.lower())
""")

replace_once('test_per_game_input_engine_v1075.py',
"""        self.assertEqual(p.step_px,4.0)
        self.assertEqual(p.palette_click_delay,.28)
""",
"""        self.assertLessEqual(p.step_px,2.5)
        self.assertEqual(p.drag_backend,'sendinput')
        self.assertTrue(p.native_drag_reliability)
        self.assertEqual(p.palette_click_delay,.28)
""")

Path('test_paint_custom_color_auto_v10130.py').write_text(r'''import tempfile
import unittest
from pathlib import Path

from CalibrationAnchors import make_anchor
from ExactColorTools import save, resolve_image_custom_color_workflow


class PaintCustomColorAutoV10130Tests(unittest.TestCase):
    def calibration(self, root):
        path=Path(root)/'exact.json'
        save('microsoft-paint',{
            'OpenCustomColor':(10,10),'ConfirmColor':(20,20),
            'RedField':(30,30),'GreenField':(40,40),'BlueField':(50,50),
        },anchor=make_anchor((0,0,800,600)),path=path)
        return path

    def test_auto_paint_promotes_palette_only_when_custom_color_is_calibrated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=self.calibration(tmp)
            result=resolve_image_custom_color_workflow(
                'Microsoft Paint','microsoft-paint','Calibrated palette',render_preset='Auto',path=path)
            self.assertTrue(result['available'])
            self.assertTrue(result['auto_promoted'])
            self.assertEqual(result['workflow'],'Adaptive exact (recommended)')

    def test_manual_paint_preserves_explicit_palette_only_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=self.calibration(tmp)
            result=resolve_image_custom_color_workflow(
                'Microsoft Paint','microsoft-paint','Calibrated palette',render_preset='Manual',path=path)
            self.assertTrue(result['available'])
            self.assertFalse(result['auto_promoted'])
            self.assertEqual(result['workflow'],'Calibrated palette')

    def test_unavailable_custom_color_never_promotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=resolve_image_custom_color_workflow(
                'Microsoft Paint','microsoft-paint','Calibrated palette',render_preset='Auto',path=Path(tmp)/'missing.json')
            self.assertFalse(result['available'])
            self.assertFalse(result['auto_promoted'])

    def test_non_paint_target_is_never_auto_promoted(self):
        result=resolve_image_custom_color_workflow(
            'Gartic Phone','gartic-phone','Calibrated palette',render_preset='Auto')
        self.assertFalse(result['available'])
        self.assertFalse(result['auto_promoted'])
        self.assertEqual(result['workflow'],'Calibrated palette')

    def test_drawbot_wires_auto_custom_color_into_planning_and_preflight(self):
        source=Path('DrawBot.py').read_text(encoding='utf-8')
        self.assertGreaterEqual(source.count('resolve_image_custom_color_workflow('),2)
        self.assertIn("exact_available=bool(plan_options.get('exact_color_available'))",source)
        self.assertIn("options['custom_color_workflow']=custom_resolution['workflow']",source)


if __name__=='__main__': unittest.main()
''',encoding='utf-8')

print('PAINT_RUNTIME_PATCH=APPLIED')
