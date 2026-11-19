"""What the band app draws is what the engine will simulate (SPEC16 review, findings 6 and 7).

The page draws only from the drawing model that ``/api/case/check`` and ``/api/case/edit``
compute from the BUILT case (``band_plain.drawing_model``). The invariant tested here: for every
answer state the page can reach, the model's per-nozzle levels are the levels the engine uses for
that case (``band_width.spray_layout``, the engine's own resolution of ``nozzle_levels`` and
``blocked_nozzle_indices``), they are what a run of that case reports (``thermal_steady.
nozzle_levels``), and after a nozzle edit they are exactly what the person set. Software
verification only; the screening itself is not validated against plant data.
"""
import copy
import json
import random
import unittest

from physicroll import band_plain as bpl
from physicroll import band_width as bw
from tests.test_band_app import ServerCase, fake_engine

WEAK = bpl.WEAK_NOZZLE_LEVEL


def engine_levels(case):
    """The nozzle levels the width model simulates for a case, from the engine itself."""
    return [float(x) for x in bw.spray_layout(case)['nozzle_levels']]


def model_levels(out):
    return [n['level'] for n in out['model']['header']['nozzles']]


class Api:
    """The calls the page makes, with the page's own bookkeeping of the answers."""

    def __init__(self, test, preset='foil_mill', case_file=None):
        self.t, self.preset, self.case_file = test, preset, case_file
        st, meta = test.client.json('GET', '/api/meta')
        test.assertEqual(st, 200)
        self.meta = {p['id']: p for p in meta['presets']}
        self.answers = copy.deepcopy(self.meta[preset]['answers']) if preset in self.meta \
            else None

    def body(self, **kw):
        b = {'preset': self.preset, 'answers': self.answers}
        if self.case_file is not None:
            b['case_file'] = self.case_file
        b.update(kw)
        return b

    def take(self, st, out):
        if st == 200 or 'answers_patch' in out:
            self.answers['values'].update(out.get('answers_patch') or {})
        return st, out

    def check(self):
        return self.take(*self.t.client.json('POST', '/api/case/check', self.body()))

    def edit(self, **edit):
        return self.take(*self.t.client.json('POST', '/api/case/edit', self.body(edit=edit)))

    def set(self, qid, value):
        self.answers['values'][qid] = value
        self.answers['origins'][qid] = 'estimated'
        return self.check()


