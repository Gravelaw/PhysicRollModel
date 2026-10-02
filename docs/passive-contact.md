# Optional passive contact boundary for the flowing energy ledger

This development increment extends the [prescribed-boundary handoff](energy-handoff.md)
with an **opt-in numerical closure**. The existing `PassHeatBoundary` remains the
default. Set its prescribed `contact_heat_to_strip_w` to zero and pass a
`PassiveContactBoundary` to `handoff_pass`; giving both contact powers rejects.
The synthetic example is `scenarios/passive_contact_demo.json`, executed by
`scripts/run_flowing_energy_demo.py` into `artifacts/passive_contact_demo.json`.
Neither example supplies a calibrated aluminium contact law.

## Declared reduced equations and units

Let `G` be the **total conductance of both roll/strip interfaces**, supplied in
W/K, not inferred from lubricant identity. It is an effective input, not a
measured or predicted heat-transfer coefficient. If an area-specific coefficient
is later used, its contact area and interface count must be declared separately
before forming this total G. The strip is a steady flowing control volume and
the rolls are one aggregate finite thermal body over a stated interval:

```text
T_s,mid = (T_s,in + T_s,out)/2
T_r,mid = (T_r,in + T_r,out)/2
Q_contact = G (T_r,mid - T_s,mid)                         [P1, W]
m_dot [H_s(T_s,out)-H_s(T_s,in)] = S_s + Q_contact        [P2, W]
m_roll [H_r(T_r,out)-H_r(T_r,in)]/delta_t = S_r-Q_contact [P3, W]
S_s = beta P_plastic + f_strip P_solid_slip - Q_cool,s
S_r = (1-f_strip) P_solid_slip - Q_cool,r
```

`H(T)=integral c_p(T)dT` is J/kg; `m_dot` is kg/s; aggregate `m_roll` is kg;
`delta_t` is s. The two midpoint temperatures are an explicit **two-node
approximation**, not a bite or roll surface temperature field. The signed
contact power is positive from roll to strip. P1 is passive: at the chosen
representative temperatures, `Q_contact*(1/T_s,mid-1/T_r,mid) >= 0` W/K.
P2+P3 reproduce E1+E2; the contact powers cancel, while unconverted plastic
work stays the existing explicit allocation. Solid-slip power already includes
both interfaces. The caller must declare `law_scope='conductive_only'`; a
declared fitted-effective scope rejects because it could already contain slip
heating. Software cannot determine whether a mislabelled supplied G embeds
dissipation, so its provenance must be independently checked.

The scalar root is bracketed by both heat-capacity domains and the declared
mechanical strip-temperature envelope. Raising Q heats the strip and cools
the roll, making `Q-G*(T_r,mid-T_s,mid)` monotone. A missing admissible root,
nonfinite input, excessive residual or incompatible property range rejects
rather than extrapolating. This numerical law adds no friction, coolant,
film, material or thermal-force feedback. Constant prescribed cooling export
remains the prior assumption, even if the fluid is warmer; a physical cooling
closure is outside this module.

## Equation, source and test map

| Equation or guard | Basis | Code | Verification |
|---|---|---|---|
| P1, representative temperatures and passive sign | Full research report (2 October 2026), Section 25 proposes equal/opposite conductive exchange and distinguishes it from friction partition; the midpoint reduction is **this repository's declared approximation** | `PassiveContactBoundary`, `_passive_contact_power` | Independent constant-cp solution; zero/equal/reversed temperature; entropy sign; large-G case in `tests/test_passive_contact.py` |
| P2–P3 and exact cancellation | Existing E1–E4 [first-law ledger](energy-handoff.md), derived in this repository | `handoff_pass` | Analytic temperatures, total W and J budget, variable cp, unit scaling, carried roll state, step refinement |
| Domain and declared-law no-double-count guard | Existing mechanical and thermal guards; [specialist audit](energy-specialist-audit.md) | `handoff_pass`, `_passive_contact_power` | Mixed-mode, *declared* fitted-effective-law, invalid G, property and assumed-material envelope rejection |

The [source ledger](research/source-ledger.md) records access depth: the AA8015
thermal/contact publication was inspected at abstract depth and supplies no G;
the AA5052 paper supplies force/slip cases but no thermal validation. The
numerical example's `G=1000 W/K` is an arbitrary labelled synthetic input,
not an aluminium or plant recommendation. The new result fields report G,
representative temperature difference, P1 residual and contact entropy
production; they do not claim thermodynamic admissibility for unmodelled film,
cooling or plastic internal energy.

Calibration would need known alloy/temper and prior history; independent
heat capacities; emissivity-qualified entry/exit strip and roll surface/bulk
temperatures; contact area and residence; effective roll thermal geometry;
coolant/lubricant circuit flows and supply/return temperatures; synchronized
mechanical force, torque, speeds, tensions and gauges; and held-out coils.
Temporal substep convergence is numerical evidence only. Spatial conduction,
advection, film dissipation and thermal feedback each require a separate model
and observations.
