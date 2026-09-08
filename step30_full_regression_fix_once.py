from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
APP_VERSION='1.0.129-rc1'
PACKAGE='Draw-Studio-1.0.129-rc1-Step30-Release-Candidate-Hardening.zip'


def read(name): return (ROOT/name).read_text(encoding='utf-8')
def write(name,text):
    path=ROOT/name; path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')

def replace_once(name,old,new):
    text=read(name)
    if new in text:return
    if old not in text:raise RuntimeError(f'{name}: patch anchor not found: {old[:100]!r}')
    write(name,text.replace(old,new,1))

# ---------------------------------------------------------------------------
# REAL RC FIX: Skribbl Fast promises to retain dark structural ink, but the
# adaptive palette selector could omit a tiny black contour/dot when its pixel
# weight was smaller than broad colour regions. Force that structural anchor
# into the bounded palette and remap perceptually to the final kept set.
# ---------------------------------------------------------------------------
replace_once(
    'SkribblFastRenderer.py',
    'from ColorFidelity import color_metrics, validate_color_fidelity\n',
    'from ColorFidelity import color_metrics, palette_match_cost, validate_color_fidelity\n',
)
old='''    keep,mapping,palette_quality=select_adaptive_palette(selector_groups,palette,max_colors,fidelity=color_fidelity)\n    if not keep:\n        keep=[darkest];mapping={i:darkest for i in active};palette_quality={}\n\n    result: list[list[Segment]] = [[] for _ in work]\n'''
new='''    keep,mapping,palette_quality=select_adaptive_palette(selector_groups,palette,max_colors,fidelity=color_fidelity)\n    if not keep:\n        keep=[darkest];mapping={i:darkest for i in active};palette_quality={}\n    elif darkest not in keep:\n        # Structural dark ink is a semantic geometry anchor for this fast path.\n        # Preserve it even when its pixel weight is tiny, while keeping the same\n        # max-colour budget. Drop the weakest non-dark retained swatch if needed.\n        keep=list(map(int,keep))\n        if len(keep) >= max_colors:\n            removable=[i for i in keep if i != darkest]\n            if removable:\n                drop=min(removable,key=lambda i:(weights[i],i))\n                keep.remove(drop)\n        keep.append(int(darkest))\n        keep=list(dict.fromkeys(keep))\n        mapping={}\n        for index in active:\n            if index in keep:\n                mapping[index]=index\n                continue\n            mapping[index]=min(\n                keep,\n                key=lambda target:(\n                    palette_match_cost(palette[index],palette[target],\n                                       color_rendering='Perceptual match',fidelity=color_fidelity),\n                    -weights[target],target),\n            )\n        mapping[darkest]=darkest\n        palette_quality=dict(palette_quality or {})\n        palette_quality['forced_dark_structure']=True\n\n    result: list[list[Segment]] = [[] for _ in work]\n'''
replace_once('SkribblFastRenderer.py',old,new)
replace_once(
    'SkribblFastRenderer.py',
    "        'region_detail_anchors_kept': tuple(palette_quality.get('region_detail_anchors_kept',())),\n",
    "        'region_detail_anchors_kept': tuple(palette_quality.get('region_detail_anchors_kept',())),\n        'dark_structure_forced': bool(palette_quality.get('forced_dark_structure',False)),\n",
)

# ---------------------------------------------------------------------------
# RELEASE PACKAGE: exclude VCS/env/build/history artifacts and one-shot helper
# files without treating their mere presence in a developer checkout as a dirty
# runtime release. Logs/dumps/diagnostics remain release-blocking.
# ---------------------------------------------------------------------------
replace_once(
    'ReleasePackage.py',
    'NON_FATAL_EXCLUDED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}\n',
    'NON_FATAL_EXCLUDED_DIR_NAMES = {".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".build-venv", ".venv", "venv", "build", "dist", "release"}\n',
)
old='''    # Generated release/source archives should never be re-bundled into another release.\n    if name.startswith(("Draw-Studio-", "DrawStudio-")) and suffix in {".zip", ".exe"}:\n        return True\n    return False\n'''
new='''    # Generated release/source archives should never be re-bundled into another release.\n    if name.startswith(("Draw-Studio-", "DrawStudio-")) and suffix in {".zip", ".exe"}:\n        return True\n    # One-shot integration/packaging helpers are repository maintenance state,\n    # never source-release contents.\n    if name.lower().endswith('_once.py'):\n        return True\n    if len(parts) >= 3 and parts[0] == '.github' and parts[1] == 'workflows' and 'once' in name.lower():\n        return True\n    return False\n\n\ndef is_nonfatal_excluded_path(relative_path: str | PurePosixPath) -> bool:\n    rel=PurePosixPath(relative_path)\n    parts=_parts(rel); name=parts[-1] if parts else ''\n    suffix=PurePosixPath(name).suffix.lower()\n    if any(part in NON_FATAL_EXCLUDED_DIR_NAMES for part in parts):\n        return True\n    if name.startswith(("Draw-Studio-", "DrawStudio-")) and suffix in {'.zip','.exe'}:\n        return True\n    if name.lower().endswith('_once.py'):\n        return True\n    if len(parts) >= 3 and parts[0] == '.github' and parts[1] == 'workflows' and 'once' in name.lower():\n        return True\n    return False\n'''
replace_once('ReleasePackage.py',old,new)
old='''        for filename in files:\n            rel = PurePosixPath(rel_current, filename).as_posix() if rel_current else filename\n            if is_forbidden_path(rel):\n                forbidden.append(rel)\n'''
new='''        for filename in files:\n            rel = PurePosixPath(rel_current, filename).as_posix() if rel_current else filename\n            if is_forbidden_path(rel):\n                if is_nonfatal_excluded_path(rel):\n                    continue\n                forbidden.append(rel)\n'''
replace_once('ReleasePackage.py',old,new)

