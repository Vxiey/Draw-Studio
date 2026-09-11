# Image Draw Bot v1.0.144-rc13 — Automatic Image-Aware Brush Selection

- Analyze the actual planned image geometry and classify it as detail-heavy, balanced or flat-shape before assigning brush widths.
- Automatically use a broader verified brush for large flat regions when that reduces work without weakening CanvasGuard.
- Automatically downshift to smaller verified brushes for contours, narrow components, protected details, cleanup and accuracy corrections.
- Let supported browser targets reserve a bounded safety inset for one verified automatic brush upshift; very large brush presets are never selected just because they exist.
- Keep low-confidence or incomplete brush-control detection fail-closed: no guessed control clicks and no invented dynamic brush sizes.
- Preserve the existing fixed brush behavior on targets that do not expose verified multi-size controls.
- Add deterministic Auto Brush diagnostics with image classification, selected base/detail/mid sizes, reasons and planned brush-switch counts.
- Update the Brush width help so the value is clearly a baseline for automatic selection rather than a required single fixed width.

This release keeps the existing drawing geometry authoritative. Automatic brush choices are constrained by verified target controls, per-path detail protection and CanvasGuard, and the release remains gated by the complete Windows regression suite, self-test, package validation and silent installer round-trip.
