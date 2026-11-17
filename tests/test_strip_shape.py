import json
import math
import unittest

from physicroll import strip_shape as ss
from physicroll.strip_shape import (
    classify_crown_change, coil_ridge_buildup, crown_heredity, differential_elongation,
    flatness_from_elongation, grinding_feed_pitch_m, i_units_from_wave, i_units_to_stress_pa,
    local_bump_transfer, match_positions, match_spacing, narrow_band_buckling_stress_pa,
    roll_line_compliance_m2_n, roller_wrinkle_critical_lateral_stress_pa,
    shohet_townsend_window, spacing_analysis, tension_trough_screen,
    tension_wrinkle_amplitude_m, tension_wrinkle_wavelength_m, thermal_stripe_flatness,
    transfer_radius_profile, trough_critical_lateral_stress_pa, two_tone_positions_m)

E_AL, NU_AL = 70e9, 0.33
DZ = 0.005
Z = [(i + 0.5) * DZ for i in range(300)]          # 1.5 m strip, centre 0.75 m


def stripe(height_m, centre_m=0.75, width_m=0.05):
    return [height_m if abs(z - centre_m) < width_m / 2 else 0.0 for z in Z]


def dumps(value):
    return json.dumps(value, allow_nan=False)


class TestLocalTransfer(unittest.TestCase):
    def test_compliance_check_value(self):
        # 2*(1-0.09)/(pi*210e9) * (ln(0.05/(pi*0.002)) + 0.42278) = 6.889e-12
        expected = 2 * 0.91 / (math.pi * 210e9) * (math.log(0.05 / (math.pi * 0.002))
                                                    + 1 - 0.5772156649)
        c = roll_line_compliance_m2_n(0.05, 0.002, 210e9, 0.3)
        self.assertAlmostEqual(c / expected, 1.0, places=9)
        self.assertLess(abs(c - 6.88e-12) / 6.88e-12, 2e-3)   # spec value, rounding

    def test_transfer_check_values(self):
        r = local_bump_transfer(0.05, 0.002, 5e10, roll_youngs_modulus_pa=210e9,
                                roll_poisson_ratio=0.3, radius_deviation_m=1e-7)
        self.assertAlmostEqual(r['transfer_factor'], 1 / (1 + 2 * 6.889e-12 * 5e10), places=3)
        self.assertAlmostEqual(round(r['transfer_factor'], 2), 0.59)
        self.assertAlmostEqual(r['local_thickness_change_m'], -2 * r['transfer_factor'] * 1e-7)
        r2 = local_bump_transfer(0.05, 0.002, 5e11)
        self.assertAlmostEqual(round(r2['transfer_factor'], 2), 0.13)
        self.assertEqual(r2['status'], 'UNVALIDATED_LOCAL_TRANSFER_ESTIMATE')

    def test_transfer_monotonic(self):
        ts = [local_bump_transfer(0.05, 0.003, q)['transfer_factor']
              for q in (1e9, 1e10, 1e11, 1e12)]
        self.assertTrue(all(a > b for a, b in zip(ts, ts[1:])))
        tl = [local_bump_transfer(lam, 0.003, 1e10)['transfer_factor']
              for lam in (0.02, 0.05, 0.1, 0.2)]
        self.assertTrue(all(a > b for a, b in zip(tl, tl[1:])))

    def test_validity_flags(self):
        with self.assertRaises(ValueError):
            roll_line_compliance_m2_n(0.007, 0.002)
        r = local_bump_transfer(0.5, 0.003, 1e10, roll_radius_m=0.2)
        self.assertIn('LONG_WAVELENGTH_BELONGS_TO_CROWN_MODEL', r['flags'])
        r = local_bump_transfer(0.1, 0.003, 1e10, roll_radius_m=0.2, n_rolls=1)
        self.assertNotIn('LONG_WAVELENGTH_BELONGS_TO_CROWN_MODEL', r['flags'])
        self.assertAlmostEqual(r['thickness_change_per_radius_deviation'],
                               -r['transfer_factor'])

    def test_dft_round_trip(self):
        x = [math.sin(0.3 * i) + 0.1 * i - 0.002 * i * i for i in range(64)]
        back = [v.real / 64 for v in ss._dft(ss._dft(x), sign=+1)]
        for a, b in zip(x, back):
            self.assertAlmostEqual(a, b, places=10)

    def test_sinusoid_is_eigenfunction(self):
        n, dz = 200, 0.005           # period 1.0 m, k = 10 -> lam = 0.1 m
        z = [i * dz for i in range(n)]
        dr = [1e-7 * math.cos(2 * math.pi * 10 * v) for v in z]
        r = transfer_radius_profile(z, dr, bite_half_length_m=0.003,
                                    strip_stiffness_per_width_pa=1e10, roll_radius_m=0.2)
        t = local_bump_transfer(0.1, 0.003, 1e10)['transfer_factor']
        for a, b in zip(dr, r['local_thickness_change_m']):
            self.assertAlmostEqual(b, -2 * t * a, delta=1e-18)
        self.assertLess(r['short_wavelength_energy_fraction'], 1e-20)
        self.assertLess(r['long_wavelength_energy_fraction'], 1e-20)
        self.assertNotIn('LONG_WAVELENGTH_BELONGS_TO_CROWN_MODEL', r['flags'])

    def test_spectrum_flags(self):
        z = [i * 0.002 for i in range(200)]
        spike = [1e-7 if i == 100 else 0.0 for i in range(200)]
        r = transfer_radius_profile(z, spike, bite_half_length_m=0.003,
                                    strip_stiffness_per_width_pa=1e10, roll_radius_m=0.2)
        self.assertIn('SHORT_WAVELENGTH_OUTSIDE_COMPLIANCE_VALIDITY', r['flags'])
        longwave = [1e-7 * math.cos(2 * math.pi * v / 0.4) for v in z]   # lam 0.4 > R
        r = transfer_radius_profile(z, longwave, bite_half_length_m=0.003,
                                    strip_stiffness_per_width_pa=1e10, roll_radius_m=0.2)
        self.assertIn('LONG_WAVELENGTH_BELONGS_TO_CROWN_MODEL', r['flags'])
        t_r = local_bump_transfer(0.2, 0.003, 1e10)['transfer_factor']
        self.assertAlmostEqual(r['local_thickness_change_m'][0], -2 * t_r * 1e-7, delta=1e-18)


