# T2A5 distributed moving elastic-span benchmark

**Status: frozen synthetic verification case, implemented and independently
reviewed for equation/sign scope.** This is
the next restricted T2 stage after the inextensible T2A4 benchmark. It solves
distributed stretch and velocity on a fixed spatial span while material
crosses both ends. It does not predict reel motion, winding transitions,
rolling contact or a physical mill response.

## Continuum and ownership

Let `S` label reference material, `x(S,t)` be position, `lambda=x_S>0`,
`v=x_t`, `mu0=rho0*A0` be mass per reference metre, and
`W(lambda)=EA0*(lambda-1)^2/2` be stored energy per reference metre. The
synthetic law has `T=W'=EA0*(lambda-1)` and reference wave speed
`c0=sqrt(EA0/mu0)`. On the fixed span `0<x<L`, reference-length density
`a=1/lambda` and momentum per current metre `p=mu0*a*v` obey

```text
a_t + (a*v)_x = 0
p_t + (p*v-T)_x = 0
e = p*v/2 + a*W(1/a)
e_t + [v*(e-T)]_x = 0.
```

Thus the boundary balances for mass, momentum and energy are, respectively,
`dM/dt=-[mu0*a*v]`, `dP/dt=-[p*v-T]`, and
`dH/dt=-[v*(e-T)]`, where `[f]=f(L)-f(0)`. A moving port of spatial
speed `b` substitutes `v-b` only in its advective flux. Material labels
obey `S_x=a`, `S_t=-a*v`; for each fixed endpoint,
`dS_cut/dt=-(a*v)_port`. The two port fluxes are independent: changing span
strain changes its material inventory.

The first solver uses conservative finite volumes with monotone piecewise
linear reconstruction, a Rusanov interface flux, and two-stage SSP Runge–
Kutta time integration. It reports the **numerical** boundary flux used by
the conservative update separately from the **physical** characteristic-port
flux. Physical port energy is split into advected kinetic energy, advected
stored strain energy and traction work, with signed net flux equal to the
first two minus the third. Mass and momentum must close to roundoff; elastic
energy lost by numerical diffusion is reported as a defect and must decrease
on refinement. No clipping of negative tension is allowed. A trial outside
positive stretch and tension fails. The accepted step obeys a declared CFL
limit of `0.35`, checked from reconstructed interface states at both Runge–
Kutta stages. This is an algorithm setting, not an empirical limit.

## Exact characteristic-compatible case

The independent reference is the finite-amplitude material-coordinate wave

```text
x(S,t) = lambda0*S + V*t + A*sin(k*(S-c0*t))
lambda(S,t) = lambda0 + A*k*cos(k*(S-c0*t))
v(S,t) = V - A*k*c0*cos(k*(S-c0*t)).
```

Use `L=1 m`, `mu0=0.1 kg/m`, `EA0=10 N`, `c0=10 m/s`,
`lambda0=1.001`, `V=0.1 m/s`, `k=5*pi rad/m`, and
`A*k=1e-4`, over `0<=t<=0.08 s`. Hence `lambda>=1.0009`,
`v>=0.099 m/s`, and `T>=0.009 N`. Invert the strictly increasing `x(S,t)`
at each spatial point independently for the exact reference. At the left
port prescribe only the incoming right-running invariant
`v-c0*lambda` from that exact wave. At the right port prescribe only the
incoming left-running invariant `v+c0*lambda=V+c0*lambda0`.
The outgoing invariant at each port comes from the computed interior state.
Both ends are subsonic (`|v|<lambda*c0`). These incoming histories are
synthetic boundary data, not reel predictions.

