"""Independent exact-wave and discrete-balance tests for T2A7 coupling."""

import math
import unittest
from unittest.mock import patch

from physicroll import transient_t2a7 as coupled


MU = 0.1
EA = 10.0
C = 10.0
L0 = 1.001
V = 0.1
D = 1e-4
K = 5 * math.pi
B = V + C * L0
RC = 0.1
KAPPA = .001 / math.pi
JCORE = .01


def exact_at(position, time):
    low, high = (position - V * time) / L0 - .001, (position - V * time) / L0 + .001
    for _ in range(55):
        label = (low + high) / 2
        location = L0 * label + V * time + D / K * math.sin(K * (label - C * time))
        if location < position:
            low = label
        else:
            high = label
    label = (low + high) / 2
    stretch = L0 + D * math.cos(K * (label - C * time))
    speed = V - C * D * math.cos(K * (label - C * time))
    return label, stretch, speed


def exact_cell_average(index, cells, time):
    dx = 1 / cells
    total = [0.0, 0.0]
    for node, weight in ((-0.8611363115940526, 0.3478548451374538),
                         (-0.3399810435848563, 0.6521451548625461),
                         (0.3399810435848563, 0.6521451548625461),
                         (0.8611363115940526, 0.3478548451374538)):
        _, stretch, speed = exact_at((index + .5 + node / 2) * dx, time)
        total[0] += weight / (2 * stretch)
        total[1] += weight * MU * speed / (2 * stretch)
    return total


def exact_reel(time):
    initial_label, _, _ = exact_at(1.0, 0.0)
    current_label, stretch, speed = exact_at(1.0, time)
    length = 1 + initial_label - current_label
    radius = math.sqrt(RC ** 2 + KAPPA * length)
    inertia = JCORE + MU * (RC ** 2 * length + KAPPA * length ** 2 / 2)
    return length, speed / radius, radius, inertia, stretch


