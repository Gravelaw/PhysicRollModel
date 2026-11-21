"""The guided app's plain layer for the Phase 2 inputs and results (SPEC19 package 15).

One quick-profile run of the battery-foil example with every Phase 2 group answered through the
form (the coil with an entered stack law, the roller alignment, the gauge control with an entry
coil, the valves of its flatness control, the wavelength search): the answers convert both ways,
the groups state what they need, the required stack law is never filled in, the cards sit under
one heading per input group, every range card states its range, and the texts keep the plain
words and the glossary. Software verification of the plain layer only.
"""
import copy
import json
import math
from pathlib import Path
import unittest

from physicroll import band_app as ba
from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl
from tests.test_band_plain import (PASS_CODE_TEXT, check_chart, engine_token_problems,
                                   glossary_problems, labels_in, numbers_in, reader_texts)

PHASE2_ANSWERS = dict(
    control_zone_size=2, stack_law_kind='ratio_of_hoop_modulus', stack_ratio=100.0,
    ironing_roll_load=0.5, ironing_roll_traction=0.1,
    coil_surface_htc=10.0, coil_ambient=25.0, strip_conductivity=220.0, coil_gap_medium='oil',
    coil_gap=1.0, entry_misalignment=0.2, entry_roller_radius=200.0, exit_misalignment=0.1,
    exit_roller_radius=200.0, gap_mode='constant_force', gauge_distance=1.5,
    gauge_response=10.0, tension_loop_bandwidth=2.0, tension_trim_limit=20.0,
    reel_coil_radius=1000.0, reel_core_radius=300.0, reel_motor_inertia=50.0, reel_runout=0.1,
    reel_regulator='none', buckling_model='sine_mode_and_fe')
_RUN = {}


def preset(pid):
    return copy.deepcopy([p for p in bpl.presets(ba.load_worked_examples())
                          if p['id'] == pid][0])


def phase2_run():
    """(preset, answers, case, result) of the battery-foil example with every Phase 2 group
    answered, run with the quick profile (cached)."""
    if not _RUN:
        p = preset('example_battery_foil')
        a = bpl.answers_from_case(p['case'])
        a['values'].update(PHASE2_ANSWERS)
        case = bpl.case_from_answers(a, p)
        engine_case, left = bpl.apply_profile(case, 'quick')
        _RUN.update(preset=p, answers=a, case=case, left=left, result=bd.diagnose(engine_case))
    return copy.deepcopy(_RUN)


def converted(x, engine):
    """x is an engine number or one of its plain unit conversions (%, kPa, MPa, °C, hours)."""
    for f in (lambda v: v, lambda v: v / 100, lambda v: v * 1e3, lambda v: v * 1e6,
              lambda v: v + 273.15, lambda v: v * 3600, lambda v: -v, lambda v: -v * 1e3):
        y = f(x)
        if any(math.isclose(y, e, rel_tol=1e-9, abs_tol=1e-12) for e in engine):
            return True
    return False


class Phase2AnswersTest(unittest.TestCase):
    def test_answers_reach_the_case_and_come_back(self):
        run = phase2_run()
        c = run['case']
        w = c['width_model']
        self.assertEqual(w['flatness_control']['control_zone_nozzles'][:2], [[0, 1], [2, 3]])
        self.assertNotIn(bpl.ZONE_SIZE_KEY, w['flatness_control'])
        self.assertEqual(w['coil_winding']['radial_law'], {'kind': 'ratio_of_hoop_modulus',
                                                           'ratio': 100.0})
        self.assertEqual(w['coil_winding']['ironing_roll'], {'load_per_width_n_m': 500.0,
                                                             'traction_coefficient': 0.1})
        self.assertEqual(w['span_alignment']['entry_span'], {'misalignment_m_per_m': 2e-4,
                                                             'roller_radius_m': 0.1})
        self.assertAlmostEqual(w['coil_thermal']['ambient_temperature_k'], 298.15, places=9)
        g = c['foil_gauge_control']
        self.assertEqual((g['gap_mode'], g['tension_trim_limit_fraction'],
                          g['gauge_time_constant_s'], g['smith_predictor']),
                         ('constant_force', 0.2, 0.01, False))
        self.assertEqual(g['reels']['entry']['runout_m'], 1e-4)
        back = bpl.answers_from_case(c)['values']
        for k, v in PHASE2_ANSWERS.items():
            self.assertEqual(back[k], run['answers']['values'][k], k)
        again = bpl.case_from_answers(bpl.answers_from_case(c), c)
        self.assertEqual(bd.validate_case(again)['width_model'],
                         bd.validate_case(c)['width_model'])
        st = bpl.addon_status(c)
        for gid in ('flatness_control', 'coil', 'alignment', 'gauge_control', 'oil_data'):
            self.assertTrue(st[gid]['filled'], gid)
        # the valves as drawn come from the engine's grouping of this case
        valves = bpl.drawing_model(c)['control_zones']['valves']
        self.assertEqual([v['nozzle_numbers'] for v in valves],
                         [[i + 1 for i in g]
                          for g in w['flatness_control']['control_zone_nozzles']])

    def test_a_group_says_what_it_needs(self):
        p = preset('foil_mill')
        a = bpl.answers_from_case(p['case'])
        a['values'].update(valve_levels_kind=[0.0, 1.0], valve_min_on=10.0, valve_min_off=10.0,
                           flatness_dead_band=2.0)
        c = bpl.case_from_answers(a, p)
        st = bpl.addon_status(c)['flatness_control']
        self.assertTrue(st['summary'].startswith('needs: a flatness roll'), st)
        self.assertEqual(st['needs'], ['a flatness roll (shapemeter)'])
        self.assertIsNone(bpl.drawing_model(c)['control_zones'])

    def test_the_stack_law_is_asked_never_filled_in(self):
        for p in bpl.presets(ba.load_worked_examples()):
            self.assertIsNone(bpl.answers_from_case(p['case'])['values']['stack_law_kind'])
        q = bpl.QUESTION_BY_ID['stack_law_kind']
        self.assertIn('press test', q.help)
        self.assertIn('never fills in a number', q.help)
        p = preset('example_battery_foil')
        a = bpl.answers_from_case(p['case'])
        a['values'].update(stack_law_kind='constant')
        with self.assertRaises(bpl.AnswerError) as cm:
            bpl.case_from_answers(a, p)
        self.assertEqual(cm.exception.question, 'stack_modulus')
        self.assertIn('never fills in', str(cm.exception))


