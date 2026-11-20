"""SPEC18 package 11: the spray coefficient calibration routine (A5, command line only).

Twin tests on the battery-foil demo roll with quick numerics (20 mm axial cells, 6 radial
cells): the "measurement" is the model itself at 3400 W/m2K, with and without stated noise.
"""
import copy
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import time
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_thermal as bt
from physicroll import band_width as bw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASE_FILE = os.path.join(ROOT, 'scenarios', 'band_diagnosis_battery_foil.json')
TRUE_H = 3400.0
POSITIONS = [0.2 + 0.1 * i for i in range(12)]


class SprayCalibrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(CASE_FILE) as fh:
            cls.case = json.load(fh)
        t0 = time.perf_counter()
        cls.eff, cls.row, _ = bd.case_pass_heat_row(cls.case)
        cls.heat_row_time = time.perf_counter() - t0
        w = cls.eff['width_model']
        frac, _, heat, _, _ = bw.thermal_heat_inputs(w, cls.eff['tribology'], cls.row)
        cls.model = staticmethod(bt._calibration_model(cls.eff, w, heat, frac,
                                                       dict(bt.CALIBRATION_QUICK)))
        cls.frac = frac

    def twin(self, kind, h=TRUE_H, noise=0.0, **extra):
        probe = bt.validate_calibration(
            dict(kind=kind, positions_m=POSITIONS, values=[300.0] * 12 if kind != 'thermal_camber'
                 else [0.0] * 12, provenance='twin', **extra), 1.5)
        vals = self.model(h, probe)
        rnd = random.Random(7)
        vals = [v + rnd.gauss(0.0, noise) for v in vals] if noise else vals
        return dict(kind=kind, positions_m=POSITIONS, values=vals, provenance='twin', **extra)

    def fit(self, cal, **kw):
        return bt.calibrate_spray_coefficient(self.case, cal, heat_row=self.row, **kw)

    def test_twin_recovers_both_kinds(self):
        for kind, extra in (('thermal_camber', {}),
                            ('roll_surface_temperature_after_stop', {'seconds_after_stop': 30.0})):
            t0 = time.perf_counter()
            r = self.fit(self.twin(kind, **extra))
            self.assertLess(time.perf_counter() - t0, 60)          # budget, quick numerics
            self.assertEqual(r['outcome'], 'FITTED', kind)
            self.assertEqual(r['status'], bt.CALIBRATION_STATUS)
            self.assertAlmostEqual(r['fitted_spray_mean_htc_w_m2k'] / TRUE_H, 1, delta=0.02)
            curve = r['misfit_curve']
            best = min(curve, key=lambda x: x['misfit_rms'])
            self.assertAlmostEqual(best['spray_mean_htc_w_m2k'] / TRUE_H, 1, delta=0.02)
            self.assertLessEqual(len(curve), bt.CALIBRATION_SCAN + bt.CALIBRATION_GOLDEN_MAX)
            self.assertEqual(r['how_to_use'], bt.CALIBRATION_HOW_TO_USE)
            self.assertIn('THIS model', r['basis'])
            self.assertIn('not compared', r['basis'])
            self.assertIn('heat_share_sensitivity', r)
            self.assertGreater(r['heat_share_sensitivity'][
                'dln_fitted_over_dln_roll_heat_fraction'], 0)
            self.assertEqual(len(r['residuals']), 12)
            self.assertNotIn('footprint_equivalent_w_m2k', r)     # no wetted arc in the case

    def test_noisy_round_trip_inside_the_reported_interval(self):
        """Noise of the stated standard deviation added: the true coefficient lies inside the
        interval the routine reports for that uncertainty."""
        for kind, extra, sigma in (('thermal_camber', {}, 2e-7),
                                   ('roll_surface_temperature_after_stop',
                                    {'seconds_after_stop': 30.0}, 0.2)):
            cal = self.twin(kind, noise=sigma, uncertainty=sigma, **extra)
            r = self.fit(cal)
            self.assertEqual(r['outcome'], 'FITTED', kind)
            lo, hi = r['range_within_measurement_uncertainty_w_m2k']
            self.assertLess(lo, TRUE_H, kind)
            self.assertGreater(hi, TRUE_H, kind)
            self.assertLess(hi / lo, 3.0, kind)                    # still informative

    def test_footprint_equivalent_with_a_wetted_arc(self):
        case = copy.deepcopy(self.case)
        case['width_model']['spray_wetted_arc_rad'] = math.pi / 3
        r = bt.calibrate_spray_coefficient(case, self.twin('thermal_camber'), heat_row=self.row)
        bg = case['width_model']['spray_header']['background_htc_w_m2k']
        self.assertAlmostEqual(r['footprint_equivalent_w_m2k'],
                               bg + r['fitted_spray_mean_htc_w_m2k'] * 6, delta=1e-6)

    def test_at_search_limit(self):
        r = self.fit(self.twin('thermal_camber', h=60000.0))
        self.assertEqual(r['outcome'], 'AT_SEARCH_LIMIT')
        self.assertIsNone(r['fitted_spray_mean_htc_w_m2k'])
        self.assertAlmostEqual(r['minimum_at_w_m2k'], 20000.0, delta=1e-6)

    def test_header_off_long_after_the_stop_is_not_determined(self):
        """A scan with the whole header off (every nozzle level 0) taken long after the stop
        carries no information on the spray coefficient: the misfit curve is flat and the
        routine refuses with a named outcome, no number."""
        case = copy.deepcopy(self.case)
        case['width_model']['nozzle_levels'] = [0.0] * len(
            bw.spray_layout(case)['nozzle_positions_m'])
        eff = bd.validate_case(case)
        w = eff['width_model']
        frac, _, heat, _, _ = bw.thermal_heat_inputs(w, eff['tribology'], self.row)
        model = bt._calibration_model(eff, w, heat, frac, dict(bt.CALIBRATION_QUICK))
        cal = dict(kind='roll_surface_temperature_after_stop', positions_m=POSITIONS,
                   values=[300.0] * 12, provenance='header off', seconds_after_stop=3600.0)
        cal['values'] = model(TRUE_H, bt.validate_calibration(cal, 1.5))
        rnd = random.Random(3)
        cal['values'] = [v + rnd.gauss(0.0, 0.05) for v in cal['values']]
        cal['uncertainty'] = 0.05
        r = bt.calibrate_spray_coefficient(case, cal, heat_row=self.row)
        self.assertEqual(r['outcome'], 'NOT_DETERMINED_FLAT_MISFIT')
        self.assertIsNone(r['fitted_spray_mean_htc_w_m2k'])
        lo, hi = r['range_within_10_percent_of_minimum_w_m2k']
        self.assertAlmostEqual(lo, 500.0, delta=1e-6)
        self.assertAlmostEqual(hi, 20000.0, delta=1e-6)

    def test_refusals(self):
        r = self.fit(dict(kind='thermal_camber', positions_m=[0.2, 0.4, 0.6, 0.8],
                          values=[0.0, 1e-6, 2e-6, 1e-6], provenance='x'))
        self.assertEqual((r['outcome'], r['fitted_spray_mean_htc_w_m2k']), ('TOO_FEW_POINTS', None))
        r = self.fit(dict(kind='thermal_camber', positions_m=POSITIONS, values=[1e-6] * 12,
                          provenance='x'))
        self.assertEqual(r['outcome'], 'NO_CONTRAST')
        cal = self.twin('roll_surface_temperature_after_stop', seconds_after_stop=30.0,
                        uncertainty=100.0)
        self.assertEqual(self.fit(cal)['outcome'], 'NO_CONTRAST')

    def test_validation_messages(self):
        good = dict(kind='thermal_camber', positions_m=POSITIONS, values=[0.0] * 12,
                    provenance='x')
        for bad, msg in ((dict(kind='camber'), 'calibration.kind must be one of'),
                         (dict(positions_m=POSITIONS[::-1]), 'strictly increasing'),
                         (dict(positions_m=[0.2] + POSITIONS[1:-1] + [9.0]), 'the barrel'),
                         (dict(values=[0.0] * 11), 'same length'),
                         (dict(values=[2e-3] * 12), '[-1e-3, 1e-3] m'),
                         (dict(search_range_w_m2k=[50, 100]), '100 <= lo < hi <= 1e5'),
                         (dict(seconds_after_stop=10.0), 'only for'),
                         (dict(provenance=' '), 'provenance must be a nonempty'),
                         (dict(colour=1), "unknown keys ['colour']")):
            with self.assertRaises(ValueError) as ctx:
                bt.validate_calibration(dict(good, **bad), 1.5)
            self.assertIn(msg, str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            bt.validate_calibration(dict(good, kind='roll_surface_temperature_after_stop',
                                         values=[300.0] * 12), 1.5)
        self.assertIn('seconds_after_stop must be in [0, 3600]', str(ctx.exception))

    def test_cli_prints_and_writes_nothing(self):
        cal = self.twin('thermal_camber')
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'cal.json')
            with open(path, 'w') as fh:
                json.dump(cal, fh)
            before = sorted(os.listdir(tmp))
            out = subprocess.run([sys.executable, '-m', 'physicroll.band_cli', CASE_FILE,
                                  '--calibrate-spray', path], cwd=ROOT, capture_output=True,
                                 text=True, check=True)
            self.assertEqual(sorted(os.listdir(tmp)), before)
        res = json.loads(out.stdout)
        self.assertEqual(res['outcome'], 'FITTED')
        self.assertAlmostEqual(res['fitted_spray_mean_htc_w_m2k'] / TRUE_H, 1, delta=0.02)


if __name__ == '__main__':
    unittest.main()
