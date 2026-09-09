"""Color-fidelity diagnostics/rating shared by preview and final plans."""
from __future__ import annotations
import math

def fidelity_rating(*, average_delta_e2000: float, luminance_drift_percent: float,
                    max_delta_e2000: float=0.0) -> str:
    try:
        de=float(average_delta_e2000);lum=abs(float(luminance_drift_percent));mx=float(max_delta_e2000)
    except (TypeError, ValueError, OverflowError):
        return "Unavailable"
    if not all(math.isfinite(v) for v in (de,lum,mx)) or de < 0 or mx < 0:
        return "Unavailable"
    if de<=2.0 and lum<=4.0 and mx<=8.0:return 'Excellent'
    if de<=4.0 and lum<=8.0 and mx<=16.0:return 'Good'
    if de<=7.0 and lum<=14.0 and mx<=28.0:return 'Acceptable'
    if de<=12.0 and lum<=24.0:return 'Poor'
    return 'Very Poor'


def should_auto_remap(diag: dict) -> bool:
    if not isinstance(diag, dict):
        return False
    try:
        lum=float(diag.get('luminance_drift_percent',0.0))
        de=float(diag.get('average_delta_e2000',0.0))
    except (TypeError, ValueError, OverflowError):
        return False
    return (math.isfinite(lum) and abs(lum)>15.0 or
            math.isfinite(de) and de>8.0 or diag.get('dark_bias_detected') is True)
