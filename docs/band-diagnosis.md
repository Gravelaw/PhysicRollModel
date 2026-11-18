# Band root-cause screening (lengthwise bands and transverse chatter marks)

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
statements in their docstrings.

Every demo number in this document is read from the generated results
`artifacts/band_diagnosis/*.result.json`; the file is named at each table.

## 1. Purpose, scope and what is established

The tool answers one question for a cold-mill process engineer: given what has been observed
on the strip, which band mechanisms are consistent with the observations, which are
contradicted, and what measurement would separate the remaining ones. It covers two
families of bands:

- **Lengthwise bands**: stripes that run along the rolling direction at fixed positions
  across the width (loose or tight bands, buckles, shade stripes, creases), continuous along
  the coil or present only for a while. Mechanisms: a blocked or partly blocked spray nozzle,
  cooling-zone switching, roll-surface bands, grinding feed lines, incoming ridges that
  build up in the coil, tension troughs, profile / flatness mismatch, heat streaks, oil stain.
- **Transverse marks**: marks across the strip that repeat along its length at a pitch
  (chatter marks). Mechanisms: third-octave self-excited chatter, fifth-octave stack
  resonance, roll-borne marks, bearing / gear orders, torsional drive vibration, coil-locked
  marks, yield-point bending marks, herringbone, skidding.

What is established, and what is not. The software is verified: the equations are
implemented as written and reproduce their analytic limits (section 12). The physics is
not validated: no number from this tool has been compared with a measurement on a mill.
Several inputs are placeholders (the friction closure), supplied guesses (the heat split
between strip and rolls, the spray heat-transfer coefficients) or analyst choices
(evidence weights, thresholds). The ranking is an evidence tally: a leading hypothesis is
the one most consistent with the observations as entered, not a confirmed cause. The
"confirming test" listed with each hypothesis is the step that can confirm it on the mill.

The tool was built in two phases. Phase 1: the transverse family (chatter model, pitch
signatures, levers, schedule sweep). Phase 2: the lengthwise family (roll thermal model,
strip shape and flatness), coupled process models (lubricant-dependent friction, pass
heating, hardening), gauge control and drive dynamics, an experimental thin-gauge roll-bite
model, case schema v2, nine lengthwise hypotheses and new report sections.

## 2. Which path to read

| your bands | read |
|---|---|
| run **along** the strip at fixed width positions | sections 3-4 (run, observations), 5.2 (lengthwise rules), 6 (lengthwise physics, including thin gauge and short-lived bands), 11 (report), 13 (limitations) |
| run **across** the strip and repeat along it | sections 3-4, 5.3 (transverse rules), 10 (chatter physics), 7-9 as needed |
| not sure | record the orientation first (section 4.1); the report states which family the observations point to |

Both families are always evaluated: a lengthwise case also reports the chatter results, and
the transverse hypotheses are then contradicted by the longitudinal orientation.

## 3. How to run

```
python -m physicroll.band_cli scenarios/band_diagnosis_lengthwise_bands.json --out artifacts/band_diagnosis
python -m physicroll.band_cli scenarios/band_diagnosis_thin_gauge_chatter.json --out artifacts/band_diagnosis
python -m physicroll.band_cli scenarios/band_diagnosis_bearing_order.json --out artifacts/band_diagnosis
python -m physicroll.band_cli my_case.json --out my_output_dir
```

Each run validates the case, writes `<case-name-slug>.result.json` (deterministic: sorted
keys, no timestamps) and `<case-name-slug>.report.html` atomically, and prints the ranked
standings. Running the three demo commands into a scratch directory reproduced the
committed result files byte for byte. On this container (Python 3.13) they took about 66 s
(lengthwise), 22 s (thin-gauge chatter) and 12 s (bearing order). From Python:
`from physicroll.band_diagnosis import load_case, diagnose`.

Which demo to look at:

| demo | schema | what it shows |
|---|---|---|
| `scenarios/band_diagnosis_lengthwise_bands.json` | v2 | lengthwise bands at three width positions, one continuous (a partly blocked nozzle) and two short-lived (cooling-zone switching), worse at thinner gauge; every phase-2 section (roll thermal, shape, gauge trend, events, process, gauge control, drive, incoming hardness) |
| `scenarios/band_diagnosis_thin_gauge_chatter.json` | v1 | transverse third-octave chatter at the final pass of a six-pass schedule; the chatter schedule sweep and levers |
| `scenarios/band_diagnosis_bearing_order.json` | v1 | transverse marks from a work-roll bearing order (speed-independent pitch) |

All three are `synthetic: true` and their observations were generated from the model
itself, so they test the screening logic, not the physics.

## 4. Filling in the template for your mill

Copy `scenarios/band_diagnosis_template.json` (schema `physicroll.band_case.v2`,
`synthetic: false`, which adds the flag `USER_SUPPLIED_INPUTS_NOT_VERIFIED`). Its `notes`
explain every field. Replace the mill, pass and material numbers with your own, in SI
units (m, Pa, kg, N/m, m/s, Hz, rad, K); the values in the template are the synthetic demo
mill. Keys are strict: unknown or missing keys are rejected. **Leave an observation `null`
when nobody has looked**: `null` always gives `NOT_OBSERVED` evidence and never counts
against a hypothesis.

Schema v2 is v1 plus six optional sections (`null` = not supplied; the result section then
says `NOT_SUPPLIED`), the option `model_options.bite_model` and thirteen lengthwise
observation fields. v1 case files still load and run unchanged.

