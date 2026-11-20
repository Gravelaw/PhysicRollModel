"""Check 2: the printed end conditions (pressure Y_s at both ends of the plastic zone, db/dx = 0 at exit),
closed by a pressure ramp of prescribed length outside both ends; rigid strip; BT-V1 (Fig. 9)."""
import sys, math, time
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
from hs3 import P3, from_solution
from v_e2 import with_e
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; nu = 0.3; E = Es * (1 - nu * nu)
R, h0, h1, mu = 0.089, 20e-6, 15e-6, 0.03
scale = Es / (R * Ys ** 2)
pr, u, tot, m = solve_cold(h0, h1, R, Y, mu, 0.0, 0.0, E, nu, strip_modulus=1e13)
pe, ue, it = with_e(pr, u, Ys, Es, 1e13)
qe = pe.post(ue)
print('rigid strip, exit and entry contact zones, zone E: Wbar', round(qe['force_per_width_n_m'] * scale, 3), 'L mm', round(qe['contact_length_m'] * 1e3, 4), 'slip', round(qe['forward_slip'], 4))
prev = {'x': qe['x'], 'p': qe['p']}
bm = qe['bounds_m']
pvec, bnd, g0, hn = pe.unpack(ue)
free = [bm[1], bm[2], bm[3], bm[4], bm[5]]
hn_m = hn * h1
for zone_e in (True, False):
    prev_l = dict(prev); fr = list(free); g = g0; hnm = hn_m
    if not zone_e:
        fr = [free[0], free[1], free[4 - 1], free[4]]   # xi, xa, xb (= xef), xe
    for n, ell in (((1, 16, 24, 8, 16, 1), 40e-6), ((1, 16, 24, 8, 16, 1), 30e-6), ((1, 16, 24, 8, 16, 1), 21e-6),
                   ((1, 16, 24, 8, 16, 1), 15e-6), ((1, 16, 24, 8, 16, 1), 10e-6), ((1, 16, 24, 8, 16, 1), 7e-6),
                   ((1, 16, 24, 8, 16, 1), 5e-6), ((1, 16, 24, 8, 16, 1), 3.5e-6), ((1, 16, 24, 8, 16, 1), 2.5e-6)):
        pp = P3(h0, h1, R, Ys, mu, 0.0, 0.0, Es, n=n, zone_e=zone_e, entry='ramp', exit='ramp', ramp_in=ell, ramp_out=ell, slope='analytic')
        u0 = from_solution(prev_l, True, pp, fr, g, hnm)
        try:
            t = time.perf_counter()
            u1, it, nrm = pp.newton(u0, maxit=60)
        except ValueError as e:
            print(f'  zone_e {zone_e} ramp {ell*1e6:.1f} um FAILED {e}'); break
        q = pp.post(u1)
        b = q['bounds_m']
        print(f'  zone_e {zone_e} ramp {ell*1e6:5.1f} um: Wbar {q["force_per_width_n_m"]*scale:7.2f} L {q["contact_length_m"]*1e3:.3f} mm entry {b[0]*1e3:.3f} exit {b[6]*1e3:.3f} peak {q["pmax_over_k"]:.2f} at {q["p_peak_x_m"]*1e3:.3f} mm slip {q["forward_slip"]:.4f} shear max {q["max_shear_ratio"]:.2f} it {it} minp {q["min_p"]:.2f} dh {tuple(round(v,5) for v in q["max_dh"])}')
        prev_l = {'x': q['x'], 'p': q['p']}
        pv, bd, g, hnn = pp.unpack(u1)
        fr = [v * pp.L for v in bd]; hnm = hnn * h1
