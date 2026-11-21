import sys, json, math, time
sys.path.insert(0, '/home/user/PhysicRollModel'); sys.dont_write_bytecode = True
from physicroll import strip_shape as ss, band_width as bw, roll_thermal as rt, band_diagnosis as bd
import shp
A = '/home/user/PhysicRollModel/artifacts/band_diagnosis/'
r = json.load(open(A + 'battery-foil-demo.result.json'))
case = bd.validate_case(json.load(open('/home/user/PhysicRollModel/scenarios/band_diagnosis_battery_foil.json')))
w = case['width_model']; used = r['width']['inputs_used']
sp = bw.shape_params(case, None, w, None, supplied={
    'strip_stiffness_per_width_pa': used['strip_stiffness_per_width_pa'],
    'bite_half_length_m': used['bite_half_length_m'],
    'exit_tension_force_sensitivity_per_width_m': used['exit_tension_force_sensitivity_per_width_m']})
ts = r['width']['thermal_steady']; zfull = ts['z_m']
print('--- G13 synthetic ground profile on the battery foil demo')
xs = [0.05 * i for i in range(31)]     # 0 .. 1.5 m at 50 mm? too coarse for 20 mm marks -> use 10 mm
xs = [0.01 * i for i in range(151)]
def g(x, c, f, a): return a * math.exp(-4 * math.log(2) * ((x - c) / f) ** 2)
prof = [round(2.0e-6 * (1 - ((x - 0.75) / 0.75) ** 2) + g(x, 0.50, 0.02, 0.3e-6) + g(x, 0.95, 0.03, -0.2e-6), 9) for x in xs]
def interp(xs, ys, x):
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    i = min(int((x - xs[0]) / (xs[1] - xs[0])), len(xs) - 2)
    t = (x - xs[i]) / (xs[i + 1] - xs[i]); return ys[i] + t * (ys[i + 1] - ys[i])
y = [interp(xs, prof, x) for x in zfull]
ls = rt.local_stripes(zfull, y, sp['strip_centre_m'], sp['strip_width_m'], threshold_m=bw.STRIPE_THRESHOLD_M, smooth_order=2)
print(' residual max', max(ls['local_radius_deviation_m']), 'min', min(ls['local_radius_deviation_m']), 'stripes', [(round(s['peak_position_m'], 4), s['peak_deviation_m'], s['sign'], round(s['width_at_half_peak_m'], 4)) for s in ls['stripes']])
# back to the full grid for shape_levels (it selects the strip samples itself)
dev = [0.0] * len(zfull)
idx = [i for i, v in enumerate(zfull) if abs(v - sp['strip_centre_m']) <= sp['strip_width_m'] / 2 * (1 + 1e-12)]
for i, v in zip(idx, ls['local_radius_deviation_m']): dev[i] = v
t = time.time(); lv = bw.shape_levels(zfull, dev, sp); print(' shape_levels s', round(time.time() - t, 2))
print(' feedback peak', lv['feedback_peak_i_units'], 'compliance', lv['compliance_only_peak_i_units'], 'rigid', lv['rigid_transfer_bound_i_units'], lv['status'], lv['released_status'])
for b in lv['levels']['with_feedback']['bands']:
    print('   band', round(b['start_m'], 4), round(b['end_m'], 4), 'peak', b['peak_i_units'], 'at', b['peak_position_m'], b['sense'], b['state'], b['state_after_tension_release'])
z = lv['z_m']; iu = lv['i_units_with_feedback']
e = shp.zone_edges(0.75, 0.052, 23); mm = shp.zone_means(z, iu, ts['strip_start_m'], ts['strip_end_m'], e); rd, mean = shp.readings(mm, e, 0.0)
for b in lv['levels']['with_feedback']['bands']:
    j = max(i for i in range(len(e) - 1) if e[i] <= b['peak_position_m'])
    print('   zone reading 52mm:', j, rd[j], 'ratio', rd[j] / b['peak_i_units'])
print(' max abs zone reading', max(abs(x) for x in rd), ' profile max', max(iu), 'min', min(iu))
print(' stiffness check: F/w', r['bite']['separating_force_n'] / 1.2, 'kf1 = F/(w*draft)', r['bite']['separating_force_n'] / 1.2 / 20e-6, '1/(2C(lam=0.04))', 1 / (2 * ss.roll_line_compliance_m2_n(0.04, sp['bite_half_length_m'], sp['roll_youngs_modulus_pa'], sp['roll_poisson_ratio'])))
print('--- half-peak width of the steady loose band (samples >= half peak)*dz')
st = r['width']['shape']['steady']; z2 = st['z_m']; m = st['i_units_with_feedback']
pk = max(range(len(m)), key=lambda i: m[i]); n = 1; i = pk - 1
while i >= 0 and m[i] >= m[pk] / 2: n += 1; i -= 1
i = pk + 1
while i < len(m) and m[i] >= m[pk] / 2: n += 1; i += 1
print(' n', n, 'width', n * (z2[1] - z2[0]))
ev = r['width']['thermal_events']['events'][0]['peak_shape']
e23 = shp.zone_edges(0.75, 0.052, 23); mm = shp.zone_means(ev['z_m'], ev['i_units_with_feedback'], ts['strip_start_m'], ts['strip_end_m'], e23); rd, mean = shp.readings(mm, e23, 0.0)
j = max(range(len(rd)), key=lambda k: abs(rd[k])); print(' event peak shape: zone', j, e23[j], e23[j+1], 'reading', rd[j], 'true peak', max(ev['i_units_with_feedback']))
print('--- nozzle map 52 mm x 23 zones')
lay = bw.spray_layout(case)
per = [[k for k, x in enumerate(lay['nozzle_positions_m']) if lo <= x < hi] for lo, hi in zip(e23, e23[1:])]
print(' nozzle count', len(lay['nozzle_positions_m']), 'first', lay['nozzle_positions_m'][:3], 'per zone', per)
