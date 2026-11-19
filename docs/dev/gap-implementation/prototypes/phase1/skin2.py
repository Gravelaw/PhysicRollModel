import math, time
def skin_cycle(*, k, rho_c, t_rev, arcs, t_coolant, t_deep, depth_factor=6.0, cells=24, steps=360,
               min_arc_steps=8, tol=1e-3, max_revs=400):
    a = k / rho_c
    depth = depth_factor * math.sqrt(a * t_rev)
    first = depth / (cells * 8.0)
    lo, hi = 1.0001, 3.0
    for _ in range(100):
        r = 0.5 * (lo + hi)
        if first * (r ** cells - 1) / (r - 1) > depth: hi = r
        else: lo = r
    dy = [first * r ** i for i in range(cells)]
    cond = [k / (0.5 * (dy[i] + dy[i + 1])) for i in range(cells - 1)] + [k / (0.5 * dy[-1])]
    cap = [rho_c * d for d in dy]
    gs = k / (0.5 * dy[0])
    sched = []                      # (dt, q, h, end_fraction)
    for s, e, q, h in arcs:
        m = max(min_arc_steps, math.ceil(steps * (e - s)))
        for i in range(m):
            sched.append(((e - s) * t_rev / m, q, h))
    # steady linear initial profile
    T = [t_deep] * cells
    prev = None
    n_c = cells
    for rev in range(max_revs):
        hist, flux = [], 0.0
        for dt, q, h in sched:
            geff = gs * h / (h + gs); src = gs * q / (h + gs)
            diag = [cap[i] / dt + (cond[i - 1] if i > 0 else 0.0) + cond[i] for i in range(n_c)]
            rhs = [cap[i] / dt * T[i] for i in range(n_c)]
            rhs[-1] += cond[-1] * t_deep
            diag[0] += geff; rhs[0] += geff * t_coolant + src
            for i in range(1, n_c):
                m_ = -cond[i - 1] / diag[i - 1]
                diag[i] += m_ * cond[i - 1]; rhs[i] -= m_ * rhs[i - 1]
            T[-1] = rhs[-1] / diag[-1]
            for i in range(n_c - 2, -1, -1):
                T[i] = (rhs[i] + cond[i] * T[i + 1]) / diag[i]
            ts = (q + h * t_coolant + gs * T[0]) / (h + gs)
            hist.append(ts)
            flux += (q - h * (ts - t_coolant)) * dt / t_rev
        if prev is not None and max(abs(x - y) for x, y in zip(hist, prev)) < tol:
            break
        prev = hist
    tmean = sum(ts * s[0] for ts, s in zip(hist, sched)) / t_rev
    return hist, sched, rev + 1, tmean, flux, cond[-1] * (T[-1] - t_deep)

k, rho_c = 40.0, 7850 * 470.0
e = math.sqrt(k * rho_c)
R = 0.135; t_rev = 2 * math.pi * R / 10.0
fb = 2e-3 / (2 * math.pi * R)
arcs = [(0.0, fb, 1e7, 0.0), (fb, 0.25, 0.0, 50.0), (0.25, 0.25 + 1 / 6, 0.0, 20450.0), (0.25 + 1 / 6, 1.0, 0.0, 50.0)]
for steps, mb in ((360, 8), (360, 16), (720, 32)):
    t = time.perf_counter()
    hist, sched, revs, tmean, flux, deep = skin_cycle(k=k, rho_c=rho_c, t_rev=t_rev, arcs=arcs, t_coolant=313.15, t_deep=330.0, steps=steps, min_arc_steps=mb)
    print(f'steps {steps} bite steps {mb}: before bite {hist[-1]:.3f}, after bite {hist[mb-1]:.3f}, rise {hist[mb-1]-hist[-1]:.3f} (formula 13.136), min {min(hist):.3f}, mean {tmean:.3f}, mean flux {flux:.1f}, deep flux {deep:.1f}, revs {revs}, n {len(sched)}, {time.perf_counter()-t:.2f}s')
hbar = 50 + (20450 - 50) / 6
# effective mean coefficient: <h (Ts - Tc)> / (mean(Ts) - Tc)
hist, sched, revs, tmean, flux, deep = skin_cycle(k=k, rho_c=rho_c, t_rev=t_rev, arcs=arcs, t_coolant=313.15, t_deep=330.0, steps=720, min_arc_steps=32)
out = sum(h * (ts - 313.15) * dt for ts, (dt, q, h) in zip(hist, sched)) / t_rev
print('mean htc', hbar, 'effective <h(Ts-Tc)>/(mean Ts - Tc)', out / (tmean - 313.15), 'ratio', out / (tmean - 313.15) / hbar)
# unit solutions (linearity)
A = skin_cycle(k=k, rho_c=rho_c, t_rev=t_rev, arcs=arcs, t_coolant=0.0, t_deep=0.0, steps=360, min_arc_steps=16, tol=1e-5)
arcs0 = [(s, e_, 0.0, h) for s, e_, q, h in arcs]
B = skin_cycle(k=k, rho_c=rho_c, t_rev=t_rev, arcs=arcs0, t_coolant=0.0, t_deep=1.0, steps=360, min_arc_steps=16, tol=1e-7)
print('unit: bite-entry rise per unit deep excess', B[0][-1], ' per 1e7 W/m2 bite flux', A[0][-1], ' combined', 313.15 + B[0][-1] * (330 - 313.15) + A[0][-1])