Initialize each cell with quadrature of the exact conservative fields. At
`t=0`, `0.04`, and `0.08 s`, compare to independently quadrature-integrated
exact cell averages, material-label cuts, span mass/momentum/energy, and
separately integrated left/right physical fluxes. Two cut estimates are
recorded: one integrates the numerical mass flux and telescopes exactly with
the finite-volume inventory; the other integrates physical characteristic-
port `a*v` separately, so its inventory mismatch must decrease on
refinement. This is a fixed spatial span with changing material labels;
moving spatial port geometry is not implemented.
Use 64, 128 and 256 uniform cells, resolving the time step by the stated
CFL limit. Smooth-field normalized RMS errors for `lambda` and `v` use
`1e-4` and `c0*1e-4`, respectively; require a decrease on both refinements
and at most `5%` at 256 cells. Require each material-cut error at most
`5e-4 m` at the finest grid and decreasing with refinement. Discrete mass
and momentum closure must be below `1e-10 kg` and `1e-10 kg m/s`. The
maximum absolute mechanical-energy defect **over accepted steps**, divided
by the initial total energy, must be below `1e-3` at the finest grid and
decrease on refinement. Physical left/right port-integral errors must each
stay below `1e-6 reference m`, `1e-6 N s` and `1e-7 J` for reference flux,
impulse and net energy. Independent kinetic, strain and traction-work
integrals must each agree within `1e-8`, `1e-9` and `1e-7 J`, respectively.
These bounds reject a missing strain-energy term. This energy defect measures
numerical dissipation, not material dissipation or physical accuracy.
At 128 cells, repeat with CFL limits `0.35`, `0.175` and `0.0875`; the
normalized final stretch/velocity difference between successive temporal
grids must decrease. Report actual errors at all three spatial grids; do
not infer order from a discontinuous event.

The separate **zero-mean-transport** preloaded-wave case must retain wave
motion and positive tension. Its local material flux changes sign; this is
not a reel reversal test. A uniform translation case must preserve exactly
constant stretch and velocity. Reel reversal, first tension zero and
contact-loss continuation remain explicit gates.

Local Python 3.12 observations for the accepted moving-wave fixture are
software errors against this exact synthetic wave, not mill accuracy:

| Cells | Steps | Normalized stretch RMS | Normalized velocity RMS | Maximum cut error (m) | Maximum scaled energy defect |
|---:|---:|---:|---:|---:|---:|
| 64 | 150 | `0.031643` | `0.031651` | `7.48e-8` | `1.15e-5` |
| 128 | 300 | `0.010179` | `0.010172` | `1.61e-8` | `2.10e-6` |
| 256 | 598 | `0.003225` | `0.003228` | `3.01e-9` | `4.26e-7` |

The largest reconstructed-stage Courant number was `0.346501` or less on
all three grids. The 256-cell Python run took about `2.7 s` locally for
the solver before the independent test oracle was evaluated. This time is
an observed software measurement, not a delivery forecast.

## Reel-transfer gate after this benchmark

For each reel, reference inventory `ell` owns its mass and wound strain
energy `U_wound=int_inventory W(lambda_w(S),z(S)) dS`. The annular idealization
retains `R^2=Rc^2+h0*ell/pi` and
`J=Jcore+mu0*(Rc^2*ell+h0*ell^2/(2*pi))`, with signed inward reference
flux `s` and `J_dot=mu0*R^2*s`. The full angular balance is
`d(J*omega)/dt=tau_drive+tau_tension+tau_loss+mu0*s*R*v_theta`.
The ideal cancellation to `J*omega_dot` applies only if `v_theta=R*omega`.
With strain-matched lossless transfer, the wound energy ledger is

```text
d(K+U_wound)/dt = (tau_drive+tau_tension)*omega
                   + s*(mu0*v_theta^2/2 + W_transfer).
```

This reel ledger is a **design gate**, not an implemented T2A5 capability.
Wound intervals need ordered material labels and retained stretch/history.
Unwinding exposes the outer interval first. A stored-release stretch that
conflicts with the one incoming elastic characteristic and reel boundary
relation must cause an explicit incompatibility event until a reviewed
transition law supplies its impulse, work and dissipation. A stationary
preloaded span is taut; reversal switches the material-history donor at a
localized zero-flux event but does not switch elastic characteristic rules.
The first taut model stops at the first zero-tension event; slack continuation
requires additional geometry and a capture law. T2/T3 domains must exchange
the same accepted velocity/traction, material flux and history, and cancel
interface impulse and work without duplicate mass or compliance.

The equations and boundary restrictions were independently reviewed before
implementation. Primary treatments of material transport in nonmaterial
domains include [Steinboeck, Saxinger and Kugi](https://doi.org/10.1115/1.4042434)
and [Vetyukov](https://doi.org/10.1016/j.jsv.2017.11.010). Primary moving-
discontinuity analyses by [Hanna](https://arxiv.org/abs/1406.5175) and
[Singh and Hanna](https://arxiv.org/abs/1611.03332) motivate explicit
interface momentum/energy closure. Those papers do not validate this
synthetic elastic span or provide a cold-rolling winding law.
