# Roll grinding for aluminium foil and thin-strip cold mills: what the open literature gives

Literature research of 2026-11-20 for the roll-stack work (gaps G1, G2, G13, G15, C4, BT-G9, BT-G11).
Nothing here was checked on a mill.

**Read tags** (never upgraded): `FT` full text read (the part read is stated), `EX` excerpt, `AB` abstract
or search snippet only, `VP` vendor, trade or teaching page, `CIT` seen only as a citation.
`[computed]` is my own arithmetic (scripts in `../../dev/gap-implementation/prototypes/grinding-research/`), `[from memory]` is recalled and not
verified, "as printed" is transcribed although it looks wrong.

**How the sources were reached.** The direct fetch tool could not resolve `par.nsf.gov`,
`www.alufoil.org`, `re.public.polimi.it` and `image-ppubs.uspto.gov` (outside the session's allowed
network), so pages were read through the search provider's page reader. Formula images, tables that are
images and figures were not delivered by it; where a number sits in an image this is stated.
`xuebao.neu.edu.cn` timed out (RG4 stays an abstract).

**The main caveat.** Almost every foil-specific number below comes from Chinese plant-level sources
(one overview article, patents, one trade knowledge base). No OEM handbook, standard or peer-reviewed
paper with a table of foil-mill ground cambers was found in open form. The two Chinese textbooks that
have chapters on foil roll grinding are not open (RG45, CIT).

---

## 1. Summary

| # | Question | Status | Most useful findings |
|---|---|---|---|
| 1 | Ground camber of work and backup rolls | **Found in part.** Work-roll magnitudes by pass from three plant-level sources; curve families named. Not found: backup-roll crown and chamfer for foil mills, numerical sine angles, variation with width or alloy as numbers, any OEM or handbook table. | Work-roll crown 40-90 um by pass, finishing 80-90, intermediate 40-65, roughing 40-90 (basis not stated) [RG1 FT]; battery-foil procedure 40 then 60 (unit printed as per mille) [RG2 VP]; crown defined on diameter, examples 0.09 and 0.12 mm on a 1600 mm face [RG3 VP]. A double-rib wave on a four-high foil mill was cured by raising the half angle of the sine curve, not the crown [RG4 AB]. |
| 2 | Grinding accuracy and surface specification | **Found in part.** Roughness by pass well covered (four sources agree within a factor 2); form tolerances only from one patent, vendor pages and steel practice. Not found: any standard, any foil OEM roll drawing tolerance, lay specification, axial resolution of real grinder reports. | Ra roughing 0.22-0.32, intermediate 0.10-0.25, finishing 0.03-0.08 um [RG1, RG2, RG5, RG6]; wheel grit 120 / 220 / 320 for 0.23 / 0.10 / 0.07 um [RG6 EX]; profile error <= 6 um, pairing difference <= 0.05 mm (aluminium cold mill) [RG5 EX]; roundness 1-2 um achieved on foil rolls [RG7 EX]; in-process gauges +-1 um [RG13 VP]. |
| 3 | Grinding defects that print | **Found in part.** Mechanisms, kinematic laws and remedies found; process parameters that let the pitch laws be evaluated found. Not found: amplitudes on foil rolls, the gauge at which marks become visible, a measured strip pitch traced to a grinder. | Feed per roll revolution in final passes 9-53 mm [computed from RG5, RG7]; chatter count = vibration frequency / roll rotation frequency, wheel-unbalance marks 12-240 per circumference [computed from RG8]; a second kind of spiral mark does not follow the feed law [RG8 FT]; EAFA names grinder vibration as a cause of chatter marks on foil [RG19 EX]. |
| 4 | Roll wear and regrind practice | **Not found** for aluminium foil in quantitative form (searched English and Chinese, journals, patents, trade pages). Qualitative statements and steel practice only. | "Wear" in cold rolling is mainly loss of roughness [RG50 AB]; wear changes foil-mill speed through a campaign [RG17 VP]; local work-roll wear gives rolling stripes on the gloss side [RG19 EX]; rolls rest >= 22 h before regrinding [RG5 EX]. |
| 5 | Measured roll profiles, open data | **Found in part.** One paper with measured profiles through a stack model (already in the project, SS-S3); no open data set of roll profiles or grinder reports; nothing for foil. | Patel et al. 2022 [RG34]; an open roundness data set exists but for reference workpieces, not rolls [RG39 AB]; report conventions (21 stations, 50 mm from the ends) from the paper industry [RG16 VP]. |
| 6 | Roll material, hardness, elastic constants | **Found in part.** Hardness ranges from patents and vendor listings; elastic constants only from non-foil roll-stack papers. Not found: an open foil work-roll specification with hardness depth. | Normal foil finishing roll HSD 98 [RG6 EX]; aluminium cold-mill work roll 77-80 HSD, neck 40-45 [RG5 EX]; 3 %Cr / 5 %Cr forged rolls HSD 88-100, hardening depth 20-28 / 30-50 mm [RG37 AB of a vendor page]; E 211-216 GPa, nu 0.3 used in cold-rolling models [RG40 AB]. |

---

## 2. Question 1: ground camber of work rolls and backup rolls

### 2.1 Definition and basis

- Chinese aluminium practice states the roll crown **on diameter**: `Cr = D_centre - D_edge = 2*dt`,
  with `dt` the radial infeed difference at the barrel edge [RG3 VP]. The same page computes template
  settings for crowns of **0.09 mm and 0.12 mm (diameter)** on a 1600 mm barrel face for a
  template-type grinder (the mill type and pass are not stated; the text is about aluminium plate,
  strip and foil rolls).
- A Chinese roll grinder specification states its crown range **on radius**: 0.01-1 mm [RG8 FT]. So
  both bases occur in the same literature and a number without a stated basis is ambiguous by a
  factor 2.
- A hot-mill paper defines thermal camber **on radius**, `R_centre - R_edge`, excluding the last
  20 mm [RG36 EX, aluminium hot rolling, not foil].

### 2.2 Magnitudes by pass (work rolls, aluminium foil mills)

| Source | Mill / product | Pass | Work-roll crown | Basis | Tag |
|---|---|---|---|---|---|
| RG1 | foil rolling in general, no mill named | finishing | 80-90 um | not stated | FT (overview article, numbers unreferenced) |
| RG1 | same | intermediate | 40-65 um | not stated | FT |
| RG1 | same | roughing | 40-90 um | not stated | FT |
| RG2 | battery foil 15 um, 1060, widths 940-1380 mm | passes 1 and 2 (280 -> 130 -> 60 um) | 40 | column headed "Cr (per mille)", as printed | VP |
| RG2 | same | pass 3 (60 -> 28 um) and pass 4, doubled (28x2 -> 15x2) | 60 | as above | VP |
| RG2 | battery foil 12 um, 1235 | rows show 40, 55, 65, 60 | table flattened by the reader, the pass assignment could not be recovered | as above | VP |
| RG3 | aluminium strip / foil roll, face 1600 mm | not stated | 90 um and 120 um | **diameter** | VP |

