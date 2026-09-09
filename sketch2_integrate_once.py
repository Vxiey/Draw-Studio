from pathlib import Path
import re

ROOT=Path('.')


def replace_once(path, old, new):
    p=ROOT/path
    text=p.read_text(encoding='utf-8')
    count=text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one anchor, found {count}')
    p.write_text(text.replace(old,new,1),encoding='utf-8')


def write(path, text):
    (ROOT/path).write_text(text.rstrip()+"\n",encoding='utf-8')

# ---------------------------------------------------------------------------
# Sketch 2.0: Paint-first deterministic structure extraction.
# ---------------------------------------------------------------------------
write('Sketch2Planner.py', r'''"""Sketch 2.0 structure extraction for Draw Studio v1.0.131-beta.

Paint-first deterministic planner. It combines luminance and colour-boundary
edges, protects small high-contrast components and removes isolated noise. It
contains no native input, AI, ML or OCR. Browser/Gartic sketch routing remains
in the legacy SketchPlanner/GarticSketchPaths path.
"""
from __future__ import annotations

from collections import deque
from typing import Callable
import numpy as np
from PIL import Image, ImageFilter

SKETCH2_DETAILS=("Simple","Balanced","Detailed")

_PROFILES={
    "Simple": dict(blur=1.8, percentile=82.0, floor=34.0, min_component=10, protect_factor=1.75),
    "Balanced": dict(blur=1.25, percentile=77.0, floor=27.0, min_component=6, protect_factor=1.60),
    "Detailed": dict(blur=.85, percentile=72.0, floor=20.0, min_component=3, protect_factor=1.45),
}


def _flatten(image: Image.Image) -> Image.Image:
    rgba=image.convert('RGBA')
    flat=Image.new('RGBA',rgba.size,'white');flat.alpha_composite(rgba)
    return flat.convert('RGB')


def _nms(mag: np.ndarray, gx: np.ndarray, gy: np.ndarray) -> np.ndarray:
    angle=(np.rad2deg(np.arctan2(gy,gx))+180.0)%180.0
    out=np.zeros_like(mag,dtype=np.float32)
    bins=(np.round(angle/45.0).astype(np.int16))%4
    dirs=((0,1),(1,1),(1,0),(1,-1))
    for b,(dy,dx) in enumerate(dirs):
        m=bins==b
        a=np.roll(mag,(dy,dx),(0,1));c=np.roll(mag,(-dy,-dx),(0,1))
        keep=m & (mag>=a) & (mag>=c)
        out[keep]=mag[keep]
    out[[0,-1],:]=0;out[:,[0,-1]]=0
    return out


def _filter_components(mask: np.ndarray, strength: np.ndarray, threshold: float,
                       *, min_component: int, protect_factor: float,
                       cancelled: Callable[[],bool]) -> tuple[np.ndarray,int,int]:
    h,w=mask.shape;seen=np.zeros_like(mask,dtype=bool);out=mask.copy()
    removed=0;protected=0
    for y in range(h):
        if cancelled():raise InterruptedError()
        for x in range(w):
            if not mask[y,x] or seen[y,x]:continue
            q=deque([(y,x)]);seen[y,x]=True;cells=[];peak=0.0
            while q:
                cy,cx=q.popleft();cells.append((cy,cx));peak=max(peak,float(strength[cy,cx]))
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if not (dx or dy):continue
                        ny,nx=cy+dy,cx+dx
                        if 0<=ny<h and 0<=nx<w and mask[ny,nx] and not seen[ny,nx]:
                            seen[ny,nx]=True;q.append((ny,nx))
            keep=len(cells)>=min_component or (len(cells)>=2 and peak>=threshold*protect_factor)
            if keep:
                if len(cells)<min_component:protected+=1
            else:
                removed+=1
                for cy,cx in cells:out[cy,cx]=False
    return out,removed,protected


def structure_map(image: Image.Image, cancelled=lambda:False, detail='Detailed'):
    if detail not in SKETCH2_DETAILS:
        raise ValueError('Choose Simple, Balanced or Detailed sketch detail.')
    cfg=_PROFILES[detail]
    flat=_flatten(image)
    if max(flat.size)>1500:
        raise ValueError('Sketch 2.0 source is too large for the bounded structure pass.')
    smooth=flat.filter(ImageFilter.GaussianBlur(cfg['blur']))
    arr=np.asarray(smooth,dtype=np.float32)
    lum=arr[:,:,0]*.2126+arr[:,:,1]*.7152+arr[:,:,2]*.0722
    # Central differences. Colour-boundary magnitude deliberately remains
    # independent of luminance so equal-brightness red/blue boundaries survive.
    lx=np.zeros_like(lum);ly=np.zeros_like(lum)
    lx[:,1:-1]=lum[:,2:]-lum[:,:-2];ly[1:-1,:]=lum[2:,:]-lum[:-2,:]
    lum_mag=np.hypot(lx,ly)
    cx=np.zeros_like(arr);cy=np.zeros_like(arr)
    cx[:,1:-1,:]=arr[:,2:,:]-arr[:,:-2,:];cy[1:-1,:,:]=arr[2:,:,:]-arr[:-2,:,:]
    color_mag=np.sqrt(np.max(cx*cx+cy*cy,axis=2))
    # Strong luminance edges remain primary; chromatic edges supplement them.
    combined=lum_mag*.78+color_mag*.46
    gx=lx + (cx[:,:,0]-cx[:,:,2])*.10
    gy=ly + (cy[:,:,0]-cy[:,:,2])*.10
    thin=_nms(combined,gx,gy)
    active=thin[thin>0]
    threshold=max(float(cfg['floor']),float(np.percentile(active,cfg['percentile'])) if active.size else 255.0)
    mask=thin>=threshold
    mask[[0,-1],:]=False;mask[:,[0,-1]]=False
    mask,removed,protected=_filter_components(mask,thin,threshold,
        min_component=int(cfg['min_component']),protect_factor=float(cfg['protect_factor']),cancelled=cancelled)
    lum_only=lum_mag>=threshold
    color_only=(color_mag*.46>=threshold*.55)&(~lum_only)&mask
    meta={
        'engine':'Sketch 2.0','detail':detail,'threshold':round(threshold,3),
        'ink_pixels':int(mask.sum()),'luminance_edge_pixels':int((mask&lum_only).sum()),
        'color_boundary_pixels':int(color_only.sum()),'removed_noise_components':int(removed),
        'protected_small_components':int(protected),'ai_ml_ocr':False,
    }
    return mask,meta


def contour_image_v2(image: Image.Image, cancelled=lambda:False, detail='Detailed'):
    mask,meta=structure_map(image,cancelled,detail)
    out=np.full(mask.shape,255,dtype=np.uint8);out[mask]=0
    return Image.fromarray(out,'L').convert('RGBA'),meta
''')

