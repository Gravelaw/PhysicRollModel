"""The survey on a user's mill file that is a copy of the template (the documented path), on a
mill without a coil, and on each demo scenario: it must finish, and a quantity a mill cannot
give is 'not assessable' with its reason, never a crash (review of a402d91)."""
import copy
import json
import pathlib
import tempfile
import unittest

from physicroll import band_survey as bs

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'scenarios' / 'band_diagnosis_template.json'
DEMOS_V2 = ('band_diagnosis_battery_foil.json', 'band_diagnosis_lengthwise_bands.json')
DEMOS_V1 = ('band_diagnosis_thin_gauge_chatter.json', 'band_diagnosis_bearing_order.json')
# a product subset for the demo mills (60 s budget): a foil product with the grade matrix,
# a household foil and a sheet product
SUBSET = ['battery_collector_foil', 'household_foil', 'can_body_stock']


class TemplateMillTests(unittest.TestCase):
    def test_template_as_mill_battery_collector_foil(self):
        # before: TypeError in _pct (both ridge heights None: the template has no coil)
        r = bs.survey(products=['battery_collector_foil'], foil_mill=str(TEMPLATE),
                      sheet_mill=str(TEMPLATE))
        m = r['battery_grade_matrix']
        self.assertIn('ridge not assessable (the mill has no width_model.coil)',
                      m['grade_sentence'])
        self.assertIn('critical ridge height not assessable (the mill has no width_model.coil)',
                      m['gauge_sentence'])
        self.assertIn('roller-wrinkle threshold magnitude not assessable (the mill has no '
                      'width_model.deflector_roll_radius_m)', m['gauge_sentence'])
        self.assertTrue(all(c.get('critical_ridge_error') for c in m['cells']
                            if c['status'] == 'EVALUATED'))
        rk = {x['mechanism']: x for x in r['rankings']}
        self.assertIn('the mill has no width_model.coil', rk['coil_ridges']['excluded'][0]['reason'])
        self.assertIn('deflector_roll_radius_m', rk['roller_wrinkles']['excluded'][0]['reason'])
        html = bs.render_survey_report(r)
        self.assertIn('not assessable: the mill has no width_model.coil', html)

    def test_mill_without_coil(self):
        c = json.loads((ROOT / 'scenarios' / DEMOS_V2[0]).read_text(encoding='utf-8'))
        c['width_model']['coil'] = None
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / 'no_coil.json'
            path.write_text(json.dumps(c), encoding='utf-8')
            r = bs.survey(products=['battery_collector_foil'], foil_mill=str(path))
        row = r['rows'][0]
        self.assertIsNone(row['critical_ridge_height_m'])
        self.assertEqual(row['critical_ridge_error'], 'the mill has no width_model.coil')
        self.assertIsNotNone(row['trough_onset_lateral_stress_pa'])
        self.assertIn('ridge not assessable (the mill has no width_model.coil)',
                      r['battery_grade_matrix']['grade_sentence'])
        bs.render_survey_report(r)

    def test_demo_scenarios_as_mill(self):
        for name in DEMOS_V2:
            path = str(ROOT / 'scenarios' / name)
            r = bs.survey(products=SUBSET, foil_mill=path, sheet_mill=path)
            self.assertEqual(len(r['rows']), len(SUBSET), name)
            bs.render_survey_report(r)
        for name in DEMOS_V1:
            # the two v1 demos are not mill files: a clean validation error
            with self.assertRaisesRegex(ValueError, 'must be a physicroll.band_case.v2'):
                bs.survey(products=SUBSET[:1], foil_mill=str(ROOT / 'scenarios' / name))


if __name__ == '__main__':
    unittest.main()
