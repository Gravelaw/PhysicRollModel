"""Public RunSpec adapter for the existing checked pass and schedule solvers.

Other W3 workflow kinds remain explicit future adapters. No empirical
qualification or mill feasibility is inferred from a completed replay.
"""

from dataclasses import fields, replace
import hashlib
from importlib.resources import files

from .checked_schedule import CheckedPass, InterpassHandoff, run_checked_schedule
from .conditional_shao import (DECLARED_PRIOR_LOG_STRAINS, SUPPORTED_ASSUMPTIONS,
                               SUPPORTED_CONTRACT, run_conditional_comparison,
                               run_declared_prior_sensitivity)
from .contact import CircularRollElasticity
from .energy_handoff import HeatCapacityCurve, PassHeatBoundary, PassiveContactBoundary
from .lubrication import FluidObservation
from .materials import MaterialState, PowerHardeningLaw
from .model import Scenario
from .operating import EquipmentLimits, ObservedSignal, PassOperatingPlan, SignalRange
from .operational_replay import (CONTRACT_VERSION, AppliedReference, MeasuredSignal,
                                 OperationSample, OperatingRecipe, PassScope,
                                 PhaseTarget, SteadyWindowEvidence,
                                 replay_operating_samples)
from .resources import resource_file
from .run_contract import ResultBundle, RunSpec
from .schedule_search import OperatingChoice, SearchSpace, search_schedules
from .transient_workflow import run_t1_spec
from .transient_t2_workflow import run_t2_spec
from .transient_t2_two_reel_workflow import run_two_reel_spec


EQUIPMENT_LIMITS = {
    'separating_force_n': 'max_separating_force_n',
    'torque_per_work_roll_nm': 'max_torque_per_work_roll_nm',
    'roll_mechanical_power_w': 'max_roll_mechanical_power_w',
    'roll_surface_speed_m_s': 'max_roll_surface_speed_m_s',
    'entry_tension_force_n': 'max_entry_reel_tension_n',
    'exit_tension_force_n': 'max_exit_reel_tension_n',
}

CONDITIONAL_SOURCE_RESOURCES = {
    'physicroll/conditional_shao.py': ('module', 'conditional_shao.py'),
    'docs/research/data/shao2015_raw.json': ('shao_research', 'shao2015_raw.json'),
    'scenarios/literature/shao2015_aa5052/inputs.csv': ('shao_fixture', 'inputs.csv'),
    'scenarios/literature/shao2015_aa5052/measured_validation.csv':
        ('shao_fixture', 'measured_validation.csv'),
    'scenarios/literature/shao2015_aa5052/reference_model_outputs.csv':
        ('shao_fixture', 'reference_model_outputs.csv'),
    'scenarios/literature/shao2015_aa5052/sources.json': ('shao_fixture', 'sources.json'),
}
CONDITIONAL_CARD_RESOURCES = {
    'docs/research/data/shao2015_conditional_adapter.json':
        ('shao_research', 'shao2015_conditional_adapter.json'),
    'docs/research/data/shao2015_prior_sensitivity.json':
        ('shao_research', 'shao2015_prior_sensitivity.json'),
    'scenarios/literature/shao2015_aa5052/assumptions.json':
        ('shao_fixture', 'assumptions.json'),
}
CONDITIONAL_ADAPTER_ID = 'shao2015_fixed_rigid_slab_prior_log_005'
OPERATING_SOURCE_RESOURCES = {
    'physicroll/operational_replay.py': 'operational_replay.py',
    'physicroll/operating.py': 'operating.py',
}
SEARCH_SOURCE_RESOURCES = {
    'physicroll/schedule_search.py': 'schedule_search.py',
    'physicroll/checked_schedule.py': 'checked_schedule.py',
}


def _record(cls, value, **converted):
    if type(value) is not dict:
        raise ValueError(f'{cls.__name__} must be an object')
    unknown = set(value) - {field.name for field in fields(cls)}
    if unknown:
        raise ValueError(f'{cls.__name__} has unknown fields: {sorted(unknown)}')
    try:
        return cls(**{**value, **converted})
    except (TypeError, ValueError) as exc:
        raise ValueError(f'invalid {cls.__name__}: {exc}') from exc


