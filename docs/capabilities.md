# Physics capability boundary

Published reviewed v0.3 is commit `09d0d5b2`; the published optional contact/material
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
| Plastic work and heat | Checked mechanics supplies plastic work, solid-slip dissipation and mass flow. Optional `energy_handoff.py` closes a flowing-strip enthalpy balance and separate roll thermal storage with supplied partitions/contact/cooling; nonthermal plastic work stays explicit. `thermal.py` remains a separate prescribed-mass exercise. | No resolved roll/strip temperature field, measured aluminium thermal validation, universal plastic heat fraction, fluid/film law, thermal crown or temperature feedback into force. |
| Passive contact option | `energy_handoff.py` can instead solve an opt-in two-node conductive exchange from a supplied total W/K conductance and inlet/outlet midpoint temperatures; contact heat and both energy balances are solved together. | Conductance is synthetic/unidentified, midpoint temperatures are approximations, and neither film nor a spatial temperature field is resolved. Prescribed and passive contact modes exclude each other. |
| Lubricant/coolant and sensors | Disconnected fluid registry can be attached to the energy output as an observation; cooling and contact powers are separately supplied with provenance. | Fluid identity cannot infer friction, heat partition or HTC. Aluminium emissivity and actual cooling boundaries need evidence; neat oil is possible. |
| Profile and flatness | `profile.py` diagnoses crown from supplied thickness, membrane mismatch and through-thickness curvature separately. | Fields are inputs, not predictions. No predictive roll stack/bending, latent-flatness/buckling or wave amplitude. |
| Fracture and residual stress | Unsupported mechanics regimes reject/flag. | No 3D edge damage, residual-stress field, crack propagation, mesh-regularized fracture or certified strip-break safety. |
| Literature comparison and optimisation | Retained conditional three-pass AA5052 fixed-data comparison and old assumed-range gauge search. New structural/sensitivity comparisons retain failures and before/after residuals. | No fit to those passes, independent validation, known mill ratings, uncertainty probabilities or expanded optimisation. Slip mismatch and semantic ambiguity remain. |
| Prescribed multi-pass workflow (development branch) | Audits gauge transitions and equivalent-strain increments; chains the existing synthetic hardening state, pass-specific steady inputs and declared signal ranges. | No inferred pass count, controller, anneal, temperature or foil prediction. The existing 300 µm single-pass model guard rejects the 50 µm target stage; see [multi-pass foundation](research/multipass-foundation-2026-10-02.md). |
| Optional checked multi-pass replay (development branch) | Selects spatial slab or circular contact per pass, with checked material state and optional flowing/passive-contact energy ledger, explicit thermal handoffs and pass-level bound checks. | No interpass heat-transfer law, thermal feedback into force, pack/foil model or production certification; see [checked integration](research/checked-schedule-integration-2026-10-02.md). |
| Band / chatter-mark root-cause screening (opt-in) | `chatter.py` linear third-octave stability (critical speed with and without the bite-damping closure, forced response, time trace); `band_signatures.py` pitch laws, roll/gear/bearing/coil catalogue, yield-point, herringbone, slip, film and spray screens; `band_diagnosis.py` tallies twelve band hypotheses against plant observations, levers and a pass-schedule sweep; HTML report and CLI. | Ordinal evidence tally, not probabilities; no plant validation, limit cycle, friction-speed law or time-domain fifth-octave regeneration; derived bite stops near 0.3 mm entry gauge for hard alloys (thinner needs supplied sensitivities); see [band diagnosis](band-diagnosis.md). |

See [mechanics audit](mechanics-audit.md), [traceability](traceability.md),
[research](research.md) and [sensor references](sensors.md) for source and test paths.
Calibrated thermal/coolant feedback, roll-stack shape and material development
remain scoped future modules with distinct data and conservation/validation
requirements.

The bounded [flowing energy handoff](energy-handoff.md) has separate
[first-law, source and run evidence](report-sync-energy-handoff.md). It adds no
calibrated thermal/material feedback or resolution of the published slip residual.
The later [passive-contact numerical option](passive-contact.md) retains that
boundary and leaves the 53-page research report as a dated historical edition.
