"""The reduced half-space bite in the engine (SPEC18 package 4), option 'half_space'.

Coarse numerics: the battery-foil demo with coarse thermal numerics, cells 64, no gauge
control or drive, thermal sensitivity off and the schedule cut to S3 (85 -> 50 um) and F2
(30 -> 18 um). Software checks of the wiring: every consumer of the bite uses the half-space
model or says why not; nothing here validates the model.
"""
import copy
import json
import unittest
from pathlib import Path

from physicroll import band_diagnosis as bd
from physicroll import band_plain
from physicroll import band_process as bp
from physicroll import halfspace_bite as hb
from physicroll.band_diagnosis import diagnose, load_case

SCEN = Path(__file__).resolve().parents[1] / 'scenarios'
COARSE = {'axial_cell_m': 0.02, 'radial_cells': 6, 'time_step_s': 5.0}
HS = 'reduced_half_space'


def coarse_battery(model):
    demo = load_case(SCEN / 'band_diagnosis_battery_foil.json')
    demo['width_model']['numerics'] = dict(COARSE)
    demo['model_options']['thermal_sensitivity'] = 'off'
    demo['model_options']['cells'] = 64
    demo['model_options']['bite_model'] = model
    demo['gauge_control'] = demo['drive'] = None
    demo['schedule'] = [s for s in demo['schedule'] if s['label'].split()[0] in ('S3', 'F2')]
    return demo


class HalfSpaceOptionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r = diagnose(coarse_battery('half_space'))

    def test_operating_bite_and_extras(self):
        r = self.r
        self.assertIn(bp.HALF_SPACE_FLAG, r['bite']['flags'])
        self.assertIn('BITE_MODEL_HALF_SPACE', r['flags'])
        self.assertEqual(r['bite_extras']['zone_structure'], 'A F')
        for key in ('dforce_dfriction_n', 'dforce_dflow_stress_m2', 'dslip_dfriction',
                    'dslip_dflow_stress_per_pa', 'dcontact_length_dexit_thickness',
                    'dcontact_length_dfriction_m', 'torque_per_work_roll_nm',
                    'slip_dissipation_both_interfaces_over_roll_speed_n',
                    'load_exponent_in_friction', 'load_exponent_in_flow_stress'):
            self.assertIn(key, r['bite_extras'])
        self.assertIn(bd.HALF_SPACE_LIMITATION, r['limitations'])
        self.assertEqual(r['foil_regime']['bite']['model'], HS)
        json.dumps(r, allow_nan=False)

    def test_every_consumer_uses_the_half_space_model_or_says_why(self):
        r = self.r
        self.assertEqual(r['levers']['perturbed_bite_model'], HS)
        sc = r['chatter']['speed_consistent']
        self.assertTrue(sc.get('perturbed_bite_model') == HS or sc.get('status') in (
            'FAILED', 'NOT_SUPPLIED'), sc.get('status'))
        rows = {'gauge trend': r['width']['gauge_trend']['rows'],
                'schedule sweep': r['schedule_sweep']['rows'],
                'friction stripes': r['width']['friction_stripes']['per_pass']}
        for name, table in rows.items():
            self.assertTrue(table, name)
            for row in table:
                if 'rejected' in row:
                    self.assertTrue(row['rejected'], name)      # says why
                    continue
                self.assertEqual(row['bite_model'], HS, name)
        for row in r['width']['friction_stripes']['per_pass']:
            self.assertEqual(row['sensitivity_bite_model'], HS)
        heat = [r['process']['heating']['operating']] + r['process']['heating']['schedule']
        for row in heat:
            self.assertIn('reduced half-space slip dissipation', row['friction_power_basis'])
        for row in r['process']['friction']['schedule']:
            self.assertEqual(row['bite_source'], HS)

    def test_foil_load_outside_the_trade_range_is_flagged(self):
        """F2 (18 um) with the half-space bite at friction 0.03: 3.24 kN/mm, outside the
        0.9-2.3 kN/mm reported for battery-foil passes; the existing credibility mark applies."""
        f2 = [x for x in self.r['schedule_sweep']['rows'] if x['label'].startswith('F2')][0]
        self.assertAlmostEqual(f2['separating_force_per_width_n_m'], 3243884.8, delta=5.0)
        ext = self.r['foil_regime']['extended_bite_domain']
        marked = {x['label'].split()[0]: x.get('bite_credibility') for x in ext['passes']}
        self.assertEqual(marked['F2'], 'FORCE_OUTSIDE_REPORTED_RANGE')
        self.assertIn('NOT CREDIBLE', ext['text'])


class OptionValidationTests(unittest.TestCase):

    def test_shear_cap_factor_option(self):
        case = load_case(SCEN / 'band_diagnosis_template.json')
        v = bd.validate_case(case)
        self.assertNotIn('shear_cap_factor', v['model_options'])     # absent stays absent
        for bad in (0.0, 1.5, True, 'x'):
            c = copy.deepcopy(case)
            c['model_options']['shear_cap_factor'] = bad
            with self.assertRaisesRegex(ValueError,
                                        r'model_options.shear_cap_factor must be in \(0, 1\]'):
                bd.validate_case(c)
        c = copy.deepcopy(case)
        c['model_options']['shear_cap_factor'] = 0.5
        self.assertEqual(bd.validate_case(c)['model_options']['shear_cap_factor'], 0.5)
        self.assertEqual(bd.BITE_MODELS[-2:], ('half_space', 'auto_half_space'))
        self.assertIn('half_space', band_plain.BITE_MODEL_WORDS)
        self.assertIn('auto_half_space', band_plain.BITE_MODEL_WORDS)

    def test_perturbed_model_never_mixes(self):
        case = {'model_options': {'bite_model': 'auto_half_space'}}
        self.assertEqual(bd.perturbed_bite_model(case, None), 'hitchcock')
        case = {'model_options': {'bite_model': 'half_space'}}
        self.assertEqual(bd.perturbed_bite_model(case, None), 'half_space')
        case = {'model_options': {'bite_model': 'auto'}}
        self.assertEqual(bd.perturbed_bite_model(case, None), 'hitchcock')   # 'auto' unchanged

    def test_solver_failure_is_a_soft_failure(self):
        """A structured failure of the half-space solver surfaces as a rejected bite with its
        reason, never as an exception out of the cache."""
        case = bd.validate_case(coarse_battery('half_space'))
        cache = bd._BiteCache(case)
        original = hb.derive_bite_response_half_space

        def failing(*a, **k):
            raise hb.HalfSpaceBiteError('structure', 'no admissible zone structure: test')
        hb.derive_bite_response_half_space = failing
        try:
            with self.assertRaisesRegex(ValueError, 'no admissible zone structure'):
                cache.get(bp.bite_pass(case, case['pass']))
            with self.assertRaisesRegex(ValueError, 'no admissible zone structure'):
                cache.get(bp.bite_pass(case, case['pass']))      # cached failure
        finally:
            hb.derive_bite_response_half_space = original


if __name__ == '__main__':
    unittest.main()
