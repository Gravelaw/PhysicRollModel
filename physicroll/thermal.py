"""Two-capacity, collapsed-interface heat budget for a prescribed short time step.

All power terms are watts, flux is W/m2, volumetric source W/m3. This is a
conservation demonstrator, not a resolved roll-bite temperature prediction.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ThermalStep:
    strip_temperature_k: float
    roll_temperature_k: float
    strip_mass_kg: float
    roll_mass_kg: float
    strip_heat_capacity_j_kg_k: float
    roll_heat_capacity_j_kg_k: float
    duration_s: float
    deforming_volume_m3: float
    contact_area_m2: float
    plastic_power_w: float
    plastic_heat_fraction: float
    signed_solid_traction_pa: float
    signed_relative_slip_m_s: float
    strip_slip_heat_fraction: float
    contact_conductance_w_m2_k: float
    strip_cooling_conductance_w_k: float
    roll_cooling_conductance_w_k: float
    strip_coolant_temperature_k: float
    roll_coolant_temperature_k: float
    contact_law: str = 'conductive_only'


def step(state: ThermalStep) -> dict:
    """Explicit Euler heat step with diagnostic source and interface budgets.

    ``contact_law='fitted_effective'`` forbids explicit solid slip heating because
    a fitted effective coefficient might already absorb it. No lubricant-film
    dissipation is resolved; its pressure-flow work needs a separate closure.
    """
    d = vars(state)
    for key, value in d.items():
        if key == 'contact_law':
            continue
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError(f'{key} must be finite')
    positive = ('strip_temperature_k', 'roll_temperature_k', 'strip_mass_kg',
                'roll_mass_kg', 'strip_heat_capacity_j_kg_k', 'roll_heat_capacity_j_kg_k',
                'duration_s', 'deforming_volume_m3', 'contact_area_m2',
                'strip_coolant_temperature_k', 'roll_coolant_temperature_k')
    if any(d[k] <= 0 for k in positive):
        raise ValueError('temperatures, capacities, duration, volume and area must be positive')
    nonnegative = ('plastic_power_w', 'contact_conductance_w_m2_k',
                   'strip_cooling_conductance_w_k', 'roll_cooling_conductance_w_k')
    if any(d[k] < 0 for k in nonnegative):
        raise ValueError('power and conductances must be nonnegative')
    if not (0 <= state.plastic_heat_fraction <= 1 and 0 <= state.strip_slip_heat_fraction <= 1):
        raise ValueError('heat fractions must be within [0,1]')
    if state.contact_law not in ('conductive_only', 'fitted_effective'):
        raise ValueError('unknown contact law')
    signed_slip_work_flux = state.signed_solid_traction_pa * state.signed_relative_slip_m_s
    if not math.isfinite(signed_slip_work_flux) or signed_slip_work_flux < 0:
        raise ValueError('solid traction and relative slip must dissipate, not generate, heat')
    slip_flux = signed_slip_work_flux
    if state.contact_law == 'fitted_effective' and slip_flux > 0:
        raise ValueError('explicit slip heat cannot accompany a fitted effective contact law')
    slip_power = slip_flux * state.contact_area_m2
    plastic_heat = state.plastic_power_w * state.plastic_heat_fraction
    contact_to_strip = (state.contact_conductance_w_m2_k * state.contact_area_m2
                        * (state.roll_temperature_k - state.strip_temperature_k))
    strip_cooling = state.strip_cooling_conductance_w_k * (state.strip_temperature_k - state.strip_coolant_temperature_k)
    roll_cooling = state.roll_cooling_conductance_w_k * (state.roll_temperature_k - state.roll_coolant_temperature_k)
    strip_rate = plastic_heat + state.strip_slip_heat_fraction * slip_power + contact_to_strip - strip_cooling
    roll_rate = (1 - state.strip_slip_heat_fraction) * slip_power - contact_to_strip - roll_cooling
    strip_capacity = state.strip_mass_kg * state.strip_heat_capacity_j_kg_k
    roll_capacity = state.roll_mass_kg * state.roll_heat_capacity_j_kg_k
    quantities = (strip_capacity, roll_capacity, slip_power, plastic_heat, contact_to_strip,
                  strip_cooling, roll_cooling, strip_rate, roll_rate)
    if not all(math.isfinite(v) for v in quantities) or min(strip_capacity,roll_capacity) <= 0:
        raise ValueError('derived heat/capacity overflows or underflows numerical domain')
    contact_g = state.contact_conductance_w_m2_k * state.contact_area_m2
    a = (contact_g+state.strip_cooling_conductance_w_k)/strip_capacity
    d = (contact_g+state.roll_cooling_conductance_w_k)/roll_capacity
    coupling = math.sqrt(contact_g/strip_capacity)*math.sqrt(contact_g/roll_capacity)
    lambda_max = (a+d+math.hypot(a-d,2*coupling))/2
    # dt*lambda <= 1 keeps every dissipative thermal mode non-oscillatory.
    # The old row bound could swap two equal-capacity bodies indefinitely.
    if not math.isfinite(lambda_max) or state.duration_s*lambda_max > 1:
        raise ValueError('time step exceeds non-oscillatory explicit thermal bound')
    strip_next = state.strip_temperature_k + state.duration_s * strip_rate / strip_capacity
    roll_next = state.roll_temperature_k + state.duration_s * roll_rate / roll_capacity
    if min(strip_next, roll_next) <= 0 or not all(map(math.isfinite, (strip_next, roll_next))):
        raise ValueError('time step gives nonphysical temperature')
    energy_change = strip_capacity * (strip_next - state.strip_temperature_k) + roll_capacity * (roll_next - state.roll_temperature_k)
    expected = state.duration_s * (plastic_heat + slip_power - strip_cooling - roll_cooling)
    return {'status': 'SYNTHETIC_UNCALIBRATED', 'strip_temperature_k': strip_next,
            'roll_temperature_k': roll_next, 'plastic_heat_volumetric_w_m3': plastic_heat / state.deforming_volume_m3,
            'solid_slip_heat_flux_w_m2': slip_flux, 'solid_slip_heat_power_w': slip_power,
            'contact_heat_to_strip_w': contact_to_strip, 'contact_heat_to_roll_w': -contact_to_strip,
            'strip_cooling_w': strip_cooling, 'roll_cooling_w': roll_cooling,
            'plastic_work_not_immediately_heat_w': state.plastic_power_w - plastic_heat,
            'explicit_mode_step_ratio':state.duration_s*lambda_max,
            'strip_thermal_capacity_j_k':strip_capacity, 'roll_thermal_capacity_j_k':roll_capacity,
            'energy_residual_j': energy_change - expected}
