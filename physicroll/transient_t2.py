"""Bounded torque-driven elastic span and right-reel transfer prototype.

This first integrated T2 increment has an explicit, idealized dissipative
release transition. Its inputs are declared histories, never exact-oracle
callbacks. The span has a fixed spatial domain and one driven reel; roll-bite
contact and the left reel are subsequent interface increments.
"""

from dataclasses import dataclass
import math

from . import transient_t2a5 as span
from . import transient_t2a6 as reel
from . import transient_t2a7 as geometry
from . import transient_t2a8 as fv


MODEL_ID = 'T2_TORQUE_DRIVEN_ELASTIC_RIGHT_REEL_IDEAL_PICKUP_V1'


@dataclass(frozen=True)
class WoundRecord:
    low_label_m: float
    high_label_m: float
    retained_stretch: float

    def __post_init__(self):
        if (any(type(x) not in (int, float) for x in (self.low_label_m,
                self.high_label_m, self.retained_stretch)) or
                not all(math.isfinite(x) for x in (self.low_label_m,
                self.high_label_m, self.retained_stretch)) or
                self.high_label_m <= self.low_label_m or
                self.retained_stretch <= 1):
            raise ValueError('T2 wound record requires ordered finite labels and taut stretch')


@dataclass(frozen=True)
class T2Episode:
    cell_count: int
    duration_s: float
    initial_conserved_fields: tuple  # cell-average (1/stretch, mu*velocity/stretch)
    initial_cut_label_m: float
    initial_reel_length_m: float
    initial_reel_omega_rad_s: float
    initial_records: tuple  # ordered from inner (high label) to outer (low label)
    left_boundary_mode: str  # fixed or incoming_characteristic
    left_incoming_history: tuple  # ((time_s, incoming_m_s), ...), empty if fixed
    applied_torque_history: tuple  # ((time_s, torque_nm), ...)
    observation_times_s: tuple
    stop_cut_label_m: float
    cfl_limit: float = span.CFL_LIMIT
    initial_phase: str = 'wind'  # wind or release

    def __post_init__(self):
        if type(self.cell_count) is not int or self.cell_count not in (64, 128, 256):
            raise ValueError('T2 requires a bounded frozen spatial grid')
        if (type(self.cfl_limit) not in (float, int) or self.cfl_limit not in
                (span.CFL_LIMIT, span.CFL_LIMIT / 2, span.CFL_LIMIT / 4)):
            raise ValueError('T2 requires a bounded frozen CFL grid')
        numbers = (self.duration_s, self.initial_cut_label_m,
                   self.initial_reel_length_m, self.initial_reel_omega_rad_s,
                   self.stop_cut_label_m)
        if (any(type(x) not in (int, float) or not math.isfinite(x)
                for x in numbers) or self.duration_s < 1e-9 or
                self.duration_s > .1 or self.initial_reel_length_m <= 0):
            raise ValueError('T2 requires positive finite bounded episode and inventory')
        if (type(self.initial_conserved_fields) is not tuple or
                len(self.initial_conserved_fields) != self.cell_count or
                any(type(item) is not tuple or len(item) != 2 or
                    any(type(x) not in (int, float) or not math.isfinite(x)
                        for x in item) or item[0] <= 0 or item[0] >= 1 or
                    abs(item[1] / (span.REFERENCE_LINE_MASS_KG_M * item[0])) >=
                    span.REFERENCE_WAVE_SPEED_M_S / item[0]
                    for item in self.initial_conserved_fields)):
            raise ValueError('T2 initial span must be taut and subsonic')
        if (type(self.initial_records) is not tuple or not self.initial_records or
                any(not isinstance(item, WoundRecord) for item in self.initial_records)):
            raise ValueError('T2 requires original retained winding records')
        records = self.initial_records
        if (abs(records[-1].low_label_m - self.initial_cut_label_m) > 1e-12 or
                abs(sum(item.high_label_m - item.low_label_m for item in records) -
                    self.initial_reel_length_m) > 1e-12 or
                any(abs(previous.low_label_m - following.high_label_m) > 1e-12
                    for previous, following in zip(records, records[1:]))):
            raise ValueError('T2 initial winding records do not own the declared inventory')
        if self.left_boundary_mode not in ('fixed', 'incoming_characteristic'):
            raise ValueError('T2 left boundary mode is unsupported')
        if self.initial_phase not in ('wind', 'release'):
            raise ValueError('T2 initial transfer phase is unsupported')
        if (self.initial_phase == 'wind' and self.initial_reel_omega_rad_s <= 0 or
                self.initial_phase == 'release' and self.initial_reel_omega_rad_s >= 0):
            raise ValueError('T2 initial phase disagrees with angular speed')
        if self.initial_phase == 'wind' and self.stop_cut_label_m > self.initial_cut_label_m:
            raise ValueError('T2 winding-return stop must not exceed initial cut')
        if self.initial_phase == 'release' and self.stop_cut_label_m <= self.initial_cut_label_m:
            raise ValueError('T2 release stop must follow initial cut')
        if (self.initial_phase == 'release' and
                self.stop_cut_label_m >= records[0].high_label_m):
            raise ValueError('T2 release stop must retain positive reel inventory')
        _check_history(self.applied_torque_history, self.duration_s, 'torque')
        if self.left_boundary_mode == 'incoming_characteristic':
            _check_history(self.left_incoming_history, self.duration_s, 'left incoming')
        elif self.left_incoming_history:
            raise ValueError('T2 fixed left end cannot also impose an incoming history')
        if (type(self.observation_times_s) is not tuple or
                any(type(t) not in (int, float) or not math.isfinite(t)
                    for t in self.observation_times_s) or
                any(not 0 < t < self.duration_s for t in self.observation_times_s) or
                any(a >= b for a, b in zip(self.observation_times_s,
                                           self.observation_times_s[1:]))):
            raise ValueError('T2 observation times must be ordered within duration')


