# T2A shaft, span and prescribed-flow reel benchmarks

**Status:** seven restricted benchmarks are executable:
[T2A1](../physicroll/transient_t2a1.py) for fixed-inertia shafts and a
massless elastic span, [T2A2](../physicroll/transient_t2a2.py) for a
fixed-material elastic bar coupled to shafts,
[T2A3](../physicroll/transient_t2a3.py) for prescribed flow through
variable-mass reels, [T2A4](../physicroll/transient_t2a4.py) for an
inextensible torque-driven moving web, and
[T2A5](v1-transient-T2A5-design.md) for a distributed moving elastic span
with characteristic-compatible fixed ports, and
[T2A6](v1-transient-T2A6-design.md) for append-only retained winding strain
with a reaction reel, and [T2A7](v1-transient-T2A7-design.md) for a bounded
two-way torque-driven elastic span/reel case. T2A1 predicts shaft motion and
locates its first tension-zero event; T2A3 calculates reaction torques for
prescribed motion; T2A4 predicts speed but treats tension as an
inextensibility constraint reaction. T2A5 predicts nonuniform stretch and
velocity with material crossing both fixed ports, but neither reel is
dynamically coupled. T2A6 uses an analytic outgoing wave as a prescribed
port; its torque is a reaction, and it does not solve the discrete T2A5
field and reel together. T2A7 couples an evolving strain field and reel only
for a taut ideal append-only episode with manufactured torque; it has no
release/reversal or slack continuation. The fixed-end bar pulse and broader
transition/interface benchmarks remain design candidates. None of these
subsets has public RunSpec/restart integration, roll bite or contact. They do
not complete full moving-web T2 or qualify a mill.

