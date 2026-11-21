"""SPEC14 part 2: thermal_check (case thermal inputs and modelled outputs against the
process-temperature literature), the report section and the temperature logs."""
import copy
import json
import unittest
from pathlib import Path

from physicroll import band_thermal as bt
from physicroll.band_diagnosis import diagnose, load_case, validate_case
from physicroll.band_report import render_band_report
from tests.test_band_robustness import v1case, v2case

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'band_diagnosis'


def by_item(fs):
    return {f['item']: f for f in fs}


class SheetCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = diagnose(v2case(width=True))

    def test_inputs_and_sheet_caveat(self):
        tc = self.r['thermal_check']
        self.assertFalse(tc['not_supplied'])
        f = by_item(tc['inputs'])
        share = f['strip_heat_fraction']
        self.assertEqual(share['verdict'], 'NO_PUBLISHED_RANGE')       # sheet gauge
        self.assertEqual(share['verdict_against_foil_literature'], 'ABOVE_PUBLISHED_RANGE')
        self.assertIn('(1 - strip share) / 2', share['conversion'])
        self.assertEqual(f['spray_heat_transfer_coefficient']['verdict'],
                         'WITHIN_PUBLISHED_RANGE')
        self.assertIn('spray_footprint_overlap', f)
        self.assertFalse(tc['battery_coil_limits_apply'])
        self.assertIn('no roll-wear model', ' '.join(tc['texts']))
        self.assertNotIn(bt.THERMAL_MEASUREMENTS[0], self.r['recommended_next_measurements'])

    def test_scores_unchanged_and_report(self):
        self.assertNotIn('thermal_check', diagnose(v1case()))
        html = render_band_report(self.r)
        self.assertIn('<h2>Process temperatures</h2>', html)
        evil = copy.deepcopy(self.r)
        evil['thermal_check']['note'] = 'x <b>&"'
        html = render_band_report(evil)
        self.assertIn('x &lt;b&gt;&amp;', html)
        self.assertNotIn('x <b>&', html)


