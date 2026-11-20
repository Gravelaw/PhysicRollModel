"""Reopening a run in the band app (SPEC16 review, finding 2): "Change the answers" on a run R
must rebuild exactly R's case, whatever kind of run R is, also after a server restart.

Round-trip invariant tested here at the API level: GET /api/runs/<R>/reopen gives a starting
point and answers; POST /api/case/check with them returns R's case.json, except the fields that
legitimately differ (``REBUILT_FIELDS``: the provenance sentence and the band app's notes lines,
which name the starting point). Software verification only.
"""
import json
from pathlib import Path
import unittest

from physicroll import band_diagnosis as bd
from tests.test_band_app import ROOT, ServerCase, fake_engine
from tests.test_band_app_drawing import Api, model_zones

REBUILT_FIELDS = ('provenance', 'notes')


def strip(case):
    return {k: v for k, v in case.items() if k not in REBUILT_FIELDS}


class ReopenTest(ServerCase):
    engine = staticmethod(fake_engine)

    def run_and_wait(self, method, path, body):
        st, out = self.client.json(method, path, body)
        self.assertEqual(st, 202, out)
        done, _ = self.wait(out['id'])
        self.assertEqual(done['run']['status'], 'done', done['run'].get('error'))
        return out['id']

    def case_of(self, rid):
        return json.loads((self.tmp / rid / 'case.json').read_text())

    def reopen_check(self, rid):
        st, ro = self.client.json('GET', f'/api/runs/{rid}/reopen')
        self.assertEqual(st, 200, ro)
        st, chk = self.client.json('POST', '/api/case/check',
                                   {'preset': ro['preset'], 'answers': ro['answers']})
        self.assertEqual(st, 200, chk)
        return ro, chk['case']

    def make_runs(self):
        runs = {}
        runs['named'] = self.run_and_wait('POST', '/api/runs', {
            'preset': 'sheet_mill', 'profile': 'quick', 'answers': {
                'name': 'sheet coil 12', 'values': {
                    'orientation': 'longitudinal', 'band_positions': [400.0, 900.0],
                    'exit_speed': 650.0, 'friction': 0.035},
                'origins': {'friction': 'measured'}}})
        runs['what_if'] = self.run_and_wait('POST', f'/api/runs/{runs["named"]}/variant',
                                            {'changes': {'exit_speed': 600.0}})
        runs['update'] = self.run_and_wait('POST', f'/api/runs/{runs["named"]}/variant',
                                           {'changes': {'changes_with_tension': False}})
        runs['rerun'] = self.run_and_wait('POST', f'/api/runs/{runs["named"]}/rerun',
                                          {'profile': 'detailed'})
        template = json.loads((ROOT / 'scenarios' / 'band_diagnosis_template.json').read_text())
        runs['case_file'] = self.run_and_wait('POST', '/api/runs', {
            'preset': 'case_file', 'case_file': template, 'profile': 'quick',
            'answers': {'values': {'orientation': 'transverse'}}})
        runs['variant_of_variant'] = self.run_and_wait(
            'POST', f'/api/runs/{runs["what_if"]}/variant', {'changes': {'exit_gauge': 200.0}})
        return runs

    def check_round_trips(self, runs):
        for kind, rid in runs.items():
            with self.subTest(kind=kind):
                ro, rebuilt = self.reopen_check(rid)
                self.assertEqual(strip(rebuilt), strip(self.case_of(rid)), kind)
                if kind in ('named', 'rerun'):        # a rerun keeps a named starting point
                    self.assertEqual(ro['preset'], 'sheet_mill')
                else:
                    self.assertEqual(ro['preset'], {'run': rid})
                    label = ro['preset_info']['label']
                    self.assertTrue(label.startswith('the case file you opened' if kind ==
                                                     'case_file' else 'the earlier run'), label)

    def test_round_trip_every_kind_of_run_and_after_restart(self):
        runs = self.make_runs()
        sheet = self.case_of(runs['named'])
        self.assertEqual(sheet['pass']['entry_thickness_m'], 3e-4)     # the sheet mill's pass
        # the variant of a variant starts from its immediate base, not the root
        vv, base, root = (self.case_of(runs[k]) for k in ('variant_of_variant', 'what_if',
                                                           'named'))
        self.assertEqual(vv['pass']['exit_speed_m_s'], base['pass']['exit_speed_m_s'])
        self.assertNotEqual(vv['pass']['exit_speed_m_s'], root['pass']['exit_speed_m_s'])
        self.assertEqual(vv['pass']['exit_thickness_m'], 2e-4)
        self.check_round_trips(runs)
        self.stop()
        self.start()                                  # nothing held in the page or in memory
        self.check_round_trips(runs)
        # a change made after reopening a what-if differs from it only in that answer
        ro, _ = self.reopen_check(runs['what_if'])
        ro['answers']['values']['exit_tension'] = 33.0
        ro['answers']['origins']['exit_tension'] = 'estimated'     # as the page marks an edit
        st, chk = self.client.json('POST', '/api/case/check',
                                   {'preset': ro['preset'], 'answers': ro['answers']})
        self.assertEqual(st, 200)
        before, after = strip(self.case_of(runs['what_if'])), strip(chk['case'])
        self.assertEqual(after['pass'].pop('exit_tension_pa'), 33e6)
        before['pass'].pop('exit_tension_pa')
        self.assertEqual(after, before)
        # a run started from a reopened run keeps that starting point
        new = self.run_and_wait('POST', '/api/runs', {'preset': ro['preset'],
                                                       'answers': ro['answers']})
        self.assertEqual(self.case_of(new)['pass']['exit_tension_pa'], 33e6)
        self.assertEqual(self.case_of(new)['pass']['entry_thickness_m'], 3e-4)

    def test_unreadable_base_gives_a_plain_error(self):
        rid = self.run_and_wait('POST', '/api/runs', {'preset': 'sheet_mill',
                                                       'answers': {'values': {}}})
        var = self.run_and_wait('POST', f'/api/runs/{rid}/variant',
                                {'changes': {'exit_speed': 600.0}})
        (self.tmp / rid / 'case.json').write_text('{damaged', encoding='utf-8')
        (self.tmp / var / 'case.json').write_text('{damaged', encoding='utf-8')
        for method, path, body in (('POST', f'/api/runs/{rid}/variant',
                                    {'changes': {'exit_speed': 500.0}}),
                                   ('POST', f'/api/runs/{rid}/rerun', {}),
                                   ('GET', f'/api/runs/{var}/reopen', None),
                                   ('POST', '/api/case/check', {'preset': {'run': var},
                                                                'answers': {'values': {}}})):
            st, out = self.client.json(method, path, body)
            self.assertEqual(st, 409, path)
            self.assertIn('can no longer be read', out['error']['text'])
        st, out = self.client.json('POST', '/api/case/check', {'preset': {'run': '../x'},
                                                               'answers': {}})
        self.assertEqual(st, 400)


