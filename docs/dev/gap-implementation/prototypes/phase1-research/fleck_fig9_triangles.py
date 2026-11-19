"""Check C4c: the paper's own discretisation idea, 'overlapping triangular elements': the
triangle centred on each END node reaches one element beyond the contact, so the pressure ramps
from 1 - Sigma to zero over one element length c outside x = -a0 and x = a2 instead of stepping.
Condition 4 (dB/dX = 0 at exit) is then the analytic nodal slope at the exit node.
The ramp length is set independently of the interior grid to show what the result depends on."""
import numpy as np
import fleck_fig9 as f

S = 11.236
PI = np.pi


class BiteT(f.Bite):
    def __init__(self, *a, ramp_um=None, **k):
        super().__init__(*a, **k)
        self.ramp = None if ramp_um is None else ramp_um * 1e-3 * S

    def ext(self, x, P):
        c0 = self.ramp if self.ramp else (x[1] - x[0])
        cN = self.ramp if self.ramp else (x[-1] - x[-2])
        return (np.concatenate([[x[0] - c0], x, [x[-1] + cN]]), np.concatenate([[0.0], P, [0.0]]))

    def shape(self, x, P):
        xe, Pe = self.ext(x, P)
        M = f.kernel(xe)
        Be = self.B0 - 0.5 * (x[0] ** 2 - xe ** 2) + (2.0 / PI) * ((M[1, :] - M) @ Pe)
        return Be[1:-1]

    def residual(self, u):
        R = super().residual(u)
        if R[0] == 1e6:
            return R
        N = self.N
        P, bnd = u[:N + 1], u[N + 1:]
        x = self.grid(bnd)
        xe, Pe = self.ext(x, P)
        iA = self.nA
        k = N + 1
        R[k] = xe[iA + 1] - (2.0 / PI) * (f.dkernel_row(xe, iA + 1) @ Pe)      # condition 1
        k4 = k + (3 if self.with_E else 2)
        R[k4] = xe[N + 1] - (2.0 / PI) * (f.dkernel_row(xe, N + 1) @ Pe)       # condition 4
        return R


B0 = 0.01e-3 * (230e9) ** 2 / (0.089 * (230e6) ** 2)
print("zones (A,B,E,F)        ramp_um   W_bar(full)  W_bar(no E)  contact_mm  peak  el.size F um")
for zones, ramp in [((20, 52, 2, 26), None), ((40, 104, 4, 52), None), ((80, 208, 8, 104), None),
                    ((40, 104, 4, 52), 21.0), ((80, 208, 8, 104), 21.0), ((80, 208, 8, 104), 10.0),
                    ((80, 208, 8, 104), 5.0), ((80, 208, 8, 104), 2.5)]:
    out = []
    for with_E in (True, False):
        b = BiteT(B0, 30.0, 0.25, zones=zones, with_E=with_E, ramp_um=ramp)
        u, nrm = b.solve(f.initial(b, with_E), verbose=False)
        N = b.N
        P, bnd = u[:N + 1], u[N + 1:]
        x = b.grid(bnd)
        xe, Pe = b.ext(x, P)
        out.append((np.trapezoid(Pe, xe), (x[-1] - x[0]) / S, P.max(), nrm, (x[-1] - x[-2]) / S * 1e3))
    print(f"{str(zones):22s} {str(ramp):>7s} {out[0][0]:11.2f} {out[1][0]:11.2f} {out[0][1]:10.3f} "
          f"{out[0][2]:6.2f} {out[0][4]:8.1f}   |R| {out[0][3]:.0e} {out[1][3]:.0e}")
