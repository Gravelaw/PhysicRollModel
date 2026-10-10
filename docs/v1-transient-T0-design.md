# T0 transient solver design candidate

**Status: design under renewed review for width-resolved structural dynamics;
the restricted prescribed-motion T1 layer and T2A1–T2A8
benchmarks are implemented, while general strain-bearing torque-driven
moving-span/reel T2 and full 3D T3 contact
remain design candidates.** This
develops the [v1 scope amendment](v1-scope-amendment-2026-10-10.md) after an
independent Astra review of primary technical sources. The user requires all
three solver layers and dynamic Blender/USD animation. This document records
the selected scope and the remaining numerical decisions before design freeze.

## Model boundary and staged contracts

The rigid-gap baseline may use a finite strip segment in the
rolling/thickness plane with plane-strain kinematics. The user also requires
cross-width barrel bending and structural vibration in the elastic-roll mode.
That mode's shipped formulation is a bounded three-dimensional transient
strip/contact region coupled to a spatial dynamic roll/stand structure,
including lateral boundary and support conditions. It cannot inherit
plane-strain exclusions or multiply one centerline traction by width to infer
a cross-width pressure/gauge profile. The user requires the shipped
strip/contact engine itself to be full 3D. A reduced multi-slice model may
serve as a separate comparison candidate, but cannot replace the v1 engine.
It omits transverse strip coupling and needs frozen error comparisons against
the 3D transient engine under nonuniform load, edge effects and moving
contact. A Lagrangian material mesh
initially keeps parcel genealogy explicit. Moving-window or ALE transfer is
a later capability with its own conservative remapping checks. Numerical
fields from this 3D model do not by themselves validate flatness, residual
stress or width-spread predictions.

T1 integrates declared strip transport and roll/reel motions, including
material-coordinate identity, reversal, length/mass inventory and winding
radius. Prescribed speed remains labeled as an input. Incompatible feed,
take-up and inventory histories reject. Animation sampling cannot advance
state. T2 adds shaft torques, inertia, gear/loss conventions, longitudinal
span tension and moving material flux. A prescribed-speed mode reports its
required torque as a reaction; torque-driven mode predicts speed. Reels are
open, variable-mass control volumes, so angular momentum and energy balances
must include material crossing their boundaries. Zero tension triggers loss
of the taut-span assumption rather than a fictitious compressive tension.

T3 resolves inertial strip deformation, stress/internal-state transport and
finite-sliding roll contact. The proposed first constitutive law is
isothermal finite-strain associative J2 plasticity with isotropic hardening,
plastic incompressibility and a consistent stress update. Analytically rigid
cylindrical rolls and unilateral Coulomb contact are the proposed first
contact model. Normal complementarity, stick/slip, frictional work,
penetration and contact numerical parameters must be explicit. Isotropic
hardening does not establish cyclic/Bauschinger accuracy. A scalar prior
strain may initialize a labeled, assumed stress-free hardened state; it does
not reconstruct residual stresses or a tensor history. The formulation needs
specialist equation-level review before coding.

T2/T3 exchange conjugate velocity/traction and angular-velocity/torque
quantities at common accepted times. The interface must specify whether a
span or the 2D/3D contact domain owns each portion of mass and compliance.
The dynamic elastic mode also partitions rigid roll/shaft rotation from
deformational roll/stand inertia and energy; no structural mass or support
compliance may be counted twice. Bearings, chocks and stand constraints must
be explicit. Contact transfer must preserve resultant forces, moments and
mechanical work. This partition needs independent impulse/work tests. T4 saves
accepted states and source-run identity for Blender/USD, and does not turn
prescribed histories into predicted fields.

## Initial, boundary and exit-gauge definitions

Every public case must state initial geometry, material state at every
parcel, velocity, roll/reel angular state and inventory, span tension,
contact status and physical start condition. The start may be a free leading
edge fed into rolls or a pre-engaged bite; these are different initial-value
problems. Boundary records declare imposed traction or velocity for each
component, incoming material state, outgoing state retention, gap/roll-center
motion and shaft input. Velocity and traction must not both be imposed on an
unconstrained component. Shaft speed and torque cannot both be independent
inputs.

