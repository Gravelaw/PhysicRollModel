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
import sys

from . import band_products
from . import roll_thermal as rt
from . import strip_shape as ss
from .band_process import (failed, int_list, keys, not_supplied, num, num_list,
                           use_computed_heat_partition,
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
    'lateral_compressive_stress_pa': None, 'shape_inputs': None,
    # SPEC17 A5 / X3: arc of the circumference the spray wets [rad]; used only to express the
    # circumferential-mean spray coefficient on a jet-zone basis in thermal_check, never in the
    # roll thermal model
    'spray_wetted_arc_rad': None,
    # SPEC17 A1 / G6: a supplied strip temperature scan across the width (not computed)
    'strip_temperature': None,
    # SPEC17 BT-G4 (screening version): friction / film stripes as a second band source
    'friction_stripe_screen': None,
    # SPEC17 G13: a measured roll ground profile (radius deviation) through the existing transfer
    'roll_ground_profile': None,
    # SPEC18 package 10 (A4, G8): angular layout of sprays and backup contact for the roll
    # surface cycle within one revolution
    'circumferential_layout': None}
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


LAYOUT_WHERE = 'width_model.circumferential_layout'
LAYOUT_MAX_SPRAY_ARCS = 6
LAYOUT_ARC_TOL_RAD = 1e-6


def _layout_region(where, r, extra=()):
    keys(where, r, ('start_rad', 'arc_rad') + tuple(extra))
    start = num(f'{where}.start_rad', r['start_rad'])
    arc = num(f'{where}.arc_rad', r['arc_rad'])
    if not 0 <= start < 2 * math.pi:
        raise ValueError(f'{where}.start_rad must be in [0, 2*pi)')
    if not arc > 0:
        raise ValueError(f'{where}.arc_rad must be > 0')
    if start + arc > 2 * math.pi + 1e-12:
        raise ValueError(f'{where}: start_rad + arc_rad ({start + arc:.6g} rad) exceeds one '
                         'revolution (2*pi): the region would pass the bite')
    return {'start_rad': start, 'arc_rad': arc}


def validate_circumferential_layout(lay, wetted_arc=None):
    """SPEC18 package 10: ``{"spray_arcs": [{"start_rad", "arc_rad"}], "backup_contact": null |
    {"start_rad", "arc_rad", "conductance_w_m2k", "backup_surface_temperature_k"},
    "provenance"}``; angles in the direction of rotation from the bite exit, in [0, 2*pi);
    regions sorted, not overlapping one another (the bite is checked against the case-pass
    bite in the section)."""
    if lay is None:
        return None
    w = LAYOUT_WHERE
    keys(w, lay, ('spray_arcs', 'provenance'), ('backup_contact',))
    prov = lay['provenance']
    if not isinstance(prov, str) or not prov.strip():
        raise ValueError(f'{w}.provenance must be a nonempty string')
    arcs = lay['spray_arcs']
    if not isinstance(arcs, list) or not 1 <= len(arcs) <= LAYOUT_MAX_SPRAY_ARCS:
        raise ValueError(f'{w}.spray_arcs must be a list of 1 to {LAYOUT_MAX_SPRAY_ARCS} arcs')
    sprays = [_layout_region(f'{w}.spray_arcs[{i}]', a) for i, a in enumerate(arcs)]
    regions = [(f'spray arc {i}', r) for i, r in enumerate(sprays)]
    bc = lay.get('backup_contact')
    backup = None
    if bc is not None:
        where = f'{w}.backup_contact'
        backup = _layout_region(where, bc, ('conductance_w_m2k', 'backup_surface_temperature_k'))
        backup['conductance_w_m2k'] = num(f'{where}.conductance_w_m2k', bc['conductance_w_m2k'],
                                          positive=True)
        if backup['conductance_w_m2k'] > 1e9:
            raise ValueError(f'{where}.conductance_w_m2k must be <= 1e9 W/m2K')
        backup['backup_surface_temperature_k'] = num(
            f'{where}.backup_surface_temperature_k', bc['backup_surface_temperature_k'],
            lo=200.0, hi=700.0)
        regions.append(('backup contact', backup))
    for i in range(len(sprays) - 1):
        if sprays[i + 1]['start_rad'] < sprays[i]['start_rad']:
            raise ValueError(f'{w}.spray_arcs must be sorted by start_rad')
    for i, (na, a) in enumerate(regions):
        for nb, b in regions[i + 1:]:
            lo = max(a['start_rad'], b['start_rad'])
            hi = min(a['start_rad'] + a['arc_rad'], b['start_rad'] + b['arc_rad'])
            if hi > lo + 1e-12:
                raise ValueError(
                    f'{w}: {na} ({a["start_rad"]:.4g} to {a["start_rad"] + a["arc_rad"]:.4g} '
                    f'rad) overlaps {nb} ({b["start_rad"]:.4g} to '
                    f'{b["start_rad"] + b["arc_rad"]:.4g} rad)')
    total = sum(r['arc_rad'] for r in sprays)
    if wetted_arc is not None and abs(total - wetted_arc) > LAYOUT_ARC_TOL_RAD:
        raise ValueError(f'{w}: the spray arcs must add up to width_model.spray_wetted_arc_rad '
                         f'({total:.6g} rad against {wetted_arc:.6g} rad)')
    return {'spray_arcs': sprays, 'backup_contact': backup, 'provenance': prov}


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
    arc = w.get('spray_wetted_arc_rad')
    if arc is not None:
        arc = num('width_model.spray_wetted_arc_rad', arc)
        if not 0 < arc <= 2 * math.pi:
            raise ValueError('width_model.spray_wetted_arc_rad must be in (0, 2*pi]')
    out['spray_wetted_arc_rad'] = arc
    out['strip_temperature'] = _validate_strip_temperature(w.get('strip_temperature'),
                                                           roll['barrel_length_m'])
    out['friction_stripe_screen'] = _validate_friction_screen(w.get('friction_stripe_screen'),
                                                              roll['barrel_length_m'])
    out['roll_ground_profile'] = _validate_roll_profile(w.get('roll_ground_profile'),
                                                        roll['barrel_length_m'])
    out['circumferential_layout'] = validate_circumferential_layout(
        w.get('circumferential_layout'), arc)
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


def band_state_at(result, x):
    """In-mill and after-release state of the with-feedback band containing ``x`` in a
    ``_tsf`` result (the rule of ``stripe_states``: the band whose [start, end] contains x,
    the largest |peak| when two do; None outside every band)."""
    b = _band_at(result['bands'], x)
    return None if b is None else (b['state'], b['state_after_tension_release'])


POSITION_STATES = {'mill': (0, 'MANIFEST_BUCKLE'),
                   'released': (1, 'MANIFEST_AFTER_TENSION_RELEASE')}


def onset_search(z, shape, sp, kind='mill', hi=None, lo=None, position=None):
    """Smallest factor s with a MANIFEST band (kind 'mill': in the mill; 'released': after
    tension release) for s*shape, decided from the with-feedback result only.

    Returns ``{'status', 'scale', 'domain_limit_scale'}``: ``FOUND`` with the onset scale
    (geometric bisection to ONSET_RELATIVE_TOL); ``NOT_REACHED_WITHIN_SEARCH_CEILING`` when the
    band is still latent at ``hi``; ``NOT_REACHED_BEFORE_FEEDBACK_MODEL_DOMAIN_LIMIT`` when the
    with-feedback calculation itself leaves its domain (ValueError) before any manifest band,
    with the largest valid scale in ``domain_limit_scale`` (never an onset). An undefined
    compliance-only bound does not decide anything (review finding: it used to count as
    manifest). ``lo``: a scale known not to exceed the onset (bracket). ``position``: decide
    from the band containing that position only (``band_state_at``, the rule of
    ``stripe_states``) instead of any band of the profile (default)."""
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
        if position is None:
            return r[key] == value
        st = band_state_at(r, position)
        i, val = POSITION_STATES[kind]
        return st is not None and st[i] == val
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


def position_manifest(z, shape, sp, kind, scale, position):
    """True / False: the band at ``position`` is manifest (kind) for scale*shape; None when the
    with-feedback calculation leaves its domain."""
    try:
        r = _tsf(z, [scale * v for v in shape], sp)
    except ValueError:
        return None
    st = band_state_at(r, position)
    i, val = POSITION_STATES[kind]
    return st is not None and st[i] == val


def onset_scale(z, shape, sp, kind='mill', hi=None, lo=None):
    """Onset scale of ``onset_search`` (None unless FOUND)."""
    return onset_search(z, shape, sp, kind, hi, lo)['scale']


def manifest_onset_scale(z, shape, sp, hi=None):
    return onset_scale(z, shape, sp, 'mill', hi)


def onsets(z, shape, sp, position=None):
    """In-mill and after-release onset scales on the coarse grid, plus the scale at which the
    linear-feedback peak reaches the reporting threshold (bands exist only above it). The
    reporting scale brackets the after-release onset from below (a band must be reported
    before it can buckle), the after-release onset brackets the in-mill one (tension only
    stabilises).

    ``position`` (review of 631195a): the onsets of the band AT that position (the rule of
    ``stripe_states``), so they pair with the states read there. A band elsewhere (the loose
    lanes beside an over-cooled stripe) no longer counts; the whole-profile onsets are kept
    under ``out['whole_profile']``. Where the band at the position is already manifest at
    the whole-profile onset the two are the same number (a hot stripe: unchanged results)."""
    zc, pc = coarse_grid(z, shape)
    out = {'mill': None, 'released': None, 'reporting': None}
    peak = max(abs(v) for v in pc)
    if peak <= 0:
        if position is not None:
            out['whole_profile'] = dict(out)
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
    if position is None:
        return out
    whole = dict(out)
    out = {'whole_profile': whole, 'position_m': position}
    # reporting: the band at the position is the same-sign lane of the linear-feedback I-unit
    # profile that contains it; it is reported once that lane's own peak exceeds the
    # threshold (linear below buckling). When that lane holds the profile peak this is the
    # whole-profile value (a hot stripe; the stripe of a restored nozzle when it is the
    # largest |I|)
    lin_i = _linear_feedback_i_units(lin, sp)
    zs = lin['z_m']
    j = min(range(len(zs)), key=lambda i: abs(zs[i] - position))
    sgn = lin_i[j] > 0
    a = b = j
    while a > 0 and (lin_i[a - 1] > 0) == sgn and lin_i[a - 1] != 0:
        a -= 1
    while b < len(zs) - 1 and (lin_i[b + 1] > 0) == sgn and lin_i[b + 1] != 0:
        b += 1
    li_x = max(abs(lin_i[i]) for i in range(a, b + 1))
    out['lane_m'] = [zs[a], zs[b]]
    if li_x > 0 and whole['reporting'] is not None and abs(li_x - li) <= 1e-9 * li:
        out['reporting'] = whole['reporting']   # the lane holds the profile peak
    else:
        out['reporting'] = None if li_x <= 0 else REFERENCE_STRIPE_HEIGHT_M / peak * thr / li_x
    lo_rel = None if out['reporting'] is None else out['reporting'] * (1 - 1e-6)
    for name in ('released', 'mill'):
        sc = whole[name]
        if sc is None:
            # no band of the profile is manifest within the search (or before the feedback
            # model's domain limit): neither is the band at the position
            out[name] = None
            if f'{name}_domain_limit' in whole:
                out[f'{name}_domain_limit'] = whole[f'{name}_domain_limit']
            continue
        if position_manifest(zc, pc, sp, name, sc, position):
            out[name] = sc                    # the band at the position is the first manifest
            continue
        lo_ = lo_rel if name == 'released' else (
            None if out['released'] is None else out['released'] * 0.999)
        lo_ = max(lo_ or 0.0, sc * (1 - 1e-6))
        r = onset_search(zc, pc, sp, name, lo=lo_, position=position)
        out[name] = r['scale']
        if r['status'] == ONSET_DOMAIN_LIMIT:
            out[f'{name}_domain_limit'] = r['domain_limit_scale']
        # bands elsewhere in the profile reach this state first (or alone): where, at their
        # onset (never fed to evidence; reported beside)
        try:
            rr = _tsf(zc, [sc * v for v in pc], sp)
        except ValueError:
            rr = None
        i, val = POSITION_STATES[name]
        where = [] if rr is None else [
            {'peak_position_m': b['peak_position_m'], 'start_m': b['start_m'],
             'end_m': b['end_m'], 'sense': b['sense']}
            for b in rr['bands'] if (b['state'], b['state_after_tension_release'])[i] == val
            and not b['start_m'] <= position <= b['end_m']]
        out[f'neighbour_{name}'] = {'scale': sc, 'bands': where}
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


