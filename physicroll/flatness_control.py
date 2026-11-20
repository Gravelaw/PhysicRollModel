"""Flatness control loop parts: low-order basis, influence matrix, gain, zone controller, loop
(SPEC19 package 3; gap row G5 core).

Status ``UNVALIDATED_FLATNESS_LOOP_SIMULATION_ANALYST_CONTROL_LAW``. Standard library only;
JSON-safe results. This module imports no ``band_*`` module: the plant (a thermal run and a
reading operator) is passed in as callables (package 4 wires them).

**What the sources give.** The reports describe the STRUCTURE of a flatness controller in words
only [SS-S34 EX, SS-S33 EX, SS-S31 EX]: least squares on actuator influence vectors (bending,
tilt, one column per spray zone), dead bands, valve minimum on / off times, a target curve. No
control law is printed. The law below is therefore a stated, simple one
[D, SPEC19: analyst design]: it is what this tool simulates, NOT what any vendor system or the
plant's controller does.

**Low-order part** [D, SPEC19]: polynomials ``1, x, x^2, ...`` in the zone centre mapped to
``[-1, 1]`` over the covered zones, orthonormalised by weighted Gram-Schmidt;
``residual = e - sum_k c_k*b_k``, ``c_k = sum_j w_j*e_j*b_kj``. Order 2 removes mean, tilt and
parabola "as if by ideal bending and tilt" (Phase 3 models those actuators); the coefficients
are reported, never controlled.

**Influence matrix** [D, SPEC19]: column ``k`` = change of the steady zone readings per unit
INCREASE of the level of control zone ``k``, by a one-sided difference
``B[:, k] = (r(u - step*e_k) - r(u))/(-step)`` at the base levels ``u`` (upward when
``u_k - step < 0``). More cooling makes the roll smaller, the strip thicker, the fibre tight:
the diagonal is negative.

**Gain** ``G = (B^T W B + lam*I)^-1 B^T W``, ``W = diag(weights)``,
``lam = regularisation_fraction*max_k (B^T W B)_kk`` (Gaussian elimination, partial pivoting).

**Control law** (``ZoneController``; per control zone: demand ``u*``, valve level, time of its
last change):

1. ``e_j = r_j - target_j`` (zones with weight 0 are left out);
2. with supplied actuators: weighted least squares of ``e`` on their influence vectors, settings
   clipped to their limits, their fitted part subtracted (instant response; the interface for
   the bender and tilt of Phase 3, which are NOT modelled here);
3. ``rho = remove_low_order(e)``;
4. ``d = G*rho``;
5. dead band: ``d_k = 0`` when ``|d_k|*b_k <= dead_band``, ``b_k = max_j |B_jk|``;
6. ``u*_k <- clip(u*_k - integral_gain*d_k, lowest level, highest level)``;
7. the allowed valve level nearest to ``u*_k`` (ties: the lower) replaces the present level only
   if it is closer by more than ``hysteresis_fraction`` of the gap between the two levels AND the
   valve has held its level for ``minimum_on_time_s`` (reached by going up) or
   ``minimum_off_time_s`` (by going down). The initial level counts as reached at the start of
   the loop (going up when it is above the lowest level, else down).

Analyst constants [D, SPEC19: analyst choice]: ``integral_gain`` 0.1, ``hysteresis_fraction``
0.1, ``regularisation_fraction`` 0.01. The loop (``run_loop``) uses a fixed control interval
and horizon, no adaptive step and no wall-clock limit; a loop that does not settle is a result
(status ``NOT_SETTLED``), never an error. It cannot run away numerically: the demand is clipped
and the dwell times bound the valve changes by ``horizon/min(dwell)`` per zone.
"""
import json
import math

