"""Closed-loop 'planted truth' checks of the band root-cause screening engine.

Each synthetic case plants one cause (observations generated from the model or from the
kinematics) and asserts that the engine ranks it first. Runs with cells=64 to stay fast.
"""
import copy
import json
import math
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from physicroll import band_signatures as bs
from physicroll.band_diagnosis import (CASE_SCHEMA, HYPOTHESIS_IDS, diagnose, load_case,
                                       rank_hypotheses, result_json, score_evidence,
                                       validate_case)
from physicroll.band_report import render_band_report
from physicroll.chatter import (BitePass, StandModel, StripSpans, derive_bite_response,
                                stability)

ROOT = Path(__file__).resolve().parents[1]
SCEN = ROOT / 'scenarios'
EMPTY_OBS = {
    'orientation': None, 'pitch_observations': [], 'faces': None,
    'gauge_variation_detected': None, 'gauge_variation_amplitude_m': None, 'first_seen': None,
    'disappears_after_work_roll_change': None, 'disappears_after_backup_roll_change': None,
    'onset_above_exit_speed_m_s': None, 'worse_at_thinner_gauge': None,
    'band_positions_across_width_m': [], 'measured_vibration_hz': None}
BEARING = {'name': 'wr_brg', 'shaft': 'work_roll', 'elements': 35,
           'element_diameter_m': 0.0235, 'pitch_diameter_m': 0.34, 'contact_angle_rad': 0.2618}
STAND = StandModel.from_modal_damping(3000.0, 22000.0, 4e10, 1.4e10, 0.03)
SPANS = StripSpans(70e9, 4.0, 4.0)


def baseline(**observation):
    """0.6 -> 0.42 mm pass on the demo mill, cells 64, no schedule, all observations null."""
    obs = dict(EMPTY_OBS)
    obs.update(observation)
    return {
        'case_schema': CASE_SCHEMA, 'name': 'unit baseline', 'synthetic': True,
        'provenance': 'unit test synthetic case',
        'pass': {'entry_thickness_m': 0.6e-3, 'exit_thickness_m': 0.42e-3, 'width_m': 1.5,
                 'work_roll_radius_m': 0.2, 'mean_flow_stress_pa': 250e6,
                 'friction_coefficient': 0.05, 'entry_tension_pa': 25e6,
                 'exit_tension_pa': 30e6, 'exit_speed_m_s': 10.0},
        'material': {'alloy': 'AA5182', 'temper': 'H19', 'yield_stress_pa': 360e6,
                     'youngs_modulus_pa': 70e9, 'luders_strain': 0.01,
                     'magnesium_wt_pct': 4.5, 'grain_size_m': None},
        'stand': {'work_roll_mass_kg': 3000.0, 'backup_roll_mass_kg': 22000.0,
                  'work_backup_contact_stiffness_n_m': 4e10, 'housing_stiffness_n_m': 1.4e10,
                  'modal_damping_ratio': 0.03, 'roll_youngs_modulus_pa': 210e9,
                  'roll_poisson_ratio': 0.3},
        'spans': {'strip_youngs_modulus_pa': 70e9, 'entry_span_length_m': 4.0,
                  'exit_span_length_m': 4.0},
        'kinematics': {'backup_roll_diameter_m': 1.15, 'gear_meshes': [], 'bearings': [],
                       'grinder_marks': [], 'deflector_roll_diameters_m': [],
                       'entry_coil_diameter_m': None, 'exit_coil_diameter_m': None},
        'lubrication': None, 'coolant': None,
        'model_options': {'bite_damping_transit_fraction': 0.5, 'max_radius_ratio': 1.5,
                          'cells': 64, 'bite_response_override': None},
        'observation': obs}


def _bite(case):
    p = case['pass']
    return derive_bite_response(BitePass(
        p['entry_thickness_m'], p['exit_thickness_m'], p['width_m'], p['work_roll_radius_m'],
        p['mean_flow_stress_pa'], p['friction_coefficient'], p['entry_tension_pa'],
        p['exit_tension_pa']), cells=64)


