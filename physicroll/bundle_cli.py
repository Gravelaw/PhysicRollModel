"""Create, verify or replay a saved offline v1 run directory."""

import argparse
from pathlib import Path

from .run_bundle import create_run_bundle, replay_run_bundle, verify_run_bundle
from .run_contract import RunSpec


def main():
    parser = argparse.ArgumentParser(description='PhysicRollModel offline run bundles')
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('create')
    create.add_argument('--run-spec', type=Path, required=True)
    create.add_argument('--out', type=Path, required=True)
    for name in ('verify', 'replay'):
        command = commands.add_parser(name)
        command.add_argument('bundle', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'create':
            result = create_run_bundle(RunSpec.from_json(args.run_spec.read_bytes()), args.out)
        elif args.command == 'verify':
            _, result = verify_run_bundle(args.bundle)
        else:
            result = replay_run_bundle(args.bundle)
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))
    print(f'{args.command} passed: ResultBundle {result.sha256}')


if __name__ == '__main__':
    main()
