"""SPEC17 package 7: a friction / film stripe as a second band source (BT-G4, screening).

The per-pass table of the battery-foil demo (dF/dmu of each pass's bite, the reference 1 %
stripe with and without the exit-tension feedback), the planner's finding on the gauge trend,
supplied stripes, the flagged placeholder conversion, credibility marking, validation, and a
small diagnose pair showing that the screen changes nothing else (no evidence item, open
decision 3). Function-level calls on the demo case (about 12 s) instead of a full diagnose.
"""
import copy
import json
import types
import unittest
from pathlib import Path

from physicroll import band_diagnosis as bd
from physicroll import band_process as bp
from physicroll import band_sensors as bs
from physicroll import band_width as bw
from physicroll.band_report import render_band_report
from tests.test_band_robustness import v2case

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'band_diagnosis'
SCEN = ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json'
STRIPES = [{'position_m': 0.988, 'half_peak_width_m': 0.06, 'friction_change_fraction': -0.10,
            'label': 'minus'},
           {'position_m': 0.988, 'half_peak_width_m': 0.06, 'friction_change_fraction': 0.10,
            'label': 'plus'}]
# implementation values (they agree with the planner's prototype table of SPEC17 to < 1 %)
PINS = {'S1': (709291, 0.637, -4.126, -54.6), 'S2': (612275, 0.666, -3.008, -78.0),
        'S3': (736445, 1.194, -4.442, -235.2), 'F1': (958605, 1.609, -3.149, -392.0),
        'ALT1': (1487662, 1.917, -3.470, -596.6), 'F2': (1536047, 2.159, -2.737, -566.1),
        'ALT2': (6187753, 6.870, -2.288, -871.4)}


def _section(case, stripes=(), with_trib=True):
    cache = bd._BiteCache(case)
    op = cache.get(bp.bite_pass(case, case['pass']))
    sm = bd.perturbed_bite_model(case, op)

    def gb(src):
        return cache.get(bp.bite_pass(case, src))

    def fsens(src):
        if src is case['pass']:
            return bp.friction_force_sensitivity(lambda q: cache.get(q, model=sm),
                                                 bp.bite_pass(case, src))
        m = bd.perturbed_bite_model(case, gb(src))
        return bp.friction_force_sensitivity(lambda q: cache.get(q, model=m),
                                             bp.bite_pass(case, src))
    art = json.loads((ART / 'battery-foil-demo.result.json').read_text())
    w = copy.deepcopy(case['width_model'])
    w['friction_stripe_screen'] = {'reference_half_peak_width_m': None,
                                   'stripes': [dict(s) for s in stripes]}
    th = types.SimpleNamespace(centre=0.75, width=1.2)
    return bw.friction_stripes_section(
        case, w, op, gb, fsens, art['width']['shape']['steady'], th,
        case['tribology'] if with_trib else None,
        art['process']['friction']['operating'] if with_trib else None)


class DemoTableTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.case = bd.validate_case(bd.load_case(SCEN))
        cls.fs = _section(cls.case, STRIPES)

    def test_per_pass_table_and_the_trend_finding(self):
        rows = {r['label'].split()[0]: r for r in self.fs['per_pass']}
        self.assertEqual(set(rows), set(PINS))
        for k, (fpw, n, fb, co) in PINS.items():
            r = rows[k]
            self.assertAlmostEqual(r['force_per_width_n_m'], fpw, delta=1.0)
            self.assertAlmostEqual(r['load_exponent_in_friction'], n, delta=1e-3)
            self.assertAlmostEqual(r['i_units_per_percent_friction_with_feedback'], fb, delta=1e-3)
            self.assertAlmostEqual(r['i_units_per_percent_friction_compliance_only'], co,
                                   delta=0.1)
        self.assertTrue(rows['F1']['is_case_pass'])
        route = [rows[k] for k in ('S1', 'S2', 'S3', 'F1', 'F2')]      # the plant's route
        ex = [r['load_exponent_in_friction'] for r in route]
        co = [abs(r['i_units_per_percent_friction_compliance_only']) for r in route]
        fb = [abs(r['i_units_per_percent_friction_with_feedback']) for r in route]
        self.assertTrue(all(b > a for a, b in zip(ex, ex[1:])))         # exponent rises
        self.assertTrue(all(b > a for a, b in zip(co, co[1:])))         # compliance-only rises
        self.assertLess(max(fb) / min(fb), 2.0)                         # feedback: no trend
        self.assertIn('the least supported element of the shape chain', self.fs['trend_text'])
        self.assertIn('with exit-tension feedback the magnitude is not monotonic',
                      self.fs['trend_text'])
        ref = self.fs['reference']
        self.assertAlmostEqual(ref['friction_change_fraction_for_reporting_threshold'], 0.00635,
                               delta=1e-4)
        self.assertAlmostEqual(ref['feedback_limit_i_units_per_percent'], -3.49, delta=0.01)
        self.assertEqual(self.fs['case_pass']['published_load_exponent'], [2.0, 2.6])
        self.assertIn('0.42', ' '.join(self.fs['limitations']))
        self.assertIn('X17', ' '.join(self.fs['limitations']))

    def test_supplied_stripes(self):
        minus, plus = self.fs['stripes']
        self.assertAlmostEqual(minus['peak_local_thickness_change_m'], -7.874e-08, delta=2e-11)
        self.assertAlmostEqual(minus['peak_i_units'], 32.86, delta=0.02)
        self.assertEqual((minus['sense'], minus['state'], minus['state_after_tension_release']),
                         ('LOOSE_LONG', 'LATENT_UNDER_TENSION', 'MANIFEST_AFTER_TENSION_RELEASE'))
        self.assertEqual((round(minus['band']['start_m'], 3), round(minus['band']['end_m'], 3)),
                         (0.935, 1.04))
        self.assertAlmostEqual(plus['peak_i_units'], -32.71, delta=0.02)
        self.assertEqual((plus['sense'], plus['state'], plus['state_after_tension_release']),
                         ('TIGHT_SHORT', 'LATENT_UNDER_TENSION', 'FLAT_AFTER_TENSION_RELEASE'))
        self.assertNotIn(bw.FS_FLAG_NOT_SATURATED, self.fs['flags'])
        prof = [p['name'] for p in bs.shapemeter_profiles({'friction_stripes': self.fs})]
        self.assertEqual(prof, ['friction_stripe_0', 'friction_stripe_1'])

    def test_placeholder_block(self):
        cv = self.fs['conversion_placeholder']
        self.assertEqual(cv['flags'], ['PLACEHOLDER_FRICTION_CLOSURE_NOT_FITTED'])
        self.assertAlmostEqual(cv['film_ratio'], 0.380, delta=1e-3)
        self.assertAlmostEqual(cv['dmu_dlambda'], -0.0561, delta=1e-4)
        self.assertAlmostEqual(cv['friction_change_per_kelvin_oil'], 3.2e-4, delta=1e-5)
        self.assertAlmostEqual(cv['friction_change_per_kelvin_oil_fraction'], 0.011, delta=5e-4)
        self.assertIn('X22', cv['note'])

    def test_not_credible_row_marked_and_excluded(self):
        res = {'width': {'friction_stripes': copy.deepcopy(self.fs)}}
        bd._apply_credibility(res, self.case, None, [])
        fs = res['width']['friction_stripes']
        alt2 = next(r for r in fs['per_pass'] if r['label'].startswith('ALT2'))
        self.assertEqual(alt2['bite_credibility'], bd.CREDIBILITY_OUTSIDE)
        self.assertIn('Not credible (excluded from the trend): ALT2', fs['trend_text'])
        head = fs['trend_text'].split('Not credible')[0]
        self.assertNotIn('ALT2', head)
        self.assertIn('ALT1', head)


