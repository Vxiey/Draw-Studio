# Step 30 — Release Candidate Hardening

Step 30 freezes feature development for the release-candidate line and turns release assumptions into executable gates.

## Release policy

During the RC phase, new renderer features are frozen. Changes should be limited to release blockers, crashes/freezes, security fixes, installer/update defects, regression fixes, documentation corrections and test hardening.

## New release gate

`ReleaseCandidateHardening.py` performs non-interactive checks before a Windows release can be accepted:

- `Version.py`, `version_info.txt` and Inno Setup version consistency
- fixed Inno Setup `AppId` and per-user installation policy
- Update Center repository consistency (`Vxiey/Draw-Studio`)
- RC channel/version validation
- build workflow hardening hooks
- repeated start/stop/disarm lifecycle soak
- repeated built-in profile-storage isolation soak
- Windows ZIP integrity and required `DrawStudio.exe`
- rejection of logs, dumps, bytecode, tests and one-time patch files in Windows packages
- SHA-256 verification
- release manifest validation

The release gate is deterministic and never performs native mouse input, target-window activation, automatic downloads or installation.

## Windows release pipeline

The permanent Windows workflow now:

1. runs the Step 30 source gate,
2. runs the complete unit-test discovery suite,
3. runs Draw Studio's non-interactive self-test,
4. builds the PyInstaller onedir application,
5. builds the per-user Inno Setup installer,
6. validates ZIP/installer/checksum/manifest artifacts,
7. silently installs the RC into an isolated temporary directory,
8. runs the installed `DrawStudio.exe --self-test`,
9. silently uninstalls it,
10. uploads only validated release artifacts.

A GitHub tag must exactly match `v{APP_VERSION}` before `build_release.py` will accept it.

## Update hardening

The manual Update Center points to the active repository `Vxiey/Draw-Studio`. RC-channel update selection accepts release-candidate/stable builds instead of treating older beta-channel releases as RC updates. Network access remains explicit: checking for updates happens only when the user asks for it, and the updater still does not auto-download or auto-install anything.

## Installer hardening

The Inno Setup file uses the same RC version as `Version.py`, keeps the existing stable `AppId`, installs per-user with `PrivilegesRequired=lowest`, and is validated through a silent install/self-test/uninstall round trip on Windows CI.

## RC soak tests

Step 30 adds repeated pure lifecycle stress checks. The default source gate executes 5,000 start/stop authorization cycles and verifies that the final state is always:

- no active draw activity,
- native input not armed,
- no pending automatic draw request.

It also repeats profile-storage key checks to ensure profile identity remains stable and unique during the RC gate.

## Package cleanliness

Release validation rejects runtime/debug leakage including `.log`, `.dmp`, `.pyc`, `.pyo`, temporary files, `__pycache__`, safety-report directories, test modules and one-time integration scripts/workflows from the packaged Windows application.

The separate source ZIP packaging step also excludes build outputs, virtual environments, caches, previous release ZIPs and all temporary `*_once` patch/workflow files.

## Release freeze

`v1.0.129-rc1` is the first Step 30 release candidate. Step 30 is the final numbered roadmap implementation step. After RC validation, changes should remain blocker/regression fixes until the stable release is cut.
