# Optional flowing-strip energy handoff

This increment starts from the reviewed and published `1f1145dfda0c6fd70b0be0abc379dcadb26e10d5`
contact/material branch. It adds an optional, prescribed-boundary energy ledger in
`physicroll/energy_handoff.py`. The legacy `solve()`, checked slab mechanics,
`thermal.py` demonstration and all earlier AA5052 comparison files remain as they
were. The ledger is a **synthetic numerical conservation exercise**, not an
aluminium temperature prediction. It does not feed temperature back into force.

## First-law and material-coordinate contract

Use one steady flowing strip control volume and one aggregate roll thermal body
for a declared duration. The strip and roll heat-capacity curves may differ.
`H(T)=∫c_p(T)dT` has units J/kg and is computed from explicitly provided,
positive, piecewise-linear `c_p(T)` [J/(kg K)]. Positive signed contact heat
`Q_contact` [W] flows from roll to strip. Cooling exports are nonnegative W.

```
m_dot [H_strip(T_out)-H_strip(T_in)]
    = beta*P_plastic + f_strip*P_solid_slip + Q_contact - Q_cool_strip       [E1]

m_roll [H_roll(T_roll_out)-H_roll(T_roll_in)] / delta_t
    = (1-f_strip)*P_solid_slip - Q_contact - Q_cool_roll                     [E2]

P_unconverted_plastic = (1-beta)*P_plastic                               [E3]

P_plastic + P_solid_slip
    = strip_enthalpy_gain_rate + roll_storage_rate
      + P_unconverted_plastic + Q_cool_strip + Q_cool_roll                 [E4]
```

`m_dot` is the checked slab's strip mass flow [kg/s], not a prescribed strip
mass. The slab's fixed-width, fixed-density, incompressible approximation is
retained; thermal expansion and density changes are not solved. `P_plastic` and `P_solid_slip` are already **total W**, with the latter
counting both roll-strip interfaces. Multiplying them by width or by two again
would double-count heat. `beta` and `f_strip` are supplied fractions in `[0,1]`,
not universal aluminium constants. `P_unconverted_plastic` remains visible as a
work allocation; no grain, defect or stored-energy state is inferred from it.
At zero solid sliding, the solid-slip source is zero despite possible nonzero
traction; a lubricant pressure-flow dissipation law is not present. An attached
`FluidObservation` records identity, type and missing measurements but has no
causal effect on friction, heat partition or cooling. Cooling powers and contact
transfer are supplied in W and carry source/quality labels; an effective HTC and
an explicit friction source are not both silently added.

The mechanical solver also reports `P_roll + P_tension - P_plastic -
P_solid_slip` [W]. The handoff checks that identity, reports its residual
separately, and reports the combined mechanical-to-outlet residual. The strip
temperature comes from an exact segmentwise integral/inverse of the supplied
`c_p(T)` curve. The roll update uses effective mass and a declared duration.
That is a quasi-steady strip/finite-capacity roll snapshot, with no roll
conduction field or varying contact boundary during the step. Because the
heat rates are prescribed rather than temperature-dependent closures, there
is no additional contact-eigenvalue step restriction; leaving the supplied
property temperature range rejects the step.

`m_roll` represents the effective aggregate mass receiving heat from **both**
work-roll interfaces; it is not a per-roll mass to be doubled elsewhere. For
the solid roll, the supplied `c_p` curve is used as an effective sensible-energy
storage coefficient, neglecting thermal expansion and thermoelastic work.
This does not model a general solid's distinction between enthalpy and internal
energy. Strip kinetic-energy changes and roll thermal gradients are also absent.
Over a constant-rate interval `delta_t`, the processed strip mass is
`m_dot*delta_t`, the roll mass remains `m_roll`, and every power term becomes
energy exactly once by multiplying by `delta_t`. Changing duration alone changes
roll storage and does not change the steady strip temperature rise.

`MaterialState` carries alloy, declared temper, equivalent strain, history and
strip temperature from pass to pass. Mechanical state metadata must match the
incoming alloy/temper/strain/history and advance history exactly once. The
reported roll temperature may feed the next prescribed boundary. If the
mechanical calculation used a different reference temperature, this is flagged;
its material law is deliberately temperature independent. A future
rate/temperature dependent force calculation requires independently qualified
alloy/temper flow curves and a coupled iteration. No anneal, recrystallisation,
property certification or residual-stress state is inferred.
Mechanics must explicitly declare `temperature_feedback=False`. Both incoming
and outgoing strip temperatures must remain inside its supplied assumed material
temperature envelope as well as the heat-capacity domain. This conservative gate
does not make that envelope a calibrated range or introduce thermal feedback.

## Inputs, validity and numerical tests

