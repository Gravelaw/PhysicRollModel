import sys, math, time
sys.path.insert(0, '.')
from run_v1 import from_mattress
from hs_bite import Problem

def solve_cold(h0, h1, R, Y, mu, tb, tf, E, nu, zones=(3, 16, 24, 16, 3), strip_modulus=80e9, verbose=False, cap=1.0):
    pr, u, m = from_mattress(h0, h1, R, Y, mu, tb, tf, E, nu, zones, strip_modulus=strip_modulus)
    pr.cap = cap / 2.0
    u, it, nrm = pr.newton(u)
    lam, step, total = 0.0, 0.25, it
    while lam < 1.0:
        new = min(1.0, lam + step)
        pr.lam = new
        try:
            u2, it, nrm = pr.newton(u, maxit=20)
            q = pr.post(u2)
            if q['min_p'] < 0:
                raise ValueError('negative pressure')
            u, lam = u2, new
            total += it
            step = min(step * 1.5, 0.5)
            if verbose:
                print(f'  lam {lam:.3f} it {it} W {q["force_per_width_n_m"]:.4e}')
        except ValueError as e:
            pr.lam = lam
            step *= 0.5
            if step < 1e-3:
                raise ValueError(f'homotopy failed at lam={lam}: {e}')
    return pr, u, total, m

if __name__ == '__main__':
    sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
    Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
    R, h0, h1, mu = 0.089, 20e-6, 15e-6, 0.03
    for sm in (40e9, 80e9, 160e9, 400e9, 1600e9, 1e13):
        for zones in ((3, 16, 24, 16, 3), (6, 32, 48, 32, 6)):
            t = time.perf_counter()
            try:
                pr, u, tot, m = solve_cold(h0, h1, R, Y, mu, 0.0, 0.0, E, nu, zones, sm)
                q = pr.post(u)
                print(f'Es* {sm:.1e} zones {zones} Wbar {q["force_per_width_n_m"]*Es/(R*Ys**2):8.3f} slip {q["forward_slip"]:.4f} pmax/K {q["max_pressure_over_K"]:.3f} L {q["contact_length_m"]*1e3:.3f} mm shear {q["neutral_shear_ratio_max"]:.3f} it {tot} t {time.perf_counter()-t:.2f}s zonesL {[round((b-a)*1e6,1) for a,b in zip(q["boundaries_m"],q["boundaries_m"][1:])]}')
            except ValueError as e:
                print(f'Es* {sm:.1e} zones {zones} FAILED {e} t {time.perf_counter()-t:.2f}')
