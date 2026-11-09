"""Prescribed-flow moving-material and variable-reel flux benchmark.

This idealized verification case reports reaction torques. It does not predict
transport speed, tension, winding strain, or a roll-bite/contact response.
"""

from dataclasses import dataclass
import math


MODEL_ID = 'T2A3_PRESCRIBED_FLOW_REEL_FLUX_V1'


def _positive_number(value, name):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'{name} must be a finite positive number')


@dataclass(frozen=True)
class T2A3Case:
    duration_s: float = 2.0
    step_s: float = 0.01
    transport_speed_m_s: float = 0.1
    stretch: float = 1.001
    span_length_m: float = 1.0
    youngs_modulus_pa: float = 1e7
    width_m: float = 0.1
    reference_thickness_m: float = 0.001
    density_kg_m3: float = 1000.0
    core_radius_m: float = 0.1
    core_inertia_kg_m2: float = 0.01
    left_initial_reference_length_m: float = 10.0
    right_initial_reference_length_m: float = 1.0

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            _positive_number(getattr(self, name), name)
        if self.stretch <= 1:
            raise ValueError('T2A3 requires positive declared span tension')
        step_count = self.duration_s / self.step_s
        if self.step_s > 0.04 or not math.isfinite(step_count) or step_count > 2000:
            raise ValueError('T2A3 exceeds the frozen sampling budget')
        released = self.transport_speed_m_s * self.duration_s / self.stretch
        if released >= self.left_initial_reference_length_m:
            raise ValueError('T2A3 would exhaust the left reel inventory')
        area = self.width_m * self.reference_thickness_m
        derived = (area, self.density_kg_m3 * area,
                   self.youngs_modulus_pa * area * (self.stretch - 1),
                   self.core_radius_m ** 2 + self.reference_thickness_m *
                   (self.right_initial_reference_length_m + released) / math.pi)
        if not all(math.isfinite(value) and value > 0 for value in derived):
            raise ValueError('T2A3 parameters exceed the finite physical domain')


def _sample(case, time_s):
    speed = case.transport_speed_m_s
    stretch = case.stretch
    area = case.width_m * case.reference_thickness_m
    line_mass = case.density_kg_m3 * area
    ea = case.youngs_modulus_pa * area
    tension = ea * (stretch - 1)
    stored_energy_per_reference_m = 0.5 * ea * (stretch - 1) ** 2
    reference_flux = speed / stretch
    thickness = case.reference_thickness_m / stretch
    kappa = case.reference_thickness_m / math.pi
    core_radius = case.core_radius_m
    reels = {}
    for side, initial_length, direction in (
            ('left', case.left_initial_reference_length_m, -1),
            ('right', case.right_initial_reference_length_m, 1)):
        signed_reference_flux = direction * reference_flux
        length = initial_length + signed_reference_flux * time_s
        radius = math.sqrt(core_radius ** 2 + kappa * length)
        initial_radius = math.sqrt(core_radius ** 2 + kappa * initial_length)
        inertia = case.core_inertia_kg_m2 + line_mass * (
            core_radius ** 2 * length + kappa * length ** 2 / 2)
        omega = speed / radius
        angular_acceleration = -speed * kappa * signed_reference_flux / (2 * radius ** 3)
        angle = 2 * speed * time_s / (radius + initial_radius)
        tension_torque = -direction * radius * tension
        drive_torque = inertia * angular_acceleration - tension_torque
        reels[side] = {
            'reference_length_m': length,
            'wound_mass_kg': line_mass * length,
            'radius_m': radius,
            'inertia_kg_m2': inertia,
            'angle_rad': angle,
            'speed_rad_s': omega,
            'acceleration_rad_s2': angular_acceleration,
            'reaction_drive_torque_nm': drive_torque,
            'tension_torque_nm': tension_torque,
            'signed_reference_flux_m_s': signed_reference_flux,
            'signed_mass_flux_kg_s': line_mass * signed_reference_flux,
            'angular_momentum_kg_m2_s': inertia * omega,
            'kinetic_energy_j': 0.5 * inertia * omega ** 2,
            'stored_strain_energy_j': stored_energy_per_reference_m * length,
        }
    span_reference_length = case.span_length_m / stretch
    span_mass = line_mass * span_reference_length
    span_energy = (0.5 * line_mass * speed ** 2 +
                   stored_energy_per_reference_m) * span_reference_length
    total_mass = span_mass + sum(reel['wound_mass_kg'] for reel in reels.values())
    total_energy = span_energy + sum(reel['kinetic_energy_j'] +
                                     reel['stored_strain_energy_j']
                                     for reel in reels.values())
    state = {
        'time_s': time_s,
        'left_material_label_m': -reference_flux * time_s,
        'right_material_label_m': (case.span_length_m - speed * time_s) / stretch,
        'reference_flux_m_s': reference_flux,
        'mass_flux_kg_s': line_mass * reference_flux,
        'span_mass_kg': span_mass,
        'span_kinetic_energy_j': 0.5 * span_mass * speed ** 2,
        'span_stored_strain_energy_j': stored_energy_per_reference_m *
        span_reference_length,
        'current_thickness_m': thickness,
        'declared_span_tension_n': tension,
        'total_mass_kg': total_mass,
        'total_mechanical_energy_j': total_energy,
        'reels': reels,
    }
    if not all(math.isfinite(value) for value in (
            total_mass, total_energy, *(
                number for reel in reels.values() for number in reel.values()))):
        raise ValueError('T2A3 state exceeded the finite numerical domain')
    return state


