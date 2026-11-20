"""Local state across the width (SPEC19 package 1; gap rows A2 inputs, BT-G12, A1 computed).

Status ``SCREENING_RESULT_NOT_PLANT_VALIDATED``. Integration layer (style of ``band_thermal``):
it reads the case and finished result sections and evaluates the single-station pieces of
SPEC18 (viscosity law, friction closure, heat partition) at every width station of the steady
thermal grid. It makes no band (SPEC19 package 2 does) and feeds nothing back.

Difference method: everything is a difference from the healthy header at the same pass, as
the radius stripes are (``band_width._steady_section``); a healthy header gives zero
everywhere. Per strip sample ``z`` (``ref`` = healthy header):

1. ``dT_r(z) = T_r,actual(z) - T_r,healthy(z)`` [K]: the roll surface temperature the bite
   meets, ``width.roll_surface_cycle.bite_entry_temperature_k`` minus its
   ``healthy_bite_entry_temperature_k`` when the surface cycle exists (SPEC18 package 10), else
   the circumferential-mean surface temperature of the bulk model (flag
   ``LOCAL_STATE_FROM_CIRCUMFERENTIAL_MEAN_SURFACE_TEMPERATURE``).
2. ``T_in(z) = tribology.inlet_temperature_k + w_in*dT_r(z)``; ``w_in`` =
   ``inlet_roll_temperature_weight`` [D, SPEC19: analyst choice; 0.5 the two-surface mean, 1.0
   the bound of the bite report, gap BT-G4 [derived]].
3. ``v(z) = eta0(T_in(z))/eta0(T_in,ref)``, ``Lubricant.dynamic_viscosity_pa_s(T, 0.0)``
   (exponential law or table, SPEC18 package 5).
4. ``h_s(z) = h_s,ref*v(z)``, ``Lambda_s(z) = Lambda_ref*v(z)``: the inlet film is
   proportional to eta0 [BT-S9 EX eq. 4.1 as coded in ``bite_tribology.inlet_film_thickness``;
   with ``tribology.thermal_correction`` the factor phi_T also depends on eta0 and the
   proportional form is an approximation].
5. Supplied film [D, re-derived in SPEC19: volume balance; the film cannot carry more oil than
   arrives]: ``q'(z) = Q_nozzle*capture*weight(z)/pitch`` [m2/s] (weight = the spray weight of
   the ACTUAL nozzle levels, 1 for a healthy header away from the barrel ends);
   ``h_sup(z) = q'(z)/u_bar``, ``u_bar = (V_r + u_entry)/2``, ``V_r = u_exit/(1 + f)``,
   ``u_entry = u_exit*h1/h0``. Film used ``h = min(h_s, h_sup)``,
   ``Lambda = Lambda_s*h/h_s``, ``starved = h_sup < h_s``. Without a flow: ``h = h_s``.
6. ``dmu(z) = mu_cl(Lambda(z)) - mu_cl(Lambda_ref)`` with the case's closure
   (``bite_tribology.friction_coefficient``; the valley models get the case-pass bite state).
   Only the DIFFERENCE is used; ``Lambda <= 0`` is evaluated at ``LAMBDA_FLOOR``.
7. ``dY_rel(z) = -c_T*dT_b(z)``, ``dT_b = 0.5*eta_x*dT_r`` [form: gap A2,
   ``Y = Y_ref*(1 - c_T*(T - T_ref))``; mid-bite temperature as in SPEC18 package 8].
8. ``eta_x = T_x(T_r0 + 1 K) - T_x(T_r0)`` from two evaluations of the case pass's heat
   partition (SPEC18 package 9, ``band_process.pass_heat_partition``); the model is linear in
   ``T_r0``, so the 1 K difference is exact [D, SPEC19]. A supplied value overrides.
9. ``dT_x = eta_x*dT_r``; ``T_x(z) = T_x,ref + dT_x`` with ``T_x,ref`` the case pass's modelled
   exit temperature (``process.heating.operating.exit_temperature_k``). The change of friction
   heat with ``dmu`` is second order and left out.

A1 computed: ``thermal_flatness = strip_shape.thermal_flatness_term(z, T_x)`` beside the
supplied-scan section ``width.strip_temperature`` (which is not changed).

NOT modelled: any feedback of the local friction, force, slip or heat into the bite, the heat
row or the roll temperature (loop I1 stays open); lateral spreading or carry-over of oil; an
inlet meniscus position (BT-G12 is reduced to a volume balance, SPEC19 finding 9); roughness
across the barrel; a strip entry temperature across the width.
"""
import math

from . import bite_tribology as bt
from . import strip_shape as ss
from .band_process import (bite_mean_pressure_pa, keys, not_supplied, num,
                           pass_heat_partition, tribology_objects)

STATUS = 'SCREENING_RESULT_NOT_PLANT_VALIDATED'
WHERE = 'width_model.local_coupling'
LOCAL_KEYS = ('inlet_roll_temperature_weight', 'flow_stress_temperature_coefficient_per_k',
              'strip_roll_temperature_coupling', 'oil_flow_per_nozzle_m3_s',
              'oil_capture_fraction')
DEFAULT_INLET_WEIGHT = 0.5          # [D, SPEC19: analyst choice] two-surface mean
DEFAULT_CAPTURE_FRACTION = 1.0      # [D, SPEC19] all oil of the nozzle reaches the roll
LAMBDA_FLOOR = 1e-6                 # [SPEC19 formula 6] Lambda <= 0 evaluated here
FRICTION_CHANGE_INDICATIVE = 0.2    # [SPEC19] |dmu|/mu above this: linear source indicative
ETA_STEP_K = 1.0                    # [D, SPEC19] the heat partition is linear in T_r0

FLAG_COMPUTED = 'LOCAL_STATE_COMPUTED'
FLAG_MEAN_SURFACE = 'LOCAL_STATE_FROM_CIRCUMFERENTIAL_MEAN_SURFACE_TEMPERATURE'
FLAG_PLACEHOLDER = 'LOCAL_FRICTION_FROM_PLACEHOLDER_CLOSURE_SLOPE'
FLAG_STARVED = 'OIL_SUPPLY_BELOW_SMOOTH_FILM'
FLAG_ZERO_SUPPLY = 'ZERO_OIL_SUPPLY_UNDER_BLOCKED_NOZZLE_NO_SPREADING_MODEL'
FLAG_LARGE_FRICTION = 'LOCAL_FRICTION_CHANGE_ABOVE_20_PERCENT_LINEAR_SOURCE_INDICATIVE'
TOP_LEVEL_FLAGS = (FLAG_COMPUTED, FLAG_MEAN_SURFACE, FLAG_PLACEHOLDER, FLAG_STARVED,
                   FLAG_ZERO_SUPPLY, FLAG_LARGE_FRICTION)

