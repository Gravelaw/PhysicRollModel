# T2A8 retained-strain reaction release to first tension zero

**Status: restricted synthetic verification implementation.** This stage
releases a specially matched wound history into a distributed elastic span.
It starts with negative reel speed; it does not reverse a winding reel.
The reel torque is a reaction to the elastic boundary state, not an
independently prescribed drive. The episode stops at the first computed
zero of tension and has no slack continuation. Arbitrary stored-strain
mismatch, torque-driven release and reversal remain unsupported.

## Exact affine benchmark and retained history

Use `L=1 m`, `mu0=0.1 kg/reference m`, `EA=10 N`, `c0=10 m/s`,
`lambda0=1.001`, `beta=0.02 1/s`, and `V=-0.1 m/s`. The exact
material map

```text
x(S,t)=(lambda0-beta*t)*S+V*t
lambda(t)=lambda0-beta*t
v(x,t)=(V*lambda0-beta*x)/lambda(t)
```

solves `x_tt=c0²*x_SS`. Its entire taut span reaches zero tension at
`t*=0.05 s`. The right material cut is
`Sb(t)=(L-V*t)/lambda(t)`, so `S0=0.999000999000999001` and
`S*=1.005`. Let `D=beta*L-V*lambda0=0.1201 m/s`. The initial
`ell0=1 m` winding owns an outer interval `[S0,S*]` with retained
`lambda_w(S)=D/(beta*S-V)`, and an inner interval `[S*,S0+ell0]`
with retained `lambda_w=1` and zero strain energy. The inner material is
geometrically held on the ideal reel; it is never released in the accepted
episode. Records are core-to-outer by decreasing label, and release
consumes increasing labels from the outer end.

The retained energy is the material-label integral of
`W=EA*(lambda_w-1)^2/2`. For `z=lambda_w(Sb)-1`, evaluate it stably as

```text
Uremain=EA*D/(2*beta)*sum_{n=3..12} (-1)^(n+1)*(n-2)*z^n/n.
```

This is the small-`z` form of
`EA*D/(2*beta)*[(1+z)-1/(1+z)-2*log(1+z)]`. Tests compare it with an
independent Simpson integral over material label. Accepted steps consume
the exact energy of `[Sold,Snew]`; speculative event probes never mutate
stored intervals. The difference between exact energy removal and the
Heun `qW` flux quadrature is reported as a **numerical defect**, not
physical transition loss.

## Boundary, reel reaction and signed fluxes

The left port takes only the exact incoming right-running characteristic.
One-sided linear extrapolation of the computed span gives its outgoing
characteristic. At the right, extrapolate outgoing `r=v-c0*lambda` from
the last two cell means. The newly exposed material supplies **one**
boundary condition, its retained stretch:

```text
lambda_p=lambda_w(Sb)
vp=r+c0*lambda_p
q=vp/lambda_p<0
ell_dot=q; Sb_dot=-q
omega=vp/R(ell); theta_dot=omega.
```

Thus no independent reel speed or torque is imposed on the span. Interior
faces use the T2A5-type monotone reconstruction and Rusanov flux. Both
spatial ends use the physical characteristic-port flux; at the right it is
shared exactly with the release ledger:

```text
F_right=(q,mu0*q*vp-T)
F_E,right=q*(mu0*vp²/2+W(lambda_p))-T*vp.
```

The ideal annulus uses the T2A6 `R(ell)` and `J(ell)` laws. Differentiate
the computed outgoing characteristic using the numerical finite-volume
cell rates, then calculate the reaction:

```text
r_dot = p_dot/(mu0*a)-r*a_dot/a
vp_dot = r_dot-c0*q*lambda_w'(Sb)
R_dot = (h0/pi)*q/(2*R)
alpha = vp_dot/R-vp*R_dot/R²
tau_reaction = J*alpha+R*T.
```

The reel speed is algebraic, not separately integrated. The full angular
balance is `d(J*omega)/dt=tau-R*T+mu0*q*R*vp`; its advected term is
positive because both `q` and `vp` are negative. The reel energy balance
is `d(K+Uremain)/dt=tau*omega+F_E,right`, and the shared right flux
cancels in the span-plus-reel ledger. Individual kinetic, retained-strain,
traction, drive-work and advected-angular terms are saved and checked.
No physical loss law is silently inserted.

## First-hit rule and numerical gates

