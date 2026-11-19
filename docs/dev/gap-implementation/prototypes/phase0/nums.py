import sys, json, math
sys.path.insert(0, '/home/user/PhysicRollModel'); sys.dont_write_bytecode = True
from physicroll import strip_shape as ss, band_width as bw, roll_thermal as rt
A = '/home/user/PhysicRollModel/artifacts/band_diagnosis/'
r = json.load(open(A + 'battery-foil-demo.result.json'))
inp = r['inputs']; p = inp['pass']; st = r['width']['shape']['steady']; ts = r['width']['thermal_steady']
z = st['z_m']; mech = st['i_units_with_feedback']
E = inp['material']['youngs_modulus_pa']; sy = inp['material']['yield_stress_pa']; h = p['exit_thickness_m']; sT = p['exit_tension_pa']
print('--- A1 strip temperature term (battery foil demo)')
alpha = 23.6e-6
def interp(xs, ys, x):
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i]); return ys[i] + t * (ys[i + 1] - ys[i])
# synthetic scan: 25 points at 50 mm pitch from 0.15 to 1.35 m, 353.15 K base, +3 K Gaussian (FWHM 0.10 m) at 0.6225 m
xs = [0.15 + 0.05 * i for i in range(25)]
Ts = [round(353.15 + 3.0 * math.exp(-4 * math.log(2) * ((x - 0.6225) / 0.10) ** 2), 3) for x in xs]
print(' scan positions', xs[:3], '...', xs[-1], 'n', len(xs)); print(' scan T', Ts)
T = [interp(xs, Ts, x) for x in z]
Tm = math.fsum(T) / len(T)
therm = [1e5 * alpha * (t - Tm) for t in T]
print(' mean T', Tm, 'max dT', max(T) - Tm, 'thermal I peak', max(therm), 'min', min(therm), 'I per K', 1e5 * alpha)
def fl(iu):
    return ss.flatness_from_elongation(z, [v * 1e-5 for v in iu], youngs_modulus_pa=E, poisson_ratio=ss.ALUMINIUM_NU, thickness_m=h, mean_tension_pa=sT, yield_stress_pa=sy)
def show(name, iu):
    f = fl(iu)
    print(f'  {name}: max {f["max_i_units"]:.4f} min {f["min_i_units"]:.4f} status {f["status"]} / {f["released_status"]}')
    for b in f['bands']:
        print(f'      band [{b["start_m"]:.3f},{b["end_m"]:.3f}] peak {b["peak_i_units"]:.4f} at {b["peak_position_m"]:.4f} {b["sense"]} {b["state"]} U={b["buckling_utilisation"]:.3f} {b["state_after_tension_release"]} Urel={b["released_buckling_utilisation"]:.3f}')
    return f
fm = show('mechanical (re-evaluated from i_units_with_feedback)', mech)
print('  re-evaluated equals artifact bands:', [round(b['peak_i_units'], 6) for b in fm['bands']] == [round(b['peak_i_units'], 6) for b in st['levels']['with_feedback']['bands']], [b['state'] + '/' + b['state_after_tension_release'] for b in st['levels']['with_feedback']['bands']])
show('as measured hot = mechanical + thermal', [a + b for a, b in zip(mech, therm)])
show('thermal term alone', therm)
show('after cooling if the hot reading had been held flat = -thermal', [-b for b in therm])
print('--- C7 dilution table (zone 52 mm)')
def tophat(b, w): return (min(b, w) / w, min(b / 2, w) / w)
def gauss(b, w):
    k = math.sqrt(math.pi / (4 * math.log(2)))
    return (b / w * k * math.erf(math.sqrt(math.log(2)) * w / b), b / (2 * w) * k * math.erf(2 * math.sqrt(math.log(2)) * w / b))
for w in (0.052, 0.026):
    for b in (0.010, 0.020, 0.040, 0.080, 0.160):
        print(f'  zone {w*1e3:.0f} mm band {b*1e3:.0f} mm: top-hat centred {tophat(b, w)[0]:.4f} on-boundary {tophat(b, w)[1]:.4f}; gaussian(FWHM) centred {gauss(b, w)[0]:.4f} on-boundary {gauss(b, w)[1]:.4f}')