class HeatPartitionConsistencyTests(unittest.TestCase):
    """Review finding: the per-pass temperatures were rescaled from the width model's share,
    not from the strip fraction the pass-heating rows used."""

    def _case(self, fs, frac):
        demo = json.loads((ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json').read_text())
        c = v2case(width=True)
        c['tribology'] = copy.deepcopy(demo['tribology'])
        c['tribology']['strip_heat_fraction'] = fs
        c['width_model']['roll_heat_fraction_per_roll'] = frac
        return c

    def test_inconsistent_inputs(self):
        r = diagnose(self._case(0.33, 0.08))
        self.assertIn(bt.HEAT_PARTITION_FLAG, r['flags'])
        hp = r['thermal_check']['heat_partition_inputs']
        self.assertEqual(hp['tribology_strip_heat_fraction'], 0.33)
        self.assertAlmostEqual(hp['width_model_strip_share_equivalent'], 0.84)
        heat_c = r['process']['heating']['operating']['exit_temperature_k'] - 273.15
        row = next(p for p in r['width']['thermal_sensitivity']['per_pass']
                   if abs(p['strip_heat_share'] - 0.33) < 1e-9)
        self.assertAlmostEqual(row['strip_exit_temperature_c'], heat_c, places=9)

    def test_consistent_inputs_no_flag(self):
        r = diagnose(self._case(0.84, None))
        self.assertNotIn(bt.HEAT_PARTITION_FLAG, r['flags'])
        self.assertIsNone(r['thermal_check']['heat_partition_inputs'])
        heat_c = r['process']['heating']['operating']['exit_temperature_k'] - 273.15
        row = next(p for p in r['width']['thermal_sensitivity']['per_pass']
                   if abs(p['strip_heat_share'] - 0.84) < 1e-9)
        self.assertAlmostEqual(row['strip_exit_temperature_c'], heat_c, places=9)
        self.assertAlmostEqual(bt.strip_rise_at_share(
            {'strip_heat_fraction': 0.0, 'bite_heat_per_width_w_m': 2.43e6 * 1e-4,
             'exit_thickness_m': 1e-4, 'exit_speed_m_s': 1.0, 'strip_temperature_rise_k': 0.0},
            0.5), 0.5)


class PropertyRiskTests(unittest.TestCase):
    """Unit check of the limit logic with a synthetic result (no bite needed)."""

    @staticmethod
    def _case(product='battery_collector_foil'):
        return {'case_schema': 'physicroll.band_case.v2', 'width_model': None,
                'tribology': {'strip_heat_fraction': 0.22, 'inlet_temperature_k': 318.15,
                              'lubricant': {}},
                'material': {'product': product}, 'pass': {'exit_thickness_m': 18e-6},
                'observation': {'band_positions_across_width_m': []}}

    def _result(self, t_final):
        rows = [{'label': lab, 'exit_temperature_k': t + 273.15}
                for lab, t in (('F1', 70.0), ('F2', t_final))]
        return {'process': {'heating': {'operating': rows[0], 'schedule': rows}},
                # final passes by row index (0 = the case pass, i >= 1 = schedule row i-1):
                # F2 is schedule row 1 (review of ac2e7df: never by label)
                'product_check': {'final_pass_labels': ['F2'], 'final_pass_row_indices': [2]}}

    def test_limits_and_flag(self):
        tc = bt.thermal_check(self._result(78.0), self._case())
        self.assertEqual(tc['flags'], [])
        self.assertIsNone(tc['property_risk'])
        tc = bt.thermal_check(self._result(95.0), self._case())
        t = {f['label']: f for f in tc['strip_exit_temperatures']}
        self.assertEqual(t['F2']['verdict'], 'ABOVE_PUBLISHED_LIMIT')
        self.assertTrue(t['F2']['above_90c'] and t['F2']['is_final_pass'])
        self.assertEqual(tc['flags'], [bt.PROPERTY_RISK_FLAG])
        self.assertIn('elongation', tc['property_risk']['literature_statement'])
        self.assertIn('not a coil temperature', tc['property_risk']['note'])
        # pouch foil: no coil limit published
        tc = bt.thermal_check(self._result(95.0), self._case('battery_pouch_laminate_foil'))
        self.assertEqual(tc['flags'], [])
        self.assertEqual(tc['strip_exit_temperatures'][1]['verdict'], 'NO_PUBLISHED_RANGE')

    def test_thermal_logs(self):
        c = self._case()
        self.assertEqual(bt.thermal_measurements(c), list(bt.THERMAL_MEASUREMENTS))
        c['material']['product'] = None
        c['pass']['exit_thickness_m'] = 0.4e-3
        self.assertEqual(bt.thermal_measurements(c), [])


class BatteryDemoArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((ART / 'battery-foil-demo.result.json').read_text(encoding='utf-8'))

    def test_committed_thermal_check_equals_a_fresh_one(self):
        # thermal_check depends on the case and on result sections only, so a fresh
        # evaluation on the committed result must reproduce it exactly
        case = validate_case(load_case(ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json'))
        r = copy.deepcopy(self.r)
        fresh = json.loads(json.dumps(bt.thermal_check(r, case)))
        self.assertEqual(json.dumps(fresh, sort_keys=True),
                         json.dumps(self.r['thermal_check'], sort_keys=True))

    def test_demo_values(self):
        tc = self.r['thermal_check']
        f = by_item(tc['inputs'])
        self.assertEqual(f['strip_heat_fraction']['verdict'], 'WITHIN_PUBLISHED_RANGE')
        self.assertEqual(f['strip_heat_fraction']['read_status'], 'abstract_or_snippet')
        self.assertEqual(f['spray_heat_transfer_coefficient']['verdict'],
                         'WITHIN_PUBLISHED_RANGE')
        self.assertEqual(f['spray_footprint_overlap']['verdict'], 'ABOVE_PUBLISHED_LIMIT')
        self.assertTrue(all(t['value'] < 80 for t in tc['strip_exit_temperatures']))
        self.assertEqual(tc['flags'], [bt.SPRAY_BASIS_FLAG])          # SPEC17 A5
        b = tc['growth']['steady_build_up']
        self.assertLess(b['time_to_50_percent_s'], b['time_to_90_percent_s'])
        for line in bt.THERMAL_MEASUREMENTS:
            self.assertIn(line, self.r['recommended_next_measurements'])
        html = (ART / 'battery-foil-demo.report.html').read_text(encoding='utf-8')
        self.assertIn('<h2>Process temperatures</h2>', html)



class SprayBasisAndFireLimitTests(unittest.TestCase):
    """SPEC17 A5 / X3 (basis of the spray coefficient) and A10 (fire limits): evaluated on the
    committed battery-foil result with a changed case (thermal_check reads only the two)."""

    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((ART / 'battery-foil-demo.result.json').read_text(encoding='utf-8'))
        cls.raw = json.loads((ROOT / 'scenarios' /
                              'band_diagnosis_battery_foil.json').read_text())

    def _tc(self, width=None, trib=None, result=None):
        c = copy.deepcopy(self.raw)
        c['width_model'].update(width or {})
        c['tribology'].update(trib or {})
        return bt.thermal_check(copy.deepcopy(result or self.r), validate_case(c))

    def test_spray_basis_keys_flag_and_unchanged_verdict(self):
        f = by_item(self.r['thermal_check']['inputs'])['spray_heat_transfer_coefficient']
        self.assertEqual(f['verdict'], 'WITHIN_PUBLISHED_RANGE')
        self.assertEqual(f['basis_comparable'], 'NOT_COMPARABLE')
        self.assertIn('roll-wall patch of one cooling zone', f['basis_comparable_reason'])
        self.assertIn('0.14 to 1.07 kW/m2K', f['basis_comparable_reason'])
        self.assertEqual(bt.SPRAY_BASIS_FLAG, 'SPRAY_COEFFICIENT_BASIS_NOT_COMPARABLE')
        self.assertIn('circumferential mean', f['value_basis'])
        self.assertIn('jet zone', f['published_basis'])
        self.assertNotIn('footprint_equivalent_w_m2k', f)
        self.assertIn(bt.SPRAY_BASIS_FLAG, self.r['flags'])
        html = (ART / 'battery-foil-demo.report.html').read_text(encoding='utf-8')
        self.assertIn('The two are not on the same basis', html)

    def test_wetted_arc_conversion_and_range(self):
        import math
        tc = self._tc(width={'spray_wetted_arc_rad': math.pi / 3})
        f = by_item(tc['inputs'])['spray_heat_transfer_coefficient']
        self.assertAlmostEqual(f['footprint_equivalent_w_m2k'], 20450.0, places=9)
        self.assertEqual(f['footprint_equivalent_verdict'], 'ABOVE_PUBLISHED_RANGE')
        self.assertEqual(f['verdict'], 'WITHIN_PUBLISHED_RANGE')      # verdict unchanged
        self.assertAlmostEqual(bt.footprint_equivalent_htc(3400.0, 50.0, 2 * math.pi), 3450.0)
        for bad in (0.0, -1.0, 7.0):
            c = copy.deepcopy(self.raw)
            c['width_model']['spray_wetted_arc_rad'] = bad
            with self.assertRaisesRegex(ValueError, r'spray_wetted_arc_rad must be in \(0, '
                                                    r'2\*pi\]'):
                validate_case(c)

    def test_fire_limits(self):
        fl = self.r['thermal_check']['fire_limits']
        self.assertTrue(fl['not_supplied'])
        self.assertEqual(fl['rows'], [])
        topics = {x['topic']: x for x in fl['context']}
        self.assertIn('PT-T9', topics['flash_point']['sources'])
        self.assertIn('PT-T15', topics['fire']['sources'])
        self.assertIn('EXIT_IS_NOT_COIL', fl['note'])
        tc = self._tc(trib={'oil_flash_point_k': 353.15})
        rows = tc['fire_limits']['rows']
        oil = next(x for x in rows if x['item'] == 'oil_inlet_temperature')
        self.assertAlmostEqual(oil['margin_k'], 35.0, places=9)
        self.assertEqual(oil['verdict'], 'BELOW_LIMIT')
        self.assertTrue(any(x['item'] == 'coolant_temperature_as_oil_supply' for x in rows))
        self.assertTrue(all(x['verdict'] == 'BELOW_LIMIT' for x in rows))   # demo below 80 C
        self.assertEqual(tc['flags'], [bt.SPRAY_BASIS_FLAG])
        # a pass hotter than the flash point (synthetic result of PropertyRiskTests)
        hot = PropertyRiskTests()._result(95.0)
        case = PropertyRiskTests._case()
        case['tribology'].update(oil_flash_point_k=353.15, oil_supply_temperature_cap_k=313.15)
        tc = bt.thermal_check(hot, case)
        f2 = next(x for x in tc['fire_limits']['rows'] if x.get('label') == 'F2')
        self.assertEqual(f2['verdict'], 'AT_OR_ABOVE_LIMIT')
        self.assertIn(bt.FIRE_FLAG_STRIP, tc['flags'])
        self.assertIn(bt.FIRE_FLAG_CAP, tc['flags'])                       # 45 C > 40 C cap
        self.assertNotIn(bt.FIRE_FLAG_OIL, tc['flags'])
        for key in ('oil_flash_point_k', 'oil_supply_temperature_cap_k'):
            for bad in (200.0, 800.0):
                c = copy.deepcopy(self.raw)
                c['tribology'][key] = bad
                with self.assertRaisesRegex(ValueError, key):
                    validate_case(c)


if __name__ == '__main__':
    unittest.main()
