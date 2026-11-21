"""SPEC19 package 10: winding by lanes (``wound_roll.allocate_tension``, ``wind_lanes``,
``band_width.coil_winding_section``), beside the present linear coil criterion."""
import copy
import json
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl
from physicroll import band_width as bw
from physicroll import wound_roll as wr
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import LONG, NOZZLES, v2, width_model

E, H, SY = 70e9, 30e-6, 165e6
LAWS = {'isotropic': {'kind': 'constant', 'radial_modulus_pa': E},
        'e_over_100': {'kind': 'ratio_of_hoop_modulus', 'ratio': 100},
        'pfeiffer_100': {'kind': 'pfeiffer', 'k1_pa': 1e4, 'k2': 100.0},
        'pfeiffer_30': {'kind': 'pfeiffer', 'k1_pa': 1e4, 'k2': 30.0}}


def _lanes(dh, law, alloc='mid_layer'):
    hs = [H] * 24
    hs[12] = H + dh
    r = wr.wind_lanes(core_radius_m=0.15, outer_radius_m=0.6, thicknesses_m=hs,
                      widths_m=[0.05] * 24, winding_tension_pa=30e6, hoop_modulus_pa=E,
                      poisson_ratio=0.33, yield_stress_pa=SY, radial_law=LAWS[law], layers=150,
                      allocation_radius=alloc)
    lanes, nl = r['lanes'], r['laps_per_layer']
    hd, nb = lanes[12], lanes[0]

    def at(laps):
        return hd.wound_on[int(round(laps / nl)) - 1] / 1e6
    ep = hd.plastic_strain
    first = next((i for i, v in enumerate(ep) if v > 0), None)
    return {'t': (at(1000), at(5000), at(15000)), 'nb_end': nb.wound_on[-1] / 1e6,
            'ceff': ((hd.outer_radius_m - nb.outer_radius_m) / ((0.45 / H) * dh) if dh
                     else None),
            'yield_frac': sum(1 for v in ep if v > 0) / len(ep),
            'first_yield_laps': None if first is None else (first + 1) * nl,
            'max_plastic_i': max(ep) * 1e5, 'max_t': max(hd.wound_on) / 1e6}


class Allocation(unittest.TestCase):
    def test_uniform_lanes_get_the_mean_and_the_force_balance_holds(self):
        s0, al = wr.allocate_tension([0.3] * 5, [H] * 5, [0.05] * 5, [0.0] * 5, 30e6,
                                     youngs_modulus_pa=E, yield_stress_pa=SY)
        for sig, ep in al:
            self.assertLess(abs(sig / 30e6 - 1), 1e-9)
            self.assertEqual(ep, 0.0)
        hs = [H, H + 1e-7, H - 5e-8, H]
        s = [0.3 + 1e-6, 0.3 + 3e-6, 0.3, 0.3 + 1e-6]
        _, al = wr.allocate_tension(s, hs, [0.05, 0.05, 0.04, 0.05], [0.0] * 4, 30e6,
                                    youngs_modulus_pa=E, yield_stress_pa=SY)
        force = sum(w * h * a[0] for w, h, a in zip([0.05, 0.05, 0.04, 0.05], hs, al))
        self.assertLess(abs(force / (30e6 * sum(w * h for w, h in zip(
            [0.05, 0.05, 0.04, 0.05], hs))) - 1), 1e-9)

    def test_longer_lane_gets_less_and_slack_and_yield(self):
        _, al = wr.allocate_tension([0.3] * 3, [H] * 3, [0.05] * 3, [0.0, 2e-4, 0.0], 30e6,
                                    youngs_modulus_pa=E, yield_stress_pa=SY)
        self.assertLess(al[1][0], al[0][0])
        _, al = wr.allocate_tension([0.3] * 3, [H] * 3, [0.05] * 3, [0.0, 2e-3, 0.0], 30e6,
                                    youngs_modulus_pa=E, yield_stress_pa=SY)
        self.assertEqual(al[1][0], 0.0)                         # slack: no compression
        e = [0.0] * 10
        e[1] = -3e-3
        _, al = wr.allocate_tension([0.3] * 10, [H] * 10, [0.05] * 10, e, 30e6,
                                    youngs_modulus_pa=E, yield_stress_pa=SY)
        self.assertEqual(al[1][0], SY)                          # short lane at yield
        self.assertGreater(al[1][1], 0.0)
        self.assertAlmostEqual(al[1][1], (al[0][0] / E + 3e-3) - SY / E, delta=1e-9)
        with self.assertRaises(ValueError):
            wr.allocate_tension([0.3] * 3, [H] * 3, [0.05] * 3, [0.0] * 3, 170e6,
                                youngs_modulus_pa=E, yield_stress_pa=SY)

    def test_uniform_profile_reproduces_the_single_lane_model(self):
        lanes = wr.wind_lanes(core_radius_m=0.15, outer_radius_m=0.6, thicknesses_m=[H] * 4,
                              widths_m=[0.05] * 4, winding_tension_pa=30e6, hoop_modulus_pa=E,
                              poisson_ratio=0.33, yield_stress_pa=SY,
                              radial_law=LAWS['e_over_100'], layers=60)['lanes']
        one = wr.wind_uniform(core_radius_m=0.15, outer_radius_m=0.6, thickness_m=H,
                              winding_tension_pa=30e6, hoop_modulus_pa=E, poisson_ratio=0.33,
                              radial_law=LAWS['e_over_100'], layers=60)
        for ln in lanes:
            for a, b in zip(ln.radial_stress, one['radial_stress_pa']):
                self.assertLessEqual(abs(a - b), 1e-6 * max(1.0, abs(b)))
            for a in ln.wound_on:
                self.assertLess(abs(a / 30e6 - 1), 1e-9)


