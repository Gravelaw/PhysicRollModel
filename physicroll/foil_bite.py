"""EXPERIMENTAL thin-gauge roll bite with an elastic-foundation ("mattress") roll (SI, stdlib).

Status: ``UNVALIDATED_EXPERIMENTAL_MATTRESS_FOIL_BITE``. The equations are the planner's
reduction [D] in the spirit of Fleck & Johnson (1987, Int. J. Mech. Sci. 29:507; read only
through a poor OCR copy) and of the MISG report "A simple model for the cold rolling of metal
foil" [V, non-dimensional form (h - G2)p' + mu*p = x]. It is NOT the Fleck-Johnson hybrid
model: the strip is rigid-perfectly-plastic (no elastic strip zones), the roll is a local
Winkler foundation, and no benchmark with fully known inputs was found. Software-verified
for internal consistency only (rigid limit, junction continuity, Coulomb limits, energy
identity, grid convergence, trends); no plant or literature validation is claimed.

Conventions (repository): x along rolling, x = 0 at the roll centreline, entry at x < 0;
full strip thickness h; pressure p > 0 compressive; sigma tensile longitudinal stress;
K = 2Y/sqrt(3) plane-strain strength; Coulomb mu; t_b / t_f entry / exit tensile stress;
tau_f = traction on the strip, positive in the rolling direction (roll drags strip forward).

Equations
---------
Gap [D]: each roll surface indents by p/K_p (Winkler foundation modulus K_p [Pa/m])::

    h(x) = g0 + x^2/R + 2*p(x)/K_p             (g0 = unloaded centreline gap)

Slab equilibrium [D, repo convention, as slab.py]: d(sigma*h)/dx = -p*h' - 2*tau_f. In a
plastic slip zone p + sigma = K and tau_f = s*mu*p (s = +1 entry side, -1 exit side)::

    p'*(h - 2K/K_p) = K*(2x/R) + s*2*mu*p
    h' = [ (2x/R)*h + s*4*mu*p/K_p ] / (h - 2K/K_p)

The denominator must stay positive, h > 2K/K_p (the mattress limiting gauge); otherwise the
solve is rejected. Stone's t_min = 3.58*mu*D*(Y - sigma_mean)/E_roll [M] is reported for
context only.

Regimes [D]: the entry branch is integrated forward from the entry point, the exit branch
backward from the exit point (RK4 on a uniform grid, as slab.py, with every junction located
by bisection on single partial RK4 steps). CONVENTIONAL: the branch pressures meet before the
entry branch reaches h' = 0 (neutral point). FOIL: the entry branch reaches h' = 0 first at
x_a with thickness h_n; from there a no-slip zone of constant thickness h_n follows,
p = K_p*(h_n - g0 - x^2/R)/2, tau_f = (h_n/2)*p' (yield p + sigma = K kept, no plastic flow),
until it meets the exit branch at x_b (equal pressure, hence equal h). |tau_f| <= mu*p is
checked in the zone (it is exactly mu*p at x_a by construction; |tau_f|/(mu*p) grows
monotonically away from x = 0, so the end points bound it). Forward slip = h_n/h_exit - 1.

Exit point [D, spec]: plastic thinning ends on the exit branch where h' = 0, i.e.
x_e = 2*mu*p_e*R/(K_p*h_exit), g0 = h_exit - x_e^2/R - 2*p_e/K_p.

CHANGE TO THE SPECIFIED EQUATIONS (derived here, default ``contact_end_zones=True``)
-------------------------------------------------------------------------------------
The specification ends contact abruptly at the entry point (p = K - t_b) and at the exit
point (p = K - t_f). With a LOCAL (Winkler) foundation the roll surface just outside those
points springs back to its unloaded position g0 + x^2/R, which is 2*(K - t)/K_p thinner than
the strip passing there (about 6 um at sheet gauge): the rolls would overlap the incoming and
outgoing strip, contradicting the model's own gap equation. The consistent completion keeps
the strip rigid (below yield, constant thickness) where it is still pressed by the
foundation, p = K_p*(h_side - g0 - x^2/R)/2, out to where that pressure falls to zero:

* exit contact zone (x_e .. c_x, c_x = sqrt(R*(h_exit - g0))): the rigid strip moves faster
  than the roll (forward slip), so tau_f = -mu*p and h*sigma' = 2*mu*p; sigma reaches t_f
  at c_x, hence sigma_e = t_f - (2*mu/h_exit)*Int(p) and p_e = K - sigma_e. On the branch,
  h' = 0 gives p' = -2*mu*p/h, which equals the foundation slope -K_p*x/R exactly at x_e:
  the spec's h' = 0 exit is precisely the smooth junction with this zone. Writing
  p_e = K_p*h_exit*x_e/(2*mu*R) the exit condition is one scalar equation in x_e (root by
  bisection). p + sigma decreases strictly beyond x_e (second derivative < 0), so the zone
  stays rigid. If no root exists, the exit would have to stick (zero forward slip), a
  structure this module does not model: ValueError.
* entry contact zone (c_i .. x_i, c_i = -sqrt(R*(h_entry - g0))): the rigid strip is slower
  than the roll, tau_f = +mu*p, sigma falls from t_b; yield starts at the first x where
  p + sigma = K (root by bisection), p_i = K - sigma_i.
In the rigid limit both zones vanish (lengths ~ sqrt(2*R*K/K_p)). ``contact_end_zones=False``
reproduces the specification literally and flags ``SPEC_LITERAL_END_CONDITIONS_OVERLAP``.

Foundation modulus [D, with the [M] recollection confirmed]: a Winkler layer under a rigid
cylinder carries P = 2*K_p*a^3/(3R) for contact half-width a; equating to Hertz line contact
P = pi*a^2*E*/(4R) gives K_p = (3*pi/8)*E*/a = 1.178*E*/a, E* = E/(1-nu^2) (roll on a rigid
strip). Applying a Hertz calibration to the non-Hertzian bite pressure is itself an
assumption [D]. a = half the total contact length; a -> K_p -> solution is iterated to a
fixed point (secant with damped fallback, 1e-10 relative, <= 300 iterations), unless
``foundation_modulus_pa_m`` is supplied.

Rejections (ValueError, never numbers): inputs outside the BitePass-like domain; h_exit <=
2K/K_p (limiting gauge) or the slab denominator vanishing inside the bite; Coulomb shear mu*p
above the material shear yield K/2 in any slip zone ("sticking model required", as slab.py);
the entry branch reaching the no-slip state at h_n <= h_exit, or no slipping exit contact
zone (both would need a sticking exit with zero forward slip, not modelled); |tau| > mu*p at
the flat/exit junction; no neutral point / junction; fixed point not converged; force
changing by > 1e-3 on the 2*cells grid. Torque, slip dissipation and the work identity
use the projected small-angle convention of slab.py (roll surface speed = V_r everywhere).

NOT modelled: elastic strip zones and elastic strip recovery, non-local (half-space) roll
deformation and roll-surface strain velocity, a sticking exit, friction capped at shear
yield, strain hardening and rate effects, lubricant films, roll heating, thermal crown.
"""
import math

