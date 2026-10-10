"""Independent standing-wave and two-sided reel ledger references for T2A9."""

import math
import unittest
from unittest.mock import patch

from physicroll import transient_t2a9 as reversal
from physicroll import transient_t2a7 as winding


MU, EA, C = .1, 10.0, 10.0
LAM, DELTA, K, S0 = 1.01, .001, math.pi / 2, .9894996247259713887694
RC, KAPPA, JCORE = .1, .001 / math.pi, .01


def exact(time, position):
    phase = C * K * (time - .02)
    lo, hi = 0.0, 1.1
    for _ in range(55):
        mid = (lo + hi) / 2
        mapped = LAM * mid + DELTA / K * math.sin(K * mid) * math.cos(phase)
        if mapped < position:
            lo = mid
        else:
            hi = mid
    label = (lo + hi) / 2
    stretch = LAM + DELTA * math.cos(K * label) * math.cos(phase)
    speed = -DELTA * C * math.sin(K * label) * math.sin(phase)
    return label, stretch, speed


def exact_reel(time):
    label, stretch, speed = exact(time, 1)
    phase = C * K * (time - .02)
    q = speed / stretch
    length = 1 + S0 - label
    radius = math.sqrt(RC ** 2 + KAPPA * length)
    inertia = JCORE + MU * (RC ** 2 * length + KAPPA * length ** 2 / 2)
    velocity_t = -DELTA * C * C * K * math.sin(K * label) * math.cos(phase)
    velocity_s = -DELTA * C * K * math.cos(K * label) * math.sin(phase)
    speed_rate = velocity_t - q * velocity_s
    radius_rate = KAPPA * q / (2 * radius)
    alpha = speed_rate / radius - speed * radius_rate / radius ** 2
    tension = EA * (stretch - 1)
    torque = inertia * alpha + radius * tension
    return label, stretch, speed, q, length, speed / radius, torque, tension, radius


def exact_integrals(start, stop):
    count = 512
    h = (stop - start) / count
    total = [0.] * 7
    for i in range(count + 1):
        _, stretch, speed, q, _, omega, torque, tension, radius = exact_reel(
            start + i * h)
        values = (torque * omega, q * MU * speed ** 2 / 2,
                  q * EA * (stretch - 1) ** 2 / 2, tension * speed,
                  omega, torque, MU * q * radius * speed)
        weight = 1 if i in (0, count) else 4 if i % 2 else 2
        for j in range(7):
            total[j] += weight * values[j]
    return [value * h / 3 for value in total]


def field_error(sample):
    count = len(sample['cell_conservative_fields'])
    stretch_error = speed_error = 0.
    for i, (a, p) in enumerate(sample['cell_conservative_fields']):
        _, stretch, speed = exact(sample['time_s'], (i + .5) / count)
        stretch_error += ((1 / a - stretch) / DELTA) ** 2
        speed_error += ((p / (MU * a) - speed) / (C * DELTA)) ** 2
    return math.sqrt(stretch_error / count), math.sqrt(speed_error / count)


def independently_owned_energy(sample):
    total = 0.0
    for item in sample['active_deposited_intervals']:
        low = item['active_label_low_m']
        high = item['material_label_high_m']
        h = (high - low) / 32
        for i in range(33):
            label = low + i * h
            k = item['profile_k_per_m']
            lam = item['profile_lambda0']
            stretch = (lam + k * (item['profile_span_length_m'] - lam * label) *
                       math.cos(k * label) / math.sin(k * label) +
                       item['profile_offset'])
            weight = 1 if i in (0, 32) else 4 if i % 2 else 2
            total += weight * EA * (stretch - 1) ** 2 * h / 6
    return total


