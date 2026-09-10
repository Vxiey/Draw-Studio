# Image Draw Bot v1.0.131-beta — Sketch 2.0 + Auto Fill

## Sketch 2.0

Microsoft Paint sketch planning now combines luminance edges with color-boundary structure, removes isolated noise while protecting small high-contrast features, and keeps the existing browser/Gartic sketch route untouched.

## Sketch + Auto Fill

A new rendering style executes three deterministic phases in strict order:

1. Sketch 2.0 contours
2. Connected color-fill runs using the existing Paint color/custom-RGB planner
3. Final structural re-outline

The existing native bucket-fill prelude is intentionally disabled for this renderer so fill cannot occur before the sketch. CanvasGuard, Target Lock, Safety Preflight, Dry Run, profile isolation and manual-mouse stop remain unchanged.

## Scope

The new renderer is Paint-first in v1.0.131-beta. Browser targets fail closed if it is selected, and Gartic/Skribbl rendering policies are not modified.
