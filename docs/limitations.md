# Limitations and exceptions of the band screening tool

This register collects in one place what the band screening tool assumes, where its models are
reduced, where it refuses a case or cannot decide, which numbers the project chose itself, and
which published values its models do not match. It is written for a plant reader. The detail
behind each row is in the band guide ([`docs/band-diagnosis.md`](band-diagnosis.md), section 14
and the sections named in the rows), in the guided-app guide ([`docs/band-app.md`](band-app.md)),
in the gap study ([`docs/simulation-coverage-gaps.md`](simulation-coverage-gaps.md)) and in the
limitation lists that every result carries.

Two blocks are generated from the code (part 5 and part 8) by
`python -m physicroll.limitations --write docs/limitations.md`; the rest is written by hand and
checked by `tests/test_limitations_register.py` (part 7).

## 1. How to read this register

- A **limitation** is a reduced model or an effect that is left out: the tool gives a number, but
  the number rests on a simplification.
- An **exception** is a case the tool refuses, leaves neutral, cannot decide, or handles by a
  fall-back (for example zero slip where the slip is unknown).
- An **analyst choice** is a number or rule the project chose because the literature gives none.
  Part 4 lists them all.
- A **discrepancy** is a published value that the model does not match. Part 5 lists every one
  the benchmark harness records.

Nothing in the tool has been compared with plant data. Every statement below holds on top of that
one; a row that does not repeat it does not lift it. The register covers the band screening tool
(the command `python -m physicroll.band_cli` and the guided app). The earlier demonstrator and the
coil-transient studies have their own documents.

In the tables, "what it means for a reader" gives the direction and size where the code or the
guide gives one, otherwise "size not known". "How the result shows it" names the flag, status
word, result section or note key a result carries. "What would lift it" names a measurement or
input, or the gap of the gap study and its phase (section 8 of the gap study).

## 2. Register

### 2.1 Roll bite

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-BITE-01 | The sheet roll-gap model assumes the rolls flatten into a circle. That is not valid toward foil gauges; below 20 µm exit gauge it does not run, and thinner passes need supplied roll-gap values or a foil model. | Size not known toward foil gauge; below its floor the sheet model gives nothing. | `CIRCULAR_FLATTENING_ASSUMED_NOT_VALIDATED`, `HITCHCOCK_RATIO_BEYOND_REVIEWED_ENVELOPE`, `THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN` | a foil roll-gap model (BT-G1, Phase 1, built in reduced form) or supplied roll-gap values | limitation |
| L-BITE-02 | The default foil roll-gap model is experimental: a rigid-plastic strip on a plain elastic mattress (a form the original authors rejected), with a foundation stiffness calibrated from a line-contact formula and contact end zones added to the published equations; no elastic zones of the strip. | On the one published case with every input stated it gives 0.42 of the reference load (part 5). Foil numbers are order of magnitude only; the force scales strongly with the foundation stiffness. | `EXPERIMENTAL_MATTRESS_FOIL_MODEL`, `BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL`, `DERIVED_BY_EXPERIMENTAL_MATTRESS_MODEL`, `MATTRESS_REGIME_FOIL`, `BITE_MODEL_MATTRESS`, `FOUNDATION_MODULUS_FROM_MEMORY_FORMULA`, `CONTACT_END_ZONES_ADDED_TO_SPEC_EQUATIONS`, `CONTACT_RADIUS_RATIO_CLAMPED_TO_ONE` | the half-space model by default (BT-G1); a measured foil pass with load, slip and every input stated | discrepancy |
| L-BITE-03 | With one constant friction value the experimental foil model gives a large forward slip (0.190 at the battery-foil case pass, flagged implausible). The slip enters the slip heat. | The friction heat and the strip exit temperature are too high at foil gauge: 47.1 kW/m of friction power against 40.3 kW/m plastic, and 333.4 K exit temperature at strip share 0.22 in the battery-foil demo. | `FORWARD_SLIP_LARGE_CONSTANT_FRICTION_NO_SLIP_ZONE_MODEL` | a friction varying through the roll gap (BT-G5, BT-G6); a measured forward slip | limitation |
| L-BITE-04 | Where the forward slip is unknown (no roll-gap result) or 0.5 or more, zero slip is used for the spacings of roll-borne, mark-locked and order-locked marks, and the forward-slip screen is not assessed; every other result uses the roll gap's slip. | The roll-mark spacings are computed as if the strip left the roll gap at roll speed. | `FORWARD_SLIP_UNKNOWN_ZERO_USED_IN_KINEMATICS`, `FORWARD_SLIP_OUTSIDE_KINEMATICS_DOMAIN_ZERO_USED_IN_KINEMATICS` | a roll-gap result inside the domain; a measured forward slip | exception |
| L-BITE-05 | The half-space foil roll-gap model is a reduced form of a published model, chosen by a case option: it leaves out the stretching equations of strip and roll surface inside the contact (stress and traction inside the no-slip zone and two zones of the third regime are not modelled), uses one friction coefficient, no oil film, no hardening, rate or heat effects inside the contact, and no closed gap. | Unvalidated: no foil pass with measured load, slip and every input stated was found to compare it with. Pressure, shape, load and torque do not depend on the left-out equations, according to the source. | `BITE_MODEL_HALF_SPACE`, `BITE_MODEL_AUTO_HALF_SPACE`, `BITE_FROM_REDUCED_HALF_SPACE_MODEL`, `DERIVED_BY_HALF_SPACE_FOIL_MODEL`, `REDUCED_HALF_SPACE_FOIL_MODEL` | the full model (BT-G1, Phase 3 with BT-G15); a measured foil pass | limitation |
| L-BITE-06 | The half-space model closes the ends of the contact by contact zones; the published model ends with a pressure step, and its published loads depend on an end length the paper does not state. | On the published foil case this model gives a dimensionless load of 88.9 to 92.9 where the printed model gives 78 to 134 depending on the unstated end length. | `limitations` of the result (half-space note); benchmark BT-V1-HS (part 5) | the end length from the authors, or a measured case | limitation |
| L-BITE-07 | The half-space model lets the strip compress elastically under the roll; the published model does not. This is the planner's addition. | It raises the load by 4.6 % on the published case. | `STRIP_THICKNESS_SPRING_NOT_IN_PUBLISHED_MODEL` | a measured case; it can be switched off by a very stiff strip input | analyst choice |
| L-BITE-08 | At the boundary between the sheet and the foil range neither contact structure of the half-space model is admissible; the sheet-type one is used and the other is reported beside it. The rule that rejects the degenerate branch is the project's own. | 1.7 % apart in force on the battery-foil case pass. | `ZONE_STRUCTURE_AT_REGIME_BOUNDARY` | the full model (BT-G1) | analyst choice |
| L-BITE-09 | The short elastic zones of the strip at entry and exit are not modelled; with a no-slip zone the half-space model lets the strip creep a little (up to 0.6 %). | Negligible for foil reductions above 10 % according to the gap study; matters for light passes. The creep is 1 to 2.5 % of the forward slip. | `LIGHT_REDUCTION_ELASTIC_STRIP_ZONES_NOT_MODELLED`, `NO_SLIP_ZONE_CREEP_ABOVE_ONE_PERCENT` | elastic strip zones (BT-G15, B6, Phase 3) | limitation |
| L-BITE-10 | The highest roll pressure of a half-space solution can exceed what published foil solutions show. | Size not known. | `PEAK_PRESSURE_ABOVE_16_PLANE_STRAIN_YIELD` | a measured or published case at that pressure | limitation |
| L-BITE-11 | Only the half-space model caps friction at the shear strength of the metal; the sheet and the experimental foil model reject a pass whose friction would exceed it. Where the experimental model cannot start, the half-space model is reached by raising the friction step by step. | A pass with high friction runs only in the half-space model. | `SHEAR_CAP_ACTIVE`, `COLD_START_BY_FRICTION_CONTINUATION` | a friction varying through the roll gap (BT-G5) | exception |
| L-BITE-12 | Between 8 and 20 µm exit gauge and between 50 and 65 % reduction the experimental foil model gives numbers only because its solution stays converged and continuous in probes; no source validates it there. | The plant's 18 µm final pass (force inside the range reported for battery-foil passes) is usable as order of magnitude only; the 12 µm pass of the demo (force 2.7 times the top of that range) is not credible at all. | `EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN`, `REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN` | a measured foil pass in that range | limitation |
| L-BITE-13 | Below 8 µm exit gauge or above 65 % reduction no roll-gap model runs; the parts that need one are not assessed. | No chatter result, no strip shape and no roll heat for that pass. | `EXIT_GAUGE_BELOW_BITE_MODEL_FLOOR`, `BITE_DERIVATION_FAILED_CHATTER_NOT_ASSESSABLE`, `WIDTH_SHAPE_CHAIN_NOT_ASSESSABLE_NO_BITE`, `WIDTH_THERMAL_NOT_ASSESSABLE_NO_BITE_HEAT` | supplied roll-gap values | exception |
| L-BITE-14 | The credibility mark compares a pass below 20 µm with the 0.9 to 2.3 kN/mm reported for battery-foil passes, a range from trade sources for battery foil only. A pass outside it is not credible: its roll-gap-dependent model items count as neutral, so the ranking rests on the observations, the inputs and the items that need no roll gap. A pass inside it is not gated, although still unvalidated. | A force inside the range does not make the roll gap right. | `CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE` | measured roll forces of the plant's passes | exception |
| L-BITE-15 | No roll-kissing (closed-gap) model: neither roll-gap model has the load path through roll-to-roll contact. The foil block appears below 100 µm exit gauge, while one source puts the onset of closed-gap rolling at up to 200 µm; the lever table and the gauge-control section are open-gap reasoning only. | Size not known; at closed gap part of the load bypasses the strip (22 % in one computed case of the gap study). | `CLOSED_GAP_ROLLING_LIKELY_ROLL_KISSING_NOT_MODELLED` | G2, BT-G2 (Phase 3) | limitation |
| L-BITE-16 | Doubled (pack-rolled) passes are not modelled. | A doubled pass has no roll gap, only per-sheet thresholds that need none. | `DOUBLED_FINAL_PASS_NOT_MODELLED` | BT-G14 (Phase 3) | exception |
| L-BITE-17 | Roll-gap sensitivities are worked out from small changes of the pass; near zero tension the tension effect is taken from one side, near the sheet / foil boundary the change can straddle the two models, and the result can depend on the step. | Size not known; the flags say where. | `ONE_SIDED_TENSION_DIFFERENCE_AT_ZERO_TENSION`, `REGIME_CHANGE_WITHIN_FINITE_DIFFERENCE_STENCIL`, `SENSITIVITY_STEP_NOT_CONVERGED` | - | exception |
| L-BITE-18 | With supplied roll-gap values, the gauge-control speed shift and the hardness response still take their force sensitivities from the tool's own roll-gap model, while the strip stiffness is the supplied one. | The two may not fit together. | `FORCE_SENSITIVITY_DERIVED_NOT_FROM_SUPPLIED_BITE` | supplied force sensitivities | limitation |

### 2.2 Friction and oil

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-FRIC-01 | Friction is an input unless the case asks for a computed one. The friction-speed law is an unfitted placeholder: its absolute values are placeholders and only its slope with speed is used (also for the friction change across the width). | Neither friction law has a published level for any mill. At foil gauge the force per width scales steeply with the friction (load exponent about 2 to 2.6). | `PLACEHOLDER_FRICTION_CLOSURE_NOT_FITTED`, `FRICTION_FROM_PLACEHOLDER_CLOSURE`, `LOCAL_FRICTION_FROM_PLACEHOLDER_CLOSURE_SLOPE` | forward slip at two speeds; a friction closure (BT-G3, Phase 1, built in reduced form) | limitation |
| L-FRIC-02 | The load-sharing friction law (a case option) takes its level from an entered contact friction (0.013 to 0.1 in the sources) on a contact-ratio curve published for one foil pass and one oil; no inlet analysis is built. Published data need a contact friction that varies with film and reduction, which one value cannot meet. The curve's film axis carries a mismatch of 1.36 to 0.79 between 30 and 1 m/s. | It supports the change of friction with speed, not its level. | `tribology.load_sharing` section and its `limitations` | the inlet analysis and asperity crushing (BT-G3) | limitation |
| L-FRIC-03 | Friction is constant through the roll gap in every model; a friction distribution, the published remedy for foil slip, is not built. | A model with one constant friction over-estimates foil slip. | `MEASURED_SLIP_NOT_REPRODUCED_BY_CONSTANT_FRICTION_BITE` | BT-G5, BT-G6 | limitation |
| L-FRIC-04 | Friction worked out from entered pass records is shown, never applied. It assumes one constant friction through the roll gap, takes the flow stress as entered, and the entered numbers are not verified. With a no-slip zone the slip carries little friction information. Simple forward-slip formulas are reported as unreliable and none is used. | The value absorbs the roll-gap model's own error: by about 12 % from load and 30 % from slip on the published case. | `FRICTION_IDENTIFIED_FROM_ENTERED_RECORDS`, `IDENTIFIED_FRICTION_DIFFERS_FROM_CASE_FRICTION`, `FORWARD_SLIP_INSENSITIVE_TO_FRICTION_IN_THIS_REGIME` | a friction distribution (BT-G6); records with load, flow stress and tension | limitation |
| L-FRIC-05 | The oil film is computed for smooth surfaces with an isothermal pressure-viscosity law and a fully flooded inlet; inlet shear heating only through an optional factor. The entry-pressure exponent and the inlet-film exponent differ between sources (both values are reported); some textbook forms subtract the entry tension. | Inlet shear heating thins the film at high speed, so the film is over-stated there; size not known. | `screens.film` and `process` film results with their `limitations` | A9 (Phase 1, built in reduced form); a measured film or slip | limitation |
| L-FRIC-06 | The film ratio uses the roughness height only, not its lay or its flattening in the roll gap; the regime boundaries are conventional. The herringbone rule keeps its weak support for a film ratio below 1, although that is normal mixed-regime operation (scoring left, wording changed). | Size not known. | `screens.film_regime`; the herringbone item in the evidence | BT-G9 (Phase 3); BT-G3 | limitation |
| L-FRIC-07 | Oil properties at roll-gap pressure are not known. For the one foil oil with data neither pressure law follows the measured viscosity above 100 MPa; no source gives a limiting shear stress for a rolling oil (only a lower bound of 0.045 of the pressure for one base oil); the Eyring stress is known for one base oil without additives. | The optional pressure law is low by a factor 12 to 30 against the measurements (part 5). | `tribology` section; benchmark A9-PRESSURE-LAWS-KEROSINE | a pressure law fitted to the plant's oil; limiting shear stress data (A9) | discrepancy |
| L-FRIC-08 | No starvation, film collapse, plate-out or roughness evolution. There is no film-collapse test for the heat-streak hypothesis: the test of the gap study needs a friction closure and a boundary-film model; only a supplied exit-temperature limit can support that item. | Size not known. | the heat-streak item in the evidence | BT-G3, BT-G11 (Phase 3) | limitation |
| L-FRIC-09 | The oil arriving at the roll gap across the width is a volume balance: no spreading from the neighbours, no carry-over, no wipers, no inlet meniscus position. | Under a fully blocked nozzle no oil arrives in this estimate. | `OIL_SUPPLY_BELOW_SMOOTH_FILM`, `ZERO_OIL_SUPPLY_UNDER_BLOCKED_NOZZLE_NO_SPREADING_MODEL` | BT-G12 in full (Phase 2) | limitation |

### 2.3 Flow stress and material

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-MAT-01 | Flow stress against strain rate and temperature (a case option) is a form without data: the rate sensitivity was measured five decades below rolling rates, the net of rate and temperature at rolling conditions is not known, the strain rate uses the undeformed contact length, the roll-gap temperature is a mid-gap estimate, no law is chosen by alloy group, there is no recovery term, and the rate share of the roll-gap damping is reported only. | Size not known. | `FLOW_STRESS_RATE_TEMPERATURE_FACTOR_APPLIED`, `STRAIN_RATE_FROM_UNDEFORMED_ARC`, `BITE_TEMPERATURE_NOT_AVAILABLE_REFERENCE_USED`, `RATE_SENSITIVITY_EXTRAPOLATED_BEYOND_MEASURED_RATES` | flow-stress data at rolling rates (B1) | limitation |
| L-MAT-02 | A rate and temperature factor outside 0.2 to 5 is not used for that pass. | That pass keeps the flow stress without the factor. | `RATE_TEMPERATURE_FACTOR_REJECTED` | - | exception |
| L-MAT-03 | By default the flow stress does not depend on strain rate or temperature (rate sensitivity zero) and there is no recovery. | Size not known. | `limitations` of the pass-heating result | B1, BT-G16 | limitation |
| L-MAT-04 | Hardening laws: published fits are tensile fits, which over-predict beyond a strain of about 0.3; the demos' parameters are synthetic; parameters are never defaulted and must be supplied; a fit with fewer than 5 points has no redundancy; an as-rolled tensile strength of a hard temper is taken as the flow stress at that strain; no redundant shear, recovery, ageing or temperature dependence between passes. | Size not known. | `FLOW_STRESS_FROM_HARDENING_LAW`; the hardening fit's `limitations` | flow-stress data per alloy group (B2) | limitation |
| L-MAT-05 | A positive late hardening slope is wrong in sign for purified Al-Fe and high-purity grades beyond 80 % reduction; a negative slope is accepted when entered, but none is chosen by alloy group. | Size not known. | `NEGATIVE_LATE_HARDENING_SLOPE_WORK_SOFTENING` | B2 (Phase 1, built in reduced form) | limitation |
| L-MAT-06 | Every roll-gap model uses the isotropic plane-strain factor 2/√3. | Published r-values of one 16 µm 1235-H18 foil would move it by -12 % to +1 %. | `limitations` of the result | an anisotropic yield law in the roll gap (B4) | limitation |
| L-MAT-07 | The alloy and temper suggestion is a literature synthesis (standards, producer pages, patents, broker reports); no source gives a hard gauge-to-alloy rule; several standard tables were read from mirrors or producer pages; the finished tensile strength stands for the rolling flow stress and the proof strength comes from a ratio where not published. | The plant must check or correct the suggestion. | `MATERIAL_NOT_STATED_LITERATURE_PROPOSAL_SHOWN`; `material_selection` | the plant's alloy and temper | limitation |
| L-MAT-08 | The alloy-group table is printed from the gap study; nothing is fitted, and nothing is passed to a hardening law or a roll-gap model. | No effect on any number. | the products guide | B2, B3 | limitation |
| L-MAT-09 | The yield-point screens cover the type with a sharp yield point only (serrated-flow lines in Al-Mg are not covered); ageing, strain rate and temperature are not modelled; the bending window uses an elastic-perfectly-plastic outer fibre and keeps the plateau end under tension; without an entered yield-point strain zero is used; the pass-reduction screen leaves out bending at deflector rolls and coilers (screened separately). | Size not known. | `LUDERS_STRAIN_NOT_SUPPLIED_ZERO_USED_IN_WINDOWS`; `screens` | the yield-point strain of the material | limitation |
| L-MAT-10 | No property change after rolling. | The battery-foil elongation decay above 90 °C is carried as a literature statement only. | `thermal_check` statements | B7 (Phase 3) | limitation |

