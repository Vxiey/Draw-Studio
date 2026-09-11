from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OLD='1.0.144-rc13'
NEW='1.0.144-rc14'


def path(name):
    return ROOT/name


def read(name):
    return path(name).read_text(encoding='utf-8')


def write(name, text):
    path(name).write_text(text,encoding='utf-8')


def replace_once(name, old, new):
    text=read(name)
    count=text.count(old)
    if count!=1:
        raise RuntimeError(f'{name}: expected exactly one match, found {count}: {old[:90]!r}')
    write(name,text.replace(old,new,1))


def replace_count(name, old, new, minimum=1):
    text=read(name);count=text.count(old)
    if count<minimum:
        raise RuntimeError(f'{name}: expected at least {minimum} matches, found {count}: {old[:90]!r}')
    write(name,text.replace(old,new))
    return count


# ---------------------------------------------------------------------------
# Automatic pixel brush baseline.
# ---------------------------------------------------------------------------
auto_brush = '''\"\"\"Automatic pixel brush-width selection for Image Draw Bot.

The selector is deliberately conservative. It chooses a baseline from the
actual image and target canvas, while AdaptiveBrushEngine may still select
smaller verified brushes for contours/details/corrections. No mouse input is
performed here.
\"\"\"
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageFilter, ImageStat


@dataclass(frozen=True)
class AutoBrushDecision:
    brush_px: int
    classification: str
    edge_density: float
    color_complexity: float
    target_size: tuple[int, int]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            'brush_px': int(self.brush_px),
            'classification': str(self.classification),
            'edge_density': round(float(self.edge_density),4),
            'color_complexity': round(float(self.color_complexity),4),
            'target_size': tuple(map(int,self.target_size)),
            'reason': str(self.reason),
        }


def _target_size(image: Image.Image, target_size=None) -> tuple[int,int]:
    try:
        w,h=map(int,target_size)
        if w>0 and h>0:return w,h
    except Exception:
        pass
    return max(1,int(image.width)),max(1,int(image.height))


def _metrics(image: Image.Image) -> tuple[float,float]:
    rgb=image.convert('RGB')
    w=max(24,min(144,rgb.width));h=max(24,min(144,rgb.height))
    sample=rgb.resize((w,h),Image.Resampling.BILINEAR)
    edge=float(ImageStat.Stat(sample.convert('L').filter(ImageFilter.FIND_EDGES)).mean[0])/255.0
    palette=rgb.resize((w,h),Image.Resampling.NEAREST).quantize(colors=32,method=Image.Quantize.MEDIANCUT)
    used=sum(1 for value in palette.histogram() if value)
    colors=min(1.0,used/32.0)
    return max(0.0,min(1.0,edge)),max(0.0,min(1.0,colors))


def resolve_brush_width(image: Image.Image | None, *, target_size=None,
                        draw_quality: str='', render_preset: str='', render_style: str='',
                        outline: bool=False, subject_focus: str='Off', profile_key: str='',
                        speed: str='', quality: str='') -> AutoBrushDecision:
    if image is None:
        return AutoBrushDecision(1,'safe-default',0.0,0.0,(1,1),'No image is loaded; use the safest 1 px baseline.')
    target=_target_size(image,target_size)
    area=max(1,target[0]*target[1]);longest=max(target)
    dq=str(draw_quality or '')
    if 'Pixel Accurate' in dq:
        return AutoBrushDecision(1,'pixel-accurate',1.0,1.0,target,'Pixel Accurate keeps a 1 px baseline for exact source geometry.')
    if outline or str(subject_focus or 'Off')!='Off':
        return AutoBrushDecision(1,'protected-detail',1.0,1.0,target,'Outline/subject-preserving drawing uses the finest baseline.')

    edge,color=_metrics(image)
    detail_score=min(1.0,edge*.72+color*.28)
    if longest<=520:base=1
    elif longest<=900:base=2
    elif longest<=1400:base=3
    elif longest<=2000:base=4
    else:base=5

    classification='balanced';reason='Balanced baseline from target pixel dimensions and image complexity.'
    if detail_score>=.40:
        base=max(1,base-1);classification='detail-heavy'
        reason='High edge/color complexity: use a smaller baseline to preserve details.'
    elif detail_score<=.17 and area>=220_000:
        base=min(7,base+1);classification='flat-shape'
        reason='Large simple color regions: a wider baseline is safe and faster.'

    if str(render_preset or '')=='Extra fast' and classification!='detail-heavy':
        base=min(7,base+1);reason+=' Extra fast permits one wider safe level.'
    if str(quality or '') in ('Best','Ultra') or dq in ('High likeness','Maximum likeness'):
        base=max(1,base-1);reason+=' High-likeness quality nudges the baseline finer.'
    if str(render_style or '')=='Portrait / shaded':
        base=max(1,base-1);reason+=' Portrait/shaded rendering protects fine facial and tonal structure.'

    # Microsoft Paint supports a wide size slider, but very large Pencil sizes
    # are destructive for automatic image recreation. Keep Auto conservative.
    cap=6 if str(profile_key or '')=='microsoft-paint' else 8
    base=max(1,min(cap,int(base)))
    return AutoBrushDecision(base,classification,edge,color,target,reason)
'''
write('AutoBrushWidth.py',auto_brush)

