# SPEC19 — Phase 2 of the coverage-gap study: width-resolved couplings and loops

Repository `/home/user/PhysicRollModel`, planned against commit `8f10cbe` PLUS everything SPEC17
(Phase 0) and SPEC18 (Phase 1) specify (same scratchpad directory). Read SPEC17 section G and
SPEC18 section G' first: both apply unchanged except for G'' below. Source of every new fact:
`docs/simulation-coverage-gaps.md` (the gap study) and the reports in
`docs/research/band-screening-2026-11/`. Nothing else may be used as a source. Do not commit. No
network. If `research_phase1_equations.md` exists in the scratchpad when a package starts, read
it; nothing in this brief depends on it.

Fifteen work packages, executed one at a time in the order given, each leaving the repository
green. Section 0 holds what the planner measured and found; read it before package 1.

Scratch material of the planner in `scratchpad/s25/` (prototypes: copy, do not import from the
repository; they import the export of `8f10cbe` in `s23/head`; where they differ from this text,
this text holds):

| file | what it is |
|---|---|
| `common.py` | loads a demo case and its committed artifact; builds the thermal object and shape parameters |
| `loop.py`, `loop_run.py`, `loop_sim2.py` | stepping wrapper over `roll_thermal`, zone operator, influence matrix, controller, closed loop |
| `steptest.py` | zone step test and the first-order-plus-dead-time fit |
| `buck.py`, `buck_ss.py`, `buck_foil.py`, `buck_table.py` | buckling finite elements across the width, closed-form checks, SS-V2 / SS-V3 scans, one-term post-buckling, dead load |
| `kernel.py` | width-coupling kernel: three closures, both demos |
| `wind.py`, `wind_lanes.py` | accretion winding model, closed form, lanes with one thicker lane |
| `foilbearing.py` | the foil-bearing constant by integrating its equation |
| `local.py`, `eta.py` | hot-stripe contributions on both demos; strip-to-roll temperature coupling |
| `gauge.py` | foil gauge sensitivities, speed-tension loop, run-out to tension to gauge |
| `g11.py` | span misalignment, taper, roller deflection, coil cooling hand numbers |

---

## G''. Rules that differ from SPEC17 section G and SPEC18 section G'