def spray_layout(case):
    """The spray header and strip of a v2 case as the width section reads them (``_Thermal``,
    the same code path): nozzle positions on the barrel [m], the EFFECTIVE flow level of each
    nozzle (``nozzle_levels``, else 1.0, with every ``blocked_nozzle_indices`` entry at 0.0),
    the nozzle pitch and effective footprint width [m], the barrel length [m], and the strip
    centre, start and end on the barrel [m]. Raises ``ValueError`` for a case without a width
    model or with an invalid one (the width model's own validation messages)."""
    w = case.get('width_model')
    if w is None:
        raise ValueError('width_model is required for the spray layout')
    th = _Thermal(case, validate_width_model(w, case['pass']), 0.0, 0.0)
    return {'nozzle_positions_m': list(th.positions), 'nozzle_levels': list(th.levels),
            'nozzle_pitch_m': th.header.nozzle_pitch_m,
            'effective_footprint_width_m': th.header.effective_footprint_width_m,
            'barrel_length_m': th.length, 'strip_centre_m': th.centre,
            'strip_width_m': th.width, 'strip_start_m': th.centre - th.width / 2,
            'strip_end_m': th.centre + th.width / 2}


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


def _threshold_times(tw_times, tw_sdev, thr, sign, ts, te, tw):
    """(time to the threshold from the event start, fade time after the event end, time
    above) of the signed stripe history against a signed stripe-height threshold."""
    t_on = fade = None
    if thr is not None and thr * sign > 0:
        t_on = _first_cross(tw_times, tw_sdev, ts, abs(thr), up=True)
        if t_on is not None and max(te, t_on) <= tw + 1e-9:
            t_off = _first_cross(tw_times, tw_sdev, max(te, t_on), abs(thr), up=False)
            fade = None if t_off is None else t_off - te
    return (None if t_on is None else t_on - ts, fade,
            None if t_on is None or fade is None else te + fade - t_on)


NEIGHBOUR_TEXT = ('The over-cooled stripe of a restored nozzle is tight (short) at its own '
                  'position; the loose bands sit beside it, in the compensating lanes. The '
                  'thresholds, times and visible time of this event are those of the band at '
                  'the stripe; neighbour_bands_* give the lanes beside it (never used as '
                  'evidence).')


def event_metrics(z, prof, k_pk, sp, on, at_mon, times, dev, sel, ts, te, tw, end, peak_change,
                  duration, flags, scale=1.0, nozzle_x=None):
    """States, thresholds and threshold times of an event stripe, its peak profile and history
    scaled by ``scale`` (1 = the event as simulated). Shared by the event section and the
    thermal sensitivity block (SPEC14), so the two cannot drift. Everything is evaluated on
    the event's own sign (a restored nozzle gives a negative, over-cooled stripe). ``on`` are
    the onset scales of the unscaled profile (None: shape chain not assessable); thresholds are
    stripe heights and do not change with ``scale``."""
    row = {'scale': scale} if scale != 1.0 else {}
    pk_prof = [v * scale for v in prof]
    sdev = [v * scale for v in dev]
    shape = None
    if on is not None:
        try:
            shape = shape_levels(z, pk_prof, sp)
        except ValueError as exc:
            row['shape_error'] = str(exc)
    if shape is None:
        row['manifest_threshold_m'] = row['reporting_threshold_m'] = None
        row['released_threshold_m'] = None
        row['peak_state_with_feedback'] = row['peak_state_after_tension_release'] = None
    else:
        row['peak_shape'] = shape
        for name in ('mill', 'released', 'reporting'):
            key = {'mill': 'manifest', 'released': 'released', 'reporting': 'reporting'}[name]
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
    if scale != 1.0:
        row['peak_deviation_m'] = peak_change * scale
    sign = 1.0 if peak_change >= 0 else -1.0
    tw_times = [times[i] for i in sel]
    tw_sdev = [sign * sdev[i] for i in sel]
    for name in ('manifest', 'released', 'reporting'):
        t_to, fade, above = _threshold_times(tw_times, tw_sdev, row[f'{name}_threshold_m'],
                                             sign, ts, te, tw)
        row[f'time_to_{name}_threshold_s'] = t_to
        row[f'fade_time_below_{name}_threshold_s'] = fade
        row[f'time_above_{name}_threshold_s'] = above
    # review of 631195a: bands elsewhere in the profile that reach a manifest state before
    # (or without) the band at the stripe: reported beside, labelled, never evidence
    if shape is not None and on is not None:
        nb = {}
        for name, key in (('mill', 'manifest'), ('released', 'released')):
            n = on.get(f'neighbour_{name}')
            if not n:
                continue
            thr_n = n['scale'] * at_mon
            t_to, fade, above = _threshold_times(tw_times, tw_sdev, thr_n, sign, ts, te, tw)
            ref = z[k_pk] if nozzle_x is None else nozzle_x
            nb[key] = {'threshold_m': thr_n,
                       'band_offsets_from_event_nozzles_m': [
                           b['peak_position_m'] - ref for b in n['bands']],
                       'band_senses': [b['sense'] for b in n['bands']],
                       'time_to_threshold_s': t_to, 'time_above_threshold_s': above,
                       'reached_by_this_event': t_to is not None}
        if nb:
            row['neighbour_bands'] = nb
            row['neighbour_bands_note'] = NEIGHBOUR_TEXT
            words = []
            for key, what in (('manifest', 'buckle in the mill'),
                              ('released', 'show after tension release')):
                if key not in nb:
                    continue
                n = nb[key]
                where = ', '.join(f'{o:+.3g} m' for o in
                                  n['band_offsets_from_event_nozzles_m']) or 'beside it'
                words.append(
                    f'bands at {where} from the event nozzles would {what} once the stripe '
                    f'reaches {abs(n["threshold_m"]) * 1e6:.3g} um'
                    + (f', which this event reaches, for {n["time_above_threshold_s"]:.3g} s'
                       if n['time_above_threshold_s'] is not None else
                       ', which this event reaches' if n['reached_by_this_event'] else
                       ', which this event does not reach'))
            row['neighbour_bands_text'] = (
                'Whole profile: ' + '; '.join(words) + '. ' + NEIGHBOUR_TEXT)
    basis = ('manifest' if row['time_to_manifest_threshold_s'] is not None
             else 'reporting' if row['time_to_reporting_threshold_s'] is not None else None)
    row['band_life_basis'] = basis
    fade = row[f'fade_time_below_{basis}_threshold_s'] if basis else None
    row['band_life_s'] = None if (basis is None or fade is None) else duration + fade
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
    return row


def _events_section(th, sp, actual, events, shape_reason=None, scales=None):
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
        on = None
        try:
            if sp is None:
                raise ValueError(f'shape chain NOT_ASSESSABLE: {shape_reason}')
            # the onsets of the band AT the stripe peak (the position its states are read at)
            on = onsets(z, prof, sp, position=z[k_pk])
        except ValueError as exc:
            row['shape_error'] = str(exc)
        row.update(event_metrics(z, prof, k_pk, sp, on, at_mon, times, dev, sel, ts, te, tw,
                                 end, met['peak_change'], e['duration_s'], flags, 1.0,
                                 nozzle_x=x))
        # SPEC14: the same metrics at other roll heat shares (the model is linear in the roll
        # heat at a fixed spray coefficient: profile and history scale, thresholds do not)
        if scales:
            row['scaled'] = [{k2: v for k2, v in event_metrics(
                z, prof, k_pk, sp, on, at_mon, times, dev, sel, ts, te, tw, end,
                met['peak_change'], e['duration_s'], [], sc, nozzle_x=x).items()
                if k2 not in ('peak_shape', 'peak_stripe_states')} | {'scale': sc}
                for sc in scales]
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
                                       'profile scaled (onsets on a >= 10 mm grid), for the band '
                                       'at the stripe peak, where the peak states are read '
                                       '(bands elsewhere: neighbour_bands, never evidence)'}


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


# SPEC17 X12 [SS-S55 EX]: the isolated-span thresholds are conservative for wide foil
WIDE_FOIL_TROUGH_NOTE = (
    'Screening value from an isolated-span formula. For aluminium and copper foil below 25 um '
    'and wider than 0.6-1 m, wrinkles needed about 15 times the predicted roller misalignment '
    '[SS-S55 EX]: at foil gauge this threshold is conservative.')


def _validate_strip_temperature(s, barrel):
    if s is None:
        return None
    where = 'width_model.strip_temperature'
    keys(where, s, ('positions_m', 'temperature_k', 'provenance'),
         ('expansion_coefficient_per_k',))
    pos = s['positions_m']
    msg = f'{where}.positions_m must be >= 3 strictly increasing positions on the barrel'
    if not isinstance(pos, list) or len(pos) < 3:
        raise ValueError(msg)
    try:
        pos = [num(f'{where}.positions_m[{i}]', v) for i, v in enumerate(pos)]
    except ValueError:
        raise ValueError(msg) from None
    if any(b <= a for a, b in zip(pos, pos[1:])) or pos[0] < 0 or pos[-1] > barrel:
        raise ValueError(msg)
    temps = s['temperature_k']
    tmsg = f'{where}.temperature_k needs one value in [250, 700] K per position'
    if not isinstance(temps, list) or len(temps) != len(pos):
        raise ValueError(tmsg)
    try:
        temps = [num(f'{where}.temperature_k[{i}]', v, lo=250.0, hi=700.0)
                 for i, v in enumerate(temps)]
    except ValueError:
        raise ValueError(tmsg) from None
    a = s.get('expansion_coefficient_per_k')
    if a is not None:
        if isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) \
                or not 1e-6 < a < 1e-4:
            raise ValueError(f'{where}.expansion_coefficient_per_k must be in (1e-6, 1e-4) or '
                             'null')
        a = float(a)
    pv = s['provenance']
    if not isinstance(pv, str) or not pv.strip():
        raise ValueError(f'{where}.provenance must be a nonempty string')
    return {'positions_m': pos, 'temperature_k': temps, 'expansion_coefficient_per_k': a,
            'provenance': pv}