# ---------------------------------------------------------------------------
# Paint UI Automation: set the requested/automatic pixel size rather than 1 px.
# ---------------------------------------------------------------------------
replace_once('PaintPreparation.py',
"def automation(handle, *, element=None, action=None, cancelled=lambda:False):",
"def automation(handle, *, element=None, action=None, size_px=1, cancelled=lambda:False):")
replace_once('PaintPreparation.py',
"""        elif action=='size':
            command+=r'''\n$pattern=$null
if(!$e.TryGetCurrentPattern([System.Windows.Automation.RangeValuePattern]::Pattern,[ref]$pattern)) {throw 'Paint size control does not expose RangeValuePattern.'}
$p=[System.Windows.Automation.RangeValuePattern]$pattern
if($p.Current.Minimum -gt 1 -or $p.Current.Maximum -lt 1){throw 'Paint size does not expose a 1 px value.'}
$p.SetValue(1)
if([Math]::Abs($p.Current.Value-1) -gt 0.001){throw 'Paint did not accept 1 px.'}
'''
""",
"""        elif action=='size':
            target_size=max(1,min(50,int(size_px or 1)))
            command+=f'$targetSize={target_size}\\n'+r'''\n$pattern=$null
if(!$e.TryGetCurrentPattern([System.Windows.Automation.RangeValuePattern]::Pattern,[ref]$pattern)) {throw 'Paint size control does not expose RangeValuePattern.'}
$p=[System.Windows.Automation.RangeValuePattern]$pattern
if($p.Current.Minimum -gt $targetSize -or $p.Current.Maximum -lt $targetSize){throw ('Paint size does not expose the requested '+$targetSize+' px value.')}
$p.SetValue($targetSize)
if([Math]::Abs($p.Current.Value-$targetSize) -gt 0.001){throw ('Paint did not accept '+$targetSize+' px.')}
'''
""")
replace_once('PaintPreparation.py',
"def prepare_tool_controls(handle, *, cancelled=lambda:False, backend=automation):\n    \"\"\"Prepare Pencil/1 px without ever opening Paint Edit colors.",
"def prepare_tool_controls(handle, *, brush_px=1, cancelled=lambda:False, backend=automation):\n    \"\"\"Prepare Pencil and the requested verified pixel size without opening Paint Edit colors.")
replace_once('PaintPreparation.py',
"    backend(handle,element=size,action='size',cancelled=cancelled)\n    return True",
"    backend(handle,element=size,action='size',size_px=max(1,min(50,int(brush_px or 1))),cancelled=cancelled)\n    return True")
replace_once('PaintPreparation.py',
"def prepare_controls(handle, *, cancelled=lambda:False, backend=automation):\n    \"\"\"Backward-compatible full Paint tool + exact-RGB preparation.\"\"\"\n    prepare_tool_controls(handle,cancelled=cancelled,backend=backend)",
"def prepare_controls(handle, *, brush_px=1, cancelled=lambda:False, backend=automation):\n    \"\"\"Backward-compatible full Paint tool + exact-RGB preparation.\"\"\"\n    prepare_tool_controls(handle,brush_px=brush_px,cancelled=cancelled,backend=backend)")

