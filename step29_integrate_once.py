from pathlib import Path
import re


def read(path):
    return Path(path).read_text(encoding='utf-8')


def write(path, text):
    Path(path).write_text(text, encoding='utf-8', newline='\n')


def replace_once(path, old, new):
    text = read(path)
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{path}: expected one occurrence, found {count}: {old[:100]!r}')
    write(path, text.replace(old, new, 1))


def insert_after(path, needle, addition):
    text = read(path)
    if addition.strip() in text:
        return
    pos = text.find(needle)
    if pos < 0:
        raise RuntimeError(f'{path}: insertion anchor not found: {needle[:100]!r}')
    pos += len(needle)
    write(path, text[:pos] + addition + text[pos:])


def insert_before_line(path, contains, line):
    text = read(path)
    if line.strip() in text:
        return
    rows = text.splitlines(True)
    for i, raw in enumerate(rows):
        if contains in raw:
            rows.insert(i, line if line.endswith('\n') else line + '\n')
            write(path, ''.join(rows))
            return
    raise RuntimeError(f'{path}: line anchor not found: {contains!r}')


# ---------------------------------------------------------------------------
# DrawBot integration
# ---------------------------------------------------------------------------
insert_after(
    'DrawBot.py',
    "                                      validate_quick_sketch_style, validate_fill_preference)\n",
    "from HybridRenderer3 import (HYBRID_RENDER_STYLE, HYBRID_MODES, apply_hybrid_policy,\n"
    "                             is_hybrid_renderer, validate_hybrid_mode)\n",
)

replace_once(
    'DrawBot.py',
    "def make_plan(original, area, options, cancelled=lambda: False):\n"
    "    from PIL import Image, ImageEnhance, ImageDraw, ImageFilter, ImageOps\n"
    "    from AutoDrawing import resolve_drawing\n"
    "    options=resolve_drawing(original,options)\n",
    "def make_plan(original, area, options, cancelled=lambda: False):\n"
    "    from PIL import Image, ImageEnhance, ImageDraw, ImageFilter, ImageOps\n"
    "    from AutoDrawing import resolve_drawing\n"
    "    # Step 29: Hybrid Renderer 3.0 resolves specialised deterministic policy\n"
    "    # before the generic AutoDrawing selector. It only changes renderer/planner\n"
    "    # fields; CanvasGuard, calibration and input authorisation remain separate.\n"
    "    if is_hybrid_renderer(options):\n"
    "        options=apply_hybrid_policy(original,options,cancelled=cancelled)\n"
    "    options=resolve_drawing(original,options)\n",
)

replace_once(
    'DrawBot.py',
    "        self.quick_sketch_style = tk.StringVar(value='Balanced')\n"
    "        self.quick_sketch_fill_preference = tk.StringVar(value='Safe Fill First')\n"
    "        self.visual_verification = tk.StringVar(value='Auto')\n",
    "        self.quick_sketch_style = tk.StringVar(value='Balanced')\n"
    "        self.quick_sketch_fill_preference = tk.StringVar(value='Safe Fill First')\n"
    "        self.hybrid_mode = tk.StringVar(value='Auto Hybrid')\n"
    "        self.visual_verification = tk.StringVar(value='Auto')\n",
)

replace_once(
    'DrawBot.py',
    "self.quick_sketch_style.set('Balanced');self.quick_sketch_fill_preference.set('Safe Fill First');self.color_rendering.set('Perceptual match')",
    "self.quick_sketch_style.set('Balanced');self.quick_sketch_fill_preference.set('Safe Fill First');self.hybrid_mode.set('Auto Hybrid');self.color_rendering.set('Perceptual match')",
)

replace_once(
    'DrawBot.py',
    "            quick_sketch_fill_preference=data.get('quick_sketch_fill_preference','Safe Fill First')\n"
    "            if hasattr(self,'quick_sketch_fill_preference') and quick_sketch_fill_preference in QUICK_SKETCH_FILL_PREFERENCES:self.quick_sketch_fill_preference.set(quick_sketch_fill_preference)\n"
    "            visual_verification=data.get('visual_verification','Auto')\n",
    "            quick_sketch_fill_preference=data.get('quick_sketch_fill_preference','Safe Fill First')\n"
    "            if hasattr(self,'quick_sketch_fill_preference') and quick_sketch_fill_preference in QUICK_SKETCH_FILL_PREFERENCES:self.quick_sketch_fill_preference.set(quick_sketch_fill_preference)\n"
    "            hybrid_mode=data.get('hybrid_mode','Auto Hybrid')\n"
    "            if hasattr(self,'hybrid_mode') and hybrid_mode in HYBRID_MODES:self.hybrid_mode.set(hybrid_mode)\n"
    "            visual_verification=data.get('visual_verification','Auto')\n",
)

