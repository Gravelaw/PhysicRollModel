# Multi-pass aluminium rolling: theory and scheduler boundary

Research recorded 2 October 2026. This note supports the prescribed-chain
foundation. It supplies neither a validated pass schedule nor plant settings
for 6 mm → 0.05 mm. Source access depth is stated so that abstracts, patents
and manufacturer descriptions are not mistaken for independent mill data.

## 1. Gauge and deformation history

Let `h_i` denote full per-layer thickness in metres. For a prescribed pass,
`d_i=h_i−h_(i+1)`, `r_i=d_i/h_i`, and `e_i=ln(h_i/h_(i+1))`. Therefore
`Σe_i=ln(h_0/h_N)` and `h_N=h_0 Π(1−r_i)`. Percentage reductions do not add.
For ideal homogeneous incompressible plane strain, the principal logarithmic
strains are `(e_i,0,−e_i)` and the von Mises equivalent increment is
`(2/√3)e_i`. This is a **kinematic idealisation**, not a measured local plastic
path: shear/reversal through the thickness can change accumulated equivalent
plastic strain and texture [S2, S3].

| Illustrative transition | Reduction | `ln(h_in/h_out)` | Ideal `Δεeq` |
|---|---:|---:|---:|
| 6 → 3.5 mm | 41.6667% | 0.538997 | 0.622380 |
| 3.5 → 2 mm | 42.8571% | 0.559616 | 0.646189 |
| 2 → 1.29 mm | 35.5000% | 0.438505 | 0.506342 |
| 1.29 → 0.8 mm | 37.9845% | 0.477786 | 0.551699 |

The complete 6 → 0.05 mm ratio is 120:1, hence 99.1667% total geometric
reduction, `ln(120)=4.787492` and ideal equivalent increment `5.528119`.
These numbers are independent of how many intermediate gauges are chosen;
they establish no material survivability, force or pass count. Total geometric
reduction persists through annealing even when the effective hardening state
changes. An anneal must be an explicit, evidenced state transition.

## 2. Per-pass mechanics and units

For rigid symmetric circular rolls of undeformed radius `R` and draft `d`, the
projected contact length is `L=sqrt(R*d−d²/4)`, with
`alpha=acos(1−d/(2R))`. The conventional no-assist threading screen is
`tan(alpha)≤mu`. A failed screen does not prove an established tensioned pass
is physically impossible; it identifies a model/threading condition to review
[S4, S7]. The existing solver also checks model-specific traction and power
conditions. None is a mill rating.

Steady incompressible constant-width mass continuity gives
`rho*w*h_in*v_in = rho*w*h_out*v_out`. For a reversing mill, the next pass
may use a different throughput after coiling/delay. Front/back tension inputs
are **stresses** [Pa]; axial force at a boundary is `T=sigma_t*w*h` [N]. A
reel torque bound depends on coil radius and cannot be inferred from a stress
limit alone. Forward slip is the strip/roll relative-speed outcome under the
selected geometric convention, not an independent control [S4, S7].

Separating force is approximately `w∫p(x)dx` [N] for the chosen projected
contact model. For two identically driven rolls, mechanical drive power is
`2*M_per_roll*omega`, with torque [N m] and speed [rad/s]. Torque inferred
from a half-contact-length lever arm is an estimate, not a universal identity
for foil/tension conditions. Electrical, reel, and idle/reversal power remain
separate ledgers. Signed drive power may be regenerative under other models;
dissipative plastic/sliding generation cannot be negative by sign convention.

The existing optional Hitchcock radius is an enlarged **circular** contact
approximation, not a noncircular foil solution. Fleck et al. [S5] show a
finite no-slip central region under their thin-foil conditions. Their example
transition gauges depend on roll modulus/radius, reduction, friction and
strength; they are not universal switching thresholds. The present 300 µm
rejection is a conservative **software guard**, not a physical minimum gauge.

## 3. State, temperature and operating roles

An implementable chain needs `state_out_i = deform(state_in_i, pass_i)` followed
by `state_in_(i+1) = interpass(state_out_i, declared event_i)`. Aluminium
through-process modelling transfers stress/strain/history and temperature,
and treats intermediate annealing as an explicit simplifying reset [S8]. The
current foundation transfers a scalar assumed hardening strain and a supplied
absolute temperature. It does not simulate recovery, recrystallisation, coil
thermal residence or temperature feedback into flow stress.

Setpoints, observations, model parameters and predictions have different
meanings. Pass target exit gauge is a requested product gauge, **not** a
screwdown or unloaded roll-gap command. That translation requires loaded mill
stretch, roll stack deformation and thermal crown. Friction and flow stress
are material/contact model parameters; neither may be freely lowered to make
a candidate pass a feasible control policy. ABB describes pass-dependent
reductions, tensions, speeds and cooling and separates threading, steady
rolling, deceleration and tailout [S7]. A steady front tension cannot silently
be credited at initial threading.

For thermal accounting, the strip/roll interface must have one signed heat
transfer in equal and opposite ledgers. Sliding generation is
`|tau|*|v_rel|` [W/m²], zero at sticking; plastic work heat requires a
declared/calibrated partition, and contact conductance is distinct from
lubricant/coolant flow. The previous [flowing-energy](../energy-handoff.md)
and [passive-contact](../passive-contact.md) modules are conditional balances,
not a predictive interpass cooling model. The foundation therefore records
boundary inputs and observed temperatures without changing predicted force.

## 4. Foil and layer topology

