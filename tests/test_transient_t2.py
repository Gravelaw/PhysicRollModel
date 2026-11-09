"""Independent torque-driven span/reel transfer and reversal references."""

import math
import unittest
from dataclasses import replace

from physicroll import transient_t2 as t2
from physicroll import transient_t2a5 as span
from physicroll import transient_t2a6 as reel
from physicroll import transient_t2a7 as geometry_module


MU, EA, C = .1, 10., 10.
S0 = .9894996247259713887694
LAMBDA0, DELTA, K = 1.01, .001, math.pi / 2


def conserved(stretch, speed):
    return 1 / stretch, MU * speed / stretch


def geometry(length):
    radius = math.sqrt(.1 ** 2 + .001 / math.pi * length)
    inertia = .01 + MU * (.1 ** 2 * length + .001 / math.pi * length ** 2 / 2)
    return radius, inertia


def constant_case(count, duration=.1, donor_stretch=1.01, torque_shift=0.):
    stretch, q = 1.001, -.1
    speed = q * stretch
    wound_speed = -.101
    def torque(time):
        length = 1 + q * time
        radius, inertia = geometry(length)
        radius_rate = (.001 / math.pi) * q / (2 * radius)
        alpha = -wound_speed * radius_rate / radius ** 2
        return (inertia * alpha + radius * EA * (stretch - 1) -
                MU * q * radius * (speed - wound_speed) + torque_shift)
    history = tuple((i * duration / 50, torque(i * duration / 50))
                    for i in range(51))
    return t2.T2Episode(
        count, duration, tuple(conserved(stretch, speed) for _ in range(count)),
        1., 1., wound_speed / geometry(1.)[0],
        (t2.WoundRecord(1., 2., donor_stretch),),
        'incoming_characteristic', ((0., speed - C * stretch),
                                    (duration, speed - C * stretch)),
        history, (duration / 4, duration / 2, 3 * duration / 4),
        1. + .11 * duration, initial_phase='release')


def wave(time, position):
    phase = C * K * (time - .02)
    low, high = 0., 1.1
    for _ in range(55):
        label = (low + high) / 2
        x = LAMBDA0 * label + DELTA / K * math.sin(K * label) * math.cos(phase)
        if x < position:
            low = label
        else:
            high = label
    label = (low + high) / 2
    stretch = LAMBDA0 + DELTA * math.cos(K * label) * math.cos(phase)
    speed = -DELTA * C * math.sin(K * label) * math.sin(phase)
    return label, stretch, speed


def wave_reel(time):
    label, stretch, speed = wave(time, 1.)
    phase = C * K * (time - .02)
    q = speed / stretch
    length = 1 + S0 - label
    radius, inertia = geometry(length)
    speed_t = -DELTA * C ** 2 * K * math.sin(K * label) * math.cos(phase)
    speed_s = -DELTA * C * K * math.cos(K * label) * math.sin(phase)
    speed_rate = speed_t - q * speed_s
    radius_rate = (.001 / math.pi) * q / (2 * radius)
    alpha = speed_rate / radius - speed * radius_rate / radius ** 2
    torque = inertia * alpha + radius * EA * (stretch - 1)
    return label, stretch, speed, q, length, speed / radius, torque


def wave_case(count, torque_shift=0.):
    duration = .045
    intervals = 90
    def torque(time):
        return wave_reel(time)[6] + torque_shift
    # Slopes are independently generated at declaration time. The runtime
    # reads only these serialized piecewise-Hermite forcing knots.
    history = tuple((i * duration / intervals,
                     torque(i * duration / intervals),
                     (torque(i * duration / intervals + 1e-6) -
                      torque(i * duration / intervals - 1e-6)) / 2e-6)
                    for i in range(intervals + 1))
    fields = tuple(conserved(*wave(0., (i + .5) / count)[1:])
                   for i in range(count))
    return t2.T2Episode(
        count, duration, fields, S0, 1., wave_reel(0.)[5],
        (t2.WoundRecord(S0, S0 + 1, 1.010015685968241193),),
        'fixed', (), history, (.01, .03), S0)


