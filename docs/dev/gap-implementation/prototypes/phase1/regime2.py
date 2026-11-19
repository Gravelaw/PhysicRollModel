import sys, math
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_final import solve
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
R, mu = 0.089, 0.03
for r, gauges in ((0.5, (56, 52, 48, 44)), (0.25, (36, 32, 28, 24)), (0.1, (30, 26, 22, 18))):
    for g in gauges:
        h0 = g * 1e-6; h1 = h0 * (1 - r)
        pr, u, tot, m, info = solve(h0, h1, R, Y, mu, 0.0, 0.0, E, nu)
        q = pr.post(u); b = q['boundaries_m']
        nz = (b[3] - b[2]) / (b[-1] - b[0]) if pr.structure == 'foil' else 0.0
        print(f'r {r} h0 {g:3d} um {pr.structure:12s} no-slip share {nz:.3f} Wbar {q["force_per_width_n_m"]*Es/(R*Ys**2):7.2f} net shear {info["net_shear_over_limit"]} ambiguous {info["ambiguous"]} other {info["other_force"] and round(info["other_force"]*Es/(R*Ys**2),2)}')
print('--- BT-V1 and the cap case')
pr, u, tot, m, info = solve(20e-6, 15e-6, R, Y, mu, 0.0, 0.0, E, nu)
print('BT-V1', pr.structure, pr.post(u)['force_per_width_n_m'] * Es / (R * Ys ** 2), info)
Yps = 150e6
pr, u, tot, m, info = solve(50e-6, 25e-6, 0.135, Yps * math.sqrt(3) / 2, 0.03, 20e6, 20e6, 210e9, 0.3)
q = pr.post(u); b = q['boundaries_m']
print('cap case mu 0.03', pr.structure, q['force_per_width_n_m'], q['forward_slip'], q['max_pressure_over_K'], [round((y - x) * 1e6) for x, y in zip(b, b[1:])], info)
for g0_, g1_ in ((30e-6, 15e-6), (20e-6, 10e-6)):
    pr, u, tot, m, info = solve(g0_, g1_, R, Y, mu, 0.0, 0.0, E, nu)
    print(g0_, pr.structure, pr.post(u)['force_per_width_n_m'] * Es / (R * Ys ** 2), info['net_shear_over_limit'])
