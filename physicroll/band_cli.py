"""Band / chatter-mark root-cause screening from a case file (synthetic or user supplied).

    python -m physicroll.band_cli CASE.json --out DIR
    python -m physicroll.band_cli --product-survey --out DIR [survey options]
        (physicroll.band_survey: --mill, --foil-mill, --sheet-mill, --products,
         --overrides, --write-cases)
    python -m physicroll.band_cli CASE.json --calibrate-spray FILE.json
        (band_thermal.calibrate_spray_coefficient: the spray coefficient fitted to a measured
         roll surface temperature scan after a stop or a thermal camber; prints the JSON
         result, writes nothing into a case; ``--numerics case`` for the case's own grid)
    python -m physicroll.band_cli --fit-hardening FILE.json
        (bite_tribology.fit_voce_to_pass_strengths on {"gauges_m", "strengths_pa",
         "reference_thickness_m", "prior_equivalent_strain"}; prints the JSON result, writes
         nothing into a case)

Writes ``DIR/<slug>.result.json`` and ``DIR/<slug>.report.html`` atomically and prints the
ranked standings. The result is an unvalidated screening tally, not a certified cause.
"""
import argparse
from pathlib import Path
import re
import sys

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
    parser.add_argument('case', type=Path, nargs='?',
                        help='band case JSON (physicroll.band_case.v1 or v2)')
    parser.add_argument('--out', type=Path, required=True, help='output directory')
    parser.add_argument('--product-survey', action='store_true',
                        help='run the product survey (physicroll.band_survey) instead of a case; '
                             'its options (--mill, --products, ...) are passed on')
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fit-hardening' in argv:
        return _fit_hardening(argv)
    if '--calibrate-spray' in argv:
        return _calibrate_spray(argv)
    if '--product-survey' in argv:
        # every other argument belongs to the survey (it validates them itself)
        from . import band_survey
        band_survey.main([a for a in argv if a != '--product-survey'])
        return
    args = parser.parse_args(argv)
    if args.case is None:
        parser.error('a case file is required (or --product-survey)')
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


FIT_KEYS = ('gauges_m', 'strengths_pa', 'reference_thickness_m', 'prior_equivalent_strain')


def _fit_hardening(argv):
    """SPEC18 package 8: fit a Voce law to entered pass strengths and print the result.
    An under-determined or invalid input prints ``{"status": "NOT_FITTED", "outcome", "reason"}``
    and exits 2; no number is returned for it."""
    import json
    from . import bite_tribology as bt
    parser = argparse.ArgumentParser(description='Fit a Voce hardening law to pass strengths')
    parser.add_argument('--fit-hardening', type=Path, required=True, metavar='FILE.json')
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.fit_hardening.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or set(data) - set(FIT_KEYS) or \
                not {'gauges_m', 'strengths_pa', 'reference_thickness_m'} <= set(data):
            raise ValueError(f'the file must be a JSON object with keys {list(FIT_KEYS)} '
                             '(prior_equivalent_strain optional)')
        res = bt.fit_voce_to_pass_strengths(
            data['gauges_m'], data['strengths_pa'],
            reference_thickness_m=data['reference_thickness_m'],
            prior_equivalent_strain=data.get('prior_equivalent_strain', 0.0))
    except (ValueError, TypeError, OSError) as exc:
        text = str(exc)
        outcome = text.split(':')[0] if text.startswith('UNDERDETERMINED') else 'INVALID_INPUT'
        print(json.dumps({'status': 'NOT_FITTED', 'outcome': outcome, 'reason': text},
                         indent=1))
        sys.exit(2)
    print(json.dumps(res, indent=1))


def _calibrate_spray(argv):
    """SPEC18 package 11: print the spray-coefficient calibration of a case to a measurement
    file. Nothing is written into the case."""
    import json
    from . import band_thermal
    parser = argparse.ArgumentParser(description='Fit the spray coefficient of a case to a '
                                     'measured roll temperature scan or thermal camber')
    parser.add_argument('case', type=Path, help='band case JSON (v2, with a width_model)')
    parser.add_argument('--calibrate-spray', type=Path, required=True, metavar='FILE.json',
                        help='the measurement: kind, positions_m, values, seconds_after_stop, '
                             'search_range_w_m2k, uncertainty, provenance')
    parser.add_argument('--numerics', choices=('quick', 'case'), default='quick')
    args = parser.parse_args(argv)
    try:
        case = load_case(args.case)
        cal = json.loads(args.calibrate_spray.read_text(encoding='utf-8'))
        res = band_thermal.calibrate_spray_coefficient(case, cal, numerics=args.numerics)
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
