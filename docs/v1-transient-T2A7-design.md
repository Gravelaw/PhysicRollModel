# T2A7 torque-driven elastic span and append-only reel benchmark

**Status: restricted synthetic verification implementation.** This stage
couples T2A5's distributed elastic span to one variable-radius reel at its
fixed right port. An applied, manufactured **time-only torque** predicts reel
speed; reel speed sets the incoming right-port characteristic, so changes in
torque alter both the reel and span. It is a bounded taut forward-winding
case. It does not implement release, reversal, slack, rolling contact or a
physical winding process.

## Continuum and port closure

Use the T2A5 span law `a=1/lambda`, `p=mu0*a*v`,
`W=EA*(lambda-1)^2/2`, `T=EA*(lambda-1)` and `c0=sqrt(EA/mu0)` on
`0<x<1 m`. The left port has T2A5's prescribed incoming right-running
characteristic. At the right port, the numerical span supplies outgoing
`r=v-c0*lambda`. The reel supplies tangential speed `vp=R(ell)*omega`.
Impose exactly one mechanical boundary relation:

```text
lambda_p = (vp-r)/c0
T_p = EA*(lambda_p-1)
q_p = vp/lambda_p
F_right = (q_p, mu0*q_p*vp-T_p)
F_E,right = q_p*(mu0*vp²/2+W(lambda_p))-T_p*vp.
```

The physical right-face `F_right` is used **directly** in the finite-volume
span update and in the reel transfer, with the same two accepted Heun stage
weights. No second incoming strain condition is imposed. The existing T2A5
solver is unchanged. T2A7's outgoing boundary trace comes from the last
cell mean, so it is a first-order boundary trace; the method has no claimed
global second-order rate. The left-face numerical energy flux includes
Rusanov diffusion and is reported as such, not interpreted as physical inlet
work.

The annulus is the same ideal material-volume geometry as T2A6:

```text
R² = Rc² + (h0/pi)*ell
J = Jc + mu0*(Rc²*ell + (h0/pi)*ell²/2)
ell_dot = q_p
omega_dot = (tau_applied(t)-R*T_p)/J
theta_dot = omega.
```

The full open-system reel angular and energy balances are independently
checked:

```text
d(J*omega)/dt = tau_applied-R*T_p+mu0*q_p*R*vp
d(K+U_wound)/dt = tau_applied*omega+F_E,right.
```

Combining span and reel cancels the shared right energy flux. The remaining
accounting is `d(H_span+K+U)/dt=F_E,left,numerical+tau_applied*omega`,
plus a measured numerical energy defect. The software records
individual span mass/momentum defects, combined inventory, reel angular
impulse, per-step and cumulative reel energy defects, and cumulative whole
system energy defect. Numerical dissipation is not physical material loss.

The preexisting wound interval retains the **exact** initial port stretch;
the numerical right-port projection difference is reported separately. Each
accepted Heun step appends two constant-stretch material packets in stage
order, of lengths `h*q_start/2` and `h*q_predictor/2`. Their retained
energies are `DeltaS*W(lambda_stage)`, so deposited energy and inventory
exactly match the transfer quadrature. Packet stretches are numerical stage
representatives, not exact crossing-time point values. Intervals are
immutable and ordered from core to outer surface by decreasing reference
material label. Packet inventory and outer label are checked separately
against the reel state.

## Independent manufactured case and gates

Use T2A5's `mu0=0.1 kg/reference m`, `EA=10 N`, `lambda0=1.001`,
`V=0.1 m/s`, `delta=1e-4`, `k=5*pi rad/reference m`, `c0=10 m/s` and
the T2A6 `Rc=0.1 m`, `h0=0.001 m`, `Jc=0.01 kg m²`, `ell0=1 m`.
The exact wave defines a **prescribed torque history** independent of the
numerical solution. At each requested time, solve
`lambda0*phi/k+(delta/k)*sin(phi)+(V+c0*lambda0)*t=1` for its right
material cut. Obtain exact `lambda*,v*,q*,ell*,R*,J*,omega*` and
`tau*(t)=J*omega_dot*+R*EA*(lambda*-1)`. This torque is input; the
span field, reel speed, stretch, inventory and angle are outputs. Using
the numerical reel or span state when constructing `tau*` would hide a
feedback error and is disallowed.

Run `0.08 s` on 64, 128 and 256 uniform cells with reconstructed-stage
Courant limit `0.35` and fewer than 4000 accepted steps. Reject before
committing a trial with nonpositive tension, transfer or angular speed,
nonpositive inventory, nonfinite values, a subsonic-domain exit or a stage
Courant violation. At 128 cells, repeat with Courant limits `0.175` and
`0.0875` and require decreasing normalized final-field differences.

The independent test inverts the exact material map by bisection and
compares cell-average stretch/velocity, reel inventory/speed/angle, initial
projection error, the early and final deposited energy, and right-port
kinetic/strain/traction terms and drive work individually. A separate
`+1e-5 Nm` torque perturbation must change both the reel and span, proving
that the boundary feeds back rather than replaying the exact wave. Require
decreasing spatial errors in these quantities; at 256 cells require final
normalized stretch/velocity RMS below `0.01`, reel inventory error below
`1e-7 m`, speed error below `3e-6 rad/s`, angle error below `1e-7 rad`,
deposited-energy relative error at `0.005 s` below `0.2%`, per-step reel
energy defect below `1e-12 J`, cumulative reel energy defect below
`1e-10 J`, and whole-system energy defect below `1e-9 J`. Span balance and
combined inventory defects must stay below `1e-12` in their SI units.
These are synthetic numerical checks, not mill accuracy tolerances. The
absolute energy defect includes both spatial and time integration errors;
its sign is not interpreted as physical dissipation.

Local Python 3.12 observations against the exact synthetic wave:

| Cells | Steps | Final normalized stretch RMS | Final normalized velocity RMS | Max cumulative reel energy defect (J) | Max combined energy defect (J) |
|---:|---:|---:|---:|---:|---:|
| 64 | 151 | `0.05416` | `0.05225` | `5.17e-10` | `5.16e-9` |
| 128 | 300 | `0.01212` | `0.02024` | `6.49e-11` | `9.85e-10` |
| 256 | 599 | `0.00358` | `0.00642` | `8.12e-12` | `2.05e-10` |

The 128-cell normalized final-field differences were `0.002086` then
`0.000512` on the successive time grids. Independent exact anchors at
`0.08 s` are `ell=1.007992803494127808 m`,
`omega=0.99407861715664627 rad/s`,
`theta=0.07875923966511506 rad`, and deposited
`U=4.00466911482543e-8 J`. At `0.005 s`, deposited
`U=2.09051356563685e-9 J`; assigning every new packet base stretch
would overstate this by about 17%.

This is an ideal no-slip, strain-matched tangential transfer. Wound
material rigidly corotates with a fixed-center annulus and retains its
deposition stretch. There is no bending, compaction, radial kinetic energy,
layer relaxation or changing tangency geometry. A release/reversal case
would expose stored stretch that can conflict with the elastic incoming
characteristic; it needs a separately reviewed transition law. A tension
zero requires a slack/contact model. Neither is silently continued here.
No physical material calibration, measurement validation, operational
qualification or full T2 completion is claimed.

[Hanna's moving-discontinuity balance analysis](https://arxiv.org/abs/1406.5175)
motivates compatibility and transport checks but does not supply an elastic
winding law. [Gottlieb, Shu and Tadmor's SSP review](https://epubs.siam.org/doi/10.1137/S003614450036757X)
conditions SSP stability on an appropriate forward-Euler property; naming
the integrator does not prove stability of this coupled boundary.
