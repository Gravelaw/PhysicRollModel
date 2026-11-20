"""Coupled pass physics for the band screening engine (case schema ``physicroll.band_case.v2``).

Status: ``SCREENING_RESULT_NOT_PLANT_VALIDATED``. Integration layer only: every equation lives
in the wrapped modules, which this file calls and never re-implements:

- ``bite_tribology``: inlet film (Wilson & Walowit form), PLACEHOLDER friction closure
  ``mu(Lambda)`` (not fitted), friction vs speed, pass heating, Voce / power hardening and
  ``schedule_flow_stress``;
- ``mill_dynamics``: gaugemeter AGC frequency response and stability, static gauge shifts,
  coil-synchronous frequencies, torsional modes and roll-speed ripple (the flow-stress and
  friction force sensitivities are the same central differences, +-0.5 % and +-2 %, taken
  here through the engine's bite cache so the perturbed bites use the operating bite model);
- ``slab._solve_grid`` (Hitchcock bites) and ``foil_bite.solve_mattress_bite`` (experimental
  mattress bites): interface slip dissipation, the friction power of the pass heating.

Couplings made here (integration choices, documented in the result):

- friction fixed point on the contact radius, friction -> bite -> R' -> friction, at most
  ``FRICTION_FIXED_POINT_ITERATIONS`` passes; the friction kept is the last one whose bite was
  derived, so friction, bite and R' are mutually consistent to ``FRICTION_FIXED_POINT_TOL``;
- inputs to ``friction_at_speed``: radius of the film's inlet angle ``R*film_radius_ratio(bite)``
  (``R'`` of a Hitchcock bite, the undeformed ``R`` of a mattress bite [BT-S3 EX; SPEC17]),
  plane-strain yield ``2Y/sqrt(3)``, back tension = entry tension, roll surface speed
  ``u_exit/(1+f)``, strip entry speed ``u_exit*h_exit/h_entry`` (SPEC6 6.7);
- the placeholder closure keeps friction near 0.09 over most of the common industrial
  film-ratio window: its end values match the one abstract on aluminium [BT-S6 AB], but
  neither its level nor its slope with speed is supported (SPEC6 6.7; SPEC17 X22);
- speed-consistent critical speed: the exit speed ``u`` with ``u = u_crit(mu(u))``, scanned
  and bisected in log speed with the contact radius held at the operating value;
- AGC: the supplied loop and, when no force filter is supplied, the same loop with a 25 Hz
  first-order force filter (the AGC/chatter interaction rests on the loop roll-off); the AGC
  result never changes hypothesis evidence; static formulas are tension-coupling-off
  (tensions held by regulators).

NOT modelled here: anything the wrapped modules do not model (see their docstrings).
"""
from dataclasses import asdict, replace
import math

from . import bite_tribology as bt
from . import mill_dynamics as md
from .chatter import BitePass, critical_speed
from .foil_bite import solve_mattress_bite
from .materials import PowerHardeningLaw
from .model import Scenario
from .slab import _solve_grid
from .strip_shape import ALUMINIUM_NU

FRICTION_FIXED_POINT_ITERATIONS = 5
FRICTION_FIXED_POINT_TOL = 1e-4          # absolute friction change (analyst choice)
CURVE_SPEEDS_M_S = (1.0, 40.0)
CURVE_POINTS = 16
SLOPE_REFERENCE_SPEEDS_M_S = (2.0, 25.0)  # SPEC6 6.7 quotes the slope between these speeds
SPEED_CONSISTENT_SCAN_M_S = (0.5, 50.0)
SPEED_CONSISTENT_POINTS = 6
SPEED_CONSISTENT_REL_TOL = 0.01
SPEED_CONSISTENT_MAX_ITERATIONS = 6
DEFAULT_FORCE_FILTER_HZ = 25.0
STRIP_DENSITY_KG_M3 = 2700.0             # aluminium; used for the span wave speed c = sqrt(E/rho)
MATTRESS_FLAG = 'BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL'
HALF_SPACE_FLAG = 'BITE_FROM_REDUCED_HALF_SPACE_MODEL'
STATIC_LABEL = ('static formulas with tension coupling OFF (tensions held by the reel '
                'regulators); with coupling on the constant-speed spans drive the DC gauge '
                'response to the mass-flow limit (mill_dynamics docstring)')
NOT_SUPPLIED = 'NOT_SUPPLIED'


def not_supplied(reason):
    """Uniform marker for an optional section whose inputs are absent."""
    return {'status': NOT_SUPPLIED, 'not_supplied': True, 'reason': reason}


def failed(section, exc):
    return {'status': 'FAILED', 'not_supplied': False, 'error': f'{section}: {exc}'}


