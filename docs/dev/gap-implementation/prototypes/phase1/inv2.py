import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold, needs_foil, convert
from sens import clone, phys, to_scaled
from physicroll import foil_bite as fb
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
h0 = 73e-6; h1 = h0 * 0.43; tb, tf = 0.107 * Ys, 0.132 * Ys
def march(pr, u, mu_target, verbose=False):
    """Warm continuation in friction with admissibility checks and structure switch."""
    ph = phys(pr, u)
    mu = pr.mu
    step = (mu_target - mu)
    while abs(mu_target - mu) > 1e-12:
        new = mu + step if abs(step) < abs(mu_target - mu) else mu_target
        pp = clone(pr, mu=new)
        try:
            uu, it, nrm = pp.newton(to_scaled(pp, ph), maxit=25)
            q = pp.post(uu)
            if q['min_p'] < 0: raise ValueError('p<0')
            if pp.structure == 'conventional' and needs_foil(pp, uu):
                pp2, u2 = convert(pp, uu, 'foil')
                uu, it, nrm = pp2.newton(u2, maxit=40)
                pp2.base_zones = pp.base_zones; pp = pp2
                q = pp.post(uu)
            if q['max_dh_slip'] > 1e-7: raise ValueError('thickening')
        except ValueError:
            step *= 0.5
            if abs(step) < 1e-5: raise ValueError(f'friction continuation failed at {mu}')
            continue
        pr, u, mu, ph = pp, uu, new, phys(pp, uu)
    return pr, u
for R in (0.089, 0.135):
    pr, u, tot, m = solve_cold(h0, h1, R, Y, 0.026, tb, tf, E, nu)
    w0 = pr.post(u)['force_per_width_n_m'] * Es / (R * Ys ** 2)
    a, fa = 0.026, w0 - 58
    b = 0.026 * (58 / w0) ** 0.7
    pr_b, u_b = march(pr, u, b)
    fb_ = pr_b.post(u_b)['force_per_width_n_m'] * Es / (R * Ys ** 2) - 58
    for it in range(12):
        c = b - fb_ * (b - a) / (fb_ - fa)
        pr_c, u_c = march(pr_b, u_b, c)
        fc = pr_c.post(u_c)['force_per_width_n_m'] * Es / (R * Ys ** 2) - 58
        a, fa, b, fb_, pr_b, u_b = b, fb_, c, fc, pr_c, u_c
        if abs(fc) < 1e-6: break
    q = pr_b.post(u_b)
    print(f'R {R}: W_bar(0.026) = {w0:.3f}; friction for W_bar 58: {b:.5f} ({pr_b.structure}, slip {q["forward_slip"]:.4f}, secant its {it+1})')
