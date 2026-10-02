"""Explicit checked-solver replay for single-layer prescribed rolling passes.

Only reviewed optional solvers are composed here. No foil, controller, anneal,
mill-stretch or interpass heat-transfer law is introduced.
"""
from dataclasses import asdict, dataclass, replace
import math

from .contact import CircularRollElasticity, solve_circular_contact
from .energy_handoff import (HeatCapacityCurve, PassHeatBoundary,
                             PassiveContactBoundary, handoff_pass)
from .lubrication import FluidObservation
from .materials import BiteHardening, MaterialState, PowerHardeningLaw
from .model import Scenario
from .operating import EquipmentLimits, PassOperatingPlan, assess_pass_operating_plan
from .schedule import GaugeSchedule, inspect_gauge_schedule
from .slab import solve_slab


@dataclass(frozen=True)
class CheckedPass:
    scenario: Scenario
    operating_plan: PassOperatingPlan
    solver: str  # spatial_slab or circular_contact
    cells: int
    bite_mode: str
    assumed_strain_range: tuple[float, float]
    assumed_temperature_range_k: tuple[float, float]
    elasticity: CircularRollElasticity | None = None
    heat_boundary: PassHeatBoundary | None = None
    passive_contact: PassiveContactBoundary | None = None
    fluid_observation: FluidObservation | None = None
    roll_body_id: str | None = None

    def validate_contract(self):
        if not isinstance(self.scenario, Scenario) or not isinstance(self.operating_plan, PassOperatingPlan):
            raise ValueError('checked pass needs a Scenario and matching operating plan')
        self.operating_plan.validate()
        if self.scenario.name != self.operating_plan.pass_name:
            raise ValueError('operating plan pass_name does not match scenario')
        if self.solver not in ('spatial_slab', 'circular_contact'):
            raise ValueError('select spatial_slab or circular_contact explicitly')
        if self.solver == 'circular_contact':
            if not isinstance(self.elasticity, CircularRollElasticity):
                raise ValueError('circular_contact requires explicit roll elasticity')
            self.elasticity.validate()
        elif self.elasticity is not None:
            raise ValueError('spatial_slab does not accept unused roll elasticity')
        if isinstance(self.cells, bool) or not isinstance(self.cells, int) or not 32 <= self.cells <= 8192:
            raise ValueError('checked pass cells must be integer in [32,8192]')
        if self.bite_mode not in ('unassisted', 'established'):
            raise ValueError('bite_mode must be unassisted or established')
        if self.heat_boundary is not None:
            if not isinstance(self.roll_body_id, str) or not self.roll_body_id.strip():
                raise ValueError('thermal pass requires explicit roll_body_id')
            if not isinstance(self.heat_boundary, PassHeatBoundary):
                raise ValueError('heat_boundary must be PassHeatBoundary')
            # A later pass may leave this unset for the explicit roll handoff.
            # The resolved boundary is fully validated by handoff_pass().
            if self.heat_boundary.roll_temperature_k is not None:
                self.heat_boundary.validate()
        elif self.roll_body_id is not None:
            raise ValueError('roll_body_id requires modeled roll thermal state')
        if self.passive_contact is not None:
            if self.heat_boundary is None or not isinstance(self.passive_contact, PassiveContactBoundary):
                raise ValueError('passive contact requires a heat boundary')
            self.passive_contact.validate()
        if self.fluid_observation is not None:
            if self.heat_boundary is None:
                raise ValueError('fluid observation requires thermal handoff; it is not a friction law')
            if not isinstance(self.fluid_observation, FluidObservation):
                raise ValueError('fluid observation must be FluidObservation')
            self.fluid_observation.validate()
        if (not isinstance(self.assumed_strain_range, tuple) or len(self.assumed_strain_range) != 2
                or not isinstance(self.assumed_temperature_range_k, tuple)
                or len(self.assumed_temperature_range_k) != 2):
            raise ValueError('assumed material envelopes must be two-value tuples')
        for value in self.assumed_strain_range + self.assumed_temperature_range_k:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('assumed material envelopes must be finite')


