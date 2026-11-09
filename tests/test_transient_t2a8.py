"""Independent affine release, retained-history and first-hit references."""

import math
import unittest
from unittest.mock import patch

from physicroll import transient_t2a8 as release


MU = .1
EA = 10.0
L0 = 1.001
BETA = .02
V = -.1
D = BETA - V * L0
RC = .1
KAPPA = .001 / math.pi
JCORE = .01
S0 = 1 / L0
SSTAR = 1.005


def exact_state(time, position=1.0):
    stretch = L0 - BETA * time
    label = (position - V * time) / stretch
    velocity = (V * L0 - BETA * position) / stretch
    return label, stretch, velocity


def exact_reel(time):
    label, stretch, velocity = exact_state(time)
    length = 1 + S0 - label
    radius = math.sqrt(RC ** 2 + KAPPA * length)
    inertia = JCORE + MU * (RC ** 2 * length + KAPPA * length ** 2 / 2)
    q = velocity / stretch
    radius_rate = KAPPA * q / (2 * radius)
    velocity_rate = -D * BETA / stretch ** 2
    alpha = velocity_rate / radius - velocity * radius_rate / radius ** 2
    tension = EA * (stretch - 1)
    torque = inertia * alpha + radius * tension
    return length, radius, inertia, velocity / radius, torque, q, velocity, tension


def exact_remaining_energy(label):
    """Independent material-label Simpson integral, not the runtime series."""
    if label >= SSTAR:
        return 0.0
    sections = 256
    h = (SSTAR - label) / sections
    total = 0.0
    for index in range(sections + 1):
        material = label + index * h
        stretch = D / (BETA * material - V)
        weight = 1 if index in (0, sections) else 4 if index % 2 else 2
        total += weight * EA * (stretch - 1) ** 2 / 2
    return total * h / 3


def exact_integrals(time):
    sections = 512
    h = time / sections
    totals = [0.0] * 5
    for index in range(sections + 1):
        current = index * h
        _, _, _, omega, torque, q, velocity, tension = exact_reel(current)
        stretch = L0 - BETA * current
        rates = (torque * omega, q * MU * velocity ** 2 / 2,
                 q * EA * (stretch - 1) ** 2 / 2, tension * velocity, omega)
        weight = 1 if index in (0, sections) else 4 if index % 2 else 2
        for j, rate in enumerate(rates):
            totals[j] += weight * rate * h / 3
    return totals


