"""Lengthwise-band physics and hypotheses for the band screening engine (schema v2).

Status: ``SCREENING_RESULT_NOT_PLANT_VALIDATED``. Integration layer for bands that run ALONG the
strip at fixed width positions. Equations live in the wrapped modules and are only called here:

- ``roll_thermal``: circumferentially averaged axisymmetric work-roll temperature and thermal
  radius growth under a spray header (steady state and transients);
- ``strip_shape``: roll bump -> thickness transfer with the exit-tension feedback, differential
  elongation, I-units, latent/manifest bands, Shohet-Townsend dead band, crown heredity, coil
  ridge build-up, tension troughs, two-tone positions, grinding feed pitch, spacing analysis.

Integration choices (SPEC6 6.2 / 6.7; each is reported in the result):

- Stripes are found by DIFFERENCING two steady solutions under the same pass: radius growth
  with the actual header state (blocked / partial nozzles) minus radius growth with a healthy
  header (all levels 1). The difference is thresholded directly at ``STRIPE_THRESHOLD_M``
  (``local_stripes`` with ``smooth_order=0`` would subtract the strip mean, which turns the
  zero background of a difference profile into a spurious cold stripe). Events are differenced
  against the steady state they start from.
- The exit-tension feedback ``N_x' = -dF/dsigma_exit / width`` [m] is ALWAYS passed to the
  shape chain; three levels are reported (rigid-transfer bound, compliance only, with
  feedback). A LATENT band (tension stripe, flat in the mill) counts as a model band: it shows
  on a shapemeter and appears once tension is released.
- The healthy-header nozzle-pattern ripple (healthy growth minus its moving average over one
  nozzle pitch, interior of the strip) is reported and fed through the shape chain.
- The smooth thermal crown (centre minus strip-edge mean) goes to the crown / heredity model:
  gap crown used = supplied mechanical gap crown - 2 x healthy thermal crown (both work rolls).
- Incoming ridges [D, this integration layer]: local force per width
  ``dp' = (F_hin/W + N_x'*E*xi/H)*dH - Q_eff*dh`` with roll compliance ``dh = 2*C(lam)*dp'``
  gives ``dh = 2*C*(F_hin/W + N_x'*E*xi/H)*dH/(1 + 2*C*Q_eff)``, ``lam = 2 x ridge width``
  (clamped to [4a, R]); limits: rigid rolls -> dh = 0 (full elongation xi*dH/H), dominant
  tension feedback -> dh = (h/H)*dH (no elongation). The exit ridge dh is wound into the coil.
- Stripe growth after a spray change: ``dR/dt = 2*alpha*factor*dq/(rho*c)`` with
  ``dq = (h_before - h_after)*(T_surface - T_coolant)`` (SPEC6 6.7), reported beside the
  simulated initial rate. The model's fade (half-decay of the order of a minute) is slower
  than the ~20 s first-order flatness response identified on a plant (Dohmae & Okamura 2012):
  an open discrepancy (possible causes, none modelled: bite heat depending on the roll
  surface temperature, emulsion-level heat transfer, per-revolution effects).

NOT modelled here: everything the wrapped modules do not model; lateral strip tracking; the
second work roll's own header (``rolls_carrying_stripe`` says how many rolls carry a stripe).
"""
import math

from . import roll_thermal as rt
from . import strip_shape as ss
from .band_process import (failed, int_list, keys, not_supplied, num, num_list,
                           opt_num)

STRIPE_THRESHOLD_M = 1e-7          # analyst choice: reporting threshold for radius stripes
REFERENCE_STRIPE_HEIGHT_M = 0.5e-6  # SPEC6 6.2 gauge_trend reference stripe
REFERENCE_STRIPE_WIDTH_M = 0.05     # SPEC6 6.7 50 mm reference stripe
ISOLATION_MARGIN_M = 0.1            # stripe isolated over [start - margin, end + margin]
ONSET_SEARCH_MAX_M = 50e-6
ONSET_ITERATIONS = 12               # geometric bisection: ~0.3 % on the onset height
RECOVERY_MIN_S = 600.0
RECORD_INTERVAL_S = 2.0
HISTORY_MAX_POINTS = 300
INITIAL_RATE_WINDOW_S = 5.0
DEFAULT_NUMERICS = {'axial_cell_m': 0.005, 'radial_cells': 16, 'time_step_s': 1.0}
DEFAULT_XI = 1.0
LITERATURE_BAND_LIFE_S = (20.0, 120.0)
POSITION_TOLERANCE_DEFAULT_M = 0.01
STRIP_POISSON_RATIO = ss.ALUMINIUM_NU
EDGE_OR_CENTRE_FRACTION = 0.15
FAMILY = 'lengthwise'

ROLL_KEYS = ('barrel_length_m', 'conductivity_w_mk', 'density_kg_m3', 'specific_heat_j_kgk',
             'expansion_coefficient_per_k', 'poisson_ratio', 'expansion_constraint')
HEADER_KEYS = ('nozzle_pitch_m', 'standoff_m', 'spray_angle_rad', 'offset_angle_rad',
               'spray_mean_htc_w_m2k', 'background_htc_w_m2k')
WIDTH_REQUIRED = ('roll', 'spray_header', 'coolant_temperature_k')
WIDTH_DEFAULTS = {
    'strip_centre_m': None, 'roll_heat_fraction_per_roll': None,
    'bite_heat_per_width_w_m': None, 'blocked_nozzle_indices': [], 'nozzle_levels': None,
    'events': [], 'numerics': None, 'rolls_carrying_stripe': 1,
    'shape_disturbing_coefficient': None, 'heredity_coefficient': None, 'gap_crown_m': None,
    'entry_crown_m': None, 'incoming_ridges': [], 'coil': None, 'previous_strip_widths_m': [],
    'grinding': None, 'cooling_zone_pitch_m': None, 'deflector_roll_radius_m': None,
    'lateral_compressive_stress_pa': None}
CONTINUITY = ('continuous', 'intermittent', 'both')
APPEARANCES = ('gloss_or_shade', 'loose_or_buckle', 'tight', 'stain', 'crease_or_flute')
OBS_V2_BOOL = ('positions_repeat_across_coils', 'positions_change_after_work_roll_change',
               'changes_with_coolant_zone_switching', 'visible_only_after_tension_release',
               'worse_toward_outer_wraps', 'changes_with_tension', 'follows_previous_strip_edges',
               'worse_at_higher_speed')
OBS_V2_KEYS = ('lengthwise_continuity', 'intermittent_duration_s', 'band_width_m',
               'band_spacing_m', 'appearance') + OBS_V2_BOOL


# ============================================================================= validation
def validate_observation_v2(ob):
    """Validate the v2 lengthwise observation fields (all nullable)."""
    out = {}
    c = ob['lengthwise_continuity']
    if c is not None and c not in CONTINUITY:
        raise ValueError(f'observation.lengthwise_continuity must be one of {CONTINUITY} or null')
    out['lengthwise_continuity'] = c
    a = ob['appearance']
    if a is not None and a not in APPEARANCES:
        raise ValueError(f'observation.appearance must be one of {APPEARANCES} or null')
    out['appearance'] = a
    out['intermittent_duration_s'] = opt_num('observation.intermittent_duration_s',
                                             ob['intermittent_duration_s'], positive=True)
    out['band_width_m'] = opt_num('observation.band_width_m', ob['band_width_m'], positive=True,
                                  hi=10.0)
    out['band_spacing_m'] = opt_num('observation.band_spacing_m', ob['band_spacing_m'],
                                    positive=True, hi=10.0)
    for k in OBS_V2_BOOL:
        if ob[k] is not None and not isinstance(ob[k], bool):
            raise ValueError(f'observation.{k} must be true, false or null')
        out[k] = ob[k]
    return out


def validate_width_model(w, pass_):
    if not isinstance(w, dict):
        raise ValueError('width_model must be a JSON object or null')
    keys('width_model', w, WIDTH_REQUIRED, tuple(WIDTH_DEFAULTS))
    out = dict(WIDTH_DEFAULTS)
    keys('width_model.roll', w['roll'], ROLL_KEYS)
    roll = {k: num(f'width_model.roll.{k}', w['roll'][k]) for k in ROLL_KEYS
            if k != 'expansion_constraint'}
    if w['roll']['expansion_constraint'] not in rt.EXPANSION_CONSTRAINTS:
        raise ValueError(f'width_model.roll.expansion_constraint must be one of '
                         f'{rt.EXPANSION_CONSTRAINTS}')
    roll['expansion_constraint'] = w['roll']['expansion_constraint']
    out['roll'] = roll
    keys('width_model.spray_header', w['spray_header'], HEADER_KEYS)
    out['spray_header'] = {k: num(f'width_model.spray_header.{k}', w['spray_header'][k])
                           for k in HEADER_KEYS}
    out['coolant_temperature_k'] = num('width_model.coolant_temperature_k',
                                       w['coolant_temperature_k'])
    for k in ('strip_centre_m', 'roll_heat_fraction_per_roll', 'bite_heat_per_width_w_m',
              'shape_disturbing_coefficient', 'heredity_coefficient', 'gap_crown_m',
              'entry_crown_m', 'cooling_zone_pitch_m', 'deflector_roll_radius_m',
              'lateral_compressive_stress_pa'):
        out[k] = opt_num(f'width_model.{k}', w.get(k))
    out['blocked_nozzle_indices'] = int_list('width_model.blocked_nozzle_indices',
                                             w.get('blocked_nozzle_indices', []))
    if w.get('nozzle_levels') is not None:
        out['nozzle_levels'] = num_list('width_model.nozzle_levels', w['nozzle_levels'],
                                        lo=0.0, hi=1.0)
    events = []
    for i, e in enumerate(_listv('width_model.events', w.get('events', []))):
        keys(f'width_model.events[{i}]', e, ('start_s', 'duration_s', 'nozzle_indices', 'level'))
        idx = int_list(f'width_model.events[{i}].nozzle_indices', e['nozzle_indices'])
        if not idx:
            raise ValueError(f'width_model.events[{i}].nozzle_indices must not be empty')
        events.append({'start_s': num(f'width_model.events[{i}].start_s', e['start_s'],
                                      nonnegative=True),
                       'duration_s': num(f'width_model.events[{i}].duration_s', e['duration_s'],
                                         positive=True, hi=1e5),
                       'nozzle_indices': idx,
                       'level': num(f'width_model.events[{i}].level', e['level'], lo=0.0,
                                    hi=1.0)})
    out['events'] = events
    if w.get('numerics') is not None:
        keys('width_model.numerics', w['numerics'], ('axial_cell_m', 'radial_cells',
                                                     'time_step_s'))
        n = w['numerics']
        rc = n['radial_cells']
        if isinstance(rc, bool) or not isinstance(rc, int) or not 3 <= rc <= 200:
            raise ValueError('width_model.numerics.radial_cells must be an int in [3, 200]')
        out['numerics'] = {'axial_cell_m': num('width_model.numerics.axial_cell_m',
                                               n['axial_cell_m'], positive=True),
                           'radial_cells': rc,
                           'time_step_s': num('width_model.numerics.time_step_s',
                                              n['time_step_s'], positive=True)}
    nr = w.get('rolls_carrying_stripe', 1)
    if nr not in (1, 2) or isinstance(nr, bool):
        raise ValueError('width_model.rolls_carrying_stripe must be 1 or 2')
    out['rolls_carrying_stripe'] = nr
    ridges = []
    for i, r in enumerate(_listv('width_model.incoming_ridges', w.get('incoming_ridges', []))):
        keys(f'width_model.incoming_ridges[{i}]', r, ('position_m', 'height_m', 'width_m'))
        ridges.append({'position_m': num(f'width_model.incoming_ridges[{i}].position_m',
                                         r['position_m'], nonnegative=True),
                       'height_m': num(f'width_model.incoming_ridges[{i}].height_m',
                                       r['height_m'], positive=True, hi=1e-3),
                       'width_m': num(f'width_model.incoming_ridges[{i}].width_m',
                                      r['width_m'], positive=True, hi=10.0)})
    out['incoming_ridges'] = ridges
    coil = w.get('coil')
    if coil is not None:
        keys('width_model.coil', coil, ('inner_radius_m', 'outer_radius_m',
                                        'winding_tension_pa', 'compaction_factor'))
        out['coil'] = {'inner_radius_m': num('width_model.coil.inner_radius_m',
                                             coil['inner_radius_m'], positive=True),
                       'outer_radius_m': num('width_model.coil.outer_radius_m',
                                             coil['outer_radius_m'], positive=True),
                       'winding_tension_pa': num('width_model.coil.winding_tension_pa',
                                                 coil['winding_tension_pa'], nonnegative=True),
                       'compaction_factor': opt_num('width_model.coil.compaction_factor',
                                                    coil['compaction_factor'], positive=True,
                                                    hi=1.0)}
        if out['coil']['outer_radius_m'] <= out['coil']['inner_radius_m']:
            raise ValueError('width_model.coil.outer_radius_m must exceed inner_radius_m')
    out['previous_strip_widths_m'] = num_list('width_model.previous_strip_widths_m',
                                              w.get('previous_strip_widths_m', []),
                                              positive=True)
    g = w.get('grinding')
    if g is not None:
        keys('width_model.grinding', g, ('traverse_speed_m_s', 'roll_rotation_hz'))
        out['grinding'] = {k: num(f'width_model.grinding.{k}', g[k], positive=True) for k in g}
    # physics-domain checks that need the module objects
    roll_obj = _roll(out, pass_['work_roll_radius_m'])
    header = _header(out)
    try:
        roll_obj.validate()
        header.validate()
        count = len(header.nozzle_positions(roll_obj.barrel_length_m))
    except ValueError as exc:
        raise ValueError(f'width_model: {exc}') from exc
    for i in out['blocked_nozzle_indices'] + [j for e in events for j in e['nozzle_indices']]:
        if i >= count:
            raise ValueError(f'width_model nozzle index {i} out of range (header has {count} '
                             'nozzles)')
    if out['nozzle_levels'] is not None and len(out['nozzle_levels']) != count:
        raise ValueError(f'width_model.nozzle_levels needs one level per nozzle ({count})')
    if out['rolls_carrying_stripe'] not in (1, 2):
        raise ValueError('width_model.rolls_carrying_stripe must be 1 or 2')
    return out


