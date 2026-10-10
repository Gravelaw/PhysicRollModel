"""Restricted torque-driven, inextensible moving-web/reel benchmark.

The common transport speed is predicted from torque and variable inertia.
Tension is an inextensibility constraint reaction, not a material law. There
is no evolving strain, slack/reversal, winding loss, bite, or roll contact.
"""

from dataclasses import dataclass
import math


MODEL_ID = 'T2A4_INEXTENSIBLE_TORQUE_DRIVEN_REELS_V1'
LINE_MASS_KG_M = 0.1
THICKNESS_M = 0.001
KAPPA_M = THICKNESS_M / math.pi
CORE_RADIUS_M = 0.1
CORE_INERTIA_KG_M2 = 0.01
SPAN_LENGTH_M = 1.0
LEFT_INITIAL_LENGTH_M = 10.0
RIGHT_INITIAL_LENGTH_M = 1.0
INITIAL_SPEED_M_S = 0.1
TRANSFER_TARGET_M = 0.2
TORQUE_TENSION_SCALE_N = 1.0
SPAN_MASS_KG = LINE_MASS_KG_M * SPAN_LENGTH_M


@dataclass(frozen=True)
class T2A4Case:
    maximum_step_s: float

    def __post_init__(self):
        step = self.maximum_step_s
        try:
            valid = (type(step) in (int, float) and math.isfinite(step) and
                     0 < step <= 0.04 and math.isfinite(2.1 / step) and
                     2.1 / step <= 2000)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('T2A4 step exceeds the frozen positive sampling budget')


def _reel(reference_length, direction, transfer_m, speed_m_s):
    length = reference_length + direction * transfer_m
    radius_sq = CORE_RADIUS_M ** 2 + KAPPA_M * length
    radius = math.sqrt(radius_sq)
    initial_radius = math.sqrt(CORE_RADIUS_M ** 2 + KAPPA_M * reference_length)
    inertia = CORE_INERTIA_KG_M2 + LINE_MASS_KG_M * (
        CORE_RADIUS_M ** 2 * length + KAPPA_M * length ** 2 / 2)
    return {
        'reference_length_m': length,
        'wound_mass_kg': LINE_MASS_KG_M * length,
        'radius_m': radius,
        'inertia_kg_m2': inertia,
        'angle_rad': 2 * transfer_m / (radius + initial_radius),
        'speed_rad_s': speed_m_s / radius,
        'signed_mass_flux_kg_s': direction * LINE_MASS_KG_M * speed_m_s,
        'radius_rate_m_s': direction * KAPPA_M * speed_m_s / (2 * radius),
    }


