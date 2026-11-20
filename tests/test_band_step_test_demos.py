"""SPEC19 package 5: the zone step test emulation on the demos (full numerics, the committed
artifacts' shape inputs and bite rows), against the planner's table (s25/steptest.py):
roll growth alone and roll growth plus the strip temperature term at couplings 1.0 and 0.5,
nozzles 18-19 (battery-foil) and 20-21 (lengthwise), no transport delay, 1 s display filter.
The fitted constants sit on a grid of ratio 1.08: checked within 10 % and pinned. A match with
the published 20 s is not evidence of what the plant measured.
"""
import json
import types
import unittest
from pathlib import Path

from physicroll import band_diagnosis as bd
from physicroll import band_local as bl
from physicroll import band_process as bp
from physicroll import band_width as bw

ROOT = Path(__file__).resolve().parents[1]
SM29 = {'zone_width_m': 0.052, 'zone_count': 29, 'provenance': 'planner assumption'}


def step_test(name, nozzles, coupling, hold):
    art = json.loads((ROOT / 'artifacts' / 'band_diagnosis' /
                      f'{name.replace("_", "-")}-demo.result.json').read_text(encoding='utf-8'))
    raw = json.loads((ROOT / 'scenarios' / f'band_diagnosis_{name}.json').read_text(
        encoding='utf-8'))
    if (raw.get('measurement') or {}).get('shapemeter') is None:
        raw['measurement'] = {'shapemeter': dict(SM29), 'thickness_gauge': None}
    w0 = raw['width_model']
    w0['flatness_control'] = None
    w0['local_coupling'] = dict(w0.get('local_coupling') or {'provenance': 'unit test'},
                                strip_roll_temperature_coupling=coupling,
                                flow_stress_temperature_coefficient_per_k=0.0015,
                                oil_flow_per_nozzle_m3_s=None)
    w0['zone_step_test'] = {'nozzle_indices': nozzles, 'hold_s': hold,
                            'fit_windows_s': [x for x in (20, 40, 60, 120, 600) if x <= hold],
                            'provenance': 'unit test'}
    case = bd.validate_case(raw)
    w = case['width_model']
    iu = art['width']['inputs_used']
    sup = {k: iu[k] for k in ('strip_stiffness_per_width_pa', 'bite_half_length_m',
                              'exit_tension_force_sensitivity_per_width_m')}
    sp = bw.shape_params(case, None, w, None, supplied=sup)
    th = bw._Thermal(case, w, iu['bite_heat_per_width_w_m'], iu['roll_heat_fraction_per_roll'])
    actual = th.steady(th.levels)
    fr = art['process']['friction']['operating']
    bite = types.SimpleNamespace(forward_slip_fraction=fr['forward_slip_fraction'],
                                 contact_length_m=art['bite']['contact_length_m'],
                                 separating_force_n=art['bite']['separating_force_n'])
    lub, fin, clo = bp.tribology_objects(case['tribology'])
    params = bl.local_params(case, w, case['tribology'], lub, clo, fin, bite,
                             art['process']['heating']['operating'], fr, None)
    sens = {'dforce_per_width_dfriction_n_m': 5.14e7, 'dforce_per_width_dflow_stress_m': 0.0112,
            'flow_stress_pa': case['pass']['mean_flow_stress_pa']}
    return bw.zone_step_test_section(case, w, th, sp, actual, {'params': params, 'sens': sens},
                                     bite)


def taus(r, name):
    return [f['time_constant_s'] for f in r['series'][name]['fits']]


class BatteryFoilStepTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c10 = step_test('battery_foil', [18, 19], 1.0, 600.0)
        cls.c05 = step_test('battery_foil', [18, 19], 0.5, 120.0)

    def _check(self, got, planner):
        for g, p in zip(got, planner):
            self.assertLess(abs(g / p - 1), 0.10, (got, planner))
            self.assertLess(abs(g / p - 1), 4e-3, (got, planner))     # same grid point

    def test_roll_growth_only(self):
        self.assertEqual(self.c10['shapemeter_zone_index'], 17)
        self._check(taus(self.c10, 'roll_growth_only'), (63.8, 63.8, 74.4, 101.3, 173.5))

    def test_with_the_strip_temperature_term(self):
        self._check(taus(self.c10, 'roll_growth_plus_strip_temperature'),
                    (16.0, 25.3, 34.5, 59.1, 137.8))
        self._check(taus(self.c05, 'roll_growth_plus_strip_temperature'),
                    (23.5, 34.5, 46.9, 68.9))

    def test_surface_and_reading(self):
        h = self.c10['surface_temperature_change_k']
        at = dict(zip(h['time_s'], h['zone_mean_minus_roll_mean_k']))   # as the planner
        for t, want in ((10.0, 4.92), (20.0, 6.30), (60.0, 8.70), (300.0, 11.54)):
            self.assertAlmostEqual(at[t], want, delta=0.06)
        r = self.c10['series']['roll_growth_only']
        at = dict(zip(r['time_s'], r['reading_i_units']))
        self.assertAlmostEqual(at[60.0], 44.33, delta=1.0)        # 1 s filter applied here
        self.assertIn('depends on the test length', self.c10['finding'])
        self.assertIn('not evidence', self.c10['finding'])


class LengthwiseStepTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r = step_test('lengthwise_bands', [20, 21], 1.0, 120.0)

    def test_planner_table(self):
        self.assertEqual(self.r['shapemeter_zone_index'], 19)
        for name, planner in (('roll_growth_only', (109.4, 93.8, 93.8, 118.1)),
                              ('roll_growth_plus_strip_temperature', (29.6, 43.4, 59.1, 86.8))):
            for g, p in zip(taus(self.r, name), planner):
                self.assertLess(abs(g / p - 1), 4e-3, (name, g, p))


if __name__ == '__main__':
    unittest.main()
