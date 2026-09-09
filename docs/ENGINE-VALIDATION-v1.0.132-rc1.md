# Engine validation — v1.0.132-rc1

## Status

Local source candidate; not a published release. No GitHub writes, pushes, tags,
releases or Actions runs were performed. No Windows EXE was built.

## Reproducible CPU planner comparison

The exact supplied v1.0.131-beta source was extracted into a separate reference
tree. The same harness ran reference and candidate sequentially using one worker,
one cold run and three warm timed runs per case. The table reports warm medians.
Allocation tracing ran separately to avoid biasing the wall-time measurements.
Calibration was frozen to empty cold-start state for both versions.

| Case | Reference ms | Candidate ms | Less planning time | Wrong mapped pixels |
| --- | ---: | ---: | ---: | ---: |
| icon | 71.9 | 52.1 | 27.6% | 0 |
| line-art | 75.1 | 49.5 | 34.2% | 0 |
| text-small-detail | 189.2 | 109.4 | 42.2% | 0 |
| cartoon-large-colour | 133.1 | 98.9 | 25.7% | 0 |
| photo-gradient | 151.7 | 96.8 | 36.2% | 0 |
| fill-risk | 114.1 | 66.5 | 41.7% | 0 |
| thin-diagonals | 319.0 | 225.0 | 29.5% | 0 |
| many-islands | 120.7 | 116.8 | 3.3% | 0 |

The sum of case medians fell from 1.175 s to 0.815 s (30.6%). This is an eight-case
CPU planner result, not an FPS number or a Paint/browser drawing-speed claim.
The smallest improvement (many-islands, 3.3%) may be within host timing noise.
No case regressed in this run. Operation counts were unchanged in these unlimited
plans. Deadline splitting is tested separately and can increase operation count
in exchange for shorter interruptible units.

All eight simulations had zero mismatched pixels against the quantized PixelMap.
This proves the tested 1px simulated geometry, not perfect reproduction of the
original image, physical brush behavior, antialiasing or actual target input delivery.
The photo case is a synthetic gradient, not a photographic test corpus.

Traced peak allocations were essentially unchanged for the simple fills; they
fell from 2,474,880 to 1,989,460 bytes on thin-diagonals and from 1,955,296 to
1,310,056 bytes on many-islands. These numbers exclude prebuilt PixelMaps and
untraced driver/native memory; they are not total RAM or VRAM measurements.

Raw evidence: engine-benchmarks/reference-v1.0.131-beta.json and
engine-benchmarks/candidate-v1.0.132-rc1.json. The candidate was measured before
its release version metadata was stamped; the recorded measured version remains
unaltered in the JSON.

Reproduce from an activated environment:

```console
python benchmark_engine.py --source-tree ../previous-source --output baseline.json
python benchmark_engine.py --output candidate.json
python -m unittest discover
python DrawBot.py --self-test
```

## Integration audit

| Area | Implementation and validation boundary |
| --- | --- |
| Hybrid strategy selection | Existing HybridRenderer3 source analysis and specialized routes retained; pure policy tests cover routing. |
| Exact region geometry | Vectorized runs, safe H/V candidates, reversal fix, bounded component jobs; independent raster tests cover holes, transparency, tiny components and serial/parallel equivalence. |
| Deadline adaptation | Existing phase scheduler improved with shorter exact paths, fit guard, pause exclusion and uncertainty telemetry; fake-clock tests cover the decisions. |
| Preview | Existing same-plan preview retained; normalized-source cache now also requires source identity. GUI rendering itself was not exercised on Windows. |
| Corrections | Existing trusted-snapshot gates retained; source-relative gain and conservative brush-envelope checks added. This is model validation, not measured physical brush calibration. |
| Recovery | Existing batch/path recovery retained and strengthened with geometry/context fingerprints. Progressive multi-pass crash recovery remains deliberately rejected; boundary pause/resume in the running process remains available. |
| CPU/GPU and tuning | Existing resource allocation, hardware benchmark, GPU routing and CPU fallback retained; bounded candidate queues added. Physical GPU performance and OOM recovery are not verified here. |
| Fills | Existing closed-region and runtime mask guards retained. Legacy Off default fixed. Exact Pixel Accurate bucket-fill remains disabled where its simulator cannot prove equivalence. |
| Advanced ideas | Arbitrary selective supersampling, a general dirty-tile replanner and inferred physical brush-shape calibration were not added. Existing detail zoom, cache invalidation and calibration remain the supported paths. |
| Packaging | Source hygiene, metadata, local source gate and archive integrity are checked. Windows installer/EXE round-trip remains a release blocker. |

## Remaining target-environment checks

A Windows machine with actual target applications is needed to verify GUI startup,
mouse event delivery, real fill leakage, physical brush footprint, DPI/zoom changes,
focus loss, pause/stop during drawing, installer round-trip and GPU execution.
This environment reports CPU fallback and has no usable NVIDIA/CuPy backend.
Do not publish this candidate as fully validated until those checks pass.

Older recovery checkpoints may be rejected by the stronger fingerprint. This
prevents skipping work under a changed plan; it does not restore input permission.
Manual GPU setup is now explicit; normal launch no longer installs GPU packages.

## Automated verification

Final source-test and gate results are recorded in engine-test-results.json.
The original baseline ran 1,241 tests with one failure: legacy Auto Fill Off still
planned a fill. That underlying default-handling error is fixed in this candidate.
