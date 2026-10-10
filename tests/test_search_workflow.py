"""Public finite search preserves exact grid, candidate and replay contracts."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from physicroll.run_contract import ResultBundle, RunSpec
from physicroll.workflows import run_workflow


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'scenarios/v1_schedule_search.runspec.json'


class SearchWorkflowTests(unittest.TestCase):
    def example(self):
        return RunSpec.from_json(EXAMPLE.read_bytes())

    def test_cli_api_parity_candidate_records_and_missing_limits(self):
        spec = self.example()
        api = run_workflow(spec)
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            subprocess.run([sys.executable, '-m', 'physicroll', '--run-spec',
                            str(EXAMPLE), '--output', str(output)],
                           cwd=ROOT, capture_output=True, text=True, check=True)
            cli = ResultBundle.from_json(output.read_bytes())
        cli.verify_run_spec(spec)
        self.assertEqual(cli.sha256, api.sha256)
        result = api.to_dict()
        search = result['outputs']['schedule_search']
        self.assertEqual(search['evaluations'], 3)
        self.assertEqual(len(search['candidates']), 3)
        self.assertEqual(search['selected']['gauges_m'], [0.002, 0.0015])
        self.assertTrue(result['checks']['independent_selected_replay'])
        self.assertEqual(result['assessments']['declared_bounds_status'], 'INDETERMINATE')
        self.assertEqual(result['assessments']['declared_bounds_coverage'], 'NONE')
        self.assertEqual(result['assessments']['scientific_qualification'], 'NOT_ASSESSED')
        self.assertEqual(result['assessments']['operating_readiness'], 'NOT_ASSESSED')

    def test_two_pass_route_carries_material_state(self):
        data = self.example().to_dict()
        space = data['resolved_inputs']['search_space']
        space['min_passes'] = 2
        space['max_evaluations'] = 2
        data['requested_inputs']['search_space'] = space
        search = run_workflow(RunSpec(data)).to_dict()['outputs']['schedule_search']
        self.assertEqual(search['evaluations'], 2)
        passes = search['selected']['checked_replay']['passes']
        self.assertEqual(len(passes), 2)
        incoming = passes[1]['mechanics']['material']['state_in']
        prior = passes[0]['state_out']
        self.assertEqual(incoming['accumulated_equivalent_plastic_strain'],
                         prior['accumulated_equivalent_plastic_strain'])
        self.assertEqual(incoming['history'][:-1], prior['history'])
        self.assertTrue(incoming['history'][-1].startswith('interpass_strip_temperature:'))
        self.assertEqual(passes[-1]['requested_scenario']['exit_thickness_m'], 0.0015)

    def test_cap_source_and_requested_grid_fail_before_execution(self):
        data = self.example().to_dict()
        data['resolved_inputs']['search_space']['max_evaluations'] = 2
        data['requested_inputs']['search_space']['max_evaluations'] = 2
        with self.assertRaisesRegex(ValueError, 'evaluation cap'):
            run_workflow(RunSpec(data))
        data = self.example().to_dict()
        data['source_hashes']['physicroll/schedule_search.py'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source hash mismatch'):
            run_workflow(RunSpec(data))
        data = self.example().to_dict()
        data['requested_inputs']['search_space']['gauges_m'][1] = 0.0019
        with self.assertRaisesRegex(ValueError, 'search spaces differ'):
            run_workflow(RunSpec(data))

    def test_rejected_grid_records_no_selected_prediction(self):
        data = self.example().to_dict()
        space = data['resolved_inputs']['search_space']
        space.update(gauges_m=[0.002, 0.0015], min_passes=1, max_passes=1,
                     choices_by_pass=[space['choices_by_pass'][0]],
                     max_evaluations=1)
        space['choices_by_pass'][0][0]['entry_tension_pa'] = 1e9
        data['requested_inputs']['search_space'] = space
        result = run_workflow(RunSpec(data)).to_dict()
        search = result['outputs']['schedule_search']
        self.assertEqual(search['status'], 'NO_NONVIOLATING_CANDIDATE_ON_GRID')
        self.assertEqual(search['candidates'][0]['status'], 'REJECTED')
        self.assertIsNone(search['selected'])
        self.assertFalse(result['assessments']['predictions_computed'])
        self.assertEqual(result['assessments']['numerical_verification'], 'NOT_ASSESSED')

    def test_total_route_reduction_above_single_pass_guard(self):
        data = self.example().to_dict()
        space = data['resolved_inputs']['search_space']
        space.update(gauges_m=[0.002, 0.0015, 0.0009], min_passes=2,
                     max_passes=2, mandatory_checkpoints_m=[0.0015],
                     max_evaluations=1)
        data['requested_inputs']['search_space'] = space
        data['resolved_inputs']['base_pass']['cells'] = 256
        data['numerical_settings']['cells'] = 256
        result = run_workflow(RunSpec(data)).to_dict()
        route = result['outputs']['schedule_search']['selected']['checked_replay']
        self.assertEqual(len(route['passes']), 2)
        self.assertEqual(route['gauge_audit']['target_exit_m'], 0.0009)
        self.assertTrue(result['assessments']['predictions_computed'])

    def test_violating_candidates_still_count_as_computed(self):
        data = self.example().to_dict()
        data['resolved_inputs']['equipment_limits'] = {
            'provenance': 'synthetic deliberately restrictive test cap',
            'max_separating_force_n': 1.0}
        result = run_workflow(RunSpec(data)).to_dict()
        search = result['outputs']['schedule_search']
        self.assertIsNone(search['selected'])
        self.assertEqual([item['status'] for item in search['candidates']],
                         ['VIOLATED'] * 3)
        self.assertTrue(result['assessments']['predictions_computed'])
        self.assertEqual(result['checks']['candidate_computation_count'], 3)
        self.assertEqual(result['checks']['candidate_violation_count'], 3)
        self.assertEqual(result['checks']['assessment_scope'], 'selected_route')
        self.assertEqual(result['assessments']['declared_bounds_coverage'], 'NONE')


if __name__ == '__main__':
    unittest.main()