| section | what it switches on |
|---|---|
| `width_model` | work-roll thermal model and strip-shape chain (lengthwise bands): roll properties, spray header, coolant temperature, nozzle levels or blocked nozzles, switching events, and optional crowns, incoming ridges, coil, previous strip widths, grinding, cooling-zone pitch, deflector radius, lateral compressive stress |
| `tribology` | rolling-oil viscosity law, roughness, temperatures, strip heat fraction: film thickness, placeholder friction, pass heating; also supplies the roll heat fraction to `width_model` |
| `hardening` | power or Voce law; with `use_computed_flow_stress` the computed flow stress replaces the supplied one on every pass |
| `gauge_control` | gaugemeter AGC compensation gain, cylinder bandwidth, optional force filter |
| `drive` | drive-train inertias and shaft stiffnesses (torsional modes) |
| `incoming_variation` | relative hardness variation of the incoming coil, once per decoiler revolution or not |

`width_model.roll_heat_fraction_per_roll` may stay `null` only when `tribology` is given
(it is then `(1 - strip_heat_fraction)/2`). `bite_heat_per_width_w_m` may stay `null`: it is
computed from the pass (section 7.2).

### 4.1 Which observations matter most for lengthwise bands

In order of how much they separate the lengthwise hypotheses (section 5.2):

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
   (section 6.2) and the evidence rules compare them with this observation.
5. **Spacing against the nozzle and zone pitch** (`band_spacing_m`, or the gaps between
   observed positions). Gaps that are integer multiples of the nozzle pitch or the
   cooling-zone pitch support the coolant hypotheses; a regular fine spacing near the
   grinder traverse per revolution supports grinding feed marks; a spacing of 0.5-2 x the
   computed trough wavelength supports tension troughs.
6. **How long a short-lived band lasts** (`intermittent_duration_s`), seconds of rolling.
   It is compared with the model's visible time of a band after a zone switch (section 6.4).
7. **Thin-gauge dependence** (`worse_at_thinner_gauge`), the **coolant header** geometry and
   flow levels in `width_model`, and for coil-related causes `worse_toward_outer_wraps`.

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

### 4.2 Which observations matter most for transverse marks

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
   grinder-mark counts, deflector roll and coil diameters. Without bearings and gears the
   drive/bearing hypothesis is `NOT_OBSERVED`.

## 5. Hypotheses and evidence rules

### 5.1 Scoring

Nineteen hypotheses are evaluated for every case, v1 or v2: ten transverse and nine
lengthwise (phase 1 had twelve; its two lengthwise hypotheses, coolant/thermal band and
roll-surface band, were replaced by the nine below). Each hypothesis carries `mechanism`,
`model_prediction`, `evidence` items `{criterion, observed, expected, verdict, weight,
basis}`, tallies, `score`, `standing`, `confirming_test` and `levers`. `basis` is
`observation` (a plant observation), `model` (a model result) or `input` (mill data).

Verdicts: `SUPPORTS`, `CONTRADICTS`, `NEUTRAL`, `NOT_OBSERVED`; weights strong / moderate /
weak. **Score = sum of supports (3/2/1) - sum of contradictions (6/2/1).** Standing:
`CONTRADICTED` if any strong contradiction; `NOT_ASSESSABLE` if nothing but
`NOT_OBSERVED`/`NEUTRAL`; `CONSISTENT_LEADING` for the non-contradicted hypotheses with the
highest score, provided that score is at least 3 **and the hypothesis has at least one
supporting plant observation** (a model result alone never makes a hypothesis lead);
`CONSISTENT` if score > 0; else `WEAKENED`. Rank: non-contradicted first, then score
descending, then id. **The score is an ordinal tally, not a probability**: a score of 20
against 17 says one hypothesis collected more weighted agreement with the observations as
entered, not that it is more likely by any stated amount. The weights are engineering
judgement (section 13).

`family_summary` states which family the recorded orientation points to and which family
the leading hypothesis belongs to. `recommended_next_measurements` collects the confirming
tests of the top three ranked hypotheses plus one line per key missing observation.

### 5.2 Lengthwise hypotheses

Common rule: orientation `longitudinal` supports moderately; any other recorded orientation
contradicts every lengthwise hypothesis strongly. Position match tolerance: one quarter of
the nozzle pitch (analyst choice). "S" = supports, "C" = contradicts, with the weight.

