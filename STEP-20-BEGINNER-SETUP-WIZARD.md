# Step 20 — UX Cleanup + Beginner Setup Wizard

Image Draw Bot now has a beginner setup wizard that shows exactly what is missing before full Start is allowed.

The wizard is powered by `BeginnerSetupWizard.py`, a pure module that builds a deterministic checklist from current UI state. It does not use mouse input, screenshots, files, network access or telemetry.

## What it shows

- target profile
- image loaded state
- tools/palette calibration state
- drawing area state
- preview suggestion
- Paint strict safety gates
- browser/game optional diagnostics
- Unlock/Start status
- target-specific warnings from Step 19

The compact wizard status is also shown in the Safety & draw step, so the user can see the next safe action without opening a dialog.
