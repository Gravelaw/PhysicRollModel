import json
import math
import unittest

from physicroll.bite_tribology import (
    ALUMINIUM_VOLUMETRIC_HEAT_CAPACITY_J_M3K, LITERATURE_FITS, PLACEHOLDER_FLAG,
    FrictionClosure, Lubricant, SurfaceFinish, VoceHardening, friction_at_speed,
    friction_coefficient, friction_speed_curve, inlet_film_thickness,
    kinematic_cst_to_dynamic_viscosity_pa_s, literature_power_law, pass_heating,
    schedule_flow_stress, temperature_viscosity_coefficient_per_k)
from physicroll.materials import PowerHardeningLaw

C0 = 273.15
FOIL_OIL = Lubricant(viscosity_ref_pa_s=2.5e-3, reference_temperature_k=C0 + 40,
                     temperature_viscosity_coefficient_per_k=0.015,
                     pressure_viscosity_coefficient_per_pa=1.2e-8)
FINISH = SurfaceFinish(roll_roughness_rq_m=0.15e-6, strip_roughness_rq_m=0.20e-6)


def kerosene():
    return Lubricant(viscosity_ref_pa_s=kinematic_cst_to_dynamic_viscosity_pa_s(2.2, 800.0),
                     reference_temperature_k=C0 + 40,
                     temperature_viscosity_coefficient_per_k=0.015,
                     pressure_viscosity_coefficient_per_pa=1.2e-8)


def case(**over):
    """0.30 -> 0.21 mm, R' 0.29 m, Y 270 MPa uniaxial, back tension 25 MPa, inlet 50 C."""
    kw = dict(roll_surface_speed_m_s=16.0, strip_entry_speed_m_s=16.0 * 0.7,
              entry_thickness_m=0.30e-3, exit_thickness_m=0.21e-3, contact_radius_m=0.29,
              plane_strain_yield_pa=2 * 270e6 / math.sqrt(3), back_tension_pa=25e6,
              inlet_temperature_k=C0 + 50)
    kw.update(over)
    return kw


class ViscosityTests(unittest.TestCase):
    def test_beta_from_kerosene_data_points(self):
        # ln(3.0/1.4)/50 = 0.01524; ln(1.4/0.7)/60 = 0.01155  -> spec 0.015 and 0.012
        b1 = temperature_viscosity_coefficient_per_k(3.0, C0 + 20, 1.4, C0 + 70)
        b2 = temperature_viscosity_coefficient_per_k(1.4, C0 + 70, 0.7, C0 + 130)
        self.assertAlmostEqual(b1, math.log(3.0 / 1.4) / 50, places=12)
        self.assertAlmostEqual(b1, 0.015, delta=0.0005)
        self.assertAlmostEqual(b2, 0.012, delta=0.0005)

    def test_kinematic_conversion(self):
        self.assertAlmostEqual(kinematic_cst_to_dynamic_viscosity_pa_s(2.2, 800.0), 1.76e-3,
                               places=12)

    def test_temperature_and_barus_laws(self):
        self.assertAlmostEqual(FOIL_OIL.dynamic_viscosity_pa_s(C0 + 40), 2.5e-3, places=15)
        self.assertAlmostEqual(FOIL_OIL.dynamic_viscosity_pa_s(C0 + 50),
                               2.5e-3 * math.exp(-0.15), places=15)
        self.assertAlmostEqual(FOIL_OIL.dynamic_viscosity_pa_s(C0 + 40, 100e6),
                               2.5e-3 * math.exp(1.2), places=12)


