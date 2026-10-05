# O0 operating-phase and model-readiness contracts

This increment implements an **offline observation replay contract**, version
`O0_OPERATING_CONTRACT_V1`, in `physicroll.operational_replay`. It is based on
thermal commit `6b2b1a345cc7aac419dbf0839cfa6308b20408ce`; that commit is unchanged.
The development branch is `dev/p1-operating-phase-contracts`. Neither this branch,
the thermal branch nor the research branch is merged into main by this work.

## Evidence and design decisions

The source of the design is the completed research at
[`a993fc40549061da5a2b1848656ec5257a9419a6`](https://github.com/Gravelaw/PhysicRollModel/tree/a993fc40549061da5a2b1848656ec5257a9419a6/docs/research/comprehensive-audit-2026-10-02),
particularly `operational-phase-review.md`, `roadmap.md`,
`implementation-traceability.md`, `traceability.csv` T046–T052, and the operational
source-review JSON files. Those source reviews establish the access depth and
version; this increment does not claim a new full-text literature audit.

| Evidence | Supported requirement | Implemented decision / limit |
|---|---|---|
| UR-OPS-01: user describes ramp-up, settled rolling and slowdown near coil completion, with alloy/gauge/pass-specific recipes | Preserve actual phase and pass-specific conditions | Explicit pass/alloy/temper/nominal-gauge scope; phase targets; length/event records. No automatic activation sequence. |
| R164 [ABB Review 4/2004, p47](https://library.e.abb.com/public/76bffa60a31d625cc1256f57004df84c/44-49%204M891.pdf); R165 [ABB 3BDD017150-EN, 08.2017, PDF pp2–4](https://library.e.abb.com/public/04580d2383cc4b53b8573d1bb8eda2e8/Technological_Controls_for_Cold_Rolling_Mill_190815_LowRes.pdf) | Distinguish full-pass dynamics, ramps, threading, tail-out, reversal and measurement delay | Phase tags retain these events; steady-model attempts are disabled for all nonsteady samples in O0. No dynamic equations are imported. |
| R112 [ABB Review 1/2009, pp46–48](https://library.e.abb.com/public/77efb4c9677e46c5c125759100274942/43-48%201M924_ENG72dpi.pdf); R166 Primetals aluminium automation, as reviewed in the pinned research | Setup precedes threading; setup and actual signals are different; roll thermal state has its own lifecycle | Setup uses explicitly hypothetical recipe assumptions independently of the actual phase. Thermal eligibility is separate and not inherited from mechanical steadiness. |
| R026 [Wehr et al., §§4.1/6.3](https://publications.rwth-aachen.de/record/817497/files/817497.pdf) | Valid synchronized measurements and a qualified identification domain precede adaptation | Located measurements, clock/parcel references, uncertainty, age and alignment evidence. No adaptation is implemented; steel laboratory evidence supplies no aluminium thresholds. |
| R014 [preprint v1 §4.4, Fig6](https://arxiv.org/html/2408.03242v1) | Force/torque steadiness can precede internal-field steadiness | Evidence names a fixed model/output bundle; it cannot enable temperature, internal-field or other-model predictions. No universal dwell time. |
| R171 [US3518857A description/Fig1](https://patents.google.com/patent/US3518857A/en); R172 [ACS880 Rev D selected sections](https://library.e.abb.com/public/b103c5c12ec749edb727e684d3a394eb/AWIL140x_en.pdf) | Slowdown/length logic depends on geometry, speed and estimator/mode provenance | Optional remaining length requires uncertainty and estimator/version provenance. A labelled transition needs evidence. No remaining-length estimator, threshold or slowdown command. Patent/vendor examples are not validated project settings. |

These are repository design choices informed by the sources, not a recovered
plant controller or validated model-enable programme. In particular, prohibiting
all ramp samples is a conservative O0 restriction. Future qualified quasi-steady
ramp evaluation requires its own output-specific evidence and adapter.

## Data and replay contract

- `PassScope` identifies one nominal recipe pass, alloy, temper and full entry/exit
  gauges. These gauges describe recipe applicability; they are never actual
  gauge readings. A different pass/alloy/gauge needs an explicit matching recipe.
- `OperatingRecipe` has an ID, revision, provenance and `PhaseTarget` values.
  Targets are matched by phase and quantity. Missing phase targets remain absent;
  no value is inherited from another phase or earlier pass.
- `OperationSample` identifies coil, pass scope, recipe revision, one clock and
  material-coordinate reference, timestamp, phase and its evidence basis/source.
  Observed and inferred labels remain distinguishable; `unknown` is retained.
  Allowed phases are `prepared`, `threading`, `ramp_up`, `steady`, `deceleration`
  (ramp-down), `tailout`, `reversal`, `interrupted`, `complete`, `unknown`.
- `AppliedReference` records a command value/time and optional acknowledgement.
  Unacknowledged commands remain unacknowledged; neither kind becomes a reading.
- `MeasuredSignal` records value/time, SI unit, location, quality, uncertainty and
  material coordinate. Unavailable values are null, never zero-filled. Zero
  tension can be an established boundary. Unknown uncertainty/coordinates remain
  null and block sample readiness. Quality/evidence are caller assertions, not
  authenticated plant data.
- `SteadyWindowEvidence` names a model/output bundle, a positive-duration window
  ending at the sample, a caller-declared maximum measurement age, and stationarity/
  error-budget and material-alignment provenance. Merely reaching a recipe speed
  supplies none of this evidence. Location and equal timestamps alone do not align
  material parcels; the caller must supply the alignment assessment.

`replay_operating_samples(recipes, samples)` accepts one oriented coil/pass,
clock and coordinate reference. Times strictly increase. It preserves each
record and emits its matching targets and model readiness. It does not detect
phases, interpolate missing data, compute acceleration, compare unequal parcels,
advance strain/history/roll state, or execute any solver. Thus a short coil can
contain ramp-up and deceleration without a fabricated steady plateau. Recipe
revisions may change explicitly; evidence windows cannot cross a recorded
nonsteady sample, recipe-change event, absent/unknown boundary, required-data
gap (missing/invalid reading, coordinate or uncertainty), or known zero speed.
This remains true when the phase annotation continues to say `steady`. The
unavailable record is retained; a subsequent evidence window must start strictly
after the recorded loss. Established zero tension is not a gap. Changed phase labels need transition
provenance, and re-entry needs a fresh window after the last such event.

Reversal is recordable but unavailable for steady evaluation. Speeds here use
the existing nonnegative entry-to-exit oriented-pass convention. Negative raw
encoder speeds are explicitly rejected, not converted with `abs()`. A signed
frame/reel-role adapter and genealogy transfer belong to a later increment;
a new oriented pass requires a new replay. No fixed state-transition graph is
assumed: sampled records can omit intermediate phases and retain interruptions.

## What readiness means for existing models

`evaluation_allowed=True` means only **the O0 evidence gate permits attempting a
separate evaluation**. `prediction_validity` is always `NOT_EVALUATED`. Nothing
is calibrated, qualified or enabled on equipment. The raw scenario solvers and
checked schedules remain hypothetical offline APIs; this module does not attach
a sample to a calculation or allow unrelated recipe predictions to masquerade
as measured-trajectory replay. A future adapter must bind actual values and
material state before calling the solver and retain every existing rejection.

| Existing capability | O0 readiness / required separate conditions |
|---|---|
| Legacy mechanics / mean-hardening pass | Named illustrative force/torque/power/assumed-slip bundle. Setup needs explicit positive-speed recipe targets; actual-sample preflight needs the gates below. Existing synthetic scenario, geometry, reduction, material/history and positive-motoring restrictions remain. No accuracy qualification. |
| Spatial slab | Separate force/torque/power/slip bundle and separate evidence. All existing positive-speed, gauge, strain/temperature, tension-strength, sliding/yield-cap, neutral-root, bite and refinement/work-conservation gates still apply. The unassisted bite screen is not a threading simulator. |
| Circular-contact slab | Own evidence bundle; additionally requires roll elasticity, fixed-point/refinement convergence and the circular-radius domain. It does not implement a roll stack or loaded-gap response. |
| Prescribed flowing energy | `SEPARATE_INPUT_CONTRACT_REQUIRED`: requires checked mechanics, material state, bounded cp, partitions, signed contact/cooling powers and roll mass/state/duration. A source-power ledger cannot certify passive contact or full process entropy. No sample adapter in O0. |
| Passive flowing energy | Same separate thermal inputs plus supplied conductance and the inherited I01 `MONOTONE_CAPACITY_V1` domain, property/energy/entropy checks. It cannot inherit a mechanics steady-window assertion. |
| Standalone `thermal.step` | Separate finite two-capacity numerical operator, not a flowing pass. Its supplied powers, capacities, temperatures and explicit step bound apply independently. No O0 phase enable or interpass-cooling prediction. |
| Equipment snapshot | Separate synthetic compliance/reel snapshot inputs; zero-acceleration snapshot is not drive/span dynamics. No O0 adapter; dynamic duty, regeneration ratings and installed limits remain unknown unless supplied. |
| Material hardening, measurement conversions, supplied-profile diagnostics, gauge audit | Components/diagnostics with their own explicit input and domain checks, not phase-driven predictions. The hardening law has no rate/temperature feedback; conversions do not align signals; profile inputs are not predicted flatness. |
| Checked/legacy schedule replay, literature comparisons and finite candidate studies | Compose hypothetical passes/scenarios; existing explicit handoffs, declared-limit incompleteness and scientific caveats remain. Time samples are never extra passes. These functions do not receive O0 enable authority. |
| Coupled dynamic rolling, parameter adaptation, live control | `NOT_IMPLEMENTED`, evaluation disabled. No learning, controller or equipment path is added. |

For an **actual-sample** mechanics attempt, every bundle separately needs: phase
`steady`; established bite and both span boundary conditions; its own current
steady/alignment evidence; valid located actual entry/exit gauge, entry speed,
entry/exit tension, uncertainty and material coordinates; measurements within the
window and declared age budget; and positive actual entry speed. Missing data
produces `WAITING_FOR_DATA`; nonsteady phase or explicitly absent boundaries
produces `NOT_APPLICABLE`. Force/torque/slip measurements are not prerequisites
for merely attempting a forward calculation, but would be needed for empirical
comparison/validation. Bounds and thresholds are not inferred from OEM examples.

`assess_setup_recipe(recipe, target_phase='steady')` separately checks that the
selected phase has speed, exit gauge and both tension targets; entry nominal
gauge comes from its scope. It marks these as `RECIPE_ASSUMPTIONS_ONLY`. It does
not claim that the selected phase is steady or present in actual data, and still
requires geometry, friction, material state/law and all solver domain checks.

## Verification and remaining gaps

Run `python -m unittest discover -s tests -p test_operational_replay.py -v` for
synthetic contract examples: distinct targets/applied/actuals, normal phase trace,
short coil without plateau, unavailable/stale/suspect/unaligned readings, zero
versus unknown tension, per-model evidence, recipe applicability/revisions,
interruption/re-entry, invalid/future information and deterministic serialization.
The full suite and `scripts/smoke.py` additionally protect existing calculations.

No actual operational dataset is included. Remaining work includes independent
phase-labelled aluminium traces; clock/parcel alignment; signed reversal mapping;
length estimation; output-specific stationarity/error budgets; numerical adapters
binding samples to solver inputs; thermal input qualification; calibration and
held-out validation. O1 or O2, material laws, controllers, optimisation, equipment
integration and deployment are outside this bounded increment.
