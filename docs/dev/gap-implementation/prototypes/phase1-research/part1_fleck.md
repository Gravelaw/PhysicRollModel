## 1. Foil bite: Fleck, Johnson, Mear & Zhang (1992) — complete governing set

Status: **found in full** for the 1992 paper [E1 FT: all 13 pages of the scan read as page images,
equations (20), (30)-(32), (36) and Appendix 3 re-read on enlarged crops]. Every equation below is
transcribed from E1 with the paper's own numbers. Plain-text notation; `Int` is an integral over
the whole arc of contact `x' in [-a0, a2]` unless limits are given.

### 1.1 Symbols (the paper's NOTATION list, p.119)

| symbol | meaning | unit / scaling |
|---|---|---|
| `x`, `z` | Cartesian coordinates; `x` along rolling, origin on the **line of centres of the rolls**, entry at `x = -a0 < 0`, exit at `x = a2 > 0`; `z` height above the centre-plane of the strip | m |
| `a` | contact width from the centre-line of the rolls to the entry (`a0`) or exit (`a2`) location | m |
| `b(x)` | **semi-thickness** of the strip; `h = 2b`. `b0` entry, `b1` in the central no-slip zone, `b2` exit | m |
| `p(x)`, `q(x)` | normal pressure (compressive positive) and shear stress between roll and strip. `q` is the traction **on the strip**, positive in the rolling direction (follows from eq. (1) and (9a)) | Pa |
| `sigma_x` | longitudinal direct stress in the strip, **tensile positive**, averaged through the thickness (overbar dropped after eq. (3a)); `sigma_0` at entry, `sigma_2` at exit | Pa |
| `Y_s` | plane strain yield stress of the strip (`= 2k`) | Pa |
| `alpha` | `q/abs(q) = +-1`; `+1` where the strip moves slower than the rolls (backward slip), `-1` where faster | - |
| `mu` | Coulomb friction coefficient | - |
| `m` | friction factor `2q/Y_s` | - |
| `R` | radius of the undeformed work roll | m |
| `E*` | plane strain modulus `E/(1 - nu^2)`; `E_R*` roll, `E_s*` strip; `nu_R`, `nu_s` Poisson ratios | Pa |
| `u`, `v` | tangential and normal displacement of the roll surface; `v` positive **into the roll** (it increases `b`, eq. (6)) | m |
| `eps` | tensile strain in `x`; `eps_s = eps_s^e + eps_s^p` strip (elastic + plastic), `eps_R` roll surface | - |
| `V_s`, `V_R` | entry speed of the (unstrained) strip, peripheral speed of the undeformed roll | m/s |
| `xi` | creep ratio `(V_s - V_R)/V_R` (also a local coordinate in Appendix 3) | - |
| `J(x)` | Cauchy integral of the traction, `Int q(x')/(x - x') dx'` | Pa |
| `W` | roll load per unit width | N/m |
| `Q` | roll torque per work roll, per unit width | N |
| `r` | overall reduction `(b0 - b2)/b0` | - |
| `c` | semi-length of an overlapping triangular element = node spacing | m |
| `C_ij, D_ij` | influence matrices for the normal displacement `v` of the rolls (from `q` and from `p`) | m/Pa |
| `C'_ij, D'_ij` | influence matrices for the displacement gradient `du/dx` (from `q` and from `p`) | 1/Pa |
| `l` | contact length of the strip in the nip | m |
| subscripts | `A`-`F` zones; `S` strip; `R` roll; `c` critical; `p` peak | |

Non-dimensional groups, eq. (21) and NOTATION:

    X = x*E_R*/(R*Y_s)     B = b*E_R*^2/(R*Y_s^2)     P = p/Y_s
    U = mu*E_R*/Y_s        Sigma_0 = sigma_0/Y_s       Sigma_2 = sigma_2/Y_s          (21)
    W_bar = W*E_R*/(R*Y_s^2)       Q_bar = Q*E_R*^2/(R^2*Y_s^3)

`H_bar` (used in the captions of Figs 6 and 7, "2 <= H_bar <= 300") is not defined in E1; it is the
group of the 1987 paper, `H_bar = 2*b0*E_R*/(mu*R*Y_s)` [E2 FT p.513], i.e. `H_bar = 2*B0/U`
[derived: `2*B0/U = 2*b0*E_R*^2/(R*Y_s^2) * Y_s/(mu*E_R*)`].

### 1.2 Strip (section 3.1)

    b(x)*d(sigma_x)/dx + {sigma_x(x) + p(x)}*db/dx + q(x) = 0                          (1)

Prandtl stress field for a strip thin compared with the bite length:

    sigma_z(z) = -p                                                                    (2a)
    tau_zx(z)  = q*z/b                                                                 (2b)
    (sigma_x - sigma_z)^2 + 4*tau_zx^2 = Y_s^2                                         (2c)

giving `sigma_x(z) + p = Y_s*sqrt{1 - (2*q*z/(b*Y_s))^2}`; averaged through the thickness

    sigma_x_mean + p = Y_s*I(m),   I(m) = {asin(m) + m*sqrt(1 - m^2)}/(2*m),  m = 2q/Y_s   (3)

`I(m)` falls from 1.0 to `pi/4` as `m` goes from 0 to 1.0. "Provided the frictional traction q is
appreciably less than the yield stress in shear (Y_s/2)":

    sigma_x(x) + p(x) ~= Y_s                                                           (3a)

