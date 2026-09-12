# Image Draw Bot v1.0.145-rc14 — Resume & Checkpoints

- Add schema-3 resume checkpoints for final progressive / Pixel Accurate execution sequences.
- Track completed operations with a compact order-independent canonical bitset, so Dynamic Replanner reordering does not invalidate safe completed work.
- Resume skips only exact operation hashes after final-plan context and sequence-multiset verification.
- Persist sequence progress every 25 completed operations, on explicit Stop, and before exiting recoverable browser interruptions.
- Treat a temporarily missing/hidden browser target as checkpointable, but still require explicit Start plus normal target recalibration/preflight before any mouse input resumes.
- Keep old color-batch/path-level checkpoints fully backward compatible; changed geometry or sequence content safely rejects resume.
