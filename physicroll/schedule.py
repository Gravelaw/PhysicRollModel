"""Prescribed sequential gauges and synthetic pass-state handoff (SI units).

This module does not choose a pass schedule or extend the single-pass model to foil.
"""
from dataclasses import asdict, dataclass, replace
import math

from .materials import MaterialState, PowerHardeningLaw, pass_with_history
from .model import Scenario
from .operating import EquipmentLimits, PassOperatingPlan, assess_pass_operating_plan


def _positive_finite(value):
    return (not isinstance(value, bool) and isinstance(value, (float, int))
            and math.isfinite(value) and value > 0)


@dataclass(frozen=True)
class GaugeSchedule:
    """Full entry gauge followed by each prescribed pass exit gauge, in metres."""
    name: str
    gauges_m: tuple[float, ...]
    target_exit_m: float

    def validate(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError('schedule name must be nonempty')
        if not isinstance(self.gauges_m, tuple) or len(self.gauges_m) < 2:
            raise ValueError('at least one prescribed pass is required')
        if not all(_positive_finite(h) for h in self.gauges_m):
            raise ValueError('full gauges must be positive finite metres')
        if any(a <= b for a, b in zip(self.gauges_m, self.gauges_m[1:])):
            raise ValueError('prescribed gauges must strictly decrease at every pass')
        if not _positive_finite(self.target_exit_m) or self.gauges_m[-1] != self.target_exit_m:
            raise ValueError('last prescribed exit gauge must equal the final target')


def inspect_gauge_schedule(schedule: GaugeSchedule) -> dict:
    """Kinematic audit only; supported-looking passes still need complete inputs."""
    schedule.validate()
    coefficient = 2 / math.sqrt(3)
    passes = []
    cumulative_log = 0.0
    cumulative_equivalent = 0.0
    for index, (entry, exit_) in enumerate(zip(schedule.gauges_m, schedule.gauges_m[1:]), 1):
        increment = math.log(entry / exit_)
        cumulative_log += increment
        cumulative_equivalent += coefficient * increment
        reasons = []
        if exit_ < 0.0003:
            reasons.append('FOIL_EXIT_BELOW_300_UM_SINGLE_PASS_MODEL_GUARD')
        if exit_ < 0.5 * entry:
            reasons.append('REDUCTION_EXCEEDS_50_PERCENT_SINGLE_PASS_MODEL_GUARD')
        passes.append({'pass_number': index, 'entry_thickness_m': entry,
                       'exit_thickness_m': exit_, 'reduction_fraction': 1 - exit_ / entry,
                       'log_thickness_strain_increment': increment,
                       'plane_strain_equivalent_increment': coefficient * increment,
                       'cumulative_log_thickness_strain': cumulative_log,
                       'cumulative_plane_strain_equivalent_strain': cumulative_equivalent,
                       'single_pass_gauge_screen': 'OUTSIDE_MODEL_DOMAIN' if reasons else 'NEEDS_FULL_INPUTS',
                       'reasons': reasons})
    return {'status': 'KINEMATIC_AUDIT_ONLY', 'name': schedule.name,
            'target_exit_m': schedule.target_exit_m, 'passes': passes,
            'total_log_thickness_strain': math.log(schedule.gauges_m[0] / schedule.target_exit_m),
            'total_plane_strain_equivalent_increment': coefficient * math.log(schedule.gauges_m[0] / schedule.target_exit_m),
            'limitations': ['Gauge screen is the existing demonstrator guard, not a physical pass limit.',
                            'No alloy, mill rating, bite, force, torque, power or temperature feasibility is inferred.',
                            'Plane-strain equivalent strain assumes homogeneous incompressible deformation without recovery.']}


@dataclass(frozen=True)
class InterpassTemperature:
    """Externally supplied state temperature after a pass; no heat transfer inferred."""
    after_pass: int
    temperature_k: float
    provenance: str

    def validate(self, pass_count):
        if (isinstance(self.after_pass, bool) or not isinstance(self.after_pass, int)
                or not 1 <= self.after_pass < pass_count):
            raise ValueError('temperature event must follow a nonfinal pass')
        if not _positive_finite(self.temperature_k):
            raise ValueError('interpass absolute temperature must be positive and finite')
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError('interpass temperature provenance is required')


def run_prescribed_schedule(passes: tuple[Scenario, ...], initial_state: MaterialState,
                            law: PowerHardeningLaw, *,
                            operating_plans: tuple[PassOperatingPlan, ...],
                            equipment_limits: EquipmentLimits | None = None,
                            interpass_temperatures: tuple[InterpassTemperature, ...] = ()) -> dict:
    """Chain the existing synthetic mean-hardening/legacy mechanics pass calculation.

    Every pass is checked before solving. No anneal or strain reset is supported.
    The caller supplies each pass's speed, tension, friction and other conditions.
    """
    if not isinstance(passes, tuple) or not passes or not all(isinstance(p, Scenario) for p in passes):
        raise ValueError('passes must be a nonempty tuple of Scenario values')
    if not isinstance(initial_state, MaterialState) or not isinstance(law, PowerHardeningLaw):
        raise ValueError('explicit material state and synthetic hardening law required')
    if (not isinstance(operating_plans, tuple) or len(operating_plans) != len(passes)
            or not all(isinstance(plan, PassOperatingPlan) for plan in operating_plans)):
        raise ValueError('exactly one explicit operating plan is required per pass')
    for index, plan in enumerate(operating_plans, 1):
        try:
            plan.validate()
        except ValueError as exc:
            raise ValueError(f'pass {index}: {exc}') from exc
    if equipment_limits is not None:
        if not isinstance(equipment_limits, EquipmentLimits):
            raise ValueError('equipment_limits must be EquipmentLimits')
        equipment_limits.validate()
    if not isinstance(interpass_temperatures, tuple) or not all(
            isinstance(event, InterpassTemperature) for event in interpass_temperatures):
        raise ValueError('interpass_temperatures must be a tuple of temperature events')
    initial_state.validate()
    law.validate()
    if (initial_state.alloy, initial_state.temper) != (law.alloy, law.temper):
        raise ValueError('initial state and law material identity differ')
    for index, scenario in enumerate(passes, 1):
        try:
            scenario.validate()
        except ValueError as exc:
            raise ValueError(f'pass {index}: {exc}') from exc
    gauges = (passes[0].entry_thickness_m,) + tuple(p.exit_thickness_m for p in passes)
    for index, (prior, following) in enumerate(zip(passes, passes[1:]), 1):
        if prior.exit_thickness_m != following.entry_thickness_m:
            raise ValueError(f'pass {index + 1}: entry gauge does not equal preceding exit gauge')
    audit = inspect_gauge_schedule(GaugeSchedule(passes[0].name, gauges, gauges[-1]))
    events = {}
    for event in interpass_temperatures:
        event.validate(len(passes))
        if event.after_pass in events:
            raise ValueError(f'duplicate interpass temperature after pass {event.after_pass}')
        events[event.after_pass] = event
    state = initial_state
    outputs = []
    for index, scenario in enumerate(passes, 1):
        try:
            result = pass_with_history(scenario, state, law)
        except ValueError as exc:
            raise ValueError(f'pass {index}: {exc}') from exc
        state = replace(state,
                        accumulated_equivalent_plastic_strain=result['state_out']['accumulated_equivalent_plastic_strain'],
                        history=state.history + (scenario.name,))
        event = events.get(index)
        if event is not None:
            state = replace(state, temperature_k=event.temperature_k,
                            history=state.history + (f'interpass_temperature:{event.provenance}',))
        outputs.append({'pass_number': index, 'gauge_audit': audit['passes'][index - 1],
                        'mechanics': result, 'interpass_temperature': asdict(event) if event else None,
                        'operating': assess_pass_operating_plan(operating_plans[index - 1], scenario,
                                                                result, equipment_limits),
                        'state_for_next_pass': asdict(state)})
    return {'status': 'SYNTHETIC_UNCALIBRATED_PRESCRIBED_SCHEDULE',
            'mechanics_model': 'legacy_heuristic_mean_hardening',
            'initial_state': asdict(initial_state), 'final_state': asdict(state),
            'gauge_audit': audit, 'passes': outputs,
            'limitations': ['No schedule optimisation or inferred pass count.',
                            'No interpass heat transfer, recovery, annealing or strain reset.',
                            'No mill ratings or alloy calibration supplied by this interface.',
                            'Each pass uses the existing illustrative pressure, torque and speed closures.']}
