"""SPEC22: spray header options (footprint profile, supplied width, flow exponent), the
realistic-header demo and the defaults that must reproduce the earlier numbers bit for bit."""
import copy
import json
import math
from pathlib import Path
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl
from physicroll import band_signatures as bsig
from physicroll import band_width as bw
from physicroll import roll_thermal as rt
from tests.json_close import first_difference

ROOT = Path(__file__).resolve().parents[1]
SCEN = ROOT / 'scenarios'
ART = ROOT / 'artifacts' / 'band_diagnosis'


def _old_weight_profile(header, z_cells, levels):
    """The weight profile as it was before SPEC22 (kept here as the reference)."""
    z = list(z_cells)
    edges = [z[0] - (z[1] - z[0]) / 2]
    edges += [(a + b) / 2 for a, b in zip(z, z[1:])]
    edges.append(z[-1] + (z[-1] - z[-2]) / 2)
    positions = header.nozzle_positions(edges[-1])
    lv = [1.0] * len(positions) if levels is None else list(levels)
    w_eff = (2 * header.standoff_m * math.tan(header.spray_angle_rad / 2)
             * math.cos(header.offset_angle_rad))
    height = header.nozzle_pitch_m / w_eff
    out = []
    for a, b in zip(edges, edges[1:]):
        acc = 0.0
        for x, s in zip(positions, lv):
            if s > 0:
                acc += s * max(0.0, min(b, x + w_eff / 2) - max(a, x - w_eff / 2))
        out.append(height * acc / (b - a))
    return out


def _scenario(name):
    return json.loads((SCEN / f'band_diagnosis_{name}.json').read_text(encoding='utf-8'))


def _header(**kw):
    base = dict(nozzle_pitch_m=0.052, standoff_m=0.2, spray_angle_rad=0.8,
                offset_angle_rad=0.17, spray_mean_htc_w_m2k=3400.0)
    base.update(kw)
    return rt.SprayHeader(**base)


def _cells(length, dz):
    n = int(round(length / dz))
    return [(i + 0.5) * length / n for i in range(n)]


class Defaults(unittest.TestCase):
    def test_weight_profile_equals_the_old_formula_for_both_v2_demos(self):
        for name in ('battery_foil', 'lengthwise_bands'):
            w = bw.validate_width_model(_scenario(name)['width_model'],
                                        _scenario(name)['pass'])
            header = bw._header(w)
            length = w['roll']['barrel_length_m']
            n = len(header.nozzle_positions(length))
            levels = w['nozzle_levels'] or [1.0] * n
            for dz in (0.005, 0.02):
                z = _cells(length, dz)
                self.assertEqual(header.weight_profile(z, levels),
                                 _old_weight_profile(header, z, levels), name)
                self.assertEqual(header.weight_profile(z, None),
                                 _old_weight_profile(header, z, None), name)
            self.assertEqual(header.footprint_width_source, 'geometric')
            self.assertEqual(header.effective_footprint_width_m,
                             2 * header.standoff_m * math.tan(header.spray_angle_rad / 2)
                             * math.cos(header.offset_angle_rad))

    def test_validated_case_keeps_no_new_key_when_none_is_given(self):
        w = bw.validate_width_model(_scenario('battery_foil')['width_model'],
                                    _scenario('battery_foil')['pass'])
        self.assertEqual(set(w['spray_header']), set(bw.HEADER_KEYS))