replace_once(
    'DrawBot.py',
    "'quick_sketch_fill_preference':getattr(getattr(self,'quick_sketch_fill_preference',None),'get',lambda:'Safe Fill First')(),'visual_verification':",
    "'quick_sketch_fill_preference':getattr(getattr(self,'quick_sketch_fill_preference',None),'get',lambda:'Safe Fill First')(),'hybrid_mode':getattr(getattr(self,'hybrid_mode',None),'get',lambda:'Auto Hybrid')(),'visual_verification':",
)

replace_once(
    'DrawBot.py',
    "quick_sketch_fill_preference=getattr(getattr(self,'quick_sketch_fill_preference',None),'get',lambda:'Safe Fill First')();visual_verification=",
    "quick_sketch_fill_preference=getattr(getattr(self,'quick_sketch_fill_preference',None),'get',lambda:'Safe Fill First')();hybrid_mode=getattr(getattr(self,'hybrid_mode',None),'get',lambda:'Auto Hybrid')();visual_verification=",
)

replace_once(
    'DrawBot.py',
    "'adaptive_detail':adaptive_detail,'quick_sketch_style':quick_sketch_style,'quick_sketch_fill_preference':quick_sketch_fill_preference,'visual_verification':visual_verification,",
    "'adaptive_detail':adaptive_detail,'quick_sketch_style':quick_sketch_style,'quick_sketch_fill_preference':quick_sketch_fill_preference,'hybrid_mode':hybrid_mode,'visual_verification':visual_verification,",
)

replace_once(
    'DrawBot.py',
    "adaptive_detail=_effective_policy['adaptive_detail'];quick_sketch_style=_effective_policy.get('quick_sketch_style',quick_sketch_style);quick_sketch_fill_preference=_effective_policy.get('quick_sketch_fill_preference',quick_sketch_fill_preference);visual_verification=",
    "adaptive_detail=_effective_policy['adaptive_detail'];quick_sketch_style=_effective_policy.get('quick_sketch_style',quick_sketch_style);quick_sketch_fill_preference=_effective_policy.get('quick_sketch_fill_preference',quick_sketch_fill_preference);hybrid_mode=_effective_policy.get('hybrid_mode',hybrid_mode);visual_verification=",
)

replace_once(
    'DrawBot.py',
    "            if hasattr(self,'render_style') and render_style in ('Auto','Portrait / shaded','Standard / pixel',QUICK_SKETCH_RENDER_STYLE):self.render_style.set(render_style)",
    "            if hasattr(self,'render_style') and render_style in ('Auto','Portrait / shaded','Standard / pixel',QUICK_SKETCH_RENDER_STYLE,HYBRID_RENDER_STYLE):self.render_style.set(render_style)",
)

replace_once(
    'DrawBot.py',
    "        if render_style not in ('Auto','Portrait / shaded','Standard / pixel',QUICK_SKETCH_RENDER_STYLE):\n"
    "            raise ValueError('Choose a valid rendering style.')\n"
    "        validate_quick_sketch_style(quick_sketch_style)\n"
    "        validate_fill_preference(quick_sketch_fill_preference)\n",
    "        if render_style not in ('Auto','Portrait / shaded','Standard / pixel',QUICK_SKETCH_RENDER_STYLE,HYBRID_RENDER_STYLE):\n"
    "            raise ValueError('Choose a valid rendering style.')\n"
    "        validate_quick_sketch_style(quick_sketch_style)\n"
    "        validate_fill_preference(quick_sketch_fill_preference)\n"
    "        validate_hybrid_mode(hybrid_mode)\n",
)