| hypothesis | mechanism | supports | contradicts | confirming test |
|---|---|---|---|---|
| `nozzle_thermal_stripe` | A blocked, partly blocked or mis-aimed nozzle leaves an under-cooled stripe; the work roll grows there and over-rolls the strip into a loose band (latent under tension, manifest once it buckles). | position on a modelled stripe or a weak nozzle (S str); continuity continuous or both (S mod); positions repeat across coils (S mod); positions stay after a work-roll change (S mod); gaps all multiples of the nozzle pitch (S mod); appearance loose_or_buckle (S mod); model band at an observed position (S mod, model); tension-release observation agrees with the model states (S mod); loose_or_buckle with a band manifest in the mill (S mod); worse at thinner gauge (S weak); both faces (S weak) | no observed position on a predicted one (C weak); only intermittent (C weak); positions do not repeat (C mod); positions move after a work-roll change (C mod); stain or crease (C weak); tension-release observation disagrees with the model (C weak) | spray footprint check and header inspection; band positions on three consecutive coils against nozzle positions; shapemeter zone map |
| `cooling_zone_switching_transient` | Zone cooling valves or an intermittently blocking nozzle switch a zone off and on; each switch grows a stripe for tens of seconds and it fades over about a minute: short-lived bands. | continuity intermittent or both (S str); changes with zone switching (S str); observed duration within 0.3-3 x the model visible time (S mod, model; without events, 0.3-3 x the 20-120 s literature range, S weak); position on an event nozzle or event stripe (S str); gaps multiples of the zone pitch (S weak); positions do not repeat (S weak); loose_or_buckle or tight (S weak); worse at thinner gauge (S weak); tension-release rules as above | only continuous (C mod); does not change with zone switching (C str); tension-release disagreement (C weak) | log valve states against shapemeter zones and band times; compare band duration with valve-off intervals |
| `roll_surface_band` | A wear band, pick-up streak or two-tone step at the edges of earlier narrower strip prints at a fixed width position until the rolls are changed. | positions change (or band disappears) after a work-roll change (S str); follows previous strip edges or on a two-tone position (S str); repeat across coils (S mod); continuous (S mod); gloss_or_shade (S mod); one face (S mod) | positions stay after a work-roll change (C str; "does not disappear" C mod); intermittent (C mod); loose_or_buckle (C weak); changes with zone switching (C mod) | roll-surface inspection at the band positions; work-roll change test; compare with earlier narrower widths |
| `grinding_feed_marks` | Helical feed lines from the roll grinder; the lateral pitch is the traverse per roll revolution. | every gap within 10 % of 1-3 x the feed pitch (S str); regular spacing (CV < 0.15) below 30 mm (S weak); positions change after a work-roll change (S mod); gloss_or_shade (S mod); continuous (S weak) | gaps not matching (C mod); positions stay after a work-roll change (C str) | measure the spacing against the grinder traverse per revolution; roll inspection; roll change |
| `incoming_ridge_coil_buildup` | A local high spot in the incoming profile stacks up wrap by wrap in the coil, stretches the band beyond yield and leaves a tight-then-loose band, worse toward the outer wraps. | positions do not repeat across coils (S mod); worse toward outer wraps (S str); position on a supplied ridge (S str); model ridge yields the strip (S mod, model); intermittent with 5-95 % of the coil length affected (S weak); worse at thinner gauge (S mod); visible only after release (S weak) | positions repeat (C mod); positions change after a work-roll change (C weak); not worse toward outer wraps (C mod); model ridge does not yield (C weak, model) | entry profile scan of the incoming coil and outside-profile scan of the wound coil |
| `tension_troughs_or_creases` | Lateral buckling of thin strip under tension in a free span (troughs), which a roll can iron into a crease. | spacing 0.5-2 x the computed trough wavelength of either span (S str); crease_or_flute (S str); changes with tension (S str); model troughs expected (S mod, model; needs `lateral_compressive_stress_pa`); intermittent or both (S weak); worse at thinner gauge (S mod) | spacing outside 0.25-4 x both wavelengths (C mod); stain (C mod); does not change with tension (C str); model below the trough threshold (C weak); positions change after a work-roll change (C weak) | vary the span tension and watch the bands; check deflector / idler alignment and crown; measure the trough spacing |
| `profile_flatness_mismatch` | Relative crown change between entry and exit outside the Shohet-Townsend dead band: smooth edge waves or a centre buckle rather than narrow stripes. | crown change outside the dead band (S str, model); all positions within 15 % of the width of an edge or of the centre (S mod); band width > 150 mm (S weak); loose_or_buckle (S mod); visible only after release (S weak); worse at thinner gauge (S mod) | crown change inside the dead band (C mod, model); two or more interior positions (C mod); band width < 60 mm (C weak) | entry and exit profile measurements; shapemeter map; compare relative crowns |
| `heat_streak_or_film_variation` | Local oil-film variation from heat: milky bands that wander in width and position. | gloss_or_shade (S mod); no gauge variation (S weak); positions do not repeat (S mod); intermittent or both (S mod); worse at higher speed (S mod); boundary film regime or exit temperature above a supplied limit (S weak, model) | crease_or_flute (C mod); positions repeat (C weak); positions change after a work-roll change (C weak) | compare band appearance with oil temperature and speed; check whether the bands wander between coils |
| `oil_carryover_drips_or_stain` | Coolant carried past the wipers, drips, or staining seen after annealing. | stain (S str); one face (S mod); intermittent (S weak); positions repeat (S weak) | loose_or_buckle or crease_or_flute (C mod); changes with tension (C weak) | anneal a sample and look for stain; inspect wipers and drip shields |

The tension-release rule used by the two coolant hypotheses compares the observation with
the model states of the bands at the observed positions (steady stripes for the nozzle
hypothesis, event peaks for the zone hypothesis): observation "only after release" true
supports moderately when a model band is latent in the mill and manifest after release, and
contradicts weakly when a model band is manifest in the mill; observation false supports
moderately when a model band is manifest in the mill and contradicts weakly when all model
bands are latent in the mill.

### 5.3 Transverse hypotheses

Notation: `f_obs = u/p` per pitch observation (plus `measured_vibration_hz` when given);
`law` = pitch-speed classification (needs two distinct speeds); `red` = pass reduction;
`u_op` = operating exit speed.

