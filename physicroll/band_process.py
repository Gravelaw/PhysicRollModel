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


# SPEC18 package 6: optional friction-closure keys (a given closure is normalised to all keys)
CLOSURE_OPTIONAL_P6 = ('model', 'contact_friction', 'contact_ratio_curve', 'valley_film_curve',
                       'valley_model')
CONTACT_FRICTION_MESSAGE = (
    'tribology.friction_closure.contact_friction is required for the load_sharing_curve model: '
    'the sources span 0.013 to 0.1, so no default is set; supply the friction on the contact '
    'areas, for example identified from your measured roll force or forward slip, or from a '
    'strip-drawing test with your oil and roll finish')


def _closure_curve(where, value, field):
    msg = (f'{where} must be null or a list of 2 to 12 {{"film_ratio", "{field}"}} points with '
           'increasing film ratio')
    if value is None:
        return None
    if not isinstance(value, list) or not 2 <= len(value) <= 12:
        raise ValueError(msg)
    out = []
    for pt in value:
        if not isinstance(pt, dict) or set(pt) != {'film_ratio', field} or \
                not _is_num(pt['film_ratio']) or not _is_num(pt[field]):
            raise ValueError(msg)
        out.append({'film_ratio': float(pt['film_ratio']), field: float(pt[field])})
    try:
        bt._curve(where, [(x['film_ratio'], x[field]) for x in out],
                  'contact' if field == 'contact_ratio' else 'valley')
    except ValueError as exc:
        raise ValueError(f'{where}: {exc}') from exc
    return out


def _closure_options(clo):
    model = clo.get('model') or 'placeholder_exponential'
    if model not in bt.CLOSURE_MODELS:
        raise ValueError(f'tribology.friction_closure.model must be one of {bt.CLOSURE_MODELS}')
    valley = clo.get('valley_model') or 'constant'
    if valley not in bt.VALLEY_MODELS:
        raise ValueError('tribology.friction_closure.valley_model must be one of '
                         f'{bt.VALLEY_MODELS}')
    mu_c = clo.get('contact_friction')
    if mu_c is not None:
        if not _is_num(mu_c) or not 0 < mu_c <= 1:
            raise ValueError('tribology.friction_closure.contact_friction must be in (0, 1]')
        mu_c = float(mu_c)
    if model == 'load_sharing_curve' and mu_c is None:
        raise ValueError(CONTACT_FRICTION_MESSAGE)
    return {'model': model, 'contact_friction': mu_c,
            'contact_ratio_curve': _closure_curve('tribology.friction_closure.contact_ratio_curve',
                                                  clo.get('contact_ratio_curve'),
                                                  'contact_ratio'),
            'valley_film_curve': _closure_curve('tribology.friction_closure.valley_film_curve',
                                                clo.get('valley_film_curve'),
                                                'valley_film_over_roughness'),
            'valley_model': valley}


def closure_kwargs(clo):
    """FrictionClosure arguments from a validated friction_closure dict."""
    out = {k: clo[k] for k in ('mu_b', 'mu_v', 'lambda0')}
    for k in ('model', 'contact_friction', 'valley_model'):
        if clo.get(k) is not None:
            out[k] = clo[k]
    if clo.get('contact_ratio_curve') is not None:
        out['contact_ratio_curve'] = tuple((x['film_ratio'], x['contact_ratio'])
                                           for x in clo['contact_ratio_curve'])
    if clo.get('valley_film_curve') is not None:
        out['valley_film_curve'] = tuple((x['film_ratio'], x['valley_film_over_roughness'])
                                         for x in clo['valley_film_curve'])
    return out


def is_load_sharing(trib):
    clo = (trib or {}).get('friction_closure')
    return bool(clo) and clo.get('model') == 'load_sharing_curve'


def bite_mean_pressure_pa(case, bite):
    """Mean bite pressure F/(width*L) of a bite response, or None without a bite."""
    if bite is None:
        return None
    return bite.separating_force_n / (case['pass']['width_m'] * bite.contact_length_m)


TRIBOLOGY_KEYS = ('lubricant', 'surface_finish', 'inlet_temperature_k',
                  'strip_entry_temperature_k', 'strip_heat_fraction', 'thermal_correction',
                  'use_computed_friction')
TRIBOLOGY_OPTIONAL = ('friction_closure', 'temperature_limit_k', 'oil_flash_point_k',
                      'oil_supply_temperature_cap_k',   # SPEC17 A10: user limits, no default
                      'interface_conductance_w_m2k', 'use_computed_heat_partition')   # SPEC18 p9
INTERFACE_CONDUCTANCE_RANGE_W_M2K = (1e3, 1e9)
HARDENING_COMMON = ('law', 'provenance', 'prior_equivalent_strain', 'reference_thickness_m',
                    'use_computed_flow_stress')
HARDENING_LAW_KEYS = {
    'power': ('yield_stress_pa', 'strength_coefficient_pa', 'exponent'),
    'voce': ('initial_stress_pa', 'saturation_stress_pa', 'characteristic_strain',
             'stage_iv_slope_pa'),
    'tome_voce': ('saturation_scale_pa', 'stage_iv_slope_pa', 'initial_hardening_rate_pa')}
HARDENING_OPTIONAL = ('rate_temperature',)        # SPEC18 package 8 (B1), null by default
RATE_TEMPERATURE_KEYS = ('rate_sensitivity', 'reference_strain_rate_per_s',
                         'temperature_coefficient_per_k', 'reference_temperature_k',
                         'rate_sensitivity_slope_per_k', 'provenance', 'use_rate_temperature')
SIGNED_HARDENING_KEYS = ('stage_iv_slope_pa',)   # may be negative (work softening, B2)


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
        keys('tribology.friction_closure', clo, ('mu_b', 'mu_v', 'lambda0'),
             CLOSURE_OPTIONAL_P6)
        out_clo = {k: num(f'tribology.friction_closure.{k}', clo[k])
                   for k in ('mu_b', 'mu_v', 'lambda0')}
        out_clo.update(_closure_options(clo))
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
    # SPEC18 package 9: computed heat partition (both null by default)
    hc = t.get('interface_conductance_w_m2k')
    if hc is not None:
        lo, hi = INTERFACE_CONDUCTANCE_RANGE_W_M2K
        hc = num('tribology.interface_conductance_w_m2k', hc)
        if not lo <= hc <= hi:
            raise ValueError(f'tribology.interface_conductance_w_m2k must be in [{lo:g}, {hi:g}] '
                             'W/m2K or null')
    out['interface_conductance_w_m2k'] = hc
    uc = t.get('use_computed_heat_partition')
    out['use_computed_heat_partition'] = (None if uc is None else boolean(
        'tribology.use_computed_heat_partition', uc))
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
               else bt.FrictionClosure(**closure_kwargs(t['friction_closure'])))
    return lubricant, finish, closure


def validate_rate_temperature(rt, use_computed):
    """``hardening.rate_temperature`` (SPEC18 package 8): the five numbers of
    ``bite_tribology.RateTemperatureFactor``, ``provenance`` and ``use_rate_temperature``."""
    keys('hardening.rate_temperature', rt, RATE_TEMPERATURE_KEYS)
    prov = rt['provenance']
    if not isinstance(prov, str) or not prov.strip():
        raise ValueError('hardening.rate_temperature.provenance must be a nonempty string')
    out = {k: num(f'hardening.rate_temperature.{k}', rt[k]) for k in RATE_TEMPERATURE_KEYS[:5]}
    out['provenance'] = prov
    out['use_rate_temperature'] = boolean('hardening.rate_temperature.use_rate_temperature',
                                          rt['use_rate_temperature'])
    try:
        rate_temperature_factor(out).validate()
    except ValueError as exc:
        raise ValueError(f'hardening.rate_temperature: {exc}') from exc
    if out['use_rate_temperature'] and not use_computed:
        raise ValueError('hardening.rate_temperature.use_rate_temperature needs '
                         'use_computed_flow_stress')
    return out


def rate_temperature_factor(rt):
    return bt.RateTemperatureFactor(**{k: rt[k] for k in RATE_TEMPERATURE_KEYS[:6]})


def validate_hardening(h, material):
    if not isinstance(h, dict) or h.get('law') not in HARDENING_LAW_KEYS:
        raise ValueError("hardening.law must be 'power', 'voce' or 'tome_voce'")
    law_keys = HARDENING_LAW_KEYS[h['law']]
    keys('hardening', h, HARDENING_COMMON + law_keys, HARDENING_OPTIONAL)
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
        out[k] = num(f'hardening.{k}', h[k], nonnegative=k not in SIGNED_HARDENING_KEYS)
    try:
        hardening_law(out, material).validate()
    except ValueError as exc:
        raise ValueError(f'hardening: {exc}') from exc
    rt = h.get('rate_temperature')
    out['rate_temperature'] = (None if rt is None else
                               validate_rate_temperature(rt, out['use_computed_flow_stress']))
    return out


