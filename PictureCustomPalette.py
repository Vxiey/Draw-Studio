"""Stable front-end for the Microsoft Paint picture custom-palette workflow.

The production palette planner/cache/calibration implementation is preserved in
``PictureCustomPaletteLegacy``.  This module adds the bounded transaction layer
used for fragile RGB entry while keeping the existing public API intact.
"""
from __future__ import annotations

import time
from typing import Iterable, Sequence

import PictureCustomPaletteLegacy as _legacy
from UiTransactionRuntime import AdaptivePacer, UiTransaction

# Public data/API retained from the production implementation.
SCHEMA = _legacy.SCHEMA
PROFILE_KEY = _legacy.PROFILE_KEY
DEFAULT_MAX_COLORS = _legacy.DEFAULT_MAX_COLORS
MAX_ANALYSIS_DIMENSION = _legacy.MAX_ANALYSIS_DIMENSION
MAX_EDGE_SAMPLES = _legacy.MAX_EDGE_SAMPLES
PicturePalette = _legacy.PicturePalette

# Keep this patchable at the historical module location.  Several tests and
# developer tools intentionally redirect the data root this way.
data_dir = _legacy.data_dir
atomic_write_text = _legacy.atomic_write_text

# Helpers that external tests/tools have historically reached directly.
_rgb = _legacy._rgb
_visible_rgb = _legacy._visible_rgb
_analysis_image = _legacy._analysis_image
_validate_payload = _legacy._validate_payload
_distance2 = _legacy._distance2
_dedupe = _legacy._dedupe
_edge_detail_colors = _legacy._edge_detail_colors
_resolve_max_colors = _legacy._resolve_max_colors
_resolve_target = _legacy._resolve_target


def _sync_legacy_environment() -> None:
    """Propagate deliberately patchable module globals into the preserved core."""
    _legacy.data_dir = data_dir
    _legacy.atomic_write_text = atomic_write_text


def image_fingerprint(image) -> str:
    return _legacy.image_fingerprint(image)


def cache_path(image_fp: str, calibration_fp: str = ""):
    _sync_legacy_environment()
    return _legacy.cache_path(image_fp, calibration_fp)


def load_cached_palette(image_fp: str, calibration_fp: str, *, max_colors: int, fidelity: str):
    _sync_legacy_environment()
    return _legacy.load_cached_palette(
        image_fp, calibration_fp, max_colors=max_colors, fidelity=fidelity
    )


def save_palette(palette: PicturePalette):
    _sync_legacy_environment()
    return _legacy.save_palette(palette)


def build_picture_palette(image, palette_rgb, *, max_colors: int = DEFAULT_MAX_COLORS,
                          fidelity: str = "Faithful", calibration_fingerprint: str = "",
                          cancelled=lambda: False) -> PicturePalette:
    _sync_legacy_environment()
    return _legacy.build_picture_palette(
        image, palette_rgb, max_colors=max_colors, fidelity=fidelity,
        calibration_fingerprint=calibration_fingerprint, cancelled=cancelled,
    )