class DrawnIsSimulatedTest(ServerCase):
    """Answer states (levels only, blocked numbers only, both agreeing and disagreeing, an
    opened case, after reconciliation, a variant, a reopened run): drawn levels = engine levels
    = what a run reports."""
    engine = None                                   # the real engine

    def assert_consistent(self, out, expected=None):
        drawn = model_levels(out)
        self.assertEqual(drawn, engine_levels(out['case']))
        if expected is not None:
            self.assertEqual(drawn, expected)
        reduced = [i + 1 for i, lv in enumerate(drawn) if lv < 1]
        cov = out['model']['coverage']
        self.assertTrue(cov['same_header'])
        self.assertEqual(cov['blocked_numbers'], reduced)
        self.assertEqual([i + 1 for i in out['case']['coolant']['blocked_nozzle_indices']],
                         reduced)
        return drawn

    def run_levels(self, rid):
        done, _ = self.wait(rid)
        self.assertEqual(done['run']['status'], 'done', done['run'].get('error'))
        result = json.loads((self.tmp / rid / 'result.json').read_text())
        ts = result['width']['thermal_steady']
        cov = result['screens']['spray_coverage']
        return ts['nozzle_levels'], cov['blocked_nozzle_indices']

    def submit(self, api):
        st, out = self.client.json('POST', '/api/runs', api.body(profile='quick'))
        self.assertEqual(st, 202, out)
        return out['id']

    def levels(self, marks, n=28):
        lv = [1.0] * n
        for i, x in marks.items():
            lv[i] = x
        return lv

    def test_answer_states_without_a_run(self):
        api = Api(self)
        # levels only
        api.answers['values']['nozzle_levels'] = self.levels({3: 0.0, 11: WEAK})
        st, out = api.check()
        self.assertEqual(st, 200, out)
        self.assert_consistent(out, self.levels({3: 0.0, 11: WEAK}))
        # blocked numbers only (an API client or an answers file from before the one-list rule)
        api.answers['values'].update(nozzle_levels=None, blocked_nozzles=[12])
        st, out = api.check()
        self.assert_consistent(out, self.levels({11: 0.0}))
        self.assertTrue(out['model']['header']['levels_known'])
        self.assertEqual(out['answers_patch']['blocked_nozzles'], None)
        self.assertEqual(api.answers['values']['nozzle_levels'], self.levels({11: 0.0}))
        # both, agreeing
        api.answers['values'].update(nozzle_levels=self.levels({11: 0.0}), blocked_nozzles=[12])
        st, out = api.check()
        self.assert_consistent(out, self.levels({11: 0.0}))
        # both, disagreeing: the blocked number wins for its nozzle, the levels for the rest
        api.answers['values'].update(nozzle_levels=self.levels({2: 0.45}), blocked_nozzles=[12])
        st, out = api.check()
        self.assert_consistent(out, self.levels({2: 0.45, 11: 0.0}))
        self.assertEqual([n['kind'] for n in out['reconciled']], ['moved'])
        # after reconciliation from a pitch change: 52 -> 60 mm resets (25 nozzles) ...
        st, out = api.set('nozzle_pitch', 60.0)
        self.assertEqual([n['kind'] for n in out['reconciled']], ['reset'])
        self.assert_consistent(out, [1.0] * 25)
        self.assertFalse(out['model']['header']['levels_known'])
        # ... 52 -> 53 mm keeps 28 nozzles and their marks, and moves them (finding 7)
        api.set('nozzle_pitch', 52.0)
        api.edit(op='set_blocked', numbers=[12])
        st, out = api.set('nozzle_pitch', 53.0)
        self.assertEqual(out['reconciled'], [])
        self.assert_consistent(out, self.levels({11: 0.0}))
        first = out['model']['header']['nozzles'][0]['position_m']
        self.assertAlmostEqual(first, 0.0345, places=9)
        self.assertEqual(first, bpl.nozzle_layout(out['case'])[0])

    def test_opened_case_with_blocked_12_and_all_ones_is_drawn_blocked_and_runs_healthy(self):
        # the reviewer's case: a case file with nozzle 12 blocked and an all-ones level list
        st, meta = self.client.json('GET', '/api/meta')
        foil = {p['id']: p for p in meta['presets']}['foil_mill']
        st, chk = self.client.json('POST', '/api/case/check', {'preset': 'foil_mill',
                                                                'answers': foil['answers']})
        case = copy.deepcopy(chk['case'])
        case['width_model']['nozzle_levels'] = [1.0] * 28
        case['width_model']['blocked_nozzle_indices'] = [11]
        case['coolant']['blocked_nozzle_indices'] = [11]
        st, opened = self.client.json('POST', '/api/case/open', {'case_file': case})
        self.assertEqual(st, 200, opened)
        model = opened['preset']['model']
        self.assertEqual(model['header']['nozzles'][11]['state'], 'blocked')
        api = Api(self, 'case_file', case)
        api.answers = opened['answers']
        self.assertIsNone(api.answers['values']['blocked_nozzles'])
        st, out = api.check()
        self.assertEqual(out['reconciled'], [])
        self.assert_consistent(out, self.levels({11: 0.0}))
        # cycle nozzle 12 back to healthy: blocked -> healthy
        st, out = api.edit(op='cycle', index=11)
        self.assertEqual(st, 200, out)
        self.assert_consistent(out, [1.0] * 28)
        run_levels, run_cov = self.run_levels(self.submit(api))
        self.assertEqual(run_levels[11], 1.0)
        self.assertEqual(run_levels, model_levels(out))
        self.assertEqual(run_cov, [])

    def test_variant_and_reopened_run(self):
        api = Api(self)
        api.answers['values']['nozzle_levels'] = self.levels({5: WEAK, 20: 0.0})
        st, out = api.check()
        drawn = self.assert_consistent(out, self.levels({5: WEAK, 20: 0.0}))
        base = self.submit(api)
        run_levels, run_cov = self.run_levels(base)
        self.assertEqual(run_levels, drawn)
        self.assertEqual(run_cov, [5, 20])
        # a what-if that blocks nozzle 9 (the page sends the result's levels with one changed)
        lv = list(run_levels)
        lv[8] = 0.0
        st, v = self.client.json('POST', f'/api/runs/{base}/variant',
                                 {'changes': {'nozzle_levels': lv}, 'profile': 'quick'})
        self.assertEqual(st, 202, v)
        var_levels, var_cov = self.run_levels(v['id'])
        self.assertEqual(var_levels, lv)
        self.assertEqual(var_cov, [5, 8, 20])
        # reopening either run draws what that run simulated
        for rid, want in ((base, run_levels), (v['id'], var_levels)):
            st, ro = self.client.json('GET', f'/api/runs/{rid}/reopen')
            self.assertEqual(st, 200, ro)
            st, out = self.client.json('POST', '/api/case/check',
                                       {'preset': ro['preset'], 'answers': ro['answers']})
            self.assertEqual(st, 200, out)
            self.assertEqual(self.assert_consistent(out), want)


def capture_engine(case):
    capture_engine.cases.append(case)
    return fake_engine(case)


capture_engine.cases = []


