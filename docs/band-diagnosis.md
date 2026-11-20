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
  thinner passes; it carries the flag `FORWARD_SLIP_LARGE_CONSTANT_FRICTION_NO_SLIP_ZONE_MODEL`
  (renamed in SPEC17 from `FORWARD_SLIP_IMPLAUSIBLY_LARGE_NO_ELASTIC_STRIP_ZONES`; threshold
  0.15 unchanged). Large forward slip is what a constant Coulomb friction model with a
  no-slip zone gives: one published model computes 5 % to 45 % on a 50 -> 25 um pass and
  describes such values as met in practice (model output) [BT-S3 EX]; mill trials show that
  constant friction over-estimates forward slip and that friction varying through the bite
  repairs it [BT-S5 AB]. Elastic strip zones are not the cause: they are negligible for
  reductions above 10 % [BT-S1 FT]. The slip enters the interface slip
  dissipation, so the pass heating is inflated [D]: at the case pass friction power 47.1 kW/m
  against 40.3 kW/m plastic power, strip exit temperature 333.4 K (+20.3 K) at the strip
  heat share 0.22 (`process.heating.operating`; 390.6 K at the former 0.84); F2, ALT1 and ALT2
  reach 339.2 K, 345.6 K and 346 K (`process.heating.schedule`), all below the 393.15 K limit
  supplied in the demo and below the published 80 C battery coil limit (section 3.12). Since
  SPEC17 the heat-streak rule supports only on an exit temperature above the supplied limit
  (a film ratio below 1 is normal mixed-regime operation, section 6.4), so the inflated
  temperature could raise that hypothesis on a case with a lower limit; in the demo it does
  not reach the limit.
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

**The third model: the reduced half-space bite** (opt-in, `model_options.bite_model:
"half_space"` or `"auto_half_space"`, section 10.3). The same passes, the same friction 0.03
[run, `python -m physicroll.benchmarks --bite-comparison` on the demo; pinned in
`tests/test_halfspace_bite_sensitivity.py`]:

| pass | Hitchcock | experimental mattress | reduced half-space | half-space zone structure |
|---|---|---|---|---|
| F1 50 -> 30 um (case pass) | rejected | 0.96 kN/mm, slip 0.190 | 1.37 kN/mm, slip 0.237 | `A F` (at the regime boundary) |
| F2 30 -> 18 um | rejected (below 20 um) | 1.54 kN/mm, slip 0.308 | 3.24 kN/mm, slip 0.367: NOT CREDIBLE | `A B E F` |
| ALT2 25 -> 12 um | rejected | 6.19 kN/mm, slip 0.422: NOT CREDIBLE | 10.13 kN/mm, slip 0.553: NOT CREDIBLE | `A B F` |

On the sheet-like passes S1-S3 the three models agree within 6 to 9 % in force. At foil gauge
the half-space loads are 43 % (30 um) to 111 % (18 um) above the mattress loads and its strip
stiffness 2.6 times higher; with friction 0.03 the 18 um and 12 um loads leave the reported
battery-foil range, and the existing credibility mark says so (`FORCE_OUTSIDE_REPORTED_RANGE`).
With a load exponent in friction of about 3 at these gauges, the 18 um pass would return into
the range at a friction of about 0.027 [computed, SPEC18 prototype]: friction is the larger
unknown, and the spread between the models measures what is not known. The half-space model
is not the default: its published reference value is itself not a defined number (section
10.3), and switching would move every foil force, stiffness, slip and heat.

Measured roll force, forward slip and torque of your own passes can narrow the friction:
section 8.5 identifies it from entered pass records with any of the three bite models, reports
which measurement carries the information at these gauges, and applies nothing.

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
The trough and roller-wrinkle thresholds come from isolated-span formulas: for aluminium
and copper foil below 25 um and wider than 0.6-1 m, wrinkles needed about 15 times the
predicted roller misalignment [SS-S55 EX], so at foil gauge these thresholds are
conservative screening values (key `wide_foil_note` on each span of `width.troughs` below
100 um, printed under the trough table; SPEC17 X12).

**A second band source: a friction or oil-film stripe** (section 7.8). The bite report argues
that a local friction difference at one width position grows as gauge falls. With the existing
models that holds for the load exponent in friction (0.64 at 135 um to 2.16 at 18 um in the
battery demo) and for the compliance-only level (55 to 566 I-units per 1 % friction), and not
with the exit-tension feedback (2.7 to 4.4 I-units per 1 %, no trend). So whether this source
explains "worse at thinner gauge" depends on the feedback, the least supported element of the
shape chain; the screen changes no score.

**A hot roll stripe at foil gauge: three parts, two signs** (SPEC19 package 2, section 7.11).
With `width_model.local_coupling` the battery-foil demo shows what the stripe of the weak
nozzle does besides growing the roll: roll growth +25.1 I-units (loose), the thinner oil film
-3.7 (tight; -7.5 with the inlet weight 1), the softer metal +0.57, the strip temperature +4.1
read while hot; mechanical net +21.9 (+18.2 with weight 1), loose either way. Twenty seconds
after zone 18-19 closes the parts are +18.0, -10.0 (-19.7), +1.5 and +11.0, and the net is
+9.5 at weight 0.5 but -0.2 (below the reporting threshold) at weight 1: in the first tens of
seconds the sign depends on an input nobody has measured. Every part rests on the exit-tension
feedback (compliance only the film part is -463 I-units against -3.7) and the film part on a
friction slope with no support in data. The terms are reported beside the band; they change no
score and no band state.

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

**Tension lines: no established model; one candidate pitch is reported** (SPEC17 G12, X16).
Entrained-air corrugation in winding has the same remedies and the same thin-gauge trend as
foil tension lines [SS-S53 EX, SS-S66 EX], so the shell-buckling wavelength of a wound lap or
of the strip on a roller is a candidate pitch: `2*pi*sqrt(R*t)/(12*(1 - nu^2))^(1/4)`, about
`3.47*sqrt(R*t)` for nu = 0.33 (quoted from memory in the shape report; re-derived in SPEC17
from the axisymmetric buckling of a thin cylindrical shell, `D*w'''' + N*w'' + (E*t/R^2)*w = 0`,
least `N` at `k^4 = 12*(1-nu^2)/(R^2*t^2)`; its critical stress is the roller-wrinkle value
the tool already uses). `foil_tension_lines` reports it per radius of the case (deflector
roll, coil inner and outer radius, exit coil) in `model_prediction.candidate_shell_buckling_
pitch`; in the battery demo (30 um) it gives 6.7 mm at the 0.125 m deflector roll, 7.4 mm and
14.7 mm at the coil radii, 12.8 mm at the exit coil. **It is a candidate, not evidence**: almost
any foil coil gives a pitch inside the published 5-20 mm, so a match proves nothing. What it
offers is a ruler test: measure the pitch at two coil radii and two gauges; this candidate
predicts a pitch proportional to sqrt(radius x gauge). No onset condition and no air-film model
(G9, G10); the rule set and its weights are unchanged.

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
| 4 | `tension_troughs_or_creases` | CONSISTENT | 4 (4) |
| 5 | `heat_streak_or_film_variation` | CONSISTENT | 3 (4; 4 before SPEC17) |
| 6 | `incoming_ridge_coil_buildup` | CONSISTENT | 1 (1) |
| 7 | `oil_carryover_drips_or_stain` | CONSISTENT | 1 (1) |
| 8 | `coil_or_mandrel_locked_marks` | NOT_ASSESSABLE | 0 (0) |
| 9 | `foil_tension_lines` | WEAKENED | 0 (-1) |
| 10-20 | `grinding_feed_marks`, `roll_surface_band` and the nine other transverse hypotheses | CONTRADICTED | -3 to -9 (unchanged) |

Both planted causes come first and second. The nozzle hypothesis matches the position
0.623 m and the zone hypothesis 0.988 m; the gap 0.365 m is 7 nozzle pitches. Also consistent:
the profile / flatness mismatch scores 5 from the orientation, the loose / buckle appearance
and "visible only after tension release"; the heat-streak hypothesis scores 3 from the
orientation, the continuity and the film ratio 0.38 (inside 0.3-3), less two weak
contradictions (positions repeat, does not track speed changes); the tribology regime item is
`NEUTRAL` since SPEC17 (score 4 before, film ratio 0.551 with the former inlet angle,
section 8.1); tension troughs score 4 from
the orientation, the continuity and the exit gauge below 50 um (weak, counted because the
continuity supports): the 365 mm gap lies at 2.27 x the entry-span and 3.03 x the exit-span
trough wavelength, outside the 0.5-2 band, so it gives no spacing support.
`foil_tension_lines` is weakened by the 365 mm spacing (C weak under the revised rule of
section 6.2, moderate before; hence 0 instead of -1) and the loose / buckle appearance (C weak),
and its gauge support is gated (section 6.1). `roll_surface_band` is contradicted strongly by
"positions do not change after a work-roll change". Adding the alternative route and the
product did not change any other score.

**Shapemeter** (`measurement.shapemeter`, section 7.6; 24 synthetic zones of 52 mm): the
loose band would show 24.49 of its 25.09 I-units in zone 9 (97.6 %), the tight edges almost all
of theirs; the event's two tight side bands would probably not show (1.83 of 3.51 I-units); the
nozzle-pattern ripple reads at most 0.53. No flatness controller is modelled.

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

**Fitting the spray coefficient to your roll.** With a roll surface temperature scan after a
stop or a measured thermal camber, `--calibrate-spray` fits the circumferential-mean spray
coefficient of this model for your mill (section 7.1); the value is entered by hand, and it is
not comparable with the published coefficients above, whose basis is not established.

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
1 % from a direct run). The share the interface model computes for the case pass, 0.338
(section 8.2), is shown beside these rows as `computed_strip_share`; it moves no stripe unless
`tribology.use_computed_heat_partition` is set):

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

**Basis of the spray coefficient (SPEC17 A5, X3).** The model applies
`spray_mean_htc_w_m2k` as a mean around the roll circumference (`roll_thermal.py`). The
published 2.5-4.3 kW/m2K [PT-T18, simulated; full text from a garbled mirror] is read by the
project's earlier note as a value inside the jet zone; PT-T18 has not been re-read, so whether
the two are on the same basis is not established. The spray finding of `thermal_check` keeps
its verdict word and carries `value_basis`, `published_basis` and
`basis_comparable: NOT_ESTABLISHED`, with the flag `SPRAY_COEFFICIENT_BASIS_NOT_ESTABLISHED`;
the report prints "The two are not on the same basis". Conversion [D, re-derived in SPEC17]: a
spray wetting an arc `phi` of the circumference with `h_fp` and leaving the rest at `h_bg` has
the mean `h_bg + (h_fp - h_bg)*phi/(2pi)`; the model writes `h_bg + spray_mean_htc`, so
`h_fp = h_bg + spray_mean_htc*2pi/phi`. With the optional `width_model.spray_wetted_arc_rad`
the finding also gives `footprint_equivalent_w_m2k` and its verdict against the same range.
For the battery-foil demo values (3400 and 50 W/m2K) a 60 degree arc would give 20450 W/m2K,
`ABOVE_PUBLISHED_RANGE` (pinned by `test_wetted_arc_conversion_and_range`); conversely 2.5-4.3
kW/m2K inside a 60 degree jet zone is a mean of 0.42-0.72 kW/m2K [D]. The demo carries no arc
(no plant value) and no coefficient was changed.

**Strip temperature across the width** (SPEC17 A1): a supplied scan gives the flatness a
shapemeter measures hot against the flatness after cooling, about 2.4 I-units per kelvin
[computed]; section 7.7.