replace_once(
    'DrawBot.py',
    "'adaptive_detail':adaptive_detail,'detail_zoom':detail_zoom,'quick_sketch_style':quick_sketch_style,'quick_sketch_fill_preference':quick_sketch_fill_preference,'visual_verification':visual_verification,",
    "'adaptive_detail':adaptive_detail,'detail_zoom':detail_zoom,'quick_sketch_style':quick_sketch_style,'quick_sketch_fill_preference':quick_sketch_fill_preference,'hybrid_mode':hybrid_mode,'visual_verification':visual_verification,",
)

# Diagnostics/settings snapshot shown in local reports.
replace_once(
    'DrawBot.py',
    "'quick_sketch_fill_preference': safe_get(getattr(self,'quick_sketch_fill_preference',None),'Safe Fill First'),\n            'visual_verification':",
    "'quick_sketch_fill_preference': safe_get(getattr(self,'quick_sketch_fill_preference',None),'Safe Fill First'),\n            'hybrid_mode': safe_get(getattr(self,'hybrid_mode',None),'Auto Hybrid'),\n            'visual_verification':",
)

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
insert_after(
    'StudioUI.py',
    "from QuickSketchFillContour import QUICK_SKETCH_RENDER_STYLE, QUICK_SKETCH_STYLES, QUICK_SKETCH_FILL_PREFERENCES\n",
    "from HybridRenderer3 import HYBRID_RENDER_STYLE, HYBRID_MODES\n",
)
replace_once(
    'StudioUI.py',
    "['Auto', 'Portrait / shaded', 'Standard / pixel', QUICK_SKETCH_RENDER_STYLE]",
    "['Auto', 'Portrait / shaded', 'Standard / pixel', QUICK_SKETCH_RENDER_STYLE, HYBRID_RENDER_STYLE]",
)
insert_before_line(
    'StudioUI.py',
    "setting_row(quality_card, 'Quick Sketch style', a.quick_sketch_style",
    "    setting_row(quality_card, 'Hybrid mode', a.hybrid_mode, list(HYBRID_MODES), 'Step 29: Auto Hybrid or a specialised deterministic mode for Pixel Art, Icon / Logo, Line Art, Portrait, Shaded Object or Deadline Silhouette. No AI/OCR; safety and calibration are unchanged.')",
)

# ---------------------------------------------------------------------------
# Profile persistence / export
# ---------------------------------------------------------------------------
replace_once(
    'ProfileIsolation.py',
    "'target_stroke_custom', 'render_style', 'draw_quality'",
    "'target_stroke_custom', 'render_style', 'hybrid_mode', 'draw_quality'",
)
replace_once(
    'ProfilePortability.py',
    '    "detail_zoom", "quick_sketch_style", "quick_sketch_fill_preference",\n',
    '    "detail_zoom", "quick_sketch_style", "quick_sketch_fill_preference", "hybrid_mode",\n',
)

# ---------------------------------------------------------------------------
# Preview diagnostics
# ---------------------------------------------------------------------------
replace_once(
    'PreviewDiagnostics.py',
    "    quick_sketch = options.get('quick_sketch_meta') if isinstance(options, dict) else {}\n"
    "    quick_sketch = quick_sketch if isinstance(quick_sketch, dict) else {}\n",
    "    quick_sketch = options.get('quick_sketch_meta') if isinstance(options, dict) else {}\n"
    "    quick_sketch = quick_sketch if isinstance(quick_sketch, dict) else {}\n"
    "    hybrid = options.get('hybrid_renderer_meta') if isinstance(options, dict) else {}\n"
    "    hybrid = hybrid if isinstance(hybrid, dict) else {}\n",
)

# Add the compact Hybrid diagnostics block immediately before Quick Sketch.
replace_once(
    'PreviewDiagnostics.py',
    "        'quick_sketch':{k:quick_sketch.get(k) for k in (\n",
    "        'hybrid_renderer':{k:hybrid.get(k) for k in (\n"
    "            'enabled','engine','step','version','requested_mode','resolved_mode','base_renderer',\n"
    "            'passes','deadline_seconds','analysis','semantic_ai_used','ocr_used','native_input_changed','safety_policy')\n"
    "            if hybrid.get(k) is not None},\n"
    "        'quick_sketch':{k:quick_sketch.get(k) for k in (\n",
)

