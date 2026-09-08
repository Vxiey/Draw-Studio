from pathlib import Path


def replace_once(path, old, new):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise RuntimeError(f'Patch anchor missing in {path}: {old[:160]!r}')
    p.write_text(text.replace(old,new,1),encoding='utf-8')


def insert_before(path, marker, block):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if marker not in text:
        raise RuntimeError(f'Insert marker missing in {path}: {marker!r}')
    p.write_text(text.replace(marker,block+marker,1),encoding='utf-8')

# Centralize the list of browser profiles that have a verified automatic detector.
replace_once('BrowserAutoCalibration.py',
"from PaletteMaps import PRESETS, detect_color_swatches\n\nSUPPORTED_BROWSER_PROFILES = frozenset({\n    'gartic-phone', 'skribbl', 'skribbl-fast', 'sketchheads', 'sketchful'\n})\n",
"from PaletteMaps import PRESETS, detect_color_swatches\nfrom TargetCapabilities import auto_browser_profile_keys\n\nSUPPORTED_BROWSER_PROFILES = auto_browser_profile_keys()\n")

for filename, old in (
    ('SmartRecovery.py', "SUPPORTED_BROWSER_PROFILES = frozenset({\n    'gartic-phone','skribbl','skribbl-fast','sketchheads','sketchful'\n})\n"),
    ('StrokeDeliveryVerification.py', "SUPPORTED_BROWSER_PROFILES = frozenset({\n    'gartic-phone', 'skribbl', 'skribbl-fast', 'sketchheads', 'sketchful'\n})\n"),
):
    replace_once(filename, old,
        "from TargetCapabilities import auto_browser_profile_keys\n\nSUPPORTED_BROWSER_PROFILES = auto_browser_profile_keys()\n")

# Step 27.5 now asks the Step 28 capability registry instead of duplicating target knowledge.
old_setup="""def setup_mode(profile_key: str) -> str:
    key=str(profile_key or '').strip().lower()
    if key == PAINT_PROFILE:
        return 'paint'
    try:
        from BrowserAutoCalibration import SUPPORTED_BROWSER_PROFILES
        if key in SUPPORTED_BROWSER_PROFILES:
            return 'browser'
    except Exception:
        pass
    return 'manual'
"""
new_setup="""def setup_mode(profile_key: str) -> str:
    from TargetCapabilities import capability_for_key
    mode=capability_for_key(profile_key).setup_mode
    if mode=='paint-auto':return 'paint'
    if mode=='browser-auto':return 'browser'
    return 'manual'
"""
replace_once('OneClickSetupVerification.py',old_setup,new_setup)

# Browser UI != auto-browser UI. Manual Step 28 browser targets keep their normal
# tool/palette/canvas controls while automatic controls stay hidden.
old_scope="""def scope_visible(scope,key):
    from BrowserAutoCalibration import SUPPORTED_BROWSER_PROFILES
    return {'paint':key=='microsoft-paint','gartic':key=='gartic-phone',
            'browser':key in SUPPORTED_BROWSER_PROFILES,'nonpaint':key!='microsoft-paint'}[scope]
"""
new_scope="""def scope_visible(scope,key):
    from TargetCapabilities import is_browser_target, supports_one_click_setup, capability_for_key
    cap=capability_for_key(key)
    return {
        'paint':key=='microsoft-paint',
        'gartic':key=='gartic-phone',
        'browser':is_browser_target(key),
        'browser-auto':cap.setup_mode=='browser-auto',
        'browser-manual':is_browser_target(key) and cap.setup_mode=='manual',
        'oneclick':supports_one_click_setup(key),
        'nonpaint':key!='microsoft-paint',
    }[scope]
"""
replace_once('ProfileIsolation.py',old_scope,new_scope)

# Setup wizard follows capability classification instead of a hard-coded name tuple.
replace_once('BeginnerSetupWizard.py',
"from typing import Any, Iterable, Mapping\n",
"from typing import Any, Iterable, Mapping\n\nfrom TargetCapabilities import capability_for_key\nfrom GameProfiles import PROFILES\n")
replace_once('BeginnerSetupWizard.py',
"    strict = profile_name == \"Microsoft Paint\"\n    browser = profile_name in (\"Gartic Phone\", \"Skribbl.io\", \"Skribbl.io Fast\", \"SketchHeads\", \"Sketchful.io\", \"Drawize\", \"Gartic.io\")\n",
"    strict = profile_name == \"Microsoft Paint\"\n    profile_key=str(PROFILES.get(profile_name,('generic',))[0])\n    capability=capability_for_key(profile_key)\n    browser=capability.kind.startswith('browser-')\n")

