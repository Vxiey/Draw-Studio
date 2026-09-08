import tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
from PaintFullCalibration import detect_setup,save_setup,choose_paint_window
from PaintTools import build_tool_actions,load_tool_calibration

class PaintFullTests(unittest.TestCase):
    def screenshot(self):
        im=Image.new('RGB',(1920,1048),(241,243,245))
        with Image.open(Path(__file__).parent/'tests/fixtures/paint-light-ribbon.png') as ribbon:im.paste(ribbon,(0,60))
        ImageDraw.Draw(im).rectangle((75,225,1844,995),fill='white')
        return im

    def test_detect_and_screen_offsets(self):
        r=detect_setup(self.screenshot(),(-1920,40))
        self.assertEqual(r['palette_count'],20)
        self.assertEqual(len(set(r['rgbs'])),20)
        self.assertEqual(r['tools']['Fill'],(-1612,128))
        self.assertEqual(r['canvas_box'],(-1843,267,-77,1034))

    def test_scaled_reference(self):
        im=self.screenshot()
        for scale in (.8,1.25,1.5,2):
            r=detect_setup(im.resize((round(im.width*scale),round(im.height*scale))))
            self.assertEqual(r['palette_count'],20)
            self.assertAlmostEqual(r['tools']['Fill'][0],308*scale,delta=5)

    def test_blank_and_wrong_icons_rejected(self):
        with self.assertRaises(ValueError):detect_setup(Image.new('RGB',(1000,800),'white'))
        im=self.screenshot();ImageDraw.Draw(im).rectangle((250,70,326,146),fill=(248,249,250))
        with self.assertRaises(ValueError):detect_setup(im)

    def test_covered_palette_and_canvas_rejected(self):
        im=self.screenshot();ImageDraw.Draw(im).rectangle((825,70,875,120),fill=(240,240,240))
        with self.assertRaises(ValueError):detect_setup(im)
        im=self.screenshot();ImageDraw.Draw(im).rectangle((500,500,900,750),fill='black')
        with self.assertRaises(ValueError):detect_setup(im)

    def test_calibration_builds_real_fill_and_pencil_actions(self):
        im=self.screenshot();r=detect_setup(im)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rect=(0,0,*im.size)
            save_setup(r,{'client_rect':rect},root/'colors.json',root/'tools.json')
            self.assertEqual(build_tool_actions('Auto (recommended)',root/'tools.json',current_client_rect=rect),[('tool',r['tools']['Pencil'])])
            self.assertEqual(build_tool_actions('Fill',root/'tools.json',current_client_rect=rect),[('tool',r['tools']['Fill'])])
            self.assertEqual(set(load_tool_calibration(root/'tools.json')['tools']),{'Pencil','Fill','Eraser'})

    def test_cancel_and_unique_window(self):
        with self.assertRaises(InterruptedError):detect_setup(self.screenshot(),cancelled=lambda:True)
        paint={'title':'Namnlös - Paint','handle':7}
        self.assertEqual(choose_paint_window([{'title':'Draw Studio'},paint]),paint)
        for windows in ([],[paint,dict(paint,handle=8)]):
            with self.assertRaises(ValueError):choose_paint_window(windows)
