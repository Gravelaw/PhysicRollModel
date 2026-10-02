# Verification and portable handoff

Build date: 2026-09-30. Base commit: `64d6bf86bb49417d5c668dc28ef6287d3e7fad98`.
Development branch: `prototype/blender-cold-mill`, pushed to the private GitHub repository.
Original Apache-2.0 LICENSE verified byte-for-byte against the base commit. No PR, merge or
deployment. No rented GPU, credentials or plant connection.

## Dependencies actually used

| Component | Version | Required for |
|---|---|---|
| Python | 3.12.14 (code requires 3.10+) | Solver, unit tests, pure-Python smoke, packaging |
| Blender | 4.3.2, existing system installation | Scene, editable `.blend`, CPU Cycles render |
| NumPy | 2.3.5, preinstalled | Preview's analytical section |
| Matplotlib | 3.10.8, preinstalled | Composite preview |
| Pillow | 12.3.0, preinstalled | Matplotlib PNG handling |
| OpenUSD `usd-core` | 25.5.1, temporary isolated install | Independent USDA parser verification only |

The solver, CLI, scenario sweep, candidate study, mesh exporter and smoke test need no third-party
Python packages. Blender's embedded Python is used for `bpy`. No Blender/Omniverse installation
was performed. This Blender build reports `bpy.app.build_options.usd == False` and no
OpenImageDenoise support; the static USDA fallback and non-denoised CPU render were used.

## Checks completed in the build cloud

* Nineteen standard-library unit tests, all passing (see `artifacts/test_results.txt`): baseline
  regression, CLI, dimensional scaling, mass continuity, mechanical/tension/electrical power
  accounting, traction capacity, exact bite boundary, zero-draft limits, perturbation continuity,
  invalid types/keys/physics/foil/numerical magnitudes, constraint ranking and no-feasible outcome;
  plus calibrated-measurement formulas, stand/reel signs, provenance, rejection limits,
  sensor disconnect state and force/power reconciliation.
* Four named synthetic scenarios solved and saved. Twenty reduction/friction combinations
  screened; rejection reasons retained in `sweep.csv`, not replaced by clipped outputs.
* Blender reopened the saved scene and checked 78 unique equipment IDs (including presentation
  floor), four named rolls, gauges/coils/reels, 15 sensor markers, work-roll gap, true entry/exit strip gauge,
  width and a closed manifold strip mesh.
* Independent OpenUSD 25.5.1 reopened the USDA and checked 77 meshes (presentation floor excluded),
  Z-up/metres, `/Mill` root, topology/index bounds, material bindings, equipment/sensor IDs and true strip gauge.
* Overview rendered headlessly on CPU; composed preview visually inspected for equipment,
  legible labels and explicitly unequal-scale analytical roll-bite inset.
* Python compilation and `git diff --check`; original LICENSE unchanged.

These are software/artifact verification checks. They do not constitute scientific validation
against an actual aluminium mill. No flatness, residual stress or control-dynamic validation
is claimed. The stated model limitations remain after all tests pass.

## Repeat on the parent's separate cloud computer

Unpack the supplied archive, then run from its `PhysicRollModel` directory:

```bash
python scripts/smoke.py
python -m unittest discover -s tests -v
python -m physicroll scenarios/baseline.json
blender -b artifacts/mill.blend --python-exit-code 1 --python scripts/check_blend.py
blender -b -t 4 --python-exit-code 1 --python blender/generate.py -- --out /tmp/physicroll-rebuild
blender -b /tmp/physicroll-rebuild/mill.blend --python-exit-code 1 --python scripts/check_blend.py
```

For an independent CPU render, add `--render` to the generator command. This uses no GPU/display,
OpenUSD Python binding or native Blender USD support. On systems without `/tmp`, substitute any
writable directory. Run `blender --version` first and ensure `blender` is on PATH.

The first smoke command checks SHA-256 of bundled artifacts, including the new equipment/sensor outputs; rebuilding those files deliberately
can change bytes even when geometry is equivalent, so use a separate output directory. Check
physical geometry using the supplied Blender checker instead of comparing `.blend` file hashes.
The render need not be byte-identical across CPU/Blender builds.

Optional full USD parsing requires `usd-core` (see pinned requirements). The parent can inspect
and rebuild `.blend` and USDA without it. Preview recomposition is optional because the finished
PNG is included. A non-writable home cache can be handled with:

```bash
MPLCONFIGDIR=/tmp/physicroll-mpl XDG_CACHE_HOME=/tmp/physicroll-cache python blender/make_preview.py
```