# Hide automatic browser controls for manually calibrated browser targets.
replace_once('StudioUI.py',
"        (one_click,'browser'),(a.browser_one_click_label,'browser'),\n        (a.browser_auto_button,'browser'),(a.browser_auto_label,'browser'),\n",
"        (a.one_click_setup_button,'oneclick'),(a.one_click_setup_label,'oneclick'),\n        (one_click,'browser-auto'),(a.browser_one_click_label,'browser-auto'),\n        (a.browser_auto_button,'browser-auto'),(a.browser_auto_label,'browser-auto'),\n")

# Manual tool semantics for the two new targets. Coordinates are never hard-coded.
replace_once('AppTools.py',
"    \"gartic-io\": {\"brush\": True, \"fill\": True, \"eraser\": True, \"clear\": True, \"note\": \"Tool positions are profile-specific and must be calibrated.\"},\n}",
"    \"gartic-io\": {\"brush\": True, \"fill\": True, \"eraser\": True, \"clear\": True, \"note\": \"Tool positions are profile-specific and must be calibrated.\"},\n    \"kleki\": {\"brush\": True, \"fill\": True, \"eraser\": True, \"clear\": False, \"note\": \"Kleki controls are manually calibrated and anchored to this profile; no layout coordinates are assumed.\"},\n    \"magma\": {\"brush\": True, \"fill\": True, \"eraser\": True, \"clear\": False, \"note\": \"Magma controls are manually calibrated per canvas/profile; collaborative UI changes require recalibration.\"},\n}")

# New first-class profiles.
replace_once('GameProfiles.py',
" 'Gartic.io':('gartic-io','#1768a2','Gartic.io profile. Keep the browser layout fixed, capture the palette and select only the drawable canvas.')}\n",
" 'Gartic.io':('gartic-io','#1768a2','Gartic.io profile. Keep the browser layout fixed, capture the palette and select only the drawable canvas.'),\n 'Kleki':('kleki','#5b6fa8','Kleki browser painting profile. Calibrate the visible brush/fill/colors and select only the canvas; no automatic layout coordinates are assumed.'),\n 'Magma':('magma','#b7492f','Magma collaborative drawing profile. Calibrate the current canvas/tools/colors per session layout and keep the browser geometry stable.')}\n")

ui_entries=""" 'Kleki': dict(icon='🖌️', badge='Browser painting app', prepare_title='Prepare Kleki',
     prepare_subtitle='Use manual tool/color calibration, then select only the drawable canvas. One-click layout detection is intentionally disabled until verified.',
     tool_button='🧰  Calibrate Kleki tools', palette_button='🎨  Read Kleki colors',
     area_button='▣  Select Kleki canvas', tip='Dedicated isolated profile. Browser layout, tool anchors, palette and timing data never leak to other targets.'),
 'Magma': dict(icon='🌋', badge='Collaborative browser app', prepare_title='Prepare Magma',
     prepare_subtitle='Open the intended collaborative canvas, calibrate visible tools/colors and select only the drawable canvas.',
     tool_button='🧰  Calibrate Magma tools', palette_button='🎨  Read Magma colors',
     area_button='▣  Select Magma canvas', tip='Dedicated isolated profile. Recalibrate when collaborative UI panels, zoom or canvas layout move.'),
"""
insert_before('GameProfiles.py',"}\n\n# Applied before reading a profile's saved settings.",ui_entries)

default_entries=""" 'Kleki': dict(mode='Shape paths', shape_model='Better shapes v2', progressive_rendering='On',
     quality='High detail', speed='Balanced', stroke_optimizer='Smart merge', adaptive_detail='Preserve detail', visual_verification='Auto', precision='High', draw_quality='High likeness', planning_resolution='High', resource_scheduler='Auto',
     background_fill='Conservative', background_simplification='Conservative', color_grouping='Smart',
     color_rendering='Perceptual match', color_fidelity='Faithful', color_layers='Off', custom_color_workflow='Adaptive exact (recommended)', time_budget_mode='Manual', max_stroke_cap='10000'),
 'Magma': dict(mode='Shape paths', shape_model='Better shapes v2', progressive_rendering='On',
     quality='High detail', speed='Balanced', stroke_optimizer='Smart merge', adaptive_detail='Preserve detail', visual_verification='Auto', precision='High', draw_quality='High likeness', planning_resolution='High', resource_scheduler='Auto',
     background_fill='Conservative', background_simplification='Conservative', color_grouping='Smart',
     color_rendering='Perceptual match', color_fidelity='Faithful', color_layers='Off', custom_color_workflow='Adaptive exact (recommended)', time_budget_mode='Manual', max_stroke_cap='10000'),
"""
insert_before('GameProfiles.py',"}\n\n\ndef profile_ui(name):",default_entries)

