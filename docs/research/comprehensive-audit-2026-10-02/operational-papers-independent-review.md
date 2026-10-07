# Independent review of operational rolling papers

Review date: 2026-10-02. Reviewer did not author the reviewed supplement. Repository HEAD inspected: `ade4d1d0c4d5f8e6ca943ea1af9860446ead01d9`. Scope: records **R167, R169 and R170**, their scientific claims and access limitations, current-code mappings, and proposed operational-phase/model-activation requirements. This is a documentation review, not empirical model validation or authorization for live control.

**Accepted for integration: no blocking findings.** Both the Markdown review and structured source records were read. Their distinction between existing capabilities and proposed work is appropriate.

- **R167:** Independently inspected the public author-uploaded manuscript. Its inertia, electrical and transmission descriptions support the coupled-dynamics characterization. Provisional manuscript pagination and the conflicting angular/peripheral interpretation of omega are correctly retained; version-of-record equivalence is not claimed.
- **R169:** Independently inspected the author-uploaded published article. Coupled electromechanical, interstand and hydraulic submodels support its characterization. The reported 8% improvement remains a simulated schedule comparison rather than demonstrated plant savings. Shared provenance with R167 does not establish independent replication.
- **R170:** Independently inspected publisher body text. The explicit stand-by-stand `.odb` state transfer supports the sequential FE characterization; transfer of a temperature field does not itself validate thermal feedback. Independently confirmed the prose discrepancy: 2.102 versus 2.0 mm implies 5.1%, not the stated 2.53%. The Table 4 endpoint failed during this independent check. Its reported 2.066/2.015 mm values and their 2.53% arithmetic therefore rely on the supplement author's separate table inspection, not a second table retrieval. That limitation does not invalidate the conservatively quarantined claim.

Code spot checks confirmed `operating.py` has threading, steady, deceleration and tailout labels, without an acceleration phase, and returns `NOT_EVALUATED_PHASE` for non-steady model checks. The inspected steady model, prescribed schedule and material metadata support the documented absence of coupled transient dynamics and calibrated temperature/rate feedback. Proposed event schemas, phase gates and fidelity choices remain research requirements rather than implemented or validated functionality. No universal thresholds, plant limits or control permission are inferred.

No files other than this review record were changed by the independent reviewer, and no implementation tests were rerun. Source retrieval was limited to the targeted checks above; figures, complete equation transcription, raw traces and R170's supplement were not independently reproduced.

The accepted artifacts are pinned by SHA-256:

| Artifact | SHA-256 |
|---|---|
| [operational-papers-review.md](operational-papers-review.md) | `6033268adb509ee1bed80509c16bd1ba9c5df70878e26efb7f7ebab50cef49e9` |
| [operational-papers-source-reviews.json](operational-papers-source-reviews.json) | `5e31bd1f5b623a71ee3d12795b8f5b2ebd4425df459a175013bb1ab3929e28d3` |