class FilmTests(unittest.TestCase):
    def test_spec_check_65nm_lambda_022(self):
        # Derivation: theta0 = sqrt(25e-6/0.135) = 0.013608; U = (5 + 2.5)/2 = 3.75 m/s
        # (zero slip: 5*25/50 = 2.5 m/s); 1 - exp(-1.2e-8*130e6) = 0.78989;
        # h = 6*2.5e-3*1.2e-8*3.75/(0.013608*0.78989) = 62.80 nm; Lambda = 0.2093.
        # The spec/paper quotes ~65 nm and 0.22 (= 66 nm): ~4-5 % above this derivation.
        r = inlet_film_thickness(
            FOIL_OIL, roll_surface_speed_m_s=5.0, strip_entry_speed_m_s=2.5,
            entry_thickness_m=50e-6, exit_thickness_m=25e-6, contact_radius_m=0.135,
            plane_strain_yield_pa=130e6, back_tension_pa=0.0, inlet_temperature_k=C0 + 40)
        expected = 6 * 2.5e-3 * 1.2e-8 * 3.75 / (math.sqrt(25e-6 / 0.135)
                                                 * (1 - math.exp(-1.56)))
        self.assertAlmostEqual(expected, 62.80e-9, delta=0.01e-9)
        self.assertAlmostEqual(r['film_thickness_m'], expected, delta=1e-13)
        self.assertAlmostEqual(r['inlet_angle_rad'], 0.013608, delta=1e-6)
        self.assertAlmostEqual(r['film_thickness_m'] / 0.3e-6, 0.2093, delta=0.0005)
        # Within rounding of the quoted ~65 nm only at the 5 % level (reported, not bent).
        self.assertLess(abs(r['film_thickness_m'] - 65e-9) / 65e-9, 0.05)

    def test_linear_in_speed_and_viscosity(self):
        base = inlet_film_thickness(FOIL_OIL, **case())['film_thickness_m']
        fast = inlet_film_thickness(FOIL_OIL, **case(roll_surface_speed_m_s=32.0,
                                                     strip_entry_speed_m_s=22.4))
        self.assertAlmostEqual(fast['film_thickness_m'] / base, 2.0, places=12)
        thick = Lubricant(5e-3, C0 + 40, 0.015, 1.2e-8)
        self.assertAlmostEqual(inlet_film_thickness(thick, **case())['film_thickness_m'] / base,
                               2.0, places=12)

    def test_case_film_closed_form_and_entry_pressure(self):
        r = inlet_film_thickness(kerosene(), **case())
        eta0 = 1.76e-3 * math.exp(-0.15)
        theta = math.sqrt(0.09e-3 / 0.29)
        p = 2 * 270e6 / math.sqrt(3) - 25e6
        h = 6 * eta0 * 1.2e-8 * 13.6 / (theta * (1 - math.exp(-1.2e-8 * p)))
        self.assertAlmostEqual(r['film_thickness_m'], h, delta=1e-15)
        self.assertAlmostEqual(r['entry_pressure_pa'], p, delta=1e-3)
        no_back = inlet_film_thickness(kerosene(), **case(back_tension_pa=0.0))
        self.assertAlmostEqual(no_back['film_thickness_m'],
                               r['film_thickness_yield_only_exponent_m'], delta=1e-18)
        self.assertGreater(r['film_thickness_m'], no_back['film_thickness_m'])
        self.assertIn('EXPONENT_USES_ENTRY_PRESSURE_SOURCES_DISAGREE', r['flags'])

    def test_thermal_factor_reported_and_optional(self):
        off = inlet_film_thickness(kerosene(), **case())
        on = inlet_film_thickness(kerosene(), **case(), thermal_correction=True)
        eta0 = 1.76e-3 * math.exp(-0.15)
        load = eta0 * 0.015 * 13.6 ** 2 / 0.13
        phi = 3.94 / (3.94 + load ** 0.62)
        self.assertAlmostEqual(off['thermal_loading_parameter'], load, places=12)
        self.assertAlmostEqual(off['thermal_reduction_factor'], phi, places=12)
        self.assertGreater(phi, 0.9)
        self.assertFalse(off['thermal_correction_applied'])
        self.assertAlmostEqual(off['film_thickness_m'], off['isothermal_film_thickness_m'])
        self.assertAlmostEqual(on['film_thickness_m'], phi * off['film_thickness_m'],
                               delta=1e-18)
        self.assertIn('OIL_CONDUCTIVITY_DEFAULT_FROM_MEMORY', off['flags'])


