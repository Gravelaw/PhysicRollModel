"""Pre-engaged two-reel elastic-span prototype with no boundary events.

Both reels are driven by independent, declared time-only torques. Each local
angular coordinate is winding-positive. This narrow increment rejects phase
changes, donor changes, slack and reel depletion rather than continuing them
under a wrong boundary law. The existing integrated one-reel solver owns its
own eventful release contract.
"""

from dataclasses import dataclass
import math

from . import transient_t2 as single
from . import transient_t2a5 as span
from . import transient_t2a7 as geometry
from . import transient_t2a8 as fv


MODEL_ID = 'T2_TWO_REEL_PREENGAGED_ELASTIC_SPAN_IDEAL_PICKUP_V1'


@dataclass(frozen=True)
class ReelEnd:
    initial_local_cut_m: float
    initial_reference_length_m: float
    initial_omega_rad_s: float
    initial_records: tuple
    applied_torque_history: tuple
    phase: str

    def check(self, duration_s):
        if (any(type(x) not in (int, float) or not math.isfinite(x) for x in
                (self.initial_local_cut_m, self.initial_reference_length_m,
                 self.initial_omega_rad_s)) or
                self.initial_reference_length_m <= 0 or
                self.phase not in ('wind', 'release') or
                (self.phase == 'wind' and self.initial_omega_rad_s <= 0) or
                (self.phase == 'release' and self.initial_omega_rad_s >= 0)):
            raise ValueError('T2 two-reel endpoint has invalid inventory or phase')
        if (type(self.initial_records) is not tuple or not self.initial_records or
                any(not isinstance(item, single.WoundRecord)
                    for item in self.initial_records)):
            raise ValueError('T2 two-reel endpoint needs immutable wound records')
        if (abs(self.initial_records[-1].low_label_m - self.initial_local_cut_m) >
                1e-12 or abs(sum(item.high_label_m-item.low_label_m for item in
                                    self.initial_records) -
                              self.initial_reference_length_m) > 1e-12 or
                any(abs(a.low_label_m-b.high_label_m) > 1e-12 for a, b in
                    zip(self.initial_records, self.initial_records[1:]))):
            raise ValueError('T2 two-reel records do not own their local interval')
        single._check_history(self.applied_torque_history, duration_s, 'torque')
        if any(len(knot) != 2 for knot in self.applied_torque_history):
            raise ValueError('T2 two-reel requires linear torque forcing knots')


@dataclass(frozen=True)
class TwoReelEpisode:
    cell_count: int
    duration_s: float
    initial_conserved_fields: tuple
    left: ReelEnd
    right: ReelEnd
    observation_times_s: tuple = ()
    cfl_limit: float = span.CFL_LIMIT

    def __post_init__(self):
        if (type(self.cell_count) is not int or self.cell_count not in
                (64, 128, 256) or type(self.duration_s) not in (int, float) or
                not math.isfinite(self.duration_s) or
                not 1e-9 <= self.duration_s <= .2 or
                type(self.cfl_limit) not in (int, float) or
                self.cfl_limit not in (span.CFL_LIMIT, span.CFL_LIMIT/2,
                                       span.CFL_LIMIT/4)):
            raise ValueError('T2 two-reel episode exceeds frozen mesh/time bounds')
        if not isinstance(self.left, ReelEnd) or not isinstance(self.right, ReelEnd):
            raise ValueError('T2 two-reel episode requires both named ends')
        self.left.check(self.duration_s)
        self.right.check(self.duration_s)
        fields = self.initial_conserved_fields
        mu, c = span.REFERENCE_LINE_MASS_KG_M, span.REFERENCE_WAVE_SPEED_M_S
        if (type(fields) is not tuple or len(fields) != self.cell_count or
                any(type(item) is not tuple or len(item) != 2 or
                    any(type(x) not in (int, float) or not math.isfinite(x)
                        for x in item) or item[0] <= 0 or item[0] >= 1 or
                    abs(item[1] / (mu*item[0])) >= c/item[0] for item in fields)):
            raise ValueError('T2 two-reel initial span must be taut and subsonic')
        reference_length = sum(item[0] for item in fields) * (
            span.SPAN_LENGTH_M/self.cell_count)
        if abs(self.left.initial_local_cut_m +
               self.right.initial_local_cut_m - reference_length) > 1e-12:
            raise ValueError('T2 two-reel cuts do not own the initial span labels')
        if (type(self.observation_times_s) is not tuple or
                any(type(t) not in (int, float) or not math.isfinite(t) or
                    not 0 < t < self.duration_s for t in self.observation_times_s) or
                any(a >= b for a, b in zip(self.observation_times_s,
                                           self.observation_times_s[1:]))):
            raise ValueError('T2 two-reel observation times must be ordered')


