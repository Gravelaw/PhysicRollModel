# PhysicRollModel research report update

**2 October 2026 · addendum to _Aluminium cold rolling models for
PhysicRollModel_, 30 September 2026, 49 pages**

**Code baseline:** reviewed `main` commit
`fbafee54bb8f22554904166c9653d75915051359`. This addendum records what
changed since the report. The original literature discussion and its 105
numbered source entries remain the long-form research record; the attached
Word/PDF has not been silently treated as an editable repository file.

## Executive correction

The report's pages 1, 17 and 35 describe the project as a generic v0.2
illustration and place a tension-aware bite solver, material-history handling
and heat accounting wholly in the future. The reviewed repository now contains
an **optional** tension-aware small-slope slab solution, optional spatial
hardening, optional coupled circular Hitchcock contact, and a separate
prescribed-boundary flowing-strip/roll energy handoff. The original heuristic
`solve()` path remains. The reported AA5052 study is a conditional three-pass
comparison; the later generic heat demonstration uses synthetic properties.
Neither is an identified production model. No measured aluminium thermal,
plant-gauge, profile, flatness, residual-stress or control validation has been
established. [Capability boundary](../capabilities.md) and
[verification record](../verification.md) provide the current scope.

## Replace these report status statements

**Page 1 — current status.** The reviewed code implements an optional,
numerically checked, tension-aware slab bite with signed traction, force,
torque, neutral point, forward slip and mechanical work diagnostics. Optional
spatial hardening and circular flattening are checked structural hypotheses.
No plant-calibrated solver or delivered-gauge closure is claimed.

**Page 5 — pressure and torque.** The projected pressure and signed-traction
law is implemented in `physicroll/slab.py`. Its local shear screen does not
constitute a resolved sticking zone, elastic entry/exit field or film model.
Physical shaft radius and effective contact radius remain distinct.

**Page 6 — flattening and gauge.** Circular Hitchcock force-radius iteration
exists in `physicroll/contact.py`, with explicit convergence and radius-envelope
gates. A measured stand-spring/loaded-gap/recovered-gauge solution still does
not exist. A fitted full stand compliance must not overlap the roll correction.

**Pages 6 and 17 — material and integration.** `MaterialState` carries
declared alloy, temper, equivalent strain, temperature and pass history;
optional `BiteHardening` varies assumed strength through a homogeneous
plane-strain path. The AA5052 bridge retains unresolved initial strain,
stress/strain convention, radius and speed-location assumptions. It is not an
identified constitutive card.

**Pages 10, 24–27 and 35 — heat.** `physicroll/energy_handoff.py` now computes
a conservative flowing-strip enthalpy and finite aggregate-roll sensible-energy
ledger from **supplied** heat fractions, heat-capacity curves, contact power
and cooling power. It does not solve a temperature field, heat-transfer
coefficient, oil film, thermal crown or thermal feedback into rolling force.

**Page 17 — repository inspection.** Repository files, tests and recorded
artifacts have now been inspected. The report's “No repository inspection or
live-project edit” statement described the earlier writing state.

**Pages 35–36 — validation gates.** Numerical conservation/refinement and
fault tests have been run. Independent aluminium measurements, calibrated
thermal boundaries, measured roll/stand geometry and held-out coils remain
necessary before predictive or operational claims.

The research sections on FE, lubrication, metallurgy, crown, fracture, released
shape, instrumentation and visual design remain **proposed research and design
options**. Nothing in the optional slab or energy handoff implements them.

## Implemented equations and source boundary

The report's page 3 convention uses full strip thickness `h` [m], width `b`
[m], rolling coordinate `x` from entry to exit, positive longitudinal tension
and positive compressive contact pressure. Repository code calls that pressure
`q` and the signed strip traction `tau`; keep this notation translation explicit
when comparing with the report's `p` and `q`. Uniaxial equivalent flow stress
`Y` and plane-strain stress difference `Kps=2Y/sqrt(3)` are in Pa. `F` is total
stand separating force [N]. Torque below is per roll [N m].

The optional projected equilibrium and material path are:

```text
h*dq/dx = h*dKps/dx + Kps*dh/dx + 2*tau               [M1]
z = q-Kps = -sigma_x
dz/dx = (Kps*dh/dx + 2*tau)/h                           [M2]
eps_eq(x) = eps_eq,in + 2/sqrt(3)*ln(h_in/h(x))          [M3]
Y(eps_eq) = sigma0 + C*eps_eq**n                         [M4]
tau = +mu*q before neutral; tau = -mu*q after neutral
```