class SelfChecks(unittest.TestCase):
    def test_parabola_integrates_to_the_top_hat_total(self):
        for wd in (0.03, 0.0743, 0.17):
            self.assertAlmostEqual(rt._parabola_integral(-1.0, 1.0, 0.0, wd), wd, places=14)
            parts = sum(rt._parabola_integral(-wd / 2 + i * wd / 7, -wd / 2 + (i + 1) * wd / 7,
                                              0.0, wd) for i in range(7))
            self.assertAlmostEqual(parts, wd, places=14)

    def test_healthy_parabolic_header_averages_to_one_away_from_the_ends(self):
        h = _header(footprint_profile='parabolic', footprint_width_m=1.43 * 0.052)
        z = _cells(1.5, 0.0005)
        wt = h.weight_profile(z, None)
        a0, a1 = 0.75 - 5 * 0.052, 0.75 + 5 * 0.052     # an integer number of pitches
        inner = [v for x, v in zip(z, wt) if a0 <= x < a1]
        self.assertAlmostEqual(sum(inner) / len(inner), 1.0, places=6)
        self.assertLess(min(inner), 0.95)                 # it ripples (-12 % / +7 %)

    def _deficit(self, profile, ratio):
        p = 0.052
        h = _header(footprint_profile=profile, footprint_width_m=ratio * p)
        z = _cells(1.5, 0.0005)
        n = len(h.nozzle_positions(1.5))
        k = n // 2
        lv = [1.0] * n
        lv[k] = 0.0
        d = [a - b for a, b in zip(h.weight_profile(z, None), h.weight_profile(z, lv))]
        pk = max(d)
        half = [x for x, v in zip(z, d) if v >= pk / 2]
        return pk, (half[-1] - half[0]) / p

    def test_blocked_nozzle_deficit_against_the_research_values(self):
        pk, hw = self._deficit('parabolic', 1.43)
        self.assertAlmostEqual(pk, 1.05, delta=0.02 * 1.05)
        self.assertAlmostEqual(hw, 1.0, delta=0.02)
        pk, hw = self._deficit('tophat', 1.43)
        self.assertAlmostEqual(pk, 0.70, delta=0.02 * 0.70)
        self.assertAlmostEqual(hw, 1.43, delta=0.02 * 1.43)
        self.assertAlmostEqual(self._deficit('parabolic', 3.21)[0], 0.47, delta=0.02 * 0.47)
        self.assertAlmostEqual(self._deficit('tophat', 3.21)[0], 0.31, delta=0.02 * 0.31)

    def test_flow_exponent(self):
        for n, expected in ((0.9, 0.49), (0.6, 0.62)):
            h = _header(htc_flow_exponent=n)
            self.assertAlmostEqual(h.nozzle_weight(0.45), expected, delta=0.005)
        self.assertEqual(_header().nozzle_weight(0.45), 0.45)

    def test_validation(self):
        _header(offset_angle_rad=math.radians(70)).validate()
        with self.assertRaises(ValueError):
            _header(offset_angle_rad=math.radians(71)).validate()
        with self.assertRaises(ValueError) as cm:
            _header(footprint_profile='gaussian').validate()
        self.assertIn('"tophat" or "parabolic"', str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            _header(footprint_width_m=6.0).validate()
        self.assertIn('the pattern width along the barrel', str(cm.exception))
        for n in (0.4, 1.1):
            with self.assertRaises(ValueError):
                _header(htc_flow_exponent=n).validate()
        raw = _scenario('battery_foil')
        raw['width_model']['spray_header']['footprint_profile'] = 'gaussian'
        with self.assertRaises(ValueError) as cm:
            bd.validate_case(raw)
        self.assertIn('"tophat" or "parabolic"', str(cm.exception))

    def test_one_width_property_everywhere(self):
        raw = _scenario('battery_foil')
        raw['width_model']['spray_header']['footprint_width_m'] = 0.07
        case = bd.validate_case(raw)
        lay = bw.spray_layout(case)
        self.assertEqual(lay['effective_footprint_width_m'], 0.07)
        self.assertEqual(lay['footprint_width_source'], 'supplied')
        self.assertAlmostEqual(lay['footprint_width_over_pitch'], 0.07 / 0.052)
        self.assertEqual(bw._header(case['width_model']).effective_footprint_width_m, 0.07)
        self.assertEqual(bd._coverage_width(case), 0.07)
        c = case['coolant']
        cov = bsig.spray_coverage(c['barrel_length_m'], c['nozzle_pitch_m'], c['standoff_m'],
                                  c['spray_angle_rad'], c['offset_angle_rad'],
                                  footprint_width_m=bd._coverage_width(case))
        self.assertEqual(cov['effective_footprint_width_m'], 0.07)
        self.assertEqual(bw.header_flags(bw._header(case['width_model'])), [])
        self.assertEqual(bw.header_flags(bw._header(bd.validate_case(
            _scenario('battery_foil'))['width_model'])), [bw.FP_FLAG_WIDE])

    def test_flags_have_plain_sentences(self):
        for f in bw.FP_TOP_FLAGS + ('SPRAY_COEFFICIENT_BASIS_NOT_COMPARABLE',):
            self.assertIn(f, bpl.FLAGS)
        self.assertNotIn('SPRAY_COEFFICIENT_BASIS_NOT_ESTABLISHED', bpl.FLAGS)


class RealisticHeaderDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.art = json.loads((ART / 'realistic-header-demo.result.json').read_text(
            encoding='utf-8'))
        cls.old = json.loads((ART / 'battery-foil-demo.result.json').read_text(
            encoding='utf-8'))

    def test_artifact_equals_a_regeneration(self):
        new = bd.diagnose(bd.load_case(SCEN / 'band_diagnosis_realistic_header.json'))
        new = json.loads(json.dumps(new, allow_nan=False))
        self.assertIsNone(first_difference(self.art, new))

    def test_header_is_inside_vendor_practice(self):
        ts = self.art['width']['thermal_steady']
        self.assertAlmostEqual(ts['footprint_width_over_pitch'], 1.3, delta=1e-3)
        self.assertEqual(ts['footprint_profile'], 'parabolic')
        self.assertIn(bw.FP_FLAG_STAND_IN, self.art['flags'])
        self.assertNotIn(bw.FP_FLAG_WIDE, self.art['flags'])
        self.assertIn(bw.FP_FLAG_WIDE, self.old['flags'])
        self.assertTrue(any('stand-in' in n for n in ts['footprint_notes']))
        self.assertTrue(any('7 to 45 % smaller' in n for n in ts['footprint_notes']))

    def test_blocked_nozzle_is_deeper_and_narrower(self):
        a = self.old['width']['thermal_steady']['stripes'][0]
        b = self.art['width']['thermal_steady']['stripes'][0]
        self.assertEqual(a['nearest_nozzle_index'], b['nearest_nozzle_index'])
        self.assertGreater(b['peak_deviation_m'], a['peak_deviation_m'])
        self.assertLess(b['width_at_half_peak_m'], a['width_at_half_peak_m'])


if __name__ == '__main__':
    unittest.main()
