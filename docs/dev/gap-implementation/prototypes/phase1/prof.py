import sys, math
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve import solve_cold
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
R, h0, h1, mu = 0.089, 20e-6, 15e-6, 0.03
zones = (4, 24, 40, 24, 4)
pr, u, tot, m = solve_cold(h0, h1, R, Y, mu, 0.0, 0.0, E, nu, zones, float(sys.argv[2]))
q = pr.post(u)
p, bnd, g0, hn = pr.unpack(u)
x = pr.nodes(bnd)
h, _ = pr.gap(x, p, g0)
idx = pr.idx
print('idx', idx, 'Wbar', q['force_per_width_n_m']*Es/(R*Ys**2), 'hn', hn)
for j in range(pr.n + 1):
    zone = sum(1 for i in idx[1:] if j >= i)
    line = f'{j:3d} z{zone} x {x[j]*pr.L*1e3:8.4f} mm  p/K {p[j]:7.4f}  h_p/h1 {h[j]:.5f}'
    if j < pr.n:
        dp = p[j+1]-p[j]; pm = 0.5*(p[j]+p[j+1]); dx = x[j+1]-x[j]
        # shear needed to keep yield with flat h: q/(mu p) = hn*dp/(2 beta mu pm dx)
        if idx[2] <= j < idx[3]:
            line += f'  q/(mu p) {hn*dp/(2*pr.beta*mu*pm*dx):7.3f}'
    print(line)
