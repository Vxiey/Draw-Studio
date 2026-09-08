# Draw Studio v1.0.126-beta — Step 27.5: One-click Setup + Automatic Canvas/Palette Verification

Step 27.5 adds one primary setup action for supported Paint/browser targets while preserving the existing roadmap numbering: Step 28 remains More Drawing Targets, Step 29 remains Hybrid Renderer 3.0 and Step 30 remains Release Candidate Hardening.

## New

- **One-click Setup + Verify** button in Prepare target app.
- Microsoft Paint setup through the existing Paint visual detector.
- Supported browser-game setup through Browser One-Click discovery / verified layout reuse.
- Automatic target, canvas and palette setup where a verified detector exists.
- Independent second live screenshot verification after the initial setup pass.
- Compact PASS/BLOCKED result showing canvas, palette, tools and confidence.
- Manual setup remains available as fallback.

## Verification rules

### Browser targets

- target client/canvas geometry must remain valid
- saved palette must belong to the selected profile and have state `verified`
- Browser Visual Preflight must independently find the expected canvas
- at least three representative palette swatches must be testable
- larger samples require approximately 80% agreement
- final confidence must be at least 68%

### Microsoft Paint

- saved palette must be a verified 20-color Paint palette
- Pencil and Fill must both be calibrated
- a second `PaintFullCalibration.detect_setup` pass must still find the 20-color layout
- detected canvas may move by at most 6 px between passes
- final confidence must be at least 85%

## Safety / isolation

- setup and verification never send mouse or keyboard drawing input
- full-draw authorization is explicitly revoked before setup starts
- no drawing is automatically started by the Step 27.5 button
- failed verification invalidates target/safety readiness
- verification state is session-only and cleared on profile reset/switch
- Step 27 `.drawprofile` export/import does not carry Step 27.5 session authorization/state
- unsupported/custom targets fail closed to the existing manual calibration workflow

## Build integration

`OneClickSetupVerification` is included as a PyInstaller hidden import so packaged Windows builds retain the dynamically loaded verification module.

## Verification result

Windows Server 2025 / Python 3.12:

- **41/41** selected setup, verification, Paint, browser and profile-isolation tests passed
- modified runtime/build modules passed `py_compile`

The first integration attempt exposed only a patch-script indentation error and was not committed. The corrected integration was then re-run and verified strictly before release packaging.
