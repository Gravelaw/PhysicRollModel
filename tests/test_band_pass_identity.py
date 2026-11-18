"""Review of ac2e7df: passes are identified by position (0 = the case pass, i >= 1 = schedule
row i-1), never by their display label. A schedule row may legally be labelled 'case pass'."""
import copy
import unittest

from physicroll.band_diagnosis import diagnose, validate_case
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import TRIBOLOGY, v2, width_model


def _row(label, h0, h1):
    return {'label': label, 'entry_thickness_m': h0, 'exit_thickness_m': h1,
            'mean_flow_stress_pa': 200e6, 'friction_coefficient': 0.03,
            'entry_tension_pa': 20e6, 'exit_tension_pa': 25e6, 'exit_speed_m_s': 10.0}


def _case(schedule, thermal=False):
    # reviewer: the v2 baseline (0.6 -> 0.42 mm case pass), a battery product and a
    # 30 -> 18 um schedule row named 'case pass'
    c = v2()
    c['material']['product'] = 'battery_collector_foil'
    c['schedule'] = schedule
    if thermal:
        c['tribology'] = dict(TRIBOLOGY)
        c['width_model'] = width_model(bite_heat_per_width_w_m=5000.0)
    return c


class PassIdentityTests(unittest.TestCase):
    def test_reviewer_case_material_selection(self):
        r = diagnose(_case([_row('case pass', 30e-6, 18e-6)]))
        ms = r['material_selection']
        self.assertEqual(ms['final_exit_thickness_m'], 18e-6)
        self.assertEqual(ms['final_pass_row_index'], 1)
        passes = ms['comparison']['passes']
        self.assertEqual([p['row_index'] for p in passes if p['is_final_pass']], [1])
        fp = ms['comparison']['final_pass']
        # before: the operating 420 um row, OUTSIDE_PUBLISHED_BANDS
        self.assertEqual(fp['exit_thickness_m'], 18e-6)
        self.assertNotEqual(fp['verdict'], 'OUTSIDE_PUBLISHED_BANDS')
        pc = r['product_check']
        self.assertEqual(pc['final_pass_row_index'], 1)
        self.assertEqual(pc['final_pass_labels'], ['case pass', 'case pass'])   # display
        self.assertEqual(pc['final_pass_row_indices'], [0, 1])  # both route ends, by index
        self.assertEqual([x['row_index'] for x in pc['rows']], [0, 1])
        render_band_report(r)

    def test_collision_through_product_check_thermal_check_and_per_pass(self):
        # the case pass (420 um) is NOT a route end here (R2 enters at its exit gauge); the
        # schedule row named 'case pass' (18 um) is final. By label the operating row was
        # marked final as well.
        r = diagnose(_case([_row('case pass', 30e-6, 18e-6), _row('R2', 420e-6, 300e-6)],
                           thermal=True))
        pc = r['product_check']
        self.assertEqual(pc['final_pass_row_indices'], [1, 2])
        self.assertFalse(pc['rows'][0]['is_final_pass'])
        tc = r['thermal_check']
        self.assertNotEqual(tc.get('status'), 'FAILED')
        by_idx = {t['row_index']: t for t in tc['strip_exit_temperatures']}
        self.assertEqual(by_idx[0]['label'], 'case pass')
        self.assertFalse(by_idx[0]['is_final_pass'])          # before: True (label match)
        self.assertTrue(by_idx[1]['is_final_pass'])
        self.assertTrue(by_idx[2]['is_final_pass'])
        pp = r['width']['thermal_sensitivity']['per_pass']
        heat = r['process']['heating']['schedule']
        for p in pp:
            src = heat[0] if p['label'] == 'case pass' else heat[1]
            self.assertEqual(p['exit_thickness_m'], src['exit_thickness_m'])
        self.assertEqual({p['exit_thickness_m'] for p in pp}, {18e-6, 300e-6})
        render_band_report(r)

    def test_duplicate_schedule_labels_are_rejected(self):
        c = _case([_row('R1', 30e-6, 18e-6), _row('R1', 50e-6, 30e-6)])
        with self.assertRaisesRegex(ValueError, 'duplicated'):
            validate_case(c)
        # 'case pass' as a schedule label is allowed (it is the operating row's display name)
        validate_case(_case([_row('case pass', 30e-6, 18e-6)]))

    def test_identical_schedule_row_is_still_the_case_pass(self):
        c = _case([])
        same = dict(copy.deepcopy(c['pass']), label='P1')
        same = {k: same[k] for k in _row('x', 1, 1)}
        c['schedule'] = [same, _row('R2', 30e-6, 18e-6)]
        r = diagnose(c)
        ms = r['material_selection']
        # is_case_pass drops the identical row from material selection; indices keep the
        # schedule position (the 18 um row is schedule row 1, index 2)
        self.assertEqual([p['row_index'] for p in ms['comparison']['passes']], [0, 2])
        self.assertEqual(ms['final_pass_row_index'], 2)
        self.assertEqual([x['row_index'] for x in r['product_check']['rows']], [0, 1, 2])


if __name__ == '__main__':
    unittest.main()
