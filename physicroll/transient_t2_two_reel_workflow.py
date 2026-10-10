"""Source-bound public adapter for the pre-engaged two-reel T2 interval."""

from dataclasses import fields
import hashlib
from importlib.resources import files

from .run_contract import ResultBundle, RunSpec, T2_CONVENTIONS, canonical_json
from .transient_t2 import WoundRecord
from .transient_t2_two_reel import (MODEL_ID, ReelEnd, TwoReelEpisode,
                                    run_two_reel_episode)


WORKFLOW_KIND = 'two_reel_span_t2'
MODEL_CHOICES = {
    'solver': MODEL_ID,
    'material': 'synthetic_linear_elastic_EA10N_mu0p1kg_m',
    'bite': 'not_modeled',
    'thermal': 'idealized_pickup_dissipation_only',
}
NUMERICAL_SETTINGS = {
    'spatial_flux': 'minmod_muscl_hll_finite_volume',
    'time_integrator': 'heun_preengaged_reel_admissibility_stop',
    'torque_interpolation': 'linear_from_declared_knots',
    'EA_n': 10.0,
    'reference_line_mass_kg_m': 0.1,
    'span_length_m': 1.0,
    'reel_core_radius_m': 0.1,
    'reel_core_inertia_kg_m2': 0.01,
    'reel_radial_growth_m2_per_reference_m': .001 / 3.141592653589793,
    'combined_inventory_tolerance_kg': 1e-10,
    'combined_energy_tolerance_j': 1e-8,
    'reel_energy_tolerance_j': 1e-8,
    'reel_angular_impulse_tolerance_nm_s': 1e-8,
}
SOURCE_MODULES = (
    'transient_t2.py', 'transient_t2_two_reel.py',
    'transient_t2_two_reel_workflow.py', 'transient_t2a5.py',
    'transient_t2a6.py', 'transient_t2a7.py', 'transient_t2a8.py',
)


def source_hashes():
    root = files('physicroll')
    return {'physicroll/'+name: hashlib.sha256(root.joinpath(name).read_bytes()).hexdigest()
            for name in SOURCE_MODULES}


def _end_from_dict(data):
    if type(data) is not dict or set(data) != {field.name for field in fields(ReelEnd)}:
        raise ValueError('T2 two-reel end must declare every supported field')
    data = dict(data)
    if (type(data['initial_records']) is not list or
            any(type(item) is not dict or set(item) != {
                'low_label_m', 'high_label_m', 'retained_stretch'}
                for item in data['initial_records'])):
        raise ValueError('T2 two-reel records must declare ordered label bounds')
    data['initial_records'] = tuple(WoundRecord(**item)
                                    for item in data['initial_records'])
    if (type(data['applied_torque_history']) is not list or
            any(type(item) is not list for item in data['applied_torque_history'])):
        raise ValueError('T2 two-reel torque history must be an array of arrays')
    data['applied_torque_history'] = tuple(tuple(item)
                                           for item in data['applied_torque_history'])
    return ReelEnd(**data)


def episode_from_spec(spec: RunSpec) -> TwoReelEpisode:
    if not isinstance(spec, RunSpec):
        raise ValueError('T2 two-reel adapter requires a RunSpec')
    data = spec.to_dict()
    if data['workflow_kind'] != WORKFLOW_KIND:
        raise ValueError('RunSpec is not a T2 two-reel workflow')
    if (data['unit_conventions'] != T2_CONVENTIONS or
            data['model_choices'] != MODEL_CHOICES or
            data['identities']['model_version'] != MODEL_ID or
            any(data['identities'][key] is not None for key in
                ('material_id', 'state_id', 'recipe_id')) or
            data['source_hashes'] != source_hashes() or data['card_hashes'] or
            data['numerical_settings'] != NUMERICAL_SETTINGS or
            data['recipe_targets'] or data['observations']):
        raise ValueError('T2 two-reel model, source or numerical policy differs')
    if (set(data['requested_inputs']) != {'episode'} or
            canonical_json(data['requested_inputs']) !=
            canonical_json(data['resolved_inputs'])):
        raise ValueError('T2 two-reel requested/resolved episode must agree exactly')
    episode = data['resolved_inputs']['episode']
    if type(episode) is not dict or set(episode) != {
            field.name for field in fields(TwoReelEpisode)}:
        raise ValueError('T2 two-reel episode must declare every supported field')
    episode = dict(episode)
    if (type(episode['initial_conserved_fields']) is not list or
            any(type(item) is not list for item in
                episode['initial_conserved_fields'])):
        raise ValueError('T2 two-reel conserved fields must be an array of arrays')
    episode['initial_conserved_fields'] = tuple(
        tuple(item) for item in episode['initial_conserved_fields'])
    if type(episode['observation_times_s']) is not list:
        raise ValueError('T2 two-reel observations must be an array')
    episode['observation_times_s'] = tuple(episode['observation_times_s'])
    for side in ('left', 'right'):
        episode[side] = _end_from_dict(episode[side])
    return TwoReelEpisode(**episode)


