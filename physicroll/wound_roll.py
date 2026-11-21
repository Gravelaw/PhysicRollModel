"""Wound roll: one radial accretion model per lane and the entrained air film (SPEC19 package 9).

UNVALIDATED. Standard library only. Gap G9 (core) and G10 (film). The gap rows quote the
classical winding model from memory; everything used here is re-derived
[D, re-derived in SPEC19] (the equation itself is restated in SS-S42 EX).

Model. Axisymmetric wound roll, radius ``r`` from the core ``r_c`` to the outer radius ``s``;
``sigma_r`` radial (pressure ``P = -sigma_r``), ``sigma_t`` hoop; increments caused by one added
lap carry a ``d``.

- Equilibrium ``r*d(sigma_r)/dr + sigma_r - sigma_t = 0``; strains ``eps_r = du/dr``,
  ``eps_t = u/r``.
- Orthotropic increments: ``eps_t = (d_sigma_t - nu*d_sigma_r)/E_t``,
  ``eps_r = d_sigma_r/E_r - nu*d_sigma_t/E_t``; ``E_r`` depends on the pressure present.
- With ``d_sigma_t = y + r*y'`` (``y = d_sigma_r``): ``r^2*y'' + 3*r*y' - (E_t/E_r - 1)*y = 0``.
- Outer condition (thin ring of thickness ``h`` wound at hoop stress ``T_w``): ``y(s) = -T_w*h/s``.
- Core: ``u(r_c) = y*r_c/E_c`` (``E_c`` = pressure per unit radial strain of the core), so
  ``r_c*y'(r_c) = y(r_c)*(E_t/E_c - 1 + nu)``; a rigid core has ``E_t/E_c = 0``. For a
  thin-walled tube ``E_c = E_core*wall/r_c`` [D: ring under external pressure].
- After a lap ``sigma_r += y``; the hoop stress of every lap below ``+= y + r*y'``; radial
  displacement ``u = r*((y + r*y') - nu*y)/E_t``, accumulated per node.

Radial stack laws (EACH NEEDS AN INPUT; there is NO default): no radial stack stiffness of
wound aluminium foil (oily, with entrained air) is published. Measure it with a press test on a
stack of 50 to 200 laps of the oily foil: pressure against strain gives ``K1`` and ``K2`` of the
Pfeiffer form. ``'constant'``: ``E_r``; ``'ratio_of_hoop_modulus'``: ``E_r = E_t/ratio``
(context only: "about two orders of magnitude softer than the bulk" for metal coils [SS-S40 VP,
a retelling]); ``'pfeiffer'``: ``E_r = K2*(P + K1)`` [SS-S42 EX].

Air layer [D: isothermal gas law and springs in series; the idea is in SS-S49 EX, SS-S50 AB]: an
air gap ``g0`` per lap at ambient pressure ``P_a`` thins to ``g(P) = g0*P_a/(P + P_a)`` with the
modulus ``P + P_a``; with the strip share ``h/(h + g)``:
``1/E_r,eq = (h/(h + g))/E_r + (g/(h + g))/(P + P_a)``. The gap enters the radial stiffness only,
not the radius of the stack [D, analyst choice].

Closed form used as the check [D]: ``E_r = E_t``, rigid core, constant ``T_w``:
``sigma_r(r) = -(T_w/2)*(1 + beta*r_c^2/r^2)*ln((R^2 + beta*r_c^2)/(r^2 + beta*r_c^2))``,
``sigma_t(r) = T_w - (T_w/2)*(1 - beta*r_c^2/r^2)*ln(same)``, ``beta = (1 - nu)/(1 + nu)``.

Numerical method: laps are lumped into layers of ``n_l`` laps (thickness ``n_l*h``); nodes at
the layer tops, node 0 on the core. For a new layer: second-order central differences of the
equation at the interior nodes with ``E_r`` from the pressure present there, the core condition
by a one-sided difference at node 0, ``y = -T_w*n_l*h/s`` at the top node; tridiagonal (Thomas)
solve; hoop increment at mid layer; then the layer is appended at its wound-on stress. FIRST
ORDER in the layer thickness (the error falls as 1/layers). Cost O(layers^2): 150 layers about
0.05 s, 400 layers about 0.3 s.

Foil-bearing film [D, re-derived in SPEC19; formula quoted in SS-S58 EX/AB]: a web of tension
``T`` [N/m] wrapping a cylinder of radius ``R``, surfaces moving at ``U``, gas viscosity
``mu_g``: ``h0 = C*R*(6*mu_g*U/T)^(2/3)`` with ``C`` from ``H''' = (1 - H)/H^3`` (computed, not
typed). An UPPER BOUND: smooth, wide, impermeable web, no side leakage, no roughness venting.
"""
import math

