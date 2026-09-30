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
and checksum; acceptance of the corrected commit remains a separate gate. The parent could
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
remains pending a user-approved file attachment because Library scope differs.
