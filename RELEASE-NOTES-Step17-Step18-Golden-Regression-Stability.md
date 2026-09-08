# Release notes — Step 17 + Step 18

## Step 17 — Golden Image Regression Suite

- Added deterministic local golden-image fixtures for banana/yellow hue, red banana texture, dominant hue preservation and small detail preservation.
- Added `GoldenImageRegression.py` with pass/fail thresholds for source-relative color, hue, coverage, OKLab ΔE and draw-time budgets.
- Added a **Golden tests** button in Tools.
- The suite is local-only and never arms mouse input, reads the screen, uses the network or stores user images.

## Step 18 — Release Stability + Crash/Freeze Hardening

- Added `ReleaseStabilityHardening.py`.
- Preview planning now uses a cancellable attempt guard with explicit timeout metadata.
- Preview-only resolution can be reduced automatically when RAM budget is tight.
- Preview rendering catches more safe failure modes and shows a recoverable message instead of failing the UI.
- Added pure helpers for event coalescing and progress throttling.
- Added PyInstaller hidden imports and packaged docs/assets.
