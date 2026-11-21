"""SPEC19 package 8 in the engine: the width-coupling kernel beside the present levels.

Always computed for a derived case-pass bite; nothing reads it. The demo numbers come from the
committed artifacts (planner, SPEC19 package 8 table: stiffnesses to 0.1 %, peak ratios 15 %).
"""
import copy
import json
from pathlib import Path
import unittest
from unittest import mock

from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl
from physicroll import band_width as bw
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import LONG, NOZZLES, v2, width_model

ART = Path(__file__).resolve().parents[1] / 'artifacts' / 'band_diagnosis'


def _art(name):
    return json.loads((ART / f'{name}.result.json').read_text(encoding='utf-8'))


class DemoArtifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = {n: _art(n) for n in ('lengthwise-bands-demo', 'battery-foil-demo')}

    def _wc(self, n):
        return self.r[n]['width']['shape']['width_coupling']

    def test_lengthwise(self):
        wc = self._wc('lengthwise-bands-demo')
        self.assertEqual(wc['status'], bw.WC_STATUS)
        c = {x['closure']: x for x in wc['closures']}
        self.assertLess(abs(c['no_lateral_velocity']['feedback_stiffness_per_width_pa']
                            / 6.957e11 - 1), 1e-3)
        self.assertAlmostEqual(c['no_lateral_velocity']['ratio_to_pointwise'], 0.690, delta=1e-3)
        self.assertAlmostEqual(c['uniaxial']['ratio_to_pointwise'], 0.241, delta=1e-3)
        self.assertFalse(c['shear_free']['defined'])
        self.assertLess(abs(wc['pointwise']['feedback_stiffness_per_width_pa'] / 1.009e12 - 1),
                        1e-3)
        # planner's single-gain estimate 44.3 against 31.0 pointwise: 1.43 times (15 %)
        self.assertAlmostEqual(wc['kernel_level']['peak_ratio_to_linear_feedback'], 1.43,
                               delta=0.15 * 1.43)
        self.assertIn(bw.WC_FLAG_SIGN, wc['flags'])
        self.assertNotIn(bw.WC_FLAG_BELOW_HALF, wc['flags'])
        rows = self.r['lengthwise-bands-demo']['width']['gauge_trend']['rows']
        case = [x for x in rows if x.get('kernel_feedback_ratio_to_pointwise') is not None]
        self.assertTrue(case)
        self.assertAlmostEqual(rows[-1]['kernel_feedback_ratio_to_pointwise'], 0.690,
                               delta=1e-3)

    def test_battery_foil(self):
        wc = self._wc('battery-foil-demo')
        c = {x['closure']: x for x in wc['closures']}
        self.assertLess(abs(c['no_lateral_velocity']['feedback_stiffness_per_width_pa']
                            / 1.500e12 - 1), 1e-3)
        self.assertAlmostEqual(c['no_lateral_velocity']['ratio_to_pointwise'], 0.102, delta=1e-3)
        self.assertAlmostEqual(c['uniaxial']['ratio_to_pointwise'], 0.0087, delta=1e-4)
        # planner: 210 against 22.8 I-units, 9.2 times (15 %)
        self.assertAlmostEqual(wc['kernel_level']['peak_ratio_to_linear_feedback'], 9.2,
                               delta=0.15 * 9.2)
        self.assertIn(bw.WC_FLAG_BELOW_HALF, wc['flags'])
        self.assertIn(bw.WC_FLAG_BELOW_HALF, self.r['battery-foil-demo']['flags'])
        d = wc['development']
        self.assertAlmostEqual(d['distance_to_95_percent_m'] / d['wavelength_m'], 0.627,
                               delta=0.005)
        self.assertEqual(d['shapemeter_distance_m'], 2.0)

    def test_words_and_the_level_the_tally_uses(self):
        for n in self.r:
            wc = self._wc(n)
            self.assertIn('with-feedback level', wc['used_by_the_evidence'])
            self.assertIn('enters no tally', wc['used_by_the_evidence'])
            self.assertIn('not wavenumber-dependent', wc['meaning'])
            self.assertIn('bracket', wc['meaning'])
            self.assertTrue(any('neither supports nor contradicts' in x
                                for x in wc['limitations']))
            self.assertTrue(any('analyst choice' in x for x in wc['limitations']))
            self.assertIn('An independent estimate of the tension feedback gives', wc['finding'])
            self.assertEqual(len(wc['closures']), 3)
        html = (ART / 'lengthwise-bands-demo.report.html').read_text(encoding='utf-8')
        self.assertIn('with width coupling (kernel)', html)
        self.assertIn('An independent estimate of the tension feedback', html)

    def test_flags_have_plain_sentences(self):
        for f in bw.WC_TOP_FLAGS:
            self.assertIn(f, bpl.FLAGS)


class EngineAlwaysOn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c = v2(override=False, **LONG, band_positions_across_width_m=[NOZZLES[12]],
               lengthwise_continuity='continuous', appearance='loose_or_buckle')
        c['width_model'] = width_model(blocked_nozzle_indices=[12])
        cls.case = c
        cls.on = bd.diagnose(copy.deepcopy(c))
        stub = bw.not_assessable('stub')
        with mock.patch.object(bw, 'width_coupling_section', return_value=stub), \
                mock.patch.object(bw, 'kernel_ratio', return_value=None):
            cls.off = bd.diagnose(copy.deepcopy(c))

    def test_section_present_for_a_derived_bite(self):
        wc = self.on['width']['shape']['width_coupling']
        self.assertEqual(wc['status'], bw.WC_STATUS)
        self.assertIn(bw.WC_FLAG, self.on['flags'])

    def test_nothing_else_changes(self):
        a, b = copy.deepcopy(self.on), copy.deepcopy(self.off)
        for r in (a, b):
            r['width']['shape'].pop('width_coupling')
            r['flags'] = [f for f in r['flags'] if f not in bw.WC_TOP_FLAGS]
            for row in (r['width'].get('gauge_trend') or {}).get('rows', []):
                row.pop('kernel_feedback_ratio_to_pointwise', None)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertIn('with width coupling (kernel)', render_band_report(self.on))

    def test_not_assessable_with_supplied_shape_inputs(self):
        sp = {'kernel_inputs': None}
        self.assertEqual(bw.width_coupling_section({'z_m': [0.0]}, sp)['status'],
                         'NOT_ASSESSABLE')
        self.assertIsNone(bw.kernel_ratio(sp))
        self.assertEqual(bw.width_coupling_section(None, None)['status'], 'NOT_ASSESSABLE')


if __name__ == '__main__':
    unittest.main()
