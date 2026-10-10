# T2A6 append-only reaction reel benchmark

**Status: frozen synthetic verification design, implemented and independently
reviewed for its restricted scope.** This
stage takes the outgoing elastic wave at T2A5's fixed right port and winds
it onto one ideal variable-radius reel. The right port's incoming elastic
characteristic remains the prescribed T2A5 value; reel speed and required
torque are reactions to the outgoing span state. No reel torque is imposed
back on the span. This is a one-way, append-only benchmark, not complete
torque-driven strain-bearing T2 or a winding/contact model.

## Transfer and ownership

At `x=L=1 m`, use the T2A5 exact wave with `mu0=0.1 kg/reference m`,
`EA0=10 N`, `lambda0=1.001`, `V=0.1 m/s`, `c0=10 m/s`,
`delta=1e-4`, and `k=5*pi rad/reference m`. Its boundary state
`lambda(t),v(t)>0` has reference flux `q=v/lambda>0`, tension
`T=EA0*(lambda-1)>0`, and moving material cut `S_b_dot=-q`. A new layer
retains the stretch it had at transfer. Its tangential velocity matches the
reel surface, `v=R*omega`; the ideal transfer has no separate strain or
velocity jump and no capture loss. The reel adds no second span boundary
condition. It reports the drive torque required to follow this prescribed
port state, rather than predicting speed from an applied torque.

Set core radius `Rc=0.1 m`, initial wound reference length `ell0=1 m`,
reference thickness `h0=0.001 m`, core inertia `Jc=0.01 kg m²`, and
`kappa=h0/pi`. The ideal fixed-width, incompressible-volume annulus has

```text
ell_dot = q
R² = Rc² + kappa*ell
J = Jc + mu0*(Rc²*ell + kappa*ell²/2)
R_dot = kappa*q/(2R)
omega = v/R
alpha = v_dot/R - v*R_dot/R²
tau_drive = J*alpha + R*T.
```

The last relation follows from
`d(J*omega)/dt=tau_drive-R*T+mu0*q*R*v` and
`J_dot=mu0*R²*q`; record the unreduced open-system balance as a separate
check. Signed drive torque and work may be regenerative.

The initial wound interval is `[S_b(0),S_b(0)+ell0]` and has a constant
declared stretch equal to the **actual initial right-port stretch**, about
`1.0009000123`. This matches the outer surface at `t=0`; a base stretch of
`1.001` would be an inconsistent initial transfer state. Each subsequent
accepted interval `[S_b(t_next),S_b(t_previous)]` is appended in core-to-
outer order, so material labels decrease outward. Store its lower/upper
labels, endpoint deposition stretches, mass and retained strain energy.
Linear interpolation of stretch in material label gives interval energy
`EA0*DeltaS*(e_low²+e_low*e_high+e_high²)/6`, where `e=lambda-1`.
Existing intervals are immutable. This interpolation is a declared
numerical representation, not an assumption that all wound layers share
the current span stretch.

With `U_wound=sum W(lambda_w(S)) dS` and `K=J*omega²/2`, separately check

```text
Delta(J*omega) = integral (tau_drive-R*T+mu0*q*R*v) dt
Delta(K+U_wound) = integral [tau_drive*omega-T*v
                          +q*(mu0*v²/2+W(lambda))] dt.
```

Also compare the stored-energy increment from the ordered intervals with
an independently integrated `q*W` time flux. Preserve initial and
deposited stored energy separately. Reject nonpositive `q`, tension or
inventory, nonfinite values and any requested release/reversal. A mismatch
at an unwinding port needs a reviewed transition law and explicit work;
this case does not implement one. Changing tangent/wrap-path geometry,
bending, compaction, radial deformation and relaxation of already wound
layers are excluded. Elastic waves can reach a stationary taut span without
triggering a slack event.

## Independent references and acceptance

Use maximum steps `0.0005`, `0.00025`, `0.000125 s` through `0.08 s`,
giving 160, 320 and 640 append intervals. Observe `0`, `0.005`, `0.02`,
`0.04`, `0.08 s` at accepted steps. Integrate `q` and each open-system
ledger with time Simpson quadrature. The stored interval energy uses its
material-label interpolation formula, **not** the time flux integral.
Compare inventory/radius/inertia, angular momentum, angle, energy and
separate work/flux terms against a material-coordinate reference.