| # | id | rules (verdict, weight) |
|---|---|---|
| 1 | `third_octave_self_excited_chatter` | transverse S mod; longitudinal C str; diagonal/chevron C mod. law FIXED_FREQUENCY S str; SPEED_INDEPENDENT C str. `f_obs` within +-15 % of model dominant/onset frequency S str, else 90-300 Hz S mod, outside 60-400 Hz C str. gauge variation detected S str, not detected C mod. faces both S weak, one C mod. `u_op >= u_crit(beta)` S str; `u_crit(0) <= u_op < u_crit(beta)` S weak; `u_op < u_crit(0)` C mod. onset speed within 0.6-1.6 x `u_crit(beta)` S mod, otherwise S weak. disappears after any roll change C mod. worse at thinner gauge S weak. **Phase 2:** when the model onset or dominant frequency lies above the span-wave limit `c/(2L)` the speed-margin item is NEUTRAL and the model-frequency match is skipped (flag `CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT`). |
| 2 | `fifth_octave_roll_stack_resonance` | orientation as 1. `f_obs` within +-15 % of the antisymmetric upper mode S str, else 500-1200 Hz S mod, below 300 Hz C str. pitch 10-40 mm S mod. gauge variation not detected S mod, detected C weak. law FIXED_FREQUENCY S mod; SPEED_INDEPENDENT S mod if `pi*D_b*(1+f)/p` within 0.05 of an integer, else NEUTRAL. order-locked source within +-10 % of the antisymmetric upper mode at `u_op` S mod. disappears after backup-roll change S mod. faces both S weak. |
| 3 | `work_roll_borne_marks` | law SPEED_INDEPENDENT S str, FIXED_FREQUENCY C str. pitch = `pi*D_w*(1+f)/n` within 3 % for n = 1..8 or a supplied grinder-mark count S str, no match C mod. work-roll change: disappears S str, persists C str. faces one S mod, both C weak. longitudinal C str. |
| 4 | `backup_roll_borne_marks` | as 3 with `D_b`; backup-roll change disappears S str, persists C str; disappears after work-roll change C str. |
| 5 | `order_locked_drive_or_bearing_excitation` | law SPEED_INDEPENDENT S str, FIXED_FREQUENCY C str. best gear / bearing / spindle source within 5 % S str (named); no gear and no bearing supplied NOT_OBSERVED; supplied but no match C weak. persists after both roll changes S weak. faces both S weak. longitudinal C str. |
| 6 | `torsional_or_low_frequency_drive_vibration` | `f_obs` 5-30 Hz S str, above 60 Hz C str. **Phase 2:** with a `drive` section, within +-15 % of a computed torsional mode S str, above max(60 Hz, 1.5 x highest mode) C str. pitch 0.1-3 m S weak. law FIXED_FREQUENCY S mod. longitudinal C str. |
| 7 | `coil_or_mandrel_locked_marks` | pitch within 10 % of `pi*D_exit_coil` or `pi*D_entry_coil*h0/h1` S str; coil diameters not supplied NOT_OBSERVED; supplied but no match C weak (gap filled, 5.4). first seen incoming S weak. law FIXED_FREQUENCY C mod. |
| 8 | `yield_point_bending_marks` | not susceptible C str, susceptible S mod, unknown NOT_OBSERVED. diagonal/irregular S mod, chevron/longitudinal C mod. a regular law C mod. first seen incoming or after bending/levelling S str; at bite exit with `red > 0.02` C str. a deflector/coil in the yield-point window S mod, none C weak. worse at thinner gauge C mod (`t/D` falls with gauge). |
| 9 | `herringbone_lubricant_film_breakdown` | chevron S str, diagonal S weak, longitudinal C str. `red >= 0.40` S mod, `red < 0.25` C mod. pitch 0.5-2 x contact length S str, > 5 x C mod. gauge variation not detected S weak. film ratio < 1 S weak. |
| 10 | `skidding_loss_of_forward_slip` | forward slip <= 0 S str, < 0.005 S mod, >= 0.02 C mod. film ratio > 3 S weak. irregular S weak, longitudinal C str. a regular law C weak. |

Each transverse hypothesis has a confirming test from mill practice (stone the strip and
measure pitch at two speeds; chock accelerometer speed-ramp order map; roll-change test;
backup-roll barrel inspection; tensile test for a yield plateau; ...).

### 5.4 Interpretations where the written rules were open, and one changed rule

- **Several observations, one evidence item.** A frequency band, pitch band or pitch-match
  criterion is evaluated for each observation and reported as one item with the **least
  favourable** verdict: one source has to explain every observation, and repeated
  observations are not independent evidence. In the bearing demo the same 24.9 mm pitch at
  6.0 and 7.83 m/s gives 241 Hz and 314 Hz; the 241 Hz observation (below 300 Hz)
  contradicts the fifth-octave hypothesis strongly.
- **Band-risk stripes of the v1 coolant screen.** Only `BLOCKED_NOZZLE` stripes and interior
  `UNCOVERED` zones count; the regular overlap alternation of a healthy header does not.
  Without a `width_model`, the lengthwise nozzle hypothesis uses these stripes.
- **Two gaps filled by mirroring an existing rule** (CONTRADICTS weak): coil diameters
  supplied but the pitch matches neither coil; predicted lengthwise positions exist but no
  observed position is on one.
- **Bite derivation failure.** Chatter-dependent criteria become `NEUTRAL` with expected
  text `NOT_ASSESSABLE: <reason>`; forward slip is then taken as 0 in the kinematics (flag
  `FORWARD_SLIP_UNKNOWN_ZERO_USED_IN_KINEMATICS`).
- **Rule changed against the written specification:** `CONSISTENT_LEADING` requires at
  least one `SUPPORTS` item with basis `observation`. As written, the chatter speed-margin
  criterion (a model result worth 3 points) made third-octave chatter lead in the template
  case with every observation `null`. Scores are unchanged by the rule.

## 6. Lengthwise physics

The lengthwise result (`result['width']`) is built in this order: steady roll temperature
and radius with the actual and with a healthy spray header (6.1); the difference between
the two gives the stripes; each stripe goes through the strip-shape chain to thickness,
elongation, flatness and buckling (6.2); the same stripe shape is carried through every
pass of the schedule (6.3); switching events are simulated in time (6.4). Integration code:
`physicroll/band_width.py`; equations: `physicroll/roll_thermal.py`,
`physicroll/strip_shape.py`.

