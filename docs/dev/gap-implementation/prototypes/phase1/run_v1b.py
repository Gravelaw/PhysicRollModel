import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from run_v1 import from_mattress, interp
from hs_bite import Problem

Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
R, h0, h1, mu = 0.089, 20e-6, 15e-6, 0.03
zones = (3, 16, 24, 16, 3)
fac = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
pr, u, m = from_mattress(h0, h1, R, Y, mu, 0.0, 0.0, E * fac, nu, zones)
print('mattress regime at stiff', m['regime'], m['force_per_width_n_m'], [m[k] for k in ('contact_start_m','plastic_entry_m','flat_zone_start_m','plastic_exit_m','contact_end_m')])
pr.lam = 1.0; pr.closure = "j4"
print(pr.structure, pr.zones, len(u))
r = pr.residual(u)
print('initial residual', max(abs(v) for v in r))
t = time.perf_counter()
u, it, nrm = pr.newton(u, verbose=True, maxit=60)
print('newton', it, nrm, time.perf_counter() - t)
q = pr.post(u)
for k in ('force_per_width_n_m', 'forward_slip', 'boundaries_m', 'max_pressure_over_K', 'work_residual_relative', 'min_p', 'max_dh_slip'):
    print(k, q[k])
