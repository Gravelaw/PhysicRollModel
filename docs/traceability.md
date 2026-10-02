# Research to implementation traceability

The later [specialist mechanics audit](mechanics-audit.md) maps actual defects,
corrections, equation derivations, unit conventions and adversarial tests.
[AA5052 study](aa5052-study.md) maps original tables and uncertain interpretations
to executable comparison/search results; no calibration fit is claimed.

The optional research-informed v0.3 modules, their primary-source and OEM links,
equations, test names and still-unmet physical validation gates are mapped in
[v0.3 foundations](v03-foundations.md#traceability-and-verification-gates).
The accepted v0.2.1 evidence below remains unchanged.

This table separates **implemented calculations** from scientific work still needed.
Tests establish algebra, input rejection and artifact structure; they do not establish
accuracy for an aluminium plant. Primary source details are in `research.md` and
`sensors.md`.

| Research finding / requirement | Code and data | Test / evidence | Status |
|---|---|---|---|
| Rigid circular bite and no silent foil extrapolation | `physicroll/model.py`, `schema/scenario.schema.json` | `test_exact_bite_boundary`, `test_rejections` | Implemented screen; scientific circular-contact domain unvalidated |
| Full entry/exit thickness convention, incompressible mass flow | `physicroll/model.py`, `physicroll/observations.py` | `test_mass_energy_units_and_traction`, `test_force_stress_and_mass_flow` | Implemented steady balance |
| Tensile stress differs from strip force; use local cross section | `physicroll/equipment.py`, `physicroll/observations.py` | `test_force_stress_and_mass_flow`, `test_reel_force_torque_power_and_inertia` | Implemented SI conversion |
| Bite force, stand reaction and hydraulic thrust are alternative load-path observations | `physicroll/equipment.py`, `physicroll/observations.py`, `docs/sensors.md` | `test_load_path_and_gap`, `test_double_acting_thrust` | Implemented bookkeeping; calibrated force-path closure future |
| Loaded versus unloaded gap; avoid double-counting compliance/flattening | `physicroll/equipment.py`, `scenarios/baseline.equipment.json` | `test_load_path_and_gap`, `test_limits_and_provenance` | Synthetic inverse F/K calculation; full elastic closure and strip recovery future |
| Reel tension, torque, inertia and power have explicit signs | `physicroll/equipment.py`, `physicroll/observations.py` | `test_reel_force_torque_power_and_inertia`, `test_slip_and_reel_torque` | Static shaft torque/energy and tested user-supplied acceleration formula; changing-radius dynamics future |
| Deflector load cell needs wrap angle/tare/qualified geometry | `physicroll/observations.py`, `physicroll/sensors.py` | `test_qualified_wrap_reaction` | Ideal equal-tension conversion implemented; unequal tension/inertia/friction future |
| Actual sensor type versus synthetic model estimate; source, position, units, quality and time | `physicroll/sensors.py`, `artifacts/sensor_manifest.json`, `blender/generate.py` | `test_disconnected_sensor_map`, `scripts/check_blend.py`, `scripts/check_usd.py` | Disconnected registry and scene/USD markers implemented; calibration/observations unavailable |
| Forward slip requires strip and roll speed, guard near zero | `physicroll/observations.py`; `model.py` keeps assumed-speed diagnostic | `test_slip_and_reel_torque`, `test_invalid_types_and_schema` | Observation helper implemented; assumed model slip is not a calibration signal |
| Flatness-roll stress profile differs from crown/buckling | `physicroll/sensors.py`, `docs/research.md`, `docs/sensors.md` | `test_disconnected_sensor_map` confirms no prediction | Instrument category documented; mechanics future |
| Aluminium IR emissivity and lubricant-specific closure | `physicroll/sensors.py`, `docs/sensors.md` | Registry confirms null observed/model temperature | Documented interface; no thermal/coolant prediction |
| Aluminium force/torque/friction calibration, FEM and hybrid residual models | `docs/research.md`, `physicroll/studies.py` | Candidate constraint tests; no scientific accuracy test | Calibration/solver/ML future pending real aluminium data |

## Optional contact/material increment after published 09d0d5b2

The current [equation/provenance table](contact-increment.md#source-to-equation-to-code-to-test-map)
and [findings log](mechanics-change-log.md) map spatial hardening, circular roll
flattening, physical shaft kinematics, numerical gates and hypotheses to code/tests.
[Report-sync packet](report-sync-contact-increment.md) carries the actual per-pass
residuals and missing experimental-validation evidence. The historical v0.2.1
rows above describe that accepted version, not a claim that newer optional
modules are absent.

## Optional flowing-strip energy handoff

The [E1–E4 equation/source table](energy-handoff.md) and
[report-sync evidence](report-sync-energy-handoff.md) map checked mechanical
work and mass flow to a prescribed-boundary flowing-strip/finite-roll energy
ledger. `tests/test_energy_handoff.py` covers analytic, conservation, units and
material-coordinate cases. `artifacts/flowing_energy_demo.json` retains the
actual synthetic two-pass outputs. No film, coolant or aluminium temperature
calibration is inferred from this data path.

The [specialist energy audit](energy-specialist-audit.md) maps four reproduced
boundary/metadata defects to corrections and adversarial tests. Its 67-test
evidence and unchanged synthetic output are same-environment numerical checks;
independent consumer acceptance and measured thermal validation remain distinct.

The [optional passive-contact equation/source/code/test map](passive-contact.md#equation-source-and-test-map)
adds a supplied-conductance numerical closure to the same ledger. Its synthetic
demonstration and passivity tests do not identify an aluminium HTC or validate
strip/roll temperatures.

## Prescribed multi-pass foundation

The [2 October multi-pass source/equation/code/test map](research/multipass-foundation-2026-10-02.md#traceability-and-acceptance-checks)
links kinematic gauge and strain identities, explicit material handoff, per-pass
signal roles and existing foil rejection to `physicroll/schedule.py`,
`physicroll/operating.py` and `tests/test_schedule.py`. This is a development
branch foundation and not a validated 50 µm production schedule.