To create another archive: `python scripts/package.py`. It deliberately omits `.git`, caches,
installed dependencies, logs and Blender backup files. Source and generated artifacts are included.
The parent independently rebuilt and rendered the first pushed commit `fee0d29` on its
separate cloud computer: 19 unit tests, the saved/reopened Blender scene, geometry and USDA
fallback passed. That run found the committed sensor manifest lacked the
`observation_shape` field now emitted by the source. This handoff regenerates the manifest
and checksum. The parent later accepted corrected commit `3d349418`: 19/19 unit
tests, exact transferred text blob hashes, regenerated sensor manifest/checksums,
CPU Blender scene rebuild/render/reopen and 78-ID geometry check passed. The parent could
not byte-verify the committed binary assets through its connector, although independent
regeneration worked. This document does not claim that binary checksum verification passed
on the parent computer. Library round-trip and extracted-archive smoke results are supplied in the handoff.

## Version 0.2 update

`physicroll/equipment.py`, `physicroll/observations.py`, `physicroll/sensors.py`,
`docs/sensors.md` and `docs/traceability.md` are included. The synthetic baseline
adds a 10 GN/m effective stand stiffness and two 0.7 m reels with assumed
800 kg·m² inertias. These are **illustrative**, not mill data. Run
`python scripts/build_extended.py` to regenerate equipment/sensor outputs without
Blender, or regenerate the scene to update its named sensor markers. The delivered
first archive remains available separately; this handoff is a versioned revision
of the same Library item. Verification of this revision is recorded in
`artifacts/build_environment.json` and bundled check logs. Parent-cloud acceptance
was completed against the corrected remote commit. The v0.3 candidate is a
separate unpushed branch; its independent software and numerical checks follow
below, and it has no physical aluminium validation.

## v0.3 candidate runs

```bash
python scripts/build_v03.py
python scripts/run_v03_study.py
python scripts/smoke.py
python -m unittest discover -s tests -v
```

The first command writes an optional result with material history, rigid-roll
slab force/torque, two-capacity heat budget, fluid closure status and supplied
profile. The second runs **separate synthetic sensitivities** at effective
friction 0.08/0.10/0.12, plastic heat fraction 0/0.5/1 and two successive
history increments. Results are retained in `artifacts/v03_foundations.result.json`
and `artifacts/v03_sensitivity.json`. These examples do not establish parameter
uncertainty or a calibrated prediction interval; real data and parameter fits
remain absent. See `v03-foundations.md` for the equations and distinct validity
gates.

## Specialist review and executed AA5052 study

The local `development/aa5052-mechanics-review` branch preserves the initial
candidate via `review/v03-before-mechanics-audit`. It has **44 passing tests**,
including 49 independent raw→SI targets, dimensional rejection tests, an
exponential-midpoint pressure reference, mechanical work/refinement, unequal-
capacity thermal exchange and a rechecked constrained search. Reproduction
commands and actual residuals are in `aa5052-study.md`; implementation verdicts
and source-equation limitations are in `mechanics-audit.md`.

The corrected generic optional slab baseline is approximately 1.739488 MN,
9.208335 kN*m per work roll, and 188.098520 kW for both work rolls. With 20 kW
net tension work, 159.449589 kW plastic work and 48.648825 kW slip dissipation,
its absolute work residual is 0.1054 W (5.61e-7 relative); this decreases under
refinement. The accepted v0.2 heuristic result is unchanged.

The AA5052 run considers 2,564 gauge candidates; 1,682 pass its assumed trust
region and solver screens. The baseline and selected schedule pass checked
512/1024-cell re-evaluation with relative work residual below 8e-8. This is
numerical verification; the measured slip mismatch and unresolved constitutive
conventions remain explicit. No thermal or final product-quality validation is
inferred.

The existing `.blend` reopened under CPU Blender 4.3.2 and passed 78-ID/gap/
true-gauge/closed-strip checks again. Regenerated sensor and equipment JSON match
the bundled accepted values exactly. A new reviewed archive uses a separate
filename, `PhysicRollModel-v0.3-reviewed-AA5052.zip`, preserving the original
candidate archive. The source tree contains no paid-service or plant connection.

## Optional contact/material increment from published 09d0d5b2

The published `development/contact-hardening-increment` at `1f1145df` adds optional spatial hardening
and circular roll compliance; default load/torque/slip match the reviewed baseline
regression. **54/54 tests pass**, including independent pressure integration and
bracketed radius checks, signed regenerative work, state continuity and limits.
The fixed-gauge structural and 15-hypothesis study ran at checked 512/1024 cells;
one zero-prior hypothesis rejected explicitly. See the
[report-sync packet](report-sync-contact-increment.md) for per-pass measured-data
residuals, worsened comparisons and unresolved source semantics.

