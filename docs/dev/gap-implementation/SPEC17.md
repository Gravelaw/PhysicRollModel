# SPEC17 — Phase 0 of the coverage-gap study: corrections, benchmarks and screens that need no new solver

Repository `/home/user/PhysicRollModel`, planned against commit `8f10cbe` (2026-11-19). House rules:
section 0 of `SPEC.md` in this scratchpad directory, with the two changes of G1 below. Source of
every new fact: `docs/simulation-coverage-gaps.md` (the gap study) and the four gap reports in
`docs/research/band-screening-2026-11/`. Nothing else may be used as a source. Do not commit.

Nine work packages, executed one at a time in the order given, each leaving the repository green.
Read section G (rules for every package) before any package.

Scratch material of the planner, usable as starting points (copy, do not import from the repo):
`scratchpad/s21/jdiff.py` (JSON diff with paths), `v1.py` (benchmark run), `g7.py` (inlet-angle
experiment), `shp.py` (zone operator prototype), `nums.py`, `nums2.py`, `g4a.py`, `g4b.py`,
`g4c.py` (worked numbers). They are prototypes, not specifications; where they differ from this
text, this text holds.

---

## G. Rules for every package

**G1. House rules.** `SPEC.md` section 0 applies (standard library only, Python >= 3.10, SI names
with unit suffix, JSON-safe results with `allow_nan=False`, frozen status
`SCREENING_RESULT_NOT_PLANT_VALIDATED`, `flags` / `limitations`, no probabilities, `unittest`,
each test module under 60 s, lines <= 100). Two changes: (1) this block DOES modify existing
modules, scenarios, tests and committed artifacts, but only where a package says so; (2) each
package ends with the artifact step of G6.

**G2. Tags travel with numbers.** The reports tag every formula and number (FT, EX, AB, VP,
[M] from memory, [D] / "derived" / "computed here", [run], "model output"). A tag is copied into
(a) the code comment at the constant or formula, (b) a `basis` entry or note of the result, (c)
the documentation sentence. Never promote a tag. Where this brief re-derives a formula from first
principles, the tag is `[D, re-derived in SPEC17]` and the derivation given here goes into the
module docstring. Do not add constants, thresholds or formulas that are not in this brief; if one
seems missing, stop and report.

**G3. No silent change of the ranking.** Packages 3 to 8 add NO evidence item and change NO
evidence item, score, standing or leader. Package 2 changes two rule outputs, listed there with
every moved score. Each package proves this with the score check of G6.

**G4. Opt-in inputs.** Schema stays `physicroll.band_case.v2`. Every new case key is optional;
`validate_case` normalises an absent key to `None` (or the stated default), as
`band_width.WIDTH_DEFAULTS` does today, so the `inputs` block of every result gains the new keys
with null values. Every new result section exists in every v2 result: without its input it is
`band_process.not_supplied('<reason>')` (`{'status': 'NOT_SUPPLIED', 'not_supplied': True,
'reason': ...}` — read `band_process.not_supplied`, line 64, and use it). A v1 result gets the
same not-supplied entry for a new TOP-LEVEL section (as it has for `gauge_control` today) and
nothing else; the v1 HTML report stays byte-identical. Consequence:
committed artifacts change ADDITIVELY in these packages (new keys only); G6 says how to prove it.

**G5. Invariants of the guided app that engine packages must keep green**
(`tests/test_band_plain.py`, about 40 s):
- every top-level flag that appears in a committed demo result needs an entry in
  `band_plain.FLAGS` (line 2122) — add one plain sentence (no engine tokens, no forbidden words
  of `band_plain.FORBIDDEN`) in the same package that introduces the flag;
- every evidence `criterion` string needs an entry in `band_plain.CRITERIA` (line 1962): do not
  rename a criterion string; no package adds one;
- `scenarios/band_diagnosis_template.json` has exactly 31 observation keys: add no observation
  key in this block;
- every key of the template's `width_model.roll`, `width_model.spray_header` and
  `tribology.surface_finish`, and every key in `band_process.TRIBOLOGY_KEYS` /
  `TRIBOLOGY_OPTIONAL`, must have a question: do not add keys there except where a package
  says so and adds the question.
New optional sections ARE added to the template with value `null` and a line in its `notes`.

**G6. End of every package — in this order.**
1. Tests: the package's own modules, then
   `python -m unittest tests.test_chatter tests.test_foil_bite tests.test_strip_shape
   tests.test_roll_thermal tests.test_bite_tribology tests.test_band_signatures
   tests.test_band_diagnosis tests.test_band_v2_sections tests.test_band_lengthwise
   tests.test_band_foil tests.test_band_extended_domain tests.test_band_robustness
   tests.test_band_thermal_check tests.test_band_process_temperatures tests.test_band_products
   tests.test_band_survey tests.test_band_plain tests.test_band_plain_partial
   tests.test_band_app tests.test_band_app_drawing tests.test_band_app_reopen` and
   `python scripts/smoke.py`. Never `unittest discover` (about 8 minutes).
2. Regenerate into a scratch directory, not into the repository:
   `python -m physicroll.band_cli scenarios/band_diagnosis_<name>.json --out <scratch>` for
   `battery_foil` (about 70 s), `lengthwise_bands` (50 s), `thin_gauge_chatter` (17 s),
   `bearing_order` (9 s), and `--product-survey --out <scratch>`. At commit `8f10cbe` a fresh run
   of the four demos is byte-identical to `artifacts/band_diagnosis/` (verified by the planner).
3. Diff old against new result JSON with `s21/jdiff.py`. Classify every differing path as
   (i) added key, (ii) changed value. The package text lists what is allowed. For "additive
   only" packages: zero changed values, and every added key under the paths the package names.
   Score check, all packages: `[(h['id'], h['score'], h['standing'], h['rank']) for h in
   result['hypotheses']]` and `leading_hypotheses` equal before and after, except as listed in
   package 2.
4. Only then copy the regenerated pairs over `artifacts/band_diagnosis/`. Report for each of the
   five pairs: byte-identical, additive only, or changed (with the list).
5. Documentation of the package (G7). Numbers quoted in a document are read from the regenerated
   artifacts or from a test, never typed from this brief without re-running.

**G7. Documentation moves with code.** Each package edits `docs/band-diagnosis.md` in the sections
it names (inputs in 5 / 5.3, theory in 7 to 10, report in 12, verification table in 13,
limitations in 14, sources in 15) and adds its rows to the gap study's status section:

- Package 1 creates `## 11. Implementation status` in `docs/simulation-coverage-gaps.md`, placed
  after section 10 and before Appendix A, with this table and one row per gap it touches:
  `| gap | status | what exists now | where | still open |`. Status words, fixed:
  `BENCHMARK_ENCODED`, `CORRECTED`, `SCREENING_VERSION` (supplied-input or screening form of the
  row's model; the row's full model is not built), `RULE_CHECK`, `TABLE_ADDED`, `TEXT_CORRECTED`.
  It also changes line 3 of the study to: "A literature gap study, dated 2026-11-18. **Nothing in
  this document was implemented or validated when it was written.** Section 11 lists what has
  been implemented since; none of it is validated on a mill." and appends "(status: section 11)"
  to the Phase 0 heading of section 8. No other text of the study is rewritten. Later packages
  only append rows.
- README: one or two sentences in the band section where a package is user-facing (packages 4
  to 8), and the capabilities row if `docs/capabilities.md` has one for the band tool.

**G8. Report back per package:** what was built; each worked number of the package as measured
(this brief's value, the implementation's value); test counts and timings; the artifact
classification of G6.4; every deviation from this brief with the reason; anything in the reports
found ambiguous.

---

## 1. Overview

| # | Package | Gap ids | What changes for a user | Depends on | Size (lines changed, with tests and docs) |
|---|---|---|---|---|---|
| 1 | Benchmark harness | BT-G17, G16 (part), X18, X26, X31 | `python -m physicroll.benchmarks` prints project values beside published ones; the 0.42 load ratio of the foil bite is a recorded, tested discrepancy | none | 500-650 |
| 2 | Bite and film corrections | BT-G7, BT-G8, X19-X24 | Film ratios at foil gauge fall by 1.45-3.3 times; no "boundary" label on normal operation; the heat-streak rule loses one weak point; one flag renamed | none | 400-550 + all five artifact pairs |
| 3 | Rule checks, tables, remaining text | A5 (basis only), A10, B3, B4, X3, X7, X12 | Spray-coefficient basis stated in the thermal check; flash-point check; alloy-group and anisotropy tables in the product guide | none | 550-750 |
| 4 | Shapemeter operator | C7 (zones), G5 (sensor part), X9 | New optional `measurement.shapemeter`: what each shapemeter zone would read for every modelled band; dilution; which nozzles sit under which zone | none | 750-900 |
| 5 | Thickness gauge transfer | C7 (gauge part) | New optional `measurement.thickness_gauge`: what a gauge with a given spot and time constant keeps of a mark pitch; observations it cannot resolve are flagged | 4 (section and validation frame) | 300-450 |
| 6 | Strip temperature as a flatness term | A1, G6 (supplied profile) | New optional `width_model.strip_temperature`: flatness as measured hot against after cooling | 4 (zone readings of the hot profile) | 550-700 |
| 7 | Friction / film stripe screen | BT-G4 (screen) | New optional `width_model.friction_stripe_screen`: I-units per percent of local friction difference per pass, supplied stripes as a second band source | 2, 4 | 650-800 |
| 8 | Measured roll profile; tension-line pitch | G13, G12 | New optional `width_model.roll_ground_profile` through the existing transfer; candidate tension-line pitch from coil and roller radius | 4 | 600-750 |
| 9 | Guided app | plant-facing side of 4-8 | Questions for shapemeter, gauge, temperature scan, roll profile; plain words and one picture for the new outputs | 4-8 | 700-900 |

Out of scope for all packages (Phase 1 and later): half-space bite, shear cap, friction closure,
computed heat split, per-width strip heat balance, flatness controller, winding model, roll stack,
any change to the mattress foundation coefficient, any new hypothesis, any new observation key.

---

## Package 1 — Benchmark harness (BT-G17, G16 in part, X18, X26, X31)

### Why
The bite report found one published foil-bite case with every input stated (Fleck et al. 1992,
Fig. 9; BT-S1, read FT) and ran the project's mattress bite on it: 0.42 of the half-space
reference load [run]. The project's documents still say that no such benchmark was found (X18,
"contradicted"). The study asks to encode the published cases as tests first, "to show how far off
the present models are before anything is built on them" (section 8).

### Design

New module `physicroll/benchmarks.py` (no change to any solver). New test module
`tests/test_benchmarks.py`. Status string of the module:
`STATUS = 'SOFTWARE_COMPARISON_WITH_PUBLISHED_VALUES_NOT_PHYSICAL_VALIDATION'`.

**How a discrepancy is recorded (the rule for this and all later phases).** A benchmark has three
separate things, never merged:
1. `project_value`: computed now by calling the solver.
2. `recorded_project_value`: a literal in `benchmarks.py`, with the date and commit it was taken
   at. A test asserts `project_value == recorded_project_value` to a relative `1e-6`. This is
   SOFTWARE verification: it fails loudly when any later change moves the number, and the fix is
   then to re-record deliberately (new literal, new date, a line in section 13 of the guide), not
   to loosen the tolerance.
3. `verdict` against the published reference, one of
   `RECORDED_DISCREPANCY` (project value outside `agreement_band` of the reference),
   `WITHIN_AGREEMENT_BAND`, `INDICATIVE_ASSUMED_INPUTS` (an input the source does not state was
   assumed), `REFERENCE_READ_BY_EYE`, `REFERENCE_ONLY_INPUTS_NOT_RECORDED`.
   `agreement_band` is `(0.9, 1.1)` on the ratio project / reference for every case (analyst
   choice [D], stated in the module docstring: a published model-to-model value read from a
   paper is not expected to be met closer than 10 %). A test asserts the verdict literal. A
   `RECORDED_DISCREPANCY` test is named `test_<id>_recorded_discrepancy_...` and its docstring
   says: "Passing this test does not mean the physics is right. It records that the model is
   <ratio> of the reference."

Public API:

```python
CASE_IDS = ('BT-V1', 'BT-V2-R89', 'BT-V2-R135', 'BT-V3-FIG1-140UM', 'BT-V3-EQ29',
            'SS-V2', 'SS-V3', 'TM-LC7')
def run_case(case_id: str) -> dict      # ValueError for an unknown id
def run_all() -> dict                   # {'status': STATUS, 'cases': [run_case(i) for i in CASE_IDS],
                                        #  'not_encoded': NOT_ENCODED, 'limitations': [...]}
def table_rows(result=None) -> list     # rows for the guide: id, quantity, project, reference, ratio, verdict
def fleck_dimensionless_load(force_per_width_n_m, roll_radius_m, plane_strain_yield_pa,
                             roll_plane_strain_modulus_pa) -> float
def fleck_regime_boundary_entry_gauge_m(roll_radius_m, reduction, friction_coefficient,
                                        plane_strain_yield_pa, roll_plane_strain_modulus_pa) -> float
def chatter_onset_comparison(stand: dict, spans: dict, bite_pass: dict, *, measured_critical_speed_m_s,
                             measured_frequency_hz, bite_damping_transit_fraction=0.5,
                             roll_youngs_modulus_pa=210e9, roll_poisson_ratio=0.3, cells=256) -> dict
def main(argv=None)                     # python -m physicroll.benchmarks [--json]
```

Each `run_case` result: `{'id', 'title', 'source', 'source_id', 'read_status', 'reference_kind'
('MODEL_OUTPUT' | 'MEASUREMENT' | 'PUBLISHED_FORMULA' | 'FIGURE_READ_BY_EYE'), 'inputs' (SI, every
value), 'input_notes' (list of sentences: where each input comes from, which are assumed),
'quantities': [{'name', 'unit', 'project_value', 'recorded_project_value', 'recorded_on',
'reference_value', 'reference_label', 'ratio_project_to_reference'}], 'verdict', 'agreement_band',
'note', 'flags'}`. JSON-safe.

Formulas [BT-S1 FT as restated in gap-bite-tribology.md section 2.1]:
- `W_bar = W * E_R* / (R * Y_s^2)`; `W` = roll load per unit width [N/m], `E_R*` = roll plane-strain
  modulus `E/(1 - nu^2)` [Pa], `R` = undeformed roll radius [m], `Y_s` = plane-strain yield stress
  of the strip [Pa].
- Regime boundary (eq. 29): `h_0c = 12 * R * r^0.5 * mu^1.24 * (Y_s/E_R*)^0.76`; `h_0c` = entry
  gauge [m] below which a neutral (no-slip) zone appears, `r` = reduction fraction.

Case definitions (all values exact; the mattress solver takes a uniaxial flow stress `Y`, so
`mean_flow_stress_pa = Y_s * sqrt(3)/2`, and a Young's modulus, so
`roll_youngs_modulus_pa = E_R* * (1 - 0.3^2)` with `roll_poisson_ratio = 0.3`; call
`foil_bite.solve_mattress_bite(h0, h1, 1.0, R, Y, mu, t_b, t_f, roll_youngs_modulus_pa=...,
roll_poisson_ratio=0.3)` with default `cells=400`, `contact_end_zones=True`):

