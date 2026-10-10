# T2 stored-strain pickup decision

**Status: independently reviewed design option, not an implemented law or a
physical validation.** This decision sits between the published T2A7
append-only torque-driven case and T2A9 matched reaction-mode reversal, and
the integrated torque-driven T2 solver. The user choice between a labeled
idealized transition and resolving reel contact remains open. Neither path
permits calling the present benchmarks a full rolling-mill solver.

## What the existing benchmarks establish

T2A7 transfers material onto the reel while the span and reel port have
identical speed and deposited stretch. Its applied torque predicts reel
motion. T2A9 reverses and reads original deposited intervals during release,
but its speed follows the span and exposed stretch; torque is a reaction.
They do not determine what happens when a torque-driven reel presents stored
stretch different from the returning span stretch. Applying T2A7's matched
port across that mismatch would silently impose incompatible kinematics.

Use positive material-reference flux `q` into the right reel. At release,
let `lambda_w` be the exposed retained stretch, `v_w=R*omega` the wound
surface speed, `lambda_s,v_s,T_s` the span-side state, `mu` the reference
line mass, and `c=sqrt(EA/mu)`. The outgoing span characteristic is
`r=v_s-c*lambda_s`. Conservation of material labels through an idealized
zero-inventory transfer zone requires

```text
q=v_w/lambda_w<0
v_s=q*lambda_s
lambda_s=r/(q-c).
```

In general `v_s` differs from `v_w`; do not impose both equal speed and
unequal stretch. The fixed spatial span uses its side of the mass, momentum
and energy flux:

```text
F=(q, mu*q*v_s-T_s)
F_E=q*(mu*v_s^2/2+W_s)-T_s*v_s.
```

The moving-discontinuity framework in [Hanna's action-principle paper](https://arxiv.org/abs/1406.5175)
and [Singh and Hanna's pickup analysis](https://arxiv.org/html/1611.03332v2)
supports explicit velocity compatibility, singular momentum supply and
separate energy accounting. Both studies have different string/contact
assumptions; neither selects the following reel law.

## Option A: explicit idealized dissipative transition

One **proposed** closure includes a contact-supported tangential transition
inside the reel control volume, with negligible transfer inventory and no
additional externally applied transition couple. The reel retains its
existing ideal annular geometry, so `Jdot=mu*q*R^2`. Let `U_w` integrate
the original wound material's stored energy `W_w`, and define
`E_reel=J*omega^2/2+U_w`. The equations are

```text
ell_dot=q
J*omega_dot=tau_applied-R*T_s+mu*q*R*(v_s-v_w)
U_w_dot=q*W_w
E_reel_dot=tau_applied*omega+F_E-D.
```

For `W(lambda)=EA*(lambda-1)^2/2`, energy balance then fixes the modeled
transition dissipation:

```text
D=(-q)/2*(EA-mu*q^2)*(lambda_s-lambda_w)^2.
```

It is nonnegative for the declared tensile, strictly subsonic release
`-c<q<0`, `lambda_s>1`, `lambda_w>0` and positive wound inventory. The
`q=-c` limit changes the boundary characteristic count and is excluded.
Track accumulated dissipated energy `Qdot=D` separately; combined span,
reel and `Q` close
against external work. At matched stretch, the correction and `D` vanish.
At a bounded zero-speed crossing, `q`, both port speeds, `U_w_dot` and `D`
go to zero without dividing by `omega`. This law cannot be applied to
mismatched positive-flow winding because its dissipative sign would reverse;
new deposition must store the actual entering span stretch.

An independent review found the algebra passive under these assumptions.
It also found that an ordinary force-free elastic jump would require
`(EA-mu*q^2)*(lambda_s-lambda_w)=0`; subsonic mismatch therefore needs
an explicit contact-supported tangential force. Define `P_t` as force on
the strip, positive along the tangent toward the right reel. The proposed
transfer-zone force is `P_t=(EA-mu*q^2)*(lambda_s-lambda_w)`, with its
reaction included in reel accounting. “No
additional applied couple” does **not** mean “no local contact force.”
Passivity does not prove that real winding contact can supply that force,
retain the assumed profile, or produce the calculated dissipation. In particular,
the [Lee–Leok–McClamroch retrieval model](https://ccom.ucsd.edu/reports/UCSD-CCoM-09-01.pdf)
has an inextensible wound side and a different loss assumption; its formula
cannot be imported by reversing flow direction.

## Option B: resolved reel-contact transition

Resolve the transfer region's contact geometry, strip bending/normal and
tangential forces, friction or slip, material state and energy conversion.
This needs additional geometry, constitutive and contact data and separate
verification before torque-driven mismatched release can be integrated.
The full 3D T3 work already requires a contact model, but reel pickup has
its own wrap geometry and cannot be assumed to inherit the roll-bite law.

## Independent verification to freeze before coding either choice

For Option A, start with a constant-state mismatch release: set
`EA=10 N`, `mu=0.1 kg/reference m`, `lambda_w=1.01`,
`lambda_s=1.001`, `q=-0.1 reference m/s`, then
`v_w=-0.101 m/s`, `v_s=-0.1001 m/s` and
`D=4.049595e-5 W`. Use the analytic annulus `R(ell),J(ell)` with
`ell=ell0+q*t` and independently manufacture a time-only torque from the
angular equation. Verify signed span flux, original-layer energy depletion,
dissipation, angular impulse and combined work; repeat with the sign of the stretch
mismatch reversed. These are synthetic checks of the chosen closure.

Next use T2A9's standing-wave reaction torque as a **frozen applied input**
and require the torque-driven solver to recover its matched reversal and
zero transition dissipation under refinement. Vary inertia with the same applied
torque and require the trajectory to change, proving actual dynamic feedback.
A specialist has proposed a non-time-symmetric full-reversal oracle with
deposited-time inversion, pending independent trajectory verification:
at `t=.03 s` it has
`q=-.003665356281849014`, span stretch `1.02210801345005144`, retained
stretch `1.02237819097795219`, and proposed dissipated power
`1.33777966071187929e-9 W`. Its turning-label donor profile has a
square-root cusp, so accepted event handling and one-sided limits need
special care before tolerances can be frozen. Include donor-interface,
depletion and first-tension-zero stops, rejected-trial ownership, restart
and frame-cadence checks. Freeze numerical thresholds from independent
quadrature before implementation; the full-wave dissipation signal is small.

For Option B, freeze a separate contact and dissipation oracle. In either
case, contact-supported pickup must not be claimed physically calibrated
without material/contact measurements and transient observations.