Reading notes:

- RG2's unit is printed as per mille. Read as thousandths of a millimetre it gives 40-65 um, which
  matches RG1; this reading is my inference and is not confirmed by the page.
- If RG1 follows the diameter convention of RG3, the radius crown per roll is 20-45 um.
- Both RG1 and RG2 give the **larger crown to the later (thinner) passes**. Neither explains why.
- No source gives the crown as a function of strip width or alloy in numbers. RG5 (a patent, six-high
  2350 mm aluminium cold mill with shifting work rolls) classes the products into five width series
  (below 1050, 1050-1250, 1250-1450, 1450-1880, above 1880 mm) and varies the curve parameters by
  series and by pass; the parameter values are in formula images that the reader did not deliver.

**Disagreement.** RG1 gives roughing the widest range (40-90) and finishing the highest (80-90); RG2
gives 40 for the first two passes and 60 for the last two. They agree in direction, not in value. No
commonly repeated "typical" foil camber could be traced to a primary source: the RG1 numbers carry no
reference.

### 2.3 Curve shapes

- Named families for aluminium plate, strip and foil rolls: parabola, sine curve, fourth-order curve
  "or others". Template (copying) grinders give a parabola or near-parabola; CNC grinders give any
  curve "by choosing a different angle or entering coordinates" at fixed crown and face length
  [RG3 VP].
- **Sine curve with a half angle as a second parameter.** On a four-high foil mill rolling decorative
  foil, double-rib (quarter) waves were attributed to too large an "equivalent crown" of the work roll
  in that region; curves of different crown and different half angle were compared and **raising the
  half angle** removed the defect in a plant trial [RG4 AB; the angle and crown values are in the full
  text, which could not be fetched].
  Consistency check [computed, `s28/checks.py`], assuming the usual cosine form
  `drop(u) = C*(1-cos(a*u))/(1-cos(a))`, `u = 2x/L`: at the quarter point the drop is 0.250 C for a
  parabola, 0.268 C at a = 60 deg, 0.275 C at 70 deg, 0.293 C at 90 deg. A larger angle makes the roll
  slimmer at the quarter points for the same total crown, which is the direction RG4 reports. The
  curve definition is my assumption; RG4's own expression was not read.
- **Top roll contoured, bottom roll flat.** A finite-element study of foil-mill work-roll contours for
  the cold (start) and hot (steady) roll recommends an "AFW" contour on the top work roll and a flat
  bottom work roll [RG32 AB].
- **Compound curves.** A work roll "of partial variable diameter", built from several curves, to
  relieve tight edges and rib waves of electronic foil on a 1450 mm foil mill [RG31 AB]; a sine plus
  power-function curve for shifted work rolls of a six-high cold mill [RG5 EX]; a flat barrel with a
  tangent circular edge-relief arc 140 mm long (steel) [RG47 EX]; a sine-shaped end taper 155 mm long
  and 0.775 mm deep on diameter on a 1450 mm steel tandem mill work roll [RG48 EX, steel].
- Laboratory models with circular-arc cambers: tungsten-carbide work roll with a camber radius of
  150 m for 50 um x 40 mm foil at 32 % reduction, thickness variation within 1 um [RG29 AB]; two-high,
  camber radius 59 m and unloaded edge gap 57 um for 100 -> 64 um, variation 4.9 -> 1.3 um [RG30 EX].
  These are narrow laboratory rolls; the barrel lengths were not captured, so the radii cannot be
  turned into crowns here.

### 2.4 Backup rolls, end relief, chamfer

**Not found for aluminium foil mills.** What was found:

- A Chinese text on roll grinders for foil plants says the work-roll barrel is "often ground convex" to
  balance the elastic deformation and then turns to the backup-roll barrel; the sentence is cut off in
  the snippet [RG51 AB].
- Foil mills increasingly carry a variable-crown backup roll instead of a fixed ground one
  [RG46 VP; project sources SS-S26, SS-S28].
- Backup-roll roughness for an aluminium cold mill: 0.70-1.0 um Ra against 0.5-0.9 um on the work roll
  [RG5 EX]; this is the cold mill, not the foil mill.
- Chamfer shapes and their effect on roll-to-roll contact pressure are studied for steel CVC mills
  only (seen as citations inside an open CVC paper, CIT).

### 2.5 How plants choose the camber

- **By model.** A commercial stack-deflection model is used to find the camber for a new alloy: the
  same pass rolled in AA1050 at 3190 kN and in AA5052 at 9115 kN; the extra roll deflection "will
  tend to over roll the edges" and give edge waves, to be compensated by positive bending or by a
  different ground camber [RG17 VP, read in full; a cold mill, not a foil mill; no camber value is
  printed].
- **By trial.** RG4 selected the curve by comparison and a plant trial.
- **By rule.** A conference paper sets out "principles for the best choice" of work-roll crown on
  universal foil mills (one mill that roughs and finishes) and blames a failed 6.5 um campaign with
  ridging and splitting in the middle on the crown design [RG33 AB, the rules were not read].
- **By actuator range.** The ground shape is chosen "to make the best use of the flatness actuators"
  [RG17 VP]. Foil mills control shape mainly by zone cooling because direct gap control is
  ineffective at foil gauge [RG45b EX; RG1 FT].

Consistency check [computed, `s28/checks.py`; generic geometry, not from a source]: a backup roll of
850 mm diameter on 2.9 m bearing centres, loaded over a 1.2 m strip, deflects between centre and
strip edge by 22 um per MN (bending and shear, simple beam). Two such rolls open the gap centre by
44 um at 1 MN and 88 um at 2 MN. RG2 states rolling forces of at least 100-200 t (about 1-2 MN) for
940-1380 mm battery foil. A crown of 40-90 um on diameter on each of the two work rolls closes the
gap centre by 40-90 um, so the published crowns are of the size that backup-roll bending alone
requires. The check ignores roll flattening, work-roll bending, roll-to-roll contact outside the
strip and thermal crown; it is an order-of-magnitude test only.

### 2.6 Interplay with thermal camber and bending

- The project already holds a measured foil-mill thermal crown of at most 30 um on a 260 x 900 mm roll
  (PT-T25 EX; basis not recorded there). Against 20-45 um of ground radius crown per roll this is the same order, so the
  cold and the hot gap differ by an amount comparable to the whole ground camber. RG32 analyses the
  contour for both states for this reason.
- Hot aluminium mill: 13 um measured against 12.3 um simulated camber on radius in one pass
  [RG36 EX, hot rolling].
- With a kissing gap the bender mainly bends the barrel ends (project SS-S26). No new source on this
  was found.

### 2.7 When the camber is wrong