V1 requires two separately identified modes. The first imposes a rigid-roll-
center gap and predicts strip deformation and downstream unloaded thickness
subject to that geometry and material law. The second includes stand
compliance and deformable elastic rolls, predicting loaded separation and
roll deflection from a declared unloaded setting, stiffness and boundary
model. Each mode must distinguish prescribed unloaded geometric gap, loaded
roll separation, in-contact thickness and downstream thickness at named
cross-width and downstream locations. The user selected roll bending along
the barrel and structural vibration: roll and stand deformation cannot be
quasistatic in the elastic mode. The shipped strip/contact model is full 3D;
its coupling to the dynamic roll/stand structure and any structural modal
reduction must be selected before equations are coded. The existing
effective-radius correction supplies
neither transient compliance nor elastic roll deformation. Both modes need
independent benchmarks; success in the rigid mode cannot certify the elastic
mode.

The compliant model must declare work/backup rolls, journals, bearings,
chocks and stand attachments, including which interfaces transmit moments,
slip or separate. Upper and lower assemblies cannot be constrained to move
symmetrically solely because the nominal pass is symmetric; that would
suppress possible vibration and lift-off modes. Large shaft rotation with
elastic deformation needs objective kinematics and a declared treatment of
spin-dependent inertia and prestress. Roll contact follows the moving
material surface, not merely its visual animation.

## Integration and acceptance

An implicit dynamic generalized-alpha scheme is the first candidate, with
documented numerical dissipation and an undamped verification setting.
Accepted steps require converged nonlinear, contact and T2/T3 interface
residuals. Failed trials retry from unmodified committed state; constitutive
history advances only on acceptance. A separate explicit small-case solver
may cross-check results. Explicit stability must cover wave speed, element
size and contact stiffness; implicit integration still needs time/event
resolution. Physical-time acceptance cases exclude mass scaling and
accelerated loading. Element choice must pass volumetric-locking and
hourglass/artificial-energy checks. Contact loss, capture, reversal and
re-entry are explicit events. Frame interpolation cannot silently cross them.

The independent benchmark pack is frozen before implementation and compares
at least three spatial and temporal resolutions where smooth convergence is
meaningful:

| Stage | Independent reference | Compared quantities |
|---|---|---|
| T1 | Analytic constant/piecewise motion and winding volume | Parcel position, angle, radius, mass, event time |
| T2 | Constant-torque acceleration, torque-free balance, elastic-bar pulse and two-inertia modes | Momentum, work, wave reflection, frequency and phase |
| T2 reel | Separately derived variable-mass control volume | Radius, angular-momentum flux and energy |
| T3 material | Rigid-body objectivity, elastic patch/manufactured wave, independent material-point paths | Stress, hardening, yield, volume and dissipation |
| T3 contact | Elastic line-contact limit, analytical sliding work and bar impact | Pressure, impulse, penetration and friction work |
| T3 compliant mode | Independent stand loading/unloading and finite elastic-roll contact reference | Stand displacement, contact pressure, roll deformation and recovery |
| T3 gap coupling | Separate gap/load calculation and compliance-to-zero limit | Loaded separation, downstream gauge, force and rigid-limit convergence |
| T3 cross-width dynamics | Independent beam/3D roll-stack bending modes and support impulse response | Mode shape, frequency, damping, phase, cross-width contact load and vibration |
| T3 width coupling | Independent width-resolved strip/roll contact reference | Pressure and gauge profiles, transverse work and mesh/time convergence |
| T3 loaded vibration | Preloaded structural frequency, lift-off/re-contact and asymmetric upper/lower motion | Contact events, amplitude, phase and support reactions |
| T3 reduced model | Full 3D reference against increasing retained modes or strip slices | Width-dependent fields, moving-contact work and declared error envelope |
| T2/T3 | Matched monolithic and partitioned elastic test | Interface impulse/work, reflected wave and convergence |
| Rolling limit | Independent steady-domain reference | Force, torque, slip and internal fields |
| Restart | Checkpoint/restart and changed frame cadence | Identical accepted history within tolerance |

