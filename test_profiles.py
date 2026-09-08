import tempfile,unittest
from pathlib import Path
from Colors import allColors,save_calibration,load_calibration,reset_palette
from DrawBot import make_test_plan
from PixelData import build_strokes
from GameProfiles import PROFILES
from PIL import Image

class Profiles(unittest.TestCase):
    def test_variable_palette_and_isolated_files(self):
        try:
            with tempfile.TemporaryDirectory() as directory:
                a=Path(directory)/'a.json';b=Path(directory)/'b.json'
                save_calibration([(1,2)],[(0,0,0)],a)
                save_calibration([(3,4),(5,6)],[(255,255,255),(255,0,0)],b)
                load_calibration(a)
                self.assertEqual(len(allColors),1)
                self.assertEqual(make_test_plan((100,100),{'delay':.01})['count'],1)
                load_calibration(b)
                self.assertEqual(len(allColors),2)
                self.assertEqual(sum(map(len,build_strokes(Image.new('RGBA',(2,2),'white')))),0)
                load_calibration(a);self.assertEqual(allColors[0].RGB,(0,0,0))
        finally:reset_palette()

    def test_games_paint_and_generic_have_distinct_storage_keys(self):
        self.assertEqual(len(PROFILES),9)
        self.assertEqual(len({v[0] for v in PROFILES.values()}),9)
