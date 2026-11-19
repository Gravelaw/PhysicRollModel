from buck import *
import json, os
RHO, GRAV = 2700.0, 9.81
def integ(z, g): return sum(0.5*(g[i] + g[i+1])*(z[i+1] - z[i]) for i in range(len(z) - 1))
def table_scan(z, sres, t, E, nu, ks):
    D = E*t**3/(12*(1 - nu*nu)); W = z[-1] - z[0]
    st = Strip(z, sres, t, E, nu, 0.0, ('free', 'free'))
    qmax = max(-v for v in sres); rows = []
    for k in ks:
        A, G = st.assemble(k); mu = mu_max(A, G, qmax/(D*k*k/t), 1e-6)
        if mu <= 0: continue
        lam = 1/mu; x = mode(A, G, mu)
        f = [0.0]*len(z)
        for dof, i in st.map.items():
            if dof % 2 == 0: f[dof//2] = x[i]
        m = max(f, key=abs); f = [v/m for v in f]
        fpp = [0.0] + [(f[i-1] - 2*f[i] + f[i+1])/((z[i+1] - z[i-1])/2)**2 for i in range(1, len(z) - 1)] + [0.0]
        i2 = integ(z, [v*v for v in f]); i4 = integ(z, [v**4 for v in f]); phi = i4 - i2*i2/W
        isf = integ(z, [s*v*v for s, v in zip(sres, f)])          # < 0
        R = -lam*isf                                             # resistance N at criticality (sigma_T = 0)
        Rstatic = 2*D*integ(z, [v*v for v in fpp])/(t*k*k)
        g1 = RHO*GRAV*t*integ(z, [abs(v) for v in f]); c4 = E*t*k**4*phi/8
        Gk = (2/(t*k*k))*(3*g1*math.sqrt(1.5*c4))**(2/3)
        s_lift = (R + Rstatic + Gk)/(-isf)
        # amplitude at scale 1 on the table: minimise -0.5 c2 a^2 + 0.25 c4 a^4 + g1 a
        c2 = t*k*k*((-isf) - R - Rstatic)/2
        a = 0.0
        if c2 > 0 and s_lift <= 1:
            a = math.sqrt(c2/c4)          # start at the weightless root, Newton on c4 a^3 - c2 a + g1 = 0
            for _ in range(60): a = a - (c4*a**3 - c2*a + g1)/(3*c4*a*a - c2)
        rows.append({'half_wave_m': math.pi/k, 'lambda_weightless': lam, 'scale_to_lift': s_lift, 'peak_to_valley_on_table_m': 2*a,
                     'peak_to_valley_weightless_m': 2*math.sqrt(max(0.0, 4*((-isf) - R)/(E*k*k*phi)))})
    return rows
HEAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 's23', 'head')
for name, t in (('battery-foil-demo', 30e-6), ('lengthwise-bands-demo', 210e-6)):
    art = json.load(open(os.path.join(HEAD, 'artifacts', 'band_diagnosis', name + '.result.json')))
    sh = art['width']['shape']['steady']; z = sh['z_m'][::2]; iu = sh['i_units_linear_feedback'][::2]
    E, nu = 70e9, 0.33; sres = [-E*1e-5*v for v in iu]; W = z[-1] - z[0]
    ks = [math.pi/(4*W)*(160)**(i/23) for i in range(24)]
    t0 = time.perf_counter(); rows = table_scan(z, sres, t, E, nu, ks); dt = time.perf_counter() - t0
    best = min(rows, key=lambda r: r['scale_to_lift'])
    print(name, 'time', round(dt, 2))
    for r in rows[::3]: print('   half wave %.3f m  weightless lambda %.3g  scale to lift %.4g  P-V table %.3f mm  weightless %.3f mm' % (r['half_wave_m'], r['lambda_weightless'], r['scale_to_lift'], r['peak_to_valley_on_table_m']*1e3, r['peak_to_valley_weightless_m']*1e3))
    print('  lowest scale to lift', {k: (round(v, 5) if isinstance(v, float) else v) for k, v in best.items()}, '-> profile peak needed', round(best['scale_to_lift']*max(iu), 3), 'I-units (profile peak', round(max(iu), 2), ')')
# hand check: top-hat band
