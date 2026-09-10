# Image Draw Bot v1.0.124 beta — Step 15 Correction Review + Recovery UI

This build adds a post-draw review card and guarded recovery actions for Step 13
real-result verification and Step 14 post-draw correction.

## Added

- Correction Review status card in the safety/drawing panel.
- Read-only Review dialog with trust, confidence, real Visual Accuracy, coverage,
  correction path counts, correction pixel count, and reason flags.
- Correction-only retry action for bounded post-draw patching without restarting
  the full drawing.
- Full retry action routed through the same normal safety gates.
- Runtime correction-review events during correction skip, correction execution,
  and post-correction re-score.
- Preview diagnostics line for Correction Review.

## Safety

Correction-only retry still requires current target validation, safety preflight,
dry-run/unlock gating, CanvasGuard, and fresh snapshot support. It does not bypass
any native-input gate.

## Privacy

No screenshots, crops, thumbnails, hashes, raw pixels, or image buffers are saved.
Only compact numeric review/correction metadata is persisted.
