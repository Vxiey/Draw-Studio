"""Deterministic native stroke-delivery policies for Draw Studio.

v1.0.75 splits browser delivery by game. The module controls only native input
spacing/timing; renderer geometry, CanvasGuard and target safety are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrokeDeliveryPolicy:
    step_px: float
    min_path_delay: float
    press_settle: float
    release_settle: float
    drag_backend: str
    native_drag_reliability: bool
    label: str
    palette_click_delay: float = 0.24
    ui_control_delay: float = 0.20
    profile_key: str = 'generic'

    def as_dict(self) -> dict:
        return {
            'step_px': float(self.step_px),
            'min_path_delay': float(self.min_path_delay),
            'press_settle': float(self.press_settle),
            'release_settle': float(self.release_settle),
            'drag_backend': self.drag_backend,
            'native_drag_reliability': bool(self.native_drag_reliability),
            'label': self.label,
            'palette_click_delay': float(self.palette_click_delay),
            'ui_control_delay': float(self.ui_control_delay),
            'profile_key': self.profile_key,
        }


def _profile_key(options: dict) -> str:
    explicit = str(options.get('profile_key') or '').strip().lower()
    if explicit:
        return explicit
    name = str(options.get('profile_name') or '').strip().lower()
    mapping = {
        'microsoft paint': 'microsoft-paint',
        'gartic phone': 'gartic-phone',
        'skribbl.io': 'skribbl',
        'skribbl.io fast': 'skribbl-fast',
        'sketchheads': 'sketchheads',
        'sketchful.io': 'sketchful',
    }
    return mapping.get(name, name.replace(' ', '-'))


def resolve_stroke_delivery(options: dict | None, *, dry_run: bool = False) -> StrokeDeliveryPolicy:
    options = options or {}
    requested = float(options.get('stroke_step_px', 8) or 8)
    if requested <= 0:
        requested = 8.0

    key = _profile_key(options)
    paint_profile = bool(options.get('paint_profile')) or key == 'microsoft-paint'
    requested_mode = str(options.get('paint_stroke_delivery') or 'Auto').strip().lower()

    if paint_profile and not dry_run:
        if requested_mode in ('reliable', 'dense', 'sendinput'):
            return StrokeDeliveryPolicy(
                step_px=min(requested, 3.0), min_path_delay=0.0030,
                press_settle=0.008, release_settle=0.005,
                drag_backend='sendinput', native_drag_reliability=True,
                label='Microsoft Paint reliable drag', palette_click_delay=.28,
                ui_control_delay=.22, profile_key=key)
        if requested_mode in ('compatible', 'compatibility', 'cursor'):
            return StrokeDeliveryPolicy(
                step_px=min(requested, 5.0), min_path_delay=0.0020,
                press_settle=0.006, release_settle=0.004,
                drag_backend='cursor', native_drag_reliability=False,
                label='Microsoft Paint compatibility drag', palette_click_delay=.28,
                ui_control_delay=.22, profile_key=key)
        return StrokeDeliveryPolicy(
            step_px=min(requested, 4.0), min_path_delay=0.0025,
            press_settle=0.007, release_settle=0.004,
            drag_backend='cursor', native_drag_reliability=False,
            label='Microsoft Paint adaptive compatible drag', palette_click_delay=.28,
            ui_control_delay=.22, profile_key=key)

    # Dry run must remain click-free, but it should still follow the same cursor
    # density as the target browser so its timing/route sample is representative.
    # No press/release settle is necessary because no button event is sent.
    dry_scale = 0.0 if dry_run else 1.0

    if key == 'gartic-phone':
        # Gartic Phone's HTML5 canvas tolerates wide interpolation well, but its
        # palette/tool UI needs a little more settle time than Skribbl.
        return StrokeDeliveryPolicy(
            step_px=max(requested, 12.0), min_path_delay=.0007 * dry_scale,
            press_settle=.0045 * dry_scale, release_settle=.0030 * dry_scale,
            drag_backend='cursor', native_drag_reliability=False,
            label='Gartic Phone HTML5 input', palette_click_delay=.075,
            ui_control_delay=.085, profile_key=key)

    if key in ('skribbl', 'skribbl-fast'):
        # Skribbl's canvas is responsive and benefits most from fewer native
        # mouse events and short palette switching pauses.
        fast = key == 'skribbl-fast'
        return StrokeDeliveryPolicy(
            step_px=max(requested, 12.0 if fast else 10.0),
            min_path_delay=(.00045 if fast else .00065) * dry_scale,
            press_settle=(.0030 if fast else .0040) * dry_scale,
            release_settle=(.0020 if fast else .0025) * dry_scale,
            drag_backend='cursor', native_drag_reliability=False,
            label=('Skribbl Fast input' if fast else 'Skribbl quality input'),
            palette_click_delay=(.050 if fast else .060),
            ui_control_delay=(.060 if fast else .070), profile_key=key)

    if key == 'sketchheads':
        # SketchHeads has larger animated UI controls along the bottom, so keep
        # control clicks slightly more conservative while still accelerating the
        # actual canvas movement compared with the generic browser path.
        return StrokeDeliveryPolicy(
            step_px=max(requested, 8.0), min_path_delay=.0010 * dry_scale,
            press_settle=.0060 * dry_scale, release_settle=.0040 * dry_scale,
            drag_backend='cursor', native_drag_reliability=False,
            label='SketchHeads canvas input', palette_click_delay=.085,
            ui_control_delay=.095, profile_key=key)

    return StrokeDeliveryPolicy(
        step_px=requested, min_path_delay=0.0,
        press_settle=0.0, release_settle=0.0,
        drag_backend='cursor', native_drag_reliability=False,
        label='Standard drag', palette_click_delay=.24,
        ui_control_delay=.20, profile_key=key or 'generic')
