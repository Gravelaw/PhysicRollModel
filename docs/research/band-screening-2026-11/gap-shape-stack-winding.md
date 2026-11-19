# Literature gap study: strip shape, roll stack, web handling, winding and flatness control at thin gauge

Scope: aluminium cold rolling from about 1 mm down to foil (6-60 um), with the project's focus on
battery collector foil rolled single-sheet 50 um -> 12-19 um. Compared: `physicroll` as of this
session against published literature found by web search.

Read-status tags used throughout (never upgraded):
**[FT]** full text read; **[EX]** excerpt of the full text (search extract or part of the paper);
**[AB]** abstract only; **[SN]** snippet / title / citation only; **[VP]** vendor or trade page;
**[M]** from memory, not verified in this session; **[D]** my own derivation or arithmetic from
cited numbers. Source numbers S1... refer to section 6.

Hosts that the fetch tool could not reach in this session: `par.nsf.gov`, `link.springer.com`,
`www.lechler.com` (the first was downloaded another way and read in full; the other two were read
only as search extracts).

---

## 1. What the project has in this area

| Topic | What is implemented | Where |
|---|---|---|
| Local roll bump -> strip thickness | Half-space (Boussinesq) roll compliance to a sinusoidal line load, `C(lam)`, per Fourier component; three levels: rigid bound, compliance only `T = 1/(1+2CQ)`, and with a linear exit-tension feedback `Q_eff = Q + N_x'*E*xi/h`; band-wise slack saturation (one scale factor) | `physicroll/strip_shape.py` `roll_line_compliance_m2_n` (l. 282), `local_bump_transfer` (l. 341), `transfer_radius_profile` (l. 408), `thermal_stripe_flatness` (l. 1029); `docs/band-diagnosis.md` 7.2 |
| Elongation, I-units, residual stress | `eps = xi*(dH/H - dh/h)` with constant `xi`, `I = 1e5*(eps - mean)`, `sigma_res = -E*(eps - mean)` | `differential_elongation` (l. 610), `flatness_from_elongation` (l. 841) |
| Buckling | Rayleigh quotient with one assumed mode `sin*sin`, half-wave = band width, `k = 4`; in the mill (net compression only) and after tension release (local mode limited to 2 x half-peak width; whole-sheet mode as indicator) | `_SineModeSearch` (l. 724), `narrow_band_buckling_stress_pa` (l. 643) |
| Crown and dead band | Crown heredity `C_h = (1-eta)*C_gap + eta*(h/H)*C_H` with a SUPPLIED mechanical gap crown; Shohet-Townsend window `-80..+40*(h/w)^beta` | `crown_heredity` (l. 520), `shohet_townsend_window` (l. 548), `classify_crown_change` (l. 580) |
| Roll thermal profile | Axisymmetric, circumferentially averaged FV/ADI conduction in one work roll under a top-hat spray header; steady state and switching events; thermal radius per axial station; stripes by differencing against a healthy header | `physicroll/roll_thermal.py` `steady_state` (l. 699), `simulate` (l. 818), `local_stripes` (l. 1004); doc 7.1, 7.4 |
| Coil ridge build-up | `dRad = c*N*r` (linear in wrap count, constant compaction factor `c = 0.5`), yield when hoop strain exceeds `(sigma_y - sigma_T)/E` | `coil_ridge_buildup` (l. 1224) |
| Troughs and roller wrinkles | Cerda-Mahadevan wavelength and amplitude; Good-Beisel-Yurtcu trough and shell-wrinkle thresholds (isotropic). Lateral compressive stress is a plant INPUT | `tension_trough_screen` (l. 1339) and helpers (l. 1303-1337) |
| Positions and pitches | Two-tone edges, grinding feed pitch, spacing tests against nozzle / zone / grinding / trough pitches | l. 1427-1532 |
| Integration, hypotheses | Stripes, events, gauge trend, incoming-ridge transfer, foil regime without a bite, `foil_tension_lines` as a rule set | `physicroll/band_width.py` (docstring l. 1-70) |
| Older profile module | Diagnoses crown, wedge and membrane mismatch from SUPPLIED fields; returns `latent_flatness_prediction: None` | `physicroll/profile.py` |

What the project itself says it lacks (`docs/band-diagnosis.md` 7.1, 7.2, 14; `docs/capabilities.md`
rows "Profile and flatness", "Roll versus stand deformation"): no roll stack, bending or
backup-roll contact; no lateral flow beyond constant `xi`; no entry-tension redistribution or shear
lag; no post-buckling; no closed-gap (roll-kiss) load path; no interlayer pressure or slip in
coils; no strip tracking; no computed lateral stress in spans; no physical model of tension lines;
circumferentially averaged roll, adiabatic barrel ends; no plant validation of anything.

Not present at all, and not listed as a limitation: any model of the flatness **measurement**
(shapemeter zones) or of the **flatness control loop**; strip temperature across the width as a
flatness term; air entrainment on rollers and in the coil; ironing roll; spool deformation;
slitting; hot-edge sprays or inductors; variable-crown rolls.

---

## 2. State of the art (concise)

### 2.1 Roll stack deflection and flattening

- **Model families.** Single beam on elastic foundation (Stone); influence-coefficient /
  point-matching method of Shohet & Townsend (slit beam, iterated contact forces), extended with
  Poisson and shear deflection, Boussinesq indentation flattening (Kono, Tozawa, Guo), force-gradient
  flattening (Berger), 6-high (Pawelski), cluster mills, and foil with mutual work-roll contact
  (Matsubara); transport-matrix models with a linear strip modulus (Guo; Allwood for CVC contact
  loss); simplified mixed FEM (Timoshenko beams + continuous Winkler foundations, Malik & Grandhi);
  large-scale 3D FEM (hours per case: 52 h quoted for a full 6-high CVC model) [S1 EX, S2 EX].
- **Hacquin / Montmitonnet Lam3-Tec3.** 3D steady-state elastic-viscoplastic strip FEM on
  streamlines, coupled to a semi-analytical roll stack: Timoshenko beam + Boussinesq half-space
  flattening after Berger et al. + Hertz inter-roll contact, discretised by influence functions on a
  2D grid, Newton-Raphson for the unknown contact lines, "including roll kiss for very thin
  strips", with a barrel-end correction identified by FEM (`FEC = 2.4*(1 - r_neck/R_barrel)`)
  [S8 EX, S7 EX]. Developed with Pechiney / Alcan, i.e. for aluminium [S8 EX].
- **Accuracy of the simple models.** Against 3D FEM, the slit-beam model's errors come mainly from
  the roll-roll flattening term (Foppl) near the barrel ends and partly cancel; the residual error
  depends on the force profile type [S5 EX; the extract garbles the unit of the quoted 4 and 9-13
  figures].
- **Local roll profile errors.** The only dedicated study found is Patel, Malik et al. (2022)
  [S3 FT]: a measured warm work-roll diameter profile is fed through a 3D SM-FEM stack model for
  301 stainless, 6061-O aluminium and copper. Without bulk-body effects the transfer is governed by
  the ratio of the strip foundation modulus `kf1 = F/(w*(H-h))` to the roll flattening modulus `kf2`
  (thin-gauge aluminium, 0.236 mm entry: `kf1` = 176, `kf2` = 57.8 kN/mm2, ratio 3.04; thin
  stainless: ratio 28, transfer "almost negligible"); bulk bending / shear / flattening strengthen
  or attenuate the transfer depending on the position along the barrel; transfer rises with
  reduction (non-linearly) and falls with larger work-roll diameter; **work-roll bending leaves the
  high-fidelity deviation unaffected** ("a low-frequency filter"). The strip is a Winkler
  foundation in plane strain: no tension feedback, no lateral flow. Spray zones of 25-100 mm "may be
  insufficient to remove highly localized defects".
- **Foil and work-roll edge contact.** Influence-function models with work-roll "edge kiss" show
  the kiss force, kiss length, strip crown and edge drop depending on reduction, width, bending and
  transverse friction (Jiang, Zhu & Tieu, several papers) [S25 AB]; for thin aluminium strip the
  edge contact lowers crown and edge drop but takes away edge control authority [S25 AB]. A VC-roll
  paper gives a computed aluminium foil case (30 um x 1100 mm, 300 tf, 50 % reduction, tensions
  10 kgf/mm2, work roll 270 mm): with -40 tf bending the kiss force is about 22 % of the total, the
  **bender has little effect on the strip portion** (it bends the barrel ends), the variable-crown
  backup roll has a large one [S26 EX].
- **Actuators.** Work-roll and intermediate-roll bending, tilting, shifting / CVC, roll crossing,
  selective cooling are the usual set; bending is fast and saturates, cooling is slow and local
  [S34 EX]. Variable-crown backup rolls (Sumitomo VC roll: one oil chamber, crown by pressure
  [S26 EX]; DSR with independent pads on aluminium cold mills [S27 AB]; Achenbach DVC as an active
  actuator "with open or closed roll gap" [S28 VP]).

