from loop import *
import sys
name = sys.argv[1] if len(sys.argv) > 1 else 'lengthwise_bands'
valve_levels = [float(v) for v in (sys.argv[2].split(',') if len(sys.argv) > 2 else ['0', '1'])]
case, art = load(name)
th = thermal(case, art); sp = shape_params(case, art)
T0 = time.perf_counter()
healthy = th.steady([1.0] * th.count)
actual = th.steady(th.levels)
z = actual['z_m']; idx = strip_idx(z, sp); zs = [z[i] for i in idx]
a0, a1 = sp['strip_centre_m'] - sp['strip_width_m'] / 2, sp['strip_centre_m'] + sp['strip_width_m'] / 2
nz_sm = int(math.ceil(sp['strip_width_m'] / 0.052 - 1e-9))
edges = zone_edges(sp['strip_centre_m'], 0.052, nz_sm)
S, cov = zone_matrix(zs, edges, a0, a1)
# reading operator M = S*G via the symmetric transfer applied to the rows of S (mean-free part handled by re-meaning)
t0 = time.perf_counter()
M = []
for row in S:
    # G is symmetric: (S G)_j = G S_j^T ; I-units operator includes the mean removal (also symmetric)
    M.append([v * 1e6 for v in linear_i_units(zs, [x * 1e-6 for x in row], sp)])
print('reading operator', time.perf_counter() - t0, 's; zones', nz_sm, 'cov', cov[0], cov[-1])
def readings(dev_s):
    r = [sum(m * d for m, d in zip(row, dev_s)) for row in M]
    mean = sum(c * v for c, v in zip(cov, r)) / sum(cov)
    return [v - mean for v in r]
base = healthy['radius_growth_m']
dev0 = [actual['radius_growth_m'][i] - base[i] for i in idx]
r0 = readings(dev0)
# check against the direct route
I0 = linear_i_units(zs, dev0, sp)
direct = [sum(s * v for s, v in zip(row, I0)) for row in S]
mean = sum(c * v for c, v in zip(cov, direct)) / sum(cov); direct = [v - mean for v in direct]
print('operator check max diff', max(abs(a - b) for a, b in zip(r0, direct)), 'max reading', max(r0), min(r0), 'profile peak', max(I0))
# control zones: nozzles grouped by cooling_zone_pitch
per = int(round(case['width_model']['cooling_zone_pitch_m'] / th.header.nozzle_pitch_m))
nctrl = th.count // per
groups = [list(range(k * per, (k + 1) * per)) for k in range(nctrl)]
def nozzle_levels(u):
    lv = list(th.levels)
    for k, g in enumerate(groups):
        for i in g: lv[i] = th.levels[i] * u[k]
    return lv
# influence matrix around u = 1 (steady, step -0.2)
t0 = time.perf_counter()
B = []
for k in range(nctrl):
    u = [1.0] * nctrl; u[k] = 0.8
    stt = th.steady(nozzle_levels(u))
    d = [stt['radius_growth_m'][i] - actual['radius_growth_m'][i] for i in idx]
    rk = readings(d)
    B.append([v / (-0.2) for v in rk])      # per unit level increase
print('influence matrix', time.perf_counter() - t0, 's for', nctrl, 'zones; diag sample', [round(B[k][min(range(nz_sm), key=lambda j: abs((edges[j]+edges[j+1])/2 - (th.positions[groups[k][0]]+th.positions[groups[k][-1]])/2))], 2) for k in (2, 6, 8)])
import json
json.dump({'B': B, 'M': M, 'edges': edges, 'cov': cov, 'r0': r0, 'zs': zs}, open(f'loop_{name}.json', 'w'))
print('setup total', time.perf_counter() - T0)
