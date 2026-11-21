
---

## 2. Mixed lubrication in the inlet

### 2.1 Asperity crushing under bulk strain: the fitted functions

Status: **found in full** as reproduced in two open theses [E5 FT sec. 4.7.1, equations read on
page images; E6 FT ch. 3]. The original papers (Wilson & Sheu 1988; Sutcliffe 1988; Korzekwa,
Dawson & Wilson 1992; Sutcliffe 1999) were not read [CIT].

Common variables. Roughness ridges along the rolling direction; `l` half spacing between
asperities; `A` real contact-area ratio; `p_a` pressure on the asperity tops, `p_l` (or `p_v`)
lubricant pressure in the valleys; `v_a` downward speed of the tops, `v_b` (or `v_v`) upward
speed of the valleys; `D_x^p` (or `eps_dot`) plastic strain rate of the bulk in the rolling
direction.

    E_p = D_x^p * l / (v_a + v_b)          non-dimensional plastic strain rate        [E5 (4.89)]
    H_a = (p_a - p_l) / tau_Y              non-dimensional effective hardness         [E5 (4.90)]
    W   = (v_a - v_v) / (c * eps_dot)      crushing rate, c = half indenter spacing   [E6 p.36]

`tau_Y` shear yield stress (E5 writes `tau_Y = sigma_Y/sqrt(3)`; E6 writes `k`, with `2k` the
plane strain yield stress; both mean that the plane strain yield stress is `2*tau_Y`). `E_p` and
`W` are reciprocals: `E = 1/W` [E8 EX, text of sec. 4.2.2; consistent with the two definitions].
The mean crushing pressure of E6 is `p_bar = A*(p_a - p_v)`, so `p_bar/2k = A*H_a/2` [derived from
E6 eq. 4.12 and the sentence on p.50].

**(a) Wilson & Sheu's fit** (upper-bound analysis, adjusted so that `H_a -> 2 + pi` at small `A`
and `E_p`):

    E_p = [1/(0.515 + 0.345*A - 0.860*A^2)] * [2/H_a - 1/(2.571 - A - A*ln(1 - A))]      [E5 (4.92)]
    2/H_a = f1*E_p + f2,   f1 = 0.515 + 0.345*A - 0.860*A^2,
                           f2 = 1/[2.571 - A - A*ln(1 - A)]                              [E5 (4.93)]

Without bulk deformation (`E_p = 0`), used by Metalub wherever the strip is elastic:

    H_a = 2*[2.571 - A - A*ln(1 - A)]                                                    [E5 (4.94)]
    dH_a/dA = -2 - 2*ln(1 - A) + 2*A/(1 - A)                                             [E5 (4.95)]

E5 notes that the reference does not explain how the fit was built, and that the upper-bound
results behind it are poor below about `A = 0.3`.

