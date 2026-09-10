from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP_VERSION = '1.0.144-rc1'
FILE_VERSION = '1.0.144'
CANONICAL_REPO = 'Vxiey/Image-Draw-Bot'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def public_replace(text):
    return (text
            .replace('Vxiey/Draw-Studio', CANONICAL_REPO)
            .replace('Draw Studio', 'Image Draw Bot')
            .replace('Draw-Studio', 'Image-Draw-Bot')
            .replace('DrawStudio.exe', 'ImageDrawBot.exe')
            .replace('DrawStudio.manifest', 'ImageDrawBot.manifest')
            .replace('DrawStudio.iss', 'ImageDrawBot.iss')
            .replace('DrawStudio-', 'ImageDrawBot-')
            .replace('DrawStudio/', 'ImageDrawBot/')
            .replace('draw-studio-ci-', 'image-draw-bot-ci-')
            .replace('draw-studio-release-', 'image-draw-bot-release-'))


# Public brand replacement across source/tooling/docs. Keep compact/internal
# identifiers unless they are user-facing executable/artifact names.
text_suffixes = {'.py', '.md', '.txt', '.bat', '.yml', '.yaml', '.iss', '.manifest', '.json'}
for p in ROOT.rglob('*'):
    if not p.is_file() or p.suffix.lower() not in text_suffixes:
        continue
    if any(part in {'.git', '.build-venv', 'build', 'dist', 'release', '__pycache__'} for part in p.parts):
        continue
    try:
        text = p.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        continue
    updated = public_replace(text)
    if updated != text:
        p.write_text(updated, encoding='utf-8')

# Version / public identity.
write('Version.py',
      "APP_NAME = 'Image Draw Bot'\n"
      "APP_TAGLINE = 'Automatic Image Drawing'\n"
      "APP_VERSION = '1.0.144-rc1'\n"
      "FILE_VERSION = '1.0.144'\n"
      "BUILD_CHANNEL = 'rc'\n"
      "LEGACY_APP_NAME = 'Draw Studio'\n"
      "EXECUTABLE_NAME = 'ImageDrawBot.exe'\n"
      "LEGACY_EXECUTABLE_NAME = 'DrawStudio.exe'\n")

# Manifest rename and identity.
old_manifest = ROOT / 'DrawStudio.manifest'
new_manifest = ROOT / 'ImageDrawBot.manifest'
manifest_path = old_manifest if old_manifest.exists() else new_manifest
if not manifest_path.exists():
    raise SystemExit('Windows manifest is missing')
manifest = manifest_path.read_text(encoding='utf-8')
manifest = manifest.replace('name="DrawStudio"', 'name="ImageDrawBot"')
manifest = manifest.replace('<description>Image Draw Bot</description>', '<description>Image Draw Bot - Automatic Image Drawing</description>')
manifest = manifest.replace('<description>Draw Studio</description>', '<description>Image Draw Bot - Automatic Image Drawing</description>')
new_manifest.write_text(manifest, encoding='utf-8')
if old_manifest.exists():
    old_manifest.unlink()

# Windows version resource.
vi = read('version_info.txt')
vi = re.sub(r'filevers=\([^\)]*\)', 'filevers=(1,0,144,0)', vi)
vi = re.sub(r'prodvers=\([^\)]*\)', 'prodvers=(1,0,144,0)', vi)
for key, value in (
    ('CompanyName', 'Image Draw Bot'),
    ('FileDescription', 'Image Draw Bot - Automatic Image Drawing'),
    ('FileVersion', FILE_VERSION),
    ('InternalName', 'ImageDrawBot'),
    ('OriginalFilename', 'ImageDrawBot.exe'),
    ('ProductName', 'Image Draw Bot'),
    ('ProductVersion', FILE_VERSION),
):
    vi = re.sub(rf"StringStruct\('{key}',\s*'[^']*'\)", f"StringStruct('{key}', '{value}')", vi)
