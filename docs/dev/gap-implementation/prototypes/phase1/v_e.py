"""Check 1: zone E on BT-V1 in the planner's own model (strip spring 80 GPa, contact end zones)."""
import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_final import solve
from hs3 import P3, from_solution
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
R, h0, h1, mu = 0.089, 20e-6, 15e-6, 0.03
pr, u, tot, m, info = solve(h0, h1, R, Y, mu, 0.0, 0.0, E, nu)
q = pr.post(u)
p_old, bnd_old, g0_old, hn_old = pr.unpack(u)
b = q['boundaries_m']
old = {'x': q['x_m'], 'p': p_old}
print('5-zone: Wbar', q['force_per_width_n_m'] * Es / (R * Ys ** 2), 'slip', q['forward_slip'], 'bounds mm', [round(v * 1e3, 4) for v in b])
# same structure in the new class (no zone E) as a regression of the new code
p3 = P3(h0, h1, R, Ys, mu, 0.0, 0.0, Es, n=(3, 16, 24, 6, 16, 3), zone_e=False, strip_modulus=80e9)
u0 = from_solution(old, True, p3, b, g0_old, hn_old * h1)
u1, it, nrm = p3.newton(u0)
q1 = p3.post(u1)
print('new class, no E: Wbar', q1['force_per_width_n_m'] * Es / (R * Ys ** 2), 'it', it, 'shear ratio max', q1['max_shear_ratio'], 'net', q1['net_shear'])
# with zone E: start x_be 12 % of the flat length before x_b
for ne in (6, 12):
    pe = P3(h0, h1, R, Ys, mu, 0.0, 0.0, Es, n=(3, 16, 24, ne, 16, 3), zone_e=True, strip_modulus=80e9)
    xa, xb = b[2], b[3]
    b_e = [b[0], b[1], xa, xb - 0.12 * (xb - xa), xb, b[4], b[5]]
    u0 = from_solution(old, True, pe, b_e, g0_old, hn_old * h1)
    t = time.perf_counter()
    u2, it, nrm = pe.newton(u0, maxit=60)
    q2 = pe.post(u2)
    print(f'zone E (nE={ne}): Wbar {q2["force_per_width_n_m"]*Es/(R*Ys**2):.4f} slip {q2["forward_slip"]:.5f} it {it} t {time.perf_counter()-t:.2f}s bounds mm {[round(v*1e3,4) for v in q2["bounds_m"]]} pmax/K {q2["pmax_over_k"]:.4f} at {q2["p_peak_x_m"]*1e3:.4f} mm shear ratio max {q2["max_shear_ratio"]:.3f} net {q2["net_shear"]:.3f} minp {q2["min_p"]:.3f} max dh A/E/F {q2["max_dh"]} thinning in E/h1 {q2["h_e_drop"]:.2e} L {q2["contact_length_m"]*1e3:.4f}')
