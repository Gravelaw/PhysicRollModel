# V1 scope amendment: transient solver and interface

This amendment records the user's decisions after the directly attached
`PhysicRollModel-v1-plan.md` was used for W0/W1. It changes the project scope;
the attached plan remains the provenance record for the original W0–W6
sequence. The v1 pull request stays open through the full release gate. A
review agent will publish findings for the user, and merging requires the
user's explicit approval even if CI passes.

The following are now **required for v1**:

- A guided scenario editor for authoring, validation, execution, error recovery
  and reopening saved runs.
- Blender/USD **dynamic animation** driven by a new time-resolved solver. The
  requested solver covers all three layers: strip transport and roll/reel
  motion, coupled drive/span-tension/reel dynamics, and transient strip
  deformation/contact. Prescribed boundary histories must remain visibly
  distinct from calculated states. Steady snapshots with interpolated motion
  alone do not meet this requirement.
- Linux and Windows wheels, with Python 3.10 and 3.12 as the initial test
  versions unless a later explicit decision changes them.

## Revised dependency sequence

W0/W1 are complete. W2 packages resources and is tested in isolation. W3
remains the public checked workflow layer. Add a separately reviewed **T
track** after W1/W2, feeding W4 reproducibility and W5 interface integration:

1. **T0 — transient contract and numerical benchmark design.** Declare the
   cold, wide, symmetric, single-layer, plane-strain domain; field and state
   variables; prescribed inputs; initial/boundary conditions; units; frame and
   time coordinates; event rules; supported constitutive/contact laws; and
   failure conditions. Select the gap/roll-compliance boundary model and state
   whether exit thickness is prescribed or predicted before T3 begins. Freeze
   quantities, numerical tolerances, and independent analytical, manufactured
   or separately verified transient references for T2/T3 before interpreting
   results. `RunSpec`/`ResultBundle` gain versioned
   transient identities and explicit prescribed-versus-predicted fields.
2. **T1 — transport and rotating-body kinematics.** Track material position,
   roll/reel angle and radius/length inventory from declared speed or motion
   histories. Carry parcel/material-coordinate identities across entry, exit,
   reversal and re-entry; sampling frames must not advance material history.
   Verify zero-speed, reversal, continuity and time-step convergence. This is
   an executable solver layer, not a claim that supplied
   speed histories were predicted.
3. **T2 — coupled drive, span and reel dynamics.** Add drive/roll/reel inertias,
   torque and loss conventions, strip-span compliance/tension, changing reel
   radius/inventory and engagement/boundary transitions. Couple traction and
   motion with an explicit, documented integrator and energy/momentum
   residuals. Reversal and contact loss must not silently reuse a steady pass.
   Coupled-interface convergence and event timing are independent acceptance
   checks, not just comparisons of end states.
4. **T3 — transient strip deformation/contact.** Resolve time-dependent
   material transport, thickness and strain fields and roll/strip contact
   tractions in the stated plane-strain domain, with a declared constitutive
   law and friction/contact regularization. It must couple to T2 through
   force/torque and strip velocities, reject unsupported regimes, and report
   spatial/time refinement, conservation, independent transient references,
   coupled-interface convergence and steady-limit comparisons. Material history
   must remain bound to transported parcels through contact transitions. New
   strain-rate or thermal claims require their own material inputs and tests.
5. **T4 — verified saved animation.** Store bounded frames or field samples
   with their source-run digest, timeline, coordinate system, unit labels and
   missing-data markers. The Blender/USD adapter consumes this saved record,
   verifies identity, and animates transport, bodies and deformation/contact
   fields without treating prescribed inputs as predictions.

T0–T3 may proceed alongside W3 after contracts stabilize. W4 must save and
replay T results as well as static workflows. W5 requires the guided editor,
offline report and T4 animation to agree with saved values. W6 requires
installed-wheel workflow and animation checks on Linux and Windows, numerical
regressions for T1–T3, performance/memory limits, independent review and
published limitations. W6 cannot close by demonstrating only synthetic
kinematics or visually plausible movement.

The current steady/fixed-gauge models remain available as explicit alternatives
and comparison baselines. The new T solver does not turn prescribed exit gauge
or an assumed material history into a measured or qualified prediction.
Software/numerical readiness (S) and scientific/operational qualification (V/O)
remain separate. Independent rate-dependent material/contact data, drive and
reel parameters, transient observations with uncertainty, and a specified
accuracy decision are needed before claims of physical validation or mill use.

The next executable step is T0, with a frozen synthetic acceptance set and
integration interfaces. No algorithm, delivery date, or physical accuracy
claim is selected merely by this scope decision; those choices require
measured prototypes and specialist review.
