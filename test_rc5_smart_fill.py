import unittest
from pathlib import Path
from RegionFillEngine import _diagonal_seal_paths, _span_contains, _region_cost_components, evaluate_region_candidates


class Rc5SmartFillTests(unittest.TestCase):
    def region(self):
        return {
            "color_index": 1,
            "row_spans": [(0, 1, 3), (1, 1, 4), (2, 1, 4), (3, 1, 4)],
            "contour": [(1, 0), (3, 0), (4, 1), (4, 3), (1, 3), (1, 0)],
            "seed_pixel": (2, 2),
            "guard_pixels": [(0, 2), (5, 2)],
            "area_pixels": 15,
            "safety_score": .99,
            "bbox_density": .94,
            "perimeter_pixels": 14,
        }

    def test_diagonal_seals_never_leave_component(self):
        r = self.region()
        paths, total, unresolved = _diagonal_seal_paths(r)
        self.assertGreaterEqual(total, 1)
        self.assertEqual(unresolved, 0)
        self.assertTrue(paths)
        for path in paths:
            for x, y in path:
                self.assertTrue(_span_contains(r, x, y), (x, y))

    def test_seal_cost_is_charged(self):
        r = self.region()
        base = dict(r)
        sealed = dict(r, fill_seal_paths=[((3, 0), (3, 1))])
        opts = {"speed": "Balanced", "delay": .003, "brush_px": 2}
        a = _region_cost_components(base, opts, (20, 20), (200, 200))
        b = _region_cost_components(sealed, opts, (20, 20), (200, 200))
        self.assertGreater(b[1], a[1])
        self.assertGreater(b[2], a[2])

    def test_hard_thin_neck_is_not_overridden(self):
        r = {
            "color_index": 1,
            "row_spans": [(y, 5, 5) for y in range(8)],
            "contour": [(5, 0), (5, 1), (5, 7), (5, 6), (5, 0)],
            "seed_pixel": (5, 3),
            "guard_pixels": [(3, 3), (7, 3)],
            "area_pixels": 8,
            "safety_score": .99,
            "bbox_density": 1.0,
            "perimeter_pixels": 16,
        }
        accepted, meta = evaluate_region_candidates(
            [r], (20, 20), (200, 200),
            {"speed": "Fast", "brush_px": 4, "fill_aggressiveness": "Aggressive", "fill_tool_available": True},
        )
        self.assertEqual(accepted, [])
        self.assertGreaterEqual(meta["rejected_by_safety"], 1)

    def test_runtime_executes_seals_before_contour(self):
        src = Path("DrawBot.py").read_text(encoding="utf-8")
        seal = src.index("for _seal_path in region.get('fill_seal_paths'")
        contour = src.index("contour=region.get('contour')", seal)
        self.assertLess(seal, contour)


if __name__ == "__main__":
    unittest.main()
