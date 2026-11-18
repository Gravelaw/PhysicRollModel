"""SPEC12 stage A: the extended roll-bite domain in the band engine (exit gauge below 20 um
with the experimental mattress model, floor 8 um; reductions up to 65 %). Split from
tests.test_band_foil to keep each module under 60 s; fixtures are shared from there.
"""
import copy
import json
import unittest

from physicroll.band_diagnosis import BITE_FLOOR_FLAG, CLOSED_GAP_FLAG, diagnose, validate_case
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


if __name__ == '__main__':
    unittest.main()
