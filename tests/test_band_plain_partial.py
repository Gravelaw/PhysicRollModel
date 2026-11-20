"""Plain summaries of REAL partial results of the band engine (SPEC16 review, finding 1).

The cases come from the engine's own fixtures and the repository scenarios
(``tests/band_partial_cases.py``) and are run through ``band_diagnosis.diagnose``: no roll bite
for the operating pass, a schedule pass rejected, a width model whose thermal part is not
assessable, a v2 case with sections not supplied, a v1 case, a foil case with a bite that is not
credible, and the case template. Software verification of the plain layer only.
"""
import copy
import json
import unittest

from physicroll import band_plain as bpl
from physicroll import band_sensors as bsensors
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

    def test_sensor_views_are_unavailable_without_their_sections(self):
        def good(sec):
            return isinstance(sec, dict) and sec.get('status') not in (
                'NOT_ASSESSABLE', 'FAILED', 'NOT_SUPPLIED')

        for name in P.CASES:
            with self.subTest(case=name):
                s, r = summary(name)
                m, w = r.get('measurement') or {}, r.get('width') or {}
                expect = {'shapemeter_view': good(m.get('shapemeter')),
                          'gauge_sensor_view': good(m.get('thickness_gauge')),
                          'temperature_flatness_view': good(w.get('strip_temperature')),
                          'friction_view': good(w.get('friction_stripes')),
                          'roll_profile_view': good(w.get('roll_profile')),
                          'friction_records_view': good((r.get('process') or {}).get(
                              'friction_identification')),
                          'roll_surface_view': good(w.get('roll_surface_cycle'))}
                for v, want in expect.items():
                    self.assertEqual(s[v]['available'], want, v)
                if name != 'foil_not_credible':           # the battery-foil scenario carries
                    self.assertFalse(any(expect.values()))   # a shapemeter and a scan
                self.assertFalse(s['flow_stress_view']['available'])    # no factor entered
                ids = [c['id'] for c in s['addon_cards']]
                for card, view in (('shapemeter', 'shapemeter_view'), ('rollsurface',
                                                                       'roll_surface_view'),
                                   ('records', 'friction_records_view')):
                    self.assertEqual(card in ids, s[view]['available'], card)
        # a shapemeter on a pass with no roll bite: the engine's own section is not
        # assessable (no modelled flatness), and the page shows no zone readings
        case, result = P.result('no_bite_width')
        case, result = copy.deepcopy(case), copy.deepcopy(result)
        case['measurement'] = {'shapemeter': {
            'zone_width_m': 0.052, 'zone_count': 24, 'edge_zone_width_m': None,
            'edge_zone_count_per_side': 0, 'centre_m': None, 'neighbour_spreading_fraction': 0.0,
            'resolution_i_units': None, 'temperature_compensated': None,
            'provenance': 'test'}, 'thickness_gauge': None}
        result['measurement'] = bsensors.measurement_section(case, result)
        self.assertEqual(result['measurement']['shapemeter']['status'], 'NOT_ASSESSABLE')
        s = bpl.plain_summary(result, case)
        self.assertFalse(s['shapemeter_view']['available'])
        self.assertEqual(engine_token_problems(reader_texts(s)), [])

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
