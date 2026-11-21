import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold, needs_foil, convert
from sens import clone, phys, to_scaled
import hs_select as S

def march_mu(pr, u, targets, cb, step0=0.002, grow=1.3, smax=0.004):
    ph = phys(pr, u); mu, step = pr.mu, step0
    targets = list(targets)
    while targets:
        new = min(targets[0], mu + step)
        pp = clone(pr, mu=new)
        try:
            uu, it, nrm = pp.newton(to_scaled(pp, ph), maxit=30)
            q = pp.post(uu)
            if q['min_p'] < 0: raise ValueError('p<0')
            if pp.structure == 'conventional' and needs_foil(pp, uu):
                pp2, u2 = convert(pp, uu, 'foil'); pp2.base_zones = pp.base_zones
                uu, it, nrm = pp2.newton(u2, maxit=40); pp = pp2; q = pp.post(uu)
            if q['max_dh_slip'] > 1e-7: raise ValueError('thickening')
        except ValueError as e:
            step *= 0.5
            if step < 1e-6: raise ValueError(f'march failed at {mu}: {e}')
            continue
        pr, mu, ph, u = pp, new, phys(pp, uu), uu
        step = min(step * grow, smax)
        if abs(mu - targets[0]) < 1e-12:
            cb(pr, u); targets.pop(0)
    return pr, u

if sys.argv[2] == 'cap':
    Yps = 150e6; es = 210e9 / 0.91; scale = es / (0.135 * Yps ** 2)
    for capf in (1.0, 0.5):
        pr, u, tot, m = solve_cold(50e-6, 25e-6, 0.135, Yps * math.sqrt(3) / 2, 0.03, 20e6, 20e6, 210e9, 0.3, cap=capf)
        def cb(pr_, u_):
            try:
                p3, u3, trail = S.select_from(pr_, u_, Yps, es, 80e9)
                q = p3.post(u3); bm = q['bounds_m']
                print(f'cap {capf} mu {pr_.mu:.3f}: {trail[-1][1]} F/w {q["force_per_width_n_m"]:.5e} slip {q["forward_slip"]:.4f} pmax/K {q["pmax_over_k"]:.2f} B {1e6*(bm[3]-bm[2]):.0f} E {1e6*(bm[4]-bm[3]):.0f} um L {q["contact_length_m"]*1e3:.3f} mm cap active {2*pr_.mu*q["pmax_over_k"] > capf} trail {[t[0] for t in trail]}')
            except ValueError as e:
                print(f'cap {capf} mu {pr_.mu:.3f}: select failed {str(e)[:200]}')
        march_mu(pr, u, [0.05, 0.10], cb)
else:
    # TM-LC7 stand 2 with the paper's process assumptions: rigid rolls, friction factor m on shear yield k
    k = 535.65e6; m_f = 0.054; K = 2 * k; Y = math.sqrt(3) * k
    h0, h1, R, w = 324e-6, 216e-6, 0.245, 0.732
    tb, tf = 151e6, 81e6
    for Eroll in (210e9, 2e12, 2e13):
        try:
            t = time.perf_counter()
            pr, u, tot, mm = solve_cold(h0, h1, R, Y, 0.02, tb, tf, Eroll, 0.3, strip_modulus=200e9 / 0.91, cap=m_f)
            q = pr.post(u)
            print(f'E_roll {Eroll:.1e} mu 0.02 {pr.structure} F/w {q["force_per_width_n_m"]:.4e} slip {q["forward_slip"]:.4f} L {q["contact_length_m"]*1e3:.3f} mm pmax/K {q["max_pressure_over_K"]:.3f} (mattress {mm["regime"]} {mm["force_per_width_n_m"]:.4e}) t {time.perf_counter()-t:.1f}s')
            def cb(pr_, u_):
                q_ = pr_.post(u_)
                print(f'   mu {pr_.mu:.3f} {pr_.structure} F/w {q_["force_per_width_n_m"]:.5e} slip {q_["forward_slip"]:.5f} L {q_["contact_length_m"]*1e3:.4f} pmax/K {q_["max_pressure_over_K"]:.3f} cap active everywhere {pr_.mu * min(v for v in pr_.unpack(u_)[0][1:-1]) > m_f/2}')
            march_mu(pr, u, [0.04, 0.08, 0.3], cb, step0=0.005, grow=1.5, smax=0.05)
        except ValueError as e:
            print(f'E_roll {Eroll:.1e} FAILED {str(e)[:200]}')
