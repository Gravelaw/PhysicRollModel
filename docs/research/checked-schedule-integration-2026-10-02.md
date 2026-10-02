# Checked multi-pass solver integration (development branch)

Recorded 2 October 2026, after the [prescribed foundation](multipass-foundation-2026-10-02.md).
The [theory and source register](multipass-theory-2026-10-02.md) remains the
source record. This increment composes existing reviewed mechanics and energy
modules; it does not add an aluminium flow law, foil contact law or optimiser.

## Execution contract

`physicroll.checked_schedule.run_checked_schedule()` accepts a named,
single-layer sequence of `CheckedPass` records. Each pass explicitly selects
`spatial_slab` or `circular_contact`, the solver grid and unassisted/established
bite mode. The latter uses the existing diagnostic convention; it is not a
threading proof. `circular_contact` requires caller-supplied roll elasticity.
Every pass supplies its own `Scenario`, `PassOperatingPlan` and assumed material
strain/temperature envelopes. No pass inherits operating settings or ranges.

The passed `Scenario.mean_flow_stress_pa` is a required legacy input field,
checked for finite positive SI units, then replaced by the mean of the named
synthetic hardening law over that pass's state-dependent equivalent-strain
interval. Both requested and effective scenarios are retained. The spatial
`BiteHardening` state is supplied to the checked slab/contact solver; its
material `state_out` advances the next pass. Geometry audit retains total
telescoping gauge strain separately from the initial and evolving hardening
state. No anneal, recovery, texture or damage transformation is inferred.

An optional `PassHeatBoundary` invokes the existing flowing-strip/roll energy
ledger after **numerically converged** mechanics. Optional
`PassiveContactBoundary` selects its supplied-conductance contact mode; passive
and prescribed contact heat cannot be combined. Supplied strip/roll heat
capacity curves, partitions, cooling powers, duration and contact inputs keep
their existing source and unit checks. The predicted strip outlet temperature
and roll storage temperature are separate from observations and prescribed
interpass values. Temperature does **not** feed back into force or friction.

Every adjacent pass requires an `InterpassHandoff`. The strip temperature may
be explicitly prescribed, or directly carried from a **predicted** preceding
thermal outlet under a declared no-exchange assumption. A pass without thermal
prediction cannot use direct predicted carry. If the next pass uses the energy
ledger, its roll temperature must be prescribed or directly carried from a
modeled preceding roll body. Direct carry requires the same declared roll-body
identity, nominal radius and effective thermal mass. An unmodeled roll has no
persistent thermal state.
These events represent neither interpass residence cooling nor annealing.
Externally prescribed temperature changes do not reset hardening; the event
appears in material history.
An interpass width change requires its own provenance (for example, declared
trimming); density changes reject because this chain has no interpass density
or mass-loss model. Within-pass mass balance remains the existing constant
width/density approximation.

`PassOperatingPlan` checks caller-supplied steady ranges for requested gauges,
speed and tensions; predicted force, per-roll torque, both-roll mechanical
power, slip and outlet temperature where modeled; declared boundary flows;
and separately observed signals. Optional fixed equipment limits check force,
torque, roll power/speed and reel tension forces. Threading, deceleration and
tailout ranges have no solver and report `NOT_EVALUATED_PHASE`. A requested
outlet-temperature range without an energy model reports
`NOT_EVALUATED_NO_MODEL`. A violated declared range/limit yields
`DECLARED_BOUNDS_VIOLATED`; otherwise declared-bounds status is
`INDETERMINATE` because material calibration, absent ratings, foil validity
and quality criteria are not proven. Plan coolant/lubricant flow values are
checked inputs, **not** inferred cooling powers, friction or HTCs.
Torque, roll power and slip ranges may be signed. A supplied positive drive
rating does not certify an unprovided regenerative rating; negative predicted
torque/power reports `NOT_EVALUATED_REGENERATIVE_LIMIT_UNKNOWN`.

The input `exit_thickness_m` is a target **strip gauge**, not an unloaded gap
or screwdown setting. Exact consecutive gauge equality and strict reduction
are required. The inherited 300 µm exit and 50% reduction software guards
reject unsupported stages before mechanics. They are not universal limits on
aluminium rolling. The route requires explicit per-layer full-thickness basis
and exactly one layer. A double-rolled pack needs a different model and cannot
be represented by replacing two 50 µm layers with a 100 µm single strip.

## Equation and output traceability

| Quantity / gate | Existing implementation composed here | New regression |
|---|---|---|
| `Δεeq=(2/√3)ln(h_in/h_out)`, state-dependent `Y(h)` | `materials.BiteHardening`; `schedule.inspect_gauge_schedule` | `test_two_pass_slab_and_energy_match_independent_replay` |
| Pressure/neutral, force, signed traction torque, work and two-grid check | `slab.solve_slab`, optionally `contact.solve_circular_contact` | `test_two_pass_slab_and_energy_match_independent_replay`; `test_circular_and_passive_options_match_direct_solver_calls` |
| Flowing strip enthalpy, roll storage, signed contact heat and energy residual | `energy_handoff.handoff_pass` | Same two tests compare independent direct calls and existing conservation gates |
| Distinct per-pass signals, ranges, equipment limits and unsupported criteria | `operating.assess_pass_operating_plan` | `test_invalid_layer_stage_handoff_and_limit_propagation` and earlier `test_schedule.py` |
| Layer, foil, handoff and solver-mode rejection | `checked_schedule.run_checked_schedule` | `test_invalid_layer_stage_handoff_and_limit_propagation` |

These are numerical composition/regression checks, not experimental
validation. The existing three-pass [Shao AA5052 comparison](../aa5052-study.md)
remains within its published 4.10→1.72 mm case with unresolved temper/speed
semantics and force/slip residuals. It does not support a 50 µm prediction.
Quarantined AA8075 supplemental tension values are not loaded by this module.

## Remaining gates for a schedule search

A search should consume this checked replay as its validator only after a
named alloy/temper flow law and assumed envelopes are calibrated, mill and
reel ratings are supplied, thermal interpass time and boundary conditions
are measured or explicitly modeled, and foil/pack mechanics are available
for the requested target. The search must preserve state-dependent histories,
phase-dependent ranges and all rejection reasons. A grid failure would be a
failure of that grid/model, not proof of physical unrollability.
