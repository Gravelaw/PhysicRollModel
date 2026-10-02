# Supplemental route and product-quality review

2 October 2026. Scope: R108–R110 and R112–R115, complementing the contact review and R111. Source-level evidence and exact access limits are in [the seven-record ledger](supplemental-route-source-reviews.json). This is original project analysis; no papers, figures or books are redistributed.

## What the additional evidence changes

The source set supports a route schema that records material genealogy, machine configuration and pass-local commands separately. It does not supply a universal aluminium route or a complete material/friction card. Route optimization should retain the present bounded replay as a baseline and add new outputs only after an output-specific validation gate.

R108's [publisher PDF](https://www.jstage.jst.go.jp/article/jilm/59/10/59_10_555/_pdf/-char/en) was recovered after initial direct-access failures. Its numerical extraction has unresolved inconsistencies, so its current role is a quality/history benchmark lead. The coil-end temperature observation requires its own measurement operator; treating it as instantaneous strip-exit temperature would change the validation target.

R109's [publisher full HTML](https://link.springer.com/article/10.1007/s11661-024-07472-y) permits a substantive methods/results review. It motivates joint discrimination using global loads and local texture. A model selected for one observable may fit another poorly. The task should keep statistical texture models and resolved crystal plasticity as alternatives until an intended product requires that fidelity.

[R110's teaching equations](https://users.encs.concordia.ca/~mmedraj/mech421/lecture%205%20rolling.pdf) are useful limiting cases. Unit tests should explicitly separate revolutions per second from rpm, total versus per-roll torque, geometric reduction strain from equivalent strain, and nominal roll radius from an elastic contact construction. Passing these checks establishes implementation consistency, not empirical accuracy.

[R112's official article](https://library.e.abb.com/public/cab489262e40ea6ac1257beb0029324a/ABB%20Review_1_2009_72dpi.pdf) extends through printed page48. Its planning lesson is to keep scheduling, machine-setting conversion and measurement adaptation distinct. No model in this repository should acquire online adaptation or write access merely because an industrial architecture contains those features.

[R113's foil section](https://european-aluminium.eu/wp-content/uploads/2023/01/European-Aluminium_Environmental-Profile-Report-2018_full-version.pdf), [R114's equipment description](https://www.achenbach.de/en/machines-equipment/optimill-rolling-mills/optimill-foil-rolling-mills/) and [R115's patent disclosure](https://patents.google.com/patent/US20040088840A1/en) motivate explicit topology and equipment records. Product descriptions, lifecycle inventories and patent examples serve different evidential roles. None establishes the plant limits required for a feasible operating recommendation.

## Recommended dependency additions

| Work package | Prerequisites and method | Acceptance and stop condition |
|---|---|---|
| Quality-sensitive route benchmark | R108 facsimile/table reconciliation, material history and actual measurement coordinates; preserve measured endpoints separately from inferred mechanisms | Reproduce observable definitions before digitizing; stop numerical import at conflicting cells or missing unit glyphs |
| Friction/texture discrimination | R109 experiment/material/initial texture, verified full/half-width observation normalization; compare GIA/VPSC and selected DAMASK references | Evaluate force and texture jointly on cases not reused for tuning; no general foil friction law inferred from a dry high-reduction case |
| Route events and topology | Separate split,trim,pair,release-oil,pack-pass,separate and anneal records; per-layer mass/width/gauge/coordinate identities | Sum layer mass and interlayer work/heat consistently; no silently substituted total thickness |
| Pack registry | Track longitudinal orientation and matching of daughter strips; preserve each layer's observed thickness/profile | Validate interlayer traction and slip with actual paired-strip observations; source route arithmetic alone cannot qualify mechanics |
| Equipment/settings closure | Actual roll stack, compliance, loaded-gap reference, reels, gearing and cooling layout | Gauge target and screwdown remain separate quantities; missing machine evidence yields indeterminate limits |
| Energy/time boundary | Separate deformation/friction work, shaft work, electrical input, auxiliaries, reversal/idle and material yield | Duration and throughput calculations conserve declared layer/pack lengths; lifecycle totals cannot substitute for a pass efficiency |

These are planning requirements, not implementation instructions. Cheap scalar/one-dimensional evaluations remain suitable for numerical route-search development. Texture and contact field methods should run offline on selected cases first; a measured target-hardware budget must precede any runtime promise. A surrogate may reduce repeated cost only inside a verified parent-model domain and must inherit its limitations.

## Gaps and actionable next steps

1. Reconcile the R108 facsimile against its abstract and extracted Table1 before making a dataset. Record whether the discrepancy is in the publication or extraction; never silently choose a route. Obtain measurement timing/location and uncertainty before using its thermal observations quantitatively.
2. Request R109 raw inputs/EBSD only through an explicitly authorized human/data-owner channel. Freeze the observation and friction-fitting contract before using this case for benchmarking. Access to article text does not establish access to raw data.
3. If pack foil becomes the chosen product, collect paired-layer genealogy, geometry, release-oil properties, tensions, surface observations and slip measurements before extending the solver. A single-layer advisory product can proceed independently.
4. Obtain actual installed-machine ratings and calibration documents; neither generic OEM capabilities nor dynamic web counters fill this gap.
5. Preserve patent table inconsistencies as an evidence-quality test. A production-time objective needs an independently verified coil/pack accounting model and measured overheads.

## Review limits and checks

All seven source identities were reconciled to direct URLs. Current-session status is four partial-text reviews and three official-document reviews; no complete-paper review is claimed by this supplement. R108 screenshots failed despite successful text recovery. R109 raw numerical/EBSD data were not obtained. R112 review covers the six-page article, not its whole magazine. R113 review covers selected foil/glossary sections, not its whole report. The patent facsimile and legal status were not audited. Counts describe access depth, not quality or completion of scientific validation.

The JSON is syntactically validated, has unique expected IDs and required fields, and preserves null DOI values for non-DOI documents. The independent roadmap review was sent to the parent without editing the roadmap.
