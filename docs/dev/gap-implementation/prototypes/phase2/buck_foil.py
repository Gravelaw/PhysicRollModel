from buck import *
from buck_ss import gauss_profile, width_at
import json, os
# (a) SS-V2 as a local window: 150 mm, Gaussian compression (not mean-free), SS and clamped
E, nu, t, b = 210e9, 0.3, 0.5e-3, 0.150
for fw in (0.075, 0.10, 0.15, 0.30):
    n = 60; z = [b*i/n for i in range(n + 1)]
    s = [-E*1e-5*math.exp(-4*math.log(2)*((x - b/2)/fw)**2) for x in z]
    out = []
    for bc in ('simply_supported', 'clamped'):
        r = critical(Strip(z, s, t, E, nu, 0.0, (bc, bc)), math.pi/(4*b), math.pi/(b/8))
        out.append((bc, round(r['lambda'], 3), round(r['half_wavelength_m']*1e3, 1)))
    print('window 150 mm, Gaussian FWHM', fw*1e3, out, '(published 5.3 / 8.92 I-units, measured half wave 60 mm)')
# (b) battery-foil steady profile
HEAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 's23', 'head')
for name, sT, t, E, nu in (('battery-foil-demo', 40e6, 30e-6, 70e9, 0.33), ('lengthwise-bands-demo', 30e6, 210e-6, 70e9, 0.33)):
    art = json.load(open(os.path.join(HEAD, 'artifacts', 'band_diagnosis', name + '.result.json')))
    sh = art['width']['shape']['steady']
    z = sh['z_m']; iu = sh['i_units_linear_feedback']
    # coarsen to 10 mm
    step = 2; zc = z[::step]; ic = iu[::step]
    sres = [-E*1e-5*v for v in ic]
    W = zc[-1] - zc[0]
    print(name, 'samples', len(zc), 'peak I', max(ic), 'min', min(ic))
    for label, tension, klo in (('in mill', sT, math.pi/W), ('released, half-wave <= strip width', 0.0, math.pi/W), ('released, half-wave <= 4 x width', 0.0, math.pi/(4*W))):
        st = Strip(zc, sres, t, E, nu, tension, ('free', 'free'))
        t0 = time.perf_counter(); r = critical(st, klo, math.pi/(4*(zc[1] - zc[0])), coarse=14, refine=10); dt = time.perf_counter() - t0
        pb = post_buckling(st, r, 1.0)
        f = r['f']; ip = max(range(len(f)), key=lambda i: abs(f[i]))
        print('  ', label, ': lambda_c', round(r['lambda'], 4), 'utilisation', round(1/r['lambda'], 3), 'half wave mm', round(r['half_wavelength_m']*1e3, 1),
              'mode peak at', round(zc[ip], 3), 'width10', round(width_at(zc, f, 0.1), 3), 'amplitude mm', round(pb['amplitude_m']*1e3, 4), 'time', round(dt, 2))
        if pb['amplitude_m'] > 0:
            sat = pb['saturated_stress_pa']; i0 = min(range(len(sres)), key=lambda i: sres[i])
            print('      most compressed sample: linear total stress MPa', round((tension + sres[i0])/1e6, 3), 'saturated', round(sat[i0]/1e6, 3), ' -> reading I-units', round(-(sat[i0] - tension)/E*1e5, 2), 'vs', round(ic[i0], 2))
