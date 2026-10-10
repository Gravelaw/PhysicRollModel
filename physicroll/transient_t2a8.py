"""Retained-strain reaction release ending at the first tautness loss.

The reel has prescribed initial wound history, but no applied torque. Its
speed and reaction torque follow the elastic span and the exposed layer.
The signed elastic continuation is evaluated only in disposable event probes.
"""

from dataclasses import dataclass
import math

from . import transient_t2a7 as winding
from . import transient_t2a5 as span
from . import transient_t2a6 as reel


MODEL_ID = 'T2A8_RETAINED_STRAIN_REACTION_RELEASE_FIRST_TENSION_ZERO_V1'
LAMBDA0 = 1.001
BETA_S_INV = 0.02
V0_M_S = -0.1
EXACT_EVENT_S = 0.05
HARD_HORIZON_S = 0.055
OBSERVATIONS_S = (0.0, 0.0125, 0.025, 0.0375)
INITIAL_REEL_LENGTH_M = 1.0
INITIAL_CUT_M = span.SPAN_LENGTH_M / LAMBDA0
FIRST_ZERO_CUT_M = (span.SPAN_LENGTH_M - V0_M_S * EXACT_EVENT_S)
D_M_S = BETA_S_INV * span.SPAN_LENGTH_M - V0_M_S * LAMBDA0
CORE_LABEL_M = INITIAL_CUT_M + INITIAL_REEL_LENGTH_M


@dataclass(frozen=True)
class T2A8Case:
    cell_count: int
    cfl_limit: float = span.CFL_LIMIT

    def __post_init__(self):
        if type(self.cell_count) is not int or self.cell_count not in (64, 128, 256):
            raise ValueError('T2A8 cell count must use a frozen spatial grid')
        if type(self.cfl_limit) not in (int, float) or self.cfl_limit not in (
                span.CFL_LIMIT, span.CFL_LIMIT / 2, span.CFL_LIMIT / 4):
            raise ValueError('T2A8 CFL must use a frozen time grid')


def _exact(time_s, position_m):
    stretch = LAMBDA0 - BETA_S_INV * time_s
    speed = (V0_M_S * LAMBDA0 - BETA_S_INV * position_m) / stretch
    label = (position_m - V0_M_S * time_s) / stretch
    return label, stretch, speed


def _wound_stretch(label_m):
    if label_m < INITIAL_CUT_M - 1e-12 or label_m > CORE_LABEL_M + 1e-12:
        raise ValueError('T2A8 material cut left retained winding inventory')
    if label_m >= FIRST_ZERO_CUT_M:
        return 1.0, 0.0
    denominator = BETA_S_INV * label_m - V0_M_S
    stretch = D_M_S / denominator
    derivative = -D_M_S * BETA_S_INV / denominator ** 2
    return stretch, derivative


def _remaining_strain_energy(label_m):
    """Stable exact integral of W(lambda_w) from the exposed cut inward."""
    stretch, _ = _wound_stretch(label_m)
    z = stretch - 1
    if z <= 0:
        return 0.0
    series = sum((-1) ** (order + 1) * (order - 2) / order * z ** order
                 for order in range(3, 13))
    return span.EA_N * D_M_S * series / (2 * BETA_S_INV)


def _primitive(state):
    a, momentum = state
    if not all(math.isfinite(value) for value in state) or a <= 0:
        raise ValueError('T2A8 left positive finite stretch domain')
    stretch = 1 / a
    velocity = momentum / (span.REFERENCE_LINE_MASS_KG_M * a)
    if not math.isfinite(stretch) or not math.isfinite(velocity) or stretch <= 0:
        raise ValueError('T2A8 left positive stretch domain')
    return stretch, velocity


def _physical_flux(state):
    stretch, velocity = _primitive(state)
    a, momentum = state
    tension = span.EA_N * (stretch - 1)
    energy = momentum * velocity / 2 + a * span.EA_N * (stretch - 1) ** 2 / 2
    return a * velocity, momentum * velocity - tension, velocity * (energy - tension)


