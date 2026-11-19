"""Verification of the linear gauge-chatter screen against closed forms (stdlib only).

Software verification only: none of these checks validates the model against a mill.
"""
from dataclasses import replace
import cmath
import json
import math
import unittest

from physicroll.chatter import (BitePass, BiteResponse, StandModel, StripSpans, STATE_NAMES,
                                assemble_state_matrix, critical_speed, derive_bite_response,
                                eigenvalues, frequency_response, natural_frequencies,
                                simulate, stability)
from physicroll.contact import CircularRollElasticity, solve_circular_contact
from physicroll.model import Scenario


def _det(matrix):
    """Determinant by Gaussian elimination with partial pivoting (real or complex)."""
    a = [list(r) for r in matrix]
    n, det = len(a), 1
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        if a[p][c] == 0:
            return 0
        if p != c:
            a[c], a[p] = a[p], a[c]
            det = -det
        det *= a[c][c]
        for r in range(c + 1, n):
            f = a[r][c] / a[c][c]
            for k in range(c, n):
                a[r][k] -= f * a[c][k]
    return det


def _norm(matrix):
    return math.sqrt(sum(abs(v) ** 2 for row in matrix for v in row))


def _poly_from_roots(roots):
    """Monic coefficients [1, c1, ..., cn] of prod(s - r)."""
    coeffs = [1 + 0j]
    for r in roots:
        coeffs = [a - r * b for a, b in zip(coeffs + [0], [0] + coeffs)]
    return [c.real for c in coeffs]


def _match(found, expected):
    """Max |found - expected| after greedy nearest matching."""
    rest, worst = list(expected), 0.0
    for z in found:
        j = min(range(len(rest)), key=lambda k: abs(rest[k] - z))
        worst = max(worst, abs(rest.pop(j) - z))
    return worst


ORIENTATION = BitePass(0.6e-3, 0.42e-3, 1.5, 0.2, 250e6, 0.05, 25e6, 30e6)


def _stand(zeta=0.03):
    return StandModel.from_modal_damping(3000.0, 22000.0, 4e10, 1.4e10, zeta)


SPANS = StripSpans(70e9, 4.0, 4.0)


def _json_ok(test, value):
    test.assertIsInstance(json.dumps(value, allow_nan=False), str)


class EigenvalueTests(unittest.TestCase):
    def check_invariants(self, a, eigs, tol=1e-9):
        n = len(a)
        self.assertEqual(len(eigs), n)
        scale = _norm(a) + 1e-300
        trace = sum(a[i][i] for i in range(n))
        self.assertLessEqual(abs(sum(eigs) - trace), tol * scale * n)
        prod = 1
        for z in eigs:
            prod *= z
        self.assertLessEqual(abs(prod - _det(a)), tol * n * (scale ** n))
        for z in eigs:
            shifted = [[a[i][j] - (z if i == j else 0) for j in range(n)] for i in range(n)]
            self.assertLessEqual(abs(_det(shifted)), tol * (scale + abs(z)) ** n)

    def test_diagonal(self):
        a = [[3.0, 0, 0], [0, -2.0, 0], [0, 0, 7.5]]
        eigs = eigenvalues(a)
        self.assertLess(_match(eigs, [3, -2, 7.5]), 1e-14)
        self.check_invariants(a, eigs)

    def test_rotation_block_gives_conjugate_pair(self):
        w = 1234.5
        a = [[0.0, w, 0], [-w, 0.0, 0], [0, 0, -1.0]]
        eigs = eigenvalues(a)
        self.assertLess(_match(eigs, [1j * w, -1j * w, -1]), 1e-9 * w)
        pair = sorted((z for z in eigs if z.imag != 0), key=lambda z: z.imag)
        self.assertEqual(pair[0], pair[1].conjugate())  # exact conjugates from real QR
        self.check_invariants(a, eigs)

    def test_companion_matrix_of_known_polynomial(self):
        roots = [1.0, -2.0, 3 + 4j, 3 - 4j, -0.5 + 10j, -0.5 - 10j, 0.25]
        c = _poly_from_roots(roots)
        n = len(roots)
        a = [[0.0] * n for _ in range(n)]
        a[0] = [-v for v in c[1:]]
        for i in range(1, n):
            a[i][i - 1] = 1.0
        eigs = eigenvalues(a)
        self.assertLess(_match(eigs, roots), 1e-8)
        self.check_invariants(a, eigs)

    def test_defective_and_ill_scaled(self):
        jordan = [[2.0, 1.0, 0], [0, 2.0, 1.0], [0, 0, 2.0]]
        jordan[2][0] = 1e-12        # perturbed Jordan block: roots 2 + 1e-4 * cube roots of 1
        eigs = eigenvalues(jordan)
        self.assertLess(_match(eigs, [2 + 1e-4 * cmath.exp(2j * math.pi * k / 3)
                                      for k in range(3)]), 1e-8)
        self.check_invariants(jordan, eigs, tol=1e-9)
        # physical, unscaled chatter matrix (entries ~1e-1 .. 1e14) vs scaled similarity
        bite = derive_bite_response_cached()
        a = assemble_state_matrix(_stand(), bite, SPANS, 10.0)
        raw = eigenvalues(a)
        scales = [1e-6, 1e-3, 1e-6, 1e-3, 1e6, 1e6]
        scaled = eigenvalues([[a[i][j] * scales[j] / scales[i] for j in range(6)]
                              for i in range(6)])
        big = max(abs(z) for z in scaled)
        self.assertLess(_match(raw, scaled), 1e-9 * big)
        self.assertLess(abs(sum(raw) - sum(a[i][i] for i in range(6))), 1e-9 * big)

    def test_rejects_bad_input(self):
        for bad in ([], [[1.0, 2.0]], [[float('nan')]], [[True]], [[0.0] * 13] * 13):
            with self.assertRaises(ValueError):
                eigenvalues(bad)