| Statement | Source |
|---|---|
| More roll deflection than the crown allows over-rolls the edges: loose edges, edge waves | RG17 VP |
| Crown too high or too low gives shape defects at the two edges or in the middle "and easily forms pinholes" | RG1 FT |
| Too large an equivalent crown at the quarter points gives double-rib waves | RG4 AB |
| Tight edges and rib waves on electronic foil, relieved by a locally reduced diameter | RG31 AB |
| Ridging and splitting in the middle on a universal mill | RG33 AB |
| Roll-shape instability under high load (soft roll): loose rib, loose centre, frequent breaks; 45 % against 95 % agreement with a 15 I-unit target shape | RG6 EX |
| "edge waves (crown too high) or centre buckles (crown too low)" | RG13 VP, **as printed** |

**Disagreement.** RG13 states the direction opposite to RG17 and to the usual convention (too much
roll crown over-rolls the centre). RG13 is a measuring-system vendor page; I read it as a slip and
would not use it.

---

## 3. Question 2: grinding accuracy and surface specification

### 3.1 Roughness by pass (work rolls)

| Pass | RG1 (overview) FT | RG2 (battery foil procedure) VP | RG5 (patent, 3xxx foil to 8-10 um) EX | RG6 (patent, battery foil 12 um) EX |
|---|---|---|---|---|
| Roughing (to about 60 um) | 0.25-0.30 | 0.3 | pass 1: 0.22-0.32 | 0.25 (0.23 with a 120 grit wheel) |
| Intermediate | 0.16-0.25 | 0.12 | passes 2-4: 0.11-0.18 | 0.10 (220 grit wheel) |
| Finishing / doubling | 0.03-0.05 | 0.12 (doubled 28x2 -> 15x2) | passes 5-6, "mirror ground": 0.037-0.078 | 0.07 (320 grit wheel) |

All values Ra in um, aluminium foil mills. Further points:

- Cold-mill work rolls before the foil mill: 0.5-0.9 um, backup rolls 0.70-1.0 um, coarser for wider
  strip [RG5 EX].
- A foil for electronic devices specifies a final-pass roll of Ra 40 nm or less [RG49 AB].
- Achieved on foil rolls at a roll maker: Ra 0.04 um [RG7 EX].
- Too rough: fine depressions grow into pinholes, breaks, dull surface. Too smooth: low mill speed
  [RG1 FT]. Roll grinding "directly influences the speed of the rolling mill"; a client gained
  20-30 % speed after changing grinding practice [RG17 VP].
- Uniformity matters: top and bottom rolls of unequal roughness give unequal friction and slipping
  [RG1 FT].

**Disagreements.** Intermediate: RG1's 0.16-0.25 against 0.10-0.18 elsewhere. Finishing: RG1's
0.03-0.05 against RG2's 0.12 for a battery-foil doubling pass. The spread is by product (battery foil
is rolled bright on both sides at 12-15 um; the RG1 figures read as packaging foil below 7.5 um), but
no source states that. Rz and lay are **not specified anywhere**; the lay of a ground roll is
circumferential and is transferred as a lengthwise lay (project BT-S9).

### 3.2 Form and position tolerances

| Quantity | Value | Refers to | Source |
|---|---|---|---|
| Ground profile (form) error | <= 6 um | work roll, six-high 2350 mm aluminium cold mill; basis not stated | RG5 EX |
| Diameter difference of the pair in a stand | <= 50 um | same | RG5 EX |
| Roundness required by the customer | <= 3 um | foil roll, stated for bearing seats and shoulders | RG7 EX |
| Roundness achieved | 1-2 um | foil roll | RG7 EX |
| Taper | "generally" 5 um | **steel** cold-mill work roll | RG10 EX |
| Roundness of barrel and neck | 5 um; the barrel may come out 2-3 times worse although the neck is within 5 um | **steel** cold mill | RG10 EX |
| Roll axis to machine datum | 1 um with automatic gauging, 5 um with a dial gauge | **steel** cold mill | RG10 EX |
| Grinder accuracy: roundness, crown profile | +-2 um each; parallelism +-2 um/m | a contract roll shop's machine table, metal not stated | RG15 VP |
| In-process gauge precision: form, diameter, roundness, eccentricity, taper | +-1 um | grinder-mounted gauge | RG13 VP |
| Caliper resolution | selectable 10, 1, 0.5 um, special 0.1 um | paper-industry roll grinders | RG16 VP |
| "Roundness <= 0.01 um, curve deviation +-0.005 um" | as printed, listed under the grinding wheel; the unit is almost certainly mm | RG5 EX |

No standard and no foil-mill OEM tolerance was found. The only aluminium-specific form tolerance is
RG5's 6 um, and it is for the cold mill that feeds the foil mill.

### 3.3 Wheel and process parameters

| Parameter | Value | Source |
|---|---|---|
| Wheel for aluminium cold-mill rolls | medium-soft, 80-120 mesh | RG8 FT |
| Wheel grit for foil rolls | 120 (Ra 0.23), 220 (Ra 0.10), 320 (Ra 0.07) | RG6 EX |
| Wheel for foil roll at a roll maker | "BWA60L" | RG7 EX |
| Wheel speed, finish and final passes on a foil roll | 20-25 m/s, then 8-10 m/s | RG7 EX |
| Roll speed, foil roll | 5 r/min, then 3-5 r/min | RG7 EX |
| Traverse, foil roll | 160-200 mm/min, then 120-160 mm/min; depth 2-5 um, then 1-2 um | RG7 EX |
| Roll speed, aluminium cold-mill roll | rough 33, finish 42, polish 45 r/min | RG5 EX |
| Carriage speed, same | rough 2200 -> 1600, finish 1050 -> 900, polish 850 -> 400, printed as "m/min" (as printed; mm/min is meant) | RG5 EX |
| Wheel speed, same | printed as 32.5-38 "r/min" (as printed; more likely m/s) | RG5 EX |
| Machine ranges of an older Chinese grinder | roll 5-50 r/min, wheel 600-1200 r/min, wheel 750 x 75 mm new, 500 mm worn | RG8 FT |
| General rules | wheel 6500 ft/min falling towards 3000 (33 -> 15 m/s [computed]); roll 60 ft/min roughing, 100 finishing, 150 for Sendzimir rolls (0.30, 0.51, 0.76 m/s [computed]); traverse 3/4 of the wheel width per roll revolution roughing, 1/2 finishing, 1/8 for very fine finish | RG11 VP |
| Coolant | pH >= 9, 4.5 % +- 0.2 %, 5-9 bar; Ra 0.10 um reachable in finish grinding | RG5 EX |

### 3.4 Measurement and what a grinder report contains

- Grinder-mounted calipers traverse the barrel and record diameter continuously; with the roll
  rotating they record roundness and eccentricity at stations. Output: profile graph, roundness polar
  plot, deviation table; the measured profile is fed back to the CNC for the next pass [RG13 VP].
- Two-point contact gives absolute diameter, concentricity and shape; a third probe aligns the roll
  [RG14 VP]. Three modes on one machine: centring (three probes, long traverse), measuring (two
  probes, long traverse, shown as a reference graph and an error graph) and roundness (three probes at
  one station) [RG47 EX, steel].
