import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
from physicroll import foil_bite as fb
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
h0 = 73e-6; h1 = h0 * 0.43; tb, tf = 0.107 * Ys, 0.132 * Ys
def wbar_hs(mu, R):
    pr, u, tot, m = solve_cold(h0, h1, R, Y, mu, tb, tf, E, nu)
    return pr.post(u)['force_per_width_n_m'] * Es / (R * Ys ** 2), pr.structure, pr.post(u)['forward_slip']
def wbar_m(mu, R):
    m = fb.solve_mattress_bite(h0, h1, 1.0, R, Y, mu, tb, tf, roll_youngs_modulus_pa=E, roll_poisson_ratio=nu)
    return m['force_per_width_n_m'] * Es / (R * Ys ** 2), m['regime'], m['forward_slip_fraction']
for R in (0.089, 0.135):
    for name, fun in (('half-space', wbar_hs), ('mattress', wbar_m)):
        lo, hi = 0.012, 0.05
        try:
            flo, fhi = fun(lo, R)[0] - 58, fun(hi, R)[0] - 58
            if flo * fhi > 0:
                print(R, name, 'no bracket', flo + 58, fhi + 58); continue
            for _ in range(22):
                mid = math.sqrt(lo * hi)
                fm = fun(mid, R)[0] - 58
                if (fm < 0) == (flo < 0): lo, flo = mid, fm
                else: hi = mid
            w, reg, slip = fun(math.sqrt(lo * hi), R)
            print(f'R {R} {name}: friction for W_bar 58 = {math.sqrt(lo*hi):.5f} ({reg}, slip {slip:.4f}); published inference 0.026')
        except ValueError as e:
            print(R, name, 'FAILED', str(e)[:120])
