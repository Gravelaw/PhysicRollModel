"""Robustness of the band engine against accepted-but-degenerate inputs, and the review
fixes whose tests were moved here from tests.test_band_v2_sections to keep that module under
its time budget (coil single source, trough spacing, perturbed bite model).

The sweep runs a small v1 case (supplied bite, coolant screen) and a small v2 case (supplied
bite; the width model only where the input concerns it) for every degenerate observation:
``diagnose`` must return and the report must render.
"""
import copy
import json
import math
import unittest
from unittest import mock

from physicroll import band_diagnosis as bd
from physicroll import band_width as bw
from physicroll.band_diagnosis import diagnose, load_case, validate_case
from physicroll.band_report import render_band_report
from tests.test_band_diagnosis import _bite, baseline
from tests.test_band_lengthwise import SCEN, V2_NULL_OBS, _h, v2, width_model


def v1case(**obs):
    c = baseline(**obs)
    b = _bite(c).to_dict()
    c['model_options']['bite_response_override'] = {
        k: b[k] for k in b if k not in ('source', 'flags', 'strip_modulus_n_m')}
    c['coolant'] = {'barrel_length_m': 1.7, 'nozzle_pitch_m': 0.052, 'standoff_m': 0.15,
                    'spray_angle_rad': 0.6, 'offset_angle_rad': 0.17,
                    'blocked_nozzle_indices': [12], 'roll_expansion_coefficient_per_k': 1.2e-5,
                    'assumed_excess_temperature_k': 5.0}
    c['kinematics'].update(entry_coil_diameter_m=1.2, exit_coil_diameter_m=1.0)
    return c


def v2case(width=False, **obs):
    c = v2(**obs)
    if width:
        c['width_model'] = width_model(
            blocked_nozzle_indices=[12], bite_heat_per_width_w_m=4e5,
            events=[{'start_s': 0.0, 'duration_s': 20.0, 'nozzle_indices': [18],
                     'level': 0.0}])
    c['kinematics'].update(entry_coil_diameter_m=1.2, exit_coil_diameter_m=1.0)
    return c


def _p(u, pitch):
    return {'exit_speed_m_s': u, 'pitch_m': pitch}


SWEEP = {
    'duplicate positions': dict(band_positions_across_width_m=[0.6, 0.6, 0.7]),
    'two identical positions': dict(band_positions_across_width_m=[0.6, 0.6]),
    'single position': dict(band_positions_across_width_m=[0.6]),
    'unsorted positions': dict(band_positions_across_width_m=[1.1, 0.4, 0.8]),
    'positions at the strip edges': dict(band_positions_across_width_m=[0.1, 1.6]),
    'positions outside strip and barrel': dict(band_positions_across_width_m=[0.0, 1.7, 2.5]),
    'duplicate pitch observations': dict(pitch_observations=[_p(10, 0.05), _p(10, 0.05)]),
    'same speed, different pitches': dict(pitch_observations=[_p(10, 0.05), _p(10, 0.07)]),
    'pitch larger than a coil circumference': dict(pitch_observations=[_p(10, 9.0)]),
}
# run on the v1 case only: the signatures section is the same code for v1 and v2 cases
SWEEP_PITCH = {
    # review finding: near-equal speeds passed an exact-float distinctness test and then made
    # pitch_speed_exponent raise, aborting the diagnosis
    'speeds 1e-10 relative apart (reviewer)': dict(
        pitch_observations=[_p(10, 0.03), _p(10.000000001, 0.031)]),
    'speeds 1e-9 relative apart': dict(pitch_observations=[_p(10, 0.03), _p(10 * (1 + 1e-9),
                                                                            0.031)]),
    'speeds 1e-6 relative apart': dict(pitch_observations=[_p(10, 0.03), _p(10 * (1 + 1e-6),
                                                                            0.031)]),
    'three pitches, two at one speed': dict(
        pitch_observations=[_p(10, 0.03), _p(10, 0.031), _p(14, 0.042)]),
    'speeds in descending order': dict(
        pitch_observations=[_p(16, 0.048), _p(12, 0.036), _p(8, 0.024)]),
    'tiny and huge pitch at distinct speeds': dict(
        pitch_observations=[_p(5, 1e-4), _p(20, 9.0)]),
}
SWEEP_V2 = {
    'tiny band spacing': dict(band_positions_across_width_m=[0.5, 0.6], band_spacing_m=1e-6),
    'band spacing at the 10 m limit': dict(band_positions_across_width_m=[0.5, 0.6],
                                           band_spacing_m=10.0),
    'band width larger than the strip': dict(band_positions_across_width_m=[0.5],
                                             band_width_m=3.0),
    'huge intermittent duration': dict(intermittent_duration_s=1e9),
}
FREE_TEXT = ('orientation', 'faces', 'first_seen', 'lengthwise_continuity', 'appearance')


