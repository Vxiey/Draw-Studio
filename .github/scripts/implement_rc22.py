from pathlib import Path
from textwrap import dedent


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected rc22 patch anchor missing in {path}: {old[:180]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')

# Learned operation averages describe the path operation at its nominal travel
# baseline. They must not erase the dynamic distance from the current cursor.
replace('ExecutionCostModel.py','EXECUTION_MODEL_VERSION = 3','EXECUTION_MODEL_VERSION = 4')
replace('ExecutionCostModel.py',
'''    def _learned_average(self, kind: str, fallback: float) -> float:\n        item = self.runtime.get(str(kind))\n        if not isinstance(item, dict):\n            return fallback\n        avg = _safe_float(item.get("average_seconds"), 0.0)\n        return avg if avg > 0.0 else fallback\n''',
'''    def _learned_average(self, kind: str, fallback: float) -> float:\n        aliases = {\n            "dot": ("dot", "point"),\n            "short_stroke": ("short_stroke", "stroke", "path", "drag"),\n            "long_stroke": ("long_stroke", "stroke", "path", "drag"),\n            "outline": ("outline", "stroke", "path", "drag"),\n            "palette_change": ("palette_change", "color_change"),\n            "tool_change": ("tool_change",),\n            "brush_change": ("brush_change", "tool_change"),\n            "fill": ("fill", "fill_action", "bucket_fill"),\n            "verification": ("verification", "visual_verify"),\n        }\n        for name in aliases.get(str(kind),(str(kind),)):\n            item = self.runtime.get(name)\n            if not isinstance(item, dict):\n                continue\n            avg = _safe_float(item.get("average_seconds"), 0.0)\n            if avg <= 0.0:\n                count=max(0,int(item.get("count") or item.get("observations") or 0))\n                total=max(0.0,_safe_float(item.get("total_seconds"),0.0))\n                avg=total/count if count else 0.0\n            if avg > 0.0:\n                return avg\n        return fallback\n''')

p=Path('ExecutionCostModel.py'); text=p.read_text(encoding='utf-8')
start=text.index('    def path_cost(self, path: Sequence[Point], *, cursor: Point | None = None,')
end=text.index('\n    def switch_cost(',start)
new_path=dedent(r'''
    def path_cost(self, path: Sequence[Point], *, cursor: Point | None = None,
                  brush_px: int | None = None) -> CostBreakdown:
        path = tuple((int(p[0]), int(p[1])) for p in (path or ()))
        if not path:
            return CostBreakdown(0.0, source=self.source)
        _brush = max(1, int(brush_px or self.options.get("brush_px") or 1))
        length = _path_length(path, self.sx, self.sy)
        start = path[0]
        travel_px = 0.0
        if cursor is not None:
            travel_px = math.hypot((start[0]-cursor[0])*self.sx,
                                   (start[1]-cursor[1])*self.sy)
        # Keep the historic bounded distance curve, but never hide it inside a
        # learned operation average. A learned average is the zero-distance /
        # nominal-travel baseline; actual cursor distance is added afterwards.
        travel_base = self.travel_wait
        travel_distance = min(.10, travel_px * .000045)
        press_release = float(self.delivery.press_settle + self.delivery.release_settle)

        if len(path) <= 1:
            body = press_release + max(.012, self.boundary_wait)
            learned = self._learned_average("dot", 0.0)
            if learned > 0.0:
                learned_body=max(.001,learned-travel_base)
                total=travel_base+travel_distance+learned_body
                body_scale=learned_body/max(.000001,body)
                travel_seconds=travel_base+travel_distance
            else:
                total=(travel_base+travel_distance+body)*self.multiplier
                body_scale=self.multiplier
                travel_seconds=(travel_base+travel_distance)*self.multiplier
            return CostBreakdown(total, travel_seconds=travel_seconds,
                                 press_release_seconds=press_release*body_scale,
                                 target_processing_seconds=max(.012,self.boundary_wait)*body_scale,
                                 operations=1, moves=1, source=self.source)

        moves = 0
        for a, b in zip(path, path[1:]):
            seg = math.hypot((b[0]-a[0])*self.sx, (b[1]-a[1])*self.sy)
            if seg > 0:
                moves += max(1, int(math.ceil(seg / max(.5, float(self.delivery.step_px)))))
        drag = moves * self.path_wait
        target = self.boundary_wait + .0015
        body = press_release + drag + target
        kind = _operation_type(path, length)
        learned = self._learned_average(kind, 0.0)
        if learned > 0.0:
            learned_body=max(.001,learned-travel_base)
            total=travel_base+travel_distance+learned_body
            body_scale=learned_body/max(.000001,body)
            travel_seconds=travel_base+travel_distance
        else:
            total=(travel_base+travel_distance+body)*self.multiplier
            body_scale=self.multiplier
            travel_seconds=(travel_base+travel_distance)*self.multiplier
        return CostBreakdown(
            total, drag_seconds=drag*body_scale, travel_seconds=travel_seconds,
            press_release_seconds=press_release*body_scale,
            target_processing_seconds=target*body_scale, operations=1, moves=moves,
            source=self.source)
''')
# dedent removes class indentation; restore it explicitly.
new_path='\n'.join(('    '+line if line else '') for line in new_path.splitlines()).lstrip('\n')+'\n'
p.write_text(text[:start]+new_path+text[end:],encoding='utf-8')

# Version / release surfaces.
replace('Version.py',"APP_VERSION = '1.0.145-rc21'","APP_VERSION = '1.0.145-rc22'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc21"','#define MyAppVersion "1.0.145-rc22"')
for test in Path('.').glob('test_*.py'):
    raw=test.read_text(encoding='utf-8')
    if '1.0.145-rc21' in raw:test.write_text(raw.replace('1.0.145-rc21','1.0.145-rc22'),encoding='utf-8')
for name in ('README.md','docs/wiki/Installation.md','docs/README.md','README-INDEX.md','docs/wiki/Home.md','docs/wiki/Updates.md'):
    p=Path(name)
    if p.exists():p.write_text(p.read_text(encoding='utf-8').replace('1.0.145-rc21','1.0.145-rc22'),encoding='utf-8')

notes='''# Image Draw Bot v1.0.145-rc22 — Learned Cursor Travel Integrity\n\n- Keep real cursor-distance cost additive even when a profile has learned dot/stroke operation runtimes.\n- Treat learned operation runtime as the nominal path body/baseline instead of replacing stateful travel.\n- Add runtime aliases so `short_stroke` and `long_stroke` can safely reuse generic `stroke/path/drag` measurements.\n- Preserve the existing bounded distance curve, operation switch calibration and cold-start behavior.\n- Bump `ExecutionCostModel` to v4 and keep cost breakdown fields summing to the exact modeled total.\n- Prevent calibrated routing from becoming distance-blind after several completed draws.\n'''
Path('RELEASE-NOTES-v1.0.145-rc22.md').write_text(notes,encoding='utf-8')
history='''# Image Draw Bot v1.0.145-rc22 — Learned Cursor Travel Integrity\n\n- Learned stroke timing no longer erases real cursor distance.\n- Generic stroke runtime measurements feed short/long stroke planning through safe aliases.\n- ExecutionCostModel v4 preserves stateful routing after calibration.\n\n'''
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=Path(name);p.write_text(history+p.read_text(encoding='utf-8'),encoding='utf-8')

TEST=dedent(r'''\
import unittest
from unittest.mock import patch

from ExecutionCostModel import build_cost_model,EXECUTION_MODEL_VERSION
from Version import APP_VERSION


def opts():
    return {'profile_key':'gartic','speed':'Balanced','delay':.004,'brush_px':2,
            'paint_current_color':False}


def cal(runtime,ratio=1.6,samples=8):
    return {'samples':samples,'ratio':ratio,'operation_runtime':runtime}


class Rc22LearnedCursorTravelTests(unittest.TestCase):
    def test_learned_short_stroke_never_erases_cursor_distance(self):
        learned=cal({'short_stroke':{'average_seconds':.20}})
        with patch('ExecutionCostModel.correction_for',return_value=learned):
            model=build_cost_model(opts(),(100,100),(100,100))
        path=((50,50),(60,50))
        near=model.path_cost(path,cursor=(50,50));far=model.path_cost(path,cursor=(-1000,50))
        self.assertGreater(far.total_seconds,near.total_seconds)
        self.assertGreater(far.travel_seconds,near.travel_seconds)
        self.assertAlmostEqual(near.total_seconds,.20,places=6)

    def test_generic_stroke_runtime_alias_applies_to_short_and_long(self):
        learned=cal({'stroke':{'average_seconds':.31}})
        with patch('ExecutionCostModel.correction_for',return_value=learned):
            model=build_cost_model(opts(),(100,100),(100,100))
        self.assertAlmostEqual(model.path_cost(((0,0),(10,0)),cursor=(0,0)).total_seconds,.31,places=6)
        self.assertAlmostEqual(model.path_cost(((0,0),(80,0)),cursor=(0,0)).total_seconds,.31,places=6)

    def test_dot_runtime_also_preserves_distance(self):
        learned=cal({'dot':{'average_seconds':.12}})
        with patch('ExecutionCostModel.correction_for',return_value=learned):
            model=build_cost_model(opts(),(100,100),(100,100))
        near=model.path_cost(((20,20),),cursor=(20,20))
        far=model.path_cost(((20,20),),cursor=(-1000,20))
        self.assertAlmostEqual(near.total_seconds,.12,places=6)
        self.assertGreater(far.total_seconds,near.total_seconds)

    def test_breakdown_sums_to_total_under_learning(self):
        learned=cal({'stroke':{'average_seconds':.25}})
        with patch('ExecutionCostModel.correction_for',return_value=learned):
            model=build_cost_model(opts(),(100,100),(400,400))
        row=model.path_cost(((5,5),(30,5)),cursor=(0,0))
        summed=row.drag_seconds+row.travel_seconds+row.press_release_seconds+row.target_processing_seconds
        self.assertAlmostEqual(row.total_seconds,summed,places=9)

    def test_cold_path_still_increases_with_distance(self):
        cold={'samples':0,'ratio':1.0,'operation_runtime':{}}
        with patch('ExecutionCostModel.correction_for',return_value=cold):
            model=build_cost_model(opts(),(100,100),(100,100))
        path=((20,20),(40,20))
        self.assertGreater(model.path_seconds(path,cursor=(-1000,20)),model.path_seconds(path,cursor=(20,20)))

    def test_version(self):
        self.assertEqual(EXECUTION_MODEL_VERSION,4)
        self.assertEqual(APP_VERSION,'1.0.145-rc22')


if __name__=='__main__':unittest.main()
''')
Path('test_rc22_learned_cursor_travel.py').write_text(TEST,encoding='utf-8')
