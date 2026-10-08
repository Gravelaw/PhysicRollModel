"""Finite-search contract tests with an explicitly synthetic full-route oracle."""
from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import physicroll.conditional_shao as conditional_shao
from physicroll.schedule_search import (OperatingChoice, SearchSpace,
                                        log_gauge_grid, search_schedules)
from physicroll.conditional_shao import (audited_raw, compare_existing_fixture,
                                         run_conditional_comparison)


FAST = OperatingChoice(2.0, 10.0, 10.0, 'synthetic fast')
SLOW = OperatingChoice(1.0, 10.0, 10.0, 'synthetic slow')


def route_result(gauges, choices, *, status='INDETERMINATE', checks=None, stamp=None):
    if checks is None:
        checks = []
    return {'declared_bounds_status': status,
            'gauge_audit': {'gauge_basis': 'per_layer_full_thickness',
                            'layer_count': 1, 'target_exit_m': gauges[-1]},
            'passes': [{'requested_scenario': {
                'entry_thickness_m': gauges[i], 'exit_thickness_m': gauges[i+1],
                'entry_speed_m_s': choice.entry_speed_m_s,
                'entry_tension_pa': choice.entry_tension_pa,
                'exit_tension_pa': choice.exit_tension_pa},
                'operating': {'equipment_checks': checks}, 'state_out': stamp}
                for i, choice in enumerate(choices)], 'stamp': stamp}


def space(**overrides):
    base = dict(gauges_m=(4.0, 3.0, 2.0, 1.0),
                mandatory_checkpoints_m=(2.0,), min_passes=2, max_passes=3,
                choices_by_pass=((FAST, SLOW), (FAST, SLOW), (FAST, SLOW)),
                max_evaluations=12)
    base.update(overrides)
    return SearchSpace(**base)