class EditSequenceTest(ServerCase):
    """A deterministic pseudo-random sequence of a few hundred edits through the calls the page
    makes. After every step the drawing model equals both what the person set and the engine's
    effective state of the case that would be submitted."""
    engine = staticmethod(capture_engine)
    STEPS = 300

    def expected_after(self, op, exp, n, arg=None):
        if op == 'clear':
            return None
        if op == 'all_healthy':
            return [1.0] * n
        new = list(exp) if exp is not None else [1.0] * n
        if op == 'cycle':
            new[arg] = WEAK if new[arg] >= 1 else 0.0 if new[arg] > 0 else 1.0
        elif op == 'set_level':
            new[arg[0]] = arg[1]
        elif op == 'set_blocked':
            if not arg and exp is None:
                return None
            for i in range(n):
                if i + 1 in arg:
                    new[i] = 0.0
                elif new[i] <= 0:
                    new[i] = 1.0
        return new

    def assert_state(self, api, out, exp, step):
        msg = f'step {step}'
        self.assertEqual(out['ok'], True, msg)
        n = len(bpl.nozzle_layout(out['case']))
        drawn = model_levels(out)
        self.assertEqual(len(drawn), n, msg)
        self.assertEqual(drawn, exp if exp is not None else [1.0] * n, msg)
        self.assertEqual(out['model']['header']['levels_known'], exp is not None, msg)
        self.assertEqual(api.answers['values'].get('nozzle_levels'), exp, msg)
        self.assertIsNone(api.answers['values'].get('blocked_nozzles'), msg)
        # the case that would be submitted, built by the submit route's own function
        preset = self.server.store.preset(api.body())
        case, notices, patch = self.server.store.build_case(api.answers, preset, for_run=True)
        self.assertEqual(patch, {}, msg)
        self.assertEqual(engine_levels(case), drawn, msg)
        self.assertEqual(engine_levels(out['case']), drawn, msg)
        self.assertEqual(out['model']['coverage']['blocked_numbers'],
                         [i + 1 for i, lv in enumerate(drawn) if lv < 1], msg)
        xs = [nz['position_m'] for nz in out['model']['header']['nozzles']]
        self.assertEqual(xs, bpl.nozzle_layout(case), msg)

    def test_pseudo_random_edit_sequence(self):
        rnd = random.Random(20261119)
        capture_engine.cases.clear()
        api = Api(self)
        st, out = api.check()
        exp = None
        counts = {}
        submitted = 0
        for step in range(self.STEPS):
            n = len(out['model']['header']['nozzles'])
            op = rnd.choice(['cycle'] * 5 + ['set_level'] * 3 + ['set_blocked'] * 3
                            + ['clear', 'all_healthy', 'pitch1', 'pitch8', 'barrel', 'reopen'])
            counts[op] = counts.get(op, 0) + 1
            if op == 'cycle':
                i = rnd.randrange(n)
                st, out = api.edit(op='cycle', index=i)
                exp = self.expected_after('cycle', exp, n, i)
            elif op == 'set_level':
                i, x = rnd.randrange(n), rnd.choice([0.0, 0.25, 0.45, 0.5, 0.8, 1.0])
                st, out = api.edit(op='set_level', index=i, level=x)
                exp = self.expected_after('set_level', exp, n, (i, x))
            elif op == 'set_blocked':
                cur = [k + 1 for k, lv in enumerate(exp or []) if lv <= 0]
                j = rnd.randrange(1, n + 1)
                nums = sorted(set(cur) ^ {j}) if rnd.random() < 0.8 else []
                st, out = api.edit(op='set_blocked', numbers=nums)
                exp = self.expected_after('set_blocked', exp, n, nums)
            elif op in ('clear', 'all_healthy'):
                st, out = api.edit(op=op)
                exp = self.expected_after(op, exp, n)
            elif op in ('pitch1', 'pitch8', 'barrel'):
                if op == 'barrel':
                    qid, v = 'barrel_length', rnd.choice([1450.0, 1500.0, 1520.0, 1560.0])
                else:
                    qid = 'nozzle_pitch'
                    cur = api.answers['values']['nozzle_pitch']
                    d = (1.0 if op == 'pitch1' else 8.0) * rnd.choice([-1, 1])
                    v = cur + d if 40.0 <= cur + d <= 70.0 else cur - d
                st, out = api.set(qid, v)
                n_new = len(out['model']['header']['nozzles'])
                if n_new != n and exp is not None:
                    self.assertEqual([x['kind'] for x in out['reconciled']], ['reset'])
                    exp = None
                else:
                    self.assertEqual(out['reconciled'], [], f'step {step}')
            else:                                   # run, then "Change the answers"
                st, run = self.client.json('POST', '/api/runs', api.body(profile='quick'))
                self.assertEqual(st, 202, run)
                done, _ = self.wait(run['id'])
                self.assertEqual(done['run']['status'], 'done')
                submitted += 1
                self.assertEqual(engine_levels(capture_engine.cases[-1]),
                                 exp if exp is not None else [1.0] * n)
                st, ro = self.client.json('GET', f'/api/runs/{run["id"]}/reopen')
                self.assertEqual(st, 200, ro)
                api.preset = ro['preset']
                api.answers = ro['answers']
                st, out = api.check()
            self.assertEqual(st, 200, (step, op, out))
            self.assert_state(api, out, exp, step)
        self.assertGreaterEqual(min(counts.values()), 3, counts)
        self.assertGreater(submitted, 0)


