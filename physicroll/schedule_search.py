"""Finite, deterministic search over explicitly supplied single-layer routes.

The builder supplies every physical input for a candidate. Search never infers
material properties, interpass conditions, mill limits, or feasibility.
"""
from dataclasses import dataclass
from itertools import combinations, product
import math

from .checked_schedule import run_checked_schedule


@dataclass(frozen=True)
class OperatingChoice:
    """Discrete entry speed and tensions; other inputs belong to the builder."""
    entry_speed_m_s: float
    entry_tension_pa: float
    exit_tension_pa: float
    provenance: str

    def validate(self):
        values = (self.entry_speed_m_s, self.entry_tension_pa, self.exit_tension_pa)
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
               not math.isfinite(v) for v in values):
            raise ValueError('operating choices require finite SI values')
        if self.entry_speed_m_s <= 0 or min(self.entry_tension_pa, self.exit_tension_pa) < 0:
            raise ValueError('speed must be positive and tensions nonnegative')
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError('operating choice provenance required')


@dataclass(frozen=True)
class SearchSpace:
    gauges_m: tuple[float, ...]  # descending; exact start and target included
    mandatory_checkpoints_m: tuple[float, ...]
    min_passes: int
    max_passes: int
    choices_by_pass: tuple[tuple[OperatingChoice, ...], ...]
    max_evaluations: int

    def validate(self):
        if not isinstance(self.gauges_m, tuple) or len(self.gauges_m) < 2 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or
                not math.isfinite(v) or v <= 0 for v in self.gauges_m):
            raise ValueError('gauge grid needs at least two positive finite values')
        if any(a <= b for a, b in zip(self.gauges_m, self.gauges_m[1:])):
            raise ValueError('gauge grid must strictly descend')
        if (not isinstance(self.mandatory_checkpoints_m, tuple) or
                any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                    not math.isfinite(v) for v in self.mandatory_checkpoints_m) or
                len(set(self.mandatory_checkpoints_m)) != len(self.mandatory_checkpoints_m) or
                any(v not in self.gauges_m[1:-1] for v in self.mandatory_checkpoints_m)):
            raise ValueError('checkpoints must be distinct interior grid gauges')
        if (any(isinstance(v, bool) or not isinstance(v, int) for v in
                (self.min_passes, self.max_passes, self.max_evaluations)) or
                not 1 <= self.min_passes <= self.max_passes <= len(self.gauges_m)-1 or
                self.max_passes < len(self.mandatory_checkpoints_m)+1 or
                self.max_evaluations < 1):
            raise ValueError('invalid finite pass/evaluation bounds')
        if (not isinstance(self.choices_by_pass, tuple) or
                len(self.choices_by_pass) < self.max_passes or
                any(not isinstance(row, tuple) or not row or
                    any(not isinstance(choice, OperatingChoice) for choice in row)
                    for row in self.choices_by_pass)):
            raise ValueError('each possible pass needs discrete operating choices')
        for row in self.choices_by_pass:
            for choice in row:
                choice.validate()


def log_gauge_grid(start_m: float, target_m: float, steps: int,
                   checkpoints_m: tuple[float, ...] = ()) -> tuple[float, ...]:
    """Exact endpoints/checkpoints plus log-spaced interior nodes; a search mesh."""
    if (any(isinstance(v, bool) or not isinstance(v, (int, float)) or
            not math.isfinite(v) for v in (start_m, target_m)) or
            not 0 < target_m < start_m or isinstance(steps, bool) or
            not isinstance(steps, int) or steps < 1 or
            not isinstance(checkpoints_m, tuple) or
            any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                not math.isfinite(v) or not target_m < v < start_m for v in checkpoints_m)):
        raise ValueError('invalid log gauge grid inputs')
    ratio = math.log(target_m)-math.log(start_m)
    nodes = (start_m, target_m) + checkpoints_m + tuple(
        start_m * math.exp(ratio*i/steps) for i in range(1, steps))
    return tuple(sorted(set(nodes), reverse=True))


def _candidate_count(space):
    optional = len(space.gauges_m)-2-len(space.mandatory_checkpoints_m)
    required = len(space.mandatory_checkpoints_m)
    return sum(math.comb(optional, n-1-required) * math.prod(
        len(row) for row in space.choices_by_pass[:n])
        for n in range(space.min_passes, space.max_passes+1)
        if 0 <= n-1-required <= optional)


