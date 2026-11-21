"""SPEC17 package 4: the shapemeter operator (``physicroll.band_sensors``).

Function-level checks of the zone geometry, the zone mean, the spreading and the dilution
formulas, the worked numbers on the committed battery-foil profile, the nozzle map against the
width section's geometry (``band_width.spray_layout``), the validation and one small diagnose
pair. The readings are zone means of a model profile, not a validation of a shapemeter.
"""
import copy
import json
import math
import unittest
from pathlib import Path

from physicroll import band_sensors as bs
from physicroll.band_diagnosis import diagnose, load_case, validate_case
from physicroll.band_report import render_band_report
from physicroll.band_width import spray_layout
from tests.test_band_robustness import v1case, v2case

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'band_diagnosis'
SM = {'zone_width_m': 0.052, 'zone_count': 24, 'edge_zone_width_m': None,
      'edge_zone_count_per_side': 0, 'centre_m': None, 'neighbour_spreading_fraction': 0.0,
      'resolution_i_units': None, 'provenance': 'unit test shapemeter'}


def _grid(n=1200, dz=0.001):
    return [(i + 0.5) * dz for i in range(n)]


class OperatorTests(unittest.TestCase):

    def test_zone_edges_and_coverage(self):
        e = bs.zone_edges(0.75, 0.052, 24)
        self.assertAlmostEqual(e[0], 0.126, places=12)
        self.assertAlmostEqual(e[-1], 1.374, places=12)
        e = bs.zone_edges(1.0, 0.052, 10, 0.026, 2)
        widths = [b - a for a, b in zip(e, e[1:])]
        self.assertEqual([round(w, 9) for w in widths[:3]], [0.026, 0.026, 0.052])
        self.assertEqual([round(w, 9) for w in widths[-2:]], [0.026, 0.026])
        self.assertAlmostEqual((e[0] + e[-1]) / 2, 1.0, places=12)
        # demo: the centre default is the width section's strip centre; edge zones half covered
        case = validate_case(load_case(ROOT / 'scenarios' / 'band_diagnosis_battery_foil.json'))
        r = json.loads((ART / 'battery-foil-demo.result.json').read_text())
        sm = bs.shapemeter_section(case, r)
        self.assertAlmostEqual(sm['zone_layout']['first_edge_m'], 0.126, places=9)
        self.assertAlmostEqual(sm['zones'][0]['coverage_fraction'], 0.5385, places=4)
        self.assertAlmostEqual(sm['zones'][23]['coverage_fraction'], 0.5385, places=4)
        self.assertTrue(all(z['coverage_fraction'] == 1.0 for z in sm['zones'][1:23]))
        self.assertEqual(sm['zone_layout']['uncovered_strip_width_m'], 0.0)

    def test_zone_mean_of_a_tophat_is_the_area_ratio(self):
        z = _grid()
        e = bs.zone_edges(0.6, 0.052, 23)          # zone 11 = [0.574, 0.626]
        v = [25.0 if abs(x - 0.6) < 0.010 else 0.0 for x in z]
        means = bs.zone_means(z, v, 0.0, 1.2, e)
        self.assertAlmostEqual(means[11][0], 25 * 0.020 / 0.052, places=4)     # 9.6154
        self.assertAlmostEqual(means[11][0], 9.6154, places=4)
        r, u, m_bar = bs.readings(means, e, 0.0)
        self.assertAlmostEqual(u[11], means[11][0] - m_bar, places=12)
        self.assertEqual(r, u)

    def test_narrow_band_reads_a_fraction_of_its_peak(self):
        """The risk-table case of SPEC17 section 4: a narrow source of 3.1 I-units reads about
        1.2 (a 20 mm top-hat centred in a 52 mm zone, 3.1*20/52)."""
        z = _grid()
        e = bs.zone_edges(0.6, 0.052, 23)          # zone 11 centred on 0.6
        v = [3.1 if abs(x - 0.6) < 0.010 else 0.0 for x in z]
        m = bs.zone_means(z, v, 0.0, 1.2, e)[11][0]
        self.assertAlmostEqual(m, 1.1923, places=4)
        self.assertAlmostEqual(m, 3.1 * bs.dilution(0.020, 0.052)['tophat_centred'], places=9)

    def test_uniform_profile_reads_zero(self):
        z = _grid()
        e = bs.zone_edges(0.6, 0.052, 20)
        r, u, m_bar = bs.readings(bs.zone_means(z, [4.0] * len(z), 0.0, 1.2, e), e, 0.1)
        self.assertAlmostEqual(m_bar, 4.0, places=12)
        self.assertTrue(all(abs(x) < 1e-12 for x in r))

    def test_mean_free_profile_keeps_roll_mean_zero_when_fully_covered(self):
        z = _grid(1040)                             # strip 0 .. 1.04 = 20 zones exactly
        e = bs.zone_edges(0.52, 0.052, 20)
        v = [math.sin(2 * math.pi * x / 0.26) for x in z]
        r, u, m_bar = bs.readings(bs.zone_means(z, v, 0.0, 1.04, e), e, 0.0)
        self.assertAlmostEqual(m_bar, 0.0, places=12)
        self.assertAlmostEqual(math.fsum(u), 0.0, places=12)

    def test_spreading_conserves_the_sum_and_s0_is_identity(self):
        e = bs.zone_edges(0.5, 0.1, 10)
        means = [(float(j * j % 7), 1.0) for j in range(10)]
        r0, u, _ = bs.readings(means, e, 0.0)
        self.assertEqual(r0, u)
        r, u2, _ = bs.readings(means, e, 0.125)
        self.assertAlmostEqual(math.fsum(r), math.fsum(u2), places=12)
        self.assertAlmostEqual(r[4], 0.75 * u[4] + 0.125 * (u[3] + u[5]), places=12)
        self.assertAlmostEqual(r[0], 0.875 * u[0] + 0.125 * u[1], places=12)   # edge: itself

    def test_dilution_table_closed_forms(self):
        d = {(w, b): bs.dilution(b, w) for w, b in ((0.052, 0.02), (0.052, 0.04),
                                                     (0.052, 0.08), (0.026, 0.02))}
        x = d[(0.052, 0.02)]
        self.assertAlmostEqual(x['tophat_centred'], 0.3846, delta=1e-4)
        self.assertAlmostEqual(x['tophat_on_boundary'], 0.1923, delta=1e-4)
        self.assertAlmostEqual(25 * x['tophat_on_boundary'], 4.8077, delta=1e-4)
        self.assertAlmostEqual(25 * x['tophat_centred'], 9.615, delta=1e-3)
        for key, want in (((0.052, 0.02), (0.4085, 0.2047)), ((0.052, 0.04), (0.7158, 0.4085)),
                          ((0.052, 0.08), (0.9104, 0.7158)), ((0.026, 0.02), (0.7158, 0.4085))):
            self.assertAlmostEqual(d[key]['gaussian_centred'], want[0], delta=1e-4)
            self.assertAlmostEqual(d[key]['gaussian_on_boundary'], want[1], delta=1e-4)
        # numeric zone mean of a sampled Gaussian (half-peak width 20 mm) against the closed form
        z = [(i + 0.5) * 1e-5 for i in range(120000)]
        g = [math.exp(-4 * math.log(2) * ((x - 0.6) / 0.02) ** 2) for x in z]
        e = bs.zone_edges(0.6, 0.052, 3)
        self.assertAlmostEqual(bs.zone_means(z, g, 0.0, 1.2, e)[1][0],
                               x['gaussian_centred'], delta=1e-3)
        t = bs.dilution_table(0.052)
        self.assertEqual([r['band_width_m'] for r in t['rows']], list(bs.DILUTION_BAND_WIDTHS_M))


