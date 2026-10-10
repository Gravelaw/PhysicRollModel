# PhysicRollModel

A runnable **generic, synthetic four-high aluminium cold rolling demonstrator**: an independent
Python process model, disconnected sensor/equipment bookkeeping, parametric Blender equipment,
an editable scene and portable USD geometry.
This is an initial digital-twin prototype, **not a plant replica or validated production model**.
No actual material/plant data, live connections or production setpoints are included.

![Generic mill and analytical roll bite](artifacts/preview.png)

## Start here — no dependencies or Blender needed

Use Python 3.10+ (tested with 3.12.14), from this directory:

```bash
python scripts/smoke.py
python -m unittest discover -s tests -v
python scripts/check_installed_wheel.py
python -m physicroll scenarios/baseline.json --output artifacts/baseline.result.json
python -m physicroll --run-spec scenarios/v1_checked_pass.runspec.json --output checked-result.json
python -m physicroll --run-spec scenarios/v1_shao_benchmark.runspec.json --output benchmark.json
python scenarios/run_sweep.py
python scripts/build_extended.py
```

The smoke test uses only the standard library and checks bundled artifact hashes. Scenario
values are **SI**: metres, seconds, kilograms, pascals, newtons, watts, radians. Edit a copy of
`scenarios/baseline.json`; retain `synthetic: true`. Invalid and unsupported cases raise a
clear error. The JSON schema is in `schema/`; additional physical checks are in Python.

The synthetic baseline (2.00 → 1.50 mm, 1 m width, 2 m/s entry, R=0.25 m) gives approximately
2.20 MN separating force, 11.84 kN·m per work roll, 220.9 kW roll mechanical power and
10.8 kg/s mass flow. These numbers demonstrate the stated assumptions, not predicted plant
performance. The 20-case sweep logs rejected cases as well as accepted results.

## Build or inspect the Blender scene

Tested with **Blender 4.3.2**, background Cycles rendering on CPU, no display or GPU required:

```bash
blender -b -t 4 --python-exit-code 1 --python blender/generate.py -- --out artifacts --render
blender -b artifacts/mill.blend --python-exit-code 1 --python scripts/check_blend.py
```

Omit `--render` for a quick build, or supply `--scenario scenarios/higher_reduction.json`.
Use a different `--out` directory for each scenario. Open `artifacts/mill.blend` in Blender
to edit individual equipment, materials, lights and camera. It contains work/backup rolls,
housings, chocks, reels/coils, strip, guides, conceptual gauge heads and cyan sensor markers. R and width drive
layout; some clearances remain fixed. Supported scene radius: 0.15–0.4 m; width: 0.5–1.8 m.

The scene uses the supplied synthetic reel radii; radii must also fit its generic clearance.
The 3D strip is true gauge with a curved roll bite. The preview's separately computed
analytical inset uses unequal X/Z scales and is visibly labelled. It is not a stress map.
The coils are static snapshots, not a simulated winding/transport sequence.

Optional preview composition (installed versions are pinned):

```bash
python -m pip install -r requirements-preview.txt
python blender/make_preview.py --out artifacts
```

The provided cloud Blender build lacks native USD and OpenImageDenoise. Rendering disables
denoising. Export falls back to the included **static USDA mesh/material writer**, which
needs no `pxr` module. `artifacts/mill.usda` was independently reopened with OpenUSD 25.5.1:
77 meshes, stable equipment and sensor IDs, valid topology/material bindings, true strip gauges,
`metersPerUnit = 1`, `upAxis = Z`. X rolls forward, Y spans width. Native USD export is
attempted first where available; status is written to `scene_status.json`.

Optional independent USD verification (not needed to generate or inspect the `.blend`):

```bash
python -m pip install -r requirements-verify-usd.txt
python scripts/check_usd.py
```

`check_usd.py` targets the included fallback's `/Mill` hierarchy. Native Blender export
on another build can have a different hierarchy and requires corresponding verifier changes.

## Contents and portability

| Path | Purpose |
|---|---|
| `physicroll/` | Standard-library solver, measurement conversions, synthetic stand/reel snapshot, disconnected sensor registry, offline candidate study |
| `scenarios/`, `schema/` | Explicit synthetic inputs, sweep driver, JSON contract |
| `blender/` | Parametric generator, fallback USDA exporter, preview composition |
| `tests/`, `scripts/` | Numerical tests, dependency-free smoke test, Blender/USD checks |
| `artifacts/` | `.blend`, `.usda`, overview/preview PNGs, process and equipment results, sensor manifest, sweep, IDs, build evidence |
| `docs/model.md` | Equations, SI conventions, rejection domain and unsupported physics |
| `docs/research.md`, `docs/sensors.md`, `docs/traceability.md`, `docs/capabilities.md`, `docs/next_modules.md` | Sources, sensors, equations, capability boundary and next research modules |
| `docs/verification.md` | Actual commands/results, dependency versions and transfer checks |

For a second computer, unpack the supplied archive, run `python scripts/smoke.py`, then
the unit tests. The included `.blend` and preview need no regeneration. On a machine with
Blender, use `--out /tmp/physicroll-rebuild` for an independent headless build without changing
the bundled artifacts. The source archive excludes Git metadata, credentials, dependencies
and temporary files. See `docs/verification.md` for detailed rebuild/transfer instructions.