def _check_history(history, duration_s, name):
    if (type(history) is not tuple or len(history) < 2 or
            any(type(item) is not tuple or len(item) not in (2, 3) or
                any(type(x) not in (int, float) or not math.isfinite(x)
                    for x in item) for item in history) or
            any(len(item) != len(history[0]) for item in history) or
            history[0][0] != 0 or history[-1][0] != duration_s or
            any(b[0] - a[0] < 1e-10 for a, b in
                zip(history, history[1:]))):
        raise ValueError(f'T2 {name} history must cover the episode with ordered finite knots')


def _history_value(history, time_s):
    if time_s < -1e-12 or time_s > history[-1][0] + 1e-12:
        raise ValueError('T2 history evaluated outside declared time')
    for first_knot, second_knot in zip(history, history[1:]):
        start, first = first_knot[:2]
        end, second = second_knot[:2]
        if time_s <= end + 1e-14:
            fraction = max(0.0, min(1.0, (time_s - start) / (end - start)))
            if len(first_knot) == 3:
                u = fraction
                h = end - start
                return ((2*u**3-3*u**2+1)*first + (u**3-2*u**2+u)*h*first_knot[2]
                        + (-2*u**3+3*u**2)*second + (u**3-u**2)*h*second_knot[2])
            return first + fraction * (second - first)
    return history[-1][1]


def _record_energy(low, high, stretch):
    return (high - low) * span.EA_N * (stretch - 1) ** 2 / 2


def _owned_energy(cut, records):
    return sum(_record_energy(max(cut, item.low_label_m), item.high_label_m,
                              item.retained_stretch)
               for item in records if item.high_label_m > cut)


def _donor(records, cut):
    # At an accepted layer boundary the next inner layer is the donor.
    for item in reversed(records):
        if item.low_label_m <= cut < item.high_label_m:
            return item
    if cut >= records[0].high_label_m:
        raise ValueError('T2 reel inventory depleted')
    if cut < records[-1].low_label_m - 1e-10:
        raise ValueError('T2 release cut left stored history')
    return records[-1]


def _next_donor_boundary(records, cut):
    return _donor(records, cut).high_label_m


def _characteristic(cell, sign):
    stretch, velocity = fv._primitive(cell)
    return velocity + sign * span.REFERENCE_WAVE_SPEED_M_S * stretch


def _require_subsonic(stretch, speed):
    if (not math.isfinite(stretch) or not math.isfinite(speed) or
            stretch <= 0 or abs(speed / stretch) >=
            span.REFERENCE_WAVE_SPEED_M_S):
        raise ValueError('T2 span state left finite positive subsonic domain')


