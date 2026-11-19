import sys, json, math
sys.path.insert(0, '/home/user/PhysicRollModel'); sys.dont_write_bytecode = True
import shp
from physicroll import strip_shape as ss, band_width as bw, band_diagnosis as bd
A = '/home/user/PhysicRollModel/artifacts/band_diagnosis/'
r = json.load(open(A + 'battery-foil-demo.result.json'))
st = r['width']['shape']['steady']; ts = r['width']['thermal_steady']
z, iu = st['z_m'], st['i_units_with_feedback']; a0, a1 = ts['strip_start_m'], ts['strip_end_m']
def zone_of(e, x):
    for j in range(len(e) - 1):
        if e[j] - 1e-9 <= x < e[j + 1] - 1e-9: return j
    return None
def hpw(zv, v, pk):
    n = 1; i = pk - 1
    while i >= 0 and v[i] * v[pk] > 0 and abs(v[i]) >= abs(v[pk]) / 2: n += 1; i -= 1
    i = pk + 1
    while i < len(v) and v[i] * v[pk] > 0 and abs(v[i]) >= abs(v[pk]) / 2: n += 1; i += 1
    return n * (zv[1] - zv[0])
for n, s in ((24, 0.0), (24, 0.125)):
    e = shp.zone_edges(0.75, 0.052, n); mm = shp.zone_means(z, iu, a0, a1, e); rd, mean = shp.readings(mm, e, s)
    print(f'zones {n} s={s}: edges {e[0]:.3f}..{e[-1]:.3f} coverage first/last {mm[0][1]:.4f} {mm[-1][1]:.4f} mean {mean:.6f}')
    for b in st['levels']['with_feedback']['bands']:
        j = zone_of(e, b['peak_position_m']); pk = min(range(len(z)), key=lambda i: abs(z[i] - b['peak_position_m']))
        print(f'   band peak {b["peak_i_units"]:.4f} at {b["peak_position_m"]:.4f} hpw {hpw(z, iu, pk):.3f} -> zone {j} [{e[j]:.3f},{e[j+1]:.3f}] reading {rd[j]:.4f} ratio {rd[j]/b["peak_i_units"]:.4f}')
    print('   readings zones 7..11', [round(x, 4) for x in rd[7:12]])
    ev = r['width']['thermal_events']['events'][0]['peak_shape']
    mm2 = shp.zone_means(ev['z_m'], ev['i_units_with_feedback'], a0, a1, e); rd2, _ = shp.readings(mm2, e, s)
    j = max(range(len(rd2)), key=lambda k: abs(rd2[k])); print(f'   event: zone {j} [{e[j]:.3f},{e[j+1]:.3f}] reading {rd2[j]:.4f} true peak {max(ev["i_units_with_feedback"]):.4f}')
case = bd.validate_case(json.load(open('/home/user/PhysicRollModel/scenarios/band_diagnosis_battery_foil.json')))
lay = bw.spray_layout(case); e = shp.zone_edges(0.75, 0.052, 24)
per = [[k for k, x in enumerate(lay['nozzle_positions_m']) if e[j] - 1e-9 <= x < e[j + 1] - 1e-9] for j in range(24)]
print('nozzles per zone (24 zones):', per)
rip = r['width']['shape'].get('nozzle_pattern_ripple')
if isinstance(rip, dict) and 'i_units_with_feedback' in rip:
    v = rip['i_units_with_feedback']; mm3 = shp.zone_means(z, v, a0, a1, e); rd3, _ = shp.readings(mm3, e, 0.0)
    print('ripple: profile max abs', max(abs(x) for x in v), 'max abs zone reading', max(abs(x) for x in rd3 if x is not None), 'len', len(v), len(z))
print('factors', [math.sqrt((1 + a) * (1 + b) / (1 + a + b)) for a, b in ((1, 1), (0.2, 0.2), (0.2, 1.1), (1.075, 1.075))])
print('eq29 fig1', 12 * 0.089 * 0.5 ** 0.5 * 0.03 ** 1.24 * (230e6 / 230e9) ** 0.76 * 1e6)
# hot profile zone readings (24 zones) for package 6
xs = [0.15 + 0.05 * i for i in range(25)]
Ts = [round(353.15 + 3.0 * math.exp(-4 * math.log(2) * ((x - 0.6225) / 0.10) ** 2), 3) for x in xs]
def interp(x):
    if x <= xs[0]: return Ts[0]
    if x >= xs[-1]: return Ts[-1]
    i = min(int((x - xs[0]) / 0.05 + 1e-9), len(xs) - 2); t = (x - xs[i]) / (xs[i + 1] - xs[i]); return Ts[i] + t * (Ts[i + 1] - Ts[i])
T = [interp(x) for x in z]; Tm = math.fsum(T) / len(T); th = [1e5 * 23.6e-6 * (t - Tm) for t in T]
hot = [a + b for a, b in zip(iu, th)]
mm4 = shp.zone_means(z, hot, a0, a1, e); rd4, _ = shp.readings(mm4, e, 0.0); j = max(range(24), key=lambda k: abs(rd4[k]))
print('hot profile: Tmean', Tm, 'thermal peak', max(th), 'hot peak', max(hot), 'zone', j, 'reading', rd4[j])
