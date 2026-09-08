# Step 23 — Universal GPU Acceleration Engine

Step 23 turns the Step 22 hardware benchmark into real execution routing.

## Real workloads routed per machine

Draw Studio now consults the saved Step 22 hardware profile for each workload:

- OKLab conversion
- palette matching
- source-relative OKLab/DeltaE analysis
- quantization distance work
- edge maps
- bulk pixel/channel math

The selected backend can differ by workload and image size. Small jobs stay on
NumPy when transfer overhead is measured to be slower than CPU execution.

## Backends

- NVIDIA: CUDA/CuPy when benchmarked fastest; OpenCL can also win a workload.
- AMD: OpenCL when the installed graphics driver exposes a usable OpenCL device.
- Intel: OpenCL for Arc/iGPU when usable.
- CPU: NumPy is always available and remains the deterministic fallback.

The legacy `NVIDIA CUDA` mode remains available as an explicit CUDA preference.
`Auto` is the universal vendor-neutral mode.

## Failure isolation

A GPU error quarantines only that backend + workload for the current process.
For example, an Intel OpenCL edge-kernel failure does not disable CUDA palette
matching or CPU OKLab conversion. The failed operation is immediately retried on
NumPy and the rest of the drawing workflow continues.

## Integrated call sites

Step 23 is connected to real Draw Studio paths, including:

- Pixel Accurate palette mapping
- Pixel Accurate edge analysis
- Advanced Color stroke palette mapping
- source-relative accuracy / DeltaE diagnostics
- standalone DeltaE heatmaps
- adaptive color-count quantization geometry
- post-draw correction color analysis

## Privacy and safety

The acceleration engine performs in-memory numeric processing only. It does not
capture the screen, move the mouse, access the network, upload telemetry, or save
user image arrays to disk.
