# Draw Studio v1.0.124-beta — Step 22 Universal Hardware Auto Benchmark

## Added

- Vendor-neutral GPU discovery for NVIDIA, AMD and Intel.
- Multi-GPU enumeration without requiring CUDA/OpenCL just to see the hardware.
- Local synthetic CPU/NumPy benchmark.
- Optional CUDA/CuPy microbenchmarks.
- Optional OpenCL microbenchmarks for NVIDIA/AMD/Intel GPU devices.
- Workload-specific backend recommendations for OKLab/color math, palette matching, edge maps and bulk matrix processing.
- Small-vs-large workload crossover thresholds so GPU overhead does not hurt tiny jobs.
- Conservative dedicated-VRAM and integrated/shared-memory budgets.
- Per-machine `hardware-performance-profile-v1.json` with hardware-signature invalidation.
- Deferred automatic re-benchmark on first run or after CPU/GPU/RAM/driver/compute-runtime changes.
- Optional AMD/Intel PyOpenCL bootstrap inside Draw Studio's `.venv` with safe CPU fallback.
- Universal Hardware Auto Benchmark labels/status in the UI.

## Compatibility

- Existing NVIDIA CUDA renderer paths remain compatible.
- Existing `NvidiaGpu`, `detect_nvidia_gpus()` and `best_nvidia_gpu()` APIs remain available.
- CPU mode remains fully supported when no GPU backend is usable.

## Privacy

Only synthetic numeric arrays are benchmarked. No mouse input, screen capture, user image storage, telemetry or network activity is used by the benchmark.

## Not changed

This step does not replace the drawing renderer with OpenCL. It creates truthful vendor-neutral hardware measurement and selection data first.