# ---------------------------------------------------------------------------
# Sketch + Auto Fill: strict Sketch -> colour runs -> re-outline sequence.
# ---------------------------------------------------------------------------
write('SketchFillRenderer.py', r'''"""Sketch 2.0 + Auto Fill orchestration for Draw Studio v1.0.131-beta.

Microsoft Paint is the first supported target. This module creates plans only;
it never sends input and never weakens CanvasGuard/preflight/authorization. The
colour phase reuses Draw Studio's existing colour/custom-RGB planning but forces
path-based fills so no bucket prelude can run before the sketch.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Sequence
from PIL import Image, ImageDraw

SKETCH_FILL_RENDER_STYLE='Sketch + Auto Fill'
SKETCH_FILL_VERSION='2.0'
SKETCH_FILL_PHASES=('sketch','color_fill','reoutline')


def is_sketch_fill(options: dict[str,Any]) -> bool:
    return str(options.get('render_style') or '')==SKETCH_FILL_RENDER_STYLE and not bool(options.get('_sketch_fill_inner'))


def _is_paint(options):
    return str(options.get('profile_key') or '').strip().lower()=='microsoft-paint' or str(options.get('profile_name') or '').strip()=='Microsoft Paint'


def _path_length(path):
    return sum(math.hypot(float(b[0]-a[0]),float(b[1]-a[1])) for a,b in zip(path,path[1:])) if len(path)>1 else 0.0


def _path_area(path):
    if not path:return 0
    xs=[p[0] for p in path];ys=[p[1] for p in path]
    return max(1,max(xs)-min(xs)+1)*max(1,max(ys)-min(ys)+1)


def _strokes_from_paths(groups):
    out=[]
    for paths in groups:
        strokes=[]
        for path in paths:
            pts=[tuple(map(int,p)) for p in path]
            if not pts:continue
            if len(pts)==1:
                x,y=pts[0];strokes.append((x,y,x,y));continue
            strokes.extend((a[0],a[1],b[0],b[1]) for a,b in zip(pts,pts[1:]) if a!=b)
        out.append(strokes)
    return out


def _black_selector(colors, selectors):
    colors=list(map(tuple,colors));selectors=list(selectors or ())
    try:return colors.index((0,0,0)),colors,selectors
    except ValueError:pass
    from Colors import allColors
    native=min(range(len(allColors)),key=lambda i:sum(int(v)*int(v) for v in allColors[i].RGB))
    colors.append((0,0,0));selectors.append({'kind':'palette','palette_index':native,'rgb':(0,0,0)})
    return len(colors)-1,colors,selectors


def _reoutline_paths(paths, detail):
    paths=[tuple(p) for p in paths if p]
    if not paths:return []
    ratio={'Simple':.20,'Balanced':.32,'Detailed':.45}.get(str(detail),.32)
    wanted=max(1,min(len(paths),int(math.ceil(len(paths)*ratio))))
    ranked=sorted(enumerate(paths),key=lambda row:(-_path_area(row[1]),-_path_length(row[1]),row[0]))
    chosen={i for i,_ in ranked[:wanted]}
    return [p for i,p in enumerate(paths) if i in chosen]


def build_sketch_fill_plan(original: Image.Image, area, options: dict[str,Any], make_plan, finish_plan,
                           cancelled: Callable[[],bool]=lambda:False):
    if not _is_paint(options):
        raise ValueError('Sketch + Auto Fill is currently optimized for Microsoft Paint. Choose another rendering style for browser targets.')
    if options.get('erase_mode'):
        raise ValueError('Sketch + Auto Fill needs Pencil or Brush, not Eraser.')
    # Build the colour layer through the proven Paint planner, but explicitly
    # disable native Fill so it cannot execute as the existing prelude before
    # the sketch. Auto Fill v1 uses long connected colour runs instead.
    inner=dict(options)
    inner.update({
        '_sketch_fill_inner':True,'auto_engine_resolved':True,
        'render_style':'Standard / pixel','outline':False,'paint_current_color':False,'erase_mode':False,
        'drawing_mode':'Smart paths (recommended)','smart_paths':True,'lines':True,
        'fill_tool_available':False,'background_fill':'Off','use_region_fill_engine':False,
        'progressive_rendering':'Off','color_workflow':'Finish color first','detail_zoom':'Off',
    })
    inner.pop('background_fill_plan',None);inner.pop('fill_regions',None)
    color_plan=make_plan(original,area,inner,cancelled)
    if cancelled():raise InterruptedError()
    colors=tuple(color_plan.get('colors') or ())
    selectors=tuple(color_plan.get('color_selectors') or ())
    black_index,colors,selectors=_black_selector(colors,selectors)
    color_groups=[list(map(tuple,paths)) for paths in (color_plan.get('execution_groups') or [])]
    while len(color_groups)<len(colors):color_groups.append([])

    from Sketch2Planner import contour_image_v2
    from PixelData import monochrome_strokes
    from ContinuousPaths import build_execution_paths
    source=original.convert('RGBA').resize(color_plan['image'].size,Image.Resampling.LANCZOS)
    detail=str(options.get('sketch_detail') or 'Detailed')
    if detail=='Auto':detail='Balanced'
    sketch_image,sketch_meta=contour_image_v2(source,cancelled,detail=detail)
    ink=monochrome_strokes(sketch_image,True,cancelled)[0]
    sketch_paths=build_execution_paths([ink],enabled=True,cancelled=cancelled)[0] if ink else []
    sketch_paths=[tuple(map(tuple,p)) for p in sketch_paths if p]
    reoutline=_reoutline_paths(sketch_paths,detail)

    combined=[list(paths) for paths in color_groups]
    combined[black_index]=list(sketch_paths)+combined[black_index]+list(reoutline)
    sequence=[];serial=0
    for path in sketch_paths:
        sequence.append({'color_index':black_index,'path':path,'phase':'sketch','phase_label':'Sketch 2.0 contours','serial':serial});serial+=1
    order=[];seen=set()
    for raw in list((color_plan.get('options') or {}).get('color_order') or ()) + list(range(len(color_groups))):
        try:i=int(raw)
        except (TypeError,ValueError):continue
        if 0<=i<len(color_groups) and i not in seen:
            order.append(i);seen.add(i)
    color_paths=0
    for i in order:
        # Large/long runs first inside each colour: the image fills visibly fast.
        paths=sorted(color_groups[i],key=lambda p:(-_path_area(p),-_path_length(p)))
        for path in paths:
            if not path:continue
            sequence.append({'color_index':i,'path':tuple(path),'phase':'color_fill','phase_label':'color fill','serial':serial});serial+=1;color_paths+=1
    for path in reoutline:
        sequence.append({'color_index':black_index,'path':path,'phase':'reoutline','phase_label':'final re-outline','serial':serial});serial+=1

    outer=dict(color_plan.get('options') or {})
    outer.update({
        'render_style':SKETCH_FILL_RENDER_STYLE,'sketch_fill_active':True,'sketch_fill_version':SKETCH_FILL_VERSION,
        'sketch2_meta':dict(sketch_meta),'fill_regions':[],'background_fill':'Off','use_region_fill_engine':False,
        'detail_zoom':'Off','stroke_optimizer':'Off','progressive_rendering':'On','color_workflow':'Progressive passes',
        'plan_palette_rgb':tuple(colors),'color_selectors':tuple(selectors),
        '_sketch_fill_execution_groups':combined,'_sketch_fill_execution_sequence':sequence,
        '_accuracy_original_source':original.copy(),
    })
    outer.pop('background_fill_plan',None)
    outer['sketch_fill_meta']={
        'enabled':True,'version':SKETCH_FILL_VERSION,'target':'Microsoft Paint','paint_first':True,
        'phase_order':'Sketch -> Color Fill -> Re-outline','sketch_paths':len(sketch_paths),
        'color_fill_paths':color_paths,'reoutline_paths':len(reoutline),'total_paths':len(sequence),
        'native_bucket_prelude':False,'fill_method':'connected color runs','custom_colors_reused':bool(outer.get('exact_color_available')),
        'browser_policy_changed':False,'ai_ml_ocr':False,
    }
    groups=_strokes_from_paths(combined)
    return finish_plan(color_plan['image'],color_plan['fitted'],groups,outer,cancelled)


def render_sequence_preview(source_size, preview_size, sequence, palette_rgb, brush_px=1, *, phases=None):
    w,h=map(int,source_size);pw,ph=map(int,preview_size)
    out=Image.new('RGB',(max(1,pw),max(1,ph)),'white');draw=ImageDraw.Draw(out)
    sx=pw/max(1,w);sy=ph/max(1,h);width=max(1,int(round(float(brush_px))))
    allowed=set(phases) if phases is not None else None
    for entry in sequence or ():
        if allowed is not None and str(entry.get('phase')) not in allowed:continue
        try:color=tuple(palette_rgb[int(entry['color_index'])])
        except (KeyError,IndexError,TypeError,ValueError):continue
        pts=[(float(x)*sx,float(y)*sy) for x,y in entry.get('path') or ()]
        if not pts:continue
        if len(pts)==1:
            x,y=pts[0];r=max(.5,width/2);draw.ellipse((x-r,y-r,x+r,y+r),fill=color)
        else:
            draw.line(pts,fill=color,width=width,joint='curve')
    return out


def build_phase_previews(source_size, preview_size, sequence, palette_rgb, brush_px=1):
    return {
        'sketch2':render_sequence_preview(source_size,preview_size,sequence,palette_rgb,brush_px,phases=('sketch',)),
        'sketch_fill':render_sequence_preview(source_size,preview_size,sequence,palette_rgb,brush_px,phases=('sketch','color_fill')),
        'sketch_fill_final':render_sequence_preview(source_size,preview_size,sequence,palette_rgb,brush_px),
    }
''')

