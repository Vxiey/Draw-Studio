"""Runtime safety reporting for Image Draw Bot v1.0.57.

Records what the real execution path actually did after CanvasGuard + Edge
Behavior decisions. Reports are local-only, deterministic and contain no source
image pixels, screenshots, OCR, AI/ML data or telemetry.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Sequence

from RuntimePaths import atomic_write_text, data_dir
from SafetyDebugOverlay import classify_edge_result
from Version import APP_VERSION


REPORT_DIR = data_dir() / "safety-reports"
REPORT_SCHEMA = 1


def _clean_reason(value: object, limit: int = 300) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return " ".join(text.split())[:limit]


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")[:-3]


@dataclass
class RuntimeSafetySession:
    dry_run: bool = False
    profile_name: str = ""
    edge_behavior: str = ""
    planned_paths: int = 0
    started_monotonic: float = field(default_factory=time.monotonic)
    started_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))
    counts: Counter = field(default_factory=Counter)
    strategies: Counter = field(default_factory=Counter)
    reasons: Counter = field(default_factory=Counter)
    fill_counts: Counter = field(default_factory=Counter)
    completed: bool = False
    stop_reason: str = ""
    stop_type: str = ""
    _saved: bool = False

    def note_edge_result(self, edge_result, raw_points: Sequence[Sequence[int | float]]) -> str:
        action, reason = classify_edge_result(edge_result, raw_points)
        self.counts["paths_processed"] += 1
        self.counts[action] += 1
        strategy = str(getattr(edge_result, "strategy", "") or "unknown")
        self.strategies[strategy] += 1
        self.reasons[_clean_reason(reason)] += 1
        return action

    def note_blocked(self, error: BaseException, *, reason: str | None = None) -> None:
        self.counts["paths_processed"] += 1
        self.counts["blocked"] += 1
        text = _clean_reason(reason or error)
        if text:
            self.reasons[text] += 1

    def note_fill(self, event: str, amount: int = 1) -> None:
        self.fill_counts[str(event)] += max(0, int(amount))

    def mark_completed(self) -> None:
        self.completed = True

    def mark_stopped(self, error: BaseException) -> None:
        self.completed = False
        self.counts["run_stopped"] = 1
        self.stop_type = type(error).__name__
        self.stop_reason = _clean_reason(error)

    def summary_counts(self) -> dict:
        return {
            "drawn": int(self.counts.get("drawn", 0)),
            "clipped": int(self.counts.get("clipped", 0)),
            "skipped": int(self.counts.get("skipped", 0)),
            "edge_follow": int(self.counts.get("edge-follow", 0)),
            "blocked": int(self.counts.get("blocked", 0)),
            "stopped": int(self.counts.get("run_stopped", 0)),
            "processed": int(self.counts.get("paths_processed", 0)),
        }

    def as_dict(self) -> dict:
        elapsed = max(0.0, time.monotonic() - self.started_monotonic)
        return {
            "schema": REPORT_SCHEMA,
            "app_version": APP_VERSION,
            "mode": "dry-run" if self.dry_run else "drawing",
            "profile": str(self.profile_name or ""),
            "edge_behavior": str(self.edge_behavior or ""),
            "started_utc": self.started_utc,
            "finished_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "elapsed_seconds": round(elapsed, 3),
            "completed": bool(self.completed),
            "planned_paths": int(self.planned_paths or 0),
            "counts": self.summary_counts(),
            "strategies": {key: int(value) for key, value in sorted(self.strategies.items())},
            "fills": {key: int(value) for key, value in sorted(self.fill_counts.items())},
            "stop": {
                "type": self.stop_type,
                "reason": self.stop_reason,
            },
            "reasons": [
                {"reason": key, "count": int(value)}
                for key, value in self.reasons.most_common(30)
            ],
            "privacy": "Local safety counters only; no source image pixels, screenshots, OCR, AI/ML or telemetry are stored.",
        }

    @staticmethod
    def to_text(payload: dict) -> str:
        c = payload.get("counts") or {}
        fills = payload.get("fills") or {}
        lines = [
            f"Image Draw Bot Runtime Safety Report - {payload.get('app_version', '')}",
            f"Mode: {payload.get('mode', '')}",
            f"Profile: {payload.get('profile', '')}",
            f"Edge behavior: {payload.get('edge_behavior', '')}",
            f"Completed: {'yes' if payload.get('completed') else 'no'}",
            f"Elapsed: {float(payload.get('elapsed_seconds', 0) or 0):.3f} s",
            f"Planned paths: {int(payload.get('planned_paths', 0) or 0):,}",
            "",
            "Runtime path counts:",
            f"  Drawn unchanged: {int(c.get('drawn', 0)):,}",
            f"  Clipped: {int(c.get('clipped', 0)):,}",
            f"  Skipped: {int(c.get('skipped', 0)):,}",
            f"  Edge-followed: {int(c.get('edge_follow', 0)):,}",
            f"  Blocked by safety: {int(c.get('blocked', 0)):,}",
            f"  Run stopped: {int(c.get('stopped', 0)):,}",
            f"  Total processed: {int(c.get('processed', 0)):,}",
        ]
        if fills:
            lines += ["", "Fill events:"]
            for key, value in sorted(fills.items()):
                lines.append(f"  {key}: {int(value):,}")
        strategies = payload.get("strategies") or {}
        if strategies:
            lines += ["", "Edge strategies:"]
            for key, value in sorted(strategies.items()):
                lines.append(f"  {key}: {int(value):,}")
        stop = payload.get("stop") or {}
        if stop.get("reason"):
            lines += ["", f"Stop: {stop.get('type', '')}: {stop.get('reason', '')}"]
        reasons = payload.get("reasons") or []
        if reasons:
            lines += ["", "Reasons:"]
            for item in reasons:
                lines.append(f"  {int(item.get('count', 0)):,}x - {item.get('reason', '')}")
        lines += ["", str(payload.get("privacy") or "")]
        return "\n".join(lines).rstrip() + "\n"

    def save(self, directory: Path | None = None) -> dict:
        payload = self.as_dict()
        if self._saved:
            return payload
        target_dir = Path(directory) if directory is not None else REPORT_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        base = f"ImageDrawBot-Safety-{_stamp()}-{'dry-run' if self.dry_run else 'drawing'}"
        json_path = target_dir / f"{base}.json"
        text_path = target_dir / f"{base}.txt"
        atomic_write_text(json_path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        atomic_write_text(text_path, self.to_text(payload))
        self._saved = True
        payload["json_path"] = str(json_path)
        payload["text_path"] = str(text_path)
        return payload


def safe_save(session: RuntimeSafetySession, directory: Path | None = None) -> dict:
    """Best-effort report save that can never mask the original draw result."""
    try:
        return session.save(directory)
    except Exception as error:
        payload = session.as_dict()
        payload["save_error"] = _clean_reason(error)
        return payload


def latest_report(directory: Path | None = None) -> dict | None:
    """Load the newest runtime safety JSON report. Local read-only helper."""
    target_dir = Path(directory) if directory is not None else REPORT_DIR
    try:
        files = sorted(target_dir.glob("ImageDrawBot-Safety-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return None
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload["json_path"] = str(path)
                txt = path.with_suffix(".txt")
                if txt.is_file(): payload["text_path"] = str(txt)
                return payload
        except (OSError, ValueError, TypeError):
            continue
    return None


def compact_summary(payload: dict | None) -> str:
    if not isinstance(payload, dict):
        return "No runtime safety report yet. Run Fast Dry run or Start drawing."
    counts=payload.get("counts") or {}
    state="PASS" if payload.get("completed") else "STOPPED"
    return (f"{state} · {payload.get('mode','')} · Drawn {int(counts.get('drawn',0)):,} · "
            f"Clipped {int(counts.get('clipped',0)):,} · Skipped {int(counts.get('skipped',0)):,} · "
            f"Edge-follow {int(counts.get('edge_follow',0)):,} · Blocked {int(counts.get('blocked',0)):,}")
