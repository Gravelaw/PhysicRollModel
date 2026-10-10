"""Portable v1 run data with exact-file verification and installed-code replay.

A bundle requires a matching installed PhysicRollModel package for execution.
Its SHA-256 manifest detects accidental changes; it is not a digital signature.
"""

import csv
import hashlib
from importlib.resources import files
from io import StringIO
import json
import os
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory

from .run_contract import ResultBundle, RunSpec, canonical_json
from .workflows import run_workflow


BUNDLE_VERSION = '1'
REQUIRED_FILES = frozenset({'input.json', 'result.json', 'checks.json',
                            'candidates.jsonl', 'summary.csv'})


def _digest(content):
    return hashlib.sha256(content).hexdigest()


def _package_hashes():
    """Pin installed module and resource bytes, independent of import location."""
    root = files('physicroll')
    result = {}

    def visit(directory, prefix):
        for item in directory.iterdir():
            relative = prefix + item.name
            if item.is_dir():
                visit(item, relative + '/')
            elif item.is_file():
                result[relative] = _digest(item.read_bytes())

    for item in root.iterdir():
        if item.is_file() and item.name.endswith('.py'):
            result[item.name] = _digest(item.read_bytes())
        elif item.name == '_resources' and item.is_dir():
            visit(item, '_resources/')
    if not result:
        raise ValueError('installed PhysicRollModel package has no verifiable files')
    return dict(sorted(result.items()))


def _runtime_identity():
    """Record provenance while allowing cross-OS replay on the same Python line."""
    return {
        'python_implementation': platform.python_implementation(),
        'python_major_minor': f'{sys.version_info.major}.{sys.version_info.minor}',
        'python_version': platform.python_version(),
        'operating_system': platform.system(),
        'architecture': platform.machine(),
    }


def _candidate_records(result):
    outputs = result['outputs']
    if 'schedule_search' in outputs:
        return outputs['schedule_search']['candidates']
    if 'conditional_comparison' in outputs:
        return outputs['conditional_comparison']['search']['candidates']
    if 'declared_prior_sensitivity' in outputs:
        return outputs['declared_prior_sensitivity']['cases']
    return []


def _summary(spec, result, candidate_count):
    assessments = result['assessments']
    columns = ('workflow_kind', 'run_spec_sha256', 'execution', 'input_validity',
               'model_applicability', 'numerical_verification',
               'declared_bounds_status', 'declared_bounds_coverage',
               'scientific_qualification', 'operating_readiness',
               'predictions_computed', 'candidate_count')
    values = (spec['workflow_kind'], result['run_spec_sha256'],
              *(str(assessments[key]).lower() if type(assessments[key]) is bool
                else assessments[key] for key in columns[2:-1]),
              candidate_count)
    stream = StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(columns)
    writer.writerow(values)
    return stream.getvalue().encode('utf-8')


def _payloads(spec, bundle, report_html):
    result = bundle.to_dict(include_runtime_metadata=False)
    candidates = _candidate_records(result)
    contents = {
        'input.json': spec.to_json().encode('utf-8'),
        'result.json': bundle.to_json().encode('utf-8'),
        'checks.json': (canonical_json(result['checks']) + '\n').encode('utf-8'),
        'candidates.jsonl': ''.join(canonical_json(item) + '\n' for item in candidates).encode('utf-8'),
        'summary.csv': _summary(spec.to_dict(), result, len(candidates)),
    }
    if report_html is not None:
        if type(report_html) is not str:
            raise ValueError('report_html must be text')
        contents['report.html'] = report_html.encode('utf-8')
    return contents