class DemoProfileTests(unittest.TestCase):
    """Worked numbers of SPEC17 package 4 on the committed battery-foil profile."""

    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((ART / 'battery-foil-demo.result.json').read_text())
        cls.case = validate_case(load_case(ROOT / 'scenarios' /
                                           'band_diagnosis_battery_foil.json'))
        cls.lay = spray_layout(cls.case)
        cls.profiles = {p['name']: p for p in bs.shapemeter_profiles(cls.r['width'])}

    def _read(self, name, n=24, s=0.0):
        e = bs.zone_edges(self.lay['strip_centre_m'], 0.052, n)
        return bs.read_profile(self.profiles[name], e, self.lay['strip_start_m'],
                               self.lay['strip_end_m'], s)[0]

    def test_band_metrics_on_the_committed_demo_profile(self):
        self.assertEqual(list(self.profiles), ['steady', 'event_0_peak', 'nozzle_pattern_ripple',
                                               'steady_as_measured_hot',    # + package 6
                                               'local_mechanical_net',      # + SPEC19 p2
                                               'local_as_measured_hot'])
        p = self._read('steady')
        for got, want in zip(p['readings_i_units'][7:12],
                             (6.5973, 20.4506, 24.4912, 20.4517, 6.5979)):
            self.assertAlmostEqual(got, want, delta=1e-3)
        b = {round(x['peak_i_units'], 4): x for x in p['bands']}
        loose = b[25.0888]
        self.assertEqual(loose['zone_index'], 9)
        self.assertAlmostEqual(loose['zone_reading_i_units'], 24.4912, delta=1e-3)
        self.assertAlmostEqual(loose['reading_to_peak_ratio'], 0.9762, delta=1e-4)
        self.assertAlmostEqual(loose['half_peak_width_m'], 0.160, places=9)
        self.assertEqual(loose['shows'], 'would show')
        self.assertAlmostEqual(b[-5.1825]['zone_reading_i_units'], -5.1776, delta=1e-3)
        self.assertEqual(b[-5.1825]['zone_index'], 0)
        self.assertAlmostEqual(b[-5.2244]['zone_reading_i_units'], -5.2142, delta=1e-3)
        self.assertEqual(b[-5.2244]['zone_index'], 23)
        self.assertTrue(all(x['reads_above_threshold'] for x in p['bands']))
        sp = self._read('steady', s=0.125)
        self.assertAlmostEqual(sp['readings_i_units'][9], 23.4812, delta=1e-3)
        self.assertAlmostEqual(sp['bands'][1]['reading_to_peak_ratio'], 0.9359, delta=1e-4)
        ev = self._read('event_0_peak')
        peak = max(ev['bands'], key=lambda x: x['peak_i_units'])
        self.assertAlmostEqual(peak['peak_i_units'], 21.0067, delta=1e-3)
        self.assertEqual(peak['zone_index'], 16)
        self.assertAlmostEqual(peak['zone_reading_i_units'], 19.3326, delta=1e-3)
        rip = self._read('nozzle_pattern_ripple')
        self.assertAlmostEqual(rip['profile_max_abs_i_units'], 3.1433, delta=1e-4)
        self.assertAlmostEqual(rip['max_abs_reading_i_units'], 0.5296, delta=1e-4)
        # mirror zones 1 and 22 tie to about 1e-11 on this symmetric ripple: the lowest zone
        # index is reported whatever the platform's rounding (band_sensors.MAX_ZONE_TIE_REL_TOL)
        r = rip['readings_i_units']
        self.assertAlmostEqual(abs(r[1]), abs(r[22]), delta=1e-9)
        self.assertEqual(rip['max_abs_zone_index'], 1)
        p23 = self._read('steady', n=23)
        self.assertAlmostEqual(p23['readings_i_units'][9], 23.5348, delta=1e-3)
        self.assertAlmostEqual(p23['roll_mean_i_units'], 0.01739, delta=1e-5)

    def test_committed_measurement_section(self):
        sm = self.r['measurement']['shapemeter']
        self.assertEqual(sm['profiles'][0]['readings_i_units'],
                         self._read('steady')['readings_i_units'])
        self.assertIn(bs.FLAG_APPLIED, self.r['flags'])
        self.assertNotIn(bs.FLAG_SPREAD, self.r['flags'])
        self.assertNotIn(bs.FLAG_UNCOVERED, self.r['flags'])
        self.assertIn(bs.NO_CONTROLLER, sm['limitations'])
        self.assertIn('SS-S29 VP', sm['neighbour_spreading_basis'])
        self.assertEqual(sm['dilution_table']['zone_width_m'], 0.052)
        html = (ART / 'battery-foil-demo.report.html').read_text(encoding='utf-8')
        self.assertIn('What a shapemeter would show', html)
        self.assertIn('NO flatness controller', html)
        self.assertIn('would probably not show', html)
        other = (ART / 'lengthwise-bands-demo.report.html').read_text(encoding='utf-8')
        self.assertIn('No shapemeter was described', other)
        self.assertIn('reads 38 % of its peak', other)

    def test_nozzle_map_one_nozzle_per_zone(self):
        e = bs.zone_edges(self.lay['strip_centre_m'], 0.052, 24)
        nm, lay = bs.nozzle_map(self.case, e, 0.052)
        self.assertEqual(lay, self.lay)                  # the width section's geometry
        self.assertEqual((nm['nozzles_per_zone_min'], nm['nozzles_per_zone_max']), (1, 1))
        for z in nm['zones']:
            j = z['zone_index']
            self.assertEqual(z['nozzle_indices'], [j + 2])
            x = self.lay['nozzle_positions_m'][j + 2]
            self.assertAlmostEqual(x, (e[j] + e[j + 1]) / 2, places=9)   # at the zone centre
        self.assertEqual(nm['zones_without_nozzle'], [])
        self.assertIn('SS-S31 EX', nm['statement'])
        # boundary rule: e_j - 1e-9 <= x < e_{j+1} - 1e-9
        self.assertEqual(bs.zone_of(e, e[5]), 5)
        self.assertEqual(bs.zone_of(e, e[5] - 0.5e-9), 5)
        self.assertEqual(bs.zone_of(e, e[5] - 2e-9), 4)
        self.assertIsNone(bs.zone_of(e, e[-1]))
        self.assertIsNone(bs.zone_of(e, e[0] - 1e-6))


