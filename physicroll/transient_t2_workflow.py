"""Public saved-run adapter for the bounded, idealized right-reel T2 model."""

from dataclasses import fields
import hashlib
from importlib.resources import files

from .run_contract import ResultBundle, RunSpec, T2_CONVENTIONS, canonical_json
from .transient_t2 import MODEL_ID, T2Episode, WoundRecord, run_torque_driven_episode


MODEL_CHOICES = {
    'solver': MODEL_ID,
    'material': 'synthetic_linear_elastic_EA10N_mu0p1kg_m',
    'bite': 'not_modeled',
    'thermal': 'idealized_pickup_dissipation_only',
}
NUMERICAL_SETTINGS = {
    'spatial_flux': 'minmod_muscl_hll_finite_volume',
    'time_integrator': 'heun_event_split',
    'torque_interpolation': 'linear_or_cubic_hermite_from_declared_knots',
    'EA_n': 10.0,
    'reference_line_mass_kg_m': 0.1,
    'span_length_m': 1.0,
    'reel_core_radius_m': 0.1,
    'reel_core_inertia_kg_m2': 0.01,
    'reel_radial_growth_m2_per_reference_m': .001 / 3.141592653589793,
    'combined_inventory_tolerance_kg': 1e-10,
    'combined_energy_tolerance_j': 1e-8,
    'reel_angular_impulse_tolerance_nm_s': 1e-8,
}
SOURCE_MODULES = (
    'transient_t2.py', 'transient_t2a5.py', 'transient_t2a6.py',
    'transient_t2a7.py', 'transient_t2a8.py', 'transient_t2_workflow.py',
)


def source_hashes():
    root = files('physicroll')
    return {'physicroll/' + name: hashlib.sha256(root.joinpath(name).read_bytes()).hexdigest()
            for name in SOURCE_MODULES}


def episode_from_spec(spec: RunSpec) -> T2Episode:
    if not isinstance(spec, RunSpec):
        raise ValueError('T2 adapter requires a RunSpec')
    data = spec.to_dict()
    if data['workflow_kind'] != 'torque_driven_span_reel_t2':
        raise ValueError('RunSpec is not a T2 span/reel workflow')
    if (data['unit_conventions'] != T2_CONVENTIONS or
            data['model_choices'] != MODEL_CHOICES or
            data['identities']['model_version'] != MODEL_ID or
            any(data['identities'][key] is not None for key in
                ('material_id', 'state_id', 'recipe_id')) or
            data['source_hashes'] != source_hashes() or data['card_hashes'] or
            data['numerical_settings'] != NUMERICAL_SETTINGS or
            data['recipe_targets'] or data['observations']):
        raise ValueError('T2 model, source, numerical policy or unsupported inputs differ')
    if (set(data['requested_inputs']) != {'episode'} or
            canonical_json(data['requested_inputs']) !=
            canonical_json(data['resolved_inputs'])):
        raise ValueError('T2 requested/resolved episode must agree exactly')
    episode = data['resolved_inputs']['episode']
    if type(episode) is not dict or set(episode) != {field.name for field in fields(T2Episode)}:
        raise ValueError('T2 episode must declare all and only the supported fields')
    for name in ('initial_conserved_fields', 'left_incoming_history',
                 'applied_torque_history'):
        if type(episode[name]) is not list or any(type(item) is not list for item in episode[name]):
            raise ValueError(f'T2 {name} must be an array of arrays')
        episode[name] = tuple(tuple(item) for item in episode[name])
    if type(episode['observation_times_s']) is not list:
        raise ValueError('T2 observation times must be an array')
    episode['observation_times_s'] = tuple(episode['observation_times_s'])
    if type(episode['initial_records']) is not list or any(
            type(item) is not dict or set(item) != {
                'low_label_m', 'high_label_m', 'retained_stretch'}
            for item in episode['initial_records']):
        raise ValueError('T2 initial records must declare label bounds and retained stretch')
    episode['initial_records'] = tuple(WoundRecord(**item)
                                       for item in episode['initial_records'])
    return T2Episode(**episode)


