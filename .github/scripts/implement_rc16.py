from pathlib import Path
from textwrap import dedent


def replace(path, old, new, count=1):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected rc16 patch anchor missing in {path}: {old[:180]!r}')
    p.write_text(text.replace(old,new,count),encoding='utf-8')


# Full-detail preview keeps final planner semantics, but no longer serializes all planning.
replace('PreviewQuality.py',
'''from PIL import Image\nimport math\n''',
'''from PIL import Image\nimport math\n\nfrom ResourceAllocation import resolve_cpu_workers\n''')
replace('PreviewQuality.py',
'''    out=dict(options,_full_detail_preview=True,_preview_plan=False,\n             _preview_mode='Manual',_target_area=(w,h),_preview_area=(w,h),\n             cpu_workers='1',cpu_workers_resolved=1,cpu_engine='Threads',gpu_mode='CPU')\n''',
'''    requested_workers=str(options.get('cpu_workers') or 'Auto')\n    try:\n        supplied=options.get('cpu_workers_resolved')\n        resolved=int(supplied) if supplied not in (None,'') else resolve_cpu_workers(requested_workers)\n    except (TypeError,ValueError):\n        resolved=resolve_cpu_workers('Auto')\n    preview_workers=max(1,min(4,int(resolved)))\n    preview_mode=str(options.get('preview_mode') or options.get('_preview_mode') or 'Manual')\n    out=dict(options,_full_detail_preview=True,_preview_plan=False,\n             _preview_mode=preview_mode,_target_area=(w,h),_preview_area=(w,h),\n             cpu_workers=str(preview_workers),cpu_workers_resolved=preview_workers,cpu_engine='Threads',gpu_mode='CPU',\n             _preview_resource_policy='full-detail-planner-parity',\n             _preview_resource_worker_cap=preview_workers)\n''')

# User-triggered Build preview should show the real planner unless the user explicitly selected Auto light.
replace('DrawBot.py',
'''    def request_preview(self):\n        if self.original is None:\n            self.status.set('Load an image before building a preview.')\n            return None\n        return self.update_plan(user_initiated=True, reason='build-preview-button')\n''',
'''    def request_preview(self):\n        if self.original is None:\n            self.status.set('Load an image before building a preview.')\n            return None\n        try:mode=validate_preview_mode(str(self.preview_mode.get()))\n        except Exception:mode='Manual'\n        # Manual / Auto full button presses are explicit and may spend more time\n        # to mirror final Draw geometry. Auto light remains the opt-in fast approximation.\n        return self.update_plan(user_initiated=True, reason='build-preview-button',full_detail=(mode!='Auto light'))\n''')
replace('DrawBot.py',
'''    Preview is intentionally an approximation of the final plan.  Heavy final\n    settings (Extreme resolution, worker batches, CUDA initialization and color\n    layering) are kept for Start Drawing, where the planning watchdog can manage\n    them.  The preview path stays small enough that cancellation is checked often.\n''',
'''    Automatic/lightweight preview is intentionally a bounded approximation of the\n    final plan. Explicit Manual / Auto full Build preview requests are routed to\n    ``full_preview_options`` instead, preserving final planner geometry while the\n    resource policy stays UI-safe and cancellable.\n''')

# Make the UI promise match the actual routing.
replace('StudioUI.py',
'''    tooltip(build_preview_btn,'Builds the preview manually. Preview uses the same CanvasGuard/Edge Behavior safety policy as execution.')\n''',
'''    tooltip(build_preview_btn,'Manual / Auto full uses the final planner for preview parity. Auto light keeps the bounded fast preview. CanvasGuard/Edge Behavior matches execution.')\n''')

# Release/version surfaces.
replace('Version.py',"APP_VERSION = '1.0.145-rc15'","APP_VERSION = '1.0.145-rc16'")
replace('installer/ImageDrawBot.iss','#define MyAppVersion "1.0.145-rc15"','#define MyAppVersion "1.0.145-rc16"')
for test in Path('.').glob('test_*.py'):
    raw=test.read_text(encoding='utf-8')
    if '1.0.145-rc15' in raw:
        test.write_text(raw.replace('1.0.145-rc15','1.0.145-rc16'),encoding='utf-8')
