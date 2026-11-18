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
  feedback), plus the with-feedback profile before the band-wise saturation scaling
  (``i_units_linear_feedback``, the one to plot). Band states come from strip_shape's
  Rayleigh-quotient rule: in the mill (``state``, ``buckling_utilisation``; tension beside a
  compressed zone stabilises it) and after tension release (``state_after_tension_release``,
  local mode). A LATENT band (flat in the mill) still counts as a model band: it shows on a
  shapemeter and may buckle once tension is released.
- Onsets: stripe heights at which a band first buckles in the mill and after release, found
  by geometric bisection of the scaled shape on a >= 10 mm grid; an after-release onset that
  coincides with the height at which the band first exceeds the 2 I-unit reporting threshold
  is flagged as limited by that threshold (an upper bound). ``gauge_trend`` uses the model
  stripe and a smooth Gaussian reference (half-peak width 100 mm); a top-hat's sharp edges
  give spike artefacts.
- Event visible time: time above the in-mill manifest threshold when reached, else above the
  after-release threshold, else above the reporting threshold (``visible_time_basis``).
- Events run as one transient. Each connected group of adjacent switched nozzles is a stripe
  with its own monitor; the stripe with the largest peak governs the event metrics. An event's
  metrics use the history only up to the start of the next event switching nozzles in the same
  neighbourhood (``attribution_window_end_s``); beyond it a fade is a lower bound, never this
  event's value. The peak profile (shape, thresholds) is the snapshot AT the governing
  stripe's measured peak time: event boundaries are always recorded, a peak between records
  triggers a second run that records it.
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

Phase 3 (SPEC9, battery foil): without a case-pass bite the section still runs (troughs, coil
ridge build-up with the proportional-transfer estimate, positions, two-tone, grinding, the
roll thermal state when ``bite_heat_per_width_w_m`` is supplied); the shape chain uses the
optional ``width_model.shape_inputs`` (precedence over a derived bite) or is NOT_ASSESSABLE
part by part (``shape_chain``); model-band rules then give NEUTRAL 'model not assessable'.
Six optional foil observations and the rule-based ``foil_tension_lines`` hypothesis [V S27,
S28]; extensions of the nozzle, roll-surface, trough and heat-streak rules (tagged in place).

NOT modelled here: everything the wrapped modules do not model; lateral strip tracking; the
second work roll's own header (``rolls_carrying_stripe`` says how many rolls carry a stripe);
closed-gap (roll-kissing) rolling; any physical model of foil tension lines.
"""
import math

from . import band_products
from . import roll_thermal as rt
from . import strip_shape as ss
from .band_process import (failed, int_list, keys, not_supplied, num, num_list,
                           opt_num)

STRIPE_THRESHOLD_M = 1e-7          # analyst choice: reporting threshold for radius stripes
REFERENCE_STRIPE_HEIGHT_M = 0.5e-6  # SPEC6 6.2 gauge_trend reference stripe (no model stripe)
REFERENCE_HALF_PEAK_WIDTH_M = 0.1   # smooth Gaussian reference, ~one cooling zone (analyst)
ONSET_GRID_M = 0.01                 # onset bisections and gauge_trend on a >= 10 mm grid
REPORTING_LIMIT_FACTOR = 1.05       # onset within 5 % of the reporting-threshold height
ISOLATION_MARGIN_M = 0.1            # stripe isolated over [start - margin, end + margin]
ONSET_SEARCH_MAX_M = 50e-6
ONSET_RELATIVE_TOL = 0.015          # geometric bisection to a 1.5 % bracket
RECOVERY_MIN_S = 600.0
RECORD_INTERVAL_S = 2.0
HISTORY_MAX_POINTS = 300
INITIAL_RATE_WINDOW_S = 5.0
SNAPSHOT_TIME_TOL_S = 1e-6          # a snapshot within this of the measured peak time is 'at' it
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
    'lateral_compressive_stress_pa': None, 'shape_inputs': None}
CONTINUITY = ('continuous', 'intermittent', 'both')
APPEARANCES = ('gloss_or_shade', 'loose_or_buckle', 'tight', 'stain', 'crease_or_flute')
OBS_V2_BOOL = ('positions_repeat_across_coils', 'positions_change_after_work_roll_change',
               'changes_with_coolant_zone_switching', 'visible_only_after_tension_release',
               'worse_toward_outer_wraps', 'changes_with_tension', 'follows_previous_strip_edges',
               'worse_at_higher_speed')
OBS_V2_KEYS = ('lengthwise_continuity', 'intermittent_duration_s', 'band_width_m',
               'band_spacing_m', 'appearance') + OBS_V2_BOOL
# SPEC9 9.3 (battery foil): OPTIONAL v2 observation fields (absent = null), so existing v2 case
# files keep loading
OBS_FOIL_BOOL = ('worse_at_lower_tension', 'changes_with_ironing_roll_pressure',
                 'changes_with_exit_air_blowoff', 'changes_after_roll_wiper_cleaning',
                 'tracks_speed_changes', 'appeared_after_narrower_coil')
OBS_V2_OPTIONAL = OBS_FOIL_BOOL
OBS_V2_ALL = OBS_V2_KEYS + OBS_V2_OPTIONAL
SHAPE_INPUT_KEYS = ('strip_stiffness_per_width_pa', 'exit_tension_force_sensitivity_per_width_m',
                    'bite_half_length_m', 'provenance')
FOIL_GAUGE_M = 100e-6               # SPEC9 9.2: below this exit gauge the foil-regime block


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
    for k in OBS_V2_BOOL + OBS_V2_OPTIONAL:
        v = ob.get(k)
        if v is not None and not isinstance(v, bool):
            raise ValueError(f'observation.{k} must be true, false or null')
        out[k] = v
    return out


def validate_shape_inputs(si):
    """SPEC9 9.1: supplied shape-chain inputs (e.g. from a plant foil model), or None."""
    if si is None:
        return None
    keys('width_model.shape_inputs', si, SHAPE_INPUT_KEYS)
    prov = si['provenance']
    if not isinstance(prov, str) or not prov.strip():
        raise ValueError('width_model.shape_inputs.provenance must be a nonempty string')
    return {'strip_stiffness_per_width_pa': num(
                'width_model.shape_inputs.strip_stiffness_per_width_pa',
                si['strip_stiffness_per_width_pa'], positive=True),
            'exit_tension_force_sensitivity_per_width_m': num(
                'width_model.shape_inputs.exit_tension_force_sensitivity_per_width_m',
                si['exit_tension_force_sensitivity_per_width_m'], nonnegative=True, hi=1.0),
            'bite_half_length_m': num('width_model.shape_inputs.bite_half_length_m',
                                      si['bite_half_length_m'], positive=True, hi=0.1),
            'provenance': prov}


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
        keys(f'width_model.events[{i}]', e, ('start_s', 'duration_s', 'nozzle_indices', 'level'),
             ('label',))
        label = e.get('label')
        if label is not None and (not isinstance(label, str) or not label.strip()):
            raise ValueError(f'width_model.events[{i}].label must be a nonempty string or null')
        idx = int_list(f'width_model.events[{i}].nozzle_indices', e['nozzle_indices'])
        if not idx:
            raise ValueError(f'width_model.events[{i}].nozzle_indices must not be empty')
        events.append({'start_s': num(f'width_model.events[{i}].start_s', e['start_s'],
                                      nonnegative=True),
                       'duration_s': num(f'width_model.events[{i}].duration_s', e['duration_s'],
                                         positive=True, hi=1e5),
                       'nozzle_indices': idx,
                       'level': num(f'width_model.events[{i}].level', e['level'], lo=0.0,
                                    hi=1.0),
                       'label': label})
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
    out['shape_inputs'] = validate_shape_inputs(w.get('shape_inputs'))
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


CASE_PASS_KEYS = ('entry_thickness_m', 'exit_thickness_m', 'mean_flow_stress_pa',
                  'friction_coefficient', 'entry_tension_pa', 'exit_tension_pa')
CASE_PASS_REL_TOL = 1e-9


def is_case_pass(case, src):
    """True when ``src`` is None or a schedule row that IS the case pass: every bite-defining
    parameter (gauges, mean flow stress, friction, tensions; width and roll radius are
    case-wide) equals the case pass within a relative 1e-9. Exit speed does not define the
    bite and is not compared. ``case`` must be the EFFECTIVE case (computed flow stress /
    friction already applied to the pass and every row), so like is compared with like.
    A row with the case gauges but another friction, flow stress or tension is a different
    pass: it gets its own bite and never the case pass's ``shape_inputs`` (review finding)."""
    if src is None:
        return True
    p = case['pass']
    return all(abs(src[k] - p[k]) <= CASE_PASS_REL_TOL * max(abs(src[k]), abs(p[k]))
               for k in CASE_PASS_KEYS)


def shape_params_or_none(case, bite, w, src=None):
    """(shape params, basis) for the strip_shape chain of the case pass (``src`` None) or of a
    schedule row, or (None, None) when neither a bite nor ``width_model.shape_inputs`` is
    available. SPEC9 9.1: supplied shape inputs take precedence over a derived bite for the
    case pass (they describe that pass only); other schedule passes use their own bite."""
    si = w.get('shape_inputs')
    if si is not None and is_case_pass(case, src):
        return shape_params(case, bite, w, src, supplied=si), 'shape_inputs_supplied'
    if bite is None:
        return None, None
    return shape_params(case, bite, w, src), 'derived_bite'


def shape_params(case, bite, w, src=None, supplied=None):
    """Pass parameters for the strip_shape chain (exit-tension feedback always on).

    ``supplied``: validated ``width_model.shape_inputs``; its strip stiffness, exit-tension
    force sensitivity and bite half-length replace the bite's. The entry force sensitivity
    (incoming ridges only) is then the bite's when a bite exists, else None."""
    p = case['pass']
    s = p if src is None else src
    width = p['width_m']
    centre = w['strip_centre_m'] if w['strip_centre_m'] is not None else \
        w['roll']['barrel_length_m'] / 2
    if supplied is not None:
        q = supplied['strip_stiffness_per_width_pa']
        a = supplied['bite_half_length_m']
        nx = supplied['exit_tension_force_sensitivity_per_width_m']
    else:
        q = bite.strip_modulus_n_m / width
        a = bite.contact_length_m / 2
        nx = -bite.dforce_dexit_tension_m2 / width
    return {'exit_thickness_m': s['exit_thickness_m'],
            'entry_thickness_m': s['entry_thickness_m'],
            'strip_stiffness_per_width_pa': q,
            'bite_half_length_m': a,
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
            'exit_tension_force_sensitivity_per_width_m': nx,
            'entry_force_sensitivity_per_width_pa': (None if bite is None else
                                                     bite.dforce_dentry_thickness_n_m / width)}


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


def _bands(bands):
    """Band dicts of strip_shape.flatness_from_elongation, passed through unchanged (in-mill
    Rayleigh state and utilisation, tension-released local and global modes)."""
    return [dict(b) for b in bands]


def _linear_feedback_i_units(fb, sp):
    """With-feedback I-unit profile BEFORE the band-wise saturation scaling (for plotting:
    the saturated profile jumps at the band edges). Same transfer and elongation chain as
    strip_shape.thermal_stripe_flatness; I = 1e5*(eps - mean(eps))."""
    if not fb['saturated_bands']:
        return list(fb['flatness']['i_units'])
    zs, drs, h = fb['z_m'], fb['local_radius_deviation_m'], sp['exit_thickness_m']
    tr = ss.transfer_radius_profile(
        zs, drs, bite_half_length_m=sp['bite_half_length_m'],
        strip_stiffness_per_width_pa=sp['strip_stiffness_per_width_pa'],
        roll_radius_m=sp['roll_radius_m'], n_rolls=sp['n_rolls'],
        roll_youngs_modulus_pa=sp['roll_youngs_modulus_pa'],
        roll_poisson_ratio=sp['roll_poisson_ratio'],
        exit_tension_force_sensitivity_per_width_m=sp[
            'exit_tension_force_sensitivity_per_width_m'],
        exit_thickness_m=h, strip_youngs_modulus_pa=sp['strip_youngs_modulus_pa'], xi=sp['xi'])
    el = ss.differential_elongation(zs, [h] * len(zs),
                                    [h + v for v in tr['local_thickness_change_m']], xi=sp['xi'])
    eps = el['elongation']
    m = math.fsum(eps) / len(eps)
    return [(v - m) / ss.I_UNIT for v in eps]


RIGID_NOT_DEFINED = 'RIGID_BOUND_NOT_DEFINED'
RIGID_NOT_DEFINED_FLAG = 'RIGID_BOUND_NOT_DEFINED_BUMP_REACHES_GAUGE'
COMPLIANCE_NOT_DEFINED = 'COMPLIANCE_ONLY_LEVEL_NOT_DEFINED'
COMPLIANCE_NOT_DEFINED_FLAG = 'COMPLIANCE_ONLY_LEVEL_NOT_DEFINED_CHANGE_REACHES_GAUGE'
_NOT_DEFINED = (RIGID_NOT_DEFINED, COMPLIANCE_NOT_DEFINED)