LIMITATIONS = (
    'Differences from the healthy header only: a healthy header gives zero everywhere.',
    'The inlet temperature weight is an assumption (no measurement of the oil temperature at '
    'the inlet across the width exists).',
    'One-way: the local force, slip and heat changes do not return to the roll temperature '
    '(loop I1 stays open).',
    'The change of the friction heat with the local friction is left out (second order).',
    'No lateral spreading or carry-over of oil: a fully blocked nozzle gives zero supplied '
    'film under it.',
    'Roughness uniform across the barrel (a rougher or coated barrel zone is entered through '
    'the friction stripe screen of width_model.friction_stripe_screen).',
    'The strip entry temperature is uniform across the width.')

BASIS = {
    'formula_1': 'dT_r = T_r,actual - T_r,healthy at the same pass (difference method of the '
                 'radius stripes) [D, SPEC19]',
    'formula_2': 'T_in = tribology.inlet_temperature_k + w_in*dT_r; w_in [D, SPEC19: analyst '
                 'choice]',
    'formula_3': 'v = eta0(T_in)/eta0(T_in,ref), Lubricant.dynamic_viscosity_pa_s(T, 0) '
                 '(exponential law or viscosity table, SPEC18)',
    'formula_4': 'h_s = h_s,ref*v, Lambda_s = Lambda_ref*v: inlet film proportional to eta0 '
                 '[BT-S9 EX eq. 4.1 as coded in bite_tribology.inlet_film_thickness]',
    'formula_5': "h_sup = Q*capture*weight/(pitch*u_bar), u_bar = (V_r + u_entry)/2; h = "
                 "min(h_s, h_sup) [D, re-derived in SPEC19: volume balance; the film cannot "
                 "carry more oil than arrives]",
    'formula_6': 'dmu = mu_cl(Lambda) - mu_cl(Lambda_ref) with the case\'s friction closure; '
                 'only the difference is used, the level stays the pass friction',
    'formula_7': 'dY_rel = -c_T*dT_b, dT_b = 0.5*eta_x*dT_r [form: gap A2, Y = Y_ref*(1 - '
                 'c_T*(T - T_ref)); mid-bite temperature as in SPEC18]',
    'formula_8': 'eta_x = T_x(T_r0 + 1 K) - T_x(T_r0), two evaluations of the case pass\'s '
                 'heat partition; exact because the model is linear in T_r0 [D, SPEC19]',
    'formula_9': 'dT_x = eta_x*dT_r; T_x = T_x,ref + dT_x, T_x,ref the case pass\'s modelled '
                 'exit temperature; friction heat change left out'}


# ============================================================================= validation
def _ranged(key, value, lo, hi, lo_open=False):
    where = f'{WHERE}.{key}'
    words = f'in {"(" if lo_open else "["}{lo:g}, {hi:g}]'
    try:
        v = num(where, value)
    except ValueError:
        raise ValueError(f'{where} must be a number {words}') from None
    if (v <= lo if lo_open else v < lo) or v > hi:
        raise ValueError(f'{where} must be {words}')
    return v


def validate_local_coupling(lc):
    """``width_model.local_coupling`` (SPEC19 package 1), or None. Strict keys; ``provenance``
    required, every other key optional with its default."""
    if lc is None:
        return None
    keys(WHERE, lc, ('provenance',), LOCAL_KEYS)
    prov = lc['provenance']
    if not isinstance(prov, str) or not prov.strip():
        raise ValueError(f'{WHERE}.provenance must be a nonempty string')
    out = {'inlet_roll_temperature_weight': _ranged(
               'inlet_roll_temperature_weight',
               lc.get('inlet_roll_temperature_weight', DEFAULT_INLET_WEIGHT), 0.0, 1.0),
           'flow_stress_temperature_coefficient_per_k': None,
           'strip_roll_temperature_coupling': None, 'oil_flow_per_nozzle_m3_s': None,
           'oil_capture_fraction': _ranged(
               'oil_capture_fraction',
               lc.get('oil_capture_fraction', DEFAULT_CAPTURE_FRACTION), 0.0, 1.0, True),
           'provenance': prov}
    for key, lo, hi, lo_open in (('flow_stress_temperature_coefficient_per_k', 0.0, 0.01, False),
                                 ('strip_roll_temperature_coupling', 0.0, 1.5, False),
                                 ('oil_flow_per_nozzle_m3_s', 0.0, 0.1, True)):
        if lc.get(key) is not None:
            out[key] = _ranged(key, lc[key], lo, hi, lo_open)
    return out


# ============================================================================= parameters
def _bite_state(case, bite, trib, v_r, u_entry):
    """The case-pass bite state of the computed valley models (as
    ``bite_tribology.friction_at_speed`` builds it from the pass)."""
    h0, h1 = case['pass']['entry_thickness_m'], case['pass']['exit_thickness_m']
    f = u_entry * h0 / (v_r * h1) - 1
    b = 1 - u_entry / v_r
    return {'mean_pressure_pa': bite_mean_pressure_pa(case, bite),
            'mean_sliding_speed_m_s': abs(v_r * (b + f) / 2),
            'inlet_temperature_k': trib['inlet_temperature_k']}


