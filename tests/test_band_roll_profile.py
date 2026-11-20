"""SPEC17 package 8 (G13): a measured roll ground profile through the existing transfer.

The planner's hand profile on the battery-foil mill (shape parameters of the committed
artifact, supplied): local deviation, stripes, band peaks and states, the shapemeter readings
(the narrow-band case where zone dilution hides a real band), the stiffness indicator,
de-trending and roll count, the combination with the thermal stripes, validation, and a small
diagnose pair (no evidence item; hypotheses identical).
"""
import copy
import json
import math
import types
import unittest
from pathlib import Path

from physicroll import band_diagnosis as bd
from physicroll import band_sensors as bs
from physicroll import band_width as bw
from physicroll import strip_shape as ss
from physicroll.band_report import render_band_report
from tests.test_band_robustness import v2case

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'band_diagnosis'
SCEN = ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json'


def _g(x, c, f):
    return math.exp(-4 * math.log(2) * ((x - c) / f) ** 2)


POS = [round(0.01 * i, 10) for i in range(151)]
DEV = [round(2.0e-6 * (1 - ((x - 0.75) / 0.75) ** 2) + 0.3e-6 * _g(x, 0.50, 0.02)
             - 0.2e-6 * _g(x, 0.95, 0.03), 9) for x in POS]


def _profile(**kw):
    return dict({'positions_m': POS, 'radius_deviation_m': DEV, 'detrend_order': 2,
                 'rolls_carrying': 1, 'provenance': 'hand profile (SPEC17 worked example)'}, **kw)


class HandProfileTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((ART / 'battery-foil-demo.result.json').read_text())
        cls.raw = json.loads(SCEN.read_text())
        iu = cls.r['width']['inputs_used']
        cls.supplied = {k: iu[k] for k in ('strip_stiffness_per_width_pa', 'bite_half_length_m',
                                           'exit_tension_force_sensitivity_per_width_m')}
        cls.ts = cls.r['width']['thermal_steady']
        cls.th = types.SimpleNamespace(centre=0.75, width=1.2)
        cls.bite = types.SimpleNamespace(separating_force_n=958605 * 1.2)
        cls.sec = cls._run(cls)

    def _run(self, **kw):
        raw = copy.deepcopy(self.raw)
        raw['width_model']['roll_ground_profile'] = _profile(**kw)
        case = bd.validate_case(raw)
        w = case['width_model']
        sp = bw.shape_params(case, None, w, None, supplied=self.supplied)
        return bw.roll_profile_section(case, w, sp, None, self.ts['z_m'], self.th, self.ts,
                                       self.bite)

    def test_local_deviation_stripes_and_bands(self):
        s = self.sec
        loose, tight = s['stripes']
        self.assertAlmostEqual(loose['peak_deviation_m'], 2.5827e-07, delta=1e-11)
        self.assertAlmostEqual(loose['peak_position_m'], 0.4975, places=6)
        self.assertAlmostEqual(loose['width_at_half_peak_m'], 0.0227, delta=1e-4)
        self.assertAlmostEqual(tight['peak_deviation_m'], -1.8181e-07, delta=1e-11)
        self.assertAlmostEqual(tight['peak_position_m'], 0.9525, places=6)
        b = {round(x['peak_position_m'], 4): x for x in s['levels']['with_feedback']['bands']}
        self.assertAlmostEqual(b[0.4975]['peak_i_units'], 3.1289, delta=1e-3)
        self.assertEqual((b[0.4975]['state'], b[0.4975]['state_after_tension_release']),
                         ('LATENT_UNDER_TENSION', 'MANIFEST_AFTER_TENSION_RELEASE'))
        self.assertAlmostEqual(b[0.9525]['peak_i_units'], -2.0433, delta=1e-3)
        self.assertEqual((b[0.9525]['state'], b[0.9525]['state_after_tension_release']),
                         ('LATENT_UNDER_TENSION', 'FLAT_AFTER_TENSION_RELEASE'))
        self.assertAlmostEqual(s['compliance_only_peak_i_units'], 360.27, delta=0.01)
        self.assertAlmostEqual(s['rigid_transfer_bound_i_units'], 860.90, delta=0.01)
        self.assertGreater(s['removed_polynomial_peak_to_peak_m'], 1e-6)
        self.assertIn(bw.RP_FLAG_SUPPLIED, s['flags'])
        self.assertIn(bw.RP_FLAG_BAND, s['flags'])
        self.assertEqual(len(s['stripe_table']), 2)
        self.assertIn('measured cold and off the mill', ' '.join(s['limitations']))
        self.assertIn('smoothed', ' '.join(s['limitations']))

    def test_shapemeter_dilution_hides_the_band(self):
        prof = next(p for p in bs.shapemeter_profiles({'roll_profile': self.sec})
                    if p['name'] == 'roll_ground_profile')
        out = bs.read_profile(prof, bs.zone_edges(0.75, 0.052, 23), 0.15, 1.35, 0.0)[0]
        got = [(round(b['zone_reading_i_units'], 4), round(b['reading_to_peak_ratio'], 4),
                b['shows']) for b in out['bands']]
        self.assertAlmostEqual(got[0][0], 1.1780, delta=1e-3)
        self.assertAlmostEqual(got[0][1], 0.3765, delta=1e-3)
        self.assertAlmostEqual(got[1][0], -1.0989, delta=1e-3)
        self.assertAlmostEqual(got[1][1], 0.5378, delta=1e-3)
        self.assertEqual({g[2] for g in got}, {'would probably not show'})

    def test_stiffness_indicator(self):
        st = self.sec['stiffness_check']
        self.assertAlmostEqual(st['strip_foundation_modulus_pa'], 958605 / 20e-6, delta=1e3)
        # the rule of the brief: lam = twice the half-peak width (0.0454 m) -> 6.212e10 Pa; the
        # brief's 6.493e10 is the same formula at a rounded 0.04 m
        self.assertAlmostEqual(st['wavelength_m'], 2 * 0.02269, delta=1e-4)
        self.assertAlmostEqual(st['roll_term_pa'], 6.212e10, delta=0.01e10)
        self.assertAlmostEqual(1 / (2 * ss.roll_line_compliance_m2_n(0.04, 1.19213e-3)),
                               6.493e10, delta=0.002e10)
        self.assertIn('kf2', st['basis'])

    def test_detrend_none_two_rolls_and_thermal(self):
        keep = self._run(detrend_order=None)
        self.assertGreater(max(abs(v) for v in keep['local_radius_deviation_m']), 1.5e-6)
        two = self._run(rolls_carrying=2)
        self.assertAlmostEqual(two['rigid_transfer_bound_i_units'],
                               2 * self.sec['rigid_transfer_bound_i_units'], delta=1e-6)
        self.assertIn('rolls_carrying 2 differs', two['combined_with_thermal']['reason'])
        comb = self.sec['combined_with_thermal']
        st = self.r['width']['shape']['steady']
        k = st['z_m'].index(0.4975)
        # the ground stripe at 0.4975 m adds to the thermal profile there
        self.assertGreater(comb['i_units_with_feedback'][k], st['i_units_with_feedback'][k])

    def test_not_assessable_without_shape_parameters(self):
        case = bd.validate_case(dict(copy.deepcopy(self.raw)))
        case['width_model']['roll_ground_profile'] = bw._validate_roll_profile(_profile(), 1.5)
        out = bw.roll_profile_section(case, case['width_model'], None, 'no bite', [0.0, 1.0],
                                      self.th, None)
        self.assertEqual(out['status'], 'NOT_ASSESSABLE')
        self.assertEqual(out['reason'], 'no bite')

    def test_validation(self):
        for kw, msg in (({'positions_m': POS[:4], 'radius_deviation_m': DEV[:4]},
                         'positions_m must be >= 5 strictly increasing'),
                        ({'positions_m': POS[::-1]}, 'positions_m must be >= 5 strictly'),
                        ({'positions_m': POS[:-1] + [1.6]}, 'positions_m must be >= 5'),
                        ({'radius_deviation_m': DEV[:-1]}, 'radius_deviation_m needs one value'),
                        ({'radius_deviation_m': [2e-3] + DEV[1:]},
                         'radius_deviation_m needs one value'),
                        ({'detrend_order': 7}, 'detrend_order must be an int in [0, 6] or null'),
                        ({'rolls_carrying': 3}, 'rolls_carrying must be 1 or 2'),
                        ({'provenance': ''}, 'provenance must be a nonempty string')):
            raw = copy.deepcopy(self.raw)
            raw['width_model']['roll_ground_profile'] = _profile(**kw)
            with self.assertRaises(ValueError) as cm:
                bd.validate_case(raw)
            self.assertIn('width_model.roll_ground_profile.' + msg, str(cm.exception))


