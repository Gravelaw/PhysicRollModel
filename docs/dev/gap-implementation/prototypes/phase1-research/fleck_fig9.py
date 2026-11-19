"""Check C4: re-implementation of Fleck, Johnson, Mear & Zhang (1992) eqs (22), (23) with the
zone structure and matching conditions of their Appendix 2, in the paper's dimensionless
variables.  Two structures are solved on the Fig. 9 case:

  full   : A (slip, alpha=+1) | B (flat, no slip) | E (slip, alpha=+1) | F (slip, alpha=-1)
  no_E   : A | B | F          (the flat zone carried up to the neutral point)

Discretisation choices made here (not in the paper): boundary-fitted grid, each zone uniform;
exact influence coefficients for piecewise-linear pressure on a non-uniform grid, including the
half elements at the two ends where the pressure steps to 1 - Sigma; eq. (15) integrated with p
and 1/b linear over an element (derived form, not the printed eq. (20)); Newton with a finite-
difference Jacobian and a backtracking line search.
"""
import sys
import numpy as np

PI = np.pi


def G(t):
    a = np.abs(t)
    out = np.zeros_like(t)
    m = a > 0
    out[m] = 0.5 * t[m] ** 2 * np.log(a[m]) - 0.75 * t[m] ** 2
    return out


def G1(t):
    a = np.abs(t)
    out = np.zeros_like(t)
    m = a > 0
    out[m] = t[m] * np.log(a[m]) - t[m]
    return out


def kernel(x):
    """M[j, k] = Int hat_k(x') ln|x_j - x'| dx' (end nodes: half hats)."""
    T = x[:, None] - x[None, :]
    d = np.diff(x)
    g, g1 = G(T), G1(T)
    M = np.zeros_like(T)
    M[:, :-1] += g1[:, :-1] + (g[:, 1:] - g[:, :-1]) / d[None, :]
    M[:, 1:] += (g[:, :-1] - g[:, 1:]) / d[None, :] - g1[:, 1:]
    return M


def dkernel_row(x, j):
    """d/dx of M[., k] evaluated at node j (interior j only)."""
    t = x[j] - x
    d = np.diff(x)
    g1 = G1(t)
    out = np.zeros_like(x)
    out[:-1] += (g1[1:] - g1[:-1]) / d
    out[1:] += (g1[:-1] - g1[1:]) / d
    out[0] += np.log(abs(t[0]))
    out[-1] -= np.log(abs(t[-1]))
    return out