def _optional(cls, value):
    return None if value is None else _record(cls, value)


def _array(value, label):
    if type(value) is not list:
        raise ValueError(f'{label} must be an array')
    return tuple(value)


def _checked_pass(value):
    if type(value) is not dict:
        raise ValueError('checked_pass must be an object')
    try:
        scenario = Scenario.from_dict(value['scenario'])
        plan_data = value['operating_plan']
        if type(plan_data) is not dict:
            raise ValueError('operating_plan must be an object')
        plan = _record(
            PassOperatingPlan, plan_data,
            ranges=tuple(_record(SignalRange, item)
                         for item in _array(plan_data['ranges'], 'ranges')),
            observations=tuple(_record(ObservedSignal, item)
                               for item in _array(plan_data['observations'],
                                                  'observations')),
        )
        return _record(
            CheckedPass, value, scenario=scenario, operating_plan=plan,
            assumed_strain_range=_array(value['assumed_strain_range'],
                                        'assumed_strain_range'),
            assumed_temperature_range_k=_array(value['assumed_temperature_range_k'],
                                               'assumed_temperature_range_k'),
            elasticity=_optional(CircularRollElasticity, value.get('elasticity')),
            heat_boundary=_optional(PassHeatBoundary, value.get('heat_boundary')),
            passive_contact=_optional(PassiveContactBoundary, value.get('passive_contact')),
            fluid_observation=_optional(FluidObservation, value.get('fluid_observation')),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f'invalid checked_pass: {exc}') from exc


def _heat_capacity(value):
    if value is None:
        return None
    if type(value) is not dict:
        raise ValueError('heat capacity must be an object')
    try:
        return _record(HeatCapacityCurve, value,
                       temperature_k=_array(value['temperature_k'], 'temperature_k'),
                       heat_capacity_j_kg_k=_array(value['heat_capacity_j_kg_k'],
                                                   'heat_capacity_j_kg_k'))
    except (KeyError, TypeError) as exc:
        raise ValueError(f'invalid heat capacity: {exc}') from exc


def _bounds_evidence(passes):
    required, evaluations = [], []

    def add(identifier, status):
        required.append(identifier)
        if status.startswith(('WITHIN_', 'OUTSIDE_')):
            evaluations.append({'limit_id': identifier,
                                'status': 'VIOLATED' if status.startswith('OUTSIDE_')
                                else 'WITHIN'})

    for item in passes:
        prefix = f"pass:{item['pass_number']}"
        operating = item['operating']
        # Missing machine capacities remain required but unevaluated. One
        # caller-declared range cannot silently make the entire pass WITHIN.
        for limit_name in EQUIPMENT_LIMITS.values():
            required.append(f'{prefix}:equipment:{limit_name}')
        for quantity in operating['coverage']['steady_input_output_ranges_not_supplied']:
            required.append(f'{prefix}:range:steady:{quantity}')
        for check in operating['range_checks']:
            bound = check['range']
            add(f"{prefix}:range:{bound['phase']}:{bound['quantity']}", check['status'])
        for check in operating['equipment_checks']:
            if check['status'].startswith(('WITHIN_', 'OUTSIDE_')):
                evaluations.append({
                    'limit_id': f"{prefix}:equipment:{EQUIPMENT_LIMITS[check['quantity']]}",
                    'status': 'VIOLATED' if check['status'].startswith('OUTSIDE_')
                    else 'WITHIN',
                })
        for check in operating['observation_range_checks']:
            observation = check['observation']
            if check['status'] != 'NO_DECLARED_RANGE':
                add(f"{prefix}:observation:{observation['phase']}:"
                    f"{observation['quantity']}", check['status'])
    return {'required_limit_ids': required, 'evaluations': evaluations}