def _listv(where, value):
    if not isinstance(value, list):
        raise ValueError(f'{where} must be a list')
    return value


def _roll(w, radius):
    r = w['roll']
    return rt.RollThermalProperties(
        radius_m=radius, barrel_length_m=r['barrel_length_m'], density_kg_m3=r['density_kg_m3'],
        specific_heat_j_kgk=r['specific_heat_j_kgk'], conductivity_w_mk=r['conductivity_w_mk'],
        expansion_coefficient_per_k=r['expansion_coefficient_per_k'],
        poisson_ratio=r['poisson_ratio'])


def _header(w):
    h = w['spray_header']
    return rt.SprayHeader(nozzle_pitch_m=h['nozzle_pitch_m'], standoff_m=h['standoff_m'],
                          spray_angle_rad=h['spray_angle_rad'],
                          offset_angle_rad=h['offset_angle_rad'],
                          spray_mean_htc_w_m2k=h['spray_mean_htc_w_m2k'],
                          background_htc_w_m2k=h['background_htc_w_m2k'])


# ============================================================================= helpers
def _interp(xs, ys, x):
    return rt._interp(xs, ys, x)   # same linear interpolation as the thermal model


def _runs(z, values, threshold):
    """Contiguous same-sign runs with |value| > threshold (stripes of a difference profile)."""
    out, i, n = [], 0, len(z)
    while i < n:
        if abs(values[i]) <= threshold:
            i += 1
            continue
        sgn = values[i] > 0
        j = i
        while j + 1 < n and abs(values[j + 1]) > threshold and (values[j + 1] > 0) == sgn:
            j += 1
        k = max(range(i, j + 1), key=lambda m: abs(values[m]))
        half = abs(values[k]) / 2
        a = k
        while a > i and abs(values[a - 1]) >= half:
            a -= 1
        b = k
        while b < j and abs(values[b + 1]) >= half:
            b += 1
        start = (z[i - 1] + z[i]) / 2 if i > 0 else z[i]
        end = (z[j] + z[j + 1]) / 2 if j + 1 < n else z[j]
        out.append({'start_m': start, 'end_m': end, 'center_m': (start + end) / 2,
                    'width_m': end - start, 'peak_deviation_m': values[k],
                    'peak_position_m': z[k],
                    'width_at_half_peak_m': (z[b] - z[a]) + (z[1] - z[0]),
                    'sign': 'HOT_HIGH' if sgn else 'COLD_LOW'})
        i = j + 1
    return out


def _moving_average(z, values, window):
    """Centred moving average over exactly ``window`` metres (cells weighted by overlap)."""
    dz = z[1] - z[0]
    half = window / 2 / dz            # half-window in cells
    reach = int(math.ceil(half + 0.5))
    weights = [(k, max(0.0, min(k + 0.5, half) - max(k - 0.5, -half)))
               for k in range(-reach, reach + 1)]
    weights = [(k, wt) for k, wt in weights if wt > 0]
    n = len(values)
    out = []
    for i in range(n):
        acc = wsum = 0.0
        for k, wt in weights:
            j = i + k
            if 0 <= j < n:
                acc += wt * values[j]
                wsum += wt
        out.append(acc / wsum)
    return out


def _inside(z, centre, width):
    return [i for i, x in enumerate(z) if abs(x - centre) <= width / 2 * (1 + 1e-12)]


def shape_params(case, bite, w, src=None):
    """Pass parameters for the strip_shape chain (exit-tension feedback always on)."""
    p = case['pass']
    s = p if src is None else src
    width = p['width_m']
    centre = w['strip_centre_m'] if w['strip_centre_m'] is not None else \
        w['roll']['barrel_length_m'] / 2
    return {'exit_thickness_m': s['exit_thickness_m'],
            'entry_thickness_m': s['entry_thickness_m'],
            'strip_stiffness_per_width_pa': bite.strip_modulus_n_m / width,
            'bite_half_length_m': bite.contact_length_m / 2,
            'roll_radius_m': p['work_roll_radius_m'], 'strip_width_m': width,
            'mean_tension_pa': s['exit_tension_pa'], 'strip_centre_m': centre,
            'n_rolls': w['rolls_carrying_stripe'],
            'roll_youngs_modulus_pa': case['stand']['roll_youngs_modulus_pa'],
            'roll_poisson_ratio': case['stand']['roll_poisson_ratio'],
            'strip_youngs_modulus_pa': case['material']['youngs_modulus_pa'],
            'strip_poisson_ratio': STRIP_POISSON_RATIO,
            'xi': w['shape_disturbing_coefficient'] if w['shape_disturbing_coefficient']
            is not None else DEFAULT_XI,
            'yield_stress_pa': case['material']['yield_stress_pa'],
            'exit_tension_force_sensitivity_per_width_m': -bite.dforce_dexit_tension_m2 / width,
            'entry_force_sensitivity_per_width_pa': bite.dforce_dentry_thickness_n_m / width}


def _tsf(z, dev, sp, feedback=True):
    kw = {k: sp[k] for k in ('exit_thickness_m', 'strip_stiffness_per_width_pa',
                             'bite_half_length_m', 'roll_radius_m', 'strip_width_m',
                             'mean_tension_pa', 'strip_centre_m', 'n_rolls',
                             'roll_youngs_modulus_pa', 'roll_poisson_ratio',
                             'strip_youngs_modulus_pa', 'strip_poisson_ratio', 'xi',
                             'yield_stress_pa')}
    if feedback:
        kw['exit_tension_force_sensitivity_per_width_m'] = sp[
            'exit_tension_force_sensitivity_per_width_m']
    return ss.thermal_stripe_flatness(z, dev, **kw)


BAND_KEYS = ('start_m', 'end_m', 'center_m', 'width_m', 'peak_position_m', 'peak_i_units',
             'sense', 'state', 'band_buckling_stress_pa', 'local_total_stress_pa',
             'buckling_margin_pa', 'residual_stress_at_peak_pa')


def _bands(bands):
    out = []
    for b in bands:
        row = {k: b[k] for k in BAND_KEYS}
        if 'saturated' in b:
            row['saturated'] = b['saturated']
            row['linear_feedback_peak_i_units'] = b['linear_feedback_peak_i_units']
        out.append(row)
    return out


def shape_levels(z, dev, sp):
    """Rigid bound, compliance-only and exit-tension-feedback flatness of a radius profile."""
    fb = _tsf(z, dev, sp, True)
    co = _tsf(z, dev, sp, False)
    idx = _inside(z, sp['strip_centre_m'], sp['strip_width_m'])
    zs = [z[i] for i in idx]
    h = sp['exit_thickness_m']
    rigid_exit = [h - sp['n_rolls'] * dev[i] for i in idx]
    el = ss.differential_elongation(zs, [h] * len(zs), rigid_exit, xi=sp['xi'])
    rg = ss.flatness_from_elongation(
        zs, el['elongation'], youngs_modulus_pa=sp['strip_youngs_modulus_pa'],
        poisson_ratio=sp['strip_poisson_ratio'], thickness_m=h,
        mean_tension_pa=sp['mean_tension_pa'], yield_stress_pa=sp['yield_stress_pa'])
    peak_dr = max(fb['local_radius_deviation_m'], key=abs)
    peak_dh = fb['peak_local_thickness_change_m']
    return {
        'status': fb['status'], 'z_m': fb['z_m'],
        'local_radius_deviation_m': fb['local_radius_deviation_m'],
        'local_thickness_change_m': fb['local_thickness_change_m'],
        'i_units_with_feedback': fb['flatness']['i_units'],
        'i_units_compliance_only': co['flatness']['i_units'],
        'i_units_rigid': rg['i_units'],
        'rigid_transfer_bound_i_units': fb['rigid_transfer_bound_i_units'],
        'compliance_only_peak_i_units': fb['compliance_only_peak_i_units'],
        'feedback_peak_i_units': fb['feedback_peak_i_units'],
        'linear_feedback_peak_i_units': fb['linear_feedback_peak_i_units'],
        'peak_radius_deviation_m': peak_dr, 'peak_local_thickness_change_m': peak_dh,
        'peak_transfer_ratio_with_feedback': (peak_dh / (-sp['n_rolls'] * peak_dr)
                                              if peak_dr else None),
        'compliance_only_peak_transfer_ratio': (
            fb['compliance_only_peak_local_thickness_change_m'] / (-sp['n_rolls'] * peak_dr)
            if peak_dr else None),
        'effective_strip_stiffness_per_width_pa': fb['effective_strip_stiffness_per_width_pa'],
        'tension_feedback_stiffness_per_width_pa':
            fb['tension_feedback_stiffness_per_width_pa'],
        'exit_tension_force_sensitivity_per_width_m':
            fb['exit_tension_force_sensitivity_per_width_m'],
        'reporting_threshold_i_units': fb['flatness']['reporting_threshold_i_units'],
        'mean_tension_pa': sp['mean_tension_pa'],
        'levels': {
            'rigid': {'status': rg['status'], 'peak_abs_i_units':
                      max(abs(rg['max_i_units']), abs(rg['min_i_units'])),
                      'bands': _bands(rg['bands'])},
            'compliance_only': {'status': co['status'],
                                'peak_abs_i_units': co['compliance_only_peak_i_units'],
                                'bands': _bands(co['bands'])},
            'with_feedback': {'status': fb['status'],
                              'peak_abs_i_units': fb['feedback_peak_i_units'],
                              'bands': _bands(fb['bands']),
                              'saturated_bands': fb['saturated_bands']}},
        'flags': fb['flags']}


def _band_at(bands, x):
    hit = [b for b in bands if b['start_m'] <= x <= b['end_m']]
    return max(hit, key=lambda b: abs(b['peak_i_units'])) if hit else None


def stripe_states(levels, x):
    """Per level: the band containing position x (peak I-units and state) or below threshold."""
    out = {}
    for name in ('rigid', 'compliance_only', 'with_feedback'):
        b = _band_at(levels['levels'][name]['bands'], x)
        out[name] = ({'peak_i_units': b['peak_i_units'], 'state': b['state'],
                      'sense': b['sense'], 'band_width_m': b['width_m'],
                      'band_buckling_stress_pa': b['band_buckling_stress_pa'],
                      'local_total_stress_pa': b['local_total_stress_pa'],
                      'saturated': b.get('saturated', False)}
                     if b else {'peak_i_units': None, 'state': 'BELOW_REPORTING_THRESHOLD'})
    return out


def manifest_onset_scale(z, shape, sp, hi=None):
    """Smallest factor s with a MANIFEST band for s*shape (geometric bisection), or None."""
    peak = max(abs(v) for v in shape)
    if peak <= 0:
        return None
    s_hi = (ONSET_SEARCH_MAX_M if hi is None else hi) / peak

    def manifest(s):
        try:
            return _tsf(z, [s * v for v in shape], sp)['status'] == 'MANIFEST_BUCKLE_BANDS'
        except ValueError:
            return True        # thickness change exceeds the gauge: far beyond onset
    if not manifest(s_hi):
        return None
    s_lo = s_hi * 1e-4
    if manifest(s_lo):
        return s_lo
    for _ in range(ONSET_ITERATIONS):
        mid = math.sqrt(s_lo * s_hi)
        if manifest(mid):
            s_hi = mid
        else:
            s_lo = mid
    return s_hi


def _isolate(z, dev, stripe):
    a, b = stripe['start_m'] - ISOLATION_MARGIN_M, stripe['end_m'] + ISOLATION_MARGIN_M
    return [v if a <= x <= b else 0.0 for x, v in zip(z, dev)]


def _reference_stripe(z, centre):
    return [REFERENCE_STRIPE_HEIGHT_M if abs(x - centre) <= REFERENCE_STRIPE_WIDTH_M / 2 + 1e-12
            else 0.0 for x in z]


# ============================================================================= thermal
class _Thermal:
    def __init__(self, case, w, bite_heat, fraction):
        p = case['pass']
        self.w = w
        self.roll = _roll(w, p['work_roll_radius_m'])
        self.header = _header(w)
        self.length = self.roll.barrel_length_m
        self.positions = self.header.nozzle_positions(self.length)
        self.count = len(self.positions)
        self.centre = (w['strip_centre_m'] if w['strip_centre_m'] is not None
                       else self.length / 2)
        self.width = p['width_m']
        self.bite_heat, self.fraction = bite_heat, fraction
        num_ = dict(DEFAULT_NUMERICS, **(w['numerics'] or {}))
        self.numerics = num_
        self.kw = {'axial_cell_m': num_['axial_cell_m'], 'radial_cells': num_['radial_cells'],
                   'expansion_constraint': w['roll']['expansion_constraint']}
        base = list(w['nozzle_levels']) if w['nozzle_levels'] is not None else [1.0] * self.count
        for i in w['blocked_nozzle_indices']:
            base[i] = 0.0
        self.levels = base

    def segment(self, levels, duration=1.0):
        return rt.ThermalSegment(duration_s=duration, bite_heat_per_width_w_m=self.bite_heat,
                                 roll_heat_fraction_per_roll=self.fraction,
                                 strip_width_m=self.width, strip_centre_m=self.centre,
                                 coolant_temperature_k=self.w['coolant_temperature_k'],
                                 nozzle_levels=list(levels))

    def steady(self, levels):
        return rt.steady_state(self.roll, self.header, self.segment(levels), **self.kw)


