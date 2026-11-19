"""Review of 6ad7e48 (band_thermal): a build-up percentage not reached inside the simulated
horizon (``steady_build_up`` stores None) is reported in words, with the horizon, and never
makes the thermal check fail."""
import json
import pathlib
import unittest
from unittest import mock

from physicroll import band_thermal as bt
from physicroll.band_diagnosis import diagnose
from physicroll.band_report import render_band_report
from tests.test_band_robustness import v2case

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _slow_roll_case():
    # reviewer: work-roll radius 0.4 m (case['pass']['work_roll_radius_m']), no events, full
    # mode: 50 % at about 392 s, 90 % not reached inside the 1800 s horizon
    c = v2case(width=True)
    c['pass']['work_roll_radius_m'] = 0.4
    c['width_model']['events'] = []
    c['model_options']['thermal_sensitivity'] = 'full'
    return c


class BuildUpNotReachedTests(unittest.TestCase):
    def test_reviewer_case_ninety_percent_not_reached(self):
        r = diagnose(_slow_roll_case())
        b = r['width']['thermal_sensitivity']['steady_build_up']
        self.assertEqual(b['status'], 'EVALUATED')
        self.assertAlmostEqual(b['time_to_50_percent_s'], 392, delta=5)
        self.assertIsNone(b['time_to_90_percent_s'])
        self.assertEqual(b['percentages_not_reached'], [90, 95])
        self.assertIn('not reached within the simulated 1800 s', b['not_reached_note'])
        tc = r['thermal_check']
        self.assertNotEqual(tc['status'], 'FAILED')
        self.assertNotIn('THERMAL_CHECK_FAILED', r['flags'])
        g = tc['growth']
        self.assertEqual(g['steady_build_up']['percentages_not_reached'], [90, 95])
        self.assertEqual(g['steady_build_up']['simulated_s'], 1800.0)
        self.assertIn('builds up to 50 % in 392 s but does not reach 90 % within the '
                      'simulated 1800 s', g['text'])
        self.assertIn(g['text'], render_band_report(r).replace('&#x27;', "'"))

    def test_nothing_reached(self):
        # the same case with a 60 s horizon: not even 50 % is reached
        with mock.patch.object(bt, 'BUILD_UP_S', 60.0):
            r = diagnose(_slow_roll_case())
        b = r['width']['thermal_sensitivity']['steady_build_up']
        self.assertEqual(b['simulated_s'], 60.0)
        self.assertTrue(all(b[f'time_to_{p}_percent_s'] is None for p in (50, 63, 90, 95)))
        self.assertEqual(b['percentages_not_reached'], [50, 63, 90, 95])
        tc = r['thermal_check']
        self.assertNotEqual(tc['status'], 'FAILED')
        self.assertIn('the steady stripe does not reach 50 % or 90 % within the simulated 60 s',
                      tc['growth']['text'])
        render_band_report(r)

    def test_text_words(self):
        self.assertEqual(bt.build_up_text({'time_to_50_percent_s': 116.0,
                                           'time_to_90_percent_s': 551.0}),
                         'the steady stripe builds up to 50 % in 116 s and to 90 % in 551 s')
        self.assertEqual(bt.build_up_text({'time_to_50_percent_s': None,
                                           'time_to_90_percent_s': None,
                                           'simulated_s': 1800.0, 'fraction_at_end': 0.3}),
                         'the steady stripe does not reach 50 % or 90 % within the simulated '
                         '1800 s, 30 % at its end')

    def test_battery_demo_text_unchanged(self):
        r = json.loads((ROOT / 'artifacts' / 'band_diagnosis'
                        / 'battery-foil-demo.result.json').read_text(encoding='utf-8'))
        g = r['thermal_check']['growth']
        self.assertEqual(g['steady_build_up']['percentages_not_reached'], [])
        self.assertIn('the steady stripe builds up to 50 % in 116 s and to 90 % in 551 s '
                      '(radial time constant', g['text'])


if __name__ == '__main__':
    unittest.main()
