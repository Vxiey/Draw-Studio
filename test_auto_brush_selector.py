import unittest

from AdaptiveBrushEngine import analyze_brush_demand, assign_adaptive_brushes, verified_brush_sizes


def brush_plan(*, safe_guard=8):
    return {
        'profile_key':'gartic-phone',
        'nominal_sizes':[2,4,8,16,28],
        'control_positions':[[10,10],[20,10],[30,10],[40,10],[50,10]],
        'target_position':[20,10],
        'confidence':.95,
        'effective_px':4,
        'safe_guard_px':safe_guard,
    }


def entry(phase='fill', *, protected=False, importance=.2, path=((1,1),(8,1)), w=20, h=20, area=None):
    return {
        'color_index':2,
        'path':path,
        'phase':phase,
        'protected':protected,
        'importance':importance,
        'component_width':w,
        'component_height':h,
        'component_area':w*h if area is None else area,
        'serial':0,
    }


class AutoBrushSelectorTests(unittest.TestCase):
    def test_verified_sizes_can_use_only_canvas_guard_safe_presets(self):
        sizes,ok=verified_brush_sizes('gartic-phone',brush_plan(safe_guard=8),4)
        self.assertTrue(ok)
        self.assertEqual(sizes,(2,4,8))
        sizes,_=verified_brush_sizes('gartic-phone',brush_plan(safe_guard=4),4)
        self.assertEqual(sizes,(2,4))

    def test_flat_image_plan_uses_broader_verified_brush(self):
        sequence=[entry('foundation',w=80,h=60,area=4800) for _ in range(8)]
        sequence += [entry('structure',w=30,h=20,importance=.2) for _ in range(2)]
        result=assign_adaptive_brushes(sequence,profile_key='gartic-phone',default_brush_px=4,
                                       browser_brush_plan=brush_plan(safe_guard=8))
        meta=result['metadata']
        self.assertEqual(meta['image_brush_demand']['classification'],'flat-shape')
        self.assertEqual(meta['default_brush_px'],8)
        self.assertTrue(meta['automatic_image_brush_selection'])
        self.assertTrue(all(item['brush_px']<=8 for item in result['execution_sequence']))

    def test_detail_heavy_image_plan_downshifts_and_protects_details(self):
        sequence=[entry('fine_detail',protected=True,importance=.9,w=2,h=3,
                        path=((1,1),(2,1),(2,2),(3,2))) for _ in range(8)]
        sequence += [entry('fill',w=30,h=30,area=900) for _ in range(2)]
        result=assign_adaptive_brushes(sequence,profile_key='gartic-phone',default_brush_px=4,
                                       browser_brush_plan=brush_plan(safe_guard=8))
        meta=result['metadata']
        self.assertEqual(meta['image_brush_demand']['classification'],'detail-heavy')
        self.assertEqual(meta['default_brush_px'],2)
        self.assertTrue(all(item['brush_px']==2 for item in result['execution_sequence'][:8]))

    def test_unverified_target_stays_fixed_and_does_not_invent_clicks(self):
        plan=brush_plan(safe_guard=16)
        plan['target_position']=None
        plan['confidence']=.1
        result=assign_adaptive_brushes([entry('foundation'),entry('fine_detail')],
                                       profile_key='gartic-phone',default_brush_px=4,
                                       browser_brush_plan=plan)
        self.assertFalse(result['metadata']['dynamic_brush_enabled'])
        self.assertEqual([item['brush_px'] for item in result['execution_sequence']],[4,4])

    def test_analysis_is_deterministic_and_metadata_only(self):
        sequence=[entry('fine_detail',importance=.7,w=3,h=4),entry('foundation',w=40,h=40,area=1600)]
        first=analyze_brush_demand(sequence)
        second=analyze_brush_demand(sequence)
        self.assertEqual(first,second)
        self.assertIn(first['classification'],('detail-heavy','balanced','flat-shape'))
        self.assertNotIn('pixels',first)


if __name__=='__main__':
    unittest.main()
