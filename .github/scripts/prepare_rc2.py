from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def replace_once(path, old, new):
    text = read(path)
    if old not in text:
        raise RuntimeError(f'Expected patch anchor not found in {path}')
    write(path, text.replace(old, new, 1))


# Version/public current-release references. Historical rc1 notes remain intact.
replace_once('Version.py', "APP_VERSION = '1.0.145-rc1'", "APP_VERSION = '1.0.145-rc2'")
replace_once('installer/ImageDrawBot.iss', '#define MyAppVersion "1.0.145-rc1"', '#define MyAppVersion "1.0.145-rc2"')
for rel in (
    'README.md', 'docs/wiki/Installation.md', 'docs/README.md', 'README-INDEX.md',
    'docs/wiki/Home.md', 'docs/wiki/Updates.md',
):
    p = ROOT / rel
    if p.exists():
        text = p.read_text(encoding='utf-8')
        text = text.replace('1.0.145-rc1', '1.0.145-rc2')
        p.write_text(text, encoding='utf-8')

# Active regression assertions track the current app version.
for p in ROOT.glob('test_*.py'):
    text = p.read_text(encoding='utf-8')
    if '1.0.145-rc1' in text:
        p.write_text(text.replace('1.0.145-rc1', '1.0.145-rc2'), encoding='utf-8')

