"""Adaptive phase scheduler for Image Draw Bot v1.0.44.

This module is pure planning logic: it never touches the mouse, screen or GUI.
It decides which resource profile each planning phase should use and stores a
small per-machine recommendation from the CPU/RAM benchmark.
"""
from __future__ import annotations

import json
import math
import os
import platform
import tempfile
import time
from pathlib import Path
from typing import Any

from RuntimePaths import data_dir

RESOURCE_SCHEDULER_MODES = ("Auto", "Off", "Benchmark recommendations")
SCHEDULER_FILE = data_dir() / "resource-scheduler-v2.json"


def validate_resource_scheduler(value: str) -> str:
    if value not in RESOURCE_SCHEDULER_MODES:
        raise ValueError("Resource scheduler must be Auto, Off or Benchmark recommendations.")
    return value


def machine_signature(*, logical_cpus: int | None = None, ram_mb: int | None = None) -> str:
    cpus = max(1, int(logical_cpus or (os.cpu_count() or 1)))
    ram_bucket = "unknown" if ram_mb is None else str(max(1, int(ram_mb) // 1024)) + "GB"
    return f"{platform.system() or 'OS'}|{platform.machine() or 'machine'}|cpu{cpus}|ram{ram_bucket}"


def _safe_cap(logical_cpus: int, *, preview: bool = False) -> int:
    total = max(1, int(logical_cpus or 1))
    if total <= 2:
        return 1
    if preview:
        return max(1, min(4, total - 1))
    if total <= 4:
        return total - 1
    if total <= 8:
        return min(6, total - 1)
    if total <= 16:
        return min(10, total - 2)
    if total <= 24:
        return min(12, total - 3)
    # This is the important safety/performance guard: Auto never consumes all
    # 32+ logical CPUs because Tk, Paint and Windows input need headroom and many
    # image-planning tasks slow down beyond the memory/cache sweet spot.
    return min(16, total - 4)


def _requested_workers(requested: str, logical_cpus: int) -> int | None:
    total = max(1, int(logical_cpus or 1))
    if requested == "Auto":
        return None
    if requested == "All logical":
        return total
    try:
        return max(1, min(total, int(str(requested))))
    except (TypeError, ValueError):
        return None


def load_recommendation(path: Path | None = None, *, signature: str | None = None) -> dict[str, Any] | None:
    path = Path(path or SCHEDULER_FILE)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or int(data.get("version", 0)) != 2:
        return None
    sig = signature or machine_signature(logical_cpus=data.get("logical_cpus"), ram_mb=data.get("ram_budget_mb"))
    if data.get("machine_signature") != sig:
        return None
    return data


def save_recommendation(result: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    path = Path(path or SCHEDULER_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = {
        "version": 2,
        "created_at": int(time.time()),
        "machine_signature": str(result.get("machine_signature") or machine_signature(
            logical_cpus=int(result.get("logical_cpus", os.cpu_count() or 1) or 1),
            ram_mb=result.get("ram_budget_mb"))),
        "logical_cpus": int(result.get("logical_cpus", os.cpu_count() or 1) or 1),
        "recommended_workers": int(result.get("recommended_workers", 1) or 1),
        "recommended_engine": str(result.get("recommended_engine", "Threads")),
        "best_score": float(result.get("best_score", 0.0) or 0.0),
        "scores": result.get("scores", []),
        "ram_budget_mb": int(result.get("ram_budget_mb", 0) or 0),
    }
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
        tmp = Path(handle.name)
        json.dump(clean, handle, ensure_ascii=False, indent=2)
        handle.flush()
    tmp.replace(path)
    return clean


def recommended_workers(allocation: dict[str, Any], *, mode: str = "Auto", preview: bool = False,
                        recommendation: dict[str, Any] | None = None) -> tuple[int, str]:
    validate_resource_scheduler(mode)
    logical = max(1, int(allocation.get("logical_cpus", os.cpu_count() or 1) or 1))
    requested = _requested_workers(str(allocation.get("cpu_workers", "Auto")), logical)
    if mode == "Off":
        # Old behaviour: respect ResourceAllocation's resolved value.
        return max(1, min(logical, int(allocation.get("cpu_workers_resolved", requested or 1) or 1))), "scheduler off"
    if requested is not None:
        if requested >= logical and logical >= 24:
            return max(1, logical - 2), "manual all-logical guarded for UI/input headroom"
        return requested, "manual worker setting"
    cap = _safe_cap(logical, preview=preview)
    rec = recommendation or load_recommendation(signature=machine_signature(logical_cpus=logical, ram_mb=allocation.get("ram_budget_mb")))
    if mode == "Benchmark recommendations" and rec and int(rec.get("recommended_workers", 0) or 0) > 0:
        return max(1, min(cap, int(rec["recommended_workers"]))), "saved per-machine benchmark"
    if rec and int(rec.get("recommended_workers", 0) or 0) > 0:
        # Auto can use saved benchmark, but still keeps the UI/input headroom cap.
        return max(1, min(cap, int(rec["recommended_workers"]))), "auto + saved benchmark cap"
    return cap, "auto safe cap"


def phase_workers(base_workers: int, phase: str, *, pixels: int, preview: bool = False) -> int:
    base = max(1, int(base_workers or 1))
    pixels = max(1, int(pixels or 1))
    if preview:
        if pixels < 60_000:
            return 1
        if pixels < 180_000:
            return max(1, min(2, base))
        return max(1, min(4, base))
    if phase == "color_analysis":
        return max(1, min(base, 8 if pixels < 800_000 else 12))
    if phase == "image_matrix":
        return max(1, min(base, 4))
    if phase == "shape_extraction":
        if pixels < 80_000:
            return 1
        if pixels < 260_000:
            return max(1, min(base, 4))
        return max(1, min(base, 12))
    if phase in ("importance_map", "region_scoring", "correction_scoring"):
        if pixels < 80_000:
            return 1
        return max(1, min(base, 4 if pixels < 500_000 else 8))
    if phase == "connected_components":
        if pixels < 100_000:
            return 1
        return max(1, min(base, 4 if pixels < 500_000 else 10))
    if phase == "path_optimization":
        return max(1, min(base, 4))
    return base


def choose_image_matrix_backend(*, gpu_mode: str, gpu_available: bool, pixels: int, preview: bool = False,
                                recommendation: dict[str, Any] | None = None) -> tuple[str, str]:
    requested = str(gpu_mode or "Auto")
    if requested == "CPU":
        return "CPU", "CPU mode selected"
    if preview:
        return "CPU", "preview stays CPU to keep UI cancellable"
    if not gpu_available:
        return "CPU", "CUDA unavailable or untested"
    if int(pixels or 0) < 160_000:
        return "CPU", "image too small for GPU transfer overhead"
    if recommendation and recommendation.get("gpu_matrix_backend") == "CPU":
        return "CPU", "saved benchmark prefers CPU for matrix work"
    return "GPU", "large matrix/resize work benefits from CUDA when available"


def _chunk_hint(height: int, width: int, workers: int, ram_mb: int) -> dict[str, int]:
    height=max(1,int(height or 1)); width=max(1,int(width or 1)); workers=max(1,int(workers or 1)); ram_mb=max(128,int(ram_mb or 512))
    bytes_per_row = max(1, width * 64)
    rows = max(8, min(256, (ram_mb * 1024 * 1024) // max(1, workers * 4 * bytes_per_row)))
    target_chunks = max(1, workers * 2)
    if math.ceil(height / rows) < target_chunks:
        rows = max(8, math.ceil(height / target_chunks))
    chunks = math.ceil(height / rows)
    return {"rows_per_chunk": int(rows), "chunks": int(chunks)}


def resolve_resource_schedule(allocation: dict[str, Any], *, mode: str = "Auto", area: tuple[int, int] | list[int] | None = None,
                              drawing_mode: str = "Smart paths (recommended)", gpu_mode: str = "Auto",
                              gpu_available: bool = False, preview: bool = False,
                              recommendation: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_resource_scheduler(mode)
    try:
        width, height = int(area[0]), int(area[1])  # type: ignore[index]
    except Exception:
        width = height = 1
    width=max(1,width); height=max(1,height); pixels=width*height
    base, reason = recommended_workers(allocation, mode=mode, preview=preview, recommendation=recommendation)
    ram_mb = int(allocation.get("ram_budget_mb", 512) or 512)
    engine = str(allocation.get("cpu_engine", "Auto"))
    if engine == "Auto":
        engine = "Threads"
    image_backend, image_reason = choose_image_matrix_backend(
        gpu_mode=gpu_mode, gpu_available=bool(gpu_available), pixels=pixels, preview=preview, recommendation=recommendation)
    phases = {}
    for phase in ("color_analysis", "image_matrix", "importance_map", "connected_components", "region_scoring", "shape_extraction", "path_optimization", "correction_scoring"):
        workers = phase_workers(base, phase, pixels=pixels, preview=preview)
        backend = "CPU/SIMD" if phase == "color_analysis" else (image_backend if phase == "image_matrix" else "CPU")
        phase_reason = {
            "color_analysis": "palette/color math stays CPU-cache friendly",
            "image_matrix": image_reason,
            "importance_map": "vector/edge importance scoring uses bounded CPU workers",
            "connected_components": "connected-region labeling scales only above the small-image threshold",
            "region_scoring": "region safety/value scoring is parallel only when workload is large enough",
            "shape_extraction": "parallel CPU chunks for region/shape extraction",
            "path_optimization": "path ordering is CPU-bound and capped to avoid overhead",
            "correction_scoring": "error/correction candidates use bounded workers",
        }[phase]
        phases[phase] = {"backend": backend, "workers": int(workers), "reason": phase_reason}
    chunks = _chunk_hint(height, width, phases["shape_extraction"]["workers"], ram_mb)
    phases["shape_extraction"].update(chunks)
    return {
        "version": 2,
        "mode": mode,
        "logical_cpus": int(allocation.get("logical_cpus", os.cpu_count() or 1) or 1),
        "base_workers": int(base),
        "effective_cpu_workers": max(phases["color_analysis"]["workers"], phases["shape_extraction"]["workers"], phases["path_optimization"]["workers"]),
        "recommended_engine": engine,
        "ram_budget_mb": ram_mb,
        "pixels": int(pixels),
        "worker_reason": reason,
        "gpu_available": bool(gpu_available),
        "phases": phases,
    }


def _bench_once(workers: int, loops: int) -> float:
    state=0x12345678 ^ workers
    total=0
    loops=max(1000,int(loops))
    started=time.perf_counter()
    # Single-process deterministic approximation.  It is intentionally quick;
    # the result is used for recommendations, not scientific benchmarking.
    for w in range(max(1,int(workers))):
        local=(state + w*2654435761) & 0xffffffff
        for i in range(loops):
            local=(1664525*local + 1013904223 + i) & 0xffffffff
            total ^= ((local >> 7) * 2246822519) & 0xffffffff
    elapsed=max(time.perf_counter()-started,1e-9)
    return (workers*loops)/elapsed/1_000_000


def benchmark_scheduler(allocation: dict[str, Any], *, loops_per_worker: int = 28_000, save: bool = True,
                        path: Path | None = None) -> dict[str, Any]:
    logical=max(1,int(allocation.get("logical_cpus",os.cpu_count() or 1) or 1))
    cap=_safe_cap(logical)
    candidates=[]
    for value in (1,2,4,6,8,10,12,16,24,32):
        if value<=min(logical,cap) and value not in candidates:
            candidates.append(value)
    if not candidates:
        candidates=[1]
    scores=[]
    for workers in candidates:
        score=_bench_once(workers, max(1000, int(loops_per_worker)//max(1,workers)))
        # Penalize very high worker counts slightly to represent GUI/input headroom.
        headroom_penalty = 1.0 - min(0.18, max(0, workers - 8) * 0.012)
        adjusted = score * headroom_penalty
        scores.append({"workers": workers, "score": round(score, 3), "adjusted_score": round(adjusted, 3)})
    best=max(scores, key=lambda item:(item["adjusted_score"], -item["workers"]))
    result={
        "version": 2,
        "machine_signature": machine_signature(logical_cpus=logical, ram_mb=allocation.get("ram_budget_mb")),
        "logical_cpus": logical,
        "ram_budget_mb": int(allocation.get("ram_budget_mb",0) or 0),
        "recommended_workers": int(best["workers"]),
        "recommended_engine": "Threads" if str(allocation.get("cpu_engine","Auto"))=="Auto" else str(allocation.get("cpu_engine","Threads")),
        "best_score": float(best["adjusted_score"]),
        "scores": scores,
    }
    if save:
        save_recommendation(result,path=path)
    return result