# DrawBot imports and top-level route.
replace_once('DrawBot.py',
"""from HybridRenderer3 import (HYBRID_RENDER_STYLE, HYBRID_MODES, apply_hybrid_policy,\n                             is_hybrid_renderer, validate_hybrid_mode)\n""",
"""from HybridRenderer3 import (HYBRID_RENDER_STYLE, HYBRID_MODES, apply_hybrid_policy,\n                             is_hybrid_renderer, validate_hybrid_mode)\nfrom SketchFillRenderer import (SKETCH_FILL_RENDER_STYLE, build_sketch_fill_plan, is_sketch_fill)\n""")
replace_once('DrawBot.py',
"""    from AutoDrawing import resolve_drawing\n    # Step 29: Hybrid Renderer 3.0 resolves specialised deterministic policy\n""",
"""    from AutoDrawing import resolve_drawing\n    # v1.0.131: Sketch + Auto Fill owns an explicit Paint-only phase order.\n    # Route it before AutoDrawing so Auto cannot replace the user's selected\n    # renderer. The recursive colour sub-plan is marked _sketch_fill_inner.\n    if is_sketch_fill(options):\n        return build_sketch_fill_plan(original,area,options,make_plan,finish_plan,cancelled)\n    # Step 29: Hybrid Renderer 3.0 resolves specialised deterministic policy\n""")

