"""SPEC19 package 4: the closed spray loop on the battery-foil demo (full numerics, the
committed artifact's shape inputs), against the planner's prototype (s25/loop_sim2.py).

The brief's law weights the zones by their coverage and (as accepted in package 3) counts the
initial valve level as set at time 0. With it the 5 % valves do NOT settle on this demo within
1800 s: they keep trimming (TRIMMING_WITHIN_BAND). The planner's prototype weighted every
covered zone equally and let the first valve change happen at once; driven that way the same
code reproduces the planner's numbers exactly (65 changes, last at 1382 s, 2.46-2.56 I-units,
end reading 59.07). On / off valves do not settle either way. The loop is the tool's own
control law on this model, not the plant's controller.
"""
import json
import unittest
from pathlib import Path

from physicroll import band_diagnosis as bd
from physicroll import band_width as bw
from physicroll import flatness_control as flc

ROOT = Path(__file__).resolve().parents[1]
STEP05 = [i / 20 for i in range(21)]


def demo_loop(name, levels, *, shapemeter=None, prototype=False, **fc):
    """The width section's loop on a demo, with the committed artifact's shape inputs (no
    bite solve). ``prototype``: the planner's variant (unweighted zones, no initial dwell)."""
    art = json.loads((ROOT / 'artifacts' / 'band_diagnosis' /
                      f'{name.replace("_", "-")}-demo.result.json').read_text(encoding='utf-8'))
    raw = json.loads((ROOT / 'scenarios' / f'band_diagnosis_{name}.json').read_text(
        encoding='utf-8'))
    if shapemeter is not None:
        raw['measurement'] = {'shapemeter': shapemeter, 'thickness_gauge': None}
    raw['width_model']['flatness_control'] = dict(
        {'valve_levels': levels, 'initial_level': 1.0, 'minimum_on_time_s': 10.0,
         'minimum_off_time_s': 10.0, 'dead_band_i_units': 2.0, 'provenance': 'unit test'}, **fc)
    case = bd.validate_case(raw)
    w = case['width_model']
    iu = art['width']['inputs_used']
    sup = {k: iu[k] for k in ('strip_stiffness_per_width_pa', 'bite_half_length_m',
                              'exit_tension_force_sensitivity_per_width_m')}
    sp = bw.shape_params(case, None, w, None, supplied=sup)
    th = bw._Thermal(case, w, iu['bite_heat_per_width_w_m'], iu['roll_heat_fraction_per_roll'])
    healthy, actual = th.steady([1.0] * th.count), th.steady(th.levels)
    if not prototype:
        return bw.flatness_control_section(case, w, th, sp, healthy, actual)
    orig = flc.ZoneController.__init__

    def init(self, influence, weights, *a, **k):
        orig(self, influence, [1.0 if x > 0 else 0.0 for x in weights], *a, **k)
        self.changed_at = [-1e9] * len(self.changed_at)
    flc.ZoneController.__init__ = init
    try:
        return bw.flatness_control_section(case, w, th, sp, healthy, actual)
    finally:
        flc.ZoneController.__init__ = orig


class BatteryFoilLoopTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.step = demo_loop('battery_foil', STEP05)
        cls.onoff = demo_loop('battery_foil', [0.0, 1.0])
        cls.proto = demo_loop('battery_foil', STEP05, prototype=True)

    def test_stepped_valves_keep_trimming(self):
        r = self.step
        self.assertEqual(r['status'], 'TRIMMING_WITHIN_BAND')
        self.assertIn(bw.FC_FLAG_TRIMMING, r['flags'])
        for value, pinned in ((r['valve_changes'], 89), (r['last_valve_change_s'], 1756.0)):
            self.assertEqual(value, pinned)
        for value, pinned in ((r['initial']['max_abs_residual_i_units'], 19.27),
                              (r['initial']['max_abs_reading_i_units'], 24.33),
                              (r['last_window']['max_abs_residual_i_units_lowest'], 2.388),
                              (r['last_window']['max_abs_residual_i_units_highest'], 4.604),
                              (r['final']['max_abs_reading_i_units'], 79.32)):
            self.assertLess(abs(value / pinned - 1), 2e-3, (value, pinned))
        diag = [d['i_units_per_unit_level'] for d in r['set_up']['influence_diagonal']]
        self.assertTrue(all(-103 < v < -67 for v in diag[1:-1]))      # planner: -77 to -102
        self.assertIsNotNone(r['end_state_note'])

    def test_on_off_valves_do_not_settle(self):
        r = self.onoff
        self.assertEqual(r['status'], 'NOT_SETTLED')
        self.assertIn('CONTROL_INCREASES_RESIDUAL', r['flags'])
        self.assertTrue(400 <= r['valve_changes'] <= 450, r['valve_changes'])   # planner 424
        self.assertEqual(r['valve_changes'], 425)
        self.assertGreater(r['last_window']['max_abs_residual_i_units_highest'],
                           r['initial']['max_abs_residual_i_units'])
        self.assertIsNotNone(r['limit_cycle'])

    def test_prototype_variant_reproduces_the_planner(self):
        r = self.proto
        self.assertEqual(r['status'], 'SETTLED')
        self.assertEqual((r['valve_changes'], r['last_valve_change_s'],
                          r['control_steps_to_last_change']), (65, 1382.0, 691))
        self.assertAlmostEqual(r['last_window']['max_abs_residual_i_units_lowest'], 2.46,
                               delta=0.005)
        self.assertAlmostEqual(r['last_window']['max_abs_residual_i_units_highest'], 2.56,
                               delta=0.005)
        self.assertAlmostEqual(r['final']['max_abs_reading_i_units'], 59.07, delta=0.005)
        self.assertAlmostEqual(r['initial']['max_abs_residual_i_units'], 19.51, delta=0.005)


if __name__ == '__main__':
    unittest.main()
