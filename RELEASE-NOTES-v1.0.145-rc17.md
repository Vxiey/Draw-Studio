# Image Draw Bot v1.0.145-rc17 — Unified Execution Cost ETA

- Use the same stateful `ExecutionCostModel` for visible Estimated Draw Time that Adaptive Region Hybrid uses for planner decisions.
- Cost ordered cursor travel, sampled drag moves, palette switches and verified brush switches from the actual final execution sequence.
- Reuse Region Fill Engine's batch-aware contour/Fill/tool-switch estimate instead of maintaining a second Fill timing approximation.
- Add a cold calibration override to `ExecutionCostModel`; DrawTimeCalibration is applied exactly once after the complete base estimate.
- Support explicit Fill, verification, tool, palette and brush operation entries in the shared sequence cost model.
- Export ETA breakdown metadata for sequence, Fill, background Fill and outside-sequence overhead so estimate errors can be diagnosed from logs.
