import math
# single transient, half-space-like layer, step in h: fraction covered at t* = k rho c / h^2
k, rho_c, h = 40.0, 7850 * 470.0, 3400.0
a = k / rho_c
tstar = k * rho_c / h ** 2
for cells, steps in ((24, 360), (24, 1440), (48, 1440)):
    depth = 6 * math.sqrt(a * tstar)
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
    T = [1.0] * cells   # start at 1, sink at 0, deep held at 1
    dt = tstar / steps
    geff = gs * h / (h + gs)
    for n in range(steps):
        diag = [cap[i] / dt + (cond[i - 1] if i > 0 else 0.0) + cond[i] for i in range(cells)]
        rhs = [cap[i] / dt * T[i] for i in range(cells)]
        rhs[-1] += cond[-1] * 1.0
        diag[0] += geff
        for i in range(1, cells):
            m_ = -cond[i - 1] / diag[i - 1]
            diag[i] += m_ * cond[i - 1]; rhs[i] -= m_ * rhs[i - 1]
        T[-1] = rhs[-1] / diag[-1]
        for i in range(cells - 2, -1, -1):
            T[i] = (rhs[i] + cond[i] * T[i + 1]) / diag[i]
    ts = gs * T[0] / (h + gs)
    print(cells, steps, 'fraction covered', 1 - ts, 'exact', 1 - math.e * math.erfc(1))