@dataclass(frozen=True)
class InterpassHandoff:
    """Explicit transition from pass i to i+1, without a time/anneal model."""
    after_pass: int
    strip_mode: str  # direct_predicted_carry or prescribed
    strip_temperature_k: float | None
    roll_mode: str  # direct_predicted_carry, prescribed, or not_modeled
    roll_temperature_k: float | None
    provenance: str
    width_change_provenance: str | None = None

    def validate(self, pass_count):
        if (isinstance(self.after_pass, bool) or not isinstance(self.after_pass, int)
                or not 1 <= self.after_pass < pass_count):
            raise ValueError('handoff must follow a nonfinal pass')
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError('interpass handoff needs provenance')
        if (self.width_change_provenance is not None
                and (not isinstance(self.width_change_provenance, str)
                     or not self.width_change_provenance.strip())):
            raise ValueError('width-change provenance must be nonempty when supplied')
        for mode, temperature, allowed in (
                (self.strip_mode, self.strip_temperature_k, ('direct_predicted_carry', 'prescribed')),
                (self.roll_mode, self.roll_temperature_k,
                 ('direct_predicted_carry', 'prescribed', 'not_modeled'))):
            if mode not in allowed:
                raise ValueError('invalid interpass temperature mode')
            if mode == 'prescribed':
                if (isinstance(temperature, bool) or not isinstance(temperature, (int, float))
                        or not math.isfinite(temperature) or temperature <= 0):
                    raise ValueError('prescribed interpass temperature must be positive finite K')
            elif temperature is not None:
                raise ValueError('only prescribed interpass mode accepts a temperature value')