STATUS = 'UNVALIDATED_FLATNESS_LOOP_SIMULATION_ANALYST_CONTROL_LAW'
LOOP_STATUSES = ('SETTLED', 'TRIMMING_WITHIN_BAND', 'NOT_SETTLED')
TRIM_BAND_FACTOR = 3.0                 # [D, SPEC19] trimming within 3 x the dead band
DEFAULT_INTEGRAL_GAIN = 0.1            # [D, SPEC19: analyst choice]
DEFAULT_HYSTERESIS_FRACTION = 0.1      # [D, SPEC19: analyst choice]
DEFAULT_REGULARISATION_FRACTION = 0.01  # [D, SPEC19: analyst choice]
VALVE_LOG_MAX = 500
HISTORY_MAX_POINTS = 300               # as band_width.HISTORY_MAX_POINTS (SPEC19 G''4)
FLAG_INCREASES = 'CONTROL_INCREASES_RESIDUAL'
FLAG_AT_LIMIT = 'CONTROL_ZONE_AT_LIMIT'
LAW_LABEL = ("the tool's own control law [D, SPEC19: analyst design]: integral least squares "
             'on the spray-zone influence vectors with a dead band, valve dwell times and '
             "hysteresis; not a vendor's algorithm and not what the plant's controller does")
BASIS = {'control_law': LAW_LABEL,
         'structure': 'least squares on actuator influence vectors, dead bands, valve minimum '
                      'on / off times, target curve [SS-S34 EX, SS-S33 EX, SS-S31 EX]; no law '
                      'is given in the reports',
         'integral_gain': f'{DEFAULT_INTEGRAL_GAIN} [D, SPEC19: analyst choice] unless entered',
         'hysteresis_fraction': f'{DEFAULT_HYSTERESIS_FRACTION} [D, SPEC19: analyst choice] '
                                'unless entered',
         'regularisation_fraction': f'{DEFAULT_REGULARISATION_FRACTION} [D, SPEC19: analyst '
                                    'choice] unless entered',
         'low_order': 'the low-order part (order 2: mean, tilt, parabola) is removed as if by '
                      'ideal bending and tilt, which this tool does not model',
         'trim_band_factor': f'{TRIM_BAND_FACTOR} x the dead band [D, SPEC19]'}


def _finite(name, v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f'{name} must be a finite number')
    return float(v)


def _checked(d):
    json.dumps(d, allow_nan=False)
    return d


# ============================================================================= linear algebra
def _solve(a, b):
    """Solve A x = b (b a list of right-hand-side columns as rows: b[i][c]) by Gaussian
    elimination with partial pivoting. Returns x[i][c]."""
    n = len(a)
    m = [list(map(float, a[i])) + list(map(float, b[i])) for i in range(n)]
    nc = len(b[0]) if b else 0
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-300:
            raise ValueError('singular matrix in the gain (add regularisation)')
        m[col], m[piv] = m[piv], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            if f:
                m[r] = [x - f * y for x, y in zip(m[r], m[col])]
    x = [[0.0] * nc for _ in range(n)]
    for i in range(n - 1, -1, -1):
        for c in range(nc):
            acc = m[i][n + c] - sum(m[i][k] * x[k][c] for k in range(i + 1, n))
            x[i][c] = acc / m[i][i]
    return x


# ============================================================================= low order
def low_order_basis(zone_centres_m, weights, order):
    """Weighted-orthonormal polynomial vectors of order 0..``order`` (-1: empty) over the zones
    (centres mapped to [-1, 1] over the zones with weight > 0)."""
    if isinstance(order, bool) or not isinstance(order, int) or not -1 <= order <= 4:
        raise ValueError('order must be an int in [-1, 4]')
    x = [_finite('zone_centres_m', v) for v in zone_centres_m]
    w = [_finite('weights', v) for v in weights]
    if len(x) != len(w):
        raise ValueError('zone_centres_m and weights need the same length')
    if order < 0:
        return []
    cov = [xi for xi, wi in zip(x, w) if wi > 0]
    if not cov:
        return []
    lo, hi = min(cov), max(cov)
    span = hi - lo
    u = [0.0 if span == 0 else 2 * (xi - lo) / span - 1 for xi in x]
    basis = []
    for k in range(order + 1):
        v = [ui ** k for ui in u]
        for _ in range(2):
            for b in basis:
                c = sum(wi * vi * bi for wi, vi, bi in zip(w, v, b))
                v = [vi - c * bi for vi, bi in zip(v, b)]
        norm = math.sqrt(sum(wi * vi * vi for wi, vi in zip(w, v)))
        if norm <= 1e-10 * math.sqrt(sum(w)):
            continue
        basis.append([vi / norm for vi in v])
    return basis


