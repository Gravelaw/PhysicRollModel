"""Review of ad3f3dc (band_survey): a null critical speed is read from its scan status
(``band_survey.CHATTER_STATES``), never as 'stable'. An already-unstable product is the most
chatter-prone, listed apart from the ranked margins."""
import json
import pathlib
import tempfile
import unittest

from physicroll import band_survey as bs

PID = 'can_body_stock'


def _undamped_sheet_mill(path):
    # the default sheet mill with modal_damping_ratio 0 and bite_damping_transit_fraction 0,
    # as a mill file (the survey's own route for a changed machine); friction and speed kept
    c = bs.default_mill_case('sheet')
    c['stand']['modal_damping_ratio'] = 0.0
    c['model_options']['bite_damping_transit_fraction'] = 0.0
    c['pass']['friction_coefficient'] = bs.FRICTION
    c['pass']['exit_speed_m_s'] = bs.MILLS['sheet']['default_speed_m_s']
    pathlib.Path(path).write_text(json.dumps(c), encoding='utf-8')


class SurveyChatterStateTests(unittest.TestCase):
    def test_reviewer_already_unstable(self):
        with tempfile.TemporaryDirectory() as d:
            mill = pathlib.Path(d) / 'sheet.json'
            _undamped_sheet_mill(mill)
            r = bs.survey(products=[PID, 'litho_sheet'], sheet_mill=str(mill))
        row = {x['product_id']: x for x in r['rows']}[PID]
        self.assertEqual(row['critical_status_without_bite_damping'],
                         'UNSTABLE_AT_LOWEST_SCANNED_SPEED')
        lo = row['critical_speed_scan_range_m_s'][0]
        st = bs.chatter_state(row)
        self.assertEqual(st['state'], 'ALREADY_UNSTABLE')
        self.assertEqual(st['bound_m_s'], lo)
        self.assertTrue(st['margin_is_lower_bound'])
        self.assertAlmostEqual(st['margin'], row['exit_speed_m_s'] / lo)
        rk = {x['mechanism']: x for x in r['rankings']}['chatter_margin']
        ex = {x['label']: x['reason'] for x in rk['excluded']}
        # before: 'stable over the scanned speed range even without bite damping'
        self.assertIn('unstable from the lowest scanned speed', ex[row['label']])
        self.assertNotIn('stable over', ex[row['label']])
        self.assertIn(PID, [x['product_id'] for x in rk['already_unstable']])
        self.assertTrue(all(x['margin_lower_bound'] for x in rk['already_unstable']))
        self.assertNotIn(PID, [x['product_id'] for x in rk['most_sensitive_first']])
        self.assertIn('already unstable from the lowest scanned speed', r['summary'])
        cell = bs._chatter_cell(row)
        self.assertNotIn('stable over scan', cell)
        self.assertIn(f'below {lo:.3g} m/s', cell)
        self.assertIn('&gt;=', cell)

    def test_stable_over_scan_still_reads_stable(self):
        r = bs.survey(products=['battery_collector_foil'])
        row = r['rows'][0]
        self.assertEqual(row['critical_status'], 'STABLE_OVER_SCANNED_RANGE')
        self.assertEqual(bs.chatter_state(row, 'with')['state'], 'STABLE_OVER_SCAN')
        self.assertTrue(bs._chatter_cell(row).startswith('stable over scan / '))
        self.assertEqual(bs.chatter_state(row)['state'], 'CRITICAL_SPEED')

    def test_unknown_status_is_never_stable(self):
        r = bs.survey(products=[PID])
        row = dict(r['rows'][0], critical_status_without_bite_damping='SOMETHING_NEW',
                   critical_exit_speed_without_bite_damping_m_s=None,
                   speed_ratio_without_bite_damping=None)
        st = bs.chatter_state(row)
        self.assertEqual(st['state'], 'NOT_ASSESSABLE')
        self.assertIn('SOMETHING_NEW', st['text'])
        self.assertNotIn('stable over scan', bs._chatter_cell(row))
        rk = {x['mechanism']: x for x in bs.rankings([row])}['chatter_margin']
        self.assertIn('not assessable', rk['excluded'][0]['reason'])
        self.assertNotIn('already_unstable', rk)
        # a status missing altogether (an older row) is not assessable either
        self.assertEqual(bs.chatter_state(dict(row, critical_status_without_bite_damping=None))
                         ['state'], 'NOT_ASSESSABLE')

    def test_mapping_covers_every_engine_status(self):
        for status, state in (('UNSTABLE_ABOVE_CRITICAL_SPEED', 'CRITICAL_SPEED'),
                              ('STABLE_OVER_SCANNED_RANGE', 'STABLE_OVER_SCAN'),
                              ('UNSTABLE_AT_LOWEST_SCANNED_SPEED', 'ALREADY_UNSTABLE'),
                              ('UNSTABLE_AT_LOWEST_ASSESSABLE_SPEED', 'ALREADY_UNSTABLE'),
                              ('NO_CROSSING_IN_SCAN', 'STABLE_OVER_SCAN')):
            self.assertEqual(bs.CHATTER_STATES[status], state)
        row = {'bite_status': 'BITE', 'exit_speed_m_s': 100.0,
               'critical_status_without_bite_damping': 'STABLE_OVER_SCANNED_RANGE'}
        self.assertEqual(bs.chatter_state(row)['state'], 'OUTSIDE_SCAN')
        self.assertEqual(bs.chatter_state({'bite_status': 'NO_BITE'})['state'],
                         'NOT_ASSESSABLE')


if __name__ == '__main__':
    unittest.main()
