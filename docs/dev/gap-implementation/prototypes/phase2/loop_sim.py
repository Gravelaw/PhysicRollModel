from loop import *
import sys, json
name = sys.argv[1]; valve_levels = [float(v) for v in sys.argv[2].split(',')]
base_level = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
horizon = float(sys.argv[4]) if len(sys.argv) > 4 else 1800.0
gain = float(sys.argv[5]) if len(sys.argv) > 5 else 0.1
min_dwell = float(sys.argv[6]) if len(sys.argv) > 6 else 10.0
case, art = load(name); th = thermal(case, art); sp = shape_params(case, art)
d = json.load(open(f'loop_{name}.json')); B, M, edges, cov = d['B'], d['M'], d['edges'], d['cov']
nz_sm = len(M); nctrl = len(B)
per = int(round(case['width_model']['cooling_zone_pitch_m'] / th.header.nozzle_pitch_m))
groups = [list(range(k * per, (k + 1) * per)) for k in range(nctrl)]
def nozzle_levels(u):
    lv = list(th.levels)
    for k, g in enumerate(groups):
        for i in g: lv[i] = th.levels[i] * u[k]
    return lv
healthy = th.steady([1.0] * th.count)     # flat reference (assumption of the width model)
base = healthy['radius_growth_m']
u0 = [base_level] * nctrl
start = th.steady(nozzle_levels(u0))
if base_level != 1.0:   # reference = healthy header at the base level (ground camber matched to the operating point)
    ref_levels = [base_level] * th.count
    base = th.steady(ref_levels)['radius_growth_m']
z = start['z_m']; idx = strip_idx(z, sp)
def readings(growth):
    dev = [growth[i] - base[i] for i in idx]
    r = [sum(m * x for m, x in zip(row, dev)) for row in M]
    mean = sum(c * v for c, v in zip(cov, r)) / sum(cov)
    return [v - mean for v in r]
P = legendre_basis(nz_sm, 2)
# regularised pseudo-inverse of B^T (zones x ctrl): G = (B B^T + lam I)^-1 B, applied as du = -gain * G rho
lam = 0.01 * max(sum(b * b for b in row) for row in B)
BBt = [[sum(B[i][j] * B[k][j] for j in range(nz_sm)) + (lam if i == k else 0.0) for k in range(nctrl)] for i in range(nctrl)]
def ls(rho):
    rhs = [sum(B[k][j] * rho[j] for j in range(nz_sm)) for k in range(nctrl)]
    return solve_spd(BBt, rhs)
plant = Plant(th)
rows = plant.rows_from(start)
dt, tc, dead = 1.0, 2.0, 2.0
u_star = list(u0); u = list(u0); last_switch = [-1e9] * nctrl
def quantise(k, target, now):
    cur = u[k]
    best = min(valve_levels, key=lambda v: (abs(v - target), v))
    if best == cur: return cur
    # hysteresis: switch only when the target is closer to the new level by more than 10 % of the level gap
    if abs(target - best) + 0.1 * abs(best - cur) >= abs(target - cur): return cur
    if now - last_switch[k] < min_dwell: return cur
    last_switch[k] = now
    return best
t = 0.0; hist = []; switches = []; first = True
T0 = time.perf_counter()
lv = nozzle_levels(u)
while t < horizon - 1e-9:
    for _ in range(int(tc / dt)):
        rows = plant.step(rows, lv, dt, first); first = False; t += dt
    growth, surf = plant.profiles(rows, lv)
    r = readings(growth)
    rho = project_out(r, P)
    rho_db = [v if abs(v) > dead else 0.0 for v in rho]
    du = ls(rho_db)
    u_star = [min(1.0, max(0.0, a - gain * b)) for a, b in zip(u_star, du)]
    new_u = [quantise(k, u_star[k], t) for k in range(nctrl)]
    changed = [k for k in range(nctrl) if new_u[k] != u[k]]
    if changed:
        switches.append((t, [(k, u[k], new_u[k]) for k in changed]))
        u = new_u; lv = nozzle_levels(u); first = True
    hist.append((t, max(abs(v) for v in rho), max(abs(v) for v in r), list(u), list(u_star)))
wall = time.perf_counter() - T0
print(f'valves {valve_levels} base {base_level} gain {gain} dwell {min_dwell}: wall {wall:.2f} s, problems cached {len(plant.cache)}')
print('initial max|residual|', round(hist[0][1], 2), 'max|reading|', round(hist[0][2], 2))
for tt in (60, 120, 300, 600, 900, 1200, 1500, 1800, 2400, 3600):
    h = [x for x in hist if abs(x[0] - tt) < 1e-6]
    if h: print(f' t={tt}: max|residual| {h[0][1]:.2f}, max|reading| {h[0][2]:.2f}, u*[5..8] {[round(v,3) for v in h[0][4][5:9]]}')
n_sw = sum(len(s[1]) for s in switches)
print('switch events', len(switches), 'valve switches', n_sw, 'last switch at', switches[-1][0] if switches else None)
print('first 12 switch events', [(s[0], s[1]) for s in switches[:12]])
last300 = [x for x in hist if x[0] > horizon - 300]
print('last 300 s: residual max/min', round(max(x[1] for x in last300), 2), round(min(x[1] for x in last300), 2), 'switches in window', sum(len(s[1]) for s in switches if s[0] > horizon - 300))
print('final u', [round(v, 2) for v in u]); print('final u*', [round(v, 2) for v in u_star])
json.dump({'hist': [(h[0], h[1], h[2]) for h in hist], 'switches': switches}, open(f'sim_{name}_{len(valve_levels)}_{base_level}.json', 'w'))