class FrictionTests(unittest.TestCase):
    def test_closure_limits_and_slope(self):
        cl = FrictionClosure()
        self.assertAlmostEqual(friction_coefficient(0.0, cl)['friction_coefficient'], 0.09)
        self.assertAlmostEqual(friction_coefficient(50.0, cl)['friction_coefficient'], 0.008,
                               places=12)
        r = friction_coefficient(1.0, cl)
        self.assertAlmostEqual(r['friction_coefficient'], 0.008 + 0.082 * math.exp(-1))
        d = 1e-6
        fd = (friction_coefficient(1 + d)['friction_coefficient']
              - friction_coefficient(1 - d)['friction_coefficient']) / (2 * d)
        self.assertAlmostEqual(r['dmu_dlambda'], fd, places=7)
        self.assertEqual(friction_coefficient(0.5)['regime'], 'MIXED_SUBSTANTIAL_CONTACT')
        self.assertEqual(friction_coefficient(2.0)['regime'], 'MIXED_FIRST_CONTACT')
        self.assertEqual(friction_coefficient(4.0)['regime'], 'HYDRODYNAMIC')
        self.assertIn(PLACEHOLDER_FLAG, r['flags'])

    def test_regime_labels_and_window(self):
        """SPEC17 BT-G8: a film ratio below 1 is mixed lubrication with substantial asperity
        contact (BT-S9 EX); 0.01-0.5 is the common industrial window (BT-S3 EX, BT-S9 EX); no
        boundary label is produced anywhere."""
        for lam, window in ((0.005, False), (0.01, True), (0.5, True), (0.99, False)):
            r = friction_coefficient(lam)
            self.assertEqual(r['regime'], 'MIXED_SUBSTANTIAL_CONTACT')
            self.assertIs(r['in_common_industrial_window'], window)
        for lam in (1.0, 3.0):
            self.assertEqual(friction_coefficient(lam)['regime'], 'MIXED_FIRST_CONTACT')
        self.assertEqual(friction_coefficient(3.01)['regime'], 'HYDRODYNAMIC')
        self.assertEqual(friction_coefficient(0.3)['regime_boundaries'],
                         {'substantial_contact_below': 1.0, 'hydrodynamic_above': 3.0,
                          'common_industrial_window': [0.01, 0.5]})
        results = [friction_coefficient(x) for x in (0.0, 0.005, 0.3, 0.99, 1.0, 2.0, 3.0, 10.0)]
        results.append(friction_at_speed(kerosene(), FINISH, None, **case()))
        results.append(friction_speed_curve(
            kerosene(), FINISH, FrictionClosure(), exit_speeds_m_s=[0.01, 2, 16, 150],
            entry_thickness_m=0.30e-3, exit_thickness_m=0.21e-3, contact_radius_m=0.29,
            plane_strain_yield_pa=2 * 270e6 / math.sqrt(3), back_tension_pa=25e6,
            inlet_temperature_k=C0 + 50))
        for r in results:
            self.assertNotIn('BOUNDARY', json.dumps(r))
        self.assertIn('substantial asperity contact', results[2]['reasons'][0])

    def test_friction_falls_monotonically_with_speed(self):
        curve = friction_speed_curve(
            kerosene(), FINISH, FrictionClosure(), exit_speeds_m_s=[2, 5, 10, 16, 25, 60, 150],
            entry_thickness_m=0.30e-3, exit_thickness_m=0.21e-3, contact_radius_m=0.29,
            plane_strain_yield_pa=2 * 270e6 / math.sqrt(3), back_tension_pa=25e6,
            inlet_temperature_k=C0 + 50)
        mus = [p['friction_coefficient'] for p in curve['points']]
        films = [p['film_thickness_m'] for p in curve['points']]
        self.assertTrue(all(b < a for a, b in zip(mus, mus[1:])))
        self.assertTrue(all(b > a for a, b in zip(films, films[1:])))
        self.assertTrue(all(p['dmu_dspeed_per_m_s'] < 0 for p in curve['points']))
        self.assertIn(PLACEHOLDER_FLAG, curve['flags'])
        p16 = curve['points'][3]
        self.assertAlmostEqual(p16['roll_surface_speed_m_s'], 16.0)
        self.assertAlmostEqual(p16['strip_entry_speed_m_s'], 11.2)

    def test_tends_to_mu_b_and_mu_v(self):
        slow = friction_at_speed(kerosene(), FINISH, None,
                                 **case(roll_surface_speed_m_s=1e-3, strip_entry_speed_m_s=7e-4))
        rough_free = SurfaceFinish(1e-9, 1e-9)
        fast = friction_at_speed(kerosene(), rough_free, None, **case())
        self.assertAlmostEqual(slow['friction_coefficient'], 0.09, delta=1e-4)
        self.assertAlmostEqual(fast['friction_coefficient'], 0.008, delta=1e-6)
        self.assertEqual(fast['regime'], 'HYDRODYNAMIC')
        self.assertIn('THICK_FILM_SKIDDING_MATTE_RISK', fast['flags'])

    def test_speed_slope_matches_analytic(self):
        # Isothermal: h proportional to U and both speeds scale with V_r, so
        # dmu/dV_r = dmu/dLambda * Lambda / V_r.
        r = friction_at_speed(kerosene(), FINISH, FrictionClosure(), **case())
        analytic = r['dmu_dlambda'] * r['film_ratio'] / 16.0
        self.assertAlmostEqual(r['dmu_dspeed_per_m_s'], analytic, delta=1e-9)
        self.assertAlmostEqual(r['film_ratio'], r['film_thickness_m'] / 0.25e-6, places=12)

    def test_hotter_oil_thinner_film_higher_friction(self):
        cold = friction_at_speed(kerosene(), FINISH, None, **case(inlet_temperature_k=C0 + 40))
        hot = friction_at_speed(kerosene(), FINISH, None, **case(inlet_temperature_k=C0 + 60))
        self.assertLess(hot['film_thickness_m'], cold['film_thickness_m'])
        self.assertGreater(hot['friction_coefficient'], cold['friction_coefficient'])
        self.assertAlmostEqual(hot['film_thickness_m'] / cold['film_thickness_m'],
                               math.exp(-0.3), places=12)


