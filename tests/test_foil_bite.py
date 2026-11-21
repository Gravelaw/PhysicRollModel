"""Internal-consistency checks of the EXPERIMENTAL mattress (Winkler) roll-bite model.

Software verification only (rigid limit, junction continuity, Coulomb limits, energy identity,
grid convergence, trends). None of these checks validates the model against a mill or a
published foil benchmark.
"""
import json
import math
import unittest

from physicroll.chatter import (BitePass, BiteResponse, StandModel, StripSpans, critical_speed,
                                derive_bite_response)
from physicroll.foil_bite import (FOUNDATION_COEFFICIENT, STATUS, derive_bite_response_mattress,
                                  solve_mattress_bite)
from physicroll.model import Scenario
from physicroll.slab import _solve_grid

SHEET = (0.6e-3, 0.42e-3, 1.5, 0.2, 250e6, 0.05, 25e6, 30e6)          # Hitchcock: 3.556 MN
MID_MU05 = (0.3e-3, 0.21e-3, 1.5, 0.2, 270e6, 0.05, 25e6, 30e6)       # Hitchcock rejects
MID_MU03 = (0.3e-3, 0.21e-3, 1.5, 0.2, 270e6, 0.03, 25e6, 30e6)       # Hitchcock: 2.787 MN
THIN = (0.12e-3, 0.084e-3, 1.5, 0.2, 285e6, 0.03, 25e6, 30e6)         # Hitchcock rejects
FOIL_MU03 = (50e-6, 25e-6, 1.5, 0.135, 150e6, 0.03, 20e6, 20e6)
FOIL_MU10 = (50e-6, 25e-6, 1.5, 0.135, 150e6, 0.10, 20e6, 20e6)       # nominal mu 0.10
E_STAR = 210e9 / (1 - 0.3 ** 2)


class RigidLimitTests(unittest.TestCase):
    """K_p -> infinity must reproduce slab._solve_grid with a rigid roll."""

    def test_force_slip_torque_match_rigid_slab(self):
        # Small bite angle: the mattress gap is the parabola h1 + x^2/R, slab.py uses the exact
        # circle; their contact lengths differ by ~draft/(8R) = 2e-4 here, the force by ~3e-4.
        h0, h1, radius, y, mu, tb, tf = 2e-3, 1.6e-3, 0.25, 200e6, 0.1, 20e6, 30e6
        slab = _solve_grid(Scenario('rigid', True, h0, h1, 1.5, 1.0, radius, 2700.0, y, mu,
                                    tb, tf, 1.0), 2048, 'established', None, None)
        for end_zones in (True, False):
            r = solve_mattress_bite(h0, h1, 1.5, radius, y, mu, tb, tf,
                                    foundation_modulus_pa_m=1e22, cells=200,
                                    contact_end_zones=end_zones)
            self.assertEqual(r['regime'], 'conventional')
            self.assertAlmostEqual(r['separating_force_n'] / slab['separating_force_n'], 1,
                                   delta=1e-3)
            self.assertAlmostEqual(r['forward_slip_fraction'], slab['forward_slip_fraction'],
                                   delta=1e-3)
            self.assertAlmostEqual(r['torque_per_work_roll_nm'] / slab['torque_per_work_roll_nm'],
                                   1, delta=1e-3)
            self.assertLess(r['exit_zone_length_m'], 1e-5)
            self.assertIn('FOUNDATION_MODULUS_SUPPLIED', r['flags'])


class SheetAndHitchcockRangeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sheet = solve_mattress_bite(*SHEET)
        cls.sheet_literal = solve_mattress_bite(*SHEET, contact_end_zones=False)

    def test_sheet_case_is_conventional_and_same_order_as_hitchcock(self):
        for r in (self.sheet, self.sheet_literal):
            self.assertEqual(r['regime'], 'conventional')
            self.assertEqual(r['flat_zone_share'], 0.0)
            # Reported, not asserted tightly: Hitchcock slab gives 3.556 MN, f = 0.0553.
            self.assertTrue(0.5 < r['separating_force_n'] / 3.556e6 < 2.0)
            self.assertTrue(0.0 < r['forward_slip_fraction'] < 0.15)
            self.assertIn('MATTRESS_REGIME_CONVENTIONAL', r['flags'])
            self.assertIn('EXPERIMENTAL_MATTRESS_FOIL_MODEL', r['flags'])
            self.assertIn('FOUNDATION_MODULUS_FROM_MEMORY_FORMULA', r['flags'])
        self.assertIn('CONTACT_END_ZONES_ADDED_TO_SPEC_EQUATIONS', self.sheet['flags'])
        self.assertIn('SPEC_LITERAL_END_CONDITIONS_OVERLAP', self.sheet_literal['flags'])

    def test_foundation_modulus_is_fixed_point_of_contact_length(self):
        for r in (self.sheet, self.sheet_literal):
            a = r['contact_length_m'] / 2
            self.assertAlmostEqual(r['foundation_modulus_pa_m'] * a /
                                   (FOUNDATION_COEFFICIENT * E_STAR), 1, delta=1e-9)
        self.assertAlmostEqual(FOUNDATION_COEFFICIENT, 1.178, delta=1e-3)

    def test_end_zone_equilibrium_and_smooth_exit_junction(self):
        r = self.sheet
        k, mu = r['plane_strain_strength_pa'], r['friction_coefficient']
        h0, h1, w = r['entry_thickness_m'], r['exit_thickness_m'], r['width_m']
        # exit zone: sigma rises from K - p_e to t_f through backward friction
        sigma_e = r['exit_tension_pa'] - 2 * mu * r['exit_zone_force_n'] / w / h1
        self.assertAlmostEqual((k - sigma_e) / r['pressure_plastic_exit_pa'], 1, delta=1e-9)
        # entry zone: sigma falls from t_b through forward friction until yield
        sigma_i = r['entry_tension_pa'] - 2 * mu * r['entry_zone_force_n'] / w / h0
        self.assertAlmostEqual((k - sigma_i) / r['pressure_plastic_entry_pa'], 1, delta=1e-9)
        # h' = 0 at the exit point: branch slope -2 mu p/h equals foundation slope -K_p x/R
        kp, radius = r['foundation_modulus_pa_m'], r['work_roll_radius_m']
        self.assertAlmostEqual(kp * r['plastic_exit_m'] / radius /
                               (2 * mu * r['pressure_plastic_exit_pa'] / h1), 1, delta=1e-9)
        # both contact zones end at zero pressure on the unloaded roll profile
        g0 = r['unloaded_gap_m']
        self.assertAlmostEqual(g0 + r['contact_end_m'] ** 2 / radius, h1, delta=1e-12)
        self.assertAlmostEqual(g0 + r['contact_start_m'] ** 2 / radius, h0, delta=1e-12)
        self.assertGreater(r['exit_zone_length_m'], 0)
        lit = self.sheet_literal
        self.assertEqual(lit['exit_zone_length_m'], 0.0)
        self.assertAlmostEqual(lit['pressure_plastic_exit_pa'], k - lit['exit_tension_pa'],
                               delta=1e-6 * k)

    def test_work_identity_and_grid_convergence(self):
        for r in (self.sheet, self.sheet_literal):
            c = r['convergence']
            self.assertLess(c['mechanical_work_residual_relative'], 1e-8)
            self.assertLess(c['force_relative_change_on_refinement'], 1e-6)
            self.assertLess(c['slip_absolute_change_on_refinement'], 1e-7)
            self.assertLess(c['junction_pressure_mismatch_pa'], 1e-3)
            self.assertLess(c['fixed_point_residual_relative'], 1e-10)
        coarse = solve_mattress_bite(*SHEET, cells=64)
        self.assertAlmostEqual(coarse['separating_force_n'] / self.sheet['separating_force_n'],
                               1, delta=1e-5)
        self.assertGreater(self.sheet['slip_dissipation_both_interfaces_over_roll_speed_n'], 0)

    def test_hitchcock_rejected_mid_gauge_now_solves(self):
        with self.assertRaises(ValueError):
            derive_bite_response(BitePass(*MID_MU05), cells=64)
        r = solve_mattress_bite(*MID_MU05)
        self.assertEqual(r['regime'], 'conventional')
        self.assertGreater(r['separating_force_n'], solve_mattress_bite(*MID_MU03)
                           ['separating_force_n'])
        self.assertIn('THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN', r['flags'])

    def test_thin_case_lands_in_foil_regime(self):
        r = solve_mattress_bite(*THIN)
        self.assertEqual(r['regime'], 'foil')
        self.assertGreater(r['flat_zone_share'], 0.0)
        self.assertLess(r['max_flat_shear_over_coulomb'], 1 + 1e-9)


class FoilRegimeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.foil = solve_mattress_bite(*FOIL_MU03)

    def test_flat_zone_shear_within_coulomb_and_continuity(self):
        r = self.foil
        self.assertEqual(r['regime'], 'foil')
        self.assertGreater(r['flat_zone_share'], 0.1)
        kp, radius, mu = r['foundation_modulus_pa_m'], r['work_roll_radius_m'], 0.03
        h_n, g0 = r['neutral_thickness_m'], r['unloaded_gap_m']
        x_a, x_b = r['flat_zone_start_m'], r['flat_zone_end_m']

        def p_flat(x):
            return kp * (h_n - g0 - x * x / radius) / 2
        for n in range(201):
            x = x_a + (x_b - x_a) * n / 200
            tau = h_n / 2 * (-kp * x / radius)
            self.assertLessEqual(abs(tau), mu * p_flat(x) * (1 + 1e-9))
        self.assertAlmostEqual(r['flat_shear_over_coulomb_at_start'], 1, delta=1e-9)
        # pressure continuity at both junctions (entry branch -> flat, flat -> exit branch)
        self.assertAlmostEqual(p_flat(x_a) / r['pressure_flat_start_pa'], 1, delta=1e-12)
        self.assertLess(r['convergence']['junction_pressure_mismatch_pa'],
                        1e-9 * r['pressure_flat_end_pa'])
        self.assertAlmostEqual(r['forward_slip_fraction'],
                               h_n / r['exit_thickness_m'] - 1, delta=1e-12)
        zones = r['profile']['zone']
        self.assertIn('no_slip_flat', zones)
        self.assertEqual(zones[0], 'entry_contact_zone')
        self.assertEqual(zones[-1], 'exit_contact_zone')
        self.assertTrue(all(p >= 0 for p in r['profile']['pressure_pa']))
        self.assertIn('FORWARD_SLIP_LARGE_CONSTANT_FRICTION_NO_SLIP_ZONE_MODEL', r['flags'])

    def test_foil_grid_convergence(self):
        c = self.foil['convergence']
        self.assertLess(c['force_relative_change_on_refinement'], 1e-6)
        self.assertLess(c['slip_absolute_change_on_refinement'], 1e-6)
        self.assertLess(c['mechanical_work_residual_relative'], 1e-8)

    def test_published_high_friction_foil_case_rejected_coulomb_above_shear_yield(self):
        """A 50 -> 25 um pass at a NOMINAL friction of 0.10 is rejected (Coulomb shear above
        shear yield). This is not the published case, where 0.1 acts on asperity contact areas
        only, weighted by the contact-area ratio and capped at shear yield [BT-S3 EX]."""
        for end_zones in (True, False):
            with self.assertRaisesRegex(ValueError, 'shear yield'):
                solve_mattress_bite(*FOIL_MU10, contact_end_zones=end_zones)

    def test_limiting_gauge_rejected(self):
        # 2K/K_p = 2*173 MPa/1e13 = 34.6 um > 25 um exit
        with self.assertRaisesRegex(ValueError, 'limiting thickness'):
            solve_mattress_bite(*FOIL_MU03, foundation_modulus_pa_m=1e13)

    def test_sticking_exit_needed_rejected(self):
        with self.assertRaisesRegex(ValueError, 'sticking exit'):
            solve_mattress_bite(35e-6, 24.5e-6, 1.5, 0.2, 285e6, 0.03, 25e6, 30e6, cells=200)


class TrendTests(unittest.TestCase):

    def test_force_rises_with_friction_and_falls_with_tension(self):
        def force(**changes):
            args = dict(zip(('h0', 'h1', 'w', 'r', 'y', 'mu', 'tb', 'tf'), SHEET))
            args.update(changes)
            return solve_mattress_bite(*args.values(), cells=128)['separating_force_n']
        base = force()
        self.assertLess(force(mu=0.03), base)
        self.assertGreater(force(mu=0.07), base)
        self.assertLess(force(tb=50e6), base)
        self.assertLess(force(tf=60e6), base)
        self.assertGreater(force(h1=0.39e-3), base)


class DerivedResponseTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sheet = derive_bite_response_mattress(BitePass(*SHEET), cells=200)
        cls.hitchcock = derive_bite_response(BitePass(*SHEET), cells=128)
        cls.foil = derive_bite_response_mattress(BitePass(*FOIL_MU03), cells=200)

    def test_response_contract(self):
        for b in (self.sheet, self.foil):
            self.assertIsInstance(b, BiteResponse)
            b.validate()
            self.assertEqual(b.source, 'supplied')
            self.assertIn('DERIVED_BY_EXPERIMENTAL_MATTRESS_MODEL', b.flags)
            self.assertIn('EXPERIMENTAL_MATTRESS_FOIL_MODEL', b.flags)
            self.assertNotIn('SENSITIVITY_STEP_NOT_CONVERGED', b.flags)
            self.assertNotIn('GRID_REFINEMENT_NOT_MET', b.flags)
            self.assertGreaterEqual(b.contact_radius_ratio, 1.0)
            json.dumps(b.to_dict(), allow_nan=False)
        self.assertIn('MATTRESS_REGIME_FOIL', self.foil.flags)
        nominal = solve_mattress_bite(*SHEET, cells=200)
        self.assertAlmostEqual(self.sheet.separating_force_n, nominal['separating_force_n'],
                               delta=1e-9 * nominal['separating_force_n'])
        self.assertAlmostEqual(self.sheet.contact_radius_ratio, nominal['contact_radius_ratio'],
                               delta=1e-12)

    def test_sensitivity_signs_match_hitchcock(self):
        names = ('dforce_dexit_thickness_n_m', 'dforce_dentry_thickness_n_m',
                 'dforce_dentry_tension_m2', 'dforce_dexit_tension_m2',
                 'dslip_dexit_thickness_per_m', 'dslip_dentry_thickness_per_m',
                 'dslip_dentry_tension_per_pa', 'dslip_dexit_tension_per_pa')
        for name in names:
            a, b = getattr(self.sheet, name), getattr(self.hitchcock, name)
            self.assertEqual(math.copysign(1, a), math.copysign(1, b), name)
            self.assertTrue(0.2 < a / b < 5, name)            # same order only
        self.assertLess(self.foil.dforce_dexit_thickness_n_m, 0)
        self.assertLess(self.foil.dforce_dentry_tension_m2, 0)

    def test_runs_through_chatter_critical_speed(self):
        stand = StandModel.from_modal_damping(3000.0, 22000.0, 4e10, 1.4e10, 0.03)
        spans = StripSpans(70e9, 4.0, 4.0)
        r = critical_speed(stand, self.sheet, spans, bite_damping_transit_fraction=0.0)
        self.assertEqual(r['status'], 'UNSTABLE_ABOVE_CRITICAL_SPEED')
        self.assertTrue(1.0 < r['critical_exit_speed_m_s'] < 60.0)
        self.assertIn('DERIVED_BY_EXPERIMENTAL_MATTRESS_MODEL', r['flags'])
        json.dumps(r, allow_nan=False)


