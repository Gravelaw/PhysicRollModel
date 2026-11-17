# Band / chatter-mark root-cause screening

Status of every result: `SCREENING_RESULT_NOT_PLANT_VALIDATED`. This is an opt-in,
standard-library-only screening tool on synthetic, uncalibrated models. It ranks candidate
mechanisms for transverse or lengthwise strip bands by an **ordinal evidence tally** and
shows which mill levers move the model result. It does not produce probabilities and does
not certify a cause. Nothing here has been compared with plant data.

## 1. Purpose and scope

The plant problem: transverse "stress marks or bands" on aluminium strip from a cold mill,
reported as more frequent at thinner gauges, with the questions whether coolant/spray
set-up and mill parameters (force, speed) affect band formation.

The tool combines:

- `physicroll/chatter.py` - linear third-octave gauge-chatter model of one four-high stand
  (bite sensitivities from the repository slab model with Hitchcock flattening, or
  supplied), eigenvalue stability, critical speed, forced response, time simulation;
- `physicroll/band_signatures.py` - pitch laws, roll / gear / bearing / coil source
  catalogue, resonance speeds, yield-point (Lueders) bending window, herringbone, forward
  slip, inlet film, spray coverage and free thermal growth screens;
- `physicroll/band_diagnosis.py` - case file, `diagnose(case)`, hypotheses and evidence
  rules, levers, pass-schedule sweep;
- `physicroll/band_report.py` - self-contained HTML report with inline SVG charts;
- `physicroll/band_cli.py` - command line.

Twelve hypotheses are screened: third-octave self-excited chatter, fifth-octave roll-stack
resonance, work-roll-borne marks, backup-roll-borne marks, order-locked drive or bearing
excitation, torsional / low-frequency drive vibration, coil- or mandrel-locked marks,
yield-point (Lueders Type A / coil-break) bending marks, herringbone (lubricant film
breakdown), skidding (loss of forward slip), lengthwise coolant / thermal band, lengthwise
roll-surface band.

## 2. How to run

```
python -m physicroll.band_cli scenarios/band_diagnosis_thin_gauge_chatter.json --out artifacts/band_diagnosis
python -m physicroll.band_cli scenarios/band_diagnosis_bearing_order.json --out artifacts/band_diagnosis
```

Each run writes `<case-name-slug>.result.json` (deterministic: sorted keys, no timestamps)
and `<case-name-slug>.report.html` atomically, and prints the ranked standings. On this
container (Python 3.13) the thin-gauge demo takes about 18 s (19 bite derivations at
256 cells) and the bearing demo about 9 s. The generated outputs are in
`artifacts/band_diagnosis/` (not checksum-pinned).

From Python: `from physicroll.band_diagnosis import load_case, diagnose`.

### Filling in the template for a real problem

Copy `scenarios/band_diagnosis_template.json` (`synthetic: false`, which adds the flag
`USER_SUPPLIED_INPUTS_NOT_VERIFIED`). Its `notes` explain every observation field. Replace
the mill, pass and material numbers with your own (SI units). Leave an observation `null`
when nobody has looked: `null` always gives `NOT_OBSERVED` evidence and never counts
against a hypothesis. Keys are strict; unknown or missing keys are rejected.

Which observations matter most, in order:

1. **Pitch at two clearly different steady speeds** (`pitch_observations`, at least two
   speeds 20 % or more apart). This is the single most valuable measurement. If the pitch
   grows in proportion to speed (exponent of ln pitch vs ln speed >= 0.7) the source is a
   fixed-frequency vibration (self-excited chatter or a structural resonance); if the pitch
   stays the same (|exponent| <= 0.3) the source is locked to a roll, bearing, gear or coil.
   The pitch also gives the frequency `f = u/p`, which is compared with the stand modes and
   with the order-locked source catalogue.
2. **Gauge variation** at the mark frequency on the exit thickness gauge / X-ray: present for
   third-octave chatter, largely absent for fifth-octave and surface marks.
3. **Roll-change test**: does the mark disappear after a work-roll change, after a
   backup-roll change, or neither?
4. **Faces** (both or one) and **orientation** (transverse, diagonal, chevron,
   longitudinal, irregular).
