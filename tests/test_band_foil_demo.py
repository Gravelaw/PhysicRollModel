"""The foil demo tests, split from tests/test_band_foil.py to keep each module under
the time limit; fixtures are shared from there."""
import unittest

from tests import test_band_foil as _base

# the shared fixtures, helpers and imports of the original module (test classes excluded,
# so no test runs twice)
globals().update({k: v for k, v in vars(_base).items() if not k.startswith('__')
                  and not (isinstance(v, type) and issubclass(v, unittest.TestCase))})


class FoilDemoTests(unittest.TestCase):
    def test_foil_demo_leads_with_planted_cause(self):
        demo = load_case(SCEN / 'band_diagnosis_battery_foil.json')
        self.assertTrue(demo['synthetic'])
        self.assertIn('GENERATED FROM THE MODEL', demo['provenance'])
        # plant route (plant statements): 50 um input, two single-sheet passes, final
        # 17-19 um (F2 at 18 um), thinnest 12 um by the published-like route 50 -> 25 -> 12 um
        # (ALT1, ALT2; SPEC12 B4)
        sched = {x['label'].split()[0]: x for x in demo['schedule']}
        self.assertEqual(list(sched), ['S1', 'S2', 'S3', 'F1', 'F2', 'ALT1', 'ALT2'])
        self.assertAlmostEqual(sched['F1']['entry_thickness_m'], 50e-6)
        self.assertAlmostEqual(sched['F1']['exit_thickness_m'], 30e-6)
        self.assertAlmostEqual(sched['F2']['exit_thickness_m'], 18e-6)
        self.assertAlmostEqual(sched['ALT1']['exit_thickness_m'], 25e-6)
        self.assertAlmostEqual(sched['ALT2']['entry_thickness_m'], 25e-6)
        self.assertAlmostEqual(sched['ALT2']['exit_thickness_m'], 12e-6)
        self.assertEqual(demo['pass']['entry_thickness_m'], 50e-6)   # case pass = F1
        self.assertEqual(demo['pass']['exit_thickness_m'], 30e-6)
        red = {k: (x['entry_thickness_m'] - x['exit_thickness_m']) / x['entry_thickness_m']
               for k, x in sched.items()}
        self.assertTrue(all(v <= 0.5 + 1e-12 for k, v in red.items() if k != 'ALT2'))
        self.assertAlmostEqual(red['ALT2'], 0.52)    # above 50 %: extended bite domain
        # published practice: single-sheet final pass 450-650 m/min, earlier 550-1000 m/min
        for k, x in sched.items():
            lo, hi = (450, 650) if k in ('F2', 'ALT2') else (550, 1000)
            self.assertTrue(lo <= x['exit_speed_m_s'] * 60 <= hi, k)
        for k in ('S1', 'S2', 'S3', 'ALT1'):
            self.assertIn('assumed', sched[k]['label'])
        self.assertIn('plant statements', demo['provenance'])
        self.assertEqual(demo['material']['product'], 'battery_collector_foil')
        # coarse thermal numerics, final pass only, no AGC / drive (they do not enter the
        # lengthwise evidence) to keep the module fast
        demo['width_model']['numerics'] = dict(COARSE)
        # the full thermal sensitivity (spray rows, per-row onsets) is not under test here
        demo['model_options']['thermal_sensitivity'] = 'partition'
        demo['schedule'] = [x for x in demo['schedule']            # F1, F2 and ALT2
                            if x['label'].split()[0] in ('F1', 'F2', 'ALT2')]
        demo['gauge_control'] = demo['drive'] = None
        # the friction-stripe screen (SPEC17 package 7) is tested in
        # tests/test_band_friction_stripes.py; it changes nothing tested here
        demo['width_model']['friction_stripe_screen'] = None
        r = diagnose(demo)
        self.assertEqual(r['leading_hypotheses'], ['nozzle_thermal_stripe'])
        self.assertEqual(_h(r)['cooling_zone_switching_transient']['standing'], 'CONSISTENT')
        self.assertNotEqual(r['hypotheses'][0]['id'], 'foil_tension_lines')
        fr = r['foil_regime']
        self.assertIn(CLOSED_GAP_FLAG, r['flags'])
        self.assertEqual(fr['bite']['model'], 'experimental_mattress')
        self.assertTrue(fr['bite']['force_per_width_within_reported_range'])
        self.assertAlmostEqual(fr['wrinkle_rule']['wrinkle_onset_i_units'], 1e5 * 40e6 / 70e9)
        self.assertEqual(fr['wrinkle_rule']['comparison'], 'MODEL_BAND_BELOW_WRINKLE_ONSET')
        self.assertIn('H18', fr['product_question']['text'])
        st = r['width']['shape']['steady_stripe_table'][0]['with_feedback']
        self.assertEqual((st['state'], st['state_after_tension_release']),
                         ('LATENT_UNDER_TENSION', 'MANIFEST_AFTER_TENSION_RELEASE'))
        self.assertIn('OPEN ROLL GAP ASSUMED', r['levers']['foil_regime_note'])
        lines = ' '.join(r['recommended_next_measurements'])
        self.assertIn('offline sag', lines)
        self.assertTrue(math.isfinite(fr['bite']['separating_force_per_width_n_m']))
        # SPEC12 stage A: F2 (30 -> 18 um) and ALT (24.5 -> 12 um, 51 %) now get experimental
        # mattress bites in the extended domain, flagged; nothing lies below the 8 um floor
        self.assertNotIn(BITE_FLOOR_FLAG, r['flags'])
        sw = r['schedule_sweep']['rows']
        for row in sw + r['width']['gauge_trend']['rows']:
            self.assertNotIn('rejected', row)
        self.assertEqual([x['bite_model'] for x in sw], ['experimental_mattress'] * 3)
        self.assertIn('EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN', sw[1]['bite_flags'])
        self.assertNotIn('REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN', sw[1]['bite_flags'])
        for flag in ('EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN',
                     'REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN'):
            self.assertIn(flag, sw[2]['bite_flags'])
        for row in sw[1:]:
            self.assertIn('chatter_reliability', row)
        fl = fr['below_bite_model_floor']
        self.assertEqual(fl['passes'], [])
        self.assertIsNone(fl['text'])
        ext = fr['extended_bite_domain']['passes']
        self.assertEqual([round(x['exit_thickness_m'] * 1e6) for x in ext], [18, 12])
        # F2 inside the published 0.9-2.3 kN/mm, ALT (12 um) far above it: reported, not hidden
        self.assertEqual([x['force_per_width_within_reported_range'] for x in ext],
                         [True, False])
        # coordinator item 2: the 12 um bite is marked not credible, the 18 um one is not
        self.assertEqual([x['bite_credibility'] for x in ext],
                         ['FORCE_INSIDE_REPORTED_RANGE_UNVALIDATED',
                          'FORCE_OUTSIDE_REPORTED_RANGE'])
        self.assertGreater(ext[1]['bite_force_ratio_to_reported_range'], 2)
        self.assertIn('NOT CREDIBLE', fr['extended_bite_domain']['text'])
        self.assertEqual(sw[2]['bite_credibility'], 'FORCE_OUTSIDE_REPORTED_RANGE')
        self.assertNotIn('case_bite_credibility', r)          # case pass F1 is above 20 um
        self.assertNotIn('CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE',
                         r['flags'])
        # B2: product check, evidence-neutral; F2 and ALT2 are route ends (final passes)
        pc = r['product_check']
        self.assertEqual(pc['product_id'], 'battery_collector_foil')
        self.assertEqual(pc['alloy_designation_used'], '1235')
        self.assertEqual([x['label'].split()[0] for x in pc['rows'] if x['is_final_pass']],
                         ['F2', 'ALT2'])
        for x in pc['rows']:
            if x['label'].split()[0] in ('F2', 'ALT2', 'F1'):
                self.assertEqual(x['outside_published_range'], [], x['label'])
        self.assertTrue(pc['nearest_published_schedules']['final_pass'])
        self.assertTrue(any('Exit gauge below 20 um' in x for x in r['limitations']))
        self.assertIs(fr['final_pass_doubled'], False)
        self.assertIn('rolled single-sheet', fr['product_question']['text'])
        html = render_band_report(r)
        self.assertLess(html.index('class="foil"'), html.index('Leading hypotheses'))
        self.assertIn('Extended roll-bite domain', html)
        self.assertNotIn('Below the roll-bite model floor', html)
        self.assertIn('Product check (published envelope, literature survey)', html)
        json.dumps(r, allow_nan=False)

    def test_foil_gauge_trend_direction_runs_against_thinner_is_worse(self):
        # Pinned on purpose: this is the model's answer to the plant's "worse at thinner
        # gauge" at foil gauge, and for this one mechanism (the demo's cooling stripe buckling
        # in the mill) it runs AGAINST the plant observation: the exit-tension feedback grows
        # as gauge falls, so the same roll stripe needs a taller height to buckle on the
        # thinner pass. Only the direction is pinned, not the numbers. The whole schedule
        # (S1-S3 and the plant's F1; since SPEC12 stage A also F2 at 18 um and ALT at 12 um,
        # with extended-domain mattress bites) is run with coarse thermal numerics and
        # cells 64 (the mattress bite uses its own minimum) and without AGC / drive, to keep
        # the module fast; the published demo result uses the scenario's own numerics.
        demo = load_case(SCEN / 'band_diagnosis_battery_foil.json')
        demo['width_model']['numerics'] = dict(COARSE)
        # the full thermal sensitivity (spray rows, per-row onsets) is not under test here
        demo['model_options']['thermal_sensitivity'] = 'partition'
        demo['model_options']['cells'] = 64
        demo['gauge_control'] = demo['drive'] = None
        # the friction-stripe screen (SPEC17 package 7) is tested in
        # tests/test_band_friction_stripes.py; it changes nothing tested here
        demo['width_model']['friction_stripe_screen'] = None
        r = diagnose(demo)
        rows = r['width']['gauge_trend']['rows']
        self.assertEqual(len(rows), 7)
        self.assertTrue(all('rejected' not in x for x in rows))
        self.assertEqual([x['label'].split()[0] for x in rows],
                         ['S1', 'S2', 'S3', 'F1', 'F2', 'ALT1', 'ALT2'])
        alt2 = rows[-1]
        self.assertEqual(alt2['bite_credibility'], 'FORCE_OUTSIDE_REPORTED_RANGE')
        self.assertGreater(alt2['bite_force_ratio_to_reported_range'], 2)
        self.assertEqual(rows[4]['bite_credibility'], 'FORCE_INSIDE_REPORTED_RANGE_UNVALIDATED')
        # the trend is stated over the credible rows, thick -> thin by exit gauge
        cred = sorted((x for x in rows if x is not alt2), key=lambda x: -x['exit_thickness_m'])
        self.assertEqual([x['label'].split()[0] for x in cred],
                         ['S1', 'S2', 'S3', 'F1', 'ALT1', 'F2'])
        for key, sign in (('linear_feedback_i_units', -1), ('rigid_i_units', +1),
                          ('manifest_onset_stripe_height_m', +1),
                          ('released_onset_stripe_height_m', +1)):
            vals = [x[key] for x in cred]
            self.assertTrue(all(sign * (b - a) > 0 for a, b in zip(vals, vals[1:])),
                            (key, vals))
        # bite-free thresholds (exit span / exit gauge) fall over every row, ALT2 included
        allr = sorted(rows, key=lambda x: -x['exit_thickness_m'])
        for key in ('shohet_townsend_half_width_i_units', 'critical_ridge_height_m',
                    'trough_critical_lateral_stress_exit_span_pa',
                    'roller_wrinkle_critical_lateral_stress_exit_span_pa'):
            vals = [abs(x[key]) for x in allr]
            self.assertTrue(all(b < a for a, b in zip(vals, vals[1:])), (key, vals))
        g = r['width']['gauge_trend']
        self.assertIn('Not credible (excluded from the trend): ALT2', g['text'])
        self.assertIn('0.135 mm -> 0.018 mm', g['text'])
        self.assertEqual(g['bite_free_text'].count('falls on every pass'), 4)
        self.assertIn('0.271 -> 0.00301 I-units', g['bite_free_text'])
        # the report's neutral heading and generated direction sentence say the same
        html = render_band_report(r)
        self.assertIn('<h2>How the result changes with gauge</h2>', html)
        self.assertIn('thinner is less sensitive for this mechanism in the model', html)
        self.assertIn('to F2 0.030-&gt;0.018 mm', html)
        self.assertIn('Not credible (excluded from the direction): ALT2', html)
        self.assertIn('bite NOT CREDIBLE', html)
        self.assertIn('Bite-free thresholds.', html)
        self.assertNotIn('Why thin gauge is worse', html)

if __name__ == '__main__':
    unittest.main()
