"""Append-only reaction-reel ledger for a prescribed elastic-wave port.

The outgoing right-port stretch and speed come from the T2A5 analytic
boundary case. They are not predicted by this reel, which computes the
drive torque required to follow them. This is a winding ownership benchmark,
not general elastic reel/span coupling or release/reversal physics.
"""

from dataclasses import dataclass
import math


MODEL_ID = 'T2A6_APPEND_ONLY_ELASTIC_REACTION_REEL_V1'
LINE_MASS_KG_M = 0.1
EA_N = 10.0
C0_M_S = 10.0
LAMBDA0 = 1.001
V0_M_S = 0.1
DELTA = 1e-4
K_RAD_M = 5 * math.pi
B_M_S = V0_M_S + C0_M_S * LAMBDA0
CORE_RADIUS_M = 0.1
REFERENCE_THICKNESS_M = 0.001
KAPPA_M = REFERENCE_THICKNESS_M / math.pi
CORE_INERTIA_KG_M2 = 0.01
INITIAL_LENGTH_M = 1.0
DURATION_S = 0.08
SAMPLE_TIMES_S = (0.0, 0.005, 0.02, 0.04, DURATION_S)


@dataclass(frozen=True)
class T2A6Case:
    step_s: float
    transfer_mode: str = 'append_only_reaction'

    def __post_init__(self):
        if type(self.step_s) not in (int, float) or self.step_s not in (
                0.0005, 0.00025, 0.000125):
            raise ValueError('T2A6 step must use a frozen positive time grid')
        if self.transfer_mode != 'append_only_reaction':
            raise ValueError('T2A6 does not support release, reversal or torque-driven transfer')


def _phase_at(time_s):
    """Monotone right-port material phase, evaluated by Newton iteration."""
    phase = K_RAD_M * (1 - V0_M_S * time_s) / LAMBDA0 - K_RAD_M * C0_M_S * time_s
    for _ in range(8):
        residual = ((LAMBDA0 * phase + DELTA * math.sin(phase)) /
                    K_RAD_M + B_M_S * time_s - 1)
        phase -= residual * K_RAD_M / (LAMBDA0 + DELTA * math.cos(phase))
    return phase


def _port(time_s):
    phase = _phase_at(time_s)
    stretch = LAMBDA0 + DELTA * math.cos(phase)
    velocity = V0_M_S - C0_M_S * DELTA * math.cos(phase)
    reference_flux = velocity / stretch
    tension = EA_N * (stretch - 1)
    velocity_rate = -C0_M_S * DELTA * K_RAD_M * B_M_S * math.sin(phase) / stretch
    label = phase / K_RAD_M + C0_M_S * time_s
    values = (phase, stretch, velocity, reference_flux, tension, velocity_rate, label)
    if not all(math.isfinite(value) for value in values) or min(
            stretch - 1, velocity, reference_flux, tension) <= 0:
        raise ValueError('T2A6 port left positive taut append-only domain')
    return {
        'time_s': time_s,
        'phase_rad': phase,
        'stretch': stretch,
        'speed_m_s': velocity,
        'reference_flux_m_s': reference_flux,
        'tension_n': tension,
        'speed_rate_m_s2': velocity_rate,
        'material_label_m': label,
        'stored_energy_per_reference_m_j_m': EA_N * (stretch - 1) ** 2 / 2,
    }


def _reel(port, length_m):
    if not math.isfinite(length_m) or length_m <= 0:
        raise ValueError('T2A6 left positive wound inventory domain')
    radius = math.sqrt(CORE_RADIUS_M ** 2 + KAPPA_M * length_m)
    inertia = CORE_INERTIA_KG_M2 + LINE_MASS_KG_M * (
        CORE_RADIUS_M ** 2 * length_m + KAPPA_M * length_m ** 2 / 2)
    velocity = port['speed_m_s']
    flux = port['reference_flux_m_s']
    radius_rate = KAPPA_M * flux / (2 * radius)
    omega = velocity / radius
    alpha = port['speed_rate_m_s2'] / radius - velocity * radius_rate / radius ** 2
    reaction_torque = inertia * alpha + radius * port['tension_n']
    kinetic = inertia * omega ** 2 / 2
    state = {
        **port,
        'reference_length_m': length_m,
        'wound_mass_kg': LINE_MASS_KG_M * length_m,
        'radius_m': radius,
        'radius_rate_m_s': radius_rate,
        'inertia_kg_m2': inertia,
        'speed_rad_s': omega,
        'acceleration_rad_s2': alpha,
        'reaction_drive_torque_nm': reaction_torque,
        'tension_torque_nm': -radius * port['tension_n'],
        'signed_mass_flux_kg_s': LINE_MASS_KG_M * flux,
        'angular_momentum_kg_m2_s': inertia * omega,
        'kinetic_energy_j': kinetic,
    }
    if not all(math.isfinite(value) for value in state.values()):
        raise ValueError('T2A6 reel state exceeded finite domain')
    return state


