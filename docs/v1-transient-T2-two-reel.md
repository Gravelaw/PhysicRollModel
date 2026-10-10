# Pre-engaged two-reel elastic-span increment

**Status:** bounded, synthetic T2 software verification increment. The public
workflow is `two_reel_span_t2`, with a [source-bound example](../scenarios/v1_two_reel_span_t2.runspec.json)
packaged in the wheel. `python -m physicroll.bundle_cli create --run-spec
scenarios/v1_two_reel_span_t2.runspec.json --out /tmp/two-reel-run` creates a
verifiable, replayable saved run. This increment has no rolling bite or site
validation and does not close full T2.

The span is the fixed global interval `x∈[0,1] m`. Each endpoint has a local
outward normal `n_left=-1`, `n_right=+1`, local span speed `u=n v`, and
independent winding-positive angular coordinate. The outgoing characteristic
is `r=u-cλ`, with `c=10 m/s`. A winding reel supplies `u_w=Rω`,
`λ_s=(u_w-r)/c`, `q=u_w/λ_s`. A releasing reel supplies the exposed frozen
record stretch `λ_w`, then `q=Rω/λ_w`, `λ_s=r/(q-c)`, `u_s=qλ_s`.
The span receives one incoming characteristic per end; no additional speed
or tension boundary is imposed. Its global conservative flux is
`(n q, μ q u-T)` at an end, where `μ=0.1 kg/reference m`, `EA=10 N` and
`T=EA(λ_s-1)`. The left mass flux changes sign when translated from the local
port; the momentum expression does not gain another normal factor.

Each reel predicts `ℓdot=q` and
`J ωdot=τ-RT+μqR(u_s-Rω)`. Torque `τ(t)` is a **prescribed time-only input**,
interpolated linearly between serialized knots. Each reel's speed, cut and
inventory are calculated. Cubic Hermite torque is rejected in this increment:
an unresolved between-knot pulse could evade the two Heun stage samples.

The left stored record uses local material coordinate `σ_left=-S`; the right
uses `σ_right=S`. Both record stores thus use the same inner-to-outer local
ordering. The wound interval at each end is `[cut,cut+ℓ]`, with
`cut=initial_cut+initial_length-ℓ`; the initial cut sum must equal the
span's cell-average reference length. This is checked throughout, together
with total span-plus-reels mass. Winding deposits accepted-stage packets of
the computed incoming stretch. Release consumes an immutable retained donor.
The default `event_policy=reject` raises at a donor boundary or phase
reversal or tension loss. `stop_at_numerical_admissibility_limit` instead saves
the last feasible state before a reel or tautness limit. It does not change
the accepted port law, infer slack dynamics, or resume under a new donor or
phase. The separate `continue_isolated_internal_donor` policy permits
exactly one bounded internal donor restart; its [ownership and numerical
limits](v1-transient-T2-isolated-donor-restart.md) are declared separately.

The local outward span energy flux is
`G=q(μu_s²/2+EA(λ_s-1)²/2)-T u_s`. During release the declared idealized
pickup dissipation is
`D=(-q)(EA-μq²)(λ_s-λ_w)²/2`; it is zero during winding.
Separate reel angular, stored-energy and cumulative mechanical-energy ledgers
are reported. Their combined relation is
`Δ(E_span+E_left+E_right+Q_left+Q_right)=∫(τ_leftω_left+τ_rightω_right)dt`.
The pickup law is a modeling proposal, not a measured or calibrated reel
contact law.