def _all_bools(case, value):
    for k, v in list(case['observation'].items()):
        if k in FREE_TEXT or isinstance(v, list) or k.endswith(('_m', '_hz', '_s')):
            continue
        case['observation'][k] = value
    return case


def _ok(test, case, label):
    r = diagnose(case)
    json.dumps(r, allow_nan=False)
    html = render_band_report(r)
    test.assertNotIn('Traceback', html, label)
    test.assertEqual(len(r['hypotheses']), 20, label)
    return r, html


class DuplicatePositionTests(unittest.TestCase):
    """Reviewer's case: the lengthwise demo with positions [0.6, 0.6, 0.7] raised
    'gaps_m[0] must be > 0'; positions within 1 mm are now one band."""

    def test_lengthwise_demo_with_duplicate_positions(self):
        c = load_case(SCEN / 'band_diagnosis_lengthwise_bands.json')
        c['observation']['band_positions_across_width_m'] = [0.6, 0.6, 0.7]
        c['width_model']['numerics'] = {'axial_cell_m': 0.02, 'radial_cells': 6,
                                        'time_step_s': 5.0}
        c['width_model']['events'] = []
        c['gauge_control'] = c['drive'] = c['incoming_variation'] = None
        c['schedule'] = []                       # speed: the case pass is what matters here
        c['model_options']['cells'] = 64
        r, html = _ok(self, c, 'reviewer')
        self.assertIn('DUPLICATE_BAND_POSITIONS_MERGED', r['flags'])
        adj = r['observation_adjustments']
        self.assertEqual(adj['band_positions_supplied_m'], [0.6, 0.6, 0.7])
        self.assertEqual(adj['band_positions_used_m'], [0.6, 0.7])
        self.assertEqual(adj['merged_count'], 1)
        self.assertEqual(r['inputs']['observation']['band_positions_across_width_m'],
                         [0.6, 0.7])
        e = next(x for x in _h(r)['nozzle_thermal_stripe']['evidence']
                 if x['criterion'] == 'spacing vs nozzle pitch')
        self.assertIn('gaps 0.1 m', e['observed'])
        self.assertNotIn('HYPOTHESIS_EVALUATION_FAILED', r['flags'])

    def test_merge_rule(self):
        self.assertEqual(bd.merge_band_positions([0.4, 0.8]), ([0.4, 0.8], 0))
        self.assertEqual(bd.merge_band_positions([0.8, 0.4]), ([0.8, 0.4], 0))   # unchanged
        used, n = bd.merge_band_positions([0.7, 0.6, 0.6005, 0.6])
        self.assertEqual(n, 2)
        self.assertAlmostEqual(used[0], (0.6 + 0.6 + 0.6005) / 3)
        self.assertEqual(used[1], 0.7)


class HypothesisFailSoftTests(unittest.TestCase):
    """A domain error inside one hypothesis no longer aborts the diagnosis."""

    def _planted(self, registry, hid, case):
        def boom(*a, **k):
            raise ValueError('planted domain error <b>&')
        with mock.patch.dict(registry, {hid: boom}):
            r = diagnose(case)
        h = _h(r)[hid]
        self.assertEqual(h['standing'], 'NOT_ASSESSABLE')
        self.assertEqual(h['score'], 0)
        self.assertNotIn(hid, r['leading_hypotheses'])
        self.assertIn('planted domain error', h['evidence'][0]['observed'])
        self.assertEqual(r['hypothesis_evaluation_failures'],
                         [{'id': hid, 'error': 'planted domain error <b>&'}])
        self.assertIn('HYPOTHESIS_EVALUATION_FAILED', r['flags'])
        self.assertTrue(any(hid in x for x in r['limitations']))
        others = [x for x in r['hypotheses'] if x['id'] != hid]
        self.assertTrue(any(x['standing'] != 'NOT_ASSESSABLE' for x in others))
        html = render_band_report(r)
        self.assertIn('planted domain error &lt;b&gt;&amp;', html)
        self.assertNotIn('planted domain error <b>&', html)
        return r

    def test_lengthwise_hypothesis_failure(self):
        r = self._planted(bw.LENGTHWISE_BUILDERS, 'roll_surface_band',
                          v2case(orientation='longitudinal', band_positions_across_width_m=[0.6]))
        self.assertIn('nozzle_thermal_stripe', [h['id'] for h in r['hypotheses']])

    def test_transverse_hypothesis_failure(self):
        self._planted(bd._BUILDERS, 'third_octave_self_excited_chatter',
                      v1case(orientation='transverse'))


