"""Per-pass signal roles and declared operating envelopes; no control algorithm."""
from dataclasses import asdict, dataclass
import math


# Quantities are deliberately narrow: each maps to a specific existing input/output.
QUANTITIES = {
    'exit_thickness_m': ('m', 'setpoint'),
    'entry_speed_m_s': ('m/s', 'setpoint'),
    'entry_tension_pa': ('Pa', 'setpoint'),
    'exit_tension_pa': ('Pa', 'setpoint'),
    'reduction_fraction': ('1', 'setpoint'),
    'separating_force_n': ('N', 'prediction'),
    'torque_per_work_roll_nm': ('N m', 'prediction'),
    'roll_mechanical_power_w': ('W', 'prediction'),
    'assumed_forward_slip_fraction': ('1', 'prediction'),
    'exit_temperature_k': ('K', 'unsupported_prediction'),
    'coolant_flow_kg_s': ('kg/s', 'boundary'),
    'lubricant_flow_kg_s': ('kg/s', 'boundary'),
}
PHASES = frozenset(('threading', 'steady', 'deceleration', 'tailout'))


def _number(value):
    return not isinstance(value, bool) and isinstance(value, (float, int)) and math.isfinite(value)


@dataclass(frozen=True)
class SignalRange:
    quantity: str
    unit: str
    minimum: float
    maximum: float
    phase: str
    provenance: str

    def validate(self):
        if self.quantity not in QUANTITIES or self.unit != QUANTITIES[self.quantity][0]:
            raise ValueError('unknown quantity or incorrect SI unit in signal range')
        if self.phase not in PHASES or not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError('signal range needs a known phase and provenance')
        if not _number(self.minimum) or not _number(self.maximum) or self.minimum > self.maximum:
            raise ValueError('signal range bounds must be finite and ordered')
        if self.minimum < 0 or (self.quantity == 'exit_temperature_k' and self.minimum <= 0):
            raise ValueError('signal range is outside its nonnegative domain')
        if self.quantity == 'reduction_fraction' and self.maximum > 1:
            raise ValueError('reduction fraction cannot exceed one')


@dataclass(frozen=True)
class ObservedSignal:
    quantity: str
    unit: str
    value: float
    phase: str
    provenance: str

    def validate(self):
        if self.quantity not in QUANTITIES or self.unit != QUANTITIES[self.quantity][0]:
            raise ValueError('unknown observed quantity or incorrect SI unit')
        if self.phase not in PHASES or not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError('observed signal needs a known phase and provenance')
        if not _number(self.value) or self.value < 0 or (self.quantity == 'exit_temperature_k' and self.value <= 0):
            raise ValueError('observed signal must be finite and in its physical domain')
        if self.quantity == 'reduction_fraction' and self.value > 1:
            raise ValueError('observed reduction fraction cannot exceed one')


@dataclass(frozen=True)
class PassOperatingPlan:
    """Inputs and envelopes belonging to exactly one pass; never inherited."""
    pass_name: str
    ranges: tuple[SignalRange, ...] = ()
    observations: tuple[ObservedSignal, ...] = ()
    cooling_boundary: str | None = None
    lubrication_boundary: str | None = None
    coolant_flow_kg_s: float | None = None
    lubricant_flow_kg_s: float | None = None
    boundary_provenance: str | None = None

    def validate(self):
        if not isinstance(self.pass_name, str) or not self.pass_name.strip():
            raise ValueError('operating plan pass_name is required')
        if not isinstance(self.ranges, tuple) or not all(isinstance(x, SignalRange) for x in self.ranges):
            raise ValueError('pass ranges must be a tuple of SignalRange')
        if not isinstance(self.observations, tuple) or not all(isinstance(x, ObservedSignal) for x in self.observations):
            raise ValueError('pass observations must be a tuple of ObservedSignal')
        seen = set()
        for item in self.ranges:
            item.validate()
            key = item.phase, item.quantity
            if key in seen:
                raise ValueError('duplicate pass/phase quantity range')
            seen.add(key)
        seen.clear()
        for item in self.observations:
            item.validate()
            key = item.phase, item.quantity
            if key in seen:
                raise ValueError('duplicate pass/phase observation')
            seen.add(key)
        boundaries = (self.cooling_boundary, self.lubrication_boundary)
        if any(x is not None and (not isinstance(x, str) or not x.strip()) for x in boundaries):
            raise ValueError('boundary descriptions must be nonempty strings when supplied')
        flows = (self.coolant_flow_kg_s, self.lubricant_flow_kg_s)
        if any(x is not None and (not _number(x) or x < 0) for x in flows):
            raise ValueError('declared boundary flows must be finite nonnegative kg/s')
        if any(x is not None for x in boundaries + flows) and (
                not isinstance(self.boundary_provenance, str) or not self.boundary_provenance.strip()):
            raise ValueError('declared cooling/lubrication boundaries need provenance')


@dataclass(frozen=True)
class EquipmentLimits:
    """Optional fixed stand limits; absent numbers are unknown, not unlimited."""
    provenance: str
    max_separating_force_n: float | None = None
    max_torque_per_work_roll_nm: float | None = None
    max_roll_mechanical_power_w: float | None = None
    max_roll_surface_speed_m_s: float | None = None
    max_entry_reel_tension_n: float | None = None
    max_exit_reel_tension_n: float | None = None

    def validate(self):
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError('equipment limit provenance required')
        for field in ('max_separating_force_n', 'max_torque_per_work_roll_nm',
                      'max_roll_mechanical_power_w', 'max_roll_surface_speed_m_s',
                      'max_entry_reel_tension_n', 'max_exit_reel_tension_n'):
            value = getattr(self, field)
            if value is not None and (not _number(value) or value <= 0):
                raise ValueError(f'{field} must be a positive finite limit')