# Paint standard Sketch uses Sketch2; Gartic branch remains byte-for-byte legacy after this selector.
replace_once('DrawBot.py',
"""        image=contour_image(image,cancelled,detail=options.get('sketch_detail','Detailed'))\n        profiler_stop(options,'preprocessing',_prof_pre)\n        ink=monochrome_strokes(image,True,cancelled)[0]\n        plan_options=dict(options)\n""",
"""        _sketch2_meta=None\n        if str(options.get('profile_key') or '').lower()=='microsoft-paint' or str(options.get('profile_name') or '')=='Microsoft Paint':\n            from Sketch2Planner import contour_image_v2\n            _detail=options.get('sketch_detail','Detailed');_detail='Balanced' if _detail=='Auto' else _detail\n            image,_sketch2_meta=contour_image_v2(image,cancelled,detail=_detail)\n        else:\n            # Browser/Gartic path intentionally stays on the established legacy\n            # contour raster and GarticSketchPaths route.\n            image=contour_image(image,cancelled,detail=options.get('sketch_detail','Detailed'))\n        profiler_stop(options,'preprocessing',_prof_pre)\n        ink=monochrome_strokes(image,True,cancelled)[0]\n        plan_options=dict(options)\n        if _sketch2_meta is not None:plan_options['sketch2_meta']=dict(_sketch2_meta)\n""")