write('version_info.txt', vi)

# Inno installer rename. AppId is intentionally unchanged for in-place upgrades.
old_iss = ROOT / 'installer' / 'DrawStudio.iss'
new_iss = ROOT / 'installer' / 'ImageDrawBot.iss'
iss_path = old_iss if old_iss.exists() else new_iss
if not iss_path.exists():
    raise SystemExit('Inno Setup source is missing')
iss = public_replace(iss_path.read_text(encoding='utf-8'))
iss = re.sub(r'#define MyAppVersion "[^"]+"', '#define MyAppVersion "1.0.144-rc1"', iss)
iss = re.sub(r'VersionInfoVersion=\d+\.\d+\.\d+\.\d+', 'VersionInfoVersion=1.0.144.0', iss)
iss = iss.replace('Source: "..\\dist\\DrawStudio\\*"', 'Source: "..\\dist\\ImageDrawBot\\*"')
iss = iss.replace('ShouldLaunchDrawStudio', 'ShouldLaunchImageDrawBot')
iss = iss.replace('SignTool=drawstudio', 'SignTool=imagedrawbot')
if "HasCommandLineParam('/RELAUNCHIMAGEDRAWBOT')" not in iss:
    iss = iss.replace(
        "Result := (not WizardSilent) or HasCommandLineParam('/RELAUNCHDRAWSTUDIO');",
        "Result := (not WizardSilent) or HasCommandLineParam('/RELAUNCHIMAGEDRAWBOT') or HasCommandLineParam('/RELAUNCHDRAWSTUDIO');")
if '[InstallDelete]' not in iss:
    iss = iss.replace('[Files]\n',
        '[InstallDelete]\n'
        'Type: files; Name: "{app}\\DrawStudio.exe"\n'
        'Type: files; Name: "{autodesktop}\\Draw Studio.lnk"\n'
        'Type: files; Name: "{group}\\Draw Studio.lnk"\n\n'
        '[Files]\n')
new_iss.write_text(iss, encoding='utf-8')
if old_iss.exists():
    old_iss.unlink()

# EXE build identity.
be = read('build_exe.py')
be = be.replace("'--name', 'DrawStudio'", "'--name', 'ImageDrawBot'")
be = be.replace("'DrawStudio/ImageDrawBot.exe'", "'ImageDrawBot/ImageDrawBot.exe'")
be = be.replace('"DrawStudio/ImageDrawBot.exe"', '"ImageDrawBot/ImageDrawBot.exe"')
write('build_exe.py', be)

# Release builder identity + legacy Setup alias for pre-rebrand updater clients.
br = read('build_release.py')
br = br.replace('DIST = BASE / "dist" / "DrawStudio"', 'DIST = BASE / "dist" / "ImageDrawBot"')
br = br.replace('relative = Path("DrawStudio") / path.relative_to(DIST)', 'relative = Path("ImageDrawBot") / path.relative_to(DIST)')
old_clean = '    for path in RELEASE.glob(f"ImageDrawBot-{APP_VERSION}-*"):\n        if path.is_file():\n            path.unlink()'
new_clean = '    for pattern in (f"ImageDrawBot-{APP_VERSION}-*", f"DrawStudio-{APP_VERSION}-*"):\n        for path in RELEASE.glob(pattern):\n            if path.is_file():\n                path.unlink()'
if old_clean in br:
    br = br.replace(old_clean, new_clean)
needle = '        artifacts.append({"name":setup.name,"type":"inno-setup","sha256":digest,"bytes":setup.stat().st_size})\n'
if 'legacy-updater-bridge' not in br:
    legacy = (
        '        legacy_setup = RELEASE / f"DrawStudio-{APP_VERSION}-Windows-x64-Setup.exe"\n'
        '        shutil.copy2(setup, legacy_setup)\n'
        '        legacy_digest=sha256(legacy_setup)\n'
        '        hash_rows.append(f"{legacy_digest}  {legacy_setup.name}")\n'
        '        artifacts.append({"name":legacy_setup.name,"type":"legacy-updater-bridge","sha256":legacy_digest,"bytes":legacy_setup.stat().st_size})\n')
    br = br.replace(needle, needle + legacy)