- Report conventions from the paper industry: **21 equally spaced stations starting 50 mm from the
  face ends**; "station-to-station" tolerance between neighbours; total crown = middle reading minus
  the mean of the two end readings; the crown target is computed per station from the total crown and
  the **cosine angle**; roundness and concentricity normally at the middle and at each end
  [RG16 VP]. On a 1.5-2.1 m barrel 21 stations are 70-100 mm apart [computed].
- Because the caliper measures across the roll, grinder reports are **on diameter** [RG13, RG14,
  RG16].
- Temperature: a 750 mm roll leaves its shape tolerance when the temperature varies by 1.2 K along
  the face [RG12 VP, paper calender]. Check [computed]: 11.7e-6/K x 750 mm x 1.2 K = 10.5 um on
  diameter; for a 280 mm work roll 3.3 um per K, so a +-1 um profile needs the roll uniform to about
  0.3 K. Rolls rest at least 22 h after leaving the mill before grinding [RG5 EX].
- The axial resolution of a continuous trace is **not stated** in any source read.

---

## 4. Question 3: grinding defects that print on the strip

### 4.1 Feed lines (spiral marks, traverse lines)

- Law: the lead of the spiral on the roll equals the traverse per roll revolution. Two kinds of
  spiral mark are distinguished on aluminium cold-mill rolls: one "consistent with the computed
  relation of roll speed and table speed", and one that is **not**, caused by table float on too high
  a slideway oil pressure, of low and irregular frequency and "generally rather wide" [RG8 FT]. A
  troubleshooting table lists "spirals (traverse lines) same lead on work as rate of traverse", cause
  misalignment or truing [RG11 VP].
- Causes of the first kind: wheel face not straight after dressing, wheel-head nod, table float above
  0.02 mm, unequal head and tail stiffness, wheel hardness uneven across its width, dressing on a
  machine not yet thermally settled [RG8 FT]. Remedies: chamfer or round the wheel corners, dress the
  face slightly convex, freer-cutting wheel, lower traverse and wheel speed in the last passes
  [RG8 FT; RG11 VP; RG12 VP; RG27 AB]. Feed lines appear as a spiral "barber-pole" and are "removed
  during finish passes" [RG43 VP].
- **Pitch numbers** [computed from printed speeds, `s28/checks.py`]:

| Case | Traverse / roll speed | Feed per revolution |
|---|---|---|
| Aluminium cold-mill roll, rough passes [RG5] | 2200-1600 mm/min at 33 r/min | 67-48 mm |
| same, finish passes | 1050-900 at 42 | 25-21 mm |
| same, polishing passes | 850-400 at 45 | 19-9 mm |
| Foil roll at a roll maker, finish [RG7] | 160-200 at 5 | 32-40 mm |
| same, final | 120-160 at 3-5 | 24-53 mm |
| Rule of thumb, 75 mm wheel [RG11] | 1/2 and 1/8 of the wheel width | 38 and 9 mm |

  So the pitch left by the last passes lies between about **9 and 53 mm**. On the strip the pitch
  across the width equals the pitch on the roll (the roll does not move sideways); the mark is a
  steep helix on the roll and so a near-lengthwise line on the strip, repeating every roll
  circumference.
- Amplitude of feed lines: **not found.**

### 4.2 Chatter marks from the grinder

- On foil, chatter marks are "intermittent lines perpendicular to the rolling direction", with two
  listed causes: vertical vibration of the mill or work rolls, and "vibration between the grinding
  wheel and the roll". The Spanish and French names of the defect in the catalogue are literally
  "grinding marks" [RG19 EX].
- Periodic sub-micron features from roll grinding are a source of forced vibration in the mill; the
  grinder vibration usually also excites a resonance of the grinding machine; features of a few
  microns are measurable on a marked backup roll [RG18 EX; already project TM-LC14].
- Chatter marks on ground rolls are a periodic waviness "with pitches ranging up to tens of
  millimeters and with amplitudes ranging up to tens of microns" (hot-mill rolls); a controller holds
  residual waviness within a requirement of 1 um. Causes: wheel unbalance or out-of-roundness,
  mode coupling, workpiece-regenerative and wheel-regenerative chatter. Wheel regeneration dominates
  in roughing; finishing is kept stable by a conservative roll speed [RG20 EX, **hot rolling rolls,
  steel**].
- Kinematic law: vibration frequency = work surface speed / spacing of consecutive marks; a frequency
  equal to the wheel spindle speed points to wheel, flange or spindle [RG25 AB]. Number of lobes =
  wheel r/min / roll r/min for once-per-wheel-revolution forcing, lobes "up to 4 to 5 microns"
  [RG26 AB; the patent is about slender shafts for printers, not mill rolls]. "The chatter mark
  spacing can be calculated using roll and grinding wheel speeds to confirm the source" [RG24 VP].
- Orientation tells the source: wheel-spindle vibration and a dull or out-of-shape wheel give a
  **spiral** pattern; steady-rest shoes, tailstock centre, headstock rotation and wheel-head /
  headstock resonance give lines **parallel to the roll axis** [RG24 VP]. Main-spindle faults give
  straight chatter, driver-plate faults give oblique marks [RG10 EX, steel].
- Test values for the count [computed]: with the machine ranges of RG8 (wheel 600-1200 r/min, roll
  5-50 r/min) once-per-wheel-revolution marks number **12 to 240 per roll circumference**. With RG7's
  foil-roll finish settings (20-25 m/s on a 500-750 mm wheel, roll at 5 r/min) the count is 100-190
  and the pitch on a 280 mm roll is 4.6-8.6 mm. A machine resonance of 50-300 Hz at 5-45 r/min on a
  280 mm roll gives pitches of 0.24-13 mm.
- "Dark" (latent) chatter marks, invisible until the roll is stoned or lit from the side, are the
  standing problem on slender foil rolls [RG7 EX; RG5 EX: no spiral or chatter marks visible under
  side light and after stoning]. A displacement-sensor method to find slight chatter marks on ground
  rolls before they reach the cold mill is described [RG22 AB, steel]. A paper on grinding defects of
  foil finishing rolls and how to check grinder precision exists [RG23 AB, content not read].
- Remedies: vary roll and wheel speed, by 10 % per minute [RG10], by 8-10 % every 60 s [RG24], by
  +-20 % with a 5 s period [RG27 AB]; rebalance the wheel twice, softer wheel, dress more often;
  separate foundation; a final polishing step with a finely dressed wheel [RG24 VP]; regrind on the
  journals with steady rests after grinding on centres [RG7 EX].

### 4.3 Other defects

