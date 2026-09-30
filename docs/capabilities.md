# Physics capability boundary (prototype 0.2)

The current code is a **synthetic, steady, isothermal demonstrator**. This table is the
review boundary for future literature and plant-data work. “Implemented” means the stated
algebra runs and has numerical tests; it does not mean the prediction is calibrated or
validated against an aluminium mill. See `model.md` for every current equation and
`traceability.md` for research-to-test links.

| Topic | Present executable calculation | Missing physics and evidence before a production claim |
|---|---|---|
| Roll–strip contact/friction | A constant input `friction_coefficient` enters a documented heuristic mean-pressure and extra-loss multiplier. A conservative unassisted bite and torque-capacity check reject some cases. | Friction depends on lubricant, surface roughness, pressure, speed, temperature and local slip. There is no resolved traction/neutral-point field, stick–slip transition or oil-film model. Fit an **effective** friction parameter with force, torque and measured forward slip jointly; source lead: [Lenard & Zhang](https://doi.org/10.1016/S0924-0136(97)00183-0). |
| Strip mass and material flow | `Q=b h v`, `m_dot=rho Q`, and local entry/exit mass-flow observations conserve a fixed-density, fixed-width incompressible strip. The scene has a true-gauge strip mesh. | Width spread, changing density, through-thickness velocity variation, elastic recovery, coil storage and time-aligned material parcels are not solved. A separate coil/transport model is needed for transient signals. |
| Separating force, torque and reel tension | A heuristic projected-area load, energy-equivalent work-roll torque, local tension force/stress, static stand reaction and signed reel work are calculated without adding duplicate load-path forces. | A tension-aware pressure integral and signed local traction torque, calibrated material hardening, roll flattening and compliant gap closure remain future mechanics work. See `research.md`. |
| Plastic deformation energy | Uniform plane-strain ideal work `Q K ln(h0/h1)` and a **heuristic** extra dissipation term are calculated for power bookkeeping. | There is no Taylor–Quinney heat fraction, plastic-work partition or spatial plastic-heating source term. Mechanical energy is **not** converted to a strip or roll temperature prediction. |
| Roll/strip heating and cooling | None. A disconnected pyrometer type appears in the sensor registry with unknown values and emissivity. | Coupled strip/roll conduction, contact heat transfer, friction heat, convection/radiation, cooling jets/oil film, coolant state, roll thermal crown and time-dependent temperatures need measured boundary conditions and validation. Aluminium surface emissivity must be qualified; lubricant may be neat oil rather than emulsion. |
| Metallurgy and grain/property effects | One supplied constant mean flow-stress input; density is constant. | Alloy/temper-specific work hardening, grain size/texture, recovery, recrystallization, residual stress and property evolution are not predicted. No microstructure state or strength/hardness output exists. |
| Fracture and strip breaks | Unsupported parameter regimes are rejected, but no failure criterion is computed. | Ductile damage, edge cracking, local defects, fatigue/strip-break mechanisms and fracture calibration require separate experiments and field resolution. A passed bite or force screen does not certify fracture safety. |
| Flatness/profile | A disconnected shapemeter type is documented. | Roll-stack bending, widthwise gauge and tension fields, buckling, crown and flatness remain separate mechanics/measurement problems. A flatness-roll stress profile is not geometric crown. |

The next literature round should select sources and measured test cases for each missing
coupling, resolve their unit and boundary conventions, then add one independently testable
module at a time. There are no thermal, metallurgical, fracture or live plant signals in
this version. The research round and any resulting implementations are subsequent work.
