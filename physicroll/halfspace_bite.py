"""Reduced half-space foil bite: rigid-plastic strip between elastic half-space rolls (SI, stdlib).

Status: ``UNVALIDATED_REDUCED_HALF_SPACE_FOIL_BITE``. A REDUCED form of the foil-rolling model
of Fleck, Johnson, Mear & Zhang (1992) [E1 FT; transcribed in
docs/research/band-screening-2026-11/phase1-equations.md, sections 1.2-1.8, equation numbers
below are E1's]. Opt-in: nothing in ``diagnose()`` calls this module (SPEC18 package 2). It
lives beside the mattress bite (``foil_bite.py``) and takes its cold start from it.
Software-verified for internal consistency only (Hertz line contact, Winkler limit, work
identity, grid behaviour); no plant validation is claimed.

Conventions (as ``foil_bite.py``)
---------------------------------
x along rolling, entry at x < 0; h_p(x) full PLASTIC strip thickness (2b of E1); p pressure,
compressive positive; sigma tensile; K = 2Y/sqrt(3) (= Y_s of E1); tau_f traction on the strip,
positive in the rolling direction (q of E1); R undeformed roll radius; E_R* = E/(1 - nu^2) of
the roll; E_s* plane-strain modulus of the strip; t_b, t_f entry and exit tension; mu Coulomb
friction; m shear cap factor.

Model
-----
1. Roll gap between two half-space rolls [E1 FT eq. (8), written for the full thickness]::

       g(x) = g0 + x^2/R - (4/(pi*E_R*)) * Int p(x') ln|x - x'| dx'

   g0 is a datum constant (E1 takes the entry point as datum; a half-space in plane strain has
   no rigid-body reference). The effect of the traction on the normal displacement is
   neglected, as in E1.
2. Strip thickness under load: g(x) = h_p(x) - c_s*p(x), c_s = h_ref/E_s*, h_ref = (h0 + h1)/2
   [D, SPEC18; NOT in E1, which neglects the elastic thickness change of the strip]. This
   THICKNESS SPRING IS THE PLANNER'S ADDITION, not part of the published model. It is kept
   because the strip does compress (0.3 % of its thickness per Y_s of pressure for aluminium)
   and because without it the entry contact zone has no length. It is a load-determining input:
   +4.6 % load on the published case (W_bar 88.86 rigid, 92.94 at E_s* 80 GPa)
   [computed, SPEC18 prototype]. ``strip_plane_strain_modulus_pa=1e13`` (the upper limit)
   switches it off, the source's assumption.
3. Equilibrium [E1 eq. (1)]: d(sigma*h_p)/dx = -p*h_p' - 2*tau_f. Yield [eq. (3a)]:
   p + sigma = K. Friction stress magnitude T(p) = min(mu*p, m*K/2) [slip q = +-mu*p: E1 eq.
   (9a); cap at shear yield: BT-S14 FT, BT-S3 EX, E4 EX].
4. Zones, upstream to downstream (letters of E1 Fig. 3 and Appendix 2):

   - entry contact zone [c_i, x_i] (E1's elastic entry zone, eq. (13), which E1 neglects):
     strip below yield, h_p = h0, tau_f = +mu*p, sigma(x) = t_b - (2*mu/h0)*Int_{c_i}^{x} p;
     ends where p + sigma = K;
   - A, plastic reduction with backward slip [eq. (15), alpha = +1]: h_p*p' = K*h_p' + 2*T(p);
   - B, no-slip zone, h_p = h_n ("for the purpose of calculating the roll pressure it may be
     assumed that b = constant = b1 in the neutral zone", E1 FT); tau_f = (h_n/2)*p' [eq. (16)];
   - E, plastic reduction with backward slip between B and the pressure peak [eq. (15),
     alpha = +1]; exists only where B would need more than T(p) (used from package 3 on);
   - F, plastic reduction with forward slip [eq. (15), alpha = -1]: h_p*p' = K*h_p' - 2*T(p);
   - exit contact zone [x_e, c_x] (E1's elastic exit zone, eq. (13), neglected there):
     h_p = h1, tau_f = -mu*p, sigma(x) = t_f - (2*mu/h1)*Int_{x}^{c_x} p; starts where
     p + sigma = K.

   Structures: 'A F' (regime I, neutral point at the A/F boundary), 'A B F', 'A B E F'
   (regimes II and III of E1; the split of B into zones B, C, D needs eqs (10)-(14) and does
   not change pressure, shape, load or torque [E1 FT]: not modelled). Forward slip
   = h_n/h1 - 1, h_n = h_p at the E/F boundary (the end of B without zone E, the A/F
   boundary in 'A F').
5. Conditions at the free boundaries. From E1 Appendix 2: h_p' = 0 where A meets B
   (condition 1); (h_n/2)*p' = T(p) at the downstream end of B (condition 2, "slip occurs at
   x_BE"); h_p' = 0 where plastic reduction ends at exit (condition 4). In place of E1's
   condition 3 (p = Y_s - sigma_2 at the exit end, a pressure step) the two contact zones:
   p(c_i) = p(c_x) = 0 and yield at x_i and x_e. THIS IS THE DIFFERENCE FROM THE PRINTED
   MODEL, and the reason for it (SPEC18 section 0.1, finding 1): a pressure step on a
   half-space has a logarithmically infinite surface slope, so "db/dx = 0 at the exit" means
   something only relative to the length over which the step is smeared. The published load
   of the Fig. 9 case (W_bar 118) is therefore not a grid-independent number: two independent
   re-implementations give 78 to 134 for end lengths of 40 to 2.5 um [computed,
   re-implementation of E1; computed, SPEC18 prototype]. Closing the ends by contact zones
   gives a grid-converged load.
6. Admissibility (checked, never assumed): p >= 0; h_p non-increasing in A, E and F ("for a
   solution to exist in regime I, db/dx <= 0 throughout the nip", E1 FT); in 'A B F' the shear
   of eq. (16) within T(p) in every element of B; in 'A B E F' the friction-hill bounds
   p(x) <= p(x_a) + (2/h_n)*Int_{x_a}^{x} T and p(x) <= p(x_be) + (2/h_n)*Int_{x}^{x_be} T at
   every node of B, within 0.02*K [D, SPEC18].
7. Integrals: force per width Int p; traction per width (one roll)
   mu*Int_entry p + Int_A T + (h_n/2)*(p(x_be) - p(x_a)) + Int_E T - Int_F T - mu*Int_exit p;
   slip dissipation over roll speed, one interface, Int |tau_f|*|1 - h_n/h_p| over the
   sliding zones; plastic power over roll speed h_n*K*ln(h0/h1); tension power h_n*(t_f - t_b).
   Work identity 2*traction + tension - plastic - 2*slip = 0 (projected small-angle convention
   of slab.py). E1's torque formula (26), the moment of the pressure about the roll centre, is
   NOT used: torque = R * width * traction, the project's convention.

Three misprints of E1 (research note, checks C1, C2 and section 1.8), and what is used instead:

- eq. (30), the influence coefficient of a triangular pressure element, has the wrong sign as
  printed (it is the displacement OUT of the roll); the kernel here is re-derived with the
  sign eq. (7) needs and checked against Hertz line contact (``hertz_self_check``);
- eq. (20), the element integration of eq. (15), has the friction terms with the wrong sign
  and the weights swapped as printed (the pressure would fall where it must rise); it is not
  used: blocks A, E, F are the trapezoid rule on eq. (15);
- eq. (36), the finite-difference form of eq. (16), prints (x_{i+1} - x_{i+1}) for
  (x_{i+1} - x_{i-1}); it is not used: condition 2 is eq. (16) over the last element of B.

Influence coefficients [D, re-derived in SPEC18]. Surface displacement into the solid,
u(x) = -(2/(pi*E*)) Int p(x') ln|x - x'| dx' + const; p piecewise linear on nodes
x_0 < ... < x_N, p_0 = p_N = 0; with G(t) = (t^2/2) ln|t| - (3/4) t^2 (G'' = ln|t|, G(0) = 0)::

    I_jk = Int hat_k(x') ln|x_j - x'| dx'
         = (G(x_j - x_{k-1}) - G(x_j - x_k))/(x_k - x_{k-1})
         + (G(x_j - x_{k+1}) - G(x_j - x_k))/(x_{k+1} - x_k)

On a uniform grid I_jk = d*(kappa(j - k) + ln d - 3/2), kappa(n) = ((n+1)^2 ln|n+1|
- 2 n^2 ln|n| + (n-1)^2 ln|n-1|)/2: E1 eq. (30) with its sign corrected (E1 cites a
contact-mechanics text for the element [CIT]). The slope of the gap uses G'(t) = t ln|t| - t
in the same two difference quotients.

Numerical method (SPEC18 package 2). Boundary-fitted grid of six zones (entry contact, A, B,
E, F, exit contact), each uniform between its two free boundaries, default
``DEFAULT_ZONES``. Scaled unknowns P = p/K at the interior nodes, the free boundaries over
L = sqrt(R*(h0 - h1)), the datum G0 = g0/h1 and (with B) H_n = h_n/h1. Residual rows: E1 (entry
zone thickness), E2 (yield at x_i), A (trapezoid eq. (15)), S1 (three-point zero slope of h_p
where A ends), B (h_p = h_n), C2 (eq. (16) at the friction limit, with E), E, F, S2 (zero slope
where plastic reduction ends), E6 (exit zone thickness), E7 (yield at x_e). Newton with an
analytic Jacobian in the pressures, G0 and H_n and central differences (step 1e-7) in the
boundary columns, dense LU with partial pivoting, backtracking line search. This replaces the
published iteration (pressure updated with the shape, boundaries moved by Newton-Raphson,
under-relaxation 0.1-0.5 [BT-S14 FT]): a deliberate difference of method, not of equations.
Cold start: homotopy from the mattress bite (the kernel blended from the Winkler foundation of
``foil_bite`` to the half-space), with structure switches 'A F' <-> 'A B F' during the march.

NOT modelled: E1 eqs (4), (10)-(14) (longitudinal elastic strain of strip and roll surface,
hence stress and traction inside the no-slip zone and the regime-III zones C and D, BT-G15);
friction varying through the bite; hardening, rate and temperature inside the bite; the effect
of traction on the normal roll displacement; lubricant film; closed gap. In this package the
cold start returns 'A F' or 'A B F' only; a candidate that fails item 6 is rejected (zone E
and the structure selection follow in SPEC18 package 3).
"""
import math

