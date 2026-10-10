"""Saved-run adapter for restricted T1 prescribed strip and reel transport."""

from dataclasses import fields
import hashlib
from importlib.resources import files
import math

from .run_contract import ResultBundle, RunSpec, canonical_json
from .transient_t1 import MODEL_ID, T1Episode, T1Trajectory


MODEL_CHOICES = {
    'solver': MODEL_ID, 'material': 'uniform_constant_density',
    'bite': 'not_modeled', 'thermal': 'not_modeled',
}
NUMERICAL_SETTINGS = {
    'speed_interpolation': 'continuous_piecewise_linear',
    'mass_residual_tolerance_kg': 1e-9,
    'geometry_residual_tolerance_m': 1e-10,
}
SOURCE_MODULES = ('transient_t1.py', 'transient_workflow.py')


def source_hashes():
    root = files('physicroll')
    return {'physicroll/' + name: hashlib.sha256(root.joinpath(name).read_bytes()).hexdigest()
            for name in SOURCE_MODULES}


def episode_from_spec(spec: RunSpec) -> T1Episode:
    """Resolve a fully declared immutable episode with no hidden input changes."""
    if not isinstance(spec, RunSpec):
        raise ValueError('T1 adapter requires a RunSpec')
    data = spec.to_dict()
    if data['workflow_kind'] != 'prescribed_transport_t1':
        raise ValueError('RunSpec is not a T1 prescribed-transport workflow')
    if (data['model_choices'] != MODEL_CHOICES or
            data['identities']['model_version'] != MODEL_ID or
            any(data['identities'][key] is not None for key in
                ('material_id', 'state_id', 'recipe_id')) or
            data['source_hashes'] != source_hashes() or data['card_hashes'] or
            data['numerical_settings'] != NUMERICAL_SETTINGS or
            data['recipe_targets'] or data['observations']):
        raise ValueError('T1 model, source, numerical policy or unsupported inputs differ')
    if (set(data['requested_inputs']) != {'episode'} or
            canonical_json(data['requested_inputs']) !=
            canonical_json(data['resolved_inputs'])):
        raise ValueError('T1 requested/resolved episode must agree exactly')
    episode = data['resolved_inputs']['episode']
    if type(episode) is not dict or set(episode) != {field.name for field in fields(T1Episode)}:
        raise ValueError('T1 episode must declare all and only the supported fields')
    for name in ('times_s', 'prescribed_strip_speed_m_s',
                 'declared_feed_speed_m_s', 'declared_take_up_speed_m_s'):
        if episode[name] is not None:
            if type(episode[name]) is not list:
                raise ValueError(f'{name} must be an array')
            episode[name] = tuple(episode[name])
    if type(episode['parcels']) is not list or any(
            type(item) is not list or len(item) != 2 for item in episode['parcels']):
        raise ValueError('T1 parcels must be pairs')
    episode['parcels'] = tuple(tuple(item) for item in episode['parcels'])
    return T1Episode(**episode)


def run_t1_spec(spec: RunSpec) -> ResultBundle:
    episode = episode_from_spec(spec)
    trajectory = T1Trajectory(episode)
    transport = trajectory.result()
    states = transport['states']
    initial_length = (episode.left_initial_length_m + episode.free_span_length_m +
                      episode.right_initial_length_m)
    length_residual = max(abs(state['left_length_m'] + episode.free_span_length_m +
                              state['right_length_m'] - initial_length) for state in states)
    geometry_residual = max(
        abs(math.pi * (state[f'{side}_radius_m'] ** 2 -
                       getattr(episode, f'{side}_core_radius_m') ** 2) /
            episode.thickness_m - state[f'{side}_length_m'])
        for state in states for side in ('left', 'right'))
    event_ordered = (transport['events'] == sorted(
        transport['events'], key=lambda item: (item['time_s'], item['event'],
                                                item.get('parcel_id', ''))) and
        all(0 <= event['time_s'] <= trajectory.stop_time_s
            for event in transport['events']))
    checks_passed = (transport['maximum_total_mass_residual_kg'] <=
                     NUMERICAL_SETTINGS['mass_residual_tolerance_kg'] and
                     length_residual <= NUMERICAL_SETTINGS['geometry_residual_tolerance_m'] and
                     geometry_residual <= NUMERICAL_SETTINGS['geometry_residual_tolerance_m'] and
                     event_ordered)
    required = [f'{side}:{limit}' for side in ('left', 'right')
                for limit in ('nonempty_inventory', 'declared_capacity')]
    evaluations = []
    for side in ('left', 'right'):
        remaining = [state[f'{side}_length_m'] for state in states]
        evaluations.append({'limit_id': f'{side}:nonempty_inventory',
                            'status': 'WITHIN' if min(remaining) >= -1e-10 else 'VIOLATED'})
        capacity = getattr(episode, f'{side}_capacity_length_m')
        if capacity is not None:
            evaluations.append({'limit_id': f'{side}:declared_capacity',
                                'status': 'WITHIN' if max(remaining) <= capacity + 1e-10
                                else 'VIOLATED'})
    coverage = 'COMPLETE' if len(evaluations) == len(required) else 'PARTIAL'
    bounds_status = ('VIOLATED' if any(item['status'] == 'VIOLATED' for item in evaluations)
                     else 'WITHIN' if coverage == 'COMPLETE' else 'INDETERMINATE')
    return ResultBundle({
        'schema_version': '1', 'run_spec_sha256': spec.sha256,
        'effective_inputs': {'episode': data_episode(spec),
                             'model_id': MODEL_ID,
                             'speed_role': 'prescribed_input'},
        'outputs': {
            'prescribed_transport_t1': transport,
            'episode_outcome': ('TERMINATED_REEL_LIMIT' if trajectory.terminal_event
                                else 'COMPLETED_REQUESTED_DURATION'),
            'requested_duration_s': episode.times_s[-1],
            'completed_duration_s': trajectory.stop_time_s,
            'output_role': 'kinematically_derived_from_prescribed_speed',
        },
        'checks': {
            'declared_bounds': {'required_limit_ids': required, 'evaluations': evaluations},
            'assessment_scope': {'start_time_s': 0.0,
                                 'completed_time_s': trajectory.stop_time_s,
                                 'requested_time_s': episode.times_s[-1]},
            'internal_analytic_consistency': {
                'maximum_total_mass_residual_kg': transport['maximum_total_mass_residual_kg'],
                'maximum_total_length_residual_m': length_residual,
                'maximum_annular_length_residual_m': geometry_residual,
                'event_ordered_and_in_executed_interval': event_ordered,
                'passed': checks_passed,
            },
        },
        'assessments': {
            'execution': 'COMPLETED', 'input_validity': 'VALID',
            'model_applicability': 'IN_DOMAIN',
            'numerical_verification': 'PASSED' if checks_passed else 'FAILED',
            'declared_bounds_status': bounds_status,
            'declared_bounds_coverage': coverage,
            'scientific_qualification': 'NOT_ASSESSED',
            'operating_readiness': 'NOT_ASSESSED',
            'predictions_computed': True, 'qualification_evidence_refs': [],
        },
    })


def data_episode(spec):
    return spec.to_dict()['resolved_inputs']['episode']