def _rates(state):
    torque = state['reaction_drive_torque_nm']
    tension = state['tension_n']
    radius = state['radius_m']
    speed = state['speed_m_s']
    omega = state['speed_rad_s']
    q = state['reference_flux_m_s']
    angular = torque - radius * tension + LINE_MASS_KG_M * q * radius * speed
    drive_work = torque * omega
    traction_work = tension * speed
    kinetic_flux = q * LINE_MASS_KG_M * speed ** 2 / 2
    strain_flux = q * state['stored_energy_per_reference_m_j_m']
    return (q, omega, angular, drive_work, traction_work, kinetic_flux, strain_flux)


def _simpson(start, middle, end, step_s):
    return tuple(step_s * (start[i] + 4 * middle[i] + end[i]) / 6
                 for i in range(len(start)))


def _interval(start, end):
    """Immutable layer storing linear stretch in reference material label."""
    label_low = end['material_label_m']
    label_high = start['material_label_m']
    delta_label = label_high - label_low
    if delta_label <= 0:
        raise ValueError('T2A6 cannot append a nonpositive material interval')
    low_stretch, high_stretch = end['stretch'], start['stretch']
    low_e, high_e = low_stretch - 1, high_stretch - 1
    stored = EA_N * delta_label * (
        low_e ** 2 + low_e * high_e + high_e ** 2) / 6
    return {
        'material_label_low_m': label_low,
        'material_label_high_m': label_high,
        'reference_length_m': delta_label,
        'mass_kg': LINE_MASS_KG_M * delta_label,
        'stretch_at_low_label': low_stretch,
        'stretch_at_high_label': high_stretch,
        'retained_strain_energy_j': stored,
    }


def _snapshot(time_s, state, intervals, initial_strain_energy, deposited_energy,
              angle, integrals, max_angular, max_energy, max_storage,
              max_interval_angular, max_interval_energy):
    return {
        'time_s': time_s,
        'reel': dict(state),
        'angle_rad': angle,
        'initial_wound_strain_energy_j': initial_strain_energy,
        'deposited_strain_energy_j': deposited_energy,
        'total_wound_strain_energy_j': initial_strain_energy + deposited_energy,
        'total_reel_mechanical_energy_j': (state['kinetic_energy_j'] +
                                           initial_strain_energy + deposited_energy),
        'ordered_wound_intervals': [dict(interval) for interval in intervals],
        'interval_vs_reel_inventory_difference_m': (
            sum(interval['reference_length_m'] for interval in intervals) -
            state['reference_length_m']),
        'integrated_reference_flux_m': integrals[0],
        'integrated_angular_impulse_nm_s': integrals[2],
        'integrated_reaction_drive_work_j': integrals[3],
        'integrated_tension_work_j': integrals[4],
        'integrated_advected_kinetic_energy_j': integrals[5],
        'integrated_advected_strain_energy_j': integrals[6],
        'maximum_angular_impulse_defect_nm_s': max_angular,
        'maximum_energy_defect_j': max_energy,
        'maximum_storage_vs_flux_defect_j': max_storage,
        'maximum_interval_angular_impulse_defect_nm_s': max_interval_angular,
        'maximum_interval_energy_defect_j': max_interval_energy,
    }


