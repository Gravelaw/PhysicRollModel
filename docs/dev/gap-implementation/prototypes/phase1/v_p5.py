"""Package 5 worked numbers: published contact-ratio curve, slopes, Barus/Roelands at pressure."""
import math
CURVE = ((0.14, 0.88), (0.36, 0.69), (0.55, 0.53), (0.97, 0.28), (2.37, 0.01))
def area(lam, curve=CURVE):
    if lam <= curve[0][0]: return curve[0][1], 0.0
    if lam >= curve[-1][0]: return curve[-1][1], 0.0
    for (l1, a1), (l2, a2) in zip(curve, curve[1:]):
        if l1 <= lam <= l2:
            s = (a2 - a1) / math.log(l2 / l1)
            return a1 + s * math.log(lam / l1), s / lam
def mu(lam, mc, mv=0.008):
    a, da = area(lam)
    return a, a * mc + (1 - a) * mv, da * (mc - mv)
def placeholder(lam, mb=0.09, mv=0.008, l0=1.0):
    return mv + (mb - mv) * math.exp(-lam / l0), -(mb - mv) / l0 * math.exp(-lam / l0)
for lam in (0.05, 0.1, 0.2, 0.380072, 0.5, 1.0, 2.0, 3.0):
    a, m, s = mu(lam, 0.09)
    a2, m2, s2 = mu(lam, 0.03)
    pm, ps = placeholder(lam)
    print(f'{lam:9.6f} A {a:.4f} mu(0.09) {m:.5f} slope {s:.5f} | mu(0.03) {m2:.5f} slope {s2:.5f} | placeholder {pm:.5f} {ps:.5f}')
# contact friction that gives 0.03 at the demo film ratio
a, _, _ = mu(0.380072, 0.09)
print('mu_c for mu 0.03 at 0.380072:', (0.03 - (1 - a) * 0.008) / a, ' for 0.027:', (0.027 - (1 - a) * 0.008) / a)
# thesis friction with calcium stearate: mu_c 0.0135 -> mu
for mc in (0.0135, 0.036, 0.1):
    print('mu_c', mc, [round(mu(l, mc)[1], 5) for l in (0.14, 0.36, 0.55, 0.97, 2.37)])
# viscosity at pressure, Somentor 31 at 40 C
eta0, alpha, pr = 1.409e-3, 10.40e-9, 196.2e6
z = pr * alpha / (math.log(eta0) + 9.67)
def roel(p): return eta0 * math.exp((math.log(eta0) + 9.67) * ((1 + p / pr) ** z - 1))
def barus(p): return eta0 * math.exp(alpha * p)
for p, meas in ((25e6, 1.905e-3), (50e6, 2.481e-3), (75e6, 3.157e-3), (100e6, 3.985e-3), (625e6, 2.5), (945e6, 15.0), (1510e6, 740.0)):
    print(f'p {p/1e6:6.0f} MPa measured {meas:.4g}  Barus {barus(p):.6g} ({barus(p)/meas:.3f})  Roelands {roel(p):.6g} ({roel(p)/meas:.3f})')
print('z', z)
# z fitted to the 100 MPa table point
lo, hi = 0.3, 1.5
for _ in range(80):
    mid = 0.5 * (lo + hi)
    v = eta0 * math.exp((math.log(eta0) + 9.67) * ((1 + 100e6 / pr) ** mid - 1))
    if v < 3.985e-3: lo = mid
    else: hi = mid
print('z fitted at 100 MPa', lo)
# generalised reduced pressure q(Y) = int_0^Y eta0/eta dp, Y = 230 MPa (60 C thesis values: eta0 1e-3, alpha 1e-8)
def q_of(law, Y, n=20000):
    h = Y / n; s = 0.0
    for i in range(n + 1):
        w = 0.5 if i in (0, n) else 1.0
        s += w * eta0 / law(i * h)
    return s * h