A clean extracted source archive passed all 54 tests and the portable smoke test.
Its complete fixed-gauge study rerun matched all seven generated study files
byte-for-byte on this build environment. Source fingerprints and comparison
checksums are retained in `artifacts/contact_increment`. This is local package
verification, not a new independent computer acceptance or aluminium validation.
The existing scene and original reviewed archives remain unchanged.

## Optional flowing-strip energy handoff (local review increment)

The optional prescribed-boundary ledger in `energy_handoff.py` is tested by
`tests/test_energy_handoff.py`. The actual synthetic two-pass run is
`artifacts/flowing_energy_demo.json`; equations, units and source limits are in
[energy-handoff.md](energy-handoff.md). Numerical energy closure does not
validate temperature against an aluminium coil.

Full suite: **61/61 tests passed**, including seven new analytic and adversarial
energy tests. `scripts/smoke.py` passes the baseline/foundations and retained
artifact checks. The synthetic two-pass run gave strip exits 308.155685 and
314.904917 K, roll exits 295.581131 and 296.072356 K, and 10.8 kg/s fixed
mass flow. Thermal allocation residuals were −1.15e−9 and −7.13e−10 W;
combined mechanical-to-outlet residuals were 0.007842 and 0.015492 W,
inherited from the mechanics integration. The explicit nonthermal plastic work
allocations were 176676.876 and 151649.051 W. All of these temperatures and
boundaries are synthetic.

The clean extracted review archive passed 61/61 tests and smoke checks. Its
regenerated two-pass output matched `artifacts/flowing_energy_demo.json`
byte-for-byte (SHA256 `70ba963e8a53d718dee4a14f81aa488072f888a73547982488f214b54cebd5c4`).
All bundled asset checksums and executable-source fingerprints matched in that
extraction. This is build-environment repeatability; no independent cloud
computer or aluminium thermal experiment has accepted this new increment yet.

## Specialist energy review after d665cce

The [same-environment specialist audit](energy-specialist-audit.md) corrected four
input-contract/numerical-boundary defects and increased coverage to **67 tests**
(13 energy tests). The two-pass synthetic output is byte-identical to the prior
increment. Clean extraction, complete tests, smoke and source/asset fingerprints
are rechecked for the corrected package. This is not independent consumer acceptance.

## Optional passive-contact development increment

`tests/test_passive_contact.py` adds an independent constant-heat-capacity
solution, passive-sign and entropy checks, zero/equal/reversed-temperature
limits, variable-cp and large-conductance cases, temporal refinement,
W/K and throughput scaling, mixed-mode/declared-fitted-law rejection,
property-domain rejection and byte-identical legacy-demo regression.
`scenarios/passive_contact_demo.json` and `artifacts/passive_contact_demo.json`
are a separate two-pass synthetic numerical example. The [equation/source/test
map](passive-contact.md) distinguishes this optional numerical closure from
the 2 October 53-page report snapshot and from measured validation.

The full suite passed **73/73** tests and `scripts/smoke.py` passed after the
extreme-conductance and property-bracket corrections. The old prescribed-boundary demo remains
byte-identical to its retained artifact (SHA256 `70ba963e8a53d718dee4a14f81aa488072f888a73547982488f214b54cebd5c4`);
the new passive demo SHA256 is `1ec69cf7cec240845f5c251bab49b11f9989f999289df085c49166ec245a3942`.
Both are synthetic. Independent specialist review exposed the initially
nonfinite `G=1e308 W/K` result; finite derived-power and entropy guards now
reject it. The reviewer then checked dimensions, cancellation, monotonic root
and a seeded 2,000-case parameter sweep: 1,429 accepted cases met the
diagnostic invariants, while 571 rejected at the declared guards. A supplied
conductance's declared conductive scope still requires source review.

Independent Astra review reproduced a second numerical defect: a valid
constant-cp interior root was rejected because reconstructing enthalpy at a
Q bracket endpoint differed by a few floating-point units from its knot.
Endpoint-only knot-scale tolerance now handles that arithmetic difference
without relaxing the public property inverse; the exact analytic case is a
regression test. Astra's follow-up review found no remaining concrete issue:
all 19 energy/passive-contact tests passed, and 10,000 seeded admissible
constant-cp cases matched an independent analytic solution with maximum
normalised contact-power error about `1.46e-10`. This is numerical correction,
not an empirical calibration.