def shape_levels(z, dev, sp):
    """Rigid bound, compliance-only and exit-tension-feedback flatness of a radius profile."""
    fb = _tsf(z, dev, sp, True)
    co = None if fb.get('compliance_only_level_reason') else _tsf(z, dev, sp, False)
    idx = _inside(z, sp['strip_centre_m'], sp['strip_width_m'])
    zs = [z[i] for i in idx]
    h = sp['exit_thickness_m']
    rigid_exit = [h - sp['n_rolls'] * dev[i] for i in idx]
    rg, rigid_reason = None, None
    if min(rigid_exit) <= 0:
        # review finding: the rigid bound is not defined when the rigid thickness change
        # reaches the gauge; the compliant levels are kept
        bump = max(dev[i] for i in idx)
        rigid_reason = (f'rigid bound not defined: the rigid thickness change n_rolls x peak '
                        f'bump = {sp["n_rolls"]} x {bump:.3g} m = {sp["n_rolls"] * bump:.3g} m '
                        f'reaches or exceeds the exit gauge {h:.3g} m')
    else:
        el = ss.differential_elongation(zs, [h] * len(zs), rigid_exit, xi=sp['xi'])
        rg = ss.flatness_from_elongation(
            zs, el['elongation'], youngs_modulus_pa=sp['strip_youngs_modulus_pa'],
            poisson_ratio=sp['strip_poisson_ratio'], thickness_m=h,
            mean_tension_pa=sp['mean_tension_pa'], yield_stress_pa=sp['yield_stress_pa'])
    peak_dr = max(fb['local_radius_deviation_m'], key=abs)
    peak_dh = fb['peak_local_thickness_change_m']
    out = {
        'status': fb['status'], 'released_status': fb['released_status'],
        'manifest_after_release_band_count': fb['manifest_after_release_band_count'],
        'released_global_status': fb['released_global_status'],
        'released_global_max_utilisation': fb['released_global_max_utilisation'],
        'z_m': fb['z_m'],
        'local_radius_deviation_m': fb['local_radius_deviation_m'],
        'local_thickness_change_m': fb['local_thickness_change_m'],
        'i_units_with_feedback': fb['flatness']['i_units'],
        'i_units_linear_feedback': _linear_feedback_i_units(fb, sp),
        'i_units_compliance_only': None if co is None else co['flatness']['i_units'],
        'i_units_rigid': None if rg is None else rg['i_units'],
        'rigid_transfer_bound_i_units': (None if rg is None
                                         else fb['rigid_transfer_bound_i_units']),
        'compliance_only_peak_i_units': fb['compliance_only_peak_i_units'],
        'feedback_peak_i_units': fb['feedback_peak_i_units'],
        'linear_feedback_peak_i_units': fb['linear_feedback_peak_i_units'],
        'peak_radius_deviation_m': peak_dr, 'peak_local_thickness_change_m': peak_dh,
        'peak_transfer_ratio_with_feedback': (peak_dh / (-sp['n_rolls'] * peak_dr)
                                              if peak_dr else None),
        'compliance_only_peak_transfer_ratio': (
            fb['compliance_only_peak_local_thickness_change_m'] / (-sp['n_rolls'] * peak_dr)
            if peak_dr and co is not None else None),
        'effective_strip_stiffness_per_width_pa': fb['effective_strip_stiffness_per_width_pa'],
        'tension_feedback_stiffness_per_width_pa':
            fb['tension_feedback_stiffness_per_width_pa'],
        'exit_tension_force_sensitivity_per_width_m':
            fb['exit_tension_force_sensitivity_per_width_m'],
        'reporting_threshold_i_units': fb['flatness']['reporting_threshold_i_units'],
        'mean_tension_pa': sp['mean_tension_pa'],
        'levels': {
            'rigid': ({'status': RIGID_NOT_DEFINED, 'released_status': None,
                       'peak_abs_i_units': None, 'bands': [], 'reason': rigid_reason}
                      if rg is None else
                      {'status': rg['status'], 'released_status': rg['released_status'],
                       'peak_abs_i_units':
                       max(abs(rg['max_i_units']), abs(rg['min_i_units'])),
                       'bands': _bands(rg['bands'])}),
            'compliance_only': ({'status': COMPLIANCE_NOT_DEFINED, 'released_status': None,
                                 'peak_abs_i_units': None, 'bands': [],
                                 'reason': fb['compliance_only_level_reason']}
                                if co is None else
                                {'status': co['status'],
                                 'released_status': co['released_status'],
                                 'peak_abs_i_units': co['compliance_only_peak_i_units'],
                                 'bands': _bands(co['bands'])}),
            'with_feedback': {'status': fb['status'],
                              'released_status': fb['released_status'],
                              'peak_abs_i_units': fb['feedback_peak_i_units'],
                              'bands': _bands(fb['bands']),
                              'saturated_bands': fb['saturated_bands']}},
        'flags': fb['flags']}
    if rg is None:
        # keys only when the rigid bound is undefined, so other results keep their content
        out['rigid_level_reason'] = rigid_reason
        out['flags'] = sorted(set(out['flags']) | {RIGID_NOT_DEFINED_FLAG})
    if co is None:
        out['compliance_only_level_reason'] = fb['compliance_only_level_reason']
        out['flags'] = sorted(set(out['flags']) | {COMPLIANCE_NOT_DEFINED_FLAG})
    return out


def _band_at(bands, x):
    hit = [b for b in bands if b['start_m'] <= x <= b['end_m']]
    return max(hit, key=lambda b: abs(b['peak_i_units'])) if hit else None


def stripe_states(levels, x):
    """Per level: the band containing position x (peak I-units and state) or below threshold."""
    out = {}
    for name in ('rigid', 'compliance_only', 'with_feedback'):
        st = levels['levels'][name]['status']
        if st in _NOT_DEFINED:
            out[name] = {'peak_i_units': None, 'state': st,
                         'state_after_tension_release': st,
                         'buckling_utilisation': None, 'released_buckling_utilisation': None,
                         'reason': levels['levels'][name]['reason']}
            continue
        b = _band_at(levels['levels'][name]['bands'], x)
        out[name] = ({'peak_i_units': b['peak_i_units'], 'state': b['state'],
                      'state_after_tension_release': b['state_after_tension_release'],
                      'buckling_utilisation': b['buckling_utilisation'],
                      'released_buckling_utilisation': b['released_buckling_utilisation'],
                      'effective_buckling_width_m': b['effective_buckling_width_m'],
                      'released_buckling_width_m': b['released_buckling_width_m'],
                      'sense': b['sense'], 'band_width_m': b['width_m'],
                      'band_buckling_stress_pa': b['band_buckling_stress_pa'],
                      'local_total_stress_pa': b['local_total_stress_pa'],
                      'saturated': b.get('saturated', False)}
                     if b else {'peak_i_units': None, 'state': 'BELOW_REPORTING_THRESHOLD',
                                'state_after_tension_release': 'BELOW_REPORTING_THRESHOLD',
                                'buckling_utilisation': None,
                                'released_buckling_utilisation': None})
    return out


ONSET_KINDS = {'mill': ('status', 'MANIFEST_BUCKLE_BANDS'),
               'released': ('released_status', 'MANIFEST_AFTER_RELEASE_BANDS')}


def coarse_grid(z, prof):
    """Linear resampling onto a uniform grid of at least ONSET_GRID_M (cheaper onsets)."""
    if z[1] - z[0] >= ONSET_GRID_M * 0.999:
        return list(z), list(prof)
    n = max(4, int(round((z[-1] - z[0]) / ONSET_GRID_M)))
    zc = [z[0] + i * (z[-1] - z[0]) / n for i in range(n + 1)]
    return zc, [_interp(z, prof, x) for x in zc]


ONSET_FOUND = 'FOUND'
ONSET_NOT_REACHED = 'NOT_REACHED_WITHIN_SEARCH_CEILING'
ONSET_DOMAIN_LIMIT = 'NOT_REACHED_BEFORE_FEEDBACK_MODEL_DOMAIN_LIMIT'


def onset_search(z, shape, sp, kind='mill', hi=None, lo=None):
    """Smallest factor s with a MANIFEST band (kind 'mill': in the mill; 'released': after
    tension release) for s*shape, decided from the with-feedback result only.

    Returns ``{'status', 'scale', 'domain_limit_scale'}``: ``FOUND`` with the onset scale
    (geometric bisection to ONSET_RELATIVE_TOL); ``NOT_REACHED_WITHIN_SEARCH_CEILING`` when the
    band is still latent at ``hi``; ``NOT_REACHED_BEFORE_FEEDBACK_MODEL_DOMAIN_LIMIT`` when the
    with-feedback calculation itself leaves its domain (ValueError) before any manifest band,
    with the largest valid scale in ``domain_limit_scale`` (never an onset). An undefined
    compliance-only bound does not decide anything (review finding: it used to count as
    manifest). ``lo``: a scale known not to exceed the onset (bracket)."""
    out = {'status': ONSET_NOT_REACHED, 'scale': None, 'domain_limit_scale': None}
    peak = max(abs(v) for v in shape)
    if peak <= 0:
        return out
    key, value = ONSET_KINDS[kind]
    s_hi = (ONSET_SEARCH_MAX_M if hi is None else hi) / peak

    def manifest(sc):
        """True / False from the with-feedback result; None when it is outside its domain."""
        try:
            r = _tsf(z, [sc * v for v in shape], sp)
        except ValueError:
            return None
        return r[key] == value
    s_lo = s_hi * 1e-4 if lo is None or lo >= s_hi else lo
    top = manifest(s_hi)
    if top is None:
        # bracket the domain boundary: largest valid scale below s_hi
        if manifest(s_lo) is None:
            out.update(status=ONSET_DOMAIN_LIMIT, domain_limit_scale=s_lo)
            return out
        a, b = s_lo, s_hi
        while b / a > 1 + ONSET_RELATIVE_TOL:
            mid = math.sqrt(a * b)
            if manifest(mid) is None:
                b = mid
            else:
                a = mid
        if not manifest(a):
            out.update(status=ONSET_DOMAIN_LIMIT, domain_limit_scale=a)
            return out
        s_hi = a
    elif not top:
        return out
    if manifest(s_lo):
        out.update(status=ONSET_FOUND, scale=s_lo)
        return out
    while s_hi / s_lo > 1 + ONSET_RELATIVE_TOL:
        mid = math.sqrt(s_lo * s_hi)
        m = manifest(mid)
        if m is None:        # domain failure inside a valid bracket: keep the valid top
            s_hi = mid
        elif m:
            s_hi = mid
        else:
            s_lo = mid
    out.update(status=ONSET_FOUND, scale=s_hi)
    return out


def onset_scale(z, shape, sp, kind='mill', hi=None, lo=None):
    """Onset scale of ``onset_search`` (None unless FOUND)."""
    return onset_search(z, shape, sp, kind, hi, lo)['scale']


def manifest_onset_scale(z, shape, sp, hi=None):
    return onset_scale(z, shape, sp, 'mill', hi)


def onsets(z, shape, sp):
    """In-mill and after-release onset scales on the coarse grid, plus the scale at which the
    linear-feedback peak reaches the reporting threshold (bands exist only above it). The
    reporting scale brackets the after-release onset from below (a band must be reported
    before it can buckle), the after-release onset brackets the in-mill one (tension only
    stabilises)."""
    zc, pc = coarse_grid(z, shape)
    out = {'mill': None, 'released': None, 'reporting': None}
    peak = max(abs(v) for v in pc)
    if peak <= 0:
        return out
    lin = _tsf(zc, [v * REFERENCE_STRIPE_HEIGHT_M / peak for v in pc], sp)
    li = lin['linear_feedback_peak_i_units'] or 0.0
    thr = lin['flatness']['reporting_threshold_i_units']
    if li > 0:
        out['reporting'] = REFERENCE_STRIPE_HEIGHT_M / peak * thr / li
    lo = None if out['reporting'] is None else out['reporting'] * (1 - 1e-6)
    rel = onset_search(zc, pc, sp, 'released', lo=lo)
    out['released'] = rel['scale']
    mil = onset_search(zc, pc, sp, 'mill',
                       lo=None if out['released'] is None else out['released'] * 0.999)
    out['mill'] = mil['scale']
    # the scale at which the with-feedback calculation leaves its domain, when that ends the
    # search before an onset (never an onset); keys only then
    for name, r in (('released', rel), ('mill', mil)):
        if r['status'] == ONSET_DOMAIN_LIMIT:
            out[f'{name}_domain_limit'] = r['domain_limit_scale']
    return out


