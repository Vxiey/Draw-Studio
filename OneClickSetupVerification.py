"""Step 27.5 — unified one-click setup verification for Image Draw Bot.

The module is deliberately read-only.  It validates the selected target,
canvas, saved verified palette and tool state, then performs an independent
visual verification pass.  It never sends mouse or keyboard input.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Sequence

SETUP_SCHEMA = 1
MIN_CANVAS_SIDE = 40
PAINT_PROFILE = 'microsoft-paint'


@dataclass(frozen=True)
class SetupVerificationResult:
    passed: bool
    profile_key: str
    mode: str
    confidence: float
    canvas_ok: bool
    palette_ok: bool
    palette_verified: int
    palette_tested: int
    tool_ok: bool
    reasons: tuple[str, ...]

    @property
    def reason(self) -> str:
        return '; '.join(self.reasons) if self.reasons else 'setup verification passed'

    def as_dict(self) -> dict:
        return {
            'schema': SETUP_SCHEMA,
            'passed': self.passed,
            'profile_key': self.profile_key,
            'mode': self.mode,
            'confidence': self.confidence,
            'canvas_ok': self.canvas_ok,
            'palette_ok': self.palette_ok,
            'palette_verified': self.palette_verified,
            'palette_tested': self.palette_tested,
            'tool_ok': self.tool_ok,
            'reasons': list(self.reasons),
        }


def setup_mode(profile_key: str) -> str:
    from TargetCapabilities import capability_for_key
    mode=capability_for_key(profile_key).setup_mode
    if mode=='paint-auto':return 'paint'
    if mode=='browser-auto':return 'browser'
    return 'manual'


def _box(value: Sequence[int], label: str) -> tuple[int,int,int,int]:
    if not isinstance(value,(list,tuple)) or len(value)!=4:
        raise ValueError(f'{label} rectangle is unavailable.')
    l,t,r,b=map(int,value)
    if r<=l or b<=t:
        raise ValueError(f'{label} rectangle is invalid.')
    return l,t,r,b


def validate_canvas(client_rect, canvas_box, *, min_side: int = MIN_CANVAS_SIDE) -> tuple[int,int,int,int]:
    client=_box(client_rect,'Target client')
    canvas=_box(canvas_box,'Detected canvas')
    cl,ct,cr,cb=client;l,t,r,b=canvas
    if r-l < int(min_side) or b-t < int(min_side):
        raise ValueError('Detected canvas is implausibly small.')
    if not (cl<=l<r<=cr and ct<=t<b<=cb):
        raise ValueError('Detected canvas is outside the target client area.')
    return canvas


def canvas_shift(expected, detected) -> int:
    a=_box(expected,'Expected canvas');b=_box(detected,'Detected canvas')
    return max(abs(x-y) for x,y in zip(a,b))


def load_verified_palette(path, profile_key: str):
    from Colors import validate_calibration
    path=Path(path)
    data=json.loads(path.read_text(encoding='utf-8'))
    rows=validate_calibration(data,profile_key=profile_key)
    state=str(data.get('state') or 'calibrated').strip().lower()
    if state!='verified':
        raise ValueError(f'Palette is not screen-verified (state={state}).')
    verification=data.get('verification') if isinstance(data.get('verification'),dict) else {}
    confidence=float(verification.get('confidence',0) or 0)
    return data,rows,max(0.0,min(1.0,confidence))


def verify_browser_live(profile_key: str, target_meta: dict, canvas_box, palette_path, *, screenshot=None) -> SetupVerificationResult:
    profile_key=str(profile_key or '').lower()
    if setup_mode(profile_key)!='browser':
        raise ValueError('Browser one-click verification is unavailable for this profile.')
    client=_box((target_meta or {}).get('client_rect'),'Browser client')
    canvas=validate_canvas(client,canvas_box)
    _data,rows,saved_confidence=load_verified_palette(palette_path,profile_key)
    entries=[((int(row['position'][0]),int(row['position'][1])),tuple(map(int,row['rgb'][:3]))) for row in rows]
    from BrowserVisualPreflight import verify_browser_visual_preflight
    visual=verify_browser_visual_preflight(profile_key,target_meta,canvas,entries,screenshot=screenshot,require_palette=True)
    reasons=[]
    if not visual.canvas_ok:reasons.append('canvas visual verification failed')
    if visual.palette_tested<3:reasons.append('too few palette swatches could be verified')
    if visual.palette_verified < (visual.palette_tested if visual.palette_tested<=4 else max(3,(visual.palette_tested*4+4)//5)):
        reasons.append(f'palette verification matched only {visual.palette_verified}/{visual.palette_tested}')
    reasons.extend(str(x) for x in visual.reasons if str(x) not in reasons)
    palette_ok=visual.palette_tested>=3 and visual.palette_verified >= (visual.palette_tested if visual.palette_tested<=4 else max(3,(visual.palette_tested*4+4)//5))
    confidence=min(float(visual.confidence), saved_confidence if saved_confidence>0 else float(visual.confidence))
    passed=bool(visual.passed and visual.canvas_ok and palette_ok and confidence>=.68)
    return SetupVerificationResult(passed,profile_key,'browser',confidence,bool(visual.canvas_ok),bool(palette_ok),int(visual.palette_verified),int(visual.palette_tested),True,tuple(reasons))


def verify_paint_live(target_meta: dict, canvas_box, palette_path, *, tool_path=None, screenshot=None) -> SetupVerificationResult:
    profile_key=PAINT_PROFILE
    client=_box((target_meta or {}).get('client_rect'),'Paint client')
    canvas=validate_canvas(client,canvas_box)
    _data,rows,saved_confidence=load_verified_palette(palette_path,profile_key)
    reasons=[]
    palette_ok=len(rows)==20
    if not palette_ok:reasons.append(f'Paint palette contains {len(rows)} colors instead of 20')
    from PaintTools import load_tool_calibration, TOOL_FILE
    tools=load_tool_calibration(tool_path or TOOL_FILE)
    direct=tools.get('tools') if isinstance(tools,dict) else {}
    tool_ok=bool(isinstance(direct,dict) and direct.get('Pencil') is not None and direct.get('Fill') is not None)
    if not tool_ok:reasons.append('Paint Pencil and Fill are not both verified')
    if screenshot is None:
        from PIL import ImageGrab
        screenshot=ImageGrab.grab(bbox=client,all_screens=True).convert('RGB')
    else:
        screenshot=screenshot.convert('RGB')
    expected_size=(client[2]-client[0],client[3]-client[1])
    if screenshot.size!=expected_size:
        raise ValueError(f'Paint screenshot size changed during setup verification ({screenshot.size} != {expected_size}).')
    from PaintFullCalibration import detect_setup
    detected=detect_setup(screenshot,screen_origin=client[:2])
    detected_canvas=validate_canvas(client,detected.get('canvas_box'))
    shift=canvas_shift(canvas,detected_canvas)
    canvas_ok=shift<=6 and float(detected.get('confidence',0) or 0)>=.85
    if not canvas_ok:reasons.append(f'Paint canvas changed by {shift}px or confidence is too low')
    live_palette=int(detected.get('palette_count',0) or 0)
    palette_ok=bool(palette_ok and live_palette==20)
    if live_palette!=20:reasons.append(f'live Paint palette verification found {live_palette}/20 colors')
    live_conf=max(0.0,min(1.0,float(detected.get('confidence',0) or 0)))
    confidence=min(live_conf,saved_confidence if saved_confidence>0 else live_conf)
    passed=bool(canvas_ok and palette_ok and tool_ok and confidence>=.85)
    return SetupVerificationResult(passed,profile_key,'paint',confidence,canvas_ok,palette_ok,20 if palette_ok else min(20,live_palette),20,tool_ok,tuple(reasons))


def format_verification(result: SetupVerificationResult | dict) -> str:
    data=result.as_dict() if isinstance(result,SetupVerificationResult) else dict(result or {})
    passed=bool(data.get('passed'))
    canvas='OK' if data.get('canvas_ok') else 'FAIL'
    palette=f"{int(data.get('palette_verified',0) or 0)}/{int(data.get('palette_tested',0) or 0)}"
    tools='OK' if data.get('tool_ok') else 'FAIL'
    confidence=float(data.get('confidence',0) or 0)
    prefix='✓ One-click Setup verified' if passed else 'One-click Setup blocked'
    return f'{prefix} · canvas {canvas} · palette {palette} · tools {tools} · confidence {confidence*100:.0f}%'
