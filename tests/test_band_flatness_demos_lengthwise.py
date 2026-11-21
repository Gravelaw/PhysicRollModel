"""SPEC19 package 4: the closed spray loop on the lengthwise demo (full numerics) with the
planner's assumed shapemeter (29 zones of 52 mm on the strip centre; the demo carries none):
5 % valves keep trimming, on / off valves do not settle (planner: 119 and 444 changes). The
loop is the tool's own control law on this model, not the plant's controller.
"""
import unittest

from tests.test_band_flatness_demos import STEP05, demo_loop

SM = {'zone_width_m': 0.052, 'zone_count': 29, 'provenance': 'planner assumption (SPEC19)'}


class LengthwiseLoopTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.step = demo_loop('lengthwise_bands', STEP05, shapemeter=SM)
        cls.onoff = demo_loop('lengthwise_bands', [0.0, 1.0], shapemeter=SM)

    def test_stepped_valves_keep_trimming(self):
        r = self.step
        self.assertEqual(r['status'], 'TRIMMING_WITHIN_BAND')
        self.assertEqual(r['valve_changes'], 121)                 # planner 119
        self.assertAlmostEqual(r['initial']['max_abs_residual_i_units'], 39.02, delta=0.01)
        self.assertAlmostEqual(r['last_window']['max_abs_residual_i_units_highest'], 3.348,
                               delta=0.005)

    def test_on_off_valves_do_not_settle(self):
        r = self.onoff
        self.assertEqual(r['status'], 'NOT_SETTLED')
        self.assertIn('CONTROL_INCREASES_RESIDUAL', r['flags'])
        self.assertEqual(r['valve_changes'], 431)                 # planner 444
        self.assertGreater(r['last_window']['max_abs_residual_i_units_lowest'], 20.0)


if __name__ == '__main__':
    unittest.main()