class SummaryErrorTest(ServerCase):
    engine = staticmethod(fake_engine)

    @staticmethod
    def summarise(*args, **kw):
        raise RuntimeError('summary layer broke on this result')

    def start(self):
        from physicroll import band_app
        import threading
        self.server = band_app.make_server(self.tmp, 0, engine=self.engine, quiet=True,
                                           summarise=self.summarise)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        from tests.test_band_app import Client
        self.client = Client(self.server)

    def test_result_and_report_survive_a_summary_failure(self):
        st, out = self.client.json('POST', '/api/runs', {'preset': 'sheet_mill',
                                                         'answers': {'values': {}}})
        done, _ = self.wait(out['id'])
        run = done['run']
        self.assertEqual(run['status'], 'done')
        self.assertIn('visual summary could not be built', run['summary_error'])
        self.assertNotIn('summary layer broke', json.dumps(done))
        self.assertNotIn('summary', done)
        folder = self.tmp / out['id']
        self.assertTrue((folder / 'result.json').is_file())
        self.assertTrue((folder / 'report.html').is_file())
        self.assertFalse((folder / 'summary.json').exists())
        resp, body = self.client.request('GET', f'/api/runs/{out["id"]}/report.html')
        self.assertEqual(resp.status, 200)
        st, res = self.client.json('GET', f'/api/runs/{out["id"]}/result.json')
        self.assertEqual(st, 200)
        self.assertEqual(res['status'], bd.STATUS)


