"""Buckling of a long strip with a longitudinal stress profile across the width (SPEC19 planner).
Mode w(x, z) = f(z)*cos(k*x); Hermite cubic elements in z; critical multiplier of the residual
stress at fixed mean tension by inertia bisection; one-term post-buckling."""
import math, time
GP = [(0.5 - math.sqrt(3/7 + 2/7*math.sqrt(6/5))/2, (18 - math.sqrt(30))/72),
      (0.5 - math.sqrt(3/7 - 2/7*math.sqrt(6/5))/2, (18 + math.sqrt(30))/72),
      (0.5 + math.sqrt(3/7 - 2/7*math.sqrt(6/5))/2, (18 + math.sqrt(30))/72),
      (0.5 + math.sqrt(3/7 + 2/7*math.sqrt(6/5))/2, (18 - math.sqrt(30))/72)]
def shape(xi, L):
    N = [1 - 3*xi**2 + 2*xi**3, L*(xi - 2*xi**2 + xi**3), 3*xi**2 - 2*xi**3, L*(-xi**2 + xi**3)]
    d1 = [(-6*xi + 6*xi**2)/L, (1 - 4*xi + 3*xi**2), (6*xi - 6*xi**2)/L, (-2*xi + 3*xi**2)]
    d2 = [(-6 + 12*xi)/L**2, (-4 + 6*xi)/L, (6 - 12*xi)/L**2, (-2 + 6*xi)/L]
    return N, d1, d2
_TAB = {}
def tables(L):
    key = round(L, 15)
    if key not in _TAB:
        m00 = [[0.0]*4 for _ in range(4)]; m11 = [[0.0]*4 for _ in range(4)]; m22 = [[0.0]*4 for _ in range(4)]; m02 = [[0.0]*4 for _ in range(4)]
        pts = []
        for xi, w in GP:
            N, d1, d2 = shape(xi, L)
            pts.append((xi, w, N))
            for i in range(4):
                for j in range(4):
                    m00[i][j] += w*L*N[i]*N[j]; m11[i][j] += w*L*d1[i]*d1[j]; m22[i][j] += w*L*d2[i]*d2[j]
                    m02[i][j] += w*L*0.5*(N[i]*d2[j] + N[j]*d2[i])
        _TAB[key] = (m00, m11, m22, m02, pts)
    return _TAB[key]
class Strip:
    """z nodes (uniform or not), sigma_res at nodes (linear in between), bc = (left, right)
    each 'free' | 'simply_supported' | 'clamped'."""
    def __init__(self, z, sig_res, t, E, nu, sigma_t, bc=('free', 'free')):
        self.z, self.s, self.t, self.E, self.nu, self.sT = z, sig_res, t, E, nu, sigma_t
        self.D = E*t**3/(12*(1 - nu*nu))
        n = len(z)
        fixed = set()
        for end, node in ((bc[0], 0), (bc[1], n - 1)):
            if end in ('simply_supported', 'clamped'): fixed.add(2*node)
            if end == 'clamped': fixed.add(2*node + 1)
        self.free = [d for d in range(2*n) if d not in fixed]
        self.map = {d: i for i, d in enumerate(self.free)}
        self.nd = len(self.free)
    def assemble(self, k):
        """Banded (half bandwidth 3, lower storage) A = bending + tension, G = -t k^2 * sigma_res."""
        nd = self.nd; bw = 4
        A = [[0.0]*bw for _ in range(nd)]; G = [[0.0]*bw for _ in range(nd)]
        D, t, nu, sT = self.D, self.t, self.nu, self.sT
        for e in range(len(self.z) - 1):
            L = self.z[e+1] - self.z[e]
            m00, m11, m22, m02, pts = tables(L)
            sa, sb = self.s[e], self.s[e+1]
            ms = [[0.0]*4 for _ in range(4)]
            for xi, w, N in pts:
                sg = sa + (sb - sa)*xi
                for i in range(4):
                    for j in range(4): ms[i][j] += w*L*sg*N[i]*N[j]
            dofs = [2*e, 2*e+1, 2*e+2, 2*e+3]
            for i in range(4):
                gi = self.map.get(dofs[i])
                if gi is None: continue
                for j in range(4):
                    gj = self.map.get(dofs[j])
                    if gj is None or gj > gi: continue
                    a = D*(m22[i][j] + k**4*m00[i][j] - 2*nu*k*k*m02[i][j] + 2*(1 - nu)*k*k*m11[i][j]) + t*k*k*sT*m00[i][j]
                    A[gi][gi - gj] += a
                    G[gi][gi - gj] += -t*k*k*ms[i][j]
        return A, G
