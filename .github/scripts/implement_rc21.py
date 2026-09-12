from pathlib import Path
from textwrap import dedent


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected rc21 patch anchor missing in {path}: {old[:180]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

# Region Fill's exceptional fallback must be deterministic. If the authoritative
# ExecutionCostModel fails, never silently switch to a second learned cost model.
p=Path('RegionFillEngine.py'); text=p.read_text(encoding='utf-8')
start=text.index('def _legacy_region_cost(')
end=text.index('\n\ndef _region_cost(',start)
legacy=dedent(r'''
def _legacy_region_cost(region: dict[str, Any], options: dict[str, Any], image_size: tuple[int, int], fitted: tuple[int, int]) -> tuple[float, float]:
    """Deterministic emergency fallback with no learned timing dependency."""
    delivery = resolve_stroke_delivery(options, dry_run=False)
    speed_name = normalize_speed(options.get("speed", "Balanced"))
    delay = float(options.get("delay", 0.0) or 0.0)
    path_delay = max(float(delivery.min_path_delay), float(phase_delay(delay, speed_name, "path")))
    travel_delay = max(.002, float(phase_delay(delay, speed_name, "travel")))
    boundary_delay = max(.004, float(phase_delay(delay, speed_name, "boundary")))
    step = max(1.0, float(delivery.step_px))
    iw, ih = max(1, int(image_size[0])), max(1, int(image_size[1]))
    fw, fh = max(1, int(fitted[0])), max(1, int(fitted[1]))
    sx, sy = fw / iw, fh / ih
    stroke_cost = 0.0
    for raw in region.get("row_spans") or ():
        try:_y, left, right = map(int, raw)
        except Exception:continue
        length = max(0.0, (right-left) * sx)
        moves = max(1, int(ceil(length / step)))
        stroke_cost += travel_delay + moves*path_delay + delivery.press_settle + delivery.release_settle + boundary_delay
    perimeter = max(1.0, float(region.get("perimeter_pixels", 1) or 1))
    scaled_perimeter = perimeter * ((sx+sy)*.5)
    contour_moves = max(4, int(ceil(scaled_perimeter / step)))
    fill_cost = travel_delay + contour_moves*path_delay + delivery.press_settle + delivery.release_settle + boundary_delay
    fill_cost += max(.08, delivery.ui_control_delay*.45) + .24
    return max(.001, stroke_cost), max(.001, fill_cost)
''')
text=text[:start]+legacy+text[end:]
p.write_text(text,encoding='utf-8')

# Seal paths are real drawing operations. Cost them through the same stateful
# execution model as contours/scanlines. Keep the old deterministic formula only
# as a no-throw fallback so safety never depends on cost-model availability.
p=Path('RegionFillEngine.py'); text=p.read_text(encoding='utf-8')
start=text.index('def _seal_cost_seconds(')
end=text.index('\ndef _risk(',start)
seal=dedent(r'''
def _seal_cost_seconds(paths, options: dict[str, Any], image_size: tuple[int, int], fitted: tuple[int, int]) -> float:
    if not paths:
        return 0.0
    try:
        from ExecutionCostModel import build_cost_model
        model=build_cost_model(options,image_size,fitted)
        normalized=[]
        for raw_path in paths:
            pts=[]
            for raw in raw_path or ():
                try:pts.append((int(raw[0]),int(raw[1])))
                except Exception:continue
            if pts:normalized.append(tuple(pts))
        if normalized:
            return max(0.0,float(model.paths_seconds(normalized)))
    except Exception:
        pass
    delivery = resolve_stroke_delivery(options, dry_run=False)
    speed_name = normalize_speed(options.get("speed", "Balanced"))
    delay = float(options.get("delay", 0.0) or 0.0)
    path_delay = max(float(delivery.min_path_delay), float(phase_delay(delay, speed_name, "path")))
    travel_delay = max(.002, float(phase_delay(delay, speed_name, "travel")))
    boundary_delay = max(.004, float(phase_delay(delay, speed_name, "boundary")))
    step = max(1.0, float(delivery.step_px))
    iw, ih = max(1, int(image_size[0])), max(1, int(image_size[1]))
    fw, fh = max(1, int(fitted[0])), max(1, int(fitted[1]))
    sx, sy = fw / iw, fh / ih
    total=0.0
    for raw_path in paths:
        pts=[]
        for raw in raw_path or ():
            try:pts.append((int(raw[0]),int(raw[1])))
            except Exception:continue
        if len(pts)<2:continue
        length=sum(hypot((b[0]-a[0])*sx,(b[1]-a[1])*sy) for a,b in zip(pts,pts[1:]))
        moves=max(1,int(ceil(length/step)))
        total += travel_delay + moves*path_delay + delivery.press_settle + delivery.release_settle + boundary_delay
    return max(0.0,total)

''')
p.write_text(text[:start]+seal+text[end:],encoding='utf-8')

# General engine benchmark must measure the same model the production Pixel
# planner now uses. Sequence cost also prevents benchmark-only timing drift.
replace('benchmark_engine.py','from HybridCostModel import build_cost_model','from ExecutionCostModel import build_cost_model')
replace('benchmark_engine.py',
'''            model=build_cost_model(options);seconds=0.;cursor=None;color=None;switches=0\n            for e in plan['execution_sequence']:\n                if e['color_index']!=color:\n                    seconds+=model.color_change_seconds;switches+=1\n                seconds+=model.path_seconds(e['path'],cursor=cursor)\n                cursor=e['path'][-1];color=e['color_index']\n''',
'''            model=build_cost_model(options,image.size,image.size)\n            breakdown=model.sequence_cost(plan['execution_sequence'],initial_brush=1)\n            seconds=float(breakdown.total_seconds);switches=int(breakdown.palette_switches)\n''')

# Migrate stale integration assertions to the authoritative live model while
# retaining HybridCostModel's standalone compatibility tests elsewhere.
p=Path('test_hybrid_cost_engine_v10131.py'); raw=p.read_text(encoding='utf-8')
raw=raw.replace('from HybridCostModel import build_cost_model','from ExecutionCostModel import build_cost_model')
raw=raw.replace('m=build_cost_model(opts())',"m=build_cost_model(opts(),(32,24),(32,24))")
raw=raw.replace("self.assertIn(m.source,('conservative-default','calibrated-profile'))","self.assertIn(m.source,('deterministic profile model','measured local calibration','learning local calibration (1/3)','learning local calibration (2/3)'))")
raw=raw.replace('cost_model=build_cost_model(opts()))','cost_model=build_cost_model(opts(),(12,10),(12,10)))')
old="""    def test_region_fill_uses_shared_cost_model(self):
        text=Path('RegionFillEngine.py').read_text(encoding='utf-8');self.assertIn('from HybridCostModel import build_cost_model',text);self.assertIn('hybrid_cost_model',text)
    def test_region_fill_cold_start_preserves_legacy_cost_gate(self):
        text=Path('RegionFillEngine.py').read_text(encoding='utf-8')
        self.assertIn('if not model.calibrated:',text)
        self.assertIn('fill_cost += max(.08, delivery.ui_control_delay * .45) + .24',text)
"""
new="""    def test_region_fill_uses_shared_cost_model(self):
        text=Path('RegionFillEngine.py').read_text(encoding='utf-8')
        self.assertIn('from ExecutionCostModel import build_cost_model',text)
        self.assertNotIn('from HybridCostModel import build_cost_model',text)
    def test_region_fill_fallback_is_deterministic(self):
        text=Path('RegionFillEngine.py').read_text(encoding='utf-8')
        section=text[text.index('def _legacy_region_cost'):text.index('def _region_cost')]
        self.assertNotIn('correction_for',section);self.assertNotIn('HybridCostModel',section)
        self.assertIn('fill_cost += max(.08, delivery.ui_control_delay*.45) + .24',section)
"""
if old not in raw:raise SystemExit('stale RegionFill integration assertions not found')
raw=raw.replace(old,new)
p.write_text(raw,encoding='utf-8')

# Version / release surfaces.
replace('Version.py',"APP_VERSION = '1.0.145-rc20'","APP_VERSION = '1.0.145-rc21'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc20"','#define MyAppVersion "1.0.145-rc21"')
for test in Path('.').glob('test_*.py'):
    raw=test.read_text(encoding='utf-8')
    if '1.0.145-rc20' in raw:test.write_text(raw.replace('1.0.145-rc20','1.0.145-rc21'),encoding='utf-8')
for name in ('README.md','docs/wiki/Installation.md','docs/README.md','README-INDEX.md','docs/wiki/Home.md','docs/wiki/Updates.md'):
    p=Path(name)
    if p.exists():p.write_text(p.read_text(encoding='utf-8').replace('1.0.145-rc20','1.0.145-rc21'),encoding='utf-8')

notes='''# Image Draw Bot v1.0.145-rc21 — Complete Cost Model Unification\n\n- Remove the last live Region Fill dependency on `HybridCostModel`; the shared stateful `ExecutionCostModel` remains authoritative.\n- Cost Fill seal strokes with the same source-to-canvas execution model used for scanlines, contours, Extra Fast, Pixel Accurate and ETA.\n- Make Region Fill's emergency fallback purely deterministic and calibration-free so model failure cannot silently switch to a second learned policy.\n- Move the reproducible engine benchmark to `ExecutionCostModel.sequence_cost`.\n- Keep `HybridCostModel.py` as a compatibility module for historical tests/tools; it is no longer a live planner decision source.\n- Preserve Fill safety gates and exact Pixel Accurate geometry.\n'''
Path('RELEASE-NOTES-v1.0.145-rc21.md').write_text(notes,encoding='utf-8')
history='''# Image Draw Bot v1.0.145-rc21 — Complete Cost Model Unification\n\n- Live planner cost decisions now converge on one stateful ExecutionCostModel.\n- Fill seals and engine benchmarks use the same model; Region Fill fallback is deterministic.\n- HybridCostModel remains only for compatibility, not live planner selection.\n\n'''
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=Path(name);p.write_text(history+p.read_text(encoding='utf-8'),encoding='utf-8')

TEST=dedent(r'''\
import unittest
from pathlib import Path
from unittest.mock import patch

from RegionFillEngine import _legacy_region_cost,_seal_cost_seconds
from ExecutionCostModel import build_cost_model
from Version import APP_VERSION


def region():
    return {'color_index':1,'row_spans':[(y,2,18) for y in range(3,14)],
            'contour':[(2,3),(18,3),(18,13),(2,13),(2,3)],
            'perimeter_pixels':52,'area_pixels':187,'bbox_density':1.0,
            'fill_seal_paths':[((4,4),(4,8)),((10,5),(14,5))]}


class Rc21CostModelCleanupTests(unittest.TestCase):
    def test_region_fill_source_has_no_live_hybrid_import(self):
        src=Path('RegionFillEngine.py').read_text(encoding='utf-8')
        self.assertNotIn('from HybridCostModel import build_cost_model',src)
        self.assertIn('from ExecutionCostModel import build_cost_model',src)

    def test_legacy_fallback_is_calibration_free_and_positive(self):
        opts={'speed':'Balanced','delay':.004,'brush_px':2}
        with patch('DrawTimeCalibration.correction_for',side_effect=AssertionError('fallback must not read calibration')):
            stroke,fill=_legacy_region_cost(region(),opts,(40,30),(400,300))
        self.assertGreater(stroke,0);self.assertGreater(fill,0)

    def test_seal_cost_matches_shared_model_paths(self):
        r=region();opts={'speed':'Balanced','delay':.004,'brush_px':2,'_hybrid_scale_x':10.0,'_hybrid_scale_y':10.0}
        measured=_seal_cost_seconds(r['fill_seal_paths'],opts,(40,30),(400,300))
        model=build_cost_model(opts,(40,30),(400,300))
        expected=model.paths_seconds(r['fill_seal_paths'])
        self.assertAlmostEqual(measured,expected,places=9)

    def test_benchmark_uses_shared_sequence_cost(self):
        src=Path('benchmark_engine.py').read_text(encoding='utf-8')
        self.assertIn('from ExecutionCostModel import build_cost_model',src)
        self.assertIn('model.sequence_cost(',src)
        self.assertNotIn('from HybridCostModel import build_cost_model',src)

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc21')


if __name__=='__main__':unittest.main()
''')
Path('test_rc21_cost_model_cleanup.py').write_text(TEST,encoding='utf-8')