def _local_port(cells, side, length, omega, phase, records, end, donor=None):
    normal = -1 if side == 'left' else 1
    if side == 'left':
        outgoing = -(3*single._characteristic(cells[0], 1) -
                     single._characteristic(cells[1], 1))/2
    else:
        outgoing = (3*single._characteristic(cells[-1], -1) -
                    single._characteristic(cells[-2], -1))/2
    radius, inertia = geometry._geometry(length)
    cut = end.initial_local_cut_m + end.initial_reference_length_m - length
    wound_speed = radius*omega
    if phase == 'wind':
        speed = wound_speed
        stretch = (speed-outgoing)/span.REFERENCE_WAVE_SPEED_M_S
        q = speed/stretch
        retained_stretch = stretch
        donor_role = 'newly_deposited_span_state'
    else:
        retained_stretch = (donor if donor is not None else
                            single._donor(records, cut).retained_stretch)
        q = wound_speed/retained_stretch
        stretch = outgoing/(q-span.REFERENCE_WAVE_SPEED_M_S)
        speed = q*stretch
        donor_role = 'retained_wound_record'
    single._require_subsonic(stretch, speed)
    if (not math.isfinite(q) or abs(q) >= span.REFERENCE_WAVE_SPEED_M_S or
            retained_stretch <= 1):
        raise ValueError('T2 two-reel port left taut subsonic domain')
    tension = span.EA_N*(stretch-1)
    strain = span.EA_N*(stretch-1)**2/2
    retained_energy = span.EA_N*(retained_stretch-1)**2/2
    energy_flux = q*(span.REFERENCE_LINE_MASS_KG_M*speed**2/2 + strain) - tension*speed
    dissipation = ((-q)*(span.EA_N-span.REFERENCE_LINE_MASS_KG_M*q**2)*
                   (stretch-retained_stretch)**2/2 if phase == 'release'
                   else 0.0)
    return {'side': side, 'normal': normal, 'state': span._conserved(
                stretch, normal*speed), 'cut_label_m': cut,
            'reference_flux_m_s': q, 'outward_span_speed_m_s': speed,
            'wound_speed_m_s': wound_speed, 'stretch': stretch,
            'retained_stretch': retained_stretch, 'donor_role': donor_role,
            'tension_n': tension, 'radius_m': radius, 'inertia_kg_m2': inertia,
            'omega_rad_s': omega, 'outward_energy_flux_w': energy_flux,
            'stored_strain_flux_w': q*retained_energy,
            'dissipated_power_w': dissipation}


