# Newly selected material and thermal fundamentals

Audit date: 2026-10-02. This supplement adds three book identities, one separately identified published book chapter and one official teaching reference. It does **not** reconstruct the missing historical fourteen-book list: unresolved provenance record U001 remains open. No title/author match was found in the existing consolidated source ledger for these selections. The root inventory owner reconciles final IDs and counts.

## Access and identity

| ID | Exact selected reference | Actual review depth |
|---|---|---|
| R154 | Lienhard V and Lienhard IV, *A Heat Transfer Textbook*, sixth edition, v6.00, 19 April 2024, Phlogiston Press | Author-site/indexed metadata and contents only; PDF access failed. Sixth-edition ISBN/DOI not established |
| R155 | Polmear, StJohn, Nie and Qian, *Light Alloys: Metallurgy of the Light Metals*, fifth edition, 29 March 2017; ISBN 9780080994314 | Official publisher contents and bibliographic description only |
| R156 | Humphreys, Rohrer and Rollett, *Recrystallization and Related Annealing Phenomena*, third edition, 24 July 2017; ISBN 9780080982359 | Official publisher contents and bibliographic description only |
| R157 | Raabe, chapter 23 in *Physical Metallurgy*, fifth edition, 2014, pp.2291–2397; DOI 10.1016/B978-0-444-53770-6.00023-X; book ISBN 9780444537706 | Substantive selected sections of the author-hosted published chapter |
| R158 | MIT OpenCourseWare, *Part 3: Introduction to Engineering Heat Transfer*, 16.050, Fall 2002 | Selected institutional teaching-text sections; explicitly not a book |

The [structured ledger](fundamentals-materials-thermal-source-reviews.json) pins direct links, locators, access limitations, material domains and code/test mappings. Counts are three metadata-only records and two partial-text reviews; none is a claim to have read a whole textbook. No copyrighted source file or illustration is included in the repository.

## Observed coverage and reading priorities

**R154 is a verified access lead.** The author's [citation page](https://ahtt.mit.edu/bibtex-entry/) identifies the sixth edition and the [contents](https://ahtt.mit.edu/table-of-contents/) identify transient conduction and lumped-capacity treatment. The lawful PDF and an older institutional copy could not be fetched in this environment. The fifth-edition ISBN surfaced in search but was not assigned to the sixth edition. No unseen chapter equation supports this audit; use R158's accessed derivation for the immediate verification work.

**R155 provides the aluminium-specific acquisition map.** The [official contents](https://www.inspectioncopy.elsevier.com/book/details/9780080994314) identify §2.1 work hardening/annealing, §§2.2–2.3 age hardening, §2.5 mechanical behaviour and §§4.2–4.4 wrought-alloy/temper families. These are reading targets, not reviewed technical findings. Obtain those sections before citing this book for a material law. The inspected title heading and ISBN resolve the subtitle inconsistency in the publisher's description.

**R156 provides the broader recovery reading map.** The [publisher contents](https://shop.elsevier.com/books/recrystallization-and-related-annealing-phenomena/rollett/978-0-08-098235-9) separate recovery, single/two-phase recrystallisation, dynamic restoration, continuous recrystallisation and measurement. The shop's jump from chapter 15 to 18 is retained as an unresolved contents anomaly. This third edition's authorship differs from earlier editions; do not merge them by title alone. Full chapters remain an access need.

**R157 provides substantive mechanism and fidelity evidence.** Selected [published chapter sections](https://www.dierk-raabe.com/app/download/5801853763/Dierk%2BRaabe%2Boverview%2Brecrystallization.pdf) distinguish microstructure prediction from deriving strength from that microstructure. The accessed isothermal JMAK discussion assumes particular nucleation, growth and homogeneity conditions; arbitrary temperature histories require additional justification. The general/steel examples do not furnish aluminium parameters. For this project, retain measured treatment events until independent kinetics and post-treatment flow curves exist. Spatial models add inputs and calibration demands, not automatic confidence.

**R158 supplies an accessible thermal derivation.** The [MIT text](https://ocw.mit.edu/courses/16-050-thermal-energy-fall-2002/87d9f4544b7fd64a77201382500d057c_10_part3.pdf), §§3.2–3.3 and 6, relates conductivity, area, resistance, heat capacity and the small-Biot approximation. Its constant-property reservoir cooling limit is a useful verification oracle. It does not identify rolling contact coefficients or prove the admissibility of the project's finite-capacity contact step.

## Project decisions and test mapping

The following are project-authored requirements and proposed work, not claims that these books already validate the implementation.

| Phase / decision | Current code/test target | Concrete action and acceptance |
|---|---|---|
| **P1: distinguish model meaning from numerical success**; R154 acquisition target and accessed R158 | `physicroll/thermal.py`; `physicroll/energy_handoff.py`; `tests/test_passive_contact.py`, `tests/test_energy_handoff.py` | Declare body versus fluid properties, characteristic length and heat-transfer area. Track heat flux in W/m², conductance in W/K and power in W separately. Label lumped applicability rather than assuming it from thin gauge alone |
| **P1: close passive-contact defects**; R158 supports basic limiting case | Same thermal modules and tests | Add independently derived finite-capacity reference cases, long-step temperature bounds, equal-temperature equilibrium and global entropy checks. Repeat for unequal and temperature-dependent capacities. Passing the reservoir test alone cannot close the parent audit's two-body overshoot issue |
| **P1: retain material-state semantics**; R155/R156 reading targets, R157 selected mechanism sections | `physicroll/materials.py`: `MaterialState`, `PowerHardeningLaw`; `tests/test_v03.py` | Keep synthetic hardening explicitly synthetic. Reserve separate named state fields/events for observed or modelled treatment changes. A temperature assignment must not silently reset accumulated strain or claim recovered/recrystallised state |
| **P2: freeze benchmark treatment provenance**; R155/R156 acquisition map, R157 mechanism caution | `physicroll/schedule.py`; `tests/test_schedule.py`; material adapters | Record alloy, temper, prior processing and whether each new curve is measured at pass entry or predicted from previous state. Do not infer annealing kinetics from separately fitted per-entry curves |
| **P2: preserve output-specific validation**; R158 thermal scope | Benchmark residual/observation contract | Force agreement validates neither temperature nor heat partition. Keep measured thermal targets distinct from model estimates and supplied boundaries |
| **P3/P4: select minimum identifiable kinetics**; R157 | Future material/interpass module; no current implementation asserted | Start with a bounded identified reduced model. Escalate to spatial texture/microstructure models only when required output errors and available observations justify them. Require held-out time-temperature histories and post-treatment measurements before predictive anneal scheduling |

A thermally admissible numerical scheme can still have incorrect boundary coefficients; a correct constitutive fit can still lack a predictive treatment model. Maintain separate numerical verification, parameter identification and independent validation gates. The immediate P1/P2 plan is strengthened by these fundamentals, while the unchanged access register makes clear what further chapter-level evidence is needed.