# ---------------------------------------------------------------------------
# DrawBot: Auto brush setting + actual/live draw timer.
# ---------------------------------------------------------------------------
replace_once('DrawBot.py',
"        self.draw_time_text = tk.StringVar(value='Estimated draw time appears after Build preview.')\n        self.preview_diagnostics_text = tk.StringVar(value='Preview diagnostics appear after Build preview.')",
"        self.draw_time_text = tk.StringVar(value='Estimated draw time appears after Build preview.')\n        self.draw_live_time_text = tk.StringVar(value='Drawing timer: starts when drawing begins.')\n        self.total_draw_time_text = tk.StringVar(value='Total draw time: —')\n        self.preview_diagnostics_text = tk.StringVar(value='Preview diagnostics appear after Build preview.')")
replace_once('DrawBot.py',"        self.brush_px = tk.StringVar(value='3')","        self.brush_px = tk.StringVar(value='Auto')")
replace_once('DrawBot.py',
"""            for key,var,low,high in [('brush_px',self.brush_px,1,50),('max_seconds',self.max_seconds,5,3600)]:
                raw=data.get(key)
                if type(raw) is int and low<=raw<=high:var.set(str(raw))
                elif isinstance(raw,str) and raw.isdecimal() and low<=int(raw)<=high:var.set(str(int(raw)))
""",
"""            raw_brush=data.get('brush_px','Auto')
            if isinstance(raw_brush,str) and raw_brush.strip().casefold()=='auto':
                self.brush_px.set('Auto')
            elif type(raw_brush) is int and 1<=raw_brush<=50:
                self.brush_px.set(str(raw_brush))
            elif isinstance(raw_brush,str) and raw_brush.isdecimal() and 1<=int(raw_brush)<=50:
                self.brush_px.set(str(int(raw_brush)))
            raw_limit=data.get('max_seconds')
            if type(raw_limit) is int and 5<=raw_limit<=3600:self.max_seconds.set(str(raw_limit))
            elif isinstance(raw_limit,str) and raw_limit.isdecimal() and 5<=int(raw_limit)<=3600:self.max_seconds.set(str(int(raw_limit)))
""")
replace_once('DrawBot.py',
"""        try:
            brush=int(self.brush_px.get());limit=int(self.max_seconds.get())
        except (TypeError,ValueError,tk.TclError) as error:
            raise ValueError('Brush width and time limit must be whole numbers.') from error
        if not 1<=brush<=50 or not 5<=limit<=3600:
            raise ValueError('Brush width: 1–50 px. Time limit: 5–3600 seconds.')
""",
"""        brush_raw=str(self.brush_px.get()).strip()
        brush_auto=brush_raw.casefold()=='auto'
        try:
            brush=None if brush_auto else int(brush_raw)
            limit=int(self.max_seconds.get())
        except (TypeError,ValueError,tk.TclError) as error:
            raise ValueError('Brush width must be Auto or a whole number, and time limit must be a whole number.') from error
        if (brush is not None and not 1<=brush<=50) or not 5<=limit<=3600:
            raise ValueError('Brush width: Auto or 1–50 px. Time limit: 5–3600 seconds.')
        auto_brush_width_meta=None
""")
replace_once('DrawBot.py',
"""        validate_tool_strategy(tool_strategy)
        validate_edge_behavior(edge_behavior)
        paint_profile=self.game.get()=='Microsoft Paint'
        selected_tool=self.paint_tool.get() if paint_profile else 'Use current tool'
""",
"""        validate_tool_strategy(tool_strategy)
        validate_edge_behavior(edge_behavior)
        paint_profile=self.game.get()=='Microsoft Paint'
        if brush is None:
            from AutoBrushWidth import resolve_brush_width
            _auto_brush=resolve_brush_width(
                getattr(self,'original',None),target_size=area_size,draw_quality=draw_quality,
                render_preset=getattr(getattr(self,'render_preset',None),'get',lambda:'Auto')(),
                render_style=render_style,outline=bool(self.outline.get()),
                subject_focus=self.subject_focus.get() if hasattr(self,'subject_focus') else 'Off',
                profile_key=PROFILES[self.game.get()][0],speed=speed,quality=quality)
            brush=int(_auto_brush.brush_px);auto_brush_width_meta=_auto_brush.as_dict()
        selected_tool=self.paint_tool.get() if paint_profile else 'Use current tool'
""")
replace_once('DrawBot.py',
"'sketch_detail':getattr(getattr(self,'sketch_detail',None),'get',lambda:'Auto')(),'brush_px':brush,'canvas_edge_verification':'Auto'",
"'sketch_detail':getattr(getattr(self,'sketch_detail',None),'get',lambda:'Auto')(),'brush_px':brush,'brush_px_requested':brush_raw,'auto_brush_width_meta':auto_brush_width_meta,'canvas_edge_verification':'Auto'")