_CACHE = {}


def derive_bite_response_cached(bite_pass=ORIENTATION, **kw):
    key = (bite_pass, tuple(sorted(kw.items())))
    if key not in _CACHE:
        _CACHE[key] = derive_bite_response(bite_pass, **kw)
    return _CACHE[key]


def _supplied(q, n_tension, slip=0.05, length=6e-3, h0=0.6e-3, h1=0.42e-3):
    """Single-DOF benchmark bite: only F_h and F_se nonzero."""
    return BiteResponse(3e6, slip, length, 1.0, h0, h1, -q, 0.0, -n_tension, 0.0,
                        0.0, 0.0, 0.0, 0.0, 'supplied')


class SingleDofBenchmarkTests(unittest.TestCase):
    """Section 1.5. With K_h -> inf (1e7*K_wb) the backup roll is clamped and the half stack
    reduces to the work roll on K_wb, C_wb: in gap coordinates h = 2*x_w,
    M = M_w/2, C = C_wb/2, K = K_wb/2 (error O(K_wb/K_h) = 1e-7).

    Derivation: M h'' + (C+D) h' + (K+Q) h + N sigma = 0, sigma' = (E/L)(u/h0) h gives
    a3 s^3 + a2 s^2 + a1 s + a0 with a3 = M, a2 = C+D, a1 = K+Q, a0 = N E u/(L h0).
    Routh-Hurwitz (all a_i > 0): stable iff a2*a1 > a3*a0. On the boundary s = j*w is a root,
    so w^2 = a1/a3 = (K+Q)/M independent of D. With D = 0:
        u_crit = C (K+Q) L h0 / (M N E).
    With D = D0/u (D0 = Q*beta*l_d): (C + D0/u)(K+Q) = M N E u/(L h0); with
    kappa = (K+Q) L h0/(M N E): u^2 - C kappa u - D0 kappa = 0, so
        u_crit = [C kappa + sqrt((C kappa)^2 + 4 D0 kappa)]/2   (positive root)
    which confirms the form quoted in the spec. Here u is the strip exit speed u_x, both in
    the continuity term (u_x/h0) and in the bite damping closure.
    """

    m, k, zeta = 3000.0, 4e10, 0.03
    q, n_tension, h0, length = 1.2e10, 1.2e-2, 0.6e-3, 6e-3
    spans = StripSpans(70e9, 4.0, 4.0)

    @classmethod
    def setUpClass(cls):
        c = 2 * cls.zeta * math.sqrt(cls.k * cls.m)
        cls.stand = StandModel(cls.m, 22000.0, cls.k, 1e7 * cls.k, c, 0.0)
        cls.bite = _supplied(cls.q, cls.n_tension, length=cls.length, h0=cls.h0)
        cls.M, cls.C, cls.K = cls.m / 2, c / 2, cls.k / 2
        cls.kappa = (cls.K + cls.q) * 4.0 * cls.h0 / (cls.M * cls.n_tension * 70e9)

    def test_critical_speed_and_onset_frequency_without_bite_damping(self):
        expected = self.C * self.kappa
        omega = math.sqrt((self.K + self.q) / self.M)
        r = critical_speed(self.stand, self.bite, self.spans, bite_damping_transit_fraction=0.0)
        self.assertEqual(r['status'], 'UNSTABLE_ABOVE_CRITICAL_SPEED')
        self.assertAlmostEqual(r['critical_exit_speed_m_s'] / expected, 1, delta=1e-3)
        self.assertAlmostEqual(r['onset_frequency_hz'] / (omega / (2 * math.pi)), 1, delta=1e-3)
        below = stability(self.stand, self.bite, self.spans, 0.99 * expected,
                          bite_damping_transit_fraction=0.0)
        above = stability(self.stand, self.bite, self.spans, 1.01 * expected,
                          bite_damping_transit_fraction=0.0)
        self.assertTrue(below['stable'])
        self.assertFalse(above['stable'])
        # the exit-tension state is neutral (all slip sensitivities zero) and is reported
        self.assertIn('NEUTRAL_ZERO_MODE_EXCLUDED_FROM_GROWTH_RATE', below['flags'])
        _json_ok(self, r)
        _json_ok(self, below)

    def test_critical_speed_with_bite_damping(self):
        beta = 0.5
        d0 = self.q * beta * self.length
        ck = self.C * self.kappa
        expected = (ck + math.sqrt(ck * ck + 4 * d0 * self.kappa)) / 2
        r = critical_speed(self.stand, self.bite, self.spans, bite_damping_transit_fraction=beta)
        self.assertAlmostEqual(r['critical_exit_speed_m_s'] / expected, 1, delta=1e-3)
        omega = math.sqrt((self.K + self.q) / self.M)
        self.assertAlmostEqual(r['onset_frequency_hz'] / (omega / (2 * math.pi)), 1, delta=1e-3)
        self.assertAlmostEqual(r['without_bite_damping']['critical_exit_speed_m_s'] / ck, 1,
                               delta=1e-3)
        self.assertTrue(stability(self.stand, self.bite, self.spans, 0.99 * expected)['stable'])
        self.assertFalse(stability(self.stand, self.bite, self.spans, 1.01 * expected)['stable'])

    def test_cubic_coefficients_reproduced(self):
        """Characteristic polynomial of the assembled 6x6 equals cubic * clamped factors."""
        u = 3.0
        eigs = stability(self.stand, self.bite, self.spans, u,
                         bite_damping_transit_fraction=0.0)['modes']
        a0 = self.n_tension * 70e9 * u / (4.0 * self.h0)
        roots = [complex(m['real_per_s'], m['imag_rad_s']) for m in eigs]
        roots += [z.conjugate() for z in roots if z.imag > 0]
        # the cubic's roots are those lambda with |cubic(lambda)| ~ 0
        cubic = [r for r in roots
                 if abs(self.M * r ** 3 + self.C * r ** 2 + (self.K + self.q) * r + a0)
                 <= 1e-6 * (self.M * abs(r) ** 3 + a0)]
        self.assertEqual(len(cubic), 3)


