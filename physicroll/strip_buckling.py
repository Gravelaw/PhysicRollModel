"""Linear buckling of a long strip with a longitudinal stress profile across the width.

SPEC19 package 6 (gap G4, first part; G16). UNVALIDATED. Standard library only.

Model [D, re-derived in SPEC19; the reports describe the method (SS-S15 EX, SS-S12 AB) and give
no equations]. Long strip, ``x`` along rolling, ``z`` across the width on ``[z_a, z_b]``,
thickness ``t``, bending stiffness ``D = E*t^3/(12*(1 - nu^2))``. Membrane pre-stress,
longitudinal only: ``sigma(z) = sigma_T + lambda*sigma_res(z)`` (tension positive; no lateral
and no shear pre-stress). Mode ``w(x, z) = f(z)*cos(k*x)``. Second variation of the potential
energy per unit length, averaged over ``x`` (a factor 1/4 dropped)::

    P(f, k) = D*Int[ f''^2 + k^4*f^2 - 2*nu*k^2*f*f'' + 2*(1 - nu)*k^2*f'^2 ] dz
            + t*k^2*Int[ sigma(z)*f^2 ] dz

from ``w_xx = -k^2*f*cos``, ``w_zz = f''*cos``, ``w_xz = -k*f'*sin`` in the plate energy
``(D/2)*[(w_xx + w_zz)^2 - 2*(1 - nu)*(w_xx*w_zz - w_xz^2)]`` and the membrane term
``(t/2)*sigma*w_x^2``. The ``f*f''`` and ``f'^2`` terms are kept as they stand: their sum is a
boundary term that vanishes for supported edges and not for free ones. Critical multiplier at one
``k``: the smallest positive ``lambda`` of ``A(k)*a = lambda*G(k)*a``, ``A`` = bending plus
``t*k^2*sigma_T*Int f^2`` (positive definite for ``k > 0``, ``sigma_T >= 0``),
``G = -t*k^2*Int sigma_res*f^2`` (indefinite). Critical state: the minimum over ``k``.

Method. Hermite cubic elements between the given nodes (unknowns ``f`` and ``f'`` per node);
``sigma_res`` linear inside an element; element integrals by 4-point Gauss quadrature (exact for
these polynomials). Edges: ``'free'``, ``'simply_supported'`` (``f = 0``), ``'clamped'``
(``f = f' = 0``). Symmetric banded storage, half bandwidth 3. The largest eigenvalue ``mu`` of
``G*a = mu*A*a`` by bisection on the inertia (Sylvester: the number of eigenvalues above ``mu``
equals the number of positive pivots of the ``L*D*L^T`` factors of ``G - mu*A``; banded, no
pivoting; a zero pivot is replaced by 1e-300), relative tolerance 1e-6; ``lambda = 1/mu``.
Search over ``k``: ``coarse`` values geometric between ``pi/L_long`` and ``pi/L_short``, then
golden section in ``ln k`` between the neighbours of the best (``refine`` steps). Mode: three
inverse iterations from a fixed start vector. Cost: one factorisation is O(n) with n the number
of nodes; one critical-mode search with 120 nodes takes about 0.2-0.3 s.

Closed forms recovered (tests/test_strip_buckling.py): uniform compression of a long plate with
simply supported edges, ``4*pi^2*D/(t*b^2)`` and half-wave ``b``; the same with a tension, the
critical stress shifted by exactly the tension; clamped edges, coefficient 6.97 and half-wave
0.66 b [M: textbook values, not in the reports]; simply supported / free at a fixed half-wave
of 20 b, ``0.425 + (b/a)^2`` [M].
"""
import math

STATUS = 'UNVALIDATED_LINEAR_BUCKLING_OF_A_LONG_STRIP'
EDGES = ('free', 'simply_supported', 'clamped')
NO_BUCKLING = 'NO_COMPRESSION_NO_BUCKLING'
FLAG_LONGEST = 'BUCKLING_MODE_AT_LONGEST_HALF_WAVE_SEARCHED'
FLAG_SHORTEST = 'BUCKLING_MODE_AT_SHORTEST_HALF_WAVE_SEARCHED'
BASIS = ('[D, re-derived in SPEC19] second variation of the plate energy of a long flat strip '
         'with a longitudinal pre-stress sigma_T + lambda*sigma_res(z), mode f(z)*cos(k*x); '
         'Hermite cubic elements across the width, exact 4-point Gauss integrals; largest '
         'eigenvalue by inertia bisection (relative tolerance as given); minimum over k by a '
         'geometric scan and a golden section in ln k')