class DependentAnswersTest(ServerCase):
    """Answers that depend on other answers (SPEC16 review, finding 5): reconciled before the
    engine validates the case, with a plain notice; a run is never started from answers the
    person has not seen."""
    engine = staticmethod(fake_engine)

    def check(self, values, preset='foil_mill'):
        return self.client.json('POST', '/api/case/check',
                                {'preset': preset, 'answers': {'values': values}})

    def levels(self, marks):
        lv = [1.0] * 28
        for i, x in marks.items():
            lv[i] = x
        return lv

    def test_nozzle_pitch_52_to_60_mm_resets_the_marks(self):
        values = {'nozzle_levels': self.levels({5: 0.5, 11: 0.0}), 'nozzle_pitch': 60.0}
        st, out = self.check(values)
        self.assertEqual(st, 200, out)
        notice = out['reconciled'][0]
        self.assertEqual(notice['question'], 'nozzle_levels')
        self.assertEqual(notice['kind'], 'reset')
        self.assertIn('25 nozzles instead of 28', notice['text'])
        self.assertEqual(out['answers_patch'], {'nozzle_levels': None})
        self.assertIsNone(out['case']['width_model']['nozzle_levels'])
        self.assertEqual(len(out['model']['header']['nozzles']), 25)
        # a run with the stale marks is refused with the same notice ...
        st, out = self.client.json('POST', '/api/runs', {'preset': 'foil_mill',
                                                         'answers': {'values': values}})
        self.assertEqual(st, 409)
        self.assertIn('25 nozzles instead of 28', out['error']['text'])
        self.assertEqual(out['error']['question'], 'nozzle_levels')
        self.assertEqual(out['answers_patch'], {'nozzle_levels': None})
        # ... and accepted once the page has applied it (and the person marked one nozzle)
        values.update(out['answers_patch'])
        lv = [1.0] * 25
        lv[3] = 0.0
        values['nozzle_levels'] = lv
        st, out = self.client.json('POST', '/api/runs', {'preset': 'foil_mill',
                                                         'answers': {'values': values}})
        self.assertEqual(st, 202, out)

    def test_other_nozzle_numbers_are_reset_with_a_notice(self):
        events = [{'start_s': 0.0, 'duration_s': 20.0, 'nozzle_indices': [26, 27],
                   'level': 0.0, 'label': None}]
        st, out = self.check({'nozzle_pitch': 60.0, 'blocked_nozzles': [27],
                              'coverage_blocked_nozzles': [28], 'valve_events': events})
        self.assertEqual(st, 200, out)
        got = {n['question']: n for n in out['reconciled']}
        for q in ('blocked_nozzles', 'coverage_blocked_nozzles', 'valve_events'):
            self.assertEqual(got[q]['kind'], 'reset', q)
            self.assertIn('nozzles', got[q]['text'])
            self.assertIsNone(out['answers_patch'][q])
        self.assertEqual(out['case']['width_model']['events'], [])
        # the same numbers on the unchanged header are kept: the blocked number becomes a mark
        # in the one stored answer (nozzle_levels), with a notice; the valve event is unchanged
        st, out = self.check({'blocked_nozzles': [27], 'valve_events': events})
        self.assertEqual(st, 200)
        self.assertEqual([(n['question'], n['kind']) for n in out['reconciled']],
                         [('nozzle_levels', 'moved')])
        self.assertEqual(out['case']['width_model']['blocked_nozzle_indices'], [])
        self.assertEqual(out['case']['width_model']['nozzle_levels'][26], 0.0)
        self.assertEqual(out['case']['width_model']['events'][0]['nozzle_indices'], [25, 26])
        self.assertIsNone(out['answers_patch']['blocked_nozzles'])

    def test_values_outside_the_strip_or_roll_get_a_check_notice(self):
        st, out = self.check({'band_positions': [100.0, 1300.0], 'band_width': 1500.0,
                              'incoming_ridges': [{'position_m': 1250.0, 'height_m': 1.0,
                                                   'width_m': 20.0}]})
        self.assertEqual(st, 200, out)
        got = {n['question']: n for n in out['reconciled']}
        for q in ('band_positions', 'band_width', 'incoming_ridges'):
            self.assertEqual(got[q]['kind'], 'check', q)
        self.assertEqual(out['answers_patch'], {})
        self.assertIn('outside the 1200 mm wide strip', got['band_positions']['text'])
        # a strip that no longer fits on the barrel: the engine refuses the band positions, and
        # the notice on the strip centre says why
        st, out = self.check({'band_positions': [100.0], 'strip_centre': 200.0})
        self.assertEqual(st, 400)
        self.assertEqual(out['error']['question'], 'band_positions')
        got = {n['question']: n for n in out['reconciled']}
        self.assertIn('does not fit on the roll barrel', got['strip_centre']['text'])
        st, out = self.client.json('POST', '/api/runs', {'preset': 'foil_mill', 'answers': {
            'values': {'band_positions': [100.0, 1300.0]}}})
        self.assertEqual(st, 202)            # a 'check' notice does not block the run

    def test_gauge_order_points_to_the_question(self):
        st, out = self.check({'exit_gauge': 60.0})          # entry gauge of the foil mill: 50
        self.assertEqual(st, 400)
        self.assertEqual(out['error']['question'], 'exit_gauge')
        self.assertIn('must be below', out['error']['text'])


