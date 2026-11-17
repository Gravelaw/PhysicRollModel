"""Band / chatter-mark root-cause screening from a case file (synthetic or user supplied).

    python -m physicroll.band_cli CASE.json --out DIR

Writes ``DIR/<slug>.result.json`` and ``DIR/<slug>.report.html`` atomically and prints the
ranked standings. The result is an unvalidated screening tally, not a certified cause.
"""
import argparse
from pathlib import Path
import re

from .__main__ import _save_complete
from .band_diagnosis import diagnose, load_case, result_json
from .band_report import render_band_report


def slug(name):
    """File-name slug of a case name: lowercase ASCII letters, digits and single hyphens."""
    text = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return text[:80] or 'case'


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Band / chatter-mark root-cause screening (unvalidated, SI units)')
    parser.add_argument('case', type=Path, help='band case JSON (physicroll.band_case.v1)')
    parser.add_argument('--out', type=Path, required=True, help='output directory')
    args = parser.parse_args(argv)
    try:
        case = load_case(args.case)
        result = diagnose(case)
        html = render_band_report(result)
        content = result_json(result)
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))
    base = slug(result['case_name'])
    json_path = args.out / f'{base}.result.json'
    html_path = args.out / f'{base}.report.html'
    try:
        _save_complete(json_path, content)
        _save_complete(html_path, html)
    except OSError as exc:
        parser.error(f'could not write complete output: {exc}')
    print(f'{result["status"]}: {result["case_name"]}')
    print('rank  standing             score  hypothesis')
    for h in result['hypotheses']:
        print(f'{h["rank"]:>4}  {h["standing"]:<20} {h["score"]:>5}  {h["id"]}')
    print('(score = ordinal evidence tally, not a probability)')
    print(f'result: {json_path}')
    print(f'report: {html_path}')


if __name__ == '__main__':
    main()
