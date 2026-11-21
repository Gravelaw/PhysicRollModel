"""Linear buckling of a long strip with a wavelength search (``physicroll.strip_buckling``)."""
import json
import math
import unittest

from physicroll import strip_buckling as sb

E, NU, T, B = 210e9, 0.3, 0.5e-3, 0.150
D = E * T ** 3 / (12 * (1 - NU * NU))
EXACT_SS = 4 * math.pi ** 2 * D / (T * B * B)      # 8435559.3 Pa
SS = ('simply_supported', 'simply_supported')


def _uniform(n, width=B):
    return [width * i / n for i in range(n + 1)], [-1.0] * (n + 1)


def _gauss(z, centre, half_peak):
    g = [math.exp(-4 * math.log(2) * ((x - centre) / half_peak) ** 2) for x in z]
    width = z[-1] - z[0]
    mean = sum(0.5 * (g[i] + g[i + 1]) * (z[i + 1] - z[i]) for i in range(len(z) - 1)) / width
    return [-E * 1e-5 * (v - mean) for v in g]


def _crit(z, s, **kw):
    kw.setdefault('half_wave_range_m', (B / 4, 4 * B))
    return sb.critical_mode(z, s, thickness_m=T, youngs_modulus_pa=E, poisson_ratio=NU, **kw)


class ClosedForms(unittest.TestCase):
    def test_simply_supported_uniform_compression(self):
        z, s = _uniform(16)
        r = _crit(z, s, edges=SS)
        self.assertLess(abs(r['critical_multiplier'] / EXACT_SS - 1), 1e-6)
        self.assertLess(abs(r['half_wavelength_m'] / B - 1), 1e-3)   # search tolerance
        self.assertEqual(r['status'], sb.STATUS)
        self.assertIsNone(r['at_search_limit'])

    def test_tension_shifts_the_critical_stress_by_exactly_the_tension(self):
        z, s = _uniform(16)
        r = _crit(z, s, edges=SS, mean_tension_pa=20e6)
        self.assertLess(abs(r['critical_multiplier'] / (EXACT_SS + 20e6) - 1), 1e-6)
        k = math.pi / B
        a = sb.multiplier_at(z, s, k, thickness_m=T, youngs_modulus_pa=E, poisson_ratio=NU,
                             edges=SS)['critical_multiplier']
        b = sb.multiplier_at(z, s, k, thickness_m=T, youngs_modulus_pa=E, poisson_ratio=NU,
                             edges=SS, mean_tension_pa=20e6)['critical_multiplier']
        self.assertLess(abs((b - a) / 20e6 - 1), 1e-5)

    def test_clamped_coefficient_and_half_wave(self):
        z, s = _uniform(16)
        r = _crit(z, s, edges=('clamped', 'clamped'))
        self.assertLess(abs(r['critical_multiplier'] / EXACT_SS * 4 / 6.97 - 1), 2e-3)
        self.assertLess(abs(r['half_wavelength_m'] / B / 0.66 - 1), 2e-3)

    def test_simply_supported_free_at_fixed_half_wave(self):
        z, s = _uniform(16)
        m = sb.multiplier_at(z, s, math.pi / (20 * B), thickness_m=T, youngs_modulus_pa=E,
                             poisson_ratio=NU, edges=('simply_supported', 'free'))
        self.assertLess(abs(m['critical_multiplier'] / EXACT_SS * 4 / 0.4275 - 1), 2e-3)

    def test_convergence_8_to_16_elements(self):
        e8 = _crit(*_uniform(8), edges=SS)['critical_multiplier'] / EXACT_SS - 1
        e16 = _crit(*_uniform(16), edges=SS)['critical_multiplier'] / EXACT_SS - 1
        self.assertLess(abs(e16), abs(e8))
        self.assertLess(abs(e8), 2e-5)