def remove_low_order(values, basis, weights):
    """(residual, coefficients): ``residual = e - sum_k c_k*b_k``, ``c_k = sum_j w_j*e_j*b_kj``;
    ``None`` readings stay ``None`` and count as zero with zero weight."""
    e = [0.0 if v is None else float(v) for v in values]
    w = [0.0 if v is None else float(wi) for v, wi in zip(values, weights)]
    coef = [sum(wi * ei * bi for wi, ei, bi in zip(w, e, b)) for b in basis]
    res = list(e)
    for c, b in zip(coef, basis):
        res = [r - c * bi for r, bi in zip(res, b)]
    return [None if v is None else r for v, r in zip(values, res)], coef


# ============================================================================= influence, gain
def influence_matrix(readings_at, base_levels, groups, *, step=0.2):
    """``B[j][k]``: change of the steady zone reading ``j`` per unit INCREASE of the level of
    control zone ``k`` (``groups[k]``, a list of nozzle indices), one-sided difference of size
    ``step`` downward (upward when the base level is below ``step``). ``readings_at(levels)``
    takes one level per control zone and returns the zone readings (``None`` = no strip)."""
    u = [_finite('base_levels', v) for v in base_levels]
    if len(u) != len(groups):
        raise ValueError('base_levels needs one level per control zone')
    st = _finite('step', step)
    if not 0 < st <= 1:
        raise ValueError('step must be in (0, 1]')
    r0 = [0.0 if v is None else v for v in readings_at(list(u))]
    cols = []
    for k in range(len(u)):
        h = -st if u[k] - st >= 0 else st
        lv = list(u)
        lv[k] = u[k] + h
        r = [0.0 if v is None else v for v in readings_at(lv)]
        cols.append([(a - b) / h for a, b in zip(r, r0)])
    return [[cols[k][j] for k in range(len(u))] for j in range(len(r0))]


def regularised_gain(influence, weights, regularisation_fraction=DEFAULT_REGULARISATION_FRACTION):
    """``G = (B^T W B + lam*I)^-1 B^T W``, ``lam = fraction*max_k (B^T W B)_kk``; returns
    ``G[k][j]`` (control zones x reading zones)."""
    b = [[_finite('influence', v) for v in row] for row in influence]
    w = [_finite('weights', v) for v in weights]
    if len(b) != len(w):
        raise ValueError('influence needs one row per reading zone')
    frac = _finite('regularisation_fraction', regularisation_fraction)
    if frac < 0:
        raise ValueError('regularisation_fraction must be >= 0')
    nk = len(b[0]) if b else 0
    btw = [[b[j][k] * w[j] for j in range(len(b))] for k in range(nk)]
    m = [[sum(btw[k][j] * b[j][l] for j in range(len(b))) for l in range(nk)]
         for k in range(nk)]
    lam = frac * max((m[k][k] for k in range(nk)), default=0.0)
    for k in range(nk):
        m[k][k] += lam
    return _solve(m, btw)