### 2.2 Transverse flow, residual stress, latent and manifest flatness, buckling

- **The chain.** Contact stress -> roll stack gap profile -> differential elongation and post-bite
  stress profile -> buckling model; steps 1-2 are solved strongly coupled; decoupled buckling is
  acceptable only when defects stay latent, because buckling saturates stress and reorganises the
  post-bite field [S4 EX].
- **Transverse flow.** At thin gauge the lateral displacement is negligible except near the strip
  edges (FE and lithographic-grid measurements on 0.04-0.05 mm strip, 65 mm wide) [S21 EX];
  classical variational models (Lian) and strip-element models (Liu) couple lateral displacement,
  exit tension distribution and roll force distribution [S21 EX, S22 EX]. The longitudinal stress
  profile keeps changing **outside** the bite because the exit velocity is not uniform; a
  shapemeter placed too close to the bite measures residual stress plus this transient part
  [S22 EX]. Thin wide strip makes the 3D problem numerically stiff; matched edge / interior solutions
  were developed for that reason, and the downstream stress has to be fed back into the bite
  (Dixon & Yuen, citing Tozawa) [S23 EX].
- **Coupled rolling-buckling (Counhaye; Abdelkhalek; Nakhoul).** A membrane rule that forbids
  stress below a small critical value, inserted in the rolling model, changes the far-field stress
  profile completely and brings it to the stress-meter measurement, **while the in-bite fields,
  the roll stack deformation and the roll force profile are hardly changed**; the differences sit
  in the exit velocity profile right at the bite exit; the influence is larger at very small
  reduction [S8 EX, S9 AB, S10 AB, S11 EX]. The same models were applied to heterogeneous strip
  temperature fields and thinner edges [S10 AB].
- **Buckling under tension.** Rayleigh-Ritz with a harmonic mode along the length and an optimised
  shape across the width: increasing global tension raises the critical residual stress **and
  shortens the waves and concentrates them** toward the edge (edge waves) or the centre (centre
  waves) [S12 AB, S13 AB]; a 1D-in-width finite-element version with Koiter post-buckling confirms
  it and needs no artificial boundary conditions [S15 EX]; piecewise-constant stress elements
  across the width give a fast solver for arbitrary profiles (Bush, Nicholls & Tunstall; no tension
  term separated) [S17 AB, S15 EX]. Post-buckling with tension release by the asymptotic numerical
  method [S16 EX]. A fully integrated industrial roll-deflection + buckling model reproduces the
  Fischer cases within 0.4-3.3 % [S20 EX].
- **Latent against measured-on-a-table flatness.** The stress profile does not give the wave
  height directly; under dead load a strip lies flat below a residual-stress limit and shows
  post-buckled waves above it, with large differences between the stress-based and the table-based
  flatness index [S14 AB].
- **Local (narrow, interior) buckles.** Analytical local-buckling model with a Gaussian compressive
  band, an elastic edge-restraint coefficient between simply supported and clamped, and
  perturbation post-buckling; an industrial steel case and a laboratory aluminium rolling test
  [S19 FT]. The paper notes that such "strip waves" survive annealing and turn into ridges in the
  coil.
- **Taxonomy.** Centre, edge and quarter buckle, trapped buckle ("oil can") [S67 EX]; localised
  buckles, mixed modes [S4 EX]; cross buckle and herringbone as separate shear / lubrication
  mechanisms [S75 EX]; ridge-buckle as a coil-built defect [S60 EX, S61 EX].

### 2.3 Thermal crown, zone cooling, edges, measurement and control

- **Thermal crown.** For thin hard aluminium at high speed, flatness "is primarily a problem of
  thermal-crown control"; three thermal effects with different time constants are described: the
  short-term one does not affect the thermal crown directly, the medium-term one is used for local
  shape, the long-term one for overall shape; coolant control is the slow partner of fast bending
  (Davies, Alcan, 1975) [S35 AB]. A modern thermal crown model separates a fast skin and a slow
  bulk regime and is tuned on roll surface temperature and thermal profile measurements [S71 AB].
- **Tight edges.** Thermal growth falls off at the strip edge because heat conducts along the
  barrel; cooling sprays cannot correct it; hot-edge sprays or inductors heat the roll just outside
  the strip to move the fall-off outward; claimed effects are fewer edge cracks and strip breaks and
  less bending [S36 VP]. On cold and foil aluminium mills tight edges and "tight edge / loose
  pocket" from steep temperature gradients at the strip edge "are the trigger to many strip breaks"
  [S32 EX]. Very thin foil is deliberately rolled with wavy (loose) edges, e.g. a 30 I-unit target,
  to avoid breaks [S31 EX].
- **Measurement.** Shapemeter rolls measure radial force per zone. Zone widths: ABB Stressometer 26
  or 52 mm, accuracy typically 0.5 I-units, foil roll for 0.005-0.5 mm, "max. 2 x 12.5 % force
  spreading to adjacent measurement zones" [S29 VP]; BFI-type rolls 26 / 52 mm, minimum 17 mm, or
  15-60 mm [S30 VP]; air-bearing rolls with rotors 25-120 mm (Primetals) or 25-100 mm, standard
  50 mm (IHI) [S30 VP, S31 EX]; zones are "typically 50 mm wide in the body of the strip and
  reduced to 25 or 26 mm" near the edges, signals are averaged per zone with the neighbours taken
  into account, and a tight edge and a loose pocket can fall in the same zone and be missed
  [S32 EX]. A research roll with 5 mm resolution exists as a prototype [S39 EX]. Optical gauges see
  only manifest flatness and need low tension; SI-FLAT infers the tension profile without contact
  [S37 EX, S38 AB]. Cross-width strip temperature differences give an apparent shape error at the
  measuring point (about 1.25 I-units per K for steel; several tens of K quoted for process lines)
  [S40 VP, S41 AB].
- **Control.** Measured shape error -> least-squares projection on actuator sensitivity vectors
  computed by level-2 models; bending for the low-order parts, tilting for asymmetry, selective
  cooling for the residual; cooling zones are built at the shapemeter pitch (25-100 mm) and each
  spray is driven by "its" zone [S34 EX, S33 EX, S31 EX]. Foil example: accuracy within 6 I-units
  at steady speed [S31 EX].

### 2.4 Web handling at foil gauge

- **Troughs and wrinkles.** Troughs are plate buckling of the free span; wrinkles are shell
  buckling on the roller and need lateral stresses two to three orders of magnitude larger; troughs
  are a necessary precursor; the lateral compression comes from roller misalignment, taper, roller
  deflection, tension drop across a driven roller, or a bent wound roll (Shelton; Good, Beisel &
  Yurtcu) [S54 EX, S56 SN]. Closed forms give the critical misalignment or taper; verified on
  23.4 um polyester [S54 EX].
- **Foil is different.** For wide aluminium and copper foil below 25 um the isolated-span
  shear-wrinkle model is "not a good predictor": wrinkles appeared at misalignments 7-10 times
  (copper) and about 15 times (aluminium) larger than predicted, because the low strain of a stiff
  foil brings a slack edge and moment transfer to the upstream span almost immediately; a traction
  limit (Regime II) bounds wrinkling at low tension [S55 EX].
- **Air film and traction.** Foil-bearing equation `h = 0.643*R*(6*mu*(V_web+V_roller)/T)^(2/3)`
  (Knox & Sweeney); traction is lost when the film exceeds about three times the combined rms
  roughness; grooves and roughness restore it; a slipping web no longer obeys the normal-entry
  rule, so it wanders but wrinkles less [S58 EX/AB]. Wrinkle and slip maps with an air-film
  dependent friction were verified on PET [S57 EX].
- **Baggy lanes.** Cross-width length differences ("web bag strain", the web-handling word for
  latent flatness) are measured as strain; thick lanes that stretch over a ridge in the roll come
  out as baggy lanes after unwinding [S59 EX, S53 EX].

### 2.5 Winding and downstream

- **Wound-roll stress.** Accreted-hoop models: Altmann (linear anisotropic), Pfeiffer's
  pressure-dependent radial modulus `E_r = K2*(P + K1)`, Hakiel's incremental equation
  `r^2*d2(dS_r)/dr^2 + 3r*d(dS_r)/dr - (E_t/E_r - 1)*dS_r = 0` with the outer-lap condition
  `dS_r = -T_w*h/s` and a core-stiffness condition, solved lap by lap [S42 EX, S43 AB]. For metal
  coils the same structure appears as wrap-by-wrap models with asperity compressibility about two
  orders of magnitude softer than the bulk (Wadsley & Edwards, as retold in [S40 VP]; laminated
  compression tests in [S63 EX]), plus sleeve and mandrel compliance.