DOMAIN_LIMIT_NOTE = ('not reached before the with-feedback flatness calculation leaves its '
                     'domain (elongation or thickness outside the model)')


def domain_limit_text(height):
    """Plain words for a search ended by the feedback model's domain (never an onset)."""
    return f'not reached before the feedback model leaves its domain at about ' \
           f'{height * 1e6:.3g} um'


def _limited(onset, reporting):
    return (onset is not None and reporting is not None
            and onset <= reporting * REPORTING_LIMIT_FACTOR)


def _isolate(z, dev, stripe):
    a, b = stripe['start_m'] - ISOLATION_MARGIN_M, stripe['end_m'] + ISOLATION_MARGIN_M
    return [v if a <= x <= b else 0.0 for x, v in zip(z, dev)]


def _reference_stripe(z, centre, height=REFERENCE_STRIPE_HEIGHT_M):
    """Smooth Gaussian reference stripe, half-peak width REFERENCE_HALF_PEAK_WIDTH_M (a
    top-hat's sharp edges give spike artefacts in the shape chain)."""
    sig = REFERENCE_HALF_PEAK_WIDTH_M / (2 * math.sqrt(2 * math.log(2)))
    return [height * math.exp(-0.5 * ((x - centre) / sig) ** 2) for x in z]


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


def _nozzle_groups(e):
    """Connected groups of adjacent nozzle indices of an event (each group is one stripe)."""
    groups = []
    for i in sorted(e['nozzle_indices']):
        if groups and i == groups[-1][-1] + 1:
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def _event_region(th, groups):
    """[(lo, hi)] neighbourhood of each stripe (nozzle span +- ISOLATION_MARGIN_M)."""
    return [(min(th.positions[i] for i in g) - ISOLATION_MARGIN_M,
             max(th.positions[i] for i in g) + ISOLATION_MARGIN_M) for g in groups]


def _regions_overlap(ra, rb):
    return any(a0 <= b1 and b0 <= a1 for a0, a1 in ra for b0, b1 in rb)


def _attribution(k, starts, regions, end):
    """(window end [s, timeline], flags) of event k: its metrics are attributable until another
    event that switches nozzles in the same neighbourhood starts (that event's growth would be
    read as this one's); an earlier such event leaves its residual in this event's history."""
    ts, flags, window_end = starts[k], [], end
    for j, (tj, rj) in enumerate(zip(starts, regions)):
        if j == k or not _regions_overlap(regions[k], rj):
            continue
        if tj > ts + 1e-9:
            window_end = min(window_end, tj)
        elif tj < ts - 1e-9:
            if 'EARLIER_EVENT_IN_SAME_REGION' not in flags:
                flags.append('EARLIER_EVENT_IN_SAME_REGION')
        elif 'CONCURRENT_EVENT_IN_SAME_REGION' not in flags:
            flags.append('CONCURRENT_EVENT_IN_SAME_REGION')
    return window_end, flags


def _window(times, ts, tw):
    return [i for i, t in enumerate(times) if ts - 1e-9 <= t <= tw + 1e-9]


def _stripe_metrics(times, dev, sel, ts):
    return rt.history_metrics([times[i] - ts for i in sel], [dev[i] for i in sel])


def _events_section(th, sp, actual, events, shape_reason=None):
    """One transient from the steady state through all events (overlaps combined).

    Per event: one monitor per connected group of adjacent switched nozzles (a stripe); the
    stripe with the largest peak governs the event metrics. Metrics use the history up to the
    start of the next event in the same neighbourhood (attribution window); what lies beyond
    it is reported as a lower bound, not as this event's value. The peak profile is the
    snapshot AT the governing stripe's measured peak time (event boundaries are always
    recorded; a missing peak time is recorded by a second run)."""
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
    groups = [_nozzle_groups(e) for e in events]
    regions = [_event_region(th, g) for g in groups]
    stripe_x = [[sum(th.positions[i] for i in g) / len(g) for g in gs] for gs in groups]
    monitors = [x for xs in stripe_x for x in xs]
    first_monitor = [sum(len(xs) for xs in stripe_x[:k]) for k in range(len(events))]
    starts = [e['start_s'] - t0 for e in events]
    attrib = [_attribution(k, starts, regions, end) for k in range(len(events))]
    step = th.numerics['time_step_s']
    interval = max(RECORD_INTERVAL_S, step)
    n_rec = int(end / interval)
    records = sorted({k * interval for k in range(n_rec + 1)} | set(marks))
    z = actual['z_m']
    base = actual['radius_growth_m']

    def run(record_times):
        return rt.simulate(th.roll, th.header, segs, initial=actual, time_step_s=step,
                           record_times_s=record_times, monitor_positions_m=monitors, **th.kw)

    def governing(sim, k):
        """Per-stripe histories and metrics in the attribution window; governing index."""
        ts, tw = starts[k], attrib[k][0]
        out = []
        for g, (nz, x) in enumerate(zip(groups[k], stripe_x[k])):
            mon = sim['monitors'][first_monitor[k] + g]
            times = mon['time_s']
            g0 = _interp(z, base, x)
            dev = [v - g0 for v in mon['radius_growth_m']]
            sel = _window(times, ts, tw)
            out.append({'nozzle_indices': nz, 'x': x, 'times': times, 'dev': dev, 'sel': sel,
                        'met': _stripe_metrics(times, dev, sel, ts)})
        gov = max(range(len(out)), key=lambda i: (abs(out[i]['met']['peak_change']), -i))
        return out, gov

    def peak_times(sim):
        out = []
        for k in range(len(events)):
            st, gov = governing(sim, k)
            out.append(starts[k] + st[gov]['met']['time_of_peak_s'])
        return out

    sim = run(records)
    missing = [t for t in peak_times(sim)
               if not any(abs(s['time_s'] - t) <= SNAPSHOT_TIME_TOL_S for s in sim['snapshots'])]
    rerun = bool(missing)
    if rerun:
        sim = run(sorted(set(records) | set(missing)))
    rows = []
    for k, e in enumerate(events):
        ts = starts[k]
        te = ts + e['duration_s']
        tw, att_flags = attrib[k]
        flags = list(att_flags)
        if tw < end - 1e-9:
            flags.append('LATER_EVENT_IN_SAME_REGION')
            if tw < te - 1e-9:
                flags.append('PEAK_TRUNCATED_BY_LATER_EVENT')
        stripes, gov = governing(sim, k)
        gs = stripes[gov]
        x, times, dev, sel, met = gs['x'], gs['times'], gs['dev'], gs['sel'], gs['met']
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
        t_peak = ts + met['time_of_peak_s']
        snap = min(sim['snapshots'], key=lambda s: (abs(s['time_s'] - t_peak), s['time_s']))
        if abs(snap['time_s'] - t_peak) > SNAPSHOT_TIME_TOL_S:
            flags.append('PEAK_SNAPSHOT_OFFSET_FROM_MEASURED_PEAK')
        prof = [g - b for g, b in zip(snap['radius_growth_m'], base)]
        # isolate this event's stripes: zero outside its nozzle groups' neighbourhoods
        prof = [v if any(lo <= zz <= hi for lo, hi in regions[k]) else 0.0
                for zz, v in zip(z, prof)]
        at_mon = _interp(z, prof, x)
        k_pk = max(range(len(z)), key=lambda i: abs(prof[i]))
        row = {'index': k, 'label': e.get('label') or f'event {k}',
               'start_s': e['start_s'], 'duration_s': e['duration_s'],
               'nozzle_indices': e['nozzle_indices'], 'level': e['level'],
               'nozzle_positions_m': [th.positions[i] for i in e['nozzle_indices']],
               'monitor_position_m': x,
               'governing_stripe_index': gov,
               'stripes': [{'index': i, 'nozzle_indices': s['nozzle_indices'],
                            'nozzle_positions_m': [th.positions[j] for j in s['nozzle_indices']],
                            'monitor_position_m': s['x'],
                            'peak_deviation_m': s['met']['peak_change'],
                            'time_of_peak_s': s['met']['time_of_peak_s'],
                            'time_to_half_peak_s': s['met']['time_to_half_peak_s'],
                            'governing': i == gov} for i, s in enumerate(stripes)],
               'attribution_window_end_s': tw - ts,
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
            if sp is None:
                raise ValueError(f'shape chain NOT_ASSESSABLE: {shape_reason}')
            shape = shape_levels(z, prof, sp)
            row['peak_shape'] = shape
            on = onsets(z, prof, sp)
            for name in ('mill', 'released', 'reporting'):
                key = {'mill': 'manifest', 'released': 'released',
                       'reporting': 'reporting'}[name]
                row[f'{key}_threshold_m'] = None if on[name] is None else on[name] * at_mon
                if f'{name}_domain_limit' in on:
                    # the search ended at the feedback model's domain: no threshold (the band
                    # is treated as not reaching this state), never read as a threshold
                    row[f'{key}_threshold_domain_limit_m'] = on[f'{name}_domain_limit'] * at_mon
            row['released_threshold_limited_by_reporting_threshold'] = _limited(
                on['released'], on['reporting'])
            states = stripe_states(shape, z[k_pk])
            row['peak_state_with_feedback'] = states['with_feedback']['state']
            row['peak_state_after_tension_release'] = states['with_feedback'][
                'state_after_tension_release']
            row['peak_stripe_states'] = states
        except ValueError as exc:
            row['shape_error'] = str(exc)
            row['manifest_threshold_m'] = row['reporting_threshold_m'] = None
            row['released_threshold_m'] = None
            row['peak_state_with_feedback'] = row['peak_state_after_tension_release'] = None
        sign = 1.0 if met['peak_change'] >= 0 else -1.0
        tw_times = [times[i] for i in sel]
        tw_sdev = [sign * dev[i] for i in sel]
        for name in ('manifest', 'released', 'reporting'):
            thr = row[f'{name}_threshold_m']
            t_on = fade = None
            if thr is not None and thr * sign > 0:
                t_on = _first_cross(tw_times, tw_sdev, ts, abs(thr), up=True)
                if t_on is not None and max(te, t_on) <= tw + 1e-9:
                    t_off = _first_cross(tw_times, tw_sdev, max(te, t_on), abs(thr), up=False)
                    fade = None if t_off is None else t_off - te
            row[f'time_to_{name}_threshold_s'] = None if t_on is None else t_on - ts
            row[f'fade_time_below_{name}_threshold_s'] = fade
            row[f'time_above_{name}_threshold_s'] = (
                None if t_on is None or fade is None else te + fade - t_on)
        basis = ('manifest' if row['time_to_manifest_threshold_s'] is not None
                 else 'reporting' if row['time_to_reporting_threshold_s'] is not None else None)
        row['band_life_basis'] = basis
        fade = row[f'fade_time_below_{basis}_threshold_s'] if basis else None
        row['band_life_s'] = None if (basis is None or fade is None) else e['duration_s'] + fade
        row['band_life_lower_bound_s'] = None
        if basis and fade is None:
            flags.append('FADE_BEYOND_ATTRIBUTION_WINDOW' if tw < end - 1e-9
                         else 'FADE_BEYOND_SIMULATED_RECOVERY')
            row['band_life_lower_bound_s'] = tw - ts
        # visible time: in the mill if it buckles there, else after tension release, else
        # the time it stays above the reporting threshold (a shapemeter stripe only)
        vis = next((n for n in ('manifest', 'released', 'reporting')
                    if row[f'time_to_{n}_threshold_s'] is not None), None)
        row['visible_time_basis'] = {'manifest': 'in_mill_manifest',
                                     'released': 'manifest_after_tension_release',
                                     'reporting': 'above_reporting_threshold_only',
                                     None: None}[vis]
        row['visible_time_s'] = None if vis is None else row[f'time_above_{vis}_threshold_s']
        row['visible_time_lower_bound_s'] = (
            tw - (ts + row[f'time_to_{vis}_threshold_s'])
            if vis is not None and row['visible_time_s'] is None else None)
        if flags:
            row['flags'] = flags
        hist = [i for i, t in enumerate(times) if t >= ts - 1e-9]
        stride = max(1, int(math.ceil(len(hist) / HISTORY_MAX_POINTS)))
        keep = hist[::stride]
        if keep[-1] != hist[-1]:
            keep.append(hist[-1])
        row['history'] = {'time_s': [times[i] - ts for i in keep],
                          'radius_deviation_m': [dev[i] for i in keep]}
        rows.append(row)
    return {'status': sim['status'], 'events': rows, 'timeline_end_s': end,
            'recovery_s': recovery, 'time_origin_s': t0,
            'peak_snapshots_recorded_by_second_run': rerun,
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
                                    'reporting threshold when it never becomes manifest)',
            'stripe_definition': 'one monitor per connected group of adjacent switched nozzles '
                                 '(a stripe); the stripe with the largest peak radius deviation '
                                 'governs the event metrics (governing_stripe_index), the others '
                                 'are listed under stripes',
            'attribution_definition': 'event metrics use the monitor history from the event '
                                      'start to attribution_window_end_s: the start of the next '
                                      'event switching nozzles within the isolation margin '
                                      f'({ISOLATION_MARGIN_M:g} m) of this one, else the end of '
                                      'the run; a fade beyond it gives only a lower bound '
                                      '(flag FADE_BEYOND_ATTRIBUTION_WINDOW), a later event '
                                      'starting during this one truncates its peak (flag '
                                      'PEAK_TRUNCATED_BY_LATER_EVENT); an earlier event in the '
                                      'same neighbourhood leaves its residual in the history '
                                      '(flag EARLIER_EVENT_IN_SAME_REGION)',
            'visible_time_definition': 'visible_time_s = time above the in-mill manifest '
                                       'threshold if reached, else above the after-release '
                                       'threshold, else above the reporting threshold '
                                       '(visible_time_basis says which); thresholds are '
                                       'stripe heights at the monitor position, from the peak '
                                       'profile scaled (onsets on a >= 10 mm grid)'}


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
    if healthy_crown is None:
        out['heredity_status'] = ('NOT_ASSESSABLE: the gap crown used needs the healthy-header '
                                  'thermal crown (no roll thermal solution)')
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


def _ridge_proportional(case, ridge, coil, reason):
    """SPEC9 9.1, no bite: the exit ridge from the proportional-transfer limit dh = (h/H)*dH
    (the dominant-tension-feedback limit of the transfer above; a no-bite ESTIMATE, not a
    bound) wound into the coil; the in-pass flatness is not assessable."""
    p = case['pass']
    h, big_h = p['exit_thickness_m'], p['entry_thickness_m']
    ratio = h / big_h
    out = {'position_m': ridge['position_m'], 'entry_ridge_height_m': ridge['height_m'],
           'ridge_width_m': ridge['width_m'], 'exit_to_entry_ridge_ratio': ratio,
           'proportional_ratio_h_over_H': ratio, 'exit_ridge_height_m': ratio * ridge['height_m'],
           'transfer_basis': 'PROPORTIONAL_TRANSFER_LIMIT_NO_BITE',
           'flatness_status': 'NOT_ASSESSABLE', 'peak_i_units': None, 'state': 'NOT_ASSESSABLE',
           'flatness_reason': reason,
           'flags': ['RIDGE_EXIT_HEIGHT_FROM_PROPORTIONAL_LIMIT_NO_BITE'], 'coil': None}
    if coil is not None:
        out['coil'] = _coil_buildup(case, coil, ratio * ridge['height_m'], h)
    return out


def _coil_buildup(case, coil, exit_ridge, h):
    cb = ss.coil_ridge_buildup(exit_ridge, h, coil['inner_radius_m'], coil['outer_radius_m'],
                               case['material']['yield_stress_pa'], coil['winding_tension_pa'],
                               case['material']['youngs_modulus_pa'],
                               coil['compaction_factor'] or ss.DEFAULT_COMPACTION_FACTOR)
    return {k: cb[k] for k in ('status', 'ridge_height_m', 'wraps_at_outer_radius',
                               'radial_build_up_at_outer_radius_m',
                               'hoop_strain_at_outer_radius', 'yield_margin_strain',
                               'critical_ridge_height_at_outer_radius_m',
                               'ridge_to_critical_ratio', 'yield_onset_radius_m',
                               'affected_length_fraction', 'compaction_factor')}


def _ridge(case, w, sp, ridge, z, coil, reason=None):
    """Flatness effect of an incoming ridge in this pass and its coil build-up [D]."""
    if sp is None or sp.get('entry_force_sensitivity_per_width_pa') is None:
        return _ridge_proportional(case, ridge, coil, reason or (
            'the ridge transfer needs the entry-thickness force sensitivity of a derived bite '
            '(not part of width_model.shape_inputs)'))
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
           'transfer_basis': 'DERIVED_TRANSFER',
           'flags': ['RIDGE_TRANSFER_DERIVED_IN_INTEGRATION_LAYER'],
           'coil': None}
    if coil is not None:
        out['coil'] = _coil_buildup(case, coil, ratio * ridge['height_m'], h)
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


