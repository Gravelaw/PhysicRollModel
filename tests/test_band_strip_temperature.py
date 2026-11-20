"""SPEC17 package 6: strip temperature across the width as a flatness term (supplied scan).

``strip_shape.thermal_flatness_term`` and ``band_width.strip_temperature_section``: flatness as
measured hot (mechanical + thermal) against after cooling (= mechanical: the model has no
flatness controller) and the held-flat bounding case. The term is reported beside the width
section and never enters the evidence.
"""
import copy
import json
import math
import unittest
from pathlib import Path

from physicroll import band_sensors as bs
from physicroll import band_width as bw
from physicroll import strip_shape as ss
from physicroll.band_diagnosis import diagnose, load_case, validate_case
from physicroll.band_report import render_band_report
from tests.test_band_robustness import v2case

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'band_diagnosis'
SCEN = ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json'


def _case(scan=None):
    c = validate_case(load_case(SCEN))
    if scan is not None:
        c['width_model']['strip_temperature'] = scan
    return c


def _scan(pos, temps, alpha=None):
    return {'positions_m': pos, 'temperature_k': temps, 'expansion_coefficient_per_k': alpha,
            'provenance': 'unit test scan'}


class ThermalTermTests(unittest.TestCase):

    def test_one_kelvin_step_is_2_36_i_units(self):
        z = [0.005 * i for i in range(200)]
        t = [354.0 if x >= 0.5 else 353.0 for x in z]
        r = ss.thermal_flatness_term(z, t)
        self.assertAlmostEqual(max(r['i_units']) - min(r['i_units']), 2.36, delta=1e-9)
        self.assertAlmostEqual(r['i_units_per_kelvin'], 2.36, delta=1e-12)
        self.assertEqual(r['flags'], [ss.EXPANSION_FROM_MEMORY_FLAG])
        self.assertIn('[M', r['formula_basis'])
        r2 = ss.thermal_flatness_term(z, t, expansion_coefficient_per_k=2 * 23.0e-6)
        self.assertAlmostEqual(max(r2['i_units']) - min(r2['i_units']), 4.6, delta=1e-9)
        self.assertEqual(r2['flags'], [])

    def test_uniform_temperature_gives_zero_and_equal_profiles(self):
        r = json.loads((ART / 'battery-foil-demo.result.json').read_text())
        st = r['width']['shape']['steady']
        c = _case(_scan([0.15, 0.75, 1.35], [353.15] * 3))
        sec = bw.strip_temperature_section(c, c['width_model'], st, [], 0.15, 1.35)
        self.assertTrue(all(v == 0.0 for v in sec['thermal_i_units']))
        p = sec['profiles']
        self.assertEqual(p['as_measured_hot']['bands'], p['mechanical']['bands'])
        self.assertEqual(p['after_cooling']['bands'], p['mechanical']['bands'])
        self.assertEqual(p['after_cooling_if_hot_reading_held_flat']['bands'], [])
        self.assertFalse(any(x['state_differs'] for x in sec['state_changes']))


