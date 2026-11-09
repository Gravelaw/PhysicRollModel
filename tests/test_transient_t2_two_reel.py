"""Independent constant-flow, reflection, and two-drive checks for T2."""

import math
import bisect
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


def exact_torque(side, t, bump=0., initial_length=1.):
    q = -.1 if side == 'left' else .1
    outward_speed = -SPEED if side == 'left' else SPEED
    wound_speed = -.101 if side == 'left' else SPEED
    length = initial_length+q*t
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


def depletion_case(count=64, reflected=False, policy=
                   'stop_at_numerical_admissibility_limit'):
    """Manufactured constant flux with a finite release record ending at .01037 s."""
    duration, initial_length = .02, .001037
    base = case(count, duration=duration, reflected=reflected)
    side = 'right' if reflected else 'left'
    end = getattr(base, side)
    cut = end.initial_local_cut_m
    history = tuple((i*duration/100,
        exact_torque('left', i*duration/100,
                     initial_length=initial_length)) for i in range(101))
    short_end = replace(end, initial_reference_length_m=initial_length,
        initial_omega_rad_s=-.101/geometry(initial_length)[0],
        initial_records=(one.WoundRecord(cut, cut+initial_length, 1.01),),
        applied_torque_history=history)
    return replace(base, **{side: short_end, 'event_policy': policy})


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


def standing_reversal_exact(time):
    """Independent symmetric material wave and required winding torque."""
    lam0, delta, k, t_star = 1.01, .001, math.pi/2, .02
    theta = 10*k*(time-t_star)
    cut = .5/lam0
    for _ in range(12):
        stretch = lam0+delta*math.cos(k*cut)*math.cos(theta)
        position = lam0*cut+delta/k*math.sin(k*cut)*math.cos(theta)
        cut -= (position-.5)/stretch
    stretch = lam0+delta*math.cos(k*cut)*math.cos(theta)
    speed = -delta*10*math.sin(k*cut)*math.sin(theta)
    speed_time = -delta*100*k*math.sin(k*cut)*math.cos(theta)
    speed_label = -delta*10*k*math.cos(k*cut)*math.sin(theta)
    acceleration = speed_time-speed/stretch*speed_label
    initial_cut = .4946292091008748
    length = 1+initial_cut-cut
    radius, inertia = geometry(length)
    flux = speed/stretch
    radius_rate = .001/math.pi*flux/(2*radius)
    omega = speed/radius
    torque = (inertia*(acceleration/radius-speed*radius_rate/radius**2)+
              radius*EA*(stretch-1))
    return cut, length, omega, torque, stretch


def standing_reversal_case(count=64, cfl=span.CFL_LIMIT, torque_knots=400):
    """Cell-average FV fields integrate the exact material-label wave."""
    lam0, delta, k, theta = 1.01, .001, math.pi/2, -math.pi/10
    def label(position):
        value = position/lam0
        for _ in range(12):
            stretch = lam0+delta*math.cos(k*value)*math.cos(theta)
            x = lam0*value+delta/k*math.sin(k*value)*math.cos(theta)
            value -= (x-position)/stretch
        return value
    fields = []
    for index in range(count):
        low = label(index/count-.5)
        high = label((index+1)/count-.5)
        reference_per_x = count*(high-low)
        momentum_per_x = (MU*count*delta*10/k*math.sin(theta)*
                          (math.cos(k*high)-math.cos(k*low)))
        fields.append((reference_per_x, momentum_per_x))
    cut = standing_reversal_exact(0.)[0]
    history = tuple((index*.04/torque_knots,
        standing_reversal_exact(index*.04/torque_knots)[3])
        for index in range(torque_knots+1))
    end = two.ReelEnd(cut, 1., standing_reversal_exact(0.)[2],
        (one.WoundRecord(cut, cut+1., 1.0106781479918503),),
        history, 'wind')
    return two.TwoReelEpisode(count, .04, tuple(fields), end, end,
        cfl_limit=cfl, event_policy='stop_at_numerical_admissibility_limit')


def isolated_donor_case(count=64, reflected=False, cfl=span.CFL_LIMIT,
                        new_stretch=1.02, torque_knots=100):
    base = case(count, duration=.04, reflected=reflected, cfl=cfl)
    release_side = 'right' if reflected else 'left'
    ends = {}
    for side in ('left', 'right'):
        physical = ({'left': 'right', 'right': 'left'}[side]
                    if reflected else side)
        end = getattr(base, side)
        history = tuple((index*.04/torque_knots,
            exact_torque(physical, index*.04/torque_knots))
            for index in range(torque_knots+1))
        if side == release_side:
            cut = end.initial_local_cut_m
            boundary = cut+.0037
            end = replace(end, initial_records=(
                one.WoundRecord(boundary, cut+1., new_stretch),
                one.WoundRecord(cut, boundary, 1.01)))
        ends[side] = replace(end, applied_torque_history=history)
    return replace(base, **ends, event_policy=two.CONTINUE_ISOLATED_DONOR)