def _eta_x(case, trib, bite, heat_row, friction_row, supplied):
    """(eta_x or None, basis sentence, details or None)."""
    if supplied is not None:
        return supplied, 'supplied (width_model.local_coupling.strip_roll_temperature_coupling)', \
            None
    part = (heat_row or {}).get('heat_partition')
    if not isinstance(part, dict) or part.get('status') != bt.STATUS_HEAT_PARTITION:
        reason = (part or {}).get('reason') or (part or {}).get('error') or \
            'no heat partition of the case pass'
        return None, f'not computed: {reason}', None
    t0 = part['roll_entry_surface_temperature_k']
    runs = []
    for t in (t0, t0 + ETA_STEP_K):
        runs.append(pass_heat_partition(
            case, case['pass'], bite, trib, heat_row['plastic_power_per_width_w_m'],
            heat_row['friction_power_per_width_w_m'], friction_row,
            roll_entry=(t, 'SPEC19 package 1: strip-to-roll temperature coupling')))
    eta = (runs[1]['strip_exit_temperature_k'] - runs[0]['strip_exit_temperature_k']) / ETA_STEP_K
    r = runs[0]
    details = {'contact_time_s': r['contact_time_s'],
               'strip_capacity_j_m2k': r['strip_capacity_j_m2k'],
               'interface_conductance_w_m2k': r['interface_conductance_w_m2k'],
               'roll_entry_surface_temperature_k': t0}
    return eta, ('computed (formula 8): T_x(T_r0 + 1 K) - T_x(T_r0) of the case pass\'s heat '
                 f'partition (contact time {r["contact_time_s"]:.4g} s, C_s '
                 f'{r["strip_capacity_j_m2k"]:.4g} J/m2K, h_c '
                 f'{r["interface_conductance_w_m2k"]:.4g} W/m2K) [D, SPEC19]'), details


def local_params(case, w, trib, lub, closure, surface, bite, heat_row, friction_row, cycle, *,
                 z_strip=None, spray_weight=None, nozzle_level=None):
    """Everything of the local state that does not depend on the temperature profile.

    ``lub``, ``closure``, ``surface``: the case's ``Lubricant``, ``FrictionClosure`` and
    ``SurfaceFinish``; ``cycle``: ``width.roll_surface_cycle`` (or None). ``z_strip``,
    ``spray_weight`` and ``nozzle_level`` (keyword-only, on the strip samples: the spray weight
    of the actual levels and the level of the nearest nozzle) give the supply profile; without
    them the supply check is off. Raises ValueError when an input is missing."""
    lc = w['local_coupling']
    p = case['pass']
    fr = friction_row or {}
    lam_ref, h_ref = fr.get('film_ratio'), fr.get('film_thickness_m')
    if not lam_ref or not h_ref:
        raise ValueError('needs the film ratio and film thickness of the case pass '
                         '(process.friction.operating)')
    u = p['exit_speed_m_s']
    v_r = u / (1 + bite.forward_slip_fraction)
    u_entry = u * p['exit_thickness_m'] / p['entry_thickness_m']
    u_bar = (v_r + u_entry) / 2
    state = _bite_state(case, bite, trib, v_r, u_entry) \
        if closure.model == 'load_sharing_curve' else None
    ref = bt.friction_coefficient(lam_ref, closure, lubricant=lub, finish=surface,
                                  bite_state=state)
    flags = [FLAG_COMPUTED]
    have_cycle = isinstance(cycle, dict) and \
        cycle.get('healthy_bite_entry_temperature_k') is not None
    if not have_cycle:
        flags.append(FLAG_MEAN_SURFACE)
    if closure.model == 'placeholder_exponential':
        flags.append(FLAG_PLACEHOLDER)
    # flow-stress coefficient
    c_t = lc['flow_stress_temperature_coefficient_per_k']
    rt = (case.get('hardening') or {}).get('rate_temperature')
    if c_t is not None:
        c_basis = 'supplied (width_model.local_coupling.flow_stress_temperature_coefficient_per_k)'
    elif rt is not None:
        c_t = rt['temperature_coefficient_per_k']
        c_basis = 'hardening.rate_temperature.temperature_coefficient_per_k (SPEC18)'
    else:
        c_basis = ('not supplied and no hardening.rate_temperature: the flow-stress change is '
                   'not evaluated')
    eta, eta_basis, eta_details = _eta_x(case, trib, bite, heat_row, friction_row,
                                         lc['strip_roll_temperature_coupling'])
    t_x_ref = (heat_row or {}).get('exit_temperature_k')
    supply = None
    if lc['oil_flow_per_nozzle_m3_s'] is not None and z_strip is not None:
        pitch = w['spray_header']['nozzle_pitch_m']
        q_unit = lc['oil_flow_per_nozzle_m3_s'] * lc['oil_capture_fraction'] / pitch
        if len(spray_weight) != len(z_strip) or len(nozzle_level) != len(z_strip):
            raise ValueError('the supply profile needs one weight and level per strip sample')
        healthy_sup = q_unit / u_bar
        supply = {'q_per_length_m2_s': [q_unit * wt for wt in spray_weight],
                  'nozzle_level': list(nozzle_level),
                  'healthy_supplied_film_m': healthy_sup,
                  'ratio_to_smooth_film': healthy_sup / h_ref,
                  'level_below_which_starved': h_ref / healthy_sup}
    return {'inlet_roll_temperature_weight': lc['inlet_roll_temperature_weight'],
            'flow_stress_temperature_coefficient_per_k': c_t, 'coefficient_basis': c_basis,
            'strip_roll_temperature_coupling': eta, 'coupling_basis': eta_basis,
            'coupling_details': eta_details, 'strip_exit_temperature_ref_k': t_x_ref,
            'inlet_temperature_ref_k': trib['inlet_temperature_k'],
            'film_ratio_ref': lam_ref, 'film_thickness_ref_m': h_ref,
            'friction_ref': ref['friction_coefficient'], 'dmu_dlambda_ref': ref['dmu_dlambda'],
            'pass_friction': p['friction_coefficient'], 'mean_entrainment_speed_m_s': u_bar,
            'roll_surface_speed_m_s': v_r, 'strip_entry_speed_m_s': u_entry,
            'supply': supply, 'z_strip': None if z_strip is None else list(z_strip),
            'bite_state': state, 'closure_model': closure.model,
            'closure_flags': list(ref['flags']), 'lubricant': lub, 'closure': closure,
            'surface': surface, 'surface_basis': ('cycle' if have_cycle else 'mean'),
            'flags': flags}


