"""Offline check of examples and audited resources in an installed wheel."""

import json

from .conditional_shao import (compare_existing_fixture,
                               run_conditional_comparison,
                               run_declared_prior_sensitivity)
from .checked_schedule import CheckedPass, run_checked_schedule
from .literature import load_case
from .materials import MaterialState, PowerHardeningLaw
from .model import Scenario, solve
from .operating import ObservedSignal, PassOperatingPlan, SignalRange
from .resources import read_example, resource_directory, resource_file
from .run_contract import RunSpec


def main():
    baseline = read_example('baseline.json')
    result = solve(Scenario.from_dict(baseline))
    if not (abs(result['mass_flow_kg_s'] - 10.8) < 1e-10 and
            2.19e6 < result['separating_force_n'] < 2.21e6):
        raise AssertionError('packaged baseline result changed')
    spec = RunSpec(read_example('v1_checked_pass.runspec.json'))
    if spec.to_dict()['workflow_kind'] != 'checked_pass':
        raise AssertionError('packaged RunSpec kind changed')
    resolved = spec.to_dict()['resolved_inputs']
    checked_data = resolved['checked_pass']
    scenario = Scenario.from_dict(checked_data['scenario'])
    state_data = resolved['initial_state']
    state = MaterialState(**{**state_data, 'history': tuple(state_data['history'])})
    law = PowerHardeningLaw(**resolved['law'])
    plan_data = checked_data['operating_plan']
    plan = PassOperatingPlan(**{
        **plan_data,
        'ranges': tuple(SignalRange(**item) for item in plan_data['ranges']),
        'observations': tuple(ObservedSignal(**item)
                              for item in plan_data['observations']),
    })
    checked = CheckedPass(
        scenario, plan, checked_data['solver'], checked_data['cells'],
        checked_data['bite_mode'], tuple(checked_data['assumed_strain_range']),
        tuple(checked_data['assumed_temperature_range_k']),
        checked_data['elasticity'], checked_data['heat_boundary'],
        checked_data['passive_contact'], checked_data['fluid_observation'],
        checked_data['roll_body_id'],
    )
    replay = run_checked_schedule((checked,), state, law,
                                  gauge_basis=resolved['gauge_basis'],
                                  layer_count=resolved['layer_count'])
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
    print('Installed package check passed: legacy and checked examples, schemas, '
          'audited Shao fixture, conditional replay and sensitivity')


if __name__ == '__main__':
    main()
