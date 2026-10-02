# Operational rolling dynamics: primary-paper supplement

Reviewed 2 October 2026. This is research and planning, with no controller implementation or plant-operation authorization. The three new records and source-specific findings are in [operational-papers-source-reviews.json](operational-papers-source-reviews.json). All three are **partial text reviewed**: substantive body sections were read, but equations/figures or supplementary data were not completely verified. Public access was used; no papers or proprietary data are redistributed.

The design decision is to introduce operational phases as explicit simulation context, then distinguish the fidelity of each enabled model. A sequence of force calculations at different speeds can support an offline study; it cannot establish the predicted tension, torque, gap or temperature trajectory during a ramp. A usable advisory application must make that distinction visible.

## Evidence and its limits

| ID | Primary source and reviewed version | What it can support | Evidence boundary |
|---|---|---|---|
| R167 | [Kozhevnikov et al., JCTM 2018](https://journal.uctm.edu/node/j2018-2/26_17_77_p_366_372.pdf); [public author manuscript](https://www.researchgate.net/publication/323415241_Development_of_the_model_of_cold_rolling_process_in_dynamic_conditions) | Coupled dynamic structure | Manuscript/version and units need reconciliation |
| R169 | [Kozhevnikov et al., Metallurgist 2017](https://doi.org/10.1007/s11015-017-0526-5); [public author-uploaded article](https://www.researchgate.net/publication/321169636_Simulation_of_Cold-Rolling_Process_in_Dynamic_Conditions) | Industrial dynamic-comparison design | Steel; incomplete reproduction data; correlated with R167 |
| R170 | [Yan et al., Scientific Reports 2025](https://www.nature.com/articles/s41598-025-21834-5) | Offline shape/compensation investigation | Sequential state transfer; calibration and prose–table conflict |

R167 and R169 are separate publications, not interchangeable versions. Their shared provenance also prevents counting them as independent plant replications. No source here supplies universal phase-transition thresholds or validates the present aluminium prototype. The operational recommendations below are project-authored requirements inferred from the evidence, not reported mill procedures. The parent audit integrates separate OEM evidence for process sequencing.

The R170 supplement is a publicly linked spreadsheet, but its contents were not retrievable in this environment. It is an access/reproducibility lead, not a verified dataset. Unavailable machine parameters or raw waveforms are not replaced with invented values. The original JSON records retain equation locations, access versions and numerical conflicts so these issues can be resolved before benchmark promotion.

## Actual implementation boundary

The following references concern code inspected on the saved research checkout, rather than capability claims in the historical report:

| Current file/test | Observed capability | Remaining operational gap |
|---|---|---|
| [operating.py](../../../physicroll/operating.py), `PHASES` and `assess_pass_operating_plan` | Declared phase-specific signal ranges; fixed equipment limits and observations have distinct roles. Non-steady model checks return `NOT_EVALUATED_PHASE`. | No acceleration phase, phase detector, event transitions or controller logic. Adding a label alone would not add dynamics. |
| [model.py](../../../physicroll/model.py), `solve` | One prescribed scenario; algebraic volume flow, force, power and roll-speed closure. Tension stress is converted to force using local section. | No inertia, drive current, elastic span tension or actuator differential equations. |
| [schedule.py](../../../physicroll/schedule.py), `run_prescribed_schedule` | Caller supplies every pass's speed, tension and friction. | Pass sequencing is not time integration through an acceleration transient. |
| [materials.py](../../../physicroll/materials.py) | Synthetic accumulated-strain history; metadata explicitly says temperature feedback and strain-rate dependence are false. | Changing a speed input does not activate calibrated rate-sensitive aluminium flow stress. |
| [test_checked_schedule.py](../../../tests/test_checked_schedule.py) | Per-pass ranges and independent replay checks, including prescribed interpass temperature. | No measured dynamic force/tension/current/gauge trajectory benchmark. |
| [test_passive_contact.py](../../../tests/test_passive_contact.py) | Selected synthetic energy/passivity and refinement cases. | Passing these cases does not prove ramp thermal coupling; the parent audit's large-step contact/entropy issue remains an activation gate. |

The current non-steady `NOT_EVALUATED` result is therefore appropriate. Future UI or 3D animation must not convert that status into a numerical confidence badge simply because motion is displayed.

## Proposed phase and model-activation contract

Record an operational event stream independently from material history. Each event has time, strip-coordinate mapping, stand/pass identity, observed or prescribed origin, sensor quality, uncertainty and causal reason. Equipment configuration has its own version. Control settings have units, source and validity intervals. Material state carries its constitutive and thermal provenance. None should silently overwrite another.

The following is a proposed offline/advisory taxonomy. It is deliberately incomplete until a particular mill's verified sequence and measurements are available; it is not a sequence of equipment commands.

| Context | Information needed | Defensible offline behaviour | Gate before enabling additional physics |
|---|---|---|---|
| Preparation/threading | Strip presence, current stand engagement, measured or prescribed speed, boundary-tension availability | Display topology and known boundaries. Mark unsupported bite establishment and free-end predictions. | Contact topology and low-speed model validity demonstrated; no division by near-zero angular speed to invent torque. |
| Tension establishment | Reel/interstand geometry, engaged boundaries, timestamps, force measurements and relevant drive states | Replay measured tension or explicitly prescribed boundaries. | Identified span compliance, speed/slip relation and actual actuator model; measured transient comparison. |
| Acceleration/ramp-up | Time-varying speeds and settings; entry state; actuator and material validity ranges | Run labelled quasi-steady snapshots where justified; otherwise return unsupported transient prediction. | Coupled drive/tension/gap dynamics independently validated over the requested ramp family. |
| Nominal rolling | Continuous observations, strip-coordinate alignment, operating window | Validated steady mechanics with evolving material history and only supported thermal/friction couplings. | Residual/error monitoring remains within the calibrated domain; nominal speed does not imply constant material or temperature. |
| Deceleration | Signed speed derivatives, changing tensions/settings and machine power convention | Replay or validated transient simulation; distinguish mechanical demand from motor electrical power. | Regenerative drive/loss model and deceleration-specific validation if reporting drive energy. |
| Tail-out/disengagement | Which strip boundaries remain physically engaged, measurement coverage | Remove invalid tension/contact assumptions; preserve final material state with uncertainty. | Boundary-release and topology-change model validated before predictive use. |
| Interpass dwell/reversal/anneal | Elapsed time, environment, direction/topology, treatment record | Prescribed state changes retain their provenance; no inferred recovery from elapsed time alone. | Validated cooling/recovery/recrystallisation models and treatment data, separately from motion phases. |

For a first offline milestone, phases can be supplied by a benchmark event file and checked against measured evidence. Automatic detection is a later feature requiring annotated events and uncertainty assessment. A phase name is not sufficient permission to activate a model: prerequisites include compatible geometry/material domain, known inputs, initialized state and demonstrated numerical stability. If a prerequisite fails, return an explicit unavailable/unsupported status and its reason; a fallback approximation must carry its own label.

Each pass can have a different phase sequence, settings and confidence envelope. Reel forces, interstand forces and tension stresses must not be interchangeable fields. Use the instantaneous local cross-section for force/stress conversion and document the width/strain assumption. For drive power, distinguish torque at each work roll, motor-side torque after gearing, both-roll sum, mechanical losses and signed electrical input. Those distinctions matter even when the material law is rate independent.

## Fidelity choices and dependencies

| Candidate | New states or representation | Qualitative cost | Appropriate use and acceptance requirement |
|---|---|---|---|
| Prescribed phase replay | Event timeline plus measured or declared boundaries | Low | First milestone: provenance, timestamps, phase coverage, no unsupported predictions. |
| Quasi-steady mechanical sampling | Repeated contact solutions at changing measured inputs; explicit history transfer | Low to moderate | Offline sensitivities within a validated slow-change regime. Compare against dynamic observations; assess relaxation versus ramp time scales. No universal ratio threshold is established here. |
| Reduced coupled dynamics | Span tension/compliance, motor and roll inertia, transmission elasticity, gap actuator, slip/bite coupling | Moderate, possibly stiff | Ramp/perturbation predictions after parameters and initialization are identifiable. Check limiting steady solution, step response, conservation, time-step convergence and independent measured transients. |
| Thermomechanical/lubrication coupling | Validated temperature states, heat partition, constitutive rate/temperature response and friction law | Moderate to high | Only after material/thermal audit gates pass. Compare independent speed, thermal and lubrication sweeps to separate confounded effects. |
| Three-dimensional transient reference | Roll stack/contact and strip fields with calibrated boundary histories | High | Selected research cases for local shape/stress/damage; verify mesh, time-step, inertia, contact and state-transfer errors. Not required for every advisory calculation. |
| Validated reduced surrogate | Bounded mapping learned from measured or verified higher-fidelity cases | Low evaluation cost; substantial preparation | Fast offline exploration with explicit domain and error bounds; held-out coils/ramp families, no extrapolation disguised as adaptation. |

Repeated steady solutions become inadequate when stored mechanical/thermal state or delays control the response. The necessary time scales depend on the equipment and process; derive or measure them rather than borrowing an activation speed. Similarly, friction, material rate response and heat transfer cannot be inferred independently from a single force-versus-speed trace. Start with controlled excitation and external measurements that make the selected parameters identifiable.

An advisory residual correction may be considered only after the baseline physics and data alignment are tested. Preserve the uncorrected prediction, correction version, training domain and uncertainty. A controller-gain change or continuously adapting feedback law belongs to a separate controls programme; none is authorized by this audit.

## Actionable next milestones and stop conditions

1. **Phase-aware benchmark schema.** Extend the research data contract with pass/stand/strip coordinates, engagement events, measured speed/tension/force/gauge, unit conventions, controller-mode metadata when available, timestamp uncertainty and missing-data flags. Keep fixed equipment constraints distinct from per-phase operating envelopes. Acceptance: replay conserves event order and refuses ambiguous units; an unavailable phase is never scored as a successful prediction.
2. **Paper reproduction dossier.** Resolve R167's final-version equations and omega convention; reconcile R170's body/table discrepancy and obtain its supplement if lawfully available. Request raw time-series evidence or author clarification through the user/parent where necessary; no outbound messages are sent by this task. Acceptance: every benchmark number has a specific version, condition, measured/modelled label and uncertainty status. Stop numerical import when these are unresolved.
3. **One bounded aluminium transient benchmark.** Select an evidence-backed alloy/temper and mill topology, then obtain synchronized independent force, tension, speed and thickness measurements with instrument response information. Prefer multiple coils with distinct steady/ramp segments and held-out operating conditions. Begin with prescribed replay. Stop before fitting an unidentifiable multi-parameter thermal/friction/material model.
4. **Choose the smallest necessary dynamics.** Compare quasi-steady residuals by phase. Add a measured/identified dynamic subsystem only where the error mechanism and available data justify it. Acceptance: independent improvement in transient trajectory error without losing steady accuracy, physical units, stability or conservation. State numerical and experimental uncertainty separately.
5. **Offline advisory release.** Provide reproducible scenario replay, phase annotations, confidence/domain indicators and exportable audit evidence. Verify deterministic replay, invalid-input handling and version rollback. No output writes to live controllers. Any future closed-loop integration requires its own safety, controls, plant validation and authorization programme.

No universal acceleration, tension-establishment time, sampling rate, sensor threshold or acceptable error is proposed. These are material requirements to resolve from the selected equipment, measurements and advisory use case. Research can proceed now on the schema, equation audit, synthetic invariants and offline comparison design without waiting for a plant name or claiming plant readiness.