def _interface_flux(left, right):
    left_flux, right_flux = _physical_flux(left), _physical_flux(right)
    left_stretch, left_speed = _primitive(left)
    right_stretch, right_speed = _primitive(right)
    signal = max(abs(left_speed) + left_stretch * span.REFERENCE_WAVE_SPEED_M_S,
                 abs(right_speed) + right_stretch * span.REFERENCE_WAVE_SPEED_M_S)
    def energy(state):
        stretch, speed = _primitive(state)
        return (state[1] * speed / 2 + state[0] * span.EA_N *
                (stretch - 1) ** 2 / 2)
    return tuple((left_flux[i] + right_flux[i]) / 2 -
                 signal * (right[i] - left[i]) / 2 for i in (0, 1)) + (
        (left_flux[2] + right_flux[2]) / 2 -
        signal * (energy(right) - energy(left)) / 2,), signal


def _characteristic(state, sign):
    stretch, velocity = _primitive(state)
    return velocity + sign * span.REFERENCE_WAVE_SPEED_M_S * stretch


def _characteristic_rate(state, rate, sign):
    a, p = state
    da, dp = rate
    characteristic = (p / span.REFERENCE_LINE_MASS_KG_M +
                      sign * span.REFERENCE_WAVE_SPEED_M_S) / a
    return dp / (span.REFERENCE_LINE_MASS_KG_M * a) - characteristic * da / a


def _port_states(cells, length_m, time_s):
    left_outgoing = (3 * _characteristic(cells[0], 1) -
                     _characteristic(cells[1], 1)) / 2
    _, exact_left_stretch, exact_left_speed = _exact(time_s, 0.0)
    left_incoming = exact_left_speed - span.REFERENCE_WAVE_SPEED_M_S * exact_left_stretch
    left_speed = (left_outgoing + left_incoming) / 2
    left_stretch = (left_outgoing - left_incoming) / (
        2 * span.REFERENCE_WAVE_SPEED_M_S)
    right_outgoing = (3 * _characteristic(cells[-1], -1) -
                      _characteristic(cells[-2], -1)) / 2
    cut = INITIAL_CUT_M + INITIAL_REEL_LENGTH_M - length_m
    retained_stretch, retained_derivative = _wound_stretch(cut)
    right_speed = right_outgoing + span.REFERENCE_WAVE_SPEED_M_S * retained_stretch
    radius, inertia = winding._geometry(length_m)
    if not all(math.isfinite(value) for value in (
            left_speed, left_stretch, right_speed, radius, inertia)):
        raise ValueError('T2A8 port left finite domain')
    if right_speed >= 0 or abs(right_speed) >= (
            retained_stretch * span.REFERENCE_WAVE_SPEED_M_S):
        raise ValueError('T2A8 release reversed or left subsonic domain')
    q = right_speed / retained_stretch
    return {
        'left_state': span._conserved(left_stretch, left_speed),
        'right_state': span._conserved(retained_stretch, right_speed),
        'left_stretch': left_stretch,
        'right_stretch': retained_stretch,
        'right_stretch_derivative_per_label': retained_derivative,
        'right_speed_m_s': right_speed,
        'right_reference_flux_m_s': q,
        'right_tension_n': span.EA_N * (retained_stretch - 1),
        'right_cut_m': cut,
        'radius_m': radius,
        'inertia_kg_m2': inertia,
        'omega_rad_s': right_speed / radius,
    }


