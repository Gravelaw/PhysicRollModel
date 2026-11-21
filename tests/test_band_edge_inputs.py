"""Inputs at the edge of what validation accepts (review round 3 audit), on the short roll of
``test_band_flatness_loop`` (fast): an answer that is not a measurement is not assessed, and a
ratio that grows without bound is not reported as a number."""
import json
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_sensors as bsn
from physicroll.band_report import render_band_report
from tests.test_band_flatness_loop import _short


def _case(**w):
    c = _short()
    c['width_model']['flatness_control'] = None
    c['width_model'].update(w)
    return c


class RollProfileOutsideTheStrip(unittest.TestCase):
    def test_profile_entirely_outside_the_strip_is_not_assessed(self):
        # strip 0.05 to 0.55 m; a scan of 0 to 0.04 m held over the whole strip read as a flat
        # roll before (NO_BANDS_ABOVE_THRESHOLD)
        r = bd.diagnose(_case(roll_ground_profile={
            'positions_m': [0.0, 0.01, 0.02, 0.03, 0.04],
            'radius_deviation_m': [0.0, 1e-6, 0.0, -1e-6, 0.0], 'provenance': 'unit test'}))
        rp = r['width']['roll_profile']
        self.assertEqual(rp['status'], 'NOT_ASSESSABLE')
        self.assertIn('lies entirely outside the strip', rp['reason'])
        render_band_report(r)

    def test_profile_over_the_strip_is_assessed(self):
        r = bd.diagnose(_case(roll_ground_profile={
            'positions_m': [0.05, 0.15, 0.3, 0.45, 0.55],
            'radius_deviation_m': [0.0, 1e-6, 0.0, -1e-6, 0.0], 'provenance': 'unit test'}))
        self.assertNotEqual(r['width']['roll_profile']['status'], 'NOT_ASSESSABLE')


class GaugeSpotLongerThanTheMarks(unittest.TestCase):
    def test_amplitude_not_bounded_near_a_zero_of_the_spot_average(self):
        # a 1 m spot on 10 mm marks: gain 6e-18; amplitude/gain was 1.6e11 m before
        c = _case()
        c['measurement']['thickness_gauge'] = {'spot_length_m': 1.0, 'time_constant_s': 0.0,
                                               'provenance': 'unit test'}
        c['observation'].update(pitch_observations=[{'pitch_m': 0.01, 'exit_speed_m_s': 10.0},
                                                    {'pitch_m': 3.0, 'exit_speed_m_s': 10.0}],
                                gauge_variation_amplitude_m=1e-6)
        r = bd.diagnose(c)
        rows = r['measurement']['thickness_gauge']['rows']
        short, long_ = rows[0], rows[1]
        self.assertLess(short['combined_gain'], bsn.GAUGE_AMPLITUDE_MIN_GAIN)
        self.assertIsNone(short['amplitude_before_gauge_m'])
        self.assertIn('does not bound its amplitude', short['amplitude_note'])
        self.assertGreaterEqual(long_['combined_gain'], bsn.GAUGE_AMPLITUDE_MIN_GAIN)
        self.assertAlmostEqual(long_['amplitude_before_gauge_m'],
                               1e-6 / long_['combined_gain'], places=15)
        json.loads(bd.result_json(r))


class OutsideTheShapeModelRange(unittest.TestCase):
    def test_sprays_off_is_outside_the_screen_not_failed(self):
        # before: shape.steady FAILED "local_radius_deviation_m[12] must be <= 0.001" (all off)
        # and "elongation[8] must be >= -0.5" (one nozzle on); the same in thermal_sensitivity
        from physicroll import band_plain as bpl
        from physicroll import band_width as bw
        for levels, words in (([0.0] * 8, 'the roll would grow locally by'),
                              ([0.0] * 3 + [1.0] + [0.0] * 4,
                               'the strip would stretch unevenly across its width by')):
            r = bd.diagnose(_case(nozzle_levels=levels))
            st = r['width']['shape']['steady']
            self.assertEqual(st['status'], 'NOT_ASSESSABLE')
            self.assertTrue(st['outside_model_range'])
            self.assertIn(words, st['reason'])
            self.assertIn('outside the model\'s range', st['reason'])
            ts = r['width']['thermal_sensitivity']
            self.assertEqual(ts['status'], 'NOT_ASSESSABLE')
            self.assertIn('not assessed: ' + st['reason'], ts['reason'])
            self.assertEqual(r['width']['failures'], [])
            self.assertIn(bw.SHAPE_FLAG_OUTSIDE_RANGE, r['flags'])
            self.assertIn(bw.SHAPE_FLAG_OUTSIDE_RANGE, bpl.FLAGS)
            self.assertNotIn('must be', json.dumps(r['width']['shape']))
            render_band_report(r)
            bpl.plain_summary(r)


