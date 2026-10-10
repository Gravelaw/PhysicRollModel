"""Public O0 replay preserves phase evidence without claiming predictions."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from physicroll.run_contract import ResultBundle, RunSpec
from physicroll.workflows import run_workflow


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'scenarios/v1_operating_replay.runspec.json'


class OperatingWorkflowTests(unittest.TestCase):
    def example(self):
        return RunSpec.from_json(EXAMPLE.read_bytes())

    def test_full_phase_trace_cli_api_parity_and_no_prediction(self):
        spec = self.example()
        api = run_workflow(spec)
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            subprocess.run([sys.executable, '-m', 'physicroll', '--run-spec',
                            str(EXAMPLE), '--output', str(output)],
                           cwd=ROOT, capture_output=True, text=True, check=True)
            cli = ResultBundle.from_json(output.read_bytes())
        cli.verify_run_spec(spec)
        self.assertEqual(api.sha256, cli.sha256)
        result = api.to_dict()
        rows = result['outputs']['operating_replay']['samples']
        self.assertEqual([row['sample']['phase'] for row in rows],
                         ['prepared', 'threading', 'ramp_up', 'steady',
                          'deceleration', 'tailout', 'complete'])
        self.assertEqual([row['model_readiness']['spatial_slab']['evaluation_allowed']
                          for row in rows], [False, False, False, True, False, False, False])
        steady = rows[3]
        target = next(item['value'] for item in steady['recipe_targets']
                      if item['quantity'] == 'entry_speed_m_s')
        applied = steady['sample']['applied_references'][0]['value']
        actual = next(item['value'] for item in steady['sample']['measurements']
                      if item['quantity'] == 'entry_speed_m_s')
        self.assertEqual((target, applied, actual), (2.0, 1.9, 1.8))
        self.assertFalse(result['assessments']['predictions_computed'])
        self.assertFalse(result['outputs']['operating_replay']['state_advanced'])
        self.assertEqual(result['assessments']['operating_readiness'], 'NOT_ASSESSED')

    def test_source_identity_and_phase_transition_reject_changes(self):
        data = self.example().to_dict()
        data['source_hashes']['physicroll/operational_replay.py'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source hash mismatch'):
            run_workflow(RunSpec(data))
        data = self.example().to_dict()
        data['observations']['samples'][1]['transition_provenance'] = None
        with self.assertRaisesRegex(ValueError, 'transition provenance'):
            run_workflow(RunSpec(data))

    def test_rejects_recipe_actual_substitution_and_solver_claim(self):
        data = self.example().to_dict()
        data['recipe_targets']['recipes'][0]['targets'][0]['value'] = 3.0
        report = run_workflow(RunSpec(data)).to_dict()['outputs']['operating_replay']
        steady = report['samples'][3]
        self.assertEqual(steady['sample']['applied_references'][0]['value'], 1.9)
        self.assertEqual(next(item['value'] for item in steady['sample']['measurements']
                              if item['quantity'] == 'entry_speed_m_s'), 1.8)
        data = self.example().to_dict()
        data['model_choices']['solver'] = 'spatial_slab'
        with self.assertRaisesRegex(ValueError, 'no solver'):
            run_workflow(RunSpec(data))

    def test_malformed_recipe_identity_rejects_as_validation_error(self):
        data = self.example().to_dict()
        data['recipe_targets']['recipes'][0]['recipe_id'] = []
        with self.assertRaisesRegex(ValueError, 'recipe identity'):
            run_workflow(RunSpec(data))


if __name__ == '__main__':
    unittest.main()
