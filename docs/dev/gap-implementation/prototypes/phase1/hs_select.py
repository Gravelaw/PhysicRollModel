"""Planner prototype (SPEC18 amendment): structure selection with zone E, and chord sensitivities, on hs3.P3."""
import sys, math, time
sys.path.insert(0, '.')
from hs_solve2 import solve_cold, convert
from hs_bite import lu_factor, lu_solve
from hs3 import P3, from_solution

TOL_DH = 1e-7

def p3_of(pr, u, K, es, sm):
    """Same structure as the hs_bite.Problem solution, in the P3 class (no zone E)."""
    q = pr.post(u)
    p, bnd, g0, hn = pr.unpack(u)
    z = pr.zones
    if pr.structure == 'foil':
        p3 = P3(pr.h0, pr.h1, pr.R, K, pr.mu, pr.tb, pr.tf, es, n=(z[0], z[1], z[2], 0, z[3], z[4]), zone_e=False, strip_modulus=sm)
        u0 = from_solution({'x': q['x_m'], 'p': p}, True, p3, q['boundaries_m'], g0, hn * pr.h1)
    else:
        p3 = P3(pr.h0, pr.h1, pr.R, K, pr.mu, pr.tb, pr.tf, es, n=(z[0], z[1], 0, 0, z[3], z[4]), flat=False, strip_modulus=sm)
        u0 = from_solution({'x': q['x_m'], 'p': p}, False, p3, q['boundaries_m'], g0, None)
    p3.cap = pr.cap
    u1, it, nrm = p3.newton(u0, maxit=10)
    return p3, u1

def shear_ratios(p3, u):
    p, bnd, g0, hn, x, h, mat = p3.fields(u)
    i2, i3 = p3.idx[2], p3.idx[3]
    return [hn * (p[j + 1] - p[j]) / (2 * p3.beta * p3.tau(0.5 * (p[j] + p[j + 1]))[0] * (x[j + 1] - x[j])) for j in range(i2, i3)], x, p, h

HILL_TOL = 0.02     # friction-hill bounds may be missed by 0.02*K (discretisation)

def hill_margin(p3, u):
    """min over the nodes of the no-slip zone of the two friction-hill bounds, in units of K."""
    p, bnd, g0, hn, x, h, mat = p3.fields(u)
    i2, i3 = p3.idx[2], p3.idx[3]
    inc = [2 * p3.beta / hn * p3.tau(0.5 * (p[j] + p[j + 1]))[0] * (x[j + 1] - x[j]) for j in range(i2, i3)]
    fwd = [0.0]
    for v in inc: fwd.append(fwd[-1] + v)
    tot = fwd[-1]
    m1 = min(p[i2] + fwd[k - i2] - p[k] for k in range(i2, i3 + 1))
    m2 = min(p[i3] + (tot - fwd[k - i2]) - p[k] for k in range(i2, i3 + 1))
    return m1, m2

def admissible(p3, u, check_shear=True):
    """A F: monotone thinning. A B F: also eq. (16) shear within the limit in every no-slip element.
    A B E F: monotone thinning and the friction-hill bounds within HILL_TOL."""
    q = p3.post(u)
    if q['min_p'] < 0: return False, 'negative pressure'
    if max(q['max_dh']) > TOL_DH: return False, 'strip thickens in a reduction zone'
    if p3.flat and not p3.zone_e and q['max_shear_ratio'] > 1.0 + 1e-6: return False, 'eq. (16) shear above the limit in the no-slip zone'
    if p3.flat and p3.zone_e and min(hill_margin(p3, u)) < -HILL_TOL: return False, 'friction-hill bound missed'
    return True, ''

def add_e(p3, u, K, es, sm, ne=8, base=(3, 16, 24, 8, 16, 3)):
    r, x, p, h = shear_ratios(p3, u)
    i2 = p3.idx[2]
    first = next((k for k, v in enumerate(r) if v > 1.0 and k >= 2), None)
    if first is None: return None
    q = p3.post(u)
    b = q['bounds_m']
    pe = P3(p3.h0, p3.h1, p3.R, K, p3.mu, p3.tb, p3.tf, es, n=base, zone_e=True, strip_modulus=sm)
    pe.cap = p3.cap
    _, bnd, g0, hn = p3.unpack(u)
    u0 = from_solution({'x': q['x'], 'p': q['p']}, True, pe, [b[0], b[1], b[2], x[i2 + first] * p3.L, b[4], b[5], b[6]], g0, hn * p3.h1)
    u1, it, nrm = pe.newton(u0, maxit=60)
    return pe, u1

