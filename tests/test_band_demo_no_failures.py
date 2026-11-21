"""No section of a committed demo result failed (reads the artifacts; cheap).

Optional sections turn a refused input, a numerical failure or a programming error (a None
formatted, a missing key) into their own FAILED status and the diagnosis goes on
(``band_process.SECTION_ERRORS``). So a demo that runs to the end can still hide a failed
section: this test reads every committed result and names any section with a FAILED status,
any non-empty ``failures`` list and any top-level flag that reports a failed section.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'band_diagnosis'
DEMOS = ('battery-foil-demo', 'lengthwise-bands-demo', 'thin-gauge-chatter-demo',
         'bearing-order-demo', 'realistic-header-demo', 'product-survey')
FAILED_FLAG = re.compile(r'(SECTION|PER_PASS)_FAILED$')


def failures(x, path='$', out=None):
    out = [] if out is None else out
    if isinstance(x, dict):
        st = x.get('status')
        if isinstance(st, str) and (st == 'FAILED' or st.endswith('_FAILED')):
            out.append(f'{path}: {st} {x.get("error") or x.get("reason") or ""}'.strip())
        if isinstance(x.get('failures'), list) and x['failures']:
            out.append(f'{path}.failures: {x["failures"]}')
        for k, v in x.items():
            failures(v, f'{path}.{k}', out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            failures(v, f'{path}[{i}]', out)
    return out


class CommittedDemosHaveNoFailedSection(unittest.TestCase):
    def test_no_failed_section(self):
        for name in DEMOS:
            r = json.loads((ART / f'{name}.result.json').read_text(encoding='utf-8'))
            self.assertEqual(failures(r), [], name)
            self.assertEqual([f for f in r.get('flags') or [] if FAILED_FLAG.search(f)], [],
                             name)

    def test_the_check_sees_a_failed_section(self):
        r = {'width': {'zone_step_test': {'status': 'FAILED', 'error': 'zone_step_test: '
                                          'TypeError: x'}, 'failures': ['zone_step_test: x']}}
        self.assertEqual(len(failures(r)), 2)


if __name__ == '__main__':
    unittest.main()
