"""Independent analytic references for restricted fixed-geometry T2A1."""

from dataclasses import replace
import math
import unittest

from physicroll.transient_t2a1 import (T2A1Case, run_prescribed_reaction,
                                       run_torque_driven, run_uncoupled_shaft)


def case(step_s=0.01, **changes):
    return replace(T2A1Case(
        duration_s=2.0, step_s=step_s,
        left_radius_m=0.1, right_radius_m=0.1,
        left_inertia_kg_m2=1.0, right_inertia_kg_m2=1.0,
        span_stiffness_n_m=100.0, initial_extension_m=0.01,
    ), **changes)


class T2A1Tests(unittest.TestCase):
    def test_uncoupled_constant_torque_matches_closed_solution_and_work(self):
        result = run_uncoupled_shaft(inertia_kg_m2=1.0, constant_torque_nm=1.0,
                                     duration_s=2.0, step_s=0.01)
        for state in result['states']:
            time = state['time_s']
            self.assertAlmostEqual(state['angle_rad'], time * time / 2, delta=1e-12)
            self.assertAlmostEqual(state['speed_rad_s'], time, delta=1e-12)
        self.assertLess(result['maximum_energy_work_defect_j'], 1e-12)
        self.assertAlmostEqual(result['applied_work_j'], 2.0, delta=1e-12)

    def test_zero_torque_first_loss_matches_independent_harmonic_oracle(self):
        expected = math.pi / (2 * math.sqrt(2))
        errors = []
        for step in (0.04, 0.02, 0.01):
            with self.subTest(step=step):
                result = run_torque_driven(case(step))
                self.assertEqual(result['episode_outcome'], 'TERMINATED_TENSION_LOSS')
                self.assertEqual(result['shaft_speed_role'], 'predicted_from_applied_torque')
                self.assertEqual(len(result['events']), 1)
                self.assertEqual(result['states'][-1]['span_tension_n'], 0.0)
                self.assertTrue(all(state['span_tension_n'] >= 0 for state in result['states']))
                self.assertLess(result['maximum_energy_work_defect_j'], 1e-12)
                errors.append(abs(result['completed_duration_s'] - expected))
        self.assertGreater(errors[0], errors[1])
        self.assertGreater(errors[1], errors[2])
        self.assertLess(errors[-1], 1e-4)

    def test_interior_tension_loss_is_not_hidden_by_positive_step_endpoints(self):
        frequency = math.sqrt(2)
        initial_extension = 0.01 - 0.01001 * math.cos(frequency * 0.07)
        initial_extension_rate = -0.01001 * frequency * math.sin(frequency * 0.07)
        model = case(0.14, duration_s=0.14,
                     initial_extension_m=initial_extension,
                     right_initial_speed_rad_s=initial_extension_rate / 0.1,
                     left_constant_torque_nm=-0.1,
                     right_constant_torque_nm=0.1)
        result = run_torque_driven(model)
        self.assertEqual(result['episode_outcome'], 'TERMINATED_TENSION_LOSS')
        self.assertAlmostEqual(result['completed_duration_s'], 0.0383903911, delta=1e-7)
        self.assertEqual(result['states'][-1]['span_tension_n'], 0.0)
        self.assertLess(abs(result['events'][0]['tension_residual_n']), 1e-9)

    def test_small_positive_equilibrium_is_not_called_loss_and_tangent_stops(self):
        small = 5e-13
        stable = run_torque_driven(case(0.1, duration_s=0.1,
                                        initial_extension_m=small,
                                        left_constant_torque_nm=-0.1 * 100 * small,
                                        right_constant_torque_nm=0.1 * 100 * small))
        self.assertEqual(stable['episode_outcome'], 'COMPLETED_REQUESTED_DURATION')
        self.assertEqual(stable['events'], [])
        self.assertGreater(stable['states'][-1]['span_tension_n'], 0)

        frequency = math.sqrt(2)
        equilibrium = 0.01
        a = -equilibrium * math.cos(frequency * 0.07)
        b = -equilibrium * math.sin(frequency * 0.07)
        tangent = run_torque_driven(case(0.14, duration_s=0.14,
                                         initial_extension_m=equilibrium + a,
                                         right_initial_speed_rad_s=b * frequency / 0.1,
                                         left_constant_torque_nm=-0.1,
                                         right_constant_torque_nm=0.1))
        self.assertEqual(tangent['episode_outcome'], 'TERMINATED_TENSION_LOSS')
        self.assertAlmostEqual(tangent['completed_duration_s'], 0.07, delta=1e-9)

    def test_balanced_two_inertia_frequency_and_signed_work(self):
        errors = []
        for step in (0.04, 0.02, 0.01):
            model = case(step, right_initial_angle_rad=0.1,
                         left_constant_torque_nm=-0.1,
                         right_constant_torque_nm=0.1)
            result = run_torque_driven(model)
            self.assertEqual(result['episode_outcome'], 'COMPLETED_REQUESTED_DURATION')
            self.assertLess(result['maximum_energy_work_defect_j'], 1e-12)
            self.assertEqual(result['completed_duration_s'], 2.0)
            errors.append(math.sqrt(sum((state['span_extension_m'] -
                                         (0.01 + 0.01 * math.cos(math.sqrt(2) *
                                                                 state['time_s']))) ** 2
                                        for state in result['states']) /
                                    len(result['states'])) / 0.01)
            final = result['states'][-1]
            relative_speed = 0.1 * (final['right_speed_rad_s'] - final['left_speed_rad_s'])
            phase = math.atan2(-relative_speed / math.sqrt(2),
                               final['span_extension_m'] - 0.01)
            self.assertLess(abs(phase - 2 * math.sqrt(2)), 1e-3)
        self.assertGreater(errors[0], errors[1])
        self.assertGreater(errors[1], errors[2])
        self.assertLess(errors[-1], 5e-4)

    def test_prescribed_reactions_and_work_refinement(self):
        errors = []
        for step in (0.04, 0.02, 0.01):
            model = case(step, duration_s=1.3)
            result = run_prescribed_reaction(model, 'left_sine')
            self.assertEqual(result['shaft_speed_role'], 'prescribed_input')
            self.assertEqual(result['episode_outcome'], 'COMPLETED_REQUESTED_DURATION')
            for state in result['states']:
                time = state['time_s']
                angle = 0.01 * math.sin(2 * math.pi * time)
                acceleration = -0.01 * (2 * math.pi) ** 2 * math.sin(2 * math.pi * time)
                tension = 100 * (0.01 - 0.1 * angle)
                self.assertAlmostEqual(state['left_reaction_torque_nm'],
                                       acceleration - 0.1 * tension, delta=1e-10)
                self.assertAlmostEqual(state['right_reaction_torque_nm'],
                                       0.1 * tension, delta=1e-10)
            errors.append(abs(result['reaction_work_quadrature_defect_j']))
        self.assertGreater(errors[0], errors[1])
        self.assertGreater(errors[1], errors[2])

    def test_prescribed_first_zero_and_invalid_domain(self):
        result = run_prescribed_reaction(case(), 'right_linear_loss')
        self.assertEqual(result['completed_duration_s'], 0.5)
        self.assertEqual(result['episode_outcome'], 'TERMINATED_TENSION_LOSS')
        self.assertEqual(result['states'][-1]['span_tension_n'], 0.0)
        self.assertEqual(result['events'][0]['time_s'], 0.5)
        shorter = run_prescribed_reaction(case(duration_s=0.25), 'right_linear_loss')
        self.assertEqual(shorter['episode_outcome'], 'COMPLETED_REQUESTED_DURATION')
        self.assertEqual(shorter['events'], [])
        self.assertGreater(shorter['states'][-1]['span_tension_n'], 0)
        with self.assertRaisesRegex(ValueError, 'start with positive'):
            case(left_initial_angle_rad=1.0)
        with self.assertRaisesRegex(ValueError, 'too large'):
            case(step_s=1.0)
        with self.assertRaisesRegex(ValueError, 'permitted'):
            case(left_inertia_kg_m2=True)
        with self.assertRaisesRegex(ValueError, 'may leave'):
            run_prescribed_reaction(case(), 'left_sine', amplitude_rad=0.1)
        with self.assertRaisesRegex(ValueError, 'no independent'):
            run_prescribed_reaction(case(left_constant_torque_nm=1.0), 'left_sine')


if __name__ == '__main__':
    unittest.main()