def hardening_law(h, material):
    if h['law'] == 'power':
        return PowerHardeningLaw(alloy=material['alloy'], temper=material['temper'],
                                 yield_stress_pa=h['yield_stress_pa'],
                                 strength_coefficient_pa=h['strength_coefficient_pa'],
                                 exponent=h['exponent'], provenance=h['provenance'])
    if h['law'] == 'tome_voce':
        return bt.TomeVoceHardening(saturation_scale_pa=h['saturation_scale_pa'],
                                    stage_iv_slope_pa=h['stage_iv_slope_pa'],
                                    initial_hardening_rate_pa=h['initial_hardening_rate_pa'],
                                    provenance=h['provenance'])
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


def _mu_inputs(trib, src, radius, ratio, slip, exit_speed, mean_pressure_pa=None):
    h0, h1 = src['entry_thickness_m'], src['exit_thickness_m']
    extra = {} if mean_pressure_pa is None else {'mean_pressure_pa': mean_pressure_pa}
    return dict(extra, roll_surface_speed_m_s=exit_speed / (1 + slip),
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


def friction_at(trib, src, radius, ratio, slip, exit_speed, mean_pressure_pa=None):
    """Closure friction at a pass; ``mean_pressure_pa`` (of the pass's bite) is the bite state
    the computed valley models of the load-sharing closure need (the placeholder ignores it)."""
    lub, fin, clo = tribology_objects(trib)
    return bt.friction_at_speed(lub, fin, clo, **_mu_inputs(trib, src, radius, ratio, slip,
                                                           exit_speed, mean_pressure_pa))


LOAD_SHARING_ROW_KEYS = ('contact_area_ratio', 'contact_friction', 'valley_friction',
                         'valley_model', 'valley_film_thickness_m', 'valley_shear_stress_pa',
                         'valley_shear_capped', 'dmu_dlambda')


def _closure_row_keys(trib, res):
    """Keys of the load-sharing closure for a friction row (none for the placeholder)."""
    if not is_load_sharing(trib):
        return {}
    out = {k: res[k] for k in LOAD_SHARING_ROW_KEYS if k in res}
    out['closure_flags'] = [f for f in res['flags'] if f in (
        bt.LOAD_SHARING_FLAG, bt.PUBLISHED_CURVE_FLAG, bt.ENTERED_CONTACT_FRICTION_FLAG,
        bt.OUTSIDE_CURVE_FLAG, bt.LIMITING_SHEAR_FLAG)]
    return out


# ============================================================================= flow stress
def flow_stress_section(case, hardening):
    """Flow stress per pass from the hardening law (supplied value beside it)."""
    law = hardening_law(hardening, case['material'])
    ref = hardening['reference_thickness_m']
    rt = hardening.get('rate_temperature')
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
        if rt is not None and 'computed_mean_flow_stress_pa' in row:
            _rate_temperature_row(case, src, row, rt, flags)
        rows.append(row)
    out = {'status': bt.STATUS_HARDENING, 'law_type': hardening['law'],
           'law': asdict(law), 'prior_equivalent_strain': hardening['prior_equivalent_strain'],
           'reference_thickness_m': ref,
           'use_computed_flow_stress': hardening['use_computed_flow_stress'],
           'passes': rows, 'flags': flags,
           'note': 'Equivalent strain eps = prior + (2/sqrt(3))*ln(h_ref/h); the mean flow '
                   'stress of each pass is the strain average over that pass '
                   '(bite_tribology.schedule_flow_stress).'}
    # SPEC18 package 8: keys only when given (the artifacts stay additive)
    if rt is not None:
        out['rate_temperature'] = dict(
            rt, basis=RATE_TEMPERATURE_BASIS, consumers=RATE_TEMPERATURE_CONSUMERS,
            applied=rt['use_rate_temperature'], note=RATE_TEMPERATURE_NOTE)
    out['alloy_group_context'] = alloy_group_context(case)
    return out


# ------------------------------------------------ rate and temperature (SPEC18 package 8, B1)
RATE_MEASURED_LIMIT_PER_S = 1e-2      # the measured range ends here [TM-LB1 EX]
RATE_EXTRAPOLATION_MULTIPLE = 100.0   # flag above 100 times it [SPEC18 package 8]
RATE_FROM_ARC_FLAG = 'STRAIN_RATE_FROM_UNDEFORMED_ARC'
BITE_TEMPERATURE_MISSING_FLAG = 'BITE_TEMPERATURE_NOT_AVAILABLE_REFERENCE_USED'
RATE_FACTOR_APPLIED_FLAG = 'FLOW_STRESS_RATE_TEMPERATURE_FACTOR_APPLIED'
RATE_EXTRAPOLATED_FLAG = 'RATE_SENSITIVITY_EXTRAPOLATED_BEYOND_MEASURED_RATES'
RATE_FACTOR_REJECTED_FLAG = 'RATE_TEMPERATURE_FACTOR_REJECTED'
RATE_TEMPERATURE_FLAGS = (RATE_FROM_ARC_FLAG, BITE_TEMPERATURE_MISSING_FLAG,
                          RATE_FACTOR_APPLIED_FLAG, RATE_EXTRAPOLATED_FLAG,
                          RATE_FACTOR_REJECTED_FLAG)
RATE_TEMPERATURE_BASIS = {
    'factor': '(rate/rate_ref)^m(T) * (1 - c_T*(T - T_ref)), m(T) = m + dm/dT*(T - T_ref) '
              'floored at 0 [form: TM report gap B1, "as the minimum"]',
    'strain_rate': 'mean bite rate (u/l_d)*ln(h0/h1) [TM gap B1] with l_d = sqrt(R*(h0 - h1)): '
                   'strain rate from the undeformed arc [D, SPEC18: avoids a fixed point with '
                   'the bite; the rate enters to the power m]',
    'bite_temperature': 'tribology.strip_entry_temperature_k + 0.5*strip_heat_fraction*w_pl/'
                        '(rho*c), w_pl = (2/sqrt(3))*Y*ln(h0/h1) from the unfactored flow '
                        'stress, rho*c 2.43e6 J/m3K [D, SPEC18: mid-bite strip temperature]; '
                        'the reference temperature without tribology'}
RATE_TEMPERATURE_NOTE = ('The measured rate sensitivity ends at 1e-2 /s [TM-LB1 EX]; rolling '
                         'rates are about five decades higher. The net of rate and temperature '
                         'at rolling conditions is not known; enter both or neither.')
# Which consumer takes the factored flow stress (use_rate_temperature true): it replaces the
# mean flow stress of every pass row of the effective case, so everything that reads that
# value takes it; the rows of process.flow_stress say so (flow_stress_with_rate_temperature_pa,
# used_mean_flow_stress_pa) and the flag FLOW_STRESS_RATE_TEMPERATURE_FACTOR_APPLIED is set.
RATE_TEMPERATURE_CONSUMERS = [
    {'consumer': 'bite_tribology.schedule_flow_stress', 'uses_factor': False,
     'how_shown': 'unchanged; its flag STRAIN_RATE_SENSITIVITY_IGNORED stays in its own result'},
    {'consumer': 'every bite model (Hitchcock, experimental mattress, reduced half-space) of '
                 'the case pass and the schedule', 'uses_factor': True,
     'how_shown': 'the bite takes the effective mean flow stress (effective_inputs.pass, '
                  'process.flow_stress.passes[].used_mean_flow_stress_pa)'},
    {'consumer': 'bite sensitivities (flow stress, friction, tensions, gauges)',
     'uses_factor': True,
     'how_shown': 'perturbed about the factored value; the strain-rate term itself is NOT a '
                  'force term in the stability calculation (chatter.rate_sensitivity_damping '
                  'reports it beside the heuristic bite damping)'},
    {'consumer': 'speed-change gauge shift (gauge_control)', 'uses_factor': True,
     'how_shown': 'through the bite; the factor is NOT re-evaluated at the changed speed'},
    {'consumer': 'pass heating', 'uses_factor': True,
     'how_shown': 'plastic work from the effective flow stress'},
    {'consumer': 'shape inputs and yield checks (width model, flatness)', 'uses_factor': True,
     'how_shown': 'through the bite and the effective flow stress'},
    {'consumer': 'the bite temperature of the factor itself', 'uses_factor': False,
     'how_shown': 'w_pl from the unfactored flow stress (bite_temperature_k in each row)'}]


def _rate_temperature_row(case, src, row, rt, flags):
    """Strain rate, bite temperature and factor of one pass row (SPEC18 package 8)."""
    trib = case['tribology']
    h0, h1 = src['entry_thickness_m'], src['exit_thickness_m']
    radius = case['pass']['work_roll_radius_m']
    y = row['computed_mean_flow_stress_pa']
    try:
        ld = math.sqrt(radius * (h0 - h1))
        rate = bt.mean_bite_strain_rate_per_s(src['exit_speed_m_s'], ld, h0, h1)
        row['strain_rate_per_s'] = rate
        row['strain_rate_contact_length_m'] = ld
        _add(flags, RATE_FROM_ARC_FLAG)
        if trib is not None:
            w_pl = 2 / math.sqrt(3) * y * math.log(h0 / h1)
            t = (trib['strip_entry_temperature_k'] + 0.5 * trib['strip_heat_fraction'] * w_pl
                 / bt.ALUMINIUM_VOLUMETRIC_HEAT_CAPACITY_J_M3K)
            row['bite_temperature_basis'] = 'mid-bite strip temperature [D, SPEC18]'
        else:
            t = rt['reference_temperature_k']
            row['bite_temperature_basis'] = ('reference temperature (no tribology: '
                                             'bite temperature not available)')
            _add(flags, BITE_TEMPERATURE_MISSING_FLAG)
        row['bite_temperature_k'] = t
        if rate > RATE_MEASURED_LIMIT_PER_S * RATE_EXTRAPOLATION_MULTIPLE:
            _add(flags, RATE_EXTRAPOLATED_FLAG)
        fr, ft, m = rate_temperature_factor(rt).parts(rate, t)
        row.update(rate_sensitivity_at_bite_temperature=m, rate_factor=fr,
                   temperature_factor=ft, rate_temperature_factor=fr * ft,
                   flow_stress_with_rate_temperature_pa=y * fr * ft)
    except ValueError as exc:
        row['rate_temperature_rejected'] = str(exc)
        _add(flags, RATE_FACTOR_REJECTED_FLAG)


def _add(flags, flag):
    if flag not in flags:
        flags.append(flag)


X2_SENTENCE = ('A positive stage-IV (late) hardening slope is right for 1200-type and '
               'solute-bearing grades [TM-LB3 AB] and wrong in sign for purified-matrix Al-Fe '
               'alloys and high-purity grades beyond 80 % reduction [TM-LB2 EX]; it is '
               'temperature-dependent in 8079 [TM-LB7 AB]. Nothing selects a law by alloy '
               'group: the law and its sign are your entry.')


def alloy_group_context(case):
    """The X2 sentence and the alloy-group table row for ``material.alloy``: the table
    (``band_products.alloy_group_reference``) has no alloy matching of its own, so no row is
    selected (SPEC18 package 8 left this open)."""
    return {'alloy': case['material']['alloy'], 'row': None,
            'reason': 'band_products.alloy_group_reference has no alloy matching of its own; '
                      'see that table (thin-gauge products guide) for the rows by alloy group',
            'sentence': X2_SENTENCE}


def rate_sensitivity_damping(case, bite, flow_section, dforce_dflow_stress_m2, heuristic):
    """The force term in phase with gap velocity that a rate-sensitive flow stress gives
    (SPEC18 package 8, D) [D, re-derived in SPEC18]: the thickness strain rate in the bite gains
    ``-h_dot/h_mean`` when the gap moves at ``h_dot``, so
    ``d(eps_dot)/eps_dot = -h_dot*l_d/(h_mean*u*ln(h0/h1))``, ``dY/Y = m*d(eps_dot)/eps_dot``,
    ``dF = F_Y*dY``. Hence ``F_hdot_rate = -F_Y*Y*m*l_d/(h_mean*u*ln(h0/h1))`` and the
    equivalent transit fraction ``beta_rate = F_hdot_rate*u/(F_h*l_d) =
    F_Y*Y*m/(Q*h_mean*ln(h0/h1))``, ``Q = -F_h``. REPORTED only: no stability calculation uses
    it."""
    p = case['pass']
    rows = [r for r in flow_section.get('passes') or [] if r.get('label') == 'case pass']
    if not rows or rows[0].get('rate_sensitivity_at_bite_temperature') is None:
        raise ValueError('no rate sensitivity for the case pass (its flow-stress row has no '
                         'rate and temperature factor)')
    m = rows[0]['rate_sensitivity_at_bite_temperature']
    h0, h1 = bite.entry_thickness_m, bite.exit_thickness_m
    h_mean, ln_r = 0.5 * (h0 + h1), math.log(h0 / h1)
    y, u, ld = p['mean_flow_stress_pa'], p['exit_speed_m_s'], bite.contact_length_m
    q = -bite.dforce_dexit_thickness_n_m
    f_hdot = -dforce_dflow_stress_m2 * y * m * ld / (h_mean * u * ln_r)
    beta = dforce_dflow_stress_m2 * y * m / (q * h_mean * ln_r)
    return {'rate_sensitivity': m, 'dforce_dgap_velocity_n_s_m': f_hdot,
            'equivalent_transit_fraction': beta, 'heuristic_transit_fraction': heuristic,
            'share_of_heuristic': beta / heuristic if heuristic else None,
            'formula': 'F_hdot_rate = -F_Y*Y*m*l_d/(h_mean*u*ln(h0/h1)); beta_rate = '
                       'F_Y*Y*m/(Q*h_mean*ln(h0/h1)), Q = -F_h',
            'basis': '[D, re-derived in SPEC18] rate-sensitive flow stress with the mean bite '
                     'strain rate; m at the bite temperature of the case pass; F_Y = dF/dY of '
                     'the operating bite model',
            'note': 'reported only: the stability results use the heuristic unchanged (gap C3 '
                    'is not implemented)'}


def apply_flow_stress(case, section):
    """Replace the supplied flow stress by the computed one in the case pass and schedule.

    Rows are matched by position (``flow_stress_section`` builds them from ``pass_rows`` in
    order), not by label: a schedule row may legally be labelled 'case pass' too."""
    rows = section['passes']
    if len(rows) != len(pass_rows(case)):
        raise ValueError('flow stress rows do not match the case pass and schedule')
    rt = section.get('rate_temperature')
    use_rt = rt is not None and rt['use_rate_temperature']
    for (_, src), row in zip(pass_rows(case), rows):
        if use_rt and 'flow_stress_with_rate_temperature_pa' in row:
            src['mean_flow_stress_pa'] = row['flow_stress_with_rate_temperature_pa']
            row['rate_temperature_factor_applied'] = True
            _add(section['flags'], RATE_FACTOR_APPLIED_FLAG)
        elif 'computed_mean_flow_stress_pa' in row:
            src['mean_flow_stress_pa'] = row['computed_mean_flow_stress_pa']
            if use_rt:
                row['rate_temperature_factor_applied'] = False
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
        p_mean = bite_mean_pressure_pa(case, bite)
    except ValueError as exc:
        ratio, slip = 1.0, 0.0
        film_ratio, basis = 1.0, INLET_ANGLE_BASIS_MATTRESS + ' (no bite)'
        p_mean = None
        out['bite_error'] = str(exc)
        out['method'] += ' (bite rejected: undeformed roll radius used)'
    res = friction_at(trib, src, radius, film_ratio, slip, u, p_mean)
    out.update(_closure_row_keys(trib, res))
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
    p0 = None
    if is_load_sharing(trib) and trib['friction_closure']['valley_model'] != 'constant':
        # the computed valley models need a bite state from the start: the supplied-friction
        # bite's mean pressure (its own derivation; a rejection rejects the row)
        p0 = bite_mean_pressure_pa(case, cache.get(bite_pass(case, src)))
    first = friction_at(trib, src, radius, film_ratio, slip, u, p0)
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
        res = friction_at(trib, src, radius, film_ratio, slip, u,
                          bite_mean_pressure_pa(case, bite))
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
    out.update(_closure_row_keys(trib, last))
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
    if is_load_sharing(trib):
        flags = [bt.LOAD_SHARING_FLAG, bt.ENTERED_CONTACT_FRICTION_FLAG]
        if trib['friction_closure']['contact_ratio_curve'] is None:
            flags.append(bt.PUBLISHED_CURVE_FLAG)
        for row in rows:
            for f in row.get('closure_flags') or []:
                if f not in flags:
                    flags.append(f)
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
    if is_load_sharing(trib):
        extra['limitations'] = list(bt.LOAD_SHARING_LIMITATIONS) + extra.get('limitations', [])
        return {'status': bt.STATUS_LOAD_SHARING,
                'use_computed_friction': trib['use_computed_friction'],
                'operating': rows[0], 'schedule': rows[1:], **extra, 'flags': flags,
                'note': bt.LOAD_SHARING_NOTE + (
                    ' With use_computed_friction the friction is a fixed point friction -> '
                    f'bite -> friction (at most {FRICTION_FIXED_POINT_ITERATIONS} passes); '
                    'otherwise it is evaluated once at the supplied-friction bite.')}
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
        thermal_correction=trib['thermal_correction'],
        mean_pressure_pa=bite_mean_pressure_pa(case, bite))
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
            **({'closure_note': bt.LOAD_SHARING_NOTE} if is_load_sharing(trib) else {}),
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


