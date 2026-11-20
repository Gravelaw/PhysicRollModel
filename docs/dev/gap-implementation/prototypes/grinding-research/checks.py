"""Consistency checks for research_roll_grinding.md. All outputs are [computed]."""
import numpy as np

E, nu = 210e9, 0.3
G = E / (2 * (1 + nu))

def bur_deflection(P, w, Lb, D, n=4001):
    """Simply supported round beam, span Lb (bearing centres), uniform load P over central width w.
    Returns bending+shear deflection at centre minus at strip edge (m). Euler-Bernoulli + shear (k=0.9)."""
    x = np.linspace(0, Lb, n)
    q = np.where(np.abs(x - Lb / 2) <= w / 2, P / w, 0.0)
    R = P / 2
    # shear force and moment by integration
    V = R - np.concatenate(([0], np.cumsum((q[1:] + q[:-1]) / 2 * np.diff(x))))
    M = np.concatenate(([0], np.cumsum((V[1:] + V[:-1]) / 2 * np.diff(x))))
    I = np.pi * D**4 / 64
    A = np.pi * D**2 / 4
    kappa = M / (E * I)
    th = np.concatenate(([0], np.cumsum((kappa[1:] + kappa[:-1]) / 2 * np.diff(x))))
    yb = np.concatenate(([0], np.cumsum((th[1:] + th[:-1]) / 2 * np.diff(x))))
    yb = yb - x / Lb * yb[-1]          # y(0)=y(Lb)=0 ; yb is "upward" for sagging sign -> take magnitude
    ys = np.concatenate(([0], np.cumsum((V[1:] + V[:-1]) / 2 * np.diff(x)))) / (0.9 * G * A)
    y = -yb + ys                         # downward deflection positive
    yc = np.interp(Lb / 2, x, y)
    ye = np.interp(Lb / 2 - w / 2, x, y)
    return yc - ye, yc

print("1) Backup-roll beam deflection, centre minus strip edge (one roll), and total centre sag")
for D in (0.75, 0.85, 0.95):
    for (P, w) in ((1.0e6, 1.2), (2.0e6, 1.2), (3.0e6, 1.2), (2.0e6, 1.6), (3.0e6, 1.6), (6.0e6, 1.6)):
        d, yc = bur_deflection(P, w, 2.9, D)
        print(f"  BUR D={D*1e3:.0f} mm, Lb=2.9 m, P={P/1e6:.0f} MN, w={w} m: centre-edge {d*1e6:6.1f} um, "
              f"gap opening 2x = {2*d*1e6:6.1f} um, total sag {yc*1e6:6.0f} um")

print("\n2) Cosine ('sine') crown curve against a parabola, drop from centre as a fraction of the total crown")
print("   assumed definition: drop(u) = C*(1-cos(a*u))/(1-cos(a)), u = 2x/L in [0,1], a = half angle")
for a_deg in (1, 30, 45, 60, 70, 80, 90):
    a = np.radians(a_deg)
    f = lambda u: (1 - np.cos(a * u)) / (1 - np.cos(a))
    print(f"   a={a_deg:2d} deg: drop at u=0.5: {f(0.5):.4f} (parabola 0.2500), at u=0.75: {f(0.75):.4f} (parabola 0.5625)")

print("\n3) Traverse feed per roll revolution (= feed-line pitch on the roll)")
cases = [("CN114632820A rough", 2200, 33), ("CN114632820A rough last", 1600, 33),
         ("CN114632820A finish first", 1050, 42), ("CN114632820A finish last", 900, 42),
         ("CN114632820A polish first", 850, 45), ("CN114632820A polish last", 400, 45),
         ("Xingtai foil roll finish lo", 160, 5), ("Xingtai foil roll finish hi", 200, 5),
         ("Xingtai foil roll final lo", 120, 5), ("Xingtai foil roll final hi", 160, 3)]
for name, v, n in cases:
    print(f"   {name:28s}: {v} mm/min / {n} r/min = {v/n:5.1f} mm/rev")
for wheel in (50, 75, 100):
    print(f"   wheel width {wheel} mm: 3/4 -> {0.75*wheel:.1f}, 1/2 -> {0.5*wheel:.1f}, 1/8 -> {wheel/8:.1f} mm/rev (Buffalo rule)")

print("\n4) Grinding chatter marks: count per roll circumference n = f_vib / f_roll; pitch on roll = pi*D/n")
for (nw, nr) in ((600, 50), (600, 5), (1200, 50), (1200, 5)):
    print(f"   wheel {nw} r/min, roll {nr} r/min (M84100B ranges): once-per-wheel-rev marks n = {nw/nr:.0f}")
for vs in (20, 25):
    for Dw in (0.5, 0.75):
        nw = vs / (np.pi * Dw) * 60
        for nr in (5,):
            n = nw / nr
            for Dr in (0.26, 0.28, 0.42):
                print(f"   wheel {vs} m/s on D={Dw*1e3:.0f} mm -> {nw:.0f} r/min; roll {nr} r/min: n={n:.0f}; "
                      f"pitch on D_roll={Dr*1e3:.0f} mm: {np.pi*Dr/n*1e3:.1f} mm")
print("   pitch from a machine resonance f: p = v_roll_surface/f. Roll 280 mm at 5..45 r/min, f = 50..300 Hz:")
for nr in (5, 45):
    v = np.pi * 0.28 * nr / 60
    for f in (50, 100, 300):
        print(f"     {nr} r/min ({v*1e3:.0f} mm/s), {f} Hz: p = {v/f*1e3:.2f} mm, n = {f/(nr/60):.0f}")

print("\n5) Thermal: diameter change alpha*D*dT, alpha = 11.7e-6 /K")
for D in (0.28, 0.42, 0.75, 0.85):
    print(f"   D={D*1e3:.0f} mm: {11.7e-6*D*1e6:.2f} um per K; dT for 1 um: {1/(11.7e-6*D*1e6):.2f} K; dT=1.2 K -> {11.7e-6*D*1.2e6:.1f} um")

print("\n6) Station spacing of a 21-station grinder report (stations start 50 mm from the barrel ends)")
for L in (1.5, 1.7, 1.9, 2.1, 2.35):
    print(f"   barrel {L} m: spacing {(L-0.1)/20*1e3:.0f} mm")

print("\n7) Ground crown against measured thermal crown")
for c in (40, 65, 80, 90, 120):
    print(f"   crown {c} um on diameter = {c/2:.0f} um on radius; both rolls alike close the gap centre by {c} um")