**Fire limits (SPEC17 A10).** With `tribology.oil_flash_point_k` and / or
`tribology.oil_supply_temperature_cap_k` (user limits, 250-700 K, never defaulted)
`thermal_check.fire_limits` compares the oil inlet temperature and the coolant temperature
(read as the oil supply) with both, and the modelled strip exit temperature of every pass with
a pass-heating row with the flash point: rows with value, limit, margin and `BELOW_LIMIT` /
`AT_OR_ABOVE_LIMIT`, flags `STRIP_EXIT_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT`,
`OIL_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT`, `OIL_SUPPLY_TEMPERATURE_ABOVE_SITE_CAP`
(evidence-neutral). Without either input the block is `NOT_SUPPLIED` and the report says "not
checked: no flash point given"; the catalogue's flash-point and fire statements (`context`,
[PT-T9, PT-T10, PT-T11, PT-T15, PT-T14]) and the levers that raise temperature (reduction,
friction, a weak coolant zone or flow, oil supply temperature, speed) are shown either way.
A modelled strip exit temperature is an indicator, not a coil temperature (EXIT_IS_NOT_COIL);
there is no oil-mist or vapour model. Hand check: flash point 80 C against a 45 C oil inlet
gives a margin of 35.0 K.

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
python -m physicroll.band_cli my_case.json --calibrate-spray my_scan.json        # section 7.1
python -m physicroll.band_cli --fit-hardening my_strengths.json                   # section 8.3
```

`--calibrate-spray` and `--fit-hardening` only print a JSON result; they never write into a
case, and `diagnose` never runs them.

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
| `width_model.circumferential_layout` | optional: where the sprays (and a backup-roll contact) sit around the work roll, as angles in the direction of rotation measured from the bite exit (section 7.10); a wrong arc changes the surface cycle, so the layout used is printed in the result | rad | header position and fan width on the stand drawing (angle of the header centre from the bite exit, fan opening angle at the roll), the direction of rotation of the top work roll |
| `tribology.interface_conductance_w_m2k`, `tribology.use_computed_heat_partition` | optional: a heat-transfer coefficient between strip and roll in the bite (else oil conductivity over film thickness), and whether the computed heat share replaces the entered one (section 8.2) | W/(m2 K), - | leave empty unless measured |
| `hardening.rate_temperature` | optional strain-rate and temperature factor of the flow stress (section 8.3); no default number; enter the rate and temperature terms together or not at all | – | rate-jump and warm tensile tests on your stock |
| `pass.friction_coefficient` | Coulomb friction in the roll bite; no catalogue value exists, the demos use 0.03 | – | back-calculated from measured roll force and forward slip, or the mill's setup model; enter measured passes in `measurement.pass_records` and the tool reports the friction they imply (section 8.5) |
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
| `tribology.friction_closure.model: "load_sharing_curve"`, `contact_friction`, `valley_model`, `contact_ratio_curve`, `valley_film_curve` | the second friction law (section 8.1); the contact friction is REQUIRED with it; the curves default to the published foil pass | – | contact friction from your measured force, torque or slip, or a strip-drawing test; no default |
| `tribology.lubricant.viscosity_table`, `pressure_law`, `roelands_z`, `eyring_stress_pa`, `eyring_stress_pressure_coefficient`, `limiting_shear_stress_pa`, `limiting_shear_pressure_coefficient` | oil viscosity at several temperatures (list of `{"temperature_k", "viscosity_pa_s"}`); the pressure law (`barus` default, `roelands` option); the oil's Eyring and limiting shear stress (no defaults) | K, Pa s, Pa, – | oil supplier data sheet; the shear stresses only from oil tests (section 8.1) |
| `model_options.bite_model: "half_space"` / `"auto_half_space"`, `model_options.shear_cap_factor` | the reduced half-space foil model for every pass / where Hitchcock stops; the largest friction stress as a share of the shear strength (0 to 1, default 1, used only by that model) | – | use it to see how far the conclusions depend on the roll-bite model: run the case with the standard choice and with the half-space model and compare (section 3.3); it is not a better default |
| `width_model.roll` | work-roll barrel length and thermal properties (conductivity, density, specific heat, expansion) | m, W/(m K), kg/m³, J/(kg K), 1/K | roll drawing and roll supplier |
| `width_model.spray_header`, `coolant_temperature_k`, `roll_heat_fraction_per_roll`, `numerics`, `rolls_carrying_stripe`, `shape_disturbing_coefficient`, `heredity_coefficient`, `cooling_zone_pitch_m`, `strip_centre_m` | spray header and cooling zones of the roll thermal model, coolant temperature, heat share into each roll, numerics | m, W/(m² K), K, – | spray header drawing, coolant system data; flatness-controller zone map; the spray coefficient can be fitted to a roll temperature scan or camber with `--calibrate-spray` (section 7.1) |
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

Optional section added in SPEC17 package 4: `measurement` (v2 only; `null` = not supplied)
with `shapemeter`: `zone_width_m` (0-0.5 m) and `zone_count` (1-400) from the shapemeter data
sheet or the level-2 configuration, optional narrower `edge_zone_width_m` with
`edge_zone_count_per_side`, `centre_m` (null = the strip centre of the width section),
`neighbour_spreading_fraction` (0-0.25, keep 0 unless the vendor states it),
`resolution_i_units` (null unless the vendor gives one; then the tool's 2 I-unit band
threshold is used) and `provenance`. `thickness_gauge` (SPEC17 package 5, section 11.6):
`spot_length_m` along the strip (0-1 m) and `time_constant_s` of the first-order response
(0-10 s) from the gauge data sheet, optional `sample_interval_s`, `position_m` on the barrel
(null = strip centre), `spot_width_m` across the width, and `provenance`. Section 7.6.

Optional keys added in SPEC17 package 3 (absent and `null` give the same result; the template
lists them with `null`): `width_model.spray_wetted_arc_rad` (arc of the circumference the spray
wets, in (0, 2*pi]; only expresses the spray coefficient on a jet-zone basis, section 3.12; it
does not enter the roll thermal model), `tribology.oil_flash_point_k` (oil data sheet) and
`tribology.oil_supply_temperature_cap_k` (a site or insurer cap), both 250-700 K, used only by
the fire-limit check (section 3.12); the guided app asks for the two oil limits.
`width_model.strip_temperature` (SPEC17 package 6, section 7.7; null = no scan):
`positions_m` (at least 3, increasing, on the barrel), `temperature_k` (one per position,
250-700 K), `expansion_coefficient_per_k` (null = the textbook 23.6e-6 /K, flagged) and
`provenance`. Take the scan at the exit, near the shapemeter, with a line-scan pyrometer or a
contact probe across the strip, or on the coil face; the low and variable emissivity of
aluminium makes pyrometer readings difficult (gap study section 7.4), so calibrate against a
contact probe. `width_model.friction_stripe_screen` (SPEC17 package 7, section 7.8; null = no
screen): `reference_half_peak_width_m` (null = 0.1 m) and `stripes` (may be empty), each
`position_m` on the barrel, `half_peak_width_m`, `friction_change_fraction` (relative change of
the pass friction, -0.9 to 5, not 0) and an optional `label`; a stripe can come from a roll
roughness or coating map, an oil-flow or oil-temperature map per zone.
`width_model.roll_ground_profile` (SPEC17 package 8, section 7.9; null = none): `positions_m`
(at least 5, increasing, on the barrel), `radius_deviation_m` (radius, one per position, within
+-1 mm), `detrend_order` (0-6 or null, default 4 since SPEC20; 2 before), `rolls_carrying` (1 or
2, default 1) and `provenance`; from a roll grinder's profile report of the work roll in the
mill (grinder gauges read diameter: halve the deviations). `kinematics.grinder_marks` entries
(SPEC20) give the roll and EITHER `marks_per_circumference` (counted around the roll) OR the
grinder's last-pass settings: `roll_rotation_hz` with `wheel_rotation_hz` (or
`vibration_frequency_hz`), from the grinder's program sheet; the guided app asks for them in
r/min in the group "A roll grinder report".
`measurement.shapemeter.temperature_compensated` (true / false / null) says
whether the shapemeter corrects for strip temperature.
`width_model.local_coupling` (SPEC19 package 1, section 7.11; null = none):
`inlet_roll_temperature_weight` ([0, 1], default 0.5: the share of a roll surface temperature
difference that reaches the oil at the inlet; an assumption, no measurement exists),
`flow_stress_temperature_coefficient_per_k` ([0, 0.01] /K or null = the coefficient of
`hardening.rate_temperature` when that is given, else no flow-stress change; from tensile tests
of your alloy at 20 and 100 C), `strip_roll_temperature_coupling` ([0, 1.5] or null = computed
from the bite heat partition), `oil_flow_per_nozzle_m3_s` ((0, 0.1] m3/s or null = no supply
check; the oil flow per zone from the coolant system display divided by the nozzles of the
zone), `oil_capture_fraction` ((0, 1], default 1) and `provenance`. It changes no score.

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
| `grinding_feed_marks` | Helical feed lines from the roll grinder; the lateral pitch is the traverse per roll revolution. | every gap within 10 % of 1-3 x the feed pitch (S str); regular spacing (CV < 0.15) below 60 mm (S weak; SPEC20: printed final-pass feeds are 9-25 mm on an aluminium cold-mill roll [RG5] and 24-53 mm on a foil roll [RG7, computed from the printed settings], so the ceiling sits just above the largest, an analyst choice [D]; the prediction's `feed_range_note` says so and that a wide, irregular spiral from table float does not follow the feed law and belongs with `roll_surface_band` [RG8 FT]); positions change after a work-roll change (S mod); gloss_or_shade (S mod); continuous (S weak) | gaps not matching (C mod); positions stay after a work-roll change (C str) | measure the spacing against the grinder traverse per revolution; roll inspection; roll change |
| `incoming_ridge_coil_buildup` | A local high spot in the incoming profile stacks up wrap by wrap in the coil, stretches the band beyond yield and leaves a tight-then-loose band, worse toward the outer wraps. | positions do not repeat across coils (S mod); worse toward outer wraps (S str); position on a supplied ridge (S str); model ridge yields the strip (S mod, model); intermittent with 5-95 % of the coil length affected (S weak); worse at thinner gauge (S mod); visible only after release (S weak) | positions repeat (C mod); positions change after a work-roll change (C weak); not worse toward outer wraps (C mod); model ridge does not yield (C weak, model) | entry profile scan of the incoming coil and outside-profile scan of the wound coil |
| `tension_troughs_or_creases` | Lateral buckling of thin strip under tension in a free span (troughs), which a roll can iron into a crease. | spacing 0.5-2 x the computed trough wavelength of either span (S str when the spacing is established: a stated `band_spacing_m` or at least two regular gaps, CV <= 0.1; S weak for one gap or irregular gaps, with the text "cannot establish a spacing"); crease_or_flute (S str); changes with tension (S str); model troughs expected (S mod, model; needs `lateral_compressive_stress_pa`); intermittent or both (S weak); worse at thinner gauge (S mod); changes with ironing-roll pressure (S mod); exit gauge below 50 um, creasing possible [V S25] (S weak, input, gated) | spacing outside 0.25-4 x both wavelengths (C mod, only for an established spacing); stain (C mod); does not change with tension (C str); model below the trough threshold (C weak); positions change after a work-roll change (C weak); worse at lower tension (C weak: troughs need tension; a crease from a loose band is the exception, so it stays weak) | vary the span tension and watch the bands; check deflector / idler alignment and crown; measure the trough spacing |
| `profile_flatness_mismatch` | Relative crown change between entry and exit outside the Shohet-Townsend dead band: smooth edge waves or a centre buckle rather than narrow stripes. | crown change outside the dead band (S str, model); all positions within 15 % of the width of an edge or of the centre (S mod); band width > 150 mm (S weak); loose_or_buckle (S mod); visible only after release (S weak); worse at thinner gauge (S mod) | crown change inside the dead band (C mod, model); two or more interior positions (C mod); band width < 60 mm (C weak) | entry and exit profile measurements; shapemeter map; compare relative crowns |
| `heat_streak_or_film_variation` (title "Heat streak / friction or oil-film band (no roll bump)") | Local oil-film or friction variation across the width: milky heat streaks that wander in width and position (QCA-1), or, in foil where the oil film is comparable to the roughness, a cross-width difference in roughness or oil film that gives a flatness band without a geometric roll bump and tracks speed changes [V S11, S17; mechanism D]. | gloss_or_shade (S mod); no gauge variation (S weak); positions do not repeat (S mod); intermittent or both (S mod); worse at higher speed (S mod); tracks speed changes (S str); exit temperature above a supplied limit (S weak, model, gated; otherwise NEUTRAL: since SPEC17 the film-ratio label no longer counts, a film ratio below 1 being normal mixed-regime operation [BT-S3 EX, BT-S9 EX]; the film-collapse test of the gap study is not built, it needs BT-G3 / BT-G11); film ratio 0.3-3 at the operating point, from `tribology` or else the phase-1 lubrication screen (S weak, model, gated); exit air blow-off NEUTRAL | crease_or_flute (C mod); positions repeat (C weak); positions change after a work-roll change (C weak); does not track speed changes (C weak) | compare band appearance with oil temperature and speed (does the band appear, move or fade with a speed change?); check whether the bands wander between coils; measure the work-roll roughness across the barrel |
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
| 3 | `work_roll_borne_marks` | law SPEED_INDEPENDENT S str, FIXED_FREQUENCY C str. pitch = `pi*D_w*(1+f)/n` within 3 % for ONE n (1..8 or a grinder-mark count, supplied or computed) that fits every pitch best (smallest worst mismatch; a grinder count preferred on a tie), S str, no match C mod; SPEC20: a grinder count may be computed as `f/n_roll` from the grinder's last-pass wheel (or vibration) and roll speeds [RG25 AB, RG26 AB, RG24 VP] and is not rounded (grinder chatter is a spiral on the roll); with grinder data entered the test is decisive as before; without it, on the work roll, a pitch that fits no n in 1..8 but implies 12-240 marks per circumference for every pitch (the typical range of printed grinder settings, [computed]) gives NEUTRAL, not C, with the flag `GRINDER_CHATTER_NOT_EXCLUDED_NO_GRINDER_DATA`; the range bounds what cannot be excluded and is never used as a default grinder; `grinder_pitch_check` in the prediction lists the implied count per pitch and says that entering the wheel and roll speeds turns it into a test; orientation: wheel-spindle vibration leaves a spiral on the roll, work-rest, tailstock or headstock an axial one [RG24 VP], so a slightly oblique transverse mark is compatible with a grinder source; the same n in the prediction and the strip map. work-roll change: disappears S str, persists C str. faces one S mod, both C weak. longitudinal C str. |
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
  (the experimental mattress model reports such values, as a constant-friction model with a
  no-slip zone does, section 3.3; a supplied bite may too) keeps two values: zero is used only in the roll-borne pitch
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
- **Rule changed in SPEC17: the film-ratio label no longer supports the heat-streak
  hypothesis** (BT-G8, X21). A film ratio below 1 was labelled `BOUNDARY` and counted as weak
  support; in the sources it is the condition for a good roll imprint inside the mixed regime
  and 0.01-0.5 is the common industrial window [BT-S3 EX, BT-S9 EX]. The item now supports
  (weak, model, gated) only when the exit temperature exceeds a supplied limit, else it is
  `NEUTRAL`; the criterion string is unchanged. Score changes: battery-foil demo
  `heat_streak_or_film_variation` 4 -> 3 (rank 4 -> 5, `tension_troughs_or_creases` moves up),
  lengthwise demo 4 -> 3 (rank 4 -> 5, `profile_flatness_mismatch` moves up); leaders, every
  other score and every standing are unchanged. The herringbone rule keeps its film-ratio
  `Lambda < 1` item (weak support) with the wording "substantial asperity contact" (section
  14).
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
pass of the schedule (7.3); switching events are simulated in time (7.4); with an angular
layout the roll surface within one revolution is added on top (7.10). Integration code:
`physicroll/band_width.py`; equations: `physicroll/roll_thermal.py`,
`physicroll/strip_shape.py`.

### 7.1 Roll thermal model (`roll_thermal.py`)

*Calibrating the spray coefficient* (SPEC18 package 11, gap row A5): see the end of this
section.

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
[PT-T26]). Partly open (the per-revolution layer of 7.10 gives a surface-film scale of 15.9 s
for this demo's inputs: a comparison, not a resolution). Possible causes, none modelled: bite heat that depends
on the roll surface temperature, emulsion-level heat transfer, per-revolution effects. The
literature adds two candidates (gap study X5): the surface time scale of the roll, and the
strip-temperature term in measured flatness (section 7.7; a hot fibre reads loose while hot);
neither is tested here.

Not modelled: the per-revolution surface temperature cycle, the bite contact conductance
and roll-strip temperature coupling (`q` is supplied or computed from the pass, not coupled
back), the flow distribution inside a fan, spray drift, temperature-dependent properties,
neck and chock losses, axial mechanical coupling of the expansion, roll wear, bending and
flattening. No measured spray heat-transfer coefficient for kerosene-based coolant was found
(planner estimate 0.5-2 kW/m2K [D]; an Innoval blog gives 4.65-5.5 kW/m2K overall for an
unspecified coolant); the coefficients are inputs.

**Fitting the spray coefficient to a measurement (A5).**
`python -m physicroll.band_cli my_case.json --calibrate-spray my_scan.json [--numerics case]`
(`band_thermal.calibrate_spray_coefficient`) fits the ONE coefficient
`width_model.spray_header.spray_mean_htc_w_m2k` of the case's steady roll thermal problem
(built exactly as the width section builds it, `band_width.thermal_heat_inputs` and
`_Thermal`) to an entered measurement: `kind` `roll_surface_temperature_after_stop` (a barrel
surface temperature scan `seconds_after_stop` after the mill stopped; the model then runs that
long with sprays off and no bite heat) or `thermal_camber` (radius growth; both profiles
reduced by their own mean, because the reference of a measured camber is unknown [D]);
`positions_m` (at least 5, on the barrel), `values` (K or m), `provenance`, optionally
`search_range_w_m2k` (default 500-20000) and `uncertainty` (one standard deviation of a
measured value). Search: 9 geometric values, then golden section in `ln h` until the bracket
is within 2 % (at most 12 more evaluations) [D, SPEC18]. **The fitted value is the
circumferential-mean coefficient of this model for this mill** (top-hat footprints, the case's
background coefficient, heat share and bite heat), not a jet-zone value; it is not compared with
published spray coefficients, whose basis is not established (X3); with
`spray_wetted_arc_rad` the result also gives the footprint equivalent
`background + h*2*pi/arc`.

*What it holds fixed, and how to read the result.* The background coefficient, the coolant
temperature, the roll properties, the heat share and the bite heat come from the case
(`assumed_inputs`), so their errors go into the fitted value; `heat_share_sensitivity` refits
with a 10 % higher roll heat fraction and gives the exponent `d ln h / d ln(heat fraction)`
(about 0.95 for a camber and 1.08 for a scan 30 s after a stop on the battery-foil roll [run]:
a heat share 10 % too high gives a coefficient about 10 % too high, and the stripe heights
scale with that heat share). `misfit_curve` lists every evaluation; a flat curve means the
measurement does not determine the coefficient. With `uncertainty` the result gives
`range_within_measurement_uncertainty_w_m2k`, the coefficients whose RMS misfit stays within
`sqrt(minimum^2 + u^2)` [D]. Refusals, with a named `outcome` and no number: `TOO_FEW_POINTS`
(fewer than 5), `NO_CONTRAST` (a profile that spans no more than the entered uncertainty),
`NOT_DETERMINED_FLAT_MISFIT` (the misfit within 10 % of its minimum over the whole range, e.g.
the header was off), `AT_SEARCH_LIMIT` (the minimum at an end of the range: widen the range or
check the inputs). Twin tests (the model at 3400 W/m2K as the measurement) recover 3390
W/m2K with both kinds (the 2 % bracket), and with noise of the stated uncertainty the true value
lies inside the reported interval. Cost on the battery-foil roll: 5 s for the case-pass bite
heat, then 37 evaluations of 0.012-0.016 s with quick numerics (20 mm cells, 6 radial cells) or
0.20-0.26 s on the case grid. The grid matters by a few per cent (3390 quick against 3269
W/m2K on the case grid for the same camber): fit with `--numerics case` for the value you enter.
*To use it*, enter the value by hand as `width_model.spray_header.spray_mean_htc_w_m2k`;
nothing is changed automatically.

*How to take the scan* (gap study 7.4): a barrel surface temperature scan at 25-50 mm pitch
within 60 s of roll-out, with the preceding 30 min of spray-zone states, flows and oil
temperature logged, the time after the stop noted; or the roll's thermal camber measured after
a pass.

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
stripe a shapemeter can see when the band is at least about one zone wide (section 7.6)). Tension enters with its sign, so a compressed zone flanked by
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
`lateral_compressive_stress_pa`. The trough and roller-wrinkle thresholds come from isolated-span formulas: for aluminium
and copper foil below 25 um and wider than 0.6-1 m, wrinkles needed about 15 times the
predicted roller misalignment [SS-S55 EX], so at foil gauge these thresholds are
conservative screening values (key `wide_foil_note` on each span of `width.troughs` below
100 um, printed under the trough table; SPEC17 X12).

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
manifest threshold). With `width_model.local_coupling` each event row also carries
`local_sources` (section 7.11): the film, flow-stress and strip-temperature terms beside the
roll-growth term at the snapshot nearest `start + min(20 s, duration)` (the fast path,
`FAST_PATH_TIME_S` [D, SPEC19: analyst choice; the surface time scale is 8-25 s]) and at the
peak snapshot, from the surface temperature and radius differences against the starting steady
state; the simulation and every other event value are the same with and without the key.
These are integration choices of `band_width.py` [D]:

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
| 4 | `profile_flatness_mismatch` | CONSISTENT | 4 |
| 5 | `heat_streak_or_film_variation` | CONSISTENT | 3 (4 before SPEC17, section 6.4) |
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

### 7.6 What a shapemeter would show

`physicroll/band_sensors.py` (SPEC17 package 4; gap rows C7 zone part, G5 sensor part, X9).
With the optional case section `measurement.shapemeter` the result gains
`measurement.shapemeter`: what each zone of a flatness roll with that zone width **would show**
for every modelled band. It is a measurement operator only: **no flatness controller** is
modelled (no actuator fitting, no valve logic; G5, Phase 2), so the tool does not predict what
the control would have done with these readings, and the readings are not a forecast of the
operator's screen. No hypothesis reads the section.

What the literature says about shapemeters [SS-S29, SS-S30 VP; SS-S31, SS-S32 EX]: zones of 26
or 52 mm on rolls, 25-100 mm on rotors, with force spreading to the neighbouring zones; a band
narrower than a zone is diluted, and a tight edge beside a loose pocket in one zone is missed.
Vendor accuracy is quoted as 0.5 I-units typical [SS-S29 VP]; it is never used as a default.
This qualifies the sentence of section 7.2 that a latent band is a stripe a shapemeter can
see: that holds when the band is at least about one zone wide.

The operator [D, re-derived in SPEC17]: a stress-measuring roll senses the radial force per
zone, i.e. the mean tension over the zone, and shows its deviation from the mean over the
zones. Zone edges `e_0 = centre - sum(widths)/2`, `e_{j+1} = e_j + w_j` (optional narrower edge
zones; the centre defaults to the width section's strip centre). Each sample of the modelled
profile is constant over its cell, clipped to the strip; the zone mean is
`m_j = sum_i(I_i*o_ij)/sum_i(o_ij)` with `o_ij` the overlap of cell, zone and strip; coverage
`c_j` = fraction of the zone over the strip (an uncovered zone reads null); roll mean
`m_bar = sum(c_j*w_j*m_j)/sum(c_j*w_j)`; reading `u_j = m_j - m_bar`. Neighbour spreading
`r_j = (1 - 2s)*u_j + s*(u_{j-1} + u_{j+1})` is an interpretation of the vendor sentence
"max. 2 x 12.5 % force spreading to adjacent measurement zones" [SS-S29 VP; the vendor
algorithm was not read], **off by default** (`neighbour_spreading_fraction` 0). Each band of
`levels.with_feedback` is read in the zone holding its peak; it "would show" when the reading
reaches the threshold (`resolution_i_units` if supplied, else the tool's own 2 I-unit band
threshold) and "would probably not show" otherwise; a band below the threshold can still be on the
strip. Profiles read: the steady stripe profile, each cooling-zone event at its peak,
and the healthy header's nozzle-pattern ripple. The compliance-only and rigid levels are not
read.

**Dilution table** (always printed; zone mean of a band of peak 1): a top-hat of width `b`
reads `min(b, w)/w` centred in a zone and `min(b/2, w)/w` on a zone boundary; a Gaussian of
half-peak width `b` reads `(b/w)*k*erf(sqrt(ln 2)*w/b)` centred and
`(b/(2w))*k*erf(2*sqrt(ln 2)*w/b)` on a boundary, `k = sqrt(pi/(4 ln 2))`. For a 52 mm zone:
a 20 mm top-hat reads 0.3846 centred and 0.1923 on a boundary (25 I-units read 9.6 and 4.8; the
report's "about 10" [D]); a 20 mm Gaussian 0.4085 / 0.2047, 40 mm 0.7158 / 0.4085, 80 mm
0.9104 / 0.7158; a 26 mm zone reads a 20 mm Gaussian at 0.7158 / 0.4085. A narrow source matters:
a 20 mm band of 3.1 I-units centred in a 52 mm zone reads 1.2 (pinned by
`test_narrow_band_reads_a_fraction_of_its_peak`).

**Nozzle map.** From the width section's own geometry (`band_width.spray_layout`): the nozzles
inside each zone with their effective levels, nozzles per zone, zones without a nozzle and the
ratio of `width_model.cooling_zone_pitch_m` to the zone width. Cooling zones are built at the
shapemeter pitch and each spray is driven by its zone [SS-S31 EX, SS-S33 EX, SS-S34 EX]; the
tool has one header row and no controller.

**Battery-foil demo** (`measurement.shapemeter`: 24 synthetic zones of 52 mm on the mill
centre line, edges 0.126-1.374 m over the 0.15-1.35 m strip, the two end zones 54 % covered;
each zone holds exactly one nozzle at its centre, zone j nozzle j + 2). Steady profile: the
loose band of 25.09 I-units at 0.6225 m (half-peak width 160 mm) reads 24.49 in zone 9, 97.6 %
of its peak, so the demo's thermal stripe is wide enough for a 52 mm shapemeter; zones 7-11
read 6.60, 20.45, 24.49, 20.45, 6.60; the tight edges -5.18 and -5.22 read -5.18 and -5.21. With
spreading 0.125 zone 9 would read 23.48 (93.6 %). The 20 s valve event at its peak: 21.01
I-units read 19.33 in zone 16; its two tight side bands (-3.51) read -1.83, below the 2 I-unit
threshold, so the result carries `MODEL_BAND_BELOW_SHAPEMETER_THRESHOLD`. The nozzle-pattern
ripple of the healthy header (3.14 I-units peak) reads at most 0.53: a pattern at the nozzle
pitch is averaged out by zones of the same pitch. The 98 % of the demo stripe must not be read
as "dilution never matters": it matters for narrow sources (ground marks, friction stripes),
see the dilution table.

Not modelled: roll wrap, measurement noise, calibration, temperature compensation, shapemeter
dynamics and filters, the stress evolution between bite and shapemeter [SS-S22 EX], the stress
relief of a buckled band, vendor edge rules, any controller.

The thickness gauge of the same `measurement` section (the transverse side: what a gauge keeps
of a mark pitch) is described in section 11.6.

### 7.7 Strip temperature across the width

SPEC17 package 6 (gap rows A1, G6; `strip_shape.thermal_flatness_term`,
`band_width.strip_temperature_section`). A strip fibre hotter than its neighbours at the
shapemeter is longer by `alpha*dT`: it reads loose in the mill and the difference disappears
when the coil cools [TM-LA13 EX; for steel 1 C = 1.2 I-units, TM-LA30 EX; SS-S40 VP]. With the
optional `width_model.strip_temperature` (a measured or assumed scan across the width; **the
profile is supplied, not computed**: the per-width heat balance that would compute it needs the
heat split, gap A3, Phase 1) the result gains `width.strip_temperature`.

Formula [TM report gap A1]: `eps_T(z) = alpha*(T(z) - mean(T))` (arithmetic mean over the strip
samples), `I_T = 1e5*eps_T`. The default `alpha = 23.6e-6 /K` is a textbook value used by the
gap reports and tagged from memory there [M]; it is used with the flag
`STRIP_EXPANSION_COEFFICIENT_FROM_MEMORY_DEFAULT` unless `expansion_coefficient_per_k` is
supplied. That gives 2.36, about 2.4, I-units per kelvin [computed], above the tool's 2 I-unit
band threshold. The scan is interpolated linearly onto the strip samples of the steady shape;
outside its range the end value is held (`scan_coverage.extrapolated_width_m`, flag
`STRIP_TEMPERATURE_SCAN_DOES_NOT_COVER_STRIP` when that exceeds one grid cell).

Which profile means what [D, re-derived in SPEC17]: with `eps_m` the model's mechanical
elongation (what the roll gap printed, referred to a uniform temperature), the stress a
shapemeter senses in the hot strip follows `eps_m + eps_T`; after the coil has cooled to a
uniform temperature only `eps_m` is left. The model has no flatness controller, so:

| profile | elongation | meaning |
|---|---|---|
| `mechanical` | `eps_m` | the model's flatness as it is today (`width.shape.steady`, with feedback) |
| `as_measured_hot` | `eps_m + eps_T` | what a shapemeter without temperature compensation senses; also the strip in the mill and a sample released while hot |
| `after_cooling` | `eps_m` | equal to `mechanical` (no controller in the model); listed so that the reader sees it |
| `after_cooling_if_hot_reading_held_flat` | `-eps_T` | BOUNDING CASE only: if a flatness control had removed everything the hot shapemeter showed, the cold strip would carry the negative of the thermal term (a hot fibre becomes tight); it needs the controller of G5 to be more than a bound |

Each profile is evaluated by `flatness_from_elongation` (bands, in-mill state, state after
release). `state_changes` compares every band of `mechanical` and `as_measured_hot` with the
band of the other at its peak (flag `STRIP_TEMPERATURE_CHANGES_A_BAND_STATE`). The term is
reported beside the width section: it is not added to `width.shape.steady`, the onsets, the
gauge trend or any evidence item, so no latent / manifest verdict and no score moves. Without a
mechanical profile the hot profile is the thermal term alone (flag
`STRIP_TEMPERATURE_TERM_WITHOUT_MECHANICAL_PROFILE`). The shapemeter of section 7.6 also reads
`steady_as_measured_hot`; with `measurement.shapemeter.temperature_compensated: true` that
profile is labelled "before the shapemeter's own temperature compensation; a compensated system
shows the mechanical profile" (flag `SHAPEMETER_TEMPERATURE_COMPENSATED`).

**Battery-foil demo** (synthetic scan, marked so in its provenance and notes: +3 K at the partly
blocked nozzle, a Gaussian of 0.10 m half-peak width at 0.6225 m on 353.15 K, 25 points at
50 mm pitch; an assumption, not a model output). Mean 353.416 K, largest deviation 2.33 K;
thermal term +5.50 / -0.63 I-units (alone: one loose band 0.560-0.685 m, peak 5.50 at
0.6025 m, latent in the mill, manifest after release). `mechanical` equals the steady profile
(peak 25.09 I-units at 0.6225 m, latent / manifest after release). `as_measured_hot`: 30.47
I-units at 0.6175 m (band 0.495-0.745 m), latent / manifest after release, tight edges -5.81
and -5.85; no band state changes. Bounding case: one tight band of -5.50 I-units, latent, flat
after release. A 24-zone shapemeter reads 29.81 I-units hot in zone 9 against 24.49 for the
mechanical profile. The report's warning: flatness measured hot and after cooling differ by
5.5 I-units at 602.5 mm.

Limits: the temperature profile is an input; the thermal strain is not fed back into the bite
or the exit-tension feedback; where the mechanical profile was saturation-scaled the sum is
indicative; the temperature at the shapemeter is taken equal to the scan; the after-cooling
profile assumes no creep or set in the coil (A8); no target-curve offset [TM-LA30], no
controller, no coil cooling model.

### 7.8 A friction or oil-film stripe as a band source

SPEC17 package 7 (gap BT-G4, screening version; `strip_shape.transfer_force_profile`,
`band_width.friction_stripes_section`). The roll bump is the only band source of the shape
chain. The bite report argues that a local difference of friction at one width position
(roughness, roll coating, oil supply or oil temperature) acts like a roll bump, because the
load depends on friction with an exponent of about 2 to 2.6 [derived, slope read by eye from
BT-S1 Fig. 6a], and that it "grows as gauge falls" [BT-S1 FT, BT-S3 EX; mechanism derived].
The full model needs BT-G1 and BT-G3; this is the screening version from the existing bites.

Transfer [D, re-derived in SPEC17]: a local change of roll force per width at an unchanged gap,
`dp0'(z) = M_mu*dmu(z)` with `M_mu = (dF/dmu)/width` of the pass's bite (central difference
+-2 %, `band_process.friction_force_sensitivity`), is answered by the strip with
`-Q_eff*dh`; both rolls indent under the net force, so per Fourier component
`dh_k = G(lam_k)*dp0'_k`, `G = 2*C/(1 + 2*C*Q_eff)`, with the compliance `C`, the clamps and
`Q_eff` of the roll-bump transfer (section 7.2). More friction makes the strip locally thicker,
the fibre shorter: tight. With the feedback dominant the elongation tends to
`-dp0'/(N_x'*E_strip)`, independent of gauge. The elongation and I-units follow as in the
shape chain; the band-wise saturation is not applied (flag
`FRICTION_STRIPE_LINEAR_FEEDBACK_NOT_SATURATED` when a supplied stripe buckles in the mill).

With the optional `width_model.friction_stripe_screen` the result gains
`width.friction_stripes`: per pass the load exponent `M_mu*mu/(F/width)` and the I-units at the
centre of a 1 % friction stripe (Gaussian, half-peak width 0.1 m by default) with the
exit-tension feedback and compliance only (both levels always together), the trend text, the
sign note and each supplied stripe with its band states. The battery-foil demo carries an empty
screen (no stripe; the table only):

| pass | exit gauge [um] | F/w [N/m] | load exponent | I per +1 %, with feedback | compliance only |
|---|---|---|---|---|---|
| S1 | 135 | 709291 | 0.637 | -4.13 | -54.6 |
| S2 | 85 | 612275 | 0.666 | -3.01 | -78.0 |
| S3 | 50 | 736445 | 1.194 | -4.44 | -235.2 |
| F1 (case pass) | 30 | 958605 | 1.609 | -3.15 | -392.0 |
| ALT1 | 25 | 1487662 | 1.917 | -3.47 | -596.6 |
| F2 | 18 | 1536047 | 2.159 | -2.74 | -566.1 |
| ALT2 (not credible, excluded from the trend) | 12 | 6187753 | 6.870 | -2.29 | -871.4 |

**The finding, reported by the tool:** the bite report's "grows as gauge falls" holds for the
load exponent (0.64 to 2.16, rising on every credible pass) and for the compliance-only level
(55 to 566 I-units per 1 %; along the plant's route S1-S3, F1, F2 it rises on every pass, and
across the two routes it is not monotonic because ALT1 at 25 um gives 597), and it does NOT hold
with the exit-tension feedback (2.7 to 4.4 I-units per 1 %, no trend). The trend text says
so and ends: "Whether a friction stripe grows as gauge falls therefore depends on the
exit-tension feedback, the least supported element of the shape chain." Case pass: about
0.64 % of friction difference reaches the 2 I-unit threshold with the feedback; the feedback
limit is -3.49 I-units per 1 %. A supplied stripe of -10 % friction (half-peak width 60 mm at
0.988 m) on the case pass gives a thickness change of -78.7 nm and a loose band 0.935-1.04 m of
+32.9 I-units, latent in the mill and manifest after release; +10 % gives -32.7, tight, latent,
flat after release (`tests/test_band_friction_stripes.py`).

Sign: a locally higher friction makes the strip locally thicker and the fibre tight; a locally
lower friction makes it loose. For a hot roll stripe the film path (thinner film, more friction)
acts against the roll-growth path (larger roll, thinner strip). With
`width_model.local_coupling` the model gives the film, flow-stress and strip-temperature terms
of a hot roll stripe beside the roll-growth term, each on its own and summed, with two inlet
weights (section 7.11, second part); their sign rests on an assumed inlet weight. With `tribology` a separate, flagged block (`PLACEHOLDER_FRICTION_CLOSURE_NOT_FITTED`)
converts the placeholder closure's slope into a friction change per kelvin of oil temperature
(`dmu/dLambda*Lambda*(-beta)`: +3.2e-4, about 1.1 % of the friction 0.03 at the case pass) and
per +10 % roll roughness; the closure's slope is not supported by data (X22), so these are
orders of magnitude only.

What it rests on: `dF/dmu` of a constant-friction bite, at foil gauge the experimental mattress
bite, which returns 0.42 of the reference load on the one published benchmark (section 10.2);
an exit-tension feedback the literature neither supports nor contradicts (X17); friction uniform
through the bite, no film model across the width, no starvation (BT-G12), no coupling to the
roll temperature (A2). No evidence item: `heat_streak_or_film_variation` gets no model item from
this screen (SPEC17 open decision 3); the supplied stripes are also read by the shapemeter
(section 7.6) as `friction_stripe_<k>`. The screen derives its perturbed bites in a cache of its
own, so the result's `bite_derivations` count is unchanged.

### 7.9 A measured roll profile