class HeatingTests(unittest.TestCase):
    def test_spec_check_49k(self):
        # plane-strain 173 MPa, 50 % -> w = 173e6*ln2 = 119.9 MJ/m3; /2.43e6 = 49.35 K
        r = pass_heating(entry_thickness_m=1e-3, exit_thickness_m=0.5e-3, exit_speed_m_s=5.0,
                         mean_flow_stress_pa=173e6 * math.sqrt(3) / 2, strip_heat_fraction=1.0,
                         entry_temperature_k=C0 + 30)
        self.assertAlmostEqual(r['adiabatic_plastic_temperature_rise_k'],
                               173e6 * math.log(2) / 2.43e6, places=9)
        self.assertAlmostEqual(r['adiabatic_plastic_temperature_rise_k'], 49.35, delta=0.01)
        self.assertAlmostEqual(r['exit_temperature_k'] - r['entry_temperature_k'], 49.35,
                               delta=0.01)
        self.assertEqual(ALUMINIUM_VOLUMETRIC_HEAT_CAPACITY_J_M3K, 2.43e6)

    def test_energy_closes_and_partition(self):
        r = pass_heating(entry_thickness_m=0.30e-3, exit_thickness_m=0.21e-3, exit_speed_m_s=16,
                         mean_flow_stress_pa=270e6, strip_heat_fraction=0.3,
                         entry_temperature_k=C0 + 50, friction_power_per_width_w_m=40e3,
                         temperature_limit_k=C0 + 60)
        total = r['bite_heat_per_width_w_m']
        self.assertAlmostEqual(r['strip_heat_per_width_w_m']
                               + 2 * r['heat_to_each_work_roll_per_width_w_m'], total, places=6)
        self.assertAlmostEqual(r['roll_heat_fraction_per_roll'], 0.35)
        w = 2 / math.sqrt(3) * 270e6 * math.log(0.30 / 0.21)
        self.assertAlmostEqual(total, w * 0.21e-3 * 16 + 40e3, places=4)
        self.assertAlmostEqual(r['exit_temperature_k'],
                               C0 + 50 + 0.3 * total / (2.43e6 * 0.21e-3 * 16), places=9)
        self.assertIn('EXIT_TEMPERATURE_ABOVE_SUPPLIED_LIMIT', r['flags'])
        self.assertNotIn('FRICTION_POWER_NOT_SUPPLIED', r['flags'])


