"""Independent constant-flow, reflection, and two-drive checks for T2."""

import math
import unittest
from dataclasses import replace

from physicroll import transient_t2 as one
from physicroll import transient_t2_two_reel as two
from physicroll import transient_t2a5 as span


STRETCH = 1.001
SPEED = .1001
MU = .1
EA = 10.


def geometry(length):
    radius = math.sqrt(.1**2+.001/math.pi*length)
    inertia = .01+MU*(.1**2*length+.001/math.pi*length**2/2)
    return radius, inertia


def exact_torque(side, t, bump=0.):
    q = -.1 if side == 'left' else .1
    outward_speed = -SPEED if side == 'left' else SPEED
    wound_speed = -.101 if side == 'left' else SPEED
    length = 1+q*t
    radius, inertia = geometry(length)
    radius_rate = .001/math.pi*q/(2*radius)
    omega_rate = -wound_speed*radius_rate/radius**2
    return (inertia*omega_rate+radius*EA*(STRETCH-1)-
            MU*q*radius*(outward_speed-wound_speed)+bump)


def case(count=64, duration=.1, reflected=False, bump=0.,
         observation_times=(), cfl=span.CFL_LIMIT):
    cuts = {'left': 1/STRETCH-1, 'right': 1.}
    ends = {}
    for physical_side in ('left', 'right'):
        side = ({'left': 'right', 'right': 'left'}[physical_side]
                if reflected else physical_side)
        q = -.1 if physical_side == 'left' else .1
        retained = 1.01 if physical_side == 'left' else STRETCH
        wound_speed = q*retained
        cut = cuts[physical_side]
        history = tuple((i*duration/100,
            exact_torque(physical_side, i*duration/100,
                         bump if physical_side == 'left' and
                         .005 <= i*duration/100 <= .025 else 0.))
            for i in range(101))
        ends[side] = two.ReelEnd(
            cut, 1., wound_speed/geometry(1.)[0],
            (one.WoundRecord(cut, cut+1, retained),), history,
            'release' if physical_side == 'left' else 'wind')
    return two.TwoReelEpisode(
        count, duration,
        tuple(span._conserved(STRETCH, -SPEED if reflected else SPEED)
              for _ in range(count)), ends['left'], ends['right'],
        observation_times, cfl)


def affine_exact_reel(time):
    """Closed-form two-release reel state and required time-only torque."""
    lam0, beta, kappa = 1.01, .2, .001/math.pi
    lam = lam0-beta*time
    q = -beta/(2*lam**2)
    qdot = -beta**2/lam**3
    length = 1-.5*(1/lam-1/lam0)
    radius = math.sqrt(.1**2+kappa*length)
    inertia = .01+MU*(.1**2*length+kappa*length**2/2)
    radius_rate = kappa*q/(2*radius)
    omega = q*lam0/radius
    omega_rate = lam0*(qdot/radius-q*radius_rate/radius**2)
    torque = (inertia*omega_rate+radius*EA*(lam-1)-
              MU*q*radius*(q*lam-q*lam0))
    return length, inertia, omega, torque, q, lam


def affine_two_release_case(count=64, duration=.055, torque_knots=100,
                            cfl=span.CFL_LIMIT):
    """Independent affine wave with exact first physical tension zero at .05 s."""
    lam0, beta = 1.01, .2
    cut = 1/(2*lam0)
    fields = tuple(span._conserved(lam0,
        -beta*((index+.5)/count-.5)/lam0) for index in range(count))
    history = tuple((time,
        affine_exact_reel(time)[3]) for index in range(torque_knots+1)
        for time in (duration if index == torque_knots else
                     index*duration/torque_knots,))
    end = two.ReelEnd(cut, 1., affine_exact_reel(0.)[2],
        (one.WoundRecord(cut, cut+1, lam0),), history, 'release')
    return two.TwoReelEpisode(count, duration, fields, end, end,
        cfl_limit=cfl, event_policy='stop_at_numerical_admissibility_limit')


