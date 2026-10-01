# Report-sync packet: prescribed-boundary flowing energy handoff

Working branch: `development/flowing-energy-handoff`, created from published
`1f1145dfda0c6fd70b0be0abc379dcadb26e10d5`. The final local commit is
provided in the delivery message. No push or merge is part of this increment.

## Equations and implementation to mirror

[E1–E4 and unit/validity table](energy-handoff.md) are the authoritative report
text. In brief, flowing strip enthalpy `m_dot*ΔH` [W] receives declared plastic
heat, declared fraction of **both-interface** solid-slip dissipation, signed
roll-to-strip contact heat and supplied cooling export. A separate finite roll
thermal body takes the remaining solid-slip heat and the exact opposite contact
heat. `(1-beta)*P_plastic` remains an explicit nonthermal work allocation. The
sum closes against checked mechanical plastic/slip work; mechanical work residual
is reported separately and also through a combined outlet residual.

Code: `physicroll/energy_handoff.py` (`HeatCapacityCurve`, `PassHeatBoundary`,
`handoff_pass`); synthetic inputs: `scenarios/flowing_energy_demo.json`;
executed run: `scripts/run_flowing_energy_demo.py` and
`artifacts/flowing_energy_demo.json`; analytic/adversarial checks:
`tests/test_energy_handoff.py`. Fluid observation is attached as a record only;
its identity does not change model force, heat partition or temperatures.
Existing `thermal.py` remains a distinct prescribed-mass step and is not used
as an advecting strip control volume.

## Actual numerical demonstration

All values below are **synthetic**. Generic 2.00 → 1.50 → 1.20 mm strip,
1.00 m width, original synthetic density 2700 kg/m³, initial strip 300 K,
initial roll 295 K, two 5 s aggregate roll steps. Input fractions are
`beta=0.2`, `f_strip=0.6`, supplied contact heat to strip −2.0/−2.3 kW,
strip cooling 5.0/5.5 kW and roll cooling 3.0/3.2 kW. They are not aluminium
calibration values or recommended cooling settings.

| Pass | Strip exit K | Roll exit K | Mass flow kg/s | Plastic work W | Both-interface slip W | Nonthermal plastic W | Thermal allocation residual W |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 308.155685 | 295.581131 | 10.8 | 220846.094 | 68714.339 | 176676.876 | −1.15e−9 |
| 2 | 314.904917 | 296.072356 | 10.8 | 189561.314 | 58237.543 | 151649.051 | −7.13e−10 |

These are software outputs from the supplied synthetic boundaries, not measured
strip/roll temperatures. Combined mechanical-to-outlet residuals are about
0.007842 W and 0.015492 W, inherited from the checked slab integration;
contact transfers cancel exactly in the summed budget.

## Evidence versus validation

The new focused tests check exact piecewise heat-capacity integration/inversion,
constant-`c_p` analytic strip and roll temperatures, zero sliding, partition
endpoints/sum, contact sign, mass/power scaling, material and roll-state carry,
input unit sanity, property-range rejection and mechanical work identity.
Run commands and final complete test counts are recorded in
[verification](verification.md) after execution. The source AA5052 paper has
force/slip observations but no usable temperature, coolant or roll-thermal
calibration record. The AA8015 [primary publisher article](https://doi.org/10.1007/s00170-018-2811-2)
is a separate alloy/FE case; its subscription preview gives no coefficients
for this executable ledger. Equations E1–E4 are explicitly derived as a
reduced first-law balance, not a claim to reproduce that article's FE model.

No temperature feedback enters `PowerHardeningLaw`, slab pressure, friction,
roll flattening or product temper. The source speed/slip and material-history
ambiguities in [contact increment](report-sync-contact-increment.md) remain.
Physical validation requires calibrated strip/roll thermometry, alloy-specific
properties, fluid boundaries and independent coils. Full film/lubrication,
roll/strip temperature fields, thermal crown, flatness, microstructure and
fracture are outside this bounded increment.

The review archive clean extraction ran 61/61 tests and portable smoke checks,
matched all bundled asset/source hashes, and regenerated the two-pass JSON
byte-for-byte (SHA256 `70ba963e8a53d718dee4a14f81aa488072f888a73547982488f214b54cebd5c4`).
The archive is a new review deliverable; earlier v0.3 and contact-increment
archives and GitHub branches remain reproducible.

## Specialist review correction after d665cce

The [specialist audit](energy-specialist-audit.md) is part of this packet and must
be reflected in the report. Same-environment review found and fixed four defects:
inconsistent endpoint summation in cp inversion, acceptance of unsupported
temperature-feedback metadata, acceptance of false/negative mechanical residual
metadata, and missing inlet/outlet enforcement of the assumed mechanical
temperature envelope. E1–E4 and the synthetic numerical example are unchanged.
The code now uses common cp knot integrals and verifies the source work error
against the slab's own normalization before considering thermal powers.

**67/67 tests pass (13 energy tests).** Added checks cover decreasing cp, 100
seeded curves and strict knot/domain handling; finite-roll half-step composition
and flowing-strip duration invariance; W-to-J accounting; 10^3/10^6 scaling;
zero mechanical sources and pure contact; regenerative drive work; malformed
metadata and material history. The synthetic example remains byte-identical
with SHA256 `70ba963e8a53d718dee4a14f81aa488072f888a73547982488f214b54cebd5c4`.
These results are specialist numerical verification in the original environment,
not independent consumer acceptance or thermal/material validation. The roll cp
storage approximation neglects thermoelastic work; prescribed signed contact
power does not establish a passive contact law or second-law admissibility.
