from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
APP_VERSION = '1.0.130-rc2'
FILE_VERSION = '1.0.130'
OLD_APP_VERSION = '1.0.129-rc1'
OLD_FILE_VERSION = '1.0.129'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def replace_required(path, old, new):
    text = read(path)
    if old not in text:
        raise SystemExit(f'{path}: missing required anchor {old!r}')
    write(path, text.replace(old, new))


# Canonical version metadata.
write('Version.py', "APP_NAME = 'Draw Studio'\nAPP_VERSION = '1.0.130-rc2'\nFILE_VERSION = \"1.0.130\"\nBUILD_CHANNEL = 'rc'\n")
replace_required('version_info.txt', 'filevers=(1,0,129,0)', 'filevers=(1,0,130,0)')
replace_required('version_info.txt', 'prodvers=(1,0,129,0)', 'prodvers=(1,0,130,0)')
replace_required('version_info.txt', "StringStruct('FileVersion', '1.0.129')", "StringStruct('FileVersion', '1.0.130')")
replace_required('version_info.txt', "StringStruct('ProductVersion', '1.0.129')", "StringStruct('ProductVersion', '1.0.130')")
replace_required('installer/DrawStudio.iss', '#define MyAppVersion "1.0.129-rc1"', '#define MyAppVersion "1.0.130-rc2"')

# RC hardening: version-only release notes, source-tree one-shot hygiene and strict manifest metadata/hash checks.
rch = read('ReleaseCandidateHardening.py')
rch = rch.replace('"""Step 30 — Release Candidate Hardening for Draw Studio.', '"""Release Candidate Hardening for Draw Studio.')
rch = rch.replace('_assert_contains(workflow, f"RELEASE-NOTES-v{app_version}-Step30.md", "build-windows workflow", errors)', '_assert_contains(workflow, f"RELEASE-NOTES-v{app_version}.md", "build-windows workflow", errors)')
rch = rch.replace('Version.py: Step 30 release candidate must use BUILD_CHANNEL', 'Version.py: release candidate must use BUILD_CHANNEL')
rch = rch.replace('Version.py: Step 30 APP_VERSION is not an rcN version', 'Version.py: APP_VERSION is not an rcN version')
needle = 'def collect_source_gate_errors(root: Path, *, app_version: str, file_version: str,\n'
if needle not in rch:
    raise SystemExit('ReleaseCandidateHardening.py: source gate anchor missing')
helper = '''def find_one_shot_source_files(root: Path) -> list[str]:\n    """Return temporary integration/patch files that must never ship from main."""\n    root = Path(root)\n    found: list[str] = []\n    for path in root.rglob("*"):\n        if not path.is_file():\n            continue\n        try:\n            rel = path.relative_to(root).as_posix()\n        except ValueError:\n            continue\n        lowered = rel.lower()\n        if lowered.startswith(".git/") or "/.git/" in lowered:\n            continue\n        base = path.name.lower()\n        if base.endswith("_once.py"):\n            found.append(rel)\n            continue\n        if lowered.startswith(".github/workflows/") and re.search(r"(?:^|[-_])once(?:[-_.]|$)", base) and base.endswith((".yml", ".yaml")):\n            found.append(rel)\n    return sorted(set(found))\n\n\n'''
rch = rch.replace(needle, helper + needle, 1)
anchor = '    workflow = _read(root / ".github" / "workflows" / "build-windows.yml")\n\n'
if anchor not in rch:
    raise SystemExit('ReleaseCandidateHardening.py: workflow anchor missing')
