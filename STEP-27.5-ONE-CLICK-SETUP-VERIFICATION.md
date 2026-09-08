# Step 27.5 — One-click Setup + Automatic Canvas/Palette Verification

Step 27.5 sits between completed Step 27 and Step 28. **Step 28–30 keep their existing numbers.**

## Goal

Make first-time and repeated target setup safer and faster without weakening Draw Studio's explicit drawing/start gates.

The new **One-click Setup + Verify** action is configuration-only. It can activate a target window for screenshots, but it never moves/clicks the mouse, presses keys, unlocks full drawing or starts a render.

## Supported targets

- Microsoft Paint
- Gartic Phone
- Skribbl.io
- Skribbl.io Fast
- SketchHeads
- Sketchful.io

Other/custom targets keep the existing manual calibration flow until a verified detector is added in Step 28 or later.

## Browser flow

1. Reuse the currently known browser handle when valid, otherwise discover the best supported game window.
2. Reuse Layout Fingerprint v2 when the saved layout can still be verified, otherwise run Browser Auto Calibration.
3. Save the detected canvas and a screen-verified, profile-owned palette.
4. Hide Draw Studio and activate the same target again.
5. Take a fresh screenshot.
6. Run `BrowserVisualPreflight` independently against the expected canvas and representative saved palette swatches.
7. Require a valid canvas, at least three tested colors and the existing ~80% palette agreement rule for larger sample sets.
8. Report PASS or block setup safely.

## Microsoft Paint flow

1. Discover the unique Paint window.
2. Run the existing `PaintFullCalibration` detector on a blank visible Paint canvas.
3. Save the verified 20-color palette plus Pencil/Fill tool positions.
4. Hide Draw Studio and activate Paint again.
5. Take a new screenshot.
6. Independently rerun `PaintFullCalibration.detect_setup`.
7. Require 20 live colors, Pencil + Fill availability, >=85% setup confidence and no meaningful canvas reflow (maximum 6 px edge shift).
8. Report PASS or block setup safely.

## Fail-closed rules

One-click Setup is blocked if any of these are true:

- target/client rectangle is missing or invalid
- canvas is outside the target client area
- canvas is implausibly small
- profile ownership of saved palette does not match
- palette state is not `verified`
- browser palette verification is too weak
- Paint no longer exposes the expected 20-color palette
- required Paint Pencil/Fill calibration is missing
- the target/canvas changes between setup and verification
- confidence drops below the target-specific threshold

Failure invalidates the target/safety lock and points the user back to manual calibration. It does not attempt to draw.

## Profile isolation

Step 27.5 verification state is session-only and is cleared on every profile reset/switch. It is not exported in `.drawprofile` files and cannot leak from one profile into another.

## Reused components

- `BrowserOneClick.py`
- `BrowserAutoCalibration.py`
- `BrowserVisualPreflight.py`
- `PaintFullCalibration.py`
- `PaintTools.py`
- `Colors.validate_calibration`
- `ScreenGuard.WindowMonitor`
- `ScreenTaskWindow.py`

`OneClickSetupVerification.py` contains only the final validation/orchestration contract; it does not duplicate the existing detector engines.

## Verification

The Windows Step 27.5 regression selection covers:

- new one-click verification rules
- browser visual preflight
- browser target selection
- Paint full calibration
- profile state isolation
- profile switch input safety
- profile-specific calibration/timing/cache storage

The verified selection passes **41/41 tests** on Windows with Python 3.12, followed by Python compile checks for the modified runtime/build modules.
