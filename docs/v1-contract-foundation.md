# V1 foundation: W0 baseline and W1 contract

This increment starts from clean `main` at
`9d775f7623a5345b44db961064f24cf938f22b8d`. Its authoritative input is
the directly attached `PhysicRollModel-v1-plan.md` (SHA-256
`467e3afa0ae4c89786aca4a7994111604f1e7855dcc333acafb9771e64afca01`).
The Library copy had a separate folder-scope access denial. Editor and Blender
playback scope remain open. No physical equation, solver, search rule or legacy
positional CLI changes belong to W1.

## W0 evidence boundary

On 2026-10-10 UTC, a fresh published environment instance started, a disposable
workspace file was saved/read/deleted, and the checkout HEAD matched live remote
`main`. Python 3.12.14, Git 2.52.0 and Blender 4.3.2 were present. `pip check`,
the bundled smoke/checksum test, 111 project unit tests, the saved Blender scene
check (78 IDs), OpenUSD mesh check (77 meshes) and the scientific/Jupyter stack
check passed. These are software/environment results (S). Independent material
calibration and predictive accuracy (V), and site/operating qualification (O),
remain unestablished. The existing isolated wheel's missing benchmark resources
are W2 package work, not a reason to change the physics during W1.

## W1 boundary and acceptance

- `RunSpec` version 1 records workflow kind, explicit solver/material/bite/thermal
  selections, SI conventions, code/model and material/state identities, source
  and card SHA-256 hashes, numerical settings, exact requested/resolved inputs,
  recipe targets and observations in distinct fields. An omitted identity is
  explicitly `null`; a guessed card or observation is not supplied.
- `ResultBundle` version 1 binds to the canonical RunSpec hash and stores
  effective inputs, outputs and checks. Its assessments retain execution,
  input validity, applicability, numerical verification, declared bounds status
  **and coverage**, scientific qualification, operating readiness, and whether
  predictions were computed as separate fields. There is no aggregate
  `feasible`/`validated` boolean. `checks.declared_bounds` records distinct
  required limit IDs and evaluations. Coverage and status must agree with those
  records: zero evaluated limits stays `NONE`/`INDETERMINATE`, partial checks
  without a violation stay `PARTIAL`/`INDETERMINATE`, and `WITHIN` requires
  every named required limit to be evaluated. W3 must supply the complete
  workflow-specific required limit set; W1 cannot infer site ratings.
- Canonical scientific JSON is deterministic and independent of runtime metadata
  such as timestamps. Decoding rejects duplicate keys, unknown versions/fields,
  unsupported Python objects and nonfinite numbers; dataclasses and tuples are
  deliberately normalized to JSON objects and arrays. `null` and negative
  regenerative quantities survive round trips.
- Tests cover round trips, stable digests, provenance/field rejection, strict
  status distinctions and preservation of the legacy CLI. W2/W3 will bind these
  contracts to packaged resources and the existing reviewed APIs; W1 does not
  assert a new numerical or scientific result.

The [checked input example](../scenarios/v1_checked_pass.runspec.json) pins one
synthetic spatial-slab pass, its prescribed exit gauge, numerical settings and
hashes of its source/card inputs. `tests/test_run_contract.py` reconstructs and
runs the existing checked solver from that resolved input, then round-trips its
result envelope. The example is a contract fixture; the public checked CLI/API
adapter belongs to W3. [RunSpec](../schema/run-spec-v1.schema.json) and
[ResultBundle](../schema/result-bundle-v1.schema.json) have JSON Schema files;
`physicroll.run_contract` performs the additional finite-number and cross-field
checks that those schemas alone do not establish.

Fresh W0 checks on this environment: 111 baseline tests passed before W1;
the final W1 suite then passed 119 tests in 4.819 s of test runtime (5.539 s
for the wrapper command). The source smoke/checksum check took 0.052 s. A direct
conditional Shao replay took 0.203 s, retaining force residuals
−3.08/−3.01/+7.79% and slip residuals +41.89/+37.89/+23.79%; declared
prior sensitivity took 0.114 s, with one rejected and three indeterminate
cases. Timings are observed on the 2026-10-10 UTC Linux x86_64/Python 3.12.14
CPU environment, with the restored activation script's single-thread BLAS
settings. They describe these workloads, not a delivery forecast.

The envelope is used with `RunSpec.from_json(text)`, `ResultBundle(payload)` and
`ResultBundle.verify_run_spec(spec)`. `to_json()` emits a trailing newline for
files. The SHA-256 digest covers canonical sorted UTF-8 JSON without that
newline. `runtime_metadata` is carried on a ResultBundle but excluded from its
scientific digest. A digest detects accidental or unauthorized content changes;
it is not a signature or empirical qualification. The `checks` and `outputs`
objects retain workflow-specific detail without W1 inventing new physics.

The initial [pull-request source checks](../.github/workflows/source-checks.yml)
run the standard-library smoke and unit suites, the optional pinned JSON Schema
parity test, and the legacy positional CLI on Linux/Python 3.10 and 3.12. They
check this source tree; W2 still must test an installed wheel outside the
checkout, and W6 still must close the supported-runtime/release gate. Passing
source CI does not alone justify merging an incomplete v1 release.
