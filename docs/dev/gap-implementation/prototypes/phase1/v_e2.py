"""Zone E where the no-slip zone needs more than the friction limit: BT-V1 with a stiff strip, demo F1."""
import sys, math, time, json
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
from hs3 import P3, from_solution

def with_e(pr, u, K, e_star, strip_modulus, ne=8, verbose=False):
    """pr, u: converged 5-zone foil solution of hs_bite.Problem. Returns (P3 problem, vector) with zone E, or None."""
    q = pr.post(u)
    p_old, bnd_old, g0_old, hn_old = pr.unpack(u)
    x = pr.nodes(bnd_old)
    b = q['boundaries_m']
    i2, i3 = pr.idx[2], pr.idx[3]
    jbe = None
    for j in range(i2, i3):
        pm = 0.5 * (p_old[j] + p_old[j + 1])
        r = hn_old * (p_old[j + 1] - p_old[j]) / (2 * pr.beta * pr.tau(pm)[0] * (x[j + 1] - x[j]))
        if r > 1.0 and j > i2 + 1:
            jbe = j
            break
    if jbe is None:
        return None
    pe = P3(pr.h0, pr.h1, pr.R, K, pr.mu, pr.tb, pr.tf, e_star, n=(3, 16, 24, ne, 16, 3), zone_e=True, strip_modulus=strip_modulus)
    pe.cap = pr.cap
    b_e = [b[0], b[1], b[2], x[jbe] * pr.L, b[3], b[4], b[5]]
    u0 = from_solution({'x': q['x_m'], 'p': p_old}, True, pe, b_e, g0_old, hn_old * pr.h1)
    u2, it, nrm = pe.newton(u0, maxit=80, verbose=verbose)
    return pe, u2, it

Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
cases = [('BT-V1 strip 1e13', 20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 1e13),
         ('BT-V1 strip 400GPa', 20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 400e9)]
case = json.load(open(f'{sys.argv[1]}/scenarios/band_diagnosis_battery_foil.json'))
p0 = case['pass']
cases.append(('demo F1 50->30', p0['entry_thickness_m'], p0['exit_thickness_m'], p0['work_roll_radius_m'], p0['mean_flow_stress_pa'],
              p0['friction_coefficient'], p0['entry_tension_pa'], p0['exit_tension_pa'], 210e9, 78.55e9))
for name, h0, h1, R, Yv, mu, tb, tf, Ev, sm in cases:
    pr, u, tot, m = solve_cold(h0, h1, R, Yv, mu, tb, tf, Ev, 0.3, strip_modulus=sm)
    q = pr.post(u)
    K = 2 * Yv / math.sqrt(3); es = Ev / 0.91
    scale = es / (R * K ** 2)
    print(f'{name}: 5-zone {pr.structure} Wbar {q["force_per_width_n_m"]*scale:.3f} slip {q["forward_slip"]:.4f} pmax/K {q["max_pressure_over_K"]:.3f} shear ratio {q["neutral_shear_ratio_max"]:.2f} L {q["contact_length_m"]*1e3:.4f}')
    if pr.structure != 'foil':
        continue
    try:
        out = with_e(pr, u, K, es, sm)
    except ValueError as e:
        print('   zone E failed:', e); continue
    if out is None:
        print('   no element above the friction limit: zone E has zero length'); continue
    pe, u2, it = out
    q2 = pe.post(u2)
    print(f'   with zone E: Wbar {q2["force_per_width_n_m"]*scale:.3f} ({(q2["force_per_width_n_m"]/q["force_per_width_n_m"]-1)*100:+.2f} %) slip {q2["forward_slip"]:.4f} it {it} pmax/K {q2["pmax_over_k"]:.3f} peak at {q2["p_peak_x_m"]*1e3:.4f} mm bounds mm {[round(v*1e3,4) for v in q2["bounds_m"]]} shear ratio max {q2["max_shear_ratio"]:.3f} net {q2["net_shear"]:.3f} minp {q2["min_p"]:.2f} max dh A/E/F {tuple(round(v,6) for v in q2["max_dh"])} E thinning/h1 {q2["h_e_drop"]:.2e} L {q2["contact_length_m"]*1e3:.4f}')