print('q Barus closed', (1 - math.exp(-alpha * 230e6)) / alpha, 'numeric', q_of(barus, 230e6), 'Roelands', q_of(roel, 230e6), 'ratio', q_of(roel, 230e6) / q_of(barus, 230e6))
# Eyring valley example with pressure-proportional Eyring stress (0.007 p), p 4e8
p = 4e8; eta = 2.5e-3 * math.exp(1.2e-8 * p); us = 2.0; hv = 1e-7
tau0 = 0.007 * p
tn = eta * us / hv; te = tau0 * math.asinh(tn / tau0)
print('eta', eta, 'tau0', tau0, 'newtonian', tn, 'eyring', te, 'mu_v', te / p, 'cap 0.045p', 0.045 * p)
# h_w/h_s of the thesis table
for ur, hs, hw in ((30, .237, .323), (10, .097, .108), (5, .055, .054), (3, .036, .032), (1, .014, .011)):
    print(ur, 'h_w/h_s', round(hw / hs, 3))
print('--- valley film curve and Eyring valley friction')
VF = ((0.14, 0.42), (0.36, 0.62), (0.55, 0.79), (0.97, 1.10), (2.37, 2.17))
def valley(lam):
    if lam <= VF[0][0]: return VF[0][1]
    if lam >= VF[-1][0]: return lam * VF[-1][1] / VF[-1][0]
    for (l1, v1), (l2, v2) in zip(VF, VF[1:]):
        if l1 <= lam <= l2:
            return math.exp(math.log(v1) + math.log(v2 / v1) * math.log(lam / l1) / math.log(l2 / l1))
for lam in (0.1, 0.2, 0.380072, 1.0, 3.0):
    print(lam, 'h_v/Rq', valley(lam))
def closure(lam, rq, mc, eta, us, p, tau0=None, cap=None, model='eyring'):
    a, da = area(lam)
    hv = valley(lam) * rq
    tn = eta * us / hv
    t = tau0 * math.asinh(tn / tau0) if model == 'eyring' else tn
    capped = cap is not None and t > cap
    if capped: t = cap
    mv = t / p
    return a, hv, tn, t, mv, a * mc + (1 - a) * mv, capped
# thesis foil case at 3 m/s: Rq 0.1 um, Lambda 0.36, oil 60 C eta0 1.0e-3, alpha 1.0e-8, p 4e8, sliding 0.3 m/s
p = 4e8; eta = 1.0e-3 * math.exp(1.0e-8 * p)
print('eta at p', eta)
print('eyring, tau0 0.007p:', closure(0.36, 1e-7, 0.09, eta, 0.3, p, tau0=0.007 * p))
print('newtonian capped 0.045p:', closure(0.36, 1e-7, 0.09, eta, 0.3, p, cap=0.045 * p, model='newt'))
# a case where the cap acts: thicker oil eta0 2.5e-3 alpha 1.2e-8 p 6e8, sliding 2 m/s, Rq 0.3 um, Lambda 0.2
p = 6e8; eta = 2.5e-3 * math.exp(1.2e-8 * p)
print('eta', eta)
print('eyring:', closure(0.2, 3e-7, 0.09, eta, 2.0, p, tau0=0.007 * p, cap=0.045 * p))
print('newtonian capped:', closure(0.2, 3e-7, 0.09, eta, 2.0, p, cap=0.045 * p, model='newt'))
# viscosity table with the Somentor points
T = (313.15, 333.15, 373.15); V = (1.409e-3, 1.033e-3, 0.632e-3)
def eta_tab(t):
    i = 0 if t <= T[1] else 1
    return math.exp(math.log(V[i]) + (math.log(V[i + 1]) - math.log(V[i])) * (t - T[i]) / (T[i + 1] - T[i]))
print('eta0 50 C', eta_tab(323.15), '80 C', eta_tab(353.15), '120 C (extrapolated)', eta_tab(393.15), '20 C (extrapolated)', eta_tab(293.15))
# Roelands at 60 C from the table with alpha 9.60e-9, 100 MPa (table 2.699e-3)
e60 = 1.033e-3; a60 = 9.60e-9; z60 = pr * a60 / (math.log(e60) + 9.67)
print('z60', z60, 'Roelands 60 C 100 MPa', e60 * math.exp((math.log(e60) + 9.67) * ((1 + 100e6 / pr) ** z60 - 1)), 'Barus', e60 * math.exp(a60 * 100e6), 'table 2.699e-3')
