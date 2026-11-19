import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from physicroll import foil_bite as fb
from hs_bite import Problem

def interp(xs, ys, x):
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if xs[m] <= x: lo = m
        else: hi = m
    t = (x - xs[lo]) / (xs[hi] - xs[lo]) if xs[hi] > xs[lo] else 0.0
    return ys[lo] + t * (ys[hi] - ys[lo])

def from_mattress(h0, h1, R, Y, mu, tb, tf, E, nu, zones, strip_modulus=80e9, verbose=True):
    m = fb.solve_mattress_bite(h0, h1, 1.0, R, Y, mu, tb, tf, roll_youngs_modulus_pa=E, roll_poisson_ratio=nu)
    K = 2 * Y / math.sqrt(3)
    es = E / (1 - nu * nu)
    structure = 'foil' if m['regime'] == 'foil' else 'conventional'
    pr = Problem(h0, h1, R, K, mu, tb, tf, es, zones=zones, structure=structure,
                 winkler=2 * K / (m['foundation_modulus_pa_m'] * h1), lam=0.0, strip_modulus=strip_modulus)
    L = pr.L
    if structure == 'foil':
        bnd = [m['contact_start_m'], m['plastic_entry_m'], m['flat_zone_start_m'], m['flat_zone_end_m'],
               m['plastic_exit_m'], m['contact_end_m']]
    else:
        bnd = [m['contact_start_m'], m['plastic_entry_m'], m['flat_zone_start_m'],
               m['plastic_exit_m'], m['contact_end_m']]
    bnd = [b / L for b in bnd]
    x = pr.nodes(bnd)
    px, pp = m['profile']['x_m'], m['profile']['pressure_pa']
    p = [interp(px, pp, xx * L) / K for xx in x]
    u = p[1:-1] + bnd + [m['unloaded_gap_m'] / h1] + ([m['neutral_thickness_m'] / h1] if structure == 'foil' else [])
    return pr, u, m

if __name__ == '__main__':
    Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
    R, h0, h1, mu = 0.089, 20e-6, 15e-6, 0.03
    zones = (3, 16, 24, 16, 3)
    pr, u, m = from_mattress(h0, h1, R, Y, mu, 0.0, 0.0, E, nu, zones)
    print('mattress W', m['force_per_width_n_m'], 'Wbar', m['force_per_width_n_m'] * Es / (R * Ys ** 2), m['regime'])
    t = time.perf_counter()
    u, it, nrm = pr.newton(u, verbose=True)
    print('lam=0 newton', it, nrm, time.perf_counter() - t)
    q = pr.post(u)
    print(' discrete winkler W', q['force_per_width_n_m'], 'slip', q['forward_slip'], m['forward_slip_fraction'])
    lam = 0.0
    step = 0.1
    t0 = time.perf_counter()
    total_it = 0
    while lam < 1.0:
        new = min(1.0, lam + step)
        pr.lam = new
        try:
            u2, it, nrm = pr.newton(u, maxit=25)
            q = pr.post(u2)
            if q['min_p'] < 0:
                raise ValueError('negative pressure')
            u, lam = u2, new
            total_it += it
            print(f'lam {lam:.3f} it {it} W {q["force_per_width_n_m"]:.4e} Wbar {q["force_per_width_n_m"]*Es/(R*Ys**2):.2f} slip {q["forward_slip"]:.4f} pmax/K {q["max_pressure_over_K"]:.2f} L {q["contact_length_m"]*1e3:.3f} mm')
            step = min(step * 1.5, 0.25)
        except ValueError as e:
            print('  fail at', new, e)
            step *= 0.5
            if step < 1e-4: break
    print('homotopy time', time.perf_counter() - t0, 'iterations', total_it)
    q = pr.post(u)
    for k in ('force_per_width_n_m', 'forward_slip', 'neutral_thickness_m', 'boundaries_m', 'contact_length_m', 'max_pressure_over_K', 'work_residual_relative', 'neutral_shear_ratio_max', 'min_p', 'max_dh_slip'):
        print(k, q[k])
    print('Wbar', q['force_per_width_n_m'] * Es / (R * Ys ** 2), 'ratio to 118', q['force_per_width_n_m'] * Es / (R * Ys ** 2) / 118)
    import json
    json.dump({'u': u, 'zones': zones}, open('v1_solution.json', 'w'))
