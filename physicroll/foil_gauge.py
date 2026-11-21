"""Foil gauge control by speed and entry tension (SPEC19 package 13; gaps C1, BT-G13; I6, X7).

Status ``UNVALIDATED_FOIL_GAUGE_LOOP_ANALYST_CONTROL_LAW``. Opt-in (case section
``foil_gauge_control``), reported beside the gaugemeter section of ``mill_dynamics.py``, which
is unchanged: that section describes gauge control by roll force at an OPEN gap; this one
describes gauge steered by entry tension and speed, the actuators at foil gauge. No
hypothesis reads it (evidence-neutral).

Sensitivities [D, re-derived in SPEC19]. Static force balance of the linearised bite with
two extra inputs,
``dF = F_h*dh + F_hin*dh_in + F_se*ds_e + F_sx*ds_x + F_mu*dmu + F_Y*dY``, against the
structure ``dF = M_eff*(dh - dS) + K_kiss*dh``. ``M_eff``: 0 for a mill run at constant strip
force (``constant_force``), the stand's mill modulus for position control (``position``), or a
supplied number; ``K_kiss`` the stiffness of the roll-to-roll contact outside the strip, an
INPUT (null = 0): the model has no closed-gap load path (roll kiss, Phase 3, gap BT-G2). With
``den = M_eff + K_kiss - F_h``: ``g_X = dh/dX = F_X/den`` for X in (h_in, s_e, s_x, mu, Y) and
``dh/dS = M_eff/den``. Speed: ``dh/du = g_mu*dmu/du + g_Y*Y*m/u`` with ``dmu/du`` the mean slope
of the friction closure's speed curve and ``m`` the strain-rate sensitivity of
``hardening.rate_temperature`` (else the rate term is 0); oil temperature:
``dh/dT_oil = g_mu*dmu/dLambda*Lambda*(-beta)``. These are the sensitivities at constant force
(or position) and constant tension of the OPEN-gap foil bite; nothing here is a closed-gap
result, and ``dh/du`` is only as good as the closure's speed slope, which has not been checked
against a mill.

Loop [D, SPEC19: analyst design; the sources give the structure, no gains or equations]. Exit
gauge -> integral entry-tension trim (fast, limited range) -> speed (slow, acceleration
limited), per unit of gauge error, without limits:
``L(s) = (w_c/s)*1/(1 + s/w_T)*G_gauge(s)*exp(-s*theta)``, ``theta = gauge_distance/u_exit``,
``w_T = 2*pi*tension_loop_bandwidth``, ``G_gauge`` the thickness-gauge transfer of
``band_sensors.gauge_transfer`` (first-order lag; with a described gauge also its spot
average), ``w_c`` entered or ``0.5/(theta + tau_g + 1/w_T)`` (about 60 degrees phase margin).
``S = 1/(1 + L)`` is the gauge error left of a disturbance. Smith predictor (perfect model):
``L0 = L`` without the delay, ``w_c = 0.5/(tau_g + 1/w_T)``, ``S = 1 - T0*exp(-s*theta)``,
``T0 = L0/(1 + L0)``. Margins, the frequency below which ``|S| < 1`` and the peak of ``|S|``
from a scan of 1200 frequencies ``0.01*1.01^i`` rad/s (1 % resolution; crossovers refined by
bisection are reported beside; a crossing below the first scan point is bracketed below it,
down to 1e-9 rad/s, and flagged ``*_below_scan_start``). Time domain (limits make it non-linear): explicit steps
``dt = min(1 ms, theta/40)`` for 20 s; delay as a FIFO; gauge filter and tension loop as
first-order lags; the trim clipped at ``+-limit*entry tension``; while the trim is held at its
limit the speed moves at the entered ramp limit in the direction that relieves it.
"""
import cmath
import math

from . import band_sensors

STATUS = 'UNVALIDATED_FOIL_GAUGE_LOOP_ANALYST_CONTROL_LAW'
GAP_MODES = ('constant_force', 'position', 'supplied_modulus')
REQUIRED = ('gap_mode', 'gauge_distance_m', 'tension_loop_bandwidth_hz',
            'tension_trim_limit_fraction', 'provenance')
OPTIONAL = ('effective_mill_modulus_n_m', 'kiss_stiffness_n_m', 'gauge_time_constant_s',
            'integral_crossover_rad_s', 'smith_predictor', 'speed', 'reels',
            'ripple_pitches_m')
CROSSOVER_RULE_FACTOR = 0.5            # [D, SPEC19 analyst design] w_c*T_total, ~60 degrees
SCAN_START_RAD_S, SCAN_RATIO, SCAN_POINTS = 0.01, 1.01, 1200
BELOW_SCAN_LIMIT_RAD_S = 1e-9         # [D] lowest frequency searched below the scan start
TIME_STEP_MAX_S = 1e-3                 # [D] explicit step, also <= theta/40
DELAY_STEPS_MIN = 40
HORIZON_S = 20.0
TIME_RUN_MAX_STEPS = 200000            # [D, analyst choice] cost cap of one time run (20 s at
                                       # 0.1 ms: a dead time of at least 4 ms; the frequency
                                       # results need no time run and are always given)
SETTLE_WINDOW_S = 5.0
SETTLED_FRACTION = 0.05                # [D, analyst choice] within 5 % of the first value
OSCILLATING_FRACTION = 0.20            # [D, analyst choice] peak-to-peak above 20 %
GAUGE_SET_BY_STRIP_LIMIT = 0.1         # [D, analyst choice] dh/dS below this: strip sets gauge
HISTORY_INTERVAL_S = 0.1
SPEED_STEP_FRACTION = 0.10             # the disturbance row "10 % speed change"

FLAG_SIMULATED = 'FOIL_GAUGE_LOOP_SIMULATED'
FLAG_STRIP_SETS_GAUGE = 'GAUGE_SET_BY_STRIP_NOT_BY_GAP'
FLAG_COIL_AMPLIFIED = 'LOOP_AMPLIFIES_COIL_FREQUENCY'
FLAG_TRIM_SATURATES = 'TENSION_TRIM_SATURATES_FOR_ONE_PERCENT_ENTRY_GAUGE'
FLAG_PLACEHOLDER_SPEED = 'SPEED_EFFECT_FROM_PLACEHOLDER_FRICTION_SLOPE'
FLAG_KISS_ZERO = 'KISS_STIFFNESS_NOT_MODELLED_ZERO_USED'
FLAG_UNSTABLE = 'UNSTABLE_LOOP_SETTINGS'
FLAG_NO_TRIM_RANGE = 'FOIL_GAUGE_NO_TENSION_TRIM_RANGE'
FLAG_TRIM_NOT_ASSESSABLE = 'FOIL_GAUGE_TENSION_TRIM_NOT_ASSESSABLE'
FLAGS = (FLAG_SIMULATED, FLAG_STRIP_SETS_GAUGE, FLAG_COIL_AMPLIFIED, FLAG_TRIM_SATURATES,
         FLAG_PLACEHOLDER_SPEED, FLAG_KISS_ZERO, FLAG_UNSTABLE, FLAG_NO_TRIM_RANGE,
         FLAG_TRIM_NOT_ASSESSABLE)
NO_RANGE_REASON = ('no entry tension to trim: the tension trim cannot compensate for this '
                   'disturbance')
NO_LEVER_REASON = ('the gauge does not respond to entry tension here: the tension trim is not '
                   'assessable for this disturbance')

REGIME_NOTE = (
    'Two regimes, two sections: the gaugemeter section (gauge_control) describes gauge control '
    'by roll force at an open roll gap; this section describes the gauge steered by entry '
    'tension and speed, the actuators at foil gauge. Its sensitivities are those of the '
    'open-gap foil bite at constant force (or position) and constant tension: the model has no '
    'closed-gap load path (roll kiss), and the kiss stiffness is an input (zero when not '
    'given).')
SPEED_WORDS = {
    'placeholder': (
        'The speed effect rests entirely on how friction falls with speed. This slope comes '
        'from the placeholder friction closure, which is not fitted to any mill: read dh/du as '
        'what this closure implies, not as this mill\'s speed effect.'),
    'load_sharing_curve': (
        'The speed effect rests entirely on how friction falls with speed. This slope comes '
        'from the load-sharing closure with the contact friction you entered; its speed slope '
        'has not been checked against a mill: read dh/du as what this closure implies, not as '
        'this mill\'s speed effect.')}
