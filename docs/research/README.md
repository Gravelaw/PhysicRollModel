# Research and project documentation

This directory is the entry point for PhysicRollModel's research record. The
repository's executable and engineering documentation remains in `docs/` so existing links keep working.

The [comprehensive evidence audit and end-to-end roadmap (2 October 2026)](comprehensive-audit-2026-10-02/README.md)
reconciles the complete observed source corpus, records current versus historical
access depth, audits actual code/tests at `caec37ef`, and plans through advisory
deployment with explicit science/data gates. It preserves the reports below and
records unresolved historical book identities rather than claiming they were read.
Development after research remains in the saved Codex cloud environment; deployment
options are open and no deployment or main merge is authorized by this audit.

The full research report, revised 2 October 2026, is available in [editable Word](Aluminium_cold_rolling_research_for_PhysicRollModel.docx) and [PDF](Aluminium_cold_rolling_research_for_PhysicRollModel.pdf). The 53-page revision preserves the 105-entry bibliography, 63 original equation objects and original research discussion; Section 40 adds current implementation, source/code/test mapping and validation boundaries against reviewed code `fbafee54bb8f22554904166c9653d75915051359`.

The [2 October status addendum](report-update-2026-10-02.md) is retained as a historical bridge from the original 30 September, 49-page report. Its page references refer to that earlier edition; use section references in the revised full report.

## Reading order

| Question | Document or evidence |
|---|---|
| What runs, and what remains a proposal? | [Capability boundary](../capabilities.md), [model contract](../model.md), [research path](../research.md) |
| Which equations are implemented? | [Contact and material increment](../contact-increment.md), [flowing energy handoff](../energy-handoff.md), [equation-to-code traceability](../traceability.md) |
| What was checked numerically? | [Verification](../verification.md), [mechanics audit](../mechanics-audit.md), [energy specialist audit](../energy-specialist-audit.md), [change log](../mechanics-change-log.md) |
| What do the published aluminium cases support? | [AA5052 comparison](../aa5052-study.md), [contact comparison packet](../report-sync-contact-increment.md), [energy packet](../report-sync-energy-handoff.md) |
| What data and later models are needed? | [Sensors](../sensors.md), [next modules](../next_modules.md), [development](../development.md) |
| How are prescribed multi-pass gauges and pass-specific signals handled? | [Multi-pass foundation (2 October 2026)](multipass-foundation-2026-10-02.md) |
| What theory and source limits guide later schedule search? | [Multi-pass theory and scheduler boundary](multipass-theory-2026-10-02.md) |
| Which checked solvers are composed across passes? | [Checked schedule integration](checked-schedule-integration-2026-10-02.md) |
| Where are source claims qualified? | [Source and reference ledger](source-ledger.md), [contact source records](contact-sources.json), source tables in the documents above |

`artifacts/aa5052/`, `artifacts/contact_increment/` and
`artifacts/flowing_energy_demo.json` contain the numerical comparison and
synthetic-run records cited by those documents. The tests verify equations and
implementation under stated assumptions. None of these artifacts is an
independent aluminium plant validation or a production parameter set.

The full revised Word/PDF contains the long-form literature review and source bibliography. This repository includes the project's authored research and implementation records, not full third-party papers, books, manufacturer images or private assistant working notes.

The report is a **2 October 2026 snapshot** of executable code `fbafee54`.
Subsequent optional development is tracked in the live engineering documents;
the [passive-contact increment](../passive-contact.md) adds a supplied-conductance
numerical closure without revising the 53-page historical edition or claiming
new thermal validation.
The multi-pass foundation is a subsequent development note and leaves that
53-page report as a dated snapshot.
