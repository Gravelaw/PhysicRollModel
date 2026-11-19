"""Final structure check (planner prototype): after the march, a foil solution whose no-slip
zone needs more net shear than the friction limit is replaced by the conventional solution
when that one converges and does not thicken before the neutral point."""
import sys, math
sys.path.insert(0, '.')
from hs_solve2 import solve_cold as _cold, convert, needs_foil

def net_shear(pr, u):
    p, bnd, g0, hn = pr.unpack(u)
    x = pr.nodes(bnd); i2, i3 = pr.idx[2], pr.idx[3]
    S = sum(2 * pr.beta / hn * pr.tau(0.5 * (p[j] + p[j + 1]))[0] * (x[j + 1] - x[j]) for j in range(i2, i3))
    return abs(p[i3] - p[i2]) / S

def solve(*a, **k):
    pr, u, tot, m = _cold(*a, **k)
    info = {'net_shear_over_limit': None, 'ambiguous': False, 'other_force': None}
    if pr.structure == 'foil':
        ns = net_shear(pr, u)
        info['net_shear_over_limit'] = ns
        if ns > 1.0:
            f_foil = pr.post(u)['force_per_width_n_m']
            try:
                pr2, u2 = convert(pr, u, 'conventional')
                u3, it, nrm = pr2.newton(u2, maxit=40)
                q = pr2.post(u3)
                if q['min_p'] < 0:
                    raise ValueError('p<0')
                if not needs_foil(pr2, u3):
                    info['other_force'] = f_foil
                    return pr2, u3, tot + it, m, info
                info['other_force'] = q['force_per_width_n_m']
            except ValueError:
                pass
            info['ambiguous'] = True
    return pr, u, tot, m, info

if __name__ == '__main__':
    import json, time
    sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
    from sens import derive
    for name in ('battery_foil', 'lengthwise_bands'):
        case = json.load(open(f'{sys.argv[1]}/scenarios/band_diagnosis_{name}.json'))
        p = case['pass']; st = case['stand']
        for s in [p] + case['schedule']:
            label = s.get('label', 'case pass')[:6]
            t = time.perf_counter()
            pr, u, tot, m, info = solve(s['entry_thickness_m'], s['exit_thickness_m'], p['work_roll_radius_m'], s['mean_flow_stress_pa'],
                                         s['friction_coefficient'], s['entry_tension_pa'], s['exit_tension_pa'], st['roll_youngs_modulus_pa'],
                                         st['roll_poisson_ratio'], strip_modulus=case['material']['youngs_modulus_pa'] / (1 - 0.33 ** 2))
            tc = time.perf_counter() - t
            q = pr.post(u); d = derive(pr, u); F = q['force_per_width_n_m']
            ns = info['net_shear_over_limit']
            print(f'{name[:7]} {label:9s} {pr.structure:12s} F/w {F:.4e} slip {q["forward_slip"]:.3f} L {q["contact_length_m"]*1e3:.3f} Q {-d["F_h1"]:.3e} Nx {-d["F_tf"]:.3e} e_mu {d["F_mu"]*pr.mu/F:.2f} net shear {ns if ns is None else round(ns,3)} ambiguous {info["ambiguous"]} other F {info["other_force"]} cold {tc:.2f}s')
