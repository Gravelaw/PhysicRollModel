# V1 checked public workflows: first W3 adapter

`physicroll.workflows.run_checked_spec(RunSpec)` and `python -m physicroll
--run-spec input.json --output result.json` now run the same checked-pass or
checked-schedule calculation. The positional legacy scenario command remains
available. The result is a version 1 `ResultBundle` bound to the exact
canonical RunSpec digest. The checked CLI writes a complete UTF-8 result by
replacing the target only after a temporary file has been fully written.
Invalid input or a rejected calculation exits nonzero without publishing a
partial bundle.

The adapter reconstructs the existing `CheckedPass`, material, operating,
thermal and optional circular-contact data from `resolved_inputs`. The selected
solver, bite, material and thermal modes and numerical cell/refinement settings
must match `model_choices` and `numerical_settings`; unsupported nested fields
are rejected. Thermal handoff is explicit and requires heat-capacity curves.
The checked example in `scenarios/v1_checked_pass.runspec.json` runs through
both API and CLI. Tests also execute a two-pass thermal handoff.

The bundle records requested data in the RunSpec, effective scenarios and
state in the result, and operating checks with independent status axes. Six
equipment capacities and the solver's missing steady input/output ranges are
required in the bounds evidence for each pass. If a capacity or range was not
supplied, it remains unevaluated and coverage cannot become complete merely
because one supplied range passed. Declared range and observation checks are
additional named limits. The status `WITHIN`, when
possible, means only that every **declared required** limit was evaluated and
within its supplied bound; it does not mean feasible, scientifically qualified
or operationally ready. Scientific and operating statuses stay `NOT_ASSESSED`.

W3 is **not yet closed**. Public adapters for the fixed benchmark, declared
sensitivity, bounded search and O0 replay remain. W4 still needs resource-hash
verification at execution, portable saved-run bundles and reproduction; this
adapter binds the result to the RunSpec digest but does not yet resolve source
hashes against the installed package. W5 editor/report and the separately
amended transient solver/animation work are also outstanding.
