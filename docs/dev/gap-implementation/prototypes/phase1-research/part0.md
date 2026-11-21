# Phase 1 equations: what the reports cite by number or name, found and transcribed

Written 2026-11-19 for the planner of SPEC18. Scope: the equations and constants that
`gap-bite-tribology.md` and `gap-thermal-material-dynamics.md` cite without giving. Nothing under
`/home/user/PhysicRollModel` was changed. Scratch scripts: `scratchpad/s24/scripts/`; downloaded
files: `scratchpad/s24/dl_*`.

How to read the tags

- Read status of a source (section 8), never upgraded: **FT** full text read (the part read is
  stated), **EX** excerpt, **AB** abstract or snippet, **VP** vendor, trade or teaching page,
  **CIT** seen only as a citation inside another source.
- `[derived]` = computed or inferred here, with the derivation or the script named;
  `[from memory]` = recalled without a source, not verified; "as printed" = transcribed although
  it looks wrong, with the reason given beside it.
- Equation numbers are the source's own. Where the equation was read from a page image the text
  says so; where it came through a text extraction that lost symbols, the lost part is marked.

## 0. Summary

| # | Item | Status | Sources (read tag) |
|---|---|---|---|
| 1 | Fleck et al. (1992) governing set: (1)-(16), (17)-(20), (21)-(29), (30)-(32), (33)-(36), Appendix 3 (37)-(42), zone structure, matching conditions, Fig. 9 inputs | **Found in full.** Three misprints flagged ((20), (30), (36)). | E1 FT; E2 FT (5 pages) |
| 1a | What explains 92.9 against 118 | **Answered in part, by the source and by a numerical check.** Not eqs (10)-(14) (the source says so). Not zone E (load changes by under 0.3 %). The load of the printed model depends on how the bite ends are closed: 88 to 135 for end lengths 21 to 2.5 um. The plotted Fig. 9 curve corresponds to about 102 to 105, not 118. | E1 FT; E6 FT; `[derived]` C4 |
| 1b | Le & Sutcliffe (2001) robust model; Dbouk; Krimpelstaetter | **Not found** beyond abstracts. Sutcliffe & Montmitonnet friction regularisation and Table I in part. | E3 AB; E4 EX |
| 2a | Asperity crushing functions | **Found in full** for Wilson & Sheu's fit, the Sutcliffe/Marsault form, the Korzekwa regression by Sutcliffe, and Sutcliffe's own fit (thesis eq. 3.20); the two "Sutcliffe" forms disagree and are reconciled only at one point. Originals of Wilson & Sheu and Sutcliffe (1988) not read. | E5 FT; E6 FT; E8 EX |
| 2b | Patir-Cheng and Wilson-Marsault flow factors | **Found in full** as fitted by Marsault and printed by Boemer; originals not read. | E5 FT |
| 2c | Inlet analysis (Sutcliffe & Johnson type): Reynolds equation with roughness, hardness condition, yield condition, crushing in the deforming inlet, film formula; a published table of film and contact ratio against speed for the Fig. 9 foil case | **Found in full** from the thesis. | E6 FT |
| 2d | Boundary friction `mu_c(h_s, r)` for aluminium | **Found in part**: method, materials, oils, range, trend; the fitted curve is only a figure. Alternative from the thesis: boundary shear strengths at three pressures. | E7 FT (manuscript); E6 FT |
| 2e | Two-wavelength roughness | **Found in part**: structure and the numbers of one case; the crushing law of the two scales is in a paper not read. | E7 FT (manuscript) |
| 3a | Roelands law with constants and units | **Found in full** (as derived from Roelands' thesis by Boemer). | E5 FT |
| 3b | Eyring relation, Eyring stress, limiting shear stress for rolling oils | **Found in full** for a kerosine foil-rolling base oil without additives (Somentor 31): viscosity table, pressure coefficients, Eyring stress at three pressures, no limiting shear stress up to 0.045 of the pressure. Three mineral oils in part. | E6 FT; E7 FT |
| 4 | Rate- and temperature-dependent flow stress of 1xxx / 8xxx at large strain | **Not found** for foil alloys. Law forms and constants for pure Al, Al-0.2Cu, Al-Mg (bulge test, strain below about 1) and annealed 1050 / 1100 only. | E10 EX; E11 EX; E17 EX; E18 EX |
| 5 | Interface conductance: oil film plus asperity term | **Found in part**: the parallel form and one asperity correlation from a preview; the Cooper-Mikic-Yovanovich correlation from teaching pages; Tseng's papers as abstracts. Oil conductivity values found. | E12 AB; E13 VP; E14 AB; E6 FT |
| 6a | TM-LC7 chatter benchmark inputs | **Found in full** (all tables and the process-model equations). | E9 FT |
| 6b | A fully specified aluminium foil case with measured load, slip and gauge | **Not found.** The only measured foil point remains Fleck's Fig. 8 (roll radius not stated). | E1 FT; E15 AB |

The single most useful result is 1a.

---

