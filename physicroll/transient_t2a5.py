"""Restricted distributed elastic moving-span verification benchmark.

An exact right-running wave supplies initial data and one incoming elastic
characteristic at each fixed spatial port. Finite volumes predict the
interior stretch and velocity. Reel dynamics and rolling contact are absent.
"""

from dataclasses import dataclass
import math


MODEL_ID = 'T2A5_DISTRIBUTED_MOVING_ELASTIC_SPAN_V1'
SPAN_LENGTH_M = 1.0
REFERENCE_LINE_MASS_KG_M = 0.1
EA_N = 10.0
REFERENCE_WAVE_SPEED_M_S = math.sqrt(EA_N / REFERENCE_LINE_MASS_KG_M)
BASE_STRETCH = 1.001
BASE_SPEED_M_S = 0.1
WAVE_NUMBER_RAD_M = 5 * math.pi
STRETCH_AMPLITUDE = 1e-4
END_TIME_S = 0.08
SAMPLE_TIMES_S = (0.0, 0.04, END_TIME_S)
CFL_LIMIT = 0.35
_GAUSS_NODES = (-0.8611363115940526, -0.3399810435848563,
                0.3399810435848563, 0.8611363115940526)
_GAUSS_WEIGHTS = (0.3478548451374538, 0.6521451548625461,
                  0.6521451548625461, 0.3478548451374538)


@dataclass(frozen=True)
class T2A5Case:
    cell_count: int
    variant: str = 'moving_wave'
    cfl_limit: float = CFL_LIMIT

    def __post_init__(self):
        if type(self.cell_count) is not int or self.cell_count not in (64, 128, 256):
            raise ValueError('T2A5 cell count must be one of the frozen grids')
        if self.variant not in ('moving_wave', 'stationary_wave', 'uniform_transport'):
            raise ValueError('T2A5 variant is outside the frozen synthetic cases')
        if type(self.cfl_limit) not in (int, float) or self.cfl_limit not in (
                CFL_LIMIT, CFL_LIMIT / 2, CFL_LIMIT / 4):
            raise ValueError('T2A5 CFL must be one of the frozen time grids')

    @property
    def base_speed_m_s(self):
        return 0.0 if self.variant == 'stationary_wave' else BASE_SPEED_M_S

    @property
    def stretch_amplitude(self):
        return 0.0 if self.variant == 'uniform_transport' else STRETCH_AMPLITUDE


def _material_position(reference_m, time_s, case):
    phase = WAVE_NUMBER_RAD_M * (reference_m - REFERENCE_WAVE_SPEED_M_S * time_s)
    return (BASE_STRETCH * reference_m + case.base_speed_m_s * time_s +
            case.stretch_amplitude / WAVE_NUMBER_RAD_M * math.sin(phase))


def _reference_at(position_m, time_s, case):
    """Invert the monotone reference wave solely for data and boundary input."""
    center = (position_m - case.base_speed_m_s * time_s) / BASE_STRETCH
    width = case.stretch_amplitude / WAVE_NUMBER_RAD_M / BASE_STRETCH + 1e-12
    low, high = center - width, center + width
    for _ in range(54):
        middle = (low + high) / 2
        if _material_position(middle, time_s, case) < position_m:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def _exact_primitive(position_m, time_s, case):
    reference = _reference_at(position_m, time_s, case)
    phase = WAVE_NUMBER_RAD_M * (reference - REFERENCE_WAVE_SPEED_M_S * time_s)
    perturbation = case.stretch_amplitude * math.cos(phase)
    return (BASE_STRETCH + perturbation,
            case.base_speed_m_s - REFERENCE_WAVE_SPEED_M_S * perturbation)


def _conserved(stretch, velocity):
    a = 1 / stretch
    return a, REFERENCE_LINE_MASS_KG_M * a * velocity


def _initial_cell(left_m, right_m, case):
    middle, half_width = (left_m + right_m) / 2, (right_m - left_m) / 2
    sums = [0.0, 0.0]
    for node, weight in zip(_GAUSS_NODES, _GAUSS_WEIGHTS):
        stretch, velocity = _exact_primitive(middle + node * half_width, 0.0, case)
        state = _conserved(stretch, velocity)
        sums[0] += weight * state[0] / 2
        sums[1] += weight * state[1] / 2
    return tuple(sums)


