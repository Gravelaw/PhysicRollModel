"""SPEC18 package 9 in the engine: the computed bite heat partition beside the entered share.

The template case with a supplied bite response (fast: no bite derivations) runs three times:
as it is, with the heat partition switched off (the engine before the package), and with
``tribology.use_computed_heat_partition``.
"""
import copy
import json
import os
import unittest
from unittest import mock

from physicroll import band_diagnosis as bd
from physicroll import band_process as bp
from physicroll import band_report

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW_TRIBOLOGY_KEYS = ('interface_conductance_w_m2k', 'use_computed_heat_partition')


def _case():
    with open(os.path.join(ROOT, 'scenarios', 'band_diagnosis_template.json')) as fh:
        raw = json.load(fh)
    with open(os.path.join(ROOT, 'artifacts', 'band_diagnosis',
                           'lengthwise-bands-demo.result.json')) as fh:
        bite = json.load(fh)['bite']
    raw['model_options']['bite_response_override'] = {
        k: v for k, v in bite.items() if k not in ('source', 'flags', 'strip_modulus_n_m')}
    return raw


def _strip_new(result):
    """The result without the package's keys (as the engine gave it before the package)."""
    r = copy.deepcopy(result)
    for k in NEW_TRIBOLOGY_KEYS:
        r['inputs']['tribology'].pop(k)
    he = r['process']['heating']
    for row in [he['operating']] + he['schedule']:
        row.pop('heat_partition', None)
        row.pop('supplied_minus_computed_strip_heat_fraction', None)
    r['width']['thermal_sensitivity'].pop('computed_strip_share', None)
    r['thermal_check'].pop('computed_heat_partition', None)
    return r


class HeatPartitionEngineTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        raw = _case()
        cls.a = bd.diagnose(raw)
        with mock.patch.object(bp, 'pass_heat_partition', return_value=None):
            cls.before = bd.diagnose(raw)
        on = copy.deepcopy(raw)
        on['tribology']['use_computed_heat_partition'] = True
        cls.on = bd.diagnose(on)

    def test_heating_rows_carry_the_block(self):
        op = self.a['process']['heating']['operating']
        hp = op['heat_partition']
        self.assertEqual(hp['status'], 'UNVALIDATED_COMPUTED_HEAT_PARTITION')
        self.assertEqual(hp['supplied_strip_heat_fraction'], 0.84)
        self.assertAlmostEqual(op['supplied_minus_computed_strip_heat_fraction'],
                               0.84 - hp['strip_heat_fraction_computed'], delta=1e-15)
        self.assertEqual(op['strip_heat_fraction'], 0.84)            # entered share drives
        self.assertIn('STRIP_HEAT_FRACTION_SUPPLIED_NOT_COMPUTED', op['flags'])
        self.assertIn('ROLL_ENTRY_TEMPERATURE_ASSUMED_COOLANT_OR_OIL', hp['flags'])
        self.assertEqual(hp['roll_entry_surface_temperature_basis'],
                         'width_model.coolant_temperature_k')
        self.assertIn('k_oil/h', hp['interface_conductance_basis'])
        self.assertEqual([x['oil_conductivity_w_mk'] for x in
                          hp['strip_heat_fraction_at_published_oil_conductivities']],
                         [0.125, 0.25])
        self.assertEqual(hp['measured_strip_share_foil_mill']['range'], [0.11, 0.33])
        self.assertIsNone(self.a['inputs']['tribology']['use_computed_heat_partition'])
        cs = self.a['width']['thermal_sensitivity']['computed_strip_share']
        self.assertFalse(cs['used_by_the_rows_above'])

    def test_option_false_equals_before(self):
        # the 'before' run keeps the two validated tribology keys; nothing else is new in it
        self.assertNotIn('computed_heat_partition', self.before['thermal_check'])
        self.assertEqual(bd.result_json(_strip_new(self.a)),
                         bd.result_json(_strip_new(self.before)))
        self.assertIn('computed_heat_partition', self.a['thermal_check'])

    def test_option_true_drives_heating_and_width(self):
        op = self.on['process']['heating']['operating']
        f_c = op['heat_partition']['strip_heat_fraction_computed']
        self.assertEqual(op['strip_heat_fraction'], min(1.0, max(0.0, f_c)))
        self.assertIn('STRIP_HEAT_FRACTION_COMPUTED_FROM_INTERFACE_MODEL', op['flags'])
        self.assertNotIn('STRIP_HEAT_FRACTION_SUPPLIED_NOT_COMPUTED', op['flags'])
        used = self.on['width']['inputs_used']
        self.assertAlmostEqual(used['roll_heat_fraction_per_roll'], (1 - f_c) / 2, delta=1e-15)
        self.assertTrue(used['roll_heat_fraction_basis'].startswith('computed'))
        self.assertNotIn('supplied_minus_computed_strip_heat_fraction', op)

    def test_report_line(self):
        html = band_report.render_band_report(self.a)
        self.assertIn('heat share to the strip: entered 0.84, computed', html)
        self.assertNotIn('heat share to the strip', band_report.render_band_report(self.before))

    def test_validation(self):
        raw = _case()
        raw['tribology']['interface_conductance_w_m2k'] = 10.0
        with self.assertRaises(ValueError) as ctx:
            bd.validate_case(raw)
        self.assertIn('tribology.interface_conductance_w_m2k must be in [1000, 1e+09]',
                      str(ctx.exception))
        raw['tribology']['interface_conductance_w_m2k'] = 4e4
        raw['tribology']['use_computed_heat_partition'] = 'yes'
        with self.assertRaises(ValueError):
            bd.validate_case(raw)


if __name__ == '__main__':
    unittest.main()
