"""Browser One-Click orchestration for Image Draw Bot v1.0.80.

Normal browser flow: choose a supported game, import/drop an image, then Draw
Studio discovers or reuses the matching browser window, auto-calibrates canvas
and palette read-only, and hands control back to DrawBot for visual preflight,
automatic brush-size selection and explicit one-click drawing authorization.

This module never sends mouse or keyboard input.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

from BrowserAutoCalibration import SUPPORTED_BROWSER_PROFILES, detect_browser_setup, auto_calibrate_browser
from DpiSupport import get_window_dpi_info

MIN_WINDOW_W = 620
MIN_WINDOW_H = 420
MIN_CONFIDENCE = .70
UNIQUE_MARGIN = .045


@dataclass(frozen=True)
class Candidate:
    handle: int
    rect: tuple[int, int, int, int]
    client_rect: tuple[int, int, int, int]
    dpi: int
    pid: int
    title: str
    confidence: float
    palette_count: int
    canvas_box: tuple[int, int, int, int] | None
    screenshot: object | None = None

    @property
    def area(self):
        l,t,r,b=self.client_rect
        return max(0,r-l)*max(0,b-t)


def _value(item, name, default=None):
    return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)


def _rect_overlap_ratio(a, b) -> float:
    try:
        al,at,ar,ab=map(float,a); bl,bt,br,bb=map(float,b)
    except Exception:
        return 0.0
    iw=max(0.0,min(ar,br)-max(al,bl)); ih=max(0.0,min(ab,bb)-max(at,bt))
    inter=iw*ih
    aa=max(1.0,(ar-al)*(ab-at)); ba=max(1.0,(br-bl)*(bb-bt))
    return max(0.0,min(1.0,inter/max(aa,ba)))


def candidate_score(item, *, preferred_handle=None, foreground_handle=None,
                    preferred_monitor_rect=None, previous_canvas_box=None) -> float:
    """Score a browser candidate using visual evidence plus safe local context.

    Context never overrides a low-confidence visual match. It only breaks ties
    between two already plausible game windows, which avoids forcing the user to
    close unrelated browser windows during Auto Setup.
    """
    confidence=float(_value(item,'confidence',0.0) or 0.0)
    count=int(_value(item,'palette_count',0) or 0)
    canvas=_value(item,'canvas_box',None)
    handle=int(_value(item,'handle',0) or 0)
    rect=_value(item,'client_rect',None) or _value(item,'rect',None)
    palette_bonus=min(.10,count/720.0)
    canvas_bonus=.05 if canvas else 0.0
    context_bonus=0.0
    if preferred_handle and handle==int(preferred_handle):
        context_bonus += .18
    if foreground_handle and handle==int(foreground_handle):
        context_bonus += .12
    if preferred_monitor_rect and rect:
        context_bonus += .035*_rect_overlap_ratio(rect,preferred_monitor_rect)
    if previous_canvas_box and canvas:
        # Browser detector canvas boxes are client/screen rectangles depending on
        # caller. Ratio only contributes a small tie-break bonus.
        context_bonus += .045*_rect_overlap_ratio(canvas,previous_canvas_box)
    return confidence+palette_bonus+canvas_bonus+context_bonus


def choose_unique_candidate(candidates: Iterable, *, min_confidence: float=MIN_CONFIDENCE,
                            margin: float=UNIQUE_MARGIN, preferred_handle=None,
                            foreground_handle=None, preferred_monitor_rect=None,
                            previous_canvas_box=None):
    values=list(candidates)
    if not values:
        raise ValueError('No visible browser window matched the selected drawing game.')
    score=lambda c:candidate_score(c,preferred_handle=preferred_handle,foreground_handle=foreground_handle,
                                   preferred_monitor_rect=preferred_monitor_rect,previous_canvas_box=previous_canvas_box)
    values.sort(key=lambda c:(score(c), _value(c,'area',0)), reverse=True)
    best=values[0]
    if float(_value(best,'confidence',0.0)) < float(min_confidence):
        raise ValueError(f'Browser match confidence is too low ({float(_value(best,"confidence",0.0))*100:.0f}%). Bring the game window fully into view and try again.')
    if len(values)>1 and score(best)-score(values[1]) < float(margin):
        raise ValueError('More than one browser window still matches the selected game almost equally. Focus the intended game window or select its canvas once.')
    return best


def _foreground_window_handle():
    if os.name != 'nt':
        return None
    try:
        import ctypes
        value=ctypes.windll.user32.GetForegroundWindow()
        return int(value) if value else None
    except Exception:
        return None

def _enumerate_windows(exclude_pid=None):
    """Yield visible top-level Windows candidates. Imported lazily for portability."""
    import ctypes
    from ctypes import wintypes
    user32=ctypes.WinDLL('user32',use_last_error=True)
    EnumWindowsProc=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user32.IsWindowVisible.argtypes=[wintypes.HWND];user32.IsWindowVisible.restype=wintypes.BOOL
    user32.IsIconic.argtypes=[wintypes.HWND];user32.IsIconic.restype=wintypes.BOOL
    user32.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];user32.GetWindowRect.restype=wintypes.BOOL
    user32.GetClientRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];user32.GetClientRect.restype=wintypes.BOOL
    user32.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)];user32.ClientToScreen.restype=wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)];user32.GetWindowThreadProcessId.restype=wintypes.DWORD
    user32.GetWindowTextLengthW.argtypes=[wintypes.HWND];user32.GetWindowTextLengthW.restype=ctypes.c_int
    user32.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int];user32.GetWindowTextW.restype=ctypes.c_int
    try:
        user32.GetDpiForWindow.argtypes=[wintypes.HWND];user32.GetDpiForWindow.restype=wintypes.UINT
    except AttributeError:pass
    excluded={int(exclude_pid or os.getpid())}
    out=[]
    @EnumWindowsProc
    def callback(hwnd,_):
        try:
            if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):return True
            pid=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if int(pid.value) in excluded:return True
            cr=wintypes.RECT();origin=wintypes.POINT(0,0);wr=wintypes.RECT()
            if not user32.GetClientRect(hwnd,ctypes.byref(cr)) or not user32.ClientToScreen(hwnd,ctypes.byref(origin)) or not user32.GetWindowRect(hwnd,ctypes.byref(wr)):return True
            client=(origin.x,origin.y,origin.x+(cr.right-cr.left),origin.y+(cr.bottom-cr.top))
            if client[2]-client[0] < MIN_WINDOW_W or client[3]-client[1] < MIN_WINDOW_H:return True
            n=max(0,int(user32.GetWindowTextLengthW(hwnd)));buf=ctypes.create_unicode_buffer(n+1);user32.GetWindowTextW(hwnd,buf,n+1)
            dpi_info=get_window_dpi_info(hwnd,user32=user32)
            out.append({'handle':int(hwnd),'rect':(wr.left,wr.top,wr.right,wr.bottom),'client_rect':client,
                        'dpi':int(dpi_info.dpi),'dpi_source':dpi_info.source,'dpi_scale':dpi_info.scale,
                        'monitor_rect':dpi_info.monitor_rect,'pid':int(pid.value),'title':buf.value})
        except Exception:pass
        return True
    if not user32.EnumWindows(callback,0):
        raise OSError('Windows could not enumerate visible application windows.')
    out.sort(key=lambda m:(m['client_rect'][2]-m['client_rect'][0])*(m['client_rect'][3]-m['client_rect'][1]),reverse=True)
    return out[:18]


def discover_browser_target(profile_key: str, *, exclude_pid=None, preferred_handle=None, preferred_monitor_rect=None, previous_canvas_box=None):
    key=str(profile_key or '').lower()
    if key not in SUPPORTED_BROWSER_PROFILES:
        raise ValueError('Browser One-Click is not available for this profile.')
    from PIL import ImageGrab
    detected=[]
    for meta in _enumerate_windows(exclude_pid=exclude_pid):
        try:
            shot=ImageGrab.grab(bbox=meta['client_rect'],all_screens=True).convert('RGB')
            result=detect_browser_setup(key,shot,screen_origin=(meta['client_rect'][0],meta['client_rect'][1]))
            palette_conf=float(result.get('palette_confidence') or 0.0);canvas_conf=float(result.get('canvas_confidence') or 0.0)
            confidence=.64*palette_conf+.36*canvas_conf
            detected.append(Candidate(meta['handle'],meta['rect'],meta['client_rect'],meta['dpi'],meta['pid'],meta['title'],confidence,len(result.get('positions') or ()),result.get('canvas_box'),shot))
        except Exception:
            continue
    return choose_unique_candidate(
        detected, preferred_handle=preferred_handle, foreground_handle=_foreground_window_handle(),
        preferred_monitor_rect=preferred_monitor_rect, previous_canvas_box=previous_canvas_box)


def one_click_setup(profile_name: str, profile_key: str, palette_path: Path, *, current_handle=None, exclude_pid=None):
    """Return a BrowserAutoCalibration-compatible payload for one-click setup."""
    from PIL import ImageGrab
    from TargetCapture import probe_handle_isolated
    from LayoutFingerprintV2 import try_restore, record_from_calibration_file
    key=str(profile_key or '').lower()
    if key not in SUPPORTED_BROWSER_PROFILES:raise ValueError('Browser One-Click is not available for this profile.')
    if current_handle:
        meta=probe_handle_isolated(int(current_handle))
        screenshot=ImageGrab.grab(bbox=tuple(meta['client_rect']),all_screens=True).convert('RGB')
    else:
        candidate=discover_browser_target(key,exclude_pid=exclude_pid)
        meta={'handle':candidate.handle,'rect':candidate.rect,'client_rect':candidate.client_rect,'target_pid':candidate.pid,'dpi':candidate.dpi}
        screenshot=candidate.screenshot
    cached=try_restore(key,meta,Path(palette_path),screenshot=screenshot)
    if cached.hit:
        payload=cached.as_dict();payload.update({'palette_confidence':cached.confidence,'canvas_confidence':max(.90,cached.confidence),'method':'Layout Fingerprint v2 cache','note':'One-Click restored a verified local layout fingerprint.','target_meta':meta,'profile_name':profile_name,'layout_fingerprint_meta':cached.as_dict(),'one_click':True})
        return payload
    from BrowserAutoRecalibration import calibrate_browser_with_retry
    result,retry_meta=calibrate_browser_with_retry(
        key,meta,Path(palette_path),screenshot=screenshot,
        recapture=lambda:ImageGrab.grab(bbox=tuple(meta['client_rect']),all_screens=True).convert('RGB'))
    try:fingerprint=record_from_calibration_file(key,meta,result.canvas_box,Path(palette_path),method='Browser One-Click / '+result.method) if result.canvas_box else None
    except Exception as error:fingerprint={'saved':False,'reason':str(error)}
    payload=result.as_dict();payload.update({'target_meta':meta,'profile_name':profile_name,'layout_fingerprint_meta':fingerprint,'one_click':True,'recalibration_retry_meta':retry_meta})
    return payload
