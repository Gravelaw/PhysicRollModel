"""Restricted undamped fixed-radius shaft and massless elastic-span benchmark.

No moving material, changing inventory, roll bite or contact is represented.
This standalone benchmark does not complete the T2 running-web solver.
"""

from dataclasses import dataclass
import math


MODEL_ID = 'T2A1_FIXED_SHAFT_MASSLESS_SPAN_V1'


def _finite(value, name, *, positive=False, nonnegative=False):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or positive and value <= 0 or nonnegative and value < 0:
        raise ValueError(f'{name} must be a finite permitted number')


@dataclass(frozen=True)
class T2A1Case:
    duration_s: float
    step_s: float
    left_radius_m: float
    right_radius_m: float
    left_inertia_kg_m2: float
    right_inertia_kg_m2: float
    span_stiffness_n_m: float
    initial_extension_m: float
    left_initial_angle_rad: float = 0.0
    right_initial_angle_rad: float = 0.0
    left_initial_speed_rad_s: float = 0.0
    right_initial_speed_rad_s: float = 0.0
    left_constant_torque_nm: float = 0.0
    right_constant_torque_nm: float = 0.0

    def __post_init__(self):
        for name in ('duration_s', 'step_s', 'left_radius_m', 'right_radius_m',
                     'left_inertia_kg_m2', 'right_inertia_kg_m2',
                     'span_stiffness_n_m', 'initial_extension_m'):
            _finite(getattr(self, name), name, positive=True)
        for name in ('left_initial_angle_rad', 'right_initial_angle_rad',
                     'left_initial_speed_rad_s', 'right_initial_speed_rad_s',
                     'left_constant_torque_nm', 'right_constant_torque_nm'):
            _finite(getattr(self, name), name)
        frequency = math.sqrt(self.span_stiffness_n_m * (
            self.left_radius_m ** 2 / self.left_inertia_kg_m2 +
            self.right_radius_m ** 2 / self.right_inertia_kg_m2))
        if frequency == 0 or not math.isfinite(frequency) or self.step_s * frequency > 0.2:
            raise ValueError('T2A1 step is too large to resolve the elastic mode/events')
        if math.ceil(self.duration_s / self.step_s) > 2000:
            raise ValueError('T2A1 episode exceeds 2000 steps')
        if (self.initial_extension_m +
                self.right_radius_m * self.right_initial_angle_rad -
                self.left_radius_m * self.left_initial_angle_rad <= 0):
            raise ValueError('T2A1 must start with positive span tension')


def run_uncoupled_shaft(*, inertia_kg_m2, constant_torque_nm, duration_s,
                        step_s, initial_angle_rad=0.0, initial_speed_rad_s=0.0):
    """Midpoint shaft verification case with an exact constant-torque oracle."""
    for name, value in (('inertia_kg_m2', inertia_kg_m2), ('duration_s', duration_s),
                        ('step_s', step_s)):
        _finite(value, name, positive=True)
    for name, value in (('constant_torque_nm', constant_torque_nm),
                        ('initial_angle_rad', initial_angle_rad),
                        ('initial_speed_rad_s', initial_speed_rad_s)):
        _finite(value, name)
    if math.ceil(duration_s / step_s) > 2000:
        raise ValueError('shaft benchmark exceeds 2000 steps')
    states = [{'time_s': 0.0, 'angle_rad': initial_angle_rad,
               'speed_rad_s': initial_speed_rad_s,
               'kinetic_energy_j': 0.5 * inertia_kg_m2 * initial_speed_rad_s ** 2}]
    work = 0.0
    while states[-1]['time_s'] < duration_s - 1e-12:
        previous = states[-1]
        h = min(step_s, duration_s - previous['time_s'])
        speed = previous['speed_rad_s'] + h * constant_torque_nm / inertia_kg_m2
        angle = previous['angle_rad'] + h * (previous['speed_rad_s'] + speed) / 2
        work += h * constant_torque_nm * (previous['speed_rad_s'] + speed) / 2
        states.append({'time_s': previous['time_s'] + h, 'angle_rad': angle,
                       'speed_rad_s': speed,
                       'kinetic_energy_j': 0.5 * inertia_kg_m2 * speed ** 2})
    defect = max(abs(state['kinetic_energy_j'] - states[0]['kinetic_energy_j'] -
                     constant_torque_nm * (state['angle_rad'] - initial_angle_rad))
                 for state in states)
    return {'mode': 'uncoupled_constant_torque_reference', 'states': states,
            'applied_work_j': work, 'maximum_energy_work_defect_j': defect}


