"""Torque-driven, append-only elastic span/reel coupling benchmark.

An exact wave supplies the initial span, left incoming characteristic and a
manufactured drive torque. The right incoming characteristic is determined by
the evolving reel speed; the reel receives the same physical boundary flux
used by the span update. Release, reversal and rolling contact are excluded.
"""

from dataclasses import dataclass
import math

from . import transient_t2a5 as span
from . import transient_t2a6 as reel


MODEL_ID = 'T2A7_TORQUE_DRIVEN_APPEND_ONLY_ELASTIC_COUPLING_V1'
INITIAL_REEL_LENGTH_M = reel.INITIAL_LENGTH_M
SAMPLE_TIMES_S = (0.0, 0.005, 0.04, 0.08)


@dataclass(frozen=True)
class T2A7Case:
    cell_count: int
    cfl_limit: float = span.CFL_LIMIT

    def __post_init__(self):
        if type(self.cell_count) is not int or self.cell_count not in (64, 128, 256):
            raise ValueError('T2A7 cell count must use a frozen spatial grid')
        if type(self.cfl_limit) not in (int, float) or self.cfl_limit not in (
                span.CFL_LIMIT, span.CFL_LIMIT / 2, span.CFL_LIMIT / 4):
            raise ValueError('T2A7 CFL must use a frozen time grid')


def _geometry(length_m):
    if not math.isfinite(length_m) or length_m <= 0:
        raise ValueError('T2A7 requires positive wound inventory')
    radius = math.sqrt(reel.CORE_RADIUS_M ** 2 + reel.KAPPA_M * length_m)
    inertia = reel.CORE_INERTIA_KG_M2 + reel.LINE_MASS_KG_M * (
        reel.CORE_RADIUS_M ** 2 * length_m + reel.KAPPA_M * length_m ** 2 / 2)
    return radius, inertia


def _manufactured_applied_torque(time_s):
    """Prescribed time-only forcing from the independent exact-wave fixture."""
    exact_port = reel._port(time_s)
    initial_label = reel._port(0.0)['material_label_m']
    exact_length = INITIAL_REEL_LENGTH_M + initial_label - exact_port['material_label_m']
    return reel._reel(exact_port, exact_length)['reaction_drive_torque_nm']


def _left_port(cells, time_s, reference_case):
    stretch_out, speed_out = span._primitive(cells[0])
    stretch_exact, speed_exact = span._exact_primitive(0.0, time_s, reference_case)
    incoming = speed_exact - span.REFERENCE_WAVE_SPEED_M_S * stretch_exact
    outgoing = speed_out + span.REFERENCE_WAVE_SPEED_M_S * stretch_out
    speed = (incoming + outgoing) / 2
    stretch = (outgoing - incoming) / (2 * span.REFERENCE_WAVE_SPEED_M_S)
    return span._conserved(stretch, speed)


def _right_port(cells, length_m, omega_rad_s):
    if not math.isfinite(omega_rad_s) or omega_rad_s <= 0:
        raise ValueError('T2A7 requires positive winding angular speed')
    radius, inertia = _geometry(length_m)
    interior_stretch, interior_speed = span._primitive(cells[-1])
    outgoing = interior_speed - span.REFERENCE_WAVE_SPEED_M_S * interior_stretch
    speed = radius * omega_rad_s
    stretch = (speed - outgoing) / span.REFERENCE_WAVE_SPEED_M_S
    if not math.isfinite(stretch) or stretch <= 1 or speed >= (
            stretch * span.REFERENCE_WAVE_SPEED_M_S):
        raise ValueError('T2A7 right port left taut positive subsonic domain')
    tension = span.EA_N * (stretch - 1)
    q = speed / stretch
    strain_energy = span.EA_N * (stretch - 1) ** 2 / 2
    return {
        'stretch': stretch,
        'speed_m_s': speed,
        'reference_flux_m_s': q,
        'tension_n': tension,
        'radius_m': radius,
        'inertia_kg_m2': inertia,
        'angular_speed_rad_s': omega_rad_s,
        'wound_reference_length_m': length_m,
        'stored_energy_per_reference_m_j_m': strain_energy,
        'conserved_state': span._conserved(stretch, speed),
        'incoming_characteristic_m_s': speed + span.REFERENCE_WAVE_SPEED_M_S * stretch,
        'outgoing_characteristic_m_s': outgoing,
    }