COMPUTED_HEAT_FLAG = 'STRIP_HEAT_FRACTION_COMPUTED_FROM_INTERFACE_MODEL'
SUPPLIED_HEAT_FLAG = 'STRIP_HEAT_FRACTION_SUPPLIED_NOT_COMPUTED'
ROLL_ENTRY_ASSUMED_FLAG = 'ROLL_ENTRY_TEMPERATURE_ASSUMED_COOLANT_OR_OIL'
HEAT_SHARE_DIFFERENCE_WARN = 0.1      # report: entered and computed share differ by more


def use_computed_heat_partition(trib):
    return bool(trib and trib.get('use_computed_heat_partition'))


def _roll_thermal_inputs(case):
    w = case.get('width_model')
    if w is not None:
        r = w['roll']
        return (r['conductivity_w_mk'], r['density_kg_m3'], r['specific_heat_j_kgk'],
                'width_model.roll')
    from .roll_thermal import RollThermalProperties   # local: defaults only
    d = RollThermalProperties(radius_m=1.0, barrel_length_m=1.0)
    return (d.conductivity_w_mk, d.density_kg_m3, d.specific_heat_j_kgk,
            'defaults of roll_thermal.RollThermalProperties (no width_model.roll)')


def pass_heat_partition(case, src, bite, trib, plastic_power, friction_power, friction_row):
    """``heat_partition`` of one pass (SPEC18 package 9), or ``not_supplied`` with the reason.
    Reported beside the supplied share; it drives pass heating and the width model's default
    roll heat fraction only with ``tribology.use_computed_heat_partition``."""
    if trib is None:
        return not_supplied('needs tribology')
    if bite is None:
        return not_supplied('needs a bite')
    lub, _, clo = tribology_objects(trib)
    film = (friction_row or {}).get('film_thickness_m')
    hc_given = trib.get('interface_conductance_w_m2k')
    if hc_given is None and not film:
        return not_supplied('needs the film thickness of the pass (its friction row) or '
                            'tribology.interface_conductance_w_m2k')
    k_r, rho_r, c_r, roll_basis = _roll_thermal_inputs(case)
    w = case.get('width_model')
    if w is not None:
        t_r0, t_basis = w['coolant_temperature_k'], 'width_model.coolant_temperature_k'
    else:
        t_r0, t_basis = trib['inlet_temperature_k'], 'tribology.inlet_temperature_k'
    u = src['exit_speed_m_s']
    kw = dict(plastic_power_per_width_w_m=plastic_power,
              friction_power_per_width_w_m=friction_power,
              contact_length_m=bite.contact_length_m,
              roll_surface_speed_m_s=u / (1 + bite.forward_slip_fraction),
              exit_thickness_m=src['exit_thickness_m'], exit_speed_m_s=u,
              entry_thickness_m=src['entry_thickness_m'],
              strip_entry_temperature_k=trib['strip_entry_temperature_k'],
              roll_entry_surface_temperature_k=t_r0, roll_conductivity_w_mk=k_r,
              roll_density_kg_m3=rho_r, roll_specific_heat_j_kgk=c_r)
    if hc_given is not None:
        hc, hc_basis = hc_given, 'tribology.interface_conductance_w_m2k (entered)'
    else:
        k_oil = lub.effective_conductivity_w_mk()
        hc = k_oil / film
        hc_basis = (f'k_oil/h = {k_oil:g} W/mK / {film:.4g} m [row A3]; k_oil '
                    + ('[M] default 0.13 W/mK (published for a kerosine foil base oil: 0.125 '
                       'W/mK at ambient pressure, 0.25 W/mK in the nip [E6 FT])'
                       if lub.conductivity_w_mk is None else 'entered')
                    + '; film: smooth inlet film of the friction row ('
                    + str((friction_row or {}).get('bite_source') or 'bite') + ' bite, '
                    + (clo.model if trib.get('friction_closure') else 'placeholder_exponential')
                    + ' closure)')
    res = bt.heat_partition(interface_conductance_w_m2k=hc, **kw)
    out = dict(res)
    out['interface_conductance_basis'] = hc_basis
    out['film_thickness_m'] = film if hc_given is None else None
    out['roll_properties_basis'] = roll_basis
    out['roll_entry_surface_temperature_k'] = t_r0
    out['roll_entry_surface_temperature_basis'] = t_basis
    out['flags'] = list(res['flags']) + [ROLL_ENTRY_ASSUMED_FLAG]
    out['supplied_strip_heat_fraction'] = trib['strip_heat_fraction']
    out['measured_strip_share_foil_mill'] = {
        'range': list(bt.MEASURED_FOIL_STRIP_SHARE),
        'source': '[V abstract: Yin et al. 2003; TM-LA19 AB] measurement on a foil mill, '
                  'a net balance; gauge and speed not in the abstract'}
    if hc_given is None:
        out['strip_heat_fraction_at_published_oil_conductivities'] = [
            {'oil_conductivity_w_mk': k, 'tag': tag,
             'strip_heat_fraction': bt.heat_partition(interface_conductance_w_m2k=k / film,
                                                      **kw)['strip_heat_fraction_computed']}
            for k, tag in zip(bt.PUBLISHED_OIL_CONDUCTIVITIES_W_MK,
                              ('[E6 FT] ambient pressure', '[E6 FT] in the nip'))]
    return out