(used wherever the strip undergoes plastic reduction; from here `sigma_x` is the thickness
average). The concluding discussion adds: `I(m)` exceeds 0.9 provided `m (= 2*mu*p/Y_s) < 0.7`,
which with `mu = 0.03` is "satisfied (just)" for all the plastic reduction zones of Fig. 1 [p.128].

Longitudinal strain of the strip. "Reduction in thickness of the strip due to *elastic*
compression is neglected in comparison with the elastic compression of the rolls. Longitudinal
elastic strain in the strip is important in its influence on slip."

    eps_s = eps_s^e + eps_s^p = (1/E_s*)*{sigma_x(x) + (nu_s/(1 - nu_s))*p(x)} + eps_s^p    (4)

### 1.3 Rolls (section 3.2)

Undeformed profile (contact length small against `R`), `-a0` the entry point, "taken as a datum
for normal displacements":

    z(x) = b0 - (a0^2 - x^2)/(2R)                                                      (5)
    b(x) = b0 - (a0^2 - x^2)/(2R) + v(x) - v(-a0)                                      (6)

"The effect of the frictional traction q(x) on normal displacement is negligible", whereupon

    v(x) - v(-a0) = (2/(pi*E_R*)) * Int p(x') ln|(a0 + x')/(x - x')| dx'               (7)
    b(x) = b0 - (a0^2 - x^2)/(2R) + (2/(pi*E_R*)) * Int p(x') ln|(a0 + x')/(x - x')| dx'   (8)

Note the datum: the kernel vanishes at `x = -a0`, so `b(-a0) = b0` identically. The mill
"unloaded gap" does not appear; `a0` is the free parameter and `r` follows.

### 1.4 Interface (section 3.3)

    q(x) = alpha*mu*p(x)                    (slip)                                     (9a)
    |q(x)| <= mu*p(x)                       (no slip)                                  (9b)

No slip: strip and roll surface move with the same velocity, which "demands that the difference
in longitudinal strain between the rolls and the strip is constant":

    eps_R(x) - eps_s(x) = (V_s - V_R)/V_R  ==  constant  xi                            (10)

Longitudinal strain in the surface of the rolls:

    eps_R(x) = du_x/dx = -((1 - 2*nu_R)/(1 - nu_R))*(1/E_R*)*p(x)
                         - (2/(pi*E_R*)) * Int q(x')/(x - x') dx'                      (11)

Substituting (4) and (11) into (10), the **condition of no-slip**:

    sigma_x(x) + {nu_s/(1 - nu_s) + ((1 - 2*nu_R)/(1 - nu_R))*(E_s*/E_R*)}*p(x)
        + (2/pi)*(E_s*/E_R*)*J(x) + E_s**eps_s^p = -E_s**xi                            (12)

    J(x) = Int_{-a0}^{a2} q(x')/(x - x') dx'

### 1.5 Assembly per zone (section 3.4)

**3.4.1 Elastic slip (elastic zones at entry and exit).** Transverse elastic compression of the
strip neglected, so `db/dx = 0` and (1) reduces to

    b*d(sigma_x)/dx + alpha*mu*p(x) = 0,      b = b0 at entry, b2 at exit              (13)

**3.4.2 Elastic no-slip (neutral zone).** Plastic strain constant, `eps_s^p = (b0 - b1)/b0`
[as printed; this is a signed thinning strain taken positive], so (12) becomes

    sigma_x(x) + {nu_s/(1 - nu_s) + ((1 - 2*nu_R)/(1 - nu_R))*(E_s*/E_R*)}*p(x)
        + (2/pi)*(E_s*/E_R*)*J(x) = constant (C)                                       (14)

"for practical values of mu, q(x) is always much smaller than p(x) and, for aluminium strip,
E_s* ~= (1/3) E_R*, so that the term in J(x) in equation (14) is relatively small. Thus"

    sigma_x(x) + 0.62*p(x) ~= C                                                        (14a)

**3.4.3 Plastic reduction** (slip, yield (3a) in (1)):

    -b(x)*dp/dx + Y_s*db/dx + alpha*mu*p = 0                                           (15)

**3.4.4 Plastic no-slip (contained plastic).** "If the condition for elastic no-slip, given by
equation (14), cannot be satisfied without violating the yield condition (3a), then some plastic
deformation must occur according to equation (12). However, the elastic strains in the rolls,
given by equation (11), are small, which demands that any plastic strain in the strip eps_s^p must
be *constant to an elastic order of magnitude* to satisfy the no-slip condition equation (14).
Thus variations in thickness of the strip due to contained plastic deformation may be ignored
compared with the elastic compression of the rolls. **For the purpose of calculating the roll
pressure p(x), it may be assumed that b(x) = constant = b1 in the neutral zone.**" Then

    b1*d(sigma_x)/dx + q(x) = -b1*dp/dx + q(x) = 0                                     (16)

Closing paragraph of 3.4, quoted because it decides what (10)-(14) are for: "The roll deformation
equation (8) applies throughout the bite. It must be solved simultaneously with equation (15) in
the plastic reduction zones. In the elastic zone at entry, the neutral zone and the elastic zone
at exit the thickness of the strip is constant at b0, b1 and b2 respectively. Given the entry
position a0, initial strip thickness b0, entry and exit tensions sigma_0 and sigma_2, we determine
the pressure distribution p(x) and the deformation b(x) throughout the bite. **The subdivision of
the neutral zone into elastic and contained plastic zones, leading to the determination of the
stress in the strip sigma_x(x) and the frictional traction q(x) throughout the bite, is found by
a subsequent calculation using equations (14) and (16).**"

### 1.6 Zone structure (section 2, Fig. 3, Appendix 2)

Section 2 lists five zones; Fig. 3 and Appendix 2 letter them A-F:

| zone | state | slip | thickness | equations |
|---|---|---|---|---|
| (elastic entry) | elastic | backward slip | `b0` | (13); "very small and can be neglected" for practical reductions |
| A | plastic reduction | backward slip, `alpha = +1` | `2*b0 -> 2*b1` | (8), (15) |
| B | contained plastic | no slip | `b1` | (8) with `b = b1`; `q` from (16); pressure rising |
| C | elastic unloading (regime III only) | no slip | `b1` | (8) with `b = b1`; `sigma_x` from (14a); `q` from (16)/(36) |
| D | contained plastic again (regime III) | no slip | `b1` | as B |
| E | plastic reduction | **backward** slip, `alpha = +1` | starts at `b1` | (8), (15); a short zone between the no-slip zone and the pressure peak |
| F | plastic reduction | forward slip, `alpha = -1` | `-> 2*b2` | (8), (15) |
| (elastic exit) | elastic | forward slip | `b2` | (13); neglected |

- **Regime I** (thick strip): zones A and F only, slip everywhere, one neutral section at the
  pressure peak (Jortner regime). Requires `db/dx <= 0` throughout the nip.
- **Regime II**: A, B, E, F. Pressure rises monotonically from entry to the pressure spike.
- **Regime III**: A, B, C, D, E, F. Local Hertzian-type pressure maximum near `x = 0`, the strip
  unloads elastically in C; a sharp peak E/F close to the downstream end of the neutral zone.
- The peak "coinciding with a reversal of slip and friction, persists in regimes II and III and is
  located near the downstream end of the neutral zone" [p.124]. The neutral *point* (slip
  reversal) is the E/F boundary, not the end of the no-slip zone.

### 1.7 Numerical implementation (section 4) and boundary conditions

Pressure and traction piecewise linear: `N` (typically 100) overlapping triangular elements,
`N + 1` nodes equally spaced a distance `c` apart; unknowns `p_j`, `q_j`, `b_j` at the nodes.

    v_i = C_ij*q_j + D_ij*p_j                                                          (17)
    (du/dx)_i = C'_ij*q_j + D'_ij*p_j                                                  (18)

(summation over the `N + 1` nodes). "The problem is greatly simplified by neglecting the effect of
frictional traction q upon the normal displacement v, that is by putting C_ij = 0 in equation
(17). This has the effect of decoupling equation (8) for the pressure from equation (11) for the
frictional traction."

    b_i = b0 - (a0^2 - x_i^2)/(2R) + v_i - v(-a0),   v_i = D_ij*p_j,  v(-a0) = D_0j*p_j   (19)

Integration of (15) over one element "assuming a piecewise linear variation of both pressure p(x)
and the inverse of the thickness 1/b(x)", **as printed**:

    p_i = [ Y_s*ln(b_i/b_{i-1}) + p_{i-1}*{1 - alpha*mu*c*(1/(3*b_{i-1}) + 1/(6*b_i))} ]
          / [ 1 + alpha*mu*c*(1/(3*b_{i-1}) + 1/(6*b_i)) ]                             (20)

> **Transcription flag on (20).** Integrating (15), `dp/dx = (Y_s*b' + alpha*mu*p)/b`, from
> `x_{i-1}` to `x_i = x_{i-1} + c` with `p` and `1/b` linear gives [derived]
> `p_i*{1 - alpha*mu*c*(1/(6*b_{i-1}) + 1/(3*b_i))} = Y_s*ln(b_i/b_{i-1}) + p_{i-1}*{1 + alpha*mu*c*(1/(3*b_{i-1}) + 1/(6*b_i))}`.
> The printed (20) has the opposite sign on both friction terms and the same weight pair in
> numerator and denominator. With `b` constant the printed form gives a pressure that *falls*
> in the direction of increasing `x` for `alpha = +1`, against (15) and against Fig. 3. Either
> the printed equation carries a sign error or it is meant for a march against `x`; use the
> derived form (checked numerically, section 1.12, check C2).

Boundary conditions with the elastic end zones neglected ("for practical reductions (r > 10 per
cent) the *elastic* zones at entry and exit are very short and can be neglected"):

    entry:  b(-a0) = b0   and   p(-a0) = Y_s - sigma_0
    exit:   (db/dx)_2 = 0 and   p(x_2) = Y_s - sigma_2

So the published pressure does **not** start and end at zero: it steps to `Y_s - sigma` at both
ends. "To obtain a solution, values of a0, b0, sigma_0 and sigma_2 are selected. The strategy
consists of iterating the pressure distribution. At each stage the deformed thickness of the strip
b_i is given in terms of the current pressure by equation (19); equation (20) is then used to
update the pressure."

Influence coefficients (Appendix 1), `k = i - j`, **as printed**:

    D_ij  = (c/(2*pi*E_R*)) * {(k+1)^2*ln(k+1)^2 + (k-1)^2*ln(k-1)^2 - 2*k^2*ln k^2} + constant   (30)
    C'_ij = -(1/(pi*E_R*)) * {(k+1)*ln((k+1)/k)^2 + (k-1)*ln((k-1)/k)^2}                         (31)
    D'_ij = -(1 - 2*nu_R)/((1 - nu_R)*E_R*)   for j = i;    = 0 for j != i                        (32)

> **Transcription flag on (30).** As printed, `D_ij` grows with distance from the loaded node
> (`k = 0`: 0; `k = 1`: `4 ln 4 > 0`), i.e. it is the displacement *out of* the roll. Equation (7)
> and (19) need `v` positive *into* the roll, largest under the load: `v_i = -(2/(pi*E_R*)) Int p ln|x_i - x'| dx' + const`.
> So (30) must be used with a minus sign, `D_ij = -(c/(2*pi*E_R*))*{...} + constant` [derived;
> check C1 below confirms it by quadrature]. With that sign it is identical to the kernel SPEC18
> derived: `-(2/(pi*E*))*d*kappa(n)`, `kappa(n) = {(n+1)^2 ln|n+1| - 2 n^2 ln|n| + (n-1)^2 ln|n-1|}/2`.
> The source cited for it is Johnson, Contact Mechanics, p.27 (triangular pressure element) and
> p.148 [E1 p.123; the book itself was not read, CIT].
> (31) was checked by quadrature against (11) and holds as printed (check C1).

### 1.8 Solution procedure (Appendix 2) and the matching conditions between zones

**Regime I.** Zones A and F. "The boundary x_AF and the exit location x_2 are chosen arbitrarily.
After converged distributions of pressure p(x) and strip thickness b(x) are obtained using
equations (19) and (20), the positions of the boundaries x_AF and x_2 are moved by a
Newton-Raphson procedure until the exit conditions sigma_x = sigma_2 and db/dx = 0 are satisfied
at x = x_2. The value of reduction r associated with the chosen values of a0 and b0 follows from
the exit thickness b2." After convergence

    (sigma_x)_i = Y_s - p_i                                                            (33)
    q_i = alpha*mu*p_i                                                                 (34)

"For a solution to exist in regime I, db/dx <= 0 throughout the nip."

**Regime II.** Zones A, B, E, F. "Fix a0 and b0, guess initial values for the boundaries x_AB,
x_BE, x_EF and a2, and assume an initial pressure distribution in the plastic reduction zones A, E
and F. Since the strip thickness is constant in the contained plastic zone B, equations (6) and
(17) give"

    (D_ij - D_(i-1)j)*p_j = (x_{i-1}^2 - x_i^2)/(2R)                                   (35)

"where j ranges over all nodes and i refers to nodes in the contained plastic zone. Equation (35)
is used to deduce the pressure in the contained plastic zone from the assumed pressure
distribution in the plastic reduction zones A, E and F. The strip thickness is then calculated
from equation (19) ... The pressure profile is updated in zones A, E and F by integrating the
equilibrium equation, and in zone B by equation (35), until a converged solution for p(x) and b(x)
is obtained. The boundaries x_AB, x_BE, x_EF and a2 are moved in order to satisfy the four
conditions:"

1. "Plastic reduction stops and hence `db/dx = 0` at `x_AB`. This is equivalent to the statement
   `dp/dx` is continuous at `x_AB`."
2. "Slip occurs at `x_BE` (`q = mu*p`). The shear stress q(x) is calculated at nodes in the
   contained plastic zone by equation (16) in finite difference form:"

       b1*(p_{i+1} - p_{i-1}) - q_i*(x_{i+1} - x_{i+1}) = 0      (no sum on i)        (36)

   [as printed; the second bracket is a misprint for `(x_{i+1} - x_{i-1})`, which is what (16),
   `q = b1*dp/dx`, gives by central differences: derived].
3. `p = Y_s - sigma_2` at `x = a2`.
4. "Plastic reduction stops and hence `db/dx = 0` at `x = a2`."

"Boundaries x_AB, x_BE, x_EF and a2 are moved by the Newton-Raphson method until the four
conditions are met at the three boundaries and the exit."

Count [derived]: four unknown positions, four conditions; pressure is continuous across every
boundary because zones A, E and F are integrated forward from the neighbouring value; thickness is
continuous because (8) holds everywhere. No separate condition is written for `x_EF`: it is the
position at which `alpha` switches from `+1` to `-1`, fixed together with the other three by
conditions 1-4.

**Regime III.** Case 1 (peak near exit higher than the Hertzian maximum near `x = 0`, Fig. 1(e))
is given, case 2 (lower, Fig. 1(f)) is omitted. "Assuming the strip thickness to be constant in
the central no-slip regime (comprising the contained plastic zones B and D and the elastic no-slip
zone C), **the positions of the boundaries x_BC and x_CD have no influence on the pressure
distribution p(x). Hence p(x) and boundaries x_AB, x_DE, x_EF and a2 are found in an identical
manner to that described for regime II.**" Then, as a post-processing step:

- `x_BC`: in zone B (pressure increasing) (12) needs a small positive contained plastic strain
  rate; B ends when that rate is zero; "neglecting the small term in J(x), equation (12) shows
  this to occur when `dp/dx = 0`, that is at the pressure maximum".
- Zone C: elastic unloading, `sigma_x` from (14a).
- `x_CD`: yield is reached again, "which by equation (14a) occurs when the pressure rises to its
  earlier maximum, that is `p(x_CD) = p(x_BC)`" [consistent: with `C = Y_s - 0.38*p_max` from
  yield at `x_BC`, `sigma_x + p = Y_s` gives `0.38*p = 0.38*p_max`: derived].
