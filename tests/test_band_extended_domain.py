"""SPEC12 stage A: the extended roll-bite domain in the band engine (exit gauge below 20 um
with the experimental mattress model, floor 8 um; reductions up to 65 %). Split from
tests.test_band_foil to keep each module under 60 s; fixtures are shared from there.
"""
import copy
import json
import unittest

from physicroll.band_diagnosis import (BITE_FLOOR_FLAG, BITE_FREE_MODEL_CRITERIA, CLOSED_GAP_FLAG,
                                       WEIGHT_POINTS_CONTRADICT, WEIGHT_POINTS_SUPPORT,
                                       diagnose, validate_case)
from physicroll.band_report import render_band_report
from tests.test_band_foil import TRIBOLOGY, foil_case


TENSION_LINE_OBS = dict(orientation='longitudinal',
                        band_positions_across_width_m=[0.40 + 0.010 * i for i in range(6)],
                        band_spacing_m=0.010, worse_at_lower_tension=True,
                        changes_with_ironing_roll_pressure=True,
                        changes_with_exit_air_blowoff=True, positions_repeat_across_coils=False,
                        appearance='gloss_or_shade', worse_at_thinner_gauge=True,
                        lengthwise_continuity='continuous')


class CollectorFoilExtendedDomainTests(unittest.TestCase):
    """SPEC12 stage A: a 0.030 -> 0.017 mm case pass (formerly below the 20 um floor) now gets
    an experimental mattress bite in the extended domain, flagged and with its limitations."""

    @classmethod
    def setUpClass(cls):
        c = foil_case(friction=0.03, h0=30e-6, h1=17e-6, **TENSION_LINE_OBS)
        c['tribology'] = dict(TRIBOLOGY)
        c['width_model']['roll_heat_fraction_per_roll'] = None
        c['model_options']['bite_model'] = 'auto'
        cls.case = c
        cls.r = diagnose(c)

    def test_hitchcock_only_keeps_its_20_um_floor(self):
        c = copy.deepcopy(self.case)
        c['model_options']['bite_model'] = 'hitchcock'
        c['width_model'] = None
        r = diagnose(c)
        self.assertIsNone(r['bite'])
        self.assertIn('slab/Hitchcock bite domain', r['bite_error'])
        self.assertNotIn('EXIT_GAUGE_BELOW_BITE_MODEL_FLOOR', r['flags'])

    def test_extended_bite_flags_and_limitations(self):
        r = self.r
        validate_case(self.case)
        self.assertIsNone(r['bite_error'])
        self.assertIn('EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN', r['bite']['flags'])
        self.assertIn('EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN', r['flags'])
        self.assertIn('BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL', r['flags'])
        self.assertIn('slab/Hitchcock bite domain', r['bite_fallback_reason'])
        self.assertNotIn(BITE_FLOOR_FLAG, r['flags'])
        self.assertIn(CLOSED_GAP_FLAG, r['flags'])
        self.assertTrue(any('Exit gauge below 20 um' in x for x in r['limitations']))
        fr = r['foil_regime']
        self.assertEqual(fr['below_bite_model_floor']['passes'], [])
        ext = fr['extended_bite_domain']
        self.assertIn('not a prediction', ext['text'])
        self.assertTrue(any(abs(x['exit_thickness_m'] - 17e-6) < 1e-12 for x in ext['passes']))
        # A3: chatter at this gauge is not presented as a prediction
        self.assertIn('CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT', r['flags'])
        row = r['schedule_sweep']['rows'][-1]
        self.assertIn('chatter_reliability', row)
        self.assertIn('not predictions', row['extended_domain_note'])
        self.assertEqual(r['width']['shape_chain']['status'], 'EVALUATED')
        json.dumps(r, allow_nan=False)

    def test_tension_lines_lead_and_no_model_contradiction(self):
        r = self.r
        self.assertEqual(r['leading_hypotheses'], ['foil_tension_lines'])
        for h in r['hypotheses']:
            if h['family'] == 'lengthwise':
                for e in h['evidence']:
                    if e['basis'] in ('model', 'model not assessable'):
                        self.assertNotEqual(e['verdict'], 'CONTRADICTS', (h['id'], e))

    def test_report_renders(self):
        html = render_band_report(self.r)
        self.assertIn('Extended roll-bite domain', html)
        self.assertNotIn('Below the roll-bite model floor', html)