# Snapshot Paint's desired brush on the UI thread before the worker begins.
replace_once('DrawBot.py',
"        _skip_exact_rgb=bool(bypasses_palette(self) or _black_contour_sketch)\n        # Snapshot an explicit user-selected canvas on the UI thread.",
"""        _skip_exact_rgb=bool(bypasses_palette(self) or _black_contour_sketch)
        _paint_brush_meta=None
        try:
            _paint_brush_raw=str(self.brush_px.get()).strip()
            if _paint_brush_raw.casefold()=='auto':
                from AutoBrushWidth import resolve_brush_width
                _target_size=None
                try:
                    if len(self.corners)==2:
                        _area=self.area();_target_size=(int(_area[2]),int(_area[3]))
                except Exception:
                    _target_size=None
                _decision=resolve_brush_width(
                    self.original,target_size=_target_size,
                    draw_quality=getattr(getattr(self,'draw_quality',None),'get',lambda:'High likeness')(),
                    render_preset=getattr(getattr(self,'render_preset',None),'get',lambda:'Auto')(),
                    render_style=getattr(getattr(self,'render_style',None),'get',lambda:'Auto')(),
                    outline=_black_contour_sketch,
                    subject_focus=getattr(getattr(self,'subject_focus',None),'get',lambda:'Off')(),
                    profile_key='microsoft-paint',speed=normalize_speed(self.speed.get()),quality=self.quality.get())
                _paint_brush_px=int(_decision.brush_px);_paint_brush_meta=_decision.as_dict()
            else:
                _paint_brush_px=int(_paint_brush_raw)
                if not 1<=_paint_brush_px<=50:raise ValueError('out of range')
        except (TypeError,ValueError,tk.TclError):
            self.paint_start_request=None
            self.status.set('Brush width must be Auto or 1–50 px before Paint preparation can start.')
            return False
        # Snapshot an explicit user-selected canvas on the UI thread.""")
replace_once('DrawBot.py',
"                prepare_tool_controls(int(candidate['handle']),cancelled=self.stop.is_set)",
"                prepare_tool_controls(int(candidate['handle']),brush_px=_paint_brush_px,cancelled=self.stop.is_set)")
replace_once('DrawBot.py',
"                result['exact_colors_reused']=bool(exact_reused)\n                result['start_request']=request",
"                result['exact_colors_reused']=bool(exact_reused)\n                result['prepared_brush_px']=int(_paint_brush_px)\n                result['auto_brush_width_meta']=dict(_paint_brush_meta or {})\n                result['start_request']=request")
replace_once('DrawBot.py',
"        self.status.set('Preparing Paint: pencil, 1 px, canvas, palette and RGB color controls…')",
"        self.status.set(f'Preparing Paint: pencil, {_paint_brush_px} px, canvas, palette and RGB color controls…')")

