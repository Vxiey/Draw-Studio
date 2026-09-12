# Image Draw Bot v1.0.145-rc6 — Region Brush Packing

- Add exact multi-brush region packing for verified browser brush ladders such as Gartic `2 / 4 / 8 / 16 / 28 px`.
- Remove the previous requirement for a verified 1 px brush before broad-brush hybrid planning can run.
- Pack large safe interiors largest-first, then progressively use smaller verified brushes for residual coverage.
- Simulate every brush footprint against the exact connected source component and reject any candidate that spills outside it.
- Fall back to existing connected runs when the smallest verified brush cannot repair a region exactly.
- Fix even-sized brush erosion so 2/4/8/16/28 px center safety matches the execution footprint.
- Prevent isolated hybrid paths from requesting a brush size that the target does not expose.
