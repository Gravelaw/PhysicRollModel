"""Independent energy/quadrature and subsystem checks for inextensible T2A4."""

import math
import unittest

from physicroll.transient_t2a4 import T2A4Case, run_torque_driven_reels


def independent_mass(q):
    """Use the annular area integral, separate from solver inventory algebra."""
    mass = 0.1
    for initial_length, direction in ((10, -1), (1, 1)):
        radius = math.sqrt(0.1 ** 2 + 0.001 * (initial_length + direction * q) / math.pi)
        inertia = 0.01 + 50 * math.pi * (radius ** 4 - 0.1 ** 4)
        mass += inertia / radius ** 2
    return mass


def independent_terminal_time():
    """Composite quadrature of the energy-based t(q) reference."""
    intervals = 8192
    spacing = 0.2 / intervals
    initial_mass = independent_mass(0)
    def integrand(q):
        return math.sqrt(independent_mass(q) / initial_mass) / 0.1
    return spacing / 3 * (
        integrand(0) + integrand(0.2) +
        sum((4 if i % 2 else 2) * integrand(i * spacing)
            for i in range(1, intervals)))


class T2A4Tests(unittest.TestCase):
    def test_energy_oracle_event_and_positive_tension(self):
        oracle_time = independent_terminal_time()
        self.assertAlmostEqual(oracle_time, 2.00023193699641217, delta=1e-12)
        initial_mass = independent_mass(0)
        for step in (0.04, 0.02, 0.01):
            with self.subTest(step=step):
                result = run_torque_driven_reels(T2A4Case(step))
                self.assertEqual(result['mode'], 'torque_driven_inextensible_moving_web')
                self.assertEqual(result['shaft_speed_role'], 'predicted_from_applied_torque')
                self.assertEqual(result['span_tension_role'],
                                 'inextensibility_constraint_reaction')
                self.assertEqual(result['episode_outcome'], 'COMPLETED_TRANSFER_TARGET')
                self.assertLessEqual(len(result['states']) - 1, 2000)
                self.assertLess(result['maximum_speed_oracle_error_m_s'], 1e-10)
                self.assertLess(result['maximum_scaled_total_energy_defect'], 1e-9)
                defects = result['maximum_balance_defects']
                for side in ('left', 'right'):
                    self.assertLess(defects['reel_mass_kg'][side], 1e-12)
                    self.assertLess(defects['reel_angular_impulse_nm_s'][side], 1e-10)
                    self.assertLess(defects['reel_energy_j'][side], 1e-10)
                self.assertLess(defects['span_momentum_n_s'], 1e-10)
                self.assertLess(defects['span_energy_j'], 1e-10)
                initial_total_mass = result['states'][0]['total_mass_kg']
                for state in result['states']:
                    q = state['transferred_reference_length_m']
                    expected_speed = 0.1 * math.sqrt(initial_mass / independent_mass(q))
                    self.assertLess(abs(state['strip_speed_m_s'] - expected_speed), 1e-10)
                    self.assertGreater(state['strip_speed_m_s'], 0)
                    self.assertAlmostEqual(state['total_mass_kg'], initial_total_mass,
                                           delta=1e-12)
                    left, right = state['reels']['left'], state['reels']['right']
                    self.assertGreater(left['constraint_tension_n'], 0)
                    self.assertGreater(right['constraint_tension_n'], 0)
                    self.assertAlmostEqual(right['constraint_tension_n'] -
                                           left['constraint_tension_n'],
                                           0.1 * state['strip_acceleration_m_s2'],
                                           delta=1e-12)
                    self.assertAlmostEqual(
                        left['applied_drive_torque_nm'] * left['speed_rad_s'] +
                        right['applied_drive_torque_nm'] * right['speed_rad_s'],
                        0, delta=1e-12)
                    for side, initial_length in (('left', 10), ('right', 1)):
                        reel = state['reels'][side]
                        initial_radius = math.sqrt(0.01 + .001 *
                                                   initial_length / math.pi)
                        self.assertAlmostEqual(reel['angle_rad'],
                                               2 * q / (reel['radius_m'] + initial_radius),
                                               delta=1e-12)
                        self.assertAlmostEqual(reel['radius_m'] * reel['speed_rad_s'],
                                               state['strip_speed_m_s'], delta=1e-12)
                final = result['states'][-1]
                self.assertLess(abs(final['transferred_reference_length_m'] - .2), 1e-12)
                self.assertLess(abs(final['time_s'] - oracle_time), 1e-8)
                self.assertAlmostEqual(final['effective_mass_kg'],
                                       2.80672012521324316, delta=1e-10)
                self.assertAlmostEqual(final['strip_speed_m_s'],
                                       0.09997699682837918, delta=1e-10)
                self.assertAlmostEqual(final['strip_acceleration_m_s2'],
                                       -0.00001121901573108618, delta=1e-10)
                self.assertAlmostEqual(final['reels']['left']['constraint_tension_n'],
                                       1.00017889011892767, delta=1e-8)
                self.assertAlmostEqual(final['reels']['right']['constraint_tension_n'],
                                       1.00017776821735456, delta=1e-8)

    def test_separate_reel_and_span_ledgers_need_flux(self):
        result = run_torque_driven_reels(T2A4Case(.04))
        states = result['states']
        for side in ('left', 'right'):
            before, middle, after = [states[i]['reels'][side] for i in (24, 25, 26)]
            h = states[26]['time_s'] - states[24]['time_s']
            angular_rate = (after['angular_momentum_kg_m2_s'] -
                            before['angular_momentum_kg_m2_s']) / h
            applied = (middle['applied_drive_torque_nm'] +
                       middle['tension_torque_nm'])
            flux = (middle['signed_mass_flux_kg_s'] * middle['radius_m'] *
                    states[25]['strip_speed_m_s'])
            self.assertAlmostEqual(angular_rate, applied + flux, delta=1e-7)
            self.assertGreater(abs(angular_rate - applied), 1e-5)

    def test_rejects_invalid_budget_or_case(self):
        for value in (True, 0, -0.01, .1, .0001, float('nan'),
                      float('inf'), 10**1000):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    T2A4Case(value)
        with self.assertRaises(ValueError):
            run_torque_driven_reels(None)


if __name__ == '__main__':
    unittest.main()
