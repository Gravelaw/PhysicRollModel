"""Residual of a cosine ('sine') ground crown after order-2 and order-4 polynomial de-trending. [computed]
Assumed curve: radius drop(u) = Cr*(1-cos(a*u))/(1-cos(a)), u = 2x/L, a = half angle; Cr = crown on radius."""
import numpy as np
for Cd in (40.0, 80.0, 90.0):            # crown on diameter, um
    Cr = Cd / 2
    for a_deg in (45, 70, 90):
        a = np.radians(a_deg)
        for cover in (0.79, 1.0):           # strip width / barrel length
            u = np.linspace(-cover, cover, 801)
            r = -Cr * (1 - np.cos(a * u)) / (1 - np.cos(a))
            out = []
            for order in (2, 4):
                res = r - np.polyval(np.polyfit(u, r, order), u)
                out.append((res.max() - res.min()))
            print(f"crown {Cd:.0f} um dia ({Cr:.0f} um radius), half angle {a_deg} deg, strip/barrel {cover}: "
                  f"residual peak-to-peak after order 2: {out[0]:.3f} um radius, after order 4: {out[1]:.4f} um")
