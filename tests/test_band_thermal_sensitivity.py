"""SPEC14 part 3: width.thermal_sensitivity (heat partition and spray coefficient)."""
import copy
import json
import unittest

from physicroll import band_thermal as bt
from physicroll.band_diagnosis import diagnose, validate_case
from physicroll.band_report import render_band_report
from tests.test_band_robustness import v2case


class SensitivityBlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = v2case(width=True)
        cls.r = diagnose(copy.deepcopy(cls.case))
        full = copy.deepcopy(cls.case)
        full['model_options']['thermal_sensitivity'] = 'full'
        cls.full = diagnose(full)

    def test_default_partition_rows(self):
        ts = self.r['width']['thermal_sensitivity']
        self.assertEqual((ts['status'], ts['mode']), ('EVALUATED', 'partition'))
        self.assertEqual([s['strip_heat_share'] for s in ts['shares']], [0.84, 0.33, 0.11])
        for s in ts['shares']:
            self.assertAlmostEqual(s['roll_heat_fraction_per_roll'],
                                   (1 - s['strip_heat_share']) / 2)
        self.assertEqual(len(ts['rows']), 3)
        self.assertIn('"full"', ts['spray_rows_note'])
        self.assertLess(ts['linearity_check_max_relative_difference'], bt.LINEARITY_TOLERANCE)
        # linear scaling of the stripe with the roll share at a fixed spray coefficient
        r0, r1 = ts['rows'][0], ts['rows'][2]
        self.assertAlmostEqual(r1['stripe_peak_m'] / r0['stripe_peak_m'], 0.445 / 0.08)
        self.assertAlmostEqual(r1['in_mill_onset_height_m'], r0['in_mill_onset_height_m'])
        # the case row reuses the steady stripe table's onsets
        st = self.r['width']['shape']['steady_stripe_table']
        big = max(st, key=lambda x: abs(x['peak_radius_deviation_m']))
        self.assertAlmostEqual(r0['in_mill_onset_height_m'], big['manifest_onset_peak_height_m'])
        self.assertEqual(r0['state_in_mill'],
                         big['with_feedback']['state'])
        lit = {f['item']: f['verdict'] for f in ts['literature_check_of_case_inputs']}
        self.assertEqual(lit['strip_heat_fraction'], 'ABOVE_PUBLISHED_RANGE')
        json.dumps(ts, allow_nan=False)

    def test_full_spray_rows_and_events(self):
        ts = self.full['width']['thermal_sensitivity']
        htcs = [h['spray_htc_w_m2k'] for h in ts['spray_coefficients']]
        self.assertEqual(htcs[0], self.case['width_model']['spray_header']['spray_mean_htc_w_m2k'])
        self.assertTrue({2500.0, 4300.0, 13000.0, 2000.0} <= set(htcs))
        self.assertEqual(len(ts['rows']), 3 * len(htcs))
        by = {(x['strip_heat_share'], x['spray_htc_w_m2k']): x for x in ts['rows']}
        # more cooling, smaller stripe; more roll heat, larger stripe
        self.assertGreater(by[(0.84, 2500.0)]['stripe_peak_m'], by[(0.84, 4300.0)]['stripe_peak_m'])
        self.assertGreater(by[(0.11, 2500.0)]['stripe_peak_m'], by[(0.84, 2500.0)]['stripe_peak_m'])
        for x in ts['rows']:
            self.assertIsNotNone(x['events'])
            for e in x['events']:
                self.assertIn(e['in_mill'], ('MANIFEST_IN_MILL', 'LATENT_UNDER_TENSION', None))
        base = by[(0.84, htcs[0])]
        listed = {(c['strip_heat_share'], c['spray_htc_w_m2k']) for c in
                  ts['combinations_changing_a_state']}
        for k, x in by.items():
            if x is base:
                continue
            moved = (x['state_in_mill'] != base['state_in_mill']
                     or x['state_after_tension_release'] != base['state_after_tension_release']
                     or any(a['in_mill'] != b['in_mill'] or a['after_release'] != b['after_release']
                            for a, b in zip(base['events'], x['events'])))
            self.assertEqual(moved, k in listed, k)

    def test_scores_unchanged_and_report(self):
        off = copy.deepcopy(self.case)
        off['model_options']['thermal_sensitivity'] = 'off'
        r = diagnose(off)
        self.assertTrue(r['width']['thermal_sensitivity']['not_supplied'])
        self.assertEqual([(h['id'], h['score']) for h in r['hypotheses']],
                         [(h['id'], h['score']) for h in self.r['hypotheses']])
        render_band_report(self.full)

    def test_option_validation_and_time_above(self):
        bad = copy.deepcopy(self.case)
        bad['model_options']['thermal_sensitivity'] = 'yes'
        with self.assertRaisesRegex(ValueError, 'thermal_sensitivity'):
            validate_case(bad)
        self.assertNotIn('thermal_sensitivity', validate_case(self.case)['model_options'])
        self.assertAlmostEqual(bt._time_above([0, 1, 2, 3], [0, 2, 2, 0], 1), 2.0)
        self.assertEqual(bt._time_above([0, 1], [0, 0.5], 1), 0.0)
        self.assertAlmostEqual(bt.share_to_fraction(0.22), 0.39)
        self.assertAlmostEqual(bt.fraction_to_share(0.08), 0.84)


if __name__ == '__main__':
    unittest.main()