# Runtime timer starts exactly where the existing measured final-draw timing starts.
replace_once('DrawBot.py',
"""        execution_measure_started=clock()
        if (plan['options'].get('paint_profile') or stroke_delivery.profile_key in ('gartic-phone','skribbl','skribbl-fast','sketchheads')) and not dry_run:
""",
"""        execution_measure_started=clock()
        _draw_timer_last=[execution_measure_started]
        try:_planned_draw_seconds=max(0.0,float((plan.get('draw_time_estimate') or {}).get('projected_seconds') or plan.get('estimate') or 0.0))
        except Exception:_planned_draw_seconds=0.0
        def report_draw_timer(*,force=False,completed=False):
            if dry_run or execution_measure_started is None:return
            now=clock()
            if not force and now-_draw_timer_last[0]<.50:return
            _draw_timer_last[0]=now
            elapsed=max(0.0,now-execution_measure_started)
            total_paths=max(1,int(plan.get('count') or 0))
            if completed:
                predicted=elapsed;remaining=0.0
            else:
                path_projection=(elapsed*total_paths/max(1,done)) if done>0 else 0.0
                if path_projection>0:
                    weight=min(.65,max(.15,done/total_paths))
                    predicted=max(elapsed,((_planned_draw_seconds*(1.0-weight)+path_projection*weight) if _planned_draw_seconds>0 else path_projection))
                else:
                    predicted=max(elapsed,_planned_draw_seconds)
                remaining=max(0.0,predicted-elapsed)
            report('draw_timer',{'elapsed_seconds':elapsed,'remaining_seconds':remaining,
                                  'predicted_total_seconds':predicted,'done':int(done),'total':int(plan.get('count') or 0),
                                  'state':'completed' if completed else 'running'})
        report_draw_timer(force=True)
        if (plan['options'].get('paint_profile') or stroke_delivery.profile_key in ('gartic-phone','skribbl','skribbl-fast','sketchheads')) and not dry_run:
""")
progress_count=replace_count('DrawBot.py',"                        report('progress', (done, plan['count']))","                        report('progress', (done, plan['count']))\n                        report_draw_timer()",minimum=2)
if progress_count<2:raise RuntimeError('Expected progress timer hooks in at least two execution paths.')
replace_once('DrawBot.py',
"""            if isinstance(_correction_meta,dict) and int(_correction_meta.get('executed_paths',0) or 0)>0:
                execution_measure_completed_at=clock()
        runtime_safety.mark_completed()
""",
"""            if isinstance(_correction_meta,dict) and int(_correction_meta.get('executed_paths',0) or 0)>0:
                execution_measure_completed_at=clock()
        actual_draw_seconds=None
        if (not dry_run) and execution_measure_started is not None:
            actual_draw_seconds=max(.001,(execution_measure_completed_at or clock())-execution_measure_started)
            plan['options']['actual_draw_seconds']=round(actual_draw_seconds,4)
            report_draw_timer(force=True,completed=True)
            report('draw_time_actual',{'seconds':actual_draw_seconds,'paths':int(done),
                                       'correction_paths':int((plan['options'].get('post_draw_correction_meta') or {}).get('executed_paths',0) or 0)})
        runtime_safety.mark_completed()
""")
replace_once('DrawBot.py',
"            report('status', f'Finished locally: {done:,} brush strokes sent. Also verify the final result in the target application.')",
"""            try:
                from DrawTimeEstimate import format_duration
                _actual_label=format_duration(actual_draw_seconds or 0.0)
            except Exception:
                _actual_label=f'{float(actual_draw_seconds or 0.0):.1f}s'
            report('status', f'Finished locally: {done:,} brush strokes sent · total draw time {_actual_label}. Also verify the final result in the target application.')""")

# UI event handling for live/final timer.
replace_once('DrawBot.py',
"""                else:
                    self.status.set(f'Drawing: {done:,} / {total:,} brush strokes • Esc stops • F6 pauses')
        elif kind=='upscaled':
""",
"""                else:
                    self.status.set(f'Drawing: {done:,} / {total:,} brush strokes • Esc stops • F6 pauses')
        elif kind=='draw_timer':
            data=value if isinstance(value,dict) else {}
            try:
                from DrawTimeEstimate import format_duration
                elapsed=max(0.0,float(data.get('elapsed_seconds',0) or 0))
                remaining=max(0.0,float(data.get('remaining_seconds',0) or 0))
                predicted=max(elapsed,float(data.get('predicted_total_seconds',elapsed) or elapsed))
                if str(data.get('state') or '')=='completed':
                    self.draw_live_time_text.set(f'Drawing timer: {format_duration(elapsed)} elapsed · complete')
                else:
                    self.draw_live_time_text.set(f'Drawing timer: {format_duration(elapsed)} elapsed · ≈ {format_duration(remaining)} remaining · ≈ {format_duration(predicted)} total')
                    self.total_draw_time_text.set('Total draw time: drawing…')
            except (TypeError,ValueError,tk.TclError,AttributeError):
                pass
        elif kind=='draw_time_actual':
            data=value if isinstance(value,dict) else {}
            try:
                from DrawTimeEstimate import format_duration
                seconds=max(0.0,float(data.get('seconds',0) or 0))
                self.total_draw_time_text.set(f'Total draw time: {format_duration(seconds)}')
                self.draw_live_time_text.set(f'Drawing timer: completed in {format_duration(seconds)}')
            except (TypeError,ValueError,tk.TclError,AttributeError):
                pass
        elif kind=='upscaled':
""")
replace_once('DrawBot.py',
"""            try:self.draw_time_text.set('Estimated draw time appears after Build preview.')
            except (tk.TclError,AttributeError):pass
            DrawBotApp._queue_drop_in_start(self,_action,source_label=str(label))
""",
"""            try:self.draw_time_text.set('Estimated draw time appears after Build preview.')
            except (tk.TclError,AttributeError):pass
            try:self.draw_live_time_text.set('Drawing timer: starts when drawing begins.')
            except (tk.TclError,AttributeError):pass
            try:self.total_draw_time_text.set('Total draw time: —')
            except (tk.TclError,AttributeError):pass
            DrawBotApp._queue_drop_in_start(self,_action,source_label=str(label))
""")