### 6.1 Roll thermal model (`roll_thermal.py`)

Circumferentially averaged, axisymmetric conduction in a solid work roll of radius `R` and
barrel length `B`; `z` along the barrel, `r` radial [V: Yamaguchi et al. 2016; Li et al.
2024]:

```
rho*c*dT/dt = k_r*(1/r)*d/dr(r*dT/dr) + k_z*d2T/dz2                      [V]
r = R:   -k_r*dT/dr = h(z,t)*(T - T_coolant) - q(z,t)                    [V]
r = 0:   symmetry;   z = 0, B: adiabatic (neck and chock losses ignored, flagged)
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
factor = 1 ('axially_free', default) or (1 + nu) ('plane_strain')
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

**Open discrepancy.** Dohmae & Okamura (2012) identified on a plant a first-order flatness
response to one cooling zone with a time constant of about 20 s. This model grows and fades
stripes over tens of seconds to minutes (section 6.4: half-decay 57 s and 84 s after the two
demo events). The discrepancy is open. Possible causes, none modelled: bite heat that depends
on the roll surface temperature, emulsion-level heat transfer, per-revolution effects.

Not modelled: the per-revolution surface temperature cycle, the bite contact conductance
and roll-strip temperature coupling (`q` is supplied or computed from the pass, not coupled
back), the flow distribution inside a fan, spray drift, temperature-dependent properties,
neck and chock losses, axial mechanical coupling of the expansion, roll wear, bending and
flattening. No measured spray heat-transfer coefficient for kerosene-based coolant was found
(planner estimate 0.5-2 kW/m2K [D]; an Innoval blog gives 4.65-5.5 kW/m2K overall for an
unspecified coolant); the coefficients are inputs.

### 6.2 Strip shape and flatness (`strip_shape.py`)

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
  dp' = -Q*dh - N_x'*dsigma_x,  dsigma_x = -E_strip*eps,  eps = -xi*dh/h_exit
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
feedback stiffness per width is 85 to 140 times `Q` on every pass (gauge-trend table, 6.3).
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

### 6.3 What the model says about thin gauge for lengthwise bands

Source: `artifacts/band_diagnosis/lengthwise-bands-demo.result.json`,
`width.gauge_trend`. The same 2.715 um roll stripe (the demo's steady stripe at 0.6675 m,
isolated and scaled; it is a what-if, not each pass's own thermal state) is carried through
the six passes of the schedule, each with its own derived bite (all
`derived_slab_hitchcock`), tension and computed flow stress. A smooth Gaussian reference
stripe (half-peak width 0.1 m, about one cooling zone) is evaluated alongside. Onset heights
are the stripe heights at which a band first buckles, found by bisection on a grid of
0.00997 m.

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
  tension release" (section 4.1).

### 6.4 Short-lived bands

A switching event (`width_model.events`) sets the listed nozzles to a level for a duration;
the engine starts from the steady state, simulates the event and a recovery of at least
600 s, and differences the radius against the steady state it started from. At the monitor
position it reports the analytic initial growth rate (6.1) beside the simulated rate over
the first 5 s, the time to each threshold (in-mill manifest onset, after-release onset,
reporting threshold, all as stripe heights from the peak profile scaled), the time above
the in-mill threshold (`visible_time_s`), the fade time after the event, and the band life
(event duration plus the time after the event to fall below the manifest threshold).

Demo events (`width.thermal_events`):

| quantity | event 1: nozzles 20-21 off | event 2: nozzle 6 off |
|---|---|---|
| start, duration | 0 s, 60 s | 300 s, 150 s |
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
than the ~20 s plant-identified response (6.1, open discrepancy).

### 6.5 Lengthwise demo case

`scenarios/band_diagnosis_lengthwise_bands.json` (`synthetic: true`): the same single-stand
four-high mill as the chatter demo, final pass 0.30 -> 0.21 mm at 12 m/s, 1.5 m wide, work
roll radius 0.2 m, friction 0.03 supplied, flow stress computed from a synthetic Voce law,
schedule 2.2 -> 0.21 mm in six passes. Header: 32 nozzles at 52 mm pitch, 0.2 m standoff,
0.8 rad fans, mean spray coefficient 3000 W/m2K; nozzle 12 at 0.668 m partly blocked (flow
level 0.45); events: nozzles 20-21 off for 60 s, nozzle 6 off for 150 s. The roll heat share
(0.08 per roll from `strip_heat_fraction` 0.84) and the spray coefficient were chosen so that
the thermal crown lands in the 2-16 um reported for mills. Observations were generated from
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
| 3 | `tension_troughs_or_creases` | CONSISTENT | 8 |
| 4 | `heat_streak_or_film_variation` | CONSISTENT | 4 |
| 5 | `profile_flatness_mismatch` | CONSISTENT | 4 |
| 6 | `incoming_ridge_coil_buildup` | CONSISTENT | 2 |
| 7 | `oil_carryover_drips_or_stain` | CONSISTENT | 1 |
| 8 | `coil_or_mandrel_locked_marks` | NOT_ASSESSABLE | 0 |
| 9-19 | `roll_surface_band`, `grinding_feed_marks` and the other nine transverse hypotheses | CONTRADICTED | -3 to -11 |

Both planted causes come first and second. Tension troughs score 8 because the mean
observed gap (368 mm) happens to lie at 0.745 and 0.932 x the computed trough wavelengths of
the two spans (494 mm and 395 mm), a strong support; the lateral compressive stress is not
supplied, so the trough model gives thresholds only. The nozzle hypothesis matches only one
of the three positions (0.667 m), the zone hypothesis the other two; the "least favourable"
rule (5.4) is not applied to position matching, so each coolant hypothesis is supported by
the positions it explains.

## 7. Process models

Integration code: `physicroll/band_process.py`; equations: `physicroll/bite_tribology.py`.
These sections appear only in v2 cases with `tribology` and/or `hardening`.

### 7.1 Lubricant, film and friction

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

### 7.2 Pass heating

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

### 7.3 Work hardening

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

### 7.4 Speed-consistent chatter critical speed

With friction falling as speed rises, the critical speed is the speed `u` with
`u = u_crit(mu(u))` [D], where `mu(u) = mu_used + [mu_closure(u) - mu_closure(u_op)]` (the
placeholder supplies the slope, the operating friction the level), scanned and bisected in
log speed with the contact radius and forward slip held at the operating bite. Lengthwise
demo (`chatter.speed_consistent`): 13.30 m/s against 13.85 m/s at fixed friction 0.03
(beta 0.5); 8.79 m/s against 5.16 m/s with beta = 0. The second pair moves the other way
because below the operating speed the placeholder friction is higher, and higher friction
raises the critical speed in this model.

## 8. Mill dynamics (`mill_dynamics.py`)

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
run-out e:        dh = -2e*M/(M + (1-alpha)*Q)
bite input dF0:   dh = (1-alpha)*dF0/(M + (1-alpha)*Q)
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
"Improvement of thickness tolerances"]. `dF/dY` by central differences of the bite derivation
[D]; static gauge change by the bite-input formula above (tension held constant); decoiler
frequency `n*u_e/(pi*D_coil)`, exit pitch `pi*D_coil*h0/(h1*n)` [D]. Demo
(`incoming_variation`): 2 % = 5.65 MPa flow-stress amplitude; static exit-gauge change 3.68 um
without AGC, 1.22 um with it; decoiler 2.23 Hz, exit pitch 5.39 m (first harmonic).

**Drive torsional modes** [D; benchmark V: J. Phys. Conf. Ser. 2419 (2022) 012027; first-mode
guidance 10-20 Hz V: Gao et al.]: free-free chain `J*theta'' + K*theta = 0`; reel inertia
reflected to the motor `J = J_motor + pi*rho*W*(R^4 - R_m^4)/(2*N^2)` [V: Soler, Isermann &
Feldmann 2008]. Roll-speed ripple enters the tension rows only:
`du_x = (1+f)*dV_r`, `du_e = (1+f)*(h1/h0)*dV_r` [D]. Demo (`drive`): modes 18.47 and 37.56 Hz,
strip pitch 0.650 and 0.319 m at 12 m/s; the computed modes replace the generic 5-30 Hz band
in the torsional rule (5.3).

**Speed-change gauge shift** [V context: Zhang et al. 2017 IJCA 10(6); formula D, tension held
constant]: `dh = (1-alpha)*dF0/(M + (1-alpha)*Q)` with `dF0 = dF/dmu*dmu` from the friction-speed
slope. Demo (`gauge_control.speed_change_gauge_shift`, 6 -> 12 m/s): placeholder friction
0.0829 -> 0.0765, force -242 kN, exit gauge -4.68 um with AGC, -14.2 um without; the
absolute friction values are placeholders (7.1).

Not modelled: the cylinder as anything but a first-order loop, AGC monitor / feed-forward /
mass-flow AGC, eccentricity compensation, tension regulators between the two idealisations,
motor and drive control loops, gear backlash, strip elastic recovery, thermal effects, roll
bending and cross-width variation.

## 9. Thin-gauge roll bite

### 9.1 Where the Hitchcock path stops

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
Passes below 0.3 mm carry the flag `THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN`.

### 9.2 Experimental mattress (elastic-foundation) model (`foil_bite.py`)

Status `UNVALIDATED_EXPERIMENTAL_MATTRESS_FOIL_BITE`. A planner reduction [D] in the spirit of
Fleck & Johnson (1987; read only through a poor OCR copy) and of the MISG report "A simple
model for the cold rolling of metal foil" [V for the non-dimensional form
`(h - G2)p' + mu*p = x`]. It is **not** the Fleck-Johnson hybrid model: the strip is
rigid-perfectly-plastic (no elastic strip zones) and the roll a local Winkler foundation.

