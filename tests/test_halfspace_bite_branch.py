"""Rule SLIP_CONSISTENCY of the reduced half-space bite (SPEC18 package 3, follow-up).

With a Newton budget of 40 per homotopy step, three passes reached a degenerate branch: zone F
of zero length, forward slip about 1e-10, load 8.6 to 12.5 times the mattress load, contact 1.3
to 2.4 times longer, the peak pressure near the roll centre line. It satisfies the discrete
equations because the rows of a zone of zero length hold trivially (the zero-slope row S2 then
measures no slope), but the exit contact zone is written with forward sliding friction while
the strip leaves at roll speed, and E1's structures always end with the forward-slip zone F
after the slip reversal at the peak. The rule rejects it; these tests show that the result
does not depend on the Newton budget. Software checks, not a validation.
"""
import math
import unittest

from physicroll import halfspace_bite as hb

YS = 230e6
Y_PUB = YS * math.sqrt(3) / 2
E_PUB = 230e9 * 0.91
AL = hb.ALUMINIUM_PLANE_STRAIN_MODULUS_PA


def _solve(args):
    h0, h1, r, y, mu, tb, tf, e, es = args
    return hb.solve_half_space_bite(h0, h1, 1.0, r, y, mu, tb, tf, roll_youngs_modulus_pa=e,
                                    strip_plane_strain_modulus_pa=es)


def _w_bar(force):
    return force * 230e9 / (0.089 * YS ** 2)
# The three cases on which a Newton budget of 40 per march step reached the degenerate branch
# (zone F of zero length, forward slip ~1e-10, load 8.6 to 12.5 times the mattress load).
BRANCH_CASES = {
    'demo_f2_30_18': ((30e-6, 18e-6, 0.135, 180e6, 0.03, 38e6, 42e6, 210e9, AL), 'A B E F',
                      3243884.8278453886),
    'published_es_40': ((20e-6, 15e-6, 0.089, Y_PUB, 0.03, 0.0, 0.0, E_PUB, 40e9), 'A B F',
                        1980502.5470322696),
    'published_es_160': ((20e-6, 15e-6, 0.089, Y_PUB, 0.03, 0.0, 0.0, E_PUB, 160e9), 'A B E F',
                         1860817.9985161491),
}


class DegenerateBranchTests(unittest.TestCase):
    """Rule SLIP_CONSISTENCY [the project's own rule, on E1 eq. (9a) and Appendix 2]: the
    result must not depend on the Newton budget of the march."""

    def setUp(self):
        self.saved = hb._MARCH_MAXIT

    def tearDown(self):
        hb._MARCH_MAXIT = self.saved

    def test_newton_budget_does_not_change_the_result(self):
        for budget in (20, 40, 80):
            hb._MARCH_MAXIT = budget
            for name, (args, structure, force) in BRANCH_CASES.items():
                r = _solve(args)
                self.assertEqual(r['zone_structure'], structure, (budget, name))
                self.assertLessEqual(abs(r['force_per_width_n_m'] / force - 1), 1e-6,
                                     (budget, name, r['force_per_width_n_m']))
                self.assertGreater(r['forward_slip_fraction'], 0.2)

    def test_degenerate_state_is_rejected_by_name(self):
        """The degenerate branch reached without the rule (budget 40) is rejected by it."""
        hb._MARCH_MAXIT = 40
        original = hb._Problem.sliding_inconsistency
        captured = []

        def off(problem, u, q=None):
            captured.append((problem, list(u)))
            return ''
        hb._Problem.sliding_inconsistency = off
        try:
            r = _solve(BRANCH_CASES['published_es_160'][0])
        finally:
            hb._Problem.sliding_inconsistency = original
        self.assertLess(r['forward_slip_fraction'], 1e-6)          # the degenerate branch
        self.assertGreater(_w_bar(r['force_per_width_n_m']), 400)
        problem, u = captured[-1]
        reason = problem.sliding_inconsistency(u)
        self.assertTrue(reason.startswith('SLIP_CONSISTENCY'), reason)
        ok, why = hb._admissible(problem, u)
        self.assertFalse(ok)
        self.assertIn('SLIP_CONSISTENCY', why)


if __name__ == '__main__':
    unittest.main()