- Shear traction in C and D from (36).
- Case 2 (`p(x_EF) < p(x_BC)`): "Fortunately, **the pressure profile, strip thickness, rolling
  load and torque do not depend upon the detailed solution in the central no-slip zone, and there
  is no practical requirement to solve for the central zone.** Admissible solutions have been
  found, but are not detailed here."

The peak (section 4, last paragraph, and Appendix 3): "(i) for the pressure to be bounded and
continuous through the peak there should be no discontinuity in surface gradient db/dx through the
peak and (ii) a small region of plastic reduction must exist to the left of the peak, in which the
strip slips backwards relative to the rolls. The peaks in regime III ... are located at neutral
sections in the same way as the peaks in cases (a), (b), (c) and (d). The fact of no-slip at the
peak determines the value of the creep ratio xi in equation (12). With this value of xi, the
condition of no-slip is satisfied in the contained plastic zone by plastic flow eps_s^p of
appropriate magnitude."

### 1.9 Appendix 3: the pressure peak (Greenwood, Fleck & Johnson, "Modified Hertzian contacts", cited as to be published)

Peak at `x_p`; roll to the left of the peak, `xi_1 == (x_p - x) >= 0`, deformed to a perfect flat
(`v(xi_1) = 0`); to the right of the peak [printed "`xi == x_p - x >= 0`", which must read
`xi == x - x_p >= 0`: derived from Fig. 11] the pressure is that of plastic deformation, eq. (15).
Substitution, as printed,

    g(xi) = p(xi) - p0*{a^2 - (x_p + xi)^2}^(1/2),   a = 2*p0*R/E_R*,   p0 = pressure at x = 0

