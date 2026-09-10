# Image Draw Bot v1.0.124-beta — Step 23 Universal GPU Acceleration Engine

## Added

- New `UniversalGpuAcceleration.py` routing layer backed by the Step 22 hardware profile.
- Real per-workload CUDA/OpenCL/NumPy routing for OKLab, palette, DeltaE, quantization, edge and pixel math.
- NVIDIA CUDA/CuPy support with explicit device selection from the measured backend id.
- AMD, Intel and NVIDIA OpenCL kernels for real OKLab, DeltaE, edge, palette and pixel operations.
- Workload-size crossover handling so small operations remain on CPU when faster.
- Per-backend/per-workload runtime quarantine and immediate NumPy fallback after driver/kernel failure.
- Universal acceleration metadata in Pixel Accurate planning, accuracy diagnostics and correction diagnostics.
- Step 23 compute-backend test in the GPU UI.

## Preserved

- CPU/NumPy deterministic fallback.
- Existing `NVIDIA CUDA` explicit mode.
- Existing palette fidelity and dominant-hue behaviour.
- Existing renderer geometry, mouse delivery, CanvasGuard and deadline safety behaviour.

## Not changed

Step 23 accelerates analysis/planning workloads. Mouse drawing itself remains a single controlled input stream.