```
h(x) = g0 + x^2/R + 2*p(x)/K_p                                          [D]
p'*(h - 2K/K_p) = K*(2x/R) + s*2*mu*p,   yield p + sigma = K,  K = 2Y/sqrt(3)   [D]
h' = [ (2x/R)*h + s*4*mu*p/K_p ] / (h - 2K/K_p)   (s = +1 entry side, -1 exit side)
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
Mattress bites carry the flag `BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL`. The lengthwise demo
uses `auto`; every pass derived with Hitchcock. A bite from a plant or foil-mill model can
still be supplied in `model_options.bite_response_override`.

## 10. Transverse physics (chatter)

### 10.1 Third-octave chatter model (`chatter.py`)

`x_w`, `x_b`: upper work / backup roll displacement, positive away from the pass line; the
lower half mirrors it, so `dh = 2*x_w` (no strip elastic recovery). `dF`: separating-force
perturbation, positive pushes the rolls apart. `sigma_e`, `sigma_x`: entry / exit tensile
stress perturbations. `V_r` roll surface speed (held constant), forward slip
`f = u_x/V_r - 1`. Model built in this project on the mechanism of Tlusty et al. (1982), Yun,
Wilson & Ehmann (1998) and Niroomand et al. (2012) [D]:

```
M_w*x_w'' = -K_wb*(x_w - x_b) - C_wb*(x_w' - x_b') + dF                        [D]
M_b*x_b'' = +K_wb*(x_w - x_b) + C_wb*(x_w' - x_b') - K_h*x_b - C_h*x_b'        [D]
K_mill = 1/(2*(1/K_wb + 1/K_h))
dF = F_h*dh + F_hdot*dh' + F_se*sigma_e + F_sx*sigma_x + F_hin*dh_in,   Q_s = -F_h > 0
df = f_h*dh + f_se*sigma_e + f_sx*sigma_x + f_hin*dh_in
F_hdot = F_h*beta*l_d/u_x          [D] bite-damping closure, declared heuristic
du_x = V_r*df
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
is not reliable and the result is flagged (5.3).