def _by_id(result):
    return {h['id']: h for h in result['hypotheses']}


class BandDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # --- planted third-octave chatter: operate above the model critical speed
        c = baseline()
        bite = _bite(c)
        c['pass']['exit_speed_m_s'] = 18.0
        pitches = []
        for u in (16.0, 18.0):
            f = stability(STAND, bite, SPANS, u)['dominant_frequency_hz']
            pitches.append({'exit_speed_m_s': u, 'pitch_m': u / f})
        c['observation'].update(orientation='transverse', pitch_observations=pitches,
                                faces='both', gauge_variation_detected=True,
                                onset_above_exit_speed_m_s=15.5, worse_at_thinner_gauge=True,
                                disappears_after_work_roll_change=False,
                                disappears_after_backup_roll_change=False)
        c['kinematics']['bearings'] = [dict(BEARING)]
        cls.chatter_case = c
        cls.chatter = diagnose(c)
        cls.slip = bite.forward_slip_fraction

        # --- planted bearing order (2 x BPFI), speed-independent pitch
        b = baseline(orientation='transverse', faces='both', gauge_variation_detected=False,
                     disappears_after_work_roll_change=False,
                     disappears_after_backup_roll_change=False)
        b['kinematics']['bearings'] = [dict(BEARING)]
        orders = bs.bearing_defect_orders(35, 0.0235, 0.34, 0.2618)
        pitch = math.pi * 0.4 * (1 + cls.slip) / (2 * orders['bpfi_order'])
        b['observation']['pitch_observations'] = [{'exit_speed_m_s': 6.0, 'pitch_m': pitch},
                                                  {'exit_speed_m_s': 9.0, 'pitch_m': pitch}]
        b['pass']['exit_speed_m_s'] = 9.0
        cls.bearing = diagnose(b)
        cls.bearing_pitch = pitch

        # --- planted backup-roll-borne mark
        pb = math.pi * 1.15 * (1 + cls.slip)
        r = baseline(orientation='transverse', faces='one',
                     disappears_after_backup_roll_change=True,
                     disappears_after_work_roll_change=False,
                     pitch_observations=[{'exit_speed_m_s': 8.0, 'pitch_m': pb},
                                         {'exit_speed_m_s': 12.0, 'pitch_m': pb}])
        cls.backup = diagnose(r)

        # --- planted yield-point bending marks (5182-O, incoming, diagonal)
        y = baseline(orientation='diagonal', first_seen='incoming_strip',
                     gauge_variation_detected=False)
        y['material'].update(alloy='AA5182', temper='O', yield_stress_pa=139e6,
                             grain_size_m=20e-6)
        y['pass'].update(mean_flow_stress_pa=200e6, exit_speed_m_s=5.0)
        y['kinematics'].update(deflector_roll_diameters_m=[0.12], entry_coil_diameter_m=0.6)
        cls.yield_case = y
        cls.yielding = diagnose(y)

        # --- planted lengthwise band at a blocked nozzle
        cov = bs.spray_coverage(1.7, 0.052, 0.15, 0.6, 0.17, (12,))
        stripe = next(s for s in cov['stripes'] if s['cause'] == 'BLOCKED_NOZZLE')
        n = baseline(orientation='longitudinal', faces='both', worse_at_thinner_gauge=True,
                     band_positions_across_width_m=[stripe['center_m']])
        n['coolant'] = {'barrel_length_m': 1.7, 'nozzle_pitch_m': 0.052, 'standoff_m': 0.15,
                        'spray_angle_rad': 0.6, 'offset_angle_rad': 0.17,
                        'blocked_nozzle_indices': [12], 'roll_expansion_coefficient_per_k': 1.2e-5,
                        'assumed_excess_temperature_k': 5.0}
        cls.nozzle = diagnose(n)
        cls.nozzle_stripe = stripe

        # --- all observations missing
        cls.empty = diagnose(baseline())

        # --- bite derivation failure (radius ratio above 1.5)
        f = baseline(orientation='transverse')
        f['pass'].update(entry_thickness_m=0.30e-3, exit_thickness_m=0.21e-3,
                         mean_flow_stress_pa=270e6, friction_coefficient=0.05)
        cls.failed = diagnose(f)

    # ------------------------------------------------------------- planted truths
    def test_planted_third_octave_chatter_leads(self):
        r = self.chatter
        self.assertEqual(r['leading_hypotheses'][0], 'third_octave_self_excited_chatter')
        self.assertEqual(r['hypotheses'][0]['id'], 'third_octave_self_excited_chatter')
        self.assertFalse(r['chatter']['stability']['stable'])
        for hid in ('fifth_octave_roll_stack_resonance', 'work_roll_borne_marks',
                    'order_locked_drive_or_bearing_excitation'):
            self.assertEqual(_by_id(r)[hid]['standing'], 'CONTRADICTED')
        self.assertEqual(r['signatures']['law'], 'FIXED_FREQUENCY')

    def test_planted_bearing_order_leads_and_names_source(self):
        r = self.bearing
        self.assertEqual(r['leading_hypotheses'], ['order_locked_drive_or_bearing_excitation'])
        best = _by_id(r)['order_locked_drive_or_bearing_excitation']['model_prediction'][
            'best_match']
        self.assertEqual(best['id'], 'bearing:wr_brg:2x_bpfi')
        self.assertLess(best['worst_relative_mismatch'], 1e-9)
        self.assertEqual(r['signatures']['law'], 'SPEED_INDEPENDENT_PITCH')
        self.assertEqual(_by_id(r)['third_octave_self_excited_chatter']['standing'],
                         'CONTRADICTED')

    def test_planted_backup_roll_mark_leads(self):
        r = self.backup
        self.assertEqual(r['leading_hypotheses'], ['backup_roll_borne_marks'])
        h = _by_id(r)
        self.assertEqual(h['work_roll_borne_marks']['standing'], 'CONTRADICTED')
        self.assertEqual(h['fifth_octave_roll_stack_resonance']['standing'], 'CONTRADICTED')

    def test_planted_yield_point_bending_leads(self):
        r = self.yielding
        self.assertEqual(r['leading_hypotheses'], ['yield_point_bending_marks'])
        windows = {w['location']: w['status'] for w in r['screens']['bending_windows']}
        self.assertEqual(windows['deflector_roll:0'], 'IN_YIELD_POINT_WINDOW')
        self.assertTrue(r['screens']['luders_susceptibility']['status'].startswith('SUSCEPTIBLE'))

    def test_planted_blocked_nozzle_band_leads(self):
        r = self.nozzle
        # SPEC6 6.3 replaced lengthwise_coolant_or_thermal_band by nozzle_thermal_stripe; with
        # a v1 coolant section (no width model) its position rule uses the band-risk stripes
        self.assertEqual(r['leading_hypotheses'], ['nozzle_thermal_stripe'])
        risk = r['screens']['band_risk_stripes']
        self.assertTrue(risk and all(s['cause'] == 'BLOCKED_NOZZLE' or s['kind'] == 'UNCOVERED'
                                     for s in risk))
        self.assertEqual(r['screens']['band_position_match']['status'],
                         'ALL_OBSERVED_POSITIONS_MATCHED')

    def test_healthy_header_pattern_is_not_band_risk(self):
        r = self.chatter_case
        c = copy.deepcopy(r)
        c['coolant'] = {'barrel_length_m': 1.7, 'nozzle_pitch_m': 0.052, 'standoff_m': 0.15,
                        'spray_angle_rad': 0.6, 'offset_angle_rad': 0.17,
                        'blocked_nozzle_indices': [], 'roll_expansion_coefficient_per_k': 1.2e-5,
                        'assumed_excess_temperature_k': 5.0}
        cov = bs.spray_coverage(1.7, 0.052, 0.15, 0.6, 0.17, ())
        self.assertTrue(any(s['cause'] == 'NOZZLE_PATTERN' for s in cov['stripes']))
        from physicroll.band_diagnosis import _section_screens
        scr = _section_screens(validate_case(c), None, 0.05, 0.005, 1.3, [])
        self.assertEqual(scr['band_risk_stripes'], [])

    # ------------------------------------------------------------- evidence rules
    def test_missing_observations_never_contradict(self):
        for h in self.empty['hypotheses']:
            for e in h['evidence']:
                if e['basis'] == 'observation':
                    self.assertEqual(e['verdict'], 'NOT_OBSERVED', (h['id'], e))
        # SPEC6 6.3: ten transverse + nine lengthwise hypotheses (was 12 in phase 1)
        self.assertEqual(len(self.empty['hypotheses']), 19)
        self.assertEqual(sorted(h['id'] for h in self.empty['hypotheses']),
                         sorted(HYPOTHESIS_IDS))
        lines = ' '.join(self.empty['recommended_next_measurements'])
        for word in ('two clearly different steady speeds', 'thickness gauge', 'both strip faces',
                     'roll-change', 'orientation'):
            self.assertIn(word, lines)

    def test_scoring_and_standing_rules(self):
        ev = [{'verdict': 'SUPPORTS', 'weight': 'strong'},
              {'verdict': 'SUPPORTS', 'weight': 'weak'},
              {'verdict': 'CONTRADICTS', 'weight': 'moderate'},
              {'verdict': 'NOT_OBSERVED', 'weight': None}]
        t, score, standing = score_evidence(ev)
        self.assertEqual((score, standing), (3 + 1 - 2, 'CONSISTENT'))
        t, score, standing = score_evidence([{'verdict': 'SUPPORTS', 'weight': 'strong'}] * 3 +
                                            [{'verdict': 'CONTRADICTS', 'weight': 'strong'}])
        self.assertEqual((score, standing), (3, 'CONTRADICTED'))
        self.assertEqual(score_evidence([{'verdict': 'NEUTRAL', 'weight': None}])[2],
                         'NOT_ASSESSABLE')
        self.assertEqual(score_evidence([{'verdict': 'CONTRADICTS', 'weight': 'weak'}])[2],
                         'WEAKENED')
        obs = {'observation_supports': 1}
        hyps = [{'id': 'b', 'score': 5, 'standing': 'CONSISTENT', 'tallies': obs},
                {'id': 'a', 'score': 5, 'standing': 'CONSISTENT', 'tallies': obs},
                {'id': 'c', 'score': 9, 'standing': 'CONTRADICTED', 'tallies': obs},
                {'id': 'd', 'score': 2, 'standing': 'CONSISTENT', 'tallies': obs}]
        self.assertEqual(rank_hypotheses(hyps), ['a', 'b'])
        self.assertEqual([h['id'] for h in hyps], ['a', 'b', 'd', 'c'])
        low = [{'id': 'x', 'score': 2, 'standing': 'CONSISTENT', 'tallies': obs}]
        self.assertEqual(rank_hypotheses(low), [])
        # model-only support cannot lead (rule change, see docs/band-diagnosis.md)
        model_only = [{'id': 'm', 'score': 3, 'standing': 'CONSISTENT',
                       'tallies': {'observation_supports': 0}}]
        self.assertEqual(rank_hypotheses(model_only), [])
        self.assertEqual(model_only[0]['standing'], 'CONSISTENT')
        for r in (self.chatter, self.bearing):
            for h in r['hypotheses']:
                self.assertEqual(h['score'], h['tallies']['support_points']
                                 - h['tallies']['contradiction_points'])
            self.assertIn('not a probability', r['score_note'])

    def test_bite_failure_degrades_gracefully(self):
        r = self.failed
        self.assertIsNone(r['bite'])
        self.assertIn('max_radius_ratio', r['bite_error'])
        self.assertIn('BITE_DERIVATION_FAILED_CHATTER_NOT_ASSESSABLE', r['flags'])
        self.assertEqual(r['chatter']['status'], 'NOT_ASSESSABLE')
        self.assertEqual(r['levers']['status'], 'NOT_ASSESSABLE')
        h = _by_id(r)['third_octave_self_excited_chatter']
        margin = next(e for e in h['evidence'] if e['criterion'] == 'speed margin')
        self.assertEqual(margin['verdict'], 'NEUTRAL')
        self.assertIn('NOT_ASSESSABLE', margin['expected'])
        self.assertEqual(len(r['hypotheses']), 19)
        self.assertGreater(r['stand_modes']['natural_frequencies']['fifth_octave_candidate_hz'],
                           0)

    def test_supplied_bite_override(self):
        c = baseline(orientation='transverse')
        bite = _bite(c).to_dict()
        override = {k: bite[k] for k in bite if k not in ('source', 'flags',
                                                          'strip_modulus_n_m')}
        c['model_options']['bite_response_override'] = override
        r = diagnose(c)
        self.assertEqual(r['bite']['source'], 'supplied')
        self.assertIn('BITE_RESPONSE_SUPPLIED', r['flags'])
        friction = [x for x in r['levers']['rows'] if x['lever'] == 'friction']
        self.assertTrue(all('rejected' in x for x in friction))
        span = [x for x in r['levers']['rows'] if x['lever'] == 'entry_span']
        self.assertTrue(all(x['critical_exit_speed_m_s'] for x in span))

    def test_lever_directions_are_computed(self):
        rows = self.chatter['levers']['rows']
        fr = next(x for x in rows if x['lever'] == 'friction' and x['factor'] == 0.7)
        self.assertLess(fr['ratio_to_baseline'], 1.0)
        self.assertAlmostEqual(fr['ratio_to_baseline'], fr['critical_exit_speed_m_s']
                               / self.chatter['levers']['baseline_critical_exit_speed_m_s'])
        d = {x['lever']: x for x in self.chatter['levers']['directions']}
        self.assertEqual(d['friction']['raising_parameter_effect_on_critical_speed'], 'RAISES')
        self.assertTrue(d['friction']['direction'].startswith('lower friction lowers'))
        self.assertIn(f'{fr["ratio_to_baseline"]:.3f}', d['friction']['direction'])
        self.assertEqual(d['entry_span']['raising_parameter_effect_on_critical_speed'], 'RAISES')
        self.assertEqual(d['structural_damping']['raising_parameter_effect_on_critical_speed'],
                         'RAISES')
        keys = [abs(math.log(x['ratio_to_baseline'])) for x in rows
                if x['ratio_to_baseline']]
        self.assertEqual(keys, sorted(keys, reverse=True))

    def test_zero_tension_lever_is_not_assessable(self):
        # SPEC6 6.0 bug 2: a x0.5 / x1.5 change of a zero tension equals the baseline
        c = baseline(orientation='transverse')
        c['pass']['exit_tension_pa'] = 0.0
        r = diagnose(c)
        rows = [x for x in r['levers']['rows'] if x['lever'] == 'exit_tension']
        self.assertTrue(all(x.get('variant_equals_baseline') for x in rows))
        d = {x['lever']: x for x in r['levers']['directions']}
        self.assertEqual(d['exit_tension']['raising_parameter_effect_on_critical_speed'],
                         'NOT_ASSESSABLE')
        self.assertIn('not assessable', d['exit_tension']['direction'])
        self.assertNotIn('lowers', d['exit_tension']['direction'])
        self.assertNotEqual(d['friction']['raising_parameter_effect_on_critical_speed'],
                            'NOT_ASSESSABLE')

    def test_high_damping_variant_is_a_rejected_row(self):
        # SPEC6 6.0 bug 3: doubled modal damping 0.5 -> 1.0 is rejected by StandModel; the
        # diagnosis must complete with that lever row marked rejected
        c = baseline(orientation='transverse')
        c['stand']['modal_damping_ratio'] = 0.5
        r = diagnose(c)
        rows = {x['factor']: x for x in r['levers']['rows']
                if x['lever'] == 'structural_damping'}
        self.assertIn('rejected', rows[2.0])
        self.assertNotIn('rejected', rows[0.5])
        self.assertEqual(len(r['hypotheses']), len(HYPOTHESIS_IDS))

    # ------------------------------------------------------------- validation, output
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
