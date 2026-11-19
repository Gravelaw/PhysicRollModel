# Band root-cause screening (lengthwise bands, transverse chatter marks, battery foil)

Status of every result: `SCREENING_RESULT_NOT_PLANT_VALIDATED`. This is an opt-in,
standard-library-only screening tool built on synthetic, uncalibrated models. It ranks
candidate mechanisms for strip bands by an **ordinal evidence tally** and shows which mill
quantities move the model result. It does not produce probabilities and does not certify a
cause. Nothing in it has been compared with plant data.

Formula tags, used throughout and carried over from the module docstrings and the result
`basis` / `formula_basis` / `threshold_basis` texts: **[V]** read in a cited source,
**[D]** derived in this project (by the planner or in the module), **[M]** quoted from memory
and not verified. A tag such as "[V reconstructed]" or "[V second-hand]" keeps the
qualifier the code gives. The phase-1 modules `chatter.py` and `band_signatures.py` carry no
explicit tags; for their formulas the tag below is assigned from the citations and
statements in their docstrings. The battery-foil facts (section 3) come from a research pass
and carry its source labels, as the code does (`FOIL_SOURCES` in `physicroll/band_diagnosis.py`;
list in section 15): "[V S27]" means read in source S27. A foil fact that the research pass
gave without a source is tagged [M] here.

Every demo number in this document is read from the generated results
`artifacts/band_diagnosis/*.result.json`; the file is named at each table. Numbers from
probes run for this document (not demo files) are labelled as such.

## 1. Purpose, scope and what is established

The tool answers one question for a cold-mill process engineer: given what has been observed
on the strip, which band mechanisms are consistent with the observations, which are
contradicted, and what measurement would separate the remaining ones. It covers two
families of bands:

- **Lengthwise bands**: stripes that run along the rolling direction at fixed positions
  across the width (loose or tight bands, buckles, shade stripes, creases), continuous along
  the coil or present only for a while. Mechanisms: a blocked or partly blocked spray nozzle,
  cooling-zone switching, roll-surface bands, grinding feed lines, incoming ridges that
  build up in the coil, tension troughs and creases, profile / flatness mismatch, heat
  streaks and friction or oil-film bands, oil stain, and foil tension lines.
- **Transverse marks**: marks across the strip that repeat along its length at a pitch
  (chatter marks). Mechanisms: third-octave self-excited chatter, fifth-octave stack
  resonance, roll-borne marks, bearing / gear orders, torsional drive vibration, coil-locked
  marks, yield-point bending marks, herringbone, skidding.

What is established, and what is not. The software is verified: the equations are
implemented as written and reproduce their analytic limits (section 13). The physics is
not validated: no number from this tool has been compared with a measurement on a mill.
Several inputs are placeholders (the friction closure), supplied guesses (the heat split
between strip and rolls, the spray heat-transfer coefficients) or analyst choices
(evidence weights, thresholds). The ranking is an evidence tally: a leading hypothesis is
the one most consistent with the observations as entered, not a confirmed cause. The
"confirming test" listed with each hypothesis is the step that can confirm it on the mill.

**At battery-foil gauge (16-60 um), plainly.** The tool was built and documented at sheet
gauge (final pass 0.30 -> 0.21 mm) and then extended so that it runs at foil gauge and says
what it cannot assess there. For a foil mill it can: screen the twenty band mechanisms
against your observations, including a rule-based foil tension-line hypothesis; compute the
thermal stripes your spray header leaves on the work roll and whether such a stripe is hidden
under mill tension or visible after tension release; compute the tension-trough, roller-wrinkle
and coil-ridge thresholds; and list the observations that would separate the candidates. It
cannot: model closed-gap rolling (work rolls touching outside the strip), which published
sources place somewhere between 200 and 50 um exit gauge; solve the roll bite of a pass with an
exit gauge below 8 um or a reduction above 65 %; give a validated roll bite anywhere below
about 60 um; model a doubled (two-sheet) pass (this plant rolls its final pass single-sheet,
section 3.1, so that gap does not apply to it); or model tension lines physically. Below about
60 um the roll bite comes from an experimental model whose numbers are order of magnitude only;
below 20 um exit gauge and above 50 % reduction that model runs in an EXTENDED domain (flags
`EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN`, `REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN`;
section 3.3), and a bite there whose force lies outside the range reported for battery-foil
passes is marked not credible and kept out of every trend statement. And one model result runs
against the plant observation "worse at thinner gauge": in the foil demo the cooling-stripe
mechanism becomes **harder** to see in the mill as the gauge thins (section 3.5).

**For this plant's route** (plant statements: 50 um input, two single-sheet passes, final gauge
usually 17-19 um and down to 12 um; intermediate gauge, alloy and temper not stated): the
first pass (50 um to about 30 um, an assumed intermediate) gets a roll bite from the
experimental mattress model. The final pass gets one too, in the extended domain: at 18 um its
force lies inside the range reported for battery-foil passes (still unvalidated, order of
magnitude only); at 12 um (route 50 -> 25 -> 12 um, 25 um assumed) the force is 2.7 times the
top of that range and the bite is marked NOT CREDIBLE. Both passes lie in closed-gap rolling,
which the tool does not model. The bite-free screens (tension troughs and creases, coil ridge
build-up, position and spacing matching, thermal stripes) and the rule-based hypotheses do not
depend on any of this. With `material.product` the result also checks every pass against the
published product envelope (section 3.1; `docs/thin-gauge-products.md`).

The tool was built in three phases. Phase 1: the transverse family (chatter model, pitch
signatures, levers, schedule sweep). Phase 2: the lengthwise family (roll thermal model,
strip shape and flatness), coupled process models (lubricant-dependent friction, pass
heating, hardening), gauge control and drive dynamics, an experimental thin-gauge roll-bite
model, case schema v2, nine lengthwise hypotheses and new report sections. Phase 3 (battery
foil): the width section runs without a roll bite, optional supplied shape inputs, the
closed-gap and below-floor warnings and the `foil_regime` result block, six foil
observations, the `foil_tension_lines` hypothesis, extended roll-surface, trough and
friction-band rules, a gate on case-wide supports, and a battery-foil demo; then, from a
literature survey of thin-gauge products, an extended roll-bite domain (exit gauge to 8 um,
reduction to 65 %, flagged, with a credibility mark), the product catalogue and the
evidence-neutral product check (`material.product`), and tension-line rules from the
published description.

## 2. Which path to read

| your product and bands | read |
|---|---|
| **battery foil** (exit gauge below 100 um), bands along the strip | section 3 first (what the tool can and cannot say at foil gauge, which observations to record, the foil demo); then sections 4-5 (run, template), 6.2 (lengthwise rules), 12 (report), 14 (limitations); the sheet-gauge physics in 7-10 as needed |
| sheet: bands run **along** the strip at fixed width positions | sections 4-5 (run, observations), 6.2 (lengthwise rules), 7 (lengthwise physics, including thin gauge and short-lived bands), 12 (report), 14 (limitations) |
| sheet or foil: marks run **across** the strip and repeat along it | sections 4-5, 6.3 (transverse rules), 11 (chatter physics), 8-10 as needed |
| not sure | record the orientation first (section 5.1); the report states which family the observations point to |

Both families are always evaluated: a lengthwise case also reports the chatter results, and
the transverse hypotheses are then contradicted by the longitudinal orientation.

## 3. Battery foil: what the tool can and cannot tell you

This section is for a foil-mill engineer making aluminium foil for EV batteries (final gauge
usually 17-19 um and down to 12 um, reached from a 50 um input in two single-sheet passes;
intermediate or thicker products 25-60 um) whose bands run along the length at
several width positions, sometimes continuous and sometimes short-lived, and are worse at
thinner gauge. Code: `physicroll/band_diagnosis.py` (`_foil_regime`, bite floor),
`physicroll/band_width.py` (width section without a bite, foil rules); demo:
`scenarios/band_diagnosis_battery_foil.json`.

### 3.1 Which product this probably is, and what to tell the tool

Two kinds of product fit "battery foil at 16-60 um": current-collector foil (rolled hard,
H18 / H19) and pouch-laminate barrier foil (8021 / 8079 / 8A21, annealed O); tab foil and thick
collector foil also sit at 20-100 um. The catalogue's second battery survey
(`docs/thin-gauge-products.md`, "Battery foil: alloy and temper by gauge"; sources `BG-`)
answers which alloy and temper are used at each gauge. Its three findings: no source gives a
hard "gauge X -> alloy Y" rule, only a GB/T 33143-2022 strength floor that rises as gauge
falls, met by moving from 1085 / 1070 / 1060 / 1235 to Cu-bearing 1100- or 1C30-type alloys;
the first survey's 8011 minimum was wrong (180 MPa, not 220-230); and "H18" on battery foil is a
label for a strength table that European producers call H19 (the foil gets 97-99 % cold
reduction after the last anneal).

Collector foil by gauge band (minimum tensile strength by GB/T 33143-2022, MPa, read from a
producer page reproducing the table; the proposals the tool uses; numbers read from
`physicroll.band_products` by script):

| gauge band | standard minimum Rm by alloy | usually chosen | standard proposal | high-strength proposal | evidence |
|---|---|---|---|---|---|
| ≤10 um | 1100 230, 1C30 220, 1070 185, 8011 180 | 1100-type or 1C30-type; 8021 at 10 µm one-side-bright. | 1070-H18 185 MPa (fallback rule, evidence WEAK) | 1100-H18 262 MPa (evidence medium) | minima strong, choice medium |
| >10–13 um | 1100 230, 1235 180, 1060 190, 1C30 230, 1050 190, 1070 185, 8011 180 | 1100-type for EV; 1235 or 1060 where 180–190 MPa suffices. | 1235-H18 180 MPa (evidence medium) | 1100-H18 250 MPa (evidence medium) | minima strong, choice medium |
| >13–15 um | 1235 185, 1060 190, 1100 220, 1C30 225, 1050 190, 1070 180, 8011 180, 8A21 165 | 1235, 1060, 1N30 standard; 1085 for high power; 1100-type or 3003 when ≥250 MPa is specified. | 1235-H18 185 MPa (evidence strong) | 1100-H18 220 MPa (evidence strong) | minima strong, choice strong |
| >15–20 um | 1235 175, 1060 185, 1070 175, 1050 185, 1100 220, 1C30 220 | 1235, 1060, 1070, 1085 (same grades as at 15 µm). | 1235-H18 210 MPa (evidence vendor_level) | 1100-H18 220 MPa (fallback rule, evidence WEAK) | minima strong, choice vendor_level |
| >20–30 um | none (GB/T 33143 stops at 20 um) | 1235, 1N30, 1085, 3003. | 1235-H18 185 MPa (evidence weak) | 3003-H18, Rm not published (evidence weak) | minima not_rated, choice weak |

**The two bands that matter for this plant.** The usual 17-19 um final gauge is in the
**>15–20 um** band: standard proposal 1235-H18 210 MPa (evidence vendor_level)
(range 175-220 MPa); the research names no usual
high-strength choice there, so the high-strength proposal 1100-H18 220 MPa (fallback rule, evidence WEAK) comes
from the fallback rule and is less supported than the 12 um one. 12 um is in the
**>10–13 um** band: standard minimum 180 MPa for 1235 and
190 MPa for 1060, 230 MPa for the 1100 / 1C30 type that EV practice favours; standard
proposal 1235-H18 180 MPa (evidence medium), high-strength proposal 1100-H18 250 MPa (evidence medium).

**What the tool does with it.** With `material.product` set to a battery product, the result
section `material_selection` gives the gauge band of the final pass (the thinnest pass of the
case) and of the case pass, every alloy option of the final band (temper labels, standard
minimum, typical producer values, usual choice, evidence rating, sources), the standard and
high-strength proposals (status `LITERATURE_PROPOSAL_TO_CONFIRM_WITH_PLANT`), the last pass of any other route in the
schedule with its own proposals, and the case compared with the band: alloy (usual choice /
option / not an option), temper (H18 and H19 both consistent), `material.yield_stress_pa`
against the proof-strength range, and every pass's flow stress against the standard minimum
and the typical range of its own exit-gauge band (INDICATOR ONLY: finished tensile strength is
not the rolling flow stress). Flags, evidence-neutral: `MATERIAL_NOT_STATED_LITERATURE_PROPOSAL_SHOWN`
(unless `material.alloy_temper_stated` is `true`) and
`CASE_STRENGTH_BELOW_STANDARD_MINIMUM_FOR_GAUGE`. It never changes a number in the case or a
hypothesis score. **The plant confirms or corrects** by entering its alloy, temper and
strengths and setting `material.alloy_temper_stated: true` (optional, v2; `null` or absent =
not stated). In the tool the temper acts through the numbers entered:
`material.yield_stress_pa` (coil-ridge yield, critical ridge height) and the pass flow stress
(bite).

The result's `foil_regime.product_question` is worded from the case, not from any plant
statement, and no longer asks the plant for alloy and temper. With a battery
`material.product` it states the literature proposal for the thinnest exit gauge of the case
and points to `material_selection` (in the demo: "the literature proposal for the final gauge
12 um (>10–13 µm band) is standard 1235-H18 ... confirm or correct it with the plant").
Without a product it asks which product this is (pouch-laminate barrier foil, thick collector
foil, tab foil, or an intermediate pass of thinner collector foil, with the catalogue's gauges
and tempers) and to set `material.product`, and names the thinnest exit gauge of the case
pass and schedule (below about 20 um it points to collector foil in H18). Texts that depend on
`material.final_pass_doubled` say "the case states" (the key is the plant's answer as
entered), not "the plant states".

**Answered: the final pass (usually 17-19 um, down to 12 um) is rolled single-sheet** (plant
statement). Published
schedules start doubling at about 18-32 um entry gauge, or not at all for two-side-bright
foil [V S3]; this plant does not double. What follows from it:

- the tool's doubled-pass gap (it has no model of two sheets in one bite with a
  sheet-to-sheet interface) does not apply to this plant;
- the binding limits for the final pass are the experimental, unvalidated roll bite in its
  extended domain below 20 um (section 3.3; at 12 um not credible) and the missing closed-gap
  model: a single-sheet pass at this gauge is closed-gap rolling, where the gauge is set by
  tension, speed and lubrication rather than load [V S8, S16, S17] (section 3.2);
- both strip faces run against a work roll (no matte sheet-to-sheet face), so
  `observation.faces` is worth recording [D]: a surface band printed by one work roll or a
  stain from one side can show on one face only, a flatness or thickness band shows on both
  (the rules: `faces` one S moderate for `roll_surface_band` and
  `oil_carryover_drips_or_stain`, both S weak for `nozzle_thermal_stripe`, section 6.2).

Record the answer in the case as `material.final_pass_doubled` (optional, v2): `null` or
absent = not stated (the foil block asks the plant), `false` = single-sheet stated (the
block records it, drops the question and adds the faces implication), `true` = doubled stated
(flag `DOUBLED_FINAL_PASS_NOT_MODELLED` in `foil_regime.flags` and the top-level flags: the
tool models one sheet in the bite, so every bite-dependent result for that pass describes a
single sheet of the entered gauge, not the doubled pass, and one face of each sheet is the
matte sheet-to-sheet face). "Final pass" is the thinnest pass of the case (the product check
also applies the key to the last pass of every route in the schedule); the key has no
effect without a `foil_regime` block. The foil demo sets it to `false`. The plant has not
stated the alloy and temper; the demo uses the literature proposal 1235-H18 (standard grade
of both final-gauge bands) and says so (`material.alloy_temper_stated: false`).

**The plant's route** (plant statements): the foil mill takes a **50 um input** and reaches
final gauge in **two single-sheet passes**; the final gauge is **usually 17-19 um** and can
go **down to 12 um**. The intermediate gauge, the alloy and the temper were not stated. The demo
ASSUMES 30 um for the usual product (50 -> 30 -> 18 um, 40 % per pass; the published
single-sheet passes 59 -> 30 um [BF-S14], 34 -> 20 um [BF-S11] and 32 -> 17 um [BF-S13] are its
neighbours) and 25 um for the thinnest
(50 -> 25 -> 12 um, 50 % then 52 %, matching the published 50 -> 25 um [BF-S15] and
55 -> 25 -> 12 um [BF-S12] passes) [product catalogue, `docs/thin-gauge-products.md`; reductions
D, computed from the gauges]. What the tool can say for each pass:

| plant pass | gauges | roll bite | what runs |
|---|---|---|---|
| first pass | 50 -> about 30 um (30 um assumed) | experimental mattress model (Hitchcock rejects it); order of magnitude only; closed gap already likely (below every reported onset) | everything, as a case pass: chatter (flagged unreliable at foil gauge), open-gap levers and gauge control, thermal stripes, the strip-shape chain, gauge trend, all hypotheses |
| final pass | about 30 -> 17-19 um | experimental mattress model in its extended domain (exit below 20 um, flagged); force inside the reported battery-foil range at 18 um in the demo, still unvalidated | everything a schedule row gets: bite, gauge-trend row, bite-free thresholds; as a case pass also chatter and the shape chain, with the extended-domain caveat |
| thinnest product | 50 -> about 25 -> 12 um (25 um assumed) | first pass mattress at 50 %; final pass mattress in the extended domain (52 %, 12 um, both flags) | in the demo the 12 um bite force is 6.19 kN/mm, 2.7 times the top of the reported range: marked NOT CREDIBLE, kept in the tables, excluded from every trend statement; its bite-free thresholds stand |

**Published single-sheet battery-foil practice** (the product catalogue, `physicroll/band_products.py`
and `docs/thin-gauge-products.md`, which cites every value with its source id and read
status): per-pass reductions 29-64 %; final-pass entry gauge 15-32 um and final-pass reduction
29-57 %; final single-sheet pass speed 450 +/- 20 m/min [BF-S11, a patent that keeps the coil
at or below 80 C against foil softening] and 600-650 m/min [BF-S16], with 1000-1200 m/min
claimed in a third patent [BF-S12]; earlier passes 550-1000 m/min [BF-S11, BF-S16, BF-S17].
All of these sources are read as excerpts or trade pages, not full text, except BF-S15. **Correction:** earlier versions of this document quoted
260 -> 135 -> 65 -> 30 um and 280 -> 120 -> 55 -> 24 um as single-sheet battery-foil practice
[S3, S4]. On the trade page they come from (catalogue source BF-S17) the next pass is doubled
(30x2 -> 15x2 um and 24x2 -> 12x2 um), so 30 um and 24 um are doubling-entry gauges for
one-side-bright foil, not single-sheet final gauges (the catalogue's
`BATTERY_SCHEDULE_CAVEAT`). Other facts quoted from the research pass of phase 3: work roll
230-330 mm diameter (260-280 mm typical), backup roll 2.4-2.8 times that [V S8]; entry tension
29-49 MPa, exit tension 34-44 MPa [V S3]; load about 0.9-2.3 kN per mm of width [V S3, S4;
conversion D]; work-roll Ra 0.11-0.125 um on intermediate and finishing passes [V S3, S4];
rolling oil 1.8-2.1 mm2/s at 35-55 C [V S3, S4]. Sutcliffe & Montmitonnet use plane-strain
flow stress 150 MPa, tensions 20 / 20 MPa and combined roughness 0.3 um for a foil case
[V S11]. The catalogue is a literature survey with vendor-level sources for much of the route
data; nothing in it was measured on a plant.

**The product check** (`material.product`, optional, v2): a catalogue id (unknown ids are
rejected with the list of valid ids). The result then carries `product_check`: the product's
published envelope (final gauge, single-sheet gauge, rolled mode, per-pass and final-pass
spans, speeds, alloys, tempers) and, for the case pass and every schedule row,
`band_products.check_pass` findings with the verdicts `WITHIN_PUBLISHED_RANGE`,
`BELOW_PUBLISHED_RANGE`, `ABOVE_PUBLISHED_RANGE`, `NO_PUBLISHED_RANGE`,
`INCONSISTENT_WITH_PUBLISHED_MODE`, each with its source ids and read status; final passes are
the thinnest pass and the last pass of any route the schedule lists (no pass enters at its
exit gauge), and `material.final_pass_doubled` applies to them; the nearest published passes
for the case pass and the final pass. `material.alloy` may carry a prefix (AA1235, EN AW-1235):
the check uses the bare designation. Flags `CASE_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE` and
`FINAL_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE` are evidence-neutral: the product check never
changes a hypothesis score, and a value inside a published span is not evidence that a pass
is good. Without a product, a foil-regime case gets `product_check` `NOT_SUPPLIED` with the
list of ids; a sheet case without a product gets no `product_check`.

What to tell the tool: a case pass the roll-bite models can solve (exit gauge at least
8 um, reduction at most 65 %; below 20 um and above 50 % flagged as extended; section 3.3),
the whole schedule including the final pass, `model_options.bite_model: "auto"` (the
Hitchcock model keeps its own 20 um floor, so `"hitchcock"` rejects a thinner pass), a
`width_model` with your spray header, a `tribology` section with your oil and roughness,
`material.product`, and the foil observations of section 3.8. If a plant foil model gives the
strip stiffness, the exit-tension force sensitivity and the bite half-length of your pass,
supply them in `width_model.shape_inputs` (section 3.4).

### 3.2 Closed-gap rolling

In closed-gap rolling the work rolls touch each other outside the strip width, so part of the
roll load passes from roll to roll instead of through the strip. The sources disagree on
where it starts: at 0.1-0.2 mm exit gauge [V S8]; below 100 um, about 80 um, with the roll
force ineffective for gauge control below 50 um [V S16]; below 50 um [V S17]. In closed gap
more screw-down only bends the rolls and changes flatness; the reduction is set by tension,
speed and lubrication [V S8, S16, S17].

The tool has **no roll-kissing load path**: both roll-bite models see only the contact with
the strip. What this means for the results, as the `foil_regime.implications` list states it:

- the roll load is not a gauge actuator; the lever table (critical chatter speed against
  friction, reduction, tensions, span, damping) and the gauge-control section (section 9)
  assume an open roll gap and are open-gap reasoning only; in a foil case both carry the note
  "OPEN ROLL GAP ASSUMED";
- the local transfer of a roll stripe to the strip by roll and strip compliance is what the
  shape chain models, but without the load shunted outside the strip where the rolls touch,
  so the transfer may be misestimated;
- online (shapemeter) and offline flatness diverge at foil gauge because front tension masks
  the true shape [V S17, S8]; the in-mill and after-release band states of the shape chain
  are the tool's proxy for that difference;
- foil defects with no physical model in the tool (tension lines, hot spots from roll
  wipers, creasing from ironing rolls) are screened by rules only.

Even the open-gap model says the load hardly moves the gauge at the demo's case pass: the
strip is 38.4 times stiffer than the mill (`schedule_sweep` row F1,
`strip_to_mill_modulus_ratio`), so a gap change moves the exit gauge by about
`M/(M+Q)` = 2.5 % of the stroke [D, gaugemeter relation of section 9].

**The `foil_regime` block.** For a case-pass exit gauge below 100 um the result carries
`foil_regime` (else `null`) and the flag `CLOSED_GAP_ROLLING_LIKELY_ROLL_KISSING_NOT_MODELLED`.
It holds: the exit gauge; `closed_gap_onset_range_m` (50-200 um) with the three sources;
`case_position` (`BELOW_EVERY_REPORTED_ONSET` below 50 um, else `INSIDE_REPORTED_ONSET_RANGE`)
and its text; `implications` (the list above); `bite` (which roll-bite model produced the
numbers, its reliability text and flags, the reason Hitchcock rejected the pass, separating
force per width against the reported 0.9-2.3 kN/mm and whether it lies inside, forward slip,
or the bite error); `schedule_bites` (bite model and force per width for each schedule pass);
`extended_bite_domain` (the passes whose bite lies in the extended domain, each with its
flags, force per width, whether that force lies inside the reported range, and its
credibility mark, section 3.3, plus a text that says what the extended numbers are worth);
`below_bite_model_floor` (the passes below the 8 um floor of the mattress model, flag
`EXIT_GAUGE_BELOW_BITE_MODEL_FLOOR`, and a text that asks whether the last pass is doubled,
or, with `material.final_pass_doubled` stated, records the answer: `false` says the missing
bite is a limit of the tool, not of an unmodelled doubled pass; `true` adds the flag
`DOUBLED_FINAL_PASS_NOT_MODELLED`; empty in the demo); `final_pass_doubled` when stated; with
`false` also a sixth implication on `observation.faces` (section 3.1);
`wrinkle_rule` (section 3.6); `product_question` (section 3.1: with a battery
`material.product` it states the literature proposal for the final gauge, without one it asks
which product this is; it no longer asks for alloy and temper); flags, limitations and the
foil sources. Above 100 um exit gauge there is no foil block, although one source puts the
onset of closed-gap rolling at up to 200 um.

### 3.3 Where the roll-bite models stand at these gauges

Source: `artifacts/band_diagnosis/battery-foil-demo.result.json`, `foil_regime.schedule_bites`
and `schedule_sweep.rows` (friction 0.03 supplied on every pass, `bite_model: auto`).

| pass | reduction | bite model | force per width [kN/mm] | contact radius ratio | forward slip | credibility |
|---|---|---|---|---|---|---|
| S1 0.260 -> 0.135 mm (assumed stock route) | 48 % | Hitchcock (slab + circular flattening) | 0.709 | 1.125 | 0.0453 | |
| S2 0.135 -> 0.085 mm (assumed stock route) | 37 % | Hitchcock | 0.612 | 1.270 | 0.0664 | |
| S3 0.085 -> 0.050 mm (assumed stock route) | 41 % | Hitchcock | 0.736 | 1.464 | 0.0934 | |
| F1 0.050 -> 0.030 mm (plant pass 1, case pass; 30 um assumed) | 40 % | experimental mattress; Hitchcock rejected it (contact radius ratio 2.481 above 1.5) | 0.959 (inside 0.9-2.3) | 2.105 | 0.190, flagged implausible | |
| F2 0.030 -> 0.018 mm (plant pass 2, final) | 40 % | experimental mattress, extended domain (exit below 20 um) | 1.54 (inside 0.9-2.3) | 3.313 | 0.308 | `FORCE_INSIDE_REPORTED_RANGE_UNVALIDATED` |
| ALT1 0.050 -> 0.025 mm (thinnest product, alternative first pass; 25 um assumed) | 50 % | experimental mattress | 1.49 (inside 0.9-2.3) | 2.256 | 0.315 | |
| ALT2 0.025 -> 0.012 mm (thinnest product, alternative final pass) | 52 % | experimental mattress, extended domain (exit below 20 um and reduction above 50 %) | 6.19 (2.7 x the 2.3 top) | 11.14 | 0.422 | `FORCE_OUTSIDE_REPORTED_RANGE`: NOT CREDIBLE |

- **Force per width.** The case pass gives 0.959 kN/mm, inside the 0.9-2.3 kN/mm reported for
  battery-foil passes [V S3, S4]; the three Hitchcock passes give 0.709, 0.612 and
  0.736 kN/mm, below it; F2 and ALT1 give 1.54 and 1.49 kN/mm, inside it; ALT2 gives
  6.19 kN/mm, 2.7 times its top. The force rises steeply with friction (probe below), so
  "inside the reported range" holds because friction 0.03 was supplied, and says nothing about
  whether the friction is right.
- **Forward slip** of the mattress bite is 0.190 at the case pass and 0.308-0.422 on the
  thinner passes; it carries the flag `FORWARD_SLIP_IMPLAUSIBLY_LARGE_NO_ELASTIC_STRIP_ZONES`
  (the model has no elastic strip zones; section 10.2). The slip enters the interface slip
  dissipation, so the pass heating is inflated [D]: at the case pass friction power 47.1 kW/m
  against 40.3 kW/m plastic power, strip exit temperature 333.4 K (+20.3 K) at the strip
  heat share 0.22 (`process.heating.operating`; 390.6 K at the former 0.84); F2, ALT1 and ALT2
  reach 339.2 K, 345.6 K and 346 K (`process.heating.schedule`), all below the 393.15 K limit
  supplied in the demo and below the published 80 C battery coil limit (section 3.12). The
  heat-streak rule "boundary regime or exit temperature above the limit" is met at the case
  pass by the boundary regime alone, so the inflated temperature does not change the demo
  ranking, but it could on a case in the mixed regime.
- **The extended roll-bite domain.** `chatter.BitePass.validate` keeps a 20 um floor and a
  50 % reduction limit for the slab and Hitchcock path; the mattress model
  (`foil_bite.py`) accepts an exit gauge down to 8 um (`BITE_FLOOR_M`) and a reduction up to
  65 %. Probe runs of this project found its solution converged and continuous across 20 um
  and across 50 %, and published foil passes reach 64 % (section 3.1); no source validates it
  there. A bite below 20 um exit gauge carries `EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN`,
  one above 50 % `REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN` (both in the row's
  `bite_flags` and in `foil_regime.extended_bite_domain`); each such row also carries an
  `extended_domain_note`. What the numbers are worth: the same experimental model and the same
  missing closed-gap load path as at 30 um, order of magnitude only, and nothing validated.
- **The credibility mark.** A bite in the extended domain below 20 um exit gauge is compared
  with the 0.9-2.3 kN/mm reported for battery-foil passes (the range applies to battery-foil
  passes; it is not a general foil limit). Inside it the row carries
  `bite_credibility: FORCE_INSIDE_REPORTED_RANGE_UNVALIDATED` (the demo's F2 at 18 um: usable,
  still unvalidated); outside it `FORCE_OUTSIDE_REPORTED_RANGE` with
  `bite_force_ratio_to_reported_range` (force over the nearer end of the range; the demo's ALT2
  at 12 um: 2.7). A not-credible row stays in every table, marked, and is excluded from the
  gauge-trend text, the report's direction sentence and its charts (section 3.5). When the
  case pass itself is not credible the result carries `case_bite_credibility`, the flag
  `CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE`, a limitations sentence, and
  every model-based evidence item that rests on the bite is gated: it becomes `NEUTRAL` with
  basis `model not credible` and the note "[NOT CREDIBLE BASIS: ...]", and keeps its verdict
  and weight without the gate in `verdict_without_credibility_gate` and
  `weight_without_credibility_gate` (section 6.1). Below 8 um, or above 65 %, the pass has no bite: its schedule-sweep,
  pass-heating and gauge-trend rows are reported as not derivable with the reason, flag
  `EXIT_GAUGE_BELOW_BITE_MODEL_FLOOR` for the floor; for a case pass also chatter, levers,
  gauge control and the derived shape chain. Bite-free parts still run (section 3.4).
- **Chatter on the thin passes.** F2 is stable over the scanned speed range with bite damping
  (4.67 m/s critical speed without it) and flagged `NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT`; ALT2 is
  stable over the scanned range with and without it. Neither is evidence, ALT2 because its bite
  is not credible.
- **Time simulation.** A very stiff bite can make the time simulation exceed its step limit
  (a 12 um case pass does); the section then reads `FAILED` with the reason instead of
  stopping the diagnosis.
