from pathlib import Path


def replace_once(path, old, new):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected integration marker not found in {path}: {old[:80]!r}')
    p.write_text(text.replace(old,new,1),encoding='utf-8')

# Clarify machine-specific timing exclusion and strengthen imported target/calibration validation.
p=Path('ProfilePortability.py'); text=p.read_text(encoding='utf-8')
text=text.replace('"draw-time calibration",','"draw timing calibration",',1)
old='''    if not isinstance(key, str):\n        raise ProfilePortabilityError("Profile target key is missing.")\n    _validate_source_key(key)\n\n    canvas = deepcopy(data.get("canvas") or {})\n'''
new='''    if not isinstance(key, str):\n        raise ProfilePortabilityError("Profile target key is missing.")\n    _validate_source_key(key)\n    existing = PROFILES.get(name.strip())\n    if existing is not None and not str(existing[0]).startswith("custom-") and key != str(existing[0]):\n        raise ProfilePortabilityError("Built-in profile name does not match its Draw Studio target key.")\n\n    canvas = deepcopy(data.get("canvas") or {})\n'''
if old not in text: raise SystemExit('Profile identity validation marker missing')
text=text.replace(old,new,1)
old='''    palette = calibration.get("palette")\n    if palette is not None:\n        try:\n            from Colors import validate_calibration\n            validate_calibration(palette, profile_key=key)\n        except (ValueError, TypeError) as error:\n            raise ProfilePortabilityError(f"Palette calibration failed validation: {error}") from error\n\n    safety = data.get("safety") or {}\n'''
new='''    palette = calibration.get("palette")\n    if palette is not None:\n        try:\n            from Colors import validate_calibration\n            validate_calibration(palette, profile_key=key)\n        except (ValueError, TypeError) as error:\n            raise ProfilePortabilityError(f"Palette calibration failed validation: {error}") from error\n\n    tools = calibration.get("tools")\n    if tools is not None:\n        try:\n            if key == "microsoft-paint":\n                from PaintTools import validate_tool_calibration\n                validate_tool_calibration(tools)\n            else:\n                from AppTools import validate_calibration as validate_app_tools\n                validate_app_tools(tools, key)\n        except (ValueError, TypeError) as error:\n            raise ProfilePortabilityError(f"Tool calibration failed validation: {error}") from error\n\n    exact_colors = calibration.get("exact_colors")\n    if exact_colors is not None:\n        try:\n            from ExactColorTools import validate as validate_exact_colors\n            validate_exact_colors(exact_colors, key)\n        except (ValueError, TypeError) as error:\n            raise ProfilePortabilityError(f"Exact-color calibration failed validation: {error}") from error\n\n    safety = data.get("safety") or {}\n'''
if old not in text: raise SystemExit('Calibration validation marker missing')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')

# Step 27 controls live next to the target-profile selector.
replace_once('StudioUI.py',
'''from ProfileEngine import PROFILE_ENGINE_MODES, policy_summary\n''',
'''from ProfileEngine import PROFILE_ENGINE_MODES, policy_summary\nfrom ProfilePortability import export_profile_dialog, import_profile_dialog, reset_profile_dialog\n''')
replace_once('StudioUI.py',
'''    btn(step1, '➕  Custom app profile', a.add_profile, height=32).pack(fill='x', pady=(7, 5))\n    label(step1, var=a.profile_hint, muted=True, wraplength=270, size=9).pack(anchor='w')\n''',
'''    btn(step1, '➕  Custom app profile', a.add_profile, height=32).pack(fill='x', pady=(7, 5))\n    profile_io = frame(step1)\n    profile_io.pack(fill='x', pady=(0, 5))\n    export_btn = btn(profile_io, '⇧  Export', lambda: export_profile_dialog(a), height=31, width=125)\n    export_btn.pack(side='left', fill='x', expand=True, padx=(0, 4))\n    import_btn = btn(profile_io, '⇩  Import', lambda: import_profile_dialog(a), height=31, width=125)\n    import_btn.pack(side='left', fill='x', expand=True, padx=(4, 0))\n    reset_profile_btn = btn(step1, '↺  Reset profile to defaults', lambda: reset_profile_dialog(a), height=31)\n    reset_profile_btn.pack(fill='x', pady=(0, 5))\n    tooltip(export_btn, 'Step 27: export only this profile to a portable .drawprofile/JSON file. Hardware/timing state and input authorization are excluded.')\n    tooltip(import_btn, 'Step 27: validate and import a .drawprofile. Existing names can be replaced or imported as an isolated copy.')\n    tooltip(reset_profile_btn, 'Delete only this profile’s saved settings/calibration/cache files and restore Draw Studio defaults. Other profiles are untouched.')\n    label(step1, var=a.profile_hint, muted=True, wraplength=270, size=9).pack(anchor='w')\n''')

# Step 27 is the next beta version.
Path('Version.py').write_text("APP_NAME = 'Draw Studio'\nAPP_VERSION = '1.0.125-beta'\nFILE_VERSION = \"1.0.125\"\nBUILD_CHANNEL = 'beta'\n",encoding='utf-8')

# Mark Step 27 complete without renumbering later roadmap steps.
p=Path('ROADMAP-STEP22-PLUS.md'); text=p.read_text(encoding='utf-8')
text=text.replace('Step 22 is now implemented. Steps 23–26 are now implemented as well.','Step 22 is now implemented. Steps 23–27 are now implemented as well.',1)
text=text.replace('## Step 27 — Export / Import Profiles','## Completed — Step 27 — Export / Import Profiles',1)
text=text.replace('Export/import one profile at a time, including portable settings and calibration metadata, while refusing to import machine-specific hardware/timing state onto the wrong computer.','Export/import one profile at a time as `.drawprofile`/JSON with schema migration, pre-import validation, renderer/resource settings, canvas/calibration metadata, Replace/Import-as-copy conflict handling, strict profile isolation and reset-to-defaults. Machine-specific hardware/timing state and all native-input authorization remain excluded.',1)
p.write_text(text,encoding='utf-8')

# Add stronger regression cases.
p=Path('test_profile_portability_step27.py'); text=p.read_text(encoding='utf-8')
marker='''    def test_invalid_canvas_is_rejected(self):\n'''
insert='''    def test_builtin_name_cannot_claim_another_target_key(self):\n        package = build_package('Microsoft Paint', self.basic_settings(), {'palette': self.palette()})\n        package['profile']['key'] = 'gartic-phone'\n        package['calibration']['palette']['profile'] = 'gartic-phone'\n        with self.assertRaises(ProfilePortabilityError):\n            validate_package(package)\n\n    def test_invalid_tool_calibration_is_rejected(self):\n        with self.assertRaises(ProfilePortabilityError):\n            build_package('Microsoft Paint', self.basic_settings(), {\n                'palette': self.palette(), 'tools': {'version': 99, 'tools': {}}\n            })\n\n    def test_invalid_exact_color_calibration_is_rejected(self):\n        with self.assertRaises(ProfilePortabilityError):\n            build_package('Microsoft Paint', self.basic_settings(), {\n                'palette': self.palette(), 'exact_colors': {'version': 99, 'profile': 'microsoft-paint'}\n            })\n\n'''
if marker not in text: raise SystemExit('Test insertion marker missing')
text=text.replace(marker,insert+marker,1)
p.write_text(text,encoding='utf-8')

print('Step 27 source integration prepared.')