def _rates(cells, reels, time_s, records, episode, donors=None):
    ports = {side: _local_port(cells, side, reels[side][0], reels[side][1],
                              getattr(episode, side).phase, records[side],
                              getattr(episode, side),
                              None if donors is None else donors[side])
             for side in ('left', 'right')}
    slopes = []
    for index in range(len(cells)):
        if index == 0:
            slopes.append(tuple(cells[1][j]-cells[0][j] for j in (0, 1)))
        elif index == len(cells)-1:
            slopes.append(tuple(cells[-1][j]-cells[-2][j] for j in (0, 1)))
        else:
            slopes.append(tuple(span._minmod3(
                2*(cells[index][j]-cells[index-1][j]),
                (cells[index+1][j]-cells[index-1][j])/2,
                2*(cells[index+1][j]-cells[index][j])) for j in (0, 1)))
    fluxes = [fv._physical_flux(ports['left']['state'])]
    signal = 0.0
    minimum_stretch = min(port['stretch'] for port in ports.values())
    for cell in cells:
        stretch, speed = fv._primitive(cell)
        single._require_subsonic(stretch, speed)
        minimum_stretch = min(minimum_stretch, stretch)
        signal = max(signal, abs(speed)+stretch*span.REFERENCE_WAVE_SPEED_M_S)
    for index in range(len(cells)-1):
        left = tuple(cells[index][j]+slopes[index][j]/2 for j in (0, 1))
        right = tuple(cells[index+1][j]-slopes[index+1][j]/2 for j in (0, 1))
        for state in (left, right):
            stretch, speed = fv._primitive(state)
            single._require_subsonic(stretch, speed)
            minimum_stretch = min(minimum_stretch, stretch)
        face_flux, face_signal = fv._interface_flux(left, right)
        fluxes.append(face_flux)
        signal = max(signal, face_signal)
    fluxes.append(fv._physical_flux(ports['right']['state']))
    for port in ports.values():
        stretch, speed = fv._primitive(port['state'])
        signal = max(signal, abs(speed)+stretch*span.REFERENCE_WAVE_SPEED_M_S)
    dx = span.SPAN_LENGTH_M/episode.cell_count
    field_rates = [tuple(-(fluxes[i+1][j]-fluxes[i][j])/dx for j in (0, 1))
                   for i in range(len(cells))]
    reel_rates = {}
    drive_powers = {}
    angular_rhs = {}
    for side, port in ports.items():
        torque = single._history_value(getattr(episode, side).applied_torque_history,
                                       time_s)
        mu = span.REFERENCE_LINE_MASS_KG_M
        q, radius = port['reference_flux_m_s'], port['radius_m']
        wound_speed = port['wound_speed_m_s']
        angular_rhs[side] = (torque-radius*port['tension_n']+
                             mu*q*radius*port['outward_span_speed_m_s'])
        omega_rate = ((torque-radius*port['tension_n']+
                       mu*q*radius*(port['outward_span_speed_m_s']-wound_speed)) /
                      port['inertia_kg_m2'])
        reel_rates[side] = (q, omega_rate, port['omega_rad_s'])
        drive_powers[side] = torque*port['omega_rad_s']
        port['applied_torque_nm'] = torque
    return {'ports': ports, 'field_rates': field_rates,
            'reel_rates': reel_rates, 'drive_powers': drive_powers,
            'angular_rhs': angular_rhs, 'left_flux': fluxes[0],
            'right_flux': fluxes[-1], 'minimum_stretch': minimum_stretch,
            'maximum_signal_m_s': signal}


def _advance(cells, reels, time_s, h, records, episode):
    donors = {}
    for side in ('left', 'right'):
        end = getattr(episode, side)
        cut = end.initial_local_cut_m + end.initial_reference_length_m - reels[side][0]
        donors[side] = (single._donor(records[side], cut).retained_stretch
                        if end.phase == 'release' else None)
    first = _rates(cells, reels, time_s, records, episode, donors)
    predicted = [tuple(cell[j]+h*rate[j] for j in (0, 1))
                 for cell, rate in zip(cells, first['field_rates'])]
    predicted_reels = {side: tuple(reels[side][j]+h*first['reel_rates'][side][j]
                                   for j in range(3)) for side in ('left', 'right')}
    second = _rates(predicted, predicted_reels, time_s+h, records, episode, donors)
    updated = [tuple((cells[i][j]+predicted[i][j]+h*second['field_rates'][i][j])/2
                     for j in (0, 1)) for i in range(len(cells))]
    updated_reels = {side: tuple((reels[side][j]+predicted_reels[side][j]+
                                  h*second['reel_rates'][side][j])/2
                                 for j in range(3)) for side in ('left', 'right')}
    final = _rates(updated, updated_reels, time_s+h, records, episode, donors)
    courant = h*max(rate['maximum_signal_m_s'] for rate in
                    (first, second, final))/(span.SPAN_LENGTH_M/episode.cell_count)
    return {'cells': updated, 'reels': updated_reels, 'first': first,
            'second': second, 'final': final, 'courant': courant}