class TestCrownAndFlatness(unittest.TestCase):
    def test_heredity_limits(self):
        r0 = crown_heredity(20e-6, 40e-6, 2e-3, 1e-3, 0.0)
        self.assertAlmostEqual(r0['exit_crown_m'], 20e-6)
        r1 = crown_heredity(20e-6, 40e-6, 2e-3, 1e-3, 1.0)
        self.assertAlmostEqual(r1['exit_crown_m'], 20e-6)    # (h/H)*C_H = 0.5*40 um
        r1 = crown_heredity(5e-6, 40e-6, 2e-3, 1e-3, 1.0)
        self.assertAlmostEqual(r1['exit_crown_m'], 20e-6)
        self.assertAlmostEqual(r1['relative_crown_change'], 0.0, places=15)
        rh = crown_heredity(10e-6, 40e-6, 2e-3, 1e-3, 0.5)
        self.assertAlmostEqual(rh['exit_crown_m'], 0.5 * 10e-6 + 0.5 * 20e-6)
        c = classify_crown_change(40e-6, 2e-3, 20e-6, 1e-3, 1.5)
        self.assertEqual(c['status'], 'WITHIN_DEAD_BAND')

    def test_shohet_townsend_check_values(self):
        s = (0.2 / 1500) ** 1.86
        w = shohet_townsend_window(0.2e-3, 1.5)
        self.assertAlmostEqual(w['upper_bound'], 40 * s, delta=1e-15)
        self.assertAlmostEqual(w['lower_bound'], -80 * s, delta=1e-15)
        self.assertLess(abs(w['upper_bound'] - 2.5e-6), 0.02 * 2.5e-6)
        self.assertLess(abs(w['lower_bound'] + 5.0e-6), 0.02 * 5.0e-6)
        self.assertLess(w['upper_bound_i_units'], 1.0)
        w2 = shohet_townsend_window(2e-3, 1.5)
        self.assertAlmostEqual(w2['upper_bound_i_units'], 18.0, delta=0.1)
        self.assertLess(shohet_townsend_window(0.2e-3, 1.5, beta=2.0)['upper_bound'],
                        w['upper_bound'])

    def test_classify_sign(self):
        # entry relative crown 2e-5; exit flat -> delta = +2e-5 > +2.5e-6 -> centre buckle
        self.assertEqual(classify_crown_change(20e-6, 1e-3, 0.0, 0.2e-3, 1.5)['status'],
                         'CENTRE_BUCKLE_RISK')
        self.assertEqual(classify_crown_change(0.0, 1e-3, 4e-9, 0.2e-3, 1.5)['status'],
                         'EDGE_WAVE_RISK')
        self.assertEqual(classify_crown_change(0.0, 1e-3, 0.4e-9, 0.2e-3, 1.5)['status'],
                         'WITHIN_DEAD_BAND')

    def test_proportional_profile_gives_zero_i_units(self):
        z = [i * 0.01 for i in range(151)]
        entry = [2e-3 * (1 + 0.01 * (1 - ((v - 0.75) / 0.75) ** 2)) for v in z]
        exit_ = [0.1 * v for v in entry]
        el = differential_elongation(z, entry, exit_)
        self.assertTrue(all(abs(e) < 1e-14 for e in el['elongation']))
        el = differential_elongation(z, [2e-3] * len(z), [0.2e-3] * len(z))
        fl = flatness_from_elongation(z, el['elongation'], youngs_modulus_pa=E_AL,
                                      poisson_ratio=NU_AL, thickness_m=0.2e-3,
                                      mean_tension_pa=30e6)
        self.assertTrue(all(abs(i) < 1e-9 for i in fl['i_units']))
        self.assertEqual(fl['status'], 'NO_BANDS_ABOVE_THRESHOLD')

    def test_elongation_sign(self):
        z = [0.0, 0.1, 0.2, 0.3]
        el = differential_elongation(z, [1e-3] * 4, [0.5e-3, 0.5e-3, 0.49e-3, 0.5e-3])
        self.assertGreater(el['elongation'][2], 0)      # thinner fibre is longer
        half = differential_elongation(z, [1e-3] * 4, [0.5e-3, 0.5e-3, 0.49e-3, 0.5e-3],
                                       xi=0.5)
        self.assertAlmostEqual(half['elongation'][2], 0.5 * el['elongation'][2])

    def test_buckling_check_values(self):
        s = narrow_band_buckling_stress_pa(0.2e-3, 0.05, E_AL, NU_AL)
        expected = 4 * math.pi ** 2 * 70e9 / (12 * (1 - 0.33 ** 2)) * (0.2 / 50) ** 2
        self.assertAlmostEqual(s, expected, delta=1e-6)
        self.assertAlmostEqual(s / 1e6, 4.14, delta=0.01)
        self.assertAlmostEqual(s / i_units_to_stress_pa(1.0, E_AL), 5.9, delta=0.1)  # ~6 I
        self.assertAlmostEqual(narrow_band_buckling_stress_pa(2e-3, 0.05, E_AL, NU_AL) / s,
                               100.0)

    def test_unit_conversions(self):
        self.assertAlmostEqual(i_units_to_stress_pa(1.0, E_AL), 0.7e6)
        self.assertAlmostEqual(i_units_from_wave(0.01, 1.0), (math.pi * 0.01 / 2) ** 2 * 1e5)
        self.assertAlmostEqual(i_units_from_wave(0.01, 1.0), 24.674, places=3)

    def test_narrow_stripe_latent_vs_manifest(self):
        eps = [1e-4 if abs(z - 0.75) < 0.025 else 0.0 for z in Z]   # 10 I-unit stripe
        kw = dict(youngs_modulus_pa=E_AL, poisson_ratio=NU_AL, thickness_m=0.2e-3)
        hi = flatness_from_elongation(Z, eps, mean_tension_pa=5e6, **kw)
        lo = flatness_from_elongation(Z, eps, mean_tension_pa=1e6, **kw)
        for r in (hi, lo):
            loose = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG']
            self.assertEqual(len(loose), 1)
            self.assertAlmostEqual(loose[0]['center_m'], 0.75, delta=1e-9)
            self.assertAlmostEqual(loose[0]['width_m'], 0.05, delta=1e-9)
            # I = 1e5*(1e-4 - 1e-4/30) = 9.667; residual = -0.7 MPa * 9.667
            self.assertAlmostEqual(loose[0]['peak_i_units'], 10 * 29 / 30, places=9)
            self.assertAlmostEqual(loose[0]['residual_stress_at_peak_pa'],
                                   -0.7e6 * 10 * 29 / 30, delta=1e-3)
        self.assertEqual(hi['bands'][0]['state'], 'LATENT_UNDER_TENSION')
        self.assertEqual(hi['status'], 'LATENT_BANDS_UNDER_TENSION')
        self.assertEqual(lo['bands'][0]['state'], 'MANIFEST_BUCKLE')
        self.assertEqual(lo['status'], 'MANIFEST_BUCKLE_BANDS')

    def test_thermal_stripe_chain(self):
        kw = dict(exit_thickness_m=0.2e-3, strip_stiffness_per_width_pa=1e10,
                  bite_half_length_m=0.004, roll_radius_m=0.2, strip_width_m=1.5)
        rig = thermal_stripe_flatness(Z, stripe(0.1e-6), mean_tension_pa=30e6, **kw)
        self.assertAlmostEqual(rig['rigid_transfer_bound_i_units'], 100.0, places=9)
        self.assertLess(rig['compliant_to_rigid_i_unit_ratio'], 1.0)
        small = stripe(0.01e-6)
        hi = thermal_stripe_flatness(Z, small, mean_tension_pa=30e6, **kw)
        lo = thermal_stripe_flatness(Z, small, mean_tension_pa=0.0, **kw)
        for r in (hi, lo):
            loose = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG']
            self.assertEqual(len(loose), 1)
            self.assertAlmostEqual(loose[0]['center_m'], 0.75, delta=DZ)
        self.assertEqual(hi['status'], 'LATENT_BANDS_UNDER_TENSION')
        self.assertEqual(lo['status'], 'MANIFEST_BUCKLE_BANDS')
        # thinner gauge: same stripe, larger I-units
        thick = thermal_stripe_flatness(Z, small, mean_tension_pa=30e6,
                                        **{**kw, 'exit_thickness_m': 2e-3})
        self.assertGreater(hi['flatness']['max_i_units'],
                           5 * thick['flatness']['max_i_units'])
        dumps(hi)


