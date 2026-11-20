"""Reduced half-space foil bite (``physicroll.halfspace_bite``, SPEC18 package 2).

Software checks only: the influence coefficients against closed forms and Hertz line contact,
the Winkler limit against the mattress solver, the planner's worked numbers (SPEC18 package 2,
produced by its standard-library prototype; pinned here to 1e-6 relative after agreeing with
the brief), the work identity and the rejections. Passing them does not validate the model on
a mill, and a value close to a published load would not either: the published load of the
foil case is not a grid-independent number (benchmarks.py, BT-V1).
"""
import json
import math
import unittest

from physicroll import foil_bite
from physicroll import halfspace_bite as hb

YS = 230e6
Y_PUB = YS * math.sqrt(3) / 2           # uniaxial flow stress giving K = Y_s
E_PUB = 230e9 * 0.91                    # roll E with E/(1 - 0.3^2) = E_R* = 230 GPa
AL = hb.ALUMINIUM_PLANE_STRAIN_MODULUS_PA

# name: (h0, h1, R, Y, mu, t_b, t_f, roll E, strip E_s*), structure, force N/m, forward slip,
# contact length m, p_max/K. Pins [run, 2026-11-20]; brief values in the comment.
CASES = {
    # published case (Fig. 9 of E1): 1902400.8, 0.203668, 2.03843 mm, 7.3315
    'published': ((20e-6, 15e-6, 0.089, Y_PUB, 0.03, 0.0, 0.0, E_PUB, 80e9), 'A B F',
                  1902400.8262138662, 0.20366789443940547, 0.0020384344556250494,
                  7.331458838064114),
    # 958396, 0.0709, 3.0580 mm, 2.197
    '140_70': ((140e-6, 70e-6, 0.089, Y_PUB, 0.03, 0.0, 0.0, E_PUB, 80e9), 'A F',
               958396.2011841041, 0.07086544486050572, 0.0030580299313940095,
               2.197397689876214),
    # 1392660, 0.2180, 2.4456 mm, 5.747
    '60_30': ((60e-6, 30e-6, 0.089, Y_PUB, 0.03, 0.0, 0.0, E_PUB, 80e9), 'A F',
              1392662.2909656938, 0.21798506607942558, 0.0024456309210148935,
              5.74691755811879),
    # 4239890, 0.4769, 3.1557 mm, 11.295
    '30_15': ((30e-6, 15e-6, 0.089, Y_PUB, 0.03, 0.0, 0.0, E_PUB, 80e9), 'A B F',
              4239892.51097468, 0.4769201994283683, 0.0031557477358569157,
              11.295312150386318),
    # 8364090, 0.5091, 4.2167 mm, 11.864
    '20_10': ((20e-6, 10e-6, 0.089, Y_PUB, 0.03, 0.0, 0.0, E_PUB, 80e9), 'A B F',
              8364086.110061222, 0.5091322532367017, 0.004216651815719808,
              11.863569283857819),
    # BT-V2 R 89 mm: 876108, 0.1295, 2.4897 mm, 3.104
    'btv2_r89': ((73e-6, 73e-6 * 0.43, 0.089, Y_PUB, 0.026, 0.107 * YS, 0.132 * YS, E_PUB,
                  80e9), 'A F',
                 876107.5340411479, 0.12945304435421456, 0.0024897297725070423,
                 3.1040431976254363),
    # BT-V2 R 135 mm: 2084240, 0.3103, 3.6184 mm, 6.475
    'btv2_r135': ((73e-6, 73e-6 * 0.43, 0.135, Y_PUB, 0.026, 0.107 * YS, 0.132 * YS, E_PUB,
                   80e9), 'A F',
                  2084239.0952775052, 0.3102698379027431, 0.0036184083008166616,
                  6.47541328209266),
    # battery-foil demo ALT2: 10128500, 0.5527, 5.7101 mm, 11.859
    'alt2': ((25e-6, 12e-6, 0.135, 185e6, 0.03, 38e6, 42e6, 210e9, AL), 'A B F',
             10128539.679649357, 0.5526634108030299, 0.005710136984904321, 11.85867587048394),
}
BRIEF = {'published': (1902400.8, 0.203668, 2.03843e-3, 7.3315),
         '140_70': (958396, 0.0709, 3.0580e-3, 2.197),
         '60_30': (1392660, 0.2180, 2.4456e-3, 5.747),
         '30_15': (4239890, 0.4769, 3.1557e-3, 11.295),
         '20_10': (8364090, 0.5091, 4.2167e-3, 11.864),
         'btv2_r89': (876108, 0.1295, 2.4897e-3, 3.104),
         'btv2_r135': (2084240, 0.3103, 3.6184e-3, 6.475),
         'alt2': (10128500, 0.5527, 5.7101e-3, 11.859)}


