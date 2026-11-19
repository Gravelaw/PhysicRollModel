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
                self.assertIn(e['in_mill'], ('MANIFEST_BUCKLE', 'LATENT_UNDER_TENSION',
                                              'BELOW_REPORTING_THRESHOLD', None))
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


def _events_case(**wm):
    c = v2case(width=True)
    c['width_model'].update(wm)
    return c


class ReviewFindingTests(unittest.TestCase):
    """Review of 37fee15: signed events, event-only cases, zero roll-heat fraction, signed
    steady stripes."""

    def _case_row_matches_section(self, r):
        ts = r['width']['thermal_sensitivity']
        base = ts['rows'][0]
        self.assertEqual(base['strip_heat_share'], ts['case_strip_heat_share'])
        for e, row in zip(r['width']['thermal_events']['events'], base['events']):
            for k in ('peak_deviation_m', 'manifest_threshold_m', 'released_threshold_m',
                      'visible_time_s', 'visible_time_basis', 'band_life_s',
                      'time_above_manifest_threshold_s', 'time_above_released_threshold_s'):
                self.assertEqual(row[k], e[k], k)
            self.assertEqual(row['in_mill'], e['peak_state_with_feedback'])
            self.assertEqual(row['after_release'], e['peak_state_after_tension_release'])
        return ts

    def test_heating_and_cooling_events_reproduce_the_event_section(self):
        # closure (heating) as in v2case; restore of the blocked nozzle 12 (cooling)
        heat = diagnose(_events_case())
        ts = self._case_row_matches_section(heat)
        self.assertEqual(ts['rows'][0]['events'][0]['sign'], 'HEATING')
        cool = diagnose(_events_case(events=[{'start_s': 0.0, 'duration_s': 20.0,
                                              'nozzle_indices': [12], 'level': 1.0}]))
        ts = self._case_row_matches_section(cool)
        e = ts['rows'][0]['events'][0]
        self.assertEqual(e['sign'], 'COOLING')
        self.assertLess(e['peak_deviation_m'], 0)
        # reviewer: -0.717 um against -23.2 um must stay latent, never manifest for 620 s
        self.assertEqual(e['in_mill'], 'LATENT_UNDER_TENSION')
        self.assertNotEqual(e['visible_time_basis'], 'in_mill_manifest')
        for row in ts['rows']:
            for ev in row['events']:
                # the over-cooled stripe is tight: at its own position there is no in-mill
                # manifest threshold (the loose lanes beside it are neighbour_bands), so the
                # ratio is absent; where a threshold exists the peak stays below it
                ratio = ev['ratio_peak_to_in_mill_threshold']
                self.assertTrue(ratio is None or ratio < 1, ratio)
                self.assertEqual(ev['in_mill'], 'LATENT_UNDER_TENSION')

    def test_event_only_case_evaluates_events(self):
        r = diagnose(_events_case(blocked_nozzle_indices=[]))
        ts = self._case_row_matches_section(r)
        self.assertTrue(all(x['status'] == 'NO_STEADY_STRIPE_ABOVE_THRESHOLD'
                            for x in ts['rows']))
        low = next(x for x in ts['rows'] if x['strip_heat_share'] == 0.11)
        self.assertEqual(low['events'][0]['in_mill'], 'MANIFEST_BUCKLE')
        ch = [c for c in ts['combinations_changing_a_state'] if c['strip_heat_share'] == 0.11]
        self.assertEqual(len(ch), 1)
        self.assertTrue(all(w.startswith('event ') for w in ch[0]['changes']))

    def test_zero_roll_heat_fraction_fails_soft(self):
        r = diagnose(_events_case(roll_heat_fraction_per_roll=0.0))
        ts = r['width']['thermal_sensitivity']
        self.assertEqual(ts['status'], 'NOT_ASSESSABLE')
        self.assertIn('nothing to scale', ts['reason'])
        render_band_report(r)

    def test_arithmetic_error_inside_the_block_fails_soft(self):
        from unittest import mock

        def boom(*a, **k):
            raise ZeroDivisionError('planted')
        with mock.patch.object(bt, 'thermal_sensitivity', boom):
            r = diagnose(_events_case())
        self.assertEqual(r['width']['thermal_sensitivity']['status'], 'FAILED')
        self.assertIn('THERMAL_SENSITIVITY_FAILED', r['flags'])

    def test_negative_steady_stripe(self):
        # the model's actual-minus-healthy stripes are hot (levels <= 1); a cold (over-cooled)
        # stripe is planted by negating the steady deviation of a real case
        from physicroll import band_width as bw
        from tests.test_band_diagnosis import _bite
        c = validate_case(_events_case(events=[]))
        w = c['width_model']
        th = bw._Thermal(c, w, 4e5, 0.08)
        sp, _ = bw.shape_params_or_none(c, _bite(c), w)
        steady, _, actual, _ = bw._steady_section(th, sp)
        neg = dict(steady, local_deviation_m=[-v for v in steady['local_deviation_m']])
        z = neg['z_m']
        idx = bw._inside(z, th.centre, th.width)
        neg['stripes'] = bw._runs([z[i] for i in idx], [neg['local_deviation_m'][i]
                                                        for i in idx], bw.STRIPE_THRESHOLD_M)
        ts = bt.thermal_sensitivity(c, w, th, sp, neg, actual, None, bw)
        pos = bt.thermal_sensitivity(c, w, th, sp, steady, actual, None, bw)
        r0, p0 = ts['rows'][0], pos['rows'][0]
        self.assertEqual(r0['stripe_sign'], 'COLD_LOW')
        self.assertEqual(p0['stripe_sign'], 'HOT_HIGH')
        self.assertGreater(r0['stripe_peak_m'], 0)            # a magnitude
        self.assertAlmostEqual(r0['stripe_peak_m'], p0['stripe_peak_m'])
        for x in ts['rows']:
            # review of 631195a: the onset is that of the band AT the stripe (the tight lane of
            # an over-cooled stripe never buckles; the loose lanes beside it do not count)
            self.assertIsNotNone(x['state_in_mill'])
            if x['state_in_mill'] == 'MANIFEST_BUCKLE':
                self.assertGreaterEqual(x['ratio_stripe_to_in_mill_onset'], 0.97)
            elif x['ratio_stripe_to_in_mill_onset'] is not None:
                self.assertLess(x['ratio_stripe_to_in_mill_onset'], 1.03)
        lv = bw.shape_levels(z, neg['local_deviation_m'], sp)
        st = bw.stripe_states(lv, r0['stripe_position_m'])['with_feedback']
        self.assertEqual(r0['state_in_mill'], st['state'])


if __name__ == '__main__':
    unittest.main()