if __name__ == '__main__':
    unittest.main()


class ShapemeterRunTest(ServerCase):
    """SPEC17 package 9: a run with a shapemeter stores it, the result card shows the zones the
    page drew before the run (the zones the engine reports), and the run reopens with it."""
    engine = None                                   # the real engine (quick profile)

    def test_shapemeter_run_stores_draws_and_reopens(self):
        api = Api(self)
        lv = [1.0] * 28
        lv[11] = 0.0
        api.answers['values'].update(shapemeter_zone_width=52.0, shapemeter_zone_count=24,
                                     nozzle_levels=lv)
        st, out = api.check()
        self.assertEqual(st, 200, out)
        drawn = model_zones(out)
        self.assertEqual(len(drawn), 24)
        st, run = self.client.json('POST', '/api/runs', api.body(profile='quick'))
        self.assertEqual(st, 202, run)
        done, _ = self.wait(run['id'])
        self.assertEqual(done['run']['status'], 'done', done['run'].get('error'))
        rid = run['id']
        case = json.loads((self.tmp / rid / 'case.json').read_text())
        self.assertEqual((case['measurement']['shapemeter']['zone_width_m'],
                          case['measurement']['shapemeter']['zone_count']), (0.052, 24))
        result = json.loads((self.tmp / rid / 'result.json').read_text())
        sm = result['measurement']['shapemeter']
        self.assertEqual([(z['start_m'], z['end_m'], [i + 1 for i in z['nozzle_indices']])
                          for z in sm['zones']], drawn)
        sv = done['summary']['shapemeter_view']
        self.assertTrue(sv['available'])
        self.assertEqual([(z['start_m'], z['end_m']) for z in sv['zones']],
                         [(a, b) for a, b, _ in drawn])
        st, ro = self.client.json('GET', f'/api/runs/{rid}/reopen')
        self.assertEqual(st, 200, ro)
        self.assertEqual((ro['answers']['values']['shapemeter_zone_width'],
                          ro['answers']['values']['shapemeter_zone_count']), (52.0, 24))
        st, chk = self.client.json('POST', '/api/case/check',
                                   {'preset': ro['preset'], 'answers': ro['answers']})
        self.assertEqual(st, 200, chk)
        self.assertEqual(chk['case']['measurement'], case['measurement'])
        self.assertEqual(model_zones(chk), drawn)
