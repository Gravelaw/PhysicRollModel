# Implementation and validation traceability audit

Audit date: 2026-10-02. Immutable implementation baseline: [`caec37ef86a8b78e1eb88292ea6368bfb64bcbdc`](https://github.com/Gravelaw/PhysicRollModel/tree/caec37ef86a8b78e1eb88292ea6368bfb64bcbdc). The research branch was inspected without changing executable code. All 19 `physicroll/*.py` modules and all 12 test files were read. Research IDs `R001`–`R105` retain the original report bibliography numbering; they are source identities, not review-depth or validity scores. The accompanying [traceability.csv](traceability.csv) provides requirement → source/derivation → code/test → data → gap records, including explicitly absent capabilities.

**The repository is a verified synthetic research demonstrator with optional mechanics and energy extensions, not a calibrated aluminium process simulator.** Freshly executed baseline tests: **86/86 pass**. Conservation, dimensional conversion, independent reduced-equation comparisons and refinement checks provide useful software evidence. They do not establish alloy accuracy, product quality, threading capacity, safe plant settings or predictive route feasibility. An independent large-step thermal counterexample below shows why energy residuals alone cannot establish physical admissibility.

A separate, unmerged search implementation at [`ef0996acdd7af1799c62cb9a2e628e35acd26206`](https://github.com/Gravelaw/PhysicRollModel/tree/ef0996acdd7af1799c62cb9a2e628e35acd26206) is reviewed separately below. It is not counted as a baseline capability. This audit neither merges that branch nor authorizes deployment. The user has subsequently specified that further rolling development must use Codex cloud after research completion; this work is research documentation only, and the bounded optimiser remains a separate paused checkpoint.

## What the implementation actually does

| Path at baseline | Inspected behavior | Evidence boundary |
|---|---|---|
| `model.py`, `__init__.py`, `__main__.py` | Default public solver/CLI: exact rigid-circle geometry; mass continuity; illustrative pressure, dissipation and mean-speed closures; positive motoring torque; electrical-power division by supplied efficiency | Synthetic inputs required. Default solver is still the legacy heuristic, not the optional slab solver. |
| `slab.py` | Entry/exit RK4 pressure branches; interior neutral intersection; projected signed traction/torque/slip work; optional spatial hardening; coarse/fine grid checks | Leading-order sliding contact; no through-thickness stresses, elastic recovery, sticking or transient threading. |
| `contact.py` | Damped fixed point between force and circular Hitchcock radius; physical shaft radius retained for speed/torque | Circular geometry only; no uniqueness proof, noncircular elasticity, roll stack or stand-gap closure. |
| `materials.py` | Synthetic isotropic power hardening; integrated mean stress; accumulated equivalent strain and append-only pass history; assumed strain/temperature envelopes | No fitted alloy card, rate effect, temperature feedback, anisotropy, recovery, precipitation, recrystallisation, annealing or damage. |
| `thermal.py` | Standalone two-capacity explicit Euler heat-budget step with an eigenvalue-based nonoscillatory time bound | Supplied powers, contact area and coefficients; not a flowing-bite temperature field. |
| `energy_handoff.py` | Piecewise-linear heat-capacity integration/inversion; steady strip enthalpy and finite aggregate-roll storage; prescribed contact heat or implicit midpoint conductance | Pass heat partitions, cooling export, conductance and roll effective mass remain supplied. Midpoint contact has the finite-step admissibility gap described below. |
| `schedule.py` | Gauge arithmetic; legacy heuristic pass replay; explicit local operating plans; optional externally prescribed interpass temperatures | Not a route generator; inherited single-layer/gauge/reduction guards. Legacy handoff checks are weaker than checked replay. |
| `checked_schedule.py` | Explicit per-pass spatial-slab/circular solver selection; required adjacent handoffs; optional energy composition; per-pass declared-bound reporting | No interpass time law, anneal or thermal-force coupling. Nonviolating declared checks remain `INDETERMINATE`. |
| `operating.py` | Distinct setpoints, predictions, observations, boundary declarations and fixed equipment limits; phase-qualified ranges | Steady-state outputs only; no controller. Regenerative torque/power capacity is explicitly unevaluated. Missing ratings are unknown. |
| `literature.py` | Forty-nine audited numeric imports; conditional three-pass AA5052 comparisons; two-gauge mesh search | Three author-reported force/slip pairs; unqualified model validation blocked by unresolved source semantics/history. Search fixes pass count and operating values. |
| `studies.py` | Ranks an explicit finite list of single-pass candidates under declared synthetic constraints | No candidate generation, learned model, robust optimisation or general schedule planning. |
| `lubrication.py` | Fluid observations and declared effective friction metadata | No lubricant-film, viscosity-to-friction, supply-flow-to-cooling or asperity model. A `calibrated` flag is caller assertion, not an executed fit. |
| `equipment.py` | Synthetic static stand compliance bookkeeping and reel power/inertia snapshot around the legacy result | Prescribed exit gauge; `F/K` does not solve a coupled loaded-gap problem. No reel dynamics or measured mill capacity. |
| `observations.py`, `sensors.py` | Measurement-conversion helpers; 15 disconnected sensor types/markers; prediction/reading separation | No actual readings, calibrated instruments, uncertainty model, parcel alignment, historian or PLC connection. |
| `profile.py` | Integrates supplied widthwise thickness, membrane mismatch and curvature fields | Crown/wedge/strain diagnostics only; neither predicts those fields nor free-strip waves/flatness. |
| `units.py` | Dimension-qualified SI conversion, Celsius offsets and source/convention provenance | Does not infer units, quantity scope, radius versus diameter, or whether a reported force was total/per width. |

The Blender generator remains a parameterized static generic four-high scene linked to the legacy process result. It has true-gauge strip geometry and stable equipment IDs, not live assets or a spatial stress/temperature solution. `scripts/package.py` builds a portable archive with the selected source/docs/artifacts and excludes Git/caches; it is packaging infrastructure, not a deployed application. There is no CI directory at this baseline and no service/API, authentication, installer/update service, observability pipeline or industrial control interface.

## Evidence classes and current measured-data limit

Keep four questions separate: (1) whether a source equation was read, (2) whether code implements the declared approximation, (3) whether numerical error is controlled, and (4) whether measured data validate it in the intended process domain. The suite gives substantial evidence for (2) and (3). A literature formula or an OEM capability page cannot establish (4).

Current imported experimental comparison consists of **three author-reported total separating-force values and three forward-slip fractions** from R062. It has no raw traces, instrument uncertainty, repeat coils, measured torque or measured thermal outcomes. Author-calculated forces/slips/radii are stored separately from measured values. There is no fitted training set and no independently held-out validation set. R107 Hulamin supplies generic AA5052 density context, not a benchmark material card; R106 AA8015 heat-transfer evidence is research motivation only, with no thermal coefficients imported. The additional sensor links R123–R133 identify instrumentation context, not installed calibration. Synthetic regression outputs are not observations; data marked `measured` by a caller are not independently authenticated.

Fresh primary checks on 2026-10-02 were targeted to implemented equations: R012 preprint v1 Sections 2 and 3.1, R006 Eq. 1 and experimental context, and R062 Eqs. 2–9 and Tables 1–2. This is a fresh equation/table review, not a claim that this implementation audit reread every source in full. Other source IDs below express inherited research lineage or candidate future methods; their actual access depth belongs to the corpus ledger.

- **R012:** the [2024 v1 preprint](https://arxiv.org/html/2408.01347v1) uses half-thickness and shear-yield scaling; code uses dimensional full thickness and contact pressure. Its constant-strength leading-order limit motivates `slab.py`. The variable-strength extension and signed projected work are repository derivations. Higher-order through-thickness solutions are not implemented. Journal equation numbering must not be substituted for the v1 numbering without checking.
- **R006:** [Li et al. Eq. 1](https://www.jstage.jst.go.jp/article/isijinternational/58/4/58_ISIJINT-2017-623/_html/-char/en) supports the circular compliance expression. Its experiment is stainless steel and documents noncircular limits. No steel flow curve, measured accuracy, friction fit or roll modulus from that experiment validates this aluminium implementation.
- **R062:** [Shao et al. publisher text](https://www.iieta.org/journals/ijht/paper/10.18280/ijht.330113) agrees with the imported process and force/slip table entries. The radius/diameter labels conflict; Eq. 3 has unspecified accumulation coefficient `a`; stress/strain pairing and speed location remain unresolved. The printed friction branches and power expressions require dimensional/physical reconstruction before reuse. The source's mechanical comparison is not measured heat validation.

R030 Choi 2026 tension quantities remain quarantined: no quantity enters these input files, code paths or test constants. Do not introduce those values until original units, force/stress/line-load scope, local area and any normalization are resolved. A conversion factor cannot repair an unknown quantity definition.

## Equation, sign and unit audit

The following are this audit's compact descriptions of the inspected implementation. They are not assertions that every equation is copied from a named publication. `h` is full thickness, `b` strip width, `R` physical shaft radius, `Rc` circular contact radius, `Y` uniaxial flow stress, `Kps=2Y/sqrt(3)`, `x` increases entry→exit, `q` is positive contact compression and `sigma_x` is positive longitudinal tension. R012's hydrostatic `p` is not code `q`.

| ID | Implemented expression/convention | Unit/interpretation audit | Main evidence |
|---|---|---|---|
| E01 | `L=sqrt(Rc*(h0-h1)-(h0-h1)^2/4)`; circular gap; `Qv=b*h0*v0=b*h1*v1` | `L` m; `Qv` m³/s. Constant width/density within one pass. Exact circle geometry does not make projected mechanics exact finite-angle mechanics. | `test_model`, `test_mechanics_audit`, `test_contact_increment` |
| E02 | `epsilon_h=ln(h0/h1)`; `Delta epsilon_eq=2/sqrt(3)*epsilon_h` | Positive compression magnitude, dimensionless. Equivalent strain assumes homogeneous incompressible plane strain without redundant shear. State sums increments; it is not engineering reduction or an anneal state. | `test_integral_and_history`, gauge telescoping, variable-hardening work integral |
| E03 | Legacy `pbar=Kps*(1+mu*L/hmean)-(sigma_in+sigma_out)/2` | Pa. This is a heuristic mean-pressure closure. Mean roll surface speed `(v0+v1)/2` is also assumed. | Baseline regression/scaling; no measured calibration |
| E04 | Slab `h*q'=h*Kps'+Kps*h' +/- 2*mu*q`; endpoints `q=Kps-sigma_tension` | Pa equation after multiplying derivative by m. Variable law integrates `z=q-Kps=-sigma_x`, avoiding numerical differentiation of `Kps`. Plus traction before neutral, minus after. | Independent exponential-midpoint pressure references and constant-hardening limit |
| E05 | `tau=+/-mu*q`; reject `mu*q>Y/sqrt(3)`; require unique interior branch crossing | Pa; no silently clipped sticking region. Rejecting sticking does not model it. Conservative unassisted `tan(alpha)<=mu` is a threading screen. Established mode bypasses that screen with a flag, not a threading certificate. | Yield-cap, neutral-root, tension-sensitivity and established-mode tests |
| E06 | `F=b*integral(q dx)`; `T_one=R*b*integral(tau dx)`; `P_roll=2*T_one*U/R` | Total stand separation force N is not doubled. Torque N·m is per work roll; mechanical roll power W includes both rolls. `R`, not `Rc`, is shaft lever arm/speed radius. Elastic surface motion/work are omitted. | Dimensional/scaling tests; independent pressure quadrature; circular shaft-radius test |
| E07 | `P_tension=Qv*(sigma_out-sigma_in)`; `Pplastic=Qv*integral(Y d epsilon_eq)`; `Pslip=2*b*integral[tau*(U-v) dx]` | W. Local tension force is `sigma*b*h`; front pulling supplies positive work, back tension extracts it. Slip work already counts both interfaces. Negative roll torque can be admissible in slab; legacy rejects regeneration. | Work residual refinement; independent material integral; regenerative sign tests |
| E08 | `Rc=R*(1+16*(1-nu²)/(pi*E)*F/(b*draft))` | `E` Pa; compliance Pa⁻¹; `F/(b*draft)` Pa. Width cancels under geometric force scaling. Radius ratio ≤1.5 and E sanity limits are analyst guards, not calibrated validity limits. | R006 Eq. 1; zero-load/width checks; independent bisection |
| E09 | `Y(epsilon_eq)=Y0+K*epsilon_eq^n`; pass mean is analytic integral over the strain interval | Pa and dimensionless strain. Converting a log-thickness law requires changing its coefficient. No temperature/rate dependence despite a carried temperature field. | Small-interval stable mean, constant limit, history tests |
| E10 | `H(T)=integral cp(T)dT`; `mdot*Delta H_strip=beta*Pplastic+f*Pslip+Qc-Qcool,s`; `Mroll*Delta H_roll/dt=(1-f)*Pslip-Qc-Qcool,r` | `cp` J/(kg·K); H J/kg; all balance terms W. Strip uses kg/s; finite roll uses kg and seconds. `1-beta` is an allocation of mechanical work, not a predicted dislocation-energy state. | Independent constant-cp solution, exact inverse/knot tests, scale/duration tests |
| E11 | `Qc=G*(Tr,mid-Ts,mid)`, arithmetic endpoint midpoints | G W/K totals both interfaces; unlike `thermal.py` contact coefficient W/(m²·K), multiply by an explicitly scoped area once only. Positive Qc heats strip. Bracketed scalar solve checks the stated law, not finite-step monotonicity; see finding I01. | Analytic midpoint solution, zero/reverse contact, property-domain and entropy-proxy tests |
| E12 | Static `stand_extension=F/Kstand`; `unloaded_gap=h_exit-F/Kstand` | Kstand N/m; gap m. Static accounting at a prescribed loaded gauge. Stand reaction is the same bite force, not an additional force to add. | `test_load_path_and_gap`; no stiffness identification or roll-stack validation |
| E13 | Tension stress `F/(b*h_local)`; wrap tension `(reaction-tare)/(2*sin(theta/2))`; hydraulic thrust `pc*Ac-pr*(Ac-Ar)` | Pa versus N retained; wrap geometry/equal tensions must be qualified; pressure-derived actuator force is not extra bite force. | Independent observation conversion tests |
| E14 | Reel shaft torque `+/-Tension*radius+I*alpha+loss`; slip `(v_exit-U)/U` | N·m and dimensionless. Shaft direction, losses and acceleration are caller-declared; speed floor rejects an ill-conditioned slip denominator. | Winding/payoff sign and speed/radius tests |

There is no detected factor-of-two, radius/diameter, tension-force/stress or W/W·m⁻² error in the inspected standard mechanics and first-law accounting paths. This statement is bounded by the declared approximations and tested domain. Unknown source semantics and omitted physics remain gaps even when dimensional arithmetic passes.

## State, equipment and control must remain separate

| Category | Present representation | Required next representation |
|---|---|---|
| Strip state | Alloy/temper labels, accumulated equivalent strain, temperature, history; each pass returns next state | Identified initial state, validated constitutive variables, uncertainty, batch/coil/material coordinates; optional evolution laws only with data |
| Roll/equipment state | Nominal radius, optional elasticity, supplied aggregate roll temperature/mass and `roll_body_id`; static reel snapshot | Distinguish wear/grinding, thermal profile, changing reel radius, stand stiffness and actual asset identity from commanded settings |
| Pass settings | Explicit gauge, speed, entry/exit tension and supplied friction/boundary conditions | Per-pass/per-phase choices with provenance; friction often latent/estimated rather than an actuator |
| Equipment capacities | Caller-supplied stand/reel/drive ratings | Qualified motoring and regenerative ratings, phase/duty limits, allowable envelope; absence remains unknown |
| Observations | Separate declared values, provenance and disconnected sensor fields | Calibrated and aligned raw observations plus transformation uncertainty, drift, quality and missing-data policy |
| Control | No control law or equipment-write path | Separate control/safety programme, plant authorization and validated integration before any closed-loop work |

Every pass can change speeds, tensions, valid ranges, lubricant/coolant conditions, roll set, interpass time and material state. The checked replay requires explicit handoffs and does not inherit an earlier pass's operating envelope. Different steady throughputs between reversing passes can be valid; instantaneous equal flow is required within a pass, not silently across a stored coil. Direct temperature carry represents an explicit no-interpass-exchange assumption, not predicted cooling. A prescribed temperature change does not justify resetting strain or declaring a new temper.

## New audit findings and actionable acceptance gates

**I01 — required numerical/physical gate before predictive thermal use.** The passive midpoint contact law can be energy-conserving and locally passive at its representative temperatures while violating whole-step thermal monotonicity and the constant-cp entropy balance. The public API admits the diagnostic below. It follows the existing tests' isolated pure-contact construction: mechanical heat/work fields are zeroed consistently to examine the thermal operator, not to claim a physically loaded rolling experiment.

With strip inlet 300 K, roll inlet 320 K, `mdot=10.8 kg/s`, strip `cp=900 J/(kg K)`, roll mass `1 kg`, roll `cp=500 J/(kg K)`, duration `5 s`, G `1e6 W/K`, zero other heat sources/export, the output is:

| Quantity | Observed result |
|---|---:|
| Strip outlet | 300.4072513547 K |
| Roll outlet | 280.4151683211 K |
| Contact heat into strip | 3958.4831678943 W |
| Thermal first-law residual | −2.21×10⁻¹⁰ W |
| Implemented midpoint entropy diagnostic | +0.0001738681 W/K |
| Whole-step entropy rate, `mdot*cp_s*ln(Ts,out/Ts,in)+(Mroll*cp_r/dt)*ln(Tr,out/Tr,in)` | **−0.01897878795 W/K** |

The finite roll drops below the colder stream inlet although it has no external cooling. This is the known type of overshoot admitted by a centered finite-step update; a small algebraic root residual does not detect it. The result does **not** show that the bundled ordinary demo is wrong, and it is not an experimentally observed mill failure.

For the zero-source constant-cp case define `Cs=mdot*cp_s` and `Cr=Mroll*cp_r/dt` in W/K. The implemented solution is `Qc=G*(Tr,in-Ts,in)/(1+G*(1/Cs+1/Cr)/2)`. For a hotter roll, non-overshoot requires `Qc <= Cr*(Tr,in-Ts,in)`. Thus if `Cr<Cs`, `G*(1/Cr-1/Cs)/2 <= 1` is a necessary pure-contact roll bound. For `Cs<Cr`, an analogous strip-outlet bound applies. These are derived diagnostic limits, not a proposed universal calibrated process law.

Next task: select a monotone thermal update or enforce physically justified step/advection bounds and substepping, with constant/variable-cp maximum-principle tests, exact entropy accounting `Delta s=integral cp(T)/T dT`, zero/reverse heat-flow limits and step refinement. Revisit large-G spatial strip exchange too: midpoint inlet/outlet exchange can overstep a reservoir even with negligible roll-temperature change. Acceptance must apply over the intended complete range; checking only nonnegative `Qc*(1/Ts,mid-1/Tr,mid)` is insufficient. Keep this unsupported regime unavailable to predictive optimisation until resolved. No fix was made during this research audit.

**I02 — legacy replay contract parity.** `run_prescribed_schedule` verifies adjacent gauges but has no corresponding width-event or density-continuity check. The newer checked replay requires width-change provenance and rejects density change without a model. A fresh two-pass probe accepted widths 1.0→0.9 m and densities 2700→2800 kg/m³ with no interpass events, returning `SYNTHETIC_UNCALIBRATED_PRESCRIBED_SCHEDULE`. Thus legacy passes can carry the same material identity across unqualified width/density changes. Use checked replay as the research route baseline; either deprecate legacy multi-pass replay or add equivalent explicit interpass contracts. A width change may be a real trimming event, but must have material/mass provenance; this audit is not asserting that width must always be constant.

**I03 — source and material identification blocks.** R062's three force/slip pairs cannot jointly identify prior strain, hardening parameters, friction, roll compliance and unresolved radius/strain/speed conventions. Alternative parameter choices can compensate in force. Acquire identified flow curves, incoming temper/history, actual roll geometry, measured speed locations/torque and repeated coils before fitting; then hold out complete coils/material batches or regimes. Report force, torque and slip residuals jointly, with uncertainty. Do not tune the assumptions to obtain an attractive force fit and call it independent validation.

**I04 — capability/public-entrypoint drift.** README preserves historical statements that roll flattening, thermal and alloy hardening are not solved, next to optional extensions that implement bounded approximations. The public `physicroll.solve` and CLI still select the legacy model. Publish one versioned capability matrix and explicit solver selection before UI/advisory packaging; distinguish not implemented, prescribed/diagnostic, uncalibrated and validated. Old reports and artifacts should remain historical records with their original dates.

**I05 — release and artifact reproducibility gap.** Fresh smoke/hash and Blender structure checks succeed. The optional OpenUSD verifier cannot run in the selected environment because `pxr` is absent. Historical reopen evidence remains historical; today's checksum success is not a fresh USD semantic reopen. Reproducible release work needs the pinned optional dependency environment, automated package/clean-install/asset checks and a current solver/data/schema manifest. A passing scene topology test validates geometry, not process physics.

**I06 — partial limit coverage is not feasibility.** `operating.py` correctly reports missing-model and nonsteady checks as unevaluated, and unprovided ratings do not become infinity. Keep this in every future ranking/UI export. The existence of some `WITHIN_DECLARED_LIMIT` results does not show all mill, quality, duty, thermal or actuator constraints were evaluated. Thermal boundary metadata and generic OEM capability claims are not measured heat-transfer laws or installed limits.

## Separate bounded-search branch review

`ef0996acdd7af1799c62cb9a2e628e35acd26206` adds `schedule_search.py`, five tests and a research note. It was read with `git show` and tested from a `git archive` extracted into `/tmp/physicroll-search-audit`; the shared research checkout was not switched or edited.

The branch enumerates finite decreasing gauge paths, exact mandatory checkpoints, bounded pass counts and explicit per-pass speed/tension choices. A full-route callable produces the result; `checked_replay` provides the intended adapter to `run_checked_schedule`. It preserves errors/bound violations, checks route and rating consistency, chooses fewer passes first, then the smallest available maximum normalized equipment utilization, and independently repeats the selected route for exact reproducibility. No route is marked physically feasible: selection reports `SELECTED_DECLARED_BOUNDS_INDETERMINATE`.

This is a useful **finite candidate-search scaffold**, not a validated optimiser or a general optimal route solution. The candidate builder owns all other inputs, material and roll histories, thermal/interpass conditions and limits. Its structural return checks do not prove that an arbitrary supplied callable actually ran the checked solver; the official integration should bind and version the reviewed adapter. No cache merges equivalent gauges while losing history, which is appropriate. Candidate enumeration is combinatorial; explicit caps prevent accidental very large searches, but the selected replay adds one invocation beyond the reported candidate count. No Pareto search, uncertainty propagation, time/energy objective, anneal decision or continuous global-optimum proof is implemented.

The five new committed tests use synthetic oracle responses, so they check search contracts rather than actual rolling integration. The independent audit additionally ran four real two-pass candidates using `checked_replay`, exact 2.00→1.50→1.20 mm gauges, supplied synthetic material/temperatures and two speeds per pass. Every selected pass met numerical convergence, the equivalent-strain state carried correctly, and selection remained indeterminate. This supports interface integration, not aluminium accuracy. The isolated full branch suite passed **91/91 tests in 8.396 s**.

The baseline already contains a distinct `literature.optimise_gauges` mesh search: fixed three-pass AA5052 geometry endpoints, two intermediate gauges, peak-force objective, fixed reported speeds/tensions/friction and an assumed observed-reduction range. It is wrong to describe baseline as having no search whatsoever. Neither existing search resolves the physical/evidence gaps above. Coordinate branch adoption through the parent project; do not conflate branch capabilities or merge them as part of this audit.

## Verification executed in this audit

All commands ran in `/workspace/PhysicRollModel` at baseline unless otherwise specified. No tracked executable, scenario or artifact file was regenerated in place.

| Command/check | Fresh result | Interpretation |
|---|---|---|
| `python --version` | Python 3.12.14 | Current interpreter |
| `python -m unittest discover -s tests -v` | 86 tests passed, 8.409 s | Baseline suite; numerical/contract verification |
| `python scripts/smoke.py` | PASS; 10.8 kg/s, 2,200,485.4436 N, 220,924.0974 W baseline outputs and bundled checksums | Legacy regression plus selected optional checks and artifact identity |
| `blender -b artifacts/mill.blend --python-exit-code 1 --python scripts/check_blend.py` | PASS, 78 unique equipment IDs; true strip gauge, gap, width and closed mesh; Blender 4.3.2 | Fresh `.blend` structural reopen; not a fresh render/visual physics check |
| `python scripts/check_usd.py` | Could not run: `ModuleNotFoundError: No module named 'pxr'` | Optional verifier dependency absent; no fresh USD semantic claim |
| `python scripts/run_contact_increment.py --cells 512 --out /tmp/physicroll-contact-research-audit` | See fresh comparison below | Independent output directory; conditional comparisons only |
| Isolated pure-contact probe reproduced below | Overshoot and negative global entropy balance reproduced | Open I01; existing tests do not cover this physical gate |
| `python -m unittest discover -s tests -v` in `/tmp/physicroll-search-audit` | 91 tests passed, 8.396 s | Separate `ef0996a` branch only |
| Real `checked_replay` integration with four two-pass candidates | PASS, all selected passes converged, strain continuity exact, bounds `INDETERMINATE` | Extra integration check beyond mock search tests |

### Fresh conditional AA5052 rerun

The 512/1024-cell structural study reproduced the following mean absolute relative residuals over the same three force/slip pairs. These numbers are **conditional comparisons**, not validated error guarantees; no parameters were fitted during the run.

| Structure | Force mean absolute relative residual | Slip mean absolute relative residual |
|---|---:|---:|
| Rigid contact, pass-mean hardening | 6.74% | 41.96% |
| Rigid contact, spatial hardening | 4.63% | 34.53% |
| Circular contact, pass-mean hardening | 8.07% | 53.04% |
| Circular contact, spatial hardening | 7.94% | 44.80% |

Maximum mechanical work residual over the executed admissible structural/hypothesis cases was `7.456169673692192e-7` relative. Zero assumed prior strain was rejected because first-pass tension reaches the assumed zero incoming strength. Adding structural fidelity did not monotonically improve agreement under these uncertain inputs. The remaining slip mismatch is a clear reason to avoid optimizing physical recommendations against a force-only fit. Fresh temporary run outputs are `/tmp/physicroll-contact-research-audit`; durable inputs, commands and comparison numbers are recorded here, while no regenerated benchmark files were committed.

Test-file counts reconcile to 86: `test_checked_schedule` 4; `test_contact_increment` 10; `test_energy_handoff` 13; `test_equipment_sensors` 4; `test_literature` 3; `test_mechanics_audit` 11; `test_model` 9; `test_observations` 4; `test_passive_contact` 6; `test_schedule` 9; `test_studies` 2; `test_v03` 11.

The strongest independent verification includes exponential-midpoint integration versus production RK4 for constant and variable strength, a scalar bisection versus the circular fixed point, exact constant-cp and enthalpy-inverse checks, neutral-point edge cases, dimensional/width/speed scaling, signed regeneration and mass/mechanical/thermal conservation. Baseline-output regression alone is weaker evidence because it only detects change against previous code. None of these tests supplies empirical plant validity.

### Reproduce I01 without changing project files

Run the following from the baseline repository. The zero-source construction isolates the thermal operator and uses the same test methodology as the existing thermal suite.

```bash
python - <<'PYPROBE'
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
PYPROBE
```

### Reproduce the separate-branch integration probe

Create a temporary read-only source snapshot with `mkdir -p /tmp/physicroll-search-audit` followed by `git archive ef0996acdd7af1799c62cb9a2e628e35acd26206 | tar -x -C /tmp/physicroll-search-audit`; run its suite from that directory. The following was executed there after the 91-test suite. Every material value and equipment bound here is synthetic numerical-test input, not a proposed material card or mill limit.

```bash
python - <<'PYSEARCH'
from dataclasses import replace
from physicroll.model import Scenario
from physicroll.materials import MaterialState, PowerHardeningLaw
from physicroll.checked_schedule import CheckedPass, InterpassHandoff
from physicroll.operating import PassOperatingPlan, EquipmentLimits
from physicroll.schedule_search import (OperatingChoice, SearchSpace,
                                       search_schedules, checked_replay)
state = MaterialState('demo', 'unknown', .1, ('synthetic audit',), 300.)
law = PowerHardeningLaw('demo', 'unknown', 100e6, 100e6, .3, 'synthetic audit')
slow = OperatingChoice(1., 10e6, 15e6, 'synthetic audit choice')
fast = replace(slow, entry_speed_m_s=2.)
space = SearchSpace((.002, .0015, .0012), (.0015,), 2, 2,
                    ((slow, fast), (slow, fast)), 4)
def build(gauges, choices):
    passes = tuple(CheckedPass(
        Scenario(f'p{i+1}', True, gauges[i], gauges[i+1], 1.,
                 c.entry_speed_m_s, .25, 2700., 120e6, .08,
                 c.entry_tension_pa, c.exit_tension_pa, .9),
        PassOperatingPlan(f'p{i+1}'), 'spatial_slab', 256, 'unassisted',
        (0., 3.), (273.15, 420.)) for i, c in enumerate(choices))
    handoffs = tuple(InterpassHandoff(i+1, 'prescribed', 300.,
                     'not_modeled', None, 'synthetic audit temperature')
                     for i in range(len(passes)-1))
    return checked_replay(passes, state, law, interpass_handoffs=handoffs,
        equipment_limits=EquipmentLimits('synthetic audit bounds',
            max_separating_force_n=1e9, max_roll_mechanical_power_w=1e9))
r = search_schedules(space, build)
a, b = r['selected']['checked_replay']['passes']
assert r['evaluations'] == 4
assert all(p['mechanics']['numerical_converged'] for p in (a, b))
assert (b['mechanics']['material']['state_in']['accumulated_equivalent_plastic_strain']
        == a['mechanics']['material']['state_out']['accumulated_equivalent_plastic_strain'])
assert r['selected']['checked_replay']['declared_bounds_status'] == 'INDETERMINATE'
print(r['status'], r['evaluations'], r['selected']['gauges_m'])
PYSEARCH
```

Observed: `SELECTED_DECLARED_BOUNDS_INDETERMINATE 4 (0.002, 0.0015, 0.0012)`.

## Validation gates before moving to later project phases

1. **Resolve inputs before fitting:** exact material/temper/history, full-thickness and force/torque/speed conventions, qualified geometry/limits, measured uncertainty and source-access gaps. Unresolved R030 tensions stay excluded; R062 alternative interpretations stay explicit.
2. **Complete numerical domain gates:** close I01; preserve neutral/sticking/noncircular/domain rejections; establish full-coupling refinement and conservation tolerances against independent references. Tolerances now in code are numerical thresholds, not acceptable prediction-error percentages.
3. **Calibrate and validate by domain:** identify constitutive response independently where possible, then fit contact/friction/thermal parameters with complementary observables; perform sensitivity/identifiability analysis and hold out entire coils/runs/material batches. Acceptance thresholds require data uncertainty and the user-selected decision purpose; inventing a universal ±5% target would be unjustified.
4. **Only then rank practical scenarios:** replay every candidate with its full state, pass-local inputs and actual limits. Unknown capacity or quality constraints keep the recommendation indeterminate. Require out-of-domain rejection, robust sensitivity and held-out backtests before operator advice.
5. **Package local-first offline/advisory tooling:** explicit solver/version/data provenance, reproducible environments, artifact checks, domain/uncertainty display and safe failure. A usable UI/3D view should display synthetic/conditional/calibrated status next to results, not convert a static scene into a claim of an operating digital twin.
6. **Plant advisory and live control are different endpoints:** qualified read-only ingestion and human-reviewed recommendations require their own integration validation. Any live closed-loop actuation remains outside this work and needs a separate authorized industrial safety/controls programme.
