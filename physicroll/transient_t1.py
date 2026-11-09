"""Analytic prescribed-motion T1 strip/reel transport on a bounded episode.

This is a kinematic verification layer. It solves no torque, tension, rolling
deformation or contact law; the strip speed is an input, not a prediction.
"""

from bisect import bisect_right
from dataclasses import asdict, dataclass
import hashlib
from importlib.resources import files
import json
import math
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .run_contract import canonical_json


MODEL_ID = 'T1_UNIFORM_STRIP_PRESCRIBED_MOTION_V1'
CHECKPOINT_VERSION = '1'
SHA256 = re.compile(r'[0-9a-f]{64}\Z')


def _digest(value):
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def _module_sha256():
    return hashlib.sha256(files('physicroll').joinpath('transient_t1.py').read_bytes()).hexdigest()


def _number(value, name, *, positive=False, nonnegative=False):
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f'{name} must be a finite number')
    if positive and value <= 0 or nonnegative and value < 0:
        raise ValueError(f'{name} is outside its positive/nonnegative domain')


@dataclass(frozen=True)
class T1Episode:
    times_s: tuple[float, ...]
    prescribed_strip_speed_m_s: tuple[float, ...]
    free_span_length_m: float
    thickness_m: float
    width_m: float
    density_kg_m3: float
    left_core_radius_m: float
    right_core_radius_m: float
    left_initial_length_m: float
    right_initial_length_m: float
    parcels: tuple[tuple[str, float], ...] = ()
    left_capacity_length_m: float | None = None
    right_capacity_length_m: float | None = None
    left_initial_radius_m: float | None = None
    right_initial_radius_m: float | None = None
    left_initial_angle_rad: float = 0.0
    right_initial_angle_rad: float = 0.0
    transport_roller_radius_m: float | None = None
    transport_roller_orientation: int = 1
    transport_roller_initial_angle_rad: float = 0.0
    declared_feed_speed_m_s: tuple[float, ...] | None = None
    declared_take_up_speed_m_s: tuple[float, ...] | None = None

    def __post_init__(self):
        times, speeds = self.times_s, self.prescribed_strip_speed_m_s
        if (type(times) is not tuple or type(speeds) is not tuple or
                len(times) < 2 or len(times) != len(speeds)):
            raise ValueError('T1 needs equal-length time and speed tuples with at least two knots')
        for index, (time, speed) in enumerate(zip(times, speeds)):
            _number(time, f'times_s[{index}]', nonnegative=True)
            _number(speed, f'prescribed_strip_speed_m_s[{index}]')
            if index == 0 and time != 0 or index and time <= times[index - 1]:
                raise ValueError('T1 times must start at zero and increase strictly')
        for name in ('free_span_length_m', 'thickness_m', 'width_m', 'density_kg_m3',
                     'left_core_radius_m', 'right_core_radius_m'):
            _number(getattr(self, name), name, positive=True)
        for name in ('left_initial_length_m', 'right_initial_length_m'):
            _number(getattr(self, name), name, nonnegative=True)
        total_length = (self.left_initial_length_m + self.free_span_length_m +
                        self.right_initial_length_m)
        if (not math.isfinite(total_length) or
                not math.isfinite(self.density_kg_m3 * self.width_m *
                                  self.thickness_m * total_length) or
                any(not math.isfinite(core ** 2 + self.thickness_m * total_length / math.pi)
                    for core in (self.left_core_radius_m, self.right_core_radius_m))):
            raise ValueError('T1 initial geometry or mass exceeds the finite numerical domain')
        for side in ('left', 'right'):
            length = getattr(self, f'{side}_initial_length_m')
            capacity = getattr(self, f'{side}_capacity_length_m')
            if capacity is not None:
                _number(capacity, f'{side}_capacity_length_m', nonnegative=True)
                if capacity < length:
                    raise ValueError(f'{side} initial inventory exceeds reel capacity')
            radius = getattr(self, f'{side}_initial_radius_m')
            if radius is not None:
                _number(radius, f'{side}_initial_radius_m', positive=True)
                expected = math.sqrt(getattr(self, f'{side}_core_radius_m') ** 2 +
                                     self.thickness_m * length / math.pi)
                if not math.isclose(radius, expected, rel_tol=1e-12, abs_tol=1e-10):
                    raise ValueError(f'{side} initial radius disagrees with inventory')
        for name in ('left_initial_angle_rad', 'right_initial_angle_rad',
                     'transport_roller_initial_angle_rad'):
            _number(getattr(self, name), name)
        if self.transport_roller_radius_m is not None:
            _number(self.transport_roller_radius_m, 'transport_roller_radius_m', positive=True)
        if type(self.transport_roller_orientation) is not int or self.transport_roller_orientation not in (-1, 1):
            raise ValueError('transport_roller_orientation must be +1 or -1')
        if type(self.parcels) is not tuple:
            raise ValueError('parcels must be an immutable tuple')
        seen = set()
        for parcel in self.parcels:
            if type(parcel) is not tuple or len(parcel) != 2:
                raise ValueError('each parcel must be an (id, reference_m) tuple')
            identity, reference = parcel
            if type(identity) is not str or not identity.strip() or identity in seen:
                raise ValueError('parcel ids must be distinct nonempty strings')
            seen.add(identity)
            _number(reference, f'parcel {identity} reference_m')
            if not -self.left_initial_length_m <= reference <= self.free_span_length_m + self.right_initial_length_m:
                raise ValueError(f'parcel {identity} lies outside the initial strip')
        for name in ('declared_feed_speed_m_s', 'declared_take_up_speed_m_s'):
            secondary = getattr(self, name)
            if secondary is not None:
                if type(secondary) is not tuple or len(secondary) != len(speeds):
                    raise ValueError(f'{name} must have one value per speed knot')
                for actual, required in zip(secondary, speeds):
                    _number(actual, name)
                    if not math.isclose(actual, required, rel_tol=1e-12, abs_tol=1e-10):
                        raise ValueError(f'{name} disagrees with prescribed strip speed')

    @property
    def sha256(self):
        return hashlib.sha256(canonical_json(asdict(self)).encode('utf-8')).hexdigest()


