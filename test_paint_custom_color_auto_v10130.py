import tempfile
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