from . import foil_bite
from .chatter import REDUCTION_EXTENDED_FLAG

STATUS = 'UNVALIDATED_REDUCED_HALF_SPACE_FOIL_BITE'
MODEL = 'half_space_roll_rigid_plastic_slab_reduced'
DEFAULT_ZONES = (3, 16, 24, 8, 16, 3)
# strip_shape.ALUMINIUM_E_PA / ALUMINIUM_NU (70 GPa, 0.33) [M there]
ALUMINIUM_PLANE_STRAIN_MODULUS_PA = 70e9 / (1 - 0.33 ** 2)
RIGID_STRIP_MODULUS_PA = 1e13           # upper limit: no thickness spring (E1's assumption)
STRUCTURES = ('A F', 'A B F', 'A B E F')

_NEWTON_TOL = 1e-11
_NEWTON_ACCEPT = 1e-8
_NEWTON_MAXIT = 40
# Newton iterations per homotopy step: 20, the planner prototype's choice (s23/hs_solve2.py);
# the brief's general limit is 40. With 40 a step that should fail (and be halved) can instead
# reach a spurious branch with zero forward slip (h_n = h1): three cases of the brief did so.
_MARCH_MAXIT = 20
_FD_STEP = 1e-7
_MIN_GAP = 1e-9
_TOL_DH = 1e-7                          # thickening tolerance per element (scaled by h1)
_SHEAR_TOL = 1e-6                       # eq. (16) shear ratio above 1 + this: inadmissible
HILL_TOL = 0.02                         # friction-hill bounds within 0.02*K [D, SPEC18]
_WORK_TOL = 1e-3
_MAX_SWITCHES = 4

LARGE_SLIP_FLAG = foil_bite.LARGE_SLIP_FLAG

ZONE_WORDS = ('entry_contact_zone', 'entry_slip', 'no_slip_flat', 'backward_slip', 'exit_slip',
              'exit_contact_zone')

BASIS = {
    'gap_equation': '[E1 FT eq. (8), full thickness] g = g0 + x^2/R - (4/(pi*E_R*)) Int p '
                    'ln|x - x\'| dx\'; traction effect on normal displacement neglected as in '
                    'E1; kernel of eq. (30) with its printed sign corrected [D, re-derived in '
                    'SPEC18; research note check C1]',
    'strip_thickness_spring': '[D, SPEC18; NOT in E1] h_p = g + c_s*p, c_s = (h0 + h1)/2/E_s*: '
                              'the planner\'s addition; E_s* = 1e13 Pa switches it off',
    'equilibrium_yield_friction': '[E1 FT eqs (1), (3a), (9a)] d(sigma*h_p)/dx = -p*h_p\' - '
                                  '2*tau_f, p + sigma = K, T(p) = min(mu*p, m*K/2) [cap: BT-S14 '
                                  'FT, BT-S3 EX, E4 EX]',
    'zones': '[E1 FT eqs (13), (15), (16), Fig. 3, Appendix 2] entry contact zone, A, B (h_p = '
             'h_n, tau = (h_n/2)p\'), E, F, exit contact zone; element form: trapezoid rule on '
             'eq. (15) (printed eq. (20) misprinted, check C2)',
    'boundary_conditions': '[E1 FT Appendix 2 conditions 1, 2, 4; D, SPEC18] h_p\' = 0 where A '
                           'ends and where plastic reduction ends; eq. (16) at the friction '
                           'limit at the end of B (printed eq. (36) misprinted); contact zones '
                           'with p = 0 at both contact ends in place of E1\'s pressure step '
                           '(condition 3)',
    'admissibility': '[E1 FT; D, SPEC18] p >= 0; h_p non-increasing in A, E, F; eq. (16) shear '
                     'within T(p) in B; friction-hill bounds within 0.02*K with zone E',
    'integrals': '[D, SPEC18; repository convention of slab.py] force Int p; torque R*width*'
                 'traction (E1 eq. (26) not used); work identity 2*traction + tension - '
                 'plastic - 2*slip = 0',
}