class SpanWithoutTension(unittest.TestCase):
    def test_zero_exit_tension_is_not_assessed(self):
        from tests.test_band_foil import foil_case
        c = foil_case(schedule=False, appearance='crease_or_flute', changes_with_tension=True)
        c['width_model']['span_alignment'] = {'exit_span': {'misalignment_m_per_m': 1e-3},
                                              'provenance': 'unit test'}
        c['pass']['exit_tension_pa'] = 0.0
        r = bd.diagnose(c)
        t = r['width']['troughs']['exit_span']
        self.assertEqual(t['status'], 'NOT_ASSESSABLE')
        self.assertIn('no span tension entered, so trough onset cannot be assessed',
                      t['reason'])
        self.assertNotEqual(r['width']['troughs']['entry_span']['status'], 'NOT_ASSESSABLE')
        self.assertIn('no span tension entered', render_band_report(r))


class VoceFitOfIdenticalStrengths(unittest.TestCase):
    def test_characteristic_strain_not_determined(self):
        from physicroll import bite_tribology as bt
        r = bt.fit_voce_to_pass_strengths([2e-3, 1e-3, 0.5e-3], [200e6] * 3,
                                          reference_thickness_m=2e-3)
        self.assertIsNone(r['parameters']['characteristic_strain'])
        self.assertIn(bt.FIT_EC_NOT_DETERMINED, r['flags'])
        self.assertIn('not determined', r['characteristic_strain_reason'])
        self.assertEqual(r['law_rejected_by_validation'], r['characteristic_strain_reason'])
        self.assertIsNone(r['first_parabola_characteristic_strain'])
        json.dumps(r, allow_nan=False)
        ok = bt.fit_voce_to_pass_strengths([2e-3, 1e-3, 0.5e-3], [150e6, 200e6, 230e6],
                                           reference_thickness_m=2e-3)
        self.assertIsNotNone(ok['parameters']['characteristic_strain'])
        self.assertNotIn(bt.FIT_EC_NOT_DETERMINED, ok['flags'])

class OneNullTwoMeanings(unittest.TestCase):
    """Sentences that read a missing value as one of two outcomes."""

    def _loop(self, **kw):
        from physicroll import band_plain as bpl
        fg = {'status': 'X', 'sensitivities': {'percent': {}}, 'flags': [],
              'loop': {'sensitivity_at': []}, 'step_response': {}}
        fg.update(kw)
        return bpl._gauge_loop_view({'foil_gauge_control': fg})

    def test_gauge_loop_sentences(self):
        v = self._loop()                            # no coil diameter: not "does not amplify"
        self.assertIn('was not checked: no coil diameter was entered', v['loop_text'])
        v = self._loop(loop={'sensitivity_at': [{'name': 'entry_coil_1x', 'amplifies': False}]})
        self.assertIn('does not make a coil', v['loop_text'])
        v = self._loop(step_response={'not_run': True, 'reason': 'the gain crossover was not '
                                      'found'})
        self.assertIn('was not simulated: the gain crossover was not found', v['trim_text'])
        v = self._loop(step_response={'linear_no_limits': {
            'status': 'NOT_SETTLED_WITHIN_HORIZON', 'settling_time_s': None, 'horizon_s': 20.0}})
        self.assertIn('does not settle it within the 20 s run', v['trim_text'])
        v = self._loop(step_response={'linear_no_limits': {'status': 'SETTLED',
                                                           'settling_time_s': 0.54}})
        self.assertIn('corrected within the tension trim in about 0.54 s', v['trim_text'])

    def test_strip_temperature_band_gone_after_cooling(self):
        from physicroll import band_plain as bpl
        change = {'profile': 'as_measured_hot', 'peak_position_m': 0.3, 'peak_i_units': 12.0,
                  'other_peak_i_units': None, 'state_differs': True}
        for mech, words in ((True, 'no band is left at that position'),
                            (False, 'no modelled flatness for this pass')):
            st = {'status': 'X', 'profiles': {'mechanical': {'available': mech},
                                               'as_measured_hot': {}},
                  'state_changes': [change]}
            v = bpl._temperature_flatness_view({'width': {'strip_temperature': st}})
            self.assertIn(words, v['text'])

