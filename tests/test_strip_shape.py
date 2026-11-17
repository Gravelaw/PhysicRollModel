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
        # 0.6 mm gauge of the worked example, 6 um stripe (3 um: test_three_micron_stripe_states)
        mid = dict(self.THIN, exit_thickness_m=0.6e-3, strip_stiffness_per_width_pa=8e9,
                   bite_half_length_m=4.47e-3)
        r = thermal_stripe_flatness(Z, stripe(6e-6), **mid,
                                    exit_tension_force_sensitivity_per_width_m=3.9e-3)
        self.assertEqual(r['status'], 'MANIFEST_BUCKLE_BANDS')
        self.assertIn('TENSION_FEEDBACK_SATURATED_BAND_SLACK', r['flags'])
        self.assertEqual(len(r['saturated_bands']), 1)
        s = r['saturated_bands'][0]
        # cap uses sigma_cr of the Rayleigh effective width b;
        # |dh| = (n*dR - 2*C*dP_max)/(1 + 2*C*Q) with lam = 2*b
        self.assertAlmostEqual(s['band_buckling_stress_pa'],
                               narrow_band_buckling_stress_pa(0.6e-3,
                                                              s['effective_buckling_width_m']))
        dp = 3.9e-3 * (30e6 + s['band_buckling_stress_pa'])
        self.assertAlmostEqual(s['capped_force_increase_per_width_n_m'], dp, delta=1e-6)
        lam = min(max(2 * s['effective_buckling_width_m'], 4 * 4.47e-3), 0.2)
        self.assertAlmostEqual(s['dominant_wavelength_m'], lam, delta=1e-12)
        c = roll_line_compliance_m2_n(lam, 4.47e-3)
        expected = max((2 * 6e-6 - 2 * c * dp) / (1 + 2 * c * 8e9),
                       -s['linear_feedback_peak_thickness_change_m'])
        self.assertAlmostEqual(-s['saturated_peak_thickness_change_m'], expected, delta=1e-15)
        self.assertGreater(s['scale_factor'], 1.5)
        loose = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG'][0]
        self.assertTrue(loose['saturated'])
        self.assertEqual(loose['state'], 'MANIFEST_BUCKLE')
        self.assertEqual(loose['state_after_tension_release'], 'MANIFEST_AFTER_TENSION_RELEASE')
        self.assertGreater(loose['peak_i_units'], loose['linear_feedback_peak_i_units'])
        self.assertLess(loose['peak_i_units'], r['compliance_only_peak_i_units'])
        dumps(r)

    def test_three_micron_stripe_states(self):
        # Rayleigh rule: 3 um is MANIFEST in the mill at 0.6 mm (U ~ 38, b ~ 0.32 m after
        # saturation) and 0.21 mm (U ~ 1360, b ~ 0.57 m), LATENT at 2.0 mm (U ~ 0.58,
        # b ~ 0.15 m); saturation applies at both thin gauges. Released: whole-width mode.
        gauges = {2.0e-3: (1e9, 7.07e-3, 2.3e-3), 0.6e-3: (8e9, 4.47e-3, 3.9e-3),
                  0.21e-3: (1.1e10, 4.87e-3, 5.9e-3)}
        out = {}
        for h, (q, a, nx) in gauges.items():
            r = thermal_stripe_flatness(Z, stripe(3e-6), exit_thickness_m=h,
                                        strip_stiffness_per_width_pa=q, bite_half_length_m=a,
                                        roll_radius_m=0.2, strip_width_m=1.5,
                                        mean_tension_pa=30e6,
                                        exit_tension_force_sensitivity_per_width_m=nx)
            loose = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG'][0]
            self.assertEqual(loose['band_buckling_width_basis'], 'RAYLEIGH_QUOTIENT_SINE_MODE')
            self.assertGreater(loose['effective_buckling_width_m'], 0.1)
            self.assertLessEqual(loose['effective_buckling_start_m'], loose['end_m'])
            self.assertAlmostEqual(loose['released_buckling_width_m'], 1.5, places=6)
            self.assertAlmostEqual(loose['band_buckling_stress_pa'],
                                   narrow_band_buckling_stress_pa(
                                       h, loose['effective_buckling_width_m']))
            self.assertAlmostEqual(loose['buckling_utilisation'],
                                   loose['effective_buckling_mean_compression_pa']
                                   / loose['band_buckling_stress_pa'])
            self.assertAlmostEqual(loose['buckling_margin_pa'],
                                   loose['band_buckling_stress_pa']
                                   - loose['effective_buckling_mean_compression_pa'])
            out[h] = (r, loose)
        r, loose = out[2.0e-3]
        self.assertEqual(loose['state'], 'LATENT_UNDER_TENSION')
        self.assertGreater(loose['buckling_utilisation'], 0.4)
        self.assertLess(loose['buckling_utilisation'], 0.8)
        self.assertFalse(loose['saturated'])
        self.assertEqual(r['released_status'], 'MANIFEST_AFTER_RELEASE_BANDS')
        for h in (0.6e-3, 0.21e-3):
            r, loose = out[h]
            self.assertEqual(loose['state'], 'MANIFEST_BUCKLE')
            self.assertTrue(loose['saturated'])
            self.assertGreater(loose['buckling_utilisation'], 3.0)
            self.assertIn('TENSION_FEEDBACK_SATURATED_BAND_SLACK', r['flags'])
            self.assertEqual(loose['state_after_tension_release'],
                             'MANIFEST_AFTER_TENSION_RELEASE')

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