class EdgeTests(unittest.TestCase):

    def test_validation(self):
        raw = json.loads(SCEN.read_text())
        base = raw['width_model']['friction_stripe_screen']
        ok = dict(STRIPES[0])
        for value, msg in (
                (dict(base, reference_half_peak_width_m=2.0),
                 'reference_half_peak_width_m must be in (0, 1] m or null'),
                (dict(base, stripes={}), 'stripes must be a list'),
                (dict(base, stripes=[dict(ok, position_m=-0.1)]),
                 'position_m must be >= 0 and on the barrel'),
                (dict(base, stripes=[dict(ok, position_m=1.6)]),
                 'position_m must be >= 0 and on the barrel'),
                (dict(base, stripes=[dict(ok, half_peak_width_m=0.0)]),
                 'half_peak_width_m must be in (0, 1] m'),
                (dict(base, stripes=[dict(ok, friction_change_fraction=0.0)]),
                 'friction_change_fraction must be in [-0.9, 5] and not 0'),
                (dict(base, stripes=[dict(ok, friction_change_fraction=6.0)]),
                 'friction_change_fraction must be in [-0.9, 5] and not 0'),
                (dict(base, stripes=[dict(ok, label=' ')]), 'label must be a nonempty string')):
            c = copy.deepcopy(raw)
            c['width_model']['friction_stripe_screen'] = value
            with self.assertRaises(ValueError) as cm:
                bd.validate_case(c)
            self.assertIn('width_model.friction_stripe_screen', str(cm.exception))
            self.assertIn(msg, str(cm.exception))

    def test_not_assessable_without_a_bite(self):
        case = bd.validate_case(bd.load_case(SCEN))
        th = types.SimpleNamespace(centre=0.75, width=1.2)
        fs = bw.friction_stripes_section(case, case['width_model'], None, None, None, None, th,
                                         None, None, 'no bite here')
        self.assertEqual(fs['status'], 'NOT_ASSESSABLE')
        self.assertIn('no bite here', fs['reason'])

    def test_absent_input_changes_nothing_else(self):
        c = v2case(width=True)
        a = bd.diagnose(copy.deepcopy(c))
        c['width_model']['friction_stripe_screen'] = {
            'reference_half_peak_width_m': 0.05,
            'stripes': [{'position_m': 0.8, 'half_peak_width_m': 0.04,
                         'friction_change_fraction': 0.2}]}
        b = bd.diagnose(c)
        self.assertTrue(a['width']['friction_stripes']['not_supplied'])
        fs = b['width']['friction_stripes']
        self.assertEqual(fs['status'], 'SCREENING_RESULT_NOT_PLANT_VALIDATED')
        self.assertNotIn('conversion_placeholder', fs)                 # no tribology
        for k in set(a) | set(b):
            if k in ('inputs', 'flags', 'measurement'):
                continue
            if k == 'width':
                self.assertEqual({x: v for x, v in a['width'].items() if x != 'friction_stripes'},
                                 {x: v for x, v in b['width'].items() if x != 'friction_stripes'})
                continue
            self.assertEqual(a.get(k), b.get(k), k)
        self.assertEqual(a['hypotheses'], b['hypotheses'])
        self.assertEqual(set(b['flags']) - set(a['flags']), {bw.FS_FLAG_APPLIED})
        html = render_band_report(b)
        self.assertIn('A friction or oil-film stripe as a band source', html)
        self.assertIn('compliance only', html)
        self.assertNotIn('>nan<', html)
        other = render_band_report(a)
        self.assertIn('No friction-stripe screen requested', other)


if __name__ == '__main__':
    unittest.main()
