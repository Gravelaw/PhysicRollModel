"""Independent exact-wave comparisons for the moving elastic span."""

import math
import unittest

from physicroll.transient_t2a5 import T2A5Case, run_moving_elastic_span


MASS_PER_REFERENCE_M = 0.1
EA = 10.0
C = 10.0
STRETCH_0 = 1.001
SPEED_0 = 0.1
K = 5 * math.pi
DELTA = 1e-4


def reference_at(position, time, speed0=SPEED_0, delta=DELTA):
    """Newton inversion of the independently declared material map."""
    label = (position - speed0 * time) / STRETCH_0
    for _ in range(8):
        phase = K * (label - C * time)
        location = STRETCH_0 * label + speed0 * time + delta / K * math.sin(phase)
        stretch = STRETCH_0 + delta * math.cos(phase)
        label -= (location - position) / stretch
    return label


def exact_state(position, time, speed0=SPEED_0, delta=DELTA):
    label = reference_at(position, time, speed0, delta)
    stretch_change = delta * math.cos(K * (label - C * time))
    stretch = STRETCH_0 + stretch_change
    speed = speed0 - C * stretch_change
    a = 1 / stretch
    momentum = MASS_PER_REFERENCE_M * a * speed
    energy = momentum * speed / 2 + a * EA * (stretch - 1) ** 2 / 2
    tension = EA * (stretch - 1)
    return a, momentum, energy, (a * speed, momentum * speed - tension,
                                  speed * (energy - tension))


def exact_cell_average(index, cells, time):
    dx = 1 / cells
    left = index * dx
    sections = 12
    h = dx / sections
    values = [0.0, 0.0, 0.0]
    for j in range(sections + 1):
        state = exact_state(left + j * h, time)
        weight = 1 if j in (0, sections) else 4 if j % 2 else 2
        for k in range(3):
            values[k] += weight * state[k] * h / (3 * dx)
    return values


def exact_port_integral(position, time):
    sections = 1000
    h = time / sections
    integrated = [0.0, 0.0, 0.0]
    for j in range(sections + 1):
        rates = exact_state(position, j * h)[3]
        weight = 1 if j in (0, sections) else 4 if j % 2 else 2
        for k in range(3):
            integrated[k] += weight * rates[k] * h / 3
    return integrated


def exact_port_energy_terms(position, time):
    sections = 1000
    h = time / sections
    integrated = [0.0, 0.0, 0.0]
    for j in range(sections + 1):
        a, p, _, _ = exact_state(position, j * h)
        stretch = 1 / a
        speed = p / (MASS_PER_REFERENCE_M * a)
        q = a * speed
        terms = (q * MASS_PER_REFERENCE_M * speed ** 2 / 2,
                 q * EA * (stretch - 1) ** 2 / 2,
                 EA * (stretch - 1) * speed)
        weight = 1 if j in (0, sections) else 4 if j % 2 else 2
        for k in range(3):
            integrated[k] += weight * terms[k] * h / 3
    return integrated