def _solve(args, **kw):
    h0, h1, r, y, mu, tb, tf, e, es = args
    return hb.solve_half_space_bite(h0, h1, 1.0, r, y, mu, tb, tf, roll_youngs_modulus_pa=e,
                                    strip_plane_strain_modulus_pa=es, **kw)


def _w_bar(force):
    return force * 230e9 / (0.089 * YS ** 2)


class InfluenceTests(unittest.TestCase):

    def test_uniform_grid_closed_form(self):
        def kappa(n):
            f = (lambda m: 0.0 if m == 0 else m * m * math.log(abs(m)))
            return 0.5 * (f(n + 1) - 2 * f(n) + f(n - 1))
        self.assertEqual(kappa(0), 0.0)
        self.assertAlmostEqual(kappa(1), 1.3862943611, delta=1e-10)
        self.assertAlmostEqual(kappa(2), 2.1711665768, delta=1e-10)
        self.assertAlmostEqual(kappa(3), 2.5891386521, delta=1e-10)
        d = 0.1
        x = [i * d for i in range(11)]
        mat = hb.influence_matrix(x)
        for j in range(11):
            for k in range(1, 10):
                self.assertAlmostEqual(mat[j][k - 1], d * (kappa(j - k) + math.log(d) - 1.5),
                                       delta=1e-12)

    def test_hat_integral_against_quadrature(self):
        x = [0.0, 0.03, 0.1, 0.22]
        value = hb.influence_matrix(x)[0][1]           # hat of node 0.1 at field point 0
        self.assertAlmostEqual(value, -0.2099798413, delta=1e-8)
        n = 200000                                     # midpoint rule over the hat

        def hat(t):
            return (t - 0.03) / 0.07 if t < 0.1 else (0.22 - t) / 0.12
        h = (0.22 - 0.03) / n
        quad = sum(hat(0.03 + (i + 0.5) * h) * math.log(abs(0.03 + (i + 0.5) * h))
                   for i in range(n)) * h
        self.assertAlmostEqual(quad, value, delta=1e-6)
        nodes = [-0.2, -0.05, 0.0, 0.07, 0.15, 0.3]
        slope = hb.influence_slope_matrix(nodes)
        step = 1e-6
        for j, s in enumerate(nodes):
            up = hb._influence_rows([s + step], nodes)[0]
            dn = hb._influence_rows([s - step], nodes)[0]
            for k in range(len(nodes) - 2):
                self.assertAlmostEqual(slope[j][k], (up[k] - dn[k]) / (2 * step), delta=1e-6)

    def test_hertz_line_contact_recovered(self):
        c80, c160 = hb.hertz_self_check(80), hb.hertz_self_check(160)
        self.assertLessEqual(c80['max_error_over_depth_all_nodes'], 3.0e-3)
        self.assertLessEqual(c80['max_error_over_depth_inner_nodes'], 1.0e-3)
        self.assertLessEqual(c160['max_error_over_depth_all_nodes'], 1.3e-3)
        self.assertLessEqual(c160['max_error_over_depth_inner_nodes'], 3.5e-4)
        errors = [hb.hertz_self_check(n)['max_error_over_depth_all_nodes']
                  for n in (20, 40, 80, 160)]
        self.assertEqual(errors, sorted(errors, reverse=True))
        self.assertAlmostEqual(c80['trapezoid_load_error_relative'], -1.48e-3, delta=1e-5)


class SolverTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.results = {name: _solve(c[0]) for name, c in CASES.items()}
        cls.published, cls.solution = _solve(CASES['published'][0], with_solution=True)

    def assertRel(self, value, expected, rel):
        self.assertLessEqual(abs(value - expected), rel * abs(expected),
                             f'{value!r} != {expected!r} (rel {rel})')

    def test_equation_count(self):
        for structure, count in (('A F', 67), ('A B F', 69), ('A B E F', 78)):
            pr = hb._Problem(20e-6, 15e-6, 0.089, YS, 0.03, 0.0, 0.0, 230e9, 80e9, 1.0,
                             structure, hb.DEFAULT_ZONES)
            self.assertEqual(pr.unknown_count(), count)
            bnd = [-1.0 + 0.25 * i for i in range(pr.nb)]
            u = [1.0] * (pr.n - 1) + bnd + [0.5] + ([1.2] if pr.flat else [])
            self.assertEqual(len(pr.residual(u)), pr.unknown_count())   # rows == unknowns
        n_af = hb._Problem(20e-6, 15e-6, 0.089, YS, 0.03, 0.0, 0.0, 230e9, 80e9, 1.0, 'A F',
                           hb.DEFAULT_ZONES)
        self.assertEqual(n_af.unknown_count(), n_af.n + 5)

    def test_winkler_limit_reproduces_the_mattress_solver(self):
        args = CASES['published'][0]
        pr, u, m = hb._mattress_start(args[0], args[1], 1.0, args[2], args[3], args[4],
                                      args[5], args[6], args[7], 0.3, args[8], 1.0,
                                      hb.DEFAULT_ZONES)
        self.assertEqual(pr.lam, 0.0)
        u, iterations, norm = pr.newton(u)
        self.assertLessEqual(iterations, 5)
        self.assertLess(norm, 1e-11)
        force = hb.HalfSpaceSolution(pr, u).force_per_width_n_m()
        p, bnd, g0, hn, x, h, _ = pr.fields(u)
        self.assertRel(force, m['force_per_width_n_m'], 0.01)
        self.assertAlmostEqual(h[pr.idx[4]] - 1.0, m['forward_slip_fraction'], delta=0.002)
        self.assertRel(force, 1011331.7, 1e-6)                          # planner's value

    def test_published_case_values(self):
        """Passing pins the solver on the inputs of the published case (Fig. 9 of E1); it is
        not an agreement with the published W_bar 118, which is not grid-independent."""
        self._row('published')
        r = self.published
        self.assertRel(_w_bar(r['force_per_width_n_m']), 92.936, 1e-5)
        self.assertRel(r['neutral_thickness_m'], 18.0550e-6, 1e-5)
        got = [r[k] * 1e3 for k in ('contact_start_m', 'plastic_entry_m', 'flat_zone_start_m',
                                    'flat_zone_end_m', 'plastic_exit_m', 'contact_end_m')]
        for a, b in zip(got, (-1.15102, -1.14379, -0.76082, 0.34941, 0.80957, 0.88742)):
            self.assertAlmostEqual(a, b, delta=1e-5)
        self.assertEqual(r['convergence']['newton_iterations'], 22)
        self.assertAlmostEqual(r['convergence']['mechanical_work_residual_relative'], 4.5e-6,
                               delta=1e-7)
        self.assertIn('STRIP_THICKNESS_SPRING_NOT_IN_PUBLISHED_MODEL', r['flags'])
        self.assertIn(hb.THICKNESS_SPRING_LIMITATION, r['limitations'])
        self.assertIn(hb.END_CLOSURE_LIMITATION, r['limitations'])

    def _row(self, name):
        _, structure, force, slip, length, pmax = CASES[name]
        r = self.results[name]
        self.assertEqual(r['zone_structure'], structure, name)
        self.assertEqual(r['regime'], 'conventional' if structure == 'A F' else 'foil')
        k = r['plane_strain_strength_pa']
        got = (r['force_per_width_n_m'], r['forward_slip_fraction'], r['contact_length_m'],
               r['max_pressure_pa'] / k)
        for value, pin, brief in zip(got, (force, slip, length, pmax), BRIEF[name]):
            self.assertRel(value, pin, 1e-6)                            # software pin
            self.assertRel(value, brief, 5e-3)                          # the brief's number

    def test_sheet_and_foil_rows(self):
        for name in ('140_70', '60_30', '30_15', '20_10', 'btv2_r89', 'btv2_r135', 'alt2'):
            self._row(name)

    def test_sheet_gauge_close_to_the_mattress(self):
        args = (300e-6, 210e-6, 0.2, 270e6, 0.03, 25e6, 30e6, 210e9, AL)
        r = _solve(args)
        m = foil_bite.solve_mattress_bite(300e-6, 210e-6, 1.0, 0.2, 270e6, 0.03, 25e6, 30e6)
        self.assertEqual(r['zone_structure'], 'A F')
        self.assertRel(r['force_per_width_n_m'], 1996305.2122150448, 1e-6)  # brief 1996310
        self.assertRel(m['force_per_width_n_m'], 1890500, 1e-4)
        self.assertRel(r['force_per_width_n_m'], m['force_per_width_n_m'], 0.08)

    def test_work_identity(self):
        names = ('published', '140_70', '30_15', 'btv2_r135', 'alt2')
        for name in names:
            r = self.results[name]
            self.assertLess(r['convergence']['mechanical_work_residual_relative'], 1e-4, name)
            plastic = r['plastic_work_power_over_roll_speed_n']
            two_trac = 2 * r['torque_per_work_roll_nm'] / r['work_roll_radius_m']
            res = (two_trac + r['net_tension_power_over_roll_speed_n'] - plastic
                   - r['slip_dissipation_both_interfaces_over_roll_speed_n'])
            self.assertLess(abs(res) / plastic, 1e-4, name)

    def test_no_slip_zone_fields(self):
        ns = self.published['no_slip_zone']
        self.assertEqual(set(ns), {'eq16_shear_over_limit_max', 'friction_hill_margin_min_over_k',
                                   'net_shear_over_limit', 'note', 'no_slip_zone_thickness_m',
                                   'relative_slip_in_no_slip_zone',
                                   'slip_term_over_plastic_power'})
        self.assertAlmostEqual(ns['relative_slip_in_no_slip_zone'], 0.0, delta=1e-12)
        self.assertAlmostEqual(ns['eq16_shear_over_limit_max'], 0.955, delta=5e-4)
        self.assertLessEqual(ns['eq16_shear_over_limit_max'], 1.0)
        self.assertGreaterEqual(ns['friction_hill_margin_min_over_k'], -1e-9)
        self.assertLessEqual(ns['net_shear_over_limit'], 1.0)
        self.assertIsNone(self.results['140_70']['no_slip_zone'])
        r = self.published
        self.assertEqual(r['backward_slip_zone_length_m'], 0.0)
        self.assertEqual(r['neutral_point_m'], r['flat_zone_end_m'])
        self.assertEqual(r['structure_selection'], [['cold_start_march', 'A B F candidate'],
                                                    ['rule 2: A B F', 'accepted']])
        self.assertIsNone(r['structure_nearest_rejected_candidate'])
        zones = r['profile']['zone']
        self.assertEqual(zones[0], 'entry_contact_zone')
        self.assertEqual(zones[-1], 'exit_contact_zone')
        self.assertIn('no_slip_flat', zones)
        self.assertTrue(set(zones) <= set(hb.ZONE_WORDS))
        self.assertTrue(all(p >= 0 for p in r['profile']['pressure_pa']))
        self.assertEqual(self.solution.structure, 'A B F')
        self.assertRel(self.solution.force_per_width_n_m(), r['force_per_width_n_m'], 1e-12)

    def test_candidates_beyond_the_friction_limit_get_zone_e(self):
        """Package 2 rejected these three A B F candidates (eq. (16) shear above the limit);
        the selection rule of package 3 rejects them again and accepts A B E F (rule 3) for
        the first two and A F (rule 4) for the 50 -> 30 um demo pass."""
        rigid = CASES['published'][0][:8] + (1e13,)
        for args, ratio, structure, rule in (
                (rigid, 1.446, 'A B E F', 3),
                ((30e-6, 18e-6, 0.135, 180e6, 0.03, 38e6, 42e6, 210e9, AL), 1.030, 'A B E F', 3),
                ((50e-6, 30e-6, 0.135, 175e6, 0.03, 35e6, 40e6, 210e9, AL), 2.941, 'A F', 4)):
            r = _solve(args)
            self.assertEqual((r['zone_structure'], r['structure_rule']), (structure, rule))
            first = r['structure_selection'][1]
            self.assertEqual(first[0], 'rule 2: A B F')
            self.assertIn(f'eq. (16) shear in the no-slip zone is {ratio:.3f}', first[1])

    def test_strip_modulus_trend(self):
        r40 = _solve(CASES['published'][0][:8] + (40e9,))
        self.assertRel(_w_bar(r40['force_per_width_n_m']), 96.751, 5e-5)
        r160 = _solve(CASES['published'][0][:8] + (160e9,))     # A B F candidate: shear 1.15
        cand = r160['structure_nearest_rejected_candidate']
        self.assertEqual(cand['structure'], 'A B F')
        self.assertIn('1.150 of the friction limit', cand['outcome'])
        self.assertRel(_w_bar(cand['force_per_width_n_m']), 90.933, 5e-5)
        self.assertEqual(r160['zone_structure'], 'A B E F')
        w160 = _w_bar(r160['force_per_width_n_m'])
        self.assertTrue(w160 < _w_bar(self.published['force_per_width_n_m'])
                        < _w_bar(r40['force_per_width_n_m']))

    def test_grid_doubled(self):
        """Every zone count doubled: the A B F candidate gives W_bar 93.299 (brief) with eq. (16)
        shear 1.31; zone E is inserted and the load is 0.37 % above the default grid."""
        r = _solve(CASES['published'][0], zones=tuple(2 * z for z in hb.DEFAULT_ZONES))
        cand = r['structure_nearest_rejected_candidate']
        self.assertIn('1.313 of the friction limit', cand['outcome'])
        self.assertRel(_w_bar(cand['force_per_width_n_m']), 93.299, 5e-5)
        self.assertEqual(r['zone_structure'], 'A B E F')
        self.assertRel(r['force_per_width_n_m'], self.published['force_per_width_n_m'], 5e-3)

    def test_rejections(self):
        base = CASES['published'][0]
        with self.assertRaisesRegex(ValueError, 'half-space bite domain'):
            _solve((20e-6, 25e-6) + base[2:])
        for kw in ({'strip_plane_strain_modulus_pa': 1e8}, {'shear_cap_factor': 0.0},
                   {'shear_cap_factor': 1.5}, {'zones': (3, 16, 24, 8, 16)},
                   {'zones': (1, 16, 24, 8, 16, 3)}, {'zones': (3, 16, 24, 2, 16, 3)},
                   {'zones': (3, 160, 160, 8, 160, 3)}, {'zones': (3, 16.0, 24, 8, 16, 3)}):
            args = dict(roll_youngs_modulus_pa=E_PUB, strip_plane_strain_modulus_pa=80e9)
            args.update(kw)
            with self.assertRaises(ValueError):
                hb.solve_half_space_bite(20e-6, 15e-6, 1.0, 0.089, Y_PUB, 0.03, 0.0, 0.0, **args)
        with self.assertRaisesRegex(ValueError, 'friction'):
            _solve(base[:4] + (0.5,) + base[5:])

    def test_json_safe(self):
        for r in self.results.values():
            json.dumps(r, allow_nan=False)
            self.assertEqual(r['status'], 'UNVALIDATED_REDUCED_HALF_SPACE_FOIL_BITE')
            self.assertEqual(r['model'], 'half_space_roll_rigid_plastic_slab_reduced')
            self.assertIn('REDUCED_HALF_SPACE_FOIL_MODEL', r['flags'])
            for absent in ('foundation_modulus_pa_m', 'unloaded_gap_m', 'limiting_thickness_m',
                           'stone_minimum_thickness_m'):
                self.assertNotIn(absent, r)

    def test_no_wall_time_in_result(self):
        def keys(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    yield k
                    yield from keys(v)
            elif isinstance(obj, list):
                for v in obj:
                    yield from keys(v)
        for k in keys(self.published):
            self.assertNotIn('time', k)
            self.assertNotIn('seconds', k)
        self.assertEqual(_solve(CASES['140_70'][0]), self.results['140_70'])   # reproducible


if __name__ == '__main__':
    unittest.main()