Initial *design targets*, not measured results or universal physical limits,
are scaled closed-case mass error below `1e-8`, smooth elastic field error
below `1e-3`, and scaled mechanical energy-balance defect below `1e-3`.
Event-time, penetration and interface-work tolerances need separate frozen
values. These targets may change during T0 review, before production results
are seen. No second-order claim applies across a nonsmooth contact event.

Record strip and reel mass; linear/angular momentum; kinetic, elastic and
hardening energy; boundary work; material flux; friction/plastic dissipation;
and algorithmic dissipation separately. Include elastic-roll and stand
kinetic/stored energy, damping loss and contact dissipation, with no duplicate
roll/shaft inertia. Do not count plastic work as both
stored and dissipated energy. Isothermal mechanics does not predict a
temperature field. Result contracts include model/algorithm identities,
initial fields and parcel maps, prescribed histories and interpolation rules,
accepted times, rejected steps, events, diagnostics and full restart state.
Animation samples are separate from solver steps and are not a restart file.

## Evidence and unresolved choices

[Flanagan et al.](https://arxiv.org/html/2408.03242v1) informs spatial
rolling/contact verification and shows why steady force alone does not prove
steady internal fields. Its implicit branch is static and its explicit cases
minimize transients; it cannot validate this transient solver.
[Erfanian et al.](https://arxiv.org/html/2408.01347v1) supplies a possible
steady limiting comparison only within its own assumptions. Primary
[Patel (2023)](https://doi.org/10.1115/1.4056256) provides architecture
evidence for a dynamic 3D roll-stack coupled to a reduced bite model, not an
independent reference for full transient 3D strip fields. Structural modal
reduction could use [Craig–Bampton substructuring](https://doi.org/10.2514/3.4741),
subject to moving-contact and mode-convergence tests. Primary
[web-handling work](https://apicsllc.com/apics/Ie_cdc01/Ie_cdc01.htm)
informs span/reel coupling but does not validate cold rolling. The proposed
plasticity and integration families are associated with
[Simo (1992)](https://doi.org/10.1016/0045-7825(92)90123-2) and
[Chung and Hulbert (1993)](https://doi.org/10.1115/1.2900803);
publisher access to their full text was restricted during this review, so
equation-level specialist review remains required. Independent verification
can use the [Sandia manufactured-solutions method](https://www.sandia.gov/research/publications/details/code-verification-by-the-method-of-manufactured-solutions-2000-06-01/).
These are design inputs, not empirical qualification evidence.

The user selected bounded transient episodes and both rigid-gap and
stand-compliance/elastic-roll modes for v1. Episode duration, mesh limits and
performance budgets must be frozen before release checks. We will prototype
both a lightweight and a numerical/native dependency route against the same
frozen acceptance cases, then select a supported Linux/Windows wheel route.
This evaluation does not imply that two production engines must ship. The
existing steady workflows retain their lightweight dependency boundary.
Cross-width bending, vibration and a shipped full 3D strip/contact engine are
required. Structural damping identification, the roll/stand coupling scheme
and feasible runtime/mesh budget remain T0 decisions. Freeze episode duration,
mesh sizes, excitation bandwidth, output cadence, memory and runtime ceilings
before comparing lightweight and native prototypes. Compare equivalent
formulations on the same observables so speed differences are not confused
with reduction error. Actual Linux/Windows wheel installation, offline runs,
dependency/license review and numerical agreement are required. The principal
numerical-verification gap is an independent coupled spatial/transient compliant-roll
reference with usable inputs and outputs; steady force agreement cannot close
it.
Synthetic verification can use
declared density, elastic constants, hardening, friction, inertia and span
parameters. Physical validation further needs independently characterized
material/contact data, actual drive/reel/gap parameters and synchronized
transient observations with uncertainty. No scientific or site-use claim
follows from T0–T4 software checks.