class Bite:
    def __init__(self, B0, U, r, S0=0.0, S2=0.0, zones=(30, 50, 12, 30), with_E=True):
        self.B0, self.U, self.r, self.S0, self.S2 = B0, U, r, S0, S2
        self.with_E = with_E
        self.nA, self.nB, self.nE, self.nF = zones
        if not with_E:
            self.nE = 0
        self.N = self.nA + self.nB + self.nE + self.nF
        self.nb = 5 if with_E else 4

    def grid(self, bnd):
        if self.with_E:
            X0, Xa, Xb, Xn, X2 = bnd
            parts = [np.linspace(X0, Xa, self.nA + 1), np.linspace(Xa, Xb, self.nB + 1)[1:],
                     np.linspace(Xb, Xn, self.nE + 1)[1:], np.linspace(Xn, X2, self.nF + 1)[1:]]
        else:
            X0, Xa, Xn, X2 = bnd
            parts = [np.linspace(X0, Xa, self.nA + 1), np.linspace(Xa, Xn, self.nB + 1)[1:],
                     np.linspace(Xn, X2, self.nF + 1)[1:]]
        return np.concatenate(parts)

    def shape(self, x, P):
        M = kernel(x)
        return self.B0 - 0.5 * (x[0] ** 2 - x ** 2) + (2.0 / PI) * ((M[0, :] - M) @ P)

    def residual(self, u):
        N = self.N
        P, bnd = u[:N + 1], u[N + 1:]
        x = self.grid(bnd)
        if np.any(np.diff(x) <= 0):
            return np.full(u.size, 1e6)
        B = self.shape(x, P)
        if np.any(B <= 0):
            return np.full(u.size, 1e6)
        R = np.zeros(u.size)
        R[0] = P[0] - (1.0 - self.S0)
        c = np.diff(x)
        iA, iB = self.nA, self.nA + self.nB
        iE = iB + self.nE
        alpha = np.zeros(N + 1)
        alpha[1:iA + 1] = 1.0
        alpha[iB + 1:iE + 1] = 1.0
        alpha[iE + 1:] = -1.0
        i = np.arange(1, N + 1)
        w1 = 1.0 / (3 * B[i - 1]) + 1.0 / (6 * B[i])
        w2 = 1.0 / (6 * B[i - 1]) + 1.0 / (3 * B[i])
        ode = (P[i] * (1 - alpha[i] * self.U * c * w2) - np.log(B[i] / B[i - 1])
               - P[i - 1] * (1 + alpha[i] * self.U * c * w1))
        flat = (B[i] - B[i - 1])
        isB = (i > iA) & (i <= iB)
        R[1:N + 1] = np.where(isB, flat, ode)
        k = N + 1
        # condition 1: dB/dX = 0 at X_AB (analytic slope)
        slope_a = x[iA] - (2.0 / PI) * (dkernel_row(x, iA) @ P)
        R[k] = slope_a
        k += 1
        if self.with_E:
            # condition 2: B1 dP/dX = U P at X_BE, from the flat side (one-sided, second order)
            cB = c[iB - 1]
            dP = (3 * P[iB] - 4 * P[iB - 1] + P[iB - 2]) / (2 * cB)
            R[k] = B[iB] * dP - self.U * P[iB]
            k += 1
        # condition 3: P = 1 - Sigma_2 at exit
        R[k] = P[N] - (1.0 - self.S2)
        k += 1
        # condition 4: dB/dX = 0 at exit (last element, finite difference)
        R[k] = (B[N] - B[N - 1]) / c[-1]
        k += 1
        # reduction
        R[k] = B[N] - (1.0 - self.r) * self.B0
        return R

    def solve(self, u, tol=1e-9, itmax=80, verbose=True):
        R = self.residual(u)
        for it in range(itmax):
            nrm = np.linalg.norm(R)
            if verbose:
                print(f"  it {it:2d}  |R| {nrm:.3e}")
            if nrm < tol:
                break
            J = np.zeros((u.size, u.size))
            for j in range(u.size):
                h = 1e-6 * max(1.0, abs(u[j]))
                up = u.copy()
                up[j] += h
                J[:, j] = (self.residual(up) - R) / h
            try:
                du = np.linalg.solve(J, -R)
            except np.linalg.LinAlgError:
                du = np.linalg.lstsq(J, -R, rcond=None)[0]
            lam = 1.0
            while lam > 1e-6:
                un = u + lam * du
                Rn = self.residual(un)
                if np.linalg.norm(Rn) < (1 - 1e-4 * lam) * nrm:
                    break
                lam *= 0.5
            else:
                print("  line search failed")
                break
            u, R = un, Rn
        return u, np.linalg.norm(R)

    def report(self, u, label):
        N = self.N
        P, bnd = u[:N + 1], u[N + 1:]
        x = self.grid(bnd)
        B = self.shape(x, P)
        W = np.trapezoid(P, x)
        Q = -np.trapezoid(P * x, x) + self.B0 * self.S0 - B[-1] * self.S2
        iA, iB = self.nA, self.nA + self.nB
        iE = iB + self.nE
        c = np.diff(x)
        # shear demand in the flat zone relative to the friction limit, q/(mu p) = B1 P'/(U P)
        dP = np.gradient(P[iA:iB + 1], x[iA:iB + 1])
        ratio = B[iA:iB + 1] * dP / (self.U * P[iA:iB + 1])
        # one-sided value at the downstream end of the flat zone
        end_ratio = B[iB] * ((3 * P[iB] - 4 * P[iB - 1] + P[iB - 2]) / (2 * c[iB - 1])) / (self.U * P[iB])
        k = 0.089 / 1000.0 * 1e3  # X -> mm for R = 89 mm, Ys/E* = 1e-3
        print(f"{label}: W_bar = {W:.2f}   Q_bar = {Q:.1f}   B2/B0 = {B[-1]/self.B0:.4f}")
        print(f"   boundaries X: {np.array2string(bnd, precision=3)}   in mm (R 89 mm): "
              f"{np.array2string(bnd * k, precision=3)}")
        print(f"   P at end of A {P[iA]:.3f}, max P in flat zone {P[iA:iB+1].max():.3f}, "
              f"P at end of flat zone {P[iB]:.3f}, peak P {P.max():.3f} at x = {x[P.argmax()]*k:.3f} mm")
        print(f"   flat-zone thickness B1/B0 = {B[iB]/self.B0:.4f}; forward slip = B1/B2 - 1 = "
              f"{B[iE]/B[-1]-1:.4f} (neutral-point thickness over exit thickness)")
        print(f"   shear demand over friction limit in flat zone: max interior {ratio[1:-1].max():.3f}, "
              f"at its downstream end {end_ratio:.3f}; min dB/dX sign check: "
              f"max(B[i]-B[i-1]) outside flat = {max(np.diff(B)[:iA].max(), np.diff(B)[iB:].max()):.2e}")
        return W, x, P, B


def initial(b, with_E):
    # from the enlarged Fig. 9 (mm) -> X = x[mm] * 11.236
    s = 11.236
    if with_E:
        bnd = np.array([-1.18, -0.62, 0.34, 0.41, 0.95]) * s
    else:
        bnd = np.array([-1.10, -0.60, 0.40, 0.90]) * s
    x = b.grid(bnd)
    iA, iB = b.nA, b.nA + b.nB
    iE = iB + b.nE
    P = np.empty(b.N + 1)
    P[:iA + 1] = np.exp(np.linspace(0, np.log(5.0), iA + 1))
    P[iA:iB + 1] = np.linspace(5.0, 6.3, iB - iA + 1)
    if with_E:
        P[iB:iE + 1] = np.linspace(6.3, 7.7, iE - iB + 1)
        P[iE:] = np.exp(np.linspace(np.log(7.7), 0, b.N - iE + 1))
    else:
        P[iB:] = np.exp(np.linspace(np.log(6.3), 0, b.N - iB + 1))
    return np.concatenate([P, bnd])


if __name__ == "__main__":
    B0 = 0.01e-3 * (230e9) ** 2 / (0.089 * (230e6) ** 2)
    U = 0.03 * 230e9 / 230e6
    print(f"Fig. 9 case: B0 = {B0:.2f}, U = {U:.1f}, r = 0.25, no tensions")
    scale = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    for with_E in (True, False):
        z = tuple(int(round(n * scale)) for n in (30, 50, 12, 30))
        b = Bite(B0, U, 0.25, zones=z, with_E=with_E)
        u0 = initial(b, with_E)
        print(("full structure A|B|E|F" if with_E else "structure without zone E, A|B|F"), "zones", z)
        u, nrm = b.solve(u0, verbose=False)
        print(f"   final |R| = {nrm:.2e}")
        b.report(u, "   result")