def _state(time_s, transfer_m, speed_m_s):
    if (not all(math.isfinite(value) for value in
                (time_s, transfer_m, speed_m_s)) or time_s < 0 or
            transfer_m < 0 or transfer_m >= LEFT_INITIAL_LENGTH_M or
            speed_m_s <= 0):
        raise ValueError('T2A4 state left positive-flow inventory domain')
    left = _reel(LEFT_INITIAL_LENGTH_M, -1, transfer_m, speed_m_s)
    right = _reel(RIGHT_INITIAL_LENGTH_M, 1, transfer_m, speed_m_s)
    reels = {'left': left, 'right': right}
    effective_mass = SPAN_MASS_KG
    mass_derivative = 0.0
    for side, direction in (('left', -1), ('right', 1)):
        reel = reels[side]
        radius = reel['radius_m']
        inertia = reel['inertia_kg_m2']
        effective_mass += inertia / radius ** 2
        mass_derivative += direction * (
            LINE_MASS_KG_M - KAPPA_M * inertia / radius ** 4)
    acceleration = -mass_derivative * speed_m_s ** 2 / (2 * effective_mass)
    for side, direction in (('left', -1), ('right', 1)):
        reel = reels[side]
        radius = reel['radius_m']
        inertia = reel['inertia_kg_m2']
        angular_acceleration = (acceleration / radius -
                                speed_m_s * reel['radius_rate_m_s'] / radius ** 2)
        drive_torque = direction * TORQUE_TENSION_SCALE_N * radius
        tension_torque_sign = -direction
        if side == 'left':
            tension = (inertia * angular_acceleration - drive_torque) / radius
        else:
            tension = (drive_torque - inertia * angular_acceleration) / radius
        reel.update({
            'acceleration_rad_s2': angular_acceleration,
            'applied_drive_torque_nm': drive_torque,
            'constraint_tension_n': tension,
            'tension_torque_nm': tension_torque_sign * radius * tension,
            'angular_momentum_kg_m2_s': inertia * reel['speed_rad_s'],
            'kinetic_energy_j': 0.5 * inertia * reel['speed_rad_s'] ** 2,
        })
    kinetic_energy = (0.5 * SPAN_MASS_KG * speed_m_s ** 2 +
                      left['kinetic_energy_j'] + right['kinetic_energy_j'])
    state = {
        'time_s': time_s,
        'transferred_reference_length_m': transfer_m,
        'strip_speed_m_s': speed_m_s,
        'strip_acceleration_m_s2': acceleration,
        'span_mass_kg': SPAN_MASS_KG,
        'span_momentum_kg_m_s': SPAN_MASS_KG * speed_m_s,
        'span_kinetic_energy_j': 0.5 * SPAN_MASS_KG * speed_m_s ** 2,
        'effective_mass_kg': effective_mass,
        'effective_mass_derivative_kg_m': mass_derivative,
        'total_mass_kg': (SPAN_MASS_KG + left['wound_mass_kg'] +
                          right['wound_mass_kg']),
        'total_kinetic_energy_j': kinetic_energy,
        'reels': reels,
    }
    values = (time_s, transfer_m, speed_m_s, acceleration, effective_mass,
              mass_derivative, kinetic_energy, *(
                  value for reel in reels.values() for value in reel.values()))
    if not all(math.isfinite(value) for value in values):
        raise ValueError('T2A4 state exceeded the finite numerical domain')
    if min(left['constraint_tension_n'], right['constraint_tension_n']) <= 0:
        raise ValueError('T2A4 lost positive inextensibility tension')
    return state


def _derivative(transfer_m, speed_m_s):
    state = _state(0.0, transfer_m, speed_m_s)
    return speed_m_s, state['strip_acceleration_m_s2']


def _rk4_step(transfer_m, speed_m_s, h):
    q1, v1 = _derivative(transfer_m, speed_m_s)
    q2, v2 = _derivative(transfer_m + h * q1 / 2,
                         speed_m_s + h * v1 / 2)
    q3, v3 = _derivative(transfer_m + h * q2 / 2,
                         speed_m_s + h * v2 / 2)
    q4, v4 = _derivative(transfer_m + h * q3,
                         speed_m_s + h * v3)
    return (transfer_m + h * (q1 + 2 * q2 + 2 * q3 + q4) / 6,
            speed_m_s + h * (v1 + 2 * v2 + 2 * v3 + v4) / 6)


def _simpson(start, middle, end, h):
    return h * (start + 4 * middle + end) / 6


def _reel_rates(state, side):
    reel = state['reels'][side]
    speed = state['strip_speed_m_s']
    flux = reel['signed_mass_flux_kg_s']
    angular = (reel['applied_drive_torque_nm'] + reel['tension_torque_nm'] +
               flux * reel['radius_m'] * speed)
    energy = ((reel['applied_drive_torque_nm'] + reel['tension_torque_nm']) *
              reel['speed_rad_s'] + flux * speed ** 2 / 2)
    return angular, energy


def _update_defects(start, middle, end, h, max_defects):
    for side in ('left', 'right'):
        a, b = start['reels'][side], end['reels'][side]
        ra, rm, rb = (_reel_rates(state, side) for state in (start, middle, end))
        max_defects['reel_angular_impulse_nm_s'][side] = max(
            max_defects['reel_angular_impulse_nm_s'][side],
            abs(b['angular_momentum_kg_m2_s'] - a['angular_momentum_kg_m2_s'] -
                _simpson(ra[0], rm[0], rb[0], h)))
        max_defects['reel_energy_j'][side] = max(
            max_defects['reel_energy_j'][side],
            abs(b['kinetic_energy_j'] - a['kinetic_energy_j'] -
                _simpson(ra[1], rm[1], rb[1], h)))
        max_defects['reel_mass_kg'][side] = max(
            max_defects['reel_mass_kg'][side],
            abs(b['wound_mass_kg'] - a['wound_mass_kg'] -
                _simpson(a['signed_mass_flux_kg_s'],
                         middle['reels'][side]['signed_mass_flux_kg_s'],
                         b['signed_mass_flux_kg_s'], h)))
    span_force = lambda state: (state['reels']['right']['constraint_tension_n'] -
                                state['reels']['left']['constraint_tension_n'])
    span_momentum_work = _simpson(span_force(start), span_force(middle),
                                  span_force(end), h)
    span_energy_work = _simpson(
        span_force(start) * start['strip_speed_m_s'],
        span_force(middle) * middle['strip_speed_m_s'],
        span_force(end) * end['strip_speed_m_s'], h)
    max_defects['span_momentum_n_s'] = max(
        max_defects['span_momentum_n_s'],
        abs(end['span_momentum_kg_m_s'] - start['span_momentum_kg_m_s'] -
            span_momentum_work))
    max_defects['span_energy_j'] = max(
        max_defects['span_energy_j'],
        abs(end['span_kinetic_energy_j'] - start['span_kinetic_energy_j'] -
            span_energy_work))


