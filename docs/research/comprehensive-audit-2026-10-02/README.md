# Comprehensive evidence audit and end-to-end roadmap

Research date: **2 October 2026**. Audited main: [`caec37ef86a8b78e1eb88292ea6368bfb64bcbdc`](https://github.com/Gravelaw/PhysicRollModel/tree/caec37ef86a8b78e1eb88292ea6368bfb64bcbdc). Dedicated documentation branch: `research/comprehensive-evidence-roadmap-2026-10-02`.

## Executive findings

Build the next scientific milestone around checked multipass replay and a frozen, conditional AA5052 comparison. Prioritize source semantics, material identifiability and independent measurements before broader scheduling or extra physics. Preserve material state, equipment configuration, commanded settings, observed signals and pass-local bounds separately. The illustrative 6 mm → 0.05 mm route is not a required test case.

The code has more than the original heuristic: optional spatial hardening, tension-aware slab, circular contact, thermal ledgers, checked pass chains and a narrow gauge search. It remains uncalibrated. **86 baseline tests pass**, as do smoke and Blender structure checks; optional OpenUSD verification is blocked by missing `pxr`. Independent review reproduced a finite-roll thermal overshoot with negative whole-step entropy and a separate flowing-strip overshoot that persists as the time interval shrinks. The [thermal handoff](thermal-numerical-handoff.md) separates unchanged-law guards from time integration and spatial contact-model revisions. Stored ordinary thermal demos were freshly reproduced within their bounded synthetic claims; no plant validation is implied.

The separate bounded-search candidate at [`ef0996acdd7af1799c62cb9a2e628e35acd26206`](https://github.com/Gravelaw/PhysicRollModel/tree/ef0996acdd7af1799c62cb9a2e628e35acd26206) passes **91 tests** and an additional real checked-replay integration probe. It remains a finite-choice scaffold with indeterminate physical feasibility. It is not merged here. Parent-reported uncommitted benchmark drafts are not counted as published capability.

No public case was verified as a complete independent calibration/validation fixture for the present model. Shao's three AA5052 force/slip pairs are useful conditionally; initial history, strain/stress mapping, speed, radius wording and friction reuse remain unresolved. Choi tension inputs remain quarantined. The roadmap compares alternatives through offline simulation, calibration, scheduling, UI/3D, packaging, advisory deployment and eventual read-only plant integration. **The user leaves deployment options open. All subsequent development stays in Codex cloud after this research.** A local-first offline package is a portability recommendation, not a selected deployment or permission to deploy. Live control requires a separate authorized safety/controls programme.

The supplement adds a [new fundamentals bibliography](fundamentals-review.md), [targeted P1/P2 access review](p1-p2-access-priorities.md), and [operational-phase requirements](operational-phase-review.md) grounded in primary papers and OEM documents. Threading/bite, ramp-up, settled rolling, length-triggered deceleration and tail/reversal now enter core schema/data/dynamics gates P1/P3/P4D, not just the UI. Recipe targets, applied references, actual trajectories and model eligibility/adaptation are separate. A steady solver sampled along a speed ramp is not a validated dynamic simulator.

## Actual corpus reconciliation

The scan covers **140 tracked source-bearing files**, including both DOCX and PDF representations, code/scenario provenance and newer notes. It resolves **178 distinct external URL/DOI locators** and 450 file/locator pairs. Different locators and versions are not counted as different works.

* **146 distinct source identities already occur in the baseline:** 135 technical sources plus 11 secondary vocabulary/orientation pages. The original 105 numbered entries are a subset.
* **36 additional identities** were added by this research: 13 in the first published package, 14 newly selected fundamentals references, and 9 operational-phase references. All 159 identities from the first publication are retained with the same IDs. Five existing records gained deeper access in the targeted P1/P2 review.
* **182 total ledger identities:** 171 technical and 11 orientation. The technical set comprises 84 scholarly publications, 2 theses, 3 dataset/repository records, 48 OEM/industry documents/pages, 14 official software references, 1 SI standard, 1 official security-guidance reference, 3 teaching resources, 2 patents, 1 video, 11 books and 1 separately identified book chapter.

Every technical identity has an individual current review/access record. This does **not** mean every source was read in full. The greatest current access depth per identity is:

| Current depth | Count |
|---|---:|
| Full text substantively reviewed | 16 |
| Partial text / selected substantive sections | 37 |
| Relevant official document sections | 57 |
| Primary abstract only | 34 |
| Metadata/identity only | 21 |
| Current access unavailable | 6 |
| Secondary orientation, no new technical reliance | 11 |
| **Total** | **182** |

The scholarly-plus-thesis subset has 15 full, 28 partial, 30 abstract-only, 12 metadata-only and 1 unavailable current record. These are access-depth counts, not quality scores. A paper with a fresh full-text record can still lack raw data, independent validation or usable material constants. Official-document counts include product/README sections, not audited dataset files. The machine ledger preserves **all** reviewers' complementary findings, versions, locators and conflicts; the compact depth is only a counting convention. Historical report access is retained separately, so a failed current fetch does not erase an earlier review.

**Unresolved historical completeness:** the handoff mentions 14 book leads, but their identities were not found in the saved repository, targeted Library retrieval or the parent's subsequent room-history check. U001 stays open and its unverified cardinality is excluded. The new replacement selection is **11 books, one chapter and two teaching resources**, with six partial-body, five metadata/TOC and three abstract/summary records; **zero whole-book reviews**. It is not recovered history. These references support bounded next steps while source-specific access/data gaps remain explicit.

## Read and use the deliverables

| Need | Deliverable |
|---|---|
| End-to-end decisions, dependencies and phase gates | [Roadmap](roadmap.md) |
| Prioritized science versus engineering tasks and next milestones | [Gap register and backlog](gaps-and-backlog.md) |
| Validation, packaging, target options and advisory/live-control boundary | [Validation/deployment checklists](validation-and-deployment-checklists.md) |
| Every source, current/historical access, findings and conflicts | [Annotated inventory](annotated-source-review.md), [JSON](source-ledger.json), [CSV](source-ledger.csv) |
| Actual code, units, tests, thermal counterexample and separate scheduler review | [Implementation audit](implementation-traceability.md), [52-row traceability](traceability.csv) |
| Mechanics, contact, foil and numerical methods | [Contact review](contact-review.md) |
| Hardening, rate/temperature, annealing, heat and material quality | [Materials/thermal review](materials-thermal-review.md) |
| Sensors, alignment, stack, crown/profile/flatness, OEM scope | [Sensing/profile review](sensing-profile-review.md) |
| ML, identifiability, data, constrained/robust optimisation | [Optimisation/data review](optimisation-data-review.md) |
| Independently checked calibration contract and alternative datasets | [Benchmark review](benchmark-independent-review.md) |
| Pass-history/texture, route, teaching and patent sources | [Supplemental route review](supplemental-route-review.md) |
| New textbook/fundamentals review and unresolved U001 | [Fundamentals index](fundamentals-review.md), [independent review](fundamentals-independent-review.md) |
| Immediate P1/P2 access blockers and lawful alternatives | [Targeted access priorities](p1-p2-access-priorities.md) |
| Thermal defect, corrective alternatives, ordinary demos and acceptance | [Numerical handoff](thermal-numerical-handoff.md), [demo evidence](thermal-demo-checks.json), [independent check](thermal-handoff-independent-review.md) |
| Core operational phases, model activation and dynamic-state planning | [Operational requirements](operational-phase-review.md), [primary papers](operational-papers-review.md), [independent requirements review](operational-independent-review.md), [independent paper review](operational-papers-independent-review.md) |
| Scope, identity, copyright and user decisions | [Audit contract](audit-scope.md) |
| First publication review (159-source snapshot) | [Historical review record](independent-review.md) |

All source review JSON files are original project annotations. No full copyrighted paper, book or manufacturer artwork is committed. Existing Word/PDF reports and implementation history are preserved unchanged. This Markdown/CSV/JSON delivery is intentionally editable and diffable; it does not replace the historical 53-page report.

## Rebuild and verify

From the repository root, run:

```bash
python docs/research/comprehensive-audit-2026-10-02/build_inventory.py
python docs/research/comprehensive-audit-2026-10-02/validate_audit.py
```

The inventory reader uses Python 3.12.14 and `pypdf` 6.10.0 in this saved environment; it reads immutable baseline Git objects and authored review records, with no network or model mutation. `source-counts.json`, `citation-occurrences.csv` and `baseline-files-scanned.json` make counts reproducible. `validation-results.json` records structured-data/link/count checks. Source retrieval outcomes are documented per entry; a syntactically valid or identified URL is not claimed universally reachable. Changes in website access require a dated new review.

Next authorized implementation should be a separate, reviewable cloud task after this research handoff: thermal numerical/semantic gates and operational event/recipe/model-status contracts, fixed no-fit AA5052 adapter parity, then independent phase-labelled data and bounded scheduling integration. No main merge, deployment or equipment action occurs in this task.
