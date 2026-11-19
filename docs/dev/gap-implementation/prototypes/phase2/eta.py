import math, re, os
src = open(os.path.join('..', 's23', 'heat.py')).read()
src = src[:src.index('# --- TM report')]
exec(src)
e_r = math.sqrt(40*7850*470)
def eta(h1, u1, Vr, ld, film, label):
    tc = ld/Vr; Cs = 2.43e6*h1*u1/(2*Vr); hc = 0.13/film
    kw = dict(heat_plastic_w_m2=1e-9, heat_friction_w_m2=0.0, contact_time_s=tc, strip_capacity_j_m2k=Cs, roll_effusivity=e_r, interface_conductance_w_m2k=hc, strip_entry_k=0.0)
    r1 = partition(roll_entry_k=1.0, **kw)
    print(label, 'contact time', tc, 'C_s', round(Cs, 2), 'h_c', round(hc), ': d(strip exit)/d(roll entry) =', round(r1['strip_exit_k'], 4), ' mid-bite (half of it)', round(r1['strip_exit_k']/2, 4))
    return r1['strip_exit_k']
# battery foil F1: h1 30 um, u1 13, slip 0.1896 -> Vr = 13/1.1896; contact 2.384 mm; film 95 nm (after SPEC17 pkg 2)
eta(30e-6, 13.0, 13.0/1.1896, 2.384e-3, 9.5e-8, 'battery-foil F1')
# lengthwise case pass: h1 0.21 mm, u1 12, slip 0.0515; contact 5.17 mm; film 70 nm
eta(210e-6, 12.0, 12.0/1.0515, 5.172e-3, 7.03e-8, 'lengthwise case pass')
print('placeholder dmu for Lambda 0.380072 -> 0.380072*exp(-0.015*1.179):', 0.082*(math.exp(-0.380072*math.exp(-0.015*1.179)) - math.exp(-0.380072)), ' viscosity ratio', math.exp(-0.015*1.179))
print('two-point: dmu =', -(0.09 - 0.008)/math.log(1.0/0.01)*math.log(math.exp(-0.015*1.179)))
