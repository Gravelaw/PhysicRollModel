# Shao AA5052 prior-history sensitivity, without fitting

Recorded 8 October 2026, following the [fixed conditional replay](conditional-benchmark-2026-10-02.md).
This is the next bounded P2 numerical experiment from the
[research roadmap](comprehensive-audit-2026-10-02/roadmap.md). It varies only
the assumed incoming log-thickness strain across `0, 0.01, 0.05, 0.20`, the
values already declared in
`scenarios/literature/shao2015_aa5052/assumptions.json`. The new
[machine-readable study contract](data/shao2015_prior_sensitivity.json)
identifies those values as analyst assumptions. They are neither source
measurements, confidence limits nor certified process bounds.

All four cases retain the audited Shao three-pass gauges, tensions, width,
Table 1 radius interpretation, reported friction, source K and n, entry-strip
speed interpretation, rigid slab solver, material envelopes and constant
bookkeeping temperature. Each candidate replays the complete chain from a
distinct initial state. No material parameter is fitted, no friction is
retuned, and observed loads are never equipment capacities. The zero-prior
case fails the checked model's first-pass boundary-tension screen because
the assumed zero-offset power law has zero entry strength. This is a rejection
of that *model and assumption combination*, not evidence that the published
mill pass was impossible.

| Assumed prior log strain | Checked status | Predicted forces, passes 1–3 (MN) | Signed force residuals, passes 1–3 | Signed slip residuals, passes 1–3 |
|---:|---|---|---|---|
| 0.00 | Rejected at pass 1 | — | — | — |
| 0.01 | Indeterminate | 4.7171, 4.7705, 4.5758 | −8.30%, −4.92%, +6.37% | +39.30%, +37.28%, +23.54% |
| 0.05 | Indeterminate | 4.9853, 4.8664, 4.6370 | −3.08%, −3.01%, +7.79% | +41.89%, +37.89%, +23.79% |
| 0.20 | Indeterminate | 5.6889, 5.1855, 4.8486 | +10.60%, +3.35%, +12.71% | +47.60%, +39.65%, +24.54% |

Residual means `(model − measured) / measured`. The observed pass-1 force lies
between the predictions at assumed priors 0.05 and 0.20. This establishes a
bracket on **this discrete conditional model response** only. Three successful
points do not establish parameter identifiability, a confidence interval or
physical prior strain. Pass-1 slip is not fitted and remains substantially
high throughout; force agreement alone would hide that mismatch. The three
published passes are correlated, and the source friction may already reflect
the same force/slip observations. Pass-2/3 comparisons are therefore neither
blind holdouts nor independent validation.

The function `run_declared_prior_sensitivity()` records every case's status,
rejection reason and signed per-pass comparison. Its contract cross-checks
the existing declared list and fixed adapter; a changed value or attempted
equipment limit fails before replay. No foil, thermal, torque, operational
phase or plant-safety claim follows. A later one-parameter fit would need its
own frozen convention, declared bounds and all residuals reported, including
any boundary hit; it is not performed here.
