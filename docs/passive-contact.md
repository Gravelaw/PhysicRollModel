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
| P1, representative temperatures and passive sign | Full research report (2 October 2026), Section 25 proposes equal/opposite conductive exchange and distinguishes it from friction partition; the midpoint reduction is **this repository's declared approximation** | `PassiveContactBoundary`, `_passive_contact_power` | Independent constant-cp solution; zero/equal/reversed temperature; representative entropy sign; large-G rejection in `tests/test_passive_contact.py` |
| P2–P3 and exact cancellation | Existing E1–E4 [first-law ledger](energy-handoff.md), derived in this repository | `handoff_pass` | Analytic temperatures, total W and J budget, variable cp, unit scaling, carried roll state, step refinement |
| Domain and declared-law no-double-count guard | Existing mechanical and thermal guards; [specialist audit](energy-specialist-audit.md) | `handoff_pass`, `_passive_contact_power` | Mixed-mode, *declared* fitted-effective-law, invalid G, property and assumed-material envelope rejection |

The [source ledger](research/source-ledger.md) records access depth: the AA8015
thermal/contact publication was inspected at abstract depth and supplies no G;
the AA5052 paper supplies force/slip cases but no thermal validation. The
numerical example's `G=1000 W/K` is an arbitrary labelled synthetic input,
not an aluminium or plant recommendation. The new result fields report G,
representative temperature difference, P1 residual and representative contact entropy
diagnostic; they do not claim thermodynamic admissibility for unmodelled film,
cooling or plastic internal energy.

Calibration would need known alloy/temper and prior history; independent
heat capacities; emissivity-qualified entry/exit strip and roll surface/bulk
temperatures; contact area and residence; effective roll thermal geometry;
coolant/lubricant circuit flows and supply/return temperatures; synchronized
mechanical force, torque, speeds, tensions and gauges; and held-out coils.
Temporal substep convergence is numerical evidence only. Spatial conduction,
advection, film dissipation and thermal feedback each require a separate model
and observations.

## I01 supported domain: unchanged closure, conservative rejection

`MONOTONE_CAPACITY_V1` keeps P1–P3 unchanged and admits only

```
G/2 <= C_s,min = m_dot * min(cp_strip)          [W/K]
G/2 <= C_r,min = (m_roll/delta_t) * min(cp_roll) [W/K].
```

The minima cover each entire supplied piecewise-linear curve. These sufficient
bounds apply with or without sources; they are not necessary bounds or measured
operating limits. Even equal-temperature or balanced-capacity cases outside
this deliberately small domain reject. Zero G remains supported subject to
finite positive capacity rates, property ranges and the existing energy gates.
There is no temperature clipping, conductance rescaling or automatic substepping.
Reducing duration can repair the roll inequality, but cannot repair the stream
inequality, whose capacity is a rate independent of duration.

To see why the bounds account for sources, define positive secant capacities
`C_s=m_dot*Delta H_s/Delta T_s` and `C_r=(m_roll/delta_t)*Delta H_r/Delta T_r`
(use the local cp limit at zero temperature change). Both exceed their minima.
Writing `g=G/2`, P1–P3 give

```
[ C_s+g   -g   ] T_out = [ C_s-g    g   ] T_in + [ S_s ]
[  -g   C_r+g ]         [   g    C_r-g ]        [ S_r ].
```

The left matrix M has positive determinant and nonnegative inverse; the right
matrix N has nonnegative entries under the guard. `M^-1 N` has row sums one.
Thus the source-free part is a convex combination of inlet temperatures.
`M^-1 diag(C_s,C_r)` also has nonnegative entries and row sums one, so each
source increment lies between `S_s/C_s` and `S_r/C_r`. A conservative enclosure is

```
min(T_in) + min(0,S_s/C_s,min,S_r/C_r,min) <= each T_out
 each T_out <= max(T_in) + max(0,S_s/C_s,min,S_r/C_r,min).
```

The implementation checks this enclosure after solving, allowing only
`1e-9 K + 1e-12*max(abs(T_out),1 K)` roundoff. Property and mechanical envelopes
still apply independently without extrapolation, including unequal cp domains.
Heating may legitimately exceed the inlet maximum and cooling may fall below
the inlet minimum. The guard does not qualify supplied heating/cooling physics.

### Entropy contract and compatibility

`contact_entropy_production_w_k` keeps its historical numerical meaning:
`Q*(1/T_s,mid-1/T_r,mid)`. The additive `contact_entropy_scope` explicitly labels
it `REPRESENTATIVE_CONTACT_TEMPERATURES_ONLY`. It cannot establish whole-step
admissibility: the original temporal counterexample conserved energy and had a
positive representative diagnostic but negative whole-step entropy. The stream
counterexample even had positive whole-step entropy while overshooting the
hot inlet. Both temperature and entropy checks are required.

Only when plastic heat, slip dissipation and both cooling exports are individually
zero does `pure_exchange_entropy_rate_w_k` report
`m_dot*integral(cp_s/T)dT + (m_roll/delta_t)*integral(cp_r/T)dT`.
This is the whole-interval entropy rate of the represented thermal subsystem,
labelled `PURE_EXCHANGE_THERMAL_SUBSYSTEM`; it excludes any nonthermal work
allocation. The exact piecewise-linear integral uses stable `log1p` arithmetic.
Negative entropy beyond `(1e-8 J/K)/delta_t + 1e-10*sum(abs(entropy rates))`
rejects. These are numerical tolerances, not experimental error budgets.
With any thermal sources or exports, the field is null and
`entropy_balance_scope=INCOMPLETE_WITH_SOURCES_OR_EXPORTS`, even if net powers
cancel. Cooling transfer temperatures and nonthermal entropy closures are absent.

The ordinary passive demo retains every historical field/value and adds four
metadata/diagnostic fields. Historical artifacts are not overwritten. The
prescribed demo remains byte-identical; the standalone closed two-capacity
`thermal.step` is unchanged. This is a bounded numerical admissibility increment,
not a new contact model, resolved field, material law or thermal calibration.
