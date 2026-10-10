"""Independent repeated-event wave and reduced reel references."""

import bisect
import unittest
from dataclasses import replace
from unittest.mock import patch

from physicroll import transient_t2 as one
from physicroll import transient_t2_two_reel as two
from physicroll import transient_t2a5 as span
from tests.test_transient_t2_recapture import exact_end, wave_case
from tests.test_transient_t2_two_reel import case, geometry


def split_wave_case(count, cfl=span.CFL_LIMIT, torque_knots=100):
    base = wave_case(count, cfl=cfl, torque_knots=torque_knots)
    ends = {}
    for side, times, retained in (
            ('left', (.008, .027), 1.01),
            ('right', (.005, .012), 1.0125)):
        end = getattr(base, side)
        cuts = [end.initial_local_cut_m]
        cuts.extend(exact_end(side, time)['cut'] for time in times)
        cuts.append(end.initial_local_cut_m+end.initial_reference_length_m)
        records = tuple(one.WoundRecord(low, high, retained)
                        for low, high in reversed(list(zip(cuts, cuts[1:]))))
        ends[side] = replace(end, initial_records=records)
    return replace(base, **ends,
                   event_policy=two.CONTINUE_ISOLATED_SEQUENCE)


def unequal_donor_case(count=64, cfl=span.CFL_LIMIT):
    base = case(count, duration=.07, cfl=cfl)
    end = base.left
    cut = end.initial_local_cut_m
    first, second = cut+.0037, cut+.005
    records = (one.WoundRecord(second, cut+1., 1.03),
               one.WoundRecord(first, second, 1.02),
               one.WoundRecord(cut, first, 1.01))
    return replace(base, left=replace(end, initial_records=records),
                   event_policy=two.CONTINUE_ISOLATED_SEQUENCE)


def independent_reel_reference(episode, step_s=1e-6):
    """RK4 ODE with an imposed exact outgoing wave, independent of FV ports."""
    end = episode.left
    cut0 = end.initial_local_cut_m
    history = end.applied_torque_history
    times = [item[0] for item in history]
    values = (1., end.initial_omega_rad_s, 0., 0., 0., 0.)

    def rhs(time, state):
        length, omega, _, _, _, _ = state
        cut = cut0+1.-length
        retained = next(item.retained_stretch for item in reversed(
            end.initial_records) if item.low_label_m <= cut < item.high_label_m)
        radius, inertia = geometry(length)
        q = radius*omega/retained
        stretch = -10.1101/(q-10.)
        speed = q*stretch
        index = min(bisect.bisect_right(times, time)-1, len(times)-2)
        low_t, low_tau = history[index]
        high_t, high_tau = history[index+1]
        torque = low_tau+(high_tau-low_tau)*(time-low_t)/(high_t-low_t)
        tension = 10.*(stretch-1.)
        impulse_rate = torque-radius*tension+.1*q*radius*speed
        acceleration = (impulse_rate-.1*q*radius**2*omega)/inertia
        dissipation = (-q)*(10.-.1*q*q)*(stretch-retained)**2/2
        return q, acceleration, omega, torque*omega, dissipation, impulse_rate

    count = round(episode.duration_s/step_s)
    h = episode.duration_s/count
    for index in range(count):
        time = index*h
        a = rhs(time, values)
        b = rhs(time+h/2, tuple(values[j]+h*a[j]/2 for j in range(6)))
        c = rhs(time+h/2, tuple(values[j]+h*b[j]/2 for j in range(6)))
        d = rhs(time+h, tuple(values[j]+h*c[j] for j in range(6)))
        values = tuple(values[j]+h*(a[j]+2*b[j]+2*c[j]+d[j])/6
                       for j in range(6))
    return values