[as printed the second term has the dimension pressure times length; the Hertz pressure
`p0*sqrt(1 - x^2/a^2)` is meant: flagged, not corrected in the source]. From Barenblatt and
Schapery:

    p(xi_1) = K/sqrt(2*pi*xi_1) + g(0) + I*sqrt(xi_1) + O(xi_1)                        (37)
    v(xi)   = (2/(pi*E_R*))*K*sqrt(2*pi*xi) - (4/(3*E_R*))*I*xi^(3/2) + O(xi^2)        (38)
    K = -sqrt(2/pi) * Int_0^{xi_2} g(xi)/sqrt(xi) dxi                                  (39)
    I = (2/pi) * Int_0^{xi_2} (dg/dxi)*(1/sqrt(xi)) dxi                                (40)

Bounded, continuous pressure at `xi_1 = 0` if and only if `K = 0`, whereupon

    p(xi_1) = g(0) + I*sqrt(xi_1)                                                      (41)
    v(xi)   = -(4*I/(3*E_R*))*xi^(3/2)                                                 (42)

"the deformed profile is smooth, with no discontinuity of gradient at the peak. However, the
pressure gradient dp/dxi_1 given by equation (41) is singular at xi_1 = 0 (... I is a negative
quantity). The longitudinal stress sigma_x must also be continuous and of value p - Y_s at the
peak [as printed; (3a) gives Y_s - p], which leads to the conclusion that the pressure
distribution of equation (41) causes yield adjacent to the peak. In order to satisfy the yield
condition in this region it follows that there must be a small plastic reduction zone E to the
left of the peak in which the strip is slipping *backwards* relative to the rolls." "The condition
that K = 0 provides a relation which relates the position of the pressure peak x_p to the outlet
position x_2." This is the "perturbation solution" of Fig. 9.