- **Friction.** Probe run for this document on the demo mill (not a demo file): the mattress
  model solves the case pass 0.050 -> 0.030 mm at friction 0.03, 0.035, 0.04 and 0.05 with
  0.959, 1.25, 1.60 and 2.49 kN/mm (the last above the reported range) and rejects it at 0.06
  ("Coulomb shear mu*p reaches 1.38 x the material shear yield K/2 in a slip zone;
  sticking/shear-friction model required ..."); 60 -> 30 um and 50 -> 25 um passes at 170 MPa solve at 0.04 and are rejected at
  0.05. The test `tests/test_band_foil.py` (`NoBiteWidthTests`) pins the rejection of the
  60 -> 30 um pass at 0.05. The tool holds no foil friction value from a read source; the
  demo's 0.03 is supplied. A rejection at the plant's friction is therefore possible; it is
  reported with its reason, not hidden.

Where Hitchcock still solves at foil gauge (S1-S3 here) it carries
`THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN`; its numbers are indicative only and assume an open
gap. Mattress numbers are order of magnitude only (section 10.2).

### 3.4 What still runs without a roll bite, and supplying shape inputs

When neither roll-bite model solves the case pass (a rejection, an exit gauge below
8 um or a reduction above 65 %), the width section still evaluates everything that does not need a bite
(`width.shape_chain.parts_without_it`): tension troughs in both spans; coil ridge build-up and
the critical ridge height; positions and spacing analysis; two-tone and grinding pitch; the
Shohet-Townsend window; and the roll thermal steady state and switching events when
`width_model.bite_heat_per_width_w_m` and the roll heat fraction are supplied (otherwise
`thermal_steady` is not assessable, flag `WIDTH_THERMAL_NOT_ASSESSABLE_NO_BITE_HEAT`). An
incoming ridge's exit height then comes from the proportional-transfer estimate
`dh = (h/H)*dH` (the dominant-tension-feedback limit of the transfer of section 7.2; an
estimate, not a bound [D]; flag `RIDGE_EXIT_HEIGHT_FROM_PROPORTIONAL_LIMIT_NO_BITE`).

The strip-shape chain (thickness transfer, flatness, band states, onset heights, the case-pass
gauge-trend row, ridge flatness in the pass) needs the strip stiffness per width `Q`, the
exit-tension force sensitivity per width `N_x'` and the bite half-length `a`. Without them
`width.shape_chain.status` is `NOT_ASSESSABLE` with the bite error as the reason, flag
`WIDTH_SHAPE_CHAIN_NOT_ASSESSABLE_NO_BITE`, and each part is individually not assessable.
Hypothesis rules that use a model band then give `NEUTRAL` with basis
`model not assessable`, never a contradiction; a coil-ridge result from the proportional
estimate supports only weakly and never contradicts.

**`width_model.shape_inputs`** (optional, `null` = derive from the bite):
`{strip_stiffness_per_width_pa (> 0), exit_tension_force_sensitivity_per_width_m (0 to 1),
bite_half_length_m (> 0, at most 0.1), provenance (non-empty text)}`, from a plant foil model.
A sensitivity of 0 means no exit-tension feedback (the compliance-only limit): the feedback
stiffness is 0, the with-feedback level equals the compliance-only level exactly, no band is
saturated, `tension_feedback_applied` stays true and the reasons say "Supplied exit-tension
force sensitivity is zero: no feedback"; a negative value is rejected. (A derived bite gives a
positive sensitivity even at zero exit tension in probes of both bite models.)
They take precedence over a derived bite for the case pass only (other schedule passes use
their own bite), set the flag `SHAPE_INPUTS_SUPPLIED`, and the report says "Strip-shape chain
from SUPPLIED shape inputs (not verified by the tool)" with the provenance. The incoming-ridge
transfer still needs the bite's entry-thickness force sensitivity, which `shape_inputs` does
not carry, so without a bite it uses the proportional estimate. For orientation, the demo's
derived case-pass values (mattress bite, `width.inputs_used`): `Q` = 7.39e10 Pa,
`N_x'` = 6.31e-3 m, `a` = 1.19 mm.

### 3.5 What the model says about "worse at thinner gauge" in foil

Source: `artifacts/band_diagnosis/battery-foil-demo.result.json`, `width.gauge_trend`. As in
section 7.3, the demo's steady stripe (2.96 um at 0.6225 m, isolated; strip heat share
0.22, section 3.12) is carried through every schedule pass with that pass's own bite and
tension; a smooth Gaussian reference stripe (half-peak width 0.1 m) is evaluated alongside. This
holds the case-pass stripe unchanged on every pass (the question "what does the same roll
stripe do at each gauge"); the stripe each pass would itself produce is a different question,
answered below and in section 3.12. S1-S3 are the assumed stock route, F1 is the plant's first
pass (the case pass), F2 the plant's final pass (extended domain, force inside the reported
range, unvalidated), ALT1 and ALT2 the thinnest product's alternative route 50 -> 25 -> 12 um;
ALT2's bite is NOT CREDIBLE (force 2.7 times the top of the range reported for battery-foil
passes, section 3.3). The rows are listed in schedule order; the trend statements order them by
exit gauge and leave ALT2 out.

| pass | exit gauge [um] | exit tension [MPa] | rigid bound [I] | compliance only [I] | linear feedback [I] | feedback stiffness per width [Pa] (x `Q`) | in-mill state | after release | stripe / in-mill onset |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 135 | 35 | 2192 | 1746 | 131.8 | 6.82e11 (286) | MANIFEST (buckles) | manifest | 2.51 |
| S2 | 85 | 37 | 3481 | 2478 | 95.51 | 1.39e12 (171) | MANIFEST (buckles) | manifest | 1.73 |
| S3 | 50 | 39 | 5917 | 3375 | 63.74 | 3.53e12 (164) | MANIFEST (buckles) | manifest | 1.12 |
| F1 (case) | 30 | 40 | 9862 | 3128 | 25.13 | 1.47e13 (199) | latent | manifest | 0.434 |
| F2 (extended, unvalidated) | 18 | 42 | 1.644e+04 | 2082 | 10.06 | 6.09e13 (243) | latent | manifest | 0.169 |
| ALT1 | 25 | 40 | 1.183e+04 | 2669 | 15.53 | 2.97e13 (234) | latent | manifest | 0.273 |
| ALT2 (NOT CREDIBLE) | 12 | 42 | 2.466e+04 | 296.7 | 0.779 | 1.40e15 (386) | below reporting threshold | below reporting threshold | - |

| pass | in-mill onset, model stripe [um] | in-mill onset, Gaussian [um] | after-release onset, model stripe [um] | after-release onset, Gaussian [um] | reporting onset (2 I), model stripe [um] |
|---|---|---|---|---|---|
| S1 | 1.18 | 1.11 | 0.0456 (upper bound) | 0.0415 (upper bound) | 0.045 |
| S2 | 1.71 | 1.58 | 0.063 (upper bound) | 0.0573 (upper bound) | 0.0622 |
| S3 | 2.64 | 2.45 | 0.0945 (upper bound) | 0.086 (upper bound) | 0.0934 |
| F1 | 6.81 | 6.3 | 0.239 (upper bound) | 0.218 (upper bound) | 0.237 |
| F2 | 17.5 | 16.2 | 0.59 (upper bound) | 0.537 (upper bound) | 0.59 |
| ALT1 | 10.8 | 10.1 | 0.387 (upper bound) | 0.352 (upper bound) | 0.383 |
| ALT2 (NOT CREDIBLE) | not reached within the 50 um scan | not reached within the 50 um scan | 7.6 (upper bound) | 6.91 (upper bound) | 7.6 |

The bite-free thresholds per pass, all from `width.gauge_trend.rows`: every row carries the
flatness dead band (`shohet_townsend_half_width_i_units`), the critical coil ridge height, and,
for a foil-regime case or a schedule with a pass without a roll bite, the trough onset and
roller-wrinkle thresholds of both spans with that pass's gauges and tensions
(`trough_critical_lateral_stress_{exit,entry}_span_pa`,
`roller_wrinkle_critical_lateral_stress_{exit,entry}_span_pa`; the same
`strip_shape.tension_trough_screen` call as the case-pass `troughs` section, deflector radius
0.125 m; the exit-span trough value equals the row's `trough_critical_lateral_stress_pa`).
They need no bite, so the credibility mark does not apply to them: ALT2's thresholds stand.

| pass | exit gauge [um] | dead-band half-width [I] | critical ridge height [um] | trough onset lateral stress, exit / entry span [kPa] | roller-wrinkle threshold, exit / entry span [MPa] |
|---|---|---|---|---|---|
| S1 | 135 | 0.271 | 0.694 | -135 / -241 | -46.2 / -89.1 |
| S2 | 85 | 0.115 | 0.437 | -87.6 / -129 | -29.1 / -46.2 |
| S3 | 50 | 0.0428 | 0.257 | -52.9 / -84 | -17.1 / -29.1 |
| F1 | 30 | 0.0165 | 0.154 | -32.2 / -50.1 | -10.3 / -17.1 |
| F2 | 18 | 0.00639 | 0.0926 | -19.8 / -31.3 | -6.17 / -10.3 |
| ALT1 | 25 | 0.0118 | 0.129 | -26.8 / -50.1 | -8.56 / -17.1 |
| ALT2 | 12 | 0.00301 | 0.0617 | -13.2 / -26.1 | -4.11 / -8.56 |

The result states the trend in `width.gauge_trend.bite_free_text`, ordered by exit gauge
(S1, S2, S3, F1, ALT1, F2, ALT2): "Bite-free thresholds (no roll bite needed), thickest to thinnest pass, S1 0.260->0.135 mm (assumed stock route) (135 um) to ALT2 0.025->0.012 mm (thinnest product, alternative final pass) (12 um): flatness dead band half-width 0.271 -> 0.00301 I-units (x0.011, falls on every pass); critical coil ridge height 0.694 -> 0.0617 um (x0.089, falls on every pass); trough onset lateral stress, exit span -135 -> -13.2 kPa (x0.097, in magnitude falls on every pass); trough onset lateral stress, entry span -241 -> -26.1 kPa (x0.11, in magnitude not monotonic); roller-wrinkle threshold, exit span -46.2 -> -4.11 MPa (x0.089, in magnitude falls on every pass); roller-wrinkle threshold, entry span -89.1 -> -8.56 MPa (x0.096, in magnitude not monotonic)." The entry-span values are not monotonic because, ordered
by exit gauge, the rows interleave two routes: ALT1 (entry 50 um) lies between F1 and F2
(entry 30 um).

**The model does not reproduce "worse at thinner gauge" through cooling stripes buckling in
the mill.** Ordered by exit gauge over the credible rows, the same 2.96 um roll stripe gives
132, 95.5, 63.7, 25.1, 15.5, 10.1 I-units with the exit-tension feedback at 135, 85, 50, 30, 25 and 18 um; its in-mill onset
height rises 1.18 -> 1.71 -> 2.64 -> 6.81 -> 10.8 -> 17.5 um (Gaussian reference 1.11 -> 16.2 um). At the measured heat partition
(section 3.12) the stripe is large enough to **buckle in the mill on the three assumed stock
passes S1, S2, S3** (stripe / onset 2.51, 1.73, 1.12) and stays **hidden under tension on the
plant's passes F1, ALT1, F2** (0.434, 0.273, 0.169); it is visible after release on all six. (At the
old strip share 0.84 and 2 kW/m2K the stripe was 0.959 um and hidden on all six.) The result's text
(`width.gauge_trend.text`) ends: "Not credible (excluded from the trend): ALT2 0.025->0.012 mm (thinnest product, alternative final pass) (extended-domain bite force 6.19 kN/mm, x2.7 the nearer end of the 0.9-2.3 kN/mm reported for battery-foil passes)." The report's direction sentence says: "the in-mill onset stripe height rises from 1.18 µm to 17.5 µm (x15, on every pass), and the after-release onset rises from ≤ 0.0456 µm to ≤ 0.59 µm (x13, on every pass; reporting-threshold upper bounds); thinner is less sensitive for this mechanism in the model." The 18 um point is an
extended-domain bite (force inside the reported range, unvalidated); the 12 um point is not
usable at all.

**Two questions, two answers.** The table above holds the case-pass stripe on every pass. The
stripe each pass would itself produce scales with that pass's bite heat (same spray, same
partly blocked nozzle, steady state; `width.thermal_sensitivity.per_pass`): at the case share it
would buckle in the mill on S1, S2, S3 (stripe / onset 6, 2.26, 1.4) and stay latent on
F1, ALT1, F2 (0.434, 0.364, 0.1); at share 0.84 with the same
spray coefficient it would already be 1.23 on S1. Both answers
assume the steady state: from a healthy header the stripe needs 116 s to reach 50 % and
551 s to reach 90 % of its steady height (`width.thermal_sensitivity.steady_build_up`), so a pass must
last about ten minutes for the steady numbers to apply; shorter passes carry less. In one
sentence: in this model a partly blocked nozzle gives a stripe that shows in the mill on the
thick stock passes but stays hidden under tension on the plant's 30, 25 and 18 um passes, so a
foil band of this kind is expected after tension release, and thinner foil hides it better in
the mill.

Why, in the model [D, from the transfer of section 7.2]: the exit-tension feedback stiffness
per width `N_x'*E_strip*xi/h_exit` grows as the gauge falls, from 6.82e11 Pa at S1 to 1.47e13 Pa
at F1 and 6.09e13 Pa at F2 (x89 from S1 to F2) while the gauge falls x7.5. A locally
over-rolled fibre loses exit tension, which raises the local roll force and flattens the roll
bump; at foil gauge this effect wins, so the elongation a given stripe leaves falls with
gauge, although the rigid bound rises x7.5 from S1 to F2 and the compliance-only level is not
monotonic (3375 at S3, 3128 at F1, 2082 at F2). For a broad stripe the in-mill onset needs the
residual compression to exceed the mill tension (35-42 MPa here), so it is reached at ever
larger stripes. At sheet gauge (section 7.3) the same feedback made the elongation nearly
gauge-independent; at foil gauge it makes it fall.

What the model does make easier at thinner gauge:

- **Bands that appear after tension release.** On every credible foil pass any stripe large
  enough to be reported (2 I-units) already buckles once tension is released: the
  after-release onsets 0.0456, 0.063, 0.0945, 0.239, 0.387 and 0.59 um coincide with the
  reporting onsets and are upper bounds set by the 2 I-unit threshold. They rise in
  micrometres only because a stripe gives fewer I-units per micrometre at thinner gauge; read
  them as "every reported band is visible on the coil, at the slitter or on the table", not as
  a falling trend. (At sheet gauge the same onsets fell with gauge, section 7.3; across the
  foil passes they do not.)
- **The flatness dead band** half-width falls from 0.271 to 0.115 to 0.0428 to 0.0165 I-units
  at 30 um, 0.0118 at 25 um, 0.00639 at 18 um and 0.00301 at 12 um: a relative crown change
  that lateral flow absorbs in thicker strip shows as flatness in foil.
- **The critical coil ridge height** falls in proportion to gauge, 0.694 -> 0.437 -> 0.257 ->
  0.154 um, and to 0.129 um at 25 um, 0.0926 um at the plant's 18 um final pass and 0.0617 um at
  12 um (they need no bite).
- **The trough onset lateral stress** falls with gauge (it scales as the gauge times the
  square root of the span tension, section 7.2), -135 -> -87.6 -> -52.9 -> -32.2 kPa, to
  -19.8 kPa at 18 um and -13.2 kPa at 12 um, and the roller-wrinkle threshold falls in
  proportion to gauge, -46.2 MPa at 135 um to -10.3 MPa at 30 um, -6.17 MPa at 18 um and
  -4.11 MPa at 12 um (at the case pass the result gives -17.1 MPa on the entry span, 50 um, and
  -10.3 MPa on the exit span, 30 um; `width.troughs`).
- **Outside the model: tension lines**, which the literature reports for battery foil below
  about 30 um [V S28] (below 15 um in another source [V S27]; "below 15 um" in the excerpt of a
  trade report of a producer talk, catalogue source BF-S21), more visible at low tension: the
  plant's final pass (17-19 um, down to 12 um) is inside that range.

What this implies for where to look first on the mill (a screening order, not a diagnosis):
if your bands get worse as the gauge thins, a cooling stripe that buckles **in the mill** is
not the first candidate in this model, because a given stripe is hidden more, not less, at
thinner gauge (at the measured heat partition it shows in the mill on the thick stock passes
and not on the foil passes). The thin-gauge-sensitive candidates are bands seen only after tension
release (a thermal stripe can be one of them), tension troughs and creases in the spans and
at the ironing roll, coil ridges, a crown change outside the shrinking dead band, and tension
lines. The first observations to take are therefore: is the band visible in the mill or only
after tension release (compare the online shapemeter with the offline sag of a sample), and
does it fade above some exit tension (step the exit tension); then the ironing-roll,
blow-off, wiper and speed tests of section 3.8. Note that the rule weights for
`worse_at_thinner_gauge` are inherited from sheet gauge: "true" still supports the nozzle and
zone hypotheses weakly although the foil model trend runs the other way (section 14).

### 3.6 The wrinkle rule of thumb

"At 20 MPa tension, flatness worse than 30 I-units necessarily wrinkles" [V S27]. The
model's in-mill rule (section 7.2) asks whether the net compression of a band exceeds its
buckling stress; for a broad band at foil gauge the buckling stress is a few kPa, so the
condition is that the residual compression `E*I*1e-5` exceeds the tension: 3e-4 x 70 GPa =
21 MPa at 30 I-units, the same condition as the rule of thumb [D]. The model differs in that
tension beside a compressed zone stabilises it (Rayleigh quotient) and the buckling stress
depends on the band width. The result evaluates
`wrinkle_onset_i_units = 1e5 * exit_tension / E_strip` [D] beside the largest model band
(`foil_regime.wrinkle_rule`). Demo: 57.1 I-units at 40 MPa exit tension; the largest model
band (steady stripe, linear feedback) is 25.1 I-units, below it, consistent with that band
being hidden under tension.

### 3.7 Foil band vocabulary and the hypotheses it maps to

The mapping of each term to a hypothesis is this project's reading [D]; the descriptions are
from the sources given.

