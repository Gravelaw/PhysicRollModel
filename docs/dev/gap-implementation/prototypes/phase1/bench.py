import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
cases = [
 ('BT-V1 20->15 R89 mu.03', 20e-6, 15e-6, 0.089, 0.03, 0.0, 0.0, 118),
 ('BT-V3 140->70 R89 mu.03', 140e-6, 70e-6, 0.089, 0.03, 0.0, 0.0, 50),
 ('BT-V2 73->31.39 R89 mu.026', 73e-6, 73e-6*0.43, 0.089, 0.026, 0.107*Ys, 0.132*Ys, 58),
 ('BT-V2 73->31.39 R135 mu.026', 73e-6, 73e-6*0.43, 0.135, 0.026, 0.107*Ys, 0.132*Ys, 58),
 ('Fig1 60->30', 60e-6, 30e-6, 0.089, 0.03, 0.0, 0.0, None),
 ('Fig1 30->15', 30e-6, 15e-6, 0.089, 0.03, 0.0, 0.0, None),
 ('Fig1 20->10', 20e-6, 10e-6, 0.089, 0.03, 0.0, 0.0, None),
 ('Fig1 13->6.5 (below 8um floor)', 13e-6, 6.5e-6, 0.089, 0.03, 0.0, 0.0, None),
]
for name, h0, h1, R, mu, tb, tf, ref in cases:
    t = time.perf_counter()
    try:
        pr, u, tot, m = solve_cold(h0, h1, R, Y, mu, tb, tf, E, nu, (3, 16, 24, 16, 3), 80e9)
        q = pr.post(u)
        wb = q['force_per_width_n_m'] * Es / (R * Ys ** 2)
        wm = m['force_per_width_n_m'] * Es / (R * Ys ** 2)
        print(f'{name:32s} {pr.structure:12s} mattress {wm:7.2f} ({m["regime"]}) half-space {wb:7.2f} ref {ref} ratio {wb/ref if ref else float("nan"):.3f} slip {q["forward_slip"]:.4f} pmax/K {q["max_pressure_over_K"]:.2f} L {q["contact_length_m"]*1e3:.3f}mm it {tot} t {time.perf_counter()-t:.2f}s work {q["work_residual_relative"]:.1e} minp {q["min_p"]:.2f} maxdh {q["max_dh_slip"]:.1e}')
    except ValueError as e:
        print(f'{name:32s} FAILED: {str(e)[:150]}  t {time.perf_counter()-t:.2f}')
