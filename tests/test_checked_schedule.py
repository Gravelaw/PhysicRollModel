"""Checked multi-pass replay against independent calls to existing solvers."""
from dataclasses import replace
import json
import unittest
from pathlib import Path

from physicroll.checked_schedule import CheckedPass, InterpassHandoff, run_checked_schedule
from physicroll.contact import CircularRollElasticity, solve_circular_contact
from physicroll.energy_handoff import (HeatCapacityCurve, PassHeatBoundary,
                                       PassiveContactBoundary, handoff_pass)
from physicroll.materials import BiteHardening, MaterialState, PowerHardeningLaw
from physicroll.model import Scenario
from physicroll.operating import EquipmentLimits, PassOperatingPlan, SignalRange
from physicroll.slab import solve_slab

ROOT = Path(__file__).resolve().parents[1]


class CheckedScheduleTests(unittest.TestCase):
    def setUp(self):
        data = json.loads((ROOT / 'scenarios/flowing_energy_demo.json').read_text())
        self.scenario = Scenario.from_dict(json.loads((ROOT / data['baseline_scenario_file']).read_text()))
        self.state = MaterialState(**{**data['material_state'],
                                      'history': tuple(data['material_state']['history'])})
        self.law = PowerHardeningLaw(**data['hardening_law'])
        self.strain_range = tuple(data['assumed_equivalent_strain_range'])
        self.temp_range = tuple(data['assumed_material_temperature_range_k'])
        self.strip_cp = HeatCapacityCurve(**{**data['strip_heat_capacity'],
                                              'temperature_k': tuple(data['strip_heat_capacity']['temperature_k']),
                                              'heat_capacity_j_kg_k': tuple(data['strip_heat_capacity']['heat_capacity_j_kg_k'])})
        self.roll_cp = HeatCapacityCurve(**{**data['roll_heat_capacity'],
                                             'temperature_k': tuple(data['roll_heat_capacity']['temperature_k']),
                                             'heat_capacity_j_kg_k': tuple(data['roll_heat_capacity']['heat_capacity_j_kg_k'])})
        self.boundary1 = PassHeatBoundary(**data['boundaries'][0])
        self.boundary2 = PassHeatBoundary(**data['boundaries'][1])
        self.second_exit = data['second_pass_exit_thickness_m']
        self.gauge_args = {'gauge_basis': 'per_layer_full_thickness', 'layer_count': 1}

    def checked(self, scenario, plan, boundary=None, *, solver='spatial_slab', elasticity=None,
                passive=None):
        return CheckedPass(scenario, plan, solver, 256, 'unassisted', self.strain_range,
                           self.temp_range, elasticity, boundary, passive,
                           roll_body_id='synthetic_roll_body_A' if boundary is not None else None)

    def reference_pass(self, scenario, state, boundary=None, *, elasticity=None, passive=None):
        material = BiteHardening(state, self.law, self.strain_range, self.temp_range)
        actual = replace(scenario, mean_flow_stress_pa=material.mean_stress(
            scenario.entry_thickness_m, scenario.exit_thickness_m))
        if elasticity is None:
            mechanics = solve_slab(actual, 256, bite_mode='unassisted', material=material)
        else:
            mechanics = solve_circular_contact(actual, elasticity, 256,
                                               bite_mode='unassisted', material=material)
        energy = None if boundary is None else handoff_pass(
            mechanics, state, self.strip_cp, self.roll_cp, boundary, passive_contact=passive)
        return mechanics, energy

    def second_scenario(self, speed):
        return replace(self.scenario, name='checked_second_pass',
                       entry_thickness_m=self.scenario.exit_thickness_m,
                       exit_thickness_m=self.second_exit, entry_speed_m_s=speed,
                       entry_tension_pa=12e6, exit_tension_pa=18e6,
                       friction_coefficient=.09)

    def test_two_pass_slab_and_energy_match_independent_replay(self):
        m1, e1 = self.reference_pass(self.scenario, self.state, self.boundary1)
        state2 = MaterialState(**{**e1['strip_state_out'],
                                  'history': tuple(e1['strip_state_out']['history'])})
        scenario2 = self.second_scenario(m1['exit_speed_m_s'])
        boundary2 = replace(self.boundary2, roll_temperature_k=e1['roll_temperature_out_k'])
        m2, e2 = self.reference_pass(scenario2, state2, boundary2)
        p1 = PassOperatingPlan(self.scenario.name,
                               ranges=(SignalRange('entry_speed_m_s', 'm/s', 1, 3, 'steady', 'synthetic p1'),
                                       SignalRange('exit_temperature_k', 'K', 290, 320, 'steady', 'synthetic p1')))
        p2 = PassOperatingPlan(scenario2.name,
                               ranges=(SignalRange('entry_speed_m_s', 'm/s', 2.5, 3, 'steady', 'synthetic p2'),
                                       SignalRange('exit_temperature_k', 'K', 300, 330, 'steady', 'synthetic p2')))
        result = run_checked_schedule(
            (self.checked(self.scenario, p1, self.boundary1),
             self.checked(scenario2, p2, self.boundary2)),
            self.state, self.law, **self.gauge_args,
            interpass_handoffs=(InterpassHandoff(1, 'direct_predicted_carry', None,
                                                'direct_predicted_carry', None,
                                                'synthetic immediate reversal; no interpass exchange'),),
            strip_cp=self.strip_cp, roll_cp=self.roll_cp,
            equipment_limits=EquipmentLimits('synthetic rating', max_separating_force_n=1e9))
        self.assertEqual(result['declared_bounds_status'], 'INDETERMINATE')
        self.assertEqual(result['passes'][0]['operating']['range_checks'][1]['status'],
                         'WITHIN_DECLARED_RANGE')
        self.assertEqual(result['passes'][1]['operating']['range_checks'][0]['status'],
                         'WITHIN_DECLARED_RANGE')
        for actual, m_ref, e_ref in zip(result['passes'], (m1, m2), (e1, e2)):
            self.assertAlmostEqual(actual['mechanics']['separating_force_n'], m_ref['separating_force_n'])
            self.assertAlmostEqual(actual['mechanics']['torque_per_work_roll_nm'], m_ref['torque_per_work_roll_nm'])
            self.assertAlmostEqual(actual['thermal']['strip_temperature_out_k'], e_ref['strip_temperature_out_k'])
            self.assertLess(actual['thermal']['thermal_allocation_residual_relative'], 1e-8)
            self.assertTrue(actual['mechanics']['numerical_converged'])
        self.assertEqual(result['passes'][1]['mechanics']['material']['state_in']['temperature_k'],
                         e1['strip_temperature_out_k'])
        self.assertEqual(result['passes'][1]['thermal']['boundary']['roll_temperature_k'],
                         e1['roll_temperature_out_k'])
        self.assertEqual(result['final_state']['temperature_k'], e2['strip_temperature_out_k'])

    def test_circular_and_passive_options_match_direct_solver_calls(self):
        elasticity = CircularRollElasticity(210e9, .3, 'synthetic test elasticity')
        passive_data = json.loads((ROOT / 'scenarios/passive_contact_demo.json').read_text())
        boundary = PassHeatBoundary(**passive_data['boundaries'][0])
        passive = PassiveContactBoundary(**passive_data['passive_contacts'][0])
        m_ref, e_ref = self.reference_pass(self.scenario, self.state, boundary,
                                           elasticity=elasticity, passive=passive)
        plan = PassOperatingPlan(self.scenario.name,
                                 ranges=(SignalRange('forward_slip_fraction', '1', 0, 1,
                                                     'steady', 'synthetic range'),))
        result = run_checked_schedule((self.checked(self.scenario, plan, boundary,
                                                    solver='circular_contact', elasticity=elasticity,
                                                    passive=passive),),
                                      self.state, self.law, **self.gauge_args,
                                      strip_cp=self.strip_cp, roll_cp=self.roll_cp)
        actual = result['passes'][0]
        self.assertAlmostEqual(actual['mechanics']['separating_force_n'], m_ref['separating_force_n'])
        self.assertAlmostEqual(actual['mechanics']['forward_slip_fraction'], m_ref['forward_slip_fraction'])
        self.assertAlmostEqual(actual['thermal']['contact_heat_to_strip_w'], e_ref['contact_heat_to_strip_w'])
        self.assertEqual(actual['thermal']['contact_mode'], 'PASSIVE_SUPPLIED_TOTAL_CONDUCTANCE')

    def test_passive_contact_domain_rejection_propagates(self):
        data = json.loads((ROOT / 'scenarios/passive_contact_demo.json').read_text())
        boundary = PassHeatBoundary(**data['boundaries'][0])
        passive = replace(PassiveContactBoundary(**data['passive_contacts'][0]),
                          conductance_w_k=1e6)
        with self.assertRaisesRegex(ValueError, 'passive contact.*domain'):
            run_checked_schedule((self.checked(self.scenario, PassOperatingPlan(self.scenario.name),
                                               boundary, passive=passive),),
                                 self.state, self.law, **self.gauge_args,
                                 strip_cp=self.strip_cp, roll_cp=self.roll_cp)

    def test_invalid_layer_stage_handoff_and_limit_propagation(self):
        plan = PassOperatingPlan(self.scenario.name,
                                 ranges=(SignalRange('separating_force_n', 'N', 0, 1,
                                                     'steady', 'deliberate synthetic violation'),))
        first = self.checked(self.scenario, plan)
        result = run_checked_schedule((first,), self.state, self.law, **self.gauge_args)
        self.assertEqual(result['status'], 'DECLARED_BOUNDS_VIOLATED')
        with self.assertRaisesRegex(ValueError, 'single-layer'):
            run_checked_schedule((first,), self.state, self.law,
                                 gauge_basis='per_layer_full_thickness', layer_count=2)
        foil = replace(self.scenario, exit_thickness_m=.00005)
        with self.assertRaisesRegex(ValueError, 'software gauge guard'):
            run_checked_schedule((self.checked(foil, PassOperatingPlan(foil.name)),),
                                 self.state, self.law, **self.gauge_args)
        scenario2 = self.second_scenario(2.7)
        second = self.checked(scenario2, PassOperatingPlan(scenario2.name))
        with self.assertRaisesRegex(ValueError, 'one explicit interpass handoff'):
            run_checked_schedule((first, second), self.state, self.law, **self.gauge_args)
        with self.assertRaisesRegex(ValueError, 'cannot carry an unpredicted strip'):
            run_checked_schedule((first, second), self.state, self.law, **self.gauge_args,
                                 interpass_handoffs=(InterpassHandoff(1, 'direct_predicted_carry', None,
                                                                     'not_modeled', None, 'test'),))
        with self.assertRaisesRegex(ValueError, 'same roll body'):
            thermal1 = self.checked(self.scenario, PassOperatingPlan(self.scenario.name), self.boundary1)
            thermal2 = replace(self.checked(scenario2, PassOperatingPlan(scenario2.name), self.boundary2),
                               roll_body_id='different_roll_body')
            run_checked_schedule((thermal1, thermal2), self.state, self.law, **self.gauge_args,
                                 interpass_handoffs=(InterpassHandoff(1, 'prescribed', 305,
                                                                     'direct_predicted_carry', None,
                                                                     'invalid roll change'),),
                                 strip_cp=self.strip_cp, roll_cp=self.roll_cp)
        with self.assertRaisesRegex(ValueError, 'changed strip width'):
            run_checked_schedule((first, replace(second,
                                scenario=replace(scenario2, width_m=.9))),
                                 self.state, self.law, **self.gauge_args,
                                 interpass_handoffs=(InterpassHandoff(1, 'prescribed', 300,
                                                                     'not_modeled', None, 'test'),))

    def test_prescribed_interpass_temperature_and_pass_indexed_failure(self):
        first = self.checked(self.scenario, PassOperatingPlan(self.scenario.name))
        scenario2 = self.second_scenario(2.7)
        second = self.checked(scenario2, PassOperatingPlan(scenario2.name))
        event = InterpassHandoff(1, 'prescribed', 305.0, 'not_modeled', None,
                                 'synthetic externally declared temperature')
        result = run_checked_schedule((first, second), self.state, self.law,
                                      **self.gauge_args, interpass_handoffs=(event,))
        self.assertIsNone(result['passes'][0]['thermal'])
        self.assertEqual(result['passes'][1]['mechanics']['material']['state_in']['temperature_k'], 305)
        self.assertEqual(result['passes'][1]['operating']['predictions']['exit_temperature_k'], None)
        with self.assertRaisesRegex(ValueError, 'pass 2:'):
            run_checked_schedule((first, second), self.state, self.law, **self.gauge_args,
                                 interpass_handoffs=(replace(event, strip_temperature_k=500),))
        with self.assertRaisesRegex(ValueError, 'pass 1: enthalpy outside supplied property range'):
            bad_heat = replace(self.boundary1, strip_cooling_w=1e9)
            run_checked_schedule((replace(first, heat_boundary=bad_heat,
                                          roll_body_id='synthetic_roll_body_A'),), self.state, self.law,
                                 **self.gauge_args, strip_cp=self.strip_cp, roll_cp=self.roll_cp)


if __name__ == '__main__':
    unittest.main()
