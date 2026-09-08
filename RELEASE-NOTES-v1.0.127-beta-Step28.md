# Draw Studio v1.0.127-beta — Step 28: More Drawing Targets

Step 28 expands Draw Studio's target system without weakening calibration isolation or pretending that an unverified website layout is safe for automatic detection.

## New targets

### Kleki

A dedicated `kleki` browser-painting profile with:

- isolated settings, palette, tool calibration, layout fingerprint and timing storage
- high-detail Shape paths defaults
- manual Brush / Fill / Eraser calibration
- manual palette and canvas calibration
- no hard-coded screen coordinates
- no unverified One-click/Auto Setup

### Magma

A dedicated `magma` collaborative-browser profile with:

- isolated settings, palette, tool calibration, layout fingerprint and timing storage
- high-detail progressive Shape paths defaults
- manual Brush / Fill / Eraser calibration
- manual palette and canvas calibration
- no hard-coded screen coordinates
- no unverified One-click/Auto Setup

## Target capability registry

`TargetCapabilities.py` is now the central source of truth for target semantics. It classifies each built-in target by:

- desktop / browser game / browser painting app / generic
- setup mode: Paint Auto, verified Browser Auto or Manual
- palette mode: verified automatic or manual
- timed vs untimed target
- layout-fingerprint support
- per-profile timing-cache support

This prevents target support lists from drifting apart across modules.

## Verified automatic targets

Automatic browser setup remains limited to the layouts that already have verified deterministic detectors:

- Gartic Phone
- Skribbl.io
- Skribbl.io Fast
- SketchHeads
- Sketchful.io

## Manual browser targets

The following dedicated targets intentionally remain manual until a layout/palette detector is verified against real current UI captures:

- Drawize
- Gartic.io
- Kleki
- Magma

They still receive dedicated renderer policy, profile storage, calibration ownership and UI guidance. They simply do not expose automatic target/palette detection as if it were verified.

## UI isolation

Step 28 separates three concepts that were previously too closely coupled:

- browser target
- verified auto-browser target
- One-click-capable target

A manual browser profile therefore keeps normal tool/palette/canvas calibration controls while Browser One-Click and Browser Auto Setup stay hidden.

## Safety

Step 28 does not add any target coordinates, native handles or input authorization to profile policies. Existing CanvasGuard, target validation and explicit Start authorization remain authoritative.

## Verification

Windows Server 2025 / Python 3.12 regression selection:

- **59/59 tests passed**
- Step 28 target-capability tests passed
- Step 28 profile/storage/UI tests passed
- Step 27.5 One-click verification regressions passed
- profile isolation and profile-switch safety passed
- calibration/timing storage isolation passed
- Profile Engine and UI-profile regressions passed
- affected modules passed `py_compile`

Integration commit: `496f4ae`