class BelowBiteFloorTests(unittest.TestCase):
    """A 0.012 -> 0.007 mm case pass, below the 8 um floor of both bite models: no bite, the
    partial width evaluation applies, missing model parts never contradict."""

    @classmethod
    def setUpClass(cls):
        c = foil_case(friction=0.03, h0=12e-6, h1=7e-6, **TENSION_LINE_OBS)
        c['tribology'] = dict(TRIBOLOGY)
        c['width_model']['roll_heat_fraction_per_roll'] = None
        cls.case = c
        cls.r = diagnose(c)

    def test_loads_diagnoses_and_flags(self):
        r = self.r
        validate_case(self.case)
        self.assertIsNone(r['bite'])
        self.assertIn('8 um floor', r['bite_error'])
        self.assertIn(BITE_FLOOR_FLAG, r['flags'])
        for key in ('chatter', 'levers'):
            self.assertEqual(r[key]['status'], 'NOT_ASSESSABLE')
            self.assertIn('8 um floor', r[key]['reason'])
        fl = r['foil_regime']['below_bite_model_floor']
        self.assertTrue(fl['case_pass_below_floor'])
        self.assertIn('gauge-control', fl['text'])
        self.assertIn('single-sheet or doubled', fl['text'])
        w = r['width']
        self.assertEqual(w['shape_chain']['status'], 'NOT_ASSESSABLE')
        self.assertIn('8 um floor', w['shape_chain']['reason'])
        self.assertIn('wrinkle_wavelength_m', w['troughs']['exit_span'])
        self.assertTrue(w['thermal_steady']['stripes'])
        rows = w['gauge_trend']['rows']
        self.assertIn('8 um floor', rows[-1]['rejected'])
        self.assertGreater(rows[-1]['critical_ridge_height_m'], 0)
        self.assertEqual(r['leading_hypotheses'], ['foil_tension_lines'])
        for h in r['hypotheses']:
            if h['family'] == 'lengthwise':
                for e in h['evidence']:
                    if e['basis'] in ('model', 'model not assessable'):
                        self.assertNotEqual(e['verdict'], 'CONTRADICTS', (h['id'], e))
        json.dumps(r, allow_nan=False)

    def test_report_renders(self):
        html = render_band_report(self.r)
        self.assertIn('Below the roll-bite model floor', html)
        self.assertIn('Strip-shape chain not assessable', html)



class ProductCheckTests(unittest.TestCase):
    """SPEC12 B1/B2: material.product and the evidence-neutral product check."""

    def test_validation(self):
        c = foil_case(width=False)
        c['material']['product'] = 'no_such_product'
        with self.assertRaises(ValueError) as cm:
            validate_case(c)
        self.assertIn('battery_collector_foil', str(cm.exception))
        c['material']['product'] = 3
        with self.assertRaises(ValueError):
            validate_case(c)
        c['material']['product'] = 'battery_collector_foil'
        self.assertEqual(validate_case(c)['material']['product'], 'battery_collector_foil')

    def test_not_supplied_at_foil_gauge_absent_at_sheet_gauge(self):
        r = diagnose(foil_case(width=False, schedule=False))
        pc = r['product_check']
        self.assertEqual(pc['status'], 'NOT_SUPPLIED')
        self.assertIn('battery_collector_foil', pc['product_ids'])
        from tests.test_band_lengthwise import v2
        self.assertNotIn('product_check', diagnose(v2(orientation='longitudinal')))

    def test_findings_flags_and_no_score_change(self):
        base = foil_case(friction=0.03, h0=36e-6, h1=30e-6, schedule=False, width=False,
                         orientation='longitudinal', band_spacing_m=0.01)
        base['model_options']['bite_model'] = 'auto'
        with_p = copy.deepcopy(base)
        with_p['material']['product'] = 'battery_collector_foil'
        a, b = diagnose(base), diagnose(with_p)
        pc = b['product_check']
        row = pc['rows'][0]
        self.assertTrue(row['is_final_pass'])        # the only (thinnest) pass
        red = next(f for f in row['findings'] if f['item'] == 'per_pass_reduction')
        self.assertEqual(red['verdict'], 'BELOW_PUBLISHED_RANGE')    # 17 % < 29 %
        self.assertIn('CASE_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE', b['flags'])
        self.assertIn('FINAL_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE', b['flags'])
        self.assertEqual([(h['id'], h['score']) for h in a['hypotheses']],
                         [(h['id'], h['score']) for h in b['hypotheses']])
        self.assertIn('Product check', render_band_report(b))