class Behaviour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.z = [0.27 * i / 108 for i in range(109)]
        cls.s = _gauss(cls.z, 0.135, 0.05)

    def _wide(self, z, s, **kw):
        w = z[-1] - z[0]
        return sb.critical_mode(z, s, thickness_m=0.3e-3, youngs_modulus_pa=70e9,
                                poisson_ratio=0.33, half_wave_range_m=(4 * w / 108, 2 * w),
                                **kw)

    def test_tension_raises_the_critical_load_and_shortens_the_wave(self):
        lo = self._wide(self.z, self.s, mean_tension_pa=5e6)
        hi = self._wide(self.z, self.s, mean_tension_pa=15e6)
        self.assertGreater(hi['critical_multiplier'], lo['critical_multiplier'])
        self.assertLess(hi['half_wavelength_m'], lo['half_wavelength_m'])
        self.assertLess(hi['mode_width_10_percent_m'], lo['mode_width_10_percent_m'])
        self.assertAlmostEqual(lo['mode_peak_position_m'], 0.135, delta=0.003)
        self.assertAlmostEqual(lo['utilisation'], 1 / lo['critical_multiplier'])

    def test_mesh_independence_of_a_gaussian_case(self):
        res = []
        for n in (120, 240):
            z = [0.27 * i / n for i in range(n + 1)]
            r = sb.critical_mode(z, _gauss(z, 0.135, 0.05), thickness_m=0.3e-3,
                                 youngs_modulus_pa=70e9, poisson_ratio=0.33,
                                 mean_tension_pa=10e6, half_wave_range_m=(0.01, 0.54))
            res.append(r['critical_multiplier'])
        self.assertLess(abs(res[1] / res[0] - 1), 5e-3)

    def test_multiplier_at_equals_the_scan_value(self):
        r = self._wide(self.z, self.s, mean_tension_pa=5e6)
        row = r['scan'][5]
        m = sb.multiplier_at(self.z, self.s, math.pi / row['half_wavelength_m'],
                             thickness_m=0.3e-3, youngs_modulus_pa=70e9, poisson_ratio=0.33,
                             mean_tension_pa=5e6)
        self.assertLess(abs(m['critical_multiplier'] / row['critical_multiplier'] - 1), 1e-12)
        self.assertLessEqual(r['critical_multiplier'],
                             min(x['critical_multiplier'] for x in r['scan']) * (1 + 1e-12))

    def test_no_compression_no_buckling(self):
        z = self.z
        r = sb.critical_mode(z, [1e6] * len(z), thickness_m=0.3e-3, youngs_modulus_pa=70e9,
                             poisson_ratio=0.33)
        self.assertEqual(r['status'], sb.NO_BUCKLING)
        self.assertIsNone(r['critical_multiplier'])
        self.assertEqual(r['utilisation'], 0.0)

    def test_search_limit_flags(self):
        r = self._wide(self.z, self.s)                    # no tension: whole-sheet mode
        self.assertEqual(r['at_search_limit'], 'LONGEST')
        self.assertIn(sb.FLAG_LONGEST, r['flags'])
        z, s = _uniform(16)
        r = _crit(z, s, edges=SS, half_wave_range_m=(2 * B, 4 * B))
        self.assertEqual(r['at_search_limit'], 'SHORTEST')
        self.assertIn(sb.FLAG_SHORTEST, r['flags'])

    def test_mirrored_profile_gives_the_mirrored_mode(self):
        s = _gauss(self.z, 0.10, 0.05)
        a = self._wide(self.z, s, mean_tension_pa=5e6)
        b = self._wide(self.z, s[::-1], mean_tension_pa=5e6)
        self.assertLess(abs(a['critical_multiplier'] / b['critical_multiplier'] - 1), 1e-9)
        for u, v in zip(a['mode'], b['mode'][::-1]):
            self.assertAlmostEqual(u, v, delta=1e-4)

    def test_non_uniform_spacing_gives_the_same_answer(self):
        n = 108
        zu = [0.27 * i / n for i in range(n + 1)]
        zn = [0.27 * (i / n + 0.3 * math.sin(math.pi * i / n) / n) for i in range(n + 1)]
        a = sb.critical_mode(zu, _gauss(zu, 0.135, 0.05), thickness_m=0.3e-3,
                             youngs_modulus_pa=70e9, poisson_ratio=0.33, mean_tension_pa=10e6,
                             half_wave_range_m=(0.01, 0.54))
        b = sb.critical_mode(zn, _gauss(zn, 0.135, 0.05), thickness_m=0.3e-3,
                             youngs_modulus_pa=70e9, poisson_ratio=0.33, mean_tension_pa=10e6,
                             half_wave_range_m=(0.01, 0.54))
        self.assertLess(abs(a['critical_multiplier'] / b['critical_multiplier'] - 1), 1e-3)

    def test_rejections(self):
        z, s = _uniform(4)
        bad = [dict(z_m=[0.0, 0.1], residual_stress_pa=[-1.0, -1.0]),
               dict(z_m=[0.0, 0.1, 0.1], residual_stress_pa=[-1.0] * 3),
               dict(z_m=z, residual_stress_pa=s[:-1]),
               dict(z_m=z, residual_stress_pa=[-6e9] * len(z)),
               dict(z_m=z, residual_stress_pa=s, mean_tension_pa=-1.0),
               dict(z_m=z, residual_stress_pa=s, edges=('free', 'pinned')),
               dict(z_m=z, residual_stress_pa=s, coarse=3),
               dict(z_m=z, residual_stress_pa=s, refine=31),
               dict(z_m=z, residual_stress_pa=s, half_wave_range_m=(0.2, 0.1))]
        for kw in bad:
            with self.assertRaises(ValueError):
                sb.critical_mode(thickness_m=T, youngs_modulus_pa=E, poisson_ratio=NU, **kw)

    def test_json_safe(self):
        r = self._wide(self.z, self.s, mean_tension_pa=5e6)
        json.dumps(r, allow_nan=False)
        self.assertEqual(len(r['mode']), len(self.z))
        self.assertEqual(max(r['mode'], key=abs), 1.0)


