"""Review of 7c494fd (band_thermal): a sensitivity row must report what a direct diagnosis at
that heat share reports (stripe detected per row), and rejected pass-heating rows must not
crash the thermal post-processing. Review of 6ad7e48: per-pass onsets belong to the stripe
they are compared with (never the Gaussian reference stripe's), and the case-pass rows of the
per-pass table agree with the sensitivity rows."""
import copy
import json
import pathlib
import unittest

from physicroll import band_thermal as bt
from physicroll.band_diagnosis import diagnose
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import LONG, TRIBOLOGY, v2, width_model
from tests.test_band_robustness import v2case


def _case(frac, heat=5000.0, mode='partition'):
    c = v2case(width=True)
    c['width_model'].update(bite_heat_per_width_w_m=heat, roll_heat_fraction_per_roll=frac,
                            events=[])
    c['model_options']['thermal_sensitivity'] = mode
    return c


def _rows(r):
    ts = r['width']['thermal_sensitivity']
    return {round(x['strip_heat_share'], 9): x for x in ts['rows']
            if x['spray_htc_w_m2k'] == ts['case_spray_htc_w_m2k']}


def _direct(frac, heat=5000.0):
    t = diagnose(_case(frac, heat))['width']['shape'].get('steady_stripe_table') or []
    return max(t, key=lambda x: abs(x['peak_radius_deviation_m'])) if t else None


class PerRowDetectionTests(unittest.TestCase):
    def test_reviewer_case_stripe_appears_at_larger_roll_share(self):
        for mode in ('partition', 'full'):
            r = diagnose(_case(0.08, mode=mode))
            rows = _rows(r)
            self.assertEqual(rows[0.84]['status'], 'NO_STEADY_STRIPE_ABOVE_THRESHOLD')
            row = rows[0.11]
            self.assertEqual(row['status'], 'EVALUATED', mode)
            d = _direct(0.445)
            self.assertAlmostEqual(row['stripe_peak_m'], abs(d['peak_radius_deviation_m']),
                                   delta=1e-6 * abs(d['peak_radius_deviation_m']))
            self.assertEqual(row['state_in_mill'], d['with_feedback']['state'])
            self.assertEqual(row['state_after_tension_release'],
                             d['with_feedback']['state_after_tension_release'])
            tol = 1e-9 if mode == 'full' else 0.02      # partition: one onset window
            self.assertAlmostEqual(row['in_mill_onset_height_m'] / d['manifest_onset_peak_height_m'],
                                   1.0, delta=tol)
            ch = {round(c['strip_heat_share'], 9): c['changes'] for c in
                  r['width']['thermal_sensitivity']['combinations_changing_a_state']
                  if c['spray_htc_w_m2k'] == r['width']['thermal_sensitivity']['case_spray_htc_w_m2k']}
            self.assertIn('steady stripe appears above the detection threshold', ch[0.11])
        render_band_report(r)

    def test_reverse_case_stripe_falls_below_threshold(self):
        r = diagnose(_case(0.445))
        rows = _rows(r)
        self.assertEqual(rows[0.11]['status'], 'EVALUATED')            # the case share
        self.assertIsNone(_direct(0.08))                                # direct run at 0.84
        self.assertEqual(rows[0.84]['status'], 'NO_STEADY_STRIPE_ABOVE_THRESHOLD')
        self.assertIsNone(rows[0.84]['state_in_mill'])
        self.assertLess(rows[0.84]['largest_deviation_in_strip_m'], bt.STRIPE_THRESHOLD_M)
        changes = [c['changes'] for c in
                   r['width']['thermal_sensitivity']['combinations_changing_a_state']
                   if round(c['strip_heat_share'], 9) == 0.84]
        self.assertIn('steady stripe falls below the detection threshold', changes[0])

    def test_no_stripe_at_any_share(self):
        r = diagnose(_case(0.08, heat=500.0, mode='full'))
        ts = r['width']['thermal_sensitivity']
        self.assertTrue(all(x['status'] == 'NO_STEADY_STRIPE_ABOVE_THRESHOLD' for x in ts['rows']))
        self.assertEqual(ts['combinations_changing_a_state'], [])
        self.assertEqual(ts['steady_build_up']['status'], 'NOT_ASSESSABLE')
        render_band_report(r)


ROOT = pathlib.Path(__file__).resolve().parents[1]
# the partition-mode / own-window onset difference documented for the sensitivity rows
WINDOW_TOL = 0.02