class T1Trajectory:
    """Immutable analytic solution; read-only state/frame queries do not advance it."""

    def __init__(self, episode: T1Episode):
        if not isinstance(episode, T1Episode):
            raise ValueError('T1Trajectory requires a T1Episode')
        self.episode = episode
        self._prefix_q = [0.0]
        for t0, t1, v0, v1 in zip(episode.times_s[:-1], episode.times_s[1:],
                                  episode.prescribed_strip_speed_m_s[:-1],
                                  episode.prescribed_strip_speed_m_s[1:]):
            duration = t1 - t0
            next_q = self._prefix_q[-1] + duration * (v0 + v1) / 2
            if not math.isfinite(next_q):
                raise ValueError('prescribed displacement exceeds the finite numerical domain')
            self._prefix_q.append(next_q)
        self._parts = self._monotone_parts()
        self.stop_time_s, self._terminal_event = self._first_reel_limit()
        self._event_records = self._build_events()

    @property
    def terminal_event(self):
        return None if self._terminal_event is None else dict(self._terminal_event)

    @property
    def events(self):
        return tuple(dict(item) for item in self._event_records)

    def displacement_at(self, time_s):
        _number(time_s, 'time_s', nonnegative=True)
        times = self.episode.times_s
        if time_s > times[-1]:
            raise ValueError('T1 history does not allow extrapolation')
        index = min(bisect_right(times, time_s) - 1, len(times) - 2)
        t0, t1 = times[index:index + 2]
        v0, v1 = self.episode.prescribed_strip_speed_m_s[index:index + 2]
        dt = time_s - t0
        return self._prefix_q[index] + v0 * dt + (v1 - v0) * dt * dt / (2 * (t1 - t0))

    def _monotone_parts(self):
        times = self.episode.times_s
        speeds = self.episode.prescribed_strip_speed_m_s
        parts = []
        for index, (t0, t1, v0, v1) in enumerate(zip(times[:-1], times[1:], speeds[:-1], speeds[1:])):
            split = t0 - v0 * (t1 - t0) / (v1 - v0) if v0 * v1 < 0 else None
            if split is None:
                parts.append((t0, t1))
            else:
                parts.extend(((t0, split), (split, t1)))
        return tuple(parts)

    def _first_reel_limit(self):
        e = self.episode
        lower = max(e.left_initial_length_m - e.left_capacity_length_m
                    if e.left_capacity_length_m is not None else -math.inf,
                    -e.right_initial_length_m)
        upper = min(e.left_initial_length_m,
                    e.right_capacity_length_m - e.right_initial_length_m
                    if e.right_capacity_length_m is not None else math.inf)
        for start, end in self._parts:
            q0, q1 = self.displacement_at(start), self.displacement_at(end)
            if q1 > q0 and q1 >= upper:
                hit = self._root(start, end, upper)
                return hit, {'event': 'reel_inventory_limit', 'time_s': hit,
                             'bound': 'upper', 'displacement_m': upper}
            if q1 < q0 and q1 <= lower:
                hit = self._root(start, end, lower)
                return hit, {'event': 'reel_inventory_limit', 'time_s': hit,
                             'bound': 'lower', 'displacement_m': lower}
        return e.times_s[-1], None

    def _root(self, start, end, target):
        """Locate a first hit within a monotone analytic segment."""
        first, last = start, end
        ascending = self.displacement_at(end) > self.displacement_at(start)
        if self.displacement_at(start) == target:
            return start
        if self.displacement_at(end) == target:
            return end
        for _ in range(80):
            middle = (first + last) / 2
            value = self.displacement_at(middle)
            if (value < target) == ascending:
                first = middle
            else:
                last = middle
        return (first + last) / 2

    def _build_events(self):
        e = self.episode
        events = []
        last_motion_sign = None
        for start, unbounded_end in self._parts:
            if start >= self.stop_time_s:
                break
            end = min(unbounded_end, self.stop_time_s)
            change = self.displacement_at(end) - self.displacement_at(start)
            motion_sign = 1 if change > 0 else -1 if change < 0 else 0
            if motion_sign:
                if last_motion_sign is not None and motion_sign != last_motion_sign:
                    events.append({'event': 'speed_reversal', 'time_s': start})
                last_motion_sign = motion_sign
        for identity, reference in e.parcels:
            for boundary, target in (('left', -reference),
                                     ('right', e.free_span_length_m - reference)):
                def side(value):
                    delta = value - target
                    return 1 if delta > 0 else -1 if delta < 0 else 0

                points = []
                hits = []
                for start, unbounded_end in self._parts:
                    if start > self.stop_time_s:
                        break
                    end = min(unbounded_end, self.stop_time_s)
                    q0, q1 = self.displacement_at(start), self.displacement_at(end)
                    points.extend(((start, q0), (end, q1)))
                    if side(q0) == 0:
                        hits.append(start)
                    if side(q1) == 0:
                        hits.append(end)
                    if side(q0) * side(q1) < 0:
                        hits.append(self._root(start, end, target))
                if not hits:
                    continue
                unique_hits = []
                for hit in sorted(hits):
                    if not unique_hits or abs(hit - unique_hits[-1]) > 1e-9:
                        unique_hits.append(hit)

                def constant_between(first, last):
                    for part_start, part_end in self._parts:
                        low, high = max(first, part_start), min(last, part_end, self.stop_time_s)
                        if high > low and (side(self.displacement_at(low)) or
                                           side(self.displacement_at(high))):
                            return False
                    return True

                windows = []
                for hit in unique_hits:
                    if windows and constant_between(windows[-1][1], hit):
                        windows[-1] = (windows[-1][0], hit)
                    else:
                        windows.append((hit, hit))
                for arrival, departure in windows:
                    before = next((side(value) for time, value in reversed(points)
                                   if time < arrival - 1e-12 and side(value)), None)
                    after = next((side(value) for time, value in points
                                  if time > departure + 1e-12 and side(value)), None)
                    if before is None and after is None:
                        continue
                    if before is None:
                        event_name, time, direction = ('parcel_boundary_departure', departure,
                                                       'forward' if after > 0 else 'reverse')
                    elif after is None:
                        event_name, time, direction = ('parcel_boundary_arrival', arrival,
                                                       'forward' if before < 0 else 'reverse')
                    elif before == after:
                        event_name, time, direction = 'parcel_boundary_touch', arrival, 'touch'
                    else:
                        event_name, time, direction = ('parcel_boundary_crossing', departure,
                                                       'forward' if after > 0 else 'reverse')
                    record = {'event': event_name, 'time_s': time,
                              'parcel_id': identity, 'boundary': boundary,
                              'direction': direction}
                    if departure > arrival:
                        record['boundary_arrival_time_s'] = arrival
                        record['boundary_departure_time_s'] = departure
                    events.append(record)
        if self._terminal_event is not None:
            events.append(dict(self._terminal_event))
        return tuple(sorted(events, key=lambda item: (item['time_s'], item['event'],
                                                       item.get('parcel_id', ''))))

    def state_at(self, time_s):
        _number(time_s, 'time_s', nonnegative=True)
        if time_s > self.stop_time_s:
            raise ValueError('T1 episode terminated; no state after first reel limit')
        e = self.episode
        q = (self._terminal_event['displacement_m']
             if self._terminal_event is not None and time_s == self.stop_time_s
             else self.displacement_at(time_s))
        left_length = e.left_initial_length_m - q
        right_length = e.right_initial_length_m + q
        left_radius = math.sqrt(e.left_core_radius_m ** 2 + e.thickness_m * left_length / math.pi)
        right_radius = math.sqrt(e.right_core_radius_m ** 2 + e.thickness_m * right_length / math.pi)
        left_initial_radius = math.sqrt(e.left_core_radius_m ** 2 +
                                        e.thickness_m * e.left_initial_length_m / math.pi)
        right_initial_radius = math.sqrt(e.right_core_radius_m ** 2 +
                                         e.thickness_m * e.right_initial_length_m / math.pi)
        parcels = []
        for identity, reference in e.parcels:
            projected = reference + q
            owner = ('left_reel' if projected < 0 else
                     'right_reel' if projected > e.free_span_length_m else 'free_span')
            parcels.append({'parcel_id': identity, 'reference_coordinate_m': reference,
                            'owner': owner,
                            'free_span_x_m': projected if owner == 'free_span' else None})
        line_mass = e.density_kg_m3 * e.width_m * e.thickness_m
        return {
            'time_s': time_s, 'prescribed_displacement_m': q,
            'left_length_m': left_length, 'right_length_m': right_length,
            'left_radius_m': left_radius, 'right_radius_m': right_radius,
            'left_mass_kg': line_mass * left_length,
            'right_mass_kg': line_mass * right_length,
            'free_span_mass_kg': line_mass * e.free_span_length_m,
            'left_winding_angle_rad': e.left_initial_angle_rad +
            2 * math.pi * (left_radius - left_initial_radius) / e.thickness_m,
            'right_winding_angle_rad': e.right_initial_angle_rad +
            2 * math.pi * (right_radius - right_initial_radius) / e.thickness_m,
            'transport_roller_angle_rad': (
                e.transport_roller_initial_angle_rad +
                e.transport_roller_orientation * q / e.transport_roller_radius_m
                if e.transport_roller_radius_m is not None else None),
            'parcels': parcels,
        }

    def result(self):
        e = self.episode
        times = {0.0, self.stop_time_s}
        times.update(time for time in e.times_s if time <= self.stop_time_s)
        times.update(event['time_s'] for event in self._event_records)
        states = [self.state_at(time) for time in sorted(times)]
        initial_mass = e.density_kg_m3 * e.width_m * e.thickness_m * (
            e.left_initial_length_m + e.free_span_length_m + e.right_initial_length_m)
        residual = max(abs(state['left_mass_kg'] + state['right_mass_kg'] +
                           state['free_span_mass_kg'] - initial_mass) for state in states)
        return {
            'model_id': MODEL_ID, 'input_sha256': e.sha256,
            'status': 'TERMINATED_REEL_LIMIT' if self._terminal_event else 'COMPLETED',
            'requested_duration_s': e.times_s[-1], 'completed_duration_s': self.stop_time_s,
            'strip_speed_role': 'prescribed_input',
            'reel_angle_role': 'kinematically_derived_from_prescribed_speed',
            'states': states, 'events': [dict(item) for item in self._event_records],
            'maximum_total_mass_residual_kg': residual,
            'limitations': ['uniform nonreducing strip', 'fixed free-span path',
                            'continuous annular reels', 'no torque/tension/contact solution'],
        }

    def checkpoint_at(self, time_s, run_spec_sha256):
        """Capture an accepted cursor, consuming all events at this exact time."""
        if type(run_spec_sha256) is not str or SHA256.fullmatch(run_spec_sha256) is None:
            raise ValueError('checkpoint requires a RunSpec SHA-256 identity')
        state = self.state_at(time_s)
        next_event = sum(event['time_s'] <= time_s for event in self._event_records)
        segment = min(bisect_right(self.episode.times_s, time_s) - 1,
                      len(self.episode.times_s) - 2)
        payload = {
            'checkpoint_version': CHECKPOINT_VERSION,
            'model_id': MODEL_ID,
            'episode_sha256': self.episode.sha256,
            'run_spec_sha256': run_spec_sha256,
            'module_sha256': _module_sha256(),
            'state': state,
            'history_segment_index': segment,
            'next_event_index': next_event,
            'consumed_events_sha256': _digest(self._event_records[:next_event]),
            'terminal': self._terminal_event is not None and time_s == self.stop_time_s,
        }
        return {**payload, 'checkpoint_sha256': _digest(payload)}


