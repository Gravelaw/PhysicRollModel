import sys, math, json
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
case = json.load(open(f'{sys.argv[1]}/scenarios/band_diagnosis_battery_foil.json'))
p0 = case['pass']
def info(pr, u):
    p, bnd, g0, hn = pr.unpack(u)
    x = pr.nodes(bnd); i2, i3 = pr.idx[2], pr.idx[3]
    S = sum(2 * pr.beta / hn * pr.tau(0.5 * (p[j] + p[j + 1]))[0] * (x[j + 1] - x[j]) for j in range(i2, i3))
    q = pr.post(u); b = q['boundaries_m']
    return (p[i3] - p[i2]) / S, [round((y - z) * 1e6) for z, y in zip(b, b[1:])], p[i2], p[i3], q['force_per_width_n_m'], q['forward_slip']
r = p0
for mu in (0.026, 0.028, 0.03, 0.032, 0.034, 0.038):
    for zones in ((3, 16, 24, 16, 3), (4, 24, 40, 24, 4)):
        try:
            pr, u, tot, m = solve_cold(r['entry_thickness_m'], r['exit_thickness_m'], p0['work_roll_radius_m'], r['mean_flow_stress_pa'], mu,
                                       r['entry_tension_pa'], r['exit_tension_pa'], 210e9, 0.3, strip_modulus=78.55e9, zones=zones)
            if pr.structure == 'foil':
                rn, zl, pa, pb, F, sl = info(pr, u)
                print(f'mu {mu} zones {zones[2]} foil  net shear/limit {rn:.3f} zones um {zl} p_a/K {pa:.2f} p_b/K {pb:.2f} F/w {F:.4e} slip {sl:.3f}')
            else:
                q = pr.post(u)
                print(f'mu {mu} zones {zones[2]} conventional F/w {q["force_per_width_n_m"]:.4e} slip {q["forward_slip"]:.3f}')
        except ValueError as e:
            print('mu', mu, 'FAILED', str(e)[:80])
