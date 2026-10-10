# V1 finite schedule-search workflow

`python -m physicroll --run-spec scenarios/v1_schedule_search.runspec.json`
enumerates a small, explicitly supplied **synthetic** single-layer gauge grid.
The packaged example has two optional interior gauges and a three-candidate
evaluation cap. Search checks the cap before evaluating any candidate. Each
candidate reconstructs the full checked route from its selected gauges and
declared speed/tension choices, using one initial material state, hardening
law, pass model and prescribed interpass temperature handoff. State is carried
through every pass. A selected route is independently replayed and required
to return the same checked result.

The public adapter currently accepts isothermal passes with one declared
geometry/material/pass template and fixed equipment capacities if supplied.
It rejects mismatched requested/resolved grid inputs, changed source hashes,
phase observations, invalid base models, incompatible material identities
and non-prescribed thermal handoffs. Candidate-specific domain failures are
retained as rejected records. The built-in ordering minimizes pass count,
then compares normalized utilization only when comparable declared capacity
checks are complete. Speed and strength are model inputs/hypotheses, not
proven quality controls.

The selected route's declared-bounds status remains `INDETERMINATE` when
machine capacities or steady operating ranges are missing. “Selected” means
best within the supplied mesh and choices, not plant feasibility or global
optimality. Neither joule-level energy nor cycle time is an objective: the
current steady model lacks transported duration and handling/reversal time.
Scientific qualification and operating readiness remain `NOT_ASSESSED`.
The `base_pass` scenario is a valid single-pass template for invariant
geometry/model choices; its placeholder gauges do not constrain total route
reduction. Each generated candidate pass receives and validates its own
gauges. Envelope bounds/numerical statuses describe the selected route. When
no route is selected, candidate computation and violation counts remain in
`checks`, and `predictions_computed` remains true if any candidate reached a
checked calculation. The envelope does not certify a violating candidate.
