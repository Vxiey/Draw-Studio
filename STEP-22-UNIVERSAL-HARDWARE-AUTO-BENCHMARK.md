# Step 22 — Universal Hardware Auto Benchmark + Adaptive Performance Profile

Image Draw Bot now treats GPU capability as a set of measured compute backends rather than assuming that GPU means CUDA.

## Hardware detection

The local hardware probe detects:

- NVIDIA GPUs
- AMD Radeon GPUs
- Intel Arc / Intel integrated GPUs
- multiple adapters in the same PC
- total/reported GPU memory, driver version and adapter identity when Windows exposes them

Detection is independent from CUDA/OpenCL availability. A GPU can be shown as detected even when no optional compute backend is usable.

## Compute backends benchmarked

Image Draw Bot benchmarks synthetic arrays only:

- CPU / NumPy — always available
- NVIDIA CUDA / CuPy — when CUDA is usable
- OpenCL — when the installed NVIDIA/AMD/Intel graphics driver and PyOpenCL expose a GPU device

OpenCL is optional. On AMD/Intel systems `Start.bat` attempts to install the Python binding only inside Image Draw Bot's `.venv`. It never installs or updates a system GPU driver.

## Workload-specific selection

The benchmark measures both small and larger batches for:

- OKLab-style color math
- palette matching
- edge-map work
- bulk matrix/pixel processing

A GPU is selected for a workload only when the measured large-batch speed beats CPU by a safety margin. A crossover threshold prevents small jobs from being moved to a GPU when transfer/dispatch overhead makes CPU faster.

## Adaptive hardware profile

The local profile stores only compact hardware/performance metadata:

- hardware signature
- detected adapters and drivers
- CPU/RAM information
- backend throughput scores
- preferred backend per workload
- safe GPU-memory budget
- tile-size recommendation

The signature includes CPU, RAM, GPU identity/driver and compute-runtime versions. A missing/stale profile triggers a deferred automatic re-benchmark after startup. The automatic pass does not change manual settings.

## Multi-GPU

All visible compute devices are benchmarked independently. Image Draw Bot chooses a preferred backend per workload; Step 22 does not split one workload across multiple GPUs.

## Safety and privacy

The benchmark:

- never moves/clicks the mouse
- never captures the screen
- never uses user images
- never sends telemetry
- never accesses the network during the benchmark itself
- always retains CPU fallback

## Current renderer boundary

Step 22 measures vendor-neutral CUDA/OpenCL compute capability and records it in the adaptive profile. Existing image-analysis renderer acceleration remains CUDA-backed where currently implemented; AMD/Intel measurements are available to the hardware profile and future vendor-neutral compute routing without falsely advertising unsupported renderer acceleration.
