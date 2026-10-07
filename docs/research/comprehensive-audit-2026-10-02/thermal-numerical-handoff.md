# I01 thermal numerical handoff — documentation only

Prepared 2026-10-02 against physics/code baseline [`caec37ef86a8b78e1eb88292ea6368bfb64bcbdc`](https://github.com/Gravelaw/PhysicRollModel/tree/caec37ef86a8b78e1eb88292ea6368bfb64bcbdc). Documentation checkout at the start of this follow-up was `ade4d1d0c4d5f8e6ca943ea1af9860446ead01d9`; `git diff caec37e..HEAD -- physicroll tests scripts scenarios` was empty. The user requires subsequent rolling development in Codex cloud after research completion. This handoff proposes the scope of that later task; it changes no executable, test, scenario, existing artifact, heat-transfer law or plant setting.

**Two different midpoint approximations require separate decisions.** A temperature/time-step guard can restrict the current law without changing it. A different roll time integrator addresses temporal overshoot. A different treatment of the flowing strip changes the spatial contact approximation and must be an explicit, versioned model choice. Reducing the time step does not change the strip's heat-capacity rate, and dividing conductance by the number of time steps is not a valid numerical fix.

The original I01 counterexample fails a zero-source maximum principle and whole-step entropy despite passing the present energy and midpoint-entropy checks. A second counterexample overshoots the stream temperature even at a very small time step; its whole-step entropy is positive. Both maximum-principle and entropy tests are therefore needed. The ordinary stored examples examined here do not exhibit those counterexamples at their supplied parameters. They remain synthetic conservation/approximation examples, with the qualifications below, and provide no measured aluminium validation.

[thermal-demo-checks.json](thermal-demo-checks.json) is the structured companion: complete public-API input snapshots for the flowing examples and counterexamples; input/code/artifact SHA-256 values; exact commands; outputs; zero-source checks; temporal refinements; heat-partition sensitivity and checked-schedule replay evidence. It contains original project analysis and synthetic data only.

## 1. The three existing operators have different meanings

| Operator | Strip treatment | Roll treatment | Contact treatment | Existing guarantee |
|---|---|---|---|---|
| `thermal.step` | Finite closed capacity `m_s c_s` J/K | Finite capacity `m_r c_r` J/K | Explicit flux at current temperatures, area-specific coefficient times supplied area | Explicit nonoscillatory step bound and first-law bookkeeping for this two-capacity model |
| `handoff_pass`, prescribed mode | Steady flow `mdot*Delta H_s`, W | Finite aggregate storage `M*Delta H_r/dt`, W | Caller supplies signed total `Q_contact`, W | Energy and property-domain consistency; prescribed heat is not certified passive or measured |
| `handoff_pass`, passive mode | Same steady flow | Same finite aggregate storage | Supplied `G`, W/K, multiplied by arithmetic endpoint temperature difference | Scalar root, property-domain, first law and representative-temperature entropy proxy; insufficient whole-step physical admissibility |

`G` is the total conductance for both interfaces. It is not an area-specific heat-transfer coefficient and it is not inferred from lubricant identity. Solid-slip power already includes both interfaces. The duration belongs to roll storage and to the amount of fresh strip processed; it does not turn the strip into a closed batch. The current module predicts neither a resolved bite temperature profile, interpass cooling, roll-surface field, material recovery nor feedback of temperature into flow stress.

The `contact_entropy_production_w_k` output is `Q*(1/T_s,mid - 1/T_r,mid)`. It is a representative-temperature contact diagnostic, not the entropy balance of a finite integration step. The later implementation should label this distinction explicitly, retaining compatibility or using a schema/version change rather than silently changing the meaning of the field.

## 2. Exact algebra of the current passive closure

Use positive `Q` for heat from roll to strip. Let

```text
A = beta*P_plastic + f_strip*P_slip - Q_cool,s       [W]
B = (1-f_strip)*P_slip - Q_cool,r                   [W]
H_s(T) = integral c_s(T) dT                        [J/kg]
H_r(T) = integral c_r(T) dT                        [J/kg]
mdot*[H_s(T_s,out)-H_s(T_s,in)] = A + Q            [W]
M*[H_r(T_r,out)-H_r(T_r,in)]/dt = B - Q            [W]
Q = G*[(T_r,in+T_r,out)/2-(T_s,in+T_s,out)/2]      [W]
```

The last equation combines an arithmetic **stream inlet/outlet representative temperature** with a **roll temporal midpoint temperature**. Neither arithmetic average follows merely from the first law. The scalar bisection in `energy_handoff._passive_contact_power` solves these declared equations, and its uniqueness/monotonic residual is not a maximum-principle or entropy proof.

For constant specific heats define

```text
C_s = mdot*c_s            [W/K]   — stream heat-capacity rate
C_r = M*c_r/dt            [W/K]   — roll interval capacity divided by time
D = T_r,in - T_s,in       [K]

Q = G*[D + B/(2*C_r) - A/(2*C_s)] /
        [1 + G/(2*C_s) + G/(2*C_r)]
T_s,out = T_s,in + (A+Q)/C_s
T_r,out = T_r,in + (B-Q)/C_r
```

These expressions are independently derived from the inspected implementation. They introduce no empirical law or coefficient. With zero non-contact sources/exports (`A=B=0`), both outlets must remain between the two inlet temperatures for a passive single-contact approximation. For unequal inlet temperatures (`D != 0`), the current constant-cp algebra satisfies that bound exactly when

```text
G/2 * abs(1/C_s - 1/C_r) <= 1.
```

If `D=0`, `Q=0` and both equal temperatures are preserved for any nonnegative G; the inequality is not necessary in that degenerate case. For a hotter roll this follows from `0 <= Q <= min(C_s,C_r)*D`; reversed temperatures give the same criterion. This is a bound for the declared finite-step reduction, not a validated rolling operating envelope. In particular, coincident capacities can satisfy this whole-step bound even though the assumed internal stream/roll temperature representation remains crude. Passing the bound is not proof of a resolved contact field.

For variable positive cp, an unchanged-law guard can check the solved zero-source root against enthalpy bounds. For `T_r,in > T_s,in`, when both property curves cover the endpoints:

```text
0 <= Q <= min(
  mdot*[H_s(T_r,in)-H_s(T_s,in)],
  (M/dt)*[H_r(T_r,in)-H_r(T_s,in)]).
```

Reverse the sign and endpoints for a colder roll. Do not extrapolate cp beyond its supplied domain to construct a bound. Intersect physical and property bounds or reject an unsupported query. If the root lies outside admissible bounds, rejecting the current approximation preserves its law; clipping Q or temperatures would generally break that law and possibly conservation.

### Exact zero-source entropy balance

For the flowing strip and finite roll with no non-contact sources or exports, entropy production averaged over the current single represented interval is

```text
Sdot_generated = mdot*[s_s(T_s,out)-s_s(T_s,in)]
               + (M/dt)*[s_r(T_r,out)-s_r(T_r,in)] >= 0,
s(T_b)-s(T_a) = integral[T_a:T_b] cp(T)/T dT.
```

For constant cp this becomes the logarithmic expression used in I01. For each piecewise-linear segment `cp(T)=a*T+b`, the exact integral is `a*(T_b-T_a)+b*ln(T_b/T_a)`; split at knots and use stable `log1p` arithmetic. The audit's independent entropy routine passed constant-cp analytic, antisymmetry and knot-additivity checks, and agreed with a 20,000-interval Simpson integration to less than `1e-6 J/(kg K)` for a variable-cp curve.

For the ordinary heated/cooled examples, the JSON records thermal-state entropy change separately and marks the full entropy test **incomplete**. Prescribed cooling export does not specify its entropy-transfer temperature; a fluid observation does not establish that relationship. The nonthermal plastic-work allocation is not an identified free-energy/entropy state. Do not silently supply those missing closures or promote positive thermal-state entropy to full-process thermodynamic validation.

## 3. Reproducible counterexamples

Both probes use the public `handoff_pass` API, valid bounded constant-cp curves and the existing test-suite technique of zeroing the six mechanical heat/work/residual fields consistently to isolate the thermal operator. The remaining synthetic mechanical state transition is retained. These are numerical operator tests, not complete physical rolling experiments or proposed plant parameters.

Common inputs: strip inlet 300 K; roll inlet 320 K; `mdot=10.8 kg/s`; `c_s=900 J/(kg K)`; `c_r=500 J/(kg K)`; `G=1e6 W/K`; zero plastic/slip heat, prescribed contact heat and cooling exports; cp domain 250–450 K; the ordinary mechanical assumed temperature domain remains 273.15–420 K.

| Case | Roll mass | Duration | Strip outlet | Roll outlet | Whole-step entropy rate | Outcome |
|---|---:|---:|---:|---:|---:|---|
| I01 temporal overshoot | 1 kg | 5 s | 300.407251 K | 280.415168 K | −0.0189788 W/K | Violates both maximum principle and entropy |
| I01 stream overshoot | 500 kg | 0.001 s | 339.235732 K | 319.998475 K | +2.923883 W/K | Violates maximum principle despite positive entropy |
| Same stream case, dt/100 | 500 kg | 0.00001 s | 339.237213 K | 319.999985 K | +2.924143 W/K | Smaller time step does not repair stream overshoot |

The first case's first-law residual is `−2.21e-10 W`, and its present midpoint entropy proxy is positive `1.7386814e-4 W/K`. The later stream cases also pass the existing relative first-law gate (`1.33e-11` and `4.85e-10` respectively). Their larger absolute W residual at the shortest interval illustrates subtractive cancellation when tiny roll enthalpy changes are divided by dt; judge conservation with a dimensional error budget as well as relative residuals.

Minimal replay from the durable input snapshot, from repository root:

```bash
python - <<'PY'
import json, math
from pathlib import Path
from physicroll.materials import MaterialState
from physicroll.energy_handoff import (HeatCapacityCurve, PassHeatBoundary,
                                      PassiveContactBoundary, handoff_pass)
file = Path('docs/research/comprehensive-audit-2026-10-02/thermal-demo-checks.json')
audit = json.loads(file.read_text())
def cp(x):
    return HeatCapacityCurve(**{**x, 'temperature_k': tuple(x['temperature_k']),
        'heat_capacity_j_kg_k': tuple(x['heat_capacity_j_kg_k'])})
for case in audit['findings']:
    x = case['api_inputs']
    state = MaterialState(**{**x['state_in'], 'history': tuple(x['state_in']['history'])})
    boundary = PassHeatBoundary(**x['boundary'])
    r = handoff_pass(x['mechanics'], state, cp(x['strip_cp']), cp(x['roll_cp']),
                    boundary, passive_contact=PassiveContactBoundary(**x['passive_contact']))
    ts, tr = r['strip_temperature_out_k'], r['roll_temperature_out_k']
    entropy = (r['mass_flow_kg_s']*900*math.log(ts/300)
               + boundary.roll_effective_mass_kg*500/boundary.duration_s*math.log(tr/320))
    print(case['case_id'], ts, tr, entropy)
    assert min(ts, tr) < 300 or max(ts, tr) > 320
PY
```

The assertion reproduces an **open defect/domain limitation**, not a passing acceptance criterion. The structured input snapshots make this script self-contained without needing the temporary audit driver.

## 4. Corrective choices — keep their meanings distinct

| Class | Candidate | What stays the same | What changes / cannot be claimed |
|---|---|---|---|
| A: guard current law | Zero-source physical/entropy bounds; justified general-source domain checks; reject unsupported roots | Existing equations, G, cp, mechanical partitions, state semantics | Narrows admitted numerical domain; does not improve contact physics or identify parameters |
| A: temporal subdivision | Carry roll state through smaller intervals; fresh upstream strip for each interval; same G and source powers | Supplied conductance, rates, total duration, physical roll mass, within-pass flow | Changes numerical approximation over the interval; cannot by itself repair large stream `G/(mdot*cp)` |
| B: time integration | Backward Euler in roll enthalpy, or exact constant-property roll integration | Explicitly declared instantaneous stream representative closure and G | Version the time-evaluation/output contract; temporal stability does not cure the stream spatial approximation |
| C: spatial contact revision | Conservative serial stream segments or continuous plug-flow/exponential reference | Total physical conductance and total allocated powers only if their distribution is explicitly supplied/assumed | Introduces a spatial closure/distribution. Requires an explicit model version and independent validation; not a silent solver replacement |

### A. Unchanged-law guards and justified substeps

The lowest-scope follow-up is to add counterexample acceptance tests and reject unsupported passive results while preserving the current equations. The zero-source guard is exact for that test domain. A general-source maximum principle must account for supplied internal heat and external sinks; it must not reject legitimate source-driven heating simply because an outlet exceeds initial temperatures. Derive source-inclusive bounds or retain an explicitly narrow documented supported domain. A first-law pass alone never turns prescribed powers into qualified physical boundaries.

For temporal subdivisions `dt_j` with `sum(dt_j)=dt`:

- Keep `M`, G and the physical stream mass rate unchanged. Do not divide G by the number of time steps. A W-valued source remains a power; multiply it by `dt_j` exactly once to get energy.
- Carry only the roll thermal state across time substeps of a single steady pass. Each substep receives fresh strip at the specified upstream material state. Feeding that substep's strip outlet back as the next inlet would treat the stream as a reheated batch and be a different problem.
- Do not add strain or append a pass-history item at every thermal substep. Advance the mechanical pass once. Per-pass or per-parcel history remains distinct from numerical integration history.
- Accumulate outlet enthalpy flow: `sum(mdot_j*dt_j*H_s,out,j)/sum(mdot_j*dt_j)`. Invert H only if an explicitly labeled equivalent outlet temperature is wanted; do not silently replace it with the last substep outlet or an arithmetic temperature average.
- Accumulate entropy flow as `sum(mdot_j*dt_j*Delta s_j)`. Entropy of the enthalpy-mean outlet is generally not the mean outgoing entropy and can hide error.
- A later rolling pass may explicitly use a prior pass's representative outlet as its inlet under the existing immediate-carry assumption. That physical pass transition is different from a numerical time subdivision. A resolved time-varying strip outlet would require an explicit decision about parcel/coil aggregation before schedule propagation.

Current `handoff_pass` reports one strip outlet and one roll endpoint. A time-substepped implementation therefore needs a defined output contract: equivalent enthalpy-mean strip outlet, last/instantaneous outlet, total processed mass and entropy flow should not be conflated. That contract is part of the later task, not an assumed change here.

### B. Alternative roll integration with the stream approximation held explicit

To isolate time integration, define an instantaneous algebraic stream closure at roll temperature `T_r(t)`:

```text
mdot*[H_s(T_s,out(t))-H_s(T_s,in)] = A + Q(t)
Q(t) = G*[T_r(t)-(T_s,in+T_s,out(t))/2]
M*dH_r(T_r(t))/dt = B-Q(t).
```

This is a declared continuous-time interpretation of the present stream representative closure. It is not automatically identical to the published discrete endpoint contract; make the model/time-integrator version explicit.

For constant properties and sources define physical roll capacity `C_R=M*c_r` J/K and

```text
Gamma = G/[1+G/(2*C_s)]                         [W/K]
Q(t) = Gamma*[T_r(t)-T_s,in-A/(2*C_s)]
T_eq = T_s,in + A/(2*C_s) + B/Gamma
T_r,out = T_eq + (T_r,in-T_eq)*exp(-Gamma*dt/C_R)
Q_average = B - C_R*(T_r,out-T_r,in)/dt.
```

Handle G=0 by its separate finite-source limit. This exact temporal reference eliminates centered time-step reversal for the declared ODE. Backward Euler in roll enthalpy is a second, dissipative candidate for variable cp. Its coupled stream/roll scalar equations can be bracketed using positive cp and the same property domains. Test the expected first-order or exact temporal behavior independently.

Neither candidate cures the high-conductance stream issue. With a nearly fixed roll and zero sources, the unchanged stream closure has

```text
T_s,out-T_r = [(1-NTU/2)/(1+NTU/2)]*(T_s,in-T_r),
NTU = G/C_s.
```

It overshoots the reservoir for `NTU>2` regardless of the roll time integrator. The implemented full-step constant-cp roll midpoint corresponds, after eliminating the stream, to an amplification factor `(1-z/2)/(1+z/2)` with `z=Gamma*dt/C_R`; its temporal reversal occurs when `z>2`. These two ratios explain why a single time-step fix cannot cover both issues.

### C. Explicit spatial contact alternatives

For a new uniformly distributed conductance, uniform-temperature roll, constant-cp, zero-source **steady plug-flow** model, an independent reference is

```text
T_s,out = T_r + (T_s,in-T_r)*exp(-G/C_s).
```

This stays between inlet and roll temperatures for every nonnegative G. It assumes a spatial distribution that the current one-node ledger does not specify. With a uniformly distributed strip power A, the corresponding steady reference is `T_s,out=T_r+A/G+(T_s,in-T_r-A/G)*exp(-G/C_s)`, with G=0 handled separately. Nonuniform plastic/friction heat partition, contact geometry or a varying roll surface require further declared distributions; the present mechanical total powers do not uniquely supply them.

A serial stream-segment method could use `sum(G_j)=G`, conserve stream enthalpy from one spatial segment to the next, and exchange equal/opposite heat with the finite roll. `G_j=G/N` is justified only as an explicit equal-area/equal-conductance **spatial** discretization, not as a time-stepping trick. Source powers must also be distributed with declared weights summing to the original totals. Preserve both-interface counting once. Spatial segment refinement can then be compared with the exponential zero-source reference and, for variable cp, with an independently solved enthalpy ODE. This is a model revision requiring review and later experimental validation, not an implementation-only “fix.”

## 5. Fresh ordinary-demo assessment

All computations used Python 3.12.14. Generated outputs were placed in `/tmp/physicroll-thermal-handoff-2026-10-02`; existing tracked artifacts were not overwritten. Exact commands:

```bash
python scripts/build_v03.py --out /tmp/physicroll-thermal-handoff-2026-10-02/v03_foundations.result.json
python scripts/run_v03_study.py --out /tmp/physicroll-thermal-handoff-2026-10-02/v03_sensitivity.json
python scripts/run_flowing_energy_demo.py --config scenarios/flowing_energy_demo.json --out /tmp/physicroll-thermal-handoff-2026-10-02/flowing_energy_demo.json
python scripts/run_flowing_energy_demo.py --config scenarios/passive_contact_demo.json --out /tmp/physicroll-thermal-handoff-2026-10-02/passive_contact_demo.json
PYTHONPATH=tests python -m unittest -v test_energy_handoff test_passive_contact test_checked_schedule test_v03.ThermalTests test_mechanics_audit.MechanicsAuditTests.test_thermal_exchange_exact_limit_and_nonoscillation
```

The selected **27 existing tests pass in 2.513 s**. The new counterexamples were analytical probes, not changes to those tests.

| Stored example | Fresh comparison | Demonstrated result | Retain / reassess |
|---|---|---|---|
| `scenarios/v03_foundations.json` → `artifacts/v03_foundations.result.json` | Thermal section identical. Whole JSON adds five current slab metadata fields only. | Finite strip/roll capacities 1,800/230,000 J/K; dt 0.01 s; explicit mode ratio 0.00123016; thermal residual −1.31e−9 J. Isolated zero-source contact stays between 295/300 K and has +0.0564661 W/K entropy rate. | Retain as the separate synthetic explicit two-capacity example. Whole-file artifact metadata should be refreshed only in a later deliberate rebuild. |
| `artifacts/v03_sensitivity.json` | Byte-identical | Stored independent heat-fraction and mechanical sensitivities reproduced. | Retain its stated synthetic scope; it is not a coupled cooling calibration. |
| `scenarios/flowing_energy_demo.json` → corresponding artifact | Byte-identical | Two prescribed-contact passes conserve energy; contact inputs −2,000/−2,300 W. First-law maximum absolute residual 1.15e−9 W. | Retain as a prescribed-boundary ledger. I01 does not convert these supplied powers into a physical contact law; boundary qualification remains necessary. |
| `scenarios/passive_contact_demo.json` → corresponding artifact | Byte-identical | G 1,000 W/K, roll mass 500 kg, dt 5 s, flow 10.8 kg/s. The isolated source-free contact tests pass bounds and exact variable-cp entropy for both recorded pass inlet states (strip-to-roll heat flow). | Retain only the demonstrated bounded synthetic approximation. Broader advertised admissibility and large-G/small-mass/long-step use require reassessment. |
| Existing checked two-pass thermal fixture in `tests/test_checked_schedule.py` | Reconstructed independently; no standalone stored schedule JSON exists | `CHECKED_SYNTHETIC_SCHEDULE`, declared bounds `INDETERMINATE`; material and roll temperature carry verified; maximum residual 1.12e−9 W. Fresh `/tmp/.../checked_schedule_thermal_replay.json`. | Retain composition evidence. Any accepted thermal-model revision must be replayed through schedules before adoption. |

For the ordinary flowing and passive configurations, cp knots are `(273.15,350,420) K`; strip cp is `(880,905,940)` and roll cp `(450,470,500) J/(kg K)`. Both use `beta=0.2`, slip-to-strip fraction `0.6`, 500 kg roll effective mass and 5 s duration. Supplied strip cooling is 5,000/5,500 W and roll cooling 3,000/3,200 W. Pass 1 starts at strip/roll 300/295 K. Pass 2 directly carries the two distinct predicted temperatures. All of these values are synthetic and remain unqualified.

| Pass | Prescribed-contact strip/roll outlet, K | Passive-contact strip/roll outlet, K | Passive isolated-contact bounds | Passive isolated entropy, W/K |
|---|---|---|---|---:|
| 1 | 308.155685 / 295.581131 | 307.492307 / 295.721209 | Pass | +0.2501194 |
| 2 | 314.904917 / 296.072356 | 313.014047 / 296.472383 | Pass | +1.3506201 |

The isolated-contact tests set mechanical heat sources and cooling exports to zero while preserving the respective ordinary inlet states, cp curves, mass flow, duration and G. They do not imply the fully heated case should satisfy a zero-source temperature bound. Full-source exact entropy closure remains unavailable, as explained in Section 2.

For the passive ordinary inputs, conservative indicators over the supplied cp curves are `G/(2*mdot*cp_s,min)=0.05261` and `G*dt/(2*M*cp_r,min)=0.01111`. These are numerical diagnostics, not physical admissibility/calibration ranges. Each pass was temporally repeated with 1, 2, 4, 8, 16 and 32 substeps, keeping G and powers fixed, carrying the roll only, and processing fresh stream at the same pass inlet each substep. At 32 subdivisions the change from the single-step solution is under `0.000028 K` for the roll and under `0.000130 K` for the enthalpy-mean strip outlet. The 16→32 changes are under `8.1e−8 K` and `3.9e−7 K` respectively. Last fresh-stream outlet differs from the mean by about `0.035 K`; the distinction is therefore real even in these mild examples.

The prescribed-power examples compose in enthalpy to numerical roundoff under the same subdivision, as expected with constant supplied powers. The standalone explicit-Euler example changes its strip outlet by about `0.000259 K` between 1 and 32 subdivisions, with first-order refinement. A 3×3 sweep of `beta={0,0.5,1}` and slip partition `{0,0.5,1}` for each of the four flowing passes produced 36 successful first-law/property-domain checks. This verifies allocation bookkeeping over these inputs; it does not identify heat fractions or supply full-process entropy closure.

The checked two-pass fixture uses the flowing config but deliberately changes pass-2 tensions to 12/18 MPa and friction to 0.09, with 256/512-cell mechanics. Its outlets are approximately 308.155677/295.581130 K then 315.379827/296.139371 K (strip/roll). It must not be mislabeled byte-equivalent to the stored two-pass demo, which uses different pass-2 settings and 512/1024 cells. The complete fixture inputs and output digest are in the JSON.

### Digests and artifact differences

Full input/code and stored/fresh artifact digests are in the structured file. Selected exact SHA-256 values:

| File | SHA-256 |
|---|---|
| `physicroll/energy_handoff.py` | `28867e9dc3f3db2cd56d314dbd82eafbf1a0bebb39232d96d04d90fd9a9ed821` |
| `physicroll/thermal.py` | `00aafdd799b7432ae9d5a73c6c314db4bc966beaa692b6abae3f8accedd2f3e1` |
| `scenarios/flowing_energy_demo.json` | `5ca667a5bb6c5243de0a2e0fcd63e9c329203d8fa122c4749c37db0ac23d6848` |
| `scenarios/passive_contact_demo.json` | `ef24196b6c6bc37712eeaf826bc4efd88014dbf675c568e8e5d3233bed292607` |
| Stored and fresh `flowing_energy_demo.json` | `70ba963e8a53d718dee4a14f81aa488072f888a73547982488f214b54cebd5c4` |
| Stored and fresh `passive_contact_demo.json` | `1ec69cf7cec240845f5c251bab49b11f9989f999289df085c49166ec245a3942` |
| Stored `v03_foundations.result.json` | `1c27fbc00bc9d5d37a5b6d3f883a96d7305fa36dddc6cb9f51a36bd133000779` |
| Fresh `v03_foundations.result.json` | `cf9c076dc85c6ab986639f2bdf8625bab91dd8f0d31ef28d7c0cde9429b792d4` |

The only foundations changes are added `slab_optional` fields: `contact_radius_m`, `entry_plane_strain_strength_pa`, `exit_plane_strain_strength_pa`, `physical_roll_radius_m` and `roll_angular_speed_rad_s`. Existing values, including the thermal object, are unchanged. The structured file distinguishes this schema/metadata drift from a thermal regression.

## 6. Acceptance tests for the later numerical task

Write the regression/acceptance cases before changing code. Select the allowed remedy/model class explicitly. Tests of a retained legacy mode may legitimately expect an out-of-domain rejection; they must not force an admitted nonphysical result to become a physically accurate prediction without a reviewed law change.

| Test family | Required evidence | Distinction to preserve |
|---|---|---|
| First law | Equal/opposite contact; plastic heat + nonthermal allocation equals plastic work; slip partitions sum once; integrated stream enthalpy + roll storage + exports reconciles sources | J versus W; mass flow versus finite mass; both interfaces versus per-interface quantities |
| Zero-source maximum principle | Reproduce all three counterexamples; reject or resolve them under the selected mode. Test hot/cold reversal, equal temperatures and unequal capacities. | Positive whole-step entropy does not exempt a temperature overshoot |
| Whole-step entropy | Exact constant-cp logarithms; exact piecewise-linear `cp/T` integration; nonnegative isolated passive entropy within numerical tolerance | Retain midpoint diagnostic separately; do not invent entropy of cooling/nonthermal allocations |
| Variable cp | Positive increasing/decreasing cp, knot crossings, exact endpoint inversion, asymmetric property domains, no extrapolation | Piecewise enthalpy and entropy integrals are different quantities |
| Sign and zero cases | G=0; equal inlet T with zero sources; reversed temperature difference; zero/slip/plastic partitions | With nonzero sources, initial temperature ordering alone need not determine representative contact sign |
| Limits | Small G; small dt at fixed G; very large roll capacity; tiny roll capacity; large stream NTU; supported property endpoints | Fixed-roll stream overshoot cannot be repaired by roll time refinement |
| Temporal refinement | 1/2/4/... subdivisions; fresh upstream stream each interval; unchanged G/M/powers; conservative enthalpy and entropy aggregation | Assert expected order for the selected integrator in smooth cases; convergence across knots separately |
| Spatial partition refinement, only for class C | Preserve sum G_j and sum source weights; serial stream enthalpy; comparison with exponential fixed-roll reference | This is an explicit spatial model revision; do not divide G by time-step count |
| Heat partitions | beta and slip fraction 0/0.5/1; nonthermal allocation and both-interface power remain traceable | Allocation endpoints are numerical tests, not evidence that a real alloy's beta is 0 or 1 |
| Numerical failure | Missing admissible root, incompatible property ranges, nonfinite magnitudes, extreme scale/cancellation, failed adaptive tolerance | Report failure/domain rejection; no silent clipping, extrapolation or convergence claim |
| Schedule integration | Ordinary prescribed and passive cases, direct roll/strip carry, explicit prescribed interpass values, different roll identity, pass-local inputs and per-pass failures | Thermal substeps are not new material passes; no invented interpass cooling or strain reset |
| Reproducibility and API | Deterministic serialized input/output; solver/closure/integrator versions; legacy-mode expectations; original artifacts preserved | Deliberately changed outputs need reviewed rebaselines, not overwritten historical evidence |

Proposed **numerical** starting tolerances, to be reviewed with scale-specific cancellation/error estimates:

- For ordinary-scale reference cases, integrated first-law residual `|R_E| <= 1e-7 J + 1e-10*E_scale`, where `E_scale` is the sum of absolute exchanged/generated/stored energies, with a declared minimum scale. Report an ULP/cancellation bound for tiny enthalpy differences rather than masking them with a large relative tolerance. The existing production `1e-8` relative allocation gate should not be loosened to accommodate the counterexamples.
- Zero-source entropy: `Delta S >= -(1e-8 J/K + 1e-10*S_scale)`, with `S_scale` the sum of absolute stream/storage entropy contributions. This is a roundoff allowance, not permission for thermodynamic error of a chosen percentage. Evaluate substeps' entropy flows directly rather than entropy of their aggregate temperature.
- Ordinary reference temperature bounds: allow at most `1e-9 K + 1e-12*max(|T|,1 K)`, or a separately derived root/enthalpy-inversion error bound for extreme scales. Do not clamp physical overshoot into this interval. Both reported overshoots exceed these allowances by many orders of magnitude.
- For smooth convergence examples, use successive refinement and an independent limit, with a provisional `1e-5 K` output convergence target and `1e-6` relative integrated-contact-energy target. Report the achieved refinement and method order. These numbers define software-verification precision only; data uncertainty and decision needs must later set physical acceptance tolerances.
- Keep source/parameter scale sweeps and domain rejection tests alongside these tolerances. A guard derived only for zero sources does not establish a general-source supported envelope. Freeze any broader support claim until its source-inclusive proof/reference tests exist.

## 7. Proposed subsequent task and stop conditions

Recommended first follow-up after research closure: a narrowly scoped Codex-cloud numerical PR that adds both counterexample families and exact entropy/maximum-principle tests, labels the current representative entropy diagnostic, and defines an explicit admissible domain/rejection for the unchanged passive closure. Preserve prescribed-boundary ledger semantics and the standalone two-capacity solver. Independently review any proposed timestep logic against the fresh-stream rules above. No calibration, new HTC, material law, thermal-force coupling, optimizer recommendation or equipment interface belongs in that first change.

Before implementing class B, decide and document how time-varying strip outlets are represented and passed into subsequent rolling passes; version the integrator/aggregation semantics. Before class C, select the spatial conductance/source distribution and the reference model, and treat the change as a distinct contact approximation. Neither decision may be hidden inside an apparent numerical patch.

Stop if a candidate repair requires dividing G by time-step count, reusing strip outlet as a same-pass time-step inlet, adding thermal substeps to material strain history, inventing boundary entropy/material properties, clipping a root to conceal incompatibility, or using a new spatial law without naming it. Stop predictive thermal optimization over unsupported regimes until the numerical gates pass. Existing ordinary synthetic demonstrations may remain available with their present conditional labels; neither this handoff nor passing these gates establishes aluminium/plant accuracy or authorizes deployment.

## Appendix A. Durable entropy and fresh-stream replay

This documentation-only driver uses the committed companion input snapshots and public model API. It needs no temporary audit script. Run from repository root at the recorded physics baseline. It independently evaluates piecewise-linear entropy, checks the isolated ordinary cases, reproduces the open counterexamples, and repeats all recorded flowing temporal refinements and heat partitions. Its heated-case entropy calculation remains a thermal-state accounting diagnostic, not a complete process entropy balance. The checked-schedule fixture and separate closed-capacity operator can be replayed with the Section 5 commands and their complete JSON inputs; neither is substituted into this flowing-stream driver.

```bash
python - <<'PY'
import bisect
import json
import math
from dataclasses import replace
from pathlib import Path
from physicroll.materials import MaterialState
from physicroll.energy_handoff import (
    HeatCapacityCurve, PassHeatBoundary, PassiveContactBoundary, handoff_pass)

audit = json.loads(Path(
    'docs/research/comprehensive-audit-2026-10-02/thermal-demo-checks.json'
).read_text())

def curve(x):
    return HeatCapacityCurve(**{**x, 'temperature_k': tuple(x['temperature_k']),
        'heat_capacity_j_kg_k': tuple(x['heat_capacity_j_kg_k'])})

def unpack(x):
    state = MaterialState(**{**x['state_in'], 'history': tuple(x['state_in']['history'])})
    contact = x['passive_contact']
    return (x['mechanics'], state, curve(x['strip_cp']), curve(x['roll_cp']),
            PassHeatBoundary(**x['boundary']),
            None if contact is None else PassiveContactBoundary(**contact))

def entropy_delta(cp, ta, tb):
    # Exact integral cp(T)/T: no property extrapolation or private model method.
    cp.validate()
    knots, values = cp.temperature_k, cp.heat_capacity_j_kg_k
    assert 0 < knots[0] <= min(ta, tb) <= max(ta, tb) <= knots[-1]
    if tb < ta:
        return -entropy_delta(cp, tb, ta)
    if tb == ta:
        return 0.0
    points = [ta] + [t for t in knots if ta < t < tb] + [tb]
    terms = []
    for lo, hi in zip(points, points[1:]):
        i = min(bisect.bisect_right(knots, (lo+hi)/2)-1, len(knots)-2)
        slope = (values[i+1]-values[i])/(knots[i+1]-knots[i])
        intercept = values[i]-slope*knots[i]
        terms.append(slope*(hi-lo)+intercept*math.log1p((hi-lo)/lo))
    return math.fsum(terms)

def entropy_rate(result, state, scp, rcp, boundary):
    return math.fsum((result['mass_flow_kg_s']*entropy_delta(
        scp, state.temperature_k, result['strip_temperature_out_k']),
        boundary.roll_effective_mass_kg/boundary.duration_s*entropy_delta(
        rcp, boundary.roll_temperature_k, result['roll_temperature_out_k'])))

def run(args, boundary=None):
    m, state, scp, rcp, original, contact = args
    return handoff_pass(m, state, scp, rcp, original if boundary is None else boundary,
                        passive_contact=contact)

def near(actual, expected, absolute=1e-8):
    assert math.isclose(actual, expected, rel_tol=1e-10, abs_tol=absolute), (actual, expected)

for case in audit['cases']:
    args = unpack(case['isolated_contact_api_inputs'])
    m, state, scp, rcp, boundary, contact = args
    result = run(args)
    entropy = entropy_rate(result, state, scp, rcp, boundary)
    near(entropy, case['isolated_contact_diagnostics'][
        'whole_step_thermal_state_entropy_change_rate_w_k'])
    lo, hi = sorted((state.temperature_k, boundary.roll_temperature_k))
    assert all(lo-1e-8 <= result[k] <= hi+1e-8 for k in (
        'strip_temperature_out_k', 'roll_temperature_out_k'))
    assert entropy >= -1e-8

    args = unpack(case['api_inputs'])
    m, state, scp, rcp, boundary, contact = args
    for recorded in case['time_refinements']:
        n = recorded['substeps']
        dt, roll = boundary.duration_s/n, boundary.roll_temperature_k
        strip_h, stream_entropy, contact_energy = [], [], []
        for _ in range(n):
            local = replace(boundary, duration_s=dt, roll_temperature_k=roll)
            result = run(args, local)  # Same fresh upstream state, G, M and powers.
            ts, roll = result['strip_temperature_out_k'], result['roll_temperature_out_k']
            strip_h.append(scp.enthalpy_j_kg(ts)*dt)
            stream_entropy.append(result['mass_flow_kg_s']*dt*entropy_delta(
                scp, state.temperature_k, ts))
            contact_energy.append(result['contact_heat_to_strip_w']*dt)
        mean_ts = scp.temperature_for_enthalpy(math.fsum(strip_h)/boundary.duration_s)
        total_entropy_rate = (math.fsum(stream_entropy) +
            boundary.roll_effective_mass_kg*entropy_delta(
                rcp, boundary.roll_temperature_k, roll))/boundary.duration_s
        near(roll, recorded['roll_out_k'])
        near(mean_ts, recorded['strip_enthalpy_mean_out_k'])
        near(ts, recorded['last_fresh_stream_out_k'])
        near(total_entropy_rate, recorded['integrated_thermal_state_entropy_rate_w_k'])
        near(math.fsum(contact_energy)/boundary.duration_s,
             recorded['average_contact_heat_w'], absolute=1e-7)
    for recorded in case['heat_partition_sensitivity_checks']:
        local = replace(boundary, plastic_to_heat_fraction=recorded['beta'],
                        solid_slip_to_strip_fraction=recorded['slip_to_strip_fraction'])
        result = run(args, local)
        near(result['strip_temperature_out_k'], recorded['strip_out_k'])
        near(result['roll_temperature_out_k'], recorded['roll_out_k'])
        assert abs(result['thermal_allocation_residual_relative']) <= 1e-8
    print(case['case_id'], 'isolated/refinement/partition replay PASS')

for case in audit['findings']:
    args = unpack(case['api_inputs'])
    m, state, scp, rcp, boundary, contact = args
    result = run(args)
    entropy = entropy_rate(result, state, scp, rcp, boundary)
    near(entropy, case['diagnostics']['whole_step_thermal_state_entropy_change_rate_w_k'])
    lo, hi = sorted((state.temperature_k, boundary.roll_temperature_k))
    assert any(result[k] < lo or result[k] > hi for k in (
        'strip_temperature_out_k', 'roll_temperature_out_k'))
    print(case['case_id'], 'OPEN counterexample reproduced', entropy, 'W/K')
PY
```

This driver intentionally asserts reproduction of the open counterexamples. A later numerical acceptance suite must change those expectations to the selected mode's explicit rejection or admissible solution. The numerical comparison tolerances in this replay test matching recorded computations; they are not experimentally derived accuracy claims.
