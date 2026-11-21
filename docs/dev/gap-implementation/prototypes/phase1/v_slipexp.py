"""Exponents of load and forward slip in friction (chord sensitivities of hs_select)."""
import sys, math
sys.dont_write_bytecode = True
sys.path.insert(0, 'head')
from hs_select import select, derive
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; E = Es * 0.91
for name, h0, h1, R, Yv, mu, tb, tf, Ev, sm in (
        ('BT-V1 80 GPa', 20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 80e9),
        ('BT-V1 rigid', 20e-6, 15e-6, 0.089, Y, 0.03, 0.0, 0.0, E, 1e13),
        ('BT-V2 R89', 73e-6, 73e-6 * 0.43, 0.089, Y, 0.026, 0.107 * Ys, 0.132 * Ys, E, 80e9)):
    p3, u3, trail = select(h0, h1, R, Yv, mu, tb, tf, Ev, 0.3, sm)
    q = p3.post(u3); d = derive(p3, u3)
    F = q['force_per_width_n_m']; f = q['forward_slip']
    print(name, trail[-1][1], 'F', F, 'slip', f, 'e_F', d['F_mu'] * mu / F, 'f_mu', d['f_mu'], 'e_f', d['f_mu'] * mu / f)