for name in ('README.md','docs/wiki/Installation.md','docs/README.md','README-INDEX.md','docs/wiki/Home.md','docs/wiki/Updates.md'):
    p=Path(name)
    if p.exists():
        p.write_text(p.read_text(encoding='utf-8').replace('1.0.145-rc15','1.0.145-rc16'),encoding='utf-8')

notes='''# Image Draw Bot v1.0.145-rc16 — Preview Planner Parity\n\n- Route an explicit **Build preview** through the full-detail/final planner in Manual and Auto full modes.\n- Keep Auto light as the deliberately bounded fast approximation for users who prefer minimum preview latency.\n- Preserve final-plan geometry, Fill/brush decisions, CanvasGuard policy and execution-time model in the full-detail preview path.\n- Raise full-detail preview planning from a forced single CPU worker to a UI-safe maximum of four workers using the existing ResourceAllocation policy.\n- Keep preview GPU analysis on CPU so cancellation and UI responsiveness remain deterministic; final Draw still re-evaluates the configured GPU backend.\n- Expose preview resource-policy metadata so diagnostics can distinguish exact planner parity from lightweight previews.\n'''
Path('RELEASE-NOTES-v1.0.145-rc16.md').write_text(notes,encoding='utf-8')
history='''# Image Draw Bot v1.0.145-rc16 — Preview Planner Parity\n\n- Manual / Auto full Build preview now uses the same full-detail planner path as final Draw.\n- Auto light remains the explicit fast approximation.\n- Full-detail preview can use up to four bounded CPU workers instead of always one.\n\n'''
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=Path(name);p.write_text(history+p.read_text(encoding='utf-8'),encoding='utf-8')

TEST=dedent(r'''\
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from DrawBot import DrawBotApp
from PreviewQuality import full_preview_options
from Version import APP_VERSION


class Value:
    def __init__(self,value):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value


class Rc16PreviewParityTests(unittest.TestCase):
    def test_manual_build_preview_routes_to_full_detail_planner(self):
        app=SimpleNamespace(original=object(),preview_mode=Value('Manual'),status=Value(''))
        calls=[]
        app.update_plan=lambda **kw:calls.append(kw) or kw
        result=DrawBotApp.request_preview(app)
        self.assertTrue(result['user_initiated']);self.assertTrue(result['full_detail'])

    def test_auto_full_button_routes_to_full_detail_planner(self):
        app=SimpleNamespace(original=object(),preview_mode=Value('Auto full'),status=Value(''))
        app.update_plan=lambda **kw:kw
        self.assertTrue(DrawBotApp.request_preview(app)['full_detail'])

    def test_auto_light_button_keeps_bounded_preview(self):
        app=SimpleNamespace(original=object(),preview_mode=Value('Auto light'),status=Value(''))
        app.update_plan=lambda **kw:kw
        self.assertFalse(DrawBotApp.request_preview(app)['full_detail'])

    def test_full_detail_preview_preserves_quality_and_caps_workers(self):
        options={'ram_budget_mb':2048,'cpu_workers':'8','cpu_workers_resolved':8,
                 'color_layers':'All','planning_resolution':'Extreme','max_seconds':90,
                 'preview_mode':'Manual'}
        out=full_preview_options(options,(1200,800))
        self.assertFalse(out['_preview_plan']);self.assertTrue(out['_full_detail_preview'])
        self.assertEqual(out['planning_resolution'],'Extreme');self.assertEqual(out['color_layers'],'All')
        self.assertEqual(out['cpu_workers'],'4');self.assertEqual(out['cpu_workers_resolved'],4)
        self.assertEqual(out['gpu_mode'],'CPU')
        self.assertEqual(out['_preview_resource_policy'],'full-detail-planner-parity')

    def test_single_worker_request_stays_single_worker(self):
        out=full_preview_options({'ram_budget_mb':1024,'cpu_workers':'1'},(800,500))
        self.assertEqual(out['cpu_workers_resolved'],1)

    def test_source_options_are_not_mutated(self):
        options={'ram_budget_mb':1024,'cpu_workers':'8','color_layers':'All'}
        before=dict(options);full_preview_options(options,(800,500));self.assertEqual(options,before)

    def test_version(self):self.assertEqual(APP_VERSION,'1.0.145-rc16')


if __name__=='__main__':unittest.main()
''')
Path('test_rc16_preview_parity.py').write_text(TEST,encoding='utf-8')