class HardeningTests(unittest.TestCase):
    VOCE = VoceHardening(initial_stress_pa=40e6, saturation_stress_pa=200e6,
                         characteristic_strain=0.25, stage_iv_slope_pa=20e6,
                         provenance='synthetic test parameters')

    def test_voce_mean_equals_quadrature(self):
        a, b, n = 0.13, 0.91, 2000
        hstep = (b - a) / n
        s = self.VOCE.stress(a) + self.VOCE.stress(b) + sum(
            (4 if i % 2 else 2) * self.VOCE.stress(a + i * hstep) for i in range(1, n))
        self.assertAlmostEqual(self.VOCE.mean_stress(a, b), s * hstep / 3 / (b - a), delta=1e-3)
        self.assertAlmostEqual(self.VOCE.mean_stress(0.3, 0.3 + 1e-12), self.VOCE.stress(0.3),
                               delta=1e-2)

    def test_voce_without_stage_iv_saturates(self):
        v = VoceHardening(40e6, 200e6, 0.25, 0.0, 'synthetic')
        self.assertAlmostEqual(v.stress(0.0), 40e6)
        self.assertAlmostEqual(v.stress(20.0), 200e6, delta=1e-3)
        self.assertGreater(self.VOCE.stress(20.0), 200e6)

    def test_schedule_reproduces_power_law_mean(self):
        law = PowerHardeningLaw('5052', 'O', 90e6, 210e6, 0.13, 'synthetic test curve')
        gauges = [2.0e-3, 1.2e-3, 0.7e-3, 0.4e-3]
        r = schedule_flow_stress(gauges, law, prior_equivalent_strain=0.05)
        k = 2 / math.sqrt(3)
        for i, p in enumerate(r['passes']):
            e0 = 0.05 + k * math.log(gauges[0] / gauges[i])
            e1 = 0.05 + k * math.log(gauges[0] / gauges[i + 1])
            self.assertAlmostEqual(p['entry_equivalent_strain'], e0, places=12)
            self.assertAlmostEqual(p['exit_equivalent_strain'], e1, places=12)
            self.assertAlmostEqual(p['mean_flow_stress_pa'], law.mean_stress(e0, e1), places=3)
            self.assertAlmostEqual(p['plane_strain_mean_flow_stress_pa'],
                                   k * p['mean_flow_stress_pa'], places=3)
        self.assertIn('POWER_LAW_BEYOND_EPS_0P3_OVERPREDICTS', r['flags'])
        rv = schedule_flow_stress(gauges, self.VOCE)
        self.assertEqual(rv['law_type'], 'voce_stage_iv')
        self.assertAlmostEqual(rv['passes'][0]['entry_flow_stress_pa'], 40e6)

    def test_literature_fits(self):
        for fit_id, fit in LITERATURE_FITS.items():
            self.assertEqual(fit['tag'], 'V')
            self.assertIn('0.3', fit['warning'])
            law = literature_power_law(fit_id)
            self.assertEqual(law.strength_coefficient_pa, fit['strength_coefficient_pa'])
        self.assertEqual(LITERATURE_FITS['1050-annealed_batorfi']['yield_stress_pa'], 15.3e6)
        with self.assertRaises(ValueError):
            literature_power_law('nope')


