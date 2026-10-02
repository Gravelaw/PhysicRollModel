# Bounded schedule search foundation

Recorded 2 October 2026. This increment adds `physicroll.schedule_search`, a
finite search layer over the [checked multi-pass replay](checked-schedule-integration-2026-10-02.md).
It makes no new aluminium or foil prediction. The earlier 6 mm to 0.05 mm
illustration is neither a target nor an acceptance case. No physical benchmark
fixture is selected in this increment.

## Source audit before choosing a benchmark

The existing [Shao 2015 AA5052 fixture](../../scenarios/literature/shao2015_aa5052/)
contains three reported stages, 4.10 → 2.9024 → 2.2087 → 1.72 mm at 1360 mm
width. Its `inputs.csv` records per-pass tensions, radius-labelled 210.81 mm
work roll, reported rolling speeds and friction coefficients. The original
paper's Table 2 records measured force and forward slip separately from the
authors' model values and calculated flattened radii. The local
`measured_validation.csv` and `reference_model_outputs.csv` preserve that
separation. The [source register](../../scenarios/literature/shao2015_aa5052/sources.json)
links the original [article](https://doi.org/10.18280/ijht.330113) and lists
the unresolved quantities. The historical [AA5052 study](../aa5052-study.md)
optimised only two intermediate gauges under assumed source-extrema reductions;
those extrema are observed cases, **not** rated mill limits or a safe process
envelope.

Audit gaps that block using this fixture as a checked search acceptance case:

| Input or output | Recorded provenance | Remaining issue |
|---|---|---|
| Gauges, width, tensions, friction, speeds | Shao Table 1, local `inputs.csv` | Speed location is undefined; friction may be identified from the same force/slip observations. |
| Roll size | Shao Table 1 labels 210.81 mm as radius | Equation 6 prose calls the quantity diameter; neither interpretation is silently certified. |
| Measured separating force and forward slip | Shao Table 2, local `measured_validation.csv` | No instrument uncertainty, independent coils, torque or temperature observations. |
| Authors' force, slip and flattened radius | Shao Table 2, local `reference_model_outputs.csv` | Model outputs are not additional measurements or validation data. |
| Flow stress / entry state | Shao K = 276.5 MPa, n = 0.26; local assumptions file | Incoming temper, prior strain, strain convention, Eq. 3 accumulation coefficient and calibration envelope remain unknown. |
| Equipment and thermal constraints | No source ratings in fixture | No force, torque, power, reel, temperature or interpass time limits can be treated as hard limits. |

The manufacturer's [5052 sheet](https://www.hulamin.com/sites/default/files/downloads/5052%20Data%20Sheet.pdf)
supplies generic density context only. It does not repair the benchmark's
missing temper or flow calibration. A separately audited published aluminium
cold multi-pass case should be considered for an example only when its inputs,
measurements, constitutive convention and missing data are itemised. Observed
operating ranges must remain distinct from hard constraints.

## Search contract

The caller supplies an exact start and target gauge, a finite descending grid,
mandatory interior checkpoints, inclusive pass-count bounds, and discrete
speed/tension choices for each possible pass position. `log_gauge_grid` can
build a logarithmically spaced mesh while retaining endpoints and checkpoints
exactly. A strict evaluation cap rejects an oversized Cartesian product before
any mechanics execution. The reported result is an optimum **on that grid**, not
a continuous or physical global optimum.

Each candidate is a *complete route*. A caller builder must construct distinct
`CheckedPass` records, named per-pass operating plans, explicit interpass
handoffs, named material state/law, solver configuration, optional thermal
boundaries and declared equipment limits. `checked_replay` forwards these to
`run_checked_schedule` with its single-layer gauge contract. The search
replays the entire route for every candidate, so equal gauge nodes with
different prior controls do not collapse into one state. Rejected solver/domain
errors and declared violations stay in the candidate record. The returned
single-layer audit, pass count, gauges, speed and tensions must match the
enumerated route; a mismatched or malformed result fails the search rather
than masquerading as model rejection. A selected route is rebuilt and replayed
once more; differing results fail the search.

Only candidates with no *evaluated* declared bound violation are ranked. Their
status remains `INDETERMINATE`, even after selection. Ranking first minimises
pass count, then peak predicted value divided by its explicitly supplied
equipment rating when every pass has evaluated equipment checks. The rated
quantities and numerical limits must agree between passes and candidates;
configuration drift fails the search. Missing or unevaluable ratings leave the
tie score absent; stable grid/choice enumeration breaks remaining ties. The
caller must also keep rating provenance and conventions fixed. The
search does not optimise energy or time: strip length/throughput, drive
efficiency convention, interpass residence and supported energy boundaries
are not supplied by this interface.

This layer does not turn the software 300 µm/50% guards into process limits,
model pack rolling, infer flow law or temperature feedback, certify threading
or tails, or promote an `INDETERMINATE` route to feasible. A grid exhaustion
means only that no nonviolating route was found on the declared mesh with the
provided model and inputs.

## Verification and remaining gates

Five synthetic oracle tests exercise endpoint/checkpoint retention, pass-count
priority, stateful full-route scoring, explicit cap, rejection recording,
route/rating contract drift and selected-route replay mismatch. An independent
algorithm/physics review found route identity, rating comparability and
malformed-oracle handling gaps; all three were corrected before this note.
These are algorithm tests, not aluminium
validation. The existing checked-schedule regression tests continue to cover
direct solver composition and handoffs. A physical fixture should follow only
after source audit, with an independently specified candidate builder and a
comparison to reported measurements that does not fit parameters to those same
rows. Material calibration, equipment ratings, interpass boundary conditions
and all non-steady operating phases remain gaps for production use.
