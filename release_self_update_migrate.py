from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parent
OLD_APP = '1.0.133-rc3'
NEW_APP = '1.0.140-rc1'
OLD_FILE = '1.0.133'
NEW_FILE = '1.0.140'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')


write('Version.py', "APP_NAME = 'Draw Studio'\nAPP_VERSION = '1.0.140-rc1'\nFILE_VERSION = '1.0.140'\nBUILD_CHANNEL = 'rc'\n")

text = read('version_info.txt')
text = text.replace('(1,0,133,0)', '(1,0,140,0)').replace("'1.0.133'", "'1.0.140'")
write('version_info.txt', text)

installer = read('installer/DrawStudio.iss')
installer = installer.replace('#define MyAppVersion "1.0.133-rc3"', '#define MyAppVersion "1.0.140-rc1"')
installer = installer.replace('VersionInfoVersion=1.0.133.0', 'VersionInfoVersion=1.0.140.0')
if '[Run]\n' not in installer:
    raise SystemExit('installer [Run] section missing')
installer = installer.split('[Run]\n', 1)[0] + textwrap.dedent(r'''[Run]
Filename: "{app}\DrawStudio.exe"; Description: "Launch Draw Studio"; Flags: nowait postinstall; Check: ShouldLaunchDrawStudio

[Code]
function HasCommandLineParam(const Value: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
  begin
    if CompareText(ParamStr(I), Value) = 0 then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

function ShouldLaunchDrawStudio(): Boolean;
begin
  Result := (not WizardSilent) or HasCommandLineParam('/RELAUNCHDRAWSTUDIO');
end;
''')
write('installer/DrawStudio.iss', installer)

updater = read('UpdateCenter.py')
marker = '\ndef launch_installer(path, asset, *, executable=None, launcher=None, cancelled=lambda:False):\n'
if marker not in updater:
    raise SystemExit('UpdateCenter launch_installer marker missing')
updater = updater.split(marker, 1)[0].rstrip() + '\n\n' + textwrap.dedent('''
def installer_launch_args(path, *, executable=None):
    """Build updater arguments without touching the OS, for deterministic tests.

    Installed builds update silently in place and request an explicit relaunch
    after Setup replaces the application files. Portable/source builds keep
    the normal interactive installer flow and are never overwritten in place.
    """
    import sys
    from pathlib import Path
    target=Path(path)
    current=Path(executable or sys.executable)
    args=[str(target),'/SP-','/NORESTART']
    installed=(current.name.lower()=='drawstudio.exe' and any(current.parent.glob('unins*.exe')))
    if installed:
        args.extend([
            '/VERYSILENT',
            '/SUPPRESSMSGBOXES',
            '/CLOSEAPPLICATIONS',
            '/RELAUNCHDRAWSTUDIO',
            '/DIR='+str(current.parent),
        ])
    return args


def launch_installer(path, asset, *, executable=None, launcher=None, cancelled=lambda:False):
    """Recheck staged bytes and launch the verified Windows updater."""
    import hashlib,os,subprocess
    from pathlib import Path
    if os.name!='nt':raise UpdateCheckError('Automatic installation requires Windows.')
    target=Path(path)
    digest=hashlib.sha256()
    with target.open('rb') as stream:
        if stream.read(2)!=b'MZ':raise UpdateCheckError('Invalid installer.')
        stream.seek(0)
        for block in iter(lambda:stream.read(1024*1024),b''):
            if cancelled():raise InterruptedError('Update cancelled.')
            digest.update(block)
    if target.stat().st_size!=asset['size'] or digest.hexdigest()!=asset['sha256']:
        raise UpdateCheckError('Installer changed after download; check for updates again.')
    args=installer_launch_args(target,executable=executable)
    if cancelled():raise InterruptedError('Update cancelled.')
    return (launcher or subprocess.Popen)(args)
''').lstrip()
write('UpdateCenter.py', updater)

version_tests = []
for path in sorted(ROOT.glob('test_*.py')):
    text = path.read_text(encoding='utf-8')
    if OLD_APP in text:
        version_tests.append(path.name)
        text = text.replace(OLD_APP, NEW_APP).replace(OLD_FILE, NEW_FILE)
        path.write_text(text, encoding='utf-8')
if len(version_tests) < 60:
    raise SystemExit(f'expected broad version-pin migration, found {len(version_tests)} tests')

