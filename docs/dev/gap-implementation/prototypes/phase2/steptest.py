from loop import *
import sys, json
name = sys.argv[1]; zone_k = int(sys.argv[2]); hold = float(sys.argv[3])
case, art = load(name); th = thermal(case, art); sp = shape_params(case, art)
d = json.load(open(f'loop_{name}.json')); B, M, edges, cov = d['B'], d['M'], d['edges'], d['cov']
nctrl = len(B); per = int(round(case['width_model']['cooling_zone_pitch_m'] / th.header.nozzle_pitch_m))
groups = [list(range(k * per, (k + 1) * per)) for k in range(nctrl)]
actual = th.steady(th.levels); z = actual['z_m']; idx = strip_idx(z, sp); zs = [z[i] for i in idx]
base = actual['radius_growth_m']; base_s = actual['surface_temperature_k']
lv = list(th.levels)
for i in groups[zone_k]: lv[i] = 0.0
xz = sum(th.positions[i] for i in groups[zone_k]) / per
j_sm = max(j for j in range(len(M)) if edges[j] <= xz + 1e-9)
# zone means of the surface temperature change (for the strip-temperature term)
S, _ = zone_matrix(zs, edges, edges[0], edges[-1])
plant = Plant(th); rows = plant.rows_from(actual)
dt = 0.5; t = 0.0; first = True; T, Ym, Ts = [0.0], [0.0], [0.0]
T0 = time.perf_counter()
while t < hold - 1e-9:
    rows = plant.step(rows, lv, dt, first); first = False; t += dt
    growth, surf = plant.profiles(rows, lv)
    dev = [growth[i] - base[i] for i in idx]
    r = [sum(m * x for m, x in zip(row, dev)) for row in M]
    mean = sum(c * v for c, v in zip(cov, r)) / sum(cov)
    dT = [surf[i] - base_s[i] for i in idx]
    tz = [sum(s * x for s, x in zip(row, dT)) for row in S]
    mt = sum(c * v for c, v in zip(cov, tz)) / sum(cov)
    T.append(t); Ym.append(r[j_sm] - mean); Ts.append(tz[j_sm] - mt)
print('zone', zone_k, 'nozzles', groups[zone_k], 'x', round(xz, 4), 'shapemeter zone', j_sm, 'wall', round(time.perf_counter() - T0, 2))
def lag(y, tau_f, dt):   # first-order filter
    out = [y[0]]
    a = dt / (tau_f + dt)
    for v in y[1:]: out.append(out[-1] + a * (v - out[-1]))
    return out
def fopdt(T, Y, window):
    pts = [(t, y) for t, y in zip(T, Y) if t <= window + 1e-9]
    best = None
    taus = [1.0 * (1.08 ** k) for k in range(100)]   # 1 .. 2200 s
    thetas = [0.5 * k for k in range(int(min(window / 2, 30) / 0.5) + 1)]
    for th_ in thetas:
        for tau in taus:
            g = [(1 - math.exp(-(t - th_) / tau)) if t > th_ else 0.0 for t, _ in pts]
            gg = sum(v * v for v in g)
            if gg <= 0: continue
            K = sum(v * y for v, (_, y) in zip(g, pts)) / gg
            sse = sum((K * v - y) ** 2 for v, (_, y) in zip(g, pts))
            if best is None or sse < best[0]: best = (sse, K, tau, th_)
    sse, K, tau, th_ = best
    yend = pts[-1][1]
    t63 = next((t for t, y in pts if abs(y) >= 0.632 * abs(yend)), None)
    return {'window_s': window, 'gain': round(K, 2), 'tau_s': round(tau, 2), 'dead_time_s': th_, 'rms': round(math.sqrt(sse / len(pts)), 3), 'value_at_end': round(yend, 2), 't63_of_end_s': t63}
delay = 2.0 / case['pass']['exit_speed_m_s']
print('transport delay', round(delay, 3), 's')
for label, Y in (('mechanical only', Ym), ('mechanical + strip temperature (2.36 I/K x roll surface change, eta=1)', [a + 2.36 * b for a, b in zip(Ym, Ts)]), ('mechanical + eta=0.5', [a + 1.18 * b for a, b in zip(Ym, Ts)])):
    Yf = lag(Y, 1.0, dt)
    print(label)
    for w in (20, 40, 60, 120, 300, 600):
        if w <= hold: print('  ', fopdt(T, Yf, w))
print('surface temperature change under the zone at 5/10/20/60/300 s:', [round(Ts[int(x / dt)], 2) for x in (5, 10, 20, 60, 300) if x <= hold], 'mech reading:', [round(Ym[int(x / dt)], 2) for x in (5, 10, 20, 60, 300) if x <= hold])
json.dump({'t': T, 'ym': Ym, 'ts': Ts}, open(f'step_{name}_{zone_k}.json', 'w'))
