# Image Draw Bot v1.0.145-rc15 — CPU/GPU Performance Engine

- Retry Pixel Accurate CUDA stroke simulation after transient VRAM pressure with progressively smaller row tiles and rectangle batches before CPU fallback.
- Release retained CuPy/pinned memory between bounded OOM retries and expose recovery diagnostics.
- Replace full-frame CUDA accuracy-score allocation with bounded row-tiled scoring that preserves the existing Pixel Accuracy metrics.
- Shrink score tiles on transient OOM before using the deterministic CPU scorer.
- Do not quarantine a measured GPU backend for the whole process when one workload only hits transient allocation pressure.
- Let the Auto resource scheduler reduce CPU workers and planner chunk rows under live RAM pressure while leaving explicit Resource Scheduler = Off behavior unchanged.
- Route large final correction-scoring phases to GPU/CPU fallback metadata when a verified GPU is available.
