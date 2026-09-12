# Image Draw Bot v1.0.145-rc16 — Preview Planner Parity

- Route an explicit **Build preview** through the full-detail/final planner in Manual and Auto full modes.
- Keep Auto light as the deliberately bounded fast approximation for users who prefer minimum preview latency.
- Preserve final-plan geometry, Fill/brush decisions, CanvasGuard policy and execution-time model in the full-detail preview path.
- Raise full-detail preview planning from a forced single CPU worker to a UI-safe maximum of four workers using the existing ResourceAllocation policy.
- Keep preview GPU analysis on CPU so cancellation and UI responsiveness remain deterministic; final Draw still re-evaluates the configured GPU backend.
- Expose preview resource-policy metadata so diagnostics can distinguish exact planner parity from lightweight previews.