| term | what the sources describe | hypothesis in the tool |
|---|---|---|
| hot spot / local loose band (起鼓) | local roll expansion; a blocked nozzle or low coolant pressure; debris in the roll wiper; a wide coil run after a narrow one without a backup-roll change; ironing-roll shape or pressure; excess forward slip [V S25] | by cause: `nozzle_thermal_stripe` or `cooling_zone_switching_transient` (roll expansion, nozzle, coolant pressure); `roll_surface_band` (wiper debris, wide after narrow); `tension_troughs_or_creases` (ironing roll); excess forward slip has no hypothesis |
| tension lines (张力线) | parallel lengthwise stripes at 5-20 mm pitch, wider and more visible at low tension, vanishing above a threshold tension, worse at thinner gauge; remedies: more front tension (risks ridging), higher roll roughness, ironing-roll pressure per side, reduced or redirected exit air blow-off [V S27, S28]; a typical battery-foil flatness defect [V S5] | `foil_tension_lines` (rule-based, no physical model) |
| mill lines / gloss bands (色差) | backup-roll lines printed onto the work roll; wiper debris; roughness non-uniformity; rolling wide after narrow; mainly in finishing passes [V S25, S17] | `roll_surface_band` (backup-roll lines, wiper, wide after narrow); `heat_streak_or_film_variation` (roughness non-uniformity) |
| ridge marks (板型棱印) | a typical battery-foil flatness defect, listed with tension lines [V S5] | `incoming_ridge_coil_buildup` (ridges that build up in the coil) |
| EAFA heat stripes | straight to snaking grey stripes from temperature or flatness differences across the width or a locally overheated roll [V S26] | `nozzle_thermal_stripe`, `cooling_zone_switching_transient`, `heat_streak_or_film_variation` |
| EAFA rolling stripes | gloss side only, constant along the coil, from local work-roll wear [V S26] | `roll_surface_band` |
| EAFA grooves | sharp flatness deviations in the rolling direction [V S26] | no dedicated hypothesis; the model's thermal stripes are smooth, so a sharp groove points away from them; nearest are `roll_surface_band` and `grinding_feed_marks` |
| creasing | possible at any exit gauge below 50 um; from a local loose band, ironing-roll pressure imbalance or misalignment, low rewind tension [V S25] | `tension_troughs_or_creases` |
| friction or oil-film band | in foil the oil film is comparable to the roughness (film ratio 1.76 at 40 m/s falling to 0.22 at 5 m/s in Sutcliffe's case [V S11]), so a cross-width difference in roughness or oil film gives a flatness band without a roll bump; it tracks speed changes [V S17 for the roughness cause; mechanism D] | `heat_streak_or_film_variation` |

### 3.8 Which observations to record at foil gauge, and why each discriminates

The six foil fields are optional nullable booleans in schema v2 (absent = `null`; v2 files
written before them still load; a v1 case may not carry them). The rules quoted are those of
`physicroll/band_width.py` (section 6.2); "S" supports, "C" contradicts.

| observation (field) | how to take it | what it separates |
|---|---|---|
| visible in the mill or only after tension release (`visible_only_after_tension_release`, `appearance`) | look at the strip in the mill and at the coil, slitter or inspection table; compare the online shapemeter with the offline sag of a sample laid flat (examples of offline requirements: sag at most 4 mm over a 2 m span [V S5]; 8-10 I-units achieved at 1500 m/min [V S17]) | the most informative foil observation in the model: in the foil demo every reported model band is hidden in the mill and visible after release. "Only after release" true supports the nozzle and zone hypotheses (moderate, when the model band is latent in the mill and manifest after release), the ridge and profile hypotheses (weak) |
| does the band fade above some exit tension (`worse_at_lower_tension`) | step the exit tension and note the tension at which the bands fade | true: S strong `foil_tension_lines`, C weak `tension_troughs_or_creases` (troughs need tension); false: C strong `foil_tension_lines`. Not specific: a latent thermal stripe's in-mill onset also falls with tension (section 14) |
| ironing-roll pressure (`changes_with_ironing_roll_pressure`) | change the pressure per side, one side at a time | true: S moderate `foil_tension_lines` and `tension_troughs_or_creases` |
| exit air blow-off (`changes_with_exit_air_blowoff`) | reduce or redirect the blow-off, alone | true: S moderate `foil_tension_lines`; NEUTRAL for the friction / oil-film band |
| roll wiper cleaning (`changes_after_roll_wiper_cleaning`) | clean the wipers and watch the bands | true: S strong `roll_surface_band` (wiper debris), C weak `nozzle_thermal_stripe`; false: C weak `roll_surface_band` |
| does it track speed changes (`tracks_speed_changes`) | note whether the band appears, moves or fades when the mill speed changes | true: S strong `heat_streak_or_film_variation` (friction or oil-film band); false: C weak for it; NEUTRAL for the nozzle hypothesis (a thermal stripe follows the heat input slowly) |
| did a wider coil follow a narrower one (`appeared_after_narrower_coil`) | check the rolling sequence before the bands started | true: S strong `roll_surface_band` (wide after narrow, without a backup-roll change) |
| band spacing (`band_spacing_m`, or the observed positions) | measure the distance between neighbouring fine lines | regular 5-20 mm (the published pitch [BF-S21, excerpt]; a stated `band_spacing_m` counts as regular): S strong `foil_tension_lines`; 3-30 mm or irregular: S weak; above 60 mm: C weak for it; also tested against the nozzle, zone and trough pitches |
| disappears after a backup-roll change (`disappears_after_backup_roll_change`) | note whether the bands go with a backup-roll change | true: S moderate `roll_surface_band` (backup-roll lines printed through the work roll) and then "positions stay after a work-roll change" counts only as a weak contradiction |

The existing lengthwise observations of section 5.1 (positions on consecutive coils, work-roll
change, zone switching, duration) keep their weight at foil gauge. For a lengthwise case with
an exit gauge below 100 um `recommended_next_measurements` adds one line per foil observation
still `null` (step the exit tension; ironing-roll pressure and blow-off one at a time; clean
the wipers; speed changes; wide after narrow) and always the online / offline comparison.

### 3.9 The battery-foil demo

`scenarios/band_diagnosis_battery_foil.json` (`synthetic: true`; its `provenance` gives the
reasoning for every input). The route is the plant's (plant statements: 50 um input, two
single-sheet passes, final usually 17-19 um, down to 12 um; intermediate gauge, alloy and
temper not stated); the intermediates 30 um and 25 um and the stock route down to 50 um are
assumed, and every mill and material number is synthetic. Mill: single-stand four-high foil
mill, work roll 0.27 m diameter, backup roll 0.75 m, barrel 1.5 m, strip 1.2 m centred;
half-stack masses 1100 / 9000 kg, work-backup contact 2.0e10 N/m, housing 6.0e9 N/m (planner
estimates scaled from the sheet demo mill [D]); 3 m spans. Schedule: S1-S3
0.26 -> 0.135 -> 0.085 -> 0.050 mm at 9.5, 10.5 and 11.5 m/s (assumed stock route), F1
0.050 -> 0.030 mm at 13 m/s and F2 0.030 -> 0.018 mm at 10 m/s (the plant's two passes), and the
thinnest product's alternative route ALT1 0.050 -> 0.025 mm at 13 m/s (50 %, 25 um assumed) and
ALT2 0.025 -> 0.012 mm at 10 m/s (52 %). The speeds follow the published practice of section 3.1:
final single-sheet passes 600 m/min (inside 450-650 m/min), earlier passes 570-780 m/min (inside
550-1000 m/min). Case pass F1, tensions 35 / 40 MPa, supplied flow stress 175 MPa, friction 0.03
on every pass, `bite_model: auto`. Flow stress 150-185 MPa along the schedule (no hardening law):
180 MPa on F2 (18 um) and 185 MPa on ALT2 (12 um) lie inside the ranges of the standard
proposal 1235-H18 (175-220 MPa at 18 um, at least 180 MPa at 12 um), so they were kept;
the plant has not stated the alloy and temper, so `material.alloy` AA1235 and temper H18 are
the literature proposal to confirm (`material.alloy_temper_stated: false`). `material.product:
"battery_collector_foil"` (section 3.1); `material.final_pass_doubled: false` (plant
statement). Neat-oil spray header of 28 nozzles at 52 mm
pitch, mean spray coefficient 3.4 kW/m2K (the middle of the SIMULATED 2.5-4.3 kW/m2K for
kerosene on a work roll [PT-T18], read as an excerpt of a garbled mirror; 2 kW/m2K before
SPEC14); oil 1.6 mPa s, work-roll Rq 0.15 um, strip Rq 0.2 um. Strip heat share
0.22 (each work roll 0.39): the middle of the only measured foil-mill partition, strip
0.11-0.33 [PT-T16], read as an ABSTRACT only and a net balance (0.84 before SPEC14, as in the
sheet demo). `model_options.thermal_sensitivity: "full"` keeps the old values as rows of the
sensitivity block (section 3.12).

Planted causes: nozzle 11 (0.62 m) partly blocked at flow level 0.45, and a 20 s closure of
the zone valve of nozzles 18-19. Observations were generated from the model itself at the
case pass F1: positions 0.623 and 0.988 m (the model steady stripe and event stripe peaks),
continuity both, intermittent duration 310 s (the model's after-release visible time at the
moved heat partition, rounded to 10 s; 80 s before), loose / buckle, visible only after tension
release, positions repeat across coils and do not move after a work-roll change, change with
zone switching, do not change after roll wiper cleaning, do not track speed changes; the final
pass is rolled single-sheet (`material.final_pass_doubled: false`, plant statement);
`worse_at_thinner_gauge` and `worse_at_lower_tension` are left `null` (the model gauge trend
does not reproduce the first, and the second does not separate tension lines from a latent
stripe).

Results (`artifacts/band_diagnosis/battery-foil-demo.result.json`): bite heat 87.4 kW/m at
the case pass; healthy thermal crown 8.96 um (9.63 um with the actual header); one steady
stripe, peak 2.96 um at 0.6225 m, half-peak width 0.18 m, next to nozzle 11; 25.1 I-units
with the feedback (not saturated), 3.12e+03 compliance only, 8304 rigid bound; hidden under mill
tension (utilisation 0) and visible after release (utilisation 6269); in-mill onset 6.81 um,
after-release onset 0.239 um (reporting-limited). The whole-sheet released indicator reads
`GLOBAL_BUCKLE_AFTER_RELEASE` (utilisation 1.894e+04) for this 25.1 I-unit band. The valve event:
local spray coefficient 4293 -> 2171 W/m2K, net surface flux change 2.289e+04 W/m2, initial growth
0.145 um/s analytic against 0.12 um/s simulated; peak 2.12 um at the monitor (1.01 m)
after 20 s (stripe peak 2.33 um at 0.9875 m), 21 I-units, hidden in the mill and visible
after release; the in-mill threshold (5.89 um) is never reached; the after-release threshold
(0.206 um, reporting-limited) is crossed 1.62 s after the valve closes and the band stays
visible after release for 311 s (band life 315 s): a 20 s valve closure leaves a band for
about five minutes. Troughs: wavelength 0.161 m (entry span) and 0.12 m (exit span); thresholds
only, the lateral compressive stress is not supplied. Chatter is flagged
`CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT`: with bite damping (beta 0.5) the case pass is
stable over the whole scanned speed range; without it the critical speed is 6.36 m/s against
13 m/s operating, and the onset frequency 2133 Hz lies above the 849 Hz span-wave limit of the
3 m spans. Energy residuals: steady 1.1e-9, events 7.8e-14.

| rank | hypothesis | standing | score (before SPEC12 stage B) |
|---|---|---|---|
| 1 | `nozzle_thermal_stripe` | CONSISTENT_LEADING | 19 (19) |
| 2 | `cooling_zone_switching_transient` | CONSISTENT | 16 (16) |
| 3 | `profile_flatness_mismatch` | CONSISTENT | 5 (5) |
| 4 | `heat_streak_or_film_variation` | CONSISTENT | 4 (4) |
| 5 | `tension_troughs_or_creases` | CONSISTENT | 4 (4) |
| 6 | `incoming_ridge_coil_buildup` | CONSISTENT | 1 (1) |
| 7 | `oil_carryover_drips_or_stain` | CONSISTENT | 1 (1) |
| 8 | `coil_or_mandrel_locked_marks` | NOT_ASSESSABLE | 0 (0) |
| 9 | `foil_tension_lines` | WEAKENED | 0 (-1) |
| 10-20 | `grinding_feed_marks`, `roll_surface_band` and the nine other transverse hypotheses | CONTRADICTED | -3 to -9 (unchanged) |

Both planted causes come first and second. The nozzle hypothesis matches the position
0.623 m and the zone hypothesis 0.988 m; the gap 0.365 m is 7 nozzle pitches. Also consistent:
the profile / flatness mismatch scores 5 from the orientation, the loose / buckle appearance
and "visible only after tension release"; the heat-streak hypothesis scores 4 from the
continuity, the boundary regime and the film ratio 0.551 (inside 0.3-3), less two weak
contradictions (positions repeat, does not track speed changes); tension troughs score 4 from
the orientation, the continuity and the exit gauge below 50 um (weak, counted because the
continuity supports): the 365 mm gap lies at 2.27 x the entry-span and 3.03 x the exit-span
trough wavelength, outside the 0.5-2 band, so it gives no spacing support.
`foil_tension_lines` is weakened by the 365 mm spacing (C weak under the revised rule of
section 6.2, moderate before; hence 0 instead of -1) and the loose / buckle appearance (C weak),
and its gauge support is gated (section 6.1). `roll_surface_band` is contradicted strongly by
"positions do not change after a work-roll change". Adding the alternative route and the
product did not change any other score.

**Product check** (`product_check`, section 3.1): alloy designation used `1235`, temper H18;
no flag. The final passes are F2 (the last pass of the plant's route) and ALT2 (the thinnest);
both are inside every published span checked (final gauge, per-pass and final-pass reduction,
final-pass entry gauge, exit speed, rolled mode, single-sheet final gauge, alloy and temper
against the grade-table row of the pass's exit-gauge band (H18 and H19 both consistent), mean
flow stress as an indicator against that row: standard minimum to the top of the typical
producer range). The case pass, F1 and ALT1
are inside too; S1-S3 read `BELOW_PUBLISHED_RANGE` for the flow-stress indicator only (150-168 MPa
against the finished-foil span; an indicator, and no flag, because they are neither the case
pass nor a final pass). Nearest published passes: for the case pass 59 -> 30 um [BF-S14,
excerpt], 50 -> 25 um [BF-S15, full text] and 55 -> 25 um [BF-S12, excerpt]; for the final pass
(ALT2) 25 -> 12 um [BF-S12, excerpt], the doubled 24x2 -> 12x2 um [BF-S17, trade page] and
26 -> 13 um [BF-S12, excerpt]. The check is evidence-neutral: it changes no score.

**Material selection** (`material_selection`, section 3.1): final pass ALT2 at 12 um in the
>10–13 um band, case pass in the >20–30 um band; standard proposal
1235-H18 (180 MPa, the standard minimum; evidence medium),
high-strength proposal 1100-H18 (250 MPa; evidence medium); the other route end F2
(18 um) has standard 1235-H18 (210 MPa, evidence vendor-level) and high-strength 1100-H18
(220 MPa, evidence WEAK: fallback rule). The case's AA1235-H18 is the usual standard choice
(alloy `USUAL_CHOICE`, temper `CONSISTENT`); flow stresses: F2
`BETWEEN_STANDARD_MINIMUM_AND_TYPICAL_RANGE`, ALT2 `AT_OR_ABOVE_STANDARD_MINIMUM_NO_TYPICAL_PUBLISHED`, F1 (the case pass) and ALT1 `INSIDE_TYPICAL_RANGE` (>20-30 um band),
S1-S3 outside every published band; yield stress 165 MPa `INSIDE_RANGE`
of the assumed proof-strength range. Flag `MATERIAL_NOT_STATED_LITERATURE_PROPOSAL_SHOWN` (the plant has not stated the
material). It changes no number and no score.

What the demo shows the tool cannot say: the 18 um final pass F2 has a bite only in the
extended domain (force inside the reported range, unvalidated); the 12 um ALT2 bite is NOT
CREDIBLE (6.19 kN/mm, 2.7 times the top of the reported range) and is kept out of the trend
statements, while its bite-free thresholds stand; the 30 um case pass lies below every reported
closed-gap onset (`BELOW_EVERY_REPORTED_ONSET`) with no roll-kissing model, and the lever and
gauge-control sections carry the open-gap note. The CLI run of this demo took about 56 s on
this container (the full thermal sensitivity block included). It tests the screening logic at foil gauge, not the physics.

### 3.10 Product survey

`physicroll/band_survey.py` builds one synthetic **final pass per catalogue product** (27
products, every one with a published final gauge) from catalogue data only and evaluates it
with the engine's own models, on one stated synthetic mill per gauge class: the battery-foil
demo mill (work roll radius 0.135 m, strip 1.2 m) for an exit
gauge below 0.2 mm and the lengthwise demo mill (radius
0.2 m, strip 1.5 m) above. Run it with

```
python -m physicroll.band_survey --out artifacts/band_diagnosis
python -m physicroll.band_cli --product-survey --out artifacts/band_diagnosis
```

To run it on your own machine instead of the demo mills, with your own pass values or with starter case files, see section 5.3. It writes `product-survey.result.json` (schema `physicroll.band_survey.v1`, status `SYNTHETIC_SURVEY_LITERATURE_INPUTS_UNVALIDATED`) and
`product-survey.report.html` (about 27 s on this container).

**How the survey pass is built** (every row lists, in `catalogue_values_used`, each value taken
from the catalogue with its source ids and read status, and, in `assumed_values`, each
assumption; `vendor_level_input` marks a row resting on vendor or trade-page data):

- gauges: the last pass of a published schedule whose last step is one published pass
  (preferring an exit inside the published final-gauge span, the product's own rolling mode,
  then the exit nearest the middle of that span); otherwise the geometric middle of the
  published final-gauge span as exit, with the entry from the middle of the published
  final-pass reduction span, else the per-pass span, else (foil families) the general
  packaging-foil per-pass span, else an assumed 30 %;
- flow stress: the as-rolled strength of the pass, the median of the published
  tensile-strength numbers of an H1x temper (standard grade where both are published). For O,
  H2x and other annealed final tempers the final cold pass is rolled hard and annealed
  afterwards: a published as-rolled H1x strength of the product is used if there is one,
  otherwise an ASSUMED 180 MPa, labelled
  (19 of the 27 rows); annealed strength is never used as rolling flow stress;
- tensions 0.2 / 0.23 of the flow stress, friction 0.03 (the demos'
  value), speed from the middle of the published final-pass (or pass) speed span, else the demo
  mill's speed;
- a doubled (pack-rolled) final pass is not modelled: its bite-dependent cells read "doubled
  pass not modelled" and its bite-free thresholds are per sheet;
- credibility: the engine's marks; the force range (0.9-2.3 kN/mm) is reported for
  battery-foil passes only, so for another product an extended-domain bite is marked
  `NO_REPORTED_LOAD_RANGE_IN_CATALOGUE` (unvalidated) instead.

Per product it reports the bite model and flags, force per width, the closed-gap flag (exit
below 100 um), the strip-to-mill modulus ratio, the bite-free thresholds (flatness dead band,
critical coil ridge height at the outer coil radius, trough onset and roller-wrinkle
thresholds of the exit span), the response to a 1 um Gaussian roll stripe at the strip
centre (linear-feedback I-units, in-mill and after-release onset heights), the chatter critical
speeds with and without bite damping against the survey speed with the span-wave reliability
flag, the product-check verdicts of the survey pass and the catalogue's named defects.

Survey table (from `artifacts/band_diagnosis/product-survey.result.json`; force in kN/mm,
dead band in I-units, ridge height in um, trough onset in kPa, roller-wrinkle threshold in
MPa, stripe: I-units of the 1 um stripe; in-mill / after-release onset height in um;
chatter: critical speed with / without bite damping at the survey speed, m/s):

| product | survey pass | bite | dead band | ridge | trough | roller wrinkle | 1 um stripe | chatter | marks |
|---|---|---|---|---|---|---|---|---|---|
| 1 `battery_collector_foil` | 20 -> 13, foil, 180 MPa | mattress, 2.4 | 0.00349 | 0.0743 | -14.2 | -4.45 | 1.1 I; not reached / 1.83 | stable / 4.11 at 13.6, not reliable | NOT CREDIBLE (x1); extended domain; closed gap; vendor-level input |
| 2 `battery_pouch_laminate_foil` | 64 -> 30, foil, 180 MPa | mattress, 1.41 | 0.0165 | 0.171 | -32.7 | -10.3 | 7.1 I; 8.46 / 0.285 | stable / 5.33 at 7.92, not reliable | extended domain; closed gap; flow stress assumed |
| 3 `battery_thick_collector_foil` | 65.8 -> 31.6, foil, 185 MPa | mattress, 1.38 | 0.0182 | 0.187 | -34.9 | -10.8 | 7.54 I; 8.2 / 0.268 | stable / 5.59 at 10, not reliable | extended domain; closed gap; vendor-level input |
| 4 `battery_carbon_coated_base_foil` | 34.2 -> 16.4, foil, 140 MPa | mattress, 1.48 | 0.00538 | 0.0687 | -15.8 | -5.62 | 3.95 I; 11.8 / 0.507 | stable / 3.55 at 10, not reliable | extended domain; closed gap; vendor-level input |
| 5 `battery_tab_foil` | 114 -> 54.8, foil, 180 MPa | Hitchcock, 0.951 | 0.0507 | 0.313 | -59.7 | -18.8 | 24.3 I; 2.52 / 0.0833 | 8.58 / 3.42 at 10 | extended domain; closed gap; flow stress assumed; vendor-level input |
| 6 `capacitor_anode_foil_high_voltage` | 180 -> 86.6, foil, 180 MPa | Hitchcock, 0.888 | 0.119 | 0.495 | -94.4 | -29.7 | 36.5 I; 1.71 / 0.0555 | 5.27 / 1.06 at 10 | extended domain; closed gap; flow stress assumed |
| 7 `capacitor_anode_foil_low_voltage` | 169 -> 81.2, foil, 180 MPa | Hitchcock, 0.892 | 0.105 | 0.464 | -88.5 | -27.8 | 34.8 I; 1.8 / 0.0583 | 5.61 / 1.22 at 10 | extended domain; closed gap; flow stress assumed |
| 8 `capacitor_cathode_foil` | 72.1 -> 34.6, foil, 180 MPa | mattress, 1.25 | 0.0216 | 0.198 | -37.7 | -11.9 | 8.8 I; 6.85 / 0.23 | 24.9 / 5.68 at 10, not reliable | extended domain; closed gap; flow stress assumed |
| 9 `pharma_blister_lidding` | 55.8 -> 26.8 per sheet, foil, 150 MPa | doubled pass not modelled | 0.0134 | 0.123 | -26.7 | -9.18 | doubled pass not modelled | doubled pass not modelled | closed gap; vendor-level input |
| 10 `pharma_cold_form_foil` | 108 -> 52, foil, 180 MPa | Hitchcock, 0.967 | 0.046 | 0.297 | -56.7 | -17.8 | 22.9 I; 2.67 / 0.0886 | 9.22 / 4.06 at 10 | extended domain; closed gap; flow stress assumed; vendor-level input |
| 11 `pharma_strip_pack_foil` | 65.8 -> 31.6, foil, 180 MPa | mattress, 1.32 | 0.0182 | 0.181 | -34.5 | -10.8 | 7.78 I; 7.79 / 0.26 | stable / 5.51 at 10, not reliable | extended domain; closed gap; flow stress assumed; vendor-level input |
| 12 `household_foil` | 23 -> 10.5 per sheet, foil, 180 MPa | doubled pass not modelled | 0.00235 | 0.06 | -11.4 | -3.6 | doubled pass not modelled | doubled pass not modelled | closed gap; flow stress assumed; vendor-level input |
| 13 `household_foil_heavy_duty` | 44.2 -> 21.2 per sheet, foil, 180 MPa | doubled pass not modelled | 0.00867 | 0.121 | -23.1 | -7.26 | doubled pass not modelled | doubled pass not modelled | closed gap; flow stress assumed |
| 14 `converter_foil` | 14 -> 6.5 per sheet, foil, 180 MPa | doubled pass not modelled | 0.000961 | 0.0371 | -7.09 | -2.23 | doubled pass not modelled | doubled pass not modelled | closed gap; flow stress assumed; vendor-level input |
| 15 `cigarette_liner_foil` | 13.5 -> 6.48 per sheet, foil, 180 MPa | doubled pass not modelled | 0.000956 | 0.037 | -7.07 | -2.22 | doubled pass not modelled | doubled pass not modelled | closed gap; flow stress assumed; vendor-level input |
| 16 `dairy_lidding_foil` | 77.9 -> 37.4, foil, 180 MPa | mattress, 1.19 | 0.0249 | 0.214 | -40.8 | -12.8 | 9.77 I; 6.21 / 0.207 | 19.6 / 5.8 at 10, not reliable | extended domain; closed gap; flow stress assumed; vendor-level input |
| 17 `container_foil_wrinkle_wall` | 151 -> 72.7, foil, 180 MPa | Hitchcock, 0.899 | 0.0858 | 0.415 | -79.3 | -24.9 | 31.8 I; 1.94 / 0.0637 | 6.29 / 1.58 at 10 | extended domain; closed gap; flow stress assumed; vendor-level input |
| 18 `container_foil_smooth_wall` | 279 -> 134, foil, 180 MPa | Hitchcock, 0.902 | 0.267 | 0.766 | -146 | -45.9 | 51.1 I; 1.26 / 0.0397 | 3.17 / 0.469 at 10 | extended domain; flow stress assumed; vendor-level input |
| 19 `container_foil_retortable` | 191 -> 91.7, foil, 180 MPa | Hitchcock, 0.888 | 0.132 | 0.524 | -100 | -31.4 | 38.2 I; 1.63 / 0.0531 | 4.95 / 0.937 at 10 | extended domain; closed gap; flow stress assumed; vendor-level input |
| 20 `brazed_fin_stock` | 128 -> 89.4, foil, 148 MPa | Hitchcock, 0.484 | 0.126 | 0.4 | -88.2 | -30.6 | 37.9 I; 1.36 / 0.0534 | 6.87 / 2.31 at 10 | closed gap; vendor-level input |
| 21 `brazing_sheet_tube` | 404 -> 283, sheet, 180 MPa | Hitchcock, 1.05 | 0.709 | 1.94 | -231 | -80.8 | 30 I; 2.29 / 0.0676 | 7.8 / 2.24 at 12 | flow stress assumed; vendor-level input |
| 22 `hvac_fin_stock` | 130 -> 82.46, foil, 175 MPa | Hitchcock, 0.676 | 0.108 | 0.456 | -88.7 | -28.2 | 33.6 I; 1.81 / 0.0604 | 7.34 / 2.45 at 10 | closed gap |
| 23 `litho_sheet` | 494.5 -> 272, sheet, 135 MPa | Hitchcock, 0.955 | 0.659 | 1.34 | -193 | -77.6 | 39.7 I; 1.32 / 0.0511 | 3.76 / 0.878 at 12 | – |
| 24 `can_body_stock` | 414 -> 290, sheet, 180 MPa | Hitchcock, 1.05 | 0.742 | 1.99 | -237 | -82.8 | 30.2 I; 2.28 / 0.0672 | 7.76 / 2.23 at 12 | flow stress assumed |
| 25 `can_end_stock` | 391 -> 274, sheet, 180 MPa | Hitchcock, 1.04 | 0.668 | 1.88 | -224 | -78.2 | 29.8 I; 2.3 / 0.0681 | 7.87 / 2.27 at 12 | flow stress assumed |
| 26 `closure_sheet` | 303 -> 212, sheet, 148 MPa | Hitchcock, 0.782 | 0.415 | 1.16 | -157 | -60.5 | 29.7 I; 1.85 / 0.0683 | 7.28 / 2.14 at 12 | vendor-level input |
| 27 `transformer_strip` | 756 -> 529, sheet, 180 MPa | Hitchcock, 1.26 | 2.27 | 3.63 | -433 | -151 | 35.4 I; 2.17 / 0.114 | 6.73 / 1.91 at 12 | flow stress assumed; vendor-level input |

**Rankings** (most sensitive first; a ranking uses only rows carrying the quantity, never mixes
a not-credible bite with credible ones, and lists every excluded row with its reason):

- **Coil ridges (critical ridge height at the outer coil radius)**: most sensitive cigarette_liner_foil (0.037 um), converter_foil (0.0371 um), household_foil (0.06 um); rank correlation with thinner gauge +0.99; none excluded.
- **Troughs and creases in the exit span (trough onset lateral stress, magnitude)**: most sensitive cigarette_liner_foil (7.07 kPa), converter_foil (7.09 kPa), household_foil (11.4 kPa); rank correlation with thinner gauge +1.00; none excluded.
- **Roller wrinkles on the deflector roll (threshold magnitude)**: most sensitive cigarette_liner_foil (2.22 MPa), converter_foil (2.23 MPa), household_foil (3.6 MPa); rank correlation with thinner gauge +1.00; none excluded.
- **Cooling stripes visible in the mill (in-mill onset height of a roll stripe)**: most sensitive container_foil_smooth_wall (1.26 um), litho_sheet (1.32 um), brazed_fin_stock (1.36 um); rank correlation with thinner gauge -0.66; 6 excluded (bite NOT CREDIBLE (force outside the range reported for battery foil); doubled pass not modelled).
- **Cooling stripes visible after tension release (after-release onset height, an upper bound where reporting-limited)**: most sensitive container_foil_smooth_wall (0.0397 um), litho_sheet (0.0511 um), container_foil_retortable (0.0531 um); rank correlation with thinner gauge -0.62; 6 excluded (bite NOT CREDIBLE (force outside the range reported for battery foil); doubled pass not modelled).
- **Chatter margin (survey speed over the critical speed without bite damping)**: most sensitive container_foil_smooth_wall (21.3), litho_sheet (13.7), container_foil_retortable (10.7); rank correlation with thinner gauge -0.28; 12 excluded (bite NOT CREDIBLE (force outside the range reported for battery foil); chatter onset above the span-wave limit (not reliable); doubled pass not modelled).

The generated summary (`summary`): "27 catalogue products, one synthetic final pass each: 22 with a roll bite, 5 doubled (bite not modelled), 1 with a bite marked not credible, 19 with an assumed flow stress. Coil ridges (critical ridge height at the outer coil radius): most sensitive cigarette_liner_foil (6.48 um), converter_foil (6.5 um), household_foil (10.5 um); the thinner the product, the more sensitive (rank correlation +0.99). Troughs and creases in the exit span (trough onset lateral stress, magnitude): most sensitive cigarette_liner_foil (6.48 um), converter_foil (6.5 um), household_foil (10.5 um); the thinner the product, the more sensitive (rank correlation +1.00). Roller wrinkles on the deflector roll (threshold magnitude): most sensitive cigarette_liner_foil (6.48 um), converter_foil (6.5 um), household_foil (10.5 um); the thinner the product, the more sensitive (rank correlation +1.00). Cooling stripes visible in the mill (in-mill onset height of a roll stripe): most sensitive container_foil_smooth_wall (134 um), litho_sheet (272 um), brazed_fin_stock (89.4 um); no clear gauge order (rank correlation -0.66); 6 excluded. Cooling stripes visible after tension release (after-release onset height, an upper bound where reporting-limited): most sensitive container_foil_smooth_wall (134 um), litho_sheet (272 um), container_foil_retortable (91.7 um); no clear gauge order (rank correlation -0.62); 6 excluded. Chatter margin (survey speed over the critical speed without bite damping): most sensitive container_foil_smooth_wall (134 um), litho_sheet (272 um), container_foil_retortable (91.7 um); no clear gauge order (rank correlation -0.28); 12 excluded. These are model sensitivities on one synthetic mill per gauge class with literature inputs, not plant defect rates."

**How to read it.** The bite-free thresholds fall with gauge, so the thinnest products
(cigarette liner, converter and household foil, all doubled) are the most sensitive to coil
ridges, troughs and roller wrinkles. The cooling-stripe and chatter rankings show no clear gauge
order across the two mills; within the foil mill the in-mill ranking runs against gauge (rank
correlation of "more sensitive" with "thinner" -0.99 over 15 foil products),
the finding of section 3.5: a given roll stripe is hidden more, not less, in thinner foil. The
battery collector foil's survey pass (published 20 -> 13 um) has a bite force of
2.4 kN/mm, x1.04 the top of the range reported for battery-foil passes, so its
bite is NOT CREDIBLE and it is excluded from every bite-dependent ranking.

**What it is not.** One synthetic mill per gauge class, the same friction and tension fractions
for every product, literature inputs (many from excerpts, patents, standards previews and
vendor or trade pages), many assumed flow stresses, open-gap models in the closed-gap regime,
nothing validated. It compares model sensitivities, not plant defect rates.

### 3.12 Process temperatures

The plant asked for process temperatures because thermal interaction with the material and the
coolant affects mechanical properties, roll wear and surface finish. A third research pass
(sources `PT-`, `docs/thin-gauge-products.md`, "Process temperatures in foil rolling") gives
the temperature map below; the tool compares the case with it in `thermal_check`
(`physicroll/band_thermal.py`, evidence-neutral, never changes a score) and shows how the
cooling-stripe result depends on the two least certain inputs in `width.thermal_sensitivity`.
**The tool has no roll-wear model, no temperature-to-surface-finish (dyne, gloss) model and no
model of property change after rolling**: what the research says about those is carried as
literature statements, not model outputs.

**Temperature map** (from `physicroll.band_products.TEMPERATURE_MAP`, by script):

| temperature | typical | limit |
|---|---|---|
| Coil entering a pass | Not stated for foil; 60–100 °C entry gave exit above 150 °C at sheet gauge. [PT-T3] | ≤75 °C before the battery-foil final pass (≥10 h natural cooling). [PT-T1] |
| Strip inside the bite | Calculated to reach about 200 °C at high speed. [PT-T4] | Above 200 °C needed before softening shows. [PT-T4] |
| Coil off the final pass, battery foil (20→13 µm, 35 %, oil 42 °C) | 77.2 °C at 550 m/min; 97.9 and 99.7 °C at 600 m/min; prior art "above 90 °C". [PT-T1, PT-T2] | ≤80 °C (≤90 °C at the least), also when slit within 30 min. [PT-T1, PT-T2] |
| Coil leaving a cold-mill pass (sheet gauge) | "About 121 °C"; cold rolling defined as below 129 °C; metal at 20–200 °C. [PT-T14, PT-T13, PT-T37] | No stated limit; trouble above 150–160 °C. [PT-T3] |
| Oil supply, roughing and intermediate | 30–40 °C and 40–50 °C. [PT-T5, PT-T6] | - |
| Oil supply, finishing | 50–60 °C general foil; 40–45 °C battery foil. [PT-T5, PT-T1, PT-T6] | Window 38–55 °C at one plant; legal cap 68 °C (cold mill), 71 °C (foil mills) in one US rule. [PT-T3, PT-T13] |
| Hot edge spray | Oil up to 120 °C in 25 mm zones. [PT-T21, PT-T5] | - |
| Work-roll surface and bulk | Not found measured; a cold-mill model uses 50 °C surface with 35 °C oil. [PT-T18] | Thermal load 40–50 kcal/m²s of roll surface (167–209 kW/m², computed by the report). [PT-T4] |

**How cooling becomes a band in this tool** (one chain, section 7 for the physics): bite heat
per width (plastic work plus interface slip, section 8.2) -> the share that goes into each work
roll, `(1 - strip share) / 2` -> the spray header (nozzle footprints, flow level of each
nozzle, spray coefficient) -> the roll temperature field (axial and radial conduction,
`roll_thermal.py`) -> thermal expansion, compared with the same roll under a healthy header ->
a local change of the roll gap, turned into a local thickness change by the roll compliance,
the strip stiffness and the exit-tension feedback (`strip_shape.py`) -> extra length of that
fibre (I-units) -> latent under the mill tension or buckled in the mill, and visible or not
after tension release. A short event (a valve closure, an intermittent blockage) is the
transient of the same chain. **Not modelled**: any effect of temperature on flow stress or on
the oil film across the width, the per-revolution surface temperature cycle, the
roll-strip heat coupling (bite heat is computed from the pass, not fed back), property change
after rolling, roll wear and surface finish.

**The heat-partition finding and what it did to the demo.** The only measured foil-mill heat
balance puts 0.67-0.89 of the heat into the rolls and 0.11-0.33 into the strip [PT-T16, read as
an ABSTRACT only; a net balance, not necessarily the split inside the bite]. The battery demo
used a strip share of 0.84 (that of the sheet demo); it now uses the middle of the measured
range, 0.22 (each work roll 0.39), and the middle of the simulated spray range,
3.4 kW/m2K (no measured value on a roll exists; [PT-T18] simulated 2.5-4.3 kW/m2K on an aluminium
cold mill, read as an excerpt of a garbled mirror; a plate test gives about 5-13 kW/m2K,
computed [PT-T19]). With several times more heat in the roll the planted steady stripe grows
from 0.959 to 2.96 um and the valve event from 0.495 to 2.12 um; both stay hidden under
tension at the case pass and visible after release; the event is visible after release for
311 s instead of 81 s (the demo observation was regenerated from the model to 310 s); every
hypothesis score and the leader (`nozzle_thermal_stripe`) are unchanged. Sensitivity at the
case pass (`width.thermal_sensitivity`, `model_options.thermal_sensitivity: "full"`; stripe and
event scaled linearly with the roll heat at a fixed spray coefficient, checked by a direct
solve; the stripe is detected on every row's own scaled profile and its flatness states and, in
`full` mode, its onsets over its own extent are recomputed for every row, as a direct run at that
share would; in the default `partition` mode one onset window per spray coefficient is used, about
1 % from a direct run):

| strip share (per roll) | spray [kW/m2K] | stripe [um] | I-units | in mill / after release | stripe / in-mill onset | event peak [um] | event visible after release [s] |
|---|---|---|---|---|---|---|---|
| 0.22 (0.39) | 3.4 | 2.96 | 25.1 | latent under tension / manifest after tension release | 0.434 | 2.12 | 311 |
| 0.33 (0.335) | 3.4 | 2.54 | 21.5 | latent under tension / manifest after tension release | 0.373 | 1.82 | 276 |
| 0.11 (0.445) | 3.4 | 3.38 | 28.7 | latent under tension / manifest after tension release | 0.496 | 2.42 | 343 |
| 0.84 (0.08) | 3.4 | 0.607 | 5.12 | latent under tension / manifest after tension release | 0.0901 | 0.435 | 51.6 |
| 0.22 (0.39) | 2.5 | 3.87 | 32.7 | latent under tension / manifest after tension release | 0.567 | 2.3 | 371 |
| 0.33 (0.335) | 2.5 | 3.32 | 28.1 | latent under tension / manifest after tension release | 0.487 | 1.98 | 332 |
| 0.11 (0.445) | 2.5 | 4.42 | 37.4 | latent under tension / manifest after tension release | 0.647 | 2.63 | 406 |
| 0.84 (0.08) | 2.5 | 0.794 | 6.67 | latent under tension / manifest after tension release | 0.116 | 0.473 | 67.2 |
| 0.22 (0.39) | 4.3 | 2.4 | 20.4 | latent under tension / manifest after tension release | 0.356 | 1.96 | 272 |
| 0.33 (0.335) | 4.3 | 2.06 | 17.5 | latent under tension / manifest after tension release | 0.306 | 1.69 | 240 |
| 0.11 (0.445) | 4.3 | 2.73 | 23.3 | latent under tension / manifest after tension release | 0.406 | 2.24 | 301 |
| 0.84 (0.08) | 4.3 | 0.492 | 4.16 | latent under tension / manifest after tension release | 0.0731 | 0.403 | 41.8 |
| 0.22 (0.39) | 13 | 0.851 | 7.28 | latent under tension / manifest after tension release | 0.127 | 1.12 | 136 |
| 0.33 (0.335) | 13 | 0.731 | 6.25 | latent under tension / manifest after tension release | 0.109 | 0.959 | 116 |
| 0.11 (0.445) | 13 | 0.971 | 8.31 | latent under tension / manifest after tension release | 0.145 | 1.27 | 155 |
| 0.84 (0.08) | 13 | 0.175 | - | below reporting threshold / below reporting threshold | 0.0261 | 0.229 | 9.14 |
| 0.22 (0.39) | 2 | 4.67 | 39.4 | latent under tension / manifest after tension release | 0.684 | 2.41 | 421 |
| 0.33 (0.335) | 2 | 4.02 | 33.8 | latent under tension / manifest after tension release | 0.587 | 2.07 | 379 |
| 0.11 (0.445) | 2 | 5.33 | 45.1 | latent under tension / manifest after tension release | 0.78 | 2.76 | 459 |
| 0.84 (0.08) | 2 | 0.959 | 8.02 | latent under tension / manifest after tension release | 0.14 | 0.495 | 80.9 |

Only one combination changes a state: share 0.84 with 13 kW/m2K, where the stripe falls below the
reporting threshold. At the measured partition the same stripe held on every pass buckles in the
mill on the three assumed stock passes and stays latent on the plant's passes; the stripe each
pass would itself produce gives the same split (section 3.5, "two questions"). Both assume the
steady state, which takes 116 s to reach 50 % and 551 s to reach 90 % from a healthy header.

**Strip exit temperatures** (pass heating, `process.heating`; reused by `thermal_check`): at the
strip share 0.22, S1 54.8, S2 51.5, S3 57.1, F1 60.3, F2 66.1, ALT1 72.4, ALT2 72.9 C; at the former 0.84, S1 96.4, S2 84.1, S3 105, F1 117, F2 140, ALT1 164, ALT2 166 C. The measured partition brings
every modelled exit temperature below the published 80 C battery coil limit [PT-T1, PT-T2],
which the old partition exceeded on every pass. Two caveats stand: a strip exit temperature is
not a coil temperature, and the experimental mattress bite inflates the friction heat.

**`thermal_check` for the battery demo** (inputs, then outputs):

| item | case value | published | verdict | read status |
|---|---|---|---|---|
| strip heat fraction | 0.22 | 0.11-0.33 | `WITHIN_PUBLISHED_RANGE` | abstract_or_snippet |
| spray heat transfer coefficient | 3.4 kW/m2K | 2.5-4.3 kW/m2K | `WITHIN_PUBLISHED_RANGE` | excerpt |
| coolant temperature as oil supply | 45 C | 40-45 | `WITHIN_PUBLISHED_RANGE` | excerpt |
| oil inlet temperature | 45 C | 40-45 | `WITHIN_PUBLISHED_RANGE` | excerpt |
| oil viscosity 40c | 1.6 mPa s (dynamic) | 1.5-2.0 cSt (kinematic) | `NO_PUBLISHED_RANGE` | vendor_or_trade_page |
| spray footprint overlap | 0.688 | 0.1-0.3 | `ABOVE_PUBLISHED_LIMIT` | vendor_or_trade_page |

| pass (modelled strip exit) | value | published | verdict | final pass |
|---|---|---|---|---|
| S1 | 54.8 C | <= 80 | `WITHIN_PUBLISHED_RANGE` | no |
| S2 | 51.5 C | <= 80 | `WITHIN_PUBLISHED_RANGE` | no |
| S3 | 57.1 C | <= 80 | `WITHIN_PUBLISHED_RANGE` | no |
| F1 | 60.3 C | <= 80 | `WITHIN_PUBLISHED_RANGE` | no |
| F2 | 66.1 C | <= 80 | `WITHIN_PUBLISHED_RANGE` | yes |
| ALT1 | 72.4 C | <= 80 | `WITHIN_PUBLISHED_RANGE` | no |
| ALT2 | 72.9 C | <= 80 | `WITHIN_PUBLISHED_RANGE` | yes |

| output | value | published | verdict |
|---|---|---|---|
| stripe height on diameter | 5.92 um | 3.6-4.2 um | `ABOVE_PUBLISHED_RANGE` |
| thermal crown | 19.3 um | <= 30 um | `WITHIN_PUBLISHED_RANGE` |

The modelled stripe on diameter is above the simulated zone-cooling authority (about +-4 um on
diameter 20 revolutions after a zone change [PT-T18]) because a partly blocked nozzle is a
permanent, not a 20-revolution, disturbance; the thermal crown is inside the 30 um maximum
measured on a foil mill [PT-T25] (whether that is on diameter or radius is not stated). The
spray footprint overlap of the demo header, 69 %, is above the published 10-30 % (never above
50 %) [PT-T22, PT-T21]; the tool's spray screen has no overlap threshold (it flags only gaps
between fans) and is left as it is. The oil viscosity is not compared: the case gives a dynamic
viscosity, the literature a kinematic one, and the density is not a case input. Growth: the short event reaches half its peak in 9.25 s (axial decay time constant of a 52 mm stripe about 23 s, computed); the steady stripe builds up to 50 % in 116 s and to 90 % in 551 s (radial time constant 4-7 min computed for a 260 mm roll). A plant-identified flatness response of about 20 s is of the order of the short local (axial) time scale and of an event's rise, not of the minutes a steady stripe needs to build.
`thermal_check.quarter_barrel_note` is a positional note only (bands at 1/5-1/4 of the barrel from
each end, the quarter looseness of [PT-T38]); it changes no score. If
`width_model.roll_heat_fraction_per_roll` is given and disagrees with
`tribology.strip_heat_fraction` the result flags `HEAT_PARTITION_INPUTS_INCONSISTENT` (the roll
thermal model uses the first, pass heating the second); leave it null to derive it.

**Roll wear and surface finish (literature, not modelled).** More aluminium fines with higher oil
temperature, speed, reduction and roll roughness [PT-T15]; adsorbed films desorb as temperature
rises and the roll coating is re-deposited [PT-T37, PT-T27]; a small circumferential temperature
swing reduces thermal fatigue and wear (a general cold-mill statement) [PT-T23]; harder rolls
(115-125 HSD) held shape on strong foil [PT-T29]. Surface: heat stripes, stripes between spray
footprints, buckles after a spray is turned down and quarter looseness are documented in words
only; dyne is set mainly by the oil carried out and can fall from above 32 to below 30 within
12-24 h [PT-T29, PT-T30]; no source links oil, roll or strip temperature directly to dyne, gloss
bands or white streaks.

**Logs worth taking** (added to `recommended_next_measurements` for foil gauge or a battery
product): coil temperature before and after the final pass (<= 75 / <= 80 C), oil supply
temperature against 38-45 C, dyne at 0 h and 24 h.

## 4. How to run

```
python -m physicroll.band_cli scenarios/band_diagnosis_battery_foil.json --out artifacts/band_diagnosis
python -m physicroll.band_cli scenarios/band_diagnosis_lengthwise_bands.json --out artifacts/band_diagnosis
python -m physicroll.band_cli scenarios/band_diagnosis_thin_gauge_chatter.json --out artifacts/band_diagnosis
python -m physicroll.band_cli scenarios/band_diagnosis_bearing_order.json --out artifacts/band_diagnosis
python -m physicroll.band_cli my_case.json --out my_output_dir
python -m physicroll.band_cli --product-survey --out artifacts/band_diagnosis   # section 3.10
```

Each run validates the case, writes `<case-name-slug>.result.json` (deterministic: sorted
keys, no timestamps) and `<case-name-slug>.report.html` atomically, and prints the ranked
standings. The committed result and report files are the output of these four commands
(regenerated with the stage-B tension-line rules of section 6.2; for the three sheet demos
that changed only the `foil_tension_lines` texts and, in the lengthwise demo, its score). On
this container (Python 3.13) they took about 23 s (battery foil), 52 s (lengthwise), 18 s
(thin-gauge chatter) and 7 s (bearing order); expect different times on other machines. From Python:
`from physicroll.band_diagnosis import load_case, diagnose`.

Which demo to look at:

| demo | schema | what it shows |
|---|---|---|
| `scenarios/band_diagnosis_battery_foil.json` | v2 | battery (current-collector) foil on the plant's route (50 um input, two single-sheet passes): case pass 0.050 -> 0.030 mm, the final pass to 18 um and an alternative 12 um final pass: lengthwise bands at two width positions from a partly blocked nozzle (continuous) and a zone-valve closure (short-lived), hidden under mill tension and visible after release; the `foil_regime` block, the experimental mattress bite and its extended domain with the credibility mark (18 um inside the reported force range, 12 um not credible), the product check, the foil gauge trend (section 3.9) |
| `scenarios/band_diagnosis_lengthwise_bands.json` | v2 | lengthwise bands at three width positions, one continuous (a partly blocked nozzle) and two short-lived (cooling-zone switching), worse at thinner gauge; every phase-2 section (roll thermal, shape, gauge trend, events, process, gauge control, drive, incoming hardness) |
| `scenarios/band_diagnosis_thin_gauge_chatter.json` | v1 | transverse third-octave chatter at the final pass of a six-pass schedule; the chatter schedule sweep and levers |
| `scenarios/band_diagnosis_bearing_order.json` | v1 | transverse marks from a work-roll bearing order (speed-independent pitch) |

All four are `synthetic: true` and their observations were generated from the model
itself, so they test the screening logic, not the physics.

## 5. Filling in the template for your mill

Copy `scenarios/band_diagnosis_template.json` (schema `physicroll.band_case.v2`,
`synthetic: false`, which adds the flag `USER_SUPPLIED_INPUTS_NOT_VERIFIED`). Its `notes`
explain every field. Replace the mill, pass and material numbers with your own, in SI
units (m, Pa, kg, N/m, m/s, Hz, rad, K); the values in the template are the synthetic demo
mill. Keys are strict: unknown or missing keys are rejected, except the six optional foil
observations (section 3.8), `width_model.shape_inputs` and `material.final_pass_doubled`
(whether the thinnest pass is rolled doubled: `null` not stated, `false` single-sheet, `true`
doubled; read only in the foil regime, section 3.1), which may be absent. **Leave an observation `null`
when nobody has looked**: `null` always gives `NOT_OBSERVED` evidence and never counts
against a hypothesis. Band positions closer than 1 mm to each other (exact repeats included)
are one band at their mean: the merged list is used everywhere (position and interval
matching, spacing, trough and tension-line rules, the report chart), the result keeps both
lists in `observation_adjustments` and sets `DUPLICATE_BAND_POSITIONS_MERGED`. Rejected at
validation on purpose: `intermittent_duration_s` of 0 (no observation: use `null`),
`band_spacing_m` above 10 m (beyond any strip) and a cooling-zone event of zero duration
(it switches nothing).

Schema v2 is v1 plus six optional sections (`null` = not supplied; the result section then
says `NOT_SUPPLIED`), the option `model_options.bite_model`, thirteen lengthwise
observation fields and six optional foil observation fields (absent = `null`, so v2 files
written before them still load; a v1 case may not carry them). v1 case files still load and
run unchanged.

| section | what it switches on |
|---|---|
| `width_model` | work-roll thermal model and strip-shape chain (lengthwise bands): roll properties, spray header, coolant temperature, nozzle levels or blocked nozzles, switching events, and optional crowns, incoming ridges, coil, previous strip widths, grinding, cooling-zone pitch, deflector radius, lateral compressive stress, and `shape_inputs` (strip stiffness, exit-tension force sensitivity and bite half-length supplied from a plant foil model, section 3.4) |
| `tribology` | rolling-oil viscosity law, roughness, temperatures, strip heat fraction: film thickness, placeholder friction, pass heating; also supplies the roll heat fraction to `width_model` |
| `hardening` | power or Voce law; with `use_computed_flow_stress` the computed flow stress replaces the supplied one on every pass (schedule rows are matched to passes by their position in the schedule, not by label) |
| `gauge_control` | gaugemeter AGC compensation gain, cylinder bandwidth, optional force filter |
| `drive` | drive-train inertias and shaft stiffnesses (torsional modes) |
| `incoming_variation` | relative hardness variation of the incoming coil, once per decoiler revolution or not |

`width_model.roll_heat_fraction_per_roll` may stay `null` only when `tribology` is given
(it is then `(1 - strip_heat_fraction)/2`); leave it `null` when `tribology` is given: if both are
supplied and disagree the result flags `HEAT_PARTITION_INPUTS_INCONSISTENT` (the roll thermal
model uses the width-model value, pass heating the tribology value; neither is changed).
`bite_heat_per_width_w_m` may stay `null`: it is
computed from the pass (section 8.2), except when no roll bite solves the case pass: then it
must be supplied for the roll thermal model to run (section 3.4).

### 5.1 Which observations matter most for lengthwise bands

In order of how much they separate the lengthwise hypotheses (section 6.2):

1. **Band positions on the barrel coordinate, on three consecutive coils**
   (`band_positions_across_width_m`, `positions_repeat_across_coils`). Measure from the
   header start (0 = start of the coolant header), after removing the strip tracking
   offset. A position on a weak nozzle or on a modelled stripe is strong support for the
   nozzle hypothesis; positions that stay put from coil to coil point to the mill (nozzle,
   roll), positions that follow the mother coil point to incoming ridges.
2. **Do the positions move after a work-roll change?**
   (`positions_change_after_work_roll_change`). Moving or vanishing points to the roll
   surface (wear band, pick-up, grinding); staying put points to the coolant header.
3. **Do the bands follow cooling-zone switching?** (`changes_with_coolant_zone_switching`).
   Log the flatness-control valve states against the shapemeter zones and the times the
   bands appear and fade. This is the strongest single test for short-lived bands.
4. **Visible under tension, or only after release?**
   (`visible_only_after_tension_release`, `appearance`). A band seen on the coil, at the
   slitter or on the inspection table but not in the mill is a latent band: flat under
   strip tension, buckled once tension is removed. The model computes both states
   (section 7.2) and the evidence rules compare them with this observation.
5. **Spacing against the nozzle and zone pitch** (`band_spacing_m`, or the gaps between
   observed positions). Gaps that are integer multiples of the nozzle pitch or the
   cooling-zone pitch support the coolant hypotheses; a regular fine spacing near the
   grinder traverse per revolution supports grinding feed marks; a spacing of 0.5-2 x the
   computed trough wavelength supports tension troughs.
6. **How long a short-lived band lasts** (`intermittent_duration_s`), seconds of rolling.
   It is compared with the model's visible time of a band after a zone switch (section 7.4).
7. **Thin-gauge dependence** (`worse_at_thinner_gauge`), the **coolant header** geometry and
   flow levels in `width_model`, and for coil-related causes `worse_toward_outer_wraps`.

At foil gauge add the observations of section 3.8 (tension at which the bands fade,
ironing-roll pressure, exit air blow-off, roll wiper cleaning, speed changes, wide after
narrow, online against offline flatness).

Lengthwise observation fields in plain words:

| field | meaning |
|---|---|
| `orientation` | `longitudinal` for bands along the rolling direction (the other values are for transverse marks) |
| `band_positions_across_width_m` | centre of each band on the header's barrel coordinate [m] |
| `lengthwise_continuity` | `continuous` (along the whole coil), `intermittent` (only for a while), `both` |
| `intermittent_duration_s` | typical time a short-lived band lasts [s] |
| `band_width_m`, `band_spacing_m` | width of one band across the strip; distance between neighbouring bands when roughly regular [m] |
| `positions_repeat_across_coils` | the bands sit at the same width positions on successive coils |
| `positions_change_after_work_roll_change` | the bands move or vanish after a work-roll change |
| `changes_with_coolant_zone_switching` | the bands come and go when coolant zones switch |
| `appearance` | `gloss_or_shade` (bright or dull stripe), `loose_or_buckle` (wavy loose band), `tight`, `stain` (often after annealing), `crease_or_flute` (sharp fold) |
| `visible_only_after_tension_release` | invisible in the mill, visible on the coil or after slitting |
| `worse_toward_outer_wraps` | stronger toward the outside of the wound coil |
| `changes_with_tension` | changing the strip tension changes the bands |
| `follows_previous_strip_edges` | band edges line up with the edges of narrower strip rolled earlier on the same rolls |
| `worse_at_higher_speed` | the bands get worse as the mill speeds up |
| `worse_at_thinner_gauge` | the bands are more frequent or stronger at thinner exit gauge |
| `faces` | `both` or `one` strip face |
| `worse_at_lower_tension` (foil, optional) | the bands are more visible at lower strip tension and fade above some tension |
| `changes_with_ironing_roll_pressure` (foil, optional) | the bands change when the ironing-roll pressure (per side) is changed |
| `changes_with_exit_air_blowoff` (foil, optional) | the bands change when the exit air blow-off is reduced or redirected |
| `changes_after_roll_wiper_cleaning` (foil, optional) | true: the bands change or go after the roll wipers are cleaned; false: they stay |
| `tracks_speed_changes` (foil, optional) | true: the bands appear, move or fade when the mill speed changes; false: they ignore it |
| `appeared_after_narrower_coil` (foil, optional) | the bands started when a wider coil was rolled after a narrower one (without a backup-roll change) |

### 5.2 Which observations matter most for transverse marks

1. **Pitch at two clearly different steady speeds** (`pitch_observations`, at least two
   speeds 20 % or more apart). If the pitch grows in proportion to speed (exponent of
   ln pitch against ln speed >= 0.7) the source is a fixed-frequency vibration (chatter or a
   structural resonance); if the pitch stays the same (|exponent| <= 0.3) the source is
   locked to a roll, bearing, gear or coil. Speeds closer than 5 % apart are not classified.
   The pitch also gives the frequency `f = u/p`, compared with the stand modes and with the
   order-locked source catalogue.
2. **Gauge variation** at the mark frequency on the exit thickness gauge / X-ray: present for
   third-octave chatter, largely absent for fifth-octave and surface marks.
3. **Roll-change test**: does the mark disappear after a work-roll change, after a
   backup-roll change, or neither?
4. **Faces** (both or one) and **orientation** (transverse, diagonal, chevron, irregular).
5. Onset speed, where the marks first appear (`first_seen`: bite exit, incoming coil, after
   bending or levelling), a chock-accelerometer frequency if one exists.
6. Geometry for the catalogue: work-roll and backup-roll bearings, gear meshes,
   grinder-mark counts, deflector roll and coil diameters. Without bearings and gears only
   the spindle / coupling candidate (twice work-roll rotation, from the work-roll diameter)
   is checked: a match still supports the drive/bearing hypothesis, a mismatch is
   `NOT_OBSERVED` rather than a contradiction.

### 5.3 Using your own mill

The question this section answers: *"I have a machine of a different spec making these
products; how do I change the values?"* A case file holds three kinds of input: the
**machine** (stand and line), the **product and pass**, and the **observations**. For one
diagnosis you edit all three in one case file. For the product survey (section 3.10) you
give the tool a case file of your machine and it takes only the machine keys from it.

**(a) The machine specification.** These keys describe the stand and the line; the product
survey takes exactly these from your file (`physicroll/band_survey.py`, `MACHINE_KEYS`, and
the result lists them under `mills.<kind>.keys_taken`). All values are SI units.

| key | what it is, in plain words | unit | where a mill engineer finds it |
|---|---|---|---|
| `pass.work_roll_radius_m` | work-roll radius (half the ground diameter; use the current roll, not the new-roll size) | m | roll shop records, roll grinder log |
| `pass.width_m` | strip width rolled on this mill (one value for the survey) | m | production schedule, order book |
| `pass.friction_coefficient` | Coulomb friction in the roll bite; no catalogue value exists, the demos use 0.03 | – | back-calculated from measured roll force and forward slip, or the mill's setup model |
| `stand.work_roll_mass_kg`, `stand.backup_roll_mass_kg` | moving mass of one work-roll and one backup-roll assembly (roll, necks, chocks, bearings) | kg | roll and chock drawings |
| `stand.work_backup_contact_stiffness_n_m` | stiffness of the work-roll / backup-roll contact | N/m | stand designer's data, or a roll-contact calculation |
| `stand.housing_stiffness_n_m` | stiffness of housing, screws or cylinders: the mill modulus | N/m | mill-modulus (stretch) test at commissioning, the AGC setup |
| `stand.modal_damping_ratio` | damping of the stand vibration modes | – | modal or tap test; 0.03 is the demo value |
| `stand.roll_youngs_modulus_pa`, `stand.roll_poisson_ratio` | roll material elasticity | Pa, – | roll supplier certificate (forged steel about 210 GPa, 0.3) |
| `spans.entry_span_length_m`, `spans.exit_span_length_m` | free strip length from the bite to the first roll on each side | m | line layout drawing |
| `spans.strip_youngs_modulus_pa` | strip modulus used for the span waves (70 GPa for aluminium) | Pa | material data |
| `kinematics.backup_roll_diameter_m`, `gear_meshes`, `bearings`, `grinder_marks`, `deflector_roll_diameters_m`, `entry_coil_diameter_m`, `exit_coil_diameter_m` | roll and drive geometry that sets the pitches of roll-, gear- and bearing-borne marks | m, teeth, – | drive and bearing drawings, gearbox data sheet, roll shop |
| `lubrication` | rolling-oil viscosity and pressure coefficient, roll and strip roughness (simple film screen) | Pa s, 1/Pa, m | oil supplier sheet, roughness measurements |
| `coolant` (except `blocked_nozzle_indices`) | spray header for the coverage screen: barrel length, nozzle pitch, stand-off, spray and offset angles, roll expansion, assumed excess roll temperature | m, rad, 1/K, K | spray header drawing, nozzle supplier data |
| `tribology` | oil viscosity law, roughness, inlet and strip temperatures, strip heat fraction, friction closure (pass heating and the friction-speed slope) | SI | oil supplier, process data; the strip heat fraction is an assumption unless measured |
| `gauge_control` | gaugemeter AGC compensation gain, cylinder bandwidth, force filter | –, Hz | AGC commissioning sheet |
| `drive` | drive-train inertias and shaft stiffnesses (torsional modes) | kg m², N m/rad | drive-train data, torsional analysis |
| `model_options` (except `bite_response_override`) | bite model choice, bite-damping fraction, flattening limit, cells | – | analyst choices; keep the defaults unless you know why |
| `width_model.roll` | work-roll barrel length and thermal properties (conductivity, density, specific heat, expansion) | m, W/(m K), kg/m³, J/(kg K), 1/K | roll drawing and roll supplier |
| `width_model.spray_header`, `coolant_temperature_k`, `roll_heat_fraction_per_roll`, `numerics`, `rolls_carrying_stripe`, `shape_disturbing_coefficient`, `heredity_coefficient`, `cooling_zone_pitch_m`, `strip_centre_m` | spray header and cooling zones of the roll thermal model, coolant temperature, heat share into each roll, numerics | m, W/(m² K), K, – | spray header drawing, coolant system data; flatness-controller zone map |
| `width_model.coil`, `width_model.deflector_roll_radius_m`, `width_model.grinding` | coil inner and outer radius, winding tension and compaction; deflector (or ironing) roll radius; grinder traverse | m, Pa, m/s, Hz | winder data, line drawing, roll-grinder settings |

**(b) The product and the pass.** `pass` gauges (`entry_thickness_m`, `exit_thickness_m`),
`mean_flow_stress_pa`, `entry_tension_pa`, `exit_tension_pa`, `exit_speed_m_s`; `material`
(alloy, temper, yield stress, modulus, Lüders strain, magnesium, grain size,
`final_pass_doubled`, `product`); `hardening`; `schedule` (the other passes of the route);
`incoming_variation`; and the case-specific width inputs `bite_heat_per_width_w_m`, crowns,
incoming ridges, previous strip widths, lateral compressive stress and `shape_inputs`. Take
them from the pass schedule, the material certificate and the process data of the coil you
are diagnosing.

**(c) The observations.** `observation` (sections 5.1, 5.2 and 3.8), plus the fault state of
the cooling system you know of: `width_model.blocked_nozzle_indices`, `nozzle_levels`,
`events` and `coolant.blocked_nozzle_indices`. Leave an observation `null` when nobody has
looked.

**(d) One diagnosis on your mill.** Copy the template, replace the machine keys of (a) with
your mill's, the pass and material of (b) with the coil's, record the observations of (c),
and run it:

```
cp scenarios/band_diagnosis_template.json my_mill.json
python -m physicroll.band_cli my_mill.json --out my_output
```

**(e) The product survey on your mill.** The survey keeps its rules for the product side
(section 3.10) and takes the machine keys from your file; the pass, material, schedule,
observations and case-specific inputs of that file are ignored. The file is validated by the
engine's own case validation; it must be a `physicroll.band_case.v2` case with a
`width_model` and with `model_options.bite_response_override` null. A product whose survey
pass your mill cannot take (for example the bite model's guards `h0/R <= 0.05` and
`width/h0 >= 20`) appears as a row with the reason, not as an error.

```
python -m physicroll.band_survey --out my_survey --mill my_mill.json
python -m physicroll.band_survey --out my_survey --foil-mill scenarios/band_diagnosis_battery_foil.json --sheet-mill my_mill.json
python -m physicroll.band_survey --out my_survey --mill my_mill.json --products battery_collector_foil,household_foil,litho_sheet
python -m physicroll.band_survey --out my_survey --mill my_mill.json --products battery_collector_foil,household_foil --overrides scenarios/band_survey_overrides_example.json
python -m physicroll.band_survey --out my_survey --mill my_mill.json --products battery_collector_foil,litho_sheet --write-cases my_cases
python -m physicroll.band_cli my_cases/litho_sheet.case.json --out my_output
python -m physicroll.band_cli --product-survey --out my_survey --mill my_mill.json --products litho_sheet
```

- `--mill` uses one file for both gauge classes; `--foil-mill` (exit gauge below 0.2 mm) and
  `--sheet-mill` (0.2 mm and above) supply them separately and take precedence over `--mill`.
  The friction of your file's pass is used for every product, and its pass speed where the
  catalogue publishes none. The result records the file and the keys taken
  (`options.mill_files`, `mills.<kind>.source`, `keys_taken`, `keys_not_taken`).
- `--products` takes catalogue ids (`docs/thin-gauge-products.md`); an unknown id is an
  error that lists the valid ones. Rows keep their catalogue number.
- `--overrides FILE.json` replaces survey-pass values per product with your own:
  `{"product_id": {"key": value}}` with the keys `entry_thickness_m`, `exit_thickness_m`,
  `mean_flow_stress_pa`, `exit_speed_m_s`, `entry_tension_pa`, `exit_tension_pa`,
  `friction_coefficient`, `width_m` and `doubled`; other keys are rejected. Each overridden
  value is listed in the row's `user_supplied_values` ("user-supplied (overrides file ...)")
  and the catalogue or assumed entry it replaces is dropped from the row's provenance.
  `scenarios/band_survey_overrides_example.json` is a synthetic example (the battery-foil
  demo's 30 -> 18 um final pass).
- `--write-cases DIR` writes one ready-to-edit case per surveyed product
  (`DIR/<product_id>.case.json`): the survey pass on the chosen mill, `material.product` set,
  every observation null, the case-specific inputs reset, and `notes` that say which values
  came from the catalogue (with source ids and read status), which were assumed, which came
  from your mill file and which you supplied. It is a starting point: replace the pass and
  material with plant values and record the observations before reading a diagnosis from it.

Without any of these options the survey is the one of section 3.10, unchanged. Its two default mills ship
with the code (`physicroll/band_survey_mills.py`, the machine sections of
`scenarios/band_diagnosis_battery_foil.json` and `scenarios/band_diagnosis_lengthwise_bands.json`;
a test checks that they agree), so the default survey also runs from an installed wheel without
the repository's `scenarios` directory; the scenario files stay the demo sources.

**(f) What stays synthetic or literature-based, and what matters most.** Unless you replace
them: the product side of the survey is the literature catalogue plus the stated assumptions
(the 0.20 / 0.23 tension fractions, 180 MPa where no as-rolled strength is published, 30 %
where no reduction is published, friction 0.03 on the demo mills); the demo mills and the
template are synthetic; the strip heat fraction (`tribology.strip_heat_fraction`) and the
bite-damping fraction (`model_options.bite_damping_transit_fraction`) are assumptions in
every case. What the code shows the results depend on most:

- the roll-bite force rises steeply with friction (section 3.3 probe: 0.959 to 2.49 kN/mm
  from friction 0.03 to 0.05 at the demo case pass), and the bite is rejected above a
  friction limit; supply your friction if you have it;
- the chatter critical speed: each diagnosis's lever table (`levers.rows`, section 11.5)
  gives its change with friction, reduction, entry and exit tension, entry span length and
  structural damping on your mill, and the speed margin is given with and without bite
  damping because the closure is unvalidated;
- the strip-to-mill modulus ratio, and hence how far the roll gap moves the gauge, follows
  `housing_stiffness_n_m` and `work_backup_contact_stiffness_n_m`;
- the thermal stripe heights scale with the heat share into the rolls
  (`roll_heat_fraction_per_roll` or `1 - strip_heat_fraction`) and the spray coefficients
  (section 3.9);
- the bite-free thresholds follow closed-form expressions of the inputs: the trough onset
  stress scales as `(h/a)*sqrt(E*sigma)` (gauge, span length, span tension), the
  roller-wrinkle threshold with the deflector radius, the critical coil ridge height with the
  gauge, the coil radii, the yield stress minus the winding tension and the compaction factor
  (section 7.2), and the dead band with gauge over width.

## 6. Hypotheses and evidence rules

### 6.1 Scoring

Twenty hypotheses are evaluated for every case, v1 or v2: ten transverse and ten
lengthwise (phase 1 had twelve; its two lengthwise hypotheses, coolant/thermal band and
roll-surface band, were replaced by nine in phase 2; phase 3 added `foil_tension_lines`). Each hypothesis carries `mechanism`,
`model_prediction`, `evidence` items `{criterion, observed, expected, verdict, weight,
basis}`, tallies, `score`, `standing`, `confirming_test` and `levers`. `basis` is
`observation` (a plant observation), `model` (a model result), `input` (mill data) or
`model not assessable` (a model part that could not be computed, always `NEUTRAL`) or
`model not credible` (a model item resting on a case-pass bite whose extended-domain force
lies outside the range reported for battery-foil passes, section 3.3; always `NEUTRAL`). The
credibility gate leaves alone the three model items that do not use the bite: the
tension-trough status, the crown change against the Shohet-Townsend dead band and the
yield-point bending window. Observation and input items are never gated, and the leading
rule (a supporting plant observation) is unchanged.

Verdicts: `SUPPORTS`, `CONTRADICTS`, `NEUTRAL`, `NOT_OBSERVED`; weights strong / moderate /
weak. **Score = sum of supports (3/2/1) - sum of contradictions (6/2/1).** Standing:
`CONTRADICTED` if any strong contradiction; `NOT_ASSESSABLE` if nothing but
`NOT_OBSERVED`/`NEUTRAL`; `CONSISTENT_LEADING` for the non-contradicted hypotheses with the
highest score, provided that score is at least 3 **and the hypothesis has at least one
supporting plant observation** (a model result alone never makes a hypothesis lead);
`CONSISTENT` if score > 0; else `WEAKENED`. The orientation counts as a plant observation
here, so for a lengthwise case the leading rule alone is met by "longitudinal". Rank: non-contradicted first, then score
descending, then id. **The score is an ordinal tally, not a probability**: a score of 20
against 17 says one hypothesis collected more weighted agreement with the observations as
entered, not that it is more likely by any stated amount. The weights are engineering
judgement (section 14).

**Gate on case-wide supports (phase 3 rule change).** Some supports come from a quantity
that describes the whole pass, not a band: the exit gauge (basis `input`: tension lines at
or below 30 um, creasing below 50 um) and the operating-point tribology regime, exit
temperature and film ratio (basis `model`, heat-streak / friction-band hypothesis). Such a
`SUPPORTS` counts only when the same hypothesis also has a `SUPPORTS` from a plant
observation **other than the orientation**; otherwise it is reported as `NEUTRAL` with the
note "counted only with a band-specific supporting observation". Contradictions from these
quantities are kept. Reason (from the engine work): at foil gauge these quantities hold for
practically every pass, and without the gate the orientation plus the exit gauge alone made a
hypothesis lead (`_gate_gauge_support` in `physicroll/band_width.py`; pinned by
`test_orientation_and_gauge_alone_do_not_lead`).

`family_summary` states which family the recorded orientation points to and which family
the leading hypothesis belongs to. `recommended_next_measurements` collects the confirming
tests of the top three ranked hypotheses plus one line per key missing observation (for a
lengthwise case below 100 um exit gauge also the foil lines of section 3.8).

### 6.2 Lengthwise hypotheses

Common rule: orientation `longitudinal` supports moderately; any other recorded orientation
contradicts every lengthwise hypothesis strongly. Position match tolerance: one quarter of
the nozzle pitch (analyst choice). "S" = supports, "C" = contradicts, with the weight.

| hypothesis | mechanism | supports | contradicts | confirming test |
|---|---|---|---|---|
| `nozzle_thermal_stripe` | A blocked, partly blocked or mis-aimed nozzle leaves an under-cooled stripe; the work roll grows there and over-rolls the strip into a loose band (latent under tension, manifest once it buckles). | position on a modelled stripe or a weak nozzle, or (without a width model) inside a coverage band-risk interval widened by the tolerance (S str); continuity continuous or both (S mod); positions repeat across coils (S mod); positions stay after a work-roll change (S mod); gaps all multiples of the nozzle pitch (S mod); appearance loose_or_buckle (S mod); model band at an observed position (S mod, model); tension-release observation agrees with the model states (S mod); loose_or_buckle with a band manifest in the mill (S mod); worse at thinner gauge (S weak); both faces (S weak); tracks speed changes NEUTRAL (a thermal stripe follows heat input slowly) | no observed position on a predicted one (C weak); only intermittent (C weak); positions do not repeat (C mod); positions move after a work-roll change (C mod); stain or crease (C weak); tension-release observation disagrees with the model (C weak); changes after roll wiper cleaning (C weak) | spray footprint check and header inspection; band positions on three consecutive coils against nozzle positions; shapemeter zone map |
| `cooling_zone_switching_transient` | Zone cooling valves or an intermittently blocking nozzle switch a zone off and on; each switch grows a stripe for tens of seconds and it fades over about a minute: short-lived bands. | continuity intermittent or both (S str); changes with zone switching (S str); observed duration within 0.3-3 x the model visible time (S mod, model; without events, 0.3-3 x the 20-120 s literature range, S weak); position on an event nozzle or event stripe (S str); gaps multiples of the zone pitch (S weak); positions do not repeat (S weak); loose_or_buckle or tight (S weak); worse at thinner gauge (S weak); tension-release rules as above | only continuous (C mod); does not change with zone switching (C str); tension-release disagreement (C weak) | log valve states against shapemeter zones and band times; compare band duration with valve-off intervals |
| `roll_surface_band` | A wear band, pick-up streak or two-tone step at the edges of earlier narrower strip prints at a fixed width position until the rolls are changed; in foil also wiper debris, a wide coil after a narrow one and backup-roll lines printed through the work roll [V S25, S17]. | positions change (or band disappears) after a work-roll change (S str); follows previous strip edges or on a two-tone position (S str); repeat across coils (S mod); continuous (S mod); gloss_or_shade (S mod); one face (S mod); changes after roll wiper cleaning (S str); appeared after a narrower coil (S str); disappears after a backup-roll change (S mod) | positions stay after a work-roll change (C str; "does not disappear" C mod; both only C weak when the band disappeared after a backup-roll change, see below); intermittent (C mod); loose_or_buckle (C weak); changes with zone switching (C mod); does not change after wiper cleaning (C weak) | roll-surface inspection at the band positions; work-roll change test; compare with earlier narrower widths |
| `grinding_feed_marks` | Helical feed lines from the roll grinder; the lateral pitch is the traverse per roll revolution. | every gap within 10 % of 1-3 x the feed pitch (S str); regular spacing (CV < 0.15) below 30 mm (S weak); positions change after a work-roll change (S mod); gloss_or_shade (S mod); continuous (S weak) | gaps not matching (C mod); positions stay after a work-roll change (C str) | measure the spacing against the grinder traverse per revolution; roll inspection; roll change |
| `incoming_ridge_coil_buildup` | A local high spot in the incoming profile stacks up wrap by wrap in the coil, stretches the band beyond yield and leaves a tight-then-loose band, worse toward the outer wraps. | positions do not repeat across coils (S mod); worse toward outer wraps (S str); position on a supplied ridge (S str); model ridge yields the strip (S mod, model); intermittent with 5-95 % of the coil length affected (S weak); worse at thinner gauge (S mod); visible only after release (S weak) | positions repeat (C mod); positions change after a work-roll change (C weak); not worse toward outer wraps (C mod); model ridge does not yield (C weak, model) | entry profile scan of the incoming coil and outside-profile scan of the wound coil |
| `tension_troughs_or_creases` | Lateral buckling of thin strip under tension in a free span (troughs), which a roll can iron into a crease. | spacing 0.5-2 x the computed trough wavelength of either span (S str when the spacing is established: a stated `band_spacing_m` or at least two regular gaps, CV <= 0.1; S weak for one gap or irregular gaps, with the text "cannot establish a spacing"); crease_or_flute (S str); changes with tension (S str); model troughs expected (S mod, model; needs `lateral_compressive_stress_pa`); intermittent or both (S weak); worse at thinner gauge (S mod); changes with ironing-roll pressure (S mod); exit gauge below 50 um, creasing possible [V S25] (S weak, input, gated) | spacing outside 0.25-4 x both wavelengths (C mod, only for an established spacing); stain (C mod); does not change with tension (C str); model below the trough threshold (C weak); positions change after a work-roll change (C weak); worse at lower tension (C weak: troughs need tension; a crease from a loose band is the exception, so it stays weak) | vary the span tension and watch the bands; check deflector / idler alignment and crown; measure the trough spacing |
| `profile_flatness_mismatch` | Relative crown change between entry and exit outside the Shohet-Townsend dead band: smooth edge waves or a centre buckle rather than narrow stripes. | crown change outside the dead band (S str, model); all positions within 15 % of the width of an edge or of the centre (S mod); band width > 150 mm (S weak); loose_or_buckle (S mod); visible only after release (S weak); worse at thinner gauge (S mod) | crown change inside the dead band (C mod, model); two or more interior positions (C mod); band width < 60 mm (C weak) | entry and exit profile measurements; shapemeter map; compare relative crowns |
| `heat_streak_or_film_variation` (title "Heat streak / friction or oil-film band (no roll bump)") | Local oil-film or friction variation across the width: milky heat streaks that wander in width and position (QCA-1), or, in foil where the oil film is comparable to the roughness, a cross-width difference in roughness or oil film that gives a flatness band without a geometric roll bump and tracks speed changes [V S11, S17; mechanism D]. | gloss_or_shade (S mod); no gauge variation (S weak); positions do not repeat (S mod); intermittent or both (S mod); worse at higher speed (S mod); tracks speed changes (S str); boundary film regime or exit temperature above a supplied limit (S weak, model, gated); film ratio 0.3-3 at the operating point, from `tribology` or else the phase-1 lubrication screen (S weak, model, gated); exit air blow-off NEUTRAL | crease_or_flute (C mod); positions repeat (C weak); positions change after a work-roll change (C weak); does not track speed changes (C weak) | compare band appearance with oil temperature and speed (does the band appear, move or fade with a speed change?); check whether the bands wander between coils; measure the work-roll roughness across the barrel |
| `oil_carryover_drips_or_stain` | Coolant carried past the wipers, drips, or staining seen after annealing. | stain (S str); one face (S mod); intermittent (S weak); positions repeat (S weak) | loose_or_buckle or crease_or_flute (C mod); changes with tension (C weak) | anneal a sample and look for stain; inspect wipers and drip shields |
| `foil_tension_lines` | **Published description, not a model** (the mechanism text says so): longitudinal stripes at 5-20 mm pitch that appear below 15 um and worsen as gauge falls; drivers tension, roll roughness, roll parallelism, roll pressure and pass reduction [BF-S21, excerpt of a trade report of a producer talk; catalogue `TENSION_LINES`]; wider and more visible at low strip tension and vanishing above a threshold tension [V S27, S28]. The tool has no physical model of them (`model_prediction.model` says so); rule weights [D]. | spacing (`band_spacing_m`, else the mean observed gap) regular 5-20 mm (S str; a stated spacing counts as regular), 3-30 mm or irregular (S weak); exit gauge below 15 um (S mod, input, gated), 15-30 um (S weak, input, gated); worse at lower tension (S str); changes with tension (S mod, used only when `worse_at_lower_tension` is null); changes with ironing-roll pressure (S mod); changes with exit air blow-off (S mod); positions do not repeat across coils (S weak); gloss_or_shade or crease_or_flute (S weak); worse at thinner gauge (S weak) | spacing above 60 mm (C weak); exit gauge above 100 um (C mod, input); not worse at lower tension (C str); loose_or_buckle or stain (C weak) | raise the exit tension in steps and note the tension at which the lines vanish; vary the ironing-roll pressure per side and the exit air blow-off one at a time; check roll parallelism |

The tension-release rule used by the two coolant hypotheses compares the observation with
the model states of the bands at the observed positions (steady stripes for the nozzle
hypothesis, event peaks for the zone hypothesis): observation "only after release" true
supports moderately when a model band is latent in the mill and manifest after release, and
contradicts weakly when a model band is manifest in the mill; observation false supports
moderately when a model band is manifest in the mill and contradicts weakly when all model
bands are latent in the mill. When the shape chain is not assessable (no bite, section 3.4)
both this rule and "model band at an observed position" are `NEUTRAL` with basis
`model not assessable`.

**Roll-surface band and backup-roll print-through (phase 3).** Backup-roll lines are printed
through the work roll onto the strip, so they persist across a work-roll change. When
`disappears_after_backup_roll_change` is true, "positions do not change after a work-roll
change" (or "does not disappear after a work-roll change") counts only as a weak
contradiction, with the reason written into the item, instead of strong (or moderate); the
backup-roll observation itself supports moderately. Without it, the strong contradiction
stands, as in the foil demo.

Gated items ("gated" in the table) follow the gate of section 6.1. The levers listed with
`foil_tension_lines` are: raise front (exit) tension (risks ridging), adjust ironing-roll
pressure per side, reduce or redirect the exit air blow-off, check roll parallelism, raise
work-roll roughness.

**Stage-B check against the EAFA defect catalogue** [PK-S7, catalogue `FOIL_DEFECTS`]. The
rules of `roll_surface_band`, `nozzle_thermal_stripe`, `heat_streak_or_film_variation` and
`profile_flatness_mismatch` were compared with the EAFA descriptions using only the existing
observation keys; none was changed. Rolling stripes (gloss side only, constant along the
coil, local work-roll wear) are already covered by `roll_surface_band` (gloss_or_shade
appearance, one face, continuous). Heat stripes (grey, straight to snaking, from temperature
or flatness differences or an overheated roll) are covered by the nozzle and heat-streak rules
(gloss_or_shade appearance; positions that do not repeat for the heat streak). Gloss
difference and broken matt are matt-side defects of doubled rolling with no observation key
that separates them. Chatter marks belong to the transverse family. Grooves (sharp flatness
deviations from an unfavourable profile) would need an observation of band sharpness, which
the schema does not have; `profile_flatness_mismatch` stays a rule for smooth edge or centre
waves.

### 6.3 Transverse hypotheses

Notation: `f_obs = u/p` per pitch observation (plus `measured_vibration_hz` when given);
`law` = pitch-speed classification (needs two distinct speeds); `red` = pass reduction;
`u_op` = operating exit speed.

| # | id | rules (verdict, weight) |
|---|---|---|
| 1 | `third_octave_self_excited_chatter` | transverse S mod; longitudinal C str; diagonal/chevron C mod. law FIXED_FREQUENCY S str; SPEED_INDEPENDENT C str. `f_obs` within +-15 % of model dominant/onset frequency S str, else 90-300 Hz S mod, outside 60-400 Hz C str. gauge variation detected S str, not detected C mod. faces both S weak, one C mod. `u_op >= u_crit(beta)` S str; `u_crit(0) <= u_op < u_crit(beta)` S weak; `u_op < u_crit(0)` C mod. onset speed within 0.6-1.6 x `u_crit(beta)` S mod, otherwise S weak. disappears after any roll change C mod. worse at thinner gauge S weak. **Phase 2:** when the model onset or dominant frequency lies above the span-wave limit `c/(2L)` the speed-margin item is NEUTRAL and the model-frequency match is skipped (flag `CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT`). **Scan range:** the critical speeds come from a search over 0.05-60 m/s, so "no crossing" (`STABLE_OVER_SCANNED_RANGE`) says nothing about an operating speed outside it; there the speed-margin item is decided by the operating-point stability with and without bite damping (unstable with beta S str; unstable only with beta = 0 S weak; stable in both C mod, the text saying it rests on the operating point; stability unavailable NEUTRAL), the result carries `chatter.operating_speed_outside_scanned_range`, the flag `OPERATING_SPEED_OUTSIDE_SCANNED_RANGE` and a note on such schedule rows, and the report's chatter section warns that the scan status does not mean stable at the operating speed. |
| 2 | `fifth_octave_roll_stack_resonance` | orientation as 1. `f_obs` within +-15 % of the antisymmetric upper mode S str, else 500-1200 Hz S mod, below 300 Hz C str. pitch 10-40 mm S mod. gauge variation not detected S mod, detected C weak. law FIXED_FREQUENCY S mod; SPEED_INDEPENDENT S mod if `pi*D_b*(1+f)/p` within 0.05 of an integer, else NEUTRAL. order-locked source within +-10 % of the antisymmetric upper mode at `u_op` S mod. disappears after backup-roll change S mod. faces both S weak. |
| 3 | `work_roll_borne_marks` | law SPEED_INDEPENDENT S str, FIXED_FREQUENCY C str. pitch = `pi*D_w*(1+f)/n` within 3 % for ONE n (1..8 or a supplied grinder-mark count) that fits every pitch best (smallest worst mismatch; a supplied count preferred on a tie), S str, no match C mod; the same n in the prediction and the strip map. work-roll change: disappears S str, persists C str. faces one S mod, both C weak. longitudinal C str. |
| 4 | `backup_roll_borne_marks` | as 3 with `D_b`; backup-roll change disappears S str, persists C str; disappears after work-roll change C str. |
| 5 | `order_locked_drive_or_bearing_excitation` | law SPEED_INDEPENDENT S str, FIXED_FREQUENCY C str. best gear / bearing / spindle source within 5 % S str (named). The spindle / coupling candidate `work_roll_2x` is scored whether or not gear or bearing geometry is supplied: with no gear and no bearing supplied, a spindle match S str (the text says only the spindle was checked) and no match NOT_OBSERVED; with geometry supplied but no match C weak. No pitch and no vibration frequency observed: NOT_OBSERVED. persists after both roll changes S weak. faces both S weak. longitudinal C str. |
| 6 | `torsional_or_low_frequency_drive_vibration` | `f_obs` 5-30 Hz S str, above 60 Hz C str. **Phase 2:** with a `drive` section, within +-15 % of ONE computed torsional mode (the best single fit to every observed frequency) S str, above max(60 Hz, 1.5 x highest mode) C str. pitch 0.1-3 m S weak. law FIXED_FREQUENCY S mod. longitudinal C str. **Phase 3:** when it leads and torsional modes are computed, the strip map draws the pitch `u_op / f` with `f` the computed mode that best matches the observed frequencies (else the lowest mode) [D]. |
| 7 | `coil_or_mandrel_locked_marks` | One coil for all pitches (review fix): the coil with the smallest worst-case mismatch over the observed pitches is chosen first (`matched_coil`, `matched_coil_worst_relative_mismatch`, also drawn in the strip map), then every pitch is judged against it: within 10 % of `pi*D_exit_coil` or `pi*D_entry_coil*h0/h1` S str; coil diameters not supplied NOT_OBSERVED; supplied but no match C weak (gap filled, 6.4). When different pitches would have matched different coils, the text says the same coil is applied to every pitch. The entry-coil pitch uses the case pass's h0/h1: the pitch observations are assumed to be taken on the case pass's exit strip. first seen incoming S weak. law FIXED_FREQUENCY C mod. |
| 8 | `yield_point_bending_marks` | not susceptible C str, susceptible S mod, unknown NOT_OBSERVED. diagonal/irregular S mod, chevron/longitudinal C mod. a regular law C mod. first seen incoming or after bending/levelling S str; at bite exit with `red > 0.02` C str. a deflector/coil in the yield-point window S mod, none C weak. worse at thinner gauge C mod (`t/D` falls with gauge). |
| 9 | `herringbone_lubricant_film_breakdown` | chevron S str, diagonal S weak, longitudinal C str. `red >= 0.40` S mod, `red < 0.25` C mod. pitch 0.5-2 x contact length S str, > 5 x C mod. gauge variation not detected S weak. film ratio < 1 S weak. |
| 10 | `skidding_loss_of_forward_slip` | forward slip <= 0 S str, < 0.005 S mod, >= 0.02 C mod. film ratio > 3 S weak. irregular S weak, longitudinal C str. a regular law C weak. |

Each transverse hypothesis has a confirming test from mill practice (stone the strip and
measure pitch at two speeds; chock accelerometer speed-ramp order map; roll-change test;
backup-roll barrel inspection; tensile test for a yield plateau; ...).

### 6.4 Interpretations where the written rules were open, and two changed rules

- **Several observations, one evidence item.** A frequency band, pitch band or pitch-match
  criterion is evaluated for each observation and reported as one item with the **least
  favourable** verdict: one source has to explain every observation, and repeated
  observations are not independent evidence. In the bearing demo the same 24.9 mm pitch at
  6.0 and 7.83 m/s gives 241 Hz and 314 Hz; the 241 Hz observation (below 300 Hz)
  contradicts the fifth-octave hypothesis strongly.
- **One source for all observations (review fix).** Where the candidates are separate
  physical sources, one source is chosen first, the one with the smallest worst mismatch over
  every observation, and every observation is judged against it: the coil (entry or exit),
  the roll mark count n (work and backup roll; a supplied grinder-mark count preferred on a
  tie, named in the evidence text, used in the prediction and the strip map), the backup-roll
  count in the fifth-octave pitch-law item, the torsional mode, and the gear / bearing /
  spindle order (already so). Before, two pitches matching n = 2 and n = 3 both supported the
  work-roll hypothesis strongly. Per-observation matching is kept where it is physically
  right: a frequency or pitch band every observation must fall in (chatter 90-300 Hz,
  fifth-octave 500-1200 Hz, pitch 10-40 mm or 0.1-3 m), one fixed model frequency (the
  fifth-octave mode; the chatter dominant and onset frequencies, which are one mode at two
  speeds), one contact length (herringbone), the grinding feed pitch (one pitch; each gap may
  be a different multiple of it), the signatures' per-observation catalogue listing (a
  listing, not evidence) and band positions, each matched to its own nozzle or stripe.
- **Band-risk stripes of the v1 coolant screen.** Only `BLOCKED_NOZZLE` stripes and interior
  `UNCOVERED` zones count; the regular overlap alternation of a healthy header does not.
  Without a `width_model`, the lengthwise nozzle hypothesis uses these stripes **as
  intervals**: an observed position matches when it lies inside a stripe widened by the
  position tolerance, by the same `band_signatures.match_band_positions` that gives
  `screens.band_position_match`, so the two cannot disagree (review fix; before, only the
  stripe centres were compared and a band inside a wide uncovered zone but away from its
  centre was contradicted). The evidence text and `model_prediction.model_intervals_m` then
  show the intervals. Point sources (modelled stripe peaks, blocked or low-level nozzle
  axes) are still matched by centre within the tolerance.
- **Two gaps filled by mirroring an existing rule** (CONTRADICTS weak): coil diameters
  supplied but the pitch matches neither coil; predicted lengthwise positions exist but no
  observed position is on one.
- **Bite derivation failure.** Chatter-dependent criteria become `NEUTRAL` with expected
  text `NOT_ASSESSABLE: <reason>`; forward slip is then taken as 0 in the kinematics (flag
  `FORWARD_SLIP_UNKNOWN_ZERO_USED_IN_KINEMATICS`). A bite whose forward slip is 0.5 or more
  (the experimental mattress model reports such values because it has no elastic strip
  zones; a supplied bite may too) keeps two values: zero is used only in the roll-borne pitch
  kinematics (source catalogue, roll-mark and order-locked pitches, the work- and backup-roll
  hypotheses; `band_signatures` accepts |slip| < 0.5), flag
  `FORWARD_SLIP_OUTSIDE_KINEMATICS_DOMAIN_ZERO_USED_IN_KINEMATICS` and a limitation sentence;
  the forward-slip screen is `NOT_ASSESSABLE` with the reason (never skidding), the skidding
  hypothesis's slip item is `NEUTRAL`, and every other result (bite, film inlet roll speed,
  gauge-control roll frequencies, schedule rows, survey, report) uses the actual slip.
  The friction-speed curve accepts a slip of at most 0.4 and otherwise reads `FAILED` with
  the reason.
