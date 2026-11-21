"""Sensitivities of the reduced half-space bite and the bite-model comparison (SPEC18 package 4).

Software checks: the planner's sensitivity tables (prototype values; pinned here after they
agree to 1e-3), chord iterations against full Newton, signs, the one-sided tension flag and
the comparison of the three bite models on the battery-foil demo. The comparison is a spread
between models, not a correction of any of them.
"""
import json
import math
import unittest
from pathlib import Path

from physicroll import benchmarks as bm
from physicroll import halfspace_bite as hb
from physicroll.chatter import BitePass

YS = 230e6
Y_PUB = YS * math.sqrt(3) / 2
E_PUB = 230e9 * 0.91
ROOT = Path(__file__).resolve().parents[1]

# (h0, h1, E_s*): pins [run] of F_h, F_hin, F_se, F_sx (per width), dF/dmu, dF/dK, f_h, load
# exponent in friction; the brief's values in the comment
SENS = {
    # brief: -5.5756e11 2.7774e11 -6.4418e-3 -1.4705e-2 1.5605e8 2.0962e-2 -5.0653e4 2.461
    'published_80': ((20e-6, 15e-6, 80e9), 'A B F',
                     (-557559679989.4391, 277735254876.2225, -0.006438099331800859,
                      -0.014712560714515712, 156051477.94883233, 0.020962170325966714,
                      -50653.41214316454, 2.460861178126231),
                     (-5.5756e11, 2.7774e11, -6.4418e-3, -1.4705e-2, 1.5605e8, 2.0962e-2,
                      -5.0653e4, 2.461)),
    # brief: -5.4317e11 2.7202e11 -6.1349e-3 -1.3963e-2 1.4885e8 1.9945e-2 -5.1343e4 2.455
    'published_rigid': ((20e-6, 15e-6, 1e13), 'A B E F',
                        (-543165101667.78845, 272016586750.51294, -0.006131384896600252,
                         -0.013970235754939787, 148853187.356377, 0.019944507563779256,
                         -51342.47058187213, 2.4550565479576814),
                        (-5.4317e11, 2.7202e11, -6.1349e-3, -1.3963e-2, 1.4885e8, 1.9945e-2,
                         -5.1343e4, 2.455)),
    # brief: -1.0589e10 5.0365e9 -4.5143e-3 -2.1458e-3 2.6908e7 5.2683e-3 -1.4466e3 0.842
    '140_70': ((140e-6, 70e-6, 80e9), 'A F',
               (-10589330231.93053, 5036461025.456499, -0.004511716437339511,
                -0.0021454276517886223, 26908374.737979222, 0.005268302783764312,
                -1446.5618432657482, 0.8422938667140093),
               (-1.0589e10, 5.0365e9, -4.5143e-3, -2.1458e-3, 2.6908e7, 5.2683e-3, -1.4466e3,
                0.842)),
}

# battery-foil demo: half-space force/w, slip, contact length, Q/w, N_x'/w, load exponent;
# mattress force/w, slip, contact length (the brief's table)
DEMO = {'S1': ('A F', 7.4892e5, 0.036, 4.642e-3, 2.5692e9, 1.8046e-3, 0.675, 7.519e5, 0.029,
               4.783e-3),
        'S2': ('A F', 6.5387e5, 0.059, 3.141e-3, 9.0239e9, 2.3447e-3, 0.705, 6.409e5, 0.052,
               3.205e-3),
        'S3': ('A F', 8.0315e5, 0.101, 2.818e-3, 2.5761e10, 3.9077e-3, 1.258, 7.560e5, 0.100,
               2.829e-3),
        'F1': ('A F', 1.36995e6, 0.237, 2.654e-3, 1.9322e11, 1.6777e-2, 3.741, 9.586e5, 0.190,
               2.384e-3),
        'ALT1': ('A B E F', 2.65815e6, 0.416, 3.406e-3, 3.1795e11, 2.1410e-2, 3.044, 1.4877e6,
                 0.315, 2.759e-3),
        'F2': ('A B E F', 3.24388e6, 0.367, 3.346e-3, 6.4664e11, 2.9182e-2, 2.861, 1.5360e6,
               0.308, 2.317e-3),
        'ALT2': ('A B F', 1.01285e7, 0.553, 5.710e-3, 2.7362e12, 8.9049e-2, 3.278, 6.188e6,
                 0.422, 4.422e-3)}


def _derive(h0, h1, es):
    return hb.derive_bite_response_half_space(
        BitePass(h0, h1, 1.0, 0.089, Y_PUB, 0.03, 0.0, 0.0), roll_youngs_modulus_pa=E_PUB,
        strip_plane_strain_modulus_pa=es, with_state=True)


