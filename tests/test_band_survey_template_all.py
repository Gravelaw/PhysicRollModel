"""The documented path end to end: the unmodified template as the mill for every catalogue
product, with starter cases written, and one starter case diagnosed (review of a402d91)."""
import pathlib
import tempfile
import unittest

from physicroll import band_survey as bs
from physicroll.band_diagnosis import diagnose, load_case
from physicroll.band_report import render_band_report

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = str(ROOT / 'scenarios' / 'band_diagnosis_template.json')


class TemplateAllProductsTests(unittest.TestCase):
    def test_template_mill_all_products_and_starter_case(self):
        with tempfile.TemporaryDirectory() as d:
            result, jp, hp, cases = bs.write(pathlib.Path(d) / 'out', foil_mill=TEMPLATE,
                                             sheet_mill=TEMPLATE,
                                             cases_dir=pathlib.Path(d) / 'cases')
            self.assertEqual(len(result['rows']), 27)
            self.assertEqual(len(cases), 27)
            self.assertTrue(jp.exists() and hp.exists())
            # foil products the template's sheet-mill bite model cannot solve: no bite, not a
            # crash; every bite-free reason is stored
            for r in result['rows']:
                if r['bite_status'] == 'NO_BITE':
                    self.assertTrue(r['rejected'])
                self.assertTrue(r['critical_ridge_height_m'] is not None
                                or r.get('critical_ridge_error'))
            # one generated starter case through the engine
            case = next(p for p in cases if 'battery_collector_foil' in str(p))
            r = diagnose(load_case(case))
            render_band_report(r)


if __name__ == '__main__':
    unittest.main()