class CaseBiteCredibilityTests(unittest.TestCase):
    """Coordinator item 2: a case pass whose extended-domain bite force lies outside the range
    reported for battery-foil passes is flagged; model evidence carries a note; scores are not
    changed."""

    def test_not_credible_case_pass(self):
        c = foil_case(friction=0.03, h0=25e-6, h1=12e-6, schedule=False, width=False,
                      orientation='longitudinal', band_spacing_m=0.01)
        c['material'].update(yield_stress_pa=185e6)
        c['pass'].update(mean_flow_stress_pa=185e6, entry_tension_pa=38e6, exit_tension_pa=42e6)
        c['model_options']['bite_model'] = 'auto'
        r = diagnose(c)
        self.assertIn('EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN', r['bite']['flags'])
        cb = r['case_bite_credibility']
        self.assertEqual(cb['mark'], 'FORCE_OUTSIDE_REPORTED_RANGE')
        self.assertGreater(cb['ratio_to_reported_range'], 2)
        self.assertIn('CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE', r['flags'])
        self.assertTrue(any('not credible' in x for x in r['limitations']))
        gated = [e for h in r['hypotheses'] for e in h['evidence']
                 if e['basis'] == 'model not credible']
        self.assertTrue(gated)
        self.assertTrue(all('NOT CREDIBLE BASIS' in e['observed'] and e['verdict'] == 'NEUTRAL'
                            for e in gated))
        model = [e for h in r['hypotheses'] for e in h['evidence'] if e['basis'] == 'model']
        self.assertTrue(all(e['criterion'] in BITE_FREE_MODEL_CRITERIA for e in model))
        # the over-long time trace of this stiff bite fails soft (it crashed diagnose before)
        self.assertEqual(r['time_simulation']['status'], 'FAILED')
        self.assertIn('Simulated exit thickness trace', render_band_report(r))
        json.dumps(r, allow_nan=False)

    def test_credible_case_pass_has_no_mark(self):
        c = foil_case(friction=0.03, h0=30e-6, h1=18e-6, schedule=False, width=False,
                      orientation='longitudinal')
        c['model_options']['bite_model'] = 'auto'
        r = diagnose(c)
        self.assertEqual(r['case_bite_credibility']['mark'],
                         'FORCE_INSIDE_REPORTED_RANGE_UNVALIDATED')
        self.assertNotIn('CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE',
                         r['flags'])


def _gate_case(h0, h1):
    """Case pass on the foil demo mill with the demo's final-pass material (185 MPa, H18,
    42 MPa exit tension, 10 m/s), coarse width model with a blocked nozzle and a ridge."""
    c = foil_case(friction=0.03, h0=h0, h1=h1, schedule=False, width=True,
                  orientation='longitudinal', band_positions_across_width_m=[0.623],
                  lengthwise_continuity='continuous', visible_only_after_tension_release=True,
                  appearance='loose_or_buckle')
    c['material'].update(yield_stress_pa=185e6)
    c['pass'].update(mean_flow_stress_pa=185e6, entry_tension_pa=38e6, exit_tension_pa=42e6,
                     exit_speed_m_s=10.0)
    c['model_options']['bite_model'] = 'auto'
    return diagnose(c)


