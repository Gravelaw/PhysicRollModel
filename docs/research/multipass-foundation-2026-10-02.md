# Multi-pass rolling: bounded development foundation (2026-10-02)

The companion [theory and source register](multipass-theory-2026-10-02.md)
records derivations, operating roles, foil topology and the later search design.

## Request and interpretation

The example **6 mm → 0.05 mm** means a 6 mm entry gauge and a **0.05 mm final
exit gauge**, reached through several passes. The suggested intermediate gauges
are illustrative, not a material card or an approved mill schedule. Alloy, temper,
roll stack, mill ratings, operating ranges and interpass times have not been given.

## Primary-source basis

| Source | What it establishes here | What it does not establish |
|---|---|---|
| [ABB, *Rolling models*, ABB Review 1/2009, pp. 43–47](https://library.e.abb.com/public/cab489262e40ea6ac1257beb0029324a/ABB%20Review_1_2009_72dpi.pdf) | Cold rolling uses sequential passes. Scheduling determines pass count and gauge distribution using grade, width, start and finish gauges, mill limits and practice. Presets include speed, tensions, force, torque and cooling. Threading, steady rolling, deceleration and tailout are distinct phases. | No universal pass reduction, signal range or valid settings for this mill. The article describes a scheduling/preset system; this module only evaluates prescribed passes. |
| [Shao et al. (2015), AA5052 three-pass article](https://www.iieta.org/journals/ijht/paper/10.18280/ijht.330113) | The existing repository preserves measured and source-model data for three passes from 4.10 to 1.72 mm. | No qualification of a 6 mm → 0.05 mm path or inferred initial temper. See [AA5052 study](../aa5052-study.md). |
| [Fleck et al. (1992), *Cold rolling of foil*, DOI 10.1243/PIME_PROC_1992_206_064_02](https://sage.cnpereading.com/storage/sage/journal/article/PIB/1992/PIB_1992_206_2/unzip/10.1243_PIME_PROC_1992_206_064_02.pdf) | Thin-foil contact needs a noncircular roll-deformation and no-slip treatment under relevant conditions. | No universal gauge threshold at which every mill changes model. The demonstrator's 300 µm cutoff is an existing conservative software guard. |
| [European Aluminium (2018), *Environmental Profile Report*, §6.1 and glossary](https://european-aluminium.eu/wp-content/uploads/2023/01/European-Aluminium_Environmental-Profile-Report-2018_full-version.pdf) | Foil production can use single or double rolling, so layer/pack interpretation matters near the target gauge. | A product category threshold alone is not a mechanical model-validity threshold or a command to double roll this example. |

## Kinematics and model connection

For prescribed full gauges `h[0] > h[1] > … > h[N] = target`, pass `i` has
`r[i] = 1 − h[i+1]/h[i]` and logarithmic thickness strain
`e[i] = ln(h[i]/h[i+1])`. The existing homogeneous incompressible plane-strain
idealisation uses `Δεeq[i] = 2/√3 · e[i]`. Therefore
`Σe[i] = ln(h[0]/target)` regardless of how the intermediate gauges are split.
These are kinematic identities, not force/temperature/quality predictions.

`physicroll.schedule.GaugeSchedule` audits this path without claiming a feasible
mill pass. Its per-stage flags reflect only existing single-pass model guards:
exit gauge ≥300 µm and reduction ≤50%. A stage that passes these two checks
still needs all other model inputs and checks. The existing `Scenario.validate()`
also screens width/gauge, gauge/radius, tensions and friction; the existing
mechanics calculation checks bite, power and traction. The 50 µm target crosses
the software foil guard; `run_prescribed_schedule()` rejects it with the pass
number. There is no silent extrapolation through that stage.

`run_prescribed_schedule()` accepts one explicit `Scenario` and one
`PassOperatingPlan` bound by pass name per pass, and requires an explicit
single-layer, per-layer full-thickness gauge basis. It validates every pass
and exact gauge handoff before calculating. The current executable mechanics is the **legacy synthetic
heuristic** with the existing mean-stress hardening law. Its force, torque,
power and assumed forward slip remain illustrative. The new workflow does not
replace them with a validated slab, foil or stand model. Each pass has its own
speed, two tensions and friction; no previous pass value/range is copied.
Material identity, prior equivalent strain and temperature are explicit.
Accumulated strain and history pass forward. Temperature changes only through
a supplied `InterpassTemperature` with provenance. There is no computed
interpass cooling, thermal feedback, recovery or annealing reset.
Because the current `Scenario` contract requires `mean_flow_stress_pa`, the
caller still supplies that value for its preliminary single-pass validation;
`pass_with_history()` then replaces it with the hardening-law interval mean.
Both numbers are exposed in `model_parameters`. A future pass-input contract
should remove that redundant field. Its preliminary tension check can reject
a case whose derived hardening stress would otherwise admit it; that is an
explicit current-interface limitation, not evidence of physical infeasibility.

The operating plan separates roles: `Scenario` contains requested steady inputs;
`SignalRange` contains caller-declared phase-specific bounds; `ObservedSignal`
contains separate readings; solver output contains predictions. Only declared
steady input and model-output ranges are compared. Declared coolant/lubricant
flow inputs may also be checked against pass ranges but do not change mechanics.
Threading/deceleration/tailout range checks report `NOT_EVALUATED_PHASE`,
temperature prediction reports `NOT_EVALUATED_NO_MODEL`, and cooling/lubricant
descriptions remain declarations.
Optional `EquipmentLimits` represent fixed hardware ratings separately from
pass/phase ranges. Violations propagate to a top-level
`DECLARED_BOUNDS_VIOLATED` result. Otherwise bounds status remains
`INDETERMINATE` and coverage reports absent/unevaluated checks. Missing limits
are unknown, not unlimited. Passing supplied ranges is not a process-safety
or quality certificate.

## Traceability and acceptance checks

| Claim / equation | Code | Test |
|---|---|---|
| `Σln(h_i/h_i+1)=ln(h_0/h_N)`; `Δεeq=2/√3 ln(h_i/h_i+1)` | `schedule.py:inspect_gauge_schedule` | `test_schedule.py:test_illustrative_path_and_foil_boundary` |
| Exact consecutive gauge handoff; strict reduction; target equality | `schedule.py:GaugeSchedule.validate`, `run_prescribed_schedule` | `test_schedule.py:test_rejects_jump_reverse_target_and_bad_numbers`, `test_all_passes_preflight_and_no_inherited_plan` |
| Prior strain and supplied temperature handoff; no inferred reset | `schedule.py:run_prescribed_schedule`, `materials.py:pass_with_history` | `test_schedule.py:test_state_handoff_and_distinct_pass_ranges` |
| Per-pass role, units, provenance and phase range checks | `operating.py` | `test_schedule.py:test_state_handoff_and_distinct_pass_ranges`, `test_bad_units_duplicates_and_event_position`, `test_declared_range_and_hardware_violations_are_visible` |
| Limit violation propagation, plan binding and boundary inputs | `schedule.py`, `operating.py` | `test_schedule.py:test_all_passes_preflight_and_no_inherited_plan`, `test_declared_boundary_flow_is_pass_local_input` |
| Stable strain calculation for extremely large and tiny gauge ratios | `schedule.py:_log_thickness_ratio` | `test_schedule.py:test_extreme_positive_gauges_audit_stays_finite` |
| Foil and reduction rejection before mechanics | `model.py:Scenario.validate`; `schedule.py` | `test_schedule.py:test_all_passes_preflight_and_no_inherited_plan` |

## Development boundary and missing data

This is a **prescribed schedule simulator**, not a schedule optimiser or controller.
Any search for a pass count or intermediate gauges must first supply a named
alloy/temper and prior history, material-law calibration ranges, mill geometry,
force/torque/power/speed and reel tension ratings, operating practice by pass
and phase, friction/lubrication evidence, cooling/interpass timing and a foil
model with independent validation. Foil layer count and per-layer versus pack
gauge must be explicit before that regime is implemented. The AA5052 three-pass
comparison is not a 50 µm validation set.
