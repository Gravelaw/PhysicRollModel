"""Independent traveling-wave and ownership checks for isolated recapture."""

import math
import unittest
from dataclasses import replace

from physicroll import transient_t2 as one
from physicroll import transient_t2_two_reel as two
from physicroll import transient_t2a5 as span


K = math.pi/2
C = 1.4735899778104424
MU = .1
EA = 10.
KAPPA = .001/math.pi
TURN = .02
DURATION = .04


def geometry(length):
    radius = math.sqrt(.1**2+KAPPA*length)
    inertia = .01+MU*(.1**2*length+KAPPA*length**2/2)
    return radius, inertia


def label(position, time):
    value = (position-C-.025*time)/1.01
    for _ in range(12):
        phase = K*(value-10*time)
        x = C+1.01*value+.025*time+.005/K*math.sin(phase)
        value -= (x-position)/(1.01+.005*math.cos(phase))
    return value


def exact_end(side, time):
    normal = -1 if side == 'left' else 1
    position = 0. if side == 'left' else 1.
    material = label(position, time)
    initial = label(position, 0.)
    phase = K*(material-10*time)
    stretch = 1.01+.005*math.cos(phase)
    speed = .025-.05*math.cos(phase)
    g = speed/stretch
    gdot = -.005*K*math.sin(phase)*(g+10)**2/stretch
    lamdot = .005*K*math.sin(phase)*(g+10)
    vdot = -10*lamdot
    q = normal*g
    qdot = normal*gdot
    cut = normal*material
    initial_cut = normal*initial
    length = 1+initial_cut-cut
    radius, inertia = geometry(length)
    radius_rate = KAPPA*q/(2*radius)
    retained = 1.01 if side == 'left' else 1.0125
    if side == 'left' or time <= TURN:
        omega = q*retained/radius
        omega_rate = retained*(qdot/radius-q*radius_rate/radius**2)
    else:
        omega = normal*speed/radius
        omega_rate = normal*(vdot/radius-speed*radius_rate/radius**2)
    tension = EA*(stretch-1)
    torque = (inertia*omega_rate+radius*tension-
              MU*q*radius*(normal*speed-radius*omega))
    return {'cut': cut, 'length': length, 'omega': omega,
            'torque': torque, 'q': q, 'stretch': stretch,
            'speed': speed}


def wave_case(count=64, cfl=span.CFL_LIMIT, torque_knots=400):
    dx = 1/count
    fields = []
    for index in range(count):
        low = label(index*dx, 0.)
        high = label((index+1)*dx, 0.)
        phi_low, phi_high = K*low, K*high
        fields.append(((high-low)/dx,
                       MU*(.025*(high-low)-.05/K*(
                           math.sin(phi_high)-math.sin(phi_low)))/dx))
    ends = {}
    for side in ('left', 'right'):
        start = exact_end(side, 0.)
        cut = start['cut']
        retained = 1.01 if side == 'left' else 1.0125
        history = tuple((DURATION*index/torque_knots,
                         exact_end(side, DURATION*index/torque_knots)['torque'])
                        for index in range(torque_knots+1))
        ends[side] = two.ReelEnd(cut, 1., start['omega'],
            (one.WoundRecord(cut, cut+1, retained),), history, 'release')
    return two.TwoReelEpisode(count, DURATION, tuple(fields),
        ends['left'], ends['right'], cfl_limit=cfl,
        event_policy=two.CONTINUE_ISOLATED_RECAPTURE)