def _rates(cells, length_m, omega_rad_s, time_s, reference_case):
    left = _left_port(cells, time_s, reference_case)
    right = _right_port(cells, length_m, omega_rad_s)
    extended = [left, *cells, right['conserved_state']]
    slopes = [(0.0, 0.0)]
    for index in range(1, len(extended) - 1):
        previous, center, following = extended[index - 1:index + 2]
        slopes.append(tuple(span._minmod3(2 * (center[j] - previous[j]),
                                          (following[j] - previous[j]) / 2,
                                          2 * (following[j] - center[j]))
                            for j in (0, 1)))
    slopes.append((0.0, 0.0))
    fluxes = []
    maximum_signal = 0.0
    for index in range(len(extended) - 2):
        left_trace = tuple(extended[index][j] + slopes[index][j] / 2
                           for j in (0, 1))
        right_trace = tuple(extended[index + 1][j] - slopes[index + 1][j] / 2
                            for j in (0, 1))
        flux, signal = span._interface_flux(left_trace, right_trace)
        fluxes.append(flux)
        maximum_signal = max(maximum_signal, signal)
    right_flux = span._physical_flux(right['conserved_state'])
    fluxes.append(right_flux)
    maximum_signal = max(maximum_signal, abs(right['speed_m_s']) +
                         right['stretch'] * span.REFERENCE_WAVE_SPEED_M_S)
    dx = span.SPAN_LENGTH_M / reference_case.cell_count
    cell_rates = [tuple(-(fluxes[index + 1][j] - fluxes[index][j]) / dx
                        for j in (0, 1)) for index in range(len(cells))]
    applied_torque = _manufactured_applied_torque(time_s)
    omega_rate = ((applied_torque - right['radius_m'] * right['tension_n']) /
                  right['inertia_kg_m2'])
    q = right['reference_flux_m_s']
    speed = right['speed_m_s']
    energy_terms = (q * reel.LINE_MASS_KG_M * speed ** 2 / 2,
                    q * right['stored_energy_per_reference_m_j_m'],
                    right['tension_n'] * speed)
    return {
        'cell_rates': cell_rates,
        'reel_rates': (q, omega_rate, omega_rad_s),
        'left_flux': fluxes[0],
        'right_flux': right_flux,
        'right_port': right,
        'right_energy_terms': energy_terms,
        'applied_torque_nm': applied_torque,
        'drive_power_w': applied_torque * omega_rad_s,
        'angular_rhs_nm': (applied_torque - right['radius_m'] * right['tension_n'] +
                           reel.LINE_MASS_KG_M * q * right['radius_m'] * speed),
        'maximum_signal_m_s': maximum_signal,
    }


def _check_state(cells, length_m, omega_rad_s):
    for cell in cells:
        stretch, velocity = span._primitive(cell)
        if abs(velocity) >= stretch * span.REFERENCE_WAVE_SPEED_M_S:
            raise ValueError('T2A7 span left subsonic domain')
    _right_port(cells, length_m, omega_rad_s)


