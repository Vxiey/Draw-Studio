from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
APP_VERSION='1.0.129-rc1'
FILE_VERSION='1.0.129'


def read(name):
    return (ROOT/name).read_text(encoding='utf-8')


def write(name,text):
    path=ROOT/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')


# Freeze RC metadata.
write('Version.py', "APP_NAME = 'Draw Studio'\nAPP_VERSION = '1.0.129-rc1'\nFILE_VERSION = \"1.0.129\"\nBUILD_CHANNEL = 'rc'\n")

vi=read('version_info.txt')
vi=re.sub(r'filevers=\(1,0,\d+,0\)', 'filevers=(1,0,129,0)', vi)
vi=re.sub(r'prodvers=\(1,0,\d+,0\)', 'prodvers=(1,0,129,0)', vi)
vi=re.sub(r"StringStruct\('FileVersion', '1\.0\.\d+'\)", "StringStruct('FileVersion', '1.0.129')", vi)
vi=re.sub(r"StringStruct\('ProductVersion', '1\.0\.\d+'\)", "StringStruct('ProductVersion', '1.0.129')", vi)
write('version_info.txt',vi)

# Inno Setup metadata must match the RC even when ISCC is invoked manually.
iss=read('installer/DrawStudio.iss')
iss=re.sub(r'#define MyAppVersion "[^"]+"', '#define MyAppVersion "1.0.129-rc1"', iss, count=1)
if 'VersionInfoVersion=' not in iss:
    iss=iss.replace('AppVersion={#MyAppVersion}\n','AppVersion={#MyAppVersion}\nVersionInfoVersion=1.0.129.0\n',1)
if 'RestartIfNeededByRun=' not in iss:
    iss=iss.replace('SetupLogging=yes\n','SetupLogging=yes\nRestartIfNeededByRun=no\nCloseApplications=yes\nRestartApplications=no\n',1)
write('installer/DrawStudio.iss',iss)

# Fix the historical repository reference and tighten release-channel semantics.
up=read('UpdateCenter.py')
up=up.replace('GITHUB_REPOSITORY = "yesverynice12/Draw-Studio"','GITHUB_REPOSITORY = "Vxiey/Draw-Studio"')
old='''def _release_allowed(release: dict, channel: str) -> bool:\n    if not isinstance(release, dict) or bool(release.get("draft")):\n        return False\n    tag = normalize_tag(release.get("tag_name"))\n    if parse_version(tag) is None:\n        return False\n    # Beta builds may see both beta/prerelease and stable releases. A stable\n    # channel intentionally ignores GitHub prereleases.\n    if str(channel).lower() == "stable" and bool(release.get("prerelease")):\n        return False\n    return True\n'''
new='''def _release_allowed(release: dict, channel: str) -> bool:\n    if not isinstance(release, dict) or bool(release.get("draft")):\n        return False\n    tag = normalize_tag(release.get("tag_name"))\n    parsed = parse_version(tag)\n    if parsed is None:\n        return False\n    channel = str(channel or "beta").lower()\n    # Channel floors prevent an RC build from being pointed back toward beta\n    # releases. Higher patch versions still compare normally inside the allowed\n    # channel set. Stable accepts published non-prereleases only.\n    if channel == "stable":\n        return not bool(release.get("prerelease")) and parsed.stage_rank >= _STAGE_RANK["stable"]\n    if channel == "rc":\n        return parsed.stage_rank >= _STAGE_RANK["rc"]\n    if channel == "beta":\n        return parsed.stage_rank >= _STAGE_RANK["beta"]\n    return True\n'''
if old not in up and new not in up:
    raise RuntimeError('UpdateCenter release-channel block not found')
up=up.replace(old,new,1)
write('UpdateCenter.py',up)

