# Audit scope and reproducibility contract

Audit date: 2 October 2026. Repository baseline: `caec37ef86a8b78e1eb88292ea6368bfb64bcbdc`.
Dedicated branch: `research/comprehensive-evidence-roadmap-2026-10-02`.
This task produces research and planning documents. It does not authorize implementation of all phases, main-branch integration, deployment, or equipment operation.

The user's concern that only about 20 documents had informed work against more than 70 sources is a motivation for the audit, not its denominator. Historical counts are preserved as historical claims. Fresh counts are generated from the ledger, with source identity, current retrieval depth and historical depth kept separate.

## Corpus boundary

The inventory scans every tracked text file and both research DOCX relationship/visible-text sources and PDF annotations/text at the baseline, including source citations in code, scenarios and generated provenance. Original bibliography identities R001–R105 are persistent. Extra papers, datasets, software documents, OEM pages, teaching documents, patents and orientation pages get separate persistent identities. Mirror URLs and preprint/published versions of the same work are aliases/versions, not additional works. Datasets and thesis-to-article relationships remain distinct because their evidence is not interchangeable. Internal project links and schema identifiers are classified separately from external evidence.

The PDF and DOCX editions of the project-authored report are representations of one report, not two external sources. The 53-page original and all historical documents remain unchanged. The original report's 105-row bibliography was extracted with exact original access notes into `original-bibliography.json`.

The parent supplied additional original benchmark analysis on 2 October 2026. Those source identities are included and independently assessed. Parent-reported PDF access is not silently counted as a fresh full read by this audit. No complete third-party paper, book, brochure artwork or private plant record is republished here.

## Unresolved historical library scope

The handoff mentions **14 book leads**, mostly contents/previews, but provides no titles, editions, ISBNs or locators. Neither the tracked report text nor repository source notes contain that list. Targeted Library searches found versions of the same authored report and project archives, but did not resolve a book inventory. Personal-context retrieval was unavailable. The parent's subsequent room-history review confirms a 1 October request for textbook fundamentals in simulation, metallurgy, forging and rolling; it did not recover an actual book list. This is parent-supplied history, not a newly retrieved primary bibliography. Consequently U001 remains an unresolved historical inventory cluster; its alleged cardinality is excluded from verified distinct-source totals.

The supplement supplies a **newly selected fundamentals bibliography**, with its own source IDs, edition/access records and provenance. These choices address the underlying learning and modelling need; they are not recovered historical identities and do not close U001. Publisher contents establish chapter identity, not chapter findings. Lawfully available complete books reviewed only in selected sections retain `partial_text_reviewed` status. If an exact historical list is later found, reconcile identities/editions against the new entries before adding anything; do not count presumed matches or invent lost titles. Historical completeness remains unresolved without preventing bounded numerical research supported by the current evidence.

## Access and evidence vocabulary

`full_text_reviewed`: the identified complete article/chapter text was available and substantively inspected; it does not imply every reference or supplemental file was audited. `partial_text_reviewed`: identifiable body sections, excerpts or selected pages only. `abstract_only`: primary abstract supports scope, not detailed parameters. `metadata_only`: identity/locator only. `unavailable`: attempted route blocked or missing. `official_document_reviewed`: relevant official technical/product document sections, with exact limits. Secondary orientation remains secondary even when its page is accessible. A blocked current fetch does not erase a documented older read, and that older read does not become a fresh read.

Evidence level distinguishes primary measured aluminium evidence, primary measured other-material evidence, numerical method/simulation evidence, primary abstract leads, OEM claims, official software conventions and secondary orientation. It is **not** an ordinal score or a count-based quality measure. Public accessibility does not establish reproducibility, independent validation or redistribution permission.

## Version and numerical policy

Every usable input needs source/version and page/table/equation locator, units, quantity semantics, material/process scope and uncertainty status. A missing field stays null or explicitly unknown. A mutable webpage is dated as accessed, with revision unknown where no version is supplied; the access date is not an invented publication date. Numbered equations belong to the accessed version. In particular R012's implementation citations remain 2024 preprint v1 equations 21–28, even when later versions are readable.

Shao R062 radius/diameter, strain/history, friction provenance and speed semantics remain conditional. Choi R030 tension units remain quarantined. Author predictions, fitted friction, observed load ranges, software guards and OEM maximum offerings never become independent measurements or certified plant ratings.

## User choices and coordination

The user elected to **leave deployment options open** and asked the team to choose the best scientific approach. The roadmap therefore compares local desktop, edge and shared on-premises advisory options; local-first is a recommendation for the next reproducibility stage, not a settled deployment requirement. Alloy/temper and plant configuration remain unspecified, so initial samples are evidence-backed published cases with explicit limitations, not the illustrative 6 mm → 0.05 mm route.

The separate bounded scheduler development `codex/bounded-schedule-search` at `ef0996a` is reviewed as a separate candidate. It is not merged into this baseline or edited by this research task. Candidate acceptance semantics and calibration gates are reviewed independently. Discussion with the parent does not authorize contacting paper authors or vendors; proposed data requests remain backlog items.

All later rolling development must occur in the saved Codex cloud environment after this research task. The separately reported unpublished benchmark draft is paused and is not treated as verified main capability.
