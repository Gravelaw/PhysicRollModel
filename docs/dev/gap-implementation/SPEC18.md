# SPEC18 — Phase 1 of the coverage-gap study: the foundations other models take their input from

**Amended 2026-11-19 / 20 after the research note** `research_phase1_equations.md` (in this
scratchpad; in the repository at `docs/dev/gap-implementation/research_phase1_equations.md`).
The first version of this brief is kept as `scratchpad/s23/SPEC18_before_amendment.md`; do not
read it. What changed:

1. Section 0.1 is rewritten. Withdrawn: the reading that the elastic no-slip equations (10)-(14)
   explain the load gap on the published foil case, and the appeal to the source's `E_s*` for the
   strip thickness spring. New: the published load of that case is not a grid-independent number
   (planner's own standard-library check, section 0.1); the benchmark target and verdict follow.
2. The bite solver gains the published backward-slip zone E and a fixed rule for choosing the zone
   structure; the earlier "final structure check" is gone.
3. The friction closure takes the published contact-ratio curve of a foil pass instead of two
   assumed end points; a Roelands pressure law and published kerosine-oil data are added.
4. The steel chatter case TM-LC7 becomes a runnable benchmark (with three stated substitutions).
5. The research note is moved into the research folder by package 1.
6. Twelve packages instead of nine (the research note and the reference records are a package
   of their own; the bite is three packages; oil properties and friction closure are two).
   Every package number in this text is the new one. Old -> new: 1 -> 2 and 3; 2 -> 4;
   3 -> 5 and 6; 4 -> 7; 5 -> 8; 6 -> 9; 7 -> 10; 8 -> 11; 9 -> 12. The Phase 2 brief (SPEC19)
   still uses the old numbers (section 5).

Repository `/home/user/PhysicRollModel`. Planned against commit `8f10cbe` PLUS everything SPEC17
(Phase 0, same scratchpad directory) specifies. State on 2026-11-20: commit `ec44a01` or later, Phase 0
packages 1 to 5 committed, later ones following; `physicroll/benchmarks.py` exists and
has row-level verdicts including `NO_REFERENCE_VALUE`; the briefs, the research note and the
prototype scripts are copied under `docs/dev/gap-implementation/` (working material). Read
SPEC17 section G first: it applies unchanged except for the changes of G' below. Sources of every
new fact: `docs/simulation-coverage-gaps.md`, the reports in
`docs/research/band-screening-2026-11/`, and the research note (source ids `E1`-`E19`). Nothing
else may be used as a source. Do not commit. No network.

Twelve work packages, executed one at a time in the order given, each leaving the repository
green. Section 0 holds what the planner measured; read it before package 1.

Scratch material of the planner in `scratchpad/s23/` (prototypes: copy, do not import from the
repository; where they differ from this text, this text holds). The repository copy
`docs/dev/gap-implementation/prototypes/phase1/` was taken before the amendment and lacks
`hs_select.py`, `sel_final.log`, `v_ramp.py`, `v_tol.py`, `v_cap_tm.py`, `v_tm.py`, `v_tm2.py`,
`v_fric2.py`, `v_p5.py` and `v_slipexp.py`:

| file | what it is |
|---|---|
| `hs_kernel.py`, `hertz_check.py` | influence coefficients, closed-form and Hertz self-checks |
| `hs_bite.py` | first solver class (zones A, B, F with contact end zones): residual, Jacobian, LU, Newton |
| `hs_solve2.py`, `run_v1.py` | cold start from the mattress bite, homotopy, structure switch during the march |
| `hs3.py` | general solver class: zone E, ramp or contact-zone ends, analytic nodal slope |
| `hs_select.py` | the structure selection rule of package 3 and chord sensitivities; `sel_final.log` holds its output for every case quoted here |
| `v_e2.py`, `v_e3.py`, `v_tol.py` | zone E on the published case, near the regime boundary, shear ratios of all candidate structures |
| `v_ramp.py` | the printed end conditions with a pressure ramp of prescribed length (the load family of section 0.1) |
| `v_slipexp.py` | exponents of load and forward slip in friction (package 7) |
| `v_cap_tm.py`, `cap3.py`, `inv2.py` | shear cap by friction march, spurious slope root, friction inversion |
| `v_tm.py`, `v_tm2.py` | TM-LC7 in the project's chatter model |
| `v_fric2.py`, `v_p5.py`, `fric.py` | crushing laws, height distribution, flow factor, Roelands and Barus against the measured oil, film checks, contact-ratio and valley-film curves, valley shear |
| `heat.py` | heat partition (numerical and closed form), flow-stress and skin hand numbers |
| `skin2.py`, `skin3.py` | periodic roll surface layer, arc-aligned stepping, superposition; step response |
| `t_mattress.py`, `t_diag.py`, `t_survey.py` | timing of the present solvers and their callers |
| `head/` | export of commit `8f10cbe` used for all timings (never the working tree) |

---

## G'. Rules that differ from SPEC17 section G

**G'1. Opt-in models, not only opt-in inputs (replaces G3 for this block).** No package changes
an evidence item, score, standing or leader of any committed artifact. Every new model is either
(a) computed and reported beside the present value, or (b) selected by an explicit case key whose
default is the present behaviour. The committed scenarios are not switched to any new model.
There is NO "switch the default" package in this block (section 0.1, open decision 2). G6 applies
to every package with "additive only" as the allowed classification; anything else is a fault.

**G'2. Tags.** As SPEC17 G2. Formulas re-derived here carry `[D, re-derived in SPEC18]`. Source
ids of the research note keep its prefix and read tag (`E1 FT`, `E6 FT`, `E9 FT`, ...). Two tags
are new and are never written as a published value:
`[computed, re-implementation of E1]` = a number the research note obtained with its own numpy
re-implementation of the printed foil model;
`[computed, SPEC18 prototype]` = a number of the planner's standard-library prototypes.
Where the note says "as printed" (misprints in E1 eqs (20), (30), (36)), code comments say which
form is used and why. A reduced model built because the sources do not contain a usable full one
says so in its status string, in a flag and in the guide, and names the input a user must supply.

**G'3. Status words for section 11 of the gap study** (added to the fixed list of SPEC17 G7):
`REDUCED_MODEL_OPT_IN` (a reduced form of the row's model exists behind a case key; the default
is unchanged; the row's full model is not built) and `ROUTINE_ADDED` (a calibration or
identification routine that works on entered measurements).

**G'4. App invariants are wider than SPEC17 G5 lists.** `tests/test_band_plain.py`
(`section_53_keys`, `test_every_section_53_key_has_a_question`, `test_choices_are_the_engine_
lists`) also requires: a question for every key of `band_diagnosis.OPTION_KEYS + OPTION_OPTIONAL`
(except `bite_response_override`), for every key of `band_process.TRIBOLOGY_KEYS +
TRIBOLOGY_OPTIONAL` that is not a nested section, for every key of
`band_process.HARDENING_COMMON` and of every tuple in `HARDENING_LAW_KEYS`, and the choice lists of the questions `bite_model` and
`hardening_law` equal to `band_diagnosis.BITE_MODELS` and `tuple(HARDENING_LAW_KEYS)`. A package
that extends one of these adds the question (one plain sentence, help text, unit) in the same
package; package 12 only refines wording and layout. Keys this brief places elsewhere
(`tribology.lubricant.*` beyond the present six, `tribology.friction_closure.*` beyond the present
three, `hardening.rate_temperature`, `width_model.circumferential_layout`,
`measurement.pass_records`) are outside those lists on purpose and get their questions in
package 12. `band_survey_mills.MACHINES[...]['tribology']` gains every new optional tribology key
with `None` in the package that adds it (drift guard
`test_packaged_mills_equal_the_demo_machine_sections`).

**G'5. Benchmarks.** Every model of this block gets at least one case in
`physicroll/benchmarks.py`. Read the module as committed (case list, the three-part record,
case-level and row-level verdict words, the `test_<id>_recorded_discrepancy_...` naming) and
follow it; where this brief names a field the committed harness spells differently, the harness
wins. New ids are appended; `NOT_ENCODED` is edited where a package encodes a row. One verdict
word is added (package 1): `REFERENCE_NOT_GRID_INDEPENDENT` = the published value comes from a
calculation whose result depends on a numerical detail the source does not state; the ratio is
recorded and not judged. A verification against a published value is software verification plus
a literature comparison; every result keeps `SCREENING_RESULT_NOT_PLANT_VALIDATED`.

**G'6. Run time is a requirement.** Each package reports the measured times named in its
"Budget" paragraph. If a budget is missed, stop and report; do not loosen it.

**G'7. Numbers in this brief.** Every number given as a test target was produced by a planner
prototype named beside it. Pin the implementation's own value after checking that it agrees with
the brief's to the stated tolerance (0.5 % where none is stated); if it does not, stop and
report. Numbers quoted from the research note that the planner did not reproduce are marked so
and are never test targets.

---

## 0. What the planner measured and found (read before package 1)

### 0.1 The half-space bite, the published case and what "118" means

**What was checked of the research note's claims** (all with the standard library, in `s23/`):

| claim of the note | planner's check | result |
|---|---|---|
| The derived kernel has the right sign; printed eq. (30) of E1 has the opposite one | Hertz self-check of the derived kernel (`hertz_check.py`) | confirmed for the derived kernel (0.26 % of the indentation depth at 80 elements); the printed form was not re-read |
| Zone E (backward-slip reduction between the no-slip zone and the peak) changes the load by under 0.3 % | zone E added to the prototype (`hs3.py`, `v_e2.py`) | confirmed: -0.09 % on the published case with a rigid strip, -0.06 % at 400 GPa, -0.01 % and -0.08 % on two demo passes; it removes the shear demand above the friction limit at the downstream end of the no-slip zone |
| With the printed end conditions the load depends on the length over which the bite ends are closed: 88 to 135 for 21 to 2.5 um | the printed conditions with a pressure ramp of prescribed length and the analytic nodal slope (`v_ramp.py`) | confirmed within 0.8 %: 88.6 / 102.6 / 117.5 / 134.2 at 21 / 10 / 5 / 2.5 um against the note's 88.0 / 101.9 / 116.6 / 133.2; no limit as the length goes to zero |
| 118 needs an end length of about 5 um | same | confirmed: 117.5 at 5 um |
| The plotted curve and the contact length 2.14 mm of E6 correspond to about 102-105 | same family | consistent: 2.131 mm at `W_bar` 102.6; the by-eye reading of the figure itself was not repeated |
| `E_s*` enters only eqs (12)/(14); load, torque, pressure and shape do not depend on (10)-(14) | cannot be checked without the paper; taken from the note's quotations (E1 FT) | accepted as read; the planner's earlier reading is withdrawn |
| Crushing fits, flow factors, Roelands, film formula against the thesis table (checks C6-C9) | `v_fric2.py` | reproduced (values in packages 5 and 6) |
| The inlet analysis of E6 is "found in full" | static height-distribution relation against the thesis table's own pairs of contact ratio and mean film | NOT confirmed as implementable: the static relation gives 0.905 to 0.495 of the tabulated mean film (package 6, "Why") |
| TM-LC7 inputs | the project's chatter model run on them (`v_tm.py`, `v_tm2.py`) | runnable with three substitutions (package 1) |

**The published case (Fig. 9 of E1 = BT-V1): planner's numbers** `[computed, SPEC18 prototype]`.
R 89 mm, 20 -> 15 um, `Y_s` 230 MPa, `E_R*` 230 GPa, mu 0.03, no tensions.

| model | `W_bar` | contact length mm | peak `p/Y_s` at x mm | forward slip |
|---|---|---|---|---|
| caption of Fig. 9 (E1 FT) | 118 (full numerical), 120 (perturbation), 62 (Fleck-Johnson mattress) | - | - | - |
| contact length of the same case in E6 (FT, thesis p.54) | - | 2.14 | - | - |
| Fig. 9 read by eye by the note | about 105 by trapezoid | about 2.1 | about 7.7 at +0.41 | - |
| project mattress (Phase 0) | 49.77 | 1.474 | - | 0.170 |
| **package 2-3 solver, strip rigid in thickness** (`E_s*` 1e13 Pa; structure A B E F) | **88.859** | 1.9614 | 7.521 at +0.305 | 0.2047 |
| **package 2-3 solver, strip thickness spring 80 GPa** (structure A B F) | **92.936** | 2.0384 | 7.331 at +0.349 | 0.2037 |
| printed end conditions, pressure ramp 40 um outside both ends, rigid strip | 78.01 | 1.877 | 7.48 at +0.222 | 0.2108 |
| ramp 30 um | 82.57 | 1.920 | 7.56 at +0.255 | 0.2072 |
| ramp 21 um (the element size the paper states: about 100 elements over about 2.1 mm) | 88.62 | 1.981 | 7.66 at +0.297 | 0.2022 |
| ramp 15 um | 94.73 | 2.046 | 7.75 at +0.337 | 0.1970 |
| ramp 10 um | 102.62 | 2.131 | 7.85 at +0.386 | 0.1902 |
| ramp 7 um | 110.04 | 2.211 | 7.94 at +0.431 | 0.1838 |
| ramp 5 um | 117.47 | 2.289 | 8.02 at +0.474 | 0.1775 |
| ramp 3.5 um | 125.82 | 2.374 | 8.10 at +0.520 | 0.1706 |
| ramp 2.5 um | 134.15 | 2.458 | 8.18 at +0.564 | 0.1638 |

(Ramp rows: structure A B F; with zone E the loads are 88.55 / 102.56 / 117.44 at 21 / 10 /
5 um.) In every ramp solution the strip thickens over the last elements before the exit, by
0.03 % of the exit gauge at 40 um and 0.57 % at 2.5 um: the printed end conditions violate the
model's own requirement that the thickness never increases, more so the shorter the end.

Findings the coder must carry into code comments, result notes and documents, unsoftened:

1. **The published 118 is not a grid-independent number.** The printed model ends the bite with
   a pressure step from `Y_s` to zero and asks for `db/dx = 0` there; a pressure step on a
   half-space has a logarithmically infinite surface slope, so the condition means something
   only relative to the length over which the step is smeared. Two independent
   re-implementations (the note's in numpy, the planner's in the standard library) give the same
   family: 78 to 134 for 40 to 2.5 um, no limit. 118 is obtained at about 5 um; at the element
   size the paper states, 88 to 89. What "118" means: the caption value of one unstated end
   length. It is recorded, not used as a target.
2. **The solver of packages 2 and 3 closes the exit physically and is grid-converged.** It
   keeps the exit contact zone the paper neglects (its eq. (13): strip of constant thickness
   still pressed by the roll, sliding, pressure falling to zero). With the strip rigid in
   thickness, as the paper assumes, it gives 88.86 (0.1 % change on a doubled grid, 0.4 % with
   the spring of finding 3); that
   coincides with the printed model at the paper's stated element size (88.6). It is 0.753 of
   the caption value, 0.916 of the independent contact length (2.14 mm), and by the note's
   by-eye reading 0.85 to 0.87 of the plotted curve. None of these ratios is a verdict on the
   model; the benchmark records them (package 4).
3. **The strip thickness spring is the planner's addition, not the source's.** E1 neglects the
   elastic thickness change of the strip; its `E_s*` enters only the longitudinal no-slip
   equations. The spring `c_s = h_ref/E_s*` is kept for two stated reasons: the strip does
   compress (0.3 % of its thickness per `Y_s` of pressure for aluminium), and without it the
   ENTRY contact zone has no length (the roll would have to conform to a flat on an incline:
   `s23/dbg2.py`). Its effect is reported, not hidden: +4.6 % load on the published case (88.86
   rigid, 92.94 at 80 GPa, 96.8 at 40 GPa). It is a load-determining input of the model.
4. **Zone E belongs in the solver.** Not for the load (under 0.1 %), but because it is the
   published structure (E1 FT, Appendix 2, condition 2), it keeps the no-slip zone within the
   friction limit, and it makes the passage from regime I to regime II continuous. Without it
   there is a band of inputs at the regime boundary where the no-slip structure needs up to 1.44
   times the friction limit while the conventional structure thickens before the neutral point
   (the demo's main pass, 50 -> 30 um at friction 0.03, sits at the edge of that band).
5. **Regime boundary and load exponent agree with the source.** No-slip zone appears between 54
   and 52 um entry gauge at r = 0.5 (eq. 29: 51.2), between 34 and 32 um at r = 0.25 (36.2),
   between 28 and 26 um at r = 0.10 (22.9). Load exponent in friction at the published case
   2.46 (the bite report derives 2 to 2.6 from the master curve, slope read by eye).
6. **Newton on a boundary-fitted grid replaces the published iteration.** E1 iterates the
   pressure with the shape, solves the no-slip zone from its eq. (35) and moves four boundaries
   by Newton-Raphson; the reports add under-relaxation of 0.1-0.5 [BT-S14 FT]. The prototype
   solves pressures, boundaries and levels in one Newton system with a line search. This is a
   deliberate difference of method, not of equations.
7. **Foil loads rise against the mattress bite.** On the battery-foil demo schedule at the
   supplied friction 0.03: 1.37 / 3.24 / 2.66 / 10.13 kN/mm for F1 / F2 / ALT1 / ALT2 against
   the mattress 0.96 / 1.54 / 1.49 / 6.19 (trade range quoted by the project: 0.9-2.3 kN/mm).
   With a load exponent in friction of about 3 at these gauges, F2 would return into the range
   at a friction of about 0.027. This is why the model stays opt-in and why friction
   identification (package 7) belongs to the same block.
8. **Friction closure.** The published contact-ratio curve of a 20 um foil pass (E6 FT,
   Table 4.2) gives a contact ratio of 0.69 at a film ratio of 0.36; the two end points assumed
   in the first version of this brief gave 0.22 there. With that curve the friction level is
   set almost entirely by the friction on the contact areas, for which the sources span 0.013
   to 0.1. A closure can therefore give a defensible SHAPE against speed, not a level.
9. **Heat split.** A lumped strip on a half-space roll with perfect contact gives a strip share
   of 0.162 for the thermal report's own check case (24 um, 0.2 ms); with a 70 nm oil film
   0.228 at the sourced ambient oil conductivity (0.125 W/mK) and 0.195 at the in-nip value
   (0.25 W/mK) [E6 FT]. All lie inside the measured 0.11-0.33 [TM-LA19 AB].

### 0.2 Timings and budgets (Python 3.13, one core, export of `8f10cbe`)

| item | measured |
|---|---|
| one converged mattress solve (`foil_bite._converged`) | 0.02 s |
| `derive_bite_response_mattress` (18 converged solves) | 0.17-0.46 s |
| `chatter.derive_bite_response` (Hitchcock, 256 cells) | 0.9-1.0 s |
| half-space prototype, cold start with structure selection (62-70 elements) | 0.3-1.5 s on 27 of 29 cases; 1.8 s and 2.8 s on two cases at the regime boundary |
| half-space prototype, 12 sensitivities by chord iterations | 0.07-0.15 s |
| `diagnose`, battery-foil demo | 72.6 s; bite derivations 7.6 s (24 mattress calls 4.0 s, 7 Hitchcock 3.6 s) |
| `diagnose`, lengthwise demo | 48.7 s; bites 22.1 s (29 Hitchcock) |
| `diagnose`, thin-gauge chatter / bearing demo | 18.6 s / 8.7 s; bites 17.6 s / 7.9 s |
| guided app, quick profile on the battery-foil case | 13.8 s; bites 4.8 s |
| product survey | 46.1 s; bites 18.9 s (33 Hitchcock, 18 mattress) |
| periodic skin-layer solve, one station (prototype) | 0.14 s (368 steps per revolution, 60 revolutions) |
| heat partition, 400 steps | under 0.05 s |

Budgets that follow:

- A half-space derivation (nominal solve plus sensitivities) may cost at most 3.5 s cold and
  0.6 s warm-started, 1.2 s on average over the 15 demo passes. Then a battery-foil `diagnose`
  with `bite_model: 'auto_half_space'` stays under 105 s and the quick profile under 32 s.
- With the default bite models nothing may slow down by more than 2 % (the new code is not on
  the default path).
- Each new test module stays under 60 s; split a module that would pass 45 s.
- The new sections of packages 9 and 10 add at most 3 s to a `diagnose` that supplies their
  inputs and nothing measurable to one that does not.

---

## 1. Overview

| # | Package | Gap ids | What changes for a user | Default or opt-in | Depends on | Size (lines changed, with tests and docs) |
|---|---|---|---|---|---|---|
| 1 | Research note into the repository; reference records; steel chatter benchmark | BT-G17, X18, X31 | The note with the recovered equations sits with the other reports; the benchmark table says what the published foil load rests on; the steel chatter onset is run | harness only | SPEC17 pkg 1 | 400-550 |
| 2 | Half-space bite: kernel, equations, Newton, cold start | BT-G1 (core), BT-G5 | New module `physicroll/halfspace_bite.py`; nothing in the engine uses it yet | not wired | 1; SPEC17 pkg 2 (flag name) | 750-850 |
| 3 | Half-space bite: zone E, structure selection, friction march, warm start | BT-G1, BT-G5 | The solver returns one admissible zone structure for every pass in its domain, also at friction where the mattress bite rejects | not wired | 2 | 550-700 |
| 4 | Half-space bite: sensitivities, engine, benchmarks | BT-G1, BT-G5, BT-G17 (new rows) | `model_options.bite_model: 'half_space' / 'auto_half_space'`; benchmark rows for the published case; a bite-model comparison for any case | opt-in | 3; SPEC17 pkg 1, 2, 7 | 750-900 |
| 5 | Oil properties: viscosity table, Roelands pressure law, Eyring and limiting shear stress | A9 | Oil viscosity from data-sheet points; Roelands as a second pressure law with its measured error; fields for the Eyring and the limiting shear stress | opt-in | 1; SPEC17 pkg 2 | 450-600 |
| 6 | Friction closure on the published contact-ratio curve; published fits as tested functions | BT-G3 (reduced) | A load-sharing friction law whose contact ratio follows a published foil curve and whose level is an entered contact friction; tested crushing, height-distribution and flow-factor functions for a later inlet analysis | opt-in | 5 | 650-800 |
| 7 | Friction from load, torque and forward slip | BT-G6 | New optional `measurement.pass_records`: friction that reproduces each measured force, slip and torque, their disagreement, and the contact friction it implies | new input; never applied | 4, 6; SPEC17 pkg 4 | 550-700 |
| 8 | Flow stress: rate, temperature, law forms, fit | B1, B2 (with B3 of SPEC17) | Optional rate and temperature factor on every pass flow stress; Tome-Voce law; signed late slope; fit to the plant's pass strengths; the rate share of the chatter damping heuristic reported | opt-in | none | 650-800 |
| 9 | Computed bite heat partition | A3, X4 | Strip heat share computed beside the supplied one for every pass, also at the two published oil conductivities; optional use | computed and reported; use is opt-in | 5 (film), 4 (contact length) | 600-750 |
| 10 | Roll surface layer within one revolution | A4, G8, X5 (part) | New optional `width_model.circumferential_layout`: surface temperature around the roll, at bite entry per width station, three time scales, bias of the circumferential-mean coefficient | new input | 9; SPEC17 pkg 3 (`spray_wetted_arc_rad`) | 700-850 |
| 11 | Spray coefficient calibration | A5 (routine) | `python -m physicroll.band_cli CASE --calibrate-spray`: the coefficient that reproduces an entered roll temperature scan or camber, with its misfit curve | routine; never applied | none (10 optional) | 450-600 |
| 12 | Guided app | plant-facing side of 4-11 | Questions, plain words and cards for the new inputs and outputs | - | 4-11 | 650-850 |

Out of scope for every package (Phase 2 and 3): friction, film or flow stress varying across the
width (A2, BT-G4 in full, BT-G12); friction varying through the bite; the longitudinal elastic
equations of E1 ((4), (10)-(14)) and with them stress and traction inside the no-slip zone,
regime-III zones C and D (BT-G15); an inlet analysis with asperity crushing (BT-G3 in full);
hardening inside the bite (BT-G16); any change to `slab.py`, `contact.py`, the mattress
equations or `chatter.assemble_state_matrix`; closed gap; roll stack; flatness controller; A6;
coil models; any new hypothesis, evidence item or observation key.

---

## Package 1 — Research note into the repository; reference records; steel chatter benchmark (BT-G17, X18, X31)

### Why
The research note recovered the governing set of the foil-bite source, the inputs of the steel
chatter benchmark and several material laws. Packages 2 to 9 cite it, so it has to sit with the
other reports first. Two things in the Phase 0 harness change with it: the reference of the
published foil case needs its caveat (section 0.1, finding 1), and the chatter case
`TM-LC7`, recorded by Phase 0 as `REFERENCE_ONLY_INPUTS_NOT_RECORDED`, can now be run.

### A. Move the research note
1. `git mv docs/dev/gap-implementation/research_phase1_equations.md
   docs/research/band-screening-2026-11/phase1-equations.md`. Move the file as delivered. Change
   NOTHING in it except file names in cross-references: its own title line stays; references to
   `gap-bite-tribology.md`, `gap-thermal-material-dynamics.md` and `process-temperatures.md` are
   already relative to that folder; `scratchpad/s24/scripts/` and `s24/scripts/` become
   `../../dev/gap-implementation/prototypes/phase1-research/` (where commit `ec44a01` put those
   scripts); `scratchpad/s24/dl_*` becomes "downloaded files: not kept in the repository".
   No equation, number, tag or sentence is edited, including the note's section 9 (its advice to
   this brief): it is a dated record.
2. `docs/research/band-screening-2026-11/README.md`: one index row (file, date 2026-11-19,
   scope "equations and constants the gap reports cite without giving", source prefix `E`), and
   in the tag rules: the note's tags (`FT`, `EX`, `AB`, `VP`, `CIT`, `[derived]`,
   `[from memory]`, "as printed") with one sentence each, taken from the note's own list.