# Prebuilt SketchFill execution groups in finish_plan.
replace_once('DrawBot.py',
"""    pixel_prebuilt = options.get('_pixel_execution_groups')\n    if pixel_prebuilt is not None:\n""",
"""    pixel_prebuilt = options.get('_pixel_execution_groups')\n    sketch_fill_prebuilt = options.get('_sketch_fill_execution_groups')\n    if pixel_prebuilt is not None:\n""")
replace_once('DrawBot.py',
"""    elif options.get('sketch_execution_groups') is not None:\n""",
"""    elif sketch_fill_prebuilt is not None:\n        execution_groups=[list(paths) for paths in sketch_fill_prebuilt]\n        path_meta=dict(continuous_path_stats(groups,execution_groups))\n        path_meta.update(options.get('sketch_fill_meta') or {})\n        path_meta['mode']='Sketch + Auto Fill'\n        path_meta['sketch_fill']=True\n        path_meta['stroke_optimizer_requested']='Off'\n        path_meta['stroke_optimizer_effective']='Sketch Fill phase scheduler'\n    elif options.get('sketch_execution_groups') is not None:\n""")
replace_once('DrawBot.py',
"""        if pixel_prebuilt is not None:\n            # Geometry and component order were already optimized inside\n""",
"""        if pixel_prebuilt is not None or sketch_fill_prebuilt is not None:\n            # Pixel Accurate and Sketch+Fill already own geometry/phase order.\n            # Keep every path; no generic cap/optimizer may reorder them.\n""")
# The next old comment belongs only to pixel but is harmless; replace its body anchor target metadata works for both.
replace_once('DrawBot.py',
"""    if execution_groups is not None and pixel_prebuilt is None:\n        try:\n            from AdaptiveDeadlineRenderer import adapt_execution_plan\n""",
"""    if execution_groups is not None and pixel_prebuilt is None and sketch_fill_prebuilt is None:\n        try:\n            from AdaptiveDeadlineRenderer import adapt_execution_plan\n""")
replace_once('DrawBot.py',
"""        pixel_sequence=options.get('_pixel_execution_sequence') if pixel_prebuilt is not None else None\n        if pixel_sequence is not None:\n""",
"""        sketch_fill_sequence=options.get('_sketch_fill_execution_sequence') if sketch_fill_prebuilt is not None else None\n        pixel_sequence=options.get('_pixel_execution_sequence') if pixel_prebuilt is not None else None\n        if sketch_fill_sequence is not None:\n            execution_sequence=[dict(entry) for entry in sketch_fill_sequence]\n            _sf=options.get('sketch_fill_meta') or {}\n            path_meta.update({\n                'progressive_enabled':True,'progressive_sequence_paths':len(execution_sequence),\n                'progressive_sketch_paths':int(_sf.get('sketch_paths',0) or 0),\n                'progressive_color_fill_paths':int(_sf.get('color_fill_paths',0) or 0),\n                'progressive_reoutline_paths':int(_sf.get('reoutline_paths',0) or 0),\n                'progressive_phase_order':'Sketch -> Color Fill -> Re-outline',\n                'progressive_mode':'Sketch Fill','color_workflow':'Sketch then fill',\n            })\n        elif pixel_sequence is not None:\n""")

# Replace generic sequence-rendered preview after safety path accounting but before metrics/layers.
replace_once('DrawBot.py',
"""    profiler_stop(options, 'preview_rendering', _prof_preview)\n    _prof_estimate = profiler_start(options, 'execution_estimate')\n""",
"""    if options.get('sketch_fill_active') and execution_sequence:\n        try:\n            from SketchFillRenderer import render_sequence_preview\n            preview=render_sequence_preview(image.size,size,execution_sequence,palette_rgb,brush)\n        except Exception as _sf_preview_error:\n            log_event(f'Sketch Fill sequence preview fallback: {_sf_preview_error!r}')\n    profiler_stop(options, 'preview_rendering', _prof_preview)\n    _prof_estimate = profiler_start(options, 'execution_estimate')\n""")
replace_once('DrawBot.py',
"""    ui_previews['simulated_final']=preview\n    try:\n        from DetailZoomPass import render_detail_zoom_preview\n""",
"""    ui_previews['simulated_final']=preview\n    if options.get('sketch_fill_active') and execution_sequence:\n        try:\n            from SketchFillRenderer import build_phase_previews\n            ui_previews.update(build_phase_previews(image.size,size,execution_sequence,palette_rgb,brush))\n        except Exception as _sf_layers_error:\n            log_event(f'Sketch Fill phase previews skipped safely: {_sf_layers_error!r}')\n    try:\n        from DetailZoomPass import render_detail_zoom_preview\n""")

# Runtime status knows the dedicated 3-pass sequence.
replace_once('DrawBot.py',
"""            pixel_four_pass=any(p in phases_present for p in ('fill','mid_detail','fine_detail','cleanup'))\n            deadline_pass=any(p in phases_present for p in ('major_coverage','structure','important_details','accuracy','correction'))\n""",
"""            pixel_four_pass=any(p in phases_present for p in ('fill','mid_detail','fine_detail','cleanup'))\n            deadline_pass=any(p in phases_present for p in ('major_coverage','structure','important_details','accuracy','correction'))\n            sketch_fill_pass=any(p in phases_present for p in ('sketch','color_fill','reoutline'))\n""")
replace_once('DrawBot.py',
"""            elif deadline_pass:\n                _deadline_order=['major_coverage','structure','important_details','accuracy','correction']\n""",
"""            elif sketch_fill_pass:\n                _sf_order=[p for p in ('sketch','color_fill','reoutline') if p in phases_present]\n                phase_numbers={p:i+1 for i,p in enumerate(_sf_order)}\n                phase_names={'sketch':'Sketch 2.0 contours','color_fill':'color fill','reoutline':'final re-outline'}\n                phase_total=max(1,len(_sf_order))\n            elif deadline_pass:\n                _deadline_order=['major_coverage','structure','important_details','accuracy','correction']\n""")

