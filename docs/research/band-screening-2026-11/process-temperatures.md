# Process temperatures in aluminium foil rolling: strip, oil, rolls, and their effects

Web research only; no repository file was touched. It adds to the three earlier surveys and does not repeat them.

**Read tags.** [FT] full text; [EX] long excerpt from the search tool, not the whole document; [AB] abstract or snippet; [VP] vendor or trade page. "Computed" is my own arithmetic. No finding rests on memory; computed rows use textbook constants for steel and aluminium.

**Four findings first.**
1. Battery foil has a published coil-temperature limit: ≤80 °C on the final pass; above 90 °C elongation decays with time [T1, T2].
2. The only measured heat partition for a foil mill gives 67–89 % of the heat to the rolls and 11–33 % to the strip [T16, AB]. Your model's demo uses a strip share of 0.84. I read only the abstract; it is a net balance, so it need not equal the split inside the bite.
3. No measured spray coefficient for kerosene on a rotating work roll was found. The nearest are a simulated 2.5–4.3 kW/m²K on an aluminium cold mill [T18] and a measured "3–6 times below water" on a sprayed plate [T19].
4. No source puts numbers on a blocked-nozzle band on foil. The mechanism is documented only in words [T22, T23, T35].

## 1. Temperature map of a foil mill

| Temperature | Typical range | Limit | Reason given | Source |
|---|---|---|---|---|
| Coil entering a pass | Not stated for foil; 60–100 °C entry gave exit above 150 °C at sheet gauge | ≤75 °C before the battery-foil final pass (≥10 h natural cooling) | Keeps the final-pass coil below 80 °C | T1, T3 [EX] |
| Strip inside the bite | Calculated to reach about 200 °C at high speed | Above 200 °C needed before softening shows | "Almost adiabatic" above about 2000 m/min roll speed | T4 [EX] |
| Coil off the final pass, battery foil 20→13 µm, 35 %, oil 42 °C | 77.2 °C at 550 m/min; 97.9 and 99.7 °C at 600 m/min; prior art "above 90 °C" | ≤80 °C (≤90 °C at the least), also when slit within 30 min | Recovery and possible solute clustering: strength and elongation fall for weeks | T1, T2 [EX] |
| Coil leaving a cold-mill pass (sheet gauge) | "About 121 °C"; cold rolling defined as below 129 °C; metal at 20–200 °C | No stated limit; trouble above 150–160 °C | Erichsen value of 8150 fin stock fell over 10 % above 160 °C; coarse grains after anneal | T14 [EX], T13 [FT], T37 [EX], T3 [EX] |
| Oil supply, roughing and intermediate | 30–40 °C and 40–50 °C | — | Thick stock, more heat to remove | T5, T6 [EX] |
| Oil supply, finishing | 50–60 °C general foil; 40–45 °C battery foil | Window 38–55 °C at one plant; legal cap 68 °C (cold mill), 71 °C (foil mills) in one US rule | Thin film for lustre; lower bound set by the "ladder" tear defect; cap is for vapour emissions | T5, T6, T1, T3 [EX], T13 [FT] |
| Hot edge spray | Oil up to 120 °C in 25 mm zones | — | Expands the roll at the strip edge against tight edges and breaks | T21 [VP], T5 |
| Work-roll surface and bulk | Not found measured; a cold-mill model uses 50 °C surface with 35 °C oil | Thermal load 40–50 kcal/m²s of roll surface (167–209 kW/m², computed) | Above it the thermal balance is unstable; herringbone | T18 [FT], T4 [EX] |

**Temperature rise per pass.**
- Coil temperature rises with speed [T15, VP]. The one number pair is 77 °C at 550 m/min against 98–100 °C at 600 m/min, but the cooler case also had a pre-cooled coil and finer rolls [T1]. Entry temperature of the hot case is not given.
- Computed: plastic work alone (200 MPa flow stress, plane strain) heats the strip 41 K for 20→13 µm and 48 K for 50→30 or 30→18 µm if no heat leaves; friction adds. A 77 °C coil from a ≤75 °C entry suggests most of that heat left the strip (my inference; coil and strip temperature are not the same measurement).

**Cooling between passes.** ≥10 h natural cooling [T1]; 24 h rest in the earlier survey's Speira patent.