class TestTensionFeedback(unittest.TestCase):
    # worked-example geometry: R = 0.2 m, 50 mm stripe on both rolls, 1.5 m strip, 30 MPa
    THIN = dict(exit_thickness_m=0.21e-3, strip_stiffness_per_width_pa=1.1e10,
                bite_half_length_m=4.87e-3, roll_radius_m=0.2, strip_width_m=1.5,
                mean_tension_pa=30e6)

    def test_feedback_off_reproduces_previous_numbers(self):
        r = thermal_stripe_flatness(Z, stripe(0.5e-6), **self.THIN)
        same = thermal_stripe_flatness(Z, stripe(0.5e-6), **self.THIN,
                                       exit_tension_force_sensitivity_per_width_m=None)
        self.assertEqual(r, same)
        self.assertFalse(r['tension_feedback_applied'])
        self.assertEqual(r['tension_feedback_stiffness_per_width_pa'], 0.0)
        self.assertEqual(r['effective_strip_stiffness_per_width_pa'], 1.1e10)
        self.assertIsNone(r['feedback_peak_i_units'])
        self.assertEqual(r['compliance_only_peak_i_units'], r['flatness']['max_i_units'])
        # values reported before the feedback was added (pre-change run)
        self.assertAlmostEqual(r['flatness']['max_i_units'], 410.58, delta=0.01)
        self.assertAlmostEqual(r['peak_local_thickness_change_m'], -8.9031e-7, delta=1e-11)
        self.assertEqual(r['status'], 'MANIFEST_BUCKLE_BANDS')
        # composition of the lower-level functions, bit for bit
        tr = transfer_radius_profile(Z, stripe(0.5e-6), bite_half_length_m=4.87e-3,
                                     strip_stiffness_per_width_pa=1.1e10, roll_radius_m=0.2)
        self.assertEqual(tr['local_thickness_change_m'], r['local_thickness_change_m'])
        lb = local_bump_transfer(0.05, 0.002, 5e10)
        self.assertEqual(lb['transfer_factor'], lb['compliance_only_transfer_factor'])

    def test_effective_stiffness_formula(self):
        nx, h, q = 5.9e-3, 0.21e-3, 1.1e10
        r = local_bump_transfer(0.1, 4.87e-3, q, exit_tension_force_sensitivity_per_width_m=nx,
                                exit_thickness_m=h, strip_youngs_modulus_pa=E_AL, xi=0.8)
        q_fb = nx * 70e9 * 0.8 / h
        self.assertAlmostEqual(r['tension_feedback_stiffness_per_width_pa'] / q_fb, 1.0,
                               places=12)
        self.assertAlmostEqual(r['effective_strip_stiffness_per_width_pa'] / (q + q_fb), 1.0,
                               places=12)
        c = roll_line_compliance_m2_n(0.1, 4.87e-3)
        self.assertAlmostEqual(r['transfer_factor'], 1 / (1 + 2 * c * (q + q_fb)), places=14)
        self.assertTrue(r['tension_feedback_applied'])
        self.assertIn('EXIT_TENSION_FEEDBACK_LINEAR', r['flags'])

    def test_gauge_independent_limit(self):
        # tiny Q, large N_x': eps = xi*n*T*dR/h -> n*dR/(2*C*N_x'*E), whatever h and xi
        dr, nx, c = 1e-7, 1.0, roll_line_compliance_m2_n(0.1, 0.003)
        limit = 2 * dr / (2 * c * nx * 70e9)
        for h, xi in ((2e-3, 1.0), (0.2e-3, 1.0), (0.2e-3, 0.5)):
            r = local_bump_transfer(0.1, 0.003, 1.0, exit_tension_force_sensitivity_per_width_m=nx,
                                    exit_thickness_m=h, xi=xi, radius_deviation_m=dr)
            eps = -xi * r['local_thickness_change_m'] / h
            self.assertAlmostEqual(eps / limit, 1.0, delta=2e-3)

    def test_mean_component_keeps_q(self):
        z = [i * 0.005 for i in range(40)]
        r = transfer_radius_profile(z, [1e-7] * 40, bite_half_length_m=0.003,
                                    strip_stiffness_per_width_pa=1e10, roll_radius_m=0.2,
                                    exit_tension_force_sensitivity_per_width_m=5e-3,
                                    exit_thickness_m=0.2e-3)
        t_r = local_bump_transfer(0.2, 0.003, 1e10)['transfer_factor']
        for v in r['local_thickness_change_m']:
            self.assertAlmostEqual(v, -2 * t_r * 1e-7, delta=1e-18)

    def test_worked_example_latent_with_feedback(self):
        r = thermal_stripe_flatness(Z, stripe(0.5e-6), **self.THIN,
                                    exit_tension_force_sensitivity_per_width_m=5.9e-3)
        self.assertTrue(r['tension_feedback_applied'])
        self.assertEqual(r['status'], 'LATENT_BANDS_UNDER_TENSION')
        self.assertEqual(r['compliance_only_status'], 'MANIFEST_BUCKLE_BANDS')
        self.assertNotIn('TENSION_FEEDBACK_SATURATED_BAND_SLACK', r['flags'])
        self.assertNotIn('LONG_WAVELENGTH_BELONGS_TO_CROWN_MODEL', r['flags'])   # 0.47 < 0.75
        self.assertAlmostEqual(r['transfer']['long_wavelength_energy_fraction'], 0.47,
                               delta=0.01)
        self.assertLess(r['feedback_peak_i_units'], 0.1 * r['compliance_only_peak_i_units'])
        self.assertLess(r['compliance_only_peak_i_units'], r['rigid_transfer_bound_i_units'])
        self.assertEqual(r['feedback_peak_i_units'], r['linear_feedback_peak_i_units'])
        loose = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG']
        self.assertEqual(len(loose), 1)
        self.assertFalse(loose[0]['saturated'])
        self.assertAlmostEqual(loose[0]['center_m'], 0.75, delta=DZ)
        dumps(r)

    def test_large_stripe_saturates_and_is_manifest(self):
        r = thermal_stripe_flatness(Z, stripe(3e-6), **self.THIN,
                                    exit_tension_force_sensitivity_per_width_m=5.9e-3)
        self.assertEqual(r['status'], 'MANIFEST_BUCKLE_BANDS')
        self.assertIn('TENSION_FEEDBACK_SATURATED_BAND_SLACK', r['flags'])
        self.assertEqual(len(r['saturated_bands']), 1)
        s = r['saturated_bands'][0]
        # |dh| = (n*dR - 2*C*dP_max)/(1 + 2*C*Q) with lam = 2*b = 0.1 m
        c = roll_line_compliance_m2_n(0.1, 4.87e-3)
        s_cr = narrow_band_buckling_stress_pa(0.21e-3, 0.05)
        dp = 5.9e-3 * (30e6 + s_cr)
        self.assertAlmostEqual(s['capped_force_increase_per_width_n_m'], dp, delta=1e-6)
        self.assertAlmostEqual(-s['saturated_peak_thickness_change_m'],
                               (2 * 3e-6 - 2 * c * dp) / (1 + 2 * c * 1.1e10), delta=1e-15)
        loose = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG'][0]
        self.assertTrue(loose['saturated'])
        self.assertEqual(loose['state'], 'MANIFEST_BUCKLE')
        self.assertGreater(loose['peak_i_units'], loose['linear_feedback_peak_i_units'])
        self.assertLess(loose['peak_i_units'], r['compliance_only_peak_i_units'])
        dumps(r)

    def test_monotonic_in_sensitivity(self):
        peaks = [thermal_stripe_flatness(Z, stripe(0.2e-6), **self.THIN,
                                         exit_tension_force_sensitivity_per_width_m=nx)
                 ['feedback_peak_i_units'] for nx in (1e-4, 1e-3, 5.9e-3, 2e-2)]
        self.assertTrue(all(a > b for a, b in zip(peaks, peaks[1:])))
        ts = [local_bump_transfer(0.1, 0.003, 1e10, exit_tension_force_sensitivity_per_width_m=nx,
                                  exit_thickness_m=0.6e-3)['transfer_factor']
              for nx in (1e-4, 1e-3, 1e-2)]
        self.assertTrue(all(a > b for a, b in zip(ts, ts[1:])))

    def test_feedback_validation(self):
        with self.assertRaises(ValueError):
            local_bump_transfer(0.1, 0.003, 1e10, exit_tension_force_sensitivity_per_width_m=1e-3)
        with self.assertRaises(ValueError):
            local_bump_transfer(0.1, 0.003, 1e10, exit_tension_force_sensitivity_per_width_m=-1e-3,
                                exit_thickness_m=1e-3)
        with self.assertRaises(ValueError):
            local_bump_transfer(0.1, 0.003, 1e10, exit_tension_force_sensitivity_per_width_m=True,
                                exit_thickness_m=1e-3)
        with self.assertRaises(ValueError):
            transfer_radius_profile(Z[:20], [0.0] * 20, bite_half_length_m=0.003,
                                    strip_stiffness_per_width_pa=1e10, roll_radius_m=0.2,
                                    exit_tension_force_sensitivity_per_width_m=1e-3,
                                    exit_thickness_m=1e-3, xi=0.0)