def local_changes(z_strip, d_surface_temperature_k, params):
    """Formulas 2-9 for a roll-surface temperature difference profile (steady or a snapshot)
    on the strip samples ``z_strip``. Returns the profiles and the conditional flags."""
    z = list(z_strip)
    dtr = [float(x) for x in d_surface_temperature_k]
    if len(dtr) != len(z):
        raise ValueError('d_surface_temperature_k needs one value per strip sample')
    lub, clo, fin = params['lubricant'], params['closure'], params['surface']
    w_in = params['inlet_roll_temperature_weight']
    t_ref = params['inlet_temperature_ref_k']
    eta_ref = lub.dynamic_viscosity_pa_s(t_ref, 0.0)
    lam_ref, h_ref = params['film_ratio_ref'], params['film_thickness_ref_m']
    mu_ref, mu_pass = params['friction_ref'], params['pass_friction']
    sup = params['supply']
    if sup is not None and len(sup['q_per_length_m2_s']) != len(z):
        raise ValueError('the supply profile was built on other strip samples')
    u_bar = params['mean_entrainment_speed_m_s']
    c_t, eta = params['flow_stress_temperature_coefficient_per_k'], \
        params['strip_roll_temperature_coupling']
    t_x_ref = params['strip_exit_temperature_ref_k']
    out = {k: [] for k in ('inlet_temperature_change_k', 'viscosity_ratio', 'film_ratio',
                           'smooth_film_thickness_m', 'film_thickness_m', 'friction_change',
                           'friction_change_fraction')}
    sup_film, starved = [], []
    flags = []
    for i, d in enumerate(dtr):
        d_in = w_in * d
        v = lub.dynamic_viscosity_pa_s(t_ref + d_in, 0.0) / eta_ref
        h_s, lam_s = h_ref * v, lam_ref * v
        h = h_s
        if sup is not None:
            h_sup = sup['q_per_length_m2_s'][i] / u_bar
            h = min(h_s, h_sup)
            sup_film.append(h_sup)
            starved.append(h_sup < h_s)
            if h_sup < h_s and sup['nozzle_level'][i] > 0 and FLAG_STARVED not in flags:
                flags.append(FLAG_STARVED)
            if h_sup == 0 and FLAG_ZERO_SUPPLY not in flags:
                flags.append(FLAG_ZERO_SUPPLY)
        lam = lam_s * h / h_s
        mu = bt.friction_coefficient(lam if lam > 0 else LAMBDA_FLOOR, clo, lubricant=lub,
                                     finish=fin, bite_state=params['bite_state'])
        dmu = mu['friction_coefficient'] - mu_ref
        out['inlet_temperature_change_k'].append(d_in)
        out['viscosity_ratio'].append(v)
        out['film_ratio'].append(lam)
        out['smooth_film_thickness_m'].append(h_s)
        out['film_thickness_m'].append(h)
        out['friction_change'].append(dmu)
        out['friction_change_fraction'].append(dmu / mu_pass)
        if abs(dmu) / mu_pass > FRICTION_CHANGE_INDICATIVE and FLAG_LARGE_FRICTION not in flags:
            flags.append(FLAG_LARGE_FRICTION)
    out['supplied_film_m'] = sup_film if sup is not None else None
    out['starved'] = starved if sup is not None else None
    if eta is not None:
        dtx = [eta * d for d in dtr]
        out['strip_exit_temperature_change_k'] = dtx
        out['mid_bite_strip_temperature_change_k'] = [0.5 * x for x in dtx]
        out['strip_exit_temperature_k'] = (None if t_x_ref is None
                                           else [t_x_ref + x for x in dtx])
        out['flow_stress_change_fraction'] = (None if c_t is None
                                              else [-c_t * 0.5 * x for x in dtx])
    else:
        out['strip_exit_temperature_change_k'] = None
        out['mid_bite_strip_temperature_change_k'] = None
        out['strip_exit_temperature_k'] = None
        out['flow_stress_change_fraction'] = None
    out['z_m'] = z
    out['roll_surface_temperature_change_k'] = dtr
    out['flags'] = flags
    return out


# ============================================================================= section
def not_assessable(reason):
    return {'status': 'NOT_ASSESSABLE', 'not_supplied': False, 'reason': reason}


def _strip_samples(th, steady):
    z_all = steady['z_m']
    a0, a1 = steady['strip_start_m'], steady['strip_end_m']
    idx = [i for i, x in enumerate(z_all) if a0 <= x <= a1]
    weights = th.header.weight_profile(z_all, th.levels)
    pos = th.positions
    near = []
    for i in idx:
        j = min(range(len(pos)), key=lambda k: abs(pos[k] - z_all[i]))
        near.append(th.levels[j])
    return idx, [z_all[i] for i in idx], [weights[i] for i in idx], near