**Rolling oil.**

| Property | Value | Source |
|---|---|---|
| Viscosity at 40 °C | 1.50–1.75 cSt (Somentor 29); 1.8 and 2.0 (grades 80, 110); 1.5–2.0 (electronic foil); 1.8–2.0 in use at one plant | T9 [FT], T10 [VP], T8 [EX], T3 |
| Flash point | ≥74 °C (Somentor 29); 105–110 °C open cup (grades 80, 110); 80–111 °C for additive concentrates | T9, T10, T11 [VP] |
| Boiling range | 192–248 °C; 204–240 °C; 210–250 and 240–280 °C | T9, T8, T10 |
| Viscosity against temperature | 2.16–2.3 cSt at 25 °C, 1.64–1.68 at 40 °C for a comparable fluid: about −1.7 % per K (computed) | T12 [AB] |
| Flow | Not found for foil mills. A cold-mill example: 3, 6 and 12 L/min per nozzle in three rows, about 400 L/min per metre per header at 52 mm pitch (computed) | T20 [FT] |

**What goes wrong.**
- **Oil too hot (thin film):** film ruptures, dry contact, light-and-dark marks [T8]; more aluminium fines [T15]; herringbone when load and temperature run away [T4, T28 AB].
- **Oil too cold or viscous (thick film):** lower speed, more oil carried out, yellow-brown stain after anneal [T8]; ladder defect below 38 °C (my reading of "min 38 °C for ladder") [T3].
- **Gauge:** a thicker film gives thinner foil in closed-gap rolling (speed effect) [T4].
- **Fire:** chance rises sharply once strip reaches the flash point [T15]; ignition comes from strip breaks, static, hot bearings and electrics [T14].

## 2. Temperature and material properties

| Item | Finding | Source |
|---|---|---|
| Battery foil 1060 (also 1235, 1100), 13 µm | Strength and elongation tracked for days after rolling at coil temperatures 80–110 °C. Hotter coils lose more; elongation drops at ≥90 °C, by over 20 % at worst. A 98 °C coil decays for over 60 days; ≤80 °C coils settle in 16–20 days | T1, T2 [EX; figures not seen] |
| 1100-H18, tested hot after holding up to 10 000 h | 165/150 MPa (tensile/yield) at room temperature [T39]; 145/130 at 100 °C; 125 at 150 °C; 40 at 205 °C | T31 [AB], T39 [EX] |
| 99.5 % Al | Flow stress at 200 °C about 35 % below room temperature; hardness after deforming at 200 °C only 10 % lower | T4 [EX] |
| Recovery of 1050 rolled 99.6 % | Measured at 140–220 °C from 1 min; activation energy 131 rising to 186 kJ/mol | T32 [EX] |
| Strain-rate sensitivity, 1050 | m about 0.04 at 100 °C and 0.07 at 200 °C (H14, slow tensile tests); taken as zero for cold deformation | T33 [EX], T7 [AB] |
| 8021 pouch foil | Controlling coil and oil temperature avoids work softening during foil rolling | T36 [AB] |
| Additive film | Kerosene with 2.2 % fatty acid failed at 150–155 °C in ball-on-disc tests; 0.022 % acid held to 250 °C | T27 [EX] |

**Across the width.** A transverse strip temperature gradient goes unnoticed while rolling and changes shape as the coil cools [T23, EX]. No source reports strength or thickness bands from this cause.

## 3. Temperature and roll wear / roll surface

- **Roll coating.** Fresh aluminium sticks to the roll and is re-deposited; the additive limits this layer [T37, EX]. Physically adsorbed films desorb as temperature rises [T15, T27].
- **Fines.** More fines with higher oil temperature, speed, reduction and roll roughness [T15].
- **Circumferential temperature swing.** Keeping it small reduces thermal fatigue, surface degradation and wear [T23]; a general cold-mill statement, nothing foil-specific on spalling.
- **Bending.** Edge heating lowers the bending force and therefore work-roll wear [T24, VP].
- **Roll hardness.** 115–125 HSD rolls held shape on ≥250 MPa foil; 98 HSD rolls drifted after 1–3 h [T29].
- **Roll change and regrind interval for foil finishing rolls:** not found.

## 4. Temperature and surface finish