def _port(cells, length_m, omega, time_s, phase, records, episode,
          frozen_donor=None):
    left_out = (3 * _characteristic(cells[0], 1) -
                _characteristic(cells[1], 1)) / 2
    if episode.left_boundary_mode == 'fixed':
        left_speed = 0.0
        left_stretch = left_out / span.REFERENCE_WAVE_SPEED_M_S
    else:
        incoming = _history_value(episode.left_incoming_history, time_s)
        left_speed = (left_out + incoming) / 2
        left_stretch = (left_out - incoming) / (2 * span.REFERENCE_WAVE_SPEED_M_S)
    right_out = (3 * _characteristic(cells[-1], -1) -
                 _characteristic(cells[-2], -1)) / 2
    radius, inertia = geometry._geometry(length_m)
    wound_speed = radius * omega
    cut = episode.initial_cut_label_m + episode.initial_reel_length_m - length_m
    if phase == 'wind':
        speed = wound_speed
        stretch = (speed - right_out) / span.REFERENCE_WAVE_SPEED_M_S
        donor_stretch = stretch
        q = speed / stretch
        donor_role = 'newly_deposited_span_state'
    else:
        # A trial uses the donor exposed at its accepted start. A layer
        # transition is committed only after its one-sided event root.
        donor_stretch = (frozen_donor if frozen_donor is not None else
                         _donor(records, cut).retained_stretch)
        q = wound_speed / donor_stretch
        stretch = right_out / (q - span.REFERENCE_WAVE_SPEED_M_S)
        speed = q * stretch
        donor_role = 'original_retained_record'
    if (not all(math.isfinite(x) for x in (
            left_speed, left_stretch, speed, stretch, donor_stretch, q)) or
            min(left_stretch, stretch, donor_stretch) <= 0 or
            abs(q) >= span.REFERENCE_WAVE_SPEED_M_S):
        raise ValueError('T2 port left finite positive subsonic domain')
    _require_subsonic(left_stretch, left_speed)
    _require_subsonic(stretch, speed)
    tension = span.EA_N * (stretch - 1)
    dissipation = (max(0.0, -q) * (span.EA_N -
                   span.REFERENCE_LINE_MASS_KG_M * q ** 2) *
                   (stretch - donor_stretch) ** 2 / 2
                   if phase == 'release' else 0.0)
    return {'left_state': span._conserved(left_stretch, left_speed),
            'right_state': span._conserved(stretch, speed),
            'left_speed_m_s': left_speed, 'left_stretch': left_stretch,
            'span_stretch': stretch, 'span_speed_m_s': speed,
            'donor_stretch': donor_stretch, 'donor_role': donor_role,
            'wound_speed_m_s': wound_speed, 'reference_flux_m_s': q,
            'tension_n': tension, 'dissipated_power_w': dissipation,
            'radius_m': radius, 'inertia_kg_m2': inertia, 'omega_rad_s': omega,
            'cut_label_m': cut, 'outgoing_characteristic_m_s': right_out}


def _rates(cells, length_m, omega, time_s, phase, records, episode,
           frozen_donor=None):
    port = _port(cells, length_m, omega, time_s, phase, records, episode,
                 frozen_donor)
    left_flux = fv._physical_flux(port['left_state'])
    right_flux = fv._physical_flux(port['right_state'])
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
    fluxes = [left_flux]
    signal = 0.0
    minimum_stretch = min(port['left_stretch'], port['span_stretch'])
    for cell in cells:
        stretch, speed = fv._primitive(cell)
        _require_subsonic(stretch, speed)
        minimum_stretch = min(minimum_stretch, stretch)
        signal = max(signal, abs(speed) + stretch * span.REFERENCE_WAVE_SPEED_M_S)
    for index in range(len(cells) - 1):
        left_trace = tuple(cells[index][j] + slopes[index][j] / 2 for j in (0, 1))
        right_trace = tuple(cells[index + 1][j] - slopes[index + 1][j] / 2
                            for j in (0, 1))
        for trace in (left_trace, right_trace):
            trace_stretch, trace_speed = fv._primitive(trace)
            _require_subsonic(trace_stretch, trace_speed)
            minimum_stretch = min(minimum_stretch, trace_stretch)
        face_flux, face_signal = fv._interface_flux(left_trace, right_trace)
        fluxes.append(face_flux)
        signal = max(signal, face_signal)
    fluxes.append(right_flux)
    for state in (port['left_state'], port['right_state']):
        stretch, speed = fv._primitive(state)
        signal = max(signal, abs(speed) + stretch * span.REFERENCE_WAVE_SPEED_M_S)
    dx = span.SPAN_LENGTH_M / episode.cell_count
    field_rates = [tuple(-(fluxes[index + 1][j] - fluxes[index][j]) / dx
                         for j in (0, 1)) for index in range(len(cells))]
    torque = _history_value(episode.applied_torque_history, time_s)
    q = port['reference_flux_m_s']
    radius = port['radius_m']
    mu = span.REFERENCE_LINE_MASS_KG_M
    omega_rate = ((torque - radius * port['tension_n'] +
                   mu * q * radius * (port['span_speed_m_s'] -
                                      port['wound_speed_m_s'])) /
                  port['inertia_kg_m2'])
    strain_flux = q * span.EA_N * (port['span_stretch'] - 1) ** 2 / 2
    kinetic_flux = q * mu * port['span_speed_m_s'] ** 2 / 2
    traction_work = port['tension_n'] * port['span_speed_m_s']
    return {'field_rates': field_rates,
            'reel_rates': (q, omega_rate, omega),
            'left_flux': left_flux, 'right_flux': right_flux,
            'right_energy_terms': (kinetic_flux, strain_flux, traction_work),
            'stored_flux_w': q * span.EA_N * (port['donor_stretch'] - 1) ** 2 / 2,
            'drive_power_w': torque * omega,
            'angular_rhs_nm': torque - radius * port['tension_n'] +
                              mu * q * radius * port['span_speed_m_s'],
            'applied_torque_nm': torque,
            'dissipated_power_w': port['dissipated_power_w'],
            'port': port, 'minimum_stretch': minimum_stretch,
            'maximum_signal_m_s': signal}