# Browser tool inference: conservative, profile-relative and fail-closed.
write('BrowserToolLayout.py', '''"""Automatic browser drawing-tool layout inference for supported web profiles.

Control points are derived only from an already verified browser client/canvas
layout and visually scored before any click is allowed. Low confidence returns
no actions, preserving Image Draw Bot's no-guessed-click safety rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

SUPPORTED = frozenset({'gartic-phone', 'gartic-io'})


def _rgb_distance(a, b):
    return sqrt(sum((int(a[i]) - int(b[i])) ** 2 for i in range(3)))


def _clamp_point(point, rect):
    x, y = map(int, point); l, t, r, b = map(int, rect)
    return max(l, min(r - 1, x)), max(t, min(b - 1, y))


def _inside(point, box, margin=0):
    x, y = map(int, point); l, t, r, b = map(int, box)
    return l - margin <= x <= r + margin and t - margin <= y <= b + margin


def _patch(image, client_rect, point, radius=16):
    if image is None:
        return None
    l, t, _, _ = map(int, client_rect); x, y = map(int, point)
    x -= l; y -= t
    left=max(0,x-radius); top=max(0,y-radius)
    right=min(image.width,x+radius+1); bottom=min(image.height,y+radius+1)
    if right-left < 7 or bottom-top < 7:
        return None
    return image.crop((left,top,right,bottom)).convert('RGB')


def _control_score(patch):
    if patch is None:
        return 0.0
    w,h=patch.size; cx=w//2; cy=h//2
    center=patch.getpixel((cx,cy))
    corners=[patch.getpixel((1,1)),patch.getpixel((w-2,1)),patch.getpixel((1,h-2)),patch.getpixel((w-2,h-2))]
    ring=[]; radius=max(3,min(w,h)//3)
    for dx,dy in ((radius,0),(-radius,0),(0,radius),(0,-radius),(radius//2,radius//2),(-radius//2,radius//2)):
        ring.append(patch.getpixel((max(0,min(w-1,cx+dx)),max(0,min(h-1,cy+dy)))))
    background=tuple(sum(p[i] for p in corners)//len(corners) for i in range(3))
    contrast=max([_rgb_distance(center,background)]+[_rgb_distance(p,background) for p in ring])
    diversity=max((_rgb_distance(a,b) for a in ring for b in ring),default=0.0)
    darkness=max(0.0,255.0-sum(center)/3.0)
    return min(100.0,contrast*.55+diversity*.20+darkness*.25)


def _gartic_candidates(client_rect, canvas_box):
    l,t,r,b=map(int,client_rect); x0,y0,x1,y1=map(int,canvas_box)
    w,h=max(1,x1-x0),max(1,y1-y0); cw,ch=max(1,r-l),max(1,b-t)
    top_gap=max(22,min(int(ch*.055),int(h*.14)))
    right_gap=max(26,min(int(cw*.055),int(w*.18)))
    row=max(26,min(int(h*.115),int(ch*.090)))
    positions={
        'Brush':(x0+int(w*.060),y0-top_gap),
        'Eraser':(x1-int(w*.060),y0-top_gap),
        'Fill':(x1+right_gap,y0+int(row*1.15)),
        'Clear':(x1+right_gap,y0+int(row*2.20)),
    }
    return {name:_clamp_point(point,client_rect) for name,point in positions.items()}


def _candidates(profile_key, client_rect, canvas_box=None, palette_box=None):
    if not (isinstance(canvas_box,(tuple,list)) and len(canvas_box)==4):
        return {}
    if str(profile_key or '').lower() in SUPPORTED:
        return _gartic_candidates(client_rect,canvas_box)
    return {}


@dataclass(frozen=True)
class BrowserToolPlan:
    profile_key: str
    tools: dict
    confidence: float
    tool_scores: dict
    method: str

    def as_dict(self):
        return {
            'profile_key':self.profile_key,
            'tools':{str(name):[int(pos[0]),int(pos[1])] for name,pos in (self.tools or {}).items()},
            'confidence':float(self.confidence),
            'tool_scores':{str(name):float(score) for name,score in (self.tool_scores or {}).items()},
            'method':str(self.method),
        }


def plan_browser_tools(profile_key, screenshot, client_rect, *, canvas_box=None, palette_box=None):
    key=str(profile_key or '').lower()
    if key not in SUPPORTED:
        return BrowserToolPlan(key,{},0.0,{},'unsupported profile')
    positions=_candidates(key,client_rect,canvas_box=canvas_box,palette_box=palette_box)
    if not positions:
        return BrowserToolPlan(key,{},0.0,{},'tool geometry unavailable')
    scores={}; valid={}
    for tool,point in positions.items():
        if isinstance(canvas_box,(tuple,list)) and len(canvas_box)==4 and _inside(point,canvas_box,margin=4):
            continue
        score=_control_score(_patch(screenshot,client_rect,point)); scores[tool]=score
        if score>=8.0:
            valid[tool]=tuple(map(int,point))
    if not scores:
        return BrowserToolPlan(key,{},0.0,{},'candidate tools overlapped the canvas')
    avg=sum(min(40.0,float(v)) for v in scores.values())/(max(1,len(scores))*40.0)
    coverage=len(valid)/max(1,len(positions))
    confidence=max(0.0,min(1.0,avg*.70+coverage*.30))
    if 'Brush' not in valid:
        confidence=min(confidence,.35)
    method='verified canvas-relative browser tool layout' if confidence>=.58 and valid else 'browser tool layout confidence low'
    if confidence<.58:
        valid={}
    return BrowserToolPlan(key,valid,confidence,scores,method)


def build_browser_tool_action(plan, tool: str):
    if not isinstance(plan,dict):
        raise ValueError('Automatic browser tool layout is unavailable.')
    tools=plan.get('tools') or {}; position=tools.get(tool)
    confidence=float(plan.get('confidence',0.0) or 0.0)
    if not position or confidence<.58:
        raise ValueError(f'Automatic browser {tool} tool detection is not confident enough yet.')
    x,y=map(int,position)
    return tool.lower(),(x,y)
''')

# Extend browser brush presets to Gartic.io as well.
replace_once('BrowserBrushSize.py',
    "SUPPORTED = frozenset({'gartic-phone', 'skribbl', 'skribbl-fast', 'sketchheads'})",
    "SUPPORTED = frozenset({'gartic-phone', 'gartic-io', 'skribbl', 'skribbl-fast', 'sketchheads'})")
replace_once('BrowserBrushSize.py',
    "    'gartic-phone': {'sizes': (2, 4, 8, 16, 28), 'safe_index': 1},\n",
    "    'gartic-phone': {'sizes': (2, 4, 8, 16, 28), 'safe_index': 1},\n    'gartic-io': {'sizes': (2, 4, 8, 16, 28), 'safe_index': 1},\n")
replace_once('BrowserBrushSize.py',
    "    if profile_key == 'gartic-phone' and canvas:\n",
    "    if profile_key in ('gartic-phone', 'gartic-io') and canvas:\n")

