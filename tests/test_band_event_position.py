"""Review of 631195a (band_width): onsets that pair with a per-position state are those of
the band AT that position (the rule of ``stripe_states``), not of any band of the profile.

An over-cooled stripe (a restored nozzle) is tight at its own position; the loose bands sit in
the compensating lanes beside it. Its thresholds, times, visible time and the duration evidence
must describe the stripe; the lanes are reported separately (``neighbour_bands``)."""
import copy
import json
import math
import pathlib
import unittest
from unittest import mock

from physicroll import band_thermal as bt
from physicroll import band_width as bw
from physicroll.band_diagnosis import diagnose, validate_case
from physicroll.band_report import render_band_report
from tests.test_band_diagnosis import _bite
from tests.test_band_robustness import v2case

ROOT = pathlib.Path(__file__).resolve().parents[1]
# states on the fine grid, onsets on the >= 10 mm grid: the documented grid tolerance
GRID_TOL = 0.03


def _manifest(state):
    return state is not None and state.startswith('MANIFEST')


def assert_event_consistent(test, e, tol=GRID_TOL):
    """The thresholds, threshold times and visible-time basis of an event agree with its peak
    states: a state is manifest exactly when the stripe peak reaches that threshold."""
    pk = abs(e['peak_deviation_m'])
    for state, thr in ((e['peak_state_with_feedback'], e['manifest_threshold_m']),
                       (e['peak_state_after_tension_release'], e['released_threshold_m'])):
        if _manifest(state):
            test.assertIsNotNone(thr, (e['label'], state))
            test.assertLessEqual(abs(thr), pk * (1 + tol), (e['label'], state))
        elif thr is not None:
            test.assertGreaterEqual(abs(thr), pk * (1 - tol), (e['label'], state))
    basis = e['visible_time_basis']
    if basis == 'in_mill_manifest':
        test.assertTrue(_manifest(e['peak_state_with_feedback']))
    elif basis == 'manifest_after_tension_release':
        test.assertTrue(_manifest(e['peak_state_after_tension_release']))
        test.assertFalse(_manifest(e['peak_state_with_feedback']))
    else:
        test.assertFalse(_manifest(e['peak_state_after_tension_release']), e['label'])


def _restored_case(**obs):
    # reviewer: bite heat 4e6 W/m, nozzle 12 (partly blocked in the case) restored to level 1
    # for 20 s: an over-cooled stripe
    c = v2case(width=True, **obs)
    c['width_model'].update(bite_heat_per_width_w_m=4e6, events=[
        {'start_s': 0.0, 'duration_s': 20.0, 'nozzle_indices': [12], 'level': 1.0}])
    return c


class RestoredNozzleEventTests(unittest.TestCase):
    def test_reviewer_case_onsets_belong_to_the_stripe(self):
        r = diagnose(_restored_case(intermittent_duration_s=500.0,
                                    lengthwise_continuity='intermittent'))
        e = r['width']['thermal_events']['events'][0]
        self.assertLess(e['peak_deviation_m'], 0)
        self.assertEqual(e['peak_state_after_tension_release'], 'FLAT_AFTER_TENSION_RELEASE')
        # before: released threshold -0.646 um, visible 499 s after tension release
        self.assertIsNone(e['released_threshold_m'])
        self.assertIsNone(e['time_above_released_threshold_s'])
        self.assertNotEqual(e['visible_time_basis'], 'manifest_after_tension_release')
        assert_event_consistent(self, e)
        nb = e['neighbour_bands']['released']
        self.assertAlmostEqual(nb['threshold_m'], -6.46e-7, delta=0.01e-6)
        self.assertAlmostEqual(nb['time_above_threshold_s'], 499, delta=5)
        self.assertTrue(nb['band_offsets_from_event_nozzles_m'])
        self.assertTrue(all(s == 'LOOSE_LONG' for s in nb['band_senses']))
        self.assertIn('loose bands sit beside it', e['neighbour_bands_note'])
        self.assertIn('never used as evidence', e['neighbour_bands_note'])
        self.assertIn('show after tension release', e['neighbour_bands_text'])
        # the 499 s of the neighbour lanes no longer supports a 500 s observed duration
        h = {x['id']: x for x in r['hypotheses']}['cooling_zone_switching_transient']
        dur = [x for x in h['evidence'] if 'duration' in x['criterion']]
        self.assertTrue(dur and all(x['verdict'] != 'SUPPORTS' for x in dur))
        html = render_band_report(r).replace('&#x27;', "'")
        self.assertIn('loose bands sit beside it', html)

    def test_hot_event_unchanged(self):
        # the case's own event: nozzle 18 off for 20 s, a hot stripe
        c = v2case(width=True)
        c['width_model']['bite_heat_per_width_w_m'] = 4e6
        r = diagnose(c)
        e = r['width']['thermal_events']['events'][0]
        self.assertGreater(e['peak_deviation_m'], 0)
        self.assertNotIn('neighbour_bands', e)
        assert_event_consistent(self, e)
        # the same case with the whole-profile onsets (the behaviour before): same numbers
        orig = bw.onsets
        with mock.patch.object(bw, 'onsets', lambda z, s, sp, position=None: orig(z, s, sp)):
            r0 = diagnose(copy.deepcopy(c))
        e0 = r0['width']['thermal_events']['events'][0]
        for k in ('manifest_threshold_m', 'released_threshold_m', 'reporting_threshold_m',
                  'visible_time_s', 'visible_time_basis', 'band_life_s',
                  'time_above_manifest_threshold_s', 'time_above_released_threshold_s'):
            self.assertEqual(e[k], e0[k], k)

    def test_battery_demo_events_consistent(self):
        r = json.loads((ROOT / 'artifacts' / 'band_diagnosis'
                        / 'battery-foil-demo.result.json').read_text(encoding='utf-8'))
        for e in r['width']['thermal_events']['events']:
            self.assertNotIn('neighbour_bands', e)
            assert_event_consistent(self, e)


class PositionOnsetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c = v2case(width=True)
        c['width_model']['events'] = []
        cls.c = validate_case(c)
        w = cls.c['width_model']
        cls.th = bw._Thermal(cls.c, w, 4e5, 0.08)
        cls.sp, _ = bw.shape_params_or_none(cls.c, _bite(cls.c), w)
        cls.steady, _, cls.actual, _ = bw._steady_section(cls.th, cls.sp)
        neg = dict(cls.steady, local_deviation_m=[-v for v in cls.steady['local_deviation_m']])
        z = neg['z_m']
        idx = bw._inside(z, cls.th.centre, cls.th.width)
        neg['stripes'] = bw._runs([z[i] for i in idx], [neg['local_deviation_m'][i]
                                                        for i in idx], bw.STRIPE_THRESHOLD_M)
        cls.neg = neg

    def test_onsets_hot_equal_whole_cold_differ(self):
        z, sp, x = self.steady['z_m'], self.sp, self.th.centre
        g = bw._reference_stripe(z, x)
        whole, pos = bw.onsets(z, g, sp), bw.onsets(z, g, sp, position=x)
        for k in ('mill', 'released', 'reporting'):
            self.assertEqual(pos[k], whole[k], k)
        cold = [-v for v in g]
        whole, pos = bw.onsets(z, cold, sp), bw.onsets(z, cold, sp, position=x)
        self.assertEqual(pos['whole_profile']['released'], whole['released'])
        self.assertNotEqual(pos['released'], whole['released'])
        self.assertIn('neighbour_released', pos)
        for b in pos['neighbour_released']['bands']:
            self.assertFalse(b['start_m'] <= x <= b['end_m'])

    def test_cold_steady_stripe_table_and_sensitivity(self):
        z, sp, neg = self.neg['z_m'], self.sp, self.neg
        lv = bw.shape_levels(z, neg['local_deviation_m'], sp)
        for t in bw.steady_stripe_table(neg, lv, sp):
            fb = t['with_feedback']
            pk = abs(t['peak_radius_deviation_m'])
            for state, on in ((fb['state'], t['manifest_onset_peak_height_m']),
                              (fb['state_after_tension_release'],
                               t['released_onset_peak_height_m'])):
                if _manifest(state):
                    self.assertLessEqual(on, pk * (1 + GRID_TOL))
                elif on is not None:
                    self.assertGreaterEqual(on, pk * (1 - GRID_TOL))
        ts = bt.thermal_sensitivity(self.c, self.c['width_model'], self.th, sp, neg,
                                    self.actual, None, bw)
        for x in ts['rows']:
            self.assertEqual(x['stripe_sign'], 'COLD_LOW')
            for state, ratio in (('state_in_mill', 'ratio_stripe_to_in_mill_onset'),
                                 ('state_after_tension_release',
                                  'ratio_stripe_to_after_release_onset')):
                if _manifest(x[state]):
                    self.assertGreaterEqual(x[ratio], 1 - GRID_TOL)
                elif x[ratio] is not None:
                    self.assertLess(x[ratio], 1 + GRID_TOL)

    def test_cold_steady_stripe_gauge_trend(self):
        c, sp = self.c, self.sp
        gt = bw._gauge_trend(c, c['width_model'], lambda src: _bite(c), self.neg,
                             self.th.centre, c['width_model']['coil'], self.neg['z_m'],
                             _bite(c), None)
        row = gt['rows'][0]
        pk = abs(gt['reference_stripe_peak_m'])
        for state, on in ((row['state'], row['manifest_onset_stripe_height_m']),
                          (row['state_after_tension_release'],
                           row['released_onset_stripe_height_m'])):
            if _manifest(state):
                self.assertLessEqual(on, pk * (1 + GRID_TOL))
            elif on is not None:
                self.assertGreaterEqual(on, pk * (1 - GRID_TOL))
        self.assertTrue(math.isfinite(pk))


if __name__ == '__main__':
    unittest.main()