class T2A8Tests(unittest.TestCase):
    def test_exact_retained_energy_and_reaction_anchors(self):
        self.assertAlmostEqual(release._remaining_strain_energy(S0),
                               9.993338828338090600e-9, delta=1e-14)
        self.assertAlmostEqual(exact_remaining_energy(S0),
                               9.993338828338090600e-9, delta=1e-14)
        label, _, _ = exact_state(.025)
        self.assertAlmostEqual(release._remaining_strain_energy(label),
                               1.250103948072823712e-9, delta=1e-14)
        self.assertAlmostEqual(exact_remaining_energy(label),
                               1.250103948072823712e-9, delta=1e-14)
        self.assertAlmostEqual(exact_reel(.025)[4],
                               .0002236162931820224143, delta=1e-12)
        self.assertAlmostEqual(exact_reel(.05)[4],
                               -.0002844874178610664737, delta=1e-12)

    def test_release_fields_history_flux_and_first_event_refine(self):
        errors = []
        for cells in (64, 128, 256):
            with self.subTest(cells=cells):
                result = release.run_reaction_release_first_tension_zero(
                    release.T2A8Case(cells))
                self.assertEqual(result['reel_torque_role'], 'reaction_not_applied_input')
                self.assertEqual(result['episode_outcome'],
                                 'STOPPED_AT_FIRST_TENSION_ZERO')
                self.assertLess(result['accepted_steps'], 4000)
                self.assertLessEqual(result['maximum_reconstructed_stage_courant'],
                                     .35 * (1 + 1e-12))
                self.assertLess(result['maximum_mass_balance_defect_kg'], 1e-11)
                self.assertLess(result['maximum_momentum_balance_defect_kg_m_s'], 1e-11)
                self.assertLess(result['maximum_combined_inventory_defect_kg'], 1e-11)
                self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'], 1e-8)
                self.assertLess(result['maximum_reel_cumulative_energy_defect_j'], 1e-7)
                self.assertLess(result['maximum_combined_energy_defect_j'], 1e-7)
                self.assertLess(result['maximum_exact_storage_vs_transfer_flux_defect_j'],
                                1e-11)
                event = result['event']
                self.assertEqual(event['event_type'], 'FIRST_TENSION_ZERO')
                self.assertLessEqual(event['bracket_time_s'][1] -
                                     event['bracket_time_s'][0], 1e-9)
                self.assertGreaterEqual(event['feasible_minimum_tension_n'], 0)
                self.assertLessEqual(event['feasible_minimum_tension_n'], 1e-9)
                self.assertLessEqual(event['upper_trial_minimum_tension_n'], 0)
                self.assertEqual([sample['time_s'] for sample in result['snapshots'][:-1]],
                                 [0.0, .0125, .025, .0375])
                self.assertEqual(result['snapshots'][-1]['time_s'],
                                 event['feasible_time_s'])
                previous_released = []
                for sample in result['snapshots']:
                    time = sample['time_s']
                    label, stretch, velocity = exact_state(time)
                    length, radius, inertia, omega, torque, q, _, _ = exact_reel(time)
                    self.assertLess(sample['reel_angular_speed_rad_s'], 0)
                    self.assertAlmostEqual(sample['right_material_label_m'],
                                           S0 + 1 - sample['reel_reference_length_m'],
                                           delta=1e-12)
                    self.assertAlmostEqual(sample['integrated_right_flux'][0],
                                           sample['reel_reference_length_m'] - 1,
                                           delta=1e-12)
                    self.assertLess(abs(sample['wound_inventory_difference_m']), 1e-11)
                    self.assertLess(abs(sample['released_outer_label_difference_m']),
                                    1e-11)
                    self.assertAlmostEqual(sample['remaining_wound_strain_energy_j'],
                                           exact_remaining_energy(
                                               sample['right_material_label_m']),
                                           delta=1e-15)
                    self.assertLessEqual(sample['remaining_wound_strain_energy_j'],
                                         result['snapshots'][0][
                                             'remaining_wound_strain_energy_j'])
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
                    core, outer = sample['ordered_wound_intervals']
                    self.assertEqual(core['material_label_low_m'], SSTAR)
                    self.assertEqual(core['retained_strain_energy_j'], 0.0)
                    self.assertAlmostEqual(outer['material_label_low_m'],
                                           sample['right_material_label_m'], delta=1e-12)
                    self.assertAlmostEqual(outer['retained_strain_energy_j'],
                                           sample['remaining_wound_strain_energy_j'],
                                           delta=1e-15)
                    consumed = sample['released_intervals']
                    self.assertEqual(consumed[:len(previous_released)], previous_released)
                    previous_released = consumed
                    self.assertAlmostEqual(sum(item['reference_length_m']
                                               for item in consumed),
                                           1 - sample['reel_reference_length_m'],
                                           delta=1e-11)
                    self.assertAlmostEqual(sum(item['released_strain_energy_j']
                                               for item in consumed),
                                           result['snapshots'][0][
                                               'remaining_wound_strain_energy_j'] -
                                           sample['remaining_wound_strain_energy_j'],
                                           delta=1e-15)
                    for index, item in enumerate(consumed):
                        self.assertAlmostEqual(item['mass_kg'],
                                               MU * item['reference_length_m'], delta=1e-15)
                        if index:
                            self.assertAlmostEqual(item['material_label_low_m'],
                                                   consumed[index - 1][
                                                       'material_label_high_m'],
                                                   delta=1e-12)
                    if time in (.025, .0375):
                        self.assertLess(abs(sample['reel_reference_length_m'] - length),
                                        1e-6)
                        self.assertLess(abs(sample['reel_angular_speed_rad_s'] - omega),
                                        1e-4)
                        self.assertLess(abs(sample['reaction_torque_nm'] - torque), 1e-5)
                    if time == .025:
                        self.assertLess(abs(sample['remaining_wound_strain_energy_j'] -
                                            1.250103948072823712e-9) /
                                        1.250103948072823712e-9, .01)
                    exact_works = exact_integrals(time)
                    observed_works = (sample['integrated_drive_work_j'],
                                      *sample['integrated_right_energy_terms'],
                                      sample['reel_angle_rad'])
                    for calculated, expected, tolerance in zip(
                            observed_works, exact_works,
                            (1e-7, 1e-7, 1e-11, 1e-7, 1e-6)):
                        self.assertLess(abs(calculated - expected), tolerance)
                self.assertLess(result['snapshots'][-1][
                    'integrated_right_energy_terms'][1], 0)
                self.assertGreater(result['snapshots'][-1][
                    'integrated_advected_angular_flux_nm_s'], 0)
                middle = result['snapshots'][3]
                stretch_error = velocity_error = 0.0
                for index, (a, p) in enumerate(middle['cell_conservative_fields']):
                    _, exact_stretch, exact_velocity = exact_state(
                        middle['time_s'], (index + .5) / cells)
                    stretch_error += ((1 / a - exact_stretch) / .001) ** 2
                    velocity_error += ((p / (MU * a) - exact_velocity) / .02) ** 2
                final = result['snapshots'][-1]
                errors.append((math.sqrt(stretch_error / cells),
                               math.sqrt(velocity_error / cells),
                               abs(event['feasible_time_s'] - .05),
                               abs(middle['reel_reference_length_m'] - exact_reel(.0375)[0]),
                               result['maximum_reel_cumulative_energy_defect_j'],
                               result['maximum_combined_energy_defect_j'],
                               result['maximum_exact_storage_vs_transfer_flux_defect_j'],
                               abs(final['integrated_drive_work_j'] -
                                   exact_integrals(final['time_s'])[0])))
        for column in range(len(errors[0])):
            self.assertLess(errors[1][column], errors[0][column])
            self.assertLess(errors[2][column], errors[1][column])
        self.assertLess(errors[-1][0], .01)
        self.assertLess(errors[-1][1], .01)
        self.assertLess(errors[-1][2], 2e-4)

    def test_interior_first_hit_preserves_unreleased_outer_energy(self):
        original = release._exact
        def perturbed_initial(time, position):
            label, stretch, speed = original(time, position)
            if time == 0.0 and 0 < position < 1:
                stretch -= 5e-4
            return label, stretch, speed
        with patch.object(release, '_exact', side_effect=perturbed_initial):
            result = release.run_reaction_release_first_tension_zero(
                release.T2A8Case(64))
        final = result['snapshots'][-1]
        self.assertLess(result['event']['feasible_time_s'], .03)
        self.assertEqual(result['event']['location_type'], 'cell')
        self.assertLessEqual(result['event']['feasible_minimum_tension_n'], 1e-9)
        self.assertGreater(final['remaining_wound_strain_energy_j'], 0)
        self.assertGreater(final['ordered_wound_intervals'][-1][
            'reference_length_m'], 0)
        self.assertLess(final['right_material_label_m'], SSTAR)
        terminal = release._rates(
            [tuple(cell) for cell in final['cell_conservative_fields']],
            final['reel_reference_length_m'], final['time_s'], 1 / 64)
        self.assertAlmostEqual(EA * terminal['minimum_stretch_margin'],
                               result['event']['feasible_minimum_tension_n'],
                               delta=1e-11)

    def test_fixed_grid_temporal_refinement(self):
        results = [release.run_reaction_release_first_tension_zero(
            release.T2A8Case(128, cfl)) for cfl in (.35, .175, .0875)]
        fields = [result['snapshots'][3]['cell_conservative_fields'] for result in results]
        def difference(first, second):
            total = 0.0
            for (a0, p0), (a1, p1) in zip(first, second):
                total += ((1 / a0 - 1 / a1) / .001) ** 2
                total += ((p0 / (MU * a0) - p1 / (MU * a1)) / .02) ** 2
            return math.sqrt(total / 256)
        self.assertLess(difference(fields[1], fields[2]),
                        difference(fields[0], fields[1]))

    def test_rejects_outside_frozen_case(self):
        for count in (True, 0, 63, 512, 64.0):
            with self.assertRaises(ValueError):
                release.T2A8Case(count)
        for cfl in (0, -.35, .9, float('nan'), True):
            with self.assertRaises(ValueError):
                release.T2A8Case(64, cfl)
        with self.assertRaises(ValueError):
            release.run_reaction_release_first_tension_zero(None)


if __name__ == '__main__':
    unittest.main()