from .chatter import (BITE_MAX_REDUCTION, BITE_MIN_EXIT_THICKNESS_M, REDUCTION_EXTENDED_FLAG,
                      BitePass, BiteResponse)

STATUS = 'UNVALIDATED_EXPERIMENTAL_MATTRESS_FOIL_BITE'
# SPEC12 stage A: extended domain (see chatter.py for the reduction limit). Below 20 um exit
# gauge (the former floor of both bite models) the mattress model converged and was continuous
# through 20 um in probes, but no source validates it there; such bites are flagged.
EXTENDED_GAUGE_M = 2e-5
EXTENDED_GAUGE_FLAG = 'EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN'
EXTENDED_GAUGE_LIMITATION = (
    'Exit gauge below 20 um (extended domain): the same experimental model and the same missing '
    'closed-gap load path as at 30 um; no source validates it at this gauge; order of magnitude '
    'only.')
EXTENDED_REDUCTION_LIMITATION = (
    'Reduction above 50 % (extended domain, up to 65 %): converged and continuous across 50 % in '
    'probes; published foil passes reach 64 %; not validated.')


def _domain_flags(h0, h1):
    flags = []
    if (h0 - h1) / h0 > 0.5:
        flags.append(REDUCTION_EXTENDED_FLAG)
    if h1 < EXTENDED_GAUGE_M:
        flags.append(EXTENDED_GAUGE_FLAG)
    return flags
FOUNDATION_COEFFICIENT = 3 * math.pi / 8   # K_p = coefficient * E_star / a  (= 1.178)
_FIXED_POINT_TOL = 1e-10
_FIXED_POINT_MAX = 300
_PROFILE_POINTS = 60

BASIS = {
    'gap_equation': '[D] h = g0 + x^2/R + 2p/K_p (Winkler roll, planner reduction)',
    'slab_equation': '[D] p\'(h - 2K/K_p) = K*2x/R + s*2*mu*p, yield p + sigma = K',
    'exit_condition': '[D] h\' = 0 on the exit branch (smooth junction with the exit contact '
                      'zone, derived in this module)',
    'end_contact_zones': '[D, this module] rigid strip pressed by the foundation beyond the '
                         'plastic zone; replaces the spec\'s abrupt contact ends',
    'flat_zone': '[D] no-slip zone of constant thickness, tau = (h_n/2)*p\', |tau| <= mu*p',
    'foundation_modulus': '[D] K_p = (3*pi/8)*E*/a from Winkler vs Hertz line-contact load; '
                          'the spec quoted 1.18*E*/a from memory [M]',
    'stone_minimum_thickness': '[M] t_min = 3.58*mu*D*(Y - sigma_mean)/E_roll, context only',
    'non_dimensional_form': '[V] MISG foil report: (h - G2)p\' + mu*p = x',
}

_LIMITATIONS = [
    'EXPERIMENTAL planner reduction: rigid-plastic strip on a local Winkler roll; not the '
    'Fleck-Johnson hybrid model and not benchmarked against any case with fully known inputs.',
    'The foundation modulus is a Hertz line-contact calibration applied to a non-Hertzian bite; '
    'force scales strongly with it.',
    'No elastic strip zones: in the foil regime the roll recovery after the no-slip zone is '
    'taken up by plastic thinning, which can give implausibly large forward slip.',
    'Coulomb friction with a constant coefficient; no lubricant film, no friction capped at '
    'shear yield (rejected instead), no hardening, rate or thermal effects.',
    'Numerical convergence and internal consistency are not physical validation.',
]


# ------------------------------------------------------------------------------ helpers


def _finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _rk4(y, x, dx, rhs):
    a = rhs(x, y)
    b = rhs(x + dx / 2, [yi + dx * ai / 2 for yi, ai in zip(y, a)])
    c = rhs(x + dx / 2, [yi + dx * bi / 2 for yi, bi in zip(y, b)])
    d = rhs(x + dx, [yi + dx * ci for yi, ci in zip(y, c)])
    return [yi + dx * (ai + 2 * bi + 2 * ci + di) / 6
            for yi, ai, bi, ci, di in zip(y, a, b, c, d)]