def _positions(case, w, obs, steady, events, ridges, troughs, two_tone, grinding_pitch, th):
    """Observed against predicted positions and pitches. ``steady`` may be None (no roll
    thermal solution, SPEC9 9.1): the blocked / low-level nozzles still come from the header
    inputs (``th``), the steady stripes are then empty."""
    pos = obs['band_positions_across_width_m']
    pitch = w['spray_header']['nozzle_pitch_m']
    tol, basis = position_tolerance(obs, pitch)
    th_pos = th.positions
    low = [th_pos[i] for i, lv in enumerate(th.levels) if lv < 1.0]
    predicted = {
        'steady_stripes': [s['peak_position_m'] for s in steady['stripes']] if steady else [],
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
           'position_matches': {}, 'spacing_matches': {},
           'steady_stripes_basis': ('roll thermal steady state' if steady else
                                    'NOT_ASSESSABLE: no roll thermal solution')}
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
            out['spacing_matches'][name] = spacing_match(gaps, p)
    return out


MAX_SPACING_MULTIPLE = 8.5     # strip_shape.match_spacing caps the multiple at 8


def spacing_match(gaps, pitch):
    """match_spacing, or NOT_COMPARABLE when every gap exceeds 8.5 pitches (the module caps
    the multiple at 8 and would report misleading deviations of many pitches)."""
    min_ratio = min(gaps) / pitch
    if min_ratio > MAX_SPACING_MULTIPLE:
        return {'status': 'NOT_COMPARABLE_GAP_EXCEEDS_8_PITCHES', 'candidate_pitch_m': pitch,
                'min_gap_in_pitches': min_ratio}
    m = ss.match_spacing(gaps, pitch)
    return {'status': m['status'], 'candidate_pitch_m': pitch, 'multiples': m['multiples'],
            'gaps': m['gaps']}


def _gauge_trend(case, w, get_bite, steady, centre, coil, z_grid, op_bite, shape_reason):
    """Same stripe on every schedule pass. ``steady`` may be None (Gaussian reference stripe
    on ``z_grid``). Per pass the shape parameters come from the pass's own bite; the case pass
    uses ``width_model.shape_inputs`` when supplied (SPEC9 9.1) and is rejected with the bite
    error when it has neither. ``op_bite``: the case-pass bite (or None)."""
    th_z = steady['z_m'] if steady else z_grid
    rows_src = case['schedule'] or [dict(case['pass'], label='case pass')]
    if steady and steady['stripes']:
        big = max(steady['stripes'], key=lambda s: abs(s['peak_deviation_m']))
        shape = _isolate(th_z, steady['local_deviation_m'], big)
        basis = (f'largest steady stripe (peak {big["peak_deviation_m"]:.3e} m at '
                 f'{big["peak_position_m"]:.4g} m), isolated; onsets by scaling its own shape')
    else:
        shape = _reference_stripe(th_z, centre)
        basis = (f'{REFERENCE_STRIPE_HEIGHT_M:g} m Gaussian reference stripe (half-peak width '
                 f'{REFERENCE_HALF_PEAK_WIDTH_M:g} m) at the strip centre (no steady stripe)')
    zc, shape_c = coarse_grid(th_z, shape)
    peak_ref = max(shape_c, key=abs)
    peak_x = zc[max(range(len(shape_c)), key=lambda i: abs(shape_c[i]))]
    ref = _reference_stripe(zc, peak_x)
    rows = []
    for src in rows_src:
        row = {'label': src['label'], 'entry_thickness_m': src['entry_thickness_m'],
               'exit_thickness_m': src['exit_thickness_m'],
               'exit_tension_pa': src['exit_tension_pa'],
               'friction_coefficient': src['friction_coefficient'],
               'mean_flow_stress_pa': src['mean_flow_stress_pa']}
        try:
            # review finding: the case pass always uses the operating bite (the same object
            # the steady shape section used, supplied or derived); only genuinely different
            # passes derive their own
            if is_case_pass(case, src):
                if op_bite is None and w.get('shape_inputs') is None:
                    raise ValueError(f'shape chain NOT_ASSESSABLE: {shape_reason}')
                bite = op_bite
            else:
                bite = get_bite(src)
            sp, sp_basis = shape_params_or_none(case, bite, w, src)
            lv = shape_levels(zc, shape_c, sp)
            st = stripe_states(lv, peak_x)['with_feedback']
            win = ss.shohet_townsend_window(src['exit_thickness_m'], case['pass']['width_m'])
            on = onsets(zc, shape_c, sp)
            on_ref = onsets(zc, ref, sp)

            def h(scale, height):
                return None if scale is None else scale * height
            row.update(
                shape_inputs_basis=sp_basis,
                bite_source=None if bite is None else bite.source,
                bite_model=bite_model_name(bite),
                bite_flags=[] if bite is None else list(bite.flags),
                separating_force_per_width_n_m=(None if bite is None else
                                                bite.separating_force_n
                                                / case['pass']['width_m']),
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
                state=st['state'],
                state_after_tension_release=st['state_after_tension_release'],
                buckling_utilisation=st['buckling_utilisation'],
                released_buckling_utilisation=st['released_buckling_utilisation'],
                band_buckling_stress_pa=st.get('band_buckling_stress_pa'),
                band_width_m=st.get('band_width_m'),
                effective_buckling_width_m=st.get('effective_buckling_width_m'),
                shohet_townsend_half_width_i_units=(win['upper_bound_i_units']
                                                    - win['lower_bound_i_units']) / 2,
                shohet_townsend_upper_i_units=win['upper_bound_i_units'],
                shohet_townsend_lower_i_units=win['lower_bound_i_units'],
                manifest_onset_stripe_height_m=h(on['mill'], abs(peak_ref)),
                released_onset_stripe_height_m=h(on['released'], abs(peak_ref)),
                reporting_onset_stripe_height_m=h(on['reporting'], abs(peak_ref)),
                released_onset_limited_by_reporting_threshold=_limited(on['released'],
                                                                       on['reporting']),
                manifest_onset_height_reference_m=h(on_ref['mill'], REFERENCE_STRIPE_HEIGHT_M),
                released_onset_height_reference_m=h(on_ref['released'],
                                                    REFERENCE_STRIPE_HEIGHT_M),
                reporting_onset_height_reference_m=h(on_ref['reporting'],
                                                     REFERENCE_STRIPE_HEIGHT_M),
                released_onset_reference_limited_by_reporting_threshold=_limited(
                    on_ref['released'], on_ref['reporting']))
            for o, height, keys_ in (
                    (on, abs(peak_ref), {'mill': 'manifest_onset_stripe_height_m',
                                         'released': 'released_onset_stripe_height_m'}),
                    (on_ref, REFERENCE_STRIPE_HEIGHT_M,
                     {'mill': 'manifest_onset_height_reference_m',
                      'released': 'released_onset_height_reference_m'})):
                for name, k in keys_.items():
                    if f'{name}_domain_limit' in o:      # keys only then (no onset)
                        row[k[:-2] + '_domain_limit_m'] = o[f'{name}_domain_limit'] * height
        except ValueError as exc:
            row['rejected'] = str(exc)
        h1 = src['exit_thickness_m']
        if 'rejected' in row:
            # bite-free: the flatness dead band needs only gauge and width (review follow-up)
            try:
                win = ss.shohet_townsend_window(h1, case['pass']['width_m'])
                row.update(shohet_townsend_half_width_i_units=(win['upper_bound_i_units']
                                                               - win['lower_bound_i_units']) / 2,
                           shohet_townsend_upper_i_units=win['upper_bound_i_units'],
                           shohet_townsend_lower_i_units=win['lower_bound_i_units'])
            except ValueError as exc:
                row['shohet_townsend_error'] = str(exc)
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
    out = {'reference_stripe_peak_m': peak_ref, 'reference_stripe_position_m': peak_x,
           'reference_stripe_basis': basis,
           'reference_stripe_description': (
               f'smooth Gaussian stripe, half-peak width {REFERENCE_HALF_PEAK_WIDTH_M:g} m (about '
               f'one cooling zone), centred at {peak_x:.4g} m; its height is bisected for the '
               '*_onset_height_reference_m columns'),
           'evaluation_grid_m': zc[1] - zc[0],
           'rows': rows, 'text': _trend_text(rows, peak_ref)}
    # Bite-free span thresholds per pass and their trend sentence: only for a foil-regime case
    # or a schedule with a pass without a bite (the passes they matter for), so that sheet
    # results without such passes keep their exact content
    if (case['pass']['exit_thickness_m'] < FOIL_GAUGE_M
            or any('rejected' in r for r in rows)):
        for src, row in zip(rows_src, rows):
            _span_thresholds(case, w, src, row)
        out['bite_free_text'] = _bite_free_text(rows)
    return out