- **Thickness variation across the width.** Pseudo-2D models (Hakiel; Kedl; Cole & Hakiel) run one
  1D model per width segment and allocate the winding tension to segments from the outer-lap
  radius via a "relaxation radius"; verified on PET with a segmented instrumented core and an
  outer-lap profilometer (core pressures well, outer-lap radius only in trend) [S44 AB, S45 EX,
  S46 EX, S47 EX]. Findings: the radius deviation is **smaller** than the thickness deviation
  because the thick lane is compressed more; the pressure rise is much larger than the thickness
  rise (`dp/p = exp(K2*a) - 1` in one theory) [S45 EX, S53 EX]. Axisymmetric FE winding models add
  axial and shear stress [S46 EX]. Film practice against hard streaks: oscillation, thickened
  edges, lower tension, lay-on roll [S44 patent EX, S53 EX].
- **Metal strip with a ridge.** Wrap-by-wrap 3D stress with a non-linear interwrap layer and an
  uneven profile gives a permissible hot-coil ridge of 6-7 um for 0.35 mm tinplate (25 t coil,
  880 mm) and compares measured and calculated ridge-buckle height [S61 EX]. An FE coiling model
  shows the local strain at a 2-3 um high point **no longer rising in proportion to the number of
  wraps** after the first few [S60 EX]. Coiling models with roughness, crown and elastic-plastic
  strip quantify the extra flatness defect made by coiling [S62 AB/EX]. A profile makes the
  winding tension non-uniform across the width, the edge zone can drop to zero stress after about
  ten wraps, and plastic yielding "is most significant for softer materials such as aluminium
  foil" [S76 SN].
- **Air in the coil and the ironing roll.** Entrained air separates wraps, lowers interlayer
  traction and promotes telescoping and collapse; lay-on (ironing) rolls are "the most effective
  method known" to reduce it; with a nip, roughness carries part of the load and the film follows
  elastohydrodynamic line-contact theory; winding models with air use an equivalent radial modulus
  from Boyle's law [S50 AB/EX, S49 EX, S51 EX]. In-situ air-film measurements during winding exist
  [S50 AB].
- **Machine-direction corrugations ("tin-canning", rope marks).** Uniform-pitch MD buckles on the
  roll, common in thin film and reported for thin foil; spacing set by gauge (thinner = closer),
  not aligned one-to-one with thickness features; promoted by entrained air (low nip load, high
  speed, smooth surface, large diameter), by gauge bands on either side and by soft nip covers;
  they re-form at the same lateral positions on rewinding [S53 EX]. EAFA lists foil "grooves" with
  a rope-like pattern ("Seilfalten") below 10 um, "commonly visible on reel only", with causes
  "unfavourable flatness profiles, deviating roll line, material movement during the annealing
  process, unfavourable slitter setting" [S66 EX].
- **Foil coils, spool, anneal, slitting.** A 6.3 um x 1616 mm coil on a 300 mm core to 700 mm
  holds over 32,000 laps; core stiffness changes the inner pressure and the compressive hoop
  stress that buckles inner laps [S65 VP]. The interlap gap in a 6 um coil is below 1 um and
  controls oil removal in the final anneal; oil leaves only through the coil ends, giving a
  cross-width wettability gradient; sticking rises with anneal temperature [S65 VP, S74 EX]. EAFA
  attributes friction marks to laps moving during annealing [S66 EX]. Slitting: belled edges from
  burr or "dog bone" profiles building up on rewinding [S67 EX].

---

## 3. Gap table

Band relevance codes: **L** = lengthwise bands at fixed width positions, **S** = short-lived
bands, **T** = transverse marks. Effort: S = days, M = weeks, L = months (standard-library Python,
screening fidelity).