5. Onset speed, where the marks first appear (bite exit, incoming coil, after bending or
   levelling), whether they are worse at thinner gauge, lengthwise band positions on the
   barrel coordinate, and a chock-accelerometer frequency if one exists.
6. Geometry for the catalogue: work-roll and backup-roll bearings (rolling elements,
   element and pitch diameters, contact angle), gear meshes, grinder-mark counts, deflector
   roll and coil diameters. Without bearings and gears the drive/bearing hypothesis is
   `NOT_OBSERVED`.

## 3. Equations and sign conventions

### 3.1 Third-octave chatter model (`chatter.py`)

`x_w`, `x_b`: upper work / backup roll displacement, positive away from the pass line; the
lower half mirrors it, so the gap and exit-thickness perturbation is `dh = 2*x_w` (no strip
elastic recovery). `dF`: separating-force perturbation, positive pushes the rolls apart.
`sigma_e`, `sigma_x`: entry / exit tensile stress perturbations. `V_r` roll surface speed
(held constant), forward slip `f = u_x/V_r - 1`.

```
M_w*x_w'' = -K_wb*(x_w - x_b) - C_wb*(x_w' - x_b') + dF
M_b*x_b'' = +K_wb*(x_w - x_b) + C_wb*(x_w' - x_b') - K_h*x_b - C_h*x_b'
K_mill = 1/(2*(1/K_wb + 1/K_h))
dF = F_h*dh + F_hdot*dh' + F_se*sigma_e + F_sx*sigma_x + F_hin*dh_in,   Q_s = -F_h > 0
df = f_h*dh + f_se*sigma_e + f_sx*sigma_x + f_hin*dh_in
F_hdot = F_h*beta*l_d/u_x          (bite-damping closure, declared heuristic)
du_x = V_r*df
du_e = V_r*[(h1/h0)*df + ((1+f)/h0)*dh - ((1+f)*h1/h0**2)*dh_in]
sigma_e' = +(E/L_e)*du_e,          sigma_x' = -(E/L_x)*du_x
```

Mechanism: the gap opens, more strip is drawn in, the entry tension rises as the integral
of the gap opening (90 degree lag), the force drops, and the force component in phase with
gap velocity feeds energy into the stack - negative damping that grows with speed. The
critical exit speed is the lowest speed where the largest eigenvalue real part crosses
zero. Results are always given for the supplied `beta` (default 0.5) **and** for
`beta = 0`, because much of the margin rests on the bite-damping closure (Hu, Zhao &
Ehmann 2006; Kimura et al. 2003). Single-DOF benchmark (unit-tested in
`tests/test_chatter.py`): `u_crit = C*(K+Q_s)*L*h0/(M*N*E)` at `omega = sqrt((K+Q_s)/M)`.

Undamped closed-form modes: symmetric family with `K11 = K_wb + 2*Q_s` (the lower one is the
third-octave candidate) and antisymmetric family with `Q_s = 0` (both work rolls move
together between the backup rolls, little gauge change; the upper one is the fifth-octave
candidate).

### 3.2 Pitch laws (`band_signatures.py`)

```
fixed frequency F:            p = u_x / F                      (pitch proportional to speed)
n marks on a roll of dia. D:  p = pi*D*(1+f)/n                  (speed independent)
order k of work-roll speed:   p = pi*D_w*(1+f)/k                (speed independent)
exit coil:                    p = pi*D_coil;  entry coil: p = pi*D_coil*h0/h1
later pass:                   p_out = p_in*h_in/h_out
```

Work-roll rotation `f_wr = V_r/(pi*D_w)`, `V_r = u_x/(1+f)`; the backup roll has the same
surface speed. Bearing orders (Randall & Antoni 2011), `r = (d/D)*cos(phi)`:
`BPFO = n/2*(1-r)`, `BPFI = n/2*(1+r)`, `FTF = (1-r)/2`, `BSF = D/(2d)*(1-r^2)`.

