"""Frozen conditional Shao templates through public versioned workflows."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from physicroll.run_contract import ResultBundle, RunSpec
from physicroll.workflows import run_workflow


ROOT = Path(__file__).resolve().parents[1]


class ConditionalWorkflowTests(unittest.TestCase):
    def example(self, kind):
        path = ROOT / f'scenarios/v1_shao_{kind}.runspec.json'
        return path, RunSpec.from_json(path.read_bytes())

    def test_benchmark_and_sensitivity_cli_api_parity(self):
        for kind in ('benchmark', 'sensitivity'):
            with self.subTest(kind=kind):
                path, spec = self.example(kind)
                api = run_workflow(spec)
                with TemporaryDirectory() as directory:
                    output = Path(directory) / 'result.json'
                    subprocess.run([sys.executable, '-m', 'physicroll',
                                    '--run-spec', str(path), '--output', str(output)],
                                   cwd=ROOT, capture_output=True, text=True, check=True)
                    cli = ResultBundle.from_json(output.read_bytes())
                cli.verify_run_spec(spec)
                self.assertEqual(cli.sha256, api.sha256)
                assessment = api.to_dict()['assessments']
                self.assertEqual(assessment['declared_bounds_coverage'], 'NONE')
                self.assertEqual(assessment['declared_bounds_status'], 'INDETERMINATE')
                self.assertEqual(assessment['scientific_qualification'], 'NOT_ASSESSED')
                self.assertEqual(assessment['operating_readiness'], 'NOT_ASSESSED')

    def test_benchmark_preserves_residuals_and_numerical_evidence(self):
        _, spec = self.example('benchmark')
        result = run_workflow(spec).to_dict()
        comparison = result['outputs']['conditional_comparison']
        self.assertEqual(result['assessments']['numerical_verification'], 'PASSED')
        self.assertEqual(comparison['fixture_differences'], [])
        self.assertEqual([round(item['signed_force_residual_fraction'] * 100, 2)
                          for item in comparison['comparisons']], [-3.08, -3.01, 7.79])
        self.assertEqual([round(item['signed_slip_residual_fraction'] * 100, 2)
                          for item in comparison['comparisons']], [41.89, 37.89, 23.79])

    def test_sensitivity_retains_rejection_and_indeterminacy(self):
        _, spec = self.example('sensitivity')
        result = run_workflow(spec).to_dict()
        self.assertEqual(result['assessments']['numerical_verification'], 'NOT_ASSESSED')
        cases = result['outputs']['declared_prior_sensitivity']['cases']
        self.assertEqual([item['status'] for item in cases],
                         ['REJECTED_BY_CHECKED_MODEL'] +
                         ['CONDITIONAL_REPLAY_INDETERMINATE'] * 3)
        self.assertIsNone(cases[0]['comparisons'])

    def test_resource_tampering_or_changed_adapter_claim_rejects(self):
        _, spec = self.example('benchmark')
        data = spec.to_dict()
        raw = 'docs/research/data/shao2015_raw.json'
        data['source_hashes'][raw] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'resource hash mismatch'):
            run_workflow(RunSpec(data))
        data = spec.to_dict()
        data['resolved_inputs']['prior_log_thickness_strain'] = 0.2
        with self.assertRaisesRegex(ValueError, 'resolved inputs differ'):
            run_workflow(RunSpec(data))
        data = spec.to_dict()
        data['model_choices']['bite'] = 'unassisted'
        with self.assertRaisesRegex(ValueError, 'model choices differ'):
            run_workflow(RunSpec(data))
        data = spec.to_dict()
        data['observations']['measurement_uncertainty'] = 0.01
        with self.assertRaisesRegex(ValueError, 'observations or identities differ'):
            run_workflow(RunSpec(data))

    def test_frozen_declarations_reject_boolean_number_substitution(self):
        for kind, field, key, value, message in (
                ('benchmark', 'numerical_settings', 'verify_refinement', 1,
                 'numerical settings differ'),
                ('benchmark', 'requested_inputs', 'fit_performed', 0,
                 'request, observations or identities differ'),
                ('sensitivity', 'resolved_inputs', 'prior_log_thickness_strains',
                 [False, 0.01, 0.05, 0.2], 'resolved inputs differ'),
                ('sensitivity', 'requested_inputs', 'prior_log_thickness_strains',
                 [False, 0.01, 0.05, 0.2],
                 'request, observations or identities differ')):
            with self.subTest(kind=kind, field=field):
                _, spec = self.example(kind)
                data = spec.to_dict()
                data[field][key] = value
                with self.assertRaisesRegex(ValueError, message):
                    run_workflow(RunSpec(data))


if __name__ == '__main__':
    unittest.main()