def _state(time_s, cells, reels, records, heat, integrated, episode):
    dx = span.SPAN_LENGTH_M/episode.cell_count
    mass, momentum, energy = fv._integrals(cells, dx)
    ends = {}
    for side in ('left', 'right'):
        length, omega, angle = reels[side]
        end = getattr(episode, side)
        cut = end.initial_local_cut_m + end.initial_reference_length_m - length
        radius, inertia = geometry._geometry(length)
        port = _local_port(cells, side, length, omega, end.phase,
                           records[side], end)
        ends[side] = {
            'phase': end.phase, 'local_cut_label_m': cut,
            'global_span_cut_label_m': (-cut if side == 'left' else cut),
            'reference_length_m': length, 'radius_m': radius,
            'inertia_kg_m2': inertia, 'angular_speed_rad_s': omega,
            'angle_rad': angle, 'angular_momentum_kg_m2_s': inertia*omega,
            'kinetic_energy_j': inertia*omega**2/2,
            'owned_wound_strain_energy_j': single._owned_energy(cut, records[side]),
            'ordered_wound_records': [
                {'low_label_m': item.low_label_m,
                 'high_label_m': item.high_label_m,
                 'retained_stretch': item.retained_stretch}
                for item in records[side]],
            'outward_span_speed_m_s': port['outward_span_speed_m_s'],
            'span_stretch': port['stretch'], 'retained_stretch': port['retained_stretch'],
            'reference_flux_m_s': port['reference_flux_m_s'],
            'outward_energy_flux_w': port['outward_energy_flux_w'],
            'applied_torque_nm': single._history_value(end.applied_torque_history,
                                                       time_s),
            'integrated_drive_work_j': integrated[side]['drive_work'],
            'integrated_angular_rhs_nm_s': integrated[side]['angular_rhs'],
            'integrated_outward_energy_flux_j': integrated[side]['outward_energy'],
            'integrated_stored_strain_flux_j': integrated[side]['stored_flux'],
            'accumulated_dissipated_energy_j': heat[side]}
    mechanical = energy + sum(end['kinetic_energy_j']+
                              end['owned_wound_strain_energy_j']
                              for end in ends.values())
    return {'time_s': time_s, 'cell_conservative_fields': [list(item) for item in cells],
            'span_mass_kg': mass, 'span_momentum_kg_m_s': momentum,
            'span_mechanical_energy_j': energy, 'ends': ends,
            'total_mechanical_energy_j': mechanical,
            'total_energy_including_dissipation_j': mechanical+sum(heat.values()),
            'integrated_global_left_mass_flux_m': integrated['left_mass_flux'],
            'integrated_global_right_mass_flux_m': integrated['right_mass_flux']}


def _reject_unresolved_event(start, trial, episode, records):
    for side in ('left', 'right'):
        end = getattr(episode, side)
        old_cut = start['ports'][side]['cut_label_m']
        for rates in (trial['first'], trial['second'], trial['final']):
            port = rates['ports'][side]
            if (end.phase == 'wind' and
                    (port['omega_rad_s'] <= 0 or port['reference_flux_m_s'] <= 0)):
                raise ValueError('T2 two-reel unresolved phase reversal')
            if (end.phase == 'release' and
                    (port['omega_rad_s'] >= 0 or port['reference_flux_m_s'] >= 0)):
                raise ValueError('T2 two-reel unresolved phase reversal')
            if port['cut_label_m'] >= records[side][0].high_label_m - 1e-12:
                raise ValueError('T2 two-reel inventory depletion')
            if end.phase == 'release' and port['cut_label_m'] >= (
                    single._next_donor_boundary(records[side], old_cut)-1e-12):
                raise ValueError('T2 two-reel unresolved donor boundary')
        if trial['reels'][side][0] <= 0:
            raise ValueError('T2 two-reel inventory depletion')
    if min(rate['minimum_stretch'] for rate in
           (trial['first'], trial['second'], trial['final'])) <= 1:
        raise ValueError('T2 two-reel unresolved tension zero')