def _span_thresholds(case, w, src, row):
    """Trough onset and roller-wrinkle thresholds of both spans of one pass (bite-free; the
    same ``tension_trough_screen`` call as the case-pass ``troughs`` section, with this pass's
    gauges and tensions)."""
    sp, m, p = case['spans'], case['material'], case['pass']
    for name, h, length, tension in (
            ('entry_span', src['entry_thickness_m'], sp['entry_span_length_m'],
             src['entry_tension_pa']),
            ('exit_span', src['exit_thickness_m'], sp['exit_span_length_m'],
             src['exit_tension_pa'])):
        try:
            r = ss.tension_trough_screen(
                h, length, tension, p['width_m'], roller_radius_m=w['deflector_roll_radius_m'],
                lateral_compressive_stress_pa=None, observed_spacing_m=None,
                youngs_modulus_pa=m['youngs_modulus_pa'], poisson_ratio=STRIP_POISSON_RATIO)
            row[f'trough_critical_lateral_stress_{name}_pa'] = r[
                'trough_critical_lateral_stress_pa']
            row[f'roller_wrinkle_critical_lateral_stress_{name}_pa'] = r[
                'roller_wrinkle_critical_lateral_stress_pa']
        except ValueError as exc:
            row[f'trough_critical_lateral_stress_{name}_pa'] = None
            row[f'roller_wrinkle_critical_lateral_stress_{name}_pa'] = None
            row[f'span_threshold_error_{name}'] = str(exc)


BITE_FREE_SERIES = (
    ('shohet_townsend_half_width_i_units', 'flatness dead band half-width', 1.0, 'I-units', 3),
    ('critical_ridge_height_m', 'critical coil ridge height', 1e6, 'um', 3),
    ('trough_critical_lateral_stress_exit_span_pa', 'trough onset lateral stress, exit span',
     1e-3, 'kPa', 3),
    ('trough_critical_lateral_stress_entry_span_pa', 'trough onset lateral stress, entry span',
     1e-3, 'kPa', 3),
    ('roller_wrinkle_critical_lateral_stress_exit_span_pa', 'roller-wrinkle threshold, exit span',
     1e-6, 'MPa', 3),
    ('roller_wrinkle_critical_lateral_stress_entry_span_pa',
     'roller-wrinkle threshold, entry span', 1e-6, 'MPa', 3))


def _bite_free_text(rows):
    """How each bite-free quantity changes from the thickest to the thinnest pass (by exit
    gauge), passes without a roll bite included."""
    order = sorted(rows, key=lambda r: -r['exit_thickness_m'])
    if len(order) < 2:
        return 'Fewer than two passes: no bite-free trend statement.'
    a, b = order[0], order[-1]
    nobite = [r['label'] for r in order if 'rejected' in r]
    parts = []
    for key, label, scale, unit, d in BITE_FREE_SERIES:
        vals = [r.get(key) for r in order]
        vals = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if len(vals) < 2 or vals[0] == 0:
            continue
        mags = [abs(v) for v in vals]
        falls = all(y < x for x, y in zip(mags, mags[1:]))
        rises = all(y > x for x, y in zip(mags, mags[1:]))
        how = ('in magnitude ' if vals[0] < 0 else '') + (
            'falls on every pass' if falls else 'rises on every pass' if rises
            else 'not monotonic')
        parts.append(f'{label} {vals[0] * scale:.{d}g} -> {vals[-1] * scale:.{d}g} {unit} '
                     f'(x{mags[-1] / mags[0]:.2g}, {how})')
    if not parts:
        return 'No bite-free quantity available on two passes.'
    return (f'Bite-free thresholds (no roll bite needed), thickest to thinnest pass, '
            f'{a["label"]} ({a["exit_thickness_m"] * 1e6:.3g} um) to {b["label"]} '
            f'({b["exit_thickness_m"] * 1e6:.3g} um)'
            + (f', including passes without a roll bite ({", ".join(nobite)})' if nobite else '')
            + ': ' + '; '.join(parts) + '.')


def _trend_text(rows, peak):
    """Plain-words gauge trend, generated from the gauge_trend numbers."""
    # thick -> thin by exit gauge (a schedule may list an alternative route after the main one)
    ok = sorted((r for r in rows if 'rejected' not in r), key=lambda r: -r['exit_thickness_m'])
    if len(ok) < 2:
        return ('Fewer than two assessable passes: no gauge trend statement.' if ok or not rows
                else 'No pass assessable.') + _rejected_text(rows)
    a, b = ok[0], ok[-1]

    def um(x, limited=False, row=None, key=None):
        if x is None:
            dl = None if row is None else row.get(key[:-2] + '_domain_limit_m')
            return domain_limit_text(dl) if dl else 'not reached below 50 um'
        return f'{x * 1e6:.3g} um' + (' (reporting-threshold limited)' if limited else '')

    def ratio(x, y):
        return x / y if x and y else None
    ga, gb = a['exit_thickness_m'] * 1e3, b['exit_thickness_m'] * 1e3
    la, lb = a['linear_feedback_i_units'], b['linear_feedback_i_units']
    text = (f'Same {abs(peak) * 1e6:.3g} um roll stripe on every pass, {ga:.3g} mm -> '
            f'{gb:.3g} mm: linear-feedback I-units {la:.3g} -> {lb:.3g} (x{lb / la:.2f}; '
            + (f'rigid bound x{b["rigid_i_units"] / a["rigid_i_units"]:.2f}). '
               if a['rigid_i_units'] and b['rigid_i_units'] else
               'rigid bound not defined on ' + ', '.join(
                   r['label'] for r in (a, b) if not r['rigid_i_units'])
               + ': the rigid thickness change reaches the gauge). '))
    states = [(r['label'], r['state'], r['state_after_tension_release']) for r in ok]
    mill = sum(1 for _, m, _ in states if m == 'MANIFEST_BUCKLE')
    rel = sum(1 for _, _, x in states if x == 'MANIFEST_AFTER_TENSION_RELEASE')
    text += (f'In the mill this stripe buckles on {mill} of {len(ok)} passes (utilisation '
             f'{a["buckling_utilisation"] or 0:.2g} -> {b["buckling_utilisation"] or 0:.2g}); '
             f'after tension release on {rel} of {len(ok)} (utilisation '
             f'{a["released_buckling_utilisation"] or 0:.2g} -> '
             f'{b["released_buckling_utilisation"] or 0:.2g}). ')
    changes = [f'{r["label"]}: {r["state"]} / {r["state_after_tension_release"]}'
               for prev, r in zip(ok, ok[1:])
               if (prev['state'], prev['state_after_tension_release'])
               != (r['state'], r['state_after_tension_release'])]
    if changes:
        text += 'State changes along the schedule at ' + '; '.join(changes) + '. '
    carriers = []
    for label, mk, rk, lk in (
            ('model stripe', 'manifest_onset_stripe_height_m', 'released_onset_stripe_height_m',
             'released_onset_limited_by_reporting_threshold'),
            ('Gaussian reference', 'manifest_onset_height_reference_m',
             'released_onset_height_reference_m',
             'released_onset_reference_limited_by_reporting_threshold')):
        rm, rr = ratio(a[mk], b[mk]), ratio(a[rk], b[rk])
        text += (f'Onset stripe height, {label}: in the mill {um(a[mk], row=a, key=mk)} -> '
                 f'{um(b[mk], row=b, key=mk)}, after release {um(a[rk], a[lk], a, rk)} -> '
                 f'{um(b[rk], b[lk], b, rk)}. ')
        if rm is None and a[mk] and b[mk] is None and not b.get(mk[:-2] + '_domain_limit_m'):
            # SPEC12 stage A: not reached on the thin pass = above the 50 um search ceiling,
            # so the thick/thin ratio is at most a/50 um (a rise beyond the search)
            rm = a[mk] / ONSET_SEARCH_MAX_M
            text += (f'For the {label} the in-mill onset rises beyond the '
                     f'{ONSET_SEARCH_MAX_M * 1e6:.3g} um search ceiling on the thin pass '
                     f'(thick/thin ratio below {rm:.2g}). ')
        if rm is not None and rr is not None:
            carriers.append((label, rm, rr))
    for label, rm, rr in carriers:
        if max(rm, rr) < 1.5 and min(rm, rr) <= 1 / 1.5:
            # SPEC9 finding: at foil gauge the onsets can RISE toward thin gauge (the ratio
            # test above only looked for a fall and called this 'no change')
            text += (f'For the {label} the onsets RISE toward the thin pass (thick/thin ratio '
                     f'{rm:.2g} in the mill, {rr:.2g} after release): in this model the stripe '
                     'is LESS likely to show at thinner gauge, so the model does not reproduce '
                     '"worse at thinner gauge" for it. ')
        elif max(rm, rr) < 1.5:
            text += f'For the {label} neither onset changes much with gauge. '
        else:
            which = 'after-release onset' if rr >= rm else 'in-mill onset'
            text += (f'For the {label} the gauge trend is carried by the {which} (thick/thin '
                     f'ratio {max(rm, rr):.2g} against {min(rm, rr):.2g}). ')
    lim = [r['label'] for r in ok if r['released_onset_limited_by_reporting_threshold']
           or r['released_onset_reference_limited_by_reporting_threshold']]
    if lim:
        text += ('After-release onsets on ' + ', '.join(lim) + ' are limited by the 2 I-unit '
                 'reporting threshold (a band must first be reported), so they are upper '
                 'bounds of the buckling onset. ')
    text += ('Flatness dead band half-width '
             f'{a["shohet_townsend_half_width_i_units"]:.3g} -> '
             f'{b["shohet_townsend_half_width_i_units"]:.3g} I-units.')
    return text + _rejected_text(rows)


def _rejected_text(rows):
    bad = [r for r in rows if 'rejected' in r]
    if not bad:
        return ''
    return (' Not assessable (excluded from the trend): '
            + '; '.join(f'{r["label"]} ({r["rejected"]})' for r in bad) + '.')


# ============================================================================= section
def bite_model_name(bite):
    """'hitchcock', 'experimental_mattress', 'supplied' or None (no bite)."""
    if bite is None:
        return None
    if MATTRESS_FLAG in bite.flags:
        return 'experimental_mattress'
    return 'supplied' if bite.source == 'supplied' else 'hitchcock'


MATTRESS_FLAG = 'BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL'


def not_assessable(reason):
    return {'status': 'NOT_ASSESSABLE', 'not_supplied': False, 'reason': reason}


