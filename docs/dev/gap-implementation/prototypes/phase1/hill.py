import sys, math, json
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
def margins(pr, u):
    if pr.structure != 'foil':
        return None
    p, bnd, g0, hn = pr.unpack(u)
    x = pr.nodes(bnd)
    i2, i3 = pr.idx[2], pr.idx[3]
    # S(a,k) = (2/h_n) Int T dx, scaled: (2*beta/hn) * sum Tm dX
    fwd = [0.0]
    for j in range(i2, i3):
        fwd.append(fwd[-1] + 2 * pr.beta / hn * pr.tau(0.5 * (p[j] + p[j + 1]))[0] * (x[j + 1] - x[j]))
    tot = fwd[-1]
    m1 = min(p[i2] + fwd[k - i2] - p[k] for k in range(i2, i3 + 1))
    m2 = min(p[i3] + (tot - fwd[k - i2]) - p[k] for k in range(i2, i3 + 1))
    ratio = max(abs(hn * (p[j + 1] - p[j]) / (2 * pr.beta * pr.tau(0.5 * (p[j] + p[j + 1]))[0] * (x[j + 1] - x[j]))) for j in range(i2, i3))
    first = hn * (p[i2 + 1] - p[i2]) / (2 * pr.beta * pr.tau(0.5 * (p[i2] + p[i2 + 1]))[0] * (x[i2 + 1] - x[i2]))
    # yield in contact zones: f = P + sigma/K - 1 <= 0
    i1, i4, n = pr.idx[1], pr.idx[4], pr.n
    return m1, m2, ratio, first
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
cases = [('BT-V1', 20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 80e9), ('30->15', 30e-6, 15e-6, 0.089, Y, 0.03, 0, 0, E, 80e9),
         ('20->10', 20e-6, 10e-6, 0.089, Y, 0.03, 0, 0, E, 80e9), ('BT-V1 soft strip 40GPa', 20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 40e9)]
case = json.load(open(f'{sys.argv[1]}/scenarios/band_diagnosis_battery_foil.json'))
p = case['pass']
for r in case['schedule']:
    if r['exit_thickness_m'] <= 30e-6:
        cases.append((r['label'][:12], r['entry_thickness_m'], r['exit_thickness_m'], p['work_roll_radius_m'], r['mean_flow_stress_pa'], r['friction_coefficient'], r['entry_tension_pa'], r['exit_tension_pa'], 210e9, 78.55e9))
for name, h0, h1, R, Yv, mu, tb, tf, Ev, sm in cases:
    pr, u, tot, m = solve_cold(h0, h1, R, Yv, mu, tb, tf, Ev, 0.3, strip_modulus=sm)
    mg = margins(pr, u)
    print(f'{name:24s} {pr.structure} hill margins/K: from x_a {mg[0]:.4f}, from x_b {mg[1]:.4f}; max pointwise ratio {mg[2]:.3f}; first element ratio {mg[3]:.3f}')