def _state(case, time_s, theta1, theta2, omega1, omega2):
    extension = (case.initial_extension_m + case.right_radius_m * theta2 -
                 case.left_radius_m * theta1)
    tension = case.span_stiffness_n_m * extension
    energy = (0.5 * case.left_inertia_kg_m2 * omega1 ** 2 +
              0.5 * case.right_inertia_kg_m2 * omega2 ** 2 +
              0.5 * case.span_stiffness_n_m * extension ** 2)
    if not all(math.isfinite(value) for value in
               (extension, tension, energy, theta1, theta2, omega1, omega2)):
        raise ValueError('T2A1 state exceeded the finite numerical domain')
    return {'time_s': time_s, 'left_angle_rad': theta1, 'right_angle_rad': theta2,
            'left_speed_rad_s': omega1, 'right_speed_rad_s': omega2,
            'span_extension_m': extension, 'span_tension_n': tension,
            'mechanical_energy_j': energy}


def _midpoint_step(case, state, h):
    r1, r2 = case.left_radius_m, case.right_radius_m
    j1, j2 = case.left_inertia_kg_m2, case.right_inertia_kg_m2
    k = case.span_stiffness_n_m
    w1, w2 = state['left_speed_rad_s'], state['right_speed_rad_s']
    u0 = r2 * w2 - r1 * w1
    g = r2 * case.right_constant_torque_nm / j2 - r1 * case.left_constant_torque_nm / j1
    d = r1 * r1 / j1 + r2 * r2 / j2
    midpoint_tension = k * (state['span_extension_m'] + h * u0 / 2 +
                            h * h * g / 4) / (1 + k * h * h * d / 4)
    w1_next = w1 + h * (case.left_constant_torque_nm + r1 * midpoint_tension) / j1
    w2_next = w2 + h * (case.right_constant_torque_nm - r2 * midpoint_tension) / j2
    theta1_next = state['left_angle_rad'] + h * (w1 + w1_next) / 2
    theta2_next = state['right_angle_rad'] + h * (w2 + w2_next) / 2
    next_state = _state(case, state['time_s'] + h, theta1_next, theta2_next,
                        w1_next, w2_next)
    midpoint_power = (case.left_constant_torque_nm * (w1 + w1_next) / 2 +
                      case.right_constant_torque_nm * (w2 + w2_next) / 2)
    return next_state, h * midpoint_power


def _exact_relative(case, state, h):
    """Independent constant-load solution for extension and its derivatives."""
    r1, r2 = case.left_radius_m, case.right_radius_m
    j1, j2 = case.left_inertia_kg_m2, case.right_inertia_kg_m2
    k = case.span_stiffness_n_m
    d = r1 * r1 / j1 + r2 * r2 / j2
    frequency = math.sqrt(k * d)
    g = r2 * case.right_constant_torque_nm / j2 - r1 * case.left_constant_torque_nm / j1
    equilibrium = g / (k * d)
    a = state['span_extension_m'] - equilibrium
    b = (r2 * state['right_speed_rad_s'] - r1 * state['left_speed_rad_s']) / frequency
    return frequency, equilibrium, a, b


def _first_zero_within(case, state, h):
    """Find the first exact loss, including an interior dip or tangent touch."""
    frequency, equilibrium, a, b = _exact_relative(case, state, h)

    def extension(offset):
        angle = frequency * offset
        return equilibrium + a * math.cos(angle) + b * math.sin(angle)

    def derivative(offset):
        angle = frequency * offset
        return frequency * (-a * math.sin(angle) + b * math.cos(angle))

    positions = [0.0]
    left_slope, right_slope = derivative(0.0), derivative(h)
    if left_slope * right_slope < 0:
        low, high = 0.0, h
        for _ in range(80):
            middle = (low + high) / 2
            if (derivative(middle) > 0) == (left_slope > 0):
                low = middle
            else:
                high = middle
        positions.append((low + high) / 2)
    positions.append(h)
    for index, (start, end) in enumerate(zip(positions[:-1], positions[1:])):
        value = extension(end)
        if (0 < value <= 1e-12 and index < len(positions) - 2 and
                left_slope < 0 < right_slope):
            if math.hypot(a, b) == equilibrium:
                return end  # Algebraic tangency; trig evaluation rounded above zero.
            raise ValueError('T2A1 near-zero interior minimum is unresolved')
        if value <= 0:
            low, high = start, end
            if value == 0:
                return end
            for _ in range(80):
                middle = (low + high) / 2
                if extension(middle) > 0:
                    low = middle
                else:
                    high = middle
            return (low + high) / 2
    return None