- **Rule changed against the written specification:** `CONSISTENT_LEADING` requires at
  least one `SUPPORTS` item with basis `observation`. As written, the chatter speed-margin
  criterion (a model result worth 3 points) made third-octave chatter lead in the template
  case with every observation `null`. Scores are unchanged by the rule.
- **Second rule change (phase 3):** the gate on case-wide supports (section 6.1). It changes
  scores: a gated item contributes nothing. In the foil demo it holds the tension-line gauge
  support at `NEUTRAL`; in the sheet lengthwise demo the trough gauge item is `NEUTRAL`
  anyway (210 um is not below 50 um).
- **A hypothesis that cannot be evaluated does not stop the diagnosis.** A domain error
  (`ValueError`) raised while one hypothesis is evaluated makes that hypothesis
  `NOT_ASSESSABLE` with score 0 and one `NEUTRAL` item carrying the reason; the result lists
  it in `hypothesis_evaluation_failures` with the flag `HYPOTHESIS_EVALUATION_FAILED` and a
  limitation sentence, and every other hypothesis and section is returned. The next
  measurements and the strip map fail the same way (flags `NEXT_MEASUREMENTS_FAILED`,
  `STRIP_MAP_FAILED`). Other errors are not caught.
- **Missing model parts never contradict.** With no bite or no roll thermal solution the
  model-band items are `NEUTRAL` (`model not assessable`), the duration rule of the zone
  hypothesis likewise, and a coil-ridge result from the proportional estimate supports only
  weakly (pinned by `test_missing_model_parts_never_contradict`).