def heating_row(case, src, bite, trib, cells, roll_e, roll_nu, state=None, friction_row=None):
    power, basis = friction_power_per_width(case, src, bite, cells, roll_e, roll_nu, state)
    fs = trib['strip_heat_fraction'] if trib else 0.0
    t_in = trib['strip_entry_temperature_k'] if trib else 293.15

    def heating(share):
        return bt.pass_heating(entry_thickness_m=src['entry_thickness_m'],
                               exit_thickness_m=src['exit_thickness_m'],
                               exit_speed_m_s=src['exit_speed_m_s'],
                               mean_flow_stress_pa=src['mean_flow_stress_pa'],
                               strip_heat_fraction=share, entry_temperature_k=t_in,
                               friction_power_per_width_w_m=power,
                               temperature_limit_k=trib['temperature_limit_k'] if trib else None)
    res = heating(fs)
    part = None
    if trib is not None:      # SPEC18 package 9 (none without tribology: rows unchanged)
        try:
            part = pass_heat_partition(case, src, bite, trib,
                                       res['plastic_power_per_width_w_m'], power, friction_row)
        except ValueError as exc:
            part = failed('heat_partition', exc)
    f_c = (part or {}).get('strip_heat_fraction_computed')
    computed_used = use_computed_heat_partition(trib) and f_c is not None
    if computed_used:
        res = heating(min(1.0, max(0.0, f_c)))
    flags = list(res['flags'])
    if computed_used:
        flags = [COMPUTED_HEAT_FLAG if f == SUPPLIED_HEAT_FLAG else f for f in flags]
    if bite.source == 'supplied' and not is_foil_model(bite):
        flags.append('FRICTION_POWER_NOT_AVAILABLE_FOR_SUPPLIED_BITE')
    extra = {}
    if part is not None:
        extra['heat_partition'] = part
        if f_c is not None and not use_computed_heat_partition(trib):
            extra['supplied_minus_computed_strip_heat_fraction'] = fs - f_c
        if computed_used:
            extra['strip_heat_fraction_basis'] = ('computed: bite heat partition '
                                                  '(heat_partition, clipped to [0, 1])')
    return {**_heating_keys(res, power, basis, flags), **extra}


def _heating_keys(res, power, basis, flags):
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