class Phase2SummaryTest(unittest.TestCase):
    def test_cards_headings_and_words(self):
        run = phase2_run()
        r, c = run['result'], run['case']
        s = bpl.plain_summary(r, c)
        ids = [x['id'] for x in s['addon_cards']]
        for cid in ('loop', 'steptest', 'stepfit', 'transfer', 'winding', 'coiltemp',
                    'alignment', 'gaugeloop'):
            self.assertIn(cid, ids)
        self.assertIn('waves', ids)                     # left out by the quick run, said so
        waves = [x for x in s['addon_cards'] if x['id'] == 'waves'][0]
        self.assertTrue(waves.get('left_out'))
        self.assertIn(bpl.PROFILES['quick']['left_out'][4], run['left'])
        # every card under exactly one heading, the headings in the order of the groups
        in_sections = [x for sec in s['addon_sections'] for x in sec['cards']]
        self.assertEqual(sorted(in_sections), sorted(ids))
        order = [g[0] for g in bpl.ADDON_GROUPS]
        self.assertEqual([sec['group'] for sec in s['addon_sections']],
                         sorted({x['group'] for x in s['addon_cards']}, key=order.index))
        status = bpl.addon_status(c)
        for sec in s['addon_sections']:
            self.assertTrue(status[sec['group']]['filled'], sec['group'])
        engine = set(numbers_in(r))
        for card in s['addon_cards']:
            ch = card['chart']
            if ch is None:
                continue
            self.assertEqual(check_chart(ch), [], card['id'])
            if ch['type'] == 'range' and any(m['id'] == 'range' for m in ch['marks']):
                # a range card never states a single value as its takeaway
                self.assertRegex(card['takeaway'], r'between -?[\d.]+ and -?[\d.]+|factor -?[\d.]+',
                                 card['id'])
            if card['id'] in ('loop', 'steptest', 'stepfit', 'transfer', 'winding', 'coiltemp',
                              'alignment', 'gaugeloop'):
                for x in numbers_in(ch):
                    if isinstance(x, int) and x < 100 or x in (0.5, 1.0, 100.0, 0.0):
                        continue
                    self.assertTrue(converted(x, engine), f'{card["id"]}: {x}')
        texts = reader_texts(s) + [(x['id'], t) for x in s['addon_cards'] for t in
                                   [x['takeaway'], x['how_to_read']] + x['details']
                                   + [x.get('caveat') or '']]
        self.assertEqual(engine_token_problems(texts), [])
        self.assertEqual(glossary_problems(texts), [])
        low = ' '.join(t for _, t in texts).lower()
        for w in bpl.FORBIDDEN:
            self.assertNotIn(w, low)
        self.assertNotRegex(low, r'(?<!not )(?<!un)validated')
        self.assertEqual([f['flag'] for f in s['flags_plain'] if not f['described']], [])
        self.assertEqual([t for k in bpl.PASS_VIEWS for t in labels_in(s[k])
                          if PASS_CODE_TEXT.search(t)], [])
        # the fixed sentences of the brief
        self.assertIn('The control law is this tool\'s own, not your system\'s.',
                      s['control_loop_view']['fixed'])
        self.assertIn('not evidence', s['step_test_view']['not_evidence'])
        self.assertIn('upper bound', s['coil_view']['temperature']['text'])
        self.assertIn('not a prediction that the foil wrinkles', s['alignment_view']['caveat'])
        self.assertIn('not the mill\'s speed effect', s['gauge_loop_view']['caveat'])
        self.assertIn('second estimate', s['feedback_check_view']['second_text'].lower())

    def test_nothing_without_its_group(self):
        r = json.loads((Path(__file__).resolve().parents[1] / 'artifacts' / 'band_diagnosis'
                        / 'bearing-order-demo.result.json').read_text())
        s = bpl.plain_summary(r)
        self.assertEqual(s['addon_cards'], [])
        self.assertEqual(s['addon_sections'], [])


if __name__ == '__main__':
    unittest.main()
