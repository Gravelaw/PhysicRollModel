# Report-sync packet: optional contact/material increment

Base: published **09d0d5b2e754ddcc9840e9b2d11fbdb07efd9b89**.
Working branch: `development/contact-hardening-increment` (local, pending review).
The delivery message supplies the resulting local commit; exact executable
source hashes are in `artifacts/contact_increment/reproducibility.json`.

## Corrections to carry into Word/PDF

1. Replace any assertion that reviewed v0.3 has not been pushed: commit 09d0d5b2
   was published on `development/aa5052-mechanics-review`. This later increment
   has not been pushed or merged.
2. Cite Erfanian, Mozhdeh; Brambley, Edward J.; Flanagan, Francis; O'Kiely,
   Doireann; O'Connor, Alison N. (2025), *Through-thickness modelling of metal
   rolling using multiple-scales asymptotics*, European Journal of Mechanics
   A/Solids **113**, 105712, [DOI](https://doi.org/10.1016/j.euromechsol.2025.105712).
   Keep equation numbers **21–28 explicitly attached to the [2024 preprint v1](https://arxiv.org/html/2408.01347v1)**.
   Journal metadata was checked against [arXiv](https://arxiv.org/abs/2408.01347)
   and the [author university record](https://pure.ul.ie/en/publications/through-thickness-modelling-of-metal-rolling-using-multiple-scale/).
   The parent supplied the verified [published PDF](https://wrap.warwick.ac.uk/191529/2/1-s2.0-S0997753825001469-main.pdf).
   Journal equation numbering is not asserted to match v1.
3. Add optional variable-strength equilibrium:
   `h*q' = h*Kps' + Kps*h' + 2*tau`, integrated as
   `z'= (Kps*h'+2*tau)/h`, `z=q-Kps`. Document the homogeneous equivalent
   strain path and explicitly assumed scalar material history (M1–M4).
4. Add optional circular Hitchcock `Rc=R*[1+16*(1-nu²)*F/(pi*E*b*draft)]`.
   Source: Li, Matsumoto & Utsunomiya (2018), *Experimental Study of Roll
   Flattening in Cold Rolling Process*, [DOI](https://doi.org/10.2355/isijinternational.ISIJINT-2017-623),
   Eq1. Stainless-steel analogue and circular-shape limitations; no aluminium
   parameter validation. Nominal `R`, not `Rc`, sets projected shaft torque
   and `omega=U/R`. Neither local elastic kinematics nor strip recovery is solved.
5. Preserve no-fit status and report both improved and worsened residuals.
   Equation/provenance/code/test mapping is in [contact-increment.md](contact-increment.md);
   every finding and the entry-boundary defect are in the
   [append-only log](mechanics-change-log.md).

## Actual fixed-gauge run

AA5052, width 1.36 m, gauges **4.10 → 2.9024 → 2.2087 → 1.72 mm**.
Reported friction/tension/speed values are unchanged. Common conditional bridge:
initial log strain 0.05; additive history; source K/n interpreted as logarithmic
thickness strain and uniaxial strength; reported speed interpreted as nominal roll
surface speed; Table1 radius interpretation. These remain assumptions. The
spatial example carries 293.15 K without thermal feedback. The circular example
assumes steel roll E=210 GPa and nu=0.3, without fitting.

Source data: Shao, Jian; Sun, Wenquan; He, Anrui; Li, Bo (2015), *Research on the
Thermal Calculaion Model of High Strength Aluminum Strip Rolling Based on Finite
Diffreence Method* (title spelling as published),
[DOI 10.18280/ijht.330113](https://doi.org/10.18280/ijht.330113), Tables1–2 p94.
Author-reported measured forces are 5.1439, 5.0174, 4.3018 MN; slips are
1.50%, 1.82%, 2.27%. These are not our model outputs, raw instrument traces,
or independent held-out trials. Source-calculated values remain separate in CSV.

| Structure | Pass | Predicted force [MN] | Force relative residual [%] | Predicted forward slip [%] | Slip relative residual [%] |
|---|---:|---:|---:|---:|---:|
| reviewed_rigid_mean | 1 | 4.690313 | -8.818 | 2.307407 | +53.827 |
| reviewed_rigid_mean | 2 | 4.772709 | -4.877 | 2.626322 | +44.303 |
| reviewed_rigid_mean | 3 | 4.582181 | +6.518 | 2.899930 | +27.750 |
| rigid_spatial | 1 | 4.985315 | -3.083 | 2.128417 | +41.894 |
| rigid_spatial | 2 | 4.866419 | -3.009 | 2.509656 | +37.893 |
| rigid_spatial | 3 | 4.637042 | +7.793 | 2.810011 | +23.789 |
| circular_mean | 1 | 4.882032 | -5.091 | 2.471298 | +64.753 |
| circular_mean | 2 | 5.114911 | +1.943 | 2.837497 | +55.906 |
| circular_mean | 3 | 5.040151 | +17.164 | 3.143180 | +38.466 |
| circular_spatial | 1 | 5.199293 | +1.077 | 2.269690 | +51.313 |
| circular_spatial | 2 | 5.221537 | +4.069 | 2.710140 | +48.909 |
| circular_spatial | 3 | 5.105771 | +18.689 | 3.045970 | +34.184 |

A slip of 2.307407% is a fraction of 0.02307407; its relative residual against
1.50% is +53.827%, not +0.807 percentage points written as a relative percent.
Both dimensionless absolute and relative residuals are retained in the CSV.

Across three passes, mean absolute relative force/slip residuals are:

| Structure | Force [%] | Forward slip [%] |
|---|---:|---:|
| reviewed_rigid_mean | 6.738 | 41.960 |
| rigid_spatial | 4.628 | 34.526 |
| circular_mean | 8.066 | 53.042 |
| circular_spatial | 7.945 | 44.802 |

Spatial hardening under rigid contact improves the aggregate conditional
comparison, with a worsened pass3 force residual. Adding circular flattening
increases load/slip and worsens aggregate residuals under the chosen assumptions.
These are changes in **comparison residuals**, not measured process improvements,
calibrated accuracy or proof that real roll flattening is absent. Defaults remain
unchanged. No new gauge optimisation or experimental gain is reported.

## Sensitivity, failure and inference limits

Fifteen explicit sensitivity hypotheses were executed around the combined
spatial/circular model: prior strain, friction, strength scale, stress/strain
conventions, radius interpretation, speed mapping, roll E, and one joint alternative.
Fourteen returned numerically accepted schedules. Zero prior strain rejected
because the zero-offset flow law cannot sustain the reported positive entry tension.
These ranges are analyst assumptions, not probability distributions.

Across the four structures and accepted hypotheses, each pass's force **and** slip
residual ranges cross zero. Thus even residual direction is not invariant across
all sampled interpretations. Speed-location alternatives give identical force,
torque and dimensionless slip in this rate-independent model, but different mass
flow and power. Those mechanical observations cannot identify speed location.
The half-radius source-prose interpretation gives much lower loads; this does
not resolve the contradictory source convention. See complete `hypotheses.json`.

A simultaneous force/torque/slip campaign with explicit speed locations,
material flow curves and processing history is required for identifiable parameter
inference. Roll elasticity/contact shape, repeated coils and uncertainty are also
needed. Fit shared physical parameters only where sensitivity and independent
measurements support identification. Retain whole coils/campaigns for held-out
validation; fitting all three connected published passes cannot supply that gate.

## Numerical evidence and rerun

54 unit tests pass, including the original 44. Added tests cover independent
variable-strength pressure integration; constant-law and stiff-roll limits;
independent bracketed radius root; width/speed dimensional scaling; state
continuity and analytic plastic work; zero/friction/tension/range rejections;
signed regenerative torque; full coupled refinement and old baseline regression.
The first fine-grid run exposed a one-ULP entry-boundary geometry error, which
was fixed by returning the exact specified thickness at entry. The regression
now covers the radius/mesh combination that triggered it.

Final comparison uses checked 512/1024-cell solves. The complete coupled model
was additionally compared against 256/512-cell solves. Maximum force change
was below 2.48e-7 relative; absolute slip change below 7.93e-9. Across retained
accepted cases, maximum relative mechanical-work residual was
**7.45616967e-07**, maximum mass-flow residual was
**7.46069873e-15 kg/s**, and maximum circular-radius closure
residual was **9.92865681e-09**.
These are numerical residuals, not experimental error bars.

```
python -m unittest discover -s tests -v
python scripts/smoke.py
python scripts/run_contact_increment.py --cells 512 --out artifacts/contact_increment
```

Evidence: `before_after.csv`, `summary.json`, `structural_comparisons.json`,
`hypotheses.json`, `unit_audit.json`, `reproducibility.json`, `checksums.json` in
`artifacts/contact_increment`. The 49 raw-to-SI source conversions remain the
same; 36 derived quantities remain recorded with unresolved source semantics.
No thermal, metallurgy, residual-stress, flatness or fracture validation is
implied by these mechanics tests. The physical closure remains projected,
isothermal, homogeneous plane strain with Coulomb sliding and optional circular
compliance; the assumed parameter envelopes are not plant operating limits.

Clean extracted package verification: 54/54 tests and portable smoke pass; all
seven regenerated study files match byte-for-byte in this build environment.
Independent acceptance on the parent's other computer has not yet been run for
this increment. Existing reviewed scene and results are preserved.
