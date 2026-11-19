"""Plain summaries of REAL partial results of the band engine (SPEC16 review, finding 1).

The cases come from the engine's own fixtures and the repository scenarios
(``tests/band_partial_cases.py``) and are run through ``band_diagnosis.diagnose``: no roll bite
for the operating pass, a schedule pass rejected, a width model whose thermal part is not
assessable, a v2 case with sections not supplied, a v1 case, a foil case with a bite that is not
credible, and the case template. Software verification of the plain layer only.
"""
import json
import unittest

from physicroll import band_plain as bpl
from tests import band_partial_cases as P
from tests.test_band_plain import engine_token_problems, reader_texts


def summary(name):
    case, result = P.result(name)
    return bpl.plain_summary(result, case), result


def na(s, kind=None):
    return {x['what']: x for x in s['not_assessable'] if kind is None or x['kind'] == kind}


class PartialResultTest(unittest.TestCase):
    def test_every_partial_case_builds_a_plain_summary(self):
        for name in P.CASES:
            with self.subTest(case=name):
                s, r = summary(name)
                json.dumps(s, allow_nan=False)
                self.assertEqual(engine_token_problems(reader_texts(s, name)), [])
                text = json.dumps(s).lower()
                for w in bpl.FORBIDDEN:
                    self.assertNotIn(w, text)
                self.assertEqual(s['trust']['level'], 'LOW')     # synthetic inputs everywhere
                self.assertEqual(len(s['causes']), 20)
                self.assertEqual(s['roll_gap_failed'], bool(r['bite_error']))

    def test_operating_pass_without_a_roll_bite(self):
        for name in ('no_bite', 'no_bite_width'):
            with self.subTest(case=name):
                s, r = summary(name)
                self.assertTrue(r['bite_error'])
                first = s['not_assessable'][0]
                self.assertEqual(first['what'], 'Roll-gap model of the pass where the bands show')
                self.assertTrue(first['why'].startswith('The roll-gap model could not solve this '
                                                        'pass: the rolls would flatten more'))
                self.assertIn('could not compute the pass where the bands show',
                              s['headline']['text'])
                items = na(s)
                for sec in ('Chatter (roll-stack vibration) checks', 'Vibration time trace'):
                    self.assertEqual(items[sec]['why'], 'needs the roll-gap result of this '
                                                        'pass, which could not be computed')
                self.assertTrue(any('roll-gap model could not compute' in x['text']
                                    for x in s['trust']['reasons']))
        s, _ = summary('no_bite_width')
        items = na(s)
        self.assertIn('Roll temperature across the width', items)
        self.assertIn('"Heat made in the roll gap per metre of width"',
                      items['Roll temperature across the width']['why'])
        self.assertIn('Strip-shape part of the width model', items)
        self.assertFalse(s['strip_view'].get('thermal_profile'))

    def test_schedule_pass_rejected(self):
        s, r = summary('schedule_row_rejected')
        self.assertFalse(r['bite_error'])
        item = na(s)['Pass R1 of the route']
        self.assertEqual(item['kind'], 'not_assessable')
        self.assertTrue(item['why'].startswith('The roll-gap model could not solve this pass'))
        self.assertNotIn('could not compute', s['headline']['text'])

    def test_sections_not_supplied(self):
        s, _ = summary('sections_not_supplied')
        supplied = na(s, 'not_supplied')
        for sec in ('Across-the-width model', 'Oil film, friction and pass heating',
                    'Gauge control', 'Drive train'):
            self.assertEqual(supplied[sec]['why'], 'not supplied for this case')
        self.assertFalse([x for x in s['not_assessable']
                          if x['kind'] in ('not_assessable', 'failed')])
        self.assertFalse(s['strip_view']['available'] and s['strip_view'].get('nozzles'))
        self.assertFalse(s['gauge_view']['available'])
        self.assertFalse(s['temperature_view']['available'])

    def test_v1_case(self):
        s, r = summary('v1')
        self.assertEqual(r['case_schema'], 'physicroll.band_case.v1')
        self.assertEqual(s['family']['observed'], 'transverse')
        self.assertTrue(s['along_view']['available'])
        self.assertEqual(s['headline']['kind'], 'one_leader')

    def test_foil_bite_not_credible(self):
        s, r = summary('foil_not_credible')
        self.assertIn('CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE', r['flags'])
        self.assertTrue(any('not credible' in x['text'] for x in s['trust']['reasons']))
        self.assertTrue(any(f['flag'] == 'CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_'
                            'CREDIBLE' and f['described'] for f in s['flags_plain']))
        self.assertEqual(s['headline']['kind'], 'tie')

    def test_template_case(self):
        s, _ = summary('template')
        self.assertEqual(s['headline']['kind'], 'nothing_leads')
        self.assertIn('Nothing stands out yet', s['headline']['text'])
        self.assertTrue(any('No orientation' in x['text'] or 'No cause leads' in x['text']
                            for x in s['trust']['reasons']))


if __name__ == '__main__':
    unittest.main()