def count_positive(A, G, mu):
    """Positive pivots of LDL^T of (G - mu*A), banded, no pivoting (Sylvester inertia)."""
    n = len(A); bw = len(A[0])
    Lb = [[0.0]*bw for _ in range(n)]; d = [0.0]*n; pos = 0
    for i in range(n):
        for off in range(min(bw - 1, i), -1, -1):
            j = i - off
            s = G[i][off] - mu*A[i][off]
            for m in range(max(0, i - bw + 1), j):
                s -= Lb[i][i - m]*d[m]*Lb[j][j - m] if (j - m) < bw else 0.0
            if off:
                Lb[i][off] = s/d[j]
            else:
                d[i] = s if s != 0.0 else 1e-300
                if d[i] > 0: pos += 1
    return pos
def mu_max(A, G, hi, tol=1e-6):
    if count_positive(A, G, hi*1e-12) == 0: return 0.0
    lo = 0.0
    while count_positive(A, G, hi) > 0: hi *= 2
    for _ in range(60):
        mid = 0.5*(lo + hi)
        if count_positive(A, G, mid) > 0: lo = mid
        else: hi = mid
        if hi - lo <= tol*hi: break
    return 0.5*(lo + hi)
def band_solve(Mb, rhs):
    """Solve a banded symmetric system given as lower band rows, by dense-in-band Gaussian elimination with partial pivoting."""
    n = len(Mb); bw = len(Mb[0]); p = bw - 1
    W = 2*p + 1 + p
    a = [[0.0]*n for _ in range(n)] if n <= 0 else None
    # general band storage: rows i, columns i-p .. i+2p
    ab = [[0.0]*(3*p + 1) for _ in range(n)]
    for i in range(n):
        for off in range(min(p, i) + 1):
            j = i - off; v = Mb[i][off]
            ab[i][j - i + p] = v
            ab[j][i - j + p] = v
    b = rhs[:]
    for c in range(n):
        piv = max(range(c, min(n, c + p + 1)), key=lambda r: abs(ab[r][c - r + p]))
        if piv != c:
            # swap rows c and piv (shift band offsets)
            rc = {c + (o - p): ab[c][o] for o in range(3*p + 1)}
            rp = {piv + (o - p): ab[piv][o] for o in range(3*p + 1)}
            ab[c] = [rp.get(c + (o - p), 0.0) for o in range(3*p + 1)]
            ab[piv] = [rc.get(piv + (o - p), 0.0) for o in range(3*p + 1)]
            b[c], b[piv] = b[piv], b[c]
        d = ab[c][p]
        if d == 0.0: d = ab[c][p] = 1e-300
        for r in range(c + 1, min(n, c + p + 1)):
            f = ab[r][c - r + p]/d
            if f:
                for col in range(c, min(n, c + 2*p + 1)):
                    ab[r][col - r + p] -= f*ab[c][col - c + p]
                b[r] -= f*b[c]
    x = [0.0]*n
    for i in range(n - 1, -1, -1):
        s = b[i]
        for col in range(i + 1, min(n, i + 2*p + 1)): s -= ab[i][col - i + p]*x[col]
        x[i] = s/ab[i][p]
    return x
def band_mul(Mb, x):
    n = len(Mb); bw = len(Mb[0]); y = [0.0]*n
    for i in range(n):
        for off in range(min(bw - 1, i) + 1):
            j = i - off; v = Mb[i][off]
            y[i] += v*x[j]
            if off: y[j] += v*x[i]
    return y
def mode(A, G, mu, iters=3):
    n = len(A)
    Sb = [[G[i][o] - mu*(1 + 1e-7)*A[i][o] for o in range(len(A[0]))] for i in range(n)]
    x = [math.sin(1.0 + 0.7*i) for i in range(n)]
    for _ in range(iters):
        x = band_solve(Sb, band_mul(A, x))
        nrm = max(abs(v) for v in x); x = [v/nrm for v in x]
    return x
