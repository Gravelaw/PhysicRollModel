"""Review of 631195a (band_survey): a bite-free model that cannot run for an accepted
override value takes out only its own values and rankings, never the whole pass."""
import unittest

from physicroll import band_survey as bs

PID = 'can_body_stock'


def _run(override, products=(PID,)):
    r = bs.survey(products=list(products), overrides=bs.validate_overrides({PID: override}))
    rows = {x['product_id']: x for x in r['rows']}
    ranks = {x['mechanism']: x for x in r['rankings']}
    return r, rows, ranks


class SurveyGuardTests(unittest.TestCase):
    def test_reviewer_zero_exit_tension(self):
        r, rows, ranks = _run({'exit_tension_pa': 0})
        row = rows[PID]
        # before: REJECTED ("tension_stress_pa must be > 0") and dropped from every ranking
        self.assertEqual(row['bite_status'], 'BITE')
        self.assertNotIn('rejected', row)
        force = row['separating_force_per_width_n_m'] * r['mills'][row['mill']]['strip_width_m']
        self.assertAlmostEqual(force / 1e6, 1.68, delta=0.01)
        self.assertIsNone(row['trough_onset_lateral_stress_pa'])
        self.assertIsNone(row['roller_wrinkle_threshold_pa'])
        self.assertIn('must be > 0', row['trough_error'])
        self.assertIn('not assessable', row['trough_not_assessable_reason'])
        self.assertIsNotNone(row['critical_ridge_height_m'])
        self.assertIsNotNone(row['dead_band_half_width_i_units'])
        self.assertIsNotNone(row['stripe']['in_mill_onset_height_m'])
        for key in ('troughs', 'roller_wrinkles'):
            self.assertEqual(ranks[key]['most_sensitive_first'], [])
            self.assertIn('not assessable', ranks[key]['excluded'][0]['reason'])
        for key in ('coil_ridges', 'cooling_stripes_in_mill', 'cooling_stripes_after_release',
                    'chatter_margin'):
            self.assertEqual(len(ranks[key]['most_sensitive_first']), 1, key)
            self.assertEqual(ranks[key]['excluded'], [], key)
        self.assertIn('(trough onset lateral stress, magnitude): no product ranked; 1 excluded',
                      r['summary'])
        self.assertIn('not assessable: tension_stress_pa must be &gt; 0',
                      bs.render_survey_report(r))

    def test_only_the_overridden_product_is_excluded(self):
        r, rows, ranks = _run({'exit_tension_pa': 0}, products=(PID, 'litho_sheet'))
        for key in ('troughs', 'roller_wrinkles'):
            self.assertEqual([x['product_id'] for x in ranks[key]['most_sensitive_first']],
                             ['litho_sheet'])
            self.assertEqual([x['label'].split()[1] for x in ranks[key]['excluded']], [PID])
        self.assertEqual(len(ranks['coil_ridges']['most_sensitive_first']), 2)

    def test_zero_entry_tension_needs_no_guard(self):
        _, rows, ranks = _run({'entry_tension_pa': 0})
        row = rows[PID]
        self.assertEqual(row['bite_status'], 'BITE')
        self.assertNotIn('trough_error', row)
        self.assertTrue(all(len(x['most_sensitive_first']) == 1 for x in ranks.values()))

    def test_both_tensions_zero(self):
        _, rows, ranks = _run({'entry_tension_pa': 0, 'exit_tension_pa': 0})
        self.assertEqual(rows[PID]['bite_status'], 'BITE')
        self.assertEqual(ranks['troughs']['most_sensitive_first'], [])
        self.assertEqual(len(ranks['cooling_stripes_in_mill']['most_sensitive_first']), 1)

    def test_width_below_the_gauge(self):
        # the Shohet-Townsend window needs the gauge below the width: guarded on its own
        _, rows, ranks = _run({'width_m': 1e-4})
        row = rows[PID]
        self.assertNotEqual(row['bite_status'], 'REJECTED')
        self.assertIsNone(row['dead_band_half_width_i_units'])
        self.assertIn('width', row['dead_band_error'])
        self.assertIsNotNone(row['critical_ridge_height_m'])
        self.assertEqual(len(ranks['coil_ridges']['most_sensitive_first']), 1)

    def test_validation_unchanged(self):
        for bad in ({'exit_tension_pa': -1}, {'friction_coefficient': 0},
                    {'exit_speed_m_s': 0}, {'width_m': 0}):
            with self.assertRaises(ValueError):
                bs.validate_overrides({PID: bad})


if __name__ == '__main__':
    unittest.main()