LIMITATIONS = (
    'Linear bifurcation of a flat, infinitely long strip: no amplitude, no post-buckling.',
    'Longitudinal pre-stress only: no lateral stress, no shear.',
    'Elastic.',
    'The wavelength of a wave seen after buckling can differ from the critical one.',
)
_GP = [(0.5 - math.sqrt(3 / 7 + 2 / 7 * math.sqrt(6 / 5)) / 2, (18 - math.sqrt(30)) / 72),
       (0.5 - math.sqrt(3 / 7 - 2 / 7 * math.sqrt(6 / 5)) / 2, (18 + math.sqrt(30)) / 72),
       (0.5 + math.sqrt(3 / 7 - 2 / 7 * math.sqrt(6 / 5)) / 2, (18 + math.sqrt(30)) / 72),
       (0.5 + math.sqrt(3 / 7 + 2 / 7 * math.sqrt(6 / 5)) / 2, (18 - math.sqrt(30)) / 72)]
_BW = 4   # stored band width (half bandwidth 3)


def _shape(xi, L):
    N = [1 - 3 * xi ** 2 + 2 * xi ** 3, L * (xi - 2 * xi ** 2 + xi ** 3), 3 * xi ** 2 - 2 * xi ** 3,
         L * (-xi ** 2 + xi ** 3)]
    d1 = [(-6 * xi + 6 * xi ** 2) / L, (1 - 4 * xi + 3 * xi ** 2), (6 * xi - 6 * xi ** 2) / L,
          (-2 * xi + 3 * xi ** 2)]
    d2 = [(-6 + 12 * xi) / L ** 2, (-4 + 6 * xi) / L, (6 - 12 * xi) / L ** 2, (-2 + 6 * xi) / L]
    return N, d1, d2


def _tables(L):
    m00 = [[0.0] * 4 for _ in range(4)]
    m11 = [[0.0] * 4 for _ in range(4)]
    m22 = [[0.0] * 4 for _ in range(4)]
    m02 = [[0.0] * 4 for _ in range(4)]
    pts = []
    for xi, w in _GP:
        N, d1, d2 = _shape(xi, L)
        pts.append((xi, w, N))
        for i in range(4):
            for j in range(4):
                m00[i][j] += w * L * N[i] * N[j]
                m11[i][j] += w * L * d1[i] * d1[j]
                m22[i][j] += w * L * d2[i] * d2[j]
                m02[i][j] += w * L * 0.5 * (N[i] * d2[j] + N[j] * d2[i])
    return m00, m11, m22, m02, pts


class _Strip:
    def __init__(self, z, s, t, E, nu, sigma_t, edges):
        self.z, self.s, self.t, self.E, self.nu, self.sT = z, s, t, E, nu, sigma_t
        self.D = E * t ** 3 / (12 * (1 - nu * nu))
        n = len(z)
        fixed = set()
        for end, node in ((edges[0], 0), (edges[1], n - 1)):
            if end in ('simply_supported', 'clamped'):
                fixed.add(2 * node)
            if end == 'clamped':
                fixed.add(2 * node + 1)
        self.free = [d for d in range(2 * n) if d not in fixed]
        self.map = {d: i for i, d in enumerate(self.free)}
        self.nd = len(self.free)
        cache = {}
        self.el = []
        for e in range(n - 1):
            L = z[e + 1] - z[e]
            key = round(L, 15)
            if key not in cache:
                cache[key] = _tables(L)
            m00, m11, m22, m02, pts = cache[key]
            sa, sb = s[e], s[e + 1]
            ms = [[0.0] * 4 for _ in range(4)]
            for xi, w, N in pts:
                sg = sa + (sb - sa) * xi
                for i in range(4):
                    for j in range(4):
                        ms[i][j] += w * L * sg * N[i] * N[j]
            self.el.append((m00, m11, m22, m02, ms))

    def assemble(self, k):
        nd = self.nd
        A = [[0.0] * _BW for _ in range(nd)]
        G = [[0.0] * _BW for _ in range(nd)]
        D, t, nu, sT = self.D, self.t, self.nu, self.sT
        k2, k4 = k * k, k ** 4
        for e, (m00, m11, m22, m02, ms) in enumerate(self.el):
            dofs = (2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3)
            for i in range(4):
                gi = self.map.get(dofs[i])
                if gi is None:
                    continue
                for j in range(4):
                    gj = self.map.get(dofs[j])
                    if gj is None or gj > gi:
                        continue
                    a = (D * (m22[i][j] + k4 * m00[i][j] - 2 * nu * k2 * m02[i][j]
                              + 2 * (1 - nu) * k2 * m11[i][j]) + t * k2 * sT * m00[i][j])
                    A[gi][gi - gj] += a
                    G[gi][gi - gj] += -t * k2 * ms[i][j]
        return A, G


