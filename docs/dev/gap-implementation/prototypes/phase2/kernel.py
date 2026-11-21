import math, json, os
HEAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 's23', 'head')
def chi_numeric(nu, closure, kappa=30.0, E=1.0):
    """E*eps_xx/sigma_xx at the bite plane of a decaying plane-stress field phi = (a + b x) exp(-kappa x) cos(kappa z)."""
    a = 1.0
    if closure == 'shear_free': b = kappa*a
    elif closure == 'uniaxial': b = kappa*a/2
    elif closure == 'no_lateral_velocity': b = kappa*a*(1 + nu)/(3 + nu)
    sxx = -kappa**2*a; szz = kappa**2*a - 2*b*kappa
    # check d(u_z)/dx at x = 0 by finite differences for the third closure
    def uz(x): return ((1 + nu)*kappa*(a + b*x) - 2*b)*math.exp(-kappa*x)
    duz = (uz(1e-7) - uz(0))/1e-7
    return (sxx - nu*szz)/sxx, szz/sxx, kappa*(b - kappa*a)/sxx, duz
def kernel(b, W, E, nu, chi_x, chi_e):
    h = b['exit_thickness_m']
    Q = -b['dforce_dexit_thickness_n_m']/W; Nx = -b['dforce_dexit_tension_m2']/W; Ne = -b['dforce_dentry_tension_m2']/W
    fh, fsx, fse = b['dslip_dexit_thickness_per_m'], b['dslip_dexit_tension_per_pa'], b['dslip_dentry_tension_per_pa']
    den = chi_x/E - fsx - fse*chi_x/chi_e
    Ax = (fh + chi_x/h + fse*(E/h)*(1 - chi_x)/chi_e)/den
    Ae = (chi_x/chi_e)*Ax + (E/h)*(1 - chi_x)/chi_e
    fb = Nx*Ax + Ne*Ae
    return {'Q': Q, 'pointwise_feedback': Nx*E/h, 'kernel_feedback': fb, 'ratio': fb/(Nx*E/h), 'Ax_over_E_h': Ax*h/E, 'Ae_over_E_h': Ae*h/E,
            'Qeff_over_Q_pointwise': 1 + Nx*E/h/Q, 'Qeff_over_Q_kernel': 1 + fb/Q, 'denominator': den}
nu = 0.33
for c in ('no_lateral_velocity', 'uniaxial', 'shear_free'):
    print(c, 'chi, szz/sxx, tau/sxx, duz/dx:', [round(v, 5) for v in chi_numeric(nu, c)], ' closed form chi', {'no_lateral_velocity': (3 - nu)*(1 + nu)/(3 + nu), 'uniaxial': 1.0, 'shear_free': 1 - nu}[c])
for name, W in (('lengthwise-bands-demo', 1.5), ('battery-foil-demo', 1.2)):
    art = json.load(open(os.path.join(HEAD, 'artifacts', 'band_diagnosis', name + '.result.json')))
    b = art['bite']; sh = art['width']['shape']['steady']
    print(name, 'rigid', round(sh['rigid_transfer_bound_i_units'], 1), 'compliance only', round(sh['compliance_only_peak_i_units'], 1), 'linear feedback', round(sh['linear_feedback_peak_i_units'], 2))
    twoCQ = sh['rigid_transfer_bound_i_units']/sh['compliance_only_peak_i_units'] - 1
    for c in ('no_lateral_velocity', 'uniaxial', 'shear_free'):
        chi = chi_numeric(nu, c)[0]
        k = kernel(b, W, 7e10, nu, chi, chi)
        est = sh['rigid_transfer_bound_i_units']/(1 + twoCQ*k['Qeff_over_Q_kernel']) if k['Qeff_over_Q_kernel'] > 0 else None
        est_pt = sh['rigid_transfer_bound_i_units']/(1 + twoCQ*k['Qeff_over_Q_pointwise'])
        print('  ', c, {kk: float('%.4g' % v) for kk, v in k.items()}, 'peak estimate I-units kernel', None if est is None else round(est, 1), 'pointwise (same estimate)', round(est_pt, 1))