class NaturalFrequencyTests(unittest.TestCase):
    def test_closed_form_matches_eigenvalues(self):
        undamped = _stand(0.0)
        bite = derive_bite_response_cached()
        unloaded = natural_frequencies(undamped)
        a = assemble_state_matrix(undamped, None, SPANS, 1.0, couple_tension=False)
        freqs = sorted(abs(z.imag) / (2 * math.pi) for z in eigenvalues(a) if z.imag > 0)
        self.assertEqual(len(freqs), 2)
        for got, want in zip(freqs, unloaded['symmetric_hz']):
            self.assertAlmostEqual(got / want, 1, delta=1e-10)
        self.assertEqual(unloaded['symmetric_hz'], unloaded['antisymmetric_hz'])
        # undamped closed-form values for M_w=3 t, M_b=22 t, K_wb=4e10, K_h=1.4e10
        self.assertAlmostEqual(unloaded['symmetric_hz'][0], 118.790, delta=0.01)
        self.assertAlmostEqual(unloaded['symmetric_hz'][1], 621.128, delta=0.01)
        loaded = natural_frequencies(undamped, bite.strip_modulus_n_m)
        r = stability(undamped, bite, SPANS, 5.0, bite_damping_transit_fraction=0.0,
                      couple_tension=False)
        osc = sorted(m['frequency_hz'] for m in r['modes'] if m['frequency_hz'] > 0)
        for got, want in zip(osc, loaded['symmetric_hz']):
            self.assertAlmostEqual(got / want, 1, delta=1e-9)
        self.assertEqual(loaded['antisymmetric_hz'], unloaded['antisymmetric_hz'])
        self.assertEqual(loaded['fifth_octave_candidate_hz'], unloaded['antisymmetric_hz'][1])
        _json_ok(self, loaded)

    def test_prototype_values_are_damped_frequencies(self):
        """The spec's 118.74/620.79 Hz are the prototype's 3 %-damped eigenvalue imag parts,
        not the undamped values (118.79/621.13 Hz)."""
        a = assemble_state_matrix(_stand(0.03), None, SPANS, 1.0, couple_tension=False)
        freqs = sorted(z.imag / (2 * math.pi) for z in eigenvalues(a) if z.imag > 0)
        self.assertAlmostEqual(freqs[0], 118.74, delta=0.01)
        self.assertAlmostEqual(freqs[1], 620.79, delta=0.01)

    def test_mill_modulus(self):
        self.assertAlmostEqual(_stand().mill_modulus_n_m,
                               1 / (2 * (1 / 4e10 + 1 / 1.4e10)), delta=1)


class BiteDerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = derive_bite_response_cached()
        cls.thin = derive_bite_response_cached(BitePass(0.4e-3, 0.28e-3, 1.5, 0.2, 260e6, 0.05,
                                                        25e6, 30e6))

    def test_orientation_numbers(self):
        b = self.base
        self.assertEqual(b.source, 'derived_slab_hitchcock')
        for got, want in ((b.separating_force_n, 3.56e6), (b.contact_radius_ratio, 1.29),
                          (b.forward_slip_fraction, 0.0553), (b.strip_modulus_n_m, 12.2e9),
                          (-b.dforce_dentry_tension_m2, 1.21e-2)):
            self.assertAlmostEqual(got / want, 1, delta=0.01)
        self.assertNotIn('SENSITIVITY_STEP_NOT_CONVERGED', b.flags)
        self.assertNotIn('GRID_REFINEMENT_NOT_MET', b.flags)
        self.assertNotIn('THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN', b.flags)
        _json_ok(self, b.to_dict())

    def test_sensitivity_signs(self):
        for b in (self.base, self.thin):
            self.assertLess(b.dforce_dexit_thickness_n_m, 0)
            self.assertGreater(b.dforce_dentry_thickness_n_m, 0)
            self.assertLess(b.dforce_dentry_tension_m2, 0)
            self.assertLess(b.dforce_dexit_tension_m2, 0)
            self.assertLess(b.dslip_dentry_tension_per_pa, 0)   # back tension lowers slip
            self.assertGreater(b.dslip_dexit_tension_per_pa, 0)  # front tension raises slip
            self.assertGreater(b.dslip_dentry_thickness_per_m, 0)  # larger draft, more slip

    def test_force_matches_independent_contact_solver(self):
        p = ORIENTATION
        s = Scenario('check', True, p.entry_thickness_m, p.exit_thickness_m, p.width_m, 1.0,
                     p.work_roll_radius_m, 2700.0, p.mean_flow_stress_pa,
                     p.friction_coefficient, p.entry_tension_pa, p.exit_tension_pa, 1.0)
        s.validate()   # >= 300 micrometre case is inside the reviewed scenario domain
        ref = solve_circular_contact(s, CircularRollElasticity(210e9, 0.3, 'test'), 256,
                                     bite_mode='established', verify_refinement=False,
                                     radius_tolerance=1e-10, max_iterations=300)
        self.assertTrue(ref['flattening']['converged'])
        self.assertAlmostEqual(self.base.separating_force_n / ref['separating_force_n'], 1,
                               delta=1e-8)
        self.assertAlmostEqual(self.base.forward_slip_fraction, ref['forward_slip_fraction'],
                               delta=1e-9)
        self.assertAlmostEqual(self.base.contact_radius_ratio * p.work_roll_radius_m,
                               ref['contact_radius_m'], delta=1e-10)

    def test_thin_gauge_flag(self):
        self.assertIn('THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN', self.thin.flags)
        self.assertLess(self.thin.contact_radius_ratio, 1.5)

    def test_radius_envelope(self):
        foil = BitePass(0.3e-3, 0.21e-3, 1.5, 0.2, 270e6, 0.05, 25e6, 30e6)
        with self.assertRaisesRegex(ValueError, 'foil'):
            derive_bite_response(foil)
        raised = derive_bite_response_cached(foil, max_radius_ratio=2.0)
        self.assertGreater(raised.contact_radius_ratio, 1.5)
        self.assertIn('HITCHCOCK_RATIO_BEYOND_REVIEWED_ENVELOPE', raised.flags)
        with self.assertRaises(ValueError):
            derive_bite_response(foil, max_radius_ratio=3.5)

    def test_domain_checks(self):
        # SPEC12 stage A: the BitePass domain is exit >= 8 um and reduction <= 0.65
        bad = [replace(ORIENTATION, exit_thickness_m=5e-6, entry_thickness_m=7e-6),
               replace(ORIENTATION, exit_thickness_m=0.595e-3),        # 0.8 % reduction
               replace(ORIENTATION, exit_thickness_m=0.18e-3),         # 70 % reduction
               replace(ORIENTATION, friction_coefficient=0.0),
               replace(ORIENTATION, friction_coefficient=0.31),
               replace(ORIENTATION, entry_tension_pa=-1.0),
               replace(ORIENTATION, exit_tension_pa=250e6),
               replace(ORIENTATION, width_m=True),
               replace(ORIENTATION, work_roll_radius_m=float('inf')),
               replace(ORIENTATION, work_roll_radius_m=0.01),          # h0/R > 0.05
               replace(ORIENTATION, width_m=0.01)]                     # width/h0 < 20
        for p in bad:
            with self.assertRaises(ValueError, msg=str(p)):
                p.validate()
        for cells in (32, 5000, 256.0, True):
            with self.assertRaises(ValueError):
                derive_bite_response(ORIENTATION, cells=cells)
        # the slab/Hitchcock derivation keeps its own 20 um exit floor
        thin = replace(ORIENTATION, entry_thickness_m=30e-6, exit_thickness_m=18e-6)
        thin.validate()
        with self.assertRaisesRegex(ValueError, 'slab/Hitchcock bite domain'):
            derive_bite_response(thin)

    def test_supplied_response_validation(self):
        good = _supplied(1e10, 1e-2)
        good.validate()
        self.assertEqual(good.to_dict()['source'], 'supplied')
        for change in ({'dforce_dexit_thickness_n_m': 1e9}, {'separating_force_n': float('nan')},
                       {'contact_length_m': 0.0}, {'source': 'plant'},
                       {'exit_thickness_m': 0.7e-3}, {'contact_radius_ratio': 0.9},
                       {'dslip_dexit_tension_per_pa': True}, {'flags': ['X']}):
            with self.assertRaises(ValueError, msg=str(change)):
                replace(good, **change).validate()
        with self.assertRaises(ValueError):
            stability(_stand(), replace(good, separating_force_n=-1.0), SPANS, 1.0)