def _simpson(start, middle, end, h):
    return h * (start + 4 * middle + end) / 6


def _rates(state, side, line_mass, stored_energy_per_reference_m, speed):
    reel = state['reels'][side]
    signed_reference_flux = reel['signed_reference_flux_m_s']
    mass_flux = line_mass * signed_reference_flux
    angular_rhs = (reel['reaction_drive_torque_nm'] + reel['tension_torque_nm'] +
                   mass_flux * reel['radius_m'] * speed)
    energy_rhs = ((reel['reaction_drive_torque_nm'] +
                   reel['tension_torque_nm']) * reel['speed_rad_s'] +
                  signed_reference_flux *
                  (0.5 * line_mass * speed ** 2 + stored_energy_per_reference_m))
    drive_power = reel['reaction_drive_torque_nm'] * reel['speed_rad_s']
    return angular_rhs, energy_rhs, drive_power


def run_prescribed_reel_flux(case: T2A3Case):
    """Evaluate the frozen analytic trajectory and independently integrate fluxes."""
    if not isinstance(case, T2A3Case):
        raise ValueError('T2A3 requires a T2A3Case')
    area = case.width_m * case.reference_thickness_m
    line_mass = case.density_kg_m3 * area
    stored_energy_per_reference_m = (
        0.5 * case.youngs_modulus_pa * area * (case.stretch - 1) ** 2)
    states = [_sample(case, 0.0)]
    max_angular = {'left': 0.0, 'right': 0.0}
    max_energy = {'left': 0.0, 'right': 0.0}
    max_mass = {'left': 0.0, 'right': 0.0}
    max_total_energy = 0.0
    steps = math.ceil(case.duration_s / case.step_s)
    for index in range(steps):
        start = states[-1]
        end_time = min((index + 1) * case.step_s, case.duration_s)
        h = end_time - start['time_s']
        middle = _sample(case, start['time_s'] + h / 2)
        end = _sample(case, end_time)
        drive_work = 0.0
        for side in ('left', 'right'):
            a, m, b = (state['reels'][side] for state in (start, middle, end))
            start_rates = _rates(start, side, line_mass,
                                 stored_energy_per_reference_m, case.transport_speed_m_s)
            middle_rates = _rates(middle, side, line_mass,
                                  stored_energy_per_reference_m, case.transport_speed_m_s)
            end_rates = _rates(end, side, line_mass,
                               stored_energy_per_reference_m, case.transport_speed_m_s)
            max_angular[side] = max(max_angular[side], abs(
                b['angular_momentum_kg_m2_s'] - a['angular_momentum_kg_m2_s'] -
                _simpson(start_rates[0], middle_rates[0], end_rates[0], h)))
            max_energy[side] = max(max_energy[side], abs(
                (b['kinetic_energy_j'] + b['stored_strain_energy_j']) -
                (a['kinetic_energy_j'] + a['stored_strain_energy_j']) -
                _simpson(start_rates[1], middle_rates[1], end_rates[1], h)))
            max_mass[side] = max(max_mass[side], abs(
                b['wound_mass_kg'] - a['wound_mass_kg'] -
                h * a['signed_mass_flux_kg_s']))
            drive_work += _simpson(start_rates[2], middle_rates[2], end_rates[2], h)
        max_total_energy = max(max_total_energy, abs(
            end['total_mechanical_energy_j'] - start['total_mechanical_energy_j'] -
            drive_work))
        states.append(end)
    return {
        'model_id': MODEL_ID,
        'mode': 'constant_prescribed_transport_reaction',
        'shaft_speed_role': 'prescribed_transport_kinematic_reel_speed',
        'span_tension_role': 'declared_constant_stretch',
        'episode_outcome': 'COMPLETED_REQUESTED_DURATION',
        'requested_duration_s': case.duration_s,
        'completed_duration_s': states[-1]['time_s'],
        'states': states,
        'maximum_reel_angular_impulse_defect_nm_s': max_angular,
        'maximum_reel_energy_defect_j': max_energy,
        'maximum_reel_mass_defect_kg': max_mass,
        'maximum_total_energy_defect_j': max_total_energy,
        'limitations': ['prescribed constant speed and retained constant stretch',
                        'ideal no-slip transfer and no winding loss or compaction',
                        'no torque-driven speed, variable tension, bite or contact'],
    }