def _primitive(state):
    a, momentum = state
    if not all(math.isfinite(value) for value in state) or a <= 0:
        raise ValueError('T2A5 left positive finite stretch domain')
    stretch = 1 / a
    velocity = momentum / (REFERENCE_LINE_MASS_KG_M * a)
    if not math.isfinite(stretch) or not math.isfinite(velocity) or stretch <= 1:
        raise ValueError('T2A5 lost positive taut tension')
    return stretch, velocity


def _energy(state):
    stretch, velocity = _primitive(state)
    a = state[0]
    return (state[1] * velocity / 2 +
            a * EA_N * (stretch - 1) ** 2 / 2)


def _physical_flux(state):
    stretch, velocity = _primitive(state)
    a, momentum = state
    tension = EA_N * (stretch - 1)
    return a * velocity, momentum * velocity - tension, velocity * (_energy(state) - tension)


def _physical_port_terms(state):
    stretch, velocity = _primitive(state)
    reference_flux = state[0] * velocity
    return (reference_flux * REFERENCE_LINE_MASS_KG_M * velocity ** 2 / 2,
            reference_flux * EA_N * (stretch - 1) ** 2 / 2,
            EA_N * (stretch - 1) * velocity)


def _boundary_states(cells, time_s, case):
    left_out_stretch, left_out_speed = _primitive(cells[0])
    right_out_stretch, right_out_speed = _primitive(cells[-1])
    exact_left_stretch, exact_left_speed = _exact_primitive(0.0, time_s, case)
    incoming_right_running = exact_left_speed - REFERENCE_WAVE_SPEED_M_S * exact_left_stretch
    outgoing_left_running = left_out_speed + REFERENCE_WAVE_SPEED_M_S * left_out_stretch
    left_speed = (incoming_right_running + outgoing_left_running) / 2
    left_stretch = ((outgoing_left_running - incoming_right_running) /
                    (2 * REFERENCE_WAVE_SPEED_M_S))
    incoming_left_running = case.base_speed_m_s + REFERENCE_WAVE_SPEED_M_S * BASE_STRETCH
    outgoing_right_running = right_out_speed - REFERENCE_WAVE_SPEED_M_S * right_out_stretch
    right_speed = (incoming_left_running + outgoing_right_running) / 2
    right_stretch = ((incoming_left_running - outgoing_right_running) /
                     (2 * REFERENCE_WAVE_SPEED_M_S))
    return _conserved(left_stretch, left_speed), _conserved(right_stretch, right_speed)


def _minmod3(first, second, third):
    if first > 0 and second > 0 and third > 0:
        return min(first, second, third)
    if first < 0 and second < 0 and third < 0:
        return max(first, second, third)
    return 0.0


def _interface_flux(left, right):
    left_flux, right_flux = _physical_flux(left), _physical_flux(right)
    left_stretch, left_speed = _primitive(left)
    right_stretch, right_speed = _primitive(right)
    signal_speed = max(abs(left_speed) + left_stretch * REFERENCE_WAVE_SPEED_M_S,
                       abs(right_speed) + right_stretch * REFERENCE_WAVE_SPEED_M_S)
    energy_left, energy_right = _energy(left), _energy(right)
    flux = tuple((left_flux[i] + right_flux[i]) / 2 -
                 signal_speed * (right[i] - left[i]) / 2 for i in (0, 1)) + (
        (left_flux[2] + right_flux[2]) / 2 -
        signal_speed * (energy_right - energy_left) / 2,)
    return flux, signal_speed


def _fluxes(cells, time_s, case):
    left_ghost, right_ghost = _boundary_states(cells, time_s, case)
    extended = [left_ghost, *cells, right_ghost]
    slopes = [(0.0, 0.0)]
    for index in range(1, len(extended) - 1):
        previous, center, following = extended[index - 1:index + 2]
        slopes.append(tuple(_minmod3(2 * (center[j] - previous[j]),
                                      (following[j] - previous[j]) / 2,
                                      2 * (following[j] - center[j]))
                            for j in (0, 1)))
    slopes.append((0.0, 0.0))
    fluxes = []
    maximum_signal = 0.0
    for index in range(len(extended) - 1):
        left = tuple(extended[index][j] + slopes[index][j] / 2 for j in (0, 1))
        right = tuple(extended[index + 1][j] - slopes[index + 1][j] / 2
                      for j in (0, 1))
        flux, signal = _interface_flux(left, right)
        fluxes.append(flux)
        maximum_signal = max(maximum_signal, signal)
    return fluxes, maximum_signal


