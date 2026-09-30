# Specialist mechanics and dimensional audit — reviewed v0.3 candidate

This audit reviews executable code, not aluminium predictive accuracy. The earlier
candidate remains at `ec3e79f60c234f374aa924f32d03faf2a7074fc6` on
`review/v03-before-mechanics-audit`; v0.2.1 remains at `3d349418`. Corrections and
literature work were published at `09d0d5b2` on `development/aa5052-mechanics-review`.
The subsequent optional local contact/material increment is on
`development/contact-hardening-increment`, pending review; see
[its equations and evidence](contact-increment.md).

## Actual findings and corrections

| Finding | Review verdict and code correction | Independent/adversarial evidence |
|---|---|---|
| Slab full-thickness ODE and entry/exit sign | Correct within leading-order, constant-yield, projected-contact assumptions; derivation below | RK4 agrees with a separately coded exponential-midpoint pressure integrator; boundary-tension perturbation and grid refinement |
| Grid-node neutral point | **Defect fixed:** strict sign-change detection missed an exact zero at a grid node | `_neutral_location` test covers nodal root, boundary root, multiple roots, no root |
| Work/torque consistency | **Missing diagnostic fixed:** integrate signed traction work and slip dissipation; check roll work + tension work = plastic work + slip dissipation | Force/torque comparison to independent integrator; work residual decreases with refinement; width/speed dimensional scaling |
| Numerical validity | **Missing gate fixed:** coarse/fine force, capacity-scaled torque, absolute slip and work-residual criteria; unchecked search grids explicitly flagged | Default checked solve, small-draft limit, selected optimiser re-evaluation on 512/1024 cells |
| Coulomb shear beyond yield | **Missing rejection fixed:** reject `mu*q > Kps/2`; no silent cap or invented sticking law | High-friction thin-strip adversarial rejection |
| Unassisted bite screen used for established rolling | **Scope fixed:** preserve default threading screen but provide named `established` diagnostic mode with the failed screen recorded | First published pass executes without changing reported friction; result does not certify threading |
| Power-law mean at nearly equal strains | **Cancellation fixed:** use `expm1/log1p` evaluation | Vanishing-interval limit against point stress |
| Initial strength hidden by pass-average hardening | **Missing rejection fixed:** boundary tension must be below local assumed entry/exit uniaxial strengths | Zero-prior, zero-offset Hollomon with positive tension rejects even if the pass mean is positive |
| Thermal row-wise explicit bound | **Weak bound fixed:** it admitted an undamped temperature swap for equal capacities; now enforce non-oscillatory modal step bound | Unequal-capacity exact closed-body exchange, energy conservation/refinement; temperature-swap and overflow rejection |
| Negative tiny slip power | **Clipping removed:** reject negative dissipative work rather than zeroing it | Negative-sliding-work test at a tiny magnitude |
| Profile center at array midpoint | **Defect fixed:** interpolate at geometric width midpoint | Nonuniform-grid linear wedge has zero crown |
| Profile RMS depends on sample density | **Defect fixed:** integrate piecewise-linear membrane mismatch across physical width | Knot-insertion/nonuniform-grid invariance; analytic linear-field RMS |
| Constant curvature hidden by zero range | **Diagnostic added:** report mean and maximum absolute curvature separately from range | Nonzero constant curvature remains visible |
| Scattered source-unit interpretations | **Import boundary added:** `units.py`, dimensional type and scope metadata, original/converted values | 49 raw→SI values, explicit factor-1000/1e6, Celsius/delta, rpm/time, pressure/line-load and heat-unit tests |

These checks establish implementation consistency. They do not establish material
parameters, coefficient calibration ranges, measurement uncertainty or mill capacity.

## Mechanics conventions and work identity

`slab.py` uses `x=0` at entry and `x=L` at exit, full strip thickness `h`, width `b`,
roll radius `R`, compressive contact-pressure approximation `q>0`, tensile boundary
stresses `t0,t1`, and constant plane-strain stress difference `Kps=2Y/sqrt(3)` from
an **assumed isotropic von Mises uniaxial flow stress** `Y`. Strip longitudinal
stress is `sigma_x=Kps-q`. There is no plane-stress roll-bite assumption.

The leading-order slab equation is

```
h dq/dx = Kps dh/dx + 2 tau
q(0)=Kps-t0, q(L)=Kps-t1
tau=+mu*q before neutral, tau=-mu*q after neutral
```