def heating_section(case, trib, cache, op_bite, cells, roll_e, roll_nu, friction=None):
    """``friction``: the friction section (its rows give each pass's film thickness, matched
    by position) for the computed heat partition (SPEC18 package 9)."""
    fr_rows = ([friction.get('operating')] + list(friction.get('schedule') or [])
               if isinstance(friction, dict) and 'operating' in friction else [])
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
            row.update(heating_row(case, src, bite, trib, cells, roll_e, roll_nu, state,
                                   fr_rows[i] if i < len(fr_rows) else None))
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
    p_mean = bite_mean_pressure_pa(case, op_bite)
    anchor_res = friction_at(trib, p, radius, ratio, slip, p['exit_speed_m_s'], p_mean)
    anchor = anchor_res['friction_coefficient']
    # floor: the closure's valley friction (the placeholder's mu_v; the load-sharing closure's
    # valley friction at the operating point)
    floor = anchor_res.get('valley_friction', closure.mu_v)
    mu_used = p['friction_coefficient']

    def at(u):
        if u not in memo:
            raw = friction_at(trib, p, radius, ratio, slip, u, p_mean)['friction_coefficient']
            # the closure's SLOPE is used, anchored at the friction used at the operating point
            mu = max(floor, mu_used + raw - anchor)
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
    if is_load_sharing(trib):            # keys only then: default results unchanged
        extra['friction_closure'] = 'load_sharing_curve'
        extra['closure_note'] = ('The load-sharing closure supplies the slope (the '
                                 '"placeholder_closure_*" keys hold its values); floored at its '
                                 'valley friction at the operating point.')
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
            p_mean = bite_mean_pressure_pa(case, bite)
            mu_hi = friction_at(trib, p, radius, film_radius_ratio(bite),
                                bite.forward_slip_fraction, u, p_mean)['friction_coefficient']
            mu_lo = friction_at(trib, p, radius, film_radius_ratio(bite),
                                bite.forward_slip_fraction, lo_u, p_mean)['friction_coefficient']
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
            if is_load_sharing(trib):          # key only then: default results unchanged
                out['speed_change_gauge_shift']['friction_closure'] = 'load_sharing_curve'
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


# ============================================ friction identification (SPEC18 package 7, BT-G6)
# Inversion of a constant-friction bite to entered pass records (force, and where measured
# forward slip and torque). Every number below is the brief's (SPEC18 package 7) [D].
IDENT_STATUS = 'IDENTIFIED_FROM_ENTERED_RECORDS_NOT_VERIFIED'
IDENT_BRACKET = (0.003, 0.3)
IDENT_REL_TOL = 1e-4               # relative, in the matched quantity
IDENT_MAX_SOLVES = 12              # secant of mu_F
IDENT_REFINE_SOLVES = 8            # refinement of a scan root (slip, torque) [D]
IDENT_SCAN = (0.4, 2.5, 9)         # geometric scan around mu_F
IDENT_EXPONENT_STEP = 0.01         # mu_F*(1 +- 0.01)
IDENT_CONSISTENT_LIMIT = 2.0       # |normalised residual|
IDENT_WEAK_SLIP_EXPONENT = 0.5
IDENT_Y_SCALE = (0.5, 2.0)
IDENT_NEWTON_ITERATIONS = 8
IDENT_PARABOLA_STEPS = 6           # repeated parabola of the joint fit [D, deviation]
IDENT_PARABOLA_TOL = 1e-4          # in ln mu [D]
IDENT_DIFFERS_FRACTION = 0.20
IDENT_MIN_CONTACT_RATIO = 0.05
IDENT_FILM_RATIO_SPREAD = 0.20
IDENT_DEFAULT_VALLEY_FRICTION = 0.008
PASS_RECORD_UNCERTAINTY_DEFAULTS = {'force_uncertainty_fraction': 0.05,
                                    'slip_uncertainty_absolute': 0.01,
                                    'torque_uncertainty_fraction': 0.10}   # [D] analyst choices
IDENT_FLAG = 'FRICTION_IDENTIFIED_FROM_ENTERED_RECORDS'
IDENT_WEAK_SLIP_FLAG = 'FORWARD_SLIP_INSENSITIVE_TO_FRICTION_IN_THIS_REGIME'
IDENT_SLIP_NOT_REPRODUCED_FLAG = 'MEASURED_SLIP_NOT_REPRODUCED_BY_CONSTANT_FRICTION_BITE'
IDENT_DIFFERS_FLAG = 'IDENTIFIED_FRICTION_DIFFERS_FROM_CASE_FRICTION'
IDENT_FLAGS = (IDENT_FLAG, IDENT_WEAK_SLIP_FLAG, IDENT_SLIP_NOT_REPRODUCED_FLAG, IDENT_DIFFERS_FLAG)
IDENT_WEAK_SLIP_SENTENCE = ('with a no-slip zone the forward slip hardly depends on friction; the '
                            'force is the better indicator here')
IDENT_TWO_UNKNOWNS_NOTE = 'two unknowns from two numbers: there is no redundancy to check them'
IDENT_HOW_TO_USE = ('to use a value, enter it as pass.friction_coefficient; nothing is applied '
                    'automatically')
IDENT_UNCERTAINTY_BASIS = ('[D, first-order propagation] u = (entered uncertainty of the '
                           'quantity)/|d(quantity)/d ln(mu)| at mu_F (force and torque in ln, '
                           'slip absolute); interval mu*exp(-u) to mu*exp(+u)')
IDENT_LIMITATIONS = [
    'Constant friction through the bite: a friction distribution is the published remedy for '
    'foil forward slip [BT-S5 AB]; it is not built.',
    'The bite model\'s own status enters the identified value: on the published foil case the '
    'mattress bite gives W_bar 49.8 and the reduced half-space bite 88.9 to 92.9, while the '
    'printed model gives 78 to 134 depending on an unstated end length; an identified friction '
    'absorbs that spread, by about 12 % from load and 30 % from slip on that case.',
    'Flow stress is taken as entered (the force-and-slip pair also returns a flow-stress scale, '
    'with no redundancy to check it).',
    'Forward slip of the reduced half-space bite is defined to elastic order only (the no-slip '
    'zone creeps by up to 0.6 %, which is 1 to 2.5 % of the slip; SPEC18 package 2, item 4).',
    'Simple forward-slip formulas are reported as unreliable [BT-S37 SN]; none is used.',
    'No closed-gap load share.',
    'The entered numbers are not verified: calibrated stays false.']


def _quantity_of(state, name):
    return {'force': state['force_n'], 'slip': state['forward_slip_fraction'],
            'torque': state.get('torque_per_work_roll_nm')}[name]


class _Solver:
    """Counts the distinct solves of one record; ``solve(mu, y_scale)`` -> state or None."""

    def __init__(self, fun):
        self.fun, self.seen, self.errors = fun, {}, {}

    def __call__(self, mu, y_scale=1.0):
        key = (mu, y_scale)
        if key not in self.seen:
            try:
                self.seen[key] = self.fun(mu, y_scale)
            except ValueError as exc:
                self.seen[key] = None
                self.errors[key] = str(exc)
        return self.seen[key]

    @property
    def solves(self):
        return len(self.seen)


def _residual(name, state, meas, unc):
    """Normalised residual of one quantity: ln for force and torque, absolute for slip."""
    v = _quantity_of(state, name)
    if v is None or (name != 'slip' and v <= 0):
        return None
    if name == 'slip':
        return (v - meas) / unc
    return math.log(v / meas) / unc


def _match_error(name, value, meas, unc):
    """g(mu) of a root search: ln ratio for force/torque, difference for slip; and the test."""
    if name == 'slip':
        return value - meas, abs(value - meas) <= IDENT_REL_TOL * max(abs(meas), unc)
    return math.log(value / meas), abs(value / meas - 1) <= IDENT_REL_TOL


def _not_found(reason, **extra):
    return dict({'status': 'NOT_FOUND', 'value': None, 'reason': reason}, **extra)