Run 64, 128 and 256 cells with a reconstructed-stage Courant limit `0.35`,
and time refinement at 128 cells with `0.35`, `0.175`, `0.0875`. Observe
`0`, `0.0125`, `0.025`, `0.0375 s` plus the computed event; the hard
horizon is `0.055 s` and accepted-step budget is 4000. At each accepted
step the cell means, used reconstruction traces and physical ports must
remain taut. A signed linear-elastic extension is allowed solely in a
discarded event probe so a crossing can be bracketed. The predictor's
tautness guard and the **committed endpoint** event are distinct: a
predictor-only violation shortens an ordinary step.

When a trial endpoint first crosses zero, bisect the full coupled trial
from the same saved state. Do not interpolate fields or partly consume
history. Commit the last feasible state with a bracket width at most
`1e-9 s` and terminal minimum tension between `0` and `1e-9 N`.
The upper bracket trial must independently have nonpositive endpoint
tension; a predictor-only violation cannot establish an event bracket.
The minimum may occur inside the span before the outer wound layer is
fully consumed. In that case stop there with the remaining wound energy
and its material labels intact. Reject nonfinite states, positive flow,
nonpositive stretch, inventory exhaustion and sonic exit separately.
The bisection rule is frozen for this monotone affine fixture, not for
arbitrary oscillatory events.

Independent tests compare cell stretch/velocity, first-hit time and
location, reel inventory/speed/angle and reaction torque, retained energy,
and each signed integrated work term with exact affine and material-label
references. A test-only changed initial span strain makes an **interior**
zero occur before `S*`; it guards against falsely waiting for the stored
layer cut. Finest-grid synthetic gates include event error below
`2e-4 s`, normalized stretch/velocity RMS below `0.01`, inventory
error below `1e-6 m`, angular speed error below `1e-4 rad/s`, angle
error below `1e-6 rad`, reaction torque error below `1e-5 Nm`, and
`Uremain(.025)` relative error below `1%`. Require decreasing spatial
errors and fixed-grid temporal field differences. Span mass/momentum and
combined inventory defects stay below `1e-11` in their SI units; wound
ownership stays below `1e-15 J`; storage-versus-flux error below
`1e-11 J`; cumulative reel angular defect below `1e-8 N m s` and
reel/combined energy defects below `1e-7 J`. These are numerical software
gates, not physical mill tolerances.

Local Python 3.12 observations for the accepted synthetic fixture:

| Cells | Steps | First-hit time (s) | Max reel energy defect (J) | Max stored-vs-flux defect (J) |
|---:|---:|---:|---:|---:|
| 64 | 96 | `0.04999999842775571` | `5.65e-13` | `5.64e-13` |
| 128 | 188 | `0.04999999942979792` | `1.43e-13` | `1.42e-13` |
| 256 | 376 | `0.04999999984096546` | `3.31e-14` | `3.56e-14` |

Independent high-precision anchors are `Uremain(0)=9.99333882833809e-9 J`,
`Uremain(.025)=1.25010394807282e-9 J`,
`ell(.05)=0.994000999000999001 m`,
`omega(.05)=-1.182439458145486028 rad/s`, and
`theta(.05)=-0.05908969694360247305 rad`. Over `[0,.05]`,
drive work is `-1.32084142187743e-5 J`, advected kinetic energy is
`-4.32216179890124e-6 J`, advected strain energy is
`-9.99333882833809e-9 J`, and traction work is
`-3.00049983338333e-5 J`. These are synthetic exact references.

The matched reaction release has no extra transition work. It is not a
general winding-release law. Imposing stored stretch, an independently
driven reel speed and the outgoing elastic characteristic simultaneously
would overconstrain a subsonic port without an additional transition
model. Actual reversal, incompatible initial states, pickup impulses and
post-zero slack/contact remain separate gates. No material calibration,
physical measurement validation or operational qualification is claimed.

[Lee, Leok and McClamroch's primary elastic string/reel analysis](https://ccom.ucsd.edu/reports/UCSD-CCoM-09-01.pdf)
uses a distinct inextensible wound side and derives a retrieval loss term;
its sign cannot simply be reversed into a retained-strain release law.
[Singh and Hanna](https://arxiv.org/abs/1611.03332) likewise analyze
admissibility at moving string discontinuities without validating this
synthetic cold-rolling boundary.