def local_state_section(case, w, th, steady, trib, bite, heat_row, friction_row, cycle,
                        context=None):
    """``width.local_state`` (SPEC19 package 1): local state across the width as differences
    from the healthy header; ``not_supplied`` without ``width_model.local_coupling``.
    ``context`` (a dict, optional) receives the parameters, the changes and the strip sample
    indices for the source terms of package 2."""
    lc = w.get('local_coupling')
    if lc is None:
        return not_supplied('width_model.local_coupling is null or absent')
    if trib is None:
        return not_assessable('needs tribology (oil, surface finish, friction closure)')
    if not isinstance(steady, dict) or 'surface_temperature_k' not in steady:
        return not_assessable('needs the steady roll thermal solution')
    if bite is None:
        return not_assessable('needs the case-pass bite (forward slip, contact, heat '
                              'partition)')
    fr = friction_row or {}
    if fr.get('rejected') or not fr.get('film_ratio'):
        return not_assessable('needs the friction row of the case pass (film ratio and film '
                              'thickness)')
    lub, fin, clo = tribology_objects(trib)
    idx, z, weights, near = _strip_samples(th, steady)
    if len(z) < 3:
        raise ValueError('fewer than 3 strip samples for the local state')
    params = local_params(case, w, trib, lub, clo, fin, bite, heat_row, friction_row, cycle,
                          z_strip=z, spray_weight=weights, nozzle_level=near)
    if params['surface_basis'] == 'cycle':
        act, hea = cycle['bite_entry_temperature_k'], cycle['healthy_bite_entry_temperature_k']
        t_basis = ('width.roll_surface_cycle: bite entry temperature minus the healthy '
                   "header's (SPEC18 package 10)")
    else:
        act, hea = steady['surface_temperature_k'], steady['healthy_surface_temperature_k']
        t_basis = ('width.thermal_steady: circumferential-mean surface temperature minus the '
                   "healthy header's (no circumferential layout)")
    dtr = [act[i] - hea[i] for i in idx]
    ch = local_changes(z, dtr, params)
    if context is not None:
        context.update(params=params, changes=ch, z=z, idx=idx, dtr=dtr,
                       z_full=list(steady['z_m']))
    flags = list(params['flags']) + ch['flags']
    flags += [f for f in params['closure_flags'] if f not in flags]
    j = max(range(len(z)), key=lambda k: abs(dtr[k]))
    per_station = ('roll_surface_temperature_change_k', 'inlet_temperature_change_k',
                   'viscosity_ratio', 'film_ratio', 'film_thickness_m', 'supplied_film_m',
                   'starved', 'friction_change', 'friction_change_fraction',
                   'flow_stress_change_fraction', 'strip_exit_temperature_change_k',
                   'strip_exit_temperature_k')
    at = {'z_m': z[j]}
    for k in per_station:
        at[k] = None if ch[k] is None else ch[k][j]
    sup = params['supply']
    tf = None
    if ch['strip_exit_temperature_k'] is not None:
        t = ss.thermal_flatness_term(z, ch['strip_exit_temperature_k'])
        tf = {'i_units': t['i_units'], 'i_units_per_kelvin': t['i_units_per_kelvin'],
              'flags': t['flags'], 'formula_basis': t['formula_basis']}
    coef_reason = (None if ch['flow_stress_change_fraction'] is not None else
                   (params['coefficient_basis'] if params[
                       'flow_stress_temperature_coefficient_per_k'] is None
                    else 'needs the strip-to-roll temperature coupling: '
                         + params['coupling_basis']))
    return {'status': STATUS, 'not_supplied': False, 'provenance': lc['provenance'],
            'z_m': z,
            'roll_surface_temperature_change_k': dtr,
            'roll_surface_temperature_basis': t_basis,
            'inlet_temperature_change_k': ch['inlet_temperature_change_k'],
            'viscosity_ratio': ch['viscosity_ratio'], 'film_ratio': ch['film_ratio'],
            'film_thickness_m': ch['film_thickness_m'],
            'supplied_film_m': ch['supplied_film_m'], 'starved': ch['starved'],
            'friction_change': ch['friction_change'],
            'friction_change_fraction': ch['friction_change_fraction'],
            'flow_stress_change_fraction': ch['flow_stress_change_fraction'],
            'flow_stress_change_reason': coef_reason,
            'strip_exit_temperature_change_k': ch['strip_exit_temperature_change_k'],
            'strip_exit_temperature_k': ch['strip_exit_temperature_k'],
            'strip_exit_temperature_reference_k': params['strip_exit_temperature_ref_k'],
            'coupling': {
                'inlet_roll_temperature_weight': params['inlet_roll_temperature_weight'],
                'strip_roll_temperature_coupling': params['strip_roll_temperature_coupling'],
                'coupling_basis': params['coupling_basis'],
                'flow_stress_temperature_coefficient_per_k':
                    params['flow_stress_temperature_coefficient_per_k'],
                'coefficient_basis': params['coefficient_basis']},
            'at_largest_change': at,
            'supply': (not_supplied('width_model.local_coupling.oil_flow_per_nozzle_m3_s is '
                                    'null: no supply check') if sup is None else
                       {'healthy_supplied_film_m': sup['healthy_supplied_film_m'],
                        'ratio_to_smooth_film': sup['ratio_to_smooth_film'],
                        'level_below_which_starved': sup['level_below_which_starved'],
                        'mean_entrainment_speed_m_s': params['mean_entrainment_speed_m_s']}),
            'reference': {'film_ratio': params['film_ratio_ref'],
                          'film_thickness_m': params['film_thickness_ref_m'],
                          'closure_friction': params['friction_ref'],
                          'closure_slope_dmu_dlambda': params['dmu_dlambda_ref'],
                          'pass_friction': params['pass_friction'],
                          'inlet_temperature_k': params['inlet_temperature_ref_k']},
            'thermal_flatness': tf,
            'closure_model': params['closure_model'], 'basis': dict(BASIS), 'flags': flags,
            'limitations': list(LIMITATIONS)}


# ============================================================================= package 2
# Local sources as a band (SPEC19 package 2; gap rows A2, BT-G4 in full; I2). The film and
# flow-stress changes act as a local change of roll force per width at an unchanged gap
# (SPEC17 package 7, strip_shape.transfer_force_profile) [D, re-derived in SPEC17]:
#     dp0'_film = M_mu*dmu,  dp0'_flow = M_Y*Y_pass*dY_rel,  M = (dF/dX)/width of the pass bite
#     dh_k = G(lam_k)*dp0'_k,  G = 2*C/(1 + 2*C*Q_eff)   (with the exit-tension feedback)
#     I_X = 1e5*(eps_X - mean),  eps_X = -xi*dh_X/h_exit                          (flat entry)
# and the strip temperature term I_T = thermal_flatness_term(z, T_x) (package 1). Summed with
# the roll-growth term I_roll = width.shape.steady.i_units_linear_feedback (linear, before the
# band-wise saturation):
#     mechanical_net = I_roll + I_film + I_flow;   as_measured_hot = mechanical_net + I_T.
# Reported beside the steady shape; never added to it, to an event's peak shape or to evidence.
FAST_PATH_TIME_S = 20.0   # [D, SPEC19: analyst choice; the surface time scale is 8-25 s,
#                           computed in the thermal report]
SRC_FLAG_COMPUTED = 'LOCAL_SOURCES_COMPUTED'
SRC_FLAG_WEIGHT = 'LOCAL_NET_SIGN_DEPENDS_ON_INLET_WEIGHT'
SRC_FLAG_REVERSE = 'LOCAL_SOURCES_REVERSE_A_BAND'
SRC_FLAG_LINEAR = 'LOCAL_SOURCES_SUMMED_ON_LINEAR_PROFILE_SATURATION_NOT_APPLIED'
# added at the coordinator's request (not in SPEC19): a term of the net could not be evaluated
SRC_FLAG_MISSING = 'LOCAL_NET_INCOMPLETE_TERM_MISSING'
SOURCE_FLAGS = (SRC_FLAG_COMPUTED, SRC_FLAG_WEIGHT, SRC_FLAG_REVERSE, SRC_FLAG_LINEAR,
                SRC_FLAG_MISSING)
SIGN_NOTE = ('Roll growth makes the strip thinner and the fibre loose. A thinner oil film raises '
             'friction and force, makes the strip thicker and the fibre tight. Softer metal '
             'lowers the force and makes it loose. A hotter fibre reads loose while hot and that '
             'part is gone after cooling. Roll growth needs minutes; the other three follow the '
             'roll surface within seconds.')
TERMS = ('roll_growth', 'film', 'flow_stress', 'strip_temperature')
TERM_WORDS = {'roll_growth': 'roll growth', 'film': 'oil film', 'flow_stress': 'softer metal',
              'strip_temperature': 'strip temperature'}
