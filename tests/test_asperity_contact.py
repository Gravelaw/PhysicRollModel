"""Published asperity-contact and flow-factor fits (``physicroll.asperity_contact``).

Checks of the transcriptions against the planner's function checks (SPEC18 package 6) and the
values the sources quote. They are tested, not assembled: nothing in the engine imports the
module, and the crushing laws disagree away from one point (benchmark BT-G3-CRUSHING-LAWS).
"""
import unittest

from physicroll import asperity_contact as ac


class FitTests(unittest.TestCase):

    def test_christensen_density(self):
        self.assertEqual(ac.christensen_contact_ratio(0.0), 0.5)
        self.assertEqual(ac.christensen_contact_ratio(-3.0), 1.0)
        self.assertEqual(ac.christensen_contact_ratio(3.0), 0.0)
        self.assertEqual(ac.christensen_mean_film_over_rq(0.0), 0.41015625)
        self.assertAlmostEqual(ac.christensen_mean_film_over_rq(3.0), 3.0, places=12)
        self.assertEqual(ac.christensen_mean_film_over_rq(-3.0), 0.0)
        vals = [ac.christensen_contact_ratio(h / 10) for h in range(-30, 31)]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_wilson_sheu_hardness_and_strain_rate(self):
        self.assertAlmostEqual(ac.hardness_wilson_sheu_no_bulk(0.0), 5.142, places=12)
        self.assertAlmostEqual(ac.hardness_wilson_sheu_no_bulk(0.5), 4.835147, places=6)
        self.assertAlmostEqual(ac.plastic_strain_rate_wilson_sheu(0.5, 2.0), 1.240978, places=6)

    def test_crushing_rates_quoted_in_the_brief(self):
        def w(law, a, p):
            if law == 'thesis':
                return ac.crushing_rate_thesis(a, p)
            h = ac.hardness_from_mean_pressure(a, p)
            fn = {'marsault': ac.plastic_strain_rate_marsault,
                  'wilson_sheu': ac.plastic_strain_rate_wilson_sheu,
                  'korzekwa': ac.plastic_strain_rate_korzekwa}[law]
            return ac.crushing_rate_from_strain_rate(fn(a, h))
        table = {(0.5, 1.0): (1.62, 1.62, 5.47, 1.76),
                 (0.5, 0.6): (0.05, 0.583, 1.126, 0.587),
                 (0.3, 0.6): (0.058, 0.899, 6.81, 2.23)}
        for (a, p), expected in table.items():
            for law, want in zip(('thesis', 'marsault', 'wilson_sheu', 'korzekwa'), expected):
                self.assertAlmostEqual(w(law, a, p), want, delta=0.006, msg=(law, a, p))
        self.assertEqual(ac.crushing_rate_thesis(0.5, 0.5), 0.05)       # clipped
        self.assertEqual(ac.crushing_rate_thesis(0.1, 1.0), 2.5)
        with self.assertRaises(ValueError):
            ac.plastic_strain_rate_marsault(0.9, 3.0)     # bracket negative above 0.87
        with self.assertRaises(ValueError):
            ac.plastic_strain_rate_korzekwa(1.0, 3.0)

    def test_flow_factors(self):
        self.assertAlmostEqual(ac.percolation_film_over_rq(9.0), 0.0383191, places=7)
        self.assertAlmostEqual(ac.pressure_flow_factor(3.0, 9.0), 1.165667, places=6)
        self.assertAlmostEqual(ac.pressure_flow_factor(3.0, 1.0), 0.832857, places=6)
        self.assertEqual(ac.STATUS, 'PUBLISHED_FITS_TRANSCRIBED_NOT_ASSEMBLED_INTO_A_MODEL')

    def test_not_imported_by_the_engine(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1] / 'physicroll'
        users = [p.name for p in root.glob('*.py')
                 if p.name not in ('asperity_contact.py', 'benchmarks.py')
                 and any(t in p.read_text(encoding='utf-8')
                         for t in ('import asperity_contact', 'from .asperity_contact',
                                   'asperity_contact import'))]
        self.assertEqual(users, [])


if __name__ == '__main__':
    unittest.main()