class DemoProfileTests(unittest.TestCase):
    """Worked numbers of SPEC17 package 6 on the committed steady profile and the demo scan."""

    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((ART / 'battery-foil-demo.result.json').read_text())
        cls.case = _case()
        cls.st = cls.r['width']['shape']['steady']
        ts = cls.r['width']['thermal_steady']
        cls.sec = bw.strip_temperature_section(cls.case, cls.case['width_model'], cls.st, [],
                                               ts['strip_start_m'], ts['strip_end_m'])

    @staticmethod
    def _bands(p):
        return [(round(b['start_m'], 3), round(b['end_m'], 3), round(b['peak_i_units'], 4),
                 round(b['peak_position_m'], 4), b['state'], b['state_after_tension_release'])
                for b in p['bands']]

    def test_profiles_on_the_committed_demo_profile(self):
        s = self.sec
        self.assertIn('synthetic', self.case['width_model']['strip_temperature']['provenance'])
        self.assertAlmostEqual(s['i_units_per_kelvin'], 2.36, delta=1e-12)
        self.assertAlmostEqual(s['mean_temperature_k'], 353.416125, delta=1e-6)
        self.assertAlmostEqual(s['max_temperature_deviation_k'], 2.332175, delta=1e-6)
        self.assertAlmostEqual(max(s['thermal_i_units']), 5.5039, delta=1e-3)
        self.assertAlmostEqual(min(s['thermal_i_units']), -0.6281, delta=1e-3)
        self.assertEqual(s['flags'], [bw.ST_FLAG_SUPPLIED, ss.EXPANSION_FROM_MEMORY_FLAG])
        self.assertIn('[M]', s['expansion_coefficient_basis'])
        self.assertEqual(s['scan_coverage']['extrapolated_width_m'], 0.0)
        p = s['profiles']
        # mechanical = the width section's steady profile, bands and states identical
        want = [(b['peak_i_units'], b['state'], b['state_after_tension_release'])
                for b in self.st['levels']['with_feedback']['bands']]
        self.assertEqual([(b['peak_i_units'], b['state'], b['state_after_tension_release'])
                          for b in p['mechanical']['bands']], want)
        self.assertEqual(p['after_cooling']['bands'], p['mechanical']['bands'])
        self.assertIn('no flatness controller', p['after_cooling']['meaning'])
        self.assertIn('BOUNDING CASE', p['after_cooling_if_hot_reading_held_flat']['meaning'])
        hot = self._bands(p['as_measured_hot'])
        self.assertEqual(hot[1][:2], (0.495, 0.745))
        self.assertAlmostEqual(hot[1][2], 30.4694, delta=1e-3)
        self.assertAlmostEqual(hot[1][3], 0.6175, places=4)
        self.assertEqual(hot[1][4:], ('LATENT_UNDER_TENSION', 'MANIFEST_AFTER_TENSION_RELEASE'))
        self.assertAlmostEqual(hot[0][2], -5.8106, delta=1e-3)
        self.assertAlmostEqual(hot[2][2], -5.8524, delta=1e-3)
        held = self._bands(p['after_cooling_if_hot_reading_held_flat'])
        self.assertEqual(len(held), 1)
        self.assertAlmostEqual(held[0][2], -5.5039, delta=1e-3)
        self.assertEqual(held[0][4:], ('LATENT_UNDER_TENSION', 'FLAT_AFTER_TENSION_RELEASE'))
        self.assertFalse(any(x['state_differs'] for x in s['state_changes']))
        # the thermal term alone: one loose band [0.560, 0.685], latent / manifest after release
        m = self.case['material']
        alone = ss.flatness_from_elongation(
            s['z_m'], [v * 1e-5 for v in s['thermal_i_units']],
            youngs_modulus_pa=m['youngs_modulus_pa'], poisson_ratio=bw.STRIP_POISSON_RATIO,
            thickness_m=self.case['pass']['exit_thickness_m'],
            mean_tension_pa=self.case['pass']['exit_tension_pa'],
            yield_stress_pa=m['yield_stress_pa'])
        self.assertEqual([(round(b['start_m'], 3), round(b['end_m'], 3)) for b in alone['bands']],
                         [(0.56, 0.685)])
        b = alone['bands'][0]
        self.assertAlmostEqual(b['peak_i_units'], 5.5039, delta=1e-3)
        self.assertAlmostEqual(b['peak_position_m'], 0.6025, places=4)
        self.assertEqual((b['state'], b['state_after_tension_release']),
                         ('LATENT_UNDER_TENSION', 'MANIFEST_AFTER_TENSION_RELEASE'))
        # shapemeter (package 4): hot profile zone 9 reads 29.8136 against 24.4912 mechanical
        width = dict(self.r['width'], strip_temperature=self.sec)
        prof = {x['name']: x for x in bs.shapemeter_profiles(width)}
        self.assertIn('what the shapemeter shows', prof['steady_as_measured_hot']['label'])
        lay = bw.spray_layout(self.case)
        e = bs.zone_edges(lay['strip_centre_m'], 0.052, 24)
        hot_r = bs.read_profile(prof['steady_as_measured_hot'], e, lay['strip_start_m'],
                                lay['strip_end_m'], 0.0)[0]
        mech_r = bs.read_profile(prof['steady'], e, lay['strip_start_m'],
                                 lay['strip_end_m'], 0.0)[0]
        self.assertAlmostEqual(hot_r['readings_i_units'][9], 29.8136, delta=1e-3)
        self.assertAlmostEqual(mech_r['readings_i_units'][9], 24.4912, delta=1e-3)
        comp = {x['name']: x for x in bs.shapemeter_profiles(width, True)}
        self.assertIn('compensation', comp['steady_as_measured_hot']['label'])

    def test_committed_artifact(self):
        st = self.r['width']['strip_temperature']
        self.assertEqual(json.loads(json.dumps(self.sec)), st)
        self.assertIn(bw.ST_FLAG_SUPPLIED, self.r['flags'])
        self.assertIn(ss.EXPANSION_FROM_MEMORY_FLAG, self.r['flags'])
        names = [x['name'] for x in self.r['measurement']['shapemeter']['profiles']]
        self.assertIn('steady_as_measured_hot', names)
        html = (ART / 'battery-foil-demo.report.html').read_text(encoding='utf-8')
        self.assertIn('Strip temperature and flatness', html)
        self.assertIn('The temperature profile was supplied, not computed.', html)
        self.assertIn('BOUNDING CASE', html)
        other = (ART / 'lengthwise-bands-demo.report.html').read_text(encoding='utf-8')
        self.assertIn('No strip temperature scan: a 1 K hotter fibre reads about 2.4', other)
        self.assertTrue(self.r['inputs']['width_model']['strip_temperature'] is not None)


