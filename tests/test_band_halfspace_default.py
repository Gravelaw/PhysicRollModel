"""The reduced half-space bite in the engine (SPEC18 package 4): option 'auto_half_space',
the default left unchanged, and a solver failure inside diagnose.

Coarse numerics as tests/test_band_halfspace.py. Software checks of the wiring only.
"""
import copy
import hashlib
import unittest
from pathlib import Path

from physicroll import band_process as bp
from physicroll import halfspace_bite as hb
from physicroll.band_diagnosis import diagnose, load_case, result_json

SCEN = Path(__file__).resolve().parents[1] / 'scenarios'
COARSE = {'axial_cell_m': 0.02, 'radial_cells': 6, 'time_step_s': 5.0}
# sha256 of result_json(diagnose(template)) at commit ec2d7b4, before SPEC18 package 4; the
# only change allowed by package 4 is the additive key 'bite_extras' (removed before hashing)
TEMPLATE_SHA256_BEFORE = '30a6940eda2839ce00223e64ad4c8b84c89ec659be4c7a64416b4a2b2f21f400'


def coarse_battery(model, labels=('S3', 'F2')):
    demo = load_case(SCEN / 'band_diagnosis_battery_foil.json')
    demo['width_model']['numerics'] = dict(COARSE)
    demo['width_model']['friction_stripe_screen'] = None   # tested in test_band_halfspace
    demo['model_options']['thermal_sensitivity'] = 'off'
    demo['model_options']['cells'] = 64
    demo['model_options']['bite_model'] = model
    demo['gauge_control'] = demo['drive'] = None
    demo['schedule'] = [s for s in demo['schedule'] if s['label'].split()[0] in labels]
    return demo


class AutoHalfSpaceTests(unittest.TestCase):

    def test_auto_half_space_falls_back_where_hitchcock_stops(self):
        r = diagnose(coarse_battery('auto_half_space'))
        self.assertIn(bp.HALF_SPACE_FLAG, r['bite']['flags'])    # case pass 50 -> 30 um
        self.assertIn('BITE_MODEL_AUTO_HALF_SPACE', r['flags'])
        self.assertIn('Hitchcock', r['bite_fallback_reason'])
        models = {x['label'].split()[0]: x['bite_model'] for x in r['schedule_sweep']['rows']}
        self.assertEqual(models, {'S3': 'hitchcock', 'F2': 'reduced_half_space'})
        self.assertEqual(r['levers']['perturbed_bite_model'], 'reduced_half_space')
        self.assertEqual(r['bite_extras']['zone_structure'], 'A F')


class DefaultUnchangedTests(unittest.TestCase):

    def test_template_result_unchanged_except_bite_extras(self):
        r = diagnose(load_case(SCEN / 'band_diagnosis_template.json'))
        self.assertEqual(r['bite_extras']['status'], 'NOT_SUPPLIED')
        del r['bite_extras']
        digest = hashlib.sha256(result_json(r).encode()).hexdigest()
        self.assertEqual(digest, TEMPLATE_SHA256_BEFORE)


class FailureInsideDiagnoseTests(unittest.TestCase):

    def test_half_space_failure_does_not_crash_diagnose(self):
        original = hb.derive_bite_response_half_space

        def failing(*a, **k):
            raise hb.HalfSpaceBiteError('structure', 'no admissible zone structure: test')
        hb.derive_bite_response_half_space = failing
        try:
            case = coarse_battery('half_space', labels=('F2',))
            case['width_model'] = None
            r = diagnose(case)
        finally:
            hb.derive_bite_response_half_space = original
        self.assertIsNone(r['bite'])
        self.assertIn('no admissible zone structure', r['bite_error'])
        self.assertEqual(r['levers']['status'], 'NOT_ASSESSABLE')
        self.assertIn('rejected', r['schedule_sweep']['rows'][0])
        self.assertEqual(r['bite_extras']['status'], 'NOT_SUPPLIED')


if __name__ == '__main__':
    unittest.main()