class DiagnoseTests(unittest.TestCase):

    def test_absent_input_changes_nothing_else(self):
        c = v2case(width=True)
        a = bd.diagnose(copy.deepcopy(c))
        c['width_model']['roll_ground_profile'] = {
            'positions_m': [round(0.1 * i, 10) for i in range(18)],
            'radius_deviation_m': [1e-6 * math.exp(-((0.1 * i - 0.9) / 0.1) ** 2)
                                   for i in range(18)],
            'provenance': 'unit test'}
        b = bd.diagnose(c)
        self.assertTrue(a['width']['roll_profile']['not_supplied'])
        self.assertFalse(b['width']['roll_profile']['not_supplied'])
        self.assertEqual(b['width']['roll_profile']['status'], 'LATENT_BANDS_UNDER_TENSION')
        for k in set(a) | set(b):
            if k in ('inputs', 'flags', 'measurement'):
                continue
            if k == 'width':
                self.assertEqual({x: v for x, v in a['width'].items() if x != 'roll_profile'},
                                 {x: v for x, v in b['width'].items() if x != 'roll_profile'})
                continue
            self.assertEqual(a.get(k), b.get(k), k)
        self.assertEqual(a['hypotheses'], b['hypotheses'])     # incl. roll_surface_band etc.
        self.assertTrue(set(b['flags']) - set(a['flags']) <= {bw.RP_FLAG_SUPPLIED,
                                                                bw.RP_FLAG_BAND})
        html = render_band_report(b)
        self.assertIn('Measured roll profile', html)
        self.assertNotIn('>nan<', html)
        self.assertIn('No measured roll profile', render_band_report(a))


if __name__ == '__main__':
    unittest.main()
