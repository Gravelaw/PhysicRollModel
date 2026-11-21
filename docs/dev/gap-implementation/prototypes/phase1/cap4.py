import sys, math
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_final import solve, net_shear
from hs_solve2 import needs_foil, convert
from sens import clone, phys, to_scaled
Yps = 150e6
pr, u, tot, m, info = solve(50e-6, 25e-6, 0.135, Yps * math.sqrt(3) / 2, 0.03, 20e6, 20e6, 210e9, 0.3)
print('start', pr.structure)
ph = phys(pr, u); mu, step = 0.03, 0.002
targets = [0.05, 0.10]
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
            print('  switched to foil at mu', new)
        if q['max_dh_slip'] > 1e-7: raise ValueError('thickening')
    except ValueError as e:
        step *= 0.5
        if step < 1e-5: print('FAILED at', mu, e); break
        continue
    pr, mu, ph = pp, new, phys(pp, uu)
    step = min(step * 1.3, 0.004)
    if abs(mu - targets[0]) < 1e-12:
        b = q['boundaries_m']
        ns = net_shear(pr, uu) if pr.structure == 'foil' else None
        print(f'mu {mu:.3f} {pr.structure} F/w {q["force_per_width_n_m"]:.4e} slip {q["forward_slip"]:.4f} pmax/K {q["max_pressure_over_K"]:.2f} net shear {ns}')
        targets.pop(0)
