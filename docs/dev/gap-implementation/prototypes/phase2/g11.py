import math
def gen(h, a, W, sx, E=7e10, nu=0.33, R=None, label=''):
    s_tr = (math.pi*h/a)*math.sqrt(E*sx/(3*(1 - nu*nu)))
    tau_tr = math.sqrt(s_tr*(sx + s_tr)); th_tr = 6*a*a*tau_tr/(E*W*W)
    out = {'trough_threshold_pa': round(s_tr), 'critical_shear_pa': round(tau_tr), 'critical_misalignment_rad': th_tr, 'mm_per_m': round(th_tr*1e3, 5), 'Ka': round((a/W)*math.sqrt(12*sx/E), 4)}
    if R:
        s_w = E*h/(R*math.sqrt(3*(1 - nu*nu))); tau_w = math.sqrt(s_w*(sx + s_w)); th_w = 6*a*a*tau_w/(E*W*W)
        out.update({'wrinkle_threshold_pa': round(s_w), 'wrinkle_misalignment_mm_per_m': round(th_w*1e3, 4), 'x15_mm_per_m': round(15*th_w*1e3, 3)})
    print(label, out)
    return out
gen(30e-6, 3.0, 1.2, 40e6, R=0.125, label='battery-foil exit span')
gen(50e-6, 3.0, 1.2, 35e6, R=0.125, label='battery-foil entry span')
gen(210e-6, 4.0, 1.5, 30e6, R=0.15, label='lengthwise exit span')
# forward: misalignment 0.1 mm/m on the foil exit span
th = 1e-4; a, W, E, sx = 3.0, 1.2, 7e10, 40e6
tau = E*W*W*th/(6*a*a); s2 = sx/2 - math.sqrt(sx*sx/4 + tau*tau)
print('0.1 mm/m: shear', tau, 'Pa; second principal stress', s2, 'Pa')
# taper: radius difference 10 um over 1.2 m on a 0.125 m roller: m = dR/(R*W)
m = 10e-6/(0.125*1.2); print('taper 10 um over the width: equivalent misalignment m*a =', m*a, 'rad =', m*a*1e3, 'mm/m')
# roller deflection: tube D 0.25, wall 0.010, L 1.5 m, tension 40 MPa x 30 um, wrap 90 deg
T = 40e6*30e-6; q = 2*T*math.sin(math.radians(45)); D, tw, L = 0.25, 0.010, 1.5
I = math.pi/64*(D**4 - (D - 2*tw)**4); kap = q*L*L/(8*210e9*I); slope_edge = q*L**3/(24*210e9*I)
print('roller: load', q, 'N/m, I', I, 'curvature', kap, '1/m, end slope', slope_edge, 'rad; gathering strain bounds', kap*a/2, kap*a, '-> stress', 7e10*kap*a/2, 7e10*kap*a)
# coil cooling
rho_c = 2.43e6; kz = 200.0; W = 1.2; ri, ro = 0.15, 0.6; hconv = 8.0
for g, kg, lab in ((0.5e-6, 0.13, 'oil gap 0.5 um'), (2e-6, 0.026, 'air gap 2 um')):
    h = 30e-6; kr = (h + g)/(h/kz + g/kg)
    print(lab, 'k_r', round(kr, 2), 'W/mK; radial diffusion time (ro-ri)^2/a', round((ro - ri)**2*rho_c/kr/3600, 1), 'h; axial (W/2)^2/a', round((W/2)**2*rho_c/kz/3600, 2), 'h; lumped time constant V*rho*c/(h*A)',
          round(rho_c*math.pi*(ro*ro - ri*ri)*W/(hconv*(2*math.pi*(ro*ro - ri*ri) + 2*math.pi*ro*W))/3600, 1), 'h; Biot axial', round(hconv*(W/2)/kz, 4), 'radial', round(hconv*(ro - ri)/kr, 3))