| Defect or property | Thermal cause | Magnitude given | Source |
|---|---|---|---|
| Heat stripes (EAFA) | Temperature or flatness difference across the width; locally overheated roll | None | T35 [from the earlier survey, not re-read] |
| Stripes on strip | Gaps between spray footprints leave under-cooled roll bands. Overlap should be 10–30 %, never above 50 % | Zone pitch 25–100 mm | T22 [EX], T21 |
| Surface striping; local buckle | Blocked filter or header gives differential oil plate-out and cooling. After a spray is turned down the roll first expands in a narrow band, which grows until a wave appears | None | T23 [EX] |
| Rib (quarter) looseness after roughing | Roll hotter at 1/5–1/4 of the barrel. Nozzles of twice the diameter there removed it | None | T38 [FT] |
| Herringbone | Thermal runaway at the film-strength limit | Thermal load above 167–209 kW/m² | T4, T28 |
| Wettability (dyne) | Set mainly by oil carried out. Additive at 3.5 % gave 29–30 dyn, at 8 % gave 28 dyn. Dyne can start above 32 and fall below 30 within 12–24 h as base oil evaporates | 1–2 dyn | T29, T30 [EX] |

No source links oil, roll or strip temperature directly to dyne level, gloss bands or white streaks.

## 5. Numbers for simulation

| Quantity | Value | Basis | Source |
|---|---|---|---|
| Heat partition, foil mill | Strip 0.11–0.33, rolls 0.67–0.89; roll share rises with cooling | Measured strip surface temperature, three nozzle states | T16 [AB] |
| Spray coefficient, kerosene on work roll | 3.0 rising to 4.0 kW/m²K in the jet zone at 500 kPa; 2.5–4.3 over 200–700 kPa | Simulated, 1800 mm cold mill, 34 nozzles at 52 mm, roll 50 °C. Viscosity ranks first among spray factors [T17, AB] | T18 [FT] |
| Oil against water spray | Oil 3–6 times lower at equal impingement density | Measured on a steel plate, full-cone nozzle | T19 [EX] |
| Same, absolute | Water about 31–38 kW/m²K at 5 bar, so oil about 5–13 kW/m²K | Computed from two statements in T19; plate at 25–250 °C, not a roll | T19 |
| Thermal crown, foil mill | 30 µm maximum, "from measured values"; 260 × 900 mm work roll | — | T25 [EX] |
| Zone-cooling authority | ±3.6 to ±4.2 µm on diameter 20 revolutions after a change; grows linearly with rolled length; halves from 100 to 300 m/min | Simulated, 1100 alloy | T18 |
| Bite contact conductance | 25–40 kW/m²K in aluminium models; measurements span 7–800 | Literature review | T34 [EX] |
| Radial time constant, 260 mm roll | About 4–7 min | Computed: steel diffusivity 1.2e-5 m²/s, Biot 3–9 | — |
| Axial decay of a 52 mm stripe | About 20 s | Computed for a 104 mm wavelength | — |
| Free expansion | 3.0 µm on diameter per K for a 260 mm roll | Computed | — |

## 6. Disagreements

1. **Heat partition.** 67–89 % to the rolls, from measured strip surface temperature [T16], against "almost adiabatic" strip heating to about 200 °C inside the bite at high speed [T4]. Both can hold if the strip gives heat back to roll and oil before coiling. Gauge and speed in T16 are not in the abstract.
2. **Finishing oil temperature.** 50–60 °C in general foil texts [T5]; 40–45 °C for battery foil [T1, T6]; 38–55 °C at one plant [T3].
3. **Spray coefficient.** 2.5–4.3 kW/m²K simulated [T18]; 4.65–5.5 overall in a cold-mill model example, coolant not named [T20, FT]; 5–13 back-computed from a plate test [T19].
4. **Hot-spray temperature.** Up to 120 °C [T21] is above the flash point of some base oils (74–110 °C) [T9, T10].

## 7. Not found

