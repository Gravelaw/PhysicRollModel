"""Review of cc3fa5f (band_diagnosis process sections): when the operating pass has no roll
bite, the per-pass parts that do not need it (pass heating of the schedule passes, friction
and flow-stress tables) are still computed, and the result says so."""
import copy
import unittest

from physicroll.band_diagnosis import diagnose
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import HARDENING, TRIBOLOGY, v2, width_model


def _case(row_friction=0.02, product=None, width=False):
    # reviewer: the v2 fixture without a supplied bite; operating pass 0.12 -> 0.084 mm at
    # 285 MPa and friction 0.03 with max_radius_ratio 2 (Hitchcock rejects it); a schedule
    # row identical except friction 0.02 (solves); tribology with a 340 K strip entry
    c = v2(override=False)
    c['pass'].update(entry_thickness_m=0.12e-3, exit_thickness_m=0.084e-3,
                     mean_flow_stress_pa=285e6, friction_coefficient=0.03)
    c['model_options']['max_radius_ratio'] = 2.0
    c['tribology'] = dict(TRIBOLOGY, strip_entry_temperature_k=340.0)
    c['hardening'] = copy.deepcopy(HARDENING)
    row = {k: c['pass'][k] for k in ('entry_thickness_m', 'exit_thickness_m',
                                     'mean_flow_stress_pa', 'entry_tension_pa',
                                     'exit_tension_pa', 'exit_speed_m_s')}
    row.update(label='R1', friction_coefficient=row_friction)
    c['schedule'] = [row]
    if product:
        c['material']['product'] = product
    if width:
        c['width_model'] = width_model(roll_heat_fraction_per_roll=None)
    return c


class OperatingBiteMissingTests(unittest.TestCase):
    def test_reviewer_case(self):
        r = diagnose(_case(product='battery_collector_foil'))
        self.assertIsNotNone(r['bite_error'])
        he = r['process']['heating']                  # before: null
        self.assertIn('no roll bite for the case pass', he['operating']['rejected'])
        self.assertIn('max_radius_ratio', he['operating']['rejected'])
        self.assertNotIn('exit_temperature_k', he['operating'])
        r1 = he['schedule'][0]
        self.assertAlmostEqual(r1['exit_temperature_k'] - 273.15, 127.07, delta=0.05)
        self.assertIn('schedule passes assessed with their own bites: R1',
                      he['operating_pass_note'])
        tc = r['thermal_check']
        t = {x['row_index']: x for x in tc['strip_exit_temperatures']}
        self.assertEqual(t[0]['verdict'], 'NOT_ASSESSABLE')
        self.assertIn('max_radius_ratio', t[0]['reason'])
        self.assertAlmostEqual(t[1]['value'], 127.07, delta=0.05)
        self.assertEqual(t[1]['verdict'], 'ABOVE_PUBLISHED_LIMIT')
        self.assertTrue(t[1]['is_final_pass'])
        self.assertIn('MODELLED_EXIT_TEMPERATURE_ABOVE_BATTERY_COIL_LIMIT', r['flags'])
        self.assertIn('still assessed: R1', tc['operating_pass_note'])
        # the per-pass tables that never needed the operating bite (item 3)
        fr = r['process']['friction']
        self.assertEqual([x['label'] for x in [fr['operating']] + fr['schedule']],
                         ['case pass', 'R1'])
        self.assertEqual(len(r['process']['flow_stress']['passes']), 2)
        # the friction-speed curve is of the operating bite: genuinely absent
        self.assertIsNone(r['process']['friction_speed_curve'])
        html = render_band_report(r)
        self.assertIn('The operating pass has no roll bite', html)
        self.assertIn('The operating pass has no strip exit temperature', html)
        self.assertIn('not assessable: no roll bite for the case pass', html)

    def test_with_width_model(self):
        r = diagnose(_case(width=True))
        w = r['width']
        self.assertEqual(w['thermal_steady']['status'], 'NOT_ASSESSABLE')
        self.assertIn('not computable without a bite', w['thermal_steady']['reason'])
        self.assertEqual(w['thermal_sensitivity']['status'], 'NOT_ASSESSABLE')
        self.assertIn('WIDTH_THERMAL_NOT_ASSESSABLE_NO_BITE_HEAT', r['flags'])
        self.assertAlmostEqual(r['process']['heating']['schedule'][0]['exit_temperature_k']
                               - 273.15, 127.07, delta=0.05)
        # the heat-streak evidence never reads a temperature from the rejected operating row
        h = {x['id']: x for x in r['hypotheses']}
        for hyp in h.values():
            for e in hyp['evidence']:
                if 'exit strip temperature' in e['criterion']:
                    self.assertIn('above limit: None', e['observed'])
        render_band_report(r)

    def test_both_fail(self):
        r = diagnose(_case(row_friction=0.031, product='battery_collector_foil'))
        he = r['process']['heating']
        self.assertIn('rejected', he['operating'])
        self.assertIn('rejected', he['schedule'][0])
        self.assertIn('assessed with their own bites: none', he['operating_pass_note'])
        tc = r['thermal_check']
        self.assertTrue(all(x['verdict'] == 'NOT_ASSESSABLE'
                            for x in tc['strip_exit_temperatures']))
        self.assertEqual(tc['flags'], [])
        self.assertIn('still assessed: none', tc['operating_pass_note'])
        render_band_report(r)


if __name__ == '__main__':
    unittest.main()