`h*dq/dx`, `h*dKps/dx`, `Kps*dh/dx` and `2*tau` are Pa.
`dz/dx` is Pa/m. `mu`, `n` and `eps_eq` are dimensionless;
`sigma0`, `C`, `Y`, `q` and `tau` are Pa. The variable-strength derivative is
accounted for through `z`; merely inserting a varying `Kps` into a
constant-strength pressure equation would omit it. This is a derived projected
slab extension, not a copied aluminium-calibrated law. The multiple-scales
paper's equation numbers 21–28 refer to its
[2024 preprint v1](https://arxiv.org/html/2408.01347v1); its
[2025 journal version](https://doi.org/10.1016/j.euromechsol.2025.105712)
is the publication lineage. Journal equation numbering has not been equated
with the preprint. Details, boundary conditions and tests are in
[contact-increment.md](../contact-increment.md).

The optional circular contact closure is:

```text
Rc = R*[1 + 16*(1-nu_roll**2)*F/(pi*E_roll*b*delta_h)]  [M5]
F = b*integral(q dx)
M_one_roll = R*b*integral(tau dx)                       [M6]
P_roll + P_tension - P_plastic - P_solid_slip = 0       [M7]
```

`R`, `Rc`, `delta_h` are metres; `E_roll` is Pa and the M5 bracket is
dimensionless. `M_one_roll` uses the **physical** shaft radius `R`; `Rc` shapes
the approximate contact. M7 is in W and checks the model's projected
mechanical-work account. M5 follows
[Li, Matsumoto & Utsunomiya (2018), Eq. 1](https://doi.org/10.2355/isijinternational.ISIJINT-2017-623).
That stainless-steel experiment shows limits of circular geometry; it does not
validate the AA5052 material, contact shape or predicted slip. Zero draft,
noncircular foil contact and finite sticking remain outside this closure.

The optional first-law handoff uses `H(T)=integral c_p(T)dT` [J/kg]:

```text
m_dot*[H_strip(T_out)-H_strip(T_in)]
  = beta*P_plastic + f_strip*P_solid_slip
    + Q_contact - Q_cool_strip                         [E1]

m_roll*[H_roll(T_roll,out)-H_roll(T_roll,in)]/delta_t
  = (1-f_strip)*P_solid_slip - Q_contact - Q_cool_roll  [E2]

P_unconverted_plastic = (1-beta)*P_plastic              [E3]
P_plastic + P_solid_slip
  = strip_enthalpy_gain_rate + roll_storage_rate
    + P_unconverted_plastic + Q_cool_strip + Q_cool_roll [E4]
```

`m_dot` is flowing-strip mass rate [kg/s], `m_roll` is aggregate effective
roll mass [kg], `delta_t` is seconds, `c_p` is J/(kg K), and every `P` or
`Q` term is W. `P_solid_slip` already covers **both** interfaces. Positive
`Q_contact` enters the strip and leaves the roll. `beta` and `f_strip` are
supplied dimensionless fractions, not universal aluminium constants.
`P_unconverted_plastic` is a bookkeeping allocation, not a measured
microstructural energy state. The mechanically checked work residual remains
separate from the combined first-law residual. Source, tests and all additional
limitations are in [energy-handoff.md](../energy-handoff.md) and its
[specialist audit](../energy-specialist-audit.md).

## Evidence and interpretation

At the reviewed main commit, the recorded suite passed **67 tests**, including
13 energy-specific tests. This is **numerical verification** of the declared
equations and guards, not aluminium or plant validation. The same-environment
review fixed heat-capacity endpoint, source-metadata and outlet-temperature
guard defects before that result. See
[`artifacts/flowing_energy_tests.txt`](../../artifacts/flowing_energy_tests.txt)
and [energy specialist audit](../energy-specialist-audit.md).

The fixed-gauge AA5052 study has three author-reported measured forces and
forward slips from Shao et al. (2015),
[DOI 10.18280/ijht.330113](https://doi.org/10.18280/ijht.330113),
Tables 1–2. Under a declared conditional bridge, the rigid pass-mean baseline
has mean absolute **relative** force/slip residuals of 6.738%/41.960%; rigid
spatial hardening gives 4.628%/34.526%; circular mean gives 8.066%/53.042%; and
circular spatial gives 7.945%/44.802%. Pass 3 force worsens under rigid spatial
hardening, and circular flattening worsens aggregate comparison residuals for
that assumption set. Sensitivities to prior strain, strength interpretation,
radius, friction and speed leave the residual sign unidentifiable across sampled
cases. These are comparison residuals, **not fitted accuracy**, independent
holdout results or a basis for plant settings. The source provides no measured
torque or thermal boundary for validation. Exact inputs and each pass are in
[the contact comparison packet](../report-sync-contact-increment.md) and
[`artifacts/contact_increment/`](../../artifacts/contact_increment/).

The two-pass flowing-energy example uses a generic synthetic aluminium-like
material, supplied heat capacities, partitions, effective roll mass, contact
and cooling powers. Its temperatures are a conservation demonstration. Fluid
identity is recorded but changes no friction, heat fraction or cooling law.
No `c_p`, heat partition or contact coefficient was imported from the
[AA8015 FE study](https://doi.org/10.1007/s00170-018-2811-2); only its
thermal/contact research topic is cited, with primary abstract access.

## Remaining decision gates

1. Identify alloy/temper, initial history, roll radius convention, speed
   location and stand compliance from source measurements. Do not hide these
   ambiguities in an effective friction fit.
2. Obtain synchronized gauge, width, force, **per-roll** torque, roll and
   strip speed, tension, temperature and lubricant/cooling measurements with
   instrument quality and material-coordinate alignment.
3. Validate force, torque, slip and delivered gauge on independent aluminium
   coils, then separately validate strip and roll temperatures before adding
   thermal feedback. Current synthetic heat fractions and assumed ranges are
   not calibration uncertainty distributions.
4. Treat profile, flatness, residual stress, fracture, metallurgy, levelling,
   thermal crown and controllers as separate models with their own measurements
   and numerical convergence targets. Preserve the original report's source
   depth labels and visual inspiration as context, not evidence of a build.

The [source ledger](source-ledger.md) distinguishes DOI/publisher metadata,
full-text equation access, abstract-only leads and code-derived equations.
No full third-party paper, book, brochure or image is included in this update.