BASIS = {
    'sensitivities': '[D, re-derived in SPEC19] static force balance dF = F_h*dh + F_hin*dh_in '
                     '+ F_se*ds_e + F_sx*ds_x + F_mu*dmu + F_Y*dY = M_eff*(dh - dS) + '
                     'K_kiss*dh; g_X = F_X/(M_eff + K_kiss - F_h)',
    'speed': 'dh/du = g_mu*dmu/du + g_Y*Y*m/u (friction-closure slope; rate term only with '
             'hardening.rate_temperature)',
    'oil_temperature': 'dh/dT_oil = g_mu*dmu/dLambda*Lambda*(-beta) (SPEC19 package 1)',
    'loop': '[D, SPEC19: analyst design] integral entry-tension trim, first-order tension loop, '
            'transport delay, thickness-gauge transfer (band_sensors.gauge_transfer); speed '
            'relieves a trim held at its limit at the ramp limit; crossover rule '
            'w_c = 0.5/(theta + tau_g + 1/w_T) (0.5/(tau_g + 1/w_T) with a Smith predictor)',
    'margins': 'scan of 1200 frequencies 0.01*1.01^i rad/s (1 % resolution); refined values by '
               'bisection beside',
    'status_rules': 'SETTLED: within 5 % of the first value for the last 5 s; OSCILLATING: last '
                    '5 s peak-to-peak above 20 % of the first value; TRIM_SATURATED_*: the trim '
                    'reached its limit (held by speed when the speed brought the error within '
                    '5 %); UNSTABLE_LOOP_SETTINGS: phase margin <= 0 or gain margin <= 1, no '
                    'time run (analyst choices)'}
LIMITATIONS = (
    'No closed-gap load path: the sensitivities are those of the open-gap foil bite at constant '
    'force (or position) and constant tension; the roll-to-roll (kiss) stiffness is an input, '
    'zero when not given (Phase 3, gaps G2 and BT-G2).',
    'The speed sensitivity rests on the friction closure\'s speed slope (the placeholder, or '
    'the load-sharing closure with an entered contact friction); neither slope has been '
    'checked against a mill.',
    'The loop is the tool\'s own structure (integral tension trim, speed relief, optional '
    'Smith predictor with a perfect model), not a vendor\'s controller: no decoupling, no '
    'adaptive or feed-forward scheme; every gain is entered or a stated rule.',
    'Linear sensitivities of one operating point; the tension loop is a first-order lag and '
    'the speed a pure ramp; reels, spans and coil run-out are not modelled here (a tension '
    'ripple is an input).',
    'The sensitivities come from the bite model actually selected; at foil gauge that bite '
    'differs from the published reference loads (benchmarks BT-V1, BT-V2).',
    'Not plant-validated: a software-verified evaluation of an analyst control law.')