Other screens: bending strain `t/D` against the yield-point window
`[t/(eps_y+eps_L), t/(eps_y - sigma_t/E)]`; Lueders susceptibility (5xxx or Mg >= 2 wt% and
O temper; any H temper is cold worked); herringbone pitch about the arc of contact at
reduction >= 0.40; forward slip <= 0 skidding; inlet film
`h_s = 3*eta0*alpha*(U_r+U_s)/(theta*(1-exp(-alpha*Y_ps)))` (quoted from memory, flagged
`FORMULA_QUOTED_FROM_MEMORY_VERIFY_BEFORE_USE`) and film ratio `Lambda = h_s/Rq`; flat-fan
spray coverage; free thermal growth `dR = alpha*R*dT` (upper bound) and local gap closure
`2*dR/h_exit`.

## 4. Hypotheses and evidence rules

Each hypothesis carries `mechanism`, `model_prediction` (numbers from the models),
`evidence` items `{criterion, observed, expected, verdict, weight, basis}`, tallies,
`score`, `standing`, `confirming_test` and `levers`. `basis` is `observation` (a plant
observation), `model` (a model result) or `input` (mill/material data).

Verdicts: `SUPPORTS`, `CONTRADICTS`, `NEUTRAL`, `NOT_OBSERVED`. Weights strong / moderate /
weak. **Score = sum of supports (3/2/1) - sum of contradictions (6/2/1).** Standing:
`CONTRADICTED` if any strong contradiction; `NOT_ASSESSABLE` if nothing but
`NOT_OBSERVED`/`NEUTRAL`; `CONSISTENT_LEADING` for the non-contradicted hypotheses with the
maximum score, at least 3 **and at least one supporting plant observation** (see 4.2);
`CONSISTENT` if score > 0; else `WEAKENED`. Rank: non-contradicted first, then score
descending, then id. The score is an ordinal tally, not a probability.

Notation: `f_obs = u/p` per pitch observation; `law` = pitch-speed classification (needs two
distinct speeds); `red` = pass reduction; `u_op` = operating exit speed.

| # | id | rules (verdict, weight) |
|---|---|---|
| 1 | `third_octave_self_excited_chatter` | transverse S mod; longitudinal C str; diagonal/chevron C mod. law FIXED_FREQUENCY S str; SPEED_INDEPENDENT C str. `f_obs` within +-15 % of model dominant/onset frequency S str, else 90-300 Hz S mod, outside 60-400 Hz C str. gauge variation detected S str, not detected C mod. faces both S weak, one C mod. `u_op >= u_crit(beta)` S str; `u_crit(0) <= u_op < u_crit(beta)` S weak (inside the band set by the unvalidated closure); `u_op < u_crit(0)` C mod. onset speed within 0.6-1.6 x `u_crit(beta)` S mod, otherwise S weak. disappears after any roll change C mod. worse at thinner gauge S weak. |
| 2 | `fifth_octave_roll_stack_resonance` | orientation as 1. `f_obs` within +-15 % of the antisymmetric upper mode S str, else 500-1200 Hz S mod, below 300 Hz C str. pitch 10-40 mm S mod. gauge variation not detected S mod, detected C weak. law FIXED_FREQUENCY S mod; SPEED_INDEPENDENT S mod if `pi*D_b*(1+f)/p` within 0.05 of an integer (backup roll already marked), else NEUTRAL. order-locked catalogue source within +-10 % of the antisymmetric upper mode at `u_op` S mod (named). disappears after backup-roll change S mod. faces both S weak. |
| 3 | `work_roll_borne_marks` | law SPEED_INDEPENDENT S str, FIXED_FREQUENCY C str. pitch = `pi*D_w*(1+f)/n` within 3 % for n = 1..8 or a supplied work-roll grinder-mark count S str (n reported), no match C mod. work-roll change: disappears S str, persists C str. faces one S mod, both C weak. longitudinal C str. |
| 4 | `backup_roll_borne_marks` | as 3 with `D_b`; backup-roll change disappears S str, persists C str; disappears after work-roll change C str. |
| 5 | `order_locked_drive_or_bearing_excitation` | law SPEED_INDEPENDENT S str, FIXED_FREQUENCY C str. best gear / bearing / spindle (work roll 2x) source within 5 % S str (source, order, mismatch named); no gear and no bearing supplied NOT_OBSERVED; supplied but no match C weak. persists after both roll changes S weak. faces both S weak. longitudinal C str. |
| 6 | `torsional_or_low_frequency_drive_vibration` | `f_obs` 5-30 Hz S str, above 60 Hz C str. pitch 0.1-3 m S weak. law FIXED_FREQUENCY S mod. longitudinal C str. |
| 7 | `coil_or_mandrel_locked_marks` | pitch within 10 % of `pi*D_exit_coil` or `pi*D_entry_coil*h0/h1` S str; coil diameters not supplied NOT_OBSERVED; supplied but no match C weak (gap filled, 4.2). first seen incoming S weak. law FIXED_FREQUENCY C mod. |
| 8 | `yield_point_bending_marks` | not susceptible C str, susceptible S mod, unknown NOT_OBSERVED. diagonal/irregular S mod, chevron/longitudinal C mod. a regular law (either) C mod. first seen incoming or after bending/levelling S str; at bite exit with `red > 0.02` C str. any deflector/coil in the yield-point window S mod, none C weak. worse at thinner gauge C mod (`t/D` falls with gauge). |
| 9 | `herringbone_lubricant_film_breakdown` | chevron S str, diagonal S weak, longitudinal C str. `red >= 0.40` S mod, `red < 0.25` C mod. pitch 0.5-2 x contact length S str, > 5 x C mod. gauge variation not detected S weak. film ratio < 1 S weak. |
| 10 | `skidding_loss_of_forward_slip` | forward slip <= 0 S str, < 0.005 S mod, >= 0.02 C mod. film ratio > 3 S weak. irregular S weak, longitudinal C str. a regular law C weak. |
| 11 | `lengthwise_coolant_or_thermal_band` | longitudinal S str, any other observed orientation C str. observed band positions on a band-risk stripe S str; coolant supplied but no band-risk stripe C weak; no coolant data NOT_OBSERVED; band-risk stripes but no observed position matches C weak (gap filled). worse at thinner gauge S weak. |
| 12 | `lengthwise_roll_surface_band` | longitudinal S str, else C str. work-roll change disappears S str, persists C mod. faces one S mod. |

