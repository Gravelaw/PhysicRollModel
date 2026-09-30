# Sensor-to-physics roadmap after prototype 0.2

This is a **research and calibration plan**, not executable thermal, metallurgy,
flatness or fracture output. No single sensor makes a latent state observable on its
own. Each proposed closure needs its own boundary conditions, parameter identification,
uncertainty and held-out aluminium passes/coils. Instrument categories and present null
reading/quality fields are in `sensors.md`; the present calculation boundary is in
`capabilities.md`.

| Future module and candidate closure | Signals needed and what they could identify | Intended product outcome and separate validation |
|---|---|---|
| Mixed lubrication/contact traction `tau(x)` with effective friction, roughness/oil-film and stick/slip limits | Synchronized roll force, shaft torque, roll and strip speeds, forward slip, lubricant type/flow/temperature, surface roughness and local temperatures. Force alone confounds friction and flow stress. | Pressure/traction and bite load/torque; compare independent force, torque and slip over qualified lubricant and alloy conditions. |
| Strip energy equation with plastic volumetric source `q_plastic''' [W/m³]` and frictional slip surface source `q_friction'' = tau · (u_roll − v_strip) [W/m²]` | Entry/exit strip temperature with emissivity-qualified pyrometry, alloy heat capacity/density, local strain rate and traction/slip. Power at the motor includes losses and reel work and is **not** strip heat. | Through-thickness and surface temperatures; check measured temperature rise and total energy balance. At zero relative slip, frictional heating is zero even if traction is nonzero. |
| Coupled roll/strip conduction and cooling | Roll surface/bulk temperatures, calibrated strip pyrometry, coolant/oil flow, supply/return temperatures, nozzle geometry and contact residence. A lubricant may be neat oil, so no universal emulsion-concentration input is assumed. | Strip and roll temperature histories and roll thermal crown. Roll-to-strip contact heat flux is equal and opposite at the interface; convection/cooling and radiation are separate boundaries. Validate both strip and roll temperatures before geometric effects. |
| Elastic roll-stack and widthwise strip deformation | Widthwise entry/exit thickness scans, roll profiles/temperatures, chock force distribution, hydraulic position/pressure and bending actuator state. Avoid counting compliance already absorbed by a fitted stand modulus. | **Crown is a thickness-profile difference**, not a shapemeter stress reading. Validate gauge across width and loaded gap separately. |
| Differential elongation, residual stress and buckling | Widthwise shapemeter stress/flatness channels, gauge/strain profiles, strip tension and independent residual-stress tests. | Latent flatness and unloaded wave/buckle morphology need differential strain/residual stress and post-bite elastic/buckling mechanics. A scalar separating force or thickness crown alone cannot validate them. |
| Alloy/temper-specific hardening and microstructure | Measured entry alloy/temper, prior reduction, temperature, flow curves, hardness/tensile tests, grain/texture data where available. | Cold-work strength/property evolution, with held-out alloys and pass histories. There is no universal aluminium hardening/fracture curve or automatic recrystallization switch for ordinary cold rolling. |
| Damage/fracture/strip-break assessment | Edge/through-thickness defect observations, local stress/strain fields, alloy/temper-specific ductility tests, tension histories and validated damage tests. | Calibrated failure limits and uncertainty. A valid bite calculation or passing force test is not a fracture-safety certificate. |

Before implementing any row, resolve conservation/sign conventions and measured signal
provenance, then use a numerical benchmark and independent physical observations. In
particular, distribute plastic and slip-friction heat into strip/roll only with an
explicit partition/contact law; do not count either source twice. The next primary-source
literature round should refine this map and choose the first independently testable
module. No new coupling is claimed by this roadmap.