write('build_release.py', br)

# Updater: canonical repository, new UA, prefer new installer but accept legacy alias.
uc = read('UpdateCenter.py')
uc = uc.replace('User-Agent": f"DrawStudio/{APP_VERSION}"', 'User-Agent": f"ImageDrawBot/{APP_VERSION}"')
uc = uc.replace("headers={'User-Agent':f'DrawStudio/{APP_VERSION}'}", "headers={'User-Agent':f'ImageDrawBot/{APP_VERSION}'}")
asset_function = '''def installer_asset(release):
    """Return one verified installer, preferring the Image Draw Bot name.

    DrawStudio is accepted only as a transition bridge for pre-v1.0.144 clients.
    """
    from urllib.parse import urlparse,unquote
    version=normalize_tag(release.get('tag_name'))
    if parse_version(version) is None:return None
    names=(f'ImageDrawBot-{version}-Windows-x64-Setup.exe',
           f'DrawStudio-{version}-Windows-x64-Setup.exe')
    repositories=('Vxiey/Image-Draw-Bot','Vxiey/Draw-Studio')
    hits=[]
    for rank,name in enumerate(names):
        for asset in release.get('assets') or ():
            if not isinstance(asset,dict) or asset.get('name')!=name:continue
            url=str(asset.get('browser_download_url') or '')
            parsed=urlparse(url)
            valid_paths={f'/{repo}/releases/download/{release["tag_name"]}/{name}' for repo in repositories}
            if parsed.scheme!='https' or parsed.netloc!='github.com' or unquote(parsed.path) not in valid_paths or parsed.query or parsed.fragment:continue
            digest=str(asset.get('digest') or '')
            if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}',digest):continue
            size=asset.get('size')
            if type(size) is not int or not 0<size<=2*1024**3:continue
            hits.append((rank,dict(name=name,url=url,sha256=digest[7:].lower(),size=size,version=version)))
    if not hits:return None
    hits.sort(key=lambda item:item[0])
    best_rank=hits[0][0]
    best=[item for rank,item in hits if rank==best_rank]
    return best[0] if len(best)==1 else None


'''
uc = re.sub(r'def installer_asset\(release\):.*?\n\ndef download_installer', asset_function + 'def download_installer', uc, flags=re.S)
uc = uc.replace("installed=(current.name.lower()=='imagedrawbot.exe' and any(current.parent.glob('unins*.exe')))",
                "installed=(current.name.lower() in ('imagedrawbot.exe','drawstudio.exe') and any(current.parent.glob('unins*.exe')))")
uc = uc.replace("'/RELAUNCHDRAWSTUDIO',", "'/RELAUNCHIMAGEDRAWBOT',")
write('UpdateCenter.py', uc)

# Frozen data migration: copy old data forward once, fallback to legacy if copy fails.
rp = read('RuntimePaths.py')
if 'import shutil' not in rp:
    rp = rp.replace('import os\n', 'import os\nimport shutil\n')
new_data = '''def data_dir() -> Path:
    """Return the writable Image Draw Bot data directory.

    Frozen builds migrate the legacy DrawBotStudio directory by copying it once.
    If that copy is blocked, the old directory remains the safe fallback.
    """
    if is_frozen():
        base = Path((os.environ.get("LOCALAPPDATA") or str(Path.home())))
        root = base / "ImageDrawBot"
        legacy = base / "DrawBotStudio"
        if not root.exists() and legacy.exists():
            try:
                shutil.copytree(legacy, root)
            except OSError:
                root = legacy
    else:
        root = source_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


'''
rp = re.sub(r'def data_dir\(\) -> Path:.*?\n\ndef atomic_write_text', new_data + 'def atomic_write_text', rp, flags=re.S)
write('RuntimePaths.py', rp)

