"""Saved runs detect mutation and reproduce with the matching installed code."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from physicroll.run_bundle import (create_run_bundle, replay_run_bundle,
                                  verify_run_bundle)
from physicroll.run_contract import RunSpec, canonical_json
from physicroll.report import render_report


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = (
    'v1_checked_pass.runspec.json', 'v1_shao_benchmark.runspec.json',
    'v1_shao_sensitivity.runspec.json', 'v1_operating_replay.runspec.json',
    'v1_schedule_search.runspec.json',
    'v1_prescribed_transport_t1.runspec.json',
    'v1_torque_driven_span_reel_t2.runspec.json',
    'v1_two_reel_span_t2.runspec.json',
)


class RunBundleTests(unittest.TestCase):
    def example(self, name=EXAMPLES[0]):
        return RunSpec.from_json((ROOT / 'scenarios' / name).read_bytes())

    def test_all_public_workflows_verify_and_replay(self):
        with TemporaryDirectory() as temporary:
            for index, name in enumerate(EXAMPLES):
                with self.subTest(name=name):
                    path = Path(temporary) / f'run-{index}'
                    spec = self.example(name)
                    saved = create_run_bundle(spec, path)
                    checked_spec, checked_result = verify_run_bundle(path)
                    self.assertEqual(checked_spec.sha256, spec.sha256)
                    self.assertEqual(checked_result.sha256, saved.sha256)
                    self.assertEqual(replay_run_bundle(path).sha256, saved.sha256)
                    manifest = json.loads((path / 'manifest.json').read_text())
                    self.assertIn('physicroll/workflows.py'.split('/', 1)[1],
                                  manifest['runtime_package_sha256'])
                    self.assertEqual(manifest['result_bundle_sha256'], saved.sha256)
                    self.assertEqual((path / 'report.html').read_text(encoding='utf-8'),
                                     render_report(spec, saved))

    def test_missing_extra_tampered_and_linked_files_reject(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'run'
            create_run_bundle(self.example(), path)
            check = path / 'checks.json'
            original = check.read_bytes()
            check.write_bytes(original + b' ')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify_run_bundle(path)
            check.write_bytes(original)
            manifest_path = path / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            check.write_bytes(original + b' ')
            manifest['files']['checks.json'] = hashlib.sha256(check.read_bytes()).hexdigest()
            manifest_path.write_text(canonical_json(manifest) + '\n')
            with self.assertRaisesRegex(ValueError, 'derived file differs'):
                verify_run_bundle(path)
            check.write_bytes(original)
            manifest['files']['checks.json'] = hashlib.sha256(original).hexdigest()
            manifest_path.write_text(canonical_json(manifest) + '\n')
            report = path / 'report.html'
            original_report = report.read_bytes()
            report.write_bytes(original_report + b'<!-- changed -->')
            manifest['files']['report.html'] = hashlib.sha256(report.read_bytes()).hexdigest()
            manifest_path.write_text(canonical_json(manifest) + '\n')
            with self.assertRaisesRegex(ValueError, 'derived file differs'):
                verify_run_bundle(path)
            report.write_bytes(original_report)
            manifest['files']['report.html'] = hashlib.sha256(original_report).hexdigest()
            manifest_path.write_text(canonical_json(manifest) + '\n')
            check.unlink()
            with self.assertRaisesRegex(ValueError, 'missing, extra'):
                verify_run_bundle(path)
            check.write_bytes(original)
            (path / 'unexpected.txt').write_text('extra')
            with self.assertRaisesRegex(ValueError, 'missing, extra'):
                verify_run_bundle(path)
            (path / 'unexpected.txt').unlink()
            if os.name != 'nt':
                check.unlink()
                check.symlink_to(path / 'result.json')
                with self.assertRaisesRegex(ValueError, 'link'):
                    verify_run_bundle(path)

    def test_runtime_drift_and_existing_destination_reject(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'run'
            create_run_bundle(self.example(), path)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                create_run_bundle(self.example(), path)
            with mock.patch('physicroll.run_bundle._package_hashes',
                            return_value={'changed.py': '0' * 64}):
                with self.assertRaisesRegex(ValueError, 'runtime differs'):
                    verify_run_bundle(path)
            manifest_path = path / 'manifest.json'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            # a major.minor that differs from the running interpreter's (whatever it is)
            other = f'{sys.version_info.major}.{sys.version_info.minor + 1}'
            self.assertNotEqual(manifest['originating_runtime']['python_major_minor'], other)
            manifest['originating_runtime']['python_major_minor'] = other
            manifest['originating_runtime']['python_version'] = other + '.0'
            manifest_path.write_text(canonical_json(manifest) + '\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Python implementation or major.minor'):
                verify_run_bundle(path)

    def test_staging_or_publish_failure_leaves_no_bundle(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for failure, patch_target in (
                    ('staging', 'physicroll.run_bundle.Path.write_bytes'),
                    ('publish', 'physicroll.run_bundle.os.rename')):
                with self.subTest(failure=failure):
                    destination = root / failure
                    with mock.patch(patch_target, side_effect=OSError('injected write failure')):
                        with self.assertRaisesRegex(OSError, 'injected write failure'):
                            create_run_bundle(self.example(), destination)
                    self.assertFalse(destination.exists())
                    self.assertEqual(list(root.iterdir()), [])

    def test_cli_create_verify_replay_outside_checkout(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'run'
            environment = os.environ.copy()
            environment['PYTHONPATH'] = str(ROOT)
            for arguments in (
                    ('create', '--run-spec', str(ROOT / 'scenarios' / EXAMPLES[0]),
                     '--out', str(path)), ('verify', str(path)), ('replay', str(path))):
                completed = subprocess.run(
                    [sys.executable, '-m', 'physicroll.bundle_cli', *arguments],
                    cwd=temporary, env=environment,
                    capture_output=True, text=True, check=True)
                self.assertIn('ResultBundle', completed.stdout)


if __name__ == '__main__':
    unittest.main()