| Quantity | Internal units, provenance and gate |
|---|---|
| `m_dot`, `P_plastic`, `P_solid_slip`, mechanical work residual | kg/s, W, W, W from one checked `slab.py` result; nonconverged, nonfinite, negative dissipation and inconsistent work identity reject. Recompute relative work error using `max(abs(P_roll),abs(P_tension),P_plastic,P_slip,1e-30)`; negative, inconsistent or above-1e-4 residual metadata reject before any thermal scale is used |
| Strip and roll `c_p(T)` | J/(kg K) on monotonically increasing K knots, named material/source and synthetic/measured quality; analyst sanity ranges 100–3000 K and 1–100000 J/(kg K) catch gross unit errors, **not** calibrated domains; output outside supplied knots rejects |
| Strip material state | Named alloy/temper, prior equivalent strain/history and K; alloy must match strip property ID, material coordinate must match mechanical metadata; strip input/output must stay within the explicit assumed mechanical temperature interval |
| Roll thermal body | Positive effective mass kg and absolute temperature K, supplied duration s; effective mass is not identified from the benchmark |
| Plastic and solid-slip partitions | Dimensionless `[0,1]`; remaining plastic work and remaining slip heat are calculated explicitly, so both allocations sum to the mechanical source |
| Contact and cooling | Signed `Q_contact` to strip in W, roll gets `-Q_contact`; nonnegative strip/roll cooling exports W with explicit source/quality |
| Fluid observation | Optional named neat oil/emulsion/other record; nullable flow, temperature, viscosity and roughness; no assumed `mu(fluid)` or HTC relation |

Unit and limiting-case tests use a separate constant-`c_p` analytic temperature
solution, a varying-`c_p` integral/inverse reference, zero solid slip and heat
partition endpoints, contact sign reversal, whole-system conservation, width/
throughput scaling, invalid heat fractions and kg/s or J/(kg K) inputs, and
out-of-range temperatures. A two-pass run checks carried strip history,
temperature, roll temperature and mass flow. No test represents an independent
thermal experiment.

The [specialist audit](energy-specialist-audit.md) adds exact knot and decreasing-
heat-capacity cases, 100 seeded property curves, strict out-of-domain endpoints,
roll half-step composition, power-to-energy accounting, 10^3/10^6 dimensional
scaling and malformed mechanics/state rejection. Zero-source fixtures verify
the ledger only: the current slab solver still rejects zero draft/friction.
Signed prescribed contact heat is an external observation or assumption; this
ledger closes its first-law budget without establishing a passive heat-transfer
law, second-law admissibility or a calibrated contact coefficient.

Run from the repository root:

```
python -m unittest discover -s tests -v
python scripts/smoke.py
python scripts/run_flowing_energy_demo.py --config scenarios/flowing_energy_demo.json --out artifacts/flowing_energy_demo.json
```

The checked demonstrator uses a **generic synthetic aluminium-like alloy** and
synthetic heat-capacity knots, fractions, effective roll mass and cooling powers.
Its `artifacts/flowing_energy_demo.json` records every numerical input/output.
Earlier AA5052 data contain no measured temperature, coolant/roll thermal
boundaries, alloy temper or qualified heat fraction. They cannot validate this
ledger. The earlier contact model also shows substantial forward-slip residuals;
thermal force/friction feedback must not be tuned to hide them.

## Source lineage and report boundary

| Source | What it supports | What it does not establish here |
|---|---|---|
| Olaogun, Edberg, Lindgren, Oluwole & Akinlabi, *Heat transfer in cold rolling process of AA8015 alloy: a case study of 2-D FE simulation of coupled thermo-mechanical modeling*, published online 2018, volume 2019, [DOI 10.1007/s00170-018-2811-2](https://doi.org/10.1007/s00170-018-2811-2) | Primary publisher abstract establishes thermal/contact investigation for a specific aluminium alloy and identifies an industrial force comparison. The full article is subscription preview here. | No transferable `c_p`, heat partition, contact/film law, roll mass or validated AA5052 temperatures were imported. E1–E4 are our stated first-law ledger, not copied equations from its abstract. |
| Shao, Sun, He & Li, 2015, [DOI 10.18280/ijht.330113](https://doi.org/10.18280/ijht.330113) | Original AA5052 three-pass force/slip comparison, clearly separate in the repository. | No measured thermal results, inlet history/temper or speed convention sufficient for this handoff. |
| Lenard & Zhang, 1997, [DOI 10.1016/S0924-0136(97)00183-0](https://doi.org/10.1016/S0924-0136(97)00183-0) | Primary aluminium lubricated-cold-rolling research lead for later friction/film identification. | No friction or fluid-to-cooling coefficient is used in this increment. |
| [Existing reviewed mechanical equations](contact-increment.md) | Checked projected plastic work, solid-slip dissipation, mass flow and material state with numerical convergence. | Mechanical numerical work balance does not establish physical accuracy for heat or slip. |

Needed for physical calibration: specified alloy/temper and prior history;
independent heat-capacity/flow-property measurements over a known temperature
range; calibrated entry/exit strip and roll temperature observations with
aluminium emissivity qualified; time/material-coordinate aligned speed, gauge,
force, torque and slip; coolant/lubricant identity, supply/return state and
location; effective roll thermal geometry and separate held-out coils. Film
traction, transport delays, thermal crown, through-thickness temperatures,
metallurgy and fracture remain independent future models.