path = ROOT / 'test_update_center_v1059.py'
text = path.read_text(encoding='utf-8')
if 'test_published_rc3_detects_v10140_rc1_as_update' not in text:
    marker = "\n\nif __name__=='__main__':\n"
    case = textwrap.dedent('''
        def test_published_rc3_detects_v10140_rc1_as_update(self):
            release={
                'tag_name':'v1.0.140-rc1','draft':False,'prerelease':True,
                'html_url':'https://github.com/Vxiey/Draw-Studio/releases/tag/v1.0.140-rc1',
                'name':'Draw Studio v1.0.140-rc1','assets':[],
            }
            from unittest.mock import patch
            with patch('UpdateCenter.APP_VERSION','1.0.133-rc3'), patch('UpdateCenter.BUILD_CHANNEL','rc'):
                result=check_for_updates(request_get=lambda *a,**k:_Response([release]))
            self.assertTrue(result['update_available'])
            self.assertEqual(result['latest_version'],'1.0.140-rc1')
    ''').rstrip() + '\n'
    case = ''.join(('    ' + line if line.strip() else line) for line in case.splitlines(True))
    if marker not in text:
        raise SystemExit('update-center test marker changed')
    text = text.replace(marker, '\n' + case + marker)
path.write_text(text, encoding='utf-8')

path = ROOT / 'test_installer_updates.py'
text = path.read_text(encoding='utf-8')
text = text.replace('from UpdateCenter import installer_asset,download_installer,UpdateCheckError',
                    'from UpdateCenter import installer_asset,download_installer,installer_launch_args,UpdateCheckError')
marker = "    @unittest.skipUnless(__import__('os').name=='nt','Windows installer handoff')\n"
if 'test_installed_build_uses_silent_in_place_relaunch' not in text:
    cases = textwrap.dedent('''
        def test_installed_build_uses_silent_in_place_relaunch(self):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);setup=root/'setup.exe';setup.write_bytes(DATA)
                executable=root/'DrawStudio.exe';(root/'unins000.exe').write_bytes(b'MZ')
                args=installer_launch_args(setup,executable=executable)
                self.assertIn('/DIR='+str(root),args)
                for flag in ('/VERYSILENT','/SUPPRESSMSGBOXES','/CLOSEAPPLICATIONS','/RELAUNCHDRAWSTUDIO','/NORESTART'):
                    self.assertIn(flag,args)
                self.assertNotIn('/FORCECLOSEAPPLICATIONS',args)

        def test_portable_build_never_overwrites_itself_or_forces_silent_mode(self):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);setup=root/'setup.exe';executable=root/'DrawStudio.exe'
                args=installer_launch_args(setup,executable=executable)
                self.assertFalse(any(arg.startswith('/DIR=') for arg in args))
                self.assertNotIn('/VERYSILENT',args)
                self.assertNotIn('/RELAUNCHDRAWSTUDIO',args)

    ''')
    cases = ''.join(('    ' + line if line.strip() else line) for line in cases.splitlines(True))
    if marker not in text:
        raise SystemExit('installer test marker changed')
    text = text.replace(marker, cases + marker)
line = "            self.assertIn('/NORESTART',calls[0])\n"
extra = "            self.assertIn('/VERYSILENT',calls[0])\n            self.assertIn('/RELAUNCHDRAWSTUDIO',calls[0])\n"
if extra not in text:
    if line not in text:
        raise SystemExit('installer handoff assertion pattern changed')
    text = text.replace(line, line + extra)
path.write_text(text, encoding='utf-8')

history = read('VERSION-HISTORY.md')
if not history.startswith('# v1.0.140-rc1'):
    history = textwrap.dedent('''
    # v1.0.140-rc1

    - Merge the v1.0.134–v1.0.140 drawing-engine correctness, travel, semantic-barrier and Cost Model v2 work.
    - Installed Windows builds can download a verified GitHub Release installer, update the same installation in place, and relaunch Draw Studio automatically.
    - Version bumps on `main` trigger the verified Windows release workflow so Update Center can discover newly published installers.
    - Keep SHA-256, size, redirect-host and PE-header verification before any downloaded installer is started.

    ''').lstrip() + history
write('VERSION-HISTORY.md', history)

