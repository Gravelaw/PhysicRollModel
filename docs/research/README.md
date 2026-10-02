# Research and project documentation

This directory is the entry point for PhysicRollModel's research record. The
repository's executable and engineering documentation remains in `docs/` so
existing links keep working. The [2 October 2026 report addendum](report-update-2026-10-02.md)
maps the user's 49-page, 30 September research report to reviewed code at
`fbafee54bb8f22554904166c9653d75915051359`. Its editable Word and rendered
PDF copies are beside the Markdown source. The original report is a separate
Library attachment and is **not** reproduced in this repository.

## Reading order

| Question | Document or evidence |
|---|---|
| What runs, and what remains a proposal? | [Capability boundary](../capabilities.md), [model contract](../model.md), [research path](../research.md) |
| Which equations are implemented? | [Contact and material increment](../contact-increment.md), [flowing energy handoff](../energy-handoff.md), [equation-to-code traceability](../traceability.md) |
| What was checked numerically? | [Verification](../verification.md), [mechanics audit](../mechanics-audit.md), [energy specialist audit](../energy-specialist-audit.md), [change log](../mechanics-change-log.md) |
| What do the published aluminium cases support? | [AA5052 comparison](../aa5052-study.md), [contact comparison packet](../report-sync-contact-increment.md), [energy packet](../report-sync-energy-handoff.md) |
| What data and later models are needed? | [Sensors](../sensors.md), [next modules](../next_modules.md), [development](../development.md) |
| Where are source claims qualified? | [Source and reference ledger](source-ledger.md), [contact source records](contact-sources.json), source tables in the documents above |

`artifacts/aa5052/`, `artifacts/contact_increment/` and
`artifacts/flowing_energy_demo.json` contain the numerical comparison and
synthetic-run records cited by those documents. The tests verify equations and
implementation under stated assumptions. None of these artifacts is an
independent aluminium plant validation or a production parameter set.

The original 49-page Word/PDF report contains the long-form literature review
and source bibliography. This repository includes a concise status correction
and links to the research record; it does not include copyrighted full papers,
books, manufacturer images or private assistant working notes.
