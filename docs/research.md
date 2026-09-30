# Engineering architecture and research path

**Prototype 0.1: generic synthetic demonstrator, not a plant twin or production model.**
Source notes checked on 2026-09-30. No published equations have been copied into the
heuristic load closure. Equations and their status are enumerated in `model.md`.

## Separation of responsibilities

```text
SI scenario JSON + schema
         │
         ▼
Scenario validation → pure-Python solve → result JSON + warnings/provenance
         │                    │                   │
         │                    └→ finite-candidate offline constraint study
         ▼                                        │
Blender geometry generator ← same scenario/result ─┘
         │
         ├→ editable .blend + CPU render + analytical bite inset
         └→ static USD meshes/materials/IDs → future local RTX/Kit CAE viewer
```

X is rolling direction (entry negative), Y width and roll axis, Z up. All scene distances
and USD `metersPerUnit` are metres. Equipment names/`equipment_id` attributes are stable
across supported parameter changes. The USD scene root is `/Mill`; custom-property IDs are
preserved by the fallback exporter. Blender is a presentation and geometry layer, never
the process solver. USD does not make geometry a mechanical simulation automatically.

The installed Blender 4.3.2 lacks native USD export and OpenImageDenoise. The repository
therefore supplies a static evaluated-mesh USDA writer with PreviewSurface materials and
independent OpenUSD checks. It exports no textures, rigging, physics schema or time series.
Native Blender USD export is attempted first on builds that support it; capabilities and
failures are recorded in `scene_status.json`. Native output on another Blender build may
use a different prim hierarchy; the supplied USDA verifier targets the included fallback.
The official [Blender USD manual](https://docs.blender.org/manual/en/latest/files/import_export/usd.html)
is the interchange reference; the page fetch was blocked here, so runtime capability
inspection and reopening the actual export are the evidence for this build.

## Primary sources and their precise role

| Source | Use in this project / boundary |
|---|---|
| Lenard & Zhang, [A study of friction during lubricated cold rolling of an aluminum alloy](https://doi.org/10.1016/S0924-0136(97)00183-0), 1997 | Aluminium-specific lubrication/friction research lead. Publisher metadata/title verified; full text access was blocked. No coefficient or formula imported. Treat friction as an effective parameter until identified jointly from load, torque and slip. |
| [Lubricants 3(2), 113](https://www.mdpi.com/2075-4442/3/2/113), 2015 | Parent research identifies an equation-bearing slab equilibrium/stick-slip source for the next pressure solver. Local fetch rate-limited; equations are not implemented from an unread extract. |
| Li, Matsumoto & Utsunomiya, [Experimental Study of Roll Flattening in Cold Rolling Process](https://www.jstage.jst.go.jp/article/isijinternational/58/4/58_ISIJINT-2017-623/_html/-char/en), 2018 | Full article inspected: stainless-steel roll-flattening experiment, not aluminium validation. Explains limits of circular Hitchcock geometry and motivates excluding foil/noncircular contact. |
| Mišović et al., [Deformations and velocities during cold rolling of aluminium alloys](https://mit.imt.si/izvodi/mit161/misovic.pdf), 2016 | Parent research identifies AW2024/AW5083 hardening/kinematics. Candidate alloy-specific validation source; its coefficients are not adopted for an unspecified alloy. |
| Abdelkhalek et al., [Coupled approach for flatness prediction in cold rolling of thin strip](https://doi.org/10.1016/j.ijmecsci.2011.04.001), 2011 | Coupled roll-stack/strip/buckling research path. Title/metadata verified; publisher/HAL full text blocked here. A separating-force calculation does not establish flatness. |
| Erfanian et al., [Through-Thickness Modelling of Metal Rolling using Multiple-Scale Asymptotics](https://arxiv.org/html/2408.01347v1), 2024 preprint v1; [2025 journal lineage](https://doi.org/10.1016/j.euromechsol.2025.105712) | Full HTML inspected: rigid perfectly plastic strip and rigid-roll starting assumptions. A research extension beyond slab theory, not validation of this heuristic model or of an elastic-gap/hardening implementation. |
| [Careful finite element simulations of cold rolling with accurate through-thickness resolution and prediction of residual stress](https://arxiv.org/abs/2408.03242), 2024 | Numerical benchmark lead. Parent review identifies DC04 steel, isothermal 2D rigid rolls; not an aluminium benchmark. Reported through-thickness mesh counts are case-specific, and load convergence is not residual-stress convergence. |
| [Metals 15(1), 11](https://www.mdpi.com/2075-4701/15/1/11), 2025 | Parent review identifies direct Al-1050 flow-pattern experiments; raw data are on request, not a ready public calibration dataset. Local fetch blocked. |
| [ELTE engineering study](https://ojs.elte.hu/eis/article/view/4443) | Additional aluminium experimental research lead from parent; not used to assign coefficients here. |
| [Aluminium twin-stand AGC study](https://article.nadiapub.com/IJCA/vol10_no6/6.pdf) | Measurement transport delay and mill-stretch context for a later dynamic model; not justification to interpret the present independent steady states as controller responses. |

The [PyRolL core](https://github.com/pyroll-project/pyroll-core) is a groove-rolling framework,
not a ready flat-strip cold-mill solver. We do not depend on it or claim otherwise.
[NVIDIA Kit CAE](https://github.com/NVIDIA-Omniverse/kit-cae) is a future local visualisation/
CAE integration option after solver calibration; nothing from Omniverse is installed here.
The [public rolling roughness dataset](https://github.com/Don-Chris/data_set_roughness_control_in_cold_rolling)
is identified by parent research as steel DC04/DC05, not aluminium calibration truth.
Research leads requiring full access/data acquisition remain work to do, not completed validation.

## Staged mechanics upgrade

1. Replace the H1 pressure proxy with a tension-aware slab integration with explicit entry/
   exit traction boundary conditions, neutral point and stick/slip handling. Compute total
   load as `b * integral(p dx)` and each roll torque from **signed traction**. Close mechanical
   work/dissipation consistently; do not retain the proxy torque alongside a new pressure law.
   Validate both integration directions, neutral-point matching and refinement independently.
2. Add alloy/temper-specific measured hardening. Keep full/half-thickness and uniaxial/
   plane-strain conventions explicit. Measure actual roll/strip speed to validate forward slip;
   the present assumed slip is not useful for identifying friction.
3. Where appropriate, iteratively couple roll flattening and strip deformation. The inspected
   steel paper states Hitchcock's circular correction as
   `R_eff = R * [1 + 16(1−nu_roll²) F / (pi E_roll b (h0−h1))]`.
   This is a **future equation, not implemented**. It becomes singular as draft tends to zero
   and is not sufficient for foil/noncircular flattening. Require convergence flags and reject
   failed iterations rather than clipping a radius or force.
4. Add a measured stand-compliance closure. Separate unloaded screw gap, loaded roll gap and
   recovered strip gauge. Define what the stand modulus includes so roll deformation is not
   counted both in its calibration and in an explicit roll correction.
5. Only after force/torque/gauge validation, add the needed roll-stack/contact/buckling model
   for profile/flatness and refined elastic-plastic FEM for residual stress. Foil needs a
   separate noncircular/sticking-zone formulation; removing the 300 µm guard is not an upgrade.

## Calibration, FEM and hybrid model interfaces

The public `Scenario -> result dict` interface and `rank_candidates(..., evaluator=...)`
permit later solver adapters without importing Blender. Keep parameter sets versioned with
material/temper, provenance, units, valid ranges, uncertainty and calibration revision.
The present solver accepts only `synthetic: true`; real-data support requires an explicit
reviewed revision, not changing this flag to imply validation.

A future observation table should have `coil_id`, `pass_id`, alloy/temper, time window,
entry/exit gauge and width, both strip speeds, both roll speeds, measured tension forces,
force, per-roll torque, motor efficiencies/losses, lubricant/temperature/roughness, uncertainty
and quality flags. Convert measured tension forces to stress at the **correct** gauge.
Separate spindle torque, electrical power and reel work. Fit effective friction and flow
stress against force **and** torque **and** measured forward slip; force alone confounds them.
Do not use the assumed-slip output of this core as a third independent observation.

For FEM adapters, preserve model/material/contact versions, mesh/time-step convergence,
boundary conditions, and measurement operators from fields to each signal. Use a benchmark
with known geometry before an industrial case. Cross-code comparisons are not substitutes
for physical measurements. Keep independent experimental holdouts.

For hybrid physics+ML, begin with a bounded residual or identifiable parameter correction
around a validated physics core. Do not train a black-box production controller from these
synthetic demonstration outputs. Hold out entire coils and preferably campaigns/grades;
random adjacent-row splits leak process context. Preserve conservation laws, physical
constraints, an explicit out-of-domain flag, uncertainty and fallback/rejection behaviour.
Measure whether the correction improves independent force/torque/slip errors before adding
complexity. **No fitted ML model, training data or uncertainty calibration is shipped.**

`physicroll.studies.rank_candidates` implements a small finite-candidate constraint screen:
fixed target exit gauge, maximum force/electrical power and minimum mass flow, ranked by
throughput. It records all candidates/rejections and solver provenance. It does not generate
production schedules or establish continuous/global optimality. Do not optimise an unknown
friction coefficient as if it were a directly commanded plant variable. Future optimisation
must account for uncertainty/domain limits and use validated models inside the constraints.

## Separate validation gates

| Output class | Required evidence beyond this prototype |
|---|---|
| Force, torque, power, slip, thickness | Synchronized aluminium measurements, identified material/friction, speed and energy accounting, held-out passes/coils, uncertainty and domain checks |
| Profile/flatness | Widthwise gauge/tension/shape data, roll-stack/contact/buckling mechanics; scalar force agreement is insufficient |
| Residual stress | Elastic-plastic through-thickness resolution, convergence of stress itself and independent residual-stress evidence; converged roll force is insufficient |
| Reel/tension/AGC dynamics | Inertia, elasticity, speed controllers, sensors and transport-delay model; separate transient experiments with known sampling/latency |

Unit tests here are numerical verification only. None of these scientific validation gates
has been passed. No calibration dataset or real mill capacity has been supplied.

## Sensor/force update (prototype 0.2)

The disconnected taxonomy, vendor/paper sources, marker layout, timestamp/quality fields,
and observation equations are integrated in [sensors.md](sensors.md),
`physicroll/sensors.py`, `physicroll/observations.py`, and
`physicroll/equipment.py`. The update is an auditable demonstration: all readings,
uncertainties and time alignments remain unknown. A pressure-transducer thrust, stand
load-cell reaction, tension load-cell reaction, and roll-bite force may constrain the
same load path; they are not terms to sum indiscriminately. Real installation diagrams
and calibration/quality records are still required before comparing these channels.

## Reviewed contact/material increment

The optional implementation after published `09d0d5b2` is traced in
[contact-increment.md](contact-increment.md) and the machine-readable
[source records](research/contact-sources.json). The asymptotic paper now has
verified 2025 journal lineage, DOI
[10.1016/j.euromechsol.2025.105712](https://doi.org/10.1016/j.euromechsol.2025.105712);
our equation-number citations explicitly remain the 2024 preprint v1. The
[report-sync packet](report-sync-contact-increment.md) links updated first-principles
equations, optional circular flattening, numerical tests and actual before/after
force/slip comparisons. Mixed residual changes are retained rather than used to
claim aluminium validation or silently fit unidentified per-pass parameters.
