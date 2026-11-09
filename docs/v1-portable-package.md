# V1 portable package: W2

The wheel now carries named synthetic examples, the three JSON schemas, and the
audited Shao AA5052 fixture and conditional-replay records. Runtime loading uses
`importlib.resources`, so it does not depend on the checkout, current directory,
or a sibling `docs/` or `scenarios/` tree. `physicroll.resources.resource_file`
returns a Traversable intended for reading; `read_example` loads a named JSON example.
Unknown names are rejected. The legacy positional file-path CLI remains intact.

The package-data list in `pyproject.toml` declares four resource groups:

| Group | Reviewed source copy | Use |
|---|---|---|
| `examples` | `scenarios/*.json` (thirteen named files) | Legacy baseline, checked pass, finite search, two conditional Shao templates and synthetic O0 phase replay |
| `schemas` | `schema/*.json` | V1 contract and legacy scenario schemas |
| `shao_fixture` | `scenarios/literature/shao2015_aa5052/*` | Established audited CSV/assumptions source fixture |
| `shao_research` | `docs/research/data/shao2015_*.json` | Raw transcription, conditional adapter, prior sensitivity |

`tests/test_package_resources.py` compares every packaged copy byte-for-byte
with its reviewed source. When a source record legitimately changes, update the
package copy in the same change; any raw Shao change also requires the existing
audit and pinned checksum to be reviewed. The package does not carry the full
research library or preview artifacts. These inputs remain conditional
comparison evidence, not independent material validation or mill qualification.
`.gitattributes` disables checkout line-ending conversion so the pinned bytes
stay identical on Linux and Windows, including pre-existing audited CSV content.

From a source checkout, run `python scripts/check_installed_wheel.py`. It builds
a wheel, installs it without dependencies into a disposable virtual environment,
then runs `python -I -m physicroll.package_check` from a directory outside the
checkout. The installed check executes the synthetic legacy baseline and checked
pass, parses all packaged schemas, imports the Shao fixture with its 49 converted
numeric values, checks raw-versus-fixture identity, replays the fixed conditional
route, and runs all four declared prior-history cases. It uses no network after
the wheel has been built. CI is configured to repeat this on Linux and Windows,
Python 3.10 and 3.12. Successful runs for each combination are required before
claiming platform evidence; W6 remains a separate release gate.

The Python APIs in the package can be exercised after installation:

```python
from physicroll.resources import read_example, resource_directory
from physicroll.literature import load_case

baseline = read_example('baseline.json')
shao = load_case(resource_directory('shao_fixture'))
```

The packaged RunSpec examples cover the initial public W3 adapters.
W4 saved run bundles now record runtime-module/resource hashes, verify exact
files and replay with a matching installed wheel. Keeping the duplicate source/package records in sync is enforced in
source tests and CI, but a separately tampered installed wheel is outside W2's
integrity claim.