# Release builder: source gate before expensive build work, clean stale artifacts,
# emit a machine-readable manifest, then validate the final Windows package.
build='''"""Create and validate a release-grade Windows package for Draw Studio."""\nfrom __future__ import annotations\n\nimport argparse\nimport hashlib\nimport json\nimport os\nfrom pathlib import Path\nimport shutil\nimport subprocess\nimport sys\nimport zipfile\n\nfrom Version import APP_VERSION, BUILD_CHANNEL\nfrom ReleaseCandidateHardening import run_source_release_gate, validate_windows_release\n\nBASE = Path(__file__).resolve().parent\nDIST = BASE / "dist" / "DrawStudio"\nRELEASE = BASE / "release"\n\n\ndef run(command: list[str], *, cwd: Path = BASE) -> None:\n    print("+", " ".join(map(str, command)))\n    subprocess.run(command, cwd=cwd, check=True)\n\n\ndef sha256(path: Path) -> str:\n    digest = hashlib.sha256()\n    with path.open("rb") as stream:\n        for chunk in iter(lambda: stream.read(1024 * 1024), b""):\n            digest.update(chunk)\n    return digest.hexdigest()\n\n\ndef zip_onedir(destination: Path) -> None:\n    if destination.exists():\n        destination.unlink()\n    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:\n        for path in sorted(DIST.rglob("*")):\n            if path.is_file():\n                relative = Path("DrawStudio") / path.relative_to(DIST)\n                archive.write(path, relative.as_posix())\n    with zipfile.ZipFile(destination, "r") as archive:\n        bad=archive.testzip()\n        if bad is not None:\n            raise SystemExit(f"Release ZIP failed integrity at {bad}")\n\n\ndef find_iscc() -> Path | None:\n    candidates = [\n        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",\n        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",\n    ]\n    found = shutil.which("iscc") or shutil.which("ISCC.exe")\n    if found:\n        candidates.insert(0, Path(found))\n    return next((path for path in candidates if path.is_file()), None)\n\n\ndef _clean_current_release_outputs() -> None:\n    RELEASE.mkdir(exist_ok=True)\n    for path in RELEASE.glob(f"DrawStudio-{APP_VERSION}-*"):\n        if path.is_file():\n            path.unlink()\n\n\ndef _write_manifest(artifacts: list[dict]) -> Path:\n    path=RELEASE / f"DrawStudio-{APP_VERSION}-manifest.json"\n    payload={\n        "schema":1,\n        "app":"Draw Studio",\n        "version":APP_VERSION,\n        "channel":BUILD_CHANNEL,\n        "architecture":"windows-x64",\n        "unsigned":True,\n        "artifacts":artifacts,\n    }\n    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\\n",encoding="utf-8")\n    return path\n\n\ndef main() -> int:\n    parser = argparse.ArgumentParser()\n    parser.add_argument("--installer", action="store_true", help="Also build the Inno Setup installer")\n    parser.add_argument("--skip-tests", action="store_true", help="Skip duplicate tests only when CI already ran the complete gate")\n    parser.add_argument("--gpu", action="store_true", help="Bundle optional NVIDIA CUDA/CuPy acceleration")\n    args = parser.parse_args()\n    if sys.platform != "win32":\n        raise SystemExit("Release EXEs must be built on Windows. Use the GitHub Actions release workflow or Build-Release.bat.")\n    github_ref=os.environ.get('GITHUB_REF_NAME','').strip()\n    github_ref_type=os.environ.get('GITHUB_REF_TYPE','').strip()\n    if github_ref_type == 'tag' and github_ref and github_ref != f'v{APP_VERSION}':\n        raise SystemExit(f'Git tag {github_ref!r} does not match Version.py ({APP_VERSION}). Expected tag v{APP_VERSION}.')\n\n    report=run_source_release_gate(BASE,soak_cycles=5000)\n    print('Step 30 source gate: PASS',report.as_dict())\n    _clean_current_release_outputs()\n\n    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])\n    run([sys.executable, "-m", "pip", "install", "-r", str(BASE / "requirements.txt")])\n\n    if not args.skip_tests:\n        run([sys.executable, "-m", "unittest", "discover", "-v"])\n        run([sys.executable, "DrawBot.py", "--self-test"])\n\n    run([sys.executable, "build_exe.py"] + (["--gpu"] if args.gpu else []))\n    exe = DIST / "DrawStudio.exe"\n    if not exe.is_file() or exe.read_bytes()[:2] != b"MZ":\n        raise SystemExit("Release build did not produce a valid DrawStudio.exe.")\n    run([str(exe), "--self-test"], cwd=DIST)\n\n    suffix = "-CUDA" if args.gpu else ""\n    zip_path = RELEASE / f"DrawStudio-{APP_VERSION}-Windows-x64{suffix}.zip"\n    zip_onedir(zip_path)\n    artifacts=[{"name":zip_path.name,"type":"windows-zip","sha256":sha256(zip_path),"bytes":zip_path.stat().st_size}]\n    hash_rows = [f"{artifacts[-1]['sha256']}  {zip_path.name}"]\n\n    if args.installer and args.gpu:\n        raise SystemExit("The CUDA release currently ships as a ZIP. Build the standard installer separately without --gpu.")\n    if args.installer:\n        iscc = find_iscc()\n        if iscc is None:\n            raise SystemExit("Inno Setup 6 was not found. Install it or run without --installer.")\n        run([str(iscc), f"/DMyAppVersion={APP_VERSION}", str(BASE / "installer" / "DrawStudio.iss")])\n        setup = RELEASE / f"DrawStudio-{APP_VERSION}-Windows-x64-Setup.exe"\n        if not setup.is_file() or setup.read_bytes()[:2] != b"MZ":\n            raise SystemExit("Installer build did not produce the expected Setup.exe.")\n        digest=sha256(setup)\n        hash_rows.append(f"{digest}  {setup.name}")\n        artifacts.append({"name":setup.name,"type":"inno-setup","sha256":digest,"bytes":setup.stat().st_size})\n\n    checksum = RELEASE / f"DrawStudio-{APP_VERSION}-SHA256.txt"\n    checksum.write_text("\\n".join(hash_rows) + "\\n", encoding="utf-8")\n    manifest=_write_manifest(artifacts)\n\n    validate_windows_release(RELEASE,app_version=APP_VERSION,require_installer=args.installer)\n    print("Step 30 Windows artifact gate: PASS")\n    print("\\nRelease artifacts:")\n    for row in hash_rows:\n        print(" ", row)\n    print(" ", checksum)\n    print(" ", manifest)\n    print("\\nThe EXE and installer remain unsigned until an Authenticode certificate is configured.")\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'''
write('build_release.py',build)

