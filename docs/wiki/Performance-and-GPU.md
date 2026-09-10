# Performance and GPU

Image Draw Bot uses CPU processing with optional GPU acceleration for supported preparation tasks. A dedicated GPU is not required.

## Start with Auto

Leave GPU acceleration, RAM/VRAM budget and CPU workers on Auto initially. The local hardware tuner can benchmark supported resources and recommend settings. A larger resource allocation does not automatically make every operation faster.

- **NVIDIA:** compatible CuPy/CUDA can accelerate supported palette/image processing.
- **AMD, Intel and NVIDIA:** supported OpenCL drivers and the optional backend can accelerate eligible workloads.
- **CPU fallback:** available when a suitable GPU/backend is absent. Not every stage is implemented on the GPU.

## Preparation time versus drawing time

GPU acceleration can reduce some image-preparation work. Actual drawing is also limited by the number of strokes, color switches, target brush behavior and how quickly the target accepts input. Faster preparation does not imply an equally large speedup while drawing.

## Practical tuning

1. Start with a simple image and default resources.
2. If preparation is slow or uses too much memory, reduce planning resolution/detail.
3. If drawing is slow, try Extra Fast, reduce unnecessary detail and allow suitable fills.
4. If actions are missed, reduce input speed and check calibration with a small test.
5. Change one setting at a time and compare both preview and real results.

[Settings and Tooltips](Settings-and-Tooltips) · [Drawing Modes](Drawing-Modes)