def continue_t1(episode, checkpoint, run_spec_sha256):
    """Verify a saved cursor and return only its remaining accepted suffix."""
    if not isinstance(episode, T1Episode):
        raise ValueError('T1 continuation requires a T1Episode')
    if type(checkpoint) is not dict or set(checkpoint) != {
            'checkpoint_version', 'model_id', 'episode_sha256',
            'run_spec_sha256', 'module_sha256', 'state',
            'history_segment_index', 'next_event_index',
            'consumed_events_sha256', 'terminal', 'checkpoint_sha256'}:
        raise ValueError('invalid T1 checkpoint shape')
    data = {key: value for key, value in checkpoint.items() if key != 'checkpoint_sha256'}
    if (type(checkpoint['checkpoint_sha256']) is not str or
            checkpoint['checkpoint_sha256'] != _digest(data)):
        raise ValueError('T1 checkpoint digest differs from contents')
    if (checkpoint['checkpoint_version'] != CHECKPOINT_VERSION or
            checkpoint['model_id'] != MODEL_ID or
            checkpoint['episode_sha256'] != episode.sha256 or
            checkpoint['run_spec_sha256'] != run_spec_sha256 or
            checkpoint['module_sha256'] != _module_sha256()):
        raise ValueError('T1 checkpoint source, model or implementation differs')
    trajectory = T1Trajectory(episode)
    state = checkpoint['state']
    if type(state) is not dict or 'time_s' not in state:
        raise ValueError('T1 checkpoint has no valid accepted state')
    time_s = state['time_s']
    if (type(time_s) not in (int, float) or not math.isfinite(time_s) or
            not 0 <= time_s <= trajectory.stop_time_s):
        raise ValueError('T1 checkpoint time lies outside the accepted trajectory')
    expected = trajectory.checkpoint_at(time_s, run_spec_sha256)
    if canonical_json(checkpoint) != canonical_json(expected):
        raise ValueError('T1 checkpoint state, event cursor or history cursor differs')
    return T1Continuation(trajectory, checkpoint)