class TwoReelTests(unittest.TestCase):
    def test_affine_two_release_first_tautness_limit_refines(self):
        time_errors = []
        energy_errors = []
        drive_errors = []
        heat_errors = []
        def exact_mechanical(time):
            length, inertia, omega, _, _, lam = affine_exact_reel(time)
            span_energy = (MU*.2**2/(24*lam**3)+
                           EA*(lam-1)**2/(2*lam))
            reel_energy = (inertia*omega**2/2+
                           length*EA*(1.01-1)**2/2)
            return span_energy+2*reel_energy
        def simpson(rate, time, intervals=2000):
            h = time/intervals
            return h/3*sum((1 if index in (0, intervals) else
                4 if index%2 else 2)*rate(index*h)
                for index in range(intervals+1))
        for n in (64, 128, 256):
            with self.subTest(cells=n):
                result = two.run_two_reel_episode(affine_two_release_case(n))
                final = result['accepted_states'][-1]
                self.assertEqual(result['episode_outcome'],
                                 'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
                self.assertEqual([(event['side'], event['kind']) for event in
                                  result['events']], [('span', 'tension_zero')])
                event = result['events'][0]
                self.assertEqual(event['root_basis'],
                                 'heun_numerical_admissibility')
                self.assertLess(event['bracket_width_s'], 1e-10)
                self.assertGreater(event['lower_value'], 0.)
                self.assertLessEqual(event['upper_value'], 0.)
                self.assertGreater(result['minimum_used_stretch'], 1.)
                self.assertLess(result['maximum_combined_inventory_defect_kg'],
                                1e-10)
                self.assertLess(result['maximum_combined_energy_defect_j'],
                                1e-8)
                self.assertLess(result['maximum_reel_cumulative_energy_defect_j'],
                                1e-8)
                self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'],
                                1e-8)
                self.assertAlmostEqual(final['ends']['left']['reference_length_m'],
                    1-.5*(1/(1.01-.2*final['time_s'])-1/1.01), delta=1e-8)
                self.assertAlmostEqual(final['ends']['right']['reference_length_m'],
                    final['ends']['left']['reference_length_m'], delta=1e-12)
                time_errors.append(abs(final['time_s']-.05))
                initial = result['accepted_states'][0]
                energy_errors.append(abs((final['total_mechanical_energy_j']-
                    initial['total_mechanical_energy_j'])-
                    (exact_mechanical(final['time_s'])-exact_mechanical(0.))))
                drive = sum(end['integrated_drive_work_j']
                            for end in final['ends'].values())
                drive_errors.append(abs(drive-simpson(lambda time:
                    2*affine_exact_reel(time)[3]*affine_exact_reel(time)[2],
                    final['time_s'])))
                heat = sum(end['accumulated_dissipated_energy_j']
                           for end in final['ends'].values())
                def heat_rate(time):
                    _, _, _, _, q, lam = affine_exact_reel(time)
                    return (-q)*(EA-MU*q**2)*(lam-1.01)**2
                heat_errors.append(abs(heat-simpson(heat_rate, final['time_s'])))
        self.assertLess(time_errors[2], time_errors[1])
        self.assertLess(time_errors[1], time_errors[0])
        self.assertLess(time_errors[2], 5e-5)
        for errors, ceiling in ((energy_errors, 1e-9),
                                (drive_errors, 4e-10),
                                (heat_errors, 1e-10)):
            self.assertLess(errors[2], errors[1])
            self.assertLess(errors[1], errors[0])
            self.assertLess(errors[0], ceiling)

    def test_affine_timing_refines_at_fixed_mesh_and_forcing_error_is_separate(self):
        errors = []
        for cfl in (span.CFL_LIMIT, span.CFL_LIMIT/2,
                    span.CFL_LIMIT/4):
            result = two.run_two_reel_episode(
                affine_two_release_case(cfl=cfl))
            errors.append(abs(result['accepted_states'][-1]['time_s']-.05))
        self.assertLess(errors[2], errors[1])
        self.assertLess(errors[1], errors[0])
        # This checks the declared piecewise-linear torque against the exact
        # manufactured forcing without changing the solver time step.
        deviations = []
        for knots in (25, 50, 100):
            history = affine_two_release_case(torque_knots=knots).left.applied_torque_history
            maximum = 0.
            for (ta, va), (tb, vb) in zip(history, history[1:]):
                for fraction in (.25, .5, .75):
                    time = ta+fraction*(tb-ta)
                    linear = va+fraction*(vb-va)
                    maximum = max(maximum, abs(linear-affine_exact_reel(time)[3]))
            deviations.append(maximum)
        self.assertLess(deviations[2], deviations[1])
        self.assertLess(deviations[1], deviations[0])

    def test_winding_port_tension_stop_and_shared_earliest_order(self):
        base = case(duration=.02)
        right = replace(base.right,
            applied_torque_history=((0., -.1), (.02, -.1)))
        event_case = replace(base, right=right,
            event_policy='stop_at_numerical_admissibility_limit')
        result = two.run_two_reel_episode(event_case)
        self.assertEqual([(event['side'], event['kind']) for event in
                          result['events']], [('span', 'tension_zero')])
        event = result['events'][0]
        self.assertEqual(event['limit_source'], 'predictor_stage')
        self.assertEqual(event['localized_upper_stage_location'], 'right_port')
        self.assertGreater(result['minimum_used_stretch'], 1.)
        self.assertLess(result['maximum_combined_energy_defect_j'], 1e-8)
        cut = base.left.initial_local_cut_m
        boundary = cut+.001037
        left = replace(base.left, initial_records=(
            one.WoundRecord(boundary, cut+1., 1.02),
            one.WoundRecord(cut, boundary, 1.01)))
        donor_first = two.run_two_reel_episode(replace(event_case, left=left))
        self.assertEqual([(event['side'], event['kind']) for event in
                          donor_first['events']], [('left', 'donor_boundary')])
        tension_first = two.run_two_reel_episode(replace(event_case,
            left=left, right=replace(right,
                applied_torque_history=((0., -1.), (.02, -1.)))))
        self.assertEqual([(event['side'], event['kind']) for event in
                          tension_first['events']], [('span', 'tension_zero')])

    def test_tension_stop_reflects_and_initial_proximity_is_finite(self):
        base = case(duration=.02)
        right = replace(base.right,
            applied_torque_history=((0., -.1), (.02, -.1)))
        original = two.run_two_reel_episode(replace(base, right=right,
            event_policy='stop_at_numerical_admissibility_limit'))
        mirror = case(duration=.02, reflected=True)
        left = replace(mirror.left,
            applied_torque_history=((0., -.1), (.02, -.1)))
        reflected = two.run_two_reel_episode(replace(mirror, left=left,
            event_policy='stop_at_numerical_admissibility_limit'))
        self.assertAlmostEqual(original['accepted_states'][-1]['time_s'],
                               reflected['accepted_states'][-1]['time_s'],
                               delta=1e-11)
        self.assertEqual(original['events'][0]['localized_upper_stage_location'],
                         'right_port')
        self.assertEqual(reflected['events'][0]['localized_upper_stage_location'],
                         'left_port')
        outgoing = SPEED-10*STRETCH
        surface_speed = outgoing+10*(1+5e-13)
        near = replace(base, right=replace(base.right,
            initial_omega_rad_s=surface_speed/geometry(1.)[0]),
            event_policy='stop_at_numerical_admissibility_limit')
        result = two.run_two_reel_episode(near)
        self.assertEqual(result['accepted_states'][-1]['time_s'], 0.)
        self.assertGreater(result['minimum_used_stretch'], 1.)
        self.assertEqual(result['events'][0]['root_basis'],
                         'accepted_state_tautness_proximity')
        self.assertEqual(result['events'][0]['location'], 'right_port')
        self.assertIsNone(result['events'][0]['bracket_time_s'])
        self.assertEqual(len(result['accepted_states']), 1)

    def test_joint_donor_limits_distinguish_overlap_near_and_ordered(self):
        base = affine_two_release_case()
        cut = base.left.initial_local_cut_m
        def end(delta):
            boundary = cut+.001+delta
            return replace(base.left, initial_records=(
                one.WoundRecord(boundary, cut+1., 1.02),
                one.WoundRecord(cut, boundary, 1.01)))
        simultaneous = two.run_two_reel_episode(replace(base,
            left=end(0.), right=end(0.)))
        self.assertEqual([(item['side'], item['bracket_relation_to_selected'])
            for item in simultaneous['events']],
            [('left', 'selected_lowest_feasible_bracket'),
             ('right', 'overlapping_brackets')])
        near = two.run_two_reel_episode(replace(base,
            left=end(0.), right=end(5e-11)))
        self.assertEqual([(item['side'], item['bracket_relation_to_selected'])
            for item in near['events']],
            [('left', 'selected_lowest_feasible_bracket'),
             ('right', 'within_numerical_coincidence_tolerance')])
        self.assertGreater(near['events'][1]['corrected_margin_at_shared_stop'], 0.)
        self.assertEqual(near['events'][1]['grouping_interpretation'],
                         'numerical_only_not_physical_simultaneity')
        ordered = two.run_two_reel_episode(replace(base,
            left=end(0.), right=end(5e-8)))
        self.assertEqual([(item['side'], item['kind']) for item in
                          ordered['events']], [('left', 'donor_boundary')])
        reflected = two.run_two_reel_episode(replace(base,
            left=end(5e-11), right=end(0.)))
        self.assertEqual([(item['side'], item['selection_role'],
                           item['bracket_relation_to_selected'])
                          for item in reflected['events']],
                         [('left', 'grouped_candidate',
                           'within_numerical_coincidence_tolerance'),
                          ('right', 'selected_lowest_feasible_bracket',
                           'selected_lowest_feasible_bracket')])

    def test_supported_donor_stop_matches_independent_label_oracle(self):
        for reflected in (False, True):
            for n in (64, 128, 256):
                with self.subTest(reflected=reflected, cells=n):
                    base = case(n, duration=.02, reflected=reflected)
                    side = 'right' if reflected else 'left'
                    release = getattr(base, side)
                    cut = release.initial_local_cut_m
                    boundary = cut+.001037
                    record = (
                        one.WoundRecord(boundary, cut+1., 1.02),
                        one.WoundRecord(cut, boundary, 1.01))
                    episode = replace(base, **{side: replace(release,
                        initial_records=record)},
                        event_policy='stop_at_numerical_admissibility_limit')
                    result = two.run_two_reel_episode(episode)
                    final = result['accepted_states'][-1]
                    self.assertEqual(result['episode_outcome'],
                                     'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
                    self.assertEqual(len(result['events']), 1)
                    event = result['events'][0]
                    self.assertEqual((event['side'], event['kind']),
                                     (side, 'donor_boundary'))
                    self.assertAlmostEqual(event['boundary'], boundary)
                    self.assertEqual(event['event_time_interpretation'],
                                     'numerical_bracket_not_physical_event_time')
                    # Constant manufactured outward release flux is -0.1 m/s.
                    self.assertAlmostEqual(final['time_s'], .001037/.1,
                                           delta=2e-8)
                    self.assertLess(event['bracket_width_s'], 1e-11)
                    self.assertLess(final['ends'][side]['local_cut_label_m'],
                                    boundary)
                    self.assertEqual(final['ends'][side][
                        'ordered_wound_records'][1]['retained_stretch'], 1.01)
                    self.assertLess(result['maximum_combined_inventory_defect_kg'],
                                    1e-10)
                    self.assertLess(result['maximum_combined_energy_defect_j'],
                                    1e-8)

    def test_reversal_stop_is_one_sided_and_energy_defect_refines(self):
        defects = []
        times = []
        for n in (64, 128, 256):
            base = case(n, duration=.02)
            episode = replace(base, left=replace(base.left,
                applied_torque_history=((0., 1.), (.02, 1.))),
                event_policy='stop_at_numerical_admissibility_limit')
            result = two.run_two_reel_episode(episode)
            self.assertEqual(result['episode_outcome'],
                             'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
            self.assertEqual([(event['side'], event['kind'])
                              for event in result['events']],
                             [('left', 'reversal')])
            event = result['events'][0]
            self.assertEqual(event['limit_source'], 'predictor_stage')
            self.assertEqual(event['event_time_interpretation'],
                             'numerical_bracket_not_physical_event_time')
            final = result['accepted_states'][-1]
            self.assertLess(final['ends']['left']['angular_speed_rad_s'], 0)
            self.assertLess(event['bracket_width_s'], 1e-11)
            defects.append(result['maximum_combined_energy_defect_j'])
            times.append(final['time_s'])
        self.assertLess(defects[2], defects[1])
        self.assertLess(defects[1], defects[0])
        self.assertLess(max(times)-min(times), 1e-8)
        # This defect is numerical FV energy loss, not calibrated dissipation.
        self.assertGreater(defects[0], 1e-8)

    def test_donor_limit_on_forcing_knot_uses_accepted_state_proximity(self):
        base = case(duration=.02)
        cut = base.left.initial_local_cut_m
        left = replace(base.left, initial_records=(
            one.WoundRecord(cut+.0005, cut+1., 1.02),
            one.WoundRecord(cut, cut+.0005, 1.01)))
        result = two.run_two_reel_episode(replace(base, left=left,
            event_policy='stop_at_numerical_admissibility_limit'))
        self.assertEqual(result['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertAlmostEqual(result['accepted_states'][-1]['time_s'], .005,
                               delta=1e-10)
        self.assertEqual(result['events'][0]['root_basis'],
                         'accepted_state_label_proximity')
        self.assertIsNone(result['events'][0]['bracket_time_s'])

    def test_constant_flow_and_independent_component_oracles(self):
        for n in (64, 128, 256):
            with self.subTest(cells=n):
                result = two.run_two_reel_episode(case(n))
                final = result['accepted_states'][-1]
                self.assertEqual(result['episode_outcome'],
                                 'COMPLETED_DECLARED_DURATION')
                self.assertAlmostEqual(final['ends']['left']['reference_length_m'],
                                       .99, delta=2e-9)
                self.assertAlmostEqual(final['ends']['right']['reference_length_m'],
                                       1.01, delta=2e-9)
                self.assertAlmostEqual(final['ends']['left'][
                    'accumulated_dissipated_energy_j'], 4.049595e-6, delta=2e-10)
                self.assertAlmostEqual(final['ends']['right'][
                    'accumulated_dissipated_energy_j'], 0., delta=1e-13)
                self.assertAlmostEqual(final['ends']['left'][
                    'owned_wound_strain_energy_j']-.0005, -5e-6, delta=1e-10)
                self.assertAlmostEqual(final['ends']['right'][
                    'owned_wound_strain_energy_j']-5e-6, 5e-8, delta=1e-10)
                self.assertLess(result['maximum_combined_inventory_defect_kg'], 1e-10)
                self.assertLess(result['maximum_combined_energy_defect_j'], 1e-8)
                self.assertLess(result['maximum_reel_cumulative_energy_defect_j'], 1e-8)
                self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'], 1e-8)
                for side, q, wound_speed in (('left', -.1, -.101),
                                              ('right', .1, SPEED)):
                    exact_omega = wound_speed/geometry(1+q*.1)[0]
                    end = final['ends'][side]
                    self.assertAlmostEqual(end['angular_speed_rad_s'], exact_omega,
                                           delta=2e-9)
                    # Independent Simpson integral of manufactured torque power.
                    intervals = 1000
                    step = .1/intervals
                    work = sum((1 if k in (0, intervals) else
                                (4 if k%2 else 2))*exact_torque(side, k*step)*
                               wound_speed/geometry(1+q*k*step)[0]
                               for k in range(intervals+1))*step/3
                    self.assertAlmostEqual(end['integrated_drive_work_j'], work,
                                           delta=1e-9)
                    initial_momentum = geometry(1.)[1]*wound_speed/geometry(1.)[0]
                    expected_impulse = (geometry(1+q*.1)[1]*exact_omega-
                                        initial_momentum)
                    self.assertAlmostEqual(end['integrated_angular_rhs_nm_s'],
                                           expected_impulse, delta=1e-9)

    def test_reflection_swaps_local_ends_and_global_momentum(self):
        original = two.run_two_reel_episode(case())
        mirror = two.run_two_reel_episode(case(reflected=True))
        a, b = original['accepted_states'][-1], mirror['accepted_states'][-1]
        self.assertAlmostEqual(a['span_momentum_kg_m_s'],
                               -b['span_momentum_kg_m_s'], delta=1e-11)
        self.assertAlmostEqual(a['total_energy_including_dissipation_j'],
                               b['total_energy_including_dissipation_j'], delta=1e-11)
        for old, new in (('left', 'right'), ('right', 'left')):
            for key in ('reference_length_m', 'angular_speed_rad_s',
                        'owned_wound_strain_energy_j',
                        'accumulated_dissipated_energy_j'):
                self.assertAlmostEqual(a['ends'][old][key], b['ends'][new][key],
                                       delta=1e-11)

    def test_output_records_do_not_alias_input_or_prior_states(self):
        episode = case(duration=.02)
        result = two.run_two_reel_episode(episode)
        initial = result['accepted_states'][0]['ends']['left'][
            'ordered_wound_records'][0]
        final = result['accepted_states'][-1]['ends']['left'][
            'ordered_wound_records'][0]
        final['retained_stretch'] = 1.02
        self.assertEqual(initial['retained_stretch'], 1.01)
        self.assertEqual(episode.left.initial_records[0].retained_stretch, 1.01)

    def test_observation_cadence_and_cfl_refinement(self):
        base = two.run_two_reel_episode(case())
        sampled = two.run_two_reel_episode(case(observation_times=(.01, .04, .07)))
        self.assertEqual(base['accepted_states'], sampled['accepted_states'])
        refined = two.run_two_reel_episode(case(cfl=span.CFL_LIMIT/2))
        self.assertLess(refined['maximum_combined_energy_defect_j'], 1e-8)
        self.assertAlmostEqual(base['accepted_states'][-1]['ends']['left'][
            'angular_speed_rad_s'], refined['accepted_states'][-1]['ends']['left'][
            'angular_speed_rad_s'], delta=2e-7)

    def test_torque_perturbation_changes_both_predicted_reels(self):
        base = two.run_two_reel_episode(case(duration=.16))
        changed = two.run_two_reel_episode(case(duration=.16, bump=.001))
        before = lambda output, t: min(output['accepted_states'],
                                        key=lambda state: abs(state['time_s']-t))
        self.assertGreater(abs(before(changed, .05)['ends']['left'][
            'angular_speed_rad_s']-before(base, .05)['ends']['left'][
            'angular_speed_rad_s']), 1e-5)
        self.assertGreater(abs(before(changed, .15)['ends']['right'][
            'angular_speed_rad_s']-before(base, .15)['ends']['right'][
            'angular_speed_rad_s']), 1e-8)
        self.assertLess(abs(before(changed, .08)['ends']['right'][
            'angular_speed_rad_s']-before(base, .08)['ends']['right'][
            'angular_speed_rad_s']), 1e-9)

    def test_dynamic_opposite_reel_response_refines_in_space_and_time(self):
        def response(n, cfl):
            baseline = two.run_two_reel_episode(case(n, duration=.16, cfl=cfl))
            forced = two.run_two_reel_episode(case(n, duration=.16,
                                                    bump=.001, cfl=cfl))
            def at(output):
                return min(output['accepted_states'],
                           key=lambda state: abs(state['time_s']-.12))
            self.assertAlmostEqual(at(baseline)['time_s'], .12, delta=1e-10)
            self.assertAlmostEqual(at(forced)['time_s'], .12, delta=1e-10)
            return (at(forced)['ends']['right']['angular_speed_rad_s']-
                    at(baseline)['ends']['right']['angular_speed_rad_s'])
        spatial = [response(n, span.CFL_LIMIT) for n in (64, 128, 256)]
        temporal = [spatial[0]] + [response(64, cfl) for cfl in
                                   (span.CFL_LIMIT/2, span.CFL_LIMIT/4)]
        self.assertLess(abs(spatial[2]-spatial[1]),
                        abs(spatial[1]-spatial[0]))
        self.assertLess(abs(temporal[2]-temporal[1]),
                        abs(temporal[1]-temporal[0]))

    def test_label_and_phase_guards(self):
        good = case()
        with self.assertRaisesRegex(ValueError, 'cuts'):
            two.TwoReelEpisode(**{**good.__dict__, 'right':
                two.ReelEnd(1.01, 1., good.right.initial_omega_rad_s,
                            (one.WoundRecord(1.01, 2.01, STRETCH),),
                            good.right.applied_torque_history, 'wind')})
        wrong = two.ReelEnd(good.left.initial_local_cut_m, 1.,
                            -good.left.initial_omega_rad_s,
                            good.left.initial_records,
                            good.left.applied_torque_history, 'wind')
        # The invalid phase is rejected at construction rather than committed.
        with self.assertRaises(ValueError):
            two.TwoReelEpisode(**{**good.__dict__, 'left':
                two.ReelEnd(wrong.initial_local_cut_m, 1.,
                            -wrong.initial_omega_rad_s, wrong.initial_records,
                            wrong.applied_torque_history, 'wind')})
        with self.assertRaisesRegex(ValueError, 'linear torque'):
            two.TwoReelEpisode(**{**good.__dict__, 'left':
                replace(good.left, applied_torque_history=(
                    (0., .001, 1e9), (.1, .001, -1e9)))})

    def test_unresolved_donor_and_reversal_are_rejected(self):
        base = case(duration=.02)
        cut = base.left.initial_local_cut_m
        left = replace(base.left, initial_records=(
            one.WoundRecord(cut+.0005, cut+1., 1.02),
            one.WoundRecord(cut, cut+.0005, 1.01)))
        with self.assertRaisesRegex(ValueError, 'donor boundary'):
            two.run_two_reel_episode(replace(base, left=left))
        left = replace(base.left, applied_torque_history=((0., 1.),
                                                           (.02, 1.)))
        with self.assertRaisesRegex(ValueError, 'phase reversal'):
            two.run_two_reel_episode(replace(base, left=left))
        left = replace(base.left, applied_torque_history=((0., -.1),
                                                           (.02, -.1)))
        with self.assertRaisesRegex(ValueError, 'tension zero'):
            two.run_two_reel_episode(replace(base, left=left))


if __name__ == '__main__':
    unittest.main()