def run_two_reel_episode(episode: TwoReelEpisode):
    """Advance a pre-engaged, event-free two-reel episode with accepted-only history."""
    if not isinstance(episode, TwoReelEpisode):
        raise ValueError('T2 two-reel requires a validated episode')
    cells = [tuple(cell) for cell in episode.initial_conserved_fields]
    reels = {side: (getattr(episode, side).initial_reference_length_m,
                    getattr(episode, side).initial_omega_rad_s, 0.)
             for side in ('left', 'right')}
    records = {side: list(getattr(episode, side).initial_records)
               for side in ('left', 'right')}
    heat = {'left': 0., 'right': 0.}
    integrated = {'left_mass_flux': 0., 'right_mass_flux': 0.}
    for side in ('left', 'right'):
        integrated[side] = {'drive_work': 0., 'angular_rhs': 0.,
                            'outward_energy': 0., 'stored_flux': 0.}
    time_s = 0.
    initial = _state(time_s, cells, reels, records, heat, integrated, episode)
    accepted = [initial]
    snapshots = [initial]
    maximum = {'courant': 0., 'mass': 0., 'momentum': 0.,
               'inventory': 0., 'energy': 0., 'angular': 0.,
               'reel_energy': 0., 'storage': 0., 'minimum_stretch': float('inf')}
    observation_index = 0
    dx = span.SPAN_LENGTH_M/episode.cell_count
    while time_s < episode.duration_s-1e-13:
        if len(accepted) > 12000:
            raise ValueError('T2 two-reel exceeded accepted-step budget')
        start = _rates(cells, reels, time_s, records, episode)
        if start['minimum_stretch'] <= 1:
            raise ValueError('T2 two-reel initial or committed slack')
        knot = single._first_future_knot(time_s,
            episode.left.applied_torque_history,
            episode.right.applied_torque_history)
        h = min(episode.duration_s-time_s, knot-time_s,
                .99*episode.cfl_limit*dx/start['maximum_signal_m_s'])
        if h <= 1e-13:
            raise ValueError('T2 two-reel step collapsed')
        for _ in range(20):
            trial = _advance(cells, reels, time_s, h, records, episode)
            if trial['courant'] <= episode.cfl_limit*(1+1e-12):
                break
            h /= 2
        else:
            raise ValueError('T2 two-reel CFL retry budget exhausted')
        _reject_unresolved_event(start, trial, episode, records)
        first, second = trial['first'], trial['second']
        old_mass, old_momentum, _ = fv._integrals(cells, dx)
        for side in ('left', 'right'):
            first_port, second_port = (rate['ports'][side] for rate in (first, second))
            for name, values in (
                ('drive_work', (first['drive_powers'][side],
                                second['drive_powers'][side])),
                ('angular_rhs', (first['angular_rhs'][side],
                                 second['angular_rhs'][side])),
                ('outward_energy', (first_port['outward_energy_flux_w'],
                                    second_port['outward_energy_flux_w'])),
                ('stored_flux', (first_port['stored_strain_flux_w'],
                                 second_port['stored_strain_flux_w']))):
                integrated[side][name] += h*sum(values)/2
            heat[side] += h*(first_port['dissipated_power_w']+
                             second_port['dissipated_power_w'])/2
        for side, factor in (('left', -1), ('right', 1)):
            integrated[side+'_mass_flux'] += h*factor*(
                first['ports'][side]['reference_flux_m_s']+
                second['ports'][side]['reference_flux_m_s'])/2
        cells, reels = trial['cells'], trial['reels']
        time_s += h
        for side in ('left', 'right'):
            end = getattr(episode, side)
            old_cut = first['ports'][side]['cut_label_m']
            new_cut = end.initial_local_cut_m + end.initial_reference_length_m - reels[side][0]
            if end.phase == 'wind':
                stage_one = {'port': {'reference_flux_m_s':
                                      first['ports'][side]['reference_flux_m_s'],
                                      'span_stretch': first['ports'][side]['stretch']}}
                stage_two = {'port': {'reference_flux_m_s':
                                      second['ports'][side]['reference_flux_m_s'],
                                      'span_stretch': second['ports'][side]['stretch']}}
                packets, _ = single._winding_packets(old_cut, new_cut, h,
                                                      stage_one, stage_two)
                records[side].extend(packets)
            elif new_cut < old_cut-1e-12:
                raise ValueError('T2 two-reel release ownership reversed')
        state = _state(time_s, cells, reels, records, heat, integrated, episode)
        new_mass, new_momentum = state['span_mass_kg'], state['span_momentum_kg_m_s']
        maximum['courant'] = max(maximum['courant'], trial['courant'])
        maximum['minimum_stretch'] = min(maximum['minimum_stretch'], *(
            rate['minimum_stretch'] for rate in (first, second, trial['final'])))
        maximum['mass'] = max(maximum['mass'], abs(new_mass-old_mass+
            span.REFERENCE_LINE_MASS_KG_M*h*((first['right_flux'][0]+
                second['right_flux'][0]-first['left_flux'][0]-
                second['left_flux'][0])/2)))
        maximum['momentum'] = max(maximum['momentum'], abs(new_momentum-old_momentum+
            h*((first['right_flux'][1]+second['right_flux'][1]-
                first['left_flux'][1]-second['left_flux'][1])/2)))
        initial_mass = initial['span_mass_kg']+span.REFERENCE_LINE_MASS_KG_M*sum(
            initial['ends'][side]['reference_length_m'] for side in ('left', 'right'))
        current_mass = new_mass+span.REFERENCE_LINE_MASS_KG_M*sum(
            state['ends'][side]['reference_length_m'] for side in ('left', 'right'))
        maximum['inventory'] = max(maximum['inventory'], abs(current_mass-initial_mass),
            span.REFERENCE_LINE_MASS_KG_M*abs(sum(
                state['ends'][side]['local_cut_label_m'] for side in
                ('left', 'right'))-new_mass/span.REFERENCE_LINE_MASS_KG_M))
        drive_work = sum(integrated[side]['drive_work'] for side in ('left', 'right'))
        maximum['energy'] = max(maximum['energy'], abs(
            state['total_energy_including_dissipation_j']-
            initial['total_energy_including_dissipation_j']-drive_work))
        for side in ('left', 'right'):
            now, begin = state['ends'][side], initial['ends'][side]
            ledger = integrated[side]
            maximum['angular'] = max(maximum['angular'], abs(
                now['angular_momentum_kg_m2_s']-
                begin['angular_momentum_kg_m2_s']-ledger['angular_rhs']))
            maximum['reel_energy'] = max(maximum['reel_energy'], abs(
                now['kinetic_energy_j']+now['owned_wound_strain_energy_j']+
                heat[side]-begin['kinetic_energy_j']-
                begin['owned_wound_strain_energy_j']-ledger['drive_work']-
                ledger['outward_energy']))
            maximum['storage'] = max(maximum['storage'], abs(
                now['owned_wound_strain_energy_j']-
                begin['owned_wound_strain_energy_j']-ledger['stored_flux']))
        accepted.append(state)
        while (observation_index < len(episode.observation_times_s) and
               episode.observation_times_s[observation_index] <= time_s+1e-13):
            sample = dict(state)
            sample['requested_observation_time_s'] = (
                episode.observation_times_s[observation_index])
            sample['observation_role'] = 'first_accepted_state_at_or_after_request'
            snapshots.append(sample)
            observation_index += 1
    if snapshots[-1]['time_s'] < time_s-1e-12:
        snapshots.append(accepted[-1])
    return {'model_id': MODEL_ID, 'mode': 'preengaged_two_reel_elastic_span',
            'episode_outcome': 'COMPLETED_DECLARED_DURATION',
            'torque_role': 'prescribed_time_only_input',
            'span_and_reel_speed_role': 'predicted_from_coupled_dynamics',
            'pickup_closure_role': 'idealized_dissipative_not_physically_validated',
            'observation_role': 'first_accepted_state_at_or_after_request',
            'cell_count': episode.cell_count, 'cfl_limit': episode.cfl_limit,
            'accepted_states': accepted, 'snapshots': snapshots,
            'maximum_reconstructed_stage_courant': maximum['courant'],
            'minimum_used_stretch': maximum['minimum_stretch'],
            'maximum_mass_balance_defect_kg': maximum['mass'],
            'maximum_momentum_balance_defect_kg_m_s': maximum['momentum'],
            'maximum_combined_inventory_defect_kg': maximum['inventory'],
            'maximum_combined_energy_defect_j': maximum['energy'],
            'maximum_reel_angular_impulse_defect_nm_s': maximum['angular'],
            'maximum_reel_cumulative_energy_defect_j': maximum['reel_energy'],
            'maximum_exact_storage_vs_transfer_flux_defect_j': maximum['storage'],
            'limitations': ['pre-engaged two-reel taut subsonic interval only',
                            'phase changes, donor changes, slack and depletion rejected',
                            'no rolling contact or calibrated material data']}
