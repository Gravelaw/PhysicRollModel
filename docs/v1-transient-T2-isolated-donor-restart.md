# One isolated internal donor restart

**Status:** bounded T2 software verification under the [declared idealized
pickup law](v1-transient-T2-pickup-decision.md). The new
`continue_isolated_internal_donor` event policy continues through at most one
internal retained-record boundary during a pre-engaged, taut, subsonic
two-reel episode. Other event limits retain their feasible-side stop. This is
not a physical reel-contact or event-time validation.

For a releasing reel, the local cut increases as
`cut=initial_cut+initial_length-ell`, `cut_dot=-q>0`. The next original
retained record begins at label `b`. The terminal coupled Heun step bisects
the **corrected** cut until its accepted endpoint satisfies
`0 <= cut_H-b <= 1e-13 reference m` and its time bracket is no wider than
`1e-11 s`. The original donor is frozen throughout that terminal step,
including any predictor stage that crosses `b`. Neither cells, reel inventory,
the cut, nor original records are snapped or rewritten. The next step selects
the adjacent donor by the half-open record interval. Near a torque knot, a
represented old-donor remnant can require a very small terminal step; it is
accepted only if time and labels advance at floating-point resolution.

All other numerical guards remain active: positive reel inventory,
unchanged release sign, taut and subsonic traces/cells, CFL, no skipped next
record, and no competing limit within the numerical grouping tolerance.
A predictor-only donor crossing with no corrected endpoint crossing cannot
restart. After the terminal step, the new donor trace is calculated from the
unchanged outgoing characteristic `r=u-c*lambda`:

```text
q_new = R*omega/lambda_w_new
lambda_span_new = r/(q_new-c)
u_new = q_new*lambda_span_new
```

The new trace must itself be taut, subsonic and releasing. If it is invalid,
or another event competes, the solver retains the feasible-side stop and
records the reason. Cells, `ell`, `omega`, `R`, `J`, accumulated heat and work
are continuous across an accepted donor switch. Flux, tension and modeled
pickup dissipation may jump. The [pickup decision](v1-transient-T2-pickup-decision.md)
links the primary moving-discontinuity and pickup analyses that motivate
explicit interface momentum and energy ownership; neither paper calibrates
this proposed reel-contact law.

The old-donor terminal quadrature can represent a small amount of material
beyond the record interface. With inventory-coordinate overshoot
`delta_ell=initial_length-(b-initial_cut)-ell_H` and stored-energy density
`W(lambda)=EA*(lambda-1)^2/2`, the reported signed donor-assignment discrepancy
is `delta_ell*(W_old-W_new)`. It is reported in `transitions`, together with its
absolute bound. The bound uses the larger of the label and inventory
overshoots plus `1e-14 m` of label-resolution allowance, times the absolute
stored-energy density jump; it must not exceed `1e-12 J`. It is not injected as heat or
subtracted from the existing energy ledger. The separate full storage and
energy balance diagnostics also include ordinary numerical integration and
label arithmetic effects; this donor-assignment bound does not replace them.
The exact cut, time bracket,
old/new original-record identities, and pre/post port states are saved.
`events` separately records any later unsupported stop. Neither array claims
a rigorous physical event-time enclosure.

The terminal ownership bound is also computed from the independent inventory
coordinate, `initial_length-(b-initial_cut)-ell_H`. It must agree with the
label subtraction within `1e-14 m`; both must lie in `[0,1e-13] m`. A label
whose input or boundary ULP exceeds `1e-14 m` cannot authorize a restart.
This guard prevents a large absolute label from rounding onto the boundary
while old-donor inventory remains. Disposable post-switch steps span at most
`1e-9 s`, split at every prescribed torque knot, and check for a competing
donor, reversal, depletion or tautness limit and reconstructed CFL. The check
denies restart if its 256-step probe budget is exhausted. It does not extend
the committed episode or imply an event-time error bound.

## Independent synthetic checks

An old constant-flow donor at `lambda_w=1.01` reaches a label `0.0037 m`
away at exactly `0.037 s`. For the next donor at `lambda_w=1.02` and
the same instant's `r=-10.1101`, `R*omega=-0.101`, independent port equations
give `q=-0.09901960784313726 reference m/s`,
`lambda_span=1.00109717503155`, `u=-0.09912824968449663 m/s`,
`T=0.01097175031550046 N` and modeled pickup heat rate
`D=0.0001768894974844970 W`. A separate reduced RK4 reel ODE uses the
declared piecewise-linear torque and constant outgoing characteristic for the
short post-switch interval. Tests compare reel inventory and speed, work,
heat and angular impulse independently on 64/128/256 cells and three CFL
choices. Torque sampling is refined separately. Splitting a donor into two
equal-stretch records leaves the final trajectory unchanged to roundoff,
including under left/right reflection.

Tests also require a feasible stop for an inadmissible new trace, a record
too thin to resolve without skipping, a competing two-donor event, a second
donor arrival, and a predictor-only crossing. A donor at a forcing knot
exercises the small accepted terminal step. Separate regressions reject
unresolved million-metre absolute labels, a second donor just across a torque
knot, and an interior narrow torque pulse within the grouping window.
Source-bound RunSpec, verified
saved-run replay and installed-wheel checks use the same transition record.

This policy does not handle a second restart, phase reversal, simultaneous
events, slack, depletion continuation, bite/drive engagement or 3D contact.
Scientific validation and site qualification remain separate from these
synthetic equation checks.
