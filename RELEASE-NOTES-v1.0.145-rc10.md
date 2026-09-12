# Image Draw Bot v1.0.145-rc10 — Pixel Accuracy 2.0

- Add connected-region accuracy scores so poor local regions are visible even when global Pixel Accuracy is high.
- Score color correctness, coverage, edges and protected details per region.
- Record marginal correction gain, repaired pixels and gain per path for every correction pass.
- Stop later correction refinement when the simulated quality gain no longer justifies correction work.
- Preserve the existing CPU/GPU stroke simulation, coverage and pixel-error safety pipeline.