# Crash dump names/storage, retaining legacy backup restoration.
cd = read('CrashDumpConfig.py')
cd = cd.replace("/'DrawBotStudio'/'dumps'", "/'ImageDrawBot'/'dumps'")
cd = cd.replace("if name not in ('ImageDrawBot.exe','python.exe','pythonw.exe'):",
                "if name not in ('ImageDrawBot.exe','DrawStudio.exe','python.exe','pythonw.exe'):")
write('CrashDumpConfig.py', cd)

# New signing variable names with legacy fallback.
cs = read('CodeSigning.py')
cs = cs.replace("thumb=str(env.get('DRAWSTUDIO_SIGNING_THUMBPRINT','')).replace(' ','')",
                "thumb=str(env.get('IMAGEDRAWBOT_SIGNING_THUMBPRINT') or env.get('DRAWSTUDIO_SIGNING_THUMBPRINT','')).replace(' ','')")
cs = cs.replace('Set DRAWSTUDIO_SIGNING_THUMBPRINT', 'Set IMAGEDRAWBOT_SIGNING_THUMBPRINT (or legacy DRAWSTUDIO_SIGNING_THUMBPRINT)')
cs = cs.replace("tool=env.get('DRAWSTUDIO_SIGNTOOL') or shutil.which('signtool.exe')",
                "tool=env.get('IMAGEDRAWBOT_SIGNTOOL') or env.get('DRAWSTUDIO_SIGNTOOL') or shutil.which('signtool.exe')")
cs = cs.replace('Set DRAWSTUDIO_SIGNTOOL to Windows SDK signtool.exe.', 'Set IMAGEDRAWBOT_SIGNTOOL to Windows SDK signtool.exe.')
cs = cs.replace("return ['/DSignRelease','/Sdrawstudio='+command]", "return ['/DSignRelease','/Simagedrawbot='+command]")
write('CodeSigning.py', cs)

# Release package still excludes legacy generated/runtime files during transition.
rpk = read('ReleasePackage.py')
if '"DrawStudio-Safety-"' not in rpk:
    rpk = rpk.replace('EXCLUDED_PREFIXES = (\n',
        'EXCLUDED_PREFIXES = (\n'
        '    "DrawStudio-Safety-",\n'
        '    "DrawStudio-crash",\n'
        '    "DrawStudio-session",\n'
        '    "DrawStudio-target-probe",\n'
        '    "DrawStudio-mouse-probe",\n')
rpk = rpk.replace('name.startswith(("Image-Draw-Bot-", "ImageDrawBot-"))',
                  'name.startswith(("Image-Draw-Bot-", "ImageDrawBot-", "Draw-Studio-", "DrawStudio-"))')
write('ReleasePackage.py', rpk)

# Release workflow: new public names + legacy Setup bridge upload.
bw = read('.github/workflows/build-windows.yml')
bw = bw.replace('DrawStudio-release-install', 'ImageDrawBot-release-install')
bw = bw.replace('"Image Draw Bot $tag"', '"Image Draw Bot $tag"')
if 'release/DrawStudio-*-Windows-x64-Setup.exe' not in bw:
    bw = bw.replace('release/ImageDrawBot-*-Windows-x64-Setup.exe\n',
                    'release/ImageDrawBot-*-Windows-x64-Setup.exe\n            release/DrawStudio-*-Windows-x64-Setup.exe\n')
    bw = bw.replace('release/ImageDrawBot-*-Windows-x64-Setup.exe release/ImageDrawBot-*-SHA256.txt',
                    'release/ImageDrawBot-*-Windows-x64-Setup.exe release/DrawStudio-*-Windows-x64-Setup.exe release/ImageDrawBot-*-SHA256.txt')
write('.github/workflows/build-windows.yml', bw)