Missing observations always give `NOT_OBSERVED`. Each hypothesis has a concrete confirming
test from mill practice (stone the strip and measure pitch at two speeds; chock
accelerometer speed-ramp order map; roll-change test; backup-roll barrel inspection; tensile
test for a yield plateau; nozzle footprint check; ...). `recommended_next_measurements`
collects the confirming tests of the top three ranked hypotheses plus one line for each key
missing observation (pitch at two speeds, gauge variation, faces, roll-change test,
orientation).

### 4.1 Interpretations where the written rules were open

- **Observed frequencies.** `f_obs` is `u/p` for every pitch observation, plus
  `measured_vibration_hz` when given (a measured stand frequency at the operating speed).
- **Several observations, one evidence item.** A frequency band, pitch band or pitch-match
  criterion is evaluated for each observation and reported as one evidence item whose
  verdict is the **least favourable** one. One source has to explain every observation, and
  repeated observations must not be counted as independent evidence. Consequence in the
  bearing demo: the same 24.9 mm pitch at 6.0 and 7.83 m/s gives 241 Hz and 314 Hz; a
  fixed-frequency fifth-octave mode cannot explain both, and the 241 Hz observation (below
  300 Hz) contradicts it strongly.
- **Band-risk stripes.** Only `BLOCKED_NOZZLE` stripes and interior `UNCOVERED` zones count.
  The regular `NOZZLE_PATTERN` overlap alternation of a healthy header (30 single-fan zones between
  overlaps on the demo header) and the barrel-edge zones do not. Position match tolerance: one
  quarter of the nozzle pitch (analyst choice).
