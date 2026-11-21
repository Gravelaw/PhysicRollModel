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
bisection are reported beside). Time domain (limits make it non-linear): explicit steps
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
TIME_STEP_MAX_S = 1e-3                 # [D] explicit step, also <= theta/40
DELAY_STEPS_MIN = 40
HORIZON_S = 20.0
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
FLAGS = (FLAG_SIMULATED, FLAG_STRIP_SETS_GAUGE, FLAG_COIL_AMPLIFIED, FLAG_TRIM_SATURATES,
         FLAG_PLACEHOLDER_SPEED, FLAG_KISS_ZERO, FLAG_UNSTABLE)

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
    for key in ('reels', 'ripple_pitches_m'):
        if section.get(key) is not None:
            raise ValueError(f'{w}.{key} is not built yet (SPEC19 package 14): leave it null')
        out[key] = None
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


def analyse_loop(loop):
    """Margins, attenuation band and peak of ``|S|`` (scan, refined values beside)."""
    ws = scan_frequencies()
    mags = [abs(loop.open_loop(w)) for w in ws]
    out = {'dead_time_s': loop.theta, 'crossover_rad_s': loop.w_c,
           'crossover_hz': loop.w_c / (2 * math.pi), 'crossover_source': loop.w_c_source,
           'smith_predictor': loop.smith, 'tension_loop_rad_s': loop.w_t,
           'gauge_time_constant_s': loop.tau, 'gauge_spot_length_m': loop.spot}
    ig = next((i for i, m in enumerate(mags) if m < 1), None)
    if ig is None or ig == 0:
        pm = wg = pm_ref = wg_ref = None
    else:
        wg = ws[ig]
        pm = 180 + loop.phase_deg(wg)
        wg_ref = _bisect(lambda w: abs(loop.open_loop(w)) - 1, ws[ig - 1], ws[ig])
        pm_ref = 180 + loop.phase_deg(wg_ref)
    ip = next((i for i, w in enumerate(ws) if loop.phase_deg(w) < -180), None)
    if ip is None or ip == 0:
        gm = wp = gm_ref = wp_ref = None
    else:
        wp = ws[ip]
        gm = 1 / abs(loop.open_loop(wp))
        wp_ref = _bisect(lambda w: loop.phase_deg(w) + 180, ws[ip - 1], ws[ip])
        gm_ref = 1 / abs(loop.open_loop(wp_ref))
    s_mag = [abs(loop.sensitivity(w)) for w in ws]
    ia = next((i for i, s in enumerate(s_mag) if s > 1), None)
    att = None if ia is None else ws[ia] / (2 * math.pi)
    att_ref = None if ia is None or ia == 0 else _bisect(
        lambda w: abs(loop.sensitivity(w)) - 1, ws[ia - 1], ws[ia]) / (2 * math.pi)
    k = max(range(len(ws)), key=lambda i: s_mag[i])
    stable = (pm is not None and pm > 0) and (gm is None or gm > 1)
    out.update({
        'phase_margin_deg': pm, 'gain_crossover_rad_s': wg,
        'gain_margin': gm, 'phase_crossover_rad_s': wp,
        'attenuates_below_hz': att, 'peak_sensitivity': s_mag[k],
        'peak_sensitivity_hz': ws[k] / (2 * math.pi),
        'refined': {'phase_margin_deg': pm_ref, 'gain_crossover_rad_s': wg_ref,
                    'gain_margin': gm_ref, 'phase_crossover_rad_s': wp_ref,
                    'attenuates_below_hz': att_ref},
        'stable': stable,
        'instability_frequency_hz': None if stable or wg is None else wg / (2 * math.pi)})
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
                       sensitivity_bite_model=None, sensitivity_basis=None, bite_model=None):
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
    if not lp['stable']:
        flags.append(FLAG_UNSTABLE)
    # disturbances
    g_se = sel['dh_dentry_tension_m_per_pa']
    limit_pa = fgc['tension_trim_limit_fraction'] * se
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
        trim = -dh / g_se
        drows.append({'disturbance': name, 'open_loop_gauge_change_m': dh,
                      'open_loop_gauge_change_fraction': dh / h1,
                      'trim_needed_pa': trim, 'trim_share_of_limit': abs(trim) / limit_pa,
                      'trim_saturates': abs(trim) > limit_pa,
                      'speed_change_to_replace_m_s': (None if not dh_du else -dh / dh_du)})
    if drows[0]['trim_saturates']:
        flags.append(FLAG_TRIM_SATURATES)
    # time runs for the entry-gauge row
    d0 = dist[0][1]
    if lp['stable']:
        lin = simulate(loop, g_se, lambda t: d0, history=False)
        lim = simulate(loop, g_se, lambda t: d0, trim_limit_pa=limit_pa,
                       dh_du_m_per_m_s=dh_du,
                       ramp_limit_m_s2=(fgc['speed'] or {}).get('ramp_limit_m_s2'))
        step = {'disturbance': 'entry_thickness_1_percent', 'linear_no_limits': _clean(lin),
                'with_limits': _clean(lim), 'status': lim['status']}
        flags.insert(0, FLAG_SIMULATED)
    else:
        step = {'status': FLAG_UNSTABLE, 'not_run': True,
                'reason': f'the loop settings are unstable (phase margin '
                          f'{lp["phase_margin_deg"]}, gain margin {lp["gain_margin"]}); '
                          'instability at about '
                          f'{lp["instability_frequency_hz"]} Hz; no time run'}
    return {'status': STATUS, 'not_supplied': False, 'inputs': dict(fgc),
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