def _exact_step(case, state, h):
    """Advance only a terminal fractional interval to its analytic first hit."""
    frequency, equilibrium, a, b = _exact_relative(case, state, h)
    sine, cosine = math.sin(frequency * h), math.cos(frequency * h)
    integral_e = equilibrium * h + a * sine / frequency + b * (1 - cosine) / frequency
    double_integral_e = (equilibrium * h * h / 2 +
                         a * (1 - cosine) / frequency ** 2 +
                         b * (h / frequency - sine / frequency ** 2))
    r1, r2 = case.left_radius_m, case.right_radius_m
    j1, j2 = case.left_inertia_kg_m2, case.right_inertia_kg_m2
    k = case.span_stiffness_n_m
    w1, w2 = state['left_speed_rad_s'], state['right_speed_rad_s']
    t1, t2 = case.left_constant_torque_nm, case.right_constant_torque_nm
    theta1 = (state['left_angle_rad'] + w1 * h + t1 * h * h / (2 * j1) +
              r1 * k * double_integral_e / j1)
    theta2 = (state['right_angle_rad'] + w2 * h + t2 * h * h / (2 * j2) -
              r2 * k * double_integral_e / j2)
    next_state = _state(case, state['time_s'] + h, theta1, theta2,
                        w1 + (t1 * h + r1 * k * integral_e) / j1,
                        w2 + (t2 * h - r2 * k * integral_e) / j2)
    work = t1 * (theta1 - state['left_angle_rad']) + t2 * (theta2 - state['right_angle_rad'])
    return next_state, work


def run_torque_driven(case: T2A1Case):
    """Predict two shaft motions; stop at first loss of taut-span tension."""
    if not isinstance(case, T2A1Case):
        raise ValueError('T2A1 torque drive requires a T2A1Case')
    first = _state(case, 0.0, case.left_initial_angle_rad, case.right_initial_angle_rad,
                   case.left_initial_speed_rad_s, case.right_initial_speed_rad_s)
    states = [first]
    work = 0.0
    max_defect = 0.0
    event = None
    while states[-1]['time_s'] < case.duration_s - 1e-12:
        current = states[-1]
        h = min(case.step_s, case.duration_s - current['time_s'])
        hit = _first_zero_within(case, current, h)
        if hit is not None:
            candidate, increment = _exact_step(case, current, hit)
            if abs(candidate['span_tension_n']) > 1e-9:
                raise ValueError('T2A1 first-zero event could not be localized')
            event = {'event': 'first_loss_of_tension', 'time_s': candidate['time_s'],
                     'tension_residual_n': candidate['span_tension_n']}
            candidate['span_tension_n'] = 0.0
        else:
            candidate, increment = _midpoint_step(case, current, h)
            if candidate['span_tension_n'] <= 0:
                raise ValueError('T2A1 midpoint state conflicts with first-zero search')
        work += increment
        max_defect = max(max_defect, abs(candidate['mechanical_energy_j'] -
                                     first['mechanical_energy_j'] - work))
        states.append(candidate)
        if event is not None:
            break
    return {
        'model_id': MODEL_ID, 'mode': 'constant_torque_driven',
        'shaft_speed_role': 'predicted_from_applied_torque',
        'span_tension_role': 'dynamically_derived',
        'requested_duration_s': case.duration_s,
        'completed_duration_s': states[-1]['time_s'],
        'episode_outcome': 'TERMINATED_TENSION_LOSS' if event else 'COMPLETED_REQUESTED_DURATION',
        'states': states, 'events': [] if event is None else [event],
        'applied_work_j': work, 'maximum_energy_work_defect_j': max_defect,
        'limitations': ['fixed radius and inertia', 'undamped massless elastic span',
                        'no material flux, reel inventory, bite or contact'],
    }