def run_checked_spec(spec: RunSpec) -> ResultBundle:
    """Execute a checked pass/chain RunSpec and retain separate status axes."""
    if not isinstance(spec, RunSpec):
        raise ValueError('run_checked_spec requires a RunSpec')
    data = spec.to_dict()
    kind = data['workflow_kind']
    if kind not in ('checked_pass', 'checked_schedule'):
        raise ValueError(f'{kind} is not a checked-pass workflow')
    resolved = data['resolved_inputs']
    expected = {'checked_pass' if kind == 'checked_pass' else 'checked_passes',
                'initial_state', 'law', 'interpass_handoffs', 'gauge_basis', 'layer_count'}
    optional = {'strip_cp', 'roll_cp', 'equipment_limits'}
    if set(resolved) - (expected | optional) or expected - set(resolved):
        raise ValueError('resolved checked inputs have missing or unknown fields')
    try:
        pass_data = ([resolved['checked_pass']] if kind == 'checked_pass'
                     else resolved['checked_passes'])
        if type(pass_data) is not list:
            raise ValueError('checked_passes must be an array')
        if type(resolved['interpass_handoffs']) is not list:
            raise ValueError('interpass_handoffs must be an array')
        passes = tuple(_checked_pass(item) for item in pass_data)
        state_data = resolved['initial_state']
        if type(state_data['history']) is not list:
            raise ValueError('material history must be an array')
        state = _record(MaterialState, state_data,
                        history=tuple(state_data['history']))
        law = _record(PowerHardeningLaw, resolved['law'])
        handoffs = tuple(_record(InterpassHandoff, item)
                         for item in resolved['interpass_handoffs'])
    except (KeyError, TypeError) as exc:
        raise ValueError(f'invalid resolved checked inputs: {exc}') from exc
    choices = data['model_choices']
    thermal = 'prescribed_energy' if any(p.heat_boundary is not None for p in passes) else 'none'
    if (choices['material'] != 'power_hardening' or choices['thermal'] != thermal or
            any(p.solver != choices['solver'] or p.bite_mode != choices['bite']
                for p in passes)):
        raise ValueError('model_choices disagree with resolved checked inputs')
    settings = data['numerical_settings']
    if (settings.get('verify_refinement') is not True or
            set(settings) != {'cells', 'verify_refinement'} or
            type(settings['cells']) is not int or
            any(p.cells != settings['cells'] for p in passes)):
        raise ValueError('numerical_settings disagree with checked pass cells/refinement')
    result = run_checked_schedule(
        passes, state, law, gauge_basis=resolved['gauge_basis'],
        layer_count=resolved['layer_count'], interpass_handoffs=handoffs,
        strip_cp=_heat_capacity(resolved.get('strip_cp')),
        roll_cp=_heat_capacity(resolved.get('roll_cp')),
        equipment_limits=_optional(EquipmentLimits, resolved.get('equipment_limits')),
    )
    bounds = _bounds_evidence(result['passes'])
    evaluated = bounds['evaluations']
    coverage = ('NONE' if not evaluated else 'COMPLETE'
                if len(evaluated) == len(bounds['required_limit_ids']) else 'PARTIAL')
    status = ('VIOLATED' if any(item['status'] == 'VIOLATED' for item in evaluated)
              else 'WITHIN' if coverage == 'COMPLETE' else 'INDETERMINATE')
    return ResultBundle({
        'schema_version': '1', 'run_spec_sha256': spec.sha256,
        'effective_inputs': {'scenarios': [item['effective_scenario']
                                           for item in result['passes']],
                             'final_state': result['final_state']},
        'outputs': {'checked_schedule': result},
        'checks': {'declared_bounds': bounds,
                   'gauge_audit': result['gauge_audit'],
                   'declared_bound_violations': result['declared_bound_violations']},
        'assessments': {
            'execution': 'COMPLETED', 'input_validity': 'VALID',
            'model_applicability': 'IN_DOMAIN', 'numerical_verification': 'PASSED',
            'declared_bounds_status': status, 'declared_bounds_coverage': coverage,
            'scientific_qualification': 'NOT_ASSESSED',
            'operating_readiness': 'NOT_ASSESSED', 'predictions_computed': True,
            'qualification_evidence_refs': [],
        },
    })


def _verify_conditional_resources(data):
    for field, expected in (('source_hashes', CONDITIONAL_SOURCE_RESOURCES),
                            ('card_hashes', CONDITIONAL_CARD_RESOURCES)):
        declared = data[field]
        if set(declared) != set(expected):
            raise ValueError(f'{field} must identify every conditional source')
        for name, (category, resource_name) in expected.items():
            resource = (files('physicroll').joinpath(resource_name)
                        if category == 'module' else resource_file(category, resource_name))
            if hashlib.sha256(resource.read_bytes()).hexdigest() != declared[name]:
                raise ValueError(f'conditional resource hash mismatch: {name}')


