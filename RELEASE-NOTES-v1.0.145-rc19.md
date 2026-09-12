# Image Draw Bot v1.0.145-rc19 — Extra Fast Unified Execution Cost

- Move Extra Fast 2.0 path-limit, axis-reorientation and downstream regression decisions from `HybridCostModel` to the shared stateful `ExecutionCostModel`.
- Reuse the exact source-to-canvas scale already supplied by DrawBot, so candidate costs match real canvas motion rather than source-space stroke count.
- Add a compatibility surface (`path_seconds`, `paths_seconds`, scale and path coefficients) to `ExecutionCostModel` without introducing a second timing implementation.
- Keep Extra Fast's complete baseline fallback: a proposal is accepted only when the downstream capped/ordered plan is no slower than baseline.
- Move the Extra Fast synthetic benchmark and execution telemetry onto the same shared cost model.
- Preserve all lossless overlap-only connector and raster-identity guarantees.