# ============================================================================= validation
def _num(where, value, lo, hi, lo_open=False, text=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{where} must be a finite number')
    v = float(value)
    if (v <= lo if lo_open else v < lo) or v > hi:
        rng = text or (f'({lo}, {hi}]' if lo_open else f'[{lo}, {hi}]')
        raise ValueError(f'{where} must be in {rng}')
    return v


def validate(section, thickness_gauge=None):
    """``foil_gauge_control`` (None = not supplied). ``thickness_gauge``: the validated
    ``measurement.thickness_gauge`` or None; when it is described, the loop uses its transfer
    and ``gauge_time_constant_s`` may be left out (given, it must equal the gauge's)."""
    if section is None:
        return None
    w = 'foil_gauge_control'
    if not isinstance(section, dict):
        raise ValueError(f'{w} must be a JSON object or null')
    missing = set(REQUIRED) - set(section)
    unknown = set(section) - set(REQUIRED) - set(OPTIONAL)
    if missing or unknown:
        raise ValueError(f'{w}: missing keys {sorted(missing)}, unknown keys {sorted(unknown)}')
    mode = section['gap_mode']
    if mode not in GAP_MODES:
        raise ValueError(f'{w}.gap_mode must be one of {list(GAP_MODES)}')
    out = {'gap_mode': mode}
    em = section.get('effective_mill_modulus_n_m')
    if mode == 'supplied_modulus':
        if em is None:
            raise ValueError(f'{w}.effective_mill_modulus_n_m is needed with gap_mode '
                             '"supplied_modulus"')
        em = _num(f'{w}.effective_mill_modulus_n_m', em, 0.0, 1e12)
    elif em is not None:
        raise ValueError(f'{w}.effective_mill_modulus_n_m is only used with gap_mode '
                         '"supplied_modulus"')
    out['effective_mill_modulus_n_m'] = em
    k = section.get('kiss_stiffness_n_m')
    out['kiss_stiffness_n_m'] = None if k is None else _num(f'{w}.kiss_stiffness_n_m', k, 0.0,
                                                            1e13)
    out['gauge_distance_m'] = _num(f'{w}.gauge_distance_m', section['gauge_distance_m'], 0.0,
                                   20.0, lo_open=True)
    tg = section.get('gauge_time_constant_s')
    if tg is None:
        if thickness_gauge is None:
            raise ValueError(f'{w}.gauge_time_constant_s is needed (in [0, 1] s) unless '
                             'measurement.thickness_gauge describes the gauge')
    else:
        tg = _num(f'{w}.gauge_time_constant_s', tg, 0.0, 1.0)
        if thickness_gauge is not None and tg != thickness_gauge['time_constant_s']:
            raise ValueError(f'{w}.gauge_time_constant_s ({tg:g} s) differs from '
                             'measurement.thickness_gauge.time_constant_s '
                             f'({thickness_gauge["time_constant_s"]:g} s): give one value')
    out['gauge_time_constant_s'] = tg
    out['tension_loop_bandwidth_hz'] = _num(f'{w}.tension_loop_bandwidth_hz',
                                            section['tension_loop_bandwidth_hz'], 0.0, 100.0,
                                            lo_open=True)
    out['tension_trim_limit_fraction'] = _num(f'{w}.tension_trim_limit_fraction',
                                              section['tension_trim_limit_fraction'], 0.0, 0.5,
                                              lo_open=True)
    wc = section.get('integral_crossover_rad_s')
    out['integral_crossover_rad_s'] = None if wc is None else _num(
        f'{w}.integral_crossover_rad_s', wc, 0.0, 1000.0, lo_open=True)
    sp = section.get('smith_predictor', False)
    if not isinstance(sp, bool):
        raise ValueError(f'{w}.smith_predictor must be true or false')
    out['smith_predictor'] = sp
    speed = section.get('speed')
    if speed is not None:
        if not isinstance(speed, dict) or set(speed) != {'ramp_limit_m_s2'}:
            raise ValueError(f'{w}.speed must be null or {{"ramp_limit_m_s2": ...}}')
        speed = {'ramp_limit_m_s2': _num(f'{w}.speed.ramp_limit_m_s2',
                                         speed['ramp_limit_m_s2'], 0.0, 5.0, lo_open=True)}
    out['speed'] = speed
    out['reels'] = validate_reels(section.get('reels'))
    out['ripple_pitches_m'] = validate_ripple_pitches(section.get('ripple_pitches_m'))
    prov = section['provenance']
    if not isinstance(prov, str) or not prov.strip():
        raise ValueError(f'{w}.provenance must be a nonempty text')
    out['provenance'] = prov
    return out


# ============================================================================= sensitivities
def gauge_sensitivities(forces, mill_modulus_n_m, kiss_stiffness_n_m=0.0):
    """``g_X = F_X/(M_eff + K_kiss - F_h)`` for X in (h_in, s_e, s_x, mu, Y) and
    ``dh/dS = M_eff/den``. ``forces``: ``{'h', 'h_in', 's_e', 's_x', 'mu', 'Y'}`` (N per unit
    of each input; F_h < 0)."""
    m, k = float(mill_modulus_n_m), float(kiss_stiffness_n_m or 0.0)
    if m < 0 or k < 0:
        raise ValueError('mill modulus and kiss stiffness must be >= 0')
    den = m + k - forces['h']
    if not den > 0:
        raise ValueError('M_eff + K_kiss - dF/dh must be > 0 (a bite that stiffens with '
                         'thinner strip has no static gauge solution)')
    out = {f'dh_d{x}': forces[key] / den for x, key in (
        ('entry_thickness', 'h_in'), ('entry_tension_m_per_pa', 's_e'),
        ('exit_tension_m_per_pa', 's_x'), ('friction_m', 'mu'),
        ('flow_stress_m_per_pa', 'Y'))}
    out['dh_dgap'] = m / den
    out['mill_modulus_n_m'] = m
    out['kiss_stiffness_n_m'] = k
    out['strip_modulus_n_m'] = -forces['h']
    return out


def speed_sensitivity(dh_dfriction_m, dmu_du_per_m_s, dh_dflow_stress_m_per_pa=0.0,
                      flow_stress_pa=0.0, rate_sensitivity=None, exit_speed_m_s=1.0):
    """``dh/du = g_mu*dmu/du + g_Y*Y*m/u`` [m per m/s]; the rate term is 0 without ``m``."""
    rate = 0.0 if not rate_sensitivity else (dh_dflow_stress_m_per_pa * flow_stress_pa
                                            * rate_sensitivity / exit_speed_m_s)
    return {'dh_du_m_per_m_s': dh_dfriction_m * dmu_du_per_m_s + rate,
            'friction_term_m_per_m_s': dh_dfriction_m * dmu_du_per_m_s,
            'rate_term_m_per_m_s': rate}


# ============================================================================= loop
class Loop:
    """The analyst loop of the module docstring (frequency domain)."""

    def __init__(self, gauge_distance_m, exit_speed_m_s, gauge_time_constant_s,
                 tension_loop_bandwidth_hz, integral_crossover_rad_s=None, smith_predictor=False,
                 spot_length_m=0.0):
        self.theta = gauge_distance_m / exit_speed_m_s
        self.u = exit_speed_m_s
        self.tau = gauge_time_constant_s
        self.w_t = 2 * math.pi * tension_loop_bandwidth_hz
        self.smith = bool(smith_predictor)
        self.spot = spot_length_m or 0.0
        if integral_crossover_rad_s is None:
            total = self.tau + 1 / self.w_t + (0.0 if self.smith else self.theta)
            self.w_c, self.w_c_source = CROSSOVER_RULE_FACTOR / total, 'rule'
        else:
            self.w_c, self.w_c_source = integral_crossover_rad_s, 'entered'

    def plant(self, w):
        """Tension loop times gauge transfer (no delay) at ``w`` rad/s."""
        return (1 / complex(1.0, w / self.w_t)
                * band_sensors.gauge_transfer(self.spot, self.tau, w / (2 * math.pi), self.u))

    def open_loop(self, w):
        """``L(jw)``; with the Smith predictor the delay-free design loop ``L0``."""
        lo = self.w_c / (1j * w) * self.plant(w)
        return lo if self.smith else lo * cmath.exp(-1j * w * self.theta)

    def sensitivity(self, w):
        """``S(jw)``: gauge error left of a disturbance at ``w`` rad/s."""
        if self.smith:
            l0 = self.w_c / (1j * w) * self.plant(w)
            return 1 - l0 / (1 + l0) * cmath.exp(-1j * w * self.theta)
        return 1 / (1 + self.open_loop(w))

    def phase_deg(self, w):
        """Unwrapped phase of ``open_loop`` [deg]."""
        x = math.pi * self.spot * w / (2 * math.pi) / self.u
        spot = -180.0 * math.floor(x / math.pi) if x > 0 else 0.0
        return (-90.0 - math.degrees(math.atan(w / self.w_t) + math.atan(w * self.tau))
                - (0.0 if self.smith else math.degrees(w * self.theta)) + spot)


def _bisect(f, a, b, n=80):
    fa = f(a)
    for _ in range(n):
        m = 0.5 * (a + b)
        if (f(m) > 0) == (fa > 0):
            a, fa = m, f(m)
        else:
            b = m
    return 0.5 * (a + b)


def scan_frequencies():
    return [SCAN_START_RAD_S * SCAN_RATIO ** i for i in range(SCAN_POINTS)]


def _below_scan(f, start=None):
    """Bracket a sign change of ``f`` below the scan: ``f(start) < 0``; step down by decades
    to ``BELOW_SCAN_LIMIT_RAD_S`` until ``f >= 0``, then refine by bisection. None if no
    change within the bound."""
    hi = SCAN_START_RAD_S if start is None else start
    lo = hi
    while lo > BELOW_SCAN_LIMIT_RAD_S:
        lo = max(hi / 10.0, BELOW_SCAN_LIMIT_RAD_S)
        if f(lo) >= 0:
            return _bisect(f, lo, hi)
        hi = lo
    return None


def analyse_loop(loop):
    """Margins, attenuation band and peak of ``|S|`` (scan, refined values beside). A crossing
    that lies below the first scan point (a slow loop) is bracketed below the scan
    (``_below_scan``) and its refined value reported in both the scan and the refined keys,
    with ``*_below_scan_start`` true; a crossing not found within the bound is None and the
    loop's stability is then None (not assessed), not False."""
    ws = scan_frequencies()
    mags = [abs(loop.open_loop(w)) for w in ws]
    out = {'dead_time_s': loop.theta, 'crossover_rad_s': loop.w_c,
           'crossover_hz': loop.w_c / (2 * math.pi), 'crossover_source': loop.w_c_source,
           'smith_predictor': loop.smith, 'tension_loop_rad_s': loop.w_t,
           'gauge_time_constant_s': loop.tau, 'gauge_spot_length_m': loop.spot}
    ig = next((i for i, m in enumerate(mags) if m < 1), None)
    g_below = ig == 0
    if ig is None:
        pm = wg = pm_ref = wg_ref = None
    elif g_below:     # |L| < 1 already at the first scan point: the crossover is below it
        wg = wg_ref = _below_scan(lambda w: abs(loop.open_loop(w)) - 1)
        pm = pm_ref = None if wg is None else 180 + loop.phase_deg(wg)
    else:
        wg = ws[ig]
        pm = 180 + loop.phase_deg(wg)
        wg_ref = _bisect(lambda w: abs(loop.open_loop(w)) - 1, ws[ig - 1], ws[ig])
        pm_ref = 180 + loop.phase_deg(wg_ref)
    ip = next((i for i, w in enumerate(ws) if loop.phase_deg(w) < -180), None)
    p_below = ip == 0
    if ip is None:
        gm = wp = gm_ref = wp_ref = None
    elif p_below:     # phase below -180 already at the first scan point
        wp = wp_ref = _below_scan(lambda w: loop.phase_deg(w) + 180)
        gm = gm_ref = None if wp is None else 1 / abs(loop.open_loop(wp))
    else:
        wp = ws[ip]
        gm = 1 / abs(loop.open_loop(wp))
        wp_ref = _bisect(lambda w: loop.phase_deg(w) + 180, ws[ip - 1], ws[ip])
        gm_ref = 1 / abs(loop.open_loop(wp_ref))
    s_mag = [abs(loop.sensitivity(w)) for w in ws]
    ia = next((i for i, s in enumerate(s_mag) if s > 1), None)
    a_below = ia == 0
    if ia is None:
        att = att_ref = None
    elif a_below:     # |S| > 1 already at the first scan point: the band edge is below it
        wa = _below_scan(lambda w: 1 - abs(loop.sensitivity(w)))
        att = att_ref = None if wa is None else wa / (2 * math.pi)
    else:
        att = ws[ia] / (2 * math.pi)
        att_ref = _bisect(lambda w: abs(loop.sensitivity(w)) - 1, ws[ia - 1],
                          ws[ia]) / (2 * math.pi)
    peak_ws, peak_s = ws, s_mag
    if g_below or p_below or a_below:
        # the peak of |S| may lie below the scan too: extend the scan down (same ratio) to a
        # decade below the lowest crossing found
        low = min([x for x in (wg, wp, None if att is None else att * 2 * math.pi)
                   if x is not None] or [SCAN_START_RAD_S]) / 10.0
        n_low = max(0, int(math.ceil(math.log(SCAN_START_RAD_S / low) / math.log(SCAN_RATIO))))
        extra = [SCAN_START_RAD_S * SCAN_RATIO ** -i for i in range(n_low, 0, -1)]
        peak_ws = extra + ws
        peak_s = [abs(loop.sensitivity(w)) for w in extra] + s_mag
    k = max(range(len(peak_ws)), key=lambda i: peak_s[i])
    if pm is None:
        stable = None      # the gain crossover was not found: stability not assessed
    else:
        stable = pm > 0 and (gm is None or gm > 1)
    out.update({
        'phase_margin_deg': pm, 'gain_crossover_rad_s': wg,
        'gain_margin': gm, 'phase_crossover_rad_s': wp,
        'attenuates_below_hz': att, 'peak_sensitivity': peak_s[k],
        'peak_sensitivity_hz': peak_ws[k] / (2 * math.pi),
        'refined': {'phase_margin_deg': pm_ref, 'gain_crossover_rad_s': wg_ref,
                    'gain_margin': gm_ref, 'phase_crossover_rad_s': wp_ref,
                    'attenuates_below_hz': att_ref},
        'stable': stable,
        'instability_frequency_hz': None if stable or wg is None else wg / (2 * math.pi),
        'crossover_below_scan_start': g_below,
        'phase_crossover_below_scan_start': p_below,
        'attenuation_edge_below_scan_start': a_below})
    return out


def sensitivity_row(loop, name, frequency_hz):
    s = loop.sensitivity(2 * math.pi * frequency_hz)
    return {'name': name, 'frequency_hz': frequency_hz, 'magnitude': abs(s),
            'phase_deg': math.degrees(cmath.phase(s)), 'amplifies': abs(s) > 1}


def tension_ripple_gauge(loop, dh_dentry_tension_m_per_pa, amplitude_pa, frequency_hz,
                         exit_thickness_m):
    """Gauge ripple from an entered entry-tension ripple (the reel dynamics that generate it
    are SPEC19 package 14): open loop ``|g_se|*A``, closed loop times ``|S|``."""
    s = abs(loop.sensitivity(2 * math.pi * frequency_hz))
    op = abs(dh_dentry_tension_m_per_pa) * amplitude_pa
    return {'tension_ripple_pa': amplitude_pa, 'frequency_hz': frequency_hz,
            'gauge_ripple_open_loop_m': op, 'gauge_ripple_closed_loop_m': op * s,
            'gauge_ripple_open_loop_fraction': op / exit_thickness_m,
            'gauge_ripple_closed_loop_fraction': op * s / exit_thickness_m,
            'sensitivity_magnitude': s}


# ============================================================================= time domain
def simulate(loop, dh_dentry_tension_m_per_pa, disturbance, *, horizon_s=HORIZON_S,
             trim_limit_pa=None, dh_du_m_per_m_s=None, ramp_limit_m_s2=None, history=True):
    """Explicit time run of the loop. ``disturbance(t)``: open-loop exit gauge deviation [m].
    Returns the gauge deviation history and the run status (module docstring)."""
    g = dh_dentry_tension_m_per_pa
    if g == 0:
        raise ValueError('dh/d(entry tension) is zero: the tension trim cannot act')
    dt = min(TIME_STEP_MAX_S, loop.theta / DELAY_STEPS_MIN)
    n = int(round(horizon_s / dt))
    nd = max(1, int(round(loop.theta / dt)))
    nh = int(round(loop.spot / loop.u / dt / 2))            # half window of the spot average
    nh = min(nh, nd)
    size = nd + nh + 1
    buf_y, buf_m = [0.0] * size, [0.0] * size
    yf = mf = mdf = trim = act = du = 0.0
    ys, trims, dus, ts = [], [], [], []
    saturated = speed_moved = False
    every = max(1, int(round(HISTORY_INTERVAL_S / dt)))
    for k in range(n):
        t = k * dt
        model = g * act + (dh_du_m_per_m_s or 0.0) * du
        y = disturbance(t) + model
        buf_y.append(y)
        buf_y.pop(0)
        buf_m.append(model)
        buf_m.pop(0)
        # spot average centred on the delayed sample (index nh from the oldest)
        seg = buf_y[:2 * nh + 1] if nh else [buf_y[0]]
        ym = sum(seg) / len(seg)
        a = 0.0 if loop.tau == 0 else dt / loop.tau
        if loop.tau == 0:
            yf = ym
        else:
            yf += min(1.0, a) * (ym - yf)
        e = yf
        if loop.smith:   # perfect model: add the undelayed model output, remove the delayed one
            segm = buf_m[:2 * nh + 1] if nh else [buf_m[0]]
            md = sum(segm) / len(segm)
            if loop.tau == 0:
                mf, mdf = model, md
            else:
                mf += min(1.0, a) * (model - mf)
                mdf += min(1.0, a) * (md - mdf)
            e = yf + mf - mdf
        trim += dt * (-loop.w_c / g) * e
        if trim_limit_pa is not None and abs(trim) >= trim_limit_pa:
            trim = math.copysign(trim_limit_pa, trim)
            saturated = True
            if ramp_limit_m_s2 and dh_du_m_per_m_s:
                du -= math.copysign(1.0, e) * math.copysign(1.0, dh_du_m_per_m_s) \
                    * ramp_limit_m_s2 * dt
                speed_moved = True
        act += min(1.0, dt * loop.w_t) * (trim - act)
        ys.append(y)
        if history and k % every == 0:
            ts.append(t)
            trims.append(trim)
            dus.append(du)
    first = abs(ys[0]) if ys[0] != 0 else max(abs(v) for v in ys) or 1.0
    win = ys[-int(round(SETTLE_WINDOW_S / dt)):]
    within = max(abs(v) for v in win) <= SETTLED_FRACTION * first
    ptp = max(win) - min(win)
    at_limit = trim_limit_pa is not None and abs(trim) >= trim_limit_pa
    if saturated and speed_moved and within:
        status = 'TRIM_SATURATED_HELD_BY_SPEED'
    elif saturated and (at_limit or not within):
        status = 'TRIM_SATURATED_ERROR_REMAINS'
    elif within:
        status = 'SETTLED'
    elif ptp > OSCILLATING_FRACTION * first:
        status = 'OSCILLATING'
    else:
        status = 'NOT_SETTLED_WITHIN_HORIZON'
    settle = None
    for k in range(len(ys) - 1, -1, -1):
        if abs(ys[k]) > SETTLED_FRACTION * first:
            settle = (k + 1) * dt if k + 1 < len(ys) else None
            break
    else:
        settle = 0.0
    sign = 1.0 if ys[0] >= 0 else -1.0
    over = max(0.0, max(-sign * v for v in ys) / first)
    out = {'status': status, 'time_step_s': dt, 'horizon_s': horizon_s,
           'first_deviation_m': ys[0], 'final_deviation_m': ys[-1],
           'settling_time_s': settle, 'overshoot_fraction': over,
           'trim_reached_limit': saturated, 'final_trim_pa': trim, 'final_speed_change_m_s': du,
           'last_window_peak_to_peak_m': ptp}
    if history:
        out['history'] = {'time_s': ts, 'gauge_deviation_m': ys[::every][:len(ts)],
                          'trim_pa': trims, 'speed_change_m_s': dus}
    out['_series'] = ys
    return out


def time_run_steps(loop, horizon_s=HORIZON_S):
    """Steps of one time run of ``simulate`` (its step ``min(1 ms, theta/40)``)."""
    return int(round(horizon_s / min(TIME_STEP_MAX_S, loop.theta / DELAY_STEPS_MIN)))


def _clean(run):
    run = dict(run)
    run.pop('_series', None)
    return run


# ============================================================================= section
def _percent_block(g, h0, h1, mu, y_pa):
    return {'entry_tension_percent_per_mpa': g['dh_dentry_tension_m_per_pa'] * 1e6 / h1 * 100,
            'exit_tension_percent_per_mpa': g['dh_dexit_tension_m_per_pa'] * 1e6 / h1 * 100,
            'friction_percent_per_percent': g['dh_dfriction_m'] * 0.01 * mu / h1 * 100,
            'flow_stress_percent_per_percent': g['dh_dflow_stress_m_per_pa'] * 0.01 * y_pa
            / h1 * 100,
            'entry_thickness_percent_per_percent': g['dh_dentry_thickness'] * h0 / h1}


def foil_gauge_section(case, fgc, bite, forces, *, stand_mill_modulus_n_m, friction_closure,
                       friction_curve=None, oil=None, rate_sensitivity=None, roll_freqs=None,
                       chatter_onset_hz=None, thickness_gauge=None, closed_gap_range_m=None,
                       sensitivity_bite_model=None, sensitivity_basis=None, bite_model=None,
                       chain_passes=None):
    """``result['foil_gauge_control']``. ``forces``: ``{'h', 'h_in', 's_e', 's_x', 'mu',
    'Y'}`` of the operating bite (N per unit input, whole width); ``friction_closure``:
    ``'placeholder'``, ``'load_sharing_curve'`` or None (no tribology); ``friction_curve``:
    ``process.friction_speed_curve``; ``oil``: the friction-per-kelvin block
    (``band_width._friction_placeholder``) or None."""
    p = case['pass']
    h0, h1, u = p['entry_thickness_m'], p['exit_thickness_m'], p['exit_speed_m_s']
    mu, y_pa = p['friction_coefficient'], p['mean_flow_stress_pa']
    se = p['entry_tension_pa']
    flags = []
    kiss = fgc['kiss_stiffness_n_m']
    moduli = {'constant_force': 0.0, 'position': stand_mill_modulus_n_m}
    if fgc['gap_mode'] == 'supplied_modulus':
        moduli['supplied_modulus'] = fgc['effective_mill_modulus_n_m']
    by_mode = {}
    for mode, m in moduli.items():
        g = gauge_sensitivities(forces, m, kiss)
        g['percent'] = _percent_block(g, h0, h1, mu, y_pa)
        by_mode[mode] = g
    sel = by_mode[fgc['gap_mode']]
    if sel['dh_dgap'] < GAUGE_SET_BY_STRIP_LIMIT:
        flags.append(FLAG_STRIP_SETS_GAUGE)
    if kiss is None and closed_gap_range_m is not None and h1 < closed_gap_range_m[1]:
        flags.append(FLAG_KISS_ZERO)
    # speed and oil temperature
    speed = {'friction_closure': friction_closure}
    slope = None if not isinstance(friction_curve, dict) else friction_curve.get(
        'mean_slope_per_m_s')
    if friction_closure is None or slope is None:
        speed.update({'dh_du_m_per_m_s': None, 'percent_per_m_s': None,
                      'reason': 'needs tribology (the friction closure\'s speed curve)'})
    else:
        sp = speed_sensitivity(sel['dh_dfriction_m'], slope, sel['dh_dflow_stress_m_per_pa'],
                               y_pa, rate_sensitivity, u)
        speed.update(sp)
        speed.update({'friction_slope_per_m_s': slope,
                      'friction_slope_speeds_m_s': friction_curve.get('mean_slope_speeds_m_s'),
                      'rate_sensitivity': rate_sensitivity,
                      'percent_per_m_s': sp['dh_du_m_per_m_s'] / h1 * 100,
                      'closure_flags': list(friction_curve.get('flags') or []),
                      'words': SPEED_WORDS.get(friction_closure, SPEED_WORDS['placeholder'])})
        if friction_closure == 'placeholder':
            flags.append(FLAG_PLACEHOLDER_SPEED)
    dh_du = speed.get('dh_du_m_per_m_s')
    if isinstance(oil, dict) and oil.get('friction_change_per_kelvin_oil') is not None:
        d_t = sel['dh_dfriction_m'] * oil['friction_change_per_kelvin_oil']
        oil_block = {'dmu_dT_oil_per_k': oil['friction_change_per_kelvin_oil'],
                     'dh_dT_oil_m_per_k': d_t, 'percent_per_k': d_t / h1 * 100,
                     'closure_flags': list(oil.get('flags') or [])}
    else:
        oil_block = {'dh_dT_oil_m_per_k': None,
                     'reason': 'needs tribology and the operating film ratio'}
    # loop
    spot = 0.0 if thickness_gauge is None else thickness_gauge['spot_length_m']
    tau = (thickness_gauge['time_constant_s'] if fgc['gauge_time_constant_s'] is None
           else fgc['gauge_time_constant_s'])
    loop = Loop(fgc['gauge_distance_m'], u, tau, fgc['tension_loop_bandwidth_hz'],
                fgc['integral_crossover_rad_s'], fgc['smith_predictor'], spot)
    lp = analyse_loop(loop)
    lp['gauge_transfer_source'] = ('measurement.thickness_gauge (spot and lag)'
                                   if thickness_gauge is not None else
                                   'foil_gauge_control.gauge_time_constant_s (lag only)')
    rows = []
    u_e = u * h1 / h0
    for name in sorted(roll_freqs or {}):
        rows.append(sensitivity_row(loop, name, roll_freqs[name]))
    coil_rows = []
    k = case.get('kinematics') or {}
    for name, d, speed_ in (('entry_coil_1x', k.get('entry_coil_diameter_m'), u_e),
                            ('exit_coil_1x', k.get('exit_coil_diameter_m'), u)):
        if d:
            r = sensitivity_row(loop, name, speed_ / (math.pi * d))
            r['coil_diameter_m'] = d
            rows.append(r)
            coil_rows.append(r)
    if chatter_onset_hz:
        rows.append(sensitivity_row(loop, 'chatter_onset', chatter_onset_hz))
    lp['sensitivity_at'] = rows
    if any(r['amplifies'] for r in coil_rows):
        flags.append(FLAG_COIL_AMPLIFIED)
    if lp['stable'] is False:
        flags.append(FLAG_UNSTABLE)
    # disturbances
    g_se = sel['dh_dentry_tension_m_per_pa']
    limit_pa = fgc['tension_trim_limit_fraction'] * se
    no_range = limit_pa == 0          # zero entry tension (or a zero trim fraction)
    no_lever = g_se == 0              # the entry tension does not move the gauge
    dist = [('entry_thickness_1_percent', sel['dh_dentry_thickness'] * 0.01 * h0),
            ('flow_stress_1_percent', sel['dh_dflow_stress_m_per_pa'] * 0.01 * y_pa),
            ('friction_1_percent', sel['dh_dfriction_m'] * 0.01 * mu),
            ('oil_temperature_1_k', oil_block.get('dh_dT_oil_m_per_k')),
            ('speed_10_percent', None if dh_du is None else dh_du * SPEED_STEP_FRACTION * u)]
    drows = []
    for name, dh in dist:
        if dh is None:
            drows.append({'disturbance': name, 'open_loop_gauge_change_m': None,
                          'reason': 'needs tribology'})
            continue
        row = {'disturbance': name, 'open_loop_gauge_change_m': dh,
               'open_loop_gauge_change_fraction': dh / h1,
               'speed_change_to_replace_m_s': (None if not dh_du else -dh / dh_du)}
        if no_lever:
            row.update({'trim_needed_pa': None, 'trim_share_of_limit': None,
                        'trim_saturates': None, 'reason': NO_LEVER_REASON})
        else:
            trim = -dh / g_se
            row.update({'trim_needed_pa': trim,
                        'trim_share_of_limit': None if no_range else abs(trim) / limit_pa,
                        'trim_saturates': abs(trim) > limit_pa})
            if no_range:
                row['reason'] = NO_RANGE_REASON
        drows.append(row)
    if drows[0]['trim_saturates']:
        flags.append(FLAG_TRIM_SATURATES)
    if no_range and not no_lever:
        flags.append(FLAG_NO_TRIM_RANGE)
    if no_lever:
        flags.append(FLAG_TRIM_NOT_ASSESSABLE)
    # time runs for the entry-gauge row
    d0 = dist[0][1]
    if lp['stable'] and no_lever:
        step = {'status': 'NOT_ASSESSABLE', 'not_run': True,
                'reason': 'the gauge does not respond to entry tension here (dh/d(entry '
                          'tension) is zero): the tension trim cannot act; no time run'}
    elif lp['stable'] and time_run_steps(loop) > TIME_RUN_MAX_STEPS:
        step = {'status': 'TIME_RUN_NOT_MADE_TOO_MANY_STEPS', 'not_run': True,
                'reason': f'the dead time {loop.theta:.3g} s needs time steps of '
                          f'{loop.theta / DELAY_STEPS_MIN:.3g} s, {time_run_steps(loop)} steps '
                          f'for {HORIZON_S:g} s, more than the {TIME_RUN_MAX_STEPS} the time run '
                          'is allowed; the frequency-domain results above are complete; no '
                          'time run'}
    elif lp['stable']:
        lin = simulate(loop, g_se, lambda t: d0, history=False)
        lim = simulate(loop, g_se, lambda t: d0, trim_limit_pa=limit_pa,
                       dh_du_m_per_m_s=dh_du,
                       ramp_limit_m_s2=(fgc['speed'] or {}).get('ramp_limit_m_s2'))
        step = {'disturbance': 'entry_thickness_1_percent', 'linear_no_limits': _clean(lin),
                'with_limits': _clean(lim), 'status': lim['status']}
        if no_range:
            step['note'] = ('no entry tension to trim: the run with limits holds the trim at '
                            'zero, so only speed (if a ramp limit is given) acts')
        flags.insert(0, FLAG_SIMULATED)
    elif lp['stable'] is None:
        step = {'status': 'GAIN_CROSSOVER_NOT_FOUND', 'not_run': True,
                'reason': 'the gain crossover was not found between '
                          f'{BELOW_SCAN_LIMIT_RAD_S:g} and {scan_frequencies()[-1]:.4g} rad/s: '
                          'the phase margin and the stability of the loop are not assessed; '
                          'no time run'}
    else:
        step = {'status': FLAG_UNSTABLE, 'not_run': True,
                'reason': f'the loop settings are unstable (phase margin '
                          f'{lp["phase_margin_deg"]}, gain margin {lp["gain_margin"]}); '
                          'instability at about '
                          f'{lp["instability_frequency_hz"]} Hz; no time run'}
    # package 14: reels and run-out; pass chaining
    if fgc['reels'] is None:
        reels = {'status': 'NOT_SUPPLIED', 'not_supplied': True,
                 'reason': 'foil_gauge_control.reels is null or absent'}
    else:
        sp_ = case['spans']
        reels = reel_section(fgc['reels'], bite, g_se, sel['dh_dexit_tension_m_per_pa'], loop,
                             exit_speed_m_s=u, width_m=p['width_m'],
                             modulus_pa=sp_['strip_youngs_modulus_pa'],
                             entry_span_m=sp_['entry_span_length_m'],
                             exit_span_m=sp_['exit_span_length_m'])
        flags += [f for f in reels['flags'] if f not in flags]
    chain = _pass_chain(case, fgc, chain_passes, sel, loop, by_mode, moduli, kiss)
    flags += [f for f in chain.get('flags') or [] if f not in flags]
    return {'status': STATUS, 'not_supplied': False, 'inputs': dict(fgc),
            'reels': reels, 'pass_chain': chain,
            'regime': REGIME_NOTE,
            'bite_model': bite_model, 'sensitivity_bite_model': sensitivity_bite_model,
            'sensitivity_basis': sensitivity_basis, 'bite_flags': list(bite.flags),
            'friction_closure': friction_closure,
            'gap_mode': fgc['gap_mode'], 'sensitivities': sel,
            'sensitivities_by_gap_mode': by_mode,
            'speed': speed, 'oil_temperature': oil_block,
            'loop': lp, 'disturbances': drows, 'trim_limit_pa': limit_pa,
            'step_response': step,
            'foil_regime_note': (
                'At foil gauge the roll force no longer sets the gauge in closed-gap rolling; '
                'these are the sensitivities at constant force and constant tension of the '
                'open-gap foil bite (no closed-gap load path in the model; the kiss stiffness '
                f'{"entered" if kiss is not None else "is zero: not given"}).'),
            'basis': dict(BASIS), 'flags': flags, 'limitations': list(LIMITATIONS)}


# ============================================================================= reels (package 14)
# [D, re-derived in SPEC19 package 14] Entry side (the exit side with its own signs and the
# exit quantities):
#   s_e' = (E/L_e)*(du_e - R*dw - v_d)            span as a spring between bite and reel
#   du_e = k_e*s_e, k_e = u_e*((f_se + f_h*g_se)/(1 + f) + g_se/h1)  (< 0: the bite gives way)
#   J*dw' = A*R*s_e - dM                          reel; A = width*h0; J = reel_inertia_kg_m2
#   v_d = w_rev*e_c*sin(w_rev*t), w_rev = u_e/R   run-out e_c of the coil radius
# Exit side: s_x' = (E/L_x)*(R*dw - du_x - v_d), du_x = k_x*s_x, k_x = V_r*(f_sx + f_h*g_sx),
# V_r = u_x/(1 + f), J*dw' = -A*R*s_x + dM, A = width*h1. Both give
#   s(jw)/v_d = -(E/L)/(jw + lam_b + (E/L)*A*R^2/(J*jw)),  lam_b = -(E/L)*k_e or (E/L)*k_x
#   w_n = sqrt((E*A/L)*R^2/J), damping ratio lam_b/(2*w_n)
# Regulator 'none' (dM = 0) or 'direct': the response times s/(s + w_b) [D: the simplest form
# of "cannot attenuate above its bandwidth"]. Gauge ripple = |g_s|*|s|*|S(j*w_rev)|.
REEL_KEYS = ('coil_radius_m', 'core_radius_m', 'motor_inertia_kg_m2', 'runout_m', 'regulator')
REEL_OPTIONAL = ('gear_ratio', 'regulator_bandwidth_hz')
REGULATORS = ('none', 'direct')
STRIP_DENSITY_DEFAULT_KG_M3 = 2700.0   # [M] aluminium
RADIUS_SWEEP_POINTS = 8
RESONANCE_FREQUENCY_BAND = 0.10        # [D, analyst choice] within 10 % of each other
RESONANCE_DAMPING_LIMIT = 0.5          # [D, analyst choice] and lightly damped
STAND_RESONANCE_BAND = 0.10            # [D, analyst choice] chain frequency near a resonance
FLAG_REEL = 'REEL_RUNOUT_RIPPLE_COMPUTED'
FLAG_RESONANCE = 'COIL_ON_SPAN_RESONANCE_CROSSED_DURING_COIL'
FLAG_GROWS = 'RELATIVE_RIPPLE_GROWS_FROM_PASS_TO_PASS'
FLAG_NEAR_STAND = 'ENTRY_RIPPLE_NEAR_STAND_RESONANCE'
FLAG_NEAR_LOOP = 'ENTRY_RIPPLE_NEAR_TENSION_LOOP_PEAK'
REEL_FLAGS = (FLAG_REEL, FLAG_RESONANCE, FLAG_GROWS, FLAG_NEAR_STAND, FLAG_NEAR_LOOP)
FLAGS = FLAGS + REEL_FLAGS
BAND_CONNECTION = (
    'A tension ripple the regulator cannot remove writes a gauge mark locked to the coil: one '
    'mark per coil revolution, at an exit pitch that changes with the coil diameter (shorter '
    'as an entry coil unwinds, longer as the exit coil builds). That is how it is recognised on '
    'the mill. The coil-locked hypothesis keeps its own rules; this is what the model expects '
    'beside them, and nothing here enters the tally.')
REEL_LIMITATIONS = (
    'The regulator is the tool\'s own ideal filter (none, or a high-pass with the entered '
    'bandwidth), not the plant\'s tension control; reel friction, binding, ovality harmonics '
    'and motor torque limits are not modelled.',
    'Linear span spring with the bite as a damper (its slip and gauge response to tension); '
    'the existing chatter model, its spans and state matrix are unchanged and do not read '
    'this.',
    'Pass chaining: the loop settings of the case pass are used for every pass (dead time from '
    'each pass\'s speed); a coil is assumed to pass whole from one pass to the next (no '
    'trimming, splicing or phase tracking: amplitudes only); the pitch stretches by entry '
    'over exit gauge; the gauge sensor\'s own transfer is not applied to the chain.',
    '`incoming_variation` and the coil-locked evidence are unchanged; no ripple amplitude '
    'enters any evidence item.')


def validate_reels(reels):
    if reels is None:
        return None
    w = 'foil_gauge_control.reels'
    if not isinstance(reels, dict):
        raise ValueError(f'{w} must be a JSON object or null')
    unknown = set(reels) - {'entry', 'exit', 'strip_density_kg_m3'}
    if unknown:
        raise ValueError(f'{w}: unknown keys {sorted(unknown)}')
    rho = reels.get('strip_density_kg_m3', STRIP_DENSITY_DEFAULT_KG_M3)
    out = {'strip_density_kg_m3': _num(f'{w}.strip_density_kg_m3', rho, 1000.0, 20000.0)}
    for side in ('entry', 'exit'):
        r = reels.get(side)
        if r is None:
            out[side] = None
            continue
        ws = f'{w}.{side}'
        if not isinstance(r, dict):
            raise ValueError(f'{ws} must be a JSON object or null')
        missing = set(REEL_KEYS) - set(r)
        unknown = set(r) - set(REEL_KEYS) - set(REEL_OPTIONAL)
        if missing or unknown:
            raise ValueError(f'{ws}: missing keys {sorted(missing)}, unknown keys '
                             f'{sorted(unknown)}')
        core = _num(f'{ws}.core_radius_m', r['core_radius_m'], 0.0, 2.0, lo_open=True)
        radius = _num(f'{ws}.coil_radius_m', r['coil_radius_m'], 0.0, 3.0, lo_open=True)
        if radius < core:
            raise ValueError(f'{ws}.coil_radius_m must be at least core_radius_m')
        reg = r['regulator']
        if reg not in REGULATORS:
            raise ValueError(f'{ws}.regulator must be "none" or "direct"')
        bw_hz = r.get('regulator_bandwidth_hz')
        if reg == 'direct':
            if bw_hz is None:
                raise ValueError(f'{ws}.regulator_bandwidth_hz is needed with regulator '
                                 '"direct"')
            bw_hz = _num(f'{ws}.regulator_bandwidth_hz', bw_hz, 0.0, 100.0, lo_open=True)
        elif bw_hz is not None:
            raise ValueError(f'{ws}.regulator_bandwidth_hz is only used with regulator '
                             '"direct"')
        out[side] = {'coil_radius_m': radius, 'core_radius_m': core,
                     'motor_inertia_kg_m2': _num(f'{ws}.motor_inertia_kg_m2',
                                                 r['motor_inertia_kg_m2'], 0.0, 1e5,
                                                 lo_open=True),
                     'gear_ratio': _num(f'{ws}.gear_ratio', r.get('gear_ratio', 1.0), 0.0,
                                        100.0, lo_open=True),
                     'runout_m': _num(f'{ws}.runout_m', r['runout_m'], 0.0, 0.01),
                     'regulator': reg, 'regulator_bandwidth_hz': bw_hz}
    return out


def validate_ripple_pitches(pitches):
    if pitches is None:
        return None
    w = 'foil_gauge_control.ripple_pitches_m'
    if not isinstance(pitches, list) or not 1 <= len(pitches) <= 6:
        raise ValueError(f'{w} must be null or a list of 1 to 6 pitches')
    return [_num(f'{w}[{i}]', p, 0.0, 20.0, lo_open=True) for i, p in enumerate(pitches)]


def reel_inertia_kg_m2(motor_inertia_kg_m2, strip_density_kg_m3, width_m, coil_radius_m,
                       core_radius_m, gear_ratio=1.0):
    """``mill_dynamics.reel_inertia_kg_m2`` (one formula; a bare core is allowed here)."""
    from . import mill_dynamics as md
    if coil_radius_m == core_radius_m:
        return motor_inertia_kg_m2
    return md.reel_inertia_kg_m2(motor_inertia_kg_m2, strip_density_kg_m3, width_m,
                                 coil_radius_m, core_radius_m, gear_ratio)


def bite_speed_response(side, bite, g_s, exit_speed_m_s):
    """``k_e`` (entry) or ``k_x`` (exit): strip speed change at the bite per Pa of tension."""
    h0, h1, f = bite.entry_thickness_m, bite.exit_thickness_m, bite.forward_slip_fraction
    fh = bite.dslip_dexit_thickness_per_m
    if side == 'entry':
        u_e = exit_speed_m_s * h1 / h0
        return u_e * ((bite.dslip_dentry_tension_per_pa + fh * g_s) / (1 + f) + g_s / h1)
    return exit_speed_m_s / (1 + f) * (bite.dslip_dexit_tension_per_pa + fh * g_s)


def span_tension_response(frequency_rad_s, *, modulus_pa, span_length_m, area_m2, radius_m,
                          inertia_kg_m2, leak_rate_per_s, regulator='none',
                          regulator_bandwidth_hz=None):
    """``s(jw)/v_d`` [Pa per m/s] of the module comment (``inertia_kg_m2`` None: held reel)."""
    w = frequency_rad_s
    c = modulus_pa / span_length_m
    reel = 0.0 if inertia_kg_m2 is None else c * area_m2 * radius_m ** 2 / (inertia_kg_m2 * 1j * w)
    resp = -c / (1j * w + leak_rate_per_s + reel)
    if regulator == 'direct':
        wb = 2 * math.pi * regulator_bandwidth_hz
        resp *= 1j * w / (1j * w + wb)
    return resp


def reel_side(side, reel, bite, g_s, loop, *, exit_speed_m_s, width_m, modulus_pa,
              span_length_m, strip_density_kg_m3, radius_m=None):
    """One reel at one coil radius (the entered one when ``radius_m`` is None)."""
    h0, h1 = bite.entry_thickness_m, bite.exit_thickness_m
    r = reel['coil_radius_m'] if radius_m is None else radius_m
    area = width_m * (h0 if side == 'entry' else h1)
    speed = exit_speed_m_s * h1 / h0 if side == 'entry' else exit_speed_m_s
    j = reel_inertia_kg_m2(reel['motor_inertia_kg_m2'], strip_density_kg_m3, width_m, r,
                           reel['core_radius_m'], reel['gear_ratio'])
    k = bite_speed_response(side, bite, g_s, exit_speed_m_s)
    c = modulus_pa / span_length_m
    lam = -c * k if side == 'entry' else c * k
    w_rev = speed / r
    w_n = math.sqrt(c * area * r * r / j)
    kw = dict(modulus_pa=modulus_pa, span_length_m=span_length_m, area_m2=area, radius_m=r,
              leak_rate_per_s=lam, regulator=reel['regulator'],
              regulator_bandwidth_hz=reel['regulator_bandwidth_hz'])
    v_d = w_rev * reel['runout_m']
    s_amp = abs(span_tension_response(w_rev, inertia_kg_m2=j, **kw)) * v_d
    s_held = abs(span_tension_response(w_rev, inertia_kg_m2=None, **kw)) * v_d
    sens = abs(loop.sensitivity(w_rev))
    open_ = abs(g_s) * s_amp
    pitch = 2 * math.pi * r * (h0 / h1 if side == 'entry' else 1.0)
    return {'side': side, 'coil_radius_m': r, 'reel_inertia_kg_m2': j,
            'bite_speed_response_m_s_per_pa': k, 'bite_leak_rate_per_s': lam,
            'once_per_revolution_hz': w_rev / (2 * math.pi), 'coil_on_span_hz':
            w_n / (2 * math.pi), 'damping_ratio': lam / (2 * w_n),
            'runout_speed_m_s': v_d, 'tension_ripple_pa': s_amp,
            'tension_ripple_reel_speed_held_pa': s_held,
            'gauge_ripple_open_loop_m': open_, 'gauge_ripple_closed_loop_m': open_ * sens,
            'gauge_ripple_closed_loop_fraction': open_ * sens / h1,
            'loop_sensitivity_magnitude': sens, 'exit_strip_pitch_m': pitch}


def reel_section(reels, bite, g_se, g_sx, loop, *, exit_speed_m_s, width_m, modulus_pa,
                 entry_span_m, exit_span_m):
    out, flags = {}, []
    for side, g, span in (('entry', g_se, entry_span_m), ('exit', g_sx, exit_span_m)):
        reel = reels[side]
        if reel is None:
            out[side] = None
            continue
        kw = dict(exit_speed_m_s=exit_speed_m_s, width_m=width_m, modulus_pa=modulus_pa,
                  span_length_m=span, strip_density_kg_m3=reels['strip_density_kg_m3'])
        row = reel_side(side, reel, bite, g, loop, **kw)
        n = RADIUS_SWEEP_POINTS
        rs = [reel['coil_radius_m'] + (reel['core_radius_m'] - reel['coil_radius_m']) * i
              / (n - 1) for i in range(n - 1)] + [reel['core_radius_m']]
        sweep = [reel_side(side, reel, bite, g, loop, radius_m=r, **kw) for r in rs]
        for a in sweep:
            a['resonance_crossing'] = (abs(a['once_per_revolution_hz'] / a['coil_on_span_hz']
                                           - 1) <= RESONANCE_FREQUENCY_BAND
                                       and a['damping_ratio'] < RESONANCE_DAMPING_LIMIT)
        for a, b in zip(sweep, sweep[1:]):     # a crossing between two sweep radii
            if ((a['once_per_revolution_hz'] - a['coil_on_span_hz'])
                    * (b['once_per_revolution_hz'] - b['coil_on_span_hz']) < 0
                    and min(a['damping_ratio'], b['damping_ratio']) < RESONANCE_DAMPING_LIMIT):
                a['resonance_crossing'] = b['resonance_crossing'] = True
        row['radius_sweep'] = sweep
        row['regulator'] = reel['regulator']
        row['regulator_bandwidth_hz'] = reel['regulator_bandwidth_hz']
        row['regulator_label'] = 'the tool\'s own ideal regulator, not the plant\'s'
        if any(a['resonance_crossing'] for a in sweep):
            flags.append(FLAG_RESONANCE)
        out[side] = row
    flags.insert(0, FLAG_REEL)
    out.update({'status': 'COMPUTED', 'not_supplied': False, 'band_connection': BAND_CONNECTION,
                'basis': '[D, re-derived in SPEC19 package 14] span spring between bite and '
                         'reel, bite as a damper, reel inertia from mill_dynamics; regulator '
                         '[D: ideal high-pass]', 'flags': flags,
                'limitations': list(REEL_LIMITATIONS)})
    return out


def chain_rows(passes, pitch_m, sensitivity_of):
    """C8: a thickness ripple of ``pitch_m`` on the entry strip of the first pass through the
    passes in order. ``passes``: dicts ``label, entry_thickness_m, exit_thickness_m,
    exit_speed_m_s, g_hin`` (None: no bite, ends the chain with ``reason``),
    ``onset_frequency_hz``, ``loop_peak_hz``; ``sensitivity_of(pass, w)`` gives ``S(jw)``."""
    rows, p, cum, cum_rel = [], pitch_m, 1.0, 1.0
    for ps in passes:
        if ps.get('g_hin') is None:
            rows.append({'label': ps['label'], 'ends_chain': True,
                         'reason': ps.get('reason') or 'no bite for this pass'})
            break
        h0, h1 = ps['entry_thickness_m'], ps['exit_thickness_m']
        f = ps['exit_speed_m_s'] * h1 / h0 / p
        s = abs(sensitivity_of(ps, 2 * math.pi * f))
        ratio = abs(ps['g_hin']) * s
        rel = ratio * h0 / h1
        cum *= ratio
        cum_rel *= rel
        on = ps.get('onset_frequency_hz')
        near_stand = bool(on) and abs(f / on - 1) <= STAND_RESONANCE_BAND
        lp = ps.get('loop_peak_hz')
        near_loop = bool(lp) and abs(f / lp - 1) <= STAND_RESONANCE_BAND
        rows.append({'label': ps['label'], 'entry_pitch_m': p, 'exit_pitch_m': p * h0 / h1,
                     'frequency_hz': f, 'entry_speed_m_s': ps['exit_speed_m_s'] * h1 / h0,
                     'exit_speed_m_s': ps['exit_speed_m_s'], 'g_hin': abs(ps['g_hin']),
                     'sensitivity_magnitude': s, 'amplitude_ratio': ratio,
                     'cumulative_ratio': cum, 'relative_ripple_ratio': rel,
                     'cumulative_relative_ratio': cum_rel,
                     'near_stand_resonance': near_stand, 'near_tension_loop_peak': near_loop,
                     'onset_frequency_hz': on})
        p *= h0 / h1
    return rows


def _pass_chain(case, fgc, chain_passes, sel, loop, by_mode, moduli, kiss):
    """C8 for the schedule rows: consecutive rows (each starting at the previous row's exit
    gauge) from the first; ripples of the first pass's entry-coil circumference and of the
    entered pitches."""
    if not chain_passes:
        return {'status': 'NOT_SUPPLIED', 'not_supplied': True,
                'reason': 'no schedule (pass chaining needs the schedule rows)'}
    pitches, sources = [], []
    reels = fgc['reels'] or {}
    k = case.get('kinematics') or {}
    if reels.get('entry') is not None:
        pitches.append(2 * math.pi * reels['entry']['coil_radius_m'])
        sources.append('entry coil circumference (foil_gauge_control.reels.entry)')
    elif k.get('entry_coil_diameter_m'):
        pitches.append(math.pi * k['entry_coil_diameter_m'])
        sources.append('entry coil circumference (kinematics.entry_coil_diameter_m)')
    for x in fgc['ripple_pitches_m'] or []:
        pitches.append(x)
        sources.append('foil_gauge_control.ripple_pitches_m')
    if not pitches:
        return {'status': 'NOT_SUPPLIED', 'not_supplied': True,
                'reason': 'no pitch: give foil_gauge_control.ripple_pitches_m or an entry coil'}
    passes, prev = [], None
    for cp in chain_passes:
        if prev is not None and abs(cp['entry_thickness_m'] / prev - 1) > 1e-9:
            break                          # not the next pass of this route
        row = dict(cp)
        if cp.get('bite') is not None:
            try:
                f = {'h': cp['bite'].dforce_dexit_thickness_n_m,
                     'h_in': cp['bite'].dforce_dentry_thickness_n_m,
                     's_e': 0.0, 's_x': 0.0, 'mu': 0.0, 'Y': 0.0}
                row['g_hin'] = gauge_sensitivities(f, moduli[fgc['gap_mode']], kiss)[
                    'dh_dentry_thickness']
                lp = Loop(fgc['gauge_distance_m'], cp['exit_speed_m_s'], loop.tau,
                          fgc['tension_loop_bandwidth_hz'], loop.w_c, loop.smith, loop.spot)
                row['loop'] = lp
                row['loop_peak_hz'] = analyse_loop(lp)['peak_sensitivity_hz']
            except ValueError as exc:
                row['g_hin'], row['reason'] = None, str(exc)
        else:
            row['g_hin'] = None
        passes.append(row)
        prev = cp['exit_thickness_m']
    chains, flags, meetings = [], [], []
    for pitch, src in zip(pitches, sources):
        rows = chain_rows(passes, pitch, lambda ps, w: ps['loop'].sensitivity(w))
        for r in rows:
            for key, flag, what in (('near_stand_resonance', FLAG_NEAR_STAND,
                                     'stand (chatter onset)'),
                                    ('near_tension_loop_peak', FLAG_NEAR_LOOP,
                                     'tension-loop peak')):
                if r.get(key):
                    if flag not in flags:
                        flags.append(flag)
                    meetings.append({'pitch_m': pitch, 'pass': r['label'],
                                     'exit_speed_m_s': r['exit_speed_m_s'],
                                     'frequency_hz': r['frequency_hz'], 'resonance': what})
        if any(r.get('cumulative_relative_ratio', 0) > 1 for r in rows) and FLAG_GROWS not in flags:
            flags.append(FLAG_GROWS)
        chains.append({'first_entry_pitch_m': pitch, 'pitch_source': src, 'rows': rows})
    return {'status': 'COMPUTED', 'not_supplied': False,
            'passes_chained': [ps['label'] for ps in passes],
            'route_rule': ('schedule rows in order from the first, each starting at the '
                           'previous row\'s exit gauge; the chain ends at a row without a '
                           'bite or at the first row that does not continue the route'),
            'length_tracking': ('the whole coil passes from one pass to the next (no '
                                'trimming or splicing); the pitch stretches by entry over exit '
                                'gauge; amplitudes only, phases not tracked'),
            'loop_settings': ('the case pass\'s loop settings and crossover for every pass; '
                              'the dead time follows each pass\'s exit speed'),
            'chains': chains, 'resonance_meetings': meetings, 'flags': flags}
