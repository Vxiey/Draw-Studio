# Developer guide

Image Draw Bot uses Python, Tkinter/CustomTkinter, NumPy and Pillow, with optional CuPy/CUDA and OpenCL processing. PyInstaller packages the Windows app and Inno Setup builds Setup.

## Source and validation

Follow the [source setup](https://github.com/Vxiey/Image-Draw-Bot#run-from-source), then run on Windows:

```powershell
python ReleasePackage.py --check
python -m unittest discover -v
python DrawBot.py --self-test
```

The repository CI covers source hygiene and planner regressions on Windows/Linux. The release workflow also builds Windows artifacts and validates silent installation, installed self-test and uninstallation. These gates do not replace testing a real target app on the user's machine.

## Relevant modules

- GettingStarted.py: local guide content and setting explanations.
- StudioUI.py: UI controls and tooltip behavior.
- BeginnerSetupWizard.py: profile-specific readiness checklist.
- AppBranding.py / TaskbarIdentity.py: window and taskbar identity.
- DrawBot.py: application integration and drawing workflow.

[Publishing instructions](https://github.com/Vxiey/Image-Draw-Bot/blob/main/docs/PUBLISHING.md) · [Release structure](https://github.com/Vxiey/Image-Draw-Bot/blob/main/docs/RELEASE-STRUCTURE.md)