### 10.2 Pitch laws and signatures (`band_signatures.py`)

```
fixed frequency F:            p = u_x/F                         [V: Kim et al. 2012, f = v/p]
n marks on a roll of dia. D:  p = pi*D*(1+f)/n                  [V: Krueger, Richard & Peretic 2019]
order k of work-roll speed:   p = pi*D_w*(1+f)/k
exit coil:                    p = pi*D_coil;  entry coil: p = pi*D_coil*h0/h1     [D]
later pass:                   p_out = p_in*h_in/h_out                            [D]
bearing orders, r = (d/D)*cos(phi):  BPFO = n/2*(1-r), BPFI = n/2*(1+r),
                              FTF = (1-r)/2, BSF = D/(2d)*(1-r^2)                 [V: Randall & Antoni 2011]
```

Other screens: bending strain `t/D` against the yield-point window
`[t/(eps_y+eps_L), t/(eps_y - sigma_t/E)]` [V sources: QCA-1; Choi, Jin & Kang 1998; de Codes
et al. 2011]; herringbone pitch about the arc of contact at reduction >= 0.40 [V: Komori 1996;
Szucs et al. 2020]; forward slip <= 0 skidding [V: Reid & Schey 1978]; inlet film [M] (7.1);
flat-fan coverage `W = 2*s*tan(angle/2)`, `W_eff = W*cos(offset)` [V: Lloyd 2010; Tucker 2006];
free thermal growth `dR = alpha*R*dT` (upper bound) and gap closure `2*dR/h_exit` [D]. In v2
cases with a `width_model` the solved roll temperature field (6.1) replaces the free-growth
screen for the lengthwise hypotheses.

### 10.3 Transverse demo cases

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

### 10.4 What the model says about thin gauge for chatter

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

### 10.5 Levers and coolant for chatter

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
tension effects (section 14). Coolant acts on chatter through friction and film thickness;
with a `tribology` section the friction-speed slope enters the speed-consistent critical speed
(7.4). It acts on lengthwise bands through the roll temperature field (section 6).

## 11. The report

`<slug>.report.html` is a self-contained page (inline SVG, no scripts). A v1 result renders
the phase-1 page. A v2 result adds the family statement and the lengthwise, process and
dynamics sections; when the observed or leading family is lengthwise the page leads with the
lengthwise sections and moves the transverse (chatter) sections into a block headed
"Transverse-band (chatter) screening: supporting detail for this case". Sections of the
lengthwise demo report, in order:

| section | what it shows |
|---|---|
| Which family of causes | the `family_summary` text and the number of non-contradicted hypotheses per family |
| Leading hypotheses; Next measurements | the leading hypothesis with its confirming test, runners-up of the same family, and `recommended_next_measurements` |
| Across the width: predicted against observed bands | upper panel: steady roll radius growth with the actual and with a healthy header, nozzle positions; lower panel: flatness at the three levels of the shape chain; dashed lines at the observed positions. Tables: steady stripes (peak, width, I-units per level, in-mill state, state after release, in-mill onset height), the nozzle-pattern ripple, which predicted source each observed band matches, which pitch the gaps are multiples of, tension troughs |
| Short-lived bands | per event: radius deviation against time with the in-mill, after-release and reporting thresholds, and the event table of 6.4 |
| Why thin gauge is worse | the gauge-trend text and table of 6.3 |
| Hypotheses | every hypothesis with family, standing, score and its evidence items |
| Transverse-band (chatter) screening | key numbers, strip map, chatter stability, schedule sweep, frequency-speed map, forced response and time trace, levers, spray coverage and other screens |
| Process; Gauge control, drive and incoming variation | sections 7 and 8 |
| Limitations and sources | result limitations, literature disagreements, sources |

**Reading in-mill against after-release.** Every band state comes in pairs. *In mill*:
`LATENT_UNDER_TENSION` (flat, a stress stripe a shapemeter can see) or `MANIFEST_BUCKLE`
(buckled under the mill tension). *After tension release*: `MANIFEST_AFTER_TENSION_RELEASE` or
`FLAT_AFTER_TENSION_RELEASE`, from the local mode. A band latent in the mill and manifest
after release is a band that appears on the coil, at the slitter or on the table; compare it
with the observation `visible_only_after_tension_release`. The reported flatness level is the
one with the exit-tension feedback; the rigid and compliance-only levels are bounds for
comparison, not predictions. Onset heights flagged as limited by the reporting threshold are
upper bounds. The global (whole-sheet) released mode is not a band prediction (6.2). The
report section titles are produced by `physicroll/band_report.py`.

## 12. Verification evidence

The tests check that the code implements its equations and that the screening logic recovers
causes planted from the same models. They say nothing about whether the models describe a
real mill.