class RecaptureTests(unittest.TestCase):
    def test_traveling_wave_recap_and_owned_records(self):
        errors = []
        event_errors = []
        for count in (64, 128, 256):
            with self.subTest(count=count):
                result = two.run_two_reel_episode(wave_case(count))
                self.assertEqual(result['episode_outcome'],
                                 'COMPLETED_DECLARED_DURATION')
                self.assertEqual([(e['side'], e['kind']) for e in
                                  result['transitions']],
                                 [('right', 'release_to_wind')])
                event = result['transitions'][0]
                self.assertEqual(event['event_time_interpretation'],
                    'midpoint_numerical_root_not_physical_event_time')
                self.assertLess(abs(event['accepted_time_s']-TURN), 1e-7)
                event_errors.append(abs(event['accepted_time_s']-TURN))
                self.assertLess(event['midpoint_corrected_endpoint_omega_rad_s'],
                                two.RECAPTURE_MAX_OMEGA_RAD_S)
                self.assertGreaterEqual(event['midpoint_corrected_endpoint_omega_rad_s'], 0)
                self.assertLess(abs(event['turning_label_inventory_residual_m']),
                                1e-13)
                self.assertLess(abs(event[
                    'terminal_old_material_storage_vs_midpoint_flux_residual_j']),
                    1e-12)
                low, high = event['midpoint_corrected_root_bracket_time_s']
                self.assertLessEqual(high-low, 1e-11)
                self.assertLess(event['numerical_turning_sliver_estimate_m'],
                                two.RECAPTURE_MAX_SLIVER_M)
                at_turn = result['accepted_states'][event['accepted_state_index']]
                right = at_turn['ends']['right']
                self.assertEqual(right['phase'], 'wind')
                # The terminal step releases old material only. A mixed
                # release/wind Heun endpoint would double gross transfer.
                self.assertEqual(len(right['ordered_wound_records']), 1)
                self.assertEqual(right['local_cut_label_m'],
                                 right['ordered_wound_records'][-1]['low_label_m'])
                self.assertEqual(result['original_initial_records']['right'][0][
                    'low_label_m'], exact_end('right', 0.)['cut'])
                self.assertGreater(right['ordered_wound_records'][-1][
                    'low_label_m'], result['original_initial_records']['right'][0][
                    'low_label_m'])
                self.assertGreaterEqual(min(state['ends']['right'][
                    'accumulated_dissipated_energy_j'] for state in
                    result['accepted_states']), 0.)
                final = result['accepted_states'][-1]
                end = final['ends']['right']
                exact = exact_end('right', DURATION)
                error = abs(end['reference_length_m']-exact['length'])
                errors.append(error)
                self.assertLess(error, 4e-9)
                self.assertAlmostEqual(end['angular_speed_rad_s'], exact['omega'],
                                       delta=1e-6)
                self.assertAlmostEqual(end['reference_length_m'],
                                       1.0000165205894118, delta=4e-9)
                self.assertAlmostEqual(end['integrated_drive_work_j'],
                                       3.5045545691715055e-5, delta=4e-9)
                self.assertAlmostEqual(end['accumulated_dissipated_energy_j'],
                                       4.786903677307274e-10, delta=1e-12)
                self.assertAlmostEqual(end['integrated_angular_rhs_nm_s'],
                                       .0029011024282535602, delta=1e-8)
                self.assertAlmostEqual(end['integrated_stored_strain_flux_j'],
                                       -3.430766994215772e-9, delta=1e-11)
                # Exact original remainder plus independent quadrature of
                # q*EA*(lambda-1)^2/2 over the winding interval.
                self.assertAlmostEqual(end['owned_wound_strain_energy_j'],
                                       .000781246569233, delta=1e-10)
                left = final['ends']['left']
                self.assertAlmostEqual(left['reference_length_m'],
                                       .9973257294512909, delta=4e-9)
                self.assertAlmostEqual(left['integrated_drive_work_j'],
                                       .000980190149847922, delta=1e-8)
                self.assertAlmostEqual(left['accumulated_dissipated_energy_j'],
                                       2.451017320226447e-7, delta=1e-11)
                self.assertLess(result['maximum_combined_inventory_defect_kg'],
                                1e-10)
                self.assertLess(result['maximum_exact_storage_vs_transfer_flux_defect_j'],
                                1e-10)
                self.assertLess(result['maximum_combined_energy_defect_j'], 1e-9)
                self.assertLess(result['maximum_reel_cumulative_energy_defect_j'],
                                1e-11)
                self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'],
                                1e-12)
                self.assertEqual(end['phase'], 'wind')
                records = end['ordered_wound_records']
                self.assertAlmostEqual(records[0]['low_label_m'],
                                       event['turning_cut_label_m'], delta=1e-14)
                self.assertAlmostEqual(records[-1]['low_label_m'],
                                       end['local_cut_label_m'], delta=1e-14)
                self.assertAlmostEqual(event['turning_cut_label_m']-
                    result['original_initial_records']['right'][0]['low_label_m'],
                    .00012502089456145615, delta=2e-9)
                self.assertAlmostEqual(event['turning_cut_label_m']-
                    end['local_cut_label_m'],
                    .00014154148397321764, delta=2e-9)
                self.assertTrue(all(abs(a['low_label_m']-b['high_label_m']) < 1e-13
                    for a, b in zip(records, records[1:])))
                self.assertAlmostEqual(sum(item['high_label_m']-item['low_label_m']
                    for item in records), end['reference_length_m'], delta=1e-13)
        self.assertLess(errors[2], errors[1])
        self.assertLess(errors[1], errors[0])
        self.assertLess(event_errors[2], event_errors[1])
        self.assertLess(event_errors[1], event_errors[0])

    def test_time_and_forcing_refine_independently(self):
        def error(cfl, knots):
            result = two.run_two_reel_episode(wave_case(64, cfl, knots))
            self.assertEqual(len(result['transitions']), 1)
            return abs(result['accepted_states'][-1]['ends']['right'][
                'reference_length_m']-1.0000165205894118)
        time_errors = [error(cfl, 20) for cfl in
                       (span.CFL_LIMIT, span.CFL_LIMIT/2, span.CFL_LIMIT/4)]
        force_errors = [error(span.CFL_LIMIT, knots)
                        for knots in (20, 40, 80)]
        self.assertLess(time_errors[2], time_errors[1])
        self.assertLess(time_errors[1], time_errors[0])
        self.assertLess(force_errors[2], force_errors[1])
        self.assertLess(force_errors[1], force_errors[0])

    def test_reflection_swaps_only_the_recapturing_end(self):
        base = wave_case(64, torque_knots=100)
        reflected = replace(base, left=base.right, right=base.left,
            initial_conserved_fields=tuple((rho, -momentum)
                for rho, momentum in reversed(base.initial_conserved_fields)))
        original_result = two.run_two_reel_episode(base)
        reflected_result = two.run_two_reel_episode(reflected)
        self.assertEqual(reflected_result['transitions'][0]['side'], 'left')
        for name, reflected_name in (('left', 'right'), ('right', 'left')):
            a = original_result['accepted_states'][-1]['ends'][name]
            b = reflected_result['accepted_states'][-1]['ends'][reflected_name]
            self.assertAlmostEqual(a['reference_length_m'],
                                   b['reference_length_m'], delta=1e-12)
            self.assertAlmostEqual(a['owned_wound_strain_energy_j'],
                                   b['owned_wound_strain_energy_j'], delta=1e-12)

    def test_predictor_only_turn_and_unresolved_labels_stop(self):
        from tests.test_transient_t2_two_reel import case
        duration = .0110198707
        base = case(duration=duration)
        left = replace(base.left, applied_torque_history=((0., 1.),
                                                          (duration, 1.)))
        result = two.run_two_reel_episode(replace(base, left=left,
            event_policy=two.CONTINUE_ISOLATED_RECAPTURE))
        self.assertFalse(result['transitions'])
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'midpoint_corrected_endpoint_not_bracketed')
        base = wave_case(64, torque_knots=100)
        def shifted(end, amount):
            return replace(end, initial_local_cut_m=end.initial_local_cut_m+amount,
                initial_records=tuple(one.WoundRecord(
                    item.low_label_m+amount, item.high_label_m+amount,
                    item.retained_stretch) for item in end.initial_records))
        result = two.run_two_reel_episode(replace(base,
            left=shifted(base.left, 100.), right=shifted(base.right, -100.)))
        self.assertFalse(result['transitions'])
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'insufficient_terminal_label_resolution')

    def test_concurrent_turns_remain_stopped(self):
        cut = 1/1.001/2
        end = two.ReelEnd(cut, 1., -.01,
            (one.WoundRecord(cut, cut+1, 1.02),),
            ((0., .1), (.005, .1)), 'release')
        episode = two.TwoReelEpisode(64, .005,
            tuple(span._conserved(1.001, 0.) for _ in range(64)),
            end, end, event_policy=two.CONTINUE_ISOLATED_RECAPTURE)
        result = two.run_two_reel_episode(episode)
        self.assertEqual(result['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertFalse(result['transitions'])
        self.assertEqual([(event['side'], event['kind']) for event in
                          result['events']],
                         [('left', 'reversal'), ('right', 'reversal')])

    def test_tiny_other_winding_packet_has_bounded_rounding_loss(self):
        radius = math.sqrt(.1**2+KAPPA)
        cut = 1/1.01-.5
        omega = 1e-12
        torque = radius*10*((radius*omega-(.01-10.1))/10-1)
        left = two.ReelEnd(cut, 1., omega,
            (one.WoundRecord(cut, cut+1, 1.01),),
            ((0., torque), (.005, torque)), 'wind')
        right = two.ReelEnd(.5, 1., -.01,
            (one.WoundRecord(.5, 1.5, 1.02),),
            ((0., .1), (.005, .1)), 'release')
        episode = two.TwoReelEpisode(64, .005,
            tuple(span._conserved(1.01, -.01) for _ in range(64)),
            left, right, event_policy=two.CONTINUE_ISOLATED_RECAPTURE)
        result = two.run_two_reel_episode(episode)
        self.assertEqual(result['episode_outcome'],
                         'COMPLETED_DECLARED_DURATION')
        event = result['transitions'][0]
        self.assertEqual(event['kind'], 'release_to_wind')
        self.assertLess(abs(event['other_winding_packet_storage_residual_j']),
                        1e-12)

    def test_exact_zero_winding_start_is_transverse(self):
        radius = math.sqrt(.1**2+KAPPA)
        cut = 1/1.001-.5
        left = two.ReelEnd(cut, 1., .01/radius,
            (one.WoundRecord(cut, cut+1, 1.001),),
            ((0., .001), (.0004, .001), (.0008, .001)), 'wind')
        right = two.ReelEnd(.5, 1., -.003557995619612915,
            (one.WoundRecord(.5, 1.5, 1.02),),
            ((0., .1), (.0004, .1), (.0008, .1)), 'release')
        episode = two.TwoReelEpisode(64, .0008,
            tuple(span._conserved(1.001, -.01) for _ in range(64)),
            left, right, event_policy=two.CONTINUE_ISOLATED_RECAPTURE)
        result = two.run_two_reel_episode(episode)
        self.assertEqual(result['episode_outcome'],
                         'COMPLETED_DECLARED_DURATION')
        self.assertEqual(result['transitions'][0]['kind'], 'release_to_wind')
        self.assertLessEqual(result['transitions'][0][
            'midpoint_corrected_endpoint_omega_rad_s'], 1e-12)
        second_turn = replace(episode, right=replace(right,
            applied_torque_history=((0., .1), (.0004, .1), (.0008, -1.))))
        stopped = two.run_two_reel_episode(second_turn)
        self.assertEqual(stopped['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertEqual(len(stopped['transitions']), 1)
        self.assertEqual([(event['side'], event['kind']) for event in
                          stopped['events']], [('right', 'reversal')])
        self.assertGreater(stopped['accepted_states'][-1]['ends']['right'][
            'angular_speed_rad_s'], 0.)
        close_knot = replace(episode, right=replace(right,
            applied_torque_history=((0., .1), (.0004+5e-14, .1),
                                    (.0008, .1))))
        at_knot = two.run_two_reel_episode(close_knot)
        self.assertEqual(at_knot['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertEqual(len(at_knot['transitions']), 1)
        self.assertEqual(at_knot['events'][0]['restart_attempt_status'],
                         'no_representable_positive_startup_step')


if __name__ == '__main__':
    unittest.main()
