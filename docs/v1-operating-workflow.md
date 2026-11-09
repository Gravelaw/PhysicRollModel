# V1 offline operating replay adapter

`python -m physicroll --run-spec scenarios/v1_operating_replay.runspec.json`
replays a seven-phase **synthetic** O0 record through the public API and CLI.
The packaged template contains separate recipe targets, acknowledged applied
references, and measured samples. The source-module hashes are checked before
execution. A changed source requires an explicitly updated RunSpec; this is
source identity, not physical authentication of observations.

The adapter reconstructs and validates the existing O0 contract, including
one oriented coil/pass, timebase and material coordinate reference, ordered
sample times, explicit phase transitions, recipe revision applicability and
fresh steady-window evidence after an interruption. It records model-specific
readiness to attempt a *separate* domain evaluation. In the sample, only the
steady row has sufficient synthetic evidence to attempt a `spatial_slab`
check. It does not run that solver. `predictions_computed` remains false;
numerical, scientific and site operating statuses remain `NOT_ASSESSED`.
No material or roll state is advanced, and phase labels are caller supplied.

The `RunSpec` uses `recipe_targets.recipes` and `observations.samples` as
distinct fields. `requested_inputs` and `resolved_inputs` share an explicit
replay ID. `identities.recipe_id` names a single recipe ID when one is used;
it is null if multiple IDs occur. No O0 run specifies solver, material,
bite or thermal selections, numerical settings, or a material state. A future
actual-sample solver binding needs the separate O1 gate described in the
original v1 plan.
