from pathlib import Path
p=Path('test_rc20_pixel_execution_cost.py')
text=p.read_text(encoding='utf-8')
old="""        self.assertTrue(np.array_equal(result.covered_mask,target))
        self.assertEqual(int(result.error_pixels),0)
"""
new="""        self.assertTrue(np.array_equal(result.coverage_count>0,target))
        self.assertEqual(int(result.metrics['error_pixels']),0)
"""
if old not in text:
    raise SystemExit('rc20 coverage-test migration anchor missing')
p.write_text(text.replace(old,new,1),encoding='utf-8')