# README SEO identity + current release link.
readme = read('README.md')
readme = re.sub(r'^# .*$', '# Image Draw Bot — Automatic Image Drawing', readme, count=1, flags=re.M)
readme = re.sub(r'^\*\*Turn images into drawings.*?\*\*$',
                '**Automatically recreate images in Microsoft Paint, Gartic Phone, Skribbl.io and other drawing apps.**',
                readme, count=1, flags=re.M)
readme = readme.replace('v1.0.143-rc4', 'v1.0.144-rc1').replace('1.0.143-rc4', '1.0.144-rc1')
if 'Formerly **Draw Studio**' not in readme:
    readme = readme.replace('\n## Download', '\n> Formerly **Draw Studio**. Existing settings and calibrations are migrated automatically.\n\n## Download', 1)
write('README.md', readme)

for doc in ('README-INDEX.md','docs/README.md','docs/IN-APP-UPDATES.md'):
    p = ROOT / doc
    if p.exists():
        t = p.read_text(encoding='utf-8').replace('v1.0.143-rc4','v1.0.144-rc1').replace('1.0.143-rc4','1.0.144-rc1')
        p.write_text(t, encoding='utf-8')

# Version history + release notes.
history_entry = '''# v1.0.144-rc1

- Full public rebrand from **Draw Studio** to **Image Draw Bot — Automatic Image Drawing**.
- GitHub repository, UI titles, Windows metadata, installer, EXE and release artifacts use the Image Draw Bot identity.
- Frozen installs use `%LOCALAPPDATA%\\ImageDrawBot`; existing `DrawBotStudio` data is copied forward automatically with a safe legacy fallback.
- Installer AppId remains unchanged for in-place upgrades and stale Draw Studio shortcuts/EXE files are removed.
- Updater accepts both ImageDrawBot and legacy DrawStudio installer/executable names during the transition.
- Sketch/single-color Paint modes continue to bypass Edit colors.

'''
for path in ('VERSION-HISTORY.md','docs/VERSION-HISTORY.md'):
    p = ROOT / path
    if p.exists() and not p.read_text(encoding='utf-8').startswith('# v1.0.144-rc1'):
        p.write_text(history_entry + p.read_text(encoding='utf-8'), encoding='utf-8')

write('RELEASE-NOTES-v1.0.144-rc1.md', '''# Image Draw Bot v1.0.144-rc1 — Automatic Image Drawing

This release completes the public rebrand from **Draw Studio** to **Image Draw Bot** while preserving upgrade compatibility.

## Rebrand

- Product name: **Image Draw Bot**
- Tagline: **Automatic Image Drawing**
- Repository: `Vxiey/Image-Draw-Bot`
- Windows executable: `ImageDrawBot.exe`
- Installer/ZIP/checksum/manifest artifacts use the `ImageDrawBot-` prefix.
- UI, calibration windows, launcher text, Windows file metadata and release titles use the new brand.

## Compatibility

- Inno Setup AppId is unchanged, so installed Draw Studio copies upgrade in place.
- Existing `%LOCALAPPDATA%\\DrawBotStudio` settings/calibrations are copied to `%LOCALAPPDATA%\\ImageDrawBot` on first frozen run; the old directory remains untouched as a fallback.
- The new updater recognizes both `ImageDrawBot.exe` and legacy `DrawStudio.exe` installations.
- A legacy-named Setup alias is published for older updater clients during the transition.

## Paint behavior

Current Paint safety fixes remain intact, including the rule that sketch/single-color modes do not open Edit colors.
''')

