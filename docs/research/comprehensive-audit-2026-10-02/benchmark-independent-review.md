# Independent benchmark and calibration-contract review

Review date: 2026-10-02. Scope: nine candidate source identities, fresh primary-source checks and scientific review of the proposed calibration contract. This document contains original analysis, not a completed calibration, simulation, source-code review or declaration of plant readiness. See [the structured source reviews](benchmark-source-reviews.json) for exact access depth. No paper, book or figure is redistributed here.

## Decision

Retain **Shao 2015 AA5052, 4.10 → 2.9024 → 2.2087 → 1.72 mm**, as the first conditional force/slip comparison. It is sufficiently relevant to test a current-model adapter, but insufficient for independent validation. Keep **Szűcs 2020 .028** as a conditional force/torque reserve. No candidate independently checked here establishes a completely specified, independent measured multipass load benchmark. This finding covers these candidates; it is not a claim that no such dataset exists anywhere.

The user’s 6 mm → 0.05 mm route was illustrative. Evidence coverage and model applicability should select the first sample. A strip benchmark cannot certify a foil or pack route. Leave deployment targets open, as requested by the user; benchmark selection does not decide deployment architecture.

## Fresh primary checks

[Shao’s publisher text](https://iieta.org/journals/ijht/paper/10.18280/ijht.330113) independently confirms the reported force/slip table, Table 1 radius versus Eq. 6 diameter conflict, and the unspecified Eq. 3 history weight. The source’s ±5% compares its predictions with observations; it is neither sensor uncertainty nor a project acceptance limit. Its thermal plots are calculations. The supplied initial state remains unresolved.

[Szűcs .028](https://real.mtak.hu/221794/1/ISSN_2063_6792_vol_45_1_2020_eng_271-283.pdf), Table 3, printed p. 273, was independently read from the primary PDF text. This is the complete three-row table, with source-reported values separated from calculations:

| Pass | Entry → exit, mm | Measured force, kN | Reported measured torque, Nm | FE force, kN | FE torque, Nm | Roll speed, m/min |
|---|---|---:|---:|---:|---:|---:|
| 1 | 6.80 → 5.23 | 243.43 | 2736 | 310 | 2350 | 15 |
| 2 | 5.23 → 3.80 | 293.18 | 3250 | 340 | 1950 | 15 |
| 3 | 3.80 → 2.74 | 292.85 | 2760 | 310 | 1600 | 28 |

The paper derives friction from these loads and assumes cooling to 20°C after each FE pass. Unknown experimental tension is not measured zero tension. The torque label does not establish a per-roll or combined convention. These are substantive reasons against calling this an independent validation case.

Independent arithmetic on that table, using `(FE − measured)/measured`, gives force residuals **+27.35%, +15.97%, +5.86%** and torque residuals **−14.11%, −40.00%, −42.03%**. These describe the source's displayed predictions, not a run of this project. They show why the source's measured table and the quality of its model agreement must be judged separately.

For [Szűcs .029](https://real.mtak.hu/221795/1/ISSN_2063_6792_vol_45_1_2020_eng_284-294.pdf), pp. 287–290 confirm AA5754, 4000 N front/back tension, different speeds, inverse fitting of friction, and a nominal schedule whose actual exit thicknesses differed because of mill elasticity. A nominal gap is not a measured gauge. Fresh text access did not resolve pass-to-graph mapping or visually verify the graph axis; the parent’s force-axis warning remains inherited evidence, explicitly flagged in the ledger.

[Bátorfi 2022 author-deposited primary text](https://www.researchgate.net/publication/366244683_Models_for_symmetric_cold_rolling_of_an_aluminum_sheet) confirms the single AA1050 2 → 1.4 mm experiment, a tensile-derived material law and friction fitted against measured deformation lines. It is useful for evaluating strain fields and strain conventions; those fitted deformation lines cannot simultaneously be independent friction validation.

[Olaogun’s official thesis text](https://ujcontent.uj.ac.za/view/pdfCoverPage?download=true&filePid=135875450007691&instCode=27UOJ_INST) independently confirms separate per-entry flow curves, the four-pass schedule, conflicting initial-temperature descriptions and the predicted status/unit-label inconsistency of Table 4-25. It merits later thermal/history investigation, with raw measured loads still needed.

## Revisions to the proposed calibration contract

The proposed one-parameter fit is a defensible **conditional experiment**, with the following additions. These are reviewer recommendations, not claims that the source performed these checks.

1. **Freeze an adapter before fitting.** Preserve raw observations and unknowns. Name the mechanics solver, contact model, strain/stress conventions, elastic constants, speed interpretation, history propagation, fitting target and parameter bounds in a versioned manifest. Record bounds as assumed unless independently measured. Current `PowerHardeningLaw` permits a zero offset, but that algebraic compatibility does not reproduce the source’s history model. Its validator currently requires `synthetic=True`; fitting one conditional case does not produce an independently calibrated material card or justify clearing that provenance flag.
2. **Transform a changed strain coordinate consistently.** In the inspected code, homogeneous plane-strain increments are `2/sqrt(3) * ln(h_in/h_out)`. If a published law is assumed to use logarithmic thickness strain, its strength coefficient and initial state must transform with the coordinate: for `epsilon_eq = c * epsilon_log`, `K_eq = K_log / c**n`. Copying K unchanged while changing strain is a different material law, not an innocuous unit conversion. The stress-to-shear/plane-strain mapping is a separate choice. Compare named hypotheses without declaring either the recovered source truth.
3. **Check identifiability before calling the parameter physical.** With one force target and fixed nuisance assumptions, the scalar fit may locate an effective hardening offset, but it cannot independently distinguish entry hardening from friction/contact/material-law bias. Inspect objective shape, numerical convergence and sensitivity to each unresolved convention. If many offsets fit equally well, report a set or interval. Label the result an effective initial-hardening parameter, not measured incoming strain or temper.
4. **Use admissibility as a gate.** Nonnegative strain alone is insufficient. Verify local entry/exit strength exceeds tensile boundary stress, the declared material envelope covers every pass, and the mechanics solution remains admissible throughout the parameter search. With a zero-offset power law, zero incoming strain can imply zero incoming strength and fail tension admissibility. Do not silently add a yield offset, clip tension or widen bounds to force a fit. A boundary optimum is a diagnostic to report.
5. **Freeze held-out comparisons.** Fit only pass-1 force. Leave pass-1 slip as an unfitted cross-output diagnostic. Preserve pass-2/3 force and slip as within-chain withheld outputs, with inherited state and friction leakage disclosed. Their observations are already public and have informed case selection, so “blind” is inappropriate. Do not tune assumptions after inspecting errors without registering a new exploratory experiment. Reusing them to choose a preferred convention consumes them as validation evidence.
6. **Report errors rather than manufacture a tolerance.** Report signed dimensional and relative force residuals, absolute slip-fraction residuals and percentage-point slip residuals, plus relative slip residuals with the denominator shown. Small slip denominators can inflate relative errors. Propagate assumed-input sensitivity separately from measurement uncertainty; missing sensor uncertainty remains null. Do not interpret a three-pass residual range as a statistical confidence interval.
7. **Separate numerical and empirical acceptance.** Extraction continuity, dimensional consistency, repeatability and mesh/solver convergence can pass with explicit numerical thresholds. Physical agreement is graded and provisional until observation uncertainty and intended use supply defensible error limits. A mismatch is a successful discovery if faithfully reported; the project must not fit per-pass material strengths or friction to erase it.
8. **Require an independent next experiment before validation promotion.** Obtain another coil or test campaign with independently characterized incoming material, friction information, synchronized per-pass settings, actual gauges, force/slip measurements and uncertainty. If torque is included, require shaft location, sign, per-roll/combined convention and losses. Group train/test splits by coil or campaign, not adjacent samples from one trace.

## Evidence-backed sample portfolio and stop conditions

| Priority | Sample and purpose | Progress possible now | Stop before claiming |
|---|---|---|---|
| 1 | Shao AA5052, conditional three-pass force/slip experiment | Adapter/convention manifest; admissibility and sensitivity design; immutable observations | Independent material/friction validation, thermal validation, certified limits |
| 2 | Bátorfi AA1050, single-pass deformation-field experiment | Review strain definitions and field quantities against the tensile-informed setup | Load-chain validation; independent validation on friction-fitting lines |
| 3 | Szűcs .028, exact three-pass force/torque reserve | Data schema and conditional replay design | Physical torque comparison until its convention is resolved; independent validation using load-fitted friction |
| 4 | Dalarna 2011, potential single-pass force/slip sweep | Preserve inherited lead and obtain lawful accessible full text | Fresh audit or multipass-history claims; access failed in this review |
| 5 | Olaogun AA8015, thermal/history reserve | Investigate separate material curves, thermal conditions and measurement provenance | Propagated scalar-history validation or numerical measured loads from a predictions table |
| 6 | Safarov 1050, process topology; Scientific Reports 2026 AA1050, microstructure | Plan distinct topology and microstructure tests | Load calibration from either source; universal annealing/foil evidence |
| Quarantine | Szűcs .029 graph mapping; Choi 2026 inherited tension-unit concern | List missing quantities and exact clarification needed | Numerical benchmark use until ambiguities are independently resolved |

Yang 2012 remains a weaker load-chain reserve because its per-pass tensions and speeds are ranges; its dynamics discussion is a separate future topic. No numerical steel material card, unspecified temper, manufacturer equipment capacity or arbitrary production route is introduced by this portfolio. Choi was not freshly reviewed in this bounded assignment and is not counted among its nine source records.

## Implications for the bounded schedule search

The parent reports a search foundation that replays complete routes through checked scheduling and retains rejections. Such semantics are scientifically appropriate **provided the output remains a ranking of candidates satisfying the explicitly configured checks**. A nonviolating route is not certified feasible, safe, optimal beyond the enumerated grid, or experimentally validated. This review did not run that branch.

Changing gauge changes accumulated state and may change friction, slip, thermal conditions and admissible settings. Keeping published per-pass friction, tensions and speeds fixed during alternative-gauge search is an explicit scenario assumption; fitting one reported route does not validate those counterfactual schedules. Keep model-domain limits, numerical failure, unassessed data and equipment-limit violations distinct. A solver failure must not become a low-cost route, and an unassessed constraint must not become a passed one.

The next science milestone is therefore the frozen conditional adapter and sensitivity/identifiability report. The next engineering milestone is reproducible evaluation and retention of its provenance and rejection reasons. Promotion to robust optimisation requires independently supported uncertainty sets and pass-local allowable controls/equipment ratings. Those datasets and ratings remain unavailable here; a successful synthetic search test cannot supply them.

## Review boundaries and access reconciliation

Nine identities are accounted for in the JSON. Eight yielded full primary text from which the listed relevant sections were substantively reviewed; this does **not** mean eight entire publications were exhaustively reread. One, Dalarna, remained freshly inaccessible. Three primary sources required alternative lawful delivery: Bátorfi author upload, and Nature/Olaogun official content through Exa. The Nature article was available as full extracted text; the thesis was inspected at relevant sections rather than read cover to cover. No fresh visual inspection is claimed: browser screenshot calls returned references without viewable images in this execution environment. Consequently graph-only quantities remain unextracted, and text-derived tables retain that access qualifier.

The parent’s earlier full-text extraction and visual review are separate provenance, never relabelled as this reviewer’s own access. Raw PDFs were not added to the repository. JSON schema fields, nine identities, DOI uniqueness, URLs and the complete .028 table transcription were checked structurally; live availability is recorded per source, not inferred from URL syntax. No model simulation, fit, source-code change, commit or push was performed by this reviewer.
