# T2A fixed-geometry shaft and elastic-span benchmark candidate

**Status:** the independently reviewed, fixed-inertia massless-span **T2A1**
benchmark is executable in `physicroll/transient_t2a1.py`; the restricted
fixed-material bar/shaft **T2A2** benchmark is executable in
`physicroll/transient_t2a2.py`. T2A1's torque-driven
midpoint states, analytic first-zero event detection, prescribed-motion
reaction torques and work diagnostics pass closed-form checks. The fixed-end
bar pulse and partitioned-coupling cases remain design candidates; neither subset
has public RunSpec/restart integration. T2A is a closed local perturbation
problem. It has no material entering/leaving the span, changing reel radius,
running-web inventory, roll
bite or strip contact. Passing it will not complete T2 or qualify a mill.

This restricted stage tests the dynamic and coupling machinery needed by the
[T0 design](v1-transient-T0-design.md) without silently applying fixed-inertia
equations to T1's changing reels. Positive strip tension defines the taut
domain; its first zero is a terminal event. Shaft angles are unwrapped
perturbations from the equilibrated initial configuration. Positive `θ1`
releases strip from the left and positive `θ2` takes up strip on the right:
`θ1 = −Δθ_left_winding` and `θ2 = Δθ_right_winding` relative to T1's
winding-positive reel angles. Endpoint displacements are `u_left=R1 θ1` and
`u_right=R2 θ2`, so the extension perturbation is `u_right−u_left`.
Radius `R_i`, inertia
`J_i`, span length `L`, area `A`, modulus `E`, and nonnegative viscous shaft
loss `b_i` are constant within one case.

## Massless-span reference

Let `e = e0 + R2 θ2 − R1 θ1`, `k = EA/L`, and `T = k e` while `e > 0`.
For applied torques `τ1, τ2`, the equations are

```text
J1 θ̈1 = τ1 + R1 T − b1 θ̇1
J2 θ̈2 = τ2 − R2 T − b2 θ̇2
```

An initial static tension `T0 = k e0` requires balancing torques
`τ1 = −R1 T0` and `τ2 = +R2 T0`. Prescribed-speed mode computes the torque
reaction from these same equations; speed and torque cannot be independent
inputs to the same shaft. Torque-driven mode predicts angle and speed. The
energy `H = ½ J1 θ̇1² + ½ J2 θ̇2² + ½ k e²` obeys

```text
dH/dt = τ1 θ̇1 + τ2 θ̇2 − b1 θ̇1² − b2 θ̇2².
```

The undamped homogeneous system has one rigid mode and one elastic frequency
`ω² = k (R1²/J1 + R2²/J2)`. This frequency, energy law and exact uncoupled
constant-torque shaft solution are independent references for implementation.
For event checking, `θ1=0`, `θ2=−v t/R2`, `e0=0.01 m` and `v=0.02 m/s`
give the first taut-span loss at exactly `0.5 s`; no compressive solution is
accepted afterward. That prescribed example verifies reaction torque and
event handling, not torque-driven motion.

## Massive-span reference

The next T2A case replaces the spring with a small-strain one-dimensional bar:

```text
ρ A ü = ∂x(E A ∂x u),       c = sqrt(E/ρ).
```

Here `u` is displacement about a preloaded equilibrium, with
`u(0,t)=R1 θ1` and `u(L,t)=R2 θ2` when coupled to shafts. Total tension is
`T0 + EA ∂x u`; its first zero **anywhere** ends the taut-bar episode.
End tractions on the shafts have equal and opposite power to the bar boundary
work. Bar mass belongs only to the span; the constant shaft inertias exclude
it. A positive declared preload must exceed the pulse's negative tension
excursion. A d'Alembert pulse and its transit/reflection times are the
independent reference; a massless spring cannot satisfy this test.
The first bar comparison uses `L=1 m`, `E=100 kPa`, `ρ=1000 kg/m³` and
`A=0.01 m²`, so `c=10 m/s` and the first end-to-end transit is `0.1 s`.
For the independent fixed-end pulse, `u(0,t)=u(L,t)=0`, `u_t(x,0)=0`, and
`u(x,0)=a sin²(π(x−0.2)/0.4)` for `0.2≤x≤0.6 m`, zero elsewhere, with
`a=10⁻⁵ m` and `T0=1 N`. The maximum initial tension perturbation is
`EA π a/0.4 < 0.08 N`. The oracle is
`u(x,t)=[f(x−ct)+f(x+ct)]/2`, with `f` the odd `2L`-periodic extension
of the stated initial displacement. It includes fixed-end reflected waves;
the right-going front first reaches the right end at `0.04 s` and the last
part at `0.08 s`. A coupled-shaft pulse is a separate interface case.