def conventional_of(p3, u, K, es, sm, base=(3, 16, 24, 8, 16, 3)):
    if not p3.flat: return p3, u
    q = p3.post(u)
    b = q['bounds_m']
    pc = P3(p3.h0, p3.h1, p3.R, K, p3.mu, p3.tb, p3.tf, es, n=(base[0], base[1] + base[2] // 2, 0, 0, base[4] + base[2] // 2, base[5]), flat=False, strip_modulus=sm)
    pc.cap = p3.cap
    _, bnd, g0, hn = p3.unpack(u)
    u0 = from_solution({'x': q['x'], 'p': q['p']}, False, pc, [b[0], b[1], 0.5 * (b[3] + b[4]), b[5], b[6]], g0, None)
    u1, it, nrm = pc.newton(u0, maxit=60)
    return pc, u1

def six_from_conventional(pc, uc, K, es, sm, base=(3, 16, 24, 8, 16, 3)):
    p, bnd, g0, hn, x, h, mat = pc.fields(uc)
    i1, ie = pc.idx[1], pc.idx[4]
    rising = [j for j in range(i1, ie) if h[j + 1] > h[j] + TOL_DH]
    if not rising: return None
    q = pc.post(uc)
    b = q['bounds_m']; L = pc.L
    xa, xbe, xn = x[rising[0]] * L, x[rising[-1] + 1] * L, b[4]
    if xbe >= xn - 1e-9: xbe = xa + 0.5 * (xn - xa)
    pe = P3(pc.h0, pc.h1, pc.R, K, pc.mu, pc.tb, pc.tf, es, n=base, zone_e=True, strip_modulus=sm)
    pe.cap = pc.cap
    u0 = from_solution({'x': q['x'], 'p': q['p']}, False, pe, [b[0], b[1], xa, xbe, xn, b[5], b[6]], g0, min(h[rising[0]:rising[-1] + 2]) * pc.h1)
    u1, it, nrm = pe.newton(u0, maxit=60)
    return pe, u1

def select(h0, h1, R, Y, mu, tb, tf, E, nu, sm=80e9, cap=1.0):
    K = 2 * Y / math.sqrt(3); es = E / (1 - nu * nu)
    pr, u, tot, m = solve_cold(h0, h1, R, Y, mu, tb, tf, E, nu, strip_modulus=sm, cap=cap)
    return select_from(pr, u, K, es, sm)

def select_from(pr, u, K, es, sm):
    p3, u3 = p3_of(pr, u, K, es, sm)
    trail = [('march', 'foil' if p3.flat else 'conventional')]
    if p3.flat:
        ok, why = admissible(p3, u3)
        if ok: return p3, u3, trail + [('accept', 'A B F')]
        trail.append(('reject A B F', why))
        try:
            out = add_e(p3, u3, K, es, sm)
            if out is not None:
                ok, why = admissible(*out)
                if ok: return out[0], out[1], trail + [('accept', 'A B E F')]
                trail.append(('reject A B E F', why))
        except ValueError as e:
            trail.append(('A B E F failed', str(e)))
    try:
        pc, uc = conventional_of(p3, u3, K, es, sm)
        ok, why = admissible(pc, uc)
        if ok: return pc, uc, trail + [('accept', 'A F')]
        trail.append(('reject A F', why))
        out = six_from_conventional(pc, uc, K, es, sm)
        if out is not None:
            ok, why = admissible(*out)
            if ok: return out[0], out[1], trail + [('accept', 'A B E F from A F')]
            trail.append(('reject A B E F from A F', why))
    except ValueError as e:
        trail.append(('failed', str(e)))
    raise ValueError(f'no admissible zone structure: {trail}')

def clone(p3, **kw):
    a = dict(h0=p3.h0, h1=p3.h1, R=p3.R, K=p3.K, mu=p3.mu, tb=p3.tb, tf=p3.tf, e_star=p3.e_star)
    a.update(kw)
    n = P3(a['h0'], a['h1'], a['R'], a['K'], a['mu'], a['tb'], a['tf'], a['e_star'], n=p3.nz, zone_e=p3.zone_e, flat=p3.flat)
    n.nz, n.idx, n.n, n.names, n.nb = p3.nz, p3.idx, p3.n, p3.names, p3.nb
    n.cs = p3.cs * (0.5 * (a['h0'] + a['h1']) * a['K'] / a['h1']) / (0.5 * (p3.h0 + p3.h1) * p3.K / p3.h1)
    n.cap = p3.cap
    return n

def rescale(p3, u, new):
    p, bnd, g0, hn = p3.unpack(u)
    v = [x * p3.K / new.K for x in p[1:-1]] + [b * p3.L / new.L for b in bnd] + [g0 * p3.h1 / new.h1]
    if p3.flat: v.append(hn * p3.h1 / new.h1)
    return v

def derive(p3, u):
    t0 = time.perf_counter()
    res, jac = p3.residual(u, True)
    lu = lu_factor(jac)
    out, its = {}, 0
    steps = {'h1': 1e-3 * p3.h1, 'h0': 1e-3 * p3.h0, 'tb': 1e-3 * p3.K, 'tf': 1e-3 * p3.K, 'mu': 1e-3 * p3.mu, 'K': 1e-3 * p3.K}
    for name, d in steps.items():
        vals = []
        for sgn in (+1, -1):
            base = getattr(p3, name)
            kw = {name: base + (2 * d if sgn > 0 else 0.0)} if (name in ('tb', 'tf') and base - d < 0) else {name: base + sgn * d}
            pp = clone(p3, **kw)
            v = rescale(p3, u, pp)
            for it in range(40):
                r = pp.residual(v)
                if max(abs(x) for x in r) < 1e-10: break
                dv = lu_solve(lu, [-x for x in r])
                v = [a + b for a, b in zip(v, dv)]
            else:
                raise ValueError('chord not converged')
            its += it
            vals.append(pp.post(v))
        out['F_' + name] = (vals[0]['force_per_width_n_m'] - vals[1]['force_per_width_n_m']) / (2 * d)
        out['f_' + name] = (vals[0]['forward_slip'] - vals[1]['forward_slip']) / (2 * d)
    out['chord_iterations'] = its
    out['time_s'] = time.perf_counter() - t0
    return out

if __name__ == '__main__':
    import json
    sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
    Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
    cases = [('BT-V1 Es 80GPa', 20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 80e9),
             ('BT-V1 rigid 1e13', 20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 1e13),
             ('BT-V3 140->70', 140e-6, 70e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 80e9),
             ('BT-V2 R89', 73e-6, 73e-6 * 0.43, 0.089, Y, 0.026, 0.107 * Ys, 0.132 * Ys, E, 80e9),
             ('BT-V2 R135', 73e-6, 73e-6 * 0.43, 0.135, Y, 0.026, 0.107 * Ys, 0.132 * Ys, E, 80e9),
             ('Fig1 60->30', 60e-6, 30e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 80e9),
             ('Fig1 30->15', 30e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 80e9),
             ('Fig1 20->10', 20e-6, 10e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 80e9)]
    for r, gs in ((0.5, (56, 52, 48, 44)), (0.25, (40, 36, 32, 28)), (0.1, (30, 26, 22))):
        for g in gs:
            cases.append((f'r{r} {g}um', g * 1e-6, g * 1e-6 * (1 - r), 0.089, Y, 0.03, 0.0, 0.0, E, 80e9))
    cases.append(('cap case mu0.03', 50e-6, 25e-6, 0.135, 150e6 * math.sqrt(3) / 2, 0.03, 20e6, 20e6, 210e9, 80e9))
    for name in ('battery_foil', 'lengthwise_bands'):
        case = json.load(open(f'{sys.argv[1]}/scenarios/band_diagnosis_{name}.json'))
        p = case['pass']; st = case['stand']
        for s in case['schedule']:
            cases.append((name[:4] + ' ' + s['label'][:4], s['entry_thickness_m'], s['exit_thickness_m'], p['work_roll_radius_m'], s['mean_flow_stress_pa'],
                          s['friction_coefficient'], s['entry_tension_pa'], s['exit_tension_pa'], st['roll_youngs_modulus_pa'], case['material']['youngs_modulus_pa'] / (1 - 0.33 ** 2)))
    only = sys.argv[2] if len(sys.argv) > 2 else None
    for name, h0, h1, R, Yv, mu, tb, tf, Ev, sm in cases:
        if only and only not in name: continue
        K = 2 * Yv / math.sqrt(3); es = Ev / 0.91; scale = es / (R * K ** 2)
        t = time.perf_counter()
        try:
            p3, u3, trail = select(h0, h1, R, Yv, mu, tb, tf, Ev, 0.3, sm)
        except ValueError as e:
            print(f'{name:18s} FAILED {str(e)[:300]}'); continue
        tc = time.perf_counter() - t
        q = p3.post(u3)
        try:
            d = derive(p3, u3)
            F = q['force_per_width_n_m']
            dtxt = f'Fh {d["F_h1"]:.4e} Fhin {d["F_h0"]:.4e} Fse {d["F_tb"]:.4e} Fsx {d["F_tf"]:.4e} Fmu {d["F_mu"]:.4e} FK {d["F_K"]:.4e} fh {d["f_h1"]:.4e} e_mu {d["F_mu"]*mu/F:.3f} sens {d["time_s"]:.2f}s'
        except ValueError as e:
            dtxt = f'sens FAILED {e}'
        bm = q['bounds_m']
        hm = hill_margin(p3, u3) if p3.flat else (None, None)
        print(f'{name:18s} {trail[-1][1]:18s} hill {hm} F/w {q["force_per_width_n_m"]:.5e} Wbar {q["force_per_width_n_m"]*scale:8.3f} slip {q["forward_slip"]:.4f} L {q["contact_length_m"]*1e3:.4f} pmax/K {q["pmax_over_k"]:.3f} peak x {q["p_peak_x_m"]*1e3:.3f} B {1e6*(bm[3]-bm[2]):.0f} E {1e6*(bm[4]-bm[3]):.0f} um shear {q["max_shear_ratio"]} cold {tc:.2f}s | {dtxt} | {[t_[0] for t_ in trail]}')
