import unittest
from PIL import Image, ImageDraw

from BrowserBrushSize import plan_browser_brush_size
from BrowserAutoCalibration import _row_cluster
from Version import APP_VERSION, FILE_VERSION


class AutomaticBrushSizeV1074Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(APP_VERSION,'1.0.145-rc9')
        self.assertEqual(FILE_VERSION,'1.0.145')

    def _gartic_image(self):
        size=(1000,700);client=(0,0,*size);canvas=(200,140,800,500)
        image=Image.new('RGB',size,(245,245,245));draw=ImageDraw.Draw(image)
        y=500+max(28,min(int(700*.095),int(360*.17)))
        xs=[200+600*f for f in (.05,.118,.186,.254,.322)]
        for i,x in enumerate(xs):
            r=11+i*2
            draw.ellipse((x-r,y-r,x+r,y+r),fill=(90,90,90),outline=(255,255,255) if i==1 else (30,30,30),width=3)
        return image,client,canvas

    def test_gartic_detects_target_and_selected_size(self):
        image,client,canvas=self._gartic_image()
        plan=plan_browser_brush_size('gartic-phone',image,client,canvas_box=canvas,requested_px=4)
        self.assertGreater(plan.confidence,.58)
        self.assertIsNotNone(plan.target_position)
        self.assertEqual(plan.target_index,1)
        self.assertEqual(plan.effective_px,4)

    def test_low_confidence_never_invents_click(self):
        image=Image.new('RGB',(900,650),(240,240,240))
        plan=plan_browser_brush_size('gartic-phone',image,(0,0,900,650),canvas_box=(180,120,720,470),requested_px=8)
        self.assertIsNone(plan.target_position)
        self.assertGreaterEqual(plan.safe_guard_px,12)

    def test_control_position_can_never_be_inside_canvas(self):
        image=Image.new('RGB',(700,500),(245,245,245));draw=ImageDraw.Draw(image)
        # Canvas intentionally reaches the bottom, forcing generated toolbar
        # positions to clamp into/near the canvas. Even strong visual circles
        # there must never become a click target.
        canvas=(100,80,650,495)
        y=499
        for x in (128,165,202,240,277):
            draw.ellipse((x-12,y-12,x+12,y+12),fill=(60,60,60),outline=(255,255,255),width=2)
        plan=plan_browser_brush_size('gartic-phone',image,(0,0,700,500),canvas_box=canvas,requested_px=4)
        self.assertIsNone(plan.target_position)
        self.assertGreaterEqual(plan.safe_guard_px,12)

    def test_sketchheads_palette_row_rejects_brush_and_distant_icons(self):
        positions=[(348,662),(369,662),(400,662)] + [(452+i*29,662) for i in range(10)] + [(943,644),(1165,634)]
        rgbs=[(180,180,180),(70,70,70),(190,190,190)] + [(20+i*17,40+i*9,60+i*7) for i in range(10)] + [(245,214,103),(255,252,255)]
        row=_row_cluster(positions,rgbs,image_width=1260,image_height=700)
        self.assertGreaterEqual(len(row),9)
        self.assertGreaterEqual(row[0][0],440)
        self.assertLess(row[-1][0],800)


if __name__=='__main__': unittest.main()
