# Independent publication review

Review date: 2026-10-02. Exact implementation baseline: `caec37ef86a8b78e1eb88292ea6368bfb64bcbdc`. Separate scheduler candidate: `ef0996acdd7af1799c62cb9a2e628e35acd26206`. This is an independent review of the authored research package, not approval to merge code, implement the roadmap, deploy software or operate equipment.

## Outcome and scope

The reviewed scientific conclusions, calibration boundary and staged roadmap are suitable for publication as a research/planning baseline with the evidence gaps below. The thermal counterexample is independently reproduced. Inventory outputs reproduce exactly, complementary review findings are retained, and source-level counts are not presented as counts of fully read versions or validated models.

This reviewer checked the roadmap, implementation traceability, inventory builder/ledger/counts, annotated inventory, topic-review summaries, prioritized backlog and validation/deployment checklists. The earlier [independent benchmark review](benchmark-independent-review.md) and [nine-source annotations](benchmark-source-reviews.json) supply this reviewer's fresh primary-source checks. This publication review does not claim a second independent full-text reread of all 159 works. The complete 86/91-test suites were reported by the implementation reviewer and their scope was assessed here; this reviewer separately executed the I01 probe rather than duplicating both suites.

## Review findings resolved

| Finding | Verified correction / acceptance |
|---|---|
| Best-access review replaced complementary findings in flattened outputs | Builder now retains every reviewer version, locator, finding, conflict, domain and relevance with review-file provenance. R062 retains all three reviewers' warnings, including friction-branch and work-expression ambiguity. |
| Publicly inspected later passes could be mistaken for a blind holdout | P2 explicitly states that all three passes were already inspected and later-pass checks are previously seen conditional comparisons. The effective initial-hardening fit is not a measured prestrain or recovered source history. |
| Dataset landing page counted as document-content review | R141 is now metadata-only; raw files remain unaudited. R034's README/licence review remains separate from numerical file access. |
| NIST guidance classified as a standard, with insufficient citation-depth distinction | R143 is official guidance, primary abstract/version checked; full guidance remains unread. R144 now has a relevant-body official-document review, with hashes distinguished from trust/security. |
| Inventory collision/schema safeguards absent | Builder asserts persistent ID, DOI and canonical URL ownership; required fields, known access states, nonempty locators and original R001–R105 identity coverage are checked. No collision occurs in the current corpus. |
| Source access and implementation/validation could be conflated | Per-source traceability IDs and explicit implementation-link status are present. Source access neither claims equation implementation nor physical validation. |

## Reproducibility and count checks

An isolated temporary rebuild imported the current `build_inventory.py`, copied its JSON/CSV inputs to a temporary directory, retained the real immutable baseline as its read source, and wrote outputs only into that temporary directory. The final reader includes both PDF and DOCX representations and uses the saved pypdf runtime. All six generated files were byte-identical to the authored package: `source-ledger.json`, `source-ledger.csv`, `source-counts.json`, `citation-occurrences.csv`, `baseline-files-scanned.json` and `annotated-source-review.md`.

Independently reconciled totals:

| Quantity | Verified value |
|---|---:|
| Distinct inventoried source identities | 159 |
| Technical/evidence sources | 148 |
| Secondary orientation pages | 11 |
| Identities cited in scanned baseline files | 146 |
| Identities added by this audit | 13 |
| Original numbered bibliography identities | 105 |
| Technical records with current reviewer annotations | 148 |
| Baseline files scanned | 140 |
| File/canonical-source URL pairs, including bare DOI normalization | 450 |
| Unique external citation URLs | 178 |
| Unmapped external citation URLs | 0 |

The 54 records additional to the original bibliography are not all new discoveries: 41 were elsewhere in the existing baseline and 13 were added by this audit. No historical “14 books” count was added to verified identities. These counts concern the observed corpus, not unseen historical library contents.

The compact source status is the greatest documented current access depth among its representations. It does not imply all versions, supplements, equations or data files were read. Version-specific reviewer statuses remain in `access_summary` and `reviews`; the original reported status is retained before normalization. A blocked supplement can therefore coexist with a reviewed primary paper. Current source-status totals reconcile exactly: 16 full-text, 24 partial-text, 50 official-document, 31 abstract-only, 20 metadata-only, 7 unavailable and 11 unretrieved orientation records. None is a quality or validation score.

