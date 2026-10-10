"""Public source-bound and verified saved-run checks for two-reel T2."""

from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import asdict
import unittest

from physicroll.run_bundle import create_run_bundle, replay_run_bundle, verify_run_bundle
from physicroll.run_contract import RunSpec
from physicroll.transient_t2_two_reel_workflow import episode_from_spec
from physicroll.workflows import run_workflow
from tests.test_transient_t2_two_reel import (affine_two_release_case,
                                              depletion_case,
                                              isolated_donor_case,
                                              standing_reversal_case)
from tests.test_transient_t2_recapture import wave_case
from tests.test_transient_t2_event_sequence import split_wave_case


EXAMPLE = (Path(__file__).resolve().parents[1] /
           'scenarios/v1_two_reel_span_t2.runspec.json')


class TwoReelWorkflowTests(unittest.TestCase):
    def test_bounded_sequence_is_source_bound_and_replayable(self):
        payload = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()
        episode = asdict(split_wave_case(64))
        payload['requested_inputs']['episode'] = episode
        payload['resolved_inputs']['episode'] = episode
        spec = RunSpec(payload)
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'bounded-event-sequence'
            saved = create_run_bundle(spec, path)
            self.assertEqual(verify_run_bundle(path)[1].sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
            result = saved.to_dict()['outputs']['two_reel_span_t2']
            self.assertEqual(result['episode_outcome'],
                             'COMPLETED_DECLARED_DURATION')
            self.assertEqual(len(result['transitions']), 5)
            self.assertLessEqual(result['cumulative_absolute_event_storage_bound_j'],
                                 result['maximum_cumulative_event_storage_bound_j'])
            self.assertEqual(saved.to_dict()['assessments'][
                'scientific_qualification'], 'NOT_ASSESSED')

    def test_recapture_is_source_bound_and_replayable(self):
        payload = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()
        episode = asdict(wave_case(64, torque_knots=100))
        payload['requested_inputs']['episode'] = episode
        payload['resolved_inputs']['episode'] = episode
        spec = RunSpec(payload)
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'release-to-wind'
            saved = create_run_bundle(spec, path)
            self.assertEqual(verify_run_bundle(path)[1].sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
            result = saved.to_dict()['outputs']['two_reel_span_t2']
            self.assertEqual(result['episode_outcome'],
                             'COMPLETED_DECLARED_DURATION')
            self.assertEqual([(event['side'], event['kind']) for event in
                              result['transitions']],
                             [('right', 'release_to_wind')])
            self.assertEqual(result['accepted_states'][-1]['ends']['right'][
                'phase'], 'wind')
            self.assertEqual(result['original_initial_records']['right'][0][
                'retained_stretch'], 1.0125)

    def test_isolated_donor_restart_is_source_bound_and_replayable(self):
        payload = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()
        episode = asdict(isolated_donor_case())
        payload['requested_inputs']['episode'] = episode
        payload['resolved_inputs']['episode'] = episode
        spec = RunSpec(payload)
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'isolated-donor-restart'
            saved = create_run_bundle(spec, path)
            self.assertEqual(verify_run_bundle(path)[1].sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
            data = saved.to_dict()
            result = data['outputs']['two_reel_span_t2']
            self.assertEqual(result['episode_outcome'],
                             'COMPLETED_DECLARED_DURATION')
            self.assertEqual(result['events'], [])
            self.assertEqual(len(result['transitions']), 1)
            transition = result['transitions'][0]
            self.assertEqual(transition['old_donor']['retained_stretch'], 1.01)
            self.assertEqual(transition['new_donor']['retained_stretch'], 1.02)
            self.assertLessEqual(transition['terminal_label_overshoot_m'], 1e-13)
            self.assertAlmostEqual(data['outputs']['completed_duration_s'], .04)
            self.assertEqual(data['assessments']['scientific_qualification'],
                             'NOT_ASSESSED')

    def test_corrected_reversal_is_source_bound_and_replayable(self):
        payload = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()
        episode = asdict(standing_reversal_case(torque_knots=100))
        payload['requested_inputs']['episode'] = episode
        payload['resolved_inputs']['episode'] = episode
        spec = RunSpec(payload)
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'reversal-stop'
            saved = create_run_bundle(spec, path)
            self.assertEqual(verify_run_bundle(path)[1].sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
            data = saved.to_dict()
            events = data['outputs']['two_reel_span_t2']['events']
            self.assertEqual([(item['side'], item['kind']) for item in events],
                             [('left', 'reversal'), ('right', 'reversal')])
            for event in events:
                low, high = event['corrected_reversal_bracket_time_s']
                self.assertAlmostEqual(
                    event['corrected_reversal_gap_after_feasible_stop_s'],
                    low-data['outputs']['completed_duration_s'], delta=1e-14)
                self.assertLess(high-low, 1e-11)
            self.assertEqual(data['assessments']['scientific_qualification'],
                             'NOT_ASSESSED')

    def test_depletion_stop_is_source_bound_and_replayable(self):
        payload = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()
        episode = asdict(depletion_case())
        payload['requested_inputs']['episode'] = episode
        payload['resolved_inputs']['episode'] = episode
        spec = RunSpec(payload)
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'depletion-stop'
            saved = create_run_bundle(spec, path)
            self.assertEqual(verify_run_bundle(path)[1].sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
            data = saved.to_dict()
            output = data['outputs']['two_reel_span_t2']
            self.assertEqual(output['events'][0]['kind'], 'depletion')
            self.assertGreater(output['accepted_states'][-1]['ends']['left'][
                'reference_length_m'], 0.)
            self.assertLess(data['outputs']['completed_duration_s'],
                            data['outputs']['requested_duration_s'])
            self.assertEqual(data['assessments']['model_applicability'],
                             'INDETERMINATE')
            self.assertEqual(data['assessments']['scientific_qualification'],
                             'NOT_ASSESSED')

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
        episode['event_policy'] = 'stop_at_numerical_admissibility_limit'
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
                             'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
            self.assertLess(data['outputs']['completed_duration_s'],
                            data['outputs']['requested_duration_s'])
            self.assertEqual(data['assessments']['model_applicability'],
                             'INDETERMINATE')
            self.assertEqual(data['assessments']['scientific_qualification'],
                             'NOT_ASSESSED')
            self.assertEqual(data['outputs']['two_reel_span_t2']['events'][0][
                'event_time_interpretation'],
                'numerical_bracket_not_physical_event_time')
            event = data['outputs']['two_reel_span_t2']['events'][0]
            self.assertEqual(event['corrected_arrival_status'],
                             'bracketed_in_complete_trial')
            self.assertIsNotNone(event['corrected_arrival_bracket_time_s'])

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
        episode['event_policy'] = 'stop_at_numerical_admissibility_limit'
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

    def test_tension_stop_is_saved_and_replayed_with_actual_duration(self):
        payload = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()
        episode = asdict(affine_two_release_case())
        payload['requested_inputs']['episode'] = episode
        payload['resolved_inputs']['episode'] = episode
        spec = RunSpec(payload)
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'tension-stop'
            saved = create_run_bundle(spec, path)
            self.assertEqual(verify_run_bundle(path)[1].sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
            data = saved.to_dict()
            self.assertEqual(data['outputs']['episode_outcome'],
                             'STOPPED_AT_NUMERICAL_ADMISSIBILITY_LIMIT')
            self.assertEqual(data['outputs']['two_reel_span_t2']['events'][0][
                'kind'], 'tension_zero')
            self.assertAlmostEqual(data['outputs']['completed_duration_s'],
                                   .05, delta=5e-5)
            self.assertEqual(data['assessments']['model_applicability'],
                             'INDETERMINATE')
            self.assertEqual(data['assessments']['scientific_qualification'],
                             'NOT_ASSESSED')

    def test_grouped_numerical_limits_replay_without_simultaneity_claim(self):
        payload = RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()
        episode = asdict(affine_two_release_case())
        for side, shift in (('left', 0.), ('right', 5e-11)):
            cut = episode[side]['initial_local_cut_m']
            boundary = cut+.001+shift
            episode[side]['initial_records'] = [
                {'low_label_m': boundary, 'high_label_m': cut+1.,
                 'retained_stretch': 1.02},
                {'low_label_m': cut, 'high_label_m': boundary,
                 'retained_stretch': 1.01}]
        payload['requested_inputs']['episode'] = episode
        payload['resolved_inputs']['episode'] = episode
        spec = RunSpec(payload)
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'grouped-stop'
            saved = create_run_bundle(spec, path)
            self.assertEqual(verify_run_bundle(path)[1].sha256, saved.sha256)
            self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
            events = saved.to_dict()['outputs']['two_reel_span_t2']['events']
            self.assertEqual([item['bracket_relation_to_selected']
                              for item in events],
                             ['selected_lowest_feasible_bracket',
                              'within_numerical_coincidence_tolerance'])
            self.assertEqual(events[1]['grouping_interpretation'],
                             'numerical_only_not_physical_simultaneity')
            stop = saved.to_dict()['outputs']['completed_duration_s']
            for event in events:
                self.assertAlmostEqual(
                    event['corrected_arrival_gap_after_feasible_stop_s'],
                    event['corrected_arrival_bracket_time_s'][0]-stop,
                    delta=1e-15)


if __name__ == '__main__':
    unittest.main()