class EditRuleTest(ServerCase):
    """The edit rule's edges: "Don't know" stays until something is marked; refusals."""
    engine = staticmethod(fake_engine)

    def test_dont_know_stays_until_marked(self):
        api = Api(self)
        st, out = api.edit(op='set_blocked', numbers=[])
        self.assertEqual(st, 200)
        self.assertIsNone(api.answers['values']['nozzle_levels'])
        self.assertFalse(out['model']['header']['levels_known'])
        st, out = api.edit(op='set_blocked', numbers=[3])
        self.assertEqual(model_levels(out)[2], 0.0)
        st, out = api.edit(op='set_blocked', numbers=[])
        self.assertEqual(api.answers['values']['nozzle_levels'], [1.0] * 28)   # marked: known
        self.assertTrue(out['model']['header']['levels_known'])

    def test_refused_edits_change_nothing(self):
        api = Api(self)
        before = copy.deepcopy(api.answers)
        for edit, q in (({'op': 'cycle', 'index': 28}, 'nozzle_levels'),
                        ({'op': 'set_level', 'index': 0, 'level': 1.5}, 'nozzle_levels'),
                        ({'op': 'set_blocked', 'numbers': [0]}, 'blocked_nozzles'),
                        ({'op': 'set_blocked', 'numbers': [2.5]}, 'blocked_nozzles'),
                        ({'op': 'explode'}, 'nozzle_levels')):
            st, out = self.client.json('POST', '/api/case/edit', api.body(edit=edit))
            self.assertEqual(st, 400, edit)
            self.assertEqual(out['error']['question'], q, edit)
        self.assertEqual(api.answers, before)
        st, out = self.client.json('POST', '/api/case/edit', api.body(edit='cycle'))
        self.assertEqual(st, 400)

    def test_no_header_starting_point(self):
        api = Api(self, 'example_bearing_order')
        st, out = api.check()
        self.assertIsNone(out['model']['header'])
        self.assertFalse(out['model']['coverage']['same_header'])
        st, out = api.edit(op='cycle', index=0)
        self.assertEqual(st, 400)
        self.assertIn('no spray header model', out['error']['text'])

    def test_coverage_numbers_of_an_opened_case_that_disagree_are_shown_not_dropped(self):
        st, meta = self.client.json('GET', '/api/meta')
        foil = {p['id']: p for p in meta['presets']}['foil_mill']
        st, chk = self.client.json('POST', '/api/case/check', {'preset': 'foil_mill',
                                                                'answers': foil['answers']})
        case = copy.deepcopy(chk['case'])
        case['coolant']['blocked_nozzle_indices'] = [3]       # nozzle 4, only in the coverage
        st, opened = self.client.json('POST', '/api/case/open', {'case_file': case})
        self.assertEqual(opened['answers']['values']['coverage_blocked_nozzles'], [4])
        api = Api(self, 'case_file', case)
        api.answers = opened['answers']
        body = api.body(profile='quick')
        st, out = self.client.json('POST', '/api/runs', body)     # not run unseen
        self.assertEqual(st, 409)
        st, out = api.check()
        self.assertEqual([(n['question'], n['kind']) for n in out['reconciled']],
                         [('nozzle_levels', 'reset')])
        self.assertIn('only for the simple coverage check', out['reconciled'][0]['text'])
        self.assertEqual(model_levels(out)[3], 0.0)
        st, out = self.client.json('POST', '/api/runs', api.body(profile='quick'))
        self.assertEqual(st, 202, out)

    def test_worked_examples_round_trip_to_the_same_simulated_nozzles(self):
        st, meta = self.client.json('GET', '/api/meta')
        for p in meta['presets']:
            preset = self.server.store.presets[p['id']]
            st, out = self.client.json('POST', '/api/case/check', {'preset': p['id'],
                                                                    'answers': p['answers']})
            self.assertEqual(st, 200, p['id'])
            self.assertEqual(out['reconciled'], [], p['id'])
            self.assertEqual(out['case']['coolant'], preset['case']['coolant'], p['id'])
            if preset['case'].get('width_model'):
                self.assertEqual(engine_levels(out['case']), engine_levels(preset['case']))
                self.assertEqual(out['model'], p['model'] | {'side': out['model']['side']})


if __name__ == '__main__':
    unittest.main()