def width_section(case, bite, get_bite, heat_row, trib, flags, bite_error=None):
    """The ``width`` result section (SPEC6 6.2). ``get_bite(src)`` returns the bite of a
    schedule pass (effective values) or raises ValueError.

    SPEC9 9.1: without a case-pass bite the section still runs. Tension troughs, coil ridge
    build-up (proportional-transfer estimate) and the critical ridge height, positions and
    spacing, two-tone and grinding pitch need no bite; the roll thermal steady state and
    events need ``bite_heat_per_width_w_m`` (supplied when there is no bite) and the roll heat
    fraction. The shape chain (transfer, flatness, onsets, gauge trend of the case pass) uses
    ``width_model.shape_inputs`` when supplied (they take precedence over a derived bite),
    else the bite; with neither its parts are individually NOT_ASSESSABLE with the bite error
    as the reason (``shape_chain``)."""
    w = case.get('width_model')
    if w is None:
        return not_supplied('width_model is null or absent')
    p = case['pass']
    out = {'status': 'SCREENING_RESULT_NOT_PLANT_VALIDATED', 'not_supplied': False,
           'failures': [], 'flags': [], 'limitations': [
               'Circumferentially averaged roll temperature; top-hat spray footprints.',
               'Shape chain: half-space roll compliance, linear exit-tension feedback with an '
               'approximate band-wise saturation, k = 4 narrow-band buckling (from memory).',
               'Stripe detection by differencing against a healthy-header solution; the '
               'stripe threshold is an analyst choice.',
               'Not plant-validated.']}
    sp, sp_basis = shape_params_or_none(case, bite, w)
    shape_reason = None
    if sp is None:
        shape_reason = ('no bite response for the case pass'
                        + (f' ({bite_error})' if bite_error else '')
                        + ' and no width_model.shape_inputs: the strip stiffness, bite '
                          'half-length and exit-tension feedback are unknown')
        flags.append('WIDTH_SHAPE_CHAIN_NOT_ASSESSABLE_NO_BITE')
        out['flags'].append('WIDTH_SHAPE_CHAIN_NOT_ASSESSABLE_NO_BITE')
    elif sp_basis == 'shape_inputs_supplied':
        flags.append('SHAPE_INPUTS_SUPPLIED')
        out['flags'].append('SHAPE_INPUTS_SUPPLIED')
    out['shape_chain'] = {
        'status': 'EVALUATED' if sp is not None else 'NOT_ASSESSABLE',
        'basis': sp_basis, 'reason': shape_reason,
        'provenance': (w['shape_inputs']['provenance'] if sp_basis == 'shape_inputs_supplied'
                       else None),
        'parts_needing_it': ['shape.steady', 'shape.steady_stripe_table',
                             'shape.nozzle_pattern_ripple', 'thermal_events peak shapes and '
                             'thresholds', 'gauge_trend (case pass)',
                             'incoming ridge flatness in the pass'],
        'parts_without_it': ['thermal_steady', 'thermal_events (radius histories)',
                             'troughs', 'coil ridge build-up and critical ridge height',
                             'positions', 'two_tone', 'grinding_feed_pitch_m',
                             'shape.crown (Shohet-Townsend window)']}
    if w['roll_heat_fraction_per_roll'] is not None:
        fraction, fbasis = w['roll_heat_fraction_per_roll'], 'supplied'
    else:
        fraction = (1 - trib['strip_heat_fraction']) / 2
        fbasis = '(1 - tribology.strip_heat_fraction)/2'
    thermal_reason = None
    if w['bite_heat_per_width_w_m'] is not None:
        heat, hbasis = w['bite_heat_per_width_w_m'], 'supplied'
    elif heat_row is not None and 'bite_heat_per_width_w_m' in heat_row:
        heat = heat_row['bite_heat_per_width_w_m']
        hbasis = 'computed: plastic work + interface slip dissipation of the pass (' + \
            heat_row['friction_power_basis'] + ')'
    else:
        heat, hbasis = None, None
        thermal_reason = ('bite heat per width not supplied (width_model.bite_heat_per_width_w_m) '
                          'and not computable' + (' without a bite' if bite is None else ''))
        flags.append('WIDTH_THERMAL_NOT_ASSESSABLE_NO_BITE_HEAT')
    th = _Thermal(case, w, heat, fraction)
    out['barrel_length_m'] = th.length
    out['inputs_used'] = {
        'roll_heat_fraction_per_roll': fraction, 'roll_heat_fraction_basis': fbasis,
        'bite_heat_per_width_w_m': heat, 'bite_heat_basis': hbasis,
        'numerics': th.numerics, 'strip_centre_m': th.centre, 'strip_width_m': th.width,
        'n_rolls': w['rolls_carrying_stripe'],
        'xi': (w['shape_disturbing_coefficient'] if w['shape_disturbing_coefficient']
               is not None else DEFAULT_XI),
        'mean_tension_pa': p['exit_tension_pa'],
        'strip_stiffness_per_width_pa': sp['strip_stiffness_per_width_pa'] if sp else None,
        'bite_half_length_m': sp['bite_half_length_m'] if sp else None,
        'exit_tension_force_sensitivity_per_width_m':
            sp['exit_tension_force_sensitivity_per_width_m'] if sp else None,
        'shape_inputs_basis': sp_basis,
        'exit_tension_feedback': 'always applied (SPEC6 6.7)'}
    steady = healthy = actual = None
    if thermal_reason is not None:
        out['thermal_steady'] = not_assessable(thermal_reason)
    else:
        try:
            steady, healthy, actual, dev = _steady_section(th, sp)
            out['thermal_steady'] = steady
            out['flags'] += [f for f in steady['flags'] if f not in out['flags']]
        except ValueError as exc:
            out['thermal_steady'] = failed('thermal_steady', exc)
            out['failures'].append(out['thermal_steady']['error'])
    shape = {'steady': None, 'nozzle_pattern_ripple': None, 'crown': None, 'ridges': []}
    if steady is not None and sp is None:
        shape['steady'] = not_assessable(shape_reason)
        shape['nozzle_pattern_ripple'] = not_assessable(shape_reason)
    elif steady is not None:
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
                on = onsets(steady['z_m'], _isolate(steady['z_m'], steady['local_deviation_m'],
                                                    s), sp)
                pk = abs(s['peak_deviation_m'])
                for key, name in (('manifest_onset_peak_height_m', 'mill'),
                                  ('released_onset_peak_height_m', 'released'),
                                  ('reporting_onset_peak_height_m', 'reporting')):
                    row[key] = None if on[name] is None else on[name] * pk
                    if f'{name}_domain_limit' in on:
                        row[key[:-2] + '_domain_limit_m'] = on[f'{name}_domain_limit'] * pk
                row['released_onset_limited_by_reporting_threshold'] = _limited(
                    on['released'], on['reporting'])
        except ValueError as exc:
            shape['steady'] = failed('shape.steady', exc)
            out['failures'].append(shape['steady']['error'])
        try:
            rip = steady['nozzle_pattern_ripple']['profile_m']
            if max(abs(v) for v in rip) > 0:
                lv = shape_levels(steady['z_m'], rip, sp)
                shape['nozzle_pattern_ripple'] = {
                    k: lv[k] for k in ('status', 'released_status',
                                       'rigid_transfer_bound_i_units',
                                       'compliance_only_peak_i_units', 'feedback_peak_i_units',
                                       'linear_feedback_peak_i_units', 'i_units_with_feedback',
                                       'i_units_linear_feedback')}
                shape['nozzle_pattern_ripple']['peak_to_peak_m'] = steady[
                    'nozzle_pattern_ripple']['peak_to_peak_m']
                shape['nozzle_pattern_ripple']['band_count_with_feedback'] = len(
                    lv['levels']['with_feedback']['bands'])
        except ValueError as exc:
            shape['nozzle_pattern_ripple'] = failed('shape.nozzle_pattern_ripple', exc)
    elif sp is None:
        shape['steady'] = not_assessable(shape_reason)
    try:
        shape['crown'] = _crown(case, w, steady['healthy_thermal_crown_m'] if steady else None)
    except ValueError as exc:
        shape['crown'] = failed('shape.crown', exc)
        out['failures'].append(shape['crown']['error'])
    if w['events'] and actual is not None:
        try:
            out['thermal_events'] = _events_section(th, sp, actual, w['events'], shape_reason)
        except ValueError as exc:
            out['thermal_events'] = failed('thermal_events', exc)
            out['failures'].append(out['thermal_events']['error'])
    elif w['events']:
        out['thermal_events'] = not_assessable('steady roll thermal state not available'
                                               + (f' ({thermal_reason})' if thermal_reason
                                                  else ''))
    else:
        out['thermal_events'] = not_supplied('no width_model.events')
    cell = th.numerics['axial_cell_m']
    z = steady['z_m'] if steady else [(i + 0.5) * cell for i in
                                      range(max(4, int(round(th.length / cell))))]
    for r in w['incoming_ridges']:
        try:
            shape['ridges'].append(_ridge(case, w, sp, r, z, w['coil'], shape_reason))
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
    try:
        out['positions'] = _positions(case, w, case['observation'], steady, events,
                                      w['incoming_ridges'], out['troughs'], two_tone,
                                      grinding_pitch, th)
    except ValueError as exc:
        out['positions'] = failed('positions', exc)
        out['failures'].append(out['positions']['error'])
    try:
        out['gauge_trend'] = _gauge_trend(case, w, get_bite, steady, th.centre, w['coil'], z,
                                          bite, shape_reason)
    except ValueError as exc:
        out['gauge_trend'] = failed('gauge_trend', exc)
        out['failures'].append(out['gauge_trend']['error'])
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
        # SPEC9 9.1: the width section may run without the roll thermal solution or without
        # the shape chain; model-band rules then say 'model not assessable' (never contradict)
        self.width_ran = (isinstance(width, dict) and not width.get('not_supplied', True)
                          and width.get('status') not in ('FAILED', 'NOT_ASSESSABLE'))
        steady_shape = ((width.get('shape') or {}).get('steady')
                        if isinstance(width, dict) else None)
        self.shape_ok = (self.width_ok and isinstance(steady_shape, dict)
                         and steady_shape.get('status') not in ('FAILED', 'NOT_ASSESSABLE'))
        self.model_reason = None
        if self.width_ran and not self.width_ok:
            self.model_reason = ('no roll thermal solution: '
                                 + str((width.get('thermal_steady') or {}).get(
                                     'reason', (width.get('thermal_steady') or {}).get(
                                         'error', 'not available'))))
        elif self.width_ran and not self.shape_ok:
            self.model_reason = ('shape chain: ' + str((steady_shape or {}).get(
                'reason', (steady_shape or {}).get('error', 'not available'))))
        self.exit_thickness = case['pass']['exit_thickness_m']
        self.film_ratio, self.film_basis = None, None
        coolant = case['coolant']
        pitch = (w['spray_header']['nozzle_pitch_m'] if w is not None else
                 coolant['nozzle_pitch_m'] if coolant is not None else None)
        self.nozzle_pitch = pitch
        self.zone_pitch = w['cooling_zone_pitch_m'] if w is not None else None
        self.tol, self.tol_basis = position_tolerance(obs, pitch)
        self.gaps, self.spacing, self.gap_basis = observed_gaps(obs)
        self.header_known = False
        self.l1_predicted, self.l1_source = [], None
        # interval sources (phase-1 band-risk stripes) keep their bounds: a band anywhere
        # inside an uncovered zone matches it (review finding), as in screens.band_position_match
        self.l1_intervals = None
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
            self.steady_bands = [(r['position_m'], r['with_feedback']['state'],
                                  r['with_feedback']['state_after_tension_release'])
                                 for r in table if r['peak_radius_deviation_m'] > 0]
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
        elif self.width_ran and isinstance(width.get('positions'), dict) \
                and 'predicted_positions_m' in width['positions']:
            # no roll thermal solution: the blocked / low-level nozzles are still known
            self.header_known = True
            pred = width['positions']['predicted_positions_m']
            self.l1_predicted = sorted(set(pred.get('blocked_or_low_level_nozzles') or []))
            self.l1_source = 'blocked / low-level nozzles (no roll thermal solution)'
            self.two_tone = (width.get('two_tone') or {}).get('band_positions_m', [])
            self.ridges = [r for r in (width.get('shape') or {}).get('ridges', [])
                           if 'rejected' not in r]
            self.troughs = width.get('troughs')
            self.feed_pitch = width.get('grinding_feed_pitch_m')
        elif screens is not None and screens.get('spray_coverage') is not None:
            self.header_known = True
            self.l1_predicted = [s['center_m'] for s in screens['band_risk_stripes'] or []]
            self.l1_intervals = [dict(s) for s in screens['band_risk_stripes'] or []]
            self.l1_source = 'phase-1 spray coverage band-risk stripes (no width model)'
        self.process = process
        fr = (process or {}).get('friction') if isinstance(process, dict) else None
        op = fr.get('operating') if isinstance(fr, dict) else None
        if isinstance(op, dict) and isinstance(op.get('film_ratio'), (int, float)):
            self.film_ratio = op['film_ratio']
            self.film_basis = 'tribology inlet film at the operating point'
        elif screens is not None and isinstance(screens.get('film_regime'), dict):
            self.film_ratio = screens['film_regime']['film_ratio']
            self.film_basis = 'lubrication-screen inlet film (Wilson & Walowit form)'

    def model_bands_at_positions(self):
        if not self.steady_bands:
            return []
        if self.positions:
            return [b for b in self.steady_bands
                    if any(abs(b[0] - p) <= self.tol for p in self.positions)]
        return list(self.steady_bands)


