import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
from sens import clone, phys, to_scaled
Yps = 150e6; Y = Yps * math.sqrt(3) / 2
capf = float(sys.argv[2])
pr, u, tot, m = solve_cold(50e-6, 25e-6, 0.135, Y, 0.03, 20e6, 20e6, 210e9, 0.3, cap=capf)
ph = phys(pr, u)
mu, step = 0.03, 0.002
while mu < 0.1 - 1e-9 and step > 1e-5:
    new = min(0.10, mu + step)
    pp = clone(pr, mu=new)
    try:
        uu, it, nrm = pp.newton(to_scaled(pp, ph), maxit=30)
        q = pp.post(uu)
        if q['min_p'] < 0 or q['max_dh_slip'] > 1e-7: raise ValueError('inadmissible')
    except ValueError as e:
        step *= 0.5; continue
    ph = phys(pp, uu); pr = pp; mu = new
    b = q['boundaries_m']
    print(f'mu {mu:.4f} F/w {q["force_per_width_n_m"]:.4e} slip {q["forward_slip"]:.4f} pmax/K {q["max_pressure_over_K"]:.2f} 2mu*pmax/K {2*mu*q["max_pressure_over_K"]:.2f} it {it} zones um {[round((y-x)*1e6) for x,y in zip(b,b[1:])]}')
    step = min(step * 1.3, 0.004)
print('stopped at mu', mu, 'step', step)