def run_t2_spec(spec: RunSpec) -> ResultBundle:
    episode = episode_from_spec(spec)
    transport = run_torque_driven_episode(episode)
    final = transport['snapshots'][-1]
    balance_passed = (
        transport['maximum_combined_inventory_defect_kg'] <=
        NUMERICAL_SETTINGS['combined_inventory_tolerance_kg'] and
        transport['maximum_combined_energy_defect_j'] <=
        NUMERICAL_SETTINGS['combined_energy_tolerance_j'] and
        transport['maximum_reel_angular_impulse_defect_nm_s'] <=
        NUMERICAL_SETTINGS['reel_angular_impulse_tolerance_nm_s'] and
        transport['maximum_reconstructed_stage_courant'] <= episode.cfl_limit * (1 + 1e-12))
    limits = {
        'taut_span_until_stop': transport['minimum_used_stretch'] >= 1 - 1e-10,
        'nonempty_reel_inventory': final['reel_reference_length_m'] > 0,
        'declared_episode_duration': final['time_s'] <= episode.duration_s + 1e-12,
        'declared_spatial_grid': episode.cell_count in (64, 128, 256),
    }
    evaluations = [{'limit_id': key, 'status': 'WITHIN' if value else 'VIOLATED'}
                   for key, value in limits.items()]
    return ResultBundle({
        'schema_version': '1', 'run_spec_sha256': spec.sha256,
        'effective_inputs': {'episode': spec.to_dict()['resolved_inputs']['episode'],
                             'model_id': MODEL_ID,
                             'applied_torque_role': 'prescribed_input',
                             'left_boundary_role': episode.left_boundary_mode},
        'outputs': {
            'torque_driven_span_reel_t2': transport,
            'episode_outcome': transport['episode_outcome'],
            'requested_duration_s': episode.duration_s,
            'completed_duration_s': final['time_s'],
            'output_role': 'predicted_elastic_span_and_reel_with_idealized_pickup',
        },
        'checks': {
            'declared_bounds': {'required_limit_ids': list(limits),
                                'evaluations': evaluations},
            'assessment_scope': {'start_time_s': 0.0,
                                 'completed_time_s': final['time_s'],
                                 'requested_time_s': episode.duration_s},
            'internal_numerical_diagnostics': {
                'maximum_combined_inventory_defect_kg':
                    transport['maximum_combined_inventory_defect_kg'],
                'maximum_combined_energy_defect_j':
                    transport['maximum_combined_energy_defect_j'],
                'maximum_reel_angular_impulse_defect_nm_s':
                    transport['maximum_reel_angular_impulse_defect_nm_s'],
                'maximum_reconstructed_stage_courant':
                    transport['maximum_reconstructed_stage_courant'],
                'passed_internal_balances_only': balance_passed,
            },
            'independent_benchmark_verification': 'NOT_ASSESSED_FOR_THIS_RUN',
        },
        'assessments': {
            'execution': 'COMPLETED', 'input_validity': 'VALID',
            'model_applicability': ('IN_DOMAIN' if transport['episode_outcome'] in
                                    ('COMPLETED_DECLARED_DURATION',
                                     'STOPPED_AT_DECLARED_CUT') else 'INDETERMINATE'),
            'numerical_verification': ('NOT_ASSESSED' if balance_passed else 'FAILED'),
            'declared_bounds_status': ('WITHIN' if all(limits.values()) else 'VIOLATED'),
            'declared_bounds_coverage': 'COMPLETE',
            'scientific_qualification': 'NOT_ASSESSED',
            'operating_readiness': 'NOT_ASSESSED',
            'predictions_computed': True, 'qualification_evidence_refs': [],
        },
    })