It corresponds to the full-thickness form of the leading-order pressure relation
in Erfanian et al., *Through-thickness modelling of metal rolling using
multiple-scales asymptotics*, European Journal of Mechanics A/Solids 113 (2025),
105712, [journal DOI](https://doi.org/10.1016/j.euromechsol.2025.105712).
The equation-number references here are specifically [equations 21–28 of the
2024 preprint v1](https://arxiv.org/html/2408.01347v1); journal numbering has not
been substituted. The journal lineage is confirmed by [arXiv metadata](https://arxiv.org/abs/2408.01347)
and the author university record linked in `contact-increment.md`.
Their higher-order through-thickness solution is not implemented. That paper's
rigid perfectly plastic assumptions do not validate hardening or elastic-gap models.

The neutral point is the unique interior pressure-branch intersection. At it,
`U=Q/(b*h_neutral)` for the model's projected surface speed and incompressible
`Q=b*h*v`. The force is `F=b*integral(q dx)`; do not double it because there are
 two rolls. Signed torque on **one** work roll is
`M=R*b*integral(tau dx)`. Both driven rolls supply `P_roll=2*M*U/R`.

The same approximation gives

```
P_plastic = Q*Kps*ln(h0/h1)
P_tension = Q*(t1-t0)
P_slip = 2*b*integral[tau*(U-v) dx] >= 0
P_strip_traction = 2*b*integral(tau*v dx)
P_roll + P_tension - P_plastic - P_slip = 0
```

The last identity follows by multiplying the ODE by `Q/h` and integrating:
`P_strip_traction=P_plastic-P_tension`. The code integrates the two traction
regions separately, including a split neutral cell; it does not set torque to
`F*L/2`. Neutral pressure matching is a construction, **not** an independent
convergence test; work and coarse/fine changes provide additional diagnostics.

This is a small-angle **projected** contact model. Circular sagitta is evaluated
stably, but finite-angle tangent velocity, arc-length torque corrections, vertical
friction contributions and the coupled shear/normal yield field are omitted.
The shear-yield screen is necessary, not proof of exact local yield admissibility.
The default retains constant strength and rigid contact. The optional increment
now retains `h*dKps/dx` by integrating `z=q-Kps`, and couples a circular
Hitchcock contact radius to force; see [M1–M7](contact-increment.md). No sticking
zone, noncircular contact, springback or strip elastic recovery is solved.
The original default still uses one exact interval-mean flow stress per pass.
Foil and other original geometric exclusions remain.

Numerical acceptance requires coarse/fine relative force change ≤1e-4, torque
change divided by Coulomb torque capacity ≤1e-4, absolute slip change ≤1e-6,
and relative mechanical-work residual ≤1e-4. They are numerical tolerances, not
accuracy claims. Failed convergence is returned with a flag; the study refuses
unconverged final results. A regenerative signed torque would remain signed,
not be clipped or sold as a drive-feasibility result.

## Material and thermal states

The hardening module retains alloy, declared temper/history, accumulated equivalent
plastic strain and supplied temperature. Its demo law is `sigma0+C*epsilon_eq^n`.
A zero-offset Hollomon law is now allowed, but cannot carry a positive entry tension
at zero prior strain. The homogeneous plane-strain increment is
`(2/sqrt(3))*ln(h0/h1)`; it excludes redundant shear, elasticity and microstructure
kinetics. History and scalar temperature are carried explicitly; no anneal reset,
recovery, grain size, texture, precipitation or fracture is inferred. The source
AA5052 bridge uses **zero offset**, not an invented initial yield.

The thermal module describes two prescribed **material masses/capacities**, not
an Eulerian rolling control volume with inlet/outlet enthalpy. A flowing thermal
control volume would additionally require advective terms. It separately budgets:
plastic volumetric heating [W/m3], solid-interface slip heating [W/m2], interface
transfer `Gcontact*(Troll-Tstrip)` [W], body cooling [W], and capacity changes [J].
There is no heat source from normal pressure or motor power alone. Zero solid
slip gives zero solid-slip heat; unresolved lubricant pressure flow might still
dissipate and is explicitly absent. Heat fractions and contact/cooling coefficients
are supplied; their calibration ranges are unknown. A fitted effective contact
law cannot be combined with explicit slip heating.

For capacities `Cs,Cr` [J/K], contact conductance `G` [W/K], and cooling conductances
`Gs,Gr`, set `a=(G+Gs)/Cs`, `d=(G+Gr)/Cr`. The largest positive decay eigenvalue is

```
lambda_max = [a+d+sqrt((a-d)^2+4*G^2/(Cs*Cr))]/2
```

The revised explicit step requires `dt*lambda_max<=1`. This is stricter than mere
non-amplification: it prevents a sign-alternating thermal exchange mode. Tests
compare the unequal-capacity closed system with its exponential exact solution,
retain total energy, and demonstrate refinement. No temperature field, thermal
crown, coolant HTC calibration or aluminium temperature validation is claimed.

## Source-unit and reference gate

`physicroll/units.py` centralises the accepted spellings and dimensions. Original
source values/units, SI values/units, dimension, scope/convention, source and location
are retained in `artifacts/aa5052/values_long.csv`. Decimal table conversions precede
binary SI storage. Unknown spellings and incompatible quantities reject; no generic
string guessing is used. Display conversions occur only at report boundaries.

| Actual source trap | Treatment |
|---|---|
| mm, MPa, kN, g/cm3, percent | Convert to m, Pa, N, kg/m3 and dimensionless fraction. In particular 2.68 g/cm3 = **2680 kg/m3**, not the generic demo's 2700. |
| Table radius vs Eq6 diameter wording | Preserve Table1's 210.81 mm radius interpretation; separately test half-radius prose interpretation. Contradiction remains unresolved. |
| Speed m/s location | Resolved mapping remains null. CLI requires an explicit what-if interpretation; roll/entry/exit alternatives are run. Throughput and rpm are not claimed observed. |
| Tension stress vs force | Source MPa is tensile stress; entry/exit forces use their own local thickness. 9.47 MPa yields 52,804.72 N entry versus 37,380.59008 N exit in pass1. |
| Source `p` collision | Eq4 pressure [Pa] differs from Eq6 force per width [N/m]. Hitchcock's dimensionless correction uses `F/(b*E*draft)`; the optional `contact.py` now uses this dimensionally correct circular closure; it remains uncalibrated. |
| Source Eqs7–8 `ln(dh/h)` | Unsafe literal differential/work convention: not implemented. Our work identity is derived above. Eq8 is per-width power [W/m], not total power or heat flux. |
| Source Eq9 | `tau*length*slip` is W/m. Multiply by width and count each physical interface once; signed traction must pair with signed relative slip. |
| Source Eq4 shear cap branches | Printed pressure comparison and overlapping adhesive branches are ambiguous. We do not transcribe/repair them silently; unsupported shear is rejected. |
| Printed error percentages | Original source values retained as %, internal values as fractions. Pass3 slip printed −4.84% differs from recomputed −4.84581498%; cause unknown. |
| Celsius and differences | Absolute degC uses +273.15; delta_degC does not. No source temperatures exist in this case. |
| kN*m/N*m, rpm/rad/s, min/s | Central conversions tested; none of these were observed in the three-pass source. |
| Engineering/log/equivalent strain | Reduction `1-h/H`, log `ln(H/h)`, and homogeneous equivalent increment remain distinct. No strain rate is inferred from a pass total. |
| K and n | K=276.5 MPa, n=0.26: reported units known; stress/strain pairing and calibration ranges unknown. No coefficient conversion without an explicit interpretation. |

Shao, Sun, He and Li (2015), [original paper and tables](https://www.iieta.org/journals/ijht/paper/10.18280/ijht.330113),
provide the numerical case. Original PDF references were rechecked: reference 18
is Rihan and Abd El-Bary's Al-Si continuous-casting study, rather than an identified
AA5052 flow-curve dataset. References 12–15 include hot-roll/hot-steel thermal work;
those citations do not resolve missing history coefficient `a` or aluminium contact
calibration. No empirical thermal coefficients were taken from them. Reference 17
is a rolling-model textbook; its formula is not used here to bypass the numerical
neutral solution. Thus exact source-model reproduction is rejected as a claim.

The [Hulamin 5052 data sheet](https://www.hulamin.com/sites/default/files/downloads/5052%20Data%20Sheet.pdf)
supports generic alloy density and appliance/sheet-metal application categories.
Its temper-specific strength and bending data are **not** used to certify this
unspecified benchmark stock. The proposed 1.72 mm cut-to-length end use is an
analyst application choice, not the paper's stated end use.

## Subsequent optional mechanics increment

[Contact increment](contact-increment.md) gives the variable-strength equilibrium,
nominal-shaft versus contact-radius distinction, circular fixed-point solution,
local hardening state and explicit validity gates. [Report-sync packet](report-sync-contact-increment.md)
records all new measured-force/slip comparisons, including worsened residuals.
The fine-grid run exposed and fixed a one-ULP entry-sagitta boundary defect; the
exact prescribed entry thickness is now returned at the boundary. The
[append-only log](mechanics-change-log.md) ties this finding and all optional
changes to equations, code, tests and retained runs. Numerical verification and
experimental validation are distinct throughout.