def run_checked_schedule(passes: tuple[CheckedPass, ...], initial_state: MaterialState,
                         law: PowerHardeningLaw, *, gauge_basis: str, layer_count: int,
                         interpass_handoffs: tuple[InterpassHandoff, ...] = (),
                         strip_cp: HeatCapacityCurve | None = None,
                         roll_cp: HeatCapacityCurve | None = None,
                         equipment_limits: EquipmentLimits | None = None) -> dict:
    """Replay supplied passes; report declared bounds, never certify a mill route."""
    if not isinstance(passes, tuple) or not passes or not all(isinstance(p, CheckedPass) for p in passes):
        raise ValueError('passes must be a nonempty tuple of CheckedPass')
    if not isinstance(initial_state, MaterialState) or not isinstance(law, PowerHardeningLaw):
        raise ValueError('explicit initial material state and hardening law required')
    initial_state.validate()
    law.validate()
    if (initial_state.alloy, initial_state.temper) != (law.alloy, law.temper):
        raise ValueError('state/law material identity differs')
    if equipment_limits is not None:
        if not isinstance(equipment_limits, EquipmentLimits):
            raise ValueError('equipment_limits must be EquipmentLimits')
        equipment_limits.validate()
    thermal_enabled = any(p.heat_boundary is not None for p in passes)
    if thermal_enabled:
        if not isinstance(strip_cp, HeatCapacityCurve) or not isinstance(roll_cp, HeatCapacityCurve):
            raise ValueError('both strip and roll heat-capacity curves required for thermal passes')
        strip_cp.validate()
        roll_cp.validate()
    elif strip_cp is not None or roll_cp is not None:
        raise ValueError('heat-capacity curves need at least one thermal pass')
    names = set()
    for index, item in enumerate(passes, 1):
        try:
            item.validate_contract()
        except ValueError as exc:
            raise ValueError(f'pass {index}: {exc}') from exc
        if item.scenario.name in names:
            raise ValueError(f'pass {index}: duplicate pass name')
        names.add(item.scenario.name)
    gauges = (passes[0].scenario.entry_thickness_m,) + tuple(p.scenario.exit_thickness_m for p in passes)
    audit = inspect_gauge_schedule(GaugeSchedule(passes[0].scenario.name, gauges, gauges[-1],
                                                 gauge_basis, layer_count))
    for index, (previous, current) in enumerate(zip(passes, passes[1:]), 2):
        if previous.scenario.exit_thickness_m != current.scenario.entry_thickness_m:
            raise ValueError(f'pass {index}: entry gauge does not equal preceding exit gauge')
    for audit_pass in audit['passes']:
        if audit_pass['single_pass_gauge_screen'] == 'OUTSIDE_MODEL_DOMAIN':
            raise ValueError(f"pass {audit_pass['pass_number']}: outside inherited single-pass software gauge guard: "
                             + ', '.join(audit_pass['reasons']))
    if (not isinstance(interpass_handoffs, tuple) or len(interpass_handoffs) != len(passes)-1
            or not all(isinstance(event, InterpassHandoff) for event in interpass_handoffs)):
        raise ValueError('one explicit interpass handoff required after each nonfinal pass')
    handoffs = {}
    for event in interpass_handoffs:
        event.validate(len(passes))
        if event.after_pass in handoffs:
            raise ValueError('duplicate interpass handoff')
        handoffs[event.after_pass] = event
    if set(handoffs) != set(range(1, len(passes))):
        raise ValueError('interpass handoffs must identify every adjacent pass')
    for after_pass, event in handoffs.items():
        previous = passes[after_pass-1]
        following = passes[after_pass]
        if (previous.scenario.width_m != following.scenario.width_m
                and event.width_change_provenance is None):
            raise ValueError(f'pass {after_pass+1}: changed strip width requires an explicit interpass event')
        if previous.scenario.density_kg_m3 != following.scenario.density_kg_m3:
            raise ValueError(f'pass {after_pass+1}: density change has no interpass material model')
        if event.strip_mode == 'direct_predicted_carry' and previous.heat_boundary is None:
            raise ValueError(f'pass {after_pass+1}: cannot carry an unpredicted strip outlet temperature')
        if following.heat_boundary is None and event.roll_mode != 'not_modeled':
            raise ValueError(f'pass {after_pass+1}: roll thermal handoff requested without thermal model')
        if following.heat_boundary is not None and event.roll_mode == 'not_modeled':
            raise ValueError(f'pass {after_pass+1}: thermal pass needs an explicit roll handoff')
        if event.roll_mode == 'direct_predicted_carry' and previous.heat_boundary is None:
            raise ValueError(f'pass {after_pass+1}: cannot carry unpredicted roll thermal state')
        if event.roll_mode == 'direct_predicted_carry' and (
                previous.roll_body_id != following.roll_body_id
                or previous.scenario.work_roll_radius_m != following.scenario.work_roll_radius_m
                or previous.heat_boundary.roll_effective_mass_kg != following.heat_boundary.roll_effective_mass_kg):
            raise ValueError(f'pass {after_pass+1}: direct roll carry requires the same roll body, radius and effective mass')
    state = initial_state
    previous_roll_out = None
    outputs = []
    for index, item in enumerate(passes, 1):
        scenario = item.scenario
        boundary = item.heat_boundary
        if index > 1:
            event = handoffs[index-1]
            if event.strip_mode == 'direct_predicted_carry':
                if outputs[-1]['thermal'] is None:
                    raise ValueError(f'pass {index}: cannot carry an unpredicted strip outlet temperature')
            else:
                state = replace(state, temperature_k=event.strip_temperature_k,
                                history=state.history+(f'interpass_strip_temperature:{event.provenance}',))
            if boundary is None:
                if event.roll_mode != 'not_modeled':
                    raise ValueError(f'pass {index}: roll thermal handoff requested without thermal model')
            elif event.roll_mode == 'direct_predicted_carry':
                if previous_roll_out is None:
                    raise ValueError(f'pass {index}: cannot carry unpredicted roll thermal state')
                boundary = replace(boundary, roll_temperature_k=previous_roll_out)
            elif event.roll_mode == 'prescribed':
                boundary = replace(boundary, roll_temperature_k=event.roll_temperature_k)
            else:
                raise ValueError(f'pass {index}: thermal pass needs an explicit roll handoff')
        try:
            material = BiteHardening(state, law, item.assumed_strain_range,
                                     item.assumed_temperature_range_k)
            mean = material.mean_stress(scenario.entry_thickness_m, scenario.exit_thickness_m)
            # Scenario's required mean stress field is replaced, never used as an
            # independent calibration knob in this checked path.
            if (isinstance(scenario.mean_flow_stress_pa, bool)
                    or not isinstance(scenario.mean_flow_stress_pa, (int, float))
                    or not math.isfinite(scenario.mean_flow_stress_pa)
                    or scenario.mean_flow_stress_pa <= 0):
                raise ValueError('supplied Scenario mean-stress placeholder must be positive finite Pa')
            actual = replace(scenario, mean_flow_stress_pa=mean)
            actual.validate()
            if item.solver == 'spatial_slab':
                mechanics = solve_slab(actual, item.cells, bite_mode=item.bite_mode,
                                       material=material, verify_refinement=True)
            else:
                mechanics = solve_circular_contact(actual, item.elasticity, item.cells,
                                                   bite_mode=item.bite_mode, material=material,
                                                   verify_refinement=True)
            if not mechanics['numerical_converged']:
                raise ValueError('checked mechanics did not meet numerical convergence gates')
            thermal = None
            if boundary is not None:
                thermal = handoff_pass(mechanics, state, strip_cp, roll_cp, boundary,
                                       fluid=item.fluid_observation,
                                       passive_contact=item.passive_contact)
            elif item.passive_contact is not None:
                raise ValueError('passive contact requires thermal handoff')
        except ValueError as exc:
            raise ValueError(f'pass {index}: {exc}') from exc
        state_dict = thermal['strip_state_out'] if thermal is not None else mechanics['material']['state_out']
        state = MaterialState(**{**state_dict, 'history': tuple(state_dict['history'])})
        previous_roll_out = thermal['roll_temperature_out_k'] if thermal is not None else None
        operating = assess_pass_operating_plan(item.operating_plan, actual, mechanics,
                                                equipment_limits, thermal=thermal,
                                                requested_scenario=scenario)
        outputs.append({'pass_number': index, 'solver': item.solver,
                        'roll_body_id': item.roll_body_id,
                        'requested_scenario': asdict(scenario),
                        'effective_scenario': asdict(actual),
                        'gauge_audit': audit['passes'][index-1],
                        'mechanics': mechanics, 'thermal': thermal,
                        'interpass_handoff_before': None if index == 1 else asdict(handoffs[index-1]),
                        'operating': operating, 'state_out': asdict(state)})
    violations = [{'pass_number': item['pass_number'], 'check': check}
                  for item in outputs for check in
                  (item['operating']['range_checks'] + item['operating']['equipment_checks']
                   + item['operating']['observation_range_checks'])
                  if check['status'].startswith('OUTSIDE')]
    return {'status': 'DECLARED_BOUNDS_VIOLATED' if violations else 'CHECKED_SYNTHETIC_SCHEDULE',
            'declared_bounds_status': 'VIOLATED' if violations else 'INDETERMINATE',
            'declared_bound_violations': violations,
            'gauge_audit': audit, 'initial_state': asdict(initial_state),
            'final_state': asdict(state), 'passes': outputs,
            'limitations': ['Numerical checks and declared bounds do not establish aluminium calibration.',
                            'No temperature feedback into flow stress or interpass heat-transfer law.',
                            'No foil/pack mechanics, anneal kinetics, loaded gap or schedule optimisation.']}
