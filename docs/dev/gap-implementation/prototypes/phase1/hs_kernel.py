"""Planner prototype (SPEC18): half-space influence coefficients for piecewise-linear pressure.

u(x) = -(2/(pi*E*)) * Int p(x') ln|x - x'| dx' + const   (surface displacement INTO the solid)
hat element k on nodes x[k-1], x[k], x[k+1]:
    I_jk = Int hat_k(x') ln|x_j - x'| dx'
         = (G(x_j-x_{k-1}) - G(x_j-x_k))/(x_k-x_{k-1}) + (G(x_j-x_{k+1}) - G(x_j-x_k))/(x_{k+1}-x_k)
    G(t) = (t^2/2) ln|t| - (3/4) t^2      (G'' = ln|t|, G(0) = 0)
"""
import math


def G(t):
    if t == 0.0:
        return 0.0
    return 0.5 * t * t * math.log(abs(t)) - 0.75 * t * t


def influence(x):
    """I[j][k] for nodes x[0..N]; columns k = 0..N (k = 0 and k = N are half hats)."""
    n = len(x)
    g = [[G(xj - xk) for xk in x] for xj in x]
    inv = [1.0 / (x[k + 1] - x[k]) for k in range(n - 1)]
    out = []
    for j in range(n):
        gj = g[j]
        d = [(gj[k + 1] - gj[k]) * inv[k] for k in range(n - 1)]   # divided differences
        row = [0.0] * n
        row[0] = d[0] - (x[0] - x[0]) * 0.0   # half hat at node 0 handled below
        for k in range(1, n - 1):
            row[k] = d[k] - d[k - 1]
        # half hats (one-sided ramps): Int_{x0}^{x1} (x1-x')/(x1-x0) ln|xj-x'| dx'
        row[0] = _half(x[j], x[0], x[1])
        row[n - 1] = _half(x[j], x[n - 1], x[n - 2])
        out.append(row)
    return out


def G1(t):
    """First antiderivative of ln|t|: t ln|t| - t."""
    if t == 0.0:
        return 0.0
    return t * math.log(abs(t)) - t


def _half(s, a, b):
    """Int over the ramp that is 1 at a and 0 at b (b may be < a) of ln|s - x'| dx'."""
    # ramp r(x') = (b - x')/(b - a) on [min, max]; Int r ln|s-x'| dx'
    # with t = s - x': Int ln|t| * (b - s + t)/(b - a) dt over t in [s-max, s-min]
    lo, hi = (a, b) if a < b else (b, a)
    t1, t2 = s - hi, s - lo

    def anti(t):   # antiderivative of ln|t|*((b - s) + t)
        # Int ln|t| dt = G1(t); Int t ln|t| dt = t^2/2 ln|t| - t^2/4
        tl = 0.0 if t == 0.0 else 0.5 * t * t * math.log(abs(t)) - 0.25 * t * t
        return (b - s) * G1(t) + tl
    return (anti(t2) - anti(t1)) / (b - a)