class SearchTests(unittest.TestCase):
    def test_checkpoints_exact_ends_pass_priority_and_stateful_replay(self):
        calls = []

        def oracle(gauges, choices):
            calls.append((gauges, choices))
            # A complete sequential state history; equal intermediate gauges
            # may have different results after different preceding choices.
            state = 0.0
            for entry, exit_, choice in zip(gauges, gauges[1:], choices):
                state += (entry-exit_) * choice.entry_speed_m_s
            result = route_result(gauges, choices, stamp=state)
            for item in result['passes']:
                item['operating']['equipment_checks'] = [{
                    'quantity': 'separating_force_n', 'predicted_value': state,
                    'limit': 10.0, 'status': 'WITHIN_DECLARED_LIMIT'}]
            result['final_state'] = state
            return result

        result = search_schedules(space(), oracle)
        self.assertEqual(result['evaluations'], 12)
        self.assertEqual(len(calls), 13)  # selected route independently replayed
        self.assertEqual(result['selected']['gauges_m'], (4.0, 2.0, 1.0))
        self.assertEqual(result['selected']['choices'], (SLOW, SLOW))
        self.assertEqual(result['selected']['checked_replay']['final_state'], 3.0)
        self.assertEqual(result['status'], 'SELECTED_DECLARED_BOUNDS_INDETERMINATE')

    def test_rejection_violations_and_no_nonviolating_route(self):
        def oracle(gauges, choices):
            if choices[0] == FAST:
                raise ValueError('synthetic model domain rejection')
            result = route_result(gauges, choices, status='VIOLATED')
            result['declared_bound_violations'] = [
                {'pass_number': 1, 'check': {'status': 'OUTSIDE_DECLARED_LIMIT'}}]
            return result

        result = search_schedules(space(max_passes=2, max_evaluations=4), oracle)
        self.assertEqual(result['status'], 'NO_NONVIOLATING_CANDIDATE_ON_GRID')
        self.assertEqual([r['status'] for r in result['candidates']],
                         ['REJECTED', 'REJECTED', 'VIOLATED', 'VIOLATED'])
        self.assertIn('model domain', result['candidates'][0]['reason'])
        self.assertEqual(result['candidates'][2]['reason'][0]['pass_number'], 1)

    def test_grid_and_cap_are_explicit(self):
        grid = log_gauge_grid(4.0, 1.0, 3, (2.0,))
        self.assertEqual(grid[0], 4.0)
        self.assertEqual(grid[-1], 1.0)
        self.assertIn(2.0, grid)
        with self.assertRaisesRegex(ValueError, 'evaluation cap'):
            search_schedules(space(max_evaluations=11), lambda *_: None)
        with self.assertRaisesRegex(ValueError, 'checkpoints'):
            replace(space(), mandatory_checkpoints_m=(1.5,)).validate()

    def test_replay_mismatch_is_a_failure(self):
        calls = 0

        def changing_oracle(gauges, choices):
            nonlocal calls
            calls += 1
            return route_result(gauges, choices, stamp=calls)

        with self.assertRaisesRegex(ValueError, 'did not reproduce'):
            search_schedules(space(max_passes=2, max_evaluations=4), changing_oracle)

    def test_oracle_route_and_rating_contracts(self):
        with self.assertRaisesRegex(ValueError, 'does not match enumerated route'):
            def wrong_route(gauges, choices):
                result = route_result(gauges, choices)
                result['passes'][0]['requested_scenario']['exit_thickness_m'] = 9.0
                return result
            search_schedules(space(max_passes=2, max_evaluations=4), wrong_route)

        with self.assertRaisesRegex(ValueError, 'ratings differ between candidates'):
            def changing_ratings(gauges, choices):
                rating = 10.0 if choices[0] == FAST else 20.0
                return route_result(gauges, choices, checks=[{
                    'quantity': 'separating_force_n', 'limit': rating,
                    'predicted_value': 1.0, 'status': 'WITHIN_DECLARED_LIMIT'}])
            search_schedules(space(max_passes=2, max_evaluations=4), changing_ratings)

        with self.assertRaisesRegex(ValueError, 'oracle contract'):
            search_schedules(space(max_passes=2, max_evaluations=4), lambda *_: {})

    def test_shao_conditional_source_parity_and_continuity(self):
        raw = audited_raw()
        self.assertEqual(compare_existing_fixture(raw), [])
        self.assertIsNone(raw['material_source']['incoming_plastic_strain'])
        self.assertIsNone(raw['passes'][0]['table_1']['speed_reference'])
        self.assertIsNone(raw['passes'][0]['table_2_measured']['uncertainty'])
        result = run_conditional_comparison()
        self.assertEqual(result['status'], 'CONDITIONAL_COMPARISON_NOT_VALIDATION')
        self.assertEqual(result['search']['evaluations'], 1)
        self.assertIsNone(result['search']['selected']['peak_normalized_utilization'])
        route = result['search']['selected']['gauges_m']
        for actual, expected in zip(route, (0.0041, 0.0029024, 0.0022087, 0.00172)):
            self.assertAlmostEqual(actual, expected, places=14)
        passes = result['search']['selected']['checked_replay']['passes']
        self.assertEqual(len(passes), 3)
        for index, item in enumerate(passes):
            source = raw['passes'][index]
            table = source['table_1']
            scenario = item['requested_scenario']
            self.assertEqual(item['requested_scenario']['entry_thickness_m'], route[index])
            self.assertEqual(item['requested_scenario']['exit_thickness_m'], route[index+1])
            self.assertAlmostEqual(scenario['width_m'], table['width_mm']*1e-3)
            self.assertAlmostEqual(scenario['work_roll_radius_m'], table['radius_labelled_mm']*1e-3)
            self.assertEqual(scenario['entry_speed_m_s'], table['reported_speed_m_s'])
            self.assertEqual(scenario['entry_tension_pa'], table['back_tension_mpa']*1e6)
            self.assertEqual(scenario['exit_tension_pa'], table['front_tension_mpa']*1e6)
            self.assertEqual(scenario['friction_coefficient'],
                             source['table_2_model_input']['friction_coefficient'])
            self.assertEqual(item['operating']['equipment_checks'], [])
            self.assertTrue(item['mechanics']['numerical_converged'])
            expected_strain = (2/math.sqrt(3) *
                               (0.05 + math.log(4.1/table['exit_mm'])))
            self.assertAlmostEqual(item['state_out']['accumulated_equivalent_plastic_strain'],
                                   expected_strain, places=12)
            self.assertEqual(result['comparisons'][index]['observed_force_n'],
                             raw['passes'][index]['table_2_measured']['force_kn']*1000)
            if index:
                self.assertEqual(item['mechanics']['material']['state_in']['accumulated_equivalent_plastic_strain'],
                                 passes[index-1]['state_out']['accumulated_equivalent_plastic_strain'])
        self.assertEqual([round(row['signed_force_residual_fraction']*100, 2)
                          for row in result['comparisons']], [-3.08, -3.01, 7.79])
        self.assertEqual([round(row['signed_slip_residual_fraction']*100, 2)
                          for row in result['comparisons']], [41.89, 37.89, 23.79])
        self.assertEqual(result['finer_grid_replay']['declared_bounds_status'], 'INDETERMINATE')
        for difference in result['numerical_differences']:
            self.assertLess(abs(difference['force_relative_change']), 1e-5)
            self.assertLess(abs(difference['slip_absolute_change']), 1e-6)

    def test_shao_adapter_contract_drift_rejects(self):
        config = json.loads(conditional_shao.ADAPTER_PATH.read_text())
        config['executable_contract']['speed_mapping'] = 'reported_as_roll_surface'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'changed_adapter.json'
            path.write_text(json.dumps(config))
            with mock.patch.object(conditional_shao, 'ADAPTER_PATH', path):
                with self.assertRaisesRegex(ValueError, 'conventions differ'):
                    conditional_shao.run_conditional_comparison()


if __name__ == '__main__':
    unittest.main()
