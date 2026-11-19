# Open datasets, open-source codes and published benchmark data for thin-gauge aluminium cold rolling

Survey date: 2026-11-18. Scope: evidence that could validate, calibrate or extend `physicroll`
(slab bite, foil mattress bite, tribology and pass heating, roll thermal, strip shape and
buckling, coil ridge and troughs, chatter, AGC and drive, product catalogue).

## 0. How to read this report

**Headline.** There is no public dataset of an aluminium foil mill, and no public dataset from
any mill that holds shapemeter channels, roll temperatures or coolant zone states. Two real
aluminium/cold-mill process datasets exist (items D1, D2), both stripped of the context
(gauge, alloy, units) that a physics model needs. The best documented open benchmarks for
the roll bite are on steel (pilot-mill work at Liège / ArcelorMittal). For most of the
newer `physicroll` modules, plant data are the only route.

**Read status** (never upgraded):

| Tag | Meaning |
|---|---|
| FT | full text read |
| EX | excerpt of the page or paper read (search-engine extract or part of the file) |
| AB | abstract only |
| SN | search-result snippet only |
| LP | landing page or repository API metadata only (title, licence, file list, description) |
| MEM | from memory, not verified in this session |

**Access limits in this session.** `doi.org`, `ieee-dataport.org`, `www.repository.cam.ac.uk`
and `vtechworks.lib.vt.edu` did not resolve from the fetch tool; those pages were read as
search-engine extracts (EX / AB). The GitHub API was closed for third-party repositories;
READMEs and LICENSE files were read from `raw.githubusercontent.com`. Kaggle landing pages
were only partly readable. Nothing large was downloaded: for D1 only the first 3 kB of the
CSV were read to see the header.

**Already used by the project (not reported as new):** Shao et al. 2015 (AA5052 three passes),
Hulamin 5052 data sheet, Erfanian et al. 2024/2025, Flanagan et al. arXiv 2408.03242 (the
paper), Li/Matsumoto/Utsunomiya 2018, Mišović 2016, Abdelkhalek 2011, Metals 15(1) 11,
the Don-Chris roughness dataset (DC04/DC05), PyRolL core, CalculiX, Kratos, NVIDIA Kit CAE,
Sutcliffe & Montmitonnet 2001, Le & Sutcliffe, Tabary et al. 1996 (abstract), Fleck & Johnson
1987, the MISG foil report, Niroomand 2012/2015, Hu/Zhao/Ehmann 2006, Heidari 2014, Kimura
2003, Dohmae & Okamura 2012, Davies et al. 1975 (abstract), Yin et al. 2003 (abstract),
Horák et al. 2011, Lechler papers, Good/Beisel/Yurtcu 2009, EN 546, EN 485, EN 12258-1,
ASTM B479 / B926 / B373, GB/T 3198, GB/T 33143, GB/T 22638, GB/T 22648, JIS H 4160, QCA-1.
Where one of these could be used *more* than it is today, section 2 says so.

---

## 1. Open datasets

### 1.1 Rolling process data (real measurements)