def _advance(cells, length_m, omega, angle, time_s, step_s, phase,
             records, episode):
    frozen_donor = (_donor(records, episode.initial_cut_label_m +
                    episode.initial_reel_length_m - length_m).retained_stretch
                    if phase == 'release' else None)
    first = _rates(cells, length_m, omega, time_s, phase, records, episode,
                   frozen_donor)
    predicted = [tuple(cell[j] + step_s * rate[j] for j in (0, 1))
                 for cell, rate in zip(cells, first['field_rates'])]
    predicted_reel = tuple(value + step_s * rate for value, rate in zip(
        (length_m, omega, angle), first['reel_rates']))
    second = _rates(predicted, predicted_reel[0], predicted_reel[1],
                    time_s + step_s, phase, records, episode, frozen_donor)
    updated = [tuple((cell[j] + trial[j] + step_s * rate[j]) / 2
                     for j in (0, 1))
               for cell, trial, rate in zip(cells, predicted, second['field_rates'])]
    updated_reel = tuple((original + trial + step_s * rate) / 2
                         for original, trial, rate in zip(
                             (length_m, omega, angle), predicted_reel,
                             second['reel_rates']))
    final = _rates(updated, updated_reel[0], updated_reel[1],
                   time_s + step_s, phase, records, episode, frozen_donor)
    dx = span.SPAN_LENGTH_M / episode.cell_count
    courant = step_s * max(first['maximum_signal_m_s'],
                           second['maximum_signal_m_s'],
                           final['maximum_signal_m_s']) / dx
    return {'cells': updated, 'length_m': updated_reel[0],
            'omega_rad_s': updated_reel[1], 'angle_rad': updated_reel[2],
            'first': first, 'second': second, 'final': final,
            'courant': courant}


def _state(time_s, cells, length_m, omega, angle, phase, records,
           initial_records, heat_j, integrated, episode):
    """Copy an accepted state; sampling itself never advances ownership."""
    dx = span.SPAN_LENGTH_M / episode.cell_count
    span_mass, span_momentum, span_energy = fv._integrals(cells, dx)
    radius, inertia = geometry._geometry(length_m)
    cut = episode.initial_cut_label_m + episode.initial_reel_length_m - length_m
    owned = _owned_energy(cut, records)
    kinetic = inertia * omega ** 2 / 2
    port = _port(cells, length_m, omega, time_s, phase, records, episode)
    return {'time_s': time_s, 'phase': phase,
            'cell_conservative_fields': [list(item) for item in cells],
            'span_mass_kg': span_mass, 'span_momentum_kg_m_s': span_momentum,
            'span_mechanical_energy_j': span_energy,
            'reel_reference_length_m': length_m,
            'reel_radius_m': radius, 'reel_inertia_kg_m2': inertia,
            'reel_angular_speed_rad_s': omega, 'reel_angle_rad': angle,
            'reel_angular_momentum_kg_m2_s': inertia * omega,
            'reel_kinetic_energy_j': kinetic,
            'initial_record_count': len(initial_records),
            'accepted_record_count': len(records),
            'ordered_original_wound_records': [
                {'low_label_m': item.low_label_m,
                 'high_label_m': item.high_label_m,
                 'retained_stretch': item.retained_stretch}
                for item in records],
            'owned_wound_strain_energy_j': owned,
            'accumulated_dissipated_energy_j': heat_j,
            'total_mechanical_energy_j': span_energy + kinetic + owned,
            'total_energy_including_dissipation_j': span_energy + kinetic + owned + heat_j,
            'right_cut_label_m': cut,
            'right_span_stretch': port['span_stretch'],
            'right_donor_stretch': port['donor_stretch'],
            'right_span_speed_m_s': port['span_speed_m_s'],
            'right_wound_speed_m_s': port['wound_speed_m_s'],
            'right_reference_flux_m_s': port['reference_flux_m_s'],
            'right_donor_role': port['donor_role'],
            'applied_torque_nm': _history_value(episode.applied_torque_history,
                                                time_s),
            'integrated_left_flux': list(integrated['left_flux']),
            'integrated_right_flux': list(integrated['right_flux']),
            'integrated_right_energy_terms': list(integrated['right_energy_terms']),
            'integrated_drive_work_j': integrated['drive_work'],
            'integrated_angular_rhs_nm_s': integrated['angular_rhs'],
            'integrated_stored_flux_j': integrated['stored_flux'],
            'integrated_dissipated_power_j': integrated['dissipation']}


