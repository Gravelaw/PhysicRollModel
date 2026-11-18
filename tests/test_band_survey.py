"""SPEC12 stage C: the product survey (one synthetic final pass per catalogue product).

The survey is computed once (about 30 s); every test reads that result.
"""
import copy
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from physicroll import band_diagnosis as bd
from physicroll import band_products as bp
from physicroll import band_survey as bs
from physicroll.band_diagnosis import diagnose, load_case

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'band_diagnosis'
FEW = ['battery_pouch_laminate_foil', 'household_foil', 'litho_sheet']


class ProductSurveyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = bs.survey()
        cls.html = bs.render_survey_report(cls.r)
        cls.rows = {x['product_id']: x for x in cls.r['rows']}

    def test_every_catalogue_product_appears(self):
        ids = [p.id for p in bp.products() if p.final_gauge_m is not None]
        self.assertEqual([x['product_id'] for x in self.r['rows']], ids)
        self.assertEqual(self.r['schema'], 'physicroll.band_survey.v1')
        for x in self.r['rows']:
            self.assertLess(x['exit_thickness_m'], x['entry_thickness_m'])
            self.assertEqual(x['mill'], 'foil' if x['exit_thickness_m'] < 0.2e-3 else 'sheet')
            # every row says what came from the catalogue and what was assumed
            self.assertTrue(x['assumed_values'])
            for u in x['catalogue_values_used']:
                self.assertTrue(u['sources'], u)
                self.assertIn(u['read_status'], bp.READ_STATUSES)
            self.assertEqual(x['flow_stress_assumed'],
                             any(a['item'] == 'flow stress' for a in x['assumed_values']))
        # a published schedule's last pass is used where one exists (battery: single-sheet)
        b = self.rows['battery_collector_foil']
        self.assertEqual(b['gauge_basis'], 'published_schedule')
        self.assertFalse(b['doubled'])
        self.assertFalse(b['flow_stress_assumed'])
        # O temper: the as-rolled value is assumed, never the annealed strength
        h = self.rows['household_foil']
        self.assertTrue(h['flow_stress_assumed'])
        self.assertEqual(h['mean_flow_stress_pa'], bs.ASSUMED_AS_ROLLED_FLOW_STRESS_PA)

    def test_thinner_product_lower_ridge_and_trough_thresholds(self):
        same = sorted((x for x in self.r['rows'] if x['mill'] == 'foil'
                       and x['mean_flow_stress_pa'] == bs.ASSUMED_AS_ROLLED_FLOW_STRESS_PA),
                      key=lambda x: x['exit_thickness_m'])
        self.assertGreater(len(same), 5)
        for a, b in zip(same, same[1:]):
            if b['exit_thickness_m'] > a['exit_thickness_m']:
                self.assertLess(a['critical_ridge_height_m'], b['critical_ridge_height_m'])
                self.assertLess(abs(a['trough_onset_lateral_stress_pa']),
                                abs(b['trough_onset_lateral_stress_pa']))
                self.assertLess(abs(a['roller_wrinkle_threshold_pa']),
                                abs(b['roller_wrinkle_threshold_pa']))
        rk = {x['mechanism']: x for x in self.r['rankings']}
        for key in ('coil_ridges', 'troughs', 'roller_wrinkles'):
            self.assertGreater(rk[key]['gauge_rank_correlation'], 0.9, key)
            self.assertEqual(rk[key]['excluded'], [])

    def test_doubled_products_have_no_bite(self):
        dbl = [x for x in self.r['rows'] if x['doubled']]
        self.assertTrue(dbl)
        for p in bp.products():
            if p.rolled_mode == 'doubled':
                self.assertTrue(self.rows[p.id]['doubled'], p.id)
        for x in dbl:
            self.assertEqual(x['bite_status'], 'DOUBLED_PASS_NOT_MODELLED')
            for k in ('separating_force_per_width_n_m', 'stripe', 'critical_exit_speed_m_s',
                      'bite_credibility'):
                self.assertNotIn(k, x)
            self.assertIsNotNone(x['critical_ridge_height_m'])
            self.assertIn('DOUBLED_FINAL_PASS_NOT_MODELLED', x['flags'])
        self.assertIn('doubled pass not modelled', self.html)

    def test_credibility_marks_consistent_with_the_engine(self):
        for x in self.r['rows']:
            if x['bite_status'] != 'BITE':
                continue
            mark, ratio = bd._bite_credibility(x['bite_flags'],
                                               x['separating_force_per_width_n_m'])
            self.assertEqual(x['engine_bite_credibility'], mark)
            if x['product_id'] == bs.LOAD_RANGE_PRODUCT:
                self.assertEqual(x['bite_credibility'], mark)
                self.assertEqual(x.get('bite_force_ratio_to_reported_range'), ratio)
            else:
                self.assertEqual(x['bite_credibility'],
                                 None if mark is None else bs.NO_LOAD_RANGE)
            self.assertEqual(x['closed_gap_likely'], x['exit_thickness_m'] < 100e-6)
        # no ranking mixes a not-credible bite with credible ones
        bad = {x['label'] for x in self.r['rows']
               if x.get('bite_credibility') == bd.CREDIBILITY_OUTSIDE}
        for rk in self.r['rankings']:
            labels = {i['label'] for i in rk['most_sensitive_first']}
            excluded = {i['label'] for i in rk['excluded']}
            self.assertEqual(labels | excluded, {x['label'] for x in self.r['rows']})
            self.assertFalse(labels & excluded)
            if rk['mechanism'] not in ('coil_ridges', 'troughs', 'roller_wrinkles'):
                self.assertFalse(labels & bad, rk['mechanism'])

    def test_determinism_and_committed_artifacts(self):
        p = bp.product('converter_foil')
        mills = {k: bs._Mill(k) for k in bs.MILLS}
        again = bs.survey_row(p, mills, self.rows['converter_foil']['index'])
        self.assertEqual(json.dumps(again, sort_keys=True),
                         json.dumps(self.rows['converter_foil'], sort_keys=True))
        self.assertEqual(bs.result_json(self.r),
                         (ART / 'product-survey.result.json').read_text(encoding='utf-8'))
        self.assertEqual(self.html,
                         (ART / 'product-survey.report.html').read_text(encoding='utf-8'))

    def test_report_renders_escapes_and_is_finite(self):
        json.dumps(self.r, allow_nan=False)
        self.assertNotRegex(self.html, r'\b(nan|inf|NaN|Infinity)\b')
        self.assertIn('Rankings per mechanism', self.html)
        self.assertIn('class="scroll"', self.html)
        self.assertEqual(self.html.count('<svg'), len(self.r['rankings']))
        self.assertIn('Limitations and sources', self.html)
        evil = copy.deepcopy(self.r)
        evil['rows'][0]['product_name'] = '<b>&"x'
        out = bs.render_survey_report(evil)
        self.assertIn('&lt;b&gt;&amp;&quot;x', out)
        self.assertNotIn('<b>&"x', out)
        self.assertTrue(re.search(r'Excluded \(\d+\) and why', self.html))


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
