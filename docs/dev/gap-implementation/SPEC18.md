# SPEC18 — Phase 1 of the coverage-gap study: the foundations other models take their input from

Repository `/home/user/PhysicRollModel`, planned against commit `8f10cbe` PLUS everything SPEC17
(Phase 0, same scratchpad directory) specifies. Read SPEC17 section G first: it applies unchanged
except for the changes of G' below. Source of every new fact: `docs/simulation-coverage-gaps.md`
(the gap study) and the reports in `docs/research/band-screening-2026-11/`. Nothing else may be
used as a source. Do not commit. No network.

Nine work packages, executed one at a time in the order given, each leaving the repository green.
Section 0 holds what the planner measured; read it before package 1.

Scratch material of the planner in `scratchpad/s23/` (prototypes: copy, do not import from the
repository; where they differ from this text, this text holds):

| file | what it is |
|---|---|
| `hs_kernel.py`, `hertz_check.py` | influence coefficients, closed-form and Hertz self-checks |
| `hs_bite.py` | half-space bite: grid, residual, Jacobian, LU, Newton, post-processing |
| `hs_solve2.py`, `run_v1.py` | cold start from the mattress bite, homotopy, structure switch |
| `sens.py` | sensitivities by chord iterations; warm start between passes |
| `hs_final.py` | the final structure check (the rule of package 1) and the demo schedules with it |
| `bench.py`, `regime2.py`, `cap4.py`, `cap3.py`, `hill.py`, `inv2.py` | benchmark rows, regime boundary, shear cap by friction march, spurious slope root, friction-hill margins, friction inversion |
| `heat.py` | heat partition (numerical and closed form), flow-stress and skin hand numbers |
| `skin2.py`, `skin3.py` | periodic roll surface layer, arc-aligned stepping, superposition; step response |
| `fric.py` | two-point closure numbers, film check on BT-V4, Eyring and viscosity-table examples |
| `t_mattress.py`, `t_diag.py`, `t_survey.py` | timing of the present solvers and their callers |
| `head/` | export of commit `8f10cbe` used for all timings (never the working tree) |

---

## G'. Rules that differ from SPEC17 section G

**G'1. Opt-in models, not only opt-in inputs (replaces G3 for this block).** No package changes
an evidence item, score, standing or leader of any committed artifact. Every new model is either
(a) computed and reported beside the present value, or (b) selected by an explicit case key whose
default is the present behaviour. The committed scenarios are not switched to any new model.
There is NO "switch the default" package in this block: the benchmark results do not justify one
(section 0.1). G6 applies to every package with "additive only" as the allowed classification;
anything else is a fault.

**G'2. Tags.** As SPEC17 G2. Formulas re-derived here carry `[D, re-derived in SPEC18]`.
A reduced model built because the reports do not contain the full one says so in its status
string, in a flag and in the guide, and names the input a user must supply instead.

**G'3. Status words for section 11 of the gap study** (added to the fixed list of SPEC17 G7):
`REDUCED_MODEL_OPT_IN` (a reduced form of the row's model exists behind a case key; the default
is unchanged; the row's full model is not built) and `ROUTINE_ADDED` (a calibration or
identification routine that works on entered measurements).

**G'4. App invariants are wider than SPEC17 G5 lists.** `tests/test_band_plain.py`
(`section_53_keys`, `test_every_section_53_key_has_a_question`, `test_choices_are_the_engine_
lists`) also requires: a question for every key of `band_diagnosis.OPTION_KEYS + OPTION_OPTIONAL`
(except `bite_response_override`), for every key of `band_process.HARDENING_COMMON` and of every
tuple in `HARDENING_LAW_KEYS`, and the choice lists of the questions `bite_model` and
`hardening_law` equal to `band_diagnosis.BITE_MODELS` and `tuple(HARDENING_LAW_KEYS)`. A package
that extends one of these adds the question (one plain sentence, help text, unit) in the same
package; package 9 only refines wording and layout. Keys this brief places elsewhere
(`tribology.lubricant.*` beyond the present six, `tribology.friction_closure.*` beyond the present
three, `hardening.rate_temperature`, `width_model.circumferential_layout`,
`measurement.pass_records`) are outside those lists on purpose and get their questions in
package 9. `band_survey_mills.MACHINES[...]['tribology']` gains every new optional tribology key
with `None` in the package that adds it (drift guard
`test_packaged_mills_equal_the_demo_machine_sections`).

**G'5. Benchmarks.** Every model of this block gets at least one case in
`physicroll/benchmarks.py` (SPEC17 package 1: `CASE_IDS`, `run_case`, the three-part record, the
verdict words, the `test_<id>_recorded_discrepancy_...` naming). New ids are appended to
`CASE_IDS`; `NOT_ENCODED` is edited where a package encodes a row. A verification against a
published value is software verification plus a literature comparison; every result keeps
`SCREENING_RESULT_NOT_PLANT_VALIDATED`.

**G'6. Run time is a requirement.** Each package reports the measured times named in its
"Budget" paragraph. If a budget is missed, stop and report; do not loosen it.

---

## 0. What the planner measured and found (read before package 1)

### 0.1 The half-space bite prototype

The prototype (`s23/hs_bite.py`) solves a REDUCED form of the published model: rigid-plastic
strip in its plane, elastic thickness compliance of the strip, elastic half-space rolls, a no-slip
zone, capped Coulomb friction. It converges on every case tried (table) and on all 15 passes of
the two v2 demo schedules.

