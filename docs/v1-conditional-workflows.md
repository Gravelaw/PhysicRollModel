# V1 conditional benchmark and sensitivity adapters

The W3 public API `physicroll.workflows.run_workflow` and the versioned
`--run-spec` CLI now accept two frozen Shao AA5052 templates:

```bash
python -m physicroll --run-spec scenarios/v1_shao_benchmark.runspec.json --output benchmark.json
python -m physicroll --run-spec scenarios/v1_shao_sensitivity.runspec.json --output sensitivity.json
```

Both use the installed audited records, verify exact source/card SHA-256 hashes
before execution, reject changed model/numerical conventions, and preserve the
no-fit assumptions and unknown measurement uncertainty. The benchmark retains
the fixed three-pass source comparison, the prior-log-strain 0.05 assumption,
and the 256/512-cell numerical comparison. The sensitivity replays only the
four previously declared prior-history assumptions. Its zero-history rejection
is a checked-model rejection, not a claim that a published pass was impossible.

The benchmark ResultBundle stores signed force/slip residuals and numerical
differences. The sensitivity ResultBundle stores every case, including the
rejected one. Both have missing equipment capacities, `NONE` bounds coverage,
`INDETERMINATE` bounds status, `NOT_ASSESSED` scientific qualification and
operating readiness. Only the benchmark's declared grid-comparison gate is
marked numerically passed; sensitivity does not inherit that conclusion.
Neither path fits material parameters, supplies independent flow data, or
establishes a mill limit or validation tolerance.

Tests compare CLI/API result digests, frozen residuals, rejection records,
resource-hash tamper failures and installed-wheel execution outside the
checkout. Search and O0 remain the W3 adapters still to build. W4 will
generalize hash resolution and replay across all saved run bundles.
