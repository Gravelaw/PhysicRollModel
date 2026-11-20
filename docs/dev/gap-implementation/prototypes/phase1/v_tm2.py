import sys, math
sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from physicroll import chatter as ch
k = 535.65e6; Y = math.sqrt(3) * k; m_f = 0.054; w = 0.732
stand = ch.StandModel(14000.0, 38000.0, 7.01e10, 3.64e8, 0.0, 9.54e5)
spans = ch.StripSpans(200e9, 4.725, 6.6)
def run(mu, e_roll):
    bp = ch.BitePass(324e-6, 216e-6, w, 0.245, Y, mu, 151e6, 81e6)
    b = ch.derive_bite_response(bp, roll_youngs_modulus_pa=e_roll)
    return b
# equivalent Coulomb friction: mu * mean pressure = m * k
mu = 0.025
for it in range(30):
    b = run(mu, 1e14)
    pm = b.separating_force_n / (w * b.contact_length_m)
    new = m_f * k / pm
    if abs(new - mu) < 1e-9: break
    mu = new
print(f'equivalent Coulomb friction {mu:.6f} (mean pressure {pm/1e6:.2f} MPa, {it} iterations)')
for label, muv in (('equivalent', mu), ('0.02', 0.02), ('0.03', 0.03), ('0.054', 0.054)):
    try:
        b = run(muv, 1e14)
    except ValueError as e:
        print(label, 'rejected', str(e)[:100]); continue
    nf = ch.natural_frequencies(stand, b.strip_modulus_n_m)
    txt = []
    for beta in (0.5, 0.0):
        c = ch.critical_speed(stand, b, spans, speed_range_m_s=(0.5, 60.0), bite_damping_transit_fraction=beta)
        txt.append((beta, c.get('critical_exit_speed_m_s'), c.get('onset_frequency_hz'), c.get('status')))
    print(f'mu {label}: R\'/R {b.contact_radius_ratio:.4f} F {b.separating_force_n/1e6:.4f} MN ({b.separating_force_n/w/1e6:.4f} MN/m) L {b.contact_length_m*1e3:.4f} mm slip {b.forward_slip_fraction:.5f} Qs {b.strip_modulus_n_m:.5e} N/m symmetric modes {[round(v,3) for v in nf["symmetric_hz"]]} crit {txt}')
# strip modulus that puts the lower loaded symmetric mode at 124.6 Hz
lo, hi = 1e8, 1e12
for _ in range(80):
    mid = math.sqrt(lo * hi)
    f = ch.natural_frequencies(stand, mid)['symmetric_hz'][0]
    if f < 124.6: lo = mid
    else: hi = mid
print('strip modulus for 124.6 Hz:', math.sqrt(lo * hi), 'N/m; per width', math.sqrt(lo * hi) / w, 'Pa; unloaded modes', ch.natural_frequencies(stand, 0.0)['symmetric_hz'], ch.natural_frequencies(stand, 0.0)['antisymmetric_hz'])
print('stand-2 exit speed if 5.81 m/s is the strip speed between the stands:', 5.81 * 324 / 216)
