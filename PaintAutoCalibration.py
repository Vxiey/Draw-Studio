"""Best-effort Microsoft Paint toolbar auto-calibration.

The detector is intentionally conservative.  It analyses a screenshot of the
already-selected Paint window and only saves controls when visual evidence is
strong enough.  It never sends mouse input.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from PIL import ImageGrab, ImageOps, ImageFilter
from CalibrationAnchors import make_anchor
from PaintTools import save_tool_calibration, TOOL_FILE

@dataclass(frozen=True)
class Candidate:
    name: str
    point: tuple[int,int]
    confidence: float
    score: float

def _gray_edges(image):
    g=ImageOps.grayscale(image).filter(ImageFilter.GaussianBlur(.55))
    return g.filter(ImageFilter.FIND_EDGES)

def _density(edge, box):
    crop=edge.crop(tuple(map(int,box)))
    if crop.width<=0 or crop.height<=0:return 0.0
    hist=crop.histogram()
    return sum(hist[145:]) / max(1,crop.width*crop.height)

def _dark_density(image, box):
    crop=ImageOps.grayscale(image.crop(tuple(map(int,box))))
    h=crop.histogram()
    return sum(h[:90]) / max(1,crop.width*crop.height)

def _toolbar_bounds(client_rect):
    l,t,r,b=map(int,client_rect); w=r-l; h=b-t
    # Modern Paint keeps drawing controls in the upper ribbon.  Deliberately
    # ignore title/menu strip and canvas so false positives cannot be saved.
    top=t+max(42,round(h*.045))
    bottom=min(b,t+max(150,round(h*.20)))
    return l,top,r,bottom

def _template_score(edge, dark, cx, cy, name, scale):
    """Heuristic icon-shape score.  No clicks; weak scores are rejected."""
    s=max(12,int(18*scale))
    x0,y0,x1,y1=cx-s,cy-s,cx+s,cy+s
    e=_density(edge,(x0,y0,x1,y1)); d=_dark_density(dark,(x0,y0,x1,y1))
    if not (.015 <= e <= .55):return 0.0
    # Pencil/eraser/fill icons all contain diagonal/compact dark geometry.
    # Score icon richness + central occupancy; later spatial constraints keep
    # candidates in the drawing-tools portion of the ribbon.
    inner=_density(edge,(cx-s*.55,cy-s*.55,cx+s*.55,cy+s*.55))
    score=min(1.0,e*3.0 + d*1.6 + inner*1.8)
    if name=='Pencil': score*=1.04
    elif name=='Fill': score*=.98
    elif name=='Eraser': score*=.94
    return score

def detect_controls(image, client_rect):
    """Only accept the verified modern Paint layout; no density/order guesses."""
    from PaintFullCalibration import detect_setup
    try:result=detect_setup(image,screen_origin=tuple(client_rect[:2]))
    except ValueError:return {}
    return {name:Candidate(name,point,.90,.90) for name,point in result['tools'].items()}

def layout_signature(client_rect,dpi=None):
    l,t,r,b=map(int,client_rect)
    return f'{r-l}x{b-t}@{int(dpi or 96)}'

def auto_calibrate(target_metadata, path=TOOL_FILE, screenshot=None, min_confidence=.62):
    """Detect safe direct tools.  Never clicks and never overwrites on failure."""
    rect=tuple(target_metadata['client_rect'])
    if screenshot is None:
        screenshot=ImageGrab.grab(bbox=rect,all_screens=True)
    found=detect_controls(screenshot,rect)
    accepted={k:v for k,v in found.items() if v.confidence>=float(min_confidence)}
    if 'Pencil' not in accepted:
        raise ValueError(
            'Auto calibration could not identify Pencil with enough confidence. '
            'Keep Paint maximized at 100% Windows scaling and use manual calibration for the missing control.')
    tools={k:v.point for k,v in accepted.items() if k in ('Pencil','Eraser','Fill')}
    confidence=min(v.confidence for v in accepted.values())
    auto={'method':'visual-toolbar-v1','confidence':confidence,
          'layout_signature':layout_signature(rect,target_metadata.get('dpi')),
          'detected':sorted(tools)}
    saved=save_tool_calibration(tools,path=path,anchor=make_anchor(rect),auto=auto)
    return {'saved':saved,'confidence':confidence,'detected':sorted(tools)}
