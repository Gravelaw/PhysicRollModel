"""Verification of physicroll.mill_dynamics against limits derived from its equations.

Software verification only: none of these checks validates the model against a mill.

Static limits used below (derived here, tension coupling off = constant tension):
  equilibrium   dF = K_wb*(x_w - x_b + e) = K_h*(x_b - x_s),  so  dh = 2*x_w = 2*x_s + dF/M - 2e
  AGC loop      x_s = x_s_ref = -alpha*dF/(2*M)   ->  dh = (1 - alpha)*dF/M - 2e
  bite          dF = -Q*dh + dF0  (dF0: force change at fixed gap)
  =>  run-out   dh/e   = -2*M/(M + (1-alpha)*Q)
      input     dh/dF0 = (1-alpha)/(M + (1-alpha)*Q)
      stroke    S = 2*x_s = -alpha*dF/M
Tension coupling on (constant far-end span speeds), DC: sigma_e' = sigma_x' = 0 forces
du_x = du_e = 0, hence df = 0 and (for alpha < 1) dh = (h1/h0)*dh_in for incoming gauge and
dh = 0 for run-out (mass-flow limit). Roll-speed DC: du_x = V_r*df + (1+f)*dV = 0 and du_e = 0
give dh = 0 (so dF = 0) and F_se*s_e + F_sx*s_x = 0, f_se*s_e + f_sx*s_x = -(1+f)*dV/V_r.
"""
import json
import math
import unittest

from physicroll.chatter import (BitePass, StandModel, StripSpans, critical_speed,
                                derive_bite_response, frequency_response)
from physicroll.mill_dynamics import (AGC_STATE_NAMES, GaugemeterAGC, agc_frequency_response,
                                      agc_stability, assemble_agc_state_matrix,
                                      coil_synchronous_frequencies, flow_stress_sensitivity,
                                      friction_force_sensitivity, hardness_gauge_shift,
                                      reel_inertia_kg_m2, roll_speed_ripple_response,
                                      speed_change_gauge_shift, torsional_modes)

REFERENCE = BitePass(0.6e-3, 0.42e-3, 1.5, 0.2, 250e6, 0.05, 25e6, 30e6)
SPANS = StripSpans(70e9, 4.0, 4.0)
SPEED = 10.0
DC_HZ = 1e-3


def _stand(zeta=0.03):
    return StandModel.from_modal_damping(3000.0, 22000.0, 4e10, 1.4e10, zeta)


def _json_ok(test, value):
    test.assertIsInstance(json.dumps(value, allow_nan=False), str)


def _cplx(row, prefix):
    return complex(row[prefix + '_real'], row[prefix + '_imag'])