END_CLOSURE_LIMITATION = (
    'The load depends on how the bite ends are closed. This model keeps the entry and exit '
    'contact zones; the published model ends with a pressure step and its published loads depend '
    'on an unstated end length (benchmark BT-V1-HS).')
THICKNESS_SPRING_LIMITATION = (
    'The strip thickness spring (h_p = g + c_s*p, c_s = (h0 + h1)/2/E_s*) is the planner\'s '
    'addition, not part of the published model, which neglects the elastic thickness change of '
    'the strip; on the published case it raises the load by 4.6 % (W_bar 88.86 rigid, 92.94 at '
    'E_s* 80 GPa) [computed, SPEC18 prototype]. strip_plane_strain_modulus_pa = 1e13 switches it '
    'off.')
_LIMITATIONS = [
    'REDUCED half-space model: the longitudinal elastic equations of the source (E1 eqs (4), '
    '(10)-(14)) are not solved, so stress and traction inside the no-slip zone and the '
    'regime-III zones C and D are not modelled; pressure, shape, load and torque do not depend '
    'on them [E1 FT].',
    END_CLOSURE_LIMITATION,
    THICKNESS_SPRING_LIMITATION,
    'Constant friction coefficient through the bite, capped at m*K/2; no lubricant film, no '
    'hardening, rate or thermal effects inside the bite; traction does not displace the roll '
    'surface normally; no closed gap.',
    'Numerical convergence and internal consistency are not physical validation; no foil pass '
    'with measured load, slip and every input stated was found to compare with.',
]


class HalfSpaceBiteError(ValueError):
    """Structured failure: ``stage``, ``reason`` and, for an inadmissible but converged
    candidate, ``candidate`` (a ``HalfSpaceSolution``; never a result)."""

    def __init__(self, stage, reason, candidate=None):
        super().__init__(f'half-space bite, {stage}: {reason}')
        self.stage, self.reason, self.candidate = stage, reason, candidate


# ------------------------------------------------------------------ influence coefficients


def _g(t):
    return 0.0 if t == 0.0 else t * t * (0.5 * math.log(abs(t)) - 0.75)


def _g1(t):
    return 0.0 if t == 0.0 else t * math.log(abs(t)) - t


def _hat_rows(fields, x, fun):
    """Rows over ``fields`` of the hat integrals of the interior nodes k = 1..N-1 of ``x``."""
    n = len(x)
    inv = [1.0 / (x[k + 1] - x[k]) for k in range(n - 1)]
    out = []
    for s in fields:
        g = [fun(s - xk) for xk in x]
        d = [(g[k + 1] - g[k]) * inv[k] for k in range(n - 1)]
        out.append([d[k] - d[k - 1] for k in range(1, n - 1)])
    return out


def _influence_rows(fields, x):
    """I_jk at arbitrary field points ``fields`` for the hats of ``x`` [D, SPEC18]."""
    return _hat_rows(fields, x, _g)


def _slope_rows(fields, x):
    return _hat_rows(fields, x, _g1)


def influence_matrix(x) -> list:
    """``I[j][k-1] = Int hat_k(x') ln|x_j - x'| dx'`` for k = 1..N-1, any increasing nodes.

    Hat integral of eq. (30) of E1 with the printed sign corrected [D, re-derived in SPEC18]."""
    x = _increasing(x)
    return _influence_rows(x, x)


def influence_slope_matrix(x) -> list:
    """``dI_jk/dx_j`` (field point moved, hats fixed), same layout, from G'(t) = t ln|t| - t."""
    x = _increasing(x)
    return _slope_rows(x, x)


def _increasing(x):
    x = [float(v) for v in x]
    if len(x) < 3 or not all(math.isfinite(v) for v in x) or \
            any(b - a <= 0 for a, b in zip(x, x[1:])):
        raise ValueError('nodes must be at least three finite, strictly increasing numbers')
    return x


def hertz_self_check(elements=80) -> dict:
    """Influence coefficients against Hertz line contact [D, SPEC18 self-check].

    p = p0*sqrt(1 - x^2/a^2) on [-a, a], p0 = a*E*/(2R), must give u(0) - u(x) = x^2/(2R).
    E* 230 GPa, R 0.089 m, a 1 mm, nodal Hertz pressure on a uniform grid. Errors over the
    indentation depth a^2/(2R); load error of the trapezoid rule against pi*a*p0/2.
    """
    if isinstance(elements, bool) or not isinstance(elements, int) or \
            not 4 <= elements <= 400 or elements % 2:
        raise ValueError('elements must be an even integer in [4, 400]')
    e_star, radius, a = 230e9, 0.089, 1.0e-3
    p0 = a * e_star / (2 * radius)
    n = elements
    xs = [-a + 2 * a * i / n for i in range(n + 1)]
    p = [p0 * math.sqrt(max(0.0, 1 - (v / a) ** 2)) for v in xs]
    mat = influence_matrix(xs)
    u = [-(2 / (math.pi * e_star)) * sum(m * q for m, q in zip(row, p[1:n])) for row in mat]
    mid = n // 2
    depth = a * a / (2 * radius)
    err = [abs((u[mid] - u[j]) - xs[j] ** 2 / (2 * radius)) / depth for j in range(n + 1)]
    inner = [e for e, v in zip(err, xs) if abs(v) <= 0.8 * a + 1e-15]
    load = sum(0.5 * (p[k] + p[k + 1]) * (xs[k + 1] - xs[k]) for k in range(n))
    return {'elements': n, 'max_error_over_depth_all_nodes': max(err),
            'max_error_over_depth_inner_nodes': max(inner),
            'trapezoid_load_error_relative': load / (math.pi * a * p0 / 2) - 1,
            'inputs': {'e_star_pa': e_star, 'radius_m': radius, 'half_width_m': a},
            'basis': 'PV Int sqrt(1 - s^2/a^2)/(x - s) ds = pi*x/a [D, SPEC18]'}


# ------------------------------------------------------------------------- linear algebra