# ---------------------------------------------------------------------------
# PERMANENT WINDOWS WORKFLOW: keep Step 21's local-only source hygiene gate and
# Step 30's stricter RC gate. Both are useful and deterministic.
# ---------------------------------------------------------------------------
workflow=read('.github/workflows/build-windows.yml')
anchor="      - name: Step 30 source release gate\n        shell: pwsh\n        run: python ReleaseCandidateHardening.py --source-gate --soak-cycles 5000\n"
addition="\n      - name: Source package hygiene\n        shell: pwsh\n        run: python ReleasePackage.py --check\n"
if 'name: Source package hygiene' not in workflow:
    if anchor not in workflow:raise RuntimeError('build-windows source gate anchor missing')
    workflow=workflow.replace(anchor,anchor+addition,1)
write('.github/workflows/build-windows.yml',workflow)

# ---------------------------------------------------------------------------
# STALE REGRESSION ASSERTIONS: update old tests to current implemented policy.
# Do not change production policy to satisfy historical expectations.
# ---------------------------------------------------------------------------
replace_once('test_gartic_phone_turbo_v1065.py',
             "        self.assertEqual(effective['time_budget_mode'],'60 sec')\n        self.assertEqual(effective['max_stroke_cap'],'1000')\n",
             "        self.assertEqual(effective['time_budget_mode'],'Gartic Phone Fast')\n        self.assertEqual(effective['max_stroke_cap'],'2500')\n")
replace_once('test_profiles.py',
             '        self.assertEqual(len(PROFILES),9)\n        self.assertEqual(len({v[0] for v in PROFILES.values()}),9)\n',
             "        self.assertEqual(len(PROFILES),11)\n        self.assertEqual(len({v[0] for v in PROFILES.values()}),11)\n        self.assertIn('Kleki',PROFILES);self.assertIn('Magma',PROFILES)\n")
replace_once('test_step12_auto_tuner_feedback_v10136.py',
             '                tuned=tune_options(flat_image(), options)\n',
             "                tuned=tune_options(flat_image(), options, source_kind_hint='photo / texture')\n")

# Workspace tests deliberately simulate the old beta channel. RC1 changes the
# global channel, so patch both APP_VERSION and BUILD_CHANNEL in those simulations.
ws=read('test_workspace_v1092.py')
ws=ws.replace("with patch('UpdateCenter.APP_VERSION','1.0.92-beta'):\n            r=check_for_updates", "with patch('UpdateCenter.APP_VERSION','1.0.92-beta'), patch('UpdateCenter.BUILD_CHANNEL','beta'):\n            r=check_for_updates")
ws=ws.replace('https://github.com/yesverynice12/Draw-Studio/releases/tag/','https://github.com/Vxiey/Draw-Studio/releases/tag/')
write('test_workspace_v1092.py',ws)

# Step 21 workflow test now asserts the stricter Step 30 artifacts instead of
# requiring obsolete source-zip names from the old publisher workflow.
t=read('test_step21_release_cleanup_v10144.py')
t=t.replace('self.assertIn("python ReleasePackage.py --check", workflow)\n        self.assertIn("Draw-Studio-*-Source.zip", workflow)\n        self.assertIn("DrawStudio-*-ReleaseManifest.json", workflow)',
            'self.assertIn("python ReleasePackage.py --check", workflow)\n        self.assertIn("ReleaseCandidateHardening.py --source-gate", workflow)\n        self.assertIn("DrawStudio-*-Windows-x64.zip", workflow)\n        self.assertIn("DrawStudio-*-manifest.json", workflow)')