def _tension_release_rules(facts, states, label, not_assessable=None):
    """Tension-release rules (coordinator follow-up to SPEC6 6.7). ``states``: (in-mill state,
    state after tension release) of the model bands. Observation 'visible only after tension
    release' true: SUPPORTS moderate with a band LATENT in the mill and MANIFEST after release,
    CONTRADICTS weak with a band MANIFEST in the mill; false: SUPPORTS moderate with a band
    MANIFEST in the mill, CONTRADICTS weak with only in-mill-LATENT bands. Plus the unchanged
    rule: MANIFEST (in the mill) band with appearance loose_or_buckle SUPPORTS moderate."""
    obs = facts.obs
    out = []
    crit = f'visible only after tension release vs {label}'
    exp = 'true: LATENT in mill and MANIFEST after release; false: MANIFEST in mill'
    v = obs['visible_only_after_tension_release']
    mill = [m for m, _ in states]
    txt_states = ', '.join(f'{m} / {r}' for m, r in states) or 'no band'
    if v is None:
        out.append(ev(crit, 'not observed', exp, 'NOT_OBSERVED'))
    elif not states and not_assessable:
        out.append(ev(crit, f'{str(v).lower()}; model not assessable ({not_assessable})', exp,
                      'NEUTRAL', basis='model not assessable'))
    elif not states:
        out.append(ev(crit, f'{str(v).lower()}; model no band', exp, 'NEUTRAL'))
    elif v and any(m == 'LATENT_UNDER_TENSION' and r == 'MANIFEST_AFTER_TENSION_RELEASE'
                   for m, r in states):
        out.append(ev(crit, f'true; model {txt_states}', exp, 'SUPPORTS', 'moderate'))
    elif v and any(m == 'MANIFEST_BUCKLE' for m in mill):
        out.append(ev(crit, f'true; model {txt_states}', exp, 'CONTRADICTS', 'weak'))
    elif not v and any(m == 'MANIFEST_BUCKLE' for m in mill):
        out.append(ev(crit, f'false; model {txt_states}', exp, 'SUPPORTS', 'moderate'))
    elif not v and all(m == 'LATENT_UNDER_TENSION' for m in mill):
        out.append(ev(crit, f'false; model {txt_states}', exp, 'CONTRADICTS', 'weak'))
    else:
        out.append(ev(crit, f'{str(v).lower()}; model {txt_states}', exp, 'NEUTRAL'))
    crit2 = f'loose / buckle appearance vs MANIFEST {label}'
    a = obs['appearance']
    if a is None:
        out.append(ev(crit2, 'not observed', 'MANIFEST model band and loose_or_buckle',
                      'NOT_OBSERVED'))
    elif a == 'loose_or_buckle' and any(m == 'MANIFEST_BUCKLE' for m in mill):
        out.append(ev(crit2, f'{a}; model MANIFEST', 'MANIFEST model band and loose_or_buckle',
                      'SUPPORTS', 'moderate'))
    else:
        out.append(ev(crit2, f'{a}; model {", ".join(mill) or "no band"}',
                      'MANIFEST model band and loose_or_buckle', 'NEUTRAL'))
    return out


def _spacing_multiple(facts, pitch, criterion, weight, pitch_name):
    if facts.gaps is None:
        return ev(criterion, 'spacing not observed', f'integer multiple of the {pitch_name}',
                  'NOT_OBSERVED')
    if pitch is None:
        return ev(criterion, f'gaps {_fmt_pos(facts.gaps)}', f'{pitch_name} not known',
                  'NOT_OBSERVED', basis='input')
    m = spacing_match(facts.gaps, pitch)
    obs_txt = f'gaps {_fmt_pos(facts.gaps)} ({facts.gap_basis}); {pitch_name} {pitch:.4g} m'
    if m['status'] == 'ALL_GAPS_MATCH':
        return ev(criterion, obs_txt + f'; multiples {m["multiples"]}',
                  f'integer multiple of the {pitch_name}', 'SUPPORTS', weight)
    return ev(criterion, obs_txt + f'; {m["status"]}', f'integer multiple of the {pitch_name}',
              'NEUTRAL')


def _fmt_intervals(stripes):
    return ', '.join(f'{s["start_m"]:.4g}-{s["end_m"]:.4g} m' for s in stripes) or 'none'


def _interval_hits(f):
    """Observed positions inside a band-risk interval widened by the tolerance: the same
    ``band_signatures.match_band_positions`` the coolant screen uses, so they cannot disagree."""
    from .band_signatures import match_band_positions
    m = match_band_positions(f.l1_intervals, f.positions, f.tol)
    return [r['observed_position_m'] for r in m['matches'] if r['matched_stripes']]


def _interval_match_ev(f, crit):
    hits = _interval_hits(f)
    model = f'model intervals {_fmt_intervals(f.l1_intervals)} ({f.l1_source})'
    exp = f'inside an interval widened by {f.tol:.3g} m ({f.tol_basis})'
    if hits:
        return ev(crit, f'observed {_fmt_pos(hits)} inside {model}', exp, 'SUPPORTS', 'strong')
    return ev(crit, f'no observed position inside or within {f.tol:.3g} m of {model}', exp,
              'CONTRADICTS', 'weak')


def _interval_pred(f):
    # keys only where the interval matching was used, so results without observed positions
    # (the v1 demos) keep their exact content
    if not f.l1_intervals or not f.positions:
        return {}
    return {'model_intervals_m': [[s['start_m'], s['end_m']] for s in f.l1_intervals],
            'position_match_basis': 'interval (band-risk stripe bounds widened by the '
                                    'tolerance), as screens.band_position_match'}


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
    elif f.l1_intervals:
        e.append(_interval_match_ev(f, crit))
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
    if not f.width_ran and not f.width_ok:
        e.append(ev(crit, 'no width model', 'latent or manifest band', 'NOT_OBSERVED',
                    basis='input'))
    elif not f.shape_ok:
        e.append(ev(crit, f'model not assessable ({f.model_reason})', 'latent or manifest band',
                    'NEUTRAL', basis='model not assessable'))
    elif not f.positions:
        e.append(ev(crit, 'positions not observed', 'latent or manifest band', 'NOT_OBSERVED'))
    else:
        reported = [(x, s, r) for x, s, r in bands if s != 'BELOW_REPORTING_THRESHOLD']
        if reported:
            e.append(ev(crit, '; '.join(f'{x:.4g} m: {s} / {r}' for x, s, r in reported),
                        'latent or manifest band', 'SUPPORTS', 'moderate', 'model'))
        else:
            e.append(ev(crit, 'no model stripe band at the observed positions',
                        'latent or manifest band', 'NEUTRAL', basis='model'))
    states = [(s, r) for _, s, r in bands if s != 'BELOW_REPORTING_THRESHOLD']
    e += _tension_release_rules(f, states, 'steady model band',
                                None if f.shape_ok else f.model_reason)
    e.append(_worse_thin(o, 'weak', 'relative thickness error and buckling stress'))
    e.append(_choice(o, 'faces', 'faces', 'both', {'both': ('SUPPORTS', 'weak')}))
    # SPEC9 9.4 extensions [D]: a thermal stripe follows heat input slowly (minutes), so speed
    # tracking neither supports nor contradicts it; a band that goes with wiper cleaning points
    # to wiper debris rather than to the spray
    e.append(_rule(o, 'tracks_speed_changes', 'tracks speed changes',
                   'n/a (a thermal stripe follows the heat input slowly)', None, None))
    e.append(_rule(o, 'changes_after_roll_wiper_cleaning', 'changes after roll wiper cleaning',
                   'false (a wiper-debris band would)', ('CONTRADICTS', 'weak'), None))
    pred = {'model_positions_m': f.l1_predicted, 'model_position_source': f.l1_source,
            'position_tolerance_m': f.tol, **_interval_pred(f), 'steady_model_bands': [
                {'position_m': x, 'state': s, 'state_after_tension_release': r}
                for x, s, r in f.steady_bands]}
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
    lives = [(x['visible_time_s'], x['visible_time_basis']) for x in f.events
             if x.get('visible_time_s')]
    bounds = [x['visible_time_lower_bound_s'] for x in f.events
              if x.get('visible_time_lower_bound_s') and not x.get('visible_time_s')]
    crit = 'intermittent duration vs model visible time'
    no_shape = [x for x in f.events if x.get('shape_error')]
    if d is None:
        e.append(ev(crit, 'not observed', 'within 0.3-3 x model visible time', 'NOT_OBSERVED'))
    elif f.events and not lives and not bounds and len(no_shape) == len(f.events):
        e.append(ev(crit, f'{d:.4g} s; model visible time not assessable '
                    f'({no_shape[0]["shape_error"]})', 'within 0.3-3 x model visible time',
                    'NEUTRAL', basis='model not assessable'))
    elif not lives and bounds:
        e.append(ev(crit, f'{d:.4g} s; model visible time beyond the simulated recovery (> '
                    f'{", ".join(f"{b:.4g} s" for b in bounds)})',
                    'within 0.3-3 x model visible time', 'NEUTRAL', basis='model'))
    elif lives:
        ok = [L for L, _ in lives if 0.3 * L <= d <= 3 * L]
        e.append(ev(crit, f'{d:.4g} s; model visible time '
                    + ', '.join(f'{L:.4g} s ({b})' for L, b in lives),
                    'within 0.3-3 x model visible time', 'SUPPORTS' if ok else 'NEUTRAL',
                    'moderate' if ok else None, 'model'))
    elif f.events:
        # review finding: simulated events that never make a reportable band (or a mix of
        # those and shape errors) are model output, not 'no model events': no literature
        # support; the model amplitude is not trusted enough to contradict either
        def state(x):
            if x.get('shape_error'):
                return f'shape error: {x["shape_error"]}'
            return (f'{x.get("peak_state_with_feedback")} in the mill / '
                    f'{x.get("peak_state_after_tension_release")} after release')
        txt = '; '.join(f'{x.get("label") or "event " + str(x.get("index"))}: {state(x)}'
                        for x in f.events)
        e.append(ev(crit, f'{d:.4g} s; the supplied model events produce no reportable band '
                    f'(no visible time) - {txt}', 'within 0.3-3 x model visible time',
                    'NEUTRAL', basis='model'))
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
    states = [(x['peak_state_with_feedback'], x['peak_state_after_tension_release'])
              for x in f.events
              if x.get('peak_state_with_feedback') not in (None, 'BELOW_REPORTING_THRESHOLD')]
    e += _tension_release_rules(f, states, 'event peak band',
                                f'shape chain: {no_shape[0]["shape_error"]}'
                                if f.events and len(no_shape) == len(f.events) else
                                (f.model_reason if f.width_ran and not f.width_ok else None))
    pred = {'event_positions_m': f.event_positions,
            'events': [{k: x.get(k) for k in ('index', 'label', 'monitor_position_m',
                                              'peak_deviation_m',
                                              'time_to_manifest_threshold_s', 'band_life_s',
                                              'band_life_basis', 'visible_time_s',
                                              'visible_time_basis', 'peak_state_with_feedback',
                                              'peak_state_after_tension_release')}
                       for x in f.events],
            'literature_band_life_s': list(LITERATURE_BAND_LIFE_S)}
    return e, pred


def _h_roll_surface(f):
    o = f.obs
    e = [_orientation(o)]
    ch, dis = o['positions_change_after_work_roll_change'], o['disappears_after_work_roll_change']
    crit = 'positions change / band disappears after work-roll change'
    # SPEC9 9.4: backup-roll lines are printed through the work roll onto the strip, so with a
    # band that disappears after a BACKUP-roll change, persistence across a work-roll change
    # is expected for this hypothesis and must not count as a strong contradiction
    bur = o['disappears_after_backup_roll_change'] is True
    why = ('; band disappeared after a backup-roll change (backup-roll lines printed through '
           'the work roll persist across a work-roll change), so downgraded to weak'
           if bur else '')
    if ch is not None:
        e.append(ev(crit, f'positions change: {str(ch).lower()}' + ('' if ch else why), 'true',
                    'SUPPORTS' if ch else 'CONTRADICTS',
                    'strong' if ch or not bur else 'weak'))
    elif dis is not None:
        e.append(ev(crit, f'disappears after work-roll change: {str(dis).lower()}'
                    + ('' if dis else why), 'true', 'SUPPORTS' if dis else 'CONTRADICTS',
                    'strong' if dis else ('weak' if bur else 'moderate')))
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
    # SPEC9 9.4 extensions [V S25, S17]: wiper debris, wide coil after narrow, backup-roll lines
    e.append(_rule(o, 'changes_after_roll_wiper_cleaning', 'changes after roll wiper cleaning',
                   'true (wiper debris)', ('SUPPORTS', 'strong'), ('CONTRADICTS', 'weak')))
    e.append(_rule(o, 'appeared_after_narrower_coil', 'appeared after a narrower coil',
                   'true (wide coil rolled after a narrow one)', ('SUPPORTS', 'strong'), None))
    e.append(_rule(o, 'disappears_after_backup_roll_change',
                   'disappears after backup-roll change',
                   'true (backup-roll lines printed through the work roll)',
                   ('SUPPORTS', 'moderate'), None))
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
    # SPEC9 9.1: without a bite the exit ridge is the proportional-transfer estimate, so its
    # coil result supports only weakly and never contradicts
    estimate = any(r.get('transfer_basis') == 'PROPORTIONAL_TRANSFER_LIMIT_NO_BITE'
                   for r in f.ridges if r.get('coil'))
    note = ' (exit ridge from the proportional-transfer estimate, no bite)' if estimate else ''
    if not coils:
        e.append(ev(crit, 'no ridge with coil data', 'RIDGE_YIELDS_STRIP', 'NOT_OBSERVED',
                    basis='input'))
    elif any(c['status'] == 'RIDGE_YIELDS_STRIP' for c in coils):
        e.append(ev(crit, ', '.join(c['status'] for c in coils) + note, 'RIDGE_YIELDS_STRIP',
                    'SUPPORTS', 'weak' if estimate else 'moderate', 'model'))
    elif estimate:
        e.append(ev(crit, ', '.join(c['status'] for c in coils) + note, 'RIDGE_YIELDS_STRIP',
                    'NEUTRAL', basis='model not assessable'))
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
    # SPEC9 9.4 extensions [V S25]: creasing from ironing-roll pressure imbalance; creasing
    # possible at any exit gauge below 50 um; troughs need tension (a crease from a local loose
    # band is the exception, so the contradiction stays weak)
    e.append(_rule(o, 'changes_with_ironing_roll_pressure',
                   'changes with ironing-roll pressure', 'true', ('SUPPORTS', 'moderate'), None))
    h = f.exit_thickness
    gauge = ev('exit gauge (creasing possible below 50 um)', f'{h * 1e6:.4g} um',
               '< 50 um', 'SUPPORTS' if h < 50e-6 else 'NEUTRAL',
               'weak' if h < 50e-6 else None, 'input')
    e.append(_rule(o, 'worse_at_lower_tension', 'worse at lower tension',
                   'false (troughs need tension; a crease from a loose band is the exception)',
                   ('CONTRADICTS', 'weak'), None))
    e.append(_gate_gauge_support(e, gauge))
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
    k_regime = len(e)
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
    # SPEC9 9.4 extensions: a friction / oil-film band (no roll bump) tracks speed [V S17 for
    # the roughness cause; mechanism D]; a film comparable to the roughness makes friction
    # sensitive to local differences [V S11 for the film ratios; rule D]
    e.append(_rule(o, 'tracks_speed_changes', 'tracks speed changes', 'true',
                   ('SUPPORTS', 'strong'), ('CONTRADICTS', 'weak')))
    crit = 'film ratio at the operating point (0.3-3: friction sensitive to local differences)'
    lam = f.film_ratio
    k_film = len(e)
    if lam is None:
        e.append(ev(crit, 'no lubrication or tribology data', '0.3-3', 'NOT_OBSERVED',
                    basis='input'))
    else:
        ok = 0.3 <= lam <= 3
        e.append(ev(crit, f'Lambda = {lam:.3g} ({f.film_basis})', '0.3-3',
                    'SUPPORTS' if ok else 'NEUTRAL', 'weak' if ok else None, 'model'))
    e.append(_rule(o, 'changes_with_exit_air_blowoff', 'changes with exit air blow-off',
                   'n/a', None, None))
    # SPEC9 rule change (same gate as the foil gauge items): the operating-point regime and
    # film ratio describe the whole pass, not a band; at foil gauge they hold on practically
    # every pass, so they count only with a band-specific supporting observation
    for k in (k_regime, k_film):
        e[k] = _gate_gauge_support(e, e[k])
    return e, {'regime_at_operating_point': regime, 'exit_temperature_above_limit': hot,
               'film_ratio_at_operating_point': lam, 'film_ratio_basis': f.film_basis}