# ---------------------------------------------------------------------------
# UI: make Auto explicit and keep timer visible before/after drawing.
# ---------------------------------------------------------------------------
replace_once('StudioUI.py',
"    numeric_row(step4, 'Brush width (px)', a.brush_px, 'Auto Brush baseline · verified sizes adapt to image detail.', width=70)",
"    numeric_row(step4, 'Brush width (px)', a.brush_px, 'Auto chooses a safe pixel baseline from the image/canvas; manual 1–50 px remains available.', width=84)")
replace_once('StudioUI.py',
"""    draw_time_side = label(step5, a.draw_time_text, muted=True, size=9, wraplength=270)
    draw_time_side.pack(anchor='w', pady=(0, 6))
""",
"""    draw_time_side = label(step5, a.draw_time_text, muted=True, size=9, wraplength=270)
    draw_time_side.pack(anchor='w', pady=(0, 3))
    draw_live_side = label(step5, a.draw_live_time_text, muted=True, size=9, wraplength=270)
    draw_live_side.pack(anchor='w', pady=(0, 2))
    total_draw_side = label(step5, a.total_draw_time_text, size=10, bold=True, wraplength=270)
    total_draw_side.pack(anchor='w', pady=(0, 6))
""")
replace_once('StudioUI.py',
"    label(text, var=a.draw_time_text, size=11, bold=True, fg_color=FIELD, corner_radius=8, wraplength=560).pack(anchor='w', pady=(7, 0))",
"""    label(text, var=a.draw_time_text, size=11, bold=True, fg_color=FIELD, corner_radius=8, wraplength=560).pack(anchor='w', pady=(7, 0))
    label(text, var=a.draw_live_time_text, size=10, fg_color=FIELD, corner_radius=8, wraplength=560).pack(anchor='w', pady=(5, 0))
    label(text, var=a.total_draw_time_text, size=11, bold=True, fg_color=FIELD, corner_radius=8, wraplength=560).pack(anchor='w', pady=(5, 0))""")

# ---------------------------------------------------------------------------
# ETA calibration: isolate learning by render mode/preset/quality/style as well
# as profile/tool/brush/color workflow.
# ---------------------------------------------------------------------------
cal=read('DrawTimeCalibration.py')
cal=cal.replace('VERSION = 2','VERSION = 3',1)
old_key='''def _key(options: dict[str, Any]) -> str:\n    base = _legacy_key(options)\n    tool = str(options.get("effective_paint_tool") or options.get("paint_tool") or options.get("tool_strategy") or "default").strip().lower().replace(" ", "-")\n    try:\n        brush = max(1, min(128, int(options.get("brush_px") or 1)))\n    except Exception:\n        brush = 1\n    workflow = str(options.get("custom_color_workflow") or "calibrated-palette").strip().lower().replace(" ", "-")\n    return f"{base}|tool={tool}|brush={brush}|color={workflow}"\n'''
new_key='''def _token(value: Any, fallback: str) -> str:\n    text=str(value or fallback).strip().lower().replace(" ", "-")\n    return text or fallback\n\n\ndef _v2_key(options: dict[str, Any]) -> str:\n    base = _legacy_key(options)\n    tool = _token(options.get("effective_paint_tool") or options.get("paint_tool") or options.get("tool_strategy"), "default")\n    try:\n        brush = max(1, min(128, int(options.get("brush_px") or 1)))\n    except Exception:\n        brush = 1\n    workflow = _token(options.get("custom_color_workflow"), "calibrated-palette")\n    return f"{base}|tool={tool}|brush={brush}|color={workflow}"\n\n\ndef _key(options: dict[str, Any]) -> str:\n    base=_v2_key(options)\n    mode=_token(options.get("drawing_mode") or options.get("mode"),"default")\n    preset=_token(options.get("render_preset"),"manual")\n    quality=_token(options.get("draw_quality"),"balanced")\n    style=_token(options.get("render_style"),"auto")\n    return f"{base}|mode={mode}|preset={preset}|quality={quality}|style={style}"\n'''
if old_key not in cal:raise RuntimeError('DrawTimeCalibration.py key function did not match current main')
cal=cal.replace(old_key,new_key,1)
cal=cal.replace('valid_version = version == VERSION or (accept_legacy_version and version == 1)',
                'valid_version = version == VERSION or (accept_legacy_version and version in (1,2))',1)
