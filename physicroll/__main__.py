import argparse
import json
from pathlib import Path
from .model import Scenario, solve


def main():
    p = argparse.ArgumentParser(description='Synthetic cold rolling calculation (SI only)')
    p.add_argument('scenario', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    try:
        result = solve(Scenario.from_dict(json.loads(args.scenario.read_text())))
    except (ValueError, TypeError, OSError) as exc:
        p.error(str(exc))
    content = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
    else:
        print(content, end='')


if __name__ == '__main__':
    main()