class TestCoilRidge(unittest.TestCase):
    ARGS = dict(inner_radius_m=0.305, outer_radius_m=0.9, yield_stress_pa=200e6,
                winding_tension_pa=30e6, youngs_modulus_pa=E_AL)

    def test_critical_height_formula(self):
        r = coil_ridge_buildup(1e-6, 0.21e-3, **self.ARGS)
        expected = 0.21e-3 * 0.9 * 170e6 / (70e9 * 0.5 * (0.9 - 0.305))
        self.assertAlmostEqual(r['critical_ridge_height_at_outer_radius_m'], expected,
                               delta=1e-18)
        self.assertAlmostEqual(r['wraps_at_outer_radius'], 0.595 / 0.21e-3)

    def test_critical_height_sits_at_yield(self):
        rc = coil_ridge_buildup(1e-6, 0.21e-3, **self.ARGS)[
            'critical_ridge_height_at_outer_radius_m']
        r = coil_ridge_buildup(rc, 0.21e-3, **self.ARGS)
        self.assertAlmostEqual(r['hoop_strain_at_outer_radius'], r['yield_margin_strain'],
                               delta=1e-15)
        bigger = coil_ridge_buildup(rc * 1.001, 0.21e-3, **self.ARGS)
        self.assertEqual(bigger['status'], 'RIDGE_YIELDS_STRIP')
        self.assertAlmostEqual(bigger['yield_onset_radius_m'], 0.9, delta=2e-3)
        self.assertLess(bigger['affected_length_fraction'], 0.01)
        self.assertEqual(coil_ridge_buildup(rc * 0.999, 0.21e-3, **self.ARGS)['status'],
                         'ELASTIC_BUILD_UP')

    def test_onset_radius_and_fraction(self):
        for ridge in (0.0, 1e-6, 2e-6, 5e-6, 20e-6, 1e-4):
            r = coil_ridge_buildup(ridge, 0.21e-3, **self.ARGS)
            self.assertGreaterEqual(r['affected_length_fraction'], 0.0)
            self.assertLessEqual(r['affected_length_fraction'], 1.0)
            if r['yield_onset_radius_m'] is not None:
                ron = r['yield_onset_radius_m']
                strain = 0.5 * ridge * (ron - 0.305) / 0.21e-3 / ron
                self.assertAlmostEqual(strain, r['yield_margin_strain'], delta=1e-14)
                frac = (0.81 - ron ** 2) / (0.81 - 0.305 ** 2)
                self.assertAlmostEqual(r['affected_length_fraction'], frac)

    def test_thin_gauge_scaling(self):
        a = coil_ridge_buildup(1e-6, 2e-3, **self.ARGS)
        b = coil_ridge_buildup(1e-6, 0.2e-3, **self.ARGS)
        self.assertAlmostEqual(b['critical_ridge_height_at_outer_radius_m']
                               / a['critical_ridge_height_at_outer_radius_m'], 0.1)
        with self.assertRaises(ValueError):
            coil_ridge_buildup(1e-6, 2e-3, **{**self.ARGS, 'winding_tension_pa': 200e6})