def _steady_section(th, sp):
    healthy = th.steady([1.0] * th.count)
    actual = healthy if all(v == 1.0 for v in th.levels) else th.steady(th.levels)
    z = actual['z_m']
    dev = [a - b for a, b in zip(actual['radius_growth_m'], healthy['radius_growth_m'])]
    a0, a1 = th.centre - th.width / 2, th.centre + th.width / 2
    idx = _inside(z, th.centre, th.width)
    stripes = _runs([z[i] for i in idx], [dev[i] for i in idx], STRIPE_THRESHOLD_M)
    for s in stripes:
        j = min(range(th.count), key=lambda k: abs(th.positions[k] - s['peak_position_m']))
        s['nearest_nozzle_index'] = j
        s['nearest_nozzle_position_m'] = th.positions[j]
        s['nearest_nozzle_level'] = th.levels[j]
    # nozzle-pattern ripple of the healthy header over the strip interior
    pitch = th.header.nozzle_pitch_m
    ma = _moving_average(z, healthy['radius_growth_m'], pitch)
    ripple = [g - m if (a0 + pitch <= x <= a1 - pitch) else 0.0
              for x, g, m in zip(z, healthy['radius_growth_m'], ma)]
    inner = [r for x, r in zip(z, ripple) if a0 + pitch <= x <= a1 - pitch]
    out = {
        'status': actual['status'], 'z_m': z,
        'radius_growth_m': actual['radius_growth_m'],
        'healthy_radius_growth_m': healthy['radius_growth_m'],
        'local_deviation_m': dev, 'surface_temperature_k': actual['surface_temperature_k'],
        'healthy_surface_temperature_k': healthy['surface_temperature_k'],
        'htc_w_m2k': actual['htc_w_m2k'], 'heat_flux_w_m2': actual['heat_flux_w_m2'],
        'nozzle_positions_m': th.positions, 'nozzle_levels': th.levels,
        'blocked_nozzle_indices': list(th.w['blocked_nozzle_indices']),
        'effective_footprint_width_m': th.header.effective_footprint_width_m,
        'thermal_crown_m': actual['thermal_crown_m'],
        'healthy_thermal_crown_m': healthy['thermal_crown_m'],
        'strip_start_m': a0, 'strip_end_m': a1, 'strip_centre_m': th.centre,
        'max_surface_excess_temperature_k': max(actual['surface_temperature_k'])
        - th.w['coolant_temperature_k'],
        'stripe_threshold_m': STRIPE_THRESHOLD_M,
        'stripe_method': 'difference actual header - healthy header (same pass), thresholded '
                         'directly (no polynomial de-trend)',
        'stripes': stripes,
        'nozzle_pattern_ripple': {
            'window_m': pitch, 'peak_to_peak_m': (max(inner) - min(inner)) if inner else 0.0,
            'interior_start_m': a0 + pitch, 'interior_end_m': a1 - pitch,
            'profile_m': ripple},
        'solver': {k: actual['solver'][k] for k in ('converged', 'iterations',
                                                    'residual_temperature_equivalent_k')},
        'relative_energy_residual': actual['relative_energy_residual'],
        'expansion_factor': actual['expansion_factor'],
        'flags': actual['flags']}
    return out, healthy, actual, dev


def _event_levels(th, active):
    lv = list(th.levels)
    for e in active:
        for i in e['nozzle_indices']:
            lv[i] = e['level']
    return lv


def _events_section(th, sp, actual, events):
    """One transient from the steady state through all events (overlaps combined)."""
    t0 = min(e['start_s'] for e in events)
    marks = sorted({0.0} | {e['start_s'] - t0 for e in events}
                   | {e['start_s'] - t0 + e['duration_s'] for e in events})
    recovery = max(RECOVERY_MIN_S, 4 * max(e['duration_s'] for e in events))
    end = marks[-1] + recovery
    marks.append(end)
    segs = []
    for a, b in zip(marks, marks[1:]):
        if b - a <= 1e-9:
            continue
        active = [e for e in events if e['start_s'] - t0 <= a + 1e-9
                  and e['start_s'] - t0 + e['duration_s'] >= b - 1e-9]
        segs.append(th.segment(_event_levels(th, active), b - a))
    monitors = [sum(th.positions[i] for i in e['nozzle_indices']) / len(e['nozzle_indices'])
                for e in events]
    step = th.numerics['time_step_s']
    interval = max(RECORD_INTERVAL_S, step)
    n_rec = int(end / interval)
    records = [k * interval for k in range(n_rec + 1)]
    sim = rt.simulate(th.roll, th.header, segs, initial=actual, time_step_s=step,
                      record_times_s=records, monitor_positions_m=monitors, **th.kw)
    z = actual['z_m']
    base = actual['radius_growth_m']
    rows = []
    for k, (e, x, mon) in enumerate(zip(events, monitors, sim['monitors'])):
        ts = e['start_s'] - t0
        te = ts + e['duration_s']
        times = mon['time_s']
        g0 = _interp(z, base, x)
        dev = [g - g0 for g in mon['radius_growth_m']]
        # analytic initial growth rate from the change of the local cooling
        lv_after = _event_levels(th, [e])
        w_after = th.header.weight_profile(z, lv_after)
        hdr = th.header
        h_before = _interp(z, actual['htc_w_m2k'], x)
        h_after = hdr.background_htc_w_m2k + hdr.spray_mean_htc_w_m2k * _interp(z, w_after, x)
        t_s = _interp(z, actual['surface_temperature_k'], x)
        dq = (h_before - h_after) * (t_s - th.w['coolant_temperature_k'])
        roll = th.roll
        analytic = (2 * roll.expansion_coefficient_per_k * actual['expansion_factor'] * dq
                    / (roll.density_kg_m3 * roll.specific_heat_j_kgk))
        window = max(INITIAL_RATE_WINDOW_S,
                     2 * min(step, sim['solver']['internal_time_step_cap_s']))
        window = min(window, e['duration_s'])
        sim_rate = (_interp(times, dev, ts + window) - _interp(times, dev, ts)) / window
        sel = [i for i, t in enumerate(times) if t >= ts - 1e-9]
        met = rt.history_metrics([times[i] - ts for i in sel], [dev[i] for i in sel])
        t_peak = ts + met['time_of_peak_s']
        snap = min(sim['snapshots'], key=lambda s: (abs(s['time_s'] - t_peak), s['time_s']))
        prof = [g - b for g, b in zip(snap['radius_growth_m'], base)]
        # isolate this event's stripe: zero outside its nozzles' neighbourhood
        lo = min(th.positions[i] for i in e['nozzle_indices']) - ISOLATION_MARGIN_M
        hi = max(th.positions[i] for i in e['nozzle_indices']) + ISOLATION_MARGIN_M
        prof = [v if lo <= zz <= hi else 0.0 for zz, v in zip(z, prof)]
        at_mon = _interp(z, prof, x)
        k_pk = max(range(len(z)), key=lambda i: abs(prof[i]))
        row = {'index': k, 'start_s': e['start_s'], 'duration_s': e['duration_s'],
               'nozzle_indices': e['nozzle_indices'], 'level': e['level'],
               'nozzle_positions_m': [th.positions[i] for i in e['nozzle_indices']],
               'monitor_position_m': x,
               'local_htc_before_w_m2k': h_before, 'local_htc_during_w_m2k': h_after,
               'surface_excess_temperature_k': t_s - th.w['coolant_temperature_k'],
               'net_surface_flux_change_w_m2': dq,
               'analytic_initial_growth_rate_m_s': analytic,
               'simulated_initial_growth_rate_m_s': sim_rate,
               'initial_rate_window_s': window,
               'peak_deviation_m': met['peak_change'],
               'time_of_peak_s': met['time_of_peak_s'],
               'time_to_half_peak_s': met['time_to_half_peak_s'],
               'peak_snapshot_time_s': snap['time_s'] - ts,
               'stripe_peak_position_m': z[k_pk], 'stripe_peak_deviation_m': prof[k_pk]}
        try:
            shape = shape_levels(z, prof, sp)
            row['peak_shape'] = shape
            scale = manifest_onset_scale(z, prof, sp)
            row['manifest_threshold_m'] = None if scale is None else scale * at_mon
            pk_i = shape['linear_feedback_peak_i_units'] or 0.0
            thr_i = shape['reporting_threshold_i_units']
            # latent regime: the linear-feedback I-units scale with the stripe height
            row['reporting_threshold_m'] = (at_mon * thr_i / pk_i) if pk_i > 0 else None
            row['peak_state_with_feedback'] = _peak_state(shape, x)
            row['peak_stripe_states'] = stripe_states(shape, z[k_pk])
        except ValueError as exc:
            row['shape_error'] = str(exc)
            row['manifest_threshold_m'] = row['reporting_threshold_m'] = None
            row['peak_state_with_feedback'] = None
        sign = 1.0 if met['peak_change'] >= 0 else -1.0
        sdev = [sign * v for v in dev]
        for name in ('manifest', 'reporting'):
            thr = row[f'{name}_threshold_m']
            t_on = fade = None
            if thr is not None and thr * sign > 0:
                t_on = _first_cross(times, sdev, ts, abs(thr), up=True)
                if t_on is not None:
                    t_off = _first_cross(times, sdev, max(te, t_on), abs(thr), up=False)
                    fade = None if t_off is None else t_off - te
            row[f'time_to_{name}_threshold_s'] = None if t_on is None else t_on - ts
            row[f'fade_time_below_{name}_threshold_s'] = fade
        basis = ('manifest' if row['time_to_manifest_threshold_s'] is not None
                 else 'reporting' if row['time_to_reporting_threshold_s'] is not None else None)
        row['band_life_basis'] = basis
        fade = row[f'fade_time_below_{basis}_threshold_s'] if basis else None
        row['band_life_s'] = None if (basis is None or fade is None) else e['duration_s'] + fade
        row['time_above_manifest_threshold_s'] = (
            None if row['time_to_manifest_threshold_s'] is None
            or row['fade_time_below_manifest_threshold_s'] is None
            else e['duration_s'] - row['time_to_manifest_threshold_s']
            + row['fade_time_below_manifest_threshold_s'])
        row['band_life_lower_bound_s'] = None
        if basis and fade is None:
            row['flags'] = ['FADE_BEYOND_SIMULATED_RECOVERY']
            row['band_life_lower_bound_s'] = end - ts
        stride = max(1, int(math.ceil(len(sel) / HISTORY_MAX_POINTS)))
        keep = sel[::stride]
        if keep[-1] != sel[-1]:
            keep.append(sel[-1])
        row['history'] = {'time_s': [times[i] - ts for i in keep],
                          'radius_deviation_m': [dev[i] for i in keep]}
        rows.append(row)
    return {'status': sim['status'], 'events': rows, 'timeline_end_s': end,
            'recovery_s': recovery, 'time_origin_s': t0,
            'solver': {k: sim['solver'][k] for k in ('time_step_s', 'internal_time_step_cap_s',
                                                     'steps')},
            'relative_energy_residual': sim['relative_energy_residual'],
            'flags': sim['flags'],
            'growth_rate_note': ('Radius growth follows the radial heat integral, so right after '
                                 'a spray change the stripe grows at 2*alpha*factor*dq/(rho*c) '
                                 'whatever the radial distribution; short-lived bands arise '
                                 'because the stripe crosses the manifest threshold within '
                                 'seconds to tens of seconds and fades over about a minute '
                                 'after the zone returns, not because the roll skin responds '
                                 'fast.'),
            'open_discrepancy': ('The 20 s first-order flatness response identified on a plant '
                                 '(Dohmae & Okamura 2012) is faster than this model\'s decay; '
                                 'possible causes (none modelled): bite heat depending on the '
                                 'roll surface temperature, emulsion-level heat transfer, '
                                 'per-revolution effects.'),
            'band_life_definition': 'band_life_s = event duration + time after the event ends '
                                    'for the stripe to fall below the manifest threshold (or the '
                                    'reporting threshold when it never becomes manifest)'}


def _peak_state(shape, x):
    st = stripe_states(shape, x)['with_feedback']
    return st['state']


def _first_cross(times, values, after, thr, up):
    """First time >= after at which values reach thr (up: v >= thr; down: v < thr)."""
    def cond(v):
        return v >= thr if up else v < thr
    v0 = _interp(times, values, after)
    if cond(v0):
        return after
    prev_t, prev_v = after, v0
    for t, v in zip(times, values):
        if t <= after:
            continue
        if cond(v):
            if v == prev_v:
                return t
            return prev_t + (thr - prev_v) / (v - prev_v) * (t - prev_t)
        prev_t, prev_v = t, v
    return None


