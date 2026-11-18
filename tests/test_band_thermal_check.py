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
                'product_check': {'final_pass_labels': ['F2']}}

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
        self.assertEqual(tc['flags'], [])
        b = tc['growth']['steady_build_up']
        self.assertLess(b['time_to_50_percent_s'], b['time_to_90_percent_s'])
        for line in bt.THERMAL_MEASUREMENTS:
            self.assertIn(line, self.r['recommended_next_measurements'])
        html = (ART / 'battery-foil-demo.report.html').read_text(encoding='utf-8')
        self.assertIn('<h2>Process temperatures</h2>', html)


if __name__ == '__main__':
    unittest.main()
