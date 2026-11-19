"""Check C4b: is the grid dependence of fleck_fig9.py caused by the end conditions?
The last element before the exit (over which condition 4, dB/dX = 0, is taken) and the first
element after the entry are given a FIXED physical length delta; everything else is refined."""
import sys
import numpy as np
import fleck_fig9 as f

S = 11.236  # X per mm for R = 89 mm, Ys/E* = 1e-3


class BiteD(f.Bite):
    def __init__(self, *a, delta_x=None, delta_in=None, **k):
        super().__init__(*a, **k)
        self.delta_x, self.delta_in = delta_x, delta_in

    def grid(self, bnd):
        x = super().grid(bnd)
        iE = self.nA + self.nB + self.nE
        if self.delta_x is not None:   # exit zone: nF-1 uniform elements + one of length delta
            xn, x2 = x[iE], x[-1]
            x[iE:] = np.concatenate([np.linspace(xn, x2 - self.delta_x, self.nF), [x2]])
        if self.delta_in is not None:  # entry zone: one element of length delta + nA-1 uniform
            x0, xa = x[0], x[self.nA]
            x[:self.nA + 1] = np.concatenate([[x0], np.linspace(x0 + self.delta_in, xa, self.nA)])
        return x


B0 = 0.01e-3 * (230e9) ** 2 / (0.089 * (230e6) ** 2)
U = 30.0
print("delta_exit_um delta_entry_um  scale  elements  W_bar(full)  W_bar(no E)  contact_mm  peak")
for d_um, din_um, scale in [(20, None, 1), (20, None, 2), (20, None, 4), (20, 20, 2), (20, 20, 4),
                            (40, 40, 2), (10, 10, 2), (10, 10, 4), (5, 5, 4), (2.5, 2.5, 4)]:
    out = []
    for with_E in (True, False):
        z = tuple(int(round(n * scale)) for n in (30, 50, 12, 30))
        b = BiteD(B0, U, 0.25, zones=z, with_E=with_E, delta_x=d_um * 1e-3 * S,
                  delta_in=None if din_um is None else din_um * 1e-3 * S)
        u, nrm = b.solve(f.initial(b, with_E), verbose=False)
        N = b.N
        P, bnd = u[:N + 1], u[N + 1:]
        x = b.grid(bnd)
        out.append((np.trapezoid(P, x), (x[-1] - x[0]) / S, P.max(), nrm))
    print(f"{d_um:8.1f} {str(din_um):>12s} {scale:6d} {b.N + (12*scale if not b.with_E else 0):8d} "
          f"{out[0][0]:11.2f} {out[1][0]:11.2f} {out[0][1]:10.3f} {out[0][2]:6.2f}   |R| {out[0][3]:.0e} {out[1][3]:.0e}")
