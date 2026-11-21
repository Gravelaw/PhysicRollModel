# Work-roll spray nozzles and spray arrangements in aluminium cold and foil mills

Research report, 2026-11-20. Literature and vendor documents only; nothing was checked on a mill.
Source ids are `SN1`...`SN46` (section 4). Sources already used by the band-screening reports are
cross-referenced by their old ids (`PT-T18`, `TM-LA15`, ...). Read tags:

- `FT`: full text read (the part read is stated).
- `EX`: excerpt only.
- `AB`: abstract or snippet only.
- `VP`: vendor, trade or teaching page or catalogue. Flow and width tables are data, but they are the maker's own claims.
- `CIT`: seen only as a citation.
- `[computed]`: my own arithmetic. Script: `../../dev/gap-implementation/prototypes/spray-nozzle-research/checks.py`.
- `[from memory]`: recalled without a source and not verified.

A tag describes this report's own read. Where an earlier report gave the same source a weaker tag,
both tags are stated. No earlier tag was changed.

**Access routes.** Direct fetches of `www.lechler.com`, `xuebao.neu.edu.cn` and `download.cucdc.com`
failed with a DNS error from this session. Those documents were read through the search provider's
page reader (Exa `web_fetch`), and every text-level read in this report used that route. The
Chinese journal paper SN14 (= PT-T18) is a mirror copy with garbled layout: the running text and the
tables are legible, but the figures are not.

**Scope warning.** Most of the quantitative spray literature concerns **water** sprays on steel or on
hot-mill rolls. Every number below states its coolant, mill type and roll. Only SN14 (simulated),
SN15 (simulated) and SN16 (a plate test with one "Al-plate rolling" oil) concern oil at all.

---

## 1. Summary

| # | Question | Status | Most useful findings |
|---|---|---|---|
| 1 | Nozzle types | **Found in part.** The type, angle range, free passage, flow and materials are documented. Which exact nozzle a kerosene foil mill uses is not. | Flat-fan nozzles with a self-aligning mount (dovetail or lugs) and a built-in offset angle are the standard. The fan has a "parabolic" distribution (Lechler) or a "tapered-edge" one (Spraying Systems). Spray angles are 20/30/45/60°, the narrowest free passage is 2.1–10.5 mm, and flows are 7.7–224 l/min at 3–10 bar [SN5 VP; SN9 VP; SN2 FT]. Full cones gave about 20 % more average HTC in a water hot-mill test, but are seldom used because their footprints "clash" [SN4 FT; SN1 FT]. Electric fail-closed valves are used where kerosene is the coolant [SN6 VP]. |
| 2 | Header arrangement | **Found in part.** Rules and typical values are documented. A complete foil-mill layout with barrel length and total nozzle count is not. | Cold aluminium mills use a 52 mm (2") pitch, 25/26 mm (1") at the edges, and 2 or 3 rows [SN1 FT]. One 1800 mm kerosene cold mill has **two rows of 34 nozzles at 52 mm per work roll, entry side only** [SN14 FT, garbled mirror]. Overlap targets are 10–30 % and never above 50 % [SN1], 10–50 % [SN13 EX], or 1/4–1/3 of the spray width [SN7 VP]. The offset (twist) angle is 15° built in, with 15–70° catalogue options; about 60° to the roll axis gave the best cooling in tests [SN5 VP; SN2 FT]. |
| 3 | Zone control | **Found largely.** Minimum on/off times and inductive edge heaters are missing. | Zones match the shapemeter pitch of 26 or 52 mm; 25–100 mm is in use [SN3 FT; SN6 VP]. Control schemes: level control with three rows at 1:2:4 (7 levels) [SN12 FT; SN13 EX; SN24 EX]; basic row (20–30 % of the flow) plus selective row (70–80 %) [SN2 FT]; pulse-width modulation with 10 levels, or 120 levels per 26 mm zone [SN10 VP]. Valve response is about 30 ms, pulse rate 5–10 Hz [SN6 VP; SN11 VP]. Hot-edge sprays use oil up to 120 °C at 26 mm zones on both header ends [SN6 VP]. |
| 4 | Flow and pressure | **Found in part.** No total coolant flow is given for a stated foil-mill barrel. | Q ∝ p^0.5 for flat fans, stated by the vendor and confirmed on the Lechler tables to 0.5 % [SN8 VP; SN5 VP; computed]. Flows per nozzle in aluminium cold mills: 3/6/12 l/min [SN12 FT] and 5/10/20 l/min [SN13 EX]. Header pressure is 2–7 bar [SN14] and valves are rated for 3–9 bar [SN6]. A 1966/1990 foil mill ran 1200 l/min at 6 bar [SN22 VP]. Filtration: plate or stack filters at 0.5–5 µm [SN36, SN37 VP] against nozzle passages of ≥ 2.1 mm. Blockage comes from soaps, sludge and deposits that break loose, not from the particles the filter passes [SN3 FT]. |
| 5 | Footprint and HTC | **Found in part.** No measured footprint profile for an oil spray with numbers, and no correlation for oil with constants. | Catalogue spray widths are 6–14 % larger than 2·H·tan(α/2) [SN5; computed]. Water on a 1 m/s roll: the average HTC over a 900 mm arc is 6.0–16.7 kW/m²K, roughly linear in the number of rows and sublinear in pressure [SN4 FT]. Oil gives 3–6 (or 3–5) times less HTC than water at equal impingement density [SN16 FT]. **Basis of PT-T18:** the 2.5–4.3 kW/m²K is the CFD **average over the roll-wall patch of one two-nozzle zone** (a sprayed-area basis), not a circumferential mean [SN14 FT, garbled]. |
| 6 | Consequences for the strip | **Found in words only; no numbers.** | Gaps between footprints leave stripes [SN1]. Blinded filters cause "surface striping" [SN3]. Misaligned headers give a drive-side/operator-side gradient [SN2, SN3]. Plugged nozzles are named as a cause of asymmetric flatness [SN29]. One patent covers detecting a clogged nozzle and compensating with its neighbours [SN28]. |
| 7 | Standards | **Found in part.** Insurer data sheets exist; no standard for spray geometry was found. | FM DS 7-21 requires the ignitable rolling-fluid supply to be depressurised or isolated by fail-safe valves, plus CO₂ and deluge protection; it says nothing on nozzle geometry or flow [SN34 EX]. Vendors offer fail-closed electric valves for kerosene [SN6 VP]. |

---

## 2. Findings by question

### 2.1 Nozzle types (Q1): found in part

**Types used and why.**

- **Flat fan (flat jet) is the standard work-roll nozzle.** Lechler states that "in most cases flat jets are the preferred nozzle types for roll cooling" because they can be arranged to give an even distribution across the barrel. They need no insert, so they clog less, and their larger drops with higher impact "impinge better through the layer of coolant" [SN2 FT]. Flat jets are "simpler and cheaper than cones" and "less prone to blockage". Their patterns can overlap axially, "whereas those of cone sprays 'clash' and produce a ridge of coolant". The drawback is that "the twist angle of flat jets needs to be set and monitored otherwise very irregular cooling patterns can be produced" [SN1 FT].
- **Full cone.** In a Brno rotating-roll test (water, hot-mill conditions, off-the-shelf nozzles), full cones gave a higher average HTC. The flat jets reached 75.5–85.5 % of the full cone at equal flow [SN4 FT, Table 4]. The flat jets had the higher peak HTC; the cones covered more surface. The author warns that the flat-jet layout was not optimised. Novelis names flat spray ("narrow elliptical pattern") and full cone as "the two main types" [SN13 EX]. In a steel cold-mill test, a flat-jet plus full-cone combination used 25 % less water at a higher HTC [SN17 EX].
- **Solid stream and hollow cone** "are not generally used in the roll cooling application" [SN4 FT].
- **Air-atomising** nozzles appear only for strip oiling, lubrication and blow-off [SN9 VP; SN44 VP]. No source shows them on aluminium work-roll cooling.
- **Drilled or crushed pipes** still occur in old mills, but give "neither an even liquid distribution" nor a reproducible one [SN2 FT].
- **Disagreement.** A Chinese trade article on a single-stand aluminium **hot** mill with emulsion says the opposite of Lechler: cone nozzles for roll cooling, fan nozzles for lubricating the stock [SN33 VP]. The disagreement concerns hot emulsion mills; no foil-mill source says cones are used for cooling.

**Spray distribution of a single fan.**

- Lechler: "parabolic liquid distribution which is ideal for a multi-nozzle header arrangement" [SN5 VP]. "One nozzle alone would produce a parabolic liquid distribution as standard"; special designs give "rectangular or trapezoidal" distributions [SN44 VP; SN4 FT].
- Spraying Systems VeeJet: a "tapered-edge" flat spray, made to overlap, 15–110°; "even" flat sprays (25–65°) are "positioned for edge-to-edge pattern contact" [SN8 VP; SN9 VP].
- Neither maker publishes the shape of the profile as an equation.