class ValidationAndJsonTests(unittest.TestCase):
    def test_validation(self):
        bad = [
            lambda: inlet_film_thickness(FOIL_OIL, **case(roll_surface_speed_m_s=True)),
            lambda: inlet_film_thickness(FOIL_OIL, **case(back_tension_pa=400e6)),
            lambda: inlet_film_thickness(FOIL_OIL, **case(exit_thickness_m=0.4e-3)),
            lambda: inlet_film_thickness(FOIL_OIL, **case(inlet_temperature_k=float('nan'))),
            lambda: inlet_film_thickness(FOIL_OIL, **case(), thermal_correction=1),
            lambda: Lubricant(-1e-3, 300.0, 0.015, 1e-8).validate(),
            lambda: SurfaceFinish(0.0, 0.0).validate(),
            lambda: FrictionClosure(mu_b=0.01, mu_v=0.02).validate(),
            lambda: friction_coefficient(-0.1),
            lambda: pass_heating(entry_thickness_m=1e-3, exit_thickness_m=0.5e-3,
                                 exit_speed_m_s=5, mean_flow_stress_pa=1e8,
                                 strip_heat_fraction=1.5, entry_temperature_k=300),
            lambda: schedule_flow_stress([1e-3, 1e-3], HardeningTests.VOCE),
            lambda: schedule_flow_stress([1e-3, 0.5e-3], object()),
            lambda: VoceHardening(200e6, 100e6, 0.2, 0.0, 'x').validate(),
            lambda: friction_speed_curve(FOIL_OIL, FINISH, None, exit_speeds_m_s=[],
                                         entry_thickness_m=1e-3, exit_thickness_m=0.5e-3,
                                         contact_radius_m=0.2, plane_strain_yield_pa=2e8,
                                         back_tension_pa=0, inlet_temperature_k=300),
        ]
        for i, fn in enumerate(bad):
            with self.subTest(i=i), self.assertRaises(ValueError):
                fn()

    def test_results_json_status_flags_basis(self):
        results = [
            inlet_film_thickness(FOIL_OIL, **case()),
            friction_coefficient(1.0),
            friction_at_speed(kerosene(), FINISH, FrictionClosure(), **case()),
            pass_heating(entry_thickness_m=1e-3, exit_thickness_m=0.5e-3, exit_speed_m_s=5,
                         mean_flow_stress_pa=1e8, strip_heat_fraction=0.5,
                         entry_temperature_k=300),
            schedule_flow_stress([1e-3, 0.5e-3], HardeningTests.VOCE),
        ]
        for r in results:
            json.dumps(r, allow_nan=False)
            self.assertTrue(r['status'].startswith('UNVALIDATED'))
            for key in ('flags', 'limitations', 'basis', 'sources'):
                self.assertIn(key, r)
            self.assertTrue(all(f == f.upper() for f in r['flags']))