def _same_frozen_json(actual, expected):
    """Compare frozen declarations without treating JSON booleans as numbers."""
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return (actual.keys() == expected.keys() and
                all(_same_frozen_json(actual[key], value)
                    for key, value in expected.items()))
    if type(expected) is list:
        return (len(actual) == len(expected) and
                all(_same_frozen_json(item, value)
                    for item, value in zip(actual, expected)))
    return actual == expected


def run_conditional_spec(spec: RunSpec) -> ResultBundle:
    """Run the frozen no-fit Shao benchmark or declared prior sensitivity."""
    if not isinstance(spec, RunSpec):
        raise ValueError('run_conditional_spec requires a RunSpec')
    data = spec.to_dict()
    kind = data['workflow_kind']
    if kind not in ('benchmark', 'sensitivity'):
        raise ValueError(f'{kind} is not a conditional Shao workflow')
    if data['model_choices'] != {
            'solver': SUPPORTED_CONTRACT['solver'], 'material': 'power_hardening',
            'bite': SUPPORTED_CONTRACT['bite_mode'], 'thermal': 'none'}:
        raise ValueError('conditional model choices differ from frozen adapter')
    settings = {'cells': 256, 'verify_refinement': True}
    if kind == 'benchmark':
        settings['comparison_cells'] = 512
    if not _same_frozen_json(data['numerical_settings'], settings):
        raise ValueError('conditional numerical settings differ from frozen adapter')
    expected_inputs = {'adapter_id': CONDITIONAL_ADAPTER_ID}
    if kind == 'benchmark':
        expected_inputs['prior_log_thickness_strain'] = (
            SUPPORTED_ASSUMPTIONS['prior_log_thickness_strain'])
    else:
        expected_inputs['prior_log_thickness_strains'] = list(DECLARED_PRIOR_LOG_STRAINS)
    if not _same_frozen_json(data['resolved_inputs'], expected_inputs):
        raise ValueError('conditional resolved inputs differ from frozen adapter')
    if (not _same_frozen_json(
            data['requested_inputs'], {**expected_inputs, 'fit_performed': False}) or
            data['recipe_targets'] != {} or
            data['observations'] != {
                'source_resource':
                    'scenarios/literature/shao2015_aa5052/measured_validation.csv',
                'measurement_uncertainty': None} or
            data['identities']['model_version'] != 'conditional_shao_contract_v1' or
            any(data['identities'][name] is not None
                for name in ('material_id', 'state_id', 'recipe_id'))):
        raise ValueError('conditional request, observations or identities differ from frozen adapter')
    _verify_conditional_resources(data)
    bounds = {
        'required_limit_ids': [f'pass:{number}:equipment:{limit}'
                               for number in (1, 2, 3)
                               for limit in EQUIPMENT_LIMITS.values()],
        'evaluations': [],
    }
    if kind == 'benchmark':
        output = run_conditional_comparison()
        differences = output['numerical_differences']
        numerical_passed = all(
            abs(item['force_relative_change']) < 1e-5 and
            abs(item['slip_absolute_change']) < 1e-6 for item in differences)
        if output['fixture_differences']:
            raise ValueError('conditional source fixture differs from audited extraction')
        outputs = {'conditional_comparison': output}
        checks = {'numerical_differences': differences,
                  'fixture_differences': output['fixture_differences']}
        effective = {'gauges_m': output['search']['selected']['gauges_m'],
                     'prior_log_thickness_strain': expected_inputs['prior_log_thickness_strain']}
    else:
        output = run_declared_prior_sensitivity()
        outputs = {'declared_prior_sensitivity': output}
        checks = {'case_statuses': [item['status'] for item in output['cases']]}
        effective = {'prior_log_thickness_strains': expected_inputs['prior_log_thickness_strains']}
        numerical_passed = None
    checks['declared_bounds'] = bounds
    return ResultBundle({
        'schema_version': '1', 'run_spec_sha256': spec.sha256,
        'effective_inputs': effective, 'outputs': outputs, 'checks': checks,
        'assessments': {
            'execution': 'COMPLETED', 'input_validity': 'VALID',
            'model_applicability': 'INDETERMINATE',
            'numerical_verification': ('NOT_ASSESSED' if numerical_passed is None
                                       else 'PASSED' if numerical_passed else 'FAILED'),
            'declared_bounds_status': 'INDETERMINATE',
            'declared_bounds_coverage': 'NONE',
            'scientific_qualification': 'NOT_ASSESSED',
            'operating_readiness': 'NOT_ASSESSED', 'predictions_computed': True,
            'qualification_evidence_refs': [],
        },
    })


