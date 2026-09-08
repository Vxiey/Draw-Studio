"""Explicit, one-shot image drop-in start policy for browser canvas profiles.

This module intentionally contains no GUI or mouse code.  The UI may use it to
turn one explicit Arm action plus one explicit image import/drop into a drawing
start for non-strict browser/game profiles.
"""
from __future__ import annotations

DROP_IN_ACTION = 'manual-drop-in-start'
DROP_IN_ARM_SECONDS = 120.0


def normalize_action(action: object) -> str | None:
    """Return a supported drop-in action or None for legacy/unknown values."""
    return DROP_IN_ACTION if action == DROP_IN_ACTION else None


def action_for_import(*, armed: bool) -> str | None:
    """Action attached to an imported image when Drop-In Start is armed."""
    return DROP_IN_ACTION if bool(armed) else None


def can_arm(profile_name: str, *, ready: bool, message: str = '') -> tuple[bool, str]:
    """Validate whether Drop-In Start may be armed before the next image import.

    Paint keeps the full safety chain because loading a new image invalidates the
    dry-run/signature gates. Browser/game profiles use the shorter explicit arm
    flow, but still require target/canvas/palette readiness.
    """
    if profile_name == 'Microsoft Paint':
        return False, 'Drop-In Start is disabled for Microsoft Paint. Use image → small test → Lock → Safety preflight → Dry run → Unlock → Start.'
    if not ready:
        cleaned = str(message or 'Complete target setup first.').replace('Start locked: ', '', 1)
        if 'load, paste, or drop an image' in cleaned.lower():
            cleaned = 'select the target canvas and read the palette first.'
        return False, f'Drop-In Start blocked: {cleaned}'
    return True, 'Drop-In Start armed for the next image import.'


def should_start_after_loaded(action: object, *, armed: bool, busy: bool, closing: bool, stop_set: bool) -> bool:
    """True only when a loaded image may turn into an automatic draw request."""
    return normalize_action(action) == DROP_IN_ACTION and bool(armed) and not busy and not closing and not stop_set