def create_run_bundle(spec: RunSpec, destination, *, report_html=None) -> ResultBundle:
    """Compute once, then atomically publish a complete new bundle directory."""
    if not isinstance(spec, RunSpec):
        raise ValueError('create_run_bundle requires a RunSpec')
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('run bundle destination already exists')
    destination.parent.mkdir(parents=True, exist_ok=True)
    bundle = run_workflow(spec)
    bundle.verify_run_spec(spec)
    contents = _payloads(spec, bundle, report_html)
    manifest = {
        'bundle_version': BUNDLE_VERSION,
        'workflow_kind': spec.to_dict()['workflow_kind'],
        'run_spec_sha256': spec.sha256,
        'result_bundle_sha256': bundle.sha256,
        'files': {name: _digest(content) for name, content in sorted(contents.items())},
        'runtime_package_sha256': _package_hashes(),
        'originating_runtime': _runtime_identity(),
    }
    with TemporaryDirectory(dir=destination.parent,
                            prefix=f'.{destination.name}.') as temporary:
        staged = Path(temporary) / 'run'
        staged.mkdir()
        for name, content in contents.items():
            (staged / name).write_bytes(content)
        (staged / 'manifest.json').write_bytes(
            (canonical_json(manifest) + '\n').encode('utf-8'))
        if destination.exists() or destination.is_symlink():
            raise ValueError('run bundle destination appeared during creation')
        os.rename(staged, destination)
    return bundle


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate manifest key: {key}')
        result[key] = value
    return result


def verify_run_bundle(directory) -> tuple[RunSpec, ResultBundle]:
    """Reject missing, extra, modified or linked files and changed runtime."""
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError('run bundle must be a real directory')
    entries = list(directory.iterdir())
    if any(item.is_symlink() or not item.is_file() for item in entries):
        raise ValueError('run bundle contains a link or non-file entry')
    try:
        manifest = json.loads((directory / 'manifest.json').read_bytes(),
                              object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'invalid run manifest: {exc}') from exc
    if (type(manifest) is not dict or set(manifest) != {
            'bundle_version', 'workflow_kind', 'run_spec_sha256',
            'result_bundle_sha256', 'files', 'runtime_package_sha256',
            'originating_runtime'} or
            manifest['bundle_version'] != BUNDLE_VERSION or
            type(manifest['files']) is not dict or
            not REQUIRED_FILES.issubset(manifest['files']) or
            set(manifest['files']) - (REQUIRED_FILES | {'report.html'}) or
            {item.name for item in entries} != set(manifest['files']) | {'manifest.json'}):
        raise ValueError('run manifest has missing, extra or unsupported files')
    for name, expected in manifest['files'].items():
        if type(expected) is not str or _digest((directory / name).read_bytes()) != expected:
            raise ValueError(f'run bundle file hash mismatch: {name}')
    if manifest['runtime_package_sha256'] != _package_hashes():
        raise ValueError('installed PhysicRollModel runtime differs from saved bundle')
    saved_runtime = manifest['originating_runtime']
    current_runtime = _runtime_identity()
    if (type(saved_runtime) is not dict or
            set(saved_runtime) != set(current_runtime) or
            any(type(value) is not str or not value for value in saved_runtime.values()) or
            saved_runtime['python_implementation'] != current_runtime['python_implementation'] or
            saved_runtime['python_major_minor'] != current_runtime['python_major_minor'] or
            not saved_runtime['python_version'].startswith(
                saved_runtime['python_major_minor'] + '.')):
        raise ValueError('Python implementation or major.minor runtime differs from saved bundle')
    spec = RunSpec.from_json((directory / 'input.json').read_bytes())
    bundle = ResultBundle.from_json((directory / 'result.json').read_bytes())
    bundle.verify_run_spec(spec)
    if (manifest['workflow_kind'] != spec.to_dict()['workflow_kind'] or
            manifest['run_spec_sha256'] != spec.sha256 or
            manifest['result_bundle_sha256'] != bundle.sha256):
        raise ValueError('run manifest identity differs from inputs/results')
    expected = _payloads(spec, bundle, None)
    for name in REQUIRED_FILES:
        if (directory / name).read_bytes() != expected[name]:
            raise ValueError(f'run bundle derived file differs from result: {name}')
    return spec, bundle


def replay_run_bundle(directory) -> ResultBundle:
    """Verify the saved run and require the same canonical scientific result."""
    spec, saved = verify_run_bundle(directory)
    replayed = run_workflow(spec)
    if replayed.sha256 != saved.sha256:
        raise ValueError('saved run did not reproduce with installed runtime')
    return replayed
