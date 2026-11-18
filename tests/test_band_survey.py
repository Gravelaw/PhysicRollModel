"""SPEC12 stage C: the product survey (one synthetic final pass per catalogue product).

The survey is computed once (about 30 s); every test reads that result.
"""
import copy
import json
import re
import unittest
from pathlib import Path

from physicroll import band_diagnosis as bd
from physicroll import band_products as bp
from physicroll import band_survey as bs

ART = Path(__file__).resolve().parents[1] / 'artifacts' / 'band_diagnosis'


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


if __name__ == '__main__':
    unittest.main()
