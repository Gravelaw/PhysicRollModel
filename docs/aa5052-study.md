# AA5052 literature comparison and conditional gauge search

**Executed mechanical what-if study, not a validated mill schedule.** The case is
AA5052 strip, 1360 mm wide, rolled in three sequential single-stand passes from
4.10 to 1.72 mm. The proposed end use is cut-to-length stock for appliance panels
or general sheet-metal work. That end use is consistent with the categories in
[Hulamin's 5052 data sheet](https://www.hulamin.com/sites/default/files/downloads/5052%20Data%20Sheet.pdf),
but is not stated for the tested stock. Incoming/final temper, downstream bend
performance and any anneal/stabilisation/leveling remain unspecified.

The numerical inputs and author-reported observations are from Jian Shao, Wenquan
Sun, Anrui He and Bo Li (2015), *Research on the Thermal Calculaion Model of High
Strength Aluminum Strip Rolling Based on Finite Diffreence Method*, IJHT 33(1),
91–98, [DOI 10.18280/ijht.330113](https://doi.org/10.18280/ijht.330113),
[primary article](https://www.iieta.org/journals/ijht/paper/10.18280/ijht.330113).
Original Table1/2 numbers are stored separately from SI conversions, source model
outputs and our predictions. Nothing has been fitted to the three observations.

## Repeat the actual run

From the repository root, Python 3.10+ and its standard library suffice:

```bash
python -m unittest discover -s tests -v
python scripts/audit_literature_units.py
python scripts/run_literature_study.py \
  --speed-interpretation roll_surface \
  --strain-convention log_thickness \
  --stress-convention uniaxial \
  --prior-log-strain 0.05
```

All four interpretation arguments are explicit. They do not resolve the paper's
missing history, stress/strain pairing or speed definition. The run additionally
evaluates both other speed interpretations and constitutive sensitivities. Change
`--out /tmp/aa5052-rebuild` to retain bundled files. The optional comparison figure
uses the already installed/pinned preview dependency, never a required solver
package:

```bash
python scripts/plot_literature.py
```

See [mechanics and unit audit](mechanics-audit.md) for the corrected equations,
rejections and independent numerical tests. Source files live in
`scenarios/literature/shao2015_aa5052/`. The converter accepts 49 numeric source
values, preserves each original unit and scope, and emits its 36 derived geometry/
force/error diagnostics. This is arithmetic verification with **unresolved
semantics**, not a validated parameter envelope.

## Executed assumptions and baseline

For this named what-if, K=276.5 MPa and n=0.26 are interpreted as an uniaxial law
in logarithmic thickness strain. We assume prior log strain 0.05, additive history
and no anneal/reset; these do not reproduce the paper's missing-coefficient Eq3.
The corresponding conversion to equivalent strain is explicit in the code, with
no extra yield offset. Each pass uses the exact interval-mean flow stress in a
constant-yield rigid-roll slab. Table1's radius label is followed; reported speed
is **assumed** to be roll surface speed. Fixed friction and both tensions are the
reported values. Generic manufacturer density is 2680 kg/m3. Material calibration
ranges and source-stock temperature/strain-rate/temper remain unknown.

| Pass | Entry → exit [mm] | Author force [MN] | Our force [MN] | Relative force residual | Author slip [%] | Our slip [%] | Relative slip residual |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 4.1000 → 2.9024 | 5.1439 | 4.6903 | −8.82% | 1.50 | 2.3074 | +53.83% |
| 2 | 2.9024 → 2.2087 | 5.0174 | 4.7727 | −4.88% | 1.82 | 2.6263 | +44.30% |
| 3 | 2.2087 → 1.7200 | 4.3018 | 4.5822 | +6.52% | 2.27 | 2.8999 | +27.75% |

Mean absolute relative residual is 6.74% for force and 41.96% for slip. No
measurement uncertainty was reported, so these are residuals, not statistical
acceptance tests. The source's own model force/slip columns are retained separately;
its claimed agreement is not our implementation's agreement. The first pass's
untensioned self-bite diagnostic gives 0.075533 versus reported mu=0.075. We preserve
that flag without treating an untensioned threading rule as a rejection of an
established tensioned pass or changing friction to manufacture feasibility.

## Conditional constrained optimisation

Decision variables are two intermediate exit gauges. The entry/final gauges,
three passes, width, roll radius, speeds, tensions and friction are fixed. The
objective is the maximum predicted stand separating force. Each reduction is
constrained to **22.1261–29.2098%**, the source schedule's extrema used solely as
an analyst trust-region assumption. There are no source force/torque/power ratings
or allowable tension limits, so the search cannot establish physical mill safety.

The deterministic search evaluates global 21×21 and 41×41 reduction grids, the
published point, and a local 21×21 refinement. It considers 2,564 pairs; 1,682 pass
the trust-region/solver screens. Search grids are explicitly unchecked coarse
integrations. Both the selected schedule and the same-assumption baseline are
then re-evaluated on 512/1024-cell grids with work/convergence checks.

| Quantity | Reported schedule under our assumptions | Selected conditional schedule |
|---|---:|---:|
| First intermediate exit gauge [mm] | 2.9024 | 2.9045782 |
| Second intermediate exit gauge [mm] | 2.2087 | 2.2320736 |
| Final gauge [mm] | 1.7200 | 1.7200 |
| Maximum predicted force [MN] | 4.772709 | 4.684200 |
| Predicted peak-force change | — | −1.8545% |

Selected reductions are 29.1566%, 23.1533%, 22.9416%, and pass forces are about
4.68420, 4.68265, 4.68361 MN. Maximum final baseline/selected relative work residual
is below 8e-8. A constrained mesh search does not prove the continuous global
optimum; quoted extra gauge digits identify a reproducible numerical result, not
manufacturing tolerances. The 1.85% objective improvement is smaller than the
baseline force discrepancies. Without calibration and capacity data this is
credible only inside the assumed computational model, not as a plant-ready
schedule or evidence that real peak load will improve.

## What the sensitivities actually establish

`artifacts/aa5052/sensitivity.json` retains twelve alternatives, including rejections.
They are chosen perturbations, not confidence intervals or a probability model.

- Zero prior strain with unshifted Hollomon and positive entry tension rejects.
- Assumed prior log strain 0.01 or 0.20 materially shifts loads; first-pass force
  changes from about 4.361 to 5.491 MN. The selected schedule's peak-load advantage
  falls to about 0.11% in the 0.20 case. This is not calibrated history recovery.
- Friction ±10% and K ±10% are perturbations of uncertain states/parameters, never
  freely optimised process controls. Alternative equivalent-strain and plane-strain
  stress interpretations are explicit, not silently mixed coefficients.
- Reading 210.81 mm as diameter gives a distinct half-radius diagnostic (roughly
  3.063/3.152/3.026 MN). That sensitivity exposes the source wording conflict; it
  does not resolve which interpretation matches the mill.
- Roll/entry/exit speed interpretations change inferred flow and power, while
  this rate-independent model's force/slip are unchanged. Thus force agreement
  cannot identify the speed location. Different throughputs between sequential
  passes of one stand are allowed; within each pass mass is conserved.

Neither temperature nor heat is validated from these observations. The separate
thermal foundation still runs and conserves its two-body budget, but no material
heat fractions, coolant coefficients or source-stock temperature measurements
are supplied by this benchmark. There is no crown, flatness, residual-stress,
metallurgy, fracture, end-use strength or final-temper simulation in this study.

## Files retained

| File under `artifacts/aa5052/` | Meaning |
|---|---|
| `unit_audit.json`, `values_long.csv` | Original values/units → SI, dimension, quantity scope and source locations; unresolved semantics retained |
| `process_inputs_si.csv`, `measured_validation_si.csv` | Converted source input and measurement tables |
| `reference_model_outputs_si.csv`, `source_context.json` | Source-calculated outputs, printed errors, source references and assumptions, kept separate |
| `baseline.json`, `baseline_vs_measurements.csv` | Our fully flagged predictions and measured residuals |
| `optimisation.json`, `search_candidates.csv` | Objective, constraints, checked final solutions and every search candidate/rejection |
| `sensitivity.json`, `summary.json` | Interpretation/parameter alternatives, rejection reasons and compact actual metrics |
| `comparison.png` | Source measurements, source model and our predictions visibly distinguished |