- **Two gaps filled by mirroring an existing rule** (both CONTRADICTS weak): coil diameters
  supplied but the pitch matches neither coil (mirrors rule 5's "lists supplied but no
  match"); band-risk stripes exist but no observed band position is on one (mirrors rule
  11's "coverage uniform").
- **Bite derivation failure.** Chatter-dependent criteria become `NEUTRAL` with expected text
  `NOT_ASSESSABLE: <reason>`; band criteria that need no model (e.g. 90-300 Hz) still apply;
  forward slip is unknown and taken as 0 in the kinematics (flag
  `FORWARD_SLIP_UNKNOWN_ZERO_USED_IN_KINEMATICS`); herringbone uses the undeformed arc
  `sqrt(R*draft)`.

### 4.2 Rule changed against the written specification

**`CONSISTENT_LEADING` now also requires at least one `SUPPORTS` item with basis
`observation`.** As written, the speed-margin criterion of hypothesis 1 (a model result,
strong support when `u_op >= u_crit(beta)`) is worth 3 points by itself, which is the
leading threshold. The template case, with every observation `null`, therefore came out
with third-octave chatter as `CONSISTENT_LEADING` - a leading cause asserted without a single
plant observation. With the change it is `CONSISTENT` (score 3) and no hypothesis leads
until something is observed. Scores are unchanged. Test:
`test_scoring_and_standing_rules`, `test_scenario_files_load_and_demos_lead`.

No other rule produced a wrong ranking on the planted-truth tests (section 8), so the rule
weights were not tuned.

## 5. Demo cases

Both are `synthetic: true` on one synthetic single-stand four-high aluminium mill: work roll
0.40 m, backup roll 1.15 m, half-stack masses 3000 / 22000 kg, `K_wb = 4e10 N/m`,
`K_h = 1.4e10 N/m`, 3 % modal damping, strip E 70 GPa, 4 m entry and exit spans, beta 0.5,
256 cells, max radius ratio 1.5. Unloaded / antisymmetric modes 118.8 and 621.1 Hz.

**Thin-gauge chatter** (`scenarios/band_diagnosis_thin_gauge_chatter.json`): AA3104-H19
final pass 0.30 -> 0.21 mm, flow stress 270 MPa, friction 0.03, tensions 25 / 30 MPa, run at
16 m/s; observations generated from the model itself (pitch `u/f_model` at 14.5 and
16 m/s = 76.5 and 84.1 mm, exponent 0.964; onset 13.3 m/s; gauge variation; both faces;
worse at thinner gauge). Result: `third_octave_self_excited_chatter` CONSISTENT_LEADING,
score 18; every other vibration hypothesis CONTRADICTED.

**Bearing order** (`scenarios/band_diagnosis_bearing_order.json`): modelled on the published
aluminium case (Innoval: 20-25 mm bands, pitch independent of speed, 315 Hz at 470 m/min =
2 x BPFI of a work-roll bearing). A BPFI order of about 18.66, 315 Hz and a ~25 mm pitch are
only mutually consistent with a ~0.28 m work roll, so this case uses a 0.284 m work roll
(radius 0.142 m) instead of 0.40 m (with 0.40 m the same bearing gives 35 mm and 221 Hz).
Bearing: 35 rollers of 16.47 mm on a 0.24 m pitch circle at 15 degrees, BPFI 18.660.
Pass 1.0 -> 0.70 mm at 7.8333 m/s; pitch 24.92 mm at 6.0 and 7.83 m/s; measured 314.3 Hz;
no gauge variation; both faces; persists after both roll changes. Result:
`order_locked_drive_or_bearing_excitation` CONSISTENT_LEADING, score 8, best match
`bearing:WR_chock_4row_TRB:2x_bpfi` (mismatch 0.01 %). Note that this pass, stable with
beta = 0.5 (`u_op/u_crit` = 0.65), would be unstable with beta = 0 (`u_crit(0)` = 4.10 m/s,
ratio 1.91): the model margin on a mill that, by construction, shows no chatter rests on the
bite-damping closure.

## 6. What the model says about thin gauges

Numbers from `artifacts/band_diagnosis/thin-gauge-chatter-demo.result.json`
(`schedule_sweep`), same mill, six passes with speeds rising and friction falling as mills
run them. Flow stress rises 190 -> 270 MPa; tensions 15/20, 20/25, 20/25, 25/30, 25/30,
25/30 MPa.

| pass | gauge [mm] | speed [m/s] | friction | R'/R | Q_s/K_mill | u_crit beta 0.5 [m/s] | u_crit beta 0 [m/s] | u_op/u_crit | u_op/u_crit(0) | onset [Hz] | pitch u_op/onset [mm] | rel. ripple per um run-out (WR 2x) | thermal gap closure (5 K, upper bound) | t/D on 0.30 m deflector |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 2.20 -> 1.40 | 3.0 | 0.08 | 1.090 | 0.68 | 12.55 | 3.37 | 0.239 | 0.89 | 145.2 | 20.7 | 4.06e-4 | 0.017 | 4.67e-3 |
| P2 | 1.40 -> 0.90 | 5.0 | 0.07 | 1.140 | 1.13 | 13.60 | 3.63 | 0.368 | 1.38 | 156.9 | 31.9 | 4.69e-4 | 0.027 | 3.00e-3 |
| P3 | 0.90 -> 0.60 | 7.5 | 0.06 | 1.212 | 1.76 | 14.89 | 4.38 | 0.504 | 1.71 | 169.7 | 44.2 | 5.41e-4 | 0.040 | 2.00e-3 |
| P4 | 0.60 -> 0.42 | 10.0 | 0.05 | 1.298 | 2.41 | 15.48 | 5.20 | 0.646 | 1.92 | 179.6 | 55.7 | 6.31e-4 | 0.057 | 1.40e-3 |
| P5 | 0.42 -> 0.30 | 13.0 | 0.04 | 1.389 | 2.99 | 15.24 | 5.61 | 0.853 | 2.32 | 186.6 | 69.7 | 7.23e-4 | 0.080 | 1.00e-3 |
| P6 | 0.30 -> 0.21 | 16.0 | 0.03 | 1.456 | 3.22 | 13.27 | 4.83 | 1.206 | 3.31 | 189.1 | 84.6 | 8.34e-4 | 0.114 | 0.70e-3 |

The same passes recomputed at the final-pass friction 0.03 (other inputs unchanged;
`at_case_friction`): critical speed (beta 0.5) 5.96, 8.27, 10.43, 12.19, 13.27 m/s for
P2..P6 (P1 at friction 0.03 rejects: no unique interior neutral point).

What the numbers say, plainly:

- **At equal friction a thinner pass is more stable in this model**, not less: the critical
  speed rises from 5.96 m/s (P2) to 13.27 m/s (P6) at friction 0.03, because the plastic
  strip stiffness `Q_s` grows faster than the entry gauge falls (`Q_s/K_mill` 1.13 -> 3.22).
  The model does not support "thinner strip is intrinsically less stable".
- With the schedule's own friction the critical speed is nearly flat (12.6-15.5 m/s) and
  drops on the last pass, where friction is lowest. What rises steadily is the
  **operating-to-critical speed ratio**, 0.24 -> 1.21, because thin passes are run fastest.
  Only the final pass crosses the critical speed. The onset frequency stays in a narrow band
  (145-189 Hz), so the pitch at the operating speed grows with speed (20.7 -> 84.6 mm).
- **Without the bite-damping closure** (beta = 0) every pass except P1 is above its critical
  speed (ratios 1.38-3.31). How much margin the thinner passes have therefore depends on a
  heuristic that has not been validated; measure before trusting it.
- The **relative gauge ripple** per micrometre of work/backup roll run-out at 2 x work-roll
  rotation doubles (4.1e-4 -> 8.3e-4 of exit gauge per um), so the same roll eccentricity is
  a larger relative defect on thin strip (P6 is an unstable operating point, so its forced
  value is formal only).
- The **thermal gap-closure fraction** of a 5 K hot stripe (free-expansion upper bound,
  12 um of radius growth) rises from 0.017 to 0.114 of the exit gauge: spray stripes matter
  more as gauge thins.
- The **bending strain** `t/D` on a 0.30 m deflector falls from 4.7e-3 to 0.7e-3, so
  bending-type yield-point marks become *less* likely at thin gauge - the opposite trend.

### Where the derived-bite path stops

The bite sensitivities come from the slab model with circular Hitchcock flattening, which is
rejected above a contact radius ratio of 1.5 (`max_radius_ratio`, may be raised to 3.0 with
the flag `HITCHCOCK_RATIO_BEYOND_REVIEWED_ENVELOPE`) and rejects with "sticking model
required" when Coulomb shear exceeds the shear yield. Probe on this mill (R = 0.2 m, width
1.5 m, 30 % reduction, tensions 10 / 11 % of flow stress, 64 cells):