class ValidationAndDiagnoseTests(unittest.TestCase):

    def test_validation(self):
        bad = (('zone_width_m', 0.0, 'zone_width_m must be in (0, 0.5] m'),
               ('zone_width_m', 0.6, 'zone_width_m must be in (0, 0.5] m'),
               ('zone_count', 0, 'zone_count must be an int in [1, 400]'),
               ('zone_count', 2.0, 'zone_count must be an int in [1, 400]'),
               ('edge_zone_width_m', 0.06, 'edge_zone_width_m must be in (0, zone_width_m] or '
                                           'null'),
               ('edge_zone_count_per_side', 1, 'edge_zone_count_per_side'),
               ('centre_m', 11.0, 'centre_m must be in [0, 10] m or null'),
               ('neighbour_spreading_fraction', 0.3,
                'neighbour_spreading_fraction must be in [0, 0.25]'),
               ('resolution_i_units', 0.0, 'resolution_i_units must be in (0, 100] or null'),
               ('provenance', ' ', 'provenance must be a nonempty string'))
        for key, value, msg in bad:
            with self.assertRaises(ValueError) as cm:
                bs.validate_measurement({'shapemeter': dict(SM, **{key: value})})
            self.assertIn(msg, str(cm.exception), key)
        with self.assertRaisesRegex(ValueError, 'edge_zone_count_per_side'):
            bs.validate_measurement({'shapemeter': dict(SM, edge_zone_width_m=0.026,
                                                        edge_zone_count_per_side=0)})
        with self.assertRaisesRegex(ValueError, 'edge_zone_count_per_side'):
            bs.validate_measurement({'shapemeter': dict(SM, zone_count=3, edge_zone_width_m=0.02,
                                                        edge_zone_count_per_side=2)})
        ok = bs.validate_measurement({'shapemeter': dict(SM, edge_zone_width_m=0.026,
                                                         edge_zone_count_per_side=2)})
        self.assertEqual(ok['shapemeter']['edge_zone_count_per_side'], 2)
        with self.assertRaises(ValueError):
            bs.validate_measurement({'shapemeter': dict(SM, colour='red')})
        with self.assertRaises(ValueError):
            bs.validate_measurement({'shapemeter': SM, 'gauge': None})
        with self.assertRaisesRegex(ValueError, 'thickness_gauge'):     # validated (package 5)
            bs.validate_measurement({'shapemeter': None, 'thickness_gauge': {}})
        c = v1case()
        c['measurement'] = {'shapemeter': dict(SM)}
        with self.assertRaisesRegex(ValueError, 'measurement'):
            validate_case(c)

    def test_absent_measurement_changes_nothing_else(self):
        c = v2case(width=True)
        a = diagnose(copy.deepcopy(c))
        c['measurement'] = {'shapemeter': dict(SM, provenance='x <b>&"')}
        b = diagnose(c)
        self.assertTrue(a['measurement']['not_supplied'])
        self.assertEqual(b['measurement']['shapemeter']['status'], bs.STATUS)
        for k in set(a) | set(b):
            if k not in ('measurement', 'inputs', 'flags'):
                self.assertEqual(a.get(k), b.get(k), k)
        self.assertTrue(set(b['flags']) - set(a['flags']) <= set(bs.FLAGS))
        self.assertTrue(set(a['flags']) <= set(b['flags']))
        self.assertEqual(a['hypotheses'], b['hypotheses'])
        # report: escaped provenance, finite numbers
        html = render_band_report(b)
        self.assertIn('What a shapemeter would show', html)
        self.assertIn('x &lt;b&gt;&amp;', html)
        self.assertNotIn('x <b>', html)
        for word in ('nan', 'inf'):
            self.assertNotIn(f'>{word}<', html)
            self.assertNotIn(f' {word} ', html.lower().replace('information', ''))
        json.dumps(b['measurement'], allow_nan=False)

    def test_no_width_model_is_not_assessable(self):
        c = validate_case(dict(v2case(), measurement={'shapemeter': dict(SM)}))
        sm = bs.shapemeter_section(c, {'width': {'status': 'NOT_SUPPLIED'}})
        self.assertEqual(sm['status'], 'NOT_ASSESSABLE')
        self.assertIn('no width_model', sm['reason'])
        self.assertEqual(len(sm['dilution_table']['rows']), 5)
        self.assertTrue(sm['nozzle_map']['not_supplied'])
        self.assertEqual(sm['flags'], [])

    def test_v1_result_carries_not_supplied(self):
        r = json.loads((ART / 'bearing-order-demo.result.json').read_text())
        self.assertTrue(r['measurement']['not_supplied'])
        self.assertIsNone(r['inputs']['measurement'])


if __name__ == '__main__':
    unittest.main()
