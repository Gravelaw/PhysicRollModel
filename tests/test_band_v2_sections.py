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

from physicroll.band_diagnosis import (CASE_SCHEMA_V2, HYPOTHESIS_IDS, diagnose, load_case,
                                       result_json, validate_case)
from physicroll.band_report import render_band_report
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
                'Short-lived bands', 'Why thin gauge is worse',
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
             'Short-lived', 'Why thin', 'Hypotheses', 'Transverse-band', 'Chatter stability',
             'Process:', 'Gauge control', 'Limitations'))]
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
        cases = [('width', ('Across the width', 'Short-lived bands', 'Why thin gauge')),
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
        thin = _section(html, 'Why thin')
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
        for h in ('Across the width', 'Why thin gauge is worse'):
            self.assertIn(h, html)
        self.assertIn('Two-tone', html)
        self.assertIn('Incoming ridges and coil build-up', html)
        self.assertIn('Tension troughs', html)
        self.assertIn('not supplied: no width_model.events', html)


if __name__ == '__main__':
    unittest.main()
