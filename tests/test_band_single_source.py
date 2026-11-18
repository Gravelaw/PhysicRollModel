"""Single-source rules: one physical source must explain every observation.

Review finding (after the coil fix of f0c53a0): the roll-mark rule picked the mark count n per
pitch, so pitches fitting n = 2 and n = 3 both 'matched' although no single mark pattern
explains them. The same class of rule was checked everywhere a set of candidate sources is
matched against several observations (see ``band_diagnosis._per_freq``).
"""
import math
import unittest

from physicroll.band_diagnosis import diagnose
from tests.test_band_diagnosis import _bite, baseline


def case(pitches, wr=True, faces='one', **obs):
    c = baseline(pitch_observations=[{'exit_speed_m_s': u, 'pitch_m': p} for u, p in pitches],
                 faces=faces, disappears_after_work_roll_change=wr, **obs)
    c['pass']['work_roll_radius_m'] = 0.2
    b = _bite(c).to_dict()
    c['model_options']['bite_response_override'] = {
        k: b[k] for k in b if k not in ('source', 'flags', 'strip_modulus_n_m')}
    return c


def hyp(r, hid):
    return next(h for h in r['hypotheses'] if h['id'] == hid)


def mark_ev(h):
    return next(e for e in h['evidence'] if e['criterion'].startswith('pitch = pi*D'))


class RollMarkSingleCountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mixed = diagnose(case([(6, 0.66304), (12, 0.44203)]))
        w = hyp(cls.mixed, 'work_roll_borne_marks')
        circ = w['model_prediction']['pitch_one_mark_m']
        cls.circ = circ
        cls.shared = diagnose(case([(6, circ / 2), (12, circ / 2 * 1.01)]))
        cls.single = diagnose(case([(6, circ / 3)]))

    def test_reviewer_mixed_counts_no_strong_support(self):
        w = hyp(self.mixed, 'work_roll_borne_marks')
        e = mark_ev(w)
        self.assertNotEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertEqual(e['verdict'], 'CONTRADICTS')
        self.assertIn('one count is applied to all', e['observed'])
        self.assertNotEqual(self.mixed['hypotheses'][0]['id'], 'work_roll_borne_marks')
        n = w['model_prediction']['mark_count_used']
        self.assertEqual(n, 3)
        self.assertIn(f'n = {n}', e['observed'])

    def test_shared_count_still_supports_and_map_uses_it(self):
        w = hyp(self.shared, 'work_roll_borne_marks')
        e = mark_ev(w)
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertEqual(w['model_prediction']['mark_count_used'], 2)
        self.assertEqual(self.shared['hypotheses'][0]['id'], 'work_roll_borne_marks')
        sm = self.shared['strip_map']
        self.assertEqual(sm['hypothesis_id'], 'work_roll_borne_marks')
        self.assertIn('/2', str(sm))

    def test_single_pitch_as_before(self):
        w = hyp(self.single, 'work_roll_borne_marks')
        self.assertEqual(w['model_prediction']['mark_count_used'], 3)
        self.assertEqual((mark_ev(w)['verdict'], mark_ev(w)['weight']), ('SUPPORTS', 'strong'))

    def test_grinder_mark_count_preferred_on_tie(self):
        # pitches exactly between circ/2 and circ/3 in worst mismatch is hard to build; a
        # single pitch at circ/4 with grinder marks 4 supplied takes n = 4 and names it
        c = case([(6, self.circ / 4)])
        c['kinematics']['grinder_marks'] = [{'roll': 'work_roll', 'marks_per_circumference': 4}]
        w = hyp(diagnose(c), 'work_roll_borne_marks')
        self.assertEqual(w['model_prediction']['mark_count_used'], 4)

    def test_backup_roll_path(self):
        b = hyp(self.mixed, 'backup_roll_borne_marks')
        e = mark_ev(b)
        self.assertIn('n = ', e['observed'])
        self.assertIn('mark_count_used', b['model_prediction'])


class TorsionalSingleModeTests(unittest.TestCase):
    def test_one_mode_for_every_frequency(self):
        from physicroll import band_diagnosis as bd

        class Ctx:
            pass
        # unit test of the rule with two modes and observations at each of them
        ctx = Ctx()
        ctx.drive_modes = [{'frequency_hz': 10.0}, {'frequency_hz': 40.0}]
        ctx.freqs = [('a', 10.0), ('b', 40.0)]
        ctx.pitches = []
        ctx.law = None
        ctx.slope = None
        ctx.obs = {'orientation': None}
        ctx.u_op = 10.0
        ev, pred = bd._h_torsional(ctx)
        self.assertNotEqual((ev[0]['verdict'], ev[0]['weight']), ('SUPPORTS', 'strong'))
        self.assertIn('best single fit', ev[0]['expected'])
        ctx.freqs = [('a', 10.0), ('b', 10.5)]
        ev, _ = bd._h_torsional(ctx)
        self.assertEqual((ev[0]['verdict'], ev[0]['weight']), ('SUPPORTS', 'strong'))


class FifthOctaveSingleCountTests(unittest.TestCase):
    def test_backup_roll_count_shared(self):
        circ_b = hyp(diagnose(case([(6, 0.3)])), 'backup_roll_borne_marks')[
            'model_prediction']['pitch_one_mark_m']
        # n = 5 and n = 6 separately (speed-independent law, exponent about -0.26)
        r = diagnose(case([(6, circ_b / 5), (12, circ_b / 6)]))
        self.assertEqual(r['signatures']['law'], 'SPEED_INDEPENDENT_PITCH')
        e = next(e for e in hyp(r, 'fifth_octave_roll_stack_resonance')['evidence']
                 if e['criterion'] == 'pitch-speed law')
        self.assertEqual(e['verdict'], 'NEUTRAL')
        self.assertIn('one count 5 for all pitches', e['observed'])
        r = diagnose(case([(6, circ_b / 5), (12, circ_b / 5 * 1.005)]))
        e = next(e for e in hyp(r, 'fifth_octave_roll_stack_resonance')['evidence']
                 if e['criterion'] == 'pitch-speed law')
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'moderate'))


if __name__ == '__main__':
    unittest.main()