class DegenerateInputSweepTests(unittest.TestCase):
    """Every accepted degenerate observation input: diagnose returns, the report renders."""

    def test_v1_sweep(self):
        for label, obs in {**SWEEP, **SWEEP_PITCH}.items():
            with self.subTest(label):
                _ok(self, v1case(**obs), label)
        _ok(self, v1case(), 'all null')
        _ok(self, _all_bools(v1case(), True), 'all true')
        _ok(self, _all_bools(v1case(), False), 'all false')
        c = v1case(band_positions_across_width_m=[0.6])
        for idx in ([12, 12], [0, 31]):
            c['coolant']['blocked_nozzle_indices'] = idx
            _ok(self, copy.deepcopy(c), f'coolant blocked {idx}')

    def test_near_equal_speeds_take_the_two_speeds_path(self):
        from physicroll import band_signatures as bs
        r, html = _ok(self, v1case(pitch_observations=[_p(10, 0.03), _p(10.000000001, 0.031)]),
                      'reviewer')
        self.assertIsNone(r['signatures']['pitch_speed_exponent'])
        self.assertIn('two or more distinct exit speeds', r['signatures']['law_note'])
        self.assertFalse(bs.has_distinct_exit_speeds([10, 10.000000001]))
        self.assertTrue(bs.has_distinct_exit_speeds([10, 10.5]))
        with self.assertRaisesRegex(ValueError, 'distinct exit speeds'):
            bs.pitch_speed_exponent([(10, 0.03), (10.000000001, 0.031)])
        # 1e-6 apart is distinct numerically but below the 5 % guard: reported, not classified
        r, _ = _ok(self, v1case(pitch_observations=[_p(10, 0.03), _p(10.00001, 0.031)]), '1e-6')
        pse = r['signatures']['pitch_speed_exponent']
        self.assertEqual(pse['classification'], 'INDETERMINATE')
        self.assertIn('SPEEDS_TOO_CLOSE_FOR_PITCH_SPEED_LAW', pse['flags'])

    def test_signatures_and_screens_fail_soft(self):
        def boom(*a, **k):
            raise ValueError('planted <b>& error')
        for target, flag, key in (('pitch_speed_exponent', 'PITCH_SPEED_LAW_FAILED', None),
                                  ('source_catalogue', bd.SIGNATURES_FAILED_FLAG, 'signatures'),
                                  ('herringbone_screen', bd.SCREENS_FAILED_FLAG, 'screens'),
                                  ('luders_susceptibility', bd.SCREENS_FAILED_FLAG, 'screens')):
            cases = [v1case(pitch_observations=[_p(10, 0.03), _p(14, 0.042)])]
            if key == 'screens':  # the lengthwise facts read the screens too
                cases.append(v2case(pitch_observations=[_p(10, 0.03), _p(14, 0.042)]))
            for case in cases:
                with self.subTest(target), mock.patch.object(bd.bs, target, boom):
                    r, html = _ok(self, case, target)
                    self.assertIn(flag, r['flags'])
                    if key:
                        self.assertEqual(r[key]['status'], 'FAILED')
                    self.assertIn('planted &lt;b&gt;&amp; error', html)
                    self.assertNotIn('planted <b>&', html)

    def test_rejected_at_validation(self):
        # rejected on purpose: a zero duration is no observation (use null), a band spacing
        # above 10 m is beyond any strip, an event of zero duration switches nothing
        for obs, msg in ((dict(intermittent_duration_s=0.0),
                          'observation.intermittent_duration_s must be > 0'),
                         (dict(band_spacing_m=50.0), 'observation.band_spacing_m must be <= 10')):
            with self.assertRaisesRegex(ValueError, msg):
                diagnose(v2case(**obs))
        c = v2case(width=True)
        c['width_model']['events'][0]['duration_s'] = 0.0
        with self.assertRaisesRegex(ValueError, r'width_model.events\[0\].duration_s must be > 0'):
            diagnose(c)


