import unittest
from PIL import Image,ImageDraw
from PaletteMaps import PRESETS
from BrowserAutoCalibration import _verify_gartic_grid

class GridTests(unittest.TestCase):
    def test_selected_colour_panel_cannot_replace_black_swatch(self):
        im=Image.new('RGB',(400,500),(150,20,60));d=ImageDraw.Draw(im);preset=PRESETS['gartic-phone'];matches=[]
        for i,(name,rgb) in enumerate(zip(preset.names,preset.colors)):
            x=40+(i%6)*20;y=50+(i//6)*20;d.rectangle((x-8,y-8,x+8,y+8),fill=rgb)
            matches.append((name,(x,y),rgb,0))
        d.rectangle((20,350,150,420),fill='black');matches[0]=(matches[0][0],(85,385),(0,0,0),0)
        verified=_verify_gartic_grid(im,matches,preset,(0,0))
        self.assertEqual(len(verified),72);self.assertEqual(verified[0][1],(40,50))
    def test_grid_verification_does_not_invent_missing_colours(self):
        im=Image.new('RGB',(400,500),(150,20,60));preset=PRESETS['gartic-phone'];matches=[]
        for i,(name,rgb) in enumerate(zip(preset.names,preset.colors)):
            matches.append((name,(40+(i%6)*20,50+(i//6)*20),rgb,0))
        with self.assertRaises(ValueError):_verify_gartic_grid(im,matches,preset,(0,0))
