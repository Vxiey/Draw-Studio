# Adaptive source consolidated on main

Merged adaptive-hybrid-132 at 0fa46061d1d6aff8f853b03cc7245243ac7da318 into main, preserving its four commits and files. These experimental modules are retained alongside the current renderer; this source consolidation does not switch the application's active renderer.

Fixed the benchmark's unsupported build_pixel_map cancellation argument. Six synthetic benchmark cases completed with no missing, spilled or wrong-color pixels in their discrete adaptive simulations. This is not physical input or GPU verification.

Windows CI exposed two UTF-8 BOM fixture writes using the system default encoding; both now specify UTF-8. The 51 maintenance tests pass locally after this correction. The full Windows job is rerun.