def _operating_recipe(value):
    if type(value) is not dict:
        raise ValueError('operating recipe must be an object')
    try:
        return _record(OperatingRecipe, value,
                       scope=_record(PassScope, value['scope']),
                       targets=tuple(_record(PhaseTarget, item)
                                     for item in _array(value['targets'], 'recipe targets')))
    except KeyError as exc:
        raise ValueError(f'operating recipe missing {exc}') from exc


def _operation_sample(value):
    if type(value) is not dict:
        raise ValueError('operation sample must be an object')
    try:
        return _record(
            OperationSample, value,
            scope=_record(PassScope, value['scope']),
            measurements=tuple(_record(MeasuredSignal, item)
                               for item in _array(value['measurements'], 'measurements')),
            applied_references=tuple(_record(AppliedReference, item)
                                     for item in _array(value['applied_references'],
                                                        'applied references')),
            steady_evidence=tuple(_record(SteadyWindowEvidence, item)
                                  for item in _array(value['steady_evidence'],
                                                     'steady evidence')),
        )
    except KeyError as exc:
        raise ValueError(f'operation sample missing {exc}') from exc


def run_operating_replay_spec(spec: RunSpec) -> ResultBundle:
    """Replay supplied O0 phase observations; compute no process prediction."""
    if not isinstance(spec, RunSpec):
        raise ValueError('run_operating_replay_spec requires a RunSpec')
    data = spec.to_dict()
    if data['workflow_kind'] != 'operating_replay':
        raise ValueError('RunSpec is not an operating replay')
    if data['model_choices'] != dict.fromkeys(('solver', 'material', 'bite', 'thermal'), 'none'):
        raise ValueError('O0 model choices must declare no solver')
    if (data['numerical_settings'] != {} or data['card_hashes'] != {} or
            data['identities']['model_version'] != CONTRACT_VERSION or
            any(data['identities'][key] is not None
                for key in ('material_id', 'state_id'))):
        raise ValueError('O0 has no numerical solver or material state')
    requested = data['requested_inputs']
    if (set(requested) != {'replay_id'} or
            type(requested['replay_id']) is not str or
            not requested['replay_id'].strip() or
            not _same_frozen_json(data['resolved_inputs'], requested)):
        raise ValueError('O0 replay identity differs between requested and resolved inputs')
    if set(data['source_hashes']) != set(OPERATING_SOURCE_RESOURCES):
        raise ValueError('O0 source hashes must name both operating modules')
    for name, resource_name in OPERATING_SOURCE_RESOURCES.items():
        digest = hashlib.sha256(files('physicroll').joinpath(resource_name).read_bytes()).hexdigest()
        if data['source_hashes'][name] != digest:
            raise ValueError(f'O0 source hash mismatch: {name}')
    if (set(data['recipe_targets']) != {'recipes'} or
            set(data['observations']) != {'samples'}):
        raise ValueError('O0 recipes and samples must remain separate')
    recipes = tuple(_operating_recipe(item) for item in
                    _array(data['recipe_targets']['recipes'], 'recipes'))
    samples = tuple(_operation_sample(item) for item in
                    _array(data['observations']['samples'], 'samples'))
    replay = replay_operating_samples(recipes, samples)
    recipe_ids = {recipe.recipe_id for recipe in recipes}
    identity = next(iter(recipe_ids)) if len(recipe_ids) == 1 else None
    if data['identities']['recipe_id'] != identity:
        raise ValueError('O0 recipe identity disagrees with supplied revisions')
    return ResultBundle({
        'schema_version': '1', 'run_spec_sha256': spec.sha256,
        'effective_inputs': {'replay_id': requested['replay_id'],
                             'coil_id': samples[0].coil_id,
                             'timebase_id': samples[0].timebase_id},
        'outputs': {'operating_replay': replay},
        'checks': {'declared_bounds': {'required_limit_ids': [], 'evaluations': []}},
        'assessments': {
            'execution': 'COMPLETED', 'input_validity': 'VALID',
            'model_applicability': 'NOT_ASSESSED',
            'numerical_verification': 'NOT_ASSESSED',
            'declared_bounds_status': 'INDETERMINATE',
            'declared_bounds_coverage': 'NONE',
            'scientific_qualification': 'NOT_ASSESSED',
            'operating_readiness': 'NOT_ASSESSED',
            'predictions_computed': False,
            'qualification_evidence_refs': [],
        },
    })