def run_append_only_reaction_reel(case: T2A6Case):
    """Integrate append-only inventory and open-system winding ledgers."""
    if not isinstance(case, T2A6Case):
        raise ValueError('T2A6 requires a T2A6Case')
    initial_port = _port(0.0)
    initial_state = _reel(initial_port, INITIAL_LENGTH_M)
    initial_label = initial_port['material_label_m']
    initial_energy = INITIAL_LENGTH_M * initial_port['stored_energy_per_reference_m_j_m']
    intervals = [{
        'material_label_low_m': initial_label,
        'material_label_high_m': initial_label + INITIAL_LENGTH_M,
        'reference_length_m': INITIAL_LENGTH_M,
        'mass_kg': LINE_MASS_KG_M * INITIAL_LENGTH_M,
        'stretch_at_low_label': initial_port['stretch'],
        'stretch_at_high_label': initial_port['stretch'],
        'retained_strain_energy_j': initial_energy,
    }]
    integrals = [0.0] * 7
    deposited_energy = 0.0
    angle = 0.0
    max_angular = max_energy = max_storage = 0.0
    max_interval_angular = max_interval_energy = 0.0
    state = initial_state
    time_s = 0.0
    snapshots = [_snapshot(time_s, state, intervals, initial_energy,
                           deposited_energy, angle, integrals,
                           max_angular, max_energy, max_storage,
                           max_interval_angular, max_interval_energy)]
    steps = 0
    for observation in SAMPLE_TIMES_S[1:]:
        while time_s < observation - 1e-14:
            if steps >= 640:
                raise ValueError('T2A6 exceeded frozen append budget')
            h = min(case.step_s, observation - time_s)
            port_mid = _port(time_s + h / 2)
            port_end = _port(time_s + h)
            port_quarter = _port(time_s + h / 4)
            start_q = state['reference_flux_m_s']
            mid_q = port_mid['reference_flux_m_s']
            end_q = port_end['reference_flux_m_s']
            half_transfer = h / 12 * (start_q + 4 * port_quarter['reference_flux_m_s'] + mid_q)
            full_transfer = h / 6 * (start_q + 4 * mid_q + end_q)
            middle = _reel(port_mid, state['reference_length_m'] + half_transfer)
            next_state = _reel(port_end, state['reference_length_m'] + full_transfer)
            increment = _simpson(_rates(state), _rates(middle),
                                 _rates(next_state), h)
            for index, value in enumerate(increment):
                integrals[index] += value
            angle += increment[1]
            interval = _interval(state, next_state)
            if not math.isclose(interval['material_label_high_m'],
                                intervals[-1]['material_label_low_m'],
                                rel_tol=0, abs_tol=1e-12):
                raise ValueError('T2A6 material intervals lost adjacency')
            intervals.append(interval)
            deposited_energy += interval['retained_strain_energy_j']
            interval_angular_defect = (next_state['angular_momentum_kg_m2_s'] -
                                       state['angular_momentum_kg_m2_s'] - increment[2])
            interval_energy_defect = (
                next_state['kinetic_energy_j'] - state['kinetic_energy_j'] +
                interval['retained_strain_energy_j'] -
                (increment[3] - increment[4] + increment[5] + increment[6]))
            max_interval_angular = max(max_interval_angular,
                                       abs(interval_angular_defect))
            max_interval_energy = max(max_interval_energy,
                                      abs(interval_energy_defect))
            angular_defect = (next_state['angular_momentum_kg_m2_s'] -
                              initial_state['angular_momentum_kg_m2_s'] - integrals[2])
            energy_defect = (next_state['kinetic_energy_j'] + initial_energy +
                             deposited_energy - initial_state['kinetic_energy_j'] -
                             initial_energy - (integrals[3] - integrals[4] +
                                               integrals[5] + integrals[6]))
            max_angular = max(max_angular, abs(angular_defect))
            max_energy = max(max_energy, abs(energy_defect))
            max_storage = max(max_storage, abs(deposited_energy - integrals[6]))
            state = next_state
            time_s += h
            steps += 1
        time_s = observation
        snapshots.append(_snapshot(time_s, state, intervals, initial_energy,
                                   deposited_energy, angle, integrals,
                                   max_angular, max_energy, max_storage,
                                   max_interval_angular, max_interval_energy))
    return {
        'model_id': MODEL_ID,
        'mode': 'append_only_elastic_port_reaction_reel',
        'span_port_role': 'prescribed_characteristic_compatible_exact_wave',
        'shaft_speed_role': 'derived_from_port_speed',
        'shaft_torque_role': 'reaction_not_applied_input',
        'episode_outcome': 'COMPLETED_APPEND_ONLY_EPISODE',
        'step_s': case.step_s,
        'accepted_steps': steps,
        'snapshots': snapshots,
        'maximum_angular_impulse_defect_nm_s': max_angular,
        'maximum_energy_defect_j': max_energy,
        'maximum_storage_vs_flux_defect_j': max_storage,
        'maximum_interval_angular_impulse_defect_nm_s': max_interval_angular,
        'maximum_interval_energy_defect_j': max_interval_energy,
        'limitations': ['analytic prescribed outgoing span wave and incoming characteristic',
                        'ideal no-slip strain-matched append-only transfer',
                        'no torque-driven speed prediction, release, reversal or slack',
                        'no bending, compaction, radial deformation, wrap-path change or contact'],
    }
