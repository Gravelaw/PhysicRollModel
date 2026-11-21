"""SPEC12 stage C: the product survey (one synthetic final pass per catalogue product).

The survey is computed once (about 30 s); every test reads that result.
"""
import copy
import io
import json
import re
import tempfile
import unittest
from unittest import mock
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
        # rows in 4 processes (band_survey.survey(workers=...)): the same result, asserted
        # against the committed artifact in test_determinism_and_committed_artifacts; serial
        # it takes about 55 s, above the module time limit
        cls.r = bs.survey(workers=4)
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
        self.assertEqual(self.html.count('<svg'), len(self.r['rankings']) + 1)  # + grade matrix
        self.assertIn('Battery foil by gauge and grade', self.html)
        self.assertIn('Limitations and sources', self.html)
        evil = copy.deepcopy(self.r)
        evil['rows'][0]['product_name'] = '<b>&"x'
        out = bs.render_survey_report(evil)
        self.assertIn('&lt;b&gt;&amp;&quot;x', out)
        self.assertNotIn('<b>&"x', out)
        self.assertTrue(re.search(r'Excluded \(\d+\) and why', self.html))


class SurveyProcessPoolTests(unittest.TestCase):
    """survey(workers=...) starts its pool by spawn and falls back to serial rows when the
    pool cannot start: the result is the same either way."""

    def test_pool_failure_falls_back_to_serial(self):
        serial = bs.survey(products=FEW)
        with mock.patch('concurrent.futures.ProcessPoolExecutor',
                        side_effect=OSError('no processes here')):
            with self.assertWarnsRegex(RuntimeWarning, 'rows computed serially'):
                fallback = bs.survey(products=FEW, workers=2)
        self.assertEqual(bs.result_json(fallback), bs.result_json(serial))

    def test_spawn_pool_equals_serial(self):
        serial = bs.survey(products=FEW)
        self.assertEqual(bs.result_json(bs.survey(products=FEW, workers=2)),
                         bs.result_json(serial))


