"""Version 1 offline run envelopes; no solver, feasibility or calibration policy.

The two value objects retain validated canonical JSON, so caller-owned mutable
inputs cannot change a digest after construction. Runtime metadata is kept out
of the scientific payload and its digest.
"""

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass

SCHEMA_VERSION = '1'
WORKFLOWS = frozenset({
    'legacy_pass', 'checked_pass', 'checked_schedule', 'schedule_search',
    'benchmark', 'sensitivity', 'operating_replay', 'prescribed_transport_t1',
    'torque_driven_span_reel_t2', 'two_reel_span_t2',
})
MODEL_KEYS = frozenset({'solver', 'material', 'bite', 'thermal'})
IDENTITY_KEYS = frozenset({'code_version', 'model_version', 'material_id',
                           'state_id', 'recipe_id'})
CONVENTIONS = {
    'unit_system': 'SI',
    'gauge_basis': 'per_layer_full_thickness',
    'layer_count': 1,
    'temperature_unit': 'K',
    'force_sign': 'separating_positive',
    'torque_sign': 'motoring_positive_regeneration_negative',
    'power_sign': 'motoring_positive_regeneration_negative',
}
T2_CONVENTIONS = {**CONVENTIONS, 'torque_sign': 'winding_axis_positive'}
ASSESSMENT_VALUES = {
    'execution': frozenset({'COMPLETED', 'REJECTED', 'FAILED'}),
    'input_validity': frozenset({'VALID', 'INVALID', 'NOT_ASSESSED'}),
    'model_applicability': frozenset({'IN_DOMAIN', 'OUT_OF_DOMAIN', 'INDETERMINATE', 'NOT_ASSESSED'}),
    'numerical_verification': frozenset({'PASSED', 'FAILED', 'NOT_ASSESSED'}),
    'declared_bounds_status': frozenset({'WITHIN', 'VIOLATED', 'INDETERMINATE', 'NOT_ASSESSED'}),
    'declared_bounds_coverage': frozenset({'COMPLETE', 'PARTIAL', 'NONE'}),
    'scientific_qualification': frozenset({'QUALIFIED', 'UNQUALIFIED', 'NOT_ASSESSED'}),
    'operating_readiness': frozenset({'READY', 'NOT_READY', 'NOT_ASSESSED'}),
}
RUN_KEYS = frozenset({'schema_version', 'workflow_kind', 'model_choices',
                      'unit_conventions', 'identities', 'source_hashes',
                      'card_hashes', 'numerical_settings', 'requested_inputs',
                      'resolved_inputs', 'recipe_targets', 'observations'})
RESULT_KEYS = frozenset({'schema_version', 'run_spec_sha256', 'effective_inputs',
                         'outputs', 'checks', 'assessments'})
HASH = re.compile(r'[0-9a-f]{64}\Z')


def _normalize(value, active=None):
    """Copy supported JSON values, including dataclasses and tuples, strictly."""
    if type(value) is str:
        _unicode(value)
        return value
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError('nonfinite JSON number')
        return value
    if active is None:
        active = set()
    identity = id(value)
    if identity in active:
        raise ValueError('cyclic JSON value')
    active.add(identity)
    try:
        if is_dataclass(value) and not isinstance(value, type):
            return {field.name: _normalize(getattr(value, field.name), active)
                    for field in fields(value)}
        if isinstance(value, Mapping):
            if any(type(key) is not str for key in value):
                raise ValueError('JSON object keys must be strings')
            for key in value:
                _unicode(key)
            return {key: _normalize(item, active) for key, item in value.items()}
        if type(value) in (list, tuple):
            return [_normalize(item, active) for item in value]
        raise ValueError(f'unsupported JSON value: {type(value).__name__}')
    finally:
        active.remove(identity)


def _unicode(value):
    try:
        value.encode('utf-8')
    except UnicodeError as exc:
        raise ValueError('JSON strings must contain valid Unicode scalar values') from exc


def canonical_json(value):
    """UTF-8-ready, sorted-key JSON; every number must be finite."""
    return json.dumps(_normalize(value), ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def _pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f'nonfinite JSON number: {value}')


