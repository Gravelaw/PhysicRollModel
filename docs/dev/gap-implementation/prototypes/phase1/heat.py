"""Hand-check numbers: heat partition (lumped strip / half-space roll), skin layer, flow stress."""
import math

def partition(*, heat_plastic_w_m2, heat_friction_w_m2, contact_time_s, strip_capacity_j_m2k,
              roll_effusivity, interface_conductance_w_m2k, strip_entry_k, roll_entry_k,
              friction_to_strip_side=0.5, steps=400):
    """One roll side. Strip node (lumped, half thickness) <-> h_c <-> roll surface (half-space).
    Piecewise-constant roll flux, exact half-space response at step ends, implicit strip."""
    dt = contact_time_s / steps
    c = 2.0 / (roll_effusivity * math.sqrt(math.pi))
    w = [c * (math.sqrt((i + 1) * dt) - math.sqrt(i * dt)) for i in range(steps)]
    qs = []
    ts = strip_entry_k
    hc = interface_conductance_w_m2k
    gp = heat_plastic_w_m2 + friction_to_strip_side * heat_friction_w_m2
    gf = (1 - friction_to_strip_side) * heat_friction_w_m2
    e_roll = 0.0
    tr = roll_entry_k
    for j in range(steps):
        hist = sum(qs[k] * w[j - k] for k in range(j))        # roll surface rise from past flux
        # unknowns ts_new, q:  C (ts_new - ts)/dt = gp - hc (ts_new - tr_new);  q = hc (ts_new - tr_new) + gf
        # tr_new = roll_entry + hist + q*w0
        a = roll_entry_k + hist
        # from second: q = hc*(ts_new - a - q*w0) + gf -> q (1 + hc*w0) = hc*(ts_new - a) + gf
        # first: C/dt (ts_new - ts) = gp - (q - gf)
        k1 = hc / (1 + hc * w[0])
        # q = k1*(ts_new - a) + gf/(1 + hc*w0)
        q0 = gf / (1 + hc * w[0])
        cdt = strip_capacity_j_m2k / dt
        ts_new = (cdt * ts + gp + gf - q0 + k1 * a) / (cdt + k1)
        q = k1 * (ts_new - a) + q0
        qs.append(q)
        ts = ts_new
        tr = a + q * w[0]
        e_roll += q * dt
    total = (heat_plastic_w_m2 + heat_friction_w_m2) * contact_time_s
    return {'strip_exit_k': ts, 'roll_surface_exit_k': tr, 'roll_energy_j_m2': e_roll,
            'roll_share': e_roll / total, 'strip_share': strip_capacity_j_m2k * (ts - strip_entry_k) / total}

def erfcx(x):
    """exp(x^2)*erfc(x) for x >= 0 (math.erfc is fine up to x ~ 26)."""
    if x < 25:
        return math.exp(x * x) * math.erfc(x)
    return 1 / (x * math.sqrt(math.pi)) * (1 - 1 / (2 * x * x))

# --- TM report's own check: 24 um mean gauge, 0.2 ms, steel k 43, rho c 3.6e6; aluminium rho c 2.43e6
e_r = math.sqrt(43 * 3.6e6)
Cs = 2.43e6 * 12e-6
tc = 2e-4
Cr = 2 / math.sqrt(math.pi) * e_r * math.sqrt(tc)
print('e_roll', e_r, 'C_strip_half', Cs, 'C_roll (2/sqrt(pi)) e sqrt(tc)', Cr, 'capacity-ratio roll share', Cr / (Cr + Cs))
g = 1.0
tau = (Cs / e_r) ** 2
T = g / e_r * (2 * math.sqrt(tc / math.pi) - math.sqrt(tau) * (1 - erfcx(math.sqrt(tc / tau))))
print('exact perfect contact: tau*', tau, 'strip share', Cs * T / (g * tc), 'roll share', 1 - Cs * T / (g * tc))
for hc in (1e12, 0.13 / 70e-9, 0.13 / 200e-9, 4e4):
    r = partition(heat_plastic_w_m2=1.0, heat_friction_w_m2=0.0, contact_time_s=tc, strip_capacity_j_m2k=Cs,
                  roll_effusivity=e_r, interface_conductance_w_m2k=hc, strip_entry_k=0.0, roll_entry_k=0.0)
    print(f'h_c {hc:.3e} numerical strip share {r["strip_share"]:.4f} roll share {r["roll_share"]:.4f} sum {r["strip_share"]+r["roll_share"]:.6f}')
