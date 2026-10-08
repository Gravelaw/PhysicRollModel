# Shao AA5052 conditional benchmark replay

Recorded 2 October 2026 after the [bounded search foundation](schedule-search-foundation-2026-10-02.md).
The source audit selected [Shao et al. 2015](https://doi.org/10.18280/ijht.330113)
as the most usable currently published three-pass force/slip comparison for
the existing scalar-hardening checked solver. Selection is for a **conditional
comparison**, not full reproduction, independent validation or a feasible
mill schedule. No new 6 mm → 0.05 mm target is used.

## Raw extraction and established fixture parity

[`data/shao2015_raw.json`](data/shao2015_raw.json) is a source-only
transcription of the original paper's Table 1, Table 2 and Eqs. 2–3. Each
pass separates process values, published friction input, measured force/slip,
and the authors' calculated force/slip/flattened radius. Missing temper,
initial strain, speed reference, measurement uncertainty and capacity remain
`null`. The original publisher PDF checksum and access depth are recorded.
This file contains no selected model settings or fitted parameters. Its
SHA-256 is pinned by the replay adapter; changing the extraction requires a
new source audit before replay.

`conditional_shao.compare_existing_fixture()` compared every corresponding
numeric entry in the existing `inputs.csv`, `measured_validation.csv` and
`reference_model_outputs.csv`: **zero numeric differences**. Existing source
fixtures and historical reports were not modified. The new extraction adds
explicit unresolved fields and keeps the Table 1 radius label versus Eq. 6
diameter prose conflict visible. The source's third printed slip error of
−4.84% recomputes from its displayed values to −4.8458%; this rounding
discrepancy does not change either displayed observation.

## Fixed adapter and what it assumes

[`data/shao2015_conditional_adapter.json`](data/shao2015_conditional_adapter.json)
names all working choices separately. Its executable convention fields and
numeric assumptions are checked against the fixed adapter implementation;
an unsupported change fails before candidate search. `physicroll.conditional_shao` uses the
original 4.10 → 2.9024 → 2.2087 → 1.72 mm gauges, 1360 mm width, Table 1
radius 210.81 mm, per-pass MPa tensions and speeds, and Table 2 friction
inputs. The reported speed is **assumed to be entry-strip speed**. Source
K = 276.5 MPa and n = 0.26 are transcribed with an explicit assumed
log-thickness to plane-strain-equivalent conversion. The initial 0.05 log
strain is a pre-existing scenario assumption, not an observed history or a
fit. The temper label, constant 293.15 K bookkeeping temperature, generic
2680 kg/m³ density, unity drive efficiency and assumed material envelopes
are also declared. The checked rigid slab uses 256 cells and established-bite
diagnostic. No thermal solver, elastic flattening, Eq. 3 history blend,
temperature feedback or physical equipment capacity is inferred.

The adapter accepts exactly the published three-pass route, and the bounded
search consequently evaluates **one candidate** and independently replays
it. The selected candidate is also recalculated on a 512-cell grid, versus
256 cells in the search replay. Maximum absolute relative force change was
2.1 × 10⁻⁷, and maximum absolute slip change was 8.9 × 10⁻⁹. These are
numerical checks, not empirical accuracy. This checks search-to-checked-solver wiring, units and state continuity;
it is not an optimisation of gauge or operating conditions. There are no
equipment checks or utilization score. Published measured forces are used
only below as comparison outputs, never as mill force caps. No parameter is
fitted to any measured force or slip in this increment.

## Conditional result

Residual = `(model − measured) / measured`. The same explicit adapter is used
for all three passes; no post hoc retuning occurs.

| Pass | Measured force (MN) | Predicted force (MN) | Force residual | Measured slip | Predicted slip | Slip residual |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5.1439 | 4.9853 | −3.08% | 0.0150 | 0.02128 | +41.89% |
| 2 | 5.0174 | 4.8664 | −3.01% | 0.0182 | 0.02510 | +37.89% |
| 3 | 4.3018 | 4.6370 | +7.79% | 0.0227 | 0.02810 | +23.79% |

All three checked mechanics passes met the numerical convergence gate, and
the next pass's accumulated equivalent strain exactly equals the previous
pass's outlet strain. These numerical checks do not close the empirical
gaps. The reported friction values may have been chosen using the same
force/slip observations; therefore these residuals are neither independent
validation nor a credible prediction interval. The source's approximately
±5% model discrepancy is not a measurement uncertainty or acceptance bound.

## Next acceptance gates

The chosen source does not identify incoming temper/history, Eq. 3 weight,
speed reference, stress/shear conversion, elastic constants, measured
thermal state, independent friction measurement or certified mill ratings.
A later one-parameter initial-strain fit, if undertaken, needs a frozen
convention and interval before using pass-1 measured force; it must report
fit boundary hits and all pass-1/2/3 force/slip residuals. Pass-2/3 holdout
would remain a within-chain conditional comparison because published
friction may have used those same observations. No such fit is implemented
here. A plant-feasibility acceptance requires separately sourced hard limits
and validated physical ranges; lack of full plant data does not prevent this
qualified conditional comparison.