class ExtendedReductionDomainTests(unittest.TestCase):
    """SPEC12 stage A: reductions up to 0.65; slab + Hitchcock is continuous across 0.5."""

    def test_continuity_across_50_percent(self):
        out = {}
        for r in (0.48, 0.50, 0.52):
            p = replace(ORIENTATION, exit_thickness_m=0.6e-3 * (1 - r))
            out[r] = derive_bite_response(p, cells=128)
        f = {r: b.separating_force_n for r, b in out.items()}
        q = {r: b.strip_modulus_n_m for r, b in out.items()}
        for v in (f, q):
            self.assertLess(v[0.48], v[0.50])
            self.assertLess(v[0.50], v[0.52])
            # smooth: the second difference is small against the first difference
            self.assertLess(abs(v[0.52] - 2 * v[0.50] + v[0.48]), 0.1 * (v[0.52] - v[0.48]))
        self.assertIn('REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN', out[0.52].flags)
        self.assertNotIn('REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN', out[0.50].flags)
        for b in out.values():
            self.assertNotIn('SENSITIVITY_STEP_NOT_CONVERGED', b.flags)

    def test_published_57_percent_sheet_pass_solves(self):
        b = derive_bite_response(replace(ORIENTATION, exit_thickness_m=0.26e-3), cells=128)
        self.assertIn('REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN', b.flags)
        self.assertGreater(b.forward_slip_fraction, 0)
        with self.assertRaises(ValueError):
            replace(ORIENTATION, exit_thickness_m=0.6e-3 * 0.34).validate()   # 66 %


class CriticalSpeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = derive_bite_response_cached()
        cls.low_mu = derive_bite_response_cached(replace(ORIENTATION, friction_coefficient=0.02))
        cls.high_red = derive_bite_response_cached(replace(ORIENTATION, exit_thickness_m=0.39e-3))
        cls.high_se = derive_bite_response_cached(replace(ORIENTATION, entry_tension_pa=50e6))
        cls.ref = critical_speed(_stand(), cls.base, SPANS)

    def crit(self, bite=None, stand=None, spans=SPANS, beta=0.5):
        return critical_speed(stand or _stand(), bite or self.base, spans,
                              bite_damping_transit_fraction=beta)['critical_exit_speed_m_s']

    def test_orientation_case(self):
        r = self.ref
        self.assertEqual(r['status'], 'UNSTABLE_ABOVE_CRITICAL_SPEED')
        self.assertAlmostEqual(r['critical_exit_speed_m_s'] / 15.2, 1, delta=0.02)
        self.assertAlmostEqual(r['without_bite_damping']['critical_exit_speed_m_s'] / 5.07, 1,
                               delta=0.02)
        self.assertAlmostEqual(r['onset_frequency_hz'] / 179, 1, delta=0.02)
        self.assertAlmostEqual(r['onset_strip_pitch_m'],
                               r['critical_exit_speed_m_s'] / r['onset_frequency_hz'])
        self.assertFalse(r['restabilises_within_scan'])
        _json_ok(self, r)

    def test_trends(self):
        base = self.ref['critical_exit_speed_m_s']
        low_mu = self.crit(self.low_mu)
        self.assertLess(low_mu, base)
        self.assertAlmostEqual(low_mu / 7.1, 1, delta=0.02)
        self.assertGreater(self.crit(spans=StripSpans(70e9, 8.0, 4.0)), base)
        self.assertGreater(self.crit(stand=_stand(0.05)), base)
        self.assertLess(self.crit(self.high_red), base)
        self.assertLess(self.crit(self.high_se), base)
        for beta in (0.0, 0.5):   # damping trend holds without the bite-damping closure too
            self.assertGreater(self.crit(stand=_stand(0.05), beta=beta),
                               self.crit(beta=beta))

    def test_scan_statuses(self):
        stable = critical_speed(_stand(), self.base, SPANS, speed_range_m_s=(0.05, 4.0))
        self.assertEqual(stable['status'], 'STABLE_OVER_SCANNED_RANGE')
        self.assertIsNone(stable['critical_exit_speed_m_s'])
        unstable = critical_speed(_stand(), self.base, SPANS, speed_range_m_s=(20.0, 60.0))
        self.assertEqual(unstable['status'], 'UNSTABLE_AT_LOWEST_SCANNED_SPEED')
        self.assertGreaterEqual(unstable['scan_points'], 80)
        for bad in ((0.0, 1.0), (5.0, 1.0), (1.0,), (1.0, float('inf'))):
            with self.assertRaises(ValueError):
                critical_speed(_stand(), self.base, SPANS, speed_range_m_s=bad)
        with self.assertRaises(ValueError):
            critical_speed(_stand(), self.base, SPANS, bite_damping_transit_fraction=-0.1)
        with self.assertRaises(TypeError):
            critical_speed(_stand(), self.base, SPANS, unknown_option=1)

    def test_stability_result_shape(self):
        r = stability(_stand(), self.base, SPANS, 10.0)
        self.assertEqual(r['state_names'], list(STATE_NAMES))
        self.assertTrue(r['stable'])
        self.assertIn('without_bite_damping', r)
        self.assertFalse(r['without_bite_damping']['stable'])   # 10 m/s > 5.07 m/s
        for m in r['modes']:
            self.assertEqual(set(m), {'real_per_s', 'imag_rad_s', 'frequency_hz',
                                      'damping_ratio'})
        self.assertAlmostEqual(r['strip_pitch_m'], 10.0 / r['dominant_frequency_hz'])
        _json_ok(self, r)


