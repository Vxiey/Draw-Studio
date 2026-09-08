"""Color-fidelity diagnostics/rating shared by preview and final plans."""
from __future__ import annotations

def fidelity_rating(*, average_delta_e2000: float, luminance_drift_percent: float,
                    max_delta_e2000: float=0.0) -> str:
    de=float(average_delta_e2000);lum=abs(float(luminance_drift_percent));mx=float(max_delta_e2000)
    if de<=2.0 and lum<=4.0 and mx<=8.0:return 'Excellent'
    if de<=4.0 and lum<=8.0 and mx<=16.0:return 'Good'
    if de<=7.0 and lum<=14.0 and mx<=28.0:return 'Acceptable'
    if de<=12.0 and lum<=24.0:return 'Poor'
    return 'Very Poor'


def should_auto_remap(diag: dict) -> bool:
    return (abs(float(diag.get('luminance_drift_percent',0.0)))>15.0 or
            float(diag.get('average_delta_e2000',0.0))>8.0 or
            bool(diag.get('dark_bias_detected',False)))
