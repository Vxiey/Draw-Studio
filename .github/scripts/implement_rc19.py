from pathlib import Path
from textwrap import dedent


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected rc19 patch anchor missing in {path}: {old[:180]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

# Extend the single stateful execution model with the small compatibility surface
# used by the existing ExtraFast2 / telemetry callers. The implementation still
# delegates every real path cost to path_cost(), so this is not a second model.
p=Path('ExecutionCostModel.py')
text=p.read_text(encoding='utf-8')
if 'EXECUTION_MODEL_VERSION = 3' not in text:
    text=text.replace('Point = tuple[int, int]\n', 'Point = tuple[int, int]\nEXECUTION_MODEL_VERSION = 3\n', 1)
text=text.replace(
'''        self.sx = self.fitted_size[0] / self.source_size[0]\n        self.sy = self.fitted_size[1] / self.source_size[1]\n''',
'''        _sx_default = self.fitted_size[0] / self.source_size[0]\n        _sy_default = self.fitted_size[1] / self.source_size[1]\n        self.sx = max(.001, _safe_float(self.options.get("_execution_scale_x", self.options.get("_hybrid_scale_x", _sx_default)), _sx_default))\n        self.sy = max(.001, _safe_float(self.options.get("_execution_scale_y", self.options.get("_hybrid_scale_y", _sy_default)), _sy_default))\n''',1)
anchor='''    def path_cost(self, path: Sequence[Point], *, cursor: Point | None = None,\n'''
compat=dedent(r'''
    @property
    def scale_x(self) -> float:
        return float(self.sx)

    @property
    def scale_y(self) -> float:
        return float(self.sy)

    @property
    def path_fixed_seconds(self) -> float:
        base=(self.travel_wait + float(self.delivery.press_settle) +
              float(self.delivery.release_settle) + self.boundary_wait + .0015)
        return max(.000001,base*self.multiplier)

    @property
    def learned_path_floor_seconds(self) -> float:
        values=[]
        for kind in ("short_stroke","long_stroke","stroke","path"):
            value=self._learned_average(kind,0.0)
            if value>0:values.append(float(value))
        return max(0.0,min(values)*self.multiplier) if values else 0.0

    @property
    def draw_seconds_per_px(self) -> float:
        return max(1e-12,(self.path_wait/max(.5,float(self.delivery.step_px)))*self.multiplier)

    @property
    def color_change_seconds(self) -> float:
        return float(self.switch_cost("palette_change"))

    @property
    def model_version(self) -> int:
        return EXECUTION_MODEL_VERSION

    @property
    def calibration_confidence(self) -> float:
        if self.samples<=0:return 0.0
        return max(0.0,min(.95,1.0-math.exp(-float(self.samples)/4.0)))

    @property
    def uncertainty_multiplier(self) -> float:
        if self.samples<=0:return 1.0
        return 1.0+(1.0-self.calibration_confidence)*.10

    def path_seconds(self,path: Sequence[Point],*,cursor: Point|None=None,brush_px: int|None=None) -> float:
        return float(self.path_cost(path,cursor=cursor,brush_px=brush_px).total_seconds)

    def paths_seconds(self,paths: Iterable[Path],*,cursor: Point|None=None,brush_px: int|None=None) -> float:
        total=0.0;current=cursor
        for path in paths or ():
            if not path:continue
            total+=self.path_seconds(path,cursor=current,brush_px=brush_px)
            current=tuple(map(int,path[-1]))
        return total

    def risk_adjusted_seconds(self,seconds: float) -> float:
        value=max(0.0,float(seconds or 0.0))
        return value*self.uncertainty_multiplier

    def as_dict(self) -> dict[str,Any]:
        return {
            "model":"ExecutionCostModel","model_version":self.model_version,"source":self.source,
            "samples":self.samples,"scale_x":round(self.scale_x,7),"scale_y":round(self.scale_y,7),
            "path_fixed_seconds":round(self.path_fixed_seconds,7),
            "draw_seconds_per_px":round(self.draw_seconds_per_px,9),
            "color_change_seconds":round(self.color_change_seconds,7),
            "calibration_confidence":round(self.calibration_confidence,7),
            "uncertainty_multiplier":round(self.uncertainty_multiplier,7),
        }

''')
if 'def paths_seconds(self,paths: Iterable[Path]' not in text:
    if anchor not in text:raise SystemExit('ExecutionCostModel path_cost anchor missing')
    text=text.replace(anchor,compat+anchor,1)
p.write_text(text,encoding='utf-8')

# ExtraFast2 now selects path limits/reorientation with the same stateful model
# used by AdaptiveRegionHybrid and the visible ETA. DrawBot already injects the
# exact source->fitted scale into _hybrid_scale_x/_hybrid_scale_y.
replace('ExtraFast2.py','HybridCostModel execution cost after that ordering.','ExecutionCostModel execution cost after that ordering.')
replace('ExtraFast2.py',
'''    from ContinuousPaths import build_execution_paths, execution_groups_with_portrait_semantics\n    from HybridCostModel import build_cost_model\n''',
'''    from ContinuousPaths import build_execution_paths, execution_groups_with_portrait_semantics\n    from ExecutionCostModel import build_cost_model\n''')
replace('ExtraFast2.py','''    model = build_cost_model(options)\n''','''    # The DrawBot call supplies exact source->target scale overrides. Direct\n    # tests/benchmarks intentionally default to source-space 1:1.\n    model = build_cost_model(options,(1,1),(1,1))\n''')
replace('ExtraFast2.py',
'''        cost_scope=(\n            'post-target-cap + current StrokeOptimizer; intra-color travel + color selection; '\n            'constant fill/tool/verification terms cancel between path candidates'\n''',
'''        execution_cost_model='ExecutionCostModel stateful v3',\n        execution_scale=[round(float(getattr(model,'scale_x',1.0)),6),round(float(getattr(model,'scale_y',1.0)),6)],\n        cost_scope=(\n            'post-target-cap + current StrokeOptimizer through ExecutionCostModel; intra-color travel + color selection; '\n            'constant fill/tool/verification terms cancel between path candidates'\n''')

# Keep the synthetic Extra Fast benchmark on the same cost model as production.
replace('benchmark_extra_fast.py','from HybridCostModel import build_cost_model','from ExecutionCostModel import build_cost_model')
replace('benchmark_extra_fast.py','''    model = build_cost_model(options)\n''','''    model = build_cost_model(options,(320,320),(320,320))\n''')
replace('ExecutionTelemetry.py','This module measures geometry and HybridCostModel estimates without changing','This module measures geometry and shared execution-cost estimates without changing')

# Migrate the one ExtraFast-specific legacy mock to the authoritative model.
p=Path('test_extra_fast_review.py'); raw=p.read_text(encoding='utf-8')
raw=raw.replace("patch('HybridCostModel.build_cost_model',return_value=Model())","patch('ExecutionCostModel.build_cost_model',return_value=Model())")
p.write_text(raw,encoding='utf-8')

# Version / release surfaces.
replace('Version.py',"APP_VERSION = '1.0.145-rc18'","APP_VERSION = '1.0.145-rc19'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc18"','#define MyAppVersion "1.0.145-rc19"')
for test in Path('.').glob('test_*.py'):
    raw=test.read_text(encoding='utf-8')
    if '1.0.145-rc18' in raw:test.write_text(raw.replace('1.0.145-rc18','1.0.145-rc19'),encoding='utf-8')
for name in ('README.md','docs/wiki/Installation.md','docs/README.md','README-INDEX.md','docs/wiki/Home.md','docs/wiki/Updates.md'):
    p=Path(name)
    if p.exists():p.write_text(p.read_text(encoding='utf-8').replace('1.0.145-rc18','1.0.145-rc19'),encoding='utf-8')

notes='''# Image Draw Bot v1.0.145-rc19 — Extra Fast Unified Execution Cost\n\n- Move Extra Fast 2.0 path-limit, axis-reorientation and downstream regression decisions from `HybridCostModel` to the shared stateful `ExecutionCostModel`.\n- Reuse the exact source-to-canvas scale already supplied by DrawBot, so candidate costs match real canvas motion rather than source-space stroke count.\n- Add a compatibility surface (`path_seconds`, `paths_seconds`, scale and path coefficients) to `ExecutionCostModel` without introducing a second timing implementation.\n- Keep Extra Fast's complete baseline fallback: a proposal is accepted only when the downstream capped/ordered plan is no slower than baseline.\n- Move the Extra Fast synthetic benchmark and execution telemetry onto the same shared cost model.\n- Preserve all lossless overlap-only connector and raster-identity guarantees.\n'''
Path('RELEASE-NOTES-v1.0.145-rc19.md').write_text(notes,encoding='utf-8')
history='''# Image Draw Bot v1.0.145-rc19 — Extra Fast Unified Execution Cost\n\n- Extra Fast 2.0 now uses the same stateful execution-time model as Adaptive Hybrid, Region Fill and visible ETA.\n- Source-to-canvas scale participates in path-limit and reorientation decisions.\n- Complete downstream baseline fallback remains authoritative.\n\n'''
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=Path(name);p.write_text(history+p.read_text(encoding='utf-8'),encoding='utf-8')

TEST=dedent(r'''\
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from ExecutionCostModel import build_cost_model,EXECUTION_MODEL_VERSION
from ExtraFast2 import build_fast_paths
from Version import APP_VERSION


class Rc19ExtraFastExecutionCostTests(unittest.TestCase):
    def test_scale_override_is_authoritative(self):
        model=build_cost_model({'_hybrid_scale_x':4.0,'_hybrid_scale_y':2.5,'delay':.004},(1,1),(1,1))
        self.assertAlmostEqual(model.scale_x,4.0);self.assertAlmostEqual(model.scale_y,2.5)
        self.assertEqual(model.model_version,EXECUTION_MODEL_VERSION)

    def test_compatibility_api_delegates_to_stateful_path_cost(self):
        model=build_cost_model({'delay':.004,'brush_px':2},(100,100),(500,500))
        paths=[((0,0),(20,0)),((20,0),(20,20))]
        stateful=model.paths_seconds(paths)
        manual=model.path_seconds(paths[0])+model.path_seconds(paths[1],cursor=paths[0][-1])
        self.assertAlmostEqual(stateful,manual,places=9)
        self.assertGreater(model.draw_seconds_per_px,0);self.assertGreater(model.path_fixed_seconds,0)
        self.assertEqual(model.as_dict()['model'],'ExecutionCostModel')

    def test_extra_fast_reports_shared_model_and_scale(self):
        group=[(x,2,x,60) for x in range(2,60)]
        paths,meta=build_fast_paths([group],{'_hybrid_scale_x':3.0,'_hybrid_scale_y':2.0})
        self.assertTrue(paths[0]);self.assertEqual(meta['execution_cost_model'],'ExecutionCostModel stateful v3')
        self.assertEqual(meta['execution_scale'],[3.0,2.0])
        self.assertLessEqual(meta['ordered_cost_after_seconds'],meta['ordered_cost_before_seconds']+1e-9)

    def test_downstream_guard_still_rejects_slower_candidate(self):
        group=[(10,y,390,y) for y in range(10,350)]
        row={'target_cap_applied':False,'stroke_optimizer_effective':'Travel only'}
        with patch('ExtraFast2._downstream_plan_cost',side_effect=[(1.0,row),(2.0,row)]):
            _paths,meta=build_fast_paths([group],{})
        self.assertFalse(meta['downstream_plan_accepted'])
        self.assertEqual(meta['ordered_cost_after_seconds'],meta['ordered_cost_before_seconds'])

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc19')


if __name__=='__main__':unittest.main()
''')
Path('test_rc19_extra_fast_execution_cost.py').write_text(TEST,encoding='utf-8')
