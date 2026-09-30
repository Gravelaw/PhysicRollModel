# Append-only mechanics findings log

Entries describe findings and evidence at the time of the named increment. Later
results must be appended, not substituted for earlier outcomes. Numerical
verification is distinct from experimental validation.

| Date / increment | Finding or scope decision | Equation / assumption | Code / test | Retained result |
|---|---|---|---|---|
| 2026-09-30 / contact increment from 09d0d5b2 | A spatial-strength extension needs the derivative term; pass-mean model was not wrong under its own assumption | M1–M4 in `contact-increment.md`; integrate z=q-K to retain hK' | `materials.py::BiteHardening`, `slab.py::_solve_grid`; constant-law limit, independent variable-strength pressure and state/work tests | `structural_comparisons.json`: rigid spatial has lower average force/slip residual than rigid mean in the declared baseline hypothesis, but pass3 force worsens |
| 2026-09-30 / same | Contact radius must be coupled to force and kept distinct from shaft radius | M5–M7; Hitchcock circular approximation, assumed E/nu; no full elastic kinematics | `contact.py`, `slab.py`; independent bisection, large-E limit, width/speed scaling, nonconvergence, radius envelope | Coupled solution converges; adding flattening worsens aggregate comparison residuals in the declared baseline. Not adopted as a calibrated default |
| 2026-09-30 / initial fine-grid trial | A specific iterated circular radius rounded computed entry h above prescribed h0 by one ULP, causing a false hardening-domain rejection | Exact entry boundary must equal supplied full h0 | `slab.py::geometry`; `test_fine_grid_coupling_entry_endpoint_and_baseline_regression` | Initial 512/1024-cell combined trial aborted with `positive full thickness with local <= entry required`. Exact boundary return fixes it; subsequent checked run succeeds. No out-of-range material value is clipped |
| 2026-09-30 / same | Signed regenerative torque must survive integration | M6–M7; positive tensile work may exceed plastic+slip demand | `test_regenerative_signed_torque_and_zero_draft_limit` | Negative drive torque/power with positive slip dissipation and small work residual; no drive feasibility claim |
| 2026-09-30 / same | Zero prior strain with zero-offset Hollomon conflicts with reported positive tension | Source Eq2 plus explicitly assumed local uniaxial boundary admissibility | `simulate_schedule`, `hypotheses.json` | `zero_prior` rejected at pass1; no invented initial yield or friction fit |
| 2026-09-30 / same | Radius, constitutive and speed interpretations remain unidentified | Source Table1 radius vs Eq6 prose; unknown speed location, history and stress/strain pairing | `run_contact_increment.py`; 15 explicit sensitivities and speed invariance test | All force/slip residual-sign envelopes span zero across tested structural/hypothesis cases. No sign conclusion survives every sampled interpretation; throughput/power vary with speed mapping while load/slip are invariant in this rate-independent model |
| 2026-09-30 / reporting correction | Reviewed branch was published; 2024-only citation omitted journal lineage | 2025 journal DOI 10.1016/j.euromechsol.2025.105712; equation numbers remain 2024 v1 Eqs21–28 | `mechanics-audit.md`, `contact-increment.md`, `report-sync-contact-increment.md` | Parent checked bibliography reconciled with arXiv/author-university metadata; no claim that journal equation numbering was rechecked |

Run evidence lives in `artifacts/contact_increment/`; source fingerprints and file
hashes are retained there. Defaults retain the reviewed baseline numerically. This
increment adds optional structural tests and comparisons without parameter fitting,
new plant observations, widened optimisation or publication.