class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bite = derive_bite_response_cached()

    def test_trace_matches_eigenvalues(self):
        for u in (3.0, 8.0):     # below and above the beta = 0 critical speed (5.07 m/s)
            r = simulate(_stand(), self.bite, SPANS, u, duration_s=0.3,
                         bite_damping_transit_fraction=0.0)
            s = stability(_stand(), self.bite, SPANS, u, bite_damping_transit_fraction=0.0)
            self.assertEqual(s['stable'], u < 5.0)
            self.assertAlmostEqual(r['growth_rate_per_s'] / s['dominant_growth_rate_per_s'], 1,
                                   delta=0.02)
            self.assertAlmostEqual(r['dominant_frequency_hz'] / s['dominant_frequency_hz'], 1,
                                   delta=0.02)
            self.assertFalse(r['linear_range_exceeded'])
            self.assertLessEqual(len(r['time_s']), 4000)
            self.assertAlmostEqual(r['strip_position_m'][-1], u * r['time_s'][-1])
            _json_ok(self, r)

    def test_undamped_decoupled_conserves_amplitude(self):
        r = simulate(StandModel(3000.0, 22000.0, 4e10, 1.4e10, 0.0, 0.0), self.bite, SPANS, 5.0,
                     duration_s=0.1, bite_damping_transit_fraction=0.0, couple_tension=False)
        # exact modal solution: x = sum_i a_i phi_i cos(w_i t), phi_i = [K_wb, K11 - w_i^2 M_w]
        # (components x_w, x_b), with x(0) = [dh0/2, 0], v(0) = 0; no amplitude may be lost.
        kwb, mw, q = 4e10, 3000.0, self.bite.strip_modulus_n_m
        k11 = kwb + 2 * q
        omegas = [2 * math.pi * f for f in natural_frequencies(StandModel(
            3000.0, 22000.0, 4e10, 1.4e10, 0.0, 0.0), q)['symmetric_hz']]
        phi = [(kwb, k11 - w * w * mw) for w in omegas]
        det = phi[0][0] * phi[1][1] - phi[1][0] * phi[0][1]
        amp = [0.5e-7 * phi[1][1] / det, -0.5e-7 * phi[0][1] / det]
        for t, x in zip(r['time_s'][-50:], r['exit_thickness_perturbation_m'][-50:]):
            exact = 2 * sum(a * p[0] * math.cos(w * t) for a, p, w in zip(amp, phi, omegas))
            # RK4 phase error after ~1e4 steps of h*w <= 0.05 is ~1e-5 rad; amplitude is kept
            self.assertAlmostEqual(x, exact, delta=1e-4 * 1e-7)
        self.assertLess(abs(r['growth_rate_per_s']), 1e-4 * 2 * math.pi * 118)
        self.assertEqual(max(map(abs, r['entry_tension_perturbation_pa'])), 0.0)

    def test_linear_range_exceeded(self):
        r = simulate(_stand(), self.bite, SPANS, 12.0, duration_s=2.0,
                     bite_damping_transit_fraction=0.0)
        self.assertTrue(r['linear_range_exceeded'])
        self.assertIn('LINEAR_RANGE_EXCEEDED', r['flags'])
        self.assertLess(r['simulated_duration_s'], 2.0)
        limit = 0.2 * self.bite.exit_thickness_m
        self.assertLessEqual(max(map(abs, r['exit_thickness_perturbation_m'][:-1])), limit)
        _json_ok(self, r)

    def test_forcing_and_validation(self):
        r = simulate(_stand(), self.bite, SPANS, 3.0, duration_s=0.05,
                     initial_gap_perturbation_m=0.0,
                     forcing=({'disturbance': 'work_backup_runout', 'amplitude_m': 1e-7,
                               'frequency_hz': 50.0, 'phase_rad': 0.0},))
        self.assertGreater(max(map(abs, r['exit_thickness_perturbation_m'])), 0)
        for bad in ({'disturbance': 'bearing'}, {'disturbance': 'entry_thickness',
                                                 'amplitude_m': 1e-6, 'frequency_hz': -1.0}):
            with self.assertRaises(ValueError):
                simulate(_stand(), self.bite, SPANS, 3.0, duration_s=0.01, forcing=(bad,))
        with self.assertRaises(ValueError):
            simulate(_stand(), self.bite, SPANS, 3.0, duration_s=0.0)