class PlannerTable(unittest.TestCase):
    """The planner's table (prototype: allocation at the layer top) reproduced with
    allocation_radius='layer_top'; the specification's mid-layer allocation pinned to its own
    values (they differ by up to 17 % for the softest stack, and there a 1 um lane no longer
    reaches yield)."""

    @classmethod
    def setUpClass(cls):
        cls.top = {(dh, k): _lanes(dh, k, 'layer_top') for dh in (0.1e-6, 1e-6)
                   for k in LAWS}
        cls.mid = {(dh, k): _lanes(dh, k) for dh in (0.1e-6, 1e-6) for k in LAWS}

    def test_uniform_strip(self):
        r = _lanes(0.0, 'e_over_100')
        for v in r['t']:
            self.assertAlmostEqual(v, 30.0, places=6)

    def test_prototype_rows(self):
        rows = {('isotropic', 0.1e-6): ((67.1, 132.1, 159.9), 0.772),
                ('e_over_100', 0.1e-6): ((53.8, 51.9, 51.3), 0.121),
                ('pfeiffer_100', 0.1e-6): ((47.2, 44.1, 41.7), 0.0625),
                ('pfeiffer_30', 0.1e-6): ((38.5, 36.1, 34.5), 0.0194),
                ('isotropic', 1e-6): ((165.0, 165.0, 165.0), 0.972),
                ('e_over_100', 1e-6): ((165.0, 165.0, 165.0), 0.437),
                ('pfeiffer_30', 1e-6): ((165.0, 120.6, 93.4), 0.031)}
        for (law, dh), (t, ceff) in rows.items():
            r = self.top[(dh, law)]
            for a, b in zip(r['t'], t):
                self.assertAlmostEqual(a, b, delta=0.06, msg=(law, dh))
            self.assertAlmostEqual(r['ceff'], ceff, delta=0.02 * ceff + 2e-3, msg=(law, dh))
        self.assertAlmostEqual(self.top[(1e-6, 'pfeiffer_30')]['yield_frac'], 0.053, delta=0.01)
        self.assertAlmostEqual(self.top[(1e-6, 'pfeiffer_30')]['max_plastic_i'], 17, delta=1)
        self.assertAlmostEqual(self.top[(1e-6, 'isotropic')]['max_plastic_i'], 2230, delta=10)

    def test_specification_rows_pinned(self):
        pins = {('isotropic', 0.1e-6): 0.77248, ('e_over_100', 0.1e-6): 0.123692,
                ('pfeiffer_100', 0.1e-6): 0.065601, ('pfeiffer_30', 0.1e-6): 0.022688,
                ('isotropic', 1e-6): 0.970453, ('e_over_100', 1e-6): 0.436869,
                ('pfeiffer_100', 1e-6): 0.49334, ('pfeiffer_30', 1e-6): 0.033796}
        for (law, dh), ceff in pins.items():
            self.assertLess(abs(self.mid[(dh, law)]['ceff'] / ceff - 1), 1e-4, (law, dh))
        self.assertEqual(self.mid[(1e-6, 'pfeiffer_30')]['yield_frac'], 0.0)
        self.assertAlmostEqual(self.mid[(1e-6, 'pfeiffer_30')]['max_t'], 158.37, delta=0.05)
        for law in ('isotropic', 'e_over_100', 'pfeiffer_100'):
            self.assertAlmostEqual(self.mid[(1e-6, law)]['first_yield_laps'], 399.4, delta=0.5)

    def test_orderings(self):
        for d in (self.mid, self.top):
            for law in LAWS:
                for dh in (0.1e-6, 1e-6):
                    self.assertLess(d[(dh, law)]['ceff'], 1.0)      # below laps x dh
            for law in ('e_over_100', 'pfeiffer_100', 'pfeiffer_30'):
                t = d[(0.1e-6, law)]['t']
                self.assertLessEqual(t[2], t[0])                   # stops rising
            c = [d[(0.1e-6, k)]['ceff'] for k in ('isotropic', 'e_over_100', 'pfeiffer_100',
                                                  'pfeiffer_30')]
            self.assertEqual(c, sorted(c, reverse=True))          # softer -> smaller factor


