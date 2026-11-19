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


if __name__ == '__main__':
    unittest.main()