class EdgeCaseTests(unittest.TestCase):

    def test_hot_stripe_on_a_flat_strip(self):
        c = _case()
        z = [0.15 + 0.005 * (i + 0.5) for i in range(240)]
        sec = bw.strip_temperature_section(c, c['width_model'], {'status': 'NOT_ASSESSABLE'},
                                           z, 0.15, 1.35)
        self.assertIn(bw.ST_FLAG_NO_MECH, sec['flags'])
        self.assertFalse(sec['profiles']['mechanical']['available'])
        for got, want in zip(sec['profiles']['as_measured_hot']['i_units'],
                             sec['thermal_i_units']):
            self.assertAlmostEqual(got, want, places=9)
        self.assertEqual(sec['profiles']['mechanical']['bands'], [])

    def test_state_change_is_reported(self):
        c = _case(_scan([0.15, 0.6, 0.65, 0.7, 1.35], [353.15, 353.15, 354.15, 353.15, 353.15],
                        2.36e-5))
        z = [0.15 + 0.005 * (i + 0.5) for i in range(240)]
        mech = [1.5 * math.exp(-4 * math.log(2) * ((x - 0.65) / 0.05) ** 2) for x in z]
        mean = math.fsum(mech) / len(mech)
        mech = [v - mean for v in mech]
        st = {'z_m': z, 'i_units_with_feedback': mech}
        sec = bw.strip_temperature_section(c, c['width_model'], st, z, 0.15, 1.35)
        self.assertEqual(sec['profiles']['mechanical']['bands'], [])        # below 2 I-units
        self.assertTrue(sec['profiles']['as_measured_hot']['bands'])
        self.assertIn(bw.ST_FLAG_STATE, sec['flags'])
        ch = [x for x in sec['state_changes'] if x['profile'] == 'as_measured_hot']
        self.assertTrue(ch and ch[0]['state_differs'] and ch[0]['other_state'] is None)

    def test_scan_not_covering_the_strip(self):
        c = _case(_scan([0.3, 0.6, 0.9], [354.0, 353.0, 355.0]))
        z = [0.15 + 0.005 * (i + 0.5) for i in range(240)]
        sec = bw.strip_temperature_section(c, c['width_model'], None, z, 0.15, 1.35)
        self.assertAlmostEqual(sec['scan_coverage']['extrapolated_width_m'], 0.6, places=9)
        self.assertIn(bw.ST_FLAG_COVER, sec['flags'])
        self.assertEqual(sec['temperature_k'][0], 354.0)
        self.assertEqual(sec['temperature_k'][-1], 355.0)

    def test_validation(self):
        raw = json.loads(SCEN.read_text())
        base = raw['width_model']['strip_temperature']
        cases = (
            (dict(base, positions_m=[0.2, 0.1, 0.3]), 'positions_m must be >= 3 strictly'),
            (dict(base, positions_m=[0.1, 0.2]), 'positions_m must be >= 3 strictly'),
            (dict(base, positions_m=[0.1, 0.2, 1.6] + base['positions_m'][3:]),
             'positions_m must be >= 3 strictly'),
            (dict(base, temperature_k=base['temperature_k'][:-1]),
             'temperature_k needs one value in [250, 700] K per position'),
            (dict(base, temperature_k=[800.0] + base['temperature_k'][1:]),
             'temperature_k needs one value in [250, 700] K per position'),
            (dict(base, expansion_coefficient_per_k=1e-3),
             'expansion_coefficient_per_k must be in (1e-6, 1e-4) or null'),
            (dict(base, provenance=' '), 'provenance must be a nonempty string'))
        for value, msg in cases:
            c = copy.deepcopy(raw)
            c['width_model']['strip_temperature'] = value
            with self.assertRaises(ValueError) as cm:
                validate_case(c)
            self.assertIn('width_model.strip_temperature.' + msg, str(cm.exception))
        c = copy.deepcopy(raw)
        c['width_model']['strip_temperature'] = dict(base, colour='red')
        with self.assertRaises(ValueError):
            validate_case(c)
        c = copy.deepcopy(raw)
        c['measurement']['shapemeter']['temperature_compensated'] = 'yes'
        with self.assertRaisesRegex(ValueError, 'temperature_compensated'):
            validate_case(c)

    def test_absent_scan_changes_nothing(self):
        c = v2case(width=True)
        a = diagnose(copy.deepcopy(c))
        c['width_model']['strip_temperature'] = _scan([0.2, 0.7, 1.2], [353.0, 356.0, 353.0])
        b = diagnose(c)
        self.assertTrue(a['width']['strip_temperature']['not_supplied'])
        self.assertFalse(b['width']['strip_temperature']['not_supplied'])
        for k in set(a) | set(b):
            if k in ('measurement', 'inputs', 'flags'):
                continue
            if k == 'width':
                wa = {x: v for x, v in a['width'].items() if x != 'strip_temperature'}
                wb = {x: v for x, v in b['width'].items() if x != 'strip_temperature'}
                self.assertEqual(wa, wb)
                continue
            self.assertEqual(a.get(k), b.get(k), k)
        self.assertEqual(a['hypotheses'], b['hypotheses'])
        self.assertTrue(set(a['flags']) <= set(b['flags']))
        html = render_band_report(b)
        self.assertIn('Strip temperature and flatness', html)
        self.assertNotIn('>nan<', html)
        self.assertNotIn('NaN', html)


if __name__ == '__main__':
    unittest.main()