# Image planning may opt into Fill for supported Gartic profiles even if manual
# tool calibration is absent; real preflight still requires a verified auto plan.
replace_once('DrawBot.py', '''        fill_available=False
        if (background_fill!='Off' or use_region_fill_engine) and not bypasses_palette(self):
            try:
                if paint_profile and selected_tool not in ('Use current tool','Eraser'):
                    from PaintTools import load_tool_calibration
                    tool_data=load_tool_calibration()
                    fill_available=(tool_data.get('tools',{}).get('Fill') is not None and self._paint_tool_preflight_ready())
                elif not paint_profile:
                    from AppTools import load_calibration
                    app_data=load_calibration(PROFILES[self.game.get()][0])
                    fill_available=all(name in app_data.get('tools',{}) for name in ('Brush','Fill'))
            except (OSError,ValueError,TypeError,AttributeError):
                fill_available=False
''', '''        fill_available=False
        if (background_fill!='Off' or use_region_fill_engine) and not bypasses_palette(self):
            try:
                if paint_profile and selected_tool not in ('Use current tool','Eraser'):
                    from PaintTools import load_tool_calibration
                    tool_data=load_tool_calibration()
                    fill_available=(tool_data.get('tools',{}).get('Fill') is not None and self._paint_tool_preflight_ready())
                elif not paint_profile:
                    profile_key_for_fill=PROFILES[self.game.get()][0]
                    from AppTools import load_calibration
                    app_data=load_calibration(profile_key_for_fill)
                    fill_available=all(name in app_data.get('tools',{}) for name in ('Brush','Fill'))
            except (OSError,ValueError,TypeError,AttributeError):
                fill_available=False
            if (not fill_available) and (not paint_profile):
                try:
                    from BrowserToolLayout import SUPPORTED as AUTO_BROWSER_TOOL_PROFILES
                    fill_available=(PROFILES[self.game.get()][0] in AUTO_BROWSER_TOOL_PROFILES)
                except Exception:
                    fill_available=False
''')

replace_once('DrawBot.py', '''            except Exception as brush_error:
                # Brush automation is an optimization/convenience layer. A
                # detector failure must not invent clicks; keep the current brush
                # and enlarge only the safety inset.
                options['canvas_guard_brush_px']=max(int(options.get('brush_px',3) or 3),12)
                options['browser_brush_plan']={'target_position':None,'safe_guard_px':options['canvas_guard_brush_px'],'method':str(brush_error)}
                log_event(f'Automatic browser brush detection fell back safely: {brush_error!r}.')
            # Paint-only real preflight: resolve stale palette-only saved
''', '''            except Exception as brush_error:
                # Brush automation is an optimization/convenience layer. A
                # detector failure must not invent clicks; keep the current brush
                # and enlarge only the safety inset.
                options['canvas_guard_brush_px']=max(int(options.get('brush_px',3) or 3),12)
                options['browser_brush_plan']={'target_position':None,'safe_guard_px':options['canvas_guard_brush_px'],'method':str(brush_error)}
                log_event(f'Automatic browser brush detection fell back safely: {brush_error!r}.')
            try:
                from BrowserToolLayout import SUPPORTED as TOOL_PROFILES,plan_browser_tools
                if profile_key in TOOL_PROFILES:
                    from PIL import ImageGrab
                    tool_shot=locals().get('shot')
                    if tool_shot is None:
                        tool_shot=ImageGrab.grab(bbox=tuple(current_client),all_screens=True).convert('RGB')
                    tool_pal_box=None
                    if palette:
                        xs=[p[0] for p in palette];ys=[p[1] for p in palette]
                        tool_pal_box=(min(xs),min(ys),max(xs)+1,max(ys)+1)
                    x,y,w,h=area
                    tool_plan=plan_browser_tools(profile_key,tool_shot,tuple(current_client),
                        canvas_box=(x,y,x+w,y+h),palette_box=tool_pal_box)
                    options['browser_tool_plan']=tool_plan.as_dict()
                    log_event(f"Automatic browser tools preflight: profile={profile_key} tools={sorted((tool_plan.tools or {}).keys())} confidence={tool_plan.confidence:.3f} method={tool_plan.method!r}.")
            except Exception as tool_error:
                options['browser_tool_plan']={'tools':{},'confidence':0.0,'tool_scores':{},'method':str(tool_error)}
                log_event(f'Automatic browser tool detection fell back safely: {tool_error!r}.')
            # Paint-only real preflight: resolve stale palette-only saved
''')

