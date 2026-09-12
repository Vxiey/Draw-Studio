# Image Draw Bot v1.0.145-rc8 — Dynamic Replanner

- Extend the live DeadlineScheduler with bounded runtime replanning.
- Reorder remaining safe paths only when measured execution enters CATCH_UP or PANIC.
- Preserve phase barriers, non-stroke operation barriers, geometry, colors and brush widths.
- Reject a candidate replan if it would increase color/brush transition count.
- Add runtime telemetry for replans, reordered paths and rejected switch-heavy reorderings.