class T2A5Tests(unittest.TestCase):
    def test_distributed_wave_fields_ports_and_balances_refine(self):
        errors = []
        integral_errors = []
        for cells in (64, 128, 256):
            with self.subTest(cells=cells):
                result = run_moving_elastic_span(T2A5Case(cells))
                self.assertEqual(result['mode'],
                                 'distributed_moving_elastic_span_with_characteristic_inputs')
                self.assertEqual(result['shaft_motion_role'], 'not_modeled')
                self.assertLess(result['accepted_steps'], 4000)
                self.assertLess(result['maximum_mass_balance_defect_kg'], 1e-10)
                self.assertLess(result['maximum_momentum_balance_defect_kg_m_s'], 1e-10)
                self.assertLessEqual(result['maximum_reconstructed_stage_courant'],
                                     result['cfl_limit'] * (1 + 1e-12))
                self.assertEqual([sample['time_s'] for sample in result['snapshots']],
                                 [0.0, 0.04, 0.08])
                squared_stretch_error = squared_speed_error = 0.0
                cut_error = 0.0
                inventory_mismatch = 0.0
                global_error = [0.0, 0.0, 0.0]
                for sample in result['snapshots']:
                    time = sample['time_s']
                    self.assertAlmostEqual(sample['right_material_label_m'] -
                                           sample['left_material_label_m'],
                                           sample['span_reference_length_m'], delta=1e-11)
                    cut_error = max(cut_error,
                                    abs(sample['left_material_label_m'] -
                                        reference_at(0.0, time)),
                                    abs(sample['right_material_label_m'] -
                                        reference_at(1.0, time)),
                                    abs(sample['left_characteristic_port_label_m'] -
                                        reference_at(0.0, time)),
                                    abs(sample['right_characteristic_port_label_m'] -
                                        reference_at(1.0, time)))
                    inventory_mismatch = max(
                        inventory_mismatch,
                        abs(sample['characteristic_port_inventory_difference_m']))
                    exact_integrals = [0.0, 0.0, 0.0]
                    for index, (a, p) in enumerate(sample['cell_conservative_fields']):
                        exact_a, exact_p, exact_energy = exact_cell_average(
                            index, cells, time)
                        for component, value in enumerate((exact_a, exact_p, exact_energy)):
                            exact_integrals[component] += value / cells
                        stretch = 1 / a
                        speed = p / (MASS_PER_REFERENCE_M * a)
                        exact_stretch = 1 / exact_a
                        exact_speed = exact_p / (MASS_PER_REFERENCE_M * exact_a)
                        self.assertGreater(stretch, 1)
                        squared_stretch_error += ((stretch - exact_stretch) / DELTA) ** 2
                        squared_speed_error += ((speed - exact_speed) / (C * DELTA)) ** 2
                    observed_integrals = (sample['span_mass_kg'],
                                          sample['span_momentum_kg_m_s'],
                                          sample['span_mechanical_energy_j'])
                    exact_integrals[0] *= MASS_PER_REFERENCE_M
                    for component in range(3):
                        global_error[component] = max(
                            global_error[component],
                            abs(observed_integrals[component] - exact_integrals[component]))
                    if time:
                        for position, key, terms_key in (
                                (0.0, 'integrated_left_physical_flux',
                                 'integrated_left_physical_energy_terms'),
                                (1.0, 'integrated_right_physical_flux',
                                 'integrated_right_physical_energy_terms')):
                            expected = exact_port_integral(position, time)
                            observed = sample[key]
                            for component, tolerance in enumerate((1e-6, 1e-6, 1e-7)):
                                self.assertLess(abs(observed[component] -
                                                    expected[component]), tolerance)
                            kinetic, strain, traction = sample[terms_key]
                            self.assertAlmostEqual(observed[2],
                                                   kinetic + strain - traction,
                                                   delta=1e-12)
                            independent_terms = exact_port_energy_terms(position, time)
                            for computed, independent, tolerance in zip(
                                    (kinetic, strain, traction), independent_terms,
                                    (1e-8, 1e-9, 1e-7)):
                                self.assertLess(abs(computed - independent), tolerance)
                count = cells * len(result['snapshots'])
                errors.append((math.sqrt(squared_stretch_error / count),
                               math.sqrt(squared_speed_error / count), cut_error,
                               result['maximum_scaled_mechanical_energy_defect']))
                integral_errors.append((*global_error, inventory_mismatch))
        for index in range(4):
            self.assertLess(errors[1][index], errors[0][index])
            self.assertLess(errors[2][index], errors[1][index])
            self.assertLess(integral_errors[1][index], integral_errors[0][index])
            self.assertLess(integral_errors[2][index], integral_errors[1][index])
        self.assertLess(errors[-1][0], 0.05)
        self.assertLess(errors[-1][1], 0.05)
        self.assertLess(errors[-1][2], 5e-4)
        self.assertLess(errors[-1][3], 1e-3)
        self.assertLess(integral_errors[-1][0], 1e-8)
        self.assertLess(integral_errors[-1][1], 1e-7)
        self.assertLess(integral_errors[-1][2], 1e-8)
        self.assertLess(integral_errors[-1][3], 5e-4)

    def test_independent_time_refinement(self):
        final_fields = []
        steps = []
        for cfl in (0.35, 0.175, 0.0875):
            result = run_moving_elastic_span(T2A5Case(128, cfl_limit=cfl))
            steps.append(result['accepted_steps'])
            final_fields.append(result['snapshots'][-1]['cell_conservative_fields'])
            self.assertLessEqual(result['maximum_reconstructed_stage_courant'],
                                 cfl * (1 + 1e-12))
        self.assertLess(steps[0], steps[1])
        self.assertLess(steps[1], steps[2])
        def difference(first, second):
            return math.sqrt(sum(
                ((1 / first[i][0] - 1 / second[i][0]) / DELTA) ** 2 +
                ((first[i][1] / (MASS_PER_REFERENCE_M * first[i][0]) -
                  second[i][1] / (MASS_PER_REFERENCE_M * second[i][0])) /
                 (C * DELTA)) ** 2 for i in range(128)) / 256)
        self.assertLess(difference(final_fields[1], final_fields[2]),
                        difference(final_fields[0], final_fields[1]))

    def test_rejects_outside_frozen_grid(self):
        for cells in (True, 0, 63, 512, 64.0):
            with self.subTest(cells=cells):
                with self.assertRaises(ValueError):
                    T2A5Case(cells)
        with self.assertRaises(ValueError):
            run_moving_elastic_span(None)
        with self.assertRaises(ValueError):
            T2A5Case(64, 'unsupported')
        with self.assertRaises(ValueError):
            T2A5Case(64, cfl_limit=0.9)

    def test_zero_mean_transport_still_carries_elastic_wave(self):
        result = run_moving_elastic_span(T2A5Case(128, 'stationary_wave'))
        self.assertEqual([s['time_s'] for s in result['snapshots']],
                         [0.0, 0.01, 0.04, 0.08])
        start, quarter = result['snapshots'][:2]
        self.assertGreater(abs(start['cell_conservative_fields'][0][1] -
                               quarter['cell_conservative_fields'][0][1]), 1e-5)
        for sample in result['snapshots']:
            for index in (0, 17, 55, 127):
                a, p = sample['cell_conservative_fields'][index]
                position = (index + 0.5) / 128
                exact_a, exact_p, _, _ = exact_state(position, sample['time_s'],
                                                      speed0=0.0)
                self.assertGreater(1 / a, 1)
                self.assertLess(abs(1 / a - 1 / exact_a), 2e-5)
                self.assertLess(abs(p / (MASS_PER_REFERENCE_M * a) -
                                    exact_p / (MASS_PER_REFERENCE_M * exact_a)),
                                2e-4)
        self.assertEqual(result['episode_outcome'], 'COMPLETED_SYNTHETIC_WAVE')

    def test_uniform_transport_remains_uniform(self):
        result = run_moving_elastic_span(T2A5Case(64, 'uniform_transport'))
        for sample in result['snapshots']:
            for a, p in sample['cell_conservative_fields']:
                self.assertAlmostEqual(a, 1 / STRETCH_0, delta=1e-12)
                self.assertAlmostEqual(p / (MASS_PER_REFERENCE_M * a),
                                       SPEED_0, delta=1e-12)
            self.assertAlmostEqual(sample['left_material_label_m'],
                                   -SPEED_0 * sample['time_s'] / STRETCH_0,
                                   delta=1e-12)
            self.assertAlmostEqual(sample['right_material_label_m'],
                                   (1 - SPEED_0 * sample['time_s']) / STRETCH_0,
                                   delta=1e-12)


if __name__ == '__main__':
    unittest.main()
