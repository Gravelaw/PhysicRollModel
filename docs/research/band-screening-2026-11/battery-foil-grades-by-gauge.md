# Battery foil: alloy and temper by gauge

**Scope.** Follows the corrected brief: tempers, not temperatures. Section 4 is "how each temper is produced"; there is no temperature-limits table.

**Read tags.** [FT] full text read; [EX] long excerpt; [SN] abstract or snippet; [VP] vendor, reseller or trade page; "computed" = my arithmetic. G-numbers are this report's sources; S-numbers are the first survey's.

**Three findings first.**
1. No source gives a hard "gauge X → alloy Y" rule. What exists is a strength floor that rises as gauge falls; producers meet it by moving from 1085/1070/1060/1235 to Cu-bearing 1100-type or 1C30-type alloys.
2. The first survey's 8011 figure was wrong: the GB/T 33143-2022 minimum for 8011 is 180 MPa, not 220–230 [G2].
3. "H18" on battery foil is a label for a strength table. The foil gets 97–99 % cold reduction after the last anneal, far above the 75 % that defines H18, so European sources call the same product H19.

## 1. Collector foil: selection table by gauge

Rm = tensile strength, MPa. "GB min" = GB/T 33143-2022 Table 9, all H18, read from a producer page that reproduces the table [G2, VP], cross-checked against the garbled draft translation [G1, EX] and T/ZZB 2638-2022, which copies four of its rows [G3, FT]. A dash means no value is set for that band.

| Gauge band | GB min Rm by alloy | Typical Rm / Rp0.2 / A from producers | Alloy usually chosen | Typical cells | Evidence |
|---|---|---|---|---|---|
| ≤10 µm (8, 9, 10) | 1070 185; 1100 230; 1C30 220; 8011 180; 1060, 1050, 1235 — | 240–285 MPa, 2.5–3.8 % in Chinese patents [G21, EX] | 1100-type or 1C30-type; 8021 at 10 µm one-side-bright [S4] | Energy-dense EV, consumer | Minima strong; alloy preference medium |
| >10–13 µm (12, 13) | 1070 185; 1060/1050 190; 1235 180; 1100 230; 1C30 230; 8011 180 | 1060-type 180–230, A >3 %; 1100-type 230–270, A >2.5 %, or 260–310, A >1.5 % [G14, FT]; Speira high-strength ≥250 [S8] | 1100-type for EV; 1235 or 1060 where 180–190 MPa suffices | Mainstream EV and storage [G21, G23] | Minima strong; cell type medium |
| >13–15 µm (15) | 1070 180; 1060/1050 190; 1235 185; 1100 220; 1C30 225; 8011 180; 8A21 165 | At 15 µm: 1085 175–180 / 163–165 / 4–5 %; 1N30 or 1230 185–194 / 165–175 / 4.5 %; 1C32 230 / 200 / 4.5 %; A730H 290 / 250 / 4.0 %; 3003 270–275 / 240 / 3 %; KS81 274 / — / 5.4 % [G5, G6, G8, G9] | 1235, 1060, 1N30 standard; 1085 for high power; 1100-type or 3003 when ≥250 MPa is specified | EV, storage, consumer | Strong: several producers agree |
| >15–20 µm (16, 18, 20) | 1070 175; 1060/1050 185; 1235 175; 1100 220; 1C30 220; 8011 — | Same grades; 16 µm 1235 typically 200–220, A 2.2 % [G42, VP] | 1235, 1060, 1070, 1085 | Storage, LFP [G19, VP]; carbon-coated base, 16 µm most ordered [G38, VP] | Minima strong; cell type vendor-level |
| >20–30 µm | None; GB/T 33143 stops at 20 µm | 1235-H18 21–35 µm: 170–200 MPa, A ≥1.6 % [G35, VP] | 1235, 1N30, 1085, 3003 | Older and high-power Li-ion ("normally 15–30 µm", 2009 [G7]); supercapacitors 20 µm [G36, G37] | Weak |