def apply_custom_rgb_sequence(mouse, keyboard_backend, controls: dict,
                              colors: Iterable[Sequence[int]], *, cancelled=lambda: False,
                              wait=time.sleep, progress=None, dialog_ready=None,
                              dialog_closed=None, color_ready=None, retry_limit: int = 3,
                              state_callback=None) -> int:
    """Enter a picture palette into Paint with bounded verified retries.

    A colour is *never* committed with Paint's ``+`` button until the live RGB
    fields have been verified.  Transient UIA/WinUI lag may re-type the same
    colour up to ``retry_limit`` times, with adaptive backoff.  The final
    verification exception is preserved unchanged so Image Draw Bot's normal
    recovery/error classification still works.
    """
    required = ("OpenCustomColor", "RedField", "GreenField", "BlueField", "ConfirmColor")
    missing = [name for name in required if name not in controls]
    if missing:
        raise ValueError("Numeric Paint RGB controls are not calibrated: " + ", ".join(missing))

    controls = dict(controls)
    values = tuple(_rgb(c) for c in colors)
    dialog_open = False
    completed = 0
    transaction = UiTransaction(
        max_attempts=retry_limit,
        pacer=AdaptivePacer(base_delay=0.025, max_delay=0.30, growth=1.8, decay=0.72),
        cancelled=cancelled,
        wait=wait,
        on_state=state_callback,
    )

    def check_cancelled() -> None:
        transaction.check_cancelled("Picture custom palette cancelled.")

    def click(name: str, delay: float = 0.04) -> None:
        point = tuple(map(int, controls[name]))
        mouse.move(*point)
        wait(0.015)
        mouse.click()
        wait(delay)

    def refresh_dialog_controls() -> None:
        if dialog_ready is None:
            return
        fresh = dialog_ready()
        if fresh:
            controls.update(fresh)
        if "AddCustomColor" not in controls:
            raise ValueError("Paint + / Add to custom colors is not calibrated; no RGB input was sent.")

    if not values:
        return 0

    mouse.arm_input()
    try:
        check_cancelled()
        transaction.transition("OPEN_DIALOG", detail="open Paint Edit colors")
        click("OpenCustomColor", 0.16)
        dialog_open = True

        # Do not type anything until the modal and its live fields are proven ready.
        refresh_dialog_controls()
        if "AddCustomColor" not in controls:
            raise ValueError("Paint + / Add to custom colors is not calibrated; no RGB input was sent.")

        for index, rgb in enumerate(values, 1):
            check_cancelled()

            def write_and_verify(attempt: int):
                check_cancelled()
                # Re-acquire controls on retries. Paint's XAML dialog can move or
                # recreate Edit controls while it is catching up.
                if attempt > 1:
                    refresh_dialog_controls()
                transaction.transition(
                    "WRITE_VALUE", attempt=attempt, item_index=index,
                    detail=f"RGB {rgb}",
                )
                settle = max(0.025, float(transaction.pacer.current_delay))
                for name, value in zip(("RedField", "GreenField", "BlueField"), rgb):
                    check_cancelled()
                    click(name, settle)
                    keyboard_backend.press_and_release("ctrl+a")
                    keyboard_backend.write(str(int(value)), delay=0.01)
                    wait(settle)

                transaction.transition(
                    "VERIFY_VALUE", attempt=attempt, item_index=index,
                    detail=f"RGB {rgb}",
                )
                if color_ready is not None:
                    fresh = color_ready(rgb)
                    if fresh:
                        controls.update(fresh)
                return True

            transaction.retry(
                write_and_verify,
                item_index=index,
                retry_on=(TimeoutError, ValueError),
                cancel_message="Picture custom palette cancelled.",
            )

            check_cancelled()
            transaction.transition(
                "COMMIT_VALUE", attempt=1, item_index=index,
                detail=f"Add RGB {rgb} to Paint custom colors",
            )
            # Commit exactly once after successful verification. Never retry this
            # click blindly: a delayed first click may already have modified Paint.
            click("AddCustomColor", 0.25)
            wait(0.50)
            check_cancelled()

            # Re-probe the still-open modal after the commit. This doubles as a
            # response/anchor guard before the next colour without risking a
            # duplicate AddCustomColor click.
            transaction.transition(
                "VERIFY_COMMIT", attempt=1, item_index=index,
                detail=f"RGB {rgb}",
            )
            if dialog_ready is not None:
                fresh = dialog_ready()
                if fresh:
                    controls.update(fresh)

            completed += 1
            if progress is not None:
                progress(index, len(values), rgb)

        check_cancelled()
        click("ConfirmColor", 0.12)
        if dialog_closed is not None:
            dialog_closed()
        dialog_open = False
        transaction.transition("DONE", item_index=completed, detail=f"{completed} colors prepared")
    except Exception:
        if transaction.state not in ("FAILED", "DONE"):
            try:
                transaction.transition("FAILED", item_index=completed)
            except Exception:
                pass
        raise
    finally:
        if dialog_open:
            try:
                keyboard_backend.press_and_release("esc")
                wait(0.04)
            except Exception:
                pass
        mouse.disarm_input()

    return completed


# The preserved start workflow resolves/calibrates Paint, builds the palette and
# persists completion state.  Its global call site now points at the hardened
# transaction function above, so no planner/cache code had to be duplicated.
_legacy.apply_custom_rgb_sequence = apply_custom_rgb_sequence


def start_picture_custom_palette(app) -> bool:
    _sync_legacy_environment()
    _legacy.apply_custom_rgb_sequence = apply_custom_rgb_sequence
    return bool(_legacy.start_picture_custom_palette(app))


__all__ = [
    "SCHEMA", "PROFILE_KEY", "DEFAULT_MAX_COLORS", "MAX_ANALYSIS_DIMENSION",
    "MAX_EDGE_SAMPLES", "PicturePalette", "image_fingerprint", "cache_path",
    "load_cached_palette", "save_palette", "build_picture_palette",
    "apply_custom_rgb_sequence", "start_picture_custom_palette",
]
