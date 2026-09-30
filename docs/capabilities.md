# Physics capability boundary

Published reviewed v0.3 is commit `09d0d5b2`; the optional local contact/material
increment is described in [contact-increment.md](contact-increment.md), with actual
comparison evidence in the [report-sync packet](report-sync-contact-increment.md).
Default behavior remains backward-compatible. Tests verify implementation;
no aluminium mill, thermal, product-quality or control validation is claimed.

| Topic | Executable calculation | Remaining boundary |
|---|---|---|
| Contact, force, torque and speed | Legacy heuristic `solve()` remains. Optional slab integrates tension-aware pressure, signed traction torque, neutral speed and mass/work diagnostics. Optional spatial hardening and coupled circular Hitchcock radius have convergence gates. | Projected small-angle, Coulomb sliding; no sticking/film or noncircular deformation, exact local shear field, strip elastic recovery or measured friction identification. Foil excluded. |
| Roll versus stand deformation | `contact.py` solves force-dependent circular roll radius. `equipment.py` retains separate synthetic inverse stand F/K bookkeeping. | No coupled loaded/unloaded/recovered-gap solution; never add a fitted full stand compliance to roll deformation without identifying overlapping contributions. |
| Material history | `MaterialState` carries alloy, declared temper/history, accumulated equivalent strain and supplied temperature. Optional `BiteHardening` varies assumed strength through a homogeneous plane-strain path and carries state across passes. | Synthetic or conditional coefficients, unknown calibration ranges; no rate/thermal feedback, anisotropy, microstructure kinetics, grain/texture/precipitation or certified final properties. |
| Mass and tension | Fixed-density, fixed-width incompressible `Q=b*h*v`; local tension force/stress and reel/hydraulic load-path observations have explicit units and signs. | No spread, elastic density changes, transient material transport, evolving coil/reel dynamics or live signals. |
| Plastic work and heat | Mechanical plastic work and solid slip dissipation are separately integrated. `thermal.py` provides an independent two-prescribed-mass energy budget with supplied heat fractions/contact/cooling coefficients and a stable explicit-step gate. | This is not an advecting rolling thermal field. No measured aluminium thermal validation, automatic motor-power-to-heat conversion, universal plastic heat fraction, roll thermal crown or coolant-to-friction law. |
| Lubricant/coolant and sensors | Disconnected registry with fluid identity, observations/quality and unknown values; explicit alternative load-path observations. | No calibrated film, roughness/friction or HTC closure. Aluminium emissivity and fluid identity need evidence; neat oil is possible. |
| Profile and flatness | `profile.py` diagnoses crown from supplied thickness, membrane mismatch and through-thickness curvature separately. | Fields are inputs, not predictions. No predictive roll stack/bending, latent-flatness/buckling or wave amplitude. |
| Fracture and residual stress | Unsupported mechanics regimes reject/flag. | No 3D edge damage, residual-stress field, crack propagation, mesh-regularized fracture or certified strip-break safety. |
| Literature comparison and optimisation | Retained conditional three-pass AA5052 fixed-data comparison and old assumed-range gauge search. New structural/sensitivity comparisons retain failures and before/after residuals. | No fit to those passes, independent validation, known mill ratings, uncertainty probabilities or expanded optimisation. Slip mismatch and semantic ambiguity remain. |

See [mechanics audit](mechanics-audit.md), [traceability](traceability.md),
[research](research.md) and [sensor references](sensors.md) for source and test paths.
Thermal/coolant, roll-stack shape and material development remain scoped future
modules with distinct data and conservation/validation requirements.