| flow stress | friction | entry gauge that still derives | first rejected (reason) |
|---|---|---|---|
| 270 MPa | 0.03 | 0.30 mm (ratio 1.453) | 0.25 mm (ratio 1.536) |
| 270 MPa | 0.05 | none of 0.10-0.30 mm | 0.30 mm (ratio 1.654); 0.15 mm and below: sticking model required |
| 150 MPa | 0.03 | 0.15 mm (ratio 1.408) | 0.10 mm (ratio 1.644) |
| 150 MPa | 0.05 | 0.20 mm (ratio 1.467) | 0.15 mm (ratio 1.721); 0.10 mm: sticking model required |

So for hard alloys the derived path stops at about 0.3 mm entry gauge (0.21 mm exit) and only
at low friction; softer material reaches about 0.15-0.20 mm. On the demo final pass even the
lever variants friction x1.3 (ratio 1.532) and reduction x0.8 (ratio 1.507) are rejected.
**Thinner and foil gauges need supplied bite sensitivities**: put force, forward slip,
contact length, radius ratio and the eight sensitivities from a plant or foil (non-circular)
mill model into `model_options.bite_response_override` (`source = 'supplied'`). The levers
that need a re-derived bite are then reported as rejected; span and damping levers still run.

## 7. Levers and coolant

