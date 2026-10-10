# T0 transient solver design candidate

**Status: design for review; no transient equations are implemented.** This
develops the [v1 scope amendment](v1-scope-amendment-2026-10-10.md) after an
independent Astra review of primary technical sources. The user requires all
three solver layers and dynamic Blender/USD animation. The decisions at the
end of this document must be settled before this candidate is frozen.

## Model boundary and staged contracts

The candidate T3 domain is a finite strip segment in the rolling/thickness
plane with constant width and plane-strain kinematics. The constitutive law
retains three-dimensional stress and internal-state components. Contact
tractions are integrated per unit width; declared width is applied once to
force and torque. This excludes width spread, lateral tracking, asymmetric
cross-width loading, wrinkling and flatness predictions. A Lagrangian material
mesh initially keeps parcel genealogy explicit. Moving-window or ALE transfer
is a later capability with its own conservative remapping checks.

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
span or the 2D domain owns each portion of mass and compliance. T4 saves
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

The proposed first contact boundary is a prescribed rigid-roll-center gap.
It predicts strip deformation and downstream unloaded thickness subject to
that imposed geometry and declared material law. Results must distinguish
prescribed unloaded geometric gap, loaded roll separation, in-contact
thickness and downstream thickness at a named location. Machine-setting-to-
gauge prediction would instead require stand compliance; elastic roll
deformation/flattening requires an additional contact model. The existing
effective-radius correction does not supply either transient model.

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
and algorithmic dissipation separately. Do not count plastic work as both
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
[web-handling work](https://apicsllc.com/apics/Ie_cdc01/Ie_cdc01.htm)
informs span/reel coupling but does not validate cold rolling. The proposed
plasticity and integration families are associated with
[Simo (1992)](https://doi.org/10.1016/0045-7825(92)90123-2) and
[Chung and Hulbert (1993)](https://doi.org/10.1115/1.2900803);
publisher access to their full text was restricted during this review, so
equation-level specialist review remains required. Independent verification
can use the [Sandia manufactured-solutions method](https://www.sandia.gov/research/publications/details/code-verification-by-the-method-of-manufactured-solutions-2000-06-01/).
These are design inputs, not empirical qualification evidence.

Three choices remain pending: bounded transient episodes versus full-coil
resolved contact; prescribed rigid gap versus required stand/elastic-roll
compliance; and permission for numerical/native dependencies in Linux and
Windows wheels, with a runtime/mesh budget. Synthetic verification can use
declared density, elastic constants, hardening, friction, inertia and span
parameters. Physical validation further needs independently characterized
material/contact data, actual drive/reel/gap parameters and synchronized
transient observations with uncertainty. No scientific or site-use claim
follows from T0–T4 software checks.
