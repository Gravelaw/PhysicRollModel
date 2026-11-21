import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
R, mu = 0.089, 0.03
def h0c(r): return 12 * R * r ** 0.5 * mu ** 1.24 * (Ys / Es) ** 0.76
for r, gauges in ((0.5, (70, 60, 56, 52, 48, 44, 40)), (0.25, (44, 40, 36, 32, 28, 24)), (0.1, (30, 26, 22, 18, 14))):
    print('r', r, 'eq29 h0c um', h0c(r) * 1e6)
    for g in gauges:
        h0 = g * 1e-6; h1 = h0 * (1 - r)
        try:
            pr, u, tot, m = solve_cold(h0, h1, R, Y, mu, 0.0, 0.0, E, nu)
            q = pr.post(u)
            b = q['boundaries_m']
            nz = (b[3] - b[2]) / (b[-1] - b[0]) if pr.structure == 'foil' else 0.0
            print(f'  h0 {g:3d} um {pr.structure:12s} neutral share {nz:.3f} Wbar {q["force_per_width_n_m"]*Es/(R*Ys**2):7.2f} mattress {m["regime"]} {m["force_per_width_n_m"]*Es/(R*Ys**2):7.2f}')
        except ValueError as e:
            print(f'  h0 {g} FAILED {str(e)[:100]}')