Consequence for a solver [derived from (41) and (16)]: on the no-slip side the pressure approaches
the peak like `sqrt(xi_1)`, so `q = b1*dp/dx` grows without bound towards the peak and must pass
`mu*p` at a finite distance before it. A model that carries the no-slip zone up to the neutral
point therefore always violates (9b) at its downstream end.

### 1.10 Dimensionless form, load, torque, master curves, regime boundary (section 5)

    B(X) = B0 - (X0^2 - X^2)/2 + (2/pi) * Int_{X0}^{X2} P(X') ln|(X0 - X')/(X - X')| dX'   (22)
    -B(X)*dP/dX + dB/dX + alpha*U*P(X) = 0                                             (23)
    P(X), B(X) = f[B0, X0, U, Sigma_0, Sigma_2]                                        (24)

with `X0 = -a0*E_R*/(R*Y_s)`, `X2 = a2*E_R*/(R*Y_s)`.

    W = Int_{-a0}^{a2} p(x) dx;        W_bar == W*E_R*/(R*Y_s^2) = Int_{X0}^{X2} P(X) dX       (25)
    Q = Int_{-a0}^{a2} p(x)*x dx + (sigma_0*b0 - sigma_2*b2)*R
    Q_bar == Q*E_R*^2/(R^2*Y_s^3) = Int_{X0}^{X2} P(X)*X dX + B0*Sigma_0 - B2*Sigma_2          (26)
    r = (b0 - b2)/b0 = (B0 - B2)/B0                                                    (27)
    W_bar, Q_bar = f[B0, U, r, Sigma_0, Sigma_2]                                       (28)

[Sign note, derived: with `x` positive towards the exit the driving torque is `-Int p*x dx`; the
paper prints the magnitude convention, torque positive when the centre of pressure lies on the
entry side. `Q` is per work roll; the tension term uses the semi-thickness. The 1987 paper prints the signed form, `Q = Int -p(x)*x dx` (its eq. (10)).]

Master curves (multi-variable regression, Fig. 6, "for 10 % <= r <= 50 %, 15 <= U <= 45 and
2 <= H_bar <= 300"): `W_bar*U^-0.70*r^-0.70` and `Q_bar*U^-1.34*r^-1.62` against
`B0*U^-1.24*r^-0.50`. Boundary between regimes I and II:

    B0*U^-1.24*r^-0.50 ~= 6
    h_0c/R = 2*b_0c/R ~= 12 * r^0.5 * mu^1.24 * (Y_s/E_R*)^0.76                        (29)

`B0*U^-1.24*r^-0.5` correlates with the nip aspect ratio `2*b0/(mu*l)` (Fig. 7), `l` the contact
length. Fig. 4 and 5: `W_bar` and `Q_bar` against `B0` for `r` = 10, 30, 50 % at `U = 30`, with
the curves of Fleck & Johnson (1987), Bland & Ford and Johnson & Bentall (`r = 0`).

### 1.11 Reference cases with all inputs

**Fig. 9 (the benchmark, p.128).** Caption, verbatim: "Comparison of full numerical solution,
perturbation solution and Fleck and Johnson (6) solution, for the case R = 89 mm, b0 = 0.01 mm,
r = 25%, Y_s = 230 MPa, E_R* = 230 GPa, E_s* = 80 GPa, mu = 0.03, sigma_0 = sigma_2 = 0,
B0 = 112. The full numerical solution gives W_bar = 118, the perturbation solution gives
W_bar = 120 and the Fleck and Johnson (6) solution gives W_bar = 62".

| input | value | derived |
|---|---|---|
| `R` | 89 mm | |
| `b0` (semi-thickness) | 0.01 mm, entry gauge 20 um | `B0 = b0*E_R*^2/(R*Y_s^2) = 112.4` (caption: 112) |
| `r` | 25 %, exit gauge 15 um | `B2 = 84.3` |
| `Y_s` | 230 MPa (plane strain), no hardening | |
| `E_R*` | 230 GPa | `Y_s/E_R* = 1.0e-3`; `U = mu*E_R*/Y_s = 30` |
| `E_s*` | 80 GPa | enters only (12)/(14), i.e. `sigma_x` and `q` inside the neutral zone; **not** the pressure, the shape, `W` or `Q` (sections 1.5, 1.8) |
| `mu` | 0.03 | |
| `sigma_0`, `sigma_2` | 0 | end pressures `p = Y_s` |
| `nu_R`, `nu_s` | not stated | 0.62 in (14a) is reproduced with `nu_s = nu_R = 0.3`, `E_s*/E_R* = 1/3` (check C3) |
| result | `W_bar = 118` (full numerical), 120 (perturbation), 62 (Fleck-Johnson mattress) | `W = 118*R*Y_s^2/E_R* = 2.415 MN/m`; master-curve abscissa `B0*U^-1.24*r^-0.5 = 3.31` (below 6: regimes II/III) |

Read by eye from the enlarged Fig. 9 (full numerical curve; reading error about +-0.03 mm and
+-0.2 `Y_s`): entry at `x ~ -1.18 mm` with `p/Y_s ~ 1`; `p/Y_s` about 4.6 to 5 at `x ~ -0.6 mm`; a slowly
rising plateau reaching about 6.2 near `x ~ 0.25 mm` (no clear interior maximum is visible, so the
case is at the regime II/III border by the figure); sharp peak of about 7.7 (full numerical) and
about 8.5 (perturbation) at `x ~ +0.41 mm`; exit at `x ~ +0.95 mm`. Contact length about 2.1 mm,
70 % of it no-slip. The exit hill length agrees with (15) at constant thickness:
`ln(7.7)*b2/mu = 0.51 mm` against 0.54 mm read [derived]. A trapezoid over these points gives
`W_bar` about 105 [derived, by eye; 11 % below 118, inside the reading error of a small figure].

**Fig. 1 / Fig. 3 / Fig. 4 series.** `R = 89 mm`, `mu = 0.03`, `Y_s = 230 MPa`,
`sigma_0 = sigma_2 = 0`, `E_R* = 3*E_s* = 230 GPa` [Fig. 1 caption; i.e. `E_s*` = 76.7 GPa here,
80 GPa in Fig. 9], `r = 50 %`: entry gauges `h0 = 2*b0` = 0.140, 0.060, 0.048, 0.030, 0.020,
0.013 mm (cases a-f). (a), (b) regime I; (c), (d) regime II; (e), (f) regime III. Peak pressures
by eye from Fig. 1: about 2.5, 4.5, 6, 8.5, 12, 16 `Y_s`; contact from about -2.7 to +1.6 mm in
case (f). Fig. 3: regime I `h0 = 0.060 mm, r = 50 %`; regime II `h0 = 0.020 mm, r = 10 %`;
regime III `h0 = 0.020 mm, r = 50 %`.

**Fig. 8 (mill point).** `b0 = 0.0365 mm`, `Y_s = 230 MPa`, `r = 57 %`, `sigma_0 = 0.107 Y_s`,
`sigma_2 = 0.132 Y_s`, "1100 aluminium alloy on third pass" (mill data of Davy-McKee). Measured
`W_bar = 58` gives `mu = 0.026` (`U = 26`); predicted torque `Q_bar = 370`, measured 480 (strain
gauges in the drive shafts, within 10 %). Roll radius, `E_R*`, speed and width are not stated.

### 1.12 What accounts for 92.9 against 118 on Fig. 9

What the source establishes (E1, FT):

1. **It is not equations (10)-(14).** The published `p(x)`, `b(x)`, `W` and `Q` are computed from
   (8), (15) and `b = b1` alone. (10)-(14) are applied afterwards to split the neutral zone and to
   obtain `sigma_x` and `q` there, and the paper says in so many words that load and torque "do
   not depend upon the detailed solution in the central no-slip zone" (quotations in 1.5 and 1.8).
   The reading recorded in SPEC18 section 0.1, finding 2, and the allocation of the missing load
   to gap row BT-G15 are therefore contradicted by the source.
2. **`E_s*` = 80 GPa is not a thickness compliance in the published model.** Elastic thickness
   change of the strip is neglected outright (1.2). SPEC18 finding 3 ("The published case carries
   `E_s*` = 80 GPa") cannot be used to justify the spring `c_s = h_ref/E_s*`; the published
   model is the limit `c_s = 0` with the end conditions of 1.7.
3. **The published structure has one zone the prototype lacks: zone E**, plastic reduction with
   backward slip between the downstream end of the no-slip zone and the pressure peak. The no-slip
   zone ends where the shear demand `b1*dp/dx` reaches `mu*p` (condition 2 of 1.8), *before* the
   neutral point; from there to the peak the pressure climbs a friction hill at `alpha = +1`, and
   the exit hill starts from that higher peak. The prototype joins the no-slip zone directly to
   the forward-slip zone ("x_b follows from pressure continuity"; "the pressure at the downstream
   end of the no-slip zone sits on the exit friction hill"), which is the model of 1.8 with
   `x_BE = x_EF`. Its own symptom, a no-slip zone that needs 1.44 times the friction limit at its
   downstream end (finding 6), is what Appendix 3 predicts for that structure (1.9, last
   paragraph).
4. **End conditions differ.** Published: `p = Y_s - sigma` at both ends, no elastic end zones.
   Prototype: end contact zones in which the pressure rises from zero under friction, made
   possible by the thickness spring.

What the source does not establish: the size of each effect. It gives no solution without zone E.
This was therefore tested numerically (check C4, section 7; own re-implementation of (22), (23)
and the conditions of 1.8 in numpy, `s24/scripts/fleck_fig9*.py`; all of it `[derived]`):

5. **Zone E does not change the load.** With and without zone E the load differs by less than
   0.3 % on every grid tried (for example 98.66 against 98.55). What zone E changes is
   admissibility: without it the shear demand at the downstream end of the flat zone is 1.9 to
   5.6 times `mu*p` (growing with grid refinement, as Appendix 3 predicts); with it the demand is
   at most `mu*p` everywhere in the flat zone (maximum interior ratio 0.56 to 0.80).
6. **The load is set by how the two ends of the bite are closed, and the printed model does not
   fix that.** With the elastic end zones neglected the pressure steps from zero to
   `Y_s - sigma` at entry and exit. A pressure step on a half-space gives a logarithmically
   infinite surface slope at the step, so "`db/dx = 0` at exit" has no grid-independent meaning.
   Results on Fig. 9, all with residual norm below 1e-9:

   | closure of the exit (and entry) | elements | `W_bar` | contact length | peak `p/Y_s` |
   |---|---|---|---|---|
   | step; condition 4 as a difference over the last element (17.5 / 8.8 / 4.4 um long) | 122 / 244 / 488 | 98.7 / 108.8 / 121.9 | 2.07 / 2.19 / 2.33 mm | 7.65 / 7.79 / 7.96 |
   | step; last element held at 40 um | 244 | 91.5 | 1.98 mm | 7.53 |
   | step; last element held at 20 um | 122 / 244 / 488 | 97.09 / 96.98 / 96.95 | 2.05 mm | 7.62 |
   | step; last element held at 10 um | 244 / 488 | 106.70 / 106.66 | 2.16 mm | 7.76 |
   | step; last element held at 5 um | 488 | 119.5 | 2.30 mm | 7.93 |
   | step; last element held at 2.5 um | 488 | 134.8 | 2.46 mm | 8.10 |
   | pressure ramps to zero over 21 um outside both ends ("overlapping triangles", analytic nodal slope) | 200 / 400 | 88.04 / 88.00 | 1.93 mm | 7.47 |
   | ramp 10 um | 400 | 101.9 | 2.10 mm | 7.70 |
   | ramp 5 um | 400 | 116.6 | 2.27 mm | 7.90 |
   | ramp 2.5 um | 400 | 133.2 | 2.44 mm | 8.08 |

   For a fixed end length the interior is grid-converged to 0.1 %; the end length alone moves
   `W_bar` from 88 to 135, about 10 to 15 per halving, without a limit. The entry element has no
   measurable influence; the exit condition carries the effect.
7. **The published 118 is reproduced only with an end length of about 5 um, a quarter of the
   element size the paper states** (`N` typically 100 over about 2.1 mm is 21 um, which gives 88
   to 97 here). And the *plotted* Fig. 9 curve is matched by the 10 um ramp solution, not by the
   5 um one:

   | landmark | Fig. 9, read by eye | ramp 21 um | ramp 10 um | ramp 5 um |
   |---|---|---|---|---|
   | entry | -1.18 mm | -1.112 | -1.189 | -1.266 |
   | `p/Y_s` at -0.6 mm | about 4.6 | 4.15 | 4.65 | 5.13 |
   | `p/Y_s` at 0 | about 6.1 | 5.70 | 6.00 | 6.33 |
   | peak position | +0.41 mm | +0.300 | +0.388 | +0.473 |
   | peak height (full numerical) | about 7.7 | 7.47 | 7.70 | 7.90 |
   | exit | +0.95 mm | +0.821 | +0.915 | +1.004 |
   | `W_bar` | caption 118; trapezoid by eye about 105 | 88.0 | 101.9 | 116.6 |
   | forward slip (neutral thickness over exit thickness, minus 1) | not given | 0.199 | 0.188 | 0.175 |

   A third, independent number points the same way: Sutcliffe's thesis used the Mear and Zhang
   pressure distribution for this same case (R 88.9 mm, 20 um, 25 %, 230 MPa, mu 0.03) and gives
   the contact length as `b/R = 0.0241`, i.e. 2.14 mm [E6 FT, thesis p.54]; in the family above
   2.14 mm corresponds to `W_bar` about 105. A full Hertz ellipse of that length carries
   `(pi/4)*(a*E_R*/(R*Y_s))^2 = 114` [derived]; the foil profile lies below the ellipse over both
   reduction zones and above it only at the narrow peak.

Reading of these results (stated as a finding of this check, not of the source): the prototype's
0.79 is the difference between two closures of the bite ends, not a missing piece of physics in
its interior. Its 92.9 sits inside the range of the printed model itself (88 to 135), at an
effective end length of about 30 um, and it is 0.88 to 0.91 of what the published curve and the
independent contact length support (102 to 105). The caption value 118 is not consistent, by
about 13 %, with the curve printed above it, unless the by-eye reading of a small figure is off by
that much. What a model needs in order to be well posed here is a physical end closure: the
elastic exit and entry zones (eq. (13) with a constant thickness, or a thickness compliance of
the strip as in the prototype), because that is what sets the length over which the pressure
falls from `Y_s` to zero. The paper's statement that these zones "are very short and can be
neglected" is true for their length and false for their influence on the load.

Not done here: a solution with the elastic end zones of (13) at rigid thickness (the count of
conditions at the entry junction was not resolved in the time available); regime III
post-processing with (14a).

### 1.13 Fleck & Johnson (1987), what was read [E2 FT, pp.510-514 only]

- Strip equilibrium `b*d(sigma_x)/dx + (sigma_x - sigma_z)*db/dx + q = 0` (2), with
  `sigma_z = -p`; yield `|sigma_z - sigma_x| = Y_s`, `Y_s` there "the uniaxial yield stress of
  the strip, in accordance with the Tresca yield criterion". "we ignore elastic and contained
  plastic compression of the strip in the z direction".
- Rolls: `p(x) = K_p*w(x)` (3), `q(x) = K_q*u(x)` (4); because a plain mattress gives a parabolic
  pressure ("This discrepancy was found to be significant") the relation was modified to
  `p(x) = p0*sqrt(1 - (x/a0)^2) - K_p*Delta_b` (3a), `K_p = 8*E_R*/(3*pi*a0)`, `K_q = (2/3)*K_p`.
- Slip: `v_S = V_S*(1 + eps_S)` (5), `v_R = V_R*(1 + eps_R)` (6),
  `s_dot/V_R = eps_S - eps_R + xi` (8) with `xi = (V_S - V_R)/V_R`; `q/(mu*p) = -s_dot/|s_dot|`
  in slip. Note the sign: (8) of 1987 and (10) of 1992 are the same statement with `s_dot = 0`.
- Seven zones A-G: A elastic slip (pressure `p0*sqrt(1 - (x/a0)^2)`, thickness `2*b0`), B plastic
  reduction, C contained plastic no-slip, D elastic unloading no-slip, E elastic slip, F plastic
  reduction with forward slip, G elastic exit (`p = p0*sqrt(1 - (x/a0)^2) - K_p*Delta_b2`,
  `2*Delta_b2 = r*2*b0`, ends where `p = 0`). Here the elastic end zones are kept, and the
  pressure does fall to zero at both ends.
- `W = Int p dx` (9); `Q = Int -p(x)*x dx` (10) [this is the signed form of 1992 eq. (26)].
- Groups: `W_bar = W*E_R*/(R*Y_s^2)`, `Q_bar = Q*E_R*^2/(R^2*Y_s^3)`,
  `H_bar = 2*b0*E_R*/(mu*R*Y_s)`, `U = mu*E_R*/Y_s` ("U = 30, typical for rolling aluminium
  alloy with steel rolls"); for the central zones `mu*E_s*/E_R*` (0.01) and `E_s*/E'` (0.683),
  `1/E' = (1 - 2*nu_R)*(1 + nu_R)/E_R + nu_s*(1 + nu_s)/E_s`. `E_s*/E'` is the coefficient of `p`
  in 1992 eq. (14) [derived: multiply (12) by `1/E_s*`]. At the onset of reduction
  `W_bar = 81*pi/H_bar^2` (label in Fig. 3).
- Appendices 1 and 2 (stresses per zone, method) were not read.
