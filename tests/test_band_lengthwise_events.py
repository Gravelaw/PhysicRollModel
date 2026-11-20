"""Event attribution, the lengthwise scenario and the spray layout tests, split from
tests/test_band_lengthwise.py to keep each module under the time limit; fixtures are
shared from there."""
import unittest

from tests import test_band_lengthwise as _base

# the shared fixtures, helpers and imports of the original module (test classes excluded,
# so no test runs twice)
globals().update({k: v for k, v in vars(_base).items() if not k.startswith('__')
                  and not (isinstance(v, type) and issubclass(v, unittest.TestCase))})


class EventAttributionTests(unittest.TestCase):
    """Reproducers of code-review findings 3, 4 and 6 (zone-switching event metrics); supplied
    bite heat 1e6 W/m, coarse numerics (5 s time step)."""

    @classmethod
    def setUpClass(cls):
        def run(events):
            c = v2(**LONG)
            c['width_model'] = width_model(bite_heat_per_width_w_m=1e6, events=events)
            return diagnose(c)
        cls.same = run([{'start_s': 0.0, 'duration_s': 5.0, 'nozzle_indices': [12], 'level': 0.0},
                        {'start_s': 100.0, 'duration_s': 90.0, 'nozzle_indices': [12],
                         'level': 0.0}])
        cls.short = run([{'start_s': 0.0, 'duration_s': 2.0, 'nozzle_indices': [16],
                          'level': 0.0}])
        cls.split = run([{'start_s': 0.0, 'duration_s': 30.0, 'nozzle_indices': [6, 26],
                          'level': 0.0}])

    def test_later_event_on_same_nozzle_not_attributed_to_earlier(self):
        # finding 3: the 5 s event reported the 90 s event's peak (at t = 190 s) and a band
        # life of 222 s that included the later event
        first, second = self.same['width']['thermal_events']['events']
        self.assertEqual(first['attribution_window_end_s'], 100.0)
        self.assertLessEqual(first['time_of_peak_s'], 100.0)
        self.assertLess(first['peak_deviation_m'], 0.25 * second['peak_deviation_m'])
        self.assertIn('LATER_EVENT_IN_SAME_REGION', first['flags'])
        # the stripe of the 5 s event is still above the reporting threshold when the second
        # event starts: its life is only bounded, never the combined value
        self.assertIsNone(first['band_life_s'])
        self.assertEqual(first['band_life_lower_bound_s'], 100.0)
        self.assertIn('FADE_BEYOND_ATTRIBUTION_WINDOW', first['flags'])
        self.assertIn('EARLIER_EVENT_IN_SAME_REGION', second['flags'])
        self.assertAlmostEqual(second['time_of_peak_s'], 90.0)
        self.assertGreater(second['band_life_s'], 90.0)
        html = render_band_report(self.same)
        self.assertIn('not attributable after 100 s', html)

    def test_short_event_peak_profile_is_the_measured_peak(self):
        # finding 4: a 2 s outage (shorter than the 5 s snapshot interval) took the snapshot at
        # t = 0 (unchanged state): zero deviation and BELOW_REPORTING_THRESHOLD
        ev = self.short['width']['thermal_events']['events'][0]
        self.assertEqual(ev['time_of_peak_s'], 2.0)
        self.assertEqual(ev['peak_snapshot_time_s'], ev['time_of_peak_s'])
        self.assertGreater(ev['stripe_peak_deviation_m'], 1.5e-7)
        self.assertLess(abs(ev['stripe_peak_position_m'] - NOZZLES[16]), 0.021)
        shape = ev['peak_shape']
        self.assertGreater(shape['feedback_peak_i_units'], shape['reporting_threshold_i_units'])
        self.assertNotEqual(ev['peak_state_with_feedback'], 'BELOW_REPORTING_THRESHOLD')
        self.assertIsNotNone(ev['reporting_threshold_m'])

    def test_separated_nozzles_monitored_per_stripe(self):
        # finding 6: nozzles 6 and 26 were monitored at their mean position (an unaffected
        # region, ~ -3 nm) although both nozzle positions grow ~2.08 um
        ev = self.split['width']['thermal_events']['events'][0]
        stripes = ev['stripes']
        self.assertEqual([s['nozzle_indices'] for s in stripes], [[6], [26]])
        self.assertEqual([s['monitor_position_m'] for s in stripes], [NOZZLES[6], NOZZLES[26]])
        for s in stripes:
            self.assertGreater(s['peak_deviation_m'], 1.9e-6)
        gov = stripes[ev['governing_stripe_index']]
        self.assertTrue(gov['governing'])
        self.assertEqual(ev['monitor_position_m'], gov['monitor_position_m'])
        self.assertEqual(ev['peak_deviation_m'], max(s['peak_deviation_m'] for s in stripes))
        self.assertNotEqual(ev['peak_state_with_feedback'], 'BELOW_REPORTING_THRESHOLD')
        self.assertGreater(ev['reporting_threshold_m'], 0)
        self.assertGreater(ev['band_life_s'], ev['duration_s'])
        html = render_band_report(self.split)
        self.assertIn('stripes (one monitor per group of adjacent nozzles)', html)


