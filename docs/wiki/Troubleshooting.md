# Troubleshooting

**Stop unexpected drawing with Esc before changing setup.**

| Problem | Next checks |
| --- | --- |
| Start unavailable | Open Setup wizard, load an image, check current operation; browser/manual start may require Unlock |
| Paint preparation fails | One visible Paint window, blank full canvas, visible toolbar and RGB controls; read status |
| Mouse draws in wrong place | Correct profile, canvas bounds, zoom and display scaling; recalibrate then test |
| Wrong colors or tools | Target palette/tool calibration and current brush; stop before another attempt |
| Gaps or missed actions | Lower input speed; verify target focus and brush behavior |
| Slow preparation | Reduce planning resolution/detail; start with Auto resource settings |
| Slow drawing | Fewer details/color switches, simpler source or Extra Fast; leave enough round time |
| Blank/old preview | Confirm loaded image and canvas, read status, press Build preview again |
| Old taskbar icon | Check version and executable path; see Updates |
| Python not found | Use packaged Setup/ZIP, or install 64-bit Python 3.10+ for source use |
| GPU unavailable | CPU fallback remains available; check compatible backend and graphics driver |

## Report a reproducible problem

Use [GitHub Issues](https://github.com/Vxiey/Image-Draw-Bot/issues). Include app version, Windows version, target/profile, installer or portable/source launch, exact steps, expected/actual behavior and the status/error text. For icon issues include a screenshot and launch path. For drawing issues include a small example you can share.

Runtime safety reports and diagnostics are local. Review files for personal information before attaching them. Automated tests do not confirm compatibility with every Paint/browser layout.

[FAQ](FAQ) · [First Use](First-Use) · [Gartic Phone requirements](Gartic-Phone)
