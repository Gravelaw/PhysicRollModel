# Independent review of the fundamentals supplement

Review date: 2026-10-02. Reviewer did not author the three supplements. Repository HEAD inspected: `ade4d1d0c4d5f8e6ca943ea1af9860446ead01d9`. Scope: source identity, access-depth classification, selected claim support, implementation references and scientific transfer limits. This is a research-document review, not certification of the simulator or authorization for deployment/control. No implementation was changed or tests rerun by this review.

## Findings and resolution

**F01 — SIAM book access depth.** The initial R161 record used `partial_text_reviewed` and combined publisher excerpts with author teaching slides. The independently opened [SIAM chapter 4 record](https://epubs.siam.org/doi/10.1137/1.9780898718836.ch4) labels the accessible opening and Eq.4.1 as **Abstract**, followed by access controls for the chapter. The mathematical expression is visible, but that does not establish access to the chapter body. The review requested an `abstract_only` book classification unless separate body access could be demonstrated, and a distinct identity for the independently reviewed lecture collection. Resolution and final counts are recorded below.

No other material scientific or bibliographic error was found in the inspected supplements. Missing access and unresolved dates are retained as limitations rather than filled from inference.

## Independent evidence checks

| Records | Check performed | Assessment |
|---|---|---|
| R149 | Opened Bower's author-hosted plasticity, work and bounding-theorem pages; checked publisher-indexed DOI/ISBN identity | Mutable web text is explicitly separate from page-identical print access. The plane-strain J2 derivation is valid for the stated incompressible monotonic isotropic path. No aluminium constants or unconditional load bound are claimed. |
| R150 | Opened Cambridge third-edition record | DOI, electronic ISBN and 2007 print/2012 electronic dates agree. TOC references remain metadata, and unread chapter equations are not invoked. |
| R151 | Opened ASM volume identity/contents | Editors, 2005 date, DOI and print/electronic ISBN agree. Preface/abstract access is conservatively classified; forging tests are proposed characterization leads, not rolling laws. |
| R152 | Opened Elsevier second-edition catalog | The conflicting December 4/December 12, 2013 dates really occur on the same page; preserving the discrepancy is correct. Detailed contents are not treated as reviewed chapter findings. |
| R154 | Independently searched official author index/citation/version records; direct citation-page fetch returned 502 | Sixth edition v6.00, April 19, 2024 identity corroborated. Metadata-only status is appropriate; no older-edition ISBN is silently reused. |
| R155/R156 | Opened official Elsevier title/TOC pages | Editions, author identities, ISBNs and publication dates agree. Light Alloys subtitle inconsistency and the annealing-book contents-numbering anomaly are visible at the publisher. Both remain acquisition leads. |
| R157 | Opened author-hosted published Raabe chapter; checked selected JMAK passage | Passage explicitly concerns isothermal nucleation/growth assumptions. The review's caution about arbitrary temperature histories and steel-to-aluminium constants is supported. It is one chapter identity, not a complete-book review. |
| R158 | Opened MIT teaching PDF; checked Biot definition and lumped approximation discussion | Body conductivity is distinguished from fluid properties. Selected teaching-text review is appropriately identified and is not a Lienhard textbook edition. |
| R159 | Opened Stanford author PDF copyright/TOC and section anchors | 2004 first publication and seventh corrected printing 2009 are confirmed; section 4.1.4 begins on printed p.136. Full PDF availability is correctly distinct from whole-book review. |
| R160 | Opened Springer identity and Analysis chapter | ISBNs, edition, DOI and publication dates agree. Chapter is pp.39–66; reported pp.39–58 are explicitly selected reading. Amplification versus monotonicity distinction is supported by accessible equations. |
| R161/R163 | Opened DTU author index/errata, DTU bibliographic record, SIAM chapter 4 and author chapter-4 slides | Book identity and errata provenance agree. Author slides are separate teaching material; slide numbering must not be used as book pagination. F01 records the access-depth correction. |
| R162 | Opened Cambridge chapter-5 summary | Publisher marks access-controlled chapter with an accessible summary; `abstract_only` and TOC-only procedure leads are appropriate. No unread verification formula is asserted to have been implemented. |

Authoritative inspection links are retained in each companion JSON. Additional directly checked pages include [Bower's plasticity](https://solidmechanics.org/Text/Chapter3_7/Chapter3_7.php), [Bower's bounds](https://solidmechanics.org/Text/Chapter6_3/Chapter6_3.php), [Springer Analysis](https://link.springer.com/chapter/10.1007/978-3-319-29439-1_2), [DTU book identity](https://orbit.dtu.dk/en/publications/discrete-inverse-problems-insight-and-algorithms/) and [Cambridge verification summary](https://www.cambridge.org/core/books/abs/verification-and-validation-in-scientific-computing/code-verification/733E362E9B977EA1E3745BF9FAF607A0). Checking these samples does not mean the independent reviewer reread every source section listed by the authors.

## Code and scientific traceability

Inspected `thermal.py`, the passive-contact closure in `energy_handoff.py`, material/state definitions and interpass temperature handling. Named mechanics tests in the supplement exist in the repository. Existing source files and test names are distinguished from proposed acceptance conditions; no absent anneal, texture, global optimiser or plant-calibration capability is asserted.

Independently rederived the constant-property passive-contact algebra in the numerics supplement. With `Cs=mdot*cp_s` and `Cr=Mroll*cp_r/dt`, both quantities have units W/K. The stated midpoint closure gives `Q=G*DeltaT/[1+(G/2)*(1/Cs+1/Cr)]`; in the fixed-roll limit the strip-rise ratio is `r/(1+r/2)`. Its overshoot for `r>2` is therefore a valid counterexample. Temporal refinement alone does not reduce `G/Cs`. This is a project-specific closure result, not a theorem imported from the scalar-decay textbook. The distinct `thermal.py` batch-capacity Euler step cannot validate the flowing-strip closure.

The proposed exponential plug-flow reference has explicit constant-property, fixed-reservoir and distributed-conductance assumptions. Entropy accounting, independent refinement and a justified replacement closure remain proposed work. Numerical conservation alone is not empirical thermal validation.

The mechanics derivation connects equivalent strain and plane-strain stress difference through plastic work under the stated idealization. It does not establish shear/texture corrections or finite-elastic unloading. The calibration discussion distinguishes fit residual, parameter identifiability and physical validation; local sensitivity rank is not global uniqueness. The optimisation discussion preserves the current conditional search's lack of a global certificate. These distinctions are appropriate.

## Acceptance boundaries

These are newly selected references. They do not identify or close the historical fourteen-book provenance gap U001. A book, a separately reviewed chapter and a teaching collection are different inventory classes. Complete public availability is not a whole-book-review claim. No copied book material or new code is needed to publish these original analyses.

The remaining limitations are lawful chapter access, unspecified mutable-web revisions, unreplicated numerical procedures, and absent alloy/mill calibration data. They are explicit research backlog items, not reasons to claim inaccessible content was reviewed. Final acceptance applies to the recorded files and access labels, with consolidated corpus integration/count checks owned by the parent task.

## Final acceptance and reviewed artifacts

**Accepted for documentation integration; F01 resolved.** R161 is now `abstract_only`, and the selected author lectures are separately inventoried as R163 with component locators and undated-version limitations. Both JSON and prose were reread after the correction. No unresolved publication-blocking finding remains within this review scope.

The three supplements contain **14 new source identities: 11 books, one book chapter and two teaching resources**. Status counts are **6 partial-text, 5 metadata-only and 3 abstract-only**. Of the 11 books, 3 have selected substantive body review, 5 metadata/contents access and 3 abstract/summary access; none is claimed to be a completely reviewed book. R153 remains intentionally unused. These counts describe this supplement only; they must not be confused with the historical fourteen-book cluster or added to the corpus without parent reconciliation.

All supplied ISBN-13 values passed checksum verification; primary URLs and access dates are populated; IDs are unique. Targeted authoritative links were inspected as described above; this is not a claim that every secondary locator returned HTTP200. The final reviewed six files have these SHA-256 hashes:

| File | SHA-256 |
|---|---|
| [fundamentals-mechanics-review.md](fundamentals-mechanics-review.md) | `9763256fb815f805ef5cb2810e4f613be20dedd900124ac7a259ffc1a16c1c76` |
| [fundamentals-mechanics-source-reviews.json](fundamentals-mechanics-source-reviews.json) | `32aa80978fa38e399dcbe6abbd7eeac16d6607540d044d3b85a752b2fb69f8e5` |
| [fundamentals-materials-thermal-review.md](fundamentals-materials-thermal-review.md) | `1f59027808defe900f9c611601522fc3d8eabcc4ac016fd0778c3184912d3735` |
| [fundamentals-materials-thermal-source-reviews.json](fundamentals-materials-thermal-source-reviews.json) | `4955376d1b2968b51806a424891e8291ab277cf0a76ac29f43f7eab49d3b82f8` |
| [fundamentals-numerics-optimisation-review.md](fundamentals-numerics-optimisation-review.md) | `40c1679225622378a2fa385dab759b757b1e05fcf898bee4862e8d3482ab4297` |
| [fundamentals-numerics-optimisation-source-reviews.json](fundamentals-numerics-optimisation-source-reviews.json) | `322ca18e16a38e0ecf534c1075a49d31737f4d5bd13cf80409923e15ae11057b` |
