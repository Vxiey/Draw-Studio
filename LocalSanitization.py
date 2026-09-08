"""Local-only privacy helpers used by diagnostics.

No telemetry or network reporting is implemented here. This module only removes
common local identifiers/secrets from text before a diagnostics ZIP is created.
"""
from __future__ import annotations
from pathlib import Path
import re


def sanitize_text(text: str) -> str:
    text = str(text)
    home = str(Path.home())
    if home:
        text = text.replace(home, "<USER_HOME>")
        text = text.replace(home.replace("\\", "/"), "<USER_HOME>")
    text = re.sub(r"(?i)C:\\Users\\[^\\\r\n]+", r"C:\\Users\\<user>", text)
    text = re.sub(r"(?i)C:/Users/[^/\r\n]+", r"C:/Users/<user>", text)
    text = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s]+", r"\1<redacted>", text)
    text = re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+", r"\1<redacted>", text)
    text = re.sub(r"(?i)(token\s*[:=]\s*)[^\s,;]+", r"\1<redacted>", text)
    return text


def safe_context(context: object) -> dict:
    """Bound primitive diagnostics context; never accepts paths/coordinates."""
    if not isinstance(context, dict):
        return {}
    allowed = {
        'profile','activity','quality','speed','precision','render_style','draw_quality','human_mode',
        'gpu_mode','gpu_vram','gpu_performance','background_fill','fill_engine',
        'background_simplification','color_grouping','color_workflow','stroke_optimizer','adaptive_detail',
        'visual_verification','color_rendering','color_layers','custom_color_workflow','tool_strategy',
        'cpu_workers','cpu_engine','ram_budget','resource_scheduler','drawing_mode','shape_model',
        'time_budget_mode','target_stroke_count','paint_single_color','paint_tool','brush_px',
        'time_limit_seconds','palette_ready','drawing_area_selected','target_lock_valid',
    }
    cleaned={}
    for key in allowed:
        if key not in context:
            continue
        value=context[key]
        if isinstance(value,bool) or type(value) in (int,float):
            cleaned[key]=value
        elif isinstance(value,str):
            cleaned[key]=sanitize_text(value)[:200]
    return cleaned