class PostBuckling(unittest.TestCase):
    """SPEC19 package 7: one-mode Ritz amplitude, saturated stress, dead load on a table."""

    def _top_hat(self, sc=2e6, lam=0.6, n=200, width=1.0, band=(0.45, 0.55)):
        z = [width * i / n for i in range(n + 1)]
        f = [1.0 if band[0] - 1e-12 <= x <= band[1] + 1e-12 else 0.0 for x in z]
        s = [-sc if v else 0.0 for v in f]
        k = 2 * math.pi / 0.08
        return z, f, s, {'critical_multiplier': lam, 'mode': f, 'wavenumber_per_m': k}

    def test_top_hat_self_check_wave_formula_and_saturation(self):
        sc, lam = 2e6, 0.6
        z, f, s, mres = self._top_hat(sc, lam)
        r = sb.post_buckling(z, s, mres, thickness_m=0.1e-3, youngs_modulus_pa=70e9)
        i2 = sum(0.5 * (f[i] ** 2 + f[i + 1] ** 2) * (z[i + 1] - z[i]) for i in range(len(z) - 1))
        m = i2 / (z[-1] - z[0])
        H, L = r['peak_to_valley_m'], r['wavelength_m']
        scr = lam * sc
        self.assertLess(abs((math.pi * H / (2 * L)) ** 2 * 70e9 * (1 - m) / (sc - scr) - 1), 1e-6)
        for v, fv in zip(r['saturated_stress_pa'], f):
            if fv == 1.0:
                self.assertLess(abs(v / (-scr) - 1), 1e-6)
        self.assertEqual(r['state'], 'BUCKLED')

    def test_amplitude_zero_at_and_below_critical_and_square_root_above(self):
        z, f, s, mres = self._top_hat()
        a = []
        for scale in (0.5, 0.6, 0.7, 0.9):     # critical at 0.6 of the reference profile
            ss = [scale / 0.6 * 0.6 * v for v in s]
            r = sb.post_buckling(z, ss, dict(mres, critical_multiplier=0.6 / scale),
                                 thickness_m=0.1e-3, youngs_modulus_pa=70e9)
            a.append(r['amplitude_m'])
        self.assertEqual(a[0], 0.0)
        self.assertLess(a[1], 1e-12)
        # a^2 proportional to (scale - critical) for the top hat
        self.assertAlmostEqual((a[3] / a[2]) ** 2, (0.9 - 0.6) / (0.7 - 0.6), delta=1e-6)

    def test_mean_of_saturated_stress_equals_the_tension(self):
        z = [0.27 * i / 108 for i in range(109)]
        s = _gauss(z, 0.135, 0.05)
        s = [70e9 / E * v * 30 for v in s]            # aluminium, 30 I-units peak
        m = sb.critical_mode(z, s, thickness_m=0.3e-3, youngs_modulus_pa=70e9,
                             poisson_ratio=0.33, mean_tension_pa=5e6,
                             half_wave_range_m=(0.01, 0.54))
        self.assertGreater(m['utilisation'], 1.0)
        r = sb.post_buckling(z, s, m, thickness_m=0.3e-3, youngs_modulus_pa=70e9,
                             mean_tension_pa=5e6)
        sat = r['saturated_stress_pa']
        mean = sum(0.5 * (sat[i] + sat[i + 1]) * (z[i + 1] - z[i])
                   for i in range(len(z) - 1)) / 0.27
        self.assertLess(abs(mean - 5e6), 1e-9 * 5e6 + 1e-3)
        self.assertGreater(r['amplitude_m'], 0.0)

    def _table(self, **kw):
        z = [0.27 * i / 54 for i in range(55)]
        peak = kw.pop('peak', 5.0)
        s = [70e9 / E * v * peak for v in _gauss(z, 0.135, 0.05)]
        return z, s, sb.dead_load_lift(z, s, youngs_modulus_pa=70e9, poisson_ratio=0.33,
                                       **dict({'thickness_m': 0.1e-3}, **kw))

    def test_lift_scale_above_the_weightless_multiplier_and_limit_condition(self):
        z, s, d = self._table()
        for row in d['scan']:
            self.assertGreater(row['scale_to_lift'], row['weightless_multiplier'])
        c = d['best_lift_condition']
        # at the lift limit (scale s_lift) Pi_t = 0 and dPi_t/da = 0: a^2 = 2*c2/(3*c4) and
        # g1 = c2*a/3; check with c2 of the scaled profile
        self.assertIn(sb.FLAG_DENSITY, d['flags'])
        z2, s2, d2 = z, [v * d['scale_to_lift'] for v in s], None
        d2 = sb.dead_load_lift(z2, s2, thickness_m=0.1e-3, youngs_modulus_pa=70e9,
                               poisson_ratio=0.33)
        best = min(d2['scan'], key=lambda r: r['scale_to_lift'])
        self.assertLess(abs(best['scale_to_lift'] - 1.0), 1e-6)
        cc = d2['best_lift_condition']
        a = math.sqrt(2 * cc['c2'] / (3 * cc['c4']))
        pit = -(cc['c2'] / 2) * a * a + (cc['c4'] / 4) * a ** 4 + cc['g1'] * a
        dpit = -cc['c2'] * a + cc['c4'] * a ** 3 + cc['g1']
        self.assertLess(abs(pit) / (cc['g1'] * a), 1e-6)
        self.assertLess(abs(dpit) / cc['g1'], 1e-6)
        self.assertTrue(c['c4'] > 0)

    def test_heavier_or_thicker_sheet_raises_the_limit(self):
        _, _, d = self._table()
        _, _, heavy = self._table(density_kg_m3=7850.0)
        _, _, thick = self._table(thickness_m=0.2e-3)
        self.assertGreater(heavy['scale_to_lift'], d['scale_to_lift'])
        self.assertGreater(thick['scale_to_lift'], d['scale_to_lift'])
        self.assertNotIn(sb.FLAG_DENSITY, heavy['flags'])

    def test_table_height_below_the_weightless_height(self):
        _, _, d = self._table(peak=40.0)
        self.assertEqual(d['state'], 'LIFTS')
        self.assertGreater(d['peak_to_valley_on_table_m'], 0.0)
        self.assertLess(d['peak_to_valley_on_table_m'], d['weightless_peak_to_valley_m'])
        _, _, flat = self._table(peak=1e-3)
        self.assertEqual(flat['state'], 'LIES_FLAT')
        self.assertEqual(flat['peak_to_valley_on_table_m'], 0.0)
        json.dumps(d, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