## Frozen comparison proposal

All figures here are **software design targets**, not accuracy estimates for
rolling. Freeze this table after independent review and before implementing
T2A; changes must be recorded before examining new results.

| Case | Independent oracle | Required observations |
|---|---|---|
| Single uncoupled shaft | `θ(t)=θ0+ω0 t+τ t²/(2J)` | angle, speed, work and kinetic energy |
| Balanced two-inertia span | `ω²=k(R1²/J1+R2²/J2)` and harmonic relative coordinate | rigid/elastic modes, amplitude, phase, energy |
| Both shafts prescribed | analytic sinusoidal displacement and derivatives | reaction torques, signed work, no double-imposed drive |
| First tension loss | `e=e0−vt` | event at `0.5 s`, empty post-event suffix |
| Elastic bar pulse | `c=sqrt(E/ρ)` and separately derived reflection | transit time, sign, amplitude and phase |
| Coupling | monolithic linear reference and partitioned iteration | interface impulse/work and convergence |
| Restart | direct accepted trajectory | identical state/event suffix at mid-step, knot and terminal cursors |

For the shaft cases use `J1=J2=1 kg m²`, `R1=R2=0.1 m`, `k=100 N/m`,
`e0=0.01 m`, and a requested `2 s` interval. The undamped mode frequency is
`sqrt(2) rad/s`; the balancing torques are `−0.1` and `+0.1 N m`.
Compare accepted `Δt=0.04, 0.02, 0.01 s`. Initialize the balanced oscillator
with `θ1=0`, `θ2=0.01/R2`, zero angular speeds and balancing torques for
`T0`, then compare against the closed harmonic solution around equilibrium.
For the uncoupled shaft use `J=1 kg m²`, `θ0=ω0=0`, `τ=1 N m`. For the
prescribed reaction case use `θ1=0.01 sin(2πt) rad`, `θ2=0` and analytic
derivatives. The tension-loss case stops at `0.5 s`.

For the bar use two-node linear elements, consistent mass and exact element
integration. The element/step pairs are `(16, 0.0015625 s)`,
`(32, 0.00078125 s)`, `(64, 0.000390625 s)`; each reaches `0.2 s` in
`128`, `256`, `512` accepted steps. Candidate finest-resolution targets are
`≤10⁻¹²` absolute angle/speed error for the uncoupled shaft,
`≤5×10⁻⁴` normalized RMS relative-coordinate error and `≤10⁻³ rad` phase
error for the oscillator, `≤10⁻⁹` scaled closed-system energy defect,
`≤10⁻⁴ s` first-zero event-time error, and `≤5%` normalized bar-displacement
and `≤10%` normalized bar-tension error against the d'Alembert field.
Errors must decrease over the three refinements where the oracle is smooth.
Review these software targets before coding; they imply no physical accuracy.

The first executable subset, **T2A1**, sets `b1=b2=0` and uses fixed radii,
inertias and a massless span only. Its torque-driven loss oracle has
`τ1=τ2=0`, `θ1=θ2=θ̇1=θ̇2=0` initially: the relative extension is
`e(t)=e0 cos(sqrt(2)t)` and first zero is `π/(2sqrt(2)) s`. Accept no state
with negative tension; a root residual above `10⁻⁹ N` or event-time error
above `10⁻⁴ s` fails the run. The prescribed-motion loss case at `0.5 s`
remains a separate reaction-mode test. For the analytic prescribed sinusoid,
compare reaction torques at every accepted time with `≤10⁻¹⁰ N m` absolute
error. Its midpoint-work quadrature defect must decrease over the three time
steps; the closed torque-driven energy target is not applied to it. Damping,
bar mass and partitioned iteration are outside T2A1. Any future partitioned
run must fail if its interface iteration does not converge; an unresolved
first-zero event likewise fails rather than accepting a compressive step.