**Notes.**
- **Your usual 17–19 µm** is in the >15–20 µm band. **12 µm** is in the >10–13 µm band: 180–190 MPa for 1235/1060, 230 MPa for 1100/1C30.
- **Your reductions (computed):** 50→18 µm in two equal passes is 40 % each (50→30→18); 50→12 µm is 51 % each (50→24.5→12).
- **Elongation minima** in GB/T 33143 are 1.0–3.0 %, depending on alloy, gauge length and one- or two-side-bright; 8A21 is ≥4.0 % [G2].
- **Conductivity, % IACS:** 1085 60–61.5; 1N30/1235 58–60; 1100 56–59.5; 8021 58–59; 3003 47–48.5 [G6, G7, G41]. Vendor figures of about 62 for 1060 [G20] do not line up with these.
- **Temper as written:** H18 in GB/T 33143, T/ZZB 2638, JIS H 4160; "H18, H19" in T/ZZB 1203, Gränges, Symetal, Armor [G4, G14, G15, G18]; "H19" at Innoval [G17].
- **Surface:** single-sheet two-side-bright is preferred [G17]. Sam-A rolls single to 10 µm and says Japanese mills double at 10 µm [G11].
- **Gauge in use:** Sam-A lists 12–20 µm in A1050, A1100, A1235 [G10]; Lotte 12 µm in 2020 with 10 µm on test [G12]; Korean EV foil 10–11 µm in 2024 [G13]; China 12–15 µm mainstream [G21].
- **Pinholes per m²** (T/ZZB 2638): ≤20 at 8–10 µm, ≤10 at 10–13, ≤5 at 13–15, 0 at 15–20 [G3].

**Other documents that set strength by gauge.**
- **T/ZZB 1203-2019, power cells, 10–16 µm** [G4, FT]: 1060/1070 H18 ≥160, H19 ≥180 MPa; 1100 H18 ≥180, H19 ≥200 MPa; A100 ≥2.0–3.0 %; thickness ±2 %.
- **JIS H 4160 (1994 text)** [G25, FT]: 1085, 1070, 1050, 1N30, 1100, 3003, 3004, 8021, 8079 in O and H18. It has no strength table.
- **Targray purchase spec, 12–15 µm** [G24, VP]: 1235-H18 and 1060-H18 ≥165 MPa, ≥1.5 %; 1235D-H18 ≥200 MPa, ≥2.0 %.

## 2. The 25–60 µm battery products

| Product | Gauge | Alloy, temper | Properties | Last pass | Evidence |
|---|---|---|---|---|---|
| Pouch-laminate barrier foil | GB/T 22648-2023: 8021 35–55, 8A21 40–50, 8079 40–55 µm [G28]. 35 µm in 88 µm laminate; 40 µm in 113 and 153 µm laminate [G30] | 8021, 8079, 8A21; O | Toyo minima: 8079 ≥75 MPa / ≥10 %; 8021 ≥85 / ≥9 % [S28]. Chinese 8021-O typical 90–110 MPa, 16–20 %, cupping 7–7.5 mm; high-formability target ≥20 %, ≥7.5 mm [G32]. Vendor, 25–45 µm: 80–100 MPa, ≥12 % [G31] | Rolled hard, then fully annealed; one-side-bright unless ordered otherwise [G28] | Alloy, temper, gauge strong; values medium |
| Tab foil and strip | 30–100 µm [G34]; 80–400 µm leads [S41] | 1070 (consumer), 1235 (power); values imply O | 85–110 MPa, ≥25–30 % | Annealed after rolling (inferred) | Weak: one vendor |
| Thick collector foil | 20–35 µm; up to 50 µm in one spec [G24, G35] | 1235, 1N30, 1085, 3003; H18 | 170–200 MPa, ≥1.6 % | Supplied hard | Weak |
| Carbon-coated base | 9–30 µm, mostly 12–16 µm [G38] | 1070, 1060, 1235; H18 | ≥140–180 MPa | Supplied hard | Vendor only |
| Case, lid, busbar, cooling plate | ≥0.3 mm | 3003, 1050 | — | Not foil [G17] | Medium |

Symetal (35–40 µm) and Innoval (40–50 µm) confirm 8021-O for pouch foil [G15, G17]. A ≥26 µm aluminium layer already gives near-zero water and oxygen transmission [G33]; the extra gauge is for drawing depth.

## 3. Why alloy and temper change with gauge

