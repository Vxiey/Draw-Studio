# Contributing to Image Draw Bot

Thanks for helping improve Image Draw Bot.

## Good first contributions

Useful contributions include bug reports, target-profile fixes, Paint/Gartic/Skribbl calibration improvements, rendering-quality regressions, performance measurements, documentation fixes, and reproducible test cases.

## Before opening an issue

- Use the latest published release or current `main` when possible.
- Search existing issues first.
- Include the target app/profile, Image Draw Bot version, Windows version and display scaling.
- For drawing or calibration bugs, include the relevant session/crash/target-probe logs when available.
- Do not upload API keys, tokens, personal paths or other secrets.

## Pull requests

Keep changes focused and preserve existing working subsystems unless a root-cause fix requires a larger change. Rendering changes should protect image quality first, then stability, speed and resource usage.

Before submitting a pull request, run the relevant tests. For a full local validation pass:

```powershell
python ReleasePackage.py --check
python -m unittest discover -v
python DrawBot.py --self-test
```

For changes to the drawing engine, also verify that Paint/Gartic/Skribbl profile behavior remains isolated and that preview and actual draw planning stay aligned.

## Project priorities

1. Image quality
2. Stability
3. Real drawing speed
4. CPU/GPU/RAM efficiency
5. Ease of use
6. Backwards compatibility
7. Maintainable architecture

Please prefer measurable fixes over lower stroke counts that reduce recognizability or accuracy.