rch = rch.replace(anchor, anchor + '    one_shot_files = find_one_shot_source_files(root)\n    if one_shot_files:\n        errors.append("source tree: temporary one-shot files are present: " + ", ".join(one_shot_files[:12]))\n\n', 1)
rch = rch.replace('(\"version-metadata\", \"installer-metadata\", \"update-repository\", \"workflow-gates\",\n         \"lifecycle-soak\", \"profile-isolation-soak\"),', '(\"version-metadata\", \"installer-metadata\", \"update-repository\", \"workflow-gates\",\n         \"source-one-shot-hygiene\", \"lifecycle-soak\", \"profile-isolation-soak\"),')
old_manifest = '''def validate_manifest(path: Path, *, app_version: str, expected_files: Iterable[str]) -> dict:\n    try:\n        data = json.loads(_read(Path(path)))\n    except json.JSONDecodeError as error:\n        raise ReleaseGateError("Release manifest is not valid JSON") from error\n    if data.get("schema") != RELEASE_GATE_SCHEMA or data.get("version") != app_version:\n        raise ReleaseGateError("Release manifest metadata does not match this build")\n    artifacts = data.get("artifacts")\n    if not isinstance(artifacts, list):\n        raise ReleaseGateError("Release manifest artifacts are invalid")\n    names = {str(item.get("name")) for item in artifacts if isinstance(item, dict)}\n    missing = set(expected_files) - names\n    if missing:\n        raise ReleaseGateError("Release manifest is missing artifacts: " + ", ".join(sorted(missing)))\n    return data\n'''
new_manifest = '''def validate_manifest(path: Path, *, app_version: str, expected_files: Iterable[str],\n                      file_version: str | None = None, channel: str | None = None,\n                      base_dir: Path | None = None) -> dict:\n    path = Path(path)\n    try:\n        data = json.loads(_read(path))\n    except json.JSONDecodeError as error:\n        raise ReleaseGateError("Release manifest is not valid JSON") from error\n    if data.get("schema") != RELEASE_GATE_SCHEMA or data.get("version") != app_version:\n        raise ReleaseGateError("Release manifest metadata does not match this build")\n    if file_version is not None and data.get("file_version") != file_version:\n        raise ReleaseGateError("Release manifest file_version does not match Version.py")\n    if channel is not None and data.get("channel") != channel:\n        raise ReleaseGateError("Release manifest channel does not match Version.py")\n    if data.get("architecture") != "windows-x64":\n        raise ReleaseGateError("Release manifest architecture must be windows-x64")\n    artifacts = data.get("artifacts")\n    if not isinstance(artifacts, list) or not artifacts:\n        raise ReleaseGateError("Release manifest artifacts are invalid")\n    rows = {str(item.get("name")): item for item in artifacts if isinstance(item, dict) and item.get("name")}\n    missing = set(expected_files) - set(rows)\n    if missing:\n        raise ReleaseGateError("Release manifest is missing artifacts: " + ", ".join(sorted(missing)))\n    base = Path(base_dir) if base_dir is not None else path.parent\n    for name in expected_files:\n        item = rows[name]\n        target = base / name\n        if not target.is_file():\n            raise ReleaseGateError(f"Release manifest target is missing: {name}")\n        digest = str(item.get("sha256", "")).lower()\n        if not re.fullmatch(r"[0-9a-f]{64}", digest) or digest != _sha256(target):\n            raise ReleaseGateError(f"Release manifest SHA-256 mismatch for {name}")\n        try:\n            declared_bytes = int(item.get("bytes"))\n        except (TypeError, ValueError):\n            raise ReleaseGateError(f"Release manifest byte size is invalid for {name}")\n        if declared_bytes != target.stat().st_size:\n            raise ReleaseGateError(f"Release manifest byte size mismatch for {name}")\n    return data\n'''
if old_manifest not in rch:
    raise SystemExit('ReleaseCandidateHardening.py: manifest block anchor missing')
rch = rch.replace(old_manifest, new_manifest)
rch = rch.replace('    from Version import APP_VERSION\n    app_version = APP_VERSION if app_version is None else str(app_version)', '    from Version import APP_VERSION, FILE_VERSION, BUILD_CHANNEL\n    app_version = APP_VERSION if app_version is None else str(app_version)')
rch = rch.replace('result["manifest"] = validate_manifest(manifest_path, app_version=app_version, expected_files=expected)', 'result["manifest"] = validate_manifest(manifest_path, app_version=app_version, expected_files=expected,\n                                           file_version=FILE_VERSION, channel=BUILD_CHANNEL, base_dir=release)')
rch = rch.replace('argparse.ArgumentParser(description="Draw Studio Step 30 release gates")', 'argparse.ArgumentParser(description="Draw Studio release-candidate gates")')
write('ReleaseCandidateHardening.py', rch)

