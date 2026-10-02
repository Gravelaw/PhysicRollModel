# Comprehensive evidence audit and end-to-end roadmap

Research date: **2 October 2026**. Audited main: [`caec37ef86a8b78e1eb88292ea6368bfb64bcbdc`](https://github.com/Gravelaw/PhysicRollModel/tree/caec37ef86a8b78e1eb88292ea6368bfb64bcbdc). Dedicated documentation branch: `research/comprehensive-evidence-roadmap-2026-10-02`.

## Executive findings

Build the next scientific milestone around checked multipass replay and a frozen, conditional AA5052 comparison. Prioritize source semantics, material identifiability and independent measurements before broader scheduling or extra physics. Preserve material state, equipment configuration, commanded settings, observed signals and pass-local bounds separately. The illustrative 6 mm → 0.05 mm route is not a required test case.

The code has more than the original heuristic: optional spatial hardening, tension-aware slab, circular contact, thermal ledgers, checked pass chains and a narrow gauge search. It remains uncalibrated. **86 baseline tests pass**, as do smoke and Blender structure checks; optional OpenUSD verification is blocked by missing `pxr`. Independent review reproduced a large-step thermal midpoint overshoot with negative whole-step entropy despite an essentially zero first-law residual. This is a required numerical gate before predictive thermal use, not a claim that ordinary bundled examples fail.

The separate bounded-search candidate at [`ef0996acdd7af1799c62cb9a2e628e35acd26206`](https://github.com/Gravelaw/PhysicRollModel/tree/ef0996acdd7af1799c62cb9a2e628e35acd26206) passes **91 tests** and an additional real checked-replay integration probe. It remains a finite-choice scaffold with indeterminate physical feasibility. It is not merged here. Parent-reported uncommitted benchmark drafts are not counted as published capability.

No public case was verified as a complete independent calibration/validation fixture for the present model. Shao's three AA5052 force/slip pairs are useful conditionally; initial history, strain/stress mapping, speed, radius wording and friction reuse remain unresolved. Choi tension inputs remain quarantined. The roadmap compares alternatives through offline simulation, calibration, scheduling, UI/3D, packaging, advisory deployment and eventual read-only plant integration. **The user leaves deployment options open. All subsequent development stays in Codex cloud after this research.** A local-first offline package is a portability recommendation, not a selected deployment or permission to deploy. Live control requires a separate authorized safety/controls programme.

## Actual corpus reconciliation

The scan covers **140 tracked source-bearing files**, including both DOCX and PDF representations, code/scenario provenance and newer notes. It resolves **178 distinct external URL/DOI locators** and 450 file/locator pairs. Different locators and versions are not counted as different works.

* **146 distinct source identities already occur in the baseline:** 135 technical sources plus 11 secondary vocabulary/orientation pages. The original 105 numbered entries are a subset.
* **13 additional identities** were added through the parent benchmark selection, targeted research and deployment planning.
* **159 total ledger identities:** 148 technical and 11 orientation. The technical set comprises 81 scholarly publications, 2 theses, 3 dataset/repository records, 43 OEM/industry documents/pages, 14 official software references, 1 SI standard, 1 official security-guidance reference, 1 teaching document, 1 patent and 1 video.

Every technical identity has an individual current review/access record. This does **not** mean every source was read in full. The greatest current access depth per identity is:

| Current depth | Count |
|---|---:|
| Full text substantively reviewed | 16 |
| Partial text / selected substantive sections | 24 |
| Relevant official document sections | 50 |
| Primary abstract only | 31 |
| Metadata/identity only | 20 |
| Current access unavailable | 7 |
| Secondary orientation, no new technical reliance | 11 |
| **Total** | **159** |

The scholarly-plus-thesis subset has 15 full, 22 partial, 30 abstract-only, 15 metadata-only and 1 unavailable current record. These are access-depth counts, not quality scores. A paper with a fresh full-text record can still lack raw data, independent validation or usable material constants. Official-document counts include product/README sections, not audited dataset files. The machine ledger preserves **all** reviewers' complementary findings, versions, locators and conflicts; the compact depth is only a counting convention. Historical report access is retained separately, so a failed current fetch does not erase an earlier review.

**Unresolved historical completeness:** the handoff mentions 14 book leads, mostly contents/previews, but their exact identities were not found in the saved repository or targeted Library retrieval. U001 retains this missing inventory cluster. Its unverified cardinality is excluded from the totals. The plan and accessible corpus audit are complete within the stated scope; a claim that the entire historical book library has been reread would be false. Recovering that list and lawful access remains an explicit research action.

## Read and use the deliverables

| Need | Deliverable |
|---|---|
| End-to-end decisions, dependencies and phase gates | [Roadmap](roadmap.md) |
| Prioritized science versus engineering tasks and next milestones | [Gap register and backlog](gaps-and-backlog.md) |
| Validation, packaging, target options and advisory/live-control boundary | [Validation/deployment checklists](validation-and-deployment-checklists.md) |
| Every source, current/historical access, findings and conflicts | [Annotated inventory](annotated-source-review.md), [JSON](source-ledger.json), [CSV](source-ledger.csv) |
| Actual code, units, tests, thermal counterexample and separate scheduler review | [Implementation audit](implementation-traceability.md), [40-row traceability](traceability.csv) |
| Mechanics, contact, foil and numerical methods | [Contact review](contact-review.md) |
| Hardening, rate/temperature, annealing, heat and material quality | [Materials/thermal review](materials-thermal-review.md) |
| Sensors, alignment, stack, crown/profile/flatness, OEM scope | [Sensing/profile review](sensing-profile-review.md) |
| ML, identifiability, data, constrained/robust optimisation | [Optimisation/data review](optimisation-data-review.md) |
| Independently checked calibration contract and alternative datasets | [Benchmark review](benchmark-independent-review.md) |
| Pass-history/texture, route, teaching and patent sources | [Supplemental route review](supplemental-route-review.md) |
| Scope, identity, copyright and user decisions | [Audit contract](audit-scope.md) |
| Independent publication review | [Review record](independent-review.md) |

All source review JSON files are original project annotations. No full copyrighted paper, book or manufacturer artwork is committed. Existing Word/PDF reports and implementation history are preserved unchanged. This Markdown/CSV/JSON delivery is intentionally editable and diffable; it does not replace the historical 53-page report.

## Rebuild and verify

From the repository root, run:

```bash
python docs/research/comprehensive-audit-2026-10-02/build_inventory.py
python docs/research/comprehensive-audit-2026-10-02/validate_audit.py
```

The inventory reader uses Python 3.12.14 and `pypdf` 6.10.0 in this saved environment; it reads immutable baseline Git objects and authored review records, with no network or model mutation. `source-counts.json`, `citation-occurrences.csv` and `baseline-files-scanned.json` make counts reproducible. `validation-results.json` records structured-data/link/count checks. Source retrieval outcomes are documented per entry; a syntactically valid or identified URL is not claimed universally reachable. Changes in website access require a dated new review.

Next authorized implementation should be a separate, reviewable cloud task after this research handoff: numerical/semantic gates, fixed no-fit AA5052 adapter parity, then independent data and bounded scheduling integration. No main merge, deployment or equipment action occurs in this task.
