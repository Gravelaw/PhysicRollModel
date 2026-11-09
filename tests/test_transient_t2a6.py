"""Independent material-label and high-precision reel-flux references."""

import math
import unittest

from physicroll.transient_t2a6 import T2A6Case, run_append_only_reaction_reel


K = 5 * math.pi
LAMBDA0 = 1.001
DELTA = 1e-4
V = 0.1
C = 10.0
B = V + C * LAMBDA0
EA = 10.0
MU = 0.1
RC = 0.1
KAPPA = .001 / math.pi
JCORE = .01


def phase_at(time):
    """Bracket the material phase without using the implementation's Newton solver."""
    center = K * (1 - V * time) / LAMBDA0 - K * C * time
    low, high = center - .01, center + .01
    for _ in range(64):
        middle = (low + high) / 2
        value = LAMBDA0 * middle / K + DELTA * math.sin(middle) / K + B * time
        if value < 1:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def label_at_phase(phase):
    time = (1 - LAMBDA0 * phase / K - DELTA * math.sin(phase) / K) / B
    return phase / K + C * time


def deposition_stretch_at_label(label):
    """Invert the material point's crossing of x=1, independent of time grid."""
    low, high = 0.0, 0.08
    for _ in range(62):
        middle = (low + high) / 2
        position = (LAMBDA0 * label + V * middle +
                    DELTA / K * math.sin(K * (label - C * middle)))
        if position < 1:
            low = middle
        else:
            high = middle
    crossing = (low + high) / 2
    return LAMBDA0 + DELTA * math.cos(K * (label - C * crossing))


def energy_primitive(phase):
    e0 = LAMBDA0 - 1
    a0 = V * e0 ** 2
    a1 = 2 * V * e0 * DELTA - C * DELTA * e0 ** 2
    a2 = V * DELTA ** 2 - 2 * C * e0 * DELTA ** 2
    a3 = -C * DELTA ** 3
    return EA / (2 * K * B) * (
        a0 * phase + a1 * math.sin(phase) +
        a2 * (phase / 2 + math.sin(2 * phase) / 4) +
        a3 * (math.sin(phase) - math.sin(phase) ** 3 / 3))


def exact_angle(time):
    left, right = phase_at(time), phase_at(0)
    sections = 4096
    dphi = (right - left) / sections
    initial_label = label_at_phase(right)
    total = 0.0
    for index in range(sections + 1):
        phase = left + dphi * index
        stretch = LAMBDA0 + DELTA * math.cos(phase)
        speed = V - C * DELTA * math.cos(phase)
        wound_length = 1 + initial_label - label_at_phase(phase)
        radius = math.sqrt(RC ** 2 + KAPPA * wound_length)
        weight = 1 if index in (0, sections) else 4 if index % 2 else 2
        total += weight * speed * stretch / (K * B * radius)
    return total * dphi / 3