# Permanent tagged Windows release workflow. It verifies the actual installer by
# installing into an isolated directory and running the installed frozen self-test.
workflow='''name: Build and publish Draw Studio Windows release\n\non:\n  workflow_dispatch:\n  push:\n    tags:\n      - 'v*'\n\npermissions:\n  contents: write\n\nconcurrency:\n  group: draw-studio-release-${{ github.ref }}\n  cancel-in-progress: false\n\njobs:\n  build-windows:\n    runs-on: windows-latest\n    timeout-minutes: 60\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v4\n\n      - name: Set up Python\n        uses: actions/setup-python@v5\n        with:\n          python-version: '3.12'\n          architecture: 'x64'\n          cache: 'pip'\n\n      - name: Install source dependencies\n        shell: pwsh\n        run: |\n          python -m pip install --upgrade pip\n          pip install -r requirements.txt\n\n      - name: Step 30 source release gate\n        shell: pwsh\n        run: python ReleaseCandidateHardening.py --source-gate --soak-cycles 5000\n\n      - name: Run complete regressions and self-test\n        shell: pwsh\n        run: |\n          python -m unittest discover -v\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n          python DrawBot.py --self-test\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n\n      - name: Install Inno Setup\n        shell: pwsh\n        run: choco install innosetup --no-progress -y\n\n      - name: Build verified Windows release\n        shell: pwsh\n        run: python build_release.py --installer --skip-tests\n\n      - name: Validate packaged release\n        shell: pwsh\n        run: python ReleaseCandidateHardening.py --release-dir release\n\n      - name: Validate silent installer round-trip\n        shell: pwsh\n        run: |\n          $setup = Get-ChildItem release/DrawStudio-*-Windows-x64-Setup.exe | Select-Object -First 1\n          if (-not $setup) { throw 'Setup.exe was not produced' }\n          $installDir = Join-Path $env:RUNNER_TEMP 'DrawStudio-RC-install'\n          if (Test-Path $installDir) { Remove-Item $installDir -Recurse -Force }\n          & $setup.FullName '/VERYSILENT' '/SUPPRESSMSGBOXES' '/NORESTART' "/DIR=$installDir"\n          if ($LASTEXITCODE -ne 0) { throw "Silent install failed: $LASTEXITCODE" }\n          $exe = Join-Path $installDir 'DrawStudio.exe'\n          if (-not (Test-Path $exe)) { throw 'Installed DrawStudio.exe is missing' }\n          & $exe '--self-test'\n          if ($LASTEXITCODE -ne 0) { throw "Installed self-test failed: $LASTEXITCODE" }\n          $uninstall = Join-Path $installDir 'unins000.exe'\n          if (-not (Test-Path $uninstall)) { throw 'Uninstaller is missing' }\n          & $uninstall '/VERYSILENT' '/SUPPRESSMSGBOXES' '/NORESTART'\n          if ($LASTEXITCODE -ne 0) { throw "Silent uninstall failed: $LASTEXITCODE" }\n\n      - name: Upload workflow artifacts\n        uses: actions/upload-artifact@v4\n        with:\n          name: DrawStudio-${{ github.ref_name }}-Windows-x64\n          path: |\n            release/DrawStudio-*-Windows-x64.zip\n            release/DrawStudio-*-Windows-x64-Setup.exe\n            release/DrawStudio-*-SHA256.txt\n            release/DrawStudio-*-manifest.json\n          if-no-files-found: error\n          retention-days: 30\n\n      - name: Publish GitHub Release for tag\n        if: startsWith(github.ref, 'refs/tags/v')\n        shell: pwsh\n        env:\n          GH_TOKEN: ${{ github.token }}\n        run: |\n          gh release create "$env:GITHUB_REF_NAME" `\n            release/DrawStudio-*-Windows-x64.zip `\n            release/DrawStudio-*-Windows-x64-Setup.exe `\n            release/DrawStudio-*-SHA256.txt `\n            release/DrawStudio-*-manifest.json `\n            --prerelease `\n            --title "Draw Studio $env:GITHUB_REF_NAME" `\n            --notes-file RELEASE-NOTES-v1.0.129-rc1-Step30.md\n'''
write('.github/workflows/build-windows.yml',workflow)

