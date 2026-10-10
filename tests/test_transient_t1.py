"""Independent closed-form checks for bounded prescribed T1 transport."""

from dataclasses import replace
import math
import unittest

from physicroll.run_contract import canonical_json
from physicroll.transient_t1 import T1Episode, T1Trajectory


def episode(**changes):
    baseline = T1Episode(
        times_s=(0.0, 2.0), prescribed_strip_speed_m_s=(0.5, 0.5),
        free_span_length_m=1.0, thickness_m=0.001, width_m=1.0,
        density_kg_m3=1000.0, left_core_radius_m=0.1,
        right_core_radius_m=0.1, left_initial_length_m=3.0,
        right_initial_length_m=1.0,
        parcels=(('left-parcel', -0.25), ('span-parcel', 0.75)),
        transport_roller_radius_m=0.2,
    )
    return replace(baseline, **changes)


class T1TransportTests(unittest.TestCase):
    def test_constant_speed_exact_inventory_radius_angles_mass_and_parcels(self):
        trajectory = T1Trajectory(episode())
        final = trajectory.state_at(2.0)
        self.assertEqual(final['prescribed_displacement_m'], 1.0)
        self.assertEqual(final['left_length_m'], 2.0)
        self.assertEqual(final['right_length_m'], 2.0)
        self.assertAlmostEqual(final['right_radius_m'], math.sqrt(.01 + .002 / math.pi))
        initial = trajectory.state_at(0.0)
        self.assertAlmostEqual(final['right_winding_angle_rad'] -
                               initial['right_winding_angle_rad'],
                               2 * math.pi * (final['right_radius_m'] -
                                              initial['right_radius_m']) / .001)
        self.assertEqual(final['transport_roller_angle_rad'], 5.0)
        self.assertEqual(final['parcels'][0]['owner'], 'free_span')
        self.assertEqual(final['parcels'][1]['owner'], 'right_reel')
        self.assertLess(trajectory.result()['maximum_total_mass_residual_kg'], 1e-12)
        self.assertEqual(trajectory.result()['strip_speed_role'], 'prescribed_input')
        self.assertTrue(canonical_json(trajectory.result()))

    def test_reversal_returns_inventory_and_crosses_same_parcel_twice(self):
        case = episode(times_s=(0.0, 1.0, 2.0),
                       prescribed_strip_speed_m_s=(1.0, 0.0, -1.0))
        trajectory = T1Trajectory(case)
        start, finish = trajectory.state_at(0.0), trajectory.state_at(2.0)
        self.assertEqual(finish['prescribed_displacement_m'], 0.0)
        for key in ('left_length_m', 'right_length_m', 'left_radius_m',
                    'right_radius_m', 'left_winding_angle_rad',
                    'right_winding_angle_rad', 'transport_roller_angle_rad'):
            self.assertAlmostEqual(start[key], finish[key], delta=1e-12)
        self.assertEqual(start['parcels'], finish['parcels'])
        crossings = [item for item in trajectory.events
                     if item['event'] == 'parcel_boundary_crossing'
                     and item['parcel_id'] == 'left-parcel'
                     and item['boundary'] == 'left']
        self.assertEqual([item['direction'] for item in crossings], ['forward', 'reverse'])
        self.assertEqual(len([item for item in trajectory.events
                              if item['event'] == 'speed_reversal']), 1)
        self.assertAlmostEqual(trajectory.displacement_at(.5), .375)
        self.assertEqual(trajectory.state_at(1.75)['parcels'][0]['parcel_id'], 'left-parcel')

    def test_mid_interval_reel_limit_stops_even_when_endpoint_returns_inside(self):
        case = episode(times_s=(0.0, 1.0, 2.0),
                       prescribed_strip_speed_m_s=(0.0, 2.0, -2.0),
                       left_initial_length_m=1.2)
        trajectory = T1Trajectory(case)
        self.assertGreater(trajectory.stop_time_s, 1.0)
        self.assertLess(trajectory.stop_time_s, 1.5)
        self.assertEqual(trajectory.result()['status'], 'TERMINATED_REEL_LIMIT')
        self.assertEqual(trajectory.state_at(trajectory.stop_time_s)['left_length_m'], 0.0)
        with self.assertRaisesRegex(ValueError, 'terminated'):
            trajectory.state_at(2.0)

    def test_linear_speed_for_constant_winding_omega(self):
        initial_radius = math.sqrt(.01 + .001 / math.pi)
        omega = 2.0
        acceleration = .001 * omega * omega / (2 * math.pi)
        case = episode(times_s=(0.0, 2.0),
                       prescribed_strip_speed_m_s=(omega * initial_radius,
                                                   omega * initial_radius + 2 * acceleration))
        final = T1Trajectory(case).state_at(2.0)
        self.assertAlmostEqual(final['right_radius_m'],
                               initial_radius + .001 * omega * 2 / (2 * math.pi), delta=1e-12)
        self.assertAlmostEqual(final['right_winding_angle_rad'], 4.0, delta=1e-9)

    def test_invalid_secondary_history_and_radius_reject(self):
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            episode(declared_feed_speed_m_s=(.5, .6))
        with self.assertRaisesRegex(ValueError, 'radius disagrees'):
            episode(left_initial_radius_m=.5)
        with self.assertRaisesRegex(ValueError, 'distinct'):
            episode(parcels=(('same', 0.0), ('same', .5)))

    def test_frame_queries_are_order_independent_and_zero_speed_is_static(self):
        case = episode(prescribed_strip_speed_m_s=(0.0, 0.0))
        trajectory = T1Trajectory(case)
        final = trajectory.state_at(2.0)
        trajectory.state_at(.3)
        trajectory.state_at(1.7)
        self.assertEqual(final, trajectory.state_at(2.0))
        self.assertEqual(final['left_length_m'], trajectory.state_at(0.0)['left_length_m'])
        with self.assertRaisesRegex(ValueError, 'extrapolation'):
            trajectory.displacement_at(2.01)

    def test_initial_boundary_departure_and_dwell_reversal_touch(self):
        leaving = T1Trajectory(episode(parcels=(('at-exit', 1.0),)))
        departures = [item for item in leaving.events
                      if item['event'] == 'parcel_boundary_departure']
        self.assertEqual(len(departures), 1)
        self.assertEqual(departures[0]['time_s'], 0.0)
        self.assertEqual(departures[0]['boundary'], 'right')
        self.assertEqual(departures[0]['direction'], 'forward')

        dwell = T1Trajectory(episode(times_s=(0.0, 1.0, 2.0, 3.0),
                                     prescribed_strip_speed_m_s=(1.0, 0.0, 0.0, -1.0),
                                     parcels=(('turning-parcel', -0.5),)))
        touches = [item for item in dwell.events
                   if item['event'] == 'parcel_boundary_touch'
                   and item['boundary'] == 'left']
        self.assertEqual(len(touches), 1)
        self.assertEqual(touches[0]['boundary_arrival_time_s'], 1.0)
        self.assertEqual(touches[0]['boundary_departure_time_s'], 2.0)
        self.assertFalse(any(item['event'] == 'parcel_boundary_crossing'
                             and item['boundary'] == 'left' for item in dwell.events))

    def test_returned_events_cannot_mutate_future_trajectory(self):
        trajectory = T1Trajectory(episode(left_initial_length_m=0.5))
        original = trajectory.state_at(trajectory.stop_time_s)
        result = trajectory.result()
        result['events'][-1]['displacement_m'] = 10_000.0
        trajectory.events[-1]['displacement_m'] = 20_000.0
        trajectory.terminal_event['displacement_m'] = 30_000.0
        self.assertEqual(trajectory.state_at(trajectory.stop_time_s), original)
        self.assertEqual(trajectory.result()['events'][-1]['displacement_m'], 0.5)

    def test_slow_crossing_keeps_strict_ownership_and_analytic_event_time(self):
        trajectory = T1Trajectory(episode(
            times_s=(0.0, 20.0),
            prescribed_strip_speed_m_s=(1e-13, 1e-13),
            parcels=(('slow', -5e-13),)))
        self.assertEqual(trajectory.state_at(0.0)['parcels'][0]['owner'], 'left_reel')
        events = [item for item in trajectory.events if item.get('parcel_id') == 'slow'
                  and item['boundary'] == 'left']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['event'], 'parcel_boundary_crossing')
        self.assertAlmostEqual(events[0]['time_s'], 5.0, delta=1e-9)

    def test_lower_empty_and_capacity_first_hits_are_analytic(self):
        empty = T1Trajectory(episode(prescribed_strip_speed_m_s=(-1.0, -1.0)))
        self.assertEqual(empty.stop_time_s, 1.0)
        self.assertEqual(empty.terminal_event['bound'], 'lower')
        self.assertEqual(empty.state_at(1.0)['right_length_m'], 0.0)

        left_full = T1Trajectory(episode(prescribed_strip_speed_m_s=(-0.5, -0.5),
                                         left_capacity_length_m=3.5))
        self.assertEqual(left_full.stop_time_s, 1.0)
        self.assertEqual(left_full.state_at(1.0)['left_length_m'], 3.5)
        right_full = T1Trajectory(episode(right_capacity_length_m=1.4))
        self.assertAlmostEqual(right_full.stop_time_s, 0.8, delta=1e-9)
        self.assertEqual(right_full.state_at(right_full.stop_time_s)['right_length_m'], 1.4)


if __name__ == '__main__':
    unittest.main()