replace_once('DrawBot.py', '''            log_event(f"Draw preflight options resolved: area={area} source={getattr(self.original, 'size', None)} profile={self.game.get()!r} paint_profile={paint_profile!r} palette_points={len(palette)} {_resource_log_text(options)}.")
            # Real tool actions were previously built only for preview planning,
            # leaving real drawing with an empty action list. Resolve them here.
            if paint_profile and options.get('effective_paint_tool',options.get('paint_tool'))!='Use current tool':
                from PaintTools import build_tool_actions
                options['tool_actions']=build_tool_actions(options.get('effective_paint_tool',options['paint_tool']),current_client_rect=current_client)
                for kind,position in options['tool_actions']:
                    x,y=position
                    if area[0]<=x<=area[0]+area[2] and area[1]<=y<=area[1]+area[3]:
                        raise ValueError(f'The calibrated Paint {kind} control overlaps the drawing area. Recalibrate Paint tools.')
            options['fill_tool_actions']=[];options['fill_restore_actions']=[]
            options['fill_unavailable_reason']=''
            if (options.get('background_fill')!='Off' or options.get('use_region_fill_engine')) and not bypasses_palette(self):
                if paint_profile and options.get('paint_tool') not in ('Use current tool','Eraser'):
                    try:
                        from PaintTools import build_tool_actions
                        options['fill_tool_actions']=build_tool_actions('Fill',current_client_rect=current_client)
                        options['fill_restore_actions']=list(options.get('tool_actions',[]))
                    except (OSError,ValueError) as error:
                        options['fill_unavailable_reason']=str(error)
                elif not paint_profile:
                    try:
                        from AppTools import build_tool_action
                        profile_key=PROFILES[self.game.get()][0]
                        options['fill_tool_actions']=[build_tool_action(profile_key,'Fill',current_client)]
                        options['fill_restore_actions']=[build_tool_action(profile_key,'Brush',current_client)]
                    except (OSError,ValueError) as error:
                        options['fill_unavailable_reason']=str(error)
                options['fill_tool_available']=bool(options.get('fill_tool_actions') and options.get('fill_restore_actions'))
                for kind,position in options.get('fill_tool_actions',[])+options.get('fill_restore_actions',[]):
                    x,y=position
                    if area[0]<=x<=area[0]+area[2] and area[1]<=y<=area[1]+area[3]:
                        raise ValueError(f'The calibrated {kind} control overlaps the drawing area. Recalibrate application tools.')
''', '''            log_event(f"Draw preflight options resolved: area={area} source={getattr(self.original, 'size', None)} profile={self.game.get()!r} paint_profile={paint_profile!r} palette_points={len(palette)} {_resource_log_text(options)}.")
            # Real tool actions were previously built only for preview planning,
            # leaving real drawing with an empty action list. Resolve them here.
            auto_browser_tool_plan=options.get('browser_tool_plan') or {}
            if paint_profile and options.get('effective_paint_tool',options.get('paint_tool'))!='Use current tool':
                from PaintTools import build_tool_actions
                options['tool_actions']=build_tool_actions(options.get('effective_paint_tool',options['paint_tool']),current_client_rect=current_client)
                for kind,position in options['tool_actions']:
                    x,y=position
                    if area[0]<=x<=area[0]+area[2] and area[1]<=y<=area[1]+area[3]:
                        raise ValueError(f'The calibrated Paint {kind} control overlaps the drawing area. Recalibrate Paint tools.')
            elif not paint_profile:
                try:
                    from BrowserToolLayout import build_browser_tool_action
                    options['tool_actions']=[build_browser_tool_action(auto_browser_tool_plan,'Brush')]
                except (OSError,ValueError):
                    pass
            options['fill_tool_actions']=[];options['fill_restore_actions']=[]
            options['fill_unavailable_reason']=''
            if (options.get('background_fill')!='Off' or options.get('use_region_fill_engine')) and not bypasses_palette(self):
                if paint_profile and options.get('paint_tool') not in ('Use current tool','Eraser'):
                    try:
                        from PaintTools import build_tool_actions
                        options['fill_tool_actions']=build_tool_actions('Fill',current_client_rect=current_client)
                        options['fill_restore_actions']=list(options.get('tool_actions',[]))
                    except (OSError,ValueError) as error:
                        options['fill_unavailable_reason']=str(error)
                elif not paint_profile:
                    try:
                        from AppTools import build_tool_action
                        profile_key=PROFILES[self.game.get()][0]
                        options['fill_tool_actions']=[build_tool_action(profile_key,'Fill',current_client)]
                        options['fill_restore_actions']=[build_tool_action(profile_key,'Brush',current_client)]
                    except (OSError,ValueError) as error:
                        options['fill_unavailable_reason']=str(error)
                        try:
                            from BrowserToolLayout import build_browser_tool_action
                            options['fill_tool_actions']=[build_browser_tool_action(auto_browser_tool_plan,'Fill')]
                            options['fill_restore_actions']=[build_browser_tool_action(auto_browser_tool_plan,'Brush')]
                            options['fill_unavailable_reason']=''
                        except (OSError,ValueError):
                            pass
                options['fill_tool_available']=bool(options.get('fill_tool_actions') and options.get('fill_restore_actions'))
                for kind,position in options.get('fill_tool_actions',[])+options.get('fill_restore_actions',[]):
                    x,y=position
                    if area[0]<=x<=area[0]+area[2] and area[1]<=y<=area[1]+area[3]:
                        raise ValueError(f'The calibrated {kind} control overlaps the drawing area. Recalibrate application tools.')
''')

