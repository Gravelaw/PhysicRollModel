import argparse
import json
import os
from pathlib import Path
import tempfile
from .model import Scenario, solve
from .run_contract import RunSpec
from .workflows import run_workflow


def _save_complete(path, content):
    """Replace a result only after all bytes have been written successfully."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp',
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content.encode('utf-8'))
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description='Synthetic cold rolling calculation (SI only)')
    p.add_argument('scenario', type=Path, nargs='?')
    p.add_argument('--run-spec', type=Path,
                   help='versioned checked, search, conditional or operating RunSpec')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if (args.scenario is None) == (args.run_spec is None):
        p.error('provide one positional legacy scenario or --run-spec')
    try:
        if args.run_spec is None:
            result = solve(Scenario.from_dict(json.loads(args.scenario.read_text())))
            content = json.dumps(result, indent=2, allow_nan=False) + '\n'
        else:
            result = run_workflow(RunSpec.from_json(args.run_spec.read_bytes()))
            content = result.to_json()
    except (ValueError, TypeError, OSError) as exc:
        p.error(str(exc))
    if args.output:
        try:
            _save_complete(args.output, content)
        except OSError as exc:
            p.error(f'could not write complete output: {exc}')
    else:
        print(content, end='')


if __name__ == '__main__':
    main()