# Add one readable line to formatted diagnostics without disturbing existing
# Quick Sketch / stability formatting.
replace_once(
    'PreviewDiagnostics.py',
    "    if stability:\n",
    "    hybrid=diagnostics.get('hybrid_renderer') or {}\n"
    "    if hybrid.get('enabled'):\n"
    "        try:\n"
    "            mode=str(hybrid.get('resolved_mode') or '?')\n"
    "            passes=hybrid.get('passes') if isinstance(hybrid.get('passes'),list) else []\n"
    "            line='Hybrid 3.0: '+mode\n"
    "            if passes: line+=' · '+' → '.join(str(x) for x in passes[:4])\n"
    "            lines.append(line)\n"
    "        except Exception:\n"
    "            pass\n"
    "    if stability:\n",
)

# ---------------------------------------------------------------------------
# Frozen build + release metadata
# ---------------------------------------------------------------------------
replace_once(
    'build_exe.py',
    "        '--hidden-import', 'QuickSketchFillContour',\n",
    "        '--hidden-import', 'QuickSketchFillContour',\n        '--hidden-import', 'HybridRenderer3',\n",
)
replace_once(
    'build_exe.py',
    "'STEP-25-QUICK-SKETCH-FILL-CONTOUR.md', 'RELEASE-NOTES-Step24-Step25-Detail-Zoom-Quick-Sketch.md', 'COLOR-ENGINE-NAMED-COLOR-INTELLIGENCE.md'",
    "'STEP-25-QUICK-SKETCH-FILL-CONTOUR.md', 'STEP-29-HYBRID-RENDERER-3.md', 'RELEASE-NOTES-Step24-Step25-Detail-Zoom-Quick-Sketch.md', 'COLOR-ENGINE-NAMED-COLOR-INTELLIGENCE.md'",
)

write('Version.py', "APP_NAME = 'Draw Studio'\nAPP_VERSION = '1.0.128-beta'\nFILE_VERSION = \"1.0.128\"\nBUILD_CHANNEL = 'beta'\n")

version_info = read('version_info.txt')
version_info = re.sub(r'filevers=\(1,0,\d+,0\)', 'filevers=(1,0,128,0)', version_info)
version_info = re.sub(r'prodvers=\(1,0,\d+,0\)', 'prodvers=(1,0,128,0)', version_info)
version_info = re.sub(r"StringStruct\('FileVersion', '1\.0\.\d+'\)", "StringStruct('FileVersion', '1.0.128')", version_info)
version_info = re.sub(r"StringStruct\('ProductVersion', '1\.0\.\d+'\)", "StringStruct('ProductVersion', '1.0.128')", version_info)
write('version_info.txt', version_info)

replace_once(
    'ROADMAP-STEP22-PLUS.md',
    "## Step 29 — New Draw Modes / Hybrid Renderer 3.0\n\nAdd specialized deterministic modes for pixel art, icons/logos, line art, portraits, shaded objects and deadline-only silhouettes.\n",
    "## Completed — Step 29 — New Draw Modes / Hybrid Renderer 3.0\n\nAdds a deterministic Hybrid Renderer 3.0 orchestration layer with Auto Hybrid plus specialised Pixel Art, Icon / Logo, Line Art, Portrait, Shaded Object and Deadline Silhouette modes. It routes into the existing Pixel Accurate, Quick Sketch Fill + Contour, Shape Paths, PortraitPlanner, adaptive detail and deadline engines instead of duplicating native input. Auto Hybrid uses bounded Pillow/NumPy structure statistics only; it does not use AI, ML, OCR or face recognition. CanvasGuard, calibration, target locks, preflight and dry-run remain authoritative.\n",
)

# README index links the technical Step 29 document. Avoid duplicates if the
# index format changes later.
text = read('README-INDEX.md')
if 'STEP-29-HYBRID-RENDERER-3.md' not in text:
    anchor = '- `STEP-26-DETAIL-FIDELITY-PIXEL-ACCURATE.md`\n'
    if anchor in text:
        text = text.replace(anchor, anchor + '- `STEP-29-HYBRID-RENDERER-3.md` — specialised deterministic Hybrid Renderer 3.0 modes\n', 1)
    else:
        text += '\n- `STEP-29-HYBRID-RENDERER-3.md` — specialised deterministic Hybrid Renderer 3.0 modes\n'
    write('README-INDEX.md', text)

print('Step 29 integration prepared.')