### 2.4 Roll cooling and heat

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-HEAT-01 | The roll temperature model is averaged around the roll, with flat-topped spray footprints by default (the nozzle-pitch ripple of a healthy header is of unknown size: with a parabolic fan it would be about -12 % / +7 % at 1.43 pitches and about ±5 % at 3.2), insulated barrel ends, constant properties, expansion per axial station with a factor that differs between sources (1 or 1 + ν), and no return of the roll temperature into the roll-gap heat. | Size not known; the top-hat ripple value is not representative. | `width.limitations`; `STEADY_STATE_NOT_CONVERGED` when it did not settle | A7 (Phase 3) | limitation |
| L-HEAT-02 | The share of the roll-gap heat going into the roll and the spray cooling coefficients are inputs. The only measured foil-mill partition puts 0.11 to 0.33 of the heat into the strip (abstract only, a net balance); no sheet-gauge value was found. For kerosene on a rotating work roll only a simulated 2.5 to 4.3 kW/m²K was found; a plate test gives about 5 to 13 kW/m²K. | Stripe heights scale with the roll heat share and fall with the spray coefficient; the sensitivity table of the result shows how far. | `width.thermal_sensitivity` | a measured roll temperature scan or thermal camber (spray calibration); A3, A5 | limitation |
| L-HEAT-03 | The model's spray coefficient is an average around the roll; the published 2.5 to 4.3 kW/m²K is an average over the sprayed roll-wall patch of one cooling zone (simulated). The two are not comparable, and the process-temperature check compares different bases; its verdict word is not agreement. | For sprayed arcs of 20 to 90 degrees the published value is an average around the roll of 0.14 to 1.07 kW/m²K: the demos' coefficient would then be several times too high and the modelled stripes too low. | `SPRAY_COEFFICIENT_BASIS_NOT_COMPARABLE` | the plant's wetted arc; a roll temperature scan or camber for the spray calibration (A5) | limitation |
| L-HEAT-04 | The computed heat partition (a case option) is a reduced interface model: one strip temperature, heat spread evenly over the contact, roll curvature neglected, no conduction through asperities (no formula in the reports), film from the smooth inlet formula, the roll entry temperature assumed, not fed back into the flow stress or the film, not calibrated, not resolved across the width. Unless the option is set, the entered share drives every result. | On the benchmark case the computed strip share is 0.16 to 0.23 against the measured 0.11 to 0.33 (part 5); for the battery-foil case pass it computes 0.338 against the entered 0.22, and 0.662 against the entered 0.84 of the sheet demo. | `STRIP_HEAT_FRACTION_COMPUTED_FROM_INTERFACE_MODEL`, `ROLL_ENTRY_TEMPERATURE_ASSUMED_COOLANT_OR_OIL`, `HEAT_SHARE_OUTSIDE_0_1_TEMPERATURE_DIFFERENCE_DOMINATES`, `STRIP_NOT_THERMALLY_THIN_LUMPED_MODEL_INDICATIVE` | A3 in full; a measured partition | limitation |
| L-HEAT-05 | Two entered values for the heat partition disagree. | The tool says which it used. | `HEAT_PARTITION_INPUTS_INCONSISTENT` | one consistent input | exception |
| L-HEAT-06 | Pass heating: the strip temperature is a through-thickness mean with no conduction, coolant or air loss between roll gap and coiler; the partition is an input, not solved from a contact conductance. | Size not known. | `process.heating` and its `limitations` | A3, A8 | limitation |
| L-HEAT-07 | The roll surface within one revolution (a case option) is one-way: it never changes the roll temperature field, the stripes or the shape; one layer per axial station without axial conduction in it; even heat flux in the roll gap; no backup-roll contact unless entered; wipers and oil carry-over not modelled; the layout angles are entered, not measured by the tool; its three time scales are the model's own. | With sprays all round, the layer mean departs from the averaged model by up to about 0.4 K at nozzle scale and 0.5 K at the strip edges. | `ROLL_SURFACE_CYCLE_COMPUTED`, `CIRCUMFERENTIAL_MEAN_COEFFICIENT_BIASED` | A4 in full; the published time constants | limitation |
| L-HEAT-08 | The spray calibration (command line only, never applied) fits one coefficient for the whole header, averaged around the roll; the background coefficient, heat share, roll-gap heat, coolant temperature and roll properties come from the case, so their errors go into the fit; end effects are not modelled; the after-stop phase uses the background coefficient only; the camber is compared with each profile's own mean removed. | The grid changes the fitted value by a few per cent (3390 against 3269 W/m²K on the battery-foil roll). | the calibration result and its `limitations` | a fit with the case's own grid; a jet-zone parametrisation (A5) | limitation |
| L-HEAT-09 | A first-order flatness response of about 20 s was identified on a plant. In the model a short local event rises fast (half its peak in 9.25 s in the battery demo; axial decay about 23 s for a 52 mm stripe) while a steady stripe needs minutes (116 s to 50 %, 551 s to 90 %). The emulated step test puts 20 s inside the model's range only with the strip-temperature term on and a test of 20 to 40 s, with an assumed coupling and display filter. | A consistent reading, not evidence; plant time constants were not found. Partly open. | `width.zone_step_test`; benchmark A6-ZONE-TIME-CONSTANT (part 5) | the plant's step test protocol and a measured response (A6) | discrepancy |
| L-HEAT-10 | The simple roll screens count spray footprints only (no flow distribution across the fan, no coefficient, no drift) and take the roll growth from free expansion without axial conduction. | The free expansion over-estimates the growth of a narrow hot stripe, possibly by a large factor; most of a local gap difference becomes elongation (flatness), not a thickness band. | `screens.spray_coverage`, `screens.thermal` | the roll temperature model (already in the width section) | limitation |
| L-HEAT-11 | Fire limits are a rule check against the limits you enter: no oil-mist or vapour model; the modelled strip exit temperature is not a coil temperature (and at foil gauge it is inflated by the experimental model's slip, L-BITE-03). | A limit reached in the model is a warning only. | `STRIP_EXIT_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT`, `OIL_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT`, `OIL_SUPPLY_TEMPERATURE_ABOVE_SITE_CAP` | A10 in full, A8 | limitation |
| L-HEAT-13 | A fan stronger in the middle (a case option) uses a parabola as a stand-in: makers call the fan profile parabolic or tapered, but no measured footprint profile is published. It is never the default and not a measured shape. | At the same flow a blocked nozzle's cooling deficit is about 1.5 times deeper and 0.7 times as wide than with the even fan; on the realistic-header demo the stripe of the partly blocked nozzle is 2.3 times higher and half as wide as on the battery-foil demo. | `FOOTPRINT_PROFILE_STAND_IN`; `width.thermal_steady.footprint_profile` | a pressure-film or grease print of the spray on the roll (A5) | limitation |
| L-HEAT-14 | The footprint width is geometric (2 × distance × tan(half the fan angle) × cos(offset)) unless the pattern width from the maker's table is entered; catalogue widths are 6 to 14 % wider than the geometric one, and oil narrows the fan by an unknown amount. The four older demos' headers overlap over 3.2 nozzle pitches, more than makers recommend (1.1 to 1.5). | A wide overlap smooths a blocked nozzle: the older demos' blocked-nozzle stripes are lower and wider than on a header built to vendor practice. | `FOOTPRINT_WIDER_THAN_VENDOR_PRACTICE`; `footprint_width_source`, `footprint_width_over_pitch` | the nozzle type, spray angle, distance and the catalogue width (A5) | limitation |
| L-HEAT-15 | Cooling is taken as proportional to a nozzle's flow unless an exponent is entered; published exponents are 0.5 to 1.0, for water sprays and one kerosene simulation; none is known for the plant's oil. | A partly blocked nozzle's stripe may be overstated by 7 to 45 %; a fully blocked nozzle is not affected. | `SPRAY_FLOW_EXPONENT_APPLIED`; the `footprint_notes` of `width.thermal_steady` | a roll temperature scan at two nozzle flows (A5) | limitation |
| L-HEAT-16 | One spray header of identical nozzles on one row per work roll: several rows per roll, basic and selective rows, valve types, per-nozzle distance, hot-edge sprays and edge rows are not represented. | Size not known; a blocked nozzle in a multi-row zone removes only part of the zone's flow. | `width.thermal_steady` | rows, valve types and hot-edge sprays with the roll stack phase (Phase 3) | limitation |
| L-HEAT-12 | Stripes are found by differencing against a healthy-header solution; the reporting threshold for a roll stripe (0.1 µm on radius) is an analyst choice. | Smaller stripes are not reported. | `width.limitations` | - | analyst choice |

### 2.5 Strip shape and flatness

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-SHAPE-01 | The flatness chain is elastic and local: half-space roll compliance, a linear exit-tension feedback with an approximate band-wise buckling cap (one scale factor, no iteration), no roll bending, no redistribution of entry tension, no relief after buckling; stresses above yield are indicative only. | Size not known. | `width.limitations`; `width.shape` | G1, G3 (Phase 2 and 3) | limitation |
| L-SHAPE-02 | The exit-tension feedback that dominates every thin-gauge result is not supported or contradicted by the literature; the level without it (roll compliance only) is printed beside it and is about two orders of magnitude larger. One of the two comparison levels is not defined when the roll bump or the change reaches the gauge. | The size of a thin-gauge band depends on which level holds; a second estimate of the feedback lies between them (L-SHAPE-19). | `RIGID_BOUND_NOT_DEFINED_BUMP_REACHES_GAUGE`, `COMPLIANCE_ONLY_LEVEL_NOT_DEFINED_CHANGE_REACHES_GAUGE` | a width-coupled strip model (G3) | limitation |
| L-SHAPE-19 | A second estimate of the tension feedback, always computed beside the standard levels: a re-derived model of how the exit and entry spans respond across the width, using the roll gap's own force and slip sensitivities, half-infinite spans and an assumed way the strip is held sideways at the roll gap (three are printed; the kernel level uses "leaves the roll gap moving straight", an analyst choice). For bands it turns out to be a factor on the feedback, not a wavenumber-dependent kernel. The literature neither supports nor contradicts the feedback; this estimate is a re-derivation, not a check against a mill. The tally, every band state, onset, screen, local source, the loop and the step test use the standard (pointwise) feedback. | The second estimate gives 0.69 of the feedback at sheet gauge and 0.10 at foil gauge in the demos (0.24 and 0.009 with another closure; no steady answer with the third). A smaller feedback holds a band down less: with it the steady band reads 71.6 instead of 50.7 I-units (sheet demo) and 230 instead of 25.1 (foil demo). The rigid bound, the compliance-only level, this level and the standard level bracket the answer. | `WIDTH_COUPLING_KERNEL_REPORTED`, `KERNEL_FEEDBACK_BELOW_HALF_OF_POINTWISE`, `KERNEL_CLOSURES_DISAGREE_IN_SIGN`, `KERNEL_STEADY_STATE_NOT_DEFINED`; `width.shape.width_coupling` | a roll stack with a closed gap, a strip-element model with lateral flow (G3, Phase 3), or a plant test with a known roll stripe | limitation |
| L-SHAPE-03 | Buckling uses one assumed mode with a coefficient of 4 from memory: an upper bound on the critical load for that mode family, no interaction between neighbouring bands, finite strip length ignored, no search over wavelength under tension. These are the states the evidence uses; a wavelength search can be run beside them (L-SHAPE-16). | The published local buckles are matched only indicatively; the half-wave is 2.8 times the measured one on one case (part 5). | `width.shape` onsets | G4 (Phase 2, packages 6 and 7) | limitation |
| L-SHAPE-04 | The after-release whole-sheet mode is an upper-bound indicator, not a band prediction (it scales with strip width and ignores the sheet's own weight); the local mode's width limit (2 × half-peak width) is an analyst choice; the released state assumes the residual stress is unchanged by coiling, slitting or levelling. | Over-states what shows after release. | `GLOBAL_BUCKLE_AFTER_RELEASE` state in `width.shape` | G4, G14 | limitation |
| L-SHAPE-05 | After-release onsets limited by the reporting threshold are upper bounds. At the foil case pass they equal the 2 I-unit reporting onset (about 0.2 µm of stripe), so nearly any reportable stripe reads "visible after tension release". | A 20 s valve closure shows a band after release for 311 s in the battery demo. | `width.shape`, `width.thermal_events` | G4 | limitation |
| L-SHAPE-06 | Sharp-edged stripes can lock the local released width onto an edge spike. | The tool may report flat where a smooth stripe of the same height buckles. | `width.shape` | G4 | limitation |
| L-SHAPE-07 | The gauge trend carries one stripe shape through all passes; it does not re-solve the roll temperature for each pass. Per-pass trough and wrinkle thresholds appear only for a foil case or a schedule with a pass without a roll gap. | Size not known. | `width.gauge_trend` | - | limitation |
| L-SHAPE-08 | At battery-foil gauge the trend of the cooling-stripe mechanism runs opposite to the plant observation: the in-mill onset of a given stripe rises toward the thin pass and its I-units fall. The rule weights for "worse at thinner gauge" are inherited from sheet gauge. | The model does not reproduce "worse at thinner gauge" through stripes buckling in the mill; onset 1.19 to 17.5 µm from 135 to 18 µm. | `width.gauge_trend` | G4, G9 and plant data | discrepancy |
| L-SHAPE-09 | Short-lived bands close together in width: an event's figures stop at the start of the next event in the same neighbourhood. | What lies beyond is a lower bound. | `width.thermal_events` | - | limitation |
| L-SHAPE-10 | The strip temperature term uses a supplied scan (no heat balance across the width); the expansion coefficient defaults to a textbook value; the thermal strain is not fed back into the roll gap or the tension feedback; the temperature at the shapemeter is taken equal to the scan; without a controller the after-cooling profile equals the mechanical one and the held-flat case is only a bound; no coil cooling or creep; where the mechanical profile was capped the sum is indicative. | About 2.4 I-units per kelvin for aluminium. | `STRIP_TEMPERATURE_TERM_SUPPLIED_PROFILE`, `STRIP_EXPANSION_COEFFICIENT_FROM_MEMORY_DEFAULT`, `STRIP_TEMPERATURE_CHANGES_A_BAND_STATE` | A1 in full (Phase 2); A8 | limitation |
| L-SHAPE-11 | A scan that does not reach the whole width is carried flat to the edges; with no modelled flatness for the pass only the temperature part is shown. | Edge values are extrapolated. | `STRIP_TEMPERATURE_SCAN_DOES_NOT_COVER_STRIP`, `STRIP_TEMPERATURE_TERM_WITHOUT_MECHANICAL_PROFILE` | a full-width scan | exception |
| L-SHAPE-12 | The friction-stripe screen is linear: the force change from a constant-friction roll gap (at foil gauge the experimental model, 0.42 of the reference load) times a supplied friction change, with the unestablished tension feedback; no film model across the width, no starvation, no coupling to the roll temperature, entry tension uniform; no evidence item. | The with-feedback level shows no gauge trend while the compliance-only level grows. | `FRICTION_STRIPE_SCREEN_APPLIED`, `FRICTION_STRIPE_LINEAR_FEEDBACK_NOT_SATURATED` | BT-G4 in full (Phase 2) | limitation |
| L-SHAPE-13 | The local state across the width (oil film, friction, metal strength, strip temperature under a hot stripe) is one-way and rests on an assumed inlet weight: differences from the healthy header only; the share of a roll temperature difference that reaches the inlet oil (default 0.5) has not been measured; nothing returns to the roll temperature; no oil spreading or carry-over; friction heat change left out; strip entry temperature and roughness uniform; the roll surface temperature is the average around the roll. | It changes no other result. | `LOCAL_STATE_COMPUTED`, `LOCAL_STATE_FROM_CIRCUMFERENTIAL_MEAN_SURFACE_TEMPERATURE`, `LOCAL_FRICTION_FROM_PLACEHOLDER_CLOSURE_SLOPE` | a measured inlet temperature across the width (A2) | limitation |
| L-SHAPE-14 | The local sources of a hot stripe (film, metal strength, strip temperature beside the roll growth) are linear and rest on the tension feedback: summed on the linear profile before any buckling cap; force sensitivities of a constant-friction roll gap; nothing feeds back; no evidence item reads them. | The sign of the film term against the roll growth, and so of the net band, depends on the assumed inlet weight in the first tens of seconds after a valve change. | `LOCAL_SOURCES_COMPUTED`, `LOCAL_NET_SIGN_DEPENDS_ON_INLET_WEIGHT`, `LOCAL_SOURCES_REVERSE_A_BAND`, `LOCAL_SOURCES_SUMMED_ON_LINEAR_PROFILE_SATURATION_NOT_APPLIED`, `LOCAL_NET_INCOMPLETE_TERM_MISSING`, `LOCAL_FRICTION_CHANGE_ABOVE_20_PERCENT_LINEAR_SOURCE_INDICATIVE` | a measured inlet weight; feedback to the roll temperature (A2, I1) | limitation |
| L-SHAPE-16 | Buckling with a search over wavelengths (a case option) is a linear bifurcation of a flat, infinitely long strip with free edges, run on the modelled flatness profile (not a measured one) before the band-wise cap: one mode per profile, the most critical; longitudinal stress only, no lateral stress or shear; elastic. After release the half-wave is searched up to the strip width (a square sample, an analyst choice) and the mode is nearly always a whole-sheet mode. It changes no band state or score; the standard states stay the ones the shortlist uses. | Tension raises the critical load and shortens and localises the waves, but the half-wave stays about 0.8 of the mode width against the measured 0.36 to 0.40 of the buckle width (part 5): about twice too long. When the mode waves, only the band it peaks in is decided; the other bands read "not decided (one mode)". | `BUCKLING_FE_REPORTED_BESIDE_SINE_MODE`, `BUCKLING_FE_IN_MILL_STATE_DIFFERS_FROM_SINE_MODE`, `BUCKLING_FE_RELEASED_STATE_DIFFERS_FROM_SINE_MODE`; `width.shape.buckling_fe` | a measured stress profile and wavelength; several modes (G4, Phase 3) | limitation |
| L-SHAPE-17 | The wave height of the wavelength search is a one-mode estimate on the frozen critical mode, with each fibre carrying longitudinal stress only (no in-plane shear, no lateral stress), so the wave is softer than a plate's. It stands in for the gap study's expansion of the buckled state, which is not in the reports. The stress of the buckled band comes from the same estimate (clipped near minus its critical value) and is shown as an additional shapemeter reading only. Nothing in the tally reads either. | An upper estimate, written "of the order of", for the named mode and support (in the mill under tension, hanging free after release); not a height a person would measure on a sample. In the lengthwise demo the buckled band would read 43.6 instead of 50.6 I-units at its peak. | `width.shape.buckling_fe` (wave height, `steady_saturated` shapemeter reading) | a measured wave height with its stress profile (none in the reports) | limitation |
| L-SHAPE-18 | Whether a band lies flat on a table is a gravity criterion on a rigid flat table (the sheet can only lift; not an elastic foundation), with the weightless mode shape at each wavelength, the aluminium density from memory (2700 kg/m3), no friction, adhesion or finite sample length, and no tension-release path. It changes no band state. | With the demos' profiles a band below about 2.2 I-units of peak lies flat at 0.21 mm, below about 0.75 I-units at 30 µm foil: at foil gauge a reportable band still lifts. Lying flat is not "no defect": the length difference is still there. | `DEAD_LOAD_KEEPS_REPORTED_BAND_FLAT_ON_TABLE` | a table or sag measurement with its stress profile (case SS-S14-TABLE not encoded) | limitation |
| L-SHAPE-15 | The crown screens use one centre-minus-edge number (no profile shape or edge drop) and an empirical wide-strip criterion without alloy dependence (its source is inconsistent about the sign); lateral flow uses one constant; the spectrum treats the window as periodic. | Size not known. | `screens`, `width.shape` | G3, G15 | limitation |

### 2.6 Measurement (shapemeter, thickness gauge)

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-MEAS-01 | Shapemeter readings are zone means of the modelled stress profile, not a forecast of the operator's screen: no roll wrap, noise, calibration, temperature compensation, dynamics or filter; the stress still evolves between roll gap and shapemeter; a buckled band no longer carries the stress the linear profile gives it. The operator applies no flatness controller and does not predict what the plant's control would have done (the tool's own spray loop is a separate case option, L-LOOP-01). The readings never enter the evidence. | A narrow or weak band may not show in a zone. | `SHAPEMETER_OPERATOR_APPLIED`, `MODEL_BAND_BELOW_SHAPEMETER_THRESHOLD`, `SHAPEMETER_DOES_NOT_COVER_STRIP` | the vendor's own processing (G5) | limitation |
| L-MEAS-02 | Spreading of a zone's signal to its neighbours is the tool's reading of one vendor sentence (at most 2 × 12.5 %); the vendor algorithm was not read; off by default. | Size not known. | `SHAPEMETER_NEIGHBOUR_SPREADING_APPLIED` | the vendor's description | analyst choice |
| L-MEAS-03 | A shapemeter that corrects for strip temperature is taken to show the flatness without the temperature part; a specific vendor's compensation is not modelled. | Size not known. | `SHAPEMETER_TEMPERATURE_COMPENSATED` | G6 | limitation |
| L-MEAS-04 | The thickness gauge keeps a fraction of a mark through a spot average and a first-order lag only; real gauges have other filters (scanning frames, digital filters, noise); no calibration; the accelerometer position and detection lead time are not built. | Size of the other filters not known. | `GAUGE_TRANSFER_APPLIED`, `GAUGE_KEEPS_LESS_THAN_HALF_OF_OBSERVED_MARK`, `LENGTHWISE_MODEL_BAND_NOT_UNDER_GAUGE` | C7 in full | limitation |
| L-MEAS-05 | When the gauge cannot show the observed spacing, "no gauge variation" still counts as without a gauge description. | The score is unchanged; the flag says the answer tells little. | `GAUGE_NOT_DETECTED_BUT_MARK_NOT_RESOLVABLE` | - | exception |
| L-MEAS-06 | Positions must share one coordinate (barrel or strip); strip tracking offsets are the user's to remove. Forward slip from a model or from speed sensors carries their error; small values need sensor-level precision. | A wrong offset moves every match. | `screens.band_position_match`, `screens.forward_slip` | - | limitation |

### 2.7 Flatness control loop

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-LOOP-01 | The simulated flatness loop (a case option) uses the tool's own control rule on this model; the reports give only its structure. It is never what the plant's controller did and never evidence. | It changes no score. | `FLATNESS_LOOP_SIMULATED` | the plant's own control law (G5) | analyst choice |
| L-LOOP-02 | One spray header on one work roll, spray zones only; the smooth overall shape is assumed removed by bending and tilt, which are not modelled (they enter only as supplied influence vectors). | Size not known. | `LOW_ORDER_FLATNESS_LEFT_TO_BENDING_NOT_MODELLED` | G1 (Phase 3) | limitation |
| L-LOOP-03 | Linear readings: a buckled band reads less in reality. The weak or blocked nozzle itself is not known to the controller. No feed-forward, speed or gauge interaction; fixed control interval and horizon. | Size not known. | `width.flatness_control` and its `limitations` | G4 (buckling), G5 | limitation |
| L-LOOP-04 | The valve events the loop predicts do not enter the thermal events or any evidence item. | - | `width.flatness_control` | - | limitation |
| L-LOOP-05 | Whether the loop settles depends on analyst choices (zone weights, the first dwell) that change the battery-foil outcome from settled to trimming. A loop that does not settle is reported, not corrected. | Settled or trimming is not decided by the model. | `FLATNESS_LOOP_NOT_SETTLED`, `FLATNESS_LOOP_TRIMMING_LIMIT_CYCLE`, `CONTROL_INCREASES_RESIDUAL`, `CONTROL_ZONE_AT_LIMIT`, `CONTROL_MADE_BAND` | the plant's zone weights and timing | analyst choice |
| L-LOOP-06 | The loop can run on a roll grid coarse against the flatness zones. | Size not known. | `FLATNESS_LOOP_ON_COARSE_GRID` | a finer grid | exception |
| L-LOOP-07 | The emulated zone step test fits a constant that belongs to the test: it grows with the test length, depends on which terms are on, and over a short test trades off against the dead time (a 0.15 s delay moves it by a third). The coupling, inlet weight and display filter are assumptions; the fit is the tool's own least squares; the surface temperature is the average around the roll; no plant protocol is recorded. | Read the longer windows beside the short one. | `ZONE_STEP_TEST_EMULATED` | the plant's step-test protocol (A6) | limitation |

### 2.8 Coil, winding and web handling

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-COIL-01 | The coil ridge is a linear stack with a constant compaction factor (default 0.5, an analyst choice): uniform winding tension, a perfectly registered ridge, no interlayer pressure, slip or tension loss. | Size not known. | `width.coil` | G9 (Phase 2) | analyst choice |
| L-COIL-02 | Without a roll gap the exit ridge height uses the proportional limit (exit change = gauge ratio × entry change), an estimate, not a bound. | Its coil result supports only weakly. | `width.coil` | a roll-gap result | limitation |
| L-COIL-03 | The ridge thresholds rest on a steel context (hot-band ridge above about 6 to 7 µm on 0.35 mm strip). | Size not known for aluminium foil. | `width.coil` | G9 | limitation |
| L-COIL-04 | Troughs and wrinkles: the lateral stress in the spans is an input, or computed from an entered roller alignment survey for misalignment and taper only (L-COIL-13); the wrinkle formula assumes a thin, wide, long span far above threshold with clamped ends; isotropic sheet; roll friction and crown are not computed; creases are not predicted, only their elastic precursors; earlier strips are assumed on the same centre line. | Below the trough threshold the amplitude is zero. | `width.troughs` | G11 (Phase 2) | limitation |
| L-COIL-05 | A trough spacing needs a stated band spacing or at least two regular gaps; one gap, or irregular gaps, between bands that may have different sources give at most weak support. | Two or more equal gaps between bands of different sources would still count as a spacing. | the troughs item in the evidence | - | limitation |
| L-COIL-06 | Tension lines have no established model: a rule set with analyst weights on a published description; one candidate pitch (shell buckling of the wound lap) is reported for comparison only, never as evidence; no onset condition, air film or winding model. | Size not known. | `foil_tension_lines` model prediction | G12, G10, G9 | analyst choice |
| L-COIL-07 | The published battery-foil limits are coil temperatures and the process check compares strip exit temperatures. The coil temperature after winding can be estimated (a case option): it starts from the modelled strip exit temperature of the case pass, an upper bound at winding; the surface coefficient, the ambient temperature, the strip conductivity and the gap between laps (or the winding model's air gap) are inputs; no heat from the next laps, no radiation beyond the coefficient, a uniform gap. A thermal-stress estimate between lanes is an upper bound. No creep of the hoop stress and no recovery of the foil in the coil (Phase 3). The process check's verdicts are unchanged; the computed coil temperature is shown beside them. | The strip exit comparison is indicative; the coil estimate is high at winding by the unknown loss before the coil, and its cooling time scales rest on the supplied surface coefficient and gap (radial time scale about 18 h with an oil gap of 0.5 µm, about 330 h with an air gap of 2 µm, on a 0.15 to 0.6 m coil at 8 W/m²K). | `MODELLED_EXIT_TEMPERATURE_ABOVE_BATTERY_COIL_LIMIT`, `COIL_WINDING_TEMPERATURE_TAKEN_AS_STRIP_EXIT_UPPER_BOUND`, `COIL_COOLING_STRESS_REACHES_YIELD`; `width.coil_temperature`, `thermal_check.coil_temperature_beside` | a coil surface temperature against time with a contact probe; creep and recovery (A8, B7, Phase 3) | limitation |
| L-COIL-08 | "Worse at lower tension" is not specific to tension lines: a latent thermal stripe's in-mill onset also falls with tension. | 6.83 µm at 40 MPa against about 1.6 µm at 8 MPa in the demo's notes; the demo leaves the observation unanswered. | the tension observation in the evidence | - | limitation |
| L-COIL-09 | The winding model (a separate module; the lane model and the engine section follow in later packages) needs the radial stack stiffness of the wound foil: how the stack of oily laps, with entrained air, compresses under pressure. No value for aluminium foil is published; the stack law is a required input with no default, and no demo carries one. The model is elastic, per lane, without interlayer slip; laps are lumped into layers; the air gap enters the stiffness only. | The answer depends on that stiffness: for one slightly thicker lane the radius difference in the coil is 0.77, 0.12 or 0.02 of laps × thickness difference for a stiff, a hundred times softer, or an assumed pressure-dependent stack; the present constant 0.5 lies inside that range and has no better or worse support than before. | `RADIAL_STACK_LAW_IS_AN_INPUT_NO_ALUMINIUM_DATA_FOUND`, `INNER_LAPS_IN_HOOP_COMPRESSION`, `LUMPED_LAYERS_FIRST_ORDER` (results of `wound_roll`) | a press test on a stack of 50 to 200 laps of the oily foil (pressure against strain); a coil diameter profile (G9, Phase 2 package 10) | limitation |
| L-COIL-10 | The air film a web carries onto a roll or into the coil is a smooth-web estimate (no side leakage, no roughness venting, no nip film). | An upper bound: about 17 µm on a 0.125 m roll and 40 µm on 0.3 m at 20 m/s and 720 N/m; the real film is smaller by an unknown amount. | results of `wound_roll.entrained_air_film_m` | a nip model and venting (G10, Phase 2 package 11) | limitation |
| L-COIL-11 | Winding by lanes (a case option, beside the present coil check): the exit profile of the case pass is wound lane by lane, the tension shared by a re-derived strain allocation between lanes, with elastic-perfectly plastic laps; perfectly registered lanes, no axial stress, the case-pass profile constant along the coil, plastic thinning and creep left out. Where a new layer's strain is taken (mid layer, the specification, or layer top, the planner's prototype) is an analyst choice. Nothing in the tally reads it; the length difference after unwinding is an additional profile. The other allocation point is run beside the chosen one: a lane whose yield verdict differs reads "not decided: depends on the allocation point", and a lane within 5 % of the yield stress without yielding reads "close to yield, not decided" (an analyst choice). | For one lane 0.1 µm thicker the coil takes up 0.77, 0.12, 0.07 or 0.02 of laps × thickness difference with a stiff, a hundred times softer or two assumed pressure-dependent stacks; a lane 1 µm thicker yields the strip by about 400 laps with every stack but the softest, where the two allocation points disagree on whether it yields at all (peak 158 against 165 MPa). A lane that is thinner and also longer than its neighbours (a model band) is wound at a lower tension, and with a soft stack the factor turns negative: the thin lane stands higher on the coil. One run of the battery-foil demo with a stack law added gave 0.41 with a stiff stack and -1.08 with one a hundred times softer, so the direction of the build-up depends on the stack law too. | `COIL_WINDING_MODEL_REPORTED_BESIDE_LINEAR_CRITERION`, `WINDING_LANE_YIELDS`, `WINDING_LANE_SLACK`, `WINDING_DISAGREES_WITH_LINEAR_RIDGE_CRITERION`; `width.coil_winding` | a press test of the stack; a measured coil diameter profile across the width (G9) | limitation |
| L-COIL-12 | An ironing roll adds a wound-in tension through a traction coefficient that is an input; how much air the nip squeezes out is not known (no nip film formula is in the reports), so the winding is computed for two bounds: the nip removes all the air, and it removes none (the full entrained film in every lap). | The winding results lie between the two bounds; the softer, air-filled bound gives lower stack pressures. | `AIR_CASES_BRACKET_THE_NIP_EFFECT`, `WOUND_IN_TENSION_CAPPED_AT_YIELD`; `width.coil_winding.air_cases`, `nip` | a coil diameter profile across the width, or a measured air content of the wound coil; a nip film model (G10) | limitation |

| L-COIL-13 | Lateral stress in the spans from a roller alignment survey (a case option): only roller misalignment and taper are computed, for a beam model of an isolated span (re-derived; the two angles added in magnitude, a worst case). Roller deflection is reported as beam quantities (load, curvature, end slope, deflection) and no lateral stress is derived from it; a tension drop over a driven roller, a bent coil and a baggy lane as a source of troughs, moment transfer to the next span, a slack edge and the traction limit on the rollers are not modelled. | The computed stress is a lower estimate of the acting one: generators that are not computed add to it. | `width.troughs.<span>.generators`, `lateral_stress_basis`; `SPAN_TENSION_STIFFENING_NOT_NEGLIGIBLE`, `SPAN_SHORTER_THAN_WIDTH_BEAM_MODEL_INDICATIVE` | a lateral stress model of roller deflection, moment transfer and slack edges (G11); a baggy-lane source (I13) | limitation |
| L-COIL-14 | Isolated-span theory over-predicts wrinkling of wide foil: on aluminium foil below 25 µm, wider than 0.6-1 m, wrinkles needed about 15 times the misalignment the model predicts, copper 7-10 times [SS-S55 EX]. The factor is quoted beside the critical misalignments and applied to no threshold; the trials' tension and geometry are not in the reports. | On the battery-foil exit span troughs need 0.61 mm/m and roller wrinkles 12.2 mm/m by the model, 183 mm/m with the factor; a computed stress above a threshold is a screening result, not a prediction that the foil wrinkles. | `foil_factor_context` in `width.troughs.<span>.generators`; benchmark `SS-V14` (reference only) | the trials' inputs, or a wrinkling test on the plant's spans | limitation |
| L-COIL-15 | Evidence rule for a computed lateral stress (the one evidence branch of this phase): a trough status from a stress computed from the entered roller alignment supports the trough hypothesis only weakly and a "below the threshold" from it is neutral, never a contradiction (the computed stress covers two of the generators, and at foil gauge the isolated-span model over-predicts). A supplied plant stress keeps the rule of before (moderate support, weak contradiction) and drives the screen; the computed one is shown beside it with the status it would give. | One point at most from an alignment survey. | the trough-status item in the evidence ("lateral stress computed from the entered roller alignment"), `generators.supplied_vs_computed` | a measured lateral stress | analyst choice |
### 2.9 Mill dynamics and chatter

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-DYN-01 | The chatter model is linear: no limit cycle, mark severity or strip break; a forced response at an unstable operating point is formal only. | It says where the stand becomes unstable, not how bad it gets. | `OPERATING_POINT_LINEARLY_UNSTABLE` | C3 (Phase 3) | limitation |
| L-DYN-02 | The roll-gap damping is a declared heuristic (a fraction of the transit time). | Results without it are always shown beside. | `chatter.critical_speed` | C3 | analyst choice |
| L-DYN-03 | Strip spans are lumped springs, inaccurate near the span's wave resonance. | In the foil demo the onset frequency without roll-gap damping (2133 Hz) lies above the span-wave limit (849 Hz). | `CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT` | C3 | limitation |
| L-DYN-04 | Symmetric (gap-changing) mode only: no roll bending, cross-width or drive dynamics; the antisymmetric frequency is an undamped lumped estimate; backup-roll marking (fifth octave) is screened by its kinematics, not simulated in time. | Size not known. | `stand_modes`, `chatter` | C3, C4, C5 | limitation |
| L-DYN-05 | The gap cylinder is a first-order position loop (no servo-valve, oil column, monitor or eccentricity compensation); the static formulas hold tension constant; spans use either constant speed or constant tension. | The gauge-control effect on chatter depends on the loop roll-off: 9.70 against 13.62 m/s in the demo. | `AGC_CHATTER_INTERACTION_DEPENDS_ON_LOOP_ROLL_OFF` | C1, C2 (Phase 2) | limitation |
| L-DYN-06 | Resonant speeds above 35 m/s are dropped; the chatter scan covers a fixed speed range. | An operating speed outside the scan is not assessed. | `OPERATING_SPEED_OUTSIDE_SCANNED_RANGE` | - | exception |
| L-DYN-07 | The pitch-against-speed law separates kinematic families only, not the source within a family; coil-locked pitches drift with coil diameter and can mimic other laws; speeds within 5 % give no law. | Observations from different coil positions can mislead. | `signatures.pitch_speed_exponent` | marks at clearly different speeds | limitation |
| L-DYN-08 | Bearing and gear frequencies are nominal kinematics without rolling-element slip. | Measured defect frequencies typically deviate by a percent or two. | `signatures` | measured bearing frequencies | limitation |

| L-DYN-09 | Foil gauge control by speed and entry tension (a case option, beside the gaugemeter section): the gauge sensitivities are those of the open-gap foil bite at constant force (or position) and constant tension, from the bite model actually selected; the model has no closed-gap load path, the roll-to-roll (kiss) stiffness is an input and zero when not given. | At the battery-foil case pass 1 MPa of entry tension moves the gauge by 0.18 % and 1 % friction by 0.70 % at constant force; whether these hold at a closed gap is not known. | `GAUGE_SET_BY_STRIP_NOT_BY_GAP`, `KISS_STIFFNESS_NOT_MODELLED_ZERO_USED`; `foil_gauge_control.sensitivities` | a closed-gap load path (G2, BT-G2, Phase 3); gauge, tension and speed logs at 100 Hz | limitation |
| L-DYN-10 | The speed effect on gauge rests entirely on how friction falls with speed: by default the placeholder friction closure's slope, or the load-sharing closure's with an entered contact friction; neither slope has been checked against a mill. The rate term of the flow stress enters only with a rate law. | -3.8 % of gauge per m/s on the battery-foil case pass with the placeholder slope; another slope gives another number, of either size. | `SPEED_EFFECT_FROM_PLACEHOLDER_FRICTION_SLOPE`; `foil_gauge_control.speed` | load and gauge against speed at constant tension on the plant (BT-G13) | limitation |
| L-DYN-11 | The gauge loop is the tool's own structure (integral entry-tension trim, first-order tension loop, transport delay, the gauge's transfer, speed relief at the ramp limit while the trim is held at its limit, optional Smith predictor with a perfect model), not a vendor's controller: no decoupling, adaptive or feed-forward scheme. The crossover rule and the status thresholds are analyst choices; unstable settings are reported with their frequency and not run. A tension ripple is an input; reels, spans and run-out are not modelled here. | With the rule and a 5 Hz tension loop the loop reduces disturbances below about 0.5 Hz and amplifies them up to 1.57 times near 1.1 Hz: the entry coil's once-per-revolution ripple of the demo mill (2.5 Hz) is amplified 1.12 times. | `FOIL_GAUGE_LOOP_SIMULATED`, `LOOP_AMPLIFIES_COIL_FREQUENCY`, `TENSION_TRIM_SATURATES_FOR_ONE_PERCENT_ENTRY_GAUGE`, `UNSTABLE_LOOP_SETTINGS`; `foil_gauge_control.loop`, `step_response` | the plant's controller structure, gains, trim limits and gauge time constant (C1) | analyst choice |
| L-DYN-12 | Reels and coil run-out (a case option inside the foil gauge section): the span is a linear spring between the bite and the reel, the bite a damper through its slip and gauge response to tension, the reel inertia changes with coil radius; the regulator is the tool's own ideal filter (none, or a high-pass with the entered bandwidth), not the plant's tension control; reel friction, binding, ovality harmonics and torque limits are not modelled. The existing chatter model and its spans are unchanged. | On the battery-foil case pass (entry coil 0.5 m, core 0.15 m, 50 kg m² motor assumed, 0.1 mm run-out) the coil-on-span resonance (4.9 Hz) is overdamped by the bite (damping ratio 6.2); the once-per-revolution tension ripple is 94 kPa and the gauge ripple 0.017 % of gauge open loop, 0.019 % with the loop. A bite much less sensitive to tension (closed gap) would lower the damping. | `REEL_RUNOUT_RIPPLE_COMPUTED`, `COIL_ON_SPAN_RESONANCE_CROSSED_DURING_COIL`; `foil_gauge_control.reels` | the plant's tension regulator and reel data; gauge and tension logs over a coil (C2) | limitation |
| L-DYN-13 | Pass chaining: a thickness ripple of a pitch on the entry strip of the first schedule row is carried through the following rows (each starting at the previous exit gauge) with each pass's entry-gauge sensitivity and the case pass's loop settings; the whole coil is assumed to pass from one pass to the next (no trimming, splicing or phase tracking), the pitch stretching by entry over exit gauge; the gauge sensor's transfer is not applied. | The relative ripple changes by `|g_hin|*(h0/h1)*|S|` per pass: 0.733 statically on the battery-foil case pass; whether it grows over a route depends on the loop settings, which are the case pass's. | `RELATIVE_RIPPLE_GROWS_FROM_PASS_TO_PASS`, `ENTRY_RIPPLE_NEAR_STAND_RESONANCE`, `ENTRY_RIPPLE_NEAR_TENSION_LOOP_PEAK`; `foil_gauge_control.pass_chain` | gauge logs of the same coil on successive passes (C8) | limitation |
### 2.10 Roll grinding and roll surface

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-GRIND-01 | No amplitude of grinder marks on foil rolls is published (the open figures are for hot-mill rolls and slender shafts); the feed-mark ceiling of 60 mm and the 12 to 240 count range come from printed grinder settings in patents and trade pages; none of this was checked on a mill. | Size not known. | the grinding rules of the evidence | C4, G13 | analyst choice |
| L-GRIND-02 | Without the grinder's speeds a mark pitch that fits no simple count around the roll cannot rule out grinder chatter; that case reads neutral. | Undecided until grinder data are entered. | `GRINDER_CHATTER_NOT_EXCLUDED_NO_GRINDER_DATA` | the grinder's last-pass wheel and roll speeds, or a counted number of marks | exception |
| L-GRIND-03 | A measured roll profile is one roll's ground shape, measured cold and off the mill; marks narrower than about two grid cells or than four contact half-lengths are smoothed; no wear growth; no change of the barrel position by roll bending; the removed crown is reported only; the grinding hypotheses stay rule-based and never read it; never evidence. | A roll not thermally settled carries 3.3 µm per K on a 280 mm roll; grinder gauges read diameter, so halve the deviations. | `ROLL_GROUND_PROFILE_SUPPLIED`, `ROLL_GROUND_PROFILE_BAND_ABOVE_THRESHOLD`, `ROLL_PROFILE_GRID_TOO_COARSE` | G13 in full, G1 | limitation |
| L-GRIND-04 | The bands of a measured roll profile depend on how the smooth crown is removed (order 4 by default, an analyst choice). | Order 2 leaves a W-shaped residual of 0.68 µm on a cosine-ground roll; order 4 under 0.02 µm. | `ROLL_PROFILE_BANDS_DEPEND_ON_DETREND_ORDER` | the grinder's target curve | analyst choice |
| L-GRIND-05 | No roll-wear model and no temperature-to-surface-finish model: what the research says about roll wear, coating, fines and surface energy is carried as literature statements. | Size not known. | `thermal_check` statements | BT-G9, BT-G11, G13 (Phase 3) | limitation |

### 2.11 Products and data

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-DATA-01 | No plant validation: stand, spans, roll gap, thermal and shape parameters are synthetic and uncalibrated; every demo's observations were generated from the model. | Rankings are model sensitivities, not plant defect rates. | `SYNTHETIC_INPUTS`; status `SCREENING_RESULT_NOT_PLANT_VALIDATED` | plant measurements (gap study section 7.4) | limitation |
| L-DATA-02 | The evidence rules are engineering judgement: weights and thresholds are analyst choices (part 4); the score is an ordinal tally of fit (supports 3/2/1 minus contradictions 6/2/1). | A higher score is a better fit to what was entered, not a measure of how likely a source is. | `limitations` of every result | plant cases with known sources | analyst choice |
| L-DATA-03 | Entered and supplied values are not checked by the tool; a user mill's machine values are used as entered. | Errors in them pass through. | `USER_SUPPLIED_INPUTS_NOT_VERIFIED`, `SUPPLIED_BITE_SENSITIVITIES_NOT_VERIFIED` | - | limitation |
| L-DATA-04 | The product survey runs one synthetic mill per gauge class with the same friction, tension fractions and mill for every product, many assumed flow stresses (18 of 24 rows), doubled passes without a roll gap. | It ranks model sensitivities, not plant defect rates. | product survey `limitations` | - | limitation |
| L-DATA-05 | Product ranges are a literature survey (mostly excerpts, patents, vendor and trade pages); nothing was measured on a plant; the sources disagree (for example on final-pass speed). The product check changes no score. | A pass inside a published span is not thereby a good pass. | `CASE_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE`, `FINAL_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE`, `CASE_STRENGTH_BELOW_STANDARD_MINIMUM_FOR_GAUGE` | - | limitation |
| L-DATA-06 | The plant facts are few: 50 µm input, two single-sheet passes, usual final 17 to 19 µm, down to 12 µm. The demo's intermediate gauges, alloy and temper are assumptions from the nearest published passes and the standard grade. | Size not known. | scenario notes | the plant's schedule, alloy and temper | limitation |
| L-DATA-07 | Demo heat partition: the foil demo uses 0.22 (the middle of the only measured foil-mill range, an abstract and a net balance), with 0.84 and the measured ends as sensitivity rows; the sheet demo keeps 0.84 because no sheet-gauge partition was found (the interface model computes 0.662 for that pass). | See L-HEAT-02. | `width.thermal_sensitivity` | a measured partition | analyst choice |
| L-DATA-08 | Foil facts come from a research pass over trade, association, patent and journal sources, some not peer-reviewed; ranges without a source are marked as from memory. | None is plant-validated. | `foil_regime` | - | limitation |
| L-DATA-09 | One stand of a four-high mill is modelled; multi-stand effects are not. | - | the app's standing limits | - | limitation |
| L-DATA-10 | A part that cannot be computed is reported as such and the rest of the result is kept; a hypothesis that cannot be evaluated reads "cannot tell". | The shortlist may be missing a part. | `HYPOTHESIS_EVALUATION_FAILED`, `MEASUREMENT_SECTION_FAILED`, `NEXT_MEASUREMENTS_FAILED`, `STRIP_MAP_FAILED`, `SIGNATURES_SECTION_FAILED`, `SCREENS_SECTION_FAILED`, `THERMAL_CHECK_FAILED`, `MATERIAL_SELECTION_FAILED`, `THERMAL_SENSITIVITY_PER_PASS_FAILED`, `THERMAL_SENSITIVITY_FAILED`, `BITE_DERIVATION_FAILED_CHATTER_NOT_ASSESSABLE`, `WIDTH_SECTION_PARTIAL_FAILURE` | - | exception |
| L-DATA-11 | Band positions closer than 1 mm are merged into one band. | - | `DUPLICATE_BAND_POSITIONS_MERGED` | - | exception |
| L-DATA-12 | The benchmark harness is a software comparison: a published model value or one measurement read from a paper; a test that passes on a recorded discrepancy records the gap, it does not mean the physics is right. A tandem mill is outside the single-stand chatter model; the steel chatter case is run on one stand with three substitutions. | See part 5. | `python -m physicroll.benchmarks` | G16, BT-G17 | limitation |

### 2.12 The guided app

| id | what the tool assumes or cannot do | what it means for a reader | how the result shows it | what would lift it | kind |
|---|---|---|---|---|---|
| L-APP-01 | The app screens: the shortlist ranks how well each candidate fits what you entered, with evidence weights that are engineering judgement; it does not name a single source. | Read the shortlist as candidates to check. | the result page | - | limitation |
| L-APP-02 | The trust level is a rule, not a statistic; it is never higher than fair because nothing has been compared with plant data. Low is the normal level until your own mill values and more observations are entered. | - | the trust block, "Why not higher?" | your mill values and more observations | limitation |
| L-APP-03 | A quick run leaves out up to six things: the heat-share and spray-coefficient sensitivity table, the fine roll-temperature grid, the fine roll-gap grid, the per-pass friction stripe estimate, the wavelength search for waves and the effects of a hot stripe on the oil and the metal. On the four demos and two plant dry runs the quick runs gave the same scores, standings and ranks as the detailed runs. | That equality was checked on those six cases. | every result says which kind produced it; "Run in detail" | a detailed run | limitation |
| L-APP-04 | The typical mills, the worked examples and the product values are synthetic or literature values. | - | `SYNTHETIC_INPUTS` | your mill values | limitation |
| L-APP-05 | The page's "weak" nozzle has a flow level of 0.5 (the demos use 0.45); the simple spray coverage check knows only on and off and counts every weak or blocked nozzle as not spraying. | Size not known. | the strip drawing | - | analyst choice |
| L-APP-06 | Without the shapemeter answered, an opened case's flatness loop and zone step test are left out of the run. | Those two parts are not shown. | the result page | answer the shapemeter group | exception |
| L-APP-07 | The printed summary fits one A4 page for a result like the lengthwise example from a desktop window; a long tied shortlist, the battery-foil example or a print from a phone-size window takes two pages. | - | - | - | limitation |
| L-APP-08 | The app does not ask for the roller tube of an alignment span, the exit reel of the gauge control or the air mode of the coil winding. | Those parts run with the engine's defaults (no roller tube: beam quantities of the deflector; no exit reel; winding without air) unless a case file supplies them. | the guide, section 2.3 | an opened case file that carries them | limitation |

## 3. Outcomes that depend on an unmeasured input

These are the results whose answer, not only whose size, turns on something nobody has measured.

- **Whether the spray loop settles or keeps trimming** (L-LOOP-05): the zone weights and the
  timing of the first change are analyst choices, and they change the battery-foil outcome from
  settled to trimming.
- **The sign of the net band in the first seconds after a zone closes** (L-SHAPE-14): whether the
  film and metal-strength parts add to or cancel the roll growth depends on the share of the roll
  temperature that reaches the inlet oil, which has not been measured (default 0.5).
- **Stripe heights** (L-HEAT-02, L-HEAT-03): they scale with the roll heat share and fall with the
  spray coefficient; the only measured share is an abstract's net balance, and the basis of the
  published spray coefficient (under the jet or around the roll) is not established.
- **The friction-stripe size and every thin-gauge band height** (L-SHAPE-02, L-SHAPE-12,
  L-SHAPE-19): the two levels, with and without the exit-tension feedback, are two orders of
  magnitude apart, and the literature neither supports nor contradicts the feedback. A second
  estimate of the feedback (the width-coupling kernel, with an assumed lateral hold at the roll
  gap) gives 0.10 of it at foil gauge and 0.69 at sheet gauge in the demos, so at foil gauge a
  band may be about nine times the standard level; the tally uses the standard level.
- **The foil roll-gap reference load** (L-BITE-06): the published loads depend on an end length
  the paper does not state (78 to 134 against the model's 88.9 to 92.9).
- **The grinder chatter pitch test** (L-GRIND-02): without the grinder's speeds a grinder
  pattern cannot be ruled out and the test reads neutral.
- **How a coil winds a thicker lane** (L-COIL-01, L-COIL-09): the radial stack stiffness of the
  wound oily foil is not published; for a lane 0.1 µm thicker, with a stiff, a hundred times
  softer or two assumed pressure-dependent stacks the coil takes up 0.77, 0.12, 0.07 or 0.02 of
  laps × thickness excess (the lane model of the engine, L-COIL-11), against the present 0.5; a
  lane 1 µm thicker yields by about 400 laps except with the softest stack, so whether a coil
  ridge yields the strip is not decided by the model. For a model band, which is thinner and
  longer than its neighbours, even the direction is open: 0.41 with a stiff stack, -1.08 with
  one a hundred times softer (one run of the battery-foil demo). A press test on a stack
  of the plant's foil decides it.
- **Whether a coil is above a published coil limit** (L-COIL-07): the coil estimate starts
  from the modelled strip exit temperature (an upper bound) and cools with a supplied surface
  coefficient and gap between laps, neither measured; the radial cooling time changes about
  twentyfold between an oil gap and an air gap.
- **How much air an ironing roll removes** (L-COIL-12): unknown; the winding is given for the
  two bounds.
- **The fitted step-test constant** (L-LOOP-07, L-HEAT-09): it grows with the test length, so it
  says nothing about the plant until the plant's test length and display filter are known.
- **The speed effect on foil gauge** (L-DYN-10): `dh/du` follows the friction closure's speed
  slope, which nobody has measured on a mill (the placeholder by default, or the load-sharing
  closure with an entered contact friction); the gauge loop's speed relief inherits it.

## 4. Analyst choices

Every constant or rule the code tags `[D]`, "analyst choice", "the tool's own" or "the project's
own" on its assignment line, found by the search `ANALYST_CHOICE_PATTERN` in
`physicroll/limitations.py` over `physicroll/*.py`, and below it the choices that search does not
catch (a tag on the line above, or a threshold that section 14 of the guide calls an analyst
choice without a tag in the code). "Sensitivity" is given where the code or the guide reports one.

| constant | value | where used | stands in for | sensitivity |
|---|---|---|---|---|
| `REALISTIC_MAX_EXIT_SPEED_M_S` | 35 m/s | resonant-speed envelope of the transverse rules | a mill's top speed | resonant speeds above it are dropped |
| `DEFAULT_INLET_WEIGHT` | 0.5 | local state across the width | the share of a roll temperature difference reaching the inlet oil (not measured) | sets the sign of the net band (part 3) |
| `DEFAULT_CAPTURE_FRACTION` | 1.0 | oil supply across the width | the share of a nozzle's oil reaching the roll | not reported |
| `ETA_STEP_K` | 1 K | local state | step of the heat-partition derivative | numerical |
| `FAST_PATH_TIME_S` | 20 s | local sources | the time after a valve change at which the fast path is read (surface time scale 8 to 25 s) | not reported |
| `WEAK_NOZZLE_LEVEL` | 0.5 | guided app | the flow of a "weak" nozzle (demos 0.45) | not reported |
| `FRICTION_FIXED_POINT_TOL` | 1e-4 | computed friction | convergence of the friction loop | numerical |
| `INLET_ANGLE_BASIS_ARC` | rule | oil film | inlet slope of the deformed arc for the sheet roll gap | - |
| `IDENT_REFINE_SOLVES` | 8 | friction from pass records | refinement steps | numerical |
| `IDENT_PARABOLA_STEPS` | 6 | friction from pass records | joint-fit steps | numerical |
| `IDENT_PARABOLA_TOL` | 1e-4 | friction from pass records | joint-fit tolerance | numerical |
| `IDENT_UNCERTAINTY_BASIS` | rule | friction from pass records | first-order spread of the identified friction | - |
| `SPREADING_BASIS` | rule | shapemeter | the reading of one vendor sentence on neighbour spreading | off by default |
| `GAUGE_RESOLVABLE_GAIN` | 0.5 | thickness gauge | when a gauge "cannot show" a mark | sets the flag only |
| `MIN_LN_SPEED_SPREAD` | ln 1.05 | pitch-speed law | speeds within 5 % give no law | - |
| `MAX_EXIT_SPEED_M_S` (signatures) | 200 m/s | input check | a sanity envelope far above real mills | - |
| `ENTRY_TENSION_FRACTION` | 0.20 of flow stress | product survey | entry tension | stated per row |
| `EXIT_TENSION_FRACTION` | 0.23 of flow stress | product survey | exit tension (foil demo 40/175) | stated per row |
| `ASSUMED_REDUCTION_BASIS` | 30 % | product survey | final-pass reduction where none is published | stated per row |
| `CALIBRATION_SCAN` | 9 | spray calibration | start values of the search | numerical |
| `CALIBRATION_HEAT_SHARE_STEP` | +10 % | spray calibration | the heat-share step for the reported shift of the fit | reported |
| `STRIPE_THRESHOLD_M` | 0.1 µm | roll stripes | reporting threshold for a radius stripe | smaller stripes not reported |
| `SURFACE_CYCLE_WEIGHTS` | 9 | roll surface cycle | unit solutions over the spray-weight range | numerical |
| `SURFACE_CYCLE_TOLERANCE_K` | 1e-4 K | roll surface cycle | periodicity tolerance | numerical |
| `MADE_BAND_MIN_S` | 20 s | flatness loop | how long a loop-made band must last (literature band life 20 to 120 s) | not reported |
| `AGREEMENT_BAND` | 0.9 to 1.1 | benchmarks | what counts as agreement with a published value | part 5 |
| `ROLL_NU_FOR_SOLVER` | 0.3 | benchmarks | roll Poisson ratio to pass the modulus | - |
| `SOLVER_WIDTH_M` | 1 m | benchmarks | width for a load per width | - |
| `DEMO_ROLL_E_STAR_PA` | 210 GPa / 0.91 | benchmarks | the demo mill's roll modulus | - |
| `KEROSENE_BETA_20_70C_PER_K` | 0.015 /K | oil viscosity | kerosene viscosity slope 20 to 70 °C | - |
| `KEROSENE_BETA_70_130C_PER_K` | 0.012 /K | oil viscosity | kerosene viscosity slope 70 to 130 °C | - |
| `ALUMINIUM_VOLUMETRIC_HEAT_CAPACITY_J_M3K` | 2.43e6 J/m³K | pass heating | density times heat capacity | - |
| `VISCOSITY_EXTRAPOLATION_WARN_K` | 60 K | oil viscosity | how far beyond the data a warning starts | - |
| `SPEED_DERIVATIVE_RELATIVE_STEP` | 1e-4 | friction-speed slope | numerical step | numerical |
| `MAX_SPEED_M_S` (tribology) | 200 m/s | input check | sanity envelope | - |
| `TOME_SIMPSON_PANELS` | 64 | hardening | integration panels | numerical |
| `FIT_CHARACTERISTIC_STRAINS` | 0.05 to 5, 60 steps | hardening fit | scan of the characteristic strain | numerical |
| `FIT_PARABOLA_STEPS` | 8 | hardening fit | refinement steps | numerical |
| `FIT_PARABOLA_TOL` | 1e-6 | hardening fit | refinement tolerance | numerical |
| `TRIM_BAND_FACTOR` | 3 | flatness loop | "trimming" means within 3 × the dead band | decides settled / trimming |
| `DEFAULT_INTEGRAL_GAIN` | 0.1 | flatness loop | the controller gain | the outcome (L-LOOP-05) |
| `DEFAULT_HYSTERESIS_FRACTION` | 0.1 | flatness loop | valve hysteresis | the outcome (L-LOOP-05) |
| `DEFAULT_REGULARISATION_FRACTION` | 0.01 | flatness loop | least-squares regularisation | the outcome (L-LOOP-05) |
| `LAW_LABEL` | rule | flatness loop | the tool's own control law | - |
| `FIT_TAU_GRID_S` | 1 s to 2038 s | step-test fit | grid of time constants | numerical |
| `FIT_DEAD_TIME_MAX_S` | 30 s | step-test fit | largest dead time | trades off with the constant (L-LOOP-07) |
| `FIT_NOT_FIRST_ORDER_FRACTION` | 5 % | step-test fit | when a response is "not first order" | sets a flag |
| `HILL_TOL` | 0.02 of the shear strength | half-space roll gap | friction-hill bounds | numerical |
| `SPECTRUM_FLAG_FRACTION` | 0.05 | strip shape | short-wavelength flag | sets a flag |
| `KERNEL_CLOSURE` | the strip leaves the roll gap moving straight | width-coupling kernel level | how the strip is held sideways at the roll gap | 0.69 against 0.24 (sheet demo), 0.10 against 0.009 (foil demo) with the uniaxial hold (L-SHAPE-19) |
| `KERNEL_BASIS` | rule | width-coupling kernel | the re-derived span model (no equations in the reports) | L-SHAPE-19 |
| `FEEDBACK_BASIS` | rule | strip shape | the planner's exit-tension feedback (L-SHAPE-02) | two orders of magnitude (part 3) |
| `BASIS` (strip buckling) | rule | wavelength search | the energy, element and search method the project derived (no equations in the reports) | closed forms recovered (L-SHAPE-16) |
| `AMPLITUDE_BASIS` | rule | wave height | the one-mode estimate in place of the gap row's expansion | upper estimate (L-SHAPE-17) |
| `TABLE_BASIS` | rule | table criterion | the gravity criterion in place of the gap row's foundation | L-SHAPE-18 |
| `RELEASED_SAMPLE_LENGTH_FACTOR` | 1 × strip width | wavelength search after release | the longest half-wave searched (a square sample) | the mode sits at this limit (L-SHAPE-16) |
| `LOCAL_RELEASED_WIDTH_FACTOR` | 2 | after-release local mode | the local buckle's width limit (L-SHAPE-04) | not reported |
| `SPAN_TENSION_STIFFENING_LIMIT` | 0.5 | lateral stress in spans | the tension-stiffening parameter `K*a` above which the beam model of a span is flagged (0.19-0.21 in the demos) | sets the flag only (L-COIL-13) |

| `CROSSOVER_RULE_FACTOR` | 0.5 | foil gauge loop | integral crossover `w_c = 0.5/(theta + tau_g + 1/w_T)` when none is entered (about 60 degrees phase margin) | 61.4 degrees, 1.57 peak amplification on the battery-foil case pass (L-DYN-11) |
| `TIME_STEP_MAX_S` | 1 ms (and at most a fortieth of the dead time) | foil gauge loop time run | explicit step | numerical (the time run equals the frequency response within 0.5 % for a sinusoid) |
| `SETTLED_FRACTION` | 5 % | foil gauge loop time run | "settled": within 5 % of the first value for the last 5 s | the status word only (L-DYN-11) |
| `OSCILLATING_FRACTION` | 20 % | foil gauge loop time run | "oscillating": last 5 s peak-to-peak above 20 % of the first value | the status word only (L-DYN-11) |
| `GAUGE_SET_BY_STRIP_LIMIT` | 0.1 | foil gauge sensitivities | `dh/dS` below which the strip, not the gap, sets the gauge | sets the flag only (L-DYN-09) |
| `RESONANCE_FREQUENCY_BAND` | 10 % | reels | "the once-per-revolution and coil-on-span frequencies meet" (also a sign change between two sweep radii) | sets the flag only (L-DYN-12) |
| `RESONANCE_DAMPING_LIMIT` | 0.5 | reels | a resonance counts only when lightly damped | sets the flag only (L-DYN-12) |
| `STAND_RESONANCE_BAND` | 10 % | pass chaining | a chained ripple "near" a stand (chatter onset) or tension-loop peak frequency | sets the flags only (L-DYN-13) |
| regulator `"direct"` | `s/(s + w_b)` | reels | the simplest form of a regulator that cannot attenuate above its bandwidth | the tension ripple below the bandwidth (L-DYN-12) |
Not caught by the search:

| constant | value | where used | stands in for | sensitivity |
|---|---|---|---|---|
| `FEED_MARK_SPACING_CEILING_M` | 60 mm | grinding feed marks | just above the largest printed final-pass feed | L-GRIND-01 |
| `GRINDER_CHATTER_COUNT_RANGE` | 12 to 240 | grinder chatter | range of printed grinder settings | L-GRIND-02 |
| `ROLL_PROFILE_DETREND_ORDER_DEFAULT` | 4 | measured roll profile | crown removal | L-GRIND-04 |
| `PASS_RECORD_UNCERTAINTY_DEFAULTS` | force 5 %, slip 0.01, torque 10 % | friction from pass records | uncertainties of records entered without one | the reported interval |
| `NARROW_STRIPE_REFERENCE_WIDTH_M` | 30 mm | measured roll profile | the narrow stripe the grid check uses | sets a flag |
| `DEFAULT_COMPACTION_FACTOR` | 0.5 | coil ridge | interwrap compaction | L-COIL-01; the winding model gives 0.02 to 0.77 with the stack stiffness (L-COIL-09) |
| `BASIS` (wound roll) | rule | winding model | the re-derived accretion equation and its lumped layers | L-COIL-09 |
| `ALLOCATION_BASIS` | rule | winding by lanes | the re-derived strain allocation between lanes (relaxation radius) | L-COIL-11 |
| `allocation_radius` | mid layer (prototype: layer top) | winding by lanes | where a new layer's strain is taken | up to 17 % on the factor of the softest stack; decides whether a 1 µm lane yields there (L-COIL-11) |
| `CW_DEFAULT_LANE_WIDTH_M` | 50 mm (else the shapemeter zone width) | winding by lanes | lane width | not reported |
| `CW_CLOSE_TO_YIELD_FRACTION` | 5 % | winding by lanes | how close to yield a lane must come to read "close to yield, not decided" | the verdict wording only (L-COIL-11) |
| `AIR_CONDUCTIVITY_W_MK` | 0.026 W/mK (from memory) | coil temperature | air in the gap between laps | the radial conductivity (L-COIL-07) |
| cooling grid | 40 cells, 400 equal steps | coil temperature | discretisation of the two 1-D cooling solutions | numerical |
| wound-in tension cap | 1e-6 below yield | ironing roll | the allocation needs a mean below yield | L-COIL-12 |
| `AIR_VISCOSITY_PA_S` | 1.8e-5 Pa s (from memory) | air film | air viscosity | L-COIL-10 |
| air gap in the stiffness only | rule | winding model | whether the gap adds to the stack radius | not reported |
| `DEFAULT_REPORTING_THRESHOLD_I_UNITS` | 2 I-units | strip shape | the reporting onset of a band | L-SHAPE-05 |
| `MARGINAL_FORWARD_SLIP` | 0.005 | forward-slip screen | a marginal slip | - |
| `EDGE_OR_CENTRE_FRACTION` | 15 % | lengthwise rules | edge or centre band | - |
| `PLATE_BUCKLING_COEFFICIENT` | 4 (from memory) | buckling | the buckle mode | L-SHAPE-03 |
| `VENDOR_OVERLAP_MAX_WIDTH_OVER_PITCH` | 1.5 nozzle pitches | spray header | the upper end of the makers' overlap practice (1.1 to 1.5) above which the wide-overlap flag is set | sets a flag only (L-HEAT-14) |
| parabolic footprint `1.5*(1 - (2x/W)**2)` | rule | spray header option | the makers' "parabolic" fan, for which no profile is published | deficit 1.5 times deeper, 0.7 times as wide (L-HEAT-13) |
| realistic-header demo header | 30 degrees, 15 degrees, standoff 0.1306 m (1.3 pitches) | `scenarios/band_diagnosis_realistic_header.json` | a header chosen to match vendor overlap practice, not a mill specification | L-HEAT-14 |
| `ALUMINIUM_DENSITY_KG_M3` | 2700 kg/m³ (from memory) | table criterion | the strip density | flagged when used (L-SHAPE-18) |
| dead-load scan | half-waves 1/40 to 4 × strip width, 24 wavenumbers | table criterion | the range of table waves searched | the battery-foil limit sits at the shortest (L-SHAPE-18) |
| `BF_MAX_EVENTS` | 4 | wavelength search | events searched besides the steady profile (run time) | later events are counted, not searched |
| `FIXED_FREQUENCY_MIN_SLOPE`, `SPEED_INDEPENDENT_MAX_ABS_SLOPE` | 0.7, 0.3 | pitch-speed law | the pitch-exponent bands | - |
| `POSITION_TOLERANCE_DEFAULT_M` | 10 mm | lengthwise rules | position match | - |
| evidence weights | supports 3/2/1, contradictions 6/2/1 | every hypothesis | strong / moderate / weak | L-DATA-02 |
| the quarter-pitch position tolerance and the 0.3 to 3 × duration window | rule | evidence rules | band position and duration match | - |
| `SLIP_CONSISTENCY` rule | rule | half-space roll gap | rejects the degenerate branch (L-BITE-08) | - |
| tension-line weights | rule | `foil_tension_lines` | weights on a published description (L-COIL-06) | - |
| zone weights and first dwell of the loop | case values | flatness loop | the plant's zone weighting and timing | the outcome (L-LOOP-05) |
| spray coefficient for kerosene sprays | 0.5 to 2 kW/m²K (planner estimate) | roll temperature model | no measured value found | L-HEAT-02 |

## 5. Recorded discrepancies with published values

<!-- BEGIN GENERATED BLOCK: discrepancies (python -m physicroll.limitations --write docs/limitations.md; do not edit by hand) -->
The benchmark harness records 119 project values in 28 cases. 6 carry the verdict "within the agreement band" (project / reference 0.9 to 1.1); 27 record a project value for which no published value exists. The other 86 are listed here, including rows whose ratio lies inside the band but whose verdict qualifies the comparison (numbers to four significant digits).

| case | quantity | unit | project | reference | ratio | verdict | in plain words |
|---|---|---|---|---|---|---|---|
| BT-V1 | `w_bar` | 1 | 49.77 | 118 | 0.4218 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-V1 | `w_bar` | 1 | 49.77 | 120 | 0.4148 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-V1 | `w_bar` | 1 | 49.77 | 62 | 0.8028 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-V1 | `force_per_width_n_m` | N/m | 1.019e+06 | 2.42e+06 | 0.421 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-V1 | `contact_length_m` | m | 0.001474 | 0.00214 | 0.689 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-V2-R89 | `w_bar` | 1 | 41.07 | 58 | 0.7081 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-V2-R135 | `w_bar` | 1 | 51.05 | 58 | 0.8802 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-V3-FIG1-140UM | `w_bar` | 1 | 45.97 | 50 | 0.9194 | `REFERENCE_READ_BY_EYE` | published value read by eye from a figure |
| SS-V2 | `critical_i_units` | I | 4.017 | 5.3 | 0.7579 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2 | `critical_i_units` | I | 4.017 | 6.38 | 0.6296 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2 | `critical_i_units` | I | 4.017 | 8.92 | 0.4503 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2 | `half_wave_m` | m | 0.15 | 0.06 | 2.5 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V3 | `half_wave_m` | m | 0.105 | 0.0375 | 2.8 | `RECORDED_DISCREPANCY` | does not match the published value |
| TM-LC7 | `critical_exit_speed_m_s` | m/s | 8.101 | 8.715 | 0.9296 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| TM-LC7 | `critical_exit_speed_m_s` | m/s | 8.101 | 5.81 | 1.394 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-V1-HS | `w_bar_rigid_strip` | 1 | 88.86 | 118 | 0.753 | `REFERENCE_NOT_GRID_INDEPENDENT` | published value not grid independent |
| BT-V1-HS | `w_bar_strip_spring_80_gpa` | 1 | 92.94 | 118 | 0.7876 | `REFERENCE_NOT_GRID_INDEPENDENT` | published value not grid independent |
| BT-V1-HS | `peak_pressure_over_ys_rigid_strip` | 1 | 7.521 | 7.7 | 0.9768 | `REFERENCE_READ_BY_EYE` | published value read by eye from a figure |
| BT-V1-HS | `peak_pressure_over_ys_strip_spring_80_gpa` | 1 | 7.331 | 7.7 | 0.9521 | `REFERENCE_READ_BY_EYE` | published value read by eye from a figure |
| BT-V1-HS | `peak_position_rigid_strip_m` | m | 0.0003054 | 0.00041 | 0.7449 | `REFERENCE_READ_BY_EYE` | published value read by eye from a figure |
| BT-V1-HS | `peak_position_strip_spring_80_gpa_m` | m | 0.0003494 | 0.00041 | 0.8522 | `REFERENCE_READ_BY_EYE` | published value read by eye from a figure |
| BT-V1-HS | `contact_start_rigid_strip_m` | m | -0.001118 | -0.00118 | 0.9477 | `REFERENCE_READ_BY_EYE` | published value read by eye from a figure |
| BT-V1-HS | `contact_end_rigid_strip_m` | m | 0.0008432 | 0.00095 | 0.8875 | `REFERENCE_READ_BY_EYE` | published value read by eye from a figure |
| BT-V2-R89-HS | `w_bar` | 1 | 42.8 | 58 | 0.7379 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-V2-R135-HS | `w_bar` | 1 | 67.13 | 58 | 1.157 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-V3-FIG1-140UM-HS | `w_bar` | 1 | 46.82 | 50 | 0.9364 | `REFERENCE_READ_BY_EYE` | published value read by eye from a figure |
| BT-V3-EQ29-HS | `entry_gauge_r50_without_no_slip_zone_m` | m | 5.4e-05 | 5.125e-05 | 1.054 | `CONSISTENT_REGIME` | same regime as the published formula |
| BT-V3-EQ29-HS | `entry_gauge_r50_with_no_slip_zone_m` | m | 5.2e-05 | 5.125e-05 | 1.015 | `CONSISTENT_REGIME` | same regime as the published formula |
| BT-V3-EQ29-HS | `entry_gauge_r25_without_no_slip_zone_m` | m | 3.4e-05 | 3.624e-05 | 0.9382 | `CONSISTENT_REGIME` | same regime as the published formula |
| BT-V3-EQ29-HS | `entry_gauge_r25_with_no_slip_zone_m` | m | 3.2e-05 | 3.624e-05 | 0.883 | `CONSISTENT_REGIME` | same regime as the published formula |
| BT-V3-EQ29-HS | `entry_gauge_r10_without_no_slip_zone_m` | m | 2.8e-05 | 2.292e-05 | 1.222 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-V3-EQ29-HS | `entry_gauge_r10_with_no_slip_zone_m` | m | 2.6e-05 | 2.292e-05 | 1.134 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-X29-LOAD-EXPONENT-HS | `load_exponent_in_friction` | 1 | 2.461 | 2 | 1.23 | `REFERENCE_READ_BY_EYE` | published value read by eye from a figure |
| BT-X29-LOAD-EXPONENT-HS | `load_exponent_in_friction` | 1 | 2.461 | 2.6 | 0.9465 | `REFERENCE_READ_BY_EYE` | published value read by eye from a figure |
| BT-G3-FILM-E6-T42 | `film_thickness_30_m_s_m` | m | 3.242e-07 | 3.23e-07 | 1.004 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-G3-FILM-E6-T42 | `film_thickness_10_m_s_m` | m | 1.081e-07 | 1.08e-07 | 1.001 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-G3-FILM-E6-T42 | `film_thickness_5_m_s_m` | m | 5.404e-08 | 5.4e-08 | 1.001 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-G3-FILM-E6-T42 | `film_thickness_3_m_s_m` | m | 3.242e-08 | 3.2e-08 | 1.013 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-G3-FILM-E6-T42 | `film_thickness_1_m_s_m` | m | 1.081e-08 | 1.1e-08 | 0.9825 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-V4-FILM | `film_ratio_5_m_s` | 1 | 0.2093 | 0.22 | 0.9515 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-V4-FILM | `film_ratio_40_m_s` | 1 | 1.675 | 1.76 | 0.9515 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| A9-PRESSURE-LAWS-KEROSINE | `viscosity_barus_625_mpa_pa_s` | Pa s | 0.9372 | 2.5 | 0.3749 | `RECORDED_DISCREPANCY` | does not match the published value |
| A9-PRESSURE-LAWS-KEROSINE | `viscosity_barus_945_mpa_pa_s` | Pa s | 26.13 | 15 | 1.742 | `RECORDED_DISCREPANCY` | does not match the published value |
| A9-PRESSURE-LAWS-KEROSINE | `viscosity_barus_1510_mpa_pa_s` | Pa s | 9313 | 740 | 12.58 | `RECORDED_DISCREPANCY` | does not match the published value |
| A9-PRESSURE-LAWS-KEROSINE | `viscosity_roelands_625_mpa_pa_s` | Pa s | 0.18 | 2.5 | 0.072 | `RECORDED_DISCREPANCY` | does not match the published value |
| A9-PRESSURE-LAWS-KEROSINE | `viscosity_roelands_945_mpa_pa_s` | Pa s | 1.228 | 15 | 0.08189 | `RECORDED_DISCREPANCY` | does not match the published value |
| A9-PRESSURE-LAWS-KEROSINE | `viscosity_roelands_1510_mpa_pa_s` | Pa s | 24.36 | 740 | 0.03292 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-G3-CRUSHING-LAWS | `w_thesis_fit_eq_3_20_a050_p10` | 1 | 1.62 | 1.47 | 1.102 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-G3-CRUSHING-LAWS | `w_thesis_fit_eq_3_20_a050_p06` | 1 | 0.05 | 0.16 | 0.3125 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-G3-CRUSHING-LAWS | `w_korzekwa_regression_a050_p10` | 1 | 1.761 | 1.47 | 1.198 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-G3-CRUSHING-LAWS | `w_korzekwa_regression_a050_p06` | 1 | 0.5869 | 0.16 | 3.668 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-G3-CRUSHING-LAWS | `w_marsault_form_a050_p10` | 1 | 1.62 | 1.47 | 1.102 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-G3-CRUSHING-LAWS | `w_marsault_form_a050_p06` | 1 | 0.5832 | 0.16 | 3.645 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-G3-CRUSHING-LAWS | `w_wilson_sheu_fit_a050_p10` | 1 | 5.471 | 0.67 | 8.166 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-G3-CRUSHING-LAWS | `w_wilson_sheu_fit_a050_p06` | 1 | 1.126 | 0.32 | 3.518 | `RECORDED_DISCREPANCY` | does not match the published value |
| BT-V2-FRICTION-HS | `friction_from_force_r89` | 1 | 0.03063 | 0.026 | 1.178 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| BT-V2-FRICTION-HS | `friction_from_force_r135` | 1 | 0.02488 | 0.026 | 0.9569 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| TM-LA19-HEAT-SPLIT | `strip_share_perfect_contact_vs_low_end` | 1 | 0.1621 | 0.11 | 1.473 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| TM-LA19-HEAT-SPLIT | `strip_share_perfect_contact_vs_high_end` | 1 | 0.1621 | 0.33 | 0.4911 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| TM-LA19-HEAT-SPLIT | `strip_share_film_70nm_k0125_vs_low_end` | 1 | 0.2279 | 0.11 | 2.072 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| TM-LA19-HEAT-SPLIT | `strip_share_film_70nm_k0125_vs_high_end` | 1 | 0.2279 | 0.33 | 0.6905 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| TM-LA19-HEAT-SPLIT | `strip_share_film_70nm_k025_vs_low_end` | 1 | 0.1952 | 0.11 | 1.775 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| TM-LA19-HEAT-SPLIT | `strip_share_film_70nm_k025_vs_high_end` | 1 | 0.1952 | 0.33 | 0.5916 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| TM-LA8-SPRAY-FIT | `fitted_spray_htc_low_w_m2k` | W/m2K | - | 1.75e+04 | - | `REFERENCE_ONLY_INPUTS_NOT_RECORDED` | published value only; inputs not recorded |
| TM-LA8-SPRAY-FIT | `fitted_spray_htc_high_w_m2k` | W/m2K | - | 2.2e+04 | - | `REFERENCE_ONLY_INPUTS_NOT_RECORDED` | published value only; inputs not recorded |
| SS-V8-LOOP | `final_largest_zone_residual` | I-units | 3.252 | 6 | 0.5419 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| A6-ZONE-TIME-CONSTANT | `time_constant_20s_test_roll_growth_only` | s | 43.43 | 20 | 2.171 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| A6-ZONE-TIME-CONSTANT | `time_constant_20s_test_as_measured_hot` | s | 34.47 | 20 | 1.724 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2-LOCAL-PLATE | `critical_i_units_simply_supported` | I | 5.341 | 5.3 | 1.008 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2-LOCAL-PLATE | `critical_i_units_clamped` | I | 8.649 | 8.92 | 0.9696 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2-LOCAL-PLATE | `half_wave_simply_supported_m` | m | 0.1495 | 0.06 | 2.491 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2-LOCAL-PLATE | `half_wave_clamped_m` | m | 0.09956 | 0.06 | 1.659 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2-WIDE-STRIP | `critical_peak_i_units_10_mpa` | I | 12.3 | 7.5 | 1.64 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2-WIDE-STRIP | `half_wave_m_10_mpa` | m | 0.1767 | 0.06 | 2.946 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2-WIDE-STRIP | `half_wave_over_mode_width_10_mpa` | 1 | 0.8033 | 0.4 | 2.008 | `RECORDED_DISCREPANCY` | does not match the published value |
| SS-V2-WIDE-STRIP | `critical_peak_i_units_30_mpa` | I | 27.22 | 7.5 | 3.629 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2-WIDE-STRIP | `half_wave_m_30_mpa` | m | 0.1288 | 0.06 | 2.147 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V2-WIDE-STRIP | `half_wave_over_mode_width_30_mpa` | 1 | 0.8052 | 0.4 | 2.013 | `RECORDED_DISCREPANCY` | does not match the published value |
| SS-V3-WIDE-STRIP | `half_wave_m_5_mpa` | m | 0.09165 | 0.0375 | 2.444 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V3-WIDE-STRIP | `half_wave_over_mode_width_5_mpa` | 1 | 0.7969 | 0.3571 | 2.231 | `RECORDED_DISCREPANCY` | does not match the published value |
| SS-V3-WIDE-STRIP | `half_wave_m_15_mpa` | m | 0.06887 | 0.0375 | 1.837 | `INDICATIVE_ASSUMED_INPUTS` | indicative: some inputs were assumed |
| SS-V3-WIDE-STRIP | `half_wave_over_mode_width_15_mpa` | 1 | 0.8102 | 0.3571 | 2.269 | `RECORDED_DISCREPANCY` | does not match the published value |
| SS-V14 | `aluminium_foil_factor` | 1 | - | 15 | - | `REFERENCE_ONLY_INPUTS_NOT_RECORDED` | published value only; inputs not recorded |
| SS-V14 | `copper_foil_factor_low` | 1 | - | 7 | - | `REFERENCE_ONLY_INPUTS_NOT_RECORDED` | published value only; inputs not recorded |
| SS-V14 | `copper_foil_factor_high` | 1 | - | 10 | - | `REFERENCE_ONLY_INPUTS_NOT_RECORDED` | published value only; inputs not recorded |
| BT-G13-SPEED-EFFECT | `load_ratio_10_to_40_m_s` | 1 | - | 40 | - | `REFERENCE_ONLY_INPUTS_NOT_RECORDED` | published value only; inputs not recorded |

Cases not encoded, with the reason:

- BT-V4: film ratio encoded as BT-V4-FILM; load and slip curves need digitising and a friction distribution through the bite.
- BT-V9: the published rows give forward slip without load, flow stress or tension values, so the friction identification of BT-G6 (force required) cannot give a friction per row.
- SS-V1: geometry and temperatures are in the study; the bifurcation force is not, so there is nothing to compare.
- SS-V4: needs the stress profile of the paper.
- SS-V5: needs the roll profiles of the paper.
- SS-V11: already encoded: physicroll/literature.py, tests/test_literature.py (cross-reference only).
- A2-LOCAL-SOURCES: no published case of a film or flow-stress band exists (gap study, I2).
- SS-V15: polyester troughs and wrinkles against taper and misalignment [SS-S54 EX]: critical values not quoted in the reports.
- SS-S14-TABLE: no wave height or table measurement with its stress profile is in the reports (dead load on a table, SPEC19 package 7).
- BT-V5: needs a model of a later phase or data not in the repository.
- BT-V6: needs a model of a later phase or data not in the repository.
- BT-V7: needs a model of a later phase or data not in the repository.
- BT-V8: needs a model of a later phase or data not in the repository.
- BT-V10: needs a model of a later phase or data not in the repository.
- BT-V11: needs a model of a later phase or data not in the repository.
- BT-V12: needs a model of a later phase or data not in the repository.
- BT-V13: needs a model of a later phase or data not in the repository.
- BT-V14: needs a model of a later phase or data not in the repository.
- BT-V15: needs a model of a later phase or data not in the repository.
- BT-V16: needs a model of a later phase or data not in the repository.
- BT-V17: needs a model of a later phase or data not in the repository.
- SS-V6: needs a model of a later phase or data not in the repository.
- SS-V7: needs a model of a later phase or data not in the repository.
- SS-V9: needs a model of a later phase or data not in the repository.
- SS-V10: needs a model of a later phase or data not in the repository.
- SS-V12: needs a model of a later phase or data not in the repository.
- SS-V13: needs a model of a later phase or data not in the repository.
- SS-V16: needs a model of a later phase or data not in the repository.
- SS-V17: needs a model of a later phase or data not in the repository.
- SS-V18: needs a model of a later phase or data not in the repository.
- SS-V19: needs a model of a later phase or data not in the repository.
<!-- END GENERATED BLOCK: discrepancies -->

## 6. What is not modelled at all

Gaps of the gap study (section 5 there) still open after Phase 0, Phase 1 and the Phase 2
packages done so far. Checked against section 11 (implementation status) of the gap study by
`tests/test_limitations_register.py`: every gap is here, either as not built or as built in part.

### 6.1 Not built

| gap | what is not modelled | phase |
|---|---|---|
| A7 | Barrel ends, necks, backup-roll contact, axial mechanical coupling of the roll, the expansion factor. | 3 |
| B5 | Particles and pinholes. | 3 |
| B6 | Elastic data and yield for the strip's elastic zones. | 3 |
| B7 | Recovery of the foil in the coil after rolling. | 3 |
| C3 | Chatter beyond the linear screen: roll-gap damping from a dynamic model, film dynamics, limit cycles. | 3 |
| C5 | Torsional self-excitation and drive loops. | 3 |
| C6 | Eccentricity compensation and heat-induced run-out; behaviour at closed gap. | 3 |
| G1 | The roll stack: deflection, roll-to-roll contact, bending, tilt, shifting, ground camber. | 3 |
| G2 | The closed-gap (roll-kiss) shape path for foil. | 3 |
| G7 | Thermal camber at the strip edge and edge actuators. | 3 |
| G14 | Downstream steps: slitting, separating, annealing. | 3 |
| G15 | Edge drop. | 3 |
| BT-G2 | The closed-gap load path across the width. | 3 |
| BT-G9 | Roughness transfer and asperity flattening (imprint, lay, grinding marks). | 3 |
| BT-G10 | Thick-film surface effects: oil pits, hydropitting. | 3 |
| BT-G11 | Boundary film, additives, transfer layer, pick-up, fines. | 3 |
| BT-G14 | Doubled (pack) rolling. | 3 |
| BT-G15 | Elastic strip zones, recovery, tangential roll displacement. | 3 |
| BT-G16 | Hardening, rate and temperature inside the foil roll gap. | 3 |

### 6.2 Built in part; what is still open

| gap | what is still not modelled |
|---|---|
| A1 | A heat balance across the width with the local friction and plastic heat; the target-curve offset. |
| A2 | A measured inlet temperature across the width; the return of the local force and heat to the roll temperature; a published case to compare with. |
| A3 | The full interface: asperity conduction, calibration, a partition resolved across the width. |
| A4 | Feedback of the surface cycle to the roll temperature, stripes and shape; axial conduction in the layer; backup contact, wipers, carry-over. |
| A5 | Re-reading the spray source; flow scaling of the coefficient, a jet-zone entry and a tapered fan; the basis question. |
| A6 | The plant's step-test protocol; a measured coupling and inlet weight; the per-revolution layer in the test. |
| A8 | Creep of the hoop stress in the coil, recovery of the foil, the strip temperature loss between roll gap and coil, a measured gap between laps. |
| A9 | A pressure law that carries an oil from inlet to roll-gap pressure; limiting shear stress data. |
| A10 | An oil-mist or vapour model; a coil temperature model. |
| B1 | Flow-stress data at rolling rates; the net of rate and temperature at rolling conditions. |
| B2 | Parameter sets per alloy group; a recovery term. |
| B3 | Alloy-group parameters inside a hardening law. |
| B4 | An anisotropic yield law in the roll gap. |
| C1 | A closed-gap load path; decoupling, adaptive or feed-forward control; the plant's controller; reels and run-out. |
| C2 | The plant's tension regulator; reel friction, binding and ovality harmonics; tension dynamics inside the chatter model. |
| C4 | The amplitude of grinder marks on foil rolls; marks as a forced-response and wear problem. |
| C8 | Phase tracking of a ripple through trimming and splicing; the gauge sensor in the chain; each pass's own loop settings. |
| C7 | The accelerometer position and detection lead time; gauge filters beyond a spot and a lag. |
| G3 | Lateral metal flow and a strip-element model across the width; a non-uniform entry profile; finite spans; the roll stack and closed gap; which lateral hold at the roll gap is right. |
| G4 | Interaction of several modes; lateral stress and shear; the path from mill tension to none; a finite sample; a measured wave height, table index or stress profile to compare with. |
| G5 | The plant's own flatness controller; bending, tilt and vendor rules; feed-forward; shapemeter dynamics and temperature compensation. |
| G6 | A computed strip temperature; a vendor's temperature compensation. |
| G8 | Published roll time constants to compare the model's own with. |
| G9 | A measured radial stack law for oily aluminium foil; axial stress; a spool model; V-buckle and telescoping margins; creep in the coil. |
| G10 | A nip film formula; side leakage and roughness venting; a measured traction coefficient. |
| G11 | A lateral stress from roller deflection; moment transfer, slack edge and the traction limit; a baggy lane as a source of troughs (I13); a foil-specific correction. |
| G12 | An onset condition for tension lines; air film and winding model. |
| G13 | Roll-bending modulation of the barrel position; wear growth. |
| G16 | The other strip-shape benchmark cases; an uncertainty statement for the chain. |
| BT-G1 | The stretching equations inside the contact; validation on a measured foil pass. |
| BT-G3 | The inlet analysis and asperity crushing in the roll gap. |
| BT-G4 | The full roll-gap model by default; a measured inlet weight; the return to the roll temperature. |
| BT-G5 | The shear cap in the sheet and experimental foil models; friction varying through the roll gap. |
| BT-G6 | A friction distribution through the roll gap; the published slip table without loads. |
| BT-G7 | The film formula itself and the friction closure behind it. |
| BT-G8 | The film-collapse test. |
| BT-G12 | The inlet meniscus position; lateral spreading, carry-over and wipers. |
| BT-G13 | A closed-gap load path; a speed slope of friction checked on a mill; the BT-V4 curves. |
| BT-G17 | Two benchmark cases not encoded; the half-space model the main foil discrepancy calls for as the default. |

## 7. How this register is kept

- Every change that adds a reduced model, an exception, an analyst choice or a flag adds its row
  here in the same change; a flag also gets its line in `FLAG_REGISTER` of
  `physicroll/limitations.py`, and a benchmark is re-run with
  `python -m physicroll.limitations --write docs/limitations.md`.
- `tests/test_limitations_register.py` fails when the generated blocks differ from the code,
  when a flag is missing from the flag index or mapped to a row that does not exist, when a row
  id is used twice, when a benchmark row outside the agreement band is missing from part 5, when
  a constant found by the analyst-choice search is not named in part 4, when the gaps of part 6
  do not match the gap study, or when the prose reads as a finding.
- A statement moved here keeps the meaning it has in its source. Where two sources disagree, the
  disagreement is recorded, not settled here.

## 8. Flag index

Every flag of the result, with its plain sentence and the register row it belongs to;
"informational" marks a flag that only says which model or section was used.

<!-- BEGIN GENERATED BLOCK: flag-index (python -m physicroll.limitations --write docs/limitations.md; do not edit by hand) -->
| flag | what it says | register row |
|---|---|---|
| `AGC_CHATTER_INTERACTION_DEPENDS_ON_LOOP_ROLL_OFF` | The effect of gauge control on chatter depends on a simple control-loop model. | L-DYN-05 |
| `AIR_CASES_BRACKET_THE_NIP_EFFECT` | How much air the ironing roll squeezes out is not known; the page shows the coil with no air and with the full air film as the two limits. | L-COIL-12 |
| `BITE_DERIVATION_FAILED_CHATTER_NOT_ASSESSABLE` | No roll-gap result, so the chatter checks could not be made. | L-BITE-13, L-DATA-10 |
| `BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL` | The roll-gap numbers come from the experimental foil model. | L-BITE-02 |
| `BITE_FROM_REDUCED_HALF_SPACE_MODEL` | The roll-gap numbers come from the half-space foil model, a reduced form of a published model that has not been checked on a mill. | L-BITE-05 |
| `BITE_MODEL_AUTO` | The tool chose the roll-gap model by gauge (sheet model, foil model where it fails). | informational |
| `BITE_MODEL_AUTO_HALF_SPACE` | The tool used the sheet roll-gap model and the half-space foil model where the sheet model stops. | L-BITE-05 |
| `BITE_MODEL_HALF_SPACE` | The half-space foil roll-gap model (a reduced form of a published model) was chosen for every pass. | L-BITE-05 |
| `BITE_MODEL_MATTRESS` | The experimental foil roll-gap model was chosen for every pass. | L-BITE-02 |
| `BITE_RESPONSE_SUPPLIED` | The roll-gap values were supplied from outside. | informational |
| `BITE_TEMPERATURE_NOT_AVAILABLE_REFERENCE_USED` | Without rolling-oil data the bite temperature is unknown; the reference temperature of your factor was used. | L-MAT-01 |
| `BUCKLING_FE_IN_MILL_STATE_DIFFERS_FROM_SINE_MODE` | For at least one band the wavelength search and the standard rule disagree on whether the strip waves in the mill; the shortlist uses the standard rule. | L-SHAPE-16 |
| `BUCKLING_FE_RELEASED_STATE_DIFFERS_FROM_SINE_MODE` | For at least one band, or for the whole sheet, the wavelength search and the standard rule disagree on whether the strip waves after the tension is released; the shortlist uses the standard rule. | L-SHAPE-16 |
| `BUCKLING_FE_REPORTED_BESIDE_SINE_MODE` | Beside the standard band states, the page shows at which band height the strip would start to wave and how long the waves would be, from a search over wavelengths on the modelled flatness; the standard states are the ones the shortlist uses. | L-SHAPE-16 |
| `CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE` | The roll force the model finds for this pass lies outside the range reported for battery-foil passes, so its roll-gap results are not credible and are left out of the scoring. | L-BITE-14 |
| `CASE_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE` | A pass lies outside the published range for the chosen product. | L-DATA-05 |
| `CASE_STRENGTH_BELOW_STANDARD_MINIMUM_FOR_GAUGE` | The strength entered is below the published minimum for this gauge. | L-DATA-05 |
| `CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT` | The model's chatter frequency is above the limit where its strip-span model holds, so the chatter result is not reliable here. | L-DYN-03 |
| `CIRCULAR_FLATTENING_ASSUMED_NOT_VALIDATED` | The sheet roll-gap model assumes the rolls flatten into a circle, which is not validated. | L-BITE-01 |
| `CIRCUMFERENTIAL_MEAN_COEFFICIENT_BIASED` | With the sprays on one arc the averaged cooling of the roll model differs by more than 5 % from the cooling the surface really gets. | L-HEAT-07 |
| `CLOSED_GAP_ROLLING_LIKELY_ROLL_KISSING_NOT_MODELLED` | At this gauge the work rolls may touch beside the strip (closed-gap rolling), which the tool does not model; it assumes an open gap. | L-BITE-15 |
| `COIL_COOLING_STRESS_REACHES_YIELD` | In this estimate a hotter lane would be stretched to yield when the coil cools. | L-COIL-07 |
| `COIL_ON_SPAN_RESONANCE_CROSSED_DURING_COIL` | During the coil the once-per-revolution frequency meets the bounce of the coil on the strip span, and that bounce is lightly damped. | L-DYN-12 |
| `COIL_WINDING_MODEL_REPORTED_BESIDE_LINEAR_CRITERION` | Beside the standard coil check, the page shows the strip wound into the coil lane by lane with the stack stiffness you entered; the shortlist uses the standard check. | L-COIL-11 |
| `COIL_WINDING_TEMPERATURE_TAKEN_AS_STRIP_EXIT_UPPER_BOUND` | The coil temperature starts from the modelled strip temperature leaving the roll gap, which is an upper bound: the strip cools a little before it reaches the coil. | L-COIL-07 |
| `COLD_START_BY_FRICTION_CONTINUATION` | The half-space model reached the entered friction from a lower friction, because the simpler foil model could not start at it. | L-BITE-11 |
| `COMPLIANCE_ONLY_LEVEL_NOT_DEFINED_CHANGE_REACHES_GAUGE` | One comparison level of the flatness model is not defined for this soft strip. | L-SHAPE-02 |
| `CONTACT_END_ZONES_ADDED_TO_SPEC_EQUATIONS` | The foil roll-gap model adds contact end zones to its published equations. | L-BITE-02 |
| `CONTACT_RADIUS_RATIO_CLAMPED_TO_ONE` | The foil model's contact length is shorter than the undeformed roll would give; the flattening figure was set to its lower limit. | L-BITE-02 |
| `CONTROL_INCREASES_RESIDUAL` | In this simulation the flatness error at the end is larger than at the start. | L-LOOP-05 |
| `CONTROL_MADE_BAND` | In this simulation the valve switching itself makes a band in at least one zone for a while. | L-LOOP-05 |
| `CONTROL_ZONE_AT_LIMIT` | In this simulation at least one spray zone ends fully open or fully closed. | L-LOOP-05 |
| `DEAD_LOAD_KEEPS_REPORTED_BAND_FLAT_ON_TABLE` | A band the standard rule calls visible after release would lie flat on an inspection table under its own weight in this rough estimate; the length difference is still there, and the shortlist keeps the standard state. | L-SHAPE-18 |
| `DERIVED_BY_EXPERIMENTAL_MATTRESS_MODEL` | A roll-gap result was computed by the experimental foil model. | L-BITE-02 |
| `DERIVED_BY_HALF_SPACE_FOIL_MODEL` | A roll-gap result was computed by the half-space foil model. | L-BITE-05 |
| `DOUBLED_FINAL_PASS_NOT_MODELLED` | The thinnest pass is rolled doubled (two sheets), but the tool models one sheet. | L-BITE-16 |
| `DUPLICATE_BAND_POSITIONS_MERGED` | Some band positions were closer than 1 mm and were merged into one band. | L-DATA-11 |
| `ENTRAINED_AIR_FILM_EXCEEDS_STRIP_THICKNESS` | The air film the strip can carry into the coil (an upper estimate) is thicker than the strip itself at the outer wraps. | L-COIL-10 |
| `ENTRY_RIPPLE_NEAR_STAND_RESONANCE` | A ripple carried into a later pass arrives near that pass's stand resonance. | L-DYN-13 |
| `ENTRY_RIPPLE_NEAR_TENSION_LOOP_PEAK` | A ripple carried into a later pass arrives where the gauge loop amplifies most. | L-DYN-13 |
| `EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN` | The exit gauge is below 20 µm, outside the range where the foil roll-gap model was probed; its numbers are unvalidated. | L-BITE-12 |
| `EXIT_GAUGE_BELOW_BITE_MODEL_FLOOR` | The exit gauge is below 8 µm, where no roll-gap model runs. | L-BITE-13 |
| `EXPERIMENTAL_MATTRESS_FOIL_MODEL` | At this foil gauge the roll gap comes from an experimental model with no benchmark; its numbers are order of magnitude only. | L-BITE-02 |
| `FINAL_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE` | The final pass lies outside the published range for the chosen product. | L-DATA-05 |
| `FLATNESS_LOOP_NOT_SETTLED` | In this simulation the valves keep switching to the end of the run: the loop does not settle with these settings. | L-LOOP-05 |
| `FLATNESS_LOOP_ON_COARSE_GRID` | The simulated loop ran on a roll grid coarse against the flatness zones. | L-LOOP-06 |
| `FLATNESS_LOOP_SIMULATED` | The page shows what a flatness control loop with the settings you entered would do on this model, with the tool's own control rule; it is not what your controller did and changes no score. | L-LOOP-01 |
| `FLATNESS_LOOP_TRIMMING_LIMIT_CYCLE` | In this simulation the valves keep stepping by small amounts while the zone error stays small. | L-LOOP-05 |
| `FLOW_STRESS_FROM_HARDENING_LAW` | The flow stresses come from the hardening law, not from the values typed in. | L-MAT-04 |
| `FLOW_STRESS_RATE_TEMPERATURE_FACTOR_APPLIED` | The flow stress of every pass was multiplied by your strain-rate and temperature factor; the measured rate sensitivity stops five decades below rolling rates. | L-MAT-01 |
| `FOIL_GAUGE_LOOP_SIMULATED` | The gauge loop by entry tension and speed was simulated; it is the tool's own loop, not the plant's controller. | L-DYN-11 |
| `FOOTPRINT_PROFILE_STAND_IN` | Each nozzle cools more in the middle of its fan than at its edges; the shape used is a stand-in, because no measured fan profile is published. | L-HEAT-13 |
| `FOOTPRINT_WIDER_THAN_VENDOR_PRACTICE` | The fans overlap more than nozzle makers recommend (1.1 to 1.5 nozzle pitches); a blocked nozzle is smoothed more than on such a header. | L-HEAT-14 |
| `FORCE_SENSITIVITY_DERIVED_NOT_FROM_SUPPLIED_BITE` | Some sensitivities come from the tool's roll-gap model, not from the supplied values. | L-BITE-18 |
| `FORWARD_SLIP_INSENSITIVE_TO_FRICTION_IN_THIS_REGIME` | With a no-slip zone the forward slip hardly depends on friction; the force is the better indicator here. | L-FRIC-04 |
| `FORWARD_SLIP_LARGE_CONSTANT_FRICTION_NO_SLIP_ZONE_MODEL` | The foil roll-gap model gives a large forward slip, as a model with one constant friction value does; mill trials found less. | L-BITE-03 |
| `FORWARD_SLIP_OUTSIDE_KINEMATICS_DOMAIN_ZERO_USED_IN_KINEMATICS` | The forward slip is too large for the roll-mark spacings, so zero is used there. | L-BITE-04 |
| `FORWARD_SLIP_UNKNOWN_ZERO_USED_IN_KINEMATICS` | No roll-gap result: the forward slip is unknown and zero is used for roll-mark spacings. | L-BITE-04 |
| `FOUNDATION_MODULUS_FROM_MEMORY_FORMULA` | A stiffness inside the foil roll-gap model comes from an unchecked formula. | L-BITE-02 |
| `FRICTION_FROM_PLACEHOLDER_CLOSURE` | The friction used comes from the placeholder law, not from your value. | L-FRIC-01 |
| `FRICTION_IDENTIFIED_FROM_ENTERED_RECORDS` | A friction value was worked out from the roll force (and slip or torque where entered) of your pass records; it is shown only and used nowhere. | L-FRIC-04 |
| `FRICTION_STRIPE_LINEAR_FEEDBACK_NOT_SATURATED` | A friction stripe you gave would buckle the strip in the mill; the rough linear estimate then overstates it. | L-SHAPE-12 |
| `FRICTION_STRIPE_SCREEN_APPLIED` | The page shows how much a local difference in friction across the width would mark the strip, as a rough linear estimate; it does not change the scores. | L-SHAPE-12 |
| `GAUGE_KEEPS_LESS_THAN_HALF_OF_OBSERVED_MARK` | The thickness gauge keeps less than half of at least one mark spacing you saw. | L-MEAS-04 |
| `GAUGE_NOT_DETECTED_BUT_MARK_NOT_RESOLVABLE` | You saw no gauge variation, but the gauge could not show these marks anyway, so that answer tells little; the scores were not changed. | L-MEAS-05 |
| `GAUGE_SET_BY_STRIP_NOT_BY_GAP` | A change of the roll gap setting moves the gauge by less than a tenth of itself: the strip, not the gap, sets the gauge here. | L-DYN-09 |
| `GAUGE_TRANSFER_APPLIED` | The page shows about how much of each mark the thickness gauge you described keeps (spot size and response time only). | L-MEAS-04 |
| `GRINDER_CHATTER_NOT_EXCLUDED_NO_GRINDER_DATA` | The mark pitch fits no simple count of marks around the work roll, but it would fit a pattern left by a vibrating grinder; without the grinder's speeds that cannot be ruled out. | L-GRIND-02 |
| `HALF_SPACE_REGIME_CONVENTIONAL` | The half-space model finds the strip sliding over the whole contact (sheet range). | informational |
| `HALF_SPACE_REGIME_FOIL` | The half-space model finds a zone where strip and roll move together (foil range). | informational |
| `HEAT_PARTITION_INPUTS_INCONSISTENT` | Two inputs for how the roll-gap heat is shared disagree. | L-HEAT-05 |
| `HEAT_SHARE_OUTSIDE_0_1_TEMPERATURE_DIFFERENCE_DOMINATES` | The computed heat share lies outside 0 to 1: the temperature difference between strip and roll moves more heat than the roll gap makes. | L-HEAT-04 |
| `HITCHCOCK_RATIO_BEYOND_REVIEWED_ENVELOPE` | The rolls flatten more than the reviewed range of the sheet roll-gap model. | L-BITE-01 |
| `HYPOTHESIS_EVALUATION_FAILED` | One or more causes could not be evaluated and are shown as "cannot tell". | L-DATA-10 |
| `IDENTIFIED_FRICTION_DIFFERS_FROM_CASE_FRICTION` | The friction worked out from your pass records differs by more than 20 % from the friction entered for the pass. | L-FRIC-04 |
| `KERNEL_CLOSURES_DISAGREE_IN_SIGN` | Depending on how the strip is assumed to be held at the roll gap, the second estimate changes sign: the tension effect is not known even in direction for one of the assumptions. | L-SHAPE-19 |
| `KERNEL_FEEDBACK_BELOW_HALF_OF_POINTWISE` | The second estimate gives less than half the tension effect the standard level uses, so the band would be larger than shown by the standard level. | L-SHAPE-19 |
| `KERNEL_STEADY_STATE_NOT_DEFINED` | For at least one assumption about how the strip is held at the roll gap the second estimate has no steady answer. | L-SHAPE-19 |
| `KISS_STIFFNESS_NOT_MODELLED_ZERO_USED` | At this gauge the work rolls may touch outside the strip; that contact is not modelled and was taken as zero. | L-DYN-09 |
| `LENGTHWISE_MODEL_BAND_NOT_UNDER_GAUGE` | None of the modelled lengthwise bands passes under the thickness gauge. | L-MEAS-04 |
| `LIGHT_REDUCTION_ELASTIC_STRIP_ZONES_NOT_MODELLED` | The reduction is light (below 10 %), where the short elastic zones the model leaves out matter more. | L-BITE-09 |
| `LOCAL_FRICTION_CHANGE_ABOVE_20_PERCENT_LINEAR_SOURCE_INDICATIVE` | Somewhere across the width the friction changes by more than a fifth; the straight-line estimate built on it is then rough. | L-SHAPE-14 |
| `LOCAL_FRICTION_FROM_PLACEHOLDER_CLOSURE_SLOPE` | The friction change across the width uses a friction law whose slope is a rough stand-in, not fitted to measurements. | L-FRIC-01, L-SHAPE-13 |
| `LOCAL_NET_INCOMPLETE_TERM_MISSING` | One part of the sum could not be worked out (for example no softening of the metal with temperature was given), so the sum is incomplete. | L-SHAPE-14 |
| `LOCAL_NET_SIGN_DEPENDS_ON_INLET_WEIGHT` | Whether the sum makes the strip loose or tight depends on how much of the roll temperature reaches the oil, which nobody has measured. | L-SHAPE-14 |
| `LOCAL_SOURCES_COMPUTED` | Besides the roll growth, the page shows what a hot roll stripe does through the oil film, the softer metal and the strip temperature, each on its own and summed; it changes no score. | L-SHAPE-14 |
| `LOCAL_SOURCES_REVERSE_A_BAND` | At a band of the roll growth, the oil film and metal parts cancel it or turn it round in this rough estimate. | L-SHAPE-14 |
| `LOCAL_SOURCES_SUMMED_ON_LINEAR_PROFILE_SATURATION_NOT_APPLIED` | The parts are added on the straight-line flatness profile; a band that buckles is not capped there. | L-SHAPE-14 |
| `LOCAL_STATE_COMPUTED` | The oil film, friction, metal strength and strip temperature across the width were worked out as differences from a healthy spray header; they change no other result. | L-SHAPE-13 |
| `LOCAL_STATE_FROM_CIRCUMFERENTIAL_MEAN_SURFACE_TEMPERATURE` | The roll surface temperature used for the oil and the strip is the average around the roll, not the value just before the roll gap. | L-SHAPE-13 |
| `LOOP_AMPLIFIES_COIL_FREQUENCY` | The simulated gauge loop makes a once-per-revolution disturbance of a coil larger, not smaller. | L-DYN-11 |
| `LOW_ORDER_FLATNESS_LEFT_TO_BENDING_NOT_MODELLED` | The smooth overall shape (mean, slope, curve) is left to bending and tilt, which the tool does not model. | L-LOOP-02 |
| `LUDERS_STRAIN_NOT_SUPPLIED_ZERO_USED_IN_WINDOWS` | No yield-point strain was given, so zero is used in the bending check. | L-MAT-09 |
| `MATERIAL_NOT_STATED_LITERATURE_PROPOSAL_SHOWN` | Alloy and temper are a suggestion from the literature, not the plant's statement. | L-MAT-07 |
| `MATERIAL_SELECTION_FAILED` | The alloy and temper suggestion could not be built. | L-DATA-10 |
| `MATTRESS_REGIME_FOIL` | The pass is in the foil range where the experimental roll-gap model is used. | L-BITE-02 |
| `MEASURED_SLIP_NOT_REPRODUCED_BY_CONSTANT_FRICTION_BITE` | The entered forward slip does not fit the roll-gap model at the friction that matches the force: a model with one constant friction value over-estimates foil slip, and mill trials found friction varying through the bite. | L-FRIC-03 |
| `MEASUREMENT_SECTION_FAILED` | The shapemeter part of the page could not be worked out. | L-DATA-10 |
| `MODELLED_EXIT_TEMPERATURE_ABOVE_BATTERY_COIL_LIMIT` | The modelled strip exit temperature is above a published battery-foil coil limit. | L-COIL-07 |
| `MODEL_BAND_BELOW_SHAPEMETER_THRESHOLD` | A modelled band is narrower or weaker than a zone can show: the shapemeter would probably not show it. | L-MEAS-01 |
| `MODEL_STEADY_THERMAL_STRIPES_PRESENT` | The roll temperature model finds steady hot stripes on the work roll. | informational |
| `NEGATIVE_LATE_HARDENING_SLOPE_WORK_SOFTENING` | The hardening law softens at large strain (a negative late slope), as reported for purified Al-Fe and high-purity grades beyond 80 % reduction. | L-MAT-05 |
| `NEXT_MEASUREMENTS_FAILED` | The list of next checks could not be built. | L-DATA-10 |
| `NO_SLIP_ZONE_CREEP_ABOVE_ONE_PERCENT` | In the half-space model the strip creeps a little where it should move with the roll; the forward slip is less exact than usual. | L-BITE-09 |
| `OIL_SUPPLY_BELOW_SMOOTH_FILM` | Under at least one working nozzle less oil arrives than the film in the roll gap would carry. | L-FRIC-09 |
| `OIL_SUPPLY_TEMPERATURE_ABOVE_SITE_CAP` | An oil temperature you gave reaches the site limit you gave. | L-HEAT-11 |
| `OIL_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT` | An oil temperature you gave reaches the flash point of the oil. | L-HEAT-11 |
| `ONE_SIDED_TENSION_DIFFERENCE_AT_ZERO_TENSION` | With zero tension the effect of tension on the roll force was taken from one side only. | L-BITE-17 |
| `OPERATING_POINT_LINEARLY_UNSTABLE` | In the model the stand vibrates on its own at the operating speed (chatter). | L-DYN-01 |
| `OPERATING_SPEED_OUTSIDE_SCANNED_RANGE` | The operating speed lies outside the speed range the chatter scan covers. | L-DYN-06 |
| `PEAK_PRESSURE_ABOVE_16_PLANE_STRAIN_YIELD` | The highest roll pressure is above what published foil solutions show. | L-BITE-10 |
| `PLACEHOLDER_FRICTION_CLOSURE_NOT_FITTED` | The friction-speed law is a placeholder and not fitted. | L-FRIC-01 |
| `RADIAL_STACK_LAW_IS_AN_INPUT_NO_ALUMINIUM_DATA_FOUND` | How the coil stack compresses was entered; no measured value for oily aluminium foil is published, and the winding result depends on it. | L-COIL-09 |
| `RATE_SENSITIVITY_EXTRAPOLATED_BEYOND_MEASURED_RATES` | The rate sensitivity was measured far below rolling strain rates and is used beyond that range. | L-MAT-01 |
| `RATE_TEMPERATURE_FACTOR_REJECTED` | For at least one pass the rate and temperature factor fell outside 0.2 to 5 and was not used. | L-MAT-02 |
| `REDUCED_HALF_SPACE_FOIL_MODEL` | The half-space foil model leaves out the stretching of strip and roll surface inside the contact. | L-BITE-05 |
| `REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN` | The pass reduces the gauge by more than half, outside the reviewed range of the roll-gap model. | L-BITE-12 |
| `REEL_RUNOUT_RIPPLE_COMPUTED` | The tension and gauge ripple from coil run-out were computed for the entered reels. | L-DYN-12 |
| `REGIME_CHANGE_WITHIN_FINITE_DIFFERENCE_STENCIL` | A small change of the pass moves it across the sheet / foil boundary of the roll-gap model, so its sensitivities straddle the two. | L-BITE-17 |
| `RELATIVE_RIPPLE_GROWS_FROM_PASS_TO_PASS` | A gauge ripple carried from one pass to the next grows relative to the gauge. | L-DYN-13 |
| `RIGID_BOUND_NOT_DEFINED_BUMP_REACHES_GAUGE` | One comparison level of the flatness model is not defined because the roll bump reaches the gauge. | L-SHAPE-02 |
| `ROLL_ENTRY_TEMPERATURE_ASSUMED_COOLANT_OR_OIL` | The work-roll surface temperature entering the roll gap was taken as the coolant or oil temperature. | L-HEAT-04 |
| `ROLL_ENTRY_TEMPERATURE_FROM_SURFACE_CYCLE` | The roll surface temperature entering the roll gap came from the surface cycle. | informational |
| `ROLL_GROUND_PROFILE_BAND_ABOVE_THRESHOLD` | The roll profile you gave would make a band above the reporting level. | L-GRIND-03 |
| `ROLL_GROUND_PROFILE_SUPPLIED` | The page puts the roll profile you gave through the same model as a heat stripe on the roll. | L-GRIND-03 |
| `ROLL_PROFILE_BANDS_DEPEND_ON_DETREND_ORDER` | The bands of the measured roll profile change with how the smooth crown is taken out. | L-GRIND-04 |
| `ROLL_PROFILE_GRID_TOO_COARSE` | The points of the measured roll profile are too far apart to show a narrow mark; a missing band there does not mean the roll has none. | L-GRIND-03 |
| `ROLL_SURFACE_CYCLE_COMPUTED` | The roll surface temperature within one revolution was computed from the angular layout of bite and sprays you entered; it changes no other result. | L-HEAT-07 |
| `SCREENS_SECTION_FAILED` | The simple screens (spray coverage, oil film) could not be computed. | L-DATA-10 |
| `SENSITIVITY_STEP_NOT_CONVERGED` | The roll-gap sensitivities change with the step used to compute them. | L-BITE-17 |
| `SHAPEMETER_DOES_NOT_COVER_STRIP` | The shapemeter zones you described do not cover the whole strip width. | L-MEAS-01 |
| `SHAPEMETER_NEIGHBOUR_SPREADING_APPLIED` | Part of each zone reading is shared with its neighbours, as you set it. | L-MEAS-02 |
| `SHAPEMETER_OPERATOR_APPLIED` | The page shows what each zone of the shapemeter you described would show for the modelled bands: zone averages of a model, not a forecast of the screen. | L-MEAS-01 |
| `SHAPEMETER_TEMPERATURE_COMPENSATED` | Your shapemeter corrects for strip temperature, so it would show the flatness without the temperature part. | L-MEAS-03 |
| `SHAPE_INPUTS_SUPPLIED` | Strip-shape inputs were supplied from a plant model. | informational |
| `SHEAR_CAP_ACTIVE` | Friction reached the shear strength of the metal somewhere in the contact; the model caps it there. | L-BITE-11 |
| `SIGNATURES_SECTION_FAILED` | The mark-spacing checks could not be computed. | L-DATA-10 |
| `SPAN_SHORTER_THAN_WIDTH_BEAM_MODEL_INDICATIVE` | The span is shorter than the strip is wide, so the beam model of the lateral stress from the roller alignment is indicative only. | L-COIL-13 |
| `SPAN_TENSION_STIFFENING_NOT_NEGLIGIBLE` | In the lateral stress from the roller alignment the span is long and tense enough that tension stiffening, which the beam model leaves out, is not small. | L-COIL-13 |
| `SPEED_EFFECT_FROM_PLACEHOLDER_FRICTION_SLOPE` | The speed effect on gauge comes from a placeholder friction law that is not fitted to any mill. | L-DYN-10 |
| `SPRAY_COEFFICIENT_BASIS_NOT_COMPARABLE` | The spray cooling value is an average around the roll; the published value is an average over the sprayed patch of one cooling zone, so the two are not comparable. | L-HEAT-03 |
| `SPRAY_FLOW_EXPONENT_APPLIED` | The cooling of a nozzle was taken to fall less than its flow (flow to a power below one), as published for water sprays and one oil simulation. | L-HEAT-15 |
| `STEADY_STATE_NOT_CONVERGED` | The roll temperature model did not fully settle. | L-HEAT-01 |
| `STRAIN_RATE_FROM_UNDEFORMED_ARC` | The strain rate of each pass uses the contact length of the undeformed roll. | L-MAT-01 |
| `STRIP_EXIT_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT` | A modelled strip exit temperature reaches the flash point of the oil you gave. | L-HEAT-11 |
| `STRIP_EXPANSION_COEFFICIENT_FROM_MEMORY_DEFAULT` | The heat expansion of aluminium is a textbook value, not checked against your alloy. | L-SHAPE-10 |
| `STRIP_HEAT_FRACTION_COMPUTED_FROM_INTERFACE_MODEL` | The strip's share of the roll-gap heat was computed by an interface model instead of the share you entered. | L-HEAT-04 |
| `STRIP_MAP_FAILED` | The along-the-strip picture could not be built. | L-DATA-10 |
| `STRIP_NOT_THERMALLY_THIN_LUMPED_MODEL_INDICATIVE` | The strip is too thick for one temperature through its thickness. | L-HEAT-04 |
| `STRIP_TEMPERATURE_CHANGES_A_BAND_STATE` | The strip temperature changes whether a band shows in the mill or after release. | L-SHAPE-10 |
| `STRIP_TEMPERATURE_SCAN_DOES_NOT_COVER_STRIP` | The temperature scan does not reach the whole strip width; the end values are carried to the edges. | L-SHAPE-11 |
| `STRIP_TEMPERATURE_TERM_SUPPLIED_PROFILE` | The strip temperature scan you gave is used to show flatness as measured hot and after cooling; the scan is your input, not worked out by the tool. | L-SHAPE-10 |
| `STRIP_TEMPERATURE_TERM_WITHOUT_MECHANICAL_PROFILE` | There is no modelled flatness for this pass, so only the temperature part is shown. | L-SHAPE-11 |
| `STRIP_THICKNESS_SPRING_NOT_IN_PUBLISHED_MODEL` | The half-space model lets the strip compress a little under the roll; the published model does not. It raises the roll force by a few per cent. | L-BITE-07 |
| `SUPPLIED_BITE_SENSITIVITIES_NOT_VERIFIED` | The roll-gap values were supplied from outside and are not checked by the tool. | L-DATA-03 |
| `SYNTHETIC_INPUTS` | The inputs are synthetic or typical values, not your mill's measured values. | L-DATA-01 |
| `TENSION_TRIM_SATURATES_FOR_ONE_PERCENT_ENTRY_GAUGE` | Correcting a 1 % entry gauge change by tension alone would need more than the allowed tension trim. | L-DYN-11 |
| `THERMAL_CHECK_FAILED` | The process-temperature check could not be computed. | L-DATA-10 |
| `THERMAL_SENSITIVITY_FAILED` | The heat-share sensitivity table could not be computed. | L-DATA-10 |
| `THERMAL_SENSITIVITY_PER_PASS_FAILED` | The per-pass heat-share table could not be computed. | L-DATA-10 |
| `THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN` | The pass is thinner than the range the sheet roll-gap model was reviewed for. | L-BITE-01 |
| `UNSTABLE_LOOP_SETTINGS` | The entered gauge-loop settings are unstable; the loop was not simulated. | L-DYN-11 |
| `USER_SUPPLIED_INPUTS_NOT_VERIFIED` | The values were entered by a person and have not been checked by the tool. | L-DATA-03 |
| `WIDTH_COUPLING_KERNEL_REPORTED` | Beside the standard flatness levels, the page shows a second estimate of how much the strip tension holds a band down, from a model of how the strip is held across the width; the shortlist uses the standard level. | L-SHAPE-19 |
| `WIDTH_SECTION_PARTIAL_FAILURE` | Part of the across-the-width model could not be computed. | L-DATA-10 |
| `WIDTH_SHAPE_CHAIN_NOT_ASSESSABLE_NO_BITE` | Without a roll-gap result the strip-shape part of the width model is not assessed. | L-BITE-13 |
| `WIDTH_THERMAL_NOT_ASSESSABLE_NO_BITE_HEAT` | Without the roll-gap heat the roll temperature model could not run. | L-BITE-13 |
| `WINDING_DISAGREES_WITH_LINEAR_RIDGE_CRITERION` | The lane-by-lane winding and the standard coil check disagree on whether a ridge stretches the strip in the coil; the shortlist uses the standard check. | L-COIL-11 |
| `WINDING_INNER_LAPS_IN_HOOP_COMPRESSION` | In the lane-by-lane winding the inner laps end in compression along their length. | L-COIL-09 |
| `WINDING_LANE_SLACK` | In the lane-by-lane winding at least one lane is wound without tension (a long lane). | L-COIL-11 |
| `WINDING_LANE_YIELDS` | In the lane-by-lane winding at least one lane is stretched beyond yield in the coil. | L-COIL-11 |
| `WINDING_YIELD_VERDICT_DEPENDS_ON_ALLOCATION_POINT` | For at least one lane the lane-by-lane winding says "yields" with one numerical choice and "does not yield" with the other; that lane is not decided. | L-COIL-11 |
| `WOUND_IN_TENSION_CAPPED_AT_YIELD` | With the ironing roll the tension wound into the coil would reach the yield stress; it was capped there. | L-COIL-12 |
| `ZERO_OIL_SUPPLY_UNDER_BLOCKED_NOZZLE_NO_SPREADING_MODEL` | Under a fully blocked nozzle no oil arrives in this estimate; oil that spreads from the neighbours is not counted. | L-FRIC-09 |
| `ZONE_STEP_TEST_EMULATED` | The page shows which response time a test that switches one spray zone would give on this model, with and without the strip temperature and oil film effects, beside the published 20 s; a match does not show what your mill measured. | L-LOOP-07, L-HEAT-09 |
| `ZONE_STRUCTURE_AT_REGIME_BOUNDARY` | The pass sits between the sheet and the foil range; the half-space model used the sheet-type contact and reports the other one beside it. | L-BITE-08 |
<!-- END GENERATED BLOCK: flag-index -->