class T2A6Tests(unittest.TestCase):
    def test_reaction_reel_ownership_and_independent_oracles(self):
        errors = []
        for step in (0.0005, 0.00025, 0.000125):
            with self.subTest(step=step):
                result = run_append_only_reaction_reel(T2A6Case(step))
                self.assertEqual(result['mode'], 'append_only_elastic_port_reaction_reel')
                self.assertEqual(result['shaft_torque_role'], 'reaction_not_applied_input')
                self.assertEqual(result['accepted_steps'], round(.08 / step))
                self.assertEqual([s['time_s'] for s in result['snapshots']],
                                 [0.0, .005, .02, .04, .08])
                self.assertLess(result['maximum_angular_impulse_defect_nm_s'], 1e-10)
                self.assertLess(result['maximum_energy_defect_j'], 1e-10)
                self.assertLess(result['maximum_storage_vs_flux_defect_j'], 1e-11)
                self.assertLess(result['maximum_interval_angular_impulse_defect_nm_s'],
                                1e-10)
                self.assertLess(result['maximum_interval_energy_defect_j'], 1e-10)
                initial_label = label_at_phase(phase_at(0))
                initial_stretch = LAMBDA0 + DELTA * math.cos(phase_at(0))
                previous_intervals = []
                maximum_energy_error = 0.0
                for sample in result['snapshots']:
                    time = sample['time_s']
                    phase = phase_at(time)
                    cut = label_at_phase(phase)
                    length = 1 + initial_label - cut
                    radius = math.sqrt(RC ** 2 + KAPPA * length)
                    inertia = JCORE + MU * (RC ** 2 * length + KAPPA * length ** 2 / 2)
                    stretch = LAMBDA0 + DELTA * math.cos(phase)
                    speed = V - C * DELTA * math.cos(phase)
                    omega = speed / radius
                    speed_rate = -C * DELTA * K * B * math.sin(phase) / stretch
                    radius_rate = KAPPA * speed / stretch / (2 * radius)
                    alpha = speed_rate / radius - speed * radius_rate / radius ** 2
                    torque = inertia * alpha + radius * EA * (stretch - 1)
                    deposited = energy_primitive(phase_at(0)) - energy_primitive(phase)
                    reel = sample['reel']
                    self.assertAlmostEqual(reel['reference_length_m'], length, delta=1e-11)
                    self.assertAlmostEqual(reel['radius_m'], radius, delta=1e-11)
                    self.assertAlmostEqual(reel['inertia_kg_m2'], inertia, delta=1e-12)
                    self.assertAlmostEqual(reel['speed_rad_s'], omega, delta=1e-9)
                    self.assertAlmostEqual(reel['acceleration_rad_s2'], alpha, delta=1e-8)
                    self.assertAlmostEqual(reel['reaction_drive_torque_nm'],
                                           torque, delta=1e-8)
                    self.assertAlmostEqual(sample['angle_rad'], exact_angle(time), delta=1e-9)
                    maximum_energy_error = max(maximum_energy_error,
                                               abs(sample['deposited_strain_energy_j'] -
                                                   deposited))
                    intervals = sample['ordered_wound_intervals']
                    self.assertEqual(intervals[:len(previous_intervals)], previous_intervals)
                    previous_intervals = intervals
                    self.assertEqual(intervals[0]['stretch_at_low_label'], initial_stretch)
                    self.assertAlmostEqual(intervals[0]['retained_strain_energy_j'],
                                           sample['initial_wound_strain_energy_j'],
                                           delta=1e-16)
                    self.assertAlmostEqual(sum(item['reference_length_m']
                                               for item in intervals), length, delta=1e-11)
                    self.assertLess(abs(sample['interval_vs_reel_inventory_difference_m']),
                                    1e-11)
                    self.assertAlmostEqual(sum(item['retained_strain_energy_j']
                                               for item in intervals[1:]),
                                           sample['deposited_strain_energy_j'], delta=1e-16)
                    for index, interval in enumerate(intervals):
                        self.assertAlmostEqual(interval['mass_kg'],
                                               MU * interval['reference_length_m'],
                                               delta=1e-16)
                        if index:
                            self.assertAlmostEqual(interval['material_label_high_m'],
                                                   intervals[index - 1]['material_label_low_m'],
                                                   delta=1e-12)
                            self.assertAlmostEqual(interval['stretch_at_low_label'],
                                                   deposition_stretch_at_label(
                                                       interval['material_label_low_m']),
                                                   delta=1e-12)
                            self.assertAlmostEqual(interval['stretch_at_high_label'],
                                                   deposition_stretch_at_label(
                                                       interval['material_label_high_m']),
                                                   delta=1e-12)
                            self.assertAlmostEqual(interval['stretch_at_high_label'],
                                                   intervals[index - 1]['stretch_at_low_label'],
                                                   delta=1e-12)
                errors.append((maximum_energy_error,
                               result['maximum_angular_impulse_defect_nm_s'],
                               result['maximum_energy_defect_j'],
                               result['maximum_storage_vs_flux_defect_j'],
                               result['maximum_interval_angular_impulse_defect_nm_s'],
                               result['maximum_interval_energy_defect_j']))
                early = result['snapshots'][1]
                self.assertLess(abs(early['deposited_strain_energy_j'] -
                                    2.090513565636848851e-9) /
                                2.090513565636848851e-9, .002)
                false_uniform = (5e-6 * early['integrated_reference_flux_m'])
                self.assertGreater(abs(early['deposited_strain_energy_j'] /
                                       false_uniform - 1), .10)
                final = result['snapshots'][-1]
                self.assertAlmostEqual(final['reel']['reference_length_m'],
                                       1.0079928034941278077, delta=1e-11)
                self.assertAlmostEqual(final['reel']['reaction_drive_torque_nm'],
                                       -.001525501403045902016, delta=1e-8)
                self.assertAlmostEqual(final['deposited_strain_energy_j'],
                                       4.004669114825430643e-8, delta=1e-11)
                for name, oracle in (
                        ('integrated_reaction_drive_work_j', 7.756411054313004354e-5),
                        ('integrated_tension_work_j', 7.988901547002435848e-5),
                        ('integrated_advected_kinetic_energy_j', 3.997794662130571640e-6)):
                    self.assertAlmostEqual(final[name], oracle, delta=1e-8)
        for index in range(6):
            self.assertLess(errors[1][index], errors[0][index])
            self.assertLess(errors[2][index], errors[1][index])
        self.assertLess(errors[-1][0], 1e-11)

    def test_rejects_unsupported_release_or_time_grid(self):
        for step in (True, 0, -0.0005, .001, float('nan'), float('inf')):
            with self.subTest(step=step):
                with self.assertRaises(ValueError):
                    T2A6Case(step)
        for mode in ('release', 'reversal', 'torque_driven'):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    T2A6Case(.0005, mode)
        with self.assertRaises(ValueError):
            run_append_only_reaction_reel(None)


if __name__ == '__main__':
    unittest.main()