# ============================================================================= other parts
def _crown(case, w, healthy_crown):
    p = case['pass']
    h0, h1, width = p['entry_thickness_m'], p['exit_thickness_m'], p['width_m']
    win = ss.shohet_townsend_window(h1, width)
    out = {'shohet_townsend_window': {k: win[k] for k in (
        'upper_bound', 'lower_bound', 'upper_bound_i_units', 'lower_bound_i_units', 'beta',
        'thickness_to_width_ratio')},
        'half_width_i_units': (win['upper_bound_i_units'] - win['lower_bound_i_units']) / 2,
        'healthy_thermal_crown_m': healthy_crown, 'heredity': None, 'classification': None}
    if None in (w['gap_crown_m'], w['entry_crown_m'], w['heredity_coefficient']):
        out['heredity_status'] = ('NOT_SUPPLIED: gap_crown_m, entry_crown_m and '
                                  'heredity_coefficient are all needed')
        return out
    gap = w['gap_crown_m'] - 2 * healthy_crown
    her = ss.crown_heredity(gap, w['entry_crown_m'], h0, h1, w['heredity_coefficient'])
    cls = ss.classify_crown_change(w['entry_crown_m'], h0, her['exit_crown_m'], h1, width)
    out['heredity_status'] = 'EVALUATED'
    out['gap_crown_supplied_m'] = w['gap_crown_m']
    out['gap_crown_used_m'] = gap
    out['gap_crown_basis'] = ('supplied mechanical gap crown - 2 x healthy-header thermal crown '
                              '(both work rolls; the thermal crown closes the centre gap)')
    out['heredity'] = {k: her[k] for k in ('exit_crown_m', 'proportional_crown_m',
                                           'heredity_coefficient', 'entry_relative_crown',
                                           'exit_relative_crown', 'relative_crown_change',
                                           'relative_crown_change_i_units')}
    out['classification'] = {k: cls[k] for k in ('status', 'relative_crown_change',
                                                 'relative_crown_change_i_units',
                                                 'excess_beyond_window',
                                                 'excess_beyond_window_i_units')}
    return out


def _ridge(case, w, sp, ridge, z, coil):
    """Flatness effect of an incoming ridge in this pass and its coil build-up [D]."""
    h, big_h = sp['exit_thickness_m'], sp['entry_thickness_m']
    a = sp['bite_half_length_m']
    lam = min(max(2 * ridge['width_m'], ss.SHORT_WAVELENGTH_FACTOR * a), sp['roll_radius_m'])
    c = ss.roll_line_compliance_m2_n(lam, a, sp['roll_youngs_modulus_pa'],
                                     sp['roll_poisson_ratio'])
    nx, e, xi = (sp['exit_tension_force_sensitivity_per_width_m'],
                 sp['strip_youngs_modulus_pa'], sp['xi'])
    q_eff = sp['strip_stiffness_per_width_pa'] + nx * e * xi / h
    drive = sp['entry_force_sensitivity_per_width_pa'] + nx * e * xi / big_h
    ratio = 2 * c * drive / (1 + 2 * c * q_eff)          # dh/dH
    idx = _inside(z, sp['strip_centre_m'], sp['strip_width_m'])
    zs = [z[i] for i in idx]
    d_in = [ridge['height_m'] if abs(x - ridge['position_m']) <= ridge['width_m'] / 2 + 1e-12
            else 0.0 for x in zs]
    entry = [big_h + v for v in d_in]
    exit_ = [h + ratio * v for v in d_in]
    el = ss.differential_elongation(zs, entry, exit_, xi=xi)
    fl = ss.flatness_from_elongation(zs, el['elongation'], youngs_modulus_pa=e,
                                     poisson_ratio=sp['strip_poisson_ratio'], thickness_m=h,
                                     mean_tension_pa=sp['mean_tension_pa'],
                                     yield_stress_pa=sp['yield_stress_pa'])
    band = _band_at(fl['bands'], ridge['position_m'])
    out = {'position_m': ridge['position_m'], 'entry_ridge_height_m': ridge['height_m'],
           'ridge_width_m': ridge['width_m'], 'dominant_wavelength_m': lam,
           'roll_compliance_m2_n': c, 'exit_to_entry_ridge_ratio': ratio,
           'proportional_ratio_h_over_H': h / big_h,
           'exit_ridge_height_m': ratio * ridge['height_m'],
           'flatness_status': fl['status'],
           'peak_i_units': None if band is None else band['peak_i_units'],
           'state': 'BELOW_REPORTING_THRESHOLD' if band is None else band['state'],
           'flags': ['RIDGE_TRANSFER_DERIVED_IN_INTEGRATION_LAYER'],
           'coil': None}
    if coil is not None:
        cb = ss.coil_ridge_buildup(ratio * ridge['height_m'], h, coil['inner_radius_m'],
                                   coil['outer_radius_m'], case['material']['yield_stress_pa'],
                                   coil['winding_tension_pa'], e,
                                   coil['compaction_factor'] or ss.DEFAULT_COMPACTION_FACTOR)
        out['coil'] = {k: cb[k] for k in ('status', 'ridge_height_m', 'wraps_at_outer_radius',
                                          'radial_build_up_at_outer_radius_m',
                                          'hoop_strain_at_outer_radius', 'yield_margin_strain',
                                          'critical_ridge_height_at_outer_radius_m',
                                          'ridge_to_critical_ratio', 'yield_onset_radius_m',
                                          'affected_length_fraction', 'compaction_factor')}
    return out


def _troughs(case, w, obs):
    p, spans = case['pass'], case['spans']
    out = {}
    for name, h, length, tension in (
            ('entry_span', p['entry_thickness_m'], spans['entry_span_length_m'],
             p['entry_tension_pa']),
            ('exit_span', p['exit_thickness_m'], spans['exit_span_length_m'],
             p['exit_tension_pa'])):
        try:
            r = ss.tension_trough_screen(
                h, length, tension, p['width_m'], roller_radius_m=w['deflector_roll_radius_m'],
                lateral_compressive_stress_pa=w['lateral_compressive_stress_pa'],
                observed_spacing_m=obs['band_spacing_m'],
                youngs_modulus_pa=case['material']['youngs_modulus_pa'],
                poisson_ratio=STRIP_POISSON_RATIO)
            out[name] = {k: r[k] for k in (
                'status', 'thickness_m', 'span_length_m', 'tension_stress_pa',
                'wrinkle_wavelength_m', 'wrinkle_amplitude_m',
                'expected_trough_count_across_width', 'trough_critical_lateral_stress_pa',
                'roller_radius_m', 'roller_wrinkle_critical_lateral_stress_pa',
                'lateral_compressive_stress_pa', 'observed_spacing_to_wavelength_ratio',
                'observed_spacing_consistent', 'flags')}
        except ValueError as exc:
            out[name] = {'status': 'REJECTED', 'error': str(exc)}
    return out


def position_tolerance(obs, nozzle_pitch):
    if obs['band_width_m'] is not None:
        return obs['band_width_m'] / 2, 'half the observed band width'
    if nozzle_pitch is not None:
        return nozzle_pitch / 4, 'one quarter of the nozzle pitch'
    return POSITION_TOLERANCE_DEFAULT_M, '10 mm default (no band width or nozzle pitch)'


def observed_gaps(obs):
    pos = obs['band_positions_across_width_m']
    spacing = None
    if len(pos) >= 2 and len(set(pos)) >= 2:
        spacing = ss.spacing_analysis(pos)
    if obs['band_spacing_m'] is not None:
        return [obs['band_spacing_m']], spacing, 'observation.band_spacing_m'
    if spacing is not None:
        return spacing['gaps_m'], spacing, 'gaps between observed band positions'
    return None, spacing, None


def _positions(case, w, obs, steady, events, ridges, troughs, two_tone, grinding_pitch):
    pos = obs['band_positions_across_width_m']
    pitch = w['spray_header']['nozzle_pitch_m']
    tol, basis = position_tolerance(obs, pitch)
    th_pos = steady['nozzle_positions_m']
    low = [th_pos[i] for i, lv in enumerate(steady['nozzle_levels']) if lv < 1.0]
    predicted = {
        'steady_stripes': [s['peak_position_m'] for s in steady['stripes']],
        'blocked_or_low_level_nozzles': low,
        'event_nozzles': sorted({x for e in events for x in e['nozzle_positions_m']}),
        'event_stripe_peaks': [e['stripe_peak_position_m'] for e in events],
        'incoming_ridges': [r['position_m'] for r in ridges],
        'two_tone': list(two_tone['band_positions_m']) if two_tone else []}
    pitches = {'nozzle_pitch_m': pitch, 'cooling_zone_pitch_m': w['cooling_zone_pitch_m'],
               'grinding_feed_pitch_m': grinding_pitch,
               'trough_wavelength_entry_span_m': troughs['entry_span'].get('wrinkle_wavelength_m'),
               'trough_wavelength_exit_span_m': troughs['exit_span'].get('wrinkle_wavelength_m')}
    gaps, spacing, gap_basis = observed_gaps(obs)
    out = {'observed_positions_m': list(pos), 'tolerance_m': tol, 'tolerance_basis': basis,
           'predicted_positions_m': predicted, 'pitches_m': pitches,
           'spacing_analysis': None if spacing is None else
           {k: spacing[k] for k in ('status', 'positions_m', 'gaps_m', 'mean_gap_m',
                                    'coefficient_of_variation', 'regular')},
           'observed_gaps_m': gaps, 'observed_gaps_basis': gap_basis,
           'position_matches': {}, 'spacing_matches': {}}
    if pos:
        for name, pred in predicted.items():
            m = ss.match_positions(pred, pos, tol)
            out['position_matches'][name] = {
                'status': m['status'], 'unmatched_positions_m': m['unmatched_positions_m'],
                'matches': m['matches']}
    if gaps:
        for name, p in pitches.items():
            if p is None:
                continue
            m = ss.match_spacing(gaps, p)
            out['spacing_matches'][name] = {'status': m['status'], 'multiples': m['multiples'],
                                            'gaps': m['gaps']}
    return out


def _gauge_trend(case, w, get_bite, steady, sp_op, coil):
    th_z = steady['z_m'] if steady else None
    rows_src = case['schedule'] or [dict(case['pass'], label='case pass')]
    if steady and steady['stripes']:
        big = max(steady['stripes'], key=lambda s: abs(s['peak_deviation_m']))
        shape = _isolate(th_z, steady['local_deviation_m'], big)
        basis = (f'largest steady stripe (peak {big["peak_deviation_m"]:.3e} m at '
                 f'{big["peak_position_m"]:.4g} m), isolated; manifest onset by scaling its '
                 'own shape')
    else:
        shape = _reference_stripe(th_z, sp_op['strip_centre_m'])
        basis = (f'{REFERENCE_STRIPE_HEIGHT_M:g} m x {REFERENCE_STRIPE_WIDTH_M:g} m top-hat '
                 'reference stripe at the strip centre (no steady stripe)')
    peak_ref = max(shape, key=abs)
    peak_x = th_z[max(range(len(shape)), key=lambda i: abs(shape[i]))]
    ref50 = _reference_stripe(th_z, peak_x)
    rows = []
    for src in rows_src:
        row = {'label': src['label'], 'entry_thickness_m': src['entry_thickness_m'],
               'exit_thickness_m': src['exit_thickness_m'],
               'exit_tension_pa': src['exit_tension_pa'],
               'friction_coefficient': src['friction_coefficient'],
               'mean_flow_stress_pa': src['mean_flow_stress_pa']}
        try:
            bite = get_bite(src)
            sp = shape_params(case, bite, w, src)
            lv = shape_levels(th_z, shape, sp)
            st = stripe_states(lv, peak_x)['with_feedback']
            win = ss.shohet_townsend_window(src['exit_thickness_m'], case['pass']['width_m'])
            scale = manifest_onset_scale(th_z, shape, sp)
            scale50 = manifest_onset_scale(th_z, ref50, sp)
            row.update(
                bite_source=bite.source, bite_flags=list(bite.flags),
                strip_stiffness_per_width_pa=sp['strip_stiffness_per_width_pa'],
                tension_feedback_stiffness_per_width_pa=lv[
                    'tension_feedback_stiffness_per_width_pa'],
                bite_half_length_m=sp['bite_half_length_m'],
                transfer_factor_with_feedback=lv['peak_transfer_ratio_with_feedback'],
                transfer_factor_compliance_only=lv['compliance_only_peak_transfer_ratio'],
                rigid_i_units=lv['rigid_transfer_bound_i_units'],
                compliance_only_i_units=lv['compliance_only_peak_i_units'],
                feedback_i_units=lv['feedback_peak_i_units'],
                linear_feedback_i_units=lv['linear_feedback_peak_i_units'],
                saturated=bool(lv['levels']['with_feedback']['saturated_bands']),
                state=st['state'], band_buckling_stress_pa=st.get('band_buckling_stress_pa'),
                band_width_m=st.get('band_width_m'),
                shohet_townsend_half_width_i_units=(win['upper_bound_i_units']
                                                    - win['lower_bound_i_units']) / 2,
                shohet_townsend_upper_i_units=win['upper_bound_i_units'],
                shohet_townsend_lower_i_units=win['lower_bound_i_units'],
                manifest_onset_stripe_height_m=None if scale is None else scale * abs(peak_ref),
                manifest_onset_height_50mm_reference_m=(None if scale50 is None
                                                        else scale50 * REFERENCE_STRIPE_HEIGHT_M))
        except ValueError as exc:
            row['rejected'] = str(exc)
        h1 = src['exit_thickness_m']
        row['critical_ridge_height_m'] = None
        if coil is not None:
            try:
                cb = ss.coil_ridge_buildup(0.0, h1, coil['inner_radius_m'],
                                           coil['outer_radius_m'],
                                           case['material']['yield_stress_pa'],
                                           coil['winding_tension_pa'],
                                           case['material']['youngs_modulus_pa'],
                                           coil['compaction_factor']
                                           or ss.DEFAULT_COMPACTION_FACTOR)
                row['critical_ridge_height_m'] = cb['critical_ridge_height_at_outer_radius_m']
            except ValueError as exc:
                row['critical_ridge_error'] = str(exc)
        try:
            row['trough_critical_lateral_stress_pa'] = ss.trough_critical_lateral_stress_pa(
                h1, case['spans']['exit_span_length_m'], src['exit_tension_pa'],
                case['material']['youngs_modulus_pa'], STRIP_POISSON_RATIO)
        except ValueError as exc:
            row['trough_critical_lateral_stress_pa'] = None
            row['trough_error'] = str(exc)
        rows.append(row)
    return {'reference_stripe_peak_m': peak_ref, 'reference_stripe_position_m': peak_x,
            'reference_stripe_basis': basis,
            'onset_50mm_reference_basis': (f'{REFERENCE_STRIPE_WIDTH_M:g} m wide top-hat stripe '
                                           f'at {peak_x:.4g} m, height bisected'),
            'rows': rows, 'text': _trend_text(rows, peak_ref)}