For that independent reference, let `B=V+c0*lambda0=10.11 m/s` and
`phi=k*(S_b-c0*t)`. At fixed right position, `phi` uniquely solves
`lambda0*phi/k+(delta/k)*sin(phi)+B*t=1`. Then
`lambda=lambda0+delta*cos(phi)`, `v=V-c0*delta*cos(phi)`,
`dell/dphi=-v/(k*B)`, and
`v_dot=-c0*delta*k*B*sin(phi)/lambda`. The exact cut gives
`ell(t)=ell0+S_b(0)-S_b(t)`. An independent antiderivative for deposited
energy is

```text
P(phi)=EA0/(2*k*B)*[
  a0*phi + a1*sin(phi) + a2*(phi/2+sin(2*phi)/4)
  + a3*(sin(phi)-sin(phi)^3/3)]
a0=V*e0²
a1=2*V*e0*delta-c0*delta*e0²
a2=V*delta²-2*c0*e0*delta²
a3=-c0*delta³; e0=lambda0-1.
U_deposited(t)=P(phi(0))-P(phi(t)).
```

The independent angle reference integrates
`v(phi)*lambda(phi)/(k*B*R(phi))` from `phi(t)` to `phi(0)` using the
exact material-cut inventory, not numerical time-integrated `q`.
The first `0.005 s` is a discriminating energy interval: expected deposited
energy is about `2.0905e-9 J`, roughly 17% below falsely retaining every
new layer at base stretch `1.001`. Require its deposited-energy relative
error at most `0.2%` on the coarsest grid and improvement on refinement.
At `0.08 s`, require deposited-energy absolute error below `1e-11 J`,
decreasing on refinement. Require decreasing per-step angular-impulse and
energy-ledger defects; also require maximum cumulative reel angular-impulse
residual `<=1e-10 N m s`, cumulative energy residual `<=1e-10 J`, and
stored-energy-versus-time-flux difference `<=1e-11 J`. At every listed
snapshot, compare independent anchors within `1e-11 m` for inventory and
radius, `1e-12 kg m²` for inertia, `1e-9 rad/s` for speed,
`1e-8 rad/s²` and `1e-8 N m` for acceleration and reaction torque, and
`1e-9 rad` for angle. Check drive work, traction work and advected kinetic
energy separately to `1e-8 J` against independent reference integrals;
their cancellation alone is insufficient. Require exact core-to-outer
adjacency, unchanged old intervals, and mass `mu0*DeltaS` for every
interval. Event/reversal and
release checks must reject before changing committed interval ownership.
These are synthetic software tolerances, not physical winding accuracy.

Local Python 3.12 observations of the bounded implementation are below.
The errors refer to the synthetic analytical port and do not measure mill
accuracy:

| Step (s) | Appended intervals | Early deposited-energy relative error | Max cumulative angular defect (N m s) | Max cumulative energy defect (J) | Max stored-vs-flux defect (J) |
|---:|---:|---:|---:|---:|---:|
| `0.0005` | 160 | `1.03e-4` | `2.98e-12` | `2.94e-12` | `4.79e-13` |
| `0.00025` | 320 | `2.57e-5` | `1.86e-13` | `2.12e-13` | `1.20e-13` |
| `0.000125` | 640 | `6.43e-6` | `1.17e-14` | `2.60e-14` | `3.00e-14` |

The reel inventory from integrated time flux is compared with the sum of
retained material-label intervals; their difference is recorded separately.
The accepted finest solver run took about `0.023 s` locally, excluding the
independent test oracle.

This stage's port/flux closure follows the independently reviewed
[T2A5 formulation](v1-transient-T2A5-design.md). Moving-discontinuity
balance requirements are informed by [Hanna](https://arxiv.org/abs/1406.5175)
and [Singh and Hanna](https://arxiv.org/abs/1611.03332); those inextensible
studies do not supply an elastic reel-contact law or physical validation.