class _Shared(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bite = derive_bite_response(REFERENCE, cells=64)
        cls.stand = _stand()
        cls.m = cls.stand.mill_modulus_n_m
        cls.q = cls.bite.strip_modulus_n_m

    def dc(self, agc, disturbance='work_backup_runout', couple=False, **kw):
        r = agc_frequency_response(self.stand, self.bite, SPANS, SPEED, agc, [DC_HZ],
                                   disturbance=disturbance, couple_tension=couple, **kw)
        return r, r['responses'][0]


class AGCStaticLimitTests(_Shared):
    def test_runout_static_transfer_and_stroke(self):
        for alpha in (0.0, 0.25, 0.5, 0.9, 1.0):
            for filt in (None, 25.0):
                agc = GaugemeterAGC(alpha, 25.0, filt)
                r, row = self.dc(agc)
                expected = -2 * self.m / (self.m + (1 - alpha) * self.q)
                dh = _cplx(row, 'exit_thickness')
                self.assertAlmostEqual(dh.real / expected, 1, delta=1e-6)
                self.assertLess(abs(dh.imag), 1e-3 * abs(expected))
                self.assertAlmostEqual(
                    r['analytic_static_exit_thickness_per_unit_disturbance_tension_off'] /
                    expected, 1, delta=1e-12)
                stroke = _cplx(row, 'cylinder_stroke').real
                d_force = -self.q * dh.real
                self.assertAlmostEqual(stroke, -alpha * d_force / self.m,
                                       delta=1e-6 * abs(expected))
                no_agc = _cplx(row, 'no_agc_exit_thickness').real
                self.assertAlmostEqual(no_agc / (-2 * self.m / (self.m + self.q)), 1, delta=1e-6)

    def test_full_compensation_prints_runout_through(self):
        _, row = self.dc(GaugemeterAGC(1.0, 25.0))
        self.assertAlmostEqual(_cplx(row, 'exit_thickness').real, -2.0, delta=1e-6)
        self.assertAlmostEqual(row['agc_to_no_agc_magnitude_ratio'],
                               (self.m + self.q) / self.m, delta=1e-5)

    def test_eccentricity_amplification_rises_with_alpha(self):
        mags = []
        for alpha in (0.0, 0.3, 0.6, 0.9, 1.0):
            r, row = self.dc(GaugemeterAGC(alpha, 25.0))
            mags.append(row['exit_thickness_per_unit_disturbance'])
            self.assertAlmostEqual(r['eccentricity_amplification_vs_no_agc'],
                                   (self.m + self.q) / (self.m + (1 - alpha) * self.q),
                                   delta=1e-12)
        self.assertTrue(all(b > a for a, b in zip(mags, mags[1:])))

    def test_entry_thickness_static_limit(self):
        for alpha in (0.0, 0.5, 0.9, 1.0):
            _, row = self.dc(GaugemeterAGC(alpha, 25.0), 'entry_thickness')
            expected = ((1 - alpha) * self.bite.dforce_dentry_thickness_n_m /
                        (self.m + (1 - alpha) * self.q))
            self.assertAlmostEqual(_cplx(row, 'exit_thickness').real, expected,
                                   delta=1e-6 * self.bite.dforce_dentry_thickness_n_m / self.m)

    def test_mass_flow_limit_with_tension_coupling(self):
        h_ratio = self.bite.exit_thickness_m / self.bite.entry_thickness_m
        for alpha in (0.0, 0.5, 0.9):
            agc = GaugemeterAGC(alpha, 25.0)
            r = agc_frequency_response(self.stand, self.bite, SPANS, SPEED, agc, [1e-4],
                                       disturbance='entry_thickness')['responses'][0]
            self.assertAlmostEqual(_cplx(r, 'exit_thickness').real, h_ratio, delta=1e-5)
            r = agc_frequency_response(self.stand, self.bite, SPANS, SPEED, agc,
                                       [1e-4])['responses'][0]
            self.assertLess(r['exit_thickness_per_unit_disturbance'], 1e-4)

    def test_alpha_zero_equals_chatter_frequency_response(self):
        freqs = [0.5, 5.0, 50.0, 120.0, 179.0, 300.0, 800.0]
        for couple in (True, False):
            for dist in ('work_backup_runout', 'entry_thickness'):
                ref = frequency_response(self.stand, self.bite, SPANS, SPEED, freqs,
                                         disturbance=dist, couple_tension=couple)
                got = agc_frequency_response(self.stand, self.bite, SPANS, SPEED,
                                             GaugemeterAGC(0.0, 25.0), freqs,
                                             disturbance=dist, couple_tension=couple)
                for a, b in zip(ref, got['responses']):
                    z = complex(a['real'], a['imag'])
                    for key in ('exit_thickness', 'no_agc_exit_thickness'):
                        self.assertLess(abs(_cplx(b, key) - z), 1e-9 * abs(z))
                    self.assertLess(b['cylinder_stroke_per_unit_disturbance'], 1e-12 * abs(z))

    def test_agc_attenuates_entry_ripple_at_low_frequency_not_at_chatter(self):
        f_chatter = critical_speed(self.stand, self.bite, SPANS)['onset_frequency_hz']
        alpha = 0.9
        low = (1 - alpha) * (self.m + self.q) / (self.m + (1 - alpha) * self.q)
        for filt in (None, 25.0):
            rows = agc_frequency_response(
                self.stand, self.bite, SPANS, SPEED, GaugemeterAGC(alpha, 25.0, filt),
                [DC_HZ, f_chatter], disturbance='entry_thickness',
                couple_tension=False)['responses']
            self.assertAlmostEqual(rows[0]['agc_to_no_agc_magnitude_ratio'], low, delta=1e-5)
            self.assertLess(low, 0.3)
            self.assertGreater(rows[1]['agc_to_no_agc_magnitude_ratio'], 0.9)
        # with a second-order roll-off the loop leaves the chatter band essentially untouched
        self.assertAlmostEqual(rows[1]['agc_to_no_agc_magnitude_ratio'], 1, delta=0.05)

    def test_matrix_shape_and_entries(self):
        agc = GaugemeterAGC(0.9, 25.0)
        a = assemble_agc_state_matrix(self.stand, self.bite, SPANS, SPEED, agc)
        self.assertEqual((len(a), len(a[0])), (7, 7))
        kh, mb = self.stand.housing_stiffness_n_m, self.stand.backup_roll_mass_kg
        wc, g = 2 * math.pi * 25.0, 0.9 * kh / (2 * self.m)
        self.assertAlmostEqual(a[3][6], kh / mb)
        self.assertAlmostEqual(a[6][2], -wc * g)
        self.assertAlmostEqual(a[6][6], wc * (g - 1))
        a8 = assemble_agc_state_matrix(self.stand, self.bite, SPANS, SPEED,
                                       GaugemeterAGC(0.9, 25.0, 30.0))
        self.assertEqual(len(a8), 8)
        self.assertEqual(GaugemeterAGC(0.9, 25.0, 30.0).state_names[-1], 'force_filtered_n')
        self.assertEqual(AGC_STATE_NAMES[-1], 'x_cylinder_m')


class AGCStabilityTests(_Shared):
    def test_alpha_zero_reproduces_chatter_critical_speed(self):
        s = agc_stability(self.stand, self.bite, SPANS, SPEED, GaugemeterAGC(0.0, 25.0))
        for key in ('critical_speed_relative_change',
                    'critical_speed_relative_change_without_bite_damping'):
            self.assertLess(abs(s[key]), 1e-5)
        _json_ok(self, s)

    def test_first_order_loop_interaction_is_reported_and_rolloff_removes_it(self):
        plain = agc_stability(self.stand, self.bite, SPANS, SPEED, GaugemeterAGC(0.9, 25.0))
        self.assertLess(plain['critical_speed_relative_change'], -0.05)
        self.assertIn('AGC_LOWERS_CHATTER_CRITICAL_SPEED_BY_MORE_THAN_5_PERCENT', plain['flags'])
        self.assertAlmostEqual(plain['critical_speed_with_agc']['onset_frequency_hz'] /
                               plain['critical_speed_without_agc']['onset_frequency_hz'], 1,
                               delta=0.02)
        filtered = agc_stability(self.stand, self.bite, SPANS, SPEED,
                                 GaugemeterAGC(0.9, 25.0, 10.0))
        self.assertLess(abs(filtered['critical_speed_relative_change']), 0.02)
        _json_ok(self, plain)

    def test_negative_damping_without_strip_feedback(self):
        """Coupling off, beta = 0: the stand is stable alone and the AGC alone destabilises."""
        opts = dict(couple_tension=False, bite_damping_transit_fraction=0.0)
        s = agc_stability(self.stand, self.bite, SPANS, SPEED, GaugemeterAGC(0.9, 25.0),
                          speed_range_m_s=(1.0, 2.0), **opts)
        self.assertLess(s['no_agc_max_growth_rate_per_s'], 0)
        self.assertGreater(s['max_growth_rate_per_s'], 0)
        self.assertIn('NEUTRAL_ZERO_MODE_EXCLUDED_FROM_GROWTH_RATE', s['flags'])
        slow = agc_stability(self.stand, self.bite, SPANS, SPEED, GaugemeterAGC(0.9, 5.0),
                             speed_range_m_s=(1.0, 2.0), **opts)
        self.assertLess(slow['max_growth_rate_per_s'], 0)

    def test_full_compensation_with_tension_has_neutral_mode(self):
        s = agc_stability(self.stand, self.bite, SPANS, SPEED, GaugemeterAGC(1.0, 25.0),
                          speed_range_m_s=(1.0, 2.0))
        self.assertIn('NEUTRAL_ZERO_MODE_EXCLUDED_FROM_GROWTH_RATE', s['flags'])


class HardnessTests(_Shared):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.flow = flow_stress_sensitivity(REFERENCE, cells=64)

    def test_sensitivity_magnitude(self):
        d = self.flow['dforce_dflow_stress_m2']
        ratio = self.flow['force_per_flow_stress_m2']
        # force ~ Y times a contact area that itself grows with load (flattening)
        self.assertGreater(d, ratio)
        self.assertLess(d, 2 * ratio)
        self.assertTrue(math.isfinite(self.flow['dslip_dflow_stress_per_pa']))
        self.assertAlmostEqual(self.flow['flow_stress_step_pa'], 0.005 * 250e6)
        _json_ok(self, self.flow)

    def test_static_hardness_limit(self):
        dy = 0.02 * REFERENCE.mean_flow_stress_pa
        d0 = self.flow['dforce_dflow_stress_m2'] * dy
        for alpha in (0.0, 0.9):
            expected = (1 - alpha) * d0 / (self.m + (1 - alpha) * self.q)
            _, row = self.dc(GaugemeterAGC(alpha, 25.0), 'flow_stress',
                             flow_sensitivity=self.flow)
            self.assertAlmostEqual(_cplx(row, 'exit_thickness').real * dy / expected, 1,
                                   delta=1e-6)
            shift = hardness_gauge_shift(self.flow['dforce_dflow_stress_m2'], dy, self.m,
                                         self.q, alpha)
            self.assertAlmostEqual(shift['exit_thickness_change_m'] / expected, 1, delta=1e-12)
            _json_ok(self, shift)

    def test_flow_stress_needs_sensitivity(self):
        with self.assertRaises(ValueError):
            self.dc(GaugemeterAGC(0.5, 25.0), 'flow_stress')
        with self.assertRaises(ValueError):
            self.dc(GaugemeterAGC(0.5, 25.0), 'flow_stress',
                    flow_sensitivity={'dforce_dflow_stress_m2': float('nan'),
                                      'dslip_dflow_stress_per_pa': 0.0})

    def test_coil_synchronous_frequencies(self):
        r = coil_synchronous_frequencies(7.0, 1.6, 3, entry_thickness_m=0.6e-3,
                                         exit_thickness_m=0.42e-3)
        f1 = 7.0 / (math.pi * 1.6)
        self.assertAlmostEqual(r['decoiler_rotation_hz'], f1)
        for n, h in enumerate(r['harmonics'], start=1):
            self.assertAlmostEqual(h['frequency_hz'], n * f1)
            self.assertAlmostEqual(h['exit_strip_pitch_m'], math.pi * 1.6 * 0.6 / 0.42 / n)
        self.assertIsNone(coil_synchronous_frequencies(7.0, 1.6)['harmonics'][0][
            'exit_strip_pitch_m'])
        with self.assertRaises(ValueError):
            coil_synchronous_frequencies(7.0, 1.6, 0)
        with self.assertRaises(ValueError):
            coil_synchronous_frequencies(7.0, 1.6, entry_thickness_m=0.6e-3)
        _json_ok(self, r)


class DriveTrainTests(unittest.TestCase):
    def test_benchmark_three_mass_chain(self):
        r = torsional_modes([835.0, 122.0, 1055.0], [7.69e6, 7.16e6])
        self.assertTrue(r['rigid_body_mode_present'])
        self.assertEqual(r['frequencies_hz'][0], 0.0)
        self.assertAlmostEqual(r['elastic_frequencies_hz'][0] / 14.0, 1, delta=0.03)
        self.assertAlmostEqual(r['elastic_frequencies_hz'][1] / 56.0, 1, delta=0.03)
        self.assertTrue(all(abs(v - 1) < 1e-9 for v in r['mode_shapes'][0]))
        self.assertNotIn('FIRST_TORSIONAL_MODE_OUTSIDE_10_20_HZ_GUIDANCE', r['flags'])
        _json_ok(self, r)

    def test_two_mass_formula_and_orthogonality(self):
        j1, j2, k = 835.0, 1055.0, 7.69e6
        r = torsional_modes([j1, j2], [k])
        f1 = math.sqrt(k * (j1 + j2) / (j1 * j2)) / (2 * math.pi)
        self.assertAlmostEqual(r['elastic_frequencies_hz'][0] / f1, 1, delta=1e-10)
        j = [400.0, 50.0, 900.0, 30.0, 1200.0]
        r = torsional_modes(j, [3e6, 5e6, 2e6, 8e6])
        self.assertEqual(len(r['frequencies_hz']), 5)
        self.assertEqual(r['frequencies_hz'][0], 0.0)
        shapes = r['mode_shapes']
        for a in range(5):
            for b in range(a + 1, 5):
                dot = sum(ji * x * y for ji, x, y in zip(j, shapes[a], shapes[b]))
                self.assertLess(abs(dot), 1e-9 * sum(j))
        # Rayleigh quotient of each shape equals its omega^2
        ks = [3e6, 5e6, 2e6, 8e6]
        for f, phi in zip(r['frequencies_hz'][1:], shapes[1:]):
            pe = sum(kk * (phi[i + 1] - phi[i]) ** 2 for i, kk in enumerate(ks))
            ke = sum(ji * p * p for ji, p in zip(j, phi))
            self.assertAlmostEqual(pe / ke / (2 * math.pi * f) ** 2, 1, delta=1e-9)

    def test_reel_inertia(self):
        j = reel_inertia_kg_m2(50.0, 2700.0, 1.5, 0.9, 0.3, 2.0)
        self.assertAlmostEqual(j, 50.0 + math.pi * 2700 * 1.5 * (0.9 ** 4 - 0.3 ** 4) / 8)
        self.assertAlmostEqual(reel_inertia_kg_m2(50.0, 2700.0, 1.5, 0.3, 0.3, 2.0), 50.0)
        with self.assertRaises(ValueError):
            reel_inertia_kg_m2(50.0, 2700.0, 1.5, 0.2, 0.3, 2.0)
        with self.assertRaises(ValueError):
            reel_inertia_kg_m2(True, 2700.0, 1.5, 0.9, 0.3, 2.0)

    def test_torsional_validation(self):
        for args in (([1.0], []), ([1.0, 2.0], [1.0, 2.0]), ([1.0, -2.0], [1.0]),
                     ([1.0] * 6, [1.0] * 5), ([1.0, 2.0], [float('inf')])):
            with self.assertRaises(ValueError):
                torsional_modes(*args)


class RollSpeedTests(_Shared):
    def dc_tensions(self):
        b = self.bite
        f = b.forward_slip_fraction
        vr = SPEED / (1 + f)
        a11, a12 = b.dforce_dentry_tension_m2, b.dforce_dexit_tension_m2
        a21, a22 = b.dslip_dentry_tension_per_pa, b.dslip_dexit_tension_per_pa
        det = a11 * a22 - a12 * a21
        rhs = -(1 + f) / vr
        return -a12 * rhs / det, a11 * rhs / det

    def test_dc_limit(self):
        se, sx = self.dc_tensions()
        self.assertGreater(se, 0)     # rolls speed up: entry pulled harder, exit slackens
        self.assertLess(sx, 0)
        for agc in (None, GaugemeterAGC(0.5, 25.0)):
            r = roll_speed_ripple_response(self.stand, self.bite, SPANS, SPEED, [1e-4], agc=agc)
            row = r['responses'][0]
            self.assertAlmostEqual(row['entry_tension_real'] / se, 1, delta=1e-6)
            self.assertAlmostEqual(row['exit_tension_real'] / sx, 1, delta=1e-6)
            # gauge: dh -> 0 (compare with the coupling-off gauge scale per m/s ~ h1/V_r)
            self.assertLess(row['exit_thickness_per_unit_disturbance'],
                            1e-5 * self.bite.exit_thickness_m / SPEED)
            self.assertAlmostEqual(r['analytic_dc_limit']['entry_tension_pa_per_m_s'] / se, 1,
                                   delta=1e-12)
            _json_ok(self, r)

    def test_agc_roll_speed_matches_ripple_function(self):
        agc = GaugemeterAGC(0.7, 25.0)
        freqs = [2.0, 15.0, 180.0]
        a = roll_speed_ripple_response(self.stand, self.bite, SPANS, SPEED, freqs, agc=agc)
        b = agc_frequency_response(self.stand, self.bite, SPANS, SPEED, agc, freqs,
                                   disturbance='roll_speed')
        for x, y in zip(a['responses'], b['responses']):
            self.assertAlmostEqual(x['exit_thickness_real'], y['exit_thickness_real'],
                                   delta=1e-12)
            self.assertAlmostEqual(x['entry_tension_imag'], y['entry_tension_imag'], delta=1e-3)

    def test_no_path_without_tension_coupling(self):
        r = roll_speed_ripple_response(self.stand, self.bite, SPANS, SPEED, [5.0],
                                       couple_tension=False)
        self.assertEqual(r['responses'][0]['exit_thickness_per_unit_disturbance'], 0.0)
        self.assertIn('NO_ROLL_SPEED_PATH_WITH_TENSION_COUPLING_OFF', r['flags'])
        self.assertIsNone(r['analytic_dc_limit'])


class SpeedChangeTests(_Shared):
    def test_gauge_shift_formula(self):
        m, q, d = 5e9, 1.2e10, 3.6e7
        for alpha in (0.0, 0.5, 0.9, 1.0):
            r = speed_change_gauge_shift(d, 0.01, m, q, alpha)
            expected = (1 - alpha) * d * 0.01 / (m + (1 - alpha) * q)
            self.assertAlmostEqual(r['exit_thickness_change_m'], expected, delta=1e-15)
            self.assertAlmostEqual(r['exit_thickness_change_without_agc_m'],
                                   d * 0.01 / (m + q), delta=1e-15)
            # gaugemeter consistency: dh = S + dF/M
            self.assertAlmostEqual(r['exit_thickness_change_m'],
                                   r['cylinder_stroke_change_m'] +
                                   r['separating_force_change_n'] / m, delta=1e-15)
            _json_ok(self, r)
        self.assertEqual(speed_change_gauge_shift(d, 0.01, m, q, 1.0)['exit_thickness_change_m'],
                         0.0)

    def test_friction_sensitivity_and_agc_consistency(self):
        fr = friction_force_sensitivity(REFERENCE, cells=64)
        self.assertGreater(fr['dforce_dfriction_n'], 0)
        self.assertGreater(fr['dslip_dfriction'], 0)
        self.assertAlmostEqual(fr['friction_step'], 0.02 * 0.05)
        # the same dF0 driven through the dynamic model as a flow-stress-like force input
        alpha = 0.9
        pseudo = {'dforce_dflow_stress_m2': fr['dforce_dfriction_n'],
                  'dslip_dflow_stress_per_pa': 0.0}
        _, row = self.dc(GaugemeterAGC(alpha, 25.0), 'flow_stress', flow_sensitivity=pseudo)
        shift = speed_change_gauge_shift(fr['dforce_dfriction_n'], 0.01, self.m, self.q, alpha)
        self.assertAlmostEqual(_cplx(row, 'exit_thickness').real * 0.01 /
                               shift['exit_thickness_change_m'], 1, delta=1e-6)
        _json_ok(self, fr)


class ValidationAndSerialisationTests(_Shared):
    def test_agc_validation(self):
        for agc in (GaugemeterAGC(-0.1, 25.0), GaugemeterAGC(1.1, 25.0),
                    GaugemeterAGC(True, 25.0), GaugemeterAGC(0.5, 0.0),
                    GaugemeterAGC(0.5, float('nan')), GaugemeterAGC(0.5, 25.0, -1.0)):
            with self.assertRaises(ValueError):
                agc.validate()
        with self.assertRaises(ValueError):
            assemble_agc_state_matrix(self.stand, self.bite, SPANS, SPEED, {'alpha': 0.5})

    def test_call_validation(self):
        agc = GaugemeterAGC(0.5, 25.0)
        with self.assertRaises(ValueError):
            agc_frequency_response(self.stand, self.bite, SPANS, SPEED, agc, [1.0],
                                   disturbance='gear')
        with self.assertRaises(ValueError):
            agc_frequency_response(self.stand, self.bite, SPANS, SPEED, agc, [0.0])
        with self.assertRaises(ValueError):
            agc_frequency_response(self.stand, self.bite, SPANS, 0.0, agc, [1.0])
        with self.assertRaises(ValueError):
            agc_stability(self.stand, self.bite, SPANS, SPEED, agc, speed_range_m_s=(2.0, 1.0))
        with self.assertRaises(ValueError):
            speed_change_gauge_shift(1e7, 0.01, 0.0, 1e10)
        with self.assertRaises(ValueError):
            hardness_gauge_shift(1e-2, 1e6, 5e9, 1e10, 1.5)
        with self.assertRaises(ValueError):
            flow_stress_sensitivity(REFERENCE, relative_step=0.5, cells=64)
        with self.assertRaises(ValueError):
            friction_force_sensitivity('not a pass')

    def test_json_and_status(self):
        agc = GaugemeterAGC(0.9, 25.0, 25.0)
        for dist in ('work_backup_runout', 'entry_thickness', 'roll_speed'):
            r = agc_frequency_response(self.stand, self.bite, SPANS, SPEED, agc, [5.0, 180.0],
                                       disturbance=dist)
            _json_ok(self, r)
            self.assertEqual(r['status'], 'UNVALIDATED_LINEAR_MILL_DYNAMICS_SCREEN')
            self.assertIn('ANALYST_FORCE_FILTER_OPTION_NOT_FROM_CITED_SOURCE', r['flags'])
            self.assertTrue(r['limitations'])
            self.assertIn('basis', r)
        self.assertIn('CYLINDER_BANDWIDTH_OUTSIDE_CITED_20_30_HZ', agc_frequency_response(
            self.stand, self.bite, SPANS, SPEED, GaugemeterAGC(0.5, 5.0), [1.0])['flags'])


if __name__ == '__main__':
    unittest.main()