def _secant_force(solver, mu0, meas):
    """Step 1: mu with F_model(mu) = F_meas (secant in ln mu from the case friction and
    mu*(F_meas/F_model)^(1/2); <= 12 solves; bracket [0.003, 0.3])."""
    lo, hi = (math.log(x) for x in IDENT_BRACKET)
    x0 = min(max(math.log(mu0), lo), hi)
    st = solver(math.exp(x0))
    if st is None:
        return _not_found('the bite model rejected the pass at the case friction: '
                          + solver.errors[(math.exp(x0), 1.0)])
    g0, ok = _match_error('force', st['force_n'], meas, 0.0)
    if ok:
        return {'status': 'FOUND', 'value': math.exp(x0), 'solves': 1}
    x1 = x0 - 0.5 * g0
    used = 1
    while used < IDENT_MAX_SOLVES:
        at_edge = False
        if x1 < lo or x1 > hi:
            edge = lo if x1 < lo else hi
            if x0 == edge:
                return _not_found(f'no friction in [{IDENT_BRACKET[0]:g}, {IDENT_BRACKET[1]:g}] '
                                  f'reproduces the force (the model force at {math.exp(edge):.4g} '
                                  f'is {st["force_n"]:.4g} N against {meas:.4g} N)',
                                  solves=used)
            x1, at_edge = edge, True
        mu1 = math.exp(x1)
        st1 = solver(mu1)
        used += 1
        if st1 is None:
            return _not_found(f'the bite model rejected the pass at friction {mu1:.4g}: '
                              + solver.errors[(mu1, 1.0)], solves=used)
        g1, ok = _match_error('force', st1['force_n'], meas, 0.0)
        if ok:
            return {'status': 'FOUND', 'value': mu1, 'solves': used}
        if g1 == g0:
            return _not_found('the force does not change with friction here', solves=used)
        x2 = x1 - g1 * (x1 - x0) / (g1 - g0)
        if at_edge and (x2 - x1) * (x1 - x0) > 0:
            return _not_found(f'no friction in [{IDENT_BRACKET[0]:g}, {IDENT_BRACKET[1]:g}] '
                              f'reproduces the force (the model force at {mu1:.4g} is '
                              f'{st1["force_n"]:.4g} N against {meas:.4g} N)', solves=used)
        x0, g0, st, x1 = x1, g1, st1, x2
    return _not_found(f'secant not converged in {IDENT_MAX_SOLVES} solves', solves=used)