class BatteryGradeMatrixTests(unittest.TestCase):
    """SPEC13 2.3: battery collector foil by gauge and grade (reads the survey result)."""

    @classmethod
    def setUpClass(cls):
        cls.m = json.loads((ART / 'product-survey.result.json').read_text(
            encoding='utf-8'))['battery_grade_matrix']
        cls.cells = {(c['gauge_um'], c['grade']): c for c in cls.m['cells']}

    def test_every_gauge_and_grade(self):
        self.assertEqual(set(self.cells), {(g, gr) for g in (20, 18, 15, 13, 12, 10)
                                           for gr in ('standard', 'high_strength')})
        for c in self.m['cells']:
            self.assertEqual(c['status'], 'EVALUATED', c['gauge_um'])
            self.assertEqual(c['mill'], 'foil')
            self.assertTrue(c['pass_basis'])
        self.assertIn('plant route 50 -> 30 -> 18', self.cells[(18, 'standard')]['pass_basis'])
        self.assertIn('plant route 50 -> 25 -> 12', self.cells[(12, 'standard')]['pass_basis'])
        self.assertIn('nearest published', self.cells[(15, 'standard')]['pass_basis'])
        self.assertEqual(self.cells[(18, 'standard')]['alloy'], '1235')
        self.assertEqual(self.cells[(12, 'high_strength')]['alloy'], '1100')
        self.assertIn('proof strength', self.m['ridge_strength_basis'])

    def test_thinner_lower_bite_free_thresholds(self):
        # at fixed grade AND fixed strength thinner foil has lower thresholds; where the
        # proposal's strength steps up between bands the ridge height may rise, and the
        # sentence must say so
        for grade in ('standard', 'high_strength'):
            cs = [self.cells[(g, grade)] for g in (20, 18, 15, 13, 12, 10)]
            for key in ('critical_ridge_height_m', 'trough_onset_lateral_stress_pa',
                        'roller_wrinkle_threshold_pa'):
                for a, b in zip(cs, cs[1:]):
                    if abs(b[key]) > abs(a[key]):
                        self.assertGreater(b['tensile_strength_pa'], a['tensile_strength_pa'],
                                           (grade, key, a['gauge_um']))
                        self.assertIn(f'from {a["gauge_um"]:g} to {b["gauge_um"]:g} um',
                                      self.m['gauge_sentence'])
                    elif b['tensile_strength_pa'] == a['tensile_strength_pa']:
                        self.assertLess(abs(b[key]), abs(a[key]))
            first, last = cs[0], cs[-1]
            self.assertLess(abs(last['trough_onset_lateral_stress_pa']),
                            abs(first['trough_onset_lateral_stress_pa']))
            self.assertLess(last['critical_ridge_height_m'], first['critical_ridge_height_m'])
        self.assertIn('thinner foil lowers the bite-free thresholds', self.m['gauge_sentence'])

    def test_credible_and_not_credible_never_mixed(self):
        cred = {k for k, c in self.cells.items() if c['credible']}
        for c in self.m['cells']:
            if not c['credible']:
                self.assertIn('bite_excluded_reason', c)
        # the gauge sentence names only credible gauges for the stripe trend
        txt = self.m['gauge_sentence']
        if 'on credible bites only (' in txt:
            named = txt.split('on credible bites only (')[1].split(')')[0]
            for g in named.replace(' um', '').split(', '):
                self.assertIn((float(g), 'standard'), {(float(a), b) for a, b in cred})
        both = self.m['grade_sentence'].split('both bites are credible (')[1].split(')')[0]
        for g in [x for x in both.replace(' um', '').split(', ') if x and x != 'none']:
            self.assertTrue(self.cells[(int(g), 'standard')]['credible'])
            self.assertTrue(self.cells[(int(g), 'high_strength')]['credible'])

    def test_weak_fallback_visible(self):
        c18 = self.cells[(18, 'high_strength')]
        self.assertTrue(c18['fallback_rule_weak'])
        self.assertEqual(c18['evidence'], 'weak')
        self.assertFalse(self.cells[(12, 'high_strength')]['fallback_rule_weak'])
        self.assertIn('the high-strength proposal at 18 um (1100)', self.m['grade_sentence'])
        self.assertIn('Evidence WEAK', self.m['grade_sentence'])

    def test_main_battery_row_uses_the_proposal(self):
        r = json.loads((ART / 'product-survey.result.json').read_text(encoding='utf-8'))
        row = next(x for x in r['rows'] if x['product_id'] == 'battery_collector_foil')
        self.assertEqual(row['material_proposal']['status'],
                         'LITERATURE_PROPOSAL_TO_CONFIRM_WITH_PLANT')
        self.assertEqual(row['alloy_checked'], row['material_proposal']['alloy'])
        self.assertAlmostEqual(row['mean_flow_stress_pa'],
                               row['material_proposal']['tensile_strength_pa'])
        fs = next(x for x in row['catalogue_values_used'] if x['item'] == 'flow stress')
        self.assertIn('LITERATURE PROPOSAL', fs['basis'])

    def test_starter_case_carries_the_proposal(self):
        r = json.loads((ART / 'product-survey.result.json').read_text(encoding='utf-8'))
        row = next(x for x in r['rows'] if x['product_id'] == 'battery_collector_foil')
        mills = {k: bs._Mill(k) for k in bs.MILLS}
        c = bs.starter_case(row, mills[row['mill']])
        pr = row['material_proposal']
        self.assertEqual((c['material']['alloy'], c['material']['temper']),
                         (pr['alloy'], pr['temper']))
        self.assertIs(c['material']['alloy_temper_stated'], False)
        self.assertAlmostEqual(c['material']['yield_stress_pa'], pr['proof_strength_pa'])
        self.assertTrue(any(n.startswith('MATERIAL: LITERATURE PROPOSAL') for n in c['notes']))
        self.assertTrue(any('BG-G2' in n for n in c['notes']))


if __name__ == '__main__':
    unittest.main()
