import sys, math
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from run_v1 import from_mattress
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
h0, h1, R, mu, tb, tf = 60e-6, 30e-6, 0.089, 0.03, 0.0, 0.0
pr, u, m = from_mattress(h0, h1, R, Y, mu, tb, tf, E, nu, (3, 16, 24, 16, 3))
u, it, nrm = pr.newton(u)
lam = 0.0
for step in [0.1]*6 + [0.02]*10:
    pr.lam = lam + step
    try:
        u, it, nrm = pr.newton(u, maxit=30)
    except ValueError as e:
        print('fail', pr.lam, e); break
    lam = pr.lam
    p, bnd, g0, hn = pr.unpack(u)
    x = pr.nodes(bnd); h, _ = pr.gap(x, p, g0)
    i1, i2, i3, i4 = pr.idx[1:5]
    q = pr.post(u)
    print(f'lam {lam:.2f} it {it} zones', ' '.join(f'{(b-a):.4f}' for a, b in zip(bnd, bnd[1:])), f'hn {hn:.5f} shear {q["neutral_shear_ratio_max"]:.2f} p_a {p[i2]:.3f} p_b {p[i3]:.3f} pmax {max(p):.3f} dh_exit_first {h[i3+1]-h[i3]:.2e} dh_entry_last {h[i2]-h[i2-1]:.2e}')
