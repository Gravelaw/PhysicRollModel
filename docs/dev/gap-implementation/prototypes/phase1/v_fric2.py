"""Planner checks of the research note's friction, viscosity and heat items (standard library)."""
import math
# --- Christensen height distribution [E5 (4.18), (4.20)]
def chr_A(H):
    if H >= 1: return 0.0
    if H <= -1: return 1.0
    return (16 - 35 * H + 35 * H ** 3 - 21 * H ** 5 + 5 * H ** 7) / 32
def chr_ht_over_rq(H):
    if H >= 1: return 3 * H
    if H <= -1: return 0.0
    return 3 / 256 * (35 + 128 * H + 140 * H ** 2 - 70 * H ** 4 + 28 * H ** 6 - 5 * H ** 8)
print('Christensen A(0), A(-1), A(1):', chr_A(0), chr_A(-1), chr_A(1), ' h_t/Rq at H=1, 0, -1:', chr_ht_over_rq(1), chr_ht_over_rq(0), chr_ht_over_rq(-1))
def H_of_A(a):
    lo, hi = -1.0, 1.0
    for _ in range(80):
        m = 0.5 * (lo + hi)
        if chr_A(m) > a: lo = m
        else: hi = m
    return 0.5 * (lo + hi)
print('static truncation against thesis Table 4.2 (d0 = 0.1 um): A, table h_t um, static h_t um')
for a, ht in ((0.28, 0.088), (0.53, 0.047), (0.69, 0.028), (0.88, 0.010)):
    H = H_of_A(a)
    print(f'   A {a}: table {ht}, static {0.1 * chr_ht_over_rq(H):.4f}, ratio {0.1 * chr_ht_over_rq(H) / ht:.3f}')
# --- crushing laws
def ws_Ep(A, Ha):
    f1 = 0.515 + 0.345 * A - 0.860 * A * A
    f2 = 1 / (2.571 - A - A * math.log(1 - A))
    return (2 / Ha - f2) / f1
def ws_Ha0(A): return 2 * (2.571 - A - A * math.log(1 - A))
print('Wilson-Sheu H_a(E_p=0): A=1e-9', ws_Ha0(1e-9), ' A=0.5', ws_Ha0(0.5), ' E_p(A=0.5, H_a=2)', ws_Ep(0.5, 2.0))
def thesis_W(A, pbar_2k): return min(2.5, max(0.05, 3.81 * pbar_2k ** 2 - 4.38 * A))
def marsault_W(A, Ha): return A * A * Ha * Ha * (3.81 - 4.38 * A) / 4
def korz_Ep(A, Ha):
    D = Ha / 2
    c1 = 5.1206 * D - 4.5258 * D ** 2 + 3.5599 * D ** 3
    c2 = -9.5761 * D + 11.3854 * D ** 2 - 8.6069 * D ** 3
    c3 = 8.3193 * D - 11.7954 * D ** 2 + 7.6475 * D ** 3
    return 1 / (A * (1 - A) * (c1 + c2 * A + c3 * A * A))
for A, pb in ((0.5, 1.0), (0.5, 0.6), (0.5, 0.5), (0.3, 0.6)):
    Ha = 2 * pb / A
    print(f'A {A} pbar/2k {pb} (H_a {Ha:.3f}): thesis W {thesis_W(A, pb):.4f}  Marsault W {marsault_W(A, Ha):.4f}  Wilson-Sheu W=1/E_p {1/ws_Ep(A, Ha) if ws_Ep(A, Ha) > 0 else float("nan"):.4f}  Korzekwa W=1/E_p {1/korz_Ep(A, Ha):.4f}')
