"""Public saved-run checks for the restricted prescribed-motion T1 layer."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from physicroll.run_bundle import create_run_bundle, replay_run_bundle, verify_run_bundle
from physicroll.run_contract import RunSpec
from physicroll.transient_t1 import (T1Trajectory, continue_t1,
                                     load_t1_checkpoint, save_t1_checkpoint)
from physicroll.transient_workflow import episode_from_spec
from physicroll.workflows import run_workflow


EXAMPLE = Path(__file__).resolve().parents[1] / 'scenarios/v1_prescribed_transport_t1.runspec.json'


class T1WorkflowTests(unittest.TestCase):
    def test_first_hit_saved_result_has_honest_duration_and_scope(self):
        spec = RunSpec.from_json(EXAMPLE.read_bytes())
        data = run_workflow(spec).to_dict()
        self.assertEqual(data['assessments']['execution'], 'COMPLETED')
        self.assertEqual(data['assessments']['numerical_verification'], 'PASSED')
        self.assertEqual(data['assessments']['scientific_qualification'], 'NOT_ASSESSED')
        self.assertEqual(data['outputs']['episode_outcome'], 'TERMINATED_REEL_LIMIT')
        self.assertAlmostEqual(data['outputs']['completed_duration_s'], .8)
        self.assertEqual(data['outputs']['requested_duration_s'], 2.0)
        self.assertEqual(data['checks']['assessment_scope']['completed_time_s'],
                         data['outputs']['completed_duration_s'])
        self.assertEqual(data['assessments']['declared_bounds_status'], 'WITHIN')
        self.assertEqual(data['outputs']['prescribed_transport_t1']['strip_speed_role'],
                         'prescribed_input')

    def test_missing_optional_capacity_remains_missing_and_contract_rejects_drift(self):
        data = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()
        data['resolved_inputs']['episode']['right_capacity_length_m'] = None
        data['requested_inputs']['episode']['right_capacity_length_m'] = None
        result = run_workflow(RunSpec(data)).to_dict()
        self.assertEqual(result['outputs']['episode_outcome'],
                         'COMPLETED_REQUESTED_DURATION')
        self.assertEqual(result['assessments']['declared_bounds_coverage'], 'PARTIAL')
        self.assertEqual(result['assessments']['declared_bounds_status'], 'INDETERMINATE')
        self.assertNotIn('right:declared_capacity', [item['limit_id'] for item in
                         result['checks']['declared_bounds']['evaluations']])
        data['source_hashes']['physicroll/transient_t1.py'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source'):
            run_workflow(RunSpec(data))
        data['source_hashes'] = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()['source_hashes']
        data['requested_inputs']['episode']['width_m'] = 2.0
        with self.assertRaisesRegex(ValueError, 'must agree'):
            run_workflow(RunSpec(data))
        data['requested_inputs']['episode']['width_m'] = True
        with self.assertRaisesRegex(ValueError, 'must agree'):
            run_workflow(RunSpec(data))

    def test_saved_bundle_replays_and_restart_matches_its_event_suffix(self):
        spec = RunSpec.from_json(EXAMPLE.read_bytes())
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'run'
            saved = create_run_bundle(spec, path)
            verified_spec, verified = verify_run_bundle(path)
            self.assertEqual(verified.sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
            case = episode_from_spec(verified_spec)
            direct = T1Trajectory(case)
            checkpoint_path = Path(temporary) / 'checkpoint.json'
            checkpoint = direct.checkpoint_at(.4, verified_spec.sha256)
            save_t1_checkpoint(checkpoint_path, checkpoint)
            suffix = continue_t1(case, load_t1_checkpoint(checkpoint_path),
                                 verified_spec.sha256).result()
            self.assertEqual(suffix['final_state'], direct.state_at(direct.stop_time_s))
            self.assertEqual(suffix['remaining_events'],
                             list(direct.events)[checkpoint['next_event_index']:])
            self.assertEqual(saved.to_dict()['outputs']['prescribed_transport_t1'],
                             direct.result())


if __name__ == '__main__':
    unittest.main()
