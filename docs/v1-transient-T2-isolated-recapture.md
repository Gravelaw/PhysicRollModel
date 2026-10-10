# One isolated reel release-to-wind recapture

**Status:** bounded T2 software and synthetic-equation verification under the
[declared idealized pickup law](v1-transient-T2-pickup-decision.md). The
`continue_isolated_release_to_wind` policy may continue through one isolated
release-to-wind turn in a pre-engaged, taut, subsonic two-reel episode. Other
limits stop on their feasible numerical side. The time and label at the turn
are numerical results, not certified physical event enclosures. No contact
calibration, transient rolling contact or site qualification is claimed.

## Numerical turn and coupled state

Each reel's local angular coordinate is winding positive and its reference
inventory obeys `ell_dot=q`. For a releasing port, `q=R*omega/lambda_w<0`;
for a winding port, `u=R*omega` and `q=u/lambda`, where the outgoing span
characteristic supplies `lambda`. At zero angular speed both port traces have
`q=u=0`, `lambda=-r/c` and angular acceleration
`(torque-R*tension)/inertia`. The state is not snapped and no impulse is added.

Ordinary steps use the existing coupled Heun integrator. A candidate reversal
is accepted only if a **separate corrected explicit-midpoint** trial brackets
the release-to-wind root. From the last accepted release state, compute
`Y_mid=Y_0+(h/2) F_release(Y_0)` and
`Y_1=Y_0+h F_release(Y_mid)` for both reel inventories, speeds and angles and
all span cells. The corrected endpoint is evaluated with the winding port.
Every terminal-step ledger uses `h` times the same midpoint rate: span mass
and momentum flux, each reel's drive work, angular impulse, stored-strain
flux, pickup heat and any packet deposited at the other winding reel.
Start and midpoint release fluxes must remain negative; endpoint wind flux
must be nonnegative. An exactly represented zero endpoint may begin winding
only with strictly positive sampled angular acceleration; later stages must
wind strictly positive. Endpoint release dissipation from a disposable trial
is never committed. Subsequent steps return to Heun with the new winding phase.
If an exact-zero start and a later unsupported reversal fall inside one
coarse step, bounded step halving first establishes positive winding speed;
the later reversal then receives the ordinary feasible-side stop. If no
representable positive startup step exists, the accepted zero state is the
feasible stop.

The corrected midpoint endpoint must have
`0 <= omega <= 1e-12 rad/s`; its numerical root bracket is at most `1e-11 s`.
The sampled angular accelerations at start, midpoint and new-phase endpoint
must each exceed `1e-6 rad/s²`. Half their minimum forms a conservative
**sampled numerical guard** `a_min`; it is not a certified acceleration lower
bound between samples. The reported near-root label-sliver estimate is
`R_max*epsilon_omega²/(2*lambda_min*a_min)`, where `epsilon_omega` includes
the corrected endpoint residual and the sampled maximum acceleration times
the bracket width. The estimate must be below `1e-12 reference m`. It does
not bound midpoint truncation error or the difference from the exact physical
turning label. Predictor-only crossings do not authorize recapture.

The terminal stages retain taut/subsonic traces and cells, positive reel
inventory, reconstructed CFL and no donor, depletion, tension or other-reel
competitor. A disposable `1e-9 s` post-switch neighborhood, split at torque
knots, checks for another numerical limit. If any guard fails, the episode
keeps the feasible-side stop and records the failed restart status.

## Wound material ownership

The turn cut is calculated from the integrated inventory,
`cut=initial_cut+initial_length-ell`, with no independent label integration.
Original input records are preserved in `original_initial_records`. The live
active records are clipped at that cut; released material leaves their active
store and is not restored when the reel starts winding. Later winding steps
append material at the entering span stretch. The terminal step appends no
new packet at the turning reel. The active records must have no gaps or
overlaps, agree with the represented inventory, and meet a `1e-14 m` label
ULP guard. The terminal inventory-versus-midpoint-flux label residual must
be within `1e-13 m`. Active versus original remaining strain energy and the
old-material storage change versus midpoint stored-strain flux must each
agree within `1e-12 J`; these residuals are reported, not converted to heat.
If the other winding reel transfers less than `1e-14 reference m` on the
terminal step and its label cut cannot move at floating-point resolution, no
zero-width packet is invented. Its signed stored-energy discrepancy must be
below `1e-12 J`, is reported, and is included in the ordinary full energy
balance. A larger unresolved packet denies the transition before commit.

This one-sided terminal rule also preserves the rejected mixed-Heun
counterexample. For a linear turning flux from `-a` to `+a` over a step of
width `h`, simultaneous endpoint release and winding packets would each
transfer `a*h/2`. Their gross transfer is `a*h`, while the two true triangular
halves total `a*h/2`. Net inventory can still balance, hiding twice the gross
transfer and incorrect material ownership. The accepted terminal step uses
only release quadrature; winding begins on the next step. The regression
checks that no new winding record exists at the turn and compares gross
released and wound lengths separately.

## Independent traveling-wave reference

The tests use a separately derived material wave,
`x(S,t)=C+1.01*S+0.025*t+(0.005/k)*sin(k*(S-10*t))`, with
`k=pi/2`, `C=1.4735899778104424`, exact cell-average initial mass and
momentum, independently inverted boundary labels, and sampled exact time-only
torques. Its right reel turns once at `t=0.02 s` while the left keeps
releasing. The exact gross right release and winding lengths through
`0.04 s` are `0.00012502089456145615 m` and
`0.00014154148397321764 m`. Independent quadrature gives right final
inventory `1.0000165205894118 m`, speed `0.14388086041448067 rad/s`,
drive work `3.5045545691715055e-5 J`, pickup heat
`4.786903677307274e-10 J`, angular impulse
`0.0029011024282535602 N m s` and stored-strain flux
`-3.430766994215772e-9 J`. The active final wound strain energy has an
independent original-remainder plus deposition integral of
`0.000781246569233 J`. These are synthetic equation oracles, not physical
validation data.

Tests compare all three supported meshes (64/128/256 cells), refine CFL and
forcing knots independently, reflect the case left/right, and check mass,
energy, angular, heat and record ownership. They also require feasible stops
for a predictor-only crossing, simultaneous turns and labels too large to
resolve. The source-bound RunSpec and verified saved-run replay include a
recapture episode; the installed-wheel check runs an isolated recapture
outside the checkout. The solver and workflow identity advance to V2 so a
saved run cannot silently replay under the changed event policy.

This policy does not integrate a second turn, wind-to-release, slack,
depletion, bite engagement or 3D rolling contact. T2 remains incomplete as
an integrated strip/drive/roll model, and T3 transient deformation/contact,
compliant cross-width rolls, dynamic Blender/USD animation and broader guided
editor acceptance remain on the v1 critical path. Software readiness (S),
scientific validation (V) and site qualification (O) remain separate.
