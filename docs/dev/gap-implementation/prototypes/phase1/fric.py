import sys, math
sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from physicroll import bite_tribology as bt
# BT-V4 conditions [BT-S3 EX]: 50 -> 25 um, yield 150 MPa, tensions 20/20 MPa, R 135 mm, oil 2.5e-3 Pa s, 1.2e-8 /Pa,
# combined roughness 0.3 um; published Lambda_s 0.22 (5 m/s) to 1.76 (40 m/s)
lub = bt.Lubricant(2.5e-3, 313.15, 0.015, 1.2e-8)
for u_roll in (5.0, 40.0):
    for label, us in (('strip entry speed = roll speed/2 (no slip at exit)', u_roll * 0.5), ('entry speed = roll speed (upper bound)', u_roll)):
        r = bt.inlet_film_thickness(lub, roll_surface_speed_m_s=u_roll, strip_entry_speed_m_s=us, entry_thickness_m=50e-6,
                                    exit_thickness_m=25e-6, contact_radius_m=0.135, plane_strain_yield_pa=150e6,
                                    back_tension_pa=20e6, inlet_temperature_k=313.15)
        print(f'u_roll {u_roll:5.1f} {label}: h_s {r["film_thickness_m"]*1e9:7.1f} nm (Y-only exponent {r["film_thickness_yield_only_exponent_m"]*1e9:7.1f}) Lambda {r["film_thickness_m"]/0.3e-6:.3f} / {r["film_thickness_yield_only_exponent_m"]/0.3e-6:.3f}')

def area_ratio(lam, lam_full=0.01, lam_zero=1.0):
    if lam <= lam_full: return 1.0
    if lam >= lam_zero: return 0.0
    return math.log(lam_zero / lam) / math.log(lam_zero / lam_full)
def mu_ls(lam, mu_c=0.09, mu_v=0.008):
    a = area_ratio(lam)
    return a * mu_c + (1 - a) * mu_v, a
for lam in (0.005, 0.01, 0.0316228, 0.1, 0.2, 0.380072, 0.5, 1.0, 3.0):
    m, a = mu_ls(lam)
    print(f'Lambda {lam:8.4f}  A {a:.4f}  mu two-point {m:.5f}   placeholder {0.008 + 0.082*math.exp(-lam):.5f}  dmu/dLambda two-point {-(0.09-0.008)/(lam*math.log(100)) if 0.01 < lam < 1 else 0.0:.5f} placeholder {-0.082*math.exp(-lam):.5f}')
# Eyring valley shear example
tau0, eta, us, hv = 2e6, 2.5e-3 * math.exp(1.2e-8 * 4e8), 2.0, 1e-7
print('eta at 400 MPa', eta, 'newtonian tau', eta * us / hv, 'eyring tau', tau0 * math.asinh(eta * us / (tau0 * hv)), 'mu_v at p 4e8', tau0 * math.asinh(eta * us / (tau0 * hv)) / 4e8)
# viscosity table interpolation (Petroyag points 3.0/1.4/0.7 cSt at 20/70/130 C), density 800 [M]
pts = [(293.15, 3.0e-6 * 800), (343.15, 1.4e-6 * 800), (403.15, 0.7e-6 * 800)]
def eta_tab(T):
    for (t1, e1), (t2, e2) in zip(pts, pts[1:]):
        if T <= t2 or (t2 == pts[-1][0]):
            return math.exp(math.log(e1) + (math.log(e2) - math.log(e1)) * (T - t1) / (t2 - t1))
print('eta(40 C) from the table', eta_tab(313.15), 'beta segments', math.log(3.0/1.4)/50, math.log(1.4/0.7)/60)
