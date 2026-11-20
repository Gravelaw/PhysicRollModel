"""The guided app's plain layer for the Phase 1 inputs and results (SPEC18 package 12).

One quick-profile engine run of the battery-foil case with pass records, a speed and
temperature factor and the spray layout around the roll, all entered through the form's
answers: the answers convert both ways, the new summary views and add-on cards read their
numbers from the result, use plain words and the fixed sentences of the brief, and every
technical term on a card has its gloss. Software verification of the plain layer only.
"""
import copy
import json
import math
from pathlib import Path
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl
from tests.test_band_plain import (PASS_CODE_TEXT, check_chart, engine_token_problems,
                                   glossary_problems, labels_in, numbers_in, reader_texts)

ROOT = Path(__file__).resolve().parents[1]
HARDENING = {'law': 'voce', 'provenance': 'test: synthetic Voce law', 'initial_stress_pa': 1.0e8,
             'saturation_stress_pa': 2.6e8, 'characteristic_strain': 0.6,
             'stage_iv_slope_pa': 1.0e7, 'prior_equivalent_strain': 0.0,
             'reference_thickness_m': 2.6e-4, 'use_computed_flow_stress': False,
             'rate_temperature': None}
_RUN = {}


def phase1_run():
    """(preset, answers, case, result): the battery-foil example plus a Voce law, then the
    Phase 1 inputs entered as answers, built, and run with the quick profile (cached)."""
    if not _RUN:
        raw = json.loads((ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json').read_text())
        raw['hardening'] = dict(HARDENING)
        preset = bpl.file_preset(raw)
        a = bpl.answers_from_case(preset['case'])
        a['values'].update(
            pass_records=[{'label': 'coil 4711', 'separating_force_n': 1200.0,
                           'forward_slip_fraction': 6.0, 'torque_per_work_roll_nm': None,
                           'exit_speed_m_s': None},
                          {'label': 'coil 4712', 'separating_force_n': 1100.0,
                           'forward_slip_fraction': None, 'torque_per_work_roll_nm': None,
                           'exit_speed_m_s': 660.0}],
            rate_sensitivity=0.027, rate_reference=1e-3, temperature_softening=0.15,
            rate_reference_temperature=20.0, use_rate_temperature=False,
            spray_arcs=[{'start_rad': 90.0, 'arc_rad': 60.0}])
        case = bpl.case_from_answers(a, preset)
        engine_case, _ = bpl.apply_profile(case, 'quick')
        _RUN.update(preset=preset, answers=a, case=case, result=bd.diagnose(engine_case))
    return copy.deepcopy(_RUN)


class Phase1AnswersTest(unittest.TestCase):
    def test_answers_reach_the_case_and_come_back(self):
        run = phase1_run()
        c = run['case']
        recs = c['measurement']['pass_records']
        self.assertEqual([r['separating_force_n'] for r in recs], [1.2e6, 1.1e6])
        self.assertEqual(recs[0]['forward_slip_fraction'], 0.06)
        self.assertEqual(recs[1]['exit_speed_m_s'], 11.0)
        self.assertNotIn('torque_per_work_roll_nm', recs[0])
        self.assertEqual(recs[0]['provenance'], 'entered in the band app')
        rt = c['hardening']['rate_temperature']
        self.assertEqual((rt['rate_sensitivity'], rt['reference_strain_rate_per_s'],
                          rt['temperature_coefficient_per_k'], rt['reference_temperature_k'],
                          rt['use_rate_temperature']), (0.027, 1e-3, 0.0015, 293.15, False))
        arcs = c['width_model']['circumferential_layout']['spray_arcs']
        self.assertAlmostEqual(arcs[0]['start_rad'], math.pi / 2, places=15)
        self.assertAlmostEqual(arcs[0]['arc_rad'], math.pi / 3, places=15)
        back = bpl.answers_from_case(c)['values']
        for k in ('pass_records', 'rate_sensitivity', 'rate_reference', 'temperature_softening',
                  'rate_reference_temperature', 'use_rate_temperature', 'spray_arcs'):
            self.assertEqual(back[k], run['answers']['values'][k], k)
        again = bpl.case_from_answers(bpl.answers_from_case(c), c)
        for k in ('measurement', 'hardening'):           # equal as the engine reads them
            self.assertEqual(bd.validate_case(again)[k], bd.validate_case(c)[k], k)
        st = bpl.addon_status(c)
        self.assertEqual(st['pass_records']['summary'], '2 records')
        self.assertEqual(st['roll_cooling']['summary'], '1 spray band placed')
        self.assertEqual(st['model_choices']['summary'], 'speed and temperature factor')

    def test_dont_know_clears_the_sections(self):
        run = phase1_run()
        a = run['answers']
        for q in ('pass_records', 'rate_sensitivity', 'rate_reference', 'temperature_softening',
                  'rate_reference_temperature', 'use_rate_temperature', 'spray_arcs'):
            a['values'][q] = None
        c = bpl.case_from_answers(a, run['preset'])
        self.assertIsNone(c['hardening']['rate_temperature'])
        self.assertIsNone(c['width_model']['circumferential_layout'])
        self.assertIsNone(c['measurement']['pass_records'])
        a['values']['rate_sensitivity'] = 0.027
        with self.assertRaises(bpl.AnswerError) as cm:
            bpl.case_from_answers(a, run['preset'])
        self.assertEqual(cm.exception.question, 'rate_reference')


class Phase1SummaryTest(unittest.TestCase):
    VIEWS = ('friction_records_view', 'heat_share_view', 'roll_surface_view',
             'flow_stress_view')

    def test_views_and_cards_read_the_result(self):
        run = phase1_run()
        r = run['result']
        s = bpl.plain_summary(r, run['case'])
        engine = set(numbers_in(r))
        for v in self.VIEWS:
            self.assertTrue(s[v]['available'], v)
            for x in numbers_in(s[v]):
                if isinstance(x, int) and x < 100:
                    continue
                self.assertIn(x, engine, f'{v}: {x}')
        ids = [c['id'] for c in s['addon_cards']]
        self.assertEqual(ids, ['shapemeter', 'hotcold', 'records', 'friction', 'rollsurface',
                               'flowstress', 'heatshare', 'rollgap'])
        for c in s['addon_cards']:
            self.assertTrue(c['takeaway'] and c['how_to_read'] and c['text_alternative'])
            if c['chart']:
                self.assertEqual(check_chart(c['chart']), [], c['id'])
            for x in numbers_in(c['chart'] or {}):
                if c['id'] == 'rollgap' or isinstance(x, int) and x < 100:
                    continue
                self.assertIn(x, engine, f'{c["id"]}: {x}')
        codes = [t for k in bpl.PASS_VIEWS + ('addon_cards',)
                 for t in [t for _, t in reader_texts({k: s[k]})] + labels_in(s[k])
                 if PASS_CODE_TEXT.search(t)]
        self.assertEqual(codes, [])
        texts = reader_texts(s)
        self.assertEqual(engine_token_problems(texts), [])
        self.assertEqual(glossary_problems(texts), [])
        low = ' '.join(t for _, t in texts).lower()
        for w in bpl.FORBIDDEN:
            self.assertNotIn(w, low)
        self.assertNotRegex(low, r'(?<!not )(?<!un)validated')     # never "validated"
        self.assertEqual([f['flag'] for f in s['flags_plain'] if not f['described']], [])

    def test_fixed_sentences(self):
        s = bpl.plain_summary(phase1_run()['result'])
        fr = s['friction_records_view']
        self.assertTrue(fr['rows'][0]['text'].startswith('Your force of 1200 kN corresponds to '
                                                         'a friction of '))
        self.assertIn('your forward slip to', fr['rows'][0]['text'])
        # both values with their range, and whose measuring error it is (the app asks none)
        self.assertIn('for a force error of ±5 %, the tool\'s assumption', fr['rows'][0]['text'])
        self.assertIn('for a slip error of ±1 percentage point, the tool\'s assumption',
                      fr['rows'][0]['text'])
        self.assertIn('within these measuring errors', fr['rows'][0]['text'])
        self.assertEqual(fr['caveat'], 'Nothing was changed; enter the value yourself if you '
                                       'want to use it.')
        hs = s['heat_share_view']
        self.assertTrue(hs['text'].startswith('You entered that 22 % of the heat stays in the '
                                              'strip; the tool\'s own estimate is '))
        self.assertIn('comparison', hs['caveat'])
        rs = s['roll_surface_view']
        self.assertTrue(rs['text'].startswith('Just before the roll gap the roll surface is at '))
        self.assertIn('the average the model works with is', rs['text'])
        self.assertIn('extrapolation', s['flow_stress_view']['caveat'])
        self.assertIn('the roll forces do not use it', s['flow_stress_view']['text'])
        rg = s['roll_gap_model_view']
        self.assertIn('The published figure is 118, but it depends on a numerical detail the '
                      'paper does not state', rg['benchmark_text'])
        self.assertIn('option', rg['option_text'])


if __name__ == '__main__':
    unittest.main()