**Lechler roll-cooling series** (data sheets and the 12/23 brochure, water, all VP) [SN5]:

| Series | Mount | Built-in offset | Spray angles | Narrowest free passage E | Flow at 3 bar | Flow at 5 bar |
|---|---|---|---|---|---|---|
| 660 | dovetail, 3/8" | 5° | 20/30/45/60° | 0.4–4.4 mm | 0.39–24.5 l/min | 0.50–31.3 l/min |
| 664/665 | dovetail, 3/4" ("industrial standard") | 15° | 20/30/45/60° | 2.1–10.5 mm | 7.7–122 l/min | 10.0–158 l/min |
| 6F4/6F5 | two locating lugs | 15, 20, 25, 30, 35, 40, 45, 50, 60, 70° selectable | 20/30/45/60° | 2.1–10.5 mm | 7.7–127 l/min | 10.0–158 l/min |
| 6E | keys machined into the header plate | in the plate | 20/30/45/60° | 2.1–10.5 mm | as 6F | as 6F |
| 669 | dovetail, 1 1/4" (roughing and plate mills) | 15° | 20/30/45/60° | 5.5–13 mm | 49–196 l/min | 63–253 l/min |

The 660 series is described as "ideal ... especially in small rolling mills for non ferrous metals".

**Spraying Systems VeeJet dovetail tips** (VP) [SN9]:

- Model 18897: offsets 0, 5, 15, 30, 45 and 60°; 3.2–144 l/min and 15–110° at 3 bar.
- Model FSUN-S: 0.2–354 l/min at 5 bar.
- Versions with an integral strainer exist "for applications with clogging problems".

**Materials.** Brass, 303 and 316 stainless steel, hardened stainless steel and PVDF [SN5 VP; SN9 VP]. Headers are stainless steel; some makers use mild steel or aluminium [SN1 FT; SN6 VP]. Relative abrasion resistance: brass 1, stainless steel 4–6, hardened stainless steel 10–15 [SN8 VP].

**Quick-change and self-cleaning.**

- Self-aligning dovetail, locating-lug and machined-plate mounts are standard. "It is not recommended using flat jet nozzles with thread connections" because their orientation cannot be ensured [SN2 FT].
- Valves and nozzles can be removed from the header front [SN6 VP].
- Self-cleaning spray pipes with a rotating internal brush (STAMM) are offered for strip lines, not for work-roll headers [SN6 VP].

**Kerosene foil mills against emulsion cold mills.**

- The nozzle families are the same.
- The difference lies in the valves. Lechler: "EVA valve is used in rolling mills where inflammable rolling oil or kerosene is used ... aluminum cold or foil mills ... built-in function to fail closed"; "electrical valves are used primarily for aluminium rolling systems", while pneumatic Modulax valves are "primarily used for steel" and are "contamination tolerant – can be used with emulsion" [SN6 VP].
- EHT offers COOLECTRO for "rolling oil / kerosene ... aluminium cold" at a pitch > 25 mm, up to 10 Hz and 100 l/min. Its emulsion valve is for a pitch > 50 mm and up to 5 Hz [SN11 VP].
- Viscous oils narrow the spray angle compared with water, which "must be considered ... to ensure correct spray overlaps" [SN2 FT; SN8 VP]. No numbers were found for this.

**Cooling against lubrication headers.**

- Basic row: "the row of nozzles directed to the roll gap is for the basic cooling and lubricating", carrying 20–30 % of the header flow [SN2 FT].
- Steel cold-mill example (80/20 philosophy): "up to a third of the basic spray is being used to spray into the bite to assist in the roll bite lubrication" [SN1 FT].
- In the Brno test header, row "a" (flat jets) was "mainly for lubrication" [SN4 FT].
- Steel: lubrication by direct application from a separate header, or indirectly in the coolant [SN3 FT].
- Aluminium foil or strip: "banks of spray nozzles apply the fluid directly to the rolls in order to effectively cool them, whilst further separately controlled spray nozzles direct fluid on to the rolls nearer to the roll nip in order to lubricate". For lubrication alone, "flow rates of less than 10 litre/minute can suffice" against "up to several thousand litres per minute" for cooling with kerosene [SN23 EX].
- Hot aluminium (emulsion): lubrication nozzles 38 l/min, cooling nozzles 80 l/min [SN33 VP].

**What is missing.** The nozzle type, angle and size actually installed on a named foil mill with kerosene. Only SN14 gives a geometry for a kerosene cold mill, and it does not give the nozzle type or angle.

### 2.2 Header arrangement (Q2): found in part

**Rows and pitch.**

