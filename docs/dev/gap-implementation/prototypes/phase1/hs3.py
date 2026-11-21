"""Planner prototype 3 (SPEC18 amendment): general zone structure.
Zones: entry (contact zone | ramp of fixed length), A (plastic, alpha=+1), B (flat no-slip),
E (plastic, alpha=+1, optional), F (plastic, alpha=-1), exit (contact zone | ramp).
Standard library only."""
import math
from hs_bite import influence_scaled, lu_factor, lu_solve


def slope_matrix(x):
    """dI_jk/dx_j for interior hats: (G1(x_j-x_{k-1}) - G1(x_j-x_k))/dL + (G1(x_j-x_{k+1}) - G1(x_j-x_k))/dR,
    G1(t) = t ln|t| - t."""
    n = len(x)
    inv = [1.0 / (x[k + 1] - x[k]) for k in range(n - 1)]
    out = []
    for j in range(n):
        xj = x[j]
        g = []
        for xk in x:
            t = xj - xk
            g.append(0.0 if t == 0.0 else t * math.log(abs(t)) - t)
        d = [(g[k + 1] - g[k]) * inv[k] for k in range(n - 1)]
        out.append([d[k] - d[k - 1] for k in range(1, n - 1)])
    return out


class P3:
    def __init__(self, h0, h1, R, K, mu, tb, tf, e_star, *, n=(3, 16, 24, 6, 16, 3), zone_e=True,
                 flat=True, entry='zone', exit='zone', ramp_in=None, ramp_out=None,
                 strip_modulus=None, slope='three_point', cap=1.0):
        self.h0, self.h1, self.R, self.K, self.mu, self.tb, self.tf, self.e_star = h0, h1, R, K, mu, tb, tf, e_star
        self.L = math.sqrt(R * (h0 - h1))
        self.a1 = self.L ** 2 / (R * h1)
        self.a2 = 4 * K * self.L / (math.pi * e_star * h1)
        self.beta = self.L / h1
        self.cs = 0.0 if strip_modulus is None else 0.5 * (h0 + h1) * K / (strip_modulus * h1)
        self.cap = cap / 2.0
        self.flat, self.zone_e = flat, zone_e and flat
        self.entry, self.exit = entry, exit
        self.rin = None if ramp_in is None else ramp_in / self.L
        self.rout = None if ramp_out is None else ramp_out / self.L
        self.slope = slope
        n1, n2, n3, ne, n4, n5 = n
        if entry == 'ramp': n1 = 1
        if exit == 'ramp': n5 = 1
        if not flat: n3, ne = 0, 0
        if not self.zone_e: ne = 0
        self.nz = (n1, n2, n3, ne, n4, n5)
        self.idx = [0]
        for z in self.nz:
            self.idx.append(self.idx[-1] + z)
        self.n = self.idx[-1]
        # free boundaries (names)
        names = []
        if entry == 'zone': names.append('ci')
        names.append('xi')
        if flat:
            names.append('xa')
            names.append('xbe' if self.zone_e else 'xb')
            if self.zone_e: names.append('xef')
        else:
            names.append('xn')
        names.append('xe')
        if exit == 'zone': names.append('cx')
        self.names = names
        self.nb = len(names)

    def full_bounds(self, bnd):
        b = dict(zip(self.names, bnd))
        ci = b['ci'] if self.entry == 'zone' else b['xi'] - self.rin
        cx = b['cx'] if self.exit == 'zone' else b['xe'] + self.rout
        if self.flat:
            xa = b['xa']
            xbe = b['xbe'] if self.zone_e else b['xb']
            xef = b['xef'] if self.zone_e else xbe
        else:
            xa = xbe = xef = b['xn']
        return [ci, b['xi'], xa, xbe, xef, b['xe'], cx]

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

    def tau(self, pm):
        t = self.mu * pm
        return (t, self.mu) if t < self.cap else (self.cap, 0.0)

    def fields(self, u):
        p, bnd, g0, hn = self.unpack(u)
        x = self.nodes(bnd)
        n = self.n
        a = influence_scaled(x)
        mat = [[-self.a2 * v for v in row] for row in a]
        if self.cs:
            for j in range(1, n):
                mat[j][j - 1] += self.cs
        pin = p[1:n]
        h = [g0 + self.a1 * x[j] * x[j] + sum(m * q for m, q in zip(mat[j], pin)) for j in range(n + 1)]
        return p, bnd, g0, hn, x, h, mat

    def residual(self, u, want_jac=False):
        n = self.n
        p, bnd, g0, hn, x, h, mat = self.fields(u)
        i1, i2, i3, ie, i4 = self.idx[1], self.idx[2], self.idx[3], self.idx[4], self.idx[5]
        beta, mu = self.beta, self.mu
        nu = len(u)
        cg, ch = n - 1 + self.nb, n + self.nb
        res, rows = [], []
        smat = slope_matrix(x) if self.slope == 'analytic' else None
        pin = p[1:n]

        def addp(r, k, v):
            if 1 <= k <= n - 1:
                r[k - 1] += v

        def gap_row(j, target, dh=False):
            res.append(h[j] - target)
            if want_jac:
                r = [0.0] * nu
                r[:n - 1] = mat[j]
                r[cg] = 1.0
                if dh: r[ch] = -1.0
                rows.append(r)

        def ode_row(j, sign, flatrow=False):
            dp = p[j + 1] - p[j]; pm = 0.5 * (p[j] + p[j + 1]); dx = x[j + 1] - x[j]
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
                    r[:n - 1] = [0.5 * (a_ + b_) * dp - (b_ - a_) for a_, b_ in zip(mat[j], mat[j + 1])]
                    r[cg] = dp
                addp(r, j + 1, hm - sign * beta * dt * dx)
                addp(r, j, -hm - sign * beta * dt * dx)
                rows.append(r)

        def slope_row(j):
            if self.slope == 'analytic':
                srow = [-self.a2 * v for v in smat[j]]
                res.append(2 * self.a1 * x[j] + sum(m * q for m, q in zip(srow, pin)))
                if want_jac:
                    r = [0.0] * nu
                    r[:n - 1] = srow
                    rows.append(r)
            else:
                res.append(3 * h[j] - 4 * h[j - 1] + h[j - 2])
                if want_jac:
                    r = [0.0] * nu
                    r[:n - 1] = [3 * a_ - 4 * b_ + c_ for a_, b_, c_ in zip(mat[j], mat[j - 1], mat[j - 2])]
                    rows.append(r)

        def value_row(j, val):
            res.append(p[j] - val)
            if want_jac:
                r = [0.0] * nu
                addp(r, j, 1.0)
                rows.append(r)

        H0 = self.h0 / self.h1
        if self.entry == 'zone':
            for j in range(0, i1 + 1):
                gap_row(j, H0)
            integ = sum(0.5 * (p[j] + p[j + 1]) * (x[j + 1] - x[j]) for j in range(0, i1))
            ce = 2 * mu * self.L / self.h0
            res.append(p[i1] + self.tb / self.K - ce * integ - 1.0)
            if want_jac:
                r = [0.0] * nu
                addp(r, i1, 1.0)
                for j in range(0, i1):
                    w = 0.5 * (x[j + 1] - x[j]) * ce
                    addp(r, j, -w); addp(r, j + 1, -w)
                rows.append(r)
        else:
            gap_row(i1, H0)
            value_row(i1, 1.0 - self.tb / self.K)
        for j in range(i1, i2):
            ode_row(j, +1)
        if self.flat:
            slope_row(i2)
            for j in range(i2, i3 + 1):
                gap_row(j, hn, True)
            if self.zone_e:
                ode_row(i3 - 1, +1, True)     # q = +T at the downstream end of the no-slip zone
                for j in range(i3, ie):
                    ode_row(j, +1)
        for j in range(ie, i4):
            ode_row(j, -1)
        slope_row(i4)
        if self.exit == 'zone':
            for j in range(i4, n + 1):
                gap_row(j, 1.0)
            integ = sum(0.5 * (p[j] + p[j + 1]) * (x[j + 1] - x[j]) for j in range(i4, n))
            cx = 2 * mu * self.L / self.h1
            res.append(p[i4] + self.tf / self.K - cx * integ - 1.0)
            if want_jac:
                r = [0.0] * nu
                addp(r, i4, 1.0)
                for j in range(i4, n):
                    w = 0.5 * (x[j + 1] - x[j]) * cx
                    addp(r, j, -w); addp(r, j + 1, -w)
                rows.append(r)
        else:
            gap_row(i4, 1.0)
            value_row(i4, 1.0 - self.tf / self.K)
        assert len(res) == nu, (len(res), nu)
        if not want_jac:
            return res
        for b in range(self.nb):
            col = n - 1 + b
            step = 1e-7
            up = list(u); up[col] += step
            um = list(u); um[col] -= step
            rp, rm = self.residual(up), self.residual(um)
            for i in range(nu):
                rows[i][col] = (rp[i] - rm[i]) / (2 * step)
        return res, rows

    def admissible(self, u):
        _, bnd, _, _ = self.unpack(u)
        fb = self.full_bounds(bnd)
        active = [fb[0], fb[1], fb[2]] + ([fb[3]] if self.flat else []) + ([fb[4]] if self.zone_e else []) + [fb[5], fb[6]]
        return all(b1 - b0 > 1e-9 for b0, b1 in zip(active, active[1:]))

    def newton(self, u, tol=1e-11, maxit=40, verbose=False):
        u = list(u)
        norm = max(abs(v) for v in self.residual(u))
        for it in range(maxit):
            if norm < tol:
                return u, it, norm
            res, jac = self.residual(u, True)
            du = lu_solve(lu_factor(jac), [-v for v in res])
            step = 1.0
            while True:
                trial = [a + step * b for a, b in zip(u, du)]
                nt = float('inf')
                if self.admissible(trial):
                    try:
                        nt = max(abs(v) for v in self.residual(trial))
                    except (ValueError, ZeroDivisionError):
                        pass
                if nt < norm * (1 - 1e-4 * step) or step < 1e-4:
                    break
                step *= 0.5
            if verbose:
                print(f'   it {it} {norm:.3e} -> {nt:.3e} step {step}')
            if not math.isfinite(nt):
                raise ValueError('line search failed')
            u, norm = trial, nt
        if norm < 1e-8:
            return u, maxit, norm
        raise ValueError(f'not converged {norm:.2e}')

    def post(self, u):
        n = self.n
        p, bnd, g0, hn, x, h, mat = self.fields(u)
        i1, i2, i3, ie, i4 = self.idx[1:6]
        if not self.flat:
            hn = h[ie]
        K, L, h1 = self.K, self.L, self.h1
        force = K * L * sum(0.5 * (p[j] + p[j + 1]) * (x[j + 1] - x[j]) for j in range(n))
        fb = self.full_bounds(bnd)
        ratio = None
        net = None
        if self.flat and i3 > i2:
            rr = []
            S = 0.0
            for j in range(i2, i3):
                pm = 0.5 * (p[j] + p[j + 1]); dx = x[j + 1] - x[j]
                t = self.tau(pm)[0]
                rr.append(hn * (p[j + 1] - p[j]) / (2 * self.beta * t * dx))
                S += 2 * self.beta / hn * t * dx
            ratio = max(abs(v) for v in rr)
            net = abs(p[i3] - p[i2]) / S
        dh_a = max(h[j + 1] - h[j] for j in range(i1, i2))
        dh_e = max([h[j + 1] - h[j] for j in range(i3, ie)] or [0.0])
        dh_f = max(h[j + 1] - h[j] for j in range(ie, i4))
        return {'force_per_width_n_m': force, 'forward_slip': hn - 1.0, 'neutral_thickness': hn * h1,
                'bounds_m': [b * L for b in fb], 'contact_length_m': (fb[6] - fb[0]) * L,
                'pmax_over_k': max(p), 'p_peak_x_m': x[max(range(n + 1), key=lambda j: p[j])] * L,
                'max_shear_ratio': ratio, 'net_shear': net, 'min_p': min(p[1:n]),
                'max_dh': (dh_a, dh_e, dh_f), 'h_e_drop': (h[i3] - h[ie]) if self.zone_e else 0.0,
                'x': [v * L for v in x], 'p': p, 'h': h}


def from_solution(old_post, old_structure_flat, prob, bounds_m, g0_scaled_h1, hn_m):
    """Initial vector for `prob` from physical nodal data (x_m, p/K) and physical free boundaries."""
    xs, ps = old_post['x'], old_post['p']
    def interp(v):
        if v <= xs[0]: return ps[0]
        if v >= xs[-1]: return ps[-1]
        lo, hi = 0, len(xs) - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            if xs[m] <= v: lo = m
            else: hi = m
        t = (v - xs[lo]) / (xs[hi] - xs[lo]) if xs[hi] > xs[lo] else 0.0
        return ps[lo] + t * (ps[hi] - ps[lo])
    bnd = [b / prob.L for b in bounds_m]
    x = prob.nodes(bnd)
    p = [interp(v * prob.L) for v in x]
    u = p[1:-1] + bnd + [g0_scaled_h1]
    if prob.flat:
        u.append(hn_m / prob.h1)
    return u