def _count_positive(A, G, mu):
    """Positive pivots of LDL^T of (G - mu*A), banded, no pivoting (Sylvester inertia)."""
    n = len(A)
    Lb = [[0.0] * _BW for _ in range(n)]
    d = [0.0] * n
    pos = 0
    for i in range(n):
        for off in range(min(_BW - 1, i), -1, -1):
            j = i - off
            s = G[i][off] - mu * A[i][off]
            for m in range(max(0, i - _BW + 1), j):
                if j - m < _BW:
                    s -= Lb[i][i - m] * d[m] * Lb[j][j - m]
            if off:
                Lb[i][off] = s / d[j]
            else:
                d[i] = s if s != 0.0 else 1e-300
                if d[i] > 0:
                    pos += 1
    return pos


def _mu_max(A, G, hi, tol):
    if _count_positive(A, G, hi * 1e-12) == 0:
        return 0.0
    lo = 0.0
    while _count_positive(A, G, hi) > 0:
        hi *= 2
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _count_positive(A, G, mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo <= tol * hi:
            break
    return 0.5 * (lo + hi)


def _band_solve(Mb, rhs):
    """Banded symmetric (lower rows) system by Gaussian elimination with partial pivoting."""
    n = len(Mb)
    p = _BW - 1
    ab = [[0.0] * (3 * p + 1) for _ in range(n)]
    for i in range(n):
        for off in range(min(p, i) + 1):
            j = i - off
            v = Mb[i][off]
            ab[i][j - i + p] = v
            ab[j][i - j + p] = v
    b = rhs[:]
    for c in range(n):
        piv = max(range(c, min(n, c + p + 1)), key=lambda r: abs(ab[r][c - r + p]))
        if piv != c:
            rc = {c + (o - p): ab[c][o] for o in range(3 * p + 1)}
            rp = {piv + (o - p): ab[piv][o] for o in range(3 * p + 1)}
            ab[c] = [rp.get(c + (o - p), 0.0) for o in range(3 * p + 1)]
            ab[piv] = [rc.get(piv + (o - p), 0.0) for o in range(3 * p + 1)]
            b[c], b[piv] = b[piv], b[c]
        d = ab[c][p]
        if d == 0.0:
            d = ab[c][p] = 1e-300
        for r in range(c + 1, min(n, c + p + 1)):
            f = ab[r][c - r + p] / d
            if f:
                for col in range(c, min(n, c + 2 * p + 1)):
                    ab[r][col - r + p] -= f * ab[c][col - c + p]
                b[r] -= f * b[c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = b[i]
        for col in range(i + 1, min(n, i + 2 * p + 1)):
            s -= ab[i][col - i + p] * x[col]
        x[i] = s / ab[i][p]
    return x


def _band_mul(Mb, x):
    n = len(Mb)
    y = [0.0] * n
    for i in range(n):
        for off in range(min(_BW - 1, i) + 1):
            j = i - off
            v = Mb[i][off]
            y[i] += v * x[j]
            if off:
                y[j] += v * x[i]
    return y


def _mode(A, G, mu, iters=3):
    n = len(A)
    Sb = [[G[i][o] - mu * (1 + 1e-7) * A[i][o] for o in range(_BW)] for i in range(n)]
    x = [math.sin(1.0 + 0.7 * i) for i in range(n)]
    for _ in range(iters):
        x = _band_solve(Sb, _band_mul(A, x))
        nrm = max(abs(v) for v in x)
        x = [v / nrm for v in x]
    return x


def _number(name, value, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
            or not lo <= value <= hi:
        raise ValueError(f'{name} must be a finite number in [{lo}, {hi}]')
    return float(value)


def _check(z_m, residual_stress_pa, thickness_m, youngs_modulus_pa, poisson_ratio,
           mean_tension_pa, edges):
    if not isinstance(z_m, (list, tuple)) or not 3 <= len(z_m) <= 400:
        raise ValueError('z_m must be a list of 3 to 400 nodes')
    z = [_number('z_m', v, -1e3, 1e3) for v in z_m]
    if any(b <= a for a, b in zip(z, z[1:])):
        raise ValueError('z_m must be strictly increasing')
    if not isinstance(residual_stress_pa, (list, tuple)) or len(residual_stress_pa) != len(z):
        raise ValueError('residual_stress_pa must have one value per node')
    s = [_number('residual_stress_pa', v, -5e9, 5e9) for v in residual_stress_pa]
    t = _number('thickness_m', thickness_m, 1e-7, 0.1)
    if t == 0:
        raise ValueError('thickness_m must be positive')
    E = _number('youngs_modulus_pa', youngs_modulus_pa, 1e8, 1e13)
    nu = _number('poisson_ratio', poisson_ratio, 0.0, 0.499)
    sT = _number('mean_tension_pa', mean_tension_pa, 0.0, 2e9)
    if not isinstance(edges, (list, tuple)) or len(edges) != 2 or any(e not in EDGES for e in edges):
        raise ValueError(f'edges must be two of {EDGES}')
    return z, s, t, E, nu, sT, tuple(edges)


def _hi(strip, k):
    qmax = max(-v for v in strip.s)
    return qmax / (strip.D * k * k / strip.t + strip.sT) if qmax > 0 else 1.0


def multiplier_at(z_m, residual_stress_pa, wavenumber_per_m, *, thickness_m, youngs_modulus_pa,
                  poisson_ratio, mean_tension_pa=0.0, edges=('free', 'free'),
                  tolerance=1e-6) -> dict:
    """Critical multiplier of ``residual_stress_pa`` at one wavenumber (``None``: no buckling)."""
    z, s, t, E, nu, sT, edges = _check(z_m, residual_stress_pa, thickness_m, youngs_modulus_pa,
                                       poisson_ratio, mean_tension_pa, edges)
    k = _number('wavenumber_per_m', wavenumber_per_m, 1e-6, 1e9)
    if k <= 0:
        raise ValueError('wavenumber_per_m must be positive')
    strip = _Strip(z, s, t, E, nu, sT, edges)
    if max(-v for v in s) <= 0:
        return {'status': NO_BUCKLING, 'critical_multiplier': None, 'wavenumber_per_m': k,
                'half_wavelength_m': math.pi / k}
    A, G = strip.assemble(k)
    mu = _mu_max(A, G, _hi(strip, k), tolerance)
    return {'status': STATUS if mu > 0 else NO_BUCKLING,
            'critical_multiplier': 1 / mu if mu > 0 else None, 'wavenumber_per_m': k,
            'half_wavelength_m': math.pi / k}


def _extent(z, f, level):
    idx = [i for i, v in enumerate(f) if abs(v) >= level]
    return z[idx[-1]] - z[idx[0]]


def critical_mode(z_m, residual_stress_pa, *, thickness_m, youngs_modulus_pa, poisson_ratio,
                  mean_tension_pa=0.0, edges=('free', 'free'), half_wave_range_m=None,
                  coarse=14, refine=10, tolerance=1e-6) -> dict:
    """The smallest critical multiplier over the wavenumber, its half-wave and its mode.

    ``residual_stress_pa`` is the longitudinal stress profile at the nodes (tension positive)
    that is scaled; ``mean_tension_pa`` is held fixed. ``utilisation`` = 1/multiplier: at or
    above 1 the given profile buckles.
    """
    z, s, t, E, nu, sT, edges = _check(z_m, residual_stress_pa, thickness_m, youngs_modulus_pa,
                                       poisson_ratio, mean_tension_pa, edges)
    if isinstance(coarse, bool) or not isinstance(coarse, int) or not 4 <= coarse <= 40:
        raise ValueError('coarse must be an integer in [4, 40]')
    if isinstance(refine, bool) or not isinstance(refine, int) or not 0 <= refine <= 30:
        raise ValueError('refine must be an integer in [0, 30]')
    tol = _number('tolerance', tolerance, 1e-12, 1e-2)
    width = z[-1] - z[0]
    if half_wave_range_m is None:
        spacing = min(b - a for a, b in zip(z, z[1:]))
        l_short, l_long = 4 * spacing, 2 * width
    else:
        if not isinstance(half_wave_range_m, (list, tuple)) or len(half_wave_range_m) != 2:
            raise ValueError('half_wave_range_m must be (shortest, longest)')
        l_short = _number('half_wave_range_m', half_wave_range_m[0], 1e-9, 1e4)
        l_long = _number('half_wave_range_m', half_wave_range_m[1], 1e-9, 1e4)
        if not 0 < l_short < l_long:
            raise ValueError('half_wave_range_m must be 0 < shortest < longest')
    base = {'edges': list(edges), 'basis': BASIS, 'limitations': list(LIMITATIONS),
            'mean_tension_pa': sT, 'half_wave_range_m': [l_short, l_long]}
    if max(-v for v in s) <= 0:
        return dict(base, status=NO_BUCKLING, critical_multiplier=None, utilisation=0.0,
                    flags=[], scan=[], at_search_limit=None)
    strip = _Strip(z, s, t, E, nu, sT, edges)
    cache = {}

    def lam_of(k):
        if k not in cache:
            A, G = strip.assemble(k)
            mu = _mu_max(A, G, _hi(strip, k), tol)
            cache[k] = (1 / mu if mu > 0 else math.inf, A, G, mu)
        return cache[k]

    k_lo, k_hi = math.pi / l_long, math.pi / l_short
    ks = [k_lo * (k_hi / k_lo) ** (i / (coarse - 1)) for i in range(coarse)]
    vals = [lam_of(k)[0] for k in ks]
    scan = [{'half_wavelength_m': math.pi / k, 'critical_multiplier': (v if math.isfinite(v)
                                                                       else None)}
            for k, v in zip(ks, vals)]
    if not any(math.isfinite(v) for v in vals):
        return dict(base, status=NO_BUCKLING, critical_multiplier=None, utilisation=0.0,
                    flags=[], scan=scan, at_search_limit=None)
    i = min(range(coarse), key=lambda j: vals[j])
    a, b = ks[max(0, i - 1)], ks[min(coarse - 1, i + 1)]
    gr = (math.sqrt(5) - 1) / 2
    la, lb = math.log(a), math.log(b)
    c, d = lb - gr * (lb - la), la + gr * (lb - la)
    fc, fd = lam_of(math.exp(c))[0], lam_of(math.exp(d))[0]
    for _ in range(refine):
        if fc < fd:
            lb, d, fd = d, c, fc
            c = lb - gr * (lb - la)
            fc = lam_of(math.exp(c))[0]
        else:
            la, c, fc = c, d, fd
            d = la + gr * (lb - la)
            fd = lam_of(math.exp(d))[0]
    cands = [(fc, math.exp(c)), (fd, math.exp(d)), (vals[i], ks[i])]
    lam, k = min(cands)
    lam, A, G, mu = lam_of(k)
    x = _mode(A, G, mu)
    n = len(z)
    f, fp = [0.0] * n, [0.0] * n
    for dof, j in strip.map.items():
        if dof % 2 == 0:
            f[dof // 2] = x[j]
        else:
            fp[dof // 2] = x[j]
    m = max(f, key=abs)
    f = [v / m for v in f]
    fp = [v / m for v in fp]
    ipk = max(range(n), key=lambda j: abs(f[j]))
    w10 = _extent(z, f, 0.1)
    limit = 'LONGEST' if i == 0 and k == ks[0] else (
        'SHORTEST' if i == coarse - 1 and k == ks[-1] else None)
    flags = [FLAG_LONGEST] if limit == 'LONGEST' else ([FLAG_SHORTEST] if limit == 'SHORTEST'
                                                       else [])
    half = math.pi / k
    return dict(base, status=STATUS, critical_multiplier=lam, utilisation=1 / lam,
                wavenumber_per_m=k, half_wavelength_m=half, mode=f, mode_slope=fp,
                mode_peak_position_m=z[ipk], mode_width_10_percent_m=w10,
                mode_width_50_percent_m=_extent(z, f, 0.5),
                half_wave_over_mode_width=(half / w10 if w10 > 0 else None), scan=scan,
                at_search_limit=limit, flags=flags)