For the oscillator, normalize RMS extension error by its `0.01 m` initial
perturbation and sample every accepted time in `[0,2 s]`. Extract endpoint
phase from `atan2(−ė/ω, e−e0)`, using the independently derived
`ω=sqrt(2) rad/s` and unwrapping to the reference phase interval. For the
fixed-end bar, compare displacement at all interior nodes and tension at all
element midpoints at `t=0.025, 0.05, 0.10, 0.15, 0.20 s`, using the exact
d'Alembert function and derivative. Normalize displacement RMS by `a` and
tension RMS by the **pulse perturbation** `EA πa/0.4`, not by the 1 N preload.
Exclude only points exactly on a pulse-support corner where the oracle's
second derivative is discontinuous; record excluded coordinates.

For undamped tests, the energy metric is the defect
`H(t)−H(0)−Σ Δt(τ1 θ̇1+τ2 θ̇2)_(midpoint)`, divided by the larger of
`H(0)`, the absolute accumulated input work and `10⁻¹² J`. Thus the balanced oscillator
is checked against external work, not assumed to have constant `H`.
Time-dependent prescribed motion is evaluated analytically at accepted
times; reaction work uses the same midpoint force/velocity quadrature and
reports its quadrature defect separately. In torque-driven mode, both
implicit midpoint and the linear average-acceleration Newmark candidate
sample applied torque at the interval midpoint. Equivalence is claimed here
only for unforced or constant-load linear cases; time-varying forcing needs
its discrete acceleration and load equations reviewed separately. All five
bar observation times above are accepted-step times for each listed grid,
so no frame interpolation enters the comparison.

For the first partitioned-coupling comparison, use the balanced massless-span
oscillator above (`b1=b2=0`, initial `θ2=0.1 rad`, other angle and both
speeds zero, constant balancing torques). A monolithic linear step is the
reference. Iterate interface tension and surface speed until consecutive
iterates differ by at most `10⁻¹⁰ N` and `10⁻¹⁰ m/s`; compare accepted
angles within `10⁻⁸ rad` and interface work within `10⁻⁸ J` at every
resolution. The monolithic massive-bar/shaft case uses the separately frozen
continuum reference below; partitioned massive-bar coupling remains gated.
The first integrator candidate is undamped implicit midpoint; a separate
average-acceleration Newmark formulation may be compared under the common
constant-load cases. Record the exact
discrete energy/work balance and observed convergence order. Trial budget is
`≤64` bar elements, `≤2000` accepted steps, `≤256 MiB` peak memory and
`≤60 s` wall time on one CI runner for this benchmark; these are candidate
limits to verify, not measured performance.

Before implementing the massive-bar and partitioned cases, independent review
must confirm their endpoint power transfer, pulse/reference data, spatial
tolerances and bar first-zero event rule. Broader T2 still requires a moving-span control volume,
variable-mass reel angular-momentum and energy flux, ownership of span/reel/
shaft mass and compliance, damping/slack transitions, and independent
variable-mass benchmark outputs. T3 retains its separate full 3D and dynamic
roll/stand gates.

## Frozen T2A2 coupled massive-bar reference (2026-10-10)

Independent formulation review selected a **fixed-material**, monolithic
bar-to-shaft comparison before any moving-span solver. This is T2A2, not a
claim of full T2. The bar owns its consistent mass; the two shafts contribute
only endpoint masses `m_i=J_i/R_i²`. With constant equilibrium tension `T0`,
balancing shaft torques are `(-R1 T0,+R2 T0)`. For perturbations `u` and
`δτ`, the continuum equations and endpoint conditions are

```text
ρA u_tt = EA u_xx
m1 u_tt(0) = δτ1/R1 + EA u_x(0)
m2 u_tt(L) = δτ2/R2 − EA u_x(L).
```

The perturbation energy is half the integral of `ρA u_t²+EA u_x²` plus
`½m1 u_t(0)²+½m2 u_t(L)²`; its rate equals
`δτ1 θ̇1+δτ2 θ̇2`. Bar and shaft interface powers cancel. Do not count
equilibrium balancing-torque work again in this perturbation ledger.