class OilPropertyTests(unittest.TestCase):
    """SPEC18 package 5: viscosity table, Roelands pressure law, Eyring and limiting stress.
    Worked numbers of the planner's standard-library prototype (s23/v_p5.py), pinned."""

    def setUp(self):
        from physicroll import bite_tribology as bt
        self.bt = bt
        ex = bt.EXAMPLE_KEROSINE_BASE_OIL['viscosity_pa_s_at_0_mpa'][0]
        self.table = tuple((float(k), v) for k, v in ex.items())

    def rel(self, a, b, tol=1e-6):
        self.assertLessEqual(abs(a / b - 1), tol, (a, b))

    def test_table_interpolation_and_extrapolation(self):
        lub = Lubricant(1.409e-3, C0 + 40, 0.015, 10.40e-9, viscosity_table=self.table)
        for t, want, extrap in ((50, 1.206440e-3, False), (80, 8.07995e-4, False),
                                (120, 4.94340e-4, True), (20, 1.921860e-3, True)):
            self.rel(lub.zero_pressure_viscosity_pa_s(C0 + t), want)
            self.assertEqual(lub.viscosity_table_extrapolated(C0 + t), extrap)
        self.rel(lub.temperature_viscosity_coefficient_at(C0 + 50), 0.0155207, 5e-6)  # 6 digits
        self.rel(lub.temperature_viscosity_coefficient_at(C0 + 80), 0.0122833, 5e-6)
        nu = kinematic_cst_to_dynamic_viscosity_pa_s
        sheet = ((C0 + 20, nu(3.0, 800.0)), (C0 + 70, nu(1.4, 800.0)), (C0 + 130, nu(0.7, 800.0)))
        lub2 = Lubricant(1e-3, C0 + 40, 0.015, 1e-8, viscosity_table=sheet)
        self.rel(lub2.zero_pressure_viscosity_pa_s(C0 + 40), 1.76935e-3)
        self.rel(lub2.temperature_viscosity_coefficient_at(C0 + 40), 0.0152428, 5e-6)
        self.rel(lub2.temperature_viscosity_coefficient_at(C0 + 100), 0.0115525, 5e-6)
        for t in (C0 + 30, C0 + 65, C0 + 125):       # coefficient = -d ln eta0/dT
            d = 1e-4
            fd = -(math.log(lub.zero_pressure_viscosity_pa_s(t + d))
                   - math.log(lub.zero_pressure_viscosity_pa_s(t - d))) / (2 * d)
            self.rel(lub.temperature_viscosity_coefficient_at(t), fd, 1e-6)
        self.assertEqual(FOIL_OIL.temperature_viscosity_coefficient_at(C0 + 70),
                         FOIL_OIL.temperature_viscosity_coefficient_per_k)

    def test_two_point_table_equals_the_exponential_law(self):
        law = Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8)
        pts = tuple((t, law.dynamic_viscosity_pa_s(t)) for t in (C0 + 20, C0 + 90))
        tab = Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8, viscosity_table=pts)
        for t in (C0 + 10, C0 + 45, C0 + 120):
            for p in (0.0, 50e6):
                self.rel(tab.dynamic_viscosity_pa_s(t, p), law.dynamic_viscosity_pa_s(t, p), 1e-12)
        kw = dict(roll_surface_speed_m_s=10.0, strip_entry_speed_m_s=7.0,
                  entry_thickness_m=50e-6, exit_thickness_m=30e-6, contact_radius_m=0.135,
                  plane_strain_yield_pa=200e6, back_tension_pa=35e6, inlet_temperature_k=C0 + 45,
                  thermal_correction=True)
        a, b = inlet_film_thickness(law, **kw), inlet_film_thickness(tab, **kw)
        self.rel(b['film_thickness_m'], a['film_thickness_m'], 1e-12)
        self.assertIn('VISCOSITY_FROM_TABLE', b['flags'])
        self.assertNotIn('VISCOSITY_TABLE_EXTRAPOLATED', b['flags'])
        self.assertNotIn('VISCOSITY_FROM_TABLE', a['flags'])
        self.assertIn('reference viscosity is not used', b['basis']['viscosity_law'])
        c = inlet_film_thickness(tab, **dict(kw, inlet_temperature_k=C0 + 120))
        self.assertIn('VISCOSITY_TABLE_EXTRAPOLATED', c['flags'])

    def test_table_validation(self):
        for bad in (((300.0, 1e-3),), ((300.0, 1e-3), (300.0, 9e-4)),
                    ((300.0, 1e-3), (320.0, 2e-3)), ((200.0, 1e-3), (320.0, 9e-4)),
                    ((300.0, 0.0), (320.0, 0.0)), ((300.0, True), (320.0, 1e-3))):
            with self.assertRaises(ValueError):
                Lubricant(1e-3, 313.15, 0.015, 1e-8, viscosity_table=bad).validate()

    def test_roelands_numbers_and_slope(self):
        for t, eta0, alpha, z, rows in (
                (40, 1.409e-3, 10.40e-9, 0.657133,
                 ((100e6, 3.98637e-3, 3.69913e-3), (625e6, 0.937185, 0.180001),
                  (945e6, 26.1311, 1.22828), (1510e6, 9312.6, 24.363))),
                (60, 1.033e-3, 9.60e-9, 0.673959, ((100e6, 2.69788e-3, 2.52609e-3),))):
            barus = Lubricant(eta0, C0 + t, 0.0155, alpha)
            roel = Lubricant(eta0, C0 + t, 0.0155, alpha, pressure_law='roelands')
            self.rel(roel.roelands_index(C0 + t), z, 1e-6)
            for p, want_b, want_r in rows:
                self.rel(barus.dynamic_viscosity_pa_s(C0 + t, p), want_b, 1e-5)  # quoted digits
                self.rel(roel.dynamic_viscosity_pa_s(C0 + t, p), want_r, 1e-5)
        roel = Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8, pressure_law='roelands')
        for t in (C0 + 40, C0 + 80):                 # slope at p = 0 equals alpha
            d = 1e3
            fd = math.log(roel.dynamic_viscosity_pa_s(t, d)
                          / roel.dynamic_viscosity_pa_s(t, 0.0)) / d
            self.rel(fd, 1.2e-8, 1e-6)
        fixed = Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8, pressure_law='roelands', roelands_z=0.6)
        self.assertEqual(fixed.roelands_index(C0 + 80), 0.6)
        with self.assertRaises(ValueError):       # ln(eta0) + 9.67 <= 0
            Lubricant(5e-5, C0 + 40, 0.015, 1e-8,
                      pressure_law='roelands').dynamic_viscosity_pa_s(C0 + 40, 1e8)
        for bad in (dict(pressure_law='wlf'), dict(roelands_z=0.0), dict(roelands_z=2.5)):
            with self.assertRaises(ValueError):
                Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8, **bad).validate()

    def test_eyring_and_limiting_stress_are_supplied_only(self):
        lub = Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8)
        for f in ('eyring_stress_pa', 'eyring_stress_pressure_coefficient',
                  'limiting_shear_stress_pa', 'limiting_shear_pressure_coefficient'):
            self.assertIsNone(getattr(lub, f))
        self.assertIsNone(lub.eyring_stress_at(1e9))
        self.assertIsNone(lub.limiting_shear_stress_at(1e9))
        self.assertEqual(lub.limiting_shear_check(1e9), ([], []))
        ey = Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8, eyring_stress_pa=1e6,
                       eyring_stress_pressure_coefficient=0.007)
        self.rel(ey.eyring_stress_at(1e9), 8e6)
        low = Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8, limiting_shear_pressure_coefficient=0.03)
        flags, notes = low.limiting_shear_check(1e9)
        self.assertEqual(flags, ['LIMITING_SHEAR_BELOW_PUBLISHED_LOWER_BOUND'])
        self.assertIn('0.045', notes[0])
        high = Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8, limiting_shear_pressure_coefficient=0.06)
        self.assertEqual(high.limiting_shear_check(1e9), ([], []))
        for bad in (dict(eyring_stress_pa=1e3), dict(eyring_stress_pressure_coefficient=0.0),
                    dict(eyring_stress_pressure_coefficient=0.2),
                    dict(limiting_shear_stress_pa=1e10),
                    dict(limiting_shear_pressure_coefficient=1.5)):
            with self.assertRaises(ValueError):
                Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8, **bad).validate()

    def test_example_oil_is_tagged_and_not_a_default(self):
        ex = self.bt.EXAMPLE_KEROSINE_BASE_OIL
        for key, (value, tag) in ex.items():
            self.assertIn('E6 FT', tag, key)
        self.assertIn('not a plant', ex['note'][0])
        self.assertEqual(ex['limiting_shear_lower_bound_over_pressure'][0], 0.045)
        self.assertEqual(ex['eyring_stress_pa_at_313_k'][0],
                         {'625e6': 4.5e6, '945e6': 6.0e6, '1510e6': 11.7e6})
        lub = Lubricant(2.5e-3, C0 + 40, 0.015, 1.2e-8)
        self.assertEqual(lub.pressure_law, 'barus')
        self.assertIsNone(lub.viscosity_table)


if __name__ == '__main__':
    unittest.main()
