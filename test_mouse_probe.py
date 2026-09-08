import unittest
from MouseProbe import probe_points, run_probe


class FakeStop:
    def is_set(self): return False
    def wait(self, seconds): return False


class FakeMouse:
    def __init__(self): self.pos=(0,0); self.moves=[]
    def get_position(self): return self.pos
    def move(self,x,y): self.pos=(x,y); self.moves.append((x,y))
    def diagnostics(self): return {'ok':'fake'}


class FakeMonitor:
    def activate(self,target): return True
    def active(self,target): return True
    def verify(self,target,point): return None


class MouseProbeTests(unittest.TestCase):
    def test_points_stay_inside_area(self):
        area=(100,200,20,12)
        for x,y in probe_points(area):
            self.assertTrue(100 <= x < 120)
            self.assertTrue(200 <= y < 212)

    def test_probe_moves_without_click_api(self):
        mouse=FakeMouse(); monitor=FakeMonitor(); stop=FakeStop()
        result=run_probe((123,(0,0,500,500)),(100,100,80,60),mouse=mouse,monitor=monitor,stop=stop,wait=lambda s:None)
        self.assertTrue(result['ok'])
        self.assertEqual(len(mouse.moves),3)
        self.assertEqual(mouse.moves[0],mouse.moves[-1])
        self.assertEqual(result['diagnostics'],{'ok':'fake'})

    def test_tiny_area_rejected(self):
        with self.assertRaises(ValueError):probe_points((0,0,9,20))


if __name__=='__main__':unittest.main()