| Mill type | Nozzle pitch | Edge pitch | Rows | Source |
|---|---|---|---|---|
| Hot aluminium | 75 mm (3") | – | 2 or 3 | SN1 FT, Table 1 |
| **Cold aluminium** | **52 mm (2")** | **25/26 mm (1")** | **2 or 3** | SN1 FT, Table 1 |
| Cold steel | 52 mm (2") | – | 1 or 2 | SN1 FT |
| Cold copper/brass | 52/26 mm | – | 2 | SN1 FT |
| Aluminium cold mill, 1800 mm, 4-high single stand, **kerosene** | 52 mm | – | **2 rows × 34 nozzles per work roll; entry side only** | SN14 FT (garbled) |
| Aluminium cold mill (CRM, revamp 2019) | 26/52 mm | – | two double-row work-roll headers and two single-row backup-roll bars | SN11 VP (trade article) |
| Aluminium hot and cold mills | 1–3" | – | "several rows" | SN13 EX |
| Aluminium hot mill, 1650 mm barrel, emulsion | 75 mm (22 nozzles per row), standoff 241 mm | – | 2 bands | SN33 VP |
| Foil mills (Achenbach) | 52 and 26 mm zones, adjustable "with an accuracy of 13 mm to the actual strip edge" | – | "several hundred nozzles ... movable along the roller axis" | SN19 AB; SN20 VP |
| Aluminium foil or cold mills (Lechler EVA) | 52 mm (50 mm optional); Mini EVA 26/25 mm | – | headers for 2 and 3 rows listed | SN6 VP |

**Why 25/26/50/52 mm.** "The Selective Roll Cooling configuration [is] dimensioned to exactly match the pitch of the shape metering roll segments", with rotors "typically a 26mm or 52mm pitch" [SN3 FT; SN6 VP]. 52 mm and 26 mm are the inch pitches (2", 1"); 50/25 mm are metric options [SN6 VP]. The nozzle pitch is therefore set by the valve envelope and the shapemeter, not by the spray.

**Entry and exit side; top and bottom.**

- In a final cold stand, cooling nozzles are generally on the entry side only, because coolant carried into the coil stains it on annealing [SN2 FT; SN3 FT]. The 1800 mm kerosene mill cools on the entry side only, "to improve the exit air purge and reduce rolling-oil contamination" [SN14 FT].
- Exit sprays are more effective [SN2 FT; SN3 FT]. Novelis: "Cool exit side unless carryover is an issue" [SN13 EX].
- Hot steel rule of thumb: exit side ≈ 2/3 of the total flow [SN2 FT].
- Top and bottom must be symmetrical in flow and geometry [SN2 FT; SN3 FT].
- Backup rolls need little cooling; sometimes only the top one is cooled [SN2 FT].

**Standoff.**

| Value | Context | Source |
|---|---|---|
| 150–250 mm, recommended | steel cold reduction | SN3 FT |
| 100 mm and 150 mm | Brno rig, water, hot mill | SN4 FT |
| 241 mm | aluminium hot mill | SN33 VP |
| "not too close to roll", because footprints become sensitive to roll diameter | aluminium (Novelis) | SN13 EX |
| no strong effect on HTC | 1400 mm aluminium strip/foil mill (simulation) | SN15 FT |

**Offset (twist) angle and why it is used.**

- The fan is rotated about the nozzle axis so that neighbouring fans overlap axially without colliding. Lechler general headers: "orifices must be offset 5–15° to the pipe axis" [SN7 VP].
- For roll cooling the offset is also used to spread the footprint **around** the circumference, which lengthens the dwell time. "The steeper the nozzles are the larger will be the cooling band width (vertical) ... the cooling zone width (horizontal) is becoming smaller. Experiments have shown that the optimum cooling effect can be reached at an offset angle of approx. 60° to the horizontal. Increasing the offset angle further to 75° showed a lower cooling effect" [SN2 FT].
- Brno, steel cold mill: changing the offset from 50° to 30° "did not significantly influence" the HTC (0° = jet spraying horizontally) [SN17 EX].
- Catalogue offsets: 5° and 15° built in, 15–70° selectable [SN5 VP]; 0–60° [SN9 VP]. Aluminium hot mill: 10–20° [SN33 VP].
- Hoogovens patent: consecutive rows with opposite twist (a "herringbone") to drain the water to both ends [SN27 AB; steel].
- The "horizontal" here is the roll-axis direction, so the convention matches `offset_angle_rad` in `SprayHeader` (0 = fan along the barrel).

**Overlap of adjacent fans** (definitions differ; see 3(e)).

- Tucker: "Spray overlaps are within a 10 to 30%"; the overlap "should not be more than 50% so that the sprays can be effective in giving local changes ... Ideally ... between 10 and 30% through the work roll diameter range". Also: "stripes on the strip can result from gaps between sprays". The definition as printed is "(pattern width)/pitch × 100%" [SN1 FT].
- 80/20 systems are the exception: the basic rows overlap more [SN1 FT].
- An old header measured 288–393 % overlap ("typical on an interstand roll cooling spray pattern") and was redesigned to 17–33 % [SN1 FT, Tables 2–3].
- Novelis: "Target 10–50% spray overlap for full range of roll diameters" [SN13 EX].
- Lechler general headers: "spray widths B should overlap by 1/3 to 1/4" [SN7 VP].
- Aluminium hot mill: 25–30 % [SN33 VP].
- Lloyd: the overlap is needed "to compensate for the increasing gaps between adjacent oval-shaped foot prints and the lower spray intensity at the outer width of the footprint due to curvature of the roll surface" [SN3 FT].

**Impact angle against the roll.**

- "Directing the nozzles perpendicular to the rolls" gives symmetrical footprints and the highest HTC [SN2 FT, Fig. 13, not legible]. Novelis: "aim near perpendicular to roll" [SN13 EX].
- **Disagreement:** Tucker's steel 80/20 example has basic and selective sprays that "impact tangentially to the roll face, giving the maximum contact with the roll"; the selective spray angle should be "greater than 55°" [SN1 FT].
- Direction against rotation (Brno, water): spraying in the direction of surface motion raised the HTC slightly with speed (+1 % to +14 % from 1 to 2.5 m/s). Against the motion "the opposite will occur" (not measured) [SN4 FT].
- On a 1400 mm aluminium strip/foil mill, the "spray angle" (jet direction) had an optimum at 150°, which equals the measured angle on the mill; "jet angle" was the least important of the four factors [SN15 FT].

**Staggering.** The Brno test header staggered its rows so that full cones would not overlap [SN4 FT]. No aluminium source gives a stagger rule for flat fans.

**Total nozzle count for a foil mill.** Not found for a stated barrel. Indicators:

- 2 × 34 per work roll on an 1800 mm cold mill [SN14].
- "Several hundred" individually controlled nozzles on Achenbach foil mills [SN20 VP].
- [computed] At 52 mm on a 1700–2200 mm barrel, one row has 32–42 nozzles. At 2–3 rows per work roll and two work rolls, plus edge rows at 26 mm, that is about 130–300 nozzles.

### 2.3 Zone control (Q3): found largely

**Zone width.**

- Zone width equals the shapemeter pitch: 26 or 52 mm [SN3 FT]. Lechler offers 25–100 mm [SN6 VP].
- Patents: 2–3 nozzles per zone at about 55 mm [SN26 EX]. A 6-high oil mill had 15 zones of 90 mm with 2 V-jet nozzles and one proportional valve each [SN24 EX].
- Achenbach: 52/26 mm zones moved to the strip edge to within 13 mm [SN19 AB].

**Control philosophies.**

| Scheme | Description | Source |
|---|---|---|
| Level control | Three rows (or three nozzles per zone) with flows in the ratio 1:2:4 give 7 levels, e.g. 5/10/20 l/min → 0–35 l/min per zone. Rows give non-proportional cooling, and "higher levels can even have a reduced cooling performance" because of interaction between banks. | SN12 FT; SN13 EX; SN24 EX; SN25 EX (1/2/4 gpm) |
| Basic + selective | The basic row (20–30 % of the flow) is set to the strip width; the selective row (70–80 %) is zoned to the shapemeter; top and bottom of a zone switch together. | SN2 FT; SN1 FT ("80/20") |
| Single-zone multi-row | All rows aimed into the same zone, giving sensitivity in several steps. | SN1 FT |
| Pulse (PWM) | On/off time sets the volume, e.g. pulse-width ratios of 10 % and 90 %; the valves must respond fast. Primetals ISV: "each valve capable of dispensing ten coolant levels"; the 26 mm electric compact valve gives "up to 120 flow levels per zone". Chinese hot mill: 11 levels from 0 to 100 % by pulsing. The 1800 mm kerosene mill model uses levels 0–10 per nozzle. | SN6 VP; SN10 VP; SN33 VP; SN14 FT |
| Proportional valve per zone | Opening proportional to current, or a solenoid in PWM mode. | SN24 EX |

Innoval recommends replacing three-bar level control on small cold-mill rolls by two pulsed bars, because the third bar interacts with the others and lowers the cooling per litre [SN12 FT]. An aluminium hot mill with time-proportioned on/off valves met "thermal lobes, hydraulic hammers, and thermal waves" [SN30 AB].

**Valve data** (all VP):

| Valve | Response | Pulse rate | Max flow | Pressure | Filtration needed | Source |
|---|---|---|---|---|---|---|
| Lechler EVA (electric, fail closed, kerosene) | 30 ms at 6.5 bar | 5 Hz | 159 l/min at 8 bar (52 mm); 59 l/min (26 mm) | 3–9 bar | 250 µm; 100 ppm metal | SN6 |
| Lechler Modulax DSA (electro-pneumatic) | 30 ms | 5 Hz | as EVA | 3–9 bar | 250 µm | SN6 |
| Lechler Modulax TS (pneumatic, normally open) | 50 ms per metre of control hose | not for pulsing | as EVA | 3–9 bar | 250 µm | SN6 |
| EHT COOLECTRO (rolling oil) | "milliseconds" | 10 Hz | 100 l/min | – | – | SN11 |
| EHT COOLECTRO PRO / PISTONSPRAY / PHRAGMSPRAY | – | 5 / 5 / 2 Hz | 130 / 100 / 100 l/min | – | – | SN11 |

All Lechler valves are rated to 120 °C coolant (so hot sprays are possible) [SN6].

[computed] For a 230–254 mm foil work roll at 25 m/s (1500 m/min), one revolution takes 29–32 ms. A 30 ms valve response is therefore about one revolution, and a 5 Hz pulse period about 6–7 revolutions. Pulsing therefore averages out within the surface thermal time scale of seconds, but not within a single revolution. The "thermal lobes" of SN30 arise at slow hot-mill speeds: at 4.2 m/s on a 0.42 m roll, a 5 Hz period is 0.6 revolutions.

**Minimum on/off times.** Not found as a number in any open source. The valve pulse rate of 5–10 Hz gives a lower bound of 0.1–0.2 s [computed].

**Hot edge sprays and edge heaters.**

- Lechler: "Hot sprays are a special application especially for rolling of aluminum strip in cold rolling mills. In order to fight against so-called 'tight edges', the rolls are less cooled or even heated by the application of heated coolant typically up to 120 °C. The valves with nozzles are typically located on both header sides at small zonings of 26 mm" [SN6 VP] (= PT-T21).
- A Chinese foil-mill utility patent sprays rolling oil heated above 60 °C through 4 groups of nozzles (8 lines) at the ends of the work-roll cooling beam [SN31 EX].
- Siemens (now Primetals) offers an "integrated Hot Edge Spray System to spray hot coolant outboard of the strip edge" [SN10 VP and a 2013 trade journal, AB]. Achenbach offers "UniHeat Curved Hot Edge System" [SN21 VP] with no stated principle.
- **Inductive edge heaters:** no open source with numbers was found.

### 2.4 Flow and pressure (Q4): found in part

**Flow–pressure law.**

- Spraying Systems: Q₁/Q₂ = (P₁/P₂)ⁿ with n = 0.50 for "Flat Spray Nozzles – All" and 0.46 for standard full cones [SN8 VP]. Lechler prints the conversion V₂ = V₁·√(p₂/p₁) under each table [SN5 VP].
- [computed] Q/√p on the Lechler 664.844 row (0.5–10 bar) is 8.84 ± 0.04, i.e. within 0.5 %.
- [computed] The equal-flow pressures in the Brno test, 652.844 at 4.2 bar and 652.804 at 6.5 bar, give 18.1 and 18.0 l/min from √p scaling of the stated 19.76 and 15.81 l/min at 5 bar. This is consistent with the authors adjusting pressure to equal flow [SN4].
- **Oil against water at equal pressure.** The catalogue capacity scales by 1/√SG [SN8 VP]; [computed] that is 1.10–1.15 for SG 0.76–0.82. Measured: "although the pressure of the water and oil was exactly the same, the flow rate of oil through the nozzle was by 15 % higher" [SN16 FT]. Viscosity effects on capacity are not covered by the vendor rule [SN8].

**Flow per nozzle and per metre.**

| Value | Context | Source |
|---|---|---|
| 3, 6, 12 l/min per nozzle | three rows, aluminium cold mill, 0.3 m rolls, coolant not named | SN12 FT |
| 5/10/20 l/min (level) or 5/15/15 l/min (pulse) per nozzle, 35 l/min per zone at level 7 | aluminium (Novelis) | SN13 EX |
| 38 l/min (lubrication), 80 l/min (cooling) | aluminium hot, emulsion | SN33 VP |
| 7.7–127 l/min at 3 bar | catalogue range (water) | SN5 VP |
| [computed] 300–400 l/min per metre per row at 52 mm (664.844 at 3–5 bar; Innoval 3+6+12 l/min); 670 l/min/m at 35 l/min/52 mm | – | – |

**Header pressure.**

| Value | Context | Source |
|---|---|---|
| 200–700 kPa simulated, base 500 kPa | kerosene, 1800 mm aluminium cold mill | SN14 FT |
| jet 26–33 m/s, equivalent to about 2.8–4.5 bar of dynamic pressure at ρ = 800 kg/m³ [computed] | 1400 mm aluminium strip/foil mill | SN15 FT |
| 3–9 bar (valve rating) | – | SN6 VP |
| 6 bar | old foil mill | SN22 VP |
| 4–6 bar | aluminium hot, emulsion | SN33 VP |
| 3–8 bar | cold mills, secondary vendor blog | SN41 VP |

**Total coolant flow.**

| Value | Context | Source |
|---|---|---|
| 1200 l/min at 6 bar | Achenbach foil mill, 1966/1990, 700–1400 mm wide, work roll ≤ 254 mm | SN22 VP |
| 600–800 l/min | foil mill at 210–130 µm | TM-LA35 FT |
| "up to several thousand litres per minute" | kerosene, aluminium cold/foil | SN23 EX |
| 9000–12600 l/min ("2.5–3.5 × main motor kW") | aluminium hot, emulsion | SN33 VP |
| 12000 l/min (filter capacity) | can-stock cold mill | SN46 VP |
| 15000 l/min (filter range) | – | SN36 VP |

**Oil temperature.**

- Kerosene "is recirculated through a filter system and is cooled to about 40 degrees Celsius" (patent background, EX).
- Simulation: coolant 35 °C [SN14]; 20–30 °C as test levels [SN15].
- Earlier reports give 40–45 °C [PT].
- Coolant should be at least 15 °C below the roll surface for selective cooling to act [SN2 FT; steel].

**Filtration and what blocks a nozzle.**

| Item | Value | Source |
|---|---|---|
| Plate or paper filters with filter aid | down to 0.5 µm | SN36 VP |
| Stack filter with powder cake, foil mill | "below 5 micron" | SN37 VP |
| Diatomite and attapulgite precoat by rolling stage | proportions given | CN100350999C, EX |
| Lechler valves | 250 µm and 100 ppm metal | SN6 VP |
| Rule | "the maximum particle size should not exceed 1/3 of the smallest nozzle internal passage" | SN2 FT |
| Nozzle passages | 2.1 mm and up for 7.7 l/min at 3 bar or more | SN5 VP |

[computed] The filter fineness is three orders of magnitude below what could block a nozzle orifice. What blocks nozzles in practice (Lloyd, steel emulsion): "Headers become constricted with detritus and cholesterol over time and suffer nozzle blockages, internal build up of soaps, detritus and sludge"; deposits dry out during stops and "on mill start up ... large particles will detach ... causing ... nozzle blockages"; filters "blinded" or "holed" cause "surface striping defects (differential oil plate out and cooling)". Limits for emulsion: solids < 150 ppm, tramp oil < 0.25 % [SN3 FT]. Spraying Systems offers strainer versions "for applications with clogging problems" [SN9 VP]. No foil-mill (kerosene) source on blockage mechanisms was found.

**Wear.** "Nozzle wear is typically characterized by an increase in nozzle capacity ... Flat fan spray nozzles with elliptical orifices experience a narrowing of the spray pattern" [SN8 VP]. Worn orifices "erode the footprint geometry such that gaps will close and interference of adjacent footprints will ... occur" [SN3 FT].

### 2.5 Footprint and heat transfer on a rotating roll (Q5): found in part

**Footprint width.** Lechler's measured spray width B (water, 3 bar) against the geometric value 2·H·tan(α/2) [computed from SN5]:

| Spray angle | B at H = 250 mm | Geometric | Ratio | B at H = 500 mm | Geometric | Ratio |
|---|---|---|---|---|---|---|
| 20° | 100 mm | 88 mm | 1.13 | 200 mm | 176 mm | 1.13 |
| 30° | 150 mm | 134 mm | 1.12 | 300 mm | 268 mm | 1.12 |
| 45° | 220 mm | 207 mm | 1.06 | 440 mm | 414 mm | 1.06 |
| 60° | 330 mm | 289 mm | 1.14 | 630 mm | 577 mm | 1.09 |

For the larger-flow sizes of the same angle, B is 5–15 % wider again (e.g. 45°: 250 and 490 mm). The spray angle "varies with spray distance" and "does not hold for long spray distances"; viscous liquids form smaller angles [SN8 VP]. On the roll, footprints are "oval-shaped", with "lower spray intensity at the outer width ... due to curvature" [SN3 FT]. With a large offset "the spray height is small in the center and is larger in the outer areas", which lowers the impact at the footprint ends [SN2 FT].

**Distribution across the footprint.**

- Only qualitative statements were found: "parabolic" [SN5; SN44], "tapered-edge" [SN8; SN9], rectangular or trapezoidal for special designs [SN4].
- Lechler shows collected-volume profiles of a standard and a high-pressure flat fan over ±300 mm [SN44 VP]; the numbers are not readable.
- Novelis measured footprints with Fujifilm pressure-sensitive film on a mill roll; the plots ("pressure along spray axis [MPa]") are not legible in the slide text [SN13 EX].
- **No fitted profile with numbers was found.**

**Measured and simulated HTC.**

| Coolant / test | HTC | Basis | Dependence | Source |
|---|---|---|---|---|
| Water, Brno rig, 1.0 m/s, 3–7 bar, 100–150 mm, 1–3 rows; flat jets 652.844 (19.76 l/min at 5 bar, bore 5 mm) and 652.804, full cone 460.844 | 5.3–16.7 kW/m²K; flat jet, 2 rows, 5 bar: 10.3–10.9; peaks to about 40 kW/m²K | **average over the surface interval +200 to −700 mm** (900 mm of arc) | about linear in the number of rows (flat 844: 1→3 rows ×2.34); 3→7 bar ×1.27 (flat 844); 100→150 mm standoff +3.6 to +13 %; 1→2.5 m/s +1 to +14 %; at equal flow, higher pressure gives about 20 % higher peaks | SN4 FT (hot-mill conditions, test plate at 340 °C) |
| Water, rotating large roll, 3 flat-nozzle sizes | 10–22 kW/m²K | **average on the sprayed area** | not related to pressure; about linear in flow; larger distance raises cooling through a larger sprayed area | SN18 AB (= TM-LA17) |
| Water, impinging spray, hot-mill estimate | – | average | proportional to flow-rate density; independent of distance | SN43 AB |
| Water/emulsion, Brno roll rig (D 650 mm), steel cold mill | – (figures) | IHCP around the roll | 5, 4.2, 3.4 bar "comparable"; oil 1 % → −30 %; offset 30° against 50° no significant change | SN17 EX |
| Water/oil/emulsion, static plate, full cone 60°, 12.75 l/m²s at 5 bar, 150 mm, plate 25–250 °C | oil 3–6× below water at equal impingement density (text) / "3–5 times smaller" (conclusions); emulsion 2 % / 4 % → 84 / 79 % of water; 0.1 % → −7.8 %, 1 % → −17.7 % | time-averaged on a plate | water: 10 bar +43 %, 1 bar −47 % against 5 bar | SN16 FT (= PT-T19, EX before) |
| Rolling oils, heated aluminium block | up to 25 % below normal paraffin | relative | coverage area, flow and roll speed are the main factors | SN13 EX (= TM-LA15) |
| Emulsion against rolling oil | emulsion "about four times more effective" | – | – | SN2 FT |
| **Kerosene, CFD (Fluent), 1800 mm aluminium cold mill**, nozzle modelled as a 10 × 1.5 mm slot, 500 kPa, wall at 323 K, 31.746 rad/s | rises to about 3.0 then 4.0 kW/m²K as the coolant spreads; 2.5–4.3 kW/m²K over 200–700 kPa | **"average heat convection coefficient of the work roll spray cooling zone"**: average over the roll-wall surface of the CFD domain (one zone, two nozzles, periodic sides); "the jet's direct coverage area is the main region of convective heat transfer" | rises with pressure | SN14 FT (garbled; = PT-T18) |
| Rolling oil (coolant not named), FE, 1400 mm strip/foil mill | heat flux 94–180 kW/m² (not an HTC) | one nozzle | viscosity > jet speed > coolant temperature > jet angle; distance insensitive; validated against one measured roll cool-down (38.2 → 36.1 °C in 60 s) | SN15 FT (= PT-T17, AB before) |
| Coolant not named, ISIM model | overall 4.65 / 4.98 / 5.51 kW/m²K | "inversely proportional to the area cooled" | – | SN12 FT (= PT-T20) |
| Lechler header study | "cooling effect" 4.98–11.2 kW m⁻¹ °C⁻¹ | **per metre of barrel per kelvin**, i.e. HTC integrated around the circumference | – | SN1 FT, Tables 2–3 |

**Exponents of the HTC on flow** [computed; n defined by HTC ∝ Qⁿ with Q ∝ √p]:

| Data | n | Coolant / context |
|---|---|---|
| Brno flat 844, 3→7 bar | 0.57 | water |
| Brno full cone, 3→7 bar | 0.79 | water |
| Brno flat 844, 1→3 rows | 0.77 | water |
| Brno full cone, 1→3 rows | 0.47 | water |
| Horák water, 5→10 bar | 1.03 | water |
| Horák water, 1→5 bar | 0.79 | water |
| Shao 2015 (kerosene, CFD), 200→700 kPa | 0.87 | kerosene |
| Lee 2002 | about 1 ("approximately linearly") | water |

**Correlations with constants.**

- Water and steel only: Nozaki-type h = 1570·W^0.55·(1 − 0.0075·T_w)/α and others, for continuous casting at high surface temperature [SN42 EX]. HTC = 38.448·Im^0.454·Qi^0.132 above the Leidenfrost point [SN39 AB]. Neither applies to a 40–80 °C roll under oil.
- Novelis "correlations developed for design" are not public [SN13].
- A hot-aluminium roll model uses a water correlation in Q = V_sp/A_sp and p_sp, with B = (u_cw/16)^−0.17 for Q < 10×10⁴ L/(s·m²) and γ = 1.01 [SN38 EX]. The formula itself is printed as an image and could not be read.
- **No correlation for oil was found.**

**Basis question (X3).** See 3(c).

### 2.6 Consequences for the strip (Q6): found in words only

- "Stripes on the strip can result from gaps between sprays, which are a result of undercooling on the work roll." Excessive overlap gives poor zone sensitivity and a slow flatness response [SN1 FT].
- A hot aluminium mill (100 mm spacing, large overlaps) could not control the strip edge temperature; changing to 75 mm and "a more vertical spray" gave "excellent zonal sensitivity" [SN1 FT].
- Blinded or holed filters cause "surface striping defects (differential oil plate out and cooling)". Header misalignment or detritus on one side gives transverse gradients, and coil shape deteriorates after cooling while the shapemeter showed flat strip [SN3 FT; steel].
- Unaligned headers lead to different footprints on the drive and operator sides, profile deviations and steering problems [SN2 FT].
- "Plugged coolant spray nozzles on one side of the mill" are listed as a cause of asymmetric flatness [SN29 EX; aluminium strip].
- Total or partial clogging is detected by opening valves one at a time at constant head and measuring the flow; the neighbours then compensate by changed pulsing [SN28 EX; Alcan].
- Rib (quarter) looseness was removed with nozzles of twice the diameter at 1/5–1/4 of the barrel [PT-T38].
- "Hot bands across the strip, repeatable position: plugged or missing nozzles" [SN41 VP, secondary, steel-oriented].
- **No case with numbers** (band width, I-units, temperature or diameter change) was found for aluminium, and none for steel.

### 2.7 Standards and guidelines (Q7): found in part

- **FM Global DS 7-21 Rolling Mills.** "Some mills also spray ignitable rolling fluid onto work surfaces". The key safeguards are to depressurise or isolate the rolling-fluid supply promptly with remote shut-off valves that are "fail-safe", to divert the return, and to provide a CO₂ roll-bite "spurt", total-flooding or local CO₂, and deluge at 12 mm/min. "The spray application of an ignitable liquid ... likely produces an ignition sensitive, flammable atmosphere" [SN34 EX]. Nothing on nozzle type, flow or pressure.
- **AXA XL PRC.17.1.3.1** is similar (CO₂ to NFPA 12, spurt actuated by UV/IR or by loss of web tension) [SN35 AB].
- Consequences for nozzle choice come only from vendors: fail-closed electric valves without compressed air for kerosene [SN6 VP]. The coolant temperature limit is 120 °C for the valves; the flash-point concern for hot sprays is in PT-T9/T10.
- No ISO, EN or VDI standard on rolling-mill spray headers was found. Nozzle test standards exist for agriculture [from memory: ISO 5682 series] and were not checked.

---

## 3. What this gives the simulation

### (a) What a specification can name that the present header cannot represent

The present header has one row, identical nozzles, a top-hat footprint, one coefficient linear in level, and one standoff and offset. Ranked by how much each would change a computed thermal stripe:

1. **Footprint shape (top-hat against parabolic or tapered).** For the same flow, a parabolic profile puts 1.5× more coolant on the nozzle axis than a top-hat of the same width.
   - [computed, script part 12] The heat-transfer deficit of one blocked nozzle peaks at 1.05 of the header mean, with a half-width of 1.0 pitch, at W/p = 1.43. A top-hat gives 0.70 and 1.43 pitch.
   - At the demo ratio W/p = 3.21, the parabolic peak is 0.47 against 0.31 for the top-hat.
   - A blocked-nozzle stripe would therefore be roughly 1.5× deeper and about 0.7× as wide before axial conduction smooths it. This is the largest single change, and it applies to every blocked- or weak-nozzle result.
   - Even a healthy header has ripple with parabolic fans: about 0.88–1.07 of the mean at W/p = 1.43 and 0.95–1.04 at 3.2 [computed, part 11].
2. **Footprint width as built, not as drawn.** The present W_eff is geometric. Catalogue widths are 6–14 % wider (water, 3 bar), oil narrows the angle by an unknown amount, and worn elliptical orifices narrow the pattern [SN5; SN8; SN2].
   - Vendor overlap practice (10–30 %, at most 50 %) means W_eff/p ≈ 1.1–1.5. The demo header has 3.2 (`band_diagnosis_*.json`: 52 mm, 200 mm, 0.8 rad, 0.17 rad).
   - The model can represent the narrower footprint, but that needs an input, not new code. A narrower footprint roughly doubles the peak deficit of a blocked nozzle (top-hat: 0.31 → 0.70) [computed].
3. **Several rows per roll with different flows, footprints and functions.** Examples: basic + selective; 1:2:4 level rows; a lubrication row aimed at the gap; edge rows at 26 mm beside body rows at 52 mm [SN1; SN2; SN12; SN13].
   - A blocked nozzle in a 1:2:4 zone removes only 1/7, 2/7 or 4/7 of that zone's flow.
   - The rows have different footprints and wet different arcs, and their effects do not add (bank interaction; ISIM shows higher levels can cool less) [SN12; SN1].
   - The present per-nozzle level can mimic a flow fraction, but not the different widths and arcs, nor the interaction.
4. **Non-linear HTC in flow.** The present model makes h linear in level. Published exponents are n ≈ 0.5–1.0 [computed table, 2.5]. For a nozzle at 45 % flow, h falls to 0.45^0.6–0.45^0.9 = 0.49–0.62 of healthy, against 0.45 in the model. The model's deficit is 0.55; with n = 0.9 it is 0.51 and with n = 0.6 it is 0.38. The stripe of a partly blocked nozzle is therefore overstated by 7 % (n = 0.9) to about 45 % (n = 0.6) [computed]. A fully blocked nozzle is unaffected.
5. **Edge heating: hot-edge sprays, edge rows, nozzles movable to the strip edge.**
   - Hot sprays inject heat, at oil up to 120 °C or above 60 °C, at 26 mm zones beyond the strip edge [SN6; SN31]. The model has a single coolant temperature and only cooling.
   - Edge nozzles that track the strip edge to within 13 mm [SN19] need positions that change with width.
   - This matters for edge bands and tight edges (G7), not for body stripes.
6. **Per-nozzle standoff and alignment: a header out of parallel or level, roll diameter change.** These change W_eff and impact along the barrel, giving a drive-side/operator-side gradient [SN2; SN3]. The model has one standoff.
7. **Valve type.**
   - PWM at 5–10 Hz is a time-averaged level for the bulk thermal model, so the present levels suffice. Lobes would only appear at slow speeds [computed].
   - Level control is a quantisation: 7 or 10 or 120 steps.
   - On/off valves were already found not to settle in the closed loop (section 11, G5). The valve type and level count therefore belong in the zone definition.
8. **Offset angles above 60°.** Lechler sells 70°, and 75° was tested [SN5; SN2]; `SprayHeader.validate` rejects more than 60°. The circumferential spread with offset belongs to the wetted arc (A4/A5), not to the axial footprint.
9. **Direction of spray relative to rotation, and tangential against perpendicular impact.** The effect on HTC is ±1–14 % in water [SN4]. This is second order.

### (b) Proposed header inputs covering real specifications

One `rows` list per work roll, each row with its own fields. Defaults are only those the sources support.

| Input | Meaning | Default or example and source | Tag |
|---|---|---|---|
| `rows[].side` | entry or exit | example: entry only for a final stand [SN2 FT; SN14 FT] | FT |
| `rows[].role` | basic, selective, lubrication, edge, hot_edge | basic carries 20–30 % of the header flow, selective 70–80 % [SN2] | FT |
| `rows[].pitch_m` | nozzle pitch | 0.052 for the body, 0.026 for edges [SN1; SN6] | FT, VP |
| `rows[].first_position_m` or `stagger_m` | lateral shift of the row | no default; staggering is documented for cones only [SN4] | – |
| `rows[].standoff_m` | nozzle-to-surface distance along the jet | no aluminium default; 0.15–0.25 for steel [SN3]; 0.24 hot aluminium [SN33] | FT, VP |
| `rows[].spray_angle_deg` | nominal angle (water, catalogue pressure) | catalogue steps 20/30/45/60 [SN5] | VP |
| `rows[].width_source` | `catalogue` (B at H, p) or `geometric` | catalogue B/geometric = 1.06–1.14 at 3 bar water [SN5; computed] | VP + computed |
| `rows[].offset_angle_deg` | twist from the roll axis | 15 built in [SN5]; about 60 optimum for coverage [SN2]; range 0–70 | VP, FT |
| `rows[].nozzle_type` | flat_parabolic, flat_even, full_cone | flat_parabolic [SN2; SN5] | FT, VP |
| `rows[].profile` | axial footprint shape | `parabolic` (1 − (2x/W)²) as a stand-in for "parabolic"; `tophat` for "even"; **the actual shape must be measured** (none published) | VP for the name; shape not defensible |
| `rows[].flow_lpm_at_bar` (Q_ref, p_ref) | flow number | e.g. 3/6/12 l/min [SN12]; 5/10/20 [SN13]; catalogue 7.7–127 l/min at 3 bar [SN5] | FT, EX, VP |
| `header_pressure_bar` | supply pressure | example 5 bar (range 2–7) [SN14]; valves 3–9 bar [SN6] | FT, VP |
| `coolant_specific_gravity` | for Q = Q_ref·√(p/p_ref)/√SG | about 0.8 [from memory] or measured; +15 % flow seen for one oil [SN16] | FT for the +15 % |
| `htc_flow_exponent` | h ∝ (Q/Q_healthy)ⁿ | 0.5–1.0, oil value unknown; keep 1 as the present assumption and offer 0.6 as a sensitivity | computed from FT/AB water data and one CFD |
| `rows[].arc_rad` | wetted arc of the row | no default (plant geometry); feeds A4/A5 | – |
| `zones[]` | list of (row, nozzle) members, `zone_pitch_m`, `valve_type` (on_off, pwm, proportional, level_124), `levels`, `pwm_hz`, `response_s`, `min_dwell_s` | zone pitch = shapemeter pitch, 0.026/0.052 [SN3]; PWM 10 levels [SN10]; 5–10 Hz, 0.03 s [SN6; SN11]; minimum dwell not defensible | FT, VP |
| `rows[].coolant_temperature_c` | per row, for hot-edge rows | up to 120 °C [SN6]; above 60 °C [SN31] | VP, EX |
| `rows[].edge_tracking` | nozzles follow the strip edge | Achenbach: within 13 mm [SN19] | AB |
| `header_tilt` / `standoff_ds_os_m` | misalignment | no default | – |

### (c) What can now be said about the basis of published heat-transfer coefficients (X3)

- **PT-T18 / SN14 (2.5–4.3 kW/m²K, kerosene, simulated)** is the area average over the roll-wall surface of a periodic CFD segment containing one cooling zone with two nozzles. The roll itself is not modelled ("replaced by a fixed-temperature wall") because circumferential heat transfer is ignored. The authors say the jet's direct coverage dominates the transfer. It is therefore a **sprayed-area (cooling-zone) value**. The size of the wall patch, and so the wetted arc, is not stated in the legible text.
  - The project's earlier reading ("jet-zone value") is right in kind.
  - Comparing it with the model's circumferential mean mixes bases, as `basis_comparable: NOT_ESTABLISHED` assumes. The flag can now say *established: not comparable*.
  - The conversion still needs the plant's arc. [computed] For arcs of 20–90° the circumferential mean is 0.14–1.07 kW/m²K.
- **The Brno water values** (SN4; Tucker) are averages over a fixed **900 mm surface interval**. [computed] On the rig's 650 mm roll (diameter taken from SN17; SN4 does not state it) that is 44 % of the circumference, so the flat-jet 10.3 kW/m²K corresponds to about 4.5 kW/m²K as a circumferential mean.
- **Lee 2002**: average on the sprayed area [SN18 AB].
- **Horák 2011**: a time-averaged plate value, neither on a roll nor on an area of a roll [SN16 FT].
- **Lechler "cooling effect"**: kW per metre of barrel per kelvin [SN1 FT], i.e. h integrated around the circumference. Dividing by πD gives the circumferential mean [computed].
- **Innoval "overall htc"**: power/(area cooled × ΔT) [SN12 FT]. The "area cooled" is not defined further, so the basis remains open.

**The general rule that emerges.** A published spray HTC is usable only with the area it is averaged over. Three of the six sources state that area: SN4 (900 mm), SN18 (sprayed area) and SN1 (per metre of barrel). SN14 states it qualitatively (the zone's wall). SN12 does not state it. SN16 is a plate test.

### (d) Inputs the plant must supply

- Header drawings: rows per roll and side, the angle of each row around the roll, standoff (along the jet), pitch and first-nozzle positions, the offset angle of each row, whether nozzles are staggered, and top/bottom differences.
- The nozzle type number of each row, which gives the flow at the reference pressure and the catalogue width B at H. Also the header pressure and the oil density.
- The zone map: nozzle to valve to shapemeter zone, the valve type, levels or PWM period, response, and minimum on/off times as set in the flatness controller.
- Hot-edge or edge rows: position, oil temperature and flow.
- A measured footprint: a pressure-film or grease print on the roll [SN13; SN2], or a patternator profile in oil. No published profile can replace it.
- A roll temperature scan or a thermal camber, for the existing calibration routine (A5).
- The record of nozzle blockages and filter state, if bands are to be traced to nozzles.

### (e) Statements in the project documents that the sources contradict or qualify

1. **Source tag of the footprint formula.** `docs/band-diagnosis.md` l.1747–1748: "`W_eff = 2*standoff*tan(angle/2)*cos(offset)` [V: Lloyd 2010; Tucker 2006]". The same tag is in the `roll_thermal.py` docstring.
   - Both papers were read in full here [SN3; SN1], and neither prints this formula. Lloyd describes oval footprints whose outer parts have lower intensity; Tucker gives only the overlap rule.
   - The formula is geometric, so the tag should be [D].
   - The catalogue widths it should be checked against are 6–14 % larger [SN5; computed].
2. **"Nozzle-pattern ripple ... is an artefact of the idealisation".** `docs/band-diagnosis.md` l.1777–1780 (also `roll_thermal._LIMITATIONS`): "Real fans have a tapered flow distribution, so this ripple is an artefact."
   - With a parabolic profile, a healthy header still has a ripple of about −12 %/+7 % of the mean at W/p = 1.43 (vendor overlap) and about ±5 % at W/p = 3.2 [computed]. Lechler claims "very even" distribution only for its own designs.
   - Whether real headers ripple is therefore **not established**. "Artefact" should read "of unknown size; the top-hat value is not representative".
3. **Overlap limit and its definition.** `docs/band-diagnosis.md` l.1070 and 1091 ("published 10-30 % (never above 50 %) [PT-T22, PT-T21]"), with the project's definition (W − p)/W in `band_signatures.spray_coverage`.
   - Tucker's printed definition is "(pattern width)/pitch × 100%". Taken literally, that cannot be 10–30 %; his old-header values of 288–393 % fit W/p or (W − p)/p [SN1].
   - Lechler defines overlap as a fraction of B, which is the project's convention [SN7]. Novelis targets 10–50 % [SN13].
   - The demo verdict stands under every definition: 0.69, 2.2 or 3.2 [computed]. The published range should carry "definition varies; 10–50 % (Novelis)".
4. **What PT-T18 describes.** `process-temperatures.md` row "Spray coefficient": "Simulated, 1800 mm cold mill, 34 nozzles at 52 mm", and "3.0 rising to 4.0 kW/m²K in the jet zone at 500 kPa".
   - The mill has **two rows of 34 nozzles at 52 mm per work roll, entry side only, coolant kerosene** [SN14].
   - The rise from 3.0 to 4.0 kW/m²K is in **time**, as the coolant spreads over the wall, not across space.
   - The value is a cooling-zone wall average. See 3(c).
5. **"The coefficient is about linear in flow".** `docs/simulation-coverage-gaps.md` l.204 (A5) and the code (`s_i*pitch/W_eff`).
   - This holds for sprayed-area water averages [SN18 AB; SN43 AB].
   - The Brno roll data give HTC ∝ Q^0.5–0.8, and CFD for kerosene ∝ Q^0.87 [computed].
   - Level-controlled multi-row systems can even cool less at a higher level [SN12 FT; SN13 EX].
   - "About linear" should be "between Q^0.5 and Q^1, for water and one kerosene CFD".
6. **"Oil 3–6 times lower" [PT-T19].** `process-temperatures.md`. The same paper's conclusions say "about a 3–5 times smaller cooling intensity" [SN16 FT]. Both numbers should be cited.
7. **Offset limit in code.** `SprayHeader.validate` caps `offset_angle_rad` at 60°, but catalogue nozzles are sold with 70° [SN5]. This is not a document statement; noted for completeness.

No statement in `docs/band-diagnosis.md` on the 20 s response, the hot-edge temperature (up to 120 °C, now confirmed with "both header sides, 26 mm" [SN6]) or the zone pitch (25–100 mm) is contradicted.

---

## 4. Sources

| Id | Citation | URL | Tag |
|---|---|---|---|
| SN1 | Tucker D. (Lechler Ltd), "Flatness and profile – the problems that can exist in the design of the spray actuators", IOM3 conf. *Achieving Profile & Flatness in Flat Products*, Birmingham, 24–25 Jan 2006 (= PT-T22, TM-LA14, EX there) | https://www.lechler.com/fileadmin/media/fachberichte/metallurgy/lechler_fachbericht_walzenkuehlung_01-2006_flatness-and-profile-the-problems-that-can-exist-in-the-design-of-the-spray-actuators_dtucker_en.pdf | FT (Exa reader; figures not seen) |
| SN2 | Wenig H. (Lechler GmbH), "General aspects of roll cooling for hot & cold rolling mills", n.d. | https://www.lechler.com/fileadmin/media/fachberichte/metallurgy/lechler_fachbericht_walzenkuehlung_general-aspects-of-roll-cooling-for-hot-and-cold-rolling-mills_hwenig_en.pdf | FT (Exa; figures not legible) |
| SN3 | Lloyd D. (Lechler Ltd), "Fundamentals of roll cooling and control of flatness at primary cold reduction", 09/2010 (steel) | https://www.lechler.com/fileadmin/media/fachberichte/metallurgy/lechler_fachbericht_walzenkuehlung_09-2010_fundamentals-of-roll-cooling-and-control-of-flatness-at-primary-cold-reduction_dlloyd_en.pdf | FT (Exa) |
| SN4 | Tucker D. (Lechler Ltd), "A quantitative study into the comparative efficiency of flatjet and full cone spray nozzles when applied to the application of work roll cooling", n.d. (Brno rig, water, hot rolling) | https://www.lechler.com/fileadmin/media/fachberichte/metallurgy/lechler_fachbericht_walzenkuehlung_quantitive-study-into-the-comparativeefficiency-of-flatjet-and-full-cone-spray-nozzles-when-applied-to-the-application-of-work-roll-cooling_dtucker_en.pdf | FT (Exa; tables read, figures not) |
| SN5 | Lechler data sheets, roll-cooling series 6F, 664/665, 660; brochure "Precision nozzles and systems for roll cooling" ed. 12/23 (6E, 669) | .../datenblaetter/metallurgy/EN/lechler_metallurgy_datasheet_roll-cooling_series-6f_gb.pdf ; ...series-664-665_gb.pdf ; ...series-660_gb.pdf ; https://www.lechler.com/fileadmin/media/kataloge/pdfs/metallurgy/EN/lechler_brochure_rollcooling_en.pdf | VP |
| SN6 | Lechler SELECTOSPRAY brochure; Lechler US SELECTOSPRAY page; Lechler US "Aluminium industry" brochure | https://www.lechler.com/fileadmin/media/kataloge/pdfs/metallurgy/EN/lechler_brochure_selectospray_en.pdf ; https://www.lechlerusa.com/en/products/product-by-market/metals/nozzles-for-roll-cooling/selectospray ; https://www.lechlerusa.com/fileadmin/media-usa/Literature/Brochures/metal/Aluminium_Industry_Brochure_LR_compressed.pdf | VP |
| SN7 | Lechler, "Technical planning guide"; Lechler web page "Technical aspects of flat fan nozzles" | https://www.lechlerusa.com/fileadmin/media-usa/Literature/Brochures/Technical_Planning_Guide_Brochure.pdf ; https://www.lechler.com/de-en/service-support/technology/basics-nozzle-technology/spray-character/flat-fan-nozzles/technical-aspects-flat-fan-nozzles | VP (snippet) |
| SN8 | Spraying Systems Co., Catalog C44B "Steel mills – Technical reference" | https://www.spray.com/-/media/dam/industrial/usa/sales-material/catalog/c44b_steel-mills_tech-reference_f.pdf | VP (read) |
| SN9 | Spraying Systems Co., C44B "Solutions for cold rolling mills" and "... hot rolling mills"; Cat. 75 flat spray | https://www.spray.com/-/media/dam/industrial/usa/sales-material/catalog/c44b_steel-mills_cold-rolling-mills_d.pdf ; .../c44b_steel-mills_hot-rolling-mills_c.pdf | VP (snippet) |
| SN10 | Primetals Technologies, "Integrated Solenoid Valve Spray System" (web page) | https://www.primetals.com/en/portfolio/solutions/cold-rolling/non-ferrous/aluminum/integrated-solenoid-valve-spray-system/ | VP |
| SN11 | Evertz Hydrotechnik, product brochure 2020 (spray valves); Aluminium Journal, "Successful replacement of a selective roll cooling system", 23 Sep 2024 | https://www.evertz-hydro.com/fileadmin/evertz/PDFs/2020_EVERTZ_Produktbroschuere-HUETTENINDUSTRIE_WEB_2.0-en.pdf ; https://aluminium-journal.com/successful-replacement-of-a-selective-roll-cooling-system | VP |
| SN12 | Innoval Technology blogs: "Aluminium rolling models: optimising spray cooling" (9 Dec 2016, = PT-T20/TM-LA29); "... roll cooling systems" (30 Sep 2016); "Benefits of optimising roll cooling when rolling aluminium" (11 Feb 2016) | https://www.innovaltec.com/optimising-spray-cooling-blog/ ; https://www.innovaltec.com/roll-cooling-blog/ ; https://www.innovaltec.com/roll-cooling-rolling-aluminium-blog/ | FT, FT, EX |
| SN13 | Hobbis A. (Novelis), "Roll cooling in Novelis aluminum hot and cold rolling mills", STLE Annual Meeting 2017 (= TM-LA15) | https://www.stle.org/images/pdf/STLE_ORG/AM2017%20Presentations/Nonferrous%20Metals/STLE2017_Nonferrous%20Metals%20II_Session%206L_A.%20Hobbis_Roll%20Cooling%20in%20Novelis%20Aluminum%20Hot%20and%20Cold%20Rolling%20Mills.pdf | EX (slide text) |
| SN14 | Shao J., He A., Yang Q., Jiang L., Yao C., Zhou B., "Multi-parameter coupled subsection cooling regulation characteristics of work rolls in aluminum cold rolling", Chin. J. Eng. 37(8) (2015) 1092–1097, doi:10.13374/j.issn2095-9389.2015.08.018 (= PT-T18, TM-LA20) | http://download.cucdc.com/wenku/7e866ecc01884bf4b0beb581b59e030c.html (mirror) | FT (garbled mirror; text and tables legible, figures not) |
| SN15 | Yin F., Li M., Zhang S., "Optimum values of convection heat transfer between the working rolls and coolant fluid of mill 1400F", J. Univ. Sci. Technol. Beijing 27(4) (2005) 480–483, doi:10.13374/j.issn1001-053x.2005.04.023 (= PT-T17) | http://download.cucdc.com/wenku/207d723ccc954ba59a3ca0d5c5008d8f.html (mirror) | FT (garbled mirror; Table 1 legible) |
| SN16 | Horák A., Raudenský M., Pohanka M., Bellerová H., Reichardt T., "Research on cooling efficiencies of water, emulsions and oil", Engineering Mechanics 18(2) (2011) 81–89 (= PT-T19, EX there) | https://www.engineeringmechanics.cz/pdf/18_2_081.pdf | FT (Exa; figures not) |
| SN17 | Hnízdil M., Chabičovský M., Resl O., "Cold rolling – cooling enhancement and optimization", METAL 2024, doi:10.37904/metal.2024.4875 (steel cold mill, emulsion) | https://doi.org/10.37904/metal.2024.4875 ; https://www.confer.cz/metal/2024/4875-cold-rolling-cooling-enhancement-and-optimization | EX (long search excerpt) |
| SN18 | Lee P.-J., Choi H., Lee S.-H., "Cooling heat transfer from a rotating roll by impinging water spray jets", Trans. KSME B 26(6) (2002) 779 (= TM-LA17) | https://doi.org/10.3795/ksme-b.2002.26.6.779 | AB |
| SN19 | Barten A.E. (Achenbach), "Innovation, technological investment and cost reduction in aluminium strip and foil rolling", n.d. | https://studylib.net/doc/26154378/ (user-upload host; only the search snippet was used) | AB |
| SN20 | Bachmann electronic, application notes on Achenbach foil-mill automation ("High speed for ultrathin foils"; "Systematic") | https://www.bachmann.info/media/881/download/Applikationsbeitrag_Achenbach_EN.pdf ; https://www.bachmann.info/media/923/download/Applikationsbeitrag_Achenbach_en_06.pdf | VP (snippet) |
| SN21 | Achenbach, "OPTIMILL foil rolling mills" (web page) | https://www.achenbach.de/en/machines-equipment/optimill-rolling-mills/optimill-foil-rolling-mills/ | VP |
| SN22 | Used rolling mill machinery list (Achenbach foil mill, built 1966, revamped 1990), alcircle PDF | https://www.alcircle.com/api/uploads/downstream%20products/businesscircle/92201562521314.pdf | VP |
| SN23 | EP2376241A1, "Rolling mill temperature control" (background section) | https://patents.google.com/patent/EP2376241A1 | EX |
| SN24 | US20060254335A1, "Side supported 6-high rolling mill" | https://patents.google.com/patent/US20060254335A1/en | EX |
| SN25 | US4706480A, "Rolling mill cooling system" | https://patents.google.com/patent/US4706480A/en | EX |
| SN26 | EP0374538, "Spray system for rolling mill" (Norandal USA) | https://www.freepatentsonline.com/EP0374538.html | EX |
| SN27 | US4644774, "Apparatus for cooling a work roll ..." (Hoogovens; herringbone pattern) | https://exa.ai/library/legal/patent/z7rl4zpvn0j | AB |
| SN28 | US4932232, "Methods of detecting and correcting spray header malfunctions" (Alcan) | https://www.freepatentsonline.com/4932232.html | EX |
| SN29 | EP0138430, "Process and apparatus for strip flatness and tension measurements" | https://data.epo.org/publication-server/rest/v1.0/publication-dates/19850424/patents/EP0138430NWA2/document.html | EX |
| SN30 | Meijer O., Ballyns J., Powers R., Vignone J., Kueber P., "Aluminium hot mill work roll cooling control", IEEE IAS Annual Meeting 1989, doi:10.1109/ias.1989.96829 | https://doi.org/10.1109/ias.1989.96829 | AB |
| SN31 | Chinese utility model 201621364669, "AFC hot spray control system for aluminium foil mill strip" | https://www.xjishu.com/zhuanli/23/201621364669.html | EX |
| SN32 | (not used) | – | – |
| SN33 | Yu H., "Application of the emulsion spray system on a single-stand double-coiler hot mill for foil stock", dalilvcai.com, 26 Mar 2016 (aluminium hot, emulsion) | https://www.dalilvcai.com/teach/show-htm-itemid-1380.html | VP (trade article, read) |
| SN34 | FM Global, Property Loss Prevention Data Sheet 7-21 "Rolling Mills" | https://www.fm.com/FMAApi/data/ApprovalStandardsDownload?itemId=%7BBAA685F2-3B86-4CC6-B5D5-CA9F2A4CBFB5%7D | EX |
| SN35 | AXA XL Risk Consulting, PRC.17.1.3.1 "Aluminum rolling mills" | https://axaxl.com/prc-guidelines/-/media/axaxl/files/pdfs/prc-guidelines/prc-17/prc17131aluminumrollingmillsv1.pdf | AB |
| SN36 | Primetals Technologies, "Schneider Filter" (web page) | https://www.primetals.com/en/portfolio/solutions/hot-rolling/non-ferrous/aluminum/schneider-filter/ | VP |
| SN37 | Aakash Hydraulics, "Stack filter press – roll coolant system" | https://aakashhydraulics.com/stack-filter-press-for-roll-coolant-system/ | VP |
| SN38 | Gao S., Xi A., Liu H., Wang C., "Temperature field of hot rolling work-roll for aluminum sheet", J. Northeastern Univ. (Nat. Sci.) 36(10) (2015) 1496 | https://xuebao.neu.edu.cn/natural/article/html/2015-10-1496.htm | EX (formula images not readable) |
| SN39 | Chabičovský M. et al., "Spray cooling heat transfer above Leidenfrost temperature", Metals 10 (2020) 1270 (steel, film boiling) | https://www.mdpi.com/2075-4701/10/9/1270 | AB |
| SN40 | (not used) | – | – |
| SN41 | Chan R., "How to design a work roll cooling header", borejet.com guide, 25 Aug 2026 (vendor blog, steel-oriented, secondary) | https://borejet.com/guides/roll-cooling-flat-fan-nozzles/ | VP (secondary; not used for any number in section 3) |
| SN42 | Review "Heat transfer and water consumption of water spray cooling ...: a review on empirical correlations", Chem. Eng. Trans. 88 (2021) (continuous casting) | https://www.cetjournal.it/cet/21/88/041.pdf | EX |
| SN43 | "Cooling characteristics of an impinging spray jet which forms an ellipsoidal liquid film", Heat Transfer – Asian Research 29(4) (2000) 280 | https://onlinelibrary.wiley.com/doi/10.1002/(SICI)1523-1496(2000)29:4%3C280::AID-HTJ3%3E3.0.CO;2-Y | AB |
| SN44 | Lechler, "Precision spray nozzles" (surface technology brochure) | https://www.lechler.com/fileadmin/media/kataloge/pdfs/industrie/broschueren/EN/lechler_brochure_surfacetechnology_en.pdf | VP (snippet) |
| SN45 | PNR Italia, "Jet impact" (nozzle anatomy page) | https://www.pnr.eu/en/resources/nozzle-anatomy/jet-impact/ | VP (not used in section 3) |
| SN46 | Danieli news, "More DanPurity plate filters ..." (17 Apr 2025) | https://www.danieli.com/en/news-media/news/more-danpurity-plate-filters-for-clean-nonferrous-strip-rolling-in-operation_37_956.htm | VP |

Also used:

- The patent background "Work roll cooling apparatus and method" (kerosene cooled to about 40 °C): https://trea.com/information/work-roll-cooling-apparatus-and-method/patentgrant/a7e01df6-2807-45f8-a9ba-206ce18ba0a9 [EX].
- CN100350999C (filter-aid proportions): https://patents.google.com/patent/CN100350999C/en [EX].
- Earlier report ids: PT-T9, PT-T10, PT-T17 to PT-T22, PT-T38, TM-LA15, TM-LA17, TM-LA35.

---

## 5. Looked for and not found

- **A complete foil-mill spray specification** (barrel length, rows, nozzles per row, nozzle type number, total flow). Searched vendor sites (Achenbach, Primetals, SMS, Danieli, Lechler, EHT), Chinese patents and articles in Chinese and English, and used-mill listings. Found only partial data (SN14, SN20, SN22).
- **A measured transverse profile of a flat-fan footprint with numbers** (impact pressure or flux), for water or oil. The Lechler and Novelis figures exist but are not legible in text form. No paper with a fitted profile was found.
- **A measured HTC for kerosene or another neat rolling oil on a rotating roll, in absolute numbers.** As before (PT, TM): only relative results (SN13), a plate test (SN16) and simulations (SN14, SN15).
- **A spray HTC correlation for oil, or for water at roll temperatures of 40–100 °C, with constants.** Only high-temperature water correlations for steel were found.
- **The reduction of spray angle with oil viscosity in numbers** (stated qualitatively by SN2 and SN8).
- **Minimum valve on/off (dwell) times used by flatness controllers.** Only valve response and pulse rates were found.
- **Inductive edge heaters for aluminium foil or cold mills, with power or position.** "UniHeat Curved Hot Edge System" is named without its principle.
- **A blocked- or misaligned-nozzle band on aluminium strip or foil with measured width, height or I-units.** Searched patents, vendor papers and trade press. Mechanisms are documented in words only.
- **A standard (ISO, EN, VDI or association handbook) for rolling-mill spray header geometry or testing.** Only insurer fire data sheets were found.
- **Gao 2015 (SN38) water correlation constants.** Printed as images; not readable through the page reader.
- **Hobbis/Novelis design correlations** ("correlations developed for design of cooling systems"). Not published in the slides.