class CoilSingleSourceTests(unittest.TestCase):
    """Review finding: every pitch is judged against the one coil that fits all of them best,
    never each against its own nearest coil."""

    @staticmethod
    def _run(pitches, first_seen='incoming_strip'):
        import math
        c = v2(first_seen=first_seen, pitch_observations=[
            {'exit_speed_m_s': u, 'pitch_m': pm} for u, pm in pitches])
        c['kinematics']['entry_coil_diameter_m'] = 0.7 / math.pi
        c['kinematics']['exit_coil_diameter_m'] = 1.4 / math.pi
        r = diagnose(c)
        h = _h(r)['coil_or_mandrel_locked_marks']
        return r, h, h['evidence'][0]

    def test_mixed_sources_give_no_strong_support(self):
        # entry-coil pitch 0.7/pi*pi*h0/h1 = 1.0 m, exit-coil pitch 1.4 m
        r, h, e = self._run([(2.0, 1.0), (20.0, 1.4)])
        self.assertEqual((e['verdict'], e['weight']), ('CONTRADICTS', 'weak'))
        self.assertIn('the same coil (entry coil, the best single fit) is applied to every pitch',
                      e['observed'])
        self.assertNotIn('coil_or_mandrel_locked_marks', r['leading_hypotheses'])
        self.assertEqual(h['model_prediction']['matched_coil'], 'entry coil')

    def test_two_pitches_on_one_coil_still_support(self):
        r, h, e = self._run([(2.0, 1.4), (20.0, 1.41)])
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertNotIn('the same coil', e['observed'])     # no mixed sources to explain
        self.assertEqual(h['model_prediction']['matched_coil'], 'exit coil')

    def test_single_pitch_as_before(self):
        r, h, e = self._run([(2.0, 1.0)])
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertIn('entry coil pitch 1 m, mismatch 0.0%', e['observed'])


class TroughSpacingEstablishedTests(unittest.TestCase):
    """Review fix: one gap, or irregular gaps, cannot establish a trough spacing."""

    @staticmethod
    def _troughs(positions=(), spacing=None):
        from types import SimpleNamespace
        from physicroll import band_width as bw
        obs = validate_case(v2(band_positions_across_width_m=list(positions),
                               band_spacing_m=spacing, orientation='longitudinal'))[
            'observation']
        gaps, sp, _ = bw.observed_gaps(obs)
        f = SimpleNamespace(obs=obs, gaps=gaps, spacing=sp, positions=list(positions),
                            troughs={'exit_span': {'wrinkle_wavelength_m': 0.4,
                                                   'status': 'LATERAL_STRESS_UNKNOWN'}},
                            exit_thickness=0.21e-3, crown_class=None, strip_centre=0.85)
        e, _ = bw._h_troughs(f)
        return next(x for x in e if x['criterion'] == 'spacing vs trough wavelength')

    def test_one_gap_is_weak_and_never_contradicts(self):
        e = self._troughs([0.5, 0.9])
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'weak'))
        self.assertIn('one gap between two bands cannot establish a spacing', e['observed'])
        e = self._troughs([0.5, 0.55])           # 0.125 x wavelength, would have contradicted
        self.assertEqual(e['verdict'], 'NEUTRAL')

    def test_irregular_gaps_are_weak(self):
        e = self._troughs([0.357, 0.667, 1.093])  # the lengthwise demo's positions
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'weak'))
        self.assertIn('irregular gaps cannot establish a spacing', e['observed'])

    def test_regular_or_stated_spacing_keeps_strong_support(self):
        e = self._troughs([0.4, 0.8, 1.2])
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        e = self._troughs([0.4, 0.8], spacing=0.4)
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        e = self._troughs([0.4, 0.45, 0.5], spacing=0.05)
        self.assertEqual((e['verdict'], e['weight']), ('CONTRADICTS', 'moderate'))


if __name__ == '__main__':
    unittest.main()