class LengthwiseScenarioTests(unittest.TestCase):
    def test_scenarios_load(self):
        names = ('band_diagnosis_template.json', 'band_diagnosis_thin_gauge_chatter.json',
                 'band_diagnosis_bearing_order.json', 'band_diagnosis_lengthwise_bands.json')
        for name in names:
            load_case(SCEN / name)
        t = load_case(SCEN / 'band_diagnosis_template.json')
        self.assertEqual(t['case_schema'], CASE_SCHEMA_V2)
        self.assertTrue(all(v in (None, []) for v in t['observation'].values()))
        demo = load_case(SCEN / 'band_diagnosis_lengthwise_bands.json')
        self.assertIn('GENERATED FROM THE MODEL', demo['provenance'])
        # SPEC6 6.5 lengthwise demo: coarse cells and thermal numerics, same leading hypothesis
        demo['model_options']['cells'] = 64
        demo['width_model']['numerics'] = dict(COARSE)
        # gauge_trend, the schedule sweep and the per-pass friction do not enter the evidence:
        # keep only the final schedule pass (= the case pass) to save time
        demo['schedule'] = demo['schedule'][-1:]
        r = diagnose(demo)
        self.assertEqual(r['leading_hypotheses'], ['nozzle_thermal_stripe'])
        self.assertEqual(_h(r)['cooling_zone_switching_transient']['standing'], 'CONSISTENT')
        self.assertEqual(r['family_summary']['observed_family'], 'lengthwise')
        self.assertTrue(2e-6 < r['width']['thermal_steady']['healthy_thermal_crown_m'] < 16e-6)
        # (the two phase-1 demos are run in tests.test_band_diagnosis)


class SprayLayoutTests(unittest.TestCase):
    """band_width.spray_layout: the header and strip as the width section reads them."""

    def assert_matches(self, layout, ts):
        self.assertEqual(layout['nozzle_positions_m'], ts['nozzle_positions_m'])
        self.assertEqual(layout['nozzle_levels'], ts['nozzle_levels'])
        self.assertEqual(layout['effective_footprint_width_m'],
                         ts['effective_footprint_width_m'])
        for k in ('strip_start_m', 'strip_end_m', 'strip_centre_m'):
            self.assertEqual(layout[k], ts[k], k)

    def test_lengthwise_demo_without_blocked_indices(self):
        import json
        r = json.loads((ROOT / 'artifacts' / 'band_diagnosis'
                        / 'lengthwise-bands-demo.result.json').read_text())
        self.assertEqual(r['inputs']['width_model']['blocked_nozzle_indices'], [])
        self.assert_matches(bw.spray_layout(r['inputs']), r['width']['thermal_steady'])

    def test_lengthwise_demo_with_blocked_indices(self):
        demo = load_case(SCEN / 'band_diagnosis_lengthwise_bands.json')
        demo['model_options']['cells'] = 64
        demo['width_model']['numerics'] = dict(COARSE)
        demo['schedule'] = demo['schedule'][-1:]
        demo['width_model']['blocked_nozzle_indices'] = [3, 12]      # 12 is also weak (0.45)
        layout = bw.spray_layout(demo)
        self.assertEqual([layout['nozzle_levels'][i] for i in (3, 12)], [0.0, 0.0])
        self.assert_matches(layout, diagnose(demo)['width']['thermal_steady'])

    def test_invalid_cases_raise_the_width_model_errors(self):
        demo = load_case(SCEN / 'band_diagnosis_lengthwise_bands.json')
        bad = copy.deepcopy(demo)
        bad['width_model']['blocked_nozzle_indices'] = [99]
        with self.assertRaisesRegex(ValueError, 'nozzle index 99 out of range'):
            bw.spray_layout(bad)
        bad = copy.deepcopy(demo)
        bad['width_model'] = None
        with self.assertRaises(ValueError):
            bw.spray_layout(bad)

if __name__ == '__main__':
    unittest.main()
