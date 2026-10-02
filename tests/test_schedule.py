"""Independent kinematic identities and explicit per-pass contract tests."""
import math
import unittest
from dataclasses import replace

from physicroll.materials import MaterialState, PowerHardeningLaw
from physicroll.model import Scenario
from physicroll.operating import (EquipmentLimits, ObservedSignal, PassOperatingPlan,
                                   SignalRange)
from physicroll.schedule import (GaugeSchedule, InterpassTemperature,
                                 inspect_gauge_schedule, run_prescribed_schedule)


class GaugeScheduleTests(unittest.TestCase):
    def test_illustrative_path_and_foil_boundary(self):
        path = GaugeSchedule('illustrative only', (.006, .0035, .002, .00129, .0008,
                                                   .0004, .00025, .00012, .00005), .00005,
                             'per_layer_full_thickness', 1)
        result = inspect_gauge_schedule(path)
        self.assertEqual(len(result['passes']), 8)
        self.assertAlmostEqual(sum(p['log_thickness_strain_increment'] for p in result['passes']),
                               math.log(120))
        self.assertAlmostEqual(result['total_plane_strain_equivalent_increment'],
                               2 / math.sqrt(3) * math.log(120))
        self.assertEqual(result['passes'][-1]['single_pass_gauge_screen'], 'OUTSIDE_MODEL_DOMAIN')
        self.assertIn('FOIL_EXIT_BELOW_300_UM_SINGLE_PASS_MODEL_GUARD',
                      result['passes'][-1]['reasons'])
        self.assertEqual(result['passes'][0]['single_pass_gauge_screen'], 'NEEDS_FULL_INPUTS')

    def test_rejects_jump_reverse_target_and_bad_numbers(self):
        bad = [(.006, .00005), (.006, .007), (.006, .006), (.006, float('nan'))]
        for gauges in bad:
            with self.subTest(gauges=gauges), self.assertRaises(ValueError):
                if gauges == (.006, .00005):
                    # This path is representable for diagnostic purposes, but not a
                    # supported pass; executable Scenario below rejects it.
                    Scenario('jump', True, gauges[0], gauges[1], 1, 1, .25,
                             2700, 1e8, .08, 0, 0, .9).validate()
                else:
                    inspect_gauge_schedule(GaugeSchedule('bad', gauges, gauges[-1],
                                                         'per_layer_full_thickness', 1))
        with self.assertRaisesRegex(ValueError, 'final target'):
            inspect_gauge_schedule(GaugeSchedule('bad', (.006, .003), .00005,
                                                 'per_layer_full_thickness', 1))
        with self.assertRaisesRegex(ValueError, 'single-layer'):
            inspect_gauge_schedule(GaugeSchedule('unsupported pack', (.006, .003), .003,
                                                 'per_layer_full_thickness', 2))