print('  report check: 25 I-units, 20 mm top-hat in 52 mm ->', 25 * 20 / 52)
# half-peak width of the model loose band
pk = max(range(len(mech)), key=lambda i: mech[i]); half = mech[pk] / 2
lo = pk
while lo > 0 and mech[lo] > half: lo -= 1
hi = pk
while hi < len(mech) - 1 and mech[hi] > half: hi += 1
print('  model loose band: peak', mech[pk], 'at', z[pk], 'approx half-peak width', z[hi] - z[lo])
print('--- C7 gauge transfer')
def gauge(pitch, speed, spot, tau, dt=None):
    f = speed / pitch; x = math.pi * spot / pitch
    hs = abs(math.sin(x) / x) if x else 1.0; ht = 1 / math.sqrt(1 + (2 * math.pi * f * tau) ** 2)
    return f, hs, ht, hs * ht, (None if dt is None else f > 0.5 / dt)
for (pitch, u) in ((0.08408, 16.0), (0.07647, 14.5), (0.024921, 7.8333), (0.024921, 6.0)):
    print('  pitch', pitch, 'speed', u, 'spot 10 mm tau 5 ms dt 1 ms ->', gauge(pitch, u, 0.010, 0.005, 0.001))
print('   averaging length u*tau at 10 m/s, 5 ms:', 10 * 0.005)
print('--- G12 shell pitch')
def pitch(R, t, nu=0.33): return 2 * math.pi * math.sqrt(R * t) / (12 * (1 - nu * nu)) ** 0.25
print('  coefficient nu=0.33', 2 * math.pi / (12 * (1 - 0.33 ** 2)) ** 0.25, 'nu=0.3', 2 * math.pi / (12 * (1 - 0.09)) ** 0.25)
for R, t in ((0.125, 30e-6), (0.15, 30e-6), (0.6, 30e-6), (0.125, 18e-6), (0.15, 18e-6), (0.6, 18e-6), (0.125, 12e-6), (0.15, 12e-6), (0.5, 30e-6), (0.5, 12e-6)):
    print(f'  R {R} t {t*1e6:.0f} um -> pitch {pitch(R, t)*1e3:.4f} mm ; sigma_cr = E t/(R sqrt(3(1-nu^2))) = {E*t/(R*math.sqrt(3*(1-0.33**2)))/1e6:.4f} MPa')
print('  repo roller wrinkle fn:', ss.roller_wrinkle_critical_lateral_stress_pa(30e-6, 0.125, E, 0.33) if True else None)
print('--- SS-V2 / SS-V3 buckling benchmark')
s = ss.narrow_band_buckling_stress_pa(0.5e-3, 0.150, 210e9, 0.3)
print('  SS-V2: sigma_cr k=4 b=150mm t=0.5mm E=210GPa:', s, 'I-units', s / 210e9 * 1e5, 'ratio to 5.3:', s / 210e9 * 1e5 / 5.3, 'assumed half-wave 150 vs measured 60 ->', 150 / 60)
print('  SS-V3: assumed half-wave 105 vs measured 75/2 ->', 105 / 37.5)
print('--- Fleck eq.29 regime boundary for the demo mill')
def h0c(R, r, mu, Ys, Er): return 12 * R * r ** 0.5 * mu ** 1.24 * (Ys / Er) ** 0.76
Er = 210e9 / (1 - 0.09)
for Ys in (175e6, 175e6 * 2 / math.sqrt(3)):
    for mu in (0.03, 0.05):
        print(f'  R 0.135 r 0.4 mu {mu} Ys {Ys/1e6:.1f} MPa E* {Er/1e9:.1f} GPa -> h0c {h0c(0.135, 0.4, mu, Ys, Er)*1e6:.2f} um')
print('  BT-V1 mill:', h0c(0.089, 0.25, 0.03, 230e6, 230e9) * 1e6, 'um (entry 20 um is below -> regimes II/III)')