class FrequencyResponseTests(unittest.TestCase):
    """Static limit, coupling off. Equilibrium of one half stack with run-out e:
        0 = -K_wb (x_w - x_b + e) + 2 F_h x_w,   0 = K_wb (x_w - x_b + e) - K_h x_b.
    The contact load P = K_wb (x_w - x_b + e) = -2 Q_s x_w = K_h x_b, so
        x_w = P/K_wb + P/K_h - e = -2 Q_s x_w / K_s - e,   K_s = K_wb K_h/(K_wb + K_h),
        x_w = -e K_s/(K_s + 2 Q_s),
        dh/e = 2 x_w/e = -2 K_s/(K_s + 2 Q_s) = -2 K_mill/(K_mill + Q_s)  (K_mill = K_s/2).
    Magnitude 2 K_mill/(K_mill+Q_s): the gaugemeter attenuation applied to the gap
    disturbance 2e (run-out at both the upper and the lower contact); phase pi (the gap
    closes). Entry gauge ripple: dh/dh_in = F_hin/(K_mill + Q_s), phase 0.
    """

    @classmethod
    def setUpClass(cls):
        cls.bite = derive_bite_response_cached()
        cls.stand = _stand()

    def test_static_limits(self):
        km, q = self.stand.mill_modulus_n_m, self.bite.strip_modulus_n_m
        r = frequency_response(self.stand, self.bite, SPANS, 10.0, [1e-3],
                               couple_tension=False)[0]
        self.assertAlmostEqual(r['exit_thickness_per_unit_disturbance'] / (2 * km / (km + q)), 1,
                               delta=1e-6)
        self.assertAlmostEqual(abs(r['phase_rad']), math.pi, delta=1e-4)
        r = frequency_response(self.stand, self.bite, SPANS, 10.0, [1e-3],
                               disturbance='entry_thickness', couple_tension=False)[0]
        self.assertAlmostEqual(r['exit_thickness_per_unit_disturbance'] /
                               (self.bite.dforce_dentry_thickness_n_m / (km + q)), 1, delta=1e-6)
        self.assertAlmostEqual(r['phase_rad'], 0, delta=1e-4)

    def test_resonance_near_loaded_symmetric_modes(self):
        freqs = [50.0 + i for i in range(900)]
        rows = frequency_response(self.stand, self.bite, SPANS, 10.0, freqs,
                                  couple_tension=False, bite_damping_transit_fraction=0.0)
        mag = [r['exit_thickness_per_unit_disturbance'] for r in rows]
        peaks = [freqs[i] for i in range(1, len(mag) - 1) if mag[i - 1] < mag[i] > mag[i + 1]]
        sym = natural_frequencies(self.stand, self.bite.strip_modulus_n_m)['symmetric_hz']
        self.assertEqual(len(peaks), 2)
        for peak, mode in zip(peaks, sym):
            self.assertAlmostEqual(peak / mode, 1, delta=0.01)
        self.assertGreater(max(mag), 10 * mag[0])
        _json_ok(self, rows)

    def test_validation(self):
        with self.assertRaises(ValueError):
            frequency_response(self.stand, self.bite, SPANS, 10.0, [10.0], disturbance='gear')
        with self.assertRaises(ValueError):
            frequency_response(self.stand, self.bite, SPANS, 10.0, [0.0])
        with self.assertRaises(ValueError):
            frequency_response(self.stand, self.bite, SPANS, 10.0, [])


class ValidationAndSerialisationTests(unittest.TestCase):
    def test_input_validation(self):
        with self.assertRaises(ValueError):
            StandModel(3000.0, 22000.0, 4e10, 1.4e10, -1.0, 0.0).validate()
        with self.assertRaises(ValueError):
            StandModel(True, 22000.0, 4e10, 1.4e10, 0.0, 0.0).validate()
        with self.assertRaises(ValueError):
            StandModel.from_modal_damping(3000.0, 22000.0, 4e10, 1.4e10, 1.0)
        with self.assertRaises(ValueError):
            StripSpans(70e9, 0.0, 4.0).validate()
        with self.assertRaises(ValueError):
            natural_frequencies(_stand(), -1.0)
        bite = _supplied(1e10, 1e-2)
        with self.assertRaises(ValueError):
            stability(_stand(), bite, SPANS, 0.0)
        with self.assertRaises(ValueError):
            assemble_state_matrix(_stand(), bite, SPANS, 1.0, couple_tension=1)

    def test_assembled_matrix_entries(self):
        bite, stand = _supplied(1e10, 1e-2, slip=0.05, length=6e-3), _stand()
        u, beta = 4.0, 0.5
        a = assemble_state_matrix(stand, bite, SPANS, u, bite_damping_transit_fraction=beta)
        mw = stand.work_roll_mass_kg
        self.assertAlmostEqual(a[1][0], (-4e10 - 2e10) / mw)
        self.assertAlmostEqual(a[1][1], (-stand.work_backup_damping_n_s_m
                                         - 2 * 1e10 * beta * 6e-3 / u) / mw)
        self.assertAlmostEqual(a[1][4], -1e-2 / mw)
        # sigma_e' = (E/L_e) * V_r*(1+f)/h0 * 2 x_w = (E/L_e) * (u/h0) * dh
        self.assertAlmostEqual(a[4][0] / (70e9 / 4.0 * u / 0.6e-3 * 2), 1, delta=1e-12)
        self.assertEqual(a[5], [0.0] * 6)
        _json_ok(self, a)


if __name__ == '__main__':
    unittest.main()
