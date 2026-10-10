"""Matched elastic winding/release with a computed speed reversal.

This is a reaction-mode manufactured episode. The reel torque is calculated
from the elastic-port motion; it is not an applied drive input.
"""

from dataclasses import dataclass
import math

from . import transient_t2a5 as span
from . import transient_t2a6 as reel
from . import transient_t2a7 as winding
from . import transient_t2a8 as fv


MODEL_ID = 'T2A9_MATCHED_REACTION_REVERSAL_V1'
LAMBDA0 = 1.01
DELTA = .001
K = math.pi / 2
REVERSAL_REFERENCE_S = .02  # exact reference only; the event is located from q
S0_M = .9894996247259713887694
OLD_LENGTH_M = 1.0
OLD_STRETCH = 1.010015685968241193
HARD_HORIZON_S = .045


@dataclass(frozen=True)
class T2A9Case:
    cell_count: int
    cfl_limit: float = span.CFL_LIMIT

    def __post_init__(self):
        if type(self.cell_count) is not int or self.cell_count not in (64, 128, 256):
            raise ValueError('T2A9 requires a frozen spatial grid')
        if type(self.cfl_limit) not in (int, float) or self.cfl_limit not in (
                span.CFL_LIMIT, span.CFL_LIMIT / 2, span.CFL_LIMIT / 4):
            raise ValueError('T2A9 requires a frozen time grid')


def _exact(time_s, position_m):
    """Invert the declared wave to initialize the manufactured episode."""
    phase = span.REFERENCE_WAVE_SPEED_M_S * K * (time_s - REVERSAL_REFERENCE_S)
    def map_position(label):
        return LAMBDA0 * label + DELTA / K * math.sin(K * label) * math.cos(phase)
    low, high = 0.0, 1.1
    for _ in range(55):
        middle = (low + high) / 2
        if map_position(middle) < position_m:
            low = middle
        else:
            high = middle
    label = (low + high) / 2
    stretch = LAMBDA0 + DELTA * math.cos(K * label) * math.cos(phase)
    velocity = -DELTA * span.REFERENCE_WAVE_SPEED_M_S * math.sin(K * label) * math.sin(phase)
    return label, stretch, velocity


def _programmed_stretch(label_m):
    """The incoming condition is externally supplied only while winding."""
    phase = K * label_m
    cot = math.cos(phase) / math.sin(phase)
    stretch = LAMBDA0 + K * (span.SPAN_LENGTH_M - LAMBDA0 * label_m) * cot
    derivative = (-K * LAMBDA0 * cot - K * K *
                  (span.SPAN_LENGTH_M - LAMBDA0 * label_m) /
                  math.sin(phase) ** 2)
    return stretch, derivative


def _record_stretch(record, label_m):
    """Evaluate the saved interval's original profile, including mutations."""
    k = record['profile_k_per_m']
    lam = record['profile_lambda0']
    length = record['profile_span_length_m']
    phase = k * label_m
    cot = math.cos(phase) / math.sin(phase)
    return (lam + k * (length - lam * label_m) * cot + record['profile_offset'],
            -k * lam * cot - k * k * (length - lam * label_m) /
            math.sin(phase) ** 2)


def _donor(records, label_m):
    if not records:
        raise ValueError('T2A9 release has no newly wound donor')
    for record in reversed(records):
        if (record['material_label_low_m'] - 1e-12 <= label_m <=
                record['material_label_high_m'] + 1e-12):
            return _record_stretch(record, label_m)
    # Full-trial endpoint probes may run a fraction beyond the old-layer cut.
    # Their extrapolated new profile is never committed or stored.
    if label_m > S0_M and label_m - S0_M < .001:
        return _record_stretch(records[0], label_m)
    raise ValueError('T2A9 release left the newly deposited inventory')


def _new_record(low_m, high_m):
    if low_m > high_m + 1e-13:
        raise ValueError('T2A9 winding interval has reversed labels')
    return {'material_label_low_m': low_m, 'material_label_high_m': high_m,
            'profile_lambda0': LAMBDA0, 'profile_k_per_m': K,
            'profile_span_length_m': span.SPAN_LENGTH_M, 'profile_offset': 0.0}


