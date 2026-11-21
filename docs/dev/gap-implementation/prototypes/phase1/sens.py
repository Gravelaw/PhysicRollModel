import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
from hs_bite import Problem, lu_factor, lu_solve

def phys(pr, u):
    p, bnd, g0, hn = pr.unpack(u)
    return ([v * pr.K for v in p], [b * pr.L for b in bnd], g0 * pr.h1, None if hn is None else hn * pr.h1)

def to_scaled(pr, ph):
    p, bnd, g0, hn = ph
    u = [v / pr.K for v in p[1:-1]] + [b / pr.L for b in bnd] + [g0 / pr.h1]
    if pr.structure == 'foil':
        u.append(hn / pr.h1)
    return u

def clone(pr, **kw):
    a = dict(h0=pr.h0, h1=pr.h1, R=pr.R, K=pr.K, mu=pr.mu, tb=pr.tb, tf=pr.tf, e_star=pr.e_star)
    a.update(kw)
    new = Problem(a['h0'], a['h1'], a['R'], a['K'], a['mu'], a['tb'], a['tf'], a['e_star'],
                  zones=pr.base_zones, structure=pr.structure, lam=1.0, closure=pr.closure)
    new.base_zones = pr.base_zones
    new.cs = pr.cs * (0.5 * (a['h0'] + a['h1']) * a['K'] / a['h1']) / (0.5 * (pr.h0 + pr.h1) * pr.K / pr.h1)
    new.cap = pr.cap
    return new

def chord(pr, u, lu, tol=1e-10, maxit=30):
    for it in range(maxit):
        res = pr.residual(u)
        nrm = max(abs(v) for v in res)
        if nrm < tol:
            return u, it
        du = lu_solve(lu, [-v for v in res])
        u = [a + b for a, b in zip(u, du)]
    raise ValueError(f'chord not converged {nrm:.2e}')

def derive(pr, u, verbose=True):
    """Central differences with chord iterations on the nominal LU (rel. step 1e-3)."""
    t0 = time.perf_counter()
    res, jac = pr.residual(u, True)
    lu = lu_factor(jac)
    ph = phys(pr, u)
    q0 = pr.post(u)
    out, its = {}, 0
    steps = {'h1': 1e-3 * pr.h1, 'h0': 1e-3 * pr.h0, 'tb': 1e-3 * pr.K, 'tf': 1e-3 * pr.K,
             'mu': 1e-3 * pr.mu, 'K': 1e-3 * pr.K}
    for name, d in steps.items():
        vals = []
        for sgn in (+1, -1):
            base = getattr(pr, name)
            if name in ('tb', 'tf') and base - d < 0:
                kw = {name: base + (2 * d if sgn > 0 else 0.0)}
            else:
                kw = {name: base + sgn * d}
            pp = clone(pr, **kw)
            # the nominal LU is in the nominal scaling; rescale the solution, reuse LU (chord)
            uu, it = chord(pp, to_scaled(pp, ph), lu)
            its += it
            vals.append(pp.post(uu))
        out['F_' + name] = (vals[0]['force_per_width_n_m'] - vals[1]['force_per_width_n_m']) / (2 * d)
        out['f_' + name] = (vals[0]['forward_slip'] - vals[1]['forward_slip']) / (2 * d)
    out['chord_iterations'] = its
    out['time_s'] = time.perf_counter() - t0
    return out

def derive_newton(pr, u, scale=1.0):
    ph = phys(pr, u)
    out = {}
    steps = {'h1': 1e-3 * pr.h1, 'h0': 1e-3 * pr.h0, 'tb': 1e-3 * pr.K, 'tf': 1e-3 * pr.K,
             'mu': 1e-3 * pr.mu, 'K': 1e-3 * pr.K}
    for name, d in steps.items():
        d *= scale
        vals = []
        for sgn in (+1, -1):
            base = getattr(pr, name)
            if name in ('tb', 'tf') and base - d < 0:
                kw = {name: base + (2 * d if sgn > 0 else 0.0)}
            else:
                kw = {name: base + sgn * d}
            pp = clone(pr, **kw)
            uu, it, nrm = pp.newton(to_scaled(pp, ph))
            vals.append(pp.post(uu))
        out['F_' + name] = (vals[0]['force_per_width_n_m'] - vals[1]['force_per_width_n_m']) / (2 * d)
        out['f_' + name] = (vals[0]['forward_slip'] - vals[1]['forward_slip']) / (2 * d)
    return out

if __name__ == '__main__':
    Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
    cases = [('BT-V1', 20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 0.3),
             ('battery F1 50->30', 50e-6, 30e-6, 0.135, 175e6, 0.03, 30e6, 30e6, 210e9, 0.3),
             ('BT-V3 140->70', 140e-6, 70e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 0.3)]
    for name, h0, h1, R, Yv, mu, tb, tf, Ev, nuv in cases:
        t = time.perf_counter()
        pr, u, tot, m = solve_cold(h0, h1, R, Yv, mu, tb, tf, Ev, nuv)
        tc = time.perf_counter() - t
        q = pr.post(u)
        d = derive(pr, u)
        t = time.perf_counter()
        dn = derive_newton(pr, u)
        tn = time.perf_counter() - t
        dh = derive_newton(pr, u, 0.5)
        print(name, pr.structure, f'cold {tc:.2f}s it {tot}; chord derive {d["time_s"]:.2f}s ({d["chord_iterations"]} chord its); newton FD derive {tn:.2f}s')
        print(f'   F/w {q["force_per_width_n_m"]:.5e} slip {q["forward_slip"]:.5f} L {q["contact_length_m"]:.4e} mattress F/w {m["force_per_width_n_m"]:.4e} slip {m["forward_slip_fraction"]:.4f} L {m["contact_length_m"]:.4e}')
        for k in d:
            if k[0] in 'Ff' and k[1] == '_':
                print(f'   {k:6s} chord {d[k]: .6e}  newton {dn[k]: .6e}  half-step {dh[k]: .6e}  rel diff half {abs(dn[k]-dh[k])/max(abs(dh[k]),1e-300):.1e}')
        # elasticities
        F = q['force_per_width_n_m']
        print(f'   load exponent in friction {d["F_mu"]*pr.mu/F:.3f}; in K {d["F_K"]*pr.K/F:.3f}; Q = -dF/dh1 = {-d["F_h1"]:.4e} Pa')