cal=cal.replace('''    item = db["profiles"].get(_key(options))\n    if not isinstance(item, dict):\n        item = db["profiles"].get(_legacy_key(options))\n''',
'''    item = db["profiles"].get(_key(options))\n    if not isinstance(item, dict):\n        item = db["profiles"].get(_v2_key(options))\n    if not isinstance(item, dict):\n        item = db["profiles"].get(_legacy_key(options))\n''',1)
cal=cal.replace('''    old = db["profiles"].get(key)\n    if not isinstance(old, dict):\n        old = db["profiles"].get(_legacy_key(options)) if isinstance(db["profiles"].get(_legacy_key(options)), dict) else {}\n''',
'''    old = db["profiles"].get(key)\n    if not isinstance(old, dict):\n        old = db["profiles"].get(_v2_key(options))\n    if not isinstance(old, dict):\n        old = db["profiles"].get(_legacy_key(options)) if isinstance(db["profiles"].get(_legacy_key(options)), dict) else {}\n''',1)
cal=cal.replace('''    legacy = _legacy_key(options)\n    existed = key in db["profiles"] or legacy in db["profiles"]\n    db["profiles"].pop(key, None)\n    db["profiles"].pop(legacy, None)\n''',
'''    v2 = _v2_key(options)\n    legacy = _legacy_key(options)\n    existed = key in db["profiles"] or v2 in db["profiles"] or legacy in db["profiles"]\n    db["profiles"].pop(key, None)\n    db["profiles"].pop(v2, None)\n    db["profiles"].pop(legacy, None)\n''',1)
cal=cal.replace('Step 9 isolates persisted timing by drawing profile.','Timing data is isolated by drawing profile and execution policy.')
write('DrawTimeCalibration.py',cal)

