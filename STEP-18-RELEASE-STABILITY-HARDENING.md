# Step 18 — Release Stability + Crash/Freeze Hardening

This step hardens preview planning and diagnostics so slow images or preview UI failures do not freeze the application or leave stale work queued.

## Added guards

- Preview memory guard that lowers preview-only diagnostic resolution when RAM budget is tight.
- Cancellable preview-attempt guard with explicit timeout metadata.
- Safe primary-preview timeout → fast fallback → retain previous preview path.
- Broader safe exception handling around canvas preview rendering.
- Pure event coalescer for noisy status/progress/deadline events.
- Progress throttle helper to prevent Tk event storms.
- Stability metadata stored under `release_stability_meta`.

## Scope

This does not change final draw quality, renderer geometry, mouse delivery or the existing safety chain. It only keeps planning, preview rendering and diagnostics bounded and recoverable.

## Privacy and safety

No screenshots, crops, thumbnails, hashes, raw pixels, network calls or telemetry are added.
