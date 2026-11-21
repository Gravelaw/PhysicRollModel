"""Wound roll accretion model and the entrained air film (``physicroll.wound_roll``, SPEC19
package 9). Software checks of the re-derived equations; nothing here validates a coil."""
import json
import unittest

from physicroll import wound_roll as wr

RC, R, TW, E, NU, H = 0.15, 0.60, 30e6, 70e9, 0.33, 30e-6
ISO = {'kind': 'constant', 'radial_modulus_pa': E}
RADII = (0.15, 0.2625, 0.375, 0.4875)
EXACT = (-54.0365e6, -26.7613e6, -14.4826e6, -6.2812e6)


def _wind(layers=100, law=ISO, **kw):
    return wr.wind_uniform(core_radius_m=RC, outer_radius_m=R, thickness_m=H,
                           winding_tension_pa=TW, hoop_modulus_pa=E, poisson_ratio=NU,
                           radial_law=law, layers=layers, **kw)


def _at(res, r):
    i = min(range(len(res['node_radius_m'])), key=lambda k: abs(res['node_radius_m'][k] - r))
    return res['radial_stress_pa'][i]


class ClosedForm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = {n: _wind(n) for n in (100, 200, 400)}

    def test_closed_form_values(self):
        for r, ex in zip(RADII, EXACT):
            cf = wr.isotropic_rigid_core_closed_form(r, RC, R, TW, NU)[0]
            self.assertAlmostEqual(cf / ex, 1.0, delta=1e-5)

    def test_radial_stress_against_the_closed_form(self):
        for n, tol in ((100, 5e-3), (400, 1.2e-3)):
            for r in RADII:
                cf = wr.isotropic_rigid_core_closed_form(r, RC, R, TW, NU)[0]
                self.assertLess(abs(_at(self.r[n], r) / cf - 1), tol, (n, r))

    def test_hoop_stress_of_the_first_layer(self):
        for n, tol in ((100, 2e6), (400, 0.5e6)):
            res = self.r[n]
            cf = wr.isotropic_rigid_core_closed_form(res['radius_m'][0], RC, R, TW, NU)[1]
            self.assertLess(abs(res['hoop_stress_pa'][0] - cf), tol)

    def test_first_order_convergence(self):
        e = {}
        for n in (200, 400):
            e[n] = sum(abs(_at(self.r[n], r) - wr.isotropic_rigid_core_closed_form(
                r, RC, R, TW, NU)[0]) for r in RADII)
        e100 = sum(abs(_at(self.r[100], r) - wr.isotropic_rigid_core_closed_form(
            r, RC, R, TW, NU)[0]) for r in RADII)
        self.assertGreater(e100 / e[200], 1.7)
        self.assertTrue(1.7 <= e[200] / e[400] <= 2.3)


