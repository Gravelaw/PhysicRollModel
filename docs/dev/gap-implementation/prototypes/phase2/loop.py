"""Closed spray loop prototype (SPEC19 planner): shapemeter zones -> controller -> valves -> roll_thermal."""
from common import *

class Plant:
    """Stepping wrapper over roll_thermal internals with a cache of operators per level tuple."""
    def __init__(self, th, t_ref=None):
        self.th = th
        self.grid, self.factor = rt._common(th.roll, th.header, th.kw['axial_cell_m'], th.kw['radial_cells'], th.kw['expansion_constraint'])
        self.cache = {}
        self.t_ref = th.w['coolant_temperature_k'] if t_ref is None else t_ref
    def prob(self, levels):
        key = tuple(round(v, 6) for v in levels)
        if key not in self.cache:
            p = rt._Problem(self.th.roll, self.th.header, self.th.segment(list(levels)), self.grid)
            self.cache[key] = (p, rt._Stepper(p))
        return self.cache[key]
    def rows_from(self, result):
        return rt._initial_rows(result, self.grid, self.th.w['coolant_temperature_k'])
    def step(self, rows, levels, dt, first=False):
        p, st = self.prob(levels)
        if first:
            for _ in range(2):
                rows, _s = st.be_step(rows, dt / 2)
        else:
            rows, _s = st.pr_step(rows, dt)
        return rows
    def profiles(self, rows, levels):
        p, _ = self.prob(levels)
        mean, growth, surface = rt._profiles(p, rows, self.t_ref, self.factor, self.th.roll)
        return growth, surface

def strip_idx(z, sp):
    return bw._inside(z, sp['strip_centre_m'], sp['strip_width_m'])

def linear_i_units(zs, dev_s, sp, feedback=True):
    """I-units of a radius deviation on the strip samples: linear transfer, no saturation."""
    h = sp['exit_thickness_m']
    tr = ss.transfer_radius_profile(zs, dev_s, bite_half_length_m=sp['bite_half_length_m'],
        strip_stiffness_per_width_pa=sp['strip_stiffness_per_width_pa'], roll_radius_m=sp['roll_radius_m'],
        n_rolls=sp['n_rolls'], roll_youngs_modulus_pa=sp['roll_youngs_modulus_pa'], roll_poisson_ratio=sp['roll_poisson_ratio'],
        exit_tension_force_sensitivity_per_width_m=sp['exit_tension_force_sensitivity_per_width_m'] if feedback else None,
        exit_thickness_m=h, strip_youngs_modulus_pa=sp['strip_youngs_modulus_pa'], xi=sp['xi'])
    eps = [-sp['xi'] * v / h for v in tr['local_thickness_change_m']]
    m = sum(eps) / len(eps)
    return [(e - m) * 1e5 for e in eps]

def zone_edges(centre, width, count):
    e0 = centre - width * count / 2
    return [e0 + i * width for i in range(count + 1)]

def zone_matrix(zs, edges, a0, a1):
    """S[j][i]: weights of the zone mean; coverage list."""
    dz = zs[1] - zs[0]
    S, cov = [], []
    for lo, hi in zip(edges, edges[1:]):
        row = []
        for x in zs:
            c0, c1 = max(x - dz / 2, a0, lo), min(x + dz / 2, a1, hi)
            row.append(max(0.0, c1 - c0))
        tot = sum(row)
        cov.append(tot / (hi - lo))
        S.append([v / tot if tot > 0 else 0.0 for v in row])
    return S, cov

def legendre_basis(n, order):
    xs = [(-1 + 2 * (j + 0.5) / n) for j in range(n)]
    cols = []
    for o in range(order + 1):
        v = [x ** o for x in xs]
        for c in cols:   # Gram-Schmidt
            d = sum(a * b for a, b in zip(v, c))
            v = [a - d * b for a, b in zip(v, c)]
        nrm = math.sqrt(sum(a * a for a in v))
        cols.append([a / nrm for a in v])
    return cols

def project_out(e, basis):
    out = list(e)
    for c in basis:
        d = sum(a * b for a, b in zip(out, c))
        out = [a - d * b for a, b in zip(out, c)]
    return out

def solve_spd(a, b):
    n = len(a); a = [r[:] for r in a]; b = b[:]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(a[r][i]))
        a[i], a[p] = a[p], a[i]; b[i], b[p] = b[p], b[i]
        for r in range(i + 1, n):
            f = a[r][i] / a[i][i]
            if f:
                for c in range(i, n): a[r][c] -= f * a[i][c]
                b[r] -= f * b[i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (b[i] - sum(a[i][c] * x[c] for c in range(i + 1, n))) / a[i][i]
    return x