def _trend_text(rows, peak):
    """Plain-words gauge trend, generated from the gauge_trend numbers."""
    ok = [r for r in rows if 'rejected' not in r]
    if len(ok) < 2:
        return ('Fewer than two assessable passes: no gauge trend statement.' if ok or not rows
                else 'No pass assessable.')
    a, b = ok[0], ok[-1]

    def um(x):
        return 'not reached below 50 um' if x is None else f'{x * 1e6:.3g} um'

    def mpa(x):
        return 'n/a' if x is None else f'{x / 1e6:.3g} MPa'
    la, lb = a['linear_feedback_i_units'], b['linear_feedback_i_units']
    ratio = lb / la if la else None
    if ratio is not None and ratio <= 1.5:
        lin = (f'nearly gauge independent ({la:.3g} -> {lb:.3g} I-units, x{ratio:.2f}, against '
               f'x{b["rigid_i_units"] / a["rigid_i_units"]:.2f} for the rigid bound)')
    else:
        lin = (f'{la:.3g} -> {lb:.3g} I-units (x{ratio:.2f}; rigid bound '
               f'x{b["rigid_i_units"] / a["rigid_i_units"]:.2f})' if ratio else 'not available')
    sat = [r['label'] for r in ok if r['saturated']]
    text = (f'Same {abs(peak) * 1e6:.3g} um roll stripe on every pass, '
            f'{a["exit_thickness_m"] * 1e3:.3g} mm -> {b["exit_thickness_m"] * 1e3:.3g} mm: '
            f'with the linear exit-tension feedback the I-units are {lin}. ')
    if sat:
        text += (f'The band is slack (MANIFEST, feedback saturated) on {len(sat)} of {len(ok)} '
                 f'passes, where the reported I-units ({a["feedback_i_units"]:.3g} -> '
                 f'{b["feedback_i_units"]:.3g}) rise toward the compliance-only values. ')
    text += ('The thin-gauge trend comes from the band buckling stress (proportional to '
             f'thickness squared: {mpa(a["band_buckling_stress_pa"])} -> '
             f'{mpa(b["band_buckling_stress_pa"])} for the reported band), the saturation of '
             'the feedback once a band goes slack, and the flatness dead band (half-width '
             f'{a["shohet_townsend_half_width_i_units"]:.3g} -> '
             f'{b["shohet_townsend_half_width_i_units"]:.3g} I-units). The stripe height at '
             'which the band first buckles under the pass tension is '
             f'{um(a["manifest_onset_height_50mm_reference_m"])} -> '
             f'{um(b["manifest_onset_height_50mm_reference_m"])} for a 50 mm stripe and '
             f'{um(a["manifest_onset_stripe_height_m"])} -> '
             f'{um(b["manifest_onset_stripe_height_m"])} for the model stripe shape.')
    sa, sb = a['manifest_onset_stripe_height_m'], b['manifest_onset_stripe_height_m']
    if sa and sb and sa / sb < 1.5:
        text += (' The broad thermal stripe gives a wide band whose buckling stress is small at '
                 'every gauge, so its onset is set mainly by the pass tension.')
    return text


# ============================================================================= section
def width_section(case, bite, get_bite, heat_row, trib, flags):
    """The ``width`` result section (SPEC6 6.2). ``get_bite(src)`` returns the bite of a
    schedule pass (effective values) or raises ValueError."""
    w = case.get('width_model')
    if w is None:
        return not_supplied('width_model is null or absent')
    if bite is None:
        return {'status': 'NOT_ASSESSABLE', 'not_supplied': False,
                'reason': 'no bite response for the case pass (needed for the strip '
                          'stiffness, contact length and exit-tension feedback)'}
    p = case['pass']
    out = {'status': 'SCREENING_RESULT_NOT_PLANT_VALIDATED', 'not_supplied': False,
           'failures': [], 'flags': [], 'limitations': [
               'Circumferentially averaged roll temperature; top-hat spray footprints.',
               'Shape chain: half-space roll compliance, linear exit-tension feedback with an '
               'approximate band-wise saturation, k = 4 narrow-band buckling (from memory).',
               'Stripe detection by differencing against a healthy-header solution; the '
               'stripe threshold is an analyst choice.',
               'Not plant-validated.']}
    if w['roll_heat_fraction_per_roll'] is not None:
        fraction, fbasis = w['roll_heat_fraction_per_roll'], 'supplied'
    else:
        fraction = (1 - trib['strip_heat_fraction']) / 2
        fbasis = '(1 - tribology.strip_heat_fraction)/2'
    if w['bite_heat_per_width_w_m'] is not None:
        heat, hbasis = w['bite_heat_per_width_w_m'], 'supplied'
    elif heat_row is not None and 'bite_heat_per_width_w_m' in heat_row:
        heat = heat_row['bite_heat_per_width_w_m']
        hbasis = 'computed: plastic work + interface slip dissipation of the pass (' + \
            heat_row['friction_power_basis'] + ')'
    else:
        return failed('width', 'bite heat per width not supplied and not computable')
    th = _Thermal(case, w, heat, fraction)
    sp = shape_params(case, bite, w)
    out['inputs_used'] = {
        'roll_heat_fraction_per_roll': fraction, 'roll_heat_fraction_basis': fbasis,
        'bite_heat_per_width_w_m': heat, 'bite_heat_basis': hbasis,
        'numerics': th.numerics, 'strip_centre_m': th.centre, 'strip_width_m': th.width,
        'n_rolls': sp['n_rolls'], 'xi': sp['xi'], 'mean_tension_pa': sp['mean_tension_pa'],
        'strip_stiffness_per_width_pa': sp['strip_stiffness_per_width_pa'],
        'bite_half_length_m': sp['bite_half_length_m'],
        'exit_tension_force_sensitivity_per_width_m':
            sp['exit_tension_force_sensitivity_per_width_m'],
        'exit_tension_feedback': 'always applied (SPEC6 6.7)'}
    steady = healthy = actual = None
    try:
        steady, healthy, actual, dev = _steady_section(th, sp)
        out['thermal_steady'] = steady
        out['flags'] += [f for f in steady['flags'] if f not in out['flags']]
    except ValueError as exc:
        out['thermal_steady'] = failed('thermal_steady', exc)
        out['failures'].append(out['thermal_steady']['error'])
    shape = {'steady': None, 'nozzle_pattern_ripple': None, 'crown': None, 'ridges': []}
    if steady is not None:
        try:
            lv = shape_levels(steady['z_m'], steady['local_deviation_m'], sp)
            shape['steady'] = lv
            shape['steady_stripe_table'] = [
                dict(position_m=s['peak_position_m'], peak_radius_deviation_m=s[
                    'peak_deviation_m'], stripe_width_m=s['width_m'],
                     width_at_half_peak_m=s['width_at_half_peak_m'],
                     **stripe_states(lv, s['peak_position_m']))
                for s in steady['stripes']]
            for s, row in zip(steady['stripes'], shape['steady_stripe_table']):
                scale = manifest_onset_scale(steady['z_m'], _isolate(
                    steady['z_m'], steady['local_deviation_m'], s), sp)
                row['manifest_onset_peak_height_m'] = (None if scale is None
                                                       else scale * abs(s['peak_deviation_m']))
        except ValueError as exc:
            shape['steady'] = failed('shape.steady', exc)
            out['failures'].append(shape['steady']['error'])
        try:
            rip = steady['nozzle_pattern_ripple']['profile_m']
            if max(abs(v) for v in rip) > 0:
                lv = shape_levels(steady['z_m'], rip, sp)
                shape['nozzle_pattern_ripple'] = {
                    k: lv[k] for k in ('status', 'rigid_transfer_bound_i_units',
                                       'compliance_only_peak_i_units', 'feedback_peak_i_units',
                                       'i_units_with_feedback')}
                shape['nozzle_pattern_ripple']['peak_to_peak_m'] = steady[
                    'nozzle_pattern_ripple']['peak_to_peak_m']
                shape['nozzle_pattern_ripple']['band_count_with_feedback'] = len(
                    lv['levels']['with_feedback']['bands'])
        except ValueError as exc:
            shape['nozzle_pattern_ripple'] = failed('shape.nozzle_pattern_ripple', exc)
        try:
            shape['crown'] = _crown(case, w, steady['healthy_thermal_crown_m'])
        except ValueError as exc:
            shape['crown'] = failed('shape.crown', exc)
            out['failures'].append(shape['crown']['error'])
    if w['events'] and actual is not None:
        try:
            out['thermal_events'] = _events_section(th, sp, actual, w['events'])
        except ValueError as exc:
            out['thermal_events'] = failed('thermal_events', exc)
            out['failures'].append(out['thermal_events']['error'])
    else:
        out['thermal_events'] = not_supplied('no width_model.events' if not w['events'] else
                                             'steady state not available')
    z = steady['z_m'] if steady else [(i + 0.5) * 0.005 for i in
                                      range(int(round(th.length / 0.005)))]
    for r in w['incoming_ridges']:
        try:
            shape['ridges'].append(_ridge(case, w, sp, r, z, w['coil']))
        except ValueError as exc:
            shape['ridges'].append({'position_m': r['position_m'], 'rejected': str(exc)})
    out['shape'] = shape
    out['troughs'] = _troughs(case, w, case['observation'])
    two_tone = (ss.two_tone_positions_m(w['previous_strip_widths_m'], th.centre, th.width)
                if w['previous_strip_widths_m'] else None)
    grinding_pitch = None
    if w['grinding'] is not None:
        try:
            grinding_pitch = ss.grinding_feed_pitch_m(w['grinding']['traverse_speed_m_s'],
                                                      w['grinding']['roll_rotation_hz'])
        except ValueError as exc:
            out['failures'].append(f'grinding: {exc}')
    out['two_tone'] = None if two_tone is None else {
        k: two_tone[k] for k in ('status', 'band_positions_m', 'edges')}
    out['grinding_feed_pitch_m'] = grinding_pitch
    events = out['thermal_events'].get('events', []) if isinstance(
        out['thermal_events'], dict) else []
    if steady is not None:
        try:
            out['positions'] = _positions(case, w, case['observation'], steady, events,
                                          w['incoming_ridges'], out['troughs'], two_tone,
                                          grinding_pitch)
        except ValueError as exc:
            out['positions'] = failed('positions', exc)
            out['failures'].append(out['positions']['error'])
        try:
            out['gauge_trend'] = _gauge_trend(case, w, get_bite, steady, sp, w['coil'])
        except ValueError as exc:
            out['gauge_trend'] = failed('gauge_trend', exc)
            out['failures'].append(out['gauge_trend']['error'])
    else:
        out['positions'] = out['gauge_trend'] = failed('width', 'no steady thermal solution')
    if out['failures']:
        flags.append('WIDTH_SECTION_PARTIAL_FAILURE')
    if steady and any(s['sign'] == 'HOT_HIGH' for s in steady['stripes']):
        flags.append('MODEL_STEADY_THERMAL_STRIPES_PRESENT')
    return out


# ============================================================================= hypotheses
def ev(criterion, observed, expected, verdict, weight=None, basis='observation'):
    """Evidence item (same structure as band_diagnosis._ev)."""
    if verdict not in ('SUPPORTS', 'CONTRADICTS', 'NEUTRAL', 'NOT_OBSERVED'):
        raise AssertionError(verdict)
    if verdict in ('SUPPORTS', 'CONTRADICTS'):
        if weight not in ('strong', 'moderate', 'weak'):
            raise AssertionError(weight)
    else:
        weight = None
    return {'criterion': criterion, 'observed': observed, 'expected': expected,
            'verdict': verdict, 'weight': weight, 'basis': basis}


def _rule(obs, key, criterion, expected, on_true=None, on_false=None):
    v = obs[key]
    if v is None:
        return ev(criterion, 'not observed', expected, 'NOT_OBSERVED')
    rule = on_true if v else on_false
    txt = 'true' if v else 'false'
    if rule is None:
        return ev(criterion, txt, expected, 'NEUTRAL')
    return ev(criterion, txt, expected, rule[0], rule[1])