def fit_supplied_actuators(error, actuators, weights):
    """Weighted least squares of ``error`` on the supplied actuator influence vectors
    (``{'name', 'influence_i_units_per_unit', 'minimum', 'maximum'}``), settings clipped to
    their limits; returns (remaining error, settings)."""
    if not actuators:
        return list(error), []
    e = [0.0 if v is None else float(v) for v in error]
    w = [0.0 if v is None else float(wi) for v, wi in zip(error, weights)]
    cols = [[_finite('influence_i_units_per_unit', v) for v in a['influence_i_units_per_unit']]
            for a in actuators]
    for c in cols:
        if len(c) != len(e):
            raise ValueError('a supplied actuator needs one influence value per zone')
    n = len(cols)
    m = [[sum(wi * ci * di for wi, ci, di in zip(w, cols[a], cols[b])) for b in range(n)]
         for a in range(n)]
    rhs = [[sum(wi * ci * ei for wi, ci, ei in zip(w, cols[a], e))] for a in range(n)]
    lam = 1e-12 * max((m[a][a] for a in range(n)), default=0.0)
    for a in range(n):
        m[a][a] += lam
    s = [x[0] for x in _solve(m, rhs)]
    out = []
    for a, act in enumerate(actuators):
        v = min(max(s[a], act['minimum']), act['maximum'])
        out.append({'name': act['name'], 'setting': v, 'unclipped': s[a]})
    rem = list(e)
    for a, act in enumerate(out):
        rem = [r - act['setting'] * c for r, c in zip(rem, cols[a])]
    return [None if v is None else r for v, r in zip(error, rem)], out


# ============================================================================= controller
class ZoneController:
    """The analyst control law of the module docstring. ``step(time_s, readings)`` returns the
    valve level of every control zone after this control step."""

    def __init__(self, influence, weights, groups, valve_levels, initial_level,
                 minimum_on_time_s, minimum_off_time_s, dead_band_i_units, *,
                 integral_gain=DEFAULT_INTEGRAL_GAIN, low_order=2, targets=None,
                 supplied_actuators=None, hysteresis_fraction=DEFAULT_HYSTERESIS_FRACTION,
                 regularisation_fraction=DEFAULT_REGULARISATION_FRACTION,
                 zone_centres_m=None, start_time_s=0.0):
        self.b = [[_finite('influence', v) for v in row] for row in influence]
        self.w = [_finite('weights', v) for v in weights]
        self.groups = [list(g) for g in groups]
        nk = len(self.groups)
        if len(self.b) != len(self.w) or any(len(r) != nk for r in self.b):
            raise ValueError('influence must have one row per zone and one column per control '
                             'zone')
        lv = sorted({_finite('valve_levels', v) for v in valve_levels})
        if len(lv) < 2 or lv[0] < 0 or lv[-1] > 1:
            raise ValueError('valve_levels needs at least two levels in [0, 1]')
        self.levels_allowed = lv
        self.lo, self.hi = lv[0], lv[-1]
        init = _finite('initial_level', initial_level)
        self.min_on = _finite('minimum_on_time_s', minimum_on_time_s)
        self.min_off = _finite('minimum_off_time_s', minimum_off_time_s)
        self.dead_band = _finite('dead_band_i_units', dead_band_i_units)
        self.gain_i = _finite('integral_gain', integral_gain)
        self.hyst = _finite('hysteresis_fraction', hysteresis_fraction)
        if min(self.min_on, self.min_off, self.dead_band, self.gain_i, self.hyst) < 0:
            raise ValueError('dwell times, dead band, gain and hysteresis must be >= 0')
        self.targets = ([0.0] * len(self.w) if targets is None
                        else [_finite('targets', v) for v in targets])
        self.actuators = list(supplied_actuators or [])
        nz = len(self.w)
        centres = zone_centres_m if zone_centres_m is not None else list(range(nz))
        self.basis = low_order_basis(centres, self.w, low_order)
        self.low_order = low_order
        self.gain = regularised_gain(self.b, self.w, regularisation_fraction)
        self.b_max = [max(abs(self.b[j][k]) for j in range(nz)) for k in range(nk)]
        self.demand = [min(max(init, self.lo), self.hi)] * nk
        start = self._nearest(self.demand[0])
        self.valve = [start] * nk
        self.changed_at = [float(start_time_s)] * nk
        self.went_up = [start > self.lo] * nk
        self.last = None
        self.parameters = {'integral_gain': self.gain_i, 'hysteresis_fraction': self.hyst,
                           'regularisation_fraction': regularisation_fraction,
                           'dead_band_i_units': self.dead_band, 'minimum_on_time_s': self.min_on,
                           'minimum_off_time_s': self.min_off, 'valve_levels': lv,
                           'initial_level': init, 'low_order': low_order}

    def _nearest(self, u):
        return min(self.levels_allowed, key=lambda v: (abs(v - u), v))

    def error_terms(self, readings):
        """(error, residual after the actuators and low order, low-order coefficients,
        actuator settings) of a set of readings."""
        e = [None if (r is None or wi <= 0) else r - t
             for r, t, wi in zip(readings, self.targets, self.w)]
        e, acts = fit_supplied_actuators(e, self.actuators, self.w)
        rho, coef = remove_low_order(e, self.basis, self.w)
        return e, rho, coef, acts

    def step(self, time_s, readings):
        if len(readings) != len(self.w):
            raise ValueError('readings need one value per zone')
        e, rho, coef, acts = self.error_terms(readings)
        r = [0.0 if v is None else v for v in rho]
        d = [sum(g * x for g, x in zip(row, r)) for row in self.gain]
        for k in range(len(d)):
            if abs(d[k]) * self.b_max[k] <= self.dead_band:
                d[k] = 0.0
            self.demand[k] = min(max(self.demand[k] - self.gain_i * d[k], self.lo), self.hi)
            cand = self._nearest(self.demand[k])
            cur = self.valve[k]
            if cand == cur:
                continue
            gain = abs(cur - self.demand[k]) - abs(cand - self.demand[k])
            if gain <= self.hyst * abs(cand - cur):
                continue
            dwell = self.min_on if self.went_up[k] else self.min_off
            if time_s - self.changed_at[k] < dwell - 1e-9:
                continue
            self.went_up[k] = cand > cur
            self.valve[k] = cand
            self.changed_at[k] = time_s
        self.last = {'error': e, 'residual': rho, 'low_order_coefficients': coef,
                     'actuators': acts, 'correction': d}
        return list(self.valve)