def _case(**cw):
    c = v2(override=False, **LONG, band_positions_across_width_m=[NOZZLES[12]],
           lengthwise_continuity='continuous', appearance='loose_or_buckle')
    c['width_model'] = width_model(blocked_nozzle_indices=[12])
    c['width_model']['coil'] = {'inner_radius_m': 0.3, 'outer_radius_m': 0.9,
                                'winding_tension_pa': 20e6, 'compaction_factor': None}
    c['width_model']['incoming_ridges'] = [{'position_m': 0.85, 'height_m': 2e-6,
                                            'width_m': 0.05}]
    if cw:
        c['width_model']['coil_winding'] = dict({'radial_law': LAWS['e_over_100'],
                                                 'provenance': 'unit test', 'layers': 40}, **cw)
    return c


class Section(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.off = bd.diagnose(_case())
        cls.on = bd.diagnose(_case(layers=40))

    def test_section_filled_beside_the_linear_criterion(self):
        cw = self.on['width']['coil_winding']
        self.assertEqual(cw['status'], bw.CW_STATUS)
        self.assertIn('linear coil criterion', cw['used_by_the_evidence'])
        self.assertIn('no measured value for oily aluminium foil', cw['stack_sentence'])
        srcs = [b['source'] for b in cw['beside_linear_criterion']]
        self.assertIn('incoming ridge', srcs)
        for b in cw['beside_linear_criterion']:
            self.assertIn('linear_status', b)
            self.assertIn('effective_compaction_factor', b)
        self.assertIn(bw.CW_FLAG_STACK, self.on['flags'])
        self.assertGreaterEqual(len(cw['lanes']), 4)
        self.assertLessEqual(len(cw['radius_m']), bw.CW_MAX_RADII)
        self.assertIn('with_mechanical_profile', cw['after_unwinding'])

    def test_absent_key_changes_nothing_and_ridge_evidence_is_identical(self):
        self.assertTrue(self.off['width']['coil_winding']['not_supplied'])
        a, b = copy.deepcopy(self.on), copy.deepcopy(self.off)
        for r in (a, b):
            r['width'].pop('coil_winding')
            r['flags'] = [f for f in r['flags'] if f not in bw.CW_TOP_FLAGS]
            r['inputs']['width_model'].pop('coil_winding')
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_report_renders(self):
        html = render_band_report(self.on)
        self.assertIn('Winding the coil lane by lane', html)
        self.assertNotIn('Winding the coil lane by lane', render_band_report(self.off))

    def test_validation(self):
        for cw, msg in (({'provenance': 'x'}, 'press test'),
                        ({'radial_law': LAWS['isotropic']}, 'provenance'),
                        ({'radial_law': LAWS['isotropic'], 'provenance': 'x', 'layers': 10},
                         'layers'),
                        ({'radial_law': LAWS['isotropic'], 'provenance': 'x', 'bogus': 1},
                         'unknown keys')):
            c = _case()
            c['width_model']['coil_winding'] = cw
            with self.assertRaises(ValueError) as cm:
                bd.validate_case(c)
            self.assertIn(msg, str(cm.exception))
        c = _case()
        c['width_model']['coil'] = None
        c['width_model']['coil_winding'] = {'radial_law': LAWS['isotropic'], 'provenance': 'x'}
        with self.assertRaises(ValueError) as cm:
            bd.validate_case(c)
        self.assertIn('needs width_model.coil', str(cm.exception))

    def test_flags_have_plain_sentences(self):
        for f in bw.CW_TOP_FLAGS:
            self.assertIn(f, bpl.FLAGS)


if __name__ == '__main__':
    unittest.main()


class AllocationSensitivity(unittest.TestCase):
    """Decision after package 10: the other allocation point beside the chosen one; a verdict
    that flips, or a peak within 5 % of yield, is not reported as a plain yes or no."""

    @classmethod
    def setUpClass(cls):
        cw = bw.validate_coil_winding(
            {'radial_law': LAWS['pfeiffer_30'], 'provenance': 'unit test', 'layers': 150,
             'lane_width_m': 0.05,
             'thickness_profile': {'positions_m': [0.0, 0.6, 0.6001, 0.6499, 0.65, 1.2],
                                   'thickness_deviation_m': [0, 0, 1e-6, 1e-6, 0, 0]}},
            {'inner_radius_m': 0.15, 'outer_radius_m': 0.6, 'winding_tension_pa': 30e6,
             'compaction_factor': None})
        case = {'material': {'youngs_modulus_pa': E, 'yield_stress_pa': SY},
                'pass': {'exit_thickness_m': H, 'exit_speed_m_s': 13.0,
                         'exit_tension_pa': 40e6}, 'measurement': None}
        w = {'coil': {'inner_radius_m': 0.15, 'outer_radius_m': 0.6,
                      'winding_tension_pa': 30e6, 'compaction_factor': None},
             'coil_winding': cw}
        cls.sec = bw.coil_winding_section(case, w, {'steady': None, 'ridges': []}, 0.6, 1.2)

    def test_the_softest_stack_one_micron_lane_is_not_decided(self):
        s = self.sec
        self.assertEqual(s['status'], bw.CW_STATUS)
        self.assertEqual(len(s['lanes']), 24)
        j = 12
        lane = s['allocation_sensitivity']['lanes'][j]
        self.assertEqual(lane['mid_layer']['verdict'], 'CLOSE_TO_YIELD_NOT_DECIDED')
        self.assertEqual(lane['layer_top']['verdict'], 'YIELDS')
        self.assertAlmostEqual(lane['mid_layer']['peak_stress_pa'] / 1e6, 158.37, delta=0.05)
        self.assertLess(abs(lane['mid_layer']['effective_compaction_factor'] / 0.034 - 1), 0.03)
        self.assertLess(abs(lane['layer_top']['effective_compaction_factor'] / 0.031 - 1), 0.03)
        self.assertEqual(s['per_lane'][j]['verdict'], 'NOT_DECIDED_DEPENDS_ON_ALLOCATION_POINT')
        self.assertEqual(s['per_lane'][j]['verdict_words'],
                         'not decided: depends on the allocation point')
        self.assertIn(bw.CW_FLAG_ALLOCATION, s['flags'])
        self.assertEqual(s['per_lane'][0]['verdict'], 'DOES_NOT_YIELD')

    def test_verdict_rules(self):
        self.assertEqual(bw.CW_CLOSE_TO_YIELD_FRACTION, 0.05)
        self.assertEqual(bw._cw_variant_verdict(0.0, 158.4e6, SY), 'CLOSE_TO_YIELD_NOT_DECIDED')
        self.assertEqual(bw._cw_variant_verdict(0.0, 150e6, SY), 'DOES_NOT_YIELD')
        self.assertEqual(bw._cw_variant_verdict(0.1, 165e6, SY), 'YIELDS')
        self.assertEqual(bw._cw_lane_verdict('YIELDS', 'YIELDS'), 'YIELDS')
        self.assertEqual(bw._cw_lane_verdict('DOES_NOT_YIELD', 'CLOSE_TO_YIELD_NOT_DECIDED'),
                         'CLOSE_TO_YIELD_NOT_DECIDED')
        self.assertEqual(bw._cw_lane_verdict('DOES_NOT_YIELD', 'YIELDS'),
                         'NOT_DECIDED_DEPENDS_ON_ALLOCATION_POINT')
        self.assertIn(bw.CW_FLAG_ALLOCATION, bpl.FLAGS)