| ID | Name and URL | Licence | Size | What is in it | Material, gauge | Sampling | Read |
|---|---|---|---|---|---|---|---|
| **D1** | **D4ASCR: Dataset for Aluminum Strip Cold Rolling**, Zenodo, https://zenodo.org/records/10685675 (DOI 10.5281/zenodo.10685675) | CC BY 4.0 | one file `data_all.csv`, 1.36 GB | 20 columns: `Export_speed, Pressure, Working_bending_force_1/2, Medium_bending_force_1/2, Shift_position_1/2, Entry_thickness_deviation, Entry_tension, Medium_tension, Output_tension, Absolute_position_1/2, Rolling_force_1/2, Thickness_deviation_1/2, Pre_Thickness_deviation_1/2`. "Historical rolling data from a real-world aluminum strip rolling line", built as reinforcement-learning tuples around a Smith-predictor logging policy. | Aluminium strip. **Alloy, nominal gauge, width, roll diameters not in the file header or on the page.** | Not stated. The companion paper's abstract gives 8,373,540 tuples. No time stamp column, no units in the header. | LP + first 3 kB of the CSV; companion paper (Xiao et al., IEEE Trans. Ind. Inform. 2024, doi 10.1109/TII.2024.3390625) AB |
| **D2** | **Cold rolling mill: Dataset for Recommender system for process optimization**, Zenodo, https://zenodo.org/records/8085933; code https://github.com/CuAuPro/opti-rec-sys | data CC BY 4.0; code GPL-3.0 | `dataset.pkl`, 149.5 MB (Python pickle 4.0) | "Process values obtained from a process line", each the mean in a window at equidistant positions along the strip, steady state only. Variables not listed on the page. From the EU project INEVITABLE (GA 869815); master thesis at Univ. Ljubljana. | **Metal not stated** on the Zenodo page or in the README (the thesis, in Slovenian, was not read). | Distance-domain windows, steady state | LP (Zenodo API) + README EX |
| D3 | **CRD cold rolling dataset**, https://github.com/DGlql/CRD | **no licence file** (LICENSE returns 404) | about 15,000 samples, ten coils | Rolling forces, bending force, rolling speed, tension, entry set thickness, exit set thickness, width, actual entry and exit thickness; "collected from a steel company in China". | Steel (MRT-1/3/4/5, Q195, Q195L, HSLA, SPCC); entry 1.8-3.5 mm, exit **0.18-1.12 mm**; widths 853-1250 mm | Not stated | README FT |
| D4 | **Dataset showing steel cold rolling process parameters for a 6-high cold rolling mill in Nigeria**, Ayuba et al., Data in Brief 18 (2018) 891, https://pmc.ncbi.nlm.nih.gov/articles/PMC5996350/ | CC BY 4.0 | 486 data points in the supplement | Target and actual entry/exit thickness (X-ray), X-ray gauge temperatures, mill power, entry and exit speed, six passes. **No roll force, no tension.** | Steel, reversing 6-high | Manual HMI readings, about 3 per pass, at least 3 min apart, over 400 h | EX |
| D5 | **Hybrid transfer learning framework for chatter mark detection on a 20-high cold rolling mill**, Univ. of Pretoria research data, DOI 10.25403/UPresearchdata.29877497.v1 (Figshare article 29877497; thesis handle https://hdl.handle.net/2263/103862) | CC BY 4.0 | six `.npy` files, 73-193 MB each (about 750 MB) | `Experimental_investigation_source/target_dataset.npy` (vibration data from the mill) and four `Numerical_experiment_*` files from a physics-based dynamic model. Channel list, sampling rate and material are not on the landing page. | 20-high cluster cold mill; metal not stated | Not stated | LP (Figshare API) |
| D6 | **Xi'an University of Technology, 6-high reversing cold mill operating data** (轧机设备运行状态数据集), national basic-science data centre, https://www.nbsdc.cn/general/dataDetail?id=6504340cbb16e0792635c425&type=1 | not read | 5.59 MB, Excel + Word | 23 items from the AGC system: entry/exit thickness, reduction, width, rolling force, roll gap, speed, rolling torque, entry/exit tension stress. | Not stated | Not stated | SN (aggregator page selectdataset.com; the portal itself was not opened) |
| D7 | **PRESAGE: Physics-Anchored Digital Twin of a Hot Strip Mill, two-year dataset**, IEEE DataPort, DOI 10.21227/80ne-mn36 | "Creative Commons Attribution" as listed | csv/avi/txt/zip; size not read | Stated: 6.99 million passes, 583,468 coils, 12-stand hot strip mill, 56-column pass records, 444 PLC tags, 100 ms series for selected windows. | Steel, hot | pass level + 100 ms windows | EX. **Caution:** created 2026-09-13 by a single submitter; whether the files are downloadable without an IEEE DataPort subscription, and whether the data are plant measurements, could not be verified. |
| D8 | **Maximum Rolling Force at F1 for Steel Grade SS400**, Kaggle, https://www.kaggle.com/datasets/pandhuw/maximum-rolling-force-at-f1-for-steel-grade-ss400 | CC0 | 205 kB, about 4,000 rows | Bar length, width, thickness in/out, temperatures, maximum roll force at finishing stand 1. | Steel, hot, 33-46 mm in | one row per bar | EX |
| D9 | **SOMAR SA rolling mill vibration sensors**, Zenodo https://zenodo.org/records/17493399 (also Kaggle `lukaszduss/vibration-data-from-rolling-mill`) | CC0 | 3 CSV, about 30 MB | Vibration max / RMS and temperature of a roll-stand bearing during progressive damage. | Steel bar mill | about 1 sample per second per sensor | LP |
| D10 | **Stress316L** (FE roll-deflection results), Kaggle `mahshadlotfinia/stress316l`, code https://github.com/mahshadlotfinia/Stress316L | code MIT; data licence not read | not read | Finite-element results of work-roll deflection in 316L strip rolling (simulated, not measured). | Stainless steel | n/a | README EX |

**Not real measurements, listed so they are not mistaken for them**

| ID | Name and URL | Licence | Note | Read |
|---|---|---|---|---|
| S1 | **TCM: Benchmark Datasets for Predictive Maintenance in Steel Manufacturing**, Zenodo https://zenodo.org/records/11469702; paper Front. Artif. Intell. 2026, doi 10.3389/frai.2026.1770922; notebooks https://github.com/jjakubow/pdm-steel-datasets | CC BY 4.0 | **Synthetic.** Six CSV (about 20,000 rows, 51 features each) from a mathematical model of a 5-stand steel tandem mill: thickness, yield stress in/out, roll diameters, reductions, tensions, speeds, force, torque, gap, motor power, with planted anomalies. Entry 3.7 mm, exit about 1.3 mm in the sample row. | LP + paper EX |
| S2 | **Temperature change in cold rolling simulation**, Mendeley Data, https://data.mendeley.com/datasets/wcp8wrdhyj/1 | CC BY 4.0 (per DataCite) | Simulation outputs: surface temperature rise against material, friction, geometry, feed speed. | LP |
| S3 | **Hot Strip Rolling Process Dataset**, Kaggle `ziya07/hot-strip-rolling-process-dataset` | not read | 1,000 rows with a "friction coefficient" and "deformation resistance" column; provenance not documented, looks generated. | EX |

**What transfers from the steel cold-rolling sets and what does not.** Transfers: the structure
of the slab force balance, Hitchcock flattening, the gaugemeter relation and AGC loop
dynamics, tension coupling, the third-octave chatter structure. Does not transfer: the flow
stress level (roughly 2-4 times that of 1xxx/8xxx aluminium), water-based emulsion against
neat kerosene (film formation, friction level, spray heat transfer and heat partition), the
strip-to-roll modulus ratio (210 against 70 GPa, which sets both the I-unit to stress
conversion and the foil "mattress" regime), and gauge (the thinnest open steel data stop at
0.18 mm).

**Which project claim each could test**

| ID | Module / claim | Test | Limits |
|---|---|---|---|
| D1 | `mill_dynamics.py` (gaugemeter AGC, incoming-thickness and hardness response, tension coupling) | Row-wise relation of `Entry_thickness_deviation`, `Rolling_force_1/2`, `Absolute_position_1/2` (screw or cylinder position) and `Thickness_deviation_1/2`: sign and size of dF/dH and of the exit deviation left after control; check that the "full compensation prints run-out through" behaviour is or is not visible; two-stand tension interaction (`Medium_tension`). Shape actuators (bending, shifting) are present but there is no flatness channel. | No units, no time base, no gauge, no alloy: only dimensionless ratios and correlations are testable unless the authors supply the metadata. Looks like a two-stand 6-high mill (suffixes 1/2, intermediate-roll bending and shifting); that reading is an inference from the column names. |
| D2 | `mill_dynamics.py`, possibly `slab.py` | Unknown until the pickle is opened: if it carries force, gauges, tension and speed per window it is the only open steady-state per-coil set from a plant. | Variables and metal unknown; pickle must be opened in an isolated interpreter. |
| D3 | `slab.py` / `contact.py` (force against reduction, tension, gauge down to 0.18 mm) | Fit one flow-curve per grade on some coils, predict force on held-out coils and passes; check the Hitchcock path near its thin-gauge limit. | Steel; roll radius, friction, flow curve and units not given; no licence. |
| D4 | `mill_dynamics.py` (thickness accuracy only) | Distribution of exit-gauge error against speed and power. | No force or tension; manual sampling. |
| D5 | `chatter.py` (onset frequency band, spectral signature), `band_signatures.py` | Spectra of the experimental arrays against the model's third-octave band and pitch law. | A 20-high cluster mill has different modes from a 4-high; channel metadata missing. |
| S1 | `slab.py` | Code-to-code comparison of force, torque and power against an independent slab implementation (their generator follows Bryant-type schedules). Not validation. | Synthetic. |

### 1.2 Material test data (downloadable)

| ID | Name and URL | Licence | Content | Use | Read |
|---|---|---|---|---|---|
| M1 | **Tensile test data of a 9 microns thick aluminium foil**, Zenodo https://zenodo.org/records/2646505 | "other-open" | 51 tensile tests on **AA8079 foil, 9 um**, specimens 100 x 10 mm, cut at 0, 10, ..., 90 degrees to the rolling direction; raw CSV per specimen (zip 2 MB). Source: Käck & Malmberg, master thesis, Lund 2015. | Foil stiffness and early plasticity for `strip_shape.py` (strip modulus at foil gauge: the authors report compliance rising with strain) and for the catalogue's 8079 entries. Annealed converter foil, not as-rolled H18. | LP |
| M2 | **NPL TENSTAND ASCII tensile data sets**, https://www.npl.co.uk/products-services/advanced-materials/tensile-testing | not stated in the part read | Reference stress-strain files for software validation, including **AA1050 soft sheet**, **AA5182 hard** and **AA5182 soft** sheet. | Room-temperature flow curves with agreed proof-stress values for 1050-O and 5182 (O and H); starting points for `materials.py` hardening laws up to uniform elongation only. | EX |
| M3 | Flow curves for AA6082, Zenodo 18213558; 6061-T651 at six temperatures, Mendeley `rd6jm9tyb6` | CC BY 4.0 (Zenodo) | Heat-treatable alloys, hot or structural tempers. | Not the project's alloys; listed to close the search. | LP |
| M4 | AA1050 asymmetric rolling textures, AGH RODBUK, doi 10.58032/AGH/SQEVDB; EBSD of cold-rolled and recovered Al-Mn, Zenodo 6470217 | CC0; CC BY 4.0 | Texture and microstructure after rolling. | Outside the project's present scope (no texture model). | LP |

### 1.3 Surface-defect image sets

None of these tests a physics module. They could support a later image-based front end for the
band vocabulary (`band_signatures.py`, section 3.7 of the band-diagnosis document), and only
loosely: every aluminium set found is of **extruded, coated profiles**, not rolled strip or foil.

| Name and URL | Licence | Size and classes | Material | Read |
|---|---|---|---|---|
| Tianchi 2018 Guangdong industrial competition, aluminium profile surface defects, https://tianchi.aliyun.com/competition/entrance/231682/information | competition terms, not read | about 3,000 annotated images out of roughly 10,000 (secondary sources differ), 2560 x 1920, ten defect classes (non-conductive, scratch, orange peel, leakage, jet, paint bubble, pit, dirty point, ...) plus defect-free images, as described by secondary sources | Extruded, surface-treated aluminium profile | SN (several papers and repositories describe it; the competition page was not opened) |
| **APDDD** (re-annotated for detection), https://tianchi.aliyun.com/dataset/148297 | Apache 2.0 as shown on the page | two zips of about 0.8 GB each plus annotations; ten classes | same | EX |
| APSDs-SR, Figshare doi 10.6084/m9.figshare.32726052.v1; IEEE DataPort doi 10.21227/rca7-a606 | CC BY (as listed) | 2,195 high-resolution images plus x2 / x4 down-sampled copies; DataPort entry says files are on Baidu and "have not been uploaded" | same source | AB / EX |
| Kaggle copies: `tngw0702/defects-in-aluminium-profiles`, `weihaoreal/aluminum-profile-surface-defects-data-set` | not readable (page error) | subsets of the Tianchi images | same | SN |
| Fraunhofer ITWM, Fordatis, https://fordatis.fraunhofer.de/handle/fordatis/420 (doi 10.24406/fordatis/370) | not read | real part 542 MB, synthetic part 730 MB, segmentation masks | Machined aluminium test objects (sand-blasted, milled), not rolled product | EX |
| ASSDD, aluminium **strip** surface defects (five classes, line-scan camera at a tension leveller), Lv et al., Eng. Appl. Artif. Intell. 126 (2023) 107023 | **not public** as far as found | described in the paper only; the authors' repository https://github.com/zh-lv-94/SACV links other sets, not this one | Cold-rolled aluminium strip | AB + README FT |
| CR7-DET, cold-rolled **steel** strip, https://github.com/jsq0903/CR7-DET/ | no licence file | 4,140 images, 11,020 labels, seven classes (inclusion, dent, oil spot, pit, punching, linear, macular); files on Baidu | Steel | README EX |
| NEU-CLS / NEU-DET (hot-rolled steel, six classes), X-SDD (1,360 images, seven classes) | licence unclear ("research use" on a mirror) | well-known steel sets on IEEE DataPort / Figshare | Steel, hot | SN |
| Severstal steel defect detection (Kaggle), GC10-DET | not verified | | Steel | MEM |

No public image set of aluminium **foil** defects (pinholes, wrinkles, tension lines, heat or
rolling stripes) was found.

---

## 2. Published benchmark measurements (tables and figures, not downloads)

### 2.1 Roll bite at thin gauge: force, forward slip, friction

| Source | Where the numbers are | Conditions | Module it could test | Read |
|---|---|---|---|---|
| Boemer, Carretta, Laugier, Legrand, Papeleux, Boman, Ponthot, "An advanced model of lubricated cold rolling with its comprehensive pilot mill validation", J. Mater. Process. Technol. 296 (2021); open postprint https://orbi.uliege.be/handle/2268/261506. Thesis: Boemer, "Numerical modeling of friction in lubricated cold rolling", ULiège 2020, https://orbi.uliege.be/handle/2268/245441 | Not located (abstract level): the paper states roll force and forward slip against speed and reduction, roll and strip roughness, plane-strain-compression hardening laws, lubricant viscosity laws. | Semi-industrial pilot mill, **steel**, mixed lubrication with and without starvation. | `slab.py`, `contact.py`, `bite_tribology.py`: the most completely specified open bite benchmark found (all inputs published together). | AB |
| Stephany, PhD thesis, ULiège 2008, https://orbi.uliege.be/bitstream/2268/315004/1/AnSyThese_doc_V1.pdf | Figures 4.22-4.23 (measured forward slip and friction force against reduction for two lubricants), from the list of figures. | Steel, mixed lubrication. | same | EX (front matter) |
| Carretta et al., "MetaLub", Proc. IMechE J 225 (2011) 894; postprint https://orbi.uliege.be/handle/2268/90243 | Not located. Comparison with literature and ArcelorMittal data, including negative forward slip. | Steel. | same | AB |
| Tabary, Sutcliffe, Porral, Deneuville, J. Tribol. 118 (1996) 629 (already cited by the project as an abstract) | Not located. Abstract: friction about 0.09 at the slowest speeds (boundary value from a disc machine), below 0.01 at the highest; governed by the ratio of smooth film thickness to combined roughness and by reduction; oil temperature 40-60 C secondary. | **Aluminium strip**, experimental mill. | `bite_tribology.py`: the placeholder friction closure against film ratio. Paywalled; the full text would turn the placeholder into a fitted curve. | AB |
| Le & Sutcliffe, "Rolling of thin strip and foil: application of a tribological model for mixed lubrication", J. Tribol. 123 (2001), doi 10.1115/1.1402179 | Not located. Abstract: mill trials under industrial conditions for thin strip and foil; predicted load in reasonable agreement, forward slip over-estimated for foil unless friction varies through the bite. | **Aluminium thin strip and foil**, industrial mill. | `foil_bite.py`: the only source found that pairs a foil model with industrial foil-mill load and slip. Also direct support for the project's own "implausible forward slip" flag. Paywalled. | AB |
| Sutcliffe & Rayner, "Experimental measurements of load and strip profile in thin strip rolling", Int. J. Mech. Sci. 40 (1998) 887-899, doi 10.1016/S0020-7403(97)00138-0 | Not read. | Not verified (material and gauge not read). | `foil_bite.py`: measured load and deformed strip profile in the regime where the roll stops being circular. Paywalled. | LP (bibliographic record) |
| Sutcliffe & Montmitonnet, Rev. Métall. 2001, open at https://minesparis-psl.hal.science/hal-00574224v1/document (already used by the project for the film ratio) | Table I (inputs), Fig. 6 (load against speed), Fig. 7 (forward slip, film thickness, contact ratio). | Model results, not measurements: aluminium foil 50 to 25 um, yield 150 MPa, tensions 20 MPa, roll radius 135 mm, 5-40 m/s, viscosity 2.5 mPa s, pressure coefficient 1.2e-8 /Pa, asperity friction 0.1 or Tresca 0.25. Forward slip rises from about 5 to 45 % as speed falls (Coulomb model). | `foil_bite.py`: **model-to-model** check on a fully specified 50 to 25 um pass, the project's own demo gauge; digitise Figs. 6-7. Their large Coulomb forward slip at low speed is the same symptom the mattress model shows. | EX |
| Sutcliffe, "Friction and lubrication in metal rolling", PhD thesis, Cambridge 1989, https://www.repository.cam.ac.uk/handle/1810/244874 | Not located (abstract level). | Rheology of a typical aluminium foil rolling oil measured at high pressure and shear rate on a disc machine (Eyring model fits); asperity crushing under bulk deformation, theory against experiment; film thickness for strip and foil conditions. | `bite_tribology.py`: oil rheology and asperity-flattening inputs for foil conditions. Open repository. | AB |
| Jiang, "Mechanics of cold rolling of thin strip", in Numerical Analysis - Theory and Application, InTech 2011, https://www.intechopen.com/chapters/19449 (open) | Tables 2-3 (computed force, intermediate force, edge-contact force, exit crown with and without work-roll edge contact); Figs. 18-19 (measured against computed force for widths 100-160 mm and several speeds). | Hille 100 laboratory mill (work roll 63 mm, backup 228 mm, barrel 254 mm, dimensions from the abstract page of Jiang & Tieu, Wear 2007); low-carbon **steel** 0.55 to 0.12-0.17 mm, 0.27 m/s, friction 0.1. | `foil_bite.py` and the missing closed-gap model: the only open source found with numbers for **work-roll edge contact (roll kissing)**. | EX |
| Tibar & Jiang, "Effect of rolling parameters on thin strip profile in cold rolling" (WASET paper deposited as Zenodo 1339094) | Not located. | **Aluminium** thin strip, Hille 100 mill, dry, roll crossing 0-1 degree and shifting 0-8 mm, speed ratio 1.3; profile and force. | `strip_shape.py` (profile response); laboratory scale, asymmetric rolling. | AB |
| Öztürk & Şeherli, Turk. J. Elec. Eng. Comp. Sci. 27 (2019) 1461, open at https://journals.tubitak.gov.tr/cgi/viewcontent.cgi?article=1732&context=elektrik (doi 10.3906/elk-1803-25) | Section 3 and Table 1. | **Aluminium foil 6.35 um at 550 m/min**; X-ray gauge range 2-200 um, 100 mm measurement interval; motor armature and field currents and gauge logged at 1 Hz, 7,250 samples (121 min). Data not released. | `band_products.py` (one more published final-pass speed); shows what a foil mill historian typically holds. | EX |
| Shao et al. 2015 (in the project) | p. 94, Tables 1-2 | AA5052, 4.10 to 1.72 mm | already used | - |

### 2.2 Roll temperature, thermal crown, spray heat transfer

| Source | Where the numbers are | Conditions | Module | Read |
|---|---|---|---|---|
| Hobbis (Novelis), "Roll cooling in Novelis aluminum hot and cold rolling mills", STLE 2017 presentation, https://www.stle.org/images/pdf/STLE_ORG/AM2017%20Presentations/Nonferrous%20Metals/STLE2017_Nonferrous%20Metals%20II_Session%206L_A.%20Hobbis_Roll%20Cooling%20in%20Novelis%20Aluminum%20Hot%20and%20Cold%20Rolling%20Mills.pdf (the project cites a trade report of this talk) | Slides: heated instrumented aluminium block cooled by lubricant sprays, "up to 25 % reduction in htc compared to normal paraffin"; heated rotating-roll rig (effects of flow, pressure, nozzle, geometry, roll speed, coolant); liquid-crystal maps of the coefficient; nozzle pitch 1-3 inch; target 10-50 % overlap. Absolute coefficients not seen in the extract. | Aluminium cold-mill oils, laboratory rigs. | `roll_thermal.py`: bounds the *spread* of the spray coefficient between base oils (25 %), which is one of the two supplied inputs; the slide deck may hold absolute curves. | EX |
| Heenan & Januszkiewicz, Ind. Lubr. Tribol. 67 (2015) 9-16 (Novelis) | Not located. Measured coefficients of cold-rolling base oils **relative** to C14-C16 normal paraffin; rises with n-paraffin content. | Aluminium cold-rolling base oils, purpose-built rig. | `roll_thermal.py` spray coefficient sensitivity. Paywalled. | AB |
| Wang, Zhang & Ai, "Influence of edge thermal spraying on the temperature field and thermal crown of work roll during cold rolling of aluminum alloy strip", Int. J. Adv. Manuf. Technol. 2023, doi 10.1007/s00170-023-11830-2 | Not read. | Aluminium cold mill with hot edge sprays. | `roll_thermal.py` (hot edge spray, which the catalogue mentions but the model does not treat). | LP |
| Souto, Abdelkhalek, Koont, Legrand, "Tec3 work roll thermal crown model for hot and cold rolling of steel", ABM proceedings (open PDF) | Not located. States tuning against roll surface temperature and roll thermal profile measurements, separate skin and bulk time scales, segmented cooling zones. | Steel. | `roll_thermal.py`: independent support for the two-time-scale structure (fast skin, slow bulk) that the project's limitation list discusses. | AB |
| Song et al., NUMIFORM 2013 (AIP Conf. Proc. 1532, 1125); Li et al., J. Cent. South Univ. 21 (2014) 2160 | Not located; both claim agreement with measured thermal crown on steel tandem cold mills. | Steel, emulsion. | structure only | AB |
| Davies, Sivilotti & Tulett 1975 (in the project as an abstract) | Three thermal effects with separate time constants on a high-speed aluminium mill. | Aluminium, thin hard alloys. | The full text is the best single lead for the "20 s against minutes" open question; still paywalled. | AB |

No open table of **measured roll surface temperature across the barrel** of an aluminium
cold or foil mill with the matching coolant pattern was found, and no **measured absolute
heat-transfer coefficient** for kerosene sprays on a rotating roll.

### 2.3 Flatness, roll stack, buckling

| Source | Where the numbers are | Conditions | Module | Read |
|---|---|---|---|---|
| Kpogan, Zahrouni, Potier-Ferry et al. 2012, open at https://hal.science/hal-01868101v1/file/Kpogan2012.pdf | Table 1 (rolling case), Fig. 3 (longitudinal stress across the width: three models against stress-meter roll measurements). | Last stand of a **tinplate** tandem mill, very low gauge (steel). | `strip_shape.py`: the standard published case in which a measured shapemeter stress profile is compared with latent and buckled model stress. The same case is in Abdelkhalek et al. 2011 (in the project) and in https://minesparis-psl.hal.science/hal-00674953 (abstract read). | EX |
| Nakhoul, PhD thesis, Mines ParisTech 2014 (theses.fr) | Not located. Multi-scale buckling model for edge and centre waves, decoupled and coupled to Lam3/Tec3; parametric studies of friction and bending force. | Steel thin strip. | `strip_shape.py` buckling mode and post-buckling amplitude (the project assumes one mode). | AB |
| Wang, Li, Wang, Yang, Wu, Metals 12 (2022) 1977, doi 10.3390/met12111977 (open, CC BY) | Table of field samples: SPCC 0.28-0.66 mm, width 904-909 mm, tension 10.1-10.9 MPa, with **computed** critical buckling strain differences for centre, double-edge and local waves (about 30-32, 27-29, 14-18 in the paper's units). | Steel, single-stand 6-high. | `strip_shape.py` in-mill buckling onset: model-to-model comparison at 0.28 mm with all inputs printed. | EX |
| Malik, "Rolling mill optimization using an accurate and rapid new model for mill deflection and strip thickness profile", PhD, Wright State 2007, https://corescholar.libraries.wright.edu/etd_all/137 (open) | Not located. | 4-high and cluster mills; roll-stack deflection model combining finite elements with analytical solid mechanics, static and dynamic. | `strip_shape.py`: a documented roll-stack model with bending and shifting, which the project lacks (half-space compliance only). | AB |
| Magne, Legrand et al., J. Appl. Phys. 2022, doi 10.1063/5.0079873 | Not located. Fibre-Bragg shapemeter roll, 5 mm resolution, 0.1-1 mm strip. | Pilot lines. | Sets what "narrow band" resolution is physically available (5 mm against the usual 26-52 mm zones). | AB |

### 2.4 Chatter

| Source | Where the numbers are | Conditions | Module | Read |
|---|---|---|---|---|
| Niroomand, Forouzan, Salimi, ISIJ Int. 55 (2015) 637 (in the project, cited for the wave-model disagreement only) | Section 4, Figs. 10-11: accelerometer on the second-stand work roll sampled at 5120 Hz; chatter about 80 s into the third pass; **critical speed of the first stand 5.8 m/s**; spectral peak **124.6 Hz**. | Two-stand reversing tandem mill, **steel**, 2 mm incoming, 60-90 % total reduction. | `chatter.py`: a measured onset frequency and speed with published mill parameters. The project could run it as a numeric benchmark, not only as a caveat. | EX |
| Zhao, "Regenerative chatter in cold rolling", PhD, Northwestern 2008, doi 10.21985/n2d444; Zhao & Ehmann, J. Manuf. Sci. Eng. 135 (2013), Parts 1-2 | Not located. State-space single- and multi-stand models, stability charts in friction, tension and stand spacing; optimum friction band. | Steel tandem mill parameters. | `chatter.py`: independent stability charts for code-to-code comparison; bears on the "friction and tension disagreements" the project lists. | AB |
| Vaidya et al., "Analysis of causes and remedy of chattering in the aluminum four stand tandem cold rolling mill: a case study", J. Inst. Eng. India Ser. C 2021, doi 10.1007/s40032-021-00773-w | Not read. Snippet: 4-high CVC tandem mill, **AA3104 to 0.15 mm, 2100 mm wide**, design speed 1800 m/min, limited to 1000 m/min by chatter. | Aluminium can-stock mill. | `chatter.py`: one aluminium data point of speed limit by chatter. Frequency not seen. | SN |
| Usmani et al., Diagnostyka 19 (2018) 73, doi 10.29354/diag/81692 (open) | Sections 3-4: accelerometers on stand housings, 10 kHz sampling, 14 chatter coils against 43 normal coils, analysis band 0-1300 Hz. | Steel 5-stand tandem mill. | Measurement practice (sensor position, sampling) for the plant plan in section 6. | EX |
| Pérez et al., Computers in Industry 103 (2018) 86 | 4,102 coils, 722 chatter events, spectrograms 0-400 Hz. Data not public. | Steel tandem mill. | none directly | EX |
| D5 above | | 20-high | | LP |

### 2.5 Wound-roll (coil) stresses, ridges, troughs

| Source | Content | Transfer to aluminium coil | Read |
|---|---|---|---|
| Proceedings of the International Conference on Web Handling, Oklahoma State University, open on SHAREOK (for example Forrest 1999, "Fully nonlinear solution to the stresses inside wound rolls", https://shareok.org/handle/11244/321804; Cole & Hakiel 1992, "Widthwise variations in web properties and wound roll structure", https://shareok.org/handle/11244/321890; "On the effect of width direction thickness variations in wound rolls", https://shareok.org/handle/11244/321658) | The Hakiel model and its extensions; width-wise thickness variation (the physics of a coil ridge); measured in-roll pressures on film and paper. | Structure transfers (radial stack modulus rising with pressure, tension taper, ridge build-up); materials do not (film and paper, not metal). Directly relevant to the project's coil-ridge formula and its "compaction factor 0.5" analyst choice. | AB / SN |
| Weisz-Patrault, Ehrlacher, Legrand et al., coiling of steel strip: 2015 finite-strain model (CORE), Mechanics & Industry 18 (2017) 218 (open), "Nonlinear and multiphysics evaluation of residual stresses in coils", https://hal.science/hal-01823186 | Contact pressure between wraps and residual stress during coiling under tension with an incoming residual-stress (flatness) profile. | Metal strip, so closer than web handling; steel, thicker gauge. | SN |
| ISIJ Int. 64 (2024) 1037 (strip coiling FE with laminated-compression experiments for the interlayer law) | Measured stack compression law for steel laps. | Method transfers: the same stack test on foil laps would give the radial modulus the ridge model needs. | SN |
| Innoval Technology winding-model blog, https://www.innovaltec.com/winding-model-blog/ | Vendor description of an aluminium coil winding model (analytical and FE). No numbers. | Aluminium, but no data. | SN |

No published measurement of interlayer pressure or ridge height in an **aluminium foil** coil
was found.

### 2.6 Flow curves for 1xxx / 3xxx / 5xxx / 8xxx

| Source | Content | Read |
|---|---|---|
| Ryen, "Work hardening and mechanical anisotropy of aluminium sheets and profiles", PhD, NTNU 2003, https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/244466 (the project cites Ryen et al. 2006 as an abstract) | Part A: work hardening of commercially pure Al, Al-Mg and Al-Mn during **cold rolling** to large strain. The thesis is the open long form of the 2006 paper and the most relevant single source for rolling flow stress against rolling strain. Tables not seen. | SN |
| Bacha et al. 2006 (channel-die compression of 5xxx and 6xxx to strain about 1.5, generalised Voce fits) | Large-strain plane-strain flow curves, the right test for rolling. Seen only on a document-sharing site. | SN |
| NPL TENSTAND (M2), Zenodo AA8079 foil (M1) | downloadable curves, small strain | EX / LP |
| Strathclyde study of AA1050 sheet at several strain rates and temperatures (ASTM E2448), https://pureportal.strath.ac.uk/en/publications/analysing-the-effect-of-strain-rate-and-temperature-on-the-flow-s/ | Rate and temperature sensitivity of 1050 (the project sets rate sensitivity to zero). | SN |
| TALAT lectures (European Aluminium Association, 1994-1999), index at https://aluminium-guide.com/talat-lectures/; lecture 1301 "The rolling of aluminium: the process and the product" (24 pages) | Free training lectures with work-hardening curves against cold reduction for common alloys. Only third-party mirrors were found; figures not checked. | SN |
| Hockett & Sherby (1975), large-strain saturation law for 1100 aluminium | Classic large-strain fit. | MEM |

---

## 3. Open-source codes

| Code and URL | Licence | Language | What it models | Maturity | Use for the project | Read |
|---|---|---|---|---|---|---|
| **PyRolL core**, https://github.com/pyroll-project/pyroll-core (plus plugins such as `pyroll-hitchcock-roll-flattening`, `pyroll-freiberg-flow-stress`) | BSD-3-Clause | Python | Extensible rolling framework; "current focus lies on groove rolling in elongation grooves". JOSS paper 10.21105/joss.06200. | Active, packaged, documented. | Already known to the project. Not a flat-strip cold-mill solver; **reference** for plugin architecture and for the Hitchcock plugin as a code-to-code check of roll flattening. Would be a dependency (NumPy/SciPy stack), so not a component. | README + LICENSE FT |
| **EJM_A_input_files**, https://github.com/francisflanagan/EJM_A_input_files | MIT | Abaqus `.inp` | All input decks for "Through-thickness resolution, stress oscillations and residual stress in cold rolling" (the journal version of arXiv 2408.03242, which the project already cites): CPE4R / CPE4 / CPE4I, implicit and explicit, up to 60 elements through the thickness. | Research artefact, complete for the paper. | **Independent cross-check** of pressure and shear distributions for the rigid-roll slab and asymptotic models. Needs Abaqus (commercial); the geometry and material cards could be ported to CalculiX. Reference, not a dependency. | README + LICENSE FT |
| **Metalub** (ULiège / ArcelorMittal) | not open source (no repository found) | - | Mixed-lubrication slab model with non-circular flattening, starvation, thermo-viscoplastic strip. | Mature, closed. | Reference only: Boemer's thesis documents the equations and the validation data in full. | AB |
| **EHL-FBNS solver**, https://github.com/ErikHansenGit/EHL | Unlicense (public domain) | MATLAB | Unsteady elastohydrodynamic lubrication: finite-volume Reynolds equation with mass-conserving cavitation, elastic half-space by boundary elements, Roelands and Dowson-Higginson laws, shear thinning. | 61 stars, maintained. | **Reference** to cross-check the inlet-film calculation of `bite_tribology.py` in the hydrodynamic limit; no plastic strip, so not a rolling solver. The licence allows porting pieces. | README + LICENSE EX |
| **TriboSim**, https://github.com/a-dorgham/TriboSim | AGPL-3.0 | Python 3.10, PyQt6 | Point-contact elastohydrodynamic and plasto-elastohydrodynamic lubrication. | Young (2 stars). | Reference only (AGPL, point contact, GUI dependencies). | README + LICENSE EX |
| **pdm-steel-datasets**, https://github.com/jjakubow/pdm-steel-datasets | not read | Python notebooks | Validation and benchmarking notebooks for the synthetic tandem-mill data S1. The generator itself was not seen in the README. | Paper companion. | Code-to-code check of force/torque/power only. | README EX |
| **opti-rec-sys**, https://github.com/CuAuPro/opti-rec-sys | GPL-3.0 | Python | Recommender system for cold-mill recipes; loader for D2. | Thesis code. | Use only to learn the layout of D2. | README EX |
| **Stress316L**, https://github.com/mahshadlotfinia/Stress316L | MIT | MATLAB | Neural surrogate of FE work-roll deflection in 316L strip rolling, with a Kaggle dataset of FE results. | Paper companion. | Weak cross-check of roll bending for a future roll-stack model. | README EX |
| Hakiel wound-roll model in Mathematica (also MATLAB and COMSOL Script versions described), Wolfram Library Archive item 6950, https://library.wolfram.com/infocenter/Conferences/6950/ | not read | Mathematica | Nonlinear wound-roll stresses, closed form for constant radial modulus. | Conference material. | Reference for a standard-library re-implementation (a second-order boundary-value problem per lap: small). | SN |
| Cryogenic Materials Repository (arXiv 2509.23422) | not read | Python | Open, extensible re-implementation of the NIST cryogenic property fits, with source data. | New. | Reference for thermal property provenance below room temperature only. | SN |
| CalculiX, Kratos Multiphysics | GPL-2; BSD | Fortran/C; C++ | General FE | Mature | Already listed by the project. | - |
| Other repositories seen by name only, not read: `kmbadawy/Cold_Rolling` (code for doi 10.1016/j.mtcomm.2021.102253), `johnnybran/ColdRollingMill`, `nathdwek/rollingMill` (MATLAB mill control), `pjkang2023-hub/cold-rolling-mill-simulator`, `1500ssp-oss/timc-rolling-replay` (audit package for an ultra-thin strip study; raw data withheld) | none stated in the listing | | | | Not assessed. | LP |

**Not found as open source:** a flat-strip cold-rolling simulator in any language; a foil
(Fleck-Johnson type) bite solver; a roll-stack / flatness code; a third-octave chatter model;
a mixed-lubrication rolling solver; a Python wound-roll model; published MOOSE, FEniCS or
deal.II rolling input decks. `physicroll` appears to be alone in this space, which also means
there is no independent open code to cross-check most of it against.

---

## 4. Open material property sources

| Source | What is open | Limits | Read |
|---|---|---|---|
| NIST Cryogenic Technologies Group material pages, for example https://trc.nist.gov/cryogenics/materials/5083%20Aluminum/5083Aluminum_rev.htm and `.../6061%20Aluminum/6061_T6Aluminum_rev.htm`; 3003 and 1100 are in the 2006 database update | Polynomial fits of thermal conductivity and specific heat, 4-300 K, for 6061-T6, 5083, 3003 (and 1100 listed). | Cryogenic range, upper end at room temperature: useful only as an anchor at 300 K. A search summary noted that the 3003 specific-heat coefficients on the page equal those of 6061-T6 (possible copy error; check before use). | SN |
| NPL TENSTAND files (M2) | AA1050-O, AA5182 soft and hard tensile curves with agreed values. | Uniaxial, to necking. | EX |
| Zenodo AA8079 9 um foil tensile set (M1) | The only open raw data on a foil-gauge product. | Annealed converter foil. | LP |
| NTNU Open (Ryen 2003 and related theses on work hardening of Al-Mg / Al-Mn), Cambridge repository (Sutcliffe 1989: foil rolling oil rheology) | Open theses with tables and figures. | Numbers must be transcribed; tables not checked. | SN / AB |
| `pyroll-freiberg-flow-stress` (BSD-3) | A packaged flow-stress approach with a material database (Freiberg / Hensel-Spittel type). | Whether it holds aluminium grades was not checked; hot-forming oriented. | LP |
| TALAT lectures (mirrors) | Handbook-style curves and property tables. | Mirrors only; rights unclear. | SN |
| Abbott Aerospace spreadsheet AA-SM-000-001, https://www.abbottaerospace.com/downloads/aa-sm-000-001-aluminum-material-data-basic-full-curves-and-data/ | Free spreadsheet of elasto-plastic curves from public aerospace allowables. | Aerospace alloys and tempers, not foil stock. | EX |
| MatWeb (free to view, not openly licensed), MPDB / JAHM, Total Materia, JMatPro outputs | - | Not open; no JMatPro-derived open set for these alloys was found. | MEM |

No open database gives **rolling flow stress against accumulated cold reduction** for 1235,
8011, 8079 or 3003 in machine-readable form. The project's use of finished tensile strength
as an indicator stays the practical route until plant or laboratory curves are supplied.

---

## 5. Standards and test methods

Already in the project's catalogue (not new): EN 546-1 to -4, EN 485-4, EN 12258-1, ASTM B479,
ASTM B926, ASTM B373, GB/T 3198, GB/T 33143, GB/T 22638 (parts .1-.7 listed), GB/T 22648,
JIS H 4160, Aluminum Association QCA-1.

| Standard | What it defines | Freely readable | Read |
|---|---|---|---|
| **ASTM A1030/A1030M-21**, Standard practice for measuring flatness characteristics of steel sheet products | Wave height and interval measurement, steepness and I-unit conversion; the usual written reference for the I-unit even outside steel. A processor's note gives `I = 2.467 (H/L)^2 x 1e5` (which is `(pi/2)^2 (H/L)^2 x 1e5`), with a worked example of 1/16 inch in 12 inch giving about 6.7 I. | Scope on the ASTM store page; formula from https://www.baileymetalprocessing.com/techmatters/2018/08 (vendor). | SN |
| EN 546-4:2007, special property requirements | Contents list seen: porosity (pinholes), **wettability** (principle, test conditions, methods, frequency), stickiness, burst strength, Erichsen cupping. | Table of contents on resellers; preview pages on the SIST / iteh site the project already uses. | SN |
| GB/T 22638.2-2016, pinholes | Light-transmission inspection in a controlled room; inspected area "not less than 0.1 m2" in the 2016 revision. | English preview at chinesestandard.net. | SN |
| GB/T 22638.4 / .5, wetting tension and wettability | Dyne-liquid and water-brush classes (the A-D grades used in foil specifications). | Titles only. | SN |
| ASTM B926-09(2025), pinholes on a light table | Counting method referenced by B479. | Abstract on the ASTM store. | SN |
| ASTM D2578, wetting tension of films by dyne solutions | The method behind "dyne" values quoted for foil. | Not checked. | MEM |
| EAFA, "Surface characteristics of aluminium foil" (2020) | Vocabulary of stripes and marks (already source S26 in the project). | Free PDF. | - |

No standard defines "band" or "tension line" on foil with a measurement method; the project's
vocabulary section stays a literature synthesis. Flatness of foil is not specified in I-units
in any standard read: EN 546 and GB/T 3198 use visual and lay-flat criteria (as the project's
catalogue already records).

---

## 6. Validation plan by module

Each row gives the best open evidence, the test, and what only a plant can supply.

### 6.1 Slab bite (`slab.py`, `contact.py`, `literature.py`)

- **Best open evidence.** (a) Shao 2015, already run. (b) Boemer et al. 2021 / Boemer 2020
  (steel pilot mill with hardening laws, roughness and lubricant laws published): rebuild two
  or three of their operating points with their hardening law and a single calibrated
  friction, and compare force and forward slip against speed and reduction. (c) Flanagan's
  Abaqus decks (MIT) for pressure and shear distributions in the rigid-roll case. (d) D3 (steel,
  to 0.18 mm) for held-out force prediction after fitting one curve per grade. (e) S1 for a
  code-to-code check of force, torque and power.
- **Gap.** No open aluminium record with force **and** torque **and** measured forward slip.
- **Plant data needed.** Per pass, steady windows of 5-10 s: rolling force (both load cells),
  spindle torques or motor power with drive losses, roll surface speed and strip exit speed
  (laser velocimeter, forward slip to 0.1 % absolute), entry and exit gauge, both tensions as
  forces, width, work-roll diameter and roughness, alloy, temper and prior reduction. 10-100 Hz
  logging averaged over the window is enough.

### 6.2 Foil mattress bite (`foil_bite.py`)

- **Best open evidence.** (a) Sutcliffe & Montmitonnet 2001, Table I and Figs. 6-7: a fully
  specified 50 to 25 um aluminium pass; model-to-model only. (b) Jiang 2011 (InTech): Hille mill
  steel 0.55 to 0.12 mm with measured force and computed edge-contact forces. (c) Behind
  paywalls: Le & Sutcliffe 2001 J. Tribol. (industrial foil trials; forward slip over-predicted),
  Sutcliffe & Rayner 1998 (measured load and profile), Fleck/Johnson/Mear/Zhang 1992.
- **Test.** Reproduce (a) at 5, 20 and 40 m/s with the same yield stress and tensions; report
  load per width and forward slip next to the digitised curves. Buy or borrow the three
  paywalled papers: they are the only route to a foil benchmark with known inputs.
- **Gap.** No public foil-mill force or slip record; nothing on closed-gap (kissing) load
  share at foil gauge; nothing below 20 um.
- **Plant data needed.** For each foil pass: total rolling force and, if the mill runs
  closed-gap, bending force and roll-end contact indication; exit speed against roll speed
  (forward slip); entry and exit gauge; tensions; speed; oil viscosity and temperature;
  work-roll diameter, crown and roughness (Ra, and age in tonnes or km); strip width. One steady
  point per pass at two or three speeds separates friction from flow stress.

### 6.3 Tribology and pass heating (`bite_tribology.py`)

- **Best open evidence.** Tabary et al. 1996 (aluminium, friction against film ratio; abstract
  numbers 0.09 to below 0.01); Sutcliffe 1989 thesis (oil rheology, open); Boemer 2020
  (steel); the Don-Chris roughness data already known.
- **Test.** Replace the placeholder friction closure by a curve through the Tabary end points
  as a function of film ratio and check the slope the project already uses; compare the
  viscosity-pressure law against the Eyring parameters in the Sutcliffe thesis.
- **Gap.** No open measurement of strip exit temperature or heat partition on a foil mill
  beyond the abstract the project already holds.
- **Plant data needed.** Strip temperature just before and after the bite (contact probe on
  the coil or a calibrated pyrometer; aluminium emissivity is the difficulty), oil supply and
  return temperature and flow by zone (heat balance, 1 Hz), oil viscosity at 40 C, additive
  content.

### 6.4 Roll thermal (`roll_thermal.py`, `band_thermal.py`)

- **Best open evidence.** Hobbis 2017 (relative spray performance, design rules), Heenan &
  Januszkiewicz 2015 (relative coefficients of base oils), the Tec3 paper (skin and bulk time
  scales, steel), Dohmae & Okamura and Davies et al. (in the project).
- **Test.** Only consistency checks are possible: that a 25 % change of the spray coefficient
  moves the stripe height by the amount `width.thermal_sensitivity` reports; that the model's
  fast and slow time constants bracket those reported.
- **Gap.** Nothing public gives a roll temperature profile across the barrel, a thermal
  crown in micrometres, or an absolute kerosene spray coefficient on a rotating roll.
- **Plant data needed.** (1) Roll barrel temperature scan at 25-50 mm pitch within 60 s of
  roll-out, with the preceding 30 min of spray-zone states, flows and oil temperature. (2) A
  zone step test: close one zone valve for 20-60 s at steady speed and log the shapemeter
  channel under it and its neighbours at 1-10 Hz (gives the local time constant and gain
  directly). (3) Nozzle footprint check (pressure-sensitive film) to confirm spacing and
  overlap.

### 6.5 Strip shape and buckling (`strip_shape.py`, `band_width.py`)

- **Best open evidence.** The tinplate last-stand case (Kpogan 2012 open; Abdelkhalek 2011):
  measured stress-meter profile against latent and buckled model stress. Wang et al. 2022
  (computed buckling thresholds at 0.28-0.66 mm with inputs). Malik 2007 for a roll-stack model.
- **Test.** Feed the tinplate case's post-bite stress profile to the Rayleigh buckling check
  and compare the in-mill verdict (manifest or latent) with the paper; compare the onset
  thresholds with the Wang table at 0.28 mm after converting units.
- **Gap.** No open shapemeter data of any kind; no measured relation between a known roll
  stripe and the resulting I-units; nothing at foil gauge; nothing that could confirm or
  refute the model's "thinner is less sensitive in the mill" result.
- **Plant data needed.** Shapemeter export of every zone (raw and target curve) at 1-10 Hz with
  bending, tilt, zone cooling states, tension, speed and gauge; an off-line lay-flat
  measurement (wave height and length, or strip-length differences) of the same coil position
  after tension release; a cross-width gauge profile at 5-10 mm pitch from an off-line
  traverse.

### 6.6 Coil ridge and troughs (`strip_shape.py`)

- **Best open evidence.** The web-handling literature (Hakiel; Cole & Hakiel on width-wise
  thickness variation; the open Oklahoma State proceedings; Good et al. 2009, already used for
  troughs and wrinkles), and steel coiling models (Weisz-Patrault).
- **Test.** Implement the Hakiel wound-roll model in the standard library (a small
  boundary-value problem) and compare its ridge build-up against the project's proportional
  ridge formula and the compaction factor 0.5, using a stack modulus law from the literature.
- **Gap.** No measured interlayer pressure, stack modulus or ridge height for aluminium foil
  coils.
- **Plant data needed.** Coil outer-diameter profile across the width (5 mm pitch) at two or
  three build-up diameters, with the strip profile of the same coil; coil hardness across the
  width; winding tension and taper; a laboratory stack-compression test on 50-200 foil laps
  to get the radial modulus law.

### 6.7 Chatter (`chatter.py`, `band_signatures.py`)

- **Best open evidence.** Niroomand et al. 2015: 124.6 Hz and 5.8 m/s with mill parameters
  (steel). Zhao 2008 / Zhao & Ehmann 2013 for stability charts. D5 for raw vibration arrays
  (20-high). One aluminium case study (speed limited to 1000 of 1800 m/min).
- **Test.** Run the Niroomand mill through `chatter.py` (with and without the bite-damping
  closure) and report predicted against measured onset frequency and critical speed; this is
  the one quantitative external check available today.
- **Gap.** No open aluminium or foil chatter record with speed, frequency and mill parameters.
- **Plant data needed.** Accelerometers on both work-roll chocks or the housing top, sampled
  at 5 kHz or more, during a speed ramp to onset on at least three coils; the speed, tensions
  and gauge at onset; an impact (hammer) test of the stand for its natural frequencies; the
  measured pitch of marks on the strip.

### 6.8 AGC and drive (`mill_dynamics.py`)

- **Best open evidence.** D1 (aluminium, real, large, but without units or time base), D2
  (real cold mill, steady windows), D4 (thickness accuracy on a steel reversing mill).
- **Test.** On D1: regress exit deviation on entry deviation, force and position; compare the
  signs and ratios with the gaugemeter relation; look for a periodic component in force and
  exit gauge (roll eccentricity) once the sampling interval is known. Ask the dataset author
  for units, sampling rate and gauge range (the record is CC BY, so publishing an annotated
  derivative is allowed).
- **Gap.** No open step-response, mill-modulus or torsional data.
- **Plant data needed.** Mill stretch curve (kiss-roll test), cylinder step responses,
  100 Hz or faster logs of gap, force, entry and exit gauge, speeds and tensions through an
  acceleration and a speed change; drive torque or current for the torsional mode.

### 6.9 Product catalogue (`band_products.py`)

- **Best open evidence.** The standards already used; M1 (AA8079 9 um foil tensile data) and M2
  (AA1050, AA5182 curves) as measured anchors for strength entries; Öztürk & Şeherli 2019
  (6.35 um at 550 m/min) as one more published final-pass speed.
- **Gap.** Published schedules remain vendor and trade level; no open pass-schedule database.
- **Plant data needed.** The plant's own pass cards per product (gauges, speeds, tensions,
  roll roughness), and mill certificates for strength by temper.

---

## 7. Sources and read status

Datasets and repositories (verified to resolve through the repository API, a raw file fetch
or a page extract):

1. Zenodo 10685675, D4ASCR, https://zenodo.org/records/10685675 - LP + CSV header (first 3 kB).
2. Xiao et al., IEEE Trans. Ind. Inform. 2024, https://doi.org/10.1109/tii.2024.3390625 - AB.
3. Zenodo 8085933, https://zenodo.org/records/8085933 - LP. https://github.com/CuAuPro/opti-rec-sys - README EX, LICENSE seen (GPL-3.0).
4. https://github.com/DGlql/CRD - README FT; no LICENSE file.
5. Ayuba et al., Data in Brief 2018, https://pmc.ncbi.nlm.nih.gov/articles/PMC5996350/ - EX.
6. Univ. of Pretoria / Figshare 29877497, doi 10.25403/UPresearchdata.29877497.v1 - LP (API).
7. Zenodo 11469702, https://zenodo.org/records/11469702 - LP; https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2026.1770922/full - EX; https://github.com/jjakubow/pdm-steel-datasets - README EX.
8. IEEE DataPort PRESAGE, https://ieee-dataport.org/documents/presage-physics-anchored-digital-twin-hot-strip-mill-two-year-dataset-controlled - EX.
9. NBSDC Xi'an dataset via https://www.selectdataset.com/dataset/8dc3db8da3379d87e0e7ab7e8285ddee - SN.
10. Kaggle: `pandhuw/maximum-rolling-force-at-f1-for-steel-grade-ss400` EX; `ziya07/hot-strip-rolling-process-dataset` EX; `lukaszduss/vibration-data-from-rolling-mill` EX; `inancolak/machine-data-tpv10` EX (appears to be a polymer film extrusion, calender and winding line, not metal; no licence shown).
11. Zenodo 17493399 (SOMAR) - LP. Zenodo 2646505 (AA8079 foil) - LP. Zenodo 1339094 (Tibar & Jiang paper) - AB.
12. Mendeley `wcp8wrdhyj` - LP. AGH RODBUK doi 10.58032/AGH/SQEVDB - LP. Zenodo 6470217 - LP.
13. NPL TENSTAND, https://www.npl.co.uk/products-services/advanced-materials/tensile-testing - EX.
14. Tianchi APDDD https://tianchi.aliyun.com/dataset/148297 - EX. Figshare 32726052 - AB. IEEE DataPort APSDS-SR - EX. Fordatis 420 - EX. https://github.com/jsq0903/CR7-DET/ - README EX. https://github.com/zh-lv-94/SACV - README FT. Lv et al. 2023, https://www.sciencedirect.com/science/article/abs/pii/S0952197623012071 - AB.
15. https://github.com/pyroll-project/pyroll-core - README + LICENSE FT. https://github.com/francisflanagan/EJM_A_input_files - README + LICENSE FT. https://github.com/ErikHansenGit/EHL - README EX + LICENSE. https://github.com/a-dorgham/TriboSim - README EX + LICENSE. https://github.com/mahshadlotfinia/Stress316L - README EX. https://github.com/1500ssp-oss/timc-rolling-replay - README EX.

Papers and theses:

16. Boemer et al. 2021, https://orbi.uliege.be/handle/2268/261506 - AB. Boemer 2020 thesis, https://orbi.uliege.be/handle/2268/245441 - AB. Stephany 2008 thesis - EX (front matter). Carretta et al. 2011, https://orbi.uliege.be/handle/2268/90243 - AB.
17. Sutcliffe & Montmitonnet 2001, https://minesparis-psl.hal.science/hal-00574224v1/document - EX. Le & Sutcliffe 2001 (J. Tribol.) - AB. Tabary et al. 1996 - AB. Sutcliffe & Rayner 1998 - LP. Keife & Jonsäter, J. Tribol. 119 (1997) 349 - AB (**a simulation study of a Stribeck curve for foil rolling, not a measurement paper**). Sutcliffe 1989 thesis, https://www.repository.cam.ac.uk/handle/1810/244874 - AB.
18. Jiang 2011, https://www.intechopen.com/chapters/19449 - EX. Jiang & Tieu, Wear 263 (2007) 1447 - AB.
19. Öztürk & Şeherli 2019, TÜBİTAK - EX. Zhang et al. 2016, IET J. Eng. (in the project) - EX.
20. Hobbis, STLE 2017 slides - EX. Heenan & Januszkiewicz 2015 - AB. Christoforou, Mater. Sci. Forum 765 (2013) 373 - AB. Wang, Zhang & Ai 2023 - LP. Souto et al. (ABM) - AB. Song et al. 2013 - AB. Li et al. 2014 - AB. Yin et al. (ysxbcn.com paper 20302) - AB.
21. Kpogan et al. 2012, https://hal.science/hal-01868101v1/file/Kpogan2012.pdf - EX. Abdelkhalek et al., hal-00674953 - AB. Nakhoul 2014 - AB. Wang et al. 2022, Metals 12:1977 - EX. Malik 2007, https://corescholar.libraries.wright.edu/etd_all/137 - AB. Magne et al. 2022 - AB. Liu et al., Sensors 22 (2022) 656 - EX (describes a flatness dataset of 234,527 rows at 0.08 s from a steel tandem mill; no download link in the part read).
22. Niroomand et al. 2015, https://www.jstage.jst.go.jp/article/isijinternational/55/3/55_637/_html/-char/en - EX. Zhao 2008 (doi 10.21985/n2d444) and Zhao & Ehmann 2013 - AB. Vaidya et al. 2021 - SN. Usmani et al. 2018 - EX. Pérez et al. 2018 - EX.
23. Forrest 1999, https://shareok.org/handle/11244/321804 - AB; other SHAREOK items - SN. Weisz-Patrault et al. - SN. ISIJ Int. 64 (2024) 1037 - SN. Innoval winding blog - SN.
24. Ryen 2003, https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/244466 - SN (the handle page returned no content to the reader). Bacha et al. 2006 - SN. Strathclyde AA1050 - SN. TALAT index, https://aluminium-guide.com/talat-lectures/ - SN.
25. NIST cryogenic pages - SN. arXiv 2509.23422 - SN.
26. ASTM A1030 store page and Bailey Metal Processing note - SN. EN 546-4:2007 listing - SN. GB/T 22638.2-2016 preview - SN. ASTM B926 - SN.

From memory, not verified: Hockett & Sherby 1975; Severstal and GC10-DET image sets; ASTM D2578;
the status of MatWeb, MPDB and Total Materia as non-open.

## 8. Looked for and not found

Searches ran on Zenodo (API), Figshare (API), DataCite (API), GitHub (repository search),
Hugging Face (dataset search, no hits for "rolling mill", "cold rolling", "aluminum defect",
"hot rolling", "steel strip defect"), Kaggle and IEEE DataPort (through web search), plus
general web search.

- Any open dataset from an **aluminium foil mill** (force, speed, tension, gauge, flatness).
- Any open dataset with **shapemeter / flatness-roll channels**, for any metal. Several papers
  describe such data (steel tandem mills, 0.08 s sampling) and none releases them.
- Any open record of **roll surface temperature**, thermal crown, coolant zone states or
  spray flows on a cold mill.
- Any open **absolute spray heat-transfer coefficient** for kerosene on a rotating roll (only
  relative laboratory comparisons and the simulated value the project already holds).
- Open **vibration data from an aluminium mill**; the only open chatter set is a 20-high mill.
- Measured **interlayer pressure, stack modulus or ridge height** for aluminium coils.
- Machine-readable **flow stress against cold reduction** for 1235, 8011, 8079, 3003 or 5052
  beyond small-strain tensile curves.
- An image dataset of **aluminium strip or foil** rolling defects (the one strip set described,
  ASSDD, is not released; all public aluminium sets are extruded profiles).
- An open-source **flat-strip cold-rolling simulator**, foil bite solver, roll-stack / flatness
  code, chatter model, mixed-lubrication rolling solver, or Python wound-roll model.
- Rolling input decks for MOOSE, FEniCS or deal.II (only the Abaqus decks of item 15).
- An open copy of Sutcliffe & Rayner 1998, Le & Sutcliffe 2001 (J. Tribol.), Davies et al. 1975,
  Heenan & Januszkiewicz 2015 or Tabary et al. 1996 (all paywalled, all high value).
- The data behind Raftery, Kárný & Ettler's cold-mill thickness prediction work (19,058
  samples described in slides at https://stat.ufl.edu/wp-content/uploads/sites/120/rafteryTalk.pdf);
  whether it is distributed anywhere was not established.
- The variables and metal of D2, and the units, sampling rate and gauge of D1: not on the
  landing pages; the authors would have to be asked.