# Mark Step 30 complete and record the freeze.
road=read('ROADMAP-STEP22-PLUS.md')
old='''## Step 30 — Release Candidate Hardening\n\nRun longer real-world stability passes, validate installer/update flows and freeze the release branch.\n'''
new='''## Completed — Step 30 — Release Candidate Hardening\n\nFreezes the numbered feature roadmap for RC1, adds executable source/artifact release gates, 5,000-cycle lifecycle stress checks, profile-isolation soak checks, corrected Update Center repository/channel handling, synchronized installer/version metadata, validated SHA-256 + release manifests, and a Windows silent install → frozen self-test → silent uninstall round trip before release artifacts can be published.\n'''
if old not in road and new not in road:
    raise RuntimeError('Step 30 roadmap block not found')
write('ROADMAP-STEP22-PLUS.md',road.replace(old,new,1))

idx=read('README-INDEX.md')
if 'STEP-30-RELEASE-CANDIDATE-HARDENING.md' not in idx:
    idx += '\n- `STEP-30-RELEASE-CANDIDATE-HARDENING.md` — RC release gates, installer/update validation and feature freeze\n- `RELEASE-NOTES-v1.0.129-rc1-Step30.md` — v1.0.129-rc1 release notes\n'
write('README-INDEX.md',idx)

# Historical version tests were written as "current build" assertions. Freeze all
# such assertions to RC1 so full unittest discovery becomes a meaningful release
# gate instead of failing solely because old feature tests name an obsolete beta.
for path in ROOT.glob('test_*.py'):
    text=path.read_text(encoding='utf-8')
    text=re.sub(r"self\.assertEqual\(\s*APP_VERSION\s*,\s*(['\"])[^'\"]+\1\s*\)", "self.assertEqual(APP_VERSION,'1.0.129-rc1')", text)
    text=re.sub(r"self\.assertEqual\(\s*FILE_VERSION\s*,\s*(['\"])[^'\"]+\1\s*\)", "self.assertEqual(FILE_VERSION,'1.0.129')", text)
    text=re.sub(r"self\.assertEqual\(\s*BUILD_CHANNEL\s*,\s*(['\"])[^'\"]+\1\s*\)", "self.assertEqual(BUILD_CHANNEL,'rc')", text)
    path.write_text(text,encoding='utf-8',newline='\n')

print('Step 30 RC integration prepared.')
