# P1 operating-contract validation — 5 October 2026

Development branch: `dev/p1-operating-phase-contracts`.
Parent/dependency: immutable thermal commit
`6b2b1a345cc7aac419dbf0839cfa6308b20408ce`.
Main was independently verified at
`caec37ef86a8b78e1eb88292ea6368bfb64bcbdc`; it was not merged or modified.
The research commit `a993fc40549061da5a2b1848656ec5257a9419a6` was read
without merging its branch. Source-to-contract decisions and unsupported cases
are documented in [operational-replay.md](operational-replay.md).

All work used the saved Codex cloud workspace `/workspace/PhysicRollModel`.
No applicable AGENTS.md or populated repository `.agents/skills` was present.
Work paused on 2 October with the draft uncommitted; on 5 October cloud execution
recovered and the exact branch, parent and preserved draft files were verified
before continuing. No development ran on a user computer.

## Scope and compatibility

The new pure O0 API stores pass/alloy/temper/nominal-gauge recipe applicability,
phase targets, command/acknowledgement references and actual readings separately.
It reports evidence-based readiness for a separate mechanics domain check and
explicitly leaves thermal/equipment adapters, dynamics, adaptation and control
unavailable. It performs no solver execution or material/roll state advancement.

The only change to existing runtime code is expansion of `operating.PHASES`.
Existing nonsteady ranges still remain `NOT_EVALUATED_PHASE`; mechanics,
thermal solvers, schedules, scenarios and historical artifacts are unchanged.
The separate thermal commit remains the exact parent and is not rewritten.

## Tests and review resolution

The initial draft passed 101 tests and smoke checks. Independent Astra domain
and correctness reviewers nevertheless found a blocker: a sample labelled
`steady` could lose established bite/span boundaries, then reuse an evidence
window spanning that loss when the boundary returned. Passing the original suite
did not establish the required causal behavior.

A new regression reproduced failures in eight cases before the correction:
absent boundary, unknown boundary, missing required reading, suspect reading,
unavailable reading, known zero speed, missing material coordinate and missing
uncertainty. Replay now records a new evidence barrier at each such event,
retains the unavailable sample, and rejects later evidence windows starting at
or before that loss. Fresh windows strictly after the event remain usable.
Established zero tension does not create a barrier. Existing nonsteady and
recipe-change barriers remain in place.

Final checks executed after the correction:

| Check | Result |
|---|---|
| `python -m unittest discover -s tests -q` | 102 tests passed (6.809 s), including 10 operating replay tests and all 92 inherited tests |
| `python scripts/smoke.py` | PASS: baseline, v0.3 foundations, disconnected sensors, bundled asset checksums |
| `git diff --check` | PASS |
| Independent Astra domain re-review | APPROVED, no remaining blocking findings; 10 operating replay tests independently passed |
| Independent correctness re-review | APPROVED, no remaining blocking findings; 10 operating replay tests independently passed |

The retained tests cover deterministic serialization and no mutation, separate
recipe/applied/actual values, full phase trace, short coil without a plateau,
per-model evidence, setup versus sample readiness, absent/unknown boundaries,
missing/stale/suspect/unavailable readings, unknown alignment/uncertainty,
recipe applicability and revisions, interruption/re-entry, zero speed versus
zero tension, causal command/measurement timestamps, and legacy phase-tag
compatibility. All evidence and numeric examples are synthetic; no measured
aluminium operational validation is claimed.

## Remaining gates

Before any O1 sample-to-solver adapter: bind actual gauges/speed/tensions and
material/geometry/contact inputs, preserve every numerical domain check, and
validate clock/parcel alignment and output-specific stationarity budgets against
independent data. Remaining-length estimation, signed reversal/reel-role mapping,
thermal readiness, dynamic equations, parameter adaptation and control require
separate work. No universal speed threshold, calibrated operating envelope,
main merge, equipment integration or deployment is included.