def _validate_replay(result, gauges, choices):
    if (not isinstance(result, dict) or
            result.get('declared_bounds_status') not in ('VIOLATED', 'INDETERMINATE') or
            not isinstance(result.get('passes'), list) or
            len(result['passes']) != len(choices)):
        raise ValueError('oracle contract: checked bounds status and matching pass count required')
    audit = result.get('gauge_audit')
    if (not isinstance(audit, dict) or
            audit.get('gauge_basis') != 'per_layer_full_thickness' or
            audit.get('layer_count') != 1 or
            audit.get('target_exit_m') != gauges[-1]):
        raise ValueError('oracle contract: checked single-layer gauge audit required')
    for i, (item, choice) in enumerate(zip(result['passes'], choices)):
        scenario = item.get('requested_scenario') if isinstance(item, dict) else None
        if (not isinstance(scenario, dict) or
                any(scenario.get(key) != value for key, value in (
                    ('entry_thickness_m', gauges[i]), ('exit_thickness_m', gauges[i+1]),
                    ('entry_speed_m_s', choice.entry_speed_m_s),
                    ('entry_tension_pa', choice.entry_tension_pa),
                    ('exit_tension_pa', choice.exit_tension_pa)))):
            raise ValueError(f'oracle contract: pass {i+1} does not match enumerated route')


def _rating_signature(result):
    signatures = []
    for item in result['passes']:
        checks = item['operating']['equipment_checks']
        signatures.append(tuple(sorted((check['quantity'], check['limit']) for check in checks)))
    if len(set(signatures)) > 1:
        raise ValueError('oracle contract: equipment ratings differ between passes')
    return signatures[0]


def _peak_utilization(result):
    """Only fully evaluated declared equipment limits provide this tie score."""
    values = []
    for item in result['passes']:
        checks = item['operating']['equipment_checks']
        if not checks or any(check['status'] != 'WITHIN_DECLARED_LIMIT' for check in checks):
            return None
        values.extend(check['predicted_value']/check['limit'] for check in checks)
    return max(values) if values else None


def search_schedules(space: SearchSpace, build_and_replay):
    """Search a bounded mesh with a complete-route oracle, preserving all state.

    ``build_and_replay(gauges, choices)`` must build and replay the entire
    candidate. Rejected candidates retain their error/status. A selected route
    is replayed again and required to return the identical result.
    """
    space.validate()
    if not callable(build_and_replay):
        raise ValueError('candidate builder/replay must be callable')
    count = _candidate_count(space)
    if count > space.max_evaluations:
        raise ValueError(f'{count} candidates exceed explicit evaluation cap {space.max_evaluations}')
    required = set(space.mandatory_checkpoints_m)
    optional = tuple(v for v in space.gauges_m[1:-1] if v not in required)
    records = []
    selected = None
    selected_key = None
    rating_signature = None
    for n in range(space.min_passes, space.max_passes+1):
        extra = n-1-len(required)
        if not 0 <= extra <= len(optional):
            continue
        for subset in combinations(optional, extra):
            gauges = (space.gauges_m[0],) + tuple(sorted(required.union(subset), reverse=True)) + (space.gauges_m[-1],)
            for choices in product(*space.choices_by_pass[:n]):
                try:
                    result = build_and_replay(gauges, choices)
                except ValueError as exc:
                    result, status, score, reason = None, 'REJECTED', None, str(exc)
                else:
                    _validate_replay(result, gauges, choices)
                    status = result['declared_bounds_status']
                    signature = _rating_signature(result)
                    if rating_signature is None:
                        rating_signature = signature
                    elif signature != rating_signature:
                        raise ValueError('oracle contract: equipment ratings differ between candidates')
                    score = _peak_utilization(result) if status == 'INDETERMINATE' else None
                    reason = (result.get('declared_bound_violations', [])
                              if status == 'VIOLATED' else None)
                record = {'gauges_m': gauges, 'choices': choices, 'status': status,
                          'peak_normalized_utilization': score, 'reason': reason}
                records.append(record)
                if status == 'INDETERMINATE':
                    key = (n, score is None, float('inf') if score is None else score)
                    if selected_key is None or key < selected_key:
                        selected, selected_key = (record, result), key
    if selected is None:
        return {'status': 'NO_NONVIOLATING_CANDIDATE_ON_GRID', 'evaluations': count,
                'selected': None, 'candidates': records}
    record, result = selected
    replay = build_and_replay(record['gauges_m'], record['choices'])
    _validate_replay(replay, record['gauges_m'], record['choices'])
    if replay != result:
        raise ValueError('selected route did not reproduce on independent full replay')
    return {'status': 'SELECTED_DECLARED_BOUNDS_INDETERMINATE', 'evaluations': count,
            'selected': {**record, 'checked_replay': replay}, 'candidates': records}


def checked_replay(passes, initial_state, law, *, interpass_handoffs=(),
                   strip_cp=None, roll_cp=None, equipment_limits=None):
    """Adapter for a candidate builder with complete checked-solver inputs."""
    return run_checked_schedule(passes, initial_state, law,
                                gauge_basis='per_layer_full_thickness', layer_count=1,
                                interpass_handoffs=interpass_handoffs,
                                strip_cp=strip_cp, roll_cp=roll_cp,
                                equipment_limits=equipment_limits)