replace_once('DrawBot.py', '''                if not paint_profile:
                    try:
                        from AppTools import load_calibration as load_app_tool_calibration
                        tool_data=load_app_tool_calibration(profile_key)
                    except (OSError,ValueError,TypeError):
                        tool_data={'tools':{}}
                clear_strategy=resolve_clear_strategy(
''', '''                if not paint_profile:
                    try:
                        from AppTools import load_calibration as load_app_tool_calibration
                        tool_data=load_app_tool_calibration(profile_key)
                    except (OSError,ValueError,TypeError):
                        tool_data={'tools':{}}
                    merged_tools=dict(tool_data.get('tools',{}) or {})
                    for tool_name,tool_position in (auto_browser_tool_plan.get('tools') or {}).items():
                        merged_tools.setdefault(tool_name,tool_position)
                    tool_data={'tools':merged_tools}
                clear_strategy=resolve_clear_strategy(
''')

replace_once('DrawBot.py', '''                if clear_strategy.strategy in ('native-clear','eraser-sweep'):
                    from AppTools import build_tool_action
                    if clear_strategy.strategy=='native-clear':
                        options['canvas_clear_actions']=[build_tool_action(profile_key,'Clear',current_client)]
                    else:
                        options['canvas_clear_actions']=[build_tool_action(profile_key,'Eraser',current_client)]
                        options['canvas_clear_restore_actions']=[build_tool_action(profile_key,'Brush',current_client)]
                    for kind,position in options['canvas_clear_actions']+options['canvas_clear_restore_actions']:
''', '''                if clear_strategy.strategy in ('native-clear','eraser-sweep'):
                    try:
                        from AppTools import build_tool_action
                        if clear_strategy.strategy=='native-clear':
                            options['canvas_clear_actions']=[build_tool_action(profile_key,'Clear',current_client)]
                        else:
                            options['canvas_clear_actions']=[build_tool_action(profile_key,'Eraser',current_client)]
                            options['canvas_clear_restore_actions']=[build_tool_action(profile_key,'Brush',current_client)]
                    except (OSError,ValueError):
                        from BrowserToolLayout import build_browser_tool_action
                        if clear_strategy.strategy=='native-clear':
                            options['canvas_clear_actions']=[build_browser_tool_action(auto_browser_tool_plan,'Clear')]
                        else:
                            options['canvas_clear_actions']=[build_browser_tool_action(auto_browser_tool_plan,'Eraser')]
                            options['canvas_clear_restore_actions']=[build_browser_tool_action(auto_browser_tool_plan,'Brush')]
                    for kind,position in options['canvas_clear_actions']+options['canvas_clear_restore_actions']:
''')

# PyInstaller needs the runtime-imported module explicitly.
replace_once('build_exe.py',
    "        '--hidden-import', 'BrowserBrushSize',\n",
    "        '--hidden-import', 'BrowserBrushSize',\n        '--hidden-import', 'BrowserToolLayout',\n")

# Profile copy now reflects automatic fail-closed Gartic tool inference.
app_tools = read('AppTools.py')
app_tools = app_tools.replace(
    '"gartic-phone": {"brush": True, "fill": True, "eraser": True, "clear": True, "note": "Current layout: Brush is top-left, Eraser top-right, Fill is row 4 right. Coordinates are still user-calibrated and anchored; recalibrate after zoom/layout changes."},',
    '"gartic-phone": {"brush": True, "fill": True, "eraser": True, "clear": True, "note": "Brush, Fill, Eraser and Clear can be inferred automatically after browser visual preflight; manual anchored calibration remains the fallback."},')
