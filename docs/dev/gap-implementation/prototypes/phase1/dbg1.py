import sys, math
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from run_v1 import from_mattress
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
pr, u, m = from_mattress(20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, nu, (3, 16, 24, 16, 3))
r = pr.residual(u)
print(len(r), len(u), pr.idx)
for i, v in enumerate(r):
    print(i, f'{v:.3e}')
p, bnd, g0, hn = pr.unpack(u)
print(bnd, g0, hn, pr.L, pr.a1, pr.a2, pr.beta, pr.winkler)
print([round(v,3) for v in p])
print(m['pressure_plastic_entry_pa']/pr.K, m['pressure_flat_start_pa']/pr.K, m['pressure_flat_end_pa']/pr.K, m['pressure_plastic_exit_pa']/pr.K, m['max_pressure_pa']/pr.K)
