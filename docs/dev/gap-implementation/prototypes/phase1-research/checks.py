"""Consistency checks C1-C3, C5-C9 for research_phase1_equations.md (plain numpy)."""
import numpy as np
PI = np.pi
print("C1  Fleck eq. (30)/(31) against direct quadrature (unit E*, c = 1)")
def quad(fun, a, b, n=200001):
    s = np.linspace(a, b, n); return np.trapezoid(fun(s), s)
for k in (2, 3, 5):
    hat = lambda s: 1 - np.abs(s)
    v = -(2 / PI) * quad(lambda s: hat(s) * np.log(np.abs(k - s)), -1, 1)       # v into the roll
    v0 = -(2 / PI) * quad(lambda s: hat(s) * np.log(np.abs(7 - s)), -1, 1)      # reference k = 7
    br = lambda k: (k+1)**2*np.log((k+1)**2) + (k-1)**2*np.log((k-1)**2) - 2*k**2*np.log(k**2)
    printed = (1 / (2 * PI)) * (br(k) - br(7))
    dudx = -(2 / PI) * quad(lambda s: hat(s) / (k - s), -1, 1)
    c31 = -(1 / PI) * ((k+1)*np.log(((k+1)/k)**2) + (k-1)*np.log(((k-1)/k)**2))
    print(f"   k={k}: v(k)-v(7) quadrature {v - v0:+.6f}   printed (30) {printed:+.6f}   "
          f"-> printed = {printed/(v-v0):+.4f} x quadrature;  du/dx quadrature {dudx:+.6f}  (31) {c31:+.6f}")

print("C2  Fleck eq. (20): constant b, alpha=+1; exact p(c)/p(0) = exp(mu c/b)")
mu, c, b = 0.03, 2e-5, 1e-5
w = 1/(3*b) + 1/(6*b)
printed = (1 - mu*c*w) / (1 + mu*c*w)
derived = (1 + mu*c*(1/(3*b)+1/(6*b))) / (1 - mu*c*(1/(6*b)+1/(3*b)))
print(f"   exact {np.exp(mu*c/b):.6f}   derived form {derived:.6f}   printed form {printed:.6f}")

print("C3  coefficient of p in Fleck (14)")
for nus, nur, ratio, lab in ((0.3, 0.3, 1/3, "nu 0.3/0.3, Es*/ER* 1/3"), (1/3, 0.3, 1/3, "nu_s 1/3"),
                             (0.3, 0.3, 80/230, "Fig. 9 moduli 80/230")):
    print(f"   {lab}: {nus/(1-nus) + (1-2*nur)/(1-nur)*ratio:.3f}")
print("   1987 paper: Es*/E' with nu 0.3/0.3 and Es*/ER* = x: need 0.683 ->",
      "x =", (0.683 - 0.3/0.7) / (0.4/0.7))

print("C5  regime boundary eq. (29), R 89 mm, mu 0.03, Ys/E* 1e-3")
for r in (0.5, 0.25, 0.10):
    print(f"   r={r}: h0c = {12*r**0.5*0.03**1.24*(1e-3)**0.76*89e3:.1f} um")

print("C6  Wilson-Sheu fit: limits")
f1 = lambda A: 0.515 + 0.345*A - 0.860*A**2
f2 = lambda A: 1/(2.571 - A - A*np.log(1 - A))
print(f"   E=0, A->0: Ha = 2/f2 = {2/f2(1e-9):.4f} (2+pi = {2+PI:.4f});  f1(0.936) = {f1(0.936):.4f}")
for A in (0.3, 0.5, 0.7):
    for Ha in (1.0, 2.0, 4.0):
        Ews = (2/Ha - f2(A)) / f1(A)
        Wsm = Ha**2*A**2*(3.81 - 4.38*A)/4            # Marsault form, W = 1/E
        Wth = 3.81*(A*Ha/2)**2 - 4.38*A               # thesis form with p/2k = A*Ha/2 (k = Y/2)
        print(f"   A={A} Ha={Ha}: W&S E={Ews:7.3f} (W={1/Ews if Ews>0 else float('nan'):6.3f})  "
              f"Marsault W={Wsm:6.3f}  thesis(3.20) W={Wth:6.3f}")

print("C7  Patir-Cheng table [from memory] against the fits printed in E5 (4.160)")
for g, Cm, rm in ((1/9, 1.48, 0.42), (1/6, 1.38, 0.42), (1/3, 1.18, 0.42), (1, 0.90, 0.56)):
    print(f"   gamma={g:.3f}: C fit {0.89679-0.26591*np.log(g):.3f} (table {Cm});  r fit {0.43006-0.10828*g+0.23821*g*g:.3f} (table {rm})")
for g, Cm in ((3, 0.225), (6, 0.520), (9, 0.870)):
    print(f"   gamma={g}: C fit {-0.10667+0.10750*g:.3f} (table {Cm})")
print("   Wilson-Marsault percolation h_tc/sigma for gamma=9:", 3*(1 - 1/(0.47476/9+1)**0.25007),
      " (Sutcliffe & Montmitonnet quote 0.038)")

print("C8  Sutcliffe thesis Table 4.2: hw = 6 alpha eta0 u/(theta (1-exp(-alpha sy)))")
al, eta, sy, th = 1e-8, 1e-3, 230e6, 0.0058
for ur, hw in ((30, 0.323), (10, 0.108), (5, 0.054), (3, 0.032), (1, 0.011)):
    ubar = hw*1e-6*th*(1-np.exp(-al*sy))/(6*al*eta)
    print(f"   u_r={ur:2d}: tabulated hw {hw} um needs mean speed {ubar:.2f} m/s = {ubar/ur:.3f} u_r")

print("C9  Roelands (E5 4.193/4.194) against the Somentor 31 table at 40 C (E6 Table 2.1)")
eta0, alpha, pr = 1.409e-3, 10.40e-9, 196.2e6
z = pr*alpha/(np.log(eta0) + 9.67)
print(f"   z = {z:.3f}")
for p, meas in ((25e6, 1.905), (50e6, 2.481), (75e6, 3.157), (100e6, 3.985), (625e6, 2500.0), (945e6, 15000.0)):
    roe = eta0*np.exp((np.log(eta0)+9.67)*((1+p/pr)**z - 1))
    bar = eta0*np.exp(alpha*p)
    print(f"   p={p/1e6:6.0f} MPa: Roelands {roe*1e3:10.3f} mPa s   Barus {bar*1e3:10.3f}   measured {meas} mPa s")
print("   temperature index S0 from 40 -> 100 C at p=0:",
      np.log((np.log(0.632e-3)+9.67)/(np.log(1.409e-3)+9.67))/np.log((40+135)/(100+135)))
print("   beta = -dln(eta)/dT, 40-60 C:", np.log(1.409/1.033)/20, " 60-100 C:", np.log(1.033/0.632)/40)