class EventSequenceTests(unittest.TestCase):
    def test_sequence_cfl_and_forcing_refinement(self):
        cfl_errors = []
        for cfl in (span.CFL_LIMIT, span.CFL_LIMIT/2, span.CFL_LIMIT/4):
            result = two.run_two_reel_episode(split_wave_case(64, cfl=cfl))
            self.assertEqual(len(result['transitions']), 5)
            cfl_errors.append(abs(result['transitions'][2]['accepted_time_s']-.012))
        self.assertLess(cfl_errors[2], cfl_errors[1])
        self.assertLess(cfl_errors[1], cfl_errors[0])
        force_errors = []
        for knots in (25, 50, 100):
            result = two.run_two_reel_episode(split_wave_case(
                64, torque_knots=knots))
            self.assertEqual(len(result['transitions']), 5)
            force_errors.append(abs(result['transitions'][3]['accepted_time_s']-.02))
        self.assertLess(force_errors[2], force_errors[1])
        self.assertLess(force_errors[1], force_errors[0])

    def test_five_event_traveling_wave_and_refinement(self):
        expected = [('right', 'internal_donor_restart', .005),
                    ('left', 'internal_donor_restart', .008),
                    ('right', 'internal_donor_restart', .012),
                    ('right', 'release_to_wind', .02),
                    ('left', 'internal_donor_restart', .027)]
        errors = []
        for count in (64, 128, 256):
            with self.subTest(count=count):
                episode = split_wave_case(count)
                result = two.run_two_reel_episode(episode)
                unsplit = two.run_two_reel_episode(wave_case(count, torque_knots=100))
                self.assertEqual(result['episode_outcome'],
                                 'COMPLETED_DECLARED_DURATION')
                self.assertEqual(result['events'], [])
                self.assertEqual(len(result['transitions']), len(expected))
                for index, ((side, kind, exact_time), transition) in enumerate(
                        zip(expected, result['transitions']), 1):
                    self.assertEqual((transition['side'], transition['kind']),
                                     (side, kind))
                    self.assertEqual(transition['sequence_index'], index)
                    self.assertLess(abs(transition['accepted_time_s']-exact_time),
                                    2e-6)
                    self.assertEqual(transition['phase_before'], 'release')
                    self.assertEqual(transition['phase_after'],
                                     'wind' if kind == 'release_to_wind' else 'release')
                    self.assertLessEqual(transition[
                        'cumulative_absolute_event_storage_bound_j'],
                        two.MAX_CUMULATIVE_EVENT_STORAGE_BOUND_J)
                last = result['accepted_states'][-1]
                reference = unsplit['accepted_states'][-1]
                right_start = episode.right.initial_local_cut_m
                right_turn = result['transitions'][3]['turning_cut_label_m']
                right_final = last['ends']['right']['local_cut_label_m']
                self.assertAlmostEqual(right_turn-right_start,
                                       .00012502089456145615, delta=2e-7)
                self.assertAlmostEqual(right_turn-right_final,
                                       .00014154148397321764, delta=2e-7)
                for side in ('left', 'right'):
                    actual, prior = last['ends'][side], reference['ends'][side]
                    for field in ('reference_length_m', 'angular_speed_rad_s',
                                  'owned_wound_strain_energy_j',
                                  'integrated_drive_work_j',
                                  'accumulated_dissipated_energy_j'):
                        self.assertAlmostEqual(actual[field], prior[field],
                                               delta=2e-8)
                    cut = actual['local_cut_label_m']
                    self.assertAlmostEqual(sum(item['high_label_m']-
                        max(cut, item['low_label_m']) for item in
                        actual['ordered_wound_records'] if item['high_label_m'] > cut),
                        actual['reference_length_m'], delta=1e-13)
                    self.assertEqual(result['original_initial_records'][side][0][
                        'high_label_m'], getattr(episode, side).initial_records[0].high_label_m)
                    self.assertGreaterEqual(min(state['ends'][side][
                        'accumulated_dissipated_energy_j'] for state in
                        result['accepted_states']), 0.)
                self.assertLess(result['maximum_combined_energy_defect_j'], 1e-9)
                self.assertLess(result['maximum_combined_inventory_defect_kg'], 1e-10)
                self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'],
                                1e-10)
                self.assertLess(result['maximum_reel_cumulative_energy_defect_j'],
                                1e-9)
                errors.append(abs(result['transitions'][3]['accepted_time_s']-.02))
        self.assertLess(errors[2], errors[0])

    def test_reflection_and_observation_cadence(self):
        episode = split_wave_case(64)
        baseline = two.run_two_reel_episode(episode)
        observed = two.run_two_reel_episode(replace(episode,
            observation_times_s=(.006, .01, .018, .024, .035)))
        self.assertEqual(baseline['transitions'], observed['transitions'])
        self.assertEqual(baseline['accepted_states'], observed['accepted_states'])
        reflected = replace(episode, left=episode.right, right=episode.left,
            initial_conserved_fields=tuple((rho, -momentum) for rho, momentum
                in reversed(episode.initial_conserved_fields)))
        swapped = two.run_two_reel_episode(reflected)
        self.assertEqual(swapped['episode_outcome'], 'COMPLETED_DECLARED_DURATION')
        self.assertEqual([(item['side'], item['kind']) for item in
                          swapped['transitions']],
                         [('left' if item['side'] == 'right' else 'right',
                           item['kind']) for item in baseline['transitions']])
        for side, other in (('left', 'right'), ('right', 'left')):
            a = baseline['accepted_states'][-1]['ends'][side]
            b = swapped['accepted_states'][-1]['ends'][other]
            self.assertAlmostEqual(a['reference_length_m'],
                                   b['reference_length_m'], delta=1e-12)

    def test_sequence_budget_stops_before_ninth_donor(self):
        base = case(duration=.06)
        cut = base.left.initial_local_cut_m
        bounds = [cut+index*.0005 for index in range(10)]+[cut+1.]
        records = tuple(one.WoundRecord(low, high, 1.01) for low, high in
                        reversed(list(zip(bounds, bounds[1:]))))
        episode = replace(base, left=replace(base.left, initial_records=records),
                          event_policy=two.CONTINUE_ISOLATED_SEQUENCE)
        result = two.run_two_reel_episode(episode)
        self.assertEqual(result['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertEqual(len(result['transitions']),
                         two.MAX_ISOLATED_TRANSITIONS)
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'isolated_transition_budget_exhausted')
        self.assertGreater(result['accepted_states'][-1]['ends']['left'][
            'reference_length_m'], 0.)

    def test_two_unequal_donors_against_separate_ode(self):
        episode = unequal_donor_case()
        result = two.run_two_reel_episode(episode)
        self.assertEqual(result['episode_outcome'], 'COMPLETED_DECLARED_DURATION')
        self.assertEqual([(item['side'], item['kind']) for item in
                          result['transitions']],
                         [('left', 'internal_donor_restart')]*2)
        reference = independent_reel_reference(episode, 5e-7)
        coarser = independent_reel_reference(episode, 1e-6)
        for a, b, tolerance in zip(reference, coarser,
                (1e-9, 1e-8, 1e-9, 1e-10, 1e-10, 1e-10)):
            self.assertLess(abs(a-b), tolerance)
        end = result['accepted_states'][-1]['ends']['left']
        for field, value, tolerance in (
                ('reference_length_m', reference[0], 2e-9),
                ('angular_speed_rad_s', reference[1], 2e-8),
                ('integrated_drive_work_j', reference[3], 1e-10),
                ('accumulated_dissipated_energy_j', reference[4], 1e-10),
                ('integrated_angular_rhs_nm_s', reference[5], 1e-10)):
            self.assertAlmostEqual(end[field], value, delta=tolerance)
        self.assertGreaterEqual(end['accumulated_dissipated_energy_j'], 0.)
        self.assertLess(result['maximum_combined_energy_defect_j'], 1e-8)

    def test_cumulative_storage_budget_denies_second_commit(self):
        episode = unequal_donor_case()
        baseline = two.run_two_reel_episode(episode)
        first, second = (item['cumulative_absolute_event_storage_bound_j']
                         for item in baseline['transitions'])
        self.assertGreater(second, first)
        with patch.object(two, 'MAX_CUMULATIVE_EVENT_STORAGE_BOUND_J',
                          (first+second)/2):
            denied = two.run_two_reel_episode(episode)
        self.assertEqual(len(denied['transitions']), 1)
        self.assertEqual(denied['events'][0]['restart_attempt_status'],
                         'cumulative_event_storage_budget_exhausted')
        self.assertEqual(denied['cumulative_absolute_event_storage_bound_j'], first)
        self.assertEqual(denied['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertEqual(denied['accepted_states'][:-1],
                         baseline['accepted_states'][:len(denied['accepted_states'])-1])
        stopped = denied['accepted_states'][-1]['ends']['left']
        self.assertEqual(stopped['phase'], 'release')
        self.assertEqual(len(stopped['ordered_wound_records']), 3)
        self.assertLess(denied['maximum_combined_energy_defect_j'], 1e-8)


if __name__ == '__main__':
    unittest.main()