def _lu_factor(a):
    n = len(a)
    a = [row[:] for row in a]
    piv = list(range(n))
    for k in range(n):
        m = max(range(k, n), key=lambda i: abs(a[i][k]))
        if a[m][k] == 0.0:
            raise ArithmeticError('singular Jacobian')
        if m != k:
            a[k], a[m] = a[m], a[k]
            piv[k], piv[m] = piv[m], piv[k]
        rk = a[k]
        pk = 1.0 / rk[k]
        tail = rk[k + 1:]
        for i in range(k + 1, n):
            ri = a[i]
            f = ri[k] * pk
            if f != 0.0:
                ri[k] = f
                ri[k + 1:] = [u - f * v for u, v in zip(ri[k + 1:], tail)]
            else:
                ri[k] = 0.0
    return a, piv


def _lu_solve(lu, b):
    a, piv = lu
    n = len(a)
    y = [b[i] for i in piv]
    for i in range(n):
        ri = a[i]
        s = y[i]
        for j in range(i):
            s -= ri[j] * y[j]
        y[i] = s
    for i in range(n - 1, -1, -1):
        ri = a[i]
        s = y[i]
        for j in range(i + 1, n):
            s -= ri[j] * y[j]
        y[i] = s / ri[i]
    return y


# --------------------------------------------------------------------------- the problem


def _interp(xs, ys, v):
    if v <= xs[0]:
        return ys[0]
    if v >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= v:
            lo = mid
        else:
            hi = mid
    t = (v - xs[lo]) / (xs[hi] - xs[lo]) if xs[hi] > xs[lo] else 0.0
    return ys[lo] + t * (ys[hi] - ys[lo])


