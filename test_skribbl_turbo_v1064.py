import unittest
from SkribblFastRenderer import optimize_skribbl_groups


class SkribblTurboRendererTests(unittest.TestCase):
    def test_reduces_active_colors_and_remaps_geometry(self):
        palette = [(0,0,0),(255,0,0),(0,255,0),(0,0,255),(255,255,0),(255,0,255),(0,255,255),(255,255,255)]
        groups = [[(0,i,5,i)] for i in range(7)] + [[]]
        out, meta = optimize_skribbl_groups(groups, palette, max_colors=4)
        self.assertLessEqual(sum(bool(g) for g in out), 4)
        self.assertGreater(meta['remapped_colors'], 0)
        self.assertEqual(meta['active_colors_before'], 7)

    def test_coalesces_adjacent_runs_after_palette_reduction(self):
        palette = [(0,0,0),(5,5,5),(255,255,255)]
        groups = [[(0,0,3,0)],[(5,0,8,0)],[]]
        out, meta = optimize_skribbl_groups(groups, palette, max_colors=2, gap_join=1)
        # Both dark colours remain or merge safely, and run count cannot grow.
        self.assertLessEqual(sum(len(g) for g in out), 2)
        self.assertLessEqual(meta['runs_after'], meta['runs_before'])

    def test_keeps_dark_structure(self):
        palette = [(0,0,0),(200,20,20),(20,200,20),(20,20,200),(255,255,255)]
        groups = [[(1,1,1,1)],[(0,2,20,2)],[(0,3,19,3)],[(0,4,18,4)],[]]
        out, meta = optimize_skribbl_groups(groups, palette, max_colors=2)
        self.assertTrue(out[0])
        self.assertEqual(meta['darkest_color_index'], 0)


if __name__ == '__main__':
    unittest.main()