# Update only explicit current-version assertions, not arbitrary historical fixtures.
for p in ROOT.glob('test_*.py'):
    t = p.read_text(encoding='utf-8')
    t = re.sub(r"(assertEqual\(APP_VERSION\s*,\s*['\"])1\.0\.143-rc4(['\"]\))", r"\g<1>1.0.144-rc1\2", t)
    t = re.sub(r"(assertEqual\(FILE_VERSION\s*,\s*['\"])1\.0\.143(['\"]\))", r"\g<1>1.0.144\2", t)
    t = (t.replace('DrawStudio.manifest','ImageDrawBot.manifest')
           .replace('DrawStudio.exe','ImageDrawBot.exe')
           .replace('DrawStudio-','ImageDrawBot-')
           .replace('Vxiey/Draw-Studio','Vxiey/Image-Draw-Bot')
           .replace('Draw Studio','Image Draw Bot'))
    p.write_text(t, encoding='utf-8')

write('test_rebrand_v10144.py', '''import unittest
from pathlib import Path
from unittest import mock

from Version import APP_NAME, APP_TAGLINE, APP_VERSION, FILE_VERSION
import UpdateCenter

ROOT=Path(__file__).resolve().parent

class RebrandV10144Tests(unittest.TestCase):
    def test_public_identity(self):
        self.assertEqual(APP_NAME,'Image Draw Bot')
        self.assertEqual(APP_TAGLINE,'Automatic Image Drawing')
        self.assertEqual(APP_VERSION,'1.0.144-rc1')
        self.assertEqual(FILE_VERSION,'1.0.144')
        self.assertEqual(UpdateCenter.GITHUB_REPOSITORY,'Vxiey/Image-Draw-Bot')

    def test_windows_identity(self):
        installer=(ROOT/'installer'/'ImageDrawBot.iss').read_text(encoding='utf-8')
        self.assertIn('AppId={{6A4AD303-4F16-4ED7-A9AF-5B912352D83E}',installer)
        self.assertIn('AppName=Image Draw Bot',installer)
        self.assertIn('ImageDrawBot.exe',installer)
        self.assertIn('/RELAUNCHIMAGEDRAWBOT',installer)
        self.assertIn('/RELAUNCHDRAWSTUDIO',installer)
        self.assertFalse((ROOT/'installer'/'DrawStudio.iss').exists())
        self.assertTrue((ROOT/'ImageDrawBot.manifest').exists())
        self.assertFalse((ROOT/'DrawStudio.manifest').exists())

    def test_build_and_release_names(self):
        build=(ROOT/'build_exe.py').read_text(encoding='utf-8')
        release=(ROOT/'build_release.py').read_text(encoding='utf-8')
        workflow=(ROOT/'.github'/'workflows'/'build-windows.yml').read_text(encoding='utf-8')
        self.assertIn("'--name', 'ImageDrawBot'",build)
        self.assertIn('dist" / "ImageDrawBot',release)
        self.assertIn('ImageDrawBot-${{ github.ref_name }}-Windows-x64',workflow)

    def test_legacy_installed_exe_is_recognized(self):
        from pathlib import Path as RealPath
        with mock.patch('pathlib.Path.glob', return_value=[RealPath('C:/Apps/unins000.exe')]):
            args=UpdateCenter.installer_launch_args('setup.exe',executable='C:/Apps/Draw Studio/DrawStudio.exe')
        self.assertIn('/RELAUNCHIMAGEDRAWBOT',args)

if __name__=='__main__': unittest.main()
''')

# Remove transient rebrand machinery in the resulting commit.
for transient in (ROOT/'.github/workflows/rebrand-image-draw-bot.yml', ROOT/'tools/rebrand_image_draw_bot.py'):
    if transient.exists():
        transient.unlink()

# Static guardrails before commit.
assert (ROOT/'ImageDrawBot.manifest').is_file()
assert (ROOT/'installer/ImageDrawBot.iss').is_file()
assert not (ROOT/'DrawStudio.manifest').exists()
assert not (ROOT/'installer/DrawStudio.iss').exists()
assert "APP_NAME = 'Image Draw Bot'" in read('Version.py')
assert 'GITHUB_REPOSITORY = "Vxiey/Image-Draw-Bot"' in read('UpdateCenter.py')
assert "'--name', 'ImageDrawBot'" in read('build_exe.py')