| # | Gap | Why it matters at thin gauge (band relevance) | Couples to (variables) | Model to add | Plant inputs | Effort | Sources |
|---|---|---|---|---|---|---|---|
| G1 | **No roll stack** (deflection, WR-BUR contact, flattening distribution, bending, tilt, shifting / CVC, ground camber) | The gap crown is an input, so the low-order flatness on which a local band sits (edge tension, quarter buckles), the bending needed to hold it, and the barrel-position dependence of local transfer are all missing. Bending cannot remove a narrow band [S3], but it sets where the strip is tight or loose. (L: indirect; S: bending steps; T: none) | `strip_shape.crown_heredity` (`gap_crown_m` becomes an output); `transfer_radius_profile` (local `Q`, local force per width instead of a uniform one); `contact.py` / `slab.py` / `foil_bite.py` (force per width, `Q`); `roll_thermal` (thermal camber as roll profile) | Influence-function slit-beam model: Timoshenko beam deflection of WR and BUR, Foppl / Hertz WR-BUR approach, Boussinesq strip-side flattening, iterated contact with loss of contact; or SM-FEM (beam elements + Winkler foundations, `kf_eq = (1/kf1 + 1/kf2)^-1`). 4-high first, 6-high later. Outputs: gap profile, actuator influence functions | Roll diameters, barrel and bearing-centre lengths, neck diameters, ground cambers and tapers, BUR chamfer, bending force range and current value, tilt, shift position | L (M for a symmetric 4-high) | S1, S2, S3, S5, S7, S8 |
| G2 | **No closed-gap (roll-kiss) shape path** for foil | Below roughly 50-200 um the work rolls touch outside the strip; part of the load bypasses the strip (22 % in one computed case), the bender acts on the barrel ends and hardly on the strip, and the exit gauge is set by speed and tension, not by the gap. The project's `Q`, `N_x'` and hence every foil flatness number come from an open-gap mattress bite it calls experimental. (L, S) | `foil_bite.py` (pressure, flat zone, sensitivities); `strip_shape` (`Q`, `N_x'`, `a` via `shape_inputs`); G1 | Extend G1 with a third contact (WR-WR outside the strip) and a Fleck-Johnson type foil bite per width element; solve kiss length and kiss force; derive the local transfer of a roll bump with the kiss contact carrying the mean load | As G1 plus roll roughness, strip width relative to barrel, measured total force and bending, speed-tension-gauge operating curves | L | S8, S24, S25, S26, S28 |
| G3 | **Width-coupled strip model missing** (constant `xi`, uniform entry tension, pointwise exit-tension feedback) | The feedback term dominates every thin-gauge result (76-386 x `Q` in the demos), yet it is pointwise and uses the far-field stress. The literature couples lateral displacement, exit velocity and tension across the width, shows flow only near the edges at thin gauge, and shows the stress profile still evolving after the bite. A narrow band has shear lag: its tension deficit is shared with its neighbours over a length of the order of its width. (L, S) | `transfer_radius_profile` (replace the per-wavenumber `Q_eff` by a wavenumber-dependent in-plane kernel), `differential_elongation` (`xi(z)`), `flatness_from_elongation` | Strip-element or variational lateral-flow model (Lian; Liu) with exit and entry tension distributions as unknowns, plus a plane-stress Airy solution for the span that maps the bite-exit velocity profile to the far-field stress (gives the wavenumber filter and the distance to stabilise) | Entry profile and entry flatness (previous pass), span lengths bite-to-shapemeter and bite-to-coil | M (kernel) to L (full) | S4, S21, S22, S23 |
| G4 | **Buckling: one assumed mode, no wavelength search under tension, no post-buckling, no stress saturation** | Under tension the critical stress rises and the waves shorten and localise; after release the amplitude decides whether a band is seen; dead load on a table hides weak bands. The project's after-release result says "manifest" for almost any reportable band at foil gauge and gives no amplitude. Stress saturation in a buckled band changes what the shapemeter reads. (L, S) | Replaces `_SineModeSearch`; feeds `band_width` states, onsets, `wrinkle_rule`; new outputs wavelength and amplitude for comparison with `observations` | 1D-in-width Ritz or Hermite FE, harmonic along the length, `sigma_res(z)` + tension, minimise over wavelength (Rammerstorfer; Kpogan); Koiter one-term post-buckling for amplitude; optional elastic foundation term for the table (dead load); Counhaye rule (clip stress at `-sigma_cr`) to produce the saturated profile | Band wavelength and height on a sample, sample support (table, hanging, on coil), tension at which it appears | M | S12-S20 |
| G5 | **No shapemeter and no flatness-control model** | The plant sees bands through 26 / 52 mm zones (or 25-100 mm rotors) with cross-talk and edge-coverage rules; a band of a few centimetres is at or below one zone and is diluted. The control loop reacts to a hot stripe with more cooling in that zone, and its valve switching is itself the "event" of the short-lived-band model. Without the loop the tool cannot say what the operator's screen should have shown, nor whether the control made or removed a band. (L, S) | `band_width` (model bands -> predicted zone readings; events generated by the controller instead of supplied); `roll_thermal.SprayHeader` (levels become control outputs); observation fields | Measurement operator: zone averaging, stated neighbour spreading, edge-zone rule, temperature compensation on / off. Controller: least squares on actuator influence vectors (bending, tilt from G1; one column per spray zone from `roll_thermal`), dead bands, valve minimum on / off times, target curve (e.g. loose edges) | Shapemeter type, zone map, target curve, actuator list and limits, spray valve logic, logged zone readings and valve states | M | S29-S34, S39 |
| G6 | **Strip temperature across the width is not a flatness term** | A fibre 1 K hotter than its neighbours is longer by about 2.4 I-units for aluminium [D from alpha, M]; this is above the project's 2 I-unit reporting threshold. A hot roll stripe or a lubrication band also heats the strip locally; the shapemeter reads it loose, and it tightens when the coil cools. EAFA defines heat stripes by "temperature and/or flatness differences". (L, S) | `energy_handoff.py` / `band_thermal.py` (strip exit temperature per width position), `flatness_from_elongation` (add `alpha*dT(z)` to `eps` at the measuring point, remove it after cooling) | Per-width strip heat balance driven by the local reduction, friction and roll surface temperature; apparent flatness at the shapemeter and true flatness after equalisation | Strip temperature scan at exit (pyrometer or thermal camera), coolant carry-over pattern | S-M | S10, S32, S40, S41, S66 |
| G7 | **Thermal camber at the strip edge and edge actuators** | Tight edges and strip breaks are the foil mill's main flatness risk; the cause is the thermal fall-off beyond the strip edge. The roll model has adiabatic ends and only a spray header: no hot-edge spray or inductor, no neck / chock loss, no coupling to edge tension. (L at the edges; S on width change) | `roll_thermal` (extra surface heat flux or hot-oil zones outside the strip; end loss boundary); G1 (edge gap); G4 (edge tension -> break index) | Add heat-source segments and a convective end condition; report edge fall-off slope and the edge tension change through the transfer chain; break-risk indicator = edge tension against a notch-sensitive limit | Hot-edge system type, position relative to strip edge, power or oil temperature, edge trim practice, break statistics | S-M | S31, S32, S36, S73 |
| G8 | **Circumferential (per-revolution) and skin time scales of the roll** | The open discrepancy (about 20 s plant response against minutes in the model) matches the literature's separation into short, medium and long thermal effects; local shape control uses the medium one. A two-regime (skin + bulk) model is what current on-line models use. (S mainly) | `roll_thermal` (optional skin layer with its own storage and the bite / spray sequence around the circumference) | Two-layer or angular-resolved surface model superposed on the existing bulk solution; identify the three time constants and report which one a given event excites | Roll speed, positions of headers around the roll, zone-step tests on the mill | M | S35, S71 |
| G9 | **Coil model is a linear stack with a constant compaction factor** | At foil gauge the project's own result is that bands show after tension release and in the coil; its critical ridge heights are 0.06-0.15 um, i.e. the answer hangs on `c = 0.5`. Winding models show the ridge radius growing less than the thickness, the pressure and the tension concentrating in the hard lane, the neighbours going slack (soft bands, zero stress after about ten wraps), and yielding there. Needed too: winding-tension taper, spool stiffness, V-buckle and telescoping margins. (L; S when a transient ridge is wound in) | Replaces the criterion in `coil_ridge_buildup`; takes the exit thickness profile from `thermal_stripe_flatness` / incoming-ridge transfer; returns per-lane in-coil tension, plastic strain -> a new elongation term for `flatness_from_elongation` after unwinding | Hakiel 1D model per width segment with `E_r(P)` from stack compression, relaxation-radius tension allocation (Cole & Hakiel), core boundary condition, elastic-plastic hoop strain per lane; later an axisymmetric version for axial stress | Coil build-up (inner / outer diameter), tension and ironing-roll pressure curves versus diameter, spool dimensions and material, stack compressibility of the oily foil (a simple press test), strip yield stress, oscillation if any | M (1D + segments) to L | S42-S49, S60-S65, S76 |
| G10 | **Air entrainment and the ironing roll** | Illustration [D]: the foil-bearing formula with R = 0.125 m, 10 m/s and 720 N/m (40 MPa x 18 um) gives an air film of about 17 um on a deflector roll, about 40 um on a 0.3 m coil radius without a nip, against a foil roughness of tenths of a micrometre: at mill speed the foil floats unless roughness, grooves or a nip vent the air. This governs traction on rolls (tracking, wrinkle regime), coil density, telescoping and whether a ridge "prints". The project has an ironing-roll observation and no physics. (L; T possibly through slip) | New span / roller traction block used by `tension_trough_screen` (Regime II limit); G9 (equivalent `E_r` with air, wound-in tension `T_w + mu*N/h` with a nip) | Knox-Sweeney film with side-leakage and roughness (Ducotey & Good), effective friction versus `h/sigma`; nip film by line-contact EHL; Boyle-law air layer in the winding model | Line speed, roller radii and surface (roughness, grooves), wrap angles, ironing-roll diameter, cover and load, air blow-off arrangement | M | S49, S50, S51, S57, S58 |
| G11 | **Lateral stress in spans is an input; no generator and no foil-specific correction** | The thresholds are computed but the acting lateral stress is not, so the trough / wrinkle hypothesis is "thresholds only" unless the plant supplies a stress it cannot measure. For wide foil the isolated-span theory over-predicts sensitivity by an order of magnitude. Residual-stress bands (baggy lanes) are themselves a source of troughs, which links G4 to this block. (L) | `tension_trough_screen` (`lateral_compressive_stress_pa` computed), `band_width` troughs section | Closed forms for misalignment and taper (Good & Beisel), roller deflection (Shelton), moment-transfer and slack-edge limits (Shelton; Fu & Good; Walker et al.), plus buckling of a span with a slack lane | Roller alignment survey (mm/m), roller diameters, taper / crown, span lengths, wrap angles | M | S54-S57, S59 |
| G12 | **No physical model of foil tension lines** | The published remedies in the project's own catalogue (more tension, rougher rolls, ironing-roll pressure, less blow-off air) are the remedies for entrained-air MD corrugation in winding. The classical axisymmetric shell-buckling full wavelength `3.47*sqrt(R*t)` [M] gives 5 mm on a 0.125 m roller and 5-13 mm on coil radii 0.15-0.5 m for 12-30 um foil [D], inside the reported 5-20 mm pitch, and scales with sqrt(gauge) as observed for tin-canning. This is a candidate, not an established explanation. (L) | `foil_tension_lines` hypothesis (adds a model pitch and an onset condition); G9 / G10 (axial stress in the outer laps, air film) | Axial (width-direction) compression of the outer lap from Poisson recovery between hard lanes and from radial compaction, compared with the shell buckling stress on a compliant, air-cushioned foundation; pitch from the shell wavelength | Pitch of the lines against coil radius and gauge, whether they are on the coil only, ironing-roll and blow-off settings | S-M | S53, S66, S46 |
| G13 | **Roll ground-profile error and wear as band sources share no quantitative path** | Grinding residuals and local wear are high-fidelity diameter deviations that transfer like thermal stripes and that bending cannot remove; the project scores them by rules only. (L) | `roll_surface_band`, `grinding_feed_marks` hypotheses; reuse `transfer_radius_profile` with a measured profile | Feed a measured roll profile (grinder report) through the existing transfer; add the Patel stiffness-ratio check and the barrel-position modulation from G1 | Grinder profile reports before and after a campaign | S | S3, S72 |
| G14 | **Downstream steps absent** (slitting, separating, annealing) | A band can first appear when the wide coil is slit: narrow slit strips release cross-width stress as camber or local waves, burr and belled edges build new ridges, and rewinding re-forms corrugations at the same positions. For annealed products, lap movement, sticking and oil-removal gradients add stripes; battery foil is normally delivered hard, so only an intermediate anneal of the stock applies. (L) | New post-mill stage after `coil_ridge_buildup`; observation fields "seen first at slitter / after anneal" | Rule set first; later re-use G4 on each slit width and G9 for the rewound reel; thermal expansion mismatch and creep set-in of ridge strain for the anneal | Slit pattern, knife set-up, rewind tension, anneal cycle | S (rules) to M | S53, S65, S66, S67, S74 |
| G15 | **Edge drop** | Not a band cause, but it sets the edge ridge or valley in the coil and the edge tension. (L at the edges) | G1 (flattening recovery at the strip edge), G9 | Falls out of G1 with strip-side Boussinesq flattening | Edge profile scans | with G1 | S5, S25, S40 |
| G16 | **No validation benchmark and no uncertainty statement for this chain** | The review literature itself names "standardised validation benchmarks" as an open gap; several published cases could be coded as regression tests now. | `tests/`, `docs/band-diagnosis.md` 13-14 | Encode the cases of section 5 | none | S-M | S4 |

