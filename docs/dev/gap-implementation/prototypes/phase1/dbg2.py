import sys, math
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from run_v1 import from_mattress
import hs_bite
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
fac = float(sys.argv[2])
pr, u, m = from_mattress(20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E * fac, nu, (3, 16, 24, 16, 3))
pr.lam = 1.0
n = pr.n
for it in range(14):
    res, jac = pr.residual(u, True)
    norm = max(abs(v) for v in res)
    worst = max(range(len(res)), key=lambda i: abs(res[i]))
    p, bnd, g0, hn = pr.unpack(u)
    print(it, f'{norm:.2e} worst row {worst}', ' '.join(f'{b:.5f}' for b in bnd), f'g0 {g0:.5f}', 'p:', ' '.join(f'{v:.2f}' for v in p[:6]), '|', ' '.join(f'{v:.2f}' for v in p[-6:]))
    du = hs_bite.lu_solve(hs_bite.lu_factor(jac), [-v for v in res])
    step = 1.0
    while step > 1e-3:
        tr = [a + step * b for a, b in zip(u, du)]
        if pr.admissible(tr):
            nt = max(abs(v) for v in pr.residual(tr))
            if nt < norm: break
        step *= 0.5
    print('    step', step, 'dbnd', ' '.join(f'{b:.2e}' for b in du[n-1:n-1+pr.nb]))
    u = tr