class TestTroughs(unittest.TestCase):
    def test_check_values(self):
        lam = tension_wrinkle_wavelength_m(0.2e-3, 2.0, 30e6, E_AL, NU_AL)
        g = 30e6 / 70e9
        self.assertAlmostEqual(lam, math.sqrt(2 * math.pi * 2 * 0.2e-3)
                               / (3 * (1 - 0.33 ** 2) * g) ** 0.25, places=12)
        self.assertAlmostEqual(lam, 0.2725, delta=1e-4)
        tr = trough_critical_lateral_stress_pa(0.2e-3, 2.0, 30e6, E_AL, NU_AL)
        self.assertAlmostEqual(tr / 1e6, -0.278, delta=0.001)
        wr = roller_wrinkle_critical_lateral_stress_pa(0.2e-3, 0.1, E_AL, NU_AL)
        self.assertAlmostEqual(wr / 1e6, -86.0, delta=0.5)
        a = tension_wrinkle_amplitude_m(0.2e-3, 2.0, 30e6, E_AL, NU_AL)
        self.assertAlmostEqual(a, math.sqrt(0.33 * 2 * 0.2e-3)
                               * (16 * g / (3 * math.pi ** 2 * (1 - 0.33 ** 2))) ** 0.25)
        # ratio identity (a/(pi*R))*sqrt(E/sigma_x)
        self.assertAlmostEqual(wr / tr, 2.0 / (math.pi * 0.1) * math.sqrt(70e9 / 30e6))

    def test_short_span_large_roller_wrinkle_first(self):
        # trough: -(pi*1e-4/0.05)*sqrt(70e9*30e6/(3*0.8911)) = -5.57 MPa;
        # roller: -70e9*1e-4/(1.0*sqrt(3*0.8911)) = -4.28 MPa -> wrinkle before troughs
        r = tension_trough_screen(1e-4, 0.05, 30e6, 0.04, roller_radius_m=1.0,
                                  lateral_compressive_stress_pa=4.5e6)
        self.assertAlmostEqual(r['trough_critical_lateral_stress_pa'] / 1e6, -5.57, delta=0.01)
        self.assertAlmostEqual(r['roller_wrinkle_critical_lateral_stress_pa'] / 1e6, -4.28,
                               delta=0.01)
        self.assertEqual(r['status'], 'ROLLER_WRINKLE_EXPECTED')
        self.assertIn('ROLLER_WRINKLE_THRESHOLD_BELOW_TROUGH_THRESHOLD_SHORT_SPAN', r['flags'])
        low = tension_trough_screen(1e-4, 0.05, 30e6, 0.04, roller_radius_m=1.0,
                                    lateral_compressive_stress_pa=1e6)
        self.assertEqual(low['status'], 'BELOW_TROUGH_THRESHOLD')
        self.assertIn('ROLLER_WRINKLE_THRESHOLD_BELOW_TROUGH_THRESHOLD_SHORT_SPAN', low['flags'])
        dumps(r)

    def test_scalings(self):
        args = (2.0, 30e6, E_AL, NU_AL)
        self.assertAlmostEqual(trough_critical_lateral_stress_pa(0.4e-3, *args)
                               / trough_critical_lateral_stress_pa(0.2e-3, *args), 2.0)
        self.assertAlmostEqual(roller_wrinkle_critical_lateral_stress_pa(0.4e-3, 0.1)
                               / roller_wrinkle_critical_lateral_stress_pa(0.2e-3, 0.1), 2.0)
        self.assertAlmostEqual(tension_wrinkle_wavelength_m(0.4e-3, *args)
                               / tension_wrinkle_wavelength_m(0.2e-3, *args), math.sqrt(2))

    def test_screen_statuses(self):
        base = dict(thickness_m=0.2e-3, span_length_m=2.0, tension_stress_pa=30e6,
                    strip_width_m=1.5)
        r = tension_trough_screen(**base)
        self.assertEqual(r['status'], 'LATERAL_STRESS_UNKNOWN_THRESHOLDS_ONLY')
        self.assertAlmostEqual(r['expected_trough_count_across_width'],
                               1.5 / r['wrinkle_wavelength_m'])
        self.assertEqual(tension_trough_screen(**base, lateral_compressive_stress_pa=0.1e6)
                         ['status'], 'BELOW_TROUGH_THRESHOLD')
        self.assertEqual(tension_trough_screen(**base, roller_radius_m=0.1,
                                               lateral_compressive_stress_pa=1e6)['status'],
                         'TROUGHS_EXPECTED')
        self.assertEqual(tension_trough_screen(**base, roller_radius_m=0.1,
                                               lateral_compressive_stress_pa=100e6)['status'],
                         'ROLLER_WRINKLE_EXPECTED')
        long_span = tension_trough_screen(**base, roller_radius_m=0.1,
                                          lateral_compressive_stress_pa=1e6)
        self.assertNotIn('ROLLER_WRINKLE_THRESHOLD_BELOW_TROUGH_THRESHOLD_SHORT_SPAN',
                         long_span['flags'])
        self.assertGreater(long_span['wrinkle_to_trough_threshold_ratio'], 1.0)
        ok = tension_trough_screen(**base, observed_spacing_m=0.3)
        self.assertTrue(ok['observed_spacing_consistent'])
        self.assertFalse(tension_trough_screen(**base, observed_spacing_m=0.05)
                         ['observed_spacing_consistent'])
        dumps(ok)