Episodes accept 64, 128 or 256 finite-volume cells, duration from 1 ns to
0.2 s, and CFL 0.35, 0.175 or 0.0875. The scheme uses MUSCL/HLL spatial
flux and a coupled Heun step, split at both torque histories' knots. It
rejects initially non-taut or supersonic states. Under either event-handling
policy it locates the first **numerical admissibility limit** among both
reels' reversal, internal donor and depletion conditions and the minimum tautness margin
over ports, cells and reconstructed faces. A disposable trial may extend the
linear elastic formula only to stretch `0.9999`; deeper signed-elastic trials
are shortened or rejected. Depletion trials may continue the positive-core
radius and inertia formulas through at most `0.0001 m` of negative wound
inventory, solely to determine which boundary limits the step. The accepted
state retains positive inventory. No compressed or negative-inventory trial,
heat or wound packet is committed. The complete coupled Heun trial is repeated
while bisecting.
A predictor stage can reach a limit
before the corrected endpoint: `limit_source` identifies this, and
`bracket_time_s` is then a numerical bracket, **not a physical event-time
estimate**. Under the stop policy an accepted cut within `1e-12` reference m
of a donor boundary, or an accepted tautness margin within `1e-12`, stops by
proximity with no time bracket. The returned duration then is the last
feasible accepted time. The isolated-donor policy may instead resolve a
remaining positive label gap with a small terminal step. A release reel stops
at a positive
`1e-10 m` numerical inventory threshold. Its reported bracket locates that
threshold, not physical zero inventory; `inventory_stop_threshold_m` and
predictor/corrected signed margins make this explicit. A state already within
the threshold, or within `max(1e-15 m, 2|q|·1e-11 s)` above it at its current
release flux, stops with no time bracket. The latter distance is saved as
`inventory_proximity_tolerance_m`. The decision uses whole-reel inventory,
independent of retained-record segmentation. A winding reel may grow from
below the threshold. The default reject policy still rejects depletion.
This pre-engaged interval does not include
engagement, general post-event transitions, free leading edges or a roll/strip contact
law. Snapshot requests read accepted states
without changing the integration trajectory. Full accepted cell fields are
saved and source hashes bind the example to its installed solver.

The shared scheduler selects the lowest feasible bracket endpoint and reports
any other candidate within `1e-9 s`. Each grouped candidate identifies
whether its bracket overlaps the selected bracket or is merely within that
numerical tolerance. Predictor-trial and corrected-state signed margins at
the common feasible stop are reported separately. Overlapping brackets do
not establish an internal root order; grouping is not a claim that physical
events are simultaneous.

For an internal donor candidate, the solver separately bisects the corrected
Heun endpoint cut against the exposed record label within the original
complete trial, holding the pre-event donor fixed. It reports
`corrected_arrival_bracket_time_s` when that
corrected margin changes sign; a predictor-only crossing reports no corrected
arrival bracket. Under the stop policy, `feasible_stop_time_s` still comes
from the earliest predictor/corrected numerical admissibility limit, and no
trial transfer or next donor is committed. The isolated-donor policy uses a
separate corrected terminal bracket and accepts at most one adjacent donor
with a bounded, reported ownership residual. The corrected bracket is an estimate for the
discrete numerical trajectory, not a rigorous enclosure of the continuum
event. Sign changes can miss grazing or repeated crossings; a physical
event-time enclosure would require a separate solution-error bound and a
nonzero crossing-speed bound.

For a reversal candidate, the solver likewise bisects the **phase-signed
corrected angular speed** within the original complete trial. It reports a
`corrected_reversal_bracket_time_s` only if that signed corrected endpoint
crosses zero; a predictor-only crossing leaves the field null. Each corrected
donor or reversal bracket reports its time gap from the common accepted stop,
including when the candidate was grouped behind another limit. The reversal
bracket is also an estimate for the frozen pre-event numerical branch, with
the same physical-event caveats. It does not switch phase or move a wound
record. At a very small positive winding step, an individual Heun stage's
label interval can round to zero; the accepted whole-step packet then keeps
the represented material after bounding its strain-energy quadrature
discrepancy. The public two-reel result reports aggregate storage defects,
not an individual packet discrepancy.

## Independent synthetic checks

At `λ=1.001`, global `v=0.1001 m/s`, the left release flux is `−0.1`
reference m/s from a `λ_w=1.01` record; the right wind flux is `+0.1`.
Manufactured **two separate time-only torque histories** keep each surface
speed constant. Over 0.1 s the left inventory decreases from 1 to 0.99 m,
the right increases to 1.01 m, left stored strain drops `5e-6 J`, right
stored strain rises `5e-8 J`, and left dissipation is `4.049595e-6 J`.
The spatial reflection exchanges ends, reverses global velocity and
momentum, and preserves local reel angular and energy states. Tests also
perturb only the left torque and verify the right reel responds after a wave
crosses the span, while its early response remains at numerical zero.
The test suite separately checks mesh/CFL choices, record output isolation,
observation-cadence invariance, input label mismatches, default rejection and
the optional one-sided donor/reversal stops. The donor label oracle stops near
`0.01037 s` for a `0.001037 m` record at `0.1 m/s` release, on 64/128/256
cells and under spatial reflection. A donor limit coincident with a forcing
knot stops at the accepted state without a zero-length step. The reversal
case's combined-energy defect on 64 cells is about `3.5e-7 J` and falls to
about `1.6e-8 J` on 256 cells. This is unresolved finite-volume numerical
loss, not physical pickup heat; the public `1e-8 J` internal balance check
fails for that case. A source-bound stopped RunSpec is replayed from a saved
bundle and reports requested versus completed duration.

