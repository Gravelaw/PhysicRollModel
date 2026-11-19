"""SPEC13 part 2: material selection (literature alloy and temper for the final gauge), the
product question that no longer asks for alloy and temper, and the report section."""
import copy
import json
import unittest
from pathlib import Path

from physicroll import band_diagnosis as bd
from physicroll.band_diagnosis import diagnose, load_case, validate_case
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import v2

ROOT = Path(__file__).resolve().parents[1]
SCEN = ROOT / 'scenarios'
ART = ROOT / 'artifacts' / 'band_diagnosis'
STATUS = 'LITERATURE_PROPOSAL_TO_CONFIRM_WITH_PLANT'


def demo():
    return load_case(SCEN / 'band_diagnosis_battery_foil.json')


def ms_of(case):
    return bd._material_selection(validate_case(json.loads(json.dumps(case))), [])


def thin_case(final_um, flow=None, alloy='AA1235', temper='H18', stated=None):
    c = demo()
    c['schedule'] = [x for x in c['schedule'] if x['label'].split()[0] in ('F1', 'F2')]
    c['schedule'][-1]['exit_thickness_m'] = final_um * 1e-6
    if flow is not None:
        c['schedule'][-1]['mean_flow_stress_pa'] = flow
    c['material'].update(alloy=alloy, temper=temper)
    if stated is None:
        c['material'].pop('alloy_temper_stated', None)
    else:
        c['material']['alloy_temper_stated'] = stated
    return c