| module / test file | what is checked |
|---|---|
| `chatter.py` / `tests/test_chatter.py` | eigenvalue solver (diagonal, rotation, companion, defective cases); single-DOF critical speed and onset frequency with and without bite damping against the Routh-Hurwitz closed form; closed-form undamped modes; bite-derived force against the independent contact solver; sensitivity signs; time trace against eigenvalues; static and resonant frequency-response limits |
| `band_signatures.py` / `tests/test_band_signatures.py` | pitch doubling with speed; exponent classification and the < 5 % speed-spread guard; bearing-order identities; catalogue pitches and resonance round trip; AA5182 bending window; spray coverage of uniform, non-overlapping and blocked headers; free thermal growth rising with thinner gauge |
| `roll_thermal.py` / `tests/test_roll_thermal.py` | steady uniform `T = Tc + q/h` at every radius; lumped-limit exponential approach and axial decay length `sqrt(k_z*R/(2h))`; pure radial transient against the Bessel series; long transient reaching steady state; energy conservation to round-off; grid and time-step convergence; blocked-nozzle stripe position and size; zone-off-then-on growth law `2*alpha*dh*(Ts-Tc)/(rho*c)` in the resolved and lumped models, faster surface temperature and faster decay in the resolved model (`test_zone_off_then_on_grows_then_decays_and_skin_effects`); healthy header weight averages to 1; expansion constraints differ by `1 + nu`; difference-profile stripe detection |
| `strip_shape.py` / `tests/test_strip_shape.py` | compliance and transfer check values; sinusoid as eigenfunction; feedback-off numbers unchanged; `Q_eff` formula; gauge-independent feedback limit (`test_gauge_independent_limit`); mean component keeps `Q`; worked example latent with feedback; saturation formula; 3 um stripe states at three gauges; Rayleigh limits (uniform compression, embedded zone); released local / global modes and the top-hat edge-spike limit; heredity and Shohet-Townsend check values; coil-ridge formula, yield onset and thin-gauge scaling; trough and wrinkle check values and scalings; spacing and position matching |
| `bite_tribology.py` / `tests/test_bite_tribology.py` | viscosity `beta` from the kerosene data points; film check case (62.8 nm, film ratio 0.209, within 5 % of the quoted 65 nm); film linear in speed and viscosity; closure limits and slope; friction falling monotonically with speed; pass heating check (49.35 K) and energy closure; Voce mean against quadrature; literature fits carry the warning |
| `mill_dynamics.py` / `tests/test_mill_dynamics.py` | static run-out and stroke transfer; full compensation prints run-out through; amplification rising with `alpha`; entry-thickness limit; mass-flow limit with tension coupling; `alpha = 0` reproduces `chatter.py`; first-order loop interaction reported and removed by roll-off; neutral mode at `alpha = 1`; hardness sensitivity and static limit; coil-synchronous frequencies; three-mass torsional benchmark; reel inertia; roll-speed DC limit; speed-change gauge shift |
| `foil_bite.py` / `tests/test_foil_bite.py` | rigid limit reproduces the slab force, slip and torque within 1e-3; sheet case conventional and of the same order as Hitchcock; foundation modulus is the fixed point of the contact length; end-zone equilibrium and smooth exit junction; work identity and grid convergence; Hitchcock-rejected pass solves; foil regime with shear within Coulomb; rejection of the high-friction foil case, the limiting gauge and a sticking exit; force trends; sensitivity signs match Hitchcock |
| `band_diagnosis.py` / `tests/test_band_diagnosis.py` | planted third-octave chatter, bearing order, backup-roll mark, yield-point bending and blocked-nozzle band lead; healthy header not a band risk; missing observations never contradict; scoring, standings and the leading rule of 5.4; graceful bite failure; supplied bite; lever directions computed; zero-tension lever not assessable; rejected damping variant is a row; strict validation; determinism; report escaping; v1 report unchanged; CLI; the three scenario files load and the two v1 demos lead |
| `band_width.py` / `tests/test_band_lengthwise.py` | planted truth for each of the nine lengthwise hypotheses; three shape levels with the feedback always on; healthy header gives no stripes; gauge trend (buckling stress and dead band fall, after-release onset carries the trend, in-mill onset falls less); tension-release rule table; spacing beyond 8 pitches not comparable; any non-longitudinal orientation contradicts every lengthwise hypothesis; lengthwise demo leads with `nozzle_thermal_stripe` at coarse settings |
| `band_process.py`, report / `tests/test_band_v2_sections.py` | computed values replace supplied ones only when flagged; speed-consistent critical speed; gauge-control amplification; drive and incoming sections; `auto` falls back to the mattress model; missing sections not supplied and v1 unchanged; v2 validation; determinism, report and CLI; report section order and escaping |

Run, for example, `python -m unittest tests.test_band_lengthwise -v`.

## 13. Limitations and open discrepancies

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
- **Supplied heat partition and spray coefficients.** The strip heat fraction (hence the roll
  heat fraction) and the spray heat-transfer coefficients are inputs; no measured value for a
  kerosene-based coolant spray was found. Stripe heights scale with these guesses.
- **Thermal model slower than the plant-identified response**: stripes grow and fade over
  tens of seconds to minutes (demo half-decay 57 s and 84 s) against a first-order flatness
  response of about 20 s identified on a plant (Dohmae & Okamura 2012). Open.
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
- **Coil ridge compaction factor** is an analyst choice (default 0.5).
- **Mill dynamics**: first-order cylinder loop (the AGC-chatter result depends on the loop
  roll-off, 9.70 against 13.62 m/s in the demo); static formulas hold tension constant.
- **Hardening**: literature fits are tensile fits, over-predicting beyond `eps` about 0.3; demo
  Voce parameters are synthetic; rate sensitivity zero.
- **Tribology**: inlet-film exponent disputed between sources; no starvation, film collapse,
  plate-out or roughness evolution.

## 14. Sources and disagreements

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
