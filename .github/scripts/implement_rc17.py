from pathlib import Path
from textwrap import dedent
import re


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected rc17 patch anchor missing in {path}: {old[:180]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')


# ExecutionCostModel must support a cold/unlearned caller without reading the same
# DrawTimeCalibration a second time. Planner callers keep the existing behaviour.
replace('ExecutionCostModel.py',
'''        self.calibration = correction_for(self.options)\n        self.runtime = dict(self.calibration.get("operation_runtime") or {})\n''',
'''        _override = self.options.get("_execution_cost_calibration_override")\n        self.calibration = dict(_override) if isinstance(_override, dict) else correction_for(self.options)\n        self.runtime = dict(self.calibration.get("operation_runtime") or {})\n''')

# Make explicit UI operations first-class sequence entries. This keeps the model
# reusable by ETA/runtime optimizers without pretending every operation is a stroke.
replace('ExecutionCostModel.py',
'''            operation = str(entry.get("operation_type") or "stroke")\n            if operation == "fill":\n                c = self.switch_cost("fill")\n                totals["fill"] += c; totals["ops"] += 1\n                continue\n            new_color = int(entry.get("color_index", color if color is not None else 0))\n''',
'''            operation = str(entry.get("operation_type") or "stroke")\n            if operation in ("fill", "fill_action"):\n                totals["fill"] += self.switch_cost("fill"); totals["ops"] += 1\n                continue\n            if operation == "verification":\n                totals["verification"] += self.switch_cost("verification"); totals["ops"] += 1\n                continue\n            if operation == "tool_change":\n                totals["tool"] += self.switch_cost("tool_change"); totals["tool_n"] += 1; totals["ops"] += 1\n                continue\n            if operation == "palette_change":\n                totals["palette"] += self.switch_cost("palette_change"); totals["palette_n"] += 1; totals["ops"] += 1\n                if entry.get("color_index") is not None:\n                    color = int(entry.get("color_index"))\n                continue\n            if operation == "brush_change":\n                totals["brush"] += self.switch_cost("brush_change"); totals["brush_n"] += 1; totals["ops"] += 1\n                if entry.get("brush_px") is not None:\n                    brush = max(1, int(entry.get("brush_px")))\n                continue\n            new_color = int(entry.get("color_index", color if color is not None else 0))\n''')

# Replace the visible ETA's old HybridCostModel aggregate with the same stateful
# ExecutionCostModel used by Adaptive Region Hybrid planner decisions. Fill keeps
# RegionFillEngine's own batch-aware authoritative estimate. Both are forced cold;
# DrawTimeEstimate applies measured profile calibration exactly once afterwards.
p=Path('DrawTimeEstimate.py')
text=p.read_text(encoding='utf-8')
start=text.index('def _sequence_operation_estimate(')
end=text.index('\ndef _measured_throughput_floor', start)
new_func=dedent(r'''
def _sequence_operation_estimate(plan: dict[str,Any]) -> tuple[float,dict[str,Any]]:
    """Cost the exact final execution order with the planner's stateful cost model.

    The underlying ExecutionCostModel is deliberately forced to cold/unlearned
    calibration here. DrawTimeEstimate applies DrawTimeCalibration once, after the
    complete stroke + Fill + fixed-overhead estimate has been assembled.
    """
    sequence=[row for row in (plan.get("execution_sequence") or ()) if isinstance(row,dict)]
    if not sequence:
        return 0.0,{"used":False,"reason":"no final execution_sequence"}
    options=plan.get("options") if isinstance(plan.get("options"),dict) else {}
    model_options=dict(options)
    cold={"learned":False,"samples":0,"ratio":1.0,"mape":None,"operation_runtime":{}}
    model_options["_execution_cost_calibration_override"]=cold
    model_options["_hybrid_cost_calibration_override"]=cold

    image_size=None
    image=plan.get("image")
    try:image_size=tuple(map(int,image.size))
    except Exception:image_size=None
    if not image_size:
        image_size=_area(plan.get("plan_area") or options.get("_preview_area") or options.get("_target_area")) or (1,1)
    try:fitted=tuple(map(int,plan.get("fitted")))
    except Exception:fitted=None
    if not fitted:
        fitted=_area(plan.get("target_area") or options.get("_target_area") or plan.get("plan_area")) or image_size

    try:
        from ExecutionCostModel import build_cost_model as build_execution_cost_model
        model=build_execution_cost_model(model_options,image_size,fitted)
    except Exception as exc:
        return 0.0,{"used":False,"reason":f"execution cost model unavailable: {type(exc).__name__}"}

    try:initial_brush=max(1,int(options.get("brush_px",1) or 1))
    except Exception:initial_brush=1
    breakdown=model.sequence_cost(sequence,initial_brush=initial_brush)
    sequence_seconds=max(0.0,float(breakdown.total_seconds or 0.0))
    total=sequence_seconds

    path_rows=[];path_kinds=set();operation_counts={}
    for row in sequence:
        operation=str(row.get("operation_type") or ("dot" if len(row.get("path") or ())<=1 else "stroke"))
        if row.get("path"):
            path_rows.append(row);path_kinds.add(operation)
        operation_counts[operation]=operation_counts.get(operation,0)+1

    fill_regions=[row for row in (options.get("fill_regions") or plan.get("fill_regions") or ()) if isinstance(row,dict)]
    fill_meta={"fill_regions":0,"fill_color_batches":0,"total_seconds":0.0,
               "fill_contour_and_click_seconds":0.0,"fill_tool_switch_seconds":0.0}
    if fill_regions:
        try:
            from RegionFillEngine import estimate_fill_execution_seconds
            fill_meta=dict(estimate_fill_execution_seconds(fill_regions,image_size,fitted,model_options) or {})
        except Exception:
            fill_meta={"fill_regions":len(fill_regions),"fill_color_batches":0,
                       "total_seconds":len(fill_regions)*model.switch_cost("fill"),
                       "fill_contour_and_click_seconds":len(fill_regions)*model.switch_cost("fill"),
                       "fill_tool_switch_seconds":0.0,"fallback":True}
        total+=max(0.0,float(fill_meta.get("total_seconds") or 0.0))

    # Background Fill is a separate prelude and is not part of region Fill rows.
    background=options.get("background_fill_plan") or {}
    background_seconds=0.0;background_fill_actions=0;background_tool_changes=0;background_verifications=0
    if isinstance(background,dict) and background.get("enabled"):
        background_fill_actions=1;background_verifications=1
        tool_action_count=len(options.get("fill_tool_actions") or ())+len(options.get("fill_restore_actions") or ())
        if tool_action_count==0 and options.get("fill_tool_available"):tool_action_count=2
        background_tool_changes=tool_action_count
        background_seconds=(model.switch_cost("fill")+model.switch_cost("verification")+
                            background_tool_changes*model.switch_cost("tool_change"))
        total+=background_seconds

    deadline_meta=options.get("adaptive_deadline_meta") or {}
    fixed=deadline_meta.get("fixed_overhead") or {}
    outside_sequence=0.0
    for key in ("countdown_seconds","clear_seconds"):
        try:outside_sequence+=max(0.0,float(fixed.get(key,0.0) or 0.0))
        except Exception:pass
    total+=outside_sequence

    # Operation-level measured correction uses the same final counts, but is
    # applied later. Keep model averages here cold to prevent double learning.
    model_average_seconds={}
    path_seconds=(max(0.0,float(breakdown.drag_seconds))+max(0.0,float(breakdown.travel_seconds))+
                  max(0.0,float(breakdown.press_release_seconds))+max(0.0,float(breakdown.target_processing_seconds)))
    if path_rows:
        avg=path_seconds/max(1,len(path_rows))
        for kind in path_kinds:model_average_seconds[str(kind)]=avg
    palette_n=max(0,int(breakdown.palette_switches or 0))
    brush_n=max(0,int(breakdown.brush_switches or 0))
    tool_n=max(0,int(breakdown.tool_switches or 0))+background_tool_changes
    if palette_n:
        operation_counts["palette_change"]=palette_n
        model_average_seconds["palette_change"]=max(0.0,float(breakdown.palette_seconds))/palette_n
    if brush_n:
        operation_counts["tool_change"]=operation_counts.get("tool_change",0)+brush_n
        model_average_seconds["tool_change"]=max(0.0,float(breakdown.brush_seconds))/brush_n
    if tool_n:
        operation_counts["tool_change"]=operation_counts.get("tool_change",0)+tool_n
        prior=model_average_seconds.get("tool_change",0.0)
        direct=(max(0.0,float(breakdown.tool_seconds))+background_tool_changes*model.switch_cost("tool_change"))/max(1,tool_n)
        model_average_seconds["tool_change"]=max(prior,direct)
    fill_n=max(0,int(fill_meta.get("fill_regions") or 0))+background_fill_actions
    if fill_n:
        operation_counts["fill_action"]=fill_n
        fill_seconds=max(0.0,float(fill_meta.get("fill_contour_and_click_seconds") or 0.0))+background_fill_actions*model.switch_cost("fill")
        model_average_seconds["fill_action"]=fill_seconds/max(1,fill_n)
    verification_n=max(0,int(fill_meta.get("fill_regions") or 0))+background_verifications
    if verification_n:
        operation_counts["verification"]=verification_n
        model_average_seconds["verification"]=model.switch_cost("verification")

    modeled_operation_seconds=sum(max(0,int(operation_counts.get(kind,0) or 0))*max(0.0,float(avg or 0.0))
                                  for kind,avg in model_average_seconds.items())
    return total,{
        "used":True,"model":"stateful ExecutionCostModel + RegionFill batch model",
        "execution_cost_model":"ExecutionCostModel","execution_cost_calibration":"cold override; measured correction applied once",
        "path_count":len(path_rows),"stroke_sequence_paths":len(path_rows),
        "color_changes":palette_n,"brush_changes":brush_n,
        "fill_actions":fill_n,"fill_color_batches":int(fill_meta.get("fill_color_batches") or 0),
        "tool_changes":tool_n,"verification_actions":verification_n,
        "sequence_seconds":round(sequence_seconds,5),"fill_seconds":round(max(0.0,float(fill_meta.get("total_seconds") or 0.0)),5),
        "background_fill_seconds":round(background_seconds,5),"outside_sequence_seconds":round(outside_sequence,5),
        "operation_counts":{str(k):int(v) for k,v in operation_counts.items() if int(v)>0},
        "operation_model_average_seconds":{str(k):round(float(v),7) for k,v in model_average_seconds.items() if float(v)>0},
        "modeled_operation_seconds":round(modeled_operation_seconds,5),
        "breakdown":breakdown.as_dict(),"fill_breakdown":fill_meta,
    }
''')
p.write_text(text[:start]+new_func+text[end:],encoding='utf-8')

# Version / release surfaces.
replace('Version.py',"APP_VERSION = '1.0.145-rc16'","APP_VERSION = '1.0.145-rc17'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc16"','#define MyAppVersion "1.0.145-rc17"')
for test in Path('.').glob('test_*.py'):
    raw=test.read_text(encoding='utf-8')
    if '1.0.145-rc16' in raw:test.write_text(raw.replace('1.0.145-rc16','1.0.145-rc17'),encoding='utf-8')
for name in ('README.md','docs/wiki/Installation.md','docs/README.md','README-INDEX.md','docs/wiki/Home.md','docs/wiki/Updates.md'):
    p=Path(name)
    if p.exists():p.write_text(p.read_text(encoding='utf-8').replace('1.0.145-rc16','1.0.145-rc17'),encoding='utf-8')

notes='''# Image Draw Bot v1.0.145-rc17 — Unified Execution Cost ETA\n\n- Use the same stateful `ExecutionCostModel` for visible Estimated Draw Time that Adaptive Region Hybrid uses for planner decisions.\n- Cost ordered cursor travel, sampled drag moves, palette switches and verified brush switches from the actual final execution sequence.\n- Reuse Region Fill Engine's batch-aware contour/Fill/tool-switch estimate instead of maintaining a second Fill timing approximation.\n- Add a cold calibration override to `ExecutionCostModel`; DrawTimeCalibration is applied exactly once after the complete base estimate.\n- Support explicit Fill, verification, tool, palette and brush operation entries in the shared sequence cost model.\n- Export ETA breakdown metadata for sequence, Fill, background Fill and outside-sequence overhead so estimate errors can be diagnosed from logs.\n'''
Path('RELEASE-NOTES-v1.0.145-rc17.md').write_text(notes,encoding='utf-8')
history='''# Image Draw Bot v1.0.145-rc17 — Unified Execution Cost ETA\n\n- Estimated Draw Time now shares the planner's stateful execution-cost model.\n- Region Fill timing reuses the batch-aware Fill estimator.\n- Local measured timing is applied once, not inside both base model and visible ETA correction.\n\n'''
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=Path(name);p.write_text(history+p.read_text(encoding='utf-8'),encoding='utf-8')

TEST=dedent(r'''\
import unittest
from unittest import mock

from DrawTimeEstimate import _sequence_operation_estimate, estimate_from_plan
from ExecutionCostModel import build_cost_model
from Version import APP_VERSION


def options():
    return {'delay':0.006,'speed':'Balanced','brush_px':2,'paint_current_color':False,
            'profile_key':'gartic','fill_tool_available':True,'fill_tool_actions':[],
            'fill_restore_actions':[],'draw_quality':'Balanced'}


def plan(sequence, **extra):
    p={'execution_sequence':sequence,'options':options(),'image':type('I',(),{'size':(100,100)})(),
       'fitted':(500,500),'plan_area':(100,100),'preview_area':(100,100),'target_area':(100,100),
       'estimate':1.0,'count':len(sequence),'path_stats':{}}
    p.update(extra);return p


class Rc17UnifiedExecutionCostEtaTests(unittest.TestCase):
    def test_execution_cost_override_bypasses_learned_profile(self):
        learned={'samples':20,'ratio':4.0,'operation_runtime':{'dot':{'average_seconds':2.0}}}
        with mock.patch('ExecutionCostModel.correction_for',return_value=learned):
            normal=build_cost_model(options(),(100,100),(500,500))
            cold_opts=options();cold_opts['_execution_cost_calibration_override']={'samples':0,'ratio':1.0,'operation_runtime':{}}
            cold=build_cost_model(cold_opts,(100,100),(500,500))
        self.assertGreater(normal.samples,0);self.assertEqual(cold.samples,0);self.assertEqual(cold.multiplier,1.0)
        self.assertLess(cold.path_cost(((5,5),)).total_seconds,normal.path_cost(((5,5),)).total_seconds)

    def test_eta_uses_shared_stateful_execution_cost_model(self):
        seq=[{'color_index':0,'brush_px':2,'path':((1,1),(20,1))},
             {'color_index':1,'brush_px':8,'path':((20,1),(20,20))}]
        seconds,meta=_sequence_operation_estimate(plan(seq))
        self.assertGreater(seconds,0);self.assertEqual(meta['execution_cost_model'],'ExecutionCostModel')
        self.assertEqual(meta['color_changes'],2);self.assertEqual(meta['brush_changes'],1)
        self.assertIn('sequence_seconds',meta);self.assertIn('breakdown',meta)

    def test_cursor_travel_changes_visible_base_cost(self):
        near=[{'color_index':0,'brush_px':2,'path':((1,1),(10,1))},
              {'color_index':0,'brush_px':2,'path':((11,1),(20,1))}]
        far=[{'color_index':0,'brush_px':2,'path':((1,1),(10,1))},
             {'color_index':0,'brush_px':2,'path':((90,90),(99,90))}]
        a,_=_sequence_operation_estimate(plan(near));b,_=_sequence_operation_estimate(plan(far))
        self.assertGreater(b,a)

    def test_fill_eta_reuses_region_fill_batch_estimator(self):
        p=plan([{'color_index':0,'brush_px':2,'path':((1,1),(10,1))}])
        p['options']['fill_regions']=[{'color_index':0,'contour':[(1,1),(5,1),(5,5),(1,5),(1,1)]}]
        with mock.patch('RegionFillEngine.estimate_fill_execution_seconds',return_value={
            'fill_regions':1,'fill_color_batches':1,'total_seconds':7.5,
            'fill_contour_and_click_seconds':6.5,'fill_tool_switch_seconds':1.0}):
            seconds,meta=_sequence_operation_estimate(p)
        self.assertAlmostEqual(meta['fill_seconds'],7.5,places=5)
        self.assertGreater(seconds,7.5);self.assertEqual(meta['fill_actions'],1)

    def test_explicit_ui_operations_are_first_class(self):
        model=build_cost_model({'_execution_cost_calibration_override':{'samples':0,'ratio':1.0,'operation_runtime':{}},**options()},(100,100),(100,100))
        seq=[{'operation_type':'palette_change','color_index':2},
             {'operation_type':'brush_change','brush_px':8},
             {'operation_type':'tool_change'}, {'operation_type':'verification'}, {'operation_type':'fill'}]
        cost=model.sequence_cost(seq)
        self.assertEqual(cost.palette_switches,1);self.assertEqual(cost.brush_switches,1);self.assertEqual(cost.tool_switches,1)
        self.assertGreater(cost.fill_seconds,0);self.assertGreater(cost.verification_seconds,0)

    def test_visible_estimate_exports_shared_model_metadata(self):
        seq=[{'color_index':0,'brush_px':2,'path':((1,1),(20,1))}]
        meta=estimate_from_plan(plan(seq))
        self.assertFalse(meta['is_projection'])
        self.assertEqual(meta['sequence_cost']['execution_cost_model'],'ExecutionCostModel')

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc17')


if __name__=='__main__':unittest.main()
''')
Path('test_rc17_unified_execution_cost_eta.py').write_text(TEST,encoding='utf-8')
