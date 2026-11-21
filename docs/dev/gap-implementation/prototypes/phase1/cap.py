import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
from sens import clone, phys, to_scaled
from physicroll import foil_bite as fb
# 50 -> 25 um, R 0.135, plane-strain yield 150 MPa, tensions 20/20 MPa (BT-V4 geometry), nominal Coulomb friction
Yps = 150e6; Y = Yps * math.sqrt(3) / 2
for mu in (0.03, 0.05, 0.06):
    try:
        m = fb.solve_mattress_bite(50e-6, 25e-6, 1.0, 0.135, Y, mu, 20e6, 20e6)
        print('mattress mu', mu, m['force_per_width_n_m'], m['max_coulomb_shear_over_yield_shear'])
    except ValueError as e:
        print('mattress mu', mu, 'REJECTED', str(e)[:90])
pr, u, tot, m = solve_cold(50e-6, 25e-6, 0.135, Y, 0.03, 20e6, 20e6, 210e9, 0.3)
q = pr.post(u)
print('hs mu 0.03', pr.structure, q['force_per_width_n_m'], q['forward_slip'], q['max_pressure_over_K'], 'mu*pmax/(K/2)', 2*0.03*q['max_pressure_over_K'])
ph = phys(pr, u)
mu = 0.03
while mu < 0.1 - 1e-9:
    mu = min(0.10, mu + 0.005)
    pp = clone(pr, mu=mu)
    try:
        uu, it, nrm = pp.newton(to_scaled(pp, ph), maxit=40)
    except ValueError as e:
        print('  continuation in mu failed at', mu, e); break
    q = pp.post(uu)
    ph = phys(pp, uu); pr = pp
    capped = 2 * mu * q['max_pressure_over_K'] > 1
    print(f'hs mu {mu:.3f} {pp.structure} F/w {q["force_per_width_n_m"]:.4e} slip {q["forward_slip"]:.4f} pmax/K {q["max_pressure_over_K"]:.2f} cap active {capped} it {it} work {q["work_residual_relative"]:.1e} minp {q["min_p"]:.2f}')
