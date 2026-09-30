"""Diagnostics from supplied widthwise measurements/fields, not a flatness solver."""
import math


def diagnose_profile(width_positions_m, thickness_m, membrane_strain_mismatch,
                     through_thickness_curvature_inv_m, *, temperature_k, applied_tension_pa):
    """Report geometric crown and independent mismatch/curvature descriptors.

    Crown is center thickness minus mean edge thickness. Across-width membrane
    mismatch is reported separately from through-thickness bending curvature.
    An unloaded buckle or wave amplitude cannot be inferred from these samples.
    """
    sequences = (width_positions_m, thickness_m, membrane_strain_mismatch,
                 through_thickness_curvature_inv_m)
    n = len(width_positions_m)
    if n < 3 or n % 2 == 0 or any(len(x) != n for x in sequences):
        raise ValueError('odd, matching widthwise sample arrays of length >= 3 required')
    if any(not math.isfinite(v) for x in sequences for v in x):
        raise ValueError('all samples must be finite')
    if any(b <= a for a, b in zip(width_positions_m, width_positions_m[1:])):
        raise ValueError('width positions must be strictly increasing')
    if any(v <= 0 for v in thickness_m) or not math.isfinite(temperature_k) or temperature_k <= 0:
        raise ValueError('thickness and absolute temperature must be positive')
    if not math.isfinite(applied_tension_pa) or applied_tension_pa < 0:
        raise ValueError('applied tension must be finite and nonnegative')
    center = thickness_m[n // 2]
    edges = (thickness_m[0] + thickness_m[-1]) / 2
    avg_membrane = sum(membrane_strain_mismatch) / n
    return {'status': 'SUPPLIED_FIELDS_ONLY', 'temperature_k': temperature_k,
            'applied_tension_pa': applied_tension_pa,
            'center_crown_m': center - edges,
            'wedge_m': thickness_m[-1] - thickness_m[0],
            'thickness_range_m': max(thickness_m) - min(thickness_m),
            'membrane_mismatch_rms': math.sqrt(sum((x-avg_membrane)**2 for x in membrane_strain_mismatch)/n),
            'through_thickness_curvature_range_inv_m': max(through_thickness_curvature_inv_m)-min(through_thickness_curvature_inv_m),
            'latent_flatness_prediction': None, 'unloaded_wave_amplitude_m': None}
