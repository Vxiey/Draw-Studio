# Extra Fast review

Extra Fast now joins adjacent overlapping vertical runs as well as horizontal runs. It reuses the existing overlap-only connector, protects portrait edge prefixes, and keeps the previous path plan when the intrinsic cost model predicts an increase. The comparison uses target canvas scaling. Color selection and source geometry remain unchanged.

Fill selection rejects nonfinite costs, preserves an explicit zero UI delay, and checks cancellation inside legacy cost loops. Unlimited mode overrides a stale active deadline flag.

## Reproduce

- `python -m unittest discover -q`
- `python benchmark_extra_fast.py`

The new regression tests include 80 deterministic random masks with holes and multiple colors, mixed orientations, portrait edges, cost-based fallback, cancellation, invalid costs and batch overhead.

## Synthetic comparison

| Input | Previous paths | Updated paths | Exact source raster |
| --- | ---: | ---: | --- |
| Vertical block | 280 | 3 | Yes |
| Horizontal block | 3 | 3 | Yes |
| Vertical region with hole | 381 | 4 | Yes |
| Separate colors | 270 | 4 | Yes |
| Thin separated lines | 94 | 94 | Yes |
| Mixed orientations | 132 | 4 | Yes |

These are source-raster checks with a one-pixel stroke. Fewer paths mean fewer press/release boundaries, not a proportional reduction in total drawing time. The intrinsic estimate excludes downstream travel ordering. This is not a live Skribbl/Gartic or Windows input measurement; input delivery, brush footprint and real canvas timing still need validation on the target application. No mouse or network drawing commands are sent by the benchmark.

Local validation: all 1,317 unit tests passed in 78.890 seconds. All six synthetic comparisons preserved source raster coverage.