def _advance(cells, length_m, omega_rad_s, angle_rad, time_s, step_s,
             reference_case):
    dx = span.SPAN_LENGTH_M / reference_case.cell_count
    first = _rates(cells, length_m, omega_rad_s, time_s, reference_case)
    predicted = [tuple(cell[j] + step_s * rate[j] for j in (0, 1))
                 for cell, rate in zip(cells, first['cell_rates'])]
    predicted_reel = (length_m + step_s * first['reel_rates'][0],
                      omega_rad_s + step_s * first['reel_rates'][1],
                      angle_rad + step_s * first['reel_rates'][2])
    _check_state(predicted, *predicted_reel[:2])
    second = _rates(predicted, *predicted_reel[:2], time_s + step_s,
                    reference_case)
    updated = [tuple((cell[j] + trial[j] + step_s * rate[j]) / 2
                     for j in (0, 1))
               for cell, trial, rate in zip(cells, predicted, second['cell_rates'])]
    updated_reel = tuple((original + trial + step_s * rate) / 2
                         for original, trial, rate in zip(
                             (length_m, omega_rad_s, angle_rad), predicted_reel,
                             second['reel_rates']))
    _check_state(updated, *updated_reel[:2])
    courant = step_s * max(first['maximum_signal_m_s'],
                           second['maximum_signal_m_s']) / dx
    return updated, updated_reel, first, second, courant


def _interval(label_high, length_m, stretch, stage):
    low = label_high - length_m
    energy = span.EA_N * length_m * (stretch - 1) ** 2 / 2
    return {
        'material_label_low_m': low,
        'material_label_high_m': label_high,
        'reference_length_m': length_m,
        'mass_kg': span.REFERENCE_LINE_MASS_KG_M * length_m,
        'retained_stretch': stretch,
        'integration_stage': stage,
        'retained_strain_energy_j': energy,
    }


def _snapshot(time_s, cells, length_m, omega_rad_s, angle_rad, intervals,
              initial_label_m, integrals):
    dx = span.SPAN_LENGTH_M / len(cells)
    span_mass, span_momentum, span_energy = span._integrals(cells, dx)
    radius, inertia = _geometry(length_m)
    winding_energy = sum(item['retained_strain_energy_j'] for item in intervals)
    right_label = initial_label_m - (length_m - INITIAL_REEL_LENGTH_M)
    return {
        'time_s': time_s,
        'cell_conservative_fields': [list(cell) for cell in cells],
        'span_mass_kg': span_mass,
        'span_momentum_kg_m_s': span_momentum,
        'span_mechanical_energy_j': span_energy,
        'reel_reference_length_m': length_m,
        'reel_mass_kg': span.REFERENCE_LINE_MASS_KG_M * length_m,
        'reel_radius_m': radius,
        'reel_inertia_kg_m2': inertia,
        'reel_angular_speed_rad_s': omega_rad_s,
        'reel_angle_rad': angle_rad,
        'reel_angular_momentum_kg_m2_s': inertia * omega_rad_s,
        'reel_kinetic_energy_j': inertia * omega_rad_s ** 2 / 2,
        'wound_strain_energy_j': winding_energy,
        'total_mechanical_energy_j': (span_energy + inertia * omega_rad_s ** 2 / 2 +
                                      winding_energy),
        'right_material_label_m': right_label,
        'packet_inventory_difference_m': (sum(item['reference_length_m']
                                               for item in intervals) - length_m),
        'packet_outer_label_difference_m': (intervals[-1]['material_label_low_m'] -
                                            right_label),
        'ordered_wound_intervals': [dict(item) for item in intervals],
        'integrated_left_flux': list(integrals['left_flux']),
        'integrated_right_flux': list(integrals['right_flux']),
        'integrated_right_energy_terms': list(integrals['right_energy_terms']),
        'integrated_drive_work_j': integrals['drive_work'],
        'integrated_angular_rhs_nm_s': integrals['angular_rhs'],
    }