The independent two-release affine reference has
`λ(t)=1.01−0.2t`, `v(x,t)=−0.2(x−0.5)/λ(t)` and exact first physical
zero tension at `0.05 s`. Both prescribed torque histories are independently
manufactured from the reel angular equation, with constant retained stretch
`1.01`. The 64/128/256-cell numerical stops occur at approximately
`0.04999999928`, `0.04999999981` and `0.04999999994 s`; this is equation
verification for a synthetic case, not proof that every numerical stop
brackets a physical event. A separate winding-port case stops when its
predictor reaches zero tension while the corrected endpoint remains taut.
Tests compare tension-first and donor-first coupled cases on the same
accepted-state scheduler. The narrower [T2A8 affine fixture](v1-transient-T2A8-design.md)
remains a separate reaction-mode reference.
Tests also distinguish overlapping two-donor brackets, separated brackets
grouped by the numerical tolerance, and a clearly later donor, including
left/right reflection.
For a `0.001037 m` release record and `q=-0.1 m/s`, an independent constant-flow
oracle reaches zero inventory at `0.01037 s`. The numerical threshold stop is
approximately `0.010369999 s`; tests cover all three grids, reflected ends,
allowed CFL choices, core-radius/inertia limits, independent pickup-heat
rate, combined inventory/work/energy/angular ledgers, prelimit completion,
initial threshold proximity, and verified saved-run replay. These checks do
not establish a physical event-time estimate for arbitrary trajectories.
For internal donor arrival, a separate `0.0037 m` exposed layer at the same
constant flux reaches its label at `0.037 s`; tests compare corrected arrival
brackets across all three grids and reflection. A two-release affine wave has
independent competing label-arrival times of about `0.02031990757 s` and
`0.03041866290 s` for exposed lengths `0.002 m` and `0.003 m`, respectively.
The first corrected-arrival error decreases across the 64/128/256 grids and
across three CFL choices at fixed 64 cells. A predictor-limited torque case
shows its predictor-to-corrected arrival gap falls on a finer time grid;
forcing-knot placement can cause a plateau between adjacent CFL choices.
A faster predictor with no corrected sign change is checked to return no
invented corrected-arrival bracket.

The isolated-donor case continues across one `0.0037 m` layer at its exact
constant-flow arrival `0.037 s`. An independently calculated new-donor port
and reduced reel ODE check the immediate trace jump and short-time inventory,
angular speed, work, heat and impulse. Split versus unsplit equal-stretch
records agree to roundoff on three grids and under spatial reflection.
Spatial, CFL and declared torque-knot refinement are checked separately.
Unsupported new slack trace, skipped thin interval, competing or second donor
event and predictor-only arrival retain a feasible stop. A forcing knot at
the donor label checks the bounded small terminal step. The transition and
its signed stored-energy ownership residual are saved and replayed.

An independent symmetric standing-wave solution supplies two driven winding
reels with simultaneous exact reversal at `0.02 s`, positive tension and
cell-average initial fields integrated over exact material labels. Both
corrected numerical reversal brackets approach `0.02 s` across 64, 128 and
256 cells; the 256-cell error is below `1e-9 s` for 400 torque intervals.
The bracket widths are below `1e-11 s`; separate CFL and torque-knot
refinement checks compare successive numerical estimates. Independent
per-reel impulse and drive work, whole-system mass, inventory and mechanical
energy are checked, with zero winding heat. A separate predictor-only
reversal case verifies that no corrected root is invented. This is an
equation-level synthetic verification case, not a mill reversal validation;
the two event records share the manufactured symmetry and do not prove
general simultaneous-event resolution.

Internal ledger closure for an arbitrary declared run does not prove an
independent benchmark passed. The ResultBundle therefore reports numerical
verification, scientific qualification and operating readiness as
`NOT_ASSESSED` when internal balances pass. No synthetic result is a claim
of physical mill accuracy.

## Next dependencies

The [bounded event sequence](v1-transient-T2-event-sequence.md) now reuses
the numerical earliest-limit scheduler for up to eight separated donor and
release-to-wind transitions across both ends. Continue with independently
verified wind-to-release material re-exposure, restart across event
boundaries, and distinct physical laws for engagement, slack and depletion.
Simultaneous transitions and physical event-time validation still need
separate treatment. Then add a drive train and T2/T3
interface with a single owner for each moving material region. Full 3D
transient strip/contact, rigid gap and compliant elastic-roll modes, dynamic
animation, broader editor acceptance and W6 remain open under the
[critical path](v1-integration-critical-path.md).