class TestHelpers(unittest.TestCase):
    def test_two_tone(self):
        r = two_tone_positions_m([1.2, 1.6, 1.0], 0.75, 1.5)
        # previous widths 1.2 and 1.0 (narrower than 1.5) -> edges 0.75 -/+ 0.6 and 0.5
        expected = [0.15, 0.25, 1.25, 1.35]
        self.assertEqual(len(r['band_positions_m']), 4)
        for a, b in zip(r['band_positions_m'], expected):
            self.assertAlmostEqual(a, b)
        self.assertEqual(r['status'], 'TWO_TONE_EDGES_PREDICTED')
        self.assertEqual(two_tone_positions_m([1.6], 0.75, 1.5)['status'],
                         'NO_NARROWER_PREVIOUS_WIDTHS')

    def test_grinding_pitch(self):
        self.assertAlmostEqual(grinding_feed_pitch_m(0.01, 0.5), 0.02)

    def test_spacing_exact_multiples(self):
        sp = spacing_analysis([0.104, 0.0, 0.026, 0.078])
        self.assertEqual(sp['positions_m'], [0.0, 0.026, 0.078, 0.104])
        for a, b in zip(sp['gaps_m'], [0.026, 0.052, 0.026]):
            self.assertAlmostEqual(a, b)
        self.assertAlmostEqual(sp['mean_gap_m'], 0.104 / 3)
        m = match_spacing(sp['gaps_m'], 0.026)
        self.assertEqual(m['status'], 'ALL_GAPS_MATCH')
        self.assertEqual(m['multiples'], [1, 2, 1])
        reg = spacing_analysis([0.1 * i for i in range(6)])
        self.assertTrue(reg['regular'])
        self.assertAlmostEqual(reg['coefficient_of_variation'], 0.0, places=12)

    def test_spacing_irregular(self):
        sp = spacing_analysis([0.0, 0.03, 0.11, 0.13, 0.31])
        self.assertEqual(sp['status'], 'IRREGULAR_SPACING')
        gaps = [0.03, 0.08, 0.02, 0.18]
        mean = sum(gaps) / 4
        cv = math.sqrt(sum((g - mean) ** 2 for g in gaps) / 4) / mean
        self.assertAlmostEqual(sp['coefficient_of_variation'], cv)
        m = match_spacing(sp['gaps_m'], 0.026)
        # gaps/pitch = 1.154, 3.077, 0.769, 6.923 -> deviations 0.154, 0.077, 0.231, 0.077
        self.assertEqual(m['status'], 'SOME_GAPS_MATCH')
        self.assertEqual([g['matched'] for g in m['gaps']], [False, True, False, True])
        self.assertEqual(m['multiples'], [3, 7])
        self.assertEqual(match_spacing([0.5], 0.026)['gaps'][0]['nearest_multiple'], 8)

    def test_match_positions(self):
        r = match_positions([0.2, 0.5, 0.9], [0.21, 0.7], 0.02)
        self.assertEqual(r['status'], 'SOME_OBSERVED_POSITIONS_MATCHED')
        self.assertEqual(r['unmatched_positions_m'], [0.7])
        self.assertEqual(r['unexplained_predicted_indices'], [1, 2])
        self.assertEqual(match_positions([], [0.1], 0.01)['status'],
                         'NO_OBSERVED_POSITIONS_MATCHED')


