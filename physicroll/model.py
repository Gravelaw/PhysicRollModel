"""Synthetic steady-state flat-strip demonstrator. All dimensional values are SI.

See docs/model.md for equations, closure assumptions and rejection domain.
No Blender dependency, calibrated material database or plant interface.
"""
from dataclasses import asdict, dataclass, fields
import math


@dataclass(frozen=True)
class Scenario:
    name: str
    synthetic: bool
    entry_thickness_m: float
    exit_thickness_m: float
    width_m: float
    entry_speed_m_s: float
    work_roll_radius_m: float
    density_kg_m3: float
    mean_flow_stress_pa: float
    friction_coefficient: float
    entry_tension_pa: float
    exit_tension_pa: float
    drive_efficiency: float

    @classmethod
    def from_dict(cls, data):
        expected = {f.name for f in fields(cls)}
        if set(data) != expected:
            raise ValueError(f"Scenario keys: missing {expected - set(data)}, unknown {set(data) - expected}")
        result = cls(**data)
        result.validate()
        return result

    def validate(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a nonempty string")
        if self.synthetic is not True:
            raise ValueError("This prototype accepts only explicitly synthetic scenarios")
        for f in fields(self):
            if f.name in ('name', 'synthetic'):
                continue
            x = getattr(self, f.name)
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
                raise ValueError(f"{f.name} must be a finite number in SI units")
            if x < 0 or (x == 0 and f.name not in ('friction_coefficient', 'entry_tension_pa', 'exit_tension_pa')):
                raise ValueError(f"{f.name} is outside its positive/nonnegative domain")
        h0, h1, r = self.entry_thickness_m, self.exit_thickness_m, self.work_roll_radius_m
        if h1 < 0.0003:
            raise ValueError("Foil excluded: prototype exit gauge must be >= 0.0003 m (300 micrometres)")
        if not 0.5 * h0 <= h1 <= h0:
            raise ValueError("Prototype domain: reduction must be between 0 and 50 percent")
        if h0 / r > 0.05 or self.width_m / h0 < 20:
            raise ValueError("Requires thin, wide strip: h0/R <= 0.05 and width/h0 >= 20")
        if self.friction_coefficient > 0.3 or self.drive_efficiency > 1:
            raise ValueError("Requires friction <= 0.3 and 0 < drive efficiency <= 1")
        if max(self.entry_tension_pa, self.exit_tension_pa) >= self.mean_flow_stress_pa:
            raise ValueError("Tensions must stay below the supplied mean uniaxial flow stress")
        if h0 == h1 and self.entry_tension_pa != self.exit_tension_pa:
            raise ValueError("Zero-draft transport requires equal tension stresses")


def solve(s: Scenario) -> dict:
    s.validate()
    h0, h1, r, mu = s.entry_thickness_m, s.exit_thickness_m, s.work_roll_radius_m, s.friction_coefficient
    draft = h0 - h1
    # Exact rigid-circle projected contact length; stable near zero draft.
    length = math.sqrt(r * draft - draft * draft / 4)
    angle = math.atan2(length, r - draft / 2)
    if math.tan(angle) > mu + 1e-12:
        raise ValueError("Fails conservative unassisted bite check: tan(alpha) <= mu")
    q = s.width_m * h0 * s.entry_speed_m_s
    v1 = s.entry_speed_m_s * h0 / h1
    strain = math.log(h0 / h1)
    kps = 2 / math.sqrt(3) * s.mean_flow_stress_pa
    friction_factor = mu * length / ((h0 + h1) / 2)
    # Heuristic load closure; not a numerical slab solution.
    pressure = kps * (1 + friction_factor) - (s.entry_tension_pa + s.exit_tension_pa) / 2
    force = s.width_m * length * pressure
    ideal = q * kps * strain
    dissipation = ideal * friction_factor
    tension_power = q * (s.exit_tension_pa - s.entry_tension_pa)
    roll_power = ideal + dissipation - tension_power
    if roll_power < 0:
        raise ValueError("Tension-driven/regenerative regime is outside this prototype")
    # Synthetic neutral-speed closure; speed lies between entry and exit speeds.
    roll_speed = (s.entry_speed_m_s + v1) / 2
    omega = roll_speed / r
    torque = roll_power / (2 * omega)
    traction_bound = mu * force * r
    if torque > traction_bound * (1 + 1e-12):
        raise ValueError("Required torque exceeds the Coulomb traction upper bound")
    result = {
        'model_version': '0.1.0', 'scenario': asdict(s),
        'status': 'SYNTHETIC_UNCALIBRATED',
        'reduction_fraction': draft / h0, 'true_thickness_strain': strain,
        'contact_length_m': length, 'bite_angle_rad': angle,
        'volume_flow_m3_s': q, 'mass_flow_kg_s': s.density_kg_m3 * q,
        'exit_speed_m_s': v1, 'roll_surface_speed_m_s': roll_speed,
        'roll_angular_speed_rad_s': omega,
        'assumed_forward_slip_fraction': v1 / roll_speed - 1,
        'mean_contact_pressure_pa': pressure if draft else 0.0,
        'separating_force_n': force, 'entry_tension_force_n': s.entry_tension_pa * s.width_m * h0,
        'exit_tension_force_n': s.exit_tension_pa * s.width_m * h1,
        'ideal_plastic_power_w': ideal, 'extra_dissipation_power_w': dissipation,
        'net_tension_power_w': tension_power, 'roll_mechanical_power_w': roll_power,
        'roll_drive_electrical_power_w': roll_power / s.drive_efficiency,
        'torque_per_work_roll_nm': torque, 'traction_torque_bound_per_roll_nm': traction_bound,
        'energy_residual_w': 2 * torque * omega + tension_power - ideal - dissipation,
        'warnings': ['Synthetic inputs; no alloy or plant calibration.',
                     'Pressure, dissipation and roll-speed closures are illustrative.',
                     'Zero draft is unloaded transport, not a temper/skin-pass model.']}

    if any(isinstance(v, (int, float)) and not math.isfinite(v) for v in result.values()):
        raise ValueError("Nonfinite result: input magnitudes exceed numerical domain")
    return result