TERM_RESTS_ON = {
    'roll_growth': 'the roll thermal model and the shape chain with the exit-tension feedback '
                   '(width.shape.steady, linear before saturation)',
    'film': 'the inlet temperature weight (assumed), the oil viscosity law, the friction '
            'closure slope and dF/dmu of the pass bite, through the force transfer',
    'flow_stress': 'the softening coefficient, the strip-to-roll coupling and dF/dY of the pass '
                   'bite, through the force transfer',
    'strip_temperature': 'the strip-to-roll coupling of the heat partition and the expansion '
                         'coefficient; read while hot only'}
SOURCE_LIMITATIONS = (
    'Linear: the terms are summed on the linear-feedback profile, before any band-wise '
    'saturation.',
    'dF/dmu and dF/dY of a constant-friction bite of the pass (central differences, or the '
    'analytic derivatives of the reduced half-space bite).',
    'The exit-tension feedback is not confirmed by an independent model (SPEC19 package 8): '
    'the compliance-only level is printed beside it, two orders of magnitude larger.',
    'width.shape.steady, the onsets, the gauge trend and every evidence item are NOT changed.')


def _force_i_units(z, dp, sp, feedback):
    from . import band_width as bw     # local: band_width imports this module
    return bw._friction_i_units(z, dp, sp, feedback)[1]


def sign_word(value):
    thr = ss.DEFAULT_REPORTING_THRESHOLD_I_UNITS
    if value >= thr:
        return 'LOOSE'
    if value <= -thr:
        return 'TIGHT'
    return 'BELOW_REPORTING_THRESHOLD'


def source_terms(z_strip, changes, sp, sens):
    """The film, flow-stress and strip-temperature terms [I-units] of a set of local changes,
    with the exit-tension feedback and compliance only. ``sens``:
    ``dforce_per_width_dfriction_n_m`` (M_mu), ``dforce_per_width_dflow_stress_m`` (M_Y) and
    ``flow_stress_pa`` (Y of the pass). A term that cannot be evaluated is None and named in
    ``missing_terms`` with the reason."""
    z = list(z_strip)
    m_mu, m_y = sens['dforce_per_width_dfriction_n_m'], sens['dforce_per_width_dflow_stress_m']
    out, missing = {}, {}
    dp = [m_mu * d for d in changes['friction_change']]
    out['film_i_units'] = _force_i_units(z, dp, sp, True)
    out['film_i_units_compliance_only'] = _force_i_units(z, dp, sp, False)
    dy = changes.get('flow_stress_change_fraction')
    if dy is None:
        out['flow_stress_i_units'] = out['flow_stress_i_units_compliance_only'] = None
        missing['flow_stress'] = changes.get('flow_stress_reason') or (
            'no flow-stress change (no softening coefficient or no strip-to-roll coupling)')
    else:
        dpy = [m_y * sens['flow_stress_pa'] * d for d in dy]
        out['flow_stress_i_units'] = _force_i_units(z, dpy, sp, True)
        out['flow_stress_i_units_compliance_only'] = _force_i_units(z, dpy, sp, False)
    t_x = changes.get('strip_exit_temperature_k')
    if t_x is None:
        out['strip_temperature_i_units'] = None
        missing['strip_temperature'] = ('no strip exit temperature (no strip-to-roll coupling or '
                                        'no modelled exit temperature of the pass)')
    else:
        out['strip_temperature_i_units'] = ss.thermal_flatness_term(z, t_x)['i_units']
    out['missing_terms'] = missing
    return out


def combine(roll, terms):
    """``mechanical_net`` and ``as_measured_hot`` [I-units]; a missing term counts as zero (and
    stays named in ``missing_terms``)."""
    n = len(roll)

    def get(key):
        v = terms.get(key)
        return v if v is not None else [0.0] * n
    mech = [a + b + c for a, b, c in zip(roll, get('film_i_units'),
                                          get('flow_stress_i_units'))]
    hot = [a + b for a, b in zip(mech, get('strip_temperature_i_units'))]
    return mech, hot


def _val(series, j):
    return None if series is None else series[j]


def point_row(j, z, roll, terms, weight_film, missing, entered_weight):
    """Every term, both sums and the sign words at sample ``j``. ``weight_film``: the film
    term (with feedback) at inlet weights 0 and 1."""
    r = roll[j]
    f, y, t = (_val(terms['film_i_units'], j), _val(terms['flow_stress_i_units'], j),
               _val(terms['strip_temperature_i_units'], j))
    y0, t0 = y or 0.0, t or 0.0
    mech = r + f + y0
    hot = mech + t0
    n0 = r + weight_film[0][j] + y0
    n1 = r + weight_film[1][j] + y0
    words = (sign_word(n0), sign_word(mech), sign_word(n1))
    size = abs(r) + abs(f) + abs(y0)
    row = {'position_m': z[j], 'roll_growth_i_units': r, 'film_i_units': f,
           'film_i_units_compliance_only': _val(terms['film_i_units_compliance_only'], j),
           'flow_stress_i_units': y,
           'flow_stress_i_units_compliance_only': _val(
               terms['flow_stress_i_units_compliance_only'], j),
           'strip_temperature_i_units': t, 'mechanical_net_i_units': mech,
           'as_measured_hot_i_units': hot, 'net_sign': words[1],
           'as_measured_hot_sign': sign_word(hot),
           'mechanical_net_at_weight_0_i_units': n0, 'mechanical_net_at_weight_1_i_units': n1,
           'as_measured_hot_at_weight_0_i_units': n0 + t0,
           'as_measured_hot_at_weight_1_i_units': n1 + t0,
           'net_sign_at_weight_0': words[0], 'net_sign_at_weight_1': words[2],
           'sign_depends_on_inlet_weight': len(set(words)) > 1,
           'mechanical_terms_size_i_units': size,
           'mechanical_terms_size_over_net': None if mech == 0 else size / abs(mech),
           'missing_terms': sorted(missing)}
    text = (f'Mechanical net {mech:+.3g} I-units ({words[1].lower().replace("_", " ")}) = '
            f'roll growth {r:+.3g} + oil film {f:+.3g}'
            + (f' + softer metal {y:+.3g}' if y is not None else '')
            + f' (inlet weight {entered_weight:g}); with inlet weight 0 / 1 the net is '
            f'{n0:+.3g} / {n1:+.3g}. The mechanical terms add to {size:.3g} I-units in size'
            + (f', {size / abs(mech):.3g} times the net.' if mech != 0 else '.')
            + (f' Read while hot: {hot:+.3g} with the strip temperature term {t:+.3g}.'
               if t is not None else ''))
    for name, why in sorted(missing.items()):
        text += f' The {TERM_WORDS[name]} term is missing ({why}): the net is incomplete.'
    row['net_text'] = text
    return row