SPEC17 package 8 (gap G13; `band_width.roll_profile_section`). Grinding residuals and local
wear are narrow diameter deviations that transfer like thermal stripes and that bending cannot
remove [SS-S3 FT, model output; SS-S72 EX]. With the optional `width_model.roll_ground_profile`
a measured profile goes through the existing transfer (`shape_levels`, the same function as the
steady thermal stripe; `transfer_radius_profile` is unchanged) and the result gains
`width.roll_profile`.

How to enter a grinder report: give the RADIUS deviation (half of a diameter deviation) from
the intended ground shape, positive where the roll is larger, at `positions_m` measured from the
barrel end where the spray header starts (the width section's barrel coordinate);
`detrend_order` (default 4 since SPEC20; 2 before) removes the crown or camber by a polynomial over the strip, which
belongs to the crown model and is only reported (`removed_polynomial_m`, drawn in the report);
use `null` to keep the whole profile, a higher order only for a wavy roll. `rolls_carrying` is
1 for a profile of one roll, 2 when both work rolls carry it.

The profile is interpolated onto the width grid (end values held), de-trended by
`roll_thermal.local_stripes`, and the local deviation gives the three levels (rigid bound,
compliance only, with exit-tension feedback), the stripe table with states and onsets, the
combination with the thermal stripes of the same roll, the observed-position match (information
only) and a stiffness indicator: the strip foundation modulus `(F/width)/(h_entry - h_exit)`
(Patel's `kf1` as the report restates it [SS-S3 FT]) against the roll term `1/(2*C(lam))` at
twice the half-peak width of the largest stripe (the project's analogue, not Patel's `kf2`,
whose definition was not recorded), with the published ratios (thin aluminium 0.236 mm: 176 /
57.8 kN/mm2, ratio 3.04; thin stainless: ratio 28, transfer almost negligible; model output).

**De-trending order (SPEC20).** A polynomial of order 2 removes a parabolic crown only. On a
cosine-ground roll (80 um crown on diameter, 70 degree half angle) it leaves a W-shaped residual
of 0.68 um peak to peak on radius, order 4 under 0.02 um [computed, curve form assumed; the
unit test reproduces 0.660 um and 0.006 um on a 1.7 m barrel with the strip over 0.79 of it]:
larger than the 0.3 um bump below. The default is therefore 4, and the section always reports
`detrend_sensitivity`: the bands with order 2 and with order 4, the largest difference of the
local deviation and `bands_depend_on_order`; when the bands differ (by position within the
position tolerance, or by state) the flag `ROLL_PROFILE_BANDS_DEPEND_ON_DETREND_ORDER` is set and
the report says: subtract the grinder's target curve before entering the profile, or state the
curve. **Grid (SPEC20).** A 21-station grinder report has stations 70-100 mm apart on a foil
barrel [RG16 VP, computed]; `grid` reports the largest station spacing inside the strip and the
smallest resolvable width (two samples per feature [D]), and the flag
`ROLL_PROFILE_GRID_TOO_COARSE` is set when that exceeds the observed band width, or 30 mm when
none is given (the narrow stripe of this worked case [D]): "this profile cannot show a mark
narrower than X mm; a missing band here does not mean the roll has none". No band computation
changes with the grid.

**Worked case** (`tests/test_band_roll_profile.py` keeps the 2 um crown and order 2; no demo
carries a profile): a hand profile on the battery-foil mill with an example crown of 40 um on
radius (an example from plant-level sources that cannot be defended as a default; report
section 2.2), a 0.3 um bump of 20 mm half-peak width at 0.50 m and a -0.2 um dip of 30 mm at
0.95 m, 10 mm stations, one roll, with the committed demo's shape parameters [run].
`detrend_order: 2`: the local deviation peaks at +0.258 um at 0.5025 m (half-peak width
22.7 mm) and -0.182 um at 0.9475 m; with feedback a loose band of +3.13 I-units at 0.5025 m
(latent in the mill, manifest after release) and a tight one of -2.04 at 0.9475 m (latent, flat
after release); compliance only 361 I-units, rigid bound 861. `detrend_order: 4` (the default):
+0.243 um and -0.169 um; one loose band of +2.98 I-units at 0.5025 m (latent / manifest after
release), the dip now below the reporting threshold; compliance only 341, rigid bound 811. The
two orders differ in the local deviation by up to 0.038 um, the dip's band depends on the order
and the flag is set: the parabolic crown is removed by either order, the order-4 polynomial also
takes part of the narrow dip. The 10 mm grid resolves 20 mm (no grid flag). With order 2 (the
2 um crown of the test case gives the same local deviation to 0.1 nm): **a shapemeter of 23
zones of 52 mm reads 1.18 (38 % of the peak) and -1.10 (54 %): both below 2 I-units, so the shapemeter would
probably not show a band that is there** (section 7.6; this is the narrow-band case where zone
dilution matters). Stiffness indicator: strip foundation 47.9 kN/mm2 against a roll term of
62.1 kN/mm2 at 45 mm (ratio 0.77).

Limits: one roll's ground shape, measured cold and off the mill; marks narrower than about two
grid cells or than 4a are smoothed; no wear growth during the campaign; no barrel-position
modulation by roll bending (G1). `roll_surface_band` and `grinding_feed_marks` stay rule-based
and do not read the section; it is never evidence. A report taken on a roll not thermally
settled carries a thermal profile of the size of the grinding tolerance: 3.3 um per K on a
280 mm roll [computed; rest time about a day, RG5]; grinder gauges measure diameter, so
deviations are halved for the radius input.

### 7.10 Roll surface within one revolution

The roll model of 7.1 is a circumferential mean: the temperature the oil and the strip see at
the bite is the surface value after the last spray, not the mean (gap rows A4, G8). With
`width_model.circumferential_layout` (null by default; no demo has one, because no plant value
of the angles exists) `width.roll_surface_cycle` adds a periodic surface layer per axial
station (`physicroll/roll_skin.py`) [D, re-derived in SPEC18; the reports name a Fourier method
and a "phase shift" method without equations]: one-dimensional conduction under the surface,
curvature neglected, the deep boundary at `D = 6*sqrt(a*t_rev)` held at the steady
circumferential-mean temperature; the revolution `t_rev = 2*pi*R/V_r` is a sequence of arcs:
the bite (the roll's share of the bite heat over the contact length, no cooling), the spray
arcs (coefficient `background + spray_mean_htc*weight*2*pi/phi`, so that its angular mean is
the mean model's), an optional backup-roll contact (entered conductance and backup
temperature) and air (background coefficient). 24 geometric cells, backward Euler, at least 8
steps per arc, revolutions marched until the history changes by less than 1e-3 K. The scheme
is linear, so per station `T_s - T_c = q_b*A + (T_D - T_c)*B` (+ the backup term), with `A`
and `B` computed for 9 spray weights and interpolated [D].

**Layout input.** `{"spray_arcs": [{"start_rad", "arc_rad"}], "backup_contact": null | {...},
"provenance"}`: angles in the direction of rotation measured from the bite exit; 1 to 6 spray
arcs, sorted, overlapping neither each other, the backup contact nor the bite (the bite's arc
is the case-pass contact length over the radius); a region crossing the bite or one revolution
is rejected with a message naming the two regions; when `spray_wetted_arc_rad` is entered the
spray arcs must add up to it. The result tabulates the layout used (`layout_used`) and the
report draws the three cycles against the angle.

**Checks** (`tests/test_roll_skin.py`; k 40 W/mK, `rho*c` 7850*470, R 0.135 m, 10 m/s:
`t_rev` 0.0848230 s, `e` 12148.25, skin depth 0.5410 mm): a flux `q1*cos(omega*t)` gives the
half-space amplitude `q1/(e*sqrt(omega))` = 0.95643 K for 1e5 W/m2 to 0.13 % with a lag of
45.2 degrees; a constant flux 1e7 W/m2 for 0.2 ms raises the surface by 13.154 K against the
exact 13.136 K (13.136 with 48 cells); after a step in `h` the surface covers 0.57264 of its
change at `t* = k*rho*c/h^2` (12.766 s at 3400 W/m2K) against the exact 0.5724. Cycle with a
2 mm bite at 1e7 W/m2, one spray arc from 90 to 150 degrees at 20450 W/m2K, background 50,
coolant 313.15 K, deep 330 K: 327.154 K before the bite, 340.545 K after it, lowest 325.05 K,
mean 327.06 K, mean flux -20533 W/m2 (the deep flux within 0.74 %), 60 revolutions; mean
coefficient 3450 W/m2K, effective `<h*(T_s - T_c)>/(<T_s> - T_c)` 3171.2 W/m2K, ratio 0.919:
**the circumferential-mean model over-states the cooling of this layout by 8 %**.
Superposition: `313.15 + 0.713895*16.85 + 1.966099 = 327.145 K` (converged cycle 327.145 K).
With sprays all round, averaged over a nozzle pitch, the layer mean equals the mean model
within 1 % of the surface excess in the strip interior (pointwise up to 0.4 K at the nozzle
scale and 0.5 K at the strip edges: the layer has no axial conduction).

**What it says about X3 and the "20 s" question.** The bias of the mean coefficient
(`mean_coefficient_ratio`, flag `CIRCUMFERENTIAL_MEAN_COEFFICIENT_BIASED` beyond 5 %) is the
error of the circumferential averaging for a given layout; the bulk model is not corrected with
it. The section's `time_scales` are the model's own three: one revolution (`per_revolution_s`,
the skin cycle), the surface film `k*rho*c/h_mean^2` (`surface_film_s`, a step in the spray
coefficient reaches 0.57 of its surface change) and the roll body `rho*c*R/(2*h_mean)`
(`bulk_s`), each event's duration divided by each. The published "three thermal effects" have
no numbers in the abstract read [TM-LA9 AB]. For the demos' own inputs the surface-film scale
of this model is **15.9 s** (lengthwise demo, `h_mean` 3050 W/m2K; body 121 s, revolution
0.11 s) and **12.4 s** (battery demo, 3450 W/m2K; body 72 s, revolution 0.078 s) [run, with a
scratch layout]: of the order of the plant's 20 s, as a comparison, not an explanation; the
emulation of the plant's step test that could support a claim (A6) is not built.

The case pass's computed heat partition (8.2) takes its roll entry temperature from the cycle
at the strip centre when the section exists (one pass, no iteration; flag
`ROLL_ENTRY_TEMPERATURE_FROM_SURFACE_CYCLE`; reported values only). Nothing else uses the
cycle: not the bulk, the stripes, the shape, the viscosity, the film or the flow stress. Cost:
about 2.0 s (lengthwise demo) and 1.6 s (battery demo) per diagnosis with a layout; nothing
without one.

### 7.11 What a hot roll stripe does besides growing the roll: local state

SPEC19 package 1 (gap rows A2 inputs, BT-G12, A1 / G6 computed; `physicroll/band_local.py`).
A roll stripe that is hotter than its neighbours does more than grow the roll: the oil at that
width position is warmer and thinner, the film and the friction change, the metal is softer,
and the strip leaves the bite hotter. SPEC18 built the single-station pieces (viscosity law,
friction closure, heat partition, roll surface cycle); with the optional
`width_model.local_coupling` the result gains `width.local_state`, which evaluates them at every
strip sample of the steady thermal grid. **It makes no band** (SPEC19 package 2 turns the
changes into I-units) and feeds nothing back into the bite, the heat row or the roll
temperature.

**Difference method.** Every quantity is a difference from the healthy header at the same pass,
as the radius stripes are (section 7.1): a healthy header gives zero everywhere, and the levels
(the pass friction, the inlet temperature, the film of the friction row) stay those of the pass.

The nine formulas, per strip sample `z` (`ref` = healthy header):

| # | formula | tag |
|---|---|---|
| 1 | `dT_r = T_r,actual - T_r,healthy`: the roll surface the bite meets, from `width.roll_surface_cycle` (bite entry minus the new `healthy_bite_entry_temperature_k`, same unit solutions) when a layout is entered, else the circumferential-mean surface (flag `LOCAL_STATE_FROM_CIRCUMFERENTIAL_MEAN_SURFACE_TEMPERATURE`) | [D, SPEC19] |
| 2 | `T_in = tribology.inlet_temperature_k + w_in*dT_r` | `w_in` [D, SPEC19: analyst choice] |
| 3 | `v = eta0(T_in)/eta0(T_in,ref)` with the oil's temperature law (exponential or table) | SPEC18 |
| 4 | `h_s = h_s,ref*v`, `Lambda_s = Lambda_ref*v` (the inlet film is proportional to `eta0`) | [BT-S9 EX eq. 4.1 as coded] |
| 5 | `h_sup = Q*capture*weight/(pitch*u_bar)`, `u_bar = (V_r + u_entry)/2`; `h = min(h_s, h_sup)`, `Lambda = Lambda_s*h/h_s`, starved where `h_sup < h_s` | [D, re-derived in SPEC19: volume balance] |
| 6 | `dmu = mu_cl(Lambda) - mu_cl(Lambda_ref)` with the case's closure (placeholder or load sharing); `Lambda <= 0` evaluated at 1e-6 | closure as section 8.1 |
| 7 | `dY_rel = -c_T*dT_b`, `dT_b = 0.5*eta_x*dT_r` | form: gap A2; mid-bite temperature as SPEC18 |
| 8 | `eta_x = T_x(T_r0 + 1 K) - T_x(T_r0)` from the case pass's heat partition (section 8.2); exact, the model is linear in `T_r0` | [D, SPEC19] |
| 9 | `dT_x = eta_x*dT_r`, `T_x = T_x,ref + dT_x` (`T_x,ref` the pass heating exit temperature); the change of friction heat with `dmu` is left out (second order) | [D, SPEC19] |

**The inlet weight is an assumption.** The film forms between the roll and the strip; the strip
enters at one temperature across the width, so `w_in = 0.5` is the mean of the two surfaces and
`w_in = 1` is the bound the bite report uses ("a roll surface that is locally hotter thins the
film at once", gap BT-G4 [derived]). Nobody has measured the oil temperature at the inlet
across the width; package 2 always evaluates 0, the entered value and 1.

**Oil supply (BT-G12) is a volume balance, not a starvation model.** Oil arriving per unit
barrel length `q' = Q*capture*weight/pitch` cannot form a film thicker than `q'/u_bar`. On the
battery-foil demo (10 l/min per nozzle, assumed) a healthy nozzle delivers a film of 3.42e-4 m,
3602 times the smooth inlet film (95.0 nm): a nozzle is a film band by supply only when its
level falls below 2.78e-4, that is when it is practically dry; the weak nozzle at 0.45 is not
starved (2.62e-4 m supplied under it). A fully blocked nozzle gives zero supplied film because
the model has no spreading or carry-over (flag
`ZERO_OIL_SUPPLY_UNDER_BLOCKED_NOZZLE_NO_SPREADING_MODEL`); no inlet meniscus position is
computed. So gap BT-G12 reduces to a flag (SPEC19 finding 9).

**Strip temperature (A1 computed).** `strip_exit_temperature_k` across the width goes through
the strip-temperature term of section 7.7 (`thermal_flatness`, about 2.4 I-units per K); the
supplied-scan section `width.strip_temperature` is not changed or replaced.

**Battery-foil demo** (synthetic `local_coupling`: weight 0.5, softening 0.15 %/K from the
1100-H18 strengths at 20 and 100 C [PT-T31, PT-T39; coefficient derived], 10 l/min per nozzle
assumed; no circumferential layout, so the circumferential-mean surface is used): the largest
`dT_r` is 2.358 K at 0.6225 m (the weak nozzle). There the inlet oil is 1.179 K warmer, the
viscosity ratio 0.982469, the film ratio 0.373409 (from 0.380072), the friction 3.7487e-4
higher (1.25 % of the pass friction 0.03, placeholder closure, flag
`LOCAL_FRICTION_FROM_PLACEHOLDER_CLOSURE_SLOPE`), the flow stress 0.149 % lower; the
strip-to-roll coupling is 0.8442 (contact time 0.218 ms, `C_s` 43.4 J/m2K, film conductance
1.37e6 W/m2K) and the strip leaves 1.991 K hotter (335.42 K against 333.43 K). The
strip-temperature term of this computed profile peaks at 4.06 I-units at 0.6225 m (mean
removed; -0.64 elsewhere). Planner's prototype (s25/local.py, eta.py): 2.358 K, 0.982470,
0.373410, +3.748e-4, 0.844, -1.49e-3; with weight 1.0 the ratio is 0.965246 and the friction
change +7.45e-4 (both reproduced in `tests/test_band_local.py`). Lengthwise demo (not carried by its scenario; run with a
scratch key): 1.664 K at 0.6675 m, coupling 0.510. Cost: about 0.06 s per diagnosis.

Limits: differences from the healthy header only; the inlet weight is an assumption; one-way
(the local force, slip and heat changes do not return to the roll temperature: loop I1 stays
open); friction heat change left out; no lateral spreading or carry-over of oil; roughness
uniform across the barrel (a rougher or coated zone is entered through the friction stripe
screen of section 7.8); the strip entry temperature is uniform. Flags (also on the top-level
list): `LOCAL_STATE_COMPUTED`, `LOCAL_STATE_FROM_CIRCUMFERENTIAL_MEAN_SURFACE_TEMPERATURE`,
`LOCAL_FRICTION_FROM_PLACEHOLDER_CLOSURE_SLOPE`, `OIL_SUPPLY_BELOW_SMOOTH_FILM` (a starved
station under a nozzle whose level is above 0), `ZERO_OIL_SUPPLY_UNDER_BLOCKED_NOZZLE_NO_SPREADING_MODEL`,
`LOCAL_FRICTION_CHANGE_ABOVE_20_PERCENT_LINEAR_SOURCE_INDICATIVE`.

**Second part: the local sources as a band** (SPEC19 package 2; gap rows A2, BT-G4 in full,
I2; `band_local.source_terms`, `width.local_sources`). The film and flow-stress changes act as
a local change of roll force per width at an unchanged gap, transferred as in section 7.8
[D, re-derived in SPEC17]:

```
dp0'_film(z) = M_mu*dmu(z),   dp0'_flow(z) = M_Y*Y_pass*dY_rel(z)       M = (dF/dX)/width
dh_X,k = G(lam_k)*dp0'_X,k,   G = 2*C/(1 + 2*C*Q_eff)                   (with the feedback)
I_X = 1e5*(eps_X - mean),     eps_X = -xi*dh_X/h_exit                    (flat entry)
I_T = thermal_flatness_term(z, T_x)                                     (first part)
I_roll = width.shape.steady.i_units_linear_feedback                      (before saturation)
mechanical_net = I_roll + I_film + I_flow       (what stays after the coil has cooled)
as_measured_hot = mechanical_net + I_T          (a shapemeter without temperature compensation)
```

`M_mu` and `M_Y` come from the case-pass bite: central differences of its model (+-2 % friction,
+-0.5 % flow stress) in the friction screen's own bite cache, or the analytic derivatives of the
reduced half-space bite (`bite_extras`) when that is the operating bite; the section names the
model (`sensitivities.sensitivity_bite_model`). Every term is reported **separately**, with what
it rests on (`terms_rest_on`) and the time scale it follows (`time_scales`: roll growth the roll
body, `bulk_s`; film, flow stress and strip temperature the roll surface, `surface_film_s`, both
from `roll_skin.time_scales`), and at both transfer levels (with the exit-tension feedback,
used in the sums, and compliance only). The sums are never printed alone: every band row and
event row carries the net at the inlet weights 0, entered and 1 with their sign words (`LOOSE`
/ `TIGHT` at +-2 I-units, else `BELOW_REPORTING_THRESHOLD`), `sign_depends_on_inlet_weight`,
the size of the mechanical terms against the net, and a `net_text` sentence. A term that cannot
be evaluated (no softening coefficient, no strip-to-roll coupling) counts as zero, is named in
`missing_terms`, and the sentence says "the net is incomplete" (flag
`LOCAL_NET_INCOMPLETE_TERM_MISSING`, added beside the brief's flags). Two profiles go to the
shapemeter (`local_mechanical_net`, `local_as_measured_hot`).

Battery-foil demo (regenerated artifact; `M_mu` 5.1403e7 N/m, `M_Y` 0.011165 m, load
exponents 1.609 in friction and 2.038 in flow stress, experimental mattress bite):

| I-units at the band of 0.6225 m | roll growth | film (w 0.5 / 1.0) | flow stress | strip temperature | mechanical net (w 0.5 / 1.0) | as measured hot |
|---|---|---|---|---|---|---|
| steady stripe, `dT_r` 2.36 K | +25.1 | -3.7 / -7.5 | +0.57 | +4.1 | +21.9 / +18.2 | +26.0 |
| 20 s after zone 18-19 closes, `dT_r` 6.47 K | +18.0 | -10.0 / -19.7 | +1.5 | +11.0 | +9.5 / -0.2 | +20.5 |
| planner (peak estimates, SPEC19), steady | +25.1 | -4.3 / -8.6 | +0.7 | +4.7 | +21.5 / +17.2 | +26.2 |
| planner, 20 s | +19.2 | -11.5 / -22.6 | +1.8 | +12.5 | +9.5 / -1.6 | +22.0 |

The planner used one transfer gain at the stripe's dominant wavelength and no mean removal;
the implementation works on whole profiles with the mean removed (the strip term's background
is -0.64 I-units), and its flow-stress term uses formula 7 (`0.5*eta_x*dT_r`, 0.42 of `dT_r`)
where the prototype took half of `dT_r`. Compliance only, the steady film term is -463 I-units
(planner about -590). **Read the signs, not the digits.** Roll growth makes the strip thinner
and the fibre loose; a thinner oil film raises friction and force, makes the strip thicker and
the fibre tight; softer metal lowers the force and makes it loose; a hotter fibre reads loose
while hot and that part is gone after cooling. In the steady state the net is loose with
either weight. Twenty seconds after a zone closes the surface under it is 6.5 K hotter; the
film term then nearly cancels the roll path at weight 1, and the mechanical net is +9.5 or
-0.2: its sign in the first tens of seconds depends on an input nobody has measured (SPEC19
finding 7; flag `LOCAL_NET_SIGN_DEPENDS_ON_INLET_WEIGHT`). All of it rests on the exit-tension
feedback, which an independent check does not confirm at foil gauge (SPEC19 package 8), and on
the friction-closure slope of X22. No evidence item reads these terms (open decision 2); the
steady shape, the band states, the onsets, the gauge trend and every score are unchanged.
Flags: `LOCAL_SOURCES_COMPUTED`, `LOCAL_NET_SIGN_DEPENDS_ON_INLET_WEIGHT`,
`LOCAL_SOURCES_REVERSE_A_BAND` (a roll-growth band whose net has the other sign or falls below
the threshold), `LOCAL_SOURCES_SUMMED_ON_LINEAR_PROFILE_SATURATION_NOT_APPLIED`,
`LOCAL_NET_INCOMPLETE_TERM_MISSING`. No published case of a film or flow-stress band exists
(benchmarks `NOT_ENCODED` `A2-LOCAL-SOURCES`).

### 7.12 Flatness control loop (parts)

SPEC19 package 3 (gap row G5 core; `roll_thermal.ControlledRun`, `physicroll/flatness_control.py`).
Nothing in the diagnosis uses these parts yet; SPEC19 package 4 wires them into the width
section. **The control law is the tool's own** [D, SPEC19: analyst design]: the reports give the
structure of a flatness controller in words only (least squares on actuator influence vectors,
dead bands, valve minimum on / off times, a target curve [SS-S34 EX, SS-S33 EX, SS-S31 EX]) and
no law. What the loop does is therefore what this tool simulates, not what a vendor's system or
the plant's controller does.

**Thermal run with changing valves.** `ControlledRun(roll, header, base_segment, initial=...)`
steps the roll temperature field with the operators of `simulate`; `advance(levels, duration,
time_step)` may change the nozzle levels at every call. The first step after a change is the
start-up of `simulate` (two backward-Euler half steps), the others Peaceman-Rachford steps.
Driven with the levels of a list of segments it reproduces `simulate` bit for bit (the test asks
1e-12 K and m and the energy ledger to 1e-9). Cost on the battery-foil roll (300 x 16 cells):
about 1.9 ms per step, 0.11 s per simulated minute at 1 s steps [run], against 12 ms for each
call of `simulate`.

**Control law** (per control zone: a demand, a valve level, the time of its last change):

1. zone error `e = reading - target` (zones without strip left out);
2. supplied actuators (the interface for the bender and tilt of Phase 3; not modelled here):
   their least-squares part is removed, settings clipped to their limits;
3. the low-order part (order 2: mean, tilt, parabola) is removed "as if by ideal bending and
   tilt"; its coefficients are reported, never controlled;
4. correction `d = G*rho`, `G = (B^T W B + lam*I)^-1 B^T W` with the influence matrix `B` of
   the spray zones (one-sided difference of steady readings per unit level; the diagonal is
   negative: more cooling, smaller roll, tight fibre) and `lam = 0.01 x max diag(B^T W B)`;
5. dead band: a correction whose largest reading change is within the dead band is dropped;
6. demand `u* <- clip(u* - 0.1*d, lowest, highest level)`;
7. the valve takes the allowed level nearest the demand only if it is closer by more than 0.1 of
   the step between the levels and the valve has held its level for the minimum on time (after
   going up) or off time (after going down).

The three analyst constants (integral gain 0.1, hysteresis 0.1, regularisation 0.01) are
[D, SPEC19: analyst choice] and are named in the result's `basis`. The loop runs on a fixed
control interval over a fixed horizon (no adaptive step, no wall-clock limit) with an optional
transport delay and display filter; its status is `SETTLED` (no valve change in the last
window), `TRIMMING_WITHIN_BAND` (changes, but the largest residual there within 3 x the dead
band) or `NOT_SETTLED`, with the flags `CONTROL_INCREASES_RESIDUAL` and `CONTROL_ZONE_AT_LIMIT`.
A loop that does not settle is a result, never an error, and the dwell times bound the valve
changes by horizon / dwell per zone. On a synthetic first-order plant (four zones, diagonal
influence -10 I-units per unit level, time constant 20 s, a demand of 0.5) valves in 5 % steps
settle and two-level valves switch at the dwell bound without settling
(`tests/test_flatness_control.py`); the mill numbers are those of package 4.

## 8. Process models

Integration code: `physicroll/band_process.py`; equations: `physicroll/bite_tribology.py`.
These sections appear only in v2 cases with `tribology` and/or `hardening`.

### 8.1 Lubricant, film and friction

```
eta0(T) = eta_ref*exp(-beta*(T - T_ref)),   eta(T,p) = eta0(T)*exp(alpha*p)                 [D]
h_s = 6*eta0*alpha*U_mean/(theta0*(1 - exp(-alpha*(Y_ps - sigma_back))))                     [V restated]
U_mean = (u_roll + u_strip_entry)/2,  theta0 = sqrt((h_entry - h_exit)/R_c) [D],  Y_ps = 2Y/sqrt(3)
R_c = R' (Hitchcock arc) or R (mattress bite: undeformed roll)                [BT-S3 EX; D, SPEC17]
Lambda = h_s/sqrt(Rq_roll^2 + Rq_strip^2)
  MIXED_SUBSTANTIAL_CONTACT < 1 <= MIXED_FIRST_CONTACT <= 3 < HYDRODYNAMIC   [V: Sutcliffe 2002; BT-S9 EX]
  common industrial window 0.01 <= Lambda <= 0.5                             [BT-S3 EX, BT-S9 EX]
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
`mu_v` = 0.008 [D within 0.005-0.01]; `Lambda0` = 1.0 [D]. Its end values 0.09 and 0.008
match the one abstract on aluminium [BT-S6 AB], but it keeps friction near 0.09 over most of
the common industrial window, so **neither its level nor its slope with speed is supported**
(only the slope was ever meant to be used, and that is not supported either). The computed friction is shown beside the supplied one and replaces it
only with `tribology.use_computed_friction: true` (then by a fixed point friction -> bite ->
contact radius -> friction).

Lengthwise demo (`process.friction`, `process.friction_speed_curve`): final pass film
70.3 nm, film ratio 0.180, `MIXED_SUBSTANTIAL_CONTACT`; placeholder friction 0.0765 against
0.03 supplied (not used); slope -1.03e-3 per m/s at 12 m/s, mean -1.01e-3 per m/s between 2
and 25 m/s. Every schedule pass has a film ratio below 1 (0.0139 to 0.180).

**Two corrections of SPEC17.** (1) Regime labels (BT-G8, X21): a film ratio below 1 was
labelled `BOUNDARY`. In the sources it is the condition for a good roll imprint inside the
mixed regime, and 0.01-0.5 is the common industrial window [BT-S3 EX, BT-S9 EX]; no source
read gives a film-ratio threshold for boundary lubrication, so no result carries that label.
The labels are `MIXED_SUBSTANTIAL_CONTACT` (< 1), `MIXED_FIRST_CONTACT` (1-3) and
`HYDRODYNAMIC` (> 3), with `in_common_industrial_window` beside every film ratio. (2) Inlet
angle (BT-G7, X23): for a mattress bite the film used `R*contact_radius_ratio`, but that ratio
is `L^2/(R*draft)`, not a radius, so the angle was `draft/L`, the mean slope of the whole bite.
The literature uses the undeformed-roll inlet slope [BT-S3 EX]: for a bite
`h = h1 + x^2/R_c` the inlet slope of each roll is `sqrt(draft/R_c)` [D, re-derived in
SPEC17], with `R_c = R` for a mattress bite and `R'` (unchanged) for a Hitchcock bite
(`band_process.film_radius_ratio`; key `inlet_angle_basis` in the results). The film was
over-stated by `sqrt(contact_radius_ratio)`. Battery-foil demo, before -> after (regenerated
artifact): case pass F1 film ratio 0.551 -> 0.380, film 137.9 -> 95.0 nm, placeholder friction
0.0552 -> 0.0641 (not used); F2 / ALT1 / ALT2 film ratio 0.647 / 0.444 / 0.979 -> 0.356 /
0.296 / 0.293; screen film ratio 0.564 -> 0.389, inlet angle 8.39e-3 -> 1.217e-2 rad; mean
friction-speed slope -2.04e-3 -> -1.65e-3 per m/s; speed-consistent critical speed 16.29 ->
16.77 m/s (beta 0.5), and without bite damping from "unstable at the lowest assessable speed"
to 5.16 m/s; speed-change gauge shift -8.28 -> -6.48 um. S1-S3 (Hitchcock) and the whole
lengthwise demo keep their film numbers; the demos use `use_computed_friction: false`, so no
bite or force moves.

**Oil properties (SPEC18 package 5, all optional; nothing changes unless a case enters them).**

| oil property | what is available | read tag | how the tool uses it |
|---|---|---|---|
| viscosity against temperature | data-sheet points of your oil; one published example (below) | data sheet; E6 FT | `tribology.lubricant.viscosity_table`: `ln eta0` linear in T between the points, the end slope outside [D] (flags `VISCOSITY_FROM_TABLE`, `VISCOSITY_TABLE_EXTRAPOLATED`); the single value and rate are then not used for `eta0` |
| viscosity against pressure | Barus (default); Roelands `eta = eta0*exp{(ln eta0 + 9.67)*[(1 + p/196.2 MPa)^z - 1]}`, `z` entered or `196.2 MPa*alpha/(ln eta0 + 9.67)` | E5 FT (L.3), (4.194) | `pressure_law: "roelands"` (flag `ROELANDS_PRESSURE_LAW`) changes the viscosity at pressure only; the inlet film formula keeps its Barus closed form |
| Eyring stress | 4.5 / 6.0 / 11.7 MPa at 625 / 945 / 1510 MPa and 40 C for one kerosine base oil | E6 FT | `eyring_stress_pa` + `eyring_stress_pressure_coefficient*p`: supplied only, no default |
| limiting shear stress | no value in any source; for that oil none was seen up to 0.045 of the pressure | E6 FT | `limiting_shear_stress_pa` + `limiting_shear_pressure_coefficient*p`: supplied only; below 0.045 of the mean pressure the flag `LIMITING_SHEAR_BELOW_PUBLISHED_LOWER_BOUND` |
| oil conductivity | 0.125 W/mK at ambient pressure (assumed equal to another oil by the source), 0.25 W/mK in the nip | E6 FT | context for the heat partition (a later package) |

What to enter: the viscosity table and the pressure coefficient come from your oil supplier's
data sheet. The published example (`bite_tribology.EXAMPLE_KEROSINE_BASE_OIL`, Somentor 31,
every value tagged [E6 FT]) is a base oil with no additives, not the rolling oil of a plant: it
illustrates the inputs and is never a default.

**Which pressure law.** The one foil-rolling oil with published high-pressure data
(`A9-PRESSURE-LAWS-KEROSINE`, 40 C, `eta0` 1.409e-3 Pa s, `alpha` 10.40e-9 /Pa, `z` 0.657):

| pressure [MPa] | measured [Pa s] (E6 FT) | Barus (ratio) | Roelands (ratio) |
|---|---|---|---|
| 100 (viscometer) | 3.985e-3 | 3.986e-3 (1.000) | 3.699e-3 (0.928) |
| 625 (disc machine) | 2.5 | 0.937 (0.375) | 0.180 (0.072) |
| 945 | 15.0 | 26.1 (1.742) | 1.228 (0.082) |
| 1510 | 740 | 9313 (12.6) | 24.4 (0.033) |

Neither law carries this oil from the inlet to bite pressure; the textbook Roelands law with
the index from the low-pressure slope is low by a factor 12 to 30 there (the thesis says the
same of its own fit). Barus therefore stays the default and Roelands is an option; every
result names the law used (`viscosity_law` in the friction rows when it is not the default).
If you need the viscosity at bite pressure, enter `roelands_z` or a Barus coefficient fitted
at the pressure of interest, and read any friction built on it as an order of magnitude.

The film formula is also compared with the published table of a foil pass
(`BT-G3-FILM-E6-T42`: 0.3242 / 0.1081 / 0.0540 / 0.0324 / 0.0108 um at 30 / 10 / 5 / 3 / 1 m/s
against 0.323 / 0.108 / 0.054 / 0.032 / 0.011, with one assumed speed ratio) and with the
film ratios of another (`BT-V4-FILM`: 0.209 and 1.675 against 0.22 and 1.76 at 5 and 40 m/s,
speeds and inlet temperature assumed) [run]: the same closed form, not a check of the film
physics.

**The second friction law: load sharing on a published curve (SPEC18 package 6, opt-in:
`tribology.friction_closure.model: "load_sharing_curve"`).** `mu = A*mu_c + (1 - A)*mu_v`
[BT-S9 EX; E7 FT]: `A` is the share of the surface where roll and strip touch, read from a
curve of `A` against the film ratio; `mu_c` the friction on those contacts; `mu_v` the friction
of the oil between them (`valley_model`: `constant` = `mu_v` 0.008, `eyring` = the Eyring shear
of the valley film [E6 FT (4.32)], `newtonian_capped` = a Newtonian shear capped at the oil's
limiting stress; the last two need the oil data of package 5 and the bite's mean pressure and
sliding speed). The default curve is the only published one: five points of contact ratio
against film ratio for one foil pass (20 -> 15 um, roughness 0.1 um, wavelength 15 um, one oil)
[E6 FT, Table 4.2], interpolated linearly in `ln(Lambda)`; outside its range (0.14 to 2.37) the
end value is held, not extrapolated, with the flag `FILM_RATIO_OUTSIDE_CONTACT_RATIO_CURVE`.

| film ratio | contact ratio | load sharing, `mu_c` 0.09 (slope) | load sharing, `mu_c` 0.03 (slope) | placeholder (slope) |
|---|---|---|---|---|
| 0.1 (below the curve) | 0.880 | 0.0802 (0) | 0.0274 (0) | 0.0822 (-0.074) |
| 0.2 | 0.808 | 0.0743 (-0.082) | 0.0258 (-0.022) | 0.0751 (-0.067) |
| 0.380 (battery-foil case pass) | 0.670 | 0.0629 (-0.081) | 0.0227 (-0.022) | 0.0641 (-0.056) |
| 0.5 | 0.566 | 0.0544 (-0.062) | 0.0205 (-0.017) | 0.0577 (-0.050) |
| 1.0 | 0.271 | 0.0302 (-0.025) | 0.0140 (-0.007) | 0.0382 (-0.030) |
| 2.0 | 0.061 | 0.0130 (-0.012) | 0.0094 (-0.003) | 0.0191 (-0.011) |
| 3.0 (above the curve) | 0.010 | 0.0088 (0) | 0.0082 (0) | 0.0121 (-0.004) |

[run, `tests/test_bite_tribology.py`] **The contact friction must be entered; there is no
default.** The sources give 0.013 to 0.1 (a boundary-film shear strength over pressure 0.013 to
0.036 [E6 FT p.72, derived], 0.09 [BT-S6 AB], 0.1 or a factor 0.25 [E4 EX]); the demo's
supplied 0.03 at its film ratio needs `mu_c` 0.041, 0.027 needs 0.036. It is best taken from
your mill's own records: measured roll force, torque or forward slip (friction identification,
a later package), or a strip-drawing test with your oil and roll finish. A missing value is a
validation error that says so.

**What this closure is and is not.** It is a REDUCED closure, not a mixed-lubrication model:
its shape is the published curve and its level is your entered number, so read the change of
friction with speed, not the level. Because the published curve is its INPUT, it returns the
published contact ratios exactly at the five points; that is a software identity, not a
benchmark, and no independent published friction value exists to compare it with. The
inlet analysis that would compute the curve is not built: the transcribed height-distribution
relation gives 0.91 to 0.50 of the source table's own mean film, and the four transcribed
asperity-crushing laws differ by up to two orders of magnitude away from one point
(`BT-G3-CRUSHING-LAWS`; `physicroll/asperity_contact.py` holds them as tested functions that
nothing uses). The film ratio entered is the smooth inlet film over the composite roughness,
while the table's abscissa came from the thesis's full inlet integration (its own closed-form
film is 0.79 to 1.36 of that), so the abscissa carries that much mismatch. The curve belongs
to one foil pass: another roughness, oil, wavelength or reduction has another curve.

**X22 answered.** The placeholder's level and slope have no support; the new closure has a
published shape for one foil pass and an entered level. Under the option every place that
takes friction from the closure uses it: the friction rows and the fixed point (with either
bite model), the friction-speed curve and its slope in the speed-consistent critical speed
(floored at the closure's valley friction), the speed-change gauge shift, the friction stripe
screen's conversion block; each says so (`status`, flags, `friction_closure` /
`closure_note` keys). Pass heating takes the friction used for the pass, which is the closure's
only when `tribology.use_computed_friction` replaces the supplied value.

### 8.2 Pass heating

```
w_pl = (2/sqrt(3))*Y_mean*ln(h_entry/h_exit)        [D]   (homogeneous, no redundant shear)
Q = w_pl*h_exit*u_exit + P_friction                  [D]   per unit width [W/m]
T_exit = T_entry + f_s*Q/(rho*c*h_exit*u_exit),  rho*c = 2.43e6 J/(m3 K)   [D]
each work roll receives (1 - f_s)/2 of Q             [D]
```

`P_friction` is the interface slip dissipation of the slab (or mattress) solution. The
strip heat fraction `f_s` is **supplied** (a computed one is reported beside it, below): foil mills put 0.11-0.33 of the
bite heat into the foil [V abstract: Yin et al. 2003]; thicker strip keeps much more [M]. The
roll heat fraction derived from it drives the roll thermal model, so the stripe heights scale
with this guess. Lengthwise demo (`process.heating.operating`): plastic power 293 kW/m,
friction power 113 kW/m, total 406 kW/m; strip 313.15 -> 368.9 K (+55.7 K); 32.5 kW/m to each
work roll.

**Computed heat partition (SPEC18 package 9, gap row A3).** Beside the entered share each
heating row carries `heat_partition`: the strip's share computed by an interface model
(`bite_tribology.heat_partition`) [D, re-derived in SPEC18; the gap row's series formula
`q = (T_s - T_r)/(1/h_c + sqrt(pi*t)/(2*e))` is its time-averaged form]. One roll side per unit
contact area, over the contact time `t_c = l_d/V_r`: a lumped strip of capacity
`C_s = rho_c*h1*u1/(2*V_r)` (half the neutral thickness per side) on a roll that is a half-space
(effusivity `e = sqrt(k*rho*c)`), coupled through the interface conductance `h_c`; plastic heat
`P_pl/(2*l_d)` released in the strip, friction heat `P_f/(2*l_d)` at the interface with **half
of it released on the strip side of the film (phi = 0.5) [D, SPEC18 analyst choice]**. 400
time steps, the half-space response exact for a flux constant over a step, the strip by
backward Euler; the share is `f_s = C_s*(T_s(t_c) - T_e)/(heat input)`, reported as computed
even outside [0, 1] (flag `HEAT_SHARE_OUTSIDE_0_1_TEMPERATURE_DIFFERENCE_DOMINATES`). With
perfect contact and equal entry temperatures it has the closed form
`T(t) = (g/e)*(2*sqrt(t/pi) - sqrt(tau)*(1 - exp(t/tau)*erfc(sqrt(t/tau))))`, `tau = (C_s/e)^2`
(`perfect_contact_strip_share`, the test of the scheme).

Inputs in the engine: contact length and forward slip of the pass's bite; the film thickness
of the pass's friction row (smooth inlet film at that bite with the case's friction closure;
the row's `interface_conductance_basis` names the bite model and the closure); `h_c =
k_oil/h_film` [row A3] with the oil conductivity of the case (default 0.13 W/mK [M], unchanged),
or `tribology.interface_conductance_w_m2k` when entered (1e3 to 1e9; models use 25-40 kW/m2K,
measurements span 7-800 [PT-T34]); roll properties of `width_model.roll` (else the defaults of
`roll_thermal.RollThermalProperties`); roll surface at bite entry = the coolant temperature
(else the oil inlet temperature), flag `ROLL_ENTRY_TEMPERATURE_ASSUMED_COOLANT_OR_OIL`. The
row also gives the share at the two published conductivities of a kerosine foil base oil,
**0.125 W/mK at ambient pressure and 0.25 W/mK in the nip [E6 FT]**
(`strip_heat_fraction_at_published_oil_conductivities`). No interface-conductance
correlation is coded: a mixed-lubrication conductance model was found only as a publisher
preview without its equations (E12 AB), the Tseng papers as abstracts (E14 AB), and the
Cooper-Mikic-Yovanovich correlation on teaching pages (E13 VP), where it is a correlation for
dry rough contacts at far lower pressures than a roll bite. The gap row's "asperity term" has
no formula in the reports and is not built.

Worked numbers (the thermal report's check case: steel `k` 43 W/mK, `rho*c` 3.6e6 J/m3K,
24 um, `t_c` 0.2 ms; `C_s` 29.16 J/m2K, `tau` 5.4929e-6 s): perfect contact 0.162070 (the
scheme 0.162060 / 0.162069 / 0.162070 with 50 / 400 / 800 steps; the report's capacity-ratio
estimate gives 0.128); a 70 nm film with 0.13 W/mK 0.2254, 200 nm 0.3352, 40 kW/m2K 0.8775,
60 % plastic and 40 % friction heat at 70 nm 0.2113; with 0.125 W/mK 0.2279 (70 nm) and
0.3414 (200 nm), with 0.25 W/mK 0.1952 and 0.2553. The roll's transient resistance
`sqrt(pi*t_c)/(2e)` is 1.0073e-6 m2K/W against 5.385e-7 for the 70 nm film: the roll, not the
film, limits the heat flow. Sheet check, 0.25 mm and 0.4 ms, perfect contact: 0.6063.
Benchmark `TM-LA19-HEAT-SPLIT`: 0.1621, 0.2279 and 0.1952, inside the measured 0.11-0.33
(film and conductivity assumed).

**The entered share keeps driving every result** unless `tribology.use_computed_heat_partition`
is true: then pass heating uses `min(1, max(0, f_s))` of each pass (flag
`STRIP_HEAT_FRACTION_COMPUTED_FROM_INTERFACE_MODEL` instead of
`STRIP_HEAT_FRACTION_SUPPLIED_NOT_COMPUTED`) and the width model's default roll heat fraction
becomes the case pass's computed `(1 - f_s)/2` (basis "computed"). Otherwise each heating row
gains `supplied_minus_computed_strip_heat_fraction`, `width.thermal_sensitivity.
computed_strip_share` shows the computed share beside the rows (which keep their own shares) and
`thermal_check.computed_heat_partition` states both and the measured range.

**X4.** The entered 0.84 of the sheet demo is not supported: the computed value for that pass is
0.662 (0.663 / 0.638 at the published oil conductivities; earlier passes 0.73 to 0.78) [run,
`artifacts/band_diagnosis/lengthwise-bands-demo.result.json`]. For the battery demo the computed
share of the case pass F1 is 0.338 against the entered 0.22 (F2 0.210, ALT2 0.117); the stripe
heights stay those of the entered 0.22.

### 8.3 Work hardening

Equivalent strain `eps = prior + (2/sqrt(3))*ln(h_ref/h)` (as `physicroll.materials`). Laws:
power `sigma = sigma_y + K*eps^n` and a generalised Voce law with a stage-IV term
`sigma = s0 + (ss - s0)*(1 - exp(-eps/eps_c)) + theta4*eps` [D form; Hirsch et al., Ryen et
al. 2006, read second-hand], with the analytic pass mean. Strain-rate sensitivity is taken as
zero [M] unless a rate and temperature factor is entered (below). Literature fits shipped for reference:

| fit id | alloy, temper | law | yield [MPa] | K [MPa] | n | tag |
|---|---|---|---|---|---|---|
| `1100-O_kalpakjian` | 1100-O | Hollomon | 0 | 180 | 0.20 | [V via secondary source] |
| `5052-O_kalpakjian` | 5052-O | Hollomon | 0 | 210 | 0.13 | [V via secondary source] |
| `1050-annealed_batorfi` | 1050 annealed | Ludwik | 15.3 | 144.6 | 0.37 | [V: Batorfi et al. 2023] |

Warning carried with every fit: tensile-fitted power laws over-predict beyond `eps` about 0.3
[V: Kazaoka et al. 2015] and are not calibrated for rolling; a final pass of a schedule reaches
`eps` well above 2. The demo Voce parameters are synthetic (not fitted); final-pass flow
stress 282.6 MPa computed against 270 MPa supplied (`process.flow_stress`).

Hardening and softening data found by alloy group (gap study B3) and the anisotropy table
(B4) are in `docs/thin-gauge-products.md` ("Alloy groups: hardening and softening data found",
"Anisotropy and the plane-strain factor"; `band_products.alloy_group_reference`,
`anisotropy_reference`). They are tables only: nothing is fitted or passed to a hardening law
or a bite. A positive stage-IV slope is wrong in sign for purified Al-Fe and high-purity
grades beyond 80 % reduction [TM-LB2 EX] (gap study X2); since SPEC18 package 8 the slope may
be entered negative (below). The plane-strain
factor stays the isotropic `2/sqrt(3)`; the r-values 0.2 / 1.5 / 1.1 of one 16 um 1235-H18 foil
[TM-LB1 EX] would move it by -12 % to +1 % under Hill's 1948 criterion
(`plane_strain_factor_hill48`, [D, re-derived in SPEC17]); Hill-type criteria are known to be
poor for aluminium [M].

**Strain rate and temperature (SPEC18 package 8, gap rows B1 and X1).** The optional
`hardening.rate_temperature` (null by default; no demo has one) multiplies the computed flow
stress of each pass by

    factor = (rate/rate_ref)^m(T) * (1 - c_T*(T - T_ref)),   m(T) = m + dm/dT*(T - T_ref) >= 0

[form: TM report gap B1, "as the minimum"]; keys `rate_sensitivity`,
`reference_strain_rate_per_s`, `temperature_coefficient_per_k`, `reference_temperature_k`,
`rate_sensitivity_slope_per_k`, `provenance`, `use_rate_temperature` (true needs
`use_computed_flow_stress`). There is no default number: what has been measured, each with its
source, is

| quantity | value | conditions | source |
|---|---|---|---|
| rate sensitivity m | about 0.027 | 16 um 1235-H18 foil, 1e-5 to 1e-2 /s | TM-LB1 EX |
| m against temperature | 0.04 at 100 C, 0.07 at 200 C | 1050-H14, slow tensile tests | TM-LB10 EX |
| c_T | 0.0015 to 0.0019 /K | 1100-H18: 165 -> 145 and 150 -> 130 MPa between about 20 and 100 C, 165 -> 125 MPa at 150 C | [D from PT-T31, PT-T39]; the report states 0.15-0.3 %/K |

Worked numbers: `(1e-2/1e-5)^0.027 = 1.205036` (160 -> 192.806 MPa over the measured range;
the source reads "about 200"); `(2.6e3/1e-3)^0.027 = 1.490062` (the report's "about 1.5");
`c_T` 1.5152e-3, 1.6667e-3 and 1.8648e-3 /K from the three pairs above; at 10 m/s, contact
length 2 mm and 30 -> 18 um the mean bite strain rate `(u/l_d)*ln(h0/h1)` is 2554.128 /s, the
rate factor (m 0.027, reference 1e-3 /s) 1.489346 and, with `c_T` 0.0015 and 60 K above the
reference, the combined factor 1.355305. **The measurement stops at 1e-2 /s; rolling rates are
five decades higher** (flag `RATE_SENSITIVITY_EXTRAPOLATED_BEYOND_MEASURED_RATES` on every real
pass, by design). Rate raises and temperature lowers the flow stress: **the net of rate and
temperature at rolling conditions is not known; enter both or neither.**

Each row of `process.flow_stress.passes` then carries `strain_rate_per_s` (contact length of
the undeformed arc `sqrt(R*(h0 - h1))`, flag `STRAIN_RATE_FROM_UNDEFORMED_ARC`: strain rate
from the undeformed arc, which avoids a fixed point with the bite [D, SPEC18]),
`bite_temperature_k` (strip entry temperature plus half the strip's share of the plastic work
of the unfactored flow stress, the mid-bite strip temperature [D, SPEC18]; without `tribology`
the reference temperature and flag `BITE_TEMPERATURE_NOT_AVAILABLE_REFERENCE_USED`; the
computed heat partition of package 9 is not used here), `rate_factor`, `temperature_factor`,
`rate_temperature_factor` and `flow_stress_with_rate_temperature_pa`; a factor outside 0.2 to
5 is not used (`rate_temperature_rejected`, flag `RATE_TEMPERATURE_FACTOR_REJECTED`). With
`use_rate_temperature` true the factored value becomes the pass flow stress (flag
`FLOW_STRESS_RATE_TEMPERATURE_FACTOR_APPLIED`, also at the top level). Which consumers take it
(`process.flow_stress.rate_temperature.consumers`):

| consumer | uses the factored flow stress | how the result shows it |
|---|---|---|
| `schedule_flow_stress` | no | unchanged; its `STRAIN_RATE_SENSITIVITY_IGNORED` stays in its own result |
| every bite model (Hitchcock, mattress, half-space), case pass and schedule | yes | the effective pass flow stress (`effective_inputs`, `used_mean_flow_stress_pa`) |
| bite sensitivities | yes, perturbed about it | the rate term is not a force term of the stability calculation; `chatter.rate_sensitivity_damping` reports it (section 11.4) |
| speed-change gauge shift | yes, through the bite | the factor is not re-evaluated at the changed speed |
| pass heating | yes | plastic work from the effective flow stress |
| shape inputs and yield checks | yes | through the bite and the effective flow stress |
| the bite temperature of the factor | no | plastic work from the unfactored flow stress |

**Law forms (B2, X2).** The late (stage-IV) slope of the Voce law may be negative (down to
-5e9 Pa; the flow stress must stay positive up to strain 10), for the work softening of
purified-matrix Al-Fe and high-purity grades beyond 80 % reduction [TM-LB2 EX]; flag
`NEGATIVE_LATE_HARDENING_SLOPE_WORK_SOFTENING`. A second form, `law: tome_voce`,
`sigma = (s_v + theta4*eps)*(1 - exp(-theta0*eps/s_v))` [form: TM-LB4 EX] (keys
`saturation_scale_pa`, `stage_iv_slope_pa`, `initial_hardening_rate_pa`; pass mean by
composite Simpson with 64 panels [D]: within 1e-9 of 512 panels on passes away from the steep
start, 2e-7 to 5e-7 on a first pass from zero strain with `theta0/s_v` 13). Nothing selects a
law by alloy group: `process.flow_stress.alloy_group_context` gives the X2 sentence and no
table row, because the alloy-group table has no alloy matching of its own. No recovery term:
the gap row gives no formula for it. The logarithmic rate law of E10 is not added (no parameter
set for a foil alloy).

**Fit to pass strengths.** `python -m physicroll.band_cli --fit-hardening FILE.json` (keys
`gauges_m`, `strengths_pa`, `reference_thickness_m`, `prior_equivalent_strain`) fits the
generalised Voce law (`bite_tribology.fit_voce_to_pass_strengths`): for 60 characteristic
strains from 0.05 to 5 the law is linear in `(s0, d, theta4)` and solved by least squares
(`theta4` 0 with 3 points), the best one refined by repeated parabolas in `ln(eps_c)` (one
parabola leaves `theta4` about 1e-3 off on exact data). It prints the parameters, residuals,
RMS, the sign of the late slope and flags (`FIT_TO_ENTERED_STRENGTHS_NOT_VERIFIED`,
`FIT_UNDERDETERMINED_FEWER_THAN_5_POINTS`, `TENSILE_STRENGTH_USED_AS_FLOW_STRESS`: an
as-rolled tensile strength of a hard temper is taken as the flow stress at that strain [D]);
with fewer than 3 points it refuses (`NOT_FITTED`, outcome
`UNDERDETERMINED_FEWER_POINTS_THAN_PARAMETERS`) and returns no number. Nothing is written into
a case.

### 8.4 Speed-consistent chatter critical speed

With friction falling as speed rises, the critical speed is the speed `u` with
`u = u_crit(mu(u))` [D], where `mu(u) = mu_used + [mu_closure(u) - mu_closure(u_op)]` (the
placeholder supplies the slope, the operating friction the level), scanned and bisected in
log speed with the inlet-angle radius of the film (section 8.1) and forward slip held at
the operating bite. The perturbed
bites use the operating bite's model (review fix; section 10.2); scan speeds that model cannot
solve are rejected rows, and when the lowest assessable speed is already unstable the status
is `UNSTABLE_AT_LOWEST_ASSESSABLE_SPEED` with `lowest_assessable_exit_speed_m_s` (the crossing
lies at or below it), never a crossing. Lengthwise demo (`chatter.speed_consistent`): the
higher placeholder friction below the operating speed makes Hitchcock reject the slow scan
speeds, and at the lowest assessable speed, 19.9 m/s, the pass is already unstable with
and without bite damping, so no speed-consistent critical speed is given (fixed friction
0.03: 13.85 m/s, beta 0.5; 5.16 m/s, beta 0). Before the fix those slow scan speeds fell back
to the mattress model and gave 13.30 and 8.79 m/s, mixing the two bite models.

### 8.5 Friction from load, torque and forward slip

`measurement.pass_records` (case schema v2, null by default; no demo has records) takes 1 to 8
records of a measured pass: `label`, `separating_force_n` and `provenance` (required),
`forward_slip_fraction` (-0.2 to 1) and `torque_per_work_roll_nm` (optional), the pass values
that differ from the case pass (`exit_speed_m_s`, gauges, tensions, `mean_flow_stress_pa`; null
takes the case pass) and three uncertainties: force 5 %, slip 0.01 absolute and torque 10 % by
default (analyst choices [D], stated in the result). The result is
`process.friction_identification`; it is REPORTED only: no pass, lever, sensitivity or evidence
item uses it, and `declaration.calibrated` stays false because the tool cannot verify the
entered numbers. To use a value, enter it as `pass.friction_coefficient`.

**Method.** Each record is solved with the bite model of the operating bite (Hitchcock, the
experimental mattress bite or the reduced half-space bite; `bite_model` in the result), one
nominal solve at a time (`_BiteCache.state`, no sensitivities):

1. `friction_from_force`: the friction whose model force equals the measured force (secant in
   `ln mu` from the case friction, tolerance 1e-4 relative in force, at most 12 solves, inside
   0.003 to 0.3; otherwise `NOT_FOUND` with the reason).
2. `friction_from_slip`, `friction_from_torque`: the same for the measured slip and torque, on a
   9-point scan from 0.4 to 2.5 times the friction from force, the root nearest it refined by
   regula falsi; `multiple_roots` when the scan holds several.
3. `friction_joint`: the minimiser of the sum of squared normalised residuals (force and torque
   in `ln`, slip absolute, each divided by its uncertainty) over the scan, refined by repeated
   parabolas; `consistent` when every normalised residual is at most 2 in magnitude. (One
   parabola through the scan points, as first specified, lands 6 % off on exact half-space data
   and is repeated until it moves less than 1e-4 in `ln mu`.)
4. `friction_and_flow_stress`: with force and slip, the pair (friction, flow-stress scale)
   that reproduces both exactly (Newton, scale 0.5 to 2) - two unknowns from two numbers: there
   is no redundancy to check them.
5. `load_exponent_in_friction`, `slip_exponent_in_friction` (and the torque exponent) at the
   friction from force, by central differences at +-1 %.

Every single-quantity value carries a first-order interval `mu*exp(+-u)`, `u` = the entered
uncertainty divided by the local sensitivity `|d(quantity)/d ln mu|` [D, first-order
propagation]. `agreement.outcome` names the result: `MEASUREMENTS_AGREE` (joint fit
consistent and every pair within twice its combined uncertainty), `MEASUREMENTS_CONTRADICT`,
`SINGLE_MEASUREMENT` or `FORCE_NOT_MATCHED`.

**What a disagreement means.** The three values come from one constant-friction bite. When they
disagree, either a measurement is off or the bite cannot reproduce the pass with one friction
value: foil forward slip is over-estimated by constant friction, and a friction varying
through the bite is the published remedy [BT-S5 AB] (not built). A slip residual above 2 at the
friction from force gives `MEASURED_SLIP_NOT_REPRODUCED_BY_CONSTANT_FRICTION_BITE`. An
identified friction also absorbs the bite model's own error: on the published foil case the
printed model gives W_bar 78 to 134 depending on an unstated end length, about 12 % in a
friction from load and 30 % in one from slip.

**Which measurement carries the friction information.** It depends on the regime (reduced
half-space bite [run], `tests/test_band_friction_identification.py`):

| case | structure | load exponent | forward-slip exponent |
|---|---|---|---|
| published foil case, 20 -> 15 um, friction 0.03, strip spring 80 GPa | A B F | 2.461 | 0.378 |
| same, strip rigid in thickness | A B E F | 2.455 | 0.436 |
| BT-V2, 73 -> 31.39 um, friction 0.026, R 89 mm | A F | 1.570 | 2.473 |

With a no-slip zone the forward slip hardly depends on friction; the force is the better
indicator there (flag `FORWARD_SLIP_INSENSITIVE_TO_FRICTION_IN_THIS_REGIME` when the slip
exponent is below 0.5, and the slip value is marked `weakly_determined`: its interval is several
times wider than the force-based one). Without a no-slip zone the slip is the sharper indicator.
The forward slip of the reduced half-space bite is defined to elastic order only (section 10);
records whose bite carries `NO_SLIP_ZONE_CREEP_ABOVE_ONE_PERCENT` add that limitation.

**BT-V2 inverted** (benchmark `BT-V2-FRICTION-HS`): the reduced half-space bite reproduces the
measured W_bar 58 with friction 0.03063 for an assumed roll radius of 89 mm (forward slip
0.1965; 4 solves) and 0.02488 for 135 mm (slip 0.2594; 5 solves), ratios 1.178 and 0.957 to the
0.026 the source infers with its own model ("about 0.03" from mill tests [BT-S1 FT]); verdict
`INDICATIVE_ASSUMED_INPUTS`. (The root itself is 0.030636; the secant stops at 1e-4 in force.)

**Summary and contact friction.** `summary` lists the frictions from force, their median and
spread, and with two or more exit speeds the least-squares slope `d mu / d ln(u)`; the flag
`IDENTIFIED_FRICTION_DIFFERS_FROM_CASE_FRICTION` marks a median more than 20 % from the case
friction. With `tribology`, each record gets the film ratio of the bite at its friction, the
contact ratio `A` of the closure's curve (the published one by default, section 8.1) and the
contact friction `mu_c = (mu - (1 - A)*mu_v)/A` (constant valley friction, 0.008 by default;
null below `A` 0.05) [D, SPEC18: package 6's load sharing solved for the contact friction]: for
example friction 0.03 at film ratio 0.380072 gives `A` 0.6695 and `mu_c` 0.04086.
`suggested_contact_friction` is their median, with the slope against `ln(Lambda)` when the film
ratios differ by more than 20 % (one value does not fit a speed range, E7 FT); entering it in
`tribology.friction_closure.contact_friction` is your choice.

**Cost.** One record with force, slip and torque: 18 solves, 0.4 s with the mattress bite on the
battery-foil case pass; 21 solves, 5.4 s with the half-space bite (budget 42 solves, 3 s and
10 s). The app does not ask for records yet.

**How to log a record.** Take a steady window of 5-10 s at constant speed and tensions; average
the roll force (both sides) and the motor torque per work roll net of losses; measure forward
slip from the exit strip speed (laser velocimeter) and the work-roll surface speed to 0.1 %
absolute; note the gauges, tensions, speed and coil, and the oil temperature; see section 7.4
of the [coverage study](simulation-coverage-gaps.md) for the measurements the gap rows ask
for.

## 9. Mill dynamics (`mill_dynamics.py`)

Status `UNVALIDATED_LINEAR_MILL_DYNAMICS_SCREEN`; wraps `chatter.py` without changing it.
The results never change hypothesis evidence.

> **Not for foil passes.** Gaugemeter control acts through roll force and an open gap. At foil
> gauge the gauge is controlled by speed and tension [TM-LC18 VP]. Do not read this section
> for passes below the closed-gap onset (section 3.2); the result carries `foil_regime_note`
> on the gauge-control section there (SPEC17 X7).

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

Status `UNVALIDATED_EXPERIMENTAL_MATTRESS_FOIL_BITE`. A planner reduction [D]: a plain
Winkler-foundation ("mattress") bite, in the non-dimensional form of the MISG report "A simple
model for the cold rolling of metal foil" [V, `(h - G2)p' + mu*p = x`]. Fleck & Johnson
(1987) used a foundation only for the perturbation of a Hertzian pressure and rejected the
plain mattress [BT-S2 FT]; Fleck et al. (1992) abandoned it because it under-predicts load by
up to a factor 2 and torque by up to a factor 10 [BT-S1 FT]. Fleck & Johnson's modulus is
`8E*/(3*pi*a0) = 0.849 E*/a0`; this module uses `(3*pi/8)E*/a = 1.178 E*/a`. It is **not** the
Fleck-Johnson hybrid model: the strip is
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
`2K/K_p`; Coulomb shear above the shear yield in any slip zone (a 50 -> 25 um pass at a
NOMINAL friction of 0.10 is rejected for this reason; this is not the published case, where
0.1 acts on asperity contact areas only, weighted by the contact-area ratio and capped at
shear yield [BT-S3 EX]); an exit that would have
to stick (zero forward slip); a fixed point that does not converge; a force that changes by
more than 1e-3 on grid refinement.

**How far to trust it.** The model is verified for internal consistency only (rigid limit,
junction continuity, Coulomb limits, energy identity, grid convergence, trends). One
published foil-bite case has every input stated: Fleck, Johnson, Mear & Zhang 1992, Fig. 9
(BT-V1 [FT]: entry 20 um, 25 %, R 89 mm, `Y_s` 230 MPa, `E_R*` 230 GPa, friction 0.03, no
tensions). On it the mattress bite returns `W_bar = W*E_R*/(R*Y_s^2)` = 49.77 [run], **0.42 of
the half-space reference load** of 118 and 0.80 of the authors' own mattress value 62. This is
a recorded discrepancy, not a validation; the model is not tuned towards 118. The caption value
118 is itself not a grid-independent number: the printed end conditions of the source (a
pressure step at the exit with zero slope there) give 78 to 134 for end lengths of 40 to 2.5 um
in two independent re-implementations [computed, re-implementation of E1; computed, SPEC18
prototype]; 118 corresponds to about 5 um, and the element size the paper states (about 21 um)
to 88-89. Against every member of that family the mattress value 49.8 is low by a factor 1.6 to
2.7, so the verdict stays a recorded discrepancy. The contact length of the same published
solution, 2.14 mm (`b/R` = 0.0241 [E6 FT, thesis p.54]), gives a second reference row: 1.474 mm
[run], ratio 0.689. The source's strip modulus `E_s*` = 80 GPa enters only its longitudinal
no-slip equations and none of its loads [E1 FT].
`python -m physicroll.benchmarks` prints the encoded cases (`physicroll/benchmarks.py`, status
`SOFTWARE_COMPARISON_WITH_PUBLISHED_VALUES_NOT_PHYSICAL_VALIDATION`; agreement band 0.9-1.1 on
the ratio project / reference, an analyst choice [D]); the rows of `benchmarks.table_rows()`
(a row without a published value has the row verdict `NO_REFERENCE_VALUE`: project value
recorded only; the case verdict is unchanged):

| id | quantity | project [run] | reference (kind, read) | ratio | verdict |
|---|---|---|---|---|---|
| `BT-V1` | `W_bar` | 49.7724 | 118, half-space (model output, FT) | 0.4218 | `RECORDED_DISCREPANCY` |
| `BT-V1` | `W_bar` | 49.7724 | 120, perturbation (model output, FT) | 0.41477 | `RECORDED_DISCREPANCY` |
| `BT-V1` | `W_bar` | 49.7724 | 62, Fleck-Johnson mattress (model output, FT) | 0.802781 | `RECORDED_DISCREPANCY` |
| `BT-V1` | force per width [N/m] | 1.01884e6 | 2.42e6 [derived from 118] | 0.421009 | `RECORDED_DISCREPANCY` |
| `BT-V1` | forward slip | 0.169779 | - | - | `NO_REFERENCE_VALUE` |
| `BT-V1` | contact length [m] | 1.47447e-3 | 2.14e-3, same published solution (model output, E6 FT) | 0.689005 | `RECORDED_DISCREPANCY` |
| `BT-V2-R89` | `W_bar` | 41.0688 | 58 measured (FT); radius 89 mm assumed | 0.708083 | `INDICATIVE_ASSUMED_INPUTS` |
| `BT-V2-R135` | `W_bar` | 51.0529 | 58 measured (FT); radius 135 mm assumed | 0.880223 | `INDICATIVE_ASSUMED_INPUTS` |
| `BT-V3-FIG1-140UM` | `W_bar` | 45.9683 | "about 50", Fig. 4 read by eye | 0.919367 | `REFERENCE_READ_BY_EYE` |
| `BT-V3-EQ29` | `h_0c` [m], BT-V1 mill | 3.62386e-5 | - | - | `NO_REFERENCE_VALUE` |
| `BT-V3-EQ29` | `h_0c` [m], Fig. 1 case | 5.12491e-5 | - | - | `NO_REFERENCE_VALUE` |
| `BT-V3-EQ29` | `h_0c` [m], demo mill, 175 MPa | 5.63468e-5 | - | - | `NO_REFERENCE_VALUE` |
| `BT-V3-EQ29` | `h_0c` [m], demo mill, 202 MPa | 6.28559e-5 | - | - | `NO_REFERENCE_VALUE` |
| `SS-V2` | critical stress [Pa] | 8.43556e6 | - | - | `NO_REFERENCE_VALUE` |
| `SS-V2` | critical I-units | 4.01693 | 5.3 simply supported (SS-S19 FT) | 0.757912 | `INDICATIVE_ASSUMED_INPUTS` |
| `SS-V2` | critical I-units | 4.01693 | 6.38 elastic restraint (FT) | 0.629613 | `INDICATIVE_ASSUMED_INPUTS` |
| `SS-V2` | critical I-units | 4.01693 | 8.92 clamped (FT) | 0.450329 | `INDICATIVE_ASSUMED_INPUTS` |
| `SS-V2` | half-wave [m] | 0.15 | 0.06 measured (FT) | 2.5 | `INDICATIVE_ASSUMED_INPUTS` |
| `SS-V3` | half-wave [m] | 0.105 | 0.0375 (half of about 75 mm measured, FT) | 2.8 | `RECORDED_DISCREPANCY` |
| `TM-LC7`* | equivalent Coulomb friction | 0.0265664 | - (substitution 2) | - | `NO_REFERENCE_VALUE` |
| `TM-LC7`* | separating force [N] | 4.10437e6 | - | - | `NO_REFERENCE_VALUE` |
| `TM-LC7`* | forward slip | 0.0293589 | - | - | `NO_REFERENCE_VALUE` |
| `TM-LC7`* | contact length [m] | 5.14983e-3 | - | - | `NO_REFERENCE_VALUE` |
| `TM-LC7`* | strip modulus `Q_s` [N/m] | 2.00515e10 | - (2.1325e10 would put the mode at 124.6 Hz [D]) | - | `NO_REFERENCE_VALUE` |
| `TM-LC7`* | lower loaded symmetric mode [Hz] | 121.878 | 124.6 measured (E9 FT) | 0.978157 | `WITHIN_AGREEMENT_BAND` |
| `TM-LC7`* | onset frequency, bite damping 0.5 [Hz] | 122.303 | 124.6 measured (E9 FT); paper's model 129 / 132 | 0.981567 | `WITHIN_AGREEMENT_BAND` |
| `TM-LC7`* | critical exit speed, bite damping 0.5 [m/s] | 8.10139 | 8.715, if 5.81 is the speed between the stands [D] | 0.929592 | `INDICATIVE_ASSUMED_INPUTS` |
| `TM-LC7`* | critical exit speed, bite damping 0.5 [m/s] | 8.10139 | 5.81 measured (E9 FT), if it is stand 2's exit speed; paper's model 6.42 / 6.57 | 1.39439 | `INDICATIVE_ASSUMED_INPUTS` |
| `TM-LC7`* | critical exit speed, no bite damping [m/s] | 0.517673 | - | - | `NO_REFERENCE_VALUE` |
| `TM-LC7`* | onset frequency, no bite damping [Hz] | 481.149 | - | - | `NO_REFERENCE_VALUE` |

\* `TM-LC7` project values rest on three substitutions: (1) rigid rolls (roll modulus 1e14 Pa;
the paper has no flattening, and Hitchcock flattening rejects this pass with real rolls);
(2) a Coulomb coefficient with the same mean friction stress as the paper's friction factor
0.054 on the shear yield stress; (3) stand 2 alone with its two spans instead of the paper's two
stands with stress waves. Case verdict `INDICATIVE_ASSUMED_INPUTS`; the speed rows are
indicative only (section 11.4).

`BT-V3-EQ29` evaluates the regime boundary `h_0c = 12*R*r^0.5*mu^1.24*(Y_s/E_R*)^0.76` (eq. 29
[FT]): 36.24 um for the BT-V1 mill (entry 20 um below it; the project's regime is `foil`) and
51.25 um for the Fig. 1 case (entry 140 um above it; regime `conventional`), verdict
`CONSISTENT_REGIME`; for the battery-foil demo mill 56.35 um (`Y_s` 175 MPa) and 62.86 um
(175*2/sqrt(3) MPa), where the bite report gives "54-63 um" [derived] (its lower end is not
reproduced with these inputs). The steel chatter onset `TM-LC7` is run with the paper's stand-2
inputs and three substitutions; what it shows is in section 11.4. In the foil regime the model gives large forward slip (flag
`FORWARD_SLIP_LARGE_CONSTANT_FRICTION_NO_SLIP_ZONE_MODEL`, above 0.15): that is what a constant
Coulomb friction model with a no-slip zone gives (section 3.3); elastic strip zones are not
the cause, they are negligible above 10 % reduction [BT-S1 FT]. Treat foil-regime numbers as order
of magnitude only.

**`model_options.bite_model`**: `hitchcock` (default; slab + circular flattening), `mattress`
(always the experimental model, at least 200 cells), `auto` (Hitchcock, and the mattress
model only when Hitchcock rejects the pass; the reason is kept in `bite_fallback_reason`),
`half_space` (the reduced half-space model, section 10.3, for every pass) or
`auto_half_space` (Hitchcock, and the half-space model where Hitchcock rejects). `auto` never
falls back to the half-space model.
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

### 10.3 Reduced half-space model (`halfspace_bite.py`)

Status `UNVALIDATED_REDUCED_HALF_SPACE_FOIL_BITE`. Opt-in: `diagnose()` uses it only with
`model_options.bite_model` set to `half_space` or `auto_half_space`; the default and the
demos are unchanged. It is a REDUCED form of the foil-bite model of Fleck,
Johnson, Mear & Zhang (1992) [E1 FT, transcribed in
`docs/research/band-screening-2026-11/phase1-equations.md`].

**Model.** The rigid-plastic strip runs between two rolls that deform as elastic half-spaces:
the roll gap is `g = g0 + x^2/R - (4/(pi*E_R*)) Int p ln|x - x'| dx'` [E1 eq. (8)], so the
pressure at one point flattens the roll everywhere, not only under itself as in the mattress.
Equilibrium, yield and Coulomb slip are E1 eqs (1), (3a), (9a), with the friction stress
capped at `m*K/2`. The zones are those of E1: an entry contact zone, A (plastic reduction,
backward slip), B (no-slip zone of constant thickness, E1 eq. (16)), E (a short backward-slip
zone before the pressure peak), F (plastic reduction, forward slip) and an exit contact zone.
A pass is solved as `A F` (E1's regime I, sheet-like), `A B F` or `A B E F` (regimes II and
III); the zone boundaries are unknowns of one Newton system on a grid fitted to them. The
start comes from the mattress bite, whose Winkler roll is blended into the half-space in
steps; where the mattress bite rejects the pass (high friction), the solver starts at a
friction of 0.03, 0.02 or 0.01 and steps the friction to the entered value (flag
`COLD_START_BY_FRICTION_CONTINUATION`). A solution of a neighbouring pass can be given as a
warm start.

**Which zone structure is used.** The candidate is tested by six rules in a fixed order, and
the first that passes is used: (1) `A F` if the strip never thickens in A and F; (2) `A B F`
if the shear the no-slip zone needs (E1 eq. (16)) stays within the friction limit in every
element; (3) otherwise zone E is inserted where the no-slip zone first needs more than the
limit, accepted if the pressure in the no-slip zone stays under the two friction hills (within
`0.02*K`, an analyst tolerance); (4) otherwise `A F` again from the middle of B and E; (5)
`A B E F` built from that `A F` where its thickness rises; (6) otherwise the pass is rejected
with every step listed. Every candidate must also pass a rule of this project's own
(`SLIP_CONSISTENCY`, from E1 eq. (9a) and its zone description): the strip must leave faster
than the roll and enter slower (forward and backward slip positive), and every reduction zone
must have a length. It rejects a degenerate branch the Newton iteration can reach, in which
zone F collapses to nothing, the strip leaves at roll speed and the load is 8.6 to 12.5 times
the mattress load; the discrete equations hold there only because the rows of a zone without
length hold trivially. With the rule the result does not depend on the Newton budget (tests
with 20, 40 and 80 iterations per step). Every step of the selection is in the result
(`structure_selection`); at the regime boundary, where neither the no-slip structure nor
zone E is admissible and `A F` is used (rule 4 or 5), the result carries
`ZONE_STRUCTURE_AT_REGIME_BOUNDARY` and the nearest rejected candidate with its force: on the
battery-foil case pass F1 (50 -> 30 um) the `A B F` candidate is 1.7 % above the `A F` load
that is used [run].

**Three misprints of E1** are not used: its influence coefficient (30) has the wrong sign
(the kernel here is re-derived and recovers Hertz line contact to 2.6e-3 of the indentation
depth on 80 elements, 1.1e-3 on 160 [run]); its element formula (20) has the friction terms
with the wrong sign; its finite-difference form (36) of eq. (16) has a misprinted bracket.

**Why the bite ends are closed by contact zones.** The printed model ends the bite with a
pressure step from `Y_s - sigma` to zero and asks for a zero thickness slope there. On a
half-space a pressure step has a logarithmically infinite surface slope, so that condition
depends on the length over which the step is smeared, which the source does not state: two
independent re-implementations give `W_bar` 78 to 134 on the published case for end lengths
of 40 to 2.5 um [computed]. This model keeps the strip in contact beyond the plastic zone at
constant thickness until the pressure has fallen to zero (E1's elastic end zones, eq. (13),
which E1 neglects), and its load is grid-converged: 0.37 % change when every zone count is
doubled [run].

The printed end conditions are kept as a benchmark mode only (never reachable from the
engine): one pressure element of prescribed length outside each end, rigid strip, `A B F`.
On the published case [run, tests/test_halfspace_bite_cases.py]:

| end length [um] | 40 | 30 | 21 | 15 | 10 | 7 | 5 | 3.5 | 2.5 |
|---|---|---|---|---|---|---|---|---|---|
| `W_bar` | 78.01 | 82.57 | 88.62 | 94.73 | 102.62 | 110.04 | 117.47 | 125.82 | 134.15 |
| thickening before the exit, of the exit gauge | 0.00026 | 0.00064 | 0.00118 | 0.00175 | 0.00252 | 0.00326 | 0.00401 | 0.00485 | 0.00568 |

The load has no limit as the end shortens. The caption value 118 corresponds to an end of
about 5 um; at the element size the paper states (about 21 um) the printed model gives 88.6,
the value this model gives with a rigid strip (88.86) [run]. So "118" is the result of one
unstated numerical length, not a target; and every member of the family makes the strip
thicken before the exit, which the model itself forbids.

**The strip thickness spring is the planner's addition, not the source's.** The strip is
given a thickness compliance `h_p = g + c_s*p`, `c_s = (h0 + h1)/2/E_s*`. E1 neglects the
elastic thickness change of the strip. It is kept because the strip does compress and because
without it the entry contact zone has no length; it raises the load on the published case by
4.6 % (`W_bar` 88.86 with a rigid strip [computed, SPEC18 prototype], 92.94 at 80 GPa [run]).
Every result carries the flag `STRIP_THICKNESS_SPRING_NOT_IN_PUBLISHED_MODEL` unless
`strip_plane_strain_modulus_pa` is 1e13 Pa, which switches the spring off.

Numbers [run, tests/test_halfspace_bite.py] (R 89 mm, `Y_s` 230 MPa, `E_R*` 230 GPa,
`E_s*` 80 GPa, friction 0.03, no tensions unless stated):

| pass | structure | `W_bar` | force [N/m] | forward slip | contact length [mm] | `p_max/K` |
|---|---|---|---|---|---|---|
| 20 -> 15 um (published case) | A B F | 92.936 | 1902401 | 0.2037 | 2.038 | 7.33 |
| 140 -> 70 um | A F | 46.820 | 958396 | 0.0709 | 3.058 | 2.20 |
| 60 -> 30 um | A F | 68.034 | 1392662 | 0.2180 | 2.446 | 5.75 |
| 30 -> 15 um | A B F | 207.127 | 4239893 | 0.4769 | 3.156 | 11.30 |
| 20 -> 10 um | A B F | 408.602 | 8364086 | 0.5091 | 4.217 | 11.86 |
| 73 -> 31.39 um, friction 0.026, tensions 0.107 / 0.132 `Y_s`, R 89 / 135 mm | A F | 42.800 / 67.125 | 876108 / 2084239 | 0.1295 / 0.3103 | 2.490 / 3.618 | 3.10 / 6.48 |
| battery-foil demo ALT2, 25 -> 12 um | A B F | - | 10128540 | 0.5527 | 5.710 | 11.86 |

Regime boundary [run, tests/test_halfspace_bite_cases.py] (`W_bar`, structure, rule):

| reduction | thicker entry | thinner entry | E1 eq. (29) |
|---|---|---|---|
| 0.5 | 56 um: 75.68 `A F` (1); 54 um: 81.20 `A F` (4) | 52 um: 87.86 `A B E F` (3); 48 um: 100.19; 44 um: 114.74 | 51.2 um |
| 0.25 | 36 um: 40.19 `A F` (1); 34 um: 43.98 `A F` (4) | 32 um: 48.35 `A B E F` (3); 28 um: 58.00 | 36.2 um |
| 0.10 | 30 um: 21.86 `A F` (1); 28 um: 23.71 `A F` (4) | 26 um: 25.92 `A B E F` (3); 22 um: 31.51 | 22.9 um |

The no-slip zone appears between 54 and 52 um, 34 and 32 um and 28 and 26 um, close to eq. (29)
of E1, and the load is continuous across the boundary. Zone E changes the load by under 0.1 %
(rigid strip, published case: 88.86 against 88.94 for the `A B F` candidate) but makes the
passage between the regimes continuous. Forward slip with zone E is taken at the slip reversal
(the E/F boundary); the no-slip zone is thicker by an elastic-order amount, which raises the
slip by 1 to 2.5 % of its value if that thickness is used instead (the planner's prototype
quoted the latter).

Shear cap (50 -> 25 um, `K` 150 MPa, tensions 20 MPa, R 135 mm [E4 EX, Table I pass]; the
mattress bite rejects it at friction 0.05): 1.52 MN/m at friction 0.03, 7.72 MN/m at 0.05,
48.65 MN/m at 0.10 with a contact length of 12.15 mm and a peak of 34 times `K` (flags
`SHEAR_CAP_ACTIVE`, `PEAK_PRESSURE_ABOVE_16_PLANE_STRAIN_YIELD`) [run]. As X24 says, a nominal
friction of 0.10 is not the published case: no mill runs a foil pass at 32 times the load of
0.03.

On the published case the mattress bite gives 49.77, the reduced half-space 92.94 (88.86
with a rigid strip [computed, SPEC18 prototype]); the caption value 118 is one member of the
family 78-134 and is not a target (section 10.2). Left out: the longitudinal elastic equations of E1 ((4), (10)-(14)), hence stress
and traction inside the no-slip zone and the regime-III zones C and D; friction varying
through the bite; hardening, rate and temperature inside the bite; the lubricant film; the
closed gap. One cold solve with the selection takes 0.3 to 2.5 s, a warm start about 0.2 s.

**What "118" means (finding 1 of the Phase 1 brief, in full).** The printed model ends the
bite with a pressure step from `Y_s` to zero and asks for `db/dx = 0` there. A pressure step on
a half-space has a logarithmically infinite surface slope, so the condition means something
only relative to the length over which the step is smeared. Two independent
re-implementations (the research note's in numpy, the planner's in the standard library) give
the same family: 78 to 134 for 40 to 2.5 um, no limit. 118 is obtained at about 5 um; at the
element size the paper states, 88 to 89. "118" is the caption value of one unstated end length;
it is recorded, not used as a target.

**In the engine.** `derive_bite_response_half_space` returns the same `BiteResponse` as the
other models: force, slip, contact length and the eight sensitivities, by central differences
whose perturbed solutions are found by chord iterations with the factorised Jacobian of the
nominal solution (half steps of 1e-3; the planner checked chord against full Newton to 7
digits, a test to 1e-6). It also returns, in `result.bite_extras`, the friction and
flow-stress derivatives (`dforce_dfriction_n`, `dforce_dflow_stress_m2`, the slip and
contact-length derivatives, the load exponents), the torque and the slip dissipation; for any
other bite `bite_extras` is `NOT_SUPPLIED`. Every consumer of the bite uses the half-space
model when the operating bite is a half-space bite: the friction fixed point, the lever rows
and the speed-consistent critical speed (`perturbed_bite_model: reduced_half_space`), pass
heating (its own slip dissipation), the gauge trend, the schedule sweep and the friction
stripe screen (`bite_model` / `sensitivity_bite_model: reduced_half_space` per row). With
`auto_half_space` a pass Hitchcock solves stays Hitchcock and says so in its row. A pass the
half-space model cannot solve is a rejected row with the solver's reason (stage and rule), as
for the other models; it never stops `diagnose`. Derivations within one run warm-start from
the nearest solved pass. Cost per derivation on the 13 demo passes: cold 0.89 s mean, 1.74 s worst; warm-started 0.49 s mean, 1.58 s worst on F2 (30 -> 18 um), where the zone-E selection re-runs, above the 0.6 s the Phase 1 brief budgets [run]; the
battery-foil demo with `auto_half_space` took 92 s (88 s with `half_space`) against 105 s
with the default [run, one core].

**Benchmarks** (`python -m physicroll.benchmarks`, section 13): `BT-V1-HS` (the published case:
`W_bar` 88.86 with a rigid strip and 92.94 with the 80 GPa spring against the caption 118,
verdict `REFERENCE_NOT_GRID_INDEPENDENT`, ratio recorded and not judged; contact length 1.961
and 2.038 mm against 2.14 mm of the same published solution, 0.917 and 0.953, within the
agreement band; peak, peak position and contact ends against the figure read by eye; the
printed-end family 78.0 / 88.6 / 102.6 / 117.5 / 134.2 at 40 / 21 / 10 / 5 / 2.5 um),
`BT-V2-*-HS` (42.80 and 67.13 against the measured 58 with an assumed radius),
`BT-V3-FIG1-140UM-HS` (46.82 against about 50 by eye), `BT-V3-EQ29-HS` (the regime boundary:
consistent for r 0.5 and 0.25, 14-22 % above eq. 29 for r 0.10, recorded) and
`BT-X29-LOAD-EXPONENT-HS` (load exponent in friction 2.461, inside the 2 to 2.6 read from the
master curve).

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

**The one measured chatter onset with mill parameters (`TM-LC7`, X31).** Niroomand, Forouzan &
Salimi (2015) [E9 FT] give a two-stand steel mill with every structural input and a measured
onset of 124.6 Hz and 5.81 m/s. Its stand structure is the one of `chatter.py`; its process
model is not, so `benchmarks.py` runs stand 2 with three substitutions (rigid rolls; a Coulomb
coefficient 0.026566 with the paper's mean friction stress; stand 2 alone) [run]. The frequency
agrees (lower loaded symmetric mode 121.88 Hz, onset 122.30 Hz, ratio 0.98) because it is set by
the stand and the strip stiffness. The critical speed does not settle anything: 8.10 m/s is 0.93
of the reference if the paper's 5.81 m/s is the strip speed between the stands (stand 2 then
exits at 8.715 m/s [D]) and 1.39 of it if 5.81 m/s is stand 2's exit speed; it moves from 5.73
to 9.26 m/s for a Coulomb coefficient of 0.02 to 0.03 [run] and rests on the bite-damping
heuristic: without it the model is unstable from about 0.52 m/s in its upper mode (481 Hz), at
the low end of the scanned speeds. So the case checks the stand and strip-stiffness part of the screen on a steel mill; it
does not check the speed at which chatter starts, and it is not a validation on an aluminium
foil mill.

**The rate share of the bite damping (B1; C3 itself is not implemented).** A rate-sensitive
flow stress gives a force in phase with gap velocity [D, re-derived in SPEC18]: the bite strain
rate gains `-h_dot/h_mean` when the gap moves, so `F_hdot_rate = -F_Y*Y*m*l_d/(h_mean*u*
ln(h0/h1))` and the transit fraction it alone would justify is
`beta_rate = F_Y*Y*m/(Q*h_mean*ln(h0/h1))` (`F_Y = dF/dY` of the operating bite model,
`Q = -F_h`). With `hardening.rate_temperature` the result carries it as
`chatter.rate_sensitivity_damping` beside the heuristic `bite_damping_transit_fraction`;
reported only, the stability results use the heuristic unchanged. On the published foil case
(half-space bite, 80 GPa strip spring, m 0.027: `F_Y*Y` 4.8213e6 N/m, `Q` 5.57561e11 Pa)
`beta_rate` is 0.046375, 9.3 % of a heuristic 0.5: the measured rate sensitivity explains a
tenth of the damping the heuristic assumes.

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

### 11.6 What the thickness gauge keeps of a mark (`measurement.thickness_gauge`)

SPEC17 package 5 (gap C7, gauge part; `physicroll/band_sensors.py`). A gauge with a
few-millisecond response at 10 m/s averages over centimetres, so 10-40 mm marks are invisible
to it (gap study C7; foil gauge response under 10 ms [TM-LC24 VP]). With
`measurement.thickness_gauge` the result gives, for every pitch observation at its own speed,
the measured vibration frequency and the modelled chatter onset frequency at the operating
speed, about how much of a mark of that pitch the gauge keeps [D, re-derived in SPEC17]: a mark
`A*cos(2*pi*x/p)` passing at `u` has frequency `f = u/p`; a spot of length `L` keeps
`|sin(pi*L/p)/(pi*L/p)|`, a first-order response with time constant `tau` keeps
`1/sqrt(1 + (2*pi*f*tau)^2)` (an averaging length `u*tau`); sampling at `dt` aliases when
`f > 1/(2*dt)`. A pitch is resolvable when the product is at least 0.5 (analyst choice [D])
and it is not aliased; the shortest resolvable pitch at the operating speed is given. With
`gauge_variation_amplitude_m` each row gives the amplitude before the gauge, a lower bound of
the true amplitude if the mark has that pitch. This is a spot average and a first-order lag
only; real gauges have other filters (scanning frames, digital filters, noise), which are not
modelled. Worked numbers (spot 10 mm, 5 ms, 1 ms sampling; `tests/test_band_sensors_gauge.py`):
the thin-gauge demo's 84.08 mm pitch at 16 m/s (190.3 Hz) is kept at 0.161 (spot 0.977, time
constant 0.165), 76.47 mm at 14.5 m/s at 0.161, the bearing demo's 24.92 mm at 7.83 m/s
(314.3 Hz) at 0.076; `u*tau` at 10 m/s is 50 mm.

Flags: `GAUGE_TRANSFER_APPLIED`; `GAUGE_KEEPS_LESS_THAN_HALF_OF_OBSERVED_MARK`;
`GAUGE_NOT_DETECTED_BUT_MARK_NOT_RESOLVABLE` when `gauge_variation_detected` is false and no
observed pitch is resolvable: "not detected" then carries no information, the note names the
hypotheses whose evidence uses that observation, and **the tally is not changed** (SPEC17 open
decision 2: flag only; the item "gauge variation not detected" counts as before); and
`LENGTHWISE_MODEL_BAND_NOT_UNDER_GAUGE` when modelled lengthwise bands exist and none passes
under the gauge (`bands_under_gauge`, from the steady profile of section 7.6). No demo carries
a gauge description. Not built: accelerometer position and detection lead time (no formula in
the reports), gauge noise, calibration, scanning frames.

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
| Across the width: predicted against observed bands | upper panel: steady roll radius growth with the actual and with a healthy header, nozzle positions; lower panel: flatness at the three levels of the shape chain (the thick line is the linear-feedback level), dashed lines at the observed positions; a note on a saturated band and on the whole-sheet indicator. Tables: Steady stripes (peak, half-peak width, I-units per level, state in the mill and after tension release, buckling utilisation, stripe heights for a band in the mill, after release and at 2 I-units); the nozzle-pattern ripple; Which predicted source each observed band matches; Which pitch the gaps are multiples of; Tension troughs (span wrinkling); then two-tone, grinding feed, incoming ridges and crown lines; with an angular layout, the block "Roll surface within one revolution" (the layout used, a chart of the surface temperature against the angle at three stations, a table before / after the bite, lowest, mean and the mean model's value, the time-scale line beside the published 20 s, the bias sentence) |
| Measured roll profile (SPEC20 additions) | inside the width section: the bands with de-trending orders 2 and 4 and the largest difference, the warning "subtract the grinder's target curve before entering the profile, or state the curve" with `ROLL_PROFILE_BANDS_DEPEND_ON_DETREND_ORDER`, and "this profile cannot show a mark narrower than X mm" with `ROLL_PROFILE_GRID_TOO_COARSE`; `GRINDER_CHATTER_NOT_EXCLUDED_NO_GRINDER_DATA` appears in the flag list when a work-roll pitch fits no simple count but a grinder pattern |
| A hot stripe: roll growth, oil film, softer metal, strip temperature | only with `width_model.local_coupling` (inside the width section, after the friction-stripe block): the local state at the largest roll surface difference and the oil supply, a chart of the four terms and both sums, the band and event tables (both transfer levels, the net at inlet weights 0 / entered / 1 and the sign words), one sentence per row, the force sensitivities with their bite model and time scales, the sign note, and the warning "Read the signs, not the digits." |
| Short-lived bands (cooling-zone switching events) | per event: radius deviation against time with the in-mill, after-release and reporting thresholds, and the event table of 7.4 (rows for the stripes of an event with several groups of adjacent nozzles, and for attribution flags, appear only when present; a fade beyond the attribution window reads "not attributable after ... s: a later event switches nozzles in the same neighbourhood"); the growth-rate note and the open discrepancy |
| How the result changes with gauge | a generated direction sentence, then the gauge-trend text, two charts and the table of 7.3 |
| Hypotheses | every hypothesis grouped by family (observed family first) with standing, score, evidence items and confirming test |
| Transverse-band (chatter) screening: supporting detail | Key model numbers, What the model predicts on the strip, Chatter stability, Pass-schedule sweep, Frequency-speed map, Forced response and time trace, Levers (with coolant spray coverage and other screens) |
| Process: friction, flow stress, pass heating | section 8: friction against speed, flow stress per pass (supplied, computed, used), pass heating, speed-consistent critical speed; with pass records, the block "Friction from your pass records" (section 8.5: one row per record with the friction from force, slip and torque and their first-order intervals, the joint value, the agreement, the load and slip exponents; the summary sentence; the implied contact friction; a warning that nothing is applied) |
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
the quarter-barrel note and the heat-partition / spray sensitivity table; since SPEC17 a line
under the inputs table on the basis of the spray coefficient ("The two are not on the same
basis", with the jet-zone equivalent when `spray_wetted_arc_rad` is given) and a "Fire limits"
table (or "Fire limits not checked: no flash point given"). The width section prints the
wide-foil note under the tension-trough table below 100 um. A v2 report has a section **"What a
shapemeter would show"** right after the width section (section 7.6): the set-up sentence, a
chart of the zone readings of the steady profile (bars) over the fine model profile (line) with
the threshold (dashed) and the nozzles (ticks), a table per profile (band position, model peak,
half-peak width, zone, zone reading, reading / peak, "would show" or "would probably not
show"), the dilution table, the nozzle map sentence and the "no flatness controller" warning.
Without a shapemeter the section is one paragraph ("No shapemeter was described ...", with the
38 % of a 20 mm band in a 52 mm zone computed by the top-hat formula). With a thickness gauge
the section adds a table "What the thickness gauge keeps" (source, pitch, speed, frequency,
spot, time-constant and combined fraction kept, aliased, resolvable), the shortest resolvable
pitch, the not-detected note (the tally is not changed) and the bands under the gauge
(section 11.6). The width section ends with
"Strip temperature and flatness" (section 7.7): with a scan, the scan points, a chart of the
mechanical and the as-measured-hot profiles with the thermal term, the table of the four
profiles (meaning, largest band, in-mill state, state after release) and the warning "The
temperature profile was supplied, not computed. Flatness measured hot and flatness after the
coil has cooled differ by the thermal term: X I-units at Y mm."; without a scan one line ("a
1 K hotter fibre reads about 2.4 I-units loose", the textbook coefficient). Then "A friction or
oil-film stripe as a band source" (section 7.8): the per-pass table (gauge, force, load
exponent, I-units per 1 % with feedback and compliance only, marks), the trend text, the sign
note, the supplied stripes with their states, the flagged placeholder conversion and the
limitations; without a screen one line. Then "Measured roll profile" (section 7.9): the profile
chart (measured, removed polynomial, local deviation), the stripe table with I-units and
states, the shapemeter readings and the stiffness indicator in one sentence; without a profile
one line. In a v2 report the tension-lines hypothesis shows the candidate pitch as a short
table (radius, candidate pitch, "candidate, not evidence", the ruler test). The v1 report is
unchanged. Further down, the
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
`experimental_mattress` for a mattress bite, `reduced_half_space` for a half-space bite
(option `half_space` or `auto_half_space`), otherwise the bite's own source
(`derived_slab_hitchcock` in the lengthwise demo; `experimental_mattress` in the foil
demo). In the result JSON a mattress bite's own `source` field reads `supplied` (for example
`chatter.critical_speed.bite_source` and the gauge-trend `bite_source` of the foil case pass);
the `bite_model` fields (`experimental_mattress`, `reduced_half_space`) are the ones to read.
With a half-space operating bite the result also carries `bite_extras` (section 10.3).

**Reading in-mill against after-release.** Every band state comes in pairs, written in plain
words in the tables. *In the mill*: "hidden under mill tension" (`LATENT_UNDER_TENSION`: flat,
a stress stripe a shapemeter can see when the band is at least about one zone wide, section
7.6) or "buckled in the mill" (`MANIFEST_BUCKLE`; "(feedback
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
| `band_signatures.py` / `tests/test_band_signatures.py` | pitch doubling with speed; exponent classification and the < 5 % speed-spread guard; bearing-order identities; catalogue pitches and resonance round trip; AA5182 bending window; spray coverage of uniform, non-overlapping and blocked headers; free thermal growth rising with thinner gauge; film-ratio labels and status strings `MIXED_SUBSTANTIAL_CONTACT_LUBRICATION` / `MIXED_FIRST_CONTACT_LUBRICATION` / `HYDRODYNAMIC_LUBRICATION` and the common-industrial-window flag (SPEC17) |
| `roll_thermal.py` / `tests/test_roll_thermal.py` | steady uniform `T = Tc + q/h` at every radius; lumped-limit exponential approach and axial decay length `sqrt(k_z*R/(2h))`; pure radial transient against the Bessel series; long transient reaching steady state; energy conservation to round-off; grid and time-step convergence; blocked-nozzle stripe position and size; zone-off-then-on growth law `2*alpha*dh*(Ts-Tc)/(rho*c)` in the resolved and lumped models, faster surface temperature and faster decay in the resolved model (`test_zone_off_then_on_grows_then_decays_and_skin_effects`); healthy header weight averages to 1; expansion constraints differ by `1 + nu`; difference-profile stripe detection |
| `strip_shape.py` / `tests/test_strip_shape.py` | zero exit-tension force sensitivity reproduces the compliance-only transfer and I-units exactly and a tiny positive value is continuous with it, a negative value is rejected (`test_zero_sensitivity_is_the_compliance_only_limit`); compliance and transfer check values; sinusoid as eigenfunction; feedback-off numbers unchanged; `Q_eff` formula; gauge-independent feedback limit (`test_gauge_independent_limit`); mean component keeps `Q`; worked example latent with feedback; saturation formula; 3 um stripe states at three gauges; Rayleigh limits (uniform compression, embedded zone); released local / global modes and the top-hat edge-spike limit; heredity and Shohet-Townsend check values; coil-ridge formula, yield onset and thin-gauge scaling; trough and wrinkle check values and scalings; spacing and position matching |
| `bite_tribology.py` / `tests/test_bite_tribology.py` | viscosity `beta` from the kerosene data points; film check case (62.8 nm, film ratio 0.209, within 5 % of the quoted 65 nm); film linear in speed and viscosity; closure limits and slope; friction falling monotonically with speed; pass heating check (49.35 K) and energy closure; Voce mean against quadrature; literature fits carry the warning; regime labels and window (`test_regime_labels_and_window`: 0.005, 0.01, 0.5, 0.99 `MIXED_SUBSTANTIAL_CONTACT` with the window false / true / true / false, 1.0 and 3.0 `MIXED_FIRST_CONTACT`, 3.01 `HYDRODYNAMIC`, no result contains `BOUNDARY`; SPEC17) |
| `mill_dynamics.py` / `tests/test_mill_dynamics.py` | static run-out and stroke transfer; full compensation prints run-out through; amplification rising with `alpha`; entry-thickness limit; mass-flow limit with tension coupling; `alpha = 0` reproduces `chatter.py`; first-order loop interaction reported and removed by roll-off; neutral mode at `alpha = 1`; hardness sensitivity and static limit; coil-synchronous frequencies; three-mass torsional benchmark; reel inertia; roll-speed DC limit; speed-change gauge shift |
| `foil_bite.py` / `tests/test_foil_bite.py` | rigid limit reproduces the slab force, slip and torque within 1e-3; sheet case conventional and of the same order as Hitchcock; foundation modulus is the fixed point of the contact length; end-zone equilibrium and smooth exit junction; work identity and grid convergence; Hitchcock-rejected pass solves; foil regime with shear within Coulomb; rejection of a 50 -> 25 um pass at a nominal friction of 0.10 (not the published case, where 0.1 acts on asperity contact areas only, weighted by the contact-area ratio and capped at shear yield [BT-S3 EX]), the limiting gauge and a sticking exit; the large-slip flag `FORWARD_SLIP_LARGE_CONSTANT_FRICTION_NO_SLIP_ZONE_MODEL` (renamed in SPEC17); force trends; sensitivity signs match Hitchcock |
| `halfspace_bite.py` / `tests/test_halfspace_bite.py` | influence coefficients against the uniform-grid closed form (`kappa`) and a quadrature of one hat, their slope against a central difference; Hertz line contact recovered (80 elements: 2.6e-3 of the indentation depth at all nodes, 7.6e-4 inside 0.8a; 160 elements 1.1e-3 and 2.7e-4); equations equal unknowns for `A F`, `A B F`, `A B E F`; the Winkler limit reproduces the mattress solver (force within 1 %, slip within 0.002); the planner's worked numbers pinned (published case `W_bar` 92.936, seven sheet and foil rows, a sheet pass within 8 % of the mattress); work identity below 1e-4; the three A B F candidates beyond the friction limit (eq. (16) shear 1.446, 1.030, 2.941) replaced by A B E F or A F; the strip-modulus trend (40 GPa 96.751, 160 GPa A B F candidate 90.933); a doubled grid moves the load by 0.37 %. `tests/test_halfspace_bite_cases.py`: the selection table of fifteen passes (structure, rule, `W_bar` to 1e-4 of the planner's values), the regime boundary against E1 eq. (29), load continuity, zone E under 0.3 % of the load, path independence and warm start equal to cold start, rule 6 message, the battery-foil and lengthwise schedules (13 passes in under 30 s), the shear-cap march where the mattress rejects, the printed-end family (W_bar 88.62 / 102.62 / 117.47 at 21 / 10 / 5 um, thickening before the exit). `tests/test_halfspace_bite_branch.py`: the same three passes with a Newton budget of 20, 40 and 80 per march step give the same load; the degenerate branch is rejected by rule `SLIP_CONSISTENCY`. Software checks only: a value near a published load would not validate the model |
| friction closure and fits / `tests/test_bite_tribology.py` (`LoadSharingClosureTests`), `tests/test_asperity_contact.py`, `tests/test_band_v2_sections.py` (`LoadSharingClosureSectionTests`) | the closure table of section 8.1 (contact ratios, friction and slopes at `mu_c` 0.09 and 0.03, the placeholder beside it) to 5e-6; the five published points returned exactly (an identity, not a benchmark) and continuity across each; valley films; the Eyring, Newtonian and capped valley numbers; the 0.045 flag on a low cap; the required contact friction, bite state and cap; the default closure unchanged; the Christensen, Wilson-Sheu, crushing-rate and flow-factor values, and that no engine module imports the fits; with the new closure the friction rows carry its keys and flags while bite and scores stay those of the placeholder case, and the fixed point converges; `tests/test_benchmarks.py`: `BT-G3-CRUSHING-LAWS` |
| oil properties / `tests/test_bite_tribology.py` (`OilPropertyTests`), `tests/test_band_v2_sections.py` (`ViscosityTableSectionTests`) | viscosity table: the planner's interpolated and extrapolated values (1.206440e-3 Pa s at 50 C ... 1.921860e-3 at 20 C) and segment coefficients, the local coefficient against a finite difference, a two-point table equal to the exponential law to 1e-12 (also through the friction section), flags, validation; Roelands: the index 0.657133 and the viscosities of section 8.1, its slope at zero pressure equal to the Barus coefficient, its domain error; Eyring and limiting stresses default to none, validate, and the flag below 0.045; the example oil carries a tag on every entry; `tests/test_benchmarks.py`: `BT-G3-FILM-E6-T42`, `BT-V4-FILM`, `A9-PRESSURE-LAWS-KEROSINE` |
| half-space bite in the engine / `tests/test_halfspace_bite_sensitivity.py`, `tests/test_band_halfspace.py`, `tests/test_band_halfspace_default.py` | the sensitivity tables of the published case (spring and rigid strip) and 140 -> 70 um pinned and within 1e-3 of the planner's prototype; chord equals full Newton (1e-6); signs; the one-sided tension flag; the three-model comparison on the battery-foil demo within 1 % of the planner's table; with `half_space` (coarse battery-foil case, S3 and F2) the operating bite, `bite_extras`, the levers, the speed-consistent block, gauge trend, schedule sweep, friction stripe screen and pass heating all name the half-space model, and F2 (3.24 kN/mm) is marked not credible; `auto_half_space` falls back where Hitchcock stops; the template case with the default option gives the same result as before this package apart from the not-supplied `bite_extras` (sha256 pinned); a solver failure makes the bite not assessable without stopping `diagnose`. Software checks only |
| roll surface cycle / `tests/test_roll_skin.py` | the half-space closed forms (sinusoid amplitude within 0.5 % and lag within 1 degree; constant flux within 4 % and 1.5 % with 48 cells; step in `h` 0.5724 within 0.5 %); the planner's cycle (before / after the bite, lowest, mean, flux, 60 revolutions, mean coefficient and its ratio); energy (deep flux within 1.5 %); superposition to 2e-3 K; nine unit solutions within the 3 s budget; layout validation messages naming the two regions and the wetted-arc consistency; in the engine (template case, supplied bite) the section, `not_supplied` without a layout, every other width result, the bite and the hypotheses identical with and without it, the reduction to the mean model with sprays all round (pitch-averaged, 1 % of the surface excess) and the report block |
| spray calibration / `tests/test_band_spray_calibration.py` | twin tests on the battery-foil roll (quick numerics): both kinds recover 3400 W/m2K within 2 % and the misfit curve has its minimum there; with noise of the stated uncertainty the true value lies inside the reported interval; footprint equivalent with a wetted arc; a measurement beyond the range gives `AT_SEARCH_LIMIT`, a header-off scan an hour after the stop `NOT_DETERMINED_FLAT_MISFIT`; the refusals `TOO_FEW_POINTS` and `NO_CONTRAST`; validation messages; the CLI prints and writes nothing; `tests/test_benchmarks.py`: `TM-LA8-SPRAY-FIT` (reference only) |
| heat partition / `tests/test_bite_tribology.py` (`HeatPartitionTests`), `tests/test_band_heat_partition.py` | the closed form against the scheme (1e-5) and its asymptotic branch; the worked numbers of section 8.2 (1e-4); energy balance to 1e-9; zero conductance gives share 1, zero heat changes nothing, a hotter roll gives a share above 1 and the flag; in the engine the heating rows carry the block, with the option absent the result without the new keys equals the result with the partition switched off, with it set pass heating and the width model's roll heat fraction follow; the report line; `tests/test_benchmarks.py`: `TM-LA19-HEAT-SPLIT` |
| flow stress law forms / `tests/test_bite_tribology.py` (`FlowStressRateTemperatureTests`), `tests/test_band_rate_temperature.py` | the worked numbers of section 8.3 (1e-6); `m(T)` and its floor; factor limits; a negative late slope accepted with the positivity rule and its flag; the Tome form against a hand value (169999724 Pa to 1 Pa) and Simpson against 512 panels; the fit recovers a Voce law from 6 exact points (1e-3, positive and negative slope), flags 4 points and refuses 2; in the engine the rows carry the factor, `use_rate_temperature` needs computed flow stress, with it false nothing else differs, `chatter.rate_sensitivity_damping` equals the formula, and the worked damping share 0.046375 |
| friction from pass records / `tests/test_band_friction_identification.py` | force, slip and torque generated at friction 0.027 on the battery-foil case pass return 0.027 from each quantity and jointly (1e-3), consistent, with a flow-stress scale of 1.000, for the mattress and the half-space bite (at most 42 solves); the load and slip exponents of the three regime cases of section 8.5 (1e-3) and the weak-slip mark on the published case; an unreachable slip gives `NOT_FOUND` and `MEASURED_SLIP_NOT_REPRODUCED_BY_CONSTANT_FRICTION_BITE`; two records at two speeds give the slope and a contact friction that reproduces each friction through the load-sharing closure (1e-6); the worked contact friction 0.04086; validation messages; `not_supplied` without records; hypotheses, scores, bite, chatter, levers, screens and process identical with and without records; the report block renders and escapes; `tests/test_benchmarks.py`: `BT-V2-FRICTION-HS` |
| `benchmarks.py` / `tests/test_benchmarks.py` | software pins and recorded discrepancies against published cases (BT-V1 with the caveat that its caption value 118 is not grid-independent and a contact-length row, BT-V2 at two assumed radii, BT-V3 Fig. 1 and eq. 29, SS-V2, SS-V3, TM-LC7 run on stand 2 with three substitutions (rigid rolls, equivalent Coulomb friction, one stand): mode 121.878 Hz, onset 122.303 Hz against 124.6 Hz measured, critical exit speed 8.1014 m/s against 8.715 or 5.81 m/s, indicative only; `test_tm_lc7_hitchcock_rejects_the_pass_with_real_rolls` keeps substitution 1 necessary; the chatter harness reproduces the thin-gauge demo's 13.267836 / 4.829571 m/s and 189.109442 / 188.911169 Hz; the reduced half-space rows BT-V1-HS (verdict `REFERENCE_NOT_GRID_INDEPENDENT`; `test_bt_v1_hs_reference_not_grid_independent` passes because the load at a 5 um end is more than 1.3 times the load at 21 um, which records that the published value depends on an unstated end length and does not mean the physics is right), BT-V2-R89/R135-HS, BT-V3-FIG1-140UM-HS, BT-V3-EQ29-HS and BT-X29-LOAD-EXPONENT-HS, pinned on 2026-11-20). Each project value is pinned to a literal recorded with its date and commit (1e-6 relative): a failing pin is re-recorded deliberately, with a line here, never loosened. A separate verdict against the published value is asserted; `test_bt_v1_recorded_discrepancy_mattress_is_0_42_of_half_space_load` passes because the model is 0.42 of the reference, which records the gap and does not validate the physics |
| `band_diagnosis.py` / `tests/test_band_diagnosis.py` | planted third-octave chatter, bearing order, backup-roll mark, yield-point bending and blocked-nozzle band lead; healthy header not a band risk; missing observations never contradict; scoring, standings and the leading rule of 6.4; graceful bite failure; supplied bite; lever directions computed; zero-tension lever not assessable; rejected damping variant is a row; strict validation; determinism; report escaping; v1 report unchanged; CLI; the three scenario files load and the two v1 demos lead; review fixes (`ReviewFindingTests`): the coil strip map uses the matching coil (`test_coil_strip_map_uses_the_matching_coil`), the spindle candidate is matched without drive geometry (`test_spindle_candidate_matched_without_drive_geometry`) |
| `band_width.py` / `tests/test_band_lengthwise.py` | planted truth for each of the nine lengthwise hypotheses; three shape levels with the feedback always on; healthy header gives no stripes; gauge trend (buckling stress and dead band fall, after-release onset carries the trend, in-mill onset falls less); tension-release rule table; spacing beyond 8 pitches not comparable; any non-longitudinal orientation contradicts every lengthwise hypothesis; lengthwise demo leads with `nozzle_thermal_stripe` at coarse settings; event attribution (`EventAttributionTests`): a later event on the same nozzle is not attributed to the earlier one (`test_later_event_on_same_nozzle_not_attributed_to_earlier`), a short event's peak profile is the snapshot at the measured peak (`test_short_event_peak_profile_is_the_measured_peak`), separated nozzles are monitored per stripe (`test_separated_nozzles_monitored_per_stripe`); heat-streak tribology item (`test_heat_streak_regime_item`, SPEC17): with tribology and no temperature limit `NEUTRAL`, with a limit below the modelled exit temperature `SUPPORTS` / weak, the planted case still leads |
| `band_process.py`, report / `tests/test_band_v2_sections.py` | computed values replace supplied ones only when flagged; speed-consistent critical speed; gauge-control amplification; drive and incoming sections; `auto` falls back to the mattress model; missing sections not supplied and v1 unchanged; v2 validation; determinism, report and CLI; report section order and escaping; key numbers show the values actually used (`test_key_numbers_show_the_values_actually_used`); the engine's central-difference sensitivities equal the `mill_dynamics` ones for a Hitchcock bite (`test_hitchcock_sensitivities_unchanged_by_engine_central_difference`); review fixes (`ReviewFindingTests`): a schedule row labelled like the case pass keeps its computed flow stress (`test_schedule_row_labelled_case_pass_keeps_operating_flow_stress`), mattress-bite sensitivities use the mattress model (`test_mattress_bite_sensitivities_use_the_mattress_model`); speed margin beyond the 0.05-60 m/s scan (`SpeedMarginScanRangeTests`): the reviewer's case (supplied bite, damping 0.21, 100 m/s, scan `STABLE_OVER_SCANNED_RANGE`, operating point unstable) supports strongly with the basis named and the chatter score 5 instead of 0; 10 m/s with no crossing still contradicts as before; zero slip in the pitch kinematics only (`KinematicSlipOnlyTests`: a supplied slip of 0.6 gives a not-assessable screen showing 0.6 and no skidding support; a slip of -0.01 still skids); coverage band-risk stripes matched as intervals (`CoverageIntervalMatchTests`: the reviewer's 0.065 m band in the 0.06-0.14 m gap supports and agrees with the screen, a band 0.045 m from every interval contradicts, modelled point sources still match by centre); 100 m/s stable at the operating point (damping 0.6) contradicts with the new wording; supplied `shape_inputs` with a zero exit-tension force sensitivity (`ZeroFeedbackSensitivityTests`): the steady shape and the case-pass gauge-trend row are assessed, feedback-level numbers equal the compliance-only ones, no nan / inf, a negative value is rejected at validation; inlet angle of the film (`InletAngleTests`, SPEC17): a mattress operating bite has `film_inlet_radius_ratio` 1.0 and its film ratio times `sqrt(contact_radius_ratio)` equals the former call to 1e-9; a Hitchcock bite keeps `film_inlet_radius_ratio == contact_radius_ratio` and the lengthwise demo's film ratio 0.180115 |
| foil phase (`band_diagnosis.py`, `band_width.py`, `band_report.py`) / `tests/test_band_foil.py` | **width section without a bite** (`NoBiteWidthTests`, a 60 -> 30 um pass at friction 0.05 that both bite models reject as sticking): troughs, coil ridge (proportional estimate, ratio 0.5), positions and thermal stripes present, shape parts individually not assessable with the bite error, flag set (`test_width_section_runs_without_a_bite`); model-based and not-assessable items never contradict (`test_missing_model_parts_never_contradict`); without bite heat the thermal parts are not assessable and the rest runs (`test_without_bite_heat_thermal_not_assessable_rest_runs`); supplied shape inputs take precedence for the case pass, flag and report note, provenance escaped (`test_shape_inputs_supplied`); shape-input validation (`test_shape_inputs_validation`); `foil_regime` block, closed-gap flag, `BELOW_EVERY_REPORTED_ONSET`, wrinkle onset `1e5*40e6/70e9` (`test_foil_regime_block_without_bite`); determinism, foil box, no nan/inf in the report (`test_determinism_and_report`). **Rules** (`FoilRulesTests`): every `foil_tension_lines` branch including the gate (`test_tension_lines_rules`); the nozzle, roll-surface (backup-roll downgrade to weak), trough and heat-streak extensions, the film-ratio gate and the heat-streak tribology item (regime label never supports; exit temperature above the limit supports weakly; SPEC17) (`test_extended_rules`); foil measurement lines only below 100 um (`test_next_measurements_for_foil`); the wide-foil trough note below 100 um only, trough numbers unchanged (`WideFoilTroughNoteTests`, SPEC17 X12). **Planted truth**: regular 10 mm lines on 50 -> 25 um foil lead with `foil_tension_lines` (`test_tension_lines_lead`); orientation plus exit gauge, or plus film ratio, alone never lead (`test_orientation_and_gauge_alone_do_not_lead`). **Case-pass identity, zone-duration fallback, supplied-bite tables, sensitivity-mix flag** (`CasePassIdentityTests`, `ZoneDurationFallbackTests`, `SuppliedBiteGaugeTrendTests`, `SuppliedBiteScheduleTablesTests`, `SensitivityMixFlagTests`). **Torsional strip map**: 10 Hz mode, predicted pitch 1.0 m at 10 m/s, no foil block at sheet gauge (`test_torsional_strip_map_pitch`). **Schema**: v1 and earlier v2 files still load, a v1 case may not carry foil fields (`test_v1_and_existing_v2_files_still_load`). **Foil demo** (`FoilDemoTests`, coarse numerics, the plant's passes and the alternative route, no AGC or drive): the route in the file (S1-S3 assumed stock route, F1 50 -> 30 um = case pass, F2 to 18 um, ALT1 50 -> 25 um and ALT2 25 -> 12 um at 52 %, assumed gauges labelled, every other pass at or below 50 %, speeds inside the published spans, `material.product`), leads with `nozzle_thermal_stripe`, zone hypothesis consistent, mattress bite inside the reported load range, wrinkle comparison, latent in the mill and manifest after release, open-gap note, no floor flag, mattress bites on F2, ALT1 and ALT2 with their extended-domain flags, `extended_bite_domain` listing 18 and 12 um with the credibility marks (ALT2 ratio above 2, "NOT CREDIBLE" in the text), no case-pass mark, the product check (alloy `1235`, final passes F2 and ALT2, nothing outside the published range on the case and final passes, nearest published passes present), the extended-domain limitation, single-sheet statement, foil box before the leading hypotheses, "Extended roll-bite domain" and "Product check" in the report (`test_foil_demo_leads_with_planted_cause`); the **direction of the foil gauge trend** (`test_foil_gauge_trend_direction_runs_against_thinner_is_worse`): seven rows, ALT2 marked not credible with ratio above 2, the credible rows ordered by exit gauge S1, S2, S3, F1, ALT1, F2, along which the in-mill onset and rigid bound rise and linear-feedback I-units fall, the exit-span bite-free thresholds fall on every row, the text names ALT2 after "Not credible (excluded from the trend):" and spans 0.135 -> 0.018 mm, and the report's direction sentence ends at F2, says "thinner is less sensitive for this mechanism in the model", names ALT2 as not credible and marks its table row. **Final pass doubled or not** (`FinalPassDoubledTests`): absent or null keeps the question, `false` records single-sheet with the faces implication and no flag, `true` adds `DOUBLED_FINAL_PASS_NOT_MODELLED`, non-boolean values rejected, ignored at sheet gauge, the demo carries `false`. The direction test also pins the **bite-free values**: dead band, ridge height, trough onset and roller-wrinkle thresholds of both spans on every row, and the bite-free sentence ("falls on every pass" four times; the two entry-span quantities are not monotonic across the two routes). The **product question** is worded from the case ("The thinnest pass in this case exits at 18 um" or "... 30 um, which fits ..."; no "16-18"; `FinalPassDoubledTests`, `test_foil_regime_block_without_bite`); a sheet schedule with every pass assessable gets no span-threshold keys and no bite-free sentence (`test_case_pass_row_keeps_the_supplied_bite`). **Rules** (`test_tension_lines_rules`) also pin the stage-B tension-line weights: regular 5-20 mm strong, 25 mm weak, 80 mm a weak contradiction, irregular weak; exit gauge 12 um moderate, 25 um weak, 45 and 80 um neutral, 210 um a contradiction. **Not pinned by a test:** the forward-slip and pass-heating values of the mattress bite and the friction at which the mattress model rejects |
| product survey (`band_survey.py`) / `tests/test_band_survey.py` | the survey computed once: every catalogue product appears, with its catalogue values (sources, read status) and assumptions, the as-rolled flow stress assumed for O temper (`test_every_catalogue_product_appears`); on the foil mill at equal flow stress a thinner product has a lower critical ridge height, trough onset and roller-wrinkle threshold, and the three bite-free rankings correlate with thinner gauge above 0.9 (`test_thinner_product_lower_ridge_and_trough_thresholds`); doubled products have no bite and keep their per-sheet thresholds (`test_doubled_products_have_no_bite`); credibility marks equal the engine's (`_bite_credibility`), the load range applied to battery collector foil only, no bite-dependent ranking contains a not-credible row, ranked plus excluded rows cover every product (`test_credibility_marks_consistent_with_the_engine`); one row recomputed is identical, and the committed result and report equal a fresh run (`test_determinism_and_committed_artifacts`); the report renders, escapes text and has no nan / inf (`test_report_renders_escapes_and_is_finite`); on the user's own mill (`UserMillSurveyTests`, three products): `--products` restricts and keeps catalogue numbers, unknown ids list the valid ones; a different mill (roll radius 0.11 m, housing 9e9 N/m, 2 m spans) changes the force per width, the strip-to-mill ratio and the trough onset while the catalogue provenance stays; overrides are applied and marked user-supplied, the replaced provenance dropped, and a pass too narrow for the bite model is a row with the reason; an invalid mill file and invalid override keys or values give clear errors; a starter case written with `--write-cases` loads and diagnoses |
| packaging / `tests/test_band_products.py` | the packaged default survey mills equal the machine sections of the two demo scenarios (skipped when `scenarios/` is absent); a copy of the package run with `python -I` outside the checkout surveys a foil and a sheet product and renders the report, and `band_products --list` runs, with no `scenarios` directory (the code before the fix raised `FileNotFoundError` there) |
| robustness / `tests/test_band_robustness.py` | the reviewer's duplicate positions on the lengthwise demo case (`[0.6, 0.6, 0.7]`, which raised `gaps_m[0] must be > 0`): returns, flag set, merged list `[0.6, 0.7]` used and recorded, nozzle spacing evidence on the 0.1 m gap; the merge rule; a planted `ValueError` in one lengthwise and one transverse hypothesis leaves the others intact and shows the escaped reason in the result and the report; a sweep of accepted degenerate observations on a small v1 and a small v2 case (duplicate, identical, single, unsorted, edge and out-of-strip positions; tiny spacing and spacing at the 10 m limit; band width larger than the strip; duplicate pitch observations, two pitches at one speed, a pitch larger than a coil circumference; a huge intermittent duration; duplicated and barrel-end blocked nozzles in the coolant screen and the width model; all observations null, every boolean true, every boolean false): `diagnose` returns and the report renders; the inputs rejected at validation are rejected with their message. Also the coil single-source, trough-spacing and perturbed-bite-model tests, moved here from `tests/test_band_v2_sections.py` |
| extended domain, product check, credibility / `tests/test_band_extended_domain.py` | **extended domain** (`CollectorFoilExtendedDomainTests`, 30 -> 17 um case pass): `bite_model: "hitchcock"` keeps its 20 um floor (`test_hitchcock_only_keeps_its_20_um_floor`); the mattress bite, its extended-domain flags and limitation (`test_extended_bite_flags_and_limitations`); tension lines lead, no model contradiction (`test_tension_lines_lead_and_no_model_contradiction`); report renders (`test_report_renders`). **Below the 8 um floor** (`BelowBiteFloorTests`, 12 -> 7 um): loads and diagnoses, floor and closed-gap flags, chatter and levers not assessable, shape chain not assessable, bite-free parts present (`test_loads_diagnoses_and_flags`, `test_report_renders`). **Product check** (`ProductCheckTests`): unknown ids, non-string and v1 use rejected with the list of ids (`test_validation`); `NOT_SUPPLIED` with the ids at foil gauge, absent at sheet gauge (`test_not_supplied_at_foil_gauge_absent_at_sheet_gauge`); a 36 -> 30 um pass reads `BELOW_PUBLISHED_RANGE` for the per-pass reduction, with the case and final-pass flags, and every score equals the run without a product (`test_findings_flags_and_no_score_change`). **Credibility gate** (`CredibilityGateTests`, the demo's final-pass material on the foil mill): a 25 -> 12 um case pass gets no model-based support or contradiction from the bite-dependent items, the gated items keep their verdict without the gate, scores are the tally of the gated evidence and the leading rule is unchanged; a 30 -> 18 um case pass (force inside the range) keeps its model evidence. **Coil, trough spacing, perturbed bites** (now in `tests/test_band_robustness.py`): one coil for all pitches (`CoilSingleSourceTests`: the reviewer's pitches 1 m at 2 m/s and 1.4 m at 20 m/s on coils of 1 m and 1.4 m pitch no longer give two exact matches; the coil hypothesis contradicts weakly and does not lead; two pitches on one coil still support; a single pitch as before); trough spacing (`TroughSpacingEstablishedTests`: one gap weak and never contradicting, irregular gaps weak, regular or stated spacing strong, a stated spacing outside a factor 4 still contradicts); perturbed bites (`PerturbedBiteModelTests`: an `auto` case with a mattress operating bite has every lever row equal to a direct mattress derivation; a Hitchcock operating bite reports the friction x1.3 variant Hitchcock rejects as a rejected row). **Onset search** (`OnsetSearchDomainTests`): the reviewer's soft-strip case (1e9 Pa, 9 um bump) no longer reports the old 4.28 um in-mill onset: the reported onset is manifest with feedback and the scale just below is not; a stubbed feedback calculation that leaves its domain before buckling gives the domain-limit outcome with its height, one that buckles first gives the onset, one that stays latent gives not-reached; a sheet-gauge case gives exactly the onset of the old search. **Undefined bound levels** (`UndefinedBoundLevelTests`, the reviewer's 8 um pass, one striped roll, 9 um bump, shape inputs 1e12 Pa / 1 mm / 0.01 m): `shape_levels` keeps both compliant levels with the rigid bound not defined and its reason, a very soft strip (1e9 Pa) keeps the feedback level with the compliance-only level not defined, a normal bump reports the rigid bound exactly as the direct calculation; through `diagnose` the steady shape and the gauge-trend row are assessed, the trend text names the pass without a rigid bound, the report omits the rigid curve with a note and has no nan / inf. **Large forward slip** (`LargeForwardSlipTests`, the reviewer's 30 -> 12 um pass on a 0.14 m roll): the mattress slip is at least 0.5, `diagnose` returns, both slip flags are set, the signatures use slip 0, the schedule row keeps its slip; the forward-slip screen is not assessable with the actual slip, the skid evidence does not support. **Case-pass credibility** (`CaseBiteCredibilityTests`): a 25 -> 12 um case pass with `auto` gets `FORCE_OUTSIDE_REPORTED_RANGE` with ratio above 2, the top flag, the limitation, the gated items (`model not credible`, "NOT CREDIBLE BASIS", `NEUTRAL`) and only bite-free model items left with basis `model`, a failed time simulation instead of an exception, and a report (`test_not_credible_case_pass`); a 30 -> 18 um case pass is marked inside the range with no flag (`test_credible_case_pass_has_no_mark`) |
| `band_products.py` / `tests/test_band_products.py` | catalogue integrity (unique ids, sources with URLs and valid read status, every fact sourced and its status never upgraded, ordered ranges with units, products validate, JSON round trip, battery depth); published reductions of the battery, pouch, packaging, litho and heat-exchanger schedules; `check_pass` on 50 -> 30 um, the 30 -> 18 um final pass, a 70 % pass, mode checks, flow-stress, alloy and fallbacks, errors and JSON; nearest published passes; `docs/thin-gauge-products.md` matches the generator and is complete; CLI; alloy-group and anisotropy tables (`AlloyAndAnisotropyTests`, SPEC17): the nine `TM-` sources with the read tags of the gap study and never an upgraded read status, ten alloy-group rows, the Hill 1948 plane-strain factor 1.154701 / 1.014185 / 1.046734 / 1.169130 for (1, 1), (0.2, 0.2), (0.2, 1.1), (1.075, 1.075) and `ValueError` for r <= 0, both sections in the generated document |
| `band_sensors.py` / `tests/test_band_sensors.py` | zone edges and coverage (body and edge zones, centre default, end zones 54 % covered); a 20 mm top-hat of 25 reads 9.6154 as the mean of a 52 mm zone; a 20 mm band of 3.1 I-units reads 1.19; a uniform profile reads zero; the roll mean of a mean-free, fully covered profile is zero; spreading conserves the sum and s = 0 is the identity; the dilution closed forms against the numbers of SPEC17 and a sampled Gaussian; on the committed battery-foil profile the zone readings 6.5973 / 20.4506 / 24.4912 / 20.4517 / 6.5979, the tight edges, the half-peak width 0.160 m, spreading 23.4812, the event 19.3326, the ripple 0.5296 and 23 zones 23.5348; one nozzle per zone (zone j holds nozzle j + 2 at its centre) from `band_width.spray_layout` and the boundary rule; every validation message, v1 and a non-null thickness gauge rejected; a small case with and without a shapemeter differs only in `measurement`, `inputs` and the new flags, hypotheses identical, the report escapes the provenance; no width model is not assessable with the dilution table |
| `band_width.roll_profile_section` / `tests/test_band_roll_profile.py` | the hand profile of SPEC17: local deviation +2.5827e-7 m at 0.4975 m (half-peak 22.7 mm) and -1.8181e-7 m at 0.9525 m, bands +3.1289 (latent / manifest after release) and -2.0433 (latent / flat), compliance only 360.27, rigid 860.90; a 23-zone shapemeter reads 1.1780 (0.3765) and -1.0989 (0.5378), "would probably not show"; strip foundation modulus 958605/20e-6, roll term 6.212e10 Pa at 45.4 mm (the brief's 6.493e10 is the same formula at 40 mm); no de-trending keeps the crown, two rolls double the rigid bound, the combination with the thermal stripe, not assessable without shape parameters, validation; a small case with and without a profile differs only in `width.roll_profile`, `inputs` and its flags, hypotheses identical |
| `band_width.candidate_tension_line_pitch` / `tests/test_band_foil.py` (`CandidateTensionLinePitchTests`) | coefficient 3.4746; the pitches 6.7285 / 7.3707 / 12.766 / 14.7414 mm at 30 um, 5.2119 / 5.7093 / 11.4187 at 18 um, 4.2555 at 12 um; the critical stress 10.2751 MPa = minus the roller-wrinkle value; the three statuses; the battery-foil block; every evidence item and the score of `foil_tension_lines` equal the committed ones |
| `strip_shape.transfer_force_profile` / `tests/test_strip_shape.py` (`TransferForceProfileTests`) | a single sinusoid of force `-n*dR/(2*C(lam))` gives the roll-bump transfer of `dR` to 1e-9, with and without feedback; zero force gives zero; the mean component keeps Q; positive force gives a thicker strip; the feedback-dominated limit `-dp0'/(N_x'*E)` at two gauges; validation; the radius transfer unchanged |
| `band_width.friction_stripes_section` / `tests/test_band_friction_stripes.py` | the battery-foil per-pass table (force, load exponent, I-units per 1 % with feedback and compliance only, pinned within 1 % of the planner's prototype); exponent and compliance-only magnitude rise along the plant's route S1-F2, the with-feedback values lie within a factor 2; the trend text and its fixed last sentence; the reporting-threshold fraction 0.00635 and the feedback limit -3.49; supplied stripes of -10 % / +10 % (-78.7 nm, +32.9 / -32.7 I-units, loose manifest after release / tight flat); the flagged placeholder conversion (+3.2e-4 per K); ALT2 marked not credible and left out of the trend; validation messages; not assessable without a bite; a small case with and without a screen differs only in `width.friction_stripes`, `inputs` and the flag, hypotheses identical; the report renders |
| `strip_shape.thermal_flatness_term`, `band_width.strip_temperature_section` / `tests/test_band_strip_temperature.py` | a 1 K step over half the strip gives 2.36 I-units (1e-9), a custom coefficient scales linearly, the default sets the flag; a uniform temperature gives zero and equal profiles; on the committed battery-foil profile with the demo scan: 2.36 I-units/K, mean 353.416125 K, deviation 2.332175 K, thermal +5.5039 / -0.6281 (alone one band 0.560-0.685 m, peak 5.5039 at 0.6025 m), mechanical bands and states equal to the width section's, as measured hot 30.4694 at 0.6175 m (0.495-0.745 m) and tight -5.8106 / -5.8524, held-flat bound -5.5039, no state change, shapemeter zone 9 29.8136 hot against 24.4912; the committed section equals a fresh one; without a mechanical profile the thermal term alone with its flag; a hand case where the term lifts a 1.5 I-unit band above the threshold is a reported state change; a scan not covering the strip holds its end values and reports 0.6 m; every validation message; a small case with and without a scan differs only in `width.strip_temperature`, `measurement`, `inputs` and flags, hypotheses identical; the report renders |
| `band_sensors.py` (gauge) / `tests/test_band_sensors_gauge.py` | the three worked gains of SPEC17 to 1e-6 (190.2950 Hz: 0.976894, 0.164980, 0.161168; 189.6168 Hz: 0.160936; 314.3253 Hz: 0.076109); limits (L -> 0 and tau = 0 give 1, L = p gives 0); aliasing; the shortest resolvable pitch is a root of G = 0.5 with every longer pitch kept; amplitude before the gauge; validation messages and the barrel check; bands under a gauge at 0.75 m on the battery-foil profile ([0.49, 0.75] m) and none at 0.77 m (flag); on a v2 copy of the thin-gauge chatter demo with "gauge variation not detected" the three flags are set, the note names the hypotheses, and every hypothesis, evidence item and score equals the run without the gauge; the report table renders and escapes |
| `band_thermal.py` / `tests/test_band_thermal_check.py` | the thermal check against the literature (SPEC14); SPEC17 (`SprayBasisAndFireLimitTests`): the spray finding keeps `WITHIN_PUBLISHED_RANGE` and carries the basis keys and the flag; a 60 degree arc gives 20450 W/m2K `ABOVE_PUBLISHED_RANGE`, an arc outside (0, 2*pi] is rejected; fire limits not supplied without inputs (context sources present), a 80 C flash point gives a 35.0 K margin on the 45 C oil inlet, a pass at 95 C reads `AT_OR_ABOVE_LIMIT` with its flag, a 40 C site cap flags the oil, limits outside 250-700 K are rejected |
| local state across the width / `tests/test_band_local.py` | formulas 2-7 against their closed forms to 1e-9 on a hand profile (0, 1, 2.358 K), with the exponential law and a two-point viscosity table that reproduces it; the planner's numbers of section 7.11 (2 %, coupling 5 %) and the implementation's own pinned to 1e-4; the friction change equals the closure slope times the film-ratio change within 1 % for 0.1 K (placeholder and load-sharing closures); a zero profile gives zeros and no conditional flag; supply: the three numbers, a level of 1e-4 starved, a blocked nozzle gives zero film and its flag; supplied against computed coupling, and the coupling independent of the roll entry temperature (linearity); flow-stress coefficient from the key, from `hardening.rate_temperature` or absent with the reason; validation messages; a healthy header gives zero; one coarse diagnosis: section present, with the key absent every other result key equal and the hypotheses identical; with a layout the healthy bite entry temperature of the surface cycle is used (equal to the actual one for a healthy header) |
| flatness loop parts / `tests/test_roll_thermal.py` (`ControlledRunTests`), `tests/test_flatness_control.py` | `ControlledRun` equals `simulate` over a two-segment valve event to 1e-12 (field, radius, surface; ledger 1e-9; same steps and start-ups); constant levels from a steady start stay steady (radius 1e-11 m, surface within the steady solver's 1e-6 K, equal to `simulate`); one start-up per level change, cache cap; weighted-orthonormal low-order basis, a parabola removed at order 2 and not at order 1; the two-zone hand case (gain, corrections, demands to 1e-6, dead band, dwell); hysteresis; a fast square-wave demand cannot switch a valve faster than its dwell; clipping; a supplied actuator removes its own vector; a synthetic first-order plant settles with 5 % valves and switches at the dwell bound with two-level valves; delay FIFO, display filter, history thinning, JSON safety |
| grinding rules / `tests/test_band_grinding.py` | feed-mark ceiling (45 and 53 mm support weakly, 70 mm neutral, an irregular spacing stays neutral; the criterion string and its plain entry; the feed note's tags); grinder chatter: a 6 mm pitch on a 280 mm work roll without grinder data is neutral with the flag, the backup roll and implied counts of 10 or 300 keep the old rule, a count computed from wheel and roll speed (146.6, not rounded) supports and a non-fitting computed count contradicts (never neutral), vibration frequency in place of the wheel, validation messages naming the entry, the catalogue order, the app round trip in r/min; the cosine crown (0.660 um after order 2 within 10 % of 0.68, 0.006 um after order 4, no band with the default order); the 21-station grid flag and the observed band width as reference |
| local sources / `tests/test_band_local_sources.py` | a single sinusoid of friction gives `-1e5*xi*G(lam)*M_mu*dmu/h` to 1e-9 with the feedback and compliance only (compliance only larger); signs (more friction tight, softer metal loose, hotter fibre loose); zero changes give zero terms and the net equals the roll term; sums; a missing term named and "the net is incomplete"; the sign words; on a coarse case with a valve event: the section, event rows with the key and not-supplied rows without it, event histories and every other result identical, the report block only with the key and without `nan`; the battery-foil artifact against the planner's peaks (15 %, the flow-stress term 20 %) and pinned to 1e-6 |
| absent optional inputs / `tests/test_band_absent_inputs.py` | the template diagnosed with the SPEC17 optional keys set to `null` and with them absent gives the identical `result_json` |

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
- **The spray calibration fits one number of this model** (section 7.1): a circumferential-mean
  coefficient for the whole header, with the background coefficient, heat share, bite heat,
  coolant temperature and roll properties taken from the case (their errors go into the fit);
  end effects not modelled; the after-stop phase uses the background coefficient only; the
  grid changes the value by a few per cent; command line only, never applied.
- **The roll surface cycle is one-way** (section 7.10): it never changes the bulk field, the
  stripes or the shape; one-dimensional per axial station (no axial conduction in the layer);
  uniform flux in the bite; no backup contact unless entered; wipers and oil carry-over not
  modelled; the layout angles are entered, not measured by the tool; its time scales are a
  comparison with the plant's 20 s, not an explanation (A6 not built).
- **The computed heat partition is a reduced interface model** (section 8.2): lumped strip,
  uniform heat over the contact, roll curvature neglected, no asperity conduction (no formula
  in the reports), film from the smooth inlet formula, roll entry temperature assumed, not
  coupled back into flow stress or film, not calibrated and not width-resolved; the entered
  share drives every result unless the option is set.
- **Flow stress against rate and temperature is a form without data** (section 8.3): the rate
  sensitivity was measured five decades below rolling rates, the net of rate and temperature
  at rolling conditions is not known, the strain rate uses the undeformed arc, the bite
  temperature is a mid-bite estimate, no law is selected by alloy group, no recovery term,
  and the rate share of the bite damping is reported only.
- **Friction from pass records is reported, never applied** (section 8.5): it is identified
  with a constant friction through the bite (a friction distribution is the published remedy
  for foil slip and is not built), it absorbs the bite model's own error (12 % from load and
  30 % from slip on the published case), the flow stress is taken as entered, the entered
  numbers are not verified (`calibrated` false), and with a no-slip zone the slip carries
  little friction information.
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
  Partly open. The strip-temperature term in measured flatness (section 7.7) is one of two
  candidate causes the literature adds (X5); it is not tested here.
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
- **Measured roll profile** (section 7.9): one roll, measured cold and off the mill; narrow
  marks smoothed by the grid and by 4a; no wear growth, no roll-stack modulation; never
  evidence.
- **Candidate tension-line pitch** (section 3.7): a candidate, not evidence; no onset condition,
  no air-film or winding model.
- **Friction-stripe screen** (section 7.8): linear, from `dF/dmu` of a constant-friction bite
  (at foil gauge the mattress bite, 0.42 of the reference load on the one benchmark) and an
  unconfirmed exit-tension feedback; the with-feedback level shows no gauge trend while the
  compliance-only level grows; no film model across the width, no starvation, no coupling to
  the roll temperature; no evidence item.
- **Strip temperature term** (section 7.7): the scan is supplied, not computed (no per-width
  heat balance, A3); the expansion coefficient defaults to a textbook value from memory;
  without a controller `after_cooling` equals the mechanical profile, and the held-flat case
  is only a bound; no coil cooling or creep.
- **Thickness gauge transfer** keeps about a fraction of a mark: a spot average and a
  first-order lag only; real gauges have other filters; the evidence is not changed when the
  gauge cannot resolve the observed pitch (flag only); no accelerometer model (section 11.6).
- **Shapemeter readings are zone means of a model**: no flatness controller (the tool does not
  predict what the control would have done), no shapemeter dynamics, filter, noise,
  calibration or temperature compensation; neighbour spreading is an interpretation of one
  vendor sentence and off by default (section 7.6).
- **Spray-coefficient basis not established**: the model's coefficient is a circumferential
  mean, the published 2.5-4.3 kW/m2K is read as a jet-zone value; until PT-T18 is re-read the
  `thermal_check` verdict compares two possibly different bases (flag
  `SPRAY_COEFFICIENT_BASIS_NOT_ESTABLISHED`; section 3.12). If it is a jet-zone value the demos'
  coefficient would be several times too high and the modelled stripes too low.
- **Fire limits are a rule check**: no oil-mist or vapour model; the limits are the user's and
  the modelled strip exit temperature is not a coil temperature (inflated at foil gauge by the
  mattress slip).
- **Isotropic plane-strain factor** `2/sqrt(3)` in every bite; published r-values of one foil
  would move it by -12 % to +1 % under Hill 1948 (section 8.3); no alloy-group hardening data
  enters any law.
- **No film-collapse test** for the heat-streak hypothesis: the gap study's test (film against
  additive length or contact temperature) needs the friction closure BT-G3 and BT-G11; since
  SPEC17 only a supplied exit-temperature limit can support that item. The herringbone rule
  keeps its weak support for a film ratio below 1 (worded "substantial asperity contact"),
  although a film ratio below 1 is normal mixed-regime operation [BT-S3 EX, BT-S9 EX] (open
  decision 1 of SPEC17: scoring left, wording changed).
- **Mattress bite model is experimental**: on the one published case with every input stated
  (BT-V1, Fleck et al. 1992 Fig. 9 [FT]) it returns 0.42 of the half-space reference load
  [run], a recorded discrepancy (10.2, `physicroll/benchmarks.py`); no elastic strip zones,
  Hertz-calibrated foundation modulus; foil-regime numbers are order of magnitude only.
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
- **The friction level is not known.** Neither friction law has a published level for your
  mill: the placeholder is unfitted, and the load-sharing closure takes its level from an
  entered contact friction (0.013 to 0.1 in the sources) on a contact-ratio curve published for
  one foil pass; no inlet analysis is built (section 8.1).
- **Oil properties at bite pressure are not known.** For the one foil oil with data neither
  the Barus law (default) nor the Roelands law (option) follows the measured viscosity above
  100 MPa (Roelands low by a factor 12 to 30); no source gives a limiting shear stress for a
  rolling oil (only a lower bound 0.045 of the pressure for one base oil); the Eyring stress
  is known for one base oil without additives (section 8.1).
- **Grinding rules (SPEC20)**: no amplitude of grinder marks on foil rolls is published (the open
  figures are for hot-mill rolls and slender shafts); the feed-mark ceiling of 60 mm and the
  12-240 count range come from printed grinder settings in patents and trade pages; none of
  this was checked on a mill.
- **The local sources of a hot stripe are linear and rest on the exit-tension feedback**
  (section 7.11): their sum is taken on the linear-feedback profile; `dF/dmu` and `dF/dY` are
  those of a constant-friction bite; the film term's sign against the roll path depends on the
  assumed inlet weight in the first tens of seconds after a valve change; nothing feeds back to
  the roll temperature and no evidence item reads them.
- **The local state across the width is one-way and rests on an assumed inlet weight**
  (section 7.11): differences from the healthy header only; the share of a roll temperature
  difference that reaches the inlet oil (default 0.5) has not been measured; the local friction,
  force and heat changes do not return to the roll temperature (loop I1 open); no oil spreading
  or carry-over, no inlet meniscus position (the oil supply is a volume balance); the friction
  heat change is left out; the strip entry temperature and the roughness are uniform across the
  width.
- **The reduced half-space bite (`halfspace_bite.py`) is opt-in** (`model_options.bite_model`)
  and unvalidated: it leaves out the longitudinal elastic equations of its source, closes
  the bite ends by contact zones where the source uses a pressure step (the published loads
  depend on an unstated end length), and carries a strip thickness spring that is the
  planner's addition (+4.6 % load on the published case). At the regime boundary neither
  the no-slip structure nor zone E is admissible and the sheet-like structure is used, with
  the other candidate reported (1.7 % apart in force on the battery-foil case pass); its
  rule against the degenerate branch (`SLIP_CONSISTENCY`) is the project's own (section 10.3).
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
- **Tension lines have no established model**; `foil_tension_lines` is a rule set with analyst
  weights [D] on a published description [BF-S21, excerpt of a trade report of a producer
  talk; V S27, S28]; one candidate pitch (shell buckling of the wound lap, section 3.7) is
  reported for comparison only, never as evidence.
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
report "A simple model for the cold rolling of metal foil"; Stone (from memory); Fleck,
Johnson, Mear & Zhang (1992) Cold rolling of foil, Proc. IMechE B 206:119-131 (full text, scan;
read by the bite gap report, BT-S1; benchmark cases of `benchmarks.py`).

Phase 1 equation note (`docs/research/band-screening-2026-11/phase1-equations.md`, prefix `E`;
read tags as the note gives them): E1 Fleck, Johnson, Mear & Zhang (1992), the same paper as
BT-S1 [FT, scan read as images; eqs (20), (30)-(32), (36), Appendix 3 and Fig. 9 re-read on
enlarged crops; the governing set of `halfspace_bite.py`, section 10.3]; E6 Sutcliffe (1989) Friction and lubrication in metal rolling, PhD thesis,
Cambridge [FT for chapter 2, sections 3.2.1 (part), 3.3, 3.4, 4.2-4.3, 4.7-4.8, Tables 2.1, 4.1,
4.2, Fig. 2.7]; E9 Niroomand, Forouzan & Salimi (2015) ISIJ Int. 55(3):637-646, the TM-LC7 mill
[FT, sections 3-5 and all tables; section 2 skimmed]; E5 Boemer (2020) Numerical modeling of
friction in lubricated cold rolling, PhD thesis, Liege [FT for the sections read, among them
4.8.1.3-4.8.3 and Appendix L: the Roelands law, and 4.7.1, 4.8.1.3: the crushing and
flow-factor fits]; E4 Sutcliffe & Montmitonnet (2001) [EX: Table I, friction laws]; E7 Le &
Sutcliffe, semi-empirical friction model (author manuscript) [FT of the manuscript text,
equations partly damaged: the load-sharing law, its eq. 7]; E6 also for the kerosine base oil data
(Table 2.1, Fig. 2.7) and the film table (Table 4.2).

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
