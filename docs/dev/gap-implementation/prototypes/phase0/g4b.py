import sys, json, math
sys.path.insert(0, '/home/user/PhysicRollModel'); sys.dont_write_bytecode = True
from physicroll import strip_shape as ss
rows = json.load(open('g4rows.json'))
r = json.load(open('/home/user/PhysicRollModel/artifacts/band_diagnosis/battery-foil-demo.result.json'))
inp = r['inputs']; p = inp['pass']
E_r, nu_r = inp['stand']['roll_youngs_modulus_pa'], inp['stand']['roll_poisson_ratio']
E_s = inp['material']['youngs_modulus_pa']; sy = inp['material']['yield_stress_pa']
R = p['work_roll_radius_m']; W = p['width_m']
st = r['width']['shape']['steady']
z = st['z_m']
print('used', r['width']['inputs_used'])
def transfer_force(z, dp, a, q, radius, nx, h, e_s, xi=1.0):
    n = len(z); dz = z[1] - z[0]; period = n * dz
    q_fb = nx * e_s * xi / h
    q_eff = q + q_fb
    spec = ss._dft(dp)
    lam_short = 4 * a
    gains = []
    for k in range(n):
        kk = min(k, n - k)
        lam = math.inf if kk == 0 else period / kk
        lam_eff = lam_short if lam < lam_short else (radius if lam > radius else lam)
        c = ss._compliance(lam_eff, a, E_r, nu_r)
        gains.append(2 * c / (1 + 2 * c * (q if kk == 0 else q_eff)))
    out = ss._dft([g * s for g, s in zip(gains, spec)], sign=+1)
    return [v.real / n for v in out]
def gauss(z, c, fwhm, amp):
    return [amp * math.exp(-4 * math.log(2) * ((x - c) / fwhm) ** 2) for x in z]
def run(row, src, fwhm, frac, centre=0.75):
    mu = src['friction_coefficient']; h = src['exit_thickness_m']
    dmu = gauss(z, centre, fwhm, frac * mu)
    dp = [row['m_mu'] * v for v in dmu]
    dh = transfer_force(z, dp, row['a'], row['q'], R, row['nx'], h, E_s)
    el = ss.differential_elongation(z, [h] * len(z), [h + v for v in dh], xi=1.0)
    fl = ss.flatness_from_elongation(z, el['elongation'], youngs_modulus_pa=E_s, poisson_ratio=ss.ALUMINIUM_NU,
                                     thickness_m=h, mean_tension_pa=src['exit_tension_pa'], yield_stress_pa=sy)
    pk = max(dh, key=abs)
    return pk, fl
srcs = [('case pass', p)] + [(s['label'], s) for s in inp['schedule']]
# effective inputs: schedule rows as in the result
for row, (label, src) in zip(rows, srcs):
    for fwhm in (0.1, 0.052, 0.02):
        pk, fl = run(row, src, fwhm, 0.01)
        peak = max(fl['i_units'], key=abs)
        bands = [(round(b['peak_i_units'], 3), b['state'], b['state_after_tension_release']) for b in fl['bands']]
        print(f"{label[:12]:12s} h1 {src['exit_thickness_m']*1e6:6.1f} um fwhm {fwhm*1e3:5.0f} mm +1% mu: dh peak {pk:.4e} m, I peak {peak:+.4f} (min {fl['min_i_units']:.4f}), 2 I-units at dmu/mu = {2/abs(fl['min_i_units'])*1:.3f} %  bands {bands}")
# a supplied stripe: +10 % friction, 60 mm wide at 0.988 m (the second observed band) on the case pass
pk, fl = run(rows[0], p, 0.06, 0.10, centre=0.988)
print('supplied stripe +10% fwhm 60mm at 0.988:', pk, fl['min_i_units'], fl['max_i_units'], [(b['start_m'], b['end_m'], b['peak_i_units'], b['sense'], b['state'], b['state_after_tension_release']) for b in fl['bands']])
pk, fl = run(rows[0], p, 0.06, -0.10, centre=0.988)
print('supplied stripe -10% fwhm 60mm at 0.988:', pk, fl['min_i_units'], fl['max_i_units'], [(b['start_m'], b['end_m'], b['peak_i_units'], b['sense'], b['state'], b['state_after_tension_release']) for b in fl['bands']])
