# Optional contact and material mechanics increment

This local increment starts from published reviewed commit
`09d0d5b2e754ddcc9840e9b2d11fbdb07efd9b89`. Default `solve_slab` and the
literature runner still use rigid contact and pass-mean strength. Optional spatial
hardening and circular elastic flattening are structural hypotheses, not fitted
AA5052 models. Fixed-gauge comparisons and sensitivity results are in
`artifacts/contact_increment`; the older `artifacts/aa5052` evidence is retained.
No wider optimisation or plant-setting recommendation is made in this increment.

## Equations, conventions and scope

`x` runs from entry to exit; `h` is full thickness [m]; tensile longitudinal
stress `sigma_x` and compressive pressure `q` are positive in their named senses.
The plane-strain von Mises stress difference is `Kps=2Y/sqrt(3)` [Pa], with
`Y` a declared uniaxial equivalent flow stress. Neither the benchmark's stress
nor its strain convention is identified by this assumption.

For the projected thin-slab approximation, axial equilibrium is

```
d(h*sigma_x)/dx + q*dh/dx + 2*tau = 0
sigma_x = Kps(x) - q
h*dq/dx = h*dKps/dx + Kps*dh/dx + 2*tau                 [M1]
```

All terms on the last line are Pa. Simply replacing a constant `Kps` in the
old pressure ODE by a varying value would omit `h*dKps/dx`. The optional solver
instead integrates `z=q-Kps=-sigma_x`:

```
dz/dx = (Kps*dh/dx + 2*tau)/h
q = z+Kps; z(entry)=-t_back; z(exit)=-t_front           [M2]
tau = +mu*q before neutral, -mu*q after neutral
```

This avoids differentiation of a fractional power hardening law. Both branches
are integrated and matched at their unique interior intersection. Boundary,
nonunique and absent neutral roots reject. Coulomb shear above the local
`Kps(x)/2` rejects; it is not silently capped into an unimplemented sticking law.
The shear screen is necessary within this approximation, not a complete local
yield-field proof. Zero draft and zero friction do not determine the assumed
interior-neutral rolling solution and reject explicitly.

The optional homogeneous strain path is

```
eps_eq(x) = eps_eq_in + 2/sqrt(3)*ln(h_in/h(x))        [M3]
Y(eps_eq) = sigma0 + C*eps_eq**n                       [M4]
```

`eps_eq,n` are dimensionless; `sigma0,C,Y` are Pa. Redundant shear, elastic strain,
rate effects, temperature feedback and recovery are omitted. `BiteHardening`
preserves alloy, declared temper, temperature and accumulated history across
passes; the interval mean in plastic work is the exact integral of M4. The generic
law permits an offset; the **AA5052 bridge retains sigma0=0**, source K/n, and
explicit log/equivalent and uniaxial/stress-difference interpretations. No initial
yield is invented. Its initial log strain 0.05 is assumed. The optional example's
293.15 K and envelopes `eps_eq in [0,3]`, `T in [273.15,373.15] K` are declared
analyst boundaries, not calibration ranges or measured temperatures. Unknown
calibration ranges remain null. No grain size, texture, precipitation or final
certified temper is inferred from scalar strain.

Nominal physical shaft radius `R` differs from circular contact radius `Rc`:

```
Rc = R*[1 + C_H*F/(b*delta_h)]                        [M5]
C_H = 16*(1-nu_roll**2)/(pi*E_roll)                   [Pa^-1]
```

`F` is the total stand separating force [N], not a pressure, double roll load,
or a force already divided by width. `b*delta_h` is m2, so the bracket is
unitless. The exact circular projected contact length used by the code is
`sqrt(Rc*delta_h-delta_h**2/4)`. The source equation is the Hitchcock circular
approximation reproduced in Li et al. (2018), Eq.1, not a new inferred elastic
law. The source's steel experiment also documents departures from that shape.

`solve_circular_contact` uses a damped fixed point, default relaxation 0.5,
maximum 80 iterations, and relative closure residual
`abs(Rc_target-Rc)/R <= 1e-8`. Each returned checked pressure solution must also
pass the existing mesh/work gates. Nonconvergence is returned with false status
and a flag. Radius growth beyond a supplied maximum (default `Rc/R=1.5`), invalid
SI modulus, or unsupported pressure/shear domain rejects. The radius ceiling is
an analyst guard, **not a measured transition or universal validity boundary**.
Uniqueness of the fixed point is not established generally; an independent
bracketed root agrees for the numerical test. The optional benchmark uses assumed
roll `E=210 GPa, nu=0.3`; 180 and 230 GPa are sensitivity assumptions. This is not
identification of the source mill's elastic properties.

In this projected model, constant surface speed and torque use the nominal shaft:

```
Q = b*h*v; U = Q/(b*h_neutral); omega=U/R
F = b*integral(q dx)
M_one_roll = R*b*integral(tau dx)                     [M6]
f = (v_exit-U)/U = h_neutral/h_exit - 1
P_roll = 2*M_one_roll*omega
P_plastic = Q*integral(Y d eps_eq)
P_slip = 2*b*integral[tau*(U-v) dx] >= 0
P_tension = Q*(t_front-t_back)
P_roll+P_tension-P_plastic-P_slip = 0                 [M7]
```

