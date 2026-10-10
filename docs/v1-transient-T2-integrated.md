# Bounded torque-driven elastic span and right reel

**Status:** Integrated T2 software verification increment. This model is a
synthetic taut-span research case with one driven right reel, a fixed spatial
span, no rolling bite and no physically validated reel contact. It does not
close the full v1 T2, T3 or animation gates.

The public workflow is `torque_driven_span_reel_t2`. Its source-bound example is
`scenarios/v1_torque_driven_span_reel_t2.runspec.json`; the same example is
inside the wheel. `python -m physicroll.bundle_cli create --run-spec
scenarios/v1_torque_driven_span_reel_t2.runspec.json --out /tmp/t2-run`
creates a verifiable, replayable saved run. The example uses declared synthetic
elastic constants and prescribed applied torque, with predicted span and reel
speed. A source hash mismatch rejects execution.

## State and signs

The span occupies a fixed 1 m spatial interval. In SI units, the cell-average
conserved state is \(U=(a,\mu av)\), where \(a=1/\lambda\), \(v\) is material
velocity, \(\lambda>1\) is stretch, \(\mu=0.1\) kg per reference metre,
\(EA=10\) N and \(c=\sqrt{EA/\mu}=10\) m/s. Torque is signed about a fixed
winding-positive axis; motoring/regenerative power is classified by the sign
of \(\tau\omega\). The finite-volume flux is
\(F=(q,\mu qv-T)\), with \(q=v/\lambda\) and
\(T=EA(\lambda-1)\). Positive right-port \(q\) winds; negative \(q\)
releases. The left end is fixed or receives one prescribed incoming
characteristic history. Applied torque is a time-only input, interpolated
linearly or by declared cubic Hermite knot slopes. Initial fields, retained
wound records and all forcing are serialized, with no exact-solution callback
inside the stepper.

For Hermite inputs, the stepper computes the maximum absolute second time
derivative on each proposed within-knot interval. It caps the step so the
trapezoidal applied-torque impulse error bound `M h³/12` sums to at most
`1e-8 N m s` over the declared duration. For an incoming-characteristic
Hermite history it separately bounds departure from the endpoint chord by
`M h²/8 ≤ 1e-5 m/s`. The result reports the accumulated torque bound and
maximum incoming bound. A collapsed step or exhausted accepted-step budget
rejects the episode. These are forcing-resolution limits, not an accuracy
bound for the nonlinear coupled solution or a substitute for event checks.

At the right port, the outgoing span characteristic is \(r=v-c\lambda\).
For winding, \(v_s=R\omega\), \(\lambda_s=(v_s-r)/c\) and
\(q=v_s/\lambda_s\). The accepted Heun stages deposit immutable packets
carrying their own material labels and computed stretch. For release,
\(\lambda_w\) comes from the exposed stored record, then
\(q=R\omega/\lambda_w\), \(\lambda_s=r/(q-c)\), and
\(v_s=q\lambda_s\). A trial holds that donor fixed until a located layer
boundary is accepted; only then can the next stored record supply the port.
This is one incoming mechanical boundary condition, not a prescribed release
span speed.

The idealized annulus is \(R^2=R_c^2+\kappa\ell\) and
\(J=J_c+\mu(R_c^2\ell+\kappa\ell^2/2)\), where \(R_c=0.1\) m,
\(J_c=0.01\) kg m², and \(\kappa=0.001/\pi\) m² per reference metre.
Reel dynamics obey
\(J\dot\omega=\tau-RT_s+\mu qR(v_s-R\omega)\). The last term is
material angular momentum transfer, not another commanded torque. Wound
strain energy is owned by the retained labels. During mismatched release the
chosen pickup closure assigns
\(D=(-q)(EA-\mu q^2)(\lambda_s-\lambda_w)^2/2\) W to a separate
nonnegative modeled dissipation ledger. This closure is an explicit model proposal, not a
calibrated reel-contact law. Its derivation and alternatives are in
[the pickup decision](v1-transient-T2-pickup-decision.md).

## Episode and evidence

The bounded implementation accepts 64, 128 or 256 span cells, duration at
most 0.1 s and at least 1 ns, forcing knots at least 0.1 ns apart, and
declared CFL limits 0.35, 0.175 or 0.0875. It checks
positive subsonic states in cells, reconstructed traces and ports, and stops
at the first zero-tension root. It splits at torque/boundary knots, the first
winding-to-release reversal, stored-donor endpoints and the declared cut.
A later release-to-winding reversal stops explicitly because the second
transition is not yet supported. Root brackets, signed donor cut residuals,
storage-ownership bounds, modeled dissipated energy and numerical balance defects are
reported. Repeated snapshot requests read the first accepted state at or
after the requested time; their actual and requested timestamps are distinct.
Snapshots never create a step or alter wound history.

Independent synthetic oracles in `tests/test_transient_t2.py` include:

- A constant mismatched release with known \(q=-0.1\) reference m/s,
  \(\lambda_w=1.01\), \(\lambda_s=1.001\), 0.01 m released over 0.1 s,
  \(4.049595\times10^{-6}\) J dissipated and \(-5\times10^{-6}\) J
  wound-strain-energy change.
- A time-only manufactured torque driving a matched standing wave through
  reversal near 0.02 s and return to the original cut near 0.04 s. The span
  fields, events and modeled dissipation are checked at 64, 128 and 256 cells and at three
  CFL limits on a fixed grid. Forcing interpolation is checked separately.
- An off-knot transition to an unequal stored stretch, perturbations to torque
  and original donor history, a second reversal, first tension loss, and
  observation-cadence invariance.

The public ResultBundle keeps prescribed and predicted roles distinct and
reports internal balance diagnostics. It leaves `numerical_verification` as
`NOT_ASSESSED` for an arbitrary case that only closes its own balances;
the independent benchmark evidence is the test suite, not a property of
every user-supplied episode. Scientific qualification and operating readiness
remain `NOT_ASSESSED`.

## Remaining gates

The model has one reel, a fixed left spatial boundary, no drive train, strip
roll bite, 3D deformation, contact, compliant rolls, thermal response or
slack continuation. The release pickup law needs a resolved contact model or
independent data before physical use. T2 restart/checkpoint support and
broader input/parameter domains are still pending. T3 must couple a genuine
full 3D transient strip/contact engine, then T4 must animate verified saved
fields. The [critical path](v1-integration-critical-path.md) and
[scope amendment](v1-scope-amendment-2026-10-10.md) remain the v1 gates.