3. `docs/dev/gap-implementation/README.md`: in its table, the row of the note says where it
   went (link) and the `SPEC18.md` row loses "To be amended" (twelve packages).
4. Gap study: in section 11 (implementation status) one line under the table: "Equations and
   constants recovered after the study: research/band-screening-2026-11/phase1-equations.md
   (source ids E1-E19)". No other text of the study changes.

### B. Reference record of the published foil case
In `physicroll/benchmarks.py`, for the existing mattress case `BT-V1` (do not change its
project value, its recorded value or its verdict against the caption value):
- add the verdict word `REFERENCE_NOT_GRID_INDEPENDENT` to `VERDICTS` (G'5), with its
  definition in the module docstring;
- `_case` gives every row with a reference the case verdict. Packages 1, 4, 5, 6 and 9 need rows
  with their own verdict: give `_quantity` an optional `row_verdict=None` that `_case` keeps
  when set (one of `VERDICTS` or `NO_REFERENCE_VALUE`). Existing cases are unchanged;
  `test_run_all_is_json_safe_and_complete` then accepts any word of that list for a row and
  keeps its rule that a row has `NO_REFERENCE_VALUE` exactly when its reference value is
  `None` (a cross-check number that is not a published value goes into the row label, not into
  `reference_value`). `RECORDED_ON` is one constant today: new pins carry their own date and
  commit (optional `recorded_on` of `_quantity`);
- add to the case a `reference_caveat` (or the harness's note field) with this text: "The
  caption value 118 is not a grid-independent number: the printed end conditions (pressure step
  at exit, zero slope there) give 78 to 134 for end lengths of 40 to 2.5 um in two independent
  re-implementations [computed, re-implementation of E1; computed, SPEC18 prototype]; 118
  corresponds to about 5 um, the element size stated in the paper (about 21 um) to 88-89. See
  case BT-V1-HS.";
- add one reference row: contact length, project 1.474 mm (the mattress value) against
  2.14 mm [E6 FT, thesis p.54: `b/R` = 0.0241 with R 88.9 mm; MODEL_OUTPUT of the same
  published solution]; ratio 0.689, row verdict by the band (`RECORDED_DISCREPANCY`);
- put the Fig. 9 landmarks read by eye by the research note into the case note as text (the
  mattress case has no rows for them; package 4 compares them): entry -1.18 mm, `p/Y_s` about
  6.1 at the centre line, peak about 7.7 at +0.41 mm, exit +0.95 mm, reading error about
  0.03 mm and 0.2 [E1 FT figure, read by eye];
- `input_notes` of `BT-V1`, `BT-V2-*`: "E_s* = 80 GPa enters only the longitudinal no-slip
  equations of the source and none of its loads [E1 FT]"; for BT-V2 "roll radius, roll modulus,
  speed and width are not stated in the source [E1 FT, confirmed by a second full reading]".
The mattress ratio 0.42 stays a `RECORDED_DISCREPANCY`: against every member of the family
(78 to 134) the mattress value 49.8 is low by a factor 1.6 to 2.7.

### C. `TM-LC7`: the steel chatter onset as a runnable case

Can the project's chatter model represent the paper's case? Its STRUCTURE exactly; its PROCESS
MODEL not:

| element | paper [E9 FT] | project | what the case does |
|---|---|---|---|
| stand | two masses per half stack, eqs (3.13), (3.14) | the same equations (`chatter.py` docstring) | exact mapping (table below) |
| roll flattening | none | Hitchcock; rejects this pass at any friction of 0.02 or more (`R'/R` 2.9 at 0.015, 3.5 at 0.02, diverging at 0.03: planner, `v_tm.py`) | substitution 1: `roll_youngs_modulus_pa = 1e14` (the upper limit of the derivation), which gives `R'/R` = 1.002 |
| friction | friction FACTOR `m` = 0.054 on the shear yield stress | Coulomb | substitution 2: the Coulomb coefficient with the same mean friction stress, `mu = m*k/p_mean`, found by fixed point: 0.026566 (`p_mean` 1088.8 MPa) |
| mill | two stands, chatter in the second, stress waves between the stands | one stand, lumped spans with constant-speed far ends | substitution 3: stand 2 alone with its two spans |
| bite damping | from the paper's dynamic process model | heuristic transit fraction | both 0.5 and 0 reported |

The reduced half-space bite cannot stand in for the paper's process model either: with rigid
rolls and the shear cap used as a friction factor the forward slip of this pass falls to 0.004
and the friction march fails before the cap is active everywhere (`v_cap_tm.py tm`). So the case
is a comparison of the paper's structure with the project's own bite under the paper's
flattening assumption, labelled as such; it is not a re-run of the paper's model.

Inputs (every value [E9 FT, Tables 1, 3, 4, 5], stand 2):

| project input | value | source row |
|---|---|---|
| `work_roll_mass_kg`, `backup_roll_mass_kg` | 14000, 38000 | work / backup roll mass |
| `work_backup_contact_stiffness_n_m` | 7.01e10 | "work roll spring constant" (between work and backup roll in (3.13)) |
| `housing_stiffness_n_m` | 3.64e8 | "backup roll spring constant" |
| `work_backup_damping_n_s_m`, `housing_damping_n_s_m` | 0, 9.54e5 | work / backup roll damping coefficient |
| entry, exit thickness | 324e-6, 216e-6 m | |
| width, work roll radius | 0.732 m, 0.245 m | |
| `mean_flow_stress_pa` | `sqrt(3)*535.65e6 = 927.773e6` | shear yield stress `k` 535.65 MPa; the project's `K = 2Y/sqrt(3) = 2k` |
| entry, exit tension | 151e6, 81e6 Pa | inter-stand and exit tensile stress |
| spans | `youngs_modulus_pa` 200e9, entry 4.725 m, exit 6.6 m | Tables 1, 4 |
| friction | 0.026566 (substitution 2; `m` = 0.054) | |
| roll modulus | 1e14 Pa, Poisson 0.3 (substitution 1) | |

`chatter_onset_comparison` (Phase 0) builds the stand from a modal damping ratio: extend it so
that a `stand` dict carrying `work_backup_damping_n_s_m` and `housing_damping_n_s_m` builds
`chatter.StandModel` directly. Add a helper `equivalent_coulomb_friction(bite_pass,
friction_factor, shear_yield_pa, **bite options)` (fixed point `mu <- m*k*width*L/F`, start
0.025, tolerance 1e-9, at most 50 derivations) `[D, SPEC18]`. Speed scan `(0.5, 60.0)` m/s,
`cells` 256.

Reference [E9 FT, Table 5]: measured onset 5.81 m/s and 124.6 Hz; the paper's model 6.42 m/s,
129 Hz with stress waves and 6.57 m/s, 132 Hz without. The paper gives the recorded critical
speed as that "of the first stand". The project's critical speed is the exit speed of the stand
modelled; if 5.81 m/s is the strip speed between the stands, stand 2's exit speed is
`5.81*324/216 = 8.715 m/s` [D]. Both readings are recorded; neither is asserted.

Planner's values (`v_tm2.py`, export of `8f10cbe`):

| quantity | project | reference | ratio | row verdict |
|---|---|---|---|---|
| equivalent Coulomb friction | 0.026566 | - | - | `NO_REFERENCE_VALUE` |
| separating force, forward slip, contact length | 4.1044 MN, 0.02936, 5.1498 mm | not given in the paper | - | `NO_REFERENCE_VALUE` |
| strip modulus `Q_s` | 2.00515e10 N/m | - (2.1325e10 N/m would put the mode at 124.6 Hz [D]) | 0.940 | `NO_REFERENCE_VALUE` |
| lower loaded symmetric mode | 121.878 Hz | measured 124.6 Hz | 0.978 | `WITHIN_AGREEMENT_BAND` |
| onset frequency, bite damping 0.5 | 122.303 Hz | measured 124.6 Hz (paper's model 129, 132) | 0.982 | `WITHIN_AGREEMENT_BAND` |
| critical exit speed, bite damping 0.5 | 8.1014 m/s | 8.715 m/s if 5.81 is the inter-stand speed; 5.81 m/s if it is stand 2's exit speed | 0.930 or 1.394 | `INDICATIVE_ASSUMED_INPUTS` |
| critical exit speed, no bite damping | 0.5177 m/s at 481.15 Hz (the upper mode) | - | - | `NO_REFERENCE_VALUE` |

Sensitivity to substitution 2, same run with other Coulomb coefficients: 0.02 -> 5.731 m/s,
107.77 Hz; 0.03 -> 9.261 m/s, 128.41 Hz; 0.054 (the factor misread as a coefficient) ->
16.98 m/s, 160.23 Hz. Record these three in the case note. Case verdict
`INDICATIVE_ASSUMED_INPUTS`; `input_notes` lists the three substitutions and the two readings of
the reference speed; the note says: "The frequency agrees because it is set by the stand and
the strip stiffness. The speed depends on the friction substitution (5.7 to 9.3 m/s for 0.02 to
0.03) and on a damping heuristic; without the heuristic the model is unstable at any speed in
its upper mode." Unloaded modes of this stand for the test: 13.3134 Hz and 416.684 Hz.

### Tests (`tests/test_benchmarks.py`)
`test_tm_lc7_runs_with_three_substitutions`: replaces Phase 0's
`test_tm_lc7_is_reference_only`; the eight numbers above (1e-4 relative after pinning), the row
verdicts, the three substitutions named in `input_notes`.
`test_tm_lc7_hitchcock_rejects_the_pass_with_real_rolls`: `chatter.derive_bite_response` with
210 GPa and friction 0.026566 raises (so nobody "simplifies" substitution 1 away).
`test_bt_v1_reference_caveat`: the caveat text and the two reference rows are present; the
mattress verdict is unchanged. Existing benchmark tests untouched.

### Documentation
Guide section 13 (benchmark table: TM-LC7 row with the substitutions), 11.4 (one paragraph:
what the steel case shows and does not show about the chatter screen; X31 answered), 10.2 (the
caveat on 118 in the mattress paragraph), 15 (sources E1, E6, E9 with read tags). Gap study
section 11: BT-G17 row extended; X31 `BENCHMARK_ENCODED`.

### Must not change
No solver. The five artifact pairs are byte-identical.

### Do not
- Do not edit the research note beyond cross-reference file names.
- Do not code the paper's process equations (3.1)-(3.9): the note transcribed them from a page
  image at screen resolution and flags one as doubtful.
- Do not present the speed ratio 0.93 as agreement: it rests on one reading of the reference
  speed and on the damping heuristic.

---

## Package 2 — Half-space bite: kernel, equations, Newton, cold start (BT-G1 core, BT-G5)

### Why
Gap row BT-G1: the mattress bite is far below the published loads; the published successor puts
the rolls on elastic half-spaces with a no-slip zone. Row BT-G5: cap the friction stress at
shear yield instead of rejecting. The governing set is now available in full [E1 FT, as
transcribed in the research note, sections 1.2-1.8]. This package builds the solver core; the
zone structure with zone E and the selection rule follow in package 3.

### Model (module docstring)

Conventions of `foil_bite.py`: `x` along rolling, entry at `x < 0`; `h_p(x)` [m] full PLASTIC
strip thickness (`2b` of E1); `p` [Pa] pressure, compressive positive; `sigma` [Pa] tensile;
`K = 2Y/sqrt(3)` [Pa] (= `Y_s` of E1); `tau_f` [Pa] traction on the strip, positive in the
rolling direction (`q` of E1); `R` [m] undeformed roll radius; `E_R* = E/(1 - nu^2)` [Pa] of the
roll; `E_s*` [Pa] plane-strain modulus of the strip; `t_b`, `t_f` [Pa] entry and exit tension;
`mu`; `m` shear cap factor.

1. Roll gap between two half-space rolls [E1 FT eq. (8), written for the full thickness]:
   `g(x) = g0 + x^2/R - (4/(pi*E_R*)) * Int p(x') ln|x - x'| dx'`. `g0` is a datum constant
   (E1 takes the entry point as datum; a half-space in plane strain has no rigid-body reference).
   The effect of the traction on the normal displacement is neglected, as in E1.
2. Strip thickness under load: `g(x) = h_p(x) - c_s*p(x)`, `c_s = h_ref/E_s*`,
   `h_ref = (h0 + h1)/2` `[D, SPEC18; NOT in E1, which neglects the elastic thickness change of
   the strip]`. Uniaxial elastic strain in the thickness direction (the density change cancels
   the thickness change, so strip speed follows `h_p`). `E_s*` large (1e13 Pa, the upper limit)
   is the source's assumption. Section 0.1, finding 3, says why the spring is kept and what it
   does to the load.
3. Equilibrium [E1 eq. (1)]: `d(sigma*h_p)/dx = -p*h_p' - 2*tau_f`. Yield [eq. (3a)]:
   `p + sigma = K`. Friction stress magnitude: `T(p) = min(mu*p, m*K/2)`
   [slip `q = +-mu*p`: E1 eq. (9a); cap: BT-S14 FT, BT-S3 EX, E4 EX].
4. Zones, upstream to downstream (letters of E1, Fig. 3 and Appendix 2):
   - entry contact zone `[c_i, x_i]` (E1's elastic entry zone, eq. (13), which E1 neglects):
     strip below yield, `h_p = h0`, `tau_f = +mu*p`,
     `sigma(x) = t_b - (2*mu/h0)*Int_{c_i}^{x} p`; ends where `p + sigma = K`;
   - A, plastic reduction with backward slip [eq. (15), alpha = +1]:
     `h_p*p' = K*h_p' + 2*T(p)`;
   - B, no-slip zone: `h_p = h_n` ("for the purpose of calculating the roll pressure it may be
     assumed that b = constant = b1 in the neutral zone", E1 FT); where the strip is at yield
     there, `tau_f = (h_n/2)*p'` [eq. (16)];
   - E, plastic reduction with backward slip between the no-slip zone and the pressure peak
     [eq. (15), alpha = +1]; exists only where B would need more than `T(p)`;
   - F, plastic reduction with forward slip [eq. (15), alpha = -1]:
     `h_p*p' = K*h_p' - 2*T(p)`;
   - exit contact zone `[x_e, c_x]` (E1's elastic exit zone, eq. (13), neglected there):
     `h_p = h1`, `tau_f = -mu*p`, `sigma(x) = t_f - (2*mu/h1)*Int_{x}^{c_x} p`; starts where
     `p + sigma = K`.
   Structures: `A F` (regime I, neutral point at the A/F boundary), `A B F`, `A B E F`
   (regimes II and III of E1; the split of B into its contained-plastic and elastic parts,
   zones B, C, D of E1, needs eqs (10)-(14) and does not change pressure, shape, load or torque
   [E1 FT]: not modelled). Forward slip `= h_n/h1 - 1`, with `h_n = h_p` at the E/F boundary.
5. Conditions at the free boundaries. From E1, Appendix 2: `h_p' = 0` where A meets B
   (condition 1); `(h_n/2)*p' = T(p)` at the downstream end of B (condition 2: "slip occurs at
   x_BE"); `h_p' = 0` where plastic reduction ends at exit (condition 4). In place of E1's
   condition 3 (`p = Y_s - sigma_2` at the exit end, a pressure step) the two contact zones:
   `p(c_i) = p(c_x) = 0` and yield at `x_i` and `x_e` (item 4). This is the difference from the
   printed model, and section 0.1, finding 1, is the reason for it.
6. Admissibility (checked, never assumed): `p >= 0`; `h_p` non-increasing in A, E and F ("for a
   solution to exist in regime I, db/dx <= 0 throughout the nip", E1 FT; the same holds for
   every reduction zone); in `A B F` the shear of eq. (16) within `T(p)` in every element of B;
   in `A B E F` the friction-hill bounds
   `p(x) <= p(x_a) + (2/h_n)*Int_{x_a}^{x} T` and `p(x) <= p(x_be) + (2/h_n)*Int_{x}^{x_be} T`
   at every node of B, within `0.02*K` `[D, SPEC18: necessary and sufficient for a static
   friction field within T(p) that keeps the strip at or below yield between two ends at yield;
   the tolerance covers the discretisation at the upstream end of a short no-slip zone, where
   the prototype misses the bound by up to 0.013*K]`.
7. Integrals: force per width `Int p`; traction per width (one roll)
   `mu*Int_entry_zone p + Int_A T + (h_n/2)*(p(x_be) - p(x_a)) + Int_E T - Int_F T -
   mu*Int_exit_zone p`; slip dissipation over roll speed, one interface,
   `Int |tau_f|*|1 - h_n/h_p|` over the sliding zones; plastic power over roll speed
   `h_n*K*ln(h0/h1)`; tension power `h_n*(t_f - t_b)`. Work identity
   `2*traction + tension - plastic - 2*slip = 0` (projected small-angle convention of
   `slab.py`). E1's torque formula (26) is the moment of the pressure about the roll centre; it
   is not used (the traction integral is the project's convention); the docstring says so.

NOT modelled (docstring and `limitations`): E1 eqs (4), (10)-(14): longitudinal elastic strain
of strip and roll surface, hence stress and traction inside the no-slip zone and the regime-III
zones C and D (BT-G15); friction varying through the bite; hardening, rate and temperature
inside the bite; the effect of traction on normal roll displacement; lubricant film; closed gap.

### Influence coefficients

Surface displacement of a half-space into the solid under `p(x')`:
`u(x) = -(2/(pi*E*)) * Int p(x') ln|x - x'| dx' + const`. Pressure is piecewise linear on nodes
`x_0 < ... < x_N` with `p_0 = p_N = 0`. With `G(t) = (t^2/2)*ln|t| - (3/4)*t^2` (`G'' = ln|t|`,
`G(0) = 0`) and two integrations by parts, the hat function of node `k` gives

    I_jk = Int hat_k(x') ln|x_j - x'| dx'
         = (G(x_j - x_{k-1}) - G(x_j - x_k))/(x_k - x_{k-1})
         + (G(x_j - x_{k+1}) - G(x_j - x_k))/(x_{k+1} - x_k)              [D, re-derived in SPEC18]

On a uniform grid of spacing `d`: `I_jk = d*(kappa(j - k) + ln d - 3/2)`,
`kappa(n) = ((n+1)^2 ln|n+1| - 2 n^2 ln|n| + (n-1)^2 ln|n-1|)/2` (`0*ln 0 = 0`):
`kappa(0) = 0`, `kappa(1) = 2 ln 2 = 1.3862943611`, `kappa(2) = 2.1711665768`,
`kappa(3) = 2.5891386521`. This is E1 eq. (30) with the sign corrected: as printed, (30) is the
displacement out of the roll [research note, check C1; E1 cites a contact-mechanics text for
the element, CIT]. The comment in the code names both facts. The slope of the gap at a node,
needed in package 3, uses `G'(t) = t*ln|t| - t` in the same two difference quotients.

Self-check against Hertz line contact: `p = p0*sqrt(1 - x^2/a^2)` on `[-a, a]` with
`p0 = a*E*/(2R)` must give `u(0) - u(x) = x^2/(2R)` (follows from
`PV Int_{-a}^{a} sqrt(1 - s^2/a^2)/(x - s) ds = pi*x/a`). Planner, nodal Hertz pressure on a
uniform grid (`E*` 230 GPa, `R` 0.089 m, `a` 1 mm), error divided by `a^2/(2R)`:

| elements | all nodes | nodes with abs(x) <= 0.8a | trapezoid load error |
|---|---|---|---|
| 20 | 1.243e-2 | 6.32e-3 | -1.18e-2 |
| 40 | 5.89e-3 | 2.18e-3 | -4.18e-3 |
| 80 | 2.60e-3 | 7.63e-4 | -1.48e-3 |
| 160 | 1.10e-3 | 2.69e-4 | -5.23e-4 |

### Numerical method (copy `s23/hs3.py`, `hs_bite.py` (LU, influence), `hs_solve2.py`; this text is the specification)

**Grid.** Six zones with `zones = (n1, n2, n3, nE, n4, n5)` elements, default
`DEFAULT_ZONES = (3, 16, 24, 8, 16, 3)`, each zone uniform between its two boundaries. `A B F`
uses `nE = 0`; `A F` uses `(n1, n2 + n3//2, 0, 0, n4 + n3//2, n5)`. Node indices
`i1 = n1`, `i2 = i1 + n2`, `i3 = i2 + n3`, `iE = i3 + nE`, `i4 = iE + n4`, `N = i4 + n5`.

**Scaling.** `L = sqrt(R*(h0 - h1))`; `X = x/L`, `P = p/K`, `H = h_p/h1`;
`a1 = L^2/(R*h1)`, `a2 = 4*K*L/(pi*E_R**h1)`, `beta = L/h1`, `cs = (h0 + h1)*K/(2*E_s**h1)`.
`H_j = G0 + a1*X_j^2 + Sum_k A_jk*P_k`, `A_jk = -a2*I_jk + cs*delta_jk` with `I` computed on `X`
(the `ln L` shift is a multiple of the load and is absorbed in `G0`).

**Unknowns**: `P_1..P_{N-1}`; the free boundaries over `L`: `(c_i, x_i, x_n, x_e, c_x)` for
`A F`, `(c_i, x_i, x_a, x_b, x_e, c_x)` for `A B F`, `(c_i, x_i, x_a, x_be, x_ef, x_e, c_x)` for
`A B E F`; `G0`; `H_n` (structures with B). Totals `N + 5`, `N + 7`, `N + 8`.

**Equations**, in this order (`dX_j = X_{j+1} - X_j`, `P_m = (P_j + P_{j+1})/2`,
`Tm = min(mu*P_m, m/2)`):

| block | rows | equation |
|---|---|---|
| E1 | nodes `0..i1` | `H_j - h0/h1 = 0` |
| E2 | 1 | `P_{i1} + t_b/K - (2*mu*L/h0)*trapz(P, entry zone) - 1 = 0` |
| A | elements `i1..i2-1` | `((H_j + H_{j+1})/2)*(P_{j+1} - P_j) - (H_{j+1} - H_j) - 2*beta*Tm*dX_j = 0` |
| S1 (with B) | 1 | `3*H_{i2} - 4*H_{i2-1} + H_{i2-2} = 0` (zero slope of `h_p` where A ends) |
| B (with B) | nodes `i2..i3` | `H_j - H_n = 0` |
| C2 (with E) | 1 | `H_n*(P_{i3} - P_{i3-1}) - 2*beta*Tm*dX_{i3-1} = 0` (eq. (16) at the friction limit over the last element of B) |
| E (with E) | elements `i3..iE-1` | as block A |
| F | elements `iE..i4-1` | `((H_j + H_{j+1})/2)*(P_{j+1} - P_j) - (H_{j+1} - H_j) + 2*beta*Tm*dX_j = 0` |
| S2 | 1 | `3*H_{i4} - 4*H_{i4-1} + H_{i4-2} = 0` (zero slope where plastic reduction ends) |
| E6 | nodes `i4..N` | `H_j - 1 = 0` |
| E7 | 1 | `P_{i4} + t_f/K - (2*mu*L/h1)*trapz(P, exit zone) - 1 = 0` |

A test asserts that the row count equals the unknown count for the three structures. The
element form of blocks A, E, F is the trapezoid rule on eq. (15); E1's own element formula (20)
is misprinted (research note, check C2) and is not used.

**Jacobian.** Analytic in the pressures, `G0` and `H_n` (`dH_j/dP_k = A_jk`; the cap makes
`dTm/dP_m` equal to `mu` or 0). Central differences with step `1e-7` in the scaled boundary
positions for the boundary columns (each needs the influence matrix rebuilt). Dense LU with
partial pivoting in plain Python (row operations by list comprehension, as the prototype).

**Newton.** Step `du = -J^{-1} R`; backtracking: halve the step until the trial has strictly
increasing boundaries (by at least `1e-9`) and `max|R|` falls below `(1 - 1e-4*s)` times the
current value; give up below `s = 1e-4` (`ValueError`). Converged at `max|R| < 1e-11`; a run that
ends at the iteration limit (40 unless stated) with `max|R| < 1e-8` is accepted and recorded in
`convergence`; otherwise `ValueError`.

**Cold start: homotopy from the mattress bite** (gives an `A F` or `A B F` candidate).
1. `m = foil_bite.solve_mattress_bite(...)` with the same inputs. Structure from `m['regime']`.
   Boundaries from `contact_start_m, plastic_entry_m, flat_zone_start_m, flat_zone_end_m,
   plastic_exit_m, contact_end_m` (conventional: one neutral point), pressures by linear
   interpolation of `m['profile']`, `G0 = unloaded_gap_m/h1`, `H_n = neutral_thickness_m/h1`.
2. Kernel blend `A(lam) = lam*(-a2*I + cs*1) + (1 - lam)*w*1`, `w = 2*K/(K_p*h1)`,
   `K_p = m['foundation_modulus_pa_m']`. At `lam = 0` the equations are the mattress model on
   this grid (planner: 3 Newton iterations to `1e-15`; force 1011331.7 N/m against the mattress
   solver's 1018841.9, 0.74 % apart, forward slip 0.17064 against 0.16978).
3. March `lam` from 0 to 1: first step 0.25, after a success multiply by 1.5 up to 0.5, after a
   failure halve; fail below `1e-3`. A step is accepted only if Newton converged AND
   `min(P_1..P_{N-1}) >= 0` AND `H` does not increase by more than `1e-7` over any element of A
   or F. The last condition is essential: the slope row S1 has a second root with `h_p` rising
   into `x_a` (planner, `cap3.py`: 50 -> 25 um, `K` 150 MPa, R 135 mm; the spurious root gave a
   39 um no-slip zone, the monotone one 344 um).
4. Structure switch during the march (at most 4): `A F` -> `A B F` when an accepted `A F` step
   has `H_{i2} - H_{i2-1} > 0`: halve the step down to 0.02 first, then convert with `x_a` = the
   last node of A where `H` still falls, `x_b = x_n + (x_n - x_a)/2`, minimum zone width 2 % of
   the plastic length, `H_n` = the smallest `H` between them, pressures interpolated; Newton
   with up to 40 iterations. `A B F` -> `A F` when the no-slip length is below 1 % of
   `x_e - x_i` on an accepted step, or when a step fails while it is below 8 %:
   `x_n = (x_a + x_b)/2`.
5. The candidate at `lam = 1` is accepted in THIS package when it is `A F` and `h_p` is
   non-increasing over every element of A and F, or `A B F` with item 6 of the model satisfied.
   Otherwise `ValueError('zone structure of the cold start is not admissible ...')` with the
   measure that failed; package 3 replaces this by the selection rule.
6. Any failure: `ValueError` with the stage and the reason. Never a number from a failed solve.

### Public API (`physicroll/halfspace_bite.py`)

```python
STATUS = 'UNVALIDATED_REDUCED_HALF_SPACE_FOIL_BITE'
DEFAULT_ZONES = (3, 16, 24, 8, 16, 3)
ALUMINIUM_PLANE_STRAIN_MODULUS_PA = 70e9/(1 - 0.33**2)   # strip_shape.ALUMINIUM_E_PA / _NU [M there]
def influence_matrix(x) -> list            # I[j][k-1] for k = 1..N-1, any increasing x
def influence_slope_matrix(x) -> list      # dI_jk/dx_j, same layout
def hertz_self_check(elements=80) -> dict  # the table above for one grid
def solve_half_space_bite(entry_thickness_m, exit_thickness_m, width_m, work_roll_radius_m,
                          mean_flow_stress_pa, friction_coefficient, entry_tension_pa,
                          exit_tension_pa, *, roll_youngs_modulus_pa=210e9, roll_poisson_ratio=0.3,
                          strip_plane_strain_modulus_pa=ALUMINIUM_PLANE_STRAIN_MODULUS_PA,
                          shear_cap_factor=1.0, zones=DEFAULT_ZONES, warm_start=None,
                          with_solution=False)
# returns the result dict, or (dict, HalfSpaceSolution) when with_solution is True
class HalfSpaceSolution     # internal state for warm starts and package 4; not JSON, never in a result
```
Input checks: `foil_bite._check_inputs` domain (same messages with "half-space bite" in place of
"mattress bite"); `strip_plane_strain_modulus_pa` in `[1e9, 1e13]`; `shear_cap_factor` in
`(0, 1]`; `zones` six ints, `n1, n5 >= 2`, `n2, n4 >= 4`, `n3 >= 4`, `nE >= 4`, sum `<= 400`.
`warm_start` is accepted and ignored until package 3.

Result keys (same names and meanings as `solve_mattress_bite` wherever both exist): `status`,
`model` (`'half_space_roll_rigid_plastic_slab_reduced'`), `regime` (`'conventional'` for `A F`,
`'foil'` otherwise), `zone_structure` (`'A F'`, `'A B F'`, `'A B E F'`), the eight echoed
inputs, `roll_youngs_modulus_pa`, `roll_poisson_ratio`, `strip_plane_strain_modulus_pa`,
`shear_cap_factor`, `plane_strain_strength_pa`, `separating_force_n`, `force_per_width_n_m`,
`torque_per_work_roll_nm`, `forward_slip_fraction`, `backward_slip_fraction`,
`neutral_thickness_m`, `contact_length_m`, `plastic_contact_length_m`, `entry_zone_length_m`,
`exit_zone_length_m`, `contact_start_m`, `contact_end_m`, `plastic_entry_m`, `plastic_exit_m`,
`flat_zone_start_m`, `flat_zone_end_m`, `flat_zone_length_m`, `flat_zone_share`,
`backward_slip_zone_length_m` (zone E; 0.0 without), `neutral_point_m`, `peak_pressure_position_m`,
`contact_radius_ratio` (`L_contact^2/(R*draft)`), `max_pressure_pa`, `mean_pressure_pa`,
`plastic_work_power_over_roll_speed_n`, `slip_dissipation_both_interfaces_over_roll_speed_n`,
`net_tension_power_over_roll_speed_n`, `max_coulomb_shear_over_yield_shear`
(`mu*p_max/(K/2)`, may exceed 1 here), `shear_cap_active`, `no_slip_zone`
(`{'eq16_shear_over_limit_max', 'friction_hill_margin_min_over_k', 'net_shear_over_limit',
'note'}`; `None` for `A F`), `structure_selection` (list of `[step, outcome]` pairs; one entry
in this package), `convergence` (`zones`, `elements`, `newton_iterations`, `residual_max`,
`homotopy_steps`, `structure_switches`, `cold_start`, `mechanical_work_residual_relative`; no
wall time: results must be reproducible), `profile` (`x_m`, `pressure_pa`, `thickness_m`, `zone`
per node; zone words `entry_contact_zone`, `entry_slip`, `no_slip_flat`, `backward_slip`,
`exit_slip`, `exit_contact_zone`), `basis` (one tagged sentence per numbered item of the model),
`flags`, `limitations`. Absent on purpose: `foundation_modulus_pa_m`, `unloaded_gap_m`,
`limiting_thickness_m`, `stone_minimum_thickness_m`.

Flags: `REDUCED_HALF_SPACE_FOIL_MODEL` (always), `HALF_SPACE_REGIME_FOIL` /
`HALF_SPACE_REGIME_CONVENTIONAL`, `SHEAR_CAP_ACTIVE`,
`STRIP_THICKNESS_SPRING_NOT_IN_PUBLISHED_MODEL` (always, unless the modulus is 1e13),
`FORWARD_SLIP_LARGE_CONSTANT_FRICTION_NO_SLIP_ZONE_MODEL` (above 0.15; the name SPEC17 package 2
introduces), `LIGHT_REDUCTION_ELASTIC_STRIP_ZONES_NOT_MODELLED` (reduction below 0.10: the
elastic zones are short only "for practical reductions (r > 10 per cent)" [E1 FT]),
`PEAK_PRESSURE_ABOVE_16_PLANE_STRAIN_YIELD` (the published solutions peak at about 16 `Y_s`
[E1 FT, Fig. 1, read by eye]), `THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN` (exit below 0.3 mm, as
today), and the two domain flags of `foil_bite._domain_flags`. Rejections (`ValueError`):
inputs; inadmissible candidate (step 5); work residual above `1e-3`; solver failure.
`limitations` always holds: "The load depends on how the bite ends are closed. This model keeps
the entry and exit contact zones; the published model ends with a pressure step and its
published loads depend on an unstated end length (benchmark BT-V1-HS)." and the sentence on the
thickness spring with its effect on the published case (+4.6 %).

### Worked numbers (`s23/sel_final.log`, `bench.py`; default zones; R 89 mm, `Y_s` 230 MPa, `E_R*` 230 GPa, `E_s*` 80 GPa, mu 0.03 unless stated)

| case | structure | `W_bar` | force N/m | forward slip | contact length mm | `p_max/K` |
|---|---|---|---|---|---|---|
| 20 -> 15 um (the published case) | A B F (eq. (16) shear at most 0.955 of the limit) | 92.936 | 1902400.8 | 0.203668 | 2.03843 | 7.3315 |
| same, every zone count doubled | A B F candidate (eq. (16) shear 1.31: rejected in this package) | 93.299 | - | 0.2033 | 2.042 | 7.366 |
| 140 -> 70 um | A F | 46.820 | 958396 | 0.0709 | 3.0580 | 2.197 |
| 60 -> 30 um | A F | 68.034 | 1392660 | 0.2180 | 2.4456 | 5.747 |
| 30 -> 15 um | A B F | 207.127 | 4239890 | 0.4769 | 3.1557 | 11.295 |
| 20 -> 10 um | A B F | 408.602 | 8364090 | 0.5091 | 4.2167 | 11.864 |
| BT-V2: 73 -> 31.39 um, mu 0.026, tensions 0.107 / 0.132 `Y_s`, R 89 mm | A F | 42.800 | 876108 | 0.1295 | 2.4897 | 3.104 |
| same, R 135 mm | A F | 67.125 | 2084240 | 0.3103 | 3.6184 | 6.475 |
| demo ALT2: 25 -> 12 um, R 135 mm, Y 185 MPa, tensions as the scenario, `E` 210 GPa, `E_s*` 78.55 GPa | A B F | - | 10128500 | 0.5527 | 5.7101 | 11.859 |

The published case: work residual 4.5e-6; neutral thickness 18.0550 um; boundaries
-1.15102 / -1.14379 / -0.76082 / 0.34941 / 0.80957 / 0.88742 mm; 22 Newton iterations over the
march. Cases that this package must REJECT with the step-5 message (package 3 solves them):
the published case with `E_s*` = 1e13 (eq. (16) shear 1.45 of the limit); 30 -> 18 um of the
battery-foil demo (1.03); 50 -> 30 um of the same demo (2.94).

### Tests (`tests/test_halfspace_bite.py`)
- `test_uniform_grid_closed_form`: the three `kappa` values to `1e-10`; `I_jk` to `1e-12`.
- `test_hat_integral_against_quadrature`: nodes `0.03, 0.1, 0.22`, field point 0:
  `-0.2099798413` (`1e-8`); a midpoint-rule quadrature of the test agrees to `1e-6`; the slope
  matrix against a central difference of `influence_matrix` (`1e-6`).
- `test_hertz_line_contact_recovered`: 80 elements, all nodes `<= 3.0e-3`, inner nodes `<= 1.0e-3`
  of `a^2/(2R)`; 160 elements `<= 1.3e-3` and `<= 3.5e-4`; the error falls with refinement.
- `test_equation_count`: three structures.
- `test_winkler_limit_reproduces_the_mattress_solver`: `lam = 0` on the published case: Newton
  in at most 5 iterations, force within 1.0 % and forward slip within 0.002 of
  `solve_mattress_bite`.
- `test_published_case_values` (first row); `test_sheet_and_foil_rows` (rows 3 to 9).
- `test_sheet_gauge_close_to_the_mattress`: 300 -> 210 um, R 0.2 m, Y 270 MPa, mu 0.03,
  tensions as the lengthwise demo case pass: `A F`, force 1996310 N/m, within 8 % of
  `solve_mattress_bite` (1890500 N/m).
- `test_work_identity` (residual below `1e-4` on five cases); `test_no_slip_zone_fields`;
  `test_inadmissible_candidates_are_rejected` (the three named cases).
- `test_strip_modulus_trend`: 40 GPa gives 96.751, 160 GPa 90.933 on the published case
  (`A B F` candidates; assert on the force of the candidate through `with_solution` if the
  160 GPa case is rejected by step 5: its eq. (16) shear is 1.15).
- `test_rejections`; `test_json_safe`; `test_no_wall_time_in_result`.
Module time: planner about 12 s of solves.

### Documentation
Module docstring = the model with its E1 equation numbers, the three misprints of E1 named, the
difference at the bite ends and finding 1 of section 0.1. Guide: new section 10.3 "Reduced
half-space model (`halfspace_bite.py`)": model, what is left out, why the ends are closed by
contact zones. Section 13 row; section 14 limitations; section 15: E1 with its read tag. Gap
study section 11: rows follow in package 4.

### Must not change
No existing module is touched. The five artifact pairs are byte-identical.

### Do not
- Do not tune `E_s*`, zone counts, the tolerance `0.02*K` or the conditions towards 118 or any
  other load.
- Do not add eqs (10)-(14), zones C and D or stress inside the no-slip zone.
- Do not replace the contact end zones by a pressure step (that is the benchmark mode of
  package 3, not the solver).
- Do not replace Newton by an under-relaxed shape iteration.

---

## Package 3 — Half-space bite: zone E, structure selection, friction march, warm start (BT-G1, BT-G5)

### Why
Package 2 rejects every pass whose no-slip zone would need more than the friction limit at its
downstream end, and every pass at the regime boundary. The published structure has a zone for
exactly that: E, plastic reduction with backward slip between the no-slip zone and the pressure
peak [E1 FT, section 2, Appendix 2 and Appendix 3]. The planner's check (section 0.1) shows
that it changes the load by under 0.1 % and makes the passage between the regimes continuous.
This package also adds the path for friction where the mattress bite (the cold start) rejects,
and the benchmark mode that reproduces the printed end conditions.

### Design

**1. Structure selection** `[D, SPEC18; zone E and its conditions: E1 FT]`, applied to the
`lam = 1` candidate of package 2, after every warm start and after every friction step. Record
each step in `structure_selection`.

1. Candidate `A F`: accept if `h_p` is non-increasing over every element of A and F
   (tolerance `1e-7` in `H`). (The march's own test looks at the last element of A only; near
   the boundary the profile can thicken further upstream and thin again before the neutral
   point.)
2. Candidate `A B F`: accept if `p >= 0`, the reduction zones are monotone and the eq. (16)
   shear is within the limit in every element of B (tolerance `1e-6`): zone E then has no length.
3. Otherwise insert zone E: `x_be` = the upstream node of the first element of B, not among its
   first two, whose eq. (16) shear exceeds the limit; `x_ef` = the old `x_b`; pressures
   interpolated; solve `A B E F` (Newton limit 60). Accept if converged, `p >= 0`, A, E and F
   monotone, and the friction-hill bounds of B hold within `0.02*K`.
4. Otherwise convert to `A F` (`x_n` = middle of the old B and E), solve, accept by rule 1.
5. Otherwise build `A B E F` from that `A F` solution: `x_a` = first node of the stretch of A
   over which `H` rises, `x_be` = its last node (half way to `x_n` if the stretch reaches
   `x_n`), `x_ef = x_n`, `H_n` = the smallest `H` in the stretch; solve; accept as in rule 3.
6. Otherwise `ValueError('no admissible zone structure: ...')` with the recorded steps.

**2. Cold start where the mattress bite rejects, and friction marching.** When
`solve_mattress_bite` rejects the pass, or the march of package 2 fails: cold start at a
friction of `min(mu, 0.03)`, then `0.02`, then `0.01` (the first that works), then march in
friction to the target with warm Newton steps in the current structure (first step `0.002`,
grow by 1.3 up to `0.004`, halve on failure or on an inadmissible result, fail below `1e-6`),
with the `A F` -> `A B F` switch of package 2 during the march and the selection rule at the
end. Flag `COLD_START_BY_FRICTION_CONTINUATION`.

**3. Warm start.** `solve_half_space_bite(..., warm_start=solution)` converts the given
solution to the scaling of the new inputs through physical units (pressures, boundaries, `g0`,
`h_n`), runs Newton (limit 25) in the same structure, applies the selection rule, and falls back
to the cold start on any failure.

**4. Benchmark mode: the printed end conditions** (private; used only by `benchmarks.py`):
`_printed_end_condition_solution(..., end_length_m, zones)`: strip rigid in thickness
(`cs = 0`); structure `A B F`; instead of the two contact zones ONE linear pressure element of
the prescribed length outside each end (so the boundaries `c_i = x_i - l`, `c_x = x_e + l` are
not unknowns); rows E1, E2, E6, E7 are replaced by `H(x_i) = h0/h1`, `P(x_i) = 1 - t_b/K`,
`H(x_e) = 1`, `P(x_e) = 1 - t_f/K` (E1's boundary conditions with the elastic end zones
neglected); rows S1 and S2 use the ANALYTIC slope of the gap at the node,
`dH/dX = 2*a1*X_j - a2*Sum_k (dI_jk/dX_j)*P_k`. Unknowns `N + 5`, equations `N + 5` (test).
Start from the converged contact-zone solution at `E_s*` = 1e13 and step the end length down
through 40, 30, 21, 15, 10, 7, 5, 3.5, 2.5 um with warm starts. No admissibility test is
applied (these solutions thicken before the exit; that is one of the things the mode shows);
the result carries `max_thickening_over_exit_gauge`.

### Worked numbers (`s23/sel_final.log`, `v_tol.py`, `v_ramp.py`, `v_cap_tm.py`; R 89 mm, `Y_s` 230 MPa, `E_R*` 230 GPa, `E_s*` 80 GPa, mu 0.03, no tensions, unless stated)

| case | selection steps | structure | `W_bar` | forward slip | contact length mm | no-slip / zone E um |
|---|---|---|---|---|---|---|
| 20 -> 15 um, `E_s*` 80 GPa | 2 | A B F | 92.936 | 0.2037 | 2.0384 | 1110 / 0 |
| 20 -> 15 um, `E_s*` 1e13 | 2 fails, 3 | A B E F | 88.859 (A B F candidate 88.937) | 0.2047 | 1.9614 | 1012 / 14 |
| r 0.5: 56 um | 1 | A F | 75.676 | 0.2594 | 2.4603 | - |
| r 0.5: 54 um | 2 fails, 3 fails, 4 | A F | 81.204 (A B F candidate 82.440) | 0.2891 | - | - |
| r 0.5: 52 um | 2 fails, 3 | A B E F | 87.858 | 0.3285 | 2.5079 | 179 / 119 |
| r 0.5: 48 um | 2 fails, 3 | A B E F | 100.186 | 0.3652 | 2.5585 | 419 / 73 |
| r 0.5: 44 um | 2 fails, 3 | A B E F | 114.736 | 0.3965 | 2.6274 | 652 / 49 |
| r 0.25: 36 um | 1 | A F | 40.192 | 0.1166 | 1.5987 | - |
| r 0.25: 34 um | 2 fails, 3 fails, 4 | A F | 43.979 | 0.1363 | - | - |
| r 0.25: 32 um | 2 fails, 3 | A B E F | 48.351 | 0.1567 | 1.6509 | 192 / 68 |
| r 0.25: 28 um | 2 fails, 3 | A B E F | 57.997 | 0.1769 | 1.7243 | 449 / 34 |
| r 0.10: 30 um | 1 | A F | 21.862 | 0.0425 | 1.1079 | - |
| r 0.10: 28 um | 2 fails, 3 fails, 4 | A F | 23.711 | 0.0506 | - | - |
| r 0.10: 26 um | 2 fails, 3 | A B E F | 25.919 | 0.0584 | 1.1501 | 153 / 40 |
| r 0.10: 22 um | 2 fails, 3 | A B E F | 31.507 | 0.0665 | 1.2200 | 368 / 14 |

So the no-slip zone appears between 54 and 52 um at r = 0.5 (eq. 29 of E1: 51.2), between 34
and 32 um at r = 0.25 (36.2), between 28 and 26 um at r = 0.10 (22.9), and the load is
continuous across the boundary (75.7, 81.2, 87.9, ..., 100.2, 114.7 from 56 to 44 um).
The 52 um row misses the upstream friction-hill bound by `0.0095*K`, inside the tolerance.

Battery-foil demo schedule (R 135 mm, `E` 210 GPa, `E_s*` 78.55 GPa, friction 0.03, tensions and
flow stress of the scenario):

| pass | structure | force N/m | forward slip | contact length mm | no-slip / zone E um |
|---|---|---|---|---|---|
| S1 260 -> 135 um | A F | 748924 | 0.0362 | 4.6416 | - |
| S2 135 -> 85 | A F | 653874 | 0.0589 | 3.1410 | - |
| S3 85 -> 50 | A F | 803151 | 0.1006 | 2.8178 | - |
| F1 50 -> 30 (= case pass) | A F (rules 2 and 3 fail, 4 accepts) | 1369950 | 0.2374 | 2.6539 | - |
| ALT1 50 -> 25 | A B E F | 2658150 | 0.4212 | 3.4062 | 943 / 58 |
| F2 30 -> 18 | A B E F | 3243880 | 0.3678 | 3.3457 | 1800 / 2 |
| ALT2 25 -> 12 | A B F | 10128500 | 0.5527 | 5.7101 | 4441 / 0 |

The six sheet passes of the lengthwise demo are all `A F` (forces 3513580, 3431780, 3133380,
2643920, 2291870, 1996310 N/m for P1 to P6).

Shear cap (50 -> 25 um, `K` 150 MPa, tensions 20 MPa, R 135 mm, `E` 210 GPa: the pass of E4's
Table I [EX]; `E_s*` 80 GPa here): friction 0.03: `A B E F`, force 1517220 N/m, slip 0.3583, `p_max/K` 9.942
(no-slip 232 um, zone E 131 um). The mattress solver rejects this pass at 0.05 and 0.06.
Marched in friction: 0.05 -> `A B F`, 7718180 N/m, slip 0.5565, `p_max/K` 19.18, cap active;
0.10 -> `A B F`, 48652300 N/m, slip 0.6925, `p_max/K` 34.39, contact length 12.15 mm: 32 times
the load at 0.03. With `shear_cap_factor` 0.5: 6313520 N/m (`A B E F`) at 0.05 and
18534400 N/m at 0.10.

Printed end conditions on the published case (benchmark mode, zones `(1, 16, 24, -, 16, 1)`):
the `W_bar`, contact length, peak and slip of the nine ramp rows in section 0.1; thickening
before the exit from 0.00026 (40 um) through 0.00118 (21 um), 0.00252 (10 um), 0.00401 (5 um)
to 0.00568 (2.5 um) of the exit gauge.

### Budget
Cold solve with selection: at most 3.5 s on any case of the tables, 1.2 s on average over the
15 demo passes (planner: 0.3-1.5 s, 1.8 s for 56 um, 2.8 s for F1, where rule 3 runs to its
iteration limit before rule 4 accepts). The benchmark family: under 8 s.

### Tests (`tests/test_halfspace_bite_cases.py`)
- `test_selection_table` (the first table: structure, steps, `W_bar` to `1e-4` after pinning);
  `test_demo_schedules` (second table and the lengthwise forces).
- `test_zone_e_changes_the_load_by_less_than_0_3_percent`: rigid-strip published case, `A B E F`
  against its `A B F` candidate (planner -0.09 %); eq. (16) shear at most `1 + 1e-6` in B.
- `test_regime_follows_the_published_boundary`: the six bracketing gauges; eq. 29 values 51.2,
  36.2, 22.9 um in the docstring. `test_load_is_continuous_across_the_boundary`: the r = 0.5
  series 56, 54, 52, 48 um rises monotonically with no step above 9 %.
- `test_selection_is_path_independent`: the 52 um case from a cold start and from a warm start
  out of the 48 um solution (force within `1e-6` relative). Not run by the planner: if the two
  differ, report both forces and structures instead of loosening the test.
- `test_shear_cap_march` (the five numbers; mark as the slowest test, about 4 s);
  `test_mattress_rejects_where_this_solver_marches`.
- `test_printed_end_conditions_family`: 21, 10 and 5 um to `1e-3` after pinning; the load rises
  as the end shortens; the solutions thicken before the exit; equation count.
- `test_warm_start_equals_cold_start` (`1e-8` relative); `test_no_admissible_structure_message`
  (force rule 6 by a monkeypatched tolerance).
- Timing guard: the 15 demo passes cold in under 30 s in total (planner about 12 s).

### Documentation
Guide 10.3: zone structure with E1's letters, the selection rule in words, the regime table
against eq. 29, the shear-cap example with X24 repeated (a nominal 0.10 is not the published
case), the printed-end family table and what it means for "118". Section 13, 14. No README yet.

### Must not change
No existing module besides `halfspace_bite.py` and its tests. Artifacts byte-identical.

### Do not
- Do not accept a structure outside the six rules "because it converged".
- Do not use the benchmark mode in any solve of the engine.
- Do not widen the tolerance `0.02*K`; if a case needs more, report it.

---

## Package 4 — Half-space bite: sensitivities, engine integration, benchmarks (BT-G1, BT-G5, BT-G17)

### Why
Everything downstream takes a `chatter.BiteResponse`: eight sensitivities, contact length, force,
slip. The half-space bite must sit behind the same interface, selectable, with the mattress kept.
Phase 2 needs two more derivatives per pass (friction, flow stress), which the present code gets
by extra bite derivations. The benchmark rows of the published foil case are written here.

### Design

**1. Sensitivities** (`halfspace_bite.py`):
```python
def derive_bite_response_half_space(bite_pass, *, roll_youngs_modulus_pa=210e9,
        roll_poisson_ratio=0.3, strip_plane_strain_modulus_pa=ALUMINIUM_PLANE_STRAIN_MODULUS_PA,
        shear_cap_factor=1.0, zones=DEFAULT_ZONES, warm_start=None, with_state=False)
# -> BiteResponse, or (BiteResponse, state dict) when with_state is True
```
Recipe of `derive_bite_response_mattress` with one change of method: central differences with
steps `1e-3*h1`, `1e-3*h0`, `1e-3*Y` (each tension), and in addition `1e-3*mu` and `1e-3*Y`
(flow stress); one-sided at zero tension with `ONE_SIDED_TENSION_DIFFERENCE_AT_ZERO_TENSION`.
Each perturbed solution is found by CHORD iterations in the nominal zone structure with the LU
factors of the nominal Jacobian (`u <- u - J0^{-1} R(u)`, start = the nominal solution converted
through physical units, tolerance `1e-10`, limit 40; on failure one full Newton solve from the
same start; on failure `ValueError`). Repeat with half steps; a change above 2 % in any of the
twelve adds `SENSITIVITY_STEP_NOT_CONVERGED`; half-step values are returned. A perturbed
solution that is not admissible in the nominal structure (rules 1 to 3 of package 3) adds
`REGIME_CHANGE_WITHIN_FINITE_DIFFERENCE_STENCIL`; its value is still used (the structures join
continuously, package 3).
`BiteResponse(source='supplied', flags=('DERIVED_BY_HALF_SPACE_FOIL_MODEL',
'REDUCED_HALF_SPACE_FOIL_MODEL', 'HALF_SPACE_REGIME_...', ...))`; `contact_radius_ratio`
clamped to 1 with `CONTACT_RADIUS_RATIO_CLAMPED_TO_ONE` as the mattress derivation does.
`state` = `{'solution': HalfSpaceSolution, 'result': the solve dict without its profile,
'extra': {'dforce_dfriction_n', 'dforce_dflow_stress_m2', 'dslip_dfriction',
'dslip_dflow_stress_per_pa', 'dcontact_length_dexit_thickness', 'dcontact_length_dfriction_m',
'torque_per_work_roll_nm', 'slip_dissipation_both_interfaces_over_roll_speed_n',
'load_exponent_in_friction', 'load_exponent_in_flow_stress', 'zone_structure'}}`.

Planner (`s23/sel_final.log`; all per unit width; chord against full Newton identical to 7
digits on the cases tried):

| case | structure | `F_h` Pa | `F_hin` Pa | `F_se` m | `F_sx` m | `dF/dmu` N/m | `dF/dK` m | `f_h` 1/m | load exponent in mu |
|---|---|---|---|---|---|---|---|---|---|
| published case, `E_s*` 80 GPa | A B F | -5.5756e11 | 2.7774e11 | -6.4418e-3 | -1.4705e-2 | 1.5605e8 | 2.0962e-2 | -5.0653e4 | 2.461 |
| published case, `E_s*` 1e13 | A B E F | -5.4317e11 | 2.7202e11 | -6.1349e-3 | -1.3963e-2 | 1.4885e8 | 1.9945e-2 | -5.1218e4 | 2.455 |
| 140 -> 70 um | A F | -1.0589e10 | 5.0365e9 | -4.5143e-3 | -2.1458e-3 | 2.6908e7 | 5.2683e-3 | -1.4466e3 | 0.842 |

(`dF/dK` is with respect to the plane-strain strength; multiply by `2/sqrt(3)` for the uniaxial
flow stress.) Battery-foil demo schedule, material modulus 70 GPa (`E_s*` 78.55 GPa), supplied
friction 0.03; mattress values are plain `solve_mattress_bite` calls with the same inputs:

| pass | structure | force per width N/m, half-space (mattress) | forward slip (mattress) | contact length mm (mattress) | `Q = -dF'/dh` Pa | `N_x' = -dF'/dt_f` m | load exponent in mu |
|---|---|---|---|---|---|---|---|
| S1 260 -> 135 um | A F | 7.4892e5 (7.519e5) | 0.036 (0.029) | 4.642 (4.783) | 2.5692e9 | 1.8046e-3 | 0.675 |
| S2 135 -> 85 | A F | 6.5387e5 (6.409e5) | 0.059 (0.052) | 3.141 (3.205) | 9.0239e9 | 2.3447e-3 | 0.705 |
| S3 85 -> 50 | A F | 8.0315e5 (7.560e5) | 0.101 (0.100) | 2.818 (2.829) | 2.5761e10 | 3.9077e-3 | 1.258 |
| F1 50 -> 30 = case pass | A F | 1.36995e6 (9.586e5) | 0.237 (0.190) | 2.654 (2.384) | 1.9322e11 | 1.6777e-2 | 3.741 |
| ALT1 50 -> 25 | A B E F | 2.65815e6 (1.4877e6) | 0.421 (0.315) | 3.406 (2.759) | 3.1795e11 | 2.1410e-2 | 3.044 |
| F2 30 -> 18 | A B E F | 3.24388e6 (1.5360e6) | 0.368 (0.308) | 3.346 (2.317) | 6.4664e11 | 2.9182e-2 | 2.861 |
| ALT2 25 -> 12 | A B F | 1.01285e7 (6.188e6) | 0.553 (0.422) | 5.710 (4.422) | 2.7362e12 | 8.9049e-2 | 3.278 |

Sensitivities cost 0.07-0.15 s per pass in the prototype. On the last sheet pass of the
lengthwise demo (300 -> 210 um) the half-space force is 5.6 % above the mattress force
(package 2).

**2. Engine** (`band_diagnosis.py`, `band_process.py`, `band_width.py`, `band_report.py`,
`band_plain.py`):
- `BITE_MODELS = ('hitchcock', 'mattress', 'auto', 'half_space', 'auto_half_space')`.
  `'half_space'`: every pass by the half-space model. `'auto_half_space'`: Hitchcock, and the
  half-space model where Hitchcock rejects (as `'auto'` does with the mattress), with
  `cache.fallbacks` filled the same way.
- `band_process.HALF_SPACE_FLAG = 'BITE_FROM_REDUCED_HALF_SPACE_MODEL'`,
  `is_half_space(bite)`, `is_foil_model(bite)` (either foil model). `_BiteCache._half_space`
  mirrors `_mattress`; `_BiteCache.get` gains the model `'half_space'`; the cache keeps
  `self.states[key]` (the state dict above) and warm-starts a new half-space derivation from the
  stored solution with the smallest distance `|ln h0 ratio| + |ln h1 ratio| + |ln Y ratio| +
  |ln mu ratio| + (|dt_b| + |dt_f|)/Y` when that distance is below 0.25.
- `perturbed_bite_model`: `'half_space'` when the operating bite is a half-space bite or the
  option is `'half_space'`; otherwise as today. `_ModelCache` unchanged.
- Go through every site that tests the mattress flag and give each a half-space branch; the
  list at `8f10cbe` (find them by `is_mattress`, `MATTRESS_FLAG`, `experimental_mattress`):
  `band_process.bite_sensitivity` (`bite_model` word `'reduced_half_space'`),
  `friction_single` and `friction_fixed_point` (`bite_source`), `friction_power_per_width`
  (half-space branch: `state['extra']['slip_dissipation_...']` through a new optional argument
  `state`, or a `solve_half_space_bite` call when no state is passed; basis text "reduced
  half-space slip dissipation x roll surface speed / width"), `heating_row`
  (`FRICTION_POWER_NOT_AVAILABLE_FOR_SUPPLIED_BITE` only for a truly supplied bite), the helper
  near the end of `band_process.py` that tests `bite.source == 'supplied' and not
  is_mattress(bite)`, `band_width.bite_model_name` (`'reduced_half_space'`),
  `band_diagnosis` (the bite-model word table, `bite_fallback_reason`, the slip-kinematics
  limitation text, `_apply_credibility` if it names the mattress), `band_report` (two word
  tables), `band_plain.BITE_MODEL_WORDS` (G'4: `'half_space': 'Half-space foil roll-gap model
  (reduced)'`, `'auto_half_space': 'Standard model, half-space model where it stops'`).
  SPEC17 package 2's `film_radius_ratio` returns 1.0 for a half-space bite as well, and
  `inlet_angle_basis` its mattress text with "half-space" in place of "mattress".
- `model_options.shear_cap_factor`: new `OPTION_OPTIONAL` key, `(0, 1]`, default 1.0, message
  "model_options.shear_cap_factor must be in (0, 1]"; kept in the validated case only when given
  (as `thermal_sensitivity` is). Question (G'4): id `shear_cap_factor`, group `Model settings`,
  "Largest friction stress as a share of the metal's shear strength", help "Only used by the
  half-space foil model. 1 means friction can reach the shear strength." Unit: none.
- Strip modulus passed to the solver: `material.youngs_modulus_pa/(1 -
  band_width.STRIP_POISSON_RATIO**2)`.
- Result: `result['bite_extras']` = the `extra` dict of the operating bite when it is a
  half-space bite, else `not_supplied('only the reduced half-space bite returns these')`. Top
  flag `BITE_MODEL_HALF_SPACE` / `BITE_MODEL_AUTO_HALF_SPACE` by the existing rule;
  `band_plain.FLAGS` sentences for both and for every solver flag that can reach the top level.
- `LIMITATIONS`: one sentence when a half-space bite is used ("reduced half-space bite: its
  load depends on how the bite ends are closed; on the published foil case it gives 88.9 to
  92.9 where the printed model gives 78 to 134 depending on an unstated end length").

**3. Benchmarks** (`physicroll/benchmarks.py`; `E_s*` as stated per row).

`BT-V1-HS` — the published foil case in the new solver. Case verdict
`REFERENCE_NOT_GRID_INDEPENDENT`. Rows (project values `[computed, SPEC18 prototype]`, to be
pinned from the implementation):

| quantity | project | reference (kind, read) | ratio | row verdict |
|---|---|---|---|---|
| `W_bar`, strip rigid in thickness (`E_s*` 1e13, the source's assumption) | 88.859 | 118 (caption, MODEL_OUTPUT, E1 FT) | 0.7530 | `REFERENCE_NOT_GRID_INDEPENDENT` |
| `W_bar`, strip thickness spring 80 GPa | 92.936 | 118 | 0.7876 | `REFERENCE_NOT_GRID_INDEPENDENT` |
| contact length, rigid / 80 GPa | 1.9614 / 2.0384 mm | 2.14 mm (MODEL_OUTPUT of the same published solution, E6 FT p.54) | 0.9166 / 0.9525 | `WITHIN_AGREEMENT_BAND` |
| peak `p/Y_s`, rigid / 80 GPa | 7.521 / 7.331 | about 7.7 (figure read by eye by the research note) | 0.977 / 0.952 | `REFERENCE_READ_BY_EYE` |
| peak position, rigid / 80 GPa | +0.305 / +0.349 mm | about +0.41 mm (by eye) | - | `REFERENCE_READ_BY_EYE` |
| entry and exit of contact, rigid | -1.118 / +0.843 mm | about -1.18 / +0.95 mm (by eye) | - | `REFERENCE_READ_BY_EYE` |
| regime | foil structure with a no-slip zone | regime II/III by the figure | - | `CONSISTENT_REGIME` |
| printed end conditions, end length 40 / 21 / 10 / 5 / 2.5 um (benchmark mode of package 3) | 78.01 / 88.62 / 102.62 / 117.47 / 134.15 | none (`reference_value` `None`); the labels of the last four carry the cross-check 88.0 / 101.9 / 116.6 / 133.2 `[computed, re-implementation of E1]`, ratios 1.007 each | - | `NO_REFERENCE_VALUE` |

Case note, fixed text: "The printed model closes the bite with a pressure step; its load is not
defined without an end length (78 at 40 um, 88.6 at 21 um, 102.6 at 10 um, 117.5 at 5 um,
134.2 at 2.5 um, computed twice independently). The caption value 118 corresponds to about
5 um; the paper states an element size of about 21 um. This solver keeps the exit contact zone
instead; its value for a strip rigid in thickness, 88.86, equals the printed model at 21 um. A
ratio to 118 is recorded and not judged. The published contact length (2.14 mm) corresponds to
about 103 in the same family." Test
`test_bt_v1_hs_reference_not_grid_independent`: the pins, the verdict words, and
`assertGreater(load at 5 um, 1.3 * load at 21 um)` with the docstring "Passing this test does
not mean the physics is right. It records that the published value depends on an unstated end
length."

Other rows:

| id | project value (planner) | reference | verdict |
|---|---|---|---|
| `BT-V2-R89-HS`, `BT-V2-R135-HS` | 42.800, 67.125 (`E_s*` 80 GPa; the radius is ASSUMED) | 58 measured (E1 FT) | `INDICATIVE_ASSUMED_INPUTS` (0.738, 1.157) |
| `BT-V3-FIG1-140UM-HS` | 46.820 | about 50 by eye from Fig. 4 | `REFERENCE_READ_BY_EYE` (0.936) |
| `BT-V3-EQ29-HS` | no-slip zone absent at 54 / 34 / 28 um and present at 52 / 32 / 26 um for r 0.5 / 0.25 / 0.10 | eq. 29: 51.2 / 36.2 / 22.9 um (PUBLISHED_FORMULA, E1 FT) | `CONSISTENT_REGIME` for r 0.5 and 0.25 (the bracket lies 2-5 % above and 6-12 % below eq. 29); r 0.10 recorded as 14-22 % above it, row verdict `RECORDED_DISCREPANCY` |
| `BT-X29-LOAD-EXPONENT-HS` | 2.461 at the published case | 2 to 2.6 (derived by the bite report, slope read by eye) | `REFERENCE_READ_BY_EYE`, inside the range |

New function `bite_model_comparison(case) -> dict` (rows per case pass and schedule pass:
mattress, Hitchcock and half-space force per width, slip, contact length, stiffness, zone
structure, each or its rejection reason) and CLI `python -m physicroll.benchmarks
--bite-comparison CASE.json`; a test runs it on the battery-foil scenario and compares with the
table above to 1 %.

### Budget (measure and report)
`derive_bite_response_half_space` on the 15 demo passes: mean at most 1.2 s, worst at most 3.5 s
cold, 0.6 s warm. `diagnose` of the battery-foil scenario with `bite_model` set to
`'auto_half_space'` in a scratch copy: at most 105 s (72.6 s today); the quick profile at most
32 s (13.8 s). `tests/test_band_*` unchanged in time.

### Tests
`tests/test_halfspace_bite_cases.py`: sensitivity tables (1e-3 after pinning), chord equals
Newton (1e-6), signs (`F_h < 0`, `F_se < 0`, `F_sx < 0`, `dF/dmu > 0`), one-sided tension flag.
A new `tests/test_band_halfspace.py` (coarse numerics): a foil case with each of the two new
options returns a bite with `HALF_SPACE_FLAG`; every lever row, the speed-consistent block, the
gauge trend and the friction stripe screen (SPEC17 package 7) use the half-space model or say
why not; `bite_extras` present; with the default option the result is identical to the run
before this package (compare `result_json` of the template case). `tests/test_band_plain.py`
passes (choices, words, flags). `tests/test_benchmarks.py`: the rows above.

### Documentation
Guide 3.3 (a third row in "where the roll-bite models stand": what changes at 30, 18 and 12 um,
from the comparison of the regenerated run, with finding 7 of section 0.1), 5.3 (the option and
when to use it: to see how far conclusions depend on the bite model), 10.3 (integration, warm
start, cost, the benchmark rows and finding 1 of section 0.1 in full), 12, 13, 14. README: two
sentences. Gap study section 11: BT-G1 `REDUCED_MODEL_OPT_IN` (what is not built: eqs
(10)-(14), stress in the no-slip zone; what the benchmark shows), BT-G5 `REDUCED_MODEL_OPT_IN`
(cap in the half-space solver only; `slab.py` and the mattress still reject; no friction
distribution), BT-G17 row extended, X18 note extended.

### Must not change
Default option: all five artifact pairs byte-identical except the additive `bite_extras`
not-supplied entry. No scenario is switched.

### Do not
- Do not make `'auto'` fall back to the half-space model.
- Do not mix bite models inside one sensitivity (the perturbed bites use the operating model).
- Do not present the comparison as a correction of the mattress numbers.
- Do not call any ratio to 118 a discrepancy or an agreement.

---

## Package 5 — Oil properties: viscosity table, Roelands pressure law, Eyring and limiting shear stress (A9)

### Why, and what the sources now contain
Row A9 asks for a viscosity law beyond exponential plus Barus and for a limiting shear stress.
The gap reports name the Roelands law without its formula and give no oil data. After the
research note:

| piece | what is available | read tag | used here as |
|---|---|---|---|
| valley shear | `tau_v = tau_0*asinh(eta*u_slide/(tau_0*h_v))`, oil properties at the contact pressure | E6 FT (4.32); E7 FT (eq. 6) | the valley model of package 6; its two stresses are fields here |
| smooth inlet film | `h_w = 6*alpha*eta0*u_bar/(theta0*(1 - exp(-alpha*sigma_y)))` | E6 FT (4.20) | already in `bite_tribology.py`; benchmark below |
| Roelands law | formula | E5 FT (L.3), (4.194) | optional pressure law |
| a kerosine foil-rolling base oil without additives (Somentor 31) | viscosity at 0-100 MPa and 40 / 60 / 100 C; Eyring stress at 625-1510 MPa; no limiting shear stress up to 0.045 of the pressure | E6 FT, Table 2.1, Fig. 2.7 | documented example data; lower bound for the cap |
| limiting shear stress `tau_L(p)` | no value | - | supplied input |

So: a viscosity TABLE from the oil data sheet for the temperature dependence, Roelands as an
optional pressure law with its measured error stated, and Eyring and limiting stresses as
supplied inputs with the published data as context. Nothing here changes a result unless a case
supplies the new keys; the valley models that use the stresses are package 6.

### Design

**A. Viscosity against temperature: table** (`bite_tribology.Lubricant`). New optional field
`viscosity_table` (tuple of `(temperature_k, viscosity_pa_s)` pairs, default `None`).
`validate`: at least 2 pairs, temperatures strictly increasing in `[230, 700]`, viscosities in
`(0, 10]` and non-increasing. With a table, `ln eta0` is interpolated linearly in `T` between
neighbouring points and continued with the end segment's slope outside
`[D, SPEC18: piecewise exponential through data-sheet points]`. New method
`temperature_viscosity_coefficient_at(T)` (local `-d ln eta0/dT`; the constant coefficient
without a table); `_film_core` uses it for the thermal loading parameter. Flags
`VISCOSITY_FROM_TABLE`, `VISCOSITY_TABLE_EXTRAPOLATED`. Case key
`tribology.lubricant.viscosity_table`: list of `{"temperature_k", "viscosity_pa_s"}` or null;
message "tribology.lubricant.viscosity_table must be null or >= 2 points with increasing
temperature and non-increasing viscosity". The four existing lubricant keys stay required (the
reference viscosity is then not used for `eta0`; say so in the result).

**B. Viscosity against pressure: Barus or Roelands.** New field `pressure_law='barus'` (or
`'roelands'`) and optional `roelands_z` (`(0, 2]`, default `None`):

    eta(T, p) = eta0(T) * exp{ (ln eta0(T) + 9.67) * [ (1 + p/p_r)^z - 1 ] }      [E5 FT (L.3)]
    p_r = 196.2e6 Pa;  eta0 in Pa s
    z   = roelands_z, or p_r*alpha/(ln eta0(T) + 9.67)                           [E5 FT (4.194)]

`eta0(T)` from A or from the exponential law: the temperature factor of (L.3) is not used.
Without `roelands_z` the index is evaluated at the temperature of the call, so that the slope at
zero pressure equals the entered Barus coefficient at every temperature `[D, SPEC18]`.
`ValueError` when `ln eta0 + 9.67 <= 0`. The law is the product form: the source warns that one
thesis prints a sum, which is wrong (E5 FT); put that in a code comment.
The inlet film formula is NOT changed: it is the published closed form for a Barus oil and only
uses pressures up to the yield stress. `pressure_law` changes `dynamic_viscosity_pa_s(T, p)`,
which the valley shear of package 6 uses at the mean bite pressure. Flag `ROELANDS_PRESSURE_LAW`.

What the one foil oil with published data says about both laws (`s23/v_p5.py`; Somentor 31 at
40 C, `eta0` 1.409e-3 Pa s, `alpha` 10.40e-9 /Pa, `z` = 0.657133 from (4.194)):

| pressure MPa | measured Pa s [E6 FT] | Barus (ratio) | Roelands (ratio) |
|---|---|---|---|
| 100 (viscometer) | 3.985e-3 | 3.98637e-3 (1.000) | 3.69913e-3 (0.928) |
| 625 (disc machine) | 2.5 | 0.937185 (0.375) | 0.180001 (0.072) |
| 945 (disc machine) | 15.0 | 26.1311 (1.742) | 1.22828 (0.082) |
| 1510 (disc machine) | 740 | 9312.6 (12.6) | 24.363 (0.033) |

Neither law carries this oil from the inlet to bite pressure; Roelands with the index from the
low-pressure slope is low by a factor 12 to 30 there (the thesis says the same of its own fit).
This goes into the guide and into the result of the valley models as a limitation, with the
advice: enter `roelands_z` or the Barus coefficient fitted at the pressure of interest, and read
valley friction as an order of magnitude.

**C. Eyring and limiting shear** (`Lubricant`, all optional, default `None`, no value assumed):
`eyring_stress_pa` (`[1e4, 1e9]`), `eyring_stress_pressure_coefficient` (`(0, 0.1]`):
`tau_0(p) = eyring_stress_pa + coefficient*p` (an absent one counts as zero; at least one is
needed for the Eyring valley model) `[D, SPEC18 form; E6 FT data: 4.5 / 6.0 / 11.7 MPa at 625 /
945 / 1510 MPa and 40 C, i.e. 0.0072 / 0.0063 / 0.0077 of the pressure]`.
`limiting_shear_stress_pa` (`[1e4, 5e9]`), `limiting_shear_pressure_coefficient` (`(0, 1]`):
`tau_L(p) = limiting_shear_stress_pa + coefficient*p` `[D, SPEC18 form; no value in any
source]`. Flag `LIMITING_SHEAR_BELOW_PUBLISHED_LOWER_BOUND` when `tau_L(p_mean)/p_mean < 0.045`,
with the sentence "no limiting shear stress was seen up to 0.045 of the pressure for a kerosine
base oil at 40 C [E6 FT]; the entered cap is lower". A figure of 0.05-0.1 for mineral oils
circulates; the note has it from memory only: do not print it.

Constant `bite_tribology.EXAMPLE_KEROSINE_BASE_OIL` (a dict, documentation and tests only, never
a default): name, "no additives; a base oil, not a plant's rolling oil", the nine viscometer
values at 0 MPa and 100 MPa (40 / 60 / 100 C: 1.409e-3 / 1.033e-3 / 0.632e-3 and 3.985e-3 /
2.699e-3 / 1.625e-3 Pa s), `alpha` 10.40e-9 / 9.60e-9 / 9.44e-9 /Pa, the Eyring table, the
lower bound 0.045, conductivity 0.125 W/mK at ambient pressure ("assumed equal to another oil" by
the source) and 0.25 W/mK in the nip; every entry tagged `[E6 FT]`.

Case schema: `tribology.lubricant` accepts the present keys plus optional `viscosity_table`,
`pressure_law`, `roelands_z`, `eyring_stress_pa`, `eyring_stress_pressure_coefficient`,
`limiting_shear_stress_pa`, `limiting_shear_pressure_coefficient`; an absent key takes the
default (`None`, or `'barus'`); messages "tribology.lubricant.<key> must be ...". The film and
friction rows of `band_process.friction_section` echo the law and carry the table flags.

### Worked numbers (`s23/v_p5.py`, `s23/v_fric2.py`, `s23/fric.py`)
Viscosity table: the three 0 MPa points of the example oil give 1.206440e-3 Pa s at 50 C,
8.07995e-4 at 80 C, 4.94340e-4 at 120 C and 1.921860e-3 at 20 C (both extrapolated), segment
coefficients 0.0155207 and 0.0122833 /K. Points 20 / 70 / 130 C with 3.0 / 1.4 / 0.7 cSt (the
data-sheet values in the module docstring) at 800 kg/m3: `eta0(40 C)` = 1.76935e-3 Pa s,
coefficients 0.0152428 and 0.0115525 /K.
Roelands: the table of B; at 60 C (`eta0` 1.033e-3, `alpha` 9.60e-9): `z` = 0.673959,
2.52609e-3 Pa s at 100 MPa (measured 2.699e-3; Barus 2.69788e-3).

### Benchmarks
- `BT-G3-FILM-E6-T42`: `inlet_film_thickness` (no thermal factor) on the thesis's foil case:
  oil 1.0e-3 Pa s at 60 C, 1.0e-8 /Pa, yield 230 MPa, no tension; `contact_radius_m` =
  `5e-6/0.0058^2` = 0.148633 m so that the inlet angle is the published slope 0.0058; strip
  entry speed 0.88 of the roll speed (ASSUMED: the note finds the table reproduced with a mean
  speed of 0.93 to 0.96 of the roll speed). Project 0.3242 / 0.1081 / 0.0540 / 0.0324 /
  0.0108 um at 30 / 10 / 5 / 3 / 1 m/s; published `h_w` 0.323 / 0.108 / 0.054 / 0.032 / 0.011
  (MODEL_OUTPUT, E6 FT); ratios 1.004 / 1.001 / 1.001 / 1.013 / 0.983. Verdict
  `INDICATIVE_ASSUMED_INPUTS`.
- `BT-V4-FILM` (film only): 50 -> 25 um, yield 150 MPa, tensions 20 MPa, R 135 mm, oil
  2.5e-3 Pa s and 1.2e-8 /Pa, composite roughness 0.3 um [E4 EX, Table I]; published film
  ratios 0.22 at 5 m/s and 1.76 at 40 m/s (MODEL_OUTPUT, BT-S3 EX). Roll surface speed = the
  quoted speed, strip entry speed half of it (ASSUMED), contact radius = R, inlet 40 C: 62.8 nm
  and 502.4 nm, film ratios 0.2093 and 1.6748, ratios 0.951 and 0.952. Verdict
  `INDICATIVE_ASSUMED_INPUTS`. Edit the `BT-V4` entry of `NOT_ENCODED`: "film ratio encoded as
  BT-V4-FILM; load and slip curves need digitising and a friction distribution through the bite".
- `A9-PRESSURE-LAWS-KEROSINE`: the table of design item B, rows per law and pressure; row verdicts by the
  band (the 100 MPa Barus row `WITHIN_AGREEMENT_BAND`, every other row
  `RECORDED_DISCREPANCY`); case verdict `RECORDED_DISCREPANCY`; reference kind MEASUREMENT.

### Tests
`tests/test_bite_tribology.py`: table interpolation and extrapolation (the worked numbers to
`1e-6` relative; equality with the exponential law for two points; flags; validation);
`temperature_viscosity_coefficient_at` against a finite difference; the Roelands numbers of B
and its slope at zero pressure equal to the Barus coefficient (finite difference, `1e-6`); the
`ValueError` of the Roelands domain; the Eyring and limiting-stress fields validate and
default to `None`; the example-oil constant has a tag on every entry; a `Lubricant` built with
the present arguments gives bit-identical results (every existing test passes untouched).
`tests/test_band_v2_sections.py`: a case with a viscosity table: film and friction rows carry
the flag, and with a two-point table equal to the exponential law no number changes.
`tests/test_benchmarks.py`: the three cases. Absent-input check on the template.

### Documentation
Guide 8.1: the oil part of the availability table; what to enter and where each value comes
from (data sheet; the published example oil as an illustration, with "no additives; not a
rolling oil of a plant"); the pressure-law table with its conclusion. 5.3, 13, 14, 15 (sources
E5, E6 with read tags). Gap study section 11: A9 `REDUCED_MODEL_OPT_IN` (table, Roelands as an
option with its measured error, supplied Eyring and limiting stress; no limiting-stress value
exists in any source; inlet temperature from the roll surface is package 10's output and is not
fed back in this phase).

### Must not change
Artifacts: additive only (`inputs.tribology.lubricant` gains null or default keys where the
section is present; nothing else). No scenario selects a table or the Roelands law.

### Do not
- Do not give the Eyring stress or the limiting shear stress a default, and do not print the
  remembered 0.05-0.1.
- Do not change the film formula with the pressure law.
- Do not use the example oil as a default or a preset.

---

## Package 6 — Friction closure on the published contact-ratio curve; published fits as tested functions (BT-G3 reduced)

### Why, and what the sources now contain
Row BT-G3 asks for an inlet-only mixed-lubrication closure "(take the fitted functions from the
originals)". After the research note:

| piece | what is available | read tag | used here as |
|---|---|---|---|
| load sharing of friction | `mu = A*mu_c + (1 - A)*mu_v` | BT-S9 EX; E7 FT (its eq. 7) | the closure |
| contact ratio against film ratio for a foil pass | five points for the 20 -> 15 um case, one roughness (0.1 um), one wavelength (15 um), one oil, 1 to 30 m/s | E6 FT, Table 4.2 | the default curve |
| valley film against film ratio, same table | five points | E6 FT, Table 4.2 | the default valley film |
| valley shear | `tau_v = tau_0*asinh(eta*u_slide/(tau_0*h_v))`, oil properties at the contact pressure | E6 FT (4.32); E7 FT (eq. 6) | valley model `'eyring'` |
| smooth inlet film | `h_w = 6*alpha*eta0*u_bar/(theta0*(1 - exp(-alpha*sigma_y)))` | E6 FT (4.20) | already in `bite_tribology.py`; benchmarked in package 5 |
| asperity crushing rate under bulk strain | four fitted laws (Wilson-Sheu, thesis eq. 3.20, the Marsault form, the regression of Korzekwa's results) | E5 FT, E6 FT; the original papers CIT | tested functions; NOT assembled (below) |
| height distribution (Christensen), flow factors (Marsault's fits of Patir-Cheng; Wilson-Marsault) | formulas | E5 FT | tested functions; NOT assembled |
| inlet analysis that produces the contact ratio | method described; equations (4.8), (4.13) restored by the note, sign of (4.4) not reconciled, thermal factors not transcribed, three different inlet slopes used | E6 FT ch. 4 in part | NOT built |
| friction on the contact areas `mu_c(h_s, r)` | curves exist only as a figure; values in the sources: 0.013-0.036 (boundary film strength over pressure, E6 FT p.72, derived), 0.09 (BT-S6 AB), 0.1 or factor 0.25 (E4 EX) | - | a REQUIRED input |

**Why no inlet analysis is assembled** (planner's checks, `s23/v_fric2.py`):
- The height-distribution relation between contact ratio and mean film (E5 (4.18), (4.20)) does
  not reproduce the thesis table's own pairs: at A = 0.28 / 0.53 / 0.69 / 0.88 it gives 0.905 /
  0.788 / 0.689 / 0.495 of the tabulated mean film. The thesis's surface model is therefore not
  the one transcribed.
- The four crushing laws agree only near A = 0.5, `p_bar/2k` = 1 (`W` = 1.62, 1.62, 5.47 and 1.76
  for thesis, Marsault, Wilson-Sheu, Korzekwa); at A = 0.5, `p_bar/2k` = 0.6: 0.05 (clipped),
  0.583, 1.126, 0.587; at A = 0.3, `p_bar/2k` = 0.6: 0.058, 0.899, 6.81, 2.23. The theory values
  the thesis quotes at A = 0.5 are 1.47 (0.67 in Wilson and Sheu's field) at `p_bar/2k` = 1 and
  0.16 (0.32) at 0.6 [E6 FT p.38].
- A model built from these would have five published points to meet and no way to decide which
  transcription is at fault when it does not.
So the closure takes the published points as an INPUT curve. It is a reduced model: say so in the
status string, the flag and the guide. Crushing law to use when the inlet analysis is built
later: the regression of Korzekwa's results (E5 (4.97)-(4.100)): it is the one the foil papers
use (E4 EX, E7 FT), it is defined for all `0 < A < 1`, the thesis fit is tuned to A near 0.5 and
is clipped elsewhere, the Marsault form degenerates at small and large A, and Wilson-Sheu's is
reported as poor below A = 0.3 (E5 FT).

### Design

**A. Closure** (`bite_tribology.FrictionClosure`). New fields; the defaults keep the present
behaviour bit for bit:
`model='placeholder_exponential'` (or `'load_sharing_curve'`), `contact_friction=None`,
`contact_ratio_curve=None`, `valley_film_curve=None`, `valley_model='constant'` (or `'eyring'`,
`'newtonian_capped'`). Module constants `[E6 FT, Table 4.2; film ratio = h_s/d0, derived]`:

    PUBLISHED_FOIL_CONTACT_RATIO_CURVE = ((0.14, 0.88), (0.36, 0.69), (0.55, 0.53), (0.97, 0.28), (2.37, 0.01))
    PUBLISHED_FOIL_VALLEY_FILM_CURVE   = ((0.14, 0.42), (0.36, 0.62), (0.55, 0.79), (0.97, 1.10), (2.37, 2.17))
                                         # (film ratio, valley film / combined roughness)

A `None` curve means the published one. Validation of a supplied curve: 2 to 12 points, film
ratios strictly increasing in `(0, 100]`, contact ratios in `[0, 1]` and non-increasing, valley
films positive and non-decreasing. For `model == 'load_sharing_curve'`, `contact_friction` is
REQUIRED (`(0, 1]`; `ValueError('friction_closure.contact_friction is required for the
load_sharing_curve model: the sources span 0.013 to 0.1')`).

    A(Lambda)   linear in ln(Lambda) between neighbouring points; the end values are held outside
    h_v/Rq      linear in ln-ln between neighbouring points; first value held below the curve;
                above it h_v/Rq = Lambda * (last value / last film ratio)
                [D, SPEC18: interpolation of published points, not a contact model]
    mu          = A*mu_c + (1 - A)*mu_v                                       [BT-S9 EX; E7 FT]
    mu_v        'constant'         -> closure.mu_v (0.008, the present [D] value)
                'eyring'           -> min(tau_0*asinh(eta*u_s/(tau_0*h_v)), tau_L)/p_mean   [E6 FT (4.32)]
                'newtonian_capped' -> min(eta*u_s/h_v, tau_L)/p_mean; ValueError without a cap
    dmu/dLambda 'constant': (mu_c - mu_v)*(A_2 - A_1)/(Lambda*ln(L_2/L_1)) inside a segment, 0 outside;
                other valley models: central difference in Lambda (relative step 1e-4) at a
                fixed bite state [D, SPEC18]

with `tau_0` and `tau_L` from the lubricant fields of package 5 at `p_mean` (the Eyring model
needs an Eyring stress and applies the cap only when a limiting stress is entered),
`eta = dynamic_viscosity_pa_s(T_inlet, p_mean)`, `h_v` from the curve times the composite
roughness, `u_s` the mean sliding speed and `p_mean` the mean bite pressure. These come from the
bite, so: `friction_coefficient(film_ratio, closure=None, *, lubricant=None, finish=None,
bite_state=None)` with `bite_state = {'mean_pressure_pa', 'mean_sliding_speed_m_s',
'inlet_temperature_k'}`; `friction_at_speed` / `friction_speed_curve` gain
`mean_pressure_pa=None`, `backward_slip_fraction=None` and pass them through;
`band_process._mu_inputs` fills them from the bite (`separating_force_n/(width*
contact_length_m)`; `u_s = V_r*(b + f)/2`, `b = 1 - (1 + f)*h1/h0`, `f` = forward slip
`[D, SPEC18]`). Without them the two computed valley models raise
`ValueError('valley shear needs the bite state')` and the row is reported as rejected, as other
bite failures are.

The film ratio the closure is entered with is the repository's (smooth inlet film over composite
roughness). The table's abscissa is the thesis's full inlet integration; its own closed-form
film (4.20) is 1.36 / 1.11 / 0.98 / 0.89 / 0.79 of that at 30 / 10 / 5 / 3 / 1 m/s. State this in
the limitations: the abscissa carries that much mismatch.

Result of `friction_coefficient` for the new model: the present keys plus `contact_area_ratio`,
`contact_friction`, `valley_friction`, `valley_model`, `valley_film_thickness_m`,
`valley_shear_stress_pa` (or null), `valley_shear_capped` (bool or null), `contact_ratio_curve`,
`curve_is_published_default`; `status`
`'UNVALIDATED_LOAD_SHARING_ON_A_PUBLISHED_CONTACT_RATIO_CURVE'`; flags
`REDUCED_LOAD_SHARING_CLOSURE_NO_INLET_ANALYSIS` (instead of
`PLACEHOLDER_FRICTION_CLOSURE_NOT_FITTED`), `CONTACT_RATIO_CURVE_OF_ONE_PUBLISHED_FOIL_PASS`
with the default curve, `CONTACT_FRICTION_IS_AN_ENTERED_VALUE`,
`FILM_RATIO_OUTSIDE_CONTACT_RATIO_CURVE` when an end value is held. Limitations (fixed list):
the curve is model output for one pass (20 -> 15 um, roughness 0.1 um, wavelength 15 um, one
oil) and is not a property of other surfaces; the level of friction is set by the entered
contact friction (0.013 to 0.1 in the sources), so the closure supports the change of friction
with speed, not its level; published data need a contact friction that varies with film and
reduction and cannot be met with one value (E7 FT); friction is the same through the bite; no
roughness wavelength, lay or reduction. Regime words and the industrial window stay as SPEC17
package 2 defines them.

Case schema: `tribology.friction_closure` accepts the present three keys plus optional `model`,
`contact_friction`, `contact_ratio_curve` (list of `{"film_ratio", "contact_ratio"}`),
`valley_film_curve` (list of `{"film_ratio", "valley_film_over_roughness"}`), `valley_model`.
`validate_tribology` normalises a given closure to all its keys and an absent one to `None` as
today.
`band_process.friction_section`: `flags` and `note` follow the closure model; note of the new
model: "Load sharing on a published contact-ratio curve of one foil pass. The friction level is
your entered contact friction; read the change with speed, not the level."
`speed_consistent_critical_speed` keeps using the closure's SLOPE anchored at the friction used
(its floor `closure.mu_v` becomes the closure's valley friction).

**B. Published fits as tested functions** (new module `physicroll/asperity_contact.py`,
`STATUS = 'PUBLISHED_FITS_TRANSCRIBED_NOT_ASSEMBLED_INTO_A_MODEL'`; nothing in the engine
imports it; it exists so that the later inlet analysis starts from checked transcriptions):
`christensen_contact_ratio(h_over_rq)` (E5 (4.18)), `christensen_mean_film_over_rq(h_over_rq)`
(4.20), `crushing_rate_thesis(a, p_over_2k)` (E6 (3.20), clipped to `[0.05, 2.5]`),
`plastic_strain_rate_marsault(a, hardness)` (E5 (4.96)), `..._wilson_sheu` ((4.92)),
`..._korzekwa` ((4.97)-(4.100)), `hardness_wilson_sheu_no_bulk(a)` ((4.94)),
`pressure_flow_factor(h_over_rq, gamma)` ((4.160)), `percolation_film_over_rq(gamma)`
((4.171)). Name each after its equation and source in the docstring; none is called "Sutcliffe
(1988)" (the note's reconciliation remark). Relation between the two forms: `p_bar/2k =
A*H_a/2`, `W = 1/E_p`.

### Worked numbers (`s23/v_p5.py`, `s23/v_fric2.py`)

Closure with the published curves, constant valley friction 0.008:

| film ratio | contact ratio | mu at `mu_c` 0.09 | slope | mu at `mu_c` 0.03 | slope | placeholder mu | slope |
|---|---|---|---|---|---|---|---|
| 0.1 (below the curve) | 0.8800 | 0.08016 | 0 | 0.02736 | 0 | 0.08220 | -0.07420 |
| 0.2 | 0.8082 | 0.07428 | -0.08248 | 0.02578 | -0.02213 | 0.07514 | -0.06714 |
| 0.380072 (battery-foil demo after SPEC17 package 2) | 0.6695 | 0.06290 | -0.08145 | 0.02273 | -0.02185 | 0.06407 | -0.05607 |
| 0.5 | 0.5660 | 0.05441 | -0.06191 | 0.02045 | -0.01661 | 0.05774 | -0.04974 |
| 1.0 | 0.2708 | 0.03021 | -0.02478 | 0.01396 | -0.00665 | 0.03817 | -0.03017 |
| 2.0 | 0.0613 | 0.01303 | -0.01239 | 0.00935 | -0.00332 | 0.01910 | -0.01110 |
| 3.0 (above the curve) | 0.0100 | 0.00882 | 0 | 0.00822 | 0 | 0.01208 | -0.00408 |

At the five published film ratios the closure returns the published contact ratios exactly
(software identity). The contact friction that gives the demo's supplied 0.03 at its film ratio
is 0.04086; 0.027 needs 0.03638. Friction at the five points for `mu_c` = 0.0135 (the thesis's
boundary-film value): 0.01284 / 0.01179 / 0.01091 / 0.00954 / 0.00805.
Valley film: `h_v/Rq` = 0.42 at 0.1, 0.486548 at 0.2, 0.639534 at 0.380072, 1.125779 at 1.0,
2.746835 at 3.0.
Valley models (oil 1.0e-3 Pa s, `alpha` 1.0e-8 /Pa, Barus, `p_mean` 4e8 Pa -> `eta` 0.0545982;
roughness 0.1 um, film ratio 0.36 -> `h_v` 62 nm; sliding 0.3 m/s; `mu_c` 0.09):
Newtonian 264184.6 Pa; Eyring with `tau_0 = 0.007*p`: 263794.2 Pa, `mu_v` 6.59485e-4,
`mu` 0.0623044. Second case (2.5e-3 Pa s, 1.2e-8 /Pa, 6e8 Pa -> `eta` 3.348577; roughness
0.3 um, film ratio 0.2 -> `h_v` 145.964 nm; sliding 2 m/s): Newtonian 4.58821e7 Pa; Eyring
1.296215e7 Pa, `mu_v` 0.0216036, `mu` 0.0768848; Newtonian capped at `0.045*p`: capped,
`mu_v` 0.045, `mu` 0.0813711.
Function checks for B: Christensen contact ratio 0.5 / 1 / 0 at `h/(3 Rq)` = 0 / -1 / 1, mean
film over roughness 0.41015625 at 0 and 3 at 1; Wilson-Sheu hardness without bulk strain 5.142
at A -> 0 and 4.835147 at A = 0.5; `E_p`(A 0.5, `H_a` 2) = 1.240978; the crushing rates quoted
in "Why"; percolation film over roughness 0.0383191 at gamma 9 (the foil paper quotes 0.038, E4
EX); pressure flow factor 1.165667 (gamma 9) and 0.832857 (gamma 1) at `h/Rq` = 3.

### Benchmarks
- `BT-G3-CRUSHING-LAWS`: the four laws at (A 0.5, `p_bar/2k` 1.0) and (0.5, 0.6) against the
  thesis's theory values 1.47 and 0.16 (its own field) and 0.67, 0.32 (Wilson and Sheu's field,
  for the Wilson-Sheu fit) (MODEL_OUTPUT, E6 FT p.38). Ratios: thesis fit 1.102 and 0.31
  (clipped value); Korzekwa 1.198 and 3.67; Marsault 1.102 and 3.65; Wilson-Sheu 8.17 and 3.52.
  Case verdict `RECORDED_DISCREPANCY`; note: "the transcribed fits do not agree with one another
  or with the theory values away from one point; they are not assembled into a model".
The closure itself has no independent published friction value to be compared with: its curve
is the published table (returned exactly at the five points: a software identity, which is a
test and not a benchmark case) and its level is an entered number. Say so in the guide.

### Tests
`tests/test_bite_tribology.py`: the closure table to `1e-5`; the five published points returned
exactly; continuity of `mu` across every curve point; the valley-film values; the valley
numbers (`1e-5` relative); the lower-bound flag of package 5 on a capped case; `ValueError`
without `contact_friction`, without a bite state, without a cap; curve validation; the default
`FrictionClosure()` gives bit-identical results (every existing test passes untouched). New
`tests/test_asperity_contact.py`: the function checks of B. `tests/test_band_v2_sections.py`: a
case with the new closure and `use_computed_friction` false: friction rows carry the new keys
and flags, no bite or score differs from the same case with the placeholder; with
`use_computed_friction` true the fixed point converges (coarse numerics).
`tests/test_benchmarks.py`: `BT-G3-CRUSHING-LAWS`. Absent-input check on the template.

### Documentation
Guide 8.1: the closure part of the availability table; both closures side by side with the
worked table; what to enter and where the contact friction can come from (package 7); X22
answered ("the placeholder's level and slope have no support; the new closure has a published
shape for one foil pass and an entered level"). 5.3, 13, 14, 15 (sources E4-E7 with read
tags). Gap study section 11: BT-G3 `REDUCED_MODEL_OPT_IN` (not built: the inlet analysis,
asperity crushing in the bite, `mu_c(h_s, r)`, two wavelengths; why, with the three checks of
"Why").

### Must not change
Artifacts: additive only (`inputs.tribology.friction_closure` and every echoed `closure` dict
of the friction rows gain the new keys with their defaults where the section is present;
nothing else). No scenario selects the new closure.

### Do not
- Do not call the closure Sutcliffe's, Wilson and Sheu's or a mixed-lubrication model; it is
  load sharing on a published curve.
- Do not give `contact_friction` a default.
- Do not assemble the functions of B into a film or contact calculation.
- Do not make friction vary through the bite.

---

## Package 7 — Friction identified from load, torque and forward slip (BT-G6)

### Why
Row BT-G6 (BT-S3 EX, BT-S5 AB, BT-S37 SN, BT-S34 FT): slip is the cheapest friction indicator
on a mill; "inverse fit of friction to load, torque and slip; note that simple slip formulas are
unreliable". Section 0.1, finding 7, shows why it belongs here: at foil gauge the load depends
on friction to a power of about 3, and the supplied 0.03 puts the 18 um pass outside the trade
range with the half-space bite. Finding 1 adds a caution that goes into the result: the load of
a foil bite depends on how the bite ends are closed, and an identified friction absorbs that.
Which measured quantity carries the friction information depends on the regime (planner,
`s23/v_slipexp.py`, local exponents `d ln(.)/d ln(mu)`):

| case | structure | load exponent | forward-slip exponent |
|---|---|---|---|
| published foil case, 20 -> 15 um, friction 0.03, strip spring 80 GPa | A B F | 2.461 | 0.378 |
| same, strip rigid in thickness | A B E F | 2.455 | 0.385 |
| BT-V2, 73 -> 31.39 um, friction 0.026, R 89 mm | A F | 1.570 | 2.473 |

With a no-slip zone the forward slip hardly depends on friction. In the printed-end family of
the published case the load rises from 88.6 to 117.5 between end lengths of 21 and 5 um and the
slip falls from 0.2022 to 0.1775; by the exponents above that is 12 % in a friction identified
from load and about 30 % in one identified from slip. Without a no-slip zone the slip is the
sharper indicator. The routine therefore reports both exponents with every record.

### Design

**Input.** `measurement.pass_records` (the `measurement` section and `band_sensors.py` come from
SPEC17 package 4; add the key to its strict key list, null by default): a list of 1 to 8 records

| key | unit | rule | default |
|---|---|---|---|
| `label` | text | nonempty | required |
| `separating_force_n` | N | > 0 | required |
| `forward_slip_fraction` | - | (-0.2, 1) or null | null |
| `torque_per_work_roll_nm` | N m | > 0 or null | null |
| `exit_speed_m_s` | m/s | > 0 | the case pass |
| `entry_thickness_m`, `exit_thickness_m`, `entry_tension_pa`, `exit_tension_pa`, `mean_flow_stress_pa` | SI | as `pass` | the case pass, each |
| `force_uncertainty_fraction` | - | (0, 0.5] | 0.05 |
| `slip_uncertainty_absolute` | - | (0, 0.2] | 0.01 |
| `torque_uncertainty_fraction` | - | (0, 0.5] | 0.10 |
| `provenance` | text | nonempty | required |

The three uncertainty defaults are analyst choices `[D]`, stated in the result. Messages
"measurement.pass_records[i].<key> must be ...".

**Solver access.** `_BiteCache.state(bite_pass, model=None) -> dict` with `force_n`,
`forward_slip_fraction`, `torque_per_work_roll_nm` (or `None`), `contact_length_m`: ONE nominal
solve, no sensitivities, cached by the same key as `get` (mattress: `solve_mattress_bite`;
half-space: `solve_half_space_bite`, warm-started; Hitchcock: `chatter._converged_bite`, torque
from the slab result if it carries one, else `None`). It exists so that an inversion costs
solves, not derivations.

**Identification** (`band_process.friction_identification(case, records, cache, op_bite)`), for
each record, with the bite model `perturbed_bite_model(case, op_bite)`:
1. `mu_F`: the friction with `F_model(mu) = F_measured`. Secant in `ln mu` from the case
   friction and `mu*(F_meas/F_model)^(1/2)`, at most 12 solves, tolerance `1e-4` relative in
   force, bracket `[0.003, 0.3]`; `NOT_FOUND` with the reason when the bracket is left or a solve
   is rejected.
2. `mu_slip`, `mu_torque`: the same for forward slip and torque where measured and where the
   model returns the quantity; each may be `NOT_FOUND` (slip is not monotonic in friction in
   every regime: scan 9 friction values, geometric between `0.4*mu_F` and `2.5*mu_F`, and take
   the root nearest `mu_F`; report `multiple_roots` when there are several).
3. `mu_joint`: the minimiser over the same 9-point scan, refined by a parabola through the best
   three points, of
   `((ln F_model - ln F_meas)/s_F)^2 + ((f_model - f_meas)/s_f)^2 + ((ln T_model - ln
   T_meas)/s_T)^2` (terms of unmeasured quantities dropped); `normalised_residuals` of the three
   at `mu_joint`; `consistent` = all absolute values `<= 2`.
4. With force and slip both measured: `friction_and_flow_stress` = the pair `(mu, Y scale)`
   that reproduces both exactly, by Newton on the 2 x 2 system with numerical derivatives from
   `state` (at most 8 iterations, scale limited to `[0.5, 2]`), or `NOT_FOUND`. Note fixed in
   the result: "two unknowns from two numbers: there is no redundancy to check them".
5. `load_exponent_in_friction` and `slip_exponent_in_friction` at `mu_F` (central difference
   with `mu_F*(1 +- 0.01)`: two more solves; from `state['extra']` when a half-space derivation
   at that friction is in the cache). Flag `FORWARD_SLIP_INSENSITIVE_TO_FRICTION_IN_THIS_REGIME`
   when the slip exponent is below 0.5 in magnitude: `mu_slip` of that record is then marked
   `weakly_determined` and the fixed sentence is "with a no-slip zone the forward slip hardly
   depends on friction; the force is the better indicator here".
Summary over the records: the values of `mu_F`, their spread, and with two or more exit speeds
the slope `d mu_F / d ln(u)` by least squares.

**Contact friction implied** (only with `tribology`): for each record the film ratio at `mu_F`
(`friction_at` with the record's speed and the bite at `mu_F`), the contact ratio `A` of
package 6's curve at that film ratio (the case closure's curve, else the published one) and
`mu_c = (mu_F - (1 - A)*mu_v)/A` with the closure's valley friction (constant model; 0.008
without a closure) `[D, SPEC18: package 6's load sharing solved for the contact friction]`;
`null` with the reason when `A < 0.05`. `suggested_contact_friction` = the median over the
records, with their spread, and with two or more film ratios differing by more than 20 % the
slope of `mu_c` against `ln(Lambda)` (the published observation is that one value does not fit
a speed range, E7 FT). Worked value: `mu_F` 0.03 at film ratio 0.380072 gives `A` 0.6695 and
`mu_c` 0.04086.

**Result.** `result['process']['friction_identification']`: `not_supplied` without records;
else `status` `'IDENTIFIED_FROM_ENTERED_RECORDS_NOT_VERIFIED'`, `bite_model`, `rows`, `summary`,
`suggested_contact_friction`, `declaration` (`{'coefficient': median mu_joint,
'fit_uses_force_torque_slip': True only when every record has all three, 'calibrated': False,
'source': 'identified from entered pass records'}`: the vocabulary of
`lubrication.EffectiveFriction`; `calibrated` stays false because the tool cannot verify the
entered numbers), `how_to_use` ("to use a value, enter it as pass.friction_coefficient; nothing
is applied automatically"), `flags`, `limitations`. Flags (top level too, with
`band_plain.FLAGS` sentences): `FRICTION_IDENTIFIED_FROM_ENTERED_RECORDS`;
`MEASURED_SLIP_NOT_REPRODUCED_BY_CONSTANT_FRICTION_BITE` (a record with slip whose
`normalised_residuals` slip term exceeds 2 at `mu_F`), with the fixed sentence of SPEC17
package 2 on constant friction and forward slip [BT-S3 EX, BT-S5 AB];
`IDENTIFIED_FRICTION_DIFFERS_FROM_CASE_FRICTION` (median `mu_F` outside +-20 % of the case
value). Limitations: constant friction through the bite (a friction distribution is the
published remedy for foil slip [BT-S5 AB]; not built); the bite model's own status (the
mattress bite gives 49.8 and the reduced half-space bite 88.9 to 92.9 on the published case,
whose printed model gives 78 to 134 depending on an unstated end length: an identified friction
absorbs that spread, by about 12 % from load and 30 % from slip on that case); flow stress
taken as entered; simple forward-slip formulas are reported as
unreliable [BT-S37 SN] and none is used; no closed-gap load share.

**Report**: `band_report._process_section`: block "Friction from your pass records": one table
(record, speed, friction from force / slip / torque, joint, consistent or not), the summary
sentence, the implied contact friction, the `warn` paragraph "not applied".

### Worked numbers
BT-V2 inverted (`s23/inv2.py`, run before the selection rule of package 3 existed; structure
A F in both cases, so the rule does not change them, but re-run and pin; 73 -> 31.39 um,
tensions 0.107 and 0.132 `Y_s`, `Y_s` 230 MPa, `E_R*` 230 GPa, `E_s*` 80 GPa, measured `W_bar`
58): reduced half-space bite, `mu_F` = 0.03064 for an assumed R of 89 mm (forward slip 0.1966)
and 0.02488 for 135 mm (slip 0.2594), 5 secant steps each. The source infers 0.026 with its own model and
quotes "about 0.03" from mill tests [BT-S1 FT]. Benchmark `BT-V2-FRICTION-HS`: reference 0.026,
verdict `INDICATIVE_ASSUMED_INPUTS` (ratios 1.178 and 0.957).
Software identity for the tests: generate force, slip and torque with the mattress bite at
friction 0.027 on the battery-foil case pass; the identification must return 0.027 three times
(`1e-3` relative), `consistent`, and a flow-stress scale of 1.000 (`1e-3`).

### Budget
One record with all three quantities: at most 42 solves; under 3 s with the mattress bite,
under 10 s with the half-space bite. Report the measured times.

### Tests (`tests/test_band_friction_identification.py`, coarse numerics)
The identity above for the mattress and the half-space model; the two exponents of the three
cases of "Why" with the half-space model (`1e-3` after pinning) and the weak-slip flag on the
published foil case; a record with a slip the model
cannot reach gives `NOT_FOUND` and the flag; two records at two speeds give a slope and, with
tribology, a contact friction per record that reproduces its friction when fed to package 6's
closure (`1e-6`), and the worked value above; validation messages; `not_supplied`; every hypothesis, score and bite identical with
and without records; report block renders and escapes. `tests/test_benchmarks.py`:
`BT-V2-FRICTION-HS`.

### Documentation
Guide: new 8.5 "Friction from load, torque and forward slip" (method, the three single-quantity
values and what their disagreement means, which of force and slip carries the friction
information in which regime (the table of "Why"), the BT-V2 numbers, how to log a record: steady
window
of 5-10 s, forward slip to 0.1 % absolute, section 7.4 of the study); 3.3 pointer; 5.3; 12; 13;
14. Gap study section 11: BT-G6 `ROUTINE_ADDED` (friction distribution parameter and BT-V9 not
done: that table has no load, flow stress or tension values).

### Must not change
Artifacts: additive (`inputs.measurement.pass_records` null; `process.friction_identification`
not supplied). No scenario gets records.

### Do not
- Do not apply an identified friction to any pass, lever or evidence item.
- Do not set `calibrated` true.
- Do not add a forward-slip formula.

---

## Package 8 — Flow stress: rate, temperature, law forms, fit to pass strengths (B1, B2)

### Why
B1 (X1; TM-LB1 EX, TM-LB10 EX, PT-T31, PT-T39): rate sensitivity is zero and there is no
temperature term; a measurement on 16 um 1235-H18 foil gives m about 0.027 over 1e-5 to
1e-2 /s; 1100-H18 loses 12 % between room temperature and 100 C. The two partly cancel at
rolling conditions "by an unknown amount". B2 (X2; TM-LB2 EX, TM-LB4 EX): the sign of the late
hardening slope differs by alloy group; the law form allows only a positive slope. The alloy
group table is SPEC17 package 3 (B3). No fitted parameter set for any alloy at rolling rate
exists in the reports: this package builds law forms, a fit routine and reporting, and ships no
new default numbers. The research note looked for large-strain flow stress of 1xxx / 8xxx foil
alloys and did not find it (its section 4); what it found is a logarithmic rate law in a paper
on other alloys (E10 EX). That law is NOT added: one more form without a parameter set for a
foil alloy adds nothing a user can enter (open decision 10).

### Design

**A. Rate and temperature factor** (`bite_tribology.py`):
```python
@dataclass(frozen=True)
class RateTemperatureFactor:
    rate_sensitivity: float                  # m at the reference temperature, [0, 0.2]
    reference_strain_rate_per_s: float       # (1e-8, 1e6]
    temperature_coefficient_per_k: float     # c_T, [0, 0.01]
    reference_temperature_k: float           # [250, 700]
    rate_sensitivity_slope_per_k: float = 0.0   # dm/dT, [0, 0.002]
    provenance: str = ''
    def factor(self, strain_rate_per_s, temperature_k) -> float
def mean_bite_strain_rate_per_s(exit_speed_m_s, contact_length_m, entry_thickness_m, exit_thickness_m)
```
`factor = (rate/rate_ref)^m(T) * (1 - c_T*(T - T_ref))`, `m(T) = m + slope*(T - T_ref)`, floored
at `m >= 0` [form: TM report gap B1, "as the minimum"]; `ValueError` when the factor is not in
`[0.2, 5]`. `mean rate = (u/l_d)*ln(h0/h1)` [TM gap B1]. No default instance. The numbers a user
may enter, each with its tag, go into the guide and into `band_products.alloy_group_reference()`
context, not into code defaults: m about 0.027 (16 um 1235-H18, 1e-5 to 1e-2 /s) [TM-LB1 EX];
m 0.04 at 100 C and 0.07 at 200 C (1050-H14, slow tests) [TM-LB10 EX]; `c_T` 0.0015 to 0.0019 /K
`[D from PT-T31, PT-T39: 165 -> 145 MPa and 150 -> 130 MPa between about 20 and 100 C,
165 -> 125 MPa at 150 C]` (the report states 0.15-0.3 %/K).

Case key `hardening.rate_temperature` (optional third argument of `keys('hardening', ...)`;
null by default): the five numbers, `provenance` (required), `use_rate_temperature` (bool,
required). `band_process.flow_stress_section` adds to every pass row, when the key is given:
`strain_rate_per_s` with `contact_length_m = sqrt(R*(h0 - h1))` (the undeformed arc
`[D, SPEC18: avoids a fixed point with the bite; the rate enters to the power m]`, flag
`STRAIN_RATE_FROM_UNDEFORMED_ARC`), `bite_temperature_k` = `tribology.strip_entry_temperature_k
+ 0.5*strip_heat_fraction*w_pl/(rho*c)` with `w_pl` from the unfactored flow stress
`[D, SPEC18: mid-bite strip temperature]` (reference temperature and flag
`BITE_TEMPERATURE_NOT_AVAILABLE_REFERENCE_USED` without tribology), `rate_factor`,
`temperature_factor`, `rate_temperature_factor`, `flow_stress_with_rate_temperature_pa`.
With `use_rate_temperature` true `apply_flow_stress` uses the factored value (this needs
`use_computed_flow_stress` true as well; otherwise `ValueError('hardening.rate_temperature.
use_rate_temperature needs use_computed_flow_stress')`). Flags `FLOW_STRESS_RATE_TEMPERATURE_
FACTOR_APPLIED`, `RATE_SENSITIVITY_EXTRAPOLATED_BEYOND_MEASURED_RATES` when the pass rate
exceeds `1e-2 /s` times 100 (the measured range ends at 1e-2 /s [TM-LB1 EX]; rolling rates are
five decades higher: the flag is set on every real pass, by design). `schedule_flow_stress`
itself is unchanged; its flag `STRAIN_RATE_SENSITIVITY_IGNORED` stays in its own result.

**B. Law forms** (`bite_tribology.py`, `band_process.py`):
- `VoceHardening.stage_iv_slope_pa` may be negative (lower bound `-5e9`); `validate` then
  requires `stress(e) > 0` for `e` in `[0, 10]` (check at 0, 10 and the stationary point) and
  the schedule adds the flag `NEGATIVE_LATE_HARDENING_SLOPE_WORK_SOFTENING`
  (purified-matrix Al-Fe and high-purity grades beyond 80 % reduction [TM-LB2 EX]).
  `band_process.validate_hardening` currently passes `nonnegative=True` for every law key: drop
  it for `stage_iv_slope_pa` only.
- `TomeVoceHardening(saturation_scale_pa, stage_iv_slope_pa, initial_hardening_rate_pa,
  provenance)`: `sigma = (s_v + th4*eps)*(1 - exp(-th0*eps/s_v))` [form: TM-LB4 EX];
  `s_v > 0`, `th0 > 0`, `th4` in `[-5e9, 5e10]`, same positivity rule; `mean_stress(a, b)` by
  composite Simpson with 64 panels `[D]` (a test bounds its error against 512 panels at 1e-9
  relative). Law id `'tome_voce'` in `HARDENING_LAW_KEYS` with keys `saturation_scale_pa`,
  `stage_iv_slope_pa`, `initial_hardening_rate_pa`; `schedule_flow_stress` accepts it
  (`law_type` `'tome_voce_stage_iv'`). G'4: `HARDENING_WORDS['tome_voce'] = 'Voce law with late
  slope (Tome form)'` and two questions (`tome_scale`, `tome_rate`, MPa; `stage_iv_slope_pa` is
  shared with the Voce question, whose wording becomes "late hardening slope (negative for work
  softening)").
- Nothing selects a law by alloy group automatically. `flow_stress_section` adds
  `alloy_group_context`: the row of SPEC17's `band_products.alloy_group_reference()` that
  matches `material.alloy` when one does (the table's own matching, else null), and the fixed
  sentence of X2.

**C. Fit to pass strengths** (`bite_tribology.py`):
```python
def fit_voce_to_pass_strengths(gauges_m, strengths_pa, *, reference_thickness_m,
                               prior_equivalent_strain=0.0, strength_is='as_rolled_tensile') -> dict
```
`eps_i = prior + (2/sqrt(3))*ln(h_ref/h_i)`. For each of 60 values of `eps_c`, geometric from
0.05 to 5, the model `s0 + d*(1 - exp(-eps/eps_c)) + th4*eps` is linear in `(s0, d, th4)`:
solve the 3 x 3 normal equations (Gaussian elimination with pivoting; `th4` fixed to 0 with 3
points; `ValueError` below 3 points or for non-decreasing gauges); keep the `eps_c` with the
smallest sum of squares, refine once by a parabola through its neighbours `[D, SPEC18]`.
Returns the `VoceHardening` parameters (`saturation = s0 + d`), residuals, RMS, the sign of
`th4`, flags `FIT_TO_ENTERED_STRENGTHS_NOT_VERIFIED`, `FIT_UNDERDETERMINED_FEWER_THAN_5_POINTS`,
`TENSILE_STRENGTH_USED_AS_FLOW_STRESS` (for `strength_is='as_rolled_tensile'`: the as-rolled
tensile strength of a hard temper is taken as the flow stress at that strain, an assumption
`[D]`), `NEGATIVE_LATE_HARDENING_SLOPE_WORK_SOFTENING`. CLI:
`python -m physicroll.band_cli --fit-hardening FILE.json` (`{"gauges_m", "strengths_pa",
"reference_thickness_m", "prior_equivalent_strain"}`), printing the JSON result; nothing is
written into a case.

**D. The rate share of the chatter damping heuristic (B1; C3(c) itself is Phase 3).**
Derivation for the docstring `[D, re-derived in SPEC18]`: the thickness strain rate in the bite
gains `-h_dot/h_mean` when the gap moves at `h_dot` (`h_mean = (h0 + h1)/2`), so
`d(eps_dot)/eps_dot = -h_dot*l_d/(h_mean*u*ln(h0/h1))`; `dY/Y = m*d(eps_dot)/eps_dot`;
`dF = F_Y*dY`. Hence a force term in phase with gap velocity

    F_hdot_rate = -F_Y*Y*m*l_d/(h_mean*u*ln(h0/h1))            (negative: damping)
    beta_rate   = F_hdot_rate*u/(F_h*l_d) = F_Y*Y*m/(Q*h_mean*ln(h0/h1))

with `F_Y = dF/dY` (from `flow_stress_sensitivity`, or `bite_extras` for a half-space bite) and
`Q = -F_h`. `beta_rate` is the transit fraction the rate sensitivity alone would justify, to be
read beside the heuristic `bite_damping_transit_fraction`. New key
`result['chatter']['rate_sensitivity_damping']`: `not_supplied` without
`hardening.rate_temperature`; else `{'rate_sensitivity', 'dforce_dgap_velocity_n_s_m',
'equivalent_transit_fraction', 'heuristic_transit_fraction', 'share_of_heuristic', 'formula',
'basis', 'note'}` with the note "reported only: the stability results use the heuristic
unchanged (gap C3 is not implemented)". `assemble_state_matrix` is NOT touched.

### Worked numbers
- `(1e-2/1e-5)^0.027 = 1.205036`: 160 MPa -> 192.806 MPa (the source reads "about 200").
- `(2.6e3/1e-3)^0.027 = 1.490062` (the report's "about 1.5").
- `c_T`: `(1 - 145/165)/80 = 1.5152e-3`, `(1 - 130/150)/80 = 1.6667e-3`,
  `(1 - 125/165)/130 = 1.8648e-3` /K.
- 10 m/s, contact length 2 mm, 30 -> 18 um: rate 2554.128 /s; with m 0.027 and reference
  1e-3 /s the rate factor is 1.489346; with `c_T` 0.0015 and 60 K above the reference the
  combined factor is 1.355305.
- Damping share at the published foil case (half-space values of package 4, strip spring
  80 GPa: `F'_K*K = 2.096218e-2*2.3e8 =
  4.8213e6 N/m`, `Q` 5.57561e11 Pa, `h_mean` 17.5 um, `ln(4/3)` 0.287682, m 0.027):
  `beta_rate = 0.046375`, 9.3 % of a heuristic 0.5.

### Tests
`tests/test_bite_tribology.py`: the five numbers above (`1e-6`); `m(T)` slope; factor limits;
negative slope accepted, positivity rule, flag; Tome form values against a hand evaluation
(`s_v` 150e6, `th4` 20e6, `th0` 2e9, eps 1: `170e6*(1 - exp(-13.3333)) = 169999724 Pa` to
1 Pa); Simpson against 512 panels; the fit recovers a synthetic Voce law from 6 exact points
(parameters to `1e-3` relative, including one with negative `th4`) and reports
underdetermination with 4. `tests/test_band_v2_sections.py`: rows with the factor; `use`
requires computed flow stress; with `use_rate_temperature` false nothing else in the result
differs; `chatter.rate_sensitivity_damping` equals the formula. `tests/test_band_plain.py`
passes with the new law and questions (round trips of every preset).

### Documentation
Guide 8.3: the factor, what is measured and where the measurement stops (five decades below
rolling rates), the worked numbers, "the net of rate and temperature at rolling conditions is
not known; enter both or neither", the law forms, the fit routine and its assumption, X1 and X2
answered. 11.4: the damping share paragraph. 5.3, 13, 14. `docs/thin-gauge-products.md` is
generated: regenerate only if `band_products` changes. Gap study section 11: B1
`REDUCED_MODEL_OPT_IN` (law form and reporting; no data at rolling rate; rate from the
undeformed arc), B2 `REDUCED_MODEL_OPT_IN` (forms and fit routine; no parameter set per alloy
group; no recovery term `d_sigma_rec(eps, T)`: the row gives no formula for it).

### Must not change
Artifacts: additive (`inputs.hardening.rate_temperature` null where a hardening section exists;
`chatter.rate_sensitivity_damping` not supplied). No scenario gets a factor. Every existing
hardening test passes untouched.

### Do not
- No default m or `c_T`; no automatic law per alloy group.
- Do not feed `F_hdot_rate` into any stability calculation.
- No Kocks-Mecking model, no recovery term, no anisotropy factor in the bite (B4 stays a table).

---
## Package 9 — Computed bite heat partition (A3, X4)

### Why
Row A3 (TM-LA1 to LA4 AB, TM-LA19 AB, PT-T34): the strip's share of the bite heat is a supplied
number; the modelled stripe height moves from 0.61 to 3.4 um over the published share range. The
row names a Tseng-type interface: strip thermally thin, roll a half-space over the contact time,
`q_roll = (T_strip - T_roll_s)/(1/h_c + sqrt(pi*t)/(2*e_roll))`, `h_c = k_oil/h_s`, friction heat
at the interface, plastic heat in the strip. X4: the sheet demo's share 0.84 has no source.

What the research note adds (its sections 3.2 and 5): the oil conductivity of the kerosine foil
base oil, 0.125 W/mK at ambient pressure ("assumed equal to" another oil by the source) and
0.25 W/mK in the nip after allowing for pressure [E6 FT]. Interface conductance correlations
were found only in part: a mixed-lubrication conductance model exists as a publisher preview
without its equations (E12 AB), the Tseng papers as abstracts (E14 AB), and the
Cooper-Mikic-Yovanovich correlation on teaching pages (E13 VP), where it is a correlation for
dry rough contacts at far lower pressure than a roll bite. None is coded: the film conductance
`k_oil/h` of the gap row stays the model, the two sourced conductivities bracket it, and the
guide names the three sources as not usable.

### Model `[D, re-derived in SPEC18; the row's series formula is its time-averaged form]`
One roll side, per unit contact area. `t_c = l_d/V_r` contact time [s]; `C_s = rho_c_strip*h1*
u1/(2*V_r)` strip heat capacity per roll side [J/m2K] (half the neutral thickness, so that the
energy carried out equals `rho_c*h1*u1*dT`); `e = sqrt(k*rho*c)` roll effusivity;
`g_p = P_pl/(2*l_d)`, `g_f = P_f/(2*l_d)` plastic and friction heat [W/m2], uniform over the
contact; `phi` = share of the friction heat released on the strip side of the film (0.5);
`h_c` interface conductance [W/m2K]; `T_e` strip entry and `T_r0` roll surface temperature at
bite entry.

    strip:        C_s*dT_s/dt = g_p + phi*g_f - h_c*(T_s - T_r)
    roll surface: q_r = h_c*(T_s - T_r) + (1 - phi)*g_f
                  T_r(t) = T_r0 + (1/(e*sqrt(pi)))*Int_0^t q_r(s)/sqrt(t - s) ds     (half-space)

Scheme: `n = 400` equal steps; `q_r` constant per step; exact half-space response at step ends,
`w_i = (2/(e*sqrt(pi)))*(sqrt((i+1)*dt) - sqrt(i*dt))`, `T_r,j = T_r0 + Sum_{k<=j} q_k*w_{j-k}`;
strip by backward Euler; the two linear equations of a step are solved in closed form
(`s23/heat.py`, function `partition`). Outputs: strip exit temperature `T_s(t_c)`,
`f_s = C_s*(T_s(t_c) - T_e)/((g_p + g_f)*t_c)`, roll share per roll `(1 - f_s)/2`, roll surface
temperature at bite exit. Strip conduction: when `strip_conductivity_w_mk` is given the
interface resistance gains `(h0 + h1)/(12*k_strip)` (a slab's mean-to-surface resistance,
`h_mean/2` over `3k`) and the Fourier number `k_strip*t_c/(rho_c_strip*(h_mean/2)^2)` is
reported; below 1 the flag `STRIP_NOT_THERMALLY_THIN_LUMPED_MODEL_INDICATIVE` is set.

Closed form for perfect contact and equal entry temperatures (the test target):
`T(t) = (g/e)*(2*sqrt(t/pi) - sqrt(tau)*(1 - exp(t/tau)*erfc(sqrt(t/tau))))`,
`tau = (C_s/e)^2`, strip share `C_s*T(t_c)/(g*t_c)` (Laplace transform of the two equations with
`h_c -> inf`; limits `g*t/C_s` for `t << tau` and the constant-flux half-space result minus
`C_s/e` for `t >> tau`). For `sqrt(t/tau) > 25` use `exp(x^2)*erfc(x) = (1 - 1/(2x^2))/(x*
sqrt(pi))`.

### Design
`bite_tribology.py`: `heat_partition(*, plastic_power_per_width_w_m,
friction_power_per_width_w_m, contact_length_m, roll_surface_speed_m_s, exit_thickness_m,
exit_speed_m_s, entry_thickness_m, strip_entry_temperature_k, roll_entry_surface_temperature_k,
interface_conductance_w_m2k, roll_conductivity_w_mk, roll_density_kg_m3,
roll_specific_heat_j_kgk, strip_volumetric_heat_capacity_j_m3k=ALUMINIUM_VOLUMETRIC_HEAT_
CAPACITY_J_M3K, strip_conductivity_w_mk=None, friction_heat_to_strip_side_fraction=0.5,
steps=400) -> dict` and `perfect_contact_strip_share(strip_capacity_j_m2k, roll_effusivity,
contact_time_s) -> float`. Result: `status` `'UNVALIDATED_COMPUTED_HEAT_PARTITION'`,
`strip_heat_fraction_computed`, `roll_heat_fraction_per_roll_computed`,
`strip_exit_temperature_k`, `roll_surface_exit_temperature_k`, `contact_time_s`,
`strip_capacity_j_m2k`, `roll_effusivity`, `interface_conductance_w_m2k`,
`roll_transient_resistance_m2k_w` (`sqrt(pi*t_c)/(2e)`), `gap_row_series_roll_flux_w_m2` (the
row's formula with the time-mean strip temperature of the solution, for comparison),
`perfect_contact_strip_share`, `fourier_number` (or null), `basis`, `flags`
(`HEAT_SHARE_OUTSIDE_0_1_TEMPERATURE_DIFFERENCE_DOMINATES` when `f_s` is outside `[0, 1]`: it is
reported as computed), `limitations` (uniform heat over the contact; one lumped strip
temperature; roll curvature neglected; no asperity conduction: the row's "asperity term" has no
formula in the reports; film thickness from the smooth inlet formula; not coupled back).

Engine: `band_process.heating_row` gets the pass's friction row (film thickness) and returns
`heat_partition` (the dict, or `not_supplied` with the reason: no tribology, no film, no bite).
Inputs: contact length and forward slip from the bite; `h_c` =
`tribology.interface_conductance_w_m2k` when given (new `TRIBOLOGY_OPTIONAL` key, `[1e3, 1e9]`;
published context 25-40 kW/m2K used in models, 7-800 measured [PT-T34]; question per G'4), else
`lubricant.effective_conductivity_w_mk()/film_thickness_m` [row A3; the default conductivity
0.13 W/mK is [M] in `bite_tribology.py` and stays; add to its basis text "published for a
kerosine foil base oil: 0.125 W/mK at ambient pressure, 0.25 W/mK in the nip [E6 FT]"]. The
result also carries `strip_heat_fraction_at_published_oil_conductivities`: the share recomputed
with 0.125 and with 0.25 W/mK at the same film (two more calls; only when the conductance comes
from the film); roll properties from `width_model.roll`
when present, else the defaults of `roll_thermal.RollThermalProperties` (basis text);
`T_r0` = `width_model.coolant_temperature_k`, else `tribology.inlet_temperature_k`, with the
basis in the result and the flag `ROLL_ENTRY_TEMPERATURE_ASSUMED_COOLANT_OR_OIL` (package 10
replaces it when a surface cycle exists).
New `TRIBOLOGY_OPTIONAL` key `use_computed_heat_partition` (bool or null, default false;
question per G'4: "Use the heat share the tool computes instead of the entered one?"). When
true: `pass_heating` is called with `strip_heat_fraction = min(1, max(0, f_s))` for that pass,
and `band_width`'s default roll heat fraction (today `(1 - tribology.strip_heat_fraction)/2`)
becomes the case pass's computed `(1 - f_s)/2`; basis strings say "computed"; flag
`STRIP_HEAT_FRACTION_COMPUTED_FROM_INTERFACE_MODEL` replaces
`STRIP_HEAT_FRACTION_SUPPLIED_NOT_COMPUTED`. When false: every existing number is unchanged and
the heating row gains `supplied_minus_computed_strip_heat_fraction`.
`band_thermal.heat_partition_consistency` (read it) reports the computed share beside the
supplied one. Report: one line per pass in the heating table of `_process_section` ("heat share
to the strip: entered 0.22, computed 0.23") and a `warn` sentence when they differ by more than
0.1.

### Worked numbers (`s23/heat.py`)
The thermal report's own check case: steel `k` 43 W/mK, `rho*c` 3.6e6 J/m3K (`e` 12441.86),
aluminium `rho*c` 2.43e6, 24 um, `t_c` 0.2 ms: `C_s` 29.16 J/m2K; `tau` 5.4929e-6 s; exact
strip share 0.162070 (roll side 0.837930); the report's capacity-ratio estimate gives 0.128
(0.872 to the rolls). Scheme: 0.162060 / 0.162069 / 0.162070 with 50 / 400 / 800 steps. With
`h_c = 0.13/70e-9 = 1.857e6 W/m2K`: 0.2254; with a 200 nm film 0.3352; with 40 kW/m2K 0.8775;
60 % plastic and 40 % friction heat at 70 nm: 0.2113. With the sourced conductivities
(`s23/v_fric2.py`): 0.125 W/mK: 0.2279 at 70 nm, 0.3414 at 200 nm; 0.25 W/mK: 0.1952 at 70 nm,
0.2553 at 200 nm. Roll transient resistance 1.0073e-6
m2K/W against 5.385e-7 for the 70 nm film. Sheet check, 0.25 mm and 0.4 ms, perfect contact,
lumped: 0.6063, Fourier number 2.42.

Benchmark `TM-LA19-HEAT-SPLIT` (function inputs: exit thickness 24 um, exit speed = roll surface
speed = 10 m/s, contact length 2 mm, roll `k` 43, density 7200, specific heat 500, equal entry
temperatures, heat 1 W/m of plastic work): rows for perfect contact (0.1621, interface
conductance 1e12), a 70 nm film at 0.125 W/mK (0.2279) and at 0.25 W/mK (0.1952), each against
the two ends of the measured strip share, 0.11 and 0.33 (MEASUREMENT, AB; gauge and speed not
in the abstract; each project value is one row per end, the label says which): verdict
`INDICATIVE_ASSUMED_INPUTS`, note "inside the measured range; film thickness and conductivity
are assumed".

### Tests
`tests/test_bite_tribology.py`: closed form against the scheme (`1e-5`); the ten numbers
(`1e-4`); energy balance (strip plus roll equals the input to `1e-9`); limits (`h_c -> 0`: share
1; equal temperatures and zero heat: no change); hotter roll than strip gives a share above 1
and the flag; validation. `tests/test_band_v2_sections.py`: heating rows carry the block; with
the option false the result without the new keys equals the result before the package (compare
`result_json` after deleting the new keys); with the option true the roll heat fraction of the
width model follows. `tests/test_band_plain.py` with the two questions.

### Documentation
Guide 8.2 (model, numbers, the two sourced oil conductivities and the three conductance sources
that could not be used, X4: "the entered 0.84 of the sheet demo is not supported; the
computed value for that pass is ..." read from the regenerated artifact), 3.12, 5.3, 13, 14.
Gap study section 11: A3 `REDUCED_MODEL_OPT_IN` (lumped strip; no asperity conductance; not
calibrated; not width-resolved), X4 `TEXT_CORRECTED`.

### Must not change
Artifacts: additive (`inputs.tribology` two null keys; `heat_partition` blocks and one
comparison key per heating row). The demos keep `use_computed_heat_partition` absent.

### Do not
- Do not change `strip_heat_fraction` of any scenario.
- Do not add an asperity conductance model, a contact-conductance correlation or a default
  interface conductance.
- Do not change `DEFAULT_OIL_CONDUCTIVITY_W_MK` (it would move the film's thermal factor in
  committed artifacts).
- Do not feed the computed strip temperature into the flow stress or the film (I1, Phase 2).

---

## Package 10 — Roll surface layer within one revolution (A4, G8; X5 in part)

### Why
Rows A4 and G8 (TM-LA6 AB, TM-LA7 EX, TM-LA26 AB, TM-LA27 AB, SS-S35, SS-S71): the roll model is
a circumferential mean; "the temperature the oil and the strip see at the bite is the surface
value after the last spray, not the mean"; the cyclic depth is below 4 % of the radius; on-line
models separate skin and bulk. The reports name two methods (a Fourier series in the angle; a
time-resolved "phase shift" method) and give neither in equations. A time-resolved periodic
layer is derived here.

### Model `[D, re-derived in SPEC18]`
One axial station, depth `y` below the surface, curvature neglected (layer depth << R):
`rho*c*dT/dt = k*d2T/dy2`; surface `-k*dT/dy = q(t) - h(t)*(T_s - T_sink(t))`, periodic with
the revolution time `t_rev = 2*pi*R/V_r`; at `y = D = 6*sqrt(a*t_rev)` (`a = k/(rho*c)`) the
temperature is the bulk model's steady temperature at that depth and station. The revolution is
a sequence of arcs, each with constant `q`, `h`, `T_sink`:

| arc | `q` | `h` | `T_sink` |
|---|---|---|---|
| bite, fraction `l_d/(2*pi*R)`, starts at angle 0 | `roll_heat_fraction_per_roll*bite_heat_per_width/l_d` under the strip, 0 outside | 0 | - |
| spray arc(s) | 0 | `background + spray_mean_htc*weight(z)*2*pi/phi` | coolant |
| backup-roll contact (optional) | 0 | supplied conductance | supplied backup surface temperature |
| everything else | 0 | `background_htc` | coolant |

`phi` = total wetted arc [rad]. The spray value is the footprint coefficient of SPEC17
package 3's identity, so the angular mean of `h` equals the mean model's
`background + spray_mean_htc*weight`.
Numerics (`s23/skin2.py`): 24 geometric cells, first cell `D/192`, growth ratio by bisection;
surface node eliminated by the flux balance (as `roll_thermal.py` does); backward Euler; each
arc cut into `max(8, ceil(360*fraction))` equal steps (so arc ends fall on step ends); march
revolutions from a uniform start until the surface history changes by less than `1e-3 K`
(limit 400 revolutions, else `ValueError`).
Linearity (exact for the scheme): for a fixed pattern of `h`,
`T_s(theta) - T_c = q_b*A(theta) + (T_D - T_c)*B(theta)`; with a backup contact a third unit
solution multiplies `(T_backup - T_c)`. The engine computes `A` and `B` for 9 values of the
spray weight spanning the profile's range (plus weight 0 when present) and interpolates
linearly in the weight for every axial station `[D]`.

Closed forms used as tests `[D; classical half-space results]`: a flux `q1*cos(omega*t)` gives a
surface amplitude `q1/(e*sqrt(omega))` lagging by 45 degrees (`T = Re[q1*exp(i*omega*t)/
(e*sqrt(i*omega))]`); a constant flux `q` for a time `t` raises the surface by
`2*q*sqrt(t)/(sqrt(pi)*e)`; after a step in `h` the surface of a half-space covers the fraction
`1 - exp(s)*erfc(sqrt(s))` of its final change, `s = h^2*t/(k*rho*c)`, i.e. 0.5724 at
`t* = k*rho*c/h^2`.

### Design
New module `physicroll/roll_skin.py`: `surface_cycle(*, conductivity_w_mk,
volumetric_heat_capacity_j_m3k, revolution_time_s, arcs, deep_temperature_k, ...) -> dict`
(`arcs`: list of `{'kind', 'start_fraction', 'end_fraction', 'heat_flux_w_m2', 'htc_w_m2k',
'sink_temperature_k'}`, contiguous from 0 to 1); `unit_solutions(...)`;
`time_scales(...)`; `STATUS = 'UNVALIDATED_ROLL_SURFACE_CYCLE'`. Cycle result:
`time_fraction`, `surface_temperature_k` (per step end), `bite_entry_temperature_k` (the value
at the end of the revolution), `bite_exit_temperature_k`, `minimum_temperature_k`,
`mean_surface_temperature_k` (time weighted), `swing_k`, `mean_flux_into_roll_w_m2`,
`deep_flux_w_m2`, `mean_htc_w_m2k`, `effective_mean_htc_w_m2k`
(`<h*(T_s - T_c)>/(<T_s> - T_c)`), `mean_coefficient_ratio`, `skin_depth_m`
(`sqrt(2a/omega)`), `layer_depth_m`, `revolutions`, `flags`, `limitations`.

Case key `width_model.circumferential_layout` (`WIDTH_DEFAULTS` null):
`{"spray_arcs": [{"start_rad", "arc_rad"}], "backup_contact": null | {"start_rad", "arc_rad",
"conductance_w_m2k", "backup_surface_temperature_k"}, "provenance"}`; angles in the direction
of rotation from the bite exit, in `[0, 2*pi)`; arcs sorted, not overlapping each other or the
bite; 1 to 6 spray arcs; when `width_model.spray_wetted_arc_rad` (SPEC17 package 3) is given it
must equal the sum of the spray arcs to `1e-6 rad` ("width_model.circumferential_layout: the
spray arcs must add up to width_model.spray_wetted_arc_rad"). Messages
"width_model.circumferential_layout.<key> ...".

Section `width.roll_surface_cycle` (`band_width.py`, after the steady thermal block; needs the
steady thermal solution, the case-pass bite and the layout, else `not_supplied` or
`NOT_ASSESSABLE` with the reason): `z_m`, and per axial station `bite_entry_temperature_k`,
`mean_surface_temperature_k`, `swing_k`, `mean_coefficient_ratio`,
`mean_model_surface_temperature_k` (the steady model's own surface value) and their difference;
`cycles` at three stations (strip centre, the station of the largest steady stripe, the first
station under a healthy nozzle): the full histories; `time_scales`:
`per_revolution_s`, `skin_depth_m`, `surface_film_s` (`k*rho*c/h_mean^2`,
`h_mean = background + spray_mean_htc`), `bulk_s` (`rho*c*R/(2*h_mean)`, the lumped limit of the
`roll_thermal.py` docstring), and for every entry of `width_model.events` its duration divided
by each scale; `basis`; `flags` (`ROLL_SURFACE_CYCLE_COMPUTED`,
`CIRCUMFERENTIAL_MEAN_COEFFICIENT_BIASED` when a `mean_coefficient_ratio` differs from 1 by
more than 0.05, with the number); `limitations`: one-way (the cycle does not change the bulk
solution, the stripe heights or the shape); bulk field from the circumferential-mean model;
uniform flux in the bite; no backup contact unless supplied; wipers and oil carry-over not
modelled; the three time scales are the model's own, the published "three thermal effects" have
no numbers in the abstract read [TM-LA9 AB].
Package 9 link: when the section exists, the case pass's heat partition takes `T_r0` =
`bite_entry_temperature_k` at the strip centre (basis text; one pass, no iteration, flag
`ROLL_ENTRY_TEMPERATURE_FROM_SURFACE_CYCLE`). This changes computed (reported) values only.
Report: in `_width_section`, block "Roll surface within one revolution": a chart of the three
cycles against angle, a table (station, before the bite, after the bite, lowest, mean, mean of
the model), the time-scale line, the bias sentence.

### Worked numbers (`s23/skin2.py`, `s23/heat.py`; `k` 40, `rho*c` 7850*470, R 0.135 m, 10 m/s)
`t_rev` 0.0848230 s, `omega` 74.0741 rad/s, `e` 12148.25, skin depth 0.5410 mm.
Sinusoid `q1` 1e5 W/m2: exact amplitude 0.95643 K; scheme 0.9585 K, lag 45.0 degrees, 10
revolutions. Constant flux 1e7 W/m2 for 0.2 ms: 13.136 K. `t*` at 3400 W/m2K: 12.766 s (13.39 s
with the report's steel constants). Cycle: bite 2 mm with 1e7 W/m2, spray arc from 90 to 150
degrees at 20450 W/m2K (the footprint value of SPEC17 package 3's example), background 50,
coolant 313.15 K, deep 330 K: before the bite 327.154 K, after it 340.55-340.68 K (rise 13.39
to 13.53 K with 8 to 32 bite steps), lowest 325.05 K, mean 327.06 K, mean flux into the roll
-20533 W/m2, 60 revolutions, 0.14 s. Mean coefficient 3450 W/m2K, effective 3172.3, ratio
0.9195: the circumferential-mean model over-states the cooling of this layout by 8 %.
Superposition: `B` at bite entry 0.713887, `A` 1.966020 K per 1e7 W/m2:
`313.15 + 0.713887*16.85 + 1.966020 = 327.145 K`.

### Budget
Unit solutions for 9 weights: under 3 s. A `diagnose` without the layout: unchanged.

### Tests (`tests/test_roll_skin.py`)
Sinusoid amplitude within 0.5 % and lag within 1 degree; constant-flux rise within 4 % with the
default grid and within 1.5 % with 48 cells; step response 0.5724 at `t*` within 0.5 %
(one transient with constant `h` from a uniform start, layer depth `6*sqrt(a*t*)`; planner 0.57264
with 24 cells and 360 steps, `s23/skin3.py`);
energy: mean surface flux equals the deep flux within 1.5 % at convergence (planner 0.7 %); arc-weighted mean
of `h`; superposition to `2e-3 K`; the cycle numbers above (after pinning); validation of arcs.
`tests/test_band_lengthwise.py` or a new class: a coarse width case with a layout returns the
section; the bulk results, stripes, shape and every hypothesis are identical with and without
it; `not_supplied` without it; the wetted-arc consistency error.

### Documentation
Guide: new 7.10 "Roll surface within one revolution" (model, closed forms, numbers from the
regenerated demo, the bias of the mean coefficient and what it means for X3, the three time
scales beside the open 20 s question: X5 gains "the surface-film scale of this model is N s";
not a resolution of that question, A6 is not built); 7.1 pointer; 5.3 (how to measure the
angles: header position and fan width on the drawing, direction of rotation); 12, 13, 14.
Template: key with null. Gap study section 11: A4 and G8 `REDUCED_MODEL_OPT_IN` (one-way skin
layer; no feedback to the bulk; no backup contact model), X5 `TEXT_CORRECTED`.

### Must not change
Artifacts: additive. Open decision 6 says whether the battery-foil demo gets a layout; the
planner's choice is NO (no plant value for the angles).

### Do not
- Do not correct the bulk model's coefficient with `mean_coefficient_ratio`.
- Do not pass the bite-entry temperature to viscosity, film or flow stress (A2, Phase 2).
- No emulation of the plant's step test (A6).

---

## Package 11 — Spray coefficient calibration routine (A5, the routine)

### Why
Row A5 (TM-LA8 EX, TM-LA37 EX): "a calibration routine that fits h to a roll cool-down or to a
measured thermal camber". Section 7.4 of the study names the measurement: a barrel temperature
scan within 60 s of roll-out, or the camber after a pass. The basis question (X3) stays as
SPEC17 package 3 left it; the fitted number is a circumferential mean by construction.

### Design
`band_thermal.calibrate_spray_coefficient(case, calibration, *, numerics='quick') -> dict`.
`calibration` (a JSON object; also accepted as `width_model.spray_calibration`, `WIDTH_DEFAULTS`
null, validated by `validate_width_model`, used ONLY by this routine):

| key | rule |
|---|---|
| `kind` | `'roll_surface_temperature_after_stop'` or `'thermal_camber'` |
| `positions_m` | >= 5 strictly increasing positions on the barrel |
| `values` | same length; kelvin in [250, 700], or radius growth in metres in [-1e-3, 1e-3] |
| `seconds_after_stop` | first kind only, [0, 3600] |
| `search_range_w_m2k` | two numbers, `100 <= lo < hi <= 1e5`; default `[500, 20000]` |
| `provenance` | nonempty |

Model evaluation for a trial coefficient `h`: the case's steady thermal problem exactly as
`band_width` builds it (read how it builds `RollThermalProperties`, `SprayHeader` and the
steady `ThermalSegment`; reuse that code through one helper so both stay equal) with
`spray_mean_htc_w_m2k = h`; first kind: then one `roll_thermal.simulate` segment of
`seconds_after_stop` with zero bite heat and all nozzle levels 0, started from the steady field,
surface temperature interpolated to the positions; second kind: steady `radius_growth_m` at the
positions. Misfit: RMS of model minus measurement; for the camber both profiles are reduced by
their own mean over the positions (the reference of a measured camber is unknown) `[D]`.
Search `[D, SPEC18]`: 9 geometric values over the range, then golden section in `ln h` inside
the best bracket until the bracket ratio is below 1.02 (at most 12 more evaluations); a minimum
at an end of the range is reported as `AT_SEARCH_LIMIT`, not as a fit.
Result: `status` `'CALIBRATION_FIT_TO_ENTERED_MEASUREMENT_NOT_VALIDATED'`,
`fitted_spray_mean_htc_w_m2k`, `misfit_rms`, `misfit_unit`, `misfit_curve` (every evaluation),
`range_within_10_percent_of_minimum_w_m2k`, `case_spray_mean_htc_w_m2k`,
`ratio_fitted_to_case`, `basis` ("circumferential mean under a healthy header; see the spray
basis statement of the thermal check"), `footprint_equivalent_w_m2k` when
`spray_wetted_arc_rad` is given, `numerics`, `evaluations`, `flags`, `limitations` (one
coefficient for the whole header; background coefficient, heat share and bite heat taken from
the case, so their errors go into the fit; end effects not modelled; the after-stop phase uses
the background coefficient only), `how_to_use` ("enter the value as
width_model.spray_header.spray_mean_htc_w_m2k; nothing is changed automatically").
CLI: `python -m physicroll.band_cli CASE.json --calibrate-spray [FILE.json]` (the file when the
case has no `spray_calibration`), printing the JSON; `diagnose` never runs the routine and its
result is unchanged by the key except `inputs`.

Benchmark entry `TM-LA8-SPRAY-FIT`: 17.5-22 kW/m2K fitted to measured cambers of a hot
aluminium mill with water or emulsion [TM-LA8 EX]: `REFERENCE_ONLY_INPUTS_NOT_RECORDED`.

### Tests (`tests/test_band_spray_calibration.py`; a short roll, 20 mm cells, 6 radial cells)
Twin test: the "measurement" is the model at 3400 W/m2K; both kinds recover it within 2 %; the
misfit curve has its minimum there; a measurement the range cannot reach reports
`AT_SEARCH_LIMIT`; a uniform header-off scan long after the stop gives a wide
`range_within_10_percent`; validation messages; `diagnose` with and without the key equal
outside `inputs`. Module time under 40 s (measure one steady solve first and size the roll to
fit).

### Budget
Battery-foil roll, quick numerics: under 60 s for either kind. Report the time per evaluation.

### Documentation
Guide 3.12 and 7.1 (how to take the scan, what the routine holds fixed, how to read a flat
misfit curve), 4 (the CLI line), 5.3, 13, 14. Gap study section 11: A5 row extended to
`ROUTINE_ADDED` (flow scaling, footprint entry and tapered fan profile not built; basis open).

### Must not change
Artifacts: additive (`inputs.width_model.spray_calibration` null).

### Do not
- Do not write a fitted value into a case or a scenario.
- Do not fit more than the one coefficient.

---

## Package 12 — Guided app (plant-facing inputs and plain words for packages 4 to 11)

Read SPEC16, SPEC17 package 9, `docs/band-app.md` and the three test modules first. The app
invariants of SPEC17 package 9 hold unchanged (plain wording, numbers only from the result,
drawn equals simulated, "Don't know" stays null, trust rule unchanged; none of the new inputs
is "ask first").

**Questions** (`band_plain.py`; engine packages already added those G'4 forces; here the rest
and the wording pass). New group "Measured rolling data" in step `mill`:

| id | key | kind, unit | wording |
|---|---|---|---|
| `pass_records` | `measurement.pass_records` | list: label, force (kN), forward slip (%), torque per roll (kN m), strip speed (m/min) | Rolling force and forward slip you have logged for this pass |
| `oil_viscosity_points` | `tribology.lubricant.viscosity_table` | list: temperature (degC), viscosity (mPa s) | Oil viscosity at two or three temperatures, from the data sheet |
| `friction_law` | `tribology.friction_closure.model` | choice | Which friction law to show beside your friction value |
| `closure_contact_friction` | `tribology.friction_closure.contact_friction` | number | Friction where metal touches metal (needed for the second friction law) |
| `oil_pressure_law`, `oil_roelands_index` | `tribology.lubricant.pressure_law`, `roelands_z` | choice, number | How the oil thickens under pressure |
| `rate_sensitivity`, `rate_reference`, `temperature_softening`, `rate_reference_temperature`, `use_rate_temperature` | `hardening.rate_temperature.*` | number, 1/s, percent per K, degC, yesno | How much the metal's strength rises with speed and falls with temperature |
| `spray_arcs` | `width_model.circumferential_layout.spray_arcs` | list: start (deg after the roll gap), length (deg) | Where around the roll the sprays hit |
| `roll_scan_kind`, `roll_scan`, `roll_scan_delay` | `width_model.spray_calibration.*` | choice, list, s | Roll temperature along the barrel after a stop |

Help texts state where a value comes from and give the published numbers with their status in
plain words ("one laboratory measurement on 16 um foil: 0.027, at speeds far below rolling").
New units if absent: `mPa s`, `kN m`, `percent_per_k`, `1/s`. List questions that map to
parallel arrays or lists of objects need the two-way conversion and a round-trip test
(`test_round_trip_case_answers_case` for every preset). Eyring stress (value and share of
pressure), limiting shear stress (value and share of pressure), the two closure curves, the
valley model, backup contact and the shear cap stay in "Model settings" with expert wording; the
curves are shown as the published points and are not editable on the page in this block (a case
file can carry others). Help of `closure_contact_friction`: "Published values run from about
0.01 to 0.1. The tool cannot choose one for you; your logged force or forward slip can (see
'Measured rolling data')."

**Summary views** (`plain_summary`; numbers from the result only; extend the view tuple of
`test_summaries_build_and_keep_engine_numbers`):
- `roll_gap_model_view`: which roll-gap model ran and, when a foil model ran, the fixed
  sentence "On the one published foil case the half-space model gives a load of {a} and the
  standard foil model {b}. The published figure is 118, but it depends on a numerical detail
  the paper does not state: the same published equations give {c} to {d}." (`a`: the rigid-strip
  row, `c`, `d`: the 40 um and 2.5 um rows of `benchmarks.run_case('BT-V1-HS')`; `b` from
  `('BT-V1')`; rounded to whole numbers, not typed; no ratio is shown).
- `friction_records_view`: per record "Your force of {F} kN corresponds to a friction of {mu}
  in this model; your forward slip to {mu2}." and "They agree / do not agree within the stated
  measuring error." When the result carries the flag of a weakly determined slip value: "In
  this pass the forward slip hardly depends on friction; rely on the force." Fixed sentence:
  "Nothing was changed; enter the value yourself if you want to use it."
- `heat_share_view`: "You entered that {a} % of the heat stays in the strip; the tool's own
  estimate is {b} %."
- `roll_surface_view`: "Just before the roll gap the roll surface is at {x} C at the band
  position and {y} C beside it; the average the model works with is {z} C."
- `flow_stress_view`: the factor per pass and the sentence that the speed effect is an
  extrapolation.
- `FLAGS`: check every flag of packages 4 to 11; `GLOSSARY`: "forward slip", "heat share",
  "film ratio" if absent.

**Page**: the new group collapsed by default; one card each for the friction records and the
roll surface (a small line chart of the three cycles against angle, drawn from the result);
the calibration routine is NOT run from the page in this block (no new server route; open
decision 7): the roll-scan questions are stored in the case and the page says how to run the
routine from the command line.

**Tests**: question-table invariants; unit round trips; preset round trips; summaries of the
regenerated artifacts (numbers in result, no engine tokens, no forbidden words, flags
described); partial cases keep the views unavailable; a run with pass records stores and
reopens. **Docs**: `docs/band-app.md`; README one sentence. **Must not change**: no engine
module, scenario or artifact.

**Do not**: no physics in `band_plain.py` or the page; no sentence that turns an identified
friction or a computed heat share into advice; never "validated".

---

## 3. Open decisions (the planner's choice is implemented unless the owner says otherwise)

1. **Is the reduced half-space bite worth shipping?** Choice: yes, opt-in. It reproduces the
   published regime boundary and load exponent, removes the rejection at friction above 0.05,
   returns the two derivatives Phase 2 needs, and on the published case it lies inside the
   family the printed model itself spans (88.9 to 92.9 against 78 to 134). What it does not do:
   the longitudinal elastic equations (10)-(14), stress inside the no-slip zone, regime III.
2. **Default bite model.** Choice: unchanged (`'hitchcock'`; the demos keep `'auto'` with the
   mattress fallback). A switch would move every foil force (plus 43 % to plus 111 % on the
   demo's four foil passes), strip stiffness, slip, heat and through them the scores, on the
   strength of a model whose published reference is not a defined number. If the owner wants
   the switch after seeing the comparison of package 4: it moves all battery-foil artifact
   numbers that depend on the bite (`bite`, `chatter`, `levers`, `schedule_sweep`,
   `width.shape`, `gauge_trend`, `thermal_check` pass rows, `process`), every product-survey
   row whose bite is a mattress bite (18 mattress derivations in a survey run today), and the
   pinned expectations of `tests/test_band_foil.py`, `test_band_extended_domain.py`,
   `test_band_survey*.py` and `test_band_plain.py` (not counted here); it needs its own brief.
3. **How the bite ends are closed** (packages 2, 3). Choice: contact end zones (the strip leaves
   where the pressure has fallen to zero), which gives a grid-converged load. Alternative: the
   printed pressure step with a fixed end length; 5 um would return the caption value 118. Not
   chosen: it is tuning a numerical length to one number, and those solutions thicken the strip
   before the exit.
4. **Strip thickness spring** (package 2). Choice: keep it, as the planner's own addition, with
   the material's plane-strain modulus; the benchmark carries a rigid-strip row beside it
   (88.86 against 92.94). Alternative: a strip rigid in thickness, as the source assumes; then
   the entry contact zone has no length and the entry needs the pressure-step condition of
   decision 3.
5. **Admissibility tolerance of the six-zone structure** (package 3): friction-hill bounds
   within `0.02*K`. Analyst choice; the worst value seen on an accepted solution is `0.0134*K`.
   A tighter value rejects passes at the regime boundary on the default grid.
6. **Friction closure: required contact friction, published curve as the default shape**
   (package 6). Choice: no default for the contact friction (sources: 0.013 to 0.1). Alternative:
   0.09 as before, which gives a friction of 0.063 at the demo's film ratio where the entered
   value is 0.03.
7. **Inlet analysis with asperity crushing** (BT-G3 in full): not built. Choice: defer until
   chapter 4 of the thesis (E6) and the 1988 / 1990 papers are read again against a prototype
   that reproduces the five published points; the transcribed pieces do not (package 6, "Why").
   The owner can settle this by supplying those texts.
8. **Roelands index** (package 5): from the low-pressure slope unless entered. Known to be low
   by a factor 12 to 30 at bite pressure for the one oil with data. Alternative: require the
   index. Chosen as it is because the law is opt-in and the result carries the table.
9. **Where the friction heat is released** (package 9): half on each side of the film. With a
   70 nm film and 40 % friction heat the strip share is 0.197 with all of it on the roll side,
   0.211 with half, 0.225 with all of it on the strip side (oil conductivity 0.13 W/mK).
10. **Logarithmic rate law of E10** (package 8): not added. No parameter set for a foil alloy
    exists; the power-law factor stays the only form.
11. **New inputs in the committed demos.** Choice: none (no pass records, layout, rate factor,
    new closure or computed heat share in any scenario); the guide shows the features on scratch
    copies of the battery-foil case and quotes numbers produced by tests. Alternative: one new
    scenario file "battery foil, Phase 1 models" with its own artifact pair (about 100 s to
    regenerate).
12. **Calibration from the app** (package 12): command line only in this block. Alternative: a
    new server route and a progress card; about 300 more lines and a new invariant for the app.
13. **Strain rate from the undeformed arc** (package 8): avoids a fixed point between flow
    stress and bite. On the demo's foil passes the half-space contact is 1.6 to 4.3 times the
    undeformed arc, which lowers the rate factor by 1 to 4 % at m = 0.027. Alternative: iterate
    with the bite (two more derivations per pass).
14. **Friction ladder of the cold start** (package 3): 0.03, 0.02, 0.01. Analyst choice from the
    domain in which the mattress solver accepts foil passes.
15. **Reference speed of the steel chatter case** (package 1): the paper's 5.81 m/s is recorded
    with both readings (exit speed of the stand modelled, or strip speed between the stands,
    which makes 8.715 m/s at the exit); the case verdict is `INDICATIVE_ASSUMED_INPUTS` either
    way. The paper's text would settle it.

## 4. Risks: where an exactly implemented result could still mislead a plant user

| risk | mitigation built into the outputs |
|---|---|
| "Half-space" sounds like the published model. It is a reduced form (no longitudinal elastic equations, own end closure), and nobody knows its error on a real foil pass. | The model word everywhere is "reduced half-space"; status `UNVALIDATED_REDUCED_HALF_SPACE_FOIL_BITE`; the benchmark verdict is `REFERENCE_NOT_GRID_INDEPENDENT`, never an agreement. |
| A reader sees 88.9 against 118 and concludes the new model is 25 % low, or sees "the reference is not defined" and concludes the model is right. | The fixed case note and the app sentence give the family (78 to 134) and what the solver's value equals in it; no ratio is shown in the app; the test docstring says what passing means. |
| The strip thickness spring moves the load by 4.6 % on the published case and is not part of the source. | Stated in the module docstring and result (`strip_plane_strain_modulus_pa` in the inputs); both benchmark rows. |
| Two foil models now disagree by a factor of up to 2 in force and more in stiffness. A user may pick the one whose answer he likes. | `bite_model_comparison` prints both with the same friction; guide 3.3 says that the spread is a measure of what is not known, and that friction (exponent about 3) is the larger unknown. |
| With the half-space bite and the entered friction 0.03 the 18 um and 12 um loads leave the trade range (3.2 and 10 kN/mm against 0.9-2.3). Read alone this looks like a mill overload. | The existing credibility marks apply; guide 3.3 gives the friction that would bring F2 back (about 0.027) and points to package 7. |
| The shear cap lets the solver return numbers at friction 0.10 that no mill could run (48 kN/mm, a contact length of 12 mm, peak pressure 34 times the plane-strain strength on the example of package 3). | Flags `SHEAR_CAP_ACTIVE`, `PEAK_PRESSURE_ABOVE_16_PLANE_STRAIN_YIELD`; the guide repeats X24: a nominal 0.10 is not the published case. |
| An identified friction looks like a measurement. It absorbs every error of the bite model (including the end closure), of the entered flow stress and of the closed-gap load share that is not modelled. | Status `IDENTIFIED_FROM_ENTERED_RECORDS_NOT_VERIFIED`; `calibrated` false; three single-quantity values side by side with the exponents that say which quantity carries the information; never applied. |
| The new friction law has a published shape, so its level looks published too. The level is the entered contact friction: 0.09 gives 0.063 at the demo's film ratio, 0.0135 gives 0.012. | `contact_friction` has no default; flags `CONTACT_FRICTION_IS_AN_ENTERED_VALUE`, `CONTACT_RATIO_CURVE_OF_ONE_PUBLISHED_FOIL_PASS`; the note "read the change with speed, not the level". |
| The contact-ratio curve is model output for one pass with a roughness of 0.1 um; a plant surface of 0.3 to 0.5 um with another wavelength has another curve. | Limitation text; the curve is an input; package 7 returns the contact friction the plant's own records imply. |
| "Roelands" sounds like the better viscosity law. For the one foil oil with data it is worse than Barus at every pressure. | The benchmark `A9-PRESSURE-LAWS-KEROSINE` and its table in guide 8.1; Barus stays the default; flag on use. |
| The steel chatter case shows a frequency within 2 % and, on one reading, a speed within 7 %. This reads as a validation of the chatter screen. | Case verdict `INDICATIVE_ASSUMED_INPUTS`; the note gives the speed range over the friction substitution (5.7 to 9.3 m/s) and says that without the damping heuristic the model is unstable at any speed. |
| The rate factor at rolling speed (about 1.5) is an extrapolation over five decades; the temperature factor pulls the other way; entering one without the other biases every force. | Flag on every pass; guide 8.3 "enter both or neither"; no defaults. |
| The computed heat share (0.16-0.34 at foil gauge depending on film and oil conductivity) looks more certain than the entered 0.22. It rests on a smooth-film thickness and an oil conductivity known within a factor 2. | Reported beside the entered value, used only on request; basis strings; the shares at both sourced conductivities in the result. |
| The surface cycle shows the mean-coefficient model over-stating cooling by 8 % in the example. A reader may scale the spray coefficient by it. | Limitation "one-way"; the Do-not of package 10; the guide ties it to the open basis question X3 instead of resolving it. |
| A fitted spray coefficient inherits the errors of the heat share, bite heat and background coefficient it holds fixed. | `limitations`; the misfit curve and the 10 % range are always returned; nothing is written back. |
| The rate share of chatter damping (about 9 % of the heuristic at m = 0.027) may be read as "the heuristic is 10 times too large". | Note in the block: the heuristic stands for bite dynamics as a whole (gap C3), of which rate sensitivity is one part. |

## 5. Interfaces Phase 2 will consume

The Phase 2 brief (SPEC19) was written against the first version of this brief. Its references
to "SPEC18 package N" use the old numbers: old 1 -> new 2 and 3; 2 -> 4; 3 -> 5 and 6; 4 -> 7;
5 -> 8; 6 -> 9; 7 -> 10; 8 -> 11; 9 -> 12. Two contents changed under it: the friction closure is
`'load_sharing_curve'` with a required contact friction (not `'load_sharing_two_point'` with two
film-ratio keys), and no result quotes "0.79 of the reference load".

| Phase 2 item | what it needs | what Phase 1 provides, and where |
|---|---|---|
| A2, BT-G4 in full (I2): local friction and flow stress across the width | force per width as a function of local friction and flow stress, per pass | `state['extra']` / `result['bite_extras']`: `dforce_dfriction_n`, `dforce_dflow_stress_m2`, the slip derivatives, load exponents (package 4); for other bite models `band_process.friction_force_sensitivity` / `flow_stress_sensitivity` as today. Divide by the width for `p_mu`, `p_Y` of the row's `dp(z) = p_Y*dY + p_mu*dmu` |
| the same | a bite re-solved at a perturbed state without a cold start | `solve_half_space_bite(..., warm_start=...)` (package 3), the cache's stored states (package 4), `_BiteCache.state` (package 7) |
| A2: film and friction from local temperature | roll surface temperature at bite entry per axial station | `width.roll_surface_cycle.bite_entry_temperature_k` on `z_m`; `roll_skin.unit_solutions` for transients of the weight or the flux (package 10) |
| A2 | viscosity, film and friction as functions of a temperature | `Lubricant.dynamic_viscosity_pa_s`, `temperature_viscosity_coefficient_at`; `friction_coefficient(...)['dmu_dlambda']`; `d ln(Lambda)/dT = -beta(T)` (packages 5 and 6) |
| A2 | flow stress as a function of temperature and rate | `RateTemperatureFactor.factor`; `d ln Y/dT = -c_T/(1 - c_T*(T - T_ref))` (package 8) |
| A1 computed (I3): strip temperature across the width | strip exit temperature for local heat, film and roll temperature | `bite_tribology.heat_partition(...)` is a pure function of local inputs: call it per station with `roll_entry_surface_temperature_k` from package 10 (package 9) |
| G5 controller, A6 step-test emulation | surface and bulk time scales; response of the surface layer to a valve change | `width.roll_surface_cycle.time_scales`; `roll_skin.surface_cycle` with a changed spray arc level (package 10) |
| BT-G12 starvation | film thickness as an explicit input of friction and heat partition | `friction_coefficient(film_ratio, ...)` and `heat_partition(interface_conductance_w_m2k=...)` take the film from the caller, so `min(h_s, h_supplied)` can be inserted without touching them |
| BT-G3 in full (a later phase) | checked transcriptions of the crushing laws, height distribution and flow factors | `physicroll/asperity_contact.py` and the benchmark `BT-G3-CRUSHING-LAWS` (package 6) |
| C1, BT-G13 speed and tension gauge control | forward slip and force derivatives with respect to tensions and friction from one consistent bite | the twelve derivatives of package 4; `process.friction_identification.summary` for a friction-speed slope from plant records (package 7) |
| C2, tandem chatter | a stand and span data set with a measured onset | the inputs of `TM-LC7` in `benchmarks.py` (package 1) |
| A5 flow scaling, G5 | a calibrated mean coefficient and its uncertainty range | `calibrate_spray_coefficient(...)['range_within_10_percent_of_minimum_w_m2k']` (package 11) |