class TestValidationAndJson(unittest.TestCase):
    def test_validation_errors(self):
        bad = [
            lambda: roll_line_compliance_m2_n(True, 0.002),
            lambda: roll_line_compliance_m2_n(float('nan'), 0.002),
            lambda: local_bump_transfer(0.05, 0.002, -1.0),
            lambda: local_bump_transfer(0.05, 0.002, 1e10, n_rolls=3),
            lambda: local_bump_transfer(0.05, 0.002, 1e10, n_rolls=True),
            lambda: transfer_radius_profile([0, 0.1, 0.25, 0.3], [0.0] * 4,
                                            bite_half_length_m=0.003,
                                            strip_stiffness_per_width_pa=1e10,
                                            roll_radius_m=0.2),
            lambda: transfer_radius_profile([0, 0.1, 0.2, 0.3], [0.0] * 3,
                                            bite_half_length_m=0.003,
                                            strip_stiffness_per_width_pa=1e10,
                                            roll_radius_m=0.2),
            lambda: crown_heredity(0.0, 0.0, 1e-3, 2e-3, 0.5),
            lambda: crown_heredity(0.0, 0.0, 2e-3, 1e-3, 1.5),
            lambda: shohet_townsend_window(0.2e-3, 1.5, beta='2'),
            lambda: differential_elongation([0, 0.1], [1e-3, 1e-3], [0.0, 1e-3]),
            lambda: differential_elongation([0.1, 0.0], [1e-3] * 2, [1e-3] * 2),
            lambda: flatness_from_elongation([0, 0.1], [0, 0], youngs_modulus_pa=E_AL,
                                             poisson_ratio=0.6, thickness_m=1e-3,
                                             mean_tension_pa=1e6),
            lambda: flatness_from_elongation([0, 0.1], [0, 0], youngs_modulus_pa=E_AL,
                                             poisson_ratio=0.3, thickness_m=1e-3,
                                             mean_tension_pa=-1.0),
            lambda: coil_ridge_buildup(1e-6, 1e-3, 0.5, 0.4, 200e6, 30e6),
            lambda: tension_trough_screen(0.2e-3, 2.0, 0.0, 1.5),
            lambda: tension_trough_screen(0.2e-3, 2.0, 30e6, 1.5,
                                          lateral_compressive_stress_pa=-1.0),
            lambda: spacing_analysis([0.1]),
            lambda: spacing_analysis([0.1, 0.1]),
            lambda: match_spacing([0.1], 0.0),
            lambda: grinding_feed_pitch_m(0.01, 0),
            lambda: two_tone_positions_m('1.2', 0.75, 1.5),
            lambda: thermal_stripe_flatness(Z, stripe(1e-7), exit_thickness_m=0.2e-3,
                                            strip_stiffness_per_width_pa=1e10,
                                            bite_half_length_m=0.004, roll_radius_m=0.2,
                                            strip_width_m=0.01, mean_tension_pa=30e6),
        ]
        for i, f in enumerate(bad):
            with self.subTest(i=i):
                with self.assertRaises(ValueError):
                    f()

    def test_json_serialisable(self):
        results = [
            local_bump_transfer(0.05, 0.002, 1e10, roll_radius_m=0.2, radius_deviation_m=1e-7),
            transfer_radius_profile(Z[:100], stripe(1e-7)[:100], bite_half_length_m=0.003,
                                    strip_stiffness_per_width_pa=1e10, roll_radius_m=0.2),
            crown_heredity(1e-5, 2e-5, 1e-3, 0.5e-3, 0.4),
            shohet_townsend_window(1e-3, 1.5), classify_crown_change(1e-5, 1e-3, 0, 0.5e-3, 1.5),
            differential_elongation([0, 0.1], [1e-3] * 2, [0.5e-3, 0.49e-3]),
            flatness_from_elongation(Z, [0.0] * len(Z), youngs_modulus_pa=E_AL,
                                     poisson_ratio=NU_AL, thickness_m=1e-3,
                                     mean_tension_pa=1e7, yield_stress_pa=1e8),
            coil_ridge_buildup(5e-6, 0.21e-3, 0.305, 0.9, 200e6, 30e6),
            coil_ridge_buildup(0.0, 0.21e-3, 0.305, 0.9, 200e6, 30e6),
            tension_trough_screen(0.21e-3, 4.0, 30e6, 1.5, roller_radius_m=0.15,
                                  lateral_compressive_stress_pa=1e6, observed_spacing_m=0.4),
            two_tone_positions_m([1.2], 0.75, 1.5), spacing_analysis([0.0, 0.026]),
            match_spacing([0.026], 0.026), match_positions([0.1], [0.1], 0.0)]
        for r in results:
            dumps(r)
            self.assertIn('status', r)
            self.assertIsInstance(r['flags'], list)
            self.assertIsInstance(r['limitations'], list)
            self.assertIn('threshold_basis', r)
            self.assertIn('sources', r)


if __name__ == '__main__':
    unittest.main()
