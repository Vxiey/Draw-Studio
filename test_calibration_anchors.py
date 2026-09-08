import tempfile
import unittest
from pathlib import Path

from CalibrationAnchors import make_anchor, resolve_point, resolve_points
from Colors import save_calibration, load_calibration, allColors, reset_palette


class CalibrationAnchorTests(unittest.TestCase):
    def tearDown(self):
        reset_palette()

    def test_translation_rebases_points(self):
        anchor=make_anchor((10,20,1010,720))
        self.assertEqual(resolve_point((100,80),anchor,(30,40,1030,740)),(120,100))
        self.assertEqual(resolve_points([(100,80),(200,90)],anchor,(30,40,1030,740)),[(120,100),(220,110)])

    def test_resize_is_rejected(self):
        anchor=make_anchor((10,20,1010,720))
        with self.assertRaisesRegex(ValueError,'layout changed size'):
            resolve_point((100,80),anchor,(10,20,1210,820))

    def test_palette_load_translates_without_changing_rgb(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'calibration.json'
            save_calibration([(100,80),(200,90)],[(1,2,3),(4,5,6)],path,
                             anchor=make_anchor((10,20,1010,720)))
            reset_palette();load_calibration(path,current_client_rect=(30,40,1030,740),require_anchor=True)
            self.assertEqual([(c.x,c.y,c.RGB) for c in allColors],[(120,100,(1,2,3)),(220,110,(4,5,6))])

    def test_legacy_palette_is_rejected_when_anchor_required(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'calibration.json'
            path.write_text(json.dumps({'version':3,'colors':[{'name':'A','position':[100,80],'rgb':[1,2,3]}]}),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'fixed screen coordinates'):
                load_calibration(path,current_client_rect=(0,0,1000,700),require_anchor=True)


if __name__=='__main__':unittest.main()