def run_torque_driven_reels(case: T2A4Case):
    """Integrate the frozen ODE; use the energy oracle only for diagnostics."""
    if not isinstance(case, T2A4Case):
        raise ValueError('T2A4 requires a T2A4Case')
    states = [_state(0.0, 0.0, INITIAL_SPEED_M_S)]
    initial_mass = states[0]['effective_mass_kg']
    initial_energy = states[0]['total_kinetic_energy_j']
    max_defects = {
        'reel_angular_impulse_nm_s': {'left': 0.0, 'right': 0.0},
        'reel_energy_j': {'left': 0.0, 'right': 0.0},
        'reel_mass_kg': {'left': 0.0, 'right': 0.0},
        'span_momentum_n_s': 0.0,
        'span_energy_j': 0.0,
    }
    max_energy = 0.0
    max_speed_oracle_error = 0.0
    while states[-1]['transferred_reference_length_m'] < TRANSFER_TARGET_M - 1e-14:
        if len(states) > 2000 or states[-1]['time_s'] > 2.1:
            raise ValueError('T2A4 failed the bounded episode budget')
        start = states[-1]
        q0, v0, t0 = (start['transferred_reference_length_m'],
                      start['strip_speed_m_s'], start['time_s'])
        h = case.maximum_step_s
        trial_q, trial_v = _rk4_step(q0, v0, h)
        if trial_q >= TRANSFER_TARGET_M:
            low, high = 0.0, h
            for _ in range(64):
                middle_h = (low + high) / 2
                middle_q, _ = _rk4_step(q0, v0, middle_h)
                if middle_q < TRANSFER_TARGET_M:
                    low = middle_h
                else:
                    high = middle_h
            h = (low + high) / 2
            trial_q, trial_v = _rk4_step(q0, v0, h)
            if abs(trial_q - TRANSFER_TARGET_M) > 1e-12:
                raise ValueError('T2A4 terminal transfer could not be localized')
        middle_q, middle_v = _rk4_step(q0, v0, h / 2)
        middle = _state(t0 + h / 2, middle_q, middle_v)
        end = _state(t0 + h, trial_q, trial_v)
        _update_defects(start, middle, end, h, max_defects)
        max_energy = max(max_energy,
                         abs(end['total_kinetic_energy_j'] - initial_energy))
        oracle_speed = INITIAL_SPEED_M_S * math.sqrt(
            initial_mass / end['effective_mass_kg'])
        max_speed_oracle_error = max(max_speed_oracle_error,
                                     abs(end['strip_speed_m_s'] - oracle_speed))
        states.append(end)
    final = states[-1]
    return {
        'model_id': MODEL_ID,
        'mode': 'torque_driven_inextensible_moving_web',
        'shaft_speed_role': 'predicted_from_applied_torque',
        'span_tension_role': 'inextensibility_constraint_reaction',
        'episode_outcome': 'COMPLETED_TRANSFER_TARGET',
        'requested_transfer_m': TRANSFER_TARGET_M,
        'completed_transfer_m': final['transferred_reference_length_m'],
        'completed_duration_s': final['time_s'],
        'states': states,
        'maximum_speed_oracle_error_m_s': max_speed_oracle_error,
        'maximum_scaled_total_energy_defect': max_energy / initial_energy,
        'maximum_balance_defects': max_defects,
        'limitations': ['inextensible fixed spatial span and ideal no-slip transfer',
                        'no evolving strain, slack, reversal, capacity or losses',
                        'no bite, plasticity, roll compliance or contact'],
    }
