"""Measured/synthetic fluid inputs and a declared effective-friction parameter.

No viscosity-to-friction, oil-film, pressure-flow or coolant-to-HTC law is fitted.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FluidObservation:
    identity: str
    fluid_type: str
    flow_m3_s: float | None
    supply_temperature_k: float | None
    dynamic_viscosity_pa_s: float | None
    roll_rms_roughness_m: float | None
    strip_rms_roughness_m: float | None
    source: str
    quality: str

    def validate(self):
        if not self.identity or self.fluid_type not in ('neat_oil', 'emulsion', 'other'):
            raise ValueError('fluid identity and type are required')
        if not self.source or self.quality not in ('synthetic', 'qualified', 'unknown'):
            raise ValueError('observation provenance and quality are required')
        for key in ('flow_m3_s', 'supply_temperature_k', 'dynamic_viscosity_pa_s',
                    'roll_rms_roughness_m', 'strip_rms_roughness_m'):
            value = getattr(self, key)
            if value is not None and (not isinstance(value, (float, int)) or isinstance(value, bool)
                                      or not math.isfinite(value) or value < 0):
                raise ValueError(f'{key} must be missing or nonnegative and finite')
        if self.supply_temperature_k == 0:
            raise ValueError('absolute fluid temperature must be positive')


@dataclass(frozen=True)
class EffectiveFriction:
    coefficient: float
    source: str
    fit_uses_force_torque_slip: bool
    calibrated: bool

    def validate(self):
        if not self.source or not math.isfinite(self.coefficient) or not 0 <= self.coefficient <= 0.3:
            raise ValueError('friction requires source and prototype-domain coefficient')
        if self.calibrated and not self.fit_uses_force_torque_slip:
            raise ValueError('calibrated friction claim requires joint force/torque/slip fit')


def declared_closure(fluid: FluidObservation, friction: EffectiveFriction) -> dict:
    fluid.validate()
    friction.validate()
    missing = [key for key in ('flow_m3_s', 'supply_temperature_k', 'dynamic_viscosity_pa_s',
                              'roll_rms_roughness_m', 'strip_rms_roughness_m') if getattr(fluid, key) is None]
    return {'effective_friction_coefficient': friction.coefficient,
            'closure_status': 'CALIBRATED_EFFECTIVE' if friction.calibrated else 'SYNTHETIC_UNCALIBRATED',
            'fluid_identity': fluid.identity, 'fluid_type': fluid.fluid_type,
            'unobserved_inputs': missing, 'film_dissipation_resolved': False,
            'cooling_boundary_calibrated': False}
