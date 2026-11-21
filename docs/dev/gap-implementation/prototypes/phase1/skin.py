"""Planner prototype (SPEC18): periodic 1-D skin layer of a rotating roll, one axial station.
rho c dT/dt = k d2T/dy2, y = depth below the surface (curvature neglected, depth << R).
Surface: -k dT/dy = q_b(theta) - h(theta) (T_s - T_c).  Depth D: T = T_deep (from the bulk model).
March in time around the revolution until the surface history repeats."""
import math, time

def skin_cycle(*, k, rho_c, t_rev, arcs, t_coolant, t_deep, depth_factor=6.0, cells=24, steps=360,
               tol=1e-4, max_revs=200, theta=1.0):
    """arcs: list of (start_fraction, end_fraction, flux_w_m2, htc_w_m2k) covering [0, 1)."""
    a = k / rho_c
    depth = depth_factor * math.sqrt(a * t_rev)
    # geometric cells, first cell = depth/(cells*8)
    first = depth / (cells * 8.0)
    lo, hi = 1.0001, 3.0
    for _ in range(100):
        r = 0.5 * (lo + hi)
        if first * (r ** cells - 1) / (r - 1) > depth: hi = r
        else: lo = r
    dy = [first * r ** i for i in range(cells)]
    yc = []
    y = 0.0
    for d in dy:
        yc.append(y + d / 2); y += d
    cond = [k / (0.5 * (dy[i] + dy[i + 1])) for i in range(cells - 1)] + [k / (0.5 * dy[-1])]  # last: to T_deep
    cap = [rho_c * d for d in dy]
    gs = k / (0.5 * dy[0])
    dt = t_rev / steps
    def bc(frac):
        for s, e, q, h in arcs:
            if s <= frac < e:
                return q, h
        return 0.0, 0.0
    T = [t_deep] * cells
    prev = None
    for rev in range(max_revs):
        hist, flux_mean = [], 0.0
        for n in range(steps):
            q, h = bc((n + 0.5) / steps)
            # surface node elimination: q + h (Tc - Ts) = gs (Ts - T0) -> Ts = (q + h Tc + gs T0)/(h + gs)
            # flux into cell 0 = gs (Ts - T0) = geff (Teq - T0), geff = gs h/(h+gs) for h>0 plus source
            geff = gs * h / (h + gs)
            src = gs * q / (h + gs)          # W/m2 into cell 0 from the prescribed flux
            # backward Euler tridiagonal
            n_c = cells
            lower = [0.0] * n_c; diag = [0.0] * n_c; upper = [0.0] * n_c; rhs = [0.0] * n_c
            for i in range(n_c):
                diag[i] = cap[i] / dt
                rhs[i] = cap[i] / dt * T[i]
                if i > 0:
                    diag[i] += cond[i - 1]; lower[i] = -cond[i - 1]
                if i < n_c - 1:
                    diag[i] += cond[i]; upper[i] = -cond[i]
            diag[-1] += cond[-1]; rhs[-1] += cond[-1] * t_deep
            diag[0] += geff; rhs[0] += geff * t_coolant + src
            for i in range(1, n_c):
                m = lower[i] / diag[i - 1]
                diag[i] -= m * upper[i - 1]; rhs[i] -= m * rhs[i - 1]
            T[-1] = rhs[-1] / diag[-1]
            for i in range(n_c - 2, -1, -1):
                T[i] = (rhs[i] - upper[i] * T[i + 1]) / diag[i]
            ts = (q + h * t_coolant + gs * T[0]) / (h + gs)
            hist.append(ts)
            flux_mean += (q - h * (ts - t_coolant)) / steps
        if prev is not None and max(abs(x - y) for x, y in zip(hist, prev)) < tol:
            break
        prev = hist
    return {'surface_k': hist, 'revolutions': rev + 1, 'mean_surface_k': sum(hist) / steps,
            'mean_flux_into_roll_w_m2': flux_mean, 'depth_m': depth,
            'deep_flux_w_m2': cond[-1] * (T[-1] - t_deep)}

if __name__ == '__main__':
    k, rho_c = 40.0, 7850 * 470.0
    e = math.sqrt(k * rho_c)
    t_rev = 2 * math.pi * 0.135 / 10.0
    # 1. sinusoidal flux check: emulate with many arcs
    N = 360
    arcs = [(i / N, (i + 1) / N, 1e5 * math.cos(2 * math.pi * (i + 0.5) / N), 0.0) for i in range(N)]
    for steps in (360, 720):
        t = time.perf_counter()
        r = skin_cycle(k=k, rho_c=rho_c, t_rev=t_rev, arcs=arcs, t_coolant=300.0, t_deep=300.0, steps=steps)
        amp = 0.5 * (max(r['surface_k']) - min(r['surface_k']))
        imax = max(range(steps), key=lambda i: r['surface_k'][i])
        print(f'sinusoid steps {steps}: amplitude {amp:.4f} K (exact {1e5/(e*math.sqrt(2*math.pi/t_rev)):.4f}), lag {(imax+1)/steps*360:.1f} deg (exact 45), revs {r["revolutions"]}, time {time.perf_counter()-t:.2f}s')
    # 2. roll cycle: bite 2 mm arc with flux 1e7 W/m2, spray arc 60 deg at 20450 W/m2K, background 50
    R = 0.135
    fb = 2e-3 / (2 * math.pi * R)
    arcs = [(0.0, fb, 1e7, 0.0), (fb, 0.25, 0.0, 50.0), (0.25, 0.25 + 1 / 6, 0.0, 20450.0), (0.25 + 1 / 6, 1.0, 0.0, 50.0)]
    for steps in (720, 1440, 2880):
        t = time.perf_counter()
        r = skin_cycle(k=k, rho_c=rho_c, t_rev=t_rev, arcs=arcs, t_coolant=313.15, t_deep=330.0, steps=steps, tol=1e-3)
        s = r['surface_k']
        nb = max(1, round(fb * steps))
        print(f'cycle steps {steps}: T before bite {s[-1]:.3f} K, after bite {s[nb-1]:.3f} (rise {s[nb-1]-s[-1]:.3f}; constant-flux formula {2*1e7*math.sqrt(2e-3/10)/(math.sqrt(math.pi)*e):.3f}), min {min(s):.3f}, mean {r["mean_surface_k"]:.3f}, mean flux in {r["mean_flux_into_roll_w_m2"]:.1f}, deep flux {r["deep_flux_w_m2"]:.1f}, revs {r["revolutions"]}, time {time.perf_counter()-t:.2f}s')
    hbar = 50 + (20450 - 50) / 6
    qbar = 1e7 * fb
    print('mean htc', hbar, 'mean bite flux', qbar, 'mean-model steady surface (no conduction inward): Tc + q/h =', 313.15 + qbar / hbar)