def _rates(cells, length_m, time_s, dx):
    port = _port_states(cells, length_m, time_s)
    slopes = []
    for index in range(len(cells)):
        if index == 0:
            slopes.append(tuple(cells[1][j] - cells[0][j] for j in (0, 1)))
        elif index == len(cells) - 1:
            slopes.append(tuple(cells[-1][j] - cells[-2][j] for j in (0, 1)))
        else:
            slopes.append(tuple(span._minmod3(
                2 * (cells[index][j] - cells[index - 1][j]),
                (cells[index + 1][j] - cells[index - 1][j]) / 2,
                2 * (cells[index + 1][j] - cells[index][j]))
                for j in (0, 1)))
    left_flux = _physical_flux(port['left_state'])
    right_flux = _physical_flux(port['right_state'])
    fluxes = [left_flux]
    signal = 0.0
    minimum = (min(port['left_stretch'], port['right_stretch']) - 1, 'port')
    for index in range(len(cells)):
        stretch, speed = _primitive(cells[index])
        if stretch - 1 < minimum[0]:
            minimum = (stretch - 1, 'cell')
        signal = max(signal, abs(speed) + stretch * span.REFERENCE_WAVE_SPEED_M_S)
    for index in range(len(cells) - 1):
        left_trace = tuple(cells[index][j] + slopes[index][j] / 2 for j in (0, 1))
        right_trace = tuple(cells[index + 1][j] - slopes[index + 1][j] / 2
                            for j in (0, 1))
        for trace in (left_trace, right_trace):
            stretch, _ = _primitive(trace)
            if stretch - 1 < minimum[0]:
                minimum = (stretch - 1, 'reconstruction')
        flux, face_signal = _interface_flux(left_trace, right_trace)
        fluxes.append(flux)
        signal = max(signal, face_signal)
    fluxes.append(right_flux)
    for state in (port['left_state'], port['right_state']):
        stretch, speed = _primitive(state)
        signal = max(signal, abs(speed) + stretch * span.REFERENCE_WAVE_SPEED_M_S)
    field_rates = [tuple(-(fluxes[index + 1][j] - fluxes[index][j]) / dx
                         for j in (0, 1)) for index in range(len(cells))]
    rdot = (3 * _characteristic_rate(cells[-1], field_rates[-1], -1) -
            _characteristic_rate(cells[-2], field_rates[-2], -1)) / 2
    q = port['right_reference_flux_m_s']
    speed = port['right_speed_m_s']
    radius = port['radius_m']
    radius_rate = reel.KAPPA_M * q / (2 * radius)
    speed_rate = rdot - span.REFERENCE_WAVE_SPEED_M_S * q * (
        port['right_stretch_derivative_per_label'])
    alpha = speed_rate / radius - speed * radius_rate / radius ** 2
    torque = port['inertia_kg_m2'] * alpha + radius * port['right_tension_n']
    omega = port['omega_rad_s']
    kinetic_flux = q * span.REFERENCE_LINE_MASS_KG_M * speed ** 2 / 2
    strain_flux = q * span.EA_N * (port['right_stretch'] - 1) ** 2 / 2
    traction_work = port['right_tension_n'] * speed
    return {
        'field_rates': field_rates,
        'length_rate': q,
        'angle_rate': omega,
        'left_flux': left_flux,
        'right_flux': right_flux,
        'right_energy_terms': (kinetic_flux, strain_flux, traction_work),
        'drive_power_w': torque * omega,
        'angular_rhs_nm': (torque - radius * port['right_tension_n'] +
                           span.REFERENCE_LINE_MASS_KG_M * q * radius * speed),
        'advected_angular_flux_nm': span.REFERENCE_LINE_MASS_KG_M * q * radius * speed,
        'reaction_torque_nm': torque,
        'port': port,
        'minimum_stretch_margin': minimum[0],
        'minimum_location': minimum[1],
        'maximum_signal_m_s': signal,
    }


def _advance(cells, length_m, angle_rad, time_s, step_s, dx):
    first = _rates(cells, length_m, time_s, dx)
    predicted = [tuple(cell[j] + step_s * rate[j] for j in (0, 1))
                 for cell, rate in zip(cells, first['field_rates'])]
    predicted_length = length_m + step_s * first['length_rate']
    predicted_angle = angle_rad + step_s * first['angle_rate']
    second = _rates(predicted, predicted_length, time_s + step_s, dx)
    updated = [tuple((cell[j] + trial[j] + step_s * rate[j]) / 2
                     for j in (0, 1))
               for cell, trial, rate in zip(cells, predicted, second['field_rates'])]
    updated_length = (length_m + predicted_length +
                      step_s * second['length_rate']) / 2
    updated_angle = (angle_rad + predicted_angle +
                     step_s * second['angle_rate']) / 2
    final = _rates(updated, updated_length, time_s + step_s, dx)
    predictor_minimum = (second['minimum_stretch_margin'],
                         second['minimum_location'])
    endpoint_minimum = (final['minimum_stretch_margin'],
                        final['minimum_location'])
    courant = step_s * max(first['maximum_signal_m_s'],
                           second['maximum_signal_m_s'],
                           final['maximum_signal_m_s']) / dx
    return {
        'cells': updated,
        'length_m': updated_length,
        'angle_rad': updated_angle,
        'first': first,
        'second': second,
        'final': final,
        'predictor_minimum': predictor_minimum,
        'endpoint_minimum': endpoint_minimum,
        'courant': courant,
    }