def run_schedule_search_spec(spec: RunSpec) -> ResultBundle:
    """Search a finite supplied grid with complete, reproducible checked routes."""
    if not isinstance(spec, RunSpec):
        raise ValueError('run_schedule_search_spec requires a RunSpec')
    data = spec.to_dict()
    if data['workflow_kind'] != 'schedule_search':
        raise ValueError('RunSpec is not a schedule search')
    resolved = data['resolved_inputs']
    expected = {'search_space', 'base_pass', 'initial_state', 'law',
                'handoff_template', 'equipment_limits'}
    if set(resolved) != expected or set(data['requested_inputs']) != {'search_space'}:
        raise ValueError('search inputs have missing or unknown fields')
    if not _same_frozen_json(data['requested_inputs']['search_space'],
                             resolved['search_space']):
        raise ValueError('requested and resolved search spaces differ')
    if data['recipe_targets'] != {} or data['observations'] != {}:
        raise ValueError('search observations or phase recipes are unsupported')
    if set(data['source_hashes']) != set(SEARCH_SOURCE_RESOURCES):
        raise ValueError('search source hashes must name search and checked modules')
    for name, resource_name in SEARCH_SOURCE_RESOURCES.items():
        digest = hashlib.sha256(files('physicroll').joinpath(resource_name).read_bytes()).hexdigest()
        if data['source_hashes'][name] != digest:
            raise ValueError(f'search source hash mismatch: {name}')
    raw_space = resolved['search_space']
    if type(raw_space) is not dict:
        raise ValueError('search_space must be an object')
    try:
        space = _record(
            SearchSpace, raw_space,
            gauges_m=_array(raw_space['gauges_m'], 'search gauges'),
            mandatory_checkpoints_m=_array(raw_space['mandatory_checkpoints_m'],
                                           'mandatory checkpoints'),
            choices_by_pass=tuple(
                tuple(_record(OperatingChoice, choice)
                      for choice in _array(row, 'pass choices'))
                for row in _array(raw_space['choices_by_pass'], 'choices_by_pass')),
        )
        state_data = resolved['initial_state']
        state = _record(MaterialState, state_data,
                        history=_array(state_data['history'], 'material history'))
        law = _record(PowerHardeningLaw, resolved['law'])
        base = _checked_pass(resolved['base_pass'])
        handoff = _record(InterpassHandoff, resolved['handoff_template'])
        limits = _optional(EquipmentLimits, resolved['equipment_limits'])
    except (KeyError, TypeError) as exc:
        raise ValueError(f'invalid resolved search inputs: {exc}') from exc
    space.validate()
    base.validate_contract()
    state.validate()
    law.validate()
    if (state.alloy, state.temper) != (law.alloy, law.temper):
        raise ValueError('search initial state and law material identity differs')
    if limits is not None:
        limits.validate()
    handoff.validate(max(2, space.max_passes))
    if handoff.after_pass != 1:
        raise ValueError('search handoff template must follow pass 1')
    if (base.heat_boundary is not None or base.passive_contact is not None or
            base.fluid_observation is not None or base.roll_body_id is not None or
            base.operating_plan.ranges or base.operating_plan.observations):
        raise ValueError('search base pass must be isothermal and have no phase observations')
    # The base scenario supplies invariant geometry and a valid pass-shaped
    # template. A complete route may exceed the inherited *single-pass*
    # reduction guard; each generated pass is screened on its own gauges.
    if (data['model_choices'] != {'solver': base.solver, 'material': 'power_hardening',
                                 'bite': base.bite_mode, 'thermal': 'none'} or
            not _same_frozen_json(data['numerical_settings'],
                                  {'cells': base.cells, 'verify_refinement': True})):
        raise ValueError('search model choices or numerical settings disagree with base pass')
    if (handoff.strip_mode != 'prescribed' or handoff.roll_mode != 'not_modeled' or
            handoff.width_change_provenance is not None):
        raise ValueError('search requires explicit prescribed strip temperature handoff')

    def build_and_replay(gauges, choices):
        passes = []
        for index, choice in enumerate(choices, 1):
            name = f'search_pass_{index}'
            scenario = replace(
                base.scenario, name=name,
                entry_thickness_m=gauges[index-1], exit_thickness_m=gauges[index],
                entry_speed_m_s=choice.entry_speed_m_s,
                entry_tension_pa=choice.entry_tension_pa,
                exit_tension_pa=choice.exit_tension_pa,
            )
            passes.append(replace(base, scenario=scenario,
                                  operating_plan=replace(base.operating_plan, pass_name=name)))
        handoffs = tuple(replace(handoff, after_pass=index)
                         for index in range(1, len(passes)))
        return run_checked_schedule(tuple(passes), state, law,
                                    gauge_basis='per_layer_full_thickness', layer_count=1,
                                    interpass_handoffs=handoffs, equipment_limits=limits)

    search = search_schedules(space, build_and_replay)
    selected = search['selected']
    computed_count = sum(item['status'] in ('INDETERMINATE', 'VIOLATED')
                         for item in search['candidates'])
    violated_count = sum(item['status'] == 'VIOLATED'
                         for item in search['candidates'])
    bounds = (_bounds_evidence(selected['checked_replay']['passes']) if selected else
              {'required_limit_ids': [], 'evaluations': []})
    evaluated = bounds['evaluations']
    coverage = ('NONE' if not evaluated else 'COMPLETE'
                if len(evaluated) == len(bounds['required_limit_ids']) else 'PARTIAL')
    status = ('VIOLATED' if any(item['status'] == 'VIOLATED' for item in evaluated)
              else 'WITHIN' if coverage == 'COMPLETE' else 'INDETERMINATE')
    return ResultBundle({
        'schema_version': '1', 'run_spec_sha256': spec.sha256,
        'effective_inputs': {
            'selected_gauges_m': list(selected['gauges_m']) if selected else None,
            'final_state': selected['checked_replay']['final_state'] if selected else None,
        },
        'outputs': {'schedule_search': search},
        'checks': {'declared_bounds': bounds,
                   'assessment_scope': 'selected_route',
                   'candidate_computation_count': computed_count,
                   'candidate_violation_count': violated_count,
                   'independent_selected_replay': selected is not None},
        'assessments': {
            'execution': 'COMPLETED', 'input_validity': 'VALID',
            'model_applicability': 'IN_DOMAIN' if selected else 'NOT_ASSESSED',
            'numerical_verification': 'PASSED' if selected else 'NOT_ASSESSED',
            'declared_bounds_status': status,
            'declared_bounds_coverage': coverage,
            'scientific_qualification': 'NOT_ASSESSED',
            'operating_readiness': 'NOT_ASSESSED',
            'predictions_computed': computed_count > 0,
            'qualification_evidence_refs': [],
        },
    })


def run_workflow(spec: RunSpec) -> ResultBundle:
    """Dispatch public checked, conditional and offline operating workflows."""
    if not isinstance(spec, RunSpec):
        raise ValueError('run_workflow requires a RunSpec')
    kind = spec.to_dict()['workflow_kind']
    if kind in ('checked_pass', 'checked_schedule'):
        return run_checked_spec(spec)
    if kind in ('benchmark', 'sensitivity'):
        return run_conditional_spec(spec)
    if kind == 'operating_replay':
        return run_operating_replay_spec(spec)
    if kind == 'schedule_search':
        return run_schedule_search_spec(spec)
    if kind == 'prescribed_transport_t1':
        return run_t1_spec(spec)
    if kind == 'torque_driven_span_reel_t2':
        return run_t2_spec(spec)
    if kind == 'two_reel_span_t2':
        return run_two_reel_spec(spec)
    raise ValueError(f'no public adapter for workflow_kind {kind}')