def _interval_energy(low_m, high_m, record):
    """Original-label Simpson quadrature, independent of stage qW flux."""
    if high_m <= low_m:
        return 0.0
    count = 8
    h = (high_m - low_m) / count
    total = 0.0
    for index in range(count + 1):
        stretch, _ = _record_stretch(record, low_m + index * h)
        weight = 1 if index in (0, count) else 4 if index % 2 else 2
        total += weight * span.EA_N * (stretch - 1) ** 2 / 2
    return total * h / 3


def _active_energy(cut_m, records):
    return sum(_interval_energy(max(cut_m, item['material_label_low_m']),
                                item['material_label_high_m'], item)
               for item in records)


def _released_energy(low_m, high_m, records):
    return sum(_interval_energy(max(low_m, item['material_label_low_m']),
                                min(high_m, item['material_label_high_m']), item)
               for item in records)


def _port(cells, length_m, time_s, mode, records):
    left_out = (3 * fv._characteristic(cells[0], 1) -
                fv._characteristic(cells[1], 1)) / 2
    # One reflecting condition v(0,t)=0 determines the incoming
    # characteristic from the numerical outgoing characteristic.
    left_speed = 0.0
    left_stretch = left_out / span.REFERENCE_WAVE_SPEED_M_S
    right_out = (3 * fv._characteristic(cells[-1], -1) -
                 fv._characteristic(cells[-2], -1)) / 2
    cut = S0_M + OLD_LENGTH_M - length_m
    stretch, derivative = (_programmed_stretch(cut) if mode == 'wind'
                           else _donor(records, cut))
    speed = right_out + span.REFERENCE_WAVE_SPEED_M_S * stretch
    radius, inertia = winding._geometry(length_m)
    if not all(math.isfinite(value) for value in (
            left_stretch, left_speed, stretch, derivative, speed, radius, inertia)):
        raise ValueError('T2A9 port left finite domain')
    if min(left_stretch, stretch) < 1.008 or abs(speed / stretch) >= (
            span.REFERENCE_WAVE_SPEED_M_S):
        raise ValueError('T2A9 port left taut subsonic case')
    return {'left_state': span._conserved(left_stretch, left_speed),
            'right_state': span._conserved(stretch, speed),
            'left_stretch': left_stretch, 'right_stretch': stretch,
            'right_stretch_derivative_per_label': derivative,
            'right_speed_m_s': speed, 'right_reference_flux_m_s': speed / stretch,
            'right_tension_n': span.EA_N * (stretch - 1),
            'right_cut_m': cut, 'radius_m': radius, 'inertia_kg_m2': inertia,
            'omega_rad_s': speed / radius, 'donor_role': (
                'programmed_incoming_stretch' if mode == 'wind'
                else 'exposed_stored_interval')}


def _rates(cells, length_m, time_s, dx, mode, records):
    port = _port(cells, length_m, time_s, mode, records)
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
    left_flux = fv._physical_flux(port['left_state'])
    right_flux = fv._physical_flux(port['right_state'])
    fluxes = [left_flux]
    minimum_stretch = min(port['left_stretch'], port['right_stretch'])
    signal = 0.0
    for cell in cells:
        stretch, speed = fv._primitive(cell)
        minimum_stretch = min(minimum_stretch, stretch)
        signal = max(signal, abs(speed) + stretch * span.REFERENCE_WAVE_SPEED_M_S)
    for index in range(len(cells) - 1):
        left_trace = tuple(cells[index][j] + slopes[index][j] / 2 for j in (0, 1))
        right_trace = tuple(cells[index + 1][j] - slopes[index + 1][j] / 2
                            for j in (0, 1))
        for trace in (left_trace, right_trace):
            minimum_stretch = min(minimum_stretch, fv._primitive(trace)[0])
        face_flux, face_signal = fv._interface_flux(left_trace, right_trace)
        fluxes.append(face_flux)
        signal = max(signal, face_signal)
    fluxes.append(right_flux)
    for state in (port['left_state'], port['right_state']):
        stretch, speed = fv._primitive(state)
        signal = max(signal, abs(speed) + stretch * span.REFERENCE_WAVE_SPEED_M_S)
    field_rates = [tuple(-(fluxes[index + 1][j] - fluxes[index][j]) / dx
                         for j in (0, 1)) for index in range(len(cells))]
    rdot = (3 * fv._characteristic_rate(cells[-1], field_rates[-1], -1) -
            fv._characteristic_rate(cells[-2], field_rates[-2], -1)) / 2
    q = port['right_reference_flux_m_s']
    speed = port['right_speed_m_s']
    radius = port['radius_m']
    radius_rate = reel.KAPPA_M * q / (2 * radius)
    speed_rate = rdot - span.REFERENCE_WAVE_SPEED_M_S * q * (
        port['right_stretch_derivative_per_label'])
    alpha = speed_rate / radius - speed * radius_rate / radius ** 2
    torque = port['inertia_kg_m2'] * alpha + radius * port['right_tension_n']
    kinetic_flux = q * span.REFERENCE_LINE_MASS_KG_M * speed ** 2 / 2
    strain_flux = q * span.EA_N * (port['right_stretch'] - 1) ** 2 / 2
    traction_work = port['right_tension_n'] * speed
    return {'field_rates': field_rates, 'length_rate': q,
            'angle_rate': port['omega_rad_s'], 'left_flux': left_flux,
            'right_flux': right_flux,
            'right_energy_terms': (kinetic_flux, strain_flux, traction_work),
            'drive_power_w': torque * port['omega_rad_s'],
            'angular_rhs_nm': torque - radius * port['right_tension_n'] +
                              span.REFERENCE_LINE_MASS_KG_M * q * radius * speed,
            'advected_angular_flux_nm': span.REFERENCE_LINE_MASS_KG_M * q * radius * speed,
            'reaction_torque_nm': torque, 'port': port,
            'minimum_stretch': minimum_stretch, 'maximum_signal_m_s': signal}