def normalized_field_error(sample):
    n = len(sample['cell_conservative_fields'])
    return math.sqrt(sum(
        ((1 / a - wave(sample['time_s'], (i + .5) / n)[1]) / DELTA) ** 2 +
        ((p / (MU * a) - wave(sample['time_s'], (i + .5) / n)[2]) /
         (C * DELTA)) ** 2
        for i, (a, p) in enumerate(sample['cell_conservative_fields'])) /
        (2 * n))


def independent_drive_work(end_time):
    intervals = 200
    step = end_time / intervals
    total = 0.0
    for index in range(intervals + 1):
        *_, omega, torque = wave_reel(index * step)
        weight = 1 if index in (0, intervals) else (4 if index % 2 else 2)
        total += weight * omega * torque
    return step * total / 3


class IntegratedT2Tests(unittest.TestCase):
    def test_hermite_pulse_cannot_hide_release_reversal(self):
        duration = 1e-5
        base = constant_case(64, duration=duration)
        first = base.applied_torque_history[0][1]
        last = base.applied_torque_history[-1][1]
        history = ((0., first, 1.2e9), (duration, last, -1.2e9))
        episode = replace(base, applied_torque_history=history)
        # Independent cubic: extra torque is 12000*u*(1-u), with a 3000 Nm
        # midpoint peak and exactly 0.02 Nm s extra applied impulse.
        self.assertAlmostEqual(t2._history_value(history, duration/2),
                               (first+last)/2+3000., delta=1e-9)
        self.assertAlmostEqual(duration**2*1.2e9/6, .02, delta=1e-15)
        self.assertLess(t2._forcing_limited_step(0., duration, episode),
                        duration/100)
        initial_records = tuple((item.low_label_m, item.high_label_m,
                                 item.retained_stretch)
                                for item in episode.initial_records)
        try:
            output = t2.run_torque_driven_episode(episode)
        except ValueError as exc:
            self.assertRegex(str(exc), 'phase or event retry collapsed|forcing resolution')
        else:
            self.assertNotEqual(output['episode_outcome'],
                                'COMPLETED_DECLARED_DURATION')
        self.assertEqual(initial_records, tuple((item.low_label_m,
            item.high_label_m, item.retained_stretch)
            for item in episode.initial_records))

    def test_hermite_cancelling_lobes_are_resolved(self):
        duration = 1e-5
        base = constant_case(64, duration=duration)
        first = base.applied_torque_history[0][1]
        last = base.applied_torque_history[-1][1]
        history = ((0., first, 1.2e9), (duration, last, 1.2e9))
        episode = replace(base, applied_torque_history=history)
        self.assertAlmostEqual(t2._history_value(history, duration/2),
                               (first+last)/2, delta=1e-9)
        self.assertLess(t2._forcing_limited_step(0., duration, episode),
                        duration/100)
        output = t2.run_torque_driven_episode(episode)
        self.assertEqual(output['episode_outcome'], 'COMPLETED_DECLARED_DURATION')
        initial = output['accepted_states'][0]['reel_angular_momentum_kg_m2_s']
        self.assertGreater(max(abs(state['reel_angular_momentum_kg_m2_s']-initial)
                               for state in output['accepted_states']), .003)
        self.assertLess(output['accumulated_applied_torque_quadrature_bound_nm_s'],
                        t2.TORQUE_QUADRATURE_BUDGET_NM_S)

    def test_near_knot_forcing_uses_exact_segment_or_rejects(self):
        interval = 2.**-16
        slope = 2.**70
        history = ((0., 0., 0.), (interval, 0., slope),
                   (2*interval, interval*slope, slope))
        just_before = interval-2.**-45
        just_after = interval+2.**-47
        self.assertEqual(t2._first_future_knot(just_before, history), interval)
        with self.assertRaisesRegex(ValueError, 'crossed a knot'):
            t2._history_curvature_bound(history, just_before, interval/2)
        self.assertAlmostEqual(t2._history_value(history, just_after),
                               slope*(just_after-interval), delta=1e-6)

    def test_incoming_hermite_pulse_reaches_first_tension_zero(self):
        duration = 1e-5
        base = constant_case(64, duration=duration)
        incoming = base.left_incoming_history[0][1]
        episode = replace(base, left_incoming_history=(
            (0., incoming, 12000.), (duration, incoming, -12000.)))
        output = t2.run_torque_driven_episode(episode)
        self.assertEqual(output['episode_outcome'],
                         'STOPPED_AT_FIRST_TENSION_ZERO')
        self.assertLessEqual(output['maximum_incoming_characteristic_chord_bound_m_s'],
                             t2.INCOMING_CHARACTERISTIC_CHORD_BUDGET_M_S*(1+1e-12))

    def test_mild_hermite_pulse_matches_refined_declared_history(self):
        duration = .005
        base = constant_case(64, duration=duration)
        first = base.applied_torque_history[0][1]
        last = base.applied_torque_history[-1][1]
        episode = replace(base, applied_torque_history=(
            (0., first, 1.), (duration, last, -1.)))
        def exact_torque(time_s):
            u = time_s/duration
            return ((2*u**3-3*u**2+1)*first +
                    (-2*u**3+3*u**2)*last + duration*u*(1-u))
        reference = replace(base, applied_torque_history=tuple(
            (i*duration/200, exact_torque(i*duration/200))
            for i in range(201)))
        output = t2.run_torque_driven_episode(episode)
        refined = t2.run_torque_driven_episode(reference)
        self.assertEqual(output['episode_outcome'], 'COMPLETED_DECLARED_DURATION')
        self.assertAlmostEqual(output['accepted_states'][-1]['reel_angular_speed_rad_s'],
                               refined['accepted_states'][-1]['reel_angular_speed_rad_s'],
                               delta=2e-6)
        expected_impulse = duration*(first+last)/2+duration**2/6
        states = output['accepted_states']
        applied_impulse = sum((b['time_s']-a['time_s'])*(
            exact_torque(a['time_s'])+exact_torque(b['time_s']))/2
            for a, b in zip(states, states[1:]))
        self.assertLess(abs(applied_impulse-expected_impulse),
                        output['accumulated_applied_torque_quadrature_bound_nm_s']*
                        (1+1e-8))
        self.assertLess(output['accumulated_applied_torque_quadrature_bound_nm_s'],
                        t2.TORQUE_QUADRATURE_BUDGET_NM_S)

    def test_constant_mismatch_signed_transfer_heat_and_components(self):
        for n in (64, 128, 256):
            with self.subTest(cells=n):
                episode = constant_case(n)
                result = t2.run_torque_driven_episode(episode)
                self.assertEqual(result['episode_outcome'],
                                 'COMPLETED_DECLARED_DURATION')
                self.assertEqual(result['torque_role'], 'prescribed_input')
                self.assertEqual(result['pickup_closure_role'],
                                 'idealized_dissipative_not_physically_validated')
                self.assertEqual(result['events'], [])
                self.assertLess(result['maximum_combined_inventory_defect_kg'], 1e-10)
                self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'],
                                1e-8)
                self.assertLess(result['maximum_reel_cumulative_energy_defect_j'],
                                1e-8)
                self.assertLess(result['maximum_combined_energy_defect_j'], 1e-8)
                self.assertLess(result['maximum_exact_storage_vs_transfer_flux_defect_j'],
                                1e-10)
                self.assertLessEqual(result['maximum_reconstructed_stage_courant'],
                                     .35 * (1 + 1e-12))
                initial, final = result['snapshots'][0], result['snapshots'][-1]
                self.assertAlmostEqual(final['right_cut_label_m'], 1.01,
                                       delta=1e-10)
                self.assertAlmostEqual(final['accumulated_dissipated_energy_j'],
                                       4.049595e-6, delta=1e-9)
                self.assertAlmostEqual(final['owned_wound_strain_energy_j'] -
                                       initial['owned_wound_strain_energy_j'],
                                       -5e-6, delta=1e-10)
                self.assertLess(final['integrated_right_flux'][0], 0)
                self.assertLess(final['integrated_right_energy_terms'][1], 0)
                self.assertLess(abs(final['integrated_dissipated_power_j'] -
                                    4.049595e-6), 1e-9)
                for sample in result['snapshots']:
                    length = 1 - .1 * sample['time_s']
                    radius, _ = geometry(length)
                    self.assertAlmostEqual(sample['reel_angular_speed_rad_s'],
                                           -.101 / radius, delta=1e-8)
                    self.assertAlmostEqual(sample['right_span_stretch'], 1.001,
                                           delta=1e-9)
                    self.assertAlmostEqual(sample['right_donor_stretch'], 1.01,
                                           delta=1e-15)
                    self.assertAlmostEqual(sample['right_span_speed_m_s'],
                                           -.1001, delta=1e-9)
                    self.assertAlmostEqual(sample['right_wound_speed_m_s'],
                                           -.101, delta=1e-9)
                    self.assertAlmostEqual(sample['right_reference_flux_m_s'],
                                           -.1, delta=1e-9)
                    self.assertEqual(sample['accepted_record_count'], 1)
                    self.assertEqual(sample['right_donor_role'],
                                     'original_retained_record')
                self.assertGreater(len(result['accepted_states']),
                                   len(result['snapshots']))

    def test_torque_and_original_donor_change_predicted_trajectory(self):
        base = t2.run_torque_driven_episode(constant_case(64, .02))
        changed_torque = t2.run_torque_driven_episode(
            constant_case(64, .02, torque_shift=.0002))
        changed_donor = t2.run_torque_driven_episode(
            constant_case(64, .02, donor_stretch=1.011))
        for changed in (changed_torque, changed_donor):
            self.assertGreater(abs(changed['snapshots'][1][
                'right_reference_flux_m_s'] - base['snapshots'][1][
                    'right_reference_flux_m_s']), 1e-7)
            self.assertGreater(abs(changed['snapshots'][1][
                'right_span_speed_m_s'] - base['snapshots'][1][
                    'right_span_speed_m_s']), 1e-7)
        self.assertNotEqual(changed_donor['snapshots'][0]['right_donor_stretch'],
                            base['snapshots'][0]['right_donor_stretch'])

    def test_unequal_original_layers_switch_only_at_accepted_boundary(self):
        base = constant_case(64, .02)
        episode = t2.T2Episode(**{**base.__dict__, 'initial_records': (
            t2.WoundRecord(1.001037, 2., 1.05),
            t2.WoundRecord(1., 1.001037, 1.01))})
        result = t2.run_torque_driven_episode(episode)
        self.assertEqual([event['kind'] for event in result['events']],
                         ['donor_boundary'])
        self.assertAlmostEqual(result['events'][0]['time_s'], .01037,
                               delta=1e-6)
        self.assertLess(result['events'][0]['bracket_time_s'][1] -
                        result['events'][0]['bracket_time_s'][0], 1e-9)
        self.assertLess(result['maximum_exact_storage_vs_transfer_flux_defect_j'],
                        1e-10)
        self.assertLess(result['maximum_reel_cumulative_energy_defect_j'], 1e-10)
        self.assertLess(abs(result['events'][0]['cut_endpoint_error_m']), 1e-11)
        self.assertLess(abs(result['events'][0]['storage_ownership_error_bound_j']),
                        1e-12)
        self.assertLess(result['cumulative_donor_endpoint_storage_error_bound_j'],
                        1e-12)
        self.assertEqual([item['right_donor_stretch'] for item in
                          result['snapshots']], [1.01, 1.01, 1.01, 1.05, 1.05])

    def test_torque_driven_matched_reversal_and_stored_donor_refine(self):
        errors = []
        for n in (64, 128, 256):
            with self.subTest(cells=n):
                episode = wave_case(n)
                result = t2.run_torque_driven_episode(episode)
                self.assertEqual(result['episode_outcome'],
                                 'STOPPED_AT_DECLARED_CUT')
                self.assertEqual(result['torque_role'], 'prescribed_input')
                self.assertGreater(len(result['events']), 3)
                self.assertEqual(result['events'][0]['kind'], 'reversal')
                self.assertEqual(result['events'][-1]['kind'], 'cut_limit')
                self.assertTrue(all(event['kind'] == 'donor_boundary'
                                    for event in result['events'][1:-1]))
                for event in result['events']:
                    self.assertLess(event['bracket_time_s'][1] -
                                    event['bracket_time_s'][0], 1e-9)
                self.assertLess(result['maximum_combined_inventory_defect_kg'],
                                1e-10)
                self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'],
                                1e-8)
                self.assertLess(result['maximum_reel_cumulative_energy_defect_j'],
                                1e-8)
                self.assertLess(result['maximum_combined_energy_defect_j'],
                                1e-8)
                self.assertLess(result['maximum_exact_storage_vs_transfer_flux_defect_j'],
                                1e-10)
                self.assertLess(result['snapshots'][-1][
                    'accumulated_dissipated_energy_j'], 1e-10)
                self.assertEqual(result['original_initial_records'], [
                    {'low_label_m': S0, 'high_label_m': S0 + 1,
                     'retained_stretch': 1.010015685968241193}])
                samples = result['snapshots']
                self.assertEqual([item['phase'] for item in samples],
                                 ['wind', 'wind', 'release', 'release', 'release'])
                self.assertEqual(samples[0]['right_donor_role'],
                                 'newly_deposited_span_state')
                self.assertEqual(samples[2]['right_donor_role'],
                                 'original_retained_record')
                self.assertEqual(samples[-1]['time_s'], result['events'][-1]['time_s'])
                for anchor in (samples[2], samples[-1]):
                    exact = wave_reel(anchor['time_s'])
                    _, exact_inertia = geometry(exact[4])
                    exact_angular_impulse = (exact_inertia * exact[5] -
                        samples[0]['reel_angular_momentum_kg_m2_s'])
                    self.assertLess(abs(anchor['integrated_angular_rhs_nm_s'] -
                                        exact_angular_impulse), 1e-7)
                    self.assertLess(abs(anchor['integrated_drive_work_j'] -
                                        independent_drive_work(anchor['time_s'])),
                                    1e-9)
                for sample in samples:
                    exact = wave_reel(sample['time_s'])
                    self.assertLess(abs(sample['reel_angular_speed_rad_s'] -
                                        exact[5]), 1e-4)
                    self.assertLess(abs(sample['right_cut_label_m'] - exact[0]),
                                    1e-7)
                    self.assertLess(normalized_field_error(sample), .01)
                    records = sample['ordered_original_wound_records']
                    self.assertEqual(records[0]['low_label_m'], S0)
                    self.assertLess(abs(sum(max(0., item['high_label_m'] -
                                            max(item['low_label_m'], sample['right_cut_label_m']))
                                            for item in records) -
                                        sample['reel_reference_length_m']), 1e-10)
                    for a, b in zip(records, records[1:]):
                        self.assertAlmostEqual(a['low_label_m'], b['high_label_m'],
                                               delta=1e-11)
                errors.append((abs(result['events'][0]['time_s'] - .02),
                               abs(result['events'][-1]['time_s'] - .04),
                               normalized_field_error(samples[3])))
        for j in range(3):
            self.assertLess(errors[1][j], errors[0][j])
            self.assertLess(errors[2][j], errors[1][j])
            self.assertLess(errors[2][j], 5e-5)

    def test_history_input_rejections(self):
        good = wave_case(64)
        with self.assertRaises(ValueError):
            t2.T2Episode(**{**good.__dict__, 'initial_records': (
                t2.WoundRecord(S0, S0 + .5, 1.01),)})
        with self.assertRaises(ValueError):
            t2.T2Episode(**{**good.__dict__, 'applied_torque_history': (
                (0., 0.), (.01, 0.))})
        with self.assertRaises(ValueError):
            t2.T2Episode(**{**good.__dict__, 'initial_phase': 'release'})
        release = constant_case(64, .02)
        with self.assertRaises(ValueError):
            t2.T2Episode(**{**release.__dict__, 'stop_cut_label_m': 2.})
        with self.assertRaises(ValueError):
            t2.T2Episode(**{**good.__dict__, 'initial_records': (
                t2.WoundRecord(S0, S0 + 1, .99),)})
        with self.assertRaises(ValueError):
            t2.run_torque_driven_episode(None)
        with self.assertRaises(ValueError):
            t2.WoundRecord(True, 2., 1.01)
        with self.assertRaises(ValueError):
            t2.T2Episode(**{**good.__dict__, 'duration_s': 1e-14,
                'applied_torque_history': ((0., 0.), (1e-14, 0.))})

    def test_release_predictor_touch_does_not_commit_positive_transfer(self):
        radius, _ = geometry_module._geometry(1.)
        speed = radius * -.01 / 1.5 * 1.001
        episode = t2.T2Episode(
            64, .0005, tuple(conserved(1.001, speed) for _ in range(64)),
            1., 1., -.01, (t2.WoundRecord(1., 2., 1.5),),
            'incoming_characteristic', ((0., speed - 10.01),
                                        (.0005, speed - 10.01)),
            ((0., .33), (.0005, -.35)), (), 1.01,
            initial_phase='release')
        result = t2.run_torque_driven_episode(episode)
        self.assertEqual(result['episode_outcome'],
                         'COMPLETED_DECLARED_DURATION')
        self.assertGreater(len(result['accepted_states']), 2)
        self.assertTrue(all(item['right_reference_flux_m_s'] <= 0
                            for item in result['accepted_states']))
        self.assertLess(result['maximum_reel_cumulative_energy_defect_j'],
                        2e-7)

    def test_second_reversal_and_first_tension_zero_stop_at_located_event(self):
        reversed_episode = constant_case(64, .02, torque_shift=1.)
        reversed_result = t2.run_torque_driven_episode(reversed_episode)
        self.assertEqual(reversed_result['episode_outcome'],
                         'STOPPED_AT_UNSUPPORTED_SECOND_REVERSAL')
        self.assertEqual([item['kind'] for item in reversed_result['events']],
                         ['unsupported_reverse_to_wind'])
        self.assertLess(reversed_result['events'][0]['bracket_time_s'][1] -
                        reversed_result['events'][0]['bracket_time_s'][0], 1e-9)
        base = constant_case(64, .02)
        start = base.left_incoming_history[0][1]
        tension_episode = t2.T2Episode(**{**base.__dict__,
            'left_incoming_history': ((0., start), (.02, start + .04))})
        tension_result = t2.run_torque_driven_episode(tension_episode)
        self.assertEqual(tension_result['episode_outcome'],
                         'STOPPED_AT_FIRST_TENSION_ZERO')
        self.assertEqual([item['kind'] for item in tension_result['events']],
                         ['tension_zero'])
        self.assertAlmostEqual(tension_result['events'][0]['time_s'], .01,
                               delta=1e-9)
        self.assertGreaterEqual(tension_result['minimum_used_stretch'],
                                1 - 1e-10)

    def test_fixed_grid_time_refinement_and_declared_forcing_error(self):
        base = wave_case(64)
        forcing_error = max(abs(t2._history_value(
            base.applied_torque_history,
            (a[0] + b[0]) / 2) - wave_reel((a[0] + b[0]) / 2)[6])
            for a, b in zip(base.applied_torque_history,
                            base.applied_torque_history[1:]))
        self.assertLess(forcing_error, 5e-7)
        errors = []
        for cfl in (.35, .175, .0875):
            episode = t2.T2Episode(**{**base.__dict__, 'cfl_limit': cfl})
            result = t2.run_torque_driven_episode(episode)
            self.assertEqual(result['episode_outcome'],
                             'STOPPED_AT_DECLARED_CUT')
            errors.append((abs(result['events'][0]['time_s'] - .02),
                           abs(result['events'][-1]['time_s'] - .04)))
        for component in range(2):
            self.assertLess(errors[1][component], errors[0][component])
            self.assertLess(errors[2][component], errors[1][component])
            self.assertLess(errors[2][component], 5e-5)

    def test_observation_requests_do_not_change_accepted_material_history(self):
        episode = wave_case(64)
        sampled = t2.run_torque_driven_episode(episode)
        unsampled = t2.run_torque_driven_episode(t2.T2Episode(**{
            **episode.__dict__, 'observation_times_s': ()}))
        self.assertEqual(sampled['accepted_states'], unsampled['accepted_states'])
        self.assertEqual(sampled['events'], unsampled['events'])
        self.assertEqual(sampled['snapshots'][-1], unsampled['snapshots'][-1])
        self.assertEqual([item['requested_observation_time_s'] for item in
                          sampled['snapshots'] if 'requested_observation_time_s'
                          in item], list(episode.observation_times_s))


if __name__ == '__main__':
    unittest.main()