def _vector(bite, state):
    e = state['extra']
    return (bite.dforce_dexit_thickness_n_m, bite.dforce_dentry_thickness_n_m,
            bite.dforce_dentry_tension_m2, bite.dforce_dexit_tension_m2, e['dforce_dfriction_n'],
            e['dforce_dflow_stress_m2'] * math.sqrt(3) / 2, bite.dslip_dexit_thickness_per_m,
            e['load_exponent_in_friction'])


class SensitivityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = {name: _derive(*row[0]) for name, row in SENS.items()}

    def test_sensitivity_tables(self):
        for name, (_, structure, pins, brief) in SENS.items():
            bite, state = self.out[name]
            self.assertEqual(state['extra']['zone_structure'], structure)
            for got, pin, b in zip(_vector(bite, state), pins, brief):
                self.assertLessEqual(abs(got / pin - 1), 1e-6, (name, got, pin))
                self.assertLessEqual(abs(got / b - 1), 1e-3, (name, got, b))

    def test_signs_and_flags(self):
        for name, (bite, state) in self.out.items():
            self.assertLess(bite.dforce_dexit_thickness_n_m, 0)
            self.assertLess(bite.dforce_dentry_tension_m2, 0)
            self.assertLess(bite.dforce_dexit_tension_m2, 0)
            self.assertGreater(state['extra']['dforce_dfriction_n'], 0)
            self.assertIn('DERIVED_BY_HALF_SPACE_FOIL_MODEL', bite.flags)
            self.assertIn('REDUCED_HALF_SPACE_FOIL_MODEL', bite.flags)
            self.assertIn('ONE_SIDED_TENSION_DIFFERENCE_AT_ZERO_TENSION', bite.flags)
            self.assertEqual(bite.source, 'supplied')
            self.assertNotIn('profile', state['result'])
            json.dumps(state['extra'], allow_nan=False)
        bite, _ = hb.derive_bite_response_half_space(
            BitePass(20e-6, 15e-6, 1.0, 0.089, Y_PUB, 0.03, 20e6, 20e6),
            roll_youngs_modulus_pa=E_PUB, strip_plane_strain_modulus_pa=80e9, with_state=True)
        self.assertNotIn('ONE_SIDED_TENSION_DIFFERENCE_AT_ZERO_TENSION', bite.flags)
        with self.assertRaises(ValueError):
            hb.derive_bite_response_half_space('not a pass')

    def test_chord_equals_newton(self):
        _, state = self.out['published_80']
        sol = state['solution']
        pr0 = sol.problem
        _, jac = pr0.residual(sol.unknowns, True)
        lu = hb._lu_factor(jac)
        counter = {'chord': 0, 'newton': 0}
        change = {'h1': pr0.h1 * (1 + 1e-3)}
        pr, u = hb._perturbed(sol, lu, change, counter)
        self.assertEqual(counter, {'chord': 1, 'newton': 0})
        u_newton = pr.newton(hb._from_solution(sol, pr))[0]
        f_chord = hb.HalfSpaceSolution(pr, u).force_per_width_n_m()
        f_newton = hb.HalfSpaceSolution(pr, u_newton).force_per_width_n_m()
        self.assertLessEqual(abs(f_chord / f_newton - 1), 1e-6)


class ComparisonTests(unittest.TestCase):

    def test_bite_model_comparison_on_the_battery_foil_demo(self):
        """Three models, same inputs, against the brief's table to 1 %. Not a correction."""
        case = json.loads((ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json').read_text())
        comp = bm.bite_model_comparison(case)
        self.assertIn('Not a correction', comp['note'])
        rows = {r['label'].split()[0]: r for r in comp['rows'][1:]}
        for label, exp in DEMO.items():
            h, m = rows[label]['reduced_half_space'], rows[label]['experimental_mattress']
            self.assertEqual(h['zone_structure'], exp[0], label)
            got = (h['force_per_width_n_m'], h['forward_slip_fraction'], h['contact_length_m'],
                   h['strip_modulus_per_width_pa'],
                   h['exit_tension_force_sensitivity_per_width_m'],
                   h['load_exponent_in_friction'], m['force_per_width_n_m'],
                   m['forward_slip_fraction'], m['contact_length_m'])
            for g, e in zip(got, exp[1:]):
                tol = 0.01 * abs(e) if abs(e) > 0.2 else 6e-4      # slips quoted to 3 decimals
                self.assertAlmostEqual(g, e, delta=tol, msg=(label, g, e))
        self.assertIn('rejected', rows['F2']['hitchcock'])
        json.dumps(comp, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
