"""Review of ad3f3dc (band_thermal.thermal_check): whether the schedule lists the case pass is
decided by the engine's pass identity (``band_width.is_case_pass``), never by exit gauge and
speed, and a computed temperature is never lost to a rejected duplicate."""
import unittest

from physicroll import band_thermal as bt
from physicroll.band_diagnosis import diagnose
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import TRIBOLOGY, v2

PASS = {'entry_thickness_m': 60e-6, 'exit_thickness_m': 42e-6, 'mean_flow_stress_pa': 250e6,
        'friction_coefficient': 0.05, 'entry_tension_pa': 25e6, 'exit_tension_pa': 30e6,
        'exit_speed_m_s': 10.0}


def _reviewer_case(entry_m=44e-6):
    # the supplied-bite v2 fixture as a 60 -> 42 um operating pass, 340 K strip entry, battery
    # collector foil, and a schedule row at the same exit gauge and speed
    c = v2()
    c['pass'].update(entry_thickness_m=60e-6, exit_thickness_m=42e-6)
    c['model_options']['bite_response_override'].update(entry_thickness_m=60e-6,
                                                         exit_thickness_m=42e-6)
    c['material']['product'] = 'battery_collector_foil'
    c['tribology'] = dict(TRIBOLOGY, strip_entry_temperature_k=340.0)
    p = c['pass']
    c['schedule'] = [{'label': 'S1', 'entry_thickness_m': entry_m, 'exit_thickness_m': 42e-6,
                      **{k: p[k] for k in ('mean_flow_stress_pa', 'friction_coefficient',
                                           'entry_tension_pa', 'exit_tension_pa',
                                           'exit_speed_m_s')}}]
    return c


def _synthetic(op_t, row_t, row_entry=60e-6, finals=(0, 1)):
    """A hand-built result and case: the operating pass and one schedule row, each with an
    exit temperature in C or None (rejected)."""
    def heat(label, t):
        h = {'label': label, 'exit_thickness_m': 42e-6, 'exit_speed_m_s': 10.0}
        if t is None:
            h['rejected'] = f'planted rejection of {label}'
        else:
            h['exit_temperature_k'] = t + 273.15
        return h
    case = {'case_schema': 'physicroll.band_case.v2', 'width_model': None,
            'tribology': {'strip_heat_fraction': 0.22, 'inlet_temperature_k': 318.15,
                          'lubricant': {}},
            'material': {'product': 'battery_collector_foil'}, 'pass': dict(PASS),
            'schedule': [dict(PASS, label='S1', entry_thickness_m=row_entry)],
            'observation': {'band_positions_across_width_m': []}}
    res = {'process': {'heating': {'operating': heat('case pass', op_t),
                                   'schedule': [heat('S1', row_t)]}},
           'product_check': {'final_pass_row_indices': list(finals)}}
    return bt.thermal_check(res, case)


class CaseIdentityTests(unittest.TestCase):
    def test_reviewer_case(self):
        r = diagnose(_reviewer_case())
        tc = r['thermal_check']
        t = {x['row_index']: x for x in tc['strip_exit_temperatures']}
        # before: only the rejected S1 row, no flag
        self.assertAlmostEqual(t[0]['value'], 102.44, delta=0.01)
        self.assertEqual(t[0]['verdict'], 'ABOVE_PUBLISHED_LIMIT')
        self.assertTrue(t[0]['is_final_pass'])
        self.assertEqual(t[1]['verdict'], 'NOT_ASSESSABLE')
        self.assertIn(bt.PROPERTY_RISK_FLAG, tc['flags'])
        self.assertIn('is_case_pass', tc['strip_exit_temperature_rule'])
        render_band_report(r)

    def test_identical_schedule_row_listed_once(self):
        r = diagnose(_reviewer_case(entry_m=60e-6))
        temps = r['thermal_check']['strip_exit_temperatures']
        self.assertEqual([x['row_index'] for x in temps], [1])
        self.assertTrue(temps[0]['is_the_case_pass'])
        self.assertAlmostEqual(temps[0]['value'], 102.44, delta=0.01)
        self.assertIn(bt.PROPERTY_RISK_FLAG, r['thermal_check']['flags'])

    def test_identical_but_rejected_in_one_of_the_two(self):
        # the schedule row rejected, the operating pass computed: its value is shown once
        tc = _synthetic(95.0, None, finals=(1,))
        temps = tc['strip_exit_temperatures']
        self.assertEqual(len(temps), 1)
        self.assertEqual(temps[0]['row_index'], 0)
        self.assertEqual(temps[0]['value'], 95.0)
        self.assertEqual(temps[0]['identical_schedule_row_status'], 'NOT_ASSESSABLE')
        self.assertIn('planted rejection of S1', temps[0]['note'])
        # final through the identical row's index: the property-risk rule is not bypassed
        self.assertTrue(temps[0]['is_final_pass'])
        self.assertEqual(tc['flags'], [bt.PROPERTY_RISK_FLAG])
        # the other way round: the schedule row computed, the operating pass rejected
        tc = _synthetic(None, 95.0, finals=(0,))
        temps = tc['strip_exit_temperatures']
        self.assertEqual([x['row_index'] for x in temps], [1])
        self.assertEqual(temps[0]['operating_row_status'], 'NOT_ASSESSABLE')
        self.assertTrue(temps[0]['is_final_pass'])
        self.assertEqual(tc['flags'], [bt.PROPERTY_RISK_FLAG])
        # both rejected: one not-assessable row, never a property risk
        tc = _synthetic(None, None)
        self.assertEqual(len(tc['strip_exit_temperatures']), 1)
        self.assertEqual(tc['flags'], [])

    def test_same_exit_gauge_and_speed_other_entry_both_shown(self):
        tc = _synthetic(95.0, 70.0, row_entry=44e-6)
        temps = {x['row_index']: x for x in tc['strip_exit_temperatures']}
        self.assertEqual(sorted(temps), [0, 1])
        self.assertEqual(temps[0]['value'], 95.0)
        self.assertEqual(temps[1]['value'], 70.0)
        self.assertNotIn('is_the_case_pass', temps[1])
        self.assertEqual(tc['flags'], [bt.PROPERTY_RISK_FLAG])


if __name__ == '__main__':
    unittest.main()
