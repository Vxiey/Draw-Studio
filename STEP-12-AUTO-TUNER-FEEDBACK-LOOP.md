# Step 12 — Auto Tuner Feedback Loop + Real Draw Learning

Step 12 makes the Step 11 auto tuner learn from completed **real local drawings**.
It is deterministic and local-only. It does not use ML, network telemetry, OCR,
account data, source image pixels, screenshots, prompts or remote services.

## What is learned

After a clean completed real draw, Draw Studio records compact metrics only:

- planned draw time versus actual wall-clock draw time
- deadline pass/fail
- acceptance-gate pass/fail
- completion and structural completion ratios
- safety delivery ratio
- panic/catch-up usage
- optional trusted post-draw Visual Accuracy when a read-only canvas snapshot is safely available

If a trusted final-canvas snapshot is unavailable, the feedback loop uses a clearly
labelled **runtime delivery proxy**. It never pretends that simulated plan accuracy
was measured from the real final canvas.

## Profile isolation

Feedback is stored per target profile:

- Microsoft Paint
- Gartic Phone
- Skribbl.io
- other future profiles

Inside each profile, learning is also separated by source kind, deadline class,
strategy, active tool, brush width and custom-colour workflow. A Paint custom RGB
sample cannot influence Gartic/Skribbl timing or strategy choices.

## How the tuner uses it

After at least three clean samples for the same isolated context, Step 12 can make
one bounded deterministic adjustment before planning:

- protect deadline: reduce colour ceiling and prefer faster Extra Fast 2.0 settings
- buy quality: spend spare real-world headroom on detail/precision/colour count
- promote deadline rescue: use the rescue strategy first when real history proves it is more reliable

Short 75/80-second rounds remain deadline-first. The feedback loop will not buy
extra quality unless real history shows enough headroom.

## Safety rules

The feedback loop ignores:

- dry runs
- tests
- resumed drawings
- samples under one second
- samples without a usable prediction

The database contains bounded EWMA counters and short history rows only.
It does not persist screenshots or image pixels.
