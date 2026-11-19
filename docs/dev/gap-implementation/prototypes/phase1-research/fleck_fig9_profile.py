import numpy as np
import fleck_fig9 as f
from fleck_fig9_triangles import BiteT, S
B0 = 0.01e-3 * (230e9) ** 2 / (0.089 * (230e6) ** 2)
print("ramp_um  W_bar  Q_bar  entry_mm  x_AB  x_BE  x_EF(peak)  exit_mm  P(x_AB)  P(-0.6mm)  P(0)  P(x_BE)  P_peak  b1/b0  fwd_slip  flat_share")
for ramp in (21.0, 10.0, 5.0):
    b = BiteT(B0, 30.0, 0.25, zones=(80, 208, 8, 104), with_E=True, ramp_um=ramp)
    u, nrm = b.solve(f.initial(b, True), verbose=False)
    N = b.N; P, bnd = u[:N+1], u[N+1:]; x = b.grid(bnd); B = b.shape(x, P)
    xe, Pe = b.ext(x, P)
    W = np.trapezoid(Pe, xe); Q = -np.trapezoid(Pe*xe, xe)
    iA, iB = b.nA, b.nA+b.nB; iE = iB+b.nE
    xm = x/S
    print(f"{ramp:6.1f} {W:6.1f} {Q:6.1f} {xm[0]:8.3f} {xm[iA]:6.3f} {xm[iB]:6.3f} {xm[iE]:8.3f} {xm[-1]:9.3f} "
          f"{P[iA]:7.2f} {np.interp(-0.6, xm, P):9.2f} {np.interp(0.0, xm, P):6.2f} {P[iB]:7.2f} {P[iE]:7.2f} "
          f"{B[iB]/B0:6.3f} {B[iE]/B[-1]-1:8.3f} {(xm[iB]-xm[iA])/(xm[-1]-xm[0]):8.2f}")