def _choice(obs, key, criterion, expected, mapping):
    v = obs[key]
    if v is None:
        return ev(criterion, 'not observed', expected, 'NOT_OBSERVED')
    rule = mapping.get(v)
    if rule is None:
        return ev(criterion, v, expected, 'NEUTRAL')
    return ev(criterion, v, expected, rule[0], rule[1])


def _orientation(obs):
    o = obs['orientation']
    if o is None:
        return ev('orientation', 'not observed', 'longitudinal', 'NOT_OBSERVED')
    if o == 'longitudinal':
        return ev('orientation', o, 'longitudinal', 'SUPPORTS', 'moderate')
    return ev('orientation', o, 'longitudinal', 'CONTRADICTS', 'strong')


def _worse_thin(obs, weight, why):
    w = obs['worse_at_thinner_gauge']
    if w is None:
        return ev('worse at thinner gauge', 'not observed', 'true', 'NOT_OBSERVED')
    if w:
        return ev('worse at thinner gauge', 'true', f'true ({why})', 'SUPPORTS', weight)
    return ev('worse at thinner gauge', 'false', 'true', 'NEUTRAL')


def _fmt_pos(xs):
    return ', '.join(f'{x:.4g} m' for x in xs) if xs else 'none'


def _match_any(pred, pos, tol):
    if not pred or not pos:
        return []
    m = ss.match_positions(pred, pos, tol)
    return [r['observed_position_m'] for r in m['matches'] if r['matched']]


class Facts:
    """Model facts for the lengthwise rules, from the width section or the v1 coolant screen."""

    def __init__(self, case, width, screens, process):
        obs = case['observation']
        self.obs = obs
        self.positions = list(obs['band_positions_across_width_m'])
        w = case.get('width_model')
        self.width_ok = isinstance(width, dict) and not width.get('not_supplied', True) \
            and 'thermal_steady' in width and 'z_m' in width.get('thermal_steady', {})
        coolant = case['coolant']
        pitch = (w['spray_header']['nozzle_pitch_m'] if w is not None else
                 coolant['nozzle_pitch_m'] if coolant is not None else None)
        self.nozzle_pitch = pitch
        self.zone_pitch = w['cooling_zone_pitch_m'] if w is not None else None
        self.tol, self.tol_basis = position_tolerance(obs, pitch)
        self.gaps, self.spacing, self.gap_basis = observed_gaps(obs)
        self.header_known = False
        self.l1_predicted, self.l1_source = [], None
        self.steady_bands = []      # (position, with_feedback state) per steady stripe
        self.events = []
        self.event_positions = []
        self.two_tone = []
        self.ridges = []
        self.ridge_supplied = bool(w and w['incoming_ridges'])
        self.troughs = None
        self.crown_class = None
        self.feed_pitch = None
        self.grinding_supplied = bool(w and w['grinding'])
        if w is not None:
            p = case['pass']
            self.strip_centre = (w['strip_centre_m'] if w['strip_centre_m'] is not None
                                 else w['roll']['barrel_length_m'] / 2)
            self.strip_width = p['width_m']
        elif coolant is not None:
            self.strip_centre = coolant['barrel_length_m'] / 2
            self.strip_width = case['pass']['width_m']
        else:
            self.strip_centre = self.strip_width = None
        if self.width_ok:
            st = width['thermal_steady']
            self.header_known = True
            low = [st['nozzle_positions_m'][i] for i, lv in enumerate(st['nozzle_levels'])
                   if lv < 1.0]
            hot = [s['peak_position_m'] for s in st['stripes'] if s['sign'] == 'HOT_HIGH']
            self.l1_predicted = sorted(set(low + hot))
            self.l1_source = 'model steady stripes and blocked / low-level nozzles'
            table = (width['shape'] or {}).get('steady_stripe_table') or []
            self.steady_bands = [(r['position_m'], r['with_feedback']['state']) for r in table
                                 if r['peak_radius_deviation_m'] > 0]
            te = width.get('thermal_events') or {}
            self.events = te.get('events', []) if isinstance(te, dict) else []
            self.event_positions = sorted({x for e in self.events
                                           for x in e['nozzle_positions_m']
                                           + [e['stripe_peak_position_m']]})
            self.two_tone = (width.get('two_tone') or {}).get('band_positions_m', [])
            self.ridges = [r for r in (width['shape'] or {}).get('ridges', [])
                           if 'rejected' not in r]
            self.troughs = width.get('troughs')
            crown = (width['shape'] or {}).get('crown') or {}
            self.crown_class = ((crown.get('classification') or {}).get('status')
                                if isinstance(crown, dict) else None)
            self.feed_pitch = width.get('grinding_feed_pitch_m')
        elif screens is not None and screens.get('spray_coverage') is not None:
            self.header_known = True
            self.l1_predicted = [s['center_m'] for s in screens['band_risk_stripes'] or []]
            self.l1_source = 'phase-1 spray coverage band-risk stripes (no width model)'
        self.process = process

    def model_bands_at_positions(self):
        if not self.steady_bands:
            return []
        if self.positions:
            return [(x, s) for x, s in self.steady_bands
                    if any(abs(x - p) <= self.tol for p in self.positions)]
        return list(self.steady_bands)


def _tension_release_rules(facts, states, label):
    """SPEC6 6.7 rules: latent bands and tension release; manifest bands and loose appearance."""
    obs = facts.obs
    out = []
    crit = f'visible only after tension release vs {label}'
    v = obs['visible_only_after_tension_release']
    if not states:
        out.append(ev(crit, 'not observed' if v is None else str(v).lower(),
                      'LATENT model band', 'NOT_OBSERVED' if v is None else 'NEUTRAL'))
    elif v is None:
        out.append(ev(crit, 'not observed', 'LATENT model band', 'NOT_OBSERVED'))
    elif v and any(s == 'LATENT_UNDER_TENSION' for s in states):
        out.append(ev(crit, f'true; model {", ".join(states)}', 'LATENT model band',
                      'SUPPORTS', 'moderate'))
    elif not v and all(s == 'LATENT_UNDER_TENSION' for s in states):
        out.append(ev(crit, f'false; model only {", ".join(states)}', 'LATENT model band',
                      'CONTRADICTS', 'weak'))
    else:
        out.append(ev(crit, f'{str(v).lower()}; model {", ".join(states)}',
                      'LATENT model band', 'NEUTRAL'))
    crit2 = f'loose / buckle appearance vs MANIFEST {label}'
    a = obs['appearance']
    if a is None:
        out.append(ev(crit2, 'not observed', 'MANIFEST model band and loose_or_buckle',
                      'NOT_OBSERVED'))
    elif a == 'loose_or_buckle' and any(s == 'MANIFEST_BUCKLE' for s in states):
        out.append(ev(crit2, f'{a}; model MANIFEST', 'MANIFEST model band and loose_or_buckle',
                      'SUPPORTS', 'moderate'))
    else:
        out.append(ev(crit2, f'{a}; model {", ".join(states) or "no band"}',
                      'MANIFEST model band and loose_or_buckle', 'NEUTRAL'))
    return out


def _spacing_multiple(facts, pitch, criterion, weight, pitch_name):
    if facts.gaps is None:
        return ev(criterion, 'spacing not observed', f'integer multiple of the {pitch_name}',
                  'NOT_OBSERVED')
    if pitch is None:
        return ev(criterion, f'gaps {_fmt_pos(facts.gaps)}', f'{pitch_name} not known',
                  'NOT_OBSERVED', basis='input')
    m = ss.match_spacing(facts.gaps, pitch)
    obs_txt = f'gaps {_fmt_pos(facts.gaps)} ({facts.gap_basis}); {pitch_name} {pitch:.4g} m'
    if m['status'] == 'ALL_GAPS_MATCH':
        return ev(criterion, obs_txt + f'; multiples {m["multiples"]}',
                  f'integer multiple of the {pitch_name}', 'SUPPORTS', weight)
    return ev(criterion, obs_txt + f'; {m["status"]}', f'integer multiple of the {pitch_name}',
              'NEUTRAL')


def _h_nozzle(f):
    o = f.obs
    e = [_orientation(o)]
    crit = 'band positions vs model stripes / blocked or low-level nozzles'
    if not f.header_known:
        e.append(ev(crit, 'no width model or coolant header data', 'match', 'NOT_OBSERVED',
                    basis='input'))
    elif not f.positions:
        e.append(ev(crit, f'positions not observed (model: {_fmt_pos(f.l1_predicted)})',
                    'match', 'NOT_OBSERVED'))
    else:
        hits = _match_any(f.l1_predicted, f.positions, f.tol)
        if hits:
            e.append(ev(crit, f'observed {_fmt_pos(hits)} on model {_fmt_pos(f.l1_predicted)} '
                        f'({f.l1_source})', f'within {f.tol:.3g} m ({f.tol_basis})', 'SUPPORTS',
                        'strong'))
        else:
            e.append(ev(crit, f'no observed position near {_fmt_pos(f.l1_predicted)} '
                        f'({f.l1_source})', f'within {f.tol:.3g} m', 'CONTRADICTS', 'weak'))
    e.append(_choice(o, 'lengthwise_continuity', 'continuity', 'continuous',
                     {'continuous': ('SUPPORTS', 'moderate'), 'both': ('SUPPORTS', 'moderate'),
                      'intermittent': ('CONTRADICTS', 'weak')}))
    e.append(_rule(o, 'positions_repeat_across_coils', 'positions repeat across coils', 'true',
                   ('SUPPORTS', 'moderate'), ('CONTRADICTS', 'moderate')))
    e.append(_rule(o, 'positions_change_after_work_roll_change',
                   'positions change after work-roll change', 'false (same place)',
                   ('CONTRADICTS', 'moderate'), ('SUPPORTS', 'moderate')))
    e.append(_spacing_multiple(f, f.nozzle_pitch, 'spacing vs nozzle pitch', 'moderate',
                               'nozzle pitch'))
    e.append(_choice(o, 'appearance', 'appearance', 'loose_or_buckle',
                     {'loose_or_buckle': ('SUPPORTS', 'moderate'),
                      'stain': ('CONTRADICTS', 'weak'),
                      'crease_or_flute': ('CONTRADICTS', 'weak')}))
    bands = f.model_bands_at_positions()
    crit = 'model band at an observed position above the reporting threshold'
    if not f.width_ok:
        e.append(ev(crit, 'no width model', 'latent or manifest band', 'NOT_OBSERVED',
                    basis='input'))
    elif not f.positions:
        e.append(ev(crit, 'positions not observed', 'latent or manifest band', 'NOT_OBSERVED'))
    else:
        reported = [(x, s) for x, s in bands if s != 'BELOW_REPORTING_THRESHOLD']
        if reported:
            e.append(ev(crit, '; '.join(f'{x:.4g} m: {s}' for x, s in reported),
                        'latent or manifest band', 'SUPPORTS', 'moderate', 'model'))
        else:
            e.append(ev(crit, 'no model stripe band at the observed positions',
                        'latent or manifest band', 'NEUTRAL', basis='model'))
    states = [s for _, s in bands if s != 'BELOW_REPORTING_THRESHOLD']
    e += _tension_release_rules(f, states, 'steady model band')
    e.append(_worse_thin(o, 'weak', 'relative thickness error and buckling stress'))
    e.append(_choice(o, 'faces', 'faces', 'both', {'both': ('SUPPORTS', 'weak')}))
    pred = {'model_positions_m': f.l1_predicted, 'model_position_source': f.l1_source,
            'position_tolerance_m': f.tol, 'steady_model_bands': [
                {'position_m': x, 'state': s} for x, s in f.steady_bands]}
    return e, pred