def _interp_held(xs, ys, x):
    """Linear interpolation; outside the scan the end value is held."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if xs[m] <= x:
            lo = m
        else:
            hi = m
    f = (x - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] + f * (ys[hi] - ys[lo])


ST_FLAG_SUPPLIED = 'STRIP_TEMPERATURE_TERM_SUPPLIED_PROFILE'
ST_FLAG_COVER = 'STRIP_TEMPERATURE_SCAN_DOES_NOT_COVER_STRIP'
ST_FLAG_NO_MECH = 'STRIP_TEMPERATURE_TERM_WITHOUT_MECHANICAL_PROFILE'
ST_FLAG_STATE = 'STRIP_TEMPERATURE_CHANGES_A_BAND_STATE'
ST_MEANINGS = {
    'mechanical': "the model's flatness as it is today (width.shape.steady, with feedback)",
    'as_measured_hot': 'what a shapemeter without temperature compensation senses; also the '
                       'state of the strip in the mill and of a sample released while hot',
    'after_cooling': 'equal to mechanical (no flatness controller in the model); stated so '
                     'that the reader sees it',
    'after_cooling_if_hot_reading_held_flat': (
        'BOUNDING CASE: if a flatness control had removed everything the hot shapemeter '
        'showed, the cold strip would carry the negative of the thermal term (a hot fibre '
        'becomes tight); needs the controller of G5 to be more than a bound')}
ST_LIMITATIONS = (
    'The temperature profile is an input, not computed (no per-width heat balance, gap A3).',
    'The thermal strain is not fed back into the bite or the exit-tension feedback.',
    'Where the mechanical profile was saturation-scaled (slack band) the sum is indicative.',
    'The temperature at the shapemeter is assumed equal to the scan.',
    'The after-cooling profile assumes no creep or set in the coil (gap A8).',
    'No flatness controller: the bounding case is a bound, not a prediction.')


def strip_temperature_section(case, w, shape_steady, z_strip, strip_start, strip_end):
    """SPEC17 A1 / G6: flatness measured hot against after cooling, from a SUPPLIED scan.

    [D, re-derived in SPEC17] With eps_m the model's mechanical elongation (referred to a
    uniform temperature) the stress a shapemeter senses in the hot strip follows
    eps_m + eps_T; after the coil has cooled only eps_m is left. Without a flatness controller
    'after_cooling' equals 'mechanical'; the held-flat case is a bound. The term is reported
    beside the width section's verdicts and never folded into them or into any evidence.
    """
    s = w.get('strip_temperature')
    if s is None:
        return not_supplied('width_model.strip_temperature is null or absent')
    flags = [ST_FLAG_SUPPLIED]
    mech_ok = (isinstance(shape_steady, dict) and isinstance(shape_steady.get('z_m'), list)
               and isinstance(shape_steady.get('i_units_with_feedback'), list)
               and len(shape_steady['z_m']) > 2)
    z = list(shape_steady['z_m']) if mech_ok else list(z_strip)
    if len(z) < 3:
        raise ValueError('fewer than 3 strip samples for the strip temperature term')
    xs, ys = s['positions_m'], s['temperature_k']
    temps = [_interp_held(xs, ys, x) for x in z]
    dz = z[1] - z[0]
    a0, a1 = strip_start, strip_end
    extrap = max(0.0, min(xs[0], a1) - a0) + max(0.0, a1 - max(xs[-1], a0))
    if extrap > dz:
        flags.append(ST_FLAG_COVER)
    alpha = s['expansion_coefficient_per_k']
    th = (ss.thermal_flatness_term(z, temps) if alpha is None
          else ss.thermal_flatness_term(z, temps, expansion_coefficient_per_k=alpha))
    flags += th['flags']
    m = case['material']
    kw = dict(youngs_modulus_pa=m['youngs_modulus_pa'], poisson_ratio=STRIP_POISSON_RATIO,
              thickness_m=case['pass']['exit_thickness_m'],
              mean_tension_pa=case['pass']['exit_tension_pa'], yield_stress_pa=m['yield_stress_pa'])

    def prof(name, iu, available=True):
        f = ss.flatness_from_elongation(z, [v * 1e-5 for v in iu], **kw)
        return {'name': name, 'meaning': ST_MEANINGS[name], 'available': available,
                'i_units': f['i_units'], 'status': f['status'],
                'released_status': f['released_status'], 'max_i_units': f['max_i_units'],
                'min_i_units': f['min_i_units'], 'bands': f['bands']}
    zero = [0.0] * len(z)
    mech_iu = list(shape_steady['i_units_with_feedback']) if mech_ok else zero
    if not mech_ok:
        flags.append(ST_FLAG_NO_MECH)
    profiles = {
        'mechanical': prof('mechanical', mech_iu, mech_ok),
        'as_measured_hot': prof('as_measured_hot', [a + b for a, b in
                                                    zip(mech_iu, th['i_units'])]),
        'after_cooling': prof('after_cooling', mech_iu, mech_ok),
        'after_cooling_if_hot_reading_held_flat': prof(
            'after_cooling_if_hot_reading_held_flat', [-b for b in th['i_units']])}
    changes = []
    for src, other in (('mechanical', 'as_measured_hot'), ('as_measured_hot', 'mechanical')):
        for b in profiles[src]['bands']:
            o = _band_at(profiles[other]['bands'], b['peak_position_m'])
            differs = (o is None or o['state'] != b['state']
                       or o['state_after_tension_release'] != b['state_after_tension_release'])
            changes.append({
                'profile': src, 'peak_position_m': b['peak_position_m'],
                'peak_i_units': b['peak_i_units'], 'state': b['state'],
                'state_after_tension_release': b['state_after_tension_release'],
                'other_profile': other,
                'other_state': None if o is None else o['state'],
                'other_state_after_tension_release': (None if o is None else
                                                      o['state_after_tension_release']),
                'other_peak_i_units': None if o is None else o['peak_i_units'],
                'state_differs': differs})
    if any(c['state_differs'] for c in changes):
        flags.append(ST_FLAG_STATE)
    dev = th['temperature_deviation_k']
    return {'status': 'SCREENING_RESULT_NOT_PLANT_VALIDATED', 'not_supplied': False,
            'provenance': s['provenance'],
            'expansion_coefficient_per_k': th['expansion_coefficient_per_k'],
            'expansion_coefficient_basis': (
                '[M] 23.6e-6 /K, textbook value used by the gap reports, not verified there '
                '(default)' if alpha is None else 'supplied'),
            'i_units_per_kelvin': th['i_units_per_kelvin'],
            'z_m': z, 'temperature_k': temps, 'mean_temperature_k': th['mean_temperature_k'],
            'max_temperature_deviation_k': max(abs(d) for d in dev),
            'scan_coverage': {'scan_start_m': xs[0], 'scan_end_m': xs[-1],
                              'strip_start_m': a0, 'strip_end_m': a1,
                              'extrapolated_width_m': extrap,
                              'rule': 'linear between scan points; end values held outside'},
            'thermal_i_units': th['i_units'], 'profiles': profiles, 'state_changes': changes,
            'basis': {'thermal_term': th['formula_basis'],
                      'profiles': '[D, re-derived in SPEC17] hot = mechanical + thermal; after '
                                  'cooling = mechanical (no controller); held-flat = -thermal '
                                  '(bounding case)',
                      'literature': 'a hotter fibre reads loose in the mill and the difference '
                                    'disappears when the coil cools [TM-LA13 EX]; steel: '
                                    '1 C = 1.2 I-units [TM-LA30 EX]; about 2.4 I-units per K '
                                    'for aluminium [computed]'},
            'flags': flags, 'limitations': list(ST_LIMITATIONS)}


def _validate_friction_screen(s, barrel):
    if s is None:
        return None
    where = 'width_model.friction_stripe_screen'
    keys(where, s, (), ('reference_half_peak_width_m', 'stripes'))
    ref = s.get('reference_half_peak_width_m')
    if ref is not None:
        if isinstance(ref, bool) or not isinstance(ref, (int, float)) or not math.isfinite(ref) \
                or not 0 < ref <= 1:
            raise ValueError(f'{where}.reference_half_peak_width_m must be in (0, 1] m or null')
        ref = float(ref)
    stripes = s.get('stripes', [])
    if not isinstance(stripes, list):
        raise ValueError(f'{where}.stripes must be a list (it may be empty)')
    out = []
    for i, x in enumerate(stripes):
        w_i = f'{where}.stripes[{i}]'
        keys(w_i, x, ('position_m', 'half_peak_width_m', 'friction_change_fraction'),
             ('label',))
        pos = num(f'{w_i}.position_m', x['position_m'])
        if not 0 <= pos <= barrel:
            raise ValueError(f'{w_i}.position_m must be >= 0 and on the barrel')
        hw = num(f'{w_i}.half_peak_width_m', x['half_peak_width_m'])
        if not 0 < hw <= 1:
            raise ValueError(f'{w_i}.half_peak_width_m must be in (0, 1] m')
        fr = num(f'{w_i}.friction_change_fraction', x['friction_change_fraction'])
        if not -0.9 <= fr <= 5 or fr == 0:
            raise ValueError(f'{w_i}.friction_change_fraction must be in [-0.9, 5] and not 0')
        lab = x.get('label')
        if lab is not None and (not isinstance(lab, str) or not lab.strip()):
            raise ValueError(f'{w_i}.label must be a nonempty string or null')
        out.append({'position_m': pos, 'half_peak_width_m': hw,
                    'friction_change_fraction': fr, 'label': lab})
    return {'reference_half_peak_width_m': ref, 'stripes': out}


FS_FLAG_APPLIED = 'FRICTION_STRIPE_SCREEN_APPLIED'
FS_FLAG_NOT_SATURATED = 'FRICTION_STRIPE_LINEAR_FEEDBACK_NOT_SATURATED'
FS_PUBLISHED_EXPONENT = [2.0, 2.6]
FS_PUBLISHED_EXPONENT_NOTE = ('[derived by the bite report, slope read by eye from BT-S1 Fig. '
                              '6a; regimes II-III at fixed gauge and reduction]')
FS_TREND_END = ('Whether a friction stripe grows as gauge falls therefore depends on the '
                'exit-tension feedback, the least supported element of the shape chain.')
FS_SIGN_NOTE = ('A locally higher friction makes the strip locally thicker and the fibre tight; '
                'a locally lower friction makes it loose. For a hot roll stripe the film path '
                '(thinner film, more friction) therefore acts against the roll-growth path '
                '(larger roll, thinner strip). The net sign is not known (gap A2).')
FS_LIMITATIONS = (
    'Linear sensitivity chain: dh from dF/dmu times a supplied friction change; the band-wise '
    'saturation of the roll-bump chain is not applied.',
    'dF/dmu is a central difference (+-2 %) of a constant-friction bite; at foil gauge that '
    'bite is the experimental mattress model, which returns 0.42 of the reference load on '
    'the one published benchmark (physicroll.benchmarks, BT-V1).',
    'The with-feedback level rests on the linear exit-tension feedback, which the literature '
    'neither supports nor contradicts (gap study X17); the compliance-only level is shown '
    'beside it.',
    'Friction is taken as uniform through the bite; no film model across the width, no '
    'starvation (BT-G12), no coupling to the roll temperature (gap A2); entry tension uniform.',
    'No evidence item: the screen does not change any hypothesis score (SPEC17 open decision '
    '3).')
FS_PLACEHOLDER_NOTE = ('The closure\'s slope is not supported by data (X22); these conversions '
                       'show orders of magnitude only.')


def _gauss(z, c, b, amp):
    return [amp * math.exp(-4 * math.log(2) * ((x - c) / b) ** 2) for x in z]


def _friction_i_units(z, dp, sp, feedback):
    h = sp['exit_thickness_m']
    tr = ss.transfer_force_profile(
        z, dp, bite_half_length_m=sp['bite_half_length_m'],
        strip_stiffness_per_width_pa=sp['strip_stiffness_per_width_pa'],
        roll_radius_m=sp['roll_radius_m'], roll_youngs_modulus_pa=sp['roll_youngs_modulus_pa'],
        roll_poisson_ratio=sp['roll_poisson_ratio'],
        exit_tension_force_sensitivity_per_width_m=(
            sp['exit_tension_force_sensitivity_per_width_m'] if feedback else None),
        exit_thickness_m=h, strip_youngs_modulus_pa=sp['strip_youngs_modulus_pa'],
        xi=sp['xi'])
    dh = tr['local_thickness_change_m']
    el = ss.differential_elongation(z, [h] * len(z), [h + v for v in dh], xi=sp['xi'])
    eps = el['elongation']
    m = math.fsum(eps) / len(eps)
    return tr, [1e5 * (e - m) for e in eps], eps


def _monotonic_words(values):
    if all(b > a for a, b in zip(values, values[1:])):
        return 'rises'
    if all(b < a for a, b in zip(values, values[1:])):
        return 'falls'
    overall = 'up' if values[-1] > values[0] else 'down'
    return f'is not monotonic (overall {overall})'


def friction_trend_text(rows):
    """Trend of the three quantities over the credible rows, ordered by falling exit gauge."""
    ok = sorted([r for r in rows if 'rejected' not in r], key=lambda r: -r['exit_thickness_m'])
    if len(ok) < 2:
        return ('Fewer than two assessable passes: no trend. ' + FS_TREND_END)
    span = (f'{ok[0]["exit_thickness_m"] * 1e3:.3g} -> {ok[-1]["exit_thickness_m"] * 1e3:.3g} '
            'mm')
    ex = [r['load_exponent_in_friction'] for r in ok]
    co = [abs(r['i_units_per_percent_friction_compliance_only']) for r in ok]
    fb = [abs(r['i_units_per_percent_friction_with_feedback']) for r in ok]
    names = ', '.join(r['label'].split()[0] for r in ok)
    return (f'As the exit gauge falls ({span}, {names}): the load '
            f'exponent in friction {_monotonic_words(ex)} ({ex[0]:.3g} to {ex[-1]:.3g}); the '
            f'compliance-only I-units per 1 % friction {_monotonic_words(co)} in magnitude '
            f'({co[0]:.3g} to {co[-1]:.3g}); with exit-tension feedback the magnitude '
            f'{_monotonic_words(fb)} (between {min(fb):.3g} and {max(fb):.3g}). '
            + FS_TREND_END)


def _friction_row(case, w, src, label, bite, sens, z, b_ref):
    width = case['pass']['width_m']
    sp, sp_basis = shape_params_or_none(case, bite, w, None if src is case['pass'] else src)
    if sp is None:
        raise ValueError('no bite and no shape inputs for this pass')
    mu = src['friction_coefficient']
    fpw = bite.separating_force_n / width
    m_mu = sens['dforce_dfriction_n'] / width
    zc = sp['strip_centre_m']
    k = min(range(len(z)), key=lambda i: abs(z[i] - zc))
    dp = [m_mu * v for v in _gauss(z, zc, b_ref, 0.01 * mu)]
    _, iu_fb, _ = _friction_i_units(z, dp, sp, True)
    _, iu_co, _ = _friction_i_units(z, dp, sp, False)
    nx = sp['exit_tension_force_sensitivity_per_width_m']
    return {'label': label, 'exit_thickness_m': src['exit_thickness_m'],
            'friction_coefficient': mu, 'force_per_width_n_m': fpw,
            'dforce_per_width_dfriction_n_m': m_mu,
            'load_exponent_in_friction': m_mu * mu / fpw,
            'i_units_per_percent_friction_with_feedback': iu_fb[k],
            'i_units_per_percent_friction_compliance_only': iu_co[k],
            'feedback_limit_i_units_per_percent': (
                None if not nx else -1e5 * m_mu * 0.01 * mu
                / (nx * sp['strip_youngs_modulus_pa'])),
            'shape_inputs_basis': sp_basis, 'bite_model': bite_model_name(bite),
            'bite_flags': list(bite.flags), 'sensitivity_bite_model': sens.get('bite_model')}, sp


def friction_stripes_section(case, w, op_bite, get_bite, friction_sensitivity, steady_shape,
                             th, trib, friction_row, bite_error=None):
    """SPEC17 BT-G4, screening version: a local friction difference as a band source.

    With ``M_mu = (dF/dmu)/width`` of the existing bite (central difference +-2 %), a friction
    stripe ``dmu(z)`` gives ``dp0' = M_mu*dmu`` at an unchanged gap, ``dh`` by
    ``strip_shape.transfer_force_profile`` (with and without the exit-tension feedback) and the
    flatness as the shape chain computes it. Reported beside the roll-bump chain, never summed
    into it, and never evidence (open decision 3).
    """
    s = w.get('friction_stripe_screen')
    if s is None:
        return not_supplied('width_model.friction_stripe_screen is null or absent')
    if op_bite is None or friction_sensitivity is None:
        return {'status': 'NOT_ASSESSABLE', 'not_supplied': False,
                'reason': ('no bite for the case pass'
                           + (f' ({bite_error})' if bite_error else '')
                           + ': dF/dmu is not available'), 'flags': []}
    b_ref = s['reference_half_peak_width_m'] or REFERENCE_HALF_PEAK_WIDTH_M
    p = case['pass']
    centre, width = th.centre, th.width
    if isinstance(steady_shape, dict) and isinstance(steady_shape.get('z_m'), list) \
            and len(steady_shape['z_m']) >= 4:
        z = list(steady_shape['z_m'])
        grid_basis = 'the strip samples of width.shape.steady'
    else:
        n = max(4, int(round(width / 0.005)))
        z = [centre - width / 2 + (i + 0.5) * width / n for i in range(n)]
        grid_basis = 'a uniform 5 mm grid over the strip (no steady shape)'
    flags = [FS_FLAG_APPLIED]
    # passes: the case pass and every other schedule pass (a schedule row that IS the case
    # pass is listed once, under its own label, with the operating bite)
    srcs, case_label = [], 'case pass'
    for r in case['schedule']:
        if is_case_pass(case, r):
            case_label = r['label']
    srcs.append((case_label, p, True))
    srcs += [(r['label'], r, False) for r in case['schedule'] if not is_case_pass(case, r)]
    rows, case_row, case_sp = [], None, None
    for label, src, is_case in srcs:
        try:
            bite = op_bite if is_case else get_bite(src)
            sens = friction_sensitivity(src)
            row, sp = _friction_row(case, w, src, label, bite, sens, z, b_ref)
            if is_case:
                case_row, case_sp = row, sp
        except ValueError as exc:
            row = {'label': label, 'exit_thickness_m': src['exit_thickness_m'],
                   'friction_coefficient': src['friction_coefficient'], 'rejected': str(exc)}
        row['is_case_pass'] = is_case
        rows.append(row)
    rows.sort(key=lambda r: -r['exit_thickness_m'])
    out = {'status': 'SCREENING_RESULT_NOT_PLANT_VALIDATED', 'not_supplied': False,
           'grid_basis': grid_basis, 'reference_half_peak_width_m': b_ref,
           'reference_half_peak_width_basis': ('supplied' if s['reference_half_peak_width_m']
                                               else 'default, the gauge trend\'s reference'),
           'per_pass': rows, 'trend_text': friction_trend_text(rows),
           'sign_note': FS_SIGN_NOTE, 'stripes': []}
    if case_row is None:
        out.update(status='NOT_ASSESSABLE', reason=next(
            (r['rejected'] for r in rows if r['is_case_pass']), 'case pass not assessable'),
            flags=flags, limitations=list(FS_LIMITATIONS))
        return out
    fb_value = case_row['i_units_per_percent_friction_with_feedback']
    out['case_pass'] = {
        'label': case_row['label'], 'force_per_width_n_m': case_row['force_per_width_n_m'],
        'friction_coefficient': case_row['friction_coefficient'],
        'dforce_per_width_dfriction_n_m': case_row['dforce_per_width_dfriction_n_m'],
        'load_exponent_in_friction': case_row['load_exponent_in_friction'],
        'published_load_exponent': list(FS_PUBLISHED_EXPONENT),
        'published_load_exponent_note': FS_PUBLISHED_EXPONENT_NOTE}
    out['reference'] = {
        'stripe': (f'Gaussian friction stripe dmu = 0.01*mu*exp(-4 ln2 ((z - z_c)/b)^2) at the '
                   f'strip centre, b = {b_ref:g} m'),
        'i_units_per_percent_friction_with_feedback': fb_value,
        'i_units_per_percent_friction_compliance_only':
            case_row['i_units_per_percent_friction_compliance_only'],
        'friction_change_fraction_for_reporting_threshold': (
            None if fb_value == 0 else 0.01 * 2 / abs(fb_value)),
        'feedback_limit_i_units_per_percent': case_row['feedback_limit_i_units_per_percent']}
    mu, m_mu, sp = case_row['friction_coefficient'], case_row['dforce_per_width_dfriction_n_m'], \
        case_sp
    for i, st in enumerate(s['stripes']):
        dmu = _gauss(z, st['position_m'], st['half_peak_width_m'],
                     st['friction_change_fraction'] * mu)
        tr, _, eps = _friction_i_units(z, [m_mu * v for v in dmu], sp, True)
        fl = ss.flatness_from_elongation(
            z, eps, youngs_modulus_pa=sp['strip_youngs_modulus_pa'],
            poisson_ratio=sp['strip_poisson_ratio'], thickness_m=sp['exit_thickness_m'],
            mean_tension_pa=sp['mean_tension_pa'], yield_stress_pa=sp['yield_stress_pa'])
        band = _band_at(fl['bands'], st['position_m'])
        peak = max(fl['i_units'], key=abs)
        if any(b['state'] == 'MANIFEST_BUCKLE' for b in fl['bands']):
            if FS_FLAG_NOT_SATURATED not in flags:
                flags.append(FS_FLAG_NOT_SATURATED)
        out['stripes'].append({
            'index': i, 'label': st['label'], 'position_m': st['position_m'],
            'half_peak_width_m': st['half_peak_width_m'],
            'friction_change_fraction': st['friction_change_fraction'],
            'peak_local_thickness_change_m': tr['peak_local_thickness_change_m'],
            'peak_i_units': peak, 'sense': None if band is None else band['sense'],
            'state': 'BELOW_REPORTING_THRESHOLD' if band is None else band['state'],
            'state_after_tension_release': (None if band is None
                                            else band['state_after_tension_release']),
            'band': band, 'bands': fl['bands'], 'i_units': fl['i_units'], 'z_m': z,
            'reporting_threshold_i_units': ss.DEFAULT_REPORTING_THRESHOLD_I_UNITS})
    if trib is not None and isinstance(friction_row, dict) \
            and friction_row.get('film_ratio') is not None:
        out['conversion_placeholder'] = _friction_placeholder(trib, friction_row)
    out['flags'] = flags
    out['limitations'] = list(FS_LIMITATIONS)
    return out


def _friction_placeholder(trib, row):
    from . import band_process as bproc
    from . import bite_tribology as bt
    _, fin, clo = bproc.tribology_objects(trib)
    lam = row['film_ratio']
    load_sharing = clo.model == 'load_sharing_curve'
    if load_sharing and row.get('dmu_dlambda') is not None:
        d = row['dmu_dlambda']             # the friction row's slope (its bite state)
    else:
        d = bt.friction_coefficient(lam, clo)['dmu_dlambda']
    beta = trib['lubricant']['temperature_viscosity_coefficient_per_k']
    rr, rs = fin.roll_roughness_rq_m, fin.strip_roughness_rq_m
    mu_used = row.get('used_friction_coefficient', row.get('supplied_friction_coefficient'))
    per_k = d * lam * (-beta)
    per_rough = d * lam * (-0.1 * rr ** 2 / (rr ** 2 + rs ** 2))
    extra = ({'friction_closure': 'load_sharing_curve', 'note_closure': bt.LOAD_SHARING_NOTE}
             if load_sharing else {})      # keys only then
    return {**extra, 'flags': [bt.LOAD_SHARING_FLAG if load_sharing else bt.PLACEHOLDER_FLAG],
            'film_ratio': lam, 'dmu_dlambda': d,
            'friction_change_per_kelvin_oil': per_k,
            'friction_change_per_kelvin_oil_fraction': None if not mu_used else per_k / mu_used,
            'friction_change_per_10_percent_roll_roughness': per_rough,
            'friction_change_per_10_percent_roll_roughness_fraction':
                None if not mu_used else per_rough / mu_used,
            'friction_coefficient_used': mu_used,
            'basis': ('dmu/dT = dmu/dLambda * Lambda * (-beta) (film proportional to the inlet '
                      'viscosity, eta0 ~ exp(-beta dT)); dmu per +10 % roll Rq = dmu/dLambda * '
                      'Lambda * (-0.1 Rq_r^2/(Rq_r^2 + Rq_s^2)) [D]; '
                      + ('load-sharing closure' if load_sharing else 'placeholder closure')),
            'note': FS_PLACEHOLDER_NOTE}


def _case_radii(case):
    """(label, radius) of every roller or coil radius the case gives (SPEC17 G12)."""
    out = []
    w = case.get('width_model')
    if w is not None:
        if w.get('deflector_roll_radius_m') is not None:
            out.append(('width_model.deflector_roll_radius_m', w['deflector_roll_radius_m']))
        coil = w.get('coil')
        if coil is not None:
            out.append(('width_model.coil.inner_radius_m', coil['inner_radius_m']))
            out.append(('width_model.coil.outer_radius_m', coil['outer_radius_m']))
    k = case.get('kinematics') or {}
    for i, d in enumerate(k.get('deflector_roll_diameters_m') or []):
        out.append((f'kinematics.deflector_roll_diameters_m[{i}]/2', d / 2))
    if k.get('exit_coil_diameter_m') is not None:
        out.append(('kinematics.exit_coil_diameter_m/2', k['exit_coil_diameter_m'] / 2))
    return out


TL_PUBLISHED_PITCH_M = [0.005, 0.020]
TL_HOW_TO_TEST = ('Measure the pitch at two coil radii and two gauges: this candidate predicts '
                  'pitch proportional to sqrt(radius x gauge).')
TL_BASIS = ('entrained-air corrugation in winding has the same remedies and thin-gauge trend '
            '[SS-S53 EX, SS-S66 EX]; wavelength formula re-derived (classical shell); no onset '
            'condition, no air-film model (G9, G10)')
TL_NOTE = ('not evidence: almost any foil coil gives a candidate pitch inside the published '
           '5-20 mm')


def candidate_tension_line_pitch(exit_thickness_m, radii, observed_spacing_m=None):
    """SPEC17 G12: the shell-buckling pitch at each radius of the case; a candidate for
    comparison only, never evidence (the tension-line rules are unchanged)."""
    out = {'formula': 'pitch = 2*pi*sqrt(R*t)/(12*(1 - nu^2))^(1/4) [D, re-derived in SPEC17; '
                      'reported from memory as 3.47*sqrt(R*t)]',
           'poisson_ratio': STRIP_POISSON_RATIO, 'rows': [], 'pitch_range_m': None,
           'published_pitch_m': list(TL_PUBLISHED_PITCH_M),
           'observed_spacing_m': observed_spacing_m, 'observed_inside_candidate_range': None,
           'how_to_test': TL_HOW_TO_TEST, 'basis': TL_BASIS, 'note': TL_NOTE}
    if exit_thickness_m >= FOIL_GAUGE_M:
        out['status'] = 'NOT_APPLICABLE_ABOVE_FOIL_GAUGE'
        return out
    if not radii:
        out['status'] = 'NO_RADIUS_IN_CASE'
        return out
    rows = [{'where': where, 'radius_m': r,
             'pitch_m': ss.shell_buckling_wavelength_m(r, exit_thickness_m, STRIP_POISSON_RATIO)}
            for where, r in radii]
    lo, hi = min(x['pitch_m'] for x in rows), max(x['pitch_m'] for x in rows)
    out.update(status='CANDIDATE_NOT_ESTABLISHED', rows=rows, pitch_range_m=[lo, hi])
    if observed_spacing_m is not None:
        out['observed_inside_candidate_range'] = lo <= observed_spacing_m <= hi
    return out


def _validate_roll_profile(s, barrel):
    if s is None:
        return None
    where = 'width_model.roll_ground_profile'
    keys(where, s, ('positions_m', 'radius_deviation_m', 'provenance'),
         ('detrend_order', 'rolls_carrying'))
    pos = s['positions_m']
    msg = f'{where}.positions_m must be >= 5 strictly increasing positions on the barrel'
    if not isinstance(pos, list) or len(pos) < 5:
        raise ValueError(msg)
    try:
        pos = [num(f'{where}.positions_m[{i}]', v) for i, v in enumerate(pos)]
    except ValueError:
        raise ValueError(msg) from None
    if any(b <= a for a, b in zip(pos, pos[1:])) or pos[0] < 0 or pos[-1] > barrel:
        raise ValueError(msg)
    dev = s['radius_deviation_m']
    dmsg = f'{where}.radius_deviation_m needs one value in [-1e-3, 1e-3] m per position'
    if not isinstance(dev, list) or len(dev) != len(pos):
        raise ValueError(dmsg)
    try:
        dev = [num(f'{where}.radius_deviation_m[{i}]', v, lo=-1e-3, hi=1e-3)
               for i, v in enumerate(dev)]
    except ValueError:
        raise ValueError(dmsg) from None
    order = s.get('detrend_order', 2)
    if order is not None and (isinstance(order, bool) or not isinstance(order, int)
                              or not 0 <= order <= 6):
        raise ValueError(f'{where}.detrend_order must be an int in [0, 6] or null')
    nr = s.get('rolls_carrying', 1)
    if isinstance(nr, bool) or nr not in (1, 2):
        raise ValueError(f'{where}.rolls_carrying must be 1 or 2')
    pv = s['provenance']
    if not isinstance(pv, str) or not pv.strip():
        raise ValueError(f'{where}.provenance must be a nonempty string')
    return {'positions_m': pos, 'radius_deviation_m': dev, 'detrend_order': order,
            'rolls_carrying': nr, 'provenance': pv}


RP_FLAG_SUPPLIED = 'ROLL_GROUND_PROFILE_SUPPLIED'
RP_FLAG_BAND = 'ROLL_GROUND_PROFILE_BAND_ABOVE_THRESHOLD'
RP_LIMITATIONS = (
    "The profile is one roll's ground shape, measured cold and off the mill.",
    'Marks narrower than about two grid cells or than 4a (four bite half-lengths) are smoothed.',
    'No wear growth during the campaign.',
    'No barrel-position modulation by roll bending (needs the roll stack, gap G1).',
    'The removed polynomial (crown or camber) is reported only; it is not passed to the crown '
    'or heredity model.',
    'The hypotheses roll_surface_band and grinding_feed_marks stay rule-based and do not read '
    'this section.')
RP_PUBLISHED_STIFFNESS = ('thin aluminium 0.236 mm: 176 / 57.8 kN/mm2, ratio 3.04; thin '
                          'stainless: ratio 28, transfer almost negligible (model output) '
                          '[SS-S3 FT]')
RP_LV_KEYS = ('status', 'released_status', 'z_m', 'local_radius_deviation_m',
              'local_thickness_change_m', 'i_units_with_feedback', 'i_units_linear_feedback',
              'rigid_transfer_bound_i_units', 'compliance_only_peak_i_units',
              'feedback_peak_i_units', 'linear_feedback_peak_i_units', 'levels', 'flags')


def roll_profile_section(case, w, sp, shape_reason, z, th, thermal_steady, bite=None):
    """SPEC17 G13: a measured roll ground profile through the existing transfer.

    The supplied radius deviation (one roll, positive = larger roll) is interpolated onto the
    width section's grid (end values held outside the scan), de-trended over the strip by
    ``roll_thermal.local_stripes`` (the removed polynomial is reported, not passed on) and put
    through ``shape_levels`` exactly as a thermal stripe [SS-S3 FT: grinding residuals and
    wear transfer like thermal stripes; the transfer itself is the project's, D]. Reported
    beside the width section, never evidence.
    """
    s = w.get('roll_ground_profile')
    if s is None:
        return not_supplied('width_model.roll_ground_profile is null or absent')
    if sp is None:
        return {'status': 'NOT_ASSESSABLE', 'not_supplied': False,
                'reason': shape_reason or 'no shape parameters', 'flags': []}
    xs, ys = s['positions_m'], s['radius_deviation_m']
    vals = [_interp_held(xs, ys, x) for x in z]
    dz = z[1] - z[0]
    a0, a1 = th.centre - th.width / 2, th.centre + th.width / 2
    extrap = max(0.0, min(xs[0], a1) - a0) + max(0.0, a1 - max(xs[-1], a0))
    loc = rt.local_stripes(z, vals, th.centre, th.width, threshold_m=STRIPE_THRESHOLD_M,
                           smooth_order=s['detrend_order'])
    by_z = dict(zip(loc['z_m'], loc['local_radius_deviation_m']))
    dev = [by_z.get(x, 0.0) for x in z]
    smooth = [a - b for a, b in zip(
        [v for x, v in zip(z, vals) if x in by_z], loc['local_radius_deviation_m'])]
    spr = dict(sp, n_rolls=s['rolls_carrying'])
    lv = shape_levels(z, dev, spr)
    out = {'status': 'SCREENING_RESULT_NOT_PLANT_VALIDATED', 'not_supplied': False,
           'provenance': s['provenance'], 'detrend_order': s['detrend_order'],
           'rolls_carrying': s['rolls_carrying'],
           'scan_coverage': {'scan_start_m': xs[0], 'scan_end_m': xs[-1], 'strip_start_m': a0,
                             'strip_end_m': a1, 'extrapolated_width_m': extrap,
                             'rule': 'linear between scan points; end values held outside'},
           'removed_polynomial_m': smooth, 'removed_polynomial_z_m': list(loc['z_m']),
           'removed_polynomial_peak_to_peak_m': (max(smooth) - min(smooth)) if smooth else 0.0,
           'removed_polynomial_note': ('the removed crown or camber belongs to the crown model; '
                                       'it is reported and drawn, not passed to it'),
           'measured_on_strip_m': [v for x, v in zip(z, vals) if x in by_z],
           'stripes': loc['stripes'], 'local_stripes_status': loc['status'],
           'local_stripes_flags': loc['flags']}
    out.update({k: lv[k] for k in RP_LV_KEYS if k in lv})
    stripe_input = {'stripes': loc['stripes'], 'z_m': z, 'local_deviation_m': dev}
    try:
        out['stripe_table'] = steady_stripe_table(stripe_input, lv, spr)
        out['stripe_table_basis'] = 'steady_stripe_table (states and onsets per stripe)'
    except (ValueError, KeyError):
        out['stripe_table'] = [dict(position_m=st['peak_position_m'],
                                    peak_radius_deviation_m=st['peak_deviation_m'],
                                    width_at_half_peak_m=st['width_at_half_peak_m'],
                                    **stripe_states(lv, st['peak_position_m']))
                               for st in loc['stripes']]
        out['stripe_table_basis'] = 'stripe_states at each stripe peak'
    # combined with the thermal stripes of the same roll
    if not isinstance(thermal_steady, dict) or 'local_deviation_m' not in thermal_steady:
        out['combined_with_thermal'] = not_supplied('no roll thermal solution')
    elif s['rolls_carrying'] != w['rolls_carrying_stripe']:
        out['combined_with_thermal'] = not_assessable(
            f'rolls_carrying {s["rolls_carrying"]} differs from '
            f'width_model.rolls_carrying_stripe {w["rolls_carrying_stripe"]}: the two radius '
            'deviations are not on the same roll(s)')
    else:
        comb = shape_levels(thermal_steady['z_m'],
                            [a + _interp_held(z, dev, x) for x, a in
                             zip(thermal_steady['z_m'], thermal_steady['local_deviation_m'])],
                            sp)
        out['combined_with_thermal'] = {k: comb[k] for k in RP_LV_KEYS if k in comb}
    # stiffness indicator [SS-S3 FT idea and ratios; the project's analogue D]
    p = case['pass']
    big = max(loc['stripes'], key=lambda x: abs(x['peak_deviation_m']), default=None)
    a_half = sp['bite_half_length_m']
    lam = None if big is None else min(max(2 * big['width_at_half_peak_m'], 4 * a_half),
                                       sp['roll_radius_m'])
    roll_term = (None if lam is None else 1 / (2 * ss.roll_line_compliance_m2_n(
        lam, a_half, sp['roll_youngs_modulus_pa'], sp['roll_poisson_ratio'])))
    kf1 = (None if bite is None else bite.separating_force_n / p['width_m']
           / (p['entry_thickness_m'] - p['exit_thickness_m']))
    out['stiffness_check'] = {
        'strip_foundation_modulus_pa': kf1,
        'strip_foundation_modulus_basis': ("(F/width)/(h_entry - h_exit), Patel's kf1 as the "
                                           'report restates it [SS-S3 FT]'),
        'roll_term_pa': roll_term, 'wavelength_m': lam,
        'wavelength_basis': 'twice the half-peak width of the largest stripe, clamped to [4a, R]',
        'ratio_strip_to_roll': (None if kf1 is None or not roll_term else kf1 / roll_term),
        'published_context': RP_PUBLISHED_STIFFNESS,
        'basis': ("roll term 1/(2*C(lam)) is the project's analogue, not Patel's kf2 (its "
                  'definition was not recorded) [D]')}
    # observed positions: information only
    obs = case['observation']
    if obs['band_positions_across_width_m']:
        tol, tbasis = position_tolerance(obs, w['spray_header']['nozzle_pitch_m'])
        peaks = [b['peak_position_m'] for b in lv['levels']['with_feedback']['bands']]
        out['position_match'] = {
            'tolerance_m': tol, 'tolerance_basis': tbasis,
            'matches': ss.match_positions(peaks, obs['band_positions_across_width_m'],
                                          tol)['matches'],
            'note': 'information only: not evidence'}
    else:
        out['position_match'] = None
    flags = list(lv.get('flags') or []) + [RP_FLAG_SUPPLIED]
    if lv['levels']['with_feedback']['bands']:
        flags.append(RP_FLAG_BAND)
    out['flags'] = flags
    out['limitations'] = list(RP_LIMITATIONS)
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
            if h < FOIL_GAUGE_M:
                out[name]['wide_foil_note'] = WIDE_FOIL_TROUGH_NOTE
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


def steady_stripe_table(steady, lv, sp):
    """States and onsets of each steady stripe; ``lv``: shape_levels of the whole steady
    deviation. The onsets are those of the band at the stripe peak, where its states are
    read (a cold stripe's loose neighbour lanes are not its onset)."""
    table = [dict(position_m=s['peak_position_m'], peak_radius_deviation_m=s[
        'peak_deviation_m'], stripe_width_m=s['width_m'],
        width_at_half_peak_m=s['width_at_half_peak_m'],
        **stripe_states(lv, s['peak_position_m'])) for s in steady['stripes']]
    for s, row in zip(steady['stripes'], table):
        on = onsets(steady['z_m'], _isolate(steady['z_m'], steady['local_deviation_m'], s), sp,
                    position=s['peak_position_m'])
        pk = abs(s['peak_deviation_m'])
        for key, name in (('manifest_onset_peak_height_m', 'mill'),
                          ('released_onset_peak_height_m', 'released'),
                          ('reporting_onset_peak_height_m', 'reporting')):
            row[key] = None if on[name] is None else on[name] * pk
            if f'{name}_domain_limit' in on:
                row[key[:-2] + '_domain_limit_m'] = on[f'{name}_domain_limit'] * pk
        row['released_onset_limited_by_reporting_threshold'] = _limited(
            on['released'], on['reporting'])
    return table


def _gauge_trend(case, w, get_bite, steady, centre, coil, z_grid, op_bite, shape_reason,
                 thermal_shape=None):
    """Same stripe on every schedule pass. ``steady`` may be None (Gaussian reference stripe
    on ``z_grid``). Per pass the shape parameters come from the pass's own bite; the case pass
    uses ``width_model.shape_inputs`` when supplied (SPEC9 9.1) and is rejected with the bite
    error when it has neither. ``op_bite``: the case-pass bite (or None). ``thermal_shape``
    (``band_thermal.thermal_shape_off_case_share``): with the Gaussian reference stripe, the
    thermal stripe found at another heat share; its per-pass onsets are added
    (``thermal_shape_*_onset_height_m``) for the sensitivity per-pass table."""
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
    if steady and steady['stripes']:
        thermal_shape = None              # the model stripe's own onsets already serve
    shape_t = None if thermal_shape is None else coarse_grid(th_z, thermal_shape['shape'])[1]
    peak_t = None if shape_t is None else abs(max(shape_t, key=abs))
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
            on = onsets(zc, shape_c, sp, position=peak_x)    # paired with st at peak_x
            on_ref = onsets(zc, ref, sp)

            def h(scale, height):
                return None if scale is None else scale * height
            row.update(
                shape_inputs_basis=sp_basis,
                bite_source=(None if bite is None else 'reduced_half_space'
                             if HALF_SPACE_FLAG in bite.flags else bite.source),
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
            if shape_t is not None and peak_t > 0:
                on_t = onsets(zc, shape_t, sp, position=thermal_shape['position_m'])
                row.update(thermal_shape_manifest_onset_height_m=h(on_t['mill'], peak_t),
                           thermal_shape_released_onset_height_m=h(on_t['released'], peak_t))
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
    out['reference_stripe_kind'] = ('model_steady_stripe' if steady and steady['stripes']
                                    else 'gaussian_reference')
    if shape_t is not None:
        out['thermal_shape_onsets'] = {
            'window_strip_heat_share': thermal_shape['window_share'],
            'position_m': thermal_shape['position_m'],
            'basis': ('no steady stripe above the detection threshold at the case heat share; '
                      'thermal_shape_*_onset_height_m are the onsets of the thermal stripe '
                      'shape (case-share profile, isolated over the stripe extent at strip '
                      f'share {thermal_shape["window_share"]:.3g}, the window the sensitivity '
                      'rows use) with each pass\'s own shape parameters')}
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
    """'hitchcock', 'experimental_mattress', 'reduced_half_space', 'supplied' or None."""
    if bite is None:
        return None
    if MATTRESS_FLAG in bite.flags:
        return 'experimental_mattress'
    if HALF_SPACE_FLAG in bite.flags:
        return 'reduced_half_space'
    return 'supplied' if bite.source == 'supplied' else 'hitchcock'


MATTRESS_FLAG = 'BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL'
HALF_SPACE_FLAG = 'BITE_FROM_REDUCED_HALF_SPACE_MODEL'


# ================================================ roll surface cycle (SPEC18 package 10, A4, G8)
SURFACE_CYCLE_WEIGHTS = 9            # unit solutions spanning the spray-weight range [D]
SURFACE_CYCLE_TOLERANCE_K = 1e-4     # periodicity of the unit solutions [D]
MEAN_COEFFICIENT_BIAS = 0.05         # flag when a mean_coefficient_ratio differs from 1 by more
CYCLE_FLAG = 'ROLL_SURFACE_CYCLE_COMPUTED'
CYCLE_BIAS_FLAG = 'CIRCUMFERENTIAL_MEAN_COEFFICIENT_BIASED'


def _deep_temperature(field, depth, radius):
    """Steady bulk temperature at radius R - depth for every axial station (linear in r
    between the cell centres of the circumferential-mean field)."""
    r = radius - depth
    rs = field['r_m']
    rows = field['temperature_k']
    if r <= rs[0]:
        return list(rows[0])
    i = max(k for k in range(len(rs)) if rs[k] <= r)
    if i >= len(rs) - 1:
        return list(rows[-1])
    f = (r - rs[i]) / (rs[i + 1] - rs[i])
    return [a + f * (b - a) for a, b in zip(rows[i], rows[i + 1])]


def surface_cycle_layout(w, radius, contact_length):
    """The arcs (time fractions from bite entry) of the layout and the table of the layout used
    (angles from the bite exit in the direction of rotation). ValueError naming the region
    when a region overlaps the bite."""
    lay = w['circumferential_layout']
    theta_b = contact_length / radius
    fb = contact_length / (2 * math.pi * radius)
    regions = [('spray', f'spray arc {i}', r) for i, r in enumerate(lay['spray_arcs'])]
    if lay['backup_contact'] is not None:
        regions.append(('backup', 'backup contact', lay['backup_contact']))
    regions.sort(key=lambda t: t[2]['start_rad'])
    table = [{'region': 'bite', 'start_rad': 2 * math.pi - theta_b, 'arc_rad': theta_b,
              'start_deg': math.degrees(2 * math.pi - theta_b),
              'end_deg': 360.0, 'basis': 'contact length of the case-pass bite'}]
    limit = 2 * math.pi - theta_b
    for kind, name, r in regions:
        if r['start_rad'] + r['arc_rad'] > limit + 1e-12:
            raise ValueError(f'{LAYOUT_WHERE}: {name} ({r["start_rad"]:.4g} to '
                             f'{r["start_rad"] + r["arc_rad"]:.4g} rad) overlaps the bite '
                             f'({limit:.4g} to {2 * math.pi:.4g} rad before the bite exit)')
        table.append({'region': name, 'start_rad': r['start_rad'], 'arc_rad': r['arc_rad'],
                      'start_deg': math.degrees(r['start_rad']),
                      'end_deg': math.degrees(r['start_rad'] + r['arc_rad'])})
    arcs, pos = [('bite', 0.0, fb, None)], fb
    for kind, name, r in regions:
        a = fb + r['start_rad'] / (2 * math.pi)
        b = fb + (r['start_rad'] + r['arc_rad']) / (2 * math.pi)
        if a > pos + 1e-12:
            arcs.append(('air', pos, a, None))
        arcs.append((kind, a, b, r))
        pos = b
    if pos < 1 - 1e-12:
        arcs.append(('air', pos, 1.0, None))
    arcs[-1] = arcs[-1][:2] + (1.0,) + arcs[-1][3:]
    return arcs, table, fb


def _skin_arcs(pattern, h_spray, background, coolant, bite_flux):
    out = []
    for kind, a, b, r in pattern:
        if kind == 'bite':
            out.append({'kind': 'bite', 'start_fraction': a, 'end_fraction': b,
                        'heat_flux_w_m2': bite_flux, 'htc_w_m2k': 0.0,
                        'sink_temperature_k': None})
        elif kind == 'spray':
            out.append({'kind': 'spray', 'start_fraction': a, 'end_fraction': b,
                        'heat_flux_w_m2': 0.0, 'htc_w_m2k': h_spray,
                        'sink_temperature_k': coolant})
        elif kind == 'backup':
            out.append({'kind': 'backup', 'start_fraction': a, 'end_fraction': b,
                        'heat_flux_w_m2': 0.0, 'htc_w_m2k': r['conductance_w_m2k'],
                        'sink_temperature_k': r['backup_surface_temperature_k']})
        else:
            out.append({'kind': 'air', 'start_fraction': a, 'end_fraction': b,
                        'heat_flux_w_m2': 0.0, 'htc_w_m2k': background,
                        'sink_temperature_k': coolant})
    return out


def roll_surface_cycle_section(case, w, th, actual, bite, steady):
    """``width.roll_surface_cycle`` (SPEC18 package 10): the per-revolution surface layer on top
    of the steady circumferential-mean field, per axial station (one-way)."""
    from . import roll_skin
    lay = w['circumferential_layout']
    if lay is None:
        return not_supplied('width_model.circumferential_layout is null or absent')
    if actual is None:
        return not_assessable('needs the steady thermal solution')
    if bite is None:
        return not_assessable('needs the case-pass bite (contact length and forward slip)')
    roll, hdr = th.roll, th.header
    radius = roll.radius_m
    k = roll.conductivity_w_mk
    rho_c = roll.density_kg_m3 * roll.specific_heat_j_kgk
    tc = w['coolant_temperature_k']
    u = case['pass']['exit_speed_m_s']
    v_r = u / (1 + bite.forward_slip_fraction)
    t_rev = 2 * math.pi * radius / v_r
    ld = bite.contact_length_m
    pattern, table, fb = surface_cycle_layout(w, radius, ld)
    phi = sum(r['arc_rad'] for r in lay['spray_arcs'])
    bg, hm = hdr.background_htc_w_m2k, hdr.spray_mean_htc_w_m2k
    z, weights = actual['z_m'], actual['spray_weight']
    qmean = actual['heat_flux_w_m2']
    depth = roll_skin.LAYER_DEPTH_FACTOR * math.sqrt(k / rho_c * t_rev)
    t_deep = _deep_temperature(actual['field'], depth, radius)
    t_bk = lay['backup_contact']['backup_surface_temperature_k'] if lay['backup_contact'] \
        else None
    wl, wh = min(weights), max(weights)
    grid = sorted({wl + (wh - wl) * i / (SURFACE_CYCLE_WEIGHTS - 1)
                   for i in range(SURFACE_CYCLE_WEIGHTS)} | ({0.0} if 0.0 in weights else set()))

    def h_spray(wt):
        return bg + hm * wt * 2 * math.pi / phi
    units = []
    for wt in grid:
        units.append(roll_skin.unit_solutions(
            conductivity_w_mk=k, volumetric_heat_capacity_j_m3k=rho_c, revolution_time_s=t_rev,
            arcs=_skin_arcs(pattern, h_spray(wt), bg, tc, 1.0), coolant_temperature_k=tc,
            tolerance_k=SURFACE_CYCLE_TOLERANCE_K))
    tf = units[0]['time_fraction']
    dts = [b - a for a, b in zip([0.0] + tf[:-1], tf)]
    kinds = []      # (kind, arc) per step
    arcs0 = _skin_arcs(pattern, 0.0, bg, tc, 1.0)
    for f in tf:
        a = next(x for x in arcs0 if x['start_fraction'] < f <= x['end_fraction'] + 1e-12)
        kinds.append(a)

    def unit_at(wt, key):
        if len(grid) == 1:
            return units[0][key]
        i = max(0, min(len(grid) - 2, max(j for j in range(len(grid)) if grid[j] <= wt)
                       if wt >= grid[0] else 0))
        f = (wt - grid[i]) / (grid[i + 1] - grid[i])
        a, b = units[i][key], units[i + 1][key]
        return None if a is None else [x + f * (y - x) for x, y in zip(a, b)]
    rows = {'bite_entry_temperature_k': [], 'bite_exit_temperature_k': [],
            'minimum_temperature_k': [], 'mean_surface_temperature_k': [], 'swing_k': [],
            'mean_coefficient_ratio': [], 'mean_model_surface_temperature_k': [],
            'mean_minus_mean_model_k': []}
    histories = []
    bite_last = max(i for i, a in enumerate(kinds) if a['kind'] == 'bite')
    for j, (wt, qm, td) in enumerate(zip(weights, qmean, t_deep)):
        qb = qm * 2 * math.pi * radius / ld
        ua, ub = unit_at(wt, 'per_unit_bite_flux_k_per_w_m2'), unit_at(wt, 'per_unit_deep_excess')
        uc = unit_at(wt, 'per_unit_backup_excess')
        ts = [tc + qb * x + (td - tc) * y for x, y in zip(ua, ub)]
        if uc is not None:
            ts = [t + (t_bk - tc) * c for t, c in zip(ts, uc)]
        mean = sum(t * d for t, d in zip(ts, dts))
        hs = [h_spray(wt) if a['kind'] == 'spray' else a['htc_w_m2k'] for a in kinds]
        sinks = [tc if a['sink_temperature_k'] is None else a['sink_temperature_k']
                 for a in kinds]
        mean_h = sum(h * d for h, d in zip(hs, dts))
        hq = sum(h * (t - s_) * d for h, t, s_, d in zip(hs, ts, sinks, dts))
        ratio = (hq / (mean - tc)) / mean_h if mean != tc and mean_h > 0 else None
        rows['bite_entry_temperature_k'].append(ts[-1])
        rows['bite_exit_temperature_k'].append(ts[bite_last])
        rows['minimum_temperature_k'].append(min(ts))
        rows['mean_surface_temperature_k'].append(mean)
        rows['swing_k'].append(max(ts) - min(ts))
        rows['mean_coefficient_ratio'].append(ratio)
        mm = actual['surface_temperature_k'][j]
        rows['mean_model_surface_temperature_k'].append(mm)
        rows['mean_minus_mean_model_k'].append(mean - mm)
        histories.append(ts)
    # the three stations
    stations = [('strip centre', th.centre)]
    stripes = (steady or {}).get('stripes') or []
    if stripes:
        big = max(stripes, key=lambda s_: abs(s_['peak_deviation_m']))
        stations.append(('largest steady stripe', big['peak_position_m']))
    healthy = [x for x, lv in zip(th.positions, th.levels) if lv == 1.0]
    if healthy:
        stations.append(('first station under a healthy nozzle', healthy[0]))
    angle = [math.degrees((f - fb) * 2 * math.pi) % 360.0 for f in tf]
    cycles = []
    for name, x in stations:
        j = min(range(len(z)), key=lambda i: abs(z[i] - x))
        cycles.append({'station': name, 'z_m': z[j], 'angle_from_bite_exit_deg': angle,
                       'time_fraction_from_bite_entry': tf,
                       'surface_temperature_k': histories[j],
                       'bite_entry_temperature_k': rows['bite_entry_temperature_k'][j],
                       'bite_exit_temperature_k': rows['bite_exit_temperature_k'][j],
                       'minimum_temperature_k': rows['minimum_temperature_k'][j],
                       'mean_surface_temperature_k': rows['mean_surface_temperature_k'][j],
                       'mean_model_surface_temperature_k':
                           rows['mean_model_surface_temperature_k'][j]})
    scales = roll_skin.time_scales(
        conductivity_w_mk=k, volumetric_heat_capacity_j_m3k=rho_c, revolution_time_s=t_rev,
        radius_m=radius, mean_htc_w_m2k=bg + hm,
        event_durations_s=[e['duration_s'] for e in w['events']])
    flags = [CYCLE_FLAG]
    ratios = [r for r in rows['mean_coefficient_ratio'] if r is not None]
    worst = max(ratios, key=lambda r: abs(r - 1)) if ratios else None
    bias = None
    if worst is not None and abs(worst - 1) > MEAN_COEFFICIENT_BIAS:
        flags.append(CYCLE_BIAS_FLAG)
    if worst is not None:
        bias = (f'The effective mean cooling coefficient of this layout is {worst:.3f} of the '
                f'circumferential mean at the most affected station: the mean model '
                + ('over' if worst < 1 else 'under') + f'-states the cooling by '
                f'{abs(1 - worst) * 100:.1f} %. Reported only; the bulk model is not corrected.')
    return {'status': roll_skin.STATUS, 'not_supplied': False, 'z_m': z, **rows,
            'cycles': cycles, 'layout_used': table, 'layout_provenance': lay['provenance'],
            'revolution_time_s': t_rev, 'roll_surface_speed_m_s': v_r,
            'bite_fraction_of_revolution': fb, 'layer_depth_m': depth,
            'deep_temperature_k': t_deep,
            'unit_solution_weights': grid, 'time_scales': scales, 'bias_sentence': bias,
            'worst_mean_coefficient_ratio': worst,
            'basis': {'model': '[D, re-derived in SPEC18] periodic 1D layer under the surface '
                               '(roll_skin), deep boundary at 6*sqrt(a*t_rev) held at the '
                               'steady circumferential-mean temperature; linear in the bite '
                               'flux, the deep and the backup excess, interpolated linearly '
                               f'in the spray weight between {len(grid)} unit solutions [D]',
                      'spray_coefficient': 'background + spray_mean_htc*weight*2*pi/phi on the '
                                           'spray arcs (the footprint identity of SPEC17 '
                                           'package 3: the angular mean equals the mean model)',
                      'bite_flux': 'circumferential-mean flux of the steady model x 2*pi*R/l_d '
                                   'under the strip, no cooling in the bite',
                      'time_scale_kinds': scales['scale_meaning']},
            'flags': flags, 'limitations': list(roll_skin.LIMITATIONS) + [
                'One-dimensional layer per axial station: no axial conduction inside the layer '
                '(the bulk field carries it). With sprays all round on the template case the '
                'layer mean departs from the mean model by up to about 0.4 K at the nozzle scale '
                'and 0.5 K at the strip edges; averaged over a nozzle pitch, by less than 1 % of '
                'the surface excess in the strip interior [run].']}


def not_assessable(reason):
    return {'status': 'NOT_ASSESSABLE', 'not_supplied': False, 'reason': reason}


def thermal_heat_inputs(w, trib, heat_row):
    """(roll heat fraction per roll, its basis, bite heat per width, its basis, computed strip
    share or None) of the steady thermal problem: the ONE place the width section and the spray
    calibration (band_thermal.calibrate_spray_coefficient) take them from."""
    f_c = ((heat_row or {}).get('heat_partition') or {}).get('strip_heat_fraction_computed')
    if w['roll_heat_fraction_per_roll'] is not None:
        fraction, fbasis = w['roll_heat_fraction_per_roll'], 'supplied'
    elif use_computed_heat_partition(trib) and f_c is not None:
        # SPEC18 package 9: the case pass's computed share (clipped to [0, 1])
        fraction = (1 - min(1.0, max(0.0, f_c))) / 2
        fbasis = ('computed: (1 - strip share of the bite heat partition of the case pass)/2 '
                  '(tribology.use_computed_heat_partition)')
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
        heat, hbasis = None, None
    return fraction, fbasis, heat, hbasis, f_c


def width_section(case, bite, get_bite, heat_row, trib, flags, bite_error=None,
                  friction_sensitivity=None, friction_row=None, friction_get_bite=None):
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
    fraction, fbasis, heat, hbasis, f_c = thermal_heat_inputs(w, trib, heat_row)
    thermal_reason = None
    if heat is None:
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
    # SPEC18 package 10: the roll surface within one revolution (one-way, key only additive)
    try:
        out['roll_surface_cycle'] = roll_surface_cycle_section(case, w, th, actual, bite, steady)
        if out['roll_surface_cycle'].get('status') == 'UNVALIDATED_ROLL_SURFACE_CYCLE':
            out['flags'] += [f for f in out['roll_surface_cycle']['flags']
                             if f not in out['flags']]
    except ValueError as exc:
        out['roll_surface_cycle'] = not_assessable(str(exc))
    shape = {'steady': None, 'nozzle_pattern_ripple': None, 'crown': None, 'ridges': []}
    if steady is not None and sp is None:
        shape['steady'] = not_assessable(shape_reason)
        shape['nozzle_pattern_ripple'] = not_assessable(shape_reason)
    elif steady is not None:
        try:
            lv = shape_levels(steady['z_m'], steady['local_deviation_m'], sp)
            shape['steady'] = lv
            shape['steady_stripe_table'] = steady_stripe_table(steady, lv, sp)
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
            from . import band_thermal
            out['thermal_events'] = _events_section(
                th, sp, actual, w['events'], shape_reason,
                scales=band_thermal.event_scales(case, th.fraction))
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
    try:
        a0, a1 = th.centre - th.width / 2, th.centre + th.width / 2
        out['strip_temperature'] = strip_temperature_section(
            case, w, shape['steady'], [x for x in z if a0 <= x <= a1], a0, a1)
    except ValueError as exc:
        out['strip_temperature'] = failed('strip_temperature', exc)
        out['failures'].append(out['strip_temperature']['error'])
    st_flags = (out['strip_temperature'].get('flags') or []) if isinstance(
        out['strip_temperature'], dict) else []
    flags += [f for f in st_flags if f not in flags]
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
        from . import band_thermal
        t_shape = (band_thermal.thermal_shape_off_case_share(case, th, steady,
                                                              sys.modules[__name__])
                   if steady and not steady['stripes'] else None)
        out['gauge_trend'] = _gauge_trend(case, w, get_bite, steady, th.centre, w['coil'], z,
                                          bite, shape_reason, t_shape)
    except ValueError as exc:
        out['gauge_trend'] = failed('gauge_trend', exc)
        out['failures'].append(out['gauge_trend']['error'])
    # SPEC14 Part 3: heat partition and spray coefficient sensitivity of the stripe result
    try:
        from . import band_thermal
        out['thermal_sensitivity'] = band_thermal.thermal_sensitivity(
            case, w, th, sp, steady, actual, out['thermal_events'], sys.modules[__name__],
            shape.get('steady_stripe_table') if isinstance(shape, dict) else None)
    except (ValueError, ArithmeticError) as exc:
        # an optional block: no error inside it may abort the diagnosis
        out['thermal_sensitivity'] = failed('thermal_sensitivity', exc)
        out['failures'].append(out['thermal_sensitivity']['error'])
        flags.append('THERMAL_SENSITIVITY_FAILED')
    ts = out['thermal_sensitivity']
    if f_c is not None and isinstance(ts, dict) and ts.get('status') == 'EVALUATED':
        # SPEC18 package 9: the computed share beside the rows (the stripes stay those above)
        ts['computed_strip_share'] = {
            'strip_heat_share': f_c, 'roll_heat_fraction_per_roll': (1 - f_c) / 2,
            'used_by_the_rows_above': fbasis.startswith('computed'),
            'note': 'strip share of the bite heat partition of the case pass '
                    '(process.heating.operating.heat_partition); the rows above are evaluated '
                    'at their own shares'}
    # SPEC17 G13: a measured roll ground profile through the existing transfer
    try:
        out['roll_profile'] = roll_profile_section(case, w, sp, shape_reason, z, th,
                                                   out.get('thermal_steady'), bite)
    except (ValueError, ArithmeticError) as exc:
        out['roll_profile'] = failed('roll_profile', exc)
        out['failures'].append(out['roll_profile']['error'])
    rp_flags = [f for f in ((out['roll_profile'].get('flags') or []) if isinstance(
        out['roll_profile'], dict) else []) if f in (RP_FLAG_SUPPLIED, RP_FLAG_BAND)]
    flags += [f for f in rp_flags if f not in flags]
    # SPEC17 BT-G4: friction / film stripes as a second band source (screening version)
    try:
        out['friction_stripes'] = friction_stripes_section(
            case, w, bite, friction_get_bite or get_bite, friction_sensitivity,
            shape.get('steady'), th,
            trib, friction_row, bite_error)
    except (ValueError, ArithmeticError) as exc:
        out['friction_stripes'] = failed('friction_stripes', exc)
        out['failures'].append(out['friction_stripes']['error'])
    fs_flags = (out['friction_stripes'].get('flags') or []) if isinstance(
        out['friction_stripes'], dict) else []
    flags += [f for f in fs_flags if f not in flags]
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
        # SPEC17 G12: radii in the case, for the candidate tension-line pitch
        self.radii = _case_radii(case)
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
        # review fix: a trough spacing needs a stated spacing or at least two regular gaps
        # (three or more bands, CV <= 0.1); one gap, or irregular gaps, between bands that may
        # have different causes cannot establish one
        established = (o['band_spacing_m'] is not None
                       or (len(f.gaps) >= 2 and bool(f.spacing and f.spacing.get('regular'))))
        if not established:
            why = ('one gap between two bands cannot establish a spacing' if len(f.gaps) < 2
                   else 'irregular gaps cannot establish a spacing')
            txt += f' ({why})'
        if any(0.5 <= r <= 2 for _, r in ratios):
            e.append(ev(crit, txt, '0.5-2 x wavelength (either span)', 'SUPPORTS',
                        'strong' if established else 'weak'))
        elif all(r < 0.25 or r > 4 for _, r in ratios) and established:
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
    # SPEC17 (BT-G8, X21): the film-ratio label no longer supports. A film ratio below 1 is
    # normal mixed-regime operation (substantial asperity contact, a good roll imprint)
    # [BT-S3 EX, BT-S9 EX]; only an exit temperature above the supplied limit supports. The
    # film-collapse test of the gap study (film against additive length or contact
    # temperature) is NOT built: it needs BT-G3 / BT-G11.
    expected = ('above the temperature limit (a film ratio below 1 is normal mixed-regime '
                'operation and no longer counts [BT-S3 EX, BT-S9 EX])')
    if regime is None and hot is None:
        e.append(ev(crit, 'no tribology', expected, 'NOT_OBSERVED', basis='input'))
    elif hot:
        e.append(ev(crit, f'regime {regime}; exit temperature above limit: {hot}', expected,
                    'SUPPORTS', 'weak', 'model'))
    else:
        e.append(ev(crit, f'regime {regime}; exit temperature above limit: {hot}', expected,
                    'NEUTRAL', basis='model'))
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
               'case_exit_thickness_m': h,
               'candidate_shell_buckling_pitch': candidate_tension_line_pitch(
                   h, f.radii, None if f.gaps is None else (
                       o['band_spacing_m'] if o['band_spacing_m'] is not None
                       else sum(f.gaps) / len(f.gaps)))}


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
