"""Validation, determinism, report, CLI and scenario tests of the planted cases, split
from tests/test_band_diagnosis.py (BandDiagnosisTests) to keep each module under the
time limit; the planted cases come from its PlantedCasesBase."""
import unittest

from tests import test_band_diagnosis as _base
from tests.test_band_diagnosis import PlantedCasesBase  # the shared fixture class

# the shared fixtures, helpers and imports of the original module (test classes excluded,
# so no test runs twice)
globals().update({k: v for k, v in vars(_base).items() if not k.startswith('__')
                  and not (isinstance(v, type) and issubclass(v, unittest.TestCase))})


class BandDiagnosisReportTests(PlantedCasesBase):
    """The planted cases (PlantedCasesBase): validation, determinism, reports, CLI."""

    def test_strict_validation(self):
        c = baseline()
        c['unexpected'] = 1
        with self.assertRaisesRegex(ValueError, 'unknown keys'):
            validate_case(c)
        c = baseline()
        del c['observation']['faces']
        with self.assertRaisesRegex(ValueError, 'missing keys'):
            validate_case(c)
        c = baseline()
        c['observation']['orientation'] = 'sideways'
        with self.assertRaisesRegex(ValueError, 'orientation'):
            validate_case(c)
        c = baseline()
        c['pass']['friction_coefficient'] = True
        with self.assertRaisesRegex(ValueError, 'friction'):
            validate_case(c)
        c = baseline()
        c['observation']['pitch_observations'] = [{'exit_speed_m_s': 5.0, 'pitch_m': 0.02,
                                                   'x': 1}]
        with self.assertRaises(ValueError):
            validate_case(c)
        c = baseline()
        c['case_schema'] = 'v0'
        with self.assertRaisesRegex(ValueError, 'case_schema'):
            validate_case(c)
        c = baseline()
        c['model_options']['cells'] = 32
        with self.assertRaisesRegex(ValueError, 'cells'):
            validate_case(c)
        c = baseline()
        c['kinematics']['bearings'] = [{'name': 'x'}]
        with self.assertRaises(ValueError):
            validate_case(c)
        c = baseline()
        c['schedule'] = [{'label': 'a', 'entry_thickness_m': 1e-3}]
        with self.assertRaisesRegex(ValueError, 'schedule'):
            validate_case(c)

    def test_synthetic_false_flag_and_determinism(self):
        c = baseline()
        c['synthetic'] = False
        a = diagnose(c)
        self.assertIn('USER_SUPPLIED_INPUTS_NOT_VERIFIED', a['flags'])
        self.assertNotIn('USER_SUPPLIED_INPUTS_NOT_VERIFIED', self.empty['flags'])
        self.assertEqual(result_json(diagnose(baseline())), result_json(self.empty))
        for r in (self.chatter, self.bearing, self.empty, self.failed, self.nozzle):
            json.dumps(r, allow_nan=False)
            self.assertEqual(r['status'], 'SCREENING_RESULT_NOT_PLANT_VALIDATED')

    def test_report_sections_and_escaping(self):
        r = copy.deepcopy(self.chatter)
        r['case_name'] = '<script>alert(1)</script>'
        html = render_band_report(r)
        for heading in ('What the model predicts on the strip', 'Chatter stability',
                        'Pass-schedule sweep', 'Frequency', 'Forced response',
                        'Levers', 'Hypotheses', 'Limitations and sources',
                        'Next measurements'):
            self.assertIn(heading, html)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIsNone(re.search(r'\b(nan|inf|infinity)\b', html, re.IGNORECASE))
        self.assertIn('not a probability', html)
        self.assertEqual(html, render_band_report(r))
        for res in (self.failed, self.nozzle, self.empty):
            out = render_band_report(res)
            self.assertIn('Hypotheses', out)
            self.assertIsNone(re.search(r'\b(nan|inf|infinity)\b', out, re.IGNORECASE))

    def test_report_v1_structure_unchanged_by_phase2(self):
        """A v1 result keeps the phase-1 page: same h2 headings, no phase-2 section."""
        v1 = ['Leading hypotheses', 'Next measurements', 'What the model predicts on the strip',
              'Chatter stability', 'Pass-schedule sweep', 'Frequency-speed map',
              'Forced response and time trace', 'Levers', 'Hypotheses',
              'Limitations and sources']
        for res in (self.chatter, self.bearing, self.nozzle):
            self.assertEqual(res['case_schema'], 'physicroll.band_case.v1')
            html = render_band_report(res)
            self.assertEqual(re.findall(r'<h2[^>]*>([^<]*)</h2>', html), v1)
            for absent in ('Which family of causes', 'Across the width', 'Short-lived bands',
                           'Why thin gauge is worse', 'Process:', 'Gauge control, drive',
                           '<th scope="col">family</th>'):
                self.assertNotIn(absent, html)
            # phase-1 CSS only: the hypothesis and evidence tables keep a minimum width so the
            # hypothesis column does not collapse at phone width (they scroll in place)
            self.assertIn('table.hyp{min-width:46rem}table.evidence{min-width:38rem}', html)

    def test_cli_writes_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / 'case.json'
            case.write_text(json.dumps(self.yield_case))
            out = Path(tmp) / 'out'
            proc = subprocess.run([sys.executable, '-m', 'physicroll.band_cli', str(case),
                                   '--out', str(out)], cwd=ROOT, capture_output=True, text=True,
                                  timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((out / 'unit-baseline.result.json').is_file())
            self.assertTrue((out / 'unit-baseline.report.html').is_file())
            self.assertIn('yield_point_bending_marks', proc.stdout)
            saved = json.loads((out / 'unit-baseline.result.json').read_text())
            self.assertEqual(saved['leading_hypotheses'], ['yield_point_bending_marks'])
            bad = subprocess.run([sys.executable, '-m', 'physicroll.band_cli',
                                  str(Path(tmp) / 'missing.json'), '--out', str(out)], cwd=ROOT,
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(bad.returncode, 2)

    def test_scenario_files_load_and_demos_lead(self):
        template = load_case(SCEN / 'band_diagnosis_template.json')
        self.assertFalse(template['synthetic'])
        self.assertEqual(self.empty['leading_hypotheses'], [])
        self.assertTrue(all(v in (None, []) for v in template['observation'].values()))
        self.assertGreaterEqual(len(template['notes']), 10)
        expected = {'band_diagnosis_thin_gauge_chatter.json': 'third_octave_self_excited_chatter',
                    'band_diagnosis_bearing_order.json':
                        'order_locked_drive_or_bearing_excitation'}
        for name, lead in expected.items():
            case = load_case(SCEN / name)
            self.assertTrue(case['synthetic'])
            case['model_options']['cells'] = 64   # same leading hypothesis as the file's 256
            r = diagnose(case)
            self.assertEqual(r['leading_hypotheses'], [lead], name)
            if name.startswith('band_diagnosis_thin'):
                rows = r['schedule_sweep']['rows']
                self.assertTrue(all('rejected' not in x for x in rows))
                self.assertLess(rows[0]['speed_ratio'], 1.0)
                self.assertGreater(rows[-1]['speed_ratio'], 1.0)
        # the v2 lengthwise demo is run in tests.test_band_lengthwise (time budget)

if __name__ == '__main__':
    unittest.main()