def run_torque_driven_elastic_coupling(case: T2A7Case):
    """Integrate the frozen taut, forward-winding coupled benchmark."""
    if not isinstance(case, T2A7Case):
        raise ValueError('T2A7 requires a T2A7Case')
    reference_case = span.T2A5Case(case.cell_count)
    dx = span.SPAN_LENGTH_M / case.cell_count
    cells = [span._initial_cell(index * dx, (index + 1) * dx, reference_case)
             for index in range(case.cell_count)]
    length_m = INITIAL_REEL_LENGTH_M
    exact_initial_port = reel._port(0.0)
    radius, _ = _geometry(length_m)
    omega_rad_s = exact_initial_port['speed_m_s'] / radius
    angle_rad = 0.0
    initial_port = _right_port(cells, length_m, omega_rad_s)
    initial_port_projection_error = (initial_port['stretch'] -
                                     exact_initial_port['stretch'])
    initial_label = span._reference_at(span.SPAN_LENGTH_M, 0.0, reference_case)
    intervals = [_interval(initial_label + length_m, length_m,
                           exact_initial_port['stretch'], 'initial')]
    integrals = {'left_flux': [0.0] * 3,
                 'right_flux': [0.0] * 3,
                 'right_energy_terms': [0.0] * 3,
                 'drive_work': 0.0, 'angular_rhs': 0.0}
    snapshots = [_snapshot(0.0, cells, length_m, omega_rad_s, angle_rad,
                           intervals, initial_label, integrals)]
    initial_total_energy = snapshots[0]['total_mechanical_energy_j']
    initial_reel_energy = (snapshots[0]['reel_kinetic_energy_j'] +
                           snapshots[0]['wound_strain_energy_j'])
    initial_angular_momentum = snapshots[0]['reel_angular_momentum_kg_m2_s']
    initial_combined_mass = snapshots[0]['span_mass_kg'] + snapshots[0]['reel_mass_kg']
    maximum_courant = maximum_mass_defect = maximum_momentum_defect = 0.0
    maximum_angular_defect = maximum_reel_energy_defect = 0.0
    maximum_reel_cumulative_energy_defect = 0.0
    maximum_total_energy_defect = 0.0
    maximum_inventory_defect = 0.0
    time_s = 0.0
    step_count = 0
    for observation in SAMPLE_TIMES_S[1:]:
        while time_s < observation - 1e-14:
            if step_count >= 4000:
                raise ValueError('T2A7 exceeded accepted-step budget')
            start = _rates(cells, length_m, omega_rad_s, time_s, reference_case)
            h = min(observation - time_s,
                    0.99 * case.cfl_limit * dx / start['maximum_signal_m_s'])
            for _ in range(16):
                try:
                    updated, updated_reel, first, second, courant = _advance(
                        cells, length_m, omega_rad_s, angle_rad, time_s, h,
                        reference_case)
                except ValueError:
                    h /= 2
                    continue
                if courant <= case.cfl_limit * (1 + 1e-12):
                    break
                h /= 2
            else:
                raise ValueError('T2A7 failed stage domain/CFL gate')
            maximum_courant = max(maximum_courant, courant)
            old_span_mass, old_span_momentum, _ = span._integrals(cells, dx)
            old_length, old_omega = length_m, omega_rad_s
            old_radius, old_inertia = _geometry(old_length)
            old_reel_kinetic = old_inertia * old_omega ** 2 / 2
            for name in ('left_flux', 'right_flux', 'right_energy_terms'):
                for j in range(3):
                    integrals[name][j] += h * (first[name][j] + second[name][j]) / 2
            drive_work = h * (first['drive_power_w'] + second['drive_power_w']) / 2
            angular_impulse = h * (first['angular_rhs_nm'] + second['angular_rhs_nm']) / 2
            integrals['drive_work'] += drive_work
            integrals['angular_rhs'] += angular_impulse
            cells = updated
            length_m, omega_rad_s, angle_rad = updated_reel
            transferred = length_m - old_length
            if transferred <= 0:
                raise ValueError('T2A7 left append-only transfer domain')
            first_transfer = h * first['right_port']['reference_flux_m_s'] / 2
            second_transfer = h * second['right_port']['reference_flux_m_s'] / 2
            if abs(transferred - first_transfer - second_transfer) > 1e-12:
                raise ValueError('T2A7 reel inventory disagrees with stage transfer')
            first_packet = _interval(intervals[-1]['material_label_low_m'],
                                     first_transfer, first['right_port']['stretch'],
                                     'start')
            second_packet = _interval(first_packet['material_label_low_m'],
                                      second_transfer, second['right_port']['stretch'],
                                      'predictor')
            intervals.extend((first_packet, second_packet))
            new_span_mass, new_span_momentum, _ = span._integrals(cells, dx)
            maximum_mass_defect = max(maximum_mass_defect, abs(
                new_span_mass - old_span_mass + span.REFERENCE_LINE_MASS_KG_M *
                h * ((first['right_flux'][0] + second['right_flux'][0]) -
                     (first['left_flux'][0] + second['left_flux'][0])) / 2))
            maximum_momentum_defect = max(maximum_momentum_defect, abs(
                new_span_momentum - old_span_momentum + h *
                ((first['right_flux'][1] + second['right_flux'][1]) -
                 (first['left_flux'][1] + second['left_flux'][1])) / 2))
            radius, inertia = _geometry(length_m)
            new_reel_kinetic = inertia * omega_rad_s ** 2 / 2
            maximum_angular_defect = max(maximum_angular_defect, abs(
                inertia * omega_rad_s - initial_angular_momentum -
                integrals['angular_rhs']))
            reel_energy_input = drive_work + h * (
                first['right_flux'][2] + second['right_flux'][2]) / 2
            maximum_reel_energy_defect = max(maximum_reel_energy_defect, abs(
                new_reel_kinetic - old_reel_kinetic +
                first_packet['retained_strain_energy_j'] +
                second_packet['retained_strain_energy_j'] - reel_energy_input))
            current_span_energy = span._integrals(cells, dx)[2]
            current_total_energy = (current_span_energy + new_reel_kinetic +
                                    sum(item['retained_strain_energy_j']
                                        for item in intervals))
            maximum_reel_cumulative_energy_defect = max(
                maximum_reel_cumulative_energy_defect,
                abs(new_reel_kinetic + sum(item['retained_strain_energy_j']
                                           for item in intervals) -
                    initial_reel_energy - integrals['drive_work'] -
                    integrals['right_flux'][2]))
            maximum_total_energy_defect = max(maximum_total_energy_defect, abs(
                current_total_energy - initial_total_energy -
                integrals['left_flux'][2] - integrals['drive_work']))
            maximum_inventory_defect = max(maximum_inventory_defect, abs(
                new_span_mass + span.REFERENCE_LINE_MASS_KG_M * length_m -
                initial_combined_mass -
                span.REFERENCE_LINE_MASS_KG_M * integrals['left_flux'][0]))
            time_s += h
            step_count += 1
        time_s = observation
        snapshots.append(_snapshot(time_s, cells, length_m, omega_rad_s,
                                   angle_rad, intervals, initial_label, integrals))
    return {
        'model_id': MODEL_ID,
        'mode': 'torque_driven_append_only_elastic_span_reel_coupling',
        'drive_torque_role': 'prescribed_manufactured_time_history',
        'reel_speed_role': 'predicted_from_torque_and_span_tension',
        'right_incoming_characteristic_role': 'predicted_from_reel_speed',
        'episode_outcome': 'COMPLETED_TAUT_APPEND_ONLY_EPISODE',
        'cell_count': case.cell_count,
        'cfl_limit': case.cfl_limit,
        'accepted_steps': step_count,
        'initial_right_port_stretch_projection_error': initial_port_projection_error,
        'snapshots': snapshots,
        'maximum_reconstructed_stage_courant': maximum_courant,
        'maximum_mass_balance_defect_kg': maximum_mass_defect,
        'maximum_momentum_balance_defect_kg_m_s': maximum_momentum_defect,
        'maximum_combined_inventory_defect_kg': maximum_inventory_defect,
        'maximum_reel_angular_impulse_defect_nm_s': maximum_angular_defect,
        'maximum_reel_step_energy_defect_j': maximum_reel_energy_defect,
        'maximum_reel_cumulative_energy_defect_j': (
            maximum_reel_cumulative_energy_defect),
        'maximum_combined_energy_defect_j': maximum_total_energy_defect,
        'limitations': ['taut positive forward-winding ideal no-slip strain-matched transfer',
                        'synthetic elastic law and manufactured applied torque',
                        'no release, reversal, slack, rolling contact or physical validation'],
    }
