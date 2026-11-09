"""Independent anchors and control-volume checks for prescribed-flow T2A3."""

from dataclasses import replace
import math
import unittest

from physicroll.transient_t2a3 import T2A3Case, run_prescribed_reel_flux


class T2A3Tests(unittest.TestCase):
    def test_frozen_anchors_mass_ownership_and_per_reel_balances(self):
        anchors = {
            0: (0.11481767660877792, 0.10157908193217634, 0.0, 0.0,
                -0.11479499658008625, 0.10156237126460735),
            1: (0.1146791161127821, 0.10173548582285703,
                0.8714718738690714, 0.9836973425385772,
                -0.1146564924487594, 0.10171869622001303),
            2: (0.11454038799908096, 0.10189164963352833,
                1.7439979740144906, 1.9658847094223544,
                -0.11451782087351982, 0.10187478146045989),
        }
        for step in (0.04, 0.02, 0.01):
            with self.subTest(step=step):
                result = run_prescribed_reel_flux(T2A3Case(step_s=step))
                self.assertEqual(result['mode'], 'constant_prescribed_transport_reaction')
                self.assertEqual(result['shaft_speed_role'],
                                 'prescribed_transport_kinematic_reel_speed')
                self.assertEqual(result['span_tension_role'], 'declared_constant_stretch')
                self.assertEqual(result['episode_outcome'], 'COMPLETED_REQUESTED_DURATION')
                self.assertLessEqual(len(result['states']) - 1, 2000)
                first = result['states'][0]
                for t, (left_radius, right_radius, left_angle, right_angle,
                        left_torque, right_torque) in anchors.items():
                    state = result['states'][round(t / step)]
                    self.assertAlmostEqual(state['time_s'], t, delta=1e-12)
                    self.assertAlmostEqual(state['reels']['left']['radius_m'],
                                           left_radius, delta=1e-12)
                    self.assertAlmostEqual(state['reels']['right']['radius_m'],
                                           right_radius, delta=1e-12)
                    self.assertAlmostEqual(state['reels']['left']['angle_rad'],
                                           left_angle, delta=1e-10)
                    self.assertAlmostEqual(state['reels']['right']['angle_rad'],
                                           right_angle, delta=1e-10)
                    self.assertAlmostEqual(state['reels']['left']['reaction_drive_torque_nm'],
                                           left_torque, delta=1e-9)
                    self.assertAlmostEqual(state['reels']['right']['reaction_drive_torque_nm'],
                                           right_torque, delta=1e-9)
                    self.assertAlmostEqual(state['total_mass_kg'],
                                           first['total_mass_kg'], delta=1e-12)
                    self.assertAlmostEqual(state['span_mass_kg'], 0.1 / 1.001,
                                           delta=1e-12)
                    self.assertAlmostEqual(state['declared_span_tension_n'], 1,
                                           delta=1e-12)
                    self.assertAlmostEqual(state['current_thickness_m'], .001 / 1.001,
                                           delta=1e-12)
                    self.assertAlmostEqual(state['left_material_label_m'],
                                           -0.1 * t / 1.001, delta=1e-12)
                    self.assertAlmostEqual(state['right_material_label_m'],
                                           (1 - 0.1 * t) / 1.001, delta=1e-12)
                    for side, sign in (('left', -1), ('right', 1)):
                        reel = state['reels'][side]
                        self.assertEqual(math.copysign(1, reel['signed_mass_flux_kg_s']),
                                         sign)
                        self.assertAlmostEqual(reel['radius_m'] * reel['speed_rad_s'],
                                               0.1, delta=1e-12)
                final = result['states'][-1]
                for side, expected_length, expected_speed in (
                        ('left', 9.8001998001998, 0.8730544897473402),
                        ('right', 1.1998001998002, 0.9814346942037745)):
                    reel = final['reels'][side]
                    self.assertAlmostEqual(reel['reference_length_m'],
                                           expected_length, delta=1e-12)
                    self.assertAlmostEqual(reel['speed_rad_s'], expected_speed,
                                           delta=1e-10)
                    self.assertLess(result['maximum_reel_mass_defect_kg'][side], 1e-12)
                    self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'][side],
                                    1e-10)
                    self.assertLess(result['maximum_reel_energy_defect_j'][side], 1e-10)
                self.assertLess(result['maximum_total_energy_defect_j'], 1e-10)
                for t in (1, 2):
                    state = result['states'][round(t / step)]
                    transferred_kg = (first['reels']['left']['wound_mass_kg'] -
                                      state['reels']['left']['wound_mass_kg'])
                    self.assertAlmostEqual(transferred_kg,
                                           0.009990009990009992 * t, delta=1e-12)
                    self.assertAlmostEqual(state['reels']['right']['wound_mass_kg'] -
                                           first['reels']['right']['wound_mass_kg'],
                                           transferred_kg, delta=1e-12)

    def test_flux_term_is_necessary_for_reel_angular_momentum(self):
        states = run_prescribed_reel_flux(T2A3Case(step_s=.01))['states']
        for side in ('left', 'right'):
            before, middle, after = [states[i]['reels'][side] for i in (99, 100, 101)]
            d_omega = (after['speed_rad_s'] - before['speed_rad_s']) / .02
            d_angular_momentum = (after['angular_momentum_kg_m2_s'] -
                                  before['angular_momentum_kg_m2_s']) / .02
            applied = (middle['reaction_drive_torque_nm'] +
                       middle['tension_torque_nm'])
            flux = middle['signed_mass_flux_kg_s'] * middle['radius_m'] * .1
            self.assertAlmostEqual(middle['inertia_kg_m2'] * d_omega,
                                   applied, delta=1e-7)
            self.assertAlmostEqual(d_angular_momentum,
                                   applied + flux, delta=1e-7)
            self.assertGreater(abs(d_angular_momentum - applied), 1e-5)

    def test_invalid_or_exhausted_cases_fail_closed(self):
        baseline = T2A3Case()
        changes = (
            {'transport_speed_m_s': 0},
            {'transport_speed_m_s': -.1},
            {'stretch': 1},
            {'left_initial_reference_length_m': .1},
            {'step_s': .1},
            {'step_s': .0001},
            {'core_radius_m': True},
            {'density_kg_m3': float('nan')},
            {'density_kg_m3': 10**1000},
        )
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    replace(baseline, **change)
        with self.assertRaises(ValueError):
            run_prescribed_reel_flux(None)


if __name__ == '__main__':
    unittest.main()
