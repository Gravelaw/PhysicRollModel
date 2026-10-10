"""Public source-bound and verified saved-run checks for two-reel T2."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from physicroll.run_bundle import create_run_bundle, replay_run_bundle, verify_run_bundle
from physicroll.run_contract import RunSpec
from physicroll.transient_t2_two_reel_workflow import episode_from_spec
from physicroll.workflows import run_workflow


EXAMPLE = (Path(__file__).resolve().parents[1] /
           'scenarios/v1_two_reel_span_t2.runspec.json')


class TwoReelWorkflowTests(unittest.TestCase):
    def test_public_roles_source_and_input_binding(self):
        spec = RunSpec.from_json(EXAMPLE.read_bytes())
        episode = episode_from_spec(spec)
        result = run_workflow(spec)
        result.verify_run_spec(spec)
        data = result.to_dict()
        self.assertEqual(data['outputs']['episode_outcome'],
                         'COMPLETED_DECLARED_DURATION')
        self.assertEqual(data['outputs']['completed_duration_s'], episode.duration_s)
        self.assertEqual(data['effective_inputs']['applied_torque_role'],
                         'prescribed_time_only_input')
        self.assertEqual(data['assessments']['numerical_verification'],
                         'NOT_ASSESSED')
        self.assertEqual(data['assessments']['scientific_qualification'],
                         'NOT_ASSESSED')
        self.assertTrue(data['checks']['internal_numerical_diagnostics'][
            'passed_internal_balances_only'])
        altered = spec.to_dict()
        altered['source_hashes']['physicroll/transient_t2_two_reel.py'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'source'):
            run_workflow(RunSpec(altered))
        altered = spec.to_dict()
        altered['requested_inputs']['episode']['left']['initial_local_cut_m'] += .01
        with self.assertRaisesRegex(ValueError, 'must agree'):
            run_workflow(RunSpec(altered))

    def test_verified_bundle_replays_identically(self):
        spec = RunSpec.from_json(EXAMPLE.read_bytes())
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'two-reel'
            saved = create_run_bundle(spec, path)
            checked_spec, checked_result = verify_run_bundle(path)
            self.assertEqual(checked_spec.sha256, spec.sha256)
            self.assertEqual(checked_result.sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)

    def test_stopped_donor_result_is_source_bound_and_replayable(self):
        payload = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()
        episode = payload['requested_inputs']['episode']
        cut = episode['left']['initial_local_cut_m']
        boundary = cut+.000303
        episode['left']['initial_records'] = [
            {'low_label_m': boundary, 'high_label_m': cut+1.,
             'retained_stretch': 1.02},
            {'low_label_m': cut, 'high_label_m': boundary,
             'retained_stretch': 1.01}]
        episode['event_policy'] = 'stop_at_reel_admissibility_limit'
        payload['resolved_inputs']['episode'] = episode
        spec = RunSpec(payload)
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'stopped-two-reel'
            saved = create_run_bundle(spec, path)
            checked_spec, checked_result = verify_run_bundle(path)
            self.assertEqual(checked_spec.sha256, spec.sha256)
            self.assertEqual(checked_result.sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
            data = saved.to_dict()
            self.assertEqual(data['outputs']['episode_outcome'],
                             'STOPPED_AT_REEL_ADMISSIBILITY_LIMIT')
            self.assertLess(data['outputs']['completed_duration_s'],
                            data['outputs']['requested_duration_s'])
            self.assertEqual(data['assessments']['model_applicability'],
                             'INDETERMINATE')
            self.assertEqual(data['assessments']['scientific_qualification'],
                             'NOT_ASSESSED')
            self.assertEqual(data['outputs']['two_reel_span_t2']['events'][0][
                'event_time_interpretation'],
                'numerical_bracket_not_physical_event_time')

    def test_initial_donor_proximity_serializes_a_zero_step_stop(self):
        payload = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()
        episode = payload['requested_inputs']['episode']
        cut = episode['left']['initial_local_cut_m']
        boundary = cut+5e-13
        episode['left']['initial_records'] = [
            {'low_label_m': boundary, 'high_label_m': cut+1.,
             'retained_stretch': 1.02},
            {'low_label_m': cut, 'high_label_m': boundary,
             'retained_stretch': 1.01}]
        episode['event_policy'] = 'stop_at_reel_admissibility_limit'
        payload['resolved_inputs']['episode'] = episode
        spec = RunSpec(payload)
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'initial-stop'
            saved = create_run_bundle(spec, path)
            self.assertEqual(verify_run_bundle(path)[1].sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
            result = saved.to_dict()['outputs']['two_reel_span_t2']
            self.assertEqual(result['accepted_states'][-1]['time_s'], 0.)
            self.assertGreater(result['minimum_used_stretch'], 1.)
            self.assertEqual(result['events'][0]['root_basis'],
                             'accepted_state_label_proximity')


if __name__ == '__main__':
    unittest.main()
