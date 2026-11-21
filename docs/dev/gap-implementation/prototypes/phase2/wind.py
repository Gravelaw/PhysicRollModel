"""Accretion winding model, one radial model per lane (SPEC19 planner prototype)."""
import math, time
def thomas(a, b, c, d):
    n = len(b); cp = [0.0]*n; dp = [0.0]*n
    cp[0] = c[0]/b[0]; dp[0] = d[0]/b[0]
    for i in range(1, n):
        m = b[i] - a[i]*cp[i-1]
        cp[i] = c[i]/m if i < n - 1 else 0.0
        dp[i] = (d[i] - a[i]*dp[i-1])/m
    x = [0.0]*n; x[-1] = dp[-1]
    for i in range(n - 2, -1, -1): x[i] = dp[i] - cp[i]*x[i+1]
    return x
class Lane:
    def __init__(self, r_core, h, n_laps, E_t, nu, er_fun, core_stiffness=None):
        self.rc, self.h, self.nl, self.Et, self.nu, self.er, self.Ec = r_core, h, n_laps, E_t, nu, er_fun, core_stiffness
        self.d = n_laps*h
        self.r = [r_core]            # undeformed node radii (layer tops), node 0 = core surface
        self.sr = [0.0]              # radial stress at nodes (negative = pressure)
        self.st = []                 # hoop stress of layer i (between node i and i+1)
        self.wot = []                # wound-on hoop stress of layer i
        self.U = [0.0]               # cumulative radial displacement of nodes
        self.ep = []                 # plastic hoop strain of layer i
    def outer_radius(self):
        return self.r[-1] + self.U[-1]
    def add_layer(self, tension_pa, plastic=0.0):
        n = len(self.r) - 1          # index of the current top node
        s = self.r[-1] + self.d
        p_top = -tension_pa*self.d/s
        if n == 0:
            ds = [p_top]
            dst = []
            # displacement of the core surface under pressure
            du = [(-ds[0]*self.rc/self.Ec) if self.Ec else 0.0]
            du[0] = ds[0]*self.rc/self.Ec if self.Ec else 0.0
        else:
            N = n + 1; a = [0.0]*N; b = [0.0]*N; c = [0.0]*N; d = [0.0]*N
            dl = self.d
            # core boundary (node 0): r_c*(ds1 - ds0)/dl = ds0*(Et/Ec - 1 + nu); rigid core: Et/Ec = 0
            k = (self.Et/self.Ec if self.Ec else 0.0) - 1 + self.nu
            b[0] = -self.rc/dl - k; c[0] = self.rc/dl; d[0] = 0.0
            for i in range(1, n):
                r = self.r[i]; g2 = self.Et/self.er(-self.sr[i])
                a[i] = r*r/dl**2 - 1.5*r/dl; b[i] = -2*r*r/dl**2 - (g2 - 1); c[i] = r*r/dl**2 + 1.5*r/dl
            a[n] = 0.0; b[n] = 1.0; d[n] = p_top
            ds = thomas(a, b, c, d)
            dst = []
            for i in range(n):       # hoop increment of layer i (mid-layer): ds + r*d(ds)/dr
                rm = 0.5*(self.r[i] + self.r[i+1])
                dst.append(0.5*(ds[i] + ds[i+1]) + rm*(ds[i+1] - ds[i])/dl)
            du = []
            for i in range(N):
                if i == 0: der = (ds[1] - ds[0])/dl
                elif i == n: der = (ds[n] - ds[n-1])/dl
                else: der = (ds[i+1] - ds[i-1])/(2*dl)
                r = self.r[i]
                du.append(r*((ds[i] + r*der)/self.Et - self.nu*ds[i]/self.Et))
        for i in range(len(ds)): self.sr[i] += ds[i]; self.U[i] += du[i]
        for i in range(len(dst)): self.st[i] += dst[i]
        # the new layer: its own radial compression under its mean pressure is taken with the next increments
        self.r.append(s); self.sr.append(0.0); self.st.append(tension_pa); self.wot.append(tension_pa); self.ep.append(plastic)
        self.U.append(self.U[-1])
def closed_form_isotropic(r, rc, R, Tw, nu):
    beta = (1 - nu)/(1 + nu); L = math.log((R*R + beta*rc*rc)/(r*r + beta*rc*rc))
    return -(Tw/2)*(1 + beta*rc*rc/r**2)*L, Tw - (Tw/2)*(1 - beta*rc*rc/r**2)*L
def allocate(lanes, widths, e_nat, mean_tension, E, sy):
    """Relaxation radius s0: sum_j w_j h_j sigma_j = mean_tension * sum_j w_j h_j, sigma_j = clip(E*((s_j - s0)/s0 - e_j), 0, sy)."""
    s = [ln.outer_radius() + ln.d for ln in lanes]
    target = mean_tension*sum(w*ln.h for w, ln in zip(widths, lanes))
    def total(s0):
        return sum(w*ln.h*min(max(E*((sj - s0)/s0 - e), 0.0), sy) for w, ln, sj, e in zip(widths, lanes, s, e_nat))
    hi = max(s); lo = min(s)/(1 + 2*sy/E + max(e_nat) + 1e-6)
    for _ in range(80):
        mid = 0.5*(lo + hi)
        if total(mid) > target: lo = mid
        else: hi = mid
    s0 = 0.5*(lo + hi)
    out = []
    for sj, e in zip(s, e_nat):
        eps = (sj - s0)/s0 - e
        out.append((min(max(E*eps, 0.0), sy), max(0.0, eps - sy/E)))
    return s0, out
if __name__ == '__main__':
    # 1. isotropic, rigid core: closed form
    rc, R, Tw, E, nu, h = 0.15, 0.60, 30e6, 70e9, 0.33, 30e-6
    for n_layers in (50, 100, 200, 400):
        nl = (R - rc)/h/n_layers
        ln = Lane(rc, h, nl, E, nu, lambda p: E)
        t0 = time.perf_counter()
        for _ in range(n_layers): ln.add_layer(Tw)
        dt = time.perf_counter() - t0
        out = []
        for frac in (0.0, 0.25, 0.5, 0.75):
            i = int(round(frac*n_layers)); r = ln.r[i]
            ex_r, ex_t = closed_form_isotropic(r, rc, R, Tw, nu)
            rm = 0.5*(ln.r[i] + ln.r[i+1]); _, ex_tm = closed_form_isotropic(rm, rc, R, Tw, nu)
            out.append((round(r, 4), round(ln.sr[i]/1e6, 4), round(ex_r/1e6, 4), round(ln.st[i]/1e6, 4), round(ex_tm/1e6, 4)))
        print(n_layers, 'layers', round(dt, 3), 's  (r, sr, exact, st, exact) MPa', out)
