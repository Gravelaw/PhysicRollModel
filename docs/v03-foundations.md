# v0.3 research-informed computational foundations (candidate)

The initial candidate is preserved at `ec3e79f`. The subsequent local specialist
review and corrections are documented in [mechanics-audit.md](mechanics-audit.md),
and actual literature runs in [aa5052-study.md](aa5052-study.md). Those documents
supersede this initial description where numerical safeguards were strengthened.

This branch is an **uncalibrated, synthetic, offline candidate**. It leaves the
accepted v0.2.1 `.blend`, USDA, sensor manifest and baseline `solve()` result
unchanged. Its new calculations are separate, inspectable functions; they do not
form a validated coupled digital twin or a production recipe. Run
`python scripts/build_v03.py` to regenerate `artifacts/v03_foundations.result.json`.
The source input is `scenarios/v03_foundations.json`; every number there is a
synthetic exercise, including the aluminium-labelled hardening curve, heat
fraction, capacities, cooling coefficients, oil identity and width profile.
`python scripts/run_v03_study.py` records three friction cases, three heat
partition cases and a two-pass history in `artifacts/v03_sensitivity.json`.
Those are one-factor demonstrations, not a coupled sensitivity analysis or
uncertainty bounds. The second pass starts at the first pass's exit gauge and
speed, keeping the assumed fixed-width mass flow equal across both passes.

## Equations and conventions

- **History-aware hardening:** `materials.py` carries alloy, temper, accumulated
  equivalent plastic strain, named prior history and temperature. For the
  *assumed plane-strain thickness kinematics* of each pass,
  `Δεeq = (2/√3) ln(h_in/h_out)`. The illustrative isotropic law is
  `σflow(εeq)=σ0+C εeq^n`, and its exact interval average supplies the existing
  baseline model's mean uniaxial stress. No anneal, recovery, texture, grain,
  precipitation or fracture state is inferred. The temperature is carried as a
  declared condition, not silently evolved by this function. It is not a
  plane-stress yield law inserted into the roll bite.
- **Optional slab pressure:** `slab.py` assumes rigid circular rolls, constant
  plane-strain yield `K=2 σflow/√3`, full thickness `h`, Coulomb `µ` and
  tensile boundary stresses `t_in,t_out`. Entry/exit pressure boundaries are
  `q=K−t`; forward and backward branches integrate
  `h dq/dx = K dh/dx ± 2µq` with `x=0` at entry, then join at one interior
  neutral point. The separating load is `b∫q dx`; signed per-work-roll torque
  is `Rb∫τ dx`, with `τ=+µq` before neutral and `−µq` after. The neutral
  surface speed follows `h v = constant`. This is an optional **constant-yield
  comparison**, not the v0.2 energy-equivalent torque and not a hardening/stand
  closure. Zero draft, zero friction, negative pressure, missing/multiple
  neutral points and unsupported bites reject. Its numerical error is tested
  by refinement and a constant-gap exponential ODE reference, but there is no
  aluminium force/torque validation. It omits sticking, noncircular flattening,
  roll spring, elastic recovery and film pressure/shear. Foil remains excluded.
- **Thermal budget:** `thermal.py` advances distinct strip and roll lumped
  capacities `m cp` over an explicit step. Given **supplied** plastic work rate
  `Pp`, fraction `β` (no universal value), deforming volume `V`, traction
  `τ` and relative surface slip `Δv`, it reports `q'''plastic=βPp/V` [W/m³]
  and `q''solid-slip=τΔv` [W/m²]. The latter is zero at zero slip even with
  nonzero traction; normal pressure and motor power do not directly become
  heat. Slip heat is partitioned by an explicit input. Contact transfer
  `H A (Troll−Tstrip)` enters the strip and exits the roll equally. Separate
  measured-or-synthetic cooling boundaries are `G(T−Tcoolant)` per body.
  A fitted effective contact law cannot be combined with explicit slip heat.
  The step returns the summed energy residual and rejects an unstable
  explicit step. It is a **collapsed interface**: lubricant pressure-flow
  dissipation and resolved strip/roll temperature fields are absent.
- **Fluid registry:** `lubrication.py` records fluid identity/type, flow,
  supply temperature, viscosity, both roughness measurements, source and
  quality, each nullable if unknown. It only passes a declared *effective*
  friction coefficient; it does not infer `µ` or HTC from coolant. A
  “calibrated” effective-friction claim requires a recorded joint
  force/torque/forward-slip fit. No data or such fit ship here.
- **Supplied-field product diagnostics:** `profile.py` reports center crown
  (center gauge minus average edge gauge), wedge, widthwise thickness range,
  across-width membrane-mismatch RMS and a **separate** through-thickness
  curvature range. Result records temperature and applied tension. None of
  these fields is predicted by roll-stack mechanics. Latent flatness and
  unloaded wave amplitude are null; linear buckling alone would not give
  finite wave amplitude. No residual stress or edge fracture is calculated.

Material and thermal calculations are deliberately independent. The thermal
demonstration's `plastic_power_w` is supplied rather than secretly set equal
to motor power or slab torque. A coupled pass model will need consistent
mechanical work and heat partition, time/material-coordinate alignment, and
strip/roll property measurements. The slab's constant-yield assumption is not
quietly replaced by the hardening law. `solve()` remains the v0.2 heuristic.

## Research and visual provenance