Scratches and "commas" from loose grit or dirty coolant; burn from a hard or dull wheel, too much
infeed or poor coolant aim; scratch length limited to 1.0 mm in one specification [RG8 FT; RG43 VP;
RG5 EX]. The outer 120 mm of each barrel end is stoned after grinding [RG5 EX]. Roll shop success
rate on aluminium cold-mill rolls on an old grinder "not above 70 %", surface defects being the hard
part [RG8 FT].

### 4.4 Not found

Amplitudes of feed lines or grinder chatter on foil-mill rolls; the gauge at which they become
visible; how the mark changes over the roll's campaign; a case that traces a measured foil pitch to a
grinder setting.

---

## 5. Question 4: roll wear and regrind practice

**Not found in quantitative form for aluminium foil.** What exists:

- In cold and temper rolling "wear" means mainly loss of roughness or texture [RG50 AB, steel]. In
  foil rolling the mill speed drifts through a campaign as the rolls wear, and grinding strategies
  exist to hold it [RG17 VP, no numbers].
- "Rolling stripes": on the gloss side only, constant in the rolling direction; causes are local wear
  of the work roll and local roll damage by foreign material in the stock [RG19 EX].
- A sticking event ("aluminium pick-up") should be treated at once to extend roll life [RG8 FT, no
  method given].
- Regrind handling at an aluminium cold and foil plant [RG5 EX]: normal rolls rest >= 22 h, rolls
  from an incident >= 240 h; incident rolls are checked by eddy current every 0.5 mm of removal and
  ground a further 0.2-0.3 mm after they test clean; ultrasonic surface-wave test every 10 campaigns,
  straight-beam test every 20. The rough-grinding schedule sums to 1.6 mm if each of the 44 passes
  takes its printed infeed [computed; whether the infeed is per pass or per stroke and on radius or
  diameter is not stated, so this is an upper reading].
- Rolls must be reground regularly; regrinding changes roughness and near-surface residual stress, so
  reground rolls are re-sorted to passes; cold deep-rolling conditions the outer 0.2-0.3 mm
  [RG28 EX, aluminium strip and foil].
- Trade pages give regrind intervals of 2-8 h for foil rolling, 12-48 h for aluminium cold rolling
  [RG41 VP] with no source; **untraceable**, not to be used.
- No measured wear profile, no wear depth, no statement on how wear changes the effective camber, and
  nothing quantitative on roll coating build-up was found. The project's own view (wear and coating
  are narrow diameter changes at fixed positions) is not contradicted and not supported by numbers.

---

## 6. Question 5: measured roll profiles and open data

- **Patel, Malik, Zhang and Mathews (2022)** remains the only paper found that takes measured new,
  warm and worn work-roll diameter profiles through a roll-stack model to strip thickness (four-high,
  76.2 mm work roll, stainless, aluminium, copper). It is model output, not a rolled-strip
  measurement. The project read it in full (SS-S3 FT); in this session only the abstract was seen
  [RG34 AB here].
- The laboratory chain "ground roll profile designed to give a local wave -> buckle on 270 mm
  aluminium sheet" is already in the project (SS-S19 FT).
- **Open data:** an open roundness measurement data set (raw probe data of reference workpieces on a
  roundness instrument and a three-probe device, CC BY) [RG39 AB]. It is not roll data; it could only
  serve to test a roundness-processing routine. No open set of mill-roll profiles or grinder reports
  was found on the data repositories searched.
- Nothing for aluminium foil: no published ground or worn foil-mill roll profile, as a figure or a
  table, was found.

---

## 7. Question 6: roll material, hardness, elastic constants

| Item | Value | Refers to | Source |
|---|---|---|---|
| Normal foil finishing work roll | HSD 98 | 12 um battery foil, doubling pass | RG6 EX |
| "High-hardness" intermediate and finishing rolls | HSD 115-125, 20-25 above normal (as printed; above the usual top of the scale) | same | RG6 EX |
| Effect claimed | stable shape at high force, 20 % more speed, 15 % more yield, 2-5 % less oil additive | same | RG6 EX |
| Work roll of an aluminium cold mill | forged semi-high-speed Cr steel, barrel 77-80 HSD, neck 40-45 HSD, uniformity +-1.5 HSD | six-high 2350 mm | RG5 EX |
| Work roll of an aluminium plate mill | 70-80 HSD, <= 3 HSD along the barrel, hardening depth 35-50 mm | plate mill | RG38 AB |
| Forged cold-mill work rolls, 3 %Cr and 5 %Cr | HSD 88-100 and 90-100; hardening depth 20-28 and 30-50 mm | steel cold mills, vendor listing | RG37 AB |
| Work rolls for aluminium strip and foil | preferred 830-880 HLE (Leeb) | patent | RG28 AB (number from a search summary) |
| Roll elastic constants used in cold-rolling models | E = 22 000 kgf/mm2 (216 GPa [computed]), nu = 0.3; E = 211 GPa for a cold-work tool-steel roll | thin steel strip models | RG40 AB |
| Tungsten-carbide laboratory rolls | used for foil in RG29, RG30 | laboratory | AB / EX |

- For forged steel rolls E of about 205-210 GPa and nu of about 0.3 are the usual values, and they
  change very little with hardness or heat treatment [from memory]. No source read here states E for
  a foil work roll.
- Bearing on grinding: harder and finer finishing rolls are ground with finer wheels (320 grit) at
  low roll speed and very small infeed (1-5 um) [RG6, RG7]; the hardened depth (20-50 mm on radius
  per the vendor listing) bounds the total regrind stock over the roll's life.

---

## 8. What this gives the simulation

### (a) Defaults or example values for a roll-stack model

**No default can be defended.** Example values, each to be shown as an example and replaced by plant
data:

| Input | Example | Tag and limit |
|---|---|---|
| Work-roll ground crown, foil roughing and intermediate | 40-65 um | RG1 FT, RG2 VP; basis not stated in either; RG3 says the convention is diameter |
| Work-roll ground crown, finishing / doubling | 60-90 um | RG2 VP, RG1 FT; same limit |
| Work-roll curve | parabola or cosine ("sine") with a half angle as free parameter | RG3 VP, RG4 AB; no angle value read |
| Top roll crowned, bottom flat as an alternative layout | qualitative | RG32 AB |
| Backup-roll crown, chamfer | **none** | not found |
| Ground form error (tolerance band for a sensitivity run) | +-3 um on the profile (from "<= 6 um") | RG5 EX, aluminium cold mill, basis not stated |
| Pair diameter difference | <= 50 um | RG5 EX |
| Roundness | 1-3 um | RG7 EX (foil roll); 5 um in steel practice RG10 |
| Work-roll roughness Ra | 0.22-0.32 / 0.10-0.25 / 0.03-0.12 um for roughing / intermediate / finishing | RG1, RG2, RG5, RG6 |
| Roll elastic constants | E 210 GPa, nu 0.3 | [from memory]; RG40 AB gives 211-216 GPa, 0.3 for non-foil cases |

The model should carry the **basis (diameter or radius) as an explicit field** of every camber input;
both occur in the sources (2.1).

