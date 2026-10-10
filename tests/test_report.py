"""Offline report keeps saved statuses, unavailable values and input text intact."""

from pathlib import Path
import unittest

from physicroll.report import render_report
from physicroll.run_contract import ResultBundle, RunSpec
from physicroll.workflows import run_workflow


ROOT = Path(__file__).resolve().parents[1]


class ReportTests(unittest.TestCase):
    def test_report_displays_saved_assessments_and_missing_predictions(self):
        spec = RunSpec.from_json(
            (ROOT / 'scenarios/v1_operating_replay.runspec.json').read_bytes())
        result = run_workflow(spec)
        page = render_report(spec, result)
        self.assertIn(spec.sha256, page)
        self.assertIn(result.sha256, page)
        self.assertIn('scientific_qualification', page)
        self.assertIn('operating_readiness', page)
        self.assertIn('predictions_computed', page)
        self.assertIn('>false<', page)
        self.assertIn('not available (null)', page)
        self.assertIn('prepared', page)
        self.assertIn('Checks, limits and residuals', page)
        self.assertNotIn('<script', page)
        self.assertNotIn('src=', page)

    def test_input_text_is_escaped_and_result_identity_checked(self):
        original = RunSpec.from_json(
            (ROOT / 'scenarios/v1_checked_pass.runspec.json').read_bytes())
        modified = original.to_dict()
        modified['requested_inputs']['note'] = '<script>alert("test")</script>'
        spec = RunSpec(modified)
        result_data = run_workflow(original).to_dict(include_runtime_metadata=False)
        result_data['run_spec_sha256'] = spec.sha256
        result = ResultBundle(result_data)
        page = render_report(spec, result)
        self.assertIn('&lt;script&gt;alert(', page)
        self.assertNotIn('<script>alert(', page)
        with self.assertRaisesRegex(ValueError, 'RunSpec'):
            render_report(original, result)


if __name__ == '__main__':
    unittest.main()