`M` is N m, `omega` rad/s, `Q` m3/s; all powers are W. Interface integration counts
both surfaces once and preserves signed torque, including regenerative examples.
`P_plastic` here is plastic mechanical work, not a prescribed heat fraction.
Using `Rc` as the shaft lever arm or inferring rpm from an unresolved measured
speed would introduce a convention error. Elastic surface velocity variation,
finite-angle arc/normal-traction corrections, elastic energy/hysteresis, strip
springback and noncircular contact remain absent. Thus the work identity verifies
the projected closure, not the energy of a complete elastic continuum.
The prescribed exit thickness is the loaded plastic-zone exit gap in this model;
identifying it with reported downstream gauge is a conditional no-recovery
assumption. No mill modulus is coupled, so roll compliance is not counted again
inside a stand-spring closure.

## Source-to-equation-to-code-to-test map

| Equations / idea | Original source and interpretation | Code | Independent numerical evidence |
|---|---|---|---|
| M1–M2, constant-strength slab limit | Erfanian, Brambley, Flanagan, O'Kiely & O'Connor, **2025**, *Through-thickness modelling of metal rolling using multiple-scales asymptotics*, European Journal of Mechanics A/Solids **113**, 105712, [journal DOI](https://doi.org/10.1016/j.euromechsol.2025.105712). Earlier [2024 preprint v1 Eqs21–28](https://arxiv.org/html/2408.01347v1) are the equation-number references actually consulted. M1 for variable K is the equilibrium derivation above, not a claimed equation from that perfectly plastic paper. | `slab.py::_solve_grid` | Constant-law equivalence, separately coded exponential-midpoint integration of variable-strength pressure, work/refinement and signed tension tests |
| M3–M4, material interpretation | Homogeneous incompressible plane-strain kinematics plus declared isotropic power-law assumption. Shao, Sun, He & Li (2015), *Research on the Thermal Calculaion Model of High Strength Aluminum Strip Rolling Based on Finite Diffreence Method* (title spelling as published), [DOI 10.18280/ijht.330113](https://doi.org/10.18280/ijht.330113), Eq2 reports K/n, but Eq3 history coefficient and prior state are missing; stress/strain pairing and material reference provenance remain unresolved. Additive history is our assumption, not a reproduction of Eq3. | `materials.py::BiteHardening`, `literature.py::simulate_schedule` | Exact interval plastic work, continued state across passes, local-strength and range rejection |
| M5, circular flattening | Ling Li, Ryo Matsumoto & Hiroshi Utsunomiya (2018), *Experimental Study of Roll Flattening in Cold Rolling Process*, ISIJ International **58**, 714–720, [DOI 10.2355/isijinternational.ISIJINT-2017-623](https://doi.org/10.2355/isijinternational.ISIJINT-2017-623), Eq1. Stainless steel analogue; no aluminium validation or transfer of its fitted strip law. | `contact.py::CircularRollElasticity`, `solve_circular_contact` | Zero-force identity, units/width invariance, large-E limit, independent bracketed root, rejected radius envelope and failed iteration |
| M6–M7, neutral/speed/torque/work | Derived from M1–M2 using the same projected velocity and traction assumptions; no unexplained `F*L/2`. Published measured slip normalization is unresolved. | `slab.py`, explicit speed mapping in `literature.py` | Width/speed scaling, signed regenerative torque, power identity, invariant mechanics under alternative speed interpretations |
| Citation lineage | [arXiv journal-reference metadata](https://arxiv.org/abs/2408.01347), [author university record](https://pure.ul.ie/en/publications/through-thickness-modelling-of-metal-rolling-using-multiple-scale/) and parent-verified [published PDF](https://wrap.warwick.ac.uk/191529/2/1-s2.0-S0997753825001469-main.pdf) identify the journal publication. | Documentation and docstrings | Bibliographic check only; journal equation numbering has **not** been substituted for preprint numbering |

Citations motivate equations and delimit applicability. They do not validate our
implementation against aluminium experiments. The 54-test suite verifies numerical
and dimensional behavior; the three author-reported force/slip pairs are a conditional
comparison without raw traces, uncertainty, independently held-out coils or torque.

## Reproduce and interpret

```
python -m unittest discover -s tests -v
python scripts/run_contact_increment.py --cells 512 --out artifacts/contact_increment
```

`before_after.csv` contains each pass's predicted force/slip, author-reported
measurements, signed residuals and separately labelled source-model outputs.
`structural_comparisons.json` retains all equations' numerical outputs for four
structures. `hypotheses.json` retains both successful runs and rejected assumptions;
`summary.json` contains the comparison, refinement and sampled envelope.
`unit_audit.json` carries the same 49 source-value conversions and 36 derived
quantities; `reproducibility.json` fingerprints inputs and solver sources, and
`checksums.json` covers the run files. A failed main structural comparison is saved
before the runner raises. Old reviewed results remain in their original directory.

See [report-sync packet](report-sync-contact-increment.md) for the actual run
numbers and [append-only findings log](mechanics-change-log.md) for failure history.
No sample envelope has probability coverage. Speed interpretation cannot be inferred
from force/slip in a rate-independent model: predicted throughput and power change,
while dimensionless slip and load do not. Force-only calibration confounds flow
strength, friction and contact compliance. Unknown prior state, stress convention,
source radius/diameter contradiction and weak K/n provenance persist.

Next evidence gate: synchronized force, torque and explicitly located strip/roll
speeds, local tension and gauge measurements; independently measured flow curves
and history for the alloy/temper; roll elastic geometry and compliance; repeat
coils/campaigns with uncertainty. Fit only identifiable shared parameters on training
coils, retain entire coils/campaigns for held-out tests, and keep structural
alternatives visible. Three connected passes do not supply such a split. Thermal,
profile/flatness and fracture require separate measurements and validation gates.
