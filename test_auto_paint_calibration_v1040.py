import tempfile, unittest
from pathlib import Path
from PIL import Image, ImageDraw
from PaintAutoCalibration import layout_signature, detect_controls
from PaintTools import save_tool_calibration, load_tool_calibration, build_tool_actions
from CalibrationAnchors import make_anchor

class AutoPaintCalibrationTests(unittest.TestCase):
    def test_layout_signature(self):
        self.assertEqual(layout_signature((10,20,1010,820),120),'1000x800@120')

    def test_v3_roundtrip_auto_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tools.json'
            anchor=make_anchor((100,100,1100,900))
            save_tool_calibration({'Pencil':(300,180)},path=p,anchor=anchor,
                auto={'method':'visual-toolbar-v1','confidence':.81,'layout_signature':'1000x800@96','detected':['Pencil']})
            data=load_tool_calibration(p)
            self.assertEqual(data['version'],3)
            self.assertEqual(data['tools']['Pencil'],[300,180])
            self.assertAlmostEqual(data['auto']['confidence'],.81)
            self.assertEqual(data['auto']['detected'],['Pencil'])

    def test_v3_pencil_action_resolves_after_window_move(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tools.json'
            save_tool_calibration({'Pencil':(300,180)},path=p,anchor=make_anchor((100,100,1100,900)),
                auto={'method':'visual-toolbar-v1','confidence':.8})
            actions=build_tool_actions('Auto (recommended)',p,current_client_rect=(150,130,1150,930))
            self.assertEqual(actions,[('tool',(350,210))])

    def test_detector_rejects_blank_toolbar(self):
        img=Image.new('RGB',(1000,800),'white')
        self.assertEqual(detect_controls(img,(0,0,1000,800)),{})

if __name__=='__main__': unittest.main()