**G''1. Opt-in models; one evidence rule (replaces nothing, adds to G'1).** Every model of this
block is either computed and reported beside the present value, or selected by a new optional
case key whose absence leaves every existing result value unchanged. No committed scenario is
switched to a new model for a quantity that feeds evidence. There is NO "switch the default"
package: section 0.1 says why neither the buckling model nor the winding model earns it. Exactly
one evidence rule gains a new branch, in package 12, and only when the user supplies the new
input `width_model.span_alignment`; the rule, its weight and the reason are written there.
G6 applies with "additive only" as the allowed classification for every package.

**G''2. Tags.** As SPEC17 G2 and SPEC18 G'2. Formulas re-derived here carry
`[D, re-derived in SPEC19]`; the derivation given in the package goes into the module docstring.
Four formulas the reports quote from memory or without their text are handled as follows, and the
code comments must say so:

| formula in the reports | tag there | what this brief does |
|---|---|---|
| Hakiel winding equation, outer-lap and core conditions | equation restated [SS-S42 EX]; "Hakiel-type, from memory" in gap A8 | re-derived from equilibrium, compatibility and an orthotropic law (package 9); self-check: closed form for an isotropic roll on a rigid core |
| relaxation-radius tension allocation (Cole & Hakiel) | named only [SS-S44 AB, SS-S45 EX] | derived as a strain allocation on a common unstrained circumference (package 10) |
| foil-bearing air film `h = 0.643*R*(6*mu*U/T)^(2/3)` | [SS-S58 EX/AB]; numbers "[D] illustration" | equation re-derived; the constant 0.643 is recomputed by integrating the film equation (package 9); self-check 0.64304 |
| Koiter one-term post-buckling amplitude | named only [SS-S15 EX] | NOT used; a one-mode Rayleigh-Ritz amplitude in a fibre membrane model is derived (package 7); self-check: the I-unit wave formula of QCA-1 |
| shell-buckling wavelength `3.47*sqrt(R*t)` | from memory | already re-derived in SPEC17 package 8; reused unchanged |
| trough / wrinkle generators of Good & Beisel, Shelton | named only [SS-S54 EX, SS-S56 SN] | misalignment and taper derived from beam theory and Mohr's circle (package 12); roller deflection: the smaller model (curvature and edge slope only), because no derivation of its lateral stress could be made that the planner trusts |

**G''3. Status words for section 11 of the gap study** (added to the fixed list): `LOOP_MODEL_OPT_IN`
(a closed-loop simulation that runs on entered controller settings; default unchanged) and
`COMPUTED_BESIDE` (a computed value reported beside the present one; nothing reads it).

**G''4. Time-domain and closed-loop results.** Fixed time step, fixed horizon, no adaptive
stepping, no wall time or iteration-dependent number in a result. Every loop returns a `status`
from a fixed vocabulary given in its package, and a history thinned to at most
`band_width.HISTORY_MAX_POINTS` (300) samples per series. A loop that does not settle is a
result, not an error: it never raises for that reason.

**G''5. Run time is a requirement** (as G'6). Budgets are in section 0.3 and in each package.

**G''6. App invariants.** As SPEC17 G5 and SPEC18 G'4. Every key this brief adds to
`band_diagnosis.OPTION_OPTIONAL` gets its question in the same package. All other new keys sit in
new optional sub-sections (null by default) that are outside the question-forcing lists on
purpose; their questions come in package 15. `band_survey_mills.MACHINES[...]` gains every new
optional key of a section it carries, with `None`, in the package that adds the key (drift guard
of SPEC18 G'4).

**G''7. Demo inputs.** The battery-foil demo (`scenarios/band_diagnosis_battery_foil.json`)
gains `width_model.local_coupling` (package 1), `width_model.flatness_control` (package 4) and
`width_model.zone_step_test` (package 5): they build on the shapemeter SPEC17 package 4 put
there. Every value is synthetic and says so in `provenance` and in a `notes` line. No other
scenario gains a non-null new input. Its artifact changes additively three times (open
decision 7 gives the alternative).

**G''8. Benchmarks** (as G'5: `CASE_IDS`, the three-part record, the verdict words, the
`test_<id>_recorded_discrepancy_...` naming; every result keeps
`SCREENING_RESULT_NOT_PLANT_VALIDATED`). Appendix A has rows for only some of this block's
models. What each package records in `physicroll/benchmarks.py`:

| package | entry | verdict |
|---|---|---|
| 2 | none: add to `NOT_ENCODED` `'A2-LOCAL-SOURCES'`, "no published case of a film or flow-stress band exists (gap study, I2)" | - |
| 4 | `SS-V8-LOOP`: published "control within 6 I-units around a 30 I-unit target at steady speed" on 2 x 6.5 um foil [SS-S31 EX; MEASUREMENT]; project: the battery-foil demo's largest zone residual at the end of the loop (planner 2.46 I-units, 5 % valves) | `INDICATIVE_ASSUMED_INPUTS` (a synthetic mill, the tool's own control law; order of magnitude only) |
| 5 | `A6-ZONE-TIME-CONSTANT`: published 20 s [as cited by the project]; project: the battery-foil demo's fitted constants for a 20 s test, roll growth only (planner 63.8 s) and as measured hot | `INDICATIVE_ASSUMED_INPUTS`; both ratios recorded |
| 6 | `SS-V2-LOCAL-PLATE`, `SS-V2-WIDE-STRIP`, `SS-V3-WIDE-STRIP` (package 6) | as given there |
| 7 | none new (no amplitude or table measurement in the reports): `NOT_ENCODED` `'SS-S14-TABLE'` | - |
| 8 | none: `NOT_ENCODED` `'G3-KERNEL'`, "no paper isolates the exit-tension feedback for a narrow band (shape report, section 7)" | - |
| 9, 10 | none: `NOT_ENCODED` `SS-V12` ("thickness profiles of the PET rolls are not in the reports"), `SS-V13` ("the 6-7 um limit is a ridge on the hot coil; the hot-band gauge is not in the extract (X8)"), `SS-V17` ("figures only") | - |
| 11 | none: `NOT_ENCODED` `'TM-LA31-COIL'` ("needs the profile crown and a creep law") | - |
| 12 | `SS-V14` reference record; `SS-V15` in `NOT_ENCODED` | `REFERENCE_ONLY_INPUTS_NOT_RECORDED` |
| 13, 14 | none: `NOT_ENCODED` `'TM-LC18-HARDNESS'` ("no gauge ripple is quoted"), `BT-V4` text extended ("speed effect: curves not digitised") | - |

Software verification against closed forms (packages 3, 6, 7, 8, 9, 12, 13) is not a
literature comparison and lives in the module tests, not in the benchmark table.

**G''9. Test list.** Each package appends its new test modules to the list of SPEC17 G6.1
for the packages after it: `tests.test_band_local`, `tests.test_flatness_control`,
`tests.test_band_flatness_loop`, `tests.test_strip_buckling`, `tests.test_wound_roll`,
`tests.test_band_coil_winding`, `tests.test_foil_gauge` (and those SPEC17 and SPEC18 added).

---

## 0. What the planner measured and found (read before package 1)

### 0.1 Findings the coder must carry into code comments, result notes and documents, unsoftened

1. **A closed spray loop with on/off valves does not settle on either demo.** Lengthwise demo,
   29 shapemeter zones of 52 mm, 16 control zones of two nozzles, all valves open at the start,
   one nozzle at 0.45 flow: 444 valve switches in 1800 s, zone residual between 28 and 81 I-units
   in the last 300 s (39 at the start), largest zone reading 296 I-units (48 at the start). The
   control makes the flatness worse. With valves in 5 % steps the residual falls from 39 to
   below 6 I-units in 300 s (150 control steps, 77 valve steps) and then stays between 2.4 and
   5.9 I-units while the valves keep trimming by single steps (5 to 11 per 300 s, to 3600 s): a
   quantisation limit cycle against a residual the zones cannot reach (one weak nozzle inside a
   two-nozzle zone). Battery-foil demo, 24 zones, 14 control zones, 5 % steps: settled, last
   valve step at 1382 s (691 control steps, 65 valve steps), residual 19.5 -> 2.46 I-units. In
   every run the low-order part of the profile grows (zone reading 24 -> 59 I-units on the foil
   demo) because the mean cooling falls: that part is the bender's and the tilt's, which need
   the roll stack (Phase 3). The loop is reported with that part removed "as if by ideal bending
   and tilt", and says so.
2. **The fitted time constant of a zone step test depends on the test length and on the strip
   temperature term.** Battery-foil demo, one two-nozzle zone closed, shapemeter zone under it,
   1 s display filter: roll growth alone gives a fitted first-order constant of 63.8 s for a
   20 s test, 74.4 s for 60 s and 173.5 s for 600 s. Adding the strip-temperature term with a
   strip-to-roll coupling of 1.0 gives 16.0 s (20 s test), 25.3 s (40 s), 34.5 s (60 s); with
   0.5 it gives 23.5 / 34.5 / 46.9 s. The computed coupling of that pass is 0.84 (0.51 on the
   sheet demo). The plant-identified 20 s [Dohmae & Okamura 2012, as cited by the project] lies
   inside this range only with the strip-temperature term on and a test of 20 to 40 s. This
   supports the reading of gap A6 and X5; it is not a resolution: the coupling factor and the
   display filter are assumptions, and no plant protocol is recorded.
3. **Linear buckling under tension does not reproduce the measured short wavelengths.** For
   SS-V2 (steel 0.5 x 1000 mm) and SS-V3 (aluminium 0.3 x 270 mm) a Gaussian loose band in a
   free-edged strip under 5 to 100 MPa tension buckles with a half-wave of 0.77 to 0.90 of the
   width over which the mode exceeds 10 % of its peak. The measurements are 0.40 and 0.36 of the
   buckle width. The present sine mode has 1.0. The model is closer, not close. At the
   shapemeter values of SS-V2 (waves at 7.5-8 I-units) the model buckles only below about 5 MPa
   tension, with half-waves above 200 mm. As a LOCAL plate of the buckle width (150 mm), with a
   Gaussian compression of half-peak width 75 mm (an assumption), the solver gives 5.34 I-units
   simply supported and 8.65 clamped against the published 5.3 and 8.92: the published critical
   values are local-plate values without tension. No benchmark row supports replacing the
   present band states; the new model is reported beside them.
4. **On a table the dead load does not hide a reportable foil band.** A one-mode energy model
   with gravity (package 7) gives a lift limit of 2.2 I-units peak for the lengthwise demo's
   0.21 mm profile (half-wave 90 mm) and below 0.75 I-units for the battery-foil profile (half
   wave 30 mm or shorter). So X13 changes the statement "any reported band buckles after
   release" at sheet gauge and not at foil gauge.
5. **The winding result hangs on the radial stack modulus, for which no aluminium value
   exists.** One 50 mm lane 0.1 um thicker in a 30 um, 1.2 m wide, 0.15 -> 0.6 m coil at 30 MPa:
   with an isotropic stack the lane's wound-on tension reaches 160 MPa at the outer wraps and
   the radius difference is 0.77 of laps x thickness difference; with a radial modulus of 1/100
   of the hoop modulus [the only statement found, SS-S40 VP] the tension rises to 54 MPa in the
   first 1000 laps and then stays near 51-52 MPa, the factor is 0.12, nothing yields; with an
   assumed Pfeiffer stack (K2 = 30) the factor is 0.02. The project's constant 0.5 lies inside
   this range, and its verdict for a 0.1 um ridge ("yields") is reproduced only by the stiffest
   stack. With 1 um every stack but the softest yields within 300 laps. The qualitative
   statements of X8 are reproduced (radius difference below thickness difference; strain stops
   rising after the first wraps). No measured stack compressibility of oily aluminium foil
   exists (shape report, section 7), so the winding model cannot replace the present criterion
   by default: it needs the plant's press test.
6. **The independent check of the exit-tension feedback (X17) does not confirm it at foil
   gauge.** A width-coupling kernel that lets the entry and the exit velocity both vary across
   the width, with the bite's own slip sensitivities, gives a feedback stiffness of 0.69 of the
   project's pointwise value on the sheet demo and 0.10 on the battery-foil demo (the steady
   band would be about 210 I-units instead of 25). The result depends on how the strip is held
   laterally at the bite: 0.24 and 0.009 with a uniaxial closure, negative with a shear-free
   one. The kernel is not wavenumber-dependent for bands (the only length is the span, and a
   span of 3 m is long against every band): the row's "wavenumber-dependent kernel" reduces to
   a factor, plus a development length of about 0.7 wavelengths. Reported beside the pointwise
   level; nothing reads it.
7. **A hot roll stripe: three terms, two signs, two time scales.** Battery-foil demo, steady
   stripe (surface 2.36 K hotter, radius +2.96 um), film ratio 0.380 (after SPEC17 package 2),
   strip-to-roll coupling 0.84, softening 0.15 %/K: roll growth +25.1 I-units (loose); thinner
   film -4.3 I-units (tight) for an inlet weight of 0.5 and -8.6 for 1.0; softer metal +0.7;
   strip temperature as measured hot +4.7. Net loose in the steady state. Twenty seconds after
   a zone closes the surface under it is 6.3 K hotter and the roll path reads 19.2 I-units: the
   film term is then -11.5 (weight 0.5) or -22.6 (weight 1.0), the flow-stress term +1.8, the
   strip-temperature term +12.5. The mechanical net is +9.5 or -1.6: its sign in the first tens
   of seconds depends on an input nobody has measured. All of this rests on the exit-tension
   feedback of finding 6 and on the friction-closure slope of X22.
8. **Foil gauge at this demo is set by the strip, with or without a closed gap.** Mill modulus
   2.31e9 N/m against a strip modulus of 8.87e10 N/m: position control and constant-force
   control differ by 2.6 % in every gauge sensitivity. A speed-and-tension loop tuned for 61
   degrees of phase margin attenuates only below 0.52 Hz and amplifies a once-per-revolution
   tension ripple at 2.48 Hz by 1.12 (peak 1.57 at 1.13 Hz). A coil run-out of 0.1 mm gives a
   tension ripple of 0.094 MPa and a gauge ripple of 5.2 nm (0.017 %): small, because the bite's
   slip sensitivity makes the span a leaky element (time constant 2.6 ms) and the coil-on-span
   resonance (4.9 Hz) is overdamped. A 1 % entry gauge step needs 4.0 MPa of tension trim.
9. **Starvation needs an almost dry nozzle.** A volume balance puts the oil a healthy nozzle
   delivers three orders of magnitude above what the bite can carry. A weak nozzle (0.45) is
   not a film band by supply; only a fully blocked one is, and then the model has no spreading
   and returns zero film. Gap BT-G12 as a band source therefore reduces to a flag.
10. **Roller deflection.** Two estimates of its lateral stress differ by three orders of
    magnitude (edge slope as a misalignment: negligible; gathering strain: megapascals). Only
    the beam quantities are built.

### 0.2 What the gap study says that cannot be implemented as written

| row | statement | what is done instead |
|---|---|---|
| G3 | "wavenumber-dependent in-plane kernel" | the kernel is a constant factor for bands (finding 6); built with three closures and a development length |
| G4 | "Koiter one-term post-buckling"; "elastic foundation term for the table" | one-mode Ritz amplitude; gravity as a one-sided dead load in an energy criterion (a table is not a spring) |
| G5 | "bending, tilt from G1" | spray zones only; low-order part removed as if by ideal actuators; a column interface for supplied actuator vectors |
| G9 | "Hakiel 1D model per width segment with `E_r(P)` from stack compression" | built; no default for the stack law; three labelled choices, each needs an input |
| G10 | "nip film by line-contact EHL" | not built (no formula in the reports); two bounding cases with and without the entrained film |
| G11 | "roller deflection (Shelton), moment-transfer and slack-edge limits" | misalignment and taper only; the foil factor of 15 quoted, not modelled |
| A8 | "creep `eps_cr' = A*sigma^n`" | Phase 3; coil temperature and its thermal stress only |
| BT-G12 | "inlet meniscus position in the Reynolds integration" | volume balance (finding 9) |
| C1 | "closed gap" | constant strip force with an effective mill modulus as the interface for the kiss stiffness |

### 0.3 Timings and budgets (Python 3.13, one core, export of `8f10cbe`)

| item | measured |
|---|---|
| `roll_thermal.steady_state`, 340 x 16 cells | 0.15-0.18 s |
| one ADI step of the same grid (through the stepping wrapper) | 1.6 ms |
| `rt.simulate` called for 2 s (start-up, field conversion) | 12 ms per call: the reason for the stepping API of package 3 |
| `bw.shape_levels` on a steady profile | 0.25 s |
| `ss.transfer_radius_profile`, 300 samples | 17 ms |
| zone-reading operator, 29 zones | 0.74 s |
| spray influence matrix, 16 control zones (16 steady solves) | 2.8 s |
| closed loop, 1800 s horizon, 1 s step, 2 s control interval | 4.1-5.1 s |
| zone step test, 600 s at 0.5 s | 3.0 s |
| buckling: one critical-mode search, 120 samples (18 wavenumbers) | 0.21-0.33 s; 200 samples 0.35-0.50 s |
| dead-load scan, 24 wavenumbers with modes | 0.36-0.49 s |
| winding, 24 lanes x 150 layers | 0.30 s; one lane, 400 layers 0.07 s |
| kernel, gauge loop frequency response, span formulas | below 0.05 s |
| reference (SPEC18 section 0.2): `diagnose` battery-foil 72.6 s, lengthwise 48.7 s; quick profile 13.8 s; survey 46.1 s | |

Budgets:

- A `diagnose` that supplies none of the new inputs: at most 1 % slower (the kernel level of
  package 8, about 0.05 s, is the only always-on addition).
- `width_model.flatness_control`: at most 12 s at the default numerics (set-up 4 s, loop 6 s,
  metrics 2 s); at most 3 s with the quick profile's grid. `zone_step_test`: at most 4 s
  (1.5 s quick). Battery-foil `diagnose` with all three demo inputs: at most 90 s; its quick
  profile at most 20 s.
- `model_options.buckling_model = 'sine_mode_and_fe'`: at most 0.6 s per profile and state, at
  most 6 s per `diagnose`; never inside an onset bisection, a lever row or the gauge trend.
- Winding with lanes: at most 2 s. Everything else in this block: at most 0.5 s per section.
- Each new test module under 60 s; the loop tests use a short roll (0.6 m), 20 mm cells and
  6 radial cells.

---

## 1. Overview

| # | Package | Gap ids | What changes for a user | Default or opt-in | Depends on | Size |
|---|---|---|---|---|---|---|
| 1 | Local state across the width | A2 (inputs), BT-G12, A1 computed (I3, I11) | New optional `width_model.local_coupling`: oil temperature, viscosity, film, friction, flow stress, oil supply and strip exit temperature at every width station, as differences from the healthy header | new input | SPEC18 pkg 3, 5, 6, 7; SPEC17 pkg 6 | 650-800 |
| 2 | Local sources as a band | A2, BT-G4 in full (I2) | The film, flow-stress and strip-temperature terms of a hot stripe beside the roll-growth term, each as I-units, with their sum and its sign; the same at the peak of every valve event | new input (that of pkg 1) | 1; SPEC17 pkg 7 | 600-750 |
| 3 | Controlled thermal stepping, influence vectors, controller | G5 (core) | Nothing in the engine yet: `roll_thermal.ControlledRun`, `physicroll/flatness_control.py` | not wired | SPEC17 pkg 4 | 750-900 |
| 4 | Closed spray loop in the engine | G5 (I5) | New optional `width_model.flatness_control`: valve states computed from zone readings; predicted valve events; whether the loop settles | new input | 3; 2 (optional terms) | 750-900 |
| 5 | Zone step test emulation | A6 (X5) | New optional `width_model.zone_step_test`: the first-order constant a plant test of a given length would fit, with and without the strip-side terms | new input | 3, 2 | 450-600 |
| 6 | Buckling: wavelength under tension | G4 (part 1), G16 | New module `physicroll/strip_buckling.py`; benchmark rows; nothing in the engine yet | not wired | none | 700-850 |
| 7 | Post-buckling amplitude, saturated stress, dead load; engine | G4 (part 2), I12, X11, X13 | `model_options.buckling_model: 'sine_mode_and_fe'`: wavelength, wave height, what the shapemeter reads of a buckled band, lift limit on a table, beside the present states | opt-in, beside | 6; SPEC17 pkg 4 | 700-850 |
| 8 | Width-coupling kernel | G3 (kernel), X17 | A fourth shape level computed beside the three present ones; the distance at which the far-field stress is reached | computed beside, always | none | 550-700 |
| 9 | Winding: one radial model, air layer | G9 (core), G10 (film) | New module `physicroll/wound_roll.py`; nothing in the engine yet | not wired | none | 750-900 |
| 10 | Winding by lanes in the engine | G9 (I7), X8 | New optional `width_model.coil_winding`: tension, pressure, radius and plastic strain per lane; elongation after unwinding; the effective compaction factor beside the assumed 0.5 | new input, beside | 9 | 750-900 |
| 11 | Ironing roll, coil temperature | G10 (nip), A8 (temperature; I8) | Wound-in tension with a nip; coil temperature at winding against the published coil limits; cooling curve; thermal stress between lanes | new input | 10, 1 | 600-750 |
| 12 | Lateral stress in spans | G11 (I13) | New optional `width_model.span_alignment`: lateral stress from roller misalignment and taper; critical misalignment; one evidence branch | new input; ONE rule branch | none | 500-650 |
| 13 | Foil gauge: sensitivities and the speed-tension loop | C1, BT-G13 (I6), X7 | New optional section `foil_gauge_control`: gauge against tension, speed, friction, hardness; loop margins; response to disturbances | new input | SPEC18 pkg 2, 3 | 750-900 |
| 14 | Reels, spans, run-out; chaining of passes | C2, C8 (I6, I14) | New optional `foil_gauge_control.reels`: tension ripple from coil run-out and what the loop leaves of it; ripple carried from pass to pass | new input | 13 | 600-750 |
| 15 | Guided app | plant-facing side of 1-14 | Questions, plain words and cards | - | 1-14 | 800-900 |

Out of scope for every package (Phase 3): roll stack, bending and tilt as computed actuators,
closed-gap contact and kiss force, lateral metal flow and the strip-element model, roll ends,
creep and recovery in the coil, chatter extensions, surface generation, slitting. No package
changes `chatter.assemble_state_matrix`, `slab.py`, `foil_bite.py`, `halfspace_bite.py`, the
thermal solver's equations or any existing evidence item other than the one branch of
package 12. No new hypothesis, no new observation key.

---

## Package 1 — Local state across the width (A2 inputs, BT-G12, A1 computed; I3, I11)

### Why
Gap A2 (PT-T4, PT-T31, PT-T39, PT-T12; TM-LC25 AB; formulas are the row's): a hot roll stripe
changes the oil viscosity, the film, the friction and the flow stress at its width position.
Gap BT-G12 (BT-S14 FT, BT-S36 FT): a weak nozzle supplies less oil as well as less cooling.
Gap A1 / G6: the strip leaves the bite hotter where the roll is hotter. SPEC18 built the
single-station pieces (viscosity table, closure with its slope, rate-temperature factor, heat
partition, roll surface cycle). This package evaluates them at every width station. It makes no
band: package 2 does.

### Design

New module `physicroll/band_local.py` (integration layer, style of `band_thermal.py`; it reads
the case and finished result sections).

**Difference method.** Everything is a difference from the healthy header at the same pass, as
the radius stripes are (`band_width._steady_section`): the reference station is the healthy
state, so a healthy header gives zero everywhere.

**Case schema.** `band_width.WIDTH_DEFAULTS` gains `'local_coupling': None`;
`validate_width_model` validates (strict keys, messages
"width_model.local_coupling.<key> must be ..."):

| key | unit | range | default |
|---|---|---|---|
| `inlet_roll_temperature_weight` | - | [0, 1] | 0.5 |
| `flow_stress_temperature_coefficient_per_k` | 1/K | [0, 0.01] or null | null = `hardening.rate_temperature.temperature_coefficient_per_k` (SPEC18 package 5) when that section exists, else the flow-stress term is not supplied |
| `strip_roll_temperature_coupling` | - | [0, 1.5] or null | null = computed (formula 8) |
| `oil_flow_per_nozzle_m3_s` | m3/s | (0, 0.1] or null | null = no supply check |
| `oil_capture_fraction` | - | (0, 1] | 1.0 |
| `provenance` | text | nonempty | required |

`inlet_roll_temperature_weight` `[D, SPEC19: analyst choice]`: the share of a roll surface
temperature difference that appears in the oil at the inlet. The film forms between the roll
and the strip; the strip entry temperature is uniform across the width in this model, so 0.5
is the two-surface mean and 1.0 the bound the bite report uses ("a roll surface that is locally
hotter thins the film at once", gap BT-G4 [derived]). Package 2 always evaluates 0, the entered
value and 1.

**Formulas** (per strip sample `z_i` of the steady thermal grid; `ref` = healthy header):

1. `dT_r(z) = T_r,actual(z) - T_r,healthy(z)` [K]. `T_r` is the roll surface temperature the
   bite meets: `width.roll_surface_cycle.bite_entry_temperature_k` (SPEC18 package 7) when
   that section exists, else the bulk model's `surface_temperature_k` with the flag
   `LOCAL_STATE_FROM_CIRCUMFERENTIAL_MEAN_SURFACE_TEMPERATURE`. For the first case add one
   output to the surface-cycle function of SPEC18 package 7:
   `healthy_bite_entry_temperature_k` on the same `z_m`, from the same unit solutions at spray
   weight 1 and the healthy steady field at the layer depth (additive key).
2. `T_in(z) = tribology.inlet_temperature_k + w_in*dT_r(z)`.
3. `v(z) = eta0(T_in(z))/eta0(T_in,ref)` with `Lubricant.dynamic_viscosity_pa_s(T, 0.0)` (table
   or exponential law, SPEC18 package 3).
4. Smooth film `h_s(z) = h_s,ref*v(z)`, film ratio `Lambda_s(z) = Lambda_ref*v(z)`
   [the inlet film formula is proportional to `eta0`: BT-S9 EX eq. 4.1 as coded in
   `bite_tribology.inlet_film_thickness`]. `h_s,ref`, `Lambda_ref` =
   `process.friction.operating.film_thickness_m`, `.film_ratio`.
5. Supplied film `[D, re-derived in SPEC19: volume balance; the film cannot carry more oil than
   arrives]`: oil arriving per unit barrel length on one roll
   `q'(z) = oil_flow_per_nozzle_m3_s*oil_capture_fraction*weight(z)/nozzle_pitch_m` [m2/s],
   `weight(z)` = `SprayHeader.weight_profile` of the ACTUAL levels (a healthy header gives 1);
   the inlet passes `h*u_bar` per unit width with `u_bar = (V_r + u_entry)/2`,
   `V_r = u_exit/(1 + f)`, `u_entry = u_exit*h1/h0`; so `h_sup(z) = q'(z)/u_bar`.
   Film used: `h(z) = min(h_s(z), h_sup(z))`, `Lambda(z) = Lambda_s(z)*h(z)/h_s(z)`;
   `starved(z) = h_sup(z) < h_s(z)`. Without a flow: `h = h_s`, `starved` null.
6. `dmu(z) = mu_cl(Lambda(z)) - mu_cl(Lambda_ref)`, `mu_cl` = the case's friction closure
   evaluated by `bite_tribology.friction_coefficient` (either model of SPEC18 package 3; the
   valley models get the case-pass `bite_state`). Only the DIFFERENCE is used: the level stays
   the pass friction. `Lambda(z) <= 0` is evaluated at `Lambda = 1e-6`.
7. `dY_rel(z) = -c_T*dT_b(z)`, `dT_b(z) = 0.5*eta_x*dT_r(z)` [form: gap A2,
   `Y(z) = Y_ref*(1 - c_T*(T - T_ref))`; mid-bite temperature as in SPEC18 package 5].
8. `eta_x = T_x(T_r0 + 1 K) - T_x(T_r0)` from two calls of `bite_tribology.heat_partition`
   (SPEC18 package 6) with the case-pass inputs of `band_process.heating_row`; the model is
   linear in `T_r0`, so the 1 K difference is exact `[D, SPEC19]`. Supplied value overrides.
9. `dT_x(z) = eta_x*dT_r(z)`; `strip_exit_temperature_k(z) = T_x,ref + dT_x(z)` with `T_x,ref`
   the case pass's modelled exit temperature. The change of friction heat with `dmu(z)` is
   second order and left out (limitation).

**API.**
```python
def local_params(case, w, trib, lub, closure, surface, bite, heat_row, friction_row, cycle) -> dict
#   everything that does not depend on the temperature profile: w_in, c_T, eta_x (and its basis),
#   Lambda_ref, h_s_ref, mu_ref, u_bar, supply profile q'(z) on the strip samples, bite_state, flags
def local_changes(z_strip, d_surface_temperature_k, params) -> dict
#   formulas 2-9 for any roll-surface temperature difference profile (steady or a snapshot)
def local_state_section(case, w, th, steady, trib, bite, heat_row, friction_row, cycle) -> dict
```
`local_changes` is the function packages 2, 4 and 5 call for transient snapshots.

**Result** `width.local_state` (every v2 result; `not_supplied` without the key;
`NOT_ASSESSABLE` with the reason without tribology, without a steady thermal solution, or
without a case-pass bite): `status`, `not_supplied`, `provenance`, `z_m`,
`roll_surface_temperature_change_k`, `roll_surface_temperature_basis`,
`inlet_temperature_change_k`, `viscosity_ratio`, `film_ratio`, `film_thickness_m`,
`supplied_film_m` (or null), `starved` (or null), `friction_change`,
`friction_change_fraction` (of the pass friction), `flow_stress_change_fraction` (or null),
`strip_exit_temperature_change_k`, `strip_exit_temperature_k`, `coupling`
(`{'inlet_roll_temperature_weight', 'strip_roll_temperature_coupling', 'coupling_basis',
'flow_stress_temperature_coefficient_per_k', 'coefficient_basis'}`), `at_largest_change`
(the station of the largest `|dT_r|` with every quantity there), `supply`
(`{'healthy_supplied_film_m', 'ratio_to_smooth_film', 'level_below_which_starved'}` or
not supplied), `closure_model`, `basis` (one tagged sentence per formula), `flags`,
`limitations`.

Flags (top level too; one plain sentence each in `band_plain.FLAGS`):
`LOCAL_STATE_COMPUTED`; `LOCAL_STATE_FROM_CIRCUMFERENTIAL_MEAN_SURFACE_TEMPERATURE`;
`LOCAL_FRICTION_FROM_PLACEHOLDER_CLOSURE_SLOPE` (the closure's own flag, repeated);
`OIL_SUPPLY_BELOW_SMOOTH_FILM` (a starved station under a nozzle whose level is above 0);
`ZERO_OIL_SUPPLY_UNDER_BLOCKED_NOZZLE_NO_SPREADING_MODEL` (a station with `h_sup = 0`);
`LOCAL_FRICTION_CHANGE_ABOVE_20_PERCENT_LINEAR_SOURCE_INDICATIVE` (`|dmu|/mu > 0.2`
somewhere).
Limitations (fixed): differences from the healthy header only; inlet temperature weight is an
assumption; one-way (the local force, slip and heat changes do not return to the roll
temperature: loop I1 stays open); friction heat change left out; no lateral spreading or
carry-over of oil; roughness uniform across the barrel (a rougher or coated barrel zone is
entered through SPEC17 package 7's supplied stripes); the strip entry temperature is uniform.

**Strip temperature link (A1 computed).** `band_width.strip_temperature_section` (SPEC17
package 6) is NOT changed and a supplied scan is not replaced. `local_state_section` adds
`thermal_flatness = ss.thermal_flatness_term(z, strip_exit_temperature_k)` (keys `i_units`,
`i_units_per_kelvin`, the default-coefficient flag). Package 2 uses it.

**Demo.** Battery-foil scenario: `"local_coupling": {"inlet_roll_temperature_weight": 0.5,
"flow_stress_temperature_coefficient_per_k": 0.0015, "strip_roll_temperature_coupling": null,
"oil_flow_per_nozzle_m3_s": 1.6667e-4, "oil_capture_fraction": 1.0, "provenance": "synthetic:
inlet weight 0.5 (two-surface mean, assumed); softening 0.15 %/K from the 1100-H18 strengths at
20 and 100 C [PT-T31, PT-T39; coefficient derived]; 10 l/min per nozzle (assumed)"}` and a
notes line.

### Worked numbers (planner, `s25/local.py`, `s25/eta.py`; battery-foil demo, film ratio 0.380072 after SPEC17 package 2)
- Largest `dT_r` (circumferential mean): 2.358 K at 0.6225 m. Lengthwise demo: 1.664 K at
  0.6675 m.
- `w_in` 0.5: `dT_in` 1.179 K; viscosity ratio `exp(-0.015*1.179) = 0.982470`; film ratio
  0.373410; `dmu` +3.748e-4 with the placeholder closure (+1.25 % of 0.03), +3.149e-4 with the
  two-point closure. `w_in` 1.0: ratio 0.965246, `dmu` +7.45e-4 (placeholder).
- `eta_x` 0.844 (contact time 0.218 ms, `C_s` 43.4 J/m2K, film 95 nm, prototype of SPEC18
  package 6); lengthwise case pass 0.510. `dT_x` 1.99 K, `dT_b` 0.995 K, `dY_rel` -1.49e-3.
- Supply: 1.6667e-4 m3/s per nozzle, pitch 0.052 m: `q'` 3.205e-3 m2/s; `u_bar` 9.36 m/s;
  healthy `h_sup` 3.42e-4 m, 3600 times the smooth film 9.5e-8 m; the nozzle at 0.45 is not
  starved; `level_below_which_starved` 2.8e-4.
Pin the implementation's values after checking each against these to 2 % (`eta_x` to 5 %: it
depends on SPEC18 package 6 as built).

### Tests (`tests/test_band_local.py`)
Function level with a hand profile (`dT_r` = 0, 1, 2.358 K at three stations): formulas 2-7 to
`1e-9` relative against the numbers above (exponential law and a two-point table that
reproduces it); `dmu` equals the closure's `dmu_dlambda*dLambda` to 1 % for 0.1 K; zero profile
gives zeros and no conditional flag; supply: the three numbers, a level of 1e-4 is starved, a
blocked nozzle gives zero film and its flag; `eta_x` supplied against computed; without
`hardening.rate_temperature` and without the coefficient the flow-stress entries are null and
the reason is given; validation messages. One coarse `diagnose` (the numerics of
`tests/test_band_v2_sections.py`): section present; with the key absent every result key except
`inputs` and the `not_supplied` entry is equal; hypotheses identical.

### Documentation
Guide: new 7.11 "What a hot roll stripe does besides growing the roll: local state" (the nine
formulas with tags, the difference method, the inlet weight and why it is an assumption, the
supply balance and finding 9, numbers from the regenerated artifact); 5.3 (keys; which plant
data: oil flow per zone from the coolant system display, softening from tensile tests at 20 and
100 C); 13; 14. Gap study section 11: A2 `REDUCED_MODEL_OPT_IN` (after package 2), BT-G12
`SCREENING_VERSION` (volume balance; no meniscus position, no spreading), A1 / G6 rows extended
("computed profile from the roll surface difference; local heat change left out").

### What changes, what must not
Artifacts: additive (`inputs.width_model.local_coupling`, `width.local_state`,
`width.roll_surface_cycle.healthy_bite_entry_temperature_k` where that section exists; flags of
the battery-foil demo). No score.

### Do not
- Do not feed any local quantity back into the bite, the heat row or the roll temperature.
- Do not change `tribology.inlet_temperature_k` or the pass friction.
- No spreading, carry-over or wiper model; no default oil flow.

---

## Package 2 — Local sources as a band: three contributions and their sum (A2, BT-G4 in full; I2)

### Why
Gap BT-G4 / A2: `dp(z) = p_Y*dY + p_mu*dmu`, "local gap change through the existing roll
compliance; report the three contributions separately". SPEC17 package 7 built the transfer
(`strip_shape.transfer_force_profile`) and the sign note "the net sign is not known". Package 1
gives `dmu(z)` and `dY(z)`. This package turns them into I-units beside the roll-growth term.

### Design (`band_local.py`, `band_width.py`)

`band_local.source_terms(z_strip, changes, sp, sens) -> dict`, with `sp` the shape parameters
of the pass (`band_width.shape_params_or_none`) and `sens =
{'dforce_per_width_dfriction_n_m': M_mu, 'dforce_per_width_dflow_stress_m': M_Y}` from
`band_process.friction_force_sensitivity` and `flow_stress_sensitivity` through the callables
SPEC17 package 7 added to `width_section` (add the flow-stress one beside the friction one;
for a half-space bite both come from `bite_extras`, SPEC18 package 2):

    dp0'_film(z) = M_mu*dmu(z)                  [N/m]
    dp0'_flow(z) = M_Y*Y_pass*dY_rel(z)         [N/m]
    dh_X(z)      = transfer_force_profile(z, dp0'_X, ..., with the exit-tension feedback)
    I_X(z)       = 1e5*(eps_X(z) - mean(eps_X)),  eps_X = -xi*dh_X/h_exit      (flat entry)
    I_T(z)       = thermal_flatness_term(z, T_x(z))['i_units']                 (package 1)
    I_roll(z)    = width.shape.steady.i_units_linear_feedback

`I_roll` is the linear-feedback profile, NOT `i_units_with_feedback`: the terms are summed, and
the band-wise saturation scaling is not linear. When the steady shape has saturated bands the
flag `LOCAL_SOURCES_SUMMED_ON_LINEAR_PROFILE_SATURATION_NOT_APPLIED` is set.

    mechanical_net(z)  = I_roll + I_film + I_flow       (what stays when the coil has cooled)
    as_measured_hot(z) = mechanical_net + I_T           (what a shapemeter without temperature
                                                         compensation senses)

Each of the five profiles and both sums goes through `ss.flatness_from_elongation` (inputs as
the shape chain) for `bands`, `status`, `released_status`.

`at_bands`: for every band of `I_roll` and of `mechanical_net`, at its peak position: the five
term values, both sums, and `net_sign`:
`'LOOSE' | 'TIGHT' | 'BELOW_REPORTING_THRESHOLD'` for the entered inlet weight, plus
`net_sign_at_weight_0` and `net_sign_at_weight_1` (the film term re-evaluated with
`local_changes` at weights 0 and 1; the flow-stress and strip terms do not depend on the
weight) and `sign_depends_on_inlet_weight` (bool).
`compliance_only`: the peak of `I_film` and `I_flow` with
`exit_tension_force_sensitivity_per_width_m=None`, to show what the terms rest on.

**Events.** `band_width._events_section` already holds a snapshot of the whole surface
temperature at every record time. For each event add, only when `local_coupling` is supplied,
`local_sources = {'at_20_s': {...}, 'at_peak': {...}}`: the snapshot nearest to
`start + min(20 s, duration)` and the peak snapshot; surface temperature difference from the
starting steady state; `local_changes`; `source_terms` with the radius profile of that snapshot
through `transfer_radius_profile` (linear feedback) as `I_roll`; reported at the event's
monitor position: the five terms, both sums, the three sign words. No record time is added and
`rt.simulate` is called exactly as before (the snapshots exist every `RECORD_INTERVAL_S`); a
test asserts the event histories are bit-identical with and without `local_coupling`.
`FAST_PATH_TIME_S = 20.0` `[D, SPEC19: analyst choice; the surface time scale is 8-25 s,
computed in the thermal report]`.

**Result** `width.local_sources` (`not_supplied` / `NOT_ASSESSABLE` as package 1, also without
shape parameters): `status`, `z_m`, `roll_growth_i_units`, `film_i_units`,
`flow_stress_i_units`, `strip_temperature_i_units`, `mechanical_net_i_units`,
`as_measured_hot_i_units`, `profiles` (per name: `max_i_units`, `min_i_units`, `status`,
`released_status`, `bands`), `at_bands`, `compliance_only`, `sensitivities` (`M_mu`, `M_Y`,
load exponents, `sensitivity_bite_model`), `events` (list as above or `[]`), `sign_note`,
`basis`, `flags`, `limitations`.
`sign_note` (fixed): "Roll growth makes the strip thinner and the fibre loose. A thinner oil
film raises friction and force, makes the strip thicker and the fibre tight. Softer metal
lowers the force and makes it loose. A hotter fibre reads loose while hot and that part is gone
after cooling. Roll growth needs minutes; the other three follow the roll surface within
seconds."
Flags: `LOCAL_SOURCES_COMPUTED`; `LOCAL_NET_SIGN_DEPENDS_ON_INLET_WEIGHT` (any band or event
row); `LOCAL_SOURCES_REVERSE_A_BAND` (a band of `I_roll` whose `mechanical_net` at the same
position has the other sign or is below the threshold);
`LOCAL_SOURCES_SUMMED_ON_LINEAR_PROFILE_SATURATION_NOT_APPLIED`.
Limitations: those of package 1; those of SPEC17 package 7 (linear; `dF/dmu` of a
constant-friction bite; exit-tension feedback not confirmed by the kernel of package 8);
`width.shape.steady`, the onsets, the gauge trend and every evidence item are NOT changed.

`band_sensors.shapemeter_profiles` appends `local_mechanical_net` and `local_as_measured_hot`
(labels: "roll growth plus film and flow-stress terms", "the same plus the strip temperature
term").

**Report**: block "A hot stripe: roll growth, oil film, softer metal, strip temperature" in
`_width_section` after the friction-stripe block: one chart with the five profiles, the table
`at_bands` (signed I-units, sign words), the event table (two rows per event), the sign note,
and in a `warn` paragraph: "The film term uses a friction law whose slope has no support in
data, and an oil temperature weight that was assumed. Read the signs, not the digits."

### Worked numbers (planner; peak estimates with the transfer gain of the stripe's dominant wavelength, `G = 6.744e-14 m per N/m` with feedback, `9.248e-12` compliance only; `M_mu` 5.1403e7 N/m, `M_Y` 0.011165 m, load exponents 1.609 and 2.038)
| battery-foil demo | roll growth | film (w 0.5 / 1.0) | flow stress | strip temperature | mechanical net | as measured hot |
|---|---|---|---|---|---|---|
| steady stripe, `dT_r` 2.36 K | +25.1 | -4.3 / -8.6 | +0.7 | +4.7 | +21.5 / +17.2 | +26.2 / +21.9 |
| 20 s after zone 18-19 closes, `dT_r` 6.3 K | +19.2 | -11.5 / -22.6 | +1.8 | +12.5 | +9.5 / -1.6 | +22.0 / +10.9 |

Compliance-only film term, steady, weight 0.5: about -590 I-units. Lengthwise demo, steady
(`dT_r` 1.66 K, film ratio 0.180, load exponent in friction 0.50): roll +50.7, film -2.2 / -4.3
(prototype with the pre-correction film; recompute), flow +1.5, strip +2.0 (`eta_x` 0.51).
The implementation works on whole profiles with the mean removed: pin its own values after
checking the peaks agree with these to 15 %, and assert the signs and
`sign_depends_on_inlet_weight` true for the 20 s row.

### Tests
`tests/test_band_local.py`: a single sinusoid `dmu(z)`: `I_film` equals
`-1e5*xi*G(lam)*M_mu*dmu/h` to `1e-9`; zero changes give zero terms and
`mechanical_net == I_roll`; signs (positive `dmu` tight, negative `dY_rel` loose, positive
`dT_x` loose); sums; weight re-evaluation; `compliance_only` larger than with feedback;
`NOT_ASSESSABLE` without shape parameters. `tests/test_band_lengthwise.py` (coarse): event rows
carry `local_sources` only with the key; event histories bit-identical; hypotheses identical;
`width.shape.steady` identical. Report renders, no `nan`.

### Documentation
Guide 7.11 second part (derivation as SPEC17 7.8, the table from the regenerated artifact,
finding 7 in full, "read the signs"); 3.5 (one paragraph replacing "the net sign is not
known" by what the model gives and on what it rests); 7.4 (events: the fast path); 12; 13; 14.
Gap study section 11: A2 `REDUCED_MODEL_OPT_IN`, BT-G4 row extended ("in full, on the Phase 1
closures; one-way").

### What changes, what must not
Artifacts: additive (`width.local_sources`; `local_sources` in event rows as `not_supplied`
or filled; two shapemeter profiles and flags in the battery-foil demo). No evidence item: the
hypothesis `heat_streak_or_film_variation` gets no model item (open decision 2).

### Do not
- Do not add any term to `width.shape.steady` or to an event's `peak_shape`.
- Do not report a net number without its two weight variants.
- Do not close the loop to the roll temperature.

---

## Package 3 — Controlled thermal stepping, influence vectors, controller (G5 core)

### Why
Gap G5 (SS-S29 to SS-S34, SS-S39): "least squares on actuator influence vectors (bending, tilt
from G1; one column per spray zone from `roll_thermal`), dead bands, valve minimum on / off
times, target curve". The reports give this structure in words [SS-S34 EX, SS-S33 EX,
SS-S31 EX] and no control law. The law below is therefore a stated, simple one
`[D, SPEC19: analyst design]`: it is what the tool simulates, not what any vendor system does.
This package builds the parts and tests them alone; package 4 wires them.

### Design A — `roll_thermal.ControlledRun` (new class; `simulate` and `steady_state` untouched)

```python
class ControlledRun:
    def __init__(self, roll, header, base_segment, *, initial, axial_cell_m=0.005,
                 radial_cells=16, expansion_constraint='axially_free',
                 reference_temperature_k=None, max_cached_level_sets=512)
    z_m                      # list, the axial cell centres
    time_s                   # simulated time so far
    def advance(self, nozzle_levels, duration_s, time_step_s) -> dict
    def result(self) -> dict
```
`base_segment` gives bite heat, heat fraction, strip and coolant (its levels and duration are
ignored). `advance` steps the field for `duration_s` with the given levels:
`n = max(1, ceil(duration_s/min(time_step_s, dz^2/a_z) - 1e-9))` equal steps; the first step
after the levels CHANGED (and the very first step) is the start-up of `simulate` (two
backward-Euler half steps), every other step a Peaceman-Rachford step, exactly as `simulate`
does at a segment start. It keeps the energy ledger of `simulate`. It returns
`{'time_s', 'radius_growth_m', 'surface_temperature_k'}` at the end of the interval. `_Problem`
and `_Stepper` objects are cached per rounded level tuple (6 decimals), oldest dropped beyond
the cap. `result()` returns what `simulate` returns at its end (`field`, ledger, `solver` with
`steps` and `startup_steps`, flags, limitations), without snapshots and monitors, and without a
wall time. Use the module's private helpers (`_common`, `_Problem`, `_Stepper`, `_profiles`,
`_initial_rows`, `_stored_energy_j`); do not copy their code.

Why not `simulate` in a loop: 12 ms per call against 1.6 ms per step (section 0.3).

### Design B — `physicroll/flatness_control.py` (no import of any `band_*` module)

Status string `STATUS = 'UNVALIDATED_FLATNESS_LOOP_SIMULATION_ANALYST_CONTROL_LAW'`.

```python
def low_order_basis(zone_centres_m, weights, order) -> list      # order -1 .. 4; -1 = empty
def remove_low_order(values, basis, weights) -> tuple            # (residual, coefficients)
def influence_matrix(readings_at, base_levels, groups, *, step=0.2) -> list
def regularised_gain(influence, weights, regularisation_fraction=0.01) -> list
class ZoneController          # the law below; .step(time_s, readings) -> list of valve levels
def fit_supplied_actuators(error, actuators, weights) -> tuple   # (remaining error, settings)
def run_loop(advance, readings_of, controller, *, horizon_s, control_interval_s, time_step_s,
             settle_window_s=300.0, delay_intervals=0, display_time_constant_s=0.0) -> dict
def fit_first_order_dead_time(time_s, values, window_s) -> dict  # package 5
```

**Zones, weights.** `readings` are zone readings in I-units (positive = loose), `None` for a
zone without strip; `weights` = the zone coverage fractions (0 for `None`).

**Low-order part** `[D, SPEC19]`: polynomials `1, x, x^2, ...` in the zone centre mapped to
`[-1, 1]` over the covered zones, orthonormalised by weighted Gram-Schmidt;
`residual = e - sum_k c_k*b_k`, `c_k = sum_j w_j*e_j*b_kj`. Order 2 removes mean, tilt and
parabola: "as if by ideal bending and tilt". The coefficients are reported, never controlled.

**Influence matrix** `[D, SPEC19]`: column `k` = change of the steady zone readings per unit
INCREASE of the level of control zone `k` (a list of nozzle indices), by one-sided difference:
`B[:, k] = (r(u - step*e_k) - r(u))/(-step)` at the base levels `u` (when `u_k - step < 0` the
step is taken upward). `readings_at(levels)` is a callable. More cooling makes the roll
smaller, the strip thicker, the fibre tight: the diagonal is negative.

**Gain** `G = (B^T W B + lam*I)^-1 B^T W`, `W = diag(weights)`,
`lam = regularisation_fraction*max_k (B^T W B)_kk`; solved by Gaussian elimination with partial
pivoting.

**Control law of `ZoneController`** (state per control zone: demand `u*`, valve level, time of
its last change):
1. `e_j = r_j - target_j` (zones with weight 0 are left out).
2. With supplied actuators: weighted least squares of `e` on their influence vectors, settings
   clipped to their limits, their fitted part subtracted (instant response; the interface for
   the bender and tilt of Phase 3).
3. `rho = remove_low_order(e, basis, weights)[0]`.
4. `d = G*rho` (one value per control zone).
5. Dead band: `d_k` is set to 0 when `|d_k|*b_k <= dead_band_i_units`, `b_k = max_j |B_jk|`
   (the largest reading change that correction would make).
6. `u*_k <- clip(u*_k - integral_gain*d_k, lowest level, highest level)`.
7. Valve: the allowed level nearest to `u*_k` (ties: the lower) replaces the present level
   only if it is closer by more than `hysteresis_fraction` (0.1) of the gap between the two
   levels, AND the valve has held its present level for at least `minimum_on_time_s` (when the
   present level was reached by going up) or `minimum_off_time_s` (by going down).
Constructor arguments: `influence`, `weights`, `groups`, `valve_levels`, `initial_level`,
`minimum_on_time_s`, `minimum_off_time_s`, `dead_band_i_units`, `integral_gain=0.1`,
`low_order=2`, `targets=None`, `supplied_actuators=None`, `hysteresis_fraction=0.1`,
`regularisation_fraction=0.01`. The three analyst constants (0.1, 0.1, 0.01) are named in the
result's `basis`.

**`run_loop`.** `advance(levels, duration_s, time_step_s)` and `readings_of(state)` are
callables (package 4 passes `ControlledRun.advance` and the reading operator). Every control
interval: advance; readings; optional transport delay (a FIFO of `delay_intervals` readings)
and display filter `y <- y + (dt/(tau + dt))*(x - y)`; `controller.step`; log. Result:
`status`, `control_steps`, `valve_changes`, `valve_log`
(`[{'time_s', 'control_zone', 'from_level', 'to_level'}]`, at most 500 kept, the count always
exact), `last_valve_change_s`, `control_steps_to_last_change`, `initial` and `final`
(`readings_i_units`, `residual_i_units`, `max_abs_residual_i_units`, `max_abs_reading_i_units`,
`low_order_coefficients`, `levels`, `demand`), `history` (`time_s`, `max_abs_residual_i_units`,
`max_abs_reading_i_units`, thinned to 300), `last_window` (`valve_changes`,
`max_abs_residual_i_units` highest and lowest), `zones_at_limit`, `flags`.

Status vocabulary (fixed): `SETTLED` (no valve change in the last `settle_window_s`);
`TRIMMING_WITHIN_BAND` (changes in the last window and the largest residual there at most
`TRIM_BAND_FACTOR = 3.0` times the dead band); `NOT_SETTLED` (otherwise). Flags:
`CONTROL_INCREASES_RESIDUAL` (largest residual of the last window above the initial one),
`CONTROL_ZONE_AT_LIMIT` (a demand at its lowest or highest level at the end). A horizon shorter
than twice the window is rejected (`ValueError`). The loop cannot run away numerically: the
thermal step is unconditionally stable, the demand is clipped, and the minimum dwell times
bound the number of valve changes by `horizon/min(dwell)` per zone; a test asserts the bound.

### Worked numbers
Package 4 holds the closed-loop numbers. Here: the two-zone hand case of the tests.
`B = [[-10, -2], [-2, -10]]`, weights 1, `lam = 0`: `G = [[-0.104167, 0.020833], [0.020833,
-0.104167]]`; `rho = [5, 0]`: `d = [-0.520833, 0.104167]`; with gain 0.1 and levels 0 ... 1 in
steps of 0.05 from 0.5 and no dead band: demands 0.552083 and 0.489583 after one step. With a
dead band of 2 I-units: `|d_1|*b_1 = 5.21` moves the first demand (0.552083);
`|d_2|*b_2 = 1.04` leaves the second at 0.5. The first valve goes to 0.55 only when its dwell
time has passed.

### Tests
`tests/test_roll_thermal.py` (new class): `ControlledRun.advance` over the two segments of a
short events case equals `rt.simulate` with the same segments and step (`radius_growth_m` and
`surface_temperature_k` to `1e-12` K or m; energy ledger to `1e-9` relative); constant levels
for 2000 s from a steady start stay at the steady state (`1e-9`); a change of levels triggers
exactly one start-up step; cache cap respected; no wall time in `result()`.
`tests/test_flatness_control.py`: basis orthonormal (weighted); a parabola leaves zero
residual at order 2 and a non-zero one at order 1; the hand case above (`1e-6`); hysteresis;
dwell times (a square-wave demand cannot switch a valve faster than the minimum); dead band;
clipping; supplied actuator removes its own vector; a synthetic first-order plant
(`r_k' = (b*u_k - r_k)/tau`, 4 zones, diagonal influence) with proportional valves reaches
`SETTLED` and with two-level valves and a demand of 0.5 reaches `NOT_SETTLED` with the
switch count at the dwell bound; delay FIFO and filter; history thinning; JSON-safe.

### Documentation
Guide: new 7.12 "Flatness control loop" first part (the law, the three analyst constants,
what it is not); 13. Module docstrings carry the law and the statement that the reports give
the structure only. Gap study: nothing yet (package 4).

### Must not change
No engine module but `roll_thermal.py` (additive class). Five artifact pairs byte-identical.

### Do not
- Do not touch `simulate`, `steady_state` or the stepping classes.
- No model-predictive, decoupling or vendor law; no bending or tilt model.
- No adaptive time step; no wall-clock limit inside the loop.

---

## Package 4 — Closed spray loop in the engine (G5; I5)

### Why
"The loop's valve switching is the event of the short-lived-band model, which today is typed in
by hand" (gap study 2.1 item 4). With a shapemeter (SPEC17 package 4), the controller
(package 3) and the roll model, the tool can run the loop and say whether it settles, what the
valves do, and whether the control made or removed a band.

### Design

**Case schema.** `WIDTH_DEFAULTS` gains `'flatness_control': None`. Validation (messages
"width_model.flatness_control.<key> ..."; the section requires `measurement.shapemeter`:
"width_model.flatness_control needs measurement.shapemeter"):

| key | unit | rule | default |
|---|---|---|---|
| `valve_levels` | - | 2 to 41 strictly increasing values in [0, 1] | required |
| `initial_level` | - | one of `valve_levels` | the highest |
| `minimum_on_time_s`, `minimum_off_time_s` | s | [0, 600] | required |
| `dead_band_i_units` | I-units | (0, 100] | required |
| `control_zone_nozzles` | - | list of non-empty, disjoint lists of nozzle indices, or null | null: groups of `round(cooling_zone_pitch_m/nozzle_pitch_m)` adjacent nozzles from nozzle 0 (one nozzle per zone without `cooling_zone_pitch_m`) |
| `integral_gain` | - | (0, 1] | 0.1 |
| `control_interval_s` | s | [0.5, 60] | 2.0 |
| `low_order_removed` | - | int -1 .. 4 | 2 |
| `target_i_units` | I-units | one value per shapemeter zone in [-200, 200], or null | null (flat) |
| `supplied_actuators` | - | null or 1-4 of `{"name", "influence_i_units_per_unit": [per zone], "minimum", "maximum"}` | null |
| `horizon_s` | s | [600, 7200] | 1800 |
| `shapemeter_distance_m` | m | (0, 20] or null | null (no delay) |
| `display_time_constant_s` | s | [0, 60] | 0 |
| `include_local_sources` | bool | needs `local_coupling` when true | false |
| `provenance` | text | nonempty | required |

**Plant and readings** (`band_width.py`, new function `flatness_control_section(case, w, th,
sp, healthy, actual, local_params)`, called in `width_section` after the events block; needs
the steady thermal solution, shape parameters and the shapemeter, else `NOT_ASSESSABLE` with
the reason):
- Effective nozzle level = the case's own nozzle level (`th.levels`: weak and blocked nozzles)
  times the valve level of its control zone; nozzles in no control zone keep their own level.
- Start: steady state at `initial_level` on every control zone. Flat reference: the steady
  radius growth of a HEALTHY header at the same valve levels (the convention of the stripe
  difference: ground camber and set-up are taken to match the healthy state).
  `dev(z, t) = growth - reference` on the strip samples.
- Linear readings: `I(z) = linear feedback transfer of dev` (`transfer_radius_profile` with the
  feedback, flat entry, mean removed: the computation of
  `band_width._linear_feedback_i_units`, no saturation), then the zone means, neighbour
  spreading and roll-mean removal of `band_sensors` (SPEC17 package 4; expose its zone-edge
  and zone-mean functions if they are private, without changing any number).
- Reading operator `[D, SPEC19]`: the transfer is a symmetric linear map (real, even gains per
  Fourier component; the mean removal is symmetric), so the zone readings are `M*dev` with row
  `j` of `M` = the linear chain applied to the weight row of zone `j` (scale the row by 1e-6
  before the call and by 1e6 after, to stay inside the validation range of the transfer).
  Planner: operator against the direct route agrees to 9e-14 I-units.
- With `include_local_sources`: the zone means of the film and flow-stress terms (a second
  operator built the same way from `transfer_force_profile`) and of the strip-temperature term,
  from `band_local.local_changes` of the surface temperature difference at each control step;
  the loop then controls the as-measured-hot reading.
- Influence matrix: `flatness_control.influence_matrix` with `readings_at(levels)` = steady
  solve plus operator.
- `rt.ControlledRun` with `time_step_s = min(numerics time step, control_interval_s)`,
  `control_interval_s` rounded to a multiple of it; `delay_intervals =
  round(shapemeter_distance_m/(u_exit*control_interval_s))`.

**Result** `width.flatness_control`: the `run_loop` result plus `set_up` (`zones`,
`control_zones` with their nozzle indices and barrel positions, `influence_diagonal`,
`influence_matrix_condition_note`, `reference_basis`, numerics), `provenance`,
`zone_histories` (readings and residuals of at most four zones: largest initial residual,
largest final residual, largest excursion, and the zone over the largest steady stripe;
thinned), `predicted_events` (below), `zone_outcomes`, `low_order`, `basis`, `flags`,
`limitations`.
- `predicted_events`: for each control zone every maximal interval in which its valve level
  differs from `initial_level`: `{'start_s', 'duration_s' (null when still open at the
  horizon), 'nozzle_indices', 'level' (time-weighted mean level in the interval, times the
  nozzles' own levels is NOT applied: this is the valve level), 'changes'}`, at most 50, in the
  key names of `width_model.events` so that a user can copy one into `events` and get the
  existing event analysis for it. `predicted_event_count` is exact.
- `zone_outcomes` per shapemeter zone: residual at the start, largest during the run, at the
  end, `time_above_reporting_threshold_s`; `outcome` in `'REMOVED'` (at or above the 2 I-unit
  reporting threshold at the start, below it throughout the last window), `'MADE'` (below at
  the start, at or above for more than `MADE_BAND_MIN_S = 20.0` s in total `[D, analyst
  choice; the literature band life is 20-120 s, band_width.LITERATURE_BAND_LIFE_S]`),
  `'REMAINS'`, `'NONE'`.
- `low_order`: coefficients at start and end, `edge_to_centre_i_units` at the end, and the
  fixed sentence "This part is left to the bender and the tilt, which this tool does not
  model."
Flags (top level; `band_plain.FLAGS`): `FLATNESS_LOOP_SIMULATED`, `FLATNESS_LOOP_NOT_SETTLED`,
`FLATNESS_LOOP_TRIMMING_LIMIT_CYCLE`, `CONTROL_INCREASES_RESIDUAL`, `CONTROL_ZONE_AT_LIMIT`,
`CONTROL_MADE_BAND`, `LOW_ORDER_FLATNESS_LEFT_TO_BENDING_NOT_MODELLED` (always),
`FLATNESS_LOOP_ON_COARSE_GRID` (axial cell above a quarter of the zone width).
Limitations (fixed): the control law is the tool's own; one header on one roll; linear
readings (a buckled band reads less: package 7); low-order part assumed removed; the weak
nozzle itself is not known to the controller; no feed-forward, no speed or gauge interaction;
the valve events predicted here do not enter `width.thermal_events` or any evidence item.

**Report** (`band_report.py`): block "What the flatness control would do" at the end of
`_measurement_section`: one sentence of set-up; the status sentence from a word table
(`SETTLED`: "The valves stop moving after N s"; `TRIMMING_WITHIN_BAND`: "The valves keep
stepping; the zone error stays below X I-units"; `NOT_SETTLED`: "The loop does not settle:
N valve changes in H s"); a chart of the largest zone error against time; a valve map
(control zones against time, shade = level); the table of zone outcomes; the predicted events
(first ten); the low-order sentence in a `warn` paragraph.

**Demo.** Battery-foil: `"flatness_control": {"valve_levels": [0.0, 0.05, ..., 1.0] (21
values), "initial_level": 1.0, "minimum_on_time_s": 10.0, "minimum_off_time_s": 10.0,
"dead_band_i_units": 2.0, "control_zone_nozzles": null, "integral_gain": 0.1,
"control_interval_s": 2.0, "low_order_removed": 2, "target_i_units": null,
"supplied_actuators": null, "horizon_s": 1800.0, "shapemeter_distance_m": null,
"display_time_constant_s": 0.0, "include_local_sources": false, "provenance": "synthetic:
modulating valves in 5 % steps, 14 zones of two nozzles; an assumption, not a plant setting"}`.

### Worked numbers (planner, `s25/loop_run.py`, `loop_sim2.py`; full numerics; prototype of the law above)
| case | valves | start: largest residual / reading | status | valve changes | last change | last 300 s residual | end: reading |
|---|---|---|---|---|---|---|---|
| battery-foil, 24 zones, 14 control zones | 5 % steps | 19.51 / 24.33 | `SETTLED` | 65 | 1382 s (691 steps) | 2.46 - 2.56 | 59.07 |
| battery-foil | on / off | 19.51 / 24.33 | `NOT_SETTLED`, `CONTROL_INCREASES_RESIDUAL` | 424 | - | 8.6 - 45.0 | 108.8 |
| lengthwise, 29 zones, 16 control zones | 5 % steps | 39.08 / 47.97 | `TRIMMING_WITHIN_BAND` | 119 (165 to 3600 s) | - | 2.47 - 5.05 | 129.0 |
| lengthwise | on / off | 39.08 / 47.97 | `NOT_SETTLED`, `CONTROL_INCREASES_RESIDUAL` | 444 | - | 27.6 - 80.8 | 296.5 |
| lengthwise | 0 / 0.5 / 1 from 0.5 | 67.97 / 84.63 | `NOT_SETTLED` | 293 | - | 12.3 - 38.7 | 130.5 |

Influence diagonal: about -77 to -102 I-units per unit level (battery-foil), -160 to -166
(lengthwise). Battery-foil final levels (zone 0 to 13): 1.0, 0.9, 0.75, 0.75, 0.6, 0.9, 0.7,
0.6, 0.65, 0.65, 0.7, 0.75, 0.8, 1.0; the zone over the weak nozzle (5) stays highest in its
neighbourhood. The implementation need not reproduce the digits (the prototype uses unweighted
zones and its own rounding): assert the status words, the residual at the end within
`[2.0, 3.5]` I-units, the last change between 900 and 1700 s and the valve changes between 40
and 100 for the first row, and pin the implementation's own values.

### Budget
Section 0.3: 12 s at full numerics, 3 s on the quick grid; report both.

### Tests (`tests/test_band_flatness_loop.py`; short roll 0.6 m, 20 mm cells, 6 radial cells, 8 nozzles, 4 control zones, horizon 600 s)
Operator equals the direct route (`1e-9`); influence diagonal negative; a healthy header at
flat reference gives zero readings and no valve change; a weak nozzle with proportional valves
ends `SETTLED` or `TRIMMING_WITHIN_BAND` with the residual reduced by more than half; the same
with on / off valves ends `NOT_SETTLED`; `predicted_events` reproduce the valve log
(durations add up); `zone_outcomes` words on a hand case; `supplied_actuators` with a parabola
vector removes a parabolic target error; validation messages (including the missing
shapemeter); `NOT_ASSESSABLE` without shape parameters; with the key absent everything but
`inputs` and the entry is equal and hypotheses are identical; `thermal_events` identical with
and without the key; report renders. Module time under 45 s (measure the set-up first).

### Documentation
Guide 7.12 (the engine side, the table above from regenerated runs, findings 1 in full:
on / off valves, the unreachable residual, the low-order drift; how to read `predicted_events`
and how to copy one into `events`); 3.9 (demo); 5.3 (which plant documents hold valve logic,
dead band and minimum times); 7.4 (one sentence: events can now be predicted, the typed ones
still drive the evidence); 12; 13; 14. README: two sentences. Gap study section 11: G5
`LOOP_MODEL_OPT_IN` (spray zones only; analyst control law; bending, tilt and
vendor rules open), C7 unchanged.

### What changes, what must not
Artifacts: additive; the battery-foil demo gains the section (run time about +8 s) and flags.

### Do not
- Do not write predicted events into `width_model.events` or `width.thermal_events`.
- Do not give the predicted events to `_h_zone` or any other rule (open decision 3).
- Do not hide `NOT_SETTLED` behind a longer horizon or a retuned gain.

---

## Package 5 — Zone step test emulation (A6; X5)

### Why
Gap A6: "Emulate the plant test: one zone on / off for the plant's test duration, add transport
delay `L/u` and the shapemeter filter, fit first order plus dead time to the modelled flatness,
report the fitted constant beside the published one; repeat with A1 / A2 switched on."

### Design

**Case schema.** `WIDTH_DEFAULTS` gains `'zone_step_test': None` (needs
`measurement.shapemeter`; messages "width_model.zone_step_test.<key> ..."):

| key | unit | rule | default |
|---|---|---|---|
| `nozzle_indices` | - | non-empty list of nozzle indices | required |
| `level` | - | [0, 1] | 0.0 |
| `hold_s` | s | [10, 3600] | 60 |
| `fit_windows_s` | s | 1-6 increasing values in [10, hold_s] | `[20, 40, 60]` cut at `hold_s` |
| `time_step_s` | s | [0.1, 5] | 0.5 |
| `shapemeter_distance_m` | m | (0, 20] or null | null |
| `display_time_constant_s` | s | [0, 60] | 1.0 |
| `provenance` | text | nonempty | required |

**Run** (`band_width.zone_step_test_section`, after the flatness-control block): from the
steady state of the case (`actual`), the named nozzles go to `level` for `hold_s`
(`rt.ControlledRun`). At every step: zone readings of the radius difference from the starting
state through the operator of package 4; the reading of the shapemeter zone that holds the mean
position of the nozzles, minus the roll mean. With `local_coupling`: the film, flow-stress and
strip-temperature zone terms of that step. Series: `roll_growth_only`, `mechanical_net`
(roll + film + flow), `as_measured_hot` (+ strip temperature); the last two only with
`local_coupling`. Each series is delayed by `shapemeter_distance_m/u_exit` (linear
interpolation in time) and filtered `y <- y + (dt/(tau + dt))*(x - y)`.

**Fit** `flatness_control.fit_first_order_dead_time(time_s, values, window_s)`
`[D, SPEC19: least squares on a fixed grid; no plant fitting protocol is recorded]`: model
`y = K*(1 - exp(-(t - theta)/tau))` for `t > theta`, else 0; `theta` in steps of the series
time step from 0 to `min(window/2, 30 s)`; `tau = 1.08^k` s for `k = 0..99` (1 s to 2038 s);
`K` by linear least squares for each pair; the pair with the smallest sum of squares (ties:
smaller `tau`). Returns `gain_i_units`, `time_constant_s`, `dead_time_s`, `rms_i_units`,
`value_at_end_i_units`, `time_to_63_percent_of_end_s`, flags
`FITTED_TIME_CONSTANT_AT_SEARCH_LIMIT`, `STEP_RESPONSE_NOT_FIRST_ORDER` (rms above 5 % of the
value at the end).

**Result** `width.zone_step_test`: `status`, `provenance`, `nozzle_indices`,
`shapemeter_zone_index`, `transport_delay_s`, `display_time_constant_s`, `series` (per name:
thinned history and `fits` per window), `surface_temperature_change_k` (thinned history under
the zone), `published` (`{'time_constant_s': 20.0, 'source': roll_thermal.SOURCES[
'dohmae_2012'], 'note': 'first-order flatness response to one cooling zone, identified on a
plant; test length, zone width and filter not recorded in the project'}`),
`ratio_to_published` per series and window, `finding` (generated sentence: "A test of W s
would fit T1 s from roll growth alone and T2 s as measured hot; the published value is 20 s."),
`basis`, `flags` (`ZONE_STEP_TEST_EMULATED`), `limitations` (the coupling factor, inlet weight
and display filter are assumptions; the fit depends on the window, which is the point; one
header; no controller acting during the test). Report: a chart of the three series with their
60 s fits and the table of fitted constants, in the flatness-control block.

**Demo.** Battery-foil: `"zone_step_test": {"nozzle_indices": [18, 19], "level": 0.0,
"hold_s": 120.0, "fit_windows_s": [20, 40, 60, 120], "time_step_s": 0.5,
"shapemeter_distance_m": 2.0, "display_time_constant_s": 1.0, "provenance": "synthetic: the
zone of the demo's valve event; 2 m to the shapemeter and a 1 s display filter assumed"}`.

### Worked numbers (planner, `s25/steptest.py`; full numerics; transport delay 0.15 s neglected; strip term = 2.36 I-units/K x coupling x zone mean of the surface change, film and flow terms not included)
| demo, zone | series | 20 s | 40 s | 60 s | 120 s | 600 s |
|---|---|---|---|---|---|---|
| battery-foil, nozzles 18-19, shapemeter zone 17 | roll growth only | 63.8 s | 63.8 | 74.4 | 101.3 | 173.5 |
| | + strip temperature, coupling 1.0 | 16.0 | 25.3 | 34.5 | 59.1 | 137.8 |
| | + strip temperature, coupling 0.5 | 23.5 | 34.5 | 46.9 | 68.9 | 160.7 |
| lengthwise, nozzles 20-21, zone 19 | roll growth only | 109.4 | 93.8 | 93.8 | 118.1 | 202.4 |
| | + strip temperature, coupling 1.0 | 29.6 | 43.4 | 59.1 | 86.8 | 187.4 |

Battery-foil: surface under the zone +3.74 / 4.92 / 6.30 / 8.70 / 11.54 K at 5 / 10 / 20 /
60 / 300 s; roll-growth reading 5.79 / 10.72 / 19.24 / 44.33 / 108.15 I-units. Dead times 0
to 0.5 s. The fitted constants sit on a grid with ratio 1.08: assert them within 10 % and pin.

### Tests (`tests/test_band_flatness_loop.py`, same short roll)
`fit_first_order_dead_time` recovers `K = 10`, `tau = 20 s`, `theta = 2 s` from exact samples
(`tau` within one grid step, `theta` exact, rms below 0.05); a ramp fits `tau` at or near the
window-dependent value and sets no limit flag below 2038 s; a response slower than the grid
sets the limit flag. Section: fitted constant grows with the window; `as_measured_hot` fits a
shorter constant than `roll_growth_only` for the shortest window; series absent without
`local_coupling`; absent key changes nothing; validation.

### Documentation
Guide 7.1 and 14: the open "20 s" paragraph is rewritten around the table above (finding 2:
what is and is not shown); 7.12 pointer; 5.3 (how to describe the plant's own test: zone,
duration, shapemeter distance, display filter); 12; 13. Gap study section 11: A6
`SCREENING_VERSION` (emulation with assumed filter and coupling; no plant protocol), X5 row
extended, G8 pointer.

### What changes, what must not
Artifacts: additive (battery-foil gains the section; about +2 s).

### Do not
- Do not tune any input so that 20 s comes out.
- Do not call the result an explanation of the discrepancy.

---

## Package 6 — Buckling: wavelength under tension (G4 part 1; G16)

### Why
Gap G4 (SS-S12 to SS-S20): "1D-in-width Ritz or Hermite FE, harmonic along the length,
`sigma_res(z)` + tension, minimise over wavelength". X11: the present mode (half-wave = buckle
width, k = 4, simply supported band edges) is contradicted for the wavelength. The reports
describe the method [SS-S15 EX, SS-S12 AB] and give no equations; they are derived here.

### Model (module docstring; `[D, re-derived in SPEC19]`)
Long strip, `x` along rolling, `z` across the width on `[z_a, z_b]`, thickness `t`, bending
stiffness `D = E*t^3/(12*(1 - nu^2))`. Membrane pre-stress: longitudinal only,
`sigma(z) = sigma_T + lambda*sigma_res(z)` (tension positive; `sigma_res` has zero mean; no
lateral and no shear pre-stress). Mode `w(x, z) = f(z)*cos(k*x)`. Second variation of the
potential energy per unit length, averaged over `x` (a factor 1/4 dropped):

    P(f, k) = D*Int[ f''^2 + k^4*f^2 - 2*nu*k^2*f*f'' + 2*(1 - nu)*k^2*f'^2 ] dz
            + t*k^2*Int[ sigma(z)*f^2 ] dz

from `w_xx = -k^2*f*cos`, `w_zz = f''*cos`, `w_xz = -k*f'*sin` in the plate energy
`(D/2)*[(w_xx + w_zz)^2 - 2*(1 - nu)*(w_xx*w_zz - w_xz^2)]` and the membrane term
`(t/2)*sigma*w_x^2`. The flat strip is stable while `P >= 0` for every `f` and `k`. The
`f*f''` and `f'^2` terms are kept as they stand: their sum is a boundary term that vanishes for
supported edges and not for free ones. Critical multiplier at one `k`: the smallest positive
`lambda` of `A(k)*a = lambda*G(k)*a`, `A` = bending plus `t*k^2*sigma_T*Int f^2` (positive
definite for `k > 0`, `sigma_T >= 0`), `G = -t*k^2*Int sigma_res*f^2` (indefinite). Critical
state of the strip: the minimum over `k`.

### Numerical method (copy `s25/buck.py`; this text is the specification)
- Elements: Hermite cubics between the given nodes, unknowns `f` and `f'` per node; `sigma_res`
  linear inside an element; all element integrals by 4-point Gauss quadrature (exact). Edge
  conditions per side: `'free'` (nothing fixed), `'simply_supported'` (`f = 0`), `'clamped'`
  (`f = f' = 0`). Symmetric banded storage, half bandwidth 3.
- `mu_max` = the largest eigenvalue of `G*a = mu*A*a` by bisection on the inertia: the number
  of eigenvalues above `mu` equals the number of positive pivots of the `L*D*L^T` factors of
  `G - mu*A` (Sylvester; banded, no pivoting; a zero pivot is replaced by `1e-300`). Bracket
  `[0, q_max/(D*k^2/t + sigma_T)]`, `q_max = max(-sigma_res)` (Rayleigh bound; doubled while a
  positive pivot remains); relative tolerance `1e-6`. No positive pivot just above 0: no
  buckling at this `k`. `lambda(k) = 1/mu_max`.
- Search over `k`: `coarse = 14` values, geometric between `pi/L_long` and `pi/L_short`
  (`half_wave_range_m = (L_short, L_long)`, default `(4*smallest node spacing,
  2*(z_b - z_a))`); golden section in `ln k` between the neighbours of the best, `refine = 10`
  steps. A best value at an end of the range is returned with `at_search_limit`.
- Mode: three inverse iterations of `(G - mu*(1 + 1e-7)*A)*x = A*x_prev` (banded elimination
  with partial pivoting) from a fixed start vector `sin(1 + 0.7*i)`; normalised to
  `max|f| = 1`, positive at the peak.

### Public API (`physicroll/strip_buckling.py`)
```python
STATUS = 'UNVALIDATED_LINEAR_BUCKLING_OF_A_LONG_STRIP'
EDGES = ('free', 'simply_supported', 'clamped')
def critical_mode(z_m, residual_stress_pa, *, thickness_m, youngs_modulus_pa, poisson_ratio,
                  mean_tension_pa=0.0, edges=('free', 'free'), half_wave_range_m=None,
                  coarse=14, refine=10, tolerance=1e-6) -> dict
def multiplier_at(z_m, residual_stress_pa, wavenumber_per_m, *, ...same material keys...) -> dict
```
Checks: `z_m` 3 to 400 strictly increasing nodes; stresses in `[-5e9, 5e9]`; tension
`[0, 2e9]`; `coarse` 4-40, `refine` 0-30. Result of `critical_mode`: `status`,
`critical_multiplier` (null with `'NO_COMPRESSION_NO_BUCKLING'` when nothing buckles),
`utilisation` (`1/critical_multiplier`; at or above 1 the given profile buckles),
`wavenumber_per_m`, `half_wavelength_m`, `mode` and `mode_slope` at the nodes,
`mode_peak_position_m`, `mode_width_10_percent_m` and `mode_width_50_percent_m` (extent of the
nodes with `|f|` at or above that share), `half_wave_over_mode_width`, `scan`
(`[{'half_wavelength_m', 'critical_multiplier'}]`), `at_search_limit`
(`'LONGEST' | 'SHORTEST' | None`), `edges`, `basis`, `flags`
(`BUCKLING_MODE_AT_LONGEST_HALF_WAVE_SEARCHED`, `..._SHORTEST_...`), `limitations` (linear
bifurcation of a flat, infinitely long strip; longitudinal pre-stress only; no lateral stress,
no shear; elastic; the wavelength of a wave seen after buckling can differ from the critical
one).

### Worked numbers (planner, `s25/buck.py`, `buck_ss.py`, `buck_foil.py`)
Closed forms (steel 0.5 mm, `E` 210 GPa, `nu` 0.3, width 150 mm, uniform compression):

| case | exact | solver |
|---|---|---|
| simply supported both edges | `4*pi^2*D/(t*b^2) = 8435559.3 Pa`, half-wave `b` | 8435569.6 Pa with 16 elements (+1.2e-6), half-wave 1.0005 `b` (search tolerance); 8 elements +8.9e-6 |
| the same with 20 MPa tension | exact + 20e6 = 28435559.3 Pa | 28435504.0 (-1.9e-6) |
| clamped both edges | coefficient 6.97, half-wave 0.66 `b` [M: textbook values, not in the reports] | 6.9710, 0.6599 `b` |
| simply supported / free, half-wave fixed at 20 `b` | `0.425 + (b/a)^2 = 0.4275` [M] | 0.42796 |

Benchmark rows (inputs marked ASSUMED are not in the reports):

| id | inputs | project value | reference | verdict |
|---|---|---|---|---|
| `SS-V2-LOCAL-PLATE` | steel 0.5 mm, `E` 210 GPa, `nu` 0.3 (ASSUMED, as SS-V2 of SPEC17), local plate 150 mm, no tension, compression `exp(-4*ln2*((z - 75 mm)/75 mm)^2)` per I-unit (half-peak width 75 mm ASSUMED), 60 elements | 5.341 I-units simply supported, 8.649 clamped; half-waves 149.4 and 99.4 mm | computed 5.3 and 8.92 I-units [SS-S19 FT, formulas garbled]; measured half-wave 60 mm | `INDICATIVE_ASSUMED_INPUTS`; ratios 1.008 and 0.970 inside the band; half-wave 2.49 and 1.66 times the measured one |
| `SS-V2-WIDE-STRIP` | the same strip 1000 mm wide, free edges, mean-free Gaussian loose band of half-peak width 75 mm at the centre, tension 10 and 30 MPa (ASSUMED), 200 elements | critical peak 12.30 and 27.22 I-units; half-wave 176.1 and 128.6 mm; mode width (10 %) 220 and 160 mm; ratio 0.80 | waves at 7.5-8 I-units; half-wave 60 mm on a 150 mm buckle (0.40) | `RECORDED_DISCREPANCY` (mode ratio 2.0 times the measured one; the test is named `test_ss_v2_wide_strip_recorded_discrepancy_half_wave_is_twice_the_measured_share`) |
| `SS-V3-WIDE-STRIP` | aluminium 0.3 mm, `E` 70 GPa, `nu` 0.33, 270 mm wide, free edges, half-peak width 50 mm, tension 5 and 15 MPa (ASSUMED), 108 elements | critical peak 18.85 and 42.80 I-units; half-wave 91.9 and 68.9 mm; mode width 115 and 85 mm; ratio 0.80, 0.81 | buckle width 105 mm, wavelength about 75 mm (0.357) | `RECORDED_DISCREPANCY` |

Without tension both wide strips buckle in the longest half-wave searched (a whole-sheet mode)
at 0.4 to 2.4 I-units: record it in the notes. `NOT_ENCODED`: `SS-V1` becomes "geometry and
temperatures are in the study; the bifurcation force is not, so there is nothing to compare";
`SS-V4` "needs the stress profile of the paper".

### Tests (`tests/test_strip_buckling.py`)
The four closed forms (`1e-5`, `1e-5`, 0.2 %, 0.2 %); convergence 8 -> 16 elements; tension
shifts a uniform-compression plate by exactly the tension; mesh independence of a Gaussian
case (120 against 240 elements, 0.5 %); `multiplier_at` equals the scan value; a profile
without compression returns the no-buckling status; search-limit flags; a mirrored profile
gives the mirrored mode; uniform (non-uniform) node spacing gives the same answer to 0.1 %;
rejections; JSON-safe. `tests/test_benchmarks.py`: the three rows (pins after checking the
numbers above to 0.5 %), verdict literals. Module time below 30 s (the 200-element case takes
0.4 s).

### Documentation
Guide: new 7.13 "Buckling with a wavelength search (`strip_buckling.py`)": model, method,
closed forms, the three benchmark rows and finding 3 in full, "not used by any band state".
13 (rows); 15 (SS-S12, SS-S13, SS-S15, SS-S19 with their tags). Gap study section 11: G16 row
extended with the three ids.

### Must not change
No existing module except `benchmarks.py`. Five artifact pairs byte-identical.

### Do not
- Do not adjust the assumed half-peak width or tension to move a ratio; record what the stated
  assumptions give.
- No edge-restraint coefficient "between simply supported and clamped": the published one is
  not in the reports.
- Do not call this model from `flatness_from_elongation`.

---

## Package 7 — Post-buckling amplitude, saturated stress, dead load; engine (G4 part 2; I12, X11, X13)

### Why
Gap G4: "post-buckling amplitude; dead load on a table; stress saturation (Counhaye rule: clip
stress at `-sigma_cr`)". X13 / C6: with dead load a strip lies flat below a residual-stress
limit [SS-S14 AB]. I12: a buckled band no longer carries the stress the linear profile gives
it, which changes what the shapemeter reads. Neither Koiter's expansion nor the published
table model is in the reports; a one-mode model is derived that contains the saturation rule
as a result.

### Model (`[D, re-derived in SPEC19]`, docstring of the new functions)
Fibre membrane model, as the project's residual stress `sigma_res = -E*(eps - mean)` already
is: each fibre carries longitudinal stress only, uniform along `x`. With a wave
`w = a*f(z)*cos(k*x)` of the critical mode shape, a fibre's arc is longer than its chord by
the `x`-average of `w_x^2/2`, `k^2*a^2*f^2/4`, so at fixed mean tension

    sigma(z; a) = sigma_T + sigma_res(z) + (E*k^2*a^2/4)*(f(z)^2 - m),   m = (1/W)*Int f^2 dz

Energy per unit length (bending as package 6, membrane `(t/(2E))*Int sigma^2`, dead tension):

    Pi(a) = -(t*k^2/4)*(N - R)*a^2 + (E*t*k^4*Phi/32)*a^4
    N = -Int (sigma_T + sigma_res)*f^2 dz        (net compression carried by the mode)
    R = D*B(f, k)/(t*k^2) = -Int (sigma_T + lambda_c*sigma_res)*f^2 dz   (its value at buckling)
    Phi = Int f^4 dz - (Int f^2 dz)^2/W

    a^2 = 4*(N - R)/(E*k^2*Phi)      for N > R, else 0;  peak to valley H = 2*a

Self-check `[D]`: a top-hat mode over a narrow band of compression `sigma_c` gives
`(pi*H/(2*L_w))^2 = (sigma_c - sigma_cr)/E` with `L_w = 2*pi/k`: the I-unit wave formula
[V: QCA-1; `strip_shape.i_units_from_wave`], and `sigma(z; a) = -sigma_cr` inside the band: the
Counhaye rule [SS-S8 EX], here a consequence. Limits to state: mode shape frozen at the
critical one; fibres independent (no in-plane shear, no lateral stress), which makes the wave
softer than a plate's: the amplitude is an upper estimate; one mode.

**Dead load on a rigid table** `[D, re-derived in SPEC19]`. The sheet can only lift:
`w = a*|f(z)|*(1 + cos(k*x))`, wave amplitude `a`, peak to valley `2*a`, mean lift `a*|f|`.
Added terms per unit length: gravity `g1*a`, `g1 = rho*g*t*Int |f| dz`; bending of the mean
lift, which adds `R_s = 2*D*Int f''^2 dz/(t*k^2)` to `R`. With `c2 = t*k^2*(N - R - R_s)/2`,
`c4 = E*t*k^4*Phi/8`:

    Pi_t(a) = -(c2/2)*a^2 + (c4/4)*a^4 + g1*a

The sheet lifts when the lowest `Pi_t` is below 0 (the flat state). At the limit `Pi_t = 0`
and `dPi_t/da = 0` together give `a^2 = 2*c2/(3*c4)` and `g1 = c2*a/3`, hence

    lifts  <=>  N - R - R_s >= G(k) = (2/(t*k^2))*(3*g1*sqrt(3*c4/2))^(2/3)

Scale of the residual stress at which a mode of wavenumber `k` lifts (no tension):
`s_lift(k) = (R + R_s + G(k))/(-Int sigma_res*f^2 dz)`; the lift limit is the minimum over `k`
(gravity favours short waves, bending long ones, so the minimum is interior unless the profile
is very thin). Wave height on the table: the largest root of `c4*a^3 - c2*a + g1 = 0` (Newton
from `sqrt(c2/c4)`). `ALUMINIUM_DENSITY_KG_M3 = 2700.0` `[M: textbook value, not in the
reports]`, `g = 9.81`. Approximation to state: the weightless mode shape at each `k` is used.

### Design
`strip_buckling.py`:
```python
def post_buckling(z_m, residual_stress_pa, mode_result, *, thickness_m, youngs_modulus_pa,
                  mean_tension_pa=0.0) -> dict
def dead_load_lift(z_m, residual_stress_pa, *, thickness_m, youngs_modulus_pa, poisson_ratio,
                   density_kg_m3=ALUMINIUM_DENSITY_KG_M3, half_wave_range_m=None, points=24) -> dict
```
`post_buckling`: `amplitude_m`, `peak_to_valley_m`, `wavelength_m`, `wave_i_units`
(`ss.i_units_from_wave`), `saturated_stress_pa`, `saturated_i_units`
(`-1e5*(sigma - sigma_T)/E`, what a stress-measuring roll would be offered), `state`
(`'BUCKLED' | 'FLAT'`). `dead_load_lift`: `scale_to_lift`, `half_wavelength_m`,
`peak_to_valley_on_table_m` (0 when the scale is above 1), `weightless_peak_to_valley_m`,
`scan`, `state` (`'LIFTS' | 'LIES_FLAT'`), `at_search_limit`, flags
`DENSITY_FROM_MEMORY_DEFAULT`, `DEAD_LOAD_MODE_AT_SEARCH_LIMIT`.

Engine. `band_diagnosis.OPTION_OPTIONAL` gains `buckling_model`, values
`BUCKLING_MODELS = ('sine_mode', 'sine_mode_and_fe')`, kept in the validated case only when
given (as `thermal_sensitivity`); message "model_options.buckling_model must be one of ...".
Question (G''6): id `buckling_model`, group `Model settings`, "Also compute waves with a
wavelength search?", help "Slower. Adds wavelength, wave height and what lies flat on a table
beside the standard result; the standard result is unchanged.", words
`{'sine_mode': 'Standard', 'sine_mode_and_fe': 'Standard plus wavelength search'}`.
New function `band_width.buckling_fe_section(shape, events, sp, option)` after the shape block:
`width.shape.buckling_fe` = `not_supplied('model_options.buckling_model is sine_mode')` by
default; with the option, for the steady profile and for each event's `peak_shape`:
- profile: `i_units_linear_feedback` (the profile BEFORE the project's own saturation scaling:
  this model has its own saturation, and the comparison is the test of X10), on at least a
  `band_width.ONSET_GRID_M` (10 mm) grid by taking every n-th sample; `sigma_res = -E*1e-5*I`.
- `in_mill`: `critical_mode` at the exit tension, free edges, default half-wave range;
  `post_buckling`.
- `released`: tension 0, half-waves up to the strip width (`RELEASED_SAMPLE_LENGTH_FACTOR =
  1.0` x width `[D, analyst choice: a square sample]`); flagged at the search limit (it almost
  always is: a whole-sheet mode).
- `on_table`: `dead_load_lift`, with `lift_limit_peak_i_units = scale_to_lift*profile peak`.
- `beside`: the present band at the mode's peak position (`band_width._band_at`): its `state`,
  `state_after_tension_release`, `buckling_utilisation`, `effective_buckling_width_m`; and
  `agrees_in_mill`, `agrees_after_release` (the table state against the present after-release
  state).
Flags: `BUCKLING_FE_REPORTED_BESIDE_SINE_MODE`;
`BUCKLING_FE_IN_MILL_STATE_DIFFERS_FROM_SINE_MODE`;
`DEAD_LOAD_KEEPS_REPORTED_BAND_FLAT_ON_TABLE` (present after-release state manifest, table
state `LIES_FLAT`). `band_sensors.shapemeter_profiles` appends `steady_saturated`
(`saturated_i_units`) when the in-mill state is `BUCKLED`.
Report: in `_width_section`, table "Waves with a wavelength search" (state in the mill,
half-wave, wave height; on a table: limit, half-wave, height; the present states beside) and
the sentence "The standard result above is the one the diagnosis uses."

### Worked numbers (planner; `i_units_linear_feedback` of the committed artifacts, every second sample, i.e. 10 mm)
| demo | in the mill | released, weightless, half-wave up to the width | on a table |
|---|---|---|---|
| battery-foil (30 um, 40 MPa, profile peak 25.09) | multiplier 2.3013, utilisation 0.435, `FLAT`; half-wave 40.1 mm; mode at 0.623 m, 30 mm wide | utilisation 29795 at 1.19 m (search limit); peak to valley 20.8 mm; reading at the peak 17.3 instead of 25.1 I-units | lifts above 0.75 I-units peak (scale 0.0298, at the shortest half-wave searched, 30 mm); peak to valley 0.72 mm |
| lengthwise (0.21 mm, 30 MPa, profile peak 50.59) | multiplier 0.8981, utilisation 1.113, `BUCKLED`; half-wave 107.6 mm; mode 130 mm wide at 0.672 m; amplitude 0.5845 mm (peak to valley 1.17 mm); reading 43.6 instead of 50.6 I-units | utilisation 1799 at 1.49 m (search limit); peak to valley 33.9 mm | lifts above 2.20 I-units peak (scale 0.0435); half-wave 90 mm; peak to valley 2.99 mm |

Beside, for the lengthwise demo: the project's saturation step raises the same band to
147.5 I-units with utilisation 1343; the wavelength search on the unsaturated profile has it
just buckled (1.11) with a 1.2 mm wave. Both are printed.

### Tests
`tests/test_strip_buckling.py`: top-hat self-check (uniform compression over a simply
supported plate standing for the band: `(pi*H/(2*L_w))^2*E` equals `sigma_c - sigma_cr` to
`1e-6`; saturated stress equals `-sigma_cr` to `1e-6` relative in the band); amplitude zero at
and below the critical state and growing as the square root above it; mean of the saturated
stress equals the tension (`1e-9`); dead load: `s_lift` above the weightless multiplier for
every `k`; heavier or thicker sheet raises the limit; the limit condition reproduces
`Pi_t = 0` and `dPi_t/da = 0` (`1e-6`); table height below the weightless height; the two demo
rows from the committed profiles (2 % after pinning). `tests/test_band_lengthwise.py`
(coarse): with the default option the section is `not_supplied` and the result equals the run
before the package; with the option every other key is unchanged and hypotheses are identical.
`tests/test_band_plain.py` passes (question, choices, flags).

### Documentation
Guide 7.13 second part (derivation, self-check, the table, findings 3 and 4, X10 beside X11
and X13: what the model changes and what it does not); 7.2 pointers; 3.5 (after release:
"at sheet gauge a band below about N I-units lies flat on a table; at foil gauge it does not",
numbers from regenerated runs); 5.3; 12; 13; 14. Gap study section 11: G4 `COMPUTED_BESIDE`
(opt-in; one mode; fibre membrane; no tension-release path, no finite sample, no measured
case), X11 and X13 `TEXT_CORRECTED`.

### What changes, what must not
Artifacts: additive (`width.shape.buckling_fe` not supplied everywhere; no scenario sets the
option). No band state, onset, gauge-trend row or evidence item reads the section.

### Do not
- Do not feed `saturated_i_units` into the thickness transfer (X10: the bite is hardly
  changed by buckling [SS-S8 EX]).
- Do not replace `state` or `state_after_tension_release`.
- No amplitude without the "upper estimate" wording.

---

## Package 8 — Width-coupling kernel: an independent check of the exit-tension feedback (G3 kernel; X17)

### Why
Gap G3: the exit-tension feedback "dominates every thin-gauge result (76-386 x Q), yet it is
pointwise and uses the far-field stress"; X17: "not contradicted, not supported; independent
check through G3". The row asks for "a plane-stress Airy solution for the span that maps the
bite-exit velocity profile to the far-field stress". Derived here; it needs nothing but the
eight bite sensitivities the engine already has.

### Model (`[D, re-derived in SPEC19]`, docstring in `strip_shape.py`)
Per Fourier component across the width, `cos(kappa*z)`, small perturbations of a uniform pass.
Unknowns: `dh` exit thickness, `ds_x`, `ds_e` exit and entry tensile stress AT the bite,
`d_x`, `d_e` relative exit and entry speed.

- (K1) Bite force per width: `dF' = -Q*dh - N_x'*ds_x - N_e'*ds_e`, `N_e' = -F_se/width`.
- (K2) Bite slip: `d_x = f_h*dh + f_sx*ds_x + f_se*ds_e` (roll speed uniform).
- (K3) Mass flow with the shape-disturbing coefficient: `d_e = d_x + xi*dh/h`.
- (K4) Exit span. The fibre leaves with a length excess `e = -xi*dh/h`. Far downstream all
  fibres move at one speed and the stress is `s_inf = -E*e` (the project's pointwise value).
  Near the bite a decaying plane-stress field `phi = (a + b*x)*exp(-kappa*x)*cos(kappa*z)` is
  added; in a steady flow the speed excess equals the total strain, so
  `d_x = chi*(ds_x - s_inf)/E`, with `chi = E*eps_xx/sigma_xx` of that field at `x = 0`.
- (K5) Entry span (flat incoming strip): `d_e = chi*ds_e/E`.
- Closure for `chi` (how the strip is held laterally at the bite). From
  `sigma_xx = -kappa^2*(a + b*x)*exp(..)`, `sigma_zz = (kappa^2*(a + b*x) - 2*b*kappa)*exp(..)`,
  `E*u_z = ((1 + nu)*kappa*(a + b*x) - 2*b)*exp(..)*sin(kappa*z)`:

  | closure | condition at `x = 0` | `b` | `chi` | `nu` 0.33 |
  |---|---|---|---|---|
  | `no_lateral_velocity` (used for the kernel level) | `d(u_z)/dx = 0`: the strip leaves the bite moving straight | `kappa*a*(1 + nu)/(3 + nu)` | `(3 - nu)*(1 + nu)/(3 + nu)` | 1.066396 |
  | `uniaxial` | `sigma_zz = 0` | `kappa*a/2` | 1 | 1.0 |
  | `shear_free` | `sigma_xz = 0` | `kappa*a` | `1 - nu` | 0.67 |

Solution (with one `chi` on both sides):

    A_x = ds_x/dh = ( f_h + chi*xi/h + f_se*(E*xi/h)*(1 - chi)/chi ) / ( chi/E - f_sx - f_se )
    A_e = ds_e/dh = A_x + (E*xi/h)*(1 - chi)/chi
    K_kernel = N_x'*A_x + N_e'*A_e          (feedback stiffness per width, Pa)
    K_pointwise = N_x'*E*xi/h               (the present model)
    Q_eff = Q + K_kernel

No wavenumber appears: a half-infinite span has no length but `1/kappa`. The span length `L`
enters only when `kappa*L < 3` (flag `SPAN_SHORTER_THAN_DEVELOPMENT_LENGTH`; not the case for
any band). What does depend on `kappa` is where the far-field stress is reached:
`sigma_xx(x) = s_inf + (ds_x - s_inf)*(1 + c*kappa*x)*exp(-kappa*x)`, `c = b/(kappa*a)`; within
5 % of the far field at `kappa*x = 3.94` for `c = 0.40`, i.e. 0.63 wavelengths (SS-S22 EX: the
profile "keeps changing outside the bite"). A vanishing or negative denominator, or
`1 + 2*C*Q_eff <= 0`, means the linear steady state does not exist for that closure: reported,
never clipped.

### Design
`strip_shape.py`:
```python
LATERAL_CLOSURES = ('no_lateral_velocity', 'uniaxial', 'shear_free')
def span_strain_ratio(poisson_ratio, closure) -> float
def width_coupling_kernel(*, strip_stiffness_per_width_pa, exit_tension_force_sensitivity_per_width_m,
        entry_tension_force_sensitivity_per_width_m, dslip_dexit_thickness_per_m,
        dslip_dexit_tension_per_pa, dslip_dentry_tension_per_pa, exit_thickness_m,
        strip_youngs_modulus_pa=ALUMINIUM_E_PA, strip_poisson_ratio=ALUMINIUM_NU, xi=1.0,
        closure='no_lateral_velocity') -> dict
def stress_development_fraction(distance_m, wavelength_m, poisson_ratio, closure) -> float
```
`transfer_radius_profile` and `thermal_stripe_flatness` gain ONE optional argument,
`feedback_stiffness_per_width_pa=None`: when given (and `exit_tension_force_sensitivity_...`
is None; both given is a `ValueError`) `Q_eff = Q + that value` for every component but the
mean, exactly where the pointwise term is added today. Default: bit-identical results (the
existing tests decide).

Engine (`band_width.py`): `shape_params` gains the three slip sensitivities and `N_e'` from
the bite (None with supplied shape inputs). New function `width_coupling_section(z, dev, sp)`
called after `shape_levels` for the steady profile: `width.shape.width_coupling` =
`{'status', 'closures': [kernel dict per closure, each with 'exit_stress_per_thickness_pa_m',
'entry_stress_per_thickness_pa_m', 'feedback_stiffness_per_width_pa', 'ratio_to_pointwise',
'effective_stiffness_over_strip_stiffness', 'defined'], 'pointwise': {...},
'kernel_level': {'closure', 'i_units', 'peak_i_units', 'bands', 'status', 'released_status',
'peak_ratio_to_linear_feedback'} (linear, no saturation; `flatness_from_elongation` as the
other levels), 'development': {'wavelength_m' (twice the half-peak width of the largest
band), 'distance_to_95_percent_m', 'fraction_at_shapemeter' (null without a
`shapemeter_distance_m` in `flatness_control` or `zone_step_test`)}, 'basis', 'flags',
'limitations'}`; `NOT_ASSESSABLE` without a derived bite or without a steady profile.
`gauge_trend.rows[i]` gain `kernel_feedback_ratio_to_pointwise` (the closure used; null when
not defined). Flags (top level; `band_plain.FLAGS`): `WIDTH_COUPLING_KERNEL_REPORTED`,
`KERNEL_FEEDBACK_BELOW_HALF_OF_POINTWISE`, `KERNEL_CLOSURES_DISAGREE_IN_SIGN`,
`KERNEL_STEADY_STATE_NOT_DEFINED`. Limitations: linear; lateral closure assumed; half-infinite
spans; slip sensitivities of a constant-friction bite (mattress or reduced half-space at foil
gauge); roll stack and closed gap absent; the three present levels, the band states and every
evidence item still use the pointwise feedback.
Report: one row "with width coupling (kernel)" under the three levels of the stripe table, and
a `warn` paragraph with the three ratios: "An independent estimate of the tension feedback
gives N1 of the value used above (N2 and N3 with two other assumptions about how the strip is
held at the roll gap). With it the band would read P I-units instead of Q."

### Worked numbers (planner, `s25/kernel.py`; sensitivities of the committed artifacts)
| demo | `Q` Pa | pointwise | `no_lateral_velocity` | `uniaxial` | `shear_free` |
|---|---|---|---|---|---|
| lengthwise (0.21 mm, Hitchcock bite) | 1.186e10 | 1.009e12 | 6.957e11, ratio 0.690; `A_x*h/E` 0.260, `A_e*h/E` 0.198 | 2.432e11, ratio 0.241 | -3.446e12 (not defined) |
| battery-foil (30 um, mattress bite) | 7.389e10 | 1.472e13 | 1.500e12, ratio 0.102; `A_x*h/E` 0.0864, `A_e*h/E` 0.0241 | 1.280e11, ratio 0.0087 | -1.074e13 (not defined) |

Single-gain estimate of the steady peak (rigid bound divided by `1 + 2*C*Q_eff` at the stripe's
dominant wavelength): lengthwise 44.3 against 31.0 I-units pointwise (1.43 times);
battery-foil 210 against 22.8 (9.2 times). The profile values will differ; assert the stiffness
numbers to 0.1 % and the peak ratios within 15 %.

### Tests (`tests/test_strip_shape.py`, new class; `tests/test_band_lengthwise.py`)
`span_strain_ratio`: the three closed forms and, numerically from the stress function, the
three conditions (`d(u_z)/dx`, `sigma_zz`, `sigma_xz` zero to `1e-9` of the stress scale);
kernel: the two rows (`1e-3`); limits (`f_se = 0`, `chi = 1`: `A_x = (f_h + xi/h)/(1/E -
f_sx)`; `f_sx -> -inf`: `A_x -> 0`); `xi` scaling; sign reversal detected and reported;
`stress_development_fraction` (defined on the correction field as
`1 - (1 + c*kappa*x)*exp(-kappa*x)`): 0 at the bite, 0.95 at `kappa*x = 3.94` for the first
closure with `nu` 0.33, monotonic;
`transfer_radius_profile` with `feedback_stiffness_per_width_pa = N_x'*E*xi/h` equals the
pointwise call (`1e-12`); existing numbers unchanged. Engine: section present for a derived
bite, `NOT_ASSESSABLE` with supplied shape inputs; nothing else changes.

### Documentation
Guide: new 7.14 "Width coupling: a second estimate of the tension feedback" (equations K1-K5,
the closure table, both demo rows, finding 6 in full, the development length and what it means
for a shapemeter close to the mill); 7.2 (the sentence on the feedback gains "an independent
estimate gives 0.69 of it at sheet gauge and 0.10 at foil gauge in the demos, section 7.14");
3.5 and 14 (the thin-gauge trend "hidden more in the mill" rests on the pointwise value);
12; 13. Gap study section 11: G3 `COMPUTED_BESIDE` (kernel only; lateral flow model, entry
profile, finite spans open), X17 `TEXT_CORRECTED` ("checked by one kernel model: not
confirmed at foil gauge").

### What changes, what must not
Artifacts: additive in all four demos and the survey (`width.shape.width_coupling`, one key
per gauge-trend row, flags `WIDTH_COUPLING_KERNEL_REPORTED` and, where true, the others:
allowed changed value of `flags`). No existing number.

### Do not
- Do not switch any level, state, onset or evidence item to the kernel.
- Do not pick the closure that agrees best with the pointwise value; the three are printed.
- No finite-span, strip-element or lateral-flow solver (G3 in full is Phase 3).

---

## Package 9 — Winding: one radial model and the air layer (G9 core, G10 film)

### Why
Gap G9 / X8 (SS-S42 to SS-S49, SS-S60 to SS-S65): the coil criterion is a linear stack with a
constant compaction factor; the literature winds lap by lap with a pressure-dependent radial
modulus. Gap G10 (SS-S49, SS-S50, SS-S58): entrained air changes the radial stiffness. This
package builds the single-lane model and its checks; package 10 couples lanes.

### Model (`[D, re-derived in SPEC19]`; the equation itself is restated in SS-S42 EX)
Axisymmetric wound roll, radius `r` from the core `r_c` to the current outer radius `s`;
`sigma_r` radial (pressure `P = -sigma_r`), `sigma_t` hoop stress; increments caused by one
added lap carry a `d`.
- Equilibrium: `r*d(sigma_r)/dr + sigma_r - sigma_t = 0`.
- Strains `eps_r = du/dr`, `eps_t = u/r`, so `eps_r = d(r*eps_t)/dr`.
- Orthotropic law for increments: `eps_t = (d_sigma_t - nu*d_sigma_r)/E_t`,
  `eps_r = d_sigma_r/E_r - nu*d_sigma_t/E_t` (`nu` = hoop-radial Poisson ratio; symmetry of the
  compliances). `E_r` depends on the pressure already present.
- Substituting `d_sigma_t = d_sigma_r + r*d(d_sigma_r)/dr`:
  `r^2*y'' + 3*r*y' - (E_t/E_r - 1)*y = 0`, `y = d_sigma_r`.
- Outer condition (thin ring of thickness `h` at hoop stress `T_w`): `y(s) = -T_w*h/s`.
- Core: `u(r_c) = y*r_c/E_c` with `E_c` the core stiffness (pressure per unit radial strain),
  so `r_c*y'(r_c) = y(r_c)*(E_t/E_c - 1 + nu)`; rigid core `E_t/E_c = 0`. For a thin-walled
  tube `E_c = E_core*wall/r_c` `[D: ring under external pressure]`.
- After a lap: `sigma_r += y`; hoop stress of every lap below `+= y + r*y'`; radial
  displacement `u = r*((y + r*y') - nu*y)/E_t`, accumulated per node.
- Radial modulus laws (each needs an input; none is a default):
  `'constant'`: `E_r`; `'ratio_of_hoop_modulus'`: `E_r = E_t/ratio` (context: "about two orders
  of magnitude softer than the bulk" for metal coils [SS-S40 VP, a retelling]);
  `'pfeiffer'`: `E_r = K2*(P + K1)` [SS-S42 EX].
- Air layer `[D: isothermal gas law and springs in series; the idea is in SS-S49 EX, SS-S50
  AB]`: an air gap `g0` per lap at ambient pressure `P_a` thins to `g(P) = g0*P_a/(P + P_a)`
  and has the modulus `P + P_a`; with strip share `h/(h + g)`:
  `1/E_r,eq = (h/(h + g))/E_r + (g/(h + g))/(P + P_a)`. `P_a = 101325 Pa`.
- Closed form used as the check `[D]`: `E_r = E_t`, rigid core, constant `T_w`: each lap adds
  `y = A*(1 + beta*r_c^2/r^2)`, `beta = (1 - nu)/(1 + nu)`; summing over the laps
  `sigma_r(r) = -(T_w/2)*(1 + beta*r_c^2/r^2)*ln((R^2 + beta*r_c^2)/(r^2 + beta*r_c^2))`,
  `sigma_t(r) = T_w - (T_w/2)*(1 - beta*r_c^2/r^2)*ln(same)`.

Foil-bearing film `[D, re-derived in SPEC19; formula quoted in SS-S58 EX/AB]`: a web of tension
`T` [N/m] wrapping a cylinder of radius `R`, surfaces moving at `U = V_web + V_roller`, gas
viscosity `mu_g`. Reynolds: `d/dx(h^3*dp/dx) = 6*mu_g*U*dh/dx`; web: `p = T*(1/R - h'')`.
One integration and `h = h0*H`, `x = h0*(T/(6*mu_g*U))^(1/3)*xi` give `H''' = (1 - H)/H^3`.
The inlet branch leaves `H = 1` as `1 + eps*exp(-xi)` and tends to a parabola of curvature `C`
upstream; matching `h'' = 1/R` there gives `h0 = C*R*(6*mu_g*U/T)^(2/3)`. `C` is computed, not
typed: integrate towards `-xi` (RK4, step 1e-3, from `eps = 1e-6`, until `H > 1e4`); planner
0.6430393 (0.6430399 with `eps = 1e-8`, `H > 1e5`). `AIR_VISCOSITY_PA_S = 1.8e-5` `[M]`.

### Numerical method (copy `s25/wind.py`)
Laps are lumped into layers of `n_l` laps (thickness `n_l*h`). Nodes at the layer tops, node 0
on the core. For a new layer: second-order central differences of the equation at the interior
nodes with `E_r` from the present pressure there, the core condition by a one-sided difference
at node 0, `y = -T_w*n_l*h/s` at the top node (`s` = top of the new layer); Thomas solve; hoop
increment at mid-layer; then the layer is appended at its wound-on stress. First order in the
layer thickness.

### Public API (`physicroll/wound_roll.py`)
```python
STATUS = 'UNVALIDATED_WOUND_ROLL_ACCRETION_MODEL'
RADIAL_LAWS = ('constant', 'ratio_of_hoop_modulus', 'pfeiffer')
def radial_modulus_pa(law, pressure_pa, *, hoop_modulus_pa, thickness_m=None, air_gap_m=0.0) -> float
class WoundLane            # add_layer(tension_pa, plastic_strain=0.0); outer_radius_m; arrays
def wind_uniform(*, core_radius_m, outer_radius_m, thickness_m, winding_tension_pa,
                 hoop_modulus_pa, poisson_ratio, radial_law, core_stiffness_pa=None,
                 layers=150, air_gap_m=0.0, tension_taper=None) -> dict
def isotropic_rigid_core_closed_form(radius_m, core_radius_m, outer_radius_m, tension_pa, poisson_ratio) -> tuple
def foil_bearing_constant() -> float       # computed once, cached
def entrained_air_film_m(radius_m, surface_speed_sum_m_s, tension_per_width_n_m,
                         viscosity_pa_s=AIR_VISCOSITY_PA_S) -> float
```
`radial_law`: `{'kind': 'constant', 'radial_modulus_pa'}`, `{'kind': 'ratio_of_hoop_modulus',
'ratio'}` (ratio in [1, 1e4]) or `{'kind': 'pfeiffer', 'k1_pa', 'k2'}` (`k1_pa` in (0, 1e8],
`k2` in (0, 1e4]). `tension_taper`: list of `(radius_m, tension_pa)` points, linear between
them, end values held. `wind_uniform` result: `radius_m`, `radial_stress_pa`, `hoop_stress_pa`
(final), `wound_on_tension_pa`, `radial_displacement_m`, `max_pressure_pa`,
`min_hoop_stress_pa`, `laps`, `laps_per_layer`, flags (`INNER_LAPS_IN_HOOP_COMPRESSION`,
`LUMPED_LAYERS_FIRST_ORDER`), `basis`, `limitations` (elastic; plane model per lane, no axial
stress; no interlayer slip; stack law supplied; lumped layers; no thermal or creep term).

### Worked numbers (planner, `s25/wind.py`, `foilbearing.py`)
Closed form, `r_c` 0.15 m, `R` 0.60 m, `T_w` 30 MPa, `nu` 0.33, 30 um strip, at
`r` = 0.15 / 0.2625 / 0.375 / 0.4875 m: `sigma_r` = -54.0365 / -26.7613 / -14.4826 /
-6.2812 MPa. Model: 100 layers -54.2442 / -26.7073 / -14.4312 / -6.2565; 400 layers
-54.0878 / -26.7477 / -14.4697 / -6.2751 (error falls as 1/layers). Hoop stress of the first
layer at its mid radius: exact 11.79 MPa (100 layers), model 13.46; 400 layers 12.07 against
12.50. Air film: `R` 0.125 m, 10 + 10 m/s, 720 N/m: 16.72 um; `R` 0.30 m: 40.12 um (the study's
"about 17" and "about 40"). Uniform strip, `E_r = E_t/100`: largest pressure 5.779 MPa,
lowest hoop stress -2.98 MPa (inner laps in compression).

### Tests (`tests/test_wound_roll.py`)
Closed form: radial stress within 0.5 % at 100 layers and 0.12 % at 400 at the four radii;
hoop within 2 MPa and 0.5 MPa; first-order convergence (error ratio 200 -> 400 layers between
1.7 and 2.3); outer condition and core condition satisfied by the increment (`1e-9`); soft
core lowers the core pressure; softer `E_r` lowers the inner pressure and the lowest hoop
stress; Pfeiffer modulus rises with pressure; air layer: `g0 = 0` equals no air (`1e-12`),
a gap softens, the gap closes under pressure; taper; constant 0.6430 (`1e-3`); the two films
(`1e-3` relative); rejections; JSON-safe; module time below 10 s.

### Documentation
Guide: new 7.15 "Winding model (`wound_roll.py`)": derivation, laws and what each needs
(a stack press test on 50-200 laps: pressure against strain gives `K1`, `K2`), closed form,
air layer, the film formula with its constant and its "upper bound" status (G10 note: smooth,
wide, impermeable web, no side leakage). 13, 15. Gap study: nothing yet.

### Must not change
No existing module. Five artifact pairs byte-identical.

### Do not
- No default stack law and no Pfeiffer constants "for aluminium": none exists in the reports.
- No nip film, no side leakage or roughness venting model.
- Do not touch `strip_shape.coil_ridge_buildup`.

---

## Package 10 — Winding by lanes in the engine (G9; I7; X8)

### Why
"Hakiel 1D model per width segment ..., relaxation-radius tension allocation, ...
elastic-plastic hoop strain per lane"; "returns per-lane in-coil tension, plastic strain -> a
new elongation term after unwinding" (gap G9). The present criterion stays; this is computed
beside it and says where the two disagree.

### Design

**Case schema.** `WIDTH_DEFAULTS` gains `'coil_winding': None` (needs `width_model.coil`;
messages "width_model.coil_winding.<key> ..."):

| key | unit | rule | default |
|---|---|---|---|
| `radial_law` | - | one of the three forms of package 9 | required |
| `core_stiffness_pa` | Pa | (0, 1e13] or null | null (rigid) |
| `lane_width_m` | m | [0.005, 0.5] | the shapemeter body zone width when a shapemeter is described, else 0.05 |
| `layers` | - | int 20..400 | 150 |
| `tension_taper` | - | null or 2-20 `{"radius_m", "tension_pa"}` points with increasing radius inside the coil | null (constant `coil.winding_tension_pa`) |
| `thickness_profile` | - | null or `{"positions_m", "thickness_deviation_m"}` (>= 3 increasing positions on the barrel, deviations in [-1e-4, 1e-4]) | null (the model's own exit profile) |
| `include_length_profile` | bool | - | true |
| `air_gap_m` | m | [0, 1e-4] | 0 (package 11 can compute it) |
| `provenance` | text | nonempty | required |

**Lanes.** Equal lanes of `lane_width_m` across the strip, the last one shortened; at least 4.
Per lane `j`: thickness `h_j = h_exit + mean over the lane of dh(z)`; `dh(z)` = the supplied
deviation, else `width.shape.steady.local_thickness_change_m` (with feedback) plus the exit
ridge height of every `shape.ridges` entry over its width; natural-length excess
`e_j = 1e-5 * mean over the lane of width.shape.steady.i_units_linear_feedback` when
`include_length_profile` and that profile exists, else 0.

**Tension allocation** `[D, re-derived in SPEC19: the "relaxation radius" of the pseudo-2D
models, SS-S44 AB, SS-S45 EX, written as a strain allocation]`. A new layer lies on lane `j` at
mid radius `s_j = outer_j + n_l*h_j/2` (`outer_j` = undeformed stack height plus the
accumulated displacement of its top node). All lanes of one lap have the same unstrained
circumference `2*pi*s0` apart from their own length excess, so

    eps_j = (s_j - s0)/s0 - e_j
    sigma_j = min(max(E*eps_j, 0), sigma_y)             (a web carries no compression; yield cap)
    eps_p,j = max(0, eps_j - sigma_y/E)                 (plastic stretch of the lap in lane j)
    sum_j w_j*h_j*sigma_j = T_w(s_mean)*sum_j w_j*h_j   -> s0 by bisection (80 halvings)

`sigma_y` = `material.yield_stress_pa`, `E` = `material.youngs_modulus_pa`. Each lane then
gets `WoundLane.add_layer(sigma_j, eps_p,j)`. A mean tension at or above yield is rejected.
Lanes are coupled only through this allocation (no axial stress, no bending of the lap across
the width).

**Section** `width.coil_winding` (new function `band_width.coil_winding_section`; called after
the ridge block; `not_supplied` without the key; `NOT_ASSESSABLE` without a thickness profile
of any kind): `status`, `provenance`, `lanes` (`centre_m`, `width_m`, `thickness_m`,
`thickness_deviation_m`, `length_excess_i_units`), `radius_m` (at most 60 radii), per lane at
those radii `wound_on_tension_pa`, `hoop_stress_pa` (final), `pressure_pa`,
`plastic_strain`; `per_lane` summary (`max_wound_on_tension_pa`, `min_hoop_stress_pa`,
`max_pressure_pa`, `first_yield_radius_m`, `yielding_length_fraction` and
`slack_length_fraction` weighted by wound length, `outer_radius_deviation_m`,
`effective_compaction_factor` = radius deviation over laps x thickness deviation, null for a
lane without deviation); `after_unwinding` (`plastic_i_units_outer_wraps`,
`plastic_i_units_length_mean` per lane, mean removed; each through
`ss.flatness_from_elongation` on the lane centres for bands and states; and
`with_mechanical_profile` = lane means of the mechanical I-units plus the plastic term: the
elongation term the gap row asks for); `beside_linear_criterion` (for the lane of every
supplied ridge and of the largest model band: the present `coil_ridge_buildup` status,
critical ridge height and compaction factor used, against this model's `YIELDS` / `ELASTIC`,
its effective factor and `agrees`); `radial_law`; `basis`; `flags`; `limitations`.
Flags (top level; `band_plain.FLAGS`): `COIL_WINDING_MODEL_REPORTED_BESIDE_LINEAR_CRITERION`,
`WINDING_LANE_YIELDS`, `WINDING_LANE_SLACK`,
`WINDING_DISAGREES_WITH_LINEAR_RIDGE_CRITERION`, `WINDING_INNER_LAPS_IN_HOOP_COMPRESSION`,
`RADIAL_STACK_LAW_IS_AN_INPUT_NO_ALUMINIUM_DATA_FOUND` (always).
Limitations: those of package 9; perfectly registered lanes (no oscillation, no tracking);
elastic-perfectly plastic lap with the tensile yield stress; plastic thinning ignored; the
profile of the case pass is taken as constant along the coil; `coil_ridge_buildup`, the ridge
hypothesis and its evidence are unchanged and do not read this section.
Report: block "Winding the coil lane by lane" after the ridge table: chart of wound-on tension
against radius for the hardest lane, a neighbour and the mean; the per-lane table; the
"beside" table; the sentence "The stack stiffness was entered; no measured value for oily
aluminium foil was found. With a stiffer or softer stack the answer changes (see the guide)."

### Worked numbers (planner, `s25/wind_lanes.py`: 24 lanes of 50 mm, 30 um, 0.15 -> 0.6 m, 30 MPa, yield 165 MPa, 150 layers of 100 laps, one lane thicker; the prototype allocates at the layer top, the specification at mid layer: pin after agreement within 10 %)
| thicker lane | stack | wound-on tension of the hard lane at 1000 / 5000 / 15000 laps, MPa | neighbours | radius difference at the end / laps x dh | yields |
|---|---|---|---|---|---|
| 0 | `E_t/100` | 30.0 everywhere (uniform strip) | 30.0 | - | no |
| 0.1 um | `E_r = E_t` | 67.1 / 132.1 / 159.9 | 28.4 -> 24.3 | 1158 um / 1500 um = 0.772 | no (just) |
| 0.1 um | `E_t/100` | 53.8 / 51.9 / 51.3 | 29.0 | 181 / 1500 = 0.121 | no |
| 0.1 um | Pfeiffer `K2` 100, `K1` 10 kPa (assumed) | 47.2 / 44.1 / 41.7 | 29.3-29.5 | 0.0625 | no |
| 0.1 um | Pfeiffer `K2` 30, `K1` 10 kPa (assumed) | 38.5 / 36.1 / 34.5 | 29.6-29.8 | 0.0194 | no |
| 1 um | `E_r = E_t` | 165 (yield) from layer 3 | 23.9 | 0.972 | 98 % of the layers; plastic stretch up to 2230 I-units |
| 1 um | `E_t/100` | 165 from layer 3 | 23.9 | 0.437 | 98 %; up to 905 I-units |
| 1 um | Pfeiffer `K2` 30 | 165 at layers 3-10, then 145.6 / 120.6 / 93.4 | 24.8 -> 27.2 | 0.031 | 5 % of the layers; up to 17 I-units |

Time 0.3 s. The linear criterion at the same coil (compaction 0.5): critical ridge height
of the order of 0.1 um (the committed artifacts quote 0.06-0.15 um), i.e. "yields" for both
lanes.

### Tests (`tests/test_band_coil_winding.py`)
Allocation: uniform lanes get the mean tension (`1e-9`); the force balance holds (`1e-9`);
a longer lane (`e_j > 0`) gets less tension; a lane beyond the slack limit gets zero; yield
cap and plastic strain on a hand case of three lanes; mean tension above yield rejected. Lanes:
the rows above (signs and orderings asserted, values pinned): the radius difference is below
laps x `dh` for every stack; the hard lane's tension stops rising for the soft stacks (value at
15000 laps not above the value at 1000); softer stack -> smaller factor. Section on a coarse
case with one incoming ridge: `beside_linear_criterion` filled; absent key changes nothing;
ridge evidence identical; validation; report renders.

### Documentation
Guide 7.15 second part (allocation, the table, finding 5 in full, X8 answered: "contradicted
in form, confirmed: the factor is an outcome and ranges from 0.02 to 0.97 with the stack
stiffness; the value 0.5 has no better and no worse support than before"); 3.5; 5.3 (the press
test; winding tension and taper from the coiler set-up); 7.2 (coil paragraph); 12; 13; 14.
README: one sentence. Gap study section 11: G9 `REDUCED_MODEL_OPT_IN` (pseudo-2D, elastic-
plastic laps; no axial stress, no spool model beyond a stiffness, no V-buckle or telescoping
margin, no measured stack law), X8 `TEXT_CORRECTED`.

### What changes, what must not
Artifacts: additive (`width.coil_winding` not supplied; no scenario gets a stack law: open
decision 5). No evidence item.

### Do not
- Do not replace `compaction_factor`, `_coil_buildup` or the ridge rule.
- Do not ship a stack law in any scenario or preset as if it were data.
- Do not add the plastic term to `width.shape.steady`.

---

## Package 11 — Ironing roll, air in the coil, coil temperature (G10 nip, A8 temperature; I8 in part)

### Why
G10: "wound-in tension `T_w + mu*N/h` with a nip"; "Boyle-law air layer in the winding model";
traction is lost when the film exceeds about three times the combined roughness [SS-S58
EX/AB]. A8: "the published battery-foil limits are coil temperatures, the model gives strip
exit temperatures"; coil conduction with `k_r << k_z`. Creep is Phase 3.

### Design A — nip and air (`wound_roll.py`, `band_width.coil_winding_section`)
New optional keys of `coil_winding`:
- `ironing_roll`: null or `{"load_per_width_n_m": (0, 1e5], "traction_coefficient": (0, 1]}`.
  Wound-in tension `T_w + mu_n*N/h` [gap row G10, from SS-S49 EX; no formula for `mu_n`: it is
  an input], capped at yield with the flag `WOUND_IN_TENSION_CAPPED_AT_YIELD`.
- `air`: null or `{"mode": "entrained_film" | "none" | "both", "viscosity_pa_s": null}`.
  `'entrained_film'`: `air_gap_m` of each layer = `entrained_air_film_m(s, 2*u_exit,
  T_w(s)*h)` at its radius (it replaces a typed `air_gap_m`; both given is rejected).
  `'both'`: the section is computed twice and `air_cases` holds the two summaries. With an
  ironing roll and `mode` null the mode is `'both'`: no nip film formula is in the reports, so
  the two runs are the bounds ("the nip removes all the air" / "the nip removes none"), and
  the result says so.
Section additions: `air_entrainment` (`film_at_core_m`, `film_at_outer_radius_m`,
`film_over_strip_thickness`, `basis`, note "upper bound: smooth, wide, impermeable web, no side
leakage [gap study, note to G10]"), `deflector_roll` (film on `deflector_roll_radius_m` at the
exit speed and tension; with `tribology.surface_finish.strip_roughness_rq_m` and the new
optional `width_model.deflector_roll_roughness_rq_m`: `film_over_combined_roughness` and
`traction` = `'LIKELY_LOST'` above 3, `'KEPT'` below, else `'NOT_ASSESSABLE'`), `nip`.
Flags: `ENTRAINED_AIR_FILM_EXCEEDS_STRIP_THICKNESS`, `AIR_CASES_BRACKET_THE_NIP_EFFECT`.

### Design B — coil temperature (`wound_roll.py`; new key `width_model.coil_thermal`)
| key | unit | rule | default |
|---|---|---|---|
| `surface_htc_w_m2k` | W/m2K | (0, 500] | required |
| `ambient_temperature_k` | K | [250, 400] | required |
| `strip_conductivity_w_mk` | W/mK | [50, 300] | required |
| `gap_medium` | - | `'oil'` or `'air'` | required |
| `interlayer_gap_m` | m | (0, 1e-4] or null | null = the winding section's mean air gap under pressure when it ran with air, else required |
| `hold_times_s` | s | 1-8 increasing values in (0, 1e7] | `[3600, 14400, 86400]` |
| `provenance` | text | nonempty | required |

Model `[D, SPEC19; conduction equation and the statement k_r << k_z: gap A8, TM-LA33 EX,
TM-LA32 EX]`:
- Temperature at winding: the case pass's modelled strip exit temperature (an upper bound: no
  loss between bite and coil; flag `COIL_WINDING_TEMPERATURE_TAKEN_AS_STRIP_EXIT_UPPER_BOUND`);
  per lane the lane mean of `width.local_state.strip_exit_temperature_k` when package 1 ran.
- `k_r = (h + g)/(h/k_s + g/k_g)` (series), `k_z = k_s*h/(h + g)` (parallel); `k_g` =
  `Lubricant.effective_conductivity_w_mk()` for oil, `AIR_CONDUCTIVITY_W_MK = 0.026` `[M]` for
  air. `rho*c` = `bite_tribology.ALUMINIUM_VOLUMETRIC_HEAT_CAPACITY_J_M3K` times `h/(h + g)`.
- Cooling of a uniformly hot hollow cylinder with convection on the outer surface and both end
  faces, core side adiabatic: product of two one-dimensional solutions (exact for a uniform
  start and these conditions `[D, classical]`): `theta(r, z, t) = theta_r(r, t)*theta_z(z, t)`,
  each by backward Euler on 40 cells and 400 equal steps to the last hold time
  (`theta = (T - T_amb)/(T_wind - T_amb)`).
- Outputs at each hold time: hottest point, coil mean, outer surface at mid width; time for
  the hottest point to fall below each published coil limit (read from
  `thermal_check.coil_limits_c`: entering the final pass, leaving it, elongation decay, with
  the sources that block cites; no rows when `battery_coil_limits_apply` is false; no new
  limit);
  time scales (`(r_o - r_i)^2*rho*c/k_r`, `(W/2)^2*rho*c/k_z`, lumped
  `rho*c*V/(h_s*A)`, Biot numbers).
- Stress between lanes on cooling to a common temperature at a common radius:
  `d_sigma_j = E*alpha*(T_j - mean T)` (`alpha` = `strip_shape.ALUMINIUM_EXPANSION_PER_K`,
  SPEC17 package 6): a hotter lane ends tighter. An upper bound (no radial relaxation, no
  creep); with the winding section present it is added to that lane's final hoop stress and
  compared with yield (`COIL_COOLING_STRESS_REACHES_YIELD`).
Section `width.coil_temperature`: `status`, `winding_temperature_k`, `per_lane` (or null),
`conductivities`, `time_scales`, `cooling` rows, `limit_rows` (`limit_k`, `source`,
`at_winding`: `'ABOVE' | 'BELOW'`, `time_to_fall_below_s` or null within the last hold time),
`lane_stress_on_cooling_pa`, `basis`, `flags`, `limitations` (no heat from the next laps while
winding, no radiation model beyond the coefficient, uniform gap, no creep, no recovery
kinetics: B7 and the stress part of A8 are Phase 3). `thermal_check` itself is NOT changed.

### Worked numbers (`s25/g11.py`, `foilbearing.py`)
30 um strip, `k_s` 200 W/mK: oil gap 0.5 um (`k_g` 0.13): `k_r` 7.63 W/mK; air gap 2 um:
`k_r` 0.42. Coil 0.15 -> 0.6 m, 1.2 m wide, 8 W/m2K: radial scale 17.9 h (oil) or 329 h
(air), axial 1.22 h, lumped 16.2 h, Biot 0.024 axial and 0.47 / 8.7 radial. Stress on cooling
1.652 MPa per kelvin between lanes; the demo's 1.99 K hotter lane: 3.3 MPa. Entrained film at
the demo's coil (13 m/s, 30 MPa x 30 um = 900 N/m): 20.6 um at 0.15 m, 82.3 um at 0.6 m,
0.69 to 2.7 strip thicknesses (compute with the function and pin).

### Tests
`tests/test_wound_roll.py`: series and parallel conductivities; a slab alone and a cylinder
alone against their lumped limit at small Biot number (2 %); product structure (the 2-D value
equals the product); monotone cooling; nip tension and its cap; air modes; `'both'` returns
two summaries with the entrained case softer. `tests/test_band_coil_winding.py`: sections with
and without package 1; limit rows carry the published sources; absent keys change nothing;
`thermal_check` identical.

### Documentation
Guide 7.15 third part; 3.12 (coil temperature beside `EXIT_IS_NOT_COIL`: what is now
estimated and that it is an upper bound at winding); 5.3 (coil surface temperature against
time with a contact probe; ironing-roll load); 12; 13; 14. Gap study section 11: G10
`SCREENING_VERSION` (film formula, air layer, nip tension; no nip film, no venting), A8
`SCREENING_VERSION` (temperature and a thermal-stress bound; creep, B7 open).

### What changes, what must not
Artifacts: additive (`width.coil_temperature` not supplied; `inputs` keys).

### Do not
- No default surface coefficient, gap or strip conductivity.
- Do not change a `thermal_check` verdict or its `EXIT_IS_NOT_COIL` caveat.
- No creep, no recovery kinetics.

---

## Package 12 — Lateral stress in spans (G11; I13) — the one evidence branch of this block

### Why
Gap G11: "the thresholds are computed but the acting lateral stress is not, so the trough /
wrinkle hypothesis is thresholds only unless the plant supplies a stress it cannot measure".
The row names closed forms (Good & Beisel; Shelton) that are not in the reports. Misalignment
and taper are derived here; roller deflection is reduced to its beam quantities (finding 10).

### Model (`[D, re-derived in SPEC19]`, docstring in `strip_shape.py`)
Span of length `a` between two rollers, strip width `W`, thickness `t`, tension stress
`sigma_x`, modulus `E`; the span as a beam bending in its own plane (`I = t*W^3/12`), lateral
deflection `v(x)`.
- Misaligned downstream roller, in-plane angle `theta`: the strip leaves the upstream roller
  straight (`v(0) = v'(0) = 0`), enters the downstream roller normal to its axis
  (`v'(a) = theta`) and carries no moment there in the steady state (`v''(a) = 0`). With
  `v'''' = 0`: `v = theta*x^2/a - theta*x^3/(3*a^2)`, shear force `V = 2*E*I*theta/a^2`, mean
  shear stress `tau = V/(W*t) = E*W^2*theta/(6*a^2)`. Shear deformation does not change `V`
  under these four conditions (both slope conditions are on the total slope). Tension
  stiffening is neglected: its parameter `K*a = (a/W)*sqrt(12*sigma_x/E)` is 0.19-0.21 in the
  demos; flag above 0.5.
- Tapered roller, radius difference `dR` over the strip width on radius `R`: the surface
  speed varies by `m = dR/(R*W)` per metre of width, which is a curvature of the strip at the
  roller: `v'(a) = 0`, `v''(a) = m` give `|V| = 2*E*I*m/a`, the shear of a misalignment
  `theta_eq = m*a`.
- Lateral compression: with `sigma_x` and `tau` the second principal stress is
  `sigma_2 = sigma_x/2 - sqrt(sigma_x^2/4 + tau^2)` (compressive, about `-tau^2/sigma_x`).
  Troughs when `-sigma_2` reaches the trough threshold `s_tr` of the span
  (`trough_critical_lateral_stress_pa`), wrinkles on the roller at the wrinkle threshold.
  Critical angle: `theta_cr = (6*a^2/(E*W^2))*sqrt(s*(sigma_x + s))`, `s` the threshold
  magnitude.
- Roller deflection: uniformly loaded, simply supported tube; load per length
  `q = 2*T*sin(wrap/2)` (`T` tension per width); `I_r = pi*(D^4 - (D - 2*w)^4)/64`; curvature
  at mid length `q*L^2/(8*E_r*I_r)`, end slope `q*L^3/(24*E_r*I_r)`, mid deflection
  `5*q*L^4/(384*E_r*I_r)`. No lateral stress is derived from it.
- Foil: wrinkles on wide aluminium foil below 25 um needed about 15 times the misalignment the
  isolated-span model predicts, copper 7-10 times [SS-S55 EX]; the factor is quoted beside the
  critical angles, not applied.

### Design
`strip_shape.py`: `misalignment_shear_stress_pa`, `taper_equivalent_misalignment_rad`,
`second_principal_stress_pa`, `critical_misalignment_rad`, `roller_deflection`,
`span_lateral_stress(...) -> dict` (thresholds from the existing functions; keys
`shear_stress_pa`, `second_principal_stress_pa`, `computed_lateral_compressive_stress_pa`,
`critical_misalignment_troughs_rad`, `critical_misalignment_wrinkles_rad` (null without a
roller radius), `foil_factor_context`, `tension_stiffening_parameter`, flags
`SPAN_TENSION_STIFFENING_NOT_NEGLIGIBLE`, `SPAN_SHORTER_THAN_WIDTH_BEAM_MODEL_INDICATIVE`
(`a < W`), `basis`, `limitations`: beam model of an isolated span; misalignment and taper
only; no roller deflection, tension drop over a driven roller, bent coil or baggy lane as a
source; no moment transfer, slack edge or traction limit).

Case key `width_model.span_alignment` (`WIDTH_DEFAULTS` null): `{"entry_span": S | null,
"exit_span": S | null, "provenance"}`, `S = {"misalignment_m_per_m": [0, 0.1] or null,
"taper_radius_difference_m": [0, 1e-3] or null, "roller_radius_m": (0, 5] or null (default
`deflector_roll_radius_m`), "roller": null or {"outer_diameter_m", "wall_thickness_m",
"face_length_m", "youngs_modulus_pa", "wrap_angle_rad"}}`. The two angles add in magnitude
(worst case, stated).

`band_width._troughs`: each span dict gains `generators` (`not_supplied` without the key).
When `width_model.lateral_compressive_stress_pa` is null and a span has a misalignment or a
taper, its `computed_lateral_compressive_stress_pa` is passed to `tension_trough_screen`, and
the span dict gains `lateral_stress_basis: 'computed from span_alignment (misalignment and
taper only)'`; a supplied plant value always wins (`'supplied'`).

**The evidence branch.** `band_width._h_troughs`, item `'model trough status (either span)'`
(criterion string unchanged):

| status comes from | status | today | with this package |
|---|---|---|---|
| supplied `lateral_compressive_stress_pa` | `TROUGHS_EXPECTED` / `ROLLER_WRINKLE_EXPECTED` | `SUPPORTS`, moderate, basis model | unchanged |
| supplied | all `BELOW_TROUGH_THRESHOLD` | `CONTRADICTS`, weak | unchanged |
| none | thresholds only | `NOT_OBSERVED`, basis input | unchanged |
| computed from `span_alignment` | expected | - | `SUPPORTS`, **weak** (1 point), basis model |
| computed | all below | - | `NEUTRAL`, basis model |

Reason: the computed stress covers two of the generators the literature lists, so "below"
cannot count against troughs; and at foil gauge the isolated-span model over-predicts
[SS-S55 EX], so "expected" counts only a little. `observed` text: the status words plus
"(lateral stress computed from the entered roller alignment)". The credibility gate
(`BITE_FREE_MODEL_CRITERIA`) is unchanged: the item needs no bite. No committed scenario has
`span_alignment`, so no committed score moves; a test proves the two new branches on a case
that has it.

Report: in the trough table two more columns (computed stress, critical misalignment in mm/m)
and one line per span for taper, roller deflection and the foil factor.

### Worked numbers (`s25/g11.py`; `E` 70 GPa, `nu` 0.33)
| span | trough threshold | critical shear | critical misalignment (troughs) | wrinkle threshold | critical misalignment (wrinkles) | x 15 |
|---|---|---|---|---|---|---|
| battery-foil exit: 30 um, 3 m, 1.2 m, 40 MPa, roller radius 0.125 m | 32152 Pa | 1.1345 MPa | 0.6078 mm/m | 10.275 MPa | 12.18 mm/m | 183 mm/m |
| battery-foil entry: 50 um, 35 MPa | 50125 Pa | 1.3255 MPa | 0.7101 mm/m | 17.125 MPa | 16.01 mm/m | 240 |
| lengthwise exit: 0.21 mm, 4 m, 1.5 m, 30 MPa, 0.15 m | 146182 Pa | 2.0992 MPa | 1.2795 mm/m | 59.94 MPa | 44.75 mm/m | 671 |

Forward, battery-foil exit span, 0.1 mm/m: shear 186667 Pa, `sigma_2` -871.1 Pa: below the
trough threshold. Taper 10 um over 1.2 m on a 0.125 m roller: equivalent to 0.2 mm/m. Roller
tube 0.25 m x 10 mm wall x 1.5 m, 1200 N/m at 90 degrees wrap: `q` 1697.06 N/m, `I_r`
5.4381e-5 m4, curvature 4.179e-5 1/m, end slope 2.090e-5 rad (0.021 mm/m).

### Tests
`tests/test_strip_shape.py`: the beam solution satisfies its four conditions and
`V = 2*E*I*theta/a^2` (symbolic check by evaluating the polynomial); every number above
(`1e-4` relative); `theta_cr` inserted forward returns the threshold (`1e-9`); taper equals
misalignment `m*a`; small-shear limit `-tau^2/sigma_x`; flags; rejections.
`tests/test_band_lengthwise.py` or `test_band_foil.py`: a case with 1 mm/m on the exit span:
`TROUGHS_EXPECTED`, item `SUPPORTS` weak; with 0.1 mm/m: item `NEUTRAL`; the same case with a
supplied plant stress: branches as today; without the key: every result identical;
`tests/test_band_plain.py`: the criterion string is still in `CRITERIA`.
`tests/test_benchmarks.py`: `SS-V14` as `REFERENCE_ONLY_INPUTS_NOT_RECORDED` (the factors 15
and 7-10 recorded, tension and geometry of the trials not in the reports); `SS-V15` stays in
`NOT_ENCODED` ("critical values not quoted in the reports").

### Documentation
Guide 7.2 (trough paragraph: the two generators, derivation, the table, what is not covered);
3.5; 5.3 (roller alignment survey in mm/m; taper from roller grinding reports); 6 (the rule
table of the trough hypothesis: the two new branches, "rule extended in SPEC19"); 12; 13; 14.
Gap study section 11: G11 `SCREENING_VERSION` (misalignment and taper; one weak evidence
branch; deflection, moment transfer, slack edge, traction, baggy-lane source open).

### What changes, what must not
Artifacts: additive (`generators` not supplied in every span dict; `inputs`). Scores equal.

### Do not
- Do not apply the factor 15 to any threshold.
- Do not derive a stress from roller deflection.
- Do not let a computed "below" contradict.

---

## Package 13 — Foil gauge: sensitivities and the speed-tension loop (C1, BT-G13; I6; X7)

### Why
Gap C1 (TM-LC18 VP, TM-LC19 AB, TM-LA36 EX): at foil gauge "the strip thickness depends very
heavily on tension and rolling speed"; the row asks for the sensitivities and a loop "exit
gauge -> entry-tension trim (fast, limited range) -> speed (slow, acceleration-limited), dead
time `L_gauge/u`, gauge filter, Smith predictor option". BT-G13: the speed effect "at constant
force and constant tension". The sources give this structure and no gains or equations; the
loop below is a stated simple one `[D, SPEC19: analyst design]`.

### Model (new module `physicroll/foil_gauge.py`; `[D, re-derived in SPEC19]`)
Static force balance of the linearised bite with two extra inputs,
`dF = F_h*dh + F_hin*dh_in + F_se*ds_e + F_sx*ds_x + F_mu*dmu + F_Y*dY`, against the structure
`dF = M_eff*(dh - dS) + K_kiss*dh`. `M_eff`: 0 for a mill run at constant strip force
(`'constant_force'`), the stand's mill modulus for position control (`'position'`), or a
supplied number; `K_kiss` = stiffness of the roll-to-roll contact outside the strip, null = 0:
the interface for Phase 3 (gap BT-G2: "`dF = F_h*dh + K_kiss*dh` [coupling inferred]"). With
`den = M_eff + K_kiss - F_h`:

    g_X = dh/dX = F_X/den   for X in (h_in, s_e, s_x, mu, Y);   dh/dS = M_eff/den

    speed:  dh/du = g_mu*dmu/du + g_Y*Y*m/u
            dmu/du = process.friction_speed_curve.mean_slope_per_m_s (needs tribology)
            m = hardening.rate_temperature.rate_sensitivity (SPEC18 package 5), else the term is 0
    oil temperature: dh/dT_oil = g_mu*dmu/dLambda*Lambda*(-beta)      (package 1, formula 6)

`F_mu`, `F_Y` from `band_process.friction_force_sensitivity` / `flow_stress_sensitivity` (or
`bite_extras`). Loop on the entry tension, per unit of gauge error, without limits:

    L(s) = (w_c/s) * 1/(1 + s/w_T) * exp(-s*theta)/(1 + s*tau_g)
    theta = gauge_distance_m/u_exit,  w_T = 2*pi*tension_loop_bandwidth_hz
    w_c = integral_crossover_rad_s, default 0.5/(theta + tau_g + 1/w_T)      [D: about 60 degrees]
    S(jw) = 1/(1 + L(jw))             gauge error left of a disturbance at frequency w

With `smith_predictor` true and a perfect model: `L0 = L` without the delay,
`w_c = 0.5/(tau_g + 1/w_T)`, `T0 = L0/(1 + L0)`, `S = 1 - T0*exp(-s*theta)` `[D: the Smith
identity]`. Phase margin, gain margin, the frequency below which `|S| < 1` and the peak of
`|S|` by a scan of 1200 frequencies (0.01 rad/s times `1.01^i`).
Time domain (limits make it non-linear): explicit steps of `dt = min(0.001 s, theta/40)` for
20 s; delay as a FIFO; filter and tension loop as first-order lags; integral trim clipped at
`+-tension_trim_limit_fraction*entry tension`; when the trim stays at a limit, the speed moves
at `speed.ramp_limit_m_s2` in the direction that relieves it (`dh/du`), if `speed` is given.
Status of a run: `SETTLED` (error within 5 % of its first value for the last 5 s),
`TRIM_SATURATED_HELD_BY_SPEED`, `TRIM_SATURATED_ERROR_REMAINS`, `OSCILLATING` (last 5 s
peak-to-peak above 20 % of the first value). `UNSTABLE_LOOP_SETTINGS` is set from the margins
(phase margin at or below 0) and the time run is then not made.

### Design
New optional top-level v2 section `foil_gauge_control` (added to
`band_diagnosis.V2_SECTIONS` as SPEC17 package 4 did for `measurement`; validated by
`foil_gauge.validate`; v1 results get the not-supplied entry):

| key | unit | rule | default |
|---|---|---|---|
| `gap_mode` | - | `'constant_force'`, `'position'`, `'supplied_modulus'` | required |
| `effective_mill_modulus_n_m` | N/m | [0, 1e12], only with `'supplied_modulus'` | - |
| `kiss_stiffness_n_m` | N/m | [0, 1e13] or null | null |
| `gauge_distance_m` | m | (0, 20] | required |
| `gauge_time_constant_s` | s | [0, 1] | required |
| `tension_loop_bandwidth_hz` | Hz | (0, 100] | required |
| `tension_trim_limit_fraction` | - | (0, 0.5] | required |
| `integral_crossover_rad_s` | rad/s | (0, 1000] or null | null (rule above) |
| `smith_predictor` | bool | - | false |
| `speed` | - | null or `{"ramp_limit_m_s2": (0, 5]}` | null |
| `reels`, `ripple_pitches_m` | - | package 14 | null |
| `provenance` | text | nonempty | required |

`result['foil_gauge_control']` (computed in `diagnose` after `gauge_control`, inside the
`try / except` pattern of SPEC17 package 4; needs the operating bite): `status`
(`'UNVALIDATED_FOIL_GAUGE_LOOP_ANALYST_CONTROL_LAW'`), `sensitivities` (the `g_X`, each also
as percent of gauge per natural unit: per MPa, per percent friction, per percent flow stress,
per m/s, per kelvin of oil; `mill_modulus_n_m`, `strip_modulus_n_m`, `dh_dgap`), the same block
for the other `gap_mode` beside it (`constant_force` against `position`), `loop` (`theta`,
`w_c`, margins, `attenuates_below_hz`, `peak_sensitivity`, `sensitivity_at`: the roll and coil
frequencies of the existing `roll_freqs`, the entry and exit coil once-per-revolution
frequency, and the chatter onset frequency), `disturbances` (rows for a 1 % entry gauge step,
1 % flow stress, 1 % friction, 1 K oil temperature, a 10 % speed change: open-loop gauge
change, trim needed in Pa and as a share of the limit, `trim_saturates`, speed change that
would replace it), `step_response` (the time run for the entry gauge row: status, settling
time, overshoot, thinned history), `foil_regime_note`, `basis`, `flags`, `limitations`.
Flags: `FOIL_GAUGE_LOOP_SIMULATED`, `GAUGE_SET_BY_STRIP_NOT_BY_GAP` (`dh_dgap < 0.1`),
`LOOP_AMPLIFIES_COIL_FREQUENCY` (`|S| > 1` at a once-per-revolution frequency),
`TENSION_TRIM_SATURATES_FOR_ONE_PERCENT_ENTRY_GAUGE`, `SPEED_EFFECT_FROM_PLACEHOLDER_FRICTION_
SLOPE` (the closure's flag), `KISS_STIFFNESS_NOT_MODELLED_ZERO_USED` (below
`CLOSED_GAP_ONSET_RANGE_M` with `kiss_stiffness_n_m` null).
Report: block "Gauge control by speed and tension" in the process section; the existing
gaugemeter block gains the pointer SPEC17 package 3 wrote for X7.

### Worked numbers (planner, `s25/gauge.py`; battery-foil case pass, mattress bite of the committed artifact)
Mill modulus 2.3077e9 N/m, strip modulus 8.8665e10 N/m: `dh/dS` 0.0254.

| sensitivity | constant strip force | position control |
|---|---|---|
| `dh/ds_e` | -5.4948e-14 m/Pa (-0.183 % of gauge per MPa) | -5.3555e-14 |
| `dh/ds_x` | -8.5384e-14 m/Pa | -8.3218e-14 |
| `dh/dmu` | 6.9569e-4 m (0.696 % per 1 % friction) | 6.7804e-4 |
| `dh/dY` | 1.5110e-13 m/Pa (0.881 % per 1 % flow stress) | 1.4727e-13 |
| `dh/dh_in` | 0.4397 | 0.4286 |

Speed effect with the placeholder slope -0.0016462 per m/s: -1.145e-6 m per m/s (-3.8 % of
gauge per m/s; no rate term). Loop: gauge at 1.5 m, 13 m/s: `theta` 0.1154 s; `tau_g` 10 ms
[under 10 ms: TM-LC24 VP]; tension loop 5 Hz (assumed): `w_c` 3.180 rad/s (0.506 Hz), phase
margin 61.4 degrees, gain margin 3.34 at 10.08 rad/s; `|S| < 1` below 0.521 Hz; peak 1.565 at
1.132 Hz; at the entry coil's once-per-revolution frequency (7.8 m/s, 1.0 m: 2.483 Hz)
`|S|` = 1.123 (time run with a 1 MPa ripple: 1.126). Entry gauge step of 1 % (0.5 um): exit
deviation 0.2199 um at first, within 5 % after 0.54 s, overshoot 4 %, trim 4.00 MPa = 114 % of
a 10 % limit on 35 MPa: saturates.

### Tests (`tests/test_foil_gauge.py`)
Sensitivities: the table (`1e-4`); `M_eff -> inf` gives `dh/dS -> 1` and all `g_X -> 0`;
`K_kiss` lowers every `g_X`; signs. Loop: `S` at very low frequency tends to
`j*w/w_c`; margins of the pure delay-integrator `L = w_c*exp(-s*T)/s` against the closed forms
(phase margin `90 - w_c*T*180/pi` degrees, gain margin `pi/(2*w_c*T)`); the numbers above
(`1e-3`); Smith identity (`S` of the Smith loop with zero delay equals the plain one); time
run equals the frequency response for a sinusoid (2 %); trim clip; unstable settings are
reported, not run; JSON-safe. Engine: section present, absent key changes nothing, hypotheses
identical, v1 result carries the not-supplied entry and its HTML is byte-identical.

### Documentation
Guide: new 9.5 "Foil gauge control by speed and tension" (model, the table, finding 8, the
loop law and its three numbers the plant must supply, what `K_kiss` stands for); 9 first
paragraph (X7 pointer becomes a link); 8.4 (speed effect and its placeholder basis); 5.3; 12;
13; 14. Template: the section with null. Gap study section 11: C1 `LOOP_MODEL_OPT_IN`
(analyst loop; no decoupling, no adaptive scheme, no closed gap), BT-G13 `SCREENING_VERSION`
(sensitivity from the existing bites and closure; the BT-S3 case not reproduced: BT-V4 curves
are not digitised), X7 `TEXT_CORRECTED` extended.

### What changes, what must not
Artifacts: additive (`inputs.foil_gauge_control` null, `foil_gauge_control` not supplied in
all five pairs). No scenario gets the section (open decision 7).

### Do not
- Do not change `mill_dynamics.py`, the gaugemeter section or any transverse evidence item.
- Do not present the loop as the plant's; every gain is entered or a stated rule.
- No closed-gap load share: `K_kiss` is an input.

---

## Package 14 — Reels, spans and run-out; chaining of passes (C2, C8; I6, I14)

### Why
Gap C2 (TM-LC21 EX, TM-LC22 EX, TM-LC28 EX): four reel causes of cyclic gauge, among them coil
eccentricity and "a resonance condition resulting from a mass / spring system" of coil and
span; "a tension regulator cannot attenuate a once-per-revolution disturbance near its own
bandwidth and may amplify it". Gap C8: ripple written by one pass returns as entry forcing of
the next.

### Model (`foil_gauge.py`; `[D, re-derived in SPEC19]`)
Entry side (the exit side with its own signs and the exit quantities):

    s_e' = (E/L_e)*(du_e - R*dw - v_d)                span as a spring between bite and reel
    du_e = k_e*s_e,  k_e = u_e*((f_se + f_h*g_se)/(1 + f) + g_se/h1)     (< 0: the bite gives way)
    J*dw' = A*R*s_e - dM                              reel; A = width*h0
    v_d = w_rev*e_c*sin(w_rev*t),  w_rev = u_e/R      run-out e_c of the coil radius

`k_e` follows from the kinematics of `chatter.py` (`du_e = V_r*((h1/h0)*df + ((1 + f)/h0)*dh)`)
with `df = f_se*s_e + f_h*dh` and `dh = g_se*s_e` of package 13. `J` =
`mill_dynamics.reel_inertia_kg_m2`. Regulator: `'none'` (`dM = 0`) or `'direct'`, an ideal
high-pass on the tension error with the entered bandwidth: the response is multiplied by
`s/(s + w_b)` `[D: the simplest form of "cannot attenuate above its bandwidth"]`. Hence

    s_e(jw)/v_d = -(E/L_e)/(jw + lam_b + (E/L_e)*A*R^2/(J*jw)),   lam_b = -(E/L_e)*k_e
    coil-on-span frequency w_n = sqrt((E*A/L_e)*R^2/J),  damping ratio lam_b/(2*w_n)
    gauge ripple = |g_se|*|s_e|*|S(j*w_rev)|          (S of package 13)

Chaining (C8): a thickness ripple of pitch `p` on the entry strip of a pass passes at
`f = u_e/p`; exit amplitude `a_out = |g_hin|*|S(j*2*pi*f)|*a_in`; exit pitch `p*h0/h1`; the
exit ripple of pass `n` is the entry ripple of pass `n + 1`. Relative ripple `a/h` changes by
`|g_hin|*(h0/h1)*|S|` per pass.

### Design
`foil_gauge_control.reels`: null or `{"entry": Rl | null, "exit": Rl | null,
"strip_density_kg_m3": 2700 [M] default}`, `Rl = {"coil_radius_m", "core_radius_m",
"motor_inertia_kg_m2", "gear_ratio" (default 1), "runout_m" [0, 0.01], "regulator": "none" |
"direct", "regulator_bandwidth_hz" (needed with "direct")}`.
`foil_gauge_control.ripple_pitches_m`: null or 1-6 pitches in (0, 20].
Result additions: `reels` per side: `once_per_revolution_hz`, `bite_leak_rate_per_s`,
`coil_on_span_hz`, `damping_ratio`, `tension_ripple_pa`, `gauge_ripple_open_loop_m`,
`gauge_ripple_closed_loop_m` (and as a share of gauge), and `radius_sweep` (8 radii from the
entered coil radius to the core: the same quantities, with `resonance_crossing` true where
the two frequencies come within 10 % of each other while the damping ratio is below 0.5).
`pass_chain` (needs a schedule and a bite for each pass, through `get_bite`; rows that have
no bite are marked and end the chain): for the coil circumference of the first pass and each
entered pitch: per pass frequency, `|g_hin|`, `|S|`, amplitude ratio, cumulative ratio and
relative-ripple ratio, and `near_stand_resonance` when the frequency is within 10 % of that
pass's chatter onset frequency (`schedule_sweep` rows). Flags: `REEL_RUNOUT_RIPPLE_COMPUTED`,
`COIL_ON_SPAN_RESONANCE_CROSSED_DURING_COIL`, `RELATIVE_RIPPLE_GROWS_FROM_PASS_TO_PASS`
(cumulative relative ratio above 1), `ENTRY_RIPPLE_NEAR_STAND_RESONANCE`. Limitations: the
regulator is an ideal filter; reel friction, binding and ovality harmonics are not modelled;
loop settings of the case pass are used for every pass of the chain; the gauge sensor's own
transfer (SPEC17 package 5) is not applied; `incoming_variation` and the coil-locked evidence
are unchanged.

### Worked numbers (planner, `s25/gauge.py`; battery-foil case pass, entry coil radius 0.5 m, core 0.15 m, motor 50 kg m2 (assumed), span 3 m, run-out 0.1 mm)
`k_e` -1.649e-8 m/s per Pa; leak rate 384.7 1/s (2.6 ms); reel inertia 365.5 kg m2;
coil-on-span 4.925 Hz, damping ratio 6.2; once per revolution 2.483 Hz; run-out speed
1.56e-3 m/s; tension ripple 93966 Pa (94551 Pa with the reel speed held); gauge ripple
5.163e-9 m (0.0172 %) open loop, 5.798e-9 m with the loop of package 13. Chain: `|g_hin|`
0.4397 and `h0/h1` 1.667 give a static relative ratio of 0.733 for the case pass.

### Tests (`tests/test_foil_gauge.py`)
The numbers above (`1e-3`); no bite response (`k_e = 0`) and no regulator: an undamped
resonance at `w_n` (the response grows without bound as the frequency approaches it:
asserted through a large ratio); held reel (`J -> inf`): `|s_e| = (E/L)*v_d/sqrt(w^2 +
lam_b^2)`; regulator reduces the response below its bandwidth and not above; sweep monotonic
in frequency; chain: with `|S| = 1` and equal passes the cumulative ratio is the product of
the `g_hin`; pitch stretching `p*h0/h1`; a pass without a bite ends the chain with a reason.
Engine: absent keys change nothing.

### Documentation
Guide 9.5 second part (model, numbers, finding 8: why the resonance is overdamped here and
what would change that, namely a bite much less sensitive to tension); 9.4 or the section on
coil-locked marks (pointer); 11.2 (pitch chaining beside `stretched_pitch_m`); 5.3; 12; 13;
14. Gap study section 11: C2 `SCREENING_VERSION` (linear, ideal regulator), C8
`SCREENING_VERSION` (amplitude chain through the loop of the case pass).

### What changes, what must not
Artifacts: byte-identical apart from what package 13 added (keys inside a not-supplied
section do not exist).

### Do not
- Do not add reel states to `chatter.assemble_state_matrix` or `mill_dynamics`.
- Do not feed a ripple amplitude into any evidence item.

---

## Package 15 — Guided app (plant-facing inputs and plain words for packages 1 to 14)

Read SPEC16, SPEC17 package 9, SPEC18 package 9, `docs/band-app.md` and the three test modules
first. The invariants hold unchanged: plain wording, help and a unit for every question; no
engine tokens or forbidden words; every number shown is a number of the result; drawn equals
simulated; "Don't know" stays null; the trust rule and the `ask_first` sets are unchanged;
none of the new inputs raises or lowers trust.

**Questions** (`band_plain.py`; `SECTIONS` entries for every new nullable section, each with
its required keys and the provenance "entered in the band app"):

| group | ids | keys | wording |
|---|---|---|---|
| Flatness control | `valve_levels_kind` (choice: on / off, three steps, 5 % steps -> the list), `valve_min_on`, `valve_min_off`, `flatness_dead_band`, `control_zone_size` (nozzles per valve), `flatness_control_interval`, `shapemeter_distance`, `flatness_display_filter` | `width_model.flatness_control.*` | How your spray valves are switched by the flatness control |
| Zone test | `step_test_nozzles`, `step_test_hold`, `step_test_filter` | `width_model.zone_step_test.*` | A test you ran: one spray zone closed for a while |
| Oil and metal across the width | `inlet_weight`, `softening_per_kelvin`, `oil_flow_per_nozzle` | `width_model.local_coupling.*` | How the oil and the metal respond to a hot roll stripe |
| Coil build-up | `stack_law_kind`, `stack_modulus` / `stack_ratio` / `stack_k1`, `stack_k2`, `core_stiffness`, `winding_taper` (list), `ironing_roll_load`, `ironing_roll_traction`, `coil_air` | `width_model.coil_winding.*` | How the coil is wound and how stiff a stack of your foil is |
| Coil cooling | `coil_surface_htc`, `coil_ambient`, `coil_gap_medium`, `coil_gap`, `strip_conductivity` | `width_model.coil_thermal.*` | How the coil cools |
| Roller alignment | `entry_misalignment`, `exit_misalignment`, `entry_taper`, `exit_taper`, roller tube questions | `width_model.span_alignment.*` | Roller alignment from your last survey |
| Gauge control | `gap_mode`, `gauge_distance`, `gauge_response`, `tension_loop_bandwidth`, `tension_trim_limit`, `smith_predictor`, `speed_ramp_limit`, reel questions, `ripple_pitches` | `foil_gauge_control.*` | How gauge is controlled on this pass |

New units if absent: `mm_per_m`, `l_min` (to m3/s), `percent_per_k`, `hz`, `kn_per_m`,
`w_m2k`. The help texts say where a value comes from and carry the status of every published
number in plain words ("no measured value for aluminium foil was found; use your own press
test"). The stack law has NO preset value; "Don't know" leaves the section null.
`buckling_model` was added in package 7 (wording pass only). Round trips for every preset and
every list question (`test_round_trip_case_answers_case`); the battery-foil example returns
its local coupling, flatness control and zone test.

**Summary views** (`plain_summary`; numbers from the result only; extend the view tuple of
`test_summaries_build_and_keep_engine_numbers`):
- `control_loop_view`: status sentence; valve changes; "The zone error went from {a} to {b}
  I-units"; zones where a band was made or removed; fixed sentences "The control law is this
  tool's own, not your system's." and "The slow overall shape is left to bending and tilt,
  which the tool does not model."
- `step_test_view`: "A test of {w} s would show a response time of about {t1} s from roll
  growth alone and {t2} s with the strip temperature included."
- `hot_stripe_view`: the four terms at the largest band as signed bars; "The sign of the fast
  part depends on an assumption about the oil temperature." when the flag is set.
- `feedback_check_view`: "A second estimate of how strongly strip tension hides a roll stripe
  gives {r} of the value this tool uses; with it the band would read {p} I-units."
- `waves_view`: wavelength, wave height, lift limit on a table; "an upper estimate".
- `coil_view`: hardest lane tension, whether it yields, effective compaction against 0.5,
  agreement with the standard coil check; coil temperature at winding against the limits,
  "an upper bound".
- `alignment_view`: critical misalignment per span beside the entered one.
- `gauge_loop_view`: gauge change per MPa and per percent of friction; whether the loop
  amplifies the coil frequency; trim needed for a 1 % entry gauge step.
- `FLAGS`: check every flag of packages 1 to 14; `GLOSSARY`: "valve dead band", "stack
  stiffness", "wave height", "tension trim" if absent.

**Page** (`band_app_assets.py`): the new groups collapsed by default; result cards: "What the
flatness control would do" (valve map and error curve drawn from the result), "A hot stripe:
four effects", "Winding the coil" (tension against radius), each only when available; the
one-page print keeps its present content and adds the control card when available. Drawing
before a run: control zones as brackets over the nozzle row, from the engine's grouping
function through `drawing_model` (add to the drawn-equals-simulated test and its edit
sequence). No new server route. The quick profile runs every new section on its coarse grid;
`PROFILES['quick']['left_out']` gains "the wavelength search for waves (when it was
switched on)": `apply_profile` sets `buckling_model` back to `sine_mode` in a quick run.

**Tests**: question-table invariants; unit round trips; preset round trips; summaries of the
regenerated artifacts (numbers in result, no engine tokens, no forbidden words, flags
described); partial cases keep the views unavailable; drawing test with control zones; a run
with flatness control stores and reopens. **Docs**: `docs/band-app.md`; README one sentence.
**Must not change**: no engine module, scenario or artifact (byte-identical).

**Do not**: no physics in `band_plain.py` or the page; no sentence that turns "the loop does
not settle" into "your control is wrong"; never "validated"; no default stack stiffness.

---

## 3. Open decisions (the planner's choice is implemented unless the owner says otherwise)

1. **No default is switched.** Buckling: the benchmark rows do not support it (finding 3).
   Winding: it needs a stack law nobody has measured (finding 5). If the owner wants a switch
   anyway, it needs its own brief; it would move: every `state_after_tension_release`,
   `released_*` key and after-release onset in `width.shape`, `thermal_events`, `gauge_trend`
   and the survey; the evidence items of `_tension_release_rules` and the "visible time basis"
   of events in both lengthwise demos; `foil_regime` texts; the ridge item 'model coil
   build-up of a supplied ridge' and `affected_length_fraction`; and the pinned expectations
   of `tests/test_strip_shape.py`, `test_band_lengthwise.py`, `test_band_foil.py`,
   `test_band_survey*.py`, `test_band_plain.py`.
2. **No model evidence for the heat-streak hypothesis** from the local sources (package 2):
   the net sign depends on an assumed weight. Alternative: a weak supporting item when the
   mechanical net at an observed band position has the same sense as the observed appearance
   for both weights.
3. **Predicted valve events do not feed the zone-switching hypothesis** (package 4): they
   depend on a control law that is the tool's own. Alternative for the owner: let `_h_zone`
   read `predicted_events` when `changes_with_coolant_zone_switching` is true and no events
   were typed; it would move scores only in cases that describe a controller.
4. **Kernel level always computed** (package 8): cheap, needs no input, and X17 asks for it.
   It prints a number that contradicts the tool's main foil result by a factor of 9 beside
   that result. Alternative: behind `model_options`.
5. **No stack law in any demo** (package 10). Alternative: a separate scenario "battery foil,
   winding study" with the three laws of the worked table, labelled as assumptions.
6. **Inlet temperature weight 0.5 by default** (package 1): the two-surface mean.
   Alternative: required input.
7. **Battery-foil demo gains three inputs** (G''7); its regeneration grows from about 73 s to
   about 85 s. Alternative: a second scenario file and artifact pair for the loop features.
8. **Control law** (package 3): integral least squares with a dead band on the demanded
   change, hysteresis 0.1, gain 0.1, regularisation 0.01. All analyst choices; the owner can
   replace them by the plant's law if its description is supplied.
9. **Lateral closure of the kernel** (package 8): no lateral velocity at the bite. The other
   two are printed.
10. **The one evidence branch** (package 12): `SUPPORTS` weak / `NEUTRAL` for a computed
    lateral stress. Alternative: no evidence at all from computed stress (pure report).
11. **Roller deflection** (package 12): beam quantities only. The owner can settle it by
    supplying Shelton's paper.
12. **Released sample length** (package 7): half-waves up to the strip width. Analyst choice.

## 4. Risks: where an exactly implemented result could still mislead a plant user

| risk | mitigation built into the outputs |
|---|---|
| "The loop does not settle" reads as a statement about the plant's flatness control. It is a statement about an analyst control law with entered valve data on a model with one header, no bender and a roll-growth path the kernel check puts in doubt. | Status string `..._ANALYST_CONTROL_LAW`; fixed sentences in report and app; limitations; the three analyst constants named in `basis`. |
| Predicted valve events look like a log of what happened. | Label "predicted by the flatness loop"; kept out of `thermal_events` and of the evidence; guide 7.12. |
| The loop reports a small zone error while the largest zone reading triples: the low-order part is silently assumed away. | `low_order` block with the edge-to-centre value and its sentence; the flag is always set; both numbers in the status table. |
| A fitted 16-35 s beside the published 20 s reads as "explained". | `finding` sentence gives both series and the window; guide 7.1 says what is assumed (coupling, filter, test length) and that no plant protocol is recorded. |
| Four signed terms of a hot stripe add up to a confident net number. | Two weight variants always printed; `sign_depends_on_inlet_weight`; the `warn` paragraph "read the signs, not the digits"; compliance-only value beside. |
| The kernel's 210 I-units beside the model's 25 can be read as "the tool was wrong by 9" or be ignored. Neither estimate is validated; the kernel depends on a lateral closure. | Three closures printed; "second estimate", never "corrected value"; nothing reads it; guide 7.14 states what would decide it (roll stack with closed gap, or a plant test of a known stripe). |
| Wave heights in millimetres look measurable and exact. | "Upper estimate" in key notes, report and app; one-mode and fibre-model limitations; the present states remain the ones used. |
| "Lies flat on a table" may be read as "no defect". The band is still a stress stripe and may show after slitting. | Wording "lies flat on a table under its own weight; the length difference is still there"; guide 3.5. |
| A user enters a stack stiffness from a film handbook; the winding verdict then looks computed. | Flag `RADIAL_STACK_LAW_IS_AN_INPUT_NO_ALUMINIUM_DATA_FOUND` always; the report sentence; no preset; the worked table shows the factor moving from 0.02 to 0.97. |
| Plastic stretch of hundreds of I-units for a 1 um lane looks absurd and may discredit the section. | The guide explains it (15000 laps x 1 um); the section reports `yielding_length_fraction` and the first yield radius first. |
| Coil temperature "at winding" equals the strip exit temperature, which at foil gauge is inflated by the bite model's slip. | Flag and the words "upper bound"; the existing `EXIT_IS_NOT_COIL` caveat stays in `thermal_check`. |
| A computed lateral stress from a clean alignment survey says "below": the user concludes that troughs are excluded. | The branch is `NEUTRAL`, never a contradiction; the limitation lists the generators not covered. |
| Critical misalignment for wrinkles of 12 mm/m, or 183 mm/m with the foil factor, suggests alignment never matters. | The trough value (0.6 mm/m) is printed first; the factor 15 is context only; creases from troughs passing a roller are named as not modelled. |
| Gauge sensitivities come from a bite that is 0.42 (or 0.79) of the reference load; the speed effect uses the placeholder friction slope. | Flags of the bite and the closure are repeated in the section; both gap modes side by side; "per m/s" printed with its basis. |
| The reel model says the coil-on-span resonance is overdamped. A plant that sees it may distrust everything. | Guide 9.5: the damping comes from the bite's slip sensitivity; a stiffer bite (closed gap) would lower it; the sweep prints the damping ratio. |
| Green benchmark tests read as validation. | As SPEC17: test names, status strings, guide 13. |

## 5. Interfaces Phase 3 will consume

| Phase 3 item | what it needs | what Phase 2 provides, and where |
|---|---|---|
| G1 roll stack: bending and tilt in the flatness loop | actuator columns with limits and dynamics | `flatness_control.supplied_actuators` (influence per shapemeter zone, limits; fitted before the sprays) and `ZoneController` step 2; the low-order coefficients the loop now reports are what those actuators must take (packages 3, 4) |
| G1: gap crown and local force per width | the strip's local answer to a gap change, with both tension distributions | `strip_shape.width_coupling_kernel` (`A_x`, `A_e`, `Q_eff`) and `transfer_radius_profile(feedback_stiffness_per_width_pa=...)`: the stack's influence functions replace `C(lam)`, the kernel stays (package 8) |
| G2 / BT-G2 closed gap, kiss force | a place for the roll-to-roll stiffness in gauge and shape | `foil_gauge_control.kiss_stiffness_n_m` and `effective_mill_modulus_n_m` (package 13); the kernel's `Q_eff` to which a kiss stiffness per width adds in parallel (package 8) |
| G3 in full (lateral flow, entry profile) | the closure the kernel had to assume | `LATERAL_CLOSURES` and `span_strain_ratio`: a strip-element model supplies `chi` or replaces (K4)-(K5); the development length function gives the shapemeter-distance correction (package 8) |
| G4 extensions, G14 slitting | buckling of an arbitrary stress profile on an arbitrary width | `strip_buckling.critical_mode`, `post_buckling`, `dead_load_lift` take any nodes, edges and stresses: a slit strip is a narrower `z` range with free edges (packages 6, 7) |
| I12 shapemeter with buckled bands in the loop | the stress a buckled band still carries | `post_buckling(...)['saturated_i_units']` and the `steady_saturated` shapemeter profile (package 7) |
| G7 / A7 roll ends and edge actuators | a thermal run that accepts changing boundary data | `roll_thermal.ControlledRun.advance` (levels per call; an edge heat source is one more per-call argument of the same class) (package 3) |
| A8 creep, B7 recovery | stress and temperature history per lane and radius | `width.coil_winding` arrays (`hoop_stress_pa`, `pressure_pa` per lane and radius), `width.coil_temperature.cooling` and the product solution functions of `wound_roll.py` (packages 10, 11) |
| G9 axisymmetric winding, spool | the lane model's core condition and stack law | `WoundLane` (core stiffness, `radial_modulus_pa` with air), the allocation function with its yield cap (packages 9, 10) |
| G12 tension lines | axial compression of the outer lap and the air film | `entrained_air_film_m`, the air layer of `radial_modulus_pa`, per-lane outer radius and pressure (packages 9-11); SPEC17 package 8 holds the pitch |
| C3-C6 chatter extensions | tension dynamics beyond constant-speed span ends; a loop transfer for ripple | `foil_gauge.py`: `k_e`, `lam_b`, the reel transfer and `S(jw)`; `pass_chain` rows (packages 13, 14) |
| BT-G15, BT-G16 bite refinements | every consumer of bite sensitivities in this block | all packages read the sensitivities through `BiteResponse`, `friction_force_sensitivity`, `flow_stress_sensitivity` or `bite_extras`; none calls a bite solver directly |
| plant validation | the measurements section 7.4 of the study names | zone step test -> package 5; coil diameter profile and stack press test -> package 10; roller alignment survey -> package 12; speed, tension and gauge logs -> packages 13, 14 |
