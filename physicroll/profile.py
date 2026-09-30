"""Diagnostics of supplied piecewise-linear width fields; no flatness prediction."""
import math
from bisect import bisect_right


def diagnose_profile(width_positions_m, thickness_m, membrane_strain_mismatch,
                     through_thickness_curvature_inv_m, *, temperature_k, applied_tension_pa):
    sequences = (width_positions_m, thickness_m, membrane_strain_mismatch,
                 through_thickness_curvature_inv_m)
    n = len(width_positions_m)
    if n < 3 or any(len(x) != n for x in sequences):
        raise ValueError('matching widthwise sample arrays of length >= 3 required')
    def finite(v):
        return not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v)
    if any(not finite(v) for x in sequences for v in x):
        raise ValueError('all samples must be finite numbers')
    if any(b <= a for a,b in zip(width_positions_m,width_positions_m[1:])):
        raise ValueError('width positions must be strictly increasing')
    if any(v <= 0 for v in thickness_m) or not finite(temperature_k) or temperature_k <= 0:
        raise ValueError('thickness and absolute temperature must be positive')
    if not finite(applied_tension_pa) or applied_tension_pa < 0:
        raise ValueError('applied tension must be finite and nonnegative')
    widths = [b-a for a,b in zip(width_positions_m,width_positions_m[1:])]
    total_width = width_positions_m[-1]-width_positions_m[0]
    if not math.isfinite(total_width):
        raise ValueError('width interval exceeds numerical domain')
    midpoint = (width_positions_m[0]+width_positions_m[-1])/2
    i = min(bisect_right(width_positions_m,midpoint)-1,n-2)
    ratio = (midpoint-width_positions_m[i])/widths[i]
    center = thickness_m[i]+ratio*(thickness_m[i+1]-thickness_m[i])
    def mean(field):
        return math.fsum(w*(a+b)/2 for w,a,b in zip(widths,field,field[1:]))/total_width
    avg_membrane = mean(membrane_strain_mismatch)
    centered = [x-avg_membrane for x in membrane_strain_mismatch]
    variance = math.fsum(w*(a*a+a*b+b*b)/3 for w,a,b in zip(widths,centered,centered[1:]))/total_width
    if not math.isfinite(variance):
        raise ValueError('profile variance exceeds numerical domain')
    return {'status':'SUPPLIED_FIELDS_ONLY', 'temperature_k':temperature_k,
            'applied_tension_pa':applied_tension_pa, 'center_position_m':midpoint,
            'center_crown_m':center-(thickness_m[0]+thickness_m[-1])/2,
            'wedge_m':thickness_m[-1]-thickness_m[0],
            'thickness_range_m':max(thickness_m)-min(thickness_m),
            'membrane_mismatch_mean':avg_membrane, 'membrane_mismatch_rms':math.sqrt(variance),
            'through_thickness_curvature_mean_inv_m':mean(through_thickness_curvature_inv_m),
            'max_abs_curvature_inv_m':max(map(abs,through_thickness_curvature_inv_m)),
            'through_thickness_curvature_range_inv_m':max(through_thickness_curvature_inv_m)-min(through_thickness_curvature_inv_m),
            'latent_flatness_prediction':None, 'unloaded_wave_amplitude_m':None}