class CredibilityGateTests(unittest.TestCase):
    """SPEC12 C follow-up 1: a not-credible case-pass bite gates its model evidence to
    NEUTRAL ('model not credible'); a credible extended-domain bite does not."""

    @classmethod
    def setUpClass(cls):
        cls.bad = _gate_case(25e-6, 12e-6)
        cls.good = _gate_case(30e-6, 18e-6)

    @staticmethod
    def _bite_model_items(r):
        return [e for h in r['hypotheses'] for e in h['evidence']
                if e['basis'] == 'model' and e['criterion'] not in BITE_FREE_MODEL_CRITERIA
                and e['verdict'] in ('SUPPORTS', 'CONTRADICTS')]

    def test_not_credible_bite_gives_no_model_support_or_contradiction(self):
        r = self.bad
        self.assertEqual(r['case_bite_credibility']['mark'], 'FORCE_OUTSIDE_REPORTED_RANGE')
        self.assertIn('CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE', r['flags'])
        self.assertEqual(self._bite_model_items(r), [])
        gated = [e for h in r['hypotheses'] for e in h['evidence']
                 if e['basis'] == 'model not credible']
        self.assertTrue(any(e['verdict_without_credibility_gate'] in ('SUPPORTS', 'CONTRADICTS')
                            for e in gated))
        for h in r['hypotheses']:     # scores are the tally of the gated evidence
            pts = sum(WEIGHT_POINTS_SUPPORT[e['weight']] if e['verdict'] == 'SUPPORTS'
                      else -WEIGHT_POINTS_CONTRADICT[e['weight']] for e in h['evidence']
                      if e['verdict'] in ('SUPPORTS', 'CONTRADICTS'))
            self.assertEqual(h['score'], pts, h['id'])
        for hid in r['leading_hypotheses']:   # leading rule unchanged
            h = next(x for x in r['hypotheses'] if x['id'] == hid)
            self.assertGreater(h['tallies']['observation_supports'], 0)

    def test_credible_bite_keeps_model_evidence(self):
        r = self.good
        self.assertEqual(r['case_bite_credibility']['mark'],
                         'FORCE_INSIDE_REPORTED_RANGE_UNVALIDATED')
        self.assertTrue(self._bite_model_items(r))
        self.assertFalse(any(e['basis'] == 'model not credible'
                             for h in r['hypotheses'] for e in h['evidence']))


class LargeForwardSlipTests(unittest.TestCase):
    """Reviewer's case: a mattress bite with forward slip >= 0.5 crashed the roll-speed
    kinematics; now the kinematics use zero slip with a flag (fixed in d993e21)."""

    def test_slip_above_half_does_not_crash(self):
        c = foil_case(friction=0.03, h0=30e-6, h1=12e-6, schedule=False, width=False,
                      orientation='longitudinal')
        c['pass'].update(width_m=1.2, work_roll_radius_m=0.14, mean_flow_stress_pa=175e6,
                         entry_tension_pa=35e6, exit_tension_pa=40e6)
        c['model_options']['bite_model'] = 'auto'
        c['schedule'] = [dict(label='same pass', entry_thickness_m=30e-6,
                              exit_thickness_m=12e-6, mean_flow_stress_pa=175e6,
                              friction_coefficient=0.03, entry_tension_pa=35e6,
                              exit_tension_pa=40e6, exit_speed_m_s=13.0)]
        r = diagnose(c)
        self.assertGreaterEqual(r['bite']['forward_slip_fraction'], 0.5)
        for f in ('FORWARD_SLIP_IMPLAUSIBLY_LARGE_NO_ELASTIC_STRIP_ZONES',
                  'FORWARD_SLIP_OUTSIDE_KINEMATICS_DOMAIN_ZERO_USED_IN_KINEMATICS'):
            self.assertIn(f, r['flags'])
        self.assertEqual(r['signatures']['forward_slip_fraction_used'], 0.0)
        row = r['schedule_sweep']['rows'][0]
        self.assertNotIn('rejected', row)
        self.assertGreaterEqual(row['forward_slip_fraction'], 0.5)
        json.dumps(r, allow_nan=False)
        self.assertIn('Simulated', render_band_report(r))


if __name__ == '__main__':
    unittest.main()
