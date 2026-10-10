# V1 transient integration critical path

**Status: pre-engaged two-reel increment.** The executable T2A1–T2A9
modules remain restricted verification fixtures. The
[integrated T2 increment](v1-transient-T2-integrated.md) now combines a
torque-driven elastic span and right reel with winding, matched or mismatched
release, stored-label ownership and an explicitly idealized dissipative
pickup law. The [two-reel interval](v1-transient-T2-two-reel.md) adds two
independent prescribed drive torques, predicted reel speeds, mirrored
material-label ownership and separate ledgers. Its optional one-sided
reversal, internal-donor and tautness-limit stops save a feasible accepted
state; their numerical brackets do not certify physical event times. Both
increments have source-bound saved runs and independent synthetic checks.
Depletion, physical event timing, post-event transition, bite/drive engagement, restart, T3 contact
and full v1 coupling remain open.

## Next decisions and executable gates

1. **Freeze an integrated strain-bearing T2 formulation.** The
   [stored-strain pickup decision](v1-transient-T2-pickup-decision.md)
   records two reviewed modeling paths and their scientific limits. Define the
   supplied drive torque, both end ports, speed/tension characteristic count,
   reel state and original stored-strain ownership, including material
   pickup at reversal. Derive the interface transition law for a mismatch
   between outgoing span state and exposed wound stretch. State its
   momentum, angular momentum and energy accounting, admissibility and
   event conditions. The matched T2A9 case must be recovered as a limit;
   T2A7 must be recovered on append-only winding. Independently review
   these equations and freeze separate torque-driven reversal and
   mismatch references before implementing them. Slack, tension zero,
   release, and recapture require distinct accepted-state transitions.
2. **Build the integrated T2 solver and public transient contract.** Own
   span and reel mass once, use the same numerical port flux on each side,
   couple drive dynamics to predicted motion, and store accepted time,
   material labels, wound intervals, angular states, events and balance
   ledgers. Add versioned `RunSpec`/`ResultBundle` transient identities,
   prescribed-versus-predicted roles, saved-run verification and restart.
   Run the T2A7/T2A9 limiting cases, independent dynamic reversal cases,
   three-grid field and event refinement, interface work/impulse residuals,
   and changed-frame-cadence and restart checks. This closes strain-bearing
   T2 software verification only within its declared taut domain.
3. **Freeze and prototype T3 full 3D mechanics.** Resolve the outstanding
   [first full 3D elastic/contact verification candidate](v1-transient-T3-3d-verification-candidate.md)
   before implementation. Resolve the outstanding
   finite-strain material law, unilateral finite-sliding friction/contact,
   free-edge and entry/exit states, rigid-gap geometry, and dynamic elastic
   roll/stand supports. Test lightweight and numerical/native routes on the
   same full 3D width-resolved cases before selecting a shipped route. The
   first gate covers 3D material point/patch tests, objectivity, elastic wave,
   contact impact/sliding work, mesh/time refinement and history ownership.
   The compliant gate additionally covers barrel bending modes, vibration,
   support impulses, width pressure/gauge fields, lift-off and re-contact.
   Do not represent a stack of uncoupled slices as the shipped full 3D mode.
4. **Couple T2 and T3.** Declare one owner for each strip material region
   and structural mass, exchange conjugate traction/velocity and
   torque/angular velocity at common accepted times, and test monolithic
   and partitioned elastic cases for impulse, work, reflected waves,
   interface convergence and event time. A rigid-gap result cannot certify
   the elastic-roll mode. Check the independent steady limit separately.
5. **Deliver saved animation and guided workflows.** T4 writes verified
   frames/fields from accepted solver states with digest, time, coordinates,
   units and missing-data flags. Blender/USD animates strip transport,
   deformation/contact and roll/reel/stand motion from that record. W4
   replay, W5 editor and offline report must open the same checked transient
   run and distinguish imposed histories from calculated states. W6 then
   checks Linux/Windows source and installed wheels, bounded performance
   and memory, numerical regression, and independent review.

The right-reel pickup transition is independently reviewed and implemented as
a labeled model proposal. Step 2 next needs a physical shared earliest-event
scheduler for the two-reel port and compatible engagement, with independent work/impulse
and event gates; the current two-reel Episode is not full T2. The first T3 full 3D elastic/contact
candidate has equation-level independent review, while its numerical engine
and contact enforcement remain to be built. No synthetic fixture supplies
material calibration or transient mill measurements. Software verification
(S), scientific physical validation (V), and site qualification (O) have
separate gates.
