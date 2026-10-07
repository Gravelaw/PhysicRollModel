# Rolling mechanics, contact, lubrication and numerical-method review

Review date: 2 October 2026. Scope: R001–R010, R012–R014, R017–R022,
R056–R059, R062, R092–R093 and the separately inventoried Fleck et al.
(1992) source in the multipass note. The associated
[source records](contact-source-reviews.json) distinguish this session's access
from historical review. A failed re-fetch does not erase a previous review, but
does prevent claiming a new full-text reading. No paper files are redistributed.

## Decision supported by the evidence

Qualify a thick-strip mechanical benchmark first, retain a separate research
track for noncircular single-layer foil, and require an explicit layer/contact
model before pack rolling. These are separate applicability domains, not one
formula extrapolated over a prescribed gauge journey. The illustrative
6 mm → 0.05 mm route is not an acceptance requirement.

Current `slab.py` and `contact.py` correctly describe themselves as projected,
uncalibrated mechanics. They do not implement the noncircular roll response,
finite sticking zone or elastic strip recovery addressed by the foil literature.
The 300 µm and radius-ratio guards are software assumptions, not experimentally
established minimum gauges or mill capacity limits. More computation cannot
resolve missing material state or lubricant identification.

## What the renewed reading changes

The complete official [Shigaki et al. PDF](https://mdpi-res.com/d_attachment/lubricants/lubricants-03-00113/article_deploy/lubricants-03-00113.pdf)
is accessible even though the HTML endpoint currently returns 429. Its Eq. 6
retains the spatial derivative of plane-strain strength. Equations 11–13 retain
different strip/roll elastic properties; Eqs. 14–15 then simplify for steel
strip and steel rolls. Copying that simplification into aluminium would change
the model. Its regularisation parameter is scaled by roll speed; small values
make numerical solution difficult, while large values change the physical
friction response. Table 3 and the conclusions support a sensitivity study,
not a universal smoothing constant. Its examples compare models for steel,
not measured aluminium performance. [R005]

[Li et al.](https://www.jstage.jst.go.jp/article/isijinternational/58/4/58_ISIJINT-2017-623/_html/-char/en)
provide an unusually useful contact-profile experiment: 304 stainless strip,
three lubrication conditions, measured partly rolled profiles and load. Their
Eq. 1 states total load and strip width explicitly in Hitchcock's radius.
The profile-derived radius and contact length are different observables; the
Hitchcock radius increasingly overstates the fitted profile radius. This is
evidence to test a contact model's limits, not a source of aluminium friction
or flow-stress constants. [R006]

The [Fleck et al. 1992 paper](https://sage.cnpereading.com/storage/sage/journal/article/PIB/1992/PIB_1992_206_2/unzip/10.1243_PIME_PROC_1992_206_064_02.pdf)
improves on the 1987 elastic-foundation approximation with elastic half-space
roll response. It distinguishes plastic reduction zones from the central
no-slip region, including contained plasticity and possible elastic unloading.
Its displayed load/torque results use zero front/back tension, although the
formulation includes tensions. Torque is **per work roll, per unit strip
width**. The paper explicitly identifies constant Coulomb friction and absent
hardening as idealisations; its curves are numerical reference problems, not
an independently measured foil dataset. [FLECK1992]

For [Erfanian et al.](https://arxiv.org/html/2408.01347v4), v4 is dated 29 May
2025 and differs in equation numbering from the v1 referenced in code. The
leading-order slab pressure is distinct from the paper's higher-order
through-thickness fields. Table 1 states rigid rolls, isotropy and the
asymptotic model's slipping-everywhere assumption. Its comparison deteriorates
after the neutral point where FE develops sticking. Therefore implementing
more asymptotic terms would not itself supply a foil-contact model. The
constant-strength assumption also remains despite comparisons to a hardening
FE case. [R012]

The [Flanagan et al. author manuscript](https://green-robin.lnx.warwick.ac.uk/files/flanagan%2Boconnor%2Berfanian%2Bmusic%2Bbrambley%2Bokiely-2025.pdf)
adds a strong numerical-verification requirement: global load convergence can
coexist with poorly resolved interior stress/strain. Its case-specific study
selects 30 elements per half-thickness against a finer reference, with material
and solver choices documented. That is not a universal mesh prescription.
Rigid rolls and DC04 material make this a numerical field-resolution lead,
not foil or aluminium validation. [R014]

## Approach selection and dependencies

These are project recommendations inferred from the cited evidence, rather
than claims that any source supplies a complete ready-to-use simulator.

| Approach | Intended use and information supplied | Dependencies and limitations | Relative computation and decision |
|---|---|---|---|
| Existing heuristic | Legacy demonstration/regression | No independent calibrated applicability; can mask missing contact physics | Very low; retain labelled legacy behaviour |
| Rigid circular projected slab, constant or spatial strength | Baseline load, signed torque, slip, work and sensitivity in a bounded single-layer strip domain | Known tension stresses and independently constrained material/friction; no transverse fields or elastic recovery | Low; first measured benchmark tier |
| Circular Hitchcock iteration | Test incremental force/contact-length effect | Roll modulus, radius and force/width/draft conventions; coupled residual and independent root comparison; no uniqueness guarantee | Low to moderate; optional bounded tier, not foil solution |
| Noncircular elastic contact plus elastic-plastic slab and finite stick/slip zones | Single-layer foil mechanics and comparison of contact regimes | Roll influence kernel, strip elasticity/hardening, friction and elastic surface kinematics; branch and complementarity checks | Moderate iterative solve; research gate before foil schedules |
| Mixed lubrication/contact model | Connect speed, viscosity, roughness and lubricant state to traction and surface quality | Measured lubricant rheology/temperature, inlet supply, multiscale roughness, independent material response | Moderate to high; start with identifiable effective friction, add closures when observations support them |
| Multiple-scales/flowline reduced fields | Through-thickness deformation and possible constitutive-path inputs | Geometry/asymptotic domain checks; no automatic noncircular/sticking closure; compare fields as well as integral force | Low relative to FE; optional research branch |
| Plane-strain FE | Independent constitutive/contact/reference calculations | Mesh/contact/time-step convergence, large strain stress measures, artificial energy checks; still requires measured validation | High; selected benchmark cases, not every search candidate |
| 3D FE and stack/strip coupling | Edge spread, asymmetric loading and through-width fields | Qualified 2D kernel, stack/compliance measurements and much larger calibration dataset | Very high; use targeted designs or surrogates after simpler tiers pass |
| Pack rolling | Layer-specific states, strip/roll and interlayer contact, separation and surface outcomes | Per-layer gauge, friction, tension allocation, symmetry assumptions and route history | Separate research module; cannot multiply a single-strip gauge and call it validated |

[Bland–Ford](https://journals.sagepub.com/doi/10.1243/PIME_PROC_1948_159_015_02)
and [Orowan](https://journals.sagepub.com/doi/10.1243/PIME_PROC_1943_150_025_02)
remain important ancestry and limiting-case targets. Their full algorithms
were not recovered in this reread. The accessible abstracts cannot justify
claiming a faithful reimplementation of either complete original method.
[Sims](https://journals.sagepub.com/doi/10.1243/PIME_PROC_1954_168_023_02)
is a hot-rolling source; it must not become a cold-aluminium parameter card.

The primary abstracts of [Sutcliffe–Johnson 1990](https://journals.sagepub.com/doi/10.1243/PIME_PROC_1990_204_064_02),
[Sutcliffe–Montmitonnet 2001](https://www.cambridge.org/core/journals/metallurgical-research-and-technology/article/abs/numerical-modelling-of-lubricated-foil-rolling/28E21286CCF29BAB72008A5C288E1BA5)
and [Le–Sutcliffe 2006](https://link.springer.com/article/10.1007/s11249-006-9021-z)
support mixed-lubrication and roughness-state dependencies. They do not expose
all closure details needed for audited reproduction. Boundary friction factor,
Coulomb coefficient and real asperity contact fraction must remain distinct.
The [film-thickness experiment abstract](https://journals.sagepub.com/doi/10.1243/PIME_PROC_1990_204_065_02)
also makes inlet supply uniformity an experimental variable. It is not enough
to specify viscosity and assume a fully flooded inlet. [R056, R010, R057, R093]

## Source → implementation → evidence traceability

Code and tests below were inspected directly in the current checkout. This is
a documentary traceability assessment; the parent audit records suite execution.

| Requirement / evidence | Equation or assumption | Current implementation/test inspected | Validation debt / acceptance gate |
|---|---|---|---|
| R012 v1; R005 Eq. 6 | Full thickness; positive compressive pressure; `h p' = h K' + K h' ± 2 μ p`; uniaxial to plane-strain strength conversion | `physicroll/slab.py::_solve_grid` integrates `z=p−K` for spatial strength; `test_independent_variable_strength_pressure_reference` | Keep v1 equation mapping; independent derivation and SI/sign reference before changing laws |
| R006 Eq. 1 | `R'=R[1+16(1−ν²)F/(π E w Δh)]` | `contact.py::CircularRollElasticity.radius`; width/zero-load/rigid-limit and independent-bisection tests in `test_contact_increment.py` | Aluminium contact-profile and load comparison; do not identify compliance using force alone |
| R005, FLECK1992 | Slip/stick inequality and noncircular elastic response | Current slab rejects Coulomb shear above shear yield and requires one interior neutral point; no sticking solver | New domain-specific implementation plus regime-transition, traction-bound and regularisation convergence tests |
| R012; homogeneous plane strain | `Δεeq=2 ln(hin/hout)/√3`; independent material history | `materials.py::BiteHardening`; history/spatial-work/refinement tests | Measured alloy/temper/path/rate/temperature flow curves; scalar history cannot predict texture/damage |
| FLECK1992; projected work derivation | One-roll torque, both-interface dissipation, nominal shaft radius for angular speed | `slab.py` explicit torque/power fields; regenerative and zero-draft-limit tests | Shaft torque with idle, acceleration, drivetrain and reel losses separated; noncircular elastic kinematics remains missing |
| R062 Tables 1–2 | Three AA5052 force/slip measurements; ambiguous material/speed conventions | `scenarios/literature/shao2015_aa5052/`, `literature.py`, source-unit audit and speed/history tests | Preserve ambiguity; source friction numbers are not independently measured controllable settings |
| R014, R017–R019 | Field, mesh, equilibrium and energy convergence | No independent FE integration in current solver | Reproduce one source numerical case before aluminium use; sensitivity of fields and residual stress, not just load |
| R010/R056/R057/R093 | Mixed-film, inlet supply and roughness effects | Friction remains an input; no lubricant-film solver | Independent roughness/lubricant and force/torque/slip observations; avoid friction absorbing wrong material law |

The geometric contact formula is circular geometry, while traction and work are
projected small-angle mechanics. Using exact circular contact length does not
make the entire mechanics exact finite-angle contact. Roll diameter, effective
contact radius and physical shaft radius must remain explicitly named quantities.
The current implementation makes that distinction and preserves the nominal
shaft radius for torque and rotational speed.

## Measured samples and numerical benchmarks

**AA5052, R062: conditional first replay sample.**
[Shao et al.](https://www.iieta.org/journals/ijht/paper/10.18280/ijht.330113)
provide three single-stand passes, 4.10 → 1.72 mm, with measured force/slip
columns. Preserve these measurements separately from their model's outputs.
Eq. 3 leaves the history weight unspecified. Eq. 6 calls `R` diameter whereas
Table 1 says radius. Eq. 4 compares pressure with shear yield where a traction
cap would normally involve `μp`; resolve this before copying it. The printed
strain/work expressions and speed location also need clarification. The stated
force/slip agreement does not validate computed heat. Retain the current
alternative-interpretation diagnostics and request author/raw-data clarification.
[R062]

**AW2024/AW5083, R007: prospective aluminium laboratory benchmark.** The
historical review identifies experimental deformations/velocities and DEFORM-2D
comparisons. Current publisher and national-library content fetches failed, so
no new table extraction is asserted here. Obtain lawful full text and quantify
which values are measured before adopting this as a calibration dataset.

**Al1050, R013: prospective field benchmark.** Existing notes report flowline,
FE and distortion-pattern comparisons and data on request. Current HTML and
PDF access failed; the inventory retains the inherited review separately. This
cannot be counted as a newly audited public numerical dataset.

**R006 steel profile experiment:** use as a cross-material method check, with
source material retained, to exercise geometry and contact-profile extraction.
Do not include it in aluminium predictive-accuracy totals.

**R005/FLECK1992/R012/R014 numerical cases:** use exact documented inputs and
versions as numerical reproduction targets. They test implementation against
another model under declared assumptions. They do not replace held-out measured
coil data or qualify plant settings. Raw dataset licences, file integrity and
model-input versions require a separate archive-level check.

## Software choice

[Abaqus rolling examples](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEEXARefMap/simaexa-c-rolling.htm)
are useful reproducible verification problems. Their reported mass-scaling and
speed choices are example-specific, and their thick-plate domain differs from
cold foil. [Mass scaling documentation](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEANLRefMap/simaanl-c-massscaling.htm)
requires demonstrating that changed inertia does not alter the solution.
[ALE documentation](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEANLRefMap/simaanl-c-aleover.htm)
describes topology-preserving mesh motion/remapping; it is not an unrestricted
remesher. An FE acceptance package needs mesh, contact, artificial-energy,
mass-scaling and time-step studies for its own outputs. [R017–R019]

[CalculiX 2.23](https://dhondt.de/ov_calcu.htm) lists large-deformation,
thermal and contact capabilities, but its contact formulations and licence
must be checked against the chosen pipeline. [Kratos](https://kratosmultiphysics.github.io/Kratos/pages/Kratos/For_Developers/Data_Structures/Constitutive_Law.html)
provides a constitutive-law extension architecture and strain-measure
compatibility mechanisms, not a verified aluminium rolling application.
[PyRolL's paper](https://joss.theoj.org/papers/10.21105/joss.06200.pdf)
offers useful pass-sequence/plugin architecture for groove rolling. Reusing its
architecture does not transfer long-product calibrations to flat foil. Pin
actual solver/application/plugin versions and review dependencies before selecting
a distribution model. [R020–R022]

[COMSOL Reynolds documentation](https://doc.comsol.com/6.4/doc/com.comsol.help.rotor/rotor_ug_hydrodynamicbearing.8.03.html)
and its [cavitation example](https://doc.comsol.com/6.4/doc/com.comsol.help.models.cfd.journal_bearing_cavitation/journal_bearing_cavitation.html)
help define thin-film assumptions and distinguish physical pressure from a
cavitation solution variable. They supply no rolling-specific lubricant card.
Rendered formula images were not fully verified, so no coefficients or hidden
equations are transcribed. [R058–R059]

## Actionable mechanics backlog and stop conditions

1. **Required science:** choose alloy/temper and available measured sample;
   obtain independent flow curves, initial history, calibrated roll geometry,
   force/torque/speed/tension observations and measurement uncertainty. Stop
   accuracy claims where parameter identity or units cannot be resolved.
2. **Required evidence:** acquire lawful R001/R002/R008/R009/R010/R056/R057/R093
   full texts where reproduction depends on their algorithms; repair current
   R007/R013 access. Do not delay current bounded numerical verification while
   waiting for unrelated sources.
3. **Engineering now:** version-pin source/equation mappings, make uniaxial,
   plane-strain and shear strengths explicit in schemas, retain per-roll and
   whole-mill fields, and report every rejection/indeterminate result in route
   replay. Existing tests provide a starting point, not measured validation.
4. **Required science before foil:** specify a noncircular contact model using
   unequal strip/roll elastic constants; reproduce numerical regimes; compare
   circular and noncircular models on overlapping gauges. Stop any optimizer
   that treats a rejected domain as a low-cost candidate.
5. **Required science before lubricant optimization:** establish an identifiable
   friction/supply/roughness model from joint observations. Do not make friction
   or material strength free control variables.
6. **Required science before pack routes:** define layer count, per-layer
   thickness/history, interlayer lubrication, tension allocation and separation
   measurements. A route topology record is possible now; predictive pack force
   and quality are deferred.
7. **Engineering after benchmark qualification:** deterministic replay remains
   the judge of optimizer candidates; carry state through every pass/interpass
   event and retain pass-specific equipment/range metadata. Candidate savings
   smaller than model discrepancy cannot support plant improvement claims.

The deployment implication is a local-first offline/advisory simulator with
visible applicability and uncertainty. No source reviewed here establishes
live-control readiness for this repository. That endpoint needs a separate
plant safety/controls programme and authorization.
