# Specialist audit of the flowing energy handoff

Reviewed input commit: `d665ccef8af82c5b39451ec7dd0476776e9b0c95`.
This review and all numerical runs occurred in the **same development environment**.
It is not independent consumer acceptance or experimental aluminium validation.
The correction is a local continuation of `development/flowing-energy-handoff`.
No new physical closure, empirical fit, force-temperature feedback or publication
is introduced.

## Findings, corrections and evidence

| Finding reproduced at d665cce | Correction | Regression evidence |
|---|---|---|
| A valid upper property endpoint rejected: knots 250/300.3/350.7/420 K with cp 707.02/764.20/886.72/578.96 J/(kg K). Forward integration and inverse accumulated segment areas differently | Use shared, accurately summed knot enthalpies and exact knot returns; values beyond the final enthalpy still reject without clipping | `test_property_knots_decreasing_cp_and_strict_endpoints`: this curve, independent decreasing-cp analytic integral, 100 seeded curves, all knots/interior points and next-float domain rejection |
| `temperature_feedback=True` accepted when reference/input temperatures matched, then output claimed no feedback | Require the source metadata to explicitly say `False` | `test_reject_false_mechanical_residual_and_feedback_metadata` rejects true, missing/None and numeric zero |
| Negative relative mechanical residual accepted; a supplied relative value could hide the magnitude of the actual work error | Recompute the slab normalization before thermal scales enter; reject negative, inconsistent and above-tolerance residual metadata | Same test rejects negative/false/too-large fields and a 1000 W source-work perturbation; regenerative signed-power test remains admissible |
| Outlet 308.156 K accepted even after source material envelope was narrowed to 299–301 K | Enforce explicit increasing mechanical temperature envelope at both thermal inlet/outlet; retain the separate cp property domain | `test_enforce_material_temperature_envelope_and_history` rejects the reproduced case, out-of-range inlet, missing/malformed intervals and broken strain/history continuity |

These were input-contract and numerical-boundary defects. None changes the
published mechanical solver or its baseline parameters. The original two-pass
synthetic output remains byte-identical after correction.

## Dimensional and physical verdicts

| Quantity or claim | Audit verdict and limit |
|---|---|
| Flowing strip versus roll capacity | Correct under constant supplied powers: kg/s times J/kg is W; fixed roll kg times J/kg divided by s is W. The roll effective mass aggregates both interfaces. Roll half-step composition agrees with a full step; strip outlet is independent of roll-step duration |
| Contact and source signs | Contact to roll is exactly the negative of contact to strip. Both-interface solid-slip W is allocated once. Negative drive power is allowed when tensile work supplies the mechanical demand; negative plastic/slip dissipation rejects |
| Combined energy | Mechanical roll+tension work closes against strip enthalpy flow, roll storage, cooling exports and unconverted plastic work, subject to the separately retained mechanical quadrature residual. Independent constant-cp checks also integrate the budget in J over the duration |
| Nonthermal plastic work | Explicit remaining allocation `(1-beta)*P_plastic`, not an identified microstructural stored-energy state, defect density or accumulated material energy model |
| cp(T) | Positive piecewise-linear curve in supplied SI units, integrated/inverted with shared segment boundaries. Separate strip/roll properties and strict domains. Solid roll cp is an effective sensible-energy approximation neglecting expansion/thermoelastic work |
| Units and scaling | Simultaneous 10^-3, 10^3 and 10^6 power/flow/mass scaling preserves temperatures; multiplying roll duration and mass by 10^3 preserves roll rise. Numeric fields accept SI only. Sanity limits cannot identify every plausible but wrongly labelled number |
| Zero-source/slip limit | No source and no boundary heat leaves temperatures unchanged; pure contact exchanges equal/opposite energy. Zero-slip heat remains zero. These ledger fixtures do not establish a zero-draft slab solution; that solver still excludes it |
| Material state | Alloy, temper, equivalent strain and history align and advance once; temperature is carried. No recovery, anneal, texture, grain, fracture or certified temper is inferred |
| Time and stability | Exact enthalpy update for constant prescribed powers has no explicit contact-coefficient stability condition. It supplies no dynamic contact law, transient strip residence model or guarantee that boundary powers are physically attainable |
| Thermal validation | Unsupported: beta, slip partition, cp curves, roll mass and cooling/contact powers remain synthetic. First-law closure alone does not establish second-law admissibility of a prescribed boundary or aluminium temperature accuracy |

No new equation was borrowed from an empirical paper in this correction. E1–E4
remain the declared reduced first-law balance in [energy-handoff.md](energy-handoff.md),
whose source table distinguishes the AA8015 FE research lead and AA5052 mechanical
observations from this synthetic ledger.

## Executed evidence and reproduction

The complete suite passed **67/67 tests**, including **13 energy tests**; the
previous suite had 61 tests. Actual synthetic output is retained in
`artifacts/flowing_energy_demo.json`: strip exits 308.155684548 and 314.904916682 K,
roll exits 295.581130817 and 296.072355660 K, and 10.8 kg/s through both passes.
Thermal residuals are -1.1496e-9/-7.1304e-10 W; combined mechanical-to-outlet
residuals are 0.00784196/0.01549187 W. The latter come from mechanical integration.

```bash
python -m unittest discover -s tests -v
python scripts/smoke.py
python scripts/run_flowing_energy_demo.py --config scenarios/flowing_energy_demo.json --out /tmp/energy-review.json
```

The final review package is checked by clean extraction, rerunning the complete
suite and smoke, source/asset hashes, and byte comparison of the regenerated
two-pass output. The delivery supplies the exact local correction commit and
archive hash. Library replacement retains the prior archive's identity and
version history; the earlier source commit remains available locally.