def independent_post_donor_ode(history, step_s=5e-6):
    """RK4 reel reference with a constant outgoing wave and new donor."""
    time0, time1 = .037, .04
    length0 = 1-.0037
    radius0, _ = geometry(length0)
    state = (length0, -.101/radius0, 0., 0., 0.)
    def rates(time, values):
        length, omega, _, _, _ = values
        radius, inertia = geometry(length)
        q = radius*omega/1.02
        stretch = -10.1101/(q-10)
        speed = q*stretch
        tension = EA*(stretch-1)
        index = bisect.bisect_right(history, (time, math.inf))-1
        index = min(index, len(history)-2)
        low_time, low_torque = history[index]
        high_time, high_torque = history[index+1]
        torque = low_torque+(high_torque-low_torque)*(
            time-low_time)/(high_time-low_time)
        angular_rhs = torque-radius*tension+MU*q*radius*speed
        omega_rate = (angular_rhs-MU*q*radius**2*omega)/inertia
        heat_rate = (-q)*(EA-MU*q*q)*(stretch-1.02)**2/2
        return q, omega_rate, torque*omega, heat_rate, angular_rhs
    count = round((time1-time0)/step_s)
    h = (time1-time0)/count
    for index in range(count):
        time = time0+index*h
        first = rates(time, state)
        second = rates(time+h/2, tuple(
            state[j]+h*first[j]/2 for j in range(5)))
        third = rates(time+h/2, tuple(
            state[j]+h*second[j]/2 for j in range(5)))
        fourth = rates(time+h, tuple(
            state[j]+h*third[j] for j in range(5)))
        state = tuple(state[j]+h*(first[j]+2*second[j]+2*third[j]+fourth[j])/6
                      for j in range(5))
    return state


