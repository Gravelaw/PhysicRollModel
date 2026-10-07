# New fundamentals bibliography and implementation implications

2 October2026. These four deliberately selected works are a **new bibliography**, not a reconstruction of the historical fourteen-book list. A title/author/DOI check of the current identified source ledger found no duplicates. The unidentified historical cluster cannot be deduplicated by guessing titles and remains open. R149–R152 are used; reserved R153 is unused.

Exact identities, ISBNs, access failures and reviewed locations appear in [the source ledger](fundamentals-mechanics-source-reviews.json). Only R149 received substantive technical-section review. R150/R152 remain TOC-level; R151 has a read preface and chapter abstracts. None is claimed as a fully read book.

## What was actually accessible

| ID and work | Reviewed access | What it supports now |
|---|---|---|
| R149 Bower, *Applied Mechanics of Solids* | Author-hosted sections3.7.1–3.7.7,3.9.1–3.9.4,2.5.1–2.5.2,6.3.1–6.3.3 | Equation/convention review and scope of classical continuum assumptions |
| R150 Hosford/Caddell, *Metal Forming*,third edition2007 | Publisher TOC and chapter landing pages; preview images not inspected | An edition-specific acquisition/reading checklist; no chapter-level technical validation |
| R151 Altan/Ngaile/Shen,eds., *Cold and Hot Forging*,2005 | Publisher preface,TOC and selected abstracts | Characterization and process-variable research leads; no accessible parameter tables |
| R152 Lenard, *Primer on Flat Rolling*,second edition | Official detailed publisher TOC | Rolling-specific acquisition priorities; no read chapter equations |

R149's current [author text](https://solidmechanics.org/) is a mutable web version with2025 copyright, not an asserted page-identical copy of the2009 print edition. The author explicitly provides it freely. Its [small-strain plasticity treatment](https://solidmechanics.org/Text/Chapter3_7/Chapter3_7.php) distinguishes yielding, flow, hardening and unloading. The [finite-strain section](https://solidmechanics.org/Text/Chapter3_9/Chapter3_9.php) makes stress/kinematics conventions explicit. Small elastic strains do not imply small total deformation. These reviewed sections support the checks below; they do not supply alloy-specific calibration.

