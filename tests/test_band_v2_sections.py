"""Schema v2 process sections (tribology, hardening, AGC, drive, incoming variation), v2
validation, determinism, CLI, scenario loading, the lengthwise demo and the phase-2 report
sections. Split from tests.test_band_lengthwise to keep each module under 60 s; fixtures are
shared from there (coarse numerics, supplied bite for most cases).
"""
import copy
from html import escape
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from physicroll import mill_dynamics as md
from physicroll import band_process as bp
from physicroll.band_diagnosis import (CASE_SCHEMA_V2, HYPOTHESIS_IDS, MATTRESS_MIN_CELLS,
                                       diagnose, load_case, result_json, validate_case)
from physicroll.band_report import render_band_report
from physicroll.chatter import BitePass
from physicroll.foil_bite import derive_bite_response_mattress
from tests.test_band_lengthwise import (COARSE, HARDENING, LONG, NOZZLES, ROOT, SCEN, TRIBOLOGY,
                                        _h, v2, width_model)


class LengthwiseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c = v2(override=False, **LONG)
        c['tribology'] = dict(TRIBOLOGY, use_computed_friction=True)
        c['hardening'] = dict(HARDENING, use_computed_flow_stress=True)
        c['gauge_control'] = {'compensation_gain': 0.9, 'bandwidth_hz': 25.0,
                              'force_filter_hz': None}
        c['drive'] = {'inertias_kg_m2': [600.0, 120.0, 90.0],
                      'stiffnesses_n_m_rad': [4.0e6, 1.5e6]}
        c['incoming_variation'] = {'flow_stress_variation_fraction': 0.02,
                                   'coil_synchronous': True}
        c['kinematics']['entry_coil_diameter_m'] = 1.2
        c['pass']['exit_speed_m_s'] = 6.0
        cls.full_case = c
        cls.full = diagnose(c)
        p = v2(**LONG)
        p['tribology'] = dict(TRIBOLOGY)
        p['hardening'] = dict(HARDENING)
        cls.plain = diagnose(p)

    def test_hitchcock_film_uses_the_deformed_arc(self):
        # SPEC17 BT-G7 (InletAngleTests): a Hitchcock bite keeps R' for the film's inlet angle
        self.assertEqual(self.full['process']['friction']['operating']['bite_source'],
                         'derived_slab_hitchcock')
        for row in [self.full['process']['friction']['operating'],    # derived Hitchcock
                    self.plain['process']['friction']['operating']]:   # supplied bite
            self.assertEqual(row['film_inlet_radius_ratio'], row['contact_radius_ratio'])
            self.assertEqual(row['inlet_angle_basis'], bp.INLET_ANGLE_BASIS_ARC)

    def test_computed_values_replace_only_when_flagged(self):
        plain, full = self.plain, self.full
        self.assertNotIn('effective_inputs', plain)
        fr = plain['process']['friction']['operating']
        self.assertNotAlmostEqual(fr['computed_friction_coefficient'], 0.05, places=3)
        self.assertEqual(fr['used_friction_coefficient'], 0.05)
        fs = plain['process']['flow_stress']['passes'][0]
        self.assertEqual(fs['used_mean_flow_stress_pa'], 250e6)
        self.assertNotIn('FRICTION_FROM_PLACEHOLDER_CLOSURE', plain['flags'])
        self.assertNotIn('FLOW_STRESS_FROM_HARDENING_LAW', plain['flags'])
        eff = full['effective_inputs']['pass']
        op = full['process']['friction']['operating']
        self.assertEqual(eff['friction_coefficient'], op['computed_friction_coefficient'])
        self.assertEqual(eff['mean_flow_stress_pa'],
                         full['process']['flow_stress']['passes'][0][
                             'computed_mean_flow_stress_pa'])
        self.assertIn('FRICTION_FROM_PLACEHOLDER_CLOSURE', full['flags'])
        self.assertIn('FLOW_STRESS_FROM_HARDENING_LAW', full['flags'])
        self.assertEqual(full['inputs']['pass']['friction_coefficient'], 0.05)
        self.assertLessEqual(len(op['iterations']), 6)
        self.assertTrue(op['converged'])
        curve = full['process']['friction_speed_curve']
        mus = [q['friction_coefficient'] for q in curve['points']]
        self.assertEqual(mus, sorted(mus, reverse=True))
        self.assertLess(curve['mean_slope_per_m_s'], 0)
        heat = full['process']['heating']['operating']
        self.assertGreater(heat['friction_power_per_width_w_m'], 0)
        self.assertAlmostEqual(heat['bite_heat_per_width_w_m'],
                               heat['plastic_power_per_width_w_m']
                               + heat['friction_power_per_width_w_m'])

    def test_speed_consistent_critical_speed_below_fixed_friction(self):
        sc = self.full['chatter']['speed_consistent']
        fixed = sc['fixed_friction_critical_exit_speed_m_s']
        self.assertGreater(fixed, self.full['inputs']['pass']['exit_speed_m_s'])
        self.assertEqual(sc['status'], 'CROSSING_FOUND')
        self.assertLess(sc['speed_consistent_critical_exit_speed_m_s'], fixed)
        u = sc['speed_consistent_critical_exit_speed_m_s']
        self.assertGreater(u, self.full['inputs']['pass']['exit_speed_m_s'])

    def test_gauge_control_static_amplification(self):
        g = self.full['gauge_control']
        m, q = g['mill_modulus_n_m'], g['strip_modulus_n_m']
        self.assertAlmostEqual(g['eccentricity_amplification_vs_no_agc'],
                               (m + q) / (m + 0.1 * q))
        self.assertAlmostEqual(g['runout']['analytic_static_with_agc_tension_off'],
                               -2 * m / (m + 0.1 * q))
        self.assertIsNotNone(g['chatter_with_loop']['with_25_hz_force_filter'])
        self.assertIn('AGC_CHATTER_INTERACTION_DEPENDS_ON_LOOP_ROLL_OFF', self.full['flags'])
        self.assertIn('tension coupling OFF', g['static_formulas_label'])
        self.assertEqual(len(g['runout']['responses']), 4)
        shift = g['speed_change_gauge_shift']
        self.assertLess(shift['delta_friction'], 0)
        self.assertLess(abs(shift['exit_thickness_change_m']),
                        abs(shift['exit_thickness_change_without_agc_m']))

    def test_drive_and_incoming_sections(self):
        d = self.full['drive']
        modes = [m['frequency_hz'] for m in d['catalogue_modes']]
        self.assertEqual(len(modes), 2)
        cat = {e['id'] for e in self.full['signatures']['catalogue']}
        self.assertIn('structural_mode:torsional_1', cat)
        self.assertEqual(len(d['roll_speed_ripple']['responses']), 2)
        tors = _h(self.full)['torsional_or_low_frequency_drive_vibration']
        self.assertIn('torsional_modes_hz', tors['model_prediction'])
        iv = self.full['incoming_variation']
        self.assertLess(abs(iv['static']['exit_thickness_change_m']),
                        abs(iv['static']['exit_thickness_change_without_agc_m']))
        self.assertEqual(len(iv['coil_synchronous']['harmonics']), 3)

    def test_key_numbers_show_the_values_actually_used(self):
        # review finding 2: with use_computed_friction / _flow_stress the report showed the
        # supplied 0.05 although every section used the computed friction (~0.082)
        eff = self.full['effective_inputs']['pass']
        self.assertNotAlmostEqual(eff['friction_coefficient'], 0.05, places=3)
        html = render_band_report(self.full)
        key = html[html.index('Key model numbers'):]
        key = key[:key.index('</table>')]
        self.assertIn(f'<td>friction coefficient used</td><td>{eff["friction_coefficient"]:.4g} '
                      '(computed; supplied 0.05)</td>', key)
        self.assertIn(f'<td>mean flow stress used</td><td>{eff["mean_flow_stress_pa"]:.4g} Pa '
                      '(computed; supplied 2.5e+08 Pa)</td>', key)
        html = render_band_report(self.plain)
        self.assertIn('<td>friction coefficient used</td><td>0.05</td>', html)

    def test_hitchcock_sensitivities_unchanged_by_engine_central_difference(self):
        # review finding 5: the engine's own central difference equals mill_dynamics' for a
        # Hitchcock bite (same steps, same derivation)
        eff = self.full['effective_inputs']['pass']
        bp = BitePass(eff['entry_thickness_m'], eff['exit_thickness_m'], eff['width_m'],
                      eff['work_roll_radius_m'], eff['mean_flow_stress_pa'],
                      eff['friction_coefficient'], eff['entry_tension_pa'],
                      eff['exit_tension_pa'])
        ref = md.flow_stress_sensitivity(bp, cells=64, max_radius_ratio=1.5)
        iv = self.full['incoming_variation']
        self.assertEqual(iv['dforce_dflow_stress_m2'], ref['dforce_dflow_stress_m2'])
        self.assertEqual(iv['dslip_dflow_stress_per_pa'], ref['dslip_dflow_stress_per_pa'])
        self.assertEqual(iv['sensitivity_bite_model'], 'derived_slab_hitchcock')
        ref = md.friction_force_sensitivity(bp, cells=64, max_radius_ratio=1.5)
        self.assertEqual(self.full['gauge_control']['speed_change_gauge_shift'][
            'dforce_dfriction_n'], ref['dforce_dfriction_n'])

    def test_bite_model_auto_falls_back_to_mattress(self):
        c = v2(override=False, **LONG)
        c['pass'].update(entry_thickness_m=0.30e-3, exit_thickness_m=0.21e-3,
                         mean_flow_stress_pa=270e6, friction_coefficient=0.05)
        c['model_options']['bite_model'] = 'auto'
        r = diagnose(c)
        self.assertIsNotNone(r['bite'])
        self.assertIn('BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL', r['bite']['flags'])
        self.assertIn('BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL', r['flags'])
        self.assertIn('max_radius_ratio', r['bite_fallback_reason'])
        self.assertIn(r['chatter']['reliability'], ('WITHIN_SPAN_WAVE_LIMIT',
                                                    'NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT'))
        c['model_options']['bite_model'] = 'hitchcock'
        self.assertIsNone(diagnose(c)['bite'])

    def test_missing_sections_not_supplied_and_v1_unchanged(self):
        r = diagnose(v2(**LONG))
        for key in ('process', 'gauge_control', 'drive', 'incoming_variation', 'width'):
            self.assertEqual(r[key]['status'], 'NOT_SUPPLIED', key)
            self.assertTrue(r[key]['not_supplied'])
        self.assertEqual(len(r['hypotheses']), len(HYPOTHESIS_IDS))
        v1 = load_case(SCEN / 'band_diagnosis_bearing_order.json')
        self.assertEqual(validate_case(v1), v1)          # a validated v1 case round-trips
        self.assertIsNone(v1['width_model'])
        bad = dict(v1, width_model={'roll': {}})
        with self.assertRaisesRegex(ValueError, 'band_case.v2'):
            validate_case(bad)

    def test_validation_v2(self):
        c = v2(**LONG)
        c['observation']['appearance'] = 'sparkly'
        with self.assertRaisesRegex(ValueError, 'appearance'):
            validate_case(c)
        c = v2(**LONG)
        del c['observation']['band_width_m']
        with self.assertRaisesRegex(ValueError, 'missing keys'):
            validate_case(c)
        c = v2(**LONG)
        c['width_model'] = width_model(blocked_nozzle_indices=[99])
        with self.assertRaisesRegex(ValueError, 'out of range'):
            validate_case(c)
        c = v2(**LONG)
        c['width_model'] = width_model(roll_heat_fraction_per_roll=None)
        with self.assertRaisesRegex(ValueError, 'roll_heat_fraction_per_roll'):
            validate_case(c)
        c = v2(**LONG)
        c['tribology'] = dict(TRIBOLOGY, unexpected=1)
        with self.assertRaisesRegex(ValueError, 'unknown keys'):
            validate_case(c)
        c = v2(**LONG)
        c['model_options']['bite_model'] = 'magic'
        with self.assertRaisesRegex(ValueError, 'bite_model'):
            validate_case(c)

    def test_determinism_json_report_and_cli(self):
        c = v2(**LONG, band_positions_across_width_m=[NOZZLES[12]])
        c['width_model'] = width_model(blocked_nozzle_indices=[12], events=[
            {'start_s': 0.0, 'duration_s': 30.0, 'nozzle_indices': [20], 'level': 0.0}])
        a, b = diagnose(c), diagnose(copy.deepcopy(c))
        self.assertEqual(result_json(a), result_json(b))
        for r in (a, self.full, self.plain):
            json.dumps(r, allow_nan=False)
        c['name'] = '<script>alert(1)</script>'
        html = render_band_report(diagnose(c))
        self.assertNotIn('<script>', html)
        self.assertIsNone(re.search(r'\b(nan|inf|infinity)\b', html, re.IGNORECASE))
        self.assertIn('Hypotheses', html)
        html = render_band_report(self.full)
        self.assertIsNone(re.search(r'\b(nan|inf|infinity)\b', html, re.IGNORECASE))
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / 'case.json'
            c['name'] = 'unit v2 cli'
            case.write_text(json.dumps(c))
            out = Path(tmp) / 'out'
            proc = subprocess.run([sys.executable, '-m', 'physicroll.band_cli', str(case),
                                   '--out', str(out)], cwd=ROOT, capture_output=True, text=True,
                                  timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((out / 'unit-v2-cli.result.json').is_file())
            self.assertTrue((out / 'unit-v2-cli.report.html').is_file())


NAN_RE = re.compile(r'\b(nan|inf|infinity)\b', re.IGNORECASE)
H2_RE = re.compile(r'<h2[^>]*>([^<]*)</h2>')
NEW_HEADINGS = ('Which family of causes', 'Across the width: predicted against observed bands',
                'Short-lived bands', 'How the result changes with gauge',
                'Process: friction, flow stress, pass heating',
                'Gauge control, drive and incoming variation',
                'Transverse-band (chatter) screening: supporting detail for this case')
STATES = {'NOT_SUPPLIED': {'status': 'NOT_SUPPLIED', 'not_supplied': True,
                           'reason': 'reason-ns-x'},
          'FAILED': {'status': 'FAILED', 'not_supplied': False, 'error': 'error-fail-x'},
          'NOT_ASSESSABLE': {'status': 'NOT_ASSESSABLE', 'not_supplied': False,
                             'reason': 'reason-na-x'}}


def _section(html, heading):
    """HTML of the <section> whose h2 starts with ``heading``."""
    i = html.index('<h2>' + heading)
    return html[html.rindex('<section', 0, i):html.index('</section>', i)]


class InletAngleTests(unittest.TestCase):
    """SPEC17 BT-G7: the film's inlet angle uses the undeformed roll for a mattress bite (its
    contact_radius_ratio L^2/(R*draft) is not a radius) and the deformed arc R' for a
    Hitchcock bite (unchanged)."""

    def test_mattress_bite_uses_undeformed_roll(self):
        c = v2(override=False, **LONG)
        c['pass'].update(entry_thickness_m=0.12e-3, exit_thickness_m=0.084e-3,
                         mean_flow_stress_pa=285e6, friction_coefficient=0.03)
        c['model_options']['bite_model'] = 'mattress'
        c['tribology'] = dict(TRIBOLOGY)
        r = diagnose(c)
        self.assertIn('BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL', r['bite']['flags'])
        op = r['process']['friction']['operating']
        self.assertEqual(op['film_inlet_radius_ratio'], 1.0)
        self.assertEqual(op['inlet_angle_basis'], bp.INLET_ANGLE_BASIS_MATTRESS)
        ratio = op['contact_radius_ratio']
        self.assertGreater(ratio, 1.0)
        vc = validate_case(c)
        old = bp.friction_at(vc['tribology'], vc['pass'], c['pass']['work_roll_radius_m'],
                             ratio, op['forward_slip_fraction'], op['exit_speed_m_s'])
        new = op['film_ratio'] * ratio ** 0.5
        self.assertLessEqual(abs(new - old['film_ratio']), 1e-9 * old['film_ratio'])

    def test_hitchcock_bite_keeps_the_deformed_arc(self):
        # the Hitchcock operating bite of a diagnose run: LengthwiseIntegrationTests
        # (test_hitchcock_film_uses_the_deformed_arc); here the same call as before the change,
        # pinned from the lengthwise demo artifact
        art = json.loads((ROOT / 'artifacts' / 'band_diagnosis' /
                          'lengthwise-bands-demo.result.json').read_text())
        aop = art['process']['friction']['operating']
        case = validate_case(load_case(SCEN / 'band_diagnosis_lengthwise_bands.json'))
        res = bp.friction_at(case['tribology'], art['effective_inputs']['pass'],
                             case['pass']['work_roll_radius_m'], aop['contact_radius_ratio'],
                             aop['forward_slip_fraction'], aop['exit_speed_m_s'])
        self.assertAlmostEqual(res['film_ratio'], 0.180115, places=6)
        self.assertAlmostEqual(aop['film_ratio'], 0.180115, places=6)


class ReviewFindingTests(unittest.TestCase):
    """Reproducers of code-review findings 1 and 5 (process sections)."""

    def test_schedule_row_labelled_case_pass_keeps_operating_flow_stress(self):
        # finding 1: a schedule row labelled 'case pass' overwrote the operating pass in a
        # label-keyed map: both got the schedule row's 149.0 MPa instead of 267.6 / 149.0
        c = v2(**LONG)
        c['hardening'] = dict(HARDENING, use_computed_flow_stress=True)
        c['schedule'] = [{'label': 'case pass', 'entry_thickness_m': 2.2e-3,
                          'exit_thickness_m': 1.5e-3, 'mean_flow_stress_pa': 150e6,
                          'friction_coefficient': 0.05, 'entry_tension_pa': 20e6,
                          'exit_tension_pa': 25e6, 'exit_speed_m_s': 3.0}]
        r = diagnose(c)
        op, row = r['process']['flow_stress']['passes']
        self.assertAlmostEqual(op['computed_mean_flow_stress_pa'] / 1e6, 267.564, places=2)
        self.assertAlmostEqual(row['computed_mean_flow_stress_pa'] / 1e6, 149.009, places=2)
        eff = r['effective_inputs']
        self.assertEqual(eff['pass']['mean_flow_stress_pa'], op['computed_mean_flow_stress_pa'])
        self.assertEqual(op['used_mean_flow_stress_pa'], op['computed_mean_flow_stress_pa'])
        self.assertEqual(eff['schedule'][0]['mean_flow_stress_pa'],
                         row['computed_mean_flow_stress_pa'])
        self.assertEqual(row['used_mean_flow_stress_pa'], row['computed_mean_flow_stress_pa'])

    def test_mattress_bite_sensitivities_use_the_mattress_model(self):
        # finding 5: with bite_model 'mattress' the flow-stress / friction sensitivities went
        # through the Hitchcock derivation, which rejects this foil pass (R'/R ~2.6 > 1.5):
        # incoming_variation FAILED and the speed-change gauge shift was rejected
        c = v2(override=False, **LONG)
        c['pass'].update(entry_thickness_m=0.12e-3, exit_thickness_m=0.084e-3,
                         mean_flow_stress_pa=285e6, friction_coefficient=0.03)
        c['model_options']['bite_model'] = 'mattress'
        c['tribology'] = dict(TRIBOLOGY)
        c['gauge_control'] = {'compensation_gain': 0.9, 'bandwidth_hz': 25.0,
                              'force_filter_hz': None}
        c['incoming_variation'] = {'flow_stress_variation_fraction': 0.02,
                                   'coil_synchronous': False}
        r = diagnose(c)
        self.assertIn('BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL', r['bite']['flags'])
        iv = r['incoming_variation']
        self.assertEqual(iv['status'], md.STATUS, iv.get('error'))
        self.assertEqual(iv['sensitivity_bite_model'], 'experimental_mattress')
        p = c['pass']
        kw = dict(roll_youngs_modulus_pa=210e9, roll_poisson_ratio=0.3,
                  cells=max(64, MATTRESS_MIN_CELLS))

        def force(y):
            return derive_bite_response_mattress(BitePass(
                p['entry_thickness_m'], p['exit_thickness_m'], p['width_m'],
                p['work_roll_radius_m'], y, p['friction_coefficient'], p['entry_tension_pa'],
                p['exit_tension_pa']), **kw).separating_force_n
        y, dy = p['mean_flow_stress_pa'], 0.005 * p['mean_flow_stress_pa']
        self.assertAlmostEqual(iv['dforce_dflow_stress_m2'],
                               (force(y + dy) - force(y - dy)) / (2 * dy), places=12)
        # the report names the bite model (foil_bite marks its bites source 'supplied')
        self.assertIn('<td>bite source</td><td>experimental_mattress</td>',
                      render_band_report(r))
        shift = r['gauge_control']['speed_change_gauge_shift']
        self.assertNotIn('rejected', shift)
        self.assertEqual(shift['sensitivity_bite_model'], 'experimental_mattress')
        self.assertGreater(shift['dforce_dfriction_n'], 0)


class LengthwiseReportTests(unittest.TestCase):
    """Phase-2 report sections, rendered from the generated v2 demo result (fast)."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / 'artifacts' / 'band_diagnosis' / 'lengthwise-bands-demo.result.json'
        cls.demo = json.loads(path.read_text())
        cls.html = render_band_report(cls.demo)

    def render(self, r):
        html = render_band_report(r)
        self.assertIsNone(NAN_RE.search(html))
        self.assertEqual(html, render_band_report(r))
        return html

    def test_v2_demo_renders_every_new_section_in_order(self):
        self.assertEqual(self.demo['case_schema'], CASE_SCHEMA_V2)
        heads = H2_RE.findall(self.html)
        for h in NEW_HEADINGS:
            self.assertTrue(any(x.startswith(h) for x in heads), h)
        order = [heads.index(x) for x in heads if x.startswith(
            ('Which family', 'Leading hypotheses', 'Next measurements', 'Across the width',
             'Short-lived', 'How the result changes', 'Hypotheses', 'Transverse-band',
             'Chatter stability', 'Process:', 'Gauge control', 'Limitations'))]
        self.assertEqual(order, sorted(order))
        self.assertEqual(len(order), 12)
        self.assertIsNone(NAN_RE.search(self.html))
        self.assertNotIn('<script', self.html)
        self.assertEqual(self.html, render_band_report(self.demo))
        # numbers taken from the result: observed positions, event band life, family counts
        self.assertIn('observed 1.093 m', self.html)
        life = self.demo['width']['thermal_events']['events'][0]['band_life_s']
        self.assertIn(f'band life {life:.3g} s', self.html)
        self.assertIn(escape(self.demo['width']['gauge_trend']['text']), self.html)
        self.assertIn('<th scope="col">family</th>', self.html)
        width = _section(self.html, 'Across the width')
        self.assertIn('aria-label="across the width"', width)
        for k in ('nozzle_pitch_m', 'cooling_zone_pitch_m'):
            self.assertIn({'nozzle_pitch_m': 'nozzle pitch',
                           'cooling_zone_pitch_m': 'cooling-zone pitch'}[k], width)

    def test_gauge_section_neutral_heading_and_direction_sentence(self):
        # the heading asserts no direction; the sentence under it is generated from the rows
        sec = _section(self.html, 'How the result changes with gauge')
        self.assertNotIn('Why thin gauge is worse', self.html)
        lead = re.search(r'<p class="lead">([^<]*)</p>', sec).group(1)
        self.assertTrue(lead.startswith('Direction for this case (model stripe, thick to thin, '
                                        'P1 2.20-&gt;1.40 mm to P6 0.30-&gt;0.21 mm)'), lead)
        self.assertIn('in-mill onset stripe height falls from 3.61 µm to 2.44 µm', lead)
        self.assertIn('overall, not on every pass', lead)
        self.assertIn('after-release onset falls from 0.626 µm to ≤ 0.108 µm', lead)
        self.assertIn('thinner is worse for this mechanism in the model', lead)
        self.assertNotIn('Not assessable', lead)
        # synthetic rows: rising, mixed, and a rejected pass named
        g = copy.deepcopy(self.demo['width']['gauge_trend'])
        rows = g['rows']
        for i, x in enumerate(rows):
            x['manifest_onset_stripe_height_m'] = 1e-6 * (i + 1)
            x['released_onset_stripe_height_m'] = 1e-7 * (i + 1)
        rows[2] = {'label': rows[2]['label'], 'exit_thickness_m': rows[2]['exit_thickness_m'],
                   'rejected': 'unit test'}
        r = copy.deepcopy(self.demo)
        r['width']['gauge_trend'] = g
        sec = _section(self.render(r), 'How the result changes with gauge')
        self.assertIn('thinner is less sensitive for this mechanism in the model', sec)
        self.assertIn('Not assessable (excluded from the direction): P3 0.90-&gt;0.60 mm.', sec)
        for i, x in enumerate(rows):
            if 'rejected' not in x:
                x['released_onset_stripe_height_m'] = 1e-7 / (i + 1)
        sec = _section(self.render(r), 'How the result changes with gauge')
        self.assertIn('the direction is mixed for this mechanism in the model', sec)

    def test_transverse_v2_appends_new_sections_after_chatter(self):
        r = copy.deepcopy(self.demo)
        r['family_summary'].update(observed_family='transverse', leading_family='transverse')
        heads = H2_RE.findall(self.render(r))
        self.assertNotIn('Transverse-band (chatter) screening: supporting detail for this case',
                         heads)
        self.assertLess(heads.index('Levers'), heads.index(
            'Across the width: predicted against observed bands'))
        self.assertLess(heads.index('Gauge control, drive and incoming variation'),
                        heads.index('Hypotheses'))

    def test_each_new_section_state_renders_a_line_and_no_chart(self):
        cases = [('width', ('Across the width', 'Short-lived bands', 'How the result changes')),
                 ('process', ('Process:',)),
                 ('gauge_control', ('Gauge control, drive',)),
                 ('drive', ('Gauge control, drive',)),
                 ('incoming_variation', ('Gauge control, drive',))]
        for key, headings in cases:
            for state, value in STATES.items():
                r = copy.deepcopy(self.demo)
                r[key] = dict(value)
                html = self.render(r)
                text = value.get('reason', value.get('error'))
                label = state.lower().replace('_', ' ')
                for h in headings:
                    sec = _section(html, h)
                    self.assertIn(f'{label}: {text}', sec, (key, state, h))
                    if key in ('width', 'process') and not h.startswith('Process'):
                        self.assertNotIn('<svg', sec, (key, state, h))
                if key == 'process':
                    self.assertNotIn('Friction against exit speed', html)
        for sub in ('thermal_events', 'gauge_trend', 'positions', 'thermal_steady'):
            for state, value in STATES.items():
                r = copy.deepcopy(self.demo)
                r['width'][sub] = dict(value)
                self.render(r)
        r = copy.deepcopy(self.demo)
        r['width']['thermal_events'] = dict(STATES['NOT_SUPPLIED'])
        sec = _section(self.render(r), 'Short-lived bands')
        self.assertNotIn('<svg', sec)
        self.assertIn('not supplied: reason-ns-x', sec)

    def test_engine_follow_up_keys_rendered(self):
        html = self.html
        width = _section(html, 'Across the width')
        # both band states in plain words; linear-feedback profile; saturated peak indicative
        self.assertIn('hidden under mill tension', width)
        self.assertIn('visible after tension release', width)
        self.assertIn('with exit-tension feedback, linear (unsaturated)', width)
        self.assertIn('indicative only', width)
        self.assertIn('Whole-sheet indicator after tension release (upper-bound indicator only',
                      width)
        self.assertIn('not compared: the smallest gap is', width)
        # utilisations above 1 are capped, never printed as magnitudes
        thin = _section(html, 'How the result changes')
        self.assertIn('≥ 1', thin)
        cells = re.findall(r'<td>([^<]*) / ([^<]*)</td>', thin)
        self.assertEqual(len(cells), len(self.demo['width']['gauge_trend']['rows']))
        for v in (v for pair in cells for v in pair):
            self.assertTrue(v == '≥ 1' or float(v) < 1, v)
        # gauge chart: in mill / after release, model stripe / reference, limited markers
        for lab in ('in the mill, model stripe', 'after tension release, model stripe',
                    'in the mill, Gaussian reference', 'after tension release, Gaussian reference',
                    'hollow marker: limited by the reporting threshold (upper bound)',
                    'upper bounds of the buckling onset', '(limited)'):
            self.assertIn(lab, thin)
        self.assertNotIn('50 mm reference', html)
        # events: label as title, visible time with its basis, both thresholds on the chart
        short = _section(html, 'Short-lived')
        for e in self.demo['width']['thermal_events']['events']:
            self.assertIn(escape(e['label']), short)
            self.assertIn(f'{e["visible_time_s"]:.3g} s', short)
        self.assertIn('band buckled in the mill', short)
        self.assertIn('in-mill manifest threshold', short)
        self.assertIn('after-release threshold', short)
        self.assertIn('set by the 2 I-unit reporting threshold', short)

    def test_older_result_without_follow_up_keys_still_renders(self):
        r = copy.deepcopy(self.demo)
        w = r['width']
        w.pop('barrel_length_m')
        st = w['shape']['steady']
        for k in ('i_units_linear_feedback', 'released_status', 'released_global_status',
                  'released_global_max_utilisation', 'manifest_after_release_band_count'):
            st.pop(k, None)
        for lv in st['levels'].values():
            for b in lv['bands']:
                b.pop('state_after_tension_release', None)
        for row in w['gauge_trend']['rows']:
            for k in [k for k in row if 'released' in k or 'reporting_onset' in k
                      or 'reference' in k]:
                row.pop(k)
        for e in w['thermal_events']['events']:
            for k in [k for k in e if 'released' in k or 'visible' in k or k == 'label']:
                e.pop(k)
        for m in w['positions']['spacing_matches'].values():
            m.setdefault('gaps', [])
        html = self.render(r)
        self.assertIn('with exit-tension feedback', html)
        self.assertNotIn('after-release threshold 0', _section(html, 'Short-lived'))
        self.assertIn('in-mill manifest threshold', _section(html, 'Short-lived'))
        self.assertIn('aria-label="across the width"', html)

    def test_hostile_text_is_escaped(self):
        bad = '<script>alert(1)</script>'
        r = copy.deepcopy(self.demo)
        r['case_name'] = bad
        r['inputs']['notes'] = [bad]
        r['hypotheses'][0]['title'] = bad
        r['hypotheses'][0]['mechanism'] = bad
        r['family_summary']['text'] = bad
        r['width']['thermal_events']['growth_rate_note'] = bad
        r['width']['gauge_trend']['rows'][0]['label'] = bad
        r['process']['flow_stress']['passes'][0]['label'] = bad
        html = self.render(r)
        self.assertNotIn('<script', html)
        self.assertGreaterEqual(html.count('&lt;script&gt;'), 8)

    def test_planted_v2_results_render(self):
        """Live v2 results with other sections populated (two-tone, ridges, troughs)."""
        def w(**kw):
            m = width_model(**kw)
            m['numerics'] = dict(COARSE, axial_cell_m=0.05)
            return m
        c = v2(**LONG, band_positions_across_width_m=[0.25, 1.45],
               follows_previous_strip_edges=True)
        c['width_model'] = w(previous_strip_widths_m=[1.2], incoming_ridges=[
            {'position_m': 0.85, 'height_m': 4e-6, 'width_m': 0.03}])
        html = self.render(diagnose(c))
        for h in ('Across the width', 'How the result changes with gauge'):
            self.assertIn(h, html)
        self.assertIn('Two-tone', html)
        self.assertIn('Incoming ridges and coil build-up', html)
        self.assertIn('Tension troughs', html)
        self.assertIn('not supplied: no width_model.events', html)


def _margin_case(damping, speed):
    c = v2(orientation='transverse')
    c['stand']['modal_damping_ratio'] = damping
    c['pass']['exit_speed_m_s'] = speed
    r = diagnose(c)
    h = _h(r)['third_octave_self_excited_chatter']
    return r, h, next(e for e in h['evidence'] if e['criterion'] == 'speed margin')


class SpeedMarginScanRangeTests(unittest.TestCase):
    """Review finding: 'no crossing inside the critical-speed scan (0.05-60 m/s)' is no
    evidence about an operating speed outside it; the operating-point stability decides."""

    def test_above_the_scan_unstable_at_the_operating_point_supports(self):
        # reviewer's reproducer: supplied baseline bite, damping 0.21, 100 m/s
        r, h, e = _margin_case(0.21, 100.0)
        ch = r['chatter']
        self.assertEqual(ch['critical_speed']['status'], 'STABLE_OVER_SCANNED_RANGE')
        self.assertFalse(ch['with_bite_damping']['stable_at_operating_speed'])
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertIn('above the scanned range 0.05-60 m/s', e['observed'])
        self.assertIn('basis: operating-point stability', e['observed'])
        self.assertIn('operating-point stability', e['expected'])
        self.assertEqual(ch['operating_speed_outside_scanned_range']['side'], 'above')
        self.assertIn('OPERATING_SPEED_OUTSIDE_SCANNED_RANGE', r['flags'])
        self.assertEqual(h['score'], 5)          # was 0 with the contradiction (-2 -> +3)
        html = render_band_report(r)
        self.assertIn('does not mean stable at the operating speed', html)

    def test_inside_the_scan_without_crossing_still_contradicts(self):
        r, h, e = _margin_case(0.21, 10.0)
        self.assertEqual(r['chatter']['critical_speed']['status'], 'STABLE_OVER_SCANNED_RANGE')
        self.assertEqual((e['verdict'], e['weight']), ('CONTRADICTS', 'moderate'))
        self.assertEqual(e['expected'], 'u_op >= u_crit(0)')
        self.assertNotIn('operating_speed_outside_scanned_range', r['chatter'])
        self.assertNotIn('OPERATING_SPEED_OUTSIDE_SCANNED_RANGE', r['flags'])

    def test_above_the_scan_stable_at_the_operating_point_contradicts(self):
        r, h, e = _margin_case(0.6, 100.0)
        self.assertTrue(r['chatter']['with_bite_damping']['stable_at_operating_speed'])
        self.assertTrue(r['chatter']['without_bite_damping']['stable_at_operating_speed'])
        self.assertEqual((e['verdict'], e['weight']), ('CONTRADICTS', 'moderate'))
        self.assertIn('rests on the operating point', e['observed'])
        self.assertIn('beyond the scanned range', e['expected'])


class ZeroFeedbackSensitivityTests(unittest.TestCase):
    """Review finding: shape_inputs with exit_tension_force_sensitivity_per_width_m = 0 (no
    exit-tension feedback, the compliance-only limit) validated but failed in strip_shape."""

    def test_zero_supplied_sensitivity_is_assessed(self):
        c = v2(**LONG)
        c['width_model'] = width_model(blocked_nozzle_indices=[12], bite_heat_per_width_w_m=4e5)
        si = {'strip_stiffness_per_width_pa': 4e10,
              'exit_tension_force_sensitivity_per_width_m': 0.0,
              'bite_half_length_m': 5e-3, 'provenance': 'unit test: no feedback'}
        c['width_model']['shape_inputs'] = si
        r = diagnose(c)
        st = r['width']['shape']['steady']
        self.assertNotIn(st.get('status'), ('FAILED', 'NOT_ASSESSABLE', None))
        self.assertEqual(st['tension_feedback_stiffness_per_width_pa'], 0.0)
        self.assertEqual(st['i_units_with_feedback'], st['i_units_compliance_only'])
        self.assertEqual(st['feedback_peak_i_units'], st['compliance_only_peak_i_units'])
        row = next(x for x in r['width']['gauge_trend']['rows']
                   if x['shape_inputs_basis'] == 'shape_inputs_supplied')
        self.assertNotIn('rejected', row)
        self.assertEqual(row['linear_feedback_i_units'], row['compliance_only_i_units'])
        self.assertEqual(row['tension_feedback_stiffness_per_width_pa'], 0.0)
        json.dumps(r, allow_nan=False)
        html = render_band_report(r)
        self.assertNotRegex(html, r'\b(nan|inf|NaN|Infinity)\b')
        bad = copy.deepcopy(c)
        bad['width_model']['shape_inputs']['exit_tension_force_sensitivity_per_width_m'] = -1e-3
        with self.assertRaises(ValueError):
            validate_case(bad)


def _coverage_case(positions, standoff=0.1, half_angle_tan=0.1):
    """No width model, phase-1 coolant coverage: 1.7 m barrel, 0.1 m nozzle pitch, flat fans
    of footprint 2*standoff*half_angle_tan (0.02 m by default)."""
    import math
    c = v2(orientation='longitudinal', band_positions_across_width_m=positions)
    c['coolant'] = {'barrel_length_m': 1.7, 'nozzle_pitch_m': 0.1, 'standoff_m': standoff,
                    'spray_angle_rad': 2 * math.atan(half_angle_tan), 'offset_angle_rad': 0.0,
                    'blocked_nozzle_indices': [], 'roll_expansion_coefficient_per_k': 1.2e-5,
                    'assumed_excess_temperature_k': 5.0}
    r = diagnose(c)
    h = _h(r)['nozzle_thermal_stripe']
    e = next(x for x in h['evidence'] if x['criterion'].startswith('band positions vs model'))
    return r, h, e


class CoverageIntervalMatchTests(unittest.TestCase):
    """Review finding: phase-1 band-risk stripes are intervals; the nozzle hypothesis matched
    only their centres and contradicted a band the coverage screen had matched."""

    def test_band_inside_an_uncovered_interval_matches_as_in_the_screen(self):
        r, h, e = _coverage_case([0.065])      # inside the 0.06-0.14 m gap, 0.035 m off centre
        self.assertEqual(r['screens']['band_position_match']['status'],
                         'ALL_OBSERVED_POSITIONS_MATCHED')
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertIn('inside model intervals 0.06-0.14 m', e['observed'])
        self.assertIn('inside an interval widened by 0.025 m', e['expected'])
        pred = h['model_prediction']
        self.assertAlmostEqual(pred['model_intervals_m'][0][0], 0.06)
        self.assertAlmostEqual(pred['model_intervals_m'][0][1], 0.14)

    def test_band_outside_every_interval_still_contradicts(self):
        # footprint 0.09 m: gaps of 0.01 m around x.x0 m; 0.15 m is 0.045 m from the nearest
        r, h, e = _coverage_case([0.15], half_angle_tan=0.45)
        self.assertEqual(r['screens']['band_position_match']['status'],
                         'NO_OBSERVED_POSITIONS_MATCHED')
        self.assertEqual((e['verdict'], e['weight']), ('CONTRADICTS', 'weak'))
        self.assertIn('no observed position inside or within 0.025 m', e['observed'])

    def test_point_sources_still_match_by_centre(self):
        def run(x):
            c = v2(**LONG, band_positions_across_width_m=[x])
            c['width_model'] = width_model(blocked_nozzle_indices=[12],
                                           bite_heat_per_width_w_m=4e5)
            h = _h(diagnose(c))['nozzle_thermal_stripe']
            return h, next(x for x in h['evidence']
                           if x['criterion'].startswith('band positions vs model'))
        h, e = run(NOZZLES[12])
        self.assertEqual(e['verdict'], 'SUPPORTS')
        self.assertNotIn('model_intervals_m', h['model_prediction'])
        h, e = run(NOZZLES[12] + 0.03)       # tolerance: a quarter of the 52 mm pitch
        self.assertEqual((e['verdict'], e['weight']), ('CONTRADICTS', 'weak'))
        self.assertIn('no observed position near', e['observed'])


class KinematicSlipOnlyTests(unittest.TestCase):
    """Review finding: the zero-slip fallback for a slip of 0.5 or more applies to the
    roll-borne pitch kinematics only, not to the forward-slip screen or the skid evidence."""

    @staticmethod
    def _run(slip):
        c = v2(orientation='irregular')
        c['model_options']['bite_response_override']['forward_slip_fraction'] = slip
        r = diagnose(c)
        h = _h(r)['skidding_loss_of_forward_slip']
        return r, h, h['evidence'][0]

    def test_supplied_slip_above_half_is_not_skidding(self):
        r, h, e = self._run(0.6)
        fs = r['screens']['forward_slip']
        self.assertEqual(fs['status'], 'NOT_ASSESSABLE')
        self.assertEqual(fs['forward_slip_fraction'], 0.6)
        self.assertEqual((e['verdict'], e['basis']), ('NEUTRAL', 'model'))
        self.assertTrue(e['observed'].startswith('0.6000; not assessable'))
        self.assertEqual(h['model_prediction']['forward_slip_fraction'], 0.6)
        self.assertNotEqual(h['standing'], 'CONSISTENT_LEADING')
        self.assertEqual(r['signatures']['forward_slip_fraction_used'], 0.0)
        self.assertIn('FORWARD_SLIP_OUTSIDE_KINEMATICS_DOMAIN_ZERO_USED_IN_KINEMATICS',
                      r['flags'])
        self.assertIn('NOT_ASSESSABLE', render_band_report(r))

    def test_non_positive_slip_still_skids(self):
        r, h, e = self._run(-0.01)
        self.assertEqual(r['screens']['forward_slip']['status'],
                         'SKIDDING_NEUTRAL_POINT_AT_OR_BEYOND_EXIT')
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertEqual(r['signatures']['forward_slip_fraction_used'], -0.01)
        self.assertNotIn('FORWARD_SLIP_OUTSIDE_KINEMATICS_DOMAIN_ZERO_USED_IN_KINEMATICS',
                         r['flags'])


if __name__ == '__main__':
    unittest.main()
