# Step 11 — End-to-End Quality/Speed Auto Tuner + Acceptance Gates

Step 11 makes the **Auto** render preset compose the systems introduced in Steps 1–10 instead of relying on one fixed quality/speed profile.

## What Auto now selects

Before expensive planning, Draw Studio performs a bounded source analysis and selects:

- renderer: Shape paths or Smart paths / Extra Fast 2.0
- draw quality and planning resolution
- adaptive detail level
- Safe/Balanced/Fast delivery strategy
- an Auto colour ceiling that is handed to Steps 5 and 6

The decision is deterministic and based on source complexity, colour entropy, edge density, dominant hue/tone protection, target profile and usable deadline.

### Deadline classes

- **75/80-second class:** safe coverage-first hybrid, Fast delivery, Standard planning, Extra Fast 2.0, protected but tighter colour ceiling.
- **150-second class:** higher detail/colour allowance; simple flat art can use Shape paths.
- **300-second class:** High/Maximum likeness, Preserve detail and a larger colour budget.
- **No active deadline:** quality-first Auto policy. Explicit Masterpiece remains the unconditional Pixel Accurate mode.

Manual, Masterpiece and explicit Extra Fast presets are not rewritten by Step 11.

## Acceptance gates

After the plan has been simulated, Step 11 checks the **source-relative** metrics from Step 1/10 and the calibrated/projected draw time.

The hard acceptance decision uses two primary gates:

- **Visual Accuracy** as the source-relative quality floor
- projected draw time against the **usable deadline** when a deadline is active

Perceptual Color Accuracy, Edge Accuracy and Coverage remain visible component diagnostics. They are checked and can produce warnings, but they are not duplicated as independent hard quality gates because Visual Accuracy already combines those source-relative dimensions. Plan Execution Accuracy remains a renderer-correctness diagnostic; only catastrophic execution divergence can independently reject a plan.

A 100% Plan Execution score therefore cannot make a visually inaccurate plan pass.

Gate thresholds are centralized and get stricter as more time is available. Microsoft Paint receives a stricter visual threshold than fast browser drawing profiles.

## One bounded rescue replan

Auto may perform at most one second planning pass:

- **deadline rescue:** Smart paths + Extra Fast 2.0, Fast delivery, stronger simplification and a smaller protected colour ceiling.
- **quality rescue:** only when real schedule headroom exists; increases planning/detail quality and colour allowance without knowingly breaking a tight timer.

The rescue attempt is capped at one pass and is skipped for a slow preview planning pass.

## Diagnostics

Preview diagnostics expose:

- selected Auto strategy
- renderer / quality / detail / speed
- colour ceiling
- acceptance status
- Visual Accuracy gate
- usable deadline and schedule headroom
- whether a rescue pass was used

## Safety and scope

Step 11 does not change CanvasGuard, Safe Fill Mask, calibration coordinates, arming/locks, native input safety or profile-isolated storage. It uses no AI/ML, OCR, network access or telemetry.