class MaterialSelectionTests(unittest.TestCase):
    def test_band_at_18_and_12(self):
        m = ms_of(thin_case(18))
        self.assertEqual(m['status'], STATUS)
        self.assertEqual(m['final_pass_band']['band_id'], '15_20')
        self.assertEqual(m['case_pass_band']['band_id'], '20_30')
        self.assertEqual(m['proposals']['standard']['alloy'], '1235')
        self.assertIn('evidence WEAK', m['sentence'])          # 18 um high-strength fallback
        m = ms_of(thin_case(12))
        self.assertEqual(m['final_pass_band']['band_id'], '10_13')
        self.assertEqual(m['proposals']['high_strength']['alloy'], '1100')
        self.assertNotIn('evidence WEAK', m['sentence'].split('Other route ends')[0])
        self.assertIn('MATERIAL_NOT_STATED_LITERATURE_PROPOSAL_SHOWN', m['flags'])
        self.assertIn('closest to the standard proposal', m['sentence'])

    def test_comparison_verdicts(self):
        f = {x['label'].split()[0]: x for x in ms_of(thin_case(12, flow=170e6))['comparison'][
            'passes']}
        self.assertEqual(f['F2']['verdict'], 'BELOW_STANDARD_MINIMUM')     # 170 < 180
        m = ms_of(thin_case(12, flow=170e6))
        self.assertIn('CASE_STRENGTH_BELOW_STANDARD_MINIMUM_FOR_GAUGE', m['flags'])
        f = {x['label'].split()[0]: x for x in ms_of(thin_case(18, flow=210e6))['comparison'][
            'passes']}
        self.assertEqual(f['F2']['verdict'], 'INSIDE_TYPICAL_RANGE')        # 200-220
        f = {x['label'].split()[0]: x for x in ms_of(thin_case(18, flow=230e6))['comparison'][
            'passes']}
        self.assertEqual(f['F2']['verdict'], 'ABOVE_TYPICAL_RANGE')
        f = {x['label'].split()[0]: x for x in ms_of(thin_case(18, flow=180e6))['comparison'][
            'passes']}
        self.assertEqual(f['F2']['verdict'], 'BETWEEN_STANDARD_MINIMUM_AND_TYPICAL_RANGE')
        m = ms_of(thin_case(18, alloy='AA3003'))
        self.assertEqual(m['comparison']['alloy']['verdict'], 'NOT_AN_OPTION_OF_THE_BAND')
        self.assertIn('the standard proposal 1235',
                      next(x for x in m['comparison']['passes']
                           if x['is_final_pass'])['compared_with'])
        m = ms_of(thin_case(18, temper='H19', stated=True))
        self.assertEqual(m['comparison']['temper']['verdict'], 'CONSISTENT')
        self.assertNotIn('MATERIAL_NOT_STATED_LITERATURE_PROPOSAL_SHOWN', m['flags'])
        self.assertTrue(m['sentence'].startswith('The case states the material'))
        self.assertIn('INDICATOR ONLY', m['comparison']['flow_stress_caveat'])

    def test_not_supplied_and_validation(self):
        c = thin_case(18)
        c['material']['product'] = None
        m = ms_of(c)
        self.assertTrue(m['not_supplied'])
        self.assertIn('battery_collector_foil', m['hint'])
        c['material']['product'] = 'household_foil'
        self.assertIn('no gauge-by-gauge', ms_of(c)['reason'])
        c = thin_case(18)
        c['material']['alloy_temper_stated'] = 'yes'
        with self.assertRaisesRegex(ValueError, 'alloy_temper_stated'):
            validate_case(c)

    def test_product_question_no_longer_asks_for_alloy_and_temper(self):
        c = validate_case(demo())
        for prod in ('battery_collector_foil', None):
            c['material']['product'] = prod
            q = bd._product_question(c['material'], 12e-6, '', '', 'H18')
            self.assertFalse(q['asks_for_alloy_and_temper'])
            for bad in ('which alloy', 'alloy and temper?', 'Ask the plant which alloy'):
                self.assertNotIn(bad, q['text'])
            if prod:
                self.assertIn('literature proposal', q['text'])
                self.assertIn('material_selection', q['text'])
            else:
                for want in ('pouch-laminate barrier foil', 'thick collector foil', 'tab foil',
                             '8021 35-55', 'set material.product'):
                    self.assertIn(want, q['text'])

    def test_committed_demo_matches_a_fresh_selection(self):
        # cheap fresh-run check of what SPEC13 adds to the battery demo (the whole demo takes
        # about 25 s; its material selection and product question depend on the inputs only)
        art = json.loads((ART / 'battery-foil-demo.result.json').read_text(encoding='utf-8'))
        fresh = ms_of(demo())
        self.assertEqual(json.dumps(art['material_selection'], sort_keys=True),
                         json.dumps(json.loads(json.dumps(fresh)), sort_keys=True))
        self.assertEqual(art['inputs']['material']['alloy_temper_stated'], False)
        self.assertIn('literature proposal for the final gauge 12 um',
                      art['foil_regime']['product_question']['text'])
        html = (ART / 'battery-foil-demo.report.html').read_text(encoding='utf-8')
        self.assertIn('Material selection', html)
        self.assertLess(html.index('Product check'), html.index('Material selection'))


class ScoresAndReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # the lengthwise v2 case at its own (sheet) gauge: the selection is then outside every
        # published band, which still renders, and the scores must not move
        base = v2()
        with_p = copy.deepcopy(base)
        with_p['material']['product'] = 'battery_collector_foil'
        without = copy.deepcopy(base)
        without['material']['product'] = None
        cls.a, cls.b = diagnose(with_p), diagnose(without)

    def test_scores_unchanged(self):
        self.assertIn('material_selection', self.a)
        self.assertEqual([(h['id'], h['score'], h['standing']) for h in self.a['hypotheses']],
                         [(h['id'], h['score'], h['standing']) for h in self.b['hypotheses']])
        self.assertNotIn('material_selection', self.b)   # sheet gauge, no product: unchanged
        self.assertEqual(self.a['material_selection']['final_pass_band']['status'],
                         'OUTSIDE_PUBLISHED_BANDS')

    def test_report_renders_and_escapes(self):
        html = render_band_report(self.a)
        self.assertIn('Material selection (literature proposal', html)
        r = copy.deepcopy(self.a)
        r['material_selection']['sentence'] = 'evil <b>&"'
        html = render_band_report(r)
        self.assertIn('evil &lt;b&gt;&amp;', html)
        self.assertNotIn('evil <b>&', html)
        self.assertNotIn('Material selection', render_band_report(self.b))


if __name__ == '__main__':
    unittest.main()
