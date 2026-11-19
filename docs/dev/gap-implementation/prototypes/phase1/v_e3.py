"""Zone E near the regime boundary: start from the conventional solution."""
import sys, math, time, json
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold, convert, needs_foil
from hs3 import P3, from_solution

def conventional(pr, u):
    if pr.structure == 'conventional':
        return pr, u
    pr2, u2 = convert(pr, u, 'conventional')
    u3, it, nrm = pr2.newton(u2, maxit=60)
    return pr2, u3

def six_zone_from_conventional(prc, uc, K, es, sm, n=(3, 16, 8, 16, 16, 3), verbose=False):
    q = prc.post(uc)
    p, bnd, g0, hn = prc.unpack(uc)
    x = prc.nodes(bnd)
    h, _ = prc.gap(x, p, g0)
    i1, i2 = prc.idx[1], prc.idx[2]
    rising = [j for j in range(i1, i2) if h[j + 1] > h[j]]
    b = q['boundaries_m']     # ci, xi, xn, xe, cx
    L = prc.L
    if not rising:
        return None, 'conventional is admissible (no thickening before the neutral point)'
    xa = x[rising[0]] * L
    xbe = x[rising[-1] + 1] * L
    xn = b[2]
    if xbe >= xn - 1e-9:
        xbe = xa + 0.5 * (xn - xa)
    pe = P3(prc.h0, prc.h1, prc.R, K, prc.mu, prc.tb, prc.tf, es, n=n, zone_e=True, strip_modulus=sm)
    pe.cap = prc.cap
    u0 = from_solution({'x': q['x_m'], 'p': p}, False, pe, [b[0], b[1], xa, xbe, xn, b[3], b[4]], g0, min(h[rising[0]:rising[-1] + 2]) * prc.h1)
    u2, it, nrm = pe.newton(u0, maxit=80, verbose=verbose)
    return (pe, u2, it), f'thickening over {(xbe - xa)*1e6:.0f} um, max rise {max(h[j+1]-h[j] for j in rising):.2e}'

Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
case = json.load(open(f'{sys.argv[1]}/scenarios/band_diagnosis_battery_foil.json'))
p0 = case['pass']
cases = [('demo F1 50->30', p0['entry_thickness_m'], p0['exit_thickness_m'], p0['work_roll_radius_m'], p0['mean_flow_stress_pa'],
          p0['friction_coefficient'], p0['entry_tension_pa'], p0['exit_tension_pa'], 210e9, 78.55e9)]
for g in (56, 52, 50, 48):
    cases.append((f'r0.5 {g}um', g * 1e-6, g * 0.5e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 80e9))
for name, h0, h1, R, Yv, mu, tb, tf, Ev, sm in cases:
    K = 2 * Yv / math.sqrt(3); es = Ev / 0.91; scale = es / (R * K ** 2)
    pr, u, tot, m = solve_cold(h0, h1, R, Yv, mu, tb, tf, Ev, 0.3, strip_modulus=sm)
    q5 = pr.post(u)
    try:
        prc, uc = conventional(pr, u)
        qc = prc.post(uc)
        txt = f'conventional Wbar {qc["force_per_width_n_m"]*scale:.3f} slip {qc["forward_slip"]:.4f} thickens {needs_foil(prc, uc)}'
    except ValueError as e:
        prc = None; txt = f'conventional failed {e}'
    print(f'{name}: march gave {pr.structure} Wbar {q5["force_per_width_n_m"]*scale:.3f} slip {q5["forward_slip"]:.4f}; {txt}')
    if prc is None: continue
    try:
        out, note = six_zone_from_conventional(prc, uc, K, es, sm)
    except ValueError as e:
        print('   six-zone failed:', e); continue
    if out is None:
        print('  ', note); continue
    pe, u2, it = out
    q2 = pe.post(u2)
    bm = q2['bounds_m']
    print(f'   six-zone ({note}): Wbar {q2["force_per_width_n_m"]*scale:.3f} slip {q2["forward_slip"]:.4f} it {it} zones um A {1e6*(bm[2]-bm[1]):.0f} B {1e6*(bm[3]-bm[2]):.0f} E {1e6*(bm[4]-bm[3]):.0f} F {1e6*(bm[5]-bm[4]):.0f} shear max {q2["max_shear_ratio"]:.3f} net {q2["net_shear"]:.3f} minp {q2["min_p"]:.2f} max dh A/E/F {tuple(round(v,6) for v in q2["max_dh"])}')
