# Image Draw Bot v1.0.144-rc14 — Total Draw Timer & Automatic Pixel Brush

- Add a visible live drawing timer with elapsed time, estimated remaining time and projected total while a real drawing is running.
- Show the exact measured **Total draw time** after a completed drawing and keep it visible in Safety & draw and the preview workspace.
- Make Brush width support **Auto** as the default while preserving manual 1–50 px input and old saved numeric settings.
- Select the automatic baseline from target canvas size plus image edge/color complexity, with 1 px retained for Pixel Accurate and protected-detail workflows.
- Microsoft Paint preparation now sets the requested/automatic Pencil pixel size through verified UI Automation RangeValuePattern instead of always forcing 1 px.
- Keep browser adaptive brush switching safe: only verified controls are used, with smallest verified brushes reserved for fine details/corrections.
- Isolate learned ETA calibration by rendering mode, preset, draw quality and render style in addition to profile/tool/brush/color workflow.
- Existing CanvasGuard, calibration, cancellation and manual brush fallbacks remain mandatory.