readme = read('README.md')
readme = readme.replace('## Download — v1.0.133-rc3', '## Download — v1.0.140-rc1')
readme = readme.replace('/v1.0.133-rc3/DrawStudio-1.0.133-rc3-', '/v1.0.140-rc1/DrawStudio-1.0.140-rc1-')
readme = readme.replace('(RELEASE-NOTES-v1.0.133-rc3.md)', '(RELEASE-NOTES-v1.0.140-rc1.md)')
readme = readme.replace('From **v1.0.133-rc3**, press **Check updates / install** while the app is idle.',
                        'Installed Windows builds can press **Check updates / install** while the app is idle. A newer verified release is installed over the same Draw Studio installation and the app relaunches automatically after Setup completes.')
write('README.md', readme)

index = read('README-INDEX.md')
index = index.replace('[Current release: v1.0.133-rc3](RELEASE-NOTES-v1.0.133-rc3.md)',
                      '[Current release: v1.0.140-rc1](RELEASE-NOTES-v1.0.140-rc1.md)')
write('README-INDEX.md', index)

write('docs/IN-APP-UPDATES.md', textwrap.dedent('''
# In-app updates

Press **Check updates / install** while Draw Studio is idle. The installed Windows app checks public GitHub Releases in `Vxiey/Draw-Studio` for the newest version allowed by the current release channel.

For installed builds, Draw Studio downloads only the exact versioned Windows x64 Setup asset, validates the published size and GitHub SHA-256 digest, validates the PE header, hashes the file again immediately before launch, and then starts the installer in the existing installation directory. The app performs its normal controlled shutdown after the installer starts. Setup runs silently for an in-app upgrade and relaunches Draw Studio after replacement completes.

The updater does not use forced process termination. A failed, cancelled, truncated, oversized, redirected-to-an-unexpected-host, or checksum-mismatched download is removed without touching the installed application. The fixed Inno Setup AppId keeps upgrades attached to the same installation.

Portable ZIP and Python-source runs are never silently overwritten in place. They use the normal installer destination/flow instead.

Stable builds do not upgrade to prereleases. RC builds accept newer RC or stable releases. Updates use complete verified installers rather than binary delta patches.

## Publishing future patches

Increment `APP_VERSION`/`FILE_VERSION`, synchronize release metadata/tests, and add the matching release notes. A `Version.py` change merged to `main` automatically triggers the verified Windows release workflow. The workflow runs release hardening, full Windows tests, `DrawBot.py --self-test`, package validation and a silent install/self-test/uninstall round trip before publishing the versioned installer, portable ZIP, SHA-256 file and manifest.

Published versions are not overwritten. Draft upload retries must target the same commit. Release tags must match `APP_VERSION`.

The first updater-enabled release was `1.0.133-rc2`; `1.0.140-rc1` strengthens installed-build in-place update and automatic relaunch behavior.

References: [GitHub release asset digests](https://github.blog/changelog/2025-06-03-releases-now-expose-digests-for-release-assets/) and [Inno Setup command-line parameters](https://jrsoftware.org/ishelp/topic_setupcmdline.htm).
''').lstrip())

write('RELEASE-NOTES-v1.0.140-rc1.md', textwrap.dedent('''
# Draw Studio 1.0.140-rc1

This release integrates the drawing-engine correctness and performance work completed in v1.0.134 through v1.0.140 and restores the Windows release/update chain so installed builds can discover and install newer versions.

## Drawing engine

- Canonical raster-identity regression oracle and generated property coverage.
- Ordered execution/travel telemetry and travel-aware Extra Fast candidate selection.
- Geometry-safe bounded 2-opt with strict pen-up travel non-regression.
- Portrait outline/tone semantic barriers that survive target-path caps.
- Hybrid Cost Model v2 with confidence-weighted calibration, MAPE-aware uncertainty and compatible atomic point timing.

## Windows self-update

- Update Center accepts only the exact versioned Windows installer from this repository.
- Downloaded installers are size-checked, SHA-256 verified and PE-header checked before launch.
- Installed Draw Studio builds update the existing installation in place using the fixed application AppId.
- In-app updates use a very-silent installer handoff, controlled application shutdown, and automatic relaunch after installation.
- Portable/source runs never overwrite themselves in place; they use the normal installer flow.
- A `Version.py` change merged to `main` automatically triggers the verified Windows release workflow.

## Release validation

The release workflow runs source hygiene, release hardening, full Windows regressions, `DrawBot.py --self-test`, package validation, and a silent install/self-test/uninstall round trip before publishing assets.

This RC remains unsigned unless code signing is explicitly enabled.
''').lstrip())

print(f'Prepared v1.0.140-rc1; synchronized {len(version_tests)} version-pinned regression files.')