class ExtendedDomainTests(unittest.TestCase):
    """SPEC12 stage A: the mattress model below 20 um exit gauge (floor 8 um) and above 50 %
    reduction (to 65 %): converged, continuous, flagged; its own physical rejections stay."""
    FOIL = dict(width_m=1.2, work_roll_radius_m=0.135, mean_flow_stress_pa=180e6,
                friction_coefficient=0.03, entry_tension_pa=38e6, exit_tension_pa=42e6)

    def solve(self, h0, h1, cells=128):
        f = self.FOIL
        return solve_mattress_bite(h0, h1, f['width_m'], f['work_roll_radius_m'],
                                   f['mean_flow_stress_pa'], f['friction_coefficient'],
                                   f['entry_tension_pa'], f['exit_tension_pa'], cells=cells)

    def test_continuity_across_20_um(self):
        exits = (22e-6, 21e-6, 20e-6, 19e-6, 18e-6)
        res = [self.solve(h1 / 0.6, h1) for h1 in exits]       # fixed 40 % reduction
        forces = [r['force_per_width_n_m'] for r in res]
        steps = [b - a for a, b in zip(forces, forces[1:])]
        self.assertTrue(all(s > 0 for s in steps))              # force rises as gauge falls
        # no jump at 20 um: neighbouring increments within a factor 2 of each other
        for a, b in zip(steps, steps[1:]):
            self.assertLess(max(a, b) / min(a, b), 2.0)
        for h1, r in zip(exits, res):
            self.assertEqual(r['regime'], 'foil')
            below = 'EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN' in r['flags']
            self.assertEqual(below, h1 < 20e-6 - 1e-12, h1)
            self.assertEqual(any('Exit gauge below 20 um' in x for x in r['limitations']), below)

    def test_final_passes_below_20_um(self):
        r = self.solve(30e-6, 18e-6)
        self.assertLess(r['convergence']['force_relative_change_on_refinement'], 1e-3)
        self.assertIn('EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN', r['flags'])
        b = derive_bite_response_mattress(BitePass(30e-6, 18e-6, 1.2, 0.135, 180e6, 0.03, 38e6,
                                                   42e6), cells=128)
        self.assertIn('EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN', b.flags)
        r12 = self.solve(25e-6, 12e-6)                          # 52 %: both extensions
        self.assertIn('REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN', r12['flags'])
        # the model's own physical rejection still applies (sticking exit not modelled)
        with self.assertRaisesRegex(ValueError, 'sticking exit'):
            self.solve(15e-6, 9e-6)
        with self.assertRaisesRegex(ValueError, 'exit'):
            self.solve(10e-6, 7e-6)                             # below the 8 um floor

    def test_continuity_across_50_percent(self):
        sheet = (1.5, 0.2, 250e6, 0.05, 25e6, 30e6)
        forces = [solve_mattress_bite(0.6e-3, 0.6e-3 * (1 - r), *sheet, cells=128)[
            'force_per_width_n_m'] for r in (0.48, 0.50, 0.52)]
        self.assertLess(forces[0], forces[1])
        self.assertLess(forces[1], forces[2])
        self.assertLess(abs(forces[2] - 2 * forces[1] + forces[0]),
                        0.1 * (forces[2] - forces[0]))


class ValidationAndJsonTests(unittest.TestCase):

    def test_invalid_inputs_raise(self):
        bad = [
            dict(index=0, value=True), dict(index=0, value=float('nan')),
            dict(index=1, value=0.7e-3), dict(index=1, value=1e-5), dict(index=5, value=0.31),
            dict(index=5, value=0.0), dict(index=6, value=-1.0), dict(index=7, value=250e6),
            dict(index=3, value=0.005), dict(index=2, value=0.005),
        ]
        for case in bad:
            args = list(SHEET)
            args[case['index']] = case['value']
            with self.assertRaises(ValueError, msg=str(case)):
                solve_mattress_bite(*args, cells=64)
        for kwargs in (dict(cells=32), dict(cells=True), dict(cells=100.0),
                       dict(foundation_modulus_pa_m=-1.0), dict(foundation_modulus_pa_m=True),
                       dict(roll_poisson_ratio=0.5), dict(roll_youngs_modulus_pa=1e8),
                       dict(contact_end_zones=1)):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                solve_mattress_bite(*SHEET, **kwargs)
        with self.assertRaises(ValueError):
            derive_bite_response_mattress(SHEET)
        with self.assertRaises(ValueError):
            derive_bite_response_mattress(BitePass(*SHEET), cells=10)

    def test_result_is_json_and_honest(self):
        r = solve_mattress_bite(*THIN, cells=128)
        text = json.dumps(r, allow_nan=False)
        self.assertEqual(r['status'], STATUS)
        self.assertIn('UNVALIDATED', r['status'])
        self.assertTrue(r['limitations'] and r['basis'])
        self.assertTrue(all(isinstance(f, str) and f.upper() == f for f in r['flags']))
        self.assertNotIn('NaN', text)
        self.assertEqual(len(r['profile']['x_m']), len(r['profile']['pressure_pa']))
        self.assertEqual(r['profile']['x_m'], sorted(r['profile']['x_m']))


if __name__ == '__main__':
    unittest.main()
