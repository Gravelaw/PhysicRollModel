"""Roll surface layer within one revolution (SPEC18 package 10; gap rows A4, G8; X5 in part).

Status ``UNVALIDATED_ROLL_SURFACE_CYCLE``. Standard library only; SI units; JSON-safe results.

Model [D, re-derived in SPEC18]: one axial station, depth ``y`` below the surface, curvature
neglected (layer depth << R)::

    rho*c*dT/dt = k*d2T/dy2
    y = 0:  -k*dT/dy = q(t) - h(t)*(T_s - T_sink(t))          (periodic, period t_rev)
    y = D:  T = T_D (the bulk model's steady temperature at that depth), D = 6*sqrt(a*t_rev)

The revolution is a sequence of arcs, each with constant ``q``, ``h`` and ``T_sink``
(bite: the roll's share of the bite heat over the contact length, ``h = 0``; spray arcs:
the footprint coefficient; a supplied backup-roll contact; air elsewhere: the background
coefficient). The reports name two methods (a Fourier series in the angle; a time-resolved
"phase shift" method) without equations (TM-LA6 AB, TM-LA7 EX, TM-LA26 AB, TM-LA27 AB); this
periodic layer is derived here.

Numerics: 24 geometric cells, first cell ``D/192``, growth ratio by bisection; the surface node
eliminated by the flux balance ``q + h*(T_sink - T_s) = k*(T_s - T_1)/d_1`` (as
``roll_thermal.py``); backward Euler; each arc cut into ``max(8, ceil(360*fraction))`` equal
steps (arc ends fall on step ends); revolutions marched from a uniform start (the deep
temperature) until the surface history changes by less than 1e-3 K (at most 400 revolutions,
else ValueError). The scheme is linear: for a fixed pattern of ``h``,
``T_s - T_c = q_b*A + (T_D - T_c)*B (+ (T_backup - T_c)*C)`` (``unit_solutions``).

Closed forms used as tests [D; classical half-space results]: a flux ``q1*cos(omega*t)`` gives
a surface amplitude ``q1/(e*sqrt(omega))`` lagging by 45 degrees; a constant flux ``q`` for a
time ``t`` raises the surface by ``2*q*sqrt(t)/(sqrt(pi)*e)``; after a step in ``h`` the surface
covers ``1 - exp(s)*erfc(sqrt(s))`` of its final change, ``s = h^2*t/(k*rho*c)`` (0.5724 at
``t* = k*rho*c/h^2``).

NOT modelled: feedback to the bulk (one-way: the cycle never changes the circumferential-mean
field, the stripes or the shape), curvature, non-uniform flux in the bite, wipers and oil
carry-over, a backup-roll contact unless supplied, temperature-dependent properties.
"""
import json
import math

STATUS = 'UNVALIDATED_ROLL_SURFACE_CYCLE'
CELLS = 24
FIRST_CELL_FRACTION = 1 / 192        # first cell = D/192
LAYER_DEPTH_FACTOR = 6.0             # D = 6*sqrt(a*t_rev)
MIN_ARC_STEPS = 8
STEPS_PER_REVOLUTION = 360
TOLERANCE_K = 1e-3
MAX_REVOLUTIONS = 400
ARC_KINDS = ('bite', 'spray', 'backup', 'air')
ARC_KEYS = ('kind', 'start_fraction', 'end_fraction', 'heat_flux_w_m2', 'htc_w_m2k',
            'sink_temperature_k')
LIMITATIONS = [
    'One-way: the surface cycle does not change the bulk solution, the stripe heights or the '
    'shape.',
    'The bulk field (the deep boundary) is the circumferential-mean model\'s.',
    'Uniform heat flux in the bite.',
    'No backup-roll contact unless supplied.',
    'Wipers and oil carry-over are not modelled.',
    'The three time scales are the model\'s own; the published "three thermal effects" have no '
    'numbers in the abstract read [TM-LA9 AB].',
    'Curvature neglected (the layer is thin against the radius); constant properties.']


