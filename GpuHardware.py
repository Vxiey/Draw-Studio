"""Vendor-neutral GPU hardware discovery for Draw Studio.

Step 22 expands the original NVIDIA-only probe so the hardware auto tuner can
see NVIDIA, AMD and Intel adapters without assuming CUDA == GPU.  Discovery is
kept independent from optional compute packages: a GPU can be reported even
when CUDA/OpenCL is not installed.  Existing NVIDIA helper APIs remain for
backwards compatibility with the CUDA renderer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Iterable


@dataclass(frozen=True)
class NvidiaGpu:
    # Keep field order stable: older tests/callers construct this positionally.
    index: int | None
    name: str
    memory_total_mb: int | None = None
    driver_version: str = ""
    bus_id: str = ""
    source: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GpuDevice:
    index: int | None
    name: str
    memory_total_mb: int | None = None
    driver_version: str = ""
    bus_id: str = ""
    source: str = ""
    vendor: str = "Unknown"
    vendor_id: str = ""
    pnp_device_id: str = ""
    video_processor: str = ""
    integrated: bool | None = None

    def as_dict(self) -> dict:
        return asdict(self)


_CACHE: tuple[NvidiaGpu, ...] | None = None
_ALL_CACHE: tuple[GpuDevice, ...] | None = None


def _creationflags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def _run(command: list[str], timeout: float = 3.0) -> str:
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=_creationflags(),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or f"exit {completed.returncode}").strip())
    return completed.stdout.strip()


def _nvidia_smi_candidates() -> Iterable[str]:
    seen: set[str] = set()
    found = shutil.which("nvidia-smi")
    if found:
        seen.add(os.path.normcase(found))
        yield found
    if os.name != "nt":
        return
    candidates = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "nvidia-smi.exe",
        Path(os.environ.get("ProgramW6432", r"C:\Program Files")) / "NVIDIA Corporation" / "NVSMI" / "nvidia-smi.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "NVIDIA Corporation" / "NVSMI" / "nvidia-smi.exe",
    ]
    for candidate in candidates:
        key = os.path.normcase(str(candidate))
        if key not in seen and candidate.is_file():
            seen.add(key)
            yield str(candidate)


def _parse_int(value: object) -> int | None:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _vendor_from_text(*values: object) -> tuple[str, str]:
    text = " ".join(str(value or "") for value in values).lower()
    if "ven_10de" in text or "nvidia" in text or "geforce" in text or "quadro" in text:
        return "NVIDIA", "10DE"
    if "ven_1002" in text or "advanced micro devices" in text or "radeon" in text or re.search(r"\bamd\b", text):
        return "AMD", "1002"
    if "ven_8086" in text or "intel" in text or "arc(tm)" in text:
        return "Intel", "8086"
    return "Unknown", ""


def _detect_with_nvidia_smi() -> list[NvidiaGpu]:
    for executable in _nvidia_smi_candidates():
        try:
            output = _run([
                executable,
                "--query-gpu=index,name,memory.total,driver_version,pci.bus_id",
                "--format=csv,noheader,nounits",
            ])
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            continue
        result: list[NvidiaGpu] = []
        for line in output.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 5:
                continue
            index, name, memory, driver = parts[:4]
            bus = ",".join(parts[4:]).strip()
            result.append(NvidiaGpu(_parse_int(index), name, _parse_int(memory), driver, bus, "nvidia-smi"))
        if result:
            return result
    return []


def _powershell_video_controllers() -> list[dict]:
    if os.name != "nt":
        return []
    powershell = shutil.which("powershell") or shutil.which("powershell.exe") or shutil.which("pwsh")
    if not powershell:
        return []
    script = (
        "$g=Get-CimInstance Win32_VideoController | "
        "Select-Object Name,DriverVersion,AdapterRAM,PNPDeviceID,AdapterCompatibility,VideoProcessor,DeviceID; "
        "if($null -ne $g){$g | ConvertTo-Json -Compress}"
    )
    try:
        output = _run([powershell, "-NoProfile", "-NonInteractive", "-Command", script], timeout=5.0)
        if not output:
            return []
        payload = json.loads(output)
    except (OSError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []
    items = payload if isinstance(payload, list) else [payload]
    return [item for item in items if isinstance(item, dict)]


def _detect_with_powershell() -> list[NvidiaGpu]:
    """Legacy NVIDIA-only CIM helper kept for existing callers/tests."""
    result: list[NvidiaGpu] = []
    for item in _powershell_video_controllers():
        name = str(item.get("Name") or "").strip()
        vendor, _vendor_id = _vendor_from_text(name, item.get("AdapterCompatibility"), item.get("PNPDeviceID"))
        if vendor != "NVIDIA":
            continue
        adapter_bytes = _parse_int(item.get("AdapterRAM"))
        memory_mb = int(adapter_bytes // (1024 * 1024)) if adapter_bytes and adapter_bytes > 0 else None
        result.append(NvidiaGpu(None, name, memory_mb, str(item.get("DriverVersion") or ""),
                                str(item.get("PNPDeviceID") or ""), "Windows CIM"))
    return result


def _detect_all_with_powershell() -> list[GpuDevice]:
    result: list[GpuDevice] = []
    for ordinal, item in enumerate(_powershell_video_controllers()):
        name = str(item.get("Name") or "").strip()
        if not name:
            continue
        pnp = str(item.get("PNPDeviceID") or "")
        compatibility = str(item.get("AdapterCompatibility") or "")
        processor = str(item.get("VideoProcessor") or "")
        vendor, vendor_id = _vendor_from_text(name, compatibility, pnp, processor)
        adapter_bytes = _parse_int(item.get("AdapterRAM"))
        memory_mb = int(adapter_bytes // (1024 * 1024)) if adapter_bytes and adapter_bytes > 0 else None
        integrated: bool | None = None
        lower = f"{name} {processor}".lower()
        if vendor == "Intel":
            integrated = not any(token in lower for token in (" arc a", " arc b", "max graphics", "data center gpu"))
        elif any(token in lower for token in ("integrated", "apu", "vega 7", "vega 8")):
            integrated = True
        result.append(GpuDevice(
            ordinal, name, memory_mb, str(item.get("DriverVersion") or ""),
            str(item.get("DeviceID") or ""), "Windows CIM", vendor, vendor_id, pnp, processor, integrated,
        ))
    return result


def _detect_all_with_lspci() -> list[GpuDevice]:
    """Best-effort non-Windows discovery used by tests/development builds."""
    if os.name == "nt":
        return []
    executable = shutil.which("lspci")
    if not executable:
        return []
    try:
        output = _run([executable, "-nn"], timeout=3.0)
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return []
    result: list[GpuDevice] = []
    for line in output.splitlines():
        low = line.lower()
        if not any(token in low for token in ("vga compatible controller", "3d controller", "display controller")):
            continue
        vendor, vendor_id = _vendor_from_text(line)
        name = line.split(": ", 1)[-1].strip()
        bus_id = line.split(" ", 1)[0].strip()
        result.append(GpuDevice(len(result), name, None, "", bus_id, "lspci", vendor, vendor_id))
    return result


def detect_nvidia_gpus(*, refresh: bool = False) -> tuple[NvidiaGpu, ...]:
    global _CACHE
    if _CACHE is not None and not refresh:
        return _CACHE
    found = _detect_with_nvidia_smi()
    if not found:
        found = _detect_with_powershell()
    found.sort(key=lambda gpu: (gpu.index is None, gpu.index if gpu.index is not None else 9999,
                                -(gpu.memory_total_mb or 0), gpu.name.lower()))
    _CACHE = tuple(found)
    return _CACHE


def _norm_device_name(name: str) -> str:
    text = re.sub(r"\([^)]*\)", " ", str(name or "").lower())
    for token in ("nvidia", "geforce", "amd", "radeon", "intel", "graphics", "gpu", "corporation"):
        text = text.replace(token, " ")
    return " ".join(text.split())


def _merge_devices(generic: list[GpuDevice], nvidia: tuple[NvidiaGpu, ...]) -> list[GpuDevice]:
    merged = list(generic)
    used: set[int] = set()
    for ngpu in nvidia:
        best_index = None
        nname = _norm_device_name(ngpu.name)
        for idx, device in enumerate(merged):
            if idx in used or device.vendor != "NVIDIA":
                continue
            dname = _norm_device_name(device.name)
            if nname and dname and (nname in dname or dname in nname):
                best_index = idx
                break
        replacement = GpuDevice(
            ngpu.index, ngpu.name, ngpu.memory_total_mb, ngpu.driver_version,
            ngpu.bus_id, ngpu.source, "NVIDIA", "10DE",
            merged[best_index].pnp_device_id if best_index is not None else "",
            merged[best_index].video_processor if best_index is not None else "",
            merged[best_index].integrated if best_index is not None else False,
        )
        if best_index is None:
            merged.append(replacement)
        else:
            used.add(best_index)
            merged[best_index] = replacement
    # De-duplicate identical CIM rows while preserving physically separate adapters.
    unique: list[GpuDevice] = []
    keys: set[tuple] = set()
    for device in merged:
        key = (device.vendor, _norm_device_name(device.name), device.bus_id or device.pnp_device_id or device.index)
        if key in keys:
            continue
        keys.add(key)
        unique.append(device)
    return unique


def detect_gpus(*, refresh: bool = False) -> tuple[GpuDevice, ...]:
    """Detect NVIDIA, AMD and Intel display adapters without compute dependencies."""
    global _ALL_CACHE
    if _ALL_CACHE is not None and not refresh:
        return _ALL_CACHE
    generic = _detect_all_with_powershell() if os.name == "nt" else _detect_all_with_lspci()
    found = _merge_devices(generic, detect_nvidia_gpus(refresh=refresh))
    vendor_rank = {"NVIDIA": 0, "AMD": 1, "Intel": 2, "Unknown": 9}
    found.sort(key=lambda gpu: (
        vendor_rank.get(gpu.vendor, 8),
        gpu.integrated is True,
        -(gpu.memory_total_mb or 0),
        gpu.index if gpu.index is not None else 9999,
        gpu.name.lower(),
    ))
    _ALL_CACHE = tuple(found)
    return _ALL_CACHE


def best_nvidia_gpu(*, refresh: bool = False) -> NvidiaGpu | None:
    gpus = detect_nvidia_gpus(refresh=refresh)
    if not gpus:
        return None
    return max(gpus, key=lambda gpu: (gpu.memory_total_mb or 0, -(gpu.index or 0)))


def best_gpu(*, refresh: bool = False) -> GpuDevice | None:
    gpus = detect_gpus(refresh=refresh)
    if not gpus:
        return None
    # Discovery cannot know actual compute speed; prefer dedicated/high-memory
    # hardware only as a display default. Step 22 benchmark chooses real backends.
    return max(gpus, key=lambda gpu: (gpu.integrated is not True, gpu.memory_total_mb or 0,
                                      gpu.vendor != "Unknown", -(gpu.index or 0)))


def hardware_summary(*, refresh: bool = False) -> str:
    """Legacy NVIDIA summary used by the CUDA-specific tools."""
    gpu = best_nvidia_gpu(refresh=refresh)
    if gpu is None:
        return "No NVIDIA GPU detected"
    memory = f" · {gpu.memory_total_mb:,} MB VRAM" if gpu.memory_total_mb else ""
    driver = f" · driver {gpu.driver_version}" if gpu.driver_version else ""
    return f"{gpu.name}{memory}{driver} · detected via {gpu.source or 'Windows'}"


def universal_hardware_summary(*, refresh: bool = False) -> str:
    gpus = detect_gpus(refresh=refresh)
    if not gpus:
        return "No discrete/integrated GPU adapter detected; CPU fallback available"
    parts = []
    for gpu in gpus:
        memory = f" {gpu.memory_total_mb:,} MB" if gpu.memory_total_mb else ""
        parts.append(f"{gpu.vendor} {gpu.name}{memory}".strip())
    return " · ".join(parts)


def cupy_smoke_test() -> tuple[bool, str]:
    """Run a tiny real CUDA kernel so missing runtime/header issues are caught."""
    gpu = best_nvidia_gpu(refresh=True)
    if gpu is None:
        return False, "No NVIDIA GPU detected"
    try:
        import cupy as cp
        count = int(cp.cuda.runtime.getDeviceCount())
        if count < 1:
            return False, f"{gpu.name} detected, but CuPy reports no CUDA devices"
        target = gpu.index if gpu.index is not None and 0 <= gpu.index < count else 0
        with cp.cuda.Device(int(target)):
            kernel = cp.RawKernel(
                'extern "C" __global__ void drawstudio_probe(float* x){int i=blockDim.x*blockIdx.x+threadIdx.x;if(i<32)x[i]=x[i]*2.0f+1.0f;}',
                "drawstudio_probe",
            )
            arr = cp.arange(32, dtype=cp.float32)
            kernel((1,), (32,), (arr,))
            cp.cuda.Stream.null.synchronize()
            if float(cp.asnumpy(arr)[3]) != 7.0:
                return False, "CUDA probe returned an unexpected result"
        return True, f"CUDA ready on {gpu.name}"
    except Exception as exc:
        return False, f"{gpu.name} detected, but CUDA/CuPy smoke test failed: {type(exc).__name__}: {exc}"


def _main(argv: list[str]) -> int:
    if "--cupy-smoke" in argv:
        ok, message = cupy_smoke_test()
        print(message)
        return 0 if ok else 2
    if "--all" in argv or "--json" in argv:
        gpus = detect_gpus(refresh=True)
        if "--json" in argv:
            print(json.dumps([gpu.as_dict() for gpu in gpus], ensure_ascii=False))
        elif gpus:
            print(universal_hardware_summary())
        elif "--quiet" not in argv:
            print("No GPU adapter detected")
        return 0 if gpus else 1
    gpus = detect_nvidia_gpus(refresh=True)
    if gpus:
        print(hardware_summary())
    elif "--quiet" not in argv:
        print("No NVIDIA GPU detected")
    return 0 if gpus else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