1. **Constant line force.** "Thinning alone gives insufficient strength per unit width and foil breaks on the coating line", so strength must rise as gauge falls [G6]. One broker report puts numbers on it: 20 µm ≥170 MPa, 13 µm ≥190 MPa [G22, EX].
2. **The floor keeps rising.** 1070 minimum 150 MPa (GB 2016) → 160 (2019 group standard) → 185 (GB 2022); 1100 170 → 180 → 230 [G21, read from a flattened chart]. The ≤10 µm band first appeared in 2022.
3. **Calendering.** Higher compaction breaks strip, so buyers raise strength and elongation together: ≥200 MPa is common, some ask ≥270; a conventional route gives 200–230 MPa at 3.4–3.9 % [G21].
4. **Conductivity against strength.** 3003 costs 11–13 points of IACS, so producers strengthen 1xxx instead [G6]. In 2009: 1085 for automotive high-power cells; 1N30 general; 1100, 3003, 8021 for consumer lines run at high productivity [G7].
5. **Observed shift.** Sam-A's A1100 (10–17 µm) rose from 4.6 % of sales in 2012 to 73 % in 2020 as demand moved from ≥15 µm to ≤12 µm [G11].
6. **Strength after drying.** Drying softens hard foil, purer foil most [G7]; one patent requires ≥230 MPa as rolled and ≥210 MPa after drying [G26].
7. **Rollability and stability.** 2xxx, 5xxx, 6xxx, 7xxx are "extremely difficult to roll to foil"; 1xxx, 3003, 8021 all passivate in LiPF6 [G41]. Cu above 0.2 % caused foil-rolling breaks [G26].
8. **Sodium-ion.** Aluminium on both electrodes: 800–900 t/GWh against 350–400 (NMC) and 450–550 (LFP) [G21]; 12–15 µm conventional, 8–10 µm thin [G39, VP].

## 4. How each temper is produced

| Temper | Definition | How battery foil reaches it |
|---|---|---|
| H18 | Strength of about 75 % cold reduction after full anneal [G40] | Last anneal at 0.5–2.5 mm, or none after hot rolling; none in the foil mill [G8, G26, S8, S18]. Computed: 0.5 mm → 15 µm is 97 % (strain 3.5); 1 mm → 12 µm is 98.8 % (strain 4.4) |
| H19 | Minimum Rm ≥10 MPa (2 ksi) above H18 [G40] | Same route, more strain or solute. T/ZZB 1203 puts H19 20 MPa above H18 [G4] |
| High-strength grades | Sold as H18 or H19 | Cu 0.05–0.2 % (1100, 1C30); Fe and Mn held in solution by hot homogenising and no intermediate anneal [G26]; starting cold rolling at ≥1 mm so strain reaches 4–5 instead of about 3, which raised strength and elongation together [G8] |
| H2x | Strain hardened, then partially annealed [G40] | Not used in any public collector-foil specification |
| O | Fully annealed | Pouch foil: rolled hard, then coil-annealed 240–260 °C for 40–45 h [S32, S33]; the anneal also removes rolling oil [G44] |

**Loss of temper on heating.** Rm as rolled → 100 °C × 24 h → 150 °C × 3 h → 200 °C × 15 min [G26, Table 3; the composition and process tables were not in my excerpt]:
- Invention alloy, no intermediate anneal: 252 → 258 → 261 → 227 MPa (computed loss 10 %).
- Comparison alloy at 59.1 % IACS: 266 → 258 → 221 → 194 MPa (27 %).
- Nine comparison process routes: 216–245 → 199–233 → 182–209 → 155–188 MPa (23–28 %).

A 99.85 % Al grade is specified at ≥175 MPa as rolled and ≥170 MPa after 100–160 °C [G27].

## 5. Disagreements

1. **8011 minimum:** 180 MPa [G2] against 220–230 in the first survey.
2. **H18 or H19:** Asian standards say H18; European producers say H18/H19 or H19 for the same product.
3. **Group standard below national:** T/ZZB 1203-2019 (160–200 MPa) is lower than GB/T 33143-2022 (175–230 MPa), even in its H19 column.
4. **1060 strength:** GB minimum 185–190; Gränges 180–230; a trade article claims 230–250 [G20].
5. **"Mainstream" alloy:** 1060 and 1235 in Chinese sources [G20, G22]; 1100 at Sam-A [G11]; 1085, 1N30, 3003 in Japan [G7].
6. **Gauge by cell type:** vendor pages put 1070 at 10–12 µm for consumer cells and 1060 at 15–20 µm for storage, with no data [G19].
7. **Soft collector foil:** some reseller pages list O temper. No standard or producer datasheet supports it; I treat it as an error.
8. **Cu in 1100:** one trade article warns of micro-galvanic corrosion [G20]; I found no measurement.