- Measured work-roll surface or bulk temperatures on a foil mill.
- A quantified blocked-nozzle case on foil (temperature difference, diameter change, I-units, band width).
- Plant-identified time constants; Davies et al. describe three but only the abstract was reachable [T26, AB].
- A curve of strip temperature rise against reduction, speed and gauge; micrometres of gauge per kelvin of oil; oil-film thickness against temperature.
- Oil flow per metre of barrel on a foil mill; roll-change and regrind intervals for finishing rolls.
- A direct measurement of temperature against dyne, gloss or roll wear; property or thickness bands traced to a width-wise temperature difference.
- Full texts on hosts outside this session's allowed network domains: cje.ustb.edu.cn (heat-partition paper), eprints.bournemouth.ac.uk (Collins thesis, measured thermal cambers), opus.lib.uts.edu.au (Mansell thesis), www.engineeringmechanics.cz, www.alufoil.org, aluminium-guide.com. Allowing the first three would close the largest gaps.

## 8. Sources

- T1 CN112934967B, battery foil and processing method [EX]: https://patents.google.com/patent/CN112934967B/zh
- T2 CN application 202110122451, same applicant, slitting variant [EX]: https://www.xjishu.com/zhuanli/23/202110122451.html
- T3 Mansell, PhD thesis, UTS 2007, part 2 [EX]: https://opus.lib.uts.edu.au/bitstream/10453/44028/13/02Whole%20part%202.pdf
- T4 Kerth, Amann, Raber, Weber, Int. Metall. Rev. 20 (1975) 185 [EX, from the text copy saved by the earlier survey]: https://www.scribd.com/document/949516974/kerth1975
- T5 Li, Yang, Huang, "铝箔轧制工艺影响因素研究", 2019 [EX]: https://www.zzqklm.com/w/kjlw/24793.html ; same oil temperatures at https://bbs.plcjs.com/thread-601856-1-1.html
- T6 Three-pass battery foil patent, Jiangyin Xinren [EX]: https://www.xjishu.com/zhuanli/23/202311439469.html
- T7 Bátorfi, Pál, Chakravarty, Sidor, Appl. Sci. 13 (2023) 4359 [AB]: https://www.mdpi.com/2076-3417/13/7/4359
- T8 Chen Jiuxia, "电子铝箔轧制过程中轧制油的控制", Metal World 2008(2) [EX]: https://metalworld.ustb.edu.cn/cn/article/pdf/preview/JSSJ200802016.pdf
- T9 ExxonMobil Somentor 29 sales specification [FT]: https://www.exxonmobilchemical.com/en/chemicals/webapi/dps/v1/datasheets/130000107309/1/en
- T10 Eastto aluminium rolling oils 80 and 110 [VP]: https://www.eastopet.com/Aluminium_Rolling_Oil/ALUMINIUM_ROLLING_OILS.pdf
- T11 Mobil Wyrol additive concentrates [VP]: https://www.mobil.com/en/sap/our-products/product-series/wyrol
- T12 Exxsol D80 safety data sheets [AB]: https://nextsds.com/sds/en/281331501287376/exxsol-d80-fluid ; https://pure-chemical.com/site/others/msds/Exxsol%20D80.pdf
- T13 Missouri rule 10 CSR 10-5.451, aluminium foil rolling [FT]: https://www.epa.gov/sites/default/files/2017-09/documents/10-5451_0.pdf
- T14 AXA XL PRC.17.13.1, Aluminum Rolling Mills [EX]: https://axaxl.com/prc-guidelines/-/media/axaxl/files/pdfs/prc-guidelines/prc-17/prc17131aluminumrollingmillsv1.pdf
- T15 "铝箔轧制与润滑技术", presentation text [VP]: https://alfoilworld.com/knowledge/knowledge-2d1c71f1/?lang=zh
- T16 Yin, Li, Zhang, Li, J. Univ. Sci. Technol. Beijing 25(6) 2003 [AB]: https://cje.ustb.edu.cn/article/doi/10.13374/j.issn1001-053x.2003.06.020
- T17 Yin, Li, Zhang, same journal 27(4) 2005 [AB]: https://cje.ustb.edu.cn/article/doi/10.13374/j.issn1001-053x.2005.04.023
- T18 Shao, He, Yang et al., Chin. J. Eng. 37(8) 2015, 1092 [FT, garbled mirror]: http://download.cucdc.com/wenku/7e866ecc01884bf4b0beb581b59e030c.html
- T19 Horák, Raudenský, Pohanka et al., Engineering Mechanics 18 (2011) 81 [EX]: https://www.engineeringmechanics.cz/pdf/18_2_081.pdf
- T20 Innoval, "Optimising spray cooling", 2016 [FT]: https://www.innovaltec.com/optimising-spray-cooling-blog/
- T21 Lechler SELECTOSPRAY brochure and product page [VP]: https://www.lechlerusa.com/fileadmin/media-usa/Literature/Brochures/metal/Roll_Cooling_SELECTOSPRAY_brochure.pdf ; https://www.lechlerusa.com/en/products/product-by-market/metals/nozzles-for-roll-cooling/selectospray
- T22 Tucker (Lechler), "Flatness and profile: problems in the design of the spray actuators", 2006 [EX]: https://www.lechler.com/fileadmin/media/fachberichte/metallurgy/lechler_fachbericht_walzenkuehlung_01-2006_flatness-and-profile-the-problems-that-can-exist-in-the-design-of-the-spray-actuators_dtucker_en.pdf
- T23 Lloyd (Lechler), "Fundamentals of roll cooling and control of flatness at primary cold reduction", 2010 [EX]: https://www.lechler.com/fileadmin/media/fachberichte/metallurgy/lechler_fachbericht_walzenkuehlung_09-2010_fundamentals-of-roll-cooling-and-control-of-flatness-at-primary-cold-reduction_dlloyd_en.pdf
- T24 Primetals hot edge induction heating [VP]: https://www.primetals.com/en/portfolio/solutions/cold-rolling/non-ferrous/aluminum/hot-edge-induction-heating/
- T25 Liu, Wu, He, Yang, Chen, J. Univ. Sci. Technol. Beijing 27(1) 2005 [EX]: http://download.cucdc.com.cn/wenku/e4745e5b77164f1b8568a4905130a323.html
- T26 Davies, Sivilotti, Tulett, Metals Technology 2 (1975) [AB]: https://doi.org/10.1179/030716975803277735
- T27 Li Fang, "Study of Additive for Aluminum Cold Rolling Lubrication", thesis [EX]: https://www.collectionscanada.gc.ca/obj/thesescanada/vol2/OWA/TC-OWA-5135.pdf
- T28 Reich, Wise, Colbert, Tribology Transactions 2008 [AB]: https://doi.org/10.1080/10402000801911796
- T29 CN111438187A, high-hardness rolls for battery foil [EX]: https://patents.google.com/patent/CN111438187A/zh
- T30 CN application 202310021340, raising wetting tension of battery foil [EX]: https://www.xjishu.com/zhuanli/23/202310021340.html
- T31 Matmatch, AA 1100-H18 [AB]: https://matmatch.com/materials/mitf51-aa-1100-h18
- T32 Recovery kinetics in AA1050 deformed to ultrahigh strain, DTU postprint [EX]: https://backend.orbit.dtu.dk/ws/portalfiles/portal/125728953/postprint.pdf
- T33 Allazadeh, strain-rate sensitivity of AA1050, 2020 [EX]: https://strathprints.strath.ac.uk/74717/1/Allazadeh_ISSJ_2020_Computing_strain_rate_sensitivity_of_aluminium_alloy_1050.pdf
- T34 Wu, Liang, Tang, Pan, Appl. Therm. Eng. 106 (2016) 1002 [EX, introduction]: https://www.sciencedirect.com/science/article/abs/pii/S1359431116309929
- T35 EAFA surface characteristics catalogue [not re-read; source S7 of `products-packaging-foil.md`]: https://www.alufoil.org/surface-characteristics
- T36 Fu, Zhang, Liao, Jiang, Heat Treatment of Metals 50(9) 2025, 181 [AB]: http://www.jsrcl.net/CN/10.13251/j.issn.0254-6051.2025.09.029
- T37 "Milling Over Rolling Oils", Lubes'n'Greases 2017 [EX]: https://www.lubesngreases.com/magazine/23_9/milling-over-rolling-oils/
- T38 CN202803755U, coolant spray device for a foil roughing mill [FT]: https://www.xjishu.com/zhuanli/23/201220412752.html
- T39 Toei Denka, table of typical mechanical properties of aluminium alloys [EX]: https://toeidenka.co.jp/refer/mechanical_strength_of_aluminum.html