# Plan diagnostics line.
replace_once('DrawBot.py',
"""    region_meta=options.get('region_fill_meta') or {}\n    region_bits=''\n""",
"""    sketch_fill_meta=options.get('sketch_fill_meta') or {}\n    sketch_fill_bits=''\n    if sketch_fill_meta.get('enabled'):\n        sketch_fill_bits=(f\" sketch_fill=on sketch={int(sketch_fill_meta.get('sketch_paths',0) or 0)}\"\n                          f\" fill={int(sketch_fill_meta.get('color_fill_paths',0) or 0)}\"\n                          f\" reoutline={int(sketch_fill_meta.get('reoutline_paths',0) or 0)}\"\n                          f\" fill_method={sketch_fill_meta.get('fill_method','?')}\")\n    region_meta=options.get('region_fill_meta') or {}\n    region_bits=''\n""")
replace_once('DrawBot.py',
"""f\"{shape_bits}{target_bits}{attempt_bits}{optimizer_bits}{detail_bits}{pixel_bits}{color_bits}{quick_bits}{region_bits}{extra_fast_bits}{deadline_bits}{policy_bits}{real_speed_bits}{turbo_bits}{profiler_bits} \"\n""",
"""f\"{shape_bits}{target_bits}{attempt_bits}{optimizer_bits}{detail_bits}{pixel_bits}{color_bits}{quick_bits}{sketch_fill_bits}{region_bits}{extra_fast_bits}{deadline_bits}{policy_bits}{real_speed_bits}{turbo_bits}{profiler_bits} \"\n""")

# UI rendering style.
replace_once('StudioUI.py',
"""from HybridRenderer3 import HYBRID_RENDER_STYLE, HYBRID_MODES\n""",
"""from HybridRenderer3 import HYBRID_RENDER_STYLE, HYBRID_MODES\nfrom SketchFillRenderer import SKETCH_FILL_RENDER_STYLE\n""")
replace_once('StudioUI.py',
"""setting_row(quality_card, 'Rendering style', a.render_style, ['Auto', 'Portrait / shaded', 'Standard / pixel', QUICK_SKETCH_RENDER_STYLE, HYBRID_RENDER_STYLE],""",
"""setting_row(quality_card, 'Rendering style', a.render_style, ['Auto', 'Portrait / shaded', 'Standard / pixel', QUICK_SKETCH_RENDER_STYLE, SKETCH_FILL_RENDER_STYLE, HYBRID_RENDER_STYLE],""")

# Frozen build modules + release note.
replace_once('build_exe.py',
"""        '--hidden-import', 'HybridRenderer3',\n""",
"""        '--hidden-import', 'HybridRenderer3',\n        '--hidden-import', 'Sketch2Planner',\n        '--hidden-import', 'SketchFillRenderer',\n""")
replace_once('build_exe.py',
"""        'RELEASE-NOTES-Step26-Color-Engine-Named-Color-Intelligence.md'\n""",
"""        'RELEASE-NOTES-Step26-Color-Engine-Named-Color-Intelligence.md', 'RELEASE-NOTES-v1.0.131-beta.md'\n""")

# Generic release gate: version suffix and BUILD_CHANNEL must agree, rather than RC-only forever.
replace_once('ReleaseCandidateHardening.py',
"""    if channel != \"rc\":\n        errors.append(f\"Version.py: release candidate must use BUILD_CHANNEL='rc', got {channel!r}\")\n    if not re.fullmatch(r\"\\d+\\.\\d+\\.\\d+-rc\\d+\", app_version):\n        errors.append(f\"Version.py: APP_VERSION is not an rcN version: {app_version!r}\")\n""",
"""    if re.fullmatch(r\"\\d+\\.\\d+\\.\\d+-rc\\d+\", app_version):\n        expected_channel='rc'\n    elif re.fullmatch(r\"\\d+\\.\\d+\\.\\d+-beta\", app_version):\n        expected_channel='beta'\n    elif re.fullmatch(r\"\\d+\\.\\d+\\.\\d+\", app_version):\n        expected_channel='stable'\n    else:\n        expected_channel=None;errors.append(f\"Version.py: APP_VERSION has unsupported release format: {app_version!r}\")\n    if expected_channel is not None and channel != expected_channel:\n        errors.append(f\"Version.py: APP_VERSION {app_version!r} requires BUILD_CHANNEL={expected_channel!r}, got {channel!r}\")\n""")

# Version metadata.
write('Version.py', "APP_NAME = 'Draw Studio'\nAPP_VERSION = '1.0.131-beta'\nFILE_VERSION = \"1.0.131\"\nBUILD_CHANNEL = 'beta'\n")
vi=(ROOT/'version_info.txt').read_text(encoding='utf-8')
vi=vi.replace('filevers=(1,0,130,0)','filevers=(1,0,131,0)').replace('prodvers=(1,0,130,0)','prodvers=(1,0,131,0)')
vi=vi.replace("StringStruct('FileVersion', '1.0.130')","StringStruct('FileVersion', '1.0.131')").replace("StringStruct('ProductVersion', '1.0.130')","StringStruct('ProductVersion', '1.0.131')")
(ROOT/'version_info.txt').write_text(vi,encoding='utf-8')
iss=(ROOT/'installer/DrawStudio.iss').read_text(encoding='utf-8')
iss=iss.replace('#define MyAppVersion "1.0.130-rc2"','#define MyAppVersion "1.0.131-beta"').replace('VersionInfoVersion=1.0.129.0','VersionInfoVersion=1.0.131.0')
(ROOT/'installer/DrawStudio.iss').write_text(iss,encoding='utf-8')

# Build workflow release notes / neutral gate label. Internal trigger path stays stable.
wf=(ROOT/'.github/workflows/build-windows.yml').read_text(encoding='utf-8')
wf=wf.replace('- name: RC source release gate','- name: Release source gate').replace('--notes-file RELEASE-NOTES-v1.0.130-rc2.md','--notes-file RELEASE-NOTES-v1.0.131-beta.md')
(ROOT/'.github/workflows/build-windows.yml').write_text(wf,encoding='utf-8')