European Aluminium [S10] describes successive foil passes and double rolling
as typical below about 60 µm, while its glossary includes single rolling from
35–200 µm and double rolling from 5–70 µm. Thus 50 µm lies in an overlap;
the route must be supplied. Layer gauge, layer count and total pack gauge are
different quantities. An `n`-layer pack has nominal total gauge `n*h_layer`,
but interlayer contact, lubrication, tension and separation require a distinct
model. The executable foundation accepts **one declared layer** and refuses
to infer pack rolling or disguise 100 µm pack gauge as a 100 µm single strip.
Manufacturer foil-mill configurations [S12] support route/equipment metadata,
not a universal transition thickness. Foil patents [S14] can test topology
and units but do not calibrate this model's force or torque.

## 5. Route search after replay

The next scheduler should use a deterministic prescribed-chain evaluator as
the independent judge of every candidate. A bounded first search could
enumerate pass count, log-gauge nodes and caller-supplied discrete controls,
then replay each edge with current material/thermal state. Its graph state
must include relevant history; two paths at the same thickness can have
different hardening or temperature. A reduction-only lower bound
`ceil(ln(h_final/h_initial)/ln(1−r_max))` is geometric only. Missing model
physics, plant ratings or pass ranges imply **indeterminate**, never green.

Candidate objectives need explicit scope: fewest passes; peak *normalised*
force/torque/power utilisation when ratings are known; or elapsed time/energy
only after reversal, idle, mass/length, efficiency and reel conventions are
defined. Summing kW does not give energy. A grid result is best within that
grid and model, not a global or production optimum. Aluminium hot-tandem
optimisation [S15] is an objective precedent, not cold-foil calibration. A
recent AA8075 foil study [S16] has pass-specific table statistics but its
supplemental tension units, interpreted literally, yield implausible stress;
its physical inputs are quarantined pending clarification. Public AA5052 hot
pilot data [S17] can exercise schema/units, not validate cold foil force.

## 6. Source register and access depth

| ID | Primary source and access | Use / limitation |
|---|---|---|
| S2 | [Tsuchida (2009), AA1050 pass-schedule texture](https://doi.org/10.2464/jilm.59.555), publisher abstract | Similar total reduction through different paths altered texture/properties; no transferrable pass limits. |
| S3 | [Cantergiani et al. (2024), aluminium near-surface texture](https://doi.org/10.1007/s11661-024-07472-y), publisher abstract/introduction | Local shear-path caution; no model constants copied. |
| S4 | [Medraj, Concordia rolling lecture](https://users.encs.concordia.ca/~mmedraj/mech421/lecture%205%20rolling.pdf), official teaching slides 11–16 | Introductory geometry, bite and unit conventions, not alloy calibration. |
| S5 | [Fleck et al. (1992), *Cold rolling of foil*](https://sage.cnpereading.com/storage/sage/journal/article/PIB/1992/PIB_1992_206_2/unzip/10.1243_PIME_PROC_1992_206_064_02.pdf), full 13-page paper | Noncircular elastic contact/no-slip zone under stated idealisations; example gauges are parameter-specific. |
| S7 | [ABB, *Rolling models* (2009), pp. 43–47](https://library.e.abb.com/public/cab489262e40ea6ac1257beb0029324a/ABB%20Review_1_2009_72dpi.pdf), full relevant pages | Industrial schedule/preset/control architecture; no numerical limits for this mill. |
| S8 | [Pachnek et al. (2024), aluminium through-process cold rolling](https://link.springer.com/chapter/10.1007/978-3-031-58006-2_2), full open chapter | Pass state/temperature/anneal treatment; AA6016 benchmark ends at 1 mm, not foil. |
| S10 | [European Aluminium (2018), §6.1/glossary](https://european-aluminium.eu/wp-content/uploads/2023/01/European-Aluminium_Environmental-Profile-Report-2018_full-version.pdf), full relevant pages | Foil route and overlapping single/double ranges; product category is not mechanics cutoff. |
| S12 | [Achenbach foil-mill description](https://www.achenbach.de/en/machines-equipment/optimill-rolling-mills/optimill-foil-rolling-mills/), manufacturer page | Route/equipment diversity, not user mill data. |
| S14 | [US20040088840A1 foil route](https://patents.google.com/patent/US20040088840A1/en), full patent Table 1 | Kinematic/time/layer test lead; patent example is not independent force validation. |
| S15 | [Hu et al. (2016), aluminium hot tandem schedule optimisation](https://doi.org/10.1007/s00170-015-7909-1), publisher abstract/references | Objectives/architecture only; hot process and no full numeric benchmark retrieved. |
| S16 | [Choi et al. (2026), AA8075 foil optimisation](https://psecommunity.org/wp-content/plugins/wpor/includes/file/2606/LAPSE-2026.0468-1v1.pdf), full proceedings paper; [supplement](https://psecommunity.org/wp-content/plugins/wpor/includes/file/2603/LAPSE-2026.0041-1v1.docx), full tables | Pass-specific ranges are empirical marginals, not limits; tension-unit semantics unresolved. |
| S17 | [Smeulders, STLE 2017 AA5052 hot pilot](https://www.stle.org/images/pdf/STLE_ORG/AM2017%20Presentations/Nonferrous%20Metals/STLE2017_Nonferrous%20Metals%20II_Session%206L_B.%20Smeulders_The%20Use%20of%20a%20Pilot%20Mill%20for%20Development%20of%20Lubricants%20for%20Aluminum%20Hot%20Rolling.pdf), full three pages | Pass-varying input example; hot process and missing constitutive/force tables. |

No accessible source here provides a calibrated complete 6 mm → 50 µm
benchmark for the user's unknown alloy and mill. The existing [AA5052 cold
study](../aa5052-study.md) remains a scoped 4.10 → 1.72 mm comparison, not
validation of a foil finishing model.