# ============================================================================= loop
def _max_abs(values):
    vals = [abs(v) for v in values if v is not None]
    return max(vals) if vals else 0.0


def run_loop(advance, readings_of, controller, *, horizon_s, control_interval_s, time_step_s,
             settle_window_s=300.0, delay_intervals=0, display_time_constant_s=0.0):
    """Closed loop with a fixed control interval over a fixed horizon. ``advance(levels,
    duration_s, time_step_s)`` returns a plant state, ``readings_of(state)`` the zone readings.
    Every control interval: advance with the present valve levels; read; transport delay (a
    FIFO of ``delay_intervals`` readings) and display filter ``y += dt/(tau + dt)*(x - y)``;
    ``controller.step``; log. ``initial`` is the first reading the controller sees."""
    horizon = _finite('horizon_s', horizon_s)
    dt_c = _finite('control_interval_s', control_interval_s)
    window = _finite('settle_window_s', settle_window_s)
    tau = _finite('display_time_constant_s', display_time_constant_s)
    if dt_c <= 0 or window <= 0 or tau < 0:
        raise ValueError('control interval and settle window must be > 0, the filter >= 0')
    if horizon < 2 * window:
        raise ValueError('horizon_s must be at least twice settle_window_s')
    if isinstance(delay_intervals, bool) or not isinstance(delay_intervals, int) \
            or delay_intervals < 0:
        raise ValueError('delay_intervals must be an int >= 0')
    n = max(1, int(round(horizon / dt_c)))
    fifo, shown = [], None
    log, changes = [], 0
    hist = []
    init = None
    last_change = None
    steps_to_last = None
    t = 0.0
    for i in range(1, n + 1):
        levels = list(controller.valve)
        nozzle = advance(levels, dt_c, time_step_s)
        t = i * dt_c
        x = readings_of(nozzle)
        fifo.append(list(x))
        if len(fifo) > delay_intervals + 1:
            fifo.pop(0)
        seen = fifo[0]              # delay_intervals old once the FIFO is full
        if shown is None or tau == 0:
            shown = list(seen)
        else:
            a = dt_c / (tau + dt_c)
            shown = [None if (s is None or y is None) else y + a * (s - y)
                     for y, s in zip(shown, seen)]
        before = list(controller.valve)
        after = controller.step(t, shown)
        res = controller.last['residual']
        if init is None:
            init = {'readings_i_units': list(shown), 'residual_i_units': list(res),
                    'max_abs_residual_i_units': _max_abs(res),
                    'max_abs_reading_i_units': _max_abs(shown),
                    'low_order_coefficients': list(controller.last['low_order_coefficients']),
                    'levels': before, 'demand': list(controller.demand)}
        for k, (a_, b_) in enumerate(zip(before, after)):
            if a_ != b_:
                changes += 1
                last_change, steps_to_last = t, i
                if len(log) < VALVE_LOG_MAX:
                    log.append({'time_s': t, 'control_zone': k, 'from_level': a_,
                                'to_level': b_})
        hist.append((t, _max_abs(res), _max_abs(shown), sum(a_ != b_ for a_, b_ in
                                                              zip(before, after))))
    final = {'readings_i_units': list(shown), 'residual_i_units': list(res),
             'max_abs_residual_i_units': _max_abs(res),
             'max_abs_reading_i_units': _max_abs(shown),
             'low_order_coefficients': list(controller.last['low_order_coefficients']),
             'levels': list(controller.valve), 'demand': list(controller.demand)}
    win = [h for h in hist if h[0] > t - window + 1e-9]
    win_changes = sum(h[3] for h in win)
    win_hi = max(h[1] for h in win)
    win_lo = min(h[1] for h in win)
    if win_changes == 0:
        status = 'SETTLED'
    elif win_hi <= TRIM_BAND_FACTOR * controller.dead_band:
        status = 'TRIMMING_WITHIN_BAND'
    else:
        status = 'NOT_SETTLED'
    flags = []
    if win_hi > init['max_abs_residual_i_units']:
        flags.append(FLAG_INCREASES)
    at_limit = [k for k, u in enumerate(controller.demand)
                if u <= controller.lo or u >= controller.hi]
    if at_limit:
        flags.append(FLAG_AT_LIMIT)
    stride = max(1, int(math.ceil(len(hist) / HISTORY_MAX_POINTS)))
    keep = hist[::stride]
    if keep[-1] is not hist[-1]:
        keep = (keep if len(keep) < HISTORY_MAX_POINTS else keep[:-1]) + [hist[-1]]
    return _checked({
        'status': status, 'model_status': STATUS, 'control_law': LAW_LABEL,
        'control_steps': n, 'control_interval_s': dt_c, 'horizon_s': n * dt_c,
        'time_step_s': time_step_s, 'delay_intervals': delay_intervals,
        'display_time_constant_s': tau, 'settle_window_s': window,
        'valve_changes': changes, 'valve_log': log,
        'valve_log_truncated': changes > len(log),
        'last_valve_change_s': last_change, 'control_steps_to_last_change': steps_to_last,
        'initial': init, 'final': final,
        'history': {'time_s': [h[0] for h in keep],
                    'max_abs_residual_i_units': [h[1] for h in keep],
                    'max_abs_reading_i_units': [h[2] for h in keep]},
        'last_window': {'valve_changes': win_changes,
                        'max_abs_residual_i_units_highest': win_hi,
                        'max_abs_residual_i_units_lowest': win_lo},
        'zones_at_limit': at_limit, 'parameters': dict(controller.parameters),
        'basis': dict(BASIS), 'flags': flags,
        'limitations': [
            "The control law is the tool's own, not the plant's; the reports give its "
            'structure only.',
            'Spray zones only: bending and tilt enter as supplied influence vectors at most; '
            'the low-order part is removed as if by ideal actuators.',
            'Fixed control interval and horizon; a loop that does not settle is reported, not '
            'corrected.']})
