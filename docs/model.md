# Process model contract, equations and limits

**All scenarios and material/plant parameters are synthetic. No calibration or accuracy claim.**
This is an executable, energy-accounted demonstration, not a validated slab solver.
The circular rolls are rigid and the strip is incompressible, isothermal and plane strain,
with constant width/density. A supplied mean uniaxial flow stress represents the entire
pass; it is not an alloy database, measured yield curve or implemented hardening law.

`Scenario.from_dict` rejects missing/unknown keys. `solve(Scenario)` validates again.
`schema/scenario.schema.json` documents JSON types and SI units; cross-field constraints
remain authoritative in Python. Full thickness is used everywhere (never half thickness).
Pa = N/m², N·m = torque, W = J/s, velocities = m/s, angular velocity = rad/s.
Tension inputs are positive longitudinal **stresses**, converted to forces at each gauge.

## Implemented equations

Symbols: entry/exit gauges h0,h1 [m]; width b [m]; radius R [m]; entry speed v0 [m/s];
density rho [kg/m³]; mean uniaxial flow stress sigma [Pa]; friction mu; entry/exit tension
stresses t0,t1 [Pa]; drive efficiency eta. Both work rolls are driven symmetrically.

| ID | Equation | Basis / status |
|---|---|---|
| G1 | d = h0 − h1; reduction = d/h0; e = ln(h0/h1) | Definitions |
| G2 | L = sqrt(R d − d²/4); alpha = atan2(L,R−d/2) | Exact geometry of two rigid circular rolls; tends to sqrt(R d) |
| G3 | h(x) = h1 + 2 x² / (R + sqrt(R²−x²)), −L ≤ x ≤ 0 | Same circle geometry; stable evaluation of sagitta |
| M1 | Q = b h0 v0 = b h1 v1; mass flow = rho Q | Incompressible constant-width continuity |
| C1 | K = 2 sigma / sqrt(3) | von Mises plane-strain stress difference for uniform ideal deformation |
| H1 | phi = mu L / ((h0+h1)/2); pbar = K(1+phi) − (t0+t1)/2 | **Author-defined heuristic pressure closure**, not integrated slab equilibrium |
| F1 | F = b L pbar | Uniform mean-pressure projected-area load; total separating force, not sum over both rolls |
| E1 | Pideal = Q K e; Pextra = Pideal phi | Ideal plastic work plus **heuristic nonnegative dissipation** |
| E2 | Ptension = Q(t1−t0) = T1 v1 − T0 v0 | Net external tensile power; Ti = ti b hi |
| E3 | Proll = Pideal + Pextra − Ptension; Pelectric = Proll/eta | Steady energy balance; electricity is roll drives only, excluding reels/auxiliaries |
| H2 | u = (v0+v1)/2; omega = u/R | **Assumed** roll surface speed, not a solved neutral point |
| E4 | torque per work roll = Proll/(2 omega) | Energy-equivalent torque proxy; equal sharing by two work rolls |
| D1 | assumed forward slip = v1/u − 1 | Diagnostic of H2 only; not independently predicted or fit-worthy slip |

These equations are explicitly implemented in `physicroll/model.py`. H1/H2 and the extra
loss in E1 are transparent demonstration closures, **not equations attributed to any
cited paper**. They couple outputs for offline exploration, but do not enforce a local
pressure/traction field. In particular E4 is not a signed-traction integral and no F·L/2
lever-arm approximation is used. A next mechanics revision must replace the load and torque
closures together with a tension-aware pressure/traction solution. Passing the present power
balance does not establish that a corresponding local traction field exists.

The ideal plastic work follows from equivalent plane-strain strain increment
`d(equivalent strain) = 2/sqrt(3) d(ln(h0/h))`. The constant mean stress is input, not fitted.
Both heuristic multipliers are dimensionless. In the zero-draft branch force/power/torque
are zero and tensions must be equal. Pressure is reported as zero for this unloaded
transport state; this is **not** a skin-pass/temper-rolling/contact-preload model.

## Rejection domain

* Finite numeric SI inputs only; booleans and numeric strings are rejected.
* Positive gauges, density, flow stress, radius, speed and width. No reverse/zero-speed operation.
* `0 ≤ reduction ≤ 0.5`, `h0/R ≤ 0.05`, `b/h0 ≥ 20`, `0 ≤ mu ≤ 0.3`, `0 < eta ≤ 1`.
* **Exit gauge ≥ 0.0003 m (300 µm). Foil is excluded.** This deliberately conservative
  demonstrator guard is not a experimentally validated transition thickness. Even above it,
  significant roll flattening invalidates the rigid-roll approximation.
* Tensile stresses ≥ 0 and strictly below supplied uniaxial mean flow stress.
* `tan(alpha) ≤ mu`: conservative unassisted bite screen, including when tensions are supplied.
  This can reject tension-assisted conditions that a more complete solution could admit.
* Nonnegative required roll power: regenerative/tension-driven rolling is excluded.
* Per-roll torque ≤ `mu F R`: necessary Coulomb capacity bound in the small-angle convention,
  **not** sufficient traction-field feasibility or an accurate motor sizing check.
* Nonfinite computed outputs are rejected. Nothing is silently clipped to a plausible result.

The scene has a narrower layout domain: R=0.15–0.4 m, b=0.5–1.8 m. Decorative equipment
clearances are generic and partly fixed. Process validity checks are not equipment strength,
motor, bearing or collision certification. Constraints in `physicroll.studies` are supplied
by the user of an offline synthetic study, not plant limits inferred by this project.

## Interpretation and missing physics

The prescribed `exit_thickness_m` equals the visual rigid-roll gap by construction. It is
**not** predicted from screw position or mill stretch. The model has no unloaded-gap input,
elastic loaded-gap solution or recovered downstream thickness; these must become distinct
variables in a later elastic model. Do not treat this gauge as an AGC command.

No elastic roll flattening/bending, roll-stack compliance, roll crown, width spread,
anisotropy, texture, temperature rise, lubrication film, roughness transfer, residual stress,
flatness/buckling, real metallurgy, speed-dependent friction, coil inertia or control dynamics
is solved. Backup rolls/housings/coils/gauges are visual equipment. No live signal connections,
plant credentials, production setpoints or production control are present.

## Numerical checks versus validation

The tests verify algebra, SI scaling, mass and energy conservation, exact rigid-circle bite
limits, parameter rejection, smooth small perturbations and zero-draft limits, and a frozen
baseline. They do not validate any experimental accuracy. Regression values lock the stated
closures and may change deliberately with a reviewed model version. See `research.md` for
separate validation needs for load/torque, shape, residual stress and control dynamics.

## Coupled equipment/observation snapshot, version 0.2

`physicroll.equipment` now supplies a separate **synthetic, inverse** stand/reel snapshot.
It takes the unchanged process solution and synthetic stand stiffness/reel radius/inertia
parameters. Stand extension is `F/K`; implied unloaded gap is prescribed loaded gap minus
extension. This does **not** solve a closed mill spring, roll flattening or strip recovery.
The total housing reaction is the same `F`, not an added force. Positive signed reel torque
on strip is `T_exit r_exit`; the paying-out entry reel contributes `−T_entry r_entry`.
At constant snapshot radii their signed shaft powers sum exactly to the process net tension
power. Local mass flows and force-to-stress conversions use the correct entry/exit gauges.
`physicroll.observations` implements qualified alternative measurement conversions
(documented in [sensors.md](sensors.md)). Neither module changes the baseline H1/H2
pressure/roll-speed closures, which remain uncalibrated.
