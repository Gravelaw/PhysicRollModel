"""SPEC19 package 11 in the engine: ironing roll and air in the coil (``width.coil_winding``)
and the coil temperature (``width.coil_temperature``), beside the present checks."""
import copy
import json
from pathlib import Path
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl
from physicroll import band_width as bw
from physicroll.band_report import render_band_report

ROOT = Path(__file__).resolve().parents[1]


def quick_battery():
    c = json.loads((ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json').read_text(
        encoding='utf-8'))
    for k in ('flatness_control', 'zone_step_test', 'friction_stripe_screen'):
        c['width_model'][k] = None
    c['model_options']['thermal_sensitivity'] = 'off'
    c['width_model']['numerics'] = {'axial_cell_m': 0.02, 'radial_cells': 6, 'time_step_s': 5.0}
    c['schedule'] = []
    return c


CW = {'radial_law': {'kind': 'ratio_of_hoop_modulus', 'ratio': 100}, 'provenance': 'unit test',
      'layers': 40, 'ironing_roll': {'load_per_width_n_m': 500.0, 'traction_coefficient': 0.1}}
CT = {'surface_htc_w_m2k': 8.0, 'ambient_temperature_k': 298.15,
      'strip_conductivity_w_mk': 200.0, 'gap_medium': 'air', 'provenance': 'unit test'}


def _strip(r):
    r = copy.deepcopy(r)
    w = r['width']
    w.pop('coil_temperature', None)
    w['coil_winding'] = {'not_supplied': True}
    r['thermal_check'].pop('coil_temperature_beside', None)
    r['flags'] = [f for f in r['flags'] if f not in bw.CW_TOP_FLAGS + bw.CT_TOP_FLAGS]
    for k in ('coil_winding', 'coil_thermal', 'deflector_roll_roughness_rq_m'):
        r['inputs']['width_model'].pop(k, None)
    return r


class Sections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = bd.diagnose(quick_battery())
        c = quick_battery()
        c['width_model']['coil_winding'] = copy.deepcopy(CW)
        c['width_model']['deflector_roll_roughness_rq_m'] = 0.2e-6
        c['width_model']['coil_thermal'] = copy.deepcopy(CT)
        cls.on = bd.diagnose(c)
        c2 = copy.deepcopy(c)
        c2['width_model']['local_coupling'] = None
        c2['width_model']['coil_thermal']['interlayer_gap_m'] = 0.5e-6
        c2['width_model']['coil_thermal']['gap_medium'] = 'oil'
        cls.no_local = bd.diagnose(c2)

    def test_nip_bounds_and_air(self):
        cw = self.on['width']['coil_winding']
        self.assertEqual(cw['air_mode'], 'none')
        self.assertIn('removes all the air', cw['air_cases']['none']['words'])
        self.assertIn('removes none of the air', cw['air_cases']['entrained_film']['words'])
        self.assertIn('coil diameter profile', cw['air_cases_note'])
        self.assertIn(bw.CW_FLAG_BRACKET, self.on['flags'])
        lo = max(p['max_pressure_pa'] for p in cw['air_cases']['none']['per_lane'])
        hi = max(p['max_pressure_pa'] for p in cw['air_cases']['entrained_film']['per_lane'])
        self.assertLess(hi, lo)                         # the entrained case is softer
        self.assertAlmostEqual(cw['nip']['wound_in_tension_pa'], 30e6 + 0.1 * 500.0 / 30e-6)
        ae = cw['air_entrainment']
        self.assertLess(abs(ae['film_at_core_m'] / 20.6e-6 - 1), 2e-3)
        self.assertIn('upper bound', ae['note'])
        self.assertEqual(cw['deflector_roll']['traction'], 'LIKELY_LOST')

    def test_coil_temperature_with_package_1(self):
        ct = self.on['width']['coil_temperature']
        self.assertEqual(ct['status'], bw.CT_STATUS)
        self.assertAlmostEqual(ct['winding_temperature_k'],
                               self.on['process']['heating']['operating']['exit_temperature_k'])
        self.assertIn('entrained-film bound', ct['conductivities']['gap_basis'])
        self.assertLess(ct['conductivities']['radial_w_mk'], ct['conductivities']['axial_w_mk'])
        self.assertTrue(ct['per_lane'])
        self.assertTrue(ct['lane_stress_on_cooling_pa'])
        rows = ct['limit_rows']
        self.assertEqual({r['limit'] for r in rows}, {'entering_final_pass', 'leaving_final_pass',
                                                      'elongation_decay_above'})
        for r in rows:
            self.assertTrue(r['source'])
        hot = [r['hottest_k'] for r in ct['cooling']]
        self.assertEqual(hot, sorted(hot, reverse=True))
        self.assertIn(bw.CT_FLAG_UPPER, self.on['flags'])
        beside = self.on['thermal_check']['coil_temperature_beside']
        self.assertIn('unchanged', beside['note'])

    def test_coil_temperature_without_package_1(self):
        ct = self.no_local['width']['coil_temperature']
        self.assertEqual(ct['status'], bw.CT_STATUS)
        self.assertIsNone(ct['per_lane'])
        self.assertAlmostEqual(ct['conductivities']['radial_w_mk'], 7.63, delta=0.01)

    def test_absent_keys_change_nothing_and_thermal_check_is_identical(self):
        a, b = _strip(self.on), _strip(self.base)
        self.assertEqual(json.dumps(a['thermal_check'], sort_keys=True),
                         json.dumps(b['thermal_check'], sort_keys=True))
        self.assertEqual([(h['id'], h['score']) for h in self.on['hypotheses']],
                         [(h['id'], h['score']) for h in self.base['hypotheses']])
        self.assertNotIn('coil_temperature', self.base['width'])
        self.assertNotIn('coil_temperature_beside', self.base['thermal_check'])

    def test_report_and_flags(self):
        html = render_band_report(self.on)
        self.assertIn('Coil temperature after winding', html)
        self.assertIn('Two bounds of the nip effect', html)
        for f in bw.CT_TOP_FLAGS + ('WOUND_IN_TENSION_CAPPED_AT_YIELD',
                                    'ENTRAINED_AIR_FILM_EXCEEDS_STRIP_THICKNESS',
                                    'AIR_CASES_BRACKET_THE_NIP_EFFECT'):
            self.assertIn(f, bpl.FLAGS)

    def test_validation(self):
        c = quick_battery()
        c['width_model']['coil_thermal'] = dict(CT)
        with self.assertRaises(ValueError) as cm:
            bd.validate_case(c)
        self.assertIn('interlayer_gap_m is required', str(cm.exception))
        c['width_model']['coil_thermal']['interlayer_gap_m'] = 1e-6
        c['width_model']['coil_thermal']['gap_medium'] = 'water'
        with self.assertRaises(ValueError):
            bd.validate_case(c)
        c = quick_battery()
        c['width_model']['coil_winding'] = dict(CW, air={'mode': 'entrained_film'},
                                                air_gap_m=1e-6)
        with self.assertRaises(ValueError) as cm:
            bd.validate_case(c)
        self.assertIn('not both', str(cm.exception))


if __name__ == '__main__':
    unittest.main()