# Release builder emits complete canonical metadata.
br = read('build_release.py')
br = br.replace('from Version import APP_VERSION, BUILD_CHANNEL', 'from Version import APP_VERSION, FILE_VERSION, BUILD_CHANNEL')
br = br.replace('"version":APP_VERSION,\n        "channel":BUILD_CHANNEL,', '"version":APP_VERSION,\n        "file_version":FILE_VERSION,\n        "channel":BUILD_CHANNEL,')
br = br.replace("print('Step 30 source gate: PASS',report.as_dict())", "print('RC source gate: PASS', report.as_dict())")
br = br.replace('print("Step 30 Windows artifact gate: PASS")', 'print("RC Windows artifact gate: PASS")')
write('build_release.py', br)

# Current-version assertions across regression tests.
for path in ROOT.glob('test_*.py'):
    text = path.read_text(encoding='utf-8')
    if OLD_APP_VERSION not in text:
        continue
    text = text.replace(OLD_APP_VERSION, APP_VERSION)
    text = text.replace(OLD_FILE_VERSION, FILE_VERSION)
    text = text.replace('RELEASE-NOTES-v1.0.130-rc2-Step30.md', 'RELEASE-NOTES-v1.0.130-rc2.md')
    path.write_text(text, encoding='utf-8')

# Extend the RC hardening regression itself with hygiene/manifest coverage.
test_path = ROOT / 'test_step30_release_candidate_hardening_v10129rc1.py'
test = test_path.read_text(encoding='utf-8')
test = test.replace('    EXPECTED_REPOSITORY, ReleaseGateError, collect_source_gate_errors,\n', '    EXPECTED_REPOSITORY, ReleaseGateError, collect_source_gate_errors, find_one_shot_source_files,\n')
test = test.replace('    verify_checksum_file,\n)', '    verify_checksum_file, validate_manifest,\n)')
insert = '''\n    def test_source_hygiene_detects_one_shot_files(self):\n        with tempfile.TemporaryDirectory() as tmp:\n            root = Path(tmp)\n            (root/'step99_patch_once.py').write_text('x=1\\n', encoding='utf-8')\n            (root/'.github/workflows').mkdir(parents=True)\n            (root/'.github/workflows/release-once.yml').write_text('name: temp\\n', encoding='utf-8')\n            found = find_one_shot_source_files(root)\n            self.assertIn('step99_patch_once.py', found)\n            self.assertIn('.github/workflows/release-once.yml', found)\n\n    def test_manifest_rejects_stale_hash_and_metadata(self):\n        import hashlib\n        with tempfile.TemporaryDirectory() as tmp:\n            root = Path(tmp)\n            artifact = root/'DrawStudio-1.0.130-rc2-Windows-x64.zip'\n            artifact.write_bytes(b'payload')\n            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()\n            manifest = root/'manifest.json'\n            payload = {\n                'schema': 1, 'app': 'Draw Studio', 'version': '1.0.130-rc2',\n                'file_version': '1.0.130', 'channel': 'rc', 'architecture': 'windows-x64',\n                'artifacts': [{'name': artifact.name, 'type': 'windows-zip', 'sha256': digest, 'bytes': artifact.stat().st_size}],\n            }\n            manifest.write_text(json.dumps(payload), encoding='utf-8')\n            validate_manifest(manifest, app_version='1.0.130-rc2', expected_files=[artifact.name],\n                              file_version='1.0.130', channel='rc', base_dir=root)\n            payload['channel'] = 'beta'\n            manifest.write_text(json.dumps(payload), encoding='utf-8')\n            with self.assertRaises(ReleaseGateError):\n                validate_manifest(manifest, app_version='1.0.130-rc2', expected_files=[artifact.name],\n                                  file_version='1.0.130', channel='rc', base_dir=root)\n\n'''
marker = "    def test_windows_zip_rejects_test_and_runtime_leaks(self):\n"
if insert.strip() not in test:
    if marker not in test:
        raise SystemExit('RC test insertion anchor missing')
    test = test.replace(marker, insert + marker, 1)
test = test.replace('def test_release_version_is_rc1(self):', 'def test_release_version_is_rc2(self):')
test_path.write_text(test, encoding='utf-8')