def _advance(cells, length_m, angle_rad, time_s, step_s, dx, mode, records):
    first = _rates(cells, length_m, time_s, dx, mode, records)
    predicted = [tuple(cell[j] + step_s * rate[j] for j in (0, 1))
                 for cell, rate in zip(cells, first['field_rates'])]
    predicted_length = length_m + step_s * first['length_rate']
    predicted_angle = angle_rad + step_s * first['angle_rate']
    second = _rates(predicted, predicted_length, time_s + step_s, dx, mode, records)
    updated = [tuple((cell[j] + trial[j] + step_s * rate[j]) / 2
                     for j in (0, 1))
               for cell, trial, rate in zip(cells, predicted, second['field_rates'])]
    updated_length = (length_m + predicted_length + step_s * second['length_rate']) / 2
    updated_angle = (angle_rad + predicted_angle + step_s * second['angle_rate']) / 2
    final = _rates(updated, updated_length, time_s + step_s, dx, mode, records)
    courant = step_s * max(first['maximum_signal_m_s'], second['maximum_signal_m_s'],
                           final['maximum_signal_m_s']) / dx
    return {'cells': updated, 'length_m': updated_length,
            'angle_rad': updated_angle, 'first': first, 'second': second,
            'final': final, 'courant': courant}


def _snapshot(time_s, cells, length_m, angle_rad, mode, records,
              new_energy_j, integrated, dx):
    rates = _rates(cells, length_m, time_s, dx, mode, records)
    port = rates['port']
    mass, momentum, span_energy = fv._integrals(cells, dx)
    kinetic = port['inertia_kg_m2'] * port['omega_rad_s'] ** 2 / 2
    old_energy = span.EA_N * (OLD_STRETCH - 1) ** 2 * OLD_LENGTH_M / 2
    active = []
    for record in records:
        low = max(port['right_cut_m'], record['material_label_low_m'])
        if low < record['material_label_high_m']:
            active.append({**record, 'active_label_low_m': low,
                           'active_strain_energy_j': _interval_energy(
                               low, record['material_label_high_m'], record)})
    return {'time_s': time_s, 'mode': mode,
            'cell_conservative_fields': [list(cell) for cell in cells],
            'span_mass_kg': mass, 'span_momentum_kg_m_s': momentum,
            'span_mechanical_energy_j': span_energy,
            'reel_reference_length_m': length_m,
            'reel_radius_m': port['radius_m'],
            'reel_inertia_kg_m2': port['inertia_kg_m2'],
            'reel_angular_speed_rad_s': port['omega_rad_s'],
            'reel_angle_rad': angle_rad,
            'reaction_torque_nm': rates['reaction_torque_nm'],
            'reel_angular_momentum_kg_m2_s': (
                port['inertia_kg_m2'] * port['omega_rad_s']),
            'reel_kinetic_energy_j': kinetic,
            'old_wound_interval': {'material_label_low_m': S0_M,
                                   'material_label_high_m': S0_M + OLD_LENGTH_M,
                                   'retained_stretch': OLD_STRETCH,
                                   'retained_strain_energy_j': old_energy},
            'deposited_intervals': [dict(record) for record in records],
            'active_deposited_intervals': active,
            'newly_wound_strain_energy_j': new_energy_j,
            'owned_new_strain_energy_j': _active_energy(port['right_cut_m'], records),
            'total_mechanical_energy_j': span_energy + kinetic + old_energy + new_energy_j,
            'right_material_label_m': port['right_cut_m'],
            'right_reference_flux_m_s': port['right_reference_flux_m_s'],
            'right_stretch': port['right_stretch'],
            'right_donor_role': port['donor_role'],
            'integrated_left_flux': list(integrated['left_flux']),
            'integrated_right_flux': list(integrated['right_flux']),
            'integrated_right_energy_terms': list(integrated['right_energy_terms']),
            'integrated_drive_work_j': integrated['drive_work'],
            'integrated_angular_rhs_nm_s': integrated['angular_rhs'],
            'integrated_advected_angular_flux_nm_s': integrated['advected_angular_flux'],
            'integrated_reaction_torque_nm_s': integrated['reaction_torque']}