def _first_future_knot(time_s, *histories):
    return min(item[0] for history in histories for item in history
               if item[0] > time_s + 1e-13)


def _event_value(trial, kind, threshold):
    if kind in ('reversal', 'unsupported_reverse_to_wind'):
        return trial['omega_rad_s']
    if kind in ('donor_boundary', 'cut_limit'):
        return trial['final']['port']['cut_label_m'] - threshold
    if kind == 'tension_zero':
        return trial['final']['minimum_stretch'] - 1
    raise ValueError('unsupported T2 event')


def _locate_event(cells, length_m, omega, angle, time_s, h, phase,
                  records, episode, kind, threshold):
    """Return a complete-trial bracket and the admissible committed side."""
    low, high = 0.0, h
    first_trial = _advance(cells, length_m, omega, angle, time_s, low,
                           phase, records, episode)
    upper_trial = _advance(cells, length_m, omega, angle, time_s, high,
                           phase, records, episode)
    direction = -1 if kind in ('donor_boundary', 'cut_limit',
                               'unsupported_reverse_to_wind') else 1
    if direction * _event_value(first_trial, kind, threshold) <= 0 or (
            direction * _event_value(upper_trial, kind, threshold) > 0):
        raise ValueError('T2 event has no opposite full-trial endpoint signs')
    lower_trial = first_trial
    for _ in range(44):
        if high - low <= 1e-12:
            break
        middle = (low + high) / 2
        candidate = _advance(cells, length_m, omega, angle, time_s,
                             middle, phase, records, episode)
        value = direction * _event_value(candidate, kind, threshold)
        if value > 0:
            low, lower_trial = middle, candidate
        else:
            high, upper_trial = middle, candidate
    if kind in ('reversal', 'donor_boundary', 'unsupported_reverse_to_wind'):
        selected_h, selected = high, upper_trial
    else:
        selected_h, selected = low, lower_trial
    cut_residual = (selected['final']['port']['cut_label_m'] - threshold
                    if kind == 'donor_boundary' else None)
    if (cut_residual is not None and
            abs(cut_residual) > max(32 * math.ulp(threshold), 1e-13)):
        raise ValueError('T2 donor endpoint did not localize within label tolerance')
    storage_ownership_error = None
    if kind == 'donor_boundary':
        start_cut = episode.initial_cut_label_m + episode.initial_reel_length_m - length_m
        old_donor = _donor(records, start_cut)
        index = records.index(old_donor)
        if index == 0:
            raise ValueError('T2 donor boundary exhausts reel inventory')
        following = records[index - 1]
        storage_ownership_error = cut_residual * span.EA_N * (
            (following.retained_stretch - 1) ** 2 -
            (old_donor.retained_stretch - 1) ** 2) / 2
        if abs(storage_ownership_error) > 1e-12:
            raise ValueError('T2 donor event storage ownership error exceeds budget')
    return {'kind': kind, 'bracket_time_s': [time_s + low, time_s + high],
            'lower_endpoint_value': _event_value(lower_trial, kind, threshold),
            'upper_endpoint_value': _event_value(upper_trial, kind, threshold),
            'cut_endpoint_error_m': cut_residual,
            'storage_ownership_error_bound_j': storage_ownership_error,
            'step_s': selected_h, 'trial': selected, 'threshold': threshold}


def _winding_packets(old_cut, new_cut, h, first, second):
    transfers = [h * first['port']['reference_flux_m_s'] / 2,
                 h * second['port']['reference_flux_m_s'] / 2]
    stretches = [first['port']['span_stretch'], second['port']['span_stretch']]
    total = old_cut - new_cut
    if abs(total) < 1e-14 and abs(sum(transfers)) < 1e-14:
        return [], 0.0  # no represented material at the computed speed-zero event
    if total <= 0 or abs(sum(transfers) - total) > 1e-11:
        raise ValueError('T2 accepted winding label flux disagrees with inventory')
    if min(transfers) <= 0:
        # The event root can put its final stage a few ulps past zero. No
        # invented stretch is deposited: the nonzero stage owns the packet,
        # and the lost quadrature energy is bounded and reported separately.
        stage_energy = sum(_record_energy(0, transfer, stretch)
                           for transfer, stretch in zip(transfers, stretches))
        if min(transfers) < -1e-12 or stage_energy <= 0:
            raise ValueError('T2 winding stage reversed before accepted event')
        owner_stretch = stretches[0] if transfers[0] > 0 else stretches[1]
        discrepancy = _record_energy(new_cut, old_cut, owner_stretch) - stage_energy
        if abs(discrepancy) > 1e-12:
            raise ValueError('T2 zero-stage packet quadrature exceeds energy budget')
        return [WoundRecord(new_cut, old_cut, owner_stretch)], discrepancy
    boundary = old_cut - transfers[0]
    if abs(boundary - transfers[1] - new_cut) > 1e-11:
        raise ValueError('T2 winding stage packet labels are not contiguous')
    return [WoundRecord(boundary, old_cut, stretches[0]),
            WoundRecord(new_cut, boundary, stretches[1])], 0.0