| case (R 89 mm, `Y_s` 230 MPa, `E_R*` 230 GPa, `E_s*` 80 GPa, mu 0.03 unless stated) | published | mattress (present) | half-space prototype | ratio prototype / published |
|---|---|---|---|---|
| BT-V1, 20 -> 15 um | `W_bar` 118 (half-space), 120 (perturbation) | 49.77 (0.42) | **92.94** (foil structure) | **0.788** (0.775 to 120) |
| BT-V3 Fig. 1, 140 -> 70 um | about 50 (read by eye) | 45.97 | 46.82 (conventional) | 0.936 |
| BT-V2, 73 -> 31.39 um, mu 0.026, tensions 0.107 / 0.132 `Y_s`, R assumed 89 mm | 58 (measured) | 41.07 | 42.80 | 0.738 |
| same, R assumed 135 mm | 58 | 51.05 | 67.13 | 1.157 |
| BT-V2 inverted: friction that gives `W_bar` 58 | 0.026 (the authors' inference), "about 0.03" (mill tests) | - | 0.0306 (R 89 mm), 0.0249 (R 135 mm) | brackets both |
| eq. 29 regime boundary, r = 0.5 | 51.2 um entry gauge | "foil" at every gauge tried | no-slip zone appears between 52 and 48 um | within 7 % |
| eq. 29, r = 0.25 | 36.2 um | "foil" everywhere | between 36 and 32 um | within 12 % |
| eq. 29, r = 0.10 | 22.9 um | "foil" everywhere | between 30 and 26 um | 14-31 % high |
| load exponent in friction at BT-V1, `d ln W / d ln mu` | about 2 to 2.6 (derived by the bite report, slope read by eye) | - | 2.46 | inside |

Findings the coder must carry into code comments, result notes and documents, unsoftened:

1. **The reduced model does not reach the published load in the foil regime: 0.79, not 1.0.**
   It is a clear improvement on 0.42, it reproduces the published regime boundary and the load
   exponent, and it agrees with the reference at sheet gauge. It stays a `RECORDED_DISCREPANCY`.
   Grid error is not the cause (doubling every zone moves BT-V1 by 0.4 %), nor is the strip
   compliance (`E_s*` from 40 GPa to rigid moves `W_bar` from 96.8 to 88.9).
2. **Why (the planner's reading, tag `[D, SPEC18, not verified]`).** The equation list of gap row
   BT-G1, eqs (1), (3a), (8), (9), (15), (16), leaves out the longitudinal elastic strain of
   strip and roll surface in the no-slip condition (eqs (10) to (14), assigned by the study to
   BT-G15, Phase 3). In the reduced model the pressure at the downstream end of the no-slip zone
   sits on the exit friction hill. The published solution has "elastic unloading and a sharp
   pressure peak just after the neutral zone" [BT-S1 FT]: pressure there is not bound to the exit
   hill. This is stated as the probable cause, not as an established one.
3. **The rigid-plastic half-space problem is ill-posed without a strip compliance.** With a rigid
   strip the roll would have to conform to a flat on an incline at entry; Newton drives the entry
   contact zone to zero length (`s23/dbg2.py`). An elastic thickness compliance of the strip
   (a local spring, `h_ref/E_s*`) makes it well-posed. The published case carries `E_s*` = 80 GPa.
4. **The published under-relaxed fixed point (weights 0.1-0.5) is replaced by Newton with a line
   search on a boundary-fitted grid.** A fixed point on the roll shape cannot hold a no-slip zone
   (loop gain of the order of 1000 there); the literature solves that zone inversely for the same
   reason [BT-S4 AB]. This is a deliberate deviation from the wording of the gap row.
5. **Foil loads rise.** On the battery-foil demo schedule at the supplied friction 0.03 the
   prototype gives 1.37 / 3.24 / 2.66 / 10.13 kN/mm for F1 / F2 / ALT1 / ALT2 against the
   mattress 0.96 / 1.54 / 1.49 / 6.19 (trade range quoted by the project: 0.9-2.3 kN/mm). With a
   load exponent in friction of about 3 at these gauges, F2 would return into the range at a
   friction of about 0.027. This is why the model stays opt-in and why friction identification
   (package 4) belongs to the same block.
6. **At the regime boundary neither structure of the reduced model is strictly admissible,
   and the demo's main pass sits on it.** For 50 -> 30 um at friction 0.03 the foil structure
   needs 1.44 times the friction limit to hold its 0.18 mm no-slip zone, and the conventional
   structure is accepted on one grid and thickens slightly before the neutral point on
   another. The two give 1.3935e6 and 1.3700e6 N/m (1.7 % apart; forward slip 0.252 and
   0.237). Without a fixed rule the answer depends on the path of the cold start. Package 1
   fixes the rule ("final structure check") and reports the other structure's force.
7. **Heat split.** A lumped strip on a half-space roll with perfect contact gives a strip share
   of 0.162 for the report's own check case (24 um, 0.2 ms); with a 70 nm oil film 0.225. Both
   lie inside the measured 0.11-0.33 [TM-LA19 AB]. The film resistance is half the roll's
   transient resistance at that contact time, so "thermally perfect" (the report's words) does
   not hold as a model assumption.

### 0.2 Timings and budgets (Python 3.13, one core, export of `8f10cbe`)

| item | measured |
|---|---|
| one converged mattress solve (`foil_bite._converged`) | 0.02 s |
| `derive_bite_response_mattress` (18 converged solves) | 0.17-0.46 s |
| `chatter.derive_bite_response` (Hitchcock, 256 cells) | 0.9-1.0 s |
| half-space prototype, cold start (62 elements) | 0.25-1.0 s on the demo passes; 1.4 s worst case seen |
| half-space prototype, 12 sensitivities by chord iterations | 0.07-0.17 s |
| `diagnose`, battery-foil demo | 72.6 s; bite derivations 7.6 s (24 mattress calls 4.0 s, 7 Hitchcock 3.6 s) |
| `diagnose`, lengthwise demo | 48.7 s; bites 22.1 s (29 Hitchcock) |
| `diagnose`, thin-gauge chatter / bearing demo | 18.6 s / 8.7 s; bites 17.6 s / 7.9 s |
| guided app, quick profile on the battery-foil case | 13.8 s; bites 4.8 s |
| product survey | 46.1 s; bites 18.9 s (33 Hitchcock, 18 mattress) |
| periodic skin-layer solve, one station (prototype) | 0.14 s (368 steps per revolution, 60 revolutions) |
| heat partition, 400 steps | under 0.05 s |

Budgets that follow:

- A half-space derivation (nominal solve plus sensitivities) may cost at most 2.0 s cold and
  0.6 s warm-started, 1.0 s on average over the 15 demo passes. Then a battery-foil `diagnose`
  with `bite_model: 'auto_half_space'` stays under 100 s and the quick profile under 30 s.
- With the default bite models nothing may slow down by more than 2 % (the new code is not on
  the default path).
- Each new test module stays under 60 s; split the half-space tests into two modules
  (`tests/test_halfspace_bite.py`, `tests/test_halfspace_bite_cases.py`) if one would pass 45 s.
- The new sections of packages 6 and 7 add at most 3 s to a `diagnose` that supplies their
  inputs and nothing measurable to one that does not.

---

## 1. Overview

| # | Package | Gap ids | What changes for a user | Default or opt-in | Depends on | Size (lines changed, with tests and docs) |
|---|---|---|---|---|---|---|
| 1 | Half-space bite: kernel and solver | BT-G1 (core), BT-G5 | New module `physicroll/halfspace_bite.py`; nothing in the engine uses it yet | not wired | SPEC17 pkg 2 (flag name) | 800-900 |
| 2 | Half-space bite: sensitivities, engine, benchmarks | BT-G1, BT-G5, BT-G17 (new rows) | `model_options.bite_model: 'half_space' / 'auto_half_space'`; benchmark table shows 0.42 against 0.79; a bite-model comparison for any case | opt-in | 1; SPEC17 pkg 1, 2, 7 | 700-850 |
| 3 | Viscosity table, limiting shear, reduced friction closure | A9, BT-G3 (reduced) | Oil viscosity from data-sheet points; a load-sharing friction law with a contact-area ratio interpolated between two published end points | opt-in | SPEC17 pkg 2 | 600-750 |
| 4 | Friction from load, torque and forward slip | BT-G6 | New optional `measurement.pass_records`: friction that reproduces each measured force, slip and torque, with their disagreement; suggested closure points | new input; never applied | 2, 3; SPEC17 pkg 4 | 550-700 |
| 5 | Flow stress: rate, temperature, law forms, fit | B1, B2 (with B3 of SPEC17) | Optional rate and temperature factor on every pass flow stress; Tome-Voce law; signed late slope; fit to the plant's pass strengths; the rate share of the chatter damping heuristic reported | opt-in | none | 650-800 |
| 6 | Computed bite heat partition | A3, X4 | Strip heat share computed beside the supplied one for every pass; optional use | computed and reported; use is opt-in | 3 (film), 2 (contact length) | 550-700 |
| 7 | Roll surface layer within one revolution | A4, G8, X5 (part) | New optional `width_model.circumferential_layout`: surface temperature around the roll, at bite entry per width station, three time scales, bias of the circumferential-mean coefficient | new input | 6; SPEC17 pkg 3 (`spray_wetted_arc_rad`) | 700-850 |
| 8 | Spray coefficient calibration | A5 (routine) | `python -m physicroll.band_cli CASE --calibrate-spray`: the coefficient that reproduces an entered roll temperature scan or camber, with its misfit curve | routine; never applied | none (7 optional) | 450-600 |
| 9 | Guided app | plant-facing side of 2-8 | Questions, plain words and cards for the new inputs and outputs | - | 2-8 | 650-850 |

Out of scope for every package (Phase 2 and 3): friction, film or flow stress varying across the
width (A2, BT-G4 in full, BT-G12); friction varying through the bite; elastic strip zones and
roll surface strain (BT-G15, Fleck eqs (4), (10)-(14)); hardening inside the bite (BT-G16); any
change to `slab.py`, `contact.py`, the mattress equations or `chatter.assemble_state_matrix`;
closed gap; roll stack; flatness controller; A6; coil models; any new hypothesis, evidence item
or observation key.

---
## Package 1 — Half-space bite: kernel and solver (BT-G1 core, BT-G5)

### Why
Gap row BT-G1 (BT-S1 FT, BT-S2 FT, BT-S4 AB, BT-S14 FT): the mattress bite is 0.42 of the
reference load on the one fully specified case; the published successor puts the rolls on elastic
half-spaces with a no-slip zone. Row BT-G5 (BT-S3 EX, BT-S14 FT): cap the friction stress at
shear yield instead of rejecting. The reports restate eqs (1), (3a), (8), (9), (15), (16) of
BT-S1 [FT]; they do not contain its influence coefficients (30)-(32), its solution method or
the method of BT-S4 [AB]. Coefficients and method are therefore derived here.

### Model (module docstring; every line `[D, re-derived in SPEC18]` unless tagged)

Conventions of `foil_bite.py`: `x` along rolling, entry at `x < 0`; `h_p(x)` [m] full PLASTIC
strip thickness; `p` [Pa] pressure, compressive positive; `sigma` [Pa] tensile; `K = 2Y/sqrt(3)`
[Pa] (= `Y_s` of BT-S1); `tau_f` [Pa] traction on the strip, positive in the rolling direction;
`R` [m] undeformed roll radius; `E_R* = E/(1 - nu^2)` [Pa] of the roll; `E_s*` [Pa] plane-strain
modulus of the strip; `t_b`, `t_f` [Pa] entry and exit tension; `mu`; `m` shear cap factor.

1. Roll gap between two half-space rolls [BT-S1 FT eq. (8), written for the full thickness]:
   `g(x) = g0 + x^2/R - (4/(pi*E_R*)) * Int p(x') ln|x - x'| dx'`. `g0` is a datum constant, not
   an unloaded gap (a half-space in plane strain has no rigid-body reference).
2. Strip thickness under load: `g(x) = h_p(x) - c_s*p(x)`, `c_s = h_ref/E_s*`,
   `h_ref = (h0 + h1)/2`. Elastic strain in the thickness direction only (uniaxial strain: the
   density change cancels the thickness change, so strip speed follows `h_p`:
   `u(x)*h_p(x) = const`). No elastic strain along the strip. Without this term the problem is
   ill-posed (section 0.1, finding 3).
3. Equilibrium [BT-S1 FT eq. (1)]: `d(sigma*h_p)/dx = -p*h_p' - 2*tau_f`.
   Yield [eq. (3a)]: `p + sigma = K`.
   Friction stress magnitude: `T(p) = min(mu*p, m*K/2)` [cap: BT-S14 FT, BT-S3 EX].
4. Zones, upstream to downstream:
   - entry contact zone `[c_i, x_i]`: strip below yield, `h_p = h0`, `tau_f = +mu*p`,
     `sigma(x) = t_b - (2*mu/h0)*Int_{c_i}^{x} p`; ends where `p + sigma = K`;
   - entry slip zone `[x_i, x_a]` [eq. (15)]: `h_p*p' = K*h_p' + 2*T(p)`;
   - no-slip zone `[x_a, x_b]`: `h_p = h_n` (strip at roll speed), yield at both ends;
   - exit slip zone `[x_b, x_e]` [eq. (15)]: `h_p*p' = K*h_p' - 2*T(p)`;
   - exit contact zone `[x_e, c_x]`: `h_p = h1`, `tau_f = -mu*p`,
     `sigma(x) = t_f - (2*mu/h1)*Int_{x}^{c_x} p`; starts where `p + sigma = K`.
   Conventional structure: no no-slip zone, the slip zones meet at the neutral point `x_n`,
   `h_n = h_p(x_n)`. Forward slip `= h_n/h1 - 1`.
5. Free-boundary conditions: `p(c_i) = p(c_x) = 0`; yield at `x_i` and `x_e` (above);
   `h_p' = 0` at `x_a` approached from the entry slip zone (the first stationary point of the
   entry branch); `h_p' = 0` at `x_e` approached from the exit slip zone (thinning ends smoothly);
   `x_b` follows from pressure continuity. These are the conditions of the mattress model
   (`foil_bite.py` docstring), which this model contains as the limit of a purely local kernel.
6. Admissibility (checked, never assumed): `p >= 0`; `h_p` non-increasing in both slip zones;
   below yield in the two contact zones; and in the no-slip zone the friction-hill bounds
   `p(x) <= p(x_a) + (2/h_n)*Int_{x_a}^{x} T(p)` and `p(x) <= p(x_b) + (2/h_n)*Int_{x}^{x_b} T(p)`
   for every node. Reason: the no-slip zone need not be at yield everywhere; where it is below
   yield the friction is static and only its integral is fixed. These two bounds are necessary
   and sufficient for a static friction field `|tau_f| <= T(p)` that keeps `p + sigma <= K`
   between two ends at yield. Eq. (16) of BT-S1, `tau_f = (h_n/2)*p'`, holds only where the zone
   is at yield; the solver reports its pointwise ratio to `T(p)` and does not reject on it.
   At `x = x_b` the first bound is the net shear demand of the zone; it decides the structure
   (final structure check below). Bounds missed at interior nodes only are flagged.
7. Integrals: force per width `Int p`; traction per width (one roll)
   `mu*Int_entry_zone p + Int_entry_slip T + (h_n/2)*(p(x_b) - p(x_a)) - Int_exit_slip T -
   mu*Int_exit_zone p`; slip dissipation over roll speed, one interface,
   `Int |tau_f|*|1 - h_n/h_p|` over the four sliding zones; plastic power over roll speed
   `h_n*K*ln(h0/h1)`; tension power `h_n*(t_f - t_b)`. Work identity
   `2*traction + tension - plastic - 2*slip = 0` (projected small-angle convention of `slab.py`).

NOT modelled (docstring and `limitations`): longitudinal elastic strain of strip and roll surface
in the no-slip condition, elastic unloading inside the no-slip zone and the pressure peak after it
(BT-S1 eqs (10)-(14), regime III; BT-G15); elastic entry and exit zones beyond the thickness
spring; friction varying through the bite; hardening, rate and temperature inside the bite;
tangential roll displacement; lubricant film; closed gap.

### Influence coefficients (classical; derivation for the docstring)

Surface displacement of a half-space into the solid under `p(x')`:
`u(x) = -(2/(pi*E*)) * Int p(x') ln|x - x'| dx' + const`. Pressure is piecewise linear on nodes
`x_0 < ... < x_N` with `p_0 = p_N = 0`. With `G(t) = (t^2/2)*ln|t| - (3/4)*t^2` (`G'' = ln|t|`,
`G(0) = 0`) and two integrations by parts, the hat function of node `k` gives

    I_jk = Int hat_k(x') ln|x_j - x'| dx'
         = (G(x_j - x_{k-1}) - G(x_j - x_k))/(x_k - x_{k-1})
         + (G(x_j - x_{k+1}) - G(x_j - x_k))/(x_{k+1} - x_k)

On a uniform grid of spacing `d`: `I_jk = d*(kappa(j - k) + ln d - 3/2)`,
`kappa(n) = ((n+1)^2 ln|n+1| - 2 n^2 ln|n| + (n-1)^2 ln|n-1|)/2` (`0*ln 0 = 0`):
`kappa(0) = 0`, `kappa(1) = 2 ln 2 = 1.3862943611`, `kappa(2) = 2.1711665768`,
`kappa(3) = 2.5891386521`. The form matches the triangular pressure element of contact mechanics
texts [M: not in the reports]; the derivation above is the basis.

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

### Numerical method (copy `s23/hs_bite.py`, `hs_solve2.py`, `hs_final.py`; this text is the specification)

**Grid.** Five zones with `zones = (n1, n2, n3, n4, n5)` elements, default
`DEFAULT_ZONES = (3, 16, 24, 16, 3)` (62 elements), each zone uniform between its two boundaries.
Conventional structure: `(n1, n2 + n3//2, 0, n4 + n3//2, n5)`. Node indices
`i1 = n1`, `i2 = i1 + n2`, `i3 = i2 + n3`, `i4 = i3 + n4`, `N = i4 + n5`.

**Scaling.** `L = sqrt(R*(h0 - h1))`; `X = x/L`, `P = p/K`, `H = h_p/h1`;
`a1 = L^2/(R*h1)`, `a2 = 4*K*L/(pi*E_R**h1)`, `beta = L/h1`, `cs = (h0 + h1)*K/(2*E_s**h1)`.
`H_j = G0 + a1*X_j^2 + Sum_k A_jk*P_k`, `A_jk = -a2*I_jk + cs*delta_jk` with `I` computed on `X`
(the `ln L` shift is a multiple of the load and is absorbed in `G0`).

**Unknowns** (`N + 7` foil, `N + 5` conventional): `P_1..P_{N-1}`; the boundaries
`(c_i, x_i, x_a, x_b, x_e, c_x)/L` (foil) or `(c_i, x_i, x_n, x_e, c_x)/L`; `G0`; `H_n` (foil).

**Equations**, in this order (`dX_j = X_{j+1} - X_j`, `P_m = (P_j + P_{j+1})/2`,
`Tm = min(mu*P_m, m/2)`):

| block | rows | equation |
|---|---|---|
| E1 | nodes `0..i1` | `H_j - h0/h1 = 0` |
| E2 | 1 | `P_{i1} + t_b/K - (2*mu*L/h0)*trapz(P, zone 1) - 1 = 0` |
| E3 | elements `i1..i2-1` | `((H_j + H_{j+1})/2)*(P_{j+1} - P_j) - (H_{j+1} - H_j) - 2*beta*Tm*dX_j = 0` |
| S1 (foil) | 1 | `3*H_{i2} - 4*H_{i2-1} + H_{i2-2} = 0` (zero slope of `h_p` at `x_a` from upstream) |
| E4 (foil) | nodes `i2..i3` | `H_j - H_n = 0` |
| E5 | elements `i3..i4-1` | `((H_j + H_{j+1})/2)*(P_{j+1} - P_j) - (H_{j+1} - H_j) + 2*beta*Tm*dX_j = 0` |
| S2 | 1 | `3*H_{i4} - 4*H_{i4-1} + H_{i4-2} = 0` (zero slope at `x_e` from upstream) |
| E6 | nodes `i4..N` | `H_j - 1 = 0` |
| E7 | 1 | `P_{i4} + t_f/K - (2*mu*L/h1)*trapz(P, zone 5) - 1 = 0` |

Count: foil `(n1+1) + 1 + n2 + 1 + (n3+1) + n4 + 1 + (n5+1) + 1 = N + 7`; conventional
`N + 5`. A test asserts both.

**Jacobian.** Analytic in the pressures, `G0` and `H_n` (the residuals are polynomial in them;
`dH_j/dP_k = A_jk`; the cap makes `dTm/dP_m` equal to `mu` or 0). Central differences with step
`1e-7` in the scaled boundary positions for the 5 or 6 boundary columns (each needs the
influence matrix rebuilt). Dense LU with partial pivoting in plain Python (row operations by
list comprehension, as the prototype).

**Newton.** Start from a given vector; step `du = -J^{-1} R`; backtracking: halve the step until
the trial is admissible (boundaries strictly increasing by at least `1e-9`) and
`max|R|` falls below `(1 - 1e-4*s)` times the current value; give up below `s = 1e-4`
(`ValueError`). Converged at `max|R| < 1e-11`; accepted with the flag-free status only then; a
run that ends at the iteration limit (40) with `max|R| < 1e-8` is accepted and recorded in
`convergence`; otherwise `ValueError`. No under-relaxation is used (section 0.1, finding 4).

**Cold start: homotopy from the mattress bite.**
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
   `min(P_1..P_{N-1}) >= 0` AND `H` does not increase by more than `1e-7` over any slip element.
   The second condition is essential: the slope closure S1 has a second root with `h_p`
   rising into `x_a` (planner: 50 -> 25 um, `K` 150 MPa, R 135 mm; the spurious root gave a
   39 um no-slip zone, the monotone one 344 um).
4. Structure switch during the march (at most 4): conventional -> foil when an accepted
   conventional step has `H_{i2} - H_{i2-1} > 0` (the entry branch thickens before the neutral
   point): halve the step down to 0.02 first, then convert with `x_a` = the last entry node where
   `H` still falls, `x_b = x_n + (x_n - x_a)/2`, minimum zone width 2 % of the plastic length,
   `H_n` = the smallest `H` between them, pressures interpolated; Newton with up to 40
   iterations. Foil -> conventional when the no-slip length is below 1 % of `x_e - x_i` on an
   accepted step, or when a step fails while it is below 8 %: `x_n = (x_a + x_b)/2`, accept only
   if the converged conventional solution does not thicken before `x_n`.
5. When the mattress solver rejects the pass, or the march fails: repeat steps 1-4 at a friction
   of `min(mu, 0.03)`, then `0.02`, then `0.01`, and continue in friction with warm Newton steps
   (first step `0.002`, grow by 1.3 up to `0.004`, halve on failure or inadmissible result, fail
   below `1e-5`), with the same structure-switch rule. Flag
   `COLD_START_BY_FRICTION_CONTINUATION`. Planner: 50 -> 25 um, `K` 150 MPa, tensions 20 MPa,
   R 135 mm, marched from 0.03 to 0.10 in 19 steps of 3-5 iterations.
6. Final structure check (after `lam = 1`, after every warm start and after every friction
   step), `[D, SPEC18]`: for a foil solution compute the net shear demand of the no-slip zone,
   `(h_n/2)*|p(x_b) - p(x_a)| / Int_{x_a}^{x_b} T(p) dx`. If it exceeds 1 (the zone cannot be
   held by friction at its limit over its whole length), convert to the conventional
   structure and solve; take the conventional solution if it converges with `p >= 0` and does
   not thicken before the neutral point (flag `REGIME_BOUNDARY_STRUCTURE_CHOSEN_BY_RULE`);
   otherwise keep the foil solution with `REGIME_BOUNDARY_NEITHER_STRUCTURE_ADMISSIBLE`. In
   both cases `structure_check` records the other structure's force when it converged. This
   makes the result independent of the path that reached it (section 0.1, finding 6).
7. Anything else: `ValueError` with the stage and the reason. Never a number from a failed solve.

**Warm start.** `solve_half_space_bite(..., warm_start=solution)` converts the given solution to
the scaling of the new inputs through physical units (pressures, boundaries, `g0`, `h_n`), runs
Newton (limit 25) with the admissibility test of step 3, and falls back to the cold start on any
failure.

### Public API (`physicroll/halfspace_bite.py`)

```python
STATUS = 'UNVALIDATED_REDUCED_HALF_SPACE_FOIL_BITE'
DEFAULT_ZONES = (3, 16, 24, 16, 3)
ALUMINIUM_PLANE_STRAIN_MODULUS_PA = 70e9/(1 - 0.33**2)   # strip_shape.ALUMINIUM_E_PA / _NU [M there]
def influence_matrix(x) -> list            # I[j][k-1] for k = 1..N-1, any increasing x
def hertz_self_check(elements=80) -> dict  # the table above for one grid
def solve_half_space_bite(entry_thickness_m, exit_thickness_m, width_m, work_roll_radius_m,
                          mean_flow_stress_pa, friction_coefficient, entry_tension_pa,
                          exit_tension_pa, *, roll_youngs_modulus_pa=210e9, roll_poisson_ratio=0.3,
                          strip_plane_strain_modulus_pa=ALUMINIUM_PLANE_STRAIN_MODULUS_PA,
                          shear_cap_factor=1.0, zones=DEFAULT_ZONES, warm_start=None,
                          with_solution=False)
# returns the result dict, or (dict, HalfSpaceSolution) when with_solution is True
class HalfSpaceSolution     # internal state for warm starts and package 2; not JSON, never in a result
```
Input checks: `foil_bite._check_inputs` domain (same messages with "half-space bite" in place of
"mattress bite"); `strip_plane_strain_modulus_pa` in `[1e9, 1e13]`; `shear_cap_factor` in
`(0, 1]`; `zones` five ints, `n1, n5 >= 2`, `n2, n4 >= 4`, `n3 >= 4`, sum `<= 400`.

Result keys (same names and meanings as `solve_mattress_bite` wherever both exist, so callers and
tests can read either): `status`, `model` (`'half_space_roll_rigid_plastic_slab_reduced'`),
`regime`, the eight echoed inputs, `roll_youngs_modulus_pa`, `roll_poisson_ratio`,
`strip_plane_strain_modulus_pa`, `shear_cap_factor`, `plane_strain_strength_pa`,
`separating_force_n`, `force_per_width_n_m`, `torque_per_work_roll_nm`,
`forward_slip_fraction`, `backward_slip_fraction`, `neutral_thickness_m`, `contact_length_m`,
`plastic_contact_length_m`, `entry_zone_length_m`, `exit_zone_length_m`, `contact_start_m`,
`contact_end_m`, `plastic_entry_m`, `plastic_exit_m`, `flat_zone_start_m`, `flat_zone_end_m`,
`flat_zone_length_m`, `flat_zone_share`, `contact_radius_ratio` (`L_contact^2/(R*draft)`),
`max_pressure_pa`, `mean_pressure_pa`, `plastic_work_power_over_roll_speed_n`,
`slip_dissipation_both_interfaces_over_roll_speed_n`, `net_tension_power_over_roll_speed_n`,
`max_coulomb_shear_over_yield_shear` (`mu*p_max/(K/2)`, may exceed 1 here), `shear_cap_active`,
`no_slip_zone` (`{'net_shear_over_limit', 'pointwise_shear_over_limit_max',
'friction_hill_margin_min_over_k', 'admissible', 'note'}`; `None` in the conventional regime),
`structure_check` (`{'rule', 'other_structure', 'other_structure_force_per_width_n_m',
'relative_force_difference', 'reason'}`, values `None` when no check was needed), `convergence` (`zones`, `elements`,
`newton_iterations`, `residual_max`, `homotopy_steps`, `structure_switches`, `cold_start`
(`'mattress_homotopy' | 'friction_continuation' | 'warm'`),
`mechanical_work_residual_relative`, `wall_time_s` is NOT stored: results must be reproducible),
`profile` (`x_m`, `pressure_pa`, `thickness_m`, `zone` per node; zone words `entry_contact_zone`,
`entry_slip`, `no_slip_flat`, `exit_slip`, `exit_contact_zone`), `basis` (one tagged sentence per
numbered item of the model above), `flags`, `limitations`. Absent on purpose:
`foundation_modulus_pa_m`, `unloaded_gap_m`, `limiting_thickness_m`, `stone_minimum_thickness_m`.

Flags: `REDUCED_HALF_SPACE_FOIL_MODEL` (always), `HALF_SPACE_REGIME_FOIL` /
`HALF_SPACE_REGIME_CONVENTIONAL`, `SHEAR_CAP_ACTIVE`, `NO_SLIP_ZONE_PARTLY_BELOW_YIELD_STATIC_
FRICTION` (pointwise ratio above 1 with the bounds met), `FORWARD_SLIP_LARGE_CONSTANT_FRICTION_
NO_SLIP_ZONE_MODEL` (above 0.15; the name SPEC17 package 2 introduces),
`LIGHT_REDUCTION_ELASTIC_STRIP_ZONES_NOT_MODELLED` (reduction below 0.10: elastic zones are
negligible only above 10 % [BT-S1 FT]), `PEAK_PRESSURE_ABOVE_16_PLANE_STRAIN_YIELD` (published
foil solutions peak at about 16 `Y_s` [BT-S1 FT]), `COLD_START_BY_FRICTION_CONTINUATION`,
`THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN` (exit below 0.3 mm, as today), and the two domain flags
of `foil_bite._domain_flags`, `NO_SLIP_ZONE_FRICTION_HILL_BOUND_NOT_MET` (a bound of item 6
missed by more than `1e-6*K` while the net shear is within the limit),
`REGIME_BOUNDARY_STRUCTURE_CHOSEN_BY_RULE` (the final structure check replaced the foil
solution), `REGIME_BOUNDARY_NEITHER_STRUCTURE_ADMISSIBLE` (it could not).
Rejections (`ValueError`): inputs; work residual above `1e-3`; solver failure.

### Worked numbers (planner; default zones; `E_s*` 80 GPa for the first six, R 89 mm, `Y_s` 230 MPa, `E_R*` 230 GPa)

| case | regime | `W_bar` | forward slip | contact length mm | `p_max/K` | zone lengths um |
|---|---|---|---|---|---|---|
| 20 -> 15 um, mu 0.03 (BT-V1) | foil | 92.936 (force 1902400.8 N/m) | 0.203668 | 2.03843 | 7.3315 | 7.2 / 383.0 / 1110.2 / 460.2 / 77.8 |
| same, zones `(6, 32, 48, 32, 6)` | foil | 93.299 | 0.2033 | 2.042 | 7.366 | 7.2 / 384.3 / 1112.2 / 461.8 / 76.7 |
| 140 -> 70 um | conventional | 46.82 | 0.0709 | 3.058 | 2.20 | - |
| 60 -> 30 um | conventional | 68.03 | 0.2180 | 2.446 | 5.75 | - |
| 30 -> 15 um | foil | 207.13 | 0.4769 | 3.156 | 11.30 | - |
| 20 -> 10 um | foil | 408.60 | 0.5091 | 4.217 | 11.86 | - |
| BT-V1 with `E_s*` 40 GPa / 160 GPa / 1e13 Pa | foil | 96.751 / 90.933 / 88.937 | 0.2029 / 0.2041 / 0.2046 | - | - | - |

BT-V1 work residual 4.5e-6; neutral thickness 18.0550 um; boundaries
-1.15102 / -1.14379 / -0.76082 / 0.34941 / 0.80957 / 0.88742 mm; 22 Newton iterations over the
march; 0.9 s; net shear of the no-slip zone 0.211 of the limit. Regime scan with the final
structure check, r = 0.5: 56 um conventional (`W_bar` 75.68), 52 um conventional (88.70; the
foil structure gives 88.10 and needs 1.11 times the limit), 48 um foil (100.31, no-slip share
0.187, net shear 0.79), 44 um foil (114.82); r = 0.25: 36 um conventional (40.19), 32 um foil
(48.42, share 0.151, net shear 0.97), 28 um foil (58.03); r = 0.10: 30 um conventional (21.86),
26 um foil (25.94), 22 um foil (31.51). Shear cap (50 -> 25 um, `K` 150 MPa, tensions 20 MPa,
R 135 mm, `E` 210 GPa, `E_s*` 80 GPa): at mu 0.03 the final check returns the conventional
structure, force 1.5479e6 N/m, slip 0.3655, `p_max/K` 10.28 (the foil structure: 1.5223e6 N/m,
no-slip zone 344 um, net shear 1.09); the mattress solver rejects this pass at mu 0.05 and
0.06; marching in friction the prototype switches to the foil structure at 0.032 and gives
7.7182e6 N/m at mu 0.05 (slip 0.5565, `p_max/K` 19.18, cap active from about 0.036) and
4.8652e7 N/m at mu 0.10 (slip 0.6925, `p_max/K` 34.39, no-slip zone 10.5 mm): a load 31 times
that at 0.03. Pin the implementation's own values after checking that each agrees with these
to 0.5 %.

### Tests (`tests/test_halfspace_bite.py`)
- `test_uniform_grid_closed_form`: the three `kappa` values to `1e-10`; `I_jk` to `1e-12`.
- `test_hat_integral_against_quadrature`: nodes `0.03, 0.1, 0.22`, field point 0:
  `-0.2099798413` (`1e-8`); a midpoint-rule quadrature of the test agrees to `1e-6`.
- `test_hertz_line_contact_recovered`: 80 elements, all nodes `<= 3.0e-3`, inner nodes `<= 1.0e-3`
  of `a^2/(2R)`; 160 elements `<= 1.3e-3` and `<= 3.5e-4`; the error falls with refinement.
- `test_equation_count`: both structures.
- `test_winkler_limit_reproduces_the_mattress_solver`: `lam = 0` on BT-V1 inputs: Newton in at
  most 5 iterations, force within 1.0 % and forward slip within 0.002 of `solve_mattress_bite`.
- `test_bt_v1_values` (the first row to `1e-4` relative after pinning); `test_bt_v1_grid`:
  doubled zones change the force by less than 1 %.
- `test_regime_follows_the_published_boundary`: r = 0.5: 56 um conventional, 48 um foil;
  r = 0.25: 36 um conventional, 28 um foil (eq. 29 gives 51.2 and 36.2 um).
- `test_sheet_gauge_close_to_the_mattress_and_slab`: 300 -> 210 um, R 0.2 m, Y 270 MPa, mu 0.03,
  tensions as the lengthwise demo case pass: force within 8 % of `solve_mattress_bite`
  (planner 1.9963e6 against 1.8905e6 N/m).
- `test_work_identity` (residual below `1e-4` on five cases); `test_admissibility_fields`;
  `test_spurious_slope_root_is_rejected` (the cap case solved in the foil structure at mu 0.034
  has a no-slip zone above 0.5 mm and `h_p` non-increasing in both slip zones);
  `test_final_structure_check` (cap case at mu 0.03: conventional, the other structure's force
  within 2 %, flag set; the result is the same from a cold start and from a warm start out of
  the mu 0.034 solution).
- `test_shear_cap`: mu 0.05 on the cap case solves, `shear_cap_active`, the mattress solver
  raises; `shear_cap_factor=0.5` at mu 0.10 gives a lower force than factor 1.0 (planner
  1.853e7 against 4.8652e7 N/m). Mark the mu 0.10 march as the slowest test (about 3 s).
- `test_strip_modulus_trend` (softer strip, higher load); `test_warm_start_equals_cold_start`
  (1e-8 relative); `test_rejections`; `test_json_safe`; `test_no_wall_time_in_result`.
- Timing guard: the 15 demo passes of `s23/demo.py` (hard-code their inputs) solve cold in
  under 20 s in total (planner 6.5 s).

### Documentation
Module docstring = the model, the derivation and the finding of section 0.1. Guide: new
section 10.3 "Reduced half-space model (`halfspace_bite.py`)": model, what is left out and why,
the benchmark table with the 0.79, the regime-boundary agreement, the load rise on the demo
schedule, "not used by any default". Section 13 row; section 14: three limitations (reduced
model; rigid in plane; no friction distribution). Section 15: BT-S1, BT-S4, BT-S14 with read
tags. Gap study section 11: BT-G1 `REDUCED_MODEL_OPT_IN` (after package 2), BT-G5
`REDUCED_MODEL_OPT_IN` (cap in the half-space solver only; `slab.py` and the mattress still
reject; no friction distribution).

### Must not change
No existing module is touched (`physicroll/benchmarks.py` follows in package 2). The five
artifact pairs are byte-identical (G6.3: zero differences).

### Do not
- Do not tune `E_s*`, the zone counts or the closures towards 118.
- Do not add eqs (10)-(14), elastic unloading or a pressure peak "by analogy": none is in the
  reports in usable form (only eq. (14a) is restated, without its zone logic).
- Do not replace Newton by an under-relaxed shape iteration.
- Do not store wall times or iteration-dependent floats in results beyond `convergence`.

---

## Package 2 — Half-space bite: sensitivities, engine integration, benchmarks (BT-G1, BT-G5, BT-G17)

### Why
Everything downstream takes a `chatter.BiteResponse`: eight sensitivities, contact length, force,
slip. The half-space bite must sit behind the same interface, selectable, with the mattress kept.
Phase 2 needs two more derivatives per pass (friction, flow stress), which the present code gets
by extra bite derivations.

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
Each perturbed solution is found by CHORD iterations with the LU factors of the nominal Jacobian
(`u <- u - J0^{-1} R(u)`, start = the nominal solution converted through physical units,
tolerance `1e-10`, limit 30; on failure one full Newton solve from the same start; on failure
`ValueError`). Repeat with half steps; a change above 2 % in any of the twelve adds
`SENSITIVITY_STEP_NOT_CONVERGED`; half-step values are returned. A perturbed solution in the
other structure adds `REGIME_CHANGE_WITHIN_FINITE_DIFFERENCE_STENCIL` (detect by the
admissibility test; then solve that point cold).
`BiteResponse(source='supplied', flags=('DERIVED_BY_HALF_SPACE_FOIL_MODEL',
'REDUCED_HALF_SPACE_FOIL_MODEL', 'HALF_SPACE_REGIME_...', ...))`; `contact_radius_ratio`
clamped to 1 with `CONTACT_RADIUS_RATIO_CLAMPED_TO_ONE` as the mattress derivation does.
`state` = `{'solution': HalfSpaceSolution, 'result': the solve dict without its profile,
'extra': {'dforce_dfriction_n', 'dforce_dflow_stress_m2', 'dslip_dfriction',
'dslip_dflow_stress_per_pa', 'dcontact_length_dexit_thickness', 'dcontact_length_dfriction_m',
'torque_per_work_roll_nm', 'slip_dissipation_both_interfaces_over_roll_speed_n',
'load_exponent_in_friction', 'load_exponent_in_flow_stress'}}`.

Planner (chord against full Newton: identical to 7 digits; half-step change at most 1e-3):

| case (all per unit width) | `F_h` Pa | `F_hin` Pa | `F_se` m | `F_sx` m | `dF/dmu` N/m | `dF/dK` m | `f_h` 1/m | load exponent in mu |
|---|---|---|---|---|---|---|---|---|
| BT-V1 (`E_s*` 80 GPa) | -5.5756e11 | 2.7774e11 | -6.4418e-3 | -1.4705e-2 | 1.5605e8 | 2.0962e-2 | -5.0653e4 | 2.461 |
| 140 -> 70 um | -1.0589e10 | 5.0365e9 | -4.5143e-3 | -2.1458e-3 | 2.6908e7 | 5.2683e-3 | -1.4466e3 | 0.842 |

(per unit width; `dF/dK` is with respect to the plane-strain strength, multiply by `2/sqrt(3)`
for the uniaxial flow stress). Battery-foil demo schedule, material modulus 70 GPa
(`E_s*` 78.55 GPa), supplied friction 0.03:

| pass | force per width N/m, half-space (mattress) | forward slip (mattress) | contact length mm (mattress) | `Q = -dF'/dh` Pa | `N_x' = -dF'/dt_f` m | load exponent in mu |
|---|---|---|---|---|---|---|
| S1 260 -> 135 um | 7.489e5 (7.519e5) | 0.036 (0.029) | 4.642 (4.783) | 2.569e9 | 1.805e-3 | 0.68 |
| S2 135 -> 85 | 6.539e5 (6.409e5) | 0.059 (0.052) | 3.141 (3.205) | 9.024e9 | 2.345e-3 | 0.71 |
| S3 85 -> 50 | 8.032e5 (7.560e5) | 0.101 (0.100) | 2.818 (2.829) | 2.576e10 | 3.908e-3 | 1.26 |
| F1 50 -> 30 = case pass (conventional by the final structure check; foil structure 1.3935e6) | 1.3700e6 (9.586e5) | 0.237 (0.190) | 2.654 (2.384) | 1.932e11 | 1.678e-2 | 3.74 |
| ALT1 50 -> 25 | 2.6603e6 (1.4877e6) | 0.421 (0.315) | 3.407 (2.759) | 3.179e11 | 2.138e-2 | 3.04 |
| F2 30 -> 18 | 3.2442e6 (1.5360e6) | 0.368 (0.308) | 3.346 (2.317) | 6.456e11 | 2.910e-2 | 2.85 |
| ALT2 25 -> 12 | 1.0129e7 (6.188e6) | 0.553 (0.422) | 5.710 (4.422) | 2.736e12 | 8.905e-2 | 3.28 |

Prototype values of the mattress column are plain `solve_mattress_bite` calls with the same
inputs. All seven solved cold in 0.3-1.0 s plus 0.07-0.17 s for the sensitivities. On the six
sheet passes of the lengthwise demo the half-space force is 2-6 % above the mattress force.

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
- `LIMITATIONS`: one sentence when a half-space bite is used ("reduced model: 0.79 of the
  half-space reference load on the one published case").

**3. Benchmarks** (`physicroll/benchmarks.py`): append

| id | project value (planner) | reference | verdict |
|---|---|---|---|
| `BT-V1-HS` | `W_bar` 92.936, regime foil | 118 / 120 (MODEL_OUTPUT, FT) | `RECORDED_DISCREPANCY`, ratio 0.7876 |
| `BT-V2-R89-HS`, `BT-V2-R135-HS` | 42.80, 67.13 | 58 measured | `INDICATIVE_ASSUMED_INPUTS` (0.738, 1.157) |
| `BT-V3-FIG1-140UM-HS` | 46.82 | about 50 by eye | `REFERENCE_READ_BY_EYE` (0.936) |
| `BT-V3-EQ29-HS` | regime of 60 / 48 um at r 0.5 and of 40 / 28 um at r 0.25 | eq. 29: 51.2, 36.2 um (PUBLISHED_FORMULA, FT) | `CONSISTENT_REGIME` |
| `BT-X29-LOAD-EXPONENT-HS` | 2.461 at BT-V1 | 2 to 2.6 (derived by the report, slope read by eye) | `REFERENCE_READ_BY_EYE`, inside the range |

`E_s*` = 80 GPa as the source states. Tests: `test_bt_v1_hs_recorded_discrepancy_reduced_half_
space_is_0_79_of_the_reference` (ratio in `[0.77, 0.80]`, `assertFalse(0.9 <= ratio)`), software
pins, the regime test. New function `bite_model_comparison(case) -> dict` (rows per case pass
and schedule pass: mattress, Hitchcock and half-space force per width, slip, contact length,
stiffness, each or its rejection reason) and CLI `python -m physicroll.benchmarks
--bite-comparison CASE.json`; a test runs it on the battery-foil scenario and compares with the
table above to 1 %.

### Budget (measure and report)
`derive_bite_response_half_space` on the 15 demo passes: mean at most 1.0 s, worst at most 2.0 s
cold, 0.6 s warm. `diagnose` of the battery-foil scenario with `bite_model` set to
`'auto_half_space'` in a scratch copy: at most 100 s (72.6 s today); the quick profile at most
30 s (13.8 s). `tests/test_band_*` unchanged in time.

### Tests
`tests/test_halfspace_bite.py`: sensitivity table (1e-3 after pinning), chord equals Newton
(1e-6), signs (`F_h < 0`, `F_se < 0`, `F_sx < 0`, `dF/dmu > 0`), one-sided tension flag.
`tests/test_band_extended_domain.py` or a new `tests/test_band_halfspace.py` (coarse numerics):
a foil case with each of the two new options returns a bite with `HALF_SPACE_FLAG`; every lever
row, the speed-consistent block, the gauge trend and the friction stripe screen (SPEC17
package 7) use the half-space model or say why not; `bite_extras` present; with the default
option the result is identical to the run before this package (compare `result_json` of the
template case). `tests/test_band_plain.py` passes (choices, words, flags).

### Documentation
Guide 3.3 (a third row in "where the roll-bite models stand": what changes at 30, 18 and 12 um,
from the comparison of the regenerated run, with finding 5 of section 0.1), 5.3 (the option and
when to use it: to see how far conclusions depend on the bite model), 10.3 (integration, warm
start, cost), 12, 13, 14. README: two sentences. Gap study section 11: BT-G1, BT-G5 rows;
BT-G17 row extended with the new ids.

### Must not change
Default option: all five artifact pairs byte-identical except the additive `bite_extras`
not-supplied entry and `inputs.model_options` (unchanged unless the key is given). No scenario
is switched.

### Do not
- Do not make `'auto'` fall back to the half-space model.
- Do not mix bite models inside one sensitivity (the perturbed bites use the operating model).
- Do not present the comparison as a correction of the mattress numbers.

---
## Package 3 — Viscosity table, limiting shear stress, reduced friction closure (A9, BT-G3 reduced)

### Why and what the reports contain
Row BT-G3 asks for an inlet-only mixed-lubrication closure "(take the fitted functions from the
originals)". What the repository's reports actually hold:

| piece | available form | read tag |
|---|---|---|
| load sharing of friction | `mu = A*mu_c + (1 - A)*mu_v`; `mu_c` "to a certain extent a fitting parameter", typically 0.1 (or m = 0.2) | BT-S9 EX eq. 4.13-4.14 |
| valley shear | `tau_v = tau_0*asinh(eta*u_slide/(tau_0*h_v))` (Eyring) | BT-S7 EX eq. 4-6 |
| smooth inlet film | `h_s = 6*eta0*alpha*U/(theta0*(1 - exp(-alpha*Y)))` | BT-S9 EX eq. 4.1 (already in `bite_tribology.py`) |
| film-ratio landmarks | first contact below about 3; substantial contact below about 1; industrial window 0.01-0.5 | BT-S9 EX, BT-S3 EX |
| measured friction on aluminium | about 0.09 at the smallest films (5 nm), below 0.01 at the highest speed (500 nm); strip Rq 0.5 um, roll 0.06 um | BT-S6 AB; conditions BT-S7 EX |
| inlet-only analysis is sufficient for foil | statement | BT-S3 EX |
| contact-area ratio `A(Lambda)` from asperity crushing (Sutcliffe 1988; Wilson & Sheu 1988) | NOT in the reports ("the fitted functions ... were not read") | - |
| averaged Reynolds flow factors (Patir-Cheng) | NOT in the reports | from memory only |
| contact friction `mu_c(h_s, r)` of Le & Sutcliffe | NOT in the reports (trend statements only) | - |
| Eyring stress of a rolling oil, limiting shear stress `tau_L(p)` | no value, no function | - |
| Roelands viscosity law | named, no formula | - |

So this package builds the REDUCED closure that is fully specified: the load-sharing formula
with a contact-area ratio that is an INPUT curve through two points, defaulting to the two
published end points, plus the Eyring valley shear with user-supplied oil constants. It is not
one of the asperity-crushing models and must never be described as one. What a user supplies
instead of the missing functions: the two (film ratio, area ratio) points (from package 4's
identification at two speeds, or from surface replicas), the contact friction, and the oil's
Eyring or limiting shear stress if valley shear is to be computed.

Row A9: viscosity law beyond exponential plus Barus, and a limiting shear stress. No law is
given, so: a viscosity TABLE from the oil data sheet, and a supplied cap.

### Design

**A. Viscosity table** (`bite_tribology.Lubricant`): new optional field `viscosity_table`
(tuple of `(temperature_k, viscosity_pa_s)` pairs, default `None`). `validate`: at least 2
pairs, temperatures strictly increasing in `[230, 700]`, viscosities in `(0, 10]` and
non-increasing. `dynamic_viscosity_pa_s(T, p)`: with a table, `ln eta0` is interpolated linearly
in `T` between neighbouring points and continued with the end segment's slope outside
`[D, SPEC18: piecewise exponential through data-sheet points]`; then the Barus factor as today.
New method `temperature_viscosity_coefficient_at(T)` (local `-d ln eta0/dT`; the constant
coefficient without a table), used where the thermal loading parameter needs `beta`. Flag
`VISCOSITY_FROM_TABLE`; `VISCOSITY_TABLE_EXTRAPOLATED` outside the table. Case key
`tribology.lubricant.viscosity_table`: list of `{"temperature_k", "viscosity_pa_s"}` or null;
message "tribology.lubricant.viscosity_table must be null or >= 2 points with increasing
temperature and non-increasing viscosity". The four existing lubricant keys stay required (the
reference viscosity is then not used for `eta0`; say so in the result).

Worked number: points 20 / 70 / 130 C with 3.0 / 1.4 / 0.7 cSt (the data-sheet values already
quoted in the `bite_tribology.py` docstring) at a density of 800 kg/m3 (`KEROSENE_DENSITY_KG_M3`,
[M] there): `eta0(40 C) = 1.76935e-3 Pa s`; segment coefficients 0.0152428 and 0.0115525 /K.

**B. Limiting and Eyring shear** (`Lubricant`): optional fields `eyring_stress_pa`
(`[1e4, 1e9]`), `limiting_shear_stress_pa` (`[1e4, 5e9]`),
`limiting_shear_pressure_coefficient` (`[0, 1]`, dimensionless, default `None` = 0):
`tau_L(p) = limiting_shear_stress_pa + limiting_shear_pressure_coefficient*p`
`[D, SPEC18: the simplest form of the row's "tau_L(p)"; no value or law is in the reports]`.
No defaults: absent means "not supplied".

**C. Closure** (`bite_tribology.FrictionClosure`): new fields, all with defaults that keep the
present behaviour:
`model='placeholder_exponential'` (or `'load_sharing_two_point'`),
`contact_friction=0.09` [BT-S6 AB: friction at the smallest films; BT-S9 EX gives "typically
0.1"], `film_ratio_full_contact=0.01` [5 nm over the composite 0.504 um of BT-S7 EX],
`film_ratio_no_contact=1.0` [500 nm over the same; and "substantial contact below about 1",
BT-S9 EX], `valley_model='constant'` (or `'eyring'`, `'newtonian_capped'`).
Validation: `0 < film_ratio_full_contact < film_ratio_no_contact <= 10`;
`contact_friction` in `(0, 1]`, not below `mu_v`.

For `model == 'load_sharing_two_point'`:

    A(Lambda)  = clamp( ln(Lambda_0/Lambda) / ln(Lambda_0/Lambda_1), 0, 1 )
                 Lambda_1 = film_ratio_full_contact, Lambda_0 = film_ratio_no_contact
                 [D, SPEC18: straight line in ln(Lambda) through two points; an interpolation,
                  not a contact model]
    mu         = A*mu_c + (1 - A)*mu_v                      [BT-S9 EX]
    dmu/dLambda = -(mu_c - mu_v)/(Lambda*ln(Lambda_0/Lambda_1)) inside (Lambda_1, Lambda_0), else 0
    mu_v: 'constant'          -> closure.mu_v (0.008, the present [D] value)
          'eyring'            -> min(tau_0*asinh(eta*u_s/(tau_0*h_v)), tau_L)/p_mean   [BT-S7 EX]
          'newtonian_capped'  -> min(eta*u_s/h_v, tau_L)/p_mean; ValueError without a cap

with `eta = eta0(T_inlet)*exp(alpha*p_mean)` (Barus at the mean bite pressure),
`h_v = h_s` (the inlet film), `u_s` the mean sliding speed and `p_mean` the mean bite pressure,
all `[D, SPEC18]`. These three come from the bite, so the valley models need a new optional
argument: `friction_coefficient(film_ratio, closure=None, *, lubricant=None, bite_state=None)`
with `bite_state = {'mean_pressure_pa', 'mean_sliding_speed_m_s', 'film_thickness_m',
'inlet_temperature_k'}`; `friction_at_speed` / `friction_speed_curve` gain
`mean_pressure_pa=None`, `backward_slip_fraction=None` and pass them through;
`band_process._mu_inputs` fills them from the bite (`separating_force_n/(width*
contact_length_m)`; `u_s = V_r*(b + f)/2`, `b = 1 - (1 + f)*h1/h0`, `f` = forward slip).
Without them the valley models raise `ValueError('valley shear needs the bite state')` and the
row is reported as rejected, as other bite failures are.

Result of `friction_coefficient` for the new model: the present keys plus `contact_area_ratio`,
`contact_friction`, `valley_friction`, `valley_model`, `valley_shear_stress_pa` (or null),
`valley_shear_capped` (bool or null), `closure_points`; `status`
`'UNVALIDATED_REDUCED_LOAD_SHARING_CLOSURE'`; flags `REDUCED_LOAD_SHARING_CLOSURE_AREA_RATIO_
INTERPOLATED` (instead of `PLACEHOLDER_FRICTION_CLOSURE_NOT_FITTED`),
`CLOSURE_POINTS_ARE_PUBLISHED_END_POINTS` when both film-ratio defaults are used,
`FILM_RATIO_OUTSIDE_CLOSURE_POINTS` when `A` is clamped; limitations: an interpolation between
two points, measured on one experimental mill with a rough strip on smooth rolls [BT-S6 AB,
BT-S7 EX]; no dependence on reduction, roughness wavelength or lay; friction equal through the
bite; published data need a contact friction that varies with film and reduction [BT-S7 EX].
Regime words and the industrial window stay as SPEC17 package 2 defines them.

Case schema: `tribology.friction_closure` accepts the present three keys plus optional `model`,
`contact_friction`, `film_ratio_full_contact`, `film_ratio_no_contact`, `valley_model`; an
absent key takes the default; `validate_tribology` normalises a given closure to all eight keys
and an absent one to `None` as today. `band_process.friction_section`: `flags` and `note` follow
the closure model; the note of the new model: "Reduced load-sharing closure: the contact-area
ratio is a straight line in ln(film ratio) between two points. With the published end points
it reproduces friction 0.09 at a film ratio of 0.01 and the valley value at 1; it is not fitted
to a mill." `speed_consistent_critical_speed` keeps using the closure's SLOPE anchored at the
friction used (its floor `closure.mu_v` becomes the closure's valley friction).

### Worked numbers (`s23/fric.py`; defaults, constant valley friction 0.008)

| film ratio | area ratio | mu, two-point | mu, placeholder | dmu/dLambda, two-point | placeholder |
|---|---|---|---|---|---|
| 0.005 | 1 | 0.09000 | 0.08959 | 0 | -0.08159 |
| 0.0316228 | 0.7500 | 0.06950 | 0.08745 | -0.56308 | -0.07945 |
| 0.1 | 0.5000 | 0.04900 | 0.08220 | -0.17806 | -0.07420 |
| 0.380072 (battery-foil demo, after SPEC17 package 2) | 0.2101 | 0.02523 | 0.06407 | -0.04685 | -0.05607 |
| 0.5 | 0.1505 | 0.02034 | 0.05774 | -0.03561 | -0.04974 |
| 1.0 and above | 0 | 0.00800 | 0.03817 (at 1) | 0 | -0.03017 |

Eyring example: `eta0` 2.5e-3 Pa s, `alpha` 1.2e-8 /Pa, `p_mean` 4e8 Pa -> `eta` 0.303776 Pa s;
`u_s` 2 m/s, `h_v` 1e-7 m, `tau_0` 2e6 Pa (an example, not a property of any oil): Newtonian
6.0755e6 Pa, Eyring 3.66064e6 Pa, `mu_v` 0.0091516.

Benchmark `BT-V4-FILM` (film only; the friction curves of that source must be digitised and are
not encoded): 50 -> 25 um, yield 150 MPa, tensions 20 MPa, R 135 mm, oil 2.5e-3 Pa s and
1.2e-8 /Pa, composite roughness 0.3 um [BT-S3 EX]; published `Lambda_s` 0.22 at 5 m/s and 1.76
at 40 m/s (MODEL_OUTPUT, EX). `inlet_film_thickness` with the roll surface speed taken as the
quoted speed, the strip entry speed as half of it (ASSUMED: reduction 50 %, forward slip
ignored), contact radius = R (SPEC17 package 2 rule), inlet 40 C: 62.8 nm and 502.4 nm, film
ratios 0.2093 and 1.6748, ratios to published 0.951 and 0.952; with the entry speed equal to the
roll speed 0.279 and 2.233. Verdict `INDICATIVE_ASSUMED_INPUTS`. Edit the `BT-V4` entry of
`NOT_ENCODED` to "film ratio encoded as BT-V4-FILM; load and slip curves need digitising and a
friction distribution through the bite".

### Tests
`tests/test_bite_tribology.py`: table interpolation (the worked number to `1e-9`; equality with
the exponential law for two points; extrapolation flag; validation); the closure table to
`1e-5`; continuity of `mu` at both points; default closure object unchanged (every existing test
of the placeholder passes untouched); Eyring and capped valley numbers; `ValueError` paths.
`tests/test_band_v2_sections.py`: a case with the new closure and `use_computed_friction` false:
friction rows carry the new keys and flag, no bite or score differs from the same case with the
placeholder; with `use_computed_friction` true the fixed point converges (coarse numerics).
`tests/test_benchmarks.py`: `BT-V4-FILM`. Absent-input check on the template.

### Documentation
Guide 8.1: the availability table above, both closures side by side with the worked table, what
to enter, X22 answered ("neither level nor slope of the placeholder is supported; the two-point
form has the published end values by construction and an assumed shape between them"). 5.3,
13, 14, 15. Gap study section 11: BT-G3 `REDUCED_MODEL_OPT_IN` (what is missing: the fitted
crushing functions, flow factors, `mu_c(h_s, r)`, two wavelengths, coupling through the bite);
A9 `REDUCED_MODEL_OPT_IN` (table and supplied cap; no Roelands law; inlet temperature from the
roll surface is package 7's output and is not fed back in this phase).

### Must not change
Artifacts: additive only (`inputs.tribology.lubricant` gains three null keys; nothing else). No
scenario selects the new closure. `FrictionClosure()` and `Lubricant(...)` built with the present
arguments give bit-identical results.

### Do not
- Do not call the interpolation Sutcliffe's, Wilson and Sheu's or a mixed-lubrication model.
- Do not add a Roelands law, flow factors or an Eyring stress default.
- Do not make friction vary through the bite.

---

## Package 4 — Friction identified from load, torque and forward slip (BT-G6)

### Why
Row BT-G6 (BT-S3 EX, BT-S5 AB, BT-S37 SN, BT-S34 FT): slip is the cheapest friction indicator
on a mill; "inverse fit of friction to load, torque and slip; note that simple slip formulas are
unreliable". Section 0.1, finding 5, shows why it belongs here: at foil gauge the load depends
on friction to a power of about 3, and the supplied 0.03 puts the 18 um pass outside the trade
range with the half-space bite.

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
Summary over the records: the values of `mu_F`, their spread, and with two or more exit speeds
the slope `d mu_F / d ln(u)` by least squares.

**Closure points** (only with `tribology`): for each record the film ratio at `mu_F`
(`friction_at` with the record's speed and the bite at `mu_F`) and
`A = (mu_F - mu_v)/(mu_c - mu_v)` with the case closure's `mu_c`, `mu_v`. With two or more
records whose `A` lies in `(0.02, 0.98)` and whose film ratios differ by more than 20 %: the
straight line in `ln(Lambda)` through the two extreme records gives `suggested_closure`
(`film_ratio_full_contact`, `film_ratio_no_contact` for package 3). Otherwise `null` with the
reason.

**Result.** `result['process']['friction_identification']`: `not_supplied` without records;
else `status` `'IDENTIFIED_FROM_ENTERED_RECORDS_NOT_VERIFIED'`, `bite_model`, `rows`, `summary`,
`suggested_closure`, `declaration` (`{'coefficient': median mu_joint,
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
published remedy for foil slip [BT-S5 AB]; not built); the bite model's own status (mattress
0.42, reduced half-space 0.79 of the reference load on BT-V1: an identified friction absorbs
that error); flow stress taken as entered; simple forward-slip formulas are reported as
unreliable [BT-S37 SN] and none is used; no closed-gap load share.

**Report**: `band_report._process_section`: block "Friction from your pass records": one table
(record, speed, friction from force / slip / torque, joint, consistent or not), the summary
sentence, the suggested closure points, the `warn` paragraph "not applied".

### Worked numbers
BT-V2 inverted (`s23/inv2.py`; 73 -> 31.39 um, tensions 0.107 and 0.132 `Y_s`, `Y_s` 230 MPa,
`E_R*` 230 GPa, `E_s*` 80 GPa, measured `W_bar` 58): reduced half-space bite, `mu_F` = 0.03064
for an assumed R of 89 mm (conventional, forward slip 0.1966) and 0.02488 for 135 mm
(conventional, slip 0.2594), 5 secant steps each. The source infers 0.026 with its own model and
quotes "about 0.03" from mill tests [BT-S1 FT]. Benchmark `BT-V2-FRICTION-HS`: reference 0.026,
verdict `INDICATIVE_ASSUMED_INPUTS` (ratios 1.178 and 0.957).
Software identity for the tests: generate force, slip and torque with the mattress bite at
friction 0.027 on the battery-foil case pass; the identification must return 0.027 three times
(`1e-3` relative), `consistent`, and a flow-stress scale of 1.000 (`1e-3`).

### Budget
One record with all three quantities: at most 40 solves; under 3 s with the mattress bite,
under 10 s with the half-space bite. Report the measured times.

### Tests (`tests/test_band_friction_identification.py`, coarse numerics)
The identity above for the mattress and the half-space model; a record with a slip the model
cannot reach gives `NOT_FOUND` and the flag; two records at two speeds give a slope and, with
tribology, closure points that reproduce the two frictions when fed to package 3's closure
(`1e-3`); validation messages; `not_supplied`; every hypothesis, score and bite identical with
and without records; report block renders and escapes. `tests/test_benchmarks.py`:
`BT-V2-FRICTION-HS`.

### Documentation
Guide: new 8.5 "Friction from load, torque and forward slip" (method, the three single-quantity
values and what their disagreement means, the BT-V2 numbers, how to log a record: steady window
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

## Package 5 — Flow stress: rate, temperature, law forms, fit to pass strengths (B1, B2)

### Why
B1 (X1; TM-LB1 EX, TM-LB10 EX, PT-T31, PT-T39): rate sensitivity is zero and there is no
temperature term; a measurement on 16 um 1235-H18 foil gives m about 0.027 over 1e-5 to
1e-2 /s; 1100-H18 loses 12 % between room temperature and 100 C. The two partly cancel at
rolling conditions "by an unknown amount". B2 (X2; TM-LB2 EX, TM-LB4 EX): the sign of the late
hardening slope differs by alloy group; the law form allows only a positive slope. The alloy
group table is SPEC17 package 3 (B3). No fitted parameter set for any alloy at rolling rate
exists in the reports: this package builds law forms, a fit routine and reporting, and ships no
new default numbers.

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
- Damping share at BT-V1 (half-space values of package 2: `F'_K*K = 2.096218e-2*2.3e8 =
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
## Package 6 — Computed bite heat partition (A3, X4)

### Why
Row A3 (TM-LA1 to LA4 AB, TM-LA19 AB, PT-T34): the strip's share of the bite heat is a supplied
number; the modelled stripe height moves from 0.61 to 3.4 um over the published share range. The
row names a Tseng-type interface: strip thermally thin, roll a half-space over the contact time,
`q_roll = (T_strip - T_roll_s)/(1/h_c + sqrt(pi*t)/(2*e_roll))`, `h_c = k_oil/h_s`, friction heat
at the interface, plastic heat in the strip. X4: the sheet demo's share 0.84 has no source.

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
`lubricant.effective_conductivity_w_mk()/film_thickness_m` [row A3; conductivity default 0.13
W/mK is [M] in `bite_tribology.py` and flagged there]; roll properties from `width_model.roll`
when present, else the defaults of `roll_thermal.RollThermalProperties` (basis text);
`T_r0` = `width_model.coolant_temperature_k`, else `tribology.inlet_temperature_k`, with the
basis in the result and the flag `ROLL_ENTRY_TEMPERATURE_ASSUMED_COOLANT_OR_OIL` (package 7
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
60 % plastic and 40 % friction heat at 70 nm: 0.2113. Roll transient resistance 1.0073e-6
m2K/W against 5.385e-7 for the 70 nm film. Sheet check, 0.25 mm and 0.4 ms, perfect contact,
lumped: 0.6063, Fourier number 2.42.

Benchmark `TM-LA19-HEAT-SPLIT` (function inputs: exit thickness 24 um, exit speed = roll surface
speed = 10 m/s, contact length 2 mm, roll `k` 43, density 7200, specific heat 500, equal entry
temperatures, heat 1 W/m of plastic work): the first number (0.1621, interface conductance 1e12)
and the 70 nm value (0.2254) against
the measured strip share 0.11-0.33 (MEASUREMENT, AB; gauge and speed not in the abstract):
verdict `INDICATIVE_ASSUMED_INPUTS`, note "inside the measured range".

### Tests
`tests/test_bite_tribology.py`: closed form against the scheme (`1e-5`); the six numbers
(`1e-4`); energy balance (strip plus roll equals the input to `1e-9`); limits (`h_c -> 0`: share
1; equal temperatures and zero heat: no change); hotter roll than strip gives a share above 1
and the flag; validation. `tests/test_band_v2_sections.py`: heating rows carry the block; with
the option false the result without the new keys equals the result before the package (compare
`result_json` after deleting the new keys); with the option true the roll heat fraction of the
width model follows. `tests/test_band_plain.py` with the two questions.

### Documentation
Guide 8.2 (model, numbers, X4: "the entered 0.84 of the sheet demo is not supported; the
computed value for that pass is ..." read from the regenerated artifact), 3.12, 5.3, 13, 14.
Gap study section 11: A3 `REDUCED_MODEL_OPT_IN` (lumped strip; no asperity conductance; not
calibrated; not width-resolved), X4 `TEXT_CORRECTED`.

### Must not change
Artifacts: additive (`inputs.tribology` two null keys; `heat_partition` blocks and one
comparison key per heating row). The demos keep `use_computed_heat_partition` absent.

### Do not
- Do not change `strip_heat_fraction` of any scenario.
- Do not add an asperity conductance model or a default interface conductance.
- Do not feed the computed strip temperature into the flow stress or the film (I1, Phase 2).

---

## Package 7 — Roll surface layer within one revolution (A4, G8; X5 in part)

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
Package 6 link: when the section exists, the case pass's heat partition takes `T_r0` =
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

## Package 8 — Spray coefficient calibration routine (A5, the routine)

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

## Package 9 — Guided app (plant-facing inputs and plain words for packages 2 to 8)

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
| `closure_contact_friction`, `closure_full_contact`, `closure_no_contact` | the three closure keys | number | Friction on metal contact; film ratio with full contact; film ratio with none |
| `rate_sensitivity`, `rate_reference`, `temperature_softening`, `rate_reference_temperature`, `use_rate_temperature` | `hardening.rate_temperature.*` | number, 1/s, percent per K, degC, yesno | How much the metal's strength rises with speed and falls with temperature |
| `spray_arcs` | `width_model.circumferential_layout.spray_arcs` | list: start (deg after the roll gap), length (deg) | Where around the roll the sprays hit |
| `roll_scan_kind`, `roll_scan`, `roll_scan_delay` | `width_model.spray_calibration.*` | choice, list, s | Roll temperature along the barrel after a stop |

Help texts state where a value comes from and give the published numbers with their status in
plain words ("one laboratory measurement on 16 um foil: 0.027, at speeds far below rolling").
New units if absent: `mPa s`, `kN m`, `percent_per_k`, `1/s`. List questions that map to
parallel arrays or lists of objects need the two-way conversion and a round-trip test
(`test_round_trip_case_answers_case` for every preset). Eyring and limiting shear stress,
backup contact and the shear cap stay in "Model settings" with expert wording.

**Summary views** (`plain_summary`; numbers from the result only; extend the view tuple of
`test_summaries_build_and_keep_engine_numbers`):
- `roll_gap_model_view`: which roll-gap model ran and, for the half-space model, the fixed
  sentence "This roll-gap model gives 0.79 of the published load on the one case that can be
  checked; the standard foil model gives 0.42." (both numbers read from
  `benchmarks.run_case`, not typed).
- `friction_records_view`: per record "Your force of {F} kN corresponds to a friction of {mu}
  in this model; your forward slip to {mu2}." and "They agree / do not agree within the stated
  measuring error." Fixed sentence: "Nothing was changed; enter the value yourself if you want
  to use it."
- `heat_share_view`: "You entered that {a} % of the heat stays in the strip; the tool's own
  estimate is {b} %."
- `roll_surface_view`: "Just before the roll gap the roll surface is at {x} C at the band
  position and {y} C beside it; the average the model works with is {z} C."
- `flow_stress_view`: the factor per pass and the sentence that the speed effect is an
  extrapolation.
- `FLAGS`: check every flag of packages 2 to 8; `GLOSSARY`: "forward slip", "heat share",
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

1. **Is a reduced half-space bite at 0.79 of the reference worth shipping?** Choice: yes, opt-in.
   It reproduces the published regime boundary and load exponent, removes the rejection at
   friction above 0.05, and returns the two derivatives Phase 2 needs. Reaching 118 needs the
   elastic no-slip equations (10)-(14) of the source (gap BT-G15, Phase 3 in the study) and the
   paper's solution method; the reports hold neither in usable form. The owner can settle this
   by supplying the paper (BT-S1, 13 pages) or by moving BT-G15 forward.
2. **Default bite model.** Choice: unchanged (`'hitchcock'`; the demos keep `'auto'` with the
   mattress fallback). A switch would move every foil force (plus 43 % to plus 110 % on the
   demo passes), strip stiffness, slip, heat and through them the scores, on the strength of a
   model that is itself outside the agreement band. If the owner wants the switch after seeing
   the comparison of package 2: it moves all battery-foil artifact numbers that depend on the
   bite (`bite`, `chatter`, `levers`, `schedule_sweep`, `width.shape`, `gauge_trend`,
   `thermal_check` pass rows, `process`), every product-survey row whose bite is a mattress bite (18 mattress derivations
   in a survey run today), and the pinned expectations of `tests/test_band_foil.py`,
   `test_band_extended_domain.py`, `test_band_survey*.py` and `test_band_plain.py` (not counted
   here); it needs its own brief.
3. **Shape of the contact-area ratio between the two points** (package 3): a straight line in
   the logarithm of the film ratio. Alternative: linear in the film ratio. Neither has a
   source; the log form spreads the transition over the two decades the measurements span.
4. **Default end points of the closure** (0.01 and 1.0, contact friction 0.09): taken from one
   abstract and one manuscript excerpt on an experimental mill with a rough strip. Choice: keep
   them as defaults of an opt-in model, flagged. Alternative: no defaults, both points required.
5. **Where the friction-heat is released** (package 6): half on each side of the film. With a
   70 nm film and 40 % friction heat the strip share is 0.197 with all of it on the roll
   side, 0.211 with half, 0.225 with all of it on the strip side.
6. **New inputs in the committed demos.** Choice: none (no pass records, layout, rate factor,
   new closure or computed heat share in any scenario); the guide shows the features on scratch
   copies of the battery-foil case and quotes numbers produced by tests. Alternative: one new
   scenario file "battery foil, Phase 1 models" with its own artifact pair (about 100 s to
   regenerate).
7. **Calibration from the app** (package 9): command line only in this block. Alternative: a
   new server route and a progress card; about 300 more lines and a new invariant for the app.
8. **Strain rate from the undeformed arc** (package 5): avoids a fixed point between flow stress
   and bite. On the demo's foil passes the half-space contact is 1.6 to 4.3 times the undeformed
   arc, which lowers the rate factor by 1 to 4 % at m = 0.027. Alternative: iterate with the bite (two more derivations
   per pass).
9. **Friction ladder of the cold start** (package 1): 0.03, 0.02, 0.01. Analyst choice from the
   domain in which the mattress solver accepts foil passes.

## 4. Risks: where an exactly implemented result could still mislead a plant user

| risk | mitigation built into the outputs |
|---|---|
| "Half-space" sounds like the published model. It is a reduced form that gives 0.79 of the published load on the one checkable case, and nobody knows its error on a real foil pass. | The model word everywhere is "reduced half-space"; status `UNVALIDATED_REDUCED_HALF_SPACE_FOIL_BITE`; the benchmark test is named a recorded discrepancy; the app sentence carries both 0.79 and 0.42. |
| Two foil models now disagree by a factor of up to 2 in force and more in stiffness. A user may pick the one whose answer he likes. | `bite_model_comparison` prints both with the same friction; guide 3.3 says that the spread is a measure of what is not known, and that friction (exponent about 3) is the larger unknown. |
| With the half-space bite and the entered friction 0.03 the 18 um and 12 um loads leave the trade range (3.2 and 10 kN/mm against 0.9-2.3). Read alone this looks like a mill overload. | The existing credibility marks apply; guide 3.3 gives the friction that would bring F2 back (about 0.027) and points to package 4. |
| The shear cap lets the solver return numbers at friction 0.10 that no mill could run (48 kN/mm, a 10 mm no-slip zone, 34 `Y_s` peak pressure). | Flags `SHEAR_CAP_ACTIVE`, `PEAK_PRESSURE_ABOVE_16_PLANE_STRAIN_YIELD`; the guide repeats X24: a nominal 0.10 is not the published case. |
| An identified friction looks like a measurement. It absorbs every error of the bite model, of the entered flow stress and of the closed-gap load share that is not modelled. | Status `IDENTIFIED_FROM_ENTERED_RECORDS_NOT_VERIFIED`; `calibrated` false; three single-quantity values shown side by side; never applied. |
| The two-point friction law gives 0.025 at the demo's film ratio, close to the entered 0.03 and to the published 0.026. This agreement is partly built in (the end points are the published ones) and partly luck (the shape is assumed). | Flag `CLOSURE_POINTS_ARE_PUBLISHED_END_POINTS`; limitations; guide 8.1 says in one sentence why the match is not evidence. |
| The rate factor at rolling speed (about 1.5) is an extrapolation over five decades; the temperature factor pulls the other way; entering one without the other biases every force. | Flag on every pass; guide 8.3 "enter both or neither"; no defaults. |
| The computed heat share (0.16-0.34 at foil gauge depending on the film) looks more certain than the entered 0.22. It rests on a smooth-film thickness and a remembered oil conductivity. | Reported beside the entered value, used only on request; basis strings; the film sensitivity (70 nm: 0.23, 200 nm: 0.34) in the guide. |
| The surface cycle shows the mean-coefficient model over-stating cooling by 8 % in the example. A reader may scale the spray coefficient by it. | Limitation "one-way"; the Do-not of package 7; the guide ties it to the open basis question X3 instead of resolving it. |
| A fitted spray coefficient inherits the errors of the heat share, bite heat and background coefficient it holds fixed. | `limitations`; the misfit curve and the 10 % range are always returned; nothing is written back. |
| The rate share of chatter damping (about 9 % of the heuristic at m = 0.027) may be read as "the heuristic is 10 times too large". | Note in the block: the heuristic stands for bite dynamics as a whole (gap C3), of which rate sensitivity is one part. |

## 5. Interfaces Phase 2 will consume

| Phase 2 item | what it needs | what Phase 1 provides, and where |
|---|---|---|
| A2, BT-G4 in full (I2): local friction and flow stress across the width | force per width as a function of local friction and flow stress, per pass | `state['extra']` / `result['bite_extras']`: `dforce_dfriction_n`, `dforce_dflow_stress_m2`, the slip derivatives, load exponents (package 2); for other bite models `band_process.friction_force_sensitivity` / `flow_stress_sensitivity` as today. Divide by the width for `p_mu`, `p_Y` of the row's `dp(z) = p_Y*dY + p_mu*dmu` |
| the same | a bite re-solved at a perturbed state without a cold start | `solve_half_space_bite(..., warm_start=...)`, `_BiteCache.state` (packages 1, 2, 4) |
| A2: film and friction from local temperature | roll surface temperature at bite entry per axial station | `width.roll_surface_cycle.bite_entry_temperature_k` on `z_m`; `roll_skin.unit_solutions` for transients of the weight or the flux (package 7) |
| A2 | viscosity, film and friction as functions of a temperature | `Lubricant.dynamic_viscosity_pa_s`, `temperature_viscosity_coefficient_at`; `friction_coefficient(...)['dmu_dlambda']`; `d ln(Lambda)/dT = -beta(T)` (package 3) |
| A2 | flow stress as a function of temperature and rate | `RateTemperatureFactor.factor`; `d ln Y/dT = -c_T/(1 - c_T*(T - T_ref))` (package 5) |
| A1 computed (I3): strip temperature across the width | strip exit temperature for local heat, film and roll temperature | `bite_tribology.heat_partition(...)` is a pure function of local inputs: call it per station with `roll_entry_surface_temperature_k` from package 7 (package 6) |
| G5 controller, A6 step-test emulation | surface and bulk time scales; response of the surface layer to a valve change | `width.roll_surface_cycle.time_scales`; `roll_skin.surface_cycle` with a changed spray arc level (package 7) |
| BT-G12 starvation | film thickness as an explicit input of friction and heat partition | `friction_coefficient(film_ratio, ...)` and `heat_partition(interface_conductance_w_m2k=...)` take the film from the caller, so `min(h_s, h_supplied)` can be inserted without touching them |
| C1, BT-G13 speed and tension gauge control | forward slip and force derivatives with respect to tensions and friction from one consistent bite | the twelve derivatives of package 2; `process.friction_identification.summary` for a friction-speed slope from plant records (package 4) |
| A5 flow scaling, G5 | a calibrated mean coefficient and its uncertainty range | `calibrate_spray_coefficient(...)['range_within_10_percent_of_minimum_w_m2k']` (package 8) |
