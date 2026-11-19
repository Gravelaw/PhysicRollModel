"""Planner prototype (SPEC18): rigid-plastic strip between elastic half-space rolls.

Zones (foil structure): entry rigid contact [c_i, x_i] (h = h0, tau = +mu p), entry plastic slip
[x_i, x_a] (h p' = K h' + 2 tau), neutral no-slip flat [x_a, x_b] (h = h_n, tau = (h_n/2) p'),
exit plastic slip [x_b, x_e] (h p' = K h' - 2 tau), exit rigid contact [x_e, c_x] (h = h1).
Conventional structure: no neutral zone; neutral point x_n between the slip zones.
tau = min(mu p, m K/2).  h(x) = g0 + x^2/R - (4/(pi E*)) Int p ln|x-x'| dx'.
Scaled unknowns: P = p/K, X = x/L (L = sqrt(R*draft)), H = h/h1.
"""
import math
from hs_kernel import G


def influence_scaled(x):
    """A[j][k] = Int hat_k ln|x_j - x'| dx' for interior hats k = 1..N-1 (p_0 = p_N = 0)."""
    n = len(x)
    inv = [1.0 / (x[k + 1] - x[k]) for k in range(n - 1)]
    out = []
    log = math.log
    for j in range(n):
        xj = x[j]
        gj = []
        for xk in x:
            t = xj - xk
            gj.append(0.0 if t == 0.0 else t * t * (0.5 * log(abs(t)) - 0.75))
        d = [(gj[k + 1] - gj[k]) * inv[k] for k in range(n - 1)]
        out.append([d[k] - d[k - 1] for k in range(1, n - 1)])
    return out


def lu_factor(a):
    n = len(a)
    a = [row[:] for row in a]
    piv = list(range(n))
    for k in range(n):
        m = max(range(k, n), key=lambda i: abs(a[i][k]))
        if a[m][k] == 0.0:
            raise ValueError('singular Jacobian')
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


def lu_solve(lu, b):
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