def _scan(solver, center):
    lo_f, hi_f, n = IDENT_SCAN
    mus = [center * lo_f * (hi_f / lo_f) ** (i / (n - 1)) for i in range(n)]
    mus[(n - 1) // 2] = center
    return [(m, solver(m)) for m in mus
            if IDENT_BRACKET[0] <= m <= IDENT_BRACKET[1]]


def _scan_root(solver, scan, name, meas, unc, center):
    """Step 2: the root of quantity ``name`` on the scan nearest ``center``, refined by
    Illinois regula falsi in ln mu."""
    pts = []
    for m, st in scan:
        v = None if st is None else _quantity_of(st, name)
        if v is not None and (name == 'slip' or v > 0):
            pts.append((m, _match_error(name, v, meas, unc)))
    if not pts:
        return _not_found('the model returns no value of this quantity on the scan')
    for m, (g, ok) in pts:
        if ok and m == center:
            return {'status': 'FOUND', 'value': m, 'multiple_roots': False, 'roots_on_scan': 1}
    brackets = [(a, ga, b, gb) for (a, (ga, _)), (b, (gb, _)) in zip(pts, pts[1:])
                if ga == 0 or ga * gb < 0]
    if not brackets:
        vals = [_quantity_of(st, name) for _, st in scan if st is not None]
        return _not_found(f'no friction between {scan[0][0]:.4g} and {scan[-1][0]:.4g} reproduces '
                          f'the measured value {meas:.4g} (model range {min(vals):.4g} to '
                          f'{max(vals):.4g})')
    a, ga, b, gb = min(brackets, key=lambda t: abs(math.log(math.sqrt(t[0] * t[2]) / center)))
    la, lb, side = math.log(a), math.log(b), 0
    value = None
    for _ in range(IDENT_REFINE_SOLVES):
        lc = (la * gb - lb * ga) / (gb - ga) if gb != ga else 0.5 * (la + lb)
        mc = math.exp(lc)
        st = solver(mc)
        v = None if st is None else _quantity_of(st, name)
        if v is None or (name != 'slip' and v <= 0):
            return _not_found(f'the bite model rejected the pass at friction {mc:.4g}')
        gc, ok = _match_error(name, v, meas, unc)
        if ok:
            value = mc
            break
        if (gc > 0) == (gb > 0):
            lb, gb = lc, gc
            if side == 1:
                ga /= 2
            side = 1
        else:
            la, ga = lc, gc
            if side == -1:
                gb /= 2
            side = -1
    if value is None:
        return _not_found(f'refinement not converged in {IDENT_REFINE_SOLVES} solves '
                          f'(between {math.exp(la):.5g} and {math.exp(lb):.5g})')
    return {'status': 'FOUND', 'value': value, 'multiple_roots': len(brackets) > 1,
            'roots_on_scan': len(brackets)}


def _objective(st, meas, unc):
    rs = [r for r in (_residual(n, st, meas[n], unc[n]) for n in meas) if r is not None]
    return sum(r * r for r in rs) if len(rs) == len(meas) else None


def _joint(solver, scan, meas, unc):
    """Step 3: minimiser of the sum of squared normalised residuals over the scan, refined by a
    parabola in ln mu through the best three points."""
    pts = [(m, _objective(st, meas, unc)) for m, st in scan if st is not None]
    pts = [(m, j) for m, j in pts if j is not None]
    if not pts:
        return _not_found('no scan point returns every measured quantity')
    i = min(range(len(pts)), key=lambda k: pts[k][1])
    at_edge = i in (0, len(pts) - 1)
    mu, first, steps = pts[i][0], None, 0
    if not at_edge:
        # three points bracketing the minimum, in ln mu; the parabola's vertex replaces the
        # worst-placed point and the parabola is repeated (successive parabolic interpolation,
        # SPEC18 package 7 deviation: one parabola on the 9-point scan is 6 % off on exact data
        # of the half-space bite) until the vertex moves less than 1e-4 in ln mu
        tri = [(math.log(m), j) for m, j in pts[i - 1:i + 2]]
        for steps in range(1, IDENT_PARABOLA_STEPS + 1):
            (x0, j0), (x1, j1), (x2, j2) = tri
            den = (x0 - x1) * (x0 - x2) * (x1 - x2)
            a = (x2 * (j1 - j0) + x1 * (j0 - j2) + x0 * (j2 - j1)) / den
            b = (x2 * x2 * (j0 - j1) + x1 * x1 * (j2 - j0) + x0 * x0 * (j1 - j2)) / den
            if not a > 0:
                break
            xv = min(max(-b / (2 * a), x0), x2)
            if first is None:
                first = math.exp(xv)
            moved = abs(xv - math.log(mu))
            mu = math.exp(xv)
            if moved < IDENT_PARABOLA_TOL or xv in (x0, x1, x2):
                break
            stv = solver(mu)
            jv = None if stv is None else _objective(stv, meas, unc)
            if jv is None:
                break
            # keep the bracket (lowest point in the middle)
            pts3 = sorted(tri + [(xv, jv)])
            k = min(range(1, 3), key=lambda q: pts3[q][1])
            tri = pts3[k - 1:k + 2]
            mu = math.exp(tri[1][0]) if tri[1][1] <= jv else mu
    st = solver(mu)
    if st is None:
        return _not_found(f'the bite model rejected the pass at friction {mu:.4g}')
    res = {n: _residual(n, st, meas[n], unc[n]) for n in meas}
    return {'status': 'FOUND', 'value': mu, 'at_scan_edge': at_edge,
            'first_parabola_value': first, 'parabola_steps': steps,
            'normalised_residuals': res,
            'consistent': all(r is not None and abs(r) <= IDENT_CONSISTENT_LIMIT
                              for r in res.values())}


def _friction_and_flow_stress(solver, mu0, meas, unc, first_jacobian):
    """Step 4: (mu, Y scale) reproducing force and slip exactly; Newton in (ln mu, ln s)."""
    lo, hi = (math.log(x) for x in IDENT_BRACKET)
    slo, shi = (math.log(x) for x in IDENT_Y_SCALE)
    x, y = math.log(mu0), 0.0
    jac = first_jacobian
    for it in range(IDENT_NEWTON_ITERATIONS + 1):
        st = solver(math.exp(x), math.exp(y))
        if st is None:
            return _not_found(f'the bite model rejected the pass at friction {math.exp(x):.4g}, '
                              f'flow-stress scale {math.exp(y):.4g}')
        r1, ok1 = _match_error('force', st['force_n'], meas['force'], 0.0)
        r2, ok2 = _match_error('slip', st['forward_slip_fraction'], meas['slip'], unc['slip'])
        if ok1 and ok2:
            return {'status': 'FOUND', 'friction_coefficient': math.exp(x),
                    'flow_stress_scale': math.exp(y), 'iterations': it,
                    'note': IDENT_TWO_UNKNOWNS_NOTE}
        if it == IDENT_NEWTON_ITERATIONS:
            break
        h = math.log1p(IDENT_EXPONENT_STEP)
        if jac is None:
            sx = solver(math.exp(x + h), math.exp(y))
            if sx is None:
                return _not_found('a derivative solve was rejected')
            jac = [[math.log(sx['force_n'] / st['force_n']) / h, None],
                   [(sx['forward_slip_fraction'] - st['forward_slip_fraction']) / h, None]]
        sy = solver(math.exp(x), math.exp(y + h))
        if sy is None:
            return _not_found('a derivative solve was rejected')
        jac[0][1] = math.log(sy['force_n'] / st['force_n']) / h
        jac[1][1] = (sy['forward_slip_fraction'] - st['forward_slip_fraction']) / h
        det = jac[0][0] * jac[1][1] - jac[0][1] * jac[1][0]
        if det == 0:
            return _not_found('force and slip respond alike to friction and flow stress here')
        dx = -(r1 * jac[1][1] - r2 * jac[0][1]) / det
        dy = -(jac[0][0] * r2 - jac[1][0] * r1) / det
        nx, ny = x + dx, y + dy
        if not (lo <= nx <= hi and slo <= ny <= shi):
            if (x in (lo, hi) and not lo <= nx <= hi) or (y in (slo, shi) and not slo <= ny <= shi):
                return _not_found(f'the pair leaves friction [{IDENT_BRACKET[0]:g}, '
                                  f'{IDENT_BRACKET[1]:g}] or flow-stress scale '
                                  f'[{IDENT_Y_SCALE[0]:g}, {IDENT_Y_SCALE[1]:g}]')
            nx, ny = min(max(nx, lo), hi), min(max(ny, slo), shi)
        x, y, jac = nx, ny, None
    return _not_found(f'Newton not converged in {IDENT_NEWTON_ITERATIONS} iterations')


def friction_exponents(solver, mu):
    """``d ln(.)/d ln(mu)`` of force, forward slip and torque at ``mu`` (central difference with
    mu*(1 +- 0.01)) and ``d f/d ln(mu)``; values None where a solve is rejected."""
    lo, hi = solver(mu * (1 - IDENT_EXPONENT_STEP)), solver(mu * (1 + IDENT_EXPONENT_STEP))
    out = {'load_exponent_in_friction': None, 'slip_exponent_in_friction': None,
           'torque_exponent_in_friction': None, 'dslip_dln_friction': None}
    if lo is None or hi is None:
        return out
    d = math.log((1 + IDENT_EXPONENT_STEP) / (1 - IDENT_EXPONENT_STEP))
    out['load_exponent_in_friction'] = math.log(hi['force_n'] / lo['force_n']) / d
    f_lo, f_hi = lo['forward_slip_fraction'], hi['forward_slip_fraction']
    out['dslip_dln_friction'] = (f_hi - f_lo) / d
    if f_lo > 0 and f_hi > 0:
        out['slip_exponent_in_friction'] = math.log(f_hi / f_lo) / d
    t_lo, t_hi = lo.get('torque_per_work_roll_nm'), hi.get('torque_per_work_roll_nm')
    if t_lo and t_hi and t_lo > 0 and t_hi > 0:
        out['torque_exponent_in_friction'] = math.log(t_hi / t_lo) / d
    return out


def _uncertainty(value, u):
    if value is None or u is None:
        return None
    return {'ln_half_width': u, 'interval': [value * math.exp(-u), value * math.exp(u)],
            'basis': IDENT_UNCERTAINTY_BASIS}


def identify_record(solve, mu0, meas, unc):
    """Identification of one record (steps 1-5 of SPEC18 package 7).

    ``solve(mu, y_scale)`` -> state dict (``force_n``, ``forward_slip_fraction``,
    ``torque_per_work_roll_nm``) or ValueError; ``mu0`` the case friction; ``meas`` {'force',
    'slip', 'torque'} (None when not measured); ``unc`` the three uncertainties (force and
    torque fractions, slip absolute)."""
    solver = _Solver(solve)
    measured = {k: v for k, v in meas.items() if v is not None}
    row = {'friction_from_force': _secant_force(solver, mu0, meas['force'])}
    mu_f = row['friction_from_force']['value']
    center = mu_f if mu_f is not None else mu0
    ex = friction_exponents(solver, center)
    row['exponents_at'] = center
    row.update(ex)
    st_f = solver(center)
    scan = _scan(solver, center)
    for name, key in (('slip', 'friction_from_slip'), ('torque', 'friction_from_torque')):
        if meas.get(name) is None:
            row[key] = {'status': 'NOT_MEASURED', 'value': None}
        elif st_f is not None and _quantity_of(st_f, name) is None:
            row[key] = {'status': 'NOT_RETURNED_BY_MODEL', 'value': None}
        else:
            row[key] = _scan_root(solver, scan, name, meas[name], unc[name], center)
    # uncertainty of each identified value from the entered uncertainty [D, first order]
    e_f, e_t = ex['dslip_dln_friction'], ex['torque_exponent_in_friction']
    e_load = ex['load_exponent_in_friction']
    us = {'friction_from_force': unc['force'] / abs(e_load) if e_load else None,
          'friction_from_slip': unc['slip'] / abs(e_f) if e_f else None,
          'friction_from_torque': unc['torque'] / abs(e_t) if e_t else None}
    for key, u in us.items():
        if row[key].get('value') is not None:
            row[key]['uncertainty'] = _uncertainty(row[key]['value'], u)
    weak = (ex['slip_exponent_in_friction'] is not None
            and abs(ex['slip_exponent_in_friction']) < IDENT_WEAK_SLIP_EXPONENT)
    row['slip_weakly_determined'] = weak
    if weak and meas.get('slip') is not None:
        row['friction_from_slip']['weakly_determined'] = True
        row['friction_from_slip']['note'] = IDENT_WEAK_SLIP_SENTENCE
    row['normalised_residuals_at_friction_from_force'] = (
        {n: _residual(n, st_f, measured[n], unc[n]) for n in measured}
        if mu_f is not None and st_f is not None else None)
    row['friction_joint'] = _joint(solver, scan, measured, {n: unc[n] for n in measured})
    if meas.get('slip') is not None:
        jac = None
        if ex['load_exponent_in_friction'] is not None and mu_f is not None:
            jac = [[ex['load_exponent_in_friction'], None], [ex['dslip_dln_friction'], None]]
        row['friction_and_flow_stress'] = _friction_and_flow_stress(
            solver, center, meas, unc, jac)
    else:
        row['friction_and_flow_stress'] = {'status': 'NOT_MEASURED',
                                           'reason': 'needs force and forward slip'}
    row['agreement'] = _agreement(row, us)
    row['solves'] = solver.solves
    row['state_at_friction_from_force'] = st_f if mu_f is not None else None
    return row


def _agreement(row, us):
    """Pairwise agreement of the single-quantity values (difference in ln mu against twice the
    combined first-order uncertainty) and the outcome name."""
    keys = [k for k in ('friction_from_force', 'friction_from_slip', 'friction_from_torque')
            if row[k].get('value') is not None]
    pairs = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            d = math.log(row[b]['value'] / row[a]['value'])
            ua, ub = us[a], us[b]
            comb = math.sqrt(ua * ua + ub * ub) if ua is not None and ub is not None else None
            pairs.append({'pair': [a, b], 'difference_in_ln_friction': d,
                          'combined_uncertainty': comb,
                          'within_two_uncertainties': (None if comb is None else
                                                       abs(d) <= IDENT_CONSISTENT_LIMIT * comb)})
    joint = row['friction_joint']
    if row['friction_from_force']['status'] != 'FOUND':
        outcome = 'FORCE_NOT_MATCHED'
    elif len(keys) == 1 and all(row[k]['status'] in ('NOT_MEASURED', 'NOT_RETURNED_BY_MODEL')
                                for k in ('friction_from_slip', 'friction_from_torque')):
        outcome = 'SINGLE_MEASUREMENT'
    elif joint.get('consistent') and all(p['within_two_uncertainties'] is not False
                                         for p in pairs) and len(keys) > 1:
        outcome = 'MEASUREMENTS_AGREE'
    else:
        outcome = 'MEASUREMENTS_CONTRADICT'
    return {'outcome': outcome, 'pairs': pairs,
            'basis': 'joint fit consistent (every |normalised residual| <= 2) and every pair '
                     'within twice its combined uncertainty'}


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return None if not n else (s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2]))


