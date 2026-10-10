"""Continuum mode and conservation checks for fixed-material T2A2."""

import math
import unittest

from physicroll.transient_t2a2 import (T2A2Case, run_coupled_bar,
                                       FREQUENCY_RAD_S, PERIOD_S)


def continuum_root():
    """Bracket the continuum boundary-value equation, not a FE eigenpair."""
    def boundary_residual(z):
        return (1 - 100 * z * z) * math.sin(z) + 20 * z * math.cos(z)
    low, high = 0.01, 1.0
    for _ in range(70):
        middle = (low + high) / 2
        if boundary_residual(low) * boundary_residual(middle) <= 0:
            high = middle
        else:
            low = middle
    return (low + high) / 2


class T2A2Tests(unittest.TestCase):
    def test_independent_continuum_root_and_three_grid_convergence(self):
        root = continuum_root()
        frequency = 10 * root
        period = 2 * math.pi / frequency
        self.assertAlmostEqual(frequency, FREQUENCY_RAD_S, delta=1e-12)
        self.assertAlmostEqual(period, PERIOD_S, delta=1e-12)
        amplitude = 1e-6
        tension_amplitude = 1000 * amplitude * root * math.hypot(1, 10 * root)
        displacement_errors = []
        tension_errors = []
        phase_errors = []
        for elements, step in ((16, 0.003125), (32, 0.0015625),
                               (64, 0.00078125)):
            with self.subTest(elements=elements):
                result = run_coupled_bar(T2A2Case(elements, step))
                self.assertEqual(result['mode'], 'first_elastic')
                self.assertEqual(result['bar_material_role'], 'fixed_material_no_flux')
                self.assertEqual(result['episode_outcome'], 'COMPLETED_REQUESTED_DURATION')
                self.assertLessEqual(len(result['states']) - 1, 2000)
                self.assertAlmostEqual(result['completed_duration_s'], period, delta=1e-12)
                self.assertLess(result['maximum_energy_defect_j'], 1e-18)
                self.assertLess(result['maximum_interface_work_defect_j'], 1e-12)
                sum_u, sum_t = 0.0, 0.0
                count_u, count_t = 0, 0
                maximum_phase_error = 0.0
                for state in result['states']:
                    t = state['time_s']
                    cosine = math.cos(frequency * t)
                    sine = math.sin(frequency * t)
                    self.assertGreater(min(state['element_tension_n']), 0)
                    for endpoint, index in (('left', 0), ('right', elements)):
                        x = index / elements
                        shape = math.cos(root * x) - 10 * root * math.sin(root * x)
                        self.assertLess(abs(state[f'{endpoint}_angle_rad'] -
                                            amplitude * shape * cosine / 0.1), 3e-8)
                        self.assertLess(abs(state[f'{endpoint}_speed_rad_s'] +
                                            amplitude * shape * frequency * sine / 0.1),
                                        3e-7)
                    for i, actual in enumerate(state['bar_displacement_m']):
                        x = i / elements
                        expected = amplitude * (math.cos(root * x) -
                                                10 * root * math.sin(root * x)) * cosine
                        sum_u += (actual - expected) ** 2
                        count_u += 1
                    for i, actual in enumerate(state['element_tension_n']):
                        x = (i + 0.5) / elements
                        expected = 1 + 1000 * amplitude * (
                            -root * math.sin(root * x) -
                            10 * root * root * math.cos(root * x)) * cosine
                        sum_t += (actual - expected) ** 2
                        count_t += 1
                    measured_phase = math.atan2(
                        -state['bar_velocity_m_s'][0] / (frequency * amplitude),
                        state['bar_displacement_m'][0] / amplitude)
                    difference = measured_phase - frequency * t
                    maximum_phase_error = max(maximum_phase_error,
                                              abs(math.atan2(math.sin(difference),
                                                             math.cos(difference))))
                displacement_errors.append(math.sqrt(sum_u / count_u) / amplitude)
                tension_errors.append(math.sqrt(sum_t / count_t) / tension_amplitude)
                phase_errors.append(maximum_phase_error)
        for errors, target in ((displacement_errors, 3e-3),
                               (tension_errors, 5e-3), (phase_errors, 3e-3)):
            self.assertGreater(errors[0], errors[1])
            self.assertGreater(errors[1], errors[2])
            self.assertLess(errors[-1], target)

    def test_rigid_translation_preserves_zero_strain_and_total_mass(self):
        result = run_coupled_bar(T2A2Case(16, 0.003125, 'rigid_translation'))
        self.assertAlmostEqual(result['combined_mass_kg'], 210, delta=1e-12)
        self.assertLess(result['maximum_energy_defect_j'], 1e-18)
        for state in result['states']:
            for displacement in state['bar_displacement_m']:
                self.assertAlmostEqual(displacement, 1e-6 * state['time_s'],
                                       delta=1e-16)
            for tension in state['element_tension_n']:
                self.assertAlmostEqual(tension, 1, delta=1e-10)
            for speed in state['bar_velocity_m_s']:
                self.assertAlmostEqual(speed, 1e-6, delta=1e-15)
            self.assertAlmostEqual(state['kinetic_energy_j'], 0.5 * 210 * 1e-12,
                                   delta=1e-18)

    def test_rejects_unbounded_and_invalid_benchmark_cases(self):
        for elements, step, mode in ((True, 0.01, 'first_elastic'),
                                     (65, 0.001, 'first_elastic'),
                                     (16, float('nan'), 'first_elastic'),
                                     (16, 0.00001, 'first_elastic'),
                                     (16, 0.01, 'first_elastic'),
                                     (16, 0.003125, 'unsupported')):
            with self.subTest(elements=elements, step=step, mode=mode):
                with self.assertRaises(ValueError):
                    T2A2Case(elements, step, mode)


if __name__ == '__main__':
    unittest.main()
