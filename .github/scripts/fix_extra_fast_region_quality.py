from pathlib import Path


def replace(path, old, new):
    p=Path(path)
    text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'anchor missing in {path}: {old[:120]!r}')
    if text.count(old)!=1:
        raise SystemExit(f'anchor not unique in {path}: {text.count(old)} matches')
    p.write_text(text.replace(old,new),encoding='utf-8')


# Extra Fast is a preset. A stale saved Strong simplify setting must never leak
# into it and erase portrait/edge structure before regional planning starts.
replace(
    'AutoDrawing.py',
    "        out.setdefault('adaptive_detail','Auto')\n        engine='Extra Fast 2.0 hybrid: outline + Fill, safe connected scanlines fallback' if out.get('fill_tool_available') else 'Extra Fast 2.0 connected scanlines (calibrate Fill to enable buckets)'\n",
    "        out['adaptive_detail']='Auto'\n        engine='Extra Fast regional hybrid: Fill + verified multi-brush regions + structure/detail recovery' if out.get('fill_tool_available') else 'Extra Fast regional hybrid: verified multi-brush regions + structure/detail recovery'\n"
)

# Route full-colour Extra Fast through Adaptive Region Hybrid before the generic
# scanline/cap path. The inner colour-plan recursion is explicitly excluded.
replace(
    'DrawBot.py',
    "    options = _ensure_time_budget_options(options)\n    if options.get('outline') and options.get('sketch_detail')=='Auto':\n",
    "    options = _ensure_time_budget_options(options)\n    # Extra Fast quality fix: the old route built connected scanlines and then\n    # applied a generic path-count cap, which could discard most of a portrait\n    # (for example 653 candidate paths -> 182 kept). Adaptive Region Hybrid\n    # instead chooses exact connected components, verified H/V geometry, Fill\n    # and physically verified browser brush sizes under the real time model.\n    # Its component scheduler owns the deadline, so important structure is not\n    # destroyed later by an unrelated per-path cap.\n    if (options.get('extra_fast') and options.get('extra_fast_v2')\n            and not options.get('_adaptive_hybrid_inner')\n            and not (options.get('paint_current_color') or options.get('outline') or options.get('erase_mode'))):\n        from AdaptiveRegionHybrid import build_adaptive_hybrid_plan\n        return build_adaptive_hybrid_plan(original,area,options,make_plan,finish_plan,cancelled)\n    if options.get('outline') and options.get('sketch_detail')=='Auto':\n"
)

# Treat Adaptive Region Hybrid as a first-class prebuilt execution engine, just
# like Pixel Accurate and Sketch+Fill. This prevents generic path capping and a
# second deadline renderer from undoing the region scheduler's decisions.
replace(
    'DrawBot.py',
    "    pixel_prebuilt = options.get('_pixel_execution_groups')\n    sketch_fill_prebuilt = options.get('_sketch_fill_execution_groups')\n    if pixel_prebuilt is not None:\n",
    "    pixel_prebuilt = options.get('_pixel_execution_groups')\n    sketch_fill_prebuilt = options.get('_sketch_fill_execution_groups')\n    adaptive_hybrid_prebuilt = options.get('_adaptive_hybrid_execution_groups')\n    if pixel_prebuilt is not None:\n"
)

replace(
    'DrawBot.py',
    "    elif sketch_fill_prebuilt is not None:\n        execution_groups=[list(paths) for paths in sketch_fill_prebuilt]\n        path_meta=dict(continuous_path_stats(groups,execution_groups))\n        path_meta.update(options.get('sketch_fill_meta') or {})\n        path_meta['mode']='Sketch + Auto Fill'\n        path_meta['sketch_fill']=True\n        path_meta['stroke_optimizer_requested']='Off'\n        path_meta['stroke_optimizer_effective']='Sketch Fill phase scheduler'\n    elif options.get('sketch_execution_groups') is not None:\n",
    "    elif sketch_fill_prebuilt is not None:\n        execution_groups=[list(paths) for paths in sketch_fill_prebuilt]\n        path_meta=dict(continuous_path_stats(groups,execution_groups))\n        path_meta.update(options.get('sketch_fill_meta') or {})\n        path_meta['mode']='Sketch + Auto Fill'\n        path_meta['sketch_fill']=True\n        path_meta['stroke_optimizer_requested']='Off'\n        path_meta['stroke_optimizer_effective']='Sketch Fill phase scheduler'\n    elif adaptive_hybrid_prebuilt is not None:\n        execution_groups=[list(paths) for paths in adaptive_hybrid_prebuilt]\n        path_meta=dict(continuous_path_stats(groups,execution_groups))\n        _ah=dict(options.get('adaptive_hybrid_meta') or {})\n        _schedule=dict(_ah.get('schedule') or {})\n        path_meta.update({\n            'mode':'Extra Fast adaptive regions',\n            'extra_fast_v2':True,\n            'adaptive_hybrid':True,\n            'adaptive_hybrid_components':int(_ah.get('components',0) or 0),\n            'adaptive_hybrid_selected_components':int(_schedule.get('selected_components',0) or 0),\n            'adaptive_hybrid_dropped_components':int(_schedule.get('dropped_components',0) or 0),\n            'adaptive_hybrid_pixel_accuracy_score':float((_ah.get('quality') or {}).get('pixel_accuracy_score',0) or 0),\n            'stroke_optimizer_requested':options.get('stroke_optimizer','Off'),\n            'stroke_optimizer_effective':'Adaptive Region scheduler',\n        })\n    elif options.get('sketch_execution_groups') is not None:\n"
)