class _Problem:
    """Scaled discrete equations of one zone structure (SPEC18 package 2, numerical method)."""

    def __init__(self, h0, h1, radius, k, mu, tb, tf, e_star, strip_modulus, cap_factor,
                 structure, zones, winkler=None, lam=1.0):
        self.h0, self.h1, self.radius, self.k, self.mu = h0, h1, radius, k, mu
        self.tb, self.tf, self.e_star, self.strip_modulus = tb, tf, e_star, strip_modulus
        self.cap_factor = cap_factor
        self.cap = cap_factor / 2.0                     # m*K/2 over K
        self.L = math.sqrt(radius * (h0 - h1))
        self.a1 = self.L ** 2 / (radius * h1)
        self.a2 = 4 * k * self.L / (math.pi * e_star * h1)
        self.beta = self.L / h1
        self.cs = (h0 + h1) * k / (2 * strip_modulus * h1)
        self.structure = structure
        self.base_zones = tuple(zones)
        n1, n2, n3, ne, n4, n5 = zones
        if structure == 'A F':
            nz = (n1, n2 + n3 // 2, 0, 0, n4 + n3 // 2, n5)
            names = ('ci', 'xi', 'xn', 'xe', 'cx')
        elif structure == 'A B F':
            nz = (n1, n2, n3, 0, n4, n5)
            names = ('ci', 'xi', 'xa', 'xb', 'xe', 'cx')
        else:
            nz = (n1, n2, n3, ne, n4, n5)
            names = ('ci', 'xi', 'xa', 'xbe', 'xef', 'xe', 'cx')
        self.nz, self.names, self.nb = nz, names, len(names)
        self.flat = structure != 'A F'
        self.zone_e = structure == 'A B E F'
        idx = [0]
        for z in nz:
            idx.append(idx[-1] + z)
        self.idx = idx
        self.n = idx[-1]
        self.winkler, self.lam = winkler, lam

    def unknown_count(self):
        return self.n - 1 + self.nb + 1 + (1 if self.flat else 0)

    def full_bounds(self, bnd):
        b = dict(zip(self.names, bnd))
        if self.structure == 'A F':
            xa = xbe = xef = b['xn']
        elif self.structure == 'A B F':
            xa, xbe, xef = b['xa'], b['xb'], b['xb']
        else:
            xa, xbe, xef = b['xa'], b['xbe'], b['xef']
        return [b['ci'], b['xi'], xa, xbe, xef, b['xe'], b['cx']]

    def nodes(self, bnd):
        fb = self.full_bounds(bnd)
        x = []
        for z in range(6):
            m = self.nz[z]
            lo, hi = fb[z], fb[z + 1]
            for i in range(m):
                x.append(lo + (hi - lo) * i / m)
        x.append(fb[6])
        return x

    def unpack(self, u):
        n = self.n
        p = [0.0] + list(u[:n - 1]) + [0.0]
        bnd = list(u[n - 1:n - 1 + self.nb])
        g0 = u[n - 1 + self.nb]
        hn = u[n + self.nb] if self.flat else None
        return p, bnd, g0, hn

    def bounds_ok(self, u):
        _, bnd, _, _ = self.unpack(u)
        return all(b1 - b0 >= _MIN_GAP for b0, b1 in zip(bnd, bnd[1:])) and \
            all(math.isfinite(v) for v in u)

    def fields(self, u):
        p, bnd, g0, hn = self.unpack(u)
        x = self.nodes(bnd)
        n = self.n
        lam = self.lam
        c = -self.a2 * lam
        mat = [[c * v for v in row] for row in _influence_rows(x, x)]
        w = lam * self.cs
        if self.winkler is not None and lam < 1.0:
            w += (1 - lam) * self.winkler
        if w:
            for j in range(1, n):
                mat[j][j - 1] += w
        pin = p[1:n]
        a1 = self.a1
        h = [g0 + a1 * x[j] * x[j] + sum(m * q for m, q in zip(mat[j], pin))
             for j in range(n + 1)]
        return p, bnd, g0, hn, x, h, mat

    def tau(self, pm):
        t = self.mu * pm
        return (t, self.mu) if t < self.cap else (self.cap, 0.0)

    def residual(self, u, want_jac=False):
        n = self.n
        p, bnd, g0, hn, x, h, mat = self.fields(u)
        i1, i2, i3, ie, i4 = self.idx[1:6]
        beta, mu = self.beta, self.mu
        nu = len(u)
        cg, ch = n - 1 + self.nb, n + self.nb
        res, rows = [], []

        def addp(r, k, v):
            if 1 <= k <= n - 1:
                r[k - 1] += v

        def gap_row(j, target, with_hn=False):
            res.append(h[j] - target)
            if want_jac:
                r = [0.0] * nu
                r[:n - 1] = mat[j]
                r[cg] = 1.0
                if with_hn:
                    r[ch] = -1.0
                rows.append(r)

        def ode_row(j, sign, flatrow=False):
            # trapezoid rule on eq. (15): h_m*(p_{j+1} - p_j) - (h_{j+1} - h_j)
            #   - alpha*2*beta*T(p_m)*dx = 0 (E1's element formula (20) is misprinted)
            dp = p[j + 1] - p[j]
            pm = 0.5 * (p[j] + p[j + 1])
            dx = x[j + 1] - x[j]
            t, dt = self.tau(pm)
            if flatrow:
                hm, dh = hn, 0.0
            else:
                hm, dh = 0.5 * (h[j] + h[j + 1]), h[j + 1] - h[j]
            res.append(hm * dp - dh - sign * 2 * beta * t * dx)
            if want_jac:
                r = [0.0] * nu
                if flatrow:
                    r[ch] = dp
                else:
                    r[:n - 1] = [0.5 * (a + b) * dp - (b - a) for a, b in zip(mat[j], mat[j + 1])]
                    r[cg] = dp
                addp(r, j + 1, hm - sign * beta * dt * dx)
                addp(r, j, -hm - sign * beta * dt * dx)
                rows.append(r)

        def slope_row(j):
            # one-sided second-order slope of h_p at node j: 3H_j - 4H_{j-1} + H_{j-2} = 0
            res.append(3 * h[j] - 4 * h[j - 1] + h[j - 2])
            if want_jac:
                r = [0.0] * nu
                r[:n - 1] = [3 * a - 4 * b + c for a, b, c in zip(mat[j], mat[j - 1], mat[j - 2])]
                rows.append(r)

        def yield_row(j, lo, hi, tension, h_side):
            integ = sum(0.5 * (p[i] + p[i + 1]) * (x[i + 1] - x[i]) for i in range(lo, hi))
            ce = 2 * mu * self.L / h_side
            res.append(p[j] + tension / self.k - ce * integ - 1.0)
            if want_jac:
                r = [0.0] * nu
                addp(r, j, 1.0)
                for i in range(lo, hi):
                    w = 0.5 * (x[i + 1] - x[i]) * ce
                    addp(r, i, -w)
                    addp(r, i + 1, -w)
                rows.append(r)

        for j in range(0, i1 + 1):                       # E1
            gap_row(j, self.h0 / self.h1)
        yield_row(i1, 0, i1, self.tb, self.h0)           # E2
        for j in range(i1, i2):                          # A
            ode_row(j, +1)
        if self.flat:
            slope_row(i2)                                # S1
            for j in range(i2, i3 + 1):                  # B
                gap_row(j, hn, True)
            if self.zone_e:
                ode_row(i3 - 1, +1, True)                # C2: eq. (16) at the friction limit
                for j in range(i3, ie):                  # E
                    ode_row(j, +1)
        for j in range(ie, i4):                          # F
            ode_row(j, -1)
        slope_row(i4)                                    # S2
        for j in range(i4, n + 1):                       # E6
            gap_row(j, 1.0)
        yield_row(i4, i4, n, self.tf, self.h1)           # E7
        if len(res) != nu:
            raise ArithmeticError(f'equation count {len(res)} != unknown count {nu}')
        if not want_jac:
            return res
        for b in range(self.nb):
            col = n - 1 + b
            up = list(u)
            up[col] += _FD_STEP
            um = list(u)
            um[col] -= _FD_STEP
            rp, rm = self.residual(up), self.residual(um)
            for i in range(nu):
                rows[i][col] = (rp[i] - rm[i]) / (2 * _FD_STEP)
        return res, rows

    def newton(self, u, maxit=_NEWTON_MAXIT):
        """Returns (u, iterations, max|R|); HalfSpaceBiteError('newton', ...) on failure."""
        u = list(u)
        try:
            norm = max(abs(v) for v in self.residual(u))
        except (ArithmeticError, ValueError) as exc:
            raise HalfSpaceBiteError('newton', f'residual not computable: {exc}') from exc
        if not math.isfinite(norm):
            raise HalfSpaceBiteError('newton', 'residual not finite at the start point')
        for it in range(maxit):
            if norm < _NEWTON_TOL:
                return u, it, norm
            try:
                res, jac = self.residual(u, True)
                du = _lu_solve(_lu_factor(jac), [-v for v in res])
            except (ArithmeticError, ValueError) as exc:
                raise HalfSpaceBiteError('newton', f'linear solve failed: {exc}') from exc
            s = 1.0
            while True:
                if s < 1e-4:
                    raise HalfSpaceBiteError(
                        'newton', f'line search failed below step 1e-4 at residual {norm:.3e}')
                trial = [a + s * b for a, b in zip(u, du)]
                nt = math.inf
                if self.bounds_ok(trial):
                    try:
                        nt = max(abs(v) for v in self.residual(trial))
                    except (ArithmeticError, ValueError):
                        nt = math.inf
                if math.isfinite(nt) and nt < norm * (1 - 1e-4 * s):
                    break
                s *= 0.5
            u, norm = trial, nt
        if norm < _NEWTON_ACCEPT:      # at the iteration limit: accepted, counted by the caller
            return u, maxit, norm
        raise HalfSpaceBiteError('newton', f'not converged in {maxit} iterations '
                                           f'(residual {norm:.3e})')

    # ---------------------------------------------------------------- measures
    def measures(self, u):
        """Admissibility measures of item 6 on a solution (scaled)."""
        p, bnd, g0, hn, x, h, mat = self.fields(u)
        n = self.n
        i1, i2, i3, ie, i4 = self.idx[1:6]
        dh_a = max(h[j + 1] - h[j] for j in range(i1, i2))
        dh_e = max([h[j + 1] - h[j] for j in range(i3, ie)] or [-math.inf])
        dh_f = max(h[j + 1] - h[j] for j in range(ie, i4))
        out = {'min_p': min(p[1:n]), 'max_dh_slip': max(dh_a, dh_f, dh_e),
               'shear_ratio_max': None, 'hill_margin_min': None, 'net_shear': None}
        if self.flat and i3 > i2:
            ratios, incs = [], []
            for j in range(i2, i3):
                pm = 0.5 * (p[j] + p[j + 1])
                dx = x[j + 1] - x[j]
                t = self.tau(pm)[0]
                ratios.append(hn * (p[j + 1] - p[j]) / (2 * self.beta * t * dx))
                incs.append(2 * self.beta / hn * t * dx)
            fwd = [0.0]
            for v in incs:
                fwd.append(fwd[-1] + v)
            tot = fwd[-1]
            m1 = min(p[i2] + fwd[k - i2] - p[k] for k in range(i2, i3 + 1))
            m2 = min(p[i3] + (tot - fwd[k - i2]) - p[k] for k in range(i2, i3 + 1))
            out.update(shear_ratio_max=max(abs(v) for v in ratios), hill_margin_min=min(m1, m2),
                       net_shear=abs(p[i3] - p[i2]) / tot)
        return out

    def needs_no_slip_zone(self, u):
        """'A F': h_p rises into the neutral point (the A F structure would thicken)."""
        _, _, _, _, _, h, _ = self.fields(u)
        i2 = self.idx[2]
        return h[i2] - h[i2 - 1] > 0.0


def _convert(pr, u, structure):
    """Carry a solution of ``pr`` to the other cold-start structure (same lam)."""
    p, bnd, g0, hn, x, h, _ = pr.fields(u)
    new = _Problem(pr.h0, pr.h1, pr.radius, pr.k, pr.mu, pr.tb, pr.tf, pr.e_star,
                   pr.strip_modulus, pr.cap_factor, structure, pr.base_zones, pr.winkler, pr.lam)
    i1, i2 = pr.idx[1], pr.idx[2]
    if structure == 'A F':          # x_n = (x_a + x_b)/2
        nb = [bnd[0], bnd[1], 0.5 * (bnd[2] + bnd[3]), bnd[4], bnd[5]]
        extra = []
    else:                           # 'A B F' from 'A F'
        jt = i2
        while jt > i1 + 1 and h[jt - 1] <= h[jt]:
            jt -= 1                 # x_a: the last node of A where h_p still falls
        xa, xn = x[jt], bnd[2]
        width = max(xn - xa, 0.02 * (bnd[3] - bnd[1]))
        nb = [bnd[0], bnd[1], xn - width, xn + 0.5 * width, bnd[3], bnd[4]]
        extra = [min(h[jt:i2 + 1])]
    xn_ = new.nodes(nb)
    pn = [_interp(x, p, v) for v in xn_]
    return new, pn[1:-1] + nb + [g0] + extra


# ------------------------------------------------------------------------------ public API


class HalfSpaceSolution:
    """Internal state of a solve (problem and scaled unknowns) for warm starts and SPEC18
    package 4. Not JSON; never part of a result."""

    def __init__(self, problem, unknowns):
        self.problem = problem
        self.unknowns = list(unknowns)

    @property
    def structure(self):
        return self.problem.structure

    def force_per_width_n_m(self):
        p, bnd, g0, hn, x, h, _ = self.problem.fields(self.unknowns)
        pr = self.problem
        return pr.k * pr.L * sum(0.5 * (p[j] + p[j + 1]) * (x[j + 1] - x[j])
                                 for j in range(pr.n))

    def measures(self):
        return self.problem.measures(self.unknowns)


def _check(h0, h1, width, radius, y, mu, tb, tf, e_roll, nu, strip_modulus, cap, zones):
    try:
        foil_bite._check_inputs(h0, h1, width, radius, y, mu, tb, tf, e_roll, nu, None, 400,
                                True)
    except ValueError as exc:
        raise ValueError(str(exc).replace('mattress bite', 'half-space bite')) from exc
    if not foil_bite._finite(strip_modulus) or not 1e9 <= strip_modulus <= 1e13:
        raise ValueError('strip_plane_strain_modulus_pa must be in [1e9, 1e13] Pa')
    if not foil_bite._finite(cap) or not 0 < cap <= 1:
        raise ValueError('shear_cap_factor must be in (0, 1]')
    if not isinstance(zones, (tuple, list)) or len(zones) != 6 or \
            any(isinstance(z, bool) or not isinstance(z, int) for z in zones):
        raise ValueError('zones must be six integers (entry, A, B, E, F, exit)')
    n1, n2, n3, ne, n4, n5 = zones
    if n1 < 2 or n5 < 2 or n2 < 4 or n4 < 4 or n3 < 4 or ne < 4 or sum(zones) > 400:
        raise ValueError('zones need entry and exit >= 2, A, B, E and F >= 4 elements, and at '
                         'most 400 in all')


def _mattress_start(h0, h1, width, radius, y, mu, tb, tf, e_roll, nu, strip_modulus, cap,
                    zones):
    """Problem at lam = 0 (Winkler kernel) and its start vector from the mattress bite."""
    try:
        m = foil_bite.solve_mattress_bite(h0, h1, width, radius, y, mu, tb, tf,
                                          roll_youngs_modulus_pa=e_roll, roll_poisson_ratio=nu)
    except ValueError as exc:
        raise HalfSpaceBiteError('cold start', f'the mattress bite rejected the pass: {exc}') \
            from exc
    k = 2 * y / math.sqrt(3)
    e_star = e_roll / (1 - nu ** 2)
    structure = 'A B F' if m['regime'] == 'foil' else 'A F'
    pr = _Problem(h0, h1, radius, k, mu, tb, tf, e_star, strip_modulus, cap, structure, zones,
                  winkler=2 * k / (m['foundation_modulus_pa_m'] * h1), lam=0.0)
    if structure == 'A B F':
        bnd = [m['contact_start_m'], m['plastic_entry_m'], m['flat_zone_start_m'],
               m['flat_zone_end_m'], m['plastic_exit_m'], m['contact_end_m']]
        extra = [m['neutral_thickness_m'] / h1]
    else:
        bnd = [m['contact_start_m'], m['plastic_entry_m'], m['flat_zone_start_m'],
               m['plastic_exit_m'], m['contact_end_m']]
        extra = []
    bnd = [b / pr.L for b in bnd]
    x = pr.nodes(bnd)
    px, pp = m['profile']['x_m'], m['profile']['pressure_pa']
    p = [_interp(px, pp, v * pr.L) / k for v in x]
    return pr, p[1:-1] + bnd + [m['unloaded_gap_m'] / h1] + extra, m


class _Switch(Exception):
    pass


def _march_step_check(pr, u):
    """Acceptance of a march step: p >= 0 and no thickening in A or F (1e-7*h1)."""
    q = pr.measures(u)
    if q['min_p'] < 0:
        raise HalfSpaceBiteError('march', 'negative pressure')
    switch_to_flat = pr.structure == 'A F' and pr.needs_no_slip_zone(u)
    if q['max_dh_slip'] > _TOL_DH and not switch_to_flat:
        raise HalfSpaceBiteError('march', 'strip thickens in a reduction zone')
    if switch_to_flat:
        raise _Switch('A B F')
    if pr.structure == 'A B F':
        _, bnd, _, _ = pr.unpack(u)
        if bnd[3] - bnd[2] < 0.01 * (bnd[4] - bnd[1]):
            raise _Switch('A F')


def _cold_start(h0, h1, width, radius, y, mu, tb, tf, e_roll, nu, strip_modulus, cap, zones):
    """Homotopy from the mattress bite to the half-space kernel (SPEC18 package 2)."""
    pr, u, m = _mattress_start(h0, h1, width, radius, y, mu, tb, tf, e_roll, nu, strip_modulus,
                               cap, zones)
    try:
        u, it, norm = pr.newton(u)
    except HalfSpaceBiteError as exc:
        raise HalfSpaceBiteError('cold start at the Winkler limit', exc.reason) from exc
    lam, step, total, switches, steps = 0.0, 0.25, it, 0, 0
    at_limit = [0]

    def count(iterations, norm, maxit):
        if iterations >= maxit and norm >= _NEWTON_TOL:
            at_limit[0] += 1
        return iterations
    count(it, norm, _NEWTON_MAXIT)
    while lam < 1.0:
        new = min(1.0, lam + step)
        pr.lam = new
        try:
            u2, it, norm = pr.newton(u, maxit=_MARCH_MAXIT)
            _march_step_check(pr, u2)
            u, lam = u2, new
            total += count(it, norm, _MARCH_MAXIT)
            steps += 1
            step = min(step * 1.5, 0.5)
        except _Switch as sw:
            pr.lam = lam
            if step > 0.02:
                step *= 0.5
                continue
            target = str(sw)
            pr2, u2 = _convert(pr, u, target)
            pr2.lam = min(1.0, lam + step)
            try:
                u3, it, norm = pr2.newton(u2)
            except HalfSpaceBiteError as exc:
                raise HalfSpaceBiteError('march', f'structure switch to {target} failed at '
                                                  f'lambda {lam:.4f}: {exc.reason}') from exc
            pr, u, lam = pr2, u3, pr2.lam
            total += count(it, norm, _NEWTON_MAXIT)
            steps += 1
            switches += 1
            if switches > _MAX_SWITCHES:
                raise HalfSpaceBiteError('march', 'more than 4 structure switches')
        except HalfSpaceBiteError as exc:
            pr.lam = lam
            _, bnd, _, _ = pr.unpack(u)
            if (pr.structure == 'A B F' and bnd[3] - bnd[2] < 0.08 * (bnd[4] - bnd[1])
                    and switches < _MAX_SWITCHES):
                pr2, u2 = _convert(pr, u, 'A F')
                pr2.lam = new
                try:
                    u3, it, norm = pr2.newton(u2)
                    if pr2.needs_no_slip_zone(u3):
                        raise HalfSpaceBiteError('march', 'A F still thickens before the '
                                                          'neutral point')
                    pr, u, lam = pr2, u3, new
                    total += count(it, norm, _NEWTON_MAXIT)
                    steps += 1
                    switches += 1
                    continue
                except HalfSpaceBiteError:
                    pass
            step *= 0.5
            if step < 1e-3:
                raise HalfSpaceBiteError('march', f'homotopy failed at lambda {lam:.4f} '
                                                  f'({pr.structure}): {exc.reason}') from exc
    return pr, u, {'newton_iterations': total, 'homotopy_steps': steps,
                   'structure_switches': switches,
                   'newton_runs_accepted_at_iteration_limit': at_limit[0]}


def _admissible(pr, u):
    """Item 6 of the model on the candidate at lam = 1: (True, '') or (False, measure)."""
    q = pr.measures(u)
    if q['min_p'] < 0:
        return False, f'negative pressure (min p/K {q["min_p"]:.3e})'
    if q['max_dh_slip'] > _TOL_DH:
        return False, (f'strip thickens in a reduction zone (max dh_p/h1 per element '
                       f'{q["max_dh_slip"]:.3e})')
    if pr.structure == 'A B F' and q['shear_ratio_max'] > 1 + _SHEAR_TOL:
        return False, (f'eq. (16) shear in the no-slip zone is {q["shear_ratio_max"]:.3f} of '
                       'the friction limit')
    if pr.structure == 'A B E F' and q['hill_margin_min'] < -HILL_TOL:
        return False, (f'friction-hill bound missed by {-q["hill_margin_min"]:.4f}*K in the '
                       'no-slip zone')
    return True, ''


def _result(pr, u, width, inputs, conv):
    k, L, h0, h1, mu, radius = pr.k, pr.L, pr.h0, pr.h1, pr.mu, pr.radius
    p, bnd, g0, hn_b, x, h, _ = pr.fields(u)
    n = pr.n
    i1, i2, i3, ie, i4 = pr.idx[1:6]
    fb = [v * L for v in pr.full_bounds(bnd)]
    ci, xi, xa, xbe, xef, xe, cx = fb
    hn = h[ie]                       # neutral thickness: h_p at the E/F boundary (scaled)
    xs = [v * L for v in x]
    ps = [v * k for v in p]
    hs = [v * h1 for v in h]
    force = sum(0.5 * (ps[j] + ps[j + 1]) * (xs[j + 1] - xs[j]) for j in range(n))
    trac = slip = 0.0
    cap_active = False
    for j in range(n):
        dx = xs[j + 1] - xs[j]
        pm = 0.5 * (p[j] + p[j + 1])
        if j < i1 or j >= i4:        # contact zones: tau = +-mu*p, h_p = h0 or h1
            t = mu * pm * k
            side = 1.0 if j < i1 else -1.0
            hp = h0 / h1 if j < i1 else 1.0
            trac += side * t * dx
            slip += t * dx * abs(1 - hn / hp)
        elif i2 <= j < i3:           # no-slip zone
            trac += 0.5 * hn_b * h1 * (ps[j + 1] - ps[j])
        else:
            tt, dt = pr.tau(pm)
            if dt == 0.0:
                cap_active = True
            t = tt * k
            side = -1.0 if j >= ie else 1.0
            hm = 0.5 * (h[j] + h[j + 1])
            trac += side * t * dx
            slip += t * dx * abs(1 - hn / hm)
    plastic = hn * h1 * k * math.log(h0 / h1)
    tension = hn * h1 * (pr.tf - pr.tb)
    work = 2 * trac + tension - plastic - 2 * slip
    scale = max(abs(2 * trac), plastic, abs(2 * slip), abs(tension), 1e-300)
    work_rel = abs(work) / scale
    if work_rel > _WORK_TOL:
        raise HalfSpaceBiteError('post-processing', f'work identity residual {work_rel:.2e} '
                                                    'above 1e-3')
    q = pr.measures(u)
    jmax = max(range(n + 1), key=lambda j: ps[j])
    contact = cx - ci
    draft = h0 - h1
    neutral = xef if pr.flat else xa
    zone_of = []
    for j in range(n + 1):
        if j < i1:
            z = 0
        elif j < i2:
            z = 1
        elif j < i3:
            z = 2
        elif j < ie:
            z = 3
        elif j < i4:
            z = 4
        else:
            z = 5
        zone_of.append(ZONE_WORDS[z])
    flags = ['REDUCED_HALF_SPACE_FOIL_MODEL',
             'HALF_SPACE_REGIME_FOIL' if pr.flat else 'HALF_SPACE_REGIME_CONVENTIONAL']
    if cap_active:
        flags.append('SHEAR_CAP_ACTIVE')
    if pr.strip_modulus < RIGID_STRIP_MODULUS_PA:
        flags.append('STRIP_THICKNESS_SPRING_NOT_IN_PUBLISHED_MODEL')
    if hn - 1.0 > 0.15:
        flags.append(LARGE_SLIP_FLAG)
    if draft / h0 < 0.10:
        flags.append('LIGHT_REDUCTION_ELASTIC_STRIP_ZONES_NOT_MODELLED')
    if max(p) > 16.0:
        flags.append('PEAK_PRESSURE_ABOVE_16_PLANE_STRAIN_YIELD')
    if h1 < 3e-4:
        flags.append('THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN')
    flags += foil_bite._domain_flags(h0, h1)
    no_slip = None
    if pr.flat:
        no_slip = {'eq16_shear_over_limit_max': q['shear_ratio_max'],
                   'friction_hill_margin_min_over_k': q['hill_margin_min'],
                   'net_shear_over_limit': q['net_shear'],
                   'note': 'Ratios of the no-slip zone B: the largest eq. (16) shear '
                           '(h_n/2)*p\' over the friction limit T(p) per element; the smallest '
                           'margin of the two friction-hill bounds over K; the net pressure rise '
                           'over the largest rise the friction limit allows. Stress and traction '
                           'inside B need E1 eqs (10)-(14), not solved here.'}
    w = width
    result = {
        'status': STATUS, 'model': MODEL,
        'regime': 'foil' if pr.flat else 'conventional', 'zone_structure': pr.structure,
        **inputs,
        'plane_strain_strength_pa': k,
        'separating_force_n': w * force, 'force_per_width_n_m': force,
        'torque_per_work_roll_nm': radius * w * trac,
        'forward_slip_fraction': hn - 1.0, 'backward_slip_fraction': 1 - hn * h1 / h0,
        'neutral_thickness_m': hn * h1,
        'contact_length_m': contact, 'plastic_contact_length_m': xe - xi,
        'entry_zone_length_m': xi - ci, 'exit_zone_length_m': cx - xe,
        'contact_start_m': ci, 'contact_end_m': cx, 'plastic_entry_m': xi, 'plastic_exit_m': xe,
        'flat_zone_start_m': xa, 'flat_zone_end_m': xbe, 'flat_zone_length_m': xbe - xa,
        'flat_zone_share': (xbe - xa) / contact,
        'backward_slip_zone_length_m': xef - xbe,
        'neutral_point_m': neutral, 'peak_pressure_position_m': xs[jmax],
        'contact_radius_ratio': contact ** 2 / (radius * draft),
        'max_pressure_pa': ps[jmax], 'mean_pressure_pa': force / contact,
        'plastic_work_power_over_roll_speed_n': w * plastic,
        'slip_dissipation_both_interfaces_over_roll_speed_n': 2 * w * slip,
        'net_tension_power_over_roll_speed_n': w * tension,
        'max_coulomb_shear_over_yield_shear': mu * max(p) / 0.5,
        'shear_cap_active': cap_active,
        'no_slip_zone': no_slip,
        'structure_selection': [['cold_start_march', f'{pr.structure} accepted']],
        'convergence': {'zones': list(pr.base_zones), 'elements': n,
                        'newton_iterations': conv['newton_iterations'],
                        'residual_max': max(abs(v) for v in pr.residual(u)),
                        'homotopy_steps': conv['homotopy_steps'],
                        'structure_switches': conv['structure_switches'],
                        'newton_runs_accepted_at_iteration_limit':
                            conv['newton_runs_accepted_at_iteration_limit'],
                        'cold_start': True,
                        'mechanical_work_residual_relative': work_rel},
        'profile': {'x_m': xs, 'pressure_pa': ps, 'thickness_m': hs, 'zone': zone_of},
        'basis': dict(BASIS),
        'flags': flags,
        'limitations': list(_LIMITATIONS)
        + ([foil_bite.EXTENDED_GAUGE_LIMITATION] if foil_bite.EXTENDED_GAUGE_FLAG in flags
           else [])
        + ([foil_bite.EXTENDED_REDUCTION_LIMITATION] if REDUCTION_EXTENDED_FLAG in flags
           else []),
    }
    foil_bite._assert_finite(result)
    return result


def solve_half_space_bite(entry_thickness_m, exit_thickness_m, width_m, work_roll_radius_m,
                          mean_flow_stress_pa, friction_coefficient, entry_tension_pa,
                          exit_tension_pa, *, roll_youngs_modulus_pa=210e9, roll_poisson_ratio=0.3,
                          strip_plane_strain_modulus_pa=ALUMINIUM_PLANE_STRAIN_MODULUS_PA,
                          shear_cap_factor=1.0, zones=DEFAULT_ZONES, warm_start=None,
                          with_solution=False):
    """Reduced half-space foil bite (see module docstring). Returns a JSON-safe dict, or
    ``(dict, HalfSpaceSolution)`` when ``with_solution`` is True.

    ``warm_start`` is accepted and ignored until SPEC18 package 3. Raises ValueError (a
    ``HalfSpaceBiteError`` with ``stage`` and ``reason`` for solver failures) on inputs out of
    the domain, a failed cold start, an inadmissible candidate (its converged state is in
    ``candidate``) or a work identity residual above 1e-3. Never returns a number from a
    failed solve.
    """
    h0, h1, width, radius = entry_thickness_m, exit_thickness_m, width_m, work_roll_radius_m
    y, mu, tb, tf = mean_flow_stress_pa, friction_coefficient, entry_tension_pa, exit_tension_pa
    e_roll, nu = roll_youngs_modulus_pa, roll_poisson_ratio
    _check(h0, h1, width, radius, y, mu, tb, tf, e_roll, nu, strip_plane_strain_modulus_pa,
           shear_cap_factor, zones)
    zones = tuple(zones)
    try:
        pr, u, conv = _cold_start(h0, h1, width, radius, y, mu, tb, tf, e_roll, nu,
                                  strip_plane_strain_modulus_pa, shear_cap_factor, zones)
        ok, why = _admissible(pr, u)
    except (ArithmeticError, TypeError, IndexError) as exc:
        raise HalfSpaceBiteError('solver', f'evaluation failed: {exc}') from exc
    if not ok:
        raise HalfSpaceBiteError(
            'structure', f'zone structure of the cold start is not admissible ({pr.structure}): '
                         f'{why}', candidate=HalfSpaceSolution(pr, u))
    inputs = {'entry_thickness_m': h0, 'exit_thickness_m': h1, 'width_m': width,
              'work_roll_radius_m': radius, 'mean_flow_stress_pa': y,
              'friction_coefficient': mu, 'entry_tension_pa': tb, 'exit_tension_pa': tf,
              'roll_youngs_modulus_pa': e_roll, 'roll_poisson_ratio': nu,
              'strip_plane_strain_modulus_pa': strip_plane_strain_modulus_pa,
              'shear_cap_factor': shear_cap_factor}
    try:
        result = _result(pr, u, width, inputs, conv)
    except (ArithmeticError, TypeError, IndexError) as exc:
        raise HalfSpaceBiteError('post-processing', f'evaluation failed: {exc}') from exc
    if with_solution:
        return result, HalfSpaceSolution(pr, u)
    return result