STATUS = 'UNVALIDATED_WOUND_ROLL_ACCRETION_MODEL'
RADIAL_LAWS = ('constant', 'ratio_of_hoop_modulus', 'pfeiffer')
AMBIENT_PRESSURE_PA = 101325.0
AIR_VISCOSITY_PA_S = 1.8e-5          # [M: textbook value, not in the reports]
FLAG_HOOP_COMPRESSION = 'INNER_LAPS_IN_HOOP_COMPRESSION'
FLAG_LUMPED = 'LUMPED_LAYERS_FIRST_ORDER'
FLAG_STACK_LAW = 'RADIAL_STACK_LAW_IS_AN_INPUT_NO_ALUMINIUM_DATA_FOUND'
STACK_LAW_REQUIRED = (
    'radial_law is required and has no default: no radial stack stiffness of wound aluminium '
    'foil is published. Measure it with a press test on a stack of 50 to 200 laps of the oily '
    'foil (pressure against strain gives K1 and K2 of {"kind": "pfeiffer", "k1_pa", "k2"}), or '
    'enter {"kind": "constant", "radial_modulus_pa"} or {"kind": "ratio_of_hoop_modulus", '
    '"ratio"} as a stated assumption.')
BASIS = ('[D, re-derived in SPEC19] axisymmetric accretion: r^2*y\'\' + 3*r*y\' - (E_t/E_r - 1)*y '
         '= 0 per added layer, y(s) = -T_w*n_l*h/s, core r_c*y\' = y*(E_t/E_c - 1 + nu); laps '
         'lumped into layers (first order in the layer thickness)')
LIMITATIONS = (
    'Elastic laps (the lane model of package 10 adds a plastic strain).',
    'Plane model per lane: no axial stress, no coupling across the width in this module.',
    'No interlayer slip; no telescoping or V-buckle margin.',
    'The radial stack law is supplied: no measured value for oily aluminium foil exists; the '
    'result depends on it strongly.',
    'Laps are lumped into layers: first order in the layer thickness.',
    'No thermal or creep term; the air gap enters the radial stiffness only, not the radius.',
)
_C_CACHE = {}


