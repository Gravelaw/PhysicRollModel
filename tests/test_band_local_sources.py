"""SPEC19 package 2: local sources of a hot roll stripe as a band (A2, BT-G4 in full).

Function level: a single sinusoid of friction against the closed-form transfer, zero changes,
signs, sums, the inlet-weight variants, both transfer levels and the missing-term text. Engine
level on the coarse lengthwise case of tests/test_band_v2_sections.py (supplied bite) with one
valve event: the section and the event rows with the key, not-supplied rows without it,
event histories and every other result bit-identical, the report block only with the key.
The battery-foil numbers of the brief are checked against the committed artifact.
"""
import copy
import json
import math
import os
import re
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_local as bl
from physicroll import strip_shape as ss
from physicroll.band_report import render_band_report
from tests.json_close import first_difference
from tests.test_band_local import LOCAL, _coarse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = {'exit_thickness_m': 30e-6, 'bite_half_length_m': 0.0012,
      'strip_stiffness_per_width_pa': 7.4e10, 'roll_radius_m': 0.135,
      'roll_youngs_modulus_pa': 210e9, 'roll_poisson_ratio': 0.3,
      'exit_tension_force_sensitivity_per_width_m': 0.0063, 'strip_youngs_modulus_pa': 70e9,
      'strip_poisson_ratio': 0.33, 'xi': 1.0, 'mean_tension_pa': 40e6,
      'yield_stress_pa': 180e6}
SENS = {'dforce_per_width_dfriction_n_m': 5.14e7, 'dforce_per_width_dflow_stress_m': 0.0112,
        'flow_stress_pa': 175e6}
LAM = 0.1
N = 128
Z = [i * 4 * LAM / N for i in range(N)]


def _changes(dmu=None, dy=None, tx=None):
    return {'friction_change': dmu if dmu is not None else [0.0] * N,
            'flow_stress_change_fraction': dy, 'strip_exit_temperature_k': tx}


def _gain(feedback):
    c = ss.roll_line_compliance_m2_n(LAM, SP['bite_half_length_m'])
    q = SP['strip_stiffness_per_width_pa'] + (
        SP['exit_tension_force_sensitivity_per_width_m'] * SP['strip_youngs_modulus_pa']
        * SP['xi'] / SP['exit_thickness_m'] if feedback else 0.0)
    return 2 * c / (1 + 2 * c * q)


