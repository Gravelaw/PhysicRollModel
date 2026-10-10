"""Public checked RunSpec adapter and CLI parity, including thermal opt-in."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from physicroll.__main__ import _save_complete
from physicroll.run_contract import ResultBundle, RunSpec
from physicroll.workflows import run_checked_spec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'scenarios/v1_checked_pass.runspec.json'


class CheckedWorkflowTests(unittest.TestCase):
    def example(self):
        return RunSpec.from_json(EXAMPLE.read_bytes()).to_dict()

    def test_checked_example_api_and_cli_agree(self):
        spec = RunSpec(self.example())
        api = run_checked_spec(spec)
        self.assertEqual(api.to_dict()['assessments']['declared_bounds_coverage'], 'NONE')
        self.assertEqual(api.to_dict()['assessments']['declared_bounds_status'],
                         'INDETERMINATE')
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            subprocess.run([sys.executable, '-m', 'physicroll', '--run-spec',
                            str(EXAMPLE), '--output', str(output)],
                           cwd=ROOT, capture_output=True, text=True, check=True)
            cli = ResultBundle.from_json(output.read_bytes())
            cli.verify_run_spec(spec)
            self.assertEqual(api.sha256, cli.sha256)

    def test_declared_violation_and_unevaluated_range_stay_distinct(self):
        data = self.example()
        data['resolved_inputs']['checked_pass']['operating_plan']['ranges'] = [
            {'quantity': 'separating_force_n', 'unit': 'N', 'minimum': 0,
             'maximum': 1, 'phase': 'steady', 'provenance': 'deliberate synthetic test'},
            {'quantity': 'exit_temperature_k', 'unit': 'K', 'minimum': 290,
             'maximum': 320, 'phase': 'steady', 'provenance': 'thermal model absent'},
        ]
        result = run_checked_spec(RunSpec(data)).to_dict()
        bounds = result['checks']['declared_bounds']
        self.assertGreater(len(bounds['required_limit_ids']), 8)
        self.assertEqual(len(bounds['evaluations']), 1)
        self.assertEqual(bounds['evaluations'][0]['status'], 'VIOLATED')
        self.assertEqual(result['assessments']['declared_bounds_coverage'], 'PARTIAL')
        self.assertEqual(result['assessments']['declared_bounds_status'], 'VIOLATED')

    def test_all_six_equipment_limits_do_not_fill_missing_operating_ranges(self):
        data = self.example()
        limits = {
            'provenance': 'synthetic ratings for coverage test',
            'max_separating_force_n': 1e9,
            'max_torque_per_work_roll_nm': 1e9,
            'max_roll_mechanical_power_w': 1e9,
            'max_roll_surface_speed_m_s': 100,
            'max_entry_reel_tension_n': 1e9,
            'max_exit_reel_tension_n': 1e9,
        }
        data['resolved_inputs']['equipment_limits'] = limits
        rated = run_checked_spec(RunSpec(data)).to_dict()
        self.assertEqual(rated['assessments']['declared_bounds_coverage'], 'PARTIAL')
        self.assertEqual(rated['assessments']['declared_bounds_status'], 'INDETERMINATE')
        self.assertEqual(rated['assessments']['scientific_qualification'],
                         'NOT_ASSESSED')
        self.assertEqual(len(rated['checks']['declared_bounds']['evaluations']), 6)
        del limits['max_exit_reel_tension_n']
        incomplete = run_checked_spec(RunSpec(data)).to_dict()
        self.assertEqual(incomplete['assessments']['declared_bounds_coverage'], 'PARTIAL')
        self.assertEqual(incomplete['assessments']['declared_bounds_status'],
                         'INDETERMINATE')

    def test_malformed_collections_reject(self):
        for key in ('ranges', 'observations'):
            for malformed in ({}, '', None):
                data = self.example()
                data['resolved_inputs']['checked_pass']['operating_plan'][key] = malformed
                with self.subTest(key=key, malformed=malformed):
                    with self.assertRaisesRegex(ValueError, 'must be an array'):
                        run_checked_spec(RunSpec(data))

    def test_two_pass_thermal_route_and_handoff(self):
        data = self.example()
        first = data['resolved_inputs'].pop('checked_pass')
        config = json.loads((ROOT / 'scenarios/flowing_energy_demo.json').read_text())
        first['cells'] = 256
        first['heat_boundary'] = config['boundaries'][0]
        first['roll_body_id'] = 'synthetic_roll_A'
        # Resolve the second entry speed from the checked first-pass result.
        first_data = self.example()
        first_speed = run_checked_spec(RunSpec(first_data)).to_dict()[
            'outputs']['checked_schedule']['passes'][0]['mechanics']['exit_speed_m_s']
        second = json.loads(json.dumps(first))
        second['scenario'].update(
            name='checked_second_pass',
            entry_thickness_m=first['scenario']['exit_thickness_m'],
            exit_thickness_m=config['second_pass_exit_thickness_m'],
            entry_speed_m_s=first_speed,
        )
        second['operating_plan']['pass_name'] = 'checked_second_pass'
        second['heat_boundary'] = config['boundaries'][1]
        resolved = data['resolved_inputs']
        resolved['checked_passes'] = [first, second]
        resolved['strip_cp'] = config['strip_heat_capacity']
        resolved['roll_cp'] = config['roll_heat_capacity']
        resolved['interpass_handoffs'] = [
            {'after_pass': 1, 'strip_mode': 'direct_predicted_carry',
             'strip_temperature_k': None, 'roll_mode': 'direct_predicted_carry',
             'roll_temperature_k': None, 'provenance': 'synthetic direct carry',
             'width_change_provenance': None},
        ]
        data['workflow_kind'] = 'checked_schedule'
        data['model_choices']['thermal'] = 'prescribed_energy'
        data['numerical_settings']['cells'] = 256
        result = run_checked_spec(RunSpec(data)).to_dict()
        passes = result['outputs']['checked_schedule']['passes']
        self.assertEqual(len(passes), 2)
        self.assertTrue(all(item['thermal'] is not None for item in passes))
        self.assertEqual(passes[1]['thermal']['boundary']['roll_temperature_k'],
                         passes[0]['thermal']['roll_temperature_out_k'])
        self.assertEqual(result['assessments']['declared_bounds_status'],
                         'INDETERMINATE')

    def test_model_mismatch_and_invalid_cli_keep_existing_output(self):
        data = self.example()
        data['model_choices']['thermal'] = 'prescribed_energy'
        with self.assertRaisesRegex(ValueError, 'model_choices disagree'):
            run_checked_spec(RunSpec(data))
        data = self.example()
        data['resolved_inputs']['unexpected'] = 1
        with self.assertRaisesRegex(ValueError, 'missing or unknown'):
            run_checked_spec(RunSpec(data))
        with TemporaryDirectory() as directory:
            path = Path(directory)
            bad = path / 'bad.json'
            bad.write_text('{"schema_version":"2"}')
            output = path / 'result.json'
            output.write_bytes(b'existing complete result\n')
            process = subprocess.run([sys.executable, '-m', 'physicroll',
                                      '--run-spec', str(bad), '--output', str(output)],
                                     cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(output.read_bytes(), b'existing complete result\n')

    def test_failed_replace_leaves_existing_output_and_no_partial_file(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            output.write_bytes(b'old complete result\n')
            with mock.patch('physicroll.__main__.os.replace',
                            side_effect=OSError('simulated replace failure')):
                with self.assertRaisesRegex(OSError, 'simulated replace failure'):
                    _save_complete(output, 'new result\n')
            self.assertEqual(output.read_bytes(), b'old complete result\n')
            self.assertEqual(list(Path(directory).iterdir()), [output])


if __name__ == '__main__':
    unittest.main()