def _cfl_step(cells, time_s, dx, case):
    boundary = _boundary_states(cells, time_s, case)
    signal = max(abs(velocity) + stretch * REFERENCE_WAVE_SPEED_M_S
                 for stretch, velocity in map(_primitive, (*boundary, *cells)))
    return case.cfl_limit * dx / signal


def _advance(cells, time_s, step_s, dx, case):
    first_ports = _boundary_states(cells, time_s, case)
    first_fluxes, first_signal = _fluxes(cells, time_s, case)
    first = [tuple(value[j] - step_s / dx *
                   (first_fluxes[i + 1][j] - first_fluxes[i][j])
                   for j in (0, 1)) for i, value in enumerate(cells)]
    for value in first:
        _primitive(value)
    second_ports = _boundary_states(first, time_s + step_s, case)
    second_fluxes, second_signal = _fluxes(first, time_s + step_s, case)
    updated = [tuple((cells[i][j] + first[i][j] - step_s / dx *
                      (second_fluxes[i + 1][j] - second_fluxes[i][j])) / 2
                     for j in (0, 1)) for i in range(len(cells))]
    for value in updated:
        _primitive(value)
    left = tuple(step_s * (first_fluxes[0][i] + second_fluxes[0][i]) / 2
                 for i in (0, 1, 2))
    right = tuple(step_s * (first_fluxes[-1][i] + second_fluxes[-1][i]) / 2
                  for i in (0, 1, 2))
    physical_port_transfer = tuple(step_s * (
        first_ports[i][0] * _primitive(first_ports[i])[1] +
        second_ports[i][0] * _primitive(second_ports[i])[1]) / 2
        for i in (0, 1))
    physical_fluxes = [tuple(step_s * (
        _physical_flux(first_ports[side])[component] +
        _physical_flux(second_ports[side])[component]) / 2
        for component in (0, 1, 2)) for side in (0, 1)]
    physical_terms = [tuple(step_s * (
        _physical_port_terms(first_ports[side])[component] +
        _physical_port_terms(second_ports[side])[component]) / 2
        for component in (0, 1, 2)) for side in (0, 1)]
    return (updated, left, right, physical_port_transfer, physical_fluxes,
            physical_terms, step_s * max(first_signal, second_signal) / dx)


def _integrals(cells, dx):
    return (REFERENCE_LINE_MASS_KG_M * dx * sum(value[0] for value in cells),
            dx * sum(value[1] for value in cells),
            dx * sum(_energy(value) for value in cells))


def _snapshot(time_s, cells, dx, cuts, characteristic_cuts,
              integrated_left, integrated_right, physical_fluxes, physical_terms):
    mass, momentum, energy = _integrals(cells, dx)
    return {
        'time_s': time_s,
        'cell_conservative_fields': [list(value) for value in cells],
        'left_material_label_m': cuts[0],
        'right_material_label_m': cuts[1],
        'left_characteristic_port_label_m': characteristic_cuts[0],
        'right_characteristic_port_label_m': characteristic_cuts[1],
        'characteristic_port_inventory_difference_m': (
            characteristic_cuts[1] - characteristic_cuts[0] -
            dx * sum(value[0] for value in cells)),
        'span_reference_length_m': dx * sum(value[0] for value in cells),
        'span_mass_kg': mass,
        'span_momentum_kg_m_s': momentum,
        'span_mechanical_energy_j': energy,
        'integrated_left_numerical_flux': list(integrated_left),
        'integrated_right_numerical_flux': list(integrated_right),
        'integrated_left_physical_flux': list(physical_fluxes[0]),
        'integrated_right_physical_flux': list(physical_fluxes[1]),
        'integrated_left_physical_energy_terms': list(physical_terms[0]),
        'integrated_right_physical_energy_terms': list(physical_terms[1]),
    }