# ============================================================================= validation
def _is_num(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def num(where, value, *, positive=False, nonnegative=False, lo=None, hi=None):
    if not _is_num(value):
        raise ValueError(f'{where} must be a finite number in SI units (not bool/null)')
    value = float(value)
    if positive and value <= 0:
        raise ValueError(f'{where} must be > 0')
    if nonnegative and value < 0:
        raise ValueError(f'{where} must be >= 0')
    if lo is not None and value < lo:
        raise ValueError(f'{where} must be >= {lo}')
    if hi is not None and value > hi:
        raise ValueError(f'{where} must be <= {hi}')
    return value


def opt_num(where, value, **kw):
    return None if value is None else num(where, value, **kw)


def boolean(where, value):
    if not isinstance(value, bool):
        raise ValueError(f'{where} must be true or false')
    return value


def keys(where, data, required, optional=()):
    if not isinstance(data, dict):
        raise ValueError(f'{where} must be a JSON object')
    missing = set(required) - set(data)
    unknown = set(data) - set(required) - set(optional)
    if missing or unknown:
        raise ValueError(f'{where}: missing keys {sorted(missing)}, unknown keys {sorted(unknown)}')


def num_list(where, value, **kw):
    if not isinstance(value, list):
        raise ValueError(f'{where} must be a list')
    return [num(f'{where}[{i}]', v, **kw) for i, v in enumerate(value)]


def int_list(where, value):
    if not isinstance(value, list):
        raise ValueError(f'{where} must be a list')
    for i, v in enumerate(value):
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise ValueError(f'{where}[{i}] must be an int >= 0')
    return sorted(set(value))


LUBRICANT_KEYS = ('viscosity_ref_pa_s', 'reference_temperature_k',
                  'temperature_viscosity_coefficient_per_k',
                  'pressure_viscosity_coefficient_per_pa')
# SPEC18 package 5: optional lubricant keys (absent -> None, or 'barus'); kept in every
# validated case so the inputs block shows them
LUBRICANT_OPTIONAL_P5 = ('viscosity_table', 'pressure_law', 'roelands_z', 'eyring_stress_pa',
                         'eyring_stress_pressure_coefficient', 'limiting_shear_stress_pa',
                         'limiting_shear_pressure_coefficient')
_LUB_RANGES = {'roelands_z': ('(0, 2]', 0.0, 2.0, True),
               'eyring_stress_pa': ('[1e4, 1e9] Pa', 1e4, 1e9, False),
               'eyring_stress_pressure_coefficient': ('(0, 0.1]', 0.0, 0.1, True),
               'limiting_shear_stress_pa': ('[1e4, 5e9] Pa', 1e4, 5e9, False),
               'limiting_shear_pressure_coefficient': ('(0, 1]', 0.0, 1.0, True)}
VISCOSITY_TABLE_MESSAGE = ('tribology.lubricant.viscosity_table must be null or >= 2 points with '
                           'increasing temperature and non-increasing viscosity')


def _lubricant_options(lub):
    out = {}
    table = lub.get('viscosity_table')
    if table is None:
        out['viscosity_table'] = None
    else:
        if not isinstance(table, list) or len(table) < 2:
            raise ValueError(VISCOSITY_TABLE_MESSAGE)
        pts = []
        for pt in table:
            if not isinstance(pt, dict) or set(pt) != {'temperature_k', 'viscosity_pa_s'} or \
                    not _is_num(pt['temperature_k']) or not _is_num(pt['viscosity_pa_s']):
                raise ValueError(VISCOSITY_TABLE_MESSAGE)
            pts.append({'temperature_k': float(pt['temperature_k']),
                        'viscosity_pa_s': float(pt['viscosity_pa_s'])})
        try:
            bt._table([(x['temperature_k'], x['viscosity_pa_s']) for x in pts])
        except ValueError as exc:
            raise ValueError(VISCOSITY_TABLE_MESSAGE) from exc
        out['viscosity_table'] = pts
    law = lub.get('pressure_law') or 'barus'
    if law not in bt.PRESSURE_LAWS:
        raise ValueError(f'tribology.lubricant.pressure_law must be one of {bt.PRESSURE_LAWS}')
    out['pressure_law'] = law
    for key, (text, lo, hi, open_lo) in _LUB_RANGES.items():
        v = lub.get(key)
        if v is not None:
            if not _is_num(v) or (v <= lo if open_lo else v < lo) or v > hi:
                raise ValueError(f'tribology.lubricant.{key} must be null or in {text}')
            v = float(v)
        out[key] = v
    return out


TRIBOLOGY_KEYS = ('lubricant', 'surface_finish', 'inlet_temperature_k',
                  'strip_entry_temperature_k', 'strip_heat_fraction', 'thermal_correction',
                  'use_computed_friction')
TRIBOLOGY_OPTIONAL = ('friction_closure', 'temperature_limit_k', 'oil_flash_point_k',
                      'oil_supply_temperature_cap_k')   # SPEC17 A10: user limits, no default
HARDENING_COMMON = ('law', 'provenance', 'prior_equivalent_strain', 'reference_thickness_m',
                    'use_computed_flow_stress')
HARDENING_LAW_KEYS = {
    'power': ('yield_stress_pa', 'strength_coefficient_pa', 'exponent'),
    'voce': ('initial_stress_pa', 'saturation_stress_pa', 'characteristic_strain',
             'stage_iv_slope_pa')}


def _fire_limit(t, key):
    """SPEC17 A10: an optional user limit in kelvin, 250-700 K; never defaulted."""
    v = t.get(key)
    if v is None:
        return None
    v = num(f'tribology.{key}', v)
    if not 250.0 <= v <= 700.0:
        raise ValueError(f'tribology.{key} must be in [250, 700] K')
    return v


def validate_tribology(t):
    keys('tribology', t, TRIBOLOGY_KEYS, TRIBOLOGY_OPTIONAL)
    lub = t['lubricant']
    keys('tribology.lubricant', lub, LUBRICANT_KEYS,
         ('conductivity_w_mk', 'name') + LUBRICANT_OPTIONAL_P5)
    out_lub = {k: num(f'tribology.lubricant.{k}', lub[k]) for k in LUBRICANT_KEYS}
    out_lub['conductivity_w_mk'] = opt_num('tribology.lubricant.conductivity_w_mk',
                                           lub.get('conductivity_w_mk'), positive=True)
    name = lub.get('name', 'rolling oil')
    if not isinstance(name, str) or not name.strip():
        raise ValueError('tribology.lubricant.name must be a nonempty string')
    out_lub['name'] = name
    out_lub.update(_lubricant_options(lub))
    fin = t['surface_finish']
    keys('tribology.surface_finish', fin, ('roll_roughness_rq_m', 'strip_roughness_rq_m'))
    out_fin = {k: num(f'tribology.surface_finish.{k}', fin[k], nonnegative=True) for k in fin}
    clo = t.get('friction_closure')
    out_clo = None
    if clo is not None:
        keys('tribology.friction_closure', clo, ('mu_b', 'mu_v', 'lambda0'))
        out_clo = {k: num(f'tribology.friction_closure.{k}', clo[k]) for k in clo}
    out = {'lubricant': out_lub, 'surface_finish': out_fin, 'friction_closure': out_clo,
           'inlet_temperature_k': num('tribology.inlet_temperature_k', t['inlet_temperature_k']),
           'strip_entry_temperature_k': num('tribology.strip_entry_temperature_k',
                                            t['strip_entry_temperature_k']),
           'strip_heat_fraction': num('tribology.strip_heat_fraction', t['strip_heat_fraction'],
                                      lo=0.0, hi=1.0),
           'temperature_limit_k': opt_num('tribology.temperature_limit_k',
                                          t.get('temperature_limit_k')),
           'oil_flash_point_k': _fire_limit(t, 'oil_flash_point_k'),
           'oil_supply_temperature_cap_k': _fire_limit(t, 'oil_supply_temperature_cap_k'),
           'thermal_correction': boolean('tribology.thermal_correction', t['thermal_correction']),
           'use_computed_friction': boolean('tribology.use_computed_friction',
                                            t['use_computed_friction'])}
    lubricant, finish, closure = tribology_objects(out)
    try:
        lubricant.validate()
        finish.validate()
        closure.validate()
    except ValueError as exc:
        raise ValueError(f'tribology: {exc}') from exc
    return out


def tribology_objects(t):
    lub = t['lubricant']
    lubricant = bt.Lubricant(
        viscosity_ref_pa_s=lub['viscosity_ref_pa_s'],
        reference_temperature_k=lub['reference_temperature_k'],
        temperature_viscosity_coefficient_per_k=lub['temperature_viscosity_coefficient_per_k'],
        pressure_viscosity_coefficient_per_pa=lub['pressure_viscosity_coefficient_per_pa'],
        conductivity_w_mk=lub['conductivity_w_mk'], name=lub['name'],
        viscosity_table=(None if lub.get('viscosity_table') is None else tuple(
            (x['temperature_k'], x['viscosity_pa_s']) for x in lub['viscosity_table'])),
        **{k: lub.get(k) for k in LUBRICANT_OPTIONAL_P5[2:]},
        pressure_law=lub.get('pressure_law', 'barus'))
    finish = bt.SurfaceFinish(**t['surface_finish'])
    closure = (bt.FrictionClosure() if t['friction_closure'] is None
               else bt.FrictionClosure(**t['friction_closure']))
    return lubricant, finish, closure


def validate_hardening(h, material):
    if not isinstance(h, dict) or h.get('law') not in HARDENING_LAW_KEYS:
        raise ValueError("hardening.law must be 'power' or 'voce'")
    law_keys = HARDENING_LAW_KEYS[h['law']]
    keys('hardening', h, HARDENING_COMMON + law_keys)
    prov = h['provenance']
    if not isinstance(prov, str) or not prov.strip():
        raise ValueError('hardening.provenance must be a nonempty string')
    out = {'law': h['law'], 'provenance': prov,
           'prior_equivalent_strain': num('hardening.prior_equivalent_strain',
                                          h['prior_equivalent_strain'], nonnegative=True),
           'reference_thickness_m': num('hardening.reference_thickness_m',
                                        h['reference_thickness_m'], positive=True),
           'use_computed_flow_stress': boolean('hardening.use_computed_flow_stress',
                                               h['use_computed_flow_stress'])}
    for k in law_keys:
        out[k] = num(f'hardening.{k}', h[k], nonnegative=True)
    try:
        hardening_law(out, material).validate()
    except ValueError as exc:
        raise ValueError(f'hardening: {exc}') from exc
    return out


def hardening_law(h, material):
    if h['law'] == 'power':
        return PowerHardeningLaw(alloy=material['alloy'], temper=material['temper'],
                                 yield_stress_pa=h['yield_stress_pa'],
                                 strength_coefficient_pa=h['strength_coefficient_pa'],
                                 exponent=h['exponent'], provenance=h['provenance'])
    return bt.VoceHardening(initial_stress_pa=h['initial_stress_pa'],
                            saturation_stress_pa=h['saturation_stress_pa'],
                            characteristic_strain=h['characteristic_strain'],
                            stage_iv_slope_pa=h['stage_iv_slope_pa'], provenance=h['provenance'])


def validate_gauge_control(g):
    keys('gauge_control', g, ('compensation_gain', 'bandwidth_hz'), ('force_filter_hz',))
    out = {'compensation_gain': num('gauge_control.compensation_gain', g['compensation_gain']),
           'bandwidth_hz': num('gauge_control.bandwidth_hz', g['bandwidth_hz']),
           'force_filter_hz': opt_num('gauge_control.force_filter_hz', g.get('force_filter_hz'))}
    try:
        agc_of(out).validate()
    except ValueError as exc:
        raise ValueError(f'gauge_control: {exc}') from exc
    return out


def agc_of(g, force_filter_hz=None):
    ff = g['force_filter_hz'] if force_filter_hz is None else force_filter_hz
    return md.GaugemeterAGC(g['compensation_gain'], g['bandwidth_hz'], ff)


def validate_drive(d):
    keys('drive', d, ('inertias_kg_m2', 'stiffnesses_n_m_rad'))
    out = {'inertias_kg_m2': num_list('drive.inertias_kg_m2', d['inertias_kg_m2'], positive=True),
           'stiffnesses_n_m_rad': num_list('drive.stiffnesses_n_m_rad', d['stiffnesses_n_m_rad'],
                                           positive=True)}
    try:
        md.torsional_modes(out['inertias_kg_m2'], out['stiffnesses_n_m_rad'])
    except ValueError as exc:
        raise ValueError(f'drive: {exc}') from exc
    return out


def validate_incoming_variation(v):
    keys('incoming_variation', v, ('flow_stress_variation_fraction', 'coil_synchronous'))
    return {'flow_stress_variation_fraction': num(
                'incoming_variation.flow_stress_variation_fraction',
                v['flow_stress_variation_fraction'], positive=True, hi=0.5),
            'coil_synchronous': boolean('incoming_variation.coil_synchronous',
                                        v['coil_synchronous'])}


# ============================================================================= helpers
def pass_rows(case):
    """[(label, source dict)] for the case pass and every schedule pass."""
    return [('case pass', case['pass'])] + [(r['label'], r) for r in case['schedule']]


def bite_pass(case, src):
    p = case['pass']
    return BitePass(src['entry_thickness_m'], src['exit_thickness_m'], p['width_m'],
                    p['work_roll_radius_m'], src['mean_flow_stress_pa'],
                    src['friction_coefficient'], src['entry_tension_pa'], src['exit_tension_pa'])


def _logspace(lo, hi, n):
    return [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]


def is_mattress(bite):
    return MATTRESS_FLAG in bite.flags


def is_half_space(bite):
    return HALF_SPACE_FLAG in bite.flags


def is_foil_model(bite):
    """Either foil model (experimental mattress or reduced half-space)."""
    return is_mattress(bite) or is_half_space(bite)


def bite_source_word(bite):
    """'experimental_mattress', 'reduced_half_space' or the BiteResponse source."""
    if is_mattress(bite):
        return 'experimental_mattress'
    if is_half_space(bite):
        return 'reduced_half_space'
    return bite.source


# Inlet angle of the film [D, re-derived in SPEC17]: for a bite h(x) = h1 + x^2/R_c the inlet is
# at x_i = -sqrt(R_c*draft) and each roll surface's slope there is |x_i|/R_c = sqrt(draft/R_c).
# Hitchcock bite: R_c = R' (the deformed arc). Mattress bite: the roll is not an arc and its
# contact_radius_ratio L^2/(R*draft) is not a radius (it would give draft/L, the mean slope of
# the whole bite); the undeformed roll is used, R_c = R [BT-S3 EX]. The local slope of the
# mattress solution at the plastic entry is not used: its entry zone holds a rigid strip.
INLET_ANGLE_BASIS_MATTRESS = ('undeformed-roll inlet slope theta0 = sqrt(draft/R) [BT-S3 EX]; '
                              'the mattress contact_radius_ratio L^2/(R*draft) is not a radius')
INLET_ANGLE_BASIS_ARC = "inlet slope of the deformed circular arc theta0 = sqrt(draft/R') [D]"
INLET_ANGLE_BASIS_HALF_SPACE = INLET_ANGLE_BASIS_MATTRESS.replace('mattress', 'half-space')


def film_radius_ratio(bite):
    """Radius ratio R_c/R of the film's inlet angle (1.0 for a mattress or half-space bite)."""
    return 1.0 if is_foil_model(bite) else bite.contact_radius_ratio


def inlet_angle_basis(bite):
    if is_half_space(bite):
        return INLET_ANGLE_BASIS_HALF_SPACE
    return INLET_ANGLE_BASIS_MATTRESS if is_mattress(bite) else INLET_ANGLE_BASIS_ARC


def _mu_inputs(trib, src, radius, ratio, slip, exit_speed):
    h0, h1 = src['entry_thickness_m'], src['exit_thickness_m']
    return dict(roll_surface_speed_m_s=exit_speed / (1 + slip),
                strip_entry_speed_m_s=exit_speed * h1 / h0, entry_thickness_m=h0,
                exit_thickness_m=h1, contact_radius_m=radius * ratio,
                plane_strain_yield_pa=2 / math.sqrt(3) * src['mean_flow_stress_pa'],
                back_tension_pa=src['entry_tension_pa'],
                inlet_temperature_k=trib['inlet_temperature_k'],
                thermal_correction=trib['thermal_correction'])


# same relative steps as mill_dynamics.flow_stress_sensitivity / friction_force_sensitivity
FLOW_STRESS_RELATIVE_STEP = 0.005
FRICTION_RELATIVE_STEP = 0.02


def bite_sensitivity(get_bite, bite_pass_, field, relative_step):
    """Central difference of the separating force and forward slip in ``field`` of the pass.

    ``get_bite(BitePass) -> BiteResponse`` derives the perturbed bites through the engine's
    bite cache with the SAME bite model as the operating bite (mill_dynamics' sensitivities
    always use the Hitchcock derivation, which rejects passes the mattress model solves and,
    where both work, would mix a Hitchcock force sensitivity with a mattress strip modulus).
    """
    nominal = getattr(bite_pass_, field)
    step = relative_step * nominal
    plus = get_bite(replace(bite_pass_, **{field: nominal + step}))
    minus = get_bite(replace(bite_pass_, **{field: nominal - step}))
    flags = []
    for f in tuple(plus.flags) + tuple(minus.flags):
        if f not in flags:
            flags.append(f)
    return {'dforce': (plus.separating_force_n - minus.separating_force_n) / (2 * step),
            'dslip': (plus.forward_slip_fraction - minus.forward_slip_fraction) / (2 * step),
            'step': step, 'relative_step': relative_step,
            'mean_force': 0.5 * (plus.separating_force_n + minus.separating_force_n),
            'bite_model': bite_source_word(plus),
            'flags': flags}


def flow_stress_sensitivity(get_bite, bite_pass_):
    d = bite_sensitivity(get_bite, bite_pass_, 'mean_flow_stress_pa', FLOW_STRESS_RELATIVE_STEP)
    return {'dforce_dflow_stress_m2': d['dforce'], 'dslip_dflow_stress_per_pa': d['dslip'],
            'flow_stress_step_pa': d['step'], 'relative_step': d['relative_step'],
            'mean_separating_force_n': d['mean_force'], 'bite_model': d['bite_model'],
            'flags': d['flags'],
            'basis': 'central difference of the bite of the operating bite model (+-0.5 %)'}


def friction_force_sensitivity(get_bite, bite_pass_):
    d = bite_sensitivity(get_bite, bite_pass_, 'friction_coefficient', FRICTION_RELATIVE_STEP)
    return {'dforce_dfriction_n': d['dforce'], 'dslip_dfriction': d['dslip'],
            'friction_step': d['step'], 'relative_step': d['relative_step'],
            'mean_separating_force_n': d['mean_force'], 'bite_model': d['bite_model'],
            'flags': d['flags'],
            'basis': 'central difference of the bite of the operating bite model (+-2 %)'}


def friction_at(trib, src, radius, ratio, slip, exit_speed):
    lub, fin, clo = tribology_objects(trib)
    return bt.friction_at_speed(lub, fin, clo, **_mu_inputs(trib, src, radius, ratio, slip,
                                                           exit_speed))


# ============================================================================= flow stress
def flow_stress_section(case, hardening):
    """Flow stress per pass from the hardening law (supplied value beside it)."""
    law = hardening_law(hardening, case['material'])
    ref = hardening['reference_thickness_m']
    rows, flags = [], []
    for label, src in pass_rows(case):
        h0, h1 = src['entry_thickness_m'], src['exit_thickness_m']
        row = {'label': label, 'entry_thickness_m': h0, 'exit_thickness_m': h1,
               'supplied_mean_flow_stress_pa': src['mean_flow_stress_pa']}
        try:
            if ref < h0 * (1 - 1e-9):
                raise ValueError(f'reference_thickness_m {ref:g} m is below the pass entry '
                                 f'thickness {h0:g} m')
            gauges = [ref, h0, h1] if ref > h0 * (1 + 1e-9) else [h0, h1]
            res = bt.schedule_flow_stress(gauges, law,
                                          prior_equivalent_strain=hardening[
                                              'prior_equivalent_strain'])
            last = res['passes'][-1]
            for f in res['flags']:
                if f not in flags:
                    flags.append(f)
            row.update(computed_mean_flow_stress_pa=last['mean_flow_stress_pa'],
                       entry_equivalent_strain=last['entry_equivalent_strain'],
                       exit_equivalent_strain=last['exit_equivalent_strain'],
                       entry_flow_stress_pa=last['entry_flow_stress_pa'],
                       exit_flow_stress_pa=last['exit_flow_stress_pa'])
        except ValueError as exc:
            row['rejected'] = str(exc)
        rows.append(row)
    return {'status': bt.STATUS_HARDENING, 'law_type': hardening['law'],
            'law': asdict(law), 'prior_equivalent_strain': hardening['prior_equivalent_strain'],
            'reference_thickness_m': ref,
            'use_computed_flow_stress': hardening['use_computed_flow_stress'],
            'passes': rows, 'flags': flags,
            'note': 'Equivalent strain eps = prior + (2/sqrt(3))*ln(h_ref/h); the mean flow '
                    'stress of each pass is the strain average over that pass '
                    '(bite_tribology.schedule_flow_stress).'}


def apply_flow_stress(case, section):
    """Replace the supplied flow stress by the computed one in the case pass and schedule.

    Rows are matched by position (``flow_stress_section`` builds them from ``pass_rows`` in
    order), not by label: a schedule row may legally be labelled 'case pass' too."""
    rows = section['passes']
    if len(rows) != len(pass_rows(case)):
        raise ValueError('flow stress rows do not match the case pass and schedule')
    for (_, src), row in zip(pass_rows(case), rows):
        if 'computed_mean_flow_stress_pa' in row:
            src['mean_flow_stress_pa'] = row['computed_mean_flow_stress_pa']
        row['used_mean_flow_stress_pa'] = src['mean_flow_stress_pa']


# ============================================================================= friction
def case_pass_bite(case, src, op_bite):
    """The operating bite when ``src`` IS the case pass (``band_width.is_case_pass`` on the
    effective case) and one exists, else None (the caller derives). Review finding: with a
    supplied bite the case-pass row of a per-row table re-derived a different bite."""
    from .band_width import is_case_pass     # local import: band_width imports this module
    return op_bite if op_bite is not None and is_case_pass(case, src) else None


def friction_single(case, src, trib, cache, op_bite=None):
    """Closure friction at the bite of the SUPPLIED friction (no fixed point): used for display
    when the computed friction does not replace the supplied one (that bite is derived anyway,
    except for the case pass with a supplied operating bite, which is used)."""
    radius = case['pass']['work_roll_radius_m']
    u = src['exit_speed_m_s']
    out = {'exit_speed_m_s': u, 'supplied_friction_coefficient': src['friction_coefficient'],
           'method': 'single evaluation at the contact radius of the supplied-friction bite'}
    try:
        bite = (case_pass_bite(case, src, op_bite)
                or cache.get(bite_pass(case, src)))
        ratio, slip = bite.contact_radius_ratio, bite.forward_slip_fraction
        film_ratio, basis = film_radius_ratio(bite), inlet_angle_basis(bite)
        out['bite_source'] = bite_source_word(bite)
    except ValueError as exc:
        ratio, slip = 1.0, 0.0
        film_ratio, basis = 1.0, INLET_ANGLE_BASIS_MATTRESS + ' (no bite)'
        out['bite_error'] = str(exc)
        out['method'] += ' (bite rejected: undeformed roll radius used)'
    res = friction_at(trib, src, radius, film_ratio, slip, u)
    out.update(computed_friction_coefficient=res['friction_coefficient'], converged=None,
               iterations=[], contact_radius_ratio=ratio, forward_slip_fraction=slip,
               film_inlet_radius_ratio=film_ratio, inlet_angle_basis=basis,
               film_thickness_m=res['film_thickness_m'], film_ratio=res['film_ratio'],
               regime=res['regime'],
               in_common_industrial_window=res['in_common_industrial_window'],
               dmu_droll_speed_per_m_s=res['dmu_dspeed_per_m_s'],
               dmu_dexit_speed_per_m_s=res['dmu_dspeed_per_m_s'] / (1 + slip))
    return out


def friction_fixed_point(case, src, trib, cache):
    """friction -> bite -> R' -> friction (<= 5 passes) at the pass's own exit speed."""
    radius = case['pass']['work_roll_radius_m']
    u = src['exit_speed_m_s']
    ratio, slip = 1.0, 0.0
    film_ratio, basis = 1.0, INLET_ANGLE_BASIS_MATTRESS + ' (no bite)'
    first = friction_at(trib, src, radius, film_ratio, slip, u)
    mu = first['friction_coefficient']
    history = [{'iteration': 0, 'contact_radius_ratio': ratio, 'forward_slip_fraction': slip,
                'friction_coefficient': mu}]
    converged, error, last, bite = False, None, first, None
    for k in range(1, FRICTION_FIXED_POINT_ITERATIONS + 1):
        trial = dict(src, friction_coefficient=mu)
        try:
            bite = cache.get(bite_pass(case, trial))
        except ValueError as exc:
            error = str(exc)
            bite = None
            break
        ratio, slip = bite.contact_radius_ratio, bite.forward_slip_fraction
        film_ratio, basis = film_radius_ratio(bite), inlet_angle_basis(bite)
        res = friction_at(trib, src, radius, film_ratio, slip, u)
        new = res['friction_coefficient']
        history.append({'iteration': k, 'contact_radius_ratio': ratio,
                        'forward_slip_fraction': slip, 'friction_coefficient': new,
                        'bite_friction_coefficient': mu})
        last = res
        if abs(new - mu) <= FRICTION_FIXED_POINT_TOL:
            converged = True
            break
        mu = new
    f = 1 + slip
    out = {'exit_speed_m_s': u, 'supplied_friction_coefficient': src['friction_coefficient'],
           'computed_friction_coefficient': mu, 'converged': converged,
           'iterations': history, 'tolerance': FRICTION_FIXED_POINT_TOL,
           'contact_radius_ratio': ratio, 'forward_slip_fraction': slip,
           'film_inlet_radius_ratio': film_ratio, 'inlet_angle_basis': basis,
           'film_thickness_m': last['film_thickness_m'], 'film_ratio': last['film_ratio'],
           'regime': last['regime'],
           'in_common_industrial_window': last['in_common_industrial_window'],
           'dmu_droll_speed_per_m_s': last['dmu_dspeed_per_m_s'],
           'dmu_dexit_speed_per_m_s': last['dmu_dspeed_per_m_s'] / f,
           'bite_source': None if bite is None else bite_source_word(bite),
           'method': 'fixed point friction -> bite -> contact radius -> friction'}
    if error is not None:
        out['bite_error'] = error
    return out


def friction_section(case, trib, cache, op_bite=None):
    """Per-pass friction. ``op_bite``: the supplied operating bite (or None), used by the
    single evaluation for the case pass and any identical schedule row; the fixed point
    (use_computed_friction) iterates friction, so its bites are genuinely different passes."""
    rows = []
    fixed = trib['use_computed_friction']
    for label, src in pass_rows(case):
        try:
            row = (friction_fixed_point(case, src, trib, cache) if fixed
                   else friction_single(case, src, trib, cache, op_bite))
        except ValueError as exc:
            row = {'exit_speed_m_s': src['exit_speed_m_s'],
                   'supplied_friction_coefficient': src['friction_coefficient'],
                   'rejected': str(exc)}
        row['label'] = label
        rows.append(row)
    lub = tribology_objects(trib)[0]
    flags = [bt.PLACEHOLDER_FLAG]
    if not lub.is_default_law():       # keys only then: default results unchanged
        for row in rows:
            row['viscosity_law'] = lub.viscosity_law_text()
        flags += lub.viscosity_flags(trib['inlet_temperature_k'])
    extra = {}
    if lub.limiting_shear_stress_at(1.0) is not None:   # supplied: check against the bound
        notes = []
        for (label, src), row in zip(pass_rows(case), rows):
            try:
                bite = case_pass_bite(case, src, op_bite) or cache.get(bite_pass(case, src))
            except ValueError:
                continue
            p_mean = bite.separating_force_n / (case['pass']['width_m'] * bite.contact_length_m)
            f, sentences = lub.limiting_shear_check(p_mean)
            row['limiting_shear_stress_over_mean_pressure'] = (
                lub.limiting_shear_stress_at(p_mean) / p_mean)
            if f:
                row['lubricant_flags'] = f
                notes += sentences
                for x in f:
                    if x not in flags:
                        flags.append(x)
        if notes:
            extra['limitations'] = [notes[0]]
    return {'status': bt.STATUS_FRICTION, 'use_computed_friction': trib['use_computed_friction'],
            'operating': rows[0], 'schedule': rows[1:], **extra,
            'flags': flags,
            'note': ('PLACEHOLDER friction closure (not fitted): its end values 0.09 and 0.008 '
                     'match the one abstract on aluminium [BT-S6 AB], but it keeps friction '
                     'near 0.09 over most of the common industrial film-ratio window (0.01-0.5), '
                     'so neither its level nor its slope with speed (dmu/du) is supported. '
                     'With use_computed_friction the friction is a fixed point friction -> '
                     f'bite -> R\' -> friction (at most {FRICTION_FIXED_POINT_ITERATIONS} passes, '
                     f'tolerance {FRICTION_FIXED_POINT_TOL:g}); otherwise it is evaluated once '
                     'at the contact radius of the supplied-friction bite.')}


def apply_friction(case, section):
    rows = [section['operating']] + section['schedule']
    for (label, src), row in zip(pass_rows(case), rows):
        if 'computed_friction_coefficient' in row:
            src['friction_coefficient'] = row['computed_friction_coefficient']
        row['used_friction_coefficient'] = src['friction_coefficient']


def friction_curve(case, trib, bite):
    p = case['pass']
    radius = p['work_roll_radius_m'] * film_radius_ratio(bite)
    speeds = sorted(set(_logspace(*CURVE_SPEEDS_M_S, CURVE_POINTS)
                        + [p['exit_speed_m_s']] + list(SLOPE_REFERENCE_SPEEDS_M_S)))
    lub, fin, clo = tribology_objects(trib)
    curve = bt.friction_speed_curve(
        lub, fin, clo, exit_speeds_m_s=speeds, entry_thickness_m=p['entry_thickness_m'],
        exit_thickness_m=p['exit_thickness_m'], contact_radius_m=radius,
        plane_strain_yield_pa=2 / math.sqrt(3) * p['mean_flow_stress_pa'],
        back_tension_pa=p['entry_tension_pa'], inlet_temperature_k=trib['inlet_temperature_k'],
        forward_slip_fraction=bite.forward_slip_fraction,
        thermal_correction=trib['thermal_correction'])
    pts = [{k: q[k] for k in ('exit_speed_m_s', 'friction_coefficient', 'film_thickness_m',
                              'film_ratio', 'regime', 'dmu_dexit_speed_per_m_s')}
           for q in curve['points']]
    by_speed = {q['exit_speed_m_s']: q for q in pts}
    a, b = SLOPE_REFERENCE_SPEEDS_M_S
    mean_slope = ((by_speed[b]['friction_coefficient'] - by_speed[a]['friction_coefficient'])
                  / (b - a))
    op = by_speed[p['exit_speed_m_s']]
    return {'status': curve['status'], 'points': pts,
            'operating_exit_speed_m_s': p['exit_speed_m_s'],
            'operating_friction_coefficient': op['friction_coefficient'],
            'supplied_friction_coefficient': p['friction_coefficient'],
            'contact_radius_m': radius, 'forward_slip_fraction': bite.forward_slip_fraction,
            'inlet_angle_basis': inlet_angle_basis(bite),
            'mean_slope_per_m_s': mean_slope, 'mean_slope_speeds_m_s': [a, b],
            'flags': curve['flags'],
            'note': 'Contact radius and forward slip held at the operating bite; the absolute '
                    'values are placeholders, the slope is the useful output.'}


# ============================================================================= heating
def friction_power_per_width(case, src, bite, cells, roll_e, roll_nu, state=None):
    """Interface slip dissipation of the pass, both interfaces, per unit width [W/m].

    ``state``: the half-space state of ``bite`` (``_BiteCache.state_for``); without it a
    half-space bite is solved again."""
    p = case['pass']
    h0, h1, u = src['entry_thickness_m'], src['exit_thickness_m'], src['exit_speed_m_s']
    width, radius = p['width_m'], p['work_roll_radius_m']
    if is_half_space(bite):
        if state is not None:
            diss = state['extra']['slip_dissipation_both_interfaces_over_roll_speed_n']
            slip = bite.forward_slip_fraction
        else:
            from .halfspace_bite import solve_half_space_bite   # local: optional model
            r = solve_half_space_bite(
                h0, h1, width, radius, src['mean_flow_stress_pa'],
                src['friction_coefficient'], src['entry_tension_pa'], src['exit_tension_pa'],
                roll_youngs_modulus_pa=roll_e, roll_poisson_ratio=roll_nu,
                strip_plane_strain_modulus_pa=(case['material']['youngs_modulus_pa']
                                               / (1 - ALUMINIUM_NU ** 2)),
                shear_cap_factor=case['model_options'].get('shear_cap_factor', 1.0))
            diss, slip = (r['slip_dissipation_both_interfaces_over_roll_speed_n'],
                          r['forward_slip_fraction'])
        return (diss * (u / (1 + slip)) / width,
                'reduced half-space slip dissipation x roll surface speed / width')
    if is_mattress(bite):
        m = solve_mattress_bite(h0, h1, width, radius, src['mean_flow_stress_pa'],
                                src['friction_coefficient'], src['entry_tension_pa'],
                                src['exit_tension_pa'], roll_youngs_modulus_pa=roll_e,
                                roll_poisson_ratio=roll_nu, cells=max(cells, 200))
        vr = u / (1 + m['forward_slip_fraction'])
        return (m['slip_dissipation_both_interfaces_over_roll_speed_n'] * vr / width,
                'experimental mattress slip dissipation x roll surface speed / width')
    if bite.source == 'supplied':
        return 0.0, 'not available for a supplied bite response (friction power set to 0)'
    s = Scenario('band_heat', True, h0, h1, width, u * h1 / h0, radius, STRIP_DENSITY_KG_M3,
                 src['mean_flow_stress_pa'], src['friction_coefficient'],
                 src['entry_tension_pa'], src['exit_tension_pa'], 1.0)
    res = _solve_grid(s, cells, 'established', None, radius * bite.contact_radius_ratio)
    return (res['solid_slip_dissipation_both_interfaces_w'] / width,
            'slab solid_slip_dissipation_both_interfaces_w at the Hitchcock contact radius / '
            'width')


def heating_row(case, src, bite, trib, cells, roll_e, roll_nu, state=None):
    power, basis = friction_power_per_width(case, src, bite, cells, roll_e, roll_nu, state)
    fs = trib['strip_heat_fraction'] if trib else 0.0
    t_in = trib['strip_entry_temperature_k'] if trib else 293.15
    res = bt.pass_heating(entry_thickness_m=src['entry_thickness_m'],
                          exit_thickness_m=src['exit_thickness_m'],
                          exit_speed_m_s=src['exit_speed_m_s'],
                          mean_flow_stress_pa=src['mean_flow_stress_pa'],
                          strip_heat_fraction=fs, entry_temperature_k=t_in,
                          friction_power_per_width_w_m=power,
                          temperature_limit_k=trib['temperature_limit_k'] if trib else None)
    flags = list(res['flags'])
    if bite.source == 'supplied' and not is_foil_model(bite):
        flags.append('FRICTION_POWER_NOT_AVAILABLE_FOR_SUPPLIED_BITE')
    return {'plastic_power_per_width_w_m': res['plastic_power_per_width_w_m'],
            'friction_power_per_width_w_m': power, 'friction_power_basis': basis,
            'bite_heat_per_width_w_m': res['bite_heat_per_width_w_m'],
            'strip_heat_fraction': res['strip_heat_fraction'],
            'roll_heat_fraction_per_roll': res['roll_heat_fraction_per_roll'],
            'heat_to_each_work_roll_per_width_w_m': res['heat_to_each_work_roll_per_width_w_m'],
            'entry_temperature_k': res['entry_temperature_k'],
            'exit_temperature_k': res['exit_temperature_k'],
            'strip_temperature_rise_k': res['strip_temperature_rise_k'],
            'temperature_limit_k': res['temperature_limit_k'], 'flags': flags}


def heating_section(case, trib, cache, op_bite, cells, roll_e, roll_nu):
    rows = []
    for i, (label, src) in enumerate(pass_rows(case)):
        row = {'label': label, 'exit_thickness_m': src['exit_thickness_m'],
               'exit_speed_m_s': src['exit_speed_m_s']}
        try:
            bite = op_bite if i == 0 else (case_pass_bite(case, src, op_bite)
                                           or cache.get(bite_pass(case, src)))
            if bite is None:
                raise ValueError('no bite response for the case pass')
            state_for = getattr(cache, 'state_for', None)
            state = state_for(bite) if state_for is not None and is_half_space(bite) else None
            row.update(heating_row(case, src, bite, trib, cells, roll_e, roll_nu, state))
        except ValueError as exc:
            row['rejected'] = str(exc)
        rows.append(row)
    return {'status': bt.STATUS_HEATING, 'operating': rows[0], 'schedule': rows[1:],
            'note': 'Bite heat per width = homogeneous plastic work + interface slip '
                    'dissipation of the pass solution; strip keeps strip_heat_fraction, each '
                    'work roll (1 - strip_heat_fraction)/2 (bite_tribology.pass_heating).'}


# ============================================================================= speed-consistent
def speed_consistent_critical_speed(case, trib, cache, stand, spans, beta, op_bite, scan_range):
    """Exit speed u with u = u_crit(mu(u)) (friction falls with speed), both beta and 0."""
    p = case['pass']
    radius = p['work_roll_radius_m']
    ratio, slip = film_radius_ratio(op_bite), op_bite.forward_slip_fraction
    memo = {}
    _, _, closure = tribology_objects(trib)
    anchor = friction_at(trib, p, radius, ratio, slip, p['exit_speed_m_s'])[
        'friction_coefficient']
    mu_used = p['friction_coefficient']

    def at(u):
        if u not in memo:
            raw = friction_at(trib, p, radius, ratio, slip, u)['friction_coefficient']
            # the closure's SLOPE is used, anchored at the friction used at the operating point
            mu = max(closure.mu_v, mu_used + raw - anchor)
            row = {'exit_speed_m_s': u, 'friction_coefficient': mu,
                   'placeholder_closure_friction_coefficient': raw}
            try:
                bite = cache.get(bite_pass(case, dict(p, friction_coefficient=mu)))
                c = critical_speed(stand, bite, spans, speed_range_m_s=scan_range,
                                   bite_damping_transit_fraction=beta)
                c0 = c.get('without_bite_damping', c)
                row.update(critical_exit_speed_m_s=_crit(c, scan_range),
                           critical_exit_speed_without_bite_damping_m_s=_crit(c0, scan_range),
                           critical_status=c['status'])
            except ValueError as exc:
                row['rejected'] = str(exc)
            memo[u] = row
        return memo[u]

    def g(u, key):
        r = at(u)
        if 'rejected' in r:
            return None
        uc = r[key]
        return -math.inf if uc is None else u - uc

    speeds = _logspace(*SPEED_CONSISTENT_SCAN_M_S, SPEED_CONSISTENT_POINTS)
    roots, lowest = {}, {}
    for key in ('critical_exit_speed_m_s', 'critical_exit_speed_without_bite_damping_m_s'):
        vals = [(u, g(u, key)) for u in speeds]
        vals = [(u, v) for u, v in vals if v is not None]
        root, status = None, 'NO_CROSSING_IN_SCAN'
        if vals and vals[0][1] >= 0 and vals[0][0] != speeds[0]:
            # the lower scan speeds have no bite (rejected by the operating bite's model): the
            # crossing lies at or below the lowest assessable speed, not at it
            status = 'UNSTABLE_AT_LOWEST_ASSESSABLE_SPEED'
            lowest[key] = vals[0][0]
        elif vals and vals[0][1] >= 0:
            status, root = 'UNSTABLE_AT_LOWEST_SCANNED_SPEED', vals[0][0]
        else:
            for (ua, va), (ub, vb) in zip(vals, vals[1:]):
                if va < 0 <= vb:
                    root, status = _illinois(lambda u: g(u, key), ua, va, ub, vb), \
                        'CROSSING_FOUND'
                    break
        roots[key] = (root, status)
    scan = [memo[u] for u in sorted(memo)]
    names = {'critical_exit_speed_m_s': 'with_bite_damping',
             'critical_exit_speed_without_bite_damping_m_s': 'without_bite_damping'}
    extra = ({'lowest_assessable_exit_speed_m_s': {names[k]: v for k, v in lowest.items()},
              'scan_note': 'speeds below the lowest assessable one have no roll bite with the '
                           "operating bite's model (see scan[].rejected)"}
             if lowest else {})          # keys only then
    return {**extra, 'status': roots['critical_exit_speed_m_s'][1],
            'speed_consistent_critical_exit_speed_m_s': roots['critical_exit_speed_m_s'][0],
            'speed_consistent_critical_exit_speed_without_bite_damping_m_s':
                roots['critical_exit_speed_without_bite_damping_m_s'][0],
            'status_without_bite_damping': roots[
                'critical_exit_speed_without_bite_damping_m_s'][1],
            'bite_damping_transit_fraction': beta, 'contact_radius_ratio_held': ratio,
            'inlet_angle_basis': inlet_angle_basis(op_bite),
            'friction_used_at_operating_speed': mu_used,
            'placeholder_closure_friction_at_operating_speed': anchor,
            'friction_law': ('mu(u) = mu_used + [mu_closure(u) - mu_closure(u_op)], floored at '
                             'the closure mu_v: the placeholder closure supplies the slope, the '
                             'friction used at the operating point the level'),
            'forward_slip_fraction_held': slip, 'scan': scan,
            'relative_tolerance': SPEED_CONSISTENT_REL_TOL,
            'note': 'Solves u = u_crit(mu(u)) by a log-speed scan and Illinois regula falsi in '
                    'log speed (bracket below 1 % or 6 iterations); mu(u) from the '
                    'placeholder closure with the inlet-angle radius and forward slip held at '
                    'the operating bite. Friction falling with speed lowers the critical speed.'}


def _illinois(fun, a, fa, b, fb):
    """Root of fun in log(u) between a (fa < 0) and b (fb >= 0): Illinois regula falsi."""
    la, lb = math.log(a), math.log(b)
    if math.isinf(fa):
        fa = -b          # 'stable over the scan' at a: treat as far below the root
    side = 0
    for _ in range(SPEED_CONSISTENT_MAX_ITERATIONS):
        if lb - la <= math.log1p(SPEED_CONSISTENT_REL_TOL):
            break
        lc = (la * fb - lb * fa) / (fb - fa)
        lc = min(max(lc, la + 0.02 * (lb - la)), lb - 0.02 * (lb - la))
        fc = fun(math.exp(lc))
        if fc is None:
            break
        if math.isinf(fc):
            fc = -math.exp(lb)
        if fc >= 0:
            lb, fb = lc, fc
            if side == 1:
                fa /= 2
            side = 1
        else:
            la, fa = lc, fc
            if side == -1:
                fb /= 2
            side = -1
    return math.exp((la * fb - lb * fa) / (fb - fa)) if fb != fa else math.exp(lb)


def _crit(c, scan_range):
    if c['status'] == 'UNSTABLE_AT_LOWEST_SCANNED_SPEED':
        return scan_range[0]
    return c['critical_exit_speed_m_s']


def span_wave_limit_hz(case):
    sp = case['spans']
    c = math.sqrt(sp['strip_youngs_modulus_pa'] / STRIP_DENSITY_KG_M3)
    return min(c / (2 * sp['entry_span_length_m']), c / (2 * sp['exit_span_length_m']))


# ============================================================================= gauge control
def _response_rows(res, names):
    rows = []
    for name, r in zip(names, res['responses']):
        rows.append({'source': name, 'frequency_hz': r['frequency_hz'],
                     'with_agc_exit_thickness_per_unit_disturbance':
                         r['exit_thickness_per_unit_disturbance'],
                     'with_agc_exit_thickness_phase_rad': r['exit_thickness_phase_rad'],
                     'no_agc_exit_thickness_per_unit_disturbance':
                         r['no_agc_exit_thickness_per_unit_disturbance'],
                     'no_agc_exit_thickness_phase_rad': r['no_agc_exit_thickness_phase_rad'],
                     'cylinder_stroke_per_unit_disturbance':
                         r['cylinder_stroke_per_unit_disturbance'],
                     'agc_to_no_agc_magnitude_ratio': r['agc_to_no_agc_magnitude_ratio']})
    return rows


def _agc_crit_summary(st):
    w, wo = st['critical_speed_with_agc'], st['critical_speed_without_agc']
    return {'agc': st['agc'], 'stable_at_operating_speed': st['stable'],
            'max_growth_rate_per_s': st['max_growth_rate_per_s'],
            'critical_exit_speed_with_agc_m_s': w['critical_exit_speed_m_s'],
            'critical_status_with_agc': w['status'],
            'critical_exit_speed_without_agc_m_s': wo['critical_exit_speed_m_s'],
            'critical_speed_relative_change': st['critical_speed_relative_change'],
            'critical_exit_speed_with_agc_without_bite_damping_m_s':
                w.get('without_bite_damping', {}).get('critical_exit_speed_m_s'),
            'critical_status_with_agc_without_bite_damping':
                w.get('without_bite_damping', {}).get('status'),
            'critical_exit_speed_without_agc_without_bite_damping_m_s':
                wo.get('without_bite_damping', {}).get('critical_exit_speed_m_s'),
            'critical_speed_relative_change_without_bite_damping':
                st.get('critical_speed_relative_change_without_bite_damping'),
            'onset_frequency_with_agc_hz': w['onset_frequency_hz'],
            'flags': st['flags']}


def gauge_control_section(case, gc, stand, bite, spans, beta, roll_freqs, trib, get_bite,
                          scan_range):
    p = case['pass']
    u = p['exit_speed_m_s']
    agc = agc_of(gc)
    names = sorted(roll_freqs)
    freqs = [roll_freqs[n] for n in names]
    out = {'status': md.STATUS, 'not_supplied': False, 'inputs': dict(gc),
           'roll_frequencies_hz': dict(roll_freqs), 'flags': [], 'limitations': [],
           'static_formulas_label': STATIC_LABEL}
    for dist, key in (('work_backup_runout', 'runout'), ('entry_thickness', 'entry_thickness')):
        res = md.agc_frequency_response(stand, bite, spans, u, agc, freqs, disturbance=dist,
                                        bite_damping_transit_fraction=beta)
        out[key] = {'disturbance': dist, 'disturbance_unit': res['disturbance_unit'],
                    'responses': _response_rows(res, names),
                    'analytic_static_with_agc_tension_off':
                        res['analytic_static_exit_thickness_per_unit_disturbance_tension_off'],
                    'analytic_static_no_agc_tension_off':
                        res['analytic_static_exit_thickness_per_unit_disturbance_tension_off_'
                            'no_agc']}
        if dist == 'work_backup_runout':
            out['eccentricity_amplification_vs_no_agc'] = res[
                'eccentricity_amplification_vs_no_agc']
            out['mill_modulus_n_m'] = res['mill_modulus_n_m']
            out['strip_modulus_n_m'] = res['strip_modulus_n_m']
    st = md.agc_stability(stand, bite, spans, u, agc, speed_range_m_s=scan_range,
                          bite_damping_transit_fraction=beta)
    out['chatter_with_loop'] = {'supplied_loop': _agc_crit_summary(st)}
    if gc['force_filter_hz'] is None:
        st2 = md.agc_stability(stand, bite, spans, u, agc_of(gc, DEFAULT_FORCE_FILTER_HZ),
                               speed_range_m_s=scan_range, bite_damping_transit_fraction=beta)
        out['chatter_with_loop']['with_25_hz_force_filter'] = _agc_crit_summary(st2)
    else:
        out['chatter_with_loop']['with_25_hz_force_filter'] = None
    out['flags'].append('AGC_CHATTER_INTERACTION_DEPENDS_ON_LOOP_ROLL_OFF')
    out['limitations'].append(
        'An idealised first-order cylinder loop lags 90 degrees above its bandwidth and acts as '
        'negative damping of the loaded stand mode; a real loop rolls off faster. The AGC '
        'chatter numbers are shown for the supplied loop and with a 25 Hz force filter; they '
        'do not enter the hypothesis evidence.')
    out['speed_change_gauge_shift'] = None
    if trib is not None:
        try:
            sens = friction_force_sensitivity(get_bite, bite_pass(case, p))
            radius = p['work_roll_radius_m']
            lo_u = 0.5 * u
            mu_hi = friction_at(trib, p, radius, film_radius_ratio(bite),
                                bite.forward_slip_fraction, u)['friction_coefficient']
            mu_lo = friction_at(trib, p, radius, film_radius_ratio(bite),
                                bite.forward_slip_fraction, lo_u)['friction_coefficient']
            shift = md.speed_change_gauge_shift(sens['dforce_dfriction_n'], mu_hi - mu_lo,
                                                stand.mill_modulus_n_m, bite.strip_modulus_n_m,
                                                gc['compensation_gain'])
            out['speed_change_gauge_shift'] = {
                'from_exit_speed_m_s': lo_u, 'to_exit_speed_m_s': u,
                'friction_at_low_speed': mu_lo, 'friction_at_operating_speed': mu_hi,
                'delta_friction': mu_hi - mu_lo,
                'dforce_dfriction_n': sens['dforce_dfriction_n'],
                'sensitivity_bite_model': sens['bite_model'],
                'exit_thickness_change_m': shift['exit_thickness_change_m'],
                'exit_thickness_change_without_agc_m':
                    shift['exit_thickness_change_without_agc_m'],
                'separating_force_change_n': shift['separating_force_change_n'],
                'cylinder_stroke_change_m': shift['cylinder_stroke_change_m'],
                'label': STATIC_LABEL}
            if supplied_bite_mix(bite):
                note = SENSITIVITY_MIX_NOTE.format(sens['bite_model'])
                out['speed_change_gauge_shift']['flags'] = [SENSITIVITY_MIX_FLAG]
                out['speed_change_gauge_shift']['note'] = note
                out['flags'].append(SENSITIVITY_MIX_FLAG)
                out['limitations'].append(note)
        except ValueError as exc:
            out['speed_change_gauge_shift'] = {'rejected': str(exc)}
    return out


# ============================================================================= drive
def drive_modes(drive):
    tm = md.torsional_modes(drive['inertias_kg_m2'], drive['stiffnesses_n_m_rad'])
    modes = [{'name': f'torsional_{i + 1}', 'frequency_hz': f, 'family': 'torsional_drive'}
             for i, f in enumerate(tm['elastic_frequencies_hz'])]
    return tm, modes


def drive_section(case, drive, stand, bite, spans, beta, gc):
    tm, modes = drive_modes(drive)
    u = case['pass']['exit_speed_m_s']
    out = {'status': md.STATUS, 'not_supplied': False, 'inputs': dict(drive),
           'torsional': {k: tm[k] for k in ('frequencies_hz', 'elastic_frequencies_hz',
                                            'mode_shapes', 'rigid_body_mode_present',
                                            'first_elastic_frequency_hz', 'flags')},
           'catalogue_modes': modes,
           'pitch_at_operating_speed_m': [{'name': m['name'], 'frequency_hz': m['frequency_hz'],
                                           'strip_pitch_m': u / m['frequency_hz']}
                                          for m in modes],
           'roll_speed_ripple': None}
    if bite is not None and modes:
        try:
            agc = agc_of(gc) if gc else None
            rr = md.roll_speed_ripple_response(stand, bite, spans, u,
                                               [m['frequency_hz'] for m in modes], agc=agc,
                                               bite_damping_transit_fraction=beta)
            out['roll_speed_ripple'] = {
                'with_agc': agc is not None, 'disturbance_unit': 'm/s of roll surface speed',
                'responses': [{k: r[k] for k in (
                    'frequency_hz', 'exit_thickness_per_unit_disturbance',
                    'exit_thickness_per_relative_speed_m', 'entry_tension_per_unit_disturbance',
                    'exit_tension_per_unit_disturbance')} for r in rr['responses']],
                'analytic_dc_limit': rr['analytic_dc_limit'], 'flags': rr['flags']}
        except ValueError as exc:
            out['roll_speed_ripple'] = {'rejected': str(exc)}
    return out


# ============================================================================= incoming
def incoming_section(case, iv, stand, bite, spans, beta, gc, get_bite):
    p = case['pass']
    u = p['exit_speed_m_s']
    h0, h1 = p['entry_thickness_m'], p['exit_thickness_m']
    dy = iv['flow_stress_variation_fraction'] * p['mean_flow_stress_pa']
    alpha = gc['compensation_gain'] if gc else 0.0
    sens = flow_stress_sensitivity(get_bite, bite_pass(case, p))
    shift = md.hardness_gauge_shift(sens['dforce_dflow_stress_m2'], dy, stand.mill_modulus_n_m,
                                    bite.strip_modulus_n_m, alpha)
    out = {'status': md.STATUS, 'not_supplied': False, 'inputs': dict(iv),
           'flow_stress_amplitude_pa': dy,
           'dforce_dflow_stress_m2': sens['dforce_dflow_stress_m2'],
           'dslip_dflow_stress_per_pa': sens['dslip_dflow_stress_per_pa'],
           'sensitivity_bite_model': sens['bite_model'],
           'static': {'compensation_gain': alpha,
                      'exit_thickness_change_m': shift['exit_thickness_change_m'],
                      'exit_thickness_change_without_agc_m':
                          shift['exit_thickness_change_without_agc_m'],
                      'relative_exit_thickness_change': shift['exit_thickness_change_m'] / h1,
                      'label': STATIC_LABEL},
           'coil_synchronous': None, 'flags': list(sens['flags'])}
    if supplied_bite_mix(bite):
        out['flags'].append(SENSITIVITY_MIX_FLAG)
        out['limitations'] = [SENSITIVITY_MIX_NOTE.format(sens['bite_model'])]
    d_coil = case['kinematics']['entry_coil_diameter_m']
    if iv['coil_synchronous']:
        if d_coil is None:
            out['coil_synchronous'] = not_supplied('kinematics.entry_coil_diameter_m is null')
        else:
            cs = md.coil_synchronous_frequencies(u * h1 / h0, d_coil, 3, entry_thickness_m=h0,
                                                 exit_thickness_m=h1)
            agc = agc_of(gc) if gc else md.GaugemeterAGC(0.0, DEFAULT_FORCE_FILTER_HZ)
            res = md.agc_frequency_response(
                stand, bite, spans, u, agc, [x['frequency_hz'] for x in cs['harmonics']],
                disturbance='flow_stress', flow_sensitivity=sens,
                bite_damping_transit_fraction=beta)
            rows = []
            for x, r in zip(cs['harmonics'], res['responses']):
                rows.append({'order': x['order'], 'frequency_hz': x['frequency_hz'],
                             'exit_strip_pitch_m': x['exit_strip_pitch_m'],
                             'exit_thickness_amplitude_with_agc_m':
                                 r['exit_thickness_per_unit_disturbance'] * dy
                                 if gc else None,
                             'exit_thickness_amplitude_no_agc_m':
                                 r['no_agc_exit_thickness_per_unit_disturbance'] * dy})
            out['coil_synchronous'] = {'entry_coil_diameter_m': d_coil,
                                       'entry_speed_m_s': u * h1 / h0,
                                       'decoiler_rotation_hz': cs['decoiler_rotation_hz'],
                                       'harmonics': rows}
    return out


SENSITIVITY_MIX_FLAG = 'FORCE_SENSITIVITY_DERIVED_NOT_FROM_SUPPLIED_BITE'
SENSITIVITY_MIX_NOTE = ('With a supplied bite response the force sensitivity here comes from '
                        'perturbed bites of the derived bite model ({}) while the strip modulus '
                        'is the supplied one, so the two may be inconsistent.')


def supplied_bite_mix(bite):
    """True when ``bite`` is a supplied (override) bite: finite-difference force sensitivities
    then come from a derived model and are combined with the supplied strip modulus."""
    return bite.source == 'supplied' and not is_foil_model(bite)


def replace_bite_flags(bite, extra):
    return replace(bite, flags=tuple(bite.flags) + tuple(f for f in extra if f not in bite.flags))
