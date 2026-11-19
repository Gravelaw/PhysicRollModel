import sys, json, math
sys.path.insert(0, '/home/user/PhysicRollModel'); sys.dont_write_bytecode = True
from physicroll import strip_shape as ss
rows = json.load(open('g4rows.json'))
r = json.load(open('/home/user/PhysicRollModel/artifacts/band_diagnosis/battery-foil-demo.result.json'))
inp = r['inputs']; p = inp['pass']; E_r, nu_r = 210e9, 0.3; E_s = 70e9; R = 0.135
z = r['width']['shape']['steady']['z_m']
def tf(dp, a, q, nx, h, fb):
    n = len(z); dz = z[1] - z[0]; period = n * dz; q_eff = q + (nx * E_s / h if fb else 0.0)
    spec = ss._dft(dp); out = []
    for k in range(n):
        kk = min(k, n - k); lam = math.inf if kk == 0 else period / kk
        le = 4 * a if lam < 4 * a else (R if lam > R else lam)
        c = ss._compliance(le, a, E_r, nu_r); out.append(2 * c / (1 + 2 * c * (q if kk == 0 else q_eff)) * spec[k])
    return [v.real / n for v in ss._dft(out, sign=+1)]
srcs = [('case pass', p)] + [(s['label'], s) for s in inp['schedule']]
for row, (label, src) in zip(rows, srcs):
    mu, h = src['friction_coefficient'], src['exit_thickness_m']
    dp = [row['m_mu'] * 0.01 * mu * math.exp(-4 * math.log(2) * ((x - 0.75) / 0.1) ** 2) for x in z]
    res = {}
    for fb in (True, False):
        dh = tf(dp, row['a'], row['q'], row['nx'], h, fb)
        eps = [-v / h for v in dh]; m = math.fsum(eps) / len(eps); iu = [(e - m) * 1e5 for e in eps]
        res[fb] = min(iu)
    lim = -1e5 * row['m_mu'] * 0.01 * mu / (row['nx'] * E_s)
    print(f"{label[:14]:14s} h1 {h*1e6:6.1f} exponent {row['n']:.3f} I/% feedback {res[True]:.4f} compliance-only {res[False]:.3f} feedback-limit(peak, no mean) {lim:.4f}")