class SourceTermTests(unittest.TestCase):

    def test_single_sinusoid(self):
        dmu = [1e-3 * math.cos(2 * math.pi * x / LAM) for x in Z]
        t = bl.source_terms(Z, _changes(dmu), SP, SENS)
        for fb, key in ((True, 'film_i_units'), (False, 'film_i_units_compliance_only')):
            g = _gain(fb)
            want = [-1e5 * SP['xi'] * g * SENS['dforce_per_width_dfriction_n_m'] * d
                    / SP['exit_thickness_m'] for d in dmu]
            peak = max(abs(v) for v in want)
            for a, b in zip(t[key], want):
                self.assertLessEqual(abs(a - b), 1e-9 * peak)
        # compliance only is larger than with the feedback
        self.assertGreater(max(map(abs, t['film_i_units_compliance_only'])),
                           10 * max(map(abs, t['film_i_units'])))

    def test_signs_zero_and_sums(self):
        bump = [math.exp(-((x - 0.2) / 0.03) ** 2) for x in Z]
        t = bl.source_terms(Z, _changes([1e-3 * b for b in bump], [-1e-3 * b for b in bump],
                                        [340.0 + b for b in bump]), SP, SENS)
        k = max(range(N), key=lambda i: bump[i])
        self.assertLess(t['film_i_units'][k], 0)          # more friction: tight
        self.assertGreater(t['flow_stress_i_units'][k], 0)  # softer metal: loose
        self.assertGreater(t['strip_temperature_i_units'][k], 0)   # hotter fibre: loose
        self.assertEqual(t['missing_terms'], {})
        roll = [5.0 * b - 5.0 * sum(bump) / N for b in bump]
        mech, hot = bl.combine(roll, t)
        for i in range(N):
            self.assertAlmostEqual(mech[i], roll[i] + t['film_i_units'][i]
                                   + t['flow_stress_i_units'][i], delta=1e-12)
            self.assertAlmostEqual(hot[i], mech[i] + t['strip_temperature_i_units'][i],
                                   delta=1e-12)
        z0 = bl.source_terms(Z, _changes(None, [0.0] * N, [340.0] * N), SP, SENS)
        for key in ('film_i_units', 'flow_stress_i_units', 'strip_temperature_i_units'):
            self.assertEqual(set(z0[key]), {0.0}, key)
        self.assertEqual(bl.combine(roll, z0)[0], roll)

    def test_missing_terms_and_text(self):
        bump = [math.exp(-((x - 0.2) / 0.03) ** 2) for x in Z]
        t = bl.source_terms(Z, dict(_changes([1e-3 * b for b in bump]),
                                    flow_stress_reason='no softening coefficient'), SP, SENS)
        self.assertEqual(sorted(t['missing_terms']), ['flow_stress', 'strip_temperature'])
        self.assertIsNone(t['flow_stress_i_units'])
        roll = [30.0 * b for b in bump]
        k = max(range(N), key=lambda i: bump[i])
        wf = [[0.0] * N, [2 * v for v in t['film_i_units']]]
        row = bl.point_row(k, Z, roll, t, wf, t['missing_terms'], 0.5)
        self.assertEqual(row['missing_terms'], ['flow_stress', 'strip_temperature'])
        self.assertIn('softer metal term is missing (no softening coefficient)', row['net_text'])
        self.assertIn('the net is incomplete', row['net_text'])
        self.assertIn('with inlet weight 0 / 1 the net is', row['net_text'])
        self.assertAlmostEqual(row['mechanical_net_at_weight_0_i_units'], roll[k], delta=1e-12)
        self.assertAlmostEqual(row['mechanical_terms_size_i_units'],
                               abs(roll[k]) + abs(t['film_i_units'][k]), delta=1e-12)

    def test_sign_words(self):
        self.assertEqual(bl.sign_word(2.0), 'LOOSE')
        self.assertEqual(bl.sign_word(-2.5), 'TIGHT')
        self.assertEqual(bl.sign_word(1.99), 'BELOW_REPORTING_THRESHOLD')


EVENT = [{'start_s': 0.0, 'duration_s': 20.0, 'nozzle_indices': [18, 19], 'level': 0.0,
          'label': 'zone 18-19 closed'}]


class EngineTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        a = _coarse()
        a['width_model']['events'] = copy.deepcopy(EVENT)
        b = copy.deepcopy(a)
        b['width_model']['local_coupling'] = dict(LOCAL)
        c = copy.deepcopy(a)
        c['width_model']['local_coupling'] = dict(
            LOCAL, flow_stress_temperature_coefficient_per_k=None)
        cls.a, cls.b, cls.c = bd.diagnose(a), bd.diagnose(b), bd.diagnose(c)

    def test_section(self):
        ls = self.b['width']['local_sources']
        self.assertEqual(ls['status'], bl.STATUS, ls.get('reason') or ls.get('error'))
        self.assertIn(bl.SRC_FLAG_COMPUTED, self.b['flags'])
        self.assertEqual(ls['missing_terms'], {})
        self.assertTrue(ls['at_bands'])
        for r in ls['at_bands']:
            self.assertAlmostEqual(r['mechanical_net_i_units'], r['roll_growth_i_units']
                                   + r['film_i_units'] + r['flow_stress_i_units'], delta=1e-9)
            for key in ('net_sign_at_weight_0', 'net_sign', 'net_sign_at_weight_1'):
                self.assertIn(r[key], ('LOOSE', 'TIGHT', 'BELOW_REPORTING_THRESHOLD'))
        self.assertEqual(ls['roll_growth_i_units'],
                         self.b['width']['shape']['steady']['i_units_linear_feedback'])
        sens = ls['sensitivities']
        self.assertEqual(sens['sensitivity_bite_model'], 'derived_slab_hitchcock')
        ts = ls['time_scales']['term_time_scales']
        self.assertIn('body', ts['roll_growth']['follows'])
        self.assertIn('surface', ts['film']['follows'])
        self.assertGreater(ts['roll_growth']['scale_s'], ts['film']['scale_s'])
        co = ls['compliance_only']
        self.assertGreater(abs(co['film_peak_i_units']), abs(co['film_peak_i_units_with_feedback']))
        names = [p['name'] for p in self.b['measurement']['shapemeter']['profiles']] \
            if 'profiles' in (self.b['measurement'].get('shapemeter') or {}) else None
        self.assertTrue(names is None or 'local_mechanical_net' in names)
        json.dumps(ls, allow_nan=False)

    def test_events(self):
        ea = self.a['width']['thermal_events']['events']
        eb = self.b['width']['thermal_events']['events']
        self.assertTrue(ea[0]['local_sources']['not_supplied'])
        lsr = eb[0]['local_sources']
        self.assertEqual(lsr['status'], bl.STATUS, lsr.get('error'))
        self.assertLessEqual(abs(lsr['at_20_s']['time_after_start_s'] - 20.0), 2.0)
        self.assertGreater(lsr['at_20_s']['roll_surface_temperature_change_k'], 0)
        self.assertEqual(self.b['width']['local_sources']['events'][0]['at_20_s'],
                         lsr['at_20_s'])
        for x, y in zip(ea, eb):     # histories and every other key bit-identical
            self.assertEqual({k: v for k, v in x.items() if k != 'local_sources'},
                             {k: v for k, v in y.items() if k != 'local_sources'})

    def test_nothing_else_changes(self):
        a, b = self.a, self.b
        self.assertEqual([(h['id'], h['score'], h['standing'], h['rank'])
                          for h in a['hypotheses']],
                         [(h['id'], h['score'], h['standing'], h['rank'])
                          for h in b['hypotheses']])
        for key in a:
            if key not in ('inputs', 'width', 'flags', 'measurement'):
                self.assertEqual(a[key], b[key], key)
        for key in a['width']:
            if key not in ('local_state', 'local_sources', 'thermal_events'):
                self.assertEqual(a['width'][key], b['width'][key], key)
        self.assertEqual(a['width']['shape']['steady'], b['width']['shape']['steady'])
        self.assertTrue(a['width']['local_sources']['not_supplied'])

    def test_missing_flow_stress_term(self):
        ls = self.c['width']['local_sources']
        self.assertIn('flow_stress', ls['missing_terms'])
        self.assertIsNone(ls['flow_stress_i_units'])
        self.assertIn(bl.SRC_FLAG_MISSING, ls['flags'])
        self.assertIn(bl.SRC_FLAG_MISSING, self.c['flags'])
        self.assertIn('the net is incomplete', ls['at_bands'][0]['net_text'])

    def test_report(self):
        ha, hb = render_band_report(self.a), render_band_report(self.b)
        self.assertNotIn('A hot stripe: roll growth, oil film', ha)
        self.assertIn('A hot stripe: roll growth, oil film', hb)
        self.assertIn('Read the signs, not the digits.', hb)
        self.assertIsNone(re.search(r'\bnan\b|\bNaN\b', hb))
        self.assertIn('the net is incomplete', render_band_report(self.c))

    def test_not_assessable_without_shape_parameters(self):
        out = bl.local_sources_section(
            {}, {'local_coupling': {}}, {'params': {}}, None, {}, None, None, [])
        self.assertEqual(out['status'], 'NOT_ASSESSABLE')
        self.assertIn('shape parameters', out['reason'])