def run_prescribed_reaction(case: T2A1Case, motion: str, *, amplitude_rad=0.01,
                            frequency_rad_s=2 * math.pi, extension_rate_m_s=0.02):
    """Calculate required torques for two reviewed analytic shaft histories."""
    if not isinstance(case, T2A1Case):
        raise ValueError('T2A1 reaction requires a T2A1Case')
    if any((case.left_initial_angle_rad, case.right_initial_angle_rad,
            case.left_initial_speed_rad_s, case.right_initial_speed_rad_s,
            case.left_constant_torque_nm, case.right_constant_torque_nm)):
        raise ValueError('prescribed reaction has no independent initial motion or applied torque')
    if motion == 'left_sine':
        _finite(amplitude_rad, 'amplitude_rad')
        _finite(frequency_rad_s, 'frequency_rad_s', positive=True)
        if case.initial_extension_m <= abs(case.left_radius_m * amplitude_rad):
            raise ValueError('sine motion may leave the taut-span domain')
        stop_time = case.duration_s
    elif motion == 'right_linear_loss':
        _finite(extension_rate_m_s, 'extension_rate_m_s', positive=True)
        first_zero_time = case.initial_extension_m / extension_rate_m_s
        stop_time = min(case.duration_s, first_zero_time)
    else:
        raise ValueError('unsupported T2A1 prescribed motion')

    def sample(time_s):
        if motion == 'left_sine':
            theta1 = amplitude_rad * math.sin(frequency_rad_s * time_s)
            omega1 = amplitude_rad * frequency_rad_s * math.cos(frequency_rad_s * time_s)
            alpha1 = -amplitude_rad * frequency_rad_s ** 2 * math.sin(frequency_rad_s * time_s)
            theta2 = omega2 = alpha2 = 0.0
        else:
            theta1 = omega1 = alpha1 = alpha2 = 0.0
            theta2 = -extension_rate_m_s * time_s / case.right_radius_m
            omega2 = -extension_rate_m_s / case.right_radius_m
        state = _state(case, time_s, theta1, theta2, omega1, omega2)
        tension = state['span_tension_n']
        state['left_reaction_torque_nm'] = case.left_inertia_kg_m2 * alpha1 - case.left_radius_m * tension
        state['right_reaction_torque_nm'] = case.right_inertia_kg_m2 * alpha2 + case.right_radius_m * tension
        return state

    times = [0.0]
    while times[-1] < stop_time - 1e-12:
        times.append(min(stop_time, times[-1] + case.step_s))
    states = [sample(time) for time in times]
    event = motion == 'right_linear_loss' and first_zero_time <= case.duration_s
    if event:
        if abs(states[-1]['span_tension_n']) > 1e-9:
            raise ValueError('T2A1 prescribed first-zero event could not be localized')
        states[-1]['span_tension_n'] = 0.0
    if any(state['span_tension_n'] < -1e-9 for state in states):
        raise ValueError('T2A1 prescribed trajectory entered compression')
    work = sum((right['time_s'] - left['time_s']) * (
        (mid['left_reaction_torque_nm'] * mid['left_speed_rad_s'] +
         mid['right_reaction_torque_nm'] * mid['right_speed_rad_s']))
        for left, right in zip(states[:-1], states[1:])
        for mid in (sample((left['time_s'] + right['time_s']) / 2),))
    return {'model_id': MODEL_ID, 'mode': motion,
            'shaft_speed_role': 'prescribed_input',
            'reaction_torque_role': 'required_to_follow_prescribed_motion',
            'requested_duration_s': case.duration_s,
            'completed_duration_s': stop_time,
            'episode_outcome': 'TERMINATED_TENSION_LOSS' if event else 'COMPLETED_REQUESTED_DURATION',
            'states': states,
            'events': [{'event': 'first_loss_of_tension', 'time_s': stop_time}] if event else [],
            'midpoint_reaction_work_j': work,
            'reaction_work_quadrature_defect_j': states[-1]['mechanical_energy_j'] -
            states[0]['mechanical_energy_j'] - work,
            'limitations': ['prescribed motion, not speed prediction',
                            'fixed radius/inertia and undamped massless span'],
            }