**(b) "Sutcliffe and Marsault"** (as given by Marsault's thesis, per E5):

    E_p = 4 / [H_a^2 * A^2 * (3.81 - 4.38*A)]                                            [E5 (4.96)]

E5: "How exactly this relation was deduced from Sutcliffe's equation is not explained by
Marsault"; it degenerates for `A -> 0` and for `A > 0.87` (bracket negative) and "is almost never
included in a rolling computation".

**(c) Sutcliffe's own fit** (thesis, read on the page image):

    W = 3.81*(p_bar/2k)^2 - 4.38*A,     with 0.05 <= W <= 2.5                            [E6 (3.20)]

"chosen to be most appropriate around A = 0.5, with p_bar/2k < 1.0, since this was the requirement
of the lubrication analysis of chapter 4". Theory values it summarises, `A = 0.5`: at
`p_bar/2k = 1`, `W = 1.47` (new velocity field) and 0.67 (Wilson & Sheu's field); at
`p_bar/2k = 0.6`, 0.16 and 0.32 [E6 p.38].

> **Reconciliation of (b) and (c).** With `p_bar/2k = A*H_a/2`, (c) reads
> `W = 3.81*A^2*H_a^2/4 - 4.38*A`, while (b) reads `W = 1/E_p = A^2*H_a^2*(3.81 - 4.38*A)/4`,
> i.e. `3.81*(p_bar/2k)^2 - 4.38*A*(p_bar/2k)^2`. They agree only where `p_bar/2k = 1`
> (`A = 0.5`: both 1.62). Elsewhere they differ strongly (`A = 0.5`, `p_bar/2k = 0.5`: (b) 0.405,
> (c) negative, clipped to 0.05; check C6). Either Marsault changed the second term or the thesis
> and the 1988 paper differ; the 1988 paper would decide and was not read. Neither form may be
> called "Sutcliffe (1988)" in code without that check; name the thesis equation or Marsault.

**(d) Sutcliffe's regression of the finite-element results of Korzekwa et al.** (the form used
by Sutcliffe & Montmitonnet [E4 EX] and by Le & Sutcliffe [E7]):

    E_p = 1 / [A*(1 - A)*(c1 + c2*A + c3*A^2)]                                           [E5 (4.97)]
    c1 =  5.1206*D -  4.5258*D^2 + 3.5599*D^3                                            [E5 (4.98)]
    c2 = -9.5761*D + 11.3854*D^2 - 8.6069*D^3,       D = H_a/2                           [E5 (4.99)]
    c3 =  8.3193*D - 11.7954*D^2 + 7.6475*D^3                                            [E5 (4.100)]

**Evolution of the contact with strain.**

- Metalub form: `dh/dx = -D_x^p*l/(v_s*E_p)` [E5 (4.122), "generalized asperity flattening
  equation"], `h` the distance between the non-updated mean lines of strip and roll, `v_s` strip
  speed; together with `A(h)` below.
- Sutcliffe's form for ridges of slope `theta` whose flanks keep their slope: transverse lay
  `da/dc = W/tan(theta)` [E6 (3.15)] and
  `dA/d(eps_x) = [1/(eps_x + 1)]*(W/tan(theta) - A)` [E6 (3.16)], `eps_x = (c - c0)/c0` nominal
  strain; as `p_bar -> 0`, `W -> 1` and `eps_x = 1/(1 - A*tan(theta)) - 1` [E6 (3.17)].
  Longitudinal lay (`c` constant): `dA/d(eps) = W/tan(theta)` [derived from (3.15) with
  `dc = 0`; E6 p.39 uses it in this way; E8 eq. (4.8), whose image is lost in the manuscript
  copy, is described in the same words]. Bulk yield with a loaded surface:
  `sigma_b/2k + p_bar/2k = 1` [E6 (3.18)].
- "The evolution of the contact area does not depend on bulk strain rate, per se" [E8 EX];
  the theoretical `W` is "in the range 1-8" for transverse roughness [E8 EX].

**Contact area and mean film from the height distribution** [E5 (4.6), (4.7), (4.13)-(4.22),
page images]. `R_q` combined r.m.s. roughness, `h` as above (may become negative), `h_t` mean
film thickness (distance between updated mean lines):

    A(h)   = Int_h^{z_max} f_Z(z) dz                (0 if h > z_max)                     (4.6)
    h_t(h) = Int_{z_min}^{h} (h - z)*f_Z(z) dz      (h if h > z_max)                     (4.7)

Triangular asperities: `A = 1/2 - h/(2*sqrt(3)*R_q)` for `h < sqrt(3)*R_q` (4.13);
`h_t = (sqrt(3)*R_q/4)*(1 + h/(sqrt(3)*R_q))^2` (4.15);
`h = sqrt(3)*R_q*(sqrt(4*h_t/(sqrt(3)*R_q)) - 1)` (4.16).

Christensen (quasi-Gaussian), `H = h/(3*R_q)`, `H_t = h_t/(3*R_q)`, for `H < 1`:

    A   = (1/32)*(16 - 35*H + 35*H^3 - 21*H^5 + 5*H^7)                                   (4.18)
    dA/dh = -(35/(96*R_q))*(1 - H^2)^3                                                   (4.19)
    h_t = (3*R_q/256)*(35 + 128*H + 140*H^2 - 70*H^4 + 28*H^6 - 5*H^8)                   (4.20)
    h   = 3*R_q*[-1 + 2*H_t^0.2235 + 0.5142*H_t^0.2222*(H_t - 1)]     (fitted inverse)   (4.21)

[checked: `A(0) = 1/2`, `A(-1) = 1`, `h_t(H = 1) = 3*R_q`, `h_t(H = -1) = 0`: derived.] The same
density is Sutcliffe's eq. 4.7: `f(h/d0) = (35/96)*(1 - ((h - delta)/(3*d0))^2)^3` for
`|h - delta|/d0 < 3`, `d0` initial combined r.m.s. roughness, `delta` separation of the centre
lines [E6 p.47, OCR text]. Mean valley film: `h_v = h_t/(1 - A)` [E5 (4.203)].

### 2.2 Flow factors for the averaged Reynolds equation

Status: **found in full** as curve fits by Marsault of the Patir-Cheng tables, and as the
Wilson-Marsault extension to large contact areas [E5 FT sec. 4.8.1.3, page images]. Originals
[CIT].

Averaged Reynolds equation, small contact area (`h` nominal film, `h_t` mean film, `v_s`, `v_r`
strip and roll speed, `eta` viscosity, `gamma` Peklenik parameter: ratio of the lengths at which
the autocorrelation falls to one half along `x` and along `y`; `gamma > 1` longitudinal lay):

    d/dx(phi_x*h^3/(12*eta)*dp_l/dx) + d/dy(phi_y*h^3/(12*eta)*dp_l/dy)
        = d/dx((v_s + v_r)/2*h_t) + d/dx((v_s - v_r)/2*R_q*phi_s) + dh_t/dt             (4.153)

steady, one-dimensional, integrated once (`Q` flow per width, fixed by `p_l = 0` at the outlet):

    dp_l/dx = [12*eta/(phi_x*h_t^3)] * [ (v_s + v_r)/2*h_t + (v_s - v_r)/2*R_q*phi_s - Q ]   (4.191)

Pressure flow factor, Gaussian surface, Patir & Cheng as fitted by Marsault:

    phi_x = 1 - C_x*exp(-r_x*h/R_q),   C_x = 0.89679 - 0.26591*ln(gamma),
                                       r_x = 0.43006 - 0.10828*gamma + 0.23821*gamma^2     gamma <= 1
    phi_x = 1 + C_x*(h/R_q)^(-1.5),    C_x = -0.10667 + 0.10750*gamma                      gamma > 1   (4.160)
    phi_y(gamma) = phi_x(1/gamma)                                                                      (4.161)

Shear flow factor (`R_q,s`, `R_q,r` strip and roll roughness, `gamma_s`, `gamma_r` their
pattern parameters):

    phi_s = (R_q,s^2/R_q^2)*Phi_s(h/R_q, gamma_s) - (1 - R_q,s^2/R_q^2)*Phi_s(h/R_q, gamma_r)   (4.163)
    Phi_s = A_s*exp(-0.25*h/R_q),   A_s = 1.0766 - 0.37758*ln(gamma),   for h/R_q > 5           (4.164)

Longitudinal triangular ridges (Wilson & Chang): `phi_x = 1 + 3*R_q^2/h^2` without contact
(4.157), `phi_x = 2*sqrt(3)*R_q/h_t` with contact (4.168, defined on `h_t^3`), `phi_s = 0`.
The same factor `(1 + 3*d_v^2/h_v^2)` multiplies `h_v^3` in Sutcliffe's valley equation [E6 (4.5)]
and `(1 + 3*sigma_t^2/h_t^2)` in Le & Sutcliffe [E7 eq. 1]: three sources agree.

Large contact areas, Christensen surface, Wilson & Marsault (`h` replaced by `h_t` in the
Reynolds equation, eq. 4.165), for `h_t/R_q < 3`:

    phi_x*h_t^3 = a2*R_q*(h_t - h_tc)^2 + a3*(h_t - h_tc)^3                                (4.170)
    h_tc = 3*R_q*[1 - 1/(0.47476/gamma + 1)^0.25007]        (percolation threshold)        (4.171)
    a2 = 0.051375*ln^3(9*gamma) - 0.0071901*ln^4(9*gamma)                                  (4.172)
    a3 = 1.0019 - 0.17927*ln(gamma) + 0.047583*ln^2(gamma) - 0.016417*ln^3(gamma)          (4.173)

and for `h_t/R_q < 5`, with (4.174) of the same form as (4.163) on `h_t`:

    Phi_s = b0 + b1*t + b2*t^2 + b3*t^3 + b4*t^4 + b5*t^5,     t = h_t/R_q                 (4.175)
    b0 = 0.12667*gamma^(-0.6508)                                                           (4.176)
    b1 =  exp(-0.38768 - 0.44160*ln g - 0.12679*ln^2 g + 0.042414*ln^3 g)                  (4.177)
    b2 = -exp(-1.1748  - 0.39916*ln g - 0.11041*ln^2 g + 0.031775*ln^3 g)                  (4.178)
    b3 =  exp(-2.8843  - 0.36712*ln g - 0.10676*ln^2 g + 0.028039*ln^3 g)                  (4.179)
    b4 = -0.004706 + 0.0014493*ln g + 0.00033124*ln^2 g - 0.00017147*ln^3 g                (4.180)
    b5 = 0.00014734 - 4.255e-5*ln g - 1.057e-5*ln^2 g + 5.0292e-6*ln^3 g     (g = gamma)   (4.181)

[(4.176)-(4.179) read on the page image; (4.180), (4.181) from the text layer only.] E5 adds
that the fit can give a slightly negative `phi_x` (set to zero), notably for `gamma = 1/9`.
The Patir-Cheng table values recalled `[from memory]` (`gamma` = 1/9, 1/6, 1/3, 1: `C` = 1.48,
1.38, 1.18, 0.90, `r` = 0.42, 0.42, 0.42, 0.56; `gamma` = 3, 6, 9: `C` = 0.225, 0.520, 0.870)
are reproduced by the fits to within 0.02 (check C7), which supports the transcription.
Sutcliffe & Montmitonnet use `gamma = 9` and quote the percolation threshold
`h_t/sigma_t = 0.038` [E4 EX]; (4.171) gives 0.0383 (check C7).

### 2.3 Inlet analysis of the Sutcliffe-Johnson type

Status: **found in full** in Sutcliffe's thesis [E6 FT ch. 4, OCR text plus page images of
pp.46, 51, 55 and Tables 4.1, 4.2]. The 1990 paper [CIT] is its published form.

Oil: `eta = eta0*exp(alpha*p)` (4.2); reduced pressure `alpha*q = 1 - exp(-alpha*p)` (4.3);
`u_bar = (u_R + u_s)/2` mean of roll and strip inlet speeds. Valley Reynolds equation averaged
across the width (`h_v` mean valley film, `d_v` r.m.s. roughness of the valleys, `l` total width
of valleys in the averaging width, stars where the pressure gradient is zero), **as printed**:

    dq_v/dx = 12*eta0*u_bar * (h_v - h_v* * l*/l) / [h_v^3*(1 + 3*d_v^2/h_v^2)]            (4.5)

[its parent (4.4) carries a minus sign on the right; with `x` increasing into the bite and `h`
falling the gradient is positive: sign convention as printed, not reconciled.] Roughness:
Christensen density (2.1); mean film over the whole contact `h_bar = (1 - A)*h_v` [E6 (4.8);
the equation is lost in the OCR and restored from the sentence and E5 (4.203): derived].

Inlet zone, bulk rigid: asperity tops plastic, hardness `H = 2.57*sigma_y`, `sigma_y` plane
strain yield stress (valid when the plasticity index `psi = E'*(d0*kappa)^(1/2)/(2H) > 2`):

    p_a - p_v = 2.57*sigma_y                                                               (4.11)

End of the inlet zone, onset of bulk yield:

    p_a*A + p_v*(1 - A) = sigma_y                                                          (4.12)

Deforming zone: crushing rate `W` from (3.20) with `p_bar = sigma_y - p_v`. With `theta` the
slope of the roll (the slope of the asperity tops), `phi` the slope of the valley bottoms,
`delta` the separation of the centre lines, `t1` entry thickness:

    d(delta)/dx = phi - theta                                                              (4.14)
    t*eps_dot_x/2 = theta*u_s*A + phi*u_s*(1 - A)                                          (4.15)
    phi/theta = 1 - [t1/(2*W*lambda) + 1 - A]^(-1)                                         (4.16)

[(4.13) is printed as `phi = (v_a - v_v)u_s`; the kinematics require
`theta - phi = (v_a - v_v)/u_s`. With that and `v_a - v_v = W*c*eps_dot`, (4.15) gives
`phi/theta = 1 - [t/(2*W*c) + 1 - A]^(-1)`, so the `lambda` of (4.16) is the half spacing `c` of
chapter 3: derived.] `lambda` was taken as "the distance where the auto-correlation function has
fallen to 0.1". End of crushing: valley pressure reaches `sigma_y`; a floor `W >= 0.05` avoids the
asymptote; "The pressure gradient was assumed to be zero at the end of the bulk deformation
region to give the constant of integration". Two unknown separations are adjusted until yield
holds at the end of the rigid zone and the valley pressure reaches `sigma_y` at the end of the
deforming zone. Thermal correction factors (4.6), (4.21) exist (Wilson & Mahdavian; Wilson &
Murch, with `L = eta0*beta*u_bar^2/k`) and were not transcribed (image too coarse).

Smooth film (Wilson & Walowit, straight inlet, isothermal):

    h_w = 6*alpha*eta0*u_bar / [theta0*(1 - exp(-alpha*sigma_y))]                          (4.20)

`theta0` slope of the roll just before the strip deforms plastically; thick strip
`b = sqrt(R*(t1 - t2))`, `theta0 = b/R` (4.17), (4.18). Inlet tension acts like a yield stress
reduced by the tension [E6 p.53]. Dimensionless dependence:

    (Lambda_r, A) = f( h_w/d0 (= Lambda_s), t1/lambda, alpha*sigma_y, h_w/(theta0*b), theta0,
                       d0/b, u_bar/u_R, E_R'/sigma_y, L )                                  (4.19)

Landmarks stated: contact for `Lambda_s < 3`; below about 1 "the strip yields before the pressure
in the valleys reaches the yield stress"; in a straight, smooth, isothermal inlet "the distance at which the
reduced pressure rises to 20% of its final value is given by 8.5 h_w/theta_0 and the point of
inflection in the reduced pressure curve is given by 0.5 h_w/theta_0"; `h_w/(theta0*b) = 2*h_w/(t1 - t2)` is small in mixed lubrication, so the inlet may be taken
as straight; `theta0` and `d0/b` then have no influence on the film [E6 pp.55-56].

**Published numbers for the Fig. 9 foil case** (the thesis computed the inlet on the Mear-Zhang
bite of that case). Table 4.1, thin foil column: `eta0` 1.0e-3 Pa s at `T0 = T` = 60 C, `beta`
0.0139 /C, `alpha0` 1.0e-8 m2/N, `k` 0.125 W/m C (assumed), `R0` 88.9 mm, `E_R'` 230 GPa, `u_R`
1.0-30 m/s, `t1` 0.020 mm, reduction 0.25, `d0` 0.1 um, `lambda` 15 um, `sigma_y` 230 MPa.
Geometry of the bite used: `b/R = 0.0241`, `theta0 = 0.0036`; slope for crushing 0.00409 ("the
average slope of the front 7% of the plastic region"); slope in (4.20) 0.0058. Table 4.2
(`d0 = 0.1 um`), read on the page image:

| `u_r` m/s | `h_s` um (full integration) | `h_w` um (4.20) | `h_d` um (Dowson-Toyoda) | `h_v` um | `h_a` um (under contacts) | `h_t` um | `A` | `alpha*q_v` at `A` = 0.1 | `Lambda_s = h_s/d0` [derived] |
|---|---|---|---|---|---|---|---|---|---|
| 30 | 0.237 | 0.323 | 0.294 | 0.217 | - | - | 0.01 | - | 2.37 |
| 10 | 0.097 | 0.108 | 0.136 | 0.110 | 0.031 | 0.088 | 0.28 | 0.64 | 0.97 |
| 5 | 0.055 | 0.054 | 0.084 | 0.079 | 0.018 | 0.047 | 0.53 | 0.38 | 0.55 |
| 3 | 0.036 | 0.032 | 0.059 | 0.062 | 0.013 | 0.028 | 0.69 | 0.24 | 0.36 |
| 1 | 0.014 | 0.011 | 0.027 | 0.042 | 0.006 | 0.010 | 0.88 | 0.08 | 0.14 |

This is a published `A(Lambda_s)` curve with five points for an aluminium foil pass (one
roughness, one wavelength, one oil). The tabulated `h_w` is reproduced by (4.20) with
`u_bar = 0.93 to 0.96 u_r` (check C8), i.e. an inlet strip speed of about 0.88 of the roll speed.
Friction from these films [E6 (4.31), (4.32)], `Delta_u` sliding speed, oil properties at the
contact pressure:

    mu_a = (tau_0*A/p) * asinh(eta*Delta_u/(tau_0*h_a))             asperity tops
    mu_v = (tau_0*(1 - A)/p) * asinh(eta*Delta_u/(tau_0*h_v))       valleys

### 2.4 Boundary friction on the contact areas, `mu_c(h_s, r)`

Status: **found in part**. The method and conditions are fully described in the manuscript of
Le & Sutcliffe [E7 FT of an author manuscript on a document-sharing site; equations partly lost
in extraction, figures absent]; the fitted curves exist only as its Fig. 6 ("The curves are
fitted to the measurements using the least mean square method for the two nominal reductions");
no formula is printed in the manuscript.

- Rig: strip drawing through flat dies of heat-treated tool steel, half die angles 3, 5, 10 and
  20 degrees, die `R_q` 0.05 um (0.1 um after the first draw), die hardness about 7000 MPa
  (Vickers), re-polished after two tests. Strip: cold-rolled 1050, work hardened, 6 x 24 x
  250 mm, `R_q` about 0.225 um, hardness 415 MPa, "giving an estimated plane strain yield stress
  of 161 MPa". Speed 0.016 m/s. Film by `h_w = 6*eta0*alpha*u_bar/(theta*(1 - exp(-alpha*Y)))`
  (its eq. 2, `u_bar` half the strip inlet speed), varied from 1 to 100 nm with three oils.
- Friction from drawing force `F` and indentation force `N`:
  `mu = (F/(2N) - tan(theta))/(1 + (F/(2N))*tan(theta))` (its eq. 3; the layout is lost in the
  extraction and restored from the force balance on a wedge die: derived).
- Result in words: friction rises as the film falls from 100 to 1 nm; at 25 % nominal reduction
  it is "significantly higher" than at 12.5 %, less so at thicker films; exit `R_q` about
  0.125 um; severe pick-up at the thinnest film did not change friction.
- Use in rolling: `mu = a*mu_b + (1 - a)*tau_v/p_v` (its eq. 7), `a` contact ratio averaged across
  the width, `tau_v = tau_0*asinh(eta*u/(tau_0*h_v))` (eq. 6, from eqs 4 and 5), `mu_b` read from
  the Fig. 6 fit at the rolling `h_w`. With a constant `mu_b = 0.09` the prediction "is poor.
  Moreover, it would not be possible to bring this into line with experiments by judicious
  adjustment of the boundary friction coefficient".
- Table 1 of the manuscript (viscosities at 20 C, `eta = eta0*exp(-beta*(T - T0))`; values in
  brackets estimated by the authors):

  | oil | density kg/m3 | `eta0` Pa s | `beta` /C | `alpha` m2/N | Eyring stress `tau_0` MPa |
  |---|---|---|---|---|---|
  | Vitrea 68 | 881 | 0.149 | 0.044 | (2.2e-8) | 2.0 |
  | M320 | 891 | 0.671 | 0.043 | (2.5e-8) | (2.0) |
  | HVI 650 | 915 | 1.915 | 0.079 | 3.29e-8 | 2.6 |

An alternative that is fully specified [E6 FT p.72]: boundary shear strength of calcium stearate
(Briscoe et al., extrapolated by Sutcliffe to 60 C) 3.2, 8.3 and 55 MPa at 230, 625 and 1510 MPa,
i.e. `tau_b/p` = 0.014, 0.013, 0.036 [derived]; with `A = 0.53` this gives asperity friction
0.007, 0.007 and 0.019, as the thesis states. The thesis concludes that friction in foil rolling
computed this way is "significantly lower than the generally quoted values".

### 2.5 Two-wavelength roughness

Status: **found in part** [E7 FT manuscript]. Long and short wavelengths `L`, `lambda` with
initial r.m.s. amplitudes `Sigma_0`, `sigma_0`, longitudinal lay, pseudo-Gaussian asperity shape;
contact ratio `a` of the short wavelength averaged across the long one. One averaged Reynolds
equation for a valley pressure uniform across the width,
`dq/dx = 12*eta0*u_bar*(h_t - h*)/(h_t^3*(1 + 3*sigma_t^2/h_t^2))` (its eq. 1, restored from a
damaged extraction: `q = (1 - exp(-alpha*p_v))/alpha`, `h_t` mean film, `sigma_t` total r.m.s.
roughness, `h*` a constant). Three zones: inlet (no bulk deformation, `p_a - p_v = 2.57*Y`),
transition (bulk deformation, crushing of both scales "following the calculations of Korzekwa",
linked by volume conservation, ends where `dq/dx = 0`), work zone (pressures equal, film thins
with elongation at constant oil flow). Numbers of the illustrated case: `R` 25 mm, `t1` 0.82 mm,
25 %, `u_r` 0.1 m/s, `eta0` 0.35 Pa s, `alpha` 2.2e-8 /Pa, amplitudes 0.36 and 0.12 um,
wavelengths 50 and 5 um, `Lambda_s` 0.16; for the comparison with Tabary et al.: `sigma_t` 0.5 um,
roll 0.06 um, 50 and 5 um, `R` 30 mm, `t1` 0.35 mm, 25 %, `eta0` 0.077 Pa s, `alpha` 2.2e-8 /Pa.
"Although the inlet zone is very short, it accounts for most of the surface flattening."
Missing: the crushing laws of the two scales and their coupling (Le & Sutcliffe 2000, Tribology
Transactions, "A two-wavelength model of surface flattening ...": only the abstract was found).

### 2.6 Sutcliffe & Montmitonnet (2001): what the excerpt adds

[E4 EX: passages of the repository text returned by the search tool; equation images lost.]

- Friction on asperity tops: `tau_a = mu_a*p_a` or `m_a*k` (its [2]); Coulomb limited to the shear
  yield stress `k` of the strip, `k = Y/sqrt(3)` with `Y` the plane strain yield stress.
- Sticking zone: `tau_a = delta*mu_a*p_a` or `delta*m_a*k`, the knock-down `delta` a function of
  `theta/theta_1` and a tolerance `eps` (its [3], form lost): "For theta/theta_1 << eps the
  frictional stress is approximately proportional to the roll slope while, for
  theta/theta_1 >> eps, delta approaches one"; `theta_1` the roll slope "at the middle of the
  first reduction region"; "Typically a value of eps = 0.1 was found appropriate". "As long as eps
  is sufficiently small, the roll stays essentially flat there and the solution is unaffected by
  the exact form of the friction law."
- Valleys: Newtonian shear at a depth `h_t/(1 - A)`; "The lesser of this hydrodynamic estimate
  and the corresponding shear stress tau_a on the asperity tops is used"; mean shear a weighted
  sum of the two (its [4]).
- Table I in full: strip 50 -> 25 um, yield 150 MPa, tensions 20 / 20 MPa, **E 70 GPa, nu 0.3**;
  rolls radius 135 mm, 5-40 m/s, **E 210 GPa, nu 0.3**; combined r.m.s. roughness 0.3 um,
  wavelength 30 um, `mu_a` 0.1 or `m_a` 0.25; oil 2.5e-3 Pa s, 1.2e-8 m2/N. The two friction laws
  "give the same stress for p = 1.4Y" [`0.1*p = 0.25*Y/sqrt(3)` gives 1.44: derived].

---

## 3. Viscosity and shear

### 3.1 Roelands

Status: **found in full** [E5 FT sec. 4.8.2.2 and Appendix L, which derives it from Roelands'
thesis, eq. (V-9b); Roelands itself CIT]. Original units: `eta` in cP, `p` in kgf/cm2, `T` in C:

    (log10(eta) + 1.2) / (log10(eta0) + 1.2) = (1 + p/p_r)^z * ((T0 + 135)/(T + 135))^S0      (L.1)

`eta0` viscosity at atmospheric pressure and the reference temperature `T0`; `p_r` = 2000
kgf/cm2 = 196.2 MPa; `z` viscosity-pressure index; `S0` atmospheric slope index (temperature).
With `eta` in Pa s (`(3 + 1.2)*ln 10 = 9.67`):

    ln(eta) = (ln(eta0) + 9.67) * (1 + p/p_r)^z * ((T0 + 135)/(T + 135))^S0 - 9.67            (L.3)
    eta = eta0 * exp{ (ln(eta0) + 9.67) * [ (1 + p/p_r)^z * ((T0 + 135)/(T + 135))^S0 - 1 ] }

(Metalub's eq. (4.193) is the same with `eta0` in MPa s and `ln(1e6*eta0)`.) Matching the Barus
slope at `p = 0`, `T = T0`:

    z = p_r*alpha / (ln(eta0) + 9.67)             (eta0 in Pa s)                              (4.194)

E5 warns that Marsault's thesis prints the pressure and temperature terms as a *sum* minus 2
(its L.7), "which is wrong". Barus: `eta = eta0*exp(alpha*p)` (4.192). The extended WLF law is
given in form only (4.195)-(4.197), constants in reports not read.

Check on a real foil oil (C9): for Somentor 31 at 40 C, `z = 0.657` from `alpha`; Roelands gives
3.70 mPa s at 100 MPa (measured 3.985) and 0.18 Pa s at 625 MPa against 2.5 Pa s deduced from the
disc machine, the direction the thesis reports ("This fit underestimates the viscosity at high
pressures"). `S0` from the 40 and 100 C points is 1.01 [derived].

### 3.2 Eyring shear, Eyring stress, limiting shear stress

Status: **found in full for one kerosine foil-rolling base oil** [E6 FT ch. 2, Table 2.1 and
Fig. 2.7 read on page images].

    gamma_dot = tau_dot/G + (tau_0/eta) * sinh(tau/tau_0)        (non-linear Maxwell)      [E6 (2.2)]

with a limiting shear stress `tau_c`; `G` about `3p` for mineral oils (Evans & Johnson, as
quoted). For the foil oil the Deborah number `eta*u/(G*a0)` is at most 0.03, so the elastic term
drops: `tau = tau_0*asinh(eta*gamma_dot/tau_0)`.

Oil: "Somentor 31 is a mainly paraffinic kerosine mineral oil with a carbon chain length of
approximately 14 and a molecular weight of about 200. No additives were added". Table 2.1
(Amsterdam viscometer):

| pressure MPa | 40 C | 60 C | 100 C |
|---|---|---|---|
| 0 | 1.409 mPa s | 1.033 | 0.632 |
| 25 | 1.905 | 1.386 | 0.844 |
| 50 | 2.481 | 1.784 | 1.080 |
| 75 | 3.157 | 2.192 | 1.342 |
| 100 | 3.985 | 2.699 | 1.625 |
| `alpha` (0-100 MPa), 1e-9 m2/N | 10.40 | 9.60 | 9.44 |

[`beta = -d ln(eta0)/dT` = 0.0155 /C between 40 and 60 C, 0.0123 between 60 and 100 C: derived;
the thesis uses 0.0139 at 60 C.] Disc machine (tungsten carbide discs), Eyring fits in the
figure keys:

| mean Hertz pressure | temperature | Eyring stress `tau_0` | viscosity at pressure |
|---|---|---|---|
| 625 MPa | 40 C | 4.5 MPa | 2.5 Pa s |
| 625 MPa | 80 C | not reached (Newtonian fit) | 0.33 Pa s |
| 945 MPa | 40 C | 6.0 MPa | 15.0 Pa s |
| 1510 MPa | 40 C | 11.7 MPa | 740 Pa s |
| 1510 MPa | 80 C | 11.0 MPa | 33 Pa s |

`tau_0` rises with pressure, roughly `0.007*p` [derived: 4.5/625, 6.0/945, 11.7/1510]; it is
higher than for HVI 650 (about 2 to 7 MPa over 750 to 1450 MPa at 60 C, Fig. 2.7 by eye).
**Limiting shear stress:** "In none of the above measurements up to a shear stress/normal
pressure ratio of 68/1510 MPa (mu = 0.045) was a limiting shear stress observed"; Evans & Johnson
"find that the limiting shear stress tau_c is approximately proportional to the mean pressure for
mineral oils". So for this oil the coefficient `tau_L/p` is above 0.045 at 40 C; no value was
found. Thermal conductivity: 0.125 W/m C at ambient pressure (assumed equal to HVI 650);
"after allowing for the increase in conductivity with pressure ... 0.25 W/mK" in the nip.
Molecular length of oil and additive "of the order of 3nm" (the length Schey gives for calcium
stearate).

Other oils: Table 1 of E7 in section 2.4 (Vitrea 68: 2.0 MPa; HVI 650: 2.6 MPa; pressure and
temperature of these two values are not stated there). Oils with additives (fatty acid, alcohol,
ester in kerosene): no rheology found. A typical `tau_L/p` of 0.05 to 0.1 for mineral oils is
`[from memory]` and has no source here.

---

## 4. Flow stress of 1xxx / 8xxx foil alloys at large strain

Status: **not found for foil alloys**; law forms and constants for neighbouring materials only.

- Kocks-Mecking and Voce [E11 EX, extraction of a book chapter with damaged symbols]:
  `sigma = alpha*mu*b*M*sqrt(rho)` (11.4); `d(rho)/d(eps) = k1*sqrt(rho) - k2*rho` (11.5);
  `theta = theta_0*(1 - sigma/sigma_v)` (11.7), `sigma_v` the *scaling* stress obtained by
  extrapolating stage III to zero hardening, "to emphasise the difference" from a true saturation
  stress; `theta_0` "approximately 1200-1500 MPa for aluminium at ambient temperature"; `k1`
  athermal, `k2` strongly temperature dependent and weakly rate dependent. Stage IV: Tome's form
  `sigma = (sigma_v + theta_IV*eps)*{1 - exp(-theta_0*eps/sigma_v)}` (11.14); stage IV rate
  "usually below 100 MPa at ambient temperature"; for can-end AA5182 "about 50 MPa" beyond a
  strain of 0.5 in rolling against about 150 MPa near fracture in a bulge test; plant rolling lies
  below laboratory rolling because of heating, "the terminal Stage IV work hardening rates are
  about the same". No constants for 1xxx or 8xxx.
- A logarithmic law validated to large strain by bulge tests [E10 EX: full html text; the two
  tables through the search tool's extract of the PDF]:

      sigma = sigma_0 + sigma_s * ln(1 + (theta_0/sigma_s)*eps)                             (7)

  `sigma`, `eps` von Mises equivalent stress and plastic strain; `theta_0` initial hardening rate,
  `sigma_s` controls saturation. Table 1: pure Al `sigma_0` 30, `theta_0` 1180, `sigma_s` 33 MPa;
  Al-3Mg 82, 4800, 65; Al-4.5Mg 102, 4800, 95. Table 2, Al-0.2 % Cu: 300 K 35, 1700, 15; 200 K
  35, 1700, 33; 77 K 35, 1700, 100. No rate term ("Include the strain rate effect" is listed as
  future work). [For orientation, derived: pure Al gives 149 MPa at strain 1 and 194 MPa at
  strain 4, slope 8 MPa per unit strain at 4.] Solution-treated laboratory alloys, not foil stock.
- Saturation stress as a function of rate and temperature, form only [E19 EX, cast A356, not
  transferable in its constants]: `sigma_s = sigma_s0*(mu/mu_0)*(1 - (g/g_0)^(1/q))^(1/p)`,
  `g = (k*T/(mu*b^3))*ln(eps_dot_0/eps_dot)`, `p = 1/2`, `q = 2`, `eps_dot_0 = 1e7 /s`.
- Annealed tempers: 1100-O `sigma = 133 - 81*exp(-6.1*eps)` MPa fitted to strain 0.2, rate
  dependence "negligible" at quasi-static rates [E17 EX; already in the reports]; 1050 annealed
  `K = 144.6 MPa`, `n = 0.3` (Hollomon), and a saturation-type law with `sigma_sat = 650.8 MPa`,
  `sigma_00 = 15.3 MPa`, `h_p = 1255 MPa`, `a = 15.5` whose equation was not retrieved [E18 EX].
- Work softening of purified-matrix Al-Fe: nothing beyond the existing report (hardness data,
  no law).

Looked in: open theses (the NTNU archive holds a relevant thesis on work hardening of commercial
purity sheet, its file download was refused), publisher previews, the open chapter extract.

---

## 5. Roll-strip interface conductance

Status: **found in part.**

- Parallel form for mixed lubrication [E12 AB: publisher preview with section snippets]:
  `h_c = h_cs + h_cf`, "`h_cs` is the IHTC in the actual contact and `h_cf` is the IHTC in the
  lubricant"; solid part "based on the Mikic's work and data analysis":

      h_cs = 3800 * k_h * Ra^(-0.257) * (p_a/(M + p_a))^0.94 ,    k_h = 2*k_s*k_r/(k_s + k_r)

  [the preview cuts off inside the definition of `k_h` (harmonic mean of strip and roll
  conductivity, completed here: derived); `M` hardness, units of `Ra` and the film term `h_cf`
  are not visible]. Values it collects: aluminium rolling models 25, 30, 40 kW/m2K; Hlady et al.
  50-800 kW/m2K; Wang & Tseng 44-54 kW/m2K and 350-2800 kW/m2K with roughness varied; steel 10 to
  11.6 kW/m2K; Chen et al. 40-240 kW/m2K in hot rolling of steel.
- Cooper-Mikic-Yovanovich correlation as printed on two teaching pages [E13 VP]:

      h_c = 1.25 * k_s * (m/sigma) * (P/H_c)^0.95 ,   k_s = 2*k_1*k_2/(k_1 + k_2)
      h_g = k_g/Y ,   Y/sigma = 1.184*[-ln(3.132*P/H_c)]^0.547 ,   h_joint = h_c + h_g
      m = 0.125*(sigma in um)^0.402          (Antonetti-Yovanovich slope estimate)

  `sigma` combined r.m.s. roughness, `m` mean absolute slope, `P` contact pressure, `H_c`
  microhardness of the softer body, `k_g` conductivity of the gap fluid, `Y` mean plane
  separation. Stated validity `1e-6 <= P/H_c <= 2.3e-2`. A rolling bite has `P/H` of 0.3 to 1 and
  a contact ratio set by bulk straining, so this correlation is **outside its range** there
  [derived]; with a known contact ratio the natural form is the parallel one of E12 with the
  film term `(1 - A)*k_oil/h_v` [inferred, not from a source].
- Tseng [E14 AB]: the review recommends "the thermal contact conductance approach"; the
  interface is modelled "as one-dimensional heat transfer with friction heat generated along the
  interface"; the resistance "depends on surface roughness, contact pressure, and the coolant,
  lubricant or oxide scale". No formula in the abstracts.
- Oil conductivity for the film term [E6 FT]: 0.125 W/m C at ambient pressure, 0.25 W/m K in the
  nip. A 70 nm film then conducts 1.8 to 3.6 MW/m2K [derived].
- Metalub's simplification [E5 FT sec. 4.9.2]: no interface model; the strip is adiabatic except
  that "the heat due to friction is commonly assumed to be distributed evenly between the roll and
  the strip"; `dT_s/dx = [beta_s*(D_x^p*sigma_x + D_z^p*sigma_z) + tau_i*(v_r - v_s)/t_s]/(rho_s*c_s*v_s)`
  (4.211), Taylor-Quinney `beta_s = 0.9`.

Missing: the asperity conductance term in Tseng's own papers, and any measured interface
conductance for cold aluminium rolling with a kerosene oil.

---

## 6. Found in passing

### 6.1 The steel chatter benchmark TM-LC7 (Niroomand, Forouzan & Salimi 2015) [E9 FT]

Two-stand reversing tandem mill, four-high stands, third pass, chatter in the second stand.

Table 3, "Specifications of the two-stand tandem mill unit":

| parameter | stand 1 | stand 2 |
|---|---|---|
| work roll mass, kg | 14 000 | 14 000 |
| backup roll mass, kg | 38 000 | 38 000 |
| work roll damping coefficient, N s/m | 0 | 0 |
| backup roll damping coefficient, N s/m | 9.54e5 | 9.54e5 |
| work roll spring constant, N/m | 7.01e10 | 7.01e10 |
| backup roll spring constant, N/m | 3.64e8 | 3.64e8 |
| work roll radius, m | 0.245 | 0.245 |
| backup roll radius, m | 0.675 | 0.675 |
| friction factor `m` | 0.051 | 0.054 |
| shear yield stress `k`, MPa | 514.55 | 535.65 |
| strip width, m | 0.732 | 0.732 |
| entry thickness, m | 416e-6 | 324e-6 |
| exit thickness, m | 324e-6 | 216e-6 |

Table 4, inter-stand parameters: distance 5.675 m (payoff reel to stand 1), 4.725 m (stand 1 to
stand 2), 6.6 m (stand 2 to pick-up reel); tensile stress 95, 151, 81 MPa. Strip (Table 1, wave
model): `E` 200 GPa, density 7800 kg/m3. Table 5: experiment 5.81 m/s, 124.6 Hz; simulation with
dynamic (stress-wave) effects 6.42 m/s, 129 Hz; without 6.57 m/s, 132 Hz. The text gives the
recorded critical speed as that "of the first stand", 5.8 m/s. Excitation in the simulation: a
thickness step of 10 um for 1 ms from the payoff side. Accelerometer sampling 5120 Hz. Incoming
coils are 2 mm; the tabulated pass is the third.

Structure model (symmetric, two degrees of freedom per stand; `W` strip width):

    M_w*y_w'' + C_w*(y_w' - y_b') + K_w*(y_w - y_b) = W*df_y                               (3.13)
    M_b*y_b'' + C_b*y_b' + K_b*y_b = C_w*(y_w' - y_b') + K_w*(y_w - y_b)                   (3.14)
    I*theta'' + B*theta' + k_r*theta = -w*dT                                               (3.15)

Process model (after Hu et al.; rigid-perfectly plastic, no roll flattening, friction **factor**
`m`, shear yield stress `k`; `h_c` roll gap at the centre line, `x_c` horizontal roll position,
`v_r` roll speed, `x_1`, `x_2`, `x_n` entry, exit, neutral positions, `sigma_1`, `sigma_2` entry
and exit tensile stress), transcribed from a page image at screen resolution, to be checked
against the PDF before coding:

    f_x = (sigma_1/2)*(h1 - h2) - k*h2*ln(h1/h2)
          - m*k*h2*sqrt(R/h_c)*[2*atan((x_n - x_c)/sqrt(R*h_c)) - atan((x_1 - x_c)/sqrt(R*h_c))
                                - atan((x_2 - x_c)/sqrt(R*h_c))]                           (3.1)
    f_y = (2k + sigma_1)*(x_2 - x_1) + 4k*sqrt(R*h_c)*[atan((x_1 - x_c)/sqrt(R*h_c))
          - atan((x_2 - x_c)/sqrt(R*h_c))] + 2*m*k*sqrt(R/h_c)*(x_2 - x_c)*[2*atan((x_n - x_c)/sqrt(R*h_c))
          - atan((x_1 - x_c)/sqrt(R*h_c)) - atan((x_2 - x_c)/sqrt(R*h_c))]
          + m*k*R*[ln(h1/h_n) + ln(h2/h_n)] + 2k*(x_2 - x_c)*ln(h1/h2)                      (3.2)
    T   = m*k*R^2*[2*atan((x_c - x_n)/sqrt(R^2 - (x_n - x_c)^2)) - atan((x_c - x_1)/sqrt(R^2 - (x_1 - x_c)^2))
          - atan((x_c - x_2)/sqrt(R^2 - (x_2 - x_c)^2))]                                   (3.3)
    u_1 = (1/h1)*[(v_r + x_c')*h_c + (v_r + x_c')*(x_n - x_c)^2/R + (x_1 - x_n)*h_c' - h1*x_c']   (3.4)
    u_2 = [u_1*h1 + (x_2 - x_1)*h_c' + (h1 - h_c - (x_2 - x_c)^2/R)*x_c'] / [h_c + (x_2 - x_c)^2/R]   (3.5)
    x_1 = x_c + sqrt(R*(h1 - h_c))                                    (as printed)         (3.6)
    x_2 = x_c + R*h_c*h_c' / (2*[u_1*h1 - (x_1 - x_c)*h_c' + h1*x_c'])                      (3.7)
    h2  = h_c + (x_2 - x_c)^2/R                                                            (3.8)
    x_n = x_c + sqrt(R*h_c)*tan[ (1/2)*atan((x_1 - x_c)/sqrt(R*h_c)) + (1/2)*atan((x_2 - x_c)/sqrt(R*h_c))
          + (sqrt(h_c)/(2*m*sqrt(R)))*(ln(h2/h1) - (sigma_1 - sigma_2)/(2k)) ]             (3.9)

Inputs `[d sigma_1, d sigma_2, dh1, dx_c, dh_c, dv_r]`, outputs `[df_x, df_y, dT, du_1, du_2]`
(3.10), (3.11), linearised.

What is **not** in the paper: the rotational constants `I`, `B`, `k_r`; reel inertias; the
roll speed of the stable reference cases; the stress-wave inter-stand model of its section 2 was
not transcribed. Peculiarities to carry: friction is a *factor* on shear yield (0.051 and 0.054
of `k`), not a Coulomb coefficient; no roll flattening although `R/h` is about 1000; the entry
side sign of (3.6). To run it in a Coulomb, flattened-roll model is a different model, not a
re-run of theirs.

### 6.2 Foil cases with measured load, slip and gauge

Not found. Le & Sutcliffe (2002) report industrial mill trials for thin strip and foil (load in
reasonable agreement, forward slip over-estimated for foil) [E15 AB]; no open copy was reached.
The thesis measurements [E6 ch. 5] are film thickness on an experimental mill at 0.115 to
2.82 mm, not foil loads.

---

## 7. Consistency checks run

Scripts in `scratchpad/s24/scripts/`: `checks.py` (C1-C3, C5-C9), `fleck_fig9.py`,
`fleck_fig9_endzone.py`, `fleck_fig9_triangles.py`, `fleck_fig9_profile.py` (C4). numpy only.

| id | check | result |
|---|---|---|
| C1 | Fleck (30), (31) against direct quadrature of the half-space integrals for a triangular element | (31) agrees to six digits. (30) as printed equals **minus** the displacement into the roll required by (7): the printed sign is wrong; SPEC18's derived kernel has the right sign. |
| C2 | Fleck (20) on a constant-thickness element, exact `p(c)/p(0) = exp(mu*c/b)` = 1.061837 | derived form 1.061856; printed form 0.941748 (pressure falls where it must rise). |
| C3 | Coefficient of `p` in (14a) | 0.619 for `nu_s = nu_R = 0.3`, `E_s*/E_R* = 1/3`; 0.627 with the Fig. 9 moduli; 0.69 for `nu_s = 1/3`. The paper's 0.62 implies both Poisson ratios 0.3. |
| C4 | Re-implementation of (22), (23) with the conditions of Appendix 2 on Fig. 9 (section 1.12) | Load independent of zone E (under 0.3 %); dependent on the end closure (88 to 135); 118 needs an end length of about 5 um; the plotted curve and the thesis contact length match about 102 to 105. Dimensionless identities used: `B0` = 112.36, `U` = 30, `X` = 11.236 per mm. |
| C5 | Eq. (29), R 89 mm, mu 0.03, `Y_s/E_R*` 1e-3 | 51.2, 36.2, 22.9 um at r = 0.5, 0.25, 0.10: the numbers SPEC18 uses. |
| C6 | Wilson-Sheu fit | `H_a(E_p = 0, A -> 0)` = 5.142 = 2 + pi; `f1` is positive for `A < 1` and zero at `A = 1`. Sutcliffe (3.20) and the Marsault form coincide only at `p_bar/2k = 1`. |
| C7 | Flow-factor fits against the Patir-Cheng table values `[from memory]` | within 0.02 for all seven `gamma`; percolation threshold for `gamma = 9`: 0.0383 against 0.038 quoted by E4. |
| C8 | Thesis Table 4.2 against eq. (4.20) | reproduced with `u_bar/u_r` = 0.93 to 0.96 at all five speeds. |
| C9 | Roelands with `z` from (4.194) against the Somentor 31 table | 3.70 against 3.985 mPa s at 100 MPa; far too low at 625 and 945 MPa, as the thesis says of its Roelands fit. |
| - | Christensen polynomials (4.18), (4.20) | end values correct (by hand, section 2.1). |
| - | Regime-III yield return `p(x_CD) = p(x_BC)` from (14a) | follows (by hand, section 1.8). |
| - | Group identity `H_bar = 2*B0/U` | follows (by hand, section 1.1). |

Not checked: the Korzekwa regression against the finite-element data; the Wilson-Marsault shear
factor; the Niroomand equations (no values to compare).

---

## 8. Sources

| Id | Reference | URL | Read |
|---|---|---|---|
| E1 | Fleck, Johnson, Mear & Zhang (1992) Cold rolling of foil. Proc. IMechE Part B 206:119-131 | https://www.fleckmech.org/papers/34.pdf | FT (scan without text layer; all 13 pages read as images; eqs (20), (30)-(32), (36), Appendix 3 and Fig. 9 re-read on enlarged crops) |
| E2 | Fleck & Johnson (1987) Towards a new theory of cold rolling thin foil. Int. J. Mech. Sci. 29:507-524 | https://www.fleckmech.org/papers/12.pdf | FT for pp.510-514 (5 of 18 pages, as images); appendices not read |
| E3 | Le & Sutcliffe (2001) A robust model for rolling of thin strip and foil. Int. J. Mech. Sci. 43:1405-1419 | https://doi.org/10.1016/S0020-7403(00)00092-8 | AB (abstract through aggregators, with dropped words) |
| E4 | Sutcliffe & Montmitonnet (2001) Numerical modelling of lubricated foil rolling. Rev. Metall. 98:435-442 | https://minesparis-psl.hal.science/hal-00574224 | EX (passages returned by the search tool; equation images lost; direct download answered by an automated-access check and not pursued) |
| E5 | Boemer (2020) Numerical modeling of friction in lubricated cold rolling. PhD thesis, University of Liege, 591 pp. | https://orbi.uliege.be/handle/2268/245441 (file THESIS_BOEMER_2020.pdf) | FT for sections 4.4.2-4.4.4, 4.7.1-4.7.2, 4.8.1.3-4.8.3, 4.9.1-4.9.3, Appendix L (text layer; equations checked on page images where stated); remainder not read |
| E6 | Sutcliffe (1989) Friction and lubrication in metal rolling. PhD thesis, University of Cambridge, 219 pp. | https://www.repository.cam.ac.uk/items/c795b400-951f-4dcf-b43d-1e421264497a | FT for chapter 2, sections 3.2.1 (part), 3.3, 3.4, 4.2-4.3, 4.7-4.8, Tables 2.1, 4.1, 4.2, Fig. 2.7 (scan with OCR layer; equations and tables read on page images); chapters 1, 5, 6 and the appendices not read |
| E7 | Le & Sutcliffe, A semi-empirical friction model for cold metal rolling (author manuscript of Tribol. Trans. 44:284-290, 2001) | https://studylib.net/doc/7558620/friction4 ; https://doi.org/10.1080/10402000108982460 | FT of the manuscript text as extracted by the fetch tool (equations partly damaged, figures absent) |
| E8 | Sutcliffe (2002) Surface finish and friction in cold metal rolling, ch. 4 in Lenard (ed.), Metal Forming Science and Practice (manuscript copy) | https://docest.com/doc/493218/guidelines-for-authors | EX (sections 4.1-4.2; equation images missing; sections 4.3-4.6 not returned) |
| E9 | Niroomand, Forouzan & Salimi (2015) Theoretical and experimental analysis of chatter in tandem cold rolling mills based on wave propagation theory. ISIJ Int. 55(3):637-646 | https://www.jstage.jst.go.jp/article/isijinternational/55/3/55_637/_pdf | FT (sections 3-5 and all tables; section 2 skimmed) |
| E10 | Bouaziz & Lloyd (2022) Assessment of a physical based modelling suitable to capture the mechanical behaviour at large plastic strain of aluminium alloys. Metall. Res. Technol. 119:419 | https://doi.org/10.1051/metal/2022064 | EX (html text through the fetch tool; Tables 1, 2 through the search tool's PDF extract) |
| E11 | Poole, Embury & Lloyd (2011) Work hardening in aluminium alloys, in Fundamentals of Aluminium Metallurgy | https://www.researchgate.net/publication/285784404_Work_hardening_in_aluminium_alloys | EX (search-tool extract with damaged symbols) |
| E12 | Wu, Liang, Tang & Pan (2016) Interfacial heat transfer under mixed lubrication condition for metal rolling. Appl. Therm. Eng. 106:1002-1009 | https://doi.org/10.1016/j.applthermaleng.2016.06.078 | AB (publisher preview: introduction and section snippets) |
| E13 | Teaching pages printing the Cooper-Mikic-Yovanovich correlation | https://mechcodex.com/calculators/heat-transfer/thermal-contact-resistance ; https://thermofluidcalc.com/calculators/heat-transfer/conduction/thermal-contact-resistance | VP |
| E14 | Tseng (1999) Thermal modeling of roll and strip interface in rolling processes, Parts 1 and 2. Numer. Heat Transfer A 35; Tseng & Wang (1996) Steel Research 67 | https://doi.org/10.1080/104077899275281 ; https://doi.org/10.1080/104077899275290 ; https://doi.org/10.1002/srin.199605457 | AB |
| E15 | Le & Sutcliffe (2002) Rolling of thin strip and foil: application of a tribological model for "mixed" lubrication. J. Tribol. 124:129-136 | https://doi.org/10.1115/1.1402179 | AB |
| E16 | Nielsen, Martins & Bay (2025) Slipline solution to asperity deformation under combined high normal pressure and subsurface deformation. CIRP Annals 74:375-379 (open access) | https://doi.org/10.1016/j.cirp.2025.03.030 | EX (not used for any equation here; an open slip-line treatment that extends Sutcliffe's field) |
| E17 | Ha, Fones, Kinsey & Korkolis (2020) Plasticity and formability of annealed, commercially-pure aluminum. Materials 13:4285 | https://doi.org/10.3390/ma13194285 | EX |
| E18 | Batorfi, Pal, Chakravarty & Sidor (2023) Assessment of deformation flow in 1050 aluminum alloy. Appl. Sci. 13:4359 | https://www.mdpi.com/2076-3417/13/7/4359 | EX |
| E19 | Roy, Maijer & Dancoine (2012) Constitutive behavior of as-cast A356 | https://arxiv.org/abs/1206.2344 | EX (law form only) |

Seen only as citations inside the sources above [CIT]: Wilson & Sheu (1988) Int. J. Mech. Sci.
30:475; Sutcliffe (1988) Int. J. Mech. Sci. 30:847; Korzekwa, Dawson & Wilson (1992); Sutcliffe
(1999) J. Tribol. 121:433; Patir & Cheng (1978, 1979); Wilson & Marsault (1998); Marsault (1998)
thesis; Roelands (1966) thesis; Evans & Johnson (1986); Wilson & Walowit (1972); Johnson,
Contact Mechanics (1985); Greenwood, Fleck & Johnson, "Modified Hertzian contacts"; Sutcliffe &
Johnson (1990); Le & Sutcliffe (2000) two-wavelength model; Tabary et al. (1996); Briscoe et al.;
Hu et al. (chatter process model).

Looked for and not reached: Le & Sutcliffe (2001, 2002) full texts (publisher pages closed; the
university repository search returns only the 1989 thesis; the author's publication pages hold no
files); Dbouk et al. and Krimpelstaetter (not searched beyond what the reports hold, for lack of
time); Marsault's thesis and the repository copy of E4 (the repository answers automated
requests with a browser check; the page-fetch tool of this session cannot reach that host, nor
`mdpi.com` directly); the original Wilson & Sheu, Sutcliffe (1988), Patir & Cheng and Tseng
papers (paywalled); the NTNU thesis on work hardening of commercial purity aluminium (download
refused).

---

## 9. What this changes for the implementation brief

**Package 1 (half-space bite, kernel and solver).**

- The docstring sentence that the missing load lies in "elastic unloading inside the no-slip zone
  and the pressure peak after it (BT-S1 eqs (10)-(14) ...)" must go: the source states that load,
  torque, pressure and shape do not depend on (10)-(14) (1.5, 1.8). Finding 2 of section 0.1 is
  contradicted and should be withdrawn, not carried into code comments.
- Finding 3's support ("The published case carries `E_s*` = 80 GPa") does not hold: `E_s*` enters
  only (12)/(14). The thickness spring is the prototype's own closure of the bite ends. It can
  now be said what it does: it sets the length over which the pressure falls to zero at exit,
  and that length controls the load (1.12, item 6). `E_s*` and `h_ref` are therefore
  load-determining inputs of the reduced model, which the existing sensitivity (96.8 at 40 GPa,
  88.9 rigid) already shows; the limitation text should say so.
- Zone E can now be specified exactly (1.6, 1.8): end the no-slip zone where
  `h_n*p'/2 = T(p)`, continue with a backward-slip reduction zone to the neutral point. It removes
  the inadmissible shear at the downstream end (the "1.44 times the friction limit" of finding 6)
  and with it most of the reason for the "final structure check"; it does not change the load
  (under 0.3 %), so it is an admissibility and forward-slip refinement, not a load fix.
- Kernel: SPEC18's derived coefficients are confirmed (C1); the printed (30) has the opposite
  sign, the printed (20) and (36) are misprinted. The `[M: not in the reports]` tag on the
  triangular element can become "Fleck et al. eq. (30) with the sign corrected, citing Johnson,
  Contact Mechanics p.27".
- The published end conditions (`p = Y_s - sigma` at both ends, `db/dx = 0` at exit) can be
  stated, with the warning that they are not a grid-independent problem.

**Package 2 (benchmarks).**

- BT-V1: record `W_bar` 118 as the caption value, and beside it the profile landmarks of Fig. 9
  (entry -1.18 mm, peak about 7.7 `Y_s` at +0.41 mm, exit +0.95 mm, `p/Y_s` about 6.1 at the
  centre line) and the contact length 2.14 mm of E6. A verdict on the ratio to 118 alone is not
  defensible: the printed model gives 88 to 135 depending on the end closure, and the plotted
  curve corresponds to about 102 to 105. The prototype's 92.9 is then 0.88 to 0.91 of the curve,
  not 0.79. All of this is a `[derived]` check of this note and should be labelled so.
- A second benchmark input set for the same case exists: the inlet table of E6 (2.3).
- BT-V2: the roll radius is confirmed as not stated in E1.
- TM-LC7 can be encoded with every tabulated input (6.1), with the stated caveats (friction
  factor, no flattening, missing rotational constants).

**Package 3 (viscosity, limiting shear, friction closure).**

- The "NOT in the reports" rows can be filled: Wilson-Sheu fit, the Sutcliffe/Marsault and
  thesis forms with their disagreement, the Korzekwa regression, `A(h)` and `h_t(h)` for two
  height distributions (2.1); Patir-Cheng and Wilson-Marsault flow factors (2.2); the complete
  inlet analysis (2.3). An asperity-crushing closure is now specifiable; whether to build it is
  the planner's call.
- For the reduced two-point closure: the default end points can be replaced or cross-checked by
  the five published `(Lambda_s, A)` pairs of E6 Table 4.2 for a 20 um foil pass.
- Roelands can be offered beside the viscosity table, with constants and the unit trap (3.1),
  and with the measured warning that it under-predicts a kerosine oil at bite pressures.
- Eyring stress: 4.5, 6.0, 11.7 MPa at 625, 945, 1510 MPa and 40 C for a kerosine base oil, about
  `0.007*p`; 2.0 and 2.6 MPa for two mineral oils. Limiting shear stress: only a lower bound,
  `tau_L/p > 0.045`. A supplied cap remains necessary.
- `mu_c(h_s, r)` is still not a formula; the boundary shear strengths of 2.4 are the only
  numerical alternative found.

**Package 4 (friction from load, torque, slip).** Nothing new to specify. Two cautions follow
from 1.12: the load-based friction estimate inherits the end-closure sensitivity of the bite
model (at fixed friction 0.03 the load moves by tens of per cent with the closure), and forward
slip is far less sensitive (0.175 to 0.199 across the same range), which argues for weighting
slip in the identification.

**Package 5 (flow stress).** Still no constants for 1xxx / 8xxx foil stock at rolling rates. One
more law form with published constants for pure Al and Al-0.2Cu at three temperatures (the
logarithmic law, section 4) could be added as a selectable form; it has no rate term.

**Package 6 (heat partition).** The oil conductivity is now sourced: 0.125 W/m C at ambient
pressure and 0.25 W/m K in the nip; the in-bite value halves the film resistance used in finding
7. The asperity term has two candidate correlations (section 5), one read only as a preview and
one valid only at light loads; neither can be coded as "Tseng-type" on the evidence here.

**Packages 7 and 8.** Nothing found.

**Package 9 (guided app).** Wording only: the bite comparison card should not present 118 as an
exact target, and the oil questions can name what a data sheet must supply for Roelands (two
viscosities, a pressure coefficient) and for the Eyring shear (a stress of a few MPa that rises
with pressure).