## 7. Lengthwise physics

The lengthwise result (`result['width']`) is built in this order: steady roll temperature
and radius with the actual and with a healthy spray header (7.1); the difference between
the two gives the stripes; each stripe goes through the strip-shape chain to thickness,
elongation, flatness and buckling (7.2); the same stripe shape is carried through every
pass of the schedule (7.3); switching events are simulated in time (7.4). Integration code:
`physicroll/band_width.py`; equations: `physicroll/roll_thermal.py`,
`physicroll/strip_shape.py`.

### 7.1 Roll thermal model (`roll_thermal.py`)

Circumferentially averaged, axisymmetric conduction in a solid work roll of radius `R` and
barrel length `B`; `z` along the barrel, `r` radial [V: Yamaguchi et al. 2016; Li et al.
2024]:

```
rho*c*dT/dt = k_r*(1/r)*d/dr(r*dT/dr) + k_z*d2T/dz2                      [V]
r = R:   -k_r*dT/dr = h(z,t)*(T - T_coolant) - q(z,t)                    [V]
r = 0:   symmetry;   z = 0, B: adiabatic (neck and chock losses ignored, flagged)   [V]
q = roll_heat_fraction_per_roll * bite_heat_per_width / (2*pi*R)         [D] (under the strip only)
h = background_htc + spray_mean_htc * weight(z,t)                        [D]
```

Spray header: nozzle `i` at `z_i` with flow level `s_i` in [0, 1] adds `s_i*pitch/W_eff`
to `weight` inside its footprint, `W_eff = 2*standoff*tan(angle/2)*cos(offset)` [V: Lloyd
2010; Tucker 2006]. The footprint is a top hat, so a healthy header averages to 1 away from
the barrel ends. Default layout: `n = floor(B/pitch)` nozzles centred on the barrel, index 0
nearest the header start. A blocked nozzle is level 0, a partly blocked one a level between
0 and 1 (`nozzle_levels`), and a switching event sets the listed nozzles to `level` for
`duration_s`.

Thermal radius growth per axial station:

```
dR(z,t) = factor*(2*alpha/R) * integral_0^R (T - T_ref) r dr                       [V/D]
factor = 1 ('axially_free', default) or (1 + nu) ('plane_strain')                 [V/D]
```

The sources disagree on the expansion factor: Yamaguchi et al. (2016) use 1 [V], Li et al.
(2024) write `2(1+nu)` for an infinitely long cylinder [V]; in this formula `(1+nu)` is the
plane-strain (`eps_z = 0`) result and 1 the axially free result [D]. The choice changes
every radius and every flatness number by the factor 1.3 (`nu = 0.3`). Each axial station
uses its own radial integral (axial mechanical coupling ignored, flagged). Thermal crown =
growth at strip centre minus the mean growth at the two strip edges.

**Why stripes are found by differencing.** A smooth crown with a sharp roll-off at the strip
edges (bite heat stops there) leaves residual waves of a few micrometres under a polynomial
de-trend even for a healthy header. The engine therefore solves the same pass twice, with
the actual header and with a healthy one (all levels 1), and thresholds the difference
directly at 0.1 um (`STRIPE_THRESHOLD_M`, analyst choice). The difference has a zero
background, so subtracting its mean would itself create a spurious cold stripe; it is not
de-trended.

**Nozzle-pattern ripple.** With idealised top-hat footprints, a healthy header gives a
heat-transfer coefficient that varies at the nozzle pitch whenever the overlap is not a
whole number of pitches. Real fans have a tapered flow distribution, so this ripple is an
artefact of the idealisation. It is reported separately (healthy growth minus its moving
average over one nozzle pitch) and fed through the shape chain so that its size can be
judged, but it is never counted as a band. In the lengthwise demo it is 0.242 um peak to
peak in radius, 6.48 I-units with the exit-tension feedback (58.8 compliance only, 70.6
rigid bound), 35 latent bands above the 2 I-unit reporting threshold, flat after tension
release (`width.shape.nozzle_pattern_ripple`).

Numerics: conservative finite volumes (uniform axial cells, geometric radial cells refined
toward the surface), Peaceman-Rachford ADI with a backward-Euler start-up after each
discontinuity, internal step capped at `dz^2/a_z`; steady state by the same ADI operator
used as an iterative solver. Energy is conserved exactly by the scheme; the demo steady
solution has a relative energy residual of 9.4e-10 and the event simulation 5.7e-13.

**Growth rate after a spray change, and the correction it forced.** Radius growth follows
the radial heat integral. Differentiating the growth formula and using the heat balance of
the cross-section, the stripe starts to grow at

```
dR/dt = 2*alpha*factor*dq/(rho*c),   dq = (h_before - h_after)*(T_surface - T_coolant)   [D]
```

whatever the radial temperature distribution. A radially resolved roll therefore does
**not** grow a stripe faster than a radially lumped one; it only changes the surface
temperature faster. An earlier statement in this project (a commit message) said a lumped
roll gets the response time wrong by an order of magnitude; that is true for surface
temperature but not for radius, and was corrected. The roll-thermal test checks it: the
initial growth in the resolved and the lumped model both follow this law (the resolved one
starts slightly slower because its skin heats within seconds), the resolved surface
temperature reacts more than five times faster, and after re-cooling the resolved stripe
decays faster (half-decay about 79 s against about 113 s lumped in the reference case),
still in minutes.

**Open discrepancy, revisited.** Dohmae & Okamura (2012) identified on a plant a first-order
flatness response to one cooling zone with a time constant of about 20 s. This model fades
stripes over about a minute (section 7.4: half-decay 57 s and 84 s after the two lengthwise
demo events) and builds a steady stripe over minutes (battery demo: 116 s to 50 %,
551 s to 90 %, `width.thermal_sensitivity.steady_build_up`); a short event rises faster (half its
peak in 9.25 s in the battery demo). The literature's computed time scales are about 23 s for the
axial decay of a 52 mm stripe and 4-7 min radially for a 260 mm roll [PT-T18, PT-T25,
computed]: the plant's 20 s is of the order of the axial (local) scale, the model's steady
build-up of the radial one. Plant time constants themselves were not found (abstract only,
[PT-T26]). Partly open. Possible causes, none modelled: bite heat that depends
on the roll surface temperature, emulsion-level heat transfer, per-revolution effects.

Not modelled: the per-revolution surface temperature cycle, the bite contact conductance
and roll-strip temperature coupling (`q` is supplied or computed from the pass, not coupled
back), the flow distribution inside a fan, spray drift, temperature-dependent properties,
neck and chock losses, axial mechanical coupling of the expansion, roll wear, bending and
flattening. No measured spray heat-transfer coefficient for kerosene-based coolant was found
(planner estimate 0.5-2 kW/m2K [D]; an Innoval blog gives 4.65-5.5 kW/m2K overall for an
unspecified coolant); the coefficients are inputs.

### 7.2 Strip shape and flatness (`strip_shape.py`)

Sign conventions: `z` across the width; a positive radius deviation `dR` is a locally larger
roll (hot stripe), which over-rolls the strip (`dh < 0`). Elongation `eps > 0` = the fibre is
longer = loose; residual stress `sigma_res = -E*(eps - mean(eps))` is then compressive.
Tension positive.

**Roll compliance to a narrow line load** [D]. Boussinesq point load integrated over the
bite half-length `a`, displacement on the bite centre line, valid for `2a << lam << R`:

```
C(lam) = (2*(1-nu^2)/(pi*E)) * (ln(lam/(pi*a)) + (1 - gamma_Euler))   [m2/N]    [D]
```

(plane-strain check `p* = pi*E_star*Delta/lam`, Johnson s13.2, read second-hand). Wavelengths
below `4a` are taken at `C(4a)`, above `R` (including the mean) at `C(R)`.

**Three transfer levels.** With strip stiffness per unit width `Q = -d(F/width)/dh_exit` and
`n` rolls carrying the bump (`rolls_carrying_stripe`, 1 or 2):

```
rigid bound:              I = 1e5*n*dR/h                                       [D]
compliance only:          T = 1/(1 + 2*C*Q),        dh = -n*T*dR               [D]
with exit-tension feedback:
  dp' = -Q*dh - N_x'*dsigma_x,  dsigma_x = -E_strip*eps,  eps = -xi*dh/h_exit  [D]
  Q_eff = Q + N_x'*E_strip*xi/h_exit,  T = 1/(1 + 2*C*Q_eff)                   [D]
```

`N_x' = -dF/dsigma_exit / width` [m] comes from the bite derivation. The transfer is applied
per Fourier component; the mean component keeps `Q`, because a uniform elongation does not
change the reel-controlled mean tension.

**Why the feedback is mandatory.** A locally over-rolled fibre is longer, so its exit
tension drops, which raises the local roll force and flattens the bump. Without it the chain
overstates every band. Worked example from `tests/test_strip_shape.py` (0.5 um, 50 mm wide
stripe on both rolls, 0.21 mm exit gauge, 30 MPa tension, `Q` = 1.1e10 Pa,
`N_x'` = 5.9e-3 m): rigid bound 476 I-units; compliance only 411 I-units,
`MANIFEST_BUCKLE`; with the feedback 28.6 I-units, latent under tension (values from running
the test's inputs through `thermal_stripe_flatness`; the test asserts 410.58 I-units without
the feedback, the latent state with it and a ratio below 0.1). In the lengthwise demo the
feedback stiffness per width is 76 to 140 times `Q` on every pass (gauge-trend table, 7.3).
The engine always applies it and reports all three levels.

When the feedback term dominates, `eps -> n*dR/(2*C*N_x'*E_strip)`, independent of gauge
[D]: the raw elongation from a given stripe no longer rises as `1/h`.

**Saturation when a band goes slack** [D, planner, approximate]. A loose band that the
linear feedback leaves manifest cannot lose more tension than `sigma_T + sigma_cr(b)`. Its
force increase is capped at `dP'_max = N_x'*(sigma_T + sigma_cr)` and its peak thickness
change becomes `|dh| = (n*dR_peak - 2*C(2b)*dP'_max)/(1 + 2*C(2b)*Q)`; the band's samples are
scaled by one factor and flatness recomputed (flag `TENSION_FEEDBACK_SATURATED_BAND_SLACK`).
The linear-feedback profile (`i_units_linear_feedback`) is reported alongside and is the one
to plot.

**Differential elongation, I-units, residual stress.**

```
eps(z) = xi*(dH(z)/H_mean - dh(z)/h_mean)          [M form; xi per US 5,927,117 V]
I(z) = 1e5*(eps(z) - mean(eps))                    [V: IHI; Vollmer 2019]
wave: I = (pi*H_w/(2*L_w))^2 * 1e5                 [V: QCA-1; Bailey]
sigma_res(z) = -E*(eps(z) - mean(eps))             [D]  (0.7 MPa per I-unit at E = 70 GPa)
```

Bands are contiguous runs above the reporting threshold of 2 I-units (analyst choice).

**Buckling in the mill: tension beside a compressed zone stabilises it** [D]. Only net
compression can buckle. With the signed compression `q = -(sigma_T + sigma_res)` and an
assumed mode `w = sin(pi*(x-x1)/b)*sin(pi*y/lam)` on an interval `[x1, x1+b]` across the
width, the Rayleigh quotient is minimised at `lam = b` and gives

```
q_w = (2/b)*integral q*sin^2(pi*(x-x1)/b) dx  >=  sigma_cr(b)                       [D]
sigma_cr(b) = k*pi^2*E/(12*(1-nu^2))*(t/b)^2,  k = 4                                [M, Timoshenko]
```

The band's utilisation `U` is the maximum of `q_w/sigma_cr(b)` over intervals overlapping
it; `U >= 1` is `MANIFEST_BUCKLE`, else `LATENT_UNDER_TENSION` (a latent band is a stress
stripe a shapemeter can see). Tension enters with its sign, so a compressed zone flanked by
tension is held flat. Latent / manifest description [V: Abdelkhalek et al. 2008; Lloyd
2010].

**After tension release.** On the coil surface, at the slitter or on an inspection table
`q = -sigma_res`. The per-band released state uses a **local** mode whose width is at most
2 x the band's half-peak width of residual compression (analyst choice); this mode carries
the `t^2` gauge trend. The unrestricted **whole-sheet** mode (`released_global_*`) is
reported for information only: it is the overall wave or centre fullness of the whole
sheet, scales with strip width, ignores the sheet's weight flattening it on a table and its
finite unsupported length, and is an upper-bound indicator, not a prediction of a visible
band. Known limit: on a sharp-edged (top-hat) stripe at thin gauge the half-peak width can
lock onto an 11 mm edge spike, so the local released mode reports flat where a smooth
stripe of the same height buckles (pinned by `test_released_gaussian_and_top_hat`); smooth
stripes are unaffected.

**Shohet-Townsend dead band** [V: Qu et al. 2025; Zambrano et al. 2006; Hajduk & Bernardes
2009]: `-80*(h/w)^beta < C_H/H - C_h/h < +40*(h/w)^beta`, `beta` = 1.86 (attributed to
Somers et al. 1984) or 2 (original). Inside the window lateral flow absorbs a relative crown
change; the window shrinks steeply with `h/w`.

**Crown heredity** [V: Qu et al. 2025, eq. 4]: `C_h = (1-eta)*C_gap + eta*(h/H)*C_H`. The gap
crown used is the supplied mechanical gap crown minus 2 x the healthy thermal crown. The
classification needs `gap_crown_m`, `entry_crown_m` and `heredity_coefficient`.

**Coil ridge build-up** [D criterion; V mechanism: Zhang et al. 2016, Sun et al. 2016, Melfo
2006]: `N(R) = (R - R_i)/h` wraps; build-up `dRad = c*N*r`; yield when
`dRad/R > (sigma_y - sigma_T)/E`; critical ridge height
`r_crit(R) = h*R*(sigma_y - sigma_T)/(E*c*(R - R_i))`; onset radius
`R_on = c*r*R_i/(c*r - s*h)` with `s = (sigma_y - sigma_T)/E`. The compaction factor `c` is an
analyst choice (default 0.5; interwrap gaps vary by up to about 4 um under load [V: Zhu et
al. 2009]). Incoming ridges pass the bite as
`dh = 2*C*(F_hin/W + N_x'*E*xi/H)*dH/(1 + 2*C*Q_eff)` [D, integration layer], then wind into
the coil.

**Tension troughs and roller wrinkles.** Wavelength and amplitude
`lam = sqrt(2*pi*L*t)/(3*(1-nu^2)*gamma)^(1/4)`,
`A = sqrt(nu*L*t)*(16*gamma/(3*pi^2*(1-nu^2)))^(1/4)`, `gamma = sigma_x/E` [V reconstructed:
Cerda & Mahadevan 2003, cross-checked against Panaitescu et al.]; trough onset in a free span
`sigma_y_cr = -(pi*h/a)*sqrt(E*sigma_x/(3*(1-nu^2)))` and roller wrinkle
`sigma_y_cr = -E*h/(R*sqrt(3*(1-nu^2)))` [V: Good, Beisel & Yurtcu 2009, isotropic
reduction]. A status other than "thresholds only" needs a supplied
`lateral_compressive_stress_pa`.

**Positions and spacing.** Two-tone band edges at the edges of earlier narrower strips [V:
QCA-1]; grinding feed pitch = traverse per revolution [V: EN 12258-1 grinding streak; trade
sources]; gaps between observed positions are tested as integer multiples (up to 8) of the
nozzle pitch, cooling-zone pitch, grinding feed pitch and trough wavelengths (analyst
tolerances); a gap beyond 8 candidate pitches is "not comparable".

Not modelled: lateral metal flow beyond the constant `xi`, entry-tension redistribution,
the feedback beyond its linear form and the band-wise saturation, shear lag of the tension
field, roll bending and the backup-roll contact, post-buckling stress relief, plasticity
outside the bite, interlayer slip in coils, strip tracking that spreads ridges, orthotropy,
roll friction in troughs.

### 7.3 What the model says about thin gauge for lengthwise bands