write('test_step21_release_cleanup_v10144.py',t)

# ---------------------------------------------------------------------------
# RC README + histories: current version must exist before full discovery, not
# only after the package job.
# ---------------------------------------------------------------------------
readme=read('README.md')
readme=readme.replace('`Draw-Studio-1.0.128-beta-Step29-Hybrid-Renderer-3.zip`',f'`{PACKAGE}`')
pattern=re.compile(r"## Current beta\n\n\*\*v1\.0\.128-beta — Step 29: Hybrid Renderer 3\.0\*\*\n\nCurrent verified source package:\n\n- `Draw-Studio-1\.0\.128-beta-Step29-Hybrid-Renderer-3\.zip`\n- SHA-256 is published in `SOURCE-PACKAGE-SHA256\.txt`\n\n### Step 29 highlights\n",re.M)
replacement=f'''## Current release candidate\n\n**v1.0.129-rc1 — Step 30: Release Candidate Hardening**\n\nCurrent RC source package:\n\n- `{PACKAGE}`\n- SHA-256 is published in `SOURCE-PACKAGE-SHA256.txt` after packaging\n\n### Step 30 highlights\n\n- Numbered feature roadmap is frozen for RC validation\n- 5,000-cycle start/stop/disarm lifecycle soak gate\n- Repeated profile-storage isolation soak\n- Update Center fixed to `Vxiey/Draw-Studio` with RC-aware channel filtering\n- Version.py, PE metadata and Inno Setup version consistency gates\n- Windows ZIP/installer/SHA-256/manifest validation\n- Silent installer → installed EXE self-test → silent uninstall in Windows CI\n- Source/release packages reject logs, dumps, bytecode, tests and one-time patch files\n- Full regression discovery is a release gate\n- Hybrid Renderer 3.0 remains the current renderer; no new renderer feature is added by Step 30\n\n### Step 29 highlights\n'''
readme,n=pattern.subn(replacement,readme,count=1)
if n!=1 and '**v1.0.129-rc1 — Step 30: Release Candidate Hardening**' not in readme:
    raise RuntimeError('README Step29 current-beta block not found')
# Restore explicit local-only release hygiene references that remain useful.
if 'python ReleasePackage.py --check' not in readme:
    dev='''## Developer verification\n\n```powershell\npython -m unittest discover -v\npython DrawBot.py --self-test\n```\n'''
    newdev='''## Developer verification\n\nThe source-packaging tools are **local-only** and do not upload runtime data.\n\n```powershell\npython ReleasePackage.py --check\npython ReleaseCandidateHardening.py --source-gate --soak-cycles 5000\npython -m unittest discover -v\npython DrawBot.py --self-test\n```\n\nRelease architecture and roadmap references: `ROADMAP-STEP22-PLUS.md` and `STEP-22-UNIVERSAL-HARDWARE-AUTO-BENCHMARK.md`.\n'''
    if dev not in readme:raise RuntimeError('README developer verification block not found')
    readme=readme.replace(dev,newdev,1)
# Add a concise RC mode explanation to the drawing-mode section once.
if '### Hybrid Renderer 3.0' not in readme:
    anchor='''### Pixel Accurate\n\nUse this when preserving the original image is more important than drawing speed.\n'''
    hybrid='''### Hybrid Renderer 3.0\n\nUse Auto Hybrid when you want Draw Studio to choose a deterministic specialised renderer for Pixel Art, Icon / Logo, Line Art, Portrait, Shaded Object or Deadline Silhouette. The analysis is local Pillow/NumPy structure analysis — no AI, ML or OCR.\n\n'''
    if anchor in readme:readme=readme.replace(anchor,hybrid+anchor,1)
write('README.md',readme)

history_line=('v1.0.129-rc1 Step 30: Release Candidate Hardening freezes the numbered feature roadmap, adds executable source/artifact release gates, 5,000-cycle lifecycle and profile-isolation soak checks, fixes Update Center repository/channel handling, validates Windows ZIP/installer/checksums/manifests, and requires a silent install/self-test/uninstall round trip before RC publication.\n')
for name in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    text=read(name)
    if not text.startswith(history_line):text=history_line+text
    write(name,text)

# Release workflow assertions should target Step 30's stricter gate while still
# retaining the legacy local-only source hygiene command.
r=read('test_release_v100.py')
r=r.replace("self.assertIn('actions/upload-artifact@v4',text); self.assertIn('python ReleasePackage.py --check',text)",
            "self.assertIn('actions/upload-artifact@v4',text); self.assertIn('python ReleasePackage.py --check',text); self.assertIn('ReleaseCandidateHardening.py --source-gate',text)")
write('test_release_v100.py',r)

print('Step 30 full-regression patch prepared.')