For zero perturbation drive, a continuum mode `U(x) cos(ωt)` has
`k=ω/sqrt(E/ρ)`, `z=kL`, and `μ_i=m_i/(ρAL)`. Its nonzero frequencies solve
`(1−μ1μ2 z²)sin(z)+(μ1+μ2)z cos(z)=0`, with mode shape
`U(x)=C[cos(kx)−μ1 z sin(kx)]`. A rigid translation is the zero mode.
For `L=1 m`, `E=100 kPa`, `ρ=1000 kg/m³`, `A=0.01 m²`,
`R1=R2=0.1 m`, `J1=J2=1 kg m²`, and `T0=1 N`, the first positive
root is `z=0.4435207878818884`, `ω=4.4352078788188845 rad/s`, and
one period is `1.4166608372937926 s`. Normalize the mode to maximum
displacement `10⁻⁶ m`; its analytic maximum tension perturbation is below
`0.0021 N`, so this benchmark stays taut. Initial velocity is zero.
Run one analytic period with linear elements and consistent mass at
`(elements, maximum step_s)=(16,0.003125),(32,0.0015625),
(64,0.00078125)`. The final fractional step lands exactly on the period.
These are design comparisons, not physical accuracy claims. At the finest
resolution require normalized RMS displacement error `≤3×10⁻³`, normalized
RMS perturbation-tension error `≤5×10⁻³`, endpoint angle error
`≤3×10⁻⁸ rad`, endpoint speed error `≤3×10⁻⁷ rad/s`, and phase error
`≤3×10⁻³ rad`, with decreasing field and phase errors over all three grids.
Require scaled perturbation-energy/work defect `≤10⁻⁹`, endpoint interface
**work** cancellation `≤10⁻¹² J` per step, and every accepted element tension
positive. Rigid translation must produce zero strain, constant velocity and
the combined mass `ρAL+m1+m2=210 kg` to `10⁻¹⁰` relative. Allow at most
64 elements, 2000 steps, 256 MiB and 60 s on one CI runner. A separately
bracketed scalar continuum root, not an assembled-matrix eigenpair, is the
frequency oracle. The older fixed-end pulse and partitioned tests remain
separate gates. The displacement RMS uses all nodes at every accepted time,
divided by `10⁻⁶ m`. The tension RMS uses element midpoints at those times,
divided by the continuum mode's maximum perturbation-tension magnitude
`EA×10⁻⁶×k sqrt(1+(μ1 z)²)`. The phase error is the wrapped difference
between `atan2(−u̇(0)/(ωa),u(0)/a)` and `ωt`, over accepted times. The
per-step interface-work residual sums the bar and shaft endpoint forces
times the same midpoint endpoint displacement increment. No fitted
frequency from the numerical trajectory is used as the oracle.

## Moving-material formulation gate

For a moving control surface with velocity `v_b`, outward mass flux is
`j=ρ(v−v_b)·n`. Its mass, linear-momentum and angular-momentum balances
contain outward fluxes `j`, `j v` and `j(r×v)`, respectively. Mechanical
energy must transport kinetic and recoverable strain energy and account for
traction/shaft power and dissipation. The angular-momentum origin is fixed
and inertial. A winding strip's incoming state therefore includes velocity
and strain/internal state, not only material identity.

A restricted **reel-only** check uses a constant-density annulus of width
`w`, core radius `Rc`, and outer radius `R`:
`J=Jcore+ρπw(R⁴−Rc⁴)/2` and `J̇=R² ṁ` for signed inward mass rate.
The open control-volume balance is
`d(Jω)/dt=τext+ṁ R vθ`. Ideal no-slip transfer `vθ=Rω` cancels the
`J̇ω` term, yielding `Jω̇=τext`. At constant `ω` and zero net external
torque, `d(½Jω²)/dt=½ṁ(Rω)²` checks kinetic-energy flux. This isolated
identity does not close the moving span or winding tension/compaction.
The moving material coordinate, boundary cuts, transfer strain, flow
reversal, and slack behavior must be frozen before implementing coupled
reels. [Yan (2020)](https://www.intechopen.com/chapters/68827) provides a
published web/reel model and span continuity relations under its stated
small-strain/no-slip assumptions, but its written `d(Jω)/dt` reel equation
does not explicitly show this angular-momentum flux. The reference above
is an independent control-volume derivation, not an adoption of that
published reel equation.