def run_matched_reaction_reversal(case: T2A9Case):
    if not isinstance(case, T2A9Case):
        raise ValueError('T2A9 requires a T2A9Case')
    dx = span.SPAN_LENGTH_M / case.cell_count
    cells = [span._conserved(*_exact(0.0, (i + .5) * dx)[1:])
             for i in range(case.cell_count)]
    length_m, angle_rad, new_energy_j = OLD_LENGTH_M, 0.0, 0.0
    records = []
    integrated = {'left_flux': [0.0] * 3, 'right_flux': [0.0] * 3,
                  'right_energy_terms': [0.0] * 3, 'drive_work': 0.0,
                  'angular_rhs': 0.0, 'advected_angular_flux': 0.0,
                  'reaction_torque': 0.0}
    mode, time_s, steps = 'wind', 0.0, 0
    snapshots = [_snapshot(time_s, cells, length_m, angle_rad, mode, records,
                           new_energy_j, integrated, dx)]
    initial = snapshots[0]
    initial_total_mass = initial['span_mass_kg'] + span.REFERENCE_LINE_MASS_KG_M
    maximums = {'mass': 0.0, 'momentum': 0.0, 'inventory': 0.0,
                'angular': 0.0, 'reel_energy': 0.0, 'combined_energy': 0.0,
                'storage_flux': 0.0, 'ownership': 0.0, 'courant': 0.0,
                'minimum_stretch': float('inf')}
    events = []
    observation_index = 0
    observations = (.01, .03)
    while time_s < HARD_HORIZON_S - 1e-14:
        if steps >= 5000:
            raise ValueError('T2A9 exceeded accepted-step budget')
        next_observation = (observations[observation_index]
                            if observation_index < len(observations)
                            else HARD_HORIZON_S)
        start = _rates(cells, length_m, time_s, dx, mode, records)
        h = min(next_observation - time_s,
                .99 * case.cfl_limit * dx / start['maximum_signal_m_s'])
        if h <= 1e-14:
            time_s = next_observation
            snapshots.append(_snapshot(time_s, cells, length_m, angle_rad,
                                       mode, records, new_energy_j, integrated, dx))
            observation_index += 1
            continue
        for _ in range(20):
            trial = _advance(cells, length_m, angle_rad, time_s, h, dx, mode, records)
            if trial['courant'] <= case.cfl_limit * (1 + 1e-12):
                break
            h /= 2
        else:
            raise ValueError('T2A9 failed reconstructed-stage CFL gate')
        for _ in range(20):
            predictor_crossed = (
                trial['second']['port']['right_reference_flux_m_s'] <= 0
                if mode == 'wind' else
                trial['second']['port']['right_cut_m'] >= S0_M)
            endpoint_crossed = (
                trial['final']['port']['right_reference_flux_m_s'] <= 0
                if mode == 'wind' else
                trial['final']['port']['right_cut_m'] >= S0_M)
            if not predictor_crossed or endpoint_crossed:
                break
            # A stage-only excursion guards the trial; it is not an event.
            h /= 2
            trial = _advance(cells, length_m, angle_rad, time_s, h, dx,
                             mode, records)
        else:
            raise ValueError('T2A9 predictor event guard could not shorten')
        q_start = start['port']['right_reference_flux_m_s']
        q_end = trial['final']['port']['right_reference_flux_m_s']
        cut_start = start['port']['right_cut_m']
        cut_end = trial['final']['port']['right_cut_m']
        event_type = ('FIRST_SPEED_REVERSAL' if mode == 'wind' and
                      q_start > 0 and q_end <= 0 else
                      'RETURN_TO_OLD_LAYER' if mode == 'release' and
                      cut_start < S0_M and cut_end >= S0_M else None)
        event_bracket = None
        if event_type:
            low, high = 0.0, h
            low_trial = None
            for _ in range(40):
                if high - low <= 1e-10:
                    break
                mid = (low + high) / 2
                candidate = _advance(cells, length_m, angle_rad, time_s,
                                     mid, dx, mode, records)
                value = (candidate['final']['port']['right_reference_flux_m_s']
                         if mode == 'wind' else
                         candidate['final']['port']['right_cut_m'] - S0_M)
                if (value > 0 if mode == 'wind' else value < 0):
                    low, low_trial = mid, candidate
                else:
                    high = mid
            upper = _advance(cells, length_m, angle_rad, time_s, high, dx,
                             mode, records)
            lower = (_advance(cells, length_m, angle_rad, time_s, low, dx,
                              mode, records) if low_trial is None else low_trial)
            lower_value = (lower['final']['port']['right_reference_flux_m_s']
                           if mode == 'wind' else
                           lower['final']['port']['right_cut_m'] - S0_M)
            upper_value = (upper['final']['port']['right_reference_flux_m_s']
                           if mode == 'wind' else
                           upper['final']['port']['right_cut_m'] - S0_M)
            if not (lower_value > 0 and upper_value <= 0 if mode == 'wind'
                    else lower_value < 0 and upper_value >= 0):
                raise ValueError('T2A9 event lacks opposite full-trial endpoint signs')
            event_bracket = [time_s + low, time_s + high]
            h, trial = ((high, upper) if mode == 'wind' else (low, lower))
        first, second = trial['first'], trial['second']
        old_mass, old_momentum, _ = fv._integrals(cells, dx)
        old_port = first['port']
        old_cut = old_port['right_cut_m']
        for key in ('left_flux', 'right_flux', 'right_energy_terms'):
            for index in range(3):
                integrated[key][index] += h * (first[key][index] + second[key][index]) / 2
        for key, stage_key in (('drive_work', 'drive_power_w'),
                               ('angular_rhs', 'angular_rhs_nm'),
                               ('advected_angular_flux', 'advected_angular_flux_nm'),
                               ('reaction_torque', 'reaction_torque_nm')):
            integrated[key] += h * (first[stage_key] + second[stage_key]) / 2
        cells, length_m, angle_rad = (trial['cells'], trial['length_m'],
                                      trial['angle_rad'])
        time_s += h
        steps += 1
        final_port = trial['final']['port']
        new_cut = final_port['right_cut_m']
        if mode == 'wind':
            if new_cut > old_cut + 1e-11:
                raise ValueError('T2A9 winding cut moved outward before reversal')
            record = _new_record(new_cut, old_cut)
            records.append(record)
            new_energy_j += _interval_energy(new_cut, old_cut, record)
        else:
            if new_cut < old_cut - 1e-11 or new_cut > S0_M + 1e-11:
                raise ValueError('T2A9 release crossed new inventory')
            new_energy_j -= _released_energy(old_cut, new_cut, records)
        new_mass, new_momentum, new_span_energy = fv._integrals(cells, dx)
        new_kinetic = final_port['inertia_kg_m2'] * final_port['omega_rad_s'] ** 2 / 2
        old_wound_energy = initial['old_wound_interval']['retained_strain_energy_j']
        total_energy = new_span_energy + new_kinetic + old_wound_energy + new_energy_j
        maximums['mass'] = max(maximums['mass'], abs(
            new_mass - old_mass + span.REFERENCE_LINE_MASS_KG_M * h *
            ((first['right_flux'][0] + second['right_flux'][0]) -
             (first['left_flux'][0] + second['left_flux'][0])) / 2))
        maximums['momentum'] = max(maximums['momentum'], abs(
            new_momentum - old_momentum + h *
            ((first['right_flux'][1] + second['right_flux'][1]) -
             (first['left_flux'][1] + second['left_flux'][1])) / 2))
        maximums['inventory'] = max(maximums['inventory'], abs(
            new_mass + span.REFERENCE_LINE_MASS_KG_M * length_m -
            initial_total_mass - span.REFERENCE_LINE_MASS_KG_M *
            integrated['left_flux'][0]))
        maximums['angular'] = max(maximums['angular'], abs(
            final_port['inertia_kg_m2'] * final_port['omega_rad_s'] -
            initial['reel_angular_momentum_kg_m2_s'] - integrated['angular_rhs']))
        maximums['reel_energy'] = max(maximums['reel_energy'], abs(
            new_kinetic + new_energy_j - initial['reel_kinetic_energy_j'] -
            integrated['drive_work'] - integrated['right_flux'][2]))
        maximums['combined_energy'] = max(maximums['combined_energy'], abs(
            total_energy - initial['total_mechanical_energy_j'] -
            integrated['left_flux'][2] - integrated['drive_work']))
        maximums['storage_flux'] = max(maximums['storage_flux'], abs(
            new_energy_j - integrated['right_energy_terms'][1]))
        maximums['courant'] = max(maximums['courant'], trial['courant'])
        maximums['minimum_stretch'] = min(
            maximums['minimum_stretch'], first['minimum_stretch'],
            second['minimum_stretch'], trial['final']['minimum_stretch'])
        # Exact ownership is checked at every committed state, separately
        # from quadrature of qW through the time integrator.
        maximums['ownership'] = max(maximums['ownership'], abs(
            new_energy_j - _active_energy(new_cut, records)))
        if event_type:
            events.append({'event_type': event_type, 'bracket_time_s': event_bracket,
                           'time_s': time_s, 'lower_endpoint_value': lower_value,
                           'upper_endpoint_value': upper_value,
                           'right_reference_flux_m_s': final_port['right_reference_flux_m_s'],
                           'right_material_label_m': new_cut})
            if mode == 'wind':
                mode = 'release'
                snapshots.append(_snapshot(time_s, cells, length_m, angle_rad,
                                           mode, records, new_energy_j,
                                           integrated, dx))
            else:
                snapshots.append(_snapshot(time_s, cells, length_m, angle_rad,
                                           mode, records, new_energy_j,
                                           integrated, dx))
                break
        elif abs(time_s - next_observation) < 1e-14:
            snapshots.append(_snapshot(time_s, cells, length_m, angle_rad,
                                       mode, records, new_energy_j, integrated, dx))
            observation_index += 1
    if [event['event_type'] for event in events] != [
            'FIRST_SPEED_REVERSAL', 'RETURN_TO_OLD_LAYER']:
        raise ValueError('T2A9 did not complete one reversal and one return')
    return {'model_id': MODEL_ID,
            'mode': 'matched_elastic_reaction_winding_release',
            'episode_outcome': 'RETURNED_TO_OLD_LAYER_WITHOUT_CONSUMING_IT',
            'reel_torque_role': 'reaction_not_applied_input',
            'reel_speed_role': 'algebraic_from_span_and_donor_stretch',
            'cell_count': case.cell_count, 'cfl_limit': case.cfl_limit,
            'accepted_steps': steps, 'snapshots': snapshots, 'events': events,
            'maximum_reconstructed_stage_courant': maximums['courant'],
            'minimum_used_stretch': maximums['minimum_stretch'],
            'maximum_mass_balance_defect_kg': maximums['mass'],
            'maximum_momentum_balance_defect_kg_m_s': maximums['momentum'],
            'maximum_combined_inventory_defect_kg': maximums['inventory'],
            'maximum_reel_angular_impulse_defect_nm_s': maximums['angular'],
            'maximum_reel_cumulative_energy_defect_j': maximums['reel_energy'],
            'maximum_combined_energy_defect_j': maximums['combined_energy'],
            'maximum_exact_storage_vs_transfer_flux_defect_j': maximums['storage_flux'],
            'maximum_new_strain_ownership_defect_j': maximums['ownership'],
            'limitations': ['matched synthetic standing wave and deposited strain',
                            'reaction torque without applied drive or arbitrary release',
                            'no slack, contact, full T2/T3 or physical validation']}
