from common import *
from physicroll import foil_bite, bite_tribology as bt, chatter
import math
for name in ('battery_foil', 'lengthwise_bands'):
    case, art = load(name)
    st = art['width']['thermal_steady']; z = st['z_m']
    dT = [a - b for a, b in zip(st['surface_temperature_k'], st['healthy_surface_temperature_k'])]
    i = max(range(len(z)), key=lambda k: dT[k])
    dev = st['local_deviation_m']
    print(name, 'surface temperature excess at the stripe', round(dT[i], 3), 'K at', z[i], ' radius stripe', round(max(dev)*1e6, 3), 'um; surface minus coolant', round(st['surface_temperature_k'][i] - 318.15, 2), 'healthy', round(st['healthy_surface_temperature_k'][i] - 318.15, 2))
    p = case['pass']; W = p['width_m']
    sh = art['width']['shape']['steady']
    fr = art['process']['friction']['operating']
    print('  film ratio', fr.get('film_ratio'), 'film m', fr.get('film_thickness_m'), 'mu used', p['friction_coefficient'], 'computed mu', fr.get('computed_friction_coefficient'))
    # force sensitivities by central differences of the operating bite model
    def force(Y=None, mu=None):
        Yv = p['mean_flow_stress_pa'] if Y is None else Y; muv = p['friction_coefficient'] if mu is None else mu
        if name == 'battery_foil':
            r = foil_bite.solve_mattress_bite(p['entry_thickness_m'], p['exit_thickness_m'], W, p['work_roll_radius_m'], Yv, muv, p['entry_tension_pa'], p['exit_tension_pa'],
                                              roll_youngs_modulus_pa=case['stand']['roll_youngs_modulus_pa'], roll_poisson_ratio=case['stand']['roll_poisson_ratio'])
            return r['force_per_width_n_m']
        bp_ = chatter.BitePass(p['entry_thickness_m'], p['exit_thickness_m'], W, p['work_roll_radius_m'], Yv, muv, p['entry_tension_pa'], p['exit_tension_pa'])
        return chatter.derive_bite_response(bp_, roll_youngs_modulus_pa=case['stand']['roll_youngs_modulus_pa'], roll_poisson_ratio=case['stand']['roll_poisson_ratio'], cells=256, max_radius_ratio=1.5).separating_force_n/W
    try:
        F = force(); Y = p['mean_flow_stress_pa']; mu = p['friction_coefficient']
        pY = (force(Y=Y*1.005) - force(Y=Y*0.995))/(0.01*Y); pmu = (force(mu=mu*1.02) - force(mu=mu*0.98))/(0.04*mu)
    except Exception as exc:
        print('  bite failed', exc); continue
    print('  F/w', round(F), 'p_Y', pY, 'load exponent in Y', round(pY*Y/F, 3), 'p_mu', pmu, 'load exponent in mu', round(pmu*mu/F, 3))
    # transfer gain at the stripe wavelength, from the artifact's levels
    rigid, comp, fb = sh['rigid_transfer_bound_i_units'], sh['compliance_only_peak_i_units'], sh['linear_feedback_peak_i_units']
    iu = art['width']['inputs_used']; Q = iu['strip_stiffness_per_width_pa']; h = p['exit_thickness_m']; E = 7e10
    twoCQ = rigid/comp - 1; twoC = twoCQ/Q; Qeff = Q + iu['exit_tension_force_sensitivity_per_width_m']*E/h
    G_fb = twoC/(1 + twoC*Qeff); G_co = twoC/(1 + twoCQ)
    beta = case['tribology']['lubricant']['temperature_viscosity_coefficient_per_k']
    lam = fr.get('film_ratio') or 0.38
    # placeholder closure slope
    dmu_dlam = bt.friction_coefficient(lam)['dmu_dlambda'] if hasattr(bt, 'friction_coefficient') else None
    print('  2C', twoC, 'G with feedback', G_fb, 'G compliance only', G_co, 'dmu/dLambda', dmu_dlam)
    cT = 0.0015
    for w in (0.5, 1.0):
        dTin = w*dT[i]
        dmu = dmu_dlam*lam*(-beta)*dTin
        d_film = -G_fb*pmu*dmu/h*1e5          # I-units, positive = loose
        dY = -cT*Y*dT[i]*w
        d_flow = -G_fb*pY*dY/h*1e5
        print('   inlet/bite temperature weight', w, ': dmu', round(dmu, 6), '(', round(100*dmu/mu, 2), '% ) film term', round(d_film, 2), 'I-units; flow-stress term (c_T 0.0015, same weight)', round(d_flow, 2),
              'I-units; roll growth', round(fb, 2), '; strip thermal 2.36*dT*w', round(2.36*dT[i]*w, 2), '; compliance-only film term', round(-G_co*pmu*dmu/h*1e5, 1))
