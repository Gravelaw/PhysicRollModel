"""Public and saved-run checks for the bounded integrated T2 episode."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from physicroll.run_bundle import create_run_bundle, replay_run_bundle, verify_run_bundle
from physicroll.run_contract import RunSpec
from physicroll.transient_t2_workflow import episode_from_spec
from physicroll.workflows import run_workflow


EXAMPLE = (Path(__file__).resolve().parents[1] /
           'scenarios/v1_torque_driven_span_reel_t2.runspec.json')


class T2WorkflowTests(unittest.TestCase):
    def test_public_roles_diagnostics_and_source_binding(self):
        spec = RunSpec.from_json(EXAMPLE.read_bytes())
        episode = episode_from_spec(spec)
        result = run_workflow(spec)
        result.verify_run_spec(spec)
        data = result.to_dict()
        self.assertEqual(data['outputs']['episode_outcome'],
                         'COMPLETED_DECLARED_DURATION')
        self.assertEqual(data['outputs']['completed_duration_s'], episode.duration_s)
        self.assertEqual(data['effective_inputs']['applied_torque_role'],
                         'prescribed_input')
        self.assertEqual(data['outputs']['torque_driven_span_reel_t2'][
            'span_and_reel_speed_role'], 'predicted_from_coupled_dynamics')
        self.assertEqual(data['assessments']['numerical_verification'],
                         'NOT_ASSESSED')
        self.assertEqual(data['assessments']['scientific_qualification'],
                         'NOT_ASSESSED')
        self.assertTrue(data['checks']['internal_numerical_diagnostics'][
            'passed_internal_balances_only'])
        altered = spec.to_dict()
        altered['source_hashes']['physicroll/transient_t2.py'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source'):
            run_workflow(RunSpec(altered))
        altered = spec.to_dict()
        altered['requested_inputs']['episode']['duration_s'] = .006
        with self.assertRaisesRegex(ValueError, 'must agree'):
            run_workflow(RunSpec(altered))

    def test_verified_bundle_replays_identically(self):
        spec = RunSpec.from_json(EXAMPLE.read_bytes())
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 't2'
            saved = create_run_bundle(spec, path)
            verified_spec, verified_result = verify_run_bundle(path)
            self.assertEqual(verified_spec.sha256, spec.sha256)
            self.assertEqual(verified_result.sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)


if __name__ == '__main__':
    unittest.main()