def assess_pass_operating_plan(plan: PassOperatingPlan, scenario, mechanics: dict,
                               equipment: EquipmentLimits | None = None) -> dict:
    plan.validate()
    if equipment is not None:
        equipment.validate()
    inputs = {'exit_thickness_m': scenario.exit_thickness_m,
              'entry_speed_m_s': scenario.entry_speed_m_s,
              'entry_tension_pa': scenario.entry_tension_pa,
              'exit_tension_pa': scenario.exit_tension_pa,
              'reduction_fraction': 1 - scenario.exit_thickness_m / scenario.entry_thickness_m}
    predictions = mechanics['baseline_mechanics']
    boundaries = {'coolant_flow_kg_s': plan.coolant_flow_kg_s,
                  'lubricant_flow_kg_s': plan.lubricant_flow_kg_s}
    checks = []
    for bound in plan.ranges:
        role = QUANTITIES[bound.quantity][1]
        value = (inputs if role == 'setpoint' else predictions if role == 'prediction' else
                 boundaries if role == 'boundary' else {}).get(bound.quantity)
        status = ('NOT_EVALUATED_NO_MODEL' if role == 'unsupported_prediction' else
                  'NOT_EVALUATED_PHASE' if bound.phase != 'steady' else
                  'NOT_EVALUATED_MISSING_BOUNDARY_INPUT' if role == 'boundary' and value is None else
                  'WITHIN_DECLARED_RANGE' if bound.minimum <= value <= bound.maximum else
                  'OUTSIDE_DECLARED_RANGE')
        checks.append({'range': asdict(bound), 'role': role,
                       'evaluated_value': value if bound.phase == 'steady' and role != 'unsupported_prediction' else None,
                       'status': status})
    fixed = []
    if equipment is not None:
        for limit_name, output_name in (
                ('max_separating_force_n', 'separating_force_n'),
                ('max_torque_per_work_roll_nm', 'torque_per_work_roll_nm'),
                ('max_roll_mechanical_power_w', 'roll_mechanical_power_w'),
                ('max_roll_surface_speed_m_s', 'roll_surface_speed_m_s'),
                ('max_entry_reel_tension_n', 'entry_tension_force_n'),
                ('max_exit_reel_tension_n', 'exit_tension_force_n')):
            limit = getattr(equipment, limit_name)
            if limit is not None:
                fixed.append({'quantity': output_name, 'predicted_value': predictions[output_name],
                              'limit': limit, 'status': 'WITHIN_DECLARED_LIMIT' if predictions[output_name] <= limit
                              else 'OUTSIDE_DECLARED_LIMIT'})
    range_lookup = {(item.phase, item.quantity): item for item in plan.ranges}
    observed_checks = []
    for item in plan.observations:
        bound = range_lookup.get((item.phase, item.quantity))
        observed_checks.append({'observation': asdict(item),
                                'status': ('NO_DECLARED_RANGE' if bound is None else
                                           'WITHIN_DECLARED_RANGE' if bound.minimum <= item.value <= bound.maximum
                                           else 'OUTSIDE_DECLARED_RANGE')})
    evaluated = [x for x in checks + fixed + observed_checks
                 if x['status'].startswith(('WITHIN', 'OUTSIDE'))]
    declared_steady = {item.quantity for item in plan.ranges if item.phase == 'steady'}
    expected = {key for key, (_, role) in QUANTITIES.items() if role in ('setpoint', 'prediction')}
    return {'pass_name': plan.pass_name, 'setpoints': inputs,
            'model_parameters': {'friction_coefficient': scenario.friction_coefficient,
                                 'work_roll_radius_m': scenario.work_roll_radius_m,
                                 'density_kg_m3': scenario.density_kg_m3,
                                 'drive_efficiency': scenario.drive_efficiency,
                                 'scenario_mean_flow_stress_pa_supplied_but_replaced': scenario.mean_flow_stress_pa,
                                 'hardening_mean_flow_stress_pa_used': mechanics['mean_flow_stress_pa'],
                                 'hardening_provenance': mechanics['hardening_provenance']},
            'predictions': {key: predictions[key] for key, (_, role) in QUANTITIES.items()
                                               if role == 'prediction'},
            'observations': [asdict(item) for item in plan.observations],
            'cooling_boundary': plan.cooling_boundary,
            'lubrication_boundary': plan.lubrication_boundary,
            'boundary_inputs': boundaries,
            'boundary_provenance': plan.boundary_provenance,
            'range_checks': checks, 'equipment_checks': fixed,
            'observation_range_checks': observed_checks,
            'coverage': {'evaluated_check_count': len(evaluated),
                         'unevaluated_range_count': sum(x['status'].startswith('NOT_EVALUATED') for x in checks),
                         'steady_input_output_ranges_not_supplied': sorted(expected - declared_steady)},
            'evaluated_checks_status': ('OUTSIDE_DECLARED_BOUNDS' if any(
                x['status'].startswith('OUTSIDE') for x in evaluated) else
                                        'UNASSESSED' if not evaluated else
                                        'PARTIAL_DECLARED_CHECKS_ONLY'),
            'limitations': ['Ranges are caller-declared, not inferred from earlier passes.',
                            'Observations and boundaries do not calibrate mechanics or predict cooling/lubrication.',
                            'Only steady-state quantities with model outputs are evaluated.']}
