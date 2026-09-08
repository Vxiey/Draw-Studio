"""Profile-isolated verified-color cache for Paint custom RGB.

Step 9 binds every persistent verified color to both the drawing profile and a
fingerprint of the palette/tool/exact-color calibration context. Recalibration
therefore invalidates stale verified colors without touching another profile.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ProfileStorage import calibration_context_fingerprint, profile_verified_color_file

SCHEMA = 2
MAX_COLORS = 256


def cache_path(profile):
    return profile_verified_color_file(profile)


def _context(profile, context_fingerprint=None, workflow=''):
    return str(context_fingerprint or calibration_context_fingerprint(profile, workflow=str(workflow or '')))


def _read(profile):
    path = cache_path(profile)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(data, dict) or int(data.get('version', 0)) != SCHEMA:
        # Schema-1 entries had no calibration fingerprint and are intentionally
        # not trusted after Step 9 because they could survive a recalibration.
        return None
    if str(data.get('profile') or '') != str(profile):
        return None
    return data


def load_cache(profile, *, context_fingerprint=None, workflow=''):
    data = _read(profile)
    if data is None:
        return {}
    context = _context(profile, context_fingerprint, workflow)
    if str(data.get('context_fingerprint') or '') != context:
        return {}
    stored_workflow = str(data.get('workflow') or '')
    requested_workflow = str(workflow or '')
    if stored_workflow != requested_workflow:
        return {}
    colors = data.get('colors')
    return dict(colors) if isinstance(colors, dict) else {}


def save_cache(profile, colors, *, context_fingerprint=None, workflow=''):
    path = cache_path(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    context = _context(profile, context_fingerprint, workflow)
    payload = {
        'version': SCHEMA,
        'profile': str(profile),
        'context_fingerprint': context,
        'workflow': str(workflow or ''),
        'colors': dict(colors),
    }
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, dir=path.parent, suffix='.tmp') as f:
            tmp = Path(f.name)
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
        tmp.replace(path)
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)


def put_verified(profile, requested_rgb, detected_rgb, *, delta_e2000, method, confidence=100.0,
                 context_fingerprint=None, workflow=''):
    context = _context(profile, context_fingerprint, workflow)
    colors = load_cache(profile, context_fingerprint=context, workflow=workflow)
    key = ''.join(f'{max(0,min(255,int(v))):02X}' for v in requested_rgb[:3])
    colors[key] = {
        'requested_rgb': list(map(int, requested_rgb[:3])),
        'created_rgb': list(map(int, detected_rgb[:3])),
        'delta_e2000': float(delta_e2000),
        'method': str(method),
        'confidence': float(confidence),
        'verified': True,
        'context_fingerprint': context,
        'workflow': str(workflow or ''),
    }
    if len(colors) > MAX_COLORS:
        colors = dict(list(colors.items())[-MAX_COLORS:])
    save_cache(profile, colors, context_fingerprint=context, workflow=workflow)
    return colors[key]