def run_two_reel_spec(spec: RunSpec) -> ResultBundle:
    episode = episode_from_spec(spec)
    transport = run_two_reel_episode(episode)
    final = transport['accepted_states'][-1]
    balanced = (
        transport['maximum_combined_inventory_defect_kg'] <=
        NUMERICAL_SETTINGS['combined_inventory_tolerance_kg'] and
        transport['maximum_combined_energy_defect_j'] <=
        NUMERICAL_SETTINGS['combined_energy_tolerance_j'] and
        transport['maximum_reel_cumulative_energy_defect_j'] <=
        NUMERICAL_SETTINGS['reel_energy_tolerance_j'] and
        transport['maximum_reel_angular_impulse_defect_nm_s'] <=
        NUMERICAL_SETTINGS['reel_angular_impulse_tolerance_nm_s'] and
        transport['maximum_reconstructed_stage_courant'] <=
        episode.cfl_limit*(1+1e-12))
    limits = {
        'taut_span': transport['minimum_used_stretch'] > 1,
        'nonempty_left_reel': final['ends']['left']['reference_length_m'] > 0,
        'nonempty_right_reel': final['ends']['right']['reference_length_m'] > 0,
        'declared_episode_duration': final['time_s'] <= episode.duration_s+1e-12,
        'stopped_before_requested_end': (transport['episode_outcome'] ==
            'COMPLETED_DECLARED_DURATION' or final['time_s'] < episode.duration_s),
        'declared_spatial_grid': episode.cell_count in (64, 128, 256),
    }
    return ResultBundle({
        'schema_version': '1', 'run_spec_sha256': spec.sha256,
        'effective_inputs': {'episode': spec.to_dict()['resolved_inputs']['episode'],
                             'model_id': MODEL_ID,
                             'applied_torque_role': 'prescribed_time_only_input',
                             'two_reel_role': 'predicted_local_winding_axis_speeds'},
        'outputs': {'two_reel_span_t2': transport,
                    'episode_outcome': transport['episode_outcome'],
                    'requested_duration_s': episode.duration_s,
                    'completed_duration_s': final['time_s'],
                    'output_role': 'predicted_preengaged_elastic_span_and_two_reels'},
        'checks': {
            'declared_bounds': {'required_limit_ids': list(limits),
                'evaluations': [{'limit_id': name,
                                 'status': 'WITHIN' if passed else 'VIOLATED'}
                                for name, passed in limits.items()]},
            'assessment_scope': {'start_time_s': 0.,
                                 'completed_time_s': final['time_s'],
                                 'requested_time_s': episode.duration_s},
            'internal_numerical_diagnostics': {
                'maximum_combined_inventory_defect_kg':
                    transport['maximum_combined_inventory_defect_kg'],
                'maximum_combined_energy_defect_j':
                    transport['maximum_combined_energy_defect_j'],
                'maximum_reel_cumulative_energy_defect_j':
                    transport['maximum_reel_cumulative_energy_defect_j'],
                'maximum_reel_angular_impulse_defect_nm_s':
                    transport['maximum_reel_angular_impulse_defect_nm_s'],
                'maximum_reconstructed_stage_courant':
                    transport['maximum_reconstructed_stage_courant'],
                'passed_internal_balances_only': balanced},
            'independent_benchmark_verification': 'NOT_ASSESSED_FOR_THIS_RUN',
        },
        'assessments': {
            'execution': 'COMPLETED', 'input_validity': 'VALID',
            'model_applicability': ('IN_DOMAIN' if transport['episode_outcome'] ==
                                    'COMPLETED_DECLARED_DURATION' else
                                    'INDETERMINATE'),
            'numerical_verification': 'NOT_ASSESSED' if balanced else 'FAILED',
            'declared_bounds_status': 'WITHIN' if all(limits.values()) else 'VIOLATED',
            'declared_bounds_coverage': 'COMPLETE',
            'scientific_qualification': 'NOT_ASSESSED',
            'operating_readiness': 'NOT_ASSESSED',
            'predictions_computed': True, 'qualification_evidence_refs': [],
        },
    })
