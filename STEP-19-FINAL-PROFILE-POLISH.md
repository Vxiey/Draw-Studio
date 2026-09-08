# Step 19 — Paint/Gartic/Skribbl Final Profile Polish

Draw Studio now centralizes release-ready profile presets in `ProfilePolish.py`.
The core profiles — Microsoft Paint, Gartic Phone, Skribbl.io and Skribbl.io Fast — have one source of truth for:

- safe default renderer strategy
- time-budget preset
- color policy
- calibration requirements
- target-specific warnings
- setup flow copy used by the UI

The presets are pure metadata and option overlays. They never store coordinates, screenshots, image data or native input state.

## Core defaults

- Paint uses Shape paths, Safe Fill, Perceptual match, Faithful color fidelity and Adaptive Exact color count.
- Gartic Phone uses the 75-second `Gartic Phone Fast` budget with Extra Fast 2.0-friendly settings.
- Skribbl.io uses the 80-second `Skribbl Default` budget.
- Skribbl.io Fast uses the 60-second `Skribbl 60` budget.

Manual profile settings remain respected. The final polish overlay is applied only in Profile Engine Auto mode.