For R150, the verified [third-edition TOC](https://www.cambridge.org/core/books/metal-forming/DFD3C93FFFCB89A29076C55B8A4E1831) locates plasticity in chapter2,hardening in3,work balance in6 and slab/friction in7. Fourth-edition chapter numbers must not be substituted. Direct excerpt access failed, so citing the TOC as if its equations had been read would overstate the evidence.

R151's [official preface](https://dl.asminternational.org/technical-books/edited-volume/126/chapter/2327447/Preface) and [flow-stress chapter abstract](https://dl.asminternational.org/technical-books/edited-volume/126/chapter-abstract/2327799/Flow-Stress-and-Forgeability) identify useful characterization topics. R152's [official contents](https://shop.elsevier.com/books/primer-on-flat-rolling/lenard/978-0-08-099418-5) identifies material testing,tribology and model sensitivity as separate reading targets. Neither was used to fill an inaccessible numerical table.

## Concrete P1/P2 decisions

The following are project deductions and proposed acceptance criteria, cross-checked against actual repository functions/tests. They are not claims that a textbook validates the implementation.

| Concept | Current code/test evidence | P1/P2 decision and limitation |
|---|---|---|
| Equivalent plastic strain and plane-strain idealization | `materials.py:pass_with_history`, `BiteHardening.strain_at_thickness`; `test_v03.py:test_integral_and_history`; `test_contact_increment.py:test_history_spatial_work_and_refinement` | P1 retain explicit strain adapter. P2 fix source strain convention before fitting. No redundant shear,spread,elastic recovery or texture increment is inferred by this scalar formula. |
| Uniaxial strength versus plane-strain stress difference | `materials.py:BiteHardening`; `slab.py:strength`; `literature.py:simulate_schedule`; `test_contact_increment.py:test_constant_material_exact_limit` | P1 test conversion in both directions and work consistency. P2 do not apply the conversion twice when a source already reports a plane-strain difference. |
| Hardening as state,not a resettable label | `MaterialState`, `PowerHardeningLaw`; `test_v03.py:test_identification_and_constant_limit`; `test_contact_increment.py:test_speed_hypotheses_and_state_carry` | P1 maintain path/state provenance. P2 a fitted initial scalar is an effective parameter,not a measured dislocation density or annealing state. Kinematic hardening requires additional state and cyclic evidence. |
| Stress-power and volume conventions | `slab.py` force/torque/tension/friction work output; `test_mechanics_audit.py:test_work_identity_refinement_and_dimensions` | P1 declare deformed/reference volume and sign conventions; report all boundary power. P2 force agreement alone cannot validate power or temperature. |
| Independent limiting-case mechanics | `test_v03.py:test_constant_gap_analytic_ode_reference`; `test_mechanics_audit.py:test_independent_exponential_midpoint_pressure_reference`; `test_contact_increment.py:test_independent_variable_strength_pressure_reference` | Preserve independent analytic/quadrature checks. A bound calculation requires a compatible admissible field and assumptions; an arbitrary slab approximation is not automatically a rigorous upper/lower bound. |
| Characterization versus inverse fitting | `literature.py:simulate_schedule`, imported friction provenance; `test_literature.py:test_missing_history_and_speed_are_not_silently_filled` | P2 preserve no-fit benchmark,source assumptions and correlated holdout boundaries. Acquire independent material/contact information before adding adjustable coefficients. Book table values cannot replace named alloy/temper evidence. |

For a homogeneous incompressible monotonic plane-strain path, write the principal plastic increments as `(de,0,-de)`, where `de=d ln(h_in/h)`. Substitution into the reviewed J2 norm gives `d epsilon_eq=2/sqrt(3) de`; associated isotropic J2 flow gives the conjugate stress difference `K_ps=2Y/sqrt(3)`. Hence `Y d epsilon_eq=K_ps de`. This is a derivation for this idealized path, not a universal conversion for arbitrary shear or anisotropy. The current code's factors therefore have a defensible mathematical basis while its physical domain remains bounded.

The [work treatment](https://solidmechanics.org/Text/Chapter2_5/Chapter2_5.php) distinguishes current-volume Cauchy stress power from reference-volume alternatives and includes boundary work and kinetic energy. For the project's steady quasistatic approximation, dropping inertia must remain an explicit model choice. A positive dissipation result does not require every boundary drive torque to be positive: entry/exit tension work can change signed shaft demand. Thermal conversion requires its own partition/storage model.

The [limit-analysis chapter](https://solidmechanics.org/Text/Chapter6_3/Chapter6_3.php) derives bounds under rigid-plastic assumptions and admissibility conditions. Before using such a bound as a regression oracle, construct the same geometry,tractions,friction and material idealization. An upper bound on forming load is not a conservative lower bound on equipment structural capacity. The web text also contains apparent integral-measure/cross-reference slips; equations must be checked dimensionally,not copied mechanically.

## Why forging belongs in this research plan

Forging knowledge is relevant to **how material and interfaces are characterized**: compression/torsion tests,tool contact,temperature history and friction can influence an inferred flow law. This makes R151 a targeted access lead for independent characterization and experiment design. Its current abstract access supports that reading priority,not any specific correction formula or coefficient.

A rolling pass also has rotating contact,strip transport,tension boundaries,a neutral/slip structure and potentially repeated strip-layer interfaces. A press upset or die-fill load formula does not establish these features. Ring-test friction should not be relabelled as a rolling Coulomb coefficient without a matched definition and validated transfer. Likewise, a forging heat-transfer or forgeability range cannot become a cold-foil operating limit. Those restrictions are project applicability judgments; no unread forging chapter is asserted to contain a ready rolling law.

## Access backlog and stop conditions

1. Use the accessible R149 sections now for equation-level review and independently derived limiting cases. Pin the reviewed URL/date and chosen stress/strain convention. Obtain a numbered print edition only if stable page references are needed; do not claim exact web/print parity.
2. Acquire R150 third-edition chapters2,3,6,7 lawfully. Record the selected edition before assigning equation numbers; stop at TOC-level attribution until actual chapter text is reviewed.
3. Acquire R151 chapters3–7 first,prioritizing material testing and interface definitions. For any recovered aluminium table,record alloy,temper,test orientation,temperature,strain rate,strain measure and fit range before consideration in P2. No unauthorized author outreach was performed.
4. Acquire R152 chapters5,8,9,10 for model/material/contact discrimination; use chapter11 only for a deliberately selected hot-aluminium scope. Resolve the publisher's conflicting release-day metadata if exact dating matters. Cold rolling cannot inherit hot-aluminium parameters by title proximity.

These tasks improve scientific grounding without blocking source-explicit P1 verification or the conditional P2 replay already supported by accessible primary papers. No code,global ledger or roadmap was changed by this supplement; no book PDFs or images were committed.