A first plausibility test for the stack model [computed]: for generic geometry (backup roll 850 mm,
bearing centres 2.9 m, strip 1.2 m) backup-roll bending alone opens the gap centre by 44 um per MN.
A model that needs a very different crown at 1-2 MN to roll flat should be examined.

### (b) Corrections and test values for the existing grinding rules

1. **Feed-mark pitch.** The law (pitch = traverse per roll revolution) is confirmed [RG8 FT,
   RG11 VP]. Test values: final-pass feeds of 9-25 mm (aluminium cold-mill roll, RG5) and 24-53 mm
   (foil roll at a roll maker, RG7). The rule's supporting test "regular spacing below 30 mm" would
   miss the upper half of this range; a ceiling near 55-60 mm fits the printed data better.
2. **A spiral that does not follow the feed law** exists (table float): wide, irregular, low
   frequency [RG8 FT]. A regular-spacing test will not find it; it belongs with `roll_surface_band`.
3. **Chatter-mark count.** `n = f / n_roll` is supported [RG25 AB, RG26 AB, RG24 VP]. Test values:
   12-240 marks per circumference for once-per-wheel-revolution forcing; 100-190 for a foil roll
   finished at 5 r/min, pitch 4.6-8.6 mm on a 280 mm roll [computed]. The rule's default search over
   n = 1..8 cannot find grinder chatter; it needs the supplied count or the grinder's wheel and roll
   speeds. Asking for wheel r/min and roll r/min of the last pass would let the tool compute the
   count itself.
4. **Orientation.** Grinder marks from wheel-spindle vibration are spiral on the roll, those from
   work-rest, tailstock or headstock are axial [RG24 VP]. A slightly oblique transverse mark on the
   strip is therefore compatible with a grinder source.
5. **Measured roll profile input, basis.** Grinder gauges measure diameter; the guide's instruction
   to halve the deviation is right. Reports state crown on diameter.
6. **Measured roll profile input, grid.** Station reports of 21 points are 70-100 mm apart on a foil
   barrel [RG16 VP, computed]; a stripe of 20-30 mm half-peak width (the guide's worked case) cannot
   be carried by such a report. The input accepts "at least 5 positions"; a warning when the spacing
   exceeds half the narrowest stripe of interest (about 10 mm) would be honest. Continuous traces
   exist on current grinders [RG13 VP] but their resolution is unpublished.
7. **De-trending order.** If a raw profile with a cosine crown is entered, a second-order polynomial
   leaves a broad W-shaped residual: for 80 um diameter crown and a 70 deg half angle 0.68 um
   peak-to-peak on radius over 79 % of the barrel, 1.2 um at 90 deg; order 4 leaves under 0.02 um
   [computed, `s28/detrend_check.py`, curve form assumed]. This is larger than the 0.3 um bump of the
   worked case. Either subtract the grinder's target curve first (as the guide says) or use order 4
   for cosine-ground rolls.
8. **Temperature of the measurement.** 3.3 um per K on a 280 mm roll [computed]; a report taken on a
   roll not yet settled (rest time below about a day, RG5) carries a thermal profile of the same size
   as the grinding tolerance.
9. **Roughness per pass** for BT-G9: the table of 3.1 gives plausible roll Ra inputs when the plant
   has none.

### (c) Inputs the plant must supply

- Ground crown of each work-roll set by pass and width, with basis, curve type, angle or coordinate
  table, and whether top and bottom are alike.
- Backup-roll ground profile, end relief or chamfer geometry, and its wear at change.
- The grinder report as a continuous trace: axial spacing, diameter or radius, target curve
  subtracted or not, roll temperature and rest time at measurement, roundness at stations.
- Last-pass grinder settings: wheel r/min and diameter, roll r/min, traverse speed, wheel width,
  speed variation on or off.
- Roll material, barrel hardness and its uniformity, hardened depth, roll diameter range over life.
- Profile and roughness after the campaign, campaign length, regrind stock; pick-up events.
- Thermal crown at steady state, bending and variable-crown settings in use.

### (d) Contradictions with the project documents

1. `docs/band-diagnosis.md`, section 6.2 (lengthwise hypotheses), `grinding_feed_marks`: "regular spacing (CV < 0.15)
   below 30 mm (S weak)". Printed final-pass feeds reach 40-53 mm on foil rolls [computed from RG7].
   Partial contradiction of the threshold, not of the law.
2. `docs/band-diagnosis.md`, section 6.3 (transverse hypotheses), `work_roll_borne_marks`: "ONE n (1..8 or a supplied
   grinder-mark count)". Not wrong, but grinder chatter counts are 12-240 and more, so without a
   supplied count the rule cannot represent a grinder source. Worth saying in the guide.
3. `docs/band-diagnosis.md`, section 7.9: "`detrend_order` (default 2) removes the crown or camber by
   a polynomial". True for a parabolic crown only; see (b) 7.
4. `docs/band-diagnosis.md`, section 7.9, worked case "crown 2 um": about a tenth of the ground
   crowns reported for foil mills (20-45 um on radius). It is removed by the de-trend and changes no
   result, but it is not a representative example.
5. `docs/simulation-coverage-gaps.md`, C4: "grinding law `n_marks = f_grinder/n_roll_grinding`" and
   "sub-micron grinding waviness is a source": supported, with the note that the open amplitude
   figures are for other rolls (tens of microns on hot-mill rolls RG20; 4-5 um on slender shafts
   RG26) and none is for foil rolls.
