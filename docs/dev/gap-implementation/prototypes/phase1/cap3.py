import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold, convert, needs_foil
Yps = 150e6; Y = Yps * math.sqrt(3) / 2
for mu in (0.02, 0.025, 0.03):
    pr, u, tot, m = solve_cold(50e-6, 25e-6, 0.135, Y, mu, 20e6, 20e6, 210e9, 0.3, verbose=(mu == 0.03))
    q = pr.post(u)
    b = q['boundaries_m']
    p, bnd, g0, hn = pr.unpack(u)
    x = pr.nodes(bnd); h, _ = pr.gap(x, p, g0)
    i1, i2, i3, i4 = pr.idx[1:5]
    print(f'mu {mu} {pr.structure} mattress {m["regime"]} F/w {q["force_per_width_n_m"]:.4e} (mattress {m["force_per_width_n_m"]:.4e}) slip {q["forward_slip"]:.4f} pmax/K {q["max_pressure_over_K"]:.2f} zones um {[round((y-x)*1e6) for x,y in zip(b,b[1:])]} hn/h1 {q["neutral_thickness_m"]/25e-6:.4f} shear {q["neutral_shear_ratio_max"]:.2f}')
    print('   h around neutral:', [f'{v:.4f}' for v in h[i2-3:i3+4]])
    print('   p around neutral:', [f'{v:.3f}' for v in p[i2-3:i3+4]])
