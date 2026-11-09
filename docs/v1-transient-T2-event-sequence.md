# Bounded two-reel event sequence

**Status:** software verification of the declared idealized pre-engaged,
taut, subsonic two-reel model. The `continue_isolated_event_sequence` policy
continues at most eight isolated transitions. It accepts adjacent retained
donor changes while releasing and release-to-wind turns at either reel. Other
event policies keep their original one-transition behavior. This increment
does not validate a physical reel pickup, first engagement, slack, depletion,
or a measured event time.

The model retains the [two-reel port and balance laws](v1-transient-T2-two-reel.md),
the [isolated donor terminal](v1-transient-T2-isolated-donor-restart.md), and
the [release-to-wind midpoint terminal](v1-transient-T2-isolated-recapture.md).
No new constitutive or contact equation is introduced. Each accepted step
has one complete coupled update for both reels and every span cell. A donor
terminal freezes the old donor during its corrected Heun step; the next step
uses the adjacent record. A recapture terminal uses midpoint quadrature for
all fields and ledgers, clips the live wound records at the inventory-derived
turning cut, and starts winding on the next step. The immutable input archive
remains separate from live ownership. All candidates are recomputed from
the newly accepted state after a transition.

The event count and cumulative signed storage discrepancy persist through
the episode. The sum of absolute event storage bounds must stay at or below
`8e-12 J`; a candidate that exceeds this numerical budget stops on the
feasible side. The budget counts donor assignment bounds and the recapture
active ownership, midpoint storage flux and opposite winding packet
discrepancies without allowing cancellation. `transitions` reports ordered
indices, pre/post phases and both cumulative quantities. The separate
per-step span mass/momentum, reel angular and combined energy checks remain
active. Eight and `8e-12 J` are bounded software policies, not physical
parameters or error estimates for the actual mill.

The existing earliest-feasible-limit selection still groups candidate
brackets within `1e-9 s` for **numerical** ambiguity. Competing events stop;
they are never committed as simultaneous physical transitions. The release
root, donor label, storage, tautness, inventory, subsonic, CFL and
zero-speed-start guards from the isolated transitions remain active. A ninth
event stops with `isolated_transition_budget_exhausted`. An unsupported
wind-to-release reversal, tension loss or depletion also stops. A sign-change
bracket can miss a grazing root; none of these brackets encloses the physical
continuum event time.

## Independent equation checks

A separately inverted traveling material wave supplies five isolated exact
event times. Equal-stretch divisions of the original wound records make the
continuum solution unchanged while exercising the event state and record
ownership:

| Time (s) | Transition |
| ---: | --- |
| 0.005 | Right donor |
| 0.008 | Left donor |
| 0.012 | Right donor |
| 0.020 | Right release to wind |
| 0.027 | Left donor |

The tests compare 64/128/256-cell trajectories with the unsplit case,
check event ordering and the exact synthetic times, active ownership and
combined balances, refine CFL and prescribed torque sampling separately,
and verify reflection and observation-cadence invariance.
Separate unequal retained-stretch donor layers are checked against a
piecewise-donor RK4 reel ODE before opposite-end waves arrive; the RK4
reference is also refined independently. A ninth donor and an artificially
tightened cumulative storage budget confirm feasible stops before commit.
The source-bound public workflow and saved-run
replay exercise the same sequence; installed-wheel checks use the packaged
workflow. These are synthetic equation oracles, not physical calibration.

The modeling boundary follows moving-interface analyses that make
compatibility, momentum supply and energy supply explicit; those analyses do
not select this particular reel closure:
[Hanna, *Jump conditions for strings and sheets*](https://arxiv.org/abs/1406.5175),
[Singh and Hanna, *Pick-up and impact of flexible bodies*](https://arxiv.org/html/1611.03332v2).
[SUNDIALS rootfinding documentation](https://sundials.readthedocs.io/en/latest/cvode/Mathematics_link.html#rootfinding)
describes sign-change rootfinding limits. Slack evolution needs a spatial
configuration and constitutive choice; initial contact additionally needs
contact geometry, compatibility and impact/slip laws. Neither follows from
setting the present tensile stress to zero.