6. `docs/simulation-coverage-gaps.md`, G13 ("bending cannot remove them", "grinder profile reports
   before and after a campaign"): not contradicted. No source was found that reports such a
   before-and-after pair.
7. One external inconsistency to keep out of the documents: RG13's direction of the crown error
   (2.7).

---

## 9. Sources

| Id | Citation | URL | Tag |
|---|---|---|---|
| RG1 | Li Zhiyong, Yang Bin, Huang Yongcheng (2019) "Study of the factors influencing the aluminium foil rolling process" (in Chinese), Enterprise Science and Technology & Development; read as a repost | https://www.zzqklm.com/w/kjlw/24793.html | FT (repost read in full; overview article, numbers unreferenced) |
| RG2 | Alfoil World Knowledge Base, "Battery foil production technical procedure" (in Chinese), updated 2026-08-10 | https://alfoilworld.com/knowledge/knowledge-a38e503a/?lang=zh | VP (read in full; tables flattened) |
| RG3 | "Roll crown: introduction" (in Chinese), encyclopaedia compilation of an article on crown grinding on a template-type roll grinder in an aluminium plant; original not identified | https://www.zjtcn.com/baike/guntudujianjie7076099 | VP |
| RG4 | Gong Dianyao, Xu Jianzhong, Di Hongshuang, Lei Yine (2013) "Optimization of working roll curve of four-high aluminum foil rolling mill", J. Northeastern Univ. (Nat. Sci.) 34(7):952-955 | https://xuebao.neu.edu.cn/natural/CN/abstract/abstract4743.shtml | AB |
| RG5 | CN114632820A (2022) "Work roll contour design method for cold rolling and shape control method for ultra-thin aluminium foil cold rolling" | https://patents.google.com/patent/CN114632820A/zh | EX (description read; formula images not delivered) |
| RG6 | CN111438187A (2020) "Production process for lithium battery aluminium foil with high-hardness rolls" | https://patents.google.com/patent/CN111438187A/zh | EX |
| RG7 | Chinese patent application (published 2025-12) "A grinding method for aluminium foil rolls", a roll maker | https://www.xjishu.com/zhuanli/24/202511046305.html | EX |
| RG8 | "Grinding technology for work rolls of aluminium plate and strip cold mills" (in Chinese), repost dated 2013-04-19, authors not shown | https://www.zgdiandu.com.cn/tech/show-39706.html | FT (repost; Table 1 is an image and was not delivered) |
| RG9 | Cui Hongbo (2006) "Discussion on grinding process of working rolls for aluminum cold rolling mill" | https://exa.ai/library/publication/kh7j165lfw7 | AB (possibly the original of RG8; not confirmed) |
| RG10 | Wei Ying, Tang Shuiqing (2021) "Analysis of influencing factors of roller grinding quality and main defect control", Metal World 2021(5), doi:10.3969/j.issn.1000-6826.2021.05.0007 | https://metalworld.ustb.edu.cn/cn/article/pdf/preview/10.3969/j.issn.1000-6826.2021.05.0007.pdf | EX (steel cold rolling) |
| RG11 | Buffalo Abrasives (2012) Roll Grinding Manual | https://www.buffaloabrasives.com/pdf/Roll%20Grinding%20Manual.pdf | VP (excerpt) |
| RG12 | Valmet, "Tips for troubleshooting your roll grinding application"; white paper "Practical roll techniques: grinding and balancing" | https://www.valmet.com/insights/articles/up-and-running/performance/RollGrindingTips/ ; https://www.valmet.com/globalassets/media/downloads/white-papers/roll-services/wpr_grindandbalance.pdf | VP (paper-machine rolls) |
| RG13 | Vollmer, roll measurement systems for roll grinders (VSL series) | https://www.vollmer.se/en/roll-measurement-system/ | VP |
| RG14 | Herkules: C-frame roll measurement system; "Perfect rolls, the very best foil"; industries page | https://www.herkules-machinetools.com/technologies/measuring-technology/c-frame-roll-measurement-system/ ; https://www.herkules-machinetools.com/about-us/news/detail-page-news/perfect-rolls-the-very-best-foil/ ; https://www.herkules-machinetools.com/industries/ | VP |
| RG15 | Rockport Roll Shop, roll grinding specification table | https://rockportrollshop.com/services/roll-grinding/ | VP |
| RG16 | FMT Equipment, roll measurement definitions and RollTrack machine-mounted calipers | https://fmt-equipment.com/roll-measurement/roll-measurement/ ; https://fmt-equipment.com/machine-mounted-2/ | VP (paper industry) |
| RG17 | Innoval Technology blogs: "Why roll grinding is critical to foil rolling" (2017); "Aluminium rolling models: work roll camber" (2016) | https://www.innovaltec.com/roll-grinding-foil-rolling-blog/ ; https://www.innovaltec.com/aluminium-rolling-models-crown-blog/ | VP (both read in full; figures not delivered) |
| RG18 | Innoval Technology blog "Roll and strip chatter marks; 5th octave chatter" (2016); project id TM-LC14 | https://www.innovaltec.com/strip-chatter-marks-blog/ | EX here (FT in the project) |
| RG19 | EAFA (2020) Surface characteristics of aluminium foil; project id SS-S66 | https://www.alufoil.org/surface-characteristics | EX |
| RG20 | Parenti, Leonesio, Bianchi (2016) "Model-based adaptive process control for surface finish improvement in traverse grinding", Mechatronics 36:97-111, doi:10.1016/j.mechatronics.2016.04.001 (postprint) | https://re.public.polimi.it/retrieve/e0c31c0f-5acb-4599-e053-1705fe0aef77/Model-based%20adaptive%20process%20control%20for%20surface%20finish%20improvement%20in%20traverse%20grinding.pdf | EX (introduction and section 2.1; hot-mill rolls) |
| RG21 | Parenti et al. (2015) "A model-based approach for online estimation of surface waviness in roll grinding", Int. J. Adv. Manuf. Technol. 79:1195-1208 | https://link.springer.com/article/10.1007/s00170-015-6864-1 | AB |
| RG22 | Liu Yimin (2013) "Occurrence and measurement of chatter marks on ground roll surfaces", Baosteel Technology | https://en.cnki.com.cn/Article_en/CJFDTOTAL-BGJS201303002.htm | AB (steel) |
| RG23 | Chen Chao (2003) "Grinding defects of finishing roller used for aluminium foil; accounting and examining", Light Alloy Fabrication Technology 2003(12) | http://en.cnki.com.cn/Article_en/CJFDTotal-QHJJ200312008.htm | AB |
| RG24 | HANI trade pages: "Causes analysis for chatter marks on cold rolled strip surface" (2026); "Common defects in cold rolling rolls and their treatment measures" (2025) | https://hanrm.com/causes-analysis-for-chatter-marks-on-cold-rolled-strip-surface/ ; https://hanmillrolls.com/common-defects-in-cold-rolling-rolls-and-their-treatment-measures/ | VP (steel) |
| RG25 | Norton Abrasives, "Keep calm and continue grinding" | https://www.nortonabrasives.com/en-us/resources/expertise/keep-calm-and-continue-grinding | AB (search snippet of a vendor page) |
| RG26 | US 6,244,937 B1 (2001) "Grinding wheel with geometrical pattern" | https://patents.google.com/patent/US6244937B1/en | AB for the lobe numbers (search summary); background read |
| RG27 | US 8,029,338 "Grinding wheel for roll grinding application and method of roll grinding thereof" | https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8029338 | AB |
| RG28 | US 11,110,564 B2 (2021) "Method and device for structurally conditioning a roll" | https://patents.google.com/patent/US11110564B2/en | EX (background and summary); hardness number AB |
| RG29 | Hwang, Kan (2010) "Roll shape design for foil rolling of a four-high mill", AIP Conf. Proc. 1315:587; journal version Int. J. Adv. Manuf. Technol. 91:1587-1597 (2017) | https://pubs.aip.org/aip/acp/article/1315/1/587/943012/ | AB |
| RG30 | Abdi Mirabadi, Alizadeh Kaklar (2026) "Optimization of a two-high cambered mill for the foil rolling", Heliyon, doi:10.1016/j.heliyon.2026.e45623 | https://www.cell.com/heliyon/fulltext/S2405-8440(26)01138-2 | EX |
| RG31 | Yu, He, Chen, Wang, Liu (2020) "Research on work roll contour for improving the flatness defect of electronic aluminum foil", Trans. Can. Soc. Mech. Eng., doi:10.1139/tcsme-2020-0014 | https://cdnsciencepub.com/doi/10.1139/tcsme-2020-0014 | AB |
| RG32 | Chen Changke (the one author the index lists; 2005) "Finite element analysis of work roll contour influence on aluminum foil profile", J. Univ. Sci. Technol. Beijing 27(1); by journal, issue and year probably the paper the project holds as PT-T25 (Liu, Wu, He, Yang, Chen), not confirmed | http://en.cnki.com.cn/Article_en/CJFDTOTAL-BJKD200501023.htm | AB here (EX in the project, if the same) |
| RG33 | Bai Yubo, Chen Guiming, "Principles for the best choice of work-roll crown on universal aluminium foil mills", national foil technology symposium proceedings (in Chinese) | https://www.doc88.com/p-181335007948.html | AB (search snippet only; the document host was not opened) |
| RG34 | Patel, Malik, Zhang, Mathews (2022) Int. J. Adv. Manuf. Technol. 120:7389-7413, doi:10.1007/s00170-022-09228-7; project id SS-S3 | https://par.nsf.gov/servlets/purl/10359685 | AB here (FT in the project) |
| RG35 | Le, Sutcliffe (2000) Wear 244:71-78; project id SS-S72 | https://www.sciencedirect.com/science/article/abs/pii/S0043164800004415 | AB here |
| RG36 | Gavalas, Papaefthymiou (2020) Metals 10(11):1434; project id SS-S68 | https://www.mdpi.com/2075-4701/10/11/1434 | EX (aluminium hot rolling) |
| RG37 | Vendor listings of forged cold-mill work rolls (3 %Cr, 5 %Cr series) | https://m.made-in-china.com/amp/product/TSR-Mill-Rolls-Forged-Rolls-1904100112.html ; https://www.slideshare.net/slideshow/rolling-mill-rolls-production-process-ppt/269896623 | AB (search summary of vendor pages) |
| RG38 | CN118006882B, work roll for an aluminium plate mill and its heat treatment | https://eureka.patsnap.com/patent/CN118006882B | AB |
| RG39 | Aalto University (2022) Roundness measurement dataset, Zenodo record 7004548 | https://zenodo.org/records/7004548 | AB |
| RG40 | InTech chapter 19449 on cold rolling of thin strip (roll parameter table); arXiv:2102.02470 (cold rolling of 316L) | https://intechopen.com/chapters/19449 ; https://www.arxiv.org/pdf/2102.02470 | AB (search summary) |
| RG41 | Trade pages on regrind intervals | https://knowledge.welongoiltools.com/work-roll-regrinding-when-why-and-how-often ; https://tinvogroup.com/roll-change-frequency-cost-control/ | VP (numbers untraceable) |
| RG42 | Achenbach Buschhutten, "Aluminium Rolling Mill Technology" (Die Bibliothek der Technik 233), extract hosted by EAFA | https://www.alufoil.org/files/images_alufoil/about_alufoil/reference_library/achenbach_extract.pdf | EX (the extract holds nothing on rolls or grinding) |
| RG43 | "Calender roll grinding" slides | https://www.spin-corp.com/files/127218787.pdf | VP |
| RG44 | Weiler Abrasives, "Optimizing performance and improving efficiency in roll grinding" (2025) | https://www.weilerabrasives.com/en/na-articles/optimizing-performance-and-improving-efficiency-in-roll-grinding | VP |
| RG45 | Cheng Jie (2010) Aluminium foil production and further processing, Central South Univ. Press, ch. 3.5, 4, 5 (roll grinding, grinding defects); Cheng Rence et al. (2019) Modern aluminium foil rolling and production, section "Rolls and roll grinders" | https://csup.csu.edu.cn/info/1031/6086.htm | CIT (tables of contents only) |
| RG45b | IHI Engineering Review, "Characteristics and line-up of IHI's non-ferrous metal rolling mills" | https://www.ihi.co.jp/en/technology/techinfo/contents_no/__icsFiles/afieldfile/2023/06/18/034e79f963aa97111366d5476bfef163.pdf | EX |
| RG46 | Primetals Technologies, aluminium foil rolling mill page | https://www.primetals.com/en/portfolio/solutions/cold-rolling/non-ferrous/aluminum/aluminum-foil-rolling-mill/ | VP |
| RG47 | Chinese patent application (2021) "Grinding method and device for work rolls" (edge-drop roll, in-process probe modes) | https://www.xjishu.com/zhuanli/24/202110909334.html | EX (steel) |
| RG48 | Chinese patent application (2025) on programming a sine-curve work-roll end contour on a roll grinder | https://www.xjishu.com/zhuanli/24/202411440298.html | EX (steel) |
| RG49 | US 10,166,580, aluminium foil for electronic devices and its production | https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10166580 | AB |
| RG50 | "Damage resistance and roughness retention of work rolls in cold rolling mills", Metallurgical Research & Technology (Revue de Metallurgie) | https://www.metallurgical-research.org/10.1051/metal/2010026 | AB (steel) |
| RG51 | "Roll grinders" (in Chinese), text on rolls and roll grinding for aluminium foil production, author not shown | https://www.doc88.com/p-1867561637658.html | AB (search snippet only; the document host was not opened) |

From memory, not verified in this session: the usual elastic constants of forged steel rolls
(section 7) and their insensitivity to hardness.

---

## 10. Looked for and not found

- A published table of ground cambers for aluminium foil mills by mill type, width, alloy and pass
  from an OEM, a handbook, an association or a journal. Searched in English, Chinese, Japanese and
  German terms; the only numbers are RG1-RG3.
- Backup-roll ground crown, end relief or chamfer geometry for aluminium foil or thin-strip mills.
- The half angle of the sine curve as a number (RG4 has it; the journal site timed out).
- A standard or an open supplier specification for foil-mill roll grinding (form, roundness,
  concentricity, taper, lay). Rz and lay values.
- A real grinder report, or the axial resolution of one.
- Amplitudes of feed lines and of grinder chatter on foil-mill rolls; the foil gauge at which they
  become visible; gloss-band descriptions tied to a grinder cause.
- Measured wear profiles, wear depth, roll-coating build-up, regrind interval and stock removal for
  aluminium foil work rolls; any statement of how wear changes the effective camber.
- An open data set of roll profiles or grinder reports; any measured ground or worn foil-mill roll
  profile.
- A foil work-roll material specification with hardness depth, and measured elastic constants of
  such rolls.
- The original of RG3 and of RG8 (trade-journal articles seen only as reposts); the full text of
  RG4, RG23, RG29, RG31, RG32, RG33; the roll and grinding chapters of the Achenbach book (the open
  extract stops before them); the TALAT rolling lecture (found only on a slide host, not read).
- Panjkovic et al. on chatter and ground-roll marks (cited by RG20; not found).