def _num(name, value, lo=None, hi=None, positive=False, lo_open=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    v = float(value)
    if positive and v <= 0:
        raise ValueError(f'{name} must be positive')
    if lo is not None and (v < lo or (lo_open and v == lo)):
        raise ValueError(f'{name} must be {">" if lo_open else ">="} {lo}')
    if hi is not None and v > hi:
        raise ValueError(f'{name} must be <= {hi}')
    return v


def validate_radial_law(law):
    """The radial stack law as a validated dict (``ValueError`` names what to measure)."""
    if not isinstance(law, dict) or law.get('kind') not in RADIAL_LAWS:
        raise ValueError(STACK_LAW_REQUIRED)
    k = law['kind']
    if k == 'constant':
        if set(law) != {'kind', 'radial_modulus_pa'}:
            raise ValueError('radial_law constant needs radial_modulus_pa only')
        return {'kind': k, 'radial_modulus_pa': _num('radial_law.radial_modulus_pa',
                                                     law['radial_modulus_pa'], positive=True,
                                                     hi=1e12)}
    if k == 'ratio_of_hoop_modulus':
        if set(law) != {'kind', 'ratio'}:
            raise ValueError('radial_law ratio_of_hoop_modulus needs ratio only')
        return {'kind': k, 'ratio': _num('radial_law.ratio', law['ratio'], lo=1.0, hi=1e4)}
    if set(law) != {'kind', 'k1_pa', 'k2'}:
        raise ValueError('radial_law pfeiffer needs k1_pa and k2')
    return {'kind': k, 'k1_pa': _num('radial_law.k1_pa', law['k1_pa'], positive=True, hi=1e8),
            'k2': _num('radial_law.k2', law['k2'], positive=True, hi=1e4)}


def radial_modulus_pa(law, pressure_pa, *, hoop_modulus_pa, thickness_m=None,
                      air_gap_m=0.0) -> float:
    """Radial stack modulus at the pressure present, with the air layer in series."""
    law = validate_radial_law(law)
    p = max(0.0, float(pressure_pa))
    if law['kind'] == 'constant':
        er = law['radial_modulus_pa']
    elif law['kind'] == 'ratio_of_hoop_modulus':
        er = hoop_modulus_pa / law['ratio']
    else:
        er = law['k2'] * (p + law['k1_pa'])
    if air_gap_m:
        if thickness_m is None:
            raise ValueError('thickness_m is required with an air gap')
        g = air_gap_m * AMBIENT_PRESSURE_PA / (p + AMBIENT_PRESSURE_PA)
        h = thickness_m
        er = 1.0 / ((h / (h + g)) / er + (g / (h + g)) / (p + AMBIENT_PRESSURE_PA))
    return er


def _thomas(a, b, c, d):
    n = len(b)
    cp, dp = [0.0] * n, [0.0] * n
    if b[0] == 0:
        raise ArithmeticError('zero pivot at the core')
    cp[0] = c[0] / b[0]
    dp[0] = d[0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        if m == 0 or not math.isfinite(m):
            raise ArithmeticError(f'zero or non-finite pivot at node {i}')
        cp[i] = c[i] / m if i < n - 1 else 0.0
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m
    x = [0.0] * n
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


class WoundLane:
    """One lane wound layer by layer. Arrays: ``r`` (undeformed node radii, layer tops; node 0
    the core surface), ``radial_stress`` (nodes), ``hoop_stress``, ``wound_on``,
    ``plastic_strain`` (layers), ``displacement`` (nodes)."""

    def __init__(self, *, core_radius_m, thickness_m, laps_per_layer, hoop_modulus_pa,
                 poisson_ratio, radial_law, core_stiffness_pa=None, air_gap_m=0.0):
        self.rc = _num('core_radius_m', core_radius_m, positive=True, hi=5.0)
        self.h = _num('thickness_m', thickness_m, positive=True, hi=0.01)
        self.nl = _num('laps_per_layer', laps_per_layer, lo=1.0, hi=1e6)
        self.Et = _num('hoop_modulus_pa', hoop_modulus_pa, positive=True, hi=1e13)
        self.nu = _num('poisson_ratio', poisson_ratio, lo=0.0, hi=0.499)
        self.law = validate_radial_law(radial_law)
        self.Ec = (None if core_stiffness_pa is None else
                   _num('core_stiffness_pa', core_stiffness_pa, positive=True, hi=1e13))
        self.gap = _num('air_gap_m', air_gap_m, lo=0.0, hi=1e-4)
        self.d = self.nl * self.h
        self.r = [self.rc]
        self.radial_stress = [0.0]
        self.hoop_stress = []
        self.wound_on = []
        self.plastic_strain = []
        self.displacement = [0.0]

    @property
    def outer_radius_m(self):
        return self.r[-1] + self.displacement[-1]

    def _er(self, p):
        return radial_modulus_pa(self.law, p, hoop_modulus_pa=self.Et, thickness_m=self.h,
                                 air_gap_m=self.gap)

    def add_layer(self, tension_pa, plastic_strain=0.0):
        t = _num('tension_pa', tension_pa, lo=0.0, hi=5e9)
        n = len(self.r) - 1
        s = self.r[-1] + self.d
        top = -t * self.d / s
        dl = self.d
        if n == 0:
            ds = [top]
            dst = []
            du = [ds[0] * self.rc / self.Ec if self.Ec else 0.0]
        else:
            N = n + 1
            a, b, c, d = [0.0] * N, [0.0] * N, [0.0] * N, [0.0] * N
            k = (self.Et / self.Ec if self.Ec else 0.0) - 1 + self.nu
            b[0] = -self.rc / dl - k
            c[0] = self.rc / dl
            for i in range(1, n):
                r = self.r[i]
                g2 = self.Et / self._er(-self.radial_stress[i])
                a[i] = r * r / dl ** 2 - 1.5 * r / dl
                b[i] = -2 * r * r / dl ** 2 - (g2 - 1)
                c[i] = r * r / dl ** 2 + 1.5 * r / dl
            b[n] = 1.0
            d[n] = top
            ds = _thomas(a, b, c, d)
            dst = []
            for i in range(n):
                rm = 0.5 * (self.r[i] + self.r[i + 1])
                dst.append(0.5 * (ds[i] + ds[i + 1]) + rm * (ds[i + 1] - ds[i]) / dl)
            du = []
            for i in range(N):
                if i == 0:
                    der = (ds[1] - ds[0]) / dl
                elif i == n:
                    der = (ds[n] - ds[n - 1]) / dl
                else:
                    der = (ds[i + 1] - ds[i - 1]) / (2 * dl)
                r = self.r[i]
                du.append(r * ((ds[i] + r * der) / self.Et - self.nu * ds[i] / self.Et))
        for i, v in enumerate(ds):
            self.radial_stress[i] += v
            self.displacement[i] += du[i]
        for i, v in enumerate(dst):
            self.hoop_stress[i] += v
        self.r.append(s)
        self.radial_stress.append(0.0)
        self.hoop_stress.append(t)
        self.wound_on.append(t)
        self.plastic_strain.append(float(plastic_strain))
        self.displacement.append(self.displacement[-1])
        self.last_increment = {'radial': ds, 'top': top, 'outer_radius_m': s}
        return ds


def _taper(points, radius):
    if not points:
        return None
    pts = sorted(points)
    if radius <= pts[0][0]:
        return pts[0][1]
    if radius >= pts[-1][0]:
        return pts[-1][1]
    for (r0, t0), (r1, t1) in zip(pts, pts[1:]):
        if r0 <= radius <= r1:
            return t0 + (t1 - t0) * (radius - r0) / (r1 - r0)
    return pts[-1][1]


def wind_uniform(*, core_radius_m, outer_radius_m, thickness_m, winding_tension_pa,
                 hoop_modulus_pa, poisson_ratio, radial_law, core_stiffness_pa=None,
                 layers=150, air_gap_m=0.0, tension_taper=None) -> dict:
    """A uniform strip wound from the core to ``outer_radius_m`` in ``layers`` lumped layers.

    ``radial_law`` is REQUIRED (``validate_radial_law``; no default). ``tension_taper``: list of
    ``(radius_m, tension_pa)`` points, linear between them, end values held. Radial stress is
    given at the node radii (layer tops, ``node_radius_m``), hoop and wound-on stress at the
    layer mid radii (``radius_m``). A failed solve returns ``status`` ``SOLVE_FAILED``.
    """
    rc = _num('core_radius_m', core_radius_m, positive=True, hi=5.0)
    R = _num('outer_radius_m', outer_radius_m, positive=True, hi=5.0)
    if R <= rc:
        raise ValueError('outer_radius_m must exceed core_radius_m')
    h = _num('thickness_m', thickness_m, positive=True, hi=0.01)
    tw = _num('winding_tension_pa', winding_tension_pa, lo=0.0, hi=5e9)
    if isinstance(layers, bool) or not isinstance(layers, int) or not 1 <= layers <= 2000:
        raise ValueError('layers must be an integer in [1, 2000]')
    taper = None
    if tension_taper is not None:
        if not isinstance(tension_taper, (list, tuple)) or len(tension_taper) < 2:
            raise ValueError('tension_taper needs at least two (radius_m, tension_pa) points')
        taper = [(_num('tension_taper radius', p[0], positive=True, hi=5.0),
                  _num('tension_taper tension', p[1], lo=0.0, hi=5e9)) for p in tension_taper]
    laps = (R - rc) / h
    nl = laps / layers
    lane = WoundLane(core_radius_m=rc, thickness_m=h, laps_per_layer=max(1.0, nl),
                     hoop_modulus_pa=hoop_modulus_pa, poisson_ratio=poisson_ratio,
                     radial_law=radial_law, core_stiffness_pa=core_stiffness_pa,
                     air_gap_m=air_gap_m)
    base = {'status': STATUS, 'basis': BASIS, 'limitations': list(LIMITATIONS),
            'radial_law': lane.law, 'laps': laps, 'laps_per_layer': lane.nl, 'layers': layers}
    try:
        for _ in range(layers):
            mid = lane.r[-1] + lane.d / 2
            t = tw if taper is None else _taper(taper, mid)
            lane.add_layer(t)
    except ArithmeticError as exc:
        return dict(base, status='SOLVE_FAILED', reason=str(exc), layers_wound=len(lane.wound_on),
                    flags=[FLAG_STACK_LAW, FLAG_LUMPED])
    mids = [0.5 * (a + b) for a, b in zip(lane.r, lane.r[1:])]
    flags = [FLAG_STACK_LAW, FLAG_LUMPED]
    if min(lane.hoop_stress) < 0:
        flags.append(FLAG_HOOP_COMPRESSION)
    return dict(base, node_radius_m=list(lane.r), radial_stress_pa=list(lane.radial_stress),
                radius_m=mids, hoop_stress_pa=list(lane.hoop_stress),
                wound_on_tension_pa=list(lane.wound_on),
                radial_displacement_m=list(lane.displacement),
                outer_radius_m=lane.outer_radius_m,
                max_pressure_pa=max(-v for v in lane.radial_stress),
                min_hoop_stress_pa=min(lane.hoop_stress), flags=flags)


def isotropic_rigid_core_closed_form(radius_m, core_radius_m, outer_radius_m, tension_pa,
                                     poisson_ratio) -> tuple:
    """(sigma_r, sigma_t) at ``radius_m`` for E_r = E_t, a rigid core and constant tension."""
    r, rc, R, tw, nu = radius_m, core_radius_m, outer_radius_m, tension_pa, poisson_ratio
    beta = (1 - nu) / (1 + nu)
    L = math.log((R * R + beta * rc * rc) / (r * r + beta * rc * rc))
    return (-(tw / 2) * (1 + beta * rc * rc / r ** 2) * L,
            tw - (tw / 2) * (1 - beta * rc * rc / r ** 2) * L)


def foil_bearing_constant(eps=1e-6, step=1e-3, h_max=1e4) -> float:
    """``C`` of ``h0 = C*R*(6*mu*U/T)^(2/3)``: integrate ``H''' = (1 - H)/H^3`` from
    ``H = 1 + eps*exp(-xi)`` towards ``-xi`` (RK4) until ``H > h_max``; the curvature there."""
    key = (eps, step, h_max)
    if key in _C_CACHE:
        return _C_CACHE[key]
    y = [1 + eps, -eps, eps]

    def f(v):
        return [v[1], v[2], (1 - v[0]) / v[0] ** 3]
    hs = -step
    n = 0
    while y[0] < h_max and n < 10 ** 7:
        k1 = f(y)
        k2 = f([a + 0.5 * hs * b for a, b in zip(y, k1)])
        k3 = f([a + 0.5 * hs * b for a, b in zip(y, k2)])
        k4 = f([a + hs * b for a, b in zip(y, k3)])
        y = [a + hs * (b + 2 * c + 2 * d + e) / 6 for a, b, c, d, e in zip(y, k1, k2, k3, k4)]
        n += 1
    _C_CACHE[key] = y[2]
    return y[2]


def entrained_air_film_m(radius_m, surface_speed_sum_m_s, tension_per_width_n_m,
                         viscosity_pa_s=AIR_VISCOSITY_PA_S) -> float:
    """Foil-bearing air film on a cylinder: an UPPER BOUND (smooth, wide, impermeable web, no
    side leakage) [D, re-derived in SPEC19; SS-S58 EX/AB]."""
    R = _num('radius_m', radius_m, positive=True, hi=5.0)
    U = _num('surface_speed_sum_m_s', surface_speed_sum_m_s, positive=True, hi=200.0)
    T = _num('tension_per_width_n_m', tension_per_width_n_m, positive=True, hi=1e7)
    mu = _num('viscosity_pa_s', viscosity_pa_s, positive=True, hi=1.0)
    return foil_bearing_constant() * R * (6 * mu * U / T) ** (2 / 3)