## Literal independent reproduction of I01

The following API probe was copied literally from the implementation audit and run at the exact baseline above. It changes only in-memory mechanics fields to isolate zero-source thermal exchange; it does not edit project files or represent a measured loaded rolling pass.

```python
import json, math
from dataclasses import replace
from physicroll.model import Scenario
from physicroll.materials import MaterialState, PowerHardeningLaw, BiteHardening
from physicroll.slab import solve_slab
from physicroll.energy_handoff import (HeatCapacityCurve, PassHeatBoundary,
                                      PassiveContactBoundary, handoff_pass)
s = Scenario.from_dict(json.load(open('scenarios/baseline.json')))
state = MaterialState('demo', 'unknown', .1, ('synthetic',), 300.)
law = PowerHardeningLaw('demo', 'unknown', 100e6, 100e6, .3, 'synthetic')
material = BiteHardening(state, law, (0., 3.), (250., 450.))
s = replace(s, mean_flow_stress_pa=material.mean_stress(
    s.entry_thickness_m, s.exit_thickness_m))
mechanics = solve_slab(s, 256, material=material)
for key in ('plastic_work_power_w', 'solid_slip_dissipation_both_interfaces_w',
            'roll_mechanical_power_both_rolls_w', 'net_tension_power_w',
            'mechanical_work_residual_w', 'mechanical_work_residual_relative'):
    mechanics[key] = 0.
scp = HeatCapacityCurve('demo', (250., 450.), (900., 900.), 'synthetic', 'synthetic')
rcp = HeatCapacityCurve('roll', (250., 450.), (500., 500.), 'synthetic', 'synthetic')
boundary = PassHeatBoundary(0., 0., 0., 0., 0., 1., 320., 5.,
                           'isolated synthetic thermal operator', 'synthetic')
contact = PassiveContactBoundary(1e6, 'synthetic', 'synthetic')
r = handoff_pass(mechanics, state, scp, rcp, boundary, passive_contact=contact)
ts, tr = r['strip_temperature_out_k'], r['roll_temperature_out_k']
entropy = mechanics['mass_flow_kg_s']*900*math.log(ts/300) + 100*math.log(tr/320)
print({'strip_out_K': ts, 'roll_out_K': tr,
       'thermal_residual_W': r['thermal_allocation_residual_w'],
       'midpoint_entropy_W_per_K': r['contact_entropy_production_w_k'],
       'whole_step_entropy_W_per_K': entropy})
assert tr < 300 and entropy < 0  # Reproduces the OPEN issue, not acceptance.
```

Observed output:

```text
{'strip_out_K': 300.4072513547216, 'roll_out_K': 280.41516832105737, 'thermal_residual_W': -2.2100721253082156e-10, 'midpoint_entropy_W_per_K': 0.00017386814170859945, 'whole_step_entropy_W_per_K': -0.01897878794887653}
```

The result matches the audit: the roll falls below the colder 300 K strip inlet with no external cooling. The first-law residual is effectively zero, and the local midpoint entropy proxy is positive, yet the complete-step entropy balance is negative. For this construction, the appropriate rate balance is stream entropy change `mdot*cp_s*ln(Ts_out/Ts_in)` plus finite roll entropy storage divided by duration, `(Mroll*cp_r/dt)*ln(Tr_out/Tr_in)`. Here `Mroll*cp_r/dt = 100 W/K`, explaining the literal coefficient in the probe. All temperatures are absolute and both heat capacities are constant and positive.

Thus I01 is a valid counterexample to the sufficiency of the existing local passivity check. It is not evidence that every thermal case fails or that the ordinary bundled demo is wrong. The documented constant-cp non-overshoot inequality follows from the midpoint algebra; it is a diagnostic bound, not a universal process law. P1/P4 appropriately require finite-step bounds, exact entropy integration for variable heat capacity and refinement before predictive thermal use. The research task makes no fix.

## Scientific and roadmap acceptance