def _integrals(cells, dx):
    mass = span.REFERENCE_LINE_MASS_KG_M * dx * sum(cell[0] for cell in cells)
    momentum = dx * sum(cell[1] for cell in cells)
    energy = 0.0
    for cell in cells:
        stretch, speed = _primitive(cell)
        energy += dx * (cell[1] * speed / 2 + cell[0] *
                        span.EA_N * (stretch - 1) ** 2 / 2)
    return mass, momentum, energy


def _snapshot(time_s, cells, length_m, angle_rad, released, integrals, dx):
    port = _port_states(cells, length_m, time_s)
    radius, inertia = port['radius_m'], port['inertia_kg_m2']
    omega = port['omega_rad_s']
    mass, momentum, span_energy = _integrals(cells, dx)
    cut = port['right_cut_m']
    stored = _remaining_strain_energy(cut)
    core = {
        'material_label_low_m': FIRST_ZERO_CUT_M,
        'material_label_high_m': CORE_LABEL_M,
        'reference_length_m': CORE_LABEL_M - FIRST_ZERO_CUT_M,
        'retained_strain_energy_j': 0.0,
        'retained_stretch': 1.0,
    }
    outer = {
        'material_label_low_m': cut,
        'material_label_high_m': FIRST_ZERO_CUT_M,
        'reference_length_m': FIRST_ZERO_CUT_M - cut,
        'retained_strain_energy_j': stored,
        'retained_stretch_profile': 'D/(beta*S-V)',
    }
    return {
        'time_s': time_s,
        'cell_conservative_fields': [list(cell) for cell in cells],
        'span_mass_kg': mass,
        'span_momentum_kg_m_s': momentum,
        'span_mechanical_energy_j': span_energy,
        'reel_reference_length_m': length_m,
        'reel_radius_m': radius,
        'reel_inertia_kg_m2': inertia,
        'reel_angular_speed_rad_s': omega,
        'reel_angle_rad': angle_rad,
        'reaction_torque_nm': _rates(cells, length_m, time_s, dx)['reaction_torque_nm'],
        'reel_angular_momentum_kg_m2_s': inertia * omega,
        'reel_kinetic_energy_j': inertia * omega ** 2 / 2,
        'remaining_wound_strain_energy_j': stored,
        'total_mechanical_energy_j': span_energy + inertia * omega ** 2 / 2 + stored,
        'right_material_label_m': cut,
        'ordered_wound_intervals': [core, outer],
        'released_intervals': [dict(item) for item in released],
        'wound_inventory_difference_m': (core['reference_length_m'] +
                                         outer['reference_length_m'] - length_m),
        'released_outer_label_difference_m': (
            released[-1]['material_label_high_m'] - cut if released else 0.0),
        'integrated_left_flux': list(integrals['left_flux']),
        'integrated_right_flux': list(integrals['right_flux']),
        'integrated_right_energy_terms': list(integrals['right_energy_terms']),
        'integrated_drive_work_j': integrals['drive_work'],
        'integrated_angular_rhs_nm_s': integrals['angular_rhs'],
        'integrated_advected_angular_flux_nm_s': integrals['advected_angular_flux'],
    }