def _weight_films(z, dtr, params, sp, sens):
    out = []
    for wt in (0.0, 1.0):
        ch = local_changes(z, dtr, dict(params, inlet_roll_temperature_weight=wt))
        out.append(_force_i_units(z, [sens['dforce_per_width_dfriction_n_m'] * d
                                      for d in ch['friction_change']], sp, True))
    return out


def _changes_for_terms(ch, params):
    c = dict(ch)
    if c.get('flow_stress_change_fraction') is None:
        c['flow_stress_reason'] = (
            params['coefficient_basis'] if params['flow_stress_temperature_coefficient_per_k']
            is None else 'needs the strip-to-roll temperature coupling: '
            + params['coupling_basis'])
    return c


def event_sources(context, sp, sens, th):
    """Callback for ``band_width._events_section``: the local sources of one event at the
    snapshot nearest ``start + min(20 s, duration)`` and at its peak snapshot (surface and
    radius differences from the starting steady state, circumferential mean), reported at the
    event's monitor position."""
    from . import band_width as bw
    params, z, idx = context['params'], context['z'], context['idx']

    def one(snap, base_r, base_s, ts, x):
        dtr = [snap['surface_temperature_k'][i] - base_s[i] for i in idx]
        dev = [g - b for g, b in zip(snap['radius_growth_m'], base_r)]
        fb = bw._tsf(context['z_full'], dev, sp, True)
        roll = bw._linear_feedback_i_units(fb, sp)
        if len(roll) != len(z):
            raise ValueError('the shape grid differs from the strip samples')
        ch = local_changes(z, dtr, params)
        terms = source_terms(z, _changes_for_terms(ch, params), sp, sens)
        wf = _weight_films(z, dtr, params, sp, sens)
        j = min(range(len(z)), key=lambda k: abs(z[k] - x))
        row = point_row(j, z, roll, terms, wf, terms['missing_terms'],
                        params['inlet_roll_temperature_weight'])
        row.update(time_after_start_s=snap['time_s'] - ts,
                   roll_surface_temperature_change_k=dtr[j],
                   friction_change=ch['friction_change'][j])
        return row

    def run(ev):
        snaps, ts, dur, x = ev['snapshots'], ev['start_s'], ev['duration_s'], ev['x']
        target = ts + min(FAST_PATH_TIME_S, dur)
        s20 = min(snaps, key=lambda s: (abs(s['time_s'] - target), s['time_s']))
        try:
            return {'status': STATUS, 'not_supplied': False,
                    'at_20_s': one(s20, ev['base_radius'], ev['base_surface'], ts, x),
                    'at_peak': one(ev['peak_snapshot'], ev['base_radius'], ev['base_surface'],
                                   ts, x),
                    'fast_path_time_s': FAST_PATH_TIME_S, 'monitor_position_m': x,
                    'basis': 'surface temperature and radius growth of the snapshot minus the '
                             'starting steady state (circumferential mean), on the whole strip; '
                             'terms as width.local_sources, read at the monitor position'}
        except (ValueError, ArithmeticError) as exc:
            return {'status': 'FAILED', 'not_supplied': False, 'error': f'local_sources: {exc}'}
    return run