def _read_json(text):
    if not isinstance(text, (str, bytes, bytearray)):
        raise TypeError('JSON input must be text or bytes')
    try:
        return json.loads(text, object_pairs_hook=_pairs_without_duplicates,
                          parse_constant=_reject_constant)
    except (TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'invalid JSON: {exc}') from exc


def _object(value, label, keys=None):
    if type(value) is not dict:
        raise ValueError(f'{label} must be a JSON object')
    if keys is not None and set(value) != keys:
        raise ValueError(f'{label} keys: missing {sorted(keys - set(value))}, '
                         f'unknown {sorted(set(value) - keys)}')


def _text(value, label, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or not value.strip():
        raise ValueError(f'{label} must be a nonempty string' + (' or null' if nullable else ''))


def _hashes(value, label):
    _object(value, label)
    for key, digest in value.items():
        _text(key, f'{label} key')
        if type(digest) is not str or HASH.fullmatch(digest) is None:
            raise ValueError(f'{label}[{key}] must be a lowercase SHA-256 digest')


def _validate_run(data):
    _object(data, 'RunSpec', RUN_KEYS)
    if data['schema_version'] != SCHEMA_VERSION:
        raise ValueError('unsupported RunSpec schema_version')
    if type(data['workflow_kind']) is not str or data['workflow_kind'] not in WORKFLOWS:
        raise ValueError('unsupported workflow_kind')
    _object(data['model_choices'], 'model_choices', MODEL_KEYS)
    for key, value in data['model_choices'].items():
        _text(value, f'model_choices.{key}')
    _object(data['unit_conventions'], 'unit_conventions', set(CONVENTIONS))
    conventions = (T2_CONVENTIONS if data['workflow_kind'] in
                   ('torque_driven_span_reel_t2', 'two_reel_span_t2')
                   else CONVENTIONS)
    for key, expected in conventions.items():
        if type(data['unit_conventions'][key]) is not type(expected) or data['unit_conventions'][key] != expected:
            raise ValueError(f'unsupported unit_conventions.{key}')
    _object(data['identities'], 'identities', IDENTITY_KEYS)
    for key, value in data['identities'].items():
        _text(value, f'identities.{key}', nullable=key not in ('code_version', 'model_version'))
    _hashes(data['source_hashes'], 'source_hashes')
    _hashes(data['card_hashes'], 'card_hashes')
    if not data['source_hashes']:
        raise ValueError('at least one source hash is required')
    if data['identities']['material_id'] is not None and not data['card_hashes']:
        raise ValueError('identified material requires a card hash')
    for key in ('numerical_settings', 'requested_inputs', 'resolved_inputs',
                'recipe_targets', 'observations'):
        _object(data[key], key)


def _validate_result(data):
    _object(data, 'ResultBundle', RESULT_KEYS)
    if data['schema_version'] != SCHEMA_VERSION:
        raise ValueError('unsupported ResultBundle schema_version')
    if type(data['run_spec_sha256']) is not str or HASH.fullmatch(data['run_spec_sha256']) is None:
        raise ValueError('run_spec_sha256 must be a lowercase SHA-256 digest')
    for key in ('effective_inputs', 'outputs', 'checks'):
        _object(data[key], key)
    checks = data['checks']
    if 'declared_bounds' not in checks:
        raise ValueError('checks.declared_bounds evidence is required')
    bounds = checks['declared_bounds']
    _object(bounds, 'checks.declared_bounds', {'required_limit_ids', 'evaluations'})
    required = bounds['required_limit_ids']
    evaluations = bounds['evaluations']
    if (type(required) is not list or
            any(type(item) is not str or not item.strip() for item in required) or
            len(required) != len(set(required))):
        raise ValueError('required_limit_ids must be distinct nonempty strings')
    if type(evaluations) is not list:
        raise ValueError('evaluations must be a list')
    seen = set()
    for item in evaluations:
        _object(item, 'bounds evaluation', {'limit_id', 'status'})
        if (type(item['limit_id']) is not str or item['limit_id'] not in required
                or item['limit_id'] in seen or item['status'] not in ('WITHIN', 'VIOLATED')):
            raise ValueError('bounds evaluation must name a distinct required limit and status')
        seen.add(item['limit_id'])
    coverage = ('NONE' if not evaluations else
                'COMPLETE' if len(seen) == len(required) else 'PARTIAL')
    assessment = data['assessments']
    _object(assessment, 'assessments', set(ASSESSMENT_VALUES) | {
        'predictions_computed', 'qualification_evidence_refs'})
    for key, allowed in ASSESSMENT_VALUES.items():
        if type(assessment[key]) is not str or assessment[key] not in allowed:
            raise ValueError(f'unsupported assessments.{key}')
    if type(assessment['predictions_computed']) is not bool:
        raise ValueError('assessments.predictions_computed must be boolean')
    evidence = assessment['qualification_evidence_refs']
    if type(evidence) is not list or any(type(item) is not str or not item.strip() for item in evidence):
        raise ValueError('qualification_evidence_refs must be a list of nonempty strings')
    if assessment['declared_bounds_coverage'] != coverage:
        raise ValueError('declared bounds coverage does not match evaluations')
    status = ('VIOLATED' if any(item['status'] == 'VIOLATED' for item in evaluations) else
              'WITHIN' if coverage == 'COMPLETE' else 'INDETERMINATE')
    if assessment['declared_bounds_status'] != status and not (
            assessment['execution'] != 'COMPLETED' and not evaluations and
            assessment['declared_bounds_status'] == 'NOT_ASSESSED'):
        raise ValueError('declared bounds status does not match evaluations or coverage')
    if assessment['scientific_qualification'] == 'QUALIFIED' and (
            not evidence or assessment['execution'] != 'COMPLETED'
            or assessment['model_applicability'] != 'IN_DOMAIN'
            or assessment['numerical_verification'] != 'PASSED'):
        raise ValueError('scientific qualification requires evidence and passed model checks')
    if assessment['execution'] == 'COMPLETED' and assessment['input_validity'] == 'INVALID':
        raise ValueError('completed execution cannot have invalid inputs')
    if assessment['predictions_computed'] and assessment['execution'] != 'COMPLETED':
        raise ValueError('predictions require completed execution')


@dataclass(frozen=True, init=False)
class RunSpec:
    """Immutable snapshot of exact requested and resolved run inputs."""

    _canonical_json: str

    def __init__(self, payload):
        data = _normalize(payload)
        _validate_run(data)
        object.__setattr__(self, '_canonical_json', canonical_json(data))

    @classmethod
    def from_json(cls, text):
        return cls(_read_json(text))

    def to_dict(self):
        return json.loads(self._canonical_json)

    def to_json(self):
        return self._canonical_json + '\n'

    @property
    def sha256(self):
        return hashlib.sha256(self._canonical_json.encode('utf-8')).hexdigest()


@dataclass(frozen=True, init=False)
class ResultBundle:
    """Scientific payload with optional noncanonical execution metadata."""

    _canonical_json: str
    _runtime_metadata_json: str

    def __init__(self, payload, *, runtime_metadata=None):
        data = _normalize(payload)
        _validate_result(data)
        metadata = _normalize({} if runtime_metadata is None else runtime_metadata)
        _object(metadata, 'runtime_metadata')
        object.__setattr__(self, '_canonical_json', canonical_json(data))
        object.__setattr__(self, '_runtime_metadata_json', canonical_json(metadata))

    @classmethod
    def from_json(cls, text):
        data = _read_json(text)
        _object(data, 'ResultBundle envelope')
        metadata = data.pop('runtime_metadata', {})
        return cls(data, runtime_metadata=metadata)

    def to_dict(self, *, include_runtime_metadata=True):
        data = json.loads(self._canonical_json)
        if include_runtime_metadata:
            data['runtime_metadata'] = json.loads(self._runtime_metadata_json)
        return data

    def to_json(self):
        return canonical_json(self.to_dict()) + '\n'

    @property
    def sha256(self):
        return hashlib.sha256(self._canonical_json.encode('utf-8')).hexdigest()

    def verify_run_spec(self, spec: RunSpec):
        if not isinstance(spec, RunSpec) or self.to_dict(include_runtime_metadata=False)['run_spec_sha256'] != spec.sha256:
            raise ValueError('ResultBundle does not match RunSpec digest')