# Professional version-based README current-release section.
readme = read('README.md')
readme = readme.replace('Current release candidate: **v1.0.129-rc1**', 'Current release candidate: **v1.0.130-rc2**')
readme = readme.replace('`DrawStudio-1.0.129-rc1-Windows-x64.zip`', '`DrawStudio-1.0.130-rc2-Windows-x64.zip`', 2)
readme = readme.replace('`DrawStudio-1.0.129-rc1-Windows-x64-Setup.exe`', '`DrawStudio-1.0.130-rc2-Windows-x64-Setup.exe`', 2)
readme = readme.replace('**v1.0.129-rc1 — Release Candidate Hardening**\n\nCurrent Windows release artifact names:', '**v1.0.130-rc2 — Release Candidate Hardening II**\n\nCurrent Windows release artifact names:', 1)
rc2_section = '''### v1.0.130-rc2 — Release Candidate Hardening II\n\n- Removes leftover one-shot integration/patch scripts and workflows from the release branch\n- Adds a permanent source-tree hygiene gate that rejects future `*_once.py` and one-shot workflow leakage\n- Uses version-only release-note naming for current publishing metadata\n- Strengthens manifest validation for app version, file version, channel, architecture, SHA-256 and byte size\n- Keeps the RC feature freeze: no renderer or input-safety behavior is loosened\n- Retains the verified Windows silent install → installed EXE self-test → silent uninstall gate\n- Requires full regression discovery and the 5,000-cycle lifecycle soak before Windows artifacts are accepted\n\n'''
old_heading = '### v1.0.129-rc1 — Release Candidate Hardening\n\n'
if rc2_section not in readme:
    if old_heading not in readme:
        raise SystemExit('README RC1 section anchor missing')
    readme = readme.replace(old_heading, rc2_section + old_heading, 1)
write('README.md', readme)

release_notes = '''# Draw Studio v1.0.130-rc2 — Release Candidate Hardening II\n\nThis second release candidate is a release-engineering and stability pass on top of the verified v1.0.129-rc1 renderer/input feature set. No new drawing engine is introduced.\n\n## RC2 hardening\n\n- Clean release branch: removes leftover one-shot integration and patch scripts/workflows.\n- Permanent source-tree hygiene gate blocks `*_once.py` and one-shot workflow files from future release builds.\n- Release publishing uses version-only release-note naming.\n- Manifest validation now verifies app version, file version, channel, Windows x64 architecture, SHA-256 and exact artifact byte size.\n- PE/Inno/Version.py consistency gates remain mandatory.\n- Update Center remains pinned to the official `Vxiey/Draw-Studio` repository and RC channel policy.\n- Hybrid Renderer 3.0, Pixel Accurate, CanvasGuard and profile isolation behavior remain feature-frozen for release validation.\n\n## Required release gates\n\nA v1.0.130-rc2 Windows build is accepted only after the complete regression suite, DrawBot self-test, source hygiene checks, 5,000-cycle lifecycle soak, profile-isolation soak, packaged ZIP/manifest/checksum validation and silent installer → installed EXE self-test → silent uninstall all pass.\n\n## Artifacts\n\n- `DrawStudio-1.0.130-rc2-Windows-x64.zip`\n- `DrawStudio-1.0.130-rc2-Windows-x64-Setup.exe`\n- `DrawStudio-1.0.130-rc2-SHA256.txt`\n- `DrawStudio-1.0.130-rc2-manifest.json`\n\nThe Windows binaries remain unsigned until an Authenticode certificate is configured.\n'''
write('RELEASE-NOTES-v1.0.130-rc2.md', release_notes)

history_line = 'v1.0.130-rc2 Release Candidate Hardening II removes leftover one-shot integration files, adds permanent source-tree hygiene enforcement, adopts version-only current release-note naming, and strengthens release-manifest version/channel/hash/size validation while keeping the RC feature freeze.\n\n'
for path in ['VERSION-HISTORY.md', 'docs/VERSION-HISTORY.md']:
    text = read(path)
    if 'v1.0.130-rc2 Release Candidate Hardening II' not in text:
        text = history_line + text
    write(path, text)

for path in ['docs/README.md', 'docs/history/README.md', 'README-INDEX.md']:
    text = read(path)
    text = text.replace('v1.0.129-rc1', 'v1.0.130-rc2')
    text = text.replace('RELEASE-NOTES-v1.0.129-rc1-Step30.md', 'RELEASE-NOTES-v1.0.130-rc2.md')
    write(path, text)

print('RC2 integration patch applied successfully')