| Source (click through) | Viewed evidence, role and implementation boundary |
|---|---|
| Erfanian et al., [*Through-Thickness Modelling of Metal Rolling using Multiple-Scale Asymptotics*](https://arxiv.org/html/2408.01347v1), 2024 | Primary full HTML inspected: equations 21–28 lead to two pressure branches and a neutral point under rigid-roll, perfectly plastic asymptotics. `slab.py` uses an explicitly converted full-thickness leading-order slab equation, not their first-order through-thickness solution. Tests verify mathematics, not the paper's FEM agreement or aluminium performance. |
| Mišović et al., [*Deformations and velocities during cold rolling of aluminium alloys*](https://mit.imt.si/izvodi/mit161/misovic.pdf), 2016 | Parent-reviewed AW2024/AW5083 hardening/kinematics motivates tracking strain history. Our power law coefficients are **not taken from the paper**; no generic alloy can stand in for those grades. |
| Lenard and Zhang, [*A study of friction during lubricated cold rolling of an aluminum alloy*](https://doi.org/10.1016/S0924-0136(97)00183-0), 1997 | Aluminium lubrication/friction source; publisher metadata verified, full text unavailable here. Motivates the declared fluid variables and joint friction identification, not a borrowed `µ(fluid)` law. |
| Tadić et al., [*An analysis of longitudinal residual stresses in EN AW-5083 alloy strips as a function of cold-rolling process parameters*](https://doi.org/10.1515/jmbm-2022-0297), 2023 | DOI supplied in specialist research; full article blocked. It is a future stress-depth validation lead, **not** evidence for a friction control rule or the present profile diagnostics. |
| [Aluminium profile/center-buckle study](https://doi.org/10.1155/2017/6489769), 2017 | DOI resolves to a Hindawi article but article text was inaccessible. Parent research flags the distinction between crown and center buckle; no formula or quantitative claim imported. |
| Mathieu et al., [*Flatness defects after bridle rolls: a numerical analysis of leveling*](https://doi.org/10.1007/s12289-011-1083-2), online 2011/volume 2013 | Publisher abstract inspected: aluminium-industry **bridle/leveler** 3D FE studies width/thickness plastic strains, residual stress, springback and potential buckling. It does not validate the rolling-bite slab or predict waves from our scalar crown. |
| Abdelkhalek et al., [*Coupled approach for flatness prediction in cold rolling of thin strip*](https://doi.org/10.1016/j.ijmecsci.2011.04.001), 2011 | Full text unavailable here; primary research lead for a later coupled roll-stack/strip/buckling solver. `profile.py` only diagnoses supplied fields. |
| Achenbach, [UNIHEAT Curved Hot Edge System](https://www.achenbach.de/en/machines-equipment/technology-components/uniheat-curved-hot-edge-system/) | OEM product page inspected. Its described induction acts on the **work roll near the strip edge**, not directly on strip. No OEM CAD, logo, hardware dimensions or hot-edge actuation model is used in this candidate scene. |
| [Blender USD manual](https://docs.blender.org/manual/en/latest/files/import_export/usd.html) | Interchange reference; local Blender build lacks native USD. Existing static USDA fallback and geometry were independently checked in v0.2.1; v0.3 does not alter them. |

The parent-supplied DOI/paper leads above establish motivation and **limits**.
Citation by itself does not validate any equation, boundary, coefficient or
scene dimension. No video was viewed or treated as direct visual evidence.
The existing original generic 4-high scene and sensor markers are not a copy
of OEM CAD. Future optional spray/hood/hot-edge visuals need separate source
and geometry review, especially if six-high or HGC variants are introduced.

## Traceability and verification gates

| Finding | Code/input/output | Direct verification | Status |
|---|---|---|---|
| Alloy, temper and processing memory affect flow stress | `materials.py`, `v03_foundations.json`, `v03_foundations.result.json` | `MaterialTests`: exact interval integral, two-pass history, constant law and mismatch rejection | Implemented synthetically; no alloy fit/strength validation |
| Entry/exit tension and neutral traction alter pressure, force and torque | `slab.py`; optional result block | `SlabTests` plus `MechanicsAuditTests`: independent exponential-midpoint pressure, work balance, refinement and rejection | Specialist equation review completed within the stated approximation; measured aluminium predictive validation still absent |
| Plastic volume heating, solid slip heating and equal/opposite contact | `thermal.py`; separate demo step | `ThermalTests`: zero slip, opposite contact, energy residual, passive-cooling analytic refinement and rejected unstable/negative-work cases | Conservative lumped calculation; no resolved temperatures/film |
| Lubricant identity and observations do not identify friction by themselves | `lubrication.py`; nullable fluid inputs | `ClosureTests`: missing inputs and claim guard | Registry/declared effective coefficient only |
| Crown is not latent flatness; membrane mismatch differs from curvature | `profile.py`; supplied profile | `ClosureTests`: crown/wedge, separated descriptors, null wave amplitude | Supplied-field diagnostics only; no roll-stack/buckling prediction |
| OEM hot edge heats work roll; geometry is generic | `docs/v03-foundations.md`, unchanged `blender/` | Existing v0.2.1 geometry checks; no new v0.3 geometry claim | Documented future visual option |

Independent scientific validation remains four distinct gates: (1) synchronized
force/torque/slip/gauge with qualified aluminium passes, (2) widthwise crown and
flatness including roll-stack and buckling, (3) through-thickness residual stress
and mesh convergence, (4) reel/AGC dynamics with sensor delays. Passing any
software test or one physical gate does not pass the others.