class T2A9Tests(unittest.TestCase):
    def test_reference_landmarks_and_integral(self):
        self.assertAlmostEqual(exact_reel(.02)[0],
                               .9894687795361282210577, delta=2e-15)
        self.assertAlmostEqual(exact_reel(.02)[4],
                               1.000030845189843168, delta=2e-15)
        self.assertAlmostEqual(exact_reel(.02)[6],
                               -.006857761152179466757, delta=1e-13)
        expected = (-1.975564009452073484e-6, 7.423185831184365109e-12,
                    1.547233710226713621e-8, 3.120433871294104210e-6,
                    3.066982961368447013e-4, -1.315853104706966185e-4,
                    6.486187963675360678e-10)
        for observed, reference in zip(exact_integrals(0, .02), expected):
            self.assertAlmostEqual(observed, reference,
                                   delta=max(abs(reference) * 1e-9, 1e-15))

    def test_reversal_return_fields_donors_ledgers_and_refinement(self):
        errors = []
        for count in (64, 128, 256):
            with self.subTest(cells=count):
                result = reversal.run_matched_reaction_reversal(
                    reversal.T2A9Case(count))
                self.assertEqual(result['episode_outcome'],
                                 'RETURNED_TO_OLD_LAYER_WITHOUT_CONSUMING_IT')
                self.assertEqual(result['reel_torque_role'],
                                 'reaction_not_applied_input')
                self.assertLessEqual(result['maximum_reconstructed_stage_courant'],
                                     .35 * (1 + 1e-12))
                self.assertGreater(result['minimum_used_stretch'], 1.008)
                self.assertLess(result['maximum_mass_balance_defect_kg'], 1e-11)
                self.assertLess(result['maximum_momentum_balance_defect_kg_m_s'], 1e-11)
                self.assertLess(result['maximum_combined_inventory_defect_kg'], 1e-11)
                self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'], 1e-8)
                self.assertLess(result['maximum_reel_cumulative_energy_defect_j'], 1e-8)
                self.assertLess(result['maximum_combined_energy_defect_j'], 1e-8)
                self.assertLess(result['maximum_exact_storage_vs_transfer_flux_defect_j'],
                                1e-10)
                self.assertLess(result['maximum_new_strain_ownership_defect_j'], 1e-14)
                event, returned = result['events']
                self.assertEqual(event['event_type'], 'FIRST_SPEED_REVERSAL')
                self.assertEqual(returned['event_type'], 'RETURN_TO_OLD_LAYER')
                for item in (event, returned):
                    self.assertLessEqual(item['bracket_time_s'][1] -
                                         item['bracket_time_s'][0], 1e-9)
                    self.assertLess(abs(item['time_s'] -
                                        (.02 if item is event else .04)), 1e-4)
                self.assertGreater(event['lower_endpoint_value'], 0)
                self.assertLessEqual(event['upper_endpoint_value'], 0)
                self.assertLess(abs(event['right_reference_flux_m_s']), 2e-10)
                self.assertLess(returned['lower_endpoint_value'], 0)
                self.assertGreaterEqual(returned['upper_endpoint_value'], 0)
                self.assertLess(abs(returned['right_material_label_m'] - S0), 1e-11)
                samples = result['snapshots']
                self.assertEqual(len(samples), 5)
                self.assertEqual([sample['mode'] for sample in samples],
                                 ['wind', 'wind', 'release', 'release', 'release'])
                self.assertEqual([sample['right_donor_role'] for sample in samples],
                                 ['programmed_incoming_stretch'] * 2 +
                                 ['exposed_stored_interval'] * 3)
                self.assertEqual(samples[0]['time_s'], 0)
                self.assertEqual(samples[1]['time_s'], .01)
                self.assertEqual(samples[3]['time_s'], .03)
                self.assertEqual(samples[4]['time_s'], returned['time_s'])
                self.assertEqual(samples[0]['deposited_intervals'], [])
                self.assertGreater(len(samples[2]['deposited_intervals']), 0)
                self.assertEqual(samples[2]['deposited_intervals'][:len(
                    samples[1]['deposited_intervals'])],
                    samples[1]['deposited_intervals'])
                self.assertEqual(samples[2]['deposited_intervals'],
                                 samples[3]['deposited_intervals'])
                self.assertEqual(samples[2]['deposited_intervals'],
                                 samples[4]['deposited_intervals'])
                old_record = samples[0]['old_wound_interval']
                for sample in samples:
                    self.assertEqual(sample['old_wound_interval'], old_record)
                    self.assertEqual(sample['integrated_left_flux'][0], 0.0)
                    self.assertEqual(sample['integrated_left_flux'][2], 0.0)
                    records = sample['deposited_intervals']
                    if records:
                        self.assertAlmostEqual(records[0]['material_label_high_m'],
                                               S0, delta=1e-12)
                    for previous, current in zip(records, records[1:]):
                        self.assertAlmostEqual(
                            previous['material_label_low_m'],
                            current['material_label_high_m'], delta=1e-12)
                    active_length = sum(
                        item['material_label_high_m'] - item['active_label_low_m']
                        for item in sample['active_deposited_intervals'])
                    self.assertAlmostEqual(active_length,
                                           sample['reel_reference_length_m'] - 1,
                                           delta=1e-11)
                    self.assertLess(abs(sample['newly_wound_strain_energy_j'] -
                                        sample['owned_new_strain_energy_j']), 1e-14)
                    self.assertLess(abs(sample['owned_new_strain_energy_j'] -
                                        independently_owned_energy(sample)), 1e-14)
                    label, stretch, speed, q, length, omega, torque, _, _ = exact_reel(
                        sample['time_s'])
                    self.assertLess(abs(sample['right_material_label_m'] - label), 1e-7)
                    self.assertLess(abs(sample['reel_reference_length_m'] - length), 1e-7)
                    self.assertLess(abs(sample['reel_angular_speed_rad_s'] - omega), 1e-4)
                    self.assertLess(abs(sample['reaction_torque_nm'] - torque), 1e-4)
                    self.assertLess(abs(sample['right_stretch'] - stretch), 1e-5)
                    self.assertLess(abs(sample['right_reference_flux_m_s'] - q), 1e-4)
                    self.assertLess(max(field_error(sample)), .01)
                self.assertLess(abs(samples[2]['newly_wound_strain_energy_j'] -
                                    1.547233710226713621e-8), 1e-10)
                self.assertLess(abs(samples[-1]['newly_wound_strain_energy_j']), 1e-14)
                for left, right in ((samples[0], samples[2]),
                                    (samples[2], samples[-1])):
                    expected = exact_integrals(left['time_s'], right['time_s'])
                    observed = (
                        right['integrated_drive_work_j'] - left['integrated_drive_work_j'],
                        *(right['integrated_right_energy_terms'][i] -
                          left['integrated_right_energy_terms'][i] for i in range(3)),
                        right['reel_angle_rad'] - left['reel_angle_rad'],
                        right['integrated_reaction_torque_nm_s'] -
                        left['integrated_reaction_torque_nm_s'],
                        right['integrated_advected_angular_flux_nm_s'] -
                        left['integrated_advected_angular_flux_nm_s'])
                    for actual, reference, tol in zip(
                            observed, expected,
                            (2e-8, 1e-13, 1e-10, 3e-8, 3e-6, 1e-6, 1e-11)):
                        self.assertLess(abs(actual - reference), tol)
                    phase_sign = 1 if left is samples[0] else -1
                    for actual in observed[:5]:
                        self.assertNotEqual(actual, 0.0)
                    self.assertLess(phase_sign * observed[0], 0)
                    self.assertGreater(phase_sign * observed[1], 0)
                    self.assertGreater(phase_sign * observed[2], 0)
                    self.assertGreater(phase_sign * observed[3], 0)
                    self.assertGreater(phase_sign * observed[4], 0)
                    self.assertLess(observed[5], 0)
                    self.assertGreater(observed[6], 0)
                errors.append((max(field_error(samples[3])),
                               abs(event['time_s'] - .02),
                               abs(returned['time_s'] - .04),
                               result['maximum_combined_energy_defect_j']))
        for metric in range(4):
            self.assertLess(errors[1][metric], errors[0][metric])
            self.assertLess(errors[2][metric], errors[1][metric])

    def test_release_uses_mutated_saved_interval(self):
        result = reversal.run_matched_reaction_reversal(reversal.T2A9Case(64))
        sample = result['snapshots'][2]
        cells = [tuple(item) for item in sample['cell_conservative_fields']]
        records = [dict(item) for item in sample['deposited_intervals']]
        baseline = reversal._rates(cells, sample['reel_reference_length_m'],
                                   sample['time_s'], 1 / 64, 'release', records)
        old = dict(sample['old_wound_interval'])
        records[-1]['profile_offset'] += 1e-5
        changed = reversal._rates(cells, sample['reel_reference_length_m'],
                                  sample['time_s'], 1 / 64, 'release', records)
        self.assertEqual(sample['old_wound_interval'], old)
        self.assertAlmostEqual(changed['port']['right_stretch'] -
                               baseline['port']['right_stretch'], 1e-5, delta=1e-12)
        for name in ('right_speed_m_s', 'omega_rad_s'):
            self.assertNotEqual(changed['port'][name], baseline['port'][name])
        self.assertNotEqual(changed['reaction_torque_nm'], baseline['reaction_torque_nm'])
        self.assertGreater(reversal._active_energy(sample['right_material_label_m'],
                                                   records),
                           sample['owned_new_strain_energy_j'])
        records[-1]['profile_k_per_m'] *= 1.0001
        changed_derivative = reversal._rates(
            cells, sample['reel_reference_length_m'], sample['time_s'],
            1 / 64, 'release', records)
        self.assertNotEqual(
            changed_derivative['port']['right_stretch_derivative_per_label'],
            baseline['port']['right_stretch_derivative_per_label'])

    def test_reaction_inertia_changes_torque_only(self):
        baseline = reversal.run_matched_reaction_reversal(reversal.T2A9Case(64))
        original_geometry = winding._geometry
        with patch.object(winding, '_geometry', side_effect=lambda length: (
                original_geometry(length)[0], 1.25 * original_geometry(length)[1])):
            changed = reversal.run_matched_reaction_reversal(reversal.T2A9Case(64))
        for ordinary, heavier in zip(baseline['snapshots'], changed['snapshots']):
            self.assertEqual(ordinary['time_s'], heavier['time_s'])
            self.assertEqual(ordinary['cell_conservative_fields'],
                             heavier['cell_conservative_fields'])
            self.assertEqual(ordinary['reel_reference_length_m'],
                             heavier['reel_reference_length_m'])
            self.assertEqual(ordinary['reel_angular_speed_rad_s'],
                             heavier['reel_angular_speed_rad_s'])
        self.assertNotEqual(baseline['snapshots'][2]['reaction_torque_nm'],
                            changed['snapshots'][2]['reaction_torque_nm'])

    def test_fixed_grid_temporal_refinement_and_case_domain(self):
        results = [reversal.run_matched_reaction_reversal(reversal.T2A9Case(128, cfl))
                   for cfl in (.35, .175, .0875)]
        fields = [item['snapshots'][3]['cell_conservative_fields'] for item in results]
        def distance(first, second):
            return math.sqrt(sum(
                ((1 / a - 1 / b) / DELTA) ** 2 +
                ((p / (MU * a) - r / (MU * b)) / (C * DELTA)) ** 2
                for (a, p), (b, r) in zip(first, second)) / (2 * len(first)))
        self.assertLess(distance(fields[1], fields[2]),
                        distance(fields[0], fields[1]))
        for count in (True, 0, 63, 512, 64.0):
            with self.assertRaises(ValueError):
                reversal.T2A9Case(count)
        for cfl in (0, -.35, .9, float('nan'), True):
            with self.assertRaises(ValueError):
                reversal.T2A9Case(64, cfl)
        with self.assertRaises(ValueError):
            reversal.run_matched_reaction_reversal(None)


if __name__ == '__main__':
    unittest.main()
