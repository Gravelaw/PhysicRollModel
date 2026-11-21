"""Wound roll accretion model and the entrained air film (``physicroll.wound_roll``, SPEC19
package 9). Software checks of the re-derived equations; nothing here validates a coil."""
import json
import math
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


class CoilTemperature(unittest.TestCase):
    """SPEC19 package 11: conductivities, the cooling solutions and the nip tension."""

    def test_series_and_parallel_conductivities(self):
        self.assertAlmostEqual(wr.radial_conductivity_w_mk(H, 0.5e-6, 200.0, 0.13), 7.63,
                               delta=0.01)
        self.assertAlmostEqual(wr.radial_conductivity_w_mk(H, 2e-6, 200.0, 0.026), 0.415,
                               delta=0.002)
        self.assertAlmostEqual(wr.axial_conductivity_w_mk(H, 0.5e-6, 200.0), 200 * 30 / 30.5)
        self.assertEqual(wr.radial_conductivity_w_mk(H, 0.0, 200.0, 0.13), 200.0)

    def _cool(self, **kw):
        base = dict(inner_radius_m=0.15, outer_radius_m=0.6, width_m=1.2, surface_htc_w_m2k=8.0,
                    k_radial_w_mk=7.63, k_axial_w_mk=196.7, rho_c_j_m3k=2.39e6,
                    hold_times_s=[3600.0, 14400.0, 86400.0])
        base.update(kw)
        return wr.coil_cooling(**base)

    def test_lumped_limits_at_small_biot(self):
        rc, h = 2.39e6, 8.0
        # slab alone (radial very conductive): the axial solution against exp(-t*h/(rho*c*L))
        c = self._cool(k_radial_w_mk=1e6, k_axial_w_mk=1e5)
        for r in c['rows']:
            tz = r['theta_z'][0]
            ex = math.exp(-r['time_s'] * h / (rc * 0.6))
            self.assertLess(abs(tz / ex - 1), 0.02)
            tr = r['theta_r'][-1]
            ex_r = math.exp(-r['time_s'] * 2 * 0.6 * h / (rc * (0.6 ** 2 - 0.15 ** 2)))
            self.assertLess(abs(tr / ex_r - 1), 0.02)

    def test_product_structure_against_a_two_dimensional_solve(self):
        ri, ro, wd, h, kr, kz, rc, t_end = 0.15, 0.25, 0.2, 50.0, 2.0, 20.0, 2.0e6, 1500.0
        c = wr.coil_cooling(inner_radius_m=ri, outer_radius_m=ro, width_m=wd,
                            surface_htc_w_m2k=h, k_radial_w_mk=kr, k_axial_w_mk=kz,
                            rho_c_j_m3k=rc, hold_times_s=[t_end])
        prod = c['rows'][0]['mean']
        # independent explicit 2-D finite volumes (r, z from mid width), coarse grid
        nr, nz = 12, 12
        dr, dz = (ro - ri) / nr, (wd / 2) / nz
        rcs = [ri + (i + 0.5) * dr for i in range(nr)]
        th = [[1.0] * nz for _ in range(nr)]
        dt = 0.2 * min(rc * dr * dr / kr, rc * dz * dz / kz)
        steps = int(t_end / dt) + 1
        dt = t_end / steps
        for _ in range(steps):
            new = [row[:] for row in th]
            for i in range(nr):
                r = rcs[i]
                vol = 2 * math.pi * r * dr * dz * rc
                for j in range(nz):
                    q = 0.0
                    if i > 0:
                        q += kr * 2 * math.pi * (r - dr / 2) * dz / dr * (th[i - 1][j] - th[i][j])
                    if i < nr - 1:
                        q += kr * 2 * math.pi * (r + dr / 2) * dz / dr * (th[i + 1][j] - th[i][j])
                    else:
                        a = 2 * math.pi * ro * dz
                        q -= th[i][j] / (1 / (h * a) + (dr / 2) / (kr * a))
                    a_z = 2 * math.pi * r * dr
                    if j > 0:
                        q += kz * a_z / dz * (th[i][j - 1] - th[i][j])
                    if j < nz - 1:
                        q += kz * a_z / dz * (th[i][j + 1] - th[i][j])
                    else:
                        q -= th[i][j] / (1 / (h * a_z) + (dz / 2) / (kz * a_z))
                    new[i][j] = th[i][j] + dt * q / vol
            th = new
        vols = [[2 * math.pi * rcs[i] * dr * dz for _ in range(nz)] for i in range(nr)]
        mean2 = sum(th[i][j] * vols[i][j] for i in range(nr) for j in range(nz)) / sum(
            sum(v) for v in vols)
        self.assertLess(abs(mean2 / prod - 1), 0.01)

    def test_monotone_cooling_and_time_scales(self):
        c = self._cool()
        hot = [r['hottest'] for r in c['rows']]
        self.assertEqual(hot, sorted(hot, reverse=True))
        hist = [v for _, v in c['hottest_history']]
        self.assertTrue(all(b <= a + 1e-12 for a, b in zip(hist, hist[1:])))
        ts = c['time_scales']
        self.assertAlmostEqual(ts['biot_radial'], 8 * 0.45 / 7.63)
        self.assertAlmostEqual(ts['axial_s'] / 3600, 0.36 * 2.39e6 / 196.7 / 3600)
        t = wr.time_to_fall_below(c['hottest_history'], 0.5)
        self.assertTrue(t is None or 0 < t <= 86400)
        # one entry per step of every segment (three hold times), times increasing
        self.assertEqual(len(c['hottest_history']), 1 + 3 * wr.COOLING_STEPS)
        times = [t for t, _ in c['hottest_history']]
        self.assertTrue(all(b > a for a, b in zip(times, times[1:])))

    # the reviewer's thin coil: a short and a long hold time requested together
    THIN = dict(inner_radius_m=0.30, outer_radius_m=0.31, width_m=0.1, surface_htc_w_m2k=20.0,
                k_radial_w_mk=1.0, k_axial_w_mk=220.0, rho_c_j_m3k=2.43e6)

    def _at(self, t, times):
        c = wr.coil_cooling(hold_times_s=times, **self.THIN)
        return next(r for r in c['rows'] if r['time_s'] == t)

    def test_short_hold_time_not_taken_from_a_later_step(self):
        # before the fix the 10 s row with 86400 s also requested was 0.849 (the profile of the
        # first step after 10 s of 400 steps to 86400 s, i.e. at 216 s), alone 0.999
        alone = self._at(10.0, [10.0])['hottest']
        both = self._at(10.0, [10.0, 86400.0])['hottest']
        self.assertAlmostEqual(alone, 0.999070274052103, places=12)
        self.assertAlmostEqual(both, alone, delta=1e-9)

    def test_value_at_a_time_independent_of_later_times(self):
        times = [60.0, 600.0, 7200.0]
        for k, t in enumerate(times):
            prefix = times[:k + 1]
            ref = self._at(t, prefix)
            for later in ([86400.0], [9000.0, 86400.0], times[k + 1:]):
                req = prefix + [x for x in later if x > t]
                r = self._at(t, req)
                for key in ('hottest', 'mean', 'outer_surface_mid_width'):
                    self.assertAlmostEqual(r[key], ref[key], delta=1e-12, msg=(t, req, key))

    def test_one_hold_time_reproduces_the_previous_solver(self):
        # values of the solver before segment-by-segment stepping (400 equal steps to the time)
        r = self._at(10.0, [10.0])
        self.assertAlmostEqual(r['mean'], 0.9902552878566271, places=14)
        self.assertAlmostEqual(r['outer_surface_mid_width'], 0.9571814812217477, places=14)
        c = self._cool(hold_times_s=[86400.0])
        row = c['rows'][0]
        self.assertAlmostEqual(row['hottest'], 0.28027454527752993, places=14)
        self.assertAlmostEqual(row['mean'], 0.2517311309063244, places=14)
        self.assertAlmostEqual(row['outer_surface_mid_width'], 0.22189127525023664, places=14)
        self.assertEqual(len(c['hottest_history']), 1 + wr.COOLING_STEPS)
        t, v = c['hottest_history'][137]
        self.assertAlmostEqual(t, 29592.0, places=6)
        self.assertAlmostEqual(v, 0.6913718590022591, places=14)

    def test_layers_never_change_the_amount_wound(self):
        # 0.30 -> 0.31 m of 1 mm strip is ten laps: before the fix 150 layers wound 150 laps
        # (undeformed outer radius 0.45 m)
        law = {'kind': 'constant', 'radial_modulus_pa': E}
        for layers, used in ((5, 5), (10, 10), (150, 10)):
            u = wr.wind_uniform(core_radius_m=0.30, outer_radius_m=0.31, thickness_m=1e-3,
                                winding_tension_pa=TW, hoop_modulus_pa=E, poisson_ratio=NU,
                                radial_law=law, layers=layers)
            self.assertAlmostEqual(u['node_radius_m'][-1], 0.31, places=12)
            self.assertEqual((u['layers_requested'], u['layers_used']), (layers, used))
            self.assertAlmostEqual(u['laps_per_layer'] * used, 10.0, places=9)
            ln = wr.wind_lanes(core_radius_m=0.30, outer_radius_m=0.31, thicknesses_m=[1e-3] * 2,
                               widths_m=[0.05] * 2, winding_tension_pa=TW, hoop_modulus_pa=E,
                               poisson_ratio=NU, yield_stress_pa=165e6, radial_law=law,
                               layers=layers)
            self.assertAlmostEqual(ln['lanes'][0].r[-1], 0.31, places=12)
            self.assertEqual((ln['layers_used'], ln['layers_wound']), (used, used))
        # 150 and 10 requested layers are the same problem now
        a = wr.wind_uniform(core_radius_m=0.30, outer_radius_m=0.31, thickness_m=1e-3,
                            winding_tension_pa=TW, hoop_modulus_pa=E, poisson_ratio=NU,
                            radial_law=law, layers=150)
        self.assertAlmostEqual(a['max_pressure_pa'], 991773.8196008212, delta=1e-3)
        # a fractional lap count: 10.5 laps in 10 layers of 1.05; half a lap in one layer
        for outer, used, nl in ((0.3105, 10, 1.05), (0.3005, 1, 0.5)):
            u = wr.wind_uniform(core_radius_m=0.30, outer_radius_m=outer, thickness_m=1e-3,
                                winding_tension_pa=TW, hoop_modulus_pa=E, poisson_ratio=NU,
                                radial_law=law, layers=150)
            self.assertEqual(u['layers_used'], used)
            self.assertAlmostEqual(u['laps_per_layer'], nl, places=9)
            self.assertAlmostEqual(u['node_radius_m'][-1], outer, places=12)

    def test_many_laps_per_layer_unchanged(self):
        # values before the layer cap (15000 laps in 150 and 40 layers)
        u = _wind(150)
        self.assertEqual(u['layers_used'], 150)
        self.assertAlmostEqual(u['max_pressure_pa'], 54174158.644881345, delta=1e-3)
        self.assertAlmostEqual(u['outer_radius_m'], 0.5999144321447712, places=13)
        self.assertAlmostEqual(u['min_hoop_stress_pa'], 9431243.83491057, delta=1e-3)
        ln = wr.wind_lanes(core_radius_m=0.15, outer_radius_m=0.6,
                           thicknesses_m=[30e-6, 30.1e-6, 29.9e-6], widths_m=[0.05] * 3,
                           winding_tension_pa=30e6, hoop_modulus_pa=E, poisson_ratio=NU,
                           yield_stress_pa=165e6,
                           radial_law={'kind': 'constant', 'radial_modulus_pa': 1e9}, layers=40)
        for lane, r, t in zip(ln['lanes'], (0.5987331254395508, 0.5989529901759905,
                                            0.5984980398986375),
                              (30992232.999339223, 65217431.3476771, 21543903.201102853)):
            self.assertAlmostEqual(lane.outer_radius_m, r, places=13)
            self.assertAlmostEqual(max(lane.wound_on), t, delta=1e-4)

    def test_nip_tension_and_cap(self):
        t, capped = wr.wound_in_tension_pa(30e6, H, 500.0, 0.1, 165e6)
        self.assertAlmostEqual(t, 30e6 + 0.1 * 500.0 / H)
        self.assertFalse(capped)
        t, capped = wr.wound_in_tension_pa(30e6, H, 1e5, 1.0, 165e6)
        self.assertTrue(capped)
        self.assertLess(t, 165e6)

    def test_entrained_film_of_the_demo_coil(self):
        self.assertLess(abs(wr.entrained_air_film_m(0.15, 26.0, 900.0) / 20.6e-6 - 1), 2e-3)
        self.assertLess(abs(wr.entrained_air_film_m(0.6, 26.0, 900.0) / 82.38e-6 - 1), 1e-3)

    def test_per_layer_air_gap_softens_the_stack(self):
        law = {'kind': 'constant', 'radial_modulus_pa': 1e9}
        base = dict(core_radius_m=0.15, outer_radius_m=0.6, thicknesses_m=[H] * 4,
                    widths_m=[0.05] * 4, winding_tension_pa=30e6, hoop_modulus_pa=E,
                    poisson_ratio=NU, yield_stress_pa=165e6, radial_law=law, layers=40)
        dry = wr.wind_lanes(**base)['lanes'][0]
        wet = wr.wind_lanes(air_gap_of=lambda s, t: 5e-6, **base)['lanes'][0]
        self.assertLess(max(-v for v in wet.radial_stress), max(-v for v in dry.radial_stress))
        self.assertTrue(all(g < 5e-6 for g in wet.gap_under_pressure_m()))


if __name__ == '__main__':
    unittest.main()