def assert_case_pass_agrees(test, ts, case_exit_m, tol=WINDOW_TOL):
    """The case-pass rows of the per-pass table against the sensitivity rows at the same share
    (case spray coefficient): same stripe, same state in the mill and after release, ratios
    within the onset-window tolerance. Returns the number of rows compared."""
    rows = {round(x['strip_heat_share'], 9): x for x in ts['rows']
            if x['spray_htc_w_m2k'] == ts['case_spray_htc_w_m2k']}
    n = 0
    for p in ts['per_pass']:
        if p['exit_thickness_m'] is None or abs(p['exit_thickness_m'] - case_exit_m) > 1e-12:
            continue
        s = rows[round(p['strip_heat_share'], 9)]
        n += 1
        if s['status'] != 'EVALUATED':
            test.assertIsNone(p['stripe_peak_m'])
            continue
        test.assertAlmostEqual(p['stripe_peak_m'] / s['stripe_peak_m'], 1.0, delta=1e-6)
        for state, ratio in (('state_in_mill', 'ratio_stripe_to_in_mill_onset'),
                             ('state_after_tension_release',
                              'ratio_stripe_to_after_release_onset')):
            manifest = s[state].startswith('MANIFEST')
            rp = p[ratio]
            test.assertIsNotNone(rp, (p['label'], p['strip_heat_share'], ratio))
            if manifest:
                test.assertGreaterEqual(rp, 1.0 - tol, (p['strip_heat_share'], ratio))
            else:
                test.assertLess(rp, 1.0 + tol, (p['strip_heat_share'], ratio))
            test.assertAlmostEqual(rp / s[ratio], 1.0, delta=tol)
    return n


def _gauss_case(mode='partition', heat=1800.0):
    # reviewer: tribology on, bite heat 1800 W/m, roll heat fraction 0.08 (strip share 0.84):
    # no steady stripe at the case share, so the gauge trend uses its Gaussian reference
    c = _case(0.08, heat=heat, mode=mode)
    c['tribology'] = dict(TRIBOLOGY)
    return c


class PerPassOnsetShapeTests(unittest.TestCase):
    def test_reviewer_case_onsets_belong_to_the_thermal_stripe(self):
        for mode in ('partition', 'full'):
            r = diagnose(_gauss_case(mode))
            gt, ts = r['width']['gauge_trend'], r['width']['thermal_sensitivity']
            self.assertEqual(gt['reference_stripe_kind'], 'gaussian_reference')
            self.assertEqual(gt['thermal_shape_onsets']['window_strip_heat_share'], 0.33)
            g = gt['rows'][0]
            row = _rows(r)[0.11]
            self.assertEqual(row['state_after_tension_release'], 'MANIFEST_AFTER_TENSION_RELEASE')
            p = next(x for x in ts['per_pass'] if round(x['strip_heat_share'], 9) == 0.11)
            self.assertIn('thermal stripe shape', p['onset_shape_basis'])
            # never the Gaussian reference stripe's onset (before: 0.152 um, ratio 0.922)
            self.assertNotEqual(p['after_release_onset_height_m'],
                                g['released_onset_stripe_height_m'])
            self.assertEqual(p['after_release_onset_height_m'],
                             g['thermal_shape_released_onset_height_m'])
            self.assertGreaterEqual(p['ratio_stripe_to_after_release_onset'], 1.0)
            if mode == 'partition':      # same window as the sensitivity row: same onset
                self.assertAlmostEqual(p['ratio_stripe_to_after_release_onset']
                                       / row['ratio_stripe_to_after_release_onset'], 1.0,
                                       delta=1e-9)
            self.assertEqual(assert_case_pass_agrees(self, ts, 0.42e-3), len(ts['shares']))
            self.assertIn('Gaussian reference stripe', ts['per_pass_text'])
            self.assertIn('not of the Gaussian reference stripe', ts['per_pass_text'])
            self.assertNotIn('holds the case-pass stripe', ts['per_pass_text'])
            html = render_band_report(r)
            self.assertIn('The per-pass onsets are those of the thermal stripe shape', html)

    def test_no_thermal_stripe_shape_gives_no_onset(self):
        r = diagnose(_gauss_case(heat=300.0))
        gt, ts = r['width']['gauge_trend'], r['width']['thermal_sensitivity']
        self.assertEqual(gt['reference_stripe_kind'], 'gaussian_reference')
        self.assertNotIn('thermal_shape_onsets', gt)
        for p in ts['per_pass']:
            self.assertIsNone(p['in_mill_onset_height_m'])
            self.assertIsNone(p['after_release_onset_height_m'])
            self.assertIsNone(p['onset_shape_basis'])
        self.assertIn('Gaussian reference stripe', ts['per_pass_onsets_not_given_reason'])
        self.assertIn('No ratio is given', ts['per_pass_text'])
        # a pass that would carry a stripe (synthetic: a larger unthresholded deviation) gets
        # no ratio, and the reason, never a ratio against the Gaussian's onset
        r2 = copy.deepcopy(r)
        ts2 = r2['width']['thermal_sensitivity']
        for x in ts2['rows']:
            x['largest_deviation_in_strip_m'] = 1e-6
        bt.attach_per_pass(r2)
        p = ts2['per_pass'][0]
        self.assertIsNotNone(p['stripe_peak_m'])
        self.assertIsNone(p['ratio_stripe_to_in_mill_onset'])
        self.assertIsNone(p['ratio_stripe_to_after_release_onset'])
        self.assertIn('Gaussian reference stripe', p['not_assessable_reason'])
        self.assertIn('not assessable on case', ts2['per_pass_text'])
        self.assertIn('No per-pass onset or ratio', render_band_report(r2))

    def test_battery_demo_case_pass_agrees_with_sensitivity_rows(self):
        r = json.loads((ROOT / 'artifacts' / 'band_diagnosis'
                        / 'battery-foil-demo.result.json').read_text(encoding='utf-8'))
        ts = r['width']['thermal_sensitivity']
        self.assertEqual(r['width']['gauge_trend']['reference_stripe_kind'],
                         'model_steady_stripe')
        self.assertEqual(assert_case_pass_agrees(self, ts, r['inputs']['pass']['exit_thickness_m']),
                         len(ts['shares']))
        self.assertTrue(all('case-share steady stripe' in p['onset_shape_basis']
                            for p in ts['per_pass']))


class RejectedPassHeatingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # reviewer: supplied-bite v2 case with tribology, a schedule pass 0.12 -> 0.084 mm at
        # 285 MPa and friction 0.03 that Hitchcock rejects at max_radius_ratio 2
        c = v2(**LONG)
        c['tribology'] = dict(TRIBOLOGY)
        c['width_model'] = width_model(roll_heat_fraction_per_roll=None)
        c['model_options']['max_radius_ratio'] = 2.0
        c['schedule'] = [{'label': 'R1 0.12->0.084 mm', 'entry_thickness_m': 0.12e-3,
                          'exit_thickness_m': 0.084e-3, 'mean_flow_stress_pa': 285e6,
                          'friction_coefficient': 0.03, 'entry_tension_pa': 25e6,
                          'exit_tension_pa': 30e6, 'exit_speed_m_s': 10.0}]
        cls.r = diagnose(c)

    def test_thermal_check_keeps_the_other_passes(self):
        tc = self.r['thermal_check']
        self.assertNotEqual(tc.get('status'), 'FAILED')
        t = {f['label']: f for f in tc['strip_exit_temperatures']}
        self.assertEqual(t['R1 0.12->0.084 mm']['verdict'], 'NOT_ASSESSABLE')
        self.assertIsNone(t['R1 0.12->0.084 mm']['value'])
        self.assertIn('max_radius_ratio', t['R1 0.12->0.084 mm']['reason'])
        self.assertIsNotNone(t['case pass']['value'])
        self.assertNotIn('THERMAL_CHECK_FAILED', self.r['flags'])
        html = render_band_report(self.r)
        self.assertIn('not assessable', html)

    def test_per_pass_marks_the_rejected_pass(self):
        ts = self.r['width']['thermal_sensitivity']
        self.assertIsNotNone(ts['per_pass'])
        for p in ts['per_pass']:
            self.assertIsNone(p['strip_exit_temperature_c'])
            self.assertIsNone(p['stripe_peak_m'])
            self.assertIn('max_radius_ratio', p['not_assessable_reason'])
        self.assertIn('not assessable on R1', ts['per_pass_text'])
        self.assertNotIn('latent on R1', ts['per_pass_text'])
        self.assertNotIn('THERMAL_SENSITIVITY_PER_PASS_FAILED', self.r['flags'])

    def test_rejected_operating_row(self):
        # synthetic: the operating pass-heating row itself rejected
        rej = {'label': 'case pass', 'exit_thickness_m': 3e-5, 'exit_speed_m_s': 10.0,
               'rejected': 'planted'}
        res = {'process': {'heating': {'operating': rej, 'schedule': []}}}
        case = {'case_schema': 'physicroll.band_case.v2', 'width_model': None,
                'tribology': {'strip_heat_fraction': 0.22, 'inlet_temperature_k': 318.15,
                              'lubricant': {}},
                'material': {'product': 'battery_collector_foil'},
                'pass': {'exit_thickness_m': 3e-5},
                'observation': {'band_positions_across_width_m': []}}
        tc = bt.thermal_check(res, case)
        self.assertEqual(tc['strip_exit_temperatures'][0]['verdict'], 'NOT_ASSESSABLE')
        self.assertEqual(tc['flags'], [])
        r = copy.deepcopy(self.r)
        r['process']['heating']['operating'] = dict(rej)
        bt.attach_per_pass(r)
        pp = r['width']['thermal_sensitivity']['per_pass']
        self.assertTrue(all(p['stripe_peak_m'] is None for p in pp))


if __name__ == '__main__':
    unittest.main()
