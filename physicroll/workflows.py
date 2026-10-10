"""Public RunSpec adapter for the existing checked pass and schedule solvers.

Other W3 workflow kinds remain explicit future adapters. No empirical
qualification or mill feasibility is inferred from a completed replay.
"""

from dataclasses import fields

from .checked_schedule import CheckedPass, InterpassHandoff, run_checked_schedule
from .contact import CircularRollElasticity
from .energy_handoff import HeatCapacityCurve, PassHeatBoundary, PassiveContactBoundary
from .lubrication import FluidObservation
from .materials import MaterialState, PowerHardeningLaw
from .model import Scenario
from .operating import EquipmentLimits, ObservedSignal, PassOperatingPlan, SignalRange
from .run_contract import ResultBundle, RunSpec


EQUIPMENT_LIMITS = {
    'separating_force_n': 'max_separating_force_n',
    'torque_per_work_roll_nm': 'max_torque_per_work_roll_nm',
    'roll_mechanical_power_w': 'max_roll_mechanical_power_w',
    'roll_surface_speed_m_s': 'max_roll_surface_speed_m_s',
    'entry_tension_force_n': 'max_entry_reel_tension_n',
    'exit_tension_force_n': 'max_exit_reel_tension_n',
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