Lever table of the thin-gauge demo (critical exit speed, beta 0.5; baseline 13.27 m/s,
4.83 m/s with beta 0), sorted by effect size:

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

Directions are generated from these numbers (not hard-coded): lower friction lowers the
critical speed; higher reduction lowers it; higher entry tension lowers it; exit tension has
a small opposite effect; a longer entry span and more structural damping raise it. Speed
itself is the first lever: running below the critical speed. The literature disagrees on the
friction and tension effects (section 10); these are the model's numbers, not settled facts.

**How coolant and spray set-up act** in this tool:

- For **transverse marks**, through friction and film thickness. Lubricant viscosity and
  speed raise the inlet film (film ratio 0.70, boundary, on the thin demo pass), which lowers
  friction, and lower friction lowers the chatter-free speed (friction x0.7 -> ratio 0.73).
  No friction-speed or film-friction law is modelled: the user must express a lubricant
  change as a friction change. A very thick film raises the skidding risk (screen 10).
- For **lengthwise bands**, through coverage gaps: a blocked nozzle or an uncovered interior
  zone gives an under-cooled stripe, a local thermal crown and differential plate-out; the
  free-expansion gap closure grows as gauge thins. The regular overlap pattern of a healthy
  header is not counted as a band risk.
- Separating force enters through the strip modulus and the Hitchcock radius; it is not a
  free lever but follows from reduction, friction, tension and flow stress.

## 8. Verification evidence

`python -m unittest tests.test_band_diagnosis -v` (16 tests, about 40 s with cells 64):

| claim | test |
|---|---|
| planted third-octave chatter (pitch `u/f_model` at two speeds above `u_crit`) leads | `test_planted_third_octave_chatter_leads` |
| planted bearing 2 x BPFI (speed-independent pitch) leads and the source is named | `test_planted_bearing_order_leads_and_names_source` |
| planted backup-roll mark (`pi*D_b*(1+f)`, disappears after backup-roll change) leads | `test_planted_backup_roll_mark_leads` |
| planted yield-point bending marks (5182-O, incoming, diagonal, deflector in window) lead | `test_planted_yield_point_bending_leads` |
| planted lengthwise band at a blocked nozzle leads; healthy-header pattern is not a risk | `test_planted_blocked_nozzle_band_leads`, `test_healthy_header_pattern_is_not_band_risk` |
| missing observations never contradict; all twelve hypotheses present | `test_missing_observations_never_contradict` |
| score arithmetic, standings, ranking, leading rule incl. the change of 4.2 | `test_scoring_and_standing_rules` |
| bite-derivation failure degrades gracefully | `test_bite_failure_degrades_gracefully` |
| supplied bite sensitivities | `test_supplied_bite_override` |
| lever directions computed from numbers; sorted by effect | `test_lever_directions_are_computed` |
| strict keys and value validation | `test_strict_validation` |
| `synthetic: false` flag; byte-identical repeat; JSON without NaN | `test_synthetic_false_flag_and_determinism` |
| report sections, escaping of a hostile case name, no nan/inf | `test_report_sections_and_escaping` |
| CLI writes both files; bad input exits through `parser.error` | `test_cli_writes_both_files` |
| the three scenario files load; both demos lead with the intended hypothesis (cells 64) | `test_scenario_files_load_and_demos_lead` |