The fixed-material stages test dynamic and coupling machinery needed by the
[T0 design](v1-transient-T0-design.md) without silently applying fixed-inertia
equations to T1's changing reels. Positive strip tension defines the taut
domain. T2A1 locates its first zero; the other subsets do not resolve a
general tension-loss event. Shaft angles are unwrapped
perturbations from the equilibrated initial configuration. Positive `θ1`
releases strip from the left and positive `θ2` takes up strip on the right:
`θ1 = −Δθ_left_winding` and `θ2 = Δθ_right_winding` relative to T1's
winding-positive reel angles. Endpoint displacements are `u_left=R1 θ1` and
`u_right=R2 θ2`, so the extension perturbation is `u_right−u_left`.
In the fixed-geometry T2A1/T2A2 cases, radius `R_i`, inertia `J_i`, span
length `L`, area `A`, modulus `E`, and nonnegative viscous shaft loss `b_i`
are constant. T2A3's changing radius and inertia have separate equations
below.

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
reversal, and slack behavior must be frozen before implementing a general
torque-driven coupled-reel solver. The prescribed-flow T2A3 subset fixes
only its declared constant-stretch transfer. [Yan (2020)](https://www.intechopen.com/chapters/68827) provides a
published web/reel model and span continuity relations under its stated
small-strain/no-slip assumptions, but its written `d(Jω)/dt` reel equation
does not explicitly show this angular-momentum flux. The reference above
is an independent control-volume derivation, not an adoption of that
published reel equation.

### Frozen prescribed-flow two-reel oracle (T2A3)

This restricted reference couples a translating taut span to two
variable-mass reels in a restricted prescribed-motion setting. It checks
mass ownership, angular-momentum flux, reaction drive torques and energy
transfer before a torque-driven moving-web solver is attempted. It does not
predict speed or tension. Both reel angles are positive in the direction of
left-to-right strip transport, so the left angle is the negative of T1's
locally winding-positive left angle.

Let `S` be a reference material label, `x(S,t)=λS+Vt`, and the fixed
spatial span be `0≤x≤L`. Its moving material boundaries are
`S_a=−Vt/λ` and `S_b=(L−Vt)/λ`; `q=V/λ` reference metres per second and
`ṁ=μ0 q` kg/s cross each port. The left reel loses `qt` reference metres,
the right gains the same amount; the span always owns `μ0L/λ` kg.
Declare the one-dimensional stored energy per reference metre
`W(λ)=½EA0(λ−1)²`, hence `T=dW/dλ=EA0(λ−1)`. All wound layers retain
this same stretch. At constant width and density, current strip thickness
is `h0/λ`; transfer has matching tangential speed `V=R_iω_i` and no
stretch change, slip, velocity capture loss or extra elastic transfer work.

For signed inventory rates `s_1=−q`, `s_2=+q`, core radius `Rc`,
`κ=h0/π`, and `μ0=ρ0A0`, each reel has

```text
L_i(t) = L_i(0) + s_i t
R_i² = Rc² + κ L_i
J_i = Jcore + μ0 [Rc² L_i + κ L_i²/2]
ω_i = V/R_i                 ω̇_i = −V κ s_i/(2 R_i³)
φ_i(t)−φ_i(0) = 2V [R_i(t)−R_i(0)]/(κ s_i).
```

For `s_i=0`, the angle limit is `Vt/R_i(0)`. The left reel's tension
torque is `+R_1T`, the right reel's is `−R_2T`. Angular-momentum flux
`μ0s_i R_iV` cancels `J̇_iω_i` for matched surface speed. The required
**reaction** drive torques are therefore
`τ_1=J_1ω̇_1−R_1T` and `τ_2=J_2ω̇_2+R_2T`. Each reel's kinetic energy
`K_i=½J_iω_i²` and stored winding energy `U_i=W L_i` obey

```text
K̇_i + U̇_i = τ_i ω_i + τ_T,i ω_i +
             s_i (½ μ0 V² + W).
```

The moving-span mass, momentum and total energy are constant; its two
traction powers and two advected energy fluxes cancel. Summing the whole
strip/reel system cancels the opposite reel fluxes and `+TV/−TV` tension
powers, leaving `Ḣ=τ_1ω_1+τ_2ω_2`. Test each reel's angular-momentum
and energy residual separately as well as this total identity, since only
checking the sum could hide opposite sign errors.

Freeze the SI example `λ=1.001`, `V=0.1`, `L=1`, `E=10⁷`, `A0=10⁻⁴`,
`ρ0=1000`, `w=0.1`, `h0=0.001`, `Rc=0.1`, `Jcore=0.01`, initial
`(L_1,L_2)=(10,1)` reference metres, and `0≤t≤2 s`. Thus `μ0=0.1`
kg/m, `T=1 N`, `W=0.0005 J` per reference metre, and
`q=0.09990009990009992 m/s`. At `t=2 s`, independent formula evaluation
gives `L_1=9.8001998001998 m`, `L_2=1.1998001998002 m`,
`R_1=0.11454038799908096 m`, `R_2=0.10189164963352833 m`,
`ω_1=0.8730544897473402 rad/s`, `ω_2=0.9814346942037745 rad/s`,
`τ_1=−0.11451782087351982 N m`, and
`τ_2=0.10187478146045989 N m`. Future code must also check the `t=0`
and `t=1 s` anchors, interval fluxes, angles and parcel ownership. Further
anchors are `R_1(0)=0.11481767660877792 m`,
`R_2(0)=0.10157908193217634 m`,
`R_1(1)=0.1146791161127821 m`,
`R_2(1)=0.10173548582285703 m`,
`φ_1(1)=0.8714718738690714 rad`,
`φ_2(1)=0.9836973425385772 rad`,
`φ_1(2)=1.7439979740144906 rad`, and
`φ_2(2)=1.9658847094223544 rad`, with zero initial angles.
Each second transfers `0.09990009990009992` reference metres and
`0.009990009990009992 kg` between reel and span ports. Compare closed
formula values at `t=0,1,2 s` within `10⁻¹² m` for radius and inventory,
`10⁻¹⁰ rad` for angle, `10⁻¹⁰ rad/s` for speed and `10⁻⁹ N m` for
reaction torque. Require signed mass-flux balance within `10⁻¹² kg`
per one-second interval and per-reel angular-momentum and mechanical-energy
balance residuals below `10⁻¹⁰ N m s` and `10⁻¹⁰ J` for every accepted
interval on `Δt=0.04,0.02,0.01 s`. Record the corresponding summed energy
residual; do not substitute it for either per-reel check. These tolerances
are frozen software checks of the idealized reference, not accuracy limits
for a real winding line. Enforce nonnegative inventory; reel capacity is
unassessed in this benchmark. Zero-speed and reversal are separate gates.
The ideal ports omit bending
energy, compaction, radial deformation, changing tangent/wrap-path mass and
support work; these formulas do not validate a physical winding line.

### Frozen inextensible torque-driven reference (T2A4)

This restricted stage lets common strip speed be a predicted
state while retaining a fixed spatial span and inextensible, constant-density
material. Tension is a constraint reaction, not a constitutive prediction.
The two reel axes are fixed; material flows left to right with `V>0` and
both reel angles transport-positive. Let transferred reference length `q`
obey `q̇=V`; `L_1=L_1(0)−q` and `L_2=L_2(0)+q`. The span owns
`m_s=μL` once; the reels own wound inertia through the annular `J_i(q)`
above. Use the same ideal no-slip ports and omit bending, compaction,
changing wrap-path inventory and losses. Terminate before inventory
exhaustion, nonpositive speed or tension, or reversal. Capacity is
unassessed. This stage does not model evolving strain.

Because equal-velocity inlet/outlet momentum fluxes cancel for the fixed
span, `m_s V̇=T_2−T_1`. For each reel the material angular flux cancels
`J̇_iω_i`, leaving `J_1ω̇_1=τ_1+R_1T_1` and
`J_2ω̇_2=τ_2−R_2T_2`, with `ω_i=V/R_i` and
`Ṙ_i=(h0/π)(±V)/(2R_i)`. Eliminating tensions gives

```text
M(q) = m_s + J_1/R_1² + J_2/R_2²
M(q) V̇ + ½ M'(q) V² = τ_1/R_1 + τ_2/R_2.
```

The independent dynamic oracle uses the kinetic-energy integral
`V(q)²=[M(0)V0²+2∫(τ_1/R_1+τ_2/R_2)dq]/M(q)` and scalar quadrature
`t(q)=∫dq/V(q)`. It must not supply the numerical ODE's velocity update.
The first fixture sets `μ=0.1 kg/m`, `h0=0.001 m`, `Rc=0.1 m`,
`Jcore=0.01 kg m²`, span length `L=1 m`, initial reel lengths
`(10,1) m`, `V0=0.1 m/s`, and terminal `q=0.2 m`. Opposing
position-dependent torques are `τ_1=−(1 N)R_1(q)` and
`τ_2=(1 N)R_2(q)`; their net drive power is zero. Thus
`V(q)=V0 sqrt(M(0)/M(q))`. Independent high-precision quadrature gives
terminal `t=2.00023193699641217 s`, `M=2.80672012521324316 kg`,
`V=0.09997699682837918 m/s`,
`V̇=−0.00001121901573108618 m/s²`,
`T_1=1.00017889011892767 N`, and `T_2=1.00017776821735456 N`.
Verify positive tension over the full interval, not just at the endpoint.

The frozen software acceptance is: integrate
`q̇=V`, `V̇=−M'(q)V²/(2M(q))` with RK4 at maximum steps
`0.04,0.02,0.01 s`, shortening and reintegrating the final step to
`q=0.2 m`. At every accepted state, compare speed with the independent
energy oracle. Require maximum speed error `≤10⁻¹⁰ m/s`, terminal-time
error `≤10⁻⁸ s`, terminal-`q` error `≤10⁻¹² m` and recovered tension
error `≤10⁻⁸ N`. The total kinetic-energy defect divided by initial
kinetic energy must be `≤10⁻⁹`. Independently integrate each reel's
angular-momentum and kinetic-energy flux, plus span momentum and kinetic
energy, over every accepted interval; require residuals below
`10⁻¹⁰ N m s`, `10⁻¹⁰ J`, `10⁻¹⁰ N s` and `10⁻¹⁰ J`, respectively.
The ledger integrals use separate time quadrature, not endpoint identities
as their own right-hand sides. Record three-resolution error trends until
roundoff dominates; strict decrease at machine precision is not required.
Reject nonfinite state, nonpositive inventory/speed/tension and unresolved
terminal event. Passing this inextensible constraint benchmark will not
complete strain-bearing T2, slack/reversal or T3 contact.

Local Python 3.12 observations for the frozen fixture (software residuals,
not physical errors) are:

| Maximum step (s) | Max speed-oracle error (m/s) | Scaled total-energy defect | Max left-reel angular-impulse residual (N m s) |
|---:|---:|---:|---:|
| 0.04 | `4.16e-17` | `7.42e-16` | `7.35e-18` |
| 0.02 | `5.55e-17` | `9.89e-16` | `6.92e-18` |
| 0.01 | `5.55e-17` | `1.36e-15` | `7.04e-18` |

These differences are already at floating-point roundoff; they do not show
meaningful monotonic refinement. The independent terminal-time quadrature
and all three-grid subsystem thresholds remain the actual acceptance checks.