for n in (50, 100, 200, 400, 800):
    r = partition(heat_plastic_w_m2=1.0, heat_friction_w_m2=0.0, contact_time_s=tc, strip_capacity_j_m2k=Cs,
                  roll_effusivity=e_r, interface_conductance_w_m2k=1e12, strip_entry_k=0.0, roll_entry_k=0.0, steps=n)
    print('  steps', n, 'strip share', r['strip_share'])
# series estimate of the gap row
R_r = math.sqrt(math.pi * tc) / (2 * e_r)
print('roll resistance sqrt(pi t)/(2e)', R_r, '1/h_c at 70 nm', 70e-9 / 0.13)
# friction heat at the interface, half to each side of the film
r = partition(heat_plastic_w_m2=0.6, heat_friction_w_m2=0.4, contact_time_s=tc, strip_capacity_j_m2k=Cs,
              roll_effusivity=e_r, interface_conductance_w_m2k=0.13 / 70e-9, strip_entry_k=0.0, roll_entry_k=0.0)
print('60/40 plastic/friction, 70 nm film: strip share', r['strip_share'], 'roll share', r['roll_share'])
# sheet gauge check of the TM report: 0.25 mm, 0.4 ms
Cs2 = 2.43e6 * 0.125e-3
tau2 = (Cs2 / e_r) ** 2
tc2 = 4e-4
T2 = 1 / e_r * (2 * math.sqrt(tc2 / math.pi) - math.sqrt(tau2) * (1 - erfcx(math.sqrt(tc2 / tau2))))
print('0.25 mm, 0.4 ms perfect contact lumped strip: strip share', Cs2 * T2 / tc2, 'Fourier', 230 / 2.43e6 * tc2 / (0.125e-3) ** 2)

# --- skin layer checks
k, rc = 40.0, 7850 * 470.0
e = math.sqrt(k * rc); a = k / rc
print('repo roll: e', e, 'a', a)
print('t* = k rho c / h^2 at h=3400:', k * rc / 3400 ** 2, 'textbook steel', 43 * 3.6e6 / 3400 ** 2)
print('step response at tau=1: 1-exp(1)erfc(1) =', 1 - math.e * math.erfc(1))
q, tcx = 1e7, 2e-4
print('flash rise 2 q sqrt(t)/(sqrt(pi) e) =', 2 * q * math.sqrt(tcx) / (math.sqrt(math.pi) * e))
trev = 2 * math.pi * 0.135 / 10.0
om = 2 * math.pi / trev
print('t_rev', trev, 'omega', om, 'sinusoid amplitude q1/(e sqrt(omega)) for q1=1e5:', 1e5 / (e * math.sqrt(om)), 'skin depth sqrt(2a/omega)', math.sqrt(2 * a / om))

# --- flow stress law
m = 0.027
print('rate factor 1e-5 -> 1e-2:', (1e3) ** m, ' 160 MPa ->', 160 * 1e3 ** m)
print('rate factor 1e-3 -> 2.6e3:', (2.6e6) ** m)
print('c_T from 165->145 MPa over 80 K:', (1 - 145 / 165) / 80, ' 150->130:', (1 - 130 / 150) / 80, ' 165->125 over 130 K:', (1 - 125 / 165) / 130)
u, ld, h0, h1 = 10.0, 2.0e-3, 30e-6, 18e-6
rate = u / ld * math.log(h0 / h1)
print('mean bite rate (u/l_d) ln(h0/h1) at 10 m/s, 2 mm, 30->18 um:', rate, ' factor vs 1e-3 with m=0.027:', (rate / 1e-3) ** m, ' with T factor (c_T 0.0015, +60 K):', (rate / 1e-3) ** m * (1 - 0.0015 * 60))