def _ls_slope(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    return None if sxx == 0 else sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx


def record_source(case, rec):
    """The pass dict of a record: the case pass with the record's entered values."""
    src = dict(case['pass'])
    for k in ('exit_speed_m_s', 'entry_thickness_m', 'exit_thickness_m', 'entry_tension_pa',
              'exit_tension_pa', 'mean_flow_stress_pa'):
        if rec.get(k) is not None:
            src[k] = rec[k]
    return src


def implied_contact_friction(trib, case, src, state, mu, foil):
    """Contact friction mu_c = (mu - (1 - A)*mu_v)/A at the film ratio of the bite at mu
    [D, SPEC18: package 6's load sharing solved for the contact friction]."""
    _, _, clo = tribology_objects(trib)
    radius = case['pass']['work_roll_radius_m']
    ratio = 1.0 if foil else state['contact_radius_ratio']
    p_mean = state['force_n'] / (case['pass']['width_m'] * state['contact_length_m'])
    res = friction_at(trib, dict(src, friction_coefficient=mu), radius, ratio,
                      state['forward_slip_fraction'], src['exit_speed_m_s'], p_mean)
    lam = res['film_ratio']
    curve = clo.contact_curve()
    a, _, held = bt.contact_ratio_at(lam, curve)
    mu_v = clo.mu_v if trib.get('friction_closure') is not None else IDENT_DEFAULT_VALLEY_FRICTION
    out = {'film_ratio': lam, 'contact_area_ratio': a, 'valley_friction': mu_v,
           'curve_is_published_default': clo.contact_ratio_curve is None,
           'outside_curve_end_value_held': held,
           'basis': '[D, SPEC18: package 6\'s load sharing solved for the contact friction] '
                    'mu_c = (mu - (1 - A)*mu_v)/A, constant valley friction'}
    if a < IDENT_MIN_CONTACT_RATIO:
        out.update(contact_friction=None,
                   reason=f'contact ratio {a:.3g} below {IDENT_MIN_CONTACT_RATIO:g}: the '
                          'contact areas carry too little of the load to identify their friction')
    else:
        out['contact_friction'] = (mu - (1 - a) * mu_v) / a
    return out


def friction_identification(case, records, cache, op_bite, perturbed_model):
    """``process.friction_identification`` (SPEC18 package 7): friction identified from entered
    pass records with the bite model ``perturbed_model`` (that of the operating bite
    ``op_bite``); REPORTED only, never applied (``calibrated`` false)."""
    foil = perturbed_model in ('mattress', 'half_space')
    if not records:
        return not_supplied('measurement.pass_records is null or absent')
    trib = case['tribology']
    mu_case = case['pass']['friction_coefficient']
    rows, flags, extra_lims = [], [IDENT_FLAG], []
    for i, rec in enumerate(records):
        src = record_source(case, rec)
        base = bite_pass(case, src)

        def solve(mu, y_scale, base=base):
            return cache.state(replace(base, friction_coefficient=mu,
                                       mean_flow_stress_pa=base.mean_flow_stress_pa * y_scale),
                               model=perturbed_model)
        unc = {'force': rec['force_uncertainty_fraction'],
               'slip': rec['slip_uncertainty_absolute'],
               'torque': rec['torque_uncertainty_fraction']}
        meas = {'force': rec['separating_force_n'], 'slip': rec['forward_slip_fraction'],
                'torque': rec['torque_per_work_roll_nm']}
        row = identify_record(solve, mu_case, meas, unc)
        st = row.pop('state_at_friction_from_force')
        row = dict({'label': rec['label'], 'exit_speed_m_s': src['exit_speed_m_s'],
                    'measured': meas, 'uncertainties': unc}, **row)
        row['model_at_friction_from_force'] = (None if st is None else {
            'force_n': st['force_n'], 'forward_slip_fraction': st['forward_slip_fraction'],
            'torque_per_work_roll_nm': st.get('torque_per_work_roll_nm'),
            'contact_length_m': st['contact_length_m'], 'flags': st['flags']})
        if st is not None and 'NO_SLIP_ZONE_CREEP_ABOVE_ONE_PERCENT' in st['flags']:
            row['creep_limitation'] = True
            if 'creep' not in extra_lims:
                extra_lims.append('creep')
        if row['slip_weakly_determined'] and meas['slip'] is not None and \
                IDENT_WEAK_SLIP_FLAG not in flags:
            flags.append(IDENT_WEAK_SLIP_FLAG)
        res_f = row['normalised_residuals_at_friction_from_force']
        if res_f and res_f.get('slip') is not None and abs(res_f['slip']) > \
                IDENT_CONSISTENT_LIMIT or (meas['slip'] is not None and
                                           row['friction_from_slip']['status'] == 'NOT_FOUND'):
            row['slip_not_reproduced'] = True
            if IDENT_SLIP_NOT_REPRODUCED_FLAG not in flags:
                flags.append(IDENT_SLIP_NOT_REPRODUCED_FLAG)
        if trib is not None and st is not None:
            try:
                row['contact_friction_implied'] = implied_contact_friction(
                    trib, case, src, st, row['friction_from_force']['value'], foil)
            except ValueError as exc:
                row['contact_friction_implied'] = failed('contact friction implied', exc)
        else:
            row['contact_friction_implied'] = not_supplied(
                'needs tribology and the friction from force' if trib is None
                else 'the friction from force was not found')
        rows.append(row)
    mu_fs = [r['friction_from_force']['value'] for r in rows
             if r['friction_from_force']['value'] is not None]
    summary = {'friction_from_force': mu_fs, 'median': _median(mu_fs),
               'spread': (max(mu_fs) - min(mu_fs)) if mu_fs else None,
               'case_friction_coefficient': mu_case, 'slope_per_ln_exit_speed': None}
    pts = [(math.log(r['exit_speed_m_s']), r['friction_from_force']['value']) for r in rows
           if r['friction_from_force']['value'] is not None]
    if len({x for x, _ in pts}) >= 2:
        summary['slope_per_ln_exit_speed'] = _ls_slope([x for x, _ in pts], [y for _, y in pts])
    med = summary['median']
    if med is not None and abs(med / mu_case - 1) > IDENT_DIFFERS_FRACTION:
        flags.append(IDENT_DIFFERS_FLAG)
    summary['sentence'] = _ident_sentence(summary, rows)
    if trib is None:
        suggested = not_supplied('needs tribology')
    else:
        cs = [(r['contact_friction_implied']['film_ratio'],
               r['contact_friction_implied']['contact_friction']) for r in rows
              if r['contact_friction_implied'].get('contact_friction') is not None]
        suggested = {'contact_friction': _median([c for _, c in cs]),
                     'values': [c for _, c in cs],
                     'spread': (max(c for _, c in cs) - min(c for _, c in cs)) if cs else None,
                     'slope_per_ln_film_ratio': None,
                     'note': 'the published observation is that one contact friction does not '
                             'fit a speed range (E7 FT); enter a value as '
                             'tribology.friction_closure.contact_friction only by choice'}
        lams = [lam for lam, _ in cs]
        if len(cs) >= 2 and max(lams) > (1 + IDENT_FILM_RATIO_SPREAD) * min(lams):
            suggested['slope_per_ln_film_ratio'] = _ls_slope([math.log(x) for x in lams],
                                                             [c for _, c in cs])
    joints = [r['friction_joint']['value'] for r in rows
              if r['friction_joint'].get('value') is not None]
    lims = list(IDENT_LIMITATIONS)
    if extra_lims:
        from .halfspace_bite import CREEP_LIMITATION
        lims.append(CREEP_LIMITATION)
    if IDENT_SLIP_NOT_REPRODUCED_FLAG in flags:
        from .foil_bite import LARGE_SLIP_EXPLANATION
        lims.append(LARGE_SLIP_EXPLANATION)
    return {'status': IDENT_STATUS,
            'bite_model': {'mattress': 'experimental_mattress',
                           'half_space': 'reduced_half_space'}.get(perturbed_model, 'hitchcock'),
            'uncertainty_defaults': dict(PASS_RECORD_UNCERTAINTY_DEFAULTS,
                                         basis='[D] analyst choices'),
            'rows': rows, 'summary': summary, 'suggested_contact_friction': suggested,
            'declaration': {'coefficient': _median(joints),
                            'fit_uses_force_torque_slip': all(
                                r['measured']['slip'] is not None
                                and r['measured']['torque'] is not None for r in rows),
                            'calibrated': False, 'source': 'identified from entered pass records'},
            'how_to_use': IDENT_HOW_TO_USE, 'flags': flags, 'limitations': lims}


def _ident_sentence(summary, rows):
    mu = summary['friction_from_force']
    if not mu:
        return ('No friction reproduces the entered force of any record; see the reasons per '
                'record.')
    text = (f'Friction from force: {", ".join(f"{m:.4g}" for m in mu)} (median '
            f'{summary["median"]:.4g}, case value {summary["case_friction_coefficient"]:.4g})')
    if len(mu) > 1:
        text += f', spread {summary["spread"]:.3g}'
    if summary['slope_per_ln_exit_speed'] is not None:
        text += (f'; slope with exit speed {summary["slope_per_ln_exit_speed"]:.3g} per unit '
                 'ln(u)')
    return text + '. Reported only: nothing is applied.'