def run_reaction_release_first_tension_zero(case: T2A8Case):
    """Solve the affine release episode and stop before any slack continuation."""
    if not isinstance(case, T2A8Case):
        raise ValueError('T2A8 requires a T2A8Case')
    dx = span.SPAN_LENGTH_M / case.cell_count
    cells = []
    for index in range(case.cell_count):
        midpoint = (index + .5) * dx
        _, stretch, velocity = _exact(0.0, midpoint)
        cells.append(span._conserved(stretch, velocity))
    length_m = INITIAL_REEL_LENGTH_M
    angle_rad = 0.0
    released = []
    integrals = {'left_flux': [0.0] * 3,
                 'right_flux': [0.0] * 3,
                 'right_energy_terms': [0.0] * 3,
                 'drive_work': 0.0,
                 'angular_rhs': 0.0,
                 'advected_angular_flux': 0.0}
    snapshots = [_snapshot(0.0, cells, length_m, angle_rad, released, integrals, dx)]
    initial = snapshots[0]
    initial_reel_energy = (initial['reel_kinetic_energy_j'] +
                           initial['remaining_wound_strain_energy_j'])
    initial_mass = initial['span_mass_kg'] + span.REFERENCE_LINE_MASS_KG_M * length_m
    maximum_mass_defect = maximum_momentum_defect = maximum_inventory_defect = 0.0
    maximum_angular_defect = maximum_reel_energy_defect = 0.0
    maximum_combined_energy_defect = maximum_storage_flux_defect = 0.0
    maximum_courant = 0.0
    time_s = 0.0
    steps = 0
    event = None
    for observation in (*OBSERVATIONS_S[1:], HARD_HORIZON_S):
        while time_s < observation - 1e-14:
            if steps >= 4000:
                raise ValueError('T2A8 exceeded accepted-step budget')
            start = _rates(cells, length_m, time_s, dx)
            if start['minimum_stretch_margin'] <= 0:
                raise ValueError('T2A8 committed state lost tautness')
            h = min(observation - time_s,
                    .99 * case.cfl_limit * dx / start['maximum_signal_m_s'])
            for _ in range(16):
                trial = _advance(cells, length_m, angle_rad, time_s, h, dx)
                if trial['courant'] <= case.cfl_limit * (1 + 1e-12):
                    break
                h /= 2
            else:
                raise ValueError('T2A8 failed reconstructed-stage CFL gate')
            if (trial['predictor_minimum'][0] <= 0 and
                    trial['endpoint_minimum'][0] > 0):
                # A predictor-only domain excursion is a stage guard, not a
                # first-hit event in the committed trajectory.
                for _ in range(16):
                    h /= 2
                    trial = _advance(cells, length_m, angle_rad, time_s, h, dx)
                    if (trial['predictor_minimum'][0] > 0 and
                            trial['courant'] <= case.cfl_limit * (1 + 1e-12)):
                        break
                else:
                    raise ValueError('T2A8 predictor could not stay taut')
            is_event = trial['endpoint_minimum'][0] <= 0
            event_bracket = None
            if is_event:
                low, high = 0.0, h
                feasible = None
                while high - low > 1e-9:
                    mid = (low + high) / 2
                    candidate = _advance(cells, length_m, angle_rad, time_s,
                                         mid, dx)
                    if (candidate['endpoint_minimum'][0] > 0 and
                            candidate['predictor_minimum'][0] > 0):
                        low, feasible = mid, candidate
                    else:
                        high = mid
                if feasible is None or low <= 0:
                    raise ValueError('T2A8 could not bracket first tension zero')
                h, trial = low, feasible
                upper_trial = _advance(cells, length_m, angle_rad, time_s,
                                       high, dx)
                if (span.EA_N * trial['endpoint_minimum'][0] > 1e-9 or
                        upper_trial['endpoint_minimum'][0] > 0):
                    # The predictor reached the taut-domain guard first.
                    # Advance a shorter admissible ordinary step, then
                    # seek an endpoint event from that newly committed state.
                    h /= 2
                    trial = _advance(cells, length_m, angle_rad, time_s, h, dx)
                    if (trial['predictor_minimum'][0] <= 0 or
                            trial['endpoint_minimum'][0] <= 0):
                        raise ValueError('T2A8 predictor guard could not shorten')
                    is_event = False
                else:
                    event_bracket = (time_s + low, time_s + high)
            maximum_courant = max(maximum_courant, trial['courant'])
            first, second = trial['first'], trial['second']
            old_mass, old_momentum, _ = _integrals(cells, dx)
            old_length = length_m
            old_port = first['port']
            old_kinetic = old_port['inertia_kg_m2'] * old_port['omega_rad_s'] ** 2 / 2
            old_cut = old_port['right_cut_m']
            old_stored = _remaining_strain_energy(old_cut)
            for key in ('left_flux', 'right_flux', 'right_energy_terms'):
                for index in range(3):
                    integrals[key][index] += h * (first[key][index] + second[key][index]) / 2
            for key, stage_key in (('drive_work', 'drive_power_w'),
                                   ('angular_rhs', 'angular_rhs_nm'),
                                   ('advected_angular_flux', 'advected_angular_flux_nm')):
                integrals[key] += h * (first[stage_key] + second[stage_key]) / 2
            cells, length_m, angle_rad = (trial['cells'], trial['length_m'],
                                          trial['angle_rad'])
            final_port = trial['final']['port']
            new_cut = final_port['right_cut_m']
            if new_cut <= old_cut:
                raise ValueError('T2A8 release did not consume outer material')
            removed_energy = old_stored - _remaining_strain_energy(new_cut)
            released.append({
                'material_label_low_m': old_cut,
                'material_label_high_m': new_cut,
                'reference_length_m': new_cut - old_cut,
                'mass_kg': span.REFERENCE_LINE_MASS_KG_M * (new_cut - old_cut),
                'released_strain_energy_j': removed_energy,
            })
            new_mass, new_momentum, new_span_energy = _integrals(cells, dx)
            maximum_mass_defect = max(maximum_mass_defect, abs(
                new_mass - old_mass + span.REFERENCE_LINE_MASS_KG_M * h *
                ((first['right_flux'][0] + second['right_flux'][0]) -
                 (first['left_flux'][0] + second['left_flux'][0])) / 2))
            maximum_momentum_defect = max(maximum_momentum_defect, abs(
                new_momentum - old_momentum + h *
                ((first['right_flux'][1] + second['right_flux'][1]) -
                 (first['left_flux'][1] + second['left_flux'][1])) / 2))
            maximum_inventory_defect = max(maximum_inventory_defect, abs(
                new_mass + span.REFERENCE_LINE_MASS_KG_M * length_m -
                initial_mass - span.REFERENCE_LINE_MASS_KG_M *
                integrals['left_flux'][0]))
            new_kinetic = (final_port['inertia_kg_m2'] *
                           final_port['omega_rad_s'] ** 2 / 2)
            new_stored = _remaining_strain_energy(new_cut)
            maximum_angular_defect = max(maximum_angular_defect, abs(
                final_port['inertia_kg_m2'] * final_port['omega_rad_s'] -
                initial['reel_angular_momentum_kg_m2_s'] -
                integrals['angular_rhs']))
            maximum_reel_energy_defect = max(maximum_reel_energy_defect, abs(
                new_kinetic + new_stored - initial_reel_energy -
                integrals['drive_work'] - integrals['right_flux'][2]))
            maximum_storage_flux_defect = max(maximum_storage_flux_defect, abs(
                new_stored - initial['remaining_wound_strain_energy_j'] -
                integrals['right_energy_terms'][1]))
            maximum_combined_energy_defect = max(
                maximum_combined_energy_defect,
                abs(new_span_energy + new_kinetic + new_stored -
                    initial['total_mechanical_energy_j'] -
                    integrals['left_flux'][2] - integrals['drive_work']))
            time_s += h
            steps += 1
            if is_event:
                event = {
                    'event_type': 'FIRST_TENSION_ZERO',
                    'bracket_time_s': list(event_bracket),
                    'feasible_time_s': time_s,
                    'location_type': trial['endpoint_minimum'][1],
                    'feasible_minimum_tension_n': (
                        span.EA_N * trial['endpoint_minimum'][0]),
                    'upper_trial_minimum_tension_n': (
                        span.EA_N * upper_trial['endpoint_minimum'][0]),
                }
                break
        if event:
            break
        time_s = observation
        snapshots.append(_snapshot(time_s, cells, length_m, angle_rad,
                                   released, integrals, dx))
    if event is None:
        raise ValueError('T2A8 did not reach first tension zero by hard horizon')
    snapshots.append(_snapshot(time_s, cells, length_m, angle_rad,
                               released, integrals, dx))
    return {
        'model_id': MODEL_ID,
        'mode': 'retained_strain_reaction_release_first_tension_zero',
        'reel_torque_role': 'reaction_not_applied_input',
        'reel_speed_role': 'algebraic_from_span_and_retained_stretch',
        'episode_outcome': 'STOPPED_AT_FIRST_TENSION_ZERO',
        'cell_count': case.cell_count,
        'cfl_limit': case.cfl_limit,
        'accepted_steps': steps,
        'snapshots': snapshots,
        'event': event,
        'maximum_reconstructed_stage_courant': maximum_courant,
        'maximum_mass_balance_defect_kg': maximum_mass_defect,
        'maximum_momentum_balance_defect_kg_m_s': maximum_momentum_defect,
        'maximum_combined_inventory_defect_kg': maximum_inventory_defect,
        'maximum_reel_angular_impulse_defect_nm_s': maximum_angular_defect,
        'maximum_reel_cumulative_energy_defect_j': maximum_reel_energy_defect,
        'maximum_combined_energy_defect_j': maximum_combined_energy_defect,
        'maximum_exact_storage_vs_transfer_flux_defect_j': maximum_storage_flux_defect,
        'limitations': ['affine synthetic wave and specially matched retained history',
                        'reaction release without applied torque or general reversal',
                        'first tension zero stops; no slack, contact or physical validation'],
    }