GAUGE_GATE_NOTE = ('; counted only with a band-specific supporting observation (rule change, '
                   'SPEC9 review: this case-wide quantity is shared by every band of the pass, '
                   'so on its own it made this hypothesis lead from the orientation alone)')


def _gate_gauge_support(e, item):
    """SPEC9 rule change: a SUPPORTS from a case-wide quantity (the exit gauge, basis 'input';
    the operating-point film ratio / tribology regime, basis 'model') counts only when
    the hypothesis also has a SUPPORTS from a plant observation other than the orientation
    (shared by the whole lengthwise family); otherwise it is reported as NEUTRAL. Gauge
    contradictions are kept."""
    if item['verdict'] != 'SUPPORTS':
        return item
    specific = any(x['verdict'] == 'SUPPORTS' and x['basis'] == 'observation'
                   and x['criterion'] != 'orientation' for x in e)
    if specific:
        return item
    return ev(item['criterion'], item['observed'] + GAUGE_GATE_NOTE, item['expected'],
              'NEUTRAL', basis=item['basis'])


def _tl_published():
    """(pitch low, pitch high, onset gauge, source id, read status) from the catalogue."""
    vals = band_products.TENSION_LINES.values
    pitch = next(v for v in vals if v.unit == 'm' and v.low is not None)
    onset = next(v for v in vals if v.low is None)
    sid = band_products.TENSION_LINES.sources[0]
    return pitch.low, pitch.high, onset.high, sid, band_products.sources()[sid].read_status


def _h_tension_lines(f):
    """Foil tension lines: a PUBLISHED DESCRIPTION, not a model (SPEC9 9.4, revised in SPEC12
    B3 from the catalogue's ``TENSION_LINES`` [BF-S21, excerpt]: longitudinal stripes at
    5-20 mm pitch that appear below 15 um and worsen as gauge falls; also [V S27, S28]; rule
    weights D)."""
    o = f.obs
    e = [_orientation(o)]
    p_lo, p_hi, onset, sid, rs = _tl_published()
    cite = f'[{sid}, {rs}]'
    crit = f'band spacing {p_lo * 1e3:.3g}-{p_hi * 1e3:.3g} mm, regular {cite}'
    exp = (f'regular {p_lo * 1e3:.3g}-{p_hi * 1e3:.3g} mm (published pitch); 3-30 mm or '
           'irregular weak; > 60 mm contradicts weakly')
    if f.gaps is None:
        e.append(ev(crit, 'spacing not observed', exp, 'NOT_OBSERVED'))
    else:
        stated = o['band_spacing_m'] is not None
        sp_ = o['band_spacing_m'] if stated else sum(f.gaps) / len(f.gaps)
        regular = stated or bool(f.spacing and f.spacing.get('regular'))
        txt = (f'{sp_ * 1e3:.4g} mm ({f.gap_basis}'
               + ('' if stated else f', {"regular" if regular else "irregular"} gaps') + ')')
        if p_lo <= sp_ <= p_hi and regular:
            e.append(ev(crit, txt, exp, 'SUPPORTS', 'strong'))
        elif 0.003 <= sp_ <= 0.030:
            e.append(ev(crit, txt, exp, 'SUPPORTS', 'weak'))
        elif sp_ > 0.060:
            e.append(ev(crit, txt, exp, 'CONTRADICTS', 'weak'))
        else:
            e.append(ev(crit, txt, exp, 'NEUTRAL'))
    h = f.exit_thickness
    crit = f'exit gauge (tension lines appear below {onset * 1e6:.3g} um {cite})'
    txt = f'{h * 1e6:.4g} um'
    exp = (f'< {onset * 1e6:.3g} um moderate [{sid}, S27]; {onset * 1e6:.3g}-30 um weak '
           '[S28]; > 100 um contradicts')
    if h < onset:
        gauge = ev(crit, txt, exp, 'SUPPORTS', 'moderate', 'input')
    elif h <= 30e-6:
        gauge = ev(crit, txt, exp, 'SUPPORTS', 'weak', 'input')
    elif h > 100e-6:
        gauge = ev(crit, txt, exp, 'CONTRADICTS', 'moderate', 'input')
    else:
        gauge = ev(crit, txt, exp, 'NEUTRAL', basis='input')
    k_gauge = len(e)
    e.append(gauge)
    e.append(_rule(o, 'worse_at_lower_tension', 'worse at lower tension', 'true',
                   ('SUPPORTS', 'strong'), ('CONTRADICTS', 'strong')))
    crit = 'changes with tension'
    if o['worse_at_lower_tension'] is not None:
        v = o['changes_with_tension']
        e.append(ev(crit, 'not observed' if v is None else str(v).lower(),
                    'true (only used when worse_at_lower_tension is not observed)',
                    'NOT_OBSERVED' if v is None else 'NEUTRAL'))
    else:
        e.append(_rule(o, 'changes_with_tension', crit, 'true', ('SUPPORTS', 'moderate'), None))
    e.append(_rule(o, 'changes_with_ironing_roll_pressure',
                   'changes with ironing-roll pressure', 'true', ('SUPPORTS', 'moderate'), None))
    e.append(_rule(o, 'changes_with_exit_air_blowoff', 'changes with exit air blow-off', 'true',
                   ('SUPPORTS', 'moderate'), None))
    e.append(_rule(o, 'positions_repeat_across_coils', 'positions repeat across coils',
                   'false', None, ('SUPPORTS', 'weak')))
    e.append(_choice(o, 'appearance', 'appearance', 'gloss_or_shade or crease_or_flute',
                     {'gloss_or_shade': ('SUPPORTS', 'weak'),
                      'crease_or_flute': ('SUPPORTS', 'weak'),
                      'loose_or_buckle': ('CONTRADICTS', 'weak'),
                      'stain': ('CONTRADICTS', 'weak')}))
    e.append(_worse_thin(o, 'weak', 'onset below about 15-30 um reported'))
    e[k_gauge] = _gate_gauge_support(e, e[k_gauge])
    return e, {'model': 'NONE: rule-based hypothesis, the tool has no physical model of '
                        'tension lines (5-20 mm pitch reported, vanishing above a threshold '
                        'tension)',
               'reported_pitch_m': [0.005, 0.020],
               'reported_onset_exit_gauge_m': [15e-6, 30e-6],
               'case_exit_thickness_m': h}


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
    ('heat_streak_or_film_variation',
     'Heat streak / friction or oil-film band (no roll bump)',
     'Local oil-film or friction variation across the width: milky heat streaks that wander in '
     'width and position (QCA-1), or, in foil where the oil film is comparable to the '
     'roughness, a cross-width difference in roughness or oil film that gives a flatness band '
     'without any geometric roll bump and tracks speed changes [V S11, S17; mechanism D].',
     'Compare band appearance with oil temperature and speed (does the band appear, move or '
     'fade with a speed change?); check whether the bands wander between coils; measure the '
     'work-roll roughness across the barrel.',
     ('lower the oil inlet temperature', 'increase coolant flow', 'reduce speed',
      'regrind for uniform roll roughness')),
    ('oil_carryover_drips_or_stain', 'Oil carry-over, drips or stain',
     'Coolant carried past the wipers, drips, or staining seen after annealing.',
     'Anneal a sample and look for stain; inspect wipers and drip shields.',
     ('repair wipers / air knives', 'check drip shields', 'adjust oil filtration')),
    ('foil_tension_lines', 'Foil tension lines (fine lengthwise stripes, worse at low tension)',
     'PUBLISHED DESCRIPTION, NOT A MODEL: longitudinal stripes at 5-20 mm pitch that appear '
     'below 15 um and worsen as gauge falls; drivers tension, roll roughness, roll parallelism, '
     'roll pressure and pass reduction [BF-S21, excerpt of a trade report of a producer talk]; '
     'wider and more visible at low strip tension and vanishing above a threshold tension '
     '[V S27, S28]; listed with ridge marks as typical battery-foil flatness defects [V S5]. '
     'The tool has no physical model of them.',
     'Raise the exit tension in steps and note the tension at which the lines vanish; vary the '
     'ironing-roll pressure per side and the exit air blow-off one at a time; check roll '
     'parallelism.',
     ('raise front (exit) tension (risks ridging)', 'adjust ironing-roll pressure per side',
      'reduce or redirect the exit air blow-off', 'check roll parallelism',
      'raise work-roll roughness')),
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
    'foil_tension_lines': _h_tension_lines,
}


MEASUREMENT_TOPICS = ('Spray footprint check', 'coolant valve states', 'span tension',
                      'outside-profile scan', 'three consecutive coils')


def measurement_topic(line):
    """Key phrase of a lengthwise measurement line (used to avoid repeating a topic)."""
    return next((t for t in MEASUREMENT_TOPICS if t in line), None)


FOIL_MEASUREMENTS = (
    ('worse_at_lower_tension', 'Step the exit tension and note whether (and at which tension) '
                               'the bands fade.'),
    ('changes_with_ironing_roll_pressure', 'Change the ironing-roll pressure (per side) and, '
                                           'separately, the exit air blow-off, one at a time.'),
    ('changes_after_roll_wiper_cleaning', 'Clean the roll wipers and note whether the bands '
                                          'change.'),
    ('tracks_speed_changes', 'Note whether the bands appear, move or fade when the mill speed '
                             'changes.'),
    ('appeared_after_narrower_coil', 'Record whether the bands started when a wider coil '
                                     'followed a narrower one.'),
    (None, 'Compare the online shapemeter flatness with the offline sag of a sample laid flat '
           '(front tension masks the true shape at foil gauge).'))


def lengthwise_next_measurements(obs, exit_thickness_m=None):
    """Lengthwise measurement lines; with an exit gauge below 100 um (SPEC9 9.4) also the
    foil lines whose observation is still null (and the online/offline comparison)."""
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
    if exit_thickness_m is not None and exit_thickness_m < FOIL_GAUGE_M:
        for key, line in FOIL_MEASUREMENTS:
            if key is None or obs.get(key) is None or (
                    key == 'changes_with_ironing_roll_pressure'
                    and obs.get('changes_with_exit_air_blowoff') is None):
                lines.append(line)
    return lines