Notes on individual couplings:

- G1/G3 against the project's local transfer. The project's compliance-only level is the same
  idea as Patel et al.'s stiffness ratio, with a better (wavelength-dependent) roll compliance.
  Cross-check [D]: the foil demo's F1 values (`Q` = 7.39e10 Pa, compliance-only / rigid =
  3128 / 9862 = 0.32) imply `1/(2C)` of about 3.4e10 Pa, the same order as the 5.8-7.0e10 Pa roll
  flattening modulus in [S3]. What the literature does **not** contain is the project's
  exit-tension feedback as a multiplier of 76-386 on `Q`; coupled 3D models contain the effect
  implicitly, but no paper found isolates it for a narrow band. It is the least supported and most
  influential element of the chain.
- G5 dilution [D]: a 20 mm band of 25 I-units centred in a 52 mm zone reads about 10 I-units as a
  zone mean before any neighbour spreading; a 2 I-unit band reads below 1 I-unit, at the stated
  accuracy of the roll.
- G10 numbers are an upper-bound illustration: the formula assumes a smooth, wide, impermeable web
  in air with no side leakage; oil mist, roughness and edges reduce the film.

---

## 4. Ranked lists

### 4.1 By importance for the plant's band problem (battery foil, 50 um -> 12-19 um, two single-sheet passes)

1. **G9 coil model with G10 air and ironing roll.** The tool's own foil result is "hidden in the
   mill, visible after release / on the coil"; the coil criterion is its weakest formula.
2. **G5 shapemeter and control loop.** Decides what the plant can have seen, and turns the
   short-lived-band model from supplied valve events into predicted ones.
3. **G2 closed-gap transfer (with the kernel part of G3).** Every foil flatness number rests on
   `Q` and `N_x'` from an open-gap bite; the feedback term needs an independent check.
4. **G6 strip temperature as flatness.** Cheap; matches the published definition of heat stripes;
   1 K is already a reportable band.
5. **G12 tension-line model.** Cheap, testable with a ruler: pitch against sqrt(R*t).
6. **G11 lateral stress generators.** Removes the "thresholds only" status of the trough / crease
   hypothesis and corrects it for wide foil.
7. **G4 buckling upgrade.** Gives wavelength and amplitude to compare with what is seen.
8. **G7 / G8 roll thermal edge and time scales.** Edges and the 20 s question.
9. **G13 ground-profile and wear input.** Small step for two existing hypotheses.
10. **G14 slitting and separating rules.**
11. **G1 roll stack.** For a narrow interior band it is second order (bending is a low-pass
    actuator), but G2 needs its machinery.
12. **G15, G16.**

### 4.2 By importance for general simulation coverage of thin-gauge aluminium rolling

1. **G1 roll stack** (the reference component of every flatness model).
2. **G3 width-coupled strip model.**
3. **G4 buckling and post-buckling.**
4. **G5 measurement and automatic flatness control.**
5. **G2 closed-gap foil shape.**
6. **G7 / G8 thermal camber, edges, time scales.**
7. **G9 winding** and 8. **G10 air entrainment.**
9. **G11 web handling.**
10. **G6 thermal flatness.**
11. **G14 downstream**, 12. **G16 benchmarks**, 13. **G13**, 14. **G12**, 15. **G15**.

### 4.3 Where the literature contradicts or qualifies the project's documentation