def _num(name, value, *, positive=False, lo=None, hi=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    value = float(value)
    if positive and value <= 0:
        raise ValueError(f'{name} must be > 0')
    if lo is not None and value < lo:
        raise ValueError(f'{name} must be >= {lo}')
    if hi is not None and value > hi:
        raise ValueError(f'{name} must be <= {hi}')
    return value


def _checked(result):
    json.dumps(result, allow_nan=False)
    return result


def _arcs(arcs):
    if not isinstance(arcs, (list, tuple)) or not arcs:
        raise ValueError('arcs must be a nonempty list')
    out, pos = [], 0.0
    for i, a in enumerate(arcs):
        if not isinstance(a, dict) or set(a) != set(ARC_KEYS):
            raise ValueError(f'arcs[{i}] must have exactly the keys {list(ARC_KEYS)}')
        if a['kind'] not in ARC_KINDS:
            raise ValueError(f'arcs[{i}].kind must be one of {ARC_KINDS}')
        s = _num(f'arcs[{i}].start_fraction', a['start_fraction'], lo=0.0, hi=1.0)
        e = _num(f'arcs[{i}].end_fraction', a['end_fraction'], lo=0.0, hi=1.0)
        if abs(s - pos) > 1e-12 or not e > s:
            raise ValueError('arcs must be contiguous from 0 to 1 with increasing ends '
                             f'(arcs[{i}] starts at {s:g}, expected {pos:g})')
        h = _num(f'arcs[{i}].htc_w_m2k', a['htc_w_m2k'], lo=0.0, hi=1e9)
        sink = a['sink_temperature_k']
        sink = 0.0 if sink is None else _num(f'arcs[{i}].sink_temperature_k', sink, lo=0.0,
                                             hi=2000.0)
        if h > 0 and a['sink_temperature_k'] is None:
            raise ValueError(f'arcs[{i}] has a heat-transfer coefficient and no sink '
                             'temperature')
        out.append({'kind': a['kind'], 'start_fraction': s, 'end_fraction': e,
                    'heat_flux_w_m2': _num(f'arcs[{i}].heat_flux_w_m2', a['heat_flux_w_m2'],
                                           lo=-1e10, hi=1e10),
                    'htc_w_m2k': h, 'sink_temperature_k': sink})
        pos = e
    if abs(pos - 1.0) > 1e-12:
        raise ValueError('arcs must end at fraction 1')
    return out


class _Layer:
    """Geometric cells from the surface; backward-Euler tridiagonal operators per arc."""

    def __init__(self, k, rho_c, depth, cells):
        self.k, self.rho_c, self.n = k, rho_c, cells
        w0 = depth * FIRST_CELL_FRACTION
        target = depth / w0
        lo, hi = 1.0 + 1e-12, 2.0
        while sum(hi ** i for i in range(cells)) < target:
            hi *= 2
        for _ in range(200):
            mid = (lo + hi) / 2
            if sum(mid ** i for i in range(cells)) < target:
                lo = mid
            else:
                hi = mid
        g = (lo + hi) / 2
        w = [w0 * g ** i for i in range(cells)]
        scale = depth / sum(w)
        self.w = [x * scale for x in w]
        self.ratio = g
        self.cap = [rho_c * x for x in self.w]
        self.cond = [k / (0.5 * (self.w[i] + self.w[i + 1])) for i in range(cells - 1)]
        self.kk = k / (0.5 * self.w[0])          # surface node to first cell centre
        self.kd = k / (0.5 * self.w[-1])         # last cell centre to the deep boundary

    def operator(self, dt, h):
        """Thomas factors for (C/dt + K) T = rhs with the surface conductance of ``h``."""
        n = self.n
        gs = self.kk * h / (self.kk + h) if h > 0 else 0.0
        diag, lower, upper = [], [], []
        for i in range(n):
            d = self.cap[i] / dt
            if i > 0:
                d += self.cond[i - 1]
                lower.append(-self.cond[i - 1])
            if i < n - 1:
                d += self.cond[i]
                upper.append(-self.cond[i])
            diag.append(d)
        diag[0] += gs
        diag[-1] += self.kd
        cp, dp = [0.0] * n, [0.0] * n     # forward elimination factors
        cp[0] = upper[0] / diag[0]
        dp[0] = diag[0]
        for i in range(1, n):
            dp[i] = diag[i] - lower[i - 1] * cp[i - 1]
            if i < n - 1:
                cp[i] = upper[i] / dp[i]
        return gs, lower, cp, dp

    def solve(self, factors, rhs):
        _, lower, cp, dp = factors
        n = self.n
        y = [0.0] * n
        prev = y[0] = rhs[0] / dp[0]
        for i in range(1, n):
            prev = y[i] = (rhs[i] - lower[i - 1] * prev) / dp[i]
        for i in range(n - 2, -1, -1):
            prev = y[i] = y[i] - cp[i] * prev
        return y


def _march(layer, arcs, t_rev, deep, start, tol, max_rev):
    plan = []
    for a in arcs:
        frac = a['end_fraction'] - a['start_fraction']
        steps = max(MIN_ARC_STEPS, math.ceil(STEPS_PER_REVOLUTION * frac - 1e-9))
        dt = frac * t_rev / steps
        h, q, sink = a['htc_w_m2k'], a['heat_flux_w_m2'], a['sink_temperature_k']
        fac = layer.operator(dt, h)
        src = (layer.kk * (q + h * sink) / (layer.kk + h)) if h > 0 else q
        plan.append((a, steps, dt, fac, src))
    temps = [start] * layer.n
    prev, rev = None, 0
    n1 = layer.n - 1
    kd_deep = layer.kd * deep
    kk = layer.kk
    while True:
        rev += 1
        hist = []
        for a, steps, dt, fac, src in plan:
            h, q, sink = a['htc_w_m2k'], a['heat_flux_w_m2'], a['sink_temperature_k']
            cdt = [c / dt for c in layer.cap]
            _, lower, cp, dp = fac
            for _ in range(steps):
                # backward Euler step: (C/dt + K) T_new = C/dt*T_old + sources (Thomas)
                y = [0.0] * layer.n
                pv = y[0] = (cdt[0] * temps[0] + src) / dp[0]
                for i in range(1, n1):
                    pv = y[i] = (cdt[i] * temps[i] - lower[i - 1] * pv) / dp[i]
                pv = y[n1] = (cdt[n1] * temps[n1] + kd_deep - lower[n1 - 1] * pv) / dp[n1]
                for i in range(n1 - 1, -1, -1):
                    pv = y[i] = y[i] - cp[i] * pv
                temps = y
                ts = ((q + h * sink + kk * y[0]) / (kk + h) if h > 0 else y[0] + q / kk)
                hist.append((a, dt, ts, y[n1]))
        if prev is not None and max(abs(x[2] - y[2]) for x, y in zip(hist, prev)) < tol:
            return hist, rev
        if rev >= max_rev:
            raise ValueError(f'surface cycle not periodic to {tol:g} K after {max_rev} '
                             'revolutions')
        prev = hist


def _inputs(conductivity_w_mk, volumetric_heat_capacity_j_m3k, revolution_time_s):
    k = _num('conductivity_w_mk', conductivity_w_mk, positive=True, hi=1000.0)
    rho_c = _num('volumetric_heat_capacity_j_m3k', volumetric_heat_capacity_j_m3k, positive=True,
                 hi=1e8)
    t_rev = _num('revolution_time_s', revolution_time_s, positive=True, hi=1e4)
    return k, rho_c, t_rev


def surface_cycle(*, conductivity_w_mk, volumetric_heat_capacity_j_m3k, revolution_time_s,
                  arcs, deep_temperature_k, coolant_temperature_k=None, cells=CELLS,
                  tolerance_k=TOLERANCE_K, max_revolutions=MAX_REVOLUTIONS):
    """Periodic surface temperature over one revolution (see the module docstring).

    ``arcs``: list of ``{'kind', 'start_fraction', 'end_fraction', 'heat_flux_w_m2',
    'htc_w_m2k', 'sink_temperature_k'}``, contiguous from 0 to 1 (the bite starts at 0).
    ``coolant_temperature_k``: the ``T_c`` of the effective coefficient (default: the sink of
    the first spray arc, else of the first arc with a coefficient).
    """
    k, rho_c, t_rev = _inputs(conductivity_w_mk, volumetric_heat_capacity_j_m3k,
                              revolution_time_s)
    arcs = _arcs(arcs)
    deep = _num('deep_temperature_k', deep_temperature_k, lo=0.0, hi=2000.0)
    if isinstance(cells, bool) or not isinstance(cells, int) or not 4 <= cells <= 400:
        raise ValueError('cells must be an integer in [4, 400]')
    tol = _num('tolerance_k', tolerance_k, positive=True, hi=10.0)
    if isinstance(max_revolutions, bool) or not isinstance(max_revolutions, int) or \
            max_revolutions < 2:
        raise ValueError('max_revolutions must be an integer >= 2')
    if coolant_temperature_k is None:
        withh = [a for a in arcs if a['kind'] == 'spray'] or [a for a in arcs if a['htc_w_m2k']]
        tc = withh[0]['sink_temperature_k'] if withh else deep
    else:
        tc = _num('coolant_temperature_k', coolant_temperature_k, lo=0.0, hi=2000.0)
    a_diff = k / rho_c
    depth = LAYER_DEPTH_FACTOR * math.sqrt(a_diff * t_rev)
    layer = _Layer(k, rho_c, depth, cells)
    hist, revs = _march(layer, arcs, t_rev, deep, deep, tol, max_revolutions)
    time_fraction, ts_list, t = [], [], 0.0
    s_t = s_h = s_hts = s_flux = s_deep = 0.0
    bite_end = None
    for a, dt, ts, t_last in hist:
        t += dt
        time_fraction.append(t / t_rev)
        ts_list.append(ts)
        s_t += ts * dt
        s_h += a['htc_w_m2k'] * dt
        s_hts += a['htc_w_m2k'] * (ts - a['sink_temperature_k']) * dt
        s_flux += (a['heat_flux_w_m2'] - a['htc_w_m2k'] * (ts - a['sink_temperature_k'])) * dt
        s_deep += layer.kd * (t_last - deep) * dt
        if a['kind'] == 'bite':
            bite_end = ts
    mean_ts, mean_h = s_t / t_rev, s_h / t_rev
    # effective coefficient <h*(T_s - T_sink)>/(<T_s> - T_c)
    eff = s_hts / t_rev / (mean_ts - tc) if mean_ts != tc else None
    omega = 2 * math.pi / t_rev
    flags = []
    return _checked({
        'status': STATUS, 'time_fraction': time_fraction, 'surface_temperature_k': ts_list,
        'bite_entry_temperature_k': ts_list[-1],
        'bite_exit_temperature_k': bite_end,
        'minimum_temperature_k': min(ts_list), 'maximum_temperature_k': max(ts_list),
        'mean_surface_temperature_k': mean_ts, 'swing_k': max(ts_list) - min(ts_list),
        'mean_flux_into_roll_w_m2': s_flux / t_rev, 'deep_flux_w_m2': s_deep / t_rev,
        'mean_htc_w_m2k': mean_h, 'effective_mean_htc_w_m2k': eff,
        'mean_coefficient_ratio': (eff / mean_h) if eff is not None and mean_h > 0 else None,
        'coolant_temperature_k': tc, 'deep_temperature_k': deep,
        'skin_depth_m': math.sqrt(2 * a_diff / omega), 'layer_depth_m': depth,
        'grid': {'cells': cells, 'first_cell_m': layer.w[0], 'growth_ratio': layer.ratio},
        'revolutions': revs, 'revolution_time_s': t_rev, 'tolerance_k': tol,
        'arcs': arcs, 'flags': flags, 'limitations': list(LIMITATIONS),
        'basis': '[D, re-derived in SPEC18] periodic 1D layer under the roll surface, deep '
                 'boundary at 6*sqrt(a*t_rev) held at the bulk temperature'})


def surface_transient(*, conductivity_w_mk, volumetric_heat_capacity_j_m3k, duration_s,
                      heat_flux_w_m2=0.0, htc_w_m2k=0.0, sink_temperature_k=None,
                      initial_temperature_k, steps=STEPS_PER_REVOLUTION, cells=CELLS):
    """One transient of the same layer from a uniform start, constant ``q``, ``h`` and sink
    (layer depth ``6*sqrt(a*duration)``, deep boundary at the initial temperature): the check
    of the scheme against the closed forms (constant flux, step in ``h``)."""
    k, rho_c, dur = _inputs(conductivity_w_mk, volumetric_heat_capacity_j_m3k, duration_s)
    t0 = _num('initial_temperature_k', initial_temperature_k, lo=0.0, hi=2000.0)
    q = _num('heat_flux_w_m2', heat_flux_w_m2, lo=-1e10, hi=1e10)
    h = _num('htc_w_m2k', htc_w_m2k, lo=0.0, hi=1e9)
    sink = t0 if sink_temperature_k is None else _num('sink_temperature_k', sink_temperature_k,
                                                       lo=0.0, hi=2000.0)
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError('steps must be a positive integer')
    layer = _Layer(k, rho_c, LAYER_DEPTH_FACTOR * math.sqrt(k / rho_c * dur), cells)
    dt = dur / steps
    fac = layer.operator(dt, h)
    src = (layer.kk * (q + h * sink) / (layer.kk + h)) if h > 0 else q
    temps, hist = [t0] * layer.n, []
    for _ in range(steps):
        rhs = [c / dt * t for c, t in zip(layer.cap, temps)]
        rhs[0] += src
        rhs[-1] += layer.kd * t0
        temps = layer.solve(fac, rhs)
        hist.append((q + h * sink + layer.kk * temps[0]) / (layer.kk + h) if h > 0
                    else temps[0] + q / layer.kk)
    return _checked({'status': STATUS, 'surface_temperature_k': hist,
                     'final_surface_temperature_k': hist[-1], 'steps': steps, 'cells': cells,
                     'layer_depth_m': LAYER_DEPTH_FACTOR * math.sqrt(k / rho_c * dur)})


def unit_solutions(*, conductivity_w_mk, volumetric_heat_capacity_j_m3k, revolution_time_s,
                   arcs, coolant_temperature_k, reference_flux_w_m2=1e7, cells=CELLS,
                   tolerance_k=1e-6, max_revolutions=MAX_REVOLUTIONS):
    """Unit responses of the surface history for a fixed pattern of ``h`` (the scheme is
    linear): ``A`` per W/m2 of bite flux (bite arcs carry ``reference_flux_w_m2`` scaled by
    their own flux sign: their ``heat_flux_w_m2`` marks which arcs heat), ``B`` per K of deep
    excess over the coolant, ``C`` per K of backup excess (None without a backup arc), so that
    ``T_s - T_c = q_b*A + (T_D - T_c)*B + (T_backup - T_c)*C``. Every sink is set to the
    coolant except the backup's in ``C``."""
    tc = _num('coolant_temperature_k', coolant_temperature_k, lo=0.0, hi=2000.0)
    qref = _num('reference_flux_w_m2', reference_flux_w_m2, positive=True, hi=1e10)
    base = _arcs(arcs)

    def run(flux_on, deep, backup_excess):
        aa = []
        for a in base:
            sink = tc + (backup_excess if a['kind'] == 'backup' else 0.0)
            aa.append(dict(a, heat_flux_w_m2=(qref if flux_on and a['kind'] == 'bite' else 0.0),
                           sink_temperature_k=sink))
        r = surface_cycle(conductivity_w_mk=conductivity_w_mk,
                          volumetric_heat_capacity_j_m3k=volumetric_heat_capacity_j_m3k,
                          revolution_time_s=revolution_time_s, arcs=aa, deep_temperature_k=deep,
                          coolant_temperature_k=tc, cells=cells, tolerance_k=tolerance_k,
                          max_revolutions=max_revolutions)
        return r['time_fraction'], [t - tc for t in r['surface_temperature_k']]
    tf, a_ = run(True, tc, 0.0)
    _, b_ = run(False, tc + 1.0, 0.0)
    c_ = None
    if any(a['kind'] == 'backup' for a in base):
        _, c_ = run(False, tc, 1.0)
    return _checked({'status': STATUS, 'time_fraction': tf,
                     'per_unit_bite_flux_k_per_w_m2': [x / qref for x in a_],
                     'per_unit_deep_excess': b_,
                     'per_unit_backup_excess': c_,
                     'formula': 'T_s - T_c = q_b*A + (T_D - T_c)*B + (T_backup - T_c)*C'})


def time_scales(*, conductivity_w_mk, volumetric_heat_capacity_j_m3k, revolution_time_s,
                radius_m, mean_htc_w_m2k, event_durations_s=()):
    """The model's three thermal time scales: per revolution (and the skin depth), the surface
    film ``k*rho*c/h_mean^2`` and the bulk ``rho*c*R/(2*h_mean)`` (the lumped limit of
    ``roll_thermal``), and each event duration divided by each scale."""
    k, rho_c, t_rev = _inputs(conductivity_w_mk, volumetric_heat_capacity_j_m3k,
                              revolution_time_s)
    r = _num('radius_m', radius_m, positive=True, hi=5.0)
    h = _num('mean_htc_w_m2k', mean_htc_w_m2k, positive=True, hi=1e9)
    omega = 2 * math.pi / t_rev
    out = {'per_revolution_s': t_rev, 'skin_depth_m': math.sqrt(2 * k / rho_c / omega),
           'surface_film_s': k * rho_c / h ** 2, 'bulk_s': rho_c * r / (2 * h),
           'mean_htc_w_m2k': h,
           'scale_meaning': {
               'per_revolution_s': 'the skin cycle under bite and sprays (this module)',
               'surface_film_s': 'a step in the spray coefficient reaches 0.57 of its surface '
                                 'change (half-space, constant h)',
               'bulk_s': 'the lumped roll body (roll_thermal, radially lumped limit)'}}
    events = []
    for i, d in enumerate(event_durations_s or ()):
        d = _num(f'event_durations_s[{i}]', d, positive=True, hi=1e7)
        events.append({'duration_s': d,
                       'over_per_revolution': d / out['per_revolution_s'],
                       'over_surface_film': d / out['surface_film_s'],
                       'over_bulk': d / out['bulk_s']})
    out['events'] = events
    return _checked(out)