class Conditions(unittest.TestCase):
    def _lane(self, **kw):
        base = dict(core_radius_m=RC, thickness_m=H, laps_per_layer=100.0, hoop_modulus_pa=E,
                    poisson_ratio=NU, radial_law=ISO)
        base.update(kw)
        lane = wr.WoundLane(**base)
        for _ in range(20):
            lane.add_layer(TW)
        return lane

    def test_outer_and_core_conditions_of_the_increment(self):
        for ec in (None, 1e9):
            lane = self._lane(core_stiffness_pa=ec)
            inc = lane.last_increment
            ds, s = inc['radial'], inc['outer_radius_m']
            self.assertLess(abs(ds[-1] - (-TW * lane.d / s)), 1e-9 * TW)
            k = (E / ec if ec else 0.0) - 1 + NU
            lhs = RC * (ds[1] - ds[0]) / lane.d
            self.assertLess(abs(lhs - ds[0] * k), 1e-9 * abs(ds[0]))

    def test_soft_core_lowers_the_core_pressure(self):
        rigid = _wind(100)
        soft = _wind(100, core_stiffness_pa=5e8)
        self.assertLess(-soft['radial_stress_pa'][0], -rigid['radial_stress_pa'][0])

    def test_softer_stack_lowers_inner_pressure_and_hoop_stress(self):
        iso = _wind(150)
        soft = _wind(150, law={'kind': 'ratio_of_hoop_modulus', 'ratio': 100})
        self.assertLess(soft['max_pressure_pa'], iso['max_pressure_pa'])
        self.assertLess(soft['min_hoop_stress_pa'], iso['min_hoop_stress_pa'])
        # planner: largest pressure 5.779 MPa, lowest hoop stress -2.98 MPa
        self.assertAlmostEqual(soft['max_pressure_pa'] / 1e6, 5.779, delta=0.005)
        self.assertAlmostEqual(soft['min_hoop_stress_pa'] / 1e6, -2.98, delta=0.01)
        self.assertIn(wr.FLAG_HOOP_COMPRESSION, soft['flags'])
        self.assertIn(wr.FLAG_STACK_LAW, soft['flags'])

    def test_pfeiffer_modulus_rises_with_pressure(self):
        law = {'kind': 'pfeiffer', 'k1_pa': 1e4, 'k2': 30.0}
        a = wr.radial_modulus_pa(law, 1e5, hoop_modulus_pa=E)
        b = wr.radial_modulus_pa(law, 1e6, hoop_modulus_pa=E)
        self.assertGreater(b, a)
        self.assertAlmostEqual(a, 30.0 * (1e5 + 1e4))

    def test_air_layer(self):
        law = {'kind': 'constant', 'radial_modulus_pa': 1e9}
        self.assertEqual(wr.radial_modulus_pa(law, 1e6, hoop_modulus_pa=E, thickness_m=H,
                                              air_gap_m=0.0), 1e9)
        tiny = wr.radial_modulus_pa(law, 1e6, hoop_modulus_pa=E, thickness_m=H, air_gap_m=1e-30)
        self.assertLess(abs(tiny / 1e9 - 1), 1e-12)
        soft = wr.radial_modulus_pa(law, 0.0, hoop_modulus_pa=E, thickness_m=H, air_gap_m=2e-6)
        self.assertLess(soft, 1e9)
        hard = wr.radial_modulus_pa(law, 1e7, hoop_modulus_pa=E, thickness_m=H, air_gap_m=2e-6)
        self.assertGreater(hard, soft)          # the gap closes under pressure

    def test_taper(self):
        res = _wind(50, tension_taper=[(0.2, 30e6), (0.5, 15e6)])
        wot = res['wound_on_tension_pa']
        self.assertAlmostEqual(wot[0], 30e6)
        self.assertAlmostEqual(wot[-1], 15e6)
        self.assertTrue(all(b <= a + 1e-6 for a, b in zip(wot, wot[1:])))


class AirFilm(unittest.TestCase):
    def test_foil_bearing_constant(self):
        self.assertAlmostEqual(wr.foil_bearing_constant(), 0.6430, delta=1e-3)
        self.assertAlmostEqual(wr.foil_bearing_constant(), 0.6430393, delta=1e-6)

    def test_two_films(self):
        self.assertLess(abs(wr.entrained_air_film_m(0.125, 20.0, 720.0) / 16.72e-6 - 1), 1e-3)
        self.assertLess(abs(wr.entrained_air_film_m(0.30, 20.0, 720.0) / 40.12e-6 - 1), 1e-3)


class Rejections(unittest.TestCase):
    def test_stack_law_is_required_and_says_what_to_measure(self):
        for law in (None, {}, {'kind': 'aluminium'}):
            with self.assertRaises(ValueError) as cm:
                _wind(10, law=law)
            self.assertIn('press test', str(cm.exception))
            self.assertIn('no radial stack stiffness of wound aluminium foil is published',
                          str(cm.exception))
        for law in ({'kind': 'ratio_of_hoop_modulus', 'ratio': 0.5},
                    {'kind': 'pfeiffer', 'k1_pa': 0.0, 'k2': 30.0},
                    {'kind': 'pfeiffer', 'k1_pa': 1e4, 'k2': 2e4},
                    {'kind': 'constant', 'radial_modulus_pa': -1.0},
                    {'kind': 'constant', 'radial_modulus_pa': 1e9, 'extra': 1}):
            with self.assertRaises(ValueError):
                _wind(10, law=law)
        with self.assertRaises(ValueError):
            wr.wind_uniform(core_radius_m=0.6, outer_radius_m=0.5, thickness_m=H,
                            winding_tension_pa=TW, hoop_modulus_pa=E, poisson_ratio=NU,
                            radial_law=ISO)
        with self.assertRaises(ValueError):
            _wind(0)

    def test_json_safe(self):
        json.dumps(_wind(30, law={'kind': 'pfeiffer', 'k1_pa': 1e4, 'k2': 30.0},
                         air_gap_m=1e-6), allow_nan=False)


if __name__ == '__main__':
    unittest.main()
