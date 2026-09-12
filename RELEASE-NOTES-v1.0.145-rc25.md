# Image Draw Bot v1.0.145-rc25 — Extra Fast Regional Quality Fix

- Replace destructive Extra Fast path-count truncation with Adaptive Region Hybrid scheduling for normal full-colour runs.
- Schedule whole connected regions by visual value against the real execution-cost/time model instead of dropping large portions of a portrait after planning.
- Preserve Gartic's verified five-brush ladder (2/4/8/16/28 px) through per-path brush execution so large safe regions are not forced through the smallest brush.
- Force Extra Fast detail policy back to Auto so stale saved Strong simplify settings cannot erase important facial, contour or small-object structure before planning.
- Treat the adaptive regional plan as a first-class prebuilt execution plan so generic path caps, stroke optimizers and a second deadline pass cannot prune it again.
- Make Simulated final rasterize the same regional execution sequence and per-path brush widths used by Draw.
- Preserve the proven legacy Fill route when a profile advertises Fill capability but has no executable Fill actions; calibrated Fill and no-Fill browser runs use the regional route safely.
- Keep rc24's exact connected-region H/V planning and Sketch dense fallback, while improving real Extra Fast quality/execution parity.
- Synchronize installer, current-facing documentation and regression version assertions atomically to rc25.
