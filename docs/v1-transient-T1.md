# T1 bounded prescribed-motion transport contract

**Status:** first executable kinematic layer, not the complete v1 transient
solver. This equation-level contract was independently reviewed before coding.
It uses one continuous uniform synthetic strip: constant full thickness
`h > 0`, width `w > 0`, density `rho > 0`, fixed straight free span of length
`S > 0`, no longitudinal stretch or reduction, no winding-interface slip,
gaps, compaction or changing wrap-path inventory. The annular reel formula is
a continuous-volume approximation, not discrete spiral/contact mechanics.
Unequal entry and exit speeds through a reducing bite are outside T1; T3 must
supply a conservative deformation map before those can be modeled.

The sole prescribed strip speed `v(t)` is signed positive from left to right,
continuous and piecewise linear over explicit knots with no extrapolation.
For each knot interval, integrate exactly:

`q(t0 + dt) = q(t0) + v(t0) dt + 0.5 a dt²`, where
`a = (v(t1) - v(t0)) / (t1 - t0)`.

Each parcel has a permanent reference coordinate `a` in metres, initially
spanning `[-L_left0, S + L_right0]`. Material in the free path has
`x(a,t) = a + q(t)`. The free-path material boundaries are `a = -q(t)` and
`a = S - q(t)`; left/right reel lengths are `L_left0 - q(t)` and
`L_right0 + q(t)`. Reversal changes `q` and ownership, never the parcel ID or
orientation. A material point on a reel is not assigned a fabricated Cartesian
position by this formula.

For each reel with core radius `R_core`, annular radius and inventory mass are
`R = sqrt(R_core² + h L / pi)` and `M = rho w h L`. Angles are unwrapped and
positive in each reel's own winding direction:
`theta - theta0 = 2 pi (R - R0) / h`. A scene-specific orientation transform
maps these local angles into common world axes. A fixed transport roller with
declared no-slip coupling may use `theta = theta0 + sigma q/R_roller`, where
`sigma` is its declared orientation sign. Work-roll angle/rolling slip are not
inferred by that transport-roller equation.

The input declares initial reel lengths, optional maximum capacities, core
radii, initial angles, initial parcel coordinates and a finite motion history.
Each accepted state reports time, signed displacement, reel lengths/radii,
masses, unwrapped angles and parcel ownership/free-path position. A separate
event ledger reports speed reversals and parcel crossings at `x=0` or `x=S`.
The first empty or full reel event terminates the episode at its analytic
first-hit time; requested time after that remains unexecuted. Events at a
speed knot or reversal are deduplicated. A parcel may cross the same boundary
twice around a reversal. Animation samples query states without advancing
history.

Before treating this layer as verified, compare zero speed, constant speed,
linear ramp, forward/reverse return, mid-interval reversals, both reel
inventory bounds, parcel crossings and independent frame cadences against
closed formulas. Reject incompatible initial radius/length or secondary
speed declarations rather than average them. Check constant strip volume and
mass including the free span; no dynamics, tension, torque, plastic strain,
contact, gauge prediction or thermal field is claimed. A restart contract must
preserve displacement, inventory, unwrapped angles, parcel ownership, event
consumption and source identity; restart equivalence is a separate T1 gate.

Initial numerical-verification tolerances for these analytic checks are
`1e-10 m + 1e-12 × characteristic length` for displacement/inventory,
`1e-9 s` for event time and `1e-9 rad` for angle. They are software comparison
targets, not empirical mill accuracy. Physical-time samples are independent
of solver/animation frame cadence.

Primary [Boulter et al. web-handling work](https://apicsllc.com/apics/Ie_cdc01/Ie_cdc01.htm)
motivates explicit adjacent spans, winding dimensions and material flow. The
equations above follow geometry and conservation under this document's stated
assumptions; the web-handling study does not validate a rolling model. The
full 3D compliant strip/contact, drive/span dynamics and Blender/USD animation
remain mandatory in the [v1 scope amendment](v1-scope-amendment-2026-10-10.md).