| # | Statement in the project | What the literature says | Verdict |
|---|---|---|---|
| C1 | Coil ridge build-up is linear in the wrap count with a constant compaction factor 0.5 (`docs/band-diagnosis.md` 7.2; `strip_shape.coil_ridge_buildup`) | The local strain at a high point stops rising in proportion to the wraps after the first few [S60 EX, a source the project already cites for the mechanism]; the radius deviation is smaller than the thickness deviation because the thick lane compresses more, while pressure and tension concentrate there [S45 EX, S53 EX]; the compaction is an outcome of the radial modulus, tension and air, not a constant | **Contradicted** in form. The threshold itself could not be compared: the published 6-7 um limit is a ridge on the HOT coil for 0.35 mm tinplate [S61 EX] and the extract does not give the hot-band gauge; the project's critical ridge is about 0.5-1 % of the wound gauge |
| C2 | "A latent band is a stress stripe a shapemeter can see" (7.2) | Zones are 26 / 52 mm (rolls) or 25-100 mm (rotors), body zones typically about 50 mm, with neighbour spreading; a tight edge and a loose pocket in one zone are missed [S29-S32] | **Qualified**: true only for bands at least one zone wide; a band of 2-3 cm is diluted to a fraction of its peak |
| C3 | When a band goes slack the feedback is capped and the thickness transfer rises (7.2 "saturation"; it raises the sheet demo's final pass from 50.7 to 148.3 I-units) | In coupled rolling-buckling FEM, buckling transforms the far-field stress profile but the in-bite fields, roll stack deformation and roll force profile are hardly changed; the influence grows only at very small reduction [S8 EX, S9 AB, S10 AB] | **In tension with** the literature; the saturation step is not supported and may overstate manifest bands |
| C4 | Buckle half-wave equals the buckle width, `k = 4`, simply supported band edges (7.2) | Tension shortens and localises the waves [S12 AB, S13 AB]; measured local buckles have a full wavelength of about 0.7-0.8 of the buckle width (75 mm on 105 mm, aluminium; 120 mm on 150 mm, steel), i.e. 2.5-2.8 times shorter than the assumed mode [D from S19 FT]; the edge restraint lies between simply supported and clamped, which moved the critical value from 5.3 to 8.9 I-units in the published case [S19 FT] | **Contradicted** for the wavelength; the critical stress is uncertain by a factor of about 1.7 from the edge condition alone |
| C5 | Trough and roller-wrinkle thresholds from the isolated-span formulas are applied at foil gauge (3.5, 7.2) | The same two formulas are the "Regime I / II" expressions; for wide aluminium foil below 25 um wrinkles needed about 15 times the predicted misalignment [S55 EX] | **Qualified**: the thresholds are conservative screening values for wide foil; say so in the result |
| C6 | "Any reported band buckles after release" at foil gauge (3.5, 14) | With dead load on a table a strip lies flat below a residual-stress limit and the table index differs widely from the stress index [S14 AB] | **Qualified**: the local released mode needs a dead-load term, as the doc already admits for the whole-sheet mode |
| C7 | Crown heredity and the dead band are evaluated for foil passes with a supplied gap crown | In kiss rolling the bender changes the barrel ends, not the strip portion, and part of the load bypasses the strip [S26 EX] | **Qualified**: a gap crown is not a sufficient description of a closed gap |
| C8 | The plant's roughly 20 s flatness response against minutes in the model is "partly open" (7.1, 14) | Three thermal effects with different time constants; the medium one serves local shape control [S35 AB]; on-line models separate skin and bulk [S71 AB] | **Supported**: the doc's reading is the literature's |
| C9 | A given roll stripe is hidden more, not less, at thinner gauge in the mill (3.5) | Transfer falls as the strip becomes stiff relative to the roll (thin, hard strip) [S3 FT]; very thin foil is run with deliberately loose edges [S31 EX] | **Consistent in direction**, by a different mechanism (strip stiffness, not tension feedback) |
| C10 | Tension lines "have no physical model" (3.7, 14) | Entrained-air MD corrugation in winding has the same remedies, the same thin-gauge trend and a pitch of the right size [S53 EX, S66 EX; pitch D/M] | **Candidate model exists** (G12) |

---

## 5. Validation data found

| # | Data | Material, geometry | What is measured | Usable for | Source, read status |
|---|---|---|---|---|---|
| V1 | Wrinkling of a tensioned strip with heated edge bands, during unloading | Steel 0.332 x 210 x 800 mm (free length 731 mm), E = 205.7 GPa; heated edge zones 25 x 400 mm; mean tension 50 MPa; local temperature rise up to 60 C, 34 C at unloading | Full-field out-of-plane shape (resolution about 0.01 mm) and temperature; mode changes while tension is released; bifurcation force | G4: buckling of a narrow band under tension and after release (thermal strain stands in for residual strain); the project's `_SineModeSearch` | S18 [FT of the 2017 post-print; the 2015 paper SN] |
| V2 | Local interior buckle, industrial | Steel 0.5 x 1000 mm, buckle half-width 75 mm, half wavelength 60 mm | Shapemeter 7.5-8 I-units at the wave; no waves where below 6 I-units; computed critical 5.3 (simply supported), 6.38 (elastic restraint), 8.92 I-units (clamped) | G4: critical elongation difference and wavelength of a local band; direct test of `k = 4` and of the half-wave = width assumption | S19 [FT, formulas garbled] |
| V3 | Local buckle, laboratory rolling | Aluminium sheet 270 mm wide, 0.4 -> 0.3 mm (25 %), ground roll profile designed to give a local wave | Buckle width 105 mm, wavelength about 75 mm | G4, and the roll-profile -> local wave chain end to end (aluminium) | S19 [FT] |
| V4 | Stress-meter profile against models with and without buckling | Tinplate, last stand of a tandem mill (the "Counhaye case") | Far-field longitudinal stress across the width | G3, G4 (saturation), G5 | S8 [EX], S9 [AB] |
| V5 | Roll-profile transfer study | 4-high, work roll 76.2 mm, 301 SS / 6061-O Al / Cu, 2.576 mm and 0.236 mm entry; measured new / warm / worn roll diameter profiles | Simulated thickness and reduction deviations; stiffness table | G13, cross-check of the local transfer (model-to-model, not a measurement) | S3 [FT] |
| V6 | Transverse displacement in ultra-thin rolling | Strip 65 mm wide, 0.05 -> 0.037 mm and 0.04 -> 0.033 mm, tensions 118 and 90 MPa | Lateral displacement from a lithographic grid (10 um lines) | G3 (`xi`, edge flow) | S21 [EX] |
| V7 | Stress evolution after the bite | Cold-rolled strip (experiment described) | Tension profile at distance from the bite | G3, G5 (shapemeter distance) | S22 [EX] |
| V8 | Foil flatness control performance | Aluminium foil 0.013 mm (2 x 0.0065 mm) | Target wavy edge 30 I-units; control within 6 I-units at steady speed | G5 (order of magnitude; the project already cites it) | S31 [EX] |
| V9 | Computed aluminium foil kiss-rolling case | 30 um x 1100 mm, 300 tf, 50 %, work roll 270 mm, backup 635 mm | Thickness distribution against VC pressure and bending; kiss force share 22 % | G2 (model-to-model benchmark) | S26 [EX] |
| V10 | Work-roll thermal camber | Aluminium hot rolling, 5754: +6 um in 100 s with entry cooling, +4 um with both sides, model "validated with industrial data"; cold reversing mills: thermal crown in the range "2 to 12" (unit cut off in the extract); foil mill maximum 30 um on a 260 x 900 mm roll (earlier project research, T25) | Camber against time | `roll_thermal`, G8 | S68 [EX], S69 [AB], process-temperatures.md |
| V11 | Sheet-gauge aluminium passes with force and slip | 5052, 1360 mm wide, 4.1 -> 2.90 -> 2.21 -> 1.72 mm, work-roll radius 210.81 mm, 4.0-4.7 m/s, tensions 7.3-9.5 MPa | Force 5144 / 5017 / 4302 kN; forward slip 0.0150 / 0.0182 / 0.0227 | Bite models (`slab.py`), heat input to `roll_thermal` | S70 [EX] |
| V12 | Wound roll with cross-width thickness variation | PET film 101.6 um x 254 mm, two measured thickness profiles | Core pressure on a core of 25.4 mm ring segments; outer-lap radius profile | G9 (pseudo-2D winding; no metal equivalent found) | S46 [EX], S47 [EX], S44 [AB] |
| V13 | Ridge in steel coils | 0.35 mm x 880 mm tinplate, 25 t coil: permissible hot-coil ridge 6-7 um; measured against calculated ridge-buckle height; FE coiling at 0.4-0.6 mm, 1300 mm coil, high points 1-4 um; measured strip profiles with a local high point 100-200 mm from the edge | Ridge-buckle height, strain per wrap, profiles | G9, `coil_ridge_buildup` | S61 [EX], S60 [EX] |
| V14 | Foil wrinkling against roller misalignment | Copper 10 um x 0.4 m; aluminium and copper below 25 um, wider than 0.6-1 m | Critical misalignment against tension; ratio to the isolated-span prediction | G11, `tension_trough_screen` | S55 [EX] |
| V15 | Troughs and wrinkles on polyester | 23.4 um x 152.4 mm, spans 0.508 / 0.762 / 1.016 m, roller radius 36.8 mm | Critical taper and misalignment for troughs and for wrinkles | G11 (already the project's formula source) | S54 [EX] |
| V16 | Air film in winding; slip and wrinkle maps | Films | In-situ entrained-air thickness; slip-onset speed; wrinkle onset | G10 | S50 [AB], S57 [EX] |
| V17 | Foil coil stresses (model output) | 6.3 um x 1616 mm, 300 mm steel core, 700 mm coil, more than 32,000 laps | Radial pressure, lap thickness, hoop stress for three core stiffnesses (figures only) | G9 (plausibility) | S65 [VP] |
| V18 | Roughness transfer in industrial foil rolling | AA1200, from 0.4 mm, two passes of about 50 % | Surface spectra: long wavelengths flatten faster than short ones | G13 (wavelength dependence of surface transfer) | S72 [EX] |
| V19 | Shapemeter specifications | - | Zone widths, accuracy, spreading | G5 | S29, S30 [VP] |

No published data set was found that gives, for aluminium foil, a roll thermal or ground profile
together with the resulting cross-width flatness or thickness of a narrow band.

---

## 6. Sources

| # | Reference | URL | Read |
|---|---|---|---|
| S1 | Malik (2007) PhD thesis, Wright State Univ., "Rolling mill optimization using an accurate and rapid new model for mill deflection and strip thickness profile" | https://corescholar.libraries.wright.edu/etd_all/137 | EX |
| S2 | Zhang & Malik (2018) J. Manuf. Sci. Eng. 140(1):011008, roll-stack model for CVC mills | https://asmedigitalcollection.asme.org/manufacturingscience/article/140/1/011008/383992/ | EX |
| S3 | Patel, Malik, Zhang & Mathews (2022) Int. J. Adv. Manuf. Technol. 120:7389-7413, doi:10.1007/s00170-022-09228-7 | https://par.nsf.gov/servlets/purl/10359685 | FT |
| S4 | Previati & Ballo (2026) Int. J. Adv. Manuf. Technol., "Strip flatness prediction in cold rolling: a review", doi:10.1007/s00170-026-19263-3 (open access) | https://link.springer.com/article/10.1007/s00170-026-19263-3 | EX (abstract, introduction, parts of sections 3-4) |
| S5 | Yun, Shin & Hwang (2007) ISIJ Int. 47:1300 | https://doi.org/10.2355/isijinternational.47.1300 | EX |
| S6 | Hacquin, Montmitonnet & Guillerault (1996) J. Mater. Process. Technol. 60:109; (1998) Eur. J. Mech. A/Solids 17:79 | https://doi.org/10.1016/0924-0136(96)02315-1 ; https://www.sciencedirect.com/science/article/abs/pii/S099775389880065X | SN |
| S7 | Montmitonnet, Fourment, Ripert, Ngo & Ehrlacher (2016) "State of the art in rolling process modelling", slides | https://sf2m.fr/wp-content/uploads/2018/12/Expos8Rolling2016-Montmitonnet.pdf | EX |
| S8 | Abdelkhalek, Montmitonnet, Legrand & Buessler (2011) Int. J. Mech. Sci. 53:661-675 | https://www.academia.edu/31485162/Coupled_approach_for_flatness_prediction_in_cold_rolling_of_thin_strip | EX |
| S9 | Abdelkhalek et al. (2010) Ironmaking & Steelmaking 37(4), doi:10.1179/030192310X12646889255708 | https://doi.org/10.1179/030192310x12646889255708 | AB |
| S10 | Abdelkhalek, Nakhoul, Zahrouni, Montmitonnet, Legrand & Potier-Ferry (2012) HAL hal-00724898; Abdelkhalek et al. (2011) HAL hal-00674953 | https://minesparis-psl.hal.science/hal-00724898v1/document ; https://minesparis-psl.hal.science/hal-00674953 | AB |
| S11 | Nakhoul et al., "Coupled rolling and buckling model for friction-sensitive setting of flatness actuators" | http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.739.6240 | EX |
| S12 | Rammerstorfer, Fischer & Friedl (2001) J. Appl. Mech. 68:399-404 | https://doi.org/10.1115/1.1357519 | AB |
| S13 | Fischer, Rammerstorfer & Friedl (2003) J. Appl. Mech., doi:10.1115/1.1532322 | https://doi.org/10.1115/1.1532322 | AB |
| S14 | Fischer, Friedl, Noe & Rammerstorfer (2005) steel research int. 76:327-335 | https://doi.org/10.1002/srin.200506016 | AB |
| S15 | Kpogan & Potier-Ferry (2014) Key Eng. Mater. 611-612:221 | https://doi.org/10.4028/www.scientific.net/kem.611-612.221 | EX |
| S16 | Abdelkhalek, Zahrouni, Legrand & Potier-Ferry (2015) Int. J. Mech. Sci. 104:126-137 | https://www.sciencedirect.com/science/article/abs/pii/S0020740315003586 | EX (highlights, introduction) |
| S17 | Bush, Nicholls & Tunstall (2001) Ironmaking & Steelmaking 28:481-484 | https://doi.org/10.1179/030192301678361 | AB |
| S18 | Tran, Tardif, El Khaloui & Limam (2017) Thin-Walled Struct. 113:129-135 (HAL post-print); Tran, Tardif & Limam (2015) Int. J. Solids Struct. 69-70:343 | https://hal.science/hal-01802236v1/file/2017_TRAN_Thin_walled_Structures_PostPrint.pdf ; https://doi.org/10.1016/j.ijsolstr.2015.05.017 | FT ; SN |
| S19 | Dai, Zhang & Qin (2011) Engineering Mechanics 28(10):236-241 (Chinese); Zhang et al. (2013) same journal | https://pubs.cstam.org.cn/data/article/em/preview/pdf/em_2898.pdf ; http://en.cnki.com.cn/Article_en/CJFDTOTAL-GCLX201311046.htm | FT (formulas garbled) ; AB |
| S20 | Kiakidis et al. (2023) La Metallurgia Italiana, "A fully integrated roll deflection and strip buckling model" | https://aimnet.it/la_metallurgia_italiana/2023/maggio/Kiakidis.pdf | EX |
| S21 | Ren, Xiao, Liu & Yan (2018) ISIJ Int. 58(2) | https://www.jstage.jst.go.jp/article/isijinternational/58/2/58_ISIJINT-2017-519/_html/-char/en | EX |
| S22 | Zhang, Wang, Xu & Liu (2023) Appl. Sci. 13:6781 | https://www.mdpi.com/2076-3417/13/11/6781 | EX |
| S23 | Dixon & Yuen (2004) ANZIAM J. 45 | https://doi.org/10.21914/anziamj.v45i0.899 | EX |
| S24 | "Development of three-dimensional strip profile model for thin-foil cold rolling" (2014) Adv. Mech. Eng., doi:10.1155/2014/312382 (authors not captured) | https://journals.sagepub.com/doi/10.1155/2014/312382 | EX |
| S25 | Jiang, Zhu & Tieu (2003) J. Mater. Process. Technol. 140; Jiang et al. (2004) JMPT 155-156:1280; (2005); Jiang, Wei & Tieu (2008) Int. J. Mod. Phys. B; CCP 84 paper 198; Guan, He & Sun (2015) J. Northeastern Univ. | https://doi.org/10.1016/s0924-0136(03)00783-0 ; https://doi.org/10.1016/j.jmatprotec.2004.04.293 ; https://www.ctresources.info/ccp/paper.html?id=4273 ; https://xuebao.neu.edu.cn/natural/EN/10.12068/j.issn.1005-3026.2015.07.007 | AB |
| S26 | Masui, Yamada, Nagai & Nishino (1983) Trans. ISIJ 23:846 | https://doi.org/10.2355/isijinternational1966.23.846 | EX |
| S27 | Lawlor, Pack, Hua & Faure (2013) 50th ABM Rolling Seminar, DSR on aluminium cold mills | https://abmproceedings.com.br/en/article/recent-operational-experience-with-the-dynamic-shape-roll-on-aluminium-cold-mills | AB |
| S28 | Achenbach DVC roll; Nippon Steel VCROLL | https://www.achenbach.de/en/machines-equipment/technology-components/dvc-rolls-system/ ; https://www.nipponsteel.com/en/product/railway-automotive-machinery-parts/list/16.html | VP |
| S29 | ABB Stressometer measuring roll data; ABB "50 years of flatness control" | https://www.abb.com/global/en/areas/automation/measurement-analytics/force-measurement/flatness-measurement/measuring-roll ; https://library.e.abb.com/public/d83ad7d9b0b8438193e9fe7e67a2a03a/ | VP |
| S30 | Vollmer VPMR data sheet; IMS shapemeter roll; Primetals air-bearing shapemeter | https://www.vollmergmbh.de/fileadmin/user_upload/downloads/vollmer-datenblaetter_dina4_eng_vpmr.pdf ; https://www.ims-experts.com/en/measuring-system/shapemeter-roll-aluminium-cold-rolling-mills/ ; https://www.primetals.com/en/portfolio/solutions/cold-rolling/non-ferrous/aluminum/air-bearing-shapemeter/ | VP |
| S31 | Tsuzuki, Kira & Misumi, IHI Engineering Review, "Flatness control system of cold rolling process with pneumatic bearing type shape roll" | https://www.ihi.co.jp/en/technology/techinfo/contents_no/__icsFiles/afieldfile/2023/06/18/e66183a7b7832fe902c826e949d1ff1b.pdf | EX (vendor technical paper) |
| S32 | Silvey, US 2010/0236310 A1, "Edge flatness monitoring" | https://www.patents-review.com/a/20100236310-edge-flatness-monitoring.html | EX |
| S33 | Lloyd (Lechler, 2010), roll cooling and flatness | https://www.lechler.com/fileadmin/media/fachberichte/metallurgy/lechler_fachbericht_walzenkuehlung_09-2010_fundamentals-of-roll-cooling-and-control-of-flatness-at-primary-cold-reduction_dlloyd_en.pdf | EX |
| S34 | Bemporad, Bernardini, Cuzzola & Spinelli (2010) J. Process Control, optimisation-based flatness control | https://cse.lab.imtlucca.it/~bemporad/publications/papers/jpc-flatness.pdf | EX |
| S35 | Davies (1975) Metals Technology 2(1), "Prediction and control of strip flatness in cold rolling" | https://www.tandfonline.com/doi/abs/10.1179/030716975803277735 | AB |
| S36 | Primetals hot edge induction heating; Hulamin news item | https://www.primetals.com/en/portfolio/solutions/cold-rolling/non-ferrous/aluminum/hot-edge-induction-heating/ | VP |
| S37 | Molleda, Usamentiaga & Garcia (2013) Sensors 13, on-line flatness measurement | https://pmc.ncbi.nlm.nih.gov/articles/PMC3812602/ | EX |
| S38 | Spreitzhofer et al. (2005) Rev. Metall., SI-FLAT | https://www.metallurgical-research.org/articles/metal/abs/2005/08/P589/P589.html | AB |
| S39 | Magne et al., fibre-Bragg flatness roll prototype (CEA, HAL) | https://cea.hal.science/cea-04155953/file/article_Magne_flatness_roll_FBG_JAP_v3.pdf | EX |
| S40 | Hesling, steelonthenet technical modules (temper rolling and tension levelling; coil winding) | https://www.steelonthenet.com/resources/technical/temper-rolling-tension-levelling.html ; https://www.steelonthenet.com/resources/technical/coil-winding-galvanising-lines.html | VP |
| S41 | Usamentiaga et al. (2006) IEEE IAS, temperature compensation in flatness control | https://doi.org/10.1109/ias.2006.256569 | AB |
| S42 | Good (2005) "Winding and unwinding webs: a review", Fundamental Research Symposium | https://doi.org/10.15376/frc.2005.1.307 | EX |
| S43 | Hakiel (1987) Tappi J. 70(5):113-117 | https://eurekamag.com/research/005/993/005993354.php | AB |
| S44 | Hakiel (1991) "On the effect of width direction thickness variations in wound rolls", IWEB; US 5,308,010 | https://hdl.handle.net/20.500.14446/321658 | AB ; EX |
| S45 | Olsen (2005) IWEB, widthwise variations in web properties and wound roll structure | https://hdl.handle.net/11244/321890 | EX |
| S46 | Mollamahmutoglu & Good (2009) IWEB, axisymmetric wound roll models; (2015) CIRP J. Manuf. Sci. Technol., doi:10.1016/j.cirpj.2014.10.004 | https://hdl.handle.net/20.500.14446/321947 | EX ; SN |
| S47 | Gale (2012) MS thesis, Oklahoma State Univ., winding experiments on non-uniform thickness webs | http://hdl.handle.net/11244/9931 | EX |
| S48 | Kiribe, Aoki & Hashimoto (2015) Trans. JSME 81(821) | https://www.jstage.jst.go.jp/article/transjsme/81/821/81_14-00143/_article/-char/en | AB |
| S49 | Hashimoto, Jeenkour & Mongkolwongrojn (2010) J. Adv. Mech. Des. Syst. Manuf. 4:214 | https://doi.org/10.1299/jamdsm.4.214 | EX |
| S50 | Keshavan & Wickert (1997) J. Appl. Mech.; Forrest (1995) IWEB; Holmberg (1992) thesis; Taylor & Good (1997) IWEB; Lei, Cole & Weinstein (2003) | https://doi.org/10.1115/1.2788999 ; https://hdl.handle.net/20.500.14446/321710 ; http://hdl.handle.net/11244/13479 ; https://hdl.handle.net/20.500.14446/321744 | AB ; AB ; EX ; AB ; SN |
| S51 | Becker (Alcoa), IWEB paper on coil collapse of coated aluminium sheet | https://openresearch.okstate.edu/server/api/core/bitstreams/c5d493ad-ad07-4f43-b034-adf7dfba2346/content | EX |
| S52 | Lin & Wickert (2006) J. Manuf. Sci. Eng., corrugation and buckling defects in wound rolls | https://doi.org/10.1115/1.2113068 | AB |
| S53 | Walker & Cole (2015) IWEB, tin-canning; Jones (2012) AIMCAL slides; Smith (2007) TAPPI PLACE; PFFC columns | https://hdl.handle.net/11244/322043 ; https://pdfs.semanticscholar.org/c815/3a14e99fd5bcd13d4242ae71890b8cc1dcfb.pdf ; https://www.tappi.org/content/events/07place/papers/smith.pdf | EX ; EX ; EX ; VP |
| S54 | Good, Beisel & Yurtcu (2009) FRC, doi:10.15376/frc.2009.1.517; same authors, IWEB 2009; Good & Beisel, Tappi J. | https://bioresources.cnr.ncsu.edu/wp-content/uploads/2019/05/2009.1.517.pdf ; https://hdl.handle.net/11244/321965 ; https://doi.org/10.32964/tj5.12.9 | EX ; EX ; SN |
| S55 | Walker, Cole, Zagar & Quass (2011) IWEB, "Wrinkling of foils" | https://hdl.handle.net/11244/321981 | EX |
| S56 | Fu & Good (2013) IWEB, moment transfer; Beisel (2006) thesis; Fernandez Arias (1998) thesis | https://hdl.handle.net/11244/322020 ; http://hdl.handle.net/11244/11919 | SN ; EX |
| S57 | Hashimoto (2010) J. Adv. Mech. Des. Syst. Manuf. 4:238 | https://doi.org/10.1299/jamdsm.4.238 | EX |
| S58 | Ducotey & Good (1999) J. Tribol.; Rice & Gans (2003) IWEB; Kothari (1996) thesis; Brown (2012) AIMCAL slides | https://doi.org/10.1115/1.2834112 ; https://hdl.handle.net/20.500.14446/321859 ; http://hdl.handle.net/11244/12549 | AB ; EX ; EX ; EX |
| S59 | Swanson (2017) IWEB, baggy webs; Welch (2006) thesis; Roisum (1998) "Reading a roll" | https://hdl.handle.net/11244/322063 ; http://hdl.handle.net/11244/10087 ; https://shareok.org/handle/11244/321739 | EX ; EX ; AB |
| S60 | Sun, Zhang, He & Shao (2016) La Metallurgia Italiana, ridge buckle at local high points | http://www.aimnet.it/allpdf/pdf_pubbli/gen16/XYZhang.pdf | EX |
| S61 | "Effect of hot coil profile containing ridges on ridge-buckle defects of cold rolled thin strip" (2009) Int. J. Mater. Form., doi:10.1007/s12289-009-0412-1 (author list not captured) | https://www.academia.edu/27820504/ | EX |
| S62 | Weisz-Patrault, Ehrlacher & Legrand (2015, 2016, 2017), Weisz-Patrault (2018), coiling models | https://doi.org/10.1016/j.ijsolstr.2016.05.012 ; https://doi.org/10.1051/meca/2016038 ; https://doi.org/10.1016/j.apm.2018.03.042 | AB ; EX ; AB |
| S63 | Dai, Liang, Qiu & Xiao (2024) ISIJ Int. 64(6), coiling FE with interlayer contact deformation | https://www.jstage.jst.go.jp/article/isijinternational/64/6/64_ISIJINT-2023-405/_html/-char/en | EX |
| S64 | Bel'skii & Shopin (2017) Steel in Translation, stress-strain state of coiled steel | https://doi.org/10.3103/s096709121711002x | AB |
| S65 | Innoval Technology blogs: foil separator winding model (2018); foil final anneal (2016) | https://www.innovaltec.com/foil-separator-blog/ ; https://www.innovaltec.com/aluminium-foil-quality-blog/ | VP |
| S66 | EAFA (2020) Surface characteristics of aluminium foil | https://www.alufoil.org/surface-characteristics | EX |
| S67 | Aluminum Association (2002) QCA-1, 4th ed. | https://www.aluminum.org/sites/default/files/2021-10/VisualQualityCharacteristicsSheet%26Plate.pdf | EX |
| S68 | "Thermal camber and temperature evolution on work roll during aluminum hot rolling" (2020) Metals 10(11):1434 (authors not captured) | https://www.mdpi.com/2075-4701/10/11/1434 | EX |
| S69 | Garcia-Gil & Colas (2000) Int. J. Mach. Tools Manuf. 40:1977 | https://www.sciencedirect.com/science/article/abs/pii/S0890695500000468 | AB |
| S70 | Shao, Sun, He & Li (2015) Int. J. Heat & Technology 33(1):91-98 | https://www.iieta.org/journals/ijht/paper/10.18280/ijht.330113 | EX |
| S71 | Souto, Abdelkhalek, Koont & Legrand, TEC3 work-roll thermal crown model, ABM proceedings | https://abmproceedings.com.br/en/article/download-pdf/tec3-work-roll-thermal-crown-modelfor-hot-and-cold-rolling-of-steel | AB |
| S72 | Le & Sutcliffe (2000) Wear 244:71-78 | https://www.sciencedirect.com/science/article/abs/pii/S0043164800004415 | EX |
| S73 | Wang, Zhang & Ai (2023) Int. J. Adv. Manuf. Technol., edge thermal spraying in aluminium cold rolling | https://doi.org/10.1007/s00170-023-11830-2 | SN |
| S74 | US 4,325,753 (Swiss Aluminium), degrease annealing; TAPPI 2007 European PLACE, adhesion of coatings to foil | https://www.freepatentsonline.com/4325753.html ; https://www.tappi.org/content/events/07europlace/papers/07europl33.pdf | EX |
| S75 | Ataka (2015) ISIJ Int. 55:89, rolling theory review | https://www.jstage.jst.go.jp/article/isijinternational/55/1/55_89/_html/-char/en | EX |
| S76 | "Coil Winding" (unattributed upload, steel-industry text) | https://www.scribd.com/document/281411813/Coil-Winding | SN |

Earlier project research cited: `process-temperatures.md`
(T21-T25: hot-edge sprays, Lechler papers, foil-mill thermal crown).

From memory, not verified in this session: the classical axisymmetric shell-buckling wavelength
used in G12; the thermal expansion coefficient of aluminium used in G6; the attribution of the
flatness dead band to a 1971 Shohet & Townsend paper distinct from their 1968 roll-bending paper.

---

## 7. Looked for and not found

- Original texts of Shohet & Townsend (1968, 1971), Tomita & Shao (1993), Altmann (1968), the full
  Hakiel (1987) paper, the Good & Roisum winding book, Roisum's wrinkling papers, the Counhaye and
  Nakhoul theses, Hacquin's thesis. They are represented only through later papers that restate
  them. Tomita & Shao was not found even as an abstract.
- Any paper that isolates the exit-tension feedback on the transfer of a **narrow** roll bump, or
  that measures such a transfer on aluminium foil.
- A roll-stack or shape model for closed-gap aluminium foil rolling validated against measured
  foil profile or flatness. The 2014 thin-foil model [S24] and the Jiang-Tieu work were read as
  abstracts; their materials were not confirmed.
- Measured cross-width flatness maps of aluminium foil below 50 um showing a band a few
  centimetres wide, with the roll thermal profile or valve states that caused it.
- Measured ridge build-up in aluminium foil coils (radius profile against thickness profile), and
  any measured stack compressibility (Pfeiffer constants or equivalent) for oily aluminium foil or
  strip.
- Measured entrained-air film in aluminium foil winding at mill speed, or measured ironing-roll
  effect; only film data and qualitative aluminium statements were found.
- A published physical model of battery-foil tension lines.
- Quantified effect of hot-edge sprays or inductors on edge flatness (only vendor claims), and the
  number of pads / zones of DSR rolls on foil mills.
- Numbers from Davies (1975) for the three thermal time constants (abstract only).
- Quantitative slitting or separating studies for foil (only association catalogue descriptions).
- Published spray-zone influence functions (thermal spread to neighbouring zones) for aluminium
  mills; the Lechler paper by Tucker (2006) could not be fetched here (earlier project research
  read it as an excerpt).
