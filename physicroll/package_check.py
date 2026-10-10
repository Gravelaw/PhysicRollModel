"""Offline check of examples and audited resources in an installed wheel."""

import json
from dataclasses import replace

from .conditional_shao import (compare_existing_fixture,
                               run_conditional_comparison,
                               run_declared_prior_sensitivity)
from .literature import load_case
from .model import Scenario, solve
from .resources import read_example, resource_directory, resource_file
from .run_contract import RunSpec
from .workflows import run_checked_spec, run_workflow
from .transient_t2 import WoundRecord
from .transient_t2_two_reel import (CONTINUE_ISOLATED_SEQUENCE,
                                    run_two_reel_episode)
from .transient_t2_two_reel_workflow import episode_from_spec


def main():
    baseline = read_example('baseline.json')
    result = solve(Scenario.from_dict(baseline))
    if not (abs(result['mass_flow_kg_s'] - 10.8) < 1e-10 and
            2.19e6 < result['separating_force_n'] < 2.21e6):
        raise AssertionError('packaged baseline result changed')
    spec = RunSpec(read_example('v1_checked_pass.runspec.json'))
    if spec.to_dict()['workflow_kind'] != 'checked_pass':
        raise AssertionError('packaged RunSpec kind changed')
    bundle = run_checked_spec(spec)
    bundle.verify_run_spec(spec)
    replay = bundle.to_dict()['outputs']['checked_schedule']
    if (not replay['passes'][0]['mechanics']['numerical_converged'] or
            replay['declared_bounds_status'] != 'INDETERMINATE'):
        raise AssertionError('packaged checked example changed')
    for name in ('scenario.schema.json', 'run-spec-v1.schema.json',
                 'result-bundle-v1.schema.json'):
        if not isinstance(json.loads(resource_file('schemas', name).read_text()), dict):
            raise AssertionError(f'invalid packaged schema: {name}')
    case = load_case(resource_directory('shao_fixture'))
    if case['unit_audit']['converted_numeric_values'] != 49:
        raise AssertionError('packaged benchmark unit audit changed')
    if compare_existing_fixture():
        raise AssertionError('packaged audited source and fixture disagree')
    comparison = run_conditional_comparison()
    if comparison['status'] != 'CONDITIONAL_COMPARISON_NOT_VALIDATION':
        raise AssertionError('packaged conditional comparison changed')
    sensitivity = run_declared_prior_sensitivity()
    if [item['status'] for item in sensitivity['cases']] != [
            'REJECTED_BY_CHECKED_MODEL',
            'CONDITIONAL_REPLAY_INDETERMINATE',
            'CONDITIONAL_REPLAY_INDETERMINATE',
            'CONDITIONAL_REPLAY_INDETERMINATE']:
        raise AssertionError('packaged prior sensitivity changed')
    for name in ('v1_shao_benchmark.runspec.json',
                 'v1_shao_sensitivity.runspec.json'):
        conditional_spec = RunSpec(read_example(name))
        conditional_result = run_workflow(conditional_spec)
        conditional_result.verify_run_spec(conditional_spec)
        if conditional_result.to_dict()['assessments']['scientific_qualification'] != 'NOT_ASSESSED':
            raise AssertionError('conditional result gained unsupported qualification')
    operating_spec = RunSpec(read_example('v1_operating_replay.runspec.json'))
    operating_result = run_workflow(operating_spec)
    operating_result.verify_run_spec(operating_spec)
    operating = operating_result.to_dict()
    if (operating['assessments']['predictions_computed'] or
            len(operating['outputs']['operating_replay']['samples']) != 7):
        raise AssertionError('packaged O0 replay changed')
    search_spec = RunSpec(read_example('v1_schedule_search.runspec.json'))
    search_result = run_workflow(search_spec)
    search_result.verify_run_spec(search_spec)
    search = search_result.to_dict()['outputs']['schedule_search']
    if (search['evaluations'] != 3 or search['selected'] is None or
            search['status'] != 'SELECTED_DECLARED_BOUNDS_INDETERMINATE'):
        raise AssertionError('packaged finite search changed')
    t1_spec = RunSpec(read_example('v1_prescribed_transport_t1.runspec.json'))
    t1_result = run_workflow(t1_spec).to_dict()
    if (t1_result['outputs']['episode_outcome'] != 'TERMINATED_REEL_LIMIT' or
            t1_result['outputs']['completed_duration_s'] >=
            t1_result['outputs']['requested_duration_s'] or
            t1_result['assessments']['numerical_verification'] != 'PASSED'):
        raise AssertionError('packaged T1 transport changed')
    t2_spec = RunSpec(read_example('v1_torque_driven_span_reel_t2.runspec.json'))
    t2_result = run_workflow(t2_spec).to_dict()
    t2 = t2_result['outputs']['torque_driven_span_reel_t2']
    if (t2_result['outputs']['episode_outcome'] != 'COMPLETED_DECLARED_DURATION' or
            t2['torque_role'] != 'prescribed_input' or
            t2['span_and_reel_speed_role'] != 'predicted_from_coupled_dynamics' or
            t2['maximum_combined_inventory_defect_kg'] >= 1e-10 or
            t2_result['assessments']['scientific_qualification'] != 'NOT_ASSESSED'):
        raise AssertionError('packaged T2 span/reel example changed')
    pair_spec = RunSpec(read_example('v1_two_reel_span_t2.runspec.json'))
    pair_result = run_workflow(pair_spec).to_dict()
    pair = pair_result['outputs']['two_reel_span_t2']
    if (pair_result['outputs']['episode_outcome'] != 'COMPLETED_DECLARED_DURATION' or
            pair['torque_role'] != 'prescribed_time_only_input' or
            pair['maximum_combined_inventory_defect_kg'] >= 1e-10 or
            pair_result['assessments']['scientific_qualification'] != 'NOT_ASSESSED'):
        raise AssertionError('packaged two-reel T2 example changed')
    pair_episode = episode_from_spec(pair_spec)
    cut = pair_episode.left.initial_local_cut_m
    boundaries = (cut, cut+.0001, cut+.0002,
                  cut+pair_episode.left.initial_reference_length_m)
    records = tuple(WoundRecord(low, high, 1.01) for low, high in
                    reversed(list(zip(boundaries, boundaries[1:]))))
    sequence = run_two_reel_episode(replace(pair_episode,
        left=replace(pair_episode.left, initial_records=records),
        event_policy=CONTINUE_ISOLATED_SEQUENCE))
    if (sequence['episode_outcome'] != 'COMPLETED_DECLARED_DURATION' or
            [(item['side'], item['kind']) for item in sequence['transitions']] !=
            [('left', 'internal_donor_restart')]*2 or
            sequence['maximum_combined_energy_defect_j'] >= 1e-8):
        raise AssertionError('packaged bounded two-reel event sequence changed')
    print('Installed package check passed: legacy and checked examples, schemas, '
          'audited Shao fixture, conditional workflows, O0 replay, finite search, T1 and T2')


if __name__ == '__main__':
    main()