def run_moving_elastic_span(case: T2A5Case):
    """Solve the frozen wave case; exact data enter only initial/incoming ports."""
    if not isinstance(case, T2A5Case):
        raise ValueError('T2A5 requires a T2A5Case')
    dx = SPAN_LENGTH_M / case.cell_count
    cells = [_initial_cell(i * dx, (i + 1) * dx, case)
             for i in range(case.cell_count)]
    cuts = [_reference_at(0.0, 0.0, case),
            _reference_at(SPAN_LENGTH_M, 0.0, case)]
    characteristic_cuts = list(cuts)
    integrated_left, integrated_right = [0.0] * 3, [0.0] * 3
    physical_fluxes = [[0.0] * 3, [0.0] * 3]
    physical_terms = [[0.0] * 3, [0.0] * 3]
    snapshots = [_snapshot(0.0, cells, dx, cuts, characteristic_cuts,
                           integrated_left, integrated_right,
                           physical_fluxes, physical_terms)]
    time_s = 0.0
    step_count = 0
    maximum_mass_defect, maximum_momentum_defect = 0.0, 0.0
    maximum_courant = 0.0
    maximum_scaled_energy_defect = 0.0
    initial_energy = snapshots[0]['span_mechanical_energy_j']
    sample_times = ((0.0, 0.01, 0.04, END_TIME_S)
                    if case.variant == 'stationary_wave' else SAMPLE_TIMES_S)
    for sample_time in sample_times[1:]:
        while time_s < sample_time - 1e-14:
            if step_count >= 4000:
                raise ValueError('T2A5 exceeded the frozen accepted-step budget')
            step_s = min(sample_time - time_s, 0.99 * _cfl_step(cells, time_s, dx, case))
            before_mass, before_momentum, _ = _integrals(cells, dx)
            for _ in range(16):
                (updated, left, right, physical_transfer, port_fluxes,
                 port_terms, stage_courant) = _advance(cells, time_s, step_s, dx, case)
                if stage_courant <= case.cfl_limit * (1 + 1e-12):
                    break
                step_s /= 2
            else:
                raise ValueError('T2A5 failed the reconstructed-stage CFL gate')
            maximum_courant = max(maximum_courant, stage_courant)
            after_mass, after_momentum, after_energy = _integrals(updated, dx)
            maximum_mass_defect = max(maximum_mass_defect, abs(
                after_mass - before_mass + REFERENCE_LINE_MASS_KG_M * (right[0] - left[0])))
            maximum_momentum_defect = max(maximum_momentum_defect, abs(
                after_momentum - before_momentum + right[1] - left[1]))
            for index in range(3):
                integrated_left[index] += left[index]
                integrated_right[index] += right[index]
                for side in (0, 1):
                    physical_fluxes[side][index] += port_fluxes[side][index]
                    physical_terms[side][index] += port_terms[side][index]
            running_energy_defect = (after_energy - initial_energy +
                                     integrated_right[2] - integrated_left[2])
            maximum_scaled_energy_defect = max(
                maximum_scaled_energy_defect,
                abs(running_energy_defect) / initial_energy)
            cuts[0] -= left[0]
            cuts[1] -= right[0]
            characteristic_cuts[0] -= physical_transfer[0]
            characteristic_cuts[1] -= physical_transfer[1]
            cells = updated
            time_s += step_s
            step_count += 1
        time_s = sample_time
        snapshots.append(_snapshot(time_s, cells, dx, cuts, characteristic_cuts,
                                   integrated_left, integrated_right,
                                   physical_fluxes, physical_terms))
    final = snapshots[-1]
    energy_defect = (final['span_mechanical_energy_j'] - initial_energy +
                     final['integrated_right_numerical_flux'][2] -
                     final['integrated_left_numerical_flux'][2])
    return {
        'model_id': MODEL_ID,
        'mode': 'distributed_moving_elastic_span_with_characteristic_inputs',
        'shaft_motion_role': 'not_modeled',
        'span_field_role': 'predicted_from_elastic_conservation_law',
        'episode_outcome': 'COMPLETED_SYNTHETIC_WAVE',
        'cell_count': case.cell_count,
        'variant': case.variant,
        'accepted_steps': step_count,
        'cfl_limit': case.cfl_limit,
        'maximum_reconstructed_stage_courant': maximum_courant,
        'snapshots': snapshots,
        'maximum_mass_balance_defect_kg': maximum_mass_defect,
        'maximum_momentum_balance_defect_kg_m_s': maximum_momentum_defect,
        'mechanical_energy_defect_j': energy_defect,
        'scaled_mechanical_energy_defect': abs(energy_defect) / initial_energy,
        'maximum_scaled_mechanical_energy_defect': maximum_scaled_energy_defect,
        'limitations': ['linear elastic synthetic taut span and fixed spatial ports',
                        'one prescribed incoming elastic characteristic per port',
                        'no reel dynamics, winding transition, slack, reversal or rolling contact'],
    }