# Release-hardening test fixture evolves to beta channel and current version.
p=ROOT/'test_step30_release_candidate_hardening_v10129rc1.py'
t=p.read_text(encoding='utf-8')
t=t.replace("channel='rc'","channel='beta'")
t=t.replace('1.0.130-rc2','1.0.131-beta').replace('1.0.130','1.0.131')
t=t.replace("def test_source_gate_detects_non_rc_channel(self):","def test_source_gate_detects_channel_mismatch(self):")
t=t.replace("channel='beta')\n            self.assertTrue(any(\"BUILD_CHANNEL='rc'\" in e for e in errors))","channel='rc')\n            self.assertTrue(any('requires BUILD_CHANNEL' in e for e in errors))")
t=t.replace("self.assertEqual(BUILD_CHANNEL,'rc')","self.assertEqual(BUILD_CHANNEL,'beta')")
t=t.replace('def test_release_version_is_rc2(self):','def test_release_version_is_v10131_beta(self):')
p.write_text(t,encoding='utf-8')

# Update all ordinary current-version assertions, but do not rename historical files/docs.
for p in ROOT.glob('test_*.py'):
    if p.name=='test_step30_release_candidate_hardening_v10129rc1.py':continue
    text=p.read_text(encoding='utf-8')
    text=text.replace('1.0.130-rc2','1.0.131-beta').replace('1.0.130','1.0.131')
    p.write_text(text,encoding='utf-8')

# Dedicated tests.
write('test_sketch2_v10131.py', r'''import unittest
from PIL import Image,ImageDraw
from Sketch2Planner import contour_image_v2,structure_map

class Sketch2V10131Tests(unittest.TestCase):
    def test_equalish_luminance_color_boundary_survives(self):
        im=Image.new('RGB',(80,40),(235,40,40));ImageDraw.Draw(im).rectangle((40,0,79,39),fill=(30,135,225))
        mask,meta=structure_map(im,detail='Detailed')
        self.assertGreater(int(mask[:,38:42].sum()),5)
        self.assertGreaterEqual(meta['color_boundary_pixels'],1)

    def test_tiny_high_contrast_feature_is_protected(self):
        im=Image.new('RGB',(80,60),'white');d=ImageDraw.Draw(im);d.rectangle((10,10,65,50),outline='black',width=2);d.rectangle((35,28,37,30),fill='black')
        out,meta=contour_image_v2(im,detail='Detailed')
        self.assertLess(out.convert('L').getpixel((36,29)),255)
        self.assertGreater(meta['ink_pixels'],20)

    def test_deterministic(self):
        im=Image.new('RGB',(64,48),'white');ImageDraw.Draw(im).ellipse((8,8,56,40),fill=(40,100,210))
        a,ma=contour_image_v2(im,detail='Balanced');b,mb=contour_image_v2(im,detail='Balanced')
        self.assertEqual(a.tobytes(),b.tobytes());self.assertEqual(ma,mb)

if __name__=='__main__':unittest.main()
''')

