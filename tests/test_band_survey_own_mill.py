"""The product survey on the user's own mill (split from tests.test_band_survey to keep both
modules under their time budget)."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from physicroll import band_products as bp
from physicroll import band_survey as bs
from physicroll.band_diagnosis import diagnose, load_case

ROOT = Path(__file__).resolve().parents[1]
FEW = ['battery_pouch_laminate_foil', 'household_foil', 'litho_sheet']


class UserMillSurveyTests(unittest.TestCase):
    """The survey on the user's own mill: --mill / --foil-mill / --sheet-mill, --products,
    --overrides, --write-cases (restricted to a few products to stay fast)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        c = json.loads((ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json').read_text())
        # a different machine: smaller rolls, softer housing, shorter spans; coarse numerics
        c['pass']['work_roll_radius_m'] = 0.11
        c['stand']['housing_stiffness_n_m'] = 9.0e9
        c['spans']['entry_span_length_m'] = c['spans']['exit_span_length_m'] = 2.0
        c['width_model']['numerics'] = {'axial_cell_m': 0.02, 'radial_cells': 6,
                                        'time_step_s': 5.0}
        c['gauge_control'] = c['drive'] = None
        c['model_options']['cells'] = 64
        cls.mill_path = d / 'my-mill.json'
        cls.mill_path.write_text(json.dumps(c))
        cls.base = {x['product_id']: x for x in bs.survey(FEW)['rows']}
        cls.r, cls.mills = bs.survey_with_mills(FEW, cls.mill_path, cls.mill_path)
        cls.rows = {x['product_id']: x for x in cls.r['rows']}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_products_restrict_and_unknown_ids_error(self):
        self.assertEqual(list(self.base), FEW)
        self.assertEqual([x['index'] for x in self.base.values()],
                         [i + 1 for i, p in enumerate(bp.products()) if p.id in FEW])
        with self.assertRaisesRegex(ValueError, 'unknown product id.*valid ids: battery_'):
            bs.survey(['no_such_product'])

    def test_a_different_mill_changes_bite_numbers_not_provenance(self):
        m = self.r['mills']['foil']
        self.assertEqual(m['source'], 'user mill file')
        self.assertEqual(m['work_roll_radius_m'], 0.11)
        for k in ('pass.work_roll_radius_m', 'stand', 'spans', 'width_model.coil'):
            self.assertIn(k, m['keys_taken'])
        self.assertIn('material', m['keys_not_taken'])
        self.assertEqual(self.r['options']['mill_files'],
                         {'foil': 'my-mill.json', 'sheet': 'my-mill.json'})
        for pid in ('battery_pouch_laminate_foil', 'litho_sheet'):
            a, b = self.base[pid], self.rows[pid]
            self.assertEqual(a['catalogue_values_used'], b['catalogue_values_used'])
            self.assertEqual(a['entry_thickness_m'], b['entry_thickness_m'])
            self.assertNotEqual(a['separating_force_per_width_n_m'],
                                b['separating_force_per_width_n_m'])
            self.assertNotEqual(a['strip_to_mill_modulus_ratio'],
                                b['strip_to_mill_modulus_ratio'])
        # bite-free thresholds depend on the spans: shorter spans raise the trough onset
        a, b = self.base['household_foil'], self.rows['household_foil']
        self.assertGreater(abs(b['trough_onset_lateral_stress_pa']),
                           abs(a['trough_onset_lateral_stress_pa']))
        self.assertIn('user mill from my-mill.json', self.render())

    def render(self):
        return bs.render_survey_report(self.r)

    def test_overrides_are_applied_and_marked(self):
        ov = bs.validate_overrides({'battery_pouch_laminate_foil': {
            'exit_thickness_m': 35e-6, 'mean_flow_stress_pa': 150e6, 'width_m': 1.0}})
        r = bs.survey(['battery_pouch_laminate_foil'], overrides=ov,
                      override_source='plant data')['rows'][0]
        self.assertEqual((r['exit_thickness_m'], r['mean_flow_stress_pa'], r['strip_width_m']),
                         (35e-6, 150e6, 1.0))
        self.assertAlmostEqual(r['exit_tension_pa'], bs.EXIT_TENSION_FRACTION * 150e6)
        items = {x['item']: x for x in r['user_supplied_values']}
        self.assertEqual(set(items), {'exit_thickness_m', 'mean_flow_stress_pa', 'width_m'})
        self.assertTrue(all(x['basis'] == 'user-supplied (plant data)' for x in items.values()))
        used = {x['item'] for x in r['catalogue_values_used']}
        self.assertFalse(used & {'final pass gauges', 'flow stress'})
        self.assertFalse(r['flow_stress_assumed'])
        # the mill cannot take a pass too narrow for its bite model: a rejected row
        ov2 = bs.validate_overrides({'litho_sheet': {'width_m': 0.009}})
        x = bs.survey(['litho_sheet'], overrides=ov2)['rows'][0]
        self.assertEqual(x['bite_status'], 'NO_BITE')
        self.assertIn('width/h0 >= 20', x['rejected'])

    def test_invalid_mill_file_and_override_keys_error(self):
        with self.assertRaisesRegex(ValueError, 'must be a physicroll.band_case.v2 case'):
            bs.survey(FEW[:1], ROOT / 'scenarios' / 'band_diagnosis_bearing_order.json')
        bad = Path(self.tmp.name) / 'bad.json'
        bad.write_text('{"case_schema": "physicroll.band_case.v2"}')
        with self.assertRaisesRegex(ValueError, 'mill file .*bad.json'):
            bs.survey(FEW[:1], bad)
        with self.assertRaisesRegex(ValueError, "unknown key\\(s\\) 'speed'; allowed"):
            bs.validate_overrides({'litho_sheet': {'speed': 3.0}})
        with self.assertRaisesRegex(ValueError, 'unknown product id'):
            bs.validate_overrides({'litho': {'width_m': 1.0}})
        with self.assertRaisesRegex(ValueError, 'must be true or false'):
            bs.validate_overrides({'litho_sheet': {'doubled': 1}})
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit):
            bs.main(['--out', self.tmp.name, '--products', 'nope'])
        self.assertIn('valid ids', err.getvalue())

    def test_written_case_loads_and_diagnoses(self):
        out = Path(self.tmp.name) / 'cli'
        with redirect_stdout(io.StringIO()):
            bs.main(['--out', str(out), '--mill', str(self.mill_path), '--products',
                     'battery_pouch_laminate_foil', '--write-cases', str(out / 'cases')])
        path = out / 'cases' / 'battery_pouch_laminate_foil.case.json'
        case = load_case(path)
        self.assertEqual(case['material']['product'], 'battery_pouch_laminate_foil')
        self.assertEqual(case['pass']['work_roll_radius_m'], 0.11)
        self.assertTrue(all(v in (None, []) for v in case['observation'].values()))
        self.assertTrue(any(n.startswith('ASSUMED: flow stress') for n in case['notes']))
        self.assertTrue(any('BF-S34' in n for n in case['notes']))
        self.assertTrue(any('my-mill.json' in n for n in case['notes']))
        r = diagnose(case)
        self.assertEqual(r['product_check']['product_id'], 'battery_pouch_laminate_foil')
        json.dumps(r, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