def _h_zone(f):
    o = f.obs
    e = [_orientation(o)]
    e.append(_choice(o, 'lengthwise_continuity', 'continuity', 'intermittent or both',
                     {'intermittent': ('SUPPORTS', 'strong'), 'both': ('SUPPORTS', 'strong'),
                      'continuous': ('CONTRADICTS', 'moderate')}))
    e.append(_rule(o, 'changes_with_coolant_zone_switching', 'changes with coolant zone switching',
                   'true', ('SUPPORTS', 'strong'), ('CONTRADICTS', 'strong')))
    d = o['intermittent_duration_s']
    lives = [x['band_life_s'] for x in f.events if x.get('band_life_s')]
    bounds = [x['band_life_lower_bound_s'] for x in f.events
              if x.get('band_life_lower_bound_s') and not x.get('band_life_s')]
    crit = 'intermittent duration vs band life'
    if d is None:
        e.append(ev(crit, 'not observed', 'within 0.3-3 x band life', 'NOT_OBSERVED'))
    elif not lives and bounds:
        e.append(ev(crit, f'{d:.4g} s; model band life beyond the simulated recovery (> '
                    f'{", ".join(f"{b:.4g} s" for b in bounds)})',
                    'within 0.3-3 x model band life', 'NEUTRAL', basis='model'))
    elif lives:
        ok = [L for L in lives if 0.3 * L <= d <= 3 * L]
        e.append(ev(crit, f'{d:.4g} s; model band life {", ".join(f"{L:.4g} s" for L in lives)}',
                    'within 0.3-3 x model band life', 'SUPPORTS' if ok else 'NEUTRAL',
                    'moderate' if ok else None, 'model'))
    else:
        lo, hi = LITERATURE_BAND_LIFE_S
        ok = 0.3 * lo <= d <= 3 * hi
        e.append(ev(crit, f'{d:.4g} s; no model events (literature {lo:g}-{hi:g} s)',
                    f'within 0.3-3 x {lo:g}-{hi:g} s', 'SUPPORTS' if ok else 'NEUTRAL',
                    'weak' if ok else None))
    crit = 'band positions vs event nozzle positions'
    if not f.event_positions:
        e.append(ev(crit, 'no zone-switching events supplied', 'match', 'NOT_OBSERVED',
                    basis='input'))
    elif not f.positions:
        e.append(ev(crit, f'positions not observed (events at {_fmt_pos(f.event_positions)})',
                    'match', 'NOT_OBSERVED'))
    else:
        hits = _match_any(f.event_positions, f.positions, f.tol)
        e.append(ev(crit, f'observed {_fmt_pos(hits)} on events {_fmt_pos(f.event_positions)}'
                    if hits else f'no observed position near {_fmt_pos(f.event_positions)}',
                    f'within {f.tol:.3g} m', 'SUPPORTS' if hits else 'NEUTRAL',
                    'strong' if hits else None))
    pitch = f.zone_pitch if f.zone_pitch is not None else f.nozzle_pitch
    e.append(_spacing_multiple(f, pitch, 'spacing vs cooling-zone (or nozzle) pitch', 'weak',
                               'cooling-zone pitch' if f.zone_pitch is not None
                               else 'nozzle pitch'))
    e.append(_rule(o, 'positions_repeat_across_coils', 'positions repeat across coils',
                   'false (positions wander with the controller)', None, ('SUPPORTS', 'weak')))
    e.append(_choice(o, 'appearance', 'appearance', 'loose_or_buckle or tight',
                     {'loose_or_buckle': ('SUPPORTS', 'weak'), 'tight': ('SUPPORTS', 'weak')}))
    e.append(_worse_thin(o, 'weak', 'manifest threshold falls with gauge'))
    states = [x['peak_state_with_feedback'] for x in f.events
              if x.get('peak_state_with_feedback') not in (None, 'BELOW_REPORTING_THRESHOLD')]
    e += _tension_release_rules(f, states, 'event peak band')
    pred = {'event_positions_m': f.event_positions,
            'events': [{k: x.get(k) for k in ('index', 'monitor_position_m', 'peak_deviation_m',
                                              'time_to_manifest_threshold_s', 'band_life_s',
                                              'band_life_basis', 'peak_state_with_feedback')}
                       for x in f.events],
            'literature_band_life_s': list(LITERATURE_BAND_LIFE_S)}
    return e, pred


def _h_roll_surface(f):
    o = f.obs
    e = [_orientation(o)]
    ch, dis = o['positions_change_after_work_roll_change'], o['disappears_after_work_roll_change']
    crit = 'positions change / band disappears after work-roll change'
    if ch is not None:
        e.append(ev(crit, f'positions change: {str(ch).lower()}', 'true',
                    'SUPPORTS' if ch else 'CONTRADICTS', 'strong'))
    elif dis is not None:
        e.append(ev(crit, f'disappears after work-roll change: {str(dis).lower()}', 'true',
                    'SUPPORTS' if dis else 'CONTRADICTS', 'strong' if dis else 'moderate'))
    else:
        e.append(ev(crit, 'not observed', 'true', 'NOT_OBSERVED'))
    crit = 'follows previous strip edges / two-tone position'
    fe = o['follows_previous_strip_edges']
    hits = _match_any(f.two_tone, f.positions, f.tol)
    if fe or hits:
        why = []
        if fe:
            why.append('follows previous strip edges: true')
        if hits:
            why.append(f'observed {_fmt_pos(hits)} on two-tone {_fmt_pos(f.two_tone)}')
        e.append(ev(crit, '; '.join(why), 'true or on a two-tone position', 'SUPPORTS',
                    'strong'))
    elif fe is None and not (f.two_tone and f.positions):
        e.append(ev(crit, 'not observed', 'true or on a two-tone position', 'NOT_OBSERVED'))
    else:
        e.append(ev(crit, f'follows previous edges: {fe}; two-tone {_fmt_pos(f.two_tone)}',
                    'true or on a two-tone position', 'NEUTRAL'))
    e.append(_rule(o, 'positions_repeat_across_coils', 'positions repeat across coils', 'true',
                   ('SUPPORTS', 'moderate'), None))
    e.append(_choice(o, 'lengthwise_continuity', 'continuity', 'continuous',
                     {'continuous': ('SUPPORTS', 'moderate'),
                      'intermittent': ('CONTRADICTS', 'moderate')}))
    e.append(_choice(o, 'appearance', 'appearance', 'gloss_or_shade',
                     {'gloss_or_shade': ('SUPPORTS', 'moderate'),
                      'loose_or_buckle': ('CONTRADICTS', 'weak')}))
    e.append(_choice(o, 'faces', 'faces', 'one', {'one': ('SUPPORTS', 'moderate')}))
    e.append(_rule(o, 'changes_with_coolant_zone_switching', 'changes with coolant zone switching',
                   'false', ('CONTRADICTS', 'moderate'), None))
    return e, {'two_tone_positions_m': f.two_tone,
               'note': 'settle by roll inspection and a work-roll change test'}


def _h_grinding(f):
    o = f.obs
    e = [_orientation(o)]
    crit = 'spacing vs grinding feed pitch (1-3 x, within 10 %)'
    p = f.feed_pitch
    if not f.grinding_supplied or p is None:
        e.append(ev(crit, 'no grinding data', 'match', 'NOT_OBSERVED', basis='input'))
    elif f.gaps is None:
        e.append(ev(crit, f'spacing not observed (feed pitch {p * 1e3:.4g} mm)', 'match',
                    'NOT_OBSERVED'))
    else:
        notes, ok = [], True
        for g in f.gaps:
            m = min(3, max(1, round(g / p)))
            dev = g / (m * p) - 1
            notes.append(f'{g * 1e3:.4g} mm = {m} x pitch {dev:+.1%}')
            ok = ok and abs(dev) <= 0.10
        e.append(ev(crit, '; '.join(notes) + f' (feed pitch {p * 1e3:.4g} mm)',
                    'every gap within 10 % of 1-3 x feed pitch', 'SUPPORTS' if ok else
                    'CONTRADICTS', 'strong' if ok else 'moderate'))
    crit = 'regular fine spacing (CV < 0.15, spacing < 30 mm)'
    sp = f.spacing
    if sp is None or len(sp['gaps_m']) < 2:
        e.append(ev(crit, 'fewer than three observed positions', 'regular and < 30 mm',
                    'NOT_OBSERVED'))
    else:
        spacing = o['band_spacing_m'] if o['band_spacing_m'] is not None else sp['mean_gap_m']
        ok = sp['coefficient_of_variation'] < 0.15 and spacing < 0.030
        e.append(ev(crit, f'CV {sp["coefficient_of_variation"]:.3f}, spacing '
                    f'{spacing * 1e3:.4g} mm', 'regular and < 30 mm',
                    'SUPPORTS' if ok else 'NEUTRAL', 'weak' if ok else None))
    e.append(_rule(o, 'positions_change_after_work_roll_change',
                   'positions change after work-roll change', 'true',
                   ('SUPPORTS', 'moderate'), ('CONTRADICTS', 'strong')))
    e.append(_choice(o, 'appearance', 'appearance', 'gloss_or_shade',
                     {'gloss_or_shade': ('SUPPORTS', 'moderate')}))
    e.append(_choice(o, 'lengthwise_continuity', 'continuity', 'continuous',
                     {'continuous': ('SUPPORTS', 'weak')}))
    return e, {'grinding_feed_pitch_m': p}


def _h_ridge(f):
    o = f.obs
    e = [_orientation(o)]
    e.append(_rule(o, 'positions_repeat_across_coils', 'positions repeat across coils',
                   'false (fixed to the mother coil, not the mill)', ('CONTRADICTS', 'moderate'),
                   ('SUPPORTS', 'moderate')))
    e.append(_rule(o, 'positions_change_after_work_roll_change',
                   'positions change after work-roll change', 'false',
                   ('CONTRADICTS', 'weak'), None))
    e.append(_rule(o, 'worse_toward_outer_wraps', 'worse toward outer wraps', 'true',
                   ('SUPPORTS', 'strong'), ('CONTRADICTS', 'moderate')))
    crit = 'band positions vs supplied incoming ridges'
    rpos = [r['position_m'] for r in f.ridges]
    if not f.ridge_supplied:
        e.append(ev(crit, 'no incoming ridges supplied', 'match', 'NOT_OBSERVED', basis='input'))
    elif not f.positions:
        e.append(ev(crit, f'positions not observed (ridges at {_fmt_pos(rpos)})', 'match',
                    'NOT_OBSERVED'))
    else:
        hits = _match_any(rpos, f.positions, f.tol)
        e.append(ev(crit, f'observed {_fmt_pos(hits)} on ridges {_fmt_pos(rpos)}' if hits
                    else f'no observed position near {_fmt_pos(rpos)}', f'within {f.tol:.3g} m',
                    'SUPPORTS' if hits else 'NEUTRAL', 'strong' if hits else None))
    coils = [r['coil'] for r in f.ridges if r.get('coil')]
    crit = 'model coil build-up of a supplied ridge'
    if not coils:
        e.append(ev(crit, 'no ridge with coil data', 'RIDGE_YIELDS_STRIP', 'NOT_OBSERVED',
                    basis='input'))
    elif any(c['status'] == 'RIDGE_YIELDS_STRIP' for c in coils):
        e.append(ev(crit, ', '.join(c['status'] for c in coils), 'RIDGE_YIELDS_STRIP',
                    'SUPPORTS', 'moderate', 'model'))
    else:
        e.append(ev(crit, ', '.join(c['status'] for c in coils), 'RIDGE_YIELDS_STRIP',
                    'CONTRADICTS', 'weak', 'model'))
    crit = 'intermittent band with partial affected coil length'
    c = o['lengthwise_continuity']
    fr = [x['affected_length_fraction'] for x in coils]
    if c is None:
        e.append(ev(crit, 'continuity not observed', 'both/intermittent, fraction 0.05-0.95',
                    'NOT_OBSERVED'))
    elif c in ('both', 'intermittent') and any(0.05 <= x <= 0.95 for x in fr):
        e.append(ev(crit, f'{c}; affected length fraction {", ".join(f"{x:.3g}" for x in fr)}',
                    'both/intermittent, fraction 0.05-0.95', 'SUPPORTS', 'weak'))
    else:
        e.append(ev(crit, f'{c}; fractions {fr}', 'both/intermittent, fraction 0.05-0.95',
                    'NEUTRAL'))
    e.append(_worse_thin(o, 'moderate', 'critical ridge height scales with gauge'))
    e.append(_rule(o, 'visible_only_after_tension_release', 'visible only after tension release',
                   'true', ('SUPPORTS', 'weak'), None))
    return e, {'ridges': [{k: r.get(k) for k in ('position_m', 'exit_ridge_height_m', 'state')}
                          | {'coil_status': (r.get('coil') or {}).get('status')}
                          for r in f.ridges]}


def _h_troughs(f):
    o = f.obs
    e = [_orientation(o)]
    crit = 'spacing vs trough wavelength'
    tr = f.troughs or {}
    lams = [(n, tr[n]['wrinkle_wavelength_m']) for n in ('entry_span', 'exit_span')
            if isinstance(tr.get(n), dict) and tr[n].get('wrinkle_wavelength_m')]
    if not lams:
        e.append(ev(crit, 'no trough model', '0.5-2 x wavelength', 'NOT_OBSERVED',
                    basis='input'))
    elif f.gaps is None:
        e.append(ev(crit, 'spacing not observed', '0.5-2 x wavelength', 'NOT_OBSERVED'))
    else:
        s = o['band_spacing_m'] if o['band_spacing_m'] is not None else \
            sum(f.gaps) / len(f.gaps)
        ratios = [(n, s / lam) for n, lam in lams]
        txt = f'spacing {s * 1e3:.4g} mm; ' + ', '.join(f'{n}: {r:.3g} x wavelength'
                                                        for n, r in ratios)
        if any(0.5 <= r <= 2 for _, r in ratios):
            e.append(ev(crit, txt, '0.5-2 x wavelength (either span)', 'SUPPORTS', 'strong'))
        elif all(r < 0.25 or r > 4 for _, r in ratios):
            e.append(ev(crit, txt, '0.5-2 x wavelength (outside a factor 4 contradicts)',
                        'CONTRADICTS', 'moderate'))
        else:
            e.append(ev(crit, txt, '0.5-2 x wavelength', 'NEUTRAL'))
    e.append(_choice(o, 'appearance', 'appearance', 'crease_or_flute',
                     {'crease_or_flute': ('SUPPORTS', 'strong'),
                      'stain': ('CONTRADICTS', 'moderate')}))
    e.append(_rule(o, 'changes_with_tension', 'changes with tension', 'true',
                   ('SUPPORTS', 'strong'), ('CONTRADICTS', 'strong')))
    crit = 'model trough status (either span)'
    sts = [tr[n]['status'] for n in ('entry_span', 'exit_span') if isinstance(tr.get(n), dict)]
    valid = [s for s in sts if s != 'REJECTED']
    if any(s in ('TROUGHS_EXPECTED', 'ROLLER_WRINKLE_EXPECTED') for s in valid):
        e.append(ev(crit, ', '.join(sts), 'TROUGHS_EXPECTED', 'SUPPORTS', 'moderate', 'model'))
    elif valid and all(s == 'BELOW_TROUGH_THRESHOLD' for s in valid):
        e.append(ev(crit, ', '.join(sts), 'TROUGHS_EXPECTED', 'CONTRADICTS', 'weak', 'model'))
    else:
        e.append(ev(crit, ', '.join(sts) or 'no trough model',
                    'TROUGHS_EXPECTED (needs lateral_compressive_stress_pa)', 'NOT_OBSERVED',
                    basis='input'))
    e.append(_choice(o, 'lengthwise_continuity', 'continuity', 'intermittent or both',
                     {'intermittent': ('SUPPORTS', 'weak'), 'both': ('SUPPORTS', 'weak')}))
    e.append(_worse_thin(o, 'moderate', 'trough threshold proportional to gauge'))
    e.append(_rule(o, 'positions_change_after_work_roll_change',
                   'positions change after work-roll change', 'false',
                   ('CONTRADICTS', 'weak'), None))
    return e, {'trough_wavelengths_m': {n: lam for n, lam in lams}, 'trough_status': sts}


