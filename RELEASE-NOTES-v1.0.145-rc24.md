# Image Draw Bot v1.0.145-rc24 — Regional Axis + Sketch Dense Hybrid

- Add lossless connected-region horizontal/vertical axis planning shared by Extra Fast and Gartic Sketch.
- Let Extra Fast evaluate beneficial tall or run-reducing regions independently instead of rotating an entire same-colour group.
- Keep the existing real execution-cost model and downstream regression guard authoritative; proposals that do not improve the modeled final plan fall back to the baseline.
- Use exact horizontal/vertical run representations for dense Gartic Sketch components when they are cheaper than the junction-heavy contour representation.
- Preserve the contour tracer for thin, structural and diagonal detail.
- Preserve exact source-pixel coverage: no gap bridging, dropped pixels or colour changes.
- Keep protected portrait/detail paths and existing Fill, brush, Paint and profile safety behavior unchanged.
- Synchronize release metadata and the complete regression suite to rc24 so the Windows release gate can validate the actual release version.