replace(
    'DrawBot.py',
    "        if pixel_prebuilt is not None or sketch_fill_prebuilt is not None:\n            # Pixel Accurate and Sketch+Fill already own geometry/phase order.\n            # Keep every path; no generic cap/optimizer may reorder them.\n",
    "        if pixel_prebuilt is not None or sketch_fill_prebuilt is not None or adaptive_hybrid_prebuilt is not None:\n            # Pixel Accurate, Sketch+Fill and Adaptive Region Hybrid already own\n            # geometry/phase/deadline order. Keep every selected path; no generic\n            # cap/optimizer may discard or reorder their safe regional plan.\n"
)

replace(
    'DrawBot.py',
    "    if execution_groups is not None and pixel_prebuilt is None and sketch_fill_prebuilt is None:\n",
    "    if execution_groups is not None and pixel_prebuilt is None and sketch_fill_prebuilt is None and adaptive_hybrid_prebuilt is None:\n"
)

replace(
    'DrawBot.py',
    "    elif pixel_prebuilt is not None and options.get('time_budget_active'):\n        options['adaptive_deadline_meta']={'enabled':False,'reason':'Pixel Accurate uses the exact progressive PixelMap budget.'}\n\n    execution_sequence=[]\n",
    "    elif pixel_prebuilt is not None and options.get('time_budget_active'):\n        options['adaptive_deadline_meta']={'enabled':False,'reason':'Pixel Accurate uses the exact progressive PixelMap budget.'}\n    elif adaptive_hybrid_prebuilt is not None and options.get('time_budget_active'):\n        options['adaptive_deadline_meta']={'enabled':False,'reason':'Adaptive Region Hybrid already scheduled whole components against the real execution budget.'}\n\n    execution_sequence=[]\n"
)

replace(
    'DrawBot.py',
    "        sketch_fill_sequence=options.get('_sketch_fill_execution_sequence') if sketch_fill_prebuilt is not None else None\n        pixel_sequence=options.get('_pixel_execution_sequence') if pixel_prebuilt is not None else None\n        if sketch_fill_sequence is not None:\n",
    "        sketch_fill_sequence=options.get('_sketch_fill_execution_sequence') if sketch_fill_prebuilt is not None else None\n        pixel_sequence=options.get('_pixel_execution_sequence') if pixel_prebuilt is not None else None\n        adaptive_hybrid_sequence=options.get('_adaptive_hybrid_execution_sequence') if adaptive_hybrid_prebuilt is not None else None\n        if sketch_fill_sequence is not None:\n"
)

replace(
    'DrawBot.py',
    "        elif deadline_sequence is not None:\n            execution_sequence=[dict(entry) for entry in deadline_sequence]\n",
    "        elif adaptive_hybrid_sequence is not None:\n            execution_sequence=[dict(entry) for entry in adaptive_hybrid_sequence]\n            _ah=options.get('adaptive_hybrid_meta') or {}\n            _schedule=(_ah.get('schedule') or {}) if isinstance(_ah,dict) else {}\n            _phase_counts={}\n            for _entry in execution_sequence:\n                _phase=str(_entry.get('phase') or 'structure')\n                _phase_counts[_phase]=_phase_counts.get(_phase,0)+1\n            path_meta.update({\n                'progressive_enabled':True,\n                'progressive_sequence_paths':len(execution_sequence),\n                'progressive_foundation_paths':int(_phase_counts.get('foundation',0)),\n                'progressive_contour_paths':int(_phase_counts.get('structure',0)),\n                'progressive_detail_paths':int(_phase_counts.get('detail',0)),\n                'progressive_correction_paths':int(_phase_counts.get('correction',0)),\n                'progressive_phase_order':'foundation -> structure -> detail -> correction',\n                'progressive_mode':'Adaptive Region Hybrid',\n                'color_workflow':'Regional deadline passes',\n                'target_before_paths':len(execution_sequence),\n                'target_after_paths':len(execution_sequence),\n                'target_skipped_paths':0,\n                'target_cap_applied':False,\n                'regional_deadline_selected_components':int(_schedule.get('selected_components',0) or 0),\n                'regional_deadline_dropped_components':int(_schedule.get('dropped_components',0) or 0),\n            })\n        elif deadline_sequence is not None:\n            execution_sequence=[dict(entry) for entry in deadline_sequence]\n"
)