# ---------------------------------------------------------------------------
# Regression tests.
# ---------------------------------------------------------------------------
tests='''import tempfile\nimport unittest\nfrom pathlib import Path\nfrom types import SimpleNamespace\nfrom PIL import Image, ImageDraw\n\nfrom AutoBrushWidth import resolve_brush_width\nfrom DrawBot import DrawBotApp\nfrom DrawTimeCalibration import correction_for,record_sample\nfrom PaintPreparation import prepare_tool_controls\n\n\nclass Value:\n    def __init__(self,value=''):self.value=value\n    def set(self,value):self.value=value\n    def get(self):return self.value\n\n\nclass AutoBrushAndTimerTests(unittest.TestCase):\n    def test_pixel_accurate_auto_brush_is_one_pixel(self):\n        im=Image.new('RGB',(1400,900),'white')\n        decision=resolve_brush_width(im,target_size=(1400,900),draw_quality='Pixel Accurate',profile_key='microsoft-paint')\n        self.assertEqual(decision.brush_px,1)\n        self.assertEqual(decision.classification,'pixel-accurate')\n\n    def test_flat_large_image_can_use_wider_auto_baseline(self):\n        im=Image.new('RGB',(1600,1000),'white');ImageDraw.Draw(im).rectangle((100,100,1500,900),fill=(220,40,40))\n        decision=resolve_brush_width(im,target_size=(1600,1000),render_preset='Extra fast',profile_key='microsoft-paint')\n        self.assertGreaterEqual(decision.brush_px,3)\n        self.assertLessEqual(decision.brush_px,6)\n\n    def test_paint_preparation_passes_requested_pixel_size_to_uia(self):\n        main=[dict(name='Pencil',kind='ControlType.Button',rect=[10,10,30,30],value='',label=''),\n              dict(name='Size',kind='ControlType.Slider',rect=[40,40,60,200],value='',label='')]\n        seen=[]\n        def backend(handle,**kw):\n            if kw.get('action'):seen.append((kw.get('action'),kw.get('size_px')))\n            return main\n        self.assertTrue(prepare_tool_controls(42,brush_px=4,backend=backend))\n        self.assertIn(('size',4),seen)\n\n    def test_timing_learning_isolated_by_render_mode(self):\n        base=dict(profile_key='microsoft-paint',speed='Balanced',precision='High',use_region_fill_engine=True,\n                  effective_paint_tool='Pencil',brush_px=2,custom_color_workflow='Adaptive exact (recommended)',\n                  render_preset='Auto',draw_quality='High likeness',render_style='Auto')\n        with tempfile.TemporaryDirectory() as tmp:\n            db=Path(tmp)/'timing.json'\n            a=dict(base,drawing_mode='Shape paths')\n            b=dict(base,drawing_mode='Smart paths')\n            self.assertTrue(record_sample(a,10,14,path=db)['recorded'])\n            self.assertGreater(correction_for(a,path=db)['samples'],0)\n            self.assertEqual(correction_for(b,path=db)['samples'],0)\n\n    def test_actual_draw_time_event_persists_total_label(self):\n        app=SimpleNamespace(total_draw_time_text=Value(),draw_live_time_text=Value())\n        DrawBotApp._handle_event(app,'draw_time_actual',{'seconds':157.2,'paths':20})\n        self.assertEqual(app.total_draw_time_text.get(),'Total draw time: 2m 37s')\n        self.assertIn('completed in 2m 37s',app.draw_live_time_text.get())\n\n\nif __name__=='__main__':unittest.main()\n'''
write('test_auto_brush_total_time_v10144.py',tests)

# ---------------------------------------------------------------------------
# rc14 release metadata. Keep historical rc13 notes/history intact.
# ---------------------------------------------------------------------------
for p in ROOT.rglob('*'):
    if not p.is_file():continue
    rel=p.relative_to(ROOT).as_posix()
    if rel.startswith('.git/') or rel.startswith('.github/') or rel=='RELEASE-NOTES-v1.0.144-rc13.md' or rel in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
        continue
    if rel.startswith('RELEASE-NOTES-'):continue
    try:text=p.read_text(encoding='utf-8')
    except (UnicodeDecodeError,OSError):continue
    if OLD in text:
        p.write_text(text.replace(OLD,NEW),encoding='utf-8')

notes='''# Image Draw Bot v1.0.144-rc14 — Total Draw Timer & Automatic Pixel Brush\n\n- Add a visible live drawing timer with elapsed time, estimated remaining time and projected total while a real drawing is running.\n- Show the exact measured **Total draw time** after a completed drawing and keep it visible in Safety & draw and the preview workspace.\n- Make Brush width support **Auto** as the default while preserving manual 1–50 px input and old saved numeric settings.\n- Select the automatic baseline from target canvas size plus image edge/color complexity, with 1 px retained for Pixel Accurate and protected-detail workflows.\n- Microsoft Paint preparation now sets the requested/automatic Pencil pixel size through verified UI Automation RangeValuePattern instead of always forcing 1 px.\n- Keep browser adaptive brush switching safe: only verified controls are used, with smallest verified brushes reserved for fine details/corrections.\n- Isolate learned ETA calibration by rendering mode, preset, draw quality and render style in addition to profile/tool/brush/color workflow.\n- Existing CanvasGuard, calibration, cancellation and manual brush fallbacks remain mandatory.\n'''
write('RELEASE-NOTES-v1.0.144-rc14.md',notes)
history_header=notes+'\n'
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    text=read(name)
    if 'v1.0.144-rc14' not in text:write(name,history_header+text)

print('rc14 patch prepared successfully')