## 6. Not found

- GB/T 22648-2023 Tables 5–9 (pouch-foil strength, cupping, pinholes by gauge); every mirror drops them. T/ZZB 2076-2021 is known only from a reseller summary: ≥70–85 MPa, cupping ≥5.5–7.0 mm [G29].
- An official copy of GB/T 33143-2022 Table 9. The draft translation's host is outside this session's allowed network domains for direct download.
- Any cell-maker purchase specification, and any LFP-against-NMC rule for gauge or alloy.
- Datasheets with numbers from Lotte, Dong-IL, Dongwon, Novelis, Hydro, Constellium, Hindalco, Assan, Dingsheng, Nanshan, Wanshun, Yong Jie, Xiashun, Shenhuo. Speira's page gives gauge only (12–20 µm) [G16].
- JIS H 4160:2006 itself; the mirror carries the 1994 text.
- Recrystallisation temperature by alloy for hard foil. Furukawa-Sky plots it but values are not extractable [G7, Fig. 8]; one vendor page says 1235-H18 softens fast above 220 °C [G43].
- Any standard for thick collector foil or tab foil.

## 7. Sources

- G1 GB/T 33143-2022 draft English translation [EX]: http://www.cnsmq.com/uploadfile/2025/0227/20250227042900196.pdf
- G2 Chalco page reproducing GB/T 33143-2022 Tables 1, 2, 9 [VP]: https://www.chalcoaluminum.com/knowledge/lithium-ion-battery-foil/
- G3 T/ZZB 2638-2022 [FT]: https://www.ttbz.org.cn/Home/PdfFileStreamGet/c3QsNTk5MjU(eq)
- G4 T/ZZB 1203-2019 [FT]: https://qxb-img-osscache.qixin.com/standards/e7007ea8cb458ac1eb6e98d305058bfd.pdf
- G5 UACJ Foil battery foil page, Japanese [VP]: https://ufo.uacj-group.com/techno/rd/battery.html
- G6 Motoi et al., UACJ Technical Reports 1 (2014) 125 [EX]: https://www.uacj.co.jp/development/rd/review/vol1no1/pdf/vol1no1_18.pdf
- G7 Ashizawa, Yamamoto, Furukawa-Sky Review 5 (2009) 1 [FT]: https://www.uacj.co.jp/development/rd/review/furukawasky/005/pdf/05_abst01.pdf
- G8 Ihara et al., Kobe Steel Engineering Reports 65(2) (2015) 29 [FT]: https://www.kobelco.co.jp/r-d/technology-review/dumm/__icsFiles/afieldfile/2025/03/19/235_029-032.pdf
- G9 Kohan Shoji high-strength collector foil [VP]: https://battery-jp.net/strong_positive_electrode.html
- G10 Sam-A product page [VP]: https://sama-al.com/kor/business/foil/car
- G11 ETNews, Sam-A talk, 2021-04-28 [FT, trade press]: https://www.etnews.com/20210428000130
- G12 Newspim, Lotte Aluminium, 2020-09-16 [EX]: https://www.newspim.com/news/view/20200916000922
- G13 Asia Economy, 2024-03-02 [EX]: https://www.asiae.co.kr/article/2024022716372407494
- G14 Gränges cathode foil datasheet 2024 [FT]: https://www.granges.com/globalassets/09.-kampanjer/06.-battery-cathode-foil/03.-contact/granges-datablad_cathode-foil_2024.pdf
- G15 Symetal battery foil [VP]: https://www.symetal.gr/en/battery-foil
- G16 Speira battery foil [VP]: https://www.speira.com/markets-products/battery-systems/battery-foil/
- G17 Innoval Technology, "Aluminium battery foil", 2023 [EX]: https://www.innovaltec.com/www-innovaltec-com-insights-aluminium_battery_foil/
- G18 Armor primed foil [VP]: https://www.armorbatteryfilms.com/our-products/primed-aluminium-foil/
- G19 Mingtai and Haomei alloy-by-gauge pages [VP]: https://www.mt5083lb.com/knowledge/585.html ; https://www.aluminum-hm.com/application/battery-aluminum-foil/
- G20 OFweek, 1060 against 1100 [VP]: https://libattery.ofweek.com/2025-06/ART-36000-8110-30665024.html
- G21 Orient Securities, battery foil report, 2023-02 [EX]: https://pdf.dfcfw.com/pdf/H3_AP202302131583078254_1.pdf
- G22 Huaxin Securities, 2022-12 [EX]: https://pdf.dfcfw.com/pdf/H3_AP202212191581210899_1.pdf
- G23 LeadLeo, Li-ion battery foil, 2023 [EX]: https://pdf.dfcfw.com/pdf/H3_AP202303271584589758_1.pdf
- G24 Targray cathode foil spec [VP]: https://www.targray.com/li-ion-battery/cathode-materials/foils
- G25 JIS H 4160, 1994 text [FT]: https://jis.eomec.com/jish41601994
- G26 UACJ US 9,698,426 B2 [EX, with Table 3]: https://exa.ai/library/legal/patent/z7mfjkqz2bs
- G27 UACJ CN application 201380010002 [EX]: https://www.xjishu.com/zhuanli/24/201380010002.html
- G28 GB/T 22648-2023 mirrors [EX]: https://www.duodown.com/biaozhun/2155908.html ; https://www.guifanku.com/784986.html
- G29 T/ZZB 2076-2021 reseller summary [VP]: https://kpt-bj.com/t-zzb-2076-2021-aluminum-foil-for-aluminum-laminate-film-of-pouch-cell-1302142151.html
- G30 Laminate structures [VP, EX]: https://www.libmachine.cn/?products_66%2F372.html= ; https://xiaoweitop.com/zh-CN/equipments/aluminum-laminated-film-for-pouch-cell-case-t-113um/ ; http://www.taiwanbattery.org.tw/media/file/admin/20230901094346tBWI.pdf
- G31 HDM battery foil [VP]: https://hdmetalm.com/battery-aluminum-foil/
- G32 8021 pouch-foil stock patent [EX]: https://www.xjishu.com/zhuanli/24/202511388492.html
- G33 He et al., Material Sciences 12 (2022) 123 [EX]: https://pdf.hanspub.org/ms20220200000_28186169.pdf
- G34 Mingtai tab foil [VP]: https://www.mt6061lb.com/lvbannews/1102.html ; https://www.mt6061lb.com/lvbannews/1103.html
- G35 MC Aluminum [VP]: https://www.alummc-foil.com/product/battery-aluminum-foil.html
- G36 Supercapacitor electrode and etched foil [VP]: https://www.ssntm.com/product/dry-coating-electrode-edlc-eletrode-tape/ ; https://www.sciencegears.com.au/eal-foil-etched-aluminum-foil
- G37 Xia et al., Electronic Components and Materials 2025(11) [SN]: http://www.qikanvip.com/qkml/141553.html
- G38 HSMetal carbon-coated foil [VP]: https://www.lyhsmetal.com/lithium-battery-materials/double-side-carbon-coated-aluminium-foil.html
- G39 Sodium-ion foil gauges [VP, EX]: http://www.newsijie.com/chanye/dianzidianqi/jujiao/2026/0608/11366463.html ; https://www.xjishu.com/zhuanli/59/202511576733.html
- G40 Temper definitions [EX, VP]: https://www.totalmateria.com/en-us/articles/work-hardening-aluminum-alloys-1/ ; https://unitedaluminum.com/aluminum-technical-data-alloy-chemistry-and-mechanical/ ; https://www.chalcoaluminum.com/blog/temper-aluminum-alloys/
- G41 Saito, Tanaka, UACJ Technical Reports 9 (2022) 63 [FT]: https://www.uacj.co.jp/development/rd/review/vol9no1/pdf/vol9no1_11.pdf
- G42 Lab-supply battery foil page, 16 µm 1235 [VP]: http://www.scimaterials.cn/ProDetail.aspx?ProId=1797
- G43 1235 foil vendor note [VP]: https://www.cnal.com/product/39026221.shtml
- G44 Matsuoka, Higashi, J. JILM 67 (2017) 641 [EX]: https://www.jstage.jst.go.jp/article/jilm/67/12/67_671206/_pdf
- First-survey sources reused: S4 UACJ/Nagase datasheet; S8 Speira US11495801; S18 JP5927614B2; S28 Toyo TY-X2; S32, S33 8021 pouch-foil patents; S41 Sumitomo tab lead.