The documents consistently distinguish software verification from physical validation: 86 baseline tests and 91 separate-branch tests do not supply an identified aluminium material card, independent measurements or plant-safe settings. The current legacy default, optional mechanics, thermal ledgers, checked replay and narrow pre-existing gauge search are separated from the unmerged scheduler candidate. The finite search claims best-within-supplied-choices and indeterminate physical status; omitted ratings and quality models remain unknown.

P2 keeps raw observations immutable, freezes named assumptions before a new fit/comparison, restricts any fit to one effective initial-hardening parameter, and reports force/slip mismatch rather than tuning it away. It does not equate the source's history law with additive code history. P3 requires independent material/sensor/machine information and grouped external validation. P4/P6 qualify thermal/history, foil/pack, profile/flatness, residual stress and damage separately. P5 distinguishes synthetic algorithm tests from physical recommendations and requires full state replay, rejection reasons and uncertainty support.

The backlog distinguishes evidence/science gaps from ordinary engineering work. Phases declare inputs, alternatives, dependencies, acceptance, uncertainty, gates and deferred features. Synthetic UI/package work can proceed without pretending calibration is complete. No fabricated equipment limits, material cards, universal accuracy threshold or mandatory 6 mm → 0.05 mm route were found. Deployment options remain open; the local-first suggestion is an architectural recommendation, while subsequent development remains in the saved Codex cloud environment. Advisory deployment and any future live control are explicitly separate authorization/validation programmes.

## Remaining limitations and release boundary

- U001 remains an unresolved historical book-lead inventory. Without individual titles/editions/locators, the package cannot claim the entire historical library was recovered or reread.
- Abstract/metadata-only, blocked and partially reviewed records remain acquisition tasks. Exact original figures/equations, mutable software revisions and dataset file versions are not universally verified. In particular this reviewer achieved no fresh visual PDF review for its nine benchmark candidates; that access limitation remains explicit.
- Shao conventions/history and friction independence remain unresolved; Choi tensions and other source-specific graph/unit conflicts remain quarantined. No completely specified independent measured aluminium multipass load benchmark was established by this review.
- I01 remains an open implementation defect/domain gap. Missing temperature feedback, kinetic history, foil/pack contact and output-specific validation remain scientific gates, not documentation defects.
- The optional current OpenUSD semantic check could not run without `pxr`; prior checks and present file hashes are not substitutes.
- Zero unmapped URLs means the scanned citation set reconciles. It is not a claim of successful live retrieval of every URL, no historical omissions, or permission to redistribute linked content.

The review approves publication of the qualified research/planning documents once the final index/link and consistency checks below pass. It does not approve any implementation promotion, empirical-validation claim, main merge or deployment.

## Final local-link and consistency check

Final index review completed. All 35 existing relative Markdown links in the audit directory resolved, with no broken targets; this includes the new README and independent-review links. The 40 traceability rows reference known source identities; all 159 CSV source rows match JSON identities and nested provenance fields parse. The optimisation topic's access-count prose now agrees with its JSON (two official-document and four metadata-only records). README total, technical, orientation, baseline, added and scholarly/thesis access counts independently reconcile with the ledger.

The checked `validate_audit.py` writes only its authored `validation-results.json`; the inventory builder writes authored audit artifacts and reads immutable Git objects. No implementation-mutating subprocess was found. The validation result reports success and all four historical Word/PDF hashes independently match the preserved files. These scripts' checks do not constitute a security audit of executable code or successful retrieval of all external links.

At final review, `HEAD` and local `origin/main` both resolve to `caec37ef86a8b78e1eb88292ea6368bfb64bcbdc`; the active branch is `research/comprehensive-evidence-roadmap-2026-10-02`. Tracked changes are confined to the research index and new authored audit documents. The local remote-tracking reference is not a new network query of the server. No merge, push, deployment or equipment action was performed by this reviewer. Temporary Python bytecode from the review's inventory import was removed.

**Final outcome: no remaining blocker to publishing these qualified research/planning documents.** U001, access/data gaps, the open I01 thermal issue and all physical-validation/deployment gates remain explicit limitations; approval of the documentation does not close them. A later documentation commit/push must retain this scope and rerun the stated checks after any material changes.