class PrescribedPassTests(unittest.TestCase):
    def setUp(self):
        self.first = Scenario('p1', True, .002, .0015, 1, 2, .25, 2700,
                              120e6, .08, 10e6, 15e6, .9)
        self.second = replace(self.first, name='p2', entry_thickness_m=.0015,
                              exit_thickness_m=.0012, entry_speed_m_s=2.5,
                              entry_tension_pa=12e6, exit_tension_pa=18e6,
                              friction_coefficient=.09)
        self.state = MaterialState('synthetic Al', 'unknown', .1, ('declared prior',), 293.15)
        self.law = PowerHardeningLaw('synthetic Al', 'unknown', 100e6, 100e6,
                                     .3, 'synthetic test law')
        self.gauge_args = {'gauge_basis': 'per_layer_full_thickness', 'layer_count': 1}
        self.plans = (
            PassOperatingPlan('p1', ranges=(SignalRange('entry_speed_m_s', 'm/s', 1, 2.2,
                                                  'steady', 'declared p1 range'),),
                              observations=(ObservedSignal('separating_force_n', 'N', 1e6,
                                                           'steady', 'example reading'),),
                              cooling_boundary='declared dry',
                              lubrication_boundary='declared neat oil',
                              boundary_provenance='test declaration'),
            PassOperatingPlan('p2', ranges=(SignalRange('entry_speed_m_s', 'm/s', 2.4, 2.6,
                                                  'steady', 'declared p2 range'),
                                      SignalRange('exit_temperature_k', 'K', 290, 330,
                                                  'steady', 'unknown thermal range'),
                                      SignalRange('entry_tension_pa', 'Pa', 1e6, 20e6,
                                                  'threading', 'test only'))))

    def test_state_handoff_and_distinct_pass_ranges(self):
        result = run_prescribed_schedule((self.first, self.second), self.state, self.law,
                                          operating_plans=self.plans,
                                          **self.gauge_args,
                                          interpass_temperatures=(InterpassTemperature(1, 302, 'measured after p1'),),
                                          equipment_limits=EquipmentLimits('test limit', max_separating_force_n=1e9))
        a, b = result['passes']
        self.assertAlmostEqual(b['mechanics']['state_in']['accumulated_equivalent_plastic_strain'],
                               a['mechanics']['state_out']['accumulated_equivalent_plastic_strain'])
        self.assertEqual(b['mechanics']['state_in']['temperature_k'], 302)
        self.assertEqual(result['final_state']['temperature_k'], 302)
        self.assertAlmostEqual(result['final_state']['accumulated_equivalent_plastic_strain'],
                               .1 + 2 / math.sqrt(3) * math.log(.002 / .0012))
        self.assertEqual(a['operating']['range_checks'][0]['status'], 'WITHIN_DECLARED_RANGE')
        self.assertEqual(b['operating']['range_checks'][0]['status'], 'WITHIN_DECLARED_RANGE')
        self.assertEqual(b['operating']['range_checks'][1]['status'], 'NOT_EVALUATED_NO_MODEL')
        self.assertEqual(b['operating']['range_checks'][2]['status'], 'NOT_EVALUATED_PHASE')
        self.assertEqual(b['operating']['evaluated_checks_status'], 'PARTIAL_DECLARED_CHECKS_ONLY')
        self.assertEqual(result['declared_bounds_status'], 'INDETERMINATE')
        self.assertEqual(len(a['operating']['observations']), 1)
        self.assertEqual(len(b['operating']['observations']), 0)

    def test_all_passes_preflight_and_no_inherited_plan(self):
        with self.assertRaisesRegex(ValueError, 'one explicit operating plan is required per pass'):
            run_prescribed_schedule((self.first, self.second), self.state, self.law,
                                     operating_plans=self.plans[:1], **self.gauge_args)
        with self.assertRaisesRegex(ValueError, 'pass_name does not match'):
            run_prescribed_schedule((self.first, self.second), self.state, self.law,
                                     operating_plans=self.plans[::-1], **self.gauge_args)
        with self.assertRaisesRegex(ValueError, 'pass 2: entry gauge'):
            run_prescribed_schedule((self.first, replace(self.second, entry_thickness_m=.0014)),
                                     self.state, self.law, operating_plans=self.plans, **self.gauge_args)
        with self.assertRaisesRegex(ValueError, 'pass 2: Foil excluded'):
            run_prescribed_schedule((self.first, replace(self.second, exit_thickness_m=.00005)),
                                     self.state, self.law, operating_plans=self.plans, **self.gauge_args)

    def test_bad_units_duplicates_and_event_position(self):
        with self.assertRaisesRegex(ValueError, 'SI unit'):
            SignalRange('entry_speed_m_s', 'mm/s', 1, 3, 'steady', 'test').validate()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            PassOperatingPlan('p1', ranges=(self.plans[0].ranges[0], self.plans[0].ranges[0])).validate()
        with self.assertRaisesRegex(ValueError, 'nonfinal'):
            run_prescribed_schedule((self.first, self.second), self.state, self.law,
                                     operating_plans=self.plans, **self.gauge_args,
                                     interpass_temperatures=(InterpassTemperature(2, 300, 'test'),))

    def test_declared_range_and_hardware_violations_are_visible(self):
        narrow = PassOperatingPlan('p1', ranges=(SignalRange('entry_speed_m_s', 'm/s', 0, 1,
                                                       'steady', 'synthetic test bound'),))
        result = run_prescribed_schedule((self.first,), self.state, self.law,
                                          operating_plans=(narrow,),
                                          **self.gauge_args,
                                          equipment_limits=EquipmentLimits('synthetic test rating',
                                                                           max_separating_force_n=1))
        operating = result['passes'][0]['operating']
        self.assertEqual(operating['range_checks'][0]['status'], 'OUTSIDE_DECLARED_RANGE')
        self.assertEqual(operating['equipment_checks'][0]['status'], 'OUTSIDE_DECLARED_LIMIT')
        self.assertEqual(operating['evaluated_checks_status'], 'OUTSIDE_DECLARED_BOUNDS')
        self.assertEqual(result['status'], 'DECLARED_BOUNDS_VIOLATED')
        self.assertEqual(result['declared_bounds_status'], 'VIOLATED')

    def test_declared_boundary_flow_is_pass_local_input(self):
        plan = PassOperatingPlan('p1',
                                 ranges=(SignalRange('coolant_flow_kg_s', 'kg/s', 0, 2,
                                                     'steady', 'test declaration'),),
                                 coolant_flow_kg_s=3, boundary_provenance='test declaration')
        result = run_prescribed_schedule((self.first,), self.state, self.law,
                                          operating_plans=(plan,), **self.gauge_args)
        self.assertEqual(result['status'], 'DECLARED_BOUNDS_VIOLATED')
        self.assertEqual(result['passes'][0]['operating']['boundary_inputs']['coolant_flow_kg_s'], 3)
        self.assertEqual(result['passes'][0]['operating']['range_checks'][0]['status'],
                         'OUTSIDE_DECLARED_RANGE')

    def test_extreme_positive_gauges_audit_stays_finite(self):
        audit = inspect_gauge_schedule(GaugeSchedule('extreme numeric audit', (1e308, 1e-308),
                                                     1e-308, 'per_layer_full_thickness', 1))
        self.assertTrue(math.isfinite(audit['total_log_thickness_strain']))
        self.assertTrue(math.isfinite(audit['passes'][0]['plane_strain_equivalent_increment']))
        entry = 1e-300
        exit_ = math.nextafter(entry, 0)
        tiny = inspect_gauge_schedule(GaugeSchedule('tiny numeric audit', (entry, exit_), exit_,
                                                    'per_layer_full_thickness', 1))
        expected = math.log1p((entry - exit_) / exit_)
        self.assertGreater(tiny['passes'][0]['log_thickness_strain_increment'], 0)
        self.assertAlmostEqual(tiny['passes'][0]['log_thickness_strain_increment'], expected)


if __name__ == '__main__':
    unittest.main()
