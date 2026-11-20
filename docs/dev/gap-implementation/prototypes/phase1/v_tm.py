import sys, math, json
sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from physicroll import chatter as ch
import inspect
print(inspect.signature(ch.critical_speed)); print(inspect.signature(ch.natural_frequencies))
k = 535.65e6; Y = math.sqrt(3) * k
stand = ch.StandModel(14000.0, 38000.0, 7.01e10, 3.64e8, 0.0, 9.54e5)
spans = ch.StripSpans(200e9, 4.725, 6.6)
print('unloaded', ch.natural_frequencies(stand, 0.0))
for mu in (0.015, 0.02, 0.03, 0.04):
    for ratio in (1.5, 3.0):
        bp = ch.BitePass(324e-6, 216e-6, 0.732, 0.245, Y, mu, 151e6, 81e6)
        try:
            b = ch.derive_bite_response(bp, max_radius_ratio=ratio)
        except ValueError as e:
            print(f'mu {mu} max ratio {ratio}: bite rejected: {str(e)[:110]}'); continue
        nf = ch.natural_frequencies(stand, b.strip_modulus_n_m)
        out = {}
        for beta in (0.5, 0.0):
            c = ch.critical_speed(stand, b, spans, speed_range_m_s=(0.5, 60.0), bite_damping_transit_fraction=beta)
            out[beta] = (c.get('critical_exit_speed_m_s'), c.get('onset_frequency_hz'), c.get('status'))
        tau_over_k = mu * b.separating_force_n / (0.732 * b.contact_length_m) / k
        print(f'mu {mu} R\'/R {b.contact_radius_ratio:.3f} F {b.separating_force_n/1e6:.3f} MN slip {b.forward_slip_fraction:.4f} Qs {b.strip_modulus_n_m:.3e} N/m mean friction stress/k {tau_over_k:.3f} sym modes {[round(v,1) for v in nf["symmetric_hz"]]} crit {out} flags {list(b.flags)[:3]}')
        break