def _bisect(fun, lo, hi, f_lo):
    """Root of fun in [lo, hi] given a sign change; f_lo = fun(lo)."""
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mid in (lo, hi):
            break
        f_mid = fun(mid)
        if f_mid == 0:
            return mid
        if (f_mid < 0) == (f_lo < 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _sign_change(a, b):
    return (a < 0 <= b) or (b < 0 <= a)


def _check_inputs(h0, h1, width, radius, y, mu, tb, tf, e_roll, nu, kp, cells, end_zones):
    named = (('entry_thickness_m', h0), ('exit_thickness_m', h1), ('width_m', width),
             ('work_roll_radius_m', radius), ('mean_flow_stress_pa', y),
             ('friction_coefficient', mu))
    for name, value in named:
        if not _finite(value) or value <= 0:
            raise ValueError(f'{name} must be a finite positive number in SI units')
    for name, value in (('entry_tension_pa', tb), ('exit_tension_pa', tf)):
        if not _finite(value) or value < 0:
            raise ValueError(f'{name} must be a finite nonnegative number in SI units')
    if not BITE_MIN_EXIT_THICKNESS_M <= h1 < h0:
        raise ValueError(f'mattress bite domain requires {BITE_MIN_EXIT_THICKNESS_M:g} m <= exit '
                         'thickness < entry')
    if not 0.02 <= (h0 - h1) / h0 <= BITE_MAX_REDUCTION:
        raise ValueError(f'mattress bite domain requires reduction in [0.02, '
                         f'{BITE_MAX_REDUCTION:g}]')
    if h0 / radius > 0.05 or width / h0 < 20:
        raise ValueError('requires thin, wide strip: h0/R <= 0.05 and width/h0 >= 20')
    if mu > 0.3:
        raise ValueError('requires 0 < friction coefficient <= 0.3')
    if max(tb, tf) >= y:
        raise ValueError('tensions must stay below the mean flow stress')
    if not _finite(e_roll) or not 1e9 <= e_roll <= 1e14:
        raise ValueError('roll Young modulus must be in [1e9, 1e14] Pa')
    if not _finite(nu) or not 0 <= nu < 0.5:
        raise ValueError('roll Poisson ratio must be in [0, 0.5)')
    if kp is not None and (not _finite(kp) or not 1e9 <= kp <= 1e22):
        raise ValueError('foundation_modulus_pa_m must be None or finite in [1e9, 1e22] Pa/m')
    if isinstance(cells, bool) or not isinstance(cells, int) or not 64 <= cells <= 4096:
        raise ValueError('cells must be an integer in [64, 4096]')
    if not isinstance(end_zones, bool):
        raise ValueError('contact_end_zones must be a bool')


# ------------------------------------------------------------------------ core solve


def _zone_pressure(kp, radius, c, s):
    """Foundation pressure K_p*(c^2 - x^2)/(2R) at distance s from the contact end |x| = c."""
    return kp * s * (2 * c - s) / (2 * radius)


def _zone_integral(kp, radius, c, s):
    """Integral of the foundation pressure over the length s measured from |x| = c."""
    return kp * s * s * (3 * c - s) / (6 * radius)


def _flat_integral(kp, radius, depth, a, b):
    """Integral of K_p*(depth - x^2/R)/2 from a to b."""
    return kp / 2 * (b - a) * (depth - (a * a + a * b + b * b) / (3 * radius))


def _exit_point(h1, radius, k, mu, tf, kp, end_zones):
    """Returns x_e, p_e, g0, exit-zone end c_x (cancellation-free forms)."""
    p_spec = k - tf
    x_spec = 2 * mu * p_spec * radius / (kp * h1)
    if not end_zones:
        g0 = h1 - x_spec ** 2 / radius - 2 * p_spec / kp
        return x_spec, p_spec, g0, x_spec

    def parts(x):          # c^2 = R*(h1 - g0) = x^2 + 2*R*p_e/K_p = x^2 + h1*x/mu
        c = math.sqrt(x * x + h1 * x / mu)
        return c, (h1 * x / mu) / (c + x)

    def residual(x):
        c, ell = parts(x)
        p_e = kp * h1 * x / (2 * mu * radius)
        return p_e - 2 * mu * _zone_integral(kp, radius, c, ell) / h1 - p_spec

    lo = 0.5 * x_spec
    f_lo = residual(lo)
    hi = None
    x = lo
    for _ in range(2000):
        x *= 1.02
        f_x = residual(x)
        if f_x >= 0:
            hi = x
            break
        lo, f_lo = x, f_x
    if hi is None or f_lo >= 0:
        raise ValueError(
            'no slipping exit contact zone exists: Coulomb friction on the rigid strip '
            'leaving the plastic zone would need more than the exit tension allows; the '
            'exit would stick (zero forward slip), a structure this experimental model '
            'does not represent')
    x_e = _bisect(residual, lo, hi, f_lo)
    c, ell = parts(x_e)
    p_e = kp * h1 * x_e / (2 * mu * radius)
    g0 = h1 - x_e ** 2 / radius - 2 * p_e / kp
    return x_e, p_e, g0, x_e + ell


def _entry_point(h0, radius, k, mu, tb, kp, g0, x_e, end_zones):
    """Returns x_i, p_i, entry-zone start c_i (negative)."""
    p_spec = k - tb
    depth = h0 - g0
    c = math.sqrt(radius * depth)
    disc = c * c - 2 * radius * p_spec / kp
    if disc <= 0:
        raise ValueError('entry point does not exist: the roll would not reach yield pressure '
                         'on the incoming strip (h_entry - g0 <= 2(K - t_b)/K_p)')
    s_spec = (2 * radius * p_spec / kp) / (c + math.sqrt(disc))
    if not end_zones:
        return -c + s_spec, p_spec, -c + s_spec

    def residual(s):
        return (_zone_pressure(kp, radius, c, s) - 2 * mu * _zone_integral(kp, radius, c, s) / h0
                + tb - k)

    lo = 0.5 * s_spec
    f_lo = residual(lo)
    top = c + min(0.0, x_e)
    step = 0.05 * s_spec
    hi = None
    while lo < top and f_lo < 0:
        s = min(lo + step, top)
        f_s = residual(s)
        if f_s >= 0:
            hi = s
            break
        lo, f_lo = s, f_s
        step *= 1.3
    if hi is None or f_lo >= 0:
        raise ValueError('entry contact zone never reaches yield before the roll centreline: '
                         'friction on the rigid incoming strip consumes the back tension '
                         'margin (outside the model domain)')
    s_i = _bisect(residual, lo, hi, f_lo)
    return -c + s_i, _zone_pressure(kp, radius, c, s_i), -c


def _solve_core(h0, h1, radius, y, mu, tb, tf, kp, cells, end_zones):
    k = 2 * y / math.sqrt(3)
    lim = 2 * k / kp
    if h1 <= lim:
        raise ValueError(
            f'exit thickness {h1:.3e} m is at or below the mattress limiting thickness '
            f'2K/K_p = {lim:.3e} m: the slab equation is singular (no solution)')
    x_e, p_e, g0, c_x = _exit_point(h1, radius, k, mu, tf, kp, end_zones)
    x_i, p_i, c_i = _entry_point(h0, radius, k, mu, tb, kp, g0, x_e, end_zones)
    if not x_i < x_e:
        raise ValueError('entry point lies downstream of the exit point (outside domain)')

    def thick(x, p):
        return g0 + x * x / radius + 2 * p / kp

    def rhs(sign):
        def f(x, state):
            p = state[0]
            h = thick(x, p)
            den = h - lim
            if not den > 0 or not math.isfinite(p):
                raise ValueError('mattress slab equation became singular (h <= 2K/K_p) inside '
                                 'the bite: below the limiting gauge of this model')
            return [(k * 2 * x / radius + sign * 2 * mu * p) / den, p, mu * p, mu * p / h]
        return f

    def numerator(x, p, sign):
        return (2 * x / radius) * thick(x, p) + sign * 4 * mu * p / kp

    f_en, f_ex = rhs(1), rhs(-1)
    if numerator(x_i, p_i, 1) >= 0:
        raise ValueError('the strip cannot start thinning at the entry point (h\' >= 0 there): '
                         'outside the model domain')
    length = x_e - x_i
    dx = length / cells
    xs = [x_i + i * dx for i in range(cells + 1)]
    xs[-1] = x_e
    ex = [None] * (cells + 1)
    ex[-1] = [p_e, 0.0, 0.0, 0.0]
    for i in range(cells, 0, -1):
        ex[i - 1] = _rk4(ex[i], xs[i], xs[i - 1] - xs[i], f_ex)
    en = [[p_i, 0.0, 0.0, 0.0]]
    if not en[0][0] < ex[0][0]:
        raise ValueError('entry pressure is not below the exit-branch pressure at entry: '
                         'no neutral point (outside the model domain)')

    def ex_at(x, j):          # exit branch at x in [xs[j], xs[j+1]], integrals from x to exit
        y = _rk4(ex[j + 1], xs[j + 1], x - xs[j + 1], f_ex)
        return [y[0], -y[1], -y[2], -y[3]]

    def en_at(x, j):
        return _rk4(en[j], xs[j], x - xs[j], f_en)

    regime = None
    for i in range(cells):
        nxt = _rk4(en[i], xs[i], dx, f_en)
        d_now, d_nxt = en[i][0] - ex[i][0], nxt[0] - ex[i + 1][0]
        n_now, n_nxt = numerator(xs[i], en[i][0], 1), numerator(xs[i + 1], nxt[0], 1)
        x_n = x_a = None
        if _sign_change(d_now, d_nxt):
            x_n = _bisect(lambda x, i=i: en_at(x, i)[0] - ex_at(x, i)[0], xs[i], xs[i + 1], d_now)
        if n_nxt >= 0:
            x_a = _bisect(lambda x, i=i: numerator(x, en_at(x, i)[0], 1), xs[i], xs[i + 1],
                          n_now)
        if x_n is not None and (x_a is None or x_n <= x_a):
            regime, cell = 'conventional', i
            break
        if x_a is not None:
            regime, cell = 'foil', i
            break
        en.append(nxt)
    if regime is None:
        raise ValueError('no neutral point or no-slip zone found in the bite (outside domain)')

    if regime == 'conventional':
        ye, yx = en_at(x_n, cell), ex_at(x_n, cell)
        h_n = thick(x_n, ye[0])
        x_a = x_b = x_n
        p_a = p_b = ye[0]
        mismatch = abs(ye[0] - yx[0])
        flat_force = flat_traction = 0.0
        tau_ratio_a = tau_ratio_b = tau_ratio_max = None
    else:
        ye = en_at(x_a, cell)
        p_a = ye[0]
        h_n = thick(x_a, p_a)
        if not h_n > h1:
            raise ValueError(
                f'the entry slip branch already reaches the no-slip state at h_n = {h_n:.3e} m '
                f'<= exit thickness {h1:.3e} m: the reduction would need a sticking exit '
                '(zero forward slip), a structure this experimental model does not represent '
                '(foil regime beyond its limit)')
        depth_n = h_n - g0

        def p_flat(x):
            return kp * (depth_n - x * x / radius) / 2

        x_b = None
        lo = x_a
        d_lo = p_flat(x_a) - ex_at(x_a, cell)[0]
        for j in range(cell, cells):
            hi = xs[j + 1]
            d_hi = p_flat(hi) - ex[j + 1][0]
            if _sign_change(d_lo, d_hi):
                x_b = _bisect(lambda x, j=j: p_flat(x) - ex_at(x, j)[0], lo, hi, d_lo)
                junction_cell = j
                break
            lo, d_lo = hi, d_hi
        if x_b is None:
            raise ValueError('the no-slip zone never meets the exit branch (outside domain)')
        yx = ex_at(x_b, junction_cell)
        p_b = p_flat(x_b)
        mismatch = abs(p_b - yx[0])
        flat_force = _flat_integral(kp, radius, depth_n, x_a, x_b)
        flat_traction = h_n / 2 * (p_b - p_a)

        def tau_ratio(x):
            return h_n * kp * abs(x) / (2 * radius) / (mu * p_flat(x))
        tau_ratio_a, tau_ratio_b = tau_ratio(x_a), tau_ratio(x_b)
        tau_ratio_max = max(tau_ratio_a, tau_ratio_b)
        if tau_ratio_b > 1 + 1e-9:
            raise ValueError('no-slip zone needs shear above mu*p where it meets the exit '
                             'branch: the stick/slip structure of this model is inconsistent '
                             'here (outside domain)')

    # entry/exit contact zones (rigid strip), zero length when contact_end_zones=False
    if end_zones:
        zf_in = _zone_integral(kp, radius, -c_i, x_i - c_i)
        zf_ex = _zone_integral(kp, radius, c_x, c_x - x_e)
    else:
        zf_in = zf_ex = 0.0
    force_pw = zf_in + ye[1] + flat_force + yx[1] + zf_ex
    traction_pw = mu * zf_in + ye[2] + flat_traction - yx[2] - mu * zf_ex
    # slip dissipation over V_r: tau_f*(V_r - u)/V_r with u/V_r = h_n/h
    slip_pw = (mu * zf_in * (1 - h_n / h0) + (ye[2] - h_n * ye[3])
               + (h_n * yx[3] - yx[2]) + mu * zf_ex * (h_n / h1 - 1))
    p_max_slip = max(p_a, p_b, p_i, p_e, yx[0])
    shear_ratio = mu * p_max_slip / (k / 2)
    if shear_ratio > 1:
        raise ValueError(
            f'Coulomb shear mu*p reaches {shear_ratio:.2f} x the material shear yield K/2 in a '
            'slip zone; sticking/shear-friction model required (outside this model\'s domain)')
    roll_pw = 2 * traction_pw
    plastic_pw = h_n * k * math.log(h0 / h1)
    tension_pw = h_n * (tf - tb)
    residual = roll_pw + tension_pw - plastic_pw - 2 * slip_pw
    scale = max(abs(roll_pw), abs(tension_pw), plastic_pw, abs(2 * slip_pw), 1e-300)
    if slip_pw < -1e-9 * scale:
        raise ValueError('negative interface dissipation (inconsistent slip directions)')

    # decimated profile
    prof_x, prof_p, prof_h, prof_zone = [], [], [], []

    def add(x, p, zone):
        prof_x.append(x)
        prof_p.append(p)
        prof_h.append(thick(x, p) if zone not in ('entry_contact_zone', 'exit_contact_zone')
                      else (h0 if zone == 'entry_contact_zone' else h1))
        prof_zone.append(zone)
    if end_zones:
        for t in range(5):
            s = (x_i - c_i) * t / 5
            add(c_i + s, _zone_pressure(kp, radius, -c_i, s), 'entry_contact_zone')
    stride = max(1, cells // _PROFILE_POINTS)
    for i in range(0, cells, stride):
        x = xs[i]
        if x < x_a:
            p, zone = en[i][0], 'entry_slip'
        elif x <= x_b:
            p, zone = kp * (h_n - g0 - x * x / radius) / 2, 'no_slip_flat'
        else:
            p, zone = ex[i][0], 'exit_slip'
        add(x, p, zone)
    add(x_e, p_e, 'exit_slip')
    if end_zones:
        for t in range(1, 6):
            s = (c_x - x_e) * (5 - t) / 5
            add(c_x - s, _zone_pressure(kp, radius, c_x, s), 'exit_contact_zone')
    order = sorted(range(len(prof_x)), key=lambda n: prof_x[n])

    return {
        'regime': regime, 'plane_strain_strength_pa': k, 'foundation_modulus_pa_m': kp,
        'limiting_thickness_m': lim, 'unloaded_gap_m': g0,
        'contact_start_m': c_i, 'plastic_entry_m': x_i, 'plastic_exit_m': x_e,
        'contact_end_m': c_x, 'contact_length_m': c_x - c_i,
        'plastic_length_m': x_e - x_i,
        'entry_zone_length_m': x_i - c_i, 'exit_zone_length_m': c_x - x_e,
        'flat_start_m': x_a, 'flat_end_m': x_b, 'neutral_thickness_m': h_n,
        'forward_slip_fraction': h_n / h1 - 1, 'backward_slip_fraction': 1 - h_n / h0,
        'pressure_plastic_entry_pa': p_i, 'pressure_plastic_exit_pa': p_e,
        'pressure_flat_start_pa': p_a, 'pressure_flat_end_pa': p_b,
        'force_per_width_n_m': force_pw, 'traction_per_width_n_m': traction_pw,
        'entry_zone_force_per_width_n_m': zf_in, 'exit_zone_force_per_width_n_m': zf_ex,
        'flat_zone_force_per_width_n_m': flat_force,
        'slip_dissipation_per_width_over_roll_speed_n_m': slip_pw,
        'plastic_power_per_width_over_roll_speed_n_m': plastic_pw,
        'tension_power_per_width_over_roll_speed_n_m': tension_pw,
        'work_residual_relative': abs(residual) / scale,
        'junction_pressure_mismatch_pa': mismatch,
        'flat_shear_over_coulomb_at_start': tau_ratio_a,
        'flat_shear_over_coulomb_at_end': tau_ratio_b,
        'max_flat_shear_over_coulomb': tau_ratio_max,
        'max_coulomb_shear_over_yield_shear': shear_ratio,
        'max_pressure_pa': max(max(prof_p), p_a, p_b),
        'profile': {'x_m': [prof_x[n] for n in order], 'pressure_pa': [prof_p[n] for n in order],
                    'thickness_m': [prof_h[n] for n in order],
                    'zone': [prof_zone[n] for n in order]},
    }


def _converged(h0, h1, radius, y, mu, tb, tf, e_star, kp_fixed, cells, end_zones):
    """Solve with a supplied K_p, or iterate a -> K_p -> solution to a fixed point."""
    if kp_fixed is not None:
        out = _solve_core(h0, h1, radius, y, mu, tb, tf, kp_fixed, cells, end_zones)
        out['fixed_point_iterations'] = 0
        out['fixed_point_residual_relative'] = 0.0
        return out

    def g(a):
        out = _solve_core(h0, h1, radius, y, mu, tb, tf, FOUNDATION_COEFFICIENT * e_star / a,
                          cells, end_zones)
        return out, out['contact_length_m'] / 2 - a

    a_prev = math.sqrt(radius * (h0 - h1)) / 2
    out, r_prev = g(a_prev)
    a = a_prev + 0.5 * r_prev
    for iteration in range(1, _FIXED_POINT_MAX + 1):
        out, r = g(a)
        if abs(r) <= _FIXED_POINT_TOL * a:
            out['fixed_point_iterations'] = iteration
            out['fixed_point_residual_relative'] = abs(r) / a
            return out
        damped = a + 0.5 * r
        if r != r_prev:
            proposal = a - r * (a - a_prev) / (r - r_prev)
            if not (math.isfinite(proposal) and 0.5 * a < proposal < 2 * a):
                proposal = damped
        else:
            proposal = damped
        a_prev, r_prev, a = a, r, proposal
    raise ValueError('foundation-modulus fixed point a -> K_p -> solution not converged in '
                     f'{_FIXED_POINT_MAX} iterations')


def _stone(mu, radius, y, tb, tf, e_roll):
    return 3.58 * mu * 2 * radius * (y - (tb + tf) / 2) / e_roll


# --------------------------------------------------------------------------- public API


def solve_mattress_bite(entry_thickness_m, exit_thickness_m, width_m, work_roll_radius_m,
                        mean_flow_stress_pa, friction_coefficient, entry_tension_pa,
                        exit_tension_pa, *, roll_youngs_modulus_pa=210e9, roll_poisson_ratio=0.3,
                        foundation_modulus_pa_m=None, cells=400,
                        contact_end_zones=True) -> dict:
    """Experimental mattress roll-bite solve (see module docstring). Returns a JSON-safe dict.

    Raises ValueError outside the domain, at/below the limiting gauge, when Coulomb shear
    exceeds shear yield, when the stick/slip structure is inconsistent, when the fixed point
    fails, or when the 2*cells grid changes the force by more than 1e-3 relative.
    """
    h0, h1, width, radius = entry_thickness_m, exit_thickness_m, width_m, work_roll_radius_m
    y, mu, tb, tf = mean_flow_stress_pa, friction_coefficient, entry_tension_pa, exit_tension_pa
    _check_inputs(h0, h1, width, radius, y, mu, tb, tf, roll_youngs_modulus_pa,
                  roll_poisson_ratio, foundation_modulus_pa_m, cells, contact_end_zones)
    e_star = roll_youngs_modulus_pa / (1 - roll_poisson_ratio ** 2)
    try:
        core = _converged(h0, h1, radius, y, mu, tb, tf, e_star, foundation_modulus_pa_m,
                          cells, contact_end_zones)
        fine = _converged(h0, h1, radius, y, mu, tb, tf, e_star, foundation_modulus_pa_m,
                          2 * cells, contact_end_zones)
    except (ArithmeticError, TypeError) as exc:
        raise ValueError(f'mattress bite evaluation failed: {exc}') from exc
    force_change = abs(fine['force_per_width_n_m'] - core['force_per_width_n_m']) / \
        fine['force_per_width_n_m']
    slip_change = abs(fine['forward_slip_fraction'] - core['forward_slip_fraction'])
    if fine['regime'] != core['regime'] or force_change > 1e-3:
        raise ValueError(f'mattress bite not grid converged (force change {force_change:.2e} '
                         'on 2*cells or regime change); increase cells')
    flags = ['EXPERIMENTAL_MATTRESS_FOIL_MODEL']
    if foundation_modulus_pa_m is None:
        flags.append('FOUNDATION_MODULUS_FROM_MEMORY_FORMULA')
    else:
        flags.append('FOUNDATION_MODULUS_SUPPLIED')
    flags.append('MATTRESS_REGIME_' + core['regime'].upper())
    if contact_end_zones:
        flags.append('CONTACT_END_ZONES_ADDED_TO_SPEC_EQUATIONS')
    else:
        flags.append('SPEC_LITERAL_END_CONDITIONS_OVERLAP')
    if h1 < 3e-4:
        flags.append('THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN')
    if force_change > 1e-4 or slip_change > 1e-6:
        flags.append('GRID_REFINEMENT_NOT_MET')
    if core['forward_slip_fraction'] > 0.15:
        flags.append('FORWARD_SLIP_IMPLAUSIBLY_LARGE_NO_ELASTIC_STRIP_ZONES')
    if h1 < 2 * core['limiting_thickness_m']:
        flags.append('NEAR_MATTRESS_LIMITING_THICKNESS')
    flags += _domain_flags(h0, h1)
    stone = _stone(mu, radius, y, tb, tf, roll_youngs_modulus_pa)
    if h1 < stone:
        flags.append('BELOW_STONE_MINIMUM_THICKNESS_CONTEXT_ONLY')
    draft = h0 - h1
    total_length = core['contact_length_m']
    result = {
        'status': STATUS, 'model': 'winkler_mattress_rigid_plastic_slab',
        'regime': core['regime'], 'contact_end_zones': contact_end_zones,
        'entry_thickness_m': h0, 'exit_thickness_m': h1, 'width_m': width,
        'work_roll_radius_m': radius, 'mean_flow_stress_pa': y,
        'friction_coefficient': mu, 'entry_tension_pa': tb, 'exit_tension_pa': tf,
        'roll_youngs_modulus_pa': roll_youngs_modulus_pa, 'roll_poisson_ratio': roll_poisson_ratio,
        'plane_strain_strength_pa': core['plane_strain_strength_pa'],
        'foundation_modulus_pa_m': core['foundation_modulus_pa_m'],
        'foundation_modulus_source': ('supplied' if foundation_modulus_pa_m is not None
                                      else 'hertz_calibrated_3pi_over_8'),
        'separating_force_n': width * core['force_per_width_n_m'],
        'force_per_width_n_m': core['force_per_width_n_m'],
        'torque_per_work_roll_nm': radius * width * core['traction_per_width_n_m'],
        'forward_slip_fraction': core['forward_slip_fraction'],
        'backward_slip_fraction': core['backward_slip_fraction'],
        'neutral_thickness_m': core['neutral_thickness_m'],
        'contact_length_m': total_length,
        'plastic_contact_length_m': core['plastic_length_m'],
        'entry_zone_length_m': core['entry_zone_length_m'],
        'exit_zone_length_m': core['exit_zone_length_m'],
        'contact_start_m': core['contact_start_m'], 'contact_end_m': core['contact_end_m'],
        'plastic_entry_m': core['plastic_entry_m'], 'plastic_exit_m': core['plastic_exit_m'],
        'flat_zone_start_m': core['flat_start_m'], 'flat_zone_end_m': core['flat_end_m'],
        'flat_zone_length_m': core['flat_end_m'] - core['flat_start_m'],
        'flat_zone_share': (core['flat_end_m'] - core['flat_start_m']) / total_length,
        'contact_radius_ratio': total_length ** 2 / (radius * draft),
        'unloaded_gap_m': core['unloaded_gap_m'],
        'limiting_thickness_m': core['limiting_thickness_m'],
        'stone_minimum_thickness_m': stone,
        'pressure_plastic_entry_pa': core['pressure_plastic_entry_pa'],
        'pressure_plastic_exit_pa': core['pressure_plastic_exit_pa'],
        'pressure_flat_start_pa': core['pressure_flat_start_pa'],
        'pressure_flat_end_pa': core['pressure_flat_end_pa'],
        'max_pressure_pa': core['max_pressure_pa'],
        'mean_pressure_pa': core['force_per_width_n_m'] / total_length,
        'entry_zone_force_n': width * core['entry_zone_force_per_width_n_m'],
        'exit_zone_force_n': width * core['exit_zone_force_per_width_n_m'],
        'flat_zone_force_n': width * core['flat_zone_force_per_width_n_m'],
        'plastic_work_power_over_roll_speed_n': width * core[
            'plastic_power_per_width_over_roll_speed_n_m'],
        'slip_dissipation_both_interfaces_over_roll_speed_n': 2 * width * core[
            'slip_dissipation_per_width_over_roll_speed_n_m'],
        'net_tension_power_over_roll_speed_n': width * core[
            'tension_power_per_width_over_roll_speed_n_m'],
        'flat_shear_over_coulomb_at_start': core['flat_shear_over_coulomb_at_start'],
        'flat_shear_over_coulomb_at_end': core['flat_shear_over_coulomb_at_end'],
        'max_flat_shear_over_coulomb': core['max_flat_shear_over_coulomb'],
        'max_coulomb_shear_over_yield_shear': core['max_coulomb_shear_over_yield_shear'],
        'convergence': {
            'cells': cells, 'fine_cells': 2 * cells,
            'force_relative_change_on_refinement': force_change,
            'slip_absolute_change_on_refinement': slip_change,
            'fixed_point_iterations': core['fixed_point_iterations'],
            'fixed_point_residual_relative': core['fixed_point_residual_relative'],
            'junction_pressure_mismatch_pa': core['junction_pressure_mismatch_pa'],
            'mechanical_work_residual_relative': core['work_residual_relative'],
        },
        'profile': core['profile'],
        'basis': dict(BASIS),
        'flags': flags,
        'limitations': list(_LIMITATIONS)
        + ([EXTENDED_GAUGE_LIMITATION] if EXTENDED_GAUGE_FLAG in flags else [])
        + ([EXTENDED_REDUCTION_LIMITATION] if REDUCTION_EXTENDED_FLAG in flags else []),
    }
    _assert_finite(result)
    return result


def _assert_finite(obj):
    if isinstance(obj, dict):
        for value in obj.values():
            _assert_finite(value)
    elif isinstance(obj, list):
        for value in obj:
            _assert_finite(value)
    elif isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError('nonfinite mattress bite output')


def derive_bite_response_mattress(bite_pass, *, roll_youngs_modulus_pa=210e9,
                                  roll_poisson_ratio=0.3, foundation_modulus_pa_m=None,
                                  cells=400, contact_end_zones=True) -> BiteResponse:
    """BiteResponse from the experimental mattress model (chatter.derive_bite_response recipe).

    Central differences with steps 1e-3*h1, 1e-3*h0, 1e-3*Y (each tension); every perturbed
    point re-converges K_p (unless supplied). Repeated with half steps: > 2 % change in any
    sensitivity adds ``SENSITIVITY_STEP_NOT_CONVERGED``; the half-step values are returned.
    Nominal force on 2*cells changing by > 1e-4 adds ``GRID_REFINEMENT_NOT_MET``. A regime
    change inside any stencil adds ``REGIME_CHANGE_WITHIN_FINITE_DIFFERENCE_STENCIL``.
    chatter.BiteResponse only accepts source 'derived_slab_hitchcock' or 'supplied', so the
    source is 'supplied' with flag ``DERIVED_BY_EXPERIMENTAL_MATTRESS_MODEL``.
    contact_radius_ratio = contact_length^2/(R*draft) (>= 1 required by BiteResponse; a value
    below 1 is raised to 1 with flag ``CONTACT_RADIUS_RATIO_CLAMPED_TO_ONE``).
    """
    if not isinstance(bite_pass, BitePass):
        raise ValueError('bite_pass must be a BitePass')
    bite_pass.validate()
    p = bite_pass
    h0, h1, se, sx = p.entry_thickness_m, p.exit_thickness_m, p.entry_tension_pa, p.exit_tension_pa
    _check_inputs(h0, h1, p.width_m, p.work_roll_radius_m, p.mean_flow_stress_pa,
                  p.friction_coefficient, se, sx, roll_youngs_modulus_pa, roll_poisson_ratio,
                  foundation_modulus_pa_m, cells, contact_end_zones)
    e_star = roll_youngs_modulus_pa / (1 - roll_poisson_ratio ** 2)

    def evaluate(exit_m=h1, entry_m=h0, s_e=se, s_x=sx, n=cells):
        if not exit_m < entry_m or max(s_e, s_x) >= p.mean_flow_stress_pa or min(s_e, s_x) < 0:
            raise ValueError('finite-difference stencil leaves the model domain')
        try:
            return _converged(entry_m, exit_m, p.work_roll_radius_m, p.mean_flow_stress_pa,
                              p.friction_coefficient, s_e, s_x, e_star, foundation_modulus_pa_m,
                              n, contact_end_zones)
        except (ArithmeticError, TypeError) as exc:
            raise ValueError(f'mattress bite evaluation failed: {exc}') from exc

    nominal = evaluate()
    regimes = {nominal['regime']}

    def sensitivities(scale):
        dh1, dh0, ds = scale * 1e-3 * h1, scale * 1e-3 * h0, scale * 1e-3 * p.mean_flow_stress_pa
        out = {}
        for key, plus, minus, step in (
                ('h', {'exit_m': h1 + dh1}, {'exit_m': h1 - dh1}, dh1),
                ('hin', {'entry_m': h0 + dh0}, {'entry_m': h0 - dh0}, dh0),
                ('se', {'s_e': se + ds}, {'s_e': se - ds}, ds),
                ('sx', {'s_x': sx + ds}, {'s_x': sx - ds}, ds)):
            if key == 'se' and se - ds < 0:
                plus, minus, centre = {'s_e': se + 2 * ds}, {'s_e': se}, 1
            elif key == 'sx' and sx - ds < 0:
                plus, minus, centre = {'s_x': sx + 2 * ds}, {'s_x': sx}, 1
            else:
                centre = 0
            rp, rm = evaluate(**plus), evaluate(**minus)
            regimes.update((rp['regime'], rm['regime']))
            if centre:
                out['one_sided'] = True
            out['F_' + key] = p.width_m * (rp['force_per_width_n_m'] - rm['force_per_width_n_m']) \
                / (2 * step)
            out['f_' + key] = ((rp['forward_slip_fraction'] - rm['forward_slip_fraction'])
                               / (2 * step))
        return out

    full = sensitivities(1.0)
    half = sensitivities(0.5)
    flags = ['DERIVED_BY_EXPERIMENTAL_MATTRESS_MODEL', 'EXPERIMENTAL_MATTRESS_FOIL_MODEL',
             'MATTRESS_REGIME_' + nominal['regime'].upper()]
    if foundation_modulus_pa_m is None:
        flags.append('FOUNDATION_MODULUS_FROM_MEMORY_FORMULA')
    else:
        flags.append('FOUNDATION_MODULUS_SUPPLIED')
    flags.append('CONTACT_END_ZONES_ADDED_TO_SPEC_EQUATIONS' if contact_end_zones
                 else 'SPEC_LITERAL_END_CONDITIONS_OVERLAP')
    if h1 < 3e-4:
        flags.append('THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN')
    if len(regimes) > 1:
        flags.append('REGIME_CHANGE_WITHIN_FINITE_DIFFERENCE_STENCIL')
    flags += _domain_flags(h0, h1)
    if full.pop('one_sided', False) or half.pop('one_sided', False):
        flags.append('ONE_SIDED_TENSION_DIFFERENCE_AT_ZERO_TENSION')
    for key in full:
        a, b = full[key], half[key]
        if abs(a - b) > 0.02 * max(abs(a), abs(b), 1e-300):
            flags.append('SENSITIVITY_STEP_NOT_CONVERGED')
            break
    fine = evaluate(n=2 * cells)
    if abs(fine['force_per_width_n_m'] - nominal['force_per_width_n_m']) > \
            1e-4 * abs(fine['force_per_width_n_m']):
        flags.append('GRID_REFINEMENT_NOT_MET')
    if nominal['forward_slip_fraction'] > 0.15:
        flags.append('FORWARD_SLIP_IMPLAUSIBLY_LARGE_NO_ELASTIC_STRIP_ZONES')
    ratio = nominal['contact_length_m'] ** 2 / (p.work_roll_radius_m * (h0 - h1))
    if ratio < 1:
        ratio = 1.0
        flags.append('CONTACT_RADIUS_RATIO_CLAMPED_TO_ONE')
    response = BiteResponse(
        separating_force_n=p.width_m * nominal['force_per_width_n_m'],
        forward_slip_fraction=nominal['forward_slip_fraction'],
        contact_length_m=nominal['contact_length_m'], contact_radius_ratio=ratio,
        entry_thickness_m=h0, exit_thickness_m=h1,
        dforce_dexit_thickness_n_m=half['F_h'], dforce_dentry_thickness_n_m=half['F_hin'],
        dforce_dentry_tension_m2=half['F_se'], dforce_dexit_tension_m2=half['F_sx'],
        dslip_dexit_thickness_per_m=half['f_h'], dslip_dentry_thickness_per_m=half['f_hin'],
        dslip_dentry_tension_per_pa=half['f_se'], dslip_dexit_tension_per_pa=half['f_sx'],
        source='supplied', flags=tuple(flags))
    response.validate()
    return response
