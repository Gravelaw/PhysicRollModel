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


def local_state_section(case, w, th, steady, trib, bite, heat_row, friction_row, cycle):
    """``width.local_state`` (SPEC19 package 1): local state across the width as differences
    from the healthy header; ``not_supplied`` without ``width_model.local_coupling``."""
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