## Scope and limitations

This version enforces mass and energy balance, conservative bite/traction screening, and
finite/physical input bounds. The added stand/reel snapshot uses synthetic stiffness, coil radii
and inertias; stand reaction is the existing bite force. Sensor positions are generic markers,
with all actual readings, timestamps and uncertainty unknown. Observation helpers cover local
tension force/stress, qualified wrap reaction, hydraulic thrust, mass flow, slip and signed reel
torque, with limits documented in `docs/sensors.md`. Its **pressure, extra dissipation and neutral-speed closures
are illustrative**. Torque is an energy-equivalent estimate, not a signed-traction solution.
No published accuracy or plant calibration is claimed.

The [capability matrix](docs/capabilities.md) maps current calculations and future friction,
mass-flow, thermal, metallurgy and fracture research. Foil is excluded (exit gauge below 300 µm is rejected). Roll flattening/bending, mill stretch,
shape/flatness, residual stress, thermal effects, alloy hardening/metallurgy and control
transients are not solved. Exit gauge is prescribed, not predicted from a screw gap.
Zero draft is unloaded transport, not temper rolling. Friction needs joint force/torque/slip
identification; geometry and passing unit tests do not validate rolling accuracy.

Apache-2.0; original `LICENSE` retained unchanged. The development branch
`prototype/blender-cold-mill` is pushed to the private repository. No pull request, merge
or deployment is performed.

## v0.3 computational foundations candidate

The separate local branch `development/thermomechanics-v0.3` adds opt-in,
standard-library-only material-history, rigid-roll slab, thermal-budget,
lubricant-observation and supplied-profile modules. It does **not** modify
the accepted v0.2.1 solver or its Blender scene. Every sample value remains
synthetic. Equations, primary paper and OEM links, units, tests and missing
validation are detailed in [v0.3 foundations](docs/v03-foundations.md).

```bash
python scripts/build_v03.py
python scripts/smoke.py
python -m unittest discover -s tests -v
python scripts/package.py --output /tmp/PhysicRollModel-prototype-v0.3-candidate.zip
```

The new `artifacts/v03_foundations.result.json` carries the optional outputs
without changing legacy process results. The original v0.2.1 branch and its
archive remain the reproducible accepted baseline. The reviewed v0.3 was
published as `09d0d5b2` on the development branch; it has not been merged or
validated against aluminium plant measurements.

## Reviewed mechanics and AA5052 literature study

The published `development/aa5052-mechanics-review` branch corrects numerical and
unit-contract defects and runs an explicitly conditional AA5052 comparison and
two-intermediate-gauge search. See [the specialist audit](docs/mechanics-audit.md)
and [actual run, source citations and reproducible commands](docs/aa5052-study.md).
44 tests pass, including unit factors, independent pressure integration,
mechanical work, thermal exchange and constrained-search rechecks. The source
force/slip mismatch and unresolved material/speed conventions are retained.
No physical aluminium accuracy, product temper or safe schedule is certified.
The prior candidate and v0.2.1 are preserved; reviewed commit `09d0d5b2` is published.

## Optional contact/material review increment

From reviewed `09d0d5b2`, published contact increment `1f1145df` adds spatial
hardening and circular elastic roll contact without changing the default model.
Run `python scripts/run_contact_increment.py --cells 512` for the fixed-gauge
AA5052 comparison and explicit hypothesis sensitivity (no new optimisation).
See [equations and source provenance](docs/contact-increment.md) and
[actual report-sync evidence](docs/report-sync-contact-increment.md).

## Optional flowing-strip energy handoff

On local branch `development/flowing-energy-handoff`, run
`python scripts/run_flowing_energy_demo.py` for a two-pass **synthetic** strip
enthalpy and roll-energy example. [Equations, units and source limits](docs/energy-handoff.md),
[run/report evidence](docs/report-sync-energy-handoff.md) and
`tests/test_energy_handoff.py` specify the optional interface. Mechanical force
and the existing benchmark comparison keep their reviewed behavior.

The later opt-in [passive-contact boundary](docs/passive-contact.md) uses a
**supplied synthetic** total conductance and solves contact power jointly with
the flowing-strip/aggregate-roll ledger. Run
`python scripts/run_flowing_energy_demo.py --config scenarios/passive_contact_demo.json --out artifacts/passive_contact_demo.json`.
The unchanged closure now rejects inputs outside a conservative stream/roll
capacity domain; representative contact entropy and pure-exchange whole-step
entropy are reported separately. Its midpoint temperatures and contact coefficient
are unvalidated; the
prescribed-power example remains the default.

## Offline operating-phase replay

[O0 operating contracts](docs/operational-replay.md) preserve versioned phase
recipe targets, applied references and measured samples separately. The
`physicroll.operational_replay` API records ramp-up, steady and deceleration
histories and reports per-model readiness with explicit missing-data reasons.
Readiness permits only a separate domain check; replay computes no predictions,
advances no material state and implements no dynamic physics or control.