app_tools = app_tools.replace(
    '"gartic-io": {"brush": True, "fill": True, "eraser": True, "clear": True, "note": "Tool positions are profile-specific and must be calibrated."},',
    '"gartic-io": {"brush": True, "fill": True, "eraser": True, "clear": True, "note": "Uses the conservative Gartic browser tool detector when the verified layout matches; manual calibration remains the fallback."},')
write('AppTools.py', app_tools)

write('test_browser_tool_layout_v10145.py', '''import unittest
from PIL import Image,ImageDraw
from BrowserToolLayout import build_browser_tool_action,plan_browser_tools
from Version import APP_VERSION,FILE_VERSION

class BrowserToolLayoutV10145Tests(unittest.TestCase):
    def mock(self):
        client=(0,0,1200,900);canvas=(200,160,900,630)
        image=Image.new('RGB',(1200,900),(236,236,236));draw=ImageDraw.Draw(image)
        x0,y0,x1,y1=canvas;w,h=x1-x0,y1-y0
        top_gap=max(22,min(int(900*.055),int(h*.14)));right_gap=max(26,min(int(1200*.055),int(w*.18)))
        row=max(26,min(int(h*.115),int(900*.090)))
        points={'Brush':(x0+int(w*.060),y0-top_gap),'Eraser':(x1-int(w*.060),y0-top_gap),'Fill':(x1+right_gap,y0+int(row*1.15)),'Clear':(x1+right_gap,y0+int(row*2.20))}
        for x,y in points.values():draw.ellipse((x-12,y-12,x+12,y+12),fill=(28,28,28))
        return image,client,canvas
    def test_version(self):
        self.assertEqual((APP_VERSION,FILE_VERSION),('1.0.145-rc2','1.0.145'))
    def test_gartic_phone_tools(self):
        image,client,canvas=self.mock();plan=plan_browser_tools('gartic-phone',image,client,canvas_box=canvas)
        self.assertGreaterEqual(plan.confidence,.58);self.assertEqual(set(plan.tools),{'Brush','Fill','Eraser','Clear'})
    def test_gartic_io_tools_and_action(self):
        image,client,canvas=self.mock();plan=plan_browser_tools('gartic-io',image,client,canvas_box=canvas)
        kind,pos=build_browser_tool_action(plan.as_dict(),'Brush');self.assertEqual(kind,'brush');self.assertEqual(tuple(pos),plan.tools['Brush'])
    def test_low_confidence_fails_closed(self):
        with self.assertRaises(ValueError):build_browser_tool_action({'tools':{'Brush':[10,10]},'confidence':.2},'Brush')

if __name__=='__main__':unittest.main()
''')

notes='''# Image Draw Bot v1.0.145-rc2 — Gartic Auto Tools\n\n- Add conservative automatic Brush, Fill, Eraser and Clear selection for verified Gartic Phone layouts.\n- Extend the same fail-closed tool-layout path and automatic brush-size presets to Gartic.io.\n- Prefer manual anchored tool calibration when present, then fall back to visually verified browser-tool inference.\n- Restore Brush automatically after Fill and Eraser-based canvas clearing.\n- Keep multi-size Auto Brush bounded by BrowserBrushSize and CanvasGuard.\n- Refuse guessed tool clicks when browser-layout confidence is low.\n- Preserve the rc1 Total Draw Timer, automatic pixel brush width, Paint UI Automation sizing, profile isolation and ETA calibration.\n'''
write('RELEASE-NOTES-v1.0.145-rc2.md', notes)

for rel in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    text=read(rel)
    if not text.startswith('# Image Draw Bot v1.0.145-rc2'):
        write(rel, notes+'\n'+text)

# The external follow-up trigger will modify this file again so GitHub runs the
# release workflow from a non-GITHUB_TOKEN commit.
write('.github/release-build-trigger','1.0.145-rc2 gartic-auto-tools prepared\n')

# Remove the one-shot helper before committing the prepared release source.
(ROOT/'.github/workflows/prepare-rc2.yml').unlink(missing_ok=True)
(ROOT/'.github/scripts/prepare_rc2.py').unlink(missing_ok=True)
