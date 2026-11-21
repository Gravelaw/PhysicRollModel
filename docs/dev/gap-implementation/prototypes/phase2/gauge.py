import cmath, math, json, os, time
HEAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 's23', 'head')
art = json.load(open(os.path.join(HEAD, 'artifacts', 'band_diagnosis', 'battery-foil-demo.result.json')))
b = art['bite']; W = 1.2; h0, h1 = 50e-6, 30e-6; u = 13.0; f = b['forward_slip_fraction']; E = 7e10
Fh, Fse, Fsx, Fhin = b['dforce_dexit_thickness_n_m'], b['dforce_dentry_tension_m2'], b['dforce_dexit_tension_m2'], b['dforce_dentry_thickness_n_m']
fh, fse, fsx = b['dslip_dexit_thickness_per_m'], b['dslip_dentry_tension_per_pa'], b['dslip_dexit_tension_per_pa']
Fmu = 51402695.58563994*W; FY = 0.011164701373029301*W
M = art['gauge_control'].get('mill_modulus_n_m'); print('mill modulus', M, 'strip modulus', -Fh)
for label, Meff in (('constant strip force (M_eff = 0)', 0.0), ('position control, open gap (M = mill modulus)', M)):
    den = Meff - Fh
    g_se, g_sx, g_mu, g_Y, g_hin = Fse/den, Fsx/den, Fmu/den, FY/den, Fhin/den
    print(label, ': dh/dsigma_e', g_se, 'm/Pa (', round(g_se*1e6/h1*100, 4), '%/MPa ), dh/dsigma_x', g_sx, ', dh/dmu', g_mu, '(', round(g_mu*0.01*0.03/h1*100, 3), '% per 1 % friction ), dh/dY', g_Y, '(', round(g_Y*0.01*175e6/h1*100, 3), '% per 1 % flow stress ), dh/dh_in', round(g_hin, 4))
g = Fse/(-Fh)
slope = -0.0016462
print('speed effect at constant force (placeholder friction slope %.4g per m/s): dh/du = %.4g m per m/s = %.3f %% of gauge per m/s' % (slope, Fmu/(-Fh)*slope, Fmu/(-Fh)*slope/h1*100))
# loop
Lg, tau_g, f_T = 1.5, 0.010, 5.0
theta = Lg/u; wT = 2*math.pi*f_T; Ttot = theta + tau_g + 1/wT; wc = 0.5/Ttot
def Lw(w, smith=False):
    s = 1j*w
    plant = 1/(1 + s/wT)/(1 + s*tau_g)
    return (wc/s)*plant*cmath.exp(-s*theta)
print('dead time', round(theta, 4), 's; T_total', round(Ttot, 4), 'crossover', round(wc, 3), 'rad/s =', round(wc/2/math.pi, 3), 'Hz')
# margins by scan
ws = [0.01*1.01**i for i in range(1200)]
pm = None; gm = None
for w0, w1 in zip(ws, ws[1:]):
    a, c = Lw(w0), Lw(w1)
    if abs(a) >= 1 > abs(c): pm = 180 + math.degrees(cmath.phase(a)) if cmath.phase(a) < 0 else 180 - (360 - math.degrees(cmath.phase(a)))
for w in ws:   # unwrap phase to find -180 crossing
    pass
def phase_unwrapped(w):
    return -90 - math.degrees(w*theta) - math.degrees(math.atan(w/wT)) - math.degrees(math.atan(w*tau_g))
wg = next(w for w in ws if abs(Lw(w)) < 1); print('phase margin', round(180 + phase_unwrapped(wg), 1), 'deg at', round(wg, 3))
wp = next(w for w in ws if phase_unwrapped(w) < -180); print('gain margin', round(1/abs(Lw(wp)), 2), 'at', round(wp, 2), 'rad/s')
u_e = u*h1/h0; D = 1.0; f_rev = u_e/(math.pi*D); w_rev = 2*math.pi*f_rev
S = 1/(1 + Lw(w_rev)); print('once per revolution: entry speed', u_e, 'f_rev', round(f_rev, 4), 'Hz; |S|', round(abs(S), 4), 'phase', round(math.degrees(cmath.phase(S)), 1))
peak = max((abs(1/(1 + Lw(w))), w) for w in ws); print('peak |S|', round(peak[0], 3), 'at', round(peak[1]/2/math.pi, 3), 'Hz;  |S| < 1 below', round(next(w for w in ws if abs(1/(1 + Lw(w))) > 1)/2/math.pi, 3), 'Hz')
# run-out -> tension -> gauge
e_c = 1e-4; R = D/2; L_e = 3.0
due_dsig = u_e*((fse + fh*g)/(1 + f) + g/h1)
lam_b = -(E/L_e)*due_dsig
A = W*h0; J = math.pi*2700*W*(R**4 - 0.15**4)/2 + 50.0
vd = (u_e/R)*e_c
def tension(w, reel=True):
    s = 1j*w
    # sigma' = (E/L)(due*sigma - R*domega - vd); J*domega' = A*R*sigma  (no regulator)
    reel_term = (E/L_e)*R*A*R/(J*s) if reel else 0.0
    return -(E/L_e)*vd/(s + lam_b + reel_term)
sig = tension(w_rev); sig0 = tension(w_rev, False)
print('bite leak rate', round(lam_b, 1), '1/s; reel inertia', round(J, 1), 'kg m2; coil-on-span frequency', round(math.sqrt((E*A/L_e)*R*R/J)/2/math.pi, 3), 'Hz; run-out speed', vd)
print('tension ripple per 0.1 mm run-out: with reel', round(abs(sig)), 'Pa, fixed reel speed', round(abs(sig0)), 'Pa; open-loop gauge ripple', abs(sig)*abs(g), 'm =', round(abs(sig)*abs(g)/h1*100, 5), '% ; closed loop', abs(sig)*abs(g)*abs(S), 'm')
# time-domain check of |S| with a 1 MPa ripple, dt 1 ms
dt = 0.001; T = 30.0; n = int(T/dt); nd = int(round(theta/dt))
buf = [0.0]*(nd + 1); yf = 0.0; trim = 0.0; act = 0.0; out = []
for k in range(n):
    t = k*dt
    d = g*1e6*math.sin(w_rev*t)               # open-loop gauge deviation from the ripple
    y = d + g*act
    buf.append(y); ym = buf.pop(0)
    yf += dt/tau_g*(ym - yf)
    trim += dt*(-wc/g)*yf                      # integral trim of the tension reference [Pa]
    act += dt*wT*(trim - act)
    out.append(y)
tail = out[int(20/dt):]
print('time domain: ripple amplitude closed/open', round(max(abs(v) for v in tail)/abs(g*1e6), 4), '(frequency response', round(abs(S), 4), ')')
# step in entry gauge of 1 % (0.5 um): response
buf = [0.0]*(nd + 1); yf = trim = act = 0.0; out = []; g_hin = Fhin/(-Fh); d0 = g_hin*0.5e-6
for k in range(int(20/dt)):
    y = d0 + g*act; buf.append(y); ym = buf.pop(0); yf += dt/tau_g*(ym - yf); trim += dt*(-wc/g)*yf; act += dt*wT*(trim - act); out.append(y)
t5 = next(k*dt for k in range(len(out)) if all(abs(v) <= 0.05*abs(d0) for v in out[k:]))
print('entry gauge step 0.5 um: initial exit deviation', d0, 'm; settles within 5 % after', t5, 's; trim needed', round(trim/1e6, 3), 'MPa; overshoot', round(-min(out)/d0, 3))