class T1Continuation:
    """Read-only continuation from a validated, already-consumed event cursor."""

    def __init__(self, trajectory, checkpoint):
        self._trajectory = trajectory
        self._checkpoint = json.loads(canonical_json(checkpoint))

    def state_at(self, time_s):
        if time_s < self._checkpoint['state']['time_s']:
            raise ValueError('T1 continuation cannot query before its checkpoint')
        return self._trajectory.state_at(time_s)

    def result(self):
        saved = self._trajectory.result()
        cursor_time = self._checkpoint['state']['time_s']
        index = self._checkpoint['next_event_index']
        return {
            'model_id': MODEL_ID,
            'episode_sha256': self._trajectory.episode.sha256,
            'checkpoint_sha256': self._checkpoint['checkpoint_sha256'],
            'initial_state': json.loads(canonical_json(self._checkpoint['state'])),
            'remaining_states': [state for state in saved['states']
                                 if state['time_s'] > cursor_time],
            'remaining_events': saved['events'][index:],
            'final_state': saved['states'][-1],
        }


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate T1 checkpoint key: {key}')
        result[key] = value
    return result


def save_t1_checkpoint(path, checkpoint):
    """Publish a new checkpoint file only after its complete bytes are staged."""
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ValueError('T1 checkpoint destination already exists')
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=path.parent, prefix=f'.{path.name}.') as temporary:
        staged = Path(temporary) / 'checkpoint.json'
        staged.write_bytes((canonical_json(checkpoint) + '\n').encode('utf-8'))
        try:
            # Same-directory hard-link creation is atomic and fails if another
            # writer published the destination while we staged the bytes.
            os.link(staged, path)
        except FileExistsError as exc:
            raise ValueError('T1 checkpoint destination appeared during creation') from exc


def load_t1_checkpoint(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('T1 checkpoint must be a real file')
    try:
        return json.loads(path.read_bytes(), object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'invalid T1 checkpoint JSON: {exc}') from exc
