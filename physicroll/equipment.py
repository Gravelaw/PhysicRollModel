"""Synthetic stand/reel bookkeeping around the steady-state rolling core.

All values are SI. This module does not solve mill elasticity, reel dynamics,
roll flattening, strip recovery or a control loop.
"""
from dataclasses import asdict, dataclass, fields
import math
from .model import Scenario, solve
from .observations import reel_shaft_torque_nm, strip_mass_flow_kg_s, tension_stress_pa


@dataclass(frozen=True)
class EquipmentAssumptions:
    synthetic: bool
    stand_stiffness_n_m: float
    entry_reel_radius_m: float
    exit_reel_radius_m: float
    entry_reel_inertia_kg_m2: float
    exit_reel_inertia_kg_m2: float

    @classmethod
    def from_dict(cls, data):
        expected = {f.name for f in fields(cls)}
        if not isinstance(data, dict) or set(data) != expected:
            raise ValueError('Equipment assumptions must contain exactly: ' + ', '.join(sorted(expected)))
        result = cls(**data)
        result.validate()
        return result

    def validate(self):
        if self.synthetic is not True:
            raise ValueError('Equipment assumptions must be labelled synthetic')
        for f in fields(self):
            if f.name == 'synthetic':
                continue
            value = getattr(self, f.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'{f.name} must be a finite SI number')
            if value < 0 or (value == 0 and 'inertia' not in f.name):
                raise ValueError(f'{f.name} must be positive (inertia may be zero)')


def evaluate_equipment(scenario: Scenario, assumptions: EquipmentAssumptions,
                       process: dict | None = None) -> dict:
    """Evaluate a static stand/reel snapshot without changing the rolling solution.

    F/K is an *assumed total stand compliance*. It is not an extra force or
    an independent roll flattening calculation. Exit gauge is prescribed and
    treated as the loaded gap; no elastic strip recovery is solved.
    """
    scenario.validate()
    assumptions.validate()
    if process is None:
        process = solve(scenario)
    if process.get('scenario') != asdict(scenario) or process.get('model_version') != '0.1.0':
        raise ValueError('Process result provenance does not match the supplied scenario/model')
    force = process['separating_force_n']
    t0, t1 = process['entry_tension_force_n'], process['exit_tension_force_n']
    v0, v1 = scenario.entry_speed_m_s, process['exit_speed_m_s']
    if not all(math.isfinite(v) and v >= 0 for v in (force, t0, t1, v1)):
        raise ValueError('Process result contains invalid coupling quantities')
    if (not math.isclose(t0, scenario.entry_tension_pa*scenario.width_m*scenario.entry_thickness_m,rel_tol=1e-12)
        or not math.isclose(t1, scenario.exit_tension_pa*scenario.width_m*scenario.exit_thickness_m,rel_tol=1e-12)
        or not math.isclose(v1*scenario.exit_thickness_m, v0*scenario.entry_thickness_m,rel_tol=1e-12)):
        raise ValueError('Process tension or mass-flow quantities disagree with the scenario')
    # Equilibrium: total stand reaction equals bite separating force. Per side
    # assumes a symmetric operator/drive split, not four extra independent loads.
    deflection = force / assumptions.stand_stiffness_n_m
    unloaded_gap = scenario.exit_thickness_m - deflection
    if unloaded_gap < 0:
        raise ValueError('Implied unloaded gap is negative; chosen synthetic stand stiffness is infeasible')
    w0, w1 = v0 / assumptions.entry_reel_radius_m, v1 / assumptions.exit_reel_radius_m
    entry_torque = reel_shaft_torque_nm(t0, assumptions.entry_reel_radius_m,
        assumptions.entry_reel_inertia_kg_m2, 0, winding=False)
    exit_torque = reel_shaft_torque_nm(t1, assumptions.exit_reel_radius_m,
        assumptions.exit_reel_inertia_kg_m2, 0, winding=True)
    result = {
        'equipment_model_version': '0.2.0', 'status': 'SYNTHETIC_UNCALIBRATED_STATIC_SNAPSHOT',
        'scenario_name': scenario.name, 'process_model_version': process['model_version'],
        'assumptions': asdict(assumptions),
        'bite_separating_force_n': force, 'stand_reaction_total_n': force,
        'stand_reaction_per_side_n': force / 2,
        'assumed_stand_extension_m': deflection,
        'implied_unloaded_gap_m': unloaded_gap,
        'prescribed_loaded_gap_m': scenario.exit_thickness_m,
        'recovered_strip_thickness_m': None,
        'entry_strip_tension_force_n': t0, 'exit_strip_tension_force_n': t1,
        'entry_tension_stress_pa': tension_stress_pa(t0, scenario.width_m, scenario.entry_thickness_m),
        'exit_tension_stress_pa': tension_stress_pa(t1, scenario.width_m, scenario.exit_thickness_m),
        'entry_local_mass_flow_kg_s': strip_mass_flow_kg_s(scenario.density_kg_m3, scenario.width_m, scenario.entry_thickness_m, v0),
        'exit_local_mass_flow_kg_s': strip_mass_flow_kg_s(scenario.density_kg_m3, scenario.width_m, scenario.exit_thickness_m, v1),
        'entry_reel_angular_speed_rad_s': w0, 'exit_reel_angular_speed_rad_s': w1,
        'entry_reel_signed_torque_on_strip_nm': entry_torque,
        'exit_reel_signed_torque_on_strip_nm': exit_torque,
        'entry_reel_signed_power_on_strip_w': entry_torque * w0,
        'exit_reel_signed_power_on_strip_w': exit_torque * w1,
        'net_reel_power_on_strip_w': entry_torque*w0 + exit_torque*w1,
        'entry_reel_rotational_energy_j': .5*assumptions.entry_reel_inertia_kg_m2*w0*w0,
        'exit_reel_rotational_energy_j': .5*assumptions.exit_reel_inertia_kg_m2*w1*w1,
        'reel_acceleration_torque_nm': None,
        'mass_flow_residual_kg_s': strip_mass_flow_kg_s(scenario.density_kg_m3, scenario.width_m, scenario.entry_thickness_m, v0)
            - strip_mass_flow_kg_s(scenario.density_kg_m3, scenario.width_m, scenario.exit_thickness_m, v1),
        'stand_force_residual_n': force - force,
        'reel_tension_power_residual_w': entry_torque*w0 + exit_torque*w1 - process['net_tension_power_w'],
        'warnings': [
            'Stiffness, reel radii and inertias are synthetic stand/reel assumptions.',
            'Stand reaction is the existing separating force on an assumed symmetric load path; do not add it to bite force.',
            'Reel signs describe work on strip: entry pays out/brakes, exit winds/pulls.',
            'No reel acceleration, changing radius, motor losses or dynamic strip tension is solved.',
            'Loaded gap equals prescribed exit gauge only in this rigid-strip demonstrator; recovered thickness is unknown.',
        ],
    }
    if any(isinstance(v,(int,float)) and not math.isfinite(v) for v in result.values()):
        raise ValueError('Nonfinite equipment result')
    return result
