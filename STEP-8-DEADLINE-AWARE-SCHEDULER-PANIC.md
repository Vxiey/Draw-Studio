# Step 8 — Deadline-aware Scheduler + Panic Mode

Step 8 adds a live runtime deadline controller on top of the existing safe planning pipeline.

## Runtime policy

- **NORMAL** — execute the planned quality sequence.
- **CATCH_UP** — when live measured speed shows the plan tightening, preserve coverage/structure and trim low-value detail, accuracy and correction work.
- **PANIC** — when the remaining plan no longer safely fits, switch to structure-first scheduling. Major coverage and silhouettes remain protected; cleanup/correction is dropped and only exceptionally important, cheap details can survive.

## Live timing

The scheduler learns from actual elapsed execution time with a bounded EMA. It continuously reprojects the remaining plan using the measured runtime multiplier and operation type where enough samples exist. This reacts to browser/Paint lag, palette/tool overhead and machine-specific mouse delivery without rewriting geometry.

## Safety

- Uses the **render budget**, not the full game timer, so the Time Budget Engine safety reserve remains intact.
- Never invents shortcut geometry or changes target RGB.
- Extra Fast 2.0 safe connected paths remain the runtime speed strategy; Panic only changes scheduling priority.
- Structural coverage is gated before micro-detail.
- A hard render guard stops optional work before the usable budget is exhausted.

## Telemetry

Live status now exposes mode, strategy, elapsed time, budget left, predicted finish, schedule headroom, operations/sec, live runtime multiplier/sample count, current phase, structural coverage and skipped work.
