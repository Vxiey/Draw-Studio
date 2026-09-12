# Image Draw Bot v1.0.145-rc18 — Unified Region Fill Cost

- Make Region Fill compare connected scanlines against Outline + Fill with the shared stateful `ExecutionCostModel`.
- Include real ordered scanline cursor travel, sampled drag cost and the configured Fill/tool/verification switch cost in Fill decisions.
- Keep the existing Region Fill safety gates unchanged: leak prediction, thin-neck blockers, source masks, diagonal pre-seals and runtime flood verification remain authoritative.
- Keep the previous Region Fill timing formula only as a safe fallback if the shared execution model cannot cost an unusual region.
- Use the same execution-model tool-switch cost when batching same-colour Fill regions so per-region tool overhead is removed consistently.
- Export the active Fill cost policy in Region Fill metadata for diagnostics.