def local_sources_section(case, w, context, sp, sens, shape_steady, th, events_rows):
    """``width.local_sources`` (SPEC19 package 2)."""
    from . import roll_skin
    if w.get('local_coupling') is None:
        return not_supplied('width_model.local_coupling is null or absent')
    if not context:
        return not_assessable('needs width.local_state')
    if sp is None:
        return not_assessable('needs the shape parameters of the case pass')
    if sens is None:
        return not_assessable('needs dF/dmu and dF/dY of the case-pass bite')
    if not isinstance(shape_steady, dict) or not isinstance(
            shape_steady.get('i_units_linear_feedback'), list):
        return not_assessable('needs width.shape.steady')
    params, z, ch, dtr = context['params'], context['z'], context['changes'], context['dtr']
    roll = list(shape_steady['i_units_linear_feedback'])
    if len(roll) != len(z) or any(abs(a - b) > 1e-12 for a, b in zip(shape_steady['z_m'], z)):
        return not_assessable('the steady shape grid differs from the strip samples')
    terms = source_terms(z, _changes_for_terms(ch, params), sp, sens)
    missing = terms['missing_terms']
    mech, hot = combine(roll, terms)
    wf = _weight_films(z, dtr, params, sp, sens)
    kw = dict(youngs_modulus_pa=sp['strip_youngs_modulus_pa'],
              poisson_ratio=sp['strip_poisson_ratio'], thickness_m=sp['exit_thickness_m'],
              mean_tension_pa=sp['mean_tension_pa'], yield_stress_pa=sp['yield_stress_pa'])
    series = {'roll_growth': roll, 'film': terms['film_i_units'],
              'flow_stress': terms['flow_stress_i_units'],
              'strip_temperature': terms['strip_temperature_i_units'],
              'mechanical_net': mech, 'as_measured_hot': hot}
    profiles = {}
    for name, iu in series.items():
        if iu is None:
            profiles[name] = None
            continue
        f = ss.flatness_from_elongation(z, [v * 1e-5 for v in iu], **kw)
        profiles[name] = {'max_i_units': f['max_i_units'], 'min_i_units': f['min_i_units'],
                          'status': f['status'], 'released_status': f['released_status'],
                          'bands': f['bands']}
    flags = [SRC_FLAG_COMPUTED]
    sat = (((shape_steady.get('levels') or {}).get('with_feedback') or {})
           .get('saturated_bands'))
    if sat:
        flags.append(SRC_FLAG_LINEAR)
    if missing:
        flags.append(SRC_FLAG_MISSING)
    at_bands, seen = [], set()
    for src in ('roll_growth', 'mechanical_net'):
        for b in profiles[src]['bands']:
            j = min(range(len(z)), key=lambda k: abs(z[k] - b['peak_position_m']))
            if j in seen:
                continue
            seen.add(j)
            row = point_row(j, z, roll, terms, wf, missing,
                            params['inlet_roll_temperature_weight'])
            row.update(band_of=src, band_peak_i_units=b['peak_i_units'],
                       band_start_m=b['start_m'], band_end_m=b['end_m'])
            if src == 'roll_growth' and sign_word(row['mechanical_net_i_units']) != sign_word(
                    b['peak_i_units']):
                row['reverses_the_roll_growth_band'] = True
                if SRC_FLAG_REVERSE not in flags:
                    flags.append(SRC_FLAG_REVERSE)
            at_bands.append(row)
    ev_rows = []
    for e in events_rows or []:
        ls = e.get('local_sources') if isinstance(e, dict) else None
        if isinstance(ls, dict) and ls.get('status') == STATUS:
            ev_rows.append({'index': e['index'], 'label': e['label'],
                            'monitor_position_m': ls['monitor_position_m'],
                            'at_20_s': ls['at_20_s'], 'at_peak': ls['at_peak']})
    if any(r['sign_depends_on_inlet_weight'] for r in at_bands) or any(
            e[k]['sign_depends_on_inlet_weight'] for e in ev_rows for k in ('at_20_s',
                                                                             'at_peak')):
        flags.append(SRC_FLAG_WEIGHT)

    def peak(series_):
        return None if series_ is None else max(series_, key=abs)
    m_mu, m_y = sens['dforce_per_width_dfriction_n_m'], sens['dforce_per_width_dflow_stress_m']
    fpw = sens['force_per_width_n_m']
    roll_obj, hdr = th.roll, th.header
    v_r = params['roll_surface_speed_m_s']
    scales = roll_skin.time_scales(
        conductivity_w_mk=roll_obj.conductivity_w_mk,
        volumetric_heat_capacity_j_m3k=roll_obj.density_kg_m3 * roll_obj.specific_heat_j_kgk,
        revolution_time_s=2 * math.pi * roll_obj.radius_m / v_r,
        radius_m=roll_obj.radius_m, mean_htc_w_m2k=hdr.background_htc_w_m2k
        + hdr.spray_mean_htc_w_m2k)
    term_scales = {
        'roll_growth': {'follows': 'the roll body (minutes)', 'scale': 'bulk_s',
                        'scale_s': scales['bulk_s']},
        'film': {'follows': 'the roll surface (seconds)', 'scale': 'surface_film_s',
                 'scale_s': scales['surface_film_s']},
        'flow_stress': {'follows': 'the roll surface (seconds)', 'scale': 'surface_film_s',
                        'scale_s': scales['surface_film_s']},
        'strip_temperature': {'follows': 'the roll surface (seconds); gone after cooling',
                              'scale': 'surface_film_s', 'scale_s': scales['surface_film_s']}}
    return {'status': STATUS, 'not_supplied': False, 'z_m': z,
            'roll_growth_i_units': roll, 'film_i_units': terms['film_i_units'],
            'film_i_units_compliance_only': terms['film_i_units_compliance_only'],
            'flow_stress_i_units': terms['flow_stress_i_units'],
            'flow_stress_i_units_compliance_only': terms['flow_stress_i_units_compliance_only'],
            'strip_temperature_i_units': terms['strip_temperature_i_units'],
            'mechanical_net_i_units': mech, 'as_measured_hot_i_units': hot,
            'film_i_units_at_weight_0': wf[0], 'film_i_units_at_weight_1': wf[1],
            'inlet_roll_temperature_weight': params['inlet_roll_temperature_weight'],
            'profiles': profiles, 'at_bands': at_bands, 'missing_terms': missing,
            'compliance_only': {
                'film_peak_i_units': peak(terms['film_i_units_compliance_only']),
                'flow_stress_peak_i_units': peak(terms['flow_stress_i_units_compliance_only']),
                'film_peak_i_units_with_feedback': peak(terms['film_i_units']),
                'flow_stress_peak_i_units_with_feedback': peak(terms['flow_stress_i_units']),
                'note': 'Both transfer levels belong together: with the exit-tension feedback '
                        '(used in the sums) and compliance only (exit_tension_force_'
                        'sensitivity_per_width_m = None). The feedback is not confirmed by an '
                        'independent model.'},
            'sensitivities': {
                'M_mu_n_m': m_mu, 'M_Y_m': m_y, 'flow_stress_pa': sens['flow_stress_pa'],
                'force_per_width_n_m': fpw,
                'load_exponent_in_friction': m_mu * case['pass']['friction_coefficient'] / fpw,
                'load_exponent_in_flow_stress': m_y * sens['flow_stress_pa'] / fpw,
                'sensitivity_bite_model': sens.get('bite_model'),
                'basis': sens.get('basis')},
            'time_scales': {'term_time_scales': term_scales, 'model_scales': {
                k: scales[k] for k in ('per_revolution_s', 'surface_film_s', 'bulk_s',
                                       'mean_htc_w_m2k')},
                'scale_meaning': scales['scale_meaning']},
            'terms_rest_on': dict(TERM_RESTS_ON),
            'events': ev_rows, 'sign_note': SIGN_NOTE,
            'basis': {'transfer': '[D, re-derived in SPEC17] dh_k = G(lam_k)*dp0\'_k, G = '
                                  '2*C/(1 + 2*C*Q_eff) (strip_shape.transfer_force_profile)',
                      'film': "dp0'_film = M_mu*dmu (package 1 dmu)",
                      'flow_stress': "dp0'_flow = M_Y*Y_pass*dY_rel (package 1 dY_rel)",
                      'strip_temperature': 'I_T = thermal_flatness_term(z, T_x) (package 1)',
                      'roll_growth': 'width.shape.steady.i_units_linear_feedback (linear, '
                                     'before the band-wise saturation)',
                      'sums': 'mechanical_net = roll + film + flow; as_measured_hot = '
                              'mechanical_net + strip temperature; a missing term counts as '
                              'zero and is named',
                      'sign_words': f'LOOSE >= +{ss.DEFAULT_REPORTING_THRESHOLD_I_UNITS:g}, '
                                    f'TIGHT <= -{ss.DEFAULT_REPORTING_THRESHOLD_I_UNITS:g} '
                                    'I-units (the reporting threshold), else '
                                    'BELOW_REPORTING_THRESHOLD',
                      'fast_path': f'events: the snapshot nearest start + min({FAST_PATH_TIME_S:g}'
                                   ' s, duration) [D, SPEC19: analyst choice]'},
            'flags': flags,
            'limitations': list(LIMITATIONS) + list(SOURCE_LIMITATIONS)}