# --- percolation threshold and a flow factor
g = 9.0
print('h_tc/Rq (gamma 9):', 3 * (1 - 1 / (0.47476 / g + 1) ** 0.25007), ' phi_x(gamma=9, h/Rq=3):', 1 + (-0.10667 + 0.10750 * g) * 3 ** -1.5, ' phi_x(gamma=1, h/Rq=3):', 1 - (0.89679) * math.exp(-(0.43006 - 0.10828 + 0.23821) * 3))
# --- film formula against Table 4.2 (thin foil column)
eta0, alpha, sy = 1.0e-3, 1.0e-8, 230e6
print('h_w (4.20) with slope 0.0058 and u_bar = 0.94 u_r against the table:')
for ur, hw in ((30, 0.323), (10, 0.108), (5, 0.054), (3, 0.032), (1, 0.011)):
    h = 6 * alpha * eta0 * 0.94 * ur / (0.0058 * (1 - math.exp(-alpha * sy)))
    print(f'   u_r {ur}: {h*1e6:.4f} um, table {hw}, ratio {h*1e6/hw:.3f}')
# published curve A(Lambda_s) and log-linear interpolation
pts = [(0.14, 0.88), (0.36, 0.69), (0.55, 0.53), (0.97, 0.28), (2.37, 0.01)]
def area(lam):
    if lam <= pts[0][0]: return pts[0][1]
    if lam >= pts[-1][0]: return pts[-1][1]
    for (l1, a1), (l2, a2) in zip(pts, pts[1:]):
        if lam <= l2:
            return a1 + (a2 - a1) * math.log(lam / l1) / math.log(l2 / l1)
for lam in (0.1, 0.2, 0.380072, 0.5, 1.0, 2.0, 3.0):
    a = area(lam); print(f'Lambda {lam}: A {a:.4f}  mu (mu_c 0.09, mu_v 0.008) {a*0.09+(1-a)*0.008:.5f}')
# two-point defaults against the published points
for l, a in pts:
    a2 = min(1.0, max(0.0, math.log(1.0 / l) / math.log(100.0)))
    print(f'   published A({l}) = {a}; two-point (0.01, 1.0) gives {a2:.3f}')
# --- Roelands [E5 (L.3), (4.194)] on Somentor 31 at 40 C [E6 Table 2.1]
pr = 196.2e6
def roelands(eta0, p, T, T0, z, S0):
    return eta0 * math.exp((math.log(eta0) + 9.67) * ((1 + p / pr) ** z * ((T0 + 135) / (T + 135)) ** S0 - 1))
e40, a40 = 1.409e-3, 10.40e-9
z = pr * a40 / (math.log(e40) + 9.67)
print('z', z, ' Roelands 40 C, 100 MPa:', roelands(e40, 100e6, 40, 40, z, 0), '(table 3.985e-3; Barus', e40 * math.exp(a40 * 100e6), ')  625 MPa:', roelands(e40, 625e6, 40, 40, z, 0), ' 945 MPa:', roelands(e40, 945e6, 40, 40, z, 0))
# S0 from the 40 and 100 C points: (ln e100 + 9.67)/(ln e40 + 9.67) = (175/235)^S0
S0 = math.log((math.log(0.632e-3) + 9.67) / (math.log(e40) + 9.67)) / math.log(175 / 235)
print('S0', S0, ' check 60 C:', roelands(e40, 0, 60, 40, z, S0), '(table 1.033e-3)')
print('beta 40-60:', math.log(1.409 / 1.033) / 20, ' 60-100:', math.log(1.033 / 0.632) / 40)
print('Eyring stress / pressure:', 4.5 / 625, 6.0 / 945, 11.7 / 1510)
# --- heat partition with the sourced oil conductivities (planner's scheme, s23/heat.py)
import sys; sys.argv = ['x']
from heat import partition
e_r = math.sqrt(43 * 3.6e6); Cs = 2.43e6 * 12e-6; tc = 2e-4
for k_oil in (0.125, 0.13, 0.25):
    for film in (70e-9, 200e-9):
        r = partition(heat_plastic_w_m2=1.0, heat_friction_w_m2=0.0, contact_time_s=tc, strip_capacity_j_m2k=Cs, roll_effusivity=e_r,
                      interface_conductance_w_m2k=k_oil / film, strip_entry_k=0.0, roll_entry_k=0.0)
        print(f'k_oil {k_oil} film {film*1e9:.0f} nm: h_c {k_oil/film:.4e} strip share {r["strip_share"]:.4f}')