def _h_profile(f):
    o = f.obs
    e = [_orientation(o)]
    crit = 'crown change vs Shohet-Townsend dead band'
    if f.crown_class is None:
        e.append(ev(crit, 'entry / gap crowns or heredity coefficient not supplied',
                    'outside the dead band', 'NOT_OBSERVED', basis='input'))
    elif f.crown_class == 'WITHIN_DEAD_BAND':
        e.append(ev(crit, f.crown_class, 'outside the dead band', 'CONTRADICTS', 'moderate',
                    'model'))
    else:
        e.append(ev(crit, f.crown_class, 'outside the dead band', 'SUPPORTS', 'strong', 'model'))
    crit = 'band positions: edges or centre vs spread across the width'
    pos = f.positions
    if not pos:
        e.append(ev(crit, 'positions not observed', 'all near the edges or all near the centre',
                    'NOT_OBSERVED'))
    elif f.strip_centre is None:
        e.append(ev(crit, 'strip position on the barrel unknown', 'edges or centre',
                    'NOT_OBSERVED', basis='input'))
    else:
        c, wd = f.strip_centre, f.strip_width
        lim = EDGE_OR_CENTRE_FRACTION * wd
        edge = [x for x in pos if wd / 2 - abs(x - c) <= lim]
        centre = [x for x in pos if abs(x - c) <= lim]
        interior = [x for x in pos if x not in edge and x not in centre]
        if len(edge) == len(pos) or len(centre) == len(pos):
            e.append(ev(crit, f'{_fmt_pos(pos)} (strip {c - wd / 2:.4g}-{c + wd / 2:.4g} m)',
                        'all within 15 % of the width of an edge or of the centre', 'SUPPORTS',
                        'moderate'))
        elif len(interior) >= 2:
            e.append(ev(crit, f'{len(interior)} interior positions {_fmt_pos(interior)}',
                        'all near edges or centre', 'CONTRADICTS', 'moderate'))
        else:
            e.append(ev(crit, _fmt_pos(pos), 'all near edges or centre', 'NEUTRAL'))
    bw = o['band_width_m']
    crit = 'band width'
    if bw is None:
        e.append(ev(crit, 'not observed', '> 150 mm', 'NOT_OBSERVED'))
    elif bw > 0.150:
        e.append(ev(crit, f'{bw * 1e3:.4g} mm', '> 150 mm', 'SUPPORTS', 'weak'))
    elif bw < 0.060:
        e.append(ev(crit, f'{bw * 1e3:.4g} mm', '> 150 mm (< 60 mm contradicts)',
                    'CONTRADICTS', 'weak'))
    else:
        e.append(ev(crit, f'{bw * 1e3:.4g} mm', '> 150 mm', 'NEUTRAL'))
    e.append(_choice(o, 'appearance', 'appearance', 'loose_or_buckle',
                     {'loose_or_buckle': ('SUPPORTS', 'moderate')}))
    e.append(_rule(o, 'visible_only_after_tension_release', 'visible only after tension release',
                   'true', ('SUPPORTS', 'weak'), None))
    e.append(_worse_thin(o, 'moderate', 'dead band shrinks as (h/w)^1.86'))
    return e, {'crown_classification': f.crown_class}


def _h_heat_streak(f):
    o = f.obs
    e = [_orientation(o)]
    e.append(_choice(o, 'appearance', 'appearance', 'gloss_or_shade',
                     {'gloss_or_shade': ('SUPPORTS', 'moderate'),
                      'crease_or_flute': ('CONTRADICTS', 'moderate')}))
    e.append(_rule(o, 'gauge_variation_detected', 'gauge variation', 'not detected', None,
                   ('SUPPORTS', 'weak')))
    e.append(_rule(o, 'positions_repeat_across_coils', 'positions repeat across coils', 'false',
                   ('CONTRADICTS', 'weak'), ('SUPPORTS', 'moderate')))
    e.append(_choice(o, 'lengthwise_continuity', 'continuity', 'intermittent or both',
                     {'intermittent': ('SUPPORTS', 'moderate'), 'both': ('SUPPORTS', 'moderate')}))
    e.append(_rule(o, 'worse_at_higher_speed', 'worse at higher speed', 'true',
                   ('SUPPORTS', 'moderate'), None))
    crit = 'tribology regime / exit strip temperature at the operating point'
    pr = f.process or {}
    fr = pr.get('friction') if isinstance(pr, dict) else None
    ht = pr.get('heating') if isinstance(pr, dict) else None
    regime = (fr or {}).get('operating', {}).get('regime') if isinstance(fr, dict) else None
    hot = None
    if isinstance(ht, dict) and isinstance(ht.get('operating'), dict):
        op = ht['operating']
        if op.get('temperature_limit_k') is not None and 'exit_temperature_k' in op:
            hot = op['exit_temperature_k'] > op['temperature_limit_k']
    if regime is None and hot is None:
        e.append(ev(crit, 'no tribology', 'BOUNDARY or above the temperature limit',
                    'NOT_OBSERVED', basis='input'))
    elif regime == 'BOUNDARY' or hot:
        e.append(ev(crit, f'regime {regime}; exit temperature above limit: {hot}',
                    'BOUNDARY or above the temperature limit', 'SUPPORTS', 'weak', 'model'))
    else:
        e.append(ev(crit, f'regime {regime}; exit temperature above limit: {hot}',
                    'BOUNDARY or above the temperature limit', 'NEUTRAL', basis='model'))
    e.append(_rule(o, 'positions_change_after_work_roll_change',
                   'positions change after work-roll change', 'false',
                   ('CONTRADICTS', 'weak'), None))
    return e, {'regime_at_operating_point': regime, 'exit_temperature_above_limit': hot}


def _h_stain(f):
    o = f.obs
    e = [_orientation(o)]
    e.append(_choice(o, 'appearance', 'appearance', 'stain',
                     {'stain': ('SUPPORTS', 'strong'),
                      'loose_or_buckle': ('CONTRADICTS', 'moderate'),
                      'crease_or_flute': ('CONTRADICTS', 'moderate')}))
    e.append(_choice(o, 'faces', 'faces', 'one', {'one': ('SUPPORTS', 'moderate')}))
    e.append(_choice(o, 'lengthwise_continuity', 'continuity', 'intermittent',
                     {'intermittent': ('SUPPORTS', 'weak')}))
    e.append(_rule(o, 'positions_repeat_across_coils', 'positions repeat across coils', 'true',
                   ('SUPPORTS', 'weak'), None))
    e.append(_rule(o, 'changes_with_tension', 'changes with tension', 'false',
                   ('CONTRADICTS', 'weak'), None))
    return e, {'note': 'no model quantity; settle by annealing a sample and checking wipers'}


LENGTHWISE_HYPOTHESES = (
    ('nozzle_thermal_stripe', 'Nozzle thermal stripe (blocked / partly blocked / mis-aimed)',
     'A blocked, partly blocked or mis-aimed nozzle leaves an under-cooled stripe; the work '
     'roll grows locally and over-rolls the strip there, giving a loose band (latent under '
     'tension, manifest once it buckles).',
     'Spray footprint check (pattern paper or water test) and header inspection; compare the '
     'band positions on three consecutive coils with the nozzle positions on the barrel '
     'coordinate; shapemeter zone map.',
     ('clear or replace the blocked nozzle', 'check header pressure and filtration',
      'adjust spray overlap / offset angle')),
    ('cooling_zone_switching_transient', 'Cooling-zone switching transient',
     'Selective zone cooling (flatness control valves) or an intermittently blocking nozzle '
     'switches a zone off and on; each switch grows a thermal stripe for tens of seconds and '
     'it fades over about a minute after the zone returns: short-lived bands.',
     'Log the coolant valve states against the shapemeter zones and the band appearance '
     'times; compare the band duration with the valve-off intervals.',
     ('retune the flatness controller (zone dead band, rate limits)', 'check valve hysteresis '
      'and intermittent nozzle blockage', 'review the zone-to-nozzle mapping')),
    ('roll_surface_band', 'Roll-surface band (wear band, pick-up streak, two-tone step)',
     'A wear band, roll-coating (pick-up) streak, or a two-tone step at the edges of '
     'previously rolled narrower strip prints a band at a fixed width position until the '
     'work rolls are changed.',
     'Inspect the work-roll surface at the band positions; work-roll change test; compare the '
     'positions with the edges of earlier narrower widths.',
     ('change / regrind the work rolls', 'schedule wide-to-narrow', 'check roll coating')),
    ('grinding_feed_marks', 'Grinding feed marks',
     'Helical feed lines from the roll grinder; the lateral pitch is the traverse per roll '
     'revolution.',
     'Measure the band spacing and compare with the grinder traverse per revolution; inspect '
     'the roll surface; roll-change test.',
     ('change the grinding traverse / spark-out', 'regrind the work rolls')),
    ('incoming_ridge_coil_buildup', 'Incoming ridge, coil build-up',
     'A local high spot in the incoming profile stacks up wrap by wrap in the coil, stretches '
     'the band beyond yield, and leaves a tight-then-loose band, worse toward the outer wraps.',
     'Entry profile scan of the incoming coil and an outside-profile scan of the wound coil; '
     'check whether the band is worse toward the outer wraps and follows the mother coil.',
     ('oscillate the winding (tracking offset)', 'lower the winding tension',
      'correct the upstream profile')),
    ('tension_troughs_or_creases', 'Tension troughs or creases',
     'Lateral buckling of thin strip under tension in a free span (troughs), which can be '
     'ironed into a crease on a roll.',
     'Vary the span tension and watch the bands; check roll alignment and crown of the '
     'deflector / idler rolls; measure the trough spacing.',
     ('align / re-crown the deflector rolls', 'adjust span tension',
      'shorten the free span')),
    ('profile_flatness_mismatch', 'Profile / flatness mismatch (edge wave, centre buckle)',
     'Relative crown change between entry and exit outside the Shohet-Townsend dead band: '
     'smooth edge waves or a centre buckle rather than narrow stripes.',
     'Entry and exit profile measurements; shapemeter map; compare the relative crowns.',
     ('adjust roll bending / thermal crown', 'match the gap crown to the entry crown')),
    ('heat_streak_or_film_variation', 'Heat streak / oil-film variation',
     'Local oil-film variation from heat: milky bands that wander in width and position '
     '(QCA-1).',
     'Compare band appearance with oil temperature and speed; check whether the bands wander '
     'between coils.',
     ('lower the oil inlet temperature', 'increase coolant flow', 'reduce speed')),
    ('oil_carryover_drips_or_stain', 'Oil carry-over, drips or stain',
     'Coolant carried past the wipers, drips, or staining seen after annealing.',
     'Anneal a sample and look for stain; inspect wipers and drip shields.',
     ('repair wipers / air knives', 'check drip shields', 'adjust oil filtration')),
)

LENGTHWISE_BUILDERS = {
    'nozzle_thermal_stripe': _h_nozzle,
    'cooling_zone_switching_transient': _h_zone,
    'roll_surface_band': _h_roll_surface,
    'grinding_feed_marks': _h_grinding,
    'incoming_ridge_coil_buildup': _h_ridge,
    'tension_troughs_or_creases': _h_troughs,
    'profile_flatness_mismatch': _h_profile,
    'heat_streak_or_film_variation': _h_heat_streak,
    'oil_carryover_drips_or_stain': _h_stain,
}


MEASUREMENT_TOPICS = ('Spray footprint check', 'coolant valve states', 'span tension',
                      'outside-profile scan', 'three consecutive coils')


def measurement_topic(line):
    """Key phrase of a lengthwise measurement line (used to avoid repeating a topic)."""
    return next((t for t in MEASUREMENT_TOPICS if t in line), None)


def lengthwise_next_measurements(obs):
    lines = []
    pos = obs['band_positions_across_width_m']
    if len(pos) < 3 or obs['positions_repeat_across_coils'] is None:
        lines.append('Map the lengthwise band positions across the width (barrel coordinate) '
                     'on three consecutive coils.')
    if obs['positions_change_after_work_roll_change'] is None:
        lines.append('Note whether the band positions move after a work-roll change.')
    if obs['changes_with_coolant_zone_switching'] is None:
        lines.append('Log the coolant valve states against the shapemeter zones and the times '
                     'the bands appear and fade.')
    lines.append('Spray footprint check of the header (pattern paper or water test).')
    if obs['worse_toward_outer_wraps'] is None:
        lines.append('Entry profile scan of the incoming coil and an outside-profile scan of '
                     'the wound coil (ridges; worse toward the outer wraps?).')
    if obs['changes_with_tension'] is None:
        lines.append('Vary the span tension and note whether the bands change.')
    if obs['appearance'] in (None, 'stain'):
        lines.append('Anneal a sample to check for stain.')
    return lines