class T2A7Tests(unittest.TestCase):
    def test_applied_torque_is_independent_exact_time_history(self):
        # These high-precision independent anchors are not computed from the
        # span/reel trajectory that receives this torque.
        self.assertAlmostEqual(coupled._manufactured_applied_torque(.005),
                               -.01152216308688960483, delta=2e-13)
        self.assertAlmostEqual(coupled._manufactured_applied_torque(.08),
                               -.001525501403045902016, delta=2e-13)

    def test_two_way_fields_inventory_and_fluxes_refine(self):
        errors = []
        for cells in (64, 128, 256):
            with self.subTest(cells=cells):
                result = coupled.run_torque_driven_elastic_coupling(
                    coupled.T2A7Case(cells))
                self.assertEqual(result['reel_speed_role'],
                                 'predicted_from_torque_and_span_tension')
                self.assertEqual(result['right_incoming_characteristic_role'],
                                 'predicted_from_reel_speed')
                self.assertLess(result['accepted_steps'], 4000)
                self.assertLessEqual(result['maximum_reconstructed_stage_courant'],
                                     .35 * (1 + 1e-12))
                self.assertLess(result['maximum_mass_balance_defect_kg'], 1e-12)
                self.assertLess(result['maximum_momentum_balance_defect_kg_m_s'], 1e-12)
                self.assertLess(result['maximum_combined_inventory_defect_kg'], 1e-12)
                self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'], 1e-11)
                self.assertEqual([item['time_s'] for item in result['snapshots']],
                                 [0.0, .005, .04, .08])
                previous_intervals = []
                rms_stretch = rms_speed = 0.0
                for sample in result['snapshots']:
                    time = sample['time_s']
                    expected_length, expected_omega, radius, inertia, _ = exact_reel(time)
                    self.assertAlmostEqual(sample['reel_radius_m'],
                                           math.sqrt(RC ** 2 + KAPPA *
                                                     sample['reel_reference_length_m']),
                                           delta=1e-14)
                    self.assertAlmostEqual(sample['reel_inertia_kg_m2'],
                                           JCORE + MU * (RC ** 2 *
                                                         sample['reel_reference_length_m'] +
                                                         KAPPA * sample[
                                                             'reel_reference_length_m'] ** 2 / 2),
                                           delta=1e-14)
                    self.assertAlmostEqual(sample['right_material_label_m'],
                                           exact_at(1.0, 0.0)[0] -
                                           (sample['reel_reference_length_m'] - 1),
                                           delta=1e-12)
                    self.assertAlmostEqual(sample['integrated_right_flux'][0],
                                           sample['reel_reference_length_m'] - 1,
                                           delta=1e-12)
                    self.assertLess(abs(sample['packet_inventory_difference_m']), 1e-12)
                    self.assertLess(abs(sample['packet_outer_label_difference_m']), 1e-12)
                    kinetic, strain, traction = sample['integrated_right_energy_terms']
                    self.assertAlmostEqual(sample['integrated_right_flux'][2],
                                           kinetic + strain - traction, delta=1e-12)
                    intervals = sample['ordered_wound_intervals']
                    self.assertEqual(intervals[:len(previous_intervals)], previous_intervals)
                    previous_intervals = intervals
                    self.assertAlmostEqual(intervals[0]['retained_stretch'],
                                           exact_at(1.0, 0.0)[1], delta=1e-14)
                    self.assertAlmostEqual(intervals[0]['retained_strain_energy_j'],
                                           EA * (exact_at(1.0, 0.0)[1] - 1) ** 2 / 2,
                                           delta=1e-14)
                    if time == .08:
                        self.assertEqual(len(intervals), 1 + 2 * result['accepted_steps'])
                    self.assertAlmostEqual(sum(item['reference_length_m']
                                               for item in intervals),
                                           sample['reel_reference_length_m'], delta=1e-12)
                    self.assertAlmostEqual(sum(item['retained_strain_energy_j']
                                               for item in intervals),
                                           sample['wound_strain_energy_j'], delta=1e-14)
                    self.assertAlmostEqual(sum(item['retained_strain_energy_j']
                                               for item in intervals[1:]),
                                           strain, delta=1e-12)
                    for index, item in enumerate(intervals):
                        self.assertAlmostEqual(item['mass_kg'],
                                               MU * item['reference_length_m'], delta=1e-15)
                        self.assertAlmostEqual(item['retained_strain_energy_j'],
                                               item['reference_length_m'] * EA *
                                               (item['retained_stretch'] - 1) ** 2 / 2,
                                               delta=1e-16)
                        if index:
                            self.assertAlmostEqual(item['material_label_high_m'],
                                                   intervals[index - 1][
                                                       'material_label_low_m'],
                                                   delta=1e-12)
                    if time == .08:
                        self.assertLess(abs(sample['reel_reference_length_m'] -
                                            expected_length), 1e-7)
                        self.assertLess(abs(sample['reel_angular_speed_rad_s'] -
                                            expected_omega), 3e-6)
                        self.assertLess(abs(sample['reel_angle_rad'] -
                                            .07875923966511506), 1e-6)
                    if time == .005 and cells == 256:
                        deposited = (sample['wound_strain_energy_j'] -
                                     intervals[0]['retained_strain_energy_j'])
                        self.assertLess(abs(deposited - 2.090513565636848851e-9) /
                                        2.090513565636848851e-9, .002)
                final = result['snapshots'][-1]
                for index, (a, p) in enumerate(final['cell_conservative_fields']):
                    exact_a, exact_p = exact_cell_average(index, cells, .08)
                    rms_stretch += ((1 / a - 1 / exact_a) / D) ** 2
                    rms_speed += ((p / (MU * a) - exact_p / (MU * exact_a)) /
                                  (C * D)) ** 2
                errors.append((math.sqrt(rms_stretch / cells),
                               math.sqrt(rms_speed / cells),
                               abs(final['reel_reference_length_m'] - exact_reel(.08)[0]),
                               abs(final['reel_angular_speed_rad_s'] - exact_reel(.08)[1]),
                               result['maximum_reel_step_energy_defect_j'],
                               result['maximum_combined_energy_defect_j'],
                               result['maximum_reel_cumulative_energy_defect_j'],
                               abs(final['reel_angle_rad'] - .07875923966511506),
                               abs(final['integrated_drive_work_j'] -
                                   7.756411054313004354e-5),
                               abs(final['integrated_right_energy_terms'][0] -
                                   3.997794662130571640e-6),
                               abs(final['integrated_right_energy_terms'][1] -
                                   4.004669114825430643e-8),
                               abs(final['integrated_right_energy_terms'][2] -
                                   7.988901547002435848e-5),
                               abs(result['initial_right_port_stretch_projection_error'])))
        for column in range(len(errors[0])):
            self.assertLess(errors[1][column], errors[0][column])
            self.assertLess(errors[2][column], errors[1][column])
        self.assertLess(errors[-1][0], .01)
        self.assertLess(errors[-1][1], .01)
        self.assertLess(errors[-1][4], 1e-12)
        self.assertLess(errors[-1][5], 1e-9)
        self.assertLess(errors[-1][6], 1e-10)
        self.assertLess(errors[-1][7], 1e-7)
        self.assertLess(errors[-1][8], 1e-8)
        self.assertLess(errors[-1][9], 1e-9)
        self.assertLess(errors[-1][10], 1e-9)
        self.assertLess(errors[-1][11], 1e-8)
        self.assertLess(errors[-1][12], 3e-7)

    def test_fixed_grid_temporal_refinement(self):
        results = [coupled.run_torque_driven_elastic_coupling(
            coupled.T2A7Case(128, cfl)) for cfl in (.35, .175, .0875)]
        self.assertLess(results[0]['accepted_steps'], results[1]['accepted_steps'])
        self.assertLess(results[1]['accepted_steps'], results[2]['accepted_steps'])

        def difference(first, second):
            total = 0.0
            for (a0, p0), (a1, p1) in zip(
                    first['snapshots'][-1]['cell_conservative_fields'],
                    second['snapshots'][-1]['cell_conservative_fields']):
                total += ((1 / a0 - 1 / a1) / D) ** 2
                total += ((p0 / (MU * a0) - p1 / (MU * a1)) / (C * D)) ** 2
            return math.sqrt(total / 256)

        self.assertLess(difference(results[1], results[2]),
                        difference(results[0], results[1]))

    def test_frozen_torque_perturbation_changes_span_and_reel(self):
        baseline = coupled.run_torque_driven_elastic_coupling(coupled.T2A7Case(64))
        original = coupled._manufactured_applied_torque
        with patch.object(coupled, '_manufactured_applied_torque',
                          side_effect=lambda time: original(time) + 1e-5):
            perturbed = coupled.run_torque_driven_elastic_coupling(coupled.T2A7Case(64))
        first = baseline['snapshots'][-1]
        second = perturbed['snapshots'][-1]
        self.assertGreater(second['reel_angular_speed_rad_s'] -
                           first['reel_angular_speed_rad_s'], 5e-5)
        self.assertGreater(abs(second['cell_conservative_fields'][-1][1] -
                               first['cell_conservative_fields'][-1][1]), 5e-7)

    def test_rejects_outside_bounded_case(self):
        for value in (True, 0, 63, 512, 64.0):
            with self.assertRaises(ValueError):
                coupled.T2A7Case(value)
        for value in (0.9, -0.35, float('nan'), True):
            with self.assertRaises(ValueError):
                coupled.T2A7Case(64, value)
        with self.assertRaises(ValueError):
            coupled.run_torque_driven_elastic_coupling(None)


if __name__ == '__main__':
    unittest.main()