def run_torque_driven_episode(episode: T2Episode):
    """Integrate a declared bounded episode with accepted-only wound history."""
    if not isinstance(episode, T2Episode):
        raise ValueError('T2 requires a validated T2Episode')
    cells = [tuple(item) for item in episode.initial_conserved_fields]
    length_m = episode.initial_reel_length_m
    omega = episode.initial_reel_omega_rad_s
    angle = heat_j = time_s = 0.0
    phase = episode.initial_phase
    records = list(episode.initial_records)
    integrated = {'left_flux': [0.0] * 3, 'right_flux': [0.0] * 3,
                  'right_energy_terms': [0.0] * 3,
                  'drive_work': 0.0, 'angular_rhs': 0.0,
                  'stored_flux': 0.0, 'dissipation': 0.0}
    initial = _state(time_s, cells, length_m, omega, angle, phase, records,
                     episode.initial_records, heat_j, integrated, episode)
    snapshots = [initial]
    accepted_states = [initial]
    events = []
    winding_packet_quadrature_error_j = 0.0
    initial_combined_mass = initial['span_mass_kg'] + (
        span.REFERENCE_LINE_MASS_KG_M * length_m)
    initial_reel_energy = (initial['reel_kinetic_energy_j'] +
                           initial['owned_wound_strain_energy_j'])
    maximums = {'courant': 0.0, 'mass': 0.0, 'momentum': 0.0,
                'combined_inventory': 0.0, 'angular': 0.0,
                'reel_energy': 0.0, 'combined_energy': 0.0,
                'storage_flux': 0.0, 'minimum_stretch': float('inf')}
    observation_index = 0
    outcome = None
    dx = span.SPAN_LENGTH_M / episode.cell_count
    while time_s < episode.duration_s - 1e-13:
        if len(accepted_states) > 6000:
            raise ValueError('T2 exceeded accepted-step budget')
        start = _rates(cells, length_m, omega, time_s, phase, records, episode)
        if start['minimum_stretch'] <= 1:
            raise ValueError('T2 committed state has lost tautness')
        h = min(episode.duration_s - time_s,
                _first_future_knot(time_s, episode.applied_torque_history,
                                   episode.left_incoming_history if
                                   episode.left_boundary_mode ==
                                   'incoming_characteristic' else
                                   episode.applied_torque_history) - time_s,
                .99 * episode.cfl_limit * dx / start['maximum_signal_m_s'])
        if h <= 1e-13:
            raise ValueError('T2 step collapsed at forcing or event boundary')
        for _ in range(20):
            trial = _advance(cells, length_m, omega, angle, time_s, h,
                             phase, records, episode)
            if trial['courant'] <= episode.cfl_limit * (1 + 1e-12):
                break
            h /= 2
        else:
            raise ValueError('T2 failed reconstructed-stage CFL gate')
        for _ in range(20):
            stage = trial['second']
            endpoint = trial['final']
            predictor_only = (
                (phase == 'wind' and stage['port']['omega_rad_s'] <= 0 and
                 trial['omega_rad_s'] > 0) or
                (phase == 'release' and stage['port']['omega_rad_s'] >= 0 and
                 trial['omega_rad_s'] < 0) or
                (phase == 'release' and stage['port']['cut_label_m'] >=
                 _next_donor_boundary(records, start['port']['cut_label_m']) and
                 endpoint['port']['cut_label_m'] <
                 _next_donor_boundary(records, start['port']['cut_label_m'])) or
                (stage['minimum_stretch'] <= 1 and
                 endpoint['minimum_stretch'] > 1))
            if not predictor_only:
                break
            h /= 2
            trial = _advance(cells, length_m, omega, angle, time_s, h,
                             phase, records, episode)
        else:
            raise ValueError('T2 predictor-only event guard could not shorten')
        for _ in range(24):
            candidate_events = []
            if phase == 'wind' and omega > 0 and trial['omega_rad_s'] <= 0:
                candidate_events.append(('reversal', 0.0))
            if phase == 'release':
                if omega < 0 and trial['omega_rad_s'] >= 0:
                    candidate_events.append(('unsupported_reverse_to_wind', 0.0))
                cut = start['port']['cut_label_m']
                new_cut = trial['final']['port']['cut_label_m']
                boundary = _next_donor_boundary(records, cut)
                if (cut < boundary and new_cut >= boundary and
                        boundary < episode.stop_cut_label_m - 1e-13):
                    candidate_events.append(('donor_boundary', boundary))
                if cut < episode.stop_cut_label_m and new_cut >= episode.stop_cut_label_m:
                    candidate_events.append(('cut_limit', episode.stop_cut_label_m))
            if trial['final']['minimum_stretch'] <= 1:
                candidate_events.append(('tension_zero', 1.0))
            located = [_locate_event(cells, length_m, omega, angle, time_s, h,
                                     phase, records, episode, kind, threshold)
                       for kind, threshold in candidate_events]
            event = min(located, key=lambda item: (
                item['step_s'], 0 if item['kind'] == 'cut_limit' else 1)) if located else None
            if event:
                h, trial = event['step_s'], event['trial']
                if h <= 0:
                    raise ValueError('T2 event step collapsed')
            first, second = trial['first'], trial['second']
            wrong_phase = any(
                (phase == 'wind' and rates['port']['reference_flux_m_s'] < -1e-9) or
                (phase == 'release' and rates['port']['reference_flux_m_s'] > 1e-9)
                for rates in (first, second))
            predictor_only_boundary = (
                phase == 'release' and second['port']['cut_label_m'] >=
                _next_donor_boundary(records, start['port']['cut_label_m']) and
                trial['final']['port']['cut_label_m'] <
                _next_donor_boundary(records, start['port']['cut_label_m']))
            predictor_only_tension = (second['minimum_stretch'] <= 1 and
                                      trial['final']['minimum_stretch'] > 1)
            if not (wrong_phase or predictor_only_boundary or predictor_only_tension):
                break
            h /= 2
            if h <= 1e-13:
                raise ValueError('T2 phase or event retry collapsed')
            trial = _advance(cells, length_m, omega, angle, time_s, h,
                             phase, records, episode)
        else:
            raise ValueError('T2 phase or event retry budget exhausted')
        old_mass, old_momentum, _ = fv._integrals(cells, dx)
        old_cut = first['port']['cut_label_m']
        for name in ('left_flux', 'right_flux', 'right_energy_terms'):
            for j in range(3):
                integrated[name][j] += h * (first[name][j] + second[name][j]) / 2
        for name, stage_key in (('drive_work', 'drive_power_w'),
                                ('angular_rhs', 'angular_rhs_nm'),
                                ('stored_flux', 'stored_flux_w'),
                                ('dissipation', 'dissipated_power_w')):
            integrated[name] += h * (first[stage_key] + second[stage_key]) / 2
        heat_j = integrated['dissipation']
        cells = trial['cells']
        length_m = trial['length_m']
        omega = trial['omega_rad_s']
        angle = trial['angle_rad']
        time_s += h
        new_cut = episode.initial_cut_label_m + episode.initial_reel_length_m - length_m
        if phase == 'wind':
            packets, error_j = _winding_packets(old_cut, new_cut, h, first, second)
            records.extend(packets)
            winding_packet_quadrature_error_j += abs(error_j)
        elif new_cut < old_cut - 1e-12:
            raise ValueError('T2 release consumed negative reference length')
        state = _state(time_s, cells, length_m, omega, angle, phase, records,
                       episode.initial_records, heat_j, integrated, episode)
        new_mass, new_momentum = state['span_mass_kg'], state['span_momentum_kg_m_s']
        maximums['courant'] = max(maximums['courant'], trial['courant'])
        maximums['minimum_stretch'] = min(
            maximums['minimum_stretch'], first['minimum_stretch'],
            second['minimum_stretch'], trial['final']['minimum_stretch'])
        maximums['mass'] = max(maximums['mass'], abs(
            new_mass - old_mass + span.REFERENCE_LINE_MASS_KG_M * h *
            ((first['right_flux'][0] + second['right_flux'][0]) -
             (first['left_flux'][0] + second['left_flux'][0])) / 2))
        maximums['momentum'] = max(maximums['momentum'], abs(
            new_momentum - old_momentum + h *
            ((first['right_flux'][1] + second['right_flux'][1]) -
             (first['left_flux'][1] + second['left_flux'][1])) / 2))
        maximums['combined_inventory'] = max(
            maximums['combined_inventory'], abs(
                new_mass + span.REFERENCE_LINE_MASS_KG_M * length_m -
                initial_combined_mass - span.REFERENCE_LINE_MASS_KG_M *
                integrated['left_flux'][0]))
        maximums['angular'] = max(maximums['angular'], abs(
            state['reel_angular_momentum_kg_m2_s'] -
            initial['reel_angular_momentum_kg_m2_s'] - integrated['angular_rhs']))
        maximums['reel_energy'] = max(maximums['reel_energy'], abs(
            state['reel_kinetic_energy_j'] + state['owned_wound_strain_energy_j'] +
            heat_j - initial_reel_energy - integrated['drive_work'] -
            integrated['right_flux'][2]))
        maximums['combined_energy'] = max(maximums['combined_energy'], abs(
            state['total_energy_including_dissipation_j'] -
            initial['total_energy_including_dissipation_j'] -
            integrated['left_flux'][2] - integrated['drive_work']))
        maximums['storage_flux'] = max(maximums['storage_flux'], abs(
            state['owned_wound_strain_energy_j'] -
            initial['owned_wound_strain_energy_j'] - integrated['stored_flux']))
        accepted_states.append(state)
        if event:
            entry = {key: value for key, value in event.items()
                     if key not in ('trial', 'step_s')}
            entry['time_s'] = time_s
            entry['cut_label_m'] = new_cut
            entry['omega_rad_s'] = omega
            events.append(entry)
            if event['kind'] == 'reversal':
                phase = 'release'
                state = _state(time_s, cells, length_m, omega, angle,
                               phase, records, episode.initial_records,
                               heat_j, integrated, episode)
                accepted_states[-1] = state
                snapshots.append(state)
            elif event['kind'] == 'donor_boundary':
                pass
            else:
                outcome = ({'tension_zero': 'STOPPED_AT_FIRST_TENSION_ZERO',
                            'cut_limit': 'STOPPED_AT_DECLARED_CUT',
                            'unsupported_reverse_to_wind':
                                'STOPPED_AT_UNSUPPORTED_SECOND_REVERSAL'}[
                                    event['kind']])
                snapshots.append(state)
        while (observation_index < len(episode.observation_times_s) and
               episode.observation_times_s[observation_index] <= time_s + 1e-13):
            sampled = state.copy()
            sampled['requested_observation_time_s'] = (
                episode.observation_times_s[observation_index])
            sampled['observation_role'] = 'first_accepted_state_at_or_after_request'
            snapshots.append(sampled)
            observation_index += 1
        if outcome:
            break
    if outcome is None:
        outcome = 'COMPLETED_DECLARED_DURATION'
        if snapshots[-1]['time_s'] < time_s - 1e-12:
            snapshots.append(accepted_states[-1])
    return {'model_id': MODEL_ID,
            'mode': 'torque_driven_elastic_span_right_reel_ideal_pickup',
            'episode_outcome': outcome,
            'torque_role': 'prescribed_input',
            'span_and_reel_speed_role': 'predicted_from_coupled_dynamics',
            'left_boundary_role': episode.left_boundary_mode,
            'observation_role': 'first_accepted_state_at_or_after_request',
            'pickup_closure_role': 'idealized_dissipative_not_physically_validated',
            'cell_count': episode.cell_count,
            'cfl_limit': episode.cfl_limit,
            'snapshots': snapshots, 'accepted_states': accepted_states,
            'events': events,
            'cumulative_winding_packet_quadrature_error_bound_j':
                winding_packet_quadrature_error_j,
            'cumulative_donor_endpoint_storage_error_bound_j': sum(
                abs(item['storage_ownership_error_bound_j']) for item in events
                if item['kind'] == 'donor_boundary'),
            'original_initial_records': [item.__dict__ for item in episode.initial_records],
            'maximum_reconstructed_stage_courant': maximums['courant'],
            'minimum_used_stretch': maximums['minimum_stretch'],
            'maximum_mass_balance_defect_kg': maximums['mass'],
            'maximum_momentum_balance_defect_kg_m_s': maximums['momentum'],
            'maximum_combined_inventory_defect_kg': maximums['combined_inventory'],
            'maximum_reel_angular_impulse_defect_nm_s': maximums['angular'],
            'maximum_reel_cumulative_energy_defect_j': maximums['reel_energy'],
            'maximum_combined_energy_defect_j': maximums['combined_energy'],
            'maximum_exact_storage_vs_transfer_flux_defect_j': maximums['storage_flux'],
            'limitations': ['one reel and a fixed spatial elastic span; no roll contact',
                            'idealized transfer contact and frozen retained strain',
                            'taut subsonic only; slack and site validation unsupported']}
