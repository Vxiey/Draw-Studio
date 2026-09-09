"""Bounded native-resolution planning and viewport-only image rendering."""
from PIL import Image
import math


def full_preview_options(options,area):
    w,h=map(int,area)
    try:
        ram=max(128,int(options.get('ram_budget_mb',512)))
    except (TypeError, ValueError, OverflowError):
        ram=512
    # Reserve most of the configured RAM for the planner, app and source image.
    pixel_limit=min(8_000_000,max(250_000,ram*1024*1024//512))
    if w<1 or h<1 or w*h>pixel_limit:
        raise ValueError(f'Full preview exceeds its memory budget ({pixel_limit:,} target pixels). Use the normal preview or a smaller drawing area.')
    out=dict(options,_full_detail_preview=True,_preview_plan=False,
             _preview_mode='Manual',_target_area=(w,h),_preview_area=(w,h),
             cpu_workers='1',cpu_workers_resolved=1,cpu_engine='Threads',gpu_mode='CPU')
    screen_area=options.get("_target_screen_area") or options.get("target_area") or options.get("_target_area")
    if isinstance(screen_area, (list,tuple)) and len(screen_area)==4:
        out["_target_screen_area"]=tuple(screen_area)
    return out


def viewport_image(image,size,zoom=0,pan=(0,0)):
    w,h=[max(1,min(4096,int(v))) for v in size]
    iw,ih=image.size
    if iw < 1 or ih < 1:
        raise ValueError("Source image must have positive dimensions.")
    try:
        zoom=float(zoom)
    except (TypeError, ValueError, OverflowError):
        zoom=0.0
    if not math.isfinite(zoom):
        zoom=0.0
    try:
        pan=tuple(float(v) for v in pan)
        if len(pan) != 2 or not all(math.isfinite(v) for v in pan):
            pan=(0.0,0.0)
    except (TypeError, ValueError, OverflowError):
        pan=(0.0,0.0)
    scale=min(w/iw,h/ih) if zoom<=0 else max(.125,min(8,zoom))
    sw=min(iw,w/scale);sh=min(ih,h/scale)
    cx=min(iw-sw/2,max(sw/2,iw/2+float(pan[0])))
    cy=min(ih-sh/2,max(sh/2,ih/2+float(pan[1])))
    box=(cx-sw/2,cy-sh/2,cx+sw/2,cy+sh/2)
    # Resize the source region directly; convert only the bounded result.
    # In Fit mode this also avoids an RGBA copy of a huge original image.
    target=(max(1,min(w,round(sw*scale))),max(1,min(h,round(sh*scale))))
    crop=image.resize(target,Image.Resampling.NEAREST if scale>=1 else Image.Resampling.LANCZOS,box=box).convert('RGBA')
    out=Image.new('RGBA',target,'white');out.alpha_composite(crop)
    return out.convert('RGB'),scale