class Problem:
    def __init__(self, h0, h1, R, K, mu, tb, tf, e_star, zones=(3, 16, 24, 16, 3),
                 shear_cap=1.0, structure='foil', winkler=None, lam=1.0, closure='slope',
                 strip_modulus=None):
        self.h0, self.h1, self.R, self.K, self.mu, self.tb, self.tf = h0, h1, R, K, mu, tb, tf
        self.e_star = e_star
        self.L = math.sqrt(R * (h0 - h1))
        self.a1 = self.L ** 2 / (R * h1)
        self.a2 = 4 * K * self.L / (math.pi * e_star * h1)
        self.beta = self.L / h1
        self.cap = shear_cap / 2.0
        self.structure = structure
        if structure == 'conventional':
            zones = (zones[0], zones[1] + zones[2] // 2, 0, zones[3] + zones[2] // 2, zones[4])
        self.zones = zones
        self.n = sum(zones)
        self.idx = [0]
        for z in zones:
            self.idx.append(self.idx[-1] + z)
        self.nb = 6 if structure == 'foil' else 5
        self.winkler = winkler    # scaled Winkler coefficient 2K/(K_p h1) or None
        self.lam = lam
        self.closure = closure
        # elastic thickness compliance of the strip (local spring), scaled: (h_ref*K)/(E_s* h1)
        self.cs = 0.0 if strip_modulus is None else 0.5 * (h0 + h1) * K / (strip_modulus * h1)

    # unknown vector: P[1..n-1], boundaries (nb), G0, [Hn]
    def nodes(self, bnd):
        x = []
        if self.structure == 'foil':
            b = bnd
        else:
            b = [bnd[0], bnd[1], bnd[2], bnd[2], bnd[3], bnd[4]]
        for z in range(5):
            m = self.zones[z]
            lo, hi = b[z], b[z + 1]
            for i in range(m):
                x.append(lo + (hi - lo) * i / m)
        x.append(b[5])
        return x

    def unpack(self, u):
        n = self.n
        p = [0.0] + list(u[:n - 1]) + [0.0]
        bnd = list(u[n - 1:n - 1 + self.nb])
        g0 = u[n - 1 + self.nb]
        hn = u[n + self.nb] if self.structure == 'foil' else None
        return p, bnd, g0, hn

    def gap(self, x, p, g0):
        n = self.n
        a = influence_scaled(x)
        lam = self.lam
        c = -self.a2 * lam
        mat = [[c * v for v in row] for row in a]
        w = lam * self.cs
        if self.winkler is not None and lam < 1.0:
            w += (1 - lam) * self.winkler
        if w:
            for j in range(1, n):
                mat[j][j - 1] += w
        pin = p[1:n]
        a1 = self.a1
        h = [g0 + a1 * x[j] * x[j] + sum(m * q for m, q in zip(mat[j], pin)) for j in range(n + 1)]
        return h, mat

    def tau(self, pm):
        t = self.mu * pm
        if t < self.cap:
            return t, self.mu
        return self.cap, 0.0

    def residual(self, u, want_jac=False):
        n = self.n
        p, bnd, g0, hn = self.unpack(u)
        x = self.nodes(bnd)
        h, mat = self.gap(x, p, g0)
        i1, i2, i3, i4 = self.idx[1], self.idx[2], self.idx[3], self.idx[4]
        foil = self.structure == 'foil'
        beta, mu = self.beta, self.mu
        res = []
        rows = []     # for jacobian wrt (P, G0, Hn): list of (dict col->val) dense rows
        nu = len(u)
        cg = n - 1 + self.nb
        ch = n + self.nb

        def gap_row(j, target, dh=False):
            res.append(h[j] - target)
            if want_jac:
                r = [0.0] * nu
                r[:n - 1] = mat[j]
                r[cg] = 1.0
                if dh:
                    r[ch] = -1.0
                rows.append(r)

        def addp(r, k, v):
            if 1 <= k <= n - 1:
                r[k - 1] += v

        H0 = self.h0 / self.h1
        # E1 entry rigid nodes
        for j in range(0, i1 + 1):
            gap_row(j, H0)
        # E2 yield at x_i
        integ = sum(0.5 * (p[j] + p[j + 1]) * (x[j + 1] - x[j]) for j in range(0, i1))
        ce = 2 * mu * self.L / self.h0
        res.append(p[i1] + self.tb / self.K - ce * integ - 1.0)
        if want_jac:
            r = [0.0] * nu
            addp(r, i1, 1.0)
            for j in range(0, i1):
                w = 0.5 * (x[j + 1] - x[j]) * ce
                addp(r, j, -w)
                addp(r, j + 1, -w)
            rows.append(r)

        def ode_row(j, sign, flat):
            dp = p[j + 1] - p[j]
            pm = 0.5 * (p[j] + p[j + 1])
            dx = x[j + 1] - x[j]
            t, dt = self.tau(pm)
            if flat:
                hm = hn
                dh = 0.0
            else:
                hm = 0.5 * (h[j] + h[j + 1])
                dh = h[j + 1] - h[j]
            res.append(hm * dp - dh - sign * 2 * beta * t * dx)
            if want_jac:
                r = [0.0] * nu
                if flat:
                    r[ch] = dp
                else:
                    mj, mk = mat[j], mat[j + 1]
                    r[:n - 1] = [0.5 * (a + b) * dp - (b - a) for a, b in zip(mj, mk)]
                    r[cg] = dp
                addp(r, j + 1, hm - sign * beta * dt * dx)
                addp(r, j, -hm - sign * beta * dt * dx)
                rows.append(r)

        def slope_row(j):
            # one-sided second-order slope of h_p at node j from the two nodes before it = 0
            res.append(3 * h[j] - 4 * h[j - 1] + h[j - 2])
            if want_jac:
                r = [0.0] * nu
                r[:n - 1] = [3 * a - 4 * b + c for a, b, c in zip(mat[j], mat[j - 1], mat[j - 2])]
                rows.append(r)

        # E3 entry slip elements
        for j in range(i1, i2):
            ode_row(j, +1, False)
        if foil:
            if self.closure == 'slope':
                slope_row(i2)                # E8': h_p' = 0 where the entry slip zone ends
            else:
                ode_row(i2, +1, True)        # E8 Coulomb limit at the start of the neutral zone
            for j in range(i2, i3 + 1):      # E4
                gap_row(j, hn, True)
            if self.closure == 'e9':
                ode_row(i3 - 1, -1, True)    # E9 (Coulomb limit at the end of the neutral zone)
        # E5 exit slip elements
        for j in range(i3, i4):
            ode_row(j, -1, False)
        # J4 smooth junction plastic exit -> rigid exit zone (f' = 0 at x_e+)
        if self.closure == 'slope':
            slope_row(i4)                    # J4': h_p' = 0 where plastic thinning ends
        if self.closure == 'j4':
            dp = p[i4 + 1] - p[i4]
            pm = 0.5 * (p[i4] + p[i4 + 1])
            dx = x[i4 + 1] - x[i4]
            res.append(dp + 2 * beta * mu * pm * dx)
            if want_jac:
                r = [0.0] * nu
                addp(r, i4 + 1, 1.0 + beta * mu * dx)
                addp(r, i4, -1.0 + beta * mu * dx)
                rows.append(r)
        # E6 exit rigid nodes
        for j in range(i4, n + 1):
            gap_row(j, 1.0)
        # E7 yield at x_e
        integ = sum(0.5 * (p[j] + p[j + 1]) * (x[j + 1] - x[j]) for j in range(i4, n))
        cx = 2 * mu * self.L / self.h1
        res.append(p[i4] + self.tf / self.K - cx * integ - 1.0)
        if want_jac:
            r = [0.0] * nu
            addp(r, i4, 1.0)
            for j in range(i4, n):
                w = 0.5 * (x[j + 1] - x[j]) * cx
                addp(r, j, -w)
                addp(r, j + 1, -w)
            rows.append(r)
        if not want_jac:
            return res
        # boundary columns by finite differences
        for b in range(self.nb):
            col = n - 1 + b
            step = 1e-7
            up = list(u)
            up[col] += step
            um = list(u)
            um[col] -= step
            rp = self.residual(up)
            rm = self.residual(um)
            for i in range(nu):
                rows[i][col] = (rp[i] - rm[i]) / (2 * step)
        return res, rows

    def newton(self, u, tol=1e-11, maxit=40, verbose=False):
        u = list(u)
        res = self.residual(u)
        norm = max(abs(v) for v in res)
        for it in range(maxit):
            if norm < tol:
                return u, it, norm
            res, jac = self.residual(u, True)
            lu = lu_factor(jac)
            du = lu_solve(lu, [-v for v in res])
            step = 1.0
            while True:
                trial = [a + step * b for a, b in zip(u, du)]
                ok = self.admissible(trial)
                if ok:
                    try:
                        rt = self.residual(trial)
                        nt = max(abs(v) for v in rt)
                    except (ValueError, ZeroDivisionError):
                        nt = float('inf')
                else:
                    nt = float('inf')
                if nt < norm * (1 - 1e-4 * step) or step < 1e-4:
                    break
                step *= 0.5
            if verbose:
                print(f'   it {it} norm {norm:.3e} -> {nt:.3e} step {step}')
            if not math.isfinite(nt):
                raise ValueError('newton line search failed')
            u, norm = trial, nt
        if norm < 1e3 * tol:
            return u, maxit, norm
        raise ValueError(f'newton not converged, residual {norm:.3e}')

    def admissible(self, u):
        p, bnd, g0, hn = self.unpack(u)
        if any(b1 - b0 <= 1e-9 for b0, b1 in zip(bnd, bnd[1:])):
            return False
        return True

    # ---- post-processing
    def post(self, u):
        n = self.n
        p, bnd, g0, hn = self.unpack(u)
        x = self.nodes(bnd)
        h, _ = self.gap(x, p, g0)
        i1, i2, i3, i4 = self.idx[1], self.idx[2], self.idx[3], self.idx[4]
        if self.structure != 'foil':
            hn = h[i2]
        K, L, h1, h0, mu = self.K, self.L, self.h1, self.h0, self.mu
        force = K * L * sum(0.5 * (p[j] + p[j + 1]) * (x[j + 1] - x[j]) for j in range(n))
        # traction Int tau dx  (per unit width, one roll)
        trac = 0.0
        slip = 0.0     # Int tau (1 - h_n/h) dx   (dissipation over V_r, one interface)
        for j in range(n):
            dx = (x[j + 1] - x[j]) * L
            pm = 0.5 * (p[j] + p[j + 1])
            if j < i2:
                t = self.tau(pm)[0] * K
                hm = h0 / h1 if j < i1 else 0.5 * (h[j] + h[j + 1])
                trac += t * dx
                slip += t * dx * (1 - hn / hm)
            elif j < i3:
                trac += 0.5 * hn * h1 * (p[j + 1] - p[j]) * K
            else:
                t = self.tau(pm)[0] * K
                hm = 1.0 if j >= i4 else 0.5 * (h[j] + h[j + 1])
                trac -= t * dx
                slip += t * dx * (hn / hm - 1)
        plastic = hn * h1 * K * math.log(h0 / h1)
        tension = hn * h1 * (self.tf - self.tb)
        work_res = 2 * trac + tension - plastic - 2 * slip
        scale = max(abs(2 * trac), plastic, abs(2 * slip), 1e-300)
        # neutral zone shear ratio
        ratio = 0.0
        if self.structure == 'foil':
            for j in range(i2, i3):
                pm = 0.5 * (p[j] + p[j + 1])
                q = 0.5 * hn * (p[j + 1] - p[j]) / ((x[j + 1] - x[j]) * self.beta)
                ratio = max(ratio, abs(q) / self.tau(pm)[0])
        return {'x_m': [v * L for v in x], 'p_pa': [v * K for v in p], 'h_m': [v * h1 for v in h],
                'force_per_width_n_m': force, 'traction_per_width_n_m': trac,
                'neutral_thickness_m': hn * h1, 'forward_slip': hn - 1.0,
                'boundaries_m': [b * L for b in bnd], 'contact_length_m': (bnd[-1] - bnd[0]) * L,
                'max_pressure_over_K': max(p), 'work_residual_relative': abs(work_res) / scale,
                'slip_dissipation_one_interface_over_vr_n_m': slip,
                'neutral_shear_ratio_max': ratio,
                'min_p': min(p[1:n]),
                'max_dh_slip': max([h[j + 1] - h[j] for j in range(i1, i2)]
                                   + [h[j + 1] - h[j] for j in range(i3, i4)])}
