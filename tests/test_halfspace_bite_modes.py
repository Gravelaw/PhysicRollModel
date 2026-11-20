"""Reduced half-space bite: the shear-cap friction march and the benchmark mode of the printed
end conditions (SPEC18 package 3; split from test_halfspace_bite_cases.py for run time).

Software checks against the planner's worked numbers; not a validation on a mill.
"""
import json
import math
import unittest

from physicroll import foil_bite
from physicroll import halfspace_bite as hb

YS = 230e6
Y_PUB = YS * math.sqrt(3) / 2
E_PUB = 230e9 * 0.91
CAP_ARGS = dict(r=0.135, y=150e6 * math.sqrt(3) / 2, tb=20e6, tf=20e6, e=210e9)


def _solve(h0, h1, r=0.089, y=Y_PUB, mu=0.03, tb=0.0, tf=0.0, e=E_PUB, es=80e9, **kw):
    return hb.solve_half_space_bite(h0, h1, 1.0, r, y, mu, tb, tf, roll_youngs_modulus_pa=e,
                                    strip_plane_strain_modulus_pa=es, **kw)


def _w_bar(force):
    return force * 230e9 / (0.089 * YS ** 2)


def _rel(a, b):
    return abs(a / b - 1)


class ShearCapTests(unittest.TestCase):

    def test_shear_cap_march(self):
        """The slowest test (about 8 s). 50 -> 25 um, K 150 MPa, tensions 20 MPa, R 135 mm,
        E 210 GPa (E4's Table I pass [EX]), E_s* 80 GPa. A nominal friction of 0.10 is not the
        published case (X24): 32 times the load at 0.03."""
        args = CAP_ARGS
        expected = ((0.03, 1.0, 'A B E F', 1517220), (0.05, 1.0, 'A B F', 7718180),
                    (0.10, 1.0, 'A B F', 48652300), (0.05, 0.5, 'A B E F', 6313520),
                    (0.10, 0.5, 'A B F', 18534400))
        out = {}
        for mu, cap, structure, force in expected:
            r = _solve(50e-6, 25e-6, mu=mu, shear_cap_factor=cap, **args)
            out[(mu, cap)] = r
            self.assertEqual(r['zone_structure'], structure, (mu, cap))
            self.assertLess(_rel(r['force_per_width_n_m'], force), 5e-6, (mu, cap))
            if mu > 0.03:
                self.assertIn('COLD_START_BY_FRICTION_CONTINUATION', r['flags'])
                self.assertIn('SHEAR_CAP_ACTIVE', r['flags'])
        r = out[(0.05, 1.0)]
        self.assertAlmostEqual(r['forward_slip_fraction'], 0.5565, delta=5e-5)
        self.assertAlmostEqual(r['max_pressure_pa'] / r['plane_strain_strength_pa'], 19.18,
                               delta=5e-3)
        r = out[(0.10, 1.0)]
        self.assertAlmostEqual(r['forward_slip_fraction'], 0.6925, delta=5e-5)
        self.assertAlmostEqual(r['max_pressure_pa'] / r['plane_strain_strength_pa'], 34.39,
                               delta=5e-3)
        self.assertAlmostEqual(r['contact_length_m'], 12.15e-3, delta=5e-6)
        self.assertTrue(r['shear_cap_active'])
        self.assertIn('PEAK_PRESSURE_ABOVE_16_PLANE_STRAIN_YIELD', r['flags'])

    def test_mattress_rejects_where_this_solver_marches(self):
        y = 150e6 * math.sqrt(3) / 2
        for mu in (0.05, 0.06):
            with self.assertRaises(ValueError):
                foil_bite.solve_mattress_bite(50e-6, 25e-6, 1.0, 0.135, y, mu, 20e6, 20e6)
        r = _solve(50e-6, 25e-6, r=0.135, y=y, mu=0.06, tb=20e6, tf=20e6, e=210e9)
        self.assertIn('COLD_START_BY_FRICTION_CONTINUATION', r['flags'])
        self.assertGreater(r['convergence']['friction_march_steps'], 0)
        self.assertTrue(r['structure_selection'][0][1].startswith('failed'))


class PrintedEndTests(unittest.TestCase):

    def test_printed_end_conditions_family(self):
        """Benchmark mode only: the printed end conditions with a pressure ramp of prescribed
        length. The load rises without limit as the end shortens (W_bar 88.6 at 21 um, the
        element size the paper states, 117.5 at 5 um); the strip thickens before the exit."""
        rows = hb._printed_end_condition_family(20e-6, 15e-6, 1.0, 0.089, Y_PUB, 0.03, 0.0, 0.0,
                                                roll_youngs_modulus_pa=E_PUB)
        by = {round(r['end_length_m'] * 1e7): r for r in rows}
        for tenth_um, w_bar, length, peak, slip, thick in (
                (210, 88.62, 1.981e-3, 7.66, 0.2022, 0.00118),
                (100, 102.62, 2.131e-3, 7.85, 0.1902, 0.00252),
                (50, 117.47, 2.289e-3, 8.02, 0.1775, 0.00401)):
            r = by[tenth_um]
            self.assertLess(_rel(_w_bar(r['force_per_width_n_m']), w_bar), 1e-3)
            self.assertLess(_rel(r['contact_length_m'], length), 1e-3)
            self.assertLess(_rel(r['max_pressure_over_k'], peak), 1e-3)
            self.assertLess(_rel(r['forward_slip_fraction'], slip), 1e-3)
            self.assertLess(_rel(r['max_thickening_over_exit_gauge'], thick), 5e-3)
        loads = [r['force_per_width_n_m'] for r in rows]
        self.assertEqual(loads, sorted(loads))
        self.assertAlmostEqual(_w_bar(loads[0]), 78.01, delta=0.01)
        self.assertAlmostEqual(_w_bar(loads[-1]), 134.15, delta=0.01)
        self.assertTrue(all(r['max_thickening_over_exit_gauge'] > 0 for r in rows))
        pr = hb._Problem(20e-6, 15e-6, 0.089, YS, 0.03, 0.0, 0.0, 230e9, math.inf, 1.0,
                         'A B F', hb.DEFAULT_ZONES, end_length_m=10e-6)
        self.assertEqual(pr.unknown_count(), pr.n + 5)
        u = [1.0] * (pr.n - 1) + [-1.0 + 0.5 * i for i in range(pr.nb)] + [0.5, 1.2]
        self.assertEqual(len(pr.residual(u)), pr.n + 5)
        json.dumps(rows, allow_nan=False)
        self.assertNotIn('end_length_m', hb.solve_half_space_bite.__code__.co_varnames)


if __name__ == '__main__':
    unittest.main()
