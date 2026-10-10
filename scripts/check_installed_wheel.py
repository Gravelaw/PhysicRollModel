"""Build, install, and run the offline package check outside the source tree."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import venv


ROOT = Path(__file__).resolve().parents[1]


def main():
    with TemporaryDirectory(prefix='physicroll-wheel-') as temporary:
        target = Path(temporary)
        source = target / 'source'
        source.mkdir()
        for name in ('pyproject.toml', 'LICENSE'):
            shutil.copyfile(ROOT / name, source / name)
        shutil.copytree(ROOT / 'physicroll', source / 'physicroll',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        wheelhouse = target / 'wheels'
        wheelhouse.mkdir()
        subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-deps',
                        '--wheel-dir', str(wheelhouse), str(source)],
                       cwd=target, check=True)
        wheels = list(wheelhouse.glob('physicroll-*.whl'))
        if len(wheels) != 1:
            raise RuntimeError('expected exactly one PhysicRollModel wheel')
        environment = target / 'venv'
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        clean_env = os.environ.copy()
        clean_env.pop('PYTHONPATH', None)
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-index', '--no-deps',
                        str(wheels[0])], cwd=target, env=clean_env, check=True)
        outside = target / 'outside-checkout'
        outside.mkdir()
        subprocess.run([str(python), '-I', '-m', 'physicroll.package_check'],
                       cwd=outside, env=clean_env, check=True)
        spec = outside / 'checked-example.json'
        result = outside / 'checked-result.json'
        subprocess.run([
            str(python), '-I', '-c',
            "from pathlib import Path; import sys; "
            "from physicroll.resources import resource_file; "
            "Path(sys.argv[1]).write_bytes(resource_file('examples', "
            "'v1_checked_pass.runspec.json').read_bytes())",
            str(spec),
        ], cwd=outside, env=clean_env, check=True)
        subprocess.run([str(python), '-I', '-m', 'physicroll', '--run-spec',
                        str(spec), '--output', str(result)],
                       cwd=outside, env=clean_env, check=True)
        subprocess.run([
            str(python), '-I', '-c',
            "from pathlib import Path; import sys; "
            "from physicroll.run_contract import RunSpec, ResultBundle; "
            "from physicroll.workflows import run_checked_spec; "
            "spec=RunSpec.from_json(Path(sys.argv[1]).read_bytes()); "
            "cli=ResultBundle.from_json(Path(sys.argv[2]).read_bytes()); "
            "cli.verify_run_spec(spec); "
            "assert cli.sha256 == run_checked_spec(spec).sha256",
            str(spec), str(result),
        ], cwd=outside, env=clean_env, check=True)


if __name__ == '__main__':
    main()
