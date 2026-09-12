import unittest
from pathlib import Path
from AdaptiveBrushEngine import verified_brush_sizes, assign_adaptive_brushes
from CanvasGuard import CanvasGuard, FinalMouseGuard

class Mouse:
    def move(self,*a): pass
    def press(self): pass
    def click(self): pass
    def release(self): pass

class Rc4Tests(unittest.TestCase):
    def plan(self):
        return {"nominal_sizes":[2,4,8,16,28],"verified_sizes":[2,4,8,16,28],"control_positions":[[1,1],[2,1],[3,1],[4,1],[5,1]],"target_position":[2,1],"confidence":.9,"safe_guard_px":8}
    def test_full_verified_ladder_ignores_legacy_guard(self):
        sizes,dynamic=verified_brush_sizes('gartic-phone',self.plan(),4)
        self.assertTrue(dynamic);self.assertEqual(sizes,(2,4,8,16,28))
    def test_legacy_plan_still_obeys_guard(self):
        p=self.plan();p.pop('verified_sizes')
        sizes,dynamic=verified_brush_sizes('gartic-phone',p,4)
        self.assertTrue(dynamic);self.assertEqual(sizes,(2,4,8))
    def test_large_foundation_can_reach_28(self):
        e={"color_index":0,"path":((10,10),(190,10)),"phase":"foundation","protected":False,"importance":.1,"component_width":200,"component_height":120,"component_area":24000}
        r=assign_adaptive_brushes([e,e,e],profile_key='gartic-phone',default_brush_px=4,browser_brush_plan=self.plan())
        self.assertIn(28,r['metadata']['used_brush_sizes'])
    def test_final_mouse_guard_can_swap_inset(self):
        fg=FinalMouseGuard(Mouse(),CanvasGuard.from_area((0,0,200,200),brush_px=2))
        fg.set_canvas_guard(CanvasGuard.from_area((0,0,200,200),brush_px=28))
        self.assertEqual(fg.canvas_guard.model.brush_inset.brush_px,28)
    def test_drawbot_uses_brush_specific_guard(self):
        src=Path('DrawBot.py').read_text(encoding='utf-8')
        self.assertIn('draw_mouse.set_canvas_guard(canvas_guard)',src)
        self.assertIn("brush_plan.get('verified_sizes')",src)

if __name__=='__main__':unittest.main()