def critical(strip, k_lo, k_hi, coarse=10, refine=8, tol=1e-5):
    """Smallest critical multiplier lambda over k and the mode. Returns dict."""
    qmax = max(-v for v in strip.s)
    if qmax <= 0: return None
    def lam_of(k):
        A, G = strip.assemble(k)
        hi = qmax/(strip.D*k*k/strip.t + strip.sT) if strip.sT > 0 or True else 1.0
        mu = mu_max(A, G, hi, tol)
        return (1/mu if mu > 0 else math.inf), A, G, mu
    ks = [k_lo*(k_hi/k_lo)**(i/(coarse - 1)) for i in range(coarse)]
    vals = [lam_of(k)[0] for k in ks]
    i = min(range(coarse), key=lambda j: vals[j])
    a, b = ks[max(0, i - 1)], ks[min(coarse - 1, i + 1)]
    gr = (math.sqrt(5) - 1)/2
    la, lb = math.log(a), math.log(b)
    c, d = lb - gr*(lb - la), la + gr*(lb - la)
    fc, fd = lam_of(math.exp(c))[0], lam_of(math.exp(d))[0]
    for _ in range(refine):
        if fc < fd: lb, d, fd = d, c, fc; c = lb - gr*(lb - la); fc = lam_of(math.exp(c))[0]
        else: la, c, fc = c, d, fd; d = la + gr*(lb - la); fd = lam_of(math.exp(d))[0]
    k = math.exp(c if fc < fd else d)
    lam, A, G, mu = lam_of(k)
    x = mode(A, G, mu)
    f = [0.0]*len(strip.z); fp = [0.0]*len(strip.z)
    for dof, i in strip.map.items():
        if dof % 2 == 0: f[dof//2] = x[i]
        else: fp[dof//2] = x[i]
    m = max(f, key=abs); f = [v/m for v in f]; fp = [v/m for v in fp]
    return {'lambda': lam, 'k': k, 'half_wavelength_m': math.pi/k, 'f': f, 'fp': fp, 'scan': list(zip(ks, vals))}
def post_buckling(strip, res, scale=1.0):
    """One-term amplitude and saturated stress for residual stress scale*sigma_res (scale/lambda > 1)."""
    z, f, k = strip.z, res['f'], res['k']
    W = z[-1] - z[0]
    def integ(g):
        return sum(0.5*(g[i] + g[i+1])*(z[i+1] - z[i]) for i in range(len(z) - 1))
    i2 = integ([v*v for v in f]); i4 = integ([v**4 for v in f])
    phi = i4 - i2*i2/W
    # N - R = (scale/lambda - 1) * R_total where R_total = -(integral of sigma_T f^2) ... use energy identity:
    # at criticality: integral (sigma_T + lam*s) f^2 * t k^2 + D*B = 0  ->  D*B/(t k^2) = -(sigma_T*i2 + lam*integ(s f^2))
    isf = integ([s*v*v for s, v in zip(strip.s, f)])
    R = -(strip.sT*i2 + res['lambda']*isf)
    Nn = -(strip.sT*i2 + scale*isf)
    if Nn <= R: return {'amplitude_m': 0.0}
    A2 = 4*(Nn - R)/(strip.E*k*k*phi)
    amp = math.sqrt(A2)
    sat = [strip.sT + scale*s + strip.E*k*k*A2/4*(v*v - i2/W) for s, v in zip(strip.s, f)]
    return {'amplitude_m': amp, 'peak_to_valley_m': 2*amp, 'saturated_stress_pa': sat, 'phi': phi, 'i2': i2}
if __name__ == '__main__':
    # closed form: uniformly compressed long plate, simply supported edges: sigma_cr = 4 pi^2 D/(t b^2), half-wave = b
    E, nu, t, b = 210e9, 0.3, 0.5e-3, 0.150
    D = E*t**3/(12*(1 - nu*nu)); exact = 4*math.pi**2*D/(t*b*b)
    for n in (8, 16, 32, 64):
        z = [b*i/n for i in range(n + 1)]
        st = Strip(z, [-1.0]*(n + 1), t, E, nu, 0.0, ('simply_supported', 'simply_supported'))
        t0 = time.perf_counter(); r = critical(st, math.pi/(4*b), math.pi/(b/4)); dt = time.perf_counter() - t0
        print(n, 'lambda', r['lambda'], 'exact', exact, 'rel err', r['lambda']/exact - 1, 'half wave/b', r['half_wavelength_m']/b, 'time', round(dt, 3))
    # fixed k = pi/b check
    n = 16; z = [b*i/n for i in range(n + 1)]
    st = Strip(z, [-1.0]*(n + 1), t, E, nu, 0.0, ('simply_supported', 'simply_supported'))
    A, G = st.assemble(math.pi/b); mu = mu_max(A, G, 1.0, 1e-10); print('k = pi/b: lambda', 1/mu, 'rel', 1/mu/exact - 1)
    # with tension 20 MPa: sigma_cr rises by exactly sigma_T (uniform mode), half-wave unchanged
    st = Strip(z, [-1.0]*(n + 1), t, E, nu, 20e6, ('simply_supported', 'simply_supported'))
    r = critical(st, math.pi/(4*b), math.pi/(b/4)); print('tension: lambda', r['lambda'], 'expected', exact + 20e6, 'half/b', r['half_wavelength_m']/b)
    # clamped edges: k = 6.97 [from memory], half-wave 0.66 b
    st = Strip(z, [-1.0]*(n + 1), t, E, nu, 0.0, ('clamped', 'clamped'))
    r = critical(st, math.pi/(4*b), math.pi/(b/4)); print('clamped: k-factor', r['lambda']/exact*4, 'half/b', r['half_wavelength_m']/b)
    # simply supported / free: k = 0.425 for a long plate [from memory]; here nu = 0.3
    st = Strip(z, [-1.0]*(n + 1), t, E, nu, 0.0, ('simply_supported', 'free'))
    A, G = st.assemble(math.pi/(20*b)); mu = mu_max(A, G, 1.0, 1e-10); print('ss-free at half-wave 20 b: k-factor', (1/mu)/exact*4, '(0.425 + (b/a)^2 = ', 0.425 + 1/400, 'from memory)')
