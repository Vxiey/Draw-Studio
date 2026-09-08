# Step 24 — Adaptive Detail Zoom Pass

Step 24 adds a bounded source-detail recovery pass without changing Paint or browser page zoom.

## Goal

Recover small source details that were lost when the global planner reduced the source to the target planning resolution.

## How it works

- keeps the untouched original source in memory
- re-analyzes selected high-frequency source regions at 2x or 4x local analysis density
- detects lost edges, local luminance variation and small color accents
- maps recovered source colors through the existing OKLab/Faithful palette pipeline
- adds only detail pixels that visibly differ from the current plan
- groups adjacent same-color detail pixels into safe bounded paths
- uses the smallest verified brush where available
- marks time-budget detail paths optional so Deadline Scheduler/Panic Mode may skip them

## Modes

- `Auto` — choose Off/2x/4x from quality, source-to-plan scale and time budget
- `Off` — no detail zoom pass
- `2x` — force 2x internal source analysis
- `4x` — force 4x internal source analysis

Pixel Accurate is excluded because it already plans against the full target PixelMap.

## Safety

Step 24 never changes target application zoom, browser zoom, Paint zoom, canvas geometry, palette geometry or calibration coordinates. It is an internal source-analysis pass only.

CanvasGuard, Target Lock, Safety Preflight and runtime deadline safeguards remain authoritative.

## Preview

The new `Detail zoom` preview tab shows bounded regions that were revisited for micro-detail recovery. Preview diagnostics report factor, paths/pixels added, brush width and deadline-awareness.