class TerseNullsWorded(unittest.TestCase):
    def test_time_to_fall_below_each_outcome(self):
        from physicroll import band_plain as bpl
        from physicroll import band_report as brp
        base = {'limit': 'leaving_final_pass', 'limit_k': 353.15, 'longest_hold_time_s': 86400.0}
        for st, t, report, app in (
                ('FOUND', 7200.0, 'falls below after 2 h', 'after about 2 h'),
                ('BELOW_AT_WINDING', 0.0, 'already below at winding', 'already below'),
                ('LIMIT_BELOW_AMBIENT', None, 'the limit is below the surrounding temperature, '
                 'so the coil never gets there', 'never gets there'),
                ('NOT_REACHED_WITHIN_LONGEST_HOLD', None, 'not reached within the longest hold '
                 'time entered (24 h)', 'within the longest hold time you entered (24 h)')):
            r = dict(base, time_to_fall_below_s=t, time_to_fall_below_status=st)
            self.assertEqual(brp.fall_below_text(r), report)
            self.assertIn(app, bpl._fall_below_words(r))
            self.assertNotIn('n/a', brp.fall_below_text(r))

    def test_coil_rows_carry_the_status(self):
        from tests.test_band_coil_temperature import CT, quick_battery
        c = quick_battery()
        c['width_model']['coil_thermal'] = dict(CT, interlayer_gap_m=1e-6, hold_times_s=[60.0])
        r = bd.diagnose(c)
        rows = r['width']['coil_temperature']['limit_rows']
        self.assertTrue(rows)
        for x in rows:
            self.assertIn(x['time_to_fall_below_status'], ('FOUND', 'BELOW_AT_WINDING',
                                                           'LIMIT_BELOW_AMBIENT',
                                                           'NOT_REACHED_WITHIN_LONGEST_HOLD'))
            if x['time_to_fall_below_s'] is None:
                self.assertNotEqual(x['time_to_fall_below_status'], 'FOUND')
        html = render_band_report(r)
        self.assertNotIn('falls below after n/a', html)

    def test_attenuation_band_each_outcome(self):
        from physicroll import band_report as brp
        self.assertEqual(brp.attenuation_text({'attenuates_below_hz': 0.521}),
                         'disturbances are reduced below 0.521 Hz')
        self.assertIn('does not amplify a disturbance at any frequency of the scan (up to 242 Hz)',
                      brp.attenuation_text({'attenuates_below_hz': None}))
        self.assertIn('was not found', brp.attenuation_text(
            {'attenuates_below_hz': None, 'attenuation_edge_below_scan_start': True}))

    def test_foil_step_not_settled_has_no_na(self):
        from physicroll import band_report as brp
        r = bd.diagnose(_fg_slow())
        self.assertIsNone(r['foil_gauge_control']['step_response']['linear_no_limits'][
            'settling_time_s'])
        html = render_band_report(r)
        self.assertIn('not within 5 % by the end of the 20 s run', html)
        self.assertNotIn('after n/a s', html)
        self.assertIsNotNone(brp)


def _fg_slow():
    from tests.test_foil_gauge import FGC, _case as fg_case
    return fg_case(FGC, integral_crossover_rad_s=0.005)

if __name__ == '__main__':
    unittest.main()
