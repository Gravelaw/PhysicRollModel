# Validation and deployment decision checklists

Unchecked items are future acceptance criteria, not completed work. Evidence owners should record pass/fail/inconclusive with immutable artifact links. No numeric accuracy target is invented where product tolerances and sensor uncertainty are absent.

## Scientific release gate

- [ ] Required outputs and intended decision are defined, with material/product/equipment domain.
- [ ] Every equation/parameter has source version, quantity, units, assumption, fit status and applicability.
- [ ] Initial material history and explicit interpass/topology events are represented; unknowns are not zero defaults.
- [ ] Stress versus force, diameter versus radius, torque per roll versus mill, heat flux versus power, full versus half thickness and log versus equivalent strain are audited.
- [ ] Numerical error is bounded by output-specific refinement and independent limiting cases; convergence is not confused with empirical accuracy.
- [ ] Mechanical and thermal ledgers conserve with signs/interfaces counted once; global entropy and pure-exchange thermal bounds pass for the intended step range.
- [ ] Material, sensors, compliance and losses are independently constrained before friction fitting; identifiability and fit boundary hits are reported.
- [ ] Raw observations remain distinct from source model outputs, assumptions and inferred values.
- [ ] Calibration and grouped holdout were predeclared, including source friction reuse and within-chain dependence.
- [ ] Measurement, parameter, numerical and model-form uncertainties are separated; coverage is measured or explicitly unestablished.
- [ ] Foil/pack, thermal/history, profile/flatness, released stress/damage and dynamics each have their own evidence gate if claimed.
- [ ] Independent scientific reviewer can reproduce the result and explain all conflicts/quarantines.

## Operational-phase and dynamic-model gate

- [ ] Extend existing phase tags with evidenced transitions for threading/bite, ramp-up, settled rolling, deceleration, tail/reversal and interruption; record unknown phases honestly.
- [ ] Version recipe targets, applied references/trims and actual signals separately by alloy/temper/gauge/pass/phase; preserve transition provenance and tracking errors.
- [ ] Validate material-coordinate alignment, remaining-length/diameter uncertainty and direction/reel-role changes; never use a fixed transport delay through arbitrary ramps.
- [ ] Declare O0 observation replay, O1 qualified quasi-steady sampling or O2 coupled dynamics; no relabelling of repeated steady solves as dynamic prediction.
- [ ] Per-model/output eligibility, parameter-update gates, invalid-data fallback and interruption re-entry have independent reasons and evidence; no universal speed-only gate.
- [ ] For O2, verify span/reel/drive/actuator balances, changing-mass inertia treatment, signed power/storage and time/spatial/event convergence.
- [ ] Compare independent head/ramp/settled/tail trajectories and short-coil/no-plateau cases; test dropouts, saturation, topology loss and reversals.
- [ ] Phase thresholds and accuracy bands come from qualified data/intended use; steel paper or vendor example parameters are not installed aluminium limits.

## Scenario and optimisation gate

- [ ] Candidate inputs distinguish material state, equipment, commands, observations and pass-specific bounds.
- [ ] Every candidate uses the versioned checked evaluator with full state history; rejected and indeterminate routes remain recorded.
- [ ] The selected route is replayed independently under stricter numerical settings and compared with a tractable finite oracle.
- [ ] Missing ratings/quality models cannot produce physical feasibility; observed ranges are not certified capacities.
- [ ] Objective units and scope are correct: energy integrates power over duration, with reel/idle/reversal/efficiency scope stated; full-pass objectives require the applicable operational/dynamic gate.
- [ ] Robust margins reflect joint uncertainty and support, not a rectangle formed from marginal statistics.
- [ ] Surrogates cannot hide invalid physics or out-of-domain inputs; reference fallback/rejection exists.
- [ ] Ranking is labelled with grid/model scope; no unsupported global optimum, production savings or safe-setpoint claim.

## Package/UI release gate

- [ ] All development changes originate in the saved Codex cloud environment and have independent review.
- [ ] Solver, material, contact, data, schema and scene versions are recorded separately.
- [ ] Clean target-environment install and offline replay succeed with pinned dependencies/hashes and a licence inventory.
- [ ] Optional Blender/USD verification is actually run in a compatible runtime; historical success is not relabelled as fresh.
- [ ] UI exposes units, uncertainty, data age, evidence status, failure reasons, phase, recipe/actual separation and model domain; these states originate in the core data/model contract.
- [ ] Geometry/visualization agrees with numerical state; exaggerated scale and unavailable fields are labelled.
- [ ] Invalid/malformed/oversized inputs, cancellation, memory limits and recoverable errors are tested.
- [ ] Dependency/model updates, backup/restore, schema migration and rollback are demonstrated.
- [ ] Representative latency/resource budgets are measured on the chosen target; no generic GPU assumption.

## Deployment options (decision open)

| Option | Appropriate first use | Inputs needed before selection | Additional release obligations |
|---|---|---|---|
| Offline local desktop | Research, engineering what-if and export-based advisory | OS, hardware, user skill, offline requirement, data directory/retention | Reproducible installer/package, local permissions, safe file parsing, backup/version management |
| Read-only edge advisory | Near-line replay with plant-adjacent data | Approved historian protocol, latency/clock/data-quality needs, network isolation, support owner | Read-only account, outage/stale-data behavior, buffer limits, trusted update/rollback, OT review |
| Shared on-premises service | Multi-user engineering and governed run archive | Users/concurrency, SSO, retention/data rights, compute/network policies | Authentication/authorization, job isolation/quotas, audit logs, service backup/monitoring and controlled releases |

These are delivery targets. Development remains in Codex cloud. A local-first package is the recommended portable research baseline, not a user-selected deployment decision.

## Advisory installation/integration gate

- [ ] User/site owner explicitly approves the concrete target and installation/integration plan.
- [ ] Data owners approve use/retention; credentials and private data are excluded from public bundles.
- [ ] No actuator/PLC write path exists in the advisory release; write-capable integrations are out of scope.
- [ ] Input freshness, clock alignment, quality flags, out-of-domain status, uncertainty and solver failures suppress advice appropriately.
- [ ] Logs connect each recommendation to immutable inputs, model/data versions, evaluated constraints and human disposition.
- [ ] Drift triggers distinguish process/material changes from instrument faults; fallback is historical replay or unavailable advice.
- [ ] Historical shadow evaluation precedes prospective human-reviewed advisory use; evaluation reports confounders and negative results.
- [ ] Operational owner can disable the service, restore the prior qualified model and retrieve audit evidence.

NIST SP800-82 Rev.3 is an [official OT-security planning reference](https://csrc.nist.gov/pubs/sp/800/82/r3/final), not a compliance finding from this research. The source catalogue notes a later revision in draft; responsible owners must confirm applicable versions when integration is scoped. [pip's official hash-checking guidance](https://pip.pypa.io/en/stable/topics/secure-installs/) supports package integrity, but hashes alone do not establish trust or security.

## Live control boundary

Live closed-loop control requires a separately authorized programme with responsible safety/controls engineers, hazard analysis, controller dynamics/stability, independent protection, fault handling, hardware-in-loop and commissioning evidence, site change control and applicable standards. Nothing in this audit completes those steps. Passing the above advisory gates does not permit equipment operation.