| id | inputs | reference (kind, read) | project value, verified by the planner | ratio | verdict |
|---|---|---|---|---|---|
| `BT-V1` | `h0 = 20e-6`, `h1 = 15e-6` (25 %), `R = 0.089`, `Y_s = 230e6` (so `Y = 199185842.87`), `E_R* = 230e9` (so `E = 209.3e9`), `mu = 0.03`, tensions 0. The source's `E_s* = 80 GPa` is not an input of the rigid-plastic mattress: say so in `input_notes`. | `W_bar` 118 half-space, 120 perturbation, 62 Fleck-Johnson mattress (MODEL_OUTPUT, FT) | `force_per_width_n_m = 1018841.8703`, `W_bar = 49.772441`, regime `foil`, forward slip `0.169779` | 0.42180 (to 118), 0.41477 (to 120), 0.80278 (to 62) | `RECORDED_DISCREPANCY` |
| `BT-V2-R89`, `BT-V2-R135` | `h0 = 73e-6`, `h1 = 73e-6 * (1 - 0.57) = 3.139e-05`, `Y_s = 230e6`, `E_R* = 230e9`, `mu = 0.026`, `t_b = 0.107*Y_s`, `t_f = 0.132*Y_s`; `R = 0.089` or `0.135` ASSUMED (the source does not state the radius, the speed or the width) | measured `W_bar` 58 (MEASUREMENT, FT; friction 0.026 was inferred by the authors from this load) | `W_bar = 41.068824` (R 89 mm), `51.052946` (R 135 mm) | 0.7081, 0.8802 | `INDICATIVE_ASSUMED_INPUTS` |
| `BT-V3-FIG1-140UM` | `h0 = 140e-6`, `h1 = 70e-6`, `R = 0.089`, `Y_s = 230e6`, `E_R* = 230e9`, `mu = 0.03`, tensions 0 | "about 50" read by eye from the r = 50 % curve of Fig. 4 by the report (FIGURE_READ_BY_EYE) | `W_bar = 45.968340`, regime `conventional` | 0.919 | `REFERENCE_READ_BY_EYE` |
| `BT-V3-EQ29` | eq. 29 for (a) the BT-V1 mill (`R 0.089, r 0.25, mu 0.03, Y_s 230e6, E_R* 230e9`), (b) the Fig. 1 case (`r 0.5`), (c) the battery-foil demo mill (`R 0.135, r 0.4, mu 0.03, E_R* = 210e9/0.91`) with `Y_s = 175e6` and with `Y_s = 175e6*2/sqrt(3)` | PUBLISHED_FORMULA (FT) | (a) `36.24 um`: entry 20 um is below, project regime `foil`; (b) `51.25 um`: entry 140 um is above, project regime `conventional`; (c) `56.35 um` and `62.86 um` | - | `WITHIN_AGREEMENT_BAND` is not used here: verdict `CONSISTENT_REGIME` when the project regime agrees on (a) and (b); add this word to the verdict list |
| `SS-V2` | steel, `t = 0.5e-3`, buckle width `b = 0.150` (half-width 75 mm), measured half wavelength 60 mm; ASSUMED `E = 210e9`, `nu = 0.3`, uniform compression over `b` | computed critical 5.3 I-units simply supported, 6.38 elastic restraint, 8.92 clamped; waves seen at 7.5-8, none below 6 (SS-S19, FT, formulas garbled) | `strip_shape.narrow_band_buckling_stress_pa(0.5e-3, 0.150, 210e9, 0.3)` = `8435559.32 Pa` = `4.016933` I-units (`1e5*sigma/E`); assumed half-wave / measured half-wave = `150/60 = 2.5` | 0.7579 (to 5.3) | `INDICATIVE_ASSUMED_INPUTS` |
| `SS-V3` | aluminium 0.4 -> 0.3 mm, buckle width 105 mm, wavelength about 75 mm (SS-S19 FT) | measurement | assumed half-wave (= buckle width, the project's mode) / measured half-wave = `105/37.5 = 2.8` | - | `RECORDED_DISCREPANCY` (mode shape only; no critical value is compared) |
| `TM-LC7` | none recorded | measured onset 5.81 m/s, 124.6 Hz; the paper's own model 6.42 m/s (with span wave dynamics), 6.57 m/s (without), 129 Hz (TM-LC7 EX, OD-22 EX; two-stand steel mill, 2 mm entry, third pass) | not run | - | `REFERENCE_ONLY_INPUTS_NOT_RECORDED` |

The report's own figure for (c), "54-63 um" [derived], is not reproduced at its lower end
(56.35 here with the stated inputs). Record both in the note; do not adjust inputs to match.

**The steel chatter onset (X31) cannot be run from what the repository holds.** The reports
quote the measured onset "with published mill parameters" but none of the parameters (roll
masses, stiffnesses, damping, gauges, flow stress, friction, tensions, span lengths) is written
down in the repository, and a tandem mill is outside the single-stand model (the thermal report:
single-stand models over-predict two-stand critical speeds by 42 % on average, TM-LC6 EX). So
this package builds the harness and the reference record only:
- `chatter_onset_comparison` builds `chatter.StandModel.from_modal_damping(...)` (read its
  signature at `chatter.py` line 228), `StripSpans`, `BitePass`, calls `derive_bite_response` and
  `critical_speed`, and returns predicted critical speed and onset frequency with and without
  bite damping beside the measured pair, with ratios and the flags of the bite.
- Software check of the harness on the project's own demo (not a benchmark): with the stand,
  spans and pass of `scenarios/band_diagnosis_thin_gauge_chatter.json` it must return
  `13.267836` m/s and `189.109442` Hz with bite damping (fraction 0.5) and `4.829571` m/s,
  `188.911169` Hz without, the values of the committed artifact
  (`chatter.with_bite_damping` / `without_bite_damping`).
- `TM-LC7` stays `REFERENCE_ONLY_INPUTS_NOT_RECORDED` unless the session can open the paper
  itself (ISIJ Int. 55(3) 2015, 637; URL in the study, section 9, TM-LC7) AND reads every needed
  parameter from its tables. Then: add them as `inputs` with table number and read tag per value,
  mark each value the paper does not give as ASSUMED with the reason, run, record, and set the
  verdict by the rule above. Never fill a parameter from memory or from another mill. If the
  paper cannot be opened, change nothing and say so in the report back.

`NOT_ENCODED` (a tuple of `{'id', 'reason'}` printed by `main` and listed in the guide):
`BT-V4` (needs the friction closure of BT-G3; figures must be digitised), `BT-V9` (forward slip
without load data; needs a friction value per row, i.e. BT-G6), `SS-V1`, `SS-V4` (need the
buckling model of G4), `SS-V5` (needs the profiles of the paper), `SS-V11` (already encoded:
`physicroll/literature.py`, `tests/test_literature.py`; cross-reference only), all remaining SS-V
and BT-V rows ("needs a model of a later phase or data not in the repository").

### Tests (`tests/test_benchmarks.py`)
- `test_bt_v1_software_pin`: project `W_bar` equals 49.772441 (rel 1e-6); `force_per_width_n_m`
  equals 1018841.8703 (rel 1e-6); regime `foil`.
- `test_bt_v1_recorded_discrepancy_mattress_is_0_42_of_half_space_load`: ratio in
  `[0.415, 0.428]`; verdict `RECORDED_DISCREPANCY`; ratio to the Fleck-Johnson mattress value in
  `[0.79, 0.81]`; `assertFalse(0.9 <= ratio <= 1.1)`.
- `test_bt_v1_grid_independent`: `cells` 200 and 800 give `W_bar` within 1e-6 relative of 400
  (planner: 49.77244109, 49.77244115).
- `test_bt_v2_assumed_radius`: both pins; verdict `INDICATIVE_ASSUMED_INPUTS`; `input_notes`
  names the radius as assumed.
- `test_bt_v3_fig1_and_eq29`: pins above; `fleck_regime_boundary_entry_gauge_m` values to 0.01 um.
- `test_ss_v2_ss_v3`: the three numbers above.
- `test_tm_lc7_is_reference_only`: verdict literal, `quantities` hold the measured values and
  `project_value is None`; the docstring says the test must be replaced when inputs are recorded.
- `test_chatter_harness_reproduces_the_demo`: the four numbers above (rel 1e-6).
- `test_run_all_is_json_safe_and_complete`: `json.dumps(run_all(), allow_nan=False)`; ids equal
  `CASE_IDS`; every case has a `read_status`; `main(['--json'])` prints valid JSON.
- `test_unknown_case_rejected`.
Module time: a few seconds.

### Documentation
- `physicroll/foil_bite.py` module docstring, lines 7-10: replace "no benchmark with fully known
  inputs was found" by a sentence stating the BT-V1 case and the recorded ratio 0.42, with a
  pointer to `physicroll/benchmarks.py`. Docstring only in this package (the result strings of
  that module change in package 2).
- `docs/band-diagnosis.md`: section 10.2, paragraph "How far to trust it": replace "No benchmark
  with fully known inputs was found." by the benchmark statement and the table from
  `table_rows()`; section 13: one row for `benchmarks.py` / `tests/test_benchmarks.py` that
  states the software-pin / recorded-discrepancy rule in two sentences; section 14: correct the
  same statement where it occurs (search "benchmark"); section 15: add Fleck et al. 1992 with
  its read tag if absent.
- Gap study: create section 11 (G7). Rows: BT-G17 `BENCHMARK_ENCODED` (cases listed, the
  not-encoded list, what stays open), G16 `BENCHMARK_ENCODED` (SS-V2, SS-V3 only).
- `docs/research/band-screening-2026-11/README.md` is not edited.

### Must not change
No solver, no scenario, no artifact: the five pairs stay byte-identical (G6.3 shows zero
differences). `physicroll/literature.py` and its tests are untouched.

### Do not
- Do not tune the mattress model (foundation coefficient, end zones) towards 118.
- Do not digitise figures or add reference values that are not in Appendix A of the study.
- Do not put benchmark results into `diagnose()` or the HTML report.
- Do not invent chatter mill parameters.

---

## Package 2 — Bite and film corrections (BT-G7, BT-G8, X19 to X24)

### Why
- BT-G7 / X23 (BT-S3 EX; factor [derived]): the film's inlet angle is taken as
  `sqrt(draft/(R*contact_radius_ratio))`. For a mattress bite `contact_radius_ratio` is
  `L^2/(R*draft)` (`foil_bite.py` line 646), not a radius, so the angle is `draft/L`, the mean
  slope of the whole bite. The literature uses the undeformed-roll inlet slope. The film is
  over-stated by `sqrt(ratio)`: 1.45, 1.8 and 3.3 times on the demo passes F1, F2, ALT2.
- BT-G8 / X21 (BT-S9 EX, BT-S3 EX, BT-S6 AB): a film ratio below 1 is labelled BOUNDARY. In the
  sources it is the condition for a good roll imprint inside the MIXED regime, and 0.01-0.5 is
  the common industrial window. The heat-streak rule counts "BOUNDARY" as support, so it fires
  on normal operation.
- X19, X20, X22, X24: four statements of the project that the literature contradicts or
  qualifies; text only, except that X20 renames a flag.

This package is a correction of existing outputs (house option (b)). Everything that moves is
listed under "What changes".

### Design A — inlet angle (BT-G7)

Derivation for the docstrings [D, re-derived in SPEC17]: for a bite `h(x) = h1 + x^2/R_c` the
inlet is at `x_i = -sqrt(R_c*draft)` and the slope of each roll surface there is
`|x_i|/R_c = sqrt(draft/R_c)`. Hitchcock bite: `R_c = R'` (the deformed arc), unchanged.
Mattress bite: the roll is not an arc; use the undeformed roll, `R_c = R`, i.e.
`theta0 = sqrt((h_entry - h_exit)/R)` [BT-S3 EX: "the undeformed-roll slope is used"]. The
alternative of the gap row, the local slope `h'(x_i)/2` of the bite solution, is NOT used: the
mattress entry zone holds a rigid strip of constant thickness, so its solution slope at the
plastic entry is not an inlet-wedge slope.

1. `physicroll/band_process.py`: add after `is_mattress` (line 287)
   ```python
   INLET_ANGLE_BASIS_MATTRESS = ('undeformed-roll inlet slope theta0 = sqrt(draft/R) [BT-S3 EX]; '
                                 'the mattress contact_radius_ratio L^2/(R*draft) is not a radius')
   INLET_ANGLE_BASIS_ARC = "inlet slope of the deformed circular arc theta0 = sqrt(draft/R') [D]"
   def film_radius_ratio(bite):
       """Radius ratio R_c/R of the film's inlet angle (1.0 for a mattress bite)."""
       return 1.0 if is_mattress(bite) else bite.contact_radius_ratio
   def inlet_angle_basis(bite):
       return INLET_ANGLE_BASIS_MATTRESS if is_mattress(bite) else INLET_ANGLE_BASIS_ARC
   ```
2. Use it at every film call site and nowhere else:
   - `friction_single` (lines 418-441): `friction_at(trib, src, radius, film_radius_ratio(bite),
     slip, u)`; keep the reported `contact_radius_ratio` (the bite's), add keys
     `film_inlet_radius_ratio` and `inlet_angle_basis`. In the `except` branch (no bite) the
     ratio is 1.0 and the basis `INLET_ANGLE_BASIS_MATTRESS` text with "(no bite)" appended.
   - `friction_fixed_point` (444-486): same inside the loop and in the output.
   - `friction_curve` (525-555): `radius = R * film_radius_ratio(bite)`; add `inlet_angle_basis`.
   - `speed_consistent_critical_speed` (629-706): `ratio = film_radius_ratio(op_bite)`; the
     output key `contact_radius_ratio_held` then holds the value used for the film; add
     `inlet_angle_basis`; reword its `note` ("contact radius" -> "inlet-angle radius").
   - `gauge_control_section` (838-841): both `friction_at` calls.
   - `band_diagnosis.diagnose` line 3265: `ratio = bp.film_radius_ratio(bite) if bite is not
     None else 1.0` (it feeds only `bs.inlet_angle_rad` in `_section_screens`, line 1037); add
     `scr['film']['inlet_angle_basis']` there. `_section_screens` then needs the bite's basis:
     pass it through or compute it in `_section_screens` from `bite`.
   - NOT `friction_power_per_width` (line 576): that is the Hitchcock slab grid, not the film.
3. `bite_tribology.py` docstring (lines 22-27) and `inlet_film_thickness` docstring: say that
   `contact_radius_m` is the radius of the inlet angle and what the integration layer passes.
   No change to `_film_core`.

Worked numbers (planner, battery-foil demo at full numerics, `s21/g7.py`; before -> after):

| quantity | before | after |
|---|---|---|
| `process.friction.operating.film_ratio` (F1) | 0.551493 | 0.380072 |
| `process.friction.operating.film_thickness_m` | 1.378732e-07 | 9.501810e-08 |
| `process.friction.operating.computed_friction_coefficient` | 0.055239 | 0.064073 |
| `process.friction.schedule` F2 / ALT1 / ALT2 film ratio | 0.647494 / 0.443982 / 0.979463 | 0.355720 / 0.295589 / 0.293417 |
| `screens.film_regime.film_ratio` | 0.564323 | 0.388915 |
| `screens.film.inlet_angle_rad` | 0.0083883 | 0.0121716 |
| `process.friction_speed_curve.mean_slope_per_m_s` | -0.0020407 | -0.0016462 |
| `chatter.speed_consistent.speed_consistent_critical_exit_speed_m_s` | 16.2863 | 16.7662 |
| same, without bite damping | null (`UNSTABLE_AT_LOWEST_ASSESSABLE_SPEED`) | 5.15681 (`CROSSING_FOUND`) |
| `gauge_control.speed_change_gauge_shift.exit_thickness_change_m` | -8.2797e-06 | -6.4782e-06 |

Ratios before / after: 1.451, 1.820, 1.502, 3.338 = `sqrt(contact_radius_ratio)` of each pass
(2.1055, 3.3133, 2.2561, 11.1431). S1 to S3 (Hitchcock) and the whole lengthwise demo keep their
film numbers. The demos use `use_computed_friction: false`, so no bite, force or score moves.

### Design B — regime labels and the heat-streak rule (BT-G8)

1. `bite_tribology.py` lines 95-96 and `_regime` (295-300):
   ```python
   REGIME_SUBSTANTIAL_CONTACT_BELOW = 1.0   # [V] below about 1: substantial contact, good imprint (BT-S9 EX)
   REGIME_HYDRODYNAMIC_ABOVE = 3.0          # [V] first asperity contact below about 3 (BT-S9 EX)
   COMMON_INDUSTRIAL_FILM_RATIO_WINDOW = (0.01, 0.5)   # [V] BT-S3 EX, BT-S9 EX
   ```
   `_regime`: `< 1` -> `'MIXED_SUBSTANTIAL_CONTACT'`; `1 <= Lambda <= 3` -> `'MIXED_FIRST_CONTACT'`;
   `> 3` -> `'HYDRODYNAMIC'`. The label `BOUNDARY` is no longer produced anywhere: no source
   read gives a film-ratio threshold for it. Remove `REGIME_BOUNDARY_BELOW`. In
   `friction_coefficient` and wherever a `regime` is returned with a film ratio add
   `in_common_industrial_window` (bool) and set `regime_boundaries` to
   `{'substantial_contact_below': 1.0, 'hydrodynamic_above': 3.0,
   'common_industrial_window': [0.01, 0.5]}`. Reasons text: "Film ratio 0.380: mixed
   lubrication with substantial asperity contact (the normal condition for a roll imprint)".
2. `band_signatures.film_ratio_regime` (808-840): same labels, same extra keys; `status`
   stays `f'{regime}_LUBRICATION'`; docstring and `threshold_basis` reworded.
3. Heat-streak rule, `band_width._h_heat_streak` lines 2919-2937. Criterion string unchanged
   (`'tribology regime / exit strip temperature at the operating point'`, it is a key of
   `band_plain.CRITERIA`). New logic:
   - no tribology regime and no temperature comparison: `NOT_OBSERVED` (as now);
   - exit temperature above the supplied limit: `SUPPORTS`, `weak`, basis `model` (as now);
   - otherwise `NEUTRAL`, basis `model`.
   `expected` becomes `'above the temperature limit (a film ratio below 1 is normal '
   'mixed-regime operation and no longer counts [BT-S3 EX, BT-S9 EX])'`; `observed` keeps the
   form `f'regime {regime}; exit temperature above limit: {hot}'`. Weight unchanged where it
   still supports; the gate `_gate_gauge_support` stays. The film-collapse test the gap row
   names (film against additive length or contact temperature) is NOT built: it needs BT-G3 /
   BT-G11. Say so in the docstring and in section 6.2 of the guide.
4. Herringbone rule, `band_diagnosis._h_herringbone` lines 1974-1982, and skid rule 2011-2019:
   thresholds and scoring unchanged; `expected` text `'boundary (Lambda < 1)'` becomes
   `'substantial asperity contact (Lambda < 1)'`. (Open decision 1.)
5. Search the package for the words `BOUNDARY` and `boundary regime` (code, tests, docs,
   `band_plain.py` word tables, `band_report.py`) and update each; `foil_regime` /
   `MATTRESS_REGIME_*` are unrelated.

Score changes (the only ones in this block of work):

| demo | hypothesis | score before -> after | rank before -> after |
|---|---|---|---|
| battery-foil | `heat_streak_or_film_variation` | 4 -> 3 | 4 -> 5 (`tension_troughs_or_creases`, 4, moves up) |
| lengthwise-bands | `heat_streak_or_film_variation` | 4 -> 3 | 4 -> 5 (`profile_flatness_mismatch`, 4, moves up) |

Leaders, every other score and every standing are unchanged in the four demos. The product
survey changes wherever it lists these scores; report the list. If the planted case of
`tests/test_band_lengthwise.py` (`test_heat_streak_leads`, line 254) no longer leads, stop and
report; do not re-weight.

### Design C — text corrections

- X19: `foil_bite.py` docstring lines 3-8, `BASIS`, `_LIMITATIONS[0]`; guide 10.2 first
  paragraph. Replace "in the spirit of Fleck & Johnson" by: a plain Winkler-foundation
  ("mattress") bite; Fleck & Johnson (1987) used a foundation only for the perturbation of a
  Hertzian pressure and rejected the plain mattress [BT-S2 FT]; Fleck et al. (1992) abandoned
  it because it under-predicts load by up to a factor 2 and torque by up to a factor 10
  [BT-S1 FT]. Add the fact, without changing code: Fleck & Johnson's modulus is
  `8E*/(3*pi*a0) = 0.849 E*/a0`; this module uses `(3*pi/8)E*/a = 1.178 E*/a`.
  `_LIMITATIONS[0]`: "... not benchmarked against any case with fully known inputs" becomes
  "... on the one published case with fully stated inputs it returns 0.42 of the half-space
  reference load (physicroll.benchmarks, BT-V1)".
- X20: rename the flag `FORWARD_SLIP_IMPLAUSIBLY_LARGE_NO_ELASTIC_STRIP_ZONES` to
  `FORWARD_SLIP_LARGE_CONSTANT_FRICTION_NO_SLIP_ZONE_MODEL` (threshold 0.15 unchanged). Sites:
  `foil_bite.py` 613 and 791; `band_plain.py` 2183 (key and sentence);
  `tests/test_foil_bite.py` 163; `tests/test_band_plain.py` 36;
  `tests/test_band_extended_domain.py` 289; guide lines 348 and 2201. Reword the texts that
  blame elastic strip zones: `band_diagnosis.SLIP_KINEMATICS_LIMITATION` (655), the comment at
  3165-3170, the `reason` in `_section_screens` (about line 1031), `foil_bite._LIMITATIONS`.
  New wording (use it everywhere): "Large forward slip is what a constant Coulomb friction
  model with a no-slip zone gives. One published model computes 5 % to 45 % on a 50 -> 25 um
  pass and describes such values as met in practice (model output) [BT-S3 EX]; mill trials
  show that constant friction over-estimates forward slip and that friction varying through
  the bite repairs it [BT-S5 AB]. Elastic strip zones are not the cause: they are negligible
  for reductions above 10 % [BT-S1 FT]."
- X22: `band_process.friction_section` note (507-514) and guide 8.1: the end values 0.09 and
  0.008 match the one abstract on aluminium [BT-S6 AB]; the law keeps friction near 0.09 over
  most of the common industrial window, so neither its level nor its slope is supported.
  Replace "stays near the boundary regime".
- X24: guide 10.2 "Where it rejects": the sentence about "the published high-friction foil
  case" becomes: a 50 -> 25 um pass at a NOMINAL friction of 0.10 is rejected for this reason;
  this is not the published case, where 0.1 acts on asperity contact areas only, weighted by
  the contact-area ratio and capped at shear yield [BT-S3 EX]. Same wording in the comment or
  docstring of the corresponding test in `tests/test_foil_bite.py` and in the section 13 row.
- X21, X23: by designs A and B; guide 8.1 states both corrections with before / after numbers
  read from the regenerated artifacts.

### Tests
- `tests/test_bite_tribology.py` 128-130, 156: new labels; add `test_regime_labels_and_window`
  (0.005, 0.01, 0.5, 0.99 -> `MIXED_SUBSTANTIAL_CONTACT`, window flag false / true / true /
  false; 1.0 and 3.0 -> `MIXED_FIRST_CONTACT`; 3.01 -> `HYDRODYNAMIC`); assert that no result of
  the module contains the string `BOUNDARY`.
- `tests/test_band_signatures.py` 327-335: new labels and status strings.
- `tests/test_band_v2_sections.py` (new class `InletAngleTests`, coarse numerics as that file's
  other classes): for a case whose operating bite is a mattress bite,
  `film_inlet_radius_ratio == 1.0`, `film_ratio * sqrt(contact_radius_ratio)` equals the film
  ratio computed with the old radius (call `bp.friction_at` with the bite's ratio) to 1e-9
  relative; for a Hitchcock operating bite `film_inlet_radius_ratio == contact_radius_ratio`
  and the film ratio equals the value of the same call before the change (pin from the
  lengthwise demo artifact: 0.180115).
- `tests/test_band_lengthwise.py` 256-257: new label; add `test_heat_streak_regime_item`: with
  tribology and no temperature limit the item is `NEUTRAL`; with a limit below the modelled
  exit temperature it is `SUPPORTS` / `weak`; the planted case still leads.
- `tests/test_band_foil.py` `test_extended_rules` (about 355-375): unchanged film-ratio items
  must still pass; add the regime item cases.
- Flag rename: the three tests above.
- `tests/test_band_plain.py`: the tuples at lines 44-49 (`DRY_RUN_18UM_TOP` and its
  neighbours) name heat-streak scores of fabricated results; change them only if a test fails
  because of this package, and say which.

### Documentation
Guide: 3.3 (flag name, slip wording), 6.2 (heat-streak rule), 6.4 (add "rule changed in SPEC17:
the film-ratio label no longer supports the heat-streak hypothesis", with the two score
changes), 8.1 (inlet angle, labels, window, placeholder wording), 10.2 (X19, X24), 13 (rows of
the touched tests), 14 (limitations: no film-collapse test; herringbone rule keeps `Lambda < 1`),
every quoted film ratio, friction-curve slope, speed-consistent speed and heat-streak score of
the two v2 demos (sections 3.9, 7.5, 8.4, 9: search for the old numbers). README where it quotes
them. Gap study section 11: BT-G7 `CORRECTED`, BT-G8 `CORRECTED` (labels and rule; film-collapse
test open), X19-X24 `TEXT_CORRECTED`.

### What changes, what must not
All five artifact pairs are regenerated. Allowed changed paths: `process.friction*`,
`process.friction_speed_curve*`, `chatter.speed_consistent*`,
`gauge_control.speed_change_gauge_shift*`, `screens.film*`, `screens.forward_slip.reason`,
`bite_derivations` (count), `flags` and every nested `flags` / `bite_flags` (renamed flag),
`limitations`, the `regime` / `status` / `reasons` strings of film results, the two score
changes with their `evidence`, `tallies`, `rank`, the `observed` / `expected` texts of the
film-regime evidence items, `model_prediction` film values, `strip_map` only if it follows the
rank, and the corresponding survey rows. Anything else that differs (any `bite`, `width`,
`thermal_check`, `levers`, `schedule_sweep` number) is a fault: stop and report.

### Do not
- Do not change the Hitchcock inlet angle, the film formula, the closure constants or
  `use_computed_friction` in any scenario.
- Do not introduce a boundary threshold or a film-collapse test.
- Do not change the herringbone or skid scoring, or the 0.3-3 film-ratio item.

---

## Package 3 — Rule checks, tables and the remaining text corrections (A5 basis, A10, B3, B4, X3, X7, X12)

### Why
- X3 / A5 (TM report section 8 item 3; PT-T18 FT from a garbled mirror): the model applies
  `spray_mean_htc_w_m2k` as a circumferential mean (`roll_thermal.py` docstring line 20). The
  earlier process-temperature note gives 3.0-4.0 kW/m2K "in the jet zone at 500 kPa" and
  2.5-4.3 "over 200-700 kPa". If that is a jet-zone value, `thermal_check` compares two bases.
  The study's action: "Re-read PT-T18 before anything is changed". So this package STATES the
  basis and shows the conversion; it changes no coefficient and no verdict word.
- A10 (TM-LA35 EX, PT-T13, PT-T14, PT-T9): fire limits cap oil and strip temperature. A rule
  check only.
- B3, B4 (TM-LB1 EX, TM-LB2 EX, TM-LB6 EX and others): tables with read status; no new physics.
- X7 (TM-LC18 VP), X12 (SS-S55 EX): two sentences the documents and the result should carry.

### Design A — spray-coefficient basis (X3, A5 small part)

Identity [D, re-derived in SPEC17]: the model's boundary condition uses the circumferential mean
`h_mean(z) = (1/2pi) * integral h(theta, z) dtheta`. A spray that wets an arc `phi` [rad] of the
roll circumference with coefficient `h_fp` and leaves the rest at `h_bg` gives
`h_mean = h_bg + (h_fp - h_bg)*phi/(2pi)`. The model writes `h_mean = background_htc +
spray_mean_htc*weight`, so for a healthy header (`weight = 1`):
`h_fp = background_htc + spray_mean_htc * 2pi/phi`.

1. New optional key `width_model.spray_wetted_arc_rad` (add to `band_width.WIDTH_DEFAULTS` with
   `None`; validate with `opt_num`, range `0 < phi <= 2*pi`, message
   "width_model.spray_wetted_arc_rad must be in (0, 2*pi]"). It is NOT placed inside
   `spray_header` (G5). It does not enter the roll thermal model.
2. `band_thermal.thermal_check`: on the finding whose `item` is
   `spray_heat_transfer_coefficient` add
   `value_basis: 'circumferential mean under a healthy header (model definition, '
   'roll_thermal.py)'`,
   `published_basis: 'jet zone, as the project's note of PT-T18 reads it (full text from a '
   'garbled mirror; not re-read)'`,
   `basis_comparable: 'NOT_ESTABLISHED'`, and, when the arc is supplied,
   `footprint_equivalent_w_m2k` (formula above) with `footprint_equivalent_verdict` from the
   same range and the same verdict words. `verdict` itself is unchanged. Add the flag
   `SPRAY_COEFFICIENT_BASIS_NOT_ESTABLISHED` to `thermal_check.flags` whenever that finding
   exists (it reaches the top-level flags through line 3409 of `band_diagnosis.py`; add its
   sentence to `band_plain.FLAGS`).
3. Report (`band_report._thermal_block`, line 2411): under the inputs table one line: "The
   model's spray coefficient is an average around the roll. The published 2.5-4.3 kW/m2K is
   read as a value inside the jet zone. The two are not on the same basis; with a wetted arc of
   X degrees the model value corresponds to Y kW/m2K inside the jet zone." (second sentence only
   with the arc).

Worked number: battery-foil demo, `spray_mean_htc_w_m2k = 3400`, `background_htc_w_m2k = 50`:
with `phi = pi/3` (60 degrees) `h_fp = 50 + 3400*6 = 20450 W/m2K`, verdict
`ABOVE_PUBLISHED_RANGE`; conversely 2.5-4.3 kW/m2K in a 60 degree jet zone is a mean of
0.42-0.72 kW/m2K. The demo scenario is NOT given an arc (no plant value; G2).

### Design B — fire limits (A10)

1. `band_process.TRIBOLOGY_OPTIONAL` (line 133) gains `oil_flash_point_k` and
   `oil_supply_temperature_cap_k`; `validate_tribology` normalises both with `opt_num`
   (range 250-700 K, message naming the key). Because of G5 add two questions to
   `band_plain.MILL_QUESTIONS` next to `temperature_limit` (line 775), same `_m(...)` form,
   unit `degc`, group `Rolling oil`: "Flash point of the rolling oil" (help: "From the oil data
   sheet.") and "Highest oil supply temperature your site allows" (help: "A site or insurer
   limit, if there is one."). `band_survey_mills.py`: add both keys with `None` to the two
   `MACHINES[...]['tribology']` dicts (the drift guard
   `tests/test_band_products.py::test_packaged_mills_equal_the_demo_machine_sections` compares
   them with the validated demo tribology, which now carries the two nulls).
2. `thermal_check` gains `fire_limits`: `{'status', 'not_supplied', 'rows', 'levers_that_raise_
   temperature', 'context', 'note'}`. Rows, each `{'item', 'value_k', 'limit_k', 'margin_k',
   'verdict' ('BELOW_LIMIT' | 'AT_OR_ABOVE_LIMIT'), 'limit_basis'}`:
   - `oil_inlet_temperature` (`tribology.inlet_temperature_k`) and
     `coolant_temperature_as_oil_supply` (`width_model.coolant_temperature_k`) against
     `oil_flash_point_k` and, separately, against `oil_supply_temperature_cap_k`;
   - `strip_exit_temperature` of every pass that has a pass-heating row (reuse the rows
     `thermal_check` already builds as `strip_exit_temperatures`) against `oil_flash_point_k`.
   Flags (evidence-neutral): `STRIP_EXIT_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT`,
   `OIL_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT`, `OIL_SUPPLY_TEMPERATURE_ABOVE_SITE_CAP`.
   Without either new input: `not_supplied` with the reason; `context` is still filled.
   `context`: the catalogue's flash-point and fire statements, read from `band_products`
   (topics `flash_point` and `fire`, lines 2360-2382) with their source ids; never a default
   limit. `levers_that_raise_temperature` (fixed list, each with its basis): higher pass
   reduction (more plastic work, pass-heating formula [D]); higher friction (more slip
   dissipation [D]); a closed or weak coolant zone and a lower coolant flow (roll thermal
   model [D]); a higher oil supply temperature; higher speed (more heat per unit time into the
   rolls; the model's strip temperature rise per pass does not depend on speed [D]; plant
   reports give 77 C at 550 m/min and 98-100 C at 600 m/min [PT-T1, PT-T2 EX]). `note`: "A
   modelled strip exit temperature is an indicator (EXIT_IS_NOT_COIL); no oil-mist or vapour
   model; limits are the user's."
3. Report: a "Fire limits" table inside the process-temperature block when rows exist; one
   line "not checked: no flash point given" otherwise.

Hand case for the test: flash point 353.15 K (80 C), inlet 318.15 K -> margin 35.0 K,
`BELOW_LIMIT`; a pass with modelled exit temperature above 353.15 K -> `AT_OR_ABOVE_LIMIT`
and the flag (build it with a small case of `tests/test_band_thermal_check.py`).

### Design C — tables (B3, B4), `physicroll/band_products.py` and the generated guide

Same discipline as the existing process-temperature reference (`_S`, `_r`, `_pt`, `_s`; read
how `process_temperature_reference()` is built and tested).
- New sources `TM-LB1`, `TM-LB2`, `TM-LB3`, `TM-LB6`, `TM-LB10`, `TM-LB12`, `TM-LB13`,
  `TM-LB15`, `TM-LB18` with the URL and read status exactly as section 9 of the study gives them.
- `alloy_group_reference()` -> JSON-safe dict with one entry per row of Appendix A.1, part B
  (ten rows; the `PT-T31; PT-T39` row and the pinhole row are included as printed): quantity,
  value(s) with unit, conditions, read status, source ids. Values as printed; where the study
  says "figure values partly unreadable" the row carries that sentence. Nothing is fitted and
  nothing is passed to a hardening law; `limitations` says so and repeats X2 (the stage-IV
  slope is wrong in sign for purified Al-Fe and high-purity grades beyond 80 % reduction
  [TM-LB2 EX]).
- `plane_strain_factor_hill48(r_0, r_90)` = `sqrt((1 + r_0)*(1 + r_90)/(1 + r_0 + r_90))`,
  both > 0 (ValueError otherwise). Derivation for the docstring [D, re-derived in SPEC17]:
  Hill's 1948 criterion in plane stress on the principal axes of anisotropy,
  `sx^2 - (2*r_0/(1+r_0))*sx*sy + (r_0*(1+r_90)/(r_90*(1+r_0)))*sy^2 = s_0^2` (`s_0` =
  uniaxial yield in the rolling direction); plane strain in the width direction means
  `d(eps_y) ~ df/d(sy) = 0`, i.e. `sy = sx*r_90/(1+r_90)`; substituting gives
  `sx/s_0 = sqrt((1+r_0)(1+r_90)/(1+r_0+r_90))`. Rolling adds a hydrostatic stress, which a
  pressure-independent criterion ignores. `r_0 = r_90 = R` gives the report's
  `(1+R)/sqrt(1+2R)` [computed in the report]. Check values: (1, 1) -> 1.154701;
  (0.2, 0.2) -> 1.014185; (0.2, 1.1) -> 1.046734; (1.075, 1.075) -> 1.169130.
- `anisotropy_reference()`: the measured r-values 0.2 / 1.5 / 1.1 and the 10 % higher
  transverse stress on 16 um 1235-H18 [TM-LB1 EX], with the note that the report prints them
  for "three directions" and that 0 / 45 / 90 degrees in that order is an assumption; the four
  factors above labelled (isotropic, the engine's value; normal anisotropy R = 0.2, the
  report's bound, -12 %; Hill48 with r_0 and r_90, -9.4 %; mean normal anisotropy
  (r_0 + 2 r_45 + r_90)/4 = 1.075, +1.2 %); the statement "Hill-type criteria are known to be
  poor for aluminium" tagged from memory, as in the report. The engine keeps `2/sqrt(3)`.
- Generated document `docs/thin-gauge-products.md`: two new sections from these functions
  ("Alloy groups: hardening and softening data found", "Anisotropy and the plane-strain
  factor"); regenerate with the existing generator; the existing test "document equals the
  committed file" must pass.
- Engine: `band_diagnosis.LIMITATIONS` (line 164) gains one sentence: the plane-strain factor
  is the isotropic `2/sqrt(3)`; published r-values of one 16 um 1235-H18 foil would move it by
  -12 % to +1 % under Hill's 1948 criterion (table in thin-gauge-products.md). This changes
  `limitations` in every artifact (allowed, listed below).

### Design D — text (X7, X12)
- X7: guide section 9, first paragraph, a boxed note: gaugemeter control acts through roll
  force and an open gap; at foil gauge the gauge is controlled by speed and tension
  [TM-LC18 VP]; do not read this section for passes below the closed-gap onset. The result
  already carries `foil_regime_note`; no code.
- X12: `band_width._troughs` (line 1485): when the span's thickness is below
  `FOIL_GAUGE_M`, add to that span's dict the key `wide_foil_note`: "Screening value from an
  isolated-span formula. For aluminium and copper foil below 25 um and wider than 0.6-1 m,
  wrinkles needed about 15 times the predicted roller misalignment [SS-S55 EX]: at foil gauge
  this threshold is conservative." No number changes; the report prints the note under the
  trough table (`band_report._other_width_results`, line 1187); guide 3.5 and 7.2 get the same
  sentence.

### Tests
`tests/test_band_thermal_check.py`: basis keys and flag present on the spray finding, verdict
unchanged; arc -> `footprint_equivalent_w_m2k == 20450.0` for the demo values, range check on
the arc; fire rows, verdicts, flags, `not_supplied` without inputs, context sources present.
`tests/test_band_products.py`: integrity of the new sources and rows (read status never
upgraded: compare with a literal table of the tags in this brief's source list), the four
factor values to 1e-6, ValueError for `r <= 0`, document equality.
`tests/test_band_foil.py` or `test_band_lengthwise.py`: `wide_foil_note` present below 100 um
and absent at sheet gauge; trough numbers unchanged.
`tests/test_band_plain.py`: passes with the two new questions (round trips included).
Absent-input check: `diagnose(case)` of the template with and without the three new keys set to
null is identical (`result_json`).

### Documentation
Guide 3.12 (process temperatures: basis statement, the conversion, the fire-limit check), 5.3
(the three new keys), 8.3 (pointer to the alloy-group table and X2), 9 (X7), 3.5 and 7.2 (X12),
12, 13, 14. Template: the three keys with `null` and note lines. Gap study section 11: A5
`RULE_CHECK` (basis stated; re-read of PT-T18 and the calibration routine open), A10
`RULE_CHECK`, B3 `TABLE_ADDED`, B4 `TABLE_ADDED` (factor not applied in any bite), X3, X7, X12
`TEXT_CORRECTED`.

### What changes, what must not
Artifacts: additive, plus these allowed changed values: `flags` and `thermal_check.flags` gain
`SPRAY_COEFFICIENT_BASIS_NOT_ESTABLISHED`; `limitations` gains one sentence. Added keys under
`inputs.tribology`, `inputs.width_model`, `thermal_check`, `width.troughs.*`. No score, no
number of any existing key.

### Do not
- Do not change `spray_mean_htc_w_m2k` of any scenario or the published range, and do not
  state which basis PT-T18 is on.
- Do not default the flash point from the catalogue.
- Do not wire alloy-group data or the anisotropy factor into any bite or hardening law.

---

## Package 4 — Shapemeter operator (C7 zone part, G5 sensor part, X9)

### Why
The tool says "a latent band is a stress stripe a shapemeter can see" (guide 7.2). The shape
report qualifies this (X9): shapemeter rolls have zones of 26 or 52 mm (rotors 25-100 mm), with
spreading to neighbours; a band narrower than a zone is diluted, and a tight edge beside a loose
pocket in one zone is missed [SS-S29 VP, SS-S30 VP, SS-S31 EX, SS-S32 EX]. The report's own
arithmetic: a 20 mm band of 25 I-units reads about 10 I-units as the mean of a 52 mm zone [D].
Today the model has no shapemeter at all. The owner asked what a flatness system with a given
zone width would have shown, and how zones relate to the spray nozzles. This package builds the
measurement operator only. The flatness CONTROLLER of G5 (actuator fitting, valve logic) is
Phase 2 and is not built; every output says so.

### Design

New module `physicroll/band_sensors.py` (integration layer in the style of `band_thermal.py`:
it reads the case and finished result sections, never changes them).

**Case schema.** New optional top-level v2 section `measurement` (add `'measurement'` to
`band_diagnosis.V2_SECTIONS`, line 350; `_validate_v2_sections`, line 579, calls
`band_sensors.validate_measurement`; a v1 case may not carry it, as for the other v2 sections).

```json
"measurement": {
  "shapemeter": {
    "zone_width_m": 0.052, "zone_count": 24,
    "edge_zone_width_m": null, "edge_zone_count_per_side": 0,
    "centre_m": null, "neighbour_spreading_fraction": 0.0,
    "resolution_i_units": null, "provenance": "..."
  },
  "thickness_gauge": null
}
```

| key | unit | range | default | validation message |
|---|---|---|---|---|
| `shapemeter.zone_width_m` | m | (0, 0.5] | required | "measurement.shapemeter.zone_width_m must be in (0, 0.5] m" |
| `shapemeter.zone_count` | - | int 1..400 | required | "... zone_count must be an int in [1, 400]" |
| `shapemeter.edge_zone_width_m` | m | (0, zone_width_m] or null | null | "... edge_zone_width_m must be in (0, zone_width_m] or null" |
| `shapemeter.edge_zone_count_per_side` | - | int >= 0, `2*n <= zone_count`; must be 0 when the width is null and >= 1 when it is given | 0 | "... edge_zone_count_per_side ..." |
| `shapemeter.centre_m` | m, barrel coordinate | [0, 10] or null | null = the strip centre the width section uses (`width_model.strip_centre_m`, else half the width-model barrel); without a width model the strip is taken from 0 to `pass.width_m` and the block is `NOT_ASSESSABLE` anyway | "... centre_m must be in [0, 10] m or null" |
| `shapemeter.neighbour_spreading_fraction` | - | [0, 0.25] | 0.0 | "... neighbour_spreading_fraction must be in [0, 0.25]" |
| `shapemeter.resolution_i_units` | I-units | (0, 100] or null | null | "... resolution_i_units must be in (0, 100] or null" |
| `shapemeter.provenance` | text | nonempty | required | "... provenance must be a nonempty string" |

`measurement` may hold `shapemeter`, `thickness_gauge` (package 5), both or neither; strict keys.
`thickness_gauge` is accepted here only as `null` until package 5.

**Zone geometry.** Zone widths: `edge_zone_count_per_side` zones of `edge_zone_width_m` at each
end, the rest `zone_width_m`. Edges: `e_0 = centre - sum(widths)/2`, `e_{j+1} = e_j + w_j`.

**Zone mean** [D, re-derived in SPEC17: a stress-measuring roll senses the radial force per
zone, i.e. the mean tension over the zone; the flatness shown is its deviation from the mean
over the zones]. A model profile `I(z_i)` is given on uniform strip samples (spacing `dz`).
Treat sample `i` as constant on `[z_i - dz/2, z_i + dz/2]`, clipped to the strip
`[a_0, a_1]`. For zone `j`: overlap `o_ij` = length of (cell `i` ∩ zone `j` ∩ strip);
`m_j = sum_i(I_i*o_ij)/sum_i(o_ij)`; coverage `c_j = |zone j ∩ strip|/w_j`; a zone with
`c_j = 0` reads `null`. Mean over the roll: `m_bar = sum_j(c_j*w_j*m_j)/sum_j(c_j*w_j)`.
Unspread reading `u_j = m_j - m_bar`.

**Neighbour spreading** [D, an interpretation of the vendor statement "max. 2 x 12.5 % force
spreading to adjacent measurement zones", SS-S29 VP; the vendor's own algorithm was not read]:
with fraction `s` per side, `r_j = (1 - 2s)*u_j + s*(u_{j-1} + u_{j+1})`; a missing or
uncovered neighbour is replaced by `u_j` itself. `s = 0` gives `r_j = u_j`.

**Per model band** (the band dicts of `levels.with_feedback.bands`): the zone that holds
`peak_position_m` (zone `j` holds `x` when `e_j - 1e-9 <= x < e_{j+1} - 1e-9`; the same rule
assigns nozzles to zones); `zone_reading_i_units = r_j`; `reading_to_peak_ratio =
r_j/peak_i_units`; `half_peak_width_m` = number of contiguous samples around the peak sample
with the peak's sign and `|I| >= |peak|/2`, times `dz`; `reads_above_threshold =
abs(r_j) >= threshold`, where `threshold = resolution_i_units` if supplied, else the profile's
`reporting_threshold_i_units` (2.0, the tool's own band threshold). `threshold_basis` says
which. Vendor accuracy figures (0.5 I-units typical, SS-S29 VP) are quoted in the guide, never
used as a default.

**Dilution table** [D, re-derived: zone mean of a reference band of peak 1]. For band widths
`b` in (0.010, 0.020, 0.040, 0.080, 0.160) m and the body zone width `w`:
- top-hat of width `b`: centred in a zone `min(b, w)/w`; centred on a zone boundary
  `min(b/2, w)/w`;
- Gaussian with half-peak width `b`, `k = sqrt(pi/(4*ln 2))`: centred
  `(b/w)*k*erf(sqrt(ln 2)*w/b)`; on a boundary `(b/(2w))*k*erf(2*sqrt(ln 2)*w/b)`.

**Nozzle map.** From `band_width.spray_layout(case)` (line 893; only with a `width_model`):
per zone the nozzle indices inside it and their effective levels; `nozzles_per_zone_min/max`;
zones without a nozzle; `cooling_zone_pitch_m` and its ratio to `zone_width_m`. Statement in
the result, tagged: "cooling zones are built at the shapemeter pitch and each spray is driven by
its zone [SS-S31 EX, SS-S33 EX, SS-S34 EX]; the tool has one header row and no controller".

**Profiles read** — `band_sensors.shapemeter_profiles(width)` returns a list of
`{'name', 'label', 'z_m', 'i_units', 'bands', 'reporting_threshold_i_units'}`; later packages
append to this function:
1. `steady` — `width.shape.steady` (`z_m`, `i_units_with_feedback`,
   `levels.with_feedback.bands`), when that dict has these keys;
2. `event_<k>_peak` — each `width.thermal_events.events[k].peak_shape` with the same keys;
3. `nozzle_pattern_ripple` — `width.shape.nozzle_pattern_ripple.i_units_with_feedback` on the
   steady `z_m` (only when the lengths agree), no bands.
No profile available: the shapemeter block is `NOT_ASSESSABLE` with the reason; the dilution
table and the nozzle map are still given.

**Result.** `result['measurement']` in every result (v1 included, as `gauge_control` is today):
`not_supplied` when the case has no `measurement`. Otherwise
`{'status': STATUS, 'not_supplied': False, 'shapemeter': {...} | not_supplied,
'thickness_gauge': not_supplied, 'flags': [...], 'limitations': [...]}` with

```
shapemeter: status, provenance, zone_layout {zone_count, covered_zone_count, first_edge_m,
  last_edge_m, strip_start_m, strip_end_m, uncovered_strip_width_m}, zones [{index, start_m,
  end_m, width_m, coverage_fraction, nozzle_indices, nozzle_levels}], threshold_i_units,
  threshold_basis, neighbour_spreading_fraction, profiles [{name, label, readings_i_units,
  unspread_readings_i_units, roll_mean_i_units, max_abs_reading_i_units, max_abs_zone_index,
  profile_max_abs_i_units, bands [...]}], dilution_table, nozzle_map, basis {...}, flags,
  limitations
```

Flags (also copied to the top-level flags; add each to `band_plain.FLAGS`):
`SHAPEMETER_OPERATOR_APPLIED`; `MODEL_BAND_BELOW_SHAPEMETER_THRESHOLD` (a band of the steady or
an event profile with `reads_above_threshold` false); `SHAPEMETER_DOES_NOT_COVER_STRIP`
(`uncovered_strip_width_m > dz`); `SHAPEMETER_NEIGHBOUR_SPREADING_APPLIED`.
Limitations (fixed sentences): zone means of the modelled far-field stress; no roll wrap, no
measurement noise, no calibration, no temperature compensation (package 6), no dynamics or
filter; the stress still evolves between bite and shapemeter [SS-S22 EX]; a buckled (manifest)
band no longer carries the stress the linear profile assigns to it; NO flatness controller: the
tool does not predict what the control would have done with these readings (G5, Phase 2).

**Wiring.** `band_diagnosis.diagnose`: after the `attach_per_pass` block (line 3376) and before
`_hypotheses`: `result['measurement'] = band_sensors.measurement_section(eff, result)` inside
`try / except (ValueError, KeyError, TypeError, ArithmeticError)` -> `bp.failed('measurement',
exc)` and flag `MEASUREMENT_SECTION_FAILED`; extend `flags`. The hypotheses do not read it.

**Report** (`band_report.py`): new `_measurement_section(r)`, placed directly after
`_width_section(r)` in the `new` list of `render_band_report` (line 2880). Heading "What a
shapemeter would show". Content: one sentence of set-up (zones, width, source); an SVG bar
chart of the steady profile (one bar per zone = reading, the fine model profile as a line, the
threshold as two dashed lines, nozzle positions as ticks; reuse the chart helpers of
`_width_chart`, line 803); a table per profile: band position, model peak, half-peak width,
zone, zone reading, reading / peak, "shows" or "below the threshold"; the dilution table; one
sentence on the nozzle map; the limitation "no flatness controller" in a `warn` paragraph.
Not supplied: one paragraph, "No shapemeter was described. Add measurement.shapemeter (zone
width and count) to see what each zone would read; a band narrower than a zone is diluted (a
20 mm band reads 38 % of its peak as the mean of a 52 mm zone)." — the 38 % computed by the
top-hat formula, not typed. The v1 report is unchanged.

**Demo.** `scenarios/band_diagnosis_battery_foil.json` gains
`"measurement": {"shapemeter": {"zone_width_m": 0.052, "zone_count": 24, "edge_zone_width_m":
null, "edge_zone_count_per_side": 0, "centre_m": null, "neighbour_spreading_fraction": 0.0,
"resolution_i_units": null, "provenance": "synthetic: 24 zones of 52 mm centred on the mill
centre line, one spray nozzle per zone"}, "thickness_gauge": null}` and a `notes` line. The
other scenarios and the template get `"measurement": null` (template: with a notes line that
names the keys).

### Worked numbers (planner; battery-foil demo at full numerics, `s21/nums3.py`, `shp.py`)

- Zones: edges 0.126 ... 1.374 m; strip 0.15 ... 1.35 m; zones 0 and 23 have coverage 0.5385;
  every zone holds exactly one nozzle (zone `j` holds nozzle `j + 2`), at its centre.
- Steady profile: loose band, peak 25.0888 I-units at 0.6225 m, half-peak width 0.160 m ->
  zone 9 [0.594, 0.646] reads 24.4912 (ratio 0.9762); zones 7 to 11 read 6.5973, 20.4506,
  24.4912, 20.4517, 6.5979. Tight bands: -5.1825 -> zone 0 reads -5.1776; -5.2244 -> zone 23
  reads -5.2142. All above the 2 I-unit threshold: a thermal stripe of a partly blocked nozzle
  is wide enough for a 52 mm shapemeter.
- With `neighbour_spreading_fraction = 0.125`: zone 9 reads 23.4812 (ratio 0.9359).
- Event peak shape (valve closed 20 s, nozzles 18-19): true peak 21.0067, zone 16
  [0.958, 1.010] reads 19.3326.
- Nozzle-pattern ripple: profile peak 3.1433 I-units, largest zone reading 0.5296: a pattern at
  the nozzle pitch is averaged out by zones of the same pitch.
- Dilution, 52 mm zone: 20 mm top-hat 0.3846 centred, 0.1923 on a boundary (25 I-units ->
  9.615, the report's "about 10"); Gaussian 20 mm 0.4085 / 0.2047; 40 mm 0.7158 / 0.4085;
  80 mm 0.9104 / 0.7158. 26 mm zone, Gaussian 20 mm: 0.7158 / 0.4085.
- Function-level check with 23 zones (not the demo): zone 9 [0.620, 0.672] reads 23.5348,
  roll mean 0.01739 (2 mm of strip uncovered at each side).

### Tests (`tests/test_band_sensors.py`, function level; one coarse `diagnose` run)
- `test_zone_edges_and_coverage`: body and edge zones, centre default, coverage fractions.
- `test_zone_mean_of_a_tophat_is_the_area_ratio`: a 20 mm top-hat of 25 on a 1 mm grid, zone
  52 mm, strip much wider than the roll band: unspread mean of its zone 9.6154 before the roll
  mean is removed (assert `m_j`), and `u_j = m_j - m_bar`.
- `test_uniform_profile_reads_zero`, `test_mean_free_profile_keeps_roll_mean_zero_when_fully_
  covered`.
- `test_spreading_conserves_the_sum_and_s0_is_identity`.
- `test_dilution_table_closed_forms`: the eight numbers above to 1e-4; a numeric zone mean of
  a sampled Gaussian agrees with the closed form to 1e-3.
- `test_band_metrics_on_the_committed_demo_profile`: load `battery-foil-demo.result.json`,
  apply the operator to `width.shape.steady` with 24 zones of 0.052: the readings above to
  1e-3; half-peak width 0.160; the ripple reading; 23 zones gives 23.5348.
- `test_nozzle_map_one_nozzle_per_zone` (demo layout) and the boundary rule.
- `test_validation`: each message of the table; unknown key; v1 case with `measurement`
  rejected; `thickness_gauge` non-null rejected until package 5 (remove that case there).
- `test_absent_measurement_changes_nothing_else`: for a small v2 case, `diagnose` with
  `measurement` null and with a shapemeter: every result key except `measurement`, `inputs`
  and `flags` is equal; `flags` differ only by the new flags; hypotheses identical.
- `test_no_width_model_is_not_assessable`; `test_report_section_renders_and_escapes`
  (provenance with `<`), no `nan` / `inf` in the HTML.

### Documentation
Guide: new subsection 7.6 "What a shapemeter would show" (the operator, formulas, the vendor
facts with their VP / EX tags, the worked numbers from the regenerated artifact, the statement
that X9 qualifies section 7.2's sentence — edit that sentence in 7.2 to "... a stress stripe a
shapemeter can see when the band is at least about one zone wide (section 7.6)"); 5.3 (the
`measurement` keys, which plant document gives them); 3.9 (demo numbers); 12 (report section);
13 (test row); 14 (no controller; no shapemeter dynamics). README band section: two sentences.
Gap study section 11: C7 `SCREENING_VERSION` (zone part), G5 `SCREENING_VERSION` (measurement
operator only; controller, edge rules of a specific vendor and temperature compensation open),
X9 `TEXT_CORRECTED`.

### What changes, what must not
Artifacts: additive. All five pairs gain `inputs.measurement` and `measurement`; battery-foil
also gains the flag `SHAPEMETER_OPERATOR_APPLIED` in `flags` (allowed changed value; none of
the conditional flags is set in the demo) and its HTML gains the section; the
other v2 HTML gains the "not described" paragraph; v1 HTML byte-identical. No other value.

### Do not
- No controller, no actuator fitting, no valve logic, no generated events.
- No evidence rule and no gating of existing evidence by "the shapemeter could not see it".
- No vendor-specific edge or compensation algorithm; no default resolution.
- Do not apply the operator to the compliance-only or rigid levels.

---

## Package 5 — Thickness gauge transfer (C7 gauge part)

### Why
"A gauge with a few-millisecond response at 10 m/s averages over centimetres, so 10-40 mm marks
are invisible to it" (TM report, gap C7; foil gauge response under 10 ms, TM-LC24 VP). Several
rules use `gauge_variation_detected`. The tool should say when "not detected" cannot mean "not
there".

### Design

`measurement.thickness_gauge` (same module and validation frame as package 4):

| key | unit | range | default |
|---|---|---|---|
| `spot_length_m` (along the strip) | m | (0, 1] | required |
| `time_constant_s` (first-order response) | s | [0, 10] | required |
| `sample_interval_s` | s | (0, 10] or null | null |
| `position_m` (across the width, barrel coordinate) | m | on the barrel or null | null = strip centre |
| `spot_width_m` (across the width) | m | (0, 1] or null | null |
| `provenance` | text | nonempty | required |

Messages in the form "measurement.thickness_gauge.<key> must be ...".

Formulas [D, re-derived in SPEC17; the gap row names them without a source]. A mark is a
thickness variation `A*cos(2*pi*x/p)` of pitch `p` [m] passing at exit speed `u` [m/s],
frequency `f = u/p`.
- Spot averaging over a length `L`: `(1/L)*integral_{-L/2}^{L/2} A*cos(2*pi*(x+s)/p) ds =
  A*cos(2*pi*x/p)*sin(pi*L/p)/(pi*L/p)`, gain `G_spot = |sin(pi*L/p)/(pi*L/p)|`.
- First-order response with time constant `tau`: `G_tau = 1/sqrt(1 + (2*pi*f*tau)^2)`;
  equivalent averaging length `u*tau`.
- Sampling at interval `dt`: aliased when `f > 1/(2*dt)`.
- `G = G_spot*G_tau`. `GAUGE_RESOLVABLE_GAIN = 0.5` (analyst choice [D]: the gauge keeps less
  than half of the amplitude).

`thickness_gauge` result: `rows` for (a) every `observation.pitch_observations[i]` at its own
speed, (b) `observation.measured_vibration_hz` at the operating speed, (c) the modelled chatter
onset frequency `chatter.with_bite_damping.onset_frequency_hz` at the operating speed when it is
a number. Row: `{'source', 'pitch_m', 'exit_speed_m_s', 'frequency_hz', 'spot_gain',
'time_constant_gain', 'combined_gain', 'aliased' (bool | null), 'resolvable' (combined >= 0.5
and not aliased)}`. Also `averaging_length_time_constant_m = u_op*tau`, `spot_length_m`,
`shortest_resolvable_pitch_m` at the operating speed (bisection on `G(p) = 0.5` between
`1e-4` and `10` m, the largest root; null when none), and, when
`observation.gauge_variation_amplitude_m` is given, per pitch row
`amplitude_before_gauge_m = amplitude/combined_gain` with the note "lower bound of the true
amplitude if the mark has this pitch".
Across the width: when model bands exist (the `steady` profile of package 4's
`shapemeter_profiles`), `bands_under_gauge` = bands whose `[start_m, end_m]` overlaps
`[position - spot_width/2, position + spot_width/2]` (a point when the width is null).
Flags (top level too; add to `band_plain.FLAGS`): `GAUGE_TRANSFER_APPLIED`;
`GAUGE_KEEPS_LESS_THAN_HALF_OF_OBSERVED_MARK` (any pitch-observation row not resolvable);
`GAUGE_NOT_DETECTED_BUT_MARK_NOT_RESOLVABLE` (`gauge_variation_detected` is false and no
pitch-observation row is resolvable): its text says that "not detected" then carries no
information, names the hypotheses whose evidence uses that observation (read them from the
result: evidence items whose criterion starts with `'gauge variation'`), and states that the
tally is NOT changed; `LENGTHWISE_MODEL_BAND_NOT_UNDER_GAUGE` (model bands exist, none under
the gauge).
Report: in `_measurement_section`, a second table "What the thickness gauge keeps" and the
flag sentences.

The gap row's third item, accelerometer position and detection lead time, has no formula in
the reports: not built; say so in the limitations of the section.

### Worked numbers (`s21/nums.py`)
Spot 0.010 m, time constant 0.005 s, sample interval 0.001 s:
- pitch 0.08408 m at 16.0 m/s: `f = 190.2950 Hz`, spot 0.976894, time constant 0.164980,
  combined 0.161168, not aliased, not resolvable;
- pitch 0.07647 m at 14.5 m/s: 189.6168 Hz, 0.972107, 0.165554, 0.160936;
- pitch 0.024921 m at 7.8333 m/s: 314.3253 Hz, 0.755406, 0.100752, 0.076109;
- `u*tau` at 10 m/s: 0.05 m.

### Tests (extend `tests/test_band_sensors.py`)
Closed-form gains (the rows above to 1e-6); limits (`L -> 0` and `tau = 0` give 1; `L = p`
gives 0); aliasing; shortest resolvable pitch; amplitude correction; the two observation flags
on a v2 copy of the thin-gauge chatter demo (build it with `band_plain.as_v2` or the v2 helper
of `tests/test_band_v2_sections.py`) with `gauge_variation_detected` set to false: flag set,
every score equal to the run without the gauge; bands under the gauge on the battery-foil
profile (gauge at the strip centre 0.75 m: the loose band [0.49, 0.75] overlaps; at 0.77 m,
width 0.02: none, the profile is below 2 I-units between 0.75 and 0.795 m); validation messages; report table renders.

### Documentation
Guide 7.6 gets a second part (or 11.6 for the transverse side: put the gauge transfer where
section 11.2 discusses pitch, with a pointer from 7.6); 5.3; 12; 13; 14. Gap study section 11:
C7 row extended (gauge part `SCREENING_VERSION`; accelerometer lead time not built).

### What changes, what must not
Artifacts: no scenario gets a gauge, so the only change is the `thickness_gauge` not-supplied
entry inside `measurement` of the battery-foil result (additive). Scores untouched.

### Do not
- Do not change any evidence verdict on the strength of the gauge transfer (open decision 2).
- No gauge noise, calibration or scanning-frame model.

---

## Package 6 — Strip temperature across the width as a flatness term (A1, G6; supplied profile)

### Why
A strip fibre that is hotter than its neighbours at the shapemeter is longer by
`alpha*dT`: about 2.4 I-units per kelvin for aluminium (computed in the reports; the expansion
coefficient 23.6e-6 /K is a textbook constant there, tagged from memory in the shape report),
above the tool's 2 I-unit reporting threshold. It reads loose in the mill and the difference
disappears when the coil cools [TM-LA13 EX; TM-LA30 EX for steel: 1 C = 1.2 I-units; SS-S40 VP].
Not modelled at all today. The per-width heat balance that would COMPUTE the temperature needs
the heat split (A3) and is Phase 1; this package takes a measured or assumed temperature
profile as input and says so in every output.

### Design

**Case schema.** `band_width.WIDTH_DEFAULTS` gains `'strip_temperature': None`;
`validate_width_model` validates

```json
"strip_temperature": {
  "positions_m": [0.15, 0.20, ...],   "temperature_k": [353.15, ...],
  "expansion_coefficient_per_k": null, "provenance": "..."
}
```

| key | unit | rule | message |
|---|---|---|---|
| `positions_m` | m, barrel coordinate | list of >= 3 numbers, strictly increasing, inside [0, barrel] | "width_model.strip_temperature.positions_m must be >= 3 strictly increasing positions on the barrel" |
| `temperature_k` | K | same length, each in [250, 700] | "... temperature_k needs one value in [250, 700] K per position" |
| `expansion_coefficient_per_k` | 1/K | (1e-6, 1e-4) or null | "... expansion_coefficient_per_k must be in (1e-6, 1e-4) or null" |
| `provenance` | text | nonempty | "... provenance must be a nonempty string" |

`measurement.shapemeter` gains the optional key `temperature_compensated` (true, false or null;
default null).

**Physics** (new function in `strip_shape.py`, after `flatness_from_elongation`):

```python
ALUMINIUM_EXPANSION_PER_K = 23.6e-6   # [M] textbook value used by the gap reports, not verified there
def thermal_flatness_term(z_m, temperature_k, *, expansion_coefficient_per_k=ALUMINIUM_EXPANSION_PER_K) -> dict
```
`eps_T(z) = alpha*(T(z) - mean(T))` (arithmetic mean over the samples, as
`flatness_from_elongation` does for its own mean), `I_T(z) = 1e5*eps_T(z)` [TM report gap A1:
"eps_T(z) = alpha*(T_x(z) - mean), i.e. 1e5*eps_T I-units"]. Returns `i_units`, `elongation`,
`mean_temperature_k`, `temperature_deviation_k`, `i_units_per_kelvin = 1e5*alpha`,
`formula_basis`, `flags` (`STRIP_EXPANSION_COEFFICIENT_FROM_MEMORY_DEFAULT` when the default is
used), `limitations`.

Which profile means what [D, re-derived in SPEC17]: with `eps_m(z)` the mechanical elongation
of the model (what the roll gap printed, referred to a uniform temperature), the stress the
shapemeter senses in the hot strip follows `eps_m + eps_T`; after the coil has cooled to a
uniform temperature only `eps_m` is left. Without a flatness controller the three profiles are:

| profile | elongation | meaning |
|---|---|---|
| `mechanical` | `eps_m` | the model's flatness as it is today (`width.shape.steady`, with feedback) |
| `as_measured_hot` | `eps_m + eps_T` | what a shapemeter without temperature compensation senses; also the state of the strip in the mill and of a sample released while hot |
| `after_cooling` | `eps_m` | equal to `mechanical`; stated so that the reader sees it |
| `after_cooling_if_hot_reading_held_flat` | `-eps_T` | BOUNDING CASE: if a flatness control had removed everything the hot shapemeter showed, the cold strip would carry the negative of the thermal term (a hot fibre becomes tight). Needs the controller of G5 to be more than a bound |

**Section** `width.strip_temperature` (new function `band_width.strip_temperature_section(case,
w, shape_steady, z_strip, strip_start, strip_end)`, called in `width_section` after the shape
block, line about 2105, inside `try / except ValueError` -> `failed('strip_temperature', exc)`
appended to `out['failures']`):
1. Grid: the strip samples of `shape['steady']['z_m']` when the steady shape was evaluated, else
   the strip samples of the section's `z` (line 2093).
2. Temperature on the grid: linear interpolation of the scan; outside the scan range the end
   value is held and `extrapolated_width_m` (strip width not covered by the scan) is reported;
   flag `STRIP_TEMPERATURE_SCAN_DOES_NOT_COVER_STRIP` when it exceeds one grid cell.
3. `thermal = ss.thermal_flatness_term(...)`.
4. For each profile, `ss.flatness_from_elongation(z, eps, youngs_modulus_pa=material E,
   poisson_ratio=STRIP_POISSON_RATIO, thickness_m=pass exit thickness, mean_tension_pa=pass exit
   tension, yield_stress_pa=material yield)` with `eps = I*1e-5`; keep `i_units`, `status`,
   `released_status`, `max_i_units`, `min_i_units`, `bands`. `mechanical` uses
   `shape.steady.i_units_with_feedback`; when the steady shape is not available,
   `mechanical.available = False`, `as_measured_hot` is the thermal term alone and the flag
   `STRIP_TEMPERATURE_TERM_WITHOUT_MECHANICAL_PROFILE` is set. No bite is needed.
5. `state_changes`: for every band of `mechanical` and of `as_measured_hot`, the band of the
   other profile at its peak position (`band_width._band_at`) and whether `state` or
   `state_after_tension_release` differ; flag `STRIP_TEMPERATURE_CHANGES_A_BAND_STATE`.
6. Keys: `status`, `not_supplied`, `provenance`, `expansion_coefficient_per_k`,
   `expansion_coefficient_basis`, `i_units_per_kelvin`, `z_m`, `temperature_k`,
   `mean_temperature_k`, `max_temperature_deviation_k`, `scan_coverage`, `thermal_i_units`,
   `profiles` (the four above), `state_changes`, `basis`, `flags`, `limitations`.
Flags to the top level (`band_plain.FLAGS` entries): `STRIP_TEMPERATURE_TERM_SUPPLIED_PROFILE`
and the conditional ones above.
Limitations (fixed): the temperature profile is an input, not computed (no per-width heat
balance, A3); the thermal strain is not fed back into the bite or the exit-tension feedback;
where the mechanical profile was saturation-scaled (slack band) the sum is indicative; the
temperature at the shapemeter is assumed equal to the scan; the after-cooling profile assumes
no creep or set in the coil (A8); no controller.

**Shapemeter** (package 4): `shapemeter_profiles` appends `steady_as_measured_hot`
(`profiles.as_measured_hot`). With `temperature_compensated = true` its label is "before the
shapemeter's own temperature compensation; a compensated system shows the mechanical profile",
and the flag `SHAPEMETER_TEMPERATURE_COMPENSATED` is set; with false or null the label is "what
the shapemeter shows".

**Report**: in `_width_section` a block "Strip temperature and flatness": the temperature scan
(small chart or table), a chart with the mechanical and the as-measured-hot I-unit profiles, a
table of the four profiles (peak, in-mill state, state after release) and the sentence, in a
`warn` paragraph: "The temperature profile was supplied, not computed. Flatness measured hot and
flatness after the coil has cooled differ by the thermal term: X I-units at Y mm." Not
supplied: one line ("No strip temperature scan: a 1 K hotter fibre reads about 2.4 I-units
loose at the shapemeter", the number computed from the default coefficient and labelled as a
textbook value).

**Demo.** Battery-foil scenario gains a synthetic scan (say so in `provenance` and in a notes
line: "synthetic: +3 K at the partly blocked nozzle, an assumption, not a model output"):
`positions_m = [0.15 + 0.05*i for i in 0..24]`, `temperature_k` =
`[353.15]*6 + [353.151, 353.197, 353.849, 355.757, 355.583, 353.717, 353.183] + [353.15]*12`
(= `round(353.15 + 3.0*exp(-4*ln2*((x - 0.6225)/0.10)^2), 3)`), coefficient null.

### Worked numbers (planner, `s21/nums.py`, `nums3.py`; battery-foil demo, full numerics)
- `i_units_per_kelvin = 2.36`; mean temperature 353.416125 K; largest deviation 2.332175 K.
- Thermal term: max 5.5039, min -0.6281 I-units; alone it is one loose band [0.560, 0.685],
  peak 5.5039 at 0.6025 m, latent in the mill, manifest after release.
- `mechanical`: peak 25.0888 at 0.6225 m, latent / manifest after release (equal to
  `width.shape.steady`: the test asserts band peaks and states are identical).
- `as_measured_hot`: peak 30.4694 at 0.6175 m, band [0.495, 0.745], latent / manifest after
  release; tight bands -5.8106 and -5.8524. No state changes in this demo.
- `after_cooling_if_hot_reading_held_flat`: one tight band, peak -5.5039, latent, flat after
  release.
- Shapemeter (24 zones): hot profile zone 9 reads 29.8136 against 24.4912 mechanical.

### Tests (`tests/test_band_strip_temperature.py`)
- `test_one_kelvin_step_is_2_36_i_units`: half the strip 1 K hotter -> `max - min` of the
  thermal term `= 2.36` (1e-9); custom coefficient scales linearly; default sets the flag.
- `test_uniform_temperature_gives_zero_and_equal_profiles`.
- `test_profiles_on_the_committed_demo_profile`: the numbers above (1e-3) computed from the
  artifact's steady profile and the scan of this brief; mechanical bands equal the artifact's.
- `test_hot_stripe_on_a_flat_strip`: no mechanical profile -> thermal only, flag set.
- `test_state_change_is_reported`: a hand case in which the thermal term lifts a 1.5 I-unit
  mechanical band above the 2 I-unit threshold.
- `test_scan_not_covering_the_strip`: end values held, width reported, flag.
- `test_validation`: every message; unsorted positions; wrong lengths.
- `test_absent_scan_changes_nothing`: `diagnose` with and without the scan on a small v2 case:
  everything outside `width.strip_temperature`, `measurement`, `inputs`, `flags` identical;
  hypotheses identical in both runs.
- report renders; no `nan`.

### Documentation
Guide: new 7.7 "Strip temperature across the width" (formula, the four profiles and why
`after_cooling` equals `mechanical` in a model without a controller, the bounding case, demo
numbers, limits); 3.12 pointer; 5.3 (how to take the scan: line-scan pyrometer or contact probe
on the coil face; the emissivity problem of aluminium, from the study section 7.4); 7.1 / 14:
the open "20 s" discrepancy paragraph gains one sentence (X5: the strip-temperature term in
measured flatness is one of two candidate causes the literature adds; not tested here); 12, 13,
14. README: one sentence. Gap study section 11: A1 and G6 `SCREENING_VERSION` (supplied
profile; computed profile needs A3; target-curve offset of TM-LA30 not built).

### What changes, what must not
Artifacts: additive; battery-foil gains the section, two flags, `inputs`, the extra shapemeter
profile and HTML block; the lengthwise demo gains the not-supplied entry and HTML line. No
existing value, no score.

### Do not
- Do not derive a strip temperature from the model's roll surface temperature or pass heating.
- Do not add the thermal term to `width.shape.steady`, the onsets, the gauge trend or any
  evidence rule.
- No target-curve offset, no controller, no coil cooling model.

---

## Package 7 — Friction / film stripe as a second band source (BT-G4, screening version)

### Why
The only band source in the shape chain is a roll bump. The bite report (gap BT-G4; BT-S1 FT for
the master curve, BT-S3 EX; mechanism [derived]) argues that a local difference of friction at
one width position (roughness, roll coating, oil supply or oil temperature) acts like a roll bump
because the load depends on friction with an exponent of about 2 to 2.6 [derived, slope read by
eye], with the sign opposite to the thermal-crown effect for a hot stripe, and that it "grows as
gauge falls". The full model needs BT-G1 and BT-G3. The row itself says a screening version is
possible now from the existing bite derivatives. That is what is built: a linear sensitivity
from `dF/dmu` of the existing bites, labelled with everything it rests on.

Finding of the planner, to be reported by the tool and not smoothed away: with the existing
models the claim "grows as gauge falls" holds for the load exponent and for the compliance-only
level, and does NOT hold for the level with exit-tension feedback (numbers below). The feedback
is the element of the chain the literature neither supports nor contradicts (X17).

### Design

**1. `strip_shape.transfer_force_profile`** (new, after `transfer_radius_profile`, line 517).

Derivation for the docstring [D, re-derived in SPEC17; the same balance as the incoming-ridge
formula in the `band_width.py` docstring, lines 51-55]: let `dp0'(z)` [N/m] be a local change of
roll force per unit width at an unchanged gap (here `M_mu*dmu(z)`). The strip answers a local
thickness change `dh` with `-Q_eff*dh`, so the net local force change is
`dp' = dp0' - Q_eff*dh`. Both roll surfaces indent under it, `dh = 2*C(lam)*dp'`, hence per
Fourier component

    dh_k = G(lam_k)*dp0'_k,   G(lam) = 2*C(lam)/(1 + 2*C(lam)*Q_eff)

with `C`, the clamps (`lam < 4a -> 4a`, `lam > R -> R`), `Q_eff = Q + N_x'*E_strip*xi/h_exit`
and the mean component keeping `Q`, all exactly as in `transfer_radius_profile`. Signs: more
friction -> more local force -> the rolls indent more -> the strip is locally THICKER
(`dh > 0`) -> shorter fibre -> tight. Limits: `Q_eff -> inf` gives `dh -> dp0'/Q_eff`; with the
feedback dominant, `eps = -xi*dh/h -> -dp0'/(N_x'*E_strip)`, independent of gauge.

```python
def transfer_force_profile(z_m, local_force_per_width_n_m, *, bite_half_length_m,
                           strip_stiffness_per_width_pa, roll_radius_m,
                           roll_youngs_modulus_pa=STEEL_E_PA, roll_poisson_ratio=STEEL_NU,
                           exit_tension_force_sensitivity_per_width_m=None,
                           exit_thickness_m=None, strip_youngs_modulus_pa=ALUMINIUM_E_PA,
                           xi=1.0) -> dict
```
Same validation style and result keys as `transfer_radius_profile` (`local_thickness_change_m`,
`peak_local_thickness_change_m`, spectrum fractions, flags, `formula_basis`, limitations);
`local_force_per_width_n_m` values in `[-1e9, 1e9]`. Share the DFT loop with
`transfer_radius_profile` through one private helper if that leaves the existing function's
numbers bit-identical (the existing tests of `tests/test_strip_shape.py` decide).

**2. Case schema.** `WIDTH_DEFAULTS` gains `'friction_stripe_screen': None`:

```json
"friction_stripe_screen": {
  "reference_half_peak_width_m": null,
  "stripes": [{"position_m": 0.9, "half_peak_width_m": 0.06,
               "friction_change_fraction": 0.10, "label": null}]
}
```
`reference_half_peak_width_m`: (0, 1] or null (default `REFERENCE_HALF_PEAK_WIDTH_M` = 0.1, the
gauge trend's reference); `stripes`: list, may be empty; `position_m` >= 0 on the barrel;
`half_peak_width_m` in (0, 1]; `friction_change_fraction` in [-0.9, 5], not 0 (relative change
of the pass friction coefficient); `label` optional nonempty string. Messages
"width_model.friction_stripe_screen.<key> ...".

**3. Friction sensitivity per pass.** `width_section` gets one more keyword argument,
`friction_sensitivity=None`: a callable `(src) -> dict` (the result of
`band_process.friction_force_sensitivity`, line 340) or raising `ValueError`. `diagnose` builds
it next to `get_bite` (line 3360):
```python
def friction_sens(src):
    b = cache.get(bp.bite_pass(eff, src))
    model = perturbed_bite_model(eff, b)
    return bp.friction_force_sensitivity(lambda q: cache.get(q, model=model), bp.bite_pass(eff, src))
```
(for the case pass use the operating bite and `sens_model`, as `sens_bite` does). It is called
only when the screen is supplied. Cost measured by the planner: about 10 s for the eight passes
of the battery-foil demo.

**4. Section** `width.friction_stripes` (new function in `band_width.py`), `not_supplied`
without the input, `NOT_ASSESSABLE` (with the reason) without a bite for the case pass. With
`M_mu = (dF/dmu)/width` [N/m per unit friction]:

- `case_pass`: `force_per_width_n_m`, `friction_coefficient`,
  `dforce_per_width_dfriction_n_m`, `load_exponent_in_friction = M_mu*mu/(F/width)`,
  `published_load_exponent = [2.0, 2.6]` with the note "[derived by the bite report, slope
  read by eye from BT-S1 Fig. 6a; regimes II-III at fixed gauge and reduction]".
- `reference`: a Gaussian friction stripe `dmu(z) = 0.01*mu*exp(-4*ln2*((z - z_c)/b)^2)` at the
  strip centre, `b` = the reference half-peak width; `dp0' = M_mu*dmu`; `dh` by
  `transfer_force_profile` with feedback and, separately, without
  (`exit_tension_force_sensitivity_per_width_m=None`); elongation and I-units as the shape chain
  does (`ss.differential_elongation` with flat entry, then `I = 1e5*(eps - mean)`). Keys:
  `i_units_per_percent_friction_with_feedback`, `..._compliance_only` (signed value at the
  stripe centre for +1 %), `friction_change_fraction_for_reporting_threshold` (=
  `0.01*2/abs(with-feedback value)`), `feedback_limit_i_units_per_percent`
  (= `-1e5*M_mu*0.01*mu/(N_x'*E_strip)`, before the mean is removed).
- `per_pass`: the same for the case pass and every schedule pass (`bp.pass_rows`), each with its
  own bite (`get_bite`), shape parameters (`shape_params_or_none(case, bite_i, w, src)`) and
  friction sensitivity; row keys `label`, `exit_thickness_m`, `friction_coefficient`,
  `force_per_width_n_m`, `load_exponent_in_friction`, both I-unit values, `bite_model`,
  `bite_flags`, or `rejected` with the reason. `band_diagnosis._apply_credibility` (line 2978)
  marks these rows exactly as it marks `gauge_trend.rows` (read it): not-credible rows are kept,
  marked and left out of `trend_text`.
- `trend_text`, generated from the credible rows ordered by exit gauge: states for each of the
  three quantities (load exponent, I-units per percent compliance only, with feedback) whether
  it rises, falls or is not monotonic as gauge falls, and ends with the fixed sentence: "Whether
  a friction stripe grows as gauge falls therefore depends on the exit-tension feedback, the
  least supported element of the shape chain."
- `stripes`: for each supplied stripe, `dmu = fraction*mu*Gaussian`, `dh` with feedback,
  `ss.flatness_from_elongation` (thickness, tension, moduli and yield as the shape chain):
  `peak_local_thickness_change_m`, `peak_i_units`, `sense`, `state`,
  `state_after_tension_release`, the band dict, the `i_units` profile and `z_m`. Linear chain
  only: when a band is `MANIFEST_BUCKLE` in the mill add the flag
  `FRICTION_STRIPE_LINEAR_FEEDBACK_NOT_SATURATED` (the roll-bump chain would cap the feedback
  there; not done here).
- `sign_note` (fixed): "A locally higher friction makes the strip locally thicker and the fibre
  tight; a locally lower friction makes it loose. For a hot roll stripe the film path (thinner
  film, more friction) therefore acts against the roll-growth path (larger roll, thinner strip).
  The net sign is not known (gap A2)."
- `conversion_placeholder` (only with `tribology`; every number flagged
  `PLACEHOLDER_FRICTION_CLOSURE_NOT_FITTED`): from `process.friction.operating` and
  `bt.friction_coefficient(film_ratio, closure)['dmu_dlambda']`:
  `friction_change_per_kelvin_oil = dmu_dlambda*Lambda*(-beta)` with `beta` the case's
  `temperature_viscosity_coefficient_per_k` (film proportional to inlet viscosity,
  `eta0 ~ exp(-beta*dT)`), and `friction_change_per_10_percent_roll_roughness =
  dmu_dlambda*Lambda*(-0.1*Rq_r^2/(Rq_r^2 + Rq_s^2))` (`Lambda = h/sqrt(Rq_r^2 + Rq_s^2)`),
  each also as a fraction of the pass friction. Note: "the closure's slope is not supported by
  data (X22); these conversions show orders of magnitude only".
- Flags (top level; `band_plain.FLAGS`): `FRICTION_STRIPE_SCREEN_APPLIED`; limitations: linear;
  `dF/dmu` from a constant-friction bite (central difference +-2 %); at foil gauge that bite is
  the experimental mattress model, 0.42 of the reference load on the one benchmark; friction
  taken as uniform through the bite; no film model across the width, no starvation (BT-G12),
  no coupling to the roll temperature (A2); entry tension uniform.
- `shapemeter_profiles` (package 4) appends one profile per supplied stripe
  (`friction_stripe_<k>`).

**5. Report**: in `_width_section`, block "A friction or oil-film stripe as a band source": the
per-pass table (gauge, load exponent, I-units per 1 % with feedback and compliance only, marks),
the trend text, the sign note, the supplied stripes with states, the placeholder conversions in
a clearly marked sub-block. Not supplied: one line.

**Demo.** Battery-foil scenario gains `"friction_stripe_screen": {"reference_half_peak_width_m":
null, "stripes": []}` (sensitivity table only; no planted stripe, so the demo's story stays the
blocked nozzle).

### Worked numbers (planner, `s21/g4a.py`, `g4b.py`, `g4c.py`; battery-foil demo, full numerics,
BEFORE package 2 changes nothing here: the screen does not use the film)

| pass | exit gauge um | `F/w` N/m | `M_mu` N/m | load exponent | I-units per +1 %, with feedback | compliance only |
|---|---|---|---|---|---|---|
| S1 | 135 | 709291 | 1.5071e7 | 0.637 | -4.13 | -54.6 |
| S2 | 85 | 612275 | 1.3598e7 | 0.666 | -3.01 | -78.0 |
| S3 | 50 | 736445 | 2.9314e7 | 1.194 | -4.44 | -235.2 |
| F1 = case pass | 30 | 958605 | 5.1403e7 | 1.609 | -3.15 | -392.2 |
| ALT1 | 25 | 1487662 | 9.5085e7 | 1.917 | -3.47 | -596.9 |
| F2 | 18 | 1536047 | 1.1052e8 | 2.159 | -2.74 | -566.4 |
| ALT2 (not credible) | 12 | 6187753 | 1.4171e9 | 6.870 | -2.29 | -872.2 |

Case pass: `friction_change_fraction_for_reporting_threshold` about 0.0063 (0.63 % of friction
for 2 I-units); feedback limit -3.49. Prototype values; the implementation's values may differ
in the third digit (pin your own after checking they agree to 1 %). A supplied stripe of -10 %
friction, half-peak width 0.06 m at 0.988 m on the case pass: `dh` peak -7.87e-08 m, loose band
[0.935, 1.04], peak +32.9 I-units, latent in the mill, manifest after release; +10 %: tight,
-32.7 I-units, latent, flat after release. Placeholder conversion at the case pass after package
2 (film ratio 0.380): `dmu_dlambda = -0.082*exp(-0.380) = -0.0561`; per kelvin of oil
temperature `+3.2e-4` (about +1.1 % of the friction 0.03 used).

### Tests
`tests/test_strip_shape.py` (new class): a single sinusoid of wavelength `lam`:
`transfer_force_profile(z, [-n*dR_i/(2*C(lam))])` equals `transfer_radius_profile(z, dR)` to
1e-9 relative (use `roll_line_compliance_m2_n`), with and without feedback; zero force gives
zero; the mean component keeps `Q`; the feedback-dominated limit; sign; validation;
`transfer_radius_profile` numbers unchanged.
`tests/test_band_friction_stripes.py`: the per-pass table of a coarse battery-foil-like case
(pin the implementation's values; assert the three trend statements of the table above:
exponent rises S1 -> F2, compliance-only magnitude rises, with-feedback values lie within a
factor 2 of each other); the reporting-threshold fraction; a supplied stripe's sense and states;
`NOT_ASSESSABLE` without a bite; not-credible row marked and excluded from the trend text;
placeholder block flagged and absent without tribology; validation; absent input -> everything
else identical; hypotheses identical; report renders.

### Documentation
Guide: new 7.8 "A friction or oil-film stripe as a band source" (derivation, the table from the
regenerated artifact, the finding on the gauge trend, the sign note, what it rests on); 3.5
(one paragraph: this second source and what the screen says about "worse at thinner gauge");
5.3; 12; 13; 14. Gap study section 11: BT-G4 `SCREENING_VERSION`, with the sentence that the
row's "grows as gauge falls" is reproduced for the load exponent and the compliance-only level
and not with the exit-tension feedback (numbers); A2 stays open.

### What changes, what must not
Artifacts: additive (battery-foil gains the section, one flag, `inputs`, HTML block; the
lengthwise demo the not-supplied entry). No evidence item: the hypothesis
`heat_streak_or_film_variation` is NOT given a model item (open decision 3).

### Do not
- Do not sum friction-stripe and roll-bump thickness changes into `width.shape.steady`.
- Do not derive `dmu(z)` from the roll thermal solution or the spray levels.
- Do not present the placeholder conversions outside their flagged block.
- Do not hide the not-monotonic with-feedback trend.

---

## Package 8 — Measured roll ground profile through the existing transfer (G13); tension-line pitch (G12)

### Why
- G13 (SS-S3 FT, model output; SS-S72 EX): grinding residuals and local wear are narrow
  diameter deviations that transfer like thermal stripes and that bending cannot remove; the
  project scores them by rules only. A measured profile can go through `shape_levels` as it is.
- G12 (SS-S53 EX, SS-S66 EX; pitch [D], formula [M] in the report): entrained-air corrugation in
  winding is a candidate model for foil tension lines, with a pitch that can be checked with a
  ruler. "A candidate, not an established explanation."

### Design A — `width_model.roll_ground_profile`

```json
"roll_ground_profile": {
  "positions_m": [...], "radius_deviation_m": [...],
  "detrend_order": 2, "rolls_carrying": 1, "provenance": "..."
}
```
`positions_m`: >= 5 strictly increasing positions on the barrel; `radius_deviation_m`: same
length, each in [-1e-3, 1e-3], deviation of the ground RADIUS from the intended shape, positive =
larger roll (half a diameter deviation); `detrend_order`: int 0..6 or null (null = no
de-trending), default 2; `rolls_carrying`: 1 or 2, default 1; `provenance` nonempty. Messages
"width_model.roll_ground_profile.<key> ...".

Section `width.roll_profile` (new function in `band_width.py`, called in `width_section` after
the shape block; needs the shape parameters `sp`, else `NOT_ASSESSABLE` with `shape_reason`):
1. Interpolate linearly onto the section's `z` grid (end values held outside the scan; report
   `extrapolated_width_m`).
2. `rt.local_stripes(z, values, strip centre, strip width, threshold_m=STRIPE_THRESHOLD_M,
   smooth_order=detrend_order)` (line 1003): its `local_radius_deviation_m` on the strip samples
   is the local deviation, its `smooth_profile_m` the removed crown or camber (report its
   peak-to-peak; it belongs to the crown model and is NOT passed to it here), its `stripes` the
   stripe list.
3. Put the deviation back on the full grid (zero outside the strip) and call
   `shape_levels(z, dev, dict(sp, n_rolls=rolls_carrying))`; keep `status`, `released_status`,
   `z_m`, `local_radius_deviation_m`, `local_thickness_change_m`, `i_units_with_feedback`,
   `i_units_linear_feedback`, the three peak values, `levels` and `flags`; add
   `stripe_table` by `steady_stripe_table` if its inputs fit (read line 1591), else a table of
   `stripe_states(levels, peak position)` per stripe.
4. `combined_with_thermal`: when `thermal_steady` exists, the same call on
   `thermal local_deviation_m + ground deviation` (both are radius deviations of the same
   roll; with `rolls_carrying` different from `rolls_carrying_stripe` skip it and say why).
5. `stiffness_check` [SS-S3 FT for the idea and the published ratios; the project analogue D]:
   `strip_foundation_modulus_pa = (F/width)/(h_entry - h_exit)` (Patel's `kf1`, as the report
   restates it), `roll_term_pa = 1/(2*C(lam))` with `lam` = twice the half-peak width of the
   largest stripe clamped to `[4a, R]` (the project's analogue, NOT Patel's `kf2`, whose
   definition was not recorded), their ratio, and the published context "thin aluminium
   0.236 mm: 176 / 57.8 kN/mm2, ratio 3.04; thin stainless: ratio 28, transfer almost
   negligible (model output)".
6. `position_match`: `ss.match_positions` of the band peak positions against the observed band
   positions with the section's position tolerance (`position_tolerance`, line 1512):
   information only.
7. `shapemeter_profiles` (package 4) appends `roll_ground_profile`.
Flags (top level; `band_plain.FLAGS`): `ROLL_GROUND_PROFILE_SUPPLIED`,
`ROLL_GROUND_PROFILE_BAND_ABOVE_THRESHOLD` (a with-feedback band exists). Limitations: the
profile is one roll's ground shape measured cold and off the mill; marks narrower than about
two grid cells or than `4a` are smoothed; no wear growth during the campaign; no barrel-position
modulation by roll bending (needs the roll stack, G1); the hypotheses `roll_surface_band` and
`grinding_feed_marks` stay rule-based and do not read this section.
Report: block "Measured roll profile" in `_width_section`: profile chart (measured, removed
polynomial, local deviation), the stripe table with I-units and states, the shapemeter readings
if present, the stiffness check as one sentence.

### Design B — candidate tension-line pitch

`strip_shape.shell_buckling_wavelength_m(radius_m, thickness_m, poisson_ratio=ALUMINIUM_NU)`
= `2*pi*sqrt(R*t)/(12*(1 - nu^2))^(1/4)`.
Derivation for the docstring [D, re-derived in SPEC17; the report quotes `3.47*sqrt(R*t)` from
memory]: axisymmetric buckling of a thin cylindrical shell of radius `R`, wall `t`, under axial
(here: width-direction) compression `N` per unit length:
`D*w'''' + N*w'' + (E*t/R^2)*w = 0`, `D = E*t^3/(12*(1-nu^2))`. With `w = sin(k*x)`:
`N = D*k^2 + E*t/(R^2*k^2)`, least at `k^4 = E*t/(R^2*D) = 12*(1-nu^2)/(R^2*t^2)`; full
wavelength `2*pi/k`. The critical stress `N/t = E*t/(R*sqrt(3*(1-nu^2)))` is the roller-wrinkle
value the project already uses (`roller_wrinkle_critical_lateral_stress_pa`, line 1328), which
the test uses as a cross-check. Coefficient: 3.4746 for `nu = 0.33`, 3.4564 for 0.3.

`band_width.Facts` (line 2233) keeps the radii it can find, each with a label:
`width_model.deflector_roll_radius_m`, `width_model.coil.inner_radius_m` / `outer_radius_m`,
`kinematics.deflector_roll_diameters_m[i]/2`, `kinematics.exit_coil_diameter_m/2`.
`_h_tension_lines` (line 2998) adds to its `model_prediction` dict (the evidence list is NOT
touched) the key `candidate_shell_buckling_pitch`:
`{'status': 'CANDIDATE_NOT_ESTABLISHED' | 'NOT_APPLICABLE_ABOVE_FOIL_GAUGE' (exit gauge >=
FOIL_GAUGE_M) | 'NO_RADIUS_IN_CASE', 'formula', 'poisson_ratio', 'rows': [{'where',
'radius_m', 'pitch_m'}], 'pitch_range_m', 'published_pitch_m': [0.005, 0.020],
'observed_spacing_m', 'observed_inside_candidate_range' (bool | null), 'how_to_test': 'Measure
the pitch at two coil radii and two gauges: this candidate predicts pitch proportional to
sqrt(radius x gauge).', 'basis': 'entrained-air corrugation in winding has the same remedies and
thin-gauge trend [SS-S53 EX, SS-S66 EX]; wavelength formula re-derived (classical shell);
no onset condition, no air-film model (G9, G10)', 'note': 'not evidence: almost any foil coil
gives a candidate pitch inside the published 5-20 mm'}`. The existing `'model': 'NONE: ...'`
text gains "; a candidate pitch is reported for comparison only".
Check how `band_report._hyp_section` and `band_plain` print `model_prediction`; render the block
as a short table in the tension-lines entry, not as a raw dict.

### Worked numbers
- G12 (`s21/nums.py`): 30 um exit, `nu = 0.33`: R 0.125 m -> 6.7285 mm; R 0.15 -> 7.3707 mm;
  R 0.45 -> 12.766 mm; R 0.6 -> 14.7414 mm. 18 um: 5.2119 / 5.7093 / 11.4187 mm
  (R 0.125 / 0.15 / 0.6). 12 um, R 0.125: 4.2555 mm. Cross-check: `E*t/(R*sqrt(3*(1-nu^2)))` at
  30 um, R 0.125, E 70 GPa = 10.2751 MPa = minus the project's roller-wrinkle value.
- G13 (`s21/nums2.py`): hand profile on the battery-foil mill: `positions_m = 0.00, 0.01, ...,
  1.50` (151 points), `radius_deviation_m = round(2.0e-6*(1 - ((x - 0.75)/0.75)^2) +
  0.3e-6*g(x; 0.50, 0.02) - 0.2e-6*g(x; 0.95, 0.03), 9)` with
  `g(x; c, f) = exp(-4*ln2*((x - c)/f)^2)`, `detrend_order = 2`, one roll, and the shape
  parameters of the committed artifact (`width.inputs_used`: strip stiffness 7.38875e10 Pa,
  bite half-length 1.19213e-3 m, exit-tension sensitivity 6.30883e-3 m; build them with
  `bw.shape_params(case, None, w, None, supplied={...})`): local deviation max +2.5827e-07 m at
  0.4975 m (half-peak width 0.0227 m), min -1.8181e-07 m at 0.9525 m; with feedback a loose
  band of +3.1289 I-units at 0.4975 m (latent in the mill, manifest after release) and a tight
  one of -2.0433 at 0.9525 m (latent, flat after release); compliance-only peak 360.27, rigid
  bound 860.90 I-units. A shapemeter of 23 zones of 52 mm centred at 0.75 m reads 1.1780
  (ratio 0.3765) and -1.0989 (0.5378): both below 2 I-units. This is the case where zone
  dilution hides a real band; use it in the guide.
  Stiffness check: `kf1 = 958605/20e-6 = 4.793e10 Pa`; `1/(2*C(0.04 m)) = 6.493e10 Pa`.

### Tests (`tests/test_band_roll_profile.py`; `tests/test_band_foil.py` for G12)
Hand profile above: local deviation, stripes, band peaks and states (1e-3), zone readings
(1e-3); `detrend_order` null keeps the crown; two rolls doubles the rigid bound; combined with
thermal on a coarse case; `NOT_ASSESSABLE` without shape parameters; validation; absent input ->
identical elsewhere; hypotheses identical (in particular `roll_surface_band` and
`grinding_feed_marks`). G12: coefficient 3.4746 (1e-4); the pitches above (1e-3 mm); the
critical-stress cross-check; `model_prediction` block for the battery-foil-like case, for a
sheet case (`NOT_APPLICABLE_ABOVE_FOIL_GAUGE`) and for a case without radii; every evidence item
and score of `foil_tension_lines` unchanged (compare with a run before the change through the
committed artifact's evidence list).

### Documentation
Guide: 7.9 "A measured roll profile" (how to enter a grinder report: radius, not diameter;
positions from the barrel end where the header starts; which order to de-trend), 3.7 (the
candidate pitch, its derivation, the ruler test; replace "no physical model" by "no established
model; one candidate pitch is reported", X16), 5.3, 12, 13, 14. Gap study section 11: G13
`SCREENING_VERSION` (measured profile through the existing transfer; stiffness indicator;
barrel-position modulation and wear open), G12 `SCREENING_VERSION` (pitch only; onset and air
film open), X16 `TEXT_CORRECTED`.

### What changes, what must not
Artifacts: additive (`width.roll_profile` not-supplied entries, `inputs`, the new
`model_prediction` key of one hypothesis in every result, HTML lines). No scenario gets a ground
profile. No score.

### Do not
- No evidence from the ground profile or the candidate pitch; no new "next measurement" line
  (the app maps those lines to questions).
- No wear model, no roll-stack modulation, no air-film or winding model.
- Do not pass the removed polynomial to the crown / heredity model.

---

## Package 9 — Guided app (plant-facing inputs and plain words for packages 3 to 8)

Read `SPEC16.md` in this scratchpad (the brief the app was built from), `docs/band-app.md`, the
docstring of `band_plain.py` and the three test modules first. The app's invariants hold: every
question has plain wording, help and a unit; no engine tokens or forbidden words in reader-facing
text (`engine_token_problems`, `FORBIDDEN`); every number shown is a number of the result;
drawn equals simulated; "Don't know" stays null; the trust rule is unchanged (none of the new
inputs is "ask first" and none raises or lowers trust).

### Questions (`band_plain.py`)
New units in `UNITS` (line 93): `'i_units': ('I-units', 1.0, 1.0, 0.0)`, `'ms': ('ms', 1.0,
1e3, 0.0)`, `'um_radius': ('µm on radius', 1.0, 1e6, 0.0)`. New group "Flatness and gauge
measurement" in step `mill`, questions with `unknown='null'` semantics as the existing nullable
sections use (`SECTIONS`, line 843; add entries for `measurement`, `measurement.shapemeter`
(required `zone_width_m`, `zone_count`; defaults for the rest, provenance "entered in the band
app"), `measurement.thickness_gauge`, `width_model.strip_temperature`,
`width_model.roll_ground_profile`, `width_model.friction_stripe_screen`):

| id | key | kind, unit | wording (plain) |
|---|---|---|---|
| `shapemeter_zone_width` | `measurement.shapemeter.zone_width_m` | number, mm | How wide is one measuring zone of your flatness roll? |
| `shapemeter_zone_count` | `...zone_count` | number, count | How many zones does it have? |
| `shapemeter_edge_zone_width`, `shapemeter_edge_zone_count` | `...edge_zone_width_m`, `...edge_zone_count_per_side` | mm, count | Narrower zones at the strip edges, if any |
| `shapemeter_spreading` | `...neighbour_spreading_fraction` | number, percent | Share of a zone's signal that spreads to each neighbour |
| `shapemeter_resolution` | `...resolution_i_units` | number, i_units | Smallest flatness difference your system shows |
| `shapemeter_temperature_compensated` | `...temperature_compensated` | yesno | Does it correct for strip temperature? |
| `gauge_spot_length`, `gauge_time_constant`, `gauge_sample_interval`, `gauge_position`, `gauge_spot_width` | `measurement.thickness_gauge.*` | mm, ms, ms, pos_mm, mm | The thickness gauge: spot size, response time, where it sits |
| `strip_temperature_scan` | `width_model.strip_temperature` (`positions_m`, `temperature_k`) | list: position (pos_mm), temperature (degc) | Strip temperature across the width, measured after the roll gap |
| `roll_profile_scan` | `width_model.roll_ground_profile` (`positions_m`, `radius_deviation_m`) | list: position (mm from the barrel end at nozzle 1), deviation (um_radius) | Measured roll profile from the grinder |
| `friction_stripes` | `width_model.friction_stripe_screen.stripes` | list: position (pos_mm), width (mm), change (percent) | A place where the oil film or roll surface is known to differ |
| `spray_wetted_arc` | `width_model.spray_wetted_arc_rad` | number, deg | How much of the roll circumference do the sprays wet? |

Help texts say where the value is found (shapemeter data sheet, grinder report, line-scan
pyrometer) and give the published examples with their status in plain words ("typical
commercial rolls: 26 or 52 mm zones; vendor figures"). The two list questions that map to
parallel arrays need a two-way conversion beside `_fold_nozzle_answers` (line 1412) and a
round-trip test (`test_round_trip_case_answers_case` must stay green for every preset, including
the battery-foil example with its shapemeter and scan). `answers_from_case` of the battery-foil
example must return the 24 zones and the scan.

### Summary (`plain_summary`, line 2991) and plain words
- `FLAGS`: check that every flag added by packages 3 to 8 has its sentence (they were added
  with the packages); rewrite any that reads like engine text.
- New views, each `{'available': bool, ...}` with numbers read from the result only (extend the
  view tuple of `test_summaries_build_and_keep_engine_numbers`, line 599):
  - `shapemeter_view`: zones (start, end, reading of the steady profile), the model profile,
    the threshold, bands (`position`, `model_peak`, `reading`, `shows`), and one sentence per
    band from two templates: "At {x} mm the model has a band of {p} I-units; a zone of {w} mm
    would read {r}: it would show on the flatness display." / "... would read {r}, below
    {t}: the flatness display would probably not show it." Plus the fixed sentence "The tool
    does not model what the flatness control would do with these readings."
  - `temperature_flatness_view`: the hot and cold peaks at the largest band and the sentence
    "Measured hot the band reads {h} I-units, after the coil has cooled {c}. The temperature
    profile was entered, not computed."
  - `friction_view`: the case-pass sentence "In this model a {f} % difference in friction at
    one place is enough for a 2 I-unit band. This rests on the least certain part of the
    model." and the stripe states.
  - `roll_profile_view`: bands of the measured profile with the shapemeter sentence when
    available.
  - `gauge_view` already exists for the gauge trend: name the new one `gauge_sensor_view`
    (kept share of each measured spacing; the sentence for "not detected").
- `GLOSSARY` (line 2292): "flatness roll zone", "I-unit" if absent.

### Page (`band_app_assets.py`) and server
- Form: the new group, collapsed by default, after the cooling questions.
- Drawing before a run: when zone width and count are answered, the strip drawing shows the
  zone boundaries under the nozzle row. The geometry must come from the engine's function
  (`band_sensors` zone edges through `drawing_model`, line 1765), never from the form values
  directly (`tests/test_band_app_drawing.py`: drawn equals simulated; add the zone layout to
  that test's comparison and to the pseudo-random edit sequence).
- Result: one new card "What your flatness roll would show" (bars per zone over the strip
  drawing, same horizontal scale as the strip view), and the three short text cards. Print
  layout: the shapemeter card is part of the one-page print only when available.
- No new server route.

### Tests
`tests/test_band_plain.py`: question table invariants with the new questions; unit round trips
for the three units; round trips for every preset; summaries of the regenerated artifacts
(numbers-in-result, no engine tokens, no forbidden words, flags described);
`tests/test_band_plain_partial.py`: views unavailable for the partial cases;
`tests/test_band_app_drawing.py`: zone layout; `tests/test_band_app.py` /
`test_band_app_reopen.py`: a run with a shapemeter stores and reopens.

### Documentation
`docs/band-app.md`: the new questions, the new cards, what each sentence means and does not
mean. README: one sentence. No engine doc changes.

### What changes, what must not
No engine module, no scenario, no artifact (byte-identical). The trust rule and `ask_first`
sets are unchanged.

### Do not
- No physics and no number computed in `band_plain.py` or in the page.
- No "your shapemeter cannot see this, so the cause is ..." wording: a reading below the
  threshold is a statement about the display, not about the cause.

---

## 3. Open decisions (the planner's choice is implemented unless the owner says otherwise)

1. **Herringbone rule and `Lambda < 1`.** `herringbone_lubricant_film_breakdown` also counts a
   film ratio below 1 as weak support (`band_diagnosis.py` 1974-1982): the same defect as the
   heat-streak rule, but the study names only the latter. Choice: leave the scoring, change the
   wording, record it in guide 14. If changed instead: herringbone loses 1 point in all four
   demos (bearing demo 2 -> 1, still rank 2 or tied), no leader changes.
2. **Sensors and the tally.** When the gauge cannot resolve the observed pitch, "gauge variation
   not detected" still counts against chatter-type causes. Choice: flag only in Phase 0 (no
   silent change of the ranking). Alternative for the owner: turn those items to `NEUTRAL` when
   the flag is set; it would move transverse scores only in cases that describe a gauge.
3. **A model item for the heat-streak hypothesis from the friction screen.** Choice: none
   (the screen rests on the mattress bite and the unsupported feedback).
4. **The steel chatter benchmark (X31).** Not runnable from the repository: no mill parameter of
   the paper is recorded. Choice: harness plus reference record; run it only if the paper's
   tables can be read in the coding session. The owner can settle it by supplying the paper.
5. **Basis of the published spray coefficient (X3).** Needs a clean copy of PT-T18. Choice: flag
   and conversion only. If it is a jet-zone value, the demos' 3.4 kW/m2K circumferential mean
   corresponds to about 20 kW/m2K inside a 60 degree jet zone, far above 2.5-4.3; the demos'
   coefficient would then be several times too high and the modelled stripes too low (the
   guide's own sensitivity: 4.67 um at 2 kW/m2K, 0.85 um at 13).
6. **New inputs in the battery-foil demo.** Choice: the demo gains a 24 x 52 mm shapemeter
   (package 4), a synthetic +3 K scan (package 6) and an empty friction screen (package 7); its
   artifact changes additively three times. Alternative: a separate scenario file and artifact
   pair for the sensor features, leaving the demo untouched after package 3.
7. **Default expansion coefficient of aluminium** (23.6e-6 /K, from memory in the reports).
   Choice: default with a flag. Alternative: make the key required.
8. **Agreement band of the benchmarks** (0.9-1.1 on the ratio): analyst choice.

## 4. Risks: where an exactly implemented result could still mislead a plant user

| risk | mitigation built into the outputs |
|---|---|
| The shapemeter readings look like a prediction of the operator's screen. They are zone means of a modelled far-field stress: no controller, no filter, no calibration, and a buckled band does not carry the linear stress. | Section heading "would show"; the `warn` sentence "no flatness controller"; flags; guide 7.6. "Below the threshold" is worded "would probably not show", never "was not there". |
| The demo's thermal stripe reads 98 % of its peak, so a reader may conclude that zone dilution never matters. It matters for narrow sources (ground marks, friction stripes): 3.1 I-units read 1.2. | The dilution table is always printed; guide 7.6 and 7.9 use the narrow-band case. |
| The neighbour-spreading model and the default "no spreading" are interpretations of one vendor sentence. | `basis` text; the input is off by default; guide. |
| Strip temperature: `after_cooling` equals `mechanical` only because the model has no flatness control. On a controlled mill the bounding case (the negative of the thermal term) is closer to what happens. A synthetic scan in the demo can be read as a model output. | The table of four profiles with the meaning column; the `warn` sentence "supplied, not computed"; provenance and notes of the demo; guide 7.7. |
| Friction screen: "0.6 % friction difference gives 2 I-units" looks precise. It is `dF/dmu` of a bite that is 0.42 of the reference load, divided by an exit-tension sensitivity the literature does not confirm; compliance only is a hundred times larger. | Both levels in one table; the trend sentence; limitations; the placeholder block kept apart and flagged. |
| After package 2 the "computed" friction at foil gauge rises (0.055 -> 0.064) and may be read as a better value. | The placeholder note (X22) is printed with it; guide 8.1: only the slope with speed was ever meant to be used, and that is not supported either. |
| A green benchmark test can be read as validation. | Test names and docstrings ("recorded discrepancy"); status string; guide 13. |
| The thermal check still says `WITHIN_PUBLISHED_RANGE` for the spray coefficient while the bases may differ. | `basis_comparable: NOT_ESTABLISHED`, the flag and the report line beside the verdict. |
| The candidate tension-line pitch falls inside the published 5-20 mm for almost any foil coil; a match proves nothing. | `note` in the block; "candidate, not evidence"; the ruler test (pitch against sqrt(radius x gauge)) is what is offered. |
| A grinder profile is measured cold, off the mill, on one roll; marks narrower than the grid are smoothed; `detrend_order` changes the result. | Limitations; the removed polynomial is drawn; guide 7.9. |
| The gauge transfer is a spot average and a first-order lag; real gauges have other filters. | "keeps about" wording; limitations; the flag says the tally was not changed. |
| Fire-limit rows compare a modelled strip exit temperature (inflated at foil gauge by the mattress slip) with a flash point. | The existing caveat `EXIT_IS_NOT_COIL` repeated in `fire_limits.note`; no default limit. |
