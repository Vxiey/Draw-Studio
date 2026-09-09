# Release naming policy

Draw Studio releases, generated archives, GitHub release notes and build-trigger files use versioned feature names only.

## Current format

Use:

```text
Draw-Studio-<version>-<feature-focus>.zip
DrawStudio-<version>-Windows-x64.zip
DrawStudio-<version>-Windows-x64-Setup.exe
RELEASE-NOTES-v<version>.md
RELEASE-NOTES-v<version>-<feature-focus>.md
```

Do not add roadmap sequence labels to new release titles, artifact names, ZIP names, release-note filenames, branch names or GitHub Actions trigger filenames.

## Examples

```text
Draw-Studio-1.0.136-beta-Accuracy-Renderer-Upgrade.zip
RELEASE-NOTES-v1.0.136-beta-Accuracy-Renderer-Upgrade.md
.github/release-build-trigger
```

Historical implementation notes may still explain old development order internally, but current public release names must be version-first and feature-focused.
