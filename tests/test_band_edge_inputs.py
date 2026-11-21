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


if __name__ == '__main__':
    unittest.main()