write('test_sketch_fill_v10131.py', r'''import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from SketchFillRenderer import SKETCH_FILL_RENDER_STYLE,build_sketch_fill_plan,is_sketch_fill,render_sequence_preview

class SketchFillV10131Tests(unittest.TestCase):
    def base(self,**changes):
        d=dict(profile_name='Microsoft Paint',profile_key='microsoft-paint',render_style=SKETCH_FILL_RENDER_STYLE,
               render_preset='Auto',outline=False,paint_current_color=False,erase_mode=False,sketch_detail='Detailed')
        d.update(changes);return d

    def fake_color_plan(self,image,area,options,cancelled):
        # Two plan-local colors, including a custom selector, prove propagation.
        paths=[ [((3,8),(25,8)),((3,9),(25,9))], [((30,12),(50,12))] ]
        return {'image':image.convert('RGBA'),'fitted':image.size,'execution_groups':paths,'colors':((220,30,30),(20,120,220)),
                'color_selectors':({'kind':'custom','rgb':(220,30,30)},{'kind':'palette','palette_index':1,'rgb':(20,120,220)}),
                'options':dict(options,plan_palette_rgb=((220,30,30),(20,120,220)),color_order=[0,1],exact_color_available=True)}

    def fake_finish(self,image,fitted,groups,options,cancelled):
        return {'image':image,'fitted':fitted,'groups':groups,'options':options,'colors':tuple(options['plan_palette_rgb']),
                'color_selectors':tuple(options['color_selectors']),'execution_groups':options['_sketch_fill_execution_groups'],
                'execution_sequence':options['_sketch_fill_execution_sequence']}

    def picture(self):
        im=Image.new('RGB',(64,40),'white');d=ImageDraw.Draw(im);d.rectangle((5,5,28,32),fill=(220,30,30));d.ellipse((34,7,58,32),fill=(20,120,220));return im

    def test_phase_order_is_strict(self):
        p=build_sketch_fill_plan(self.picture(),(64,40),self.base(),self.fake_color_plan,self.fake_finish)
        phases=[e['phase'] for e in p['execution_sequence']]
        order={'sketch':0,'color_fill':1,'reoutline':2}
        self.assertEqual([order[x] for x in phases],sorted(order[x] for x in phases))
        self.assertIn('sketch',phases);self.assertIn('color_fill',phases);self.assertIn('reoutline',phases)

    def test_native_fill_prelude_is_disabled_and_custom_colors_survive(self):
        p=build_sketch_fill_plan(self.picture(),(64,40),self.base(),self.fake_color_plan,self.fake_finish)
        self.assertEqual(p['options']['fill_regions'],[])
        self.assertEqual(p['options']['background_fill'],'Off')
        self.assertFalse(p['options']['sketch_fill_meta']['native_bucket_prelude'])
        self.assertTrue(p['options']['sketch_fill_meta']['custom_colors_reused'])
        self.assertTrue(any(s.get('kind')=='custom' for s in p['color_selectors']))

    def test_browser_target_fails_closed(self):
        with self.assertRaises(ValueError):
            build_sketch_fill_plan(self.picture(),(64,40),self.base(profile_name='Gartic Phone',profile_key='gartic-phone'),self.fake_color_plan,self.fake_finish)

    def test_sequence_preview_finishes_with_reoutline(self):
        seq=[{'color_index':0,'phase':'sketch','path':((2,2),(30,2))},{'color_index':1,'phase':'color_fill','path':((2,2),(30,2))},{'color_index':0,'phase':'reoutline','path':((2,2),(30,2))}]
        out=render_sequence_preview((32,16),(32,16),seq,((0,0,0),(255,0,0)),1)
        self.assertEqual(out.getpixel((16,2)),(0,0,0))

    def test_source_keeps_gartic_legacy_route(self):
        source=Path('DrawBot.py').read_text(encoding='utf-8')
        self.assertIn("from GarticSketchPaths import trace_contours",source)
        self.assertIn("('gartic-phone','gartic-io')",source)
        self.assertNotIn("profile_name') == 'Gartic Phone' and is_sketch_fill",source)

    def test_version(self):
        from Version import APP_VERSION,FILE_VERSION,BUILD_CHANNEL
        self.assertEqual((APP_VERSION,FILE_VERSION,BUILD_CHANNEL),('1.0.131-beta','1.0.131','beta'))

if __name__=='__main__':unittest.main()
''')

# README/current release documentation.
readme=(ROOT/'README.md').read_text(encoding='utf-8')
release_block='''### v1.0.131-beta — Sketch 2.0 + Auto Fill\n\n- **Sketch 2.0 for Microsoft Paint** combines luminance and color-boundary structure so important edges survive even when brightness is similar.\n- New **Sketch + Auto Fill** rendering style uses a strict **Sketch → Color Fill → Re-outline** execution order.\n- Paint color fill uses safe connected drawing runs after the sketch; the existing bucket-fill prelude is deliberately disabled for this mode so color can never start before the sketch.\n- Existing **Adaptive exact/custom RGB** selection is reused when Paint custom-color controls are calibrated.\n- Final re-outline restores the strongest structural contours after color fill.\n- Gartic Phone, Skribbl.io and other browser execution policies are unchanged.\n- Deterministic local image analysis only — no AI, ML or OCR.\n\n'''
anchor='### v1.0.130-rc2 — Release Candidate Hardening II'
if release_block.strip() not in readme:
    if anchor not in readme:raise SystemExit('README current release anchor missing')
    readme=readme.replace(anchor,release_block+anchor,1)
readme=readme.replace('**Current version:** v1.0.130-rc2','**Current version:** v1.0.131-beta')
readme=readme.replace('DrawStudio-1.0.130-rc2-Windows-x64.zip','DrawStudio-1.0.131-beta-Windows-x64.zip')
(ROOT/'README.md').write_text(readme,encoding='utf-8')

history_line='v1.0.131-beta Sketch 2.0 + Auto Fill improves Paint sketch structure with color-boundary edges and adds a strict Sketch -> Color Fill -> Re-outline renderer that reuses calibrated custom RGB while leaving browser/Gartic execution unchanged.\n'
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p=ROOT/name;text=p.read_text(encoding='utf-8')
    if not text.startswith(history_line):p.write_text(history_line+text,encoding='utf-8')

write('RELEASE-NOTES-v1.0.131-beta.md', '''# Draw Studio v1.0.131-beta — Sketch 2.0 + Auto Fill

## Sketch 2.0

Microsoft Paint sketch planning now combines luminance edges with color-boundary structure, removes isolated noise while protecting small high-contrast features, and keeps the existing browser/Gartic sketch route untouched.

## Sketch + Auto Fill

A new rendering style executes three deterministic phases in strict order:

1. Sketch 2.0 contours
2. Connected color-fill runs using the existing Paint color/custom-RGB planner
3. Final structural re-outline

The existing native bucket-fill prelude is intentionally disabled for this renderer so fill cannot occur before the sketch. CanvasGuard, Target Lock, Safety Preflight, Dry Run, profile isolation and manual-mouse stop remain unchanged.

## Scope

The new renderer is Paint-first in v1.0.131-beta. Browser targets fail closed if it is selected, and Gartic/Skribbl rendering policies are not modified.
''')

print('SKETCH2_V10131_PATCH=APPLIED')
