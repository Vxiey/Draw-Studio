# GPU palette and Extra Fast optimization

Implemented on the existing main branch. No release tag or Windows binary is created by this change.

## Changes

- CUDA palette matching now uses one fused elementwise kernel per bounded tile. Each thread keeps its best palette candidates in registers instead of allocating pixel-by-palette distance and penalty arrays. Palette buffers are uploaded once per call, tile buffers are reused, and only int16 results are downloaded. Kernel objects are cached without retaining image data.
- CUDA tile sizing respects available device memory and an existing CuPy pool limit, caps tile storage at 16 MiB, and bounds palette comparisons per launch. Backend failures retain the existing CPU fallback. This does not change global pool settings.
- OpenCL palette mapping reuses bounded buffers and checks cancellation between tiles instead of uploading a whole float32 RGBA frame.
- CPU palette mapping uses blocks of at most 4096 pixels and 32 colors. First-candidate ties and custom-color preference are preserved across block boundaries.
- Palette byte values are explicitly normalized. A near-black byte image or palette containing only 0/1 must not be interpreted as normalized 0..1 color values.
- OpenCL RGB-nearest mapping no longer adds perceptual penalties. OpenCL edge borders now follow the CPU/CUDA convention, including single-row and single-column images.
- Extra Fast avoids repeated cost/ordering work for identical candidate geometry. It also tests a lossless vertical alternative for tall, narrow horizontal regions. Holes and protected portrait outlines remain intact. The existing downstream cost guard keeps the baseline when the proposal regresses. Mask size, dimensions, and output run count are bounded.
- Windows packaging includes CudaPalette explicitly.

These changes accelerate the existing numeric planning path; they do not make Paint accept mouse input faster. The Extra Fast orientation change reduces unnecessary turns without deleting pixels. Existing preview safety behavior remains in place. GPU ranking of many simulated stroke plans is a possible later extension, not part of this patch.

## Verification

82 targeted tests: 80 passed; 2 hardware-dependent tests skipped because this environment has neither CuPy/CUDA nor an OpenCL GPU. Coverage includes palette chunk boundaries, alpha/white masks, custom colors, first-candidate ties, near-black values, cancellation, memory bounds, exact raster coverage, holes, portrait barriers, existing golden-image checks, and CPU fallback behavior.

The exact CUDA scalar scoring body was compiled as ordinary C++ and compared against the NumPy reference for RGB and perceptual matching, all three fidelity modes, and custom-color preference. This validates scalar math, not CUDA compilation, device behavior, or GPU speed. Optional CUDA and OpenCL tests are included for machines with those backends.

Local CPU experiment: fixed-seed random 512x384 RGBA input, 64 colors, Balanced fidelity, median of three calls on each version. Before: 0.6018 seconds. After: 0.5309 seconds, approximately 11.8% less time. Index maps and visibility masks were identical. This is a small local synthetic measurement, not a general performance guarantee or a GPU result.

Tall-region fixture: five-pixel-wide, 340-pixel-tall body. Selected execution has one path and ten vertices, with identical raster coverage. Modeled execution cost changes from 0.355060 to 0.352187 seconds; these are model predictions, not measured Paint timings.

## Benchmark on the target machine

Run from the project directory with its installed Python environment:

```sh
python benchmark_gpu_pipeline.py --mode "NVIDIA CUDA" --width 1024 --height 768 --colors 64
python -m unittest test_gpu_pipeline_optimization -v
```

The benchmark uses the existing verified hardware profile. Read `route.accelerated` and `route.backend_id`; requesting CUDA does not guarantee CUDA was available. First-call cost and warm median are reported separately. Timings include completed transfers, CPU preparation, and synchronization. Index and mask mismatches against CPU are reported; inspect any mismatch before relying on device output.

## Sources consulted

- [CuPy user-defined kernels](https://docs.cupy.dev/en/stable/user_guide/kernel.html): elementwise scalar kernels and raw array indexing.
- [CuPy performance practices](https://docs.cupy.dev/en/stable/user_guide/performance.html): identify bottlenecks, distinguish startup/JIT cost, and measure asynchronous work correctly.
- [CuPy memory management](https://docs.cupy.dev/en/stable/user_guide/memory.html): reusable allocation pools and pool limits.