def gaussian_stripe(height_m, fwhm_m=0.2):
    return [height_m * math.exp(-4 * math.log(2) * (z - 0.75) ** 2 / fwhm_m ** 2) for z in Z]


# feedback settings: 0.21 mm as in the worked example; 1.4 mm chosen for this test
GAUGES = {1.4e-3: dict(strip_stiffness_per_width_pa=3e9, bite_half_length_m=6.0e-3,
                       exit_tension_force_sensitivity_per_width_m=3.0e-3),
          0.21e-3: dict(strip_stiffness_per_width_pa=1.1e10, bite_half_length_m=4.87e-3,
                        exit_tension_force_sensitivity_per_width_m=5.9e-3)}


def _run(shape, height, gauge):
    return thermal_stripe_flatness(Z, shape(height), exit_thickness_m=gauge, roll_radius_m=0.2,
                                   strip_width_m=1.5, mean_tension_pa=30e6, **GAUGES[gauge])


def _onset(shape, gauge, key, value):
    lo, hi = 1e-8, 3e-5          # geometric bisection on the stripe height [m]
    for _ in range(14):
        mid = math.sqrt(lo * hi)
        if _run(shape, mid, gauge)[key] == value:
            hi = mid
        else:
            lo = mid
    return hi


class TestNetCompressionCriterion(unittest.TestCase):
    def test_onset_gauge_trends(self):
        # Rayleigh rule (feedback on, 30 MPa). Top-hat: in-mill onset 2.97 -> 1.55 um,
        # released 0.227 -> 0.035 um (1.4 -> 0.21 mm). Gaussian: in-mill 1.72 -> 1.88 um
        # (about gauge-independent: the residual must first exceed the tension); released
        # onsets sit at the 2 I-unit reporting threshold at both gauges (whole-width mode).
        top = {g: (_onset(stripe, g, 'status', 'MANIFEST_BUCKLE_BANDS'),
                   _onset(stripe, g, 'released_status', 'MANIFEST_AFTER_RELEASE_BANDS'))
               for g in GAUGES}
        self.assertLess(top[0.21e-3][0], top[1.4e-3][0])
        self.assertLess(top[0.21e-3][1], top[1.4e-3][1])
        fall_mill = top[1.4e-3][0] / top[0.21e-3][0]
        fall_rel = top[1.4e-3][1] / top[0.21e-3][1]
        self.assertGreater(fall_rel, 1.5 * fall_mill)
        for g in GAUGES:
            self.assertLess(top[g][1], top[g][0])
            mill, rel = (_onset(gaussian_stripe, g, key, val) for key, val in
                         (('status', 'MANIFEST_BUCKLE_BANDS'),
                          ('released_status', 'MANIFEST_AFTER_RELEASE_BANDS')))
            self.assertLess(rel, mill)
            r = _run(gaussian_stripe, rel, g)
            self.assertLess(r['flatness']['max_i_units'], 2.5)        # threshold-limited
            self.assertGreater(mill, 1.5e-6)
            self.assertLess(mill, 2.1e-6)

    def test_rayleigh_analytic_limits(self):
        k = 4 * math.pi ** 2 * E_AL / (12 * (1 - NU_AL ** 2))
        t = 0.21e-3
        # uniform q0 over the whole strip: U = q0/sigma_cr(W) at b = W
        r = ss._SineModeSearch(Z, [2e6] * len(Z), k * t * t).search(0.7, 0.8, {'r': 0.0})['r']
        self.assertAlmostEqual(r[0] / (2e6 * 1.5 ** 2 / (k * t * t)), 1.0, places=9)
        self.assertAlmostEqual(r[2], 1.5, places=9)
        # uniform zone of width w = 0.1 m in tension: optimum a little wider than w, and
        # more tension outside lowers U (0: U 78.7 at b = W; -1 MPa: 12.7 at b 0.42;
        # -5 MPa: 5.55 at b 0.18; -30 MPa: see below)
        last = None
        for tension in (0.0, -1e6, -5e6, -30e6):
            q = [3e6 if abs(z - 0.75) < 0.05 else tension for z in Z]
            u, x1, b, qw, s_cr = ss._SineModeSearch(Z, q, k * t * t).search(
                0.7, 0.8, {'r': 0.0})['r']
            self.assertAlmostEqual(u, qw / s_cr)
            self.assertAlmostEqual(s_cr, narrow_band_buckling_stress_pa(t, b))
            if last is not None:
                self.assertLess(u, last)
            last = u
            if tension <= -5e6:
                self.assertGreater(b, 0.1)
                self.assertLess(b, 0.2)
                self.assertAlmostEqual(x1 + b / 2, 0.75, delta=1e-3)
        # strong tension outside: q_w is bounded by the sin^2-weighted zone content
        self.assertLess(qw, 3e6)

    def test_released_width_dependence(self):
        # same 50 mm, 1e-4 elongation stripe on a 1.0 m and a 2.0 m strip: the released
        # optimum is the whole-width mode (b = W) and U_rel scales with W (30.6 vs 61.4 at
        # 0.21 mm) - NOT insensitive to the strip width (reported to the coordinator)
        out = {}
        for width in (1.0, 2.0):
            n = int(round(width / DZ))
            zz = [(i + 0.5) * DZ for i in range(n)]
            eps = [1e-4 if abs(v - width / 2) < 0.025 else 0.0 for v in zz]
            r = flatness_from_elongation(zz, eps, youngs_modulus_pa=E_AL, poisson_ratio=NU_AL,
                                         thickness_m=0.21e-3, mean_tension_pa=30e6)
            loose = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG'][0]
            self.assertAlmostEqual(loose['released_buckling_width_m'], width, places=6)
            out[width] = loose['released_buckling_utilisation']
            self.assertEqual(loose['state'], 'LATENT_UNDER_TENSION')
        self.assertAlmostEqual(out[2.0] / out[1.0], 2.0, delta=0.1)

    def test_released_gaussian_and_top_hat(self):
        for shape in (gaussian_stripe, stripe):
            r = _run(shape, 0.5e-6, 0.21e-3)
            loose = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG'][0]
            self.assertEqual(loose['state'], 'LATENT_UNDER_TENSION')
            self.assertEqual(loose['state_after_tension_release'],
                             'MANIFEST_AFTER_TENSION_RELEASE')
            self.assertAlmostEqual(loose['released_buckling_width_m'], 1.5, places=6)
            self.assertGreater(loose['released_buckling_utilisation'], 10.0)

    def test_residual_below_tension_is_latent_at_any_gauge(self):
        eps = [3e-4 if abs(z - 0.75) < 0.05 else 0.0 for z in Z]   # resid ~ -20 MPa < 30 MPa
        for t in (2e-3, 0.6e-3, 0.21e-3, 0.05e-3):
            r = flatness_from_elongation(Z, eps, youngs_modulus_pa=E_AL, poisson_ratio=NU_AL,
                                         thickness_m=t, mean_tension_pa=30e6)
            loose = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG'][0]
            self.assertLess(loose['net_compression_peak_pa'], 0)
            self.assertIsNone(loose['effective_buckling_width_m'])
            self.assertEqual(loose['band_buckling_width_basis'],
                             'REPORTING_CONTOUR_WIDTH_NOT_IN_NET_COMPRESSION')
            self.assertEqual(loose['state'], 'LATENT_UNDER_TENSION')
        # released: same profile, same optimum interval, so U_rel scales as 1/t^2
        thick = flatness_from_elongation(Z, eps, youngs_modulus_pa=E_AL, poisson_ratio=NU_AL,
                                         thickness_m=2e-3, mean_tension_pa=30e6)
        u_thin = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG'][0][
            'released_buckling_utilisation']
        u_thick = [b for b in thick['bands'] if b['sense'] == 'LOOSE_LONG'][0][
            'released_buckling_utilisation']
        self.assertAlmostEqual(u_thin / u_thick, (2e-3 / 0.05e-3) ** 2, delta=1.0)
        self.assertEqual(r['released_status'], 'MANIFEST_AFTER_RELEASE_BANDS')

    def test_rayleigh_utilisation_continuous(self):
        prof = [math.exp(-4 * math.log(2) * (z - 0.75) ** 2 / 0.2 ** 2) for z in Z]
        utils, widths, prev = [], [], None
        for k in range(120):
            amp = 7e-4 * (1 + 0.005 * k)   # 0.5 % steps; net compression 12 .. 46 MPa
            r = flatness_from_elongation(Z, [amp * p for p in prof], youngs_modulus_pa=E_AL,
                                         poisson_ratio=NU_AL, thickness_m=1.4e-3,
                                         mean_tension_pa=30e6, reporting_threshold_i_units=0.0)
            b = [x for x in r['bands'] if x['sense'] == 'LOOSE_LONG'][0]
            u = b['buckling_utilisation']
            if prev is not None:
                self.assertLess(abs(u - prev) / prev, 0.04)
            prev = u
            utils.append(u)
            widths.append(b['effective_buckling_width_m'])
            self.assertGreater(b['released_buckling_utilisation'], u)
        self.assertTrue(all(a < b for a, b in zip(utils, utils[1:])))
        steps = [b / a - 1 for a, b in zip(utils, utils[1:])]
        for s1, s2 in zip(steps, steps[1:]):                 # smooth: no kinks or jumps
            self.assertLess(abs(s2 - s1), 0.003)
        self.assertTrue(utils[0] < 1.0 < utils[-1])          # crosses onset continuously
        self.assertGreater(len({round(w / DZ, 3) for w in widths}), 50)   # not grid-quantised
        # a single-sample spike: the narrowest admissible buckle is two spacings
        eps = [0.0] * len(Z)
        eps[150] = 1e-3
        r = flatness_from_elongation(Z, eps, youngs_modulus_pa=E_AL, poisson_ratio=NU_AL,
                                     thickness_m=0.21e-3, mean_tension_pa=30e6)
        loose = [b for b in r['bands'] if b['sense'] == 'LOOSE_LONG']
        w = loose[0]['effective_buckling_width_m']
        self.assertGreaterEqual(w, 2 * DZ * (1 - 1e-9))
        self.assertLess(w, 10 * DZ)

    def test_keys_and_json(self):
        r = _run(gaussian_stripe, 1e-6, 0.21e-3)
        for k in ('released_status', 'manifest_after_release_band_count', 'status',
                  'compliance_only_released_status'):
            self.assertIn(k, r)
        self.assertIn('released_status', r['flatness'])
        for b in r['bands']:
            for k in ('start_m', 'end_m', 'center_m', 'width_m', 'peak_position_m',
                      'peak_i_units', 'sense', 'residual_stress_at_peak_pa',
                      'local_total_stress_pa', 'band_buckling_stress_pa', 'buckling_margin_pa',
                      'state', 'band_buckling_width_basis', 'net_compression_peak_pa',
                      'effective_buckling_width_m', 'released_compression_peak_pa',
                      'released_buckling_width_m', 'released_buckling_stress_pa',
                      'state_after_tension_release', 'saturated',
                      'effective_buckling_mean_compression_pa', 'buckling_utilisation',
                      'effective_buckling_start_m', 'released_buckling_start_m',
                      'released_buckling_mean_compression_pa',
                      'released_buckling_utilisation',
                      'linear_feedback_peak_i_units'):
                self.assertIn(k, b)
            if b['sense'] == 'TIGHT_SHORT':
                self.assertEqual(b['state'], 'LATENT_UNDER_TENSION')
                self.assertEqual(b['state_after_tension_release'], 'FLAT_AFTER_TENSION_RELEASE')
        off = thermal_stripe_flatness(Z, gaussian_stripe(1e-6), exit_thickness_m=0.21e-3,
                                      roll_radius_m=0.2, strip_width_m=1.5,
                                      mean_tension_pa=30e6, strip_stiffness_per_width_pa=1.1e10,
                                      bite_half_length_m=4.87e-3)
        self.assertFalse(off['tension_feedback_applied'])
        self.assertIn('released_status', off)
        dumps(r)
        dumps(off)


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