The physics modules have their own closed-form tests (`tests/test_chatter.py`,
`tests/test_band_signatures.py`). The planted-truth tests check that the screening logic
recovers a cause that was put in from the same models; they say nothing about whether the
models describe a real mill.

## 9. Limitations

- No plant validation; synthetic, uncalibrated stand, spans and bite parameters.
- Linear model: no limit-cycle amplitude, mark severity or strip-break prediction; a forced
  response at an unstable operating point is formal only.
- Lumped-spring strip spans, inaccurate near the span axial wave resonance `c/(2L)` (about
  640 Hz for 4 m of aluminium).
- Circular Hitchcock flattening is not valid toward foil; see section 6 for where the
  derived path stops.
- The bite-damping closure is a heuristic; beta = 0 results are always shown.
- No friction-speed law; no film dynamics; friction is an input per pass.
- Fifth-octave regeneration (backup-roll marking) is screened kinematically, not simulated
  in time; antisymmetric modes are undamped lumped estimates.
- Spray coverage is geometric only; thermal growth is a free-expansion upper bound.
- Evidence weights and several thresholds (pitch exponent bands, 0.005 slip, 1e-3 gap
  closure, quarter-pitch position tolerance, 35 m/s resonance envelope) are analyst choices.

## 10. Sources and disagreements

Tlusty, Chandra, Critchley & Paton (1982) CIRP Ann. 31:195 (abstract only read); Yun, Wilson
& Ehmann (1998) Int. J. Mach. Tools Manuf. (cited, not read); Hu, Zhao & Ehmann (2006) Proc.
IMechE B, doi:10.1243/09544054B06804, as reproduced in Heidari & Forouzan (2013) J. Adv. Res.;
Kimura et al. (2003) ISIJ Int. 43:77; Niroomand et al. (2012) ISIJ Int. 52:2245 and (2015)
55:637; Zeng, Zang & Gao (2016) Shock & Vib., doi:10.1155/2016/2347386; Innoval Technology
(Farley) mill-vibration, strip-chatter-marks and chatter-cold-rolling-mill blogs; Krueger,
Richard & Peretic (SMS group) AISTech 2019; Kim et al. (2012) ISIJ Int. 52:2042; Randall &
Antoni (2011) MSSP, doi:10.1016/j.ymssp.2010.07.017; Zhang et al. (2016) IET J. Eng.;
Heidari, Forouzan & Akbarzadeh (2014) ISIJ Int. 54:2349; Aluminum Association (2002) QCA-1;
Choi, Jin & Kang (1998) Scripta Mater. 38:887; de Codes et al. (2011) Metall. Mater. Trans. A
42; Reynolds US 4,081,294; Li et al. (2020); Mucsi (2018) Eng. Fail. Anal. 83; Komori (1996)
J. Mater. Process. Technol. 60:377; Szucs et al. (2020); Alcoa US 5,508,119 citing Schey;
Reid & Schey (1978) ASLE Trans. 21(3); Sutcliffe (2002); Lloyd (Lechler, 2010); Tucker
(Lechler, 2006).

Known disagreements: the effect of friction on chatter (Yarita: high friction worse;
Chefneux: low friction worse; Kimura: an optimum band) - this model, with slab-derived
sensitivities, gives "lower friction lowers the critical speed"; the effect of tension
(Heidari: little; Zeng, Zang & Gao: higher tension lowers the critical speed) - this model
gives a modest lowering with higher entry tension; and the lumped span versus a wave model
near `c/(2L)` (Niroomand et al. 2015).