Source: `artifacts/band_diagnosis/lengthwise-bands-demo.result.json`,
`width.gauge_trend`. The same 2.715 um roll stripe (the demo's steady stripe at 0.6675 m,
isolated and scaled; it is a what-if, not each pass's own thermal state) is carried through
the six passes of the schedule, each with its own derived bite (all
`derived_slab_hitchcock`), tension and computed flow stress. A smooth Gaussian reference
stripe (half-peak width 0.1 m, about one cooling zone) is evaluated alongside. Onset heights
are the stripe heights at which a band first buckles, found by bisection on a grid of
0.00997 m. The search decides from the level with the exit-tension feedback only (review
fix: before, a scale at which the optional compliance-only bound left its domain, or any
error, counted as "buckled", which could set an onset where the feedback result was still
latent; in the demos this moved onsets only within the 1.5 % search tolerance, e.g. the
foil demo's S3 in-mill onset from 2.65 to 2.66 um). It has three outcomes: an onset at a
valid, manifest feedback result; not reached within the 50 um search ceiling; or not reached
before the feedback calculation itself leaves its domain (thickness change or elongation
outside the model), reported with that height in `*_domain_limit_m` keys and in the texts
("not reached before the feedback model leaves its domain at about X um"), never as an onset
and never as "above 50 um" in the direction sentence.

| pass | exit gauge [mm] | exit tension [MPa] | rigid bound [I] | compliance only [I] | linear feedback [I] | reported [I] | in-mill state (U) | after release (U, local mode) |
|---|---|---|---|---|---|---|---|---|
| P1 | 1.40 | 20 | 193.8 | 158.6 | 33.17 | 33.17 | latent (0.117) | manifest (4.35) |
| P2 | 0.90 | 25 | 301.4 | 238.5 | 34.70 | 34.70 | latent (0) | manifest (11.0) |
| P3 | 0.60 | 25 | 452.2 | 342.0 | 36.24 | 36.24 | latent (0.0045) | manifest (25.9) |
| P4 | 0.42 | 30 | 645.9 | 467.0 | 39.59 | 39.59 | latent (0) | manifest (57.7) |
| P5 | 0.30 | 30 | 904.3 | 628.2 | 43.84 | 43.84 | latent (0.0545) | manifest (125.4) |
| P6 | 0.21 | 30 | 1292 | 879.1 | 50.73 | 148.3 (saturated) | manifest (1377) | manifest (2424) |

| pass | in-mill onset, model stripe [um] | in-mill onset, Gaussian [um] | after-release onset, model stripe [um] | after-release onset, Gaussian [um] | reporting onset (2 I), model stripe [um] | dead-band half-width [I] | critical ridge height [um] | trough onset lateral stress [MPa] | band buckling stress [MPa] (width basis) |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 3.61 | 4.65 | 0.626 | 2.07 | 0.164 | 13.9 | 15.9 | -0.796 | 13.6 (Rayleigh b = 0.193 m) |
| P2 | 3.60 | 4.13 | 0.248 | 0.815 | 0.156 | 6.10 | 10.2 | -0.572 | 1.93 (reporting width 0.329 m) |
| P3 | 3.19 | 3.40 | 0.151 (upper bound) | 0.348 | 0.150 | 2.87 | 6.81 | -0.381 | 39.5 (Rayleigh b = 0.0485 m) |
| P4 | 3.28 | 3.34 | 0.139 (upper bound) | 0.156 | 0.137 | 1.48 | 4.77 | -0.292 | 0.421 (reporting width 0.329 m) |
| P5 | 2.88 | 2.82 | 0.125 (upper bound) | 0.111 (upper bound) | 0.124 | 0.791 | 3.41 | -0.209 | 5.88 (Rayleigh b = 0.0629 m) |
| P6 | 2.44 | 2.33 | 0.108 (upper bound) | 0.0964 (upper bound) | 0.107 | 0.407 | 2.39 | -0.146 | 0.0209 (Rayleigh b = 0.738 m) |

What these numbers say, plainly:

- **The raw elongation from a given stripe is nearly gauge-independent with the
  exit-tension feedback.** From 1.40 mm to 0.21 mm the linear-feedback flatness rises only
  from 33.2 to 50.7 I-units (x1.53), against x6.67 for the rigid bound and x5.54 for the
  compliance-only level. A model without the feedback would show a strong `1/h` trend in
  I-units that this model does not support.
- **The in-mill buckling onset falls only modestly with gauge.** For this broad cooling
  stripe a band can buckle in the mill only once its residual compression exceeds the mill
  tension (20-30 MPa here). The onset stripe height falls from 3.61 to 2.44 um for the model
  stripe (x1.48, and not monotonically: 3.19 um at P3, 3.28 um at P4) and from 4.65 to
  2.33 um for the Gaussian reference (x2.0). The 2.715 um stripe exceeds the onset only at
  P6, so it is latent in the mill on P1-P5 and manifest at the final pass; the in-mill
  utilisation is 0 to 0.12 on P1-P5 and 1377 at P6.
- **The strong thin-gauge trend is in the after-tension-release state and in the
  thresholds.** The after-release onset falls from 0.626 to 0.108 um for the model stripe
  (x5.8) and from 2.07 to 0.0964 um for the Gaussian (x21). But the after-release onsets of
  the model stripe on P3-P6 and of the Gaussian on P5-P6 coincide with the height at which
  the band first exceeds the 2 I-unit reporting threshold: they are **upper bounds**, and
  from P3 on any stripe large enough to be reported already buckles after release. The
  flatness dead band half-width falls from 13.9 to 0.407 I-units, the critical coil ridge
  height from 15.9 to 2.39 um and the trough onset lateral stress from -0.796 to -0.146 MPa:
  all scale with gauge.
- **The buckling stress column does not fall monotonically**, although `sigma_cr` scales as
  `t^2` at a fixed width. It is evaluated at the width that maximises the utilisation, which
  changes from pass to pass (0.0485 m to 0.738 m), and on P2 and P4, where the band holds no
  net compression in the mill, at the reporting-contour width (0.329 m). Between those two
  passes at equal width the ratio 1.93/0.421 = 4.59 equals `(0.90/0.42)^2`.
- So in the model, "worse at thinner gauge" for lengthwise bands is carried by bands that
  appear once tension is released (coil, slitter, table), by the shrinking dead band, by
  the critical ridge height and by the trough threshold, and at the final pass by a stripe
  that crosses the in-mill onset; it is not carried by a larger raw elongation. Which of
  these applies on a given mill has to be settled by the observation "visible only after
  tension release" (section 5.1).

At foil gauge the same chain gives a different picture: the linear-feedback I-units and the
in-mill buckling fall, not rise, toward the thin pass, and the after-release onsets are set by
the reporting threshold on every pass (section 3.5).

### 7.4 Short-lived bands

A switching event (`width_model.events`) sets the listed nozzles to a level for a duration;
the engine starts from the steady state, simulates all events as one transient followed by
a recovery of at least 600 s, and differences the radius against the steady state it started
from. At the monitor position it reports the analytic initial growth rate (7.1) beside the
simulated rate over the first 5 s, the time to each threshold (in-mill manifest onset,
after-release onset, reporting threshold, all as stripe heights from the peak profile
scaled), the time above the in-mill threshold (`visible_time_s`), the fade time after the
event, and the band life (event duration plus the time after the event to fall below the
manifest threshold). These are integration choices of `band_width.py` [D]:

- **Stripes.** Each connected group of adjacent switched nozzles is one stripe with its own
  monitor; an event that switches separated nozzles therefore gives several stripes. The
  stripe with the largest peak radius deviation governs the event's metrics
  (`governing_stripe_index`); all stripes are listed under `stripes` with their nozzles,
  monitor position, peak, time of peak and time to half peak.
- **Attribution window.** An event's metrics use the monitor history only from its start to
  `attribution_window_end_s` (measured from the event start): the start of the next event
  that switches nozzles within the isolation margin (0.1 m) of this one, else the end of the
  run. Beyond the window a fade gives only a lower bound (`band_life_lower_bound_s`,
  `visible_time_lower_bound_s`, flag `FADE_BEYOND_ATTRIBUTION_WINDOW`; at the end of the run
  `FADE_BEYOND_SIMULATED_RECOVERY`). Flags `LATER_EVENT_IN_SAME_REGION`,
  `PEAK_TRUNCATED_BY_LATER_EVENT` (the later event starts during this one),
  `EARLIER_EVENT_IN_SAME_REGION` (an earlier event leaves its residual in this history) and
  `CONCURRENT_EVENT_IN_SAME_REGION` say what could not be separated.
- **Peak profile.** Event boundaries are always recorded as snapshots, and the peak profile
  (shape and thresholds) is the snapshot at the governing stripe's measured peak time; if
  that time falls between records the transient is run a second time to record it
  (`peak_snapshots_recorded_by_second_run`). A short event is therefore never evaluated on
  the unchanged initial state.
- **Band at the stripe.** Thresholds, times, visible time and band life are the onsets of the
  band at the stripe peak, the position where the peak states are read. A restored nozzle (a
  level above the steady one) over-cools the roll: its stripe is tight at its own position
  and the loose bands sit in the compensating lanes beside it. Those lanes are reported
  separately (`neighbour_bands`: onset, offsets from the event nozzles, time above;
  `neighbour_bands_text`) and never used as evidence.

Demo events (`width.thermal_events`; the nearest switched nozzles of the two events are
0.728 m apart, so each event's window runs to the end of the run at 1050 s, no event carries a flag, each has one stripe, nozzles 20 and 21
being adjacent, and no second run was needed):

| quantity | event 1: nozzles 20-21 off | event 2: nozzle 6 off |
|---|---|---|
| start, duration | 0 s, 60 s | 300 s, 150 s |
| attribution window end, from the event start [s] | 1050 (end of run) | 750 (end of run) |
| local heat-transfer coefficient before / during [W/m2K] | 3794 / 1922 | 2858 / 1922 |
| net surface flux change [W/m2] | 14805 | 8185 |
| initial growth rate, analytic / simulated (first 5 s) [um/s] | 0.0939 / 0.0793 | 0.0519 / 0.0403 |
| peak radius deviation [um] | 3.56 at 60 s | 2.53 at 150 s |
| time to half peak [s] | 25.8 | 50.0 |
| in-mill manifest threshold [um]; time to it [s] | 2.23; 33.6 | 2.32; 128.5 |
| after-release threshold [um]; time to it [s] | 0.0977 (upper bound); 1.16 | 0.102 (upper bound); 2.37 |
| time above the in-mill threshold (visible time) [s] | 59.0 | 26.8 |
| fade time after the event, below the in-mill threshold [s] | 32.6 | 5.31 |
| band life [s] | 92.6 | 155.3 |
| half-decay after the event [s] (from `history`, interpolated) | 57 | 84 |
| state at peak, in mill / after release | manifest / manifest | manifest / manifest |

The simulated initial rate is 0.84 and 0.78 of the analytic one: the skin heats within
seconds and loses part of the flux change, and axial conduction spreads the stripe.

What makes a band short-lived in the model: the stripe crosses the in-mill threshold after
tens of seconds of zone-off time (33.6 s, 128.5 s) and drops back below it within seconds
to tens of seconds after the zone returns (32.6 s, 5.3 s), while the stripe itself decays
over about a minute (half-decay 57 s, 84 s). A band is short-lived because the stripe
spends only a short time above the threshold, not because the roll skin responds fast.
After tension release the threshold is reached within 1-3 s, so a band that is only seen
after release would last almost as long as the stripe itself. The model decay is slower
than the ~20 s plant-identified response (7.1, open discrepancy).

### 7.5 Lengthwise demo case

`scenarios/band_diagnosis_lengthwise_bands.json` (`synthetic: true`): the same single-stand
four-high mill as the chatter demo, final pass 0.30 -> 0.21 mm at 12 m/s, 1.5 m wide, work
roll radius 0.2 m, friction 0.03 supplied, flow stress computed from a synthetic Voce law,
schedule 2.2 -> 0.21 mm in six passes. Header: 32 nozzles at 52 mm pitch, 0.2 m standoff,
0.8 rad fans, mean spray coefficient 3000 W/m2K; nozzle 12 at 0.668 m partly blocked (flow
level 0.45); events: nozzles 20-21 off for 60 s, nozzle 6 off for 150 s. The roll heat share
(0.08 per roll from `strip_heat_fraction` 0.84) and the spray coefficient were chosen so that
the thermal crown lands in the 2-16 um reported for mills; the share is kept at 0.84 because the
process-temperature research found a measured partition for foil mills only (0.11-0.33 to the
strip), none for sheet-gauge cold rolling (section 3.12). Observations were generated from
the model itself (positions 0.357, 0.667, 1.093 m; duration 40 s; continuity both;
loose/buckle, visible in the mill; positions repeat and do not move after a work-roll
change; worse at thinner gauge).

Results (`artifacts/band_diagnosis/lengthwise-bands-demo.result.json`): bite heat
406 kW/m at the final pass; healthy thermal crown 8.80 um (9.24 um with the actual header);
one steady stripe, peak 2.715 um at 0.6675 m, half-peak width 0.195 m, next to nozzle 12; at
the final pass 147.5 I-units with the feedback (saturated), 878 compliance only, 1087 rigid
bound, manifest in the mill and after release. Ranking:

| rank | hypothesis | standing | score |
|---|---|---|---|
| 1 | `nozzle_thermal_stripe` | CONSISTENT_LEADING | 20 |
| 2 | `cooling_zone_switching_transient` | CONSISTENT | 17 |
| 3 | `tension_troughs_or_creases` | CONSISTENT | 6 |
| 4 | `heat_streak_or_film_variation` | CONSISTENT | 4 |
| 5 | `profile_flatness_mismatch` | CONSISTENT | 4 |
| 6 | `incoming_ridge_coil_buildup` | CONSISTENT | 2 |
| 7 | `oil_carryover_drips_or_stain` | CONSISTENT | 1 |
| 8 | `coil_or_mandrel_locked_marks` | NOT_ASSESSABLE | 0 |
| 9 | `foil_tension_lines` | WEAKENED | -1 |
| 10-20 | `roll_surface_band`, `grinding_feed_marks` and the other nine transverse hypotheses | CONTRADICTED | -3 to -11 |

Both planted causes come first and second. `foil_tension_lines` is weakened by the 368 mm
spacing (C weak; moderate, and the score -2, before the stage-B rule of section 6.2), the
210 um exit gauge (C mod) and the loose / buckle appearance (C weak).
Tension troughs score 6: the mean
observed gap (368 mm) lies at 0.745 and 0.932 x the computed trough wavelengths of the two
spans (494 mm and 395 mm), but the two gaps are irregular (coefficient of variation 0.158)
and come from bands of different causes, so the spacing gives only a weak support (it gave
a strong one, and the score 8, before the review fix of section 6.2); the lateral
compressive stress is not supplied, so the trough model gives thresholds only. The nozzle hypothesis matches only one
of the three positions (0.667 m), the zone hypothesis the other two; the "least favourable"
rule (6.4) is not applied to position matching, so each coolant hypothesis is supported by
the positions it explains.

## 8. Process models

Integration code: `physicroll/band_process.py`; equations: `physicroll/bite_tribology.py`.
These sections appear only in v2 cases with `tribology` and/or `hardening`.

### 8.1 Lubricant, film and friction

```
eta0(T) = eta_ref*exp(-beta*(T - T_ref)),   eta(T,p) = eta0(T)*exp(alpha*p)                 [D]
h_s = 6*eta0*alpha*U_mean/(theta0*(1 - exp(-alpha*(Y_ps - sigma_back))))                     [V restated]
U_mean = (u_roll + u_strip_entry)/2,  theta0 = sqrt((h_entry - h_exit)/R_contact) [D],  Y_ps = 2Y/sqrt(3)
Lambda = h_s/sqrt(Rq_roll^2 + Rq_strip^2);  BOUNDARY < 1 <= MIXED <= 3 < HYDRODYNAMIC        [V: Sutcliffe 2002]
mu(Lambda) = mu_v + (mu_b - mu_v)*exp(-Lambda/Lambda0)                                        [D] PLACEHOLDER
```

The film formula is Wilson & Walowit (1972) as restated by Sutcliffe (2002) and Le &
Sutcliffe (2000/2001) (original not read). The exponent uses the bite-entry pressure
`Y_ps - sigma_back` [D]; Sutcliffe and Le write `Y_ps` alone, Yarita (1984) writes the entry
pressure; the disagreement is recorded and the `Y_ps`-only value is reported alongside.
(The phase-1 film screen in `band_signatures.py` uses the same form with `Y_ps` alone,
flagged `FORMULA_QUOTED_FROM_MEMORY_VERIFY_BEFORE_USE` [M].) Viscosity data for
kerosene-based oils: 3.0 / 1.4 / 0.7 cSt at 20 / 70 / 130 C [V: US 4,844,830; Petroyag data
sheet], giving `beta` about 0.015 /K (20-70 C) [D]. Optional thermal thinning factor (off by
default) [V: Ghosh & Hamrock 1985 for the loading parameter; M for the factor form].

**The friction closure is a labelled placeholder, not fitted.** No closed-form mixed-film
law was found in a read source. Defaults: `mu_b` = 0.09 [V: Tabary, Sutcliffe et al. 1996,
abstract: about 0.09 at lowest speeds on aluminium strip, below 0.01 at the highest];
`mu_v` = 0.008 [D within 0.005-0.01]; `Lambda0` = 1.0 [D]. With ground-roll roughness it stays
near the boundary regime, so **its absolute values are placeholders; its slope with speed is
the usable output**. The computed friction is shown beside the supplied one and replaces it
only with `tribology.use_computed_friction: true` (then by a fixed point friction -> bite ->
contact radius -> friction).

Lengthwise demo (`process.friction`, `process.friction_speed_curve`): final pass film
70.3 nm, film ratio 0.180, BOUNDARY; placeholder friction 0.0765 against 0.03 supplied (not
used); slope -1.03e-3 per m/s at 12 m/s, mean -1.01e-3 per m/s between 2 and 25 m/s. Every
schedule pass is in the boundary regime (film ratio 0.0139 to 0.180).

### 8.2 Pass heating

```
w_pl = (2/sqrt(3))*Y_mean*ln(h_entry/h_exit)        [D]   (homogeneous, no redundant shear)
Q = w_pl*h_exit*u_exit + P_friction                  [D]   per unit width [W/m]
T_exit = T_entry + f_s*Q/(rho*c*h_exit*u_exit),  rho*c = 2.43e6 J/(m3 K)   [D]
each work roll receives (1 - f_s)/2 of Q             [D]
```

`P_friction` is the interface slip dissipation of the slab (or mattress) solution. The
strip heat fraction `f_s` is **supplied**, not computed: foil mills put 0.11-0.33 of the
bite heat into the foil [V abstract: Yin et al. 2003]; thicker strip keeps much more [M]. The
roll heat fraction derived from it drives the roll thermal model, so the stripe heights scale
with this guess. Lengthwise demo (`process.heating.operating`): plastic power 293 kW/m,
friction power 113 kW/m, total 406 kW/m; strip 313.15 -> 368.9 K (+55.7 K); 32.5 kW/m to each
work roll.

### 8.3 Work hardening

Equivalent strain `eps = prior + (2/sqrt(3))*ln(h_ref/h)` (as `physicroll.materials`). Laws:
power `sigma = sigma_y + K*eps^n` and a generalised Voce law with a stage-IV term
`sigma = s0 + (ss - s0)*(1 - exp(-eps/eps_c)) + theta4*eps` [D form; Hirsch et al., Ryen et
al. 2006, read second-hand], with the analytic pass mean. Strain-rate sensitivity is taken as
zero [M]. Literature fits shipped for reference:

| fit id | alloy, temper | law | yield [MPa] | K [MPa] | n | tag |
|---|---|---|---|---|---|---|
| `1100-O_kalpakjian` | 1100-O | Hollomon | 0 | 180 | 0.20 | [V via secondary source] |
| `5052-O_kalpakjian` | 5052-O | Hollomon | 0 | 210 | 0.13 | [V via secondary source] |
| `1050-annealed_batorfi` | 1050 annealed | Ludwik | 15.3 | 144.6 | 0.37 | [V: Batorfi et al. 2023] |

Warning carried with every fit: tensile-fitted power laws over-predict beyond `eps` about 0.3
[V: Kazaoka et al. 2015] and are not calibrated for rolling; a final pass of a schedule reaches
`eps` well above 2. The demo Voce parameters are synthetic (not fitted); final-pass flow
stress 282.6 MPa computed against 270 MPa supplied (`process.flow_stress`).

### 8.4 Speed-consistent chatter critical speed

With friction falling as speed rises, the critical speed is the speed `u` with
`u = u_crit(mu(u))` [D], where `mu(u) = mu_used + [mu_closure(u) - mu_closure(u_op)]` (the
placeholder supplies the slope, the operating friction the level), scanned and bisected in
log speed with the contact radius and forward slip held at the operating bite. The perturbed
bites use the operating bite's model (review fix; section 10.2); scan speeds that model cannot
solve are rejected rows, and when the lowest assessable speed is already unstable the status
is `UNSTABLE_AT_LOWEST_ASSESSABLE_SPEED` with `lowest_assessable_exit_speed_m_s` (the crossing
lies at or below it), never a crossing. Lengthwise demo (`chatter.speed_consistent`): the
higher placeholder friction below the operating speed makes Hitchcock reject the slow scan
speeds, and at the lowest assessable speed, 19.9 m/s, the pass is already unstable with
and without bite damping, so no speed-consistent critical speed is given (fixed friction
0.03: 13.85 m/s, beta 0.5; 5.16 m/s, beta 0). Before the fix those slow scan speeds fell back
to the mattress model and gave 13.30 and 8.79 m/s, mixing the two bite models.

## 9. Mill dynamics (`mill_dynamics.py`)

Status `UNVALIDATED_LINEAR_MILL_DYNAMICS_SCREEN`; wraps `chatter.py` without changing it.
The results never change hypothesis evidence.

**Gaugemeter AGC** [V: BISRA gaugemeter `h = S + F/M`, correction `dS = -alpha*dF/M`, IJCA
9(2); cylinder closed-loop bandwidth 20-30 Hz, Scheidl et al. 2016, Karl et al. 2011]. The
half stack gets a seventh state, the housing-spring anchor `x_s` (positive = gap opening):

```
M_b*x_b'' = K_wb*(x_w - x_b) + C_wb*(x_w' - x_b') - K_h*(x_b - x_s) - C_h*x_b'      [D]
dF_meas = K_h*(x_b - x_s),   x_s' = omega_c*(x_s_ref - x_s),   x_s_ref = -alpha*dF_meas/(2*M)   [D]
```

Static limits, **tension held constant** (reel regulators; "tension coupling off") [D]:

```
run-out e:        dh = -2e*M/(M + (1-alpha)*Q)                       [D]
bite input dF0:   dh = (1-alpha)*dF0/(M + (1-alpha)*Q)               [D]
                  (entry thickness dF0 = F_hin*dh_in; flow stress dF/dY*dY; friction dF/dmu*dmu)
```

`alpha = 0` recovers `chatter.py`; `alpha = 1` prints run-out through in full, an
amplification `(M+Q)/M` over `alpha = 0` [V: Ichiryu, J. JHPS 26(6):778]. With tension
coupling on, the constant-speed spans act as integral mass-flow control at DC [D]: run-out,
flow-stress and roll-speed inputs give `dh -> 0`, incoming gauge `dh -> (h1/h0)*dh_in`.

Lengthwise demo (`gauge_control`, alpha 0.9, 25 Hz, `M` = 5.19e9 N/m, `Q` = 1.78e10 N/m):
run-out transfer -0.451 without AGC and -1.489 with it (eccentricity amplification 3.30);
entry-thickness transfer 0.584 without and 0.193 with AGC.

**AGC-chatter interaction, and why it depends on the loop roll-off** [D, finding of this
module]. Well above its bandwidth a first-order loop lags 90 degrees, so the anchor force on
the backup roll is in phase with its velocity: an equivalent negative damping of about
`alpha*K_h^2*omega_c/(2*M*omega^2)`. Real servo-valve, oil-column and filter dynamics roll off
faster. The engine therefore reports the supplied loop and the same loop with a 25 Hz
first-order force filter (an analyst option, flag
`ANALYST_FORCE_FILTER_OPTION_NOT_FROM_CITED_SOURCE`). Lengthwise demo
(`gauge_control.chatter_with_loop`):

| loop | critical speed, beta 0.5 [m/s] | change | critical speed, beta 0 [m/s] |
|---|---|---|---|
| no AGC | 13.85 | | 5.16 |
| supplied first-order loop | 9.70 | -29.9 % (unstable at 12 m/s) | unstable at the lowest scanned speed |
| with 25 Hz force filter | 13.62 | -1.6 % (stable at 12 m/s) | 4.87 (-5.6 %) |

Which of the two applies to a real mill depends on its actual loop dynamics, which the model
does not have.

**Incoming hardness variation** [V: about 2 % cyclic, once per decoiler revolution, ABB
"Improvement of thickness tolerances"]. `dF/dY` by central differences (+-0.5 % of the flow
stress) [D], taken through the engine's own bite cache with the same bite model as the
operating pass (`sensitivity_bite_model`), so it also works for a pass solved by the mattress
model (10.2); static gauge change by the bite-input formula above (tension held constant); decoiler
frequency `n*u_e/(pi*D_coil)`, exit pitch `pi*D_coil*h0/(h1*n)` [D]. Demo
(`incoming_variation`): 2 % = 5.65 MPa flow-stress amplitude; static exit-gauge change 3.68 um
without AGC, 1.22 um with it; decoiler 2.23 Hz, exit pitch 5.39 m (first harmonic).

**Drive torsional modes** [D; benchmark V: J. Phys. Conf. Ser. 2419 (2022) 012027; first-mode
guidance 10-20 Hz V: Gao et al.]: free-free chain `J*theta'' + K*theta = 0`; reel inertia
reflected to the motor `J = J_motor + pi*rho*W*(R^4 - R_m^4)/(2*N^2)` [V: Soler, Isermann &
Feldmann 2008]. Roll-speed ripple enters the tension rows only:
`du_x = (1+f)*dV_r`, `du_e = (1+f)*(h1/h0)*dV_r` [D]. Demo (`drive`): modes 18.47 and 37.56 Hz,
strip pitch 0.650 and 0.319 m at 12 m/s; the computed modes replace the generic 5-30 Hz band
in the torsional rule (6.3).

**Speed-change gauge shift** [V context: Zhang et al. 2017 IJCA 10(6); formula D, tension held
constant]: `dh = (1-alpha)*dF0/(M + (1-alpha)*Q)` with `dF0 = dF/dmu*dmu` from the friction-speed
slope; `dF/dmu` is a central difference (+-2 % of the friction) through the bite cache with the
operating bite model, as for `dF/dY`. In the demo both sensitivities report
`sensitivity_bite_model` `derived_slab_hitchcock`. Demo (`gauge_control.speed_change_gauge_shift`, 6 -> 12 m/s): placeholder friction
0.0829 -> 0.0765, force -242 kN, exit gauge -4.68 um with AGC, -14.2 um without; the
absolute friction values are placeholders (8.1).

Not modelled: the cylinder as anything but a first-order loop, AGC monitor / feed-forward /
mass-flow AGC, eccentricity compensation, tension regulators between the two idealisations,
motor and drive control loops, gear backlash, strip elastic recovery, thermal effects, roll
bending and cross-width variation.

## 10. Thin-gauge roll bite

### 10.1 Where the Hitchcock path stops

The bite sensitivities normally come from the slab model with circular Hitchcock flattening
(`chatter.derive_bite_response`), which is rejected above a contact radius ratio of 1.5
(`max_radius_ratio`, may be raised to 3.0 with the flag
`HITCHCOCK_RATIO_BEYOND_REVIEWED_ENVELOPE`) and rejects with "sticking model required" when
Coulomb shear exceeds the shear yield. Probe on the demo mill (R = 0.2 m, width 1.5 m, 30 %
reduction, tensions 10 / 11 % of flow stress, 64 cells; phase-1 probe, not a demo file):

| flow stress | friction | entry gauge that still derives | first rejected (reason) |
|---|---|---|---|
| 270 MPa | 0.03 | 0.30 mm (ratio 1.453) | 0.25 mm (ratio 1.536) |
| 270 MPa | 0.05 | none of 0.10-0.30 mm | 0.30 mm (ratio 1.654); 0.15 mm and below: sticking model required |
| 150 MPa | 0.03 | 0.15 mm (ratio 1.408) | 0.10 mm (ratio 1.644) |
| 150 MPa | 0.05 | 0.20 mm (ratio 1.467) | 0.15 mm (ratio 1.721); 0.10 mm: sticking model required |

For hard alloys the derived path stops at about 0.3 mm entry gauge and only at low friction.
Passes below 0.3 mm carry the flag `THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN`. On the softer,
smaller-roll foil demo mill Hitchcock still solves 0.135, 0.085 and 0.050 mm exit gauge and
rejects 0.030 mm (section 3.3).

**Domain limits** (SPEC12 stage A): the slab and Hitchcock path (`chatter.BitePass.validate`)
keeps an exit thickness of at least 2e-5 m (its **20 um floor**) and a reduction between 0.02
and 0.5, so `bite_model: "hitchcock"` rejects a thinner or heavier pass. The mattress model
(`foil_bite.py`) accepts an exit thickness down to 8e-6 m (`BITE_FLOOR_M`, the **8 um floor**;
the engine checks it first and reports `EXIT_GAUGE_BELOW_BITE_MODEL_FLOOR`) and a reduction
up to 0.65. Between 8 and 20 um, and between 50 and 65 %, its bite is in the **extended
domain**, flagged `EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN` and
`REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN` and, below 20 um, given a credibility mark
against the force range reported for battery-foil passes (section 3.3). Below the 8 um floor no
bite exists for the pass, whatever `bite_model` says.

### 10.2 Experimental mattress (elastic-foundation) model (`foil_bite.py`)

Status `UNVALIDATED_EXPERIMENTAL_MATTRESS_FOIL_BITE`. A planner reduction [D] in the spirit of
Fleck & Johnson (1987; read only through a poor OCR copy) and of the MISG report "A simple
model for the cold rolling of metal foil" [V for the non-dimensional form
`(h - G2)p' + mu*p = x`]. It is **not** the Fleck-Johnson hybrid model: the strip is
rigid-perfectly-plastic (no elastic strip zones) and the roll a local Winkler foundation.

```
h(x) = g0 + x^2/R + 2*p(x)/K_p                                          [D]
p'*(h - 2K/K_p) = K*(2x/R) + s*2*mu*p,   yield p + sigma = K,  K = 2Y/sqrt(3)   [D]
h' = [ (2x/R)*h + s*4*mu*p/K_p ] / (h - 2K/K_p)   (s = +1 entry side, -1 exit side)   [D]
K_p = (3*pi/8)*E*/a = 1.178*E*/a,   E* = E/(1 - nu^2),  a = half the contact length   [D]
```

The foundation modulus comes from equating a Winkler layer under a rigid cylinder with Hertz
line contact [D; the specification quoted 1.18 E*/a from memory, M]; applying a Hertz
calibration to a non-Hertzian bite is itself an assumption, and the force scales strongly
with it. `a -> K_p -> solution` is iterated to a fixed point. The slab denominator must stay
positive: `h > 2K/K_p` is the mattress limiting gauge. Regimes: CONVENTIONAL (the branch
pressures meet at a neutral point) or FOIL (a no-slip zone of constant thickness `h_n` with
`|tau| <= mu*p`, forward slip `h_n/h_exit - 1`). Stone's `t_min = 3.58*mu*D*(Y - sigma_mean)/E_roll`
[M] is reported for context only.

**Contact end zones, added to make the model self-consistent** [D, this module; default
`contact_end_zones=True`]. The specification ended contact abruptly at the plastic entry and
exit points. With a local foundation the roll surface just outside them would spring back to
`g0 + x^2/R`, about 6 um thinner than the strip at sheet gauge: the rolls would overlap the
strip. The completion keeps the strip rigid where the foundation still presses it,
`p = K_p*(h_side - g0 - x^2/R)/2`, out to zero pressure: on the exit side the rigid strip
moves faster than the roll (`tau_f = -mu*p`, `h*sigma' = 2*mu*p`, `sigma` reaches the exit
tension at the contact end), and the specification's exit condition `h' = 0` is exactly the
smooth junction with this zone; on the entry side the strip is slower than the roll and
yields where `p + sigma = K`. `contact_end_zones=False` reproduces the specification and flags
`SPEC_LITERAL_END_CONDITIONS_OVERLAP`.

**Agreement with Hitchcock where both solve** (computed from the test inputs of
`tests/test_foil_bite.py`, not from a demo file): 0.6 -> 0.42 mm, 250 MPa, friction 0.05,
tensions 25 / 30 MPa: separating force 3.696 MN against 3.556 MN (+3.9 %), forward slip
0.0416 against 0.0553, contact radius ratio 1.547 against 1.291; 0.30 -> 0.21 mm, 270 MPa,
friction 0.03: 2.836 MN against 2.787 MN (+1.7 %), forward slip 0.0339 against 0.0510. The
tests assert only the same order (force ratio 0.5-2, the eight sensitivities of the same sign
and within a factor 5). The same 0.30 -> 0.21 mm pass at friction 0.05, rejected by
Hitchcock, solves in the conventional regime.

**Where it rejects** (ValueError, never numbers): exit gauge at or below the limiting gauge
`2K/K_p`; Coulomb shear above the shear yield in any slip zone (the published high-friction
foil case, 50 -> 25 um at friction 0.10, is rejected for this reason); an exit that would have
to stick (zero forward slip); a fixed point that does not converge; a force that changes by
more than 1e-3 on grid refinement.

**How far to trust it.** The model is verified for internal consistency only (rigid limit,
junction continuity, Coulomb limits, energy identity, grid convergence, trends). No benchmark
with fully known inputs was found. In the foil regime it can give implausibly large forward
slip because there are no elastic strip zones (flag
`FORWARD_SLIP_IMPLAUSIBLY_LARGE_NO_ELASTIC_STRIP_ZONES`). Treat foil-regime numbers as order
of magnitude only.

**`model_options.bite_model`**: `hitchcock` (default; slab + circular flattening), `mattress`
(always the experimental model, at least 200 cells) or `auto` (Hitchcock, and the mattress
model only when Hitchcock rejects the pass; the reason is kept in `bite_fallback_reason`).
Mattress bites carry the flag `BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL`, and the report's key
numbers name their source `experimental_mattress`. The perturbed bites of the flow-stress and
friction sensitivities (section 9) use the model of the operating bite: the mattress model
when the operating bite is a mattress bite or `bite_model` is `mattress`, else Hitchcock
(also for `auto` with a Hitchcock operating bite, and for a supplied bite). The lever table
and the speed-consistent critical speed follow the same rule (review fix): a perturbed pass
the operating model cannot solve is reported as rejected (not assessable) with the reason
instead of falling back to the other model. Before the fix this mixing did occur in the
lengthwise demo: the friction x1.3, reduction x0.8 and entry-tension x0.5 levers and the
slow speed-consistent scan speeds were derived with the mattress model while the operating
bite is Hitchcock; they are now rejected rows. The lengthwise demo uses `auto`; every pass derived with Hitchcock. The battery-foil demo
uses `auto`; S1-S3 derive with Hitchcock and the case pass F1 falls back to the mattress
model in its foil regime (section 3.3). A bite from a plant or foil-mill model can still be
supplied in `model_options.bite_response_override`; for the strip-shape chain alone,
`width_model.shape_inputs` is the lighter alternative (section 3.4).

## 11. Transverse physics (chatter)

### 11.1 Third-octave chatter model (`chatter.py`)

`x_w`, `x_b`: upper work / backup roll displacement, positive away from the pass line; the
lower half mirrors it, so `dh = 2*x_w` (no strip elastic recovery). `dF`: separating-force
perturbation, positive pushes the rolls apart. `sigma_e`, `sigma_x`: entry / exit tensile
stress perturbations. `V_r` roll surface speed (held constant), forward slip
`f = u_x/V_r - 1`. Model built in this project on the mechanism of Tlusty et al. (1982), Yun,
Wilson & Ehmann (1998) and Niroomand et al. (2012) [D]:

```
M_w*x_w'' = -K_wb*(x_w - x_b) - C_wb*(x_w' - x_b') + dF                        [D]
M_b*x_b'' = +K_wb*(x_w - x_b) + C_wb*(x_w' - x_b') - K_h*x_b - C_h*x_b'        [D]
K_mill = 1/(2*(1/K_wb + 1/K_h))                                                [D]
dF = F_h*dh + F_hdot*dh' + F_se*sigma_e + F_sx*sigma_x + F_hin*dh_in,   Q_s = -F_h > 0   [D]
df = f_h*dh + f_se*sigma_e + f_sx*sigma_x + f_hin*dh_in                         [D]
F_hdot = F_h*beta*l_d/u_x          [D] bite-damping closure, declared heuristic
du_x = V_r*df                                                                  [D]
du_e = V_r*[(h1/h0)*df + ((1+f)/h0)*dh - ((1+f)*h1/h0**2)*dh_in]              [D]
sigma_e' = +(E/L_e)*du_e,          sigma_x' = -(E/L_x)*du_x                    [D]
```

The gap opens, more strip is drawn in, the entry tension rises as the integral of the gap
opening (90 degree lag), the force drops, and the force component in phase with gap velocity
feeds energy into the stack: negative damping that grows with speed. The critical exit speed
is the lowest speed where the largest eigenvalue real part crosses zero. Results are given for
the supplied `beta` (default 0.5) **and** for `beta = 0`, because much of the margin rests on
the bite-damping closure (its 1/speed scaling as reported by Hu, Zhao & Ehmann 2006 and
Kimura et al. 2003). Single-DOF benchmark [D]: `u_crit = C*(K+Q_s)*L*h0/(M*N*E)` at
`omega = sqrt((K+Q_s)/M)`. Phase 2 adds a reliability check: when the onset frequency exceeds
the span-wave limit `c/(2L)`, `c = sqrt(E/rho)` (636 Hz for the 4 m demo spans), the lumped span
is not reliable and the result is flagged (6.3).

### 11.2 Pitch laws and signatures (`band_signatures.py`)

```
fixed frequency F:            p = u_x/F                         [V: Kim et al. 2012, f = v/p]
n marks on a roll of dia. D:  p = pi*D*(1+f)/n                  [V: Krueger, Richard & Peretic 2019]
order k of work-roll speed:   p = pi*D_w*(1+f)/k                [V: Krueger, Richard & Peretic 2019]
exit coil:                    p = pi*D_coil;  entry coil: p = pi*D_coil*h0/h1     [D]
later pass:                   p_out = p_in*h_in/h_out                            [D]
bearing orders, r = (d/D)*cos(phi):  BPFO = n/2*(1-r), BPFI = n/2*(1+r),
                              FTF = (1-r)/2, BSF = D/(2d)*(1-r^2)                 [V: Randall & Antoni 2011]
```

Other screens: bending strain `t/D` against the yield-point window
`[t/(eps_y+eps_L), t/(eps_y - sigma_t/E)]` [V sources: QCA-1; Choi, Jin & Kang 1998; de Codes
et al. 2011]; herringbone pitch about the arc of contact at reduction >= 0.40 [V: Komori 1996;
Szucs et al. 2020]; forward slip <= 0 skidding [V: Reid & Schey 1978]; inlet film [M] (8.1);
flat-fan coverage `W = 2*s*tan(angle/2)`, `W_eff = W*cos(offset)` [V: Lloyd 2010; Tucker 2006];
free thermal growth `dR = alpha*R*dT` (upper bound) and gap closure `2*dR/h_exit` [D]. In v2
cases with a `width_model` the solved roll temperature field (7.1) replaces the free-growth
screen for the lengthwise hypotheses.

### 11.3 Transverse demo cases

Both use the synthetic single-stand four-high aluminium mill: work roll 0.40 m, backup roll
1.15 m, half-stack masses 3000 / 22000 kg, `K_wb` = 4e10 N/m, `K_h` = 1.4e10 N/m, 3 % modal
damping, strip E 70 GPa, 4 m spans, beta 0.5, 256 cells, max radius ratio 1.5. Unloaded
antisymmetric modes 118.8 and 621.1 Hz.

**Thin-gauge chatter** (`artifacts/band_diagnosis/thin-gauge-chatter-demo.result.json`):
AA3104-H19 final pass 0.30 -> 0.21 mm, flow stress 270 MPa, friction 0.03, tensions 25 /
30 MPa, 16 m/s; observations generated from the model (pitch 76.5 and 84.1 mm at 14.5 and
16 m/s, exponent 0.964; these speeds are about 10 % apart, so the result carries the flag
`NARROW_SPEED_RANGE_BELOW_20_PERCENT`). Result: `third_octave_self_excited_chatter`
CONSISTENT_LEADING, score 18; every other transverse hypothesis WEAKENED or CONTRADICTED and
every lengthwise hypothesis CONTRADICTED by the transverse orientation.

**Bearing order** (`artifacts/band_diagnosis/bearing-order-demo.result.json`): modelled on a
published aluminium case (Innoval: 20-25 mm bands, pitch independent of speed, 315 Hz at
470 m/min = 2 x BPFI of a work-roll bearing); work roll 0.284 m (with 0.40 m the same bearing
gives 35 mm and 221 Hz). Pass 1.0 -> 0.70 mm at 7.83 m/s; pitch 24.92 mm at 6.0 and 7.83 m/s;
measured 314.3 Hz. Result: `order_locked_drive_or_bearing_excitation` CONSISTENT_LEADING,
score 8, best match `bearing:WR_chock_4row_TRB:2x_bpfi` (mismatch 0.007 %). This pass is
stable with beta = 0.5 (`u_op/u_crit` = 0.650) but would be unstable with beta = 0
(`u_crit(0)` = 4.10 m/s, ratio 1.91): the margin of a mill that by construction shows no
chatter rests on the bite-damping closure.

### 11.4 What the model says about thin gauge for chatter

Source: `artifacts/band_diagnosis/thin-gauge-chatter-demo.result.json`, `schedule_sweep`.
Six passes with speeds rising and friction falling as mills run them; flow stress
190 -> 270 MPa; tensions 15/20, 20/25, 20/25, 25/30, 25/30, 25/30 MPa.

| pass | gauge [mm] | speed [m/s] | friction | R'/R | Q_s/K_mill | u_crit beta 0.5 [m/s] | u_crit beta 0 [m/s] | u_op/u_crit | u_op/u_crit(0) | onset [Hz] | pitch at u_op [mm] | rel. ripple per um run-out (WR 2x) | thermal gap closure (upper bound) | t/D on 0.30 m deflector |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 2.20 -> 1.40 | 3.0 | 0.08 | 1.090 | 0.68 | 12.55 | 3.37 | 0.239 | 0.89 | 145.2 | 20.7 | 4.06e-4 | 0.017 | 4.67e-3 |
| P2 | 1.40 -> 0.90 | 5.0 | 0.07 | 1.140 | 1.13 | 13.60 | 3.63 | 0.368 | 1.38 | 156.9 | 31.9 | 4.69e-4 | 0.027 | 3.00e-3 |
| P3 | 0.90 -> 0.60 | 7.5 | 0.06 | 1.212 | 1.76 | 14.89 | 4.38 | 0.504 | 1.71 | 169.7 | 44.2 | 5.41e-4 | 0.040 | 2.00e-3 |
| P4 | 0.60 -> 0.42 | 10.0 | 0.05 | 1.298 | 2.41 | 15.48 | 5.20 | 0.646 | 1.92 | 179.6 | 55.7 | 6.31e-4 | 0.057 | 1.40e-3 |
| P5 | 0.42 -> 0.30 | 13.0 | 0.04 | 1.389 | 2.99 | 15.24 | 5.61 | 0.853 | 2.32 | 186.6 | 69.7 | 7.23e-4 | 0.080 | 1.00e-3 |
| P6 | 0.30 -> 0.21 | 16.0 | 0.03 | 1.456 | 3.22 | 13.27 | 4.83 | 1.206 | 3.31 | 189.1 | 84.6 | 8.34e-4 | 0.114 | 0.70e-3 |

The same passes at the final-pass friction 0.03 (`at_case_friction`): critical speed (beta
0.5) 5.96, 8.27, 10.43, 12.19, 13.27 m/s for P2..P6 (P1 at friction 0.03 rejects: no unique
interior neutral point).

- **At equal friction a thinner pass is more stable in this model**, not less: 5.96 m/s (P2)
  to 13.27 m/s (P6), because the plastic strip stiffness `Q_s` grows faster than the entry
  gauge falls (`Q_s/K_mill` 1.13 -> 3.22).
- With the schedule's own friction the critical speed is nearly flat (12.55-15.48 m/s) and
  drops on the last pass, where friction is lowest. What rises steadily is the
  operating-to-critical speed ratio, 0.239 -> 1.206, because thin passes are run fastest; only
  the final pass crosses it.
- **Without the bite-damping closure** every pass except P1 is above its critical speed
  (ratios 1.38-3.31).
- The relative gauge ripple per micrometre of run-out at 2 x work-roll rotation doubles
  (4.06e-4 -> 8.34e-4 per um), and the free-expansion thermal gap-closure fraction of a 5 K
  stripe rises from 0.017 to 0.114; the bending strain `t/D` falls (yield-point bending marks
  become less likely at thin gauge).

### 11.5 Levers and coolant for chatter

Lever table of the thin-gauge demo (`levers`; baseline 13.27 m/s, 4.83 m/s with beta 0):

| change | u_crit [m/s] | u_crit beta 0 [m/s] | ratio to baseline |
|---|---|---|---|
| entry span x2 | 19.59 | 9.04 | 1.477 |
| entry span x0.5 | 9.04 | 2.50 | 0.681 |
| friction x0.7 | 9.69 | 2.96 | 0.731 |
| structural damping x2 | 16.79 | 9.94 | 1.265 |
| structural damping x0.5 | 11.81 | 2.40 | 0.890 |
| reduction x1.2 | 12.10 | 3.93 | 0.912 |
| entry tension x1.5 | 12.23 | 4.24 | 0.922 |
| entry tension x0.5 | 14.30 | 5.46 | 1.078 |
| exit tension x1.5 | 13.49 | 4.98 | 1.017 |
| exit tension x0.5 | 13.06 | 4.70 | 0.985 |
| friction x1.3 | rejected (radius ratio 1.532) | | |
| reduction x0.8 | rejected (radius ratio 1.507) | | |

Directions are generated from these numbers: lower friction, higher reduction and higher
entry tension lower the critical speed; exit tension has a small opposite effect; a longer
entry span and more structural damping raise it. The literature disagrees on the friction and
tension effects (section 15). Coolant acts on chatter through friction and film thickness;
with a `tribology` section the friction-speed slope enters the speed-consistent critical speed
(8.4). It acts on lengthwise bands through the roll temperature field (section 7).

## 12. The report

`<slug>.report.html` is a self-contained page (inline SVG, no scripts), produced by
`physicroll/band_report.py`. It opens with the case name, a warning box with the status
`SCREENING_RESULT_NOT_PLANT_VALIDATED` and the score note, and the provenance. For a foil
case (a `foil_regime` block in the result) a red-framed box headed "Foil gauge: closed-gap
rolling likely — not modelled" comes between the warning box and the provenance, before
everything else (described below). A v1 result
renders the phase-1 page. A v2 result adds the case notes, the family statement and the
lengthwise, process and dynamics sections; when the observed or leading family is
lengthwise the page leads with the lengthwise sections and moves the transverse (chatter)
sections into a block headed "Transverse-band (chatter) screening: supporting detail for this
case". Sections of the lengthwise demo report
(`artifacts/band_diagnosis/lengthwise-bands-demo.report.html`), in order:

| section | what it shows |
|---|---|
| Which family of causes | the `family_summary` text, the observed family and the family of the leading hypothesis, the number of non-contradicted hypotheses per family, and a one-line summary of the key observations as entered |
| Leading hypotheses | each `CONSISTENT_LEADING` hypothesis with the criteria that support and contradict it; up to three other `CONSISTENT` hypotheses of the observed family with theirs |
| Next measurements | `recommended_next_measurements` (the confirming tests of the top three and the key missing observations), then the result flags |
| Across the width: predicted against observed bands | upper panel: steady roll radius growth with the actual and with a healthy header, nozzle positions; lower panel: flatness at the three levels of the shape chain (the thick line is the linear-feedback level), dashed lines at the observed positions; a note on a saturated band and on the whole-sheet indicator. Tables: Steady stripes (peak, half-peak width, I-units per level, state in the mill and after tension release, buckling utilisation, stripe heights for a band in the mill, after release and at 2 I-units); the nozzle-pattern ripple; Which predicted source each observed band matches; Which pitch the gaps are multiples of; Tension troughs (span wrinkling); then two-tone, grinding feed, incoming ridges and crown lines |
| Short-lived bands (cooling-zone switching events) | per event: radius deviation against time with the in-mill, after-release and reporting thresholds, and the event table of 7.4 (rows for the stripes of an event with several groups of adjacent nozzles, and for attribution flags, appear only when present; a fade beyond the attribution window reads "not attributable after ... s: a later event switches nozzles in the same neighbourhood"); the growth-rate note and the open discrepancy |
| How the result changes with gauge | a generated direction sentence, then the gauge-trend text, two charts and the table of 7.3 |
| Hypotheses | every hypothesis grouped by family (observed family first) with standing, score, evidence items and confirming test |
| Transverse-band (chatter) screening: supporting detail | Key model numbers, What the model predicts on the strip, Chatter stability, Pass-schedule sweep, Frequency-speed map, Forced response and time trace, Levers (with coolant spray coverage and other screens) |
| Process: friction, flow stress, pass heating | section 8: friction against speed, flow stress per pass (supplied, computed, used), pass heating, speed-consistent critical speed |
| Gauge control, drive and incoming variation | section 9 |
| Limitations and sources | result limitations, known disagreements in the literature, sources |

**The foil box** (`artifacts/band_diagnosis/battery-foil-demo.report.html`) shows, from
`foil_regime`: where the case sits against the reported closed-gap onsets and the three
disagreeing sources; the implications list (load not a gauge actuator, open-gap levers and
gauge control, compliance transfer without the shunted load, online against offline
flatness, rule-only foil defects); the bite model of the case pass with its reliability
text, force per width against the reported 0.9-2.3 kN/mm, forward slip and the reason
Hitchcock rejected it; a table of bite model and force per width per schedule pass, with the
rejection reason for a pass without a bite; an "Extended roll-bite domain." paragraph when a
pass lies below 20 um exit gauge or above 50 % reduction, with the `extended_bite_domain` text
(what the numbers are worth, and "NOT CREDIBLE ..." for a pass whose force lies outside the
0.9-2.3 kN/mm reported for battery-foil passes); a "Below the roll-bite model floor" paragraph
when a pass is under 8 um, asking whether that pass is single-sheet or doubled (or, with
`material.final_pass_doubled` set, stating the plant's answer; the foil demo shows the
single-sheet statement there, in the implications and in the product question); the wrinkle
rule of thumb against the largest model band; and the product question. Directly after the
foil box comes **"Product check (published envelope, literature survey)"** when the result
has `product_check`: the product, the alloy designation and temper used, the evidence-neutral
note, a table of verdict words per pass and item (upper case for a value outside the published
span, "(final pass)" marked), the nearest published passes for the case pass and the final
pass with their read status, the flags and the catalogue limitations; without a product it
says "not supplied" and lists the catalogue ids. After it, **"Material selection (literature
proposal, to confirm with the plant)"** when the result has `material_selection`: the plain
sentence, the bands of the final and the case pass, the options table at the final gauge
(GB minimum, typical Rm, usual choice, evidence, sources), the two proposals (a fallback
proposal marked "evidence WEAK"), the case against the band (alloy, temper, yield stress, a
verdict per pass) with the indicator-only caveat, flags and limitations. For a v2 case with a
width model or tribology, a **"Process temperatures"** section follows the process section:
the case's thermal inputs and the modelled outputs against the literature (`thermal_check`,
section 3.12), the battery coil limit line, the growth-time text, any property-risk statement,
the quarter-barrel note and the heat-partition / spray sensitivity table. Further down, the
Levers and Gauge control sections carry the warning "OPEN ROLL GAP ASSUMED ..."; when
the shape chain is not assessable the width section opens with "Strip-shape chain not
assessable: <reason>" and lists what is still evaluated; with supplied shape inputs it says
"Strip-shape chain from SUPPLIED shape inputs (not verified by the tool)" with the
provenance; an incoming ridge without a bite is marked "(proportional estimate, no bite)".

The gauge-trend section is headed "How the result changes with gauge", which asserts no
direction. Directly under the heading one sentence, generated from the `width.gauge_trend`
rows of the model stripe (first against last assessable pass, a ratio within 1/1.1-1.1
counting as roughly unchanged), states the direction of the in-mill onset and of the
after-release onset separately, says whether each changes on every pass or only overall and
whether the after-release values are reporting-threshold upper bounds, gives the verdict
(both falling toward the thin pass: "thinner is worse for this mechanism in the model"; both
rising: "thinner is less sensitive for this mechanism in the model"; otherwise mixed) and
names any pass that was not assessable and, after "Not credible (excluded from the
direction):", any pass whose extended-domain bite force lies outside the range reported for
battery-foil passes (the rows are taken thick to thin by exit gauge; a not-credible row is
also left out of the two charts). The gauge-trend text follows unchanged, then, when
the result has it, a paragraph "Bite-free thresholds." with `gauge_trend.bite_free_text`
(section 3.5). In the gauge-trend table a pass without a roll bite keeps its bite-free cells
(dead-band half-width, critical ridge height, and the trough-onset and roller-wrinkle columns
of both spans, which appear when the rows carry them); its bite-dependent cells read "no
roll-bite result", the first one with the rejection reason; an extended-domain row is labelled
"(bite NOT CREDIBLE: force xR outside the reported battery-foil range; excluded from the
direction)" or "(extended-domain bite: force inside the reported battery-foil range,
unvalidated)". In the sheet
demo: "... the in-mill onset stripe height falls from 3.61 µm to 2.44 µm (x0.68, overall, not
on every pass), and the after-release onset falls from 0.626 µm to ≤ 0.108 µm (x0.17, on every
pass; reporting-threshold upper bounds); thinner is worse for this mechanism in the model." In
the foil demo: "... to F2 0.030->0.018 mm (plant pass 2, final)): the in-mill onset stripe
height rises from 1.19 µm to 17.5 µm (x15, on every pass), and the after-release onset rises
from ≤ 0.046 µm to ≤ 0.594 µm (x13, on every pass; reporting-threshold upper bounds); thinner
is less sensitive for this mechanism in the model. Not credible (excluded from the
direction): ALT2 0.025->0.012 mm (thinnest product, alternative final pass) (extended-domain
bite force 6.19 kN/mm, x2.7 the nearer end of the 0.9-2.3 kN/mm reported for battery-foil
passes)." (section 3.5). When the time simulation fails (a very stiff bite can exceed its
step limit) its section shows the failed state with the reason.

**Key model numbers show the values actually used.** The rows "mean flow stress used" and
"friction coefficient used" give the value every section used; when it differs from the
supplied one (computed flow stress, or computed friction with
`tribology.use_computed_friction`) the supplied value follows in brackets, as in the demo:
"2.826e+08 Pa (computed; supplied 2.7e+08 Pa)". The "bite source" row reads
`experimental_mattress` for a mattress bite, otherwise the bite's own source
(`derived_slab_hitchcock` in the lengthwise demo; `experimental_mattress` in the foil
demo). In the result JSON a mattress bite's own `source` field reads `supplied` (for example
`chatter.critical_speed.bite_source` and the gauge-trend `bite_source` of the foil case pass);
the `bite_model` fields (`experimental_mattress`) are the ones to read.

**Reading in-mill against after-release.** Every band state comes in pairs, written in plain
words in the tables. *In the mill*: "hidden under mill tension" (`LATENT_UNDER_TENSION`: flat,
a stress stripe a shapemeter can see) or "buckled in the mill" (`MANIFEST_BUCKLE`; "(feedback
saturated)" is added when the saturation step of 6.2 applied). *After tension release*:
"visible after tension release" (`MANIFEST_AFTER_TENSION_RELEASE`) or "flat after tension
release" (`FLAT_AFTER_TENSION_RELEASE`), from the local mode. A band hidden in the mill and
visible after release is a band that appears on the coil, at the slitter or on the table;
compare it with the observation `visible_only_after_tension_release`. Buckling utilisation is
printed only below 1 ("≥ 1" otherwise), because once a band buckles the saturation inflates
the number. The reported flatness level is the one with the exit-tension feedback; the rigid
and compliance-only levels are bounds for comparison, not predictions. When a bound's
thickness change would reach the exit gauge (a roll bump times the number of striped rolls of
at least the gauge for the rigid bound; a very soft strip for the compliance-only level) that
bound is reported as not defined (state `RIGID_BOUND_NOT_DEFINED` or
`COMPLIANCE_ONLY_LEVEL_NOT_DEFINED`, its numbers null, a reason, the flag
`RIGID_BOUND_NOT_DEFINED_BUMP_REACHES_GAUGE` or `COMPLIANCE_ONLY_LEVEL_NOT_DEFINED_CHANGE_REACHES_GAUGE`),
its curve is left out of the chart with a note, the gauge-trend text says "rigid bound not
defined on ...", and the level with the feedback, the states, the onsets and the scores are
unchanged. Onset heights limited
by the reporting threshold are printed as "≤ ... (limited)" and are upper bounds. The global
(whole-sheet) released mode is printed as an indicator only, not charted, and is not a band
prediction (7.2).

## 13. Verification evidence

The tests check that the code implements its equations and that the screening logic recovers
causes planted from the same models. They say nothing about whether the models describe a
real mill.

| module / test file | what is checked |
|---|---|
| `chatter.py` / `tests/test_chatter.py` | eigenvalue solver (diagonal, rotation, companion, defective cases); single-DOF critical speed and onset frequency with and without bite damping against the Routh-Hurwitz closed form; closed-form undamped modes; bite-derived force against the independent contact solver; sensitivity signs; time trace against eigenvalues; static and resonant frequency-response limits |
| `band_signatures.py` / `tests/test_band_signatures.py` | pitch doubling with speed; exponent classification and the < 5 % speed-spread guard; bearing-order identities; catalogue pitches and resonance round trip; AA5182 bending window; spray coverage of uniform, non-overlapping and blocked headers; free thermal growth rising with thinner gauge |
| `roll_thermal.py` / `tests/test_roll_thermal.py` | steady uniform `T = Tc + q/h` at every radius; lumped-limit exponential approach and axial decay length `sqrt(k_z*R/(2h))`; pure radial transient against the Bessel series; long transient reaching steady state; energy conservation to round-off; grid and time-step convergence; blocked-nozzle stripe position and size; zone-off-then-on growth law `2*alpha*dh*(Ts-Tc)/(rho*c)` in the resolved and lumped models, faster surface temperature and faster decay in the resolved model (`test_zone_off_then_on_grows_then_decays_and_skin_effects`); healthy header weight averages to 1; expansion constraints differ by `1 + nu`; difference-profile stripe detection |
| `strip_shape.py` / `tests/test_strip_shape.py` | zero exit-tension force sensitivity reproduces the compliance-only transfer and I-units exactly and a tiny positive value is continuous with it, a negative value is rejected (`test_zero_sensitivity_is_the_compliance_only_limit`); compliance and transfer check values; sinusoid as eigenfunction; feedback-off numbers unchanged; `Q_eff` formula; gauge-independent feedback limit (`test_gauge_independent_limit`); mean component keeps `Q`; worked example latent with feedback; saturation formula; 3 um stripe states at three gauges; Rayleigh limits (uniform compression, embedded zone); released local / global modes and the top-hat edge-spike limit; heredity and Shohet-Townsend check values; coil-ridge formula, yield onset and thin-gauge scaling; trough and wrinkle check values and scalings; spacing and position matching |
| `bite_tribology.py` / `tests/test_bite_tribology.py` | viscosity `beta` from the kerosene data points; film check case (62.8 nm, film ratio 0.209, within 5 % of the quoted 65 nm); film linear in speed and viscosity; closure limits and slope; friction falling monotonically with speed; pass heating check (49.35 K) and energy closure; Voce mean against quadrature; literature fits carry the warning |
| `mill_dynamics.py` / `tests/test_mill_dynamics.py` | static run-out and stroke transfer; full compensation prints run-out through; amplification rising with `alpha`; entry-thickness limit; mass-flow limit with tension coupling; `alpha = 0` reproduces `chatter.py`; first-order loop interaction reported and removed by roll-off; neutral mode at `alpha = 1`; hardness sensitivity and static limit; coil-synchronous frequencies; three-mass torsional benchmark; reel inertia; roll-speed DC limit; speed-change gauge shift |
| `foil_bite.py` / `tests/test_foil_bite.py` | rigid limit reproduces the slab force, slip and torque within 1e-3; sheet case conventional and of the same order as Hitchcock; foundation modulus is the fixed point of the contact length; end-zone equilibrium and smooth exit junction; work identity and grid convergence; Hitchcock-rejected pass solves; foil regime with shear within Coulomb; rejection of the high-friction foil case, the limiting gauge and a sticking exit; force trends; sensitivity signs match Hitchcock |
| `band_diagnosis.py` / `tests/test_band_diagnosis.py` | planted third-octave chatter, bearing order, backup-roll mark, yield-point bending and blocked-nozzle band lead; healthy header not a band risk; missing observations never contradict; scoring, standings and the leading rule of 6.4; graceful bite failure; supplied bite; lever directions computed; zero-tension lever not assessable; rejected damping variant is a row; strict validation; determinism; report escaping; v1 report unchanged; CLI; the three scenario files load and the two v1 demos lead; review fixes (`ReviewFindingTests`): the coil strip map uses the matching coil (`test_coil_strip_map_uses_the_matching_coil`), the spindle candidate is matched without drive geometry (`test_spindle_candidate_matched_without_drive_geometry`) |
| `band_width.py` / `tests/test_band_lengthwise.py` | planted truth for each of the nine lengthwise hypotheses; three shape levels with the feedback always on; healthy header gives no stripes; gauge trend (buckling stress and dead band fall, after-release onset carries the trend, in-mill onset falls less); tension-release rule table; spacing beyond 8 pitches not comparable; any non-longitudinal orientation contradicts every lengthwise hypothesis; lengthwise demo leads with `nozzle_thermal_stripe` at coarse settings; event attribution (`EventAttributionTests`): a later event on the same nozzle is not attributed to the earlier one (`test_later_event_on_same_nozzle_not_attributed_to_earlier`), a short event's peak profile is the snapshot at the measured peak (`test_short_event_peak_profile_is_the_measured_peak`), separated nozzles are monitored per stripe (`test_separated_nozzles_monitored_per_stripe`) |
| `band_process.py`, report / `tests/test_band_v2_sections.py` | computed values replace supplied ones only when flagged; speed-consistent critical speed; gauge-control amplification; drive and incoming sections; `auto` falls back to the mattress model; missing sections not supplied and v1 unchanged; v2 validation; determinism, report and CLI; report section order and escaping; key numbers show the values actually used (`test_key_numbers_show_the_values_actually_used`); the engine's central-difference sensitivities equal the `mill_dynamics` ones for a Hitchcock bite (`test_hitchcock_sensitivities_unchanged_by_engine_central_difference`); review fixes (`ReviewFindingTests`): a schedule row labelled like the case pass keeps its computed flow stress (`test_schedule_row_labelled_case_pass_keeps_operating_flow_stress`), mattress-bite sensitivities use the mattress model (`test_mattress_bite_sensitivities_use_the_mattress_model`); speed margin beyond the 0.05-60 m/s scan (`SpeedMarginScanRangeTests`): the reviewer's case (supplied bite, damping 0.21, 100 m/s, scan `STABLE_OVER_SCANNED_RANGE`, operating point unstable) supports strongly with the basis named and the chatter score 5 instead of 0; 10 m/s with no crossing still contradicts as before; zero slip in the pitch kinematics only (`KinematicSlipOnlyTests`: a supplied slip of 0.6 gives a not-assessable screen showing 0.6 and no skidding support; a slip of -0.01 still skids); coverage band-risk stripes matched as intervals (`CoverageIntervalMatchTests`: the reviewer's 0.065 m band in the 0.06-0.14 m gap supports and agrees with the screen, a band 0.045 m from every interval contradicts, modelled point sources still match by centre); 100 m/s stable at the operating point (damping 0.6) contradicts with the new wording; supplied `shape_inputs` with a zero exit-tension force sensitivity (`ZeroFeedbackSensitivityTests`): the steady shape and the case-pass gauge-trend row are assessed, feedback-level numbers equal the compliance-only ones, no nan / inf, a negative value is rejected at validation |
| foil phase (`band_diagnosis.py`, `band_width.py`, `band_report.py`) / `tests/test_band_foil.py` | **width section without a bite** (`NoBiteWidthTests`, a 60 -> 30 um pass at friction 0.05 that both bite models reject as sticking): troughs, coil ridge (proportional estimate, ratio 0.5), positions and thermal stripes present, shape parts individually not assessable with the bite error, flag set (`test_width_section_runs_without_a_bite`); model-based and not-assessable items never contradict (`test_missing_model_parts_never_contradict`); without bite heat the thermal parts are not assessable and the rest runs (`test_without_bite_heat_thermal_not_assessable_rest_runs`); supplied shape inputs take precedence for the case pass, flag and report note, provenance escaped (`test_shape_inputs_supplied`); shape-input validation (`test_shape_inputs_validation`); `foil_regime` block, closed-gap flag, `BELOW_EVERY_REPORTED_ONSET`, wrinkle onset `1e5*40e6/70e9` (`test_foil_regime_block_without_bite`); determinism, foil box, no nan/inf in the report (`test_determinism_and_report`). **Rules** (`FoilRulesTests`): every `foil_tension_lines` branch including the gate (`test_tension_lines_rules`); the nozzle, roll-surface (backup-roll downgrade to weak), trough and heat-streak extensions and the film-ratio gate (`test_extended_rules`); foil measurement lines only below 100 um (`test_next_measurements_for_foil`). **Planted truth**: regular 10 mm lines on 50 -> 25 um foil lead with `foil_tension_lines` (`test_tension_lines_lead`); orientation plus exit gauge, or plus film ratio, alone never lead (`test_orientation_and_gauge_alone_do_not_lead`). **Case-pass identity, zone-duration fallback, supplied-bite tables, sensitivity-mix flag** (`CasePassIdentityTests`, `ZoneDurationFallbackTests`, `SuppliedBiteGaugeTrendTests`, `SuppliedBiteScheduleTablesTests`, `SensitivityMixFlagTests`). **Torsional strip map**: 10 Hz mode, predicted pitch 1.0 m at 10 m/s, no foil block at sheet gauge (`test_torsional_strip_map_pitch`). **Schema**: v1 and earlier v2 files still load, a v1 case may not carry foil fields (`test_v1_and_existing_v2_files_still_load`). **Foil demo** (`FoilDemoTests`, coarse numerics, the plant's passes and the alternative route, no AGC or drive): the route in the file (S1-S3 assumed stock route, F1 50 -> 30 um = case pass, F2 to 18 um, ALT1 50 -> 25 um and ALT2 25 -> 12 um at 52 %, assumed gauges labelled, every other pass at or below 50 %, speeds inside the published spans, `material.product`), leads with `nozzle_thermal_stripe`, zone hypothesis consistent, mattress bite inside the reported load range, wrinkle comparison, latent in the mill and manifest after release, open-gap note, no floor flag, mattress bites on F2, ALT1 and ALT2 with their extended-domain flags, `extended_bite_domain` listing 18 and 12 um with the credibility marks (ALT2 ratio above 2, "NOT CREDIBLE" in the text), no case-pass mark, the product check (alloy `1235`, final passes F2 and ALT2, nothing outside the published range on the case and final passes, nearest published passes present), the extended-domain limitation, single-sheet statement, foil box before the leading hypotheses, "Extended roll-bite domain" and "Product check" in the report (`test_foil_demo_leads_with_planted_cause`); the **direction of the foil gauge trend** (`test_foil_gauge_trend_direction_runs_against_thinner_is_worse`): seven rows, ALT2 marked not credible with ratio above 2, the credible rows ordered by exit gauge S1, S2, S3, F1, ALT1, F2, along which the in-mill onset and rigid bound rise and linear-feedback I-units fall, the exit-span bite-free thresholds fall on every row, the text names ALT2 after "Not credible (excluded from the trend):" and spans 0.135 -> 0.018 mm, and the report's direction sentence ends at F2, says "thinner is less sensitive for this mechanism in the model", names ALT2 as not credible and marks its table row. **Final pass doubled or not** (`FinalPassDoubledTests`): absent or null keeps the question, `false` records single-sheet with the faces implication and no flag, `true` adds `DOUBLED_FINAL_PASS_NOT_MODELLED`, non-boolean values rejected, ignored at sheet gauge, the demo carries `false`. The direction test also pins the **bite-free values**: dead band, ridge height, trough onset and roller-wrinkle thresholds of both spans on every row, and the bite-free sentence ("falls on every pass" four times; the two entry-span quantities are not monotonic across the two routes). The **product question** is worded from the case ("The thinnest pass in this case exits at 18 um" or "... 30 um, which fits ..."; no "16-18"; `FinalPassDoubledTests`, `test_foil_regime_block_without_bite`); a sheet schedule with every pass assessable gets no span-threshold keys and no bite-free sentence (`test_case_pass_row_keeps_the_supplied_bite`). **Rules** (`test_tension_lines_rules`) also pin the stage-B tension-line weights: regular 5-20 mm strong, 25 mm weak, 80 mm a weak contradiction, irregular weak; exit gauge 12 um moderate, 25 um weak, 45 and 80 um neutral, 210 um a contradiction. **Not pinned by a test:** the forward-slip and pass-heating values of the mattress bite and the friction at which the mattress model rejects |
| product survey (`band_survey.py`) / `tests/test_band_survey.py` | the survey computed once: every catalogue product appears, with its catalogue values (sources, read status) and assumptions, the as-rolled flow stress assumed for O temper (`test_every_catalogue_product_appears`); on the foil mill at equal flow stress a thinner product has a lower critical ridge height, trough onset and roller-wrinkle threshold, and the three bite-free rankings correlate with thinner gauge above 0.9 (`test_thinner_product_lower_ridge_and_trough_thresholds`); doubled products have no bite and keep their per-sheet thresholds (`test_doubled_products_have_no_bite`); credibility marks equal the engine's (`_bite_credibility`), the load range applied to battery collector foil only, no bite-dependent ranking contains a not-credible row, ranked plus excluded rows cover every product (`test_credibility_marks_consistent_with_the_engine`); one row recomputed is identical, and the committed result and report equal a fresh run (`test_determinism_and_committed_artifacts`); the report renders, escapes text and has no nan / inf (`test_report_renders_escapes_and_is_finite`); on the user's own mill (`UserMillSurveyTests`, three products): `--products` restricts and keeps catalogue numbers, unknown ids list the valid ones; a different mill (roll radius 0.11 m, housing 9e9 N/m, 2 m spans) changes the force per width, the strip-to-mill ratio and the trough onset while the catalogue provenance stays; overrides are applied and marked user-supplied, the replaced provenance dropped, and a pass too narrow for the bite model is a row with the reason; an invalid mill file and invalid override keys or values give clear errors; a starter case written with `--write-cases` loads and diagnoses |
| packaging / `tests/test_band_products.py` | the packaged default survey mills equal the machine sections of the two demo scenarios (skipped when `scenarios/` is absent); a copy of the package run with `python -I` outside the checkout surveys a foil and a sheet product and renders the report, and `band_products --list` runs, with no `scenarios` directory (the code before the fix raised `FileNotFoundError` there) |
| robustness / `tests/test_band_robustness.py` | the reviewer's duplicate positions on the lengthwise demo case (`[0.6, 0.6, 0.7]`, which raised `gaps_m[0] must be > 0`): returns, flag set, merged list `[0.6, 0.7]` used and recorded, nozzle spacing evidence on the 0.1 m gap; the merge rule; a planted `ValueError` in one lengthwise and one transverse hypothesis leaves the others intact and shows the escaped reason in the result and the report; a sweep of accepted degenerate observations on a small v1 and a small v2 case (duplicate, identical, single, unsorted, edge and out-of-strip positions; tiny spacing and spacing at the 10 m limit; band width larger than the strip; duplicate pitch observations, two pitches at one speed, a pitch larger than a coil circumference; a huge intermittent duration; duplicated and barrel-end blocked nozzles in the coolant screen and the width model; all observations null, every boolean true, every boolean false): `diagnose` returns and the report renders; the inputs rejected at validation are rejected with their message. Also the coil single-source, trough-spacing and perturbed-bite-model tests, moved here from `tests/test_band_v2_sections.py` |
| extended domain, product check, credibility / `tests/test_band_extended_domain.py` | **extended domain** (`CollectorFoilExtendedDomainTests`, 30 -> 17 um case pass): `bite_model: "hitchcock"` keeps its 20 um floor (`test_hitchcock_only_keeps_its_20_um_floor`); the mattress bite, its extended-domain flags and limitation (`test_extended_bite_flags_and_limitations`); tension lines lead, no model contradiction (`test_tension_lines_lead_and_no_model_contradiction`); report renders (`test_report_renders`). **Below the 8 um floor** (`BelowBiteFloorTests`, 12 -> 7 um): loads and diagnoses, floor and closed-gap flags, chatter and levers not assessable, shape chain not assessable, bite-free parts present (`test_loads_diagnoses_and_flags`, `test_report_renders`). **Product check** (`ProductCheckTests`): unknown ids, non-string and v1 use rejected with the list of ids (`test_validation`); `NOT_SUPPLIED` with the ids at foil gauge, absent at sheet gauge (`test_not_supplied_at_foil_gauge_absent_at_sheet_gauge`); a 36 -> 30 um pass reads `BELOW_PUBLISHED_RANGE` for the per-pass reduction, with the case and final-pass flags, and every score equals the run without a product (`test_findings_flags_and_no_score_change`). **Credibility gate** (`CredibilityGateTests`, the demo's final-pass material on the foil mill): a 25 -> 12 um case pass gets no model-based support or contradiction from the bite-dependent items, the gated items keep their verdict without the gate, scores are the tally of the gated evidence and the leading rule is unchanged; a 30 -> 18 um case pass (force inside the range) keeps its model evidence. **Coil, trough spacing, perturbed bites** (now in `tests/test_band_robustness.py`): one coil for all pitches (`CoilSingleSourceTests`: the reviewer's pitches 1 m at 2 m/s and 1.4 m at 20 m/s on coils of 1 m and 1.4 m pitch no longer give two exact matches; the coil hypothesis contradicts weakly and does not lead; two pitches on one coil still support; a single pitch as before); trough spacing (`TroughSpacingEstablishedTests`: one gap weak and never contradicting, irregular gaps weak, regular or stated spacing strong, a stated spacing outside a factor 4 still contradicts); perturbed bites (`PerturbedBiteModelTests`: an `auto` case with a mattress operating bite has every lever row equal to a direct mattress derivation; a Hitchcock operating bite reports the friction x1.3 variant Hitchcock rejects as a rejected row). **Onset search** (`OnsetSearchDomainTests`): the reviewer's soft-strip case (1e9 Pa, 9 um bump) no longer reports the old 4.28 um in-mill onset: the reported onset is manifest with feedback and the scale just below is not; a stubbed feedback calculation that leaves its domain before buckling gives the domain-limit outcome with its height, one that buckles first gives the onset, one that stays latent gives not-reached; a sheet-gauge case gives exactly the onset of the old search. **Undefined bound levels** (`UndefinedBoundLevelTests`, the reviewer's 8 um pass, one striped roll, 9 um bump, shape inputs 1e12 Pa / 1 mm / 0.01 m): `shape_levels` keeps both compliant levels with the rigid bound not defined and its reason, a very soft strip (1e9 Pa) keeps the feedback level with the compliance-only level not defined, a normal bump reports the rigid bound exactly as the direct calculation; through `diagnose` the steady shape and the gauge-trend row are assessed, the trend text names the pass without a rigid bound, the report omits the rigid curve with a note and has no nan / inf. **Large forward slip** (`LargeForwardSlipTests`, the reviewer's 30 -> 12 um pass on a 0.14 m roll): the mattress slip is at least 0.5, `diagnose` returns, both slip flags are set, the signatures use slip 0, the schedule row keeps its slip; the forward-slip screen is not assessable with the actual slip, the skid evidence does not support. **Case-pass credibility** (`CaseBiteCredibilityTests`): a 25 -> 12 um case pass with `auto` gets `FORCE_OUTSIDE_REPORTED_RANGE` with ratio above 2, the top flag, the limitation, the gated items (`model not credible`, "NOT CREDIBLE BASIS", `NEUTRAL`) and only bite-free model items left with basis `model`, a failed time simulation instead of an exception, and a report (`test_not_credible_case_pass`); a 30 -> 18 um case pass is marked inside the range with no flag (`test_credible_case_pass_has_no_mark`) |
| `band_products.py` / `tests/test_band_products.py` | catalogue integrity (unique ids, sources with URLs and valid read status, every fact sourced and its status never upgraded, ordered ranges with units, products validate, JSON round trip, battery depth); published reductions of the battery, pouch, packaging, litho and heat-exchanger schedules; `check_pass` on 50 -> 30 um, the 30 -> 18 um final pass, a 70 % pass, mode checks, flow-stress, alloy and fallbacks, errors and JSON; nearest published passes; `docs/thin-gauge-products.md` matches the generator and is complete; CLI |

`tests/test_band_diagnosis.py` also checks that twenty hypotheses are evaluated for every
case. Run, for example, `python -m unittest tests.test_band_lengthwise -v` or
`python -m unittest tests.test_band_foil -v`.

## 14. Limitations and open discrepancies

- **No plant validation.** Synthetic, uncalibrated stand, spans, bite, thermal and shape
  parameters; every demo's observations were generated from the model.
- **Evidence rules are engineering judgement.** Weights, thresholds (pitch exponent bands,
  0.005 slip, quarter-pitch position tolerance, 2 I-unit reporting threshold, 0.1 um stripe
  threshold, 0.3-3 x duration window, 15 % edge/centre band, 35 m/s resonance envelope) are
  analyst choices; the score is an ordinal tally.
- **Linear chatter model**: no limit cycle, mark severity or strip break; a forced response
  at an unstable operating point is formal only; lumped spans are unreliable near `c/(2L)`.
- **Bite-damping closure** is a heuristic; beta = 0 results are always shown.
- **Placeholder friction closure**: absolute friction values are placeholders; only the
  slope with speed is used.
- **Alloy and temper selection is a literature synthesis.** The grade table by gauge band
  and its proposals come from published standards, producer pages, patents and broker reports
  with the stated evidence ratings (strong to vendor-level); no source gives a hard
  gauge-to-alloy rule; several standard tables (GB/T 33143-2022 Table 9, GB/T 22648-2023) were
  read from mirrors or producer pages reproducing them; finished tensile strength is used as an
  indicator of the rolling flow stress and the proof strength is assumed from a ratio where not
  published. The plant must confirm or correct the proposal.
- **Supplied heat partition and spray coefficients.** Both are inputs. The only measured
  foil-mill partition puts 0.11-0.33 of the heat into the strip [PT-T16], read as an abstract
  only and a net balance (not necessarily the split inside the bite); no sheet-gauge value was
  found. For kerosene on a rotating work roll only a SIMULATED 2.5-4.3 kW/m2K was found
  [PT-T18, excerpt of a garbled mirror]; a plate test gives about 5-13 kW/m2K (computed,
  [PT-T19]). Stripe heights scale with the roll heat share and fall with the spray
  coefficient; `width.thermal_sensitivity` shows how far (section 3.12).
- **No roll-wear model and no temperature-to-surface-finish model.** What the research says
  about temperature, roll wear, roll coating, fines and dyne is carried as literature
  statements in the catalogue and in `thermal_check`, not computed. No property change after
  rolling (the battery-foil elongation decay above 90 C is a literature statement).
- **Thermal model against the plant-identified response**: a first-order flatness response
  of about 20 s was identified on a plant (Dohmae & Okamura 2012). In the model a short local
  event rises fast (the battery demo's valve event reaches half its peak in 9.25 s; the computed
  axial decay time of a 52 mm stripe is about 23 s), while a steady stripe needs minutes to
  build (116 s to 50 %, 551 s to 90 % in the battery demo; radial time constant 4-7 min
  computed for a 260 mm roll [PT-T25]) and the lengthwise demo's events fade over about a
  minute (half-decay 57 s and 84 s). The 20 s is of the order of the local time scale, not of
  the steady build-up; plant time constants were not found (only an abstract, [PT-T26]).
  Partly open.
- **The roll thermal model** is circumferentially averaged, with top-hat footprints (the
  nozzle-pattern ripple is an artefact), adiabatic barrel ends, constant properties, per-station
  expansion with a source-dependent factor (1 or 1 + nu), and no coupling of roll temperature
  back into the bite heat.
- **The flatness chain is elastic and local**: half-space roll compliance, linear exit-tension
  feedback with an approximate band-wise saturation step (one scale factor, no iteration), no
  roll bending, no entry-tension redistribution, no post-buckling relief, a single assumed
  buckle mode (Rayleigh quotient, k = 4 [M]), stresses above yield indicative only.
- **After-release whole-sheet mode** is an upper-bound indicator, not a band prediction; the
  local mode's width limit (2 x half-peak width) is an analyst choice.
- **Sharp-edged stripes** can lock the local released width onto an edge spike and report
  flat where a smooth stripe of the same height buckles.
- **After-release onsets** limited by the reporting threshold are upper bounds.
- **Gauge trend** carries one stripe shape through all passes; it does not re-solve the roll
  temperature for each pass.
- **Mattress bite model is experimental**: no benchmark with known inputs, no elastic strip
  zones, Hertz-calibrated foundation modulus; foil-regime numbers are order of magnitude only.
- **Supplied bite with derived force sensitivities**: with `bite_response_override` the
  gauge-control speed-change shift and the incoming-variation hardness response take their
  force sensitivities from perturbed bites of the derived (slab or mattress) model while the
  strip modulus is the supplied one, so the two may be inconsistent (flag
  `FORCE_SENSITIVITY_DERIVED_NOT_FROM_SUPPLIED_BITE` on both sections and in the top-level flags).
- **Short-lived bands close together in width**: an event's metrics stop at the start of the
  next event in the same neighbourhood (7.4); what lies beyond is only a lower bound.
- **Coil ridge compaction factor** is an analyst choice (default 0.5).
- **Mill dynamics**: first-order cylinder loop (the AGC-chatter result depends on the loop
  roll-off, 9.70 against 13.62 m/s in the demo); static formulas hold tension constant.
- **Hardening**: literature fits are tensile fits, over-predicting beyond `eps` about 0.3; demo
  Voce parameters are synthetic; rate sensitivity zero.
- **Tribology**: inlet-film exponent disputed between sources; no starvation, film collapse,
  plate-out or roughness evolution.

At battery-foil gauge, in addition (each checked against the code and
`artifacts/band_diagnosis/battery-foil-demo.result.json`):

- **The gauge trend of the cooling-stripe mechanism runs opposite to the plant observation.**
  In the foil demo the in-mill onset of a given stripe rises toward the thin pass (1.19 ->
  1.71 -> 2.66 -> 6.83 -> 11.0 -> 17.5 um from 135 to 18 um) and its linear-feedback I-units
  fall (42.3 -> 30.6 -> 20.4 -> 8.05 -> 4.98 -> 3.23); the model does not reproduce "worse at
  thinner gauge" through stripes buckling in the mill (section 3.5). The 18 um point comes
  from an unvalidated extended-domain bite; the 12 um pass is not credible and is left out.
  The rule weights for `worse_at_thinner_gauge` are inherited from sheet gauge: "true" still
  supports `nozzle_thermal_stripe` and `cooling_zone_switching_transient` weakly.
- **After-release onsets are set by the reporting threshold.** At the foil case pass they are
  about 0.2 um of stripe (0.239 um steady, 0.206 um for the event), equal to the 2 I-unit
  reporting onset, so nearly any reportable stripe reads "visible after tension release", and
  a 20 s valve closure shows a band after release for 311 s. The whole-sheet after-release
  indicator reads `GLOBAL_BUCKLE_AFTER_RELEASE` for bands of 25.1 and 21 I-units.
- **"Worse at lower tension" is not specific to tension lines.** A latent thermal stripe's
  in-mill onset also falls with tension: 6.83 um at 40 MPa in the result; about 1.6 um at
  8 MPa according to the demo's scenario notes (a probe with the bite re-derived at 8 MPa; not
  in the result file). The demo therefore leaves the observation `null`.
- **The experimental mattress bite at foil gauge**: forward slip 0.190 at the case pass,
  flagged implausible; it enters the slip dissipation and so inflates the friction power
  (47.1 kW/m against 40.3 kW/m plastic) and the pass-heating exit temperature (333.4 K at
  strip share 0.22) [D];
  force per width scales steeply with the supplied friction (section 3.3); no closed-gap load
  path in either bite model.
- **No roll-kissing model.** The `foil_regime` block appears below 100 um exit gauge, while
  one source puts the onset of closed-gap rolling at up to 200 um; the lever table and the
  gauge-control section are open-gap reasoning only.
- **Chatter at foil gauge is flagged unreliable**: in the foil demo the onset frequency
  without bite damping (2133 Hz) lies above the span-wave limit (849 Hz).
- **Trough spacing from few bands.** A trough spacing now needs a stated `band_spacing_m` or
  at least two regular gaps; one gap, or irregular gaps, between bands that may have
  different causes give at most a weak support and never a contradiction (review fix). Two
  or more equal gaps between bands of different causes would still count as a spacing.
- **Without a bite the ridge transfer is an estimate**: the proportional limit
  `dh = (h/H)*dH` is used for the exit ridge height (a no-bite estimate, not a bound); its
  coil result supports only weakly.
- **Domain limits**: below 8 um exit gauge or above 65 % reduction no bite at all; doubled
  passes are not modelled (`material.final_pass_doubled` true flags it; the plant rolls
  single-sheet).
- **Extended-domain bites are unvalidated.** Between 8 and 20 um exit gauge and between 50 and
  65 % reduction the mattress model gives numbers only because its solution stays converged
  and continuous in probes; no source validates it there, and the closed-gap load path is
  missing as everywhere in foil. The plant's 18 um final pass (force inside the range reported
  for battery-foil passes) is usable as order of magnitude only; the 12 um pass of the demo
  (force 2.7 times the top of that range) is not credible at all.
- **The credibility mark rests on one reported range.** It compares a bite below 20 um with the
  0.9-2.3 kN/mm reported for battery-foil passes [V S3, S4]; that range comes from trade
  sources, applies to battery-foil passes only, and a force inside it does not make the bite
  right. A not-credible case pass flags itself, and its bite-dependent model evidence is
  scored `NEUTRAL` (basis `model not credible`), so the ranking then rests on the
  observations, the inputs and the bite-free model items; a credible extended-domain bite
  (inside the range) is not gated, although it is still unvalidated.
- **The product survey is one synthetic mill per gauge class** (section 3.10): the same
  friction, tension fractions and mill for every product, many assumed flow stresses (18 of 24
  rows), doubled passes without a bite; it ranks model sensitivities, not plant defect rates.
- **Product ranges are a literature survey.** The product catalogue and the product check
  (`docs/thin-gauge-products.md`) collect published values, most read as excerpts, patents
  or vendor and trade pages, not full texts; nothing in it was measured on a plant, the
  sources disagree (for example on final-pass speed), and a pass inside a published span is
  not thereby a good pass. The check is evidence-neutral and changes no score.
- **The plant facts are few.** 50 um input, two single-sheet passes, usual final 17-19 um, down
  to 12 um. The intermediate gauges (30 um, 25 um), the alloy (1235-like) and the temper (H18)
  of the demo are assumptions from the nearest published passes and the standard grade.
- **Per-pass span thresholds only where they matter**: the per-pass trough onset and
  roller-wrinkle thresholds of both spans and the bite-free trend sentence are added to
  `width.gauge_trend` only for a foil-regime case or a schedule with a pass without a roll
  bite, so that sheet results without such passes keep their exact content; a sheet case
  sees the roller-wrinkle threshold only for the case pass's spans (`width.troughs`).
- **Tension lines have no physical model**; `foil_tension_lines` is a rule set with analyst
  weights [D] on a published description [BF-S21, excerpt of a trade report of a producer
  talk; V S27, S28].
- **Demo heat partition**: the foil demo uses the middle (0.22) of the only measured
  foil-mill strip share, 0.11-0.33 [PT-T16, abstract only, net balance], with 0.84 and the
  measured ends kept as sensitivity rows; the sheet-gauge lengthwise demo keeps 0.84 because no
  published sheet-gauge partition was found.
- **Foil facts** come from a research pass over trade, association, patent and journal
  sources (section 15), some not peer-reviewed; product ranges given there without a source
  are tagged [M]. None is plant-validated.

## 15. Sources and disagreements

How each source was read is given in brackets, as the module docstrings record it.

Chatter and transverse marks: Tlusty, Chandra, Critchley & Paton (1982) CIRP Ann. 31:195
(abstract only); Yun, Wilson & Ehmann (1998) Int. J. Mach. Tools Manuf. (cited, not read); Hu,
Zhao & Ehmann (2006) Proc. IMechE B, doi:10.1243/09544054B06804 (as reproduced in Heidari &
Forouzan 2013, J. Adv. Res.); Kimura et al. (2003) ISIJ Int. 43:77; Niroomand et al. (2012)
ISIJ Int. 52:2245 and (2015) 55:637; Zeng, Zang & Gao (2016) Shock & Vib.,
doi:10.1155/2016/2347386; Innoval Technology (Farley) mill-vibration and chatter blogs; Krueger,
Richard & Peretic (SMS group) AISTech 2019; Kim et al. (2012) ISIJ Int. 52:2042; Randall &
Antoni (2011) MSSP, doi:10.1016/j.ymssp.2010.07.017; Zhang et al. (2016) IET J. Eng.; Heidari,
Forouzan & Akbarzadeh (2014) ISIJ Int. 54:2349; Aluminum Association (2002) QCA-1; Choi, Jin &
Kang (1998) Scripta Mater. 38:887; de Codes et al. (2011) Metall. Mater. Trans. A 42; Reynolds US
4,081,294; Li et al. (2020); Mucsi (2018) Eng. Fail. Anal. 83; Komori (1996) J. Mater.
Process. Technol. 60:377; Szucs et al. (2020); Alcoa US 5,508,119 citing Schey; Reid & Schey
(1978) ASLE Trans. 21(3); Sutcliffe (2002); Lloyd (Lechler, 2010); Tucker (Lechler, 2006).

Roll thermal: Yamaguchi et al. (2016) ISIJ Int., doi:10.2355/isijinternational.isijint-2016-173;
Li et al. (2024) Metals 14(2):166; Dohmae & Okamura (2012) Trans. SICE 48(4),
doi:10.9746/sicetr.48.193; Yin et al. (2003) (abstract only); Innoval roll-cooling blogs
(coolant unspecified).

Strip shape: Johnson, Contact Mechanics s13.2 (second-hand); Qu et al. (2025) ISIJ Int. 65(9),
doi:10.2355/isijinternational.isijint-2024-371; Li et al. (2022) Int. J. Adv. Manuf. Technol.,
doi:10.1007/s00170-022-08997-5; US 5,927,117; IHI Sheetflat; Vollmer (2019); QCA-1; Bailey;
Abdelkhalek et al. (2008); Lloyd (2010); Timoshenko plate buckling (from memory); Zambrano et
al. (2006); Hajduk & Bernardes (2009); Somers et al. (1984) (as attributed in later sources);
Lorin (fabricator quoting the Aluminum Association limit); Zhang et al. (2016) La Metallurgia
Italiana; Sun et al. (2016) IJSIMM; Melfo (2006) PhD thesis, Wollongong; Zhu et al. (2009);
Cerda & Mahadevan (2003) Phys. Rev. Lett. 90, 074302 (reconstructed); Panaitescu et al.,
arXiv:1906.10054; Good, Beisel & Yurtcu (2009), doi:10.15376/frc.2009.1.517; Jacques et al.
(2007) J. Mater. Process. Technol.; EAFA (2020); EN 12258-1.

Tribology and hardening: US 4,844,830; Petroyag data sheet; Sutcliffe & Montmitonnet (2001)
Rev. Metall.; Wilson & Walowit (1972) (as restated by Sutcliffe 2002 and Le & Sutcliffe; original
not read); Le & Sutcliffe (2000/2001); Yarita (1984); Ghosh & Hamrock (1985); Murch & Wilson (from
memory); Tabary, Sutcliffe et al. (1996) J. Tribol. 118:629 (abstract); Achenbach rolling basics;
ABB Review; Kazaoka et al. (2015); Kalpakjian (via secondary source); Batorfi et al. (2023);
Hirsch et al. (second-hand); Ryen et al. (2006) (abstract).

Mill dynamics: IJCA 9(2) AGC paper; Scheidl et al. (2016); Karl et al. (2011); Ichiryu, J. JHPS
26(6):778; ABB "Improvement of thickness tolerances"; J. Phys. Conf. Ser. 2419 (2022) 012027;
Gao et al.; Soler, Isermann & Feldmann (2008); Zhang et al. (2017) IJCA 10(6).

Thin-gauge bite: Fleck & Johnson (1987) Int. J. Mech. Sci. 29:507 (poor OCR copy only); MISG
report "A simple model for the cold rolling of metal foil"; Stone (from memory).

Battery foil (phase 3; labels as in the code's `FOIL_SOURCES`, read in a research pass for
this project): [S3] alfoilworld.com, battery-foil rolling procedure
(https://alfoilworld.com/knowledge/knowledge-a38e503a/?lang=zh) (passes, tensions, speeds,
load, doubling); [S4] alfoilworld.com, 1235D procedure
(https://alfoilworld.com/knowledge/1235d-1-8f6aaef7/?lang=zh) (passes, roughness, oil, H18
UTS); [S5] SMM / Shenhuo battery-foil quality note (https://news.smm.cn/news/102941219)
(tension lines, ridge marks, offline sag); [S8] Mysteel foil-rolling reference
(https://baike.mysteel.com/doc/view/45942.html) (closed gap 0.1-0.2 mm, roll sizes, online
against offline flatness); [S11] Sutcliffe & Montmitonnet (2001) Rev. Métall.
(https://minesparis-psl.hal.science/hal-00574224v1/document) (film ratio 1.76 -> 0.22, foil
case inputs); [S16] Publitec, "The engineering design of rolling mill"
(https://www.publiteconline.it/ael/the-engineering-design-of-rolling-mill/) (closed gap about
80 um); [S17] Jiangsu Huafeng foil flatness note (http://www.jiangsuhuafeng.com/case_show.aspx?id=51)
(closed gap below 50 um, online against offline flatness, roughness-driven bands); [S25] foil
defect compilation (https://www.renrendoc.com/paper/526943083.html) (hot spot, creasing, mill
lines); [S26] EAFA, Surface Characteristics of Aluminium Foil (2020) (rolling stripes, heat
stripes, grooves); [S27] CNFA foil rolling research note
(https://www.cnfa.net.cn/research/show-1521.aspx) (wrinkle rule of thumb, tension lines);
[S28] patent text on battery-foil tension lines (https://www.xjishu.com/zhuanli/23/202321734907.html).

Known disagreements:

- Effect of friction on chatter (Yarita: high friction worse; Chefneux: low friction worse;
  Kimura: an optimum band); this model gives "lower friction lowers the critical speed".
- Effect of tension on chatter (Heidari: little; Zeng, Zang & Gao: higher tension lowers the
  critical speed); this model gives a modest lowering with higher entry tension.
- Lumped span against a wave model near `c/(2L)` (Niroomand et al. 2015).
- Thermal expansion factor: 1 (Yamaguchi et al. 2016) against `2(1+nu)` (Li et al. 2024).
- Inlet-film exponent: `Y_ps` alone (Sutcliffe; Le & Sutcliffe) against the entry pressure
  (Yarita).
- Shohet-Townsend exponent: 1.86 (attributed to Somers et al.) against 2 (original).
- Foundation modulus coefficient: 1.18 quoted from memory in the specification against
  `3*pi/8` = 1.178 derived here (agree to the quoted precision).
- Onset of closed-gap rolling: 0.1-0.2 mm [S8] against below 100 um, about 80 um [S16],
  against below 50 um [S17]; the tool reports the range 50-200 um.
- Onset gauge of tension lines: below 15 um [S27] against below 30 um for battery foil [S28].
