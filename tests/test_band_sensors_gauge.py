"""SPEC17 package 5: the thickness-gauge transfer (``band_sensors.thickness_gauge_section``).

What a gauge with a spot length and a first-order time constant keeps of a mark pitch, and the
flags on observations it cannot resolve. Open decision 2: FLAG ONLY - the evidence item "gauge
variation not detected" counts exactly as without a gauge (tested on a v2 copy of the
thin-gauge chatter demo). Split from tests/test_band_sensors.py to keep each module under 60 s.
"""
import copy
import json
import math
import unittest
from pathlib import Path

from physicroll import band_sensors as bs
from physicroll.band_diagnosis import diagnose, load_case, validate_case
from physicroll.band_plain import as_v2
from physicroll.band_report import render_band_report

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'band_diagnosis'
G = {'spot_length_m': 0.010, 'time_constant_s': 0.005, 'sample_interval_s': 0.001,
     'position_m': None, 'spot_width_m': None, 'provenance': 'unit test gauge <x>'}


class GainTests(unittest.TestCase):

    def test_closed_form_gains(self):
        g = bs.validate_thickness_gauge(G)
        for (p, u), want in (((0.08408, 16.0), (190.2950, 0.976894, 0.164980, 0.161168)),
                             ((0.07647, 14.5), (189.6168, 0.972107, 0.165554, 0.160936)),
                             ((0.024921, 7.8333), (314.3253, 0.755406, 0.100752, 0.076109))):
            r = bs.gauge_row('x', p, u, g)
            self.assertAlmostEqual(r['frequency_hz'], want[0], delta=1e-4)
            self.assertAlmostEqual(r['spot_gain'], want[1], delta=1e-6)
            self.assertAlmostEqual(r['time_constant_gain'], want[2], delta=1e-6)
            self.assertAlmostEqual(r['combined_gain'], want[3], delta=1e-6)
            self.assertIs(r['aliased'], False)
            self.assertIs(r['resolvable'], False)

    def test_limits_aliasing_and_shortest_pitch(self):
        self.assertAlmostEqual(bs.spot_gain(1e-12, 0.05), 1.0, places=12)
        self.assertAlmostEqual(bs.spot_gain(0.05, 0.05), 0.0, places=12)
        self.assertEqual(bs.time_constant_gain(0.0, 500.0), 1.0)
        g = dict(G, time_constant_s=0.0)
        self.assertTrue(bs.gauge_row('x', 0.01, 10.0, g)['aliased'])          # 1000 Hz > 500
        self.assertFalse(bs.gauge_row('x', 0.03, 10.0, g)['aliased'])         # 333 Hz
        self.assertIsNone(bs.gauge_row('x', 0.03, 10.0, dict(g, sample_interval_s=None))[
            'aliased'])
        self.assertTrue(bs.gauge_row('x', 0.03, 10.0, dict(g, sample_interval_s=None))[
            'resolvable'])
        p = bs.shortest_resolvable_pitch_m(G, 16.0)
        gain = (bs.spot_gain(0.010, p) * bs.time_constant_gain(0.005, 16.0 / p))
        self.assertAlmostEqual(gain, 0.5, places=9)
        for q in (1.001 * p, 2 * p, 9.0):                 # every longer pitch is kept
            self.assertGreaterEqual(bs.gauge_row('x', q, 16.0, G)['combined_gain'], 0.5)
        self.assertIsNone(bs.shortest_resolvable_pitch_m(dict(G, time_constant_s=10.0), 16.0))
        self.assertAlmostEqual(10.0 * 0.005, 0.05)          # u*tau at 10 m/s

    def test_validation(self):
        for key, value, msg in (('spot_length_m', 0.0, 'spot_length_m must be in (0, 1] m'),
                                ('time_constant_s', -1.0, 'time_constant_s must be in [0, 10] s'),
                                ('sample_interval_s', 0.0, 'sample_interval_s must be in (0, 10]'),
                                ('position_m', 11.0, 'position_m must be on the barrel'),
                                ('spot_width_m', 2.0, 'spot_width_m must be in (0, 1] m or null'),
                                ('provenance', '', 'provenance must be a nonempty string')):
            with self.assertRaises(ValueError) as cm:
                bs.validate_thickness_gauge(dict(G, **{key: value}))
            self.assertIn('measurement.thickness_gauge.' + msg, str(cm.exception))
        with self.assertRaises(ValueError):
            bs.validate_thickness_gauge(dict(G, colour='red'))
        raw = json.loads((ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json').read_text())
        raw['measurement']['thickness_gauge'] = dict(G, position_m=1.6)      # barrel 1.5 m
        with self.assertRaisesRegex(ValueError, 'position_m must be on the barrel'):
            validate_case(raw)


class BandsUnderGaugeTests(unittest.TestCase):

    def test_bands_under_the_gauge_on_the_battery_profile(self):
        r = json.loads((ART / 'battery-foil-demo.result.json').read_text())
        case = validate_case(load_case(ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json'))
        case['measurement']['thickness_gauge'] = bs.validate_thickness_gauge(G)
        tg = bs.thickness_gauge_section(case, r)
        self.assertEqual(tg['position_m'], 0.75)                 # the strip centre
        self.assertEqual([(round(b['start_m'], 3), round(b['end_m'], 3))
                          for b in tg['bands_under_gauge']], [(0.49, 0.75)])
        self.assertNotIn(bs.GAUGE_FLAG_BANDS, tg['flags'])
        self.assertEqual(tg['rows'], [])                         # no pitch, no chatter onset
        self.assertAlmostEqual(tg['averaging_length_time_constant_m'],
                               case['pass']['exit_speed_m_s'] * 0.005)
        case['measurement']['thickness_gauge'] = bs.validate_thickness_gauge(
            dict(G, position_m=0.77, spot_width_m=0.02))
        tg = bs.thickness_gauge_section(case, r)
        self.assertEqual(tg['bands_under_gauge'], [])
        self.assertIn(bs.GAUGE_FLAG_BANDS, tg['flags'])
        self.assertIn('other filters', ' '.join(tg['limitations']))


class ChatterDemoFlagTests(unittest.TestCase):
    """Open decision 2 (flag only) on a v2 copy of the thin-gauge chatter demo."""

    @classmethod
    def setUpClass(cls):
        c = as_v2(load_case(ROOT / 'scenarios' / 'band_diagnosis_thin_gauge_chatter.json'))
        c['observation']['gauge_variation_detected'] = False
        c['observation']['gauge_variation_amplitude_m'] = 2e-6
        cls.base = diagnose(copy.deepcopy(c))
        c['measurement'] = {'shapemeter': None, 'thickness_gauge': dict(G)}
        cls.gauge = diagnose(c)

    def test_flags_set_and_tally_unchanged(self):
        tg = self.gauge['measurement']['thickness_gauge']
        for f in (bs.GAUGE_FLAG_APPLIED, bs.GAUGE_FLAG_LESS_THAN_HALF,
                  bs.GAUGE_FLAG_NOT_DETECTED):
            self.assertIn(f, self.gauge['flags'])
            self.assertIn(f, tg['flags'])
        self.assertEqual(set(self.gauge['flags']) - set(self.base['flags']),
                         {bs.GAUGE_FLAG_APPLIED, bs.GAUGE_FLAG_LESS_THAN_HALF,
                          bs.GAUGE_FLAG_NOT_DETECTED})
        self.assertEqual(self.gauge['hypotheses'], self.base['hypotheses'])   # every item
        self.assertEqual(self.gauge['leading_hypotheses'], self.base['leading_hypotheses'])
        self.assertIn('tally is NOT changed', tg['not_detected_note'])
        users = [h['id'] for h in self.gauge['hypotheses']
                 if any(e['criterion'].startswith('gauge variation') for e in h['evidence'])]
        self.assertTrue(users)
        self.assertEqual(tg['hypotheses_using_the_observation'], users)
        for hid in users:
            self.assertIn(hid, tg['not_detected_note'])
        rows = {r['source']: r for r in tg['rows']}
        self.assertAlmostEqual(rows['pitch_observations[1]']['combined_gain'], 0.161168,
                               delta=1e-6)
        self.assertAlmostEqual(rows['pitch_observations[1]']['amplitude_before_gauge_m'],
                               2e-6 / 0.161168, delta=1e-10)
        self.assertIn('chatter.with_bite_damping.onset_frequency_hz', rows)
        for k in self.base:
            if k not in ('measurement', 'inputs', 'flags'):
                self.assertEqual(self.base[k], self.gauge[k], k)

    def test_report_table_renders(self):
        html = render_band_report(self.gauge)
        self.assertIn('What the thickness gauge keeps', html)
        self.assertIn('keeps about', html)
        self.assertIn('real gauges have other filters', html)
        self.assertIn('unit test gauge &lt;x&gt;', html)
        self.assertNotIn('>nan<', html)
        json.dumps(self.gauge['measurement'], allow_nan=False)


if __name__ == '__main__':
    unittest.main()
