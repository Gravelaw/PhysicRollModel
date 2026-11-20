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


if __name__ == '__main__':
    unittest.main()
