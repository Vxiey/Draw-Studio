import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageDraw

from AutoBrushWidth import resolve_brush_width
from DrawBot import DrawBotApp
from DrawTimeCalibration import correction_for,record_sample
from PaintPreparation import prepare_tool_controls


class Value:
    def __init__(self,value=''):self.value=value
    def set(self,value):self.value=value
    def get(self):return self.value


class AutoBrushAndTimerTests(unittest.TestCase):
    def test_pixel_accurate_auto_brush_is_one_pixel(self):
        im=Image.new('RGB',(1400,900),'white')
        decision=resolve_brush_width(im,target_size=(1400,900),draw_quality='Pixel Accurate',profile_key='microsoft-paint')
        self.assertEqual(decision.brush_px,1)
        self.assertEqual(decision.classification,'pixel-accurate')

    def test_flat_large_image_can_use_wider_auto_baseline(self):
        im=Image.new('RGB',(1600,1000),'white');ImageDraw.Draw(im).rectangle((100,100,1500,900),fill=(220,40,40))
        decision=resolve_brush_width(im,target_size=(1600,1000),render_preset='Extra fast',profile_key='microsoft-paint')
        self.assertGreaterEqual(decision.brush_px,3)
        self.assertLessEqual(decision.brush_px,6)

    def test_paint_preparation_passes_requested_pixel_size_to_uia(self):
        main=[dict(name='Pencil',kind='ControlType.Button',rect=[10,10,30,30],value='',label=''),
              dict(name='Size',kind='ControlType.Slider',rect=[40,40,60,200],value='',label='')]
        seen=[]
        def backend(handle,**kw):
            if kw.get('action'):seen.append((kw.get('action'),kw.get('size_px')))
            return main
        self.assertTrue(prepare_tool_controls(42,brush_px=4,backend=backend))
        self.assertIn(('size',4),seen)

    def test_timing_learning_isolated_by_render_mode(self):
        base=dict(profile_key='microsoft-paint',speed='Balanced',precision='High',use_region_fill_engine=True,
                  effective_paint_tool='Pencil',brush_px=2,custom_color_workflow='Adaptive exact (recommended)',
                  render_preset='Auto',draw_quality='High likeness',render_style='Auto')
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'timing.json'
            a=dict(base,drawing_mode='Shape paths')
            b=dict(base,drawing_mode='Smart paths')
            self.assertTrue(record_sample(a,10,14,path=db)['recorded'])
            self.assertGreater(correction_for(a,path=db)['samples'],0)
            self.assertEqual(correction_for(b,path=db)['samples'],0)

    def test_actual_draw_time_event_persists_total_label(self):
        app=SimpleNamespace(total_draw_time_text=Value(),draw_live_time_text=Value())
        DrawBotApp._handle_event(app,'draw_time_actual',{'seconds':157.2,'paths':20})
        self.assertEqual(app.total_draw_time_text.get(),'Total draw time: 2m 37s')
        self.assertIn('completed in 2m 37s',app.draw_live_time_text.get())


if __name__=='__main__':unittest.main()
