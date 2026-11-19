"""Published benchmark cases beside the project's numbers (``physicroll.benchmarks``).

Two kinds of assertion, never merged: SOFTWARE pins (the project value equals the literal
recorded in ``benchmarks.py`` to 1e-6 relative; when one fails, re-record deliberately, do not
loosen the tolerance) and the VERDICT literal against the published reference. A passing
``recorded_discrepancy`` test documents a gap; it is not a validation of the physics.
"""
import contextlib
import io
import json
import math
import unittest

from physicroll import benchmarks as bm

REL = 1e-6


def _q(case, name, reference=None):
    for q in case['quantities']:
        if q['name'] == name and (reference is None or q['reference_value'] == reference):
            return q
    raise AssertionError(f'{case["id"]}: no quantity {name} / {reference}')


class BenchmarkTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = bm.run_all()
        cls.cases = {c['id']: c for c in cls.result['cases']}

    def assertRel(self, value, expected, rel=REL):
        self.assertLessEqual(abs(value - expected), rel * abs(expected),
                             f'{value!r} != {expected!r} (rel {rel})')

    def test_bt_v1_software_pin(self):
        case = self.cases['BT-V1']
        self.assertRel(_q(case, 'w_bar', 118.0)['project_value'], 49.772441)
        self.assertRel(_q(case, 'force_per_width_n_m')['project_value'], 1018841.8703)
        self.assertRel(_q(case, 'forward_slip_fraction')['project_value'], 0.169779, 1e-5)
        self.assertIn('MATTRESS_REGIME_FOIL', case['flags'])

    def test_bt_v1_recorded_discrepancy_mattress_is_0_42_of_half_space_load(self):
        """Passing this test does not mean the physics is right. It records that the model is
        0.42 of the reference (half-space load W_bar 118 of BT-S1, Fig. 9)."""
        case = self.cases['BT-V1']
        ratio = _q(case, 'w_bar', 118.0)['ratio_project_to_reference']
        self.assertTrue(0.415 <= ratio <= 0.428, ratio)
        self.assertEqual(case['verdict'], 'RECORDED_DISCREPANCY')
        self.assertTrue(0.79 <= _q(case, 'w_bar', 62.0)['ratio_project_to_reference'] <= 0.81)
        self.assertFalse(0.9 <= ratio <= 1.1)
        self.assertEqual(case['reference_kind'], 'MODEL_OUTPUT')

    def test_bt_v1_grid_independent(self):
        base = _q(self.cases['BT-V1'], 'w_bar', 118.0)['project_value']
        for cells in (200, 800):
            other = _q(bm._bt_v1(cells=cells), 'w_bar', 118.0)['project_value']
            self.assertRel(other, base)

    def test_bt_v2_assumed_radius(self):
        for case_id, pin in (('BT-V2-R89', 41.068824), ('BT-V2-R135', 51.052946)):
            case = self.cases[case_id]
            q = _q(case, 'w_bar', 58.0)
            self.assertRel(q['project_value'], pin)
            self.assertEqual(case['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
            self.assertEqual(case['reference_kind'], 'MEASUREMENT')
            self.assertTrue(any('radius' in n.lower() and 'ASSUMED' in n
                                for n in case['input_notes']), case['input_notes'])
        self.assertAlmostEqual(_q(self.cases['BT-V2-R89'], 'w_bar')['ratio_project_to_reference'],
                               0.7081, places=4)
        self.assertAlmostEqual(
            _q(self.cases['BT-V2-R135'], 'w_bar')['ratio_project_to_reference'], 0.8802, places=4)

    def test_bt_v3_fig1_and_eq29(self):
        fig1 = self.cases['BT-V3-FIG1-140UM']
        q = _q(fig1, 'w_bar', 50.0)
        self.assertRel(q['project_value'], 45.968340)
        self.assertAlmostEqual(q['ratio_project_to_reference'], 0.919, places=3)
        self.assertEqual(fig1['verdict'], 'REFERENCE_READ_BY_EYE')
        self.assertEqual(fig1['reference_kind'], 'FIGURE_READ_BY_EYE')
        self.assertIn('MATTRESS_REGIME_CONVENTIONAL', fig1['flags'])
        f = bm.fleck_regime_boundary_entry_gauge_m
        er_demo = 210e9 / 0.91
        for args, expected_um in (((0.089, 0.25, 0.03, 230e6, 230e9), 36.24),
                                  ((0.089, 0.5, 0.03, 230e6, 230e9), 51.25),
                                  ((0.135, 0.4, 0.03, 175e6, er_demo), 56.35),
                                  ((0.135, 0.4, 0.03, 175e6 * 2 / math.sqrt(3), er_demo), 62.86)):
            self.assertAlmostEqual(f(*args) * 1e6, expected_um, delta=0.01)
        eq29 = self.cases['BT-V3-EQ29']
        self.assertEqual(eq29['verdict'], 'CONSISTENT_REGIME')
        self.assertIn('PROJECT_REGIME_FOIL_AT_20_UM_ENTRY', eq29['flags'])
        self.assertIn('PROJECT_REGIME_CONVENTIONAL_AT_140_UM_ENTRY', eq29['flags'])
        self.assertIn('54-63 um', eq29['note'])
        self.assertRel(bm.fleck_dimensionless_load(1018841.8703, 0.089, 230e6, 230e9),
                       49.772441)

    def test_ss_v2_ss_v3(self):
        ss2 = self.cases['SS-V2']
        self.assertRel(_q(ss2, 'critical_stress_pa')['project_value'], 8435559.32)
        q = _q(ss2, 'critical_i_units', 5.3)
        self.assertRel(q['project_value'], 4.016933)
        self.assertAlmostEqual(q['ratio_project_to_reference'], 0.7579, places=4)
        self.assertAlmostEqual(_q(ss2, 'half_wave_m')['ratio_project_to_reference'], 2.5,
                               places=12)
        self.assertEqual(ss2['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
        ss3 = self.cases['SS-V3']
        self.assertAlmostEqual(_q(ss3, 'half_wave_m')['ratio_project_to_reference'], 2.8,
                               places=12)
        self.assertEqual(ss3['verdict'], 'RECORDED_DISCREPANCY')

    def test_tm_lc7_is_reference_only(self):
        """Replace this test when the TM-LC7 mill parameters are recorded from the paper's
        tables: the case will then carry inputs, project values and a verdict by the rule."""
        case = self.cases['TM-LC7']
        self.assertEqual(case['verdict'], 'REFERENCE_ONLY_INPUTS_NOT_RECORDED')
        self.assertEqual(case['inputs'], {})
        refs = {(q['name'], q['reference_value']) for q in case['quantities']}
        self.assertIn(('critical_exit_speed_m_s', 5.81), refs)
        self.assertIn(('onset_frequency_hz', 124.6), refs)
        for q in case['quantities']:
            self.assertIsNone(q['project_value'])
            self.assertIsNone(q['ratio_project_to_reference'])

    def test_chatter_harness_reproduces_the_demo(self):
        """Software check of the harness on the project's own synthetic demo (not a
        benchmark): the values of the committed thin-gauge chatter artifact."""
        from pathlib import Path
        case = json.loads((Path(__file__).resolve().parents[1] / 'scenarios' /
                           'band_diagnosis_thin_gauge_chatter.json').read_text())
        obs = case['observation']
        measured_hz = 16.0 / 0.08408       # demo pitch at 16 m/s (model-generated)
        r = bm.chatter_onset_comparison(
            case['stand'], case['spans'], case['pass'],
            measured_critical_speed_m_s=obs['onset_above_exit_speed_m_s'],
            measured_frequency_hz=measured_hz, bite_damping_transit_fraction=0.5,
            roll_youngs_modulus_pa=case['stand']['roll_youngs_modulus_pa'],
            roll_poisson_ratio=case['stand']['roll_poisson_ratio'],
            cells=case['model_options']['cells'])
        w, z = r['with_bite_damping'], r['without_bite_damping']
        self.assertRel(w['critical_exit_speed_m_s'], 13.267836)
        self.assertRel(w['onset_frequency_hz'], 189.109442)
        self.assertRel(z['critical_exit_speed_m_s'], 4.829571)
        self.assertRel(z['onset_frequency_hz'], 188.911169)
        self.assertEqual(z['bite_damping_transit_fraction'], 0.0)
        self.assertAlmostEqual(w['speed_ratio_to_measured'],
                               w['critical_exit_speed_m_s'] / 13.3)
        self.assertAlmostEqual(z['frequency_ratio_to_measured'],
                               z['onset_frequency_hz'] / measured_hz)
        self.assertEqual(r['status'], bm.STATUS)
        json.dumps(r, allow_nan=False)
        with self.assertRaises(ValueError):
            bm.chatter_onset_comparison(case['stand'], case['spans'], case['pass'],
                                        measured_critical_speed_m_s=-1.0,
                                        measured_frequency_hz=100.0)

    def test_run_all_is_json_safe_and_complete(self):
        json.dumps(self.result, allow_nan=False)
        self.assertEqual(self.result['status'],
                         'SOFTWARE_COMPARISON_WITH_PUBLISHED_VALUES_NOT_PHYSICAL_VALIDATION')
        self.assertEqual(tuple(c['id'] for c in self.result['cases']), bm.CASE_IDS)
        keys = {'id', 'title', 'source', 'source_id', 'read_status', 'reference_kind',
                'inputs', 'input_notes', 'quantities', 'verdict', 'agreement_band', 'note',
                'flags'}
        for case in self.result['cases']:
            self.assertEqual(set(case), keys)
            self.assertTrue(case['read_status'])
            self.assertIn(case['verdict'], bm.VERDICTS)
            self.assertIn(case['reference_kind'], bm.REFERENCE_KINDS)
            self.assertEqual(case['agreement_band'], [0.9, 1.1])
            for q in case['quantities']:
                if q['project_value'] is not None:   # every software pin, 1e-6 relative
                    self.assertRel(q['project_value'], q['recorded_project_value'])
                    self.assertEqual(q['recorded_on'], bm.RECORDED_ON)
        ids = {e['id'] for e in self.result['not_encoded']}
        self.assertTrue({'BT-V4', 'BT-V9', 'SS-V1', 'SS-V4', 'SS-V5', 'SS-V11'} <= ids)
        self.assertFalse(ids & {'BT-V1', 'BT-V2', 'BT-V3', 'SS-V2', 'SS-V3'})
        rows = bm.table_rows(self.result)
        self.assertEqual(len(rows), sum(len(c['quantities']) for c in self.result['cases']))
        for case in self.result['cases']:   # row verdict: no reference -> NO_REFERENCE_VALUE
            for q in case['quantities']:
                self.assertEqual(q['row_verdict'], bm.NO_REFERENCE_VALUE
                                 if q['reference_value'] is None else case['verdict'])
        for r in rows:
            self.assertEqual(r['verdict'] == bm.NO_REFERENCE_VALUE, r['reference'] is None)
        slip = [r for r in rows if r['id'] == 'BT-V1' and r['quantity'] == 'forward_slip_fraction']
        self.assertEqual([(r['verdict'], r['case_verdict']) for r in slip],
                         [('NO_REFERENCE_VALUE', 'RECORDED_DISCREPANCY')])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(bm.main(['--json']), 0)
        self.assertEqual(json.loads(buf.getvalue())['status'], bm.STATUS)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            bm.main([])
        self.assertIn('RECORDED_DISCREPANCY', buf.getvalue())

    def test_unknown_case_rejected(self):
        with self.assertRaises(ValueError):
            bm.run_case('BT-V99')
        with self.assertRaises(ValueError):
            bm.fleck_regime_boundary_entry_gauge_m(0.089, 1.5, 0.03, 230e6, 230e9)


if __name__ == '__main__':
    unittest.main()