policy_entries="""    \"Kleki\": {
        \"name\": \"Kleki quality\",
        \"goal\": \"High-quality browser painting with explicit user-calibrated tools/colors and no unverified automatic coordinates.\",
        \"overrides\": {
            \"mode\": \"Shape paths\", \"shape_model\": \"Better shapes v2\", \"shape_order\": \"Fill first\",
            \"progressive_rendering\": \"On\", \"quality\": \"High detail\", \"speed\": \"Balanced\", \"precision\": \"High\",
            \"draw_quality\": \"High likeness\", \"planning_resolution\": \"High\", \"background_fill\": \"Conservative\",
            \"background_simplification\": \"Conservative\", \"color_grouping\": \"Smart\", \"color_workflow\": \"Finish color first\",
            \"stroke_optimizer\": \"Smart merge\", \"adaptive_detail\": \"Preserve detail\", \"visual_verification\": \"Off\",
            \"color_rendering\": \"Perceptual match\", \"color_fidelity\": \"Faithful\", \"color_layers\": \"Off\",
            \"custom_color_workflow\": \"Adaptive exact (recommended)\", \"exact_color_limit\": \"Auto\",
            \"time_budget_mode\": \"Manual\", \"target_stroke_count\": \"Auto\", \"max_stroke_cap\": \"10000\",
            \"planning_watchdog\": \"On\", \"resource_scheduler\": \"Auto\", \"edge_behavior\": \"Adaptive Clip\",
        },
    },
    \"Magma\": {
        \"name\": \"Magma collaborative quality\",
        \"goal\": \"Stable progressive rendering on a collaborative browser canvas with isolated manual calibration.\",
        \"overrides\": {
            \"mode\": \"Shape paths\", \"shape_model\": \"Better shapes v2\", \"shape_order\": \"Fill first\",
            \"progressive_rendering\": \"On\", \"quality\": \"High detail\", \"speed\": \"Balanced\", \"precision\": \"High\",
            \"draw_quality\": \"High likeness\", \"planning_resolution\": \"High\", \"background_fill\": \"Conservative\",
            \"background_simplification\": \"Conservative\", \"color_grouping\": \"Smart\", \"color_workflow\": \"Finish color first\",
            \"stroke_optimizer\": \"Smart merge\", \"adaptive_detail\": \"Preserve detail\", \"visual_verification\": \"Off\",
            \"color_rendering\": \"Perceptual match\", \"color_fidelity\": \"Faithful\", \"color_layers\": \"Off\",
            \"custom_color_workflow\": \"Adaptive exact (recommended)\", \"exact_color_limit\": \"Auto\",
            \"time_budget_mode\": \"Manual\", \"target_stroke_count\": \"Auto\", \"max_stroke_cap\": \"10000\",
            \"planning_watchdog\": \"On\", \"resource_scheduler\": \"Auto\", \"edge_behavior\": \"Adaptive Clip\",
        },
    },
"""
insert_before('ProfileEngine.py','    "Other drawing app": {',policy_entries)

# Packaged builds keep the central registry even where modules are imported dynamically.
replace_once('build_exe.py',
"        '--hidden-import', 'OneClickSetupVerification',\n",
"        '--hidden-import', 'OneClickSetupVerification',\n        '--hidden-import', 'TargetCapabilities',\n")

replace_once('Version.py',"APP_VERSION = '1.0.126-beta'\nFILE_VERSION = \"1.0.126\"\n",
             "APP_VERSION = '1.0.127-beta'\nFILE_VERSION = \"1.0.127\"\n")

replace_once('ROADMAP-STEP22-PLUS.md',
"## Step 28 — More Drawing Targets\n\nAdd carefully isolated presets for more drawing apps or browser games. Every target must get separate storage, calibration state, layout fingerprints and timing cache.\n",
"## Completed — Step 28 — More Drawing Targets\n\nAdds a central target-capability registry and dedicated **Kleki** + **Magma** profiles. Verified automatic targets stay explicitly separated from manual browser targets, so Drawize/Gartic.io/Kleki/Magma never inherit unverified auto-detection. Every profile keeps a unique storage key for settings, calibration, layout fingerprints and timing data; manual targets use explicit tool/palette/canvas calibration with no hard-coded coordinates.\n")

print('Step 28 integration prepared.')
