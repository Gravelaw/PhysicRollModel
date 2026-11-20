"""Forward slip with zone E: flat (no-slip) thickness against the thickness at the E/F boundary.
Work identity with either flow thickness. Sensitivities of the E/F-based slip. Stdlib only."""
import sys, math, json, time
sys.dont_write_bytecode = True
from hs_select import select, clone, rescale
from hs_bite import lu_factor, lu_solve

def slips(p3, q):
    ie = p3.idx[4]
    return q['forward_slip'], q['h'][ie] - 1.0

def work(p3, q, flow, creep_term):
    """relative residual of 2*traction + tension - plastic - 2*slip, over 2*traction"""
    i1, i2, i3, ie, i4 = p3.idx[1:6]; n = p3.n
    x = [v / p3.L for v in q['x']]; p = q['p']; h = q['h']; K, L, h1 = p3.K, p3.L, p3.h1
    hn = q['forward_slip'] + 1.0
    hf = hn if flow == 'flat' else h[ie]
    trac = 0.0; slip = 0.0
    def seg(a, b, sign, capped):
        nonlocal trac, slip
        for j in range(a, b):
            pm = 0.5 * (p[j] + p[j + 1]); dx = x[j + 1] - x[j]; hm = 0.5 * (h[j] + h[j + 1])
            t = (p3.tau(pm)[0] if capped else p3.mu * pm) * sign
            trac += t * dx
            slip += t * (1.0 - hf / hm) * dx
    seg(0, i1, +1, False); seg(i1, i2, +1, True)
    tb_ = hn / (2 * p3.beta) * (p[i3] - p[i2])          # Int tau dX over B from eq. (16)
    trac += tb_
    if creep_term: slip += tb_ * (1.0 - hf / hn)
    seg(i3, ie, +1, True); seg(ie, i4, -1, True); seg(i4, n, -1, False)
    trac *= K * L; slip *= K * L
    tension = hf * h1 * (p3.tf - p3.tb); plastic = hf * h1 * K * math.log(p3.h0 / h1)
    return (2 * trac + tension - plastic - 2 * slip) / (2 * trac), slip, tb_ * K * L * (1.0 - hf / hn)

def derive2(p3, u):
    res, jac = p3.residual(u, True); lu = lu_factor(jac); out = {}
    steps = {'h1': 1e-3 * p3.h1, 'h0': 1e-3 * p3.h0, 'tb': 1e-3 * p3.K, 'tf': 1e-3 * p3.K, 'mu': 1e-3 * p3.mu, 'K': 1e-3 * p3.K}
    for name, d in steps.items():
        vals = []
        for sgn in (+1, -1):
            base = getattr(p3, name)
            one = name in ('tb', 'tf') and base - d < 0
            pp = clone(p3, **({name: base + (2 * d if sgn > 0 else 0.0)} if one else {name: base + sgn * d}))
            v = rescale(p3, u, pp)
            for it in range(40):
                r = pp.residual(v)
                if max(abs(z) for z in r) < 1e-10: break
                v = [a + b for a, b in zip(v, lu_solve(lu, [-z for z in r]))]
            else: raise ValueError('chord')
            vals.append(slips(pp, pp.post(v)))
        for k, nm in ((0, 'flat'), (1, 'ef')):
            out[f'f_{name}_{nm}'] = (vals[0][k] - vals[1][k]) / (2 * d)
    return out

if __name__ == '__main__':
    root = sys.argv[1]
    Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; E = Es * 0.91
    cases = [('BT-V1 rigid', 20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 1e13)]
    for r, gs in ((0.5, (52, 48, 44)), (0.25, (32, 28)), (0.1, (26, 22))):
        for g in gs:
            cases.append((f'r{r} {g}um', g * 1e-6, g * 1e-6 * (1 - r), 0.089, Y, 0.03, 0.0, 0.0, E, 80e9))
    cases.append(('cap case mu0.03', 50e-6, 25e-6, 0.135, 150e6 * math.sqrt(3) / 2, 0.03, 20e6, 20e6, 210e9, 80e9))
    case = json.load(open(f'{root}/scenarios/band_diagnosis_battery_foil.json'))
    pp_ = case['pass']; st = case['stand']
    for s in case['schedule']:
        cases.append(('batt ' + s['label'][:12], s['entry_thickness_m'], s['exit_thickness_m'], pp_['work_roll_radius_m'], s['mean_flow_stress_pa'],
                      s['friction_coefficient'], s['entry_tension_pa'], s['exit_tension_pa'], st['roll_youngs_modulus_pa'], case['material']['youngs_modulus_pa'] / (1 - 0.33 ** 2)))
    for name, h0, h1, R, Yv, mu, tb, tf, Ev, sm in cases:
        try:
            p3, u3, trail = select(h0, h1, R, Yv, mu, tb, tf, Ev, 0.3, sm)
        except ValueError as e:
            print(name, 'FAILED', str(e)[:80]); continue
        if not (p3.flat and p3.zone_e):
            print(f'{name:22s} {trail[-1][1]}: no zone E'); continue
        q = p3.post(u3); sf, se = slips(p3, q)
        K = p3.K; er = Ev / 0.91
        w_ef, slip_tot, bterm = work(p3, q, 'ef', True)
        w_ef0 = work(p3, q, 'ef', False)[0]; w_fl = work(p3, q, 'flat', False)[0]
        d = derive2(p3, u3)
        F = q['force_per_width_n_m']
        print(f'{name:22s} slip flat {sf:.6f} E/F {se:.6f} rel {sf/se-1:.4f} creep {1-(1+se)/(1+sf):.5f} roll strain 0.571*pmax/E* {0.571*q["pmax_over_k"]*K/er:.5f} | work res: E/F+B {w_ef:.2e}, E/F no B {w_ef0:.2e}, flat {w_fl:.2e}; B share of slip {bterm/slip_tot:.4f} | f_h1 flat {d["f_h1_flat"]:.5e} ef {d["f_h1_ef"]:.5e}; e_f(mu) flat {d["f_mu_flat"]*mu/sf:.4f} ef {d["f_mu_ef"]*mu/se:.4f}; f_tb ef {d["f_tb_ef"]:.4e} f_tf ef {d["f_tf_ef"]:.4e} f_h0 ef {d["f_h0_ef"]:.4e} f_mu ef {d["f_mu_ef"]:.5f} f_K ef {d["f_K_ef"]:.4e}')