class BatteryFoilArtifactTests(unittest.TestCase):
    """The committed battery-foil artifact against the planner's numbers (SPEC19 package 2,
    peaks within 15 % unless the deviation is reported), pinned to the implementation."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, 'artifacts', 'band_diagnosis',
                               'battery-foil-demo.result.json'), encoding='utf-8') as fh:
            cls.r = json.load(fh)
        cls.ls = cls.r['width']['local_sources']

    def test_steady_and_event(self):
        ls = self.ls
        self.assertEqual(ls['status'], bl.STATUS)
        row = min(ls['at_bands'], key=lambda b: abs(b['position_m'] - 0.6225))
        ev = ls['events'][0]['at_20_s']
        for x, key, pinned in PINS:
            src = {'steady': row, 'event': ev}[x]
            self.assertLess(abs(src[key] / pinned - 1), 1e-6, (x, key, src[key], pinned))
        for x, key, planner, tol in PLANNER:
            src = {'steady': row, 'event': ev}[x]
            self.assertLess(abs(src[key] / planner - 1), tol, (x, key, src[key], planner))
        # the event row at weight 1: planner -1.6, here -0.21: both below the threshold
        self.assertEqual(ev['net_sign_at_weight_1'], 'BELOW_REPORTING_THRESHOLD')
        self.assertEqual((ev['net_sign_at_weight_0'], ev['net_sign']), ('LOOSE', 'LOOSE'))
        self.assertTrue(ev['sign_depends_on_inlet_weight'])
        self.assertLess(abs(ls['compliance_only']['film_peak_i_units'] / -590 - 1), 0.25)
        self.assertIn(bl.SRC_FLAG_WEIGHT, ls['flags'])
        self.assertEqual(ls['sensitivities']['sensitivity_bite_model'],
                         'experimental_mattress')

    def test_recompute_matches_artifact(self):
        lsr = self.r['width']['thermal_events']['events'][0]['local_sources']
        self.assertIsNone(first_difference(lsr['at_20_s'], self.ls['events'][0]['at_20_s']))


PINS = (     # the implementation's own values (whole profiles, mean removed)
    ('steady', 'roll_growth_i_units', 25.088755219209194),
    ('steady', 'film_i_units', -3.7325725867970356),
    ('steady', 'flow_stress_i_units', 0.5657019897486425),
    ('steady', 'strip_temperature_i_units', 4.055703428989846),
    ('steady', 'mechanical_net_i_units', 21.9218846221608),
    ('steady', 'as_measured_hot_i_units', 25.977588051150647),
    ('steady', 'mechanical_net_at_weight_1_i_units', 18.237098849489662),
    ('event', 'roll_growth_i_units', 17.964753960759754),
    ('event', 'film_i_units', -10.031969075842007),
    ('event', 'flow_stress_i_units', 1.5377245247564344),
    ('event', 'strip_temperature_i_units', 11.018599171703443),
    ('event', 'mechanical_net_i_units', 9.470509409674182),
    ('event', 'as_measured_hot_i_units', 20.489108581377625),
    ('event', 'mechanical_net_at_weight_1_i_units', -0.21054279265303344))
# the planner's peak estimates (SPEC19 package 2 table); 15 % except the flow-stress term of
# the steady row (0.566 against 0.7): the prototype used dY = -c_T*w*dT_r, the brief's
# formula 7 0.5*eta_x*dT_r (0.422 against 0.5 of dT_r), which accounts for 16 % of the 19 %
PLANNER = (('steady', 'roll_growth_i_units', 25.1, 0.15), ('steady', 'film_i_units', -4.3, 0.15),
           ('steady', 'flow_stress_i_units', 0.7, 0.20),
           ('steady', 'strip_temperature_i_units', 4.7, 0.15),
           ('steady', 'mechanical_net_i_units', 21.5, 0.15),
           ('steady', 'as_measured_hot_i_units', 26.2, 0.15),
           ('steady', 'mechanical_net_at_weight_1_i_units', 17.2, 0.15),
           ('event', 'roll_growth_i_units', 19.2, 0.15), ('event', 'film_i_units', -11.5, 0.15),
           ('event', 'flow_stress_i_units', 1.8, 0.15),
           ('event', 'strip_temperature_i_units', 12.5, 0.15),
           ('event', 'mechanical_net_i_units', 9.5, 0.15),
           ('event', 'as_measured_hot_i_units', 22.0, 0.15))


if __name__ == '__main__':
    unittest.main()