class TwoReelTests(unittest.TestCase):
    def test_isolated_donor_rejects_unresolved_absolute_labels(self):
        left_cut, right_cut = -1e6, 1e6+.625
        boundary = left_cut+.0001
        fields = tuple(span._conserved(1.6,
            -.2*((index+.5)/64-.5)/1.6) for index in range(64))
        radius, _ = geometry(1.)
        left = two.ReelEnd(left_cut, 1., -.0625/radius, (
            one.WoundRecord(boundary, left_cut+1., 1.7),
            one.WoundRecord(left_cut, boundary, 1.6)),
            ((0., 0.), (.005, 0.)), 'release')
        right = two.ReelEnd(right_cut, 1., -.0625/radius,
            (one.WoundRecord(right_cut, right_cut+1., 1.6),),
            ((0., 0.), (.005, 0.)), 'release')
        episode = two.TwoReelEpisode(64, .005, fields, left, right,
            event_policy=two.CONTINUE_ISOLATED_DONOR)
        result = two.run_two_reel_episode(episode)
        self.assertEqual(result['transitions'], [])
        self.assertEqual(result['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'insufficient_terminal_label_resolution')

    def test_isolated_donor_groups_competitor_across_torque_knot(self):
        base = affine_two_release_case()
        reference = two.run_two_reel_episode(base)
        at_knot = min(reference['accepted_states'],
                      key=lambda state: abs(state['time_s']-.011))
        self.assertAlmostEqual(at_knot['time_s'], .011, delta=1e-12)
        ends = {}
        for side, offset in (('left', -2e-11), ('right', 2e-11)):
            original = getattr(base, side)
            cut = original.initial_local_cut_m
            boundary = at_knot['ends'][side]['local_cut_label_m']+offset
            ends[side] = replace(original, initial_records=(
                one.WoundRecord(boundary, cut+1., 1.01),
                one.WoundRecord(cut, boundary, 1.01)))
        result = two.run_two_reel_episode(replace(base, **ends,
            event_policy=two.CONTINUE_ISOLATED_DONOR))
        self.assertEqual(result['transitions'], [])
        self.assertEqual(result['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'competing_numerical_limit_within_tolerance')

    def test_isolated_donor_lookahead_resolves_interior_torque_pulse(self):
        base = isolated_donor_case(new_stretch=1.01)
        history = tuple(sorted(base.right.applied_torque_history+(
            (.037+2e-10, exact_torque('right', .037+2e-10)),
            (.037+4e-10, -1e8),
            (.037+8e-10, exact_torque('right', .037+8e-10)))))
        result = two.run_two_reel_episode(replace(base,
            right=replace(base.right, applied_torque_history=history)))
        self.assertEqual(result['transitions'], [])
        self.assertEqual(result['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'competing_numerical_limit_within_tolerance')

    def test_isolated_donor_bounds_large_stored_energy_jump(self):
        result = two.run_two_reel_episode(
            isolated_donor_case(new_stretch=1e6))
        self.assertEqual(result['transitions'], [])
        self.assertEqual(result['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'storage_ownership_residual_exceeded')

    def test_isolated_donor_restart_preserves_split_material_identity(self):
        for count in (64, 128, 256):
            for reflected in (False, True):
                with self.subTest(cells=count, reflected=reflected):
                    split = isolated_donor_case(
                        count, reflected=reflected, new_stretch=1.01)
                    side = 'right' if reflected else 'left'
                    unsplit = replace(split, **{side: getattr(
                        case(count, duration=.04, reflected=reflected), side)})
                    a = two.run_two_reel_episode(unsplit)
                    b = two.run_two_reel_episode(split)
                    self.assertEqual(a['episode_outcome'],
                                     'COMPLETED_DECLARED_DURATION')
                    self.assertEqual(b['episode_outcome'],
                                     'COMPLETED_DECLARED_DURATION')
                    self.assertEqual(len(b['transitions']), 1)
                    transition = b['transitions'][0]
                    self.assertEqual((transition['side'], transition['kind']),
                                     (side, 'internal_donor_restart'))
                    self.assertAlmostEqual(transition['accepted_time_s'],
                                           .037, delta=2e-11)
                    self.assertLessEqual(transition['terminal_label_overshoot_m'],
                                         two.DONOR_RESTART_MAX_OVERSHOOT_M)
                    self.assertAlmostEqual(transition['terminal_inventory_overshoot_m'],
                        transition['terminal_label_overshoot_m'], delta=1e-14)
                    self.assertEqual(transition[
                        'signed_storage_ownership_residual_j'], 0.)
                    self.assertEqual(transition['old_donor'][
                        'retained_stretch'], 1.01)
                    self.assertEqual(transition['new_donor'][
                        'retained_stretch'], 1.01)
                    final_a, final_b = (result['accepted_states'][-1]
                                        for result in (a, b))
                    for key in ('span_mass_kg', 'span_momentum_kg_m_s',
                                'total_mechanical_energy_j'):
                        self.assertAlmostEqual(final_a[key], final_b[key],
                                               delta=1e-12)
                    for end_side in ('left', 'right'):
                        for key in ('reference_length_m',
                                    'angular_speed_rad_s',
                                    'owned_wound_strain_energy_j'):
                            self.assertAlmostEqual(final_a['ends'][end_side][key],
                                final_b['ends'][end_side][key], delta=1e-12)
                    self.assertEqual(len(final_b['ends'][side][
                        'ordered_wound_records']), 2)
                    self.assertLess(b['maximum_combined_inventory_defect_kg'],
                                    1e-11)

    def test_unequal_donor_restart_matches_jump_and_independent_reel_ode(self):
        base = isolated_donor_case()
        history = base.left.applied_torque_history
        coarse = independent_post_donor_ode(history, 1e-5)
        reference = independent_post_donor_ode(history, 5e-6)
        self.assertLess(abs(coarse[1]-reference[1]), 1e-11)
        self.assertLess(abs(coarse[2]-reference[2]), 1e-12)
        omega_errors = []
        energy_defects = []
        for count in (64, 128, 256):
            result = two.run_two_reel_episode(isolated_donor_case(count))
            self.assertEqual(result['episode_outcome'],
                             'COMPLETED_DECLARED_DURATION')
            self.assertEqual(len(result['transitions']), 1)
            transition = result['transitions'][0]
            post = transition['new_port']
            self.assertAlmostEqual(post['reference_flux_m_s'],
                -.09901960784313726, delta=2e-12)
            self.assertAlmostEqual(post['stretch'],
                1.00109717503155, delta=2e-12)
            self.assertAlmostEqual(post['outward_span_speed_m_s'],
                -.09912824968449663, delta=2e-12)
            self.assertAlmostEqual(post['tension_n'],
                .01097175031550046, delta=2e-11)
            self.assertAlmostEqual(post['dissipated_power_w'],
                .0001768894974844970, delta=2e-12)
            self.assertAlmostEqual(transition['old_port'][
                'reference_flux_m_s'], -.1, delta=2e-12)
            delta = transition['terminal_inventory_overshoot_m']
            expected_residual = delta*EA/2*((1.01-1)**2-(1.02-1)**2)
            self.assertAlmostEqual(transition[
                'signed_storage_ownership_residual_j'],
                expected_residual, delta=1e-18)
            self.assertLessEqual(abs(expected_residual),
                transition['absolute_storage_ownership_residual_bound_j']+1e-18)
            final = result['accepted_states'][-1]['ends']['left']
            at_switch = result['accepted_states'][transition[
                'accepted_state_index']]['ends']['left']
            self.assertAlmostEqual(final['reference_length_m'], reference[0],
                                   delta=1e-10)
            omega_errors.append(abs(final['angular_speed_rad_s']-reference[1]))
            for key, expected in (
                    ('integrated_drive_work_j', reference[2]),
                    ('accumulated_dissipated_energy_j', reference[3]),
                    ('integrated_angular_rhs_nm_s', reference[4])):
                self.assertAlmostEqual(final[key]-at_switch[key], expected,
                                       delta=1e-11)
            self.assertLess(result['maximum_combined_inventory_defect_kg'], 1e-11)
            energy_defects.append(result['maximum_combined_energy_defect_j'])
        self.assertLess(omega_errors[2], omega_errors[1])
        self.assertLess(omega_errors[1], omega_errors[0])
        self.assertLess(energy_defects[2], energy_defects[1])
        self.assertLess(energy_defects[1], energy_defects[0])
        self.assertLess(energy_defects[2], 1e-8)

    def test_isolated_donor_restart_refines_time_and_declared_torque(self):
        reference = independent_post_donor_ode(
            isolated_donor_case().left.applied_torque_history)
        errors = []
        for cfl in (span.CFL_LIMIT, span.CFL_LIMIT/2, span.CFL_LIMIT/4):
            result = two.run_two_reel_episode(isolated_donor_case(cfl=cfl))
            errors.append(abs(result['accepted_states'][-1]['ends']['left'][
                'angular_speed_rad_s']-reference[1]))
        self.assertLess(errors[2], errors[1])
        self.assertLess(errors[1], errors[0])
        work = []
        for knots in (2, 4, 8, 40):
            episode = isolated_donor_case(torque_knots=knots)
            result = two.run_two_reel_episode(episode)
            self.assertEqual(result['episode_outcome'],
                             'COMPLETED_DECLARED_DURATION')
            self.assertEqual(len(result['transitions']), 1)
            self.assertLessEqual(result['transitions'][0][
                'terminal_label_overshoot_m'],
                two.DONOR_RESTART_MAX_OVERSHOOT_M)
            reference_run = independent_post_donor_ode(
                episode.left.applied_torque_history)
            switch = result['accepted_states'][result['transitions'][0][
                'accepted_state_index']]['ends']['left']
            final = result['accepted_states'][-1]['ends']['left']
            self.assertAlmostEqual(final['integrated_drive_work_j']-
                switch['integrated_drive_work_j'], reference_run[2], delta=1e-11)
            work.append(reference_run[2])
        fine_work = independent_post_donor_ode(
            isolated_donor_case(torque_knots=100).left.applied_torque_history)[2]
        self.assertLess(abs(work[2]-fine_work), abs(work[1]-fine_work))
        self.assertLess(abs(work[1]-fine_work), abs(work[0]-fine_work))

    def test_isolated_donor_restart_rejects_slack_new_trace(self):
        lam, speed, duration = 1.00001, .100001, .003
        base = case(duration=duration)
        cut = 1/lam-1
        radius, inertia = geometry(1.)
        kappa = .001/math.pi
        def torque(q, port_speed, wound_speed):
            radius_rate = kappa*q/(2*radius)
            omega_rate = -wound_speed*radius_rate/radius**2
            return (inertia*omega_rate+radius*EA*(lam-1)-
                    MU*q*radius*(port_speed-wound_speed))
        left_torque = torque(-.1, -speed, -.102)
        right_torque = torque(.1, speed, speed)
        left = replace(base.left, initial_local_cut_m=cut,
            initial_omega_rad_s=-.102/radius,
            initial_records=(
                one.WoundRecord(cut+.0001, cut+1., 1.000001),
                one.WoundRecord(cut, cut+.0001, 1.02)),
            applied_torque_history=((0., left_torque),
                                    (duration, left_torque)))
        right = replace(base.right, initial_omega_rad_s=speed/radius,
            applied_torque_history=((0., right_torque),
                                    (duration, right_torque)))
        episode = replace(base, left=left, right=right,
            initial_conserved_fields=tuple(span._conserved(lam, speed)
                                           for _ in range(64)),
            event_policy=two.CONTINUE_ISOLATED_DONOR)
        result = two.run_two_reel_episode(episode)
        self.assertEqual(result['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertEqual(result['transitions'], [])
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'new_donor_trace_inadmissible')
        self.assertGreater(result['minimum_used_stretch'], 1.)
        self.assertLess(result['accepted_states'][-1]['time_s'], .001)

    def test_isolated_donor_restart_keeps_competing_and_thin_stops(self):
        base = case(duration=.04)
        cut = base.left.initial_local_cut_m
        boundary = cut+.0037
        thin = replace(base.left, initial_records=(
            one.WoundRecord(boundary+1e-15, cut+1., 1.03),
            one.WoundRecord(boundary, boundary+1e-15, 1.02),
            one.WoundRecord(cut, boundary, 1.01)))
        result = two.run_two_reel_episode(replace(base, left=thin,
            event_policy=two.CONTINUE_ISOLATED_DONOR))
        self.assertEqual(result['transitions'], [])
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'next_donor_interval_skipped')
        self.assertLess(result['accepted_states'][-1]['ends']['left'][
            'local_cut_label_m'], boundary)

        base = affine_two_release_case(duration=.04)
        cut = base.left.initial_local_cut_m
        boundary = cut+.002
        end = replace(base.left, initial_records=(
            one.WoundRecord(boundary, cut+1., 1.02),
            one.WoundRecord(cut, boundary, 1.01)))
        result = two.run_two_reel_episode(replace(base, left=end, right=end,
            event_policy=two.CONTINUE_ISOLATED_DONOR))
        self.assertEqual(result['transitions'], [])
        self.assertEqual([(event['side'], event['kind']) for event in
                          result['events']], [('left', 'donor_boundary'),
                                              ('right', 'donor_boundary')])
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'additional_or_competing_limit')

    def test_isolated_donor_restart_stops_on_second_or_unresolved_arrival(self):
        base = case(duration=.07)
        cut = base.left.initial_local_cut_m
        first, second = cut+.0037, cut+.005
        left = replace(base.left, initial_records=(
            one.WoundRecord(second, cut+1., 1.03),
            one.WoundRecord(first, second, 1.02),
            one.WoundRecord(cut, first, 1.01)))
        result = two.run_two_reel_episode(replace(base, left=left,
            event_policy=two.CONTINUE_ISOLATED_DONOR))
        self.assertEqual(len(result['transitions']), 1)
        self.assertEqual(result['episode_outcome'],
                         'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'additional_or_competing_limit')

        base = case(duration=.02)
        left = replace(base.left, applied_torque_history=((0., 1.),
                                                          (.02, 1.)))
        cut = left.initial_local_cut_m
        boundary = cut+(.00002000000000016+.0000198175861768)/2
        left = replace(left, initial_records=(
            one.WoundRecord(boundary, cut+1., 1.02),
            one.WoundRecord(cut, boundary, 1.01)))
        result = two.run_two_reel_episode(replace(base, left=left,
            event_policy=two.CONTINUE_ISOLATED_DONOR))
        self.assertEqual(result['transitions'], [])
        self.assertEqual(result['events'][0]['restart_attempt_status'],
                         'corrected_endpoint_not_bracketed')

    def test_corrected_reversal_matches_independent_standing_wave(self):
        self.assertAlmostEqual(standing_reversal_exact(.02)[1],
                               1.0000216140997287, delta=1e-14)
        self.assertAlmostEqual(standing_reversal_exact(.02)[3],
                               -.0010607167591660995, delta=1e-14)
        reference_work = sum(
            standing_reversal_exact((index+.5)*.02/2000)[2]*
            standing_reversal_exact((index+.5)*.02/2000)[3]*.02/2000
            for index in range(2000))
        errors = []
        for count in (64, 128, 256):
            result = two.run_two_reel_episode(standing_reversal_case(count))
            self.assertEqual(result['episode_outcome'],
                             'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
            self.assertEqual([(item['side'], item['kind']) for item in
                              result['events']], [('left', 'reversal'),
                                                  ('right', 'reversal')])
            final = result['accepted_states'][-1]
            for event in result['events']:
                self.assertEqual(event['corrected_reversal_status'],
                                 'bracketed_in_complete_trial')
                low, high = event['corrected_reversal_bracket_time_s']
                self.assertLess(high-low, 1e-11)
                self.assertGreater(event['corrected_reversal_lower_margin_rad_s'],
                                   0.)
                self.assertLessEqual(event['corrected_reversal_upper_margin_rad_s'],
                                     0.)
                self.assertAlmostEqual(
                    event['corrected_reversal_gap_after_feasible_stop_s'],
                    low-final['time_s'], delta=1e-14)
                if event['side'] == 'left':
                    errors.append(abs((low+high)/2-.02))
            for side in ('left', 'right'):
                end = final['ends'][side]
                self.assertEqual(end['phase'], 'wind')
                self.assertGreater(end['angular_speed_rad_s'], 0.)
                self.assertAlmostEqual(end['reference_length_m'],
                    standing_reversal_exact(.02)[1], delta=1e-8)
                self.assertAlmostEqual(end['integrated_angular_rhs_nm_s'],
                    -geometry(1.)[1]*standing_reversal_exact(0.)[2],
                    delta=1e-10)
                self.assertAlmostEqual(end['integrated_drive_work_j'],
                    reference_work, delta=5e-12)
                self.assertEqual(end['accumulated_dissipated_energy_j'], 0.)
            self.assertLess(result['maximum_combined_inventory_defect_kg'], 1e-12)
            self.assertLess(result['maximum_combined_energy_defect_j'], 1e-10)
        self.assertLess(errors[2], errors[1])
        self.assertLess(errors[1], errors[0])
        self.assertLess(errors[2], 1e-9)

    def test_corrected_reversal_refines_separately_in_time_and_forcing(self):
        def time_at(cfl, knots):
            result = two.run_two_reel_episode(standing_reversal_case(
                64, cfl=cfl, torque_knots=knots))
            bracket = result['events'][0]['corrected_reversal_bracket_time_s']
            return sum(bracket)/2
        cfl_times = [time_at(cfl, 20) for cfl in
                     (span.CFL_LIMIT, span.CFL_LIMIT/2, span.CFL_LIMIT/4)]
        forcing_times = [time_at(span.CFL_LIMIT, knots) for knots in
                         (100, 200, 400)]
        self.assertLess(abs(cfl_times[2]-cfl_times[1]),
                        abs(cfl_times[1]-cfl_times[0]))
        self.assertLess(abs(forcing_times[2]-forcing_times[1]),
                        abs(forcing_times[1]-forcing_times[0]))

    def test_predictor_reversal_does_not_invent_corrected_root(self):
        duration = .0110198707
        base = case(duration=duration)
        left = replace(base.left, applied_torque_history=((0., 1.),
                                                          (duration, 1.)))
        result = two.run_two_reel_episode(replace(base, left=left,
            event_policy='stop_at_numerical_admissibility_limit'))
        event = result['events'][0]
        self.assertEqual((event['side'], event['kind'], event['limit_source']),
                         ('left', 'reversal', 'predictor_stage'))
        self.assertEqual(event['corrected_reversal_status'],
                         'not_bracketed_in_complete_trial')
        self.assertIsNone(event['corrected_reversal_bracket_time_s'])
        self.assertIsNone(event['corrected_reversal_gap_after_feasible_stop_s'])
        self.assertGreater(event['corrected_reversal_upper_margin_rad_s'], 0.)

    def test_rounded_winding_stage_keeps_one_owned_packet(self):
        for first_flux, second_flux, retained in (
                (1e-17, 2e-13, 1.011),
                (2e-13, 1e-17, 1.01)):
            first = {'port': {'reference_flux_m_s': first_flux,
                              'span_stretch': 1.01}}
            second = {'port': {'reference_flux_m_s': second_flux,
                               'span_stretch': 1.011}}
            packets, discrepancy = one._winding_packets(
                1., 1.-1e-13, 1., first, second)
            self.assertEqual(len(packets), 1)
            self.assertEqual(packets[0].high_label_m, 1.)
            self.assertEqual(packets[0].low_label_m, 1.-1e-13)
            self.assertEqual(packets[0].retained_stretch, retained)
            deposited = EA/2*(packets[0].high_label_m-
                              packets[0].low_label_m)*(retained-1)**2
            stage = EA/2*(first_flux/2*(1.01-1)**2+
                          second_flux/2*(1.011-1)**2)
            self.assertAlmostEqual(discrepancy, deposited-stage,
                                   delta=1e-25)

    def test_corrected_donor_arrival_has_separate_constant_flow_oracle(self):
        for count in (64, 128, 256):
            for reflected in (False, True):
                with self.subTest(cells=count, reflected=reflected):
                    base = case(count, duration=.06, reflected=reflected)
                    side = 'right' if reflected else 'left'
                    release = getattr(base, side)
                    cut = release.initial_local_cut_m
                    boundary = cut+.0037
                    end = replace(release, initial_records=(
                        one.WoundRecord(boundary, cut+1., 1.02),
                        one.WoundRecord(cut, boundary, 1.01)))
                    result = two.run_two_reel_episode(replace(base,
                        **{side: end},
                        event_policy='stop_at_numerical_admissibility_limit'))
                    event = result['events'][0]
                    self.assertEqual((event['side'], event['kind']),
                                     (side, 'donor_boundary'))
                    self.assertEqual(event['corrected_arrival_status'],
                                     'bracketed_in_complete_trial')
                    lower, upper = event['corrected_arrival_bracket_time_s']
                    self.assertLessEqual(lower, upper)
                    self.assertLess(upper-lower, 1e-11)
                    self.assertGreater(event['corrected_arrival_lower_margin_m'],
                                       0.)
                    self.assertLessEqual(event['corrected_arrival_upper_margin_m'],
                                         0.)
                    self.assertAlmostEqual((lower+upper)/2, .037,
                                           delta=2e-8)
                    self.assertLessEqual(result['accepted_states'][-1]['time_s'],
                                         upper)
                    self.assertLess(result['maximum_combined_energy_defect_j'],
                                    1e-8)

    def test_affine_competing_donor_arrival_estimate_uses_corrected_state(self):
        exact_time = (1.01-1/(1/1.01+2*.002))/.2
        def arrival(count, cfl):
            base = affine_two_release_case(count=count, cfl=cfl)
            cut = base.left.initial_local_cut_m
            def end(distance):
                boundary = cut+distance
                return replace(base.left, initial_records=(
                    one.WoundRecord(boundary, cut+1., 1.02),
                    one.WoundRecord(cut, boundary, 1.01)))
            result = two.run_two_reel_episode(replace(base,
                left=end(.002), right=end(.003)))
            event = result['events'][0]
            self.assertEqual((event['side'], event['kind']),
                             ('left', 'donor_boundary'))
            self.assertEqual(event['corrected_arrival_status'],
                             'bracketed_in_complete_trial')
            lower, upper = event['corrected_arrival_bracket_time_s']
            self.assertLessEqual(result['accepted_states'][-1]['time_s'], upper)
            self.assertLess(result['maximum_combined_energy_defect_j'], 1e-8)
            return abs((lower+upper)/2-exact_time)
        spatial = [arrival(n, span.CFL_LIMIT) for n in (64, 128, 256)]
        temporal = [spatial[0]] + [arrival(64, cfl) for cfl in
                                   (span.CFL_LIMIT/2, span.CFL_LIMIT/4)]
        for errors in (spatial, temporal):
            self.assertLess(errors[2], errors[1])
            self.assertLess(errors[1], errors[0])
            self.assertLess(errors[2], 2e-11)

    def test_predictor_to_corrected_donor_gap_shrinks_on_finer_steps(self):
        def gap(cfl):
            base = case(256, duration=.02, cfl=cfl)
            left = replace(base.left, applied_torque_history=((0., 1.),
                                                             (.02, 1.)))
            cut = left.initial_local_cut_m
            boundary = cut+1.9e-5
            left = replace(left, initial_records=(
                one.WoundRecord(boundary, cut+1., 1.02),
                one.WoundRecord(cut, boundary, 1.01)))
            result = two.run_two_reel_episode(replace(base, left=left,
                event_policy='stop_at_numerical_admissibility_limit'))
            event = result['events'][0]
            self.assertEqual(event['limit_source'], 'predictor_stage')
            self.assertEqual(event['corrected_arrival_status'],
                             'bracketed_in_complete_trial')
            self.assertGreater(event['corrected_arrival_gap_after_feasible_stop_s'],
                               0.)
            return event['corrected_arrival_gap_after_feasible_stop_s']
        coarse, fine = gap(span.CFL_LIMIT), gap(span.CFL_LIMIT/4)
        self.assertLess(fine, coarse/4)

    def test_predictor_donor_limit_does_not_invent_corrected_arrival(self):
        base = case(duration=.02)
        left = replace(base.left, applied_torque_history=((0., 1.),
                                                         (.02, 1.)))
        cut = left.initial_local_cut_m
        # The constant-torque first-step predictor advances farther than its
        # corrected endpoint. This label lies strictly between those cuts.
        boundary = cut+(.00002000000000016+.0000198175861768)/2
        left = replace(left, initial_records=(
            one.WoundRecord(boundary, cut+1., 1.02),
            one.WoundRecord(cut, boundary, 1.01)))
        result = two.run_two_reel_episode(replace(base, left=left,
            event_policy='stop_at_numerical_admissibility_limit'))
        event = result['events'][0]
        self.assertEqual((event['side'], event['kind'],
                          event['limit_source']),
                         ('left', 'donor_boundary', 'predictor_stage'))
        self.assertEqual(event['corrected_arrival_status'],
                         'not_bracketed_in_complete_trial')
        self.assertIsNone(event['corrected_arrival_bracket_time_s'])
        self.assertGreater(event['corrected_arrival_upper_margin_m'], 0.)

    def test_depletion_stop_matches_independent_flow_and_energy_oracles(self):
        for count in (64, 128, 256):
            for reflected in (False, True):
                with self.subTest(cells=count, reflected=reflected):
                    result = two.run_two_reel_episode(
                        depletion_case(count, reflected))
                    final = result['accepted_states'][-1]
                    side = 'right' if reflected else 'left'
                    end = final['ends'][side]
                    self.assertEqual(result['episode_outcome'],
                        'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
                    event = result['events'][0]
                    self.assertEqual((event['side'], event['kind']),
                                     (side, 'depletion'))
                    self.assertEqual(event['inventory_stop_threshold_m'], 1e-10)
                    self.assertGreater(event['lower_value'], 0.)
                    self.assertLessEqual(event['upper_value'], 0.)
                    self.assertLess(event['bracket_width_s'], 1e-11)
                    self.assertAlmostEqual(final['time_s'], .01037,
                                           delta=1e-8)
                    self.assertGreater(end['reference_length_m'], 0.)
                    self.assertLess(end['reference_length_m'], 1e-9)
                    self.assertAlmostEqual(end['radius_m'], .1, delta=2e-11)
                    self.assertAlmostEqual(end['inertia_kg_m2'], .01,
                                           delta=2e-12)
                    self.assertAlmostEqual(end['accumulated_dissipated_energy_j'],
                                           4.049595e-5*final['time_s'],
                                           delta=2e-10)
                    self.assertLess(result['maximum_combined_inventory_defect_kg'],
                                    1e-10)
                    self.assertLess(result['maximum_combined_energy_defect_j'],
                                    1e-8)
                    self.assertLess(result['maximum_reel_cumulative_energy_defect_j'],
                                    1e-8)
                    self.assertLess(result['maximum_reel_angular_impulse_defect_nm_s'],
                                    1e-8)
                    self.assertTrue(all(state['ends'][side][
                        'reference_length_m'] > 0 for state in
                        result['accepted_states']))

    def test_depletion_proximity_and_prelimit_duration(self):
        base = depletion_case()
        short = replace(base, duration_s=.005,
            left=replace(base.left, applied_torque_history=
                base.left.applied_torque_history[:26]),
            right=replace(base.right, applied_torque_history=
                base.right.applied_torque_history[:26]))
        complete = two.run_two_reel_episode(short)
        self.assertEqual(complete['episode_outcome'],
                         'COMPLETED_DECLARED_DURATION')
        self.assertEqual(complete['events'], [])
        for near, split in ((5e-11, False), (5e-11, True),
                            (two.DEPLETION_PROXIMITY_M+1e-15, False)):
            with self.subTest(inventory=near, split=split):
                cut = base.left.initial_local_cut_m
                records = ((one.WoundRecord(cut+near/2, cut+near, 1.01),
                            one.WoundRecord(cut, cut+near/2, 1.01)) if split
                           else (one.WoundRecord(cut, cut+near, 1.01),))
                left = replace(base.left, initial_reference_length_m=near,
                    initial_omega_rad_s=-.101/geometry(near)[0],
                    initial_records=records)
                stopped = two.run_two_reel_episode(replace(base, left=left))
                self.assertEqual(stopped['accepted_states'][-1]['time_s'], 0.)
                self.assertEqual(stopped['events'][0]['root_basis'],
                                 'accepted_state_inventory_proximity')
                self.assertEqual(stopped['events'][0]['kind'], 'depletion')
                self.assertIsNone(stopped['events'][0]['bracket_time_s'])

    def test_winding_near_empty_reel_is_not_a_depletion_candidate(self):
        duration, small = 1e-9, 5e-11
        cut_left, cut_right = 1/STRETCH-1, 1.
        ends = {}
        for side, cut, length in (('left', cut_left, 1.),
                                  ('right', cut_right, small)):
            ends[side] = two.ReelEnd(cut, length,
                1e-6/geometry(length)[0],
                (one.WoundRecord(cut, cut+length, STRETCH),),
                ((0., 0.), (duration, 0.)), 'wind')
        base = two.TwoReelEpisode(64, duration,
            tuple(span._conserved(STRETCH, 0.) for _ in range(64)),
            ends['left'], ends['right'],
            event_policy='stop_at_numerical_admissibility_limit')
        result = two.run_two_reel_episode(base)
        self.assertEqual(result['episode_outcome'],
                         'COMPLETED_DECLARED_DURATION')
        self.assertEqual(result['events'], [])
        self.assertGreater(result['accepted_states'][-1]['ends']['right'][
            'reference_length_m'], small)

    def test_depletion_stop_is_insensitive_to_allowed_cfl_choice(self):
        stops = [two.run_two_reel_episode(replace(
            depletion_case(), cfl_limit=cfl))['accepted_states'][-1]['time_s']
            for cfl in (span.CFL_LIMIT, span.CFL_LIMIT/2, span.CFL_LIMIT/4)]
        self.assertLess(max(stops)-min(stops), 1e-8)

    def test_default_policy_rejects_depletion(self):
        with self.assertRaises(ValueError):
            two.run_two_reel_episode(depletion_case(policy='reject'))

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
        for item in near['events']:
            self.assertAlmostEqual(
                item['corrected_arrival_gap_after_feasible_stop_s'],
                item['corrected_arrival_bracket_time_s'][0]-
                near['accepted_states'][-1]['time_s'], delta=1e-15)
        self.assertGreater(near['events'][1][
            'corrected_arrival_gap_after_feasible_stop_s'], 0.)
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