# The visible Simulated final must rasterize the exact regional execution
# sequence, including per-path brush sizes. The Quantized target intentionally
# remains the uncapped color target for diagnostics.
replace(
    'DrawBot.py',
    "    if options.get('sketch_fill_active') and execution_sequence:\n        try:\n            from SketchFillRenderer import render_sequence_preview\n            preview=render_sequence_preview(image.size,size,execution_sequence,palette_rgb,brush)\n        except Exception as _sf_preview_error:\n            log_event(f'Sketch Fill sequence preview fallback: {_sf_preview_error!r}')\n    profiler_stop(options, 'preview_rendering', _prof_preview)\n",
    "    if options.get('sketch_fill_active') and execution_sequence:\n        try:\n            from SketchFillRenderer import render_sequence_preview\n            preview=render_sequence_preview(image.size,size,execution_sequence,palette_rgb,brush)\n        except Exception as _sf_preview_error:\n            log_event(f'Sketch Fill sequence preview fallback: {_sf_preview_error!r}')\n    if options.get('adaptive_hybrid_active') and execution_sequence:\n        try:\n            from AdaptiveRegionHybrid import render_adaptive_preview\n            preview=render_adaptive_preview(image.size,size,execution_sequence,palette_rgb,options.get('fill_regions') or ())\n        except Exception as _ah_preview_error:\n            log_event(f'Adaptive Region simulated-final preview fallback: {_ah_preview_error!r}')\n    profiler_stop(options, 'preview_rendering', _prof_preview)\n"
)

# Give the plan explicit Extra Fast diagnostics so logs make it obvious whether
# the new regional route is actually active on a user's machine.
replace(
    'AdaptiveRegionHybrid.py',
    '            "enabled":True,"version":ADAPTIVE_HYBRID_VERSION,"engine":"Adaptive Region Hybrid 4.0",\n',
    '            "enabled":True,"version":ADAPTIVE_HYBRID_VERSION,"engine":"Adaptive Region Hybrid 4.0",\n            "extra_fast_regional_route":bool(options.get("extra_fast")),\n'
)

# Regression coverage without creating image fixtures/artifacts.
Path('test_extra_fast_region_quality_rc24.py').write_text(r'''import ast
import unittest
from pathlib import Path

from AutoDrawing import resolve_drawing
from BrowserBrushSize import POLICIES
from Version import APP_VERSION


class ExtraFastRegionQualityRc24Tests(unittest.TestCase):
    def test_extra_fast_overrides_stale_strong_simplify(self):
        opts={
            'render_preset':'Extra fast','adaptive_detail':'Strong simplify',
            'fill_tool_available':False,'erase_mode':False,'paint_current_color':False,
            'outline':False,'exact_color_available':False,
        }
        out=resolve_drawing(object(),opts)
        self.assertEqual(out['adaptive_detail'],'Auto')
        self.assertTrue(out['extra_fast_v2'])
        self.assertIn('regional hybrid',out['auto_drawing_meta']['engine'].lower())

    def test_gartic_policy_exposes_five_real_brush_levels(self):
        self.assertEqual(POLICIES['gartic-phone']['sizes'],(2,4,8,16,28))

    def test_make_plan_routes_extra_fast_to_adaptive_regions(self):
        source=Path('DrawBot.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        make_plan=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='make_plan')
        calls=[n for n in ast.walk(make_plan) if isinstance(n,ast.Call)]
        names=[]
        for call in calls:
            fn=call.func
            if isinstance(fn,ast.Name):names.append(fn.id)
            elif isinstance(fn,ast.Attribute):names.append(fn.attr)
        self.assertIn('build_adaptive_hybrid_plan',names)

    def test_finish_plan_consumes_regional_groups_and_sequence(self):
        source=Path('DrawBot.py').read_text(encoding='utf-8')
        self.assertIn("adaptive_hybrid_prebuilt = options.get('_adaptive_hybrid_execution_groups')",source)
        self.assertIn("options.get('_adaptive_hybrid_execution_sequence')",source)
        self.assertIn('or adaptive_hybrid_prebuilt is not None',source)
        self.assertIn('adaptive_hybrid_prebuilt is None',source)
        self.assertIn('render_adaptive_preview',source)
        self.assertIn("'target_skipped_paths':0",source)

    def test_version_stays_rc24_for_hotfix_branch(self):
        self.assertEqual(APP_VERSION,'1.0.145-rc24')


if __name__=='__main__':
    unittest.main()
''',encoding='utf-8')

print('Extra Fast regional quality patch applied.')
