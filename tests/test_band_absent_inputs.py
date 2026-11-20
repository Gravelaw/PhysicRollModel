"""SPEC17 G4: optional case keys added by the SPEC17 packages. A key absent from the case and
the same key set to null give the identical result (``result_json``). Split from the other
modules to keep each under 60 s (two diagnose runs of the template, about 17 s each)."""
import copy
import unittest
from pathlib import Path

from physicroll.band_diagnosis import diagnose, load_case, result_json

ROOT = Path(__file__).resolve().parents[1]
# (section, key) of every optional key a SPEC17 package added to the template
SPEC17_OPTIONAL_KEYS = (('tribology', 'oil_flash_point_k'),
                        ('tribology', 'oil_supply_temperature_cap_k'),
                        ('width_model', 'spray_wetted_arc_rad'),
                        ('width_model', 'strip_temperature'),
                        ('width_model', 'friction_stripe_screen'))


class AbsentEqualsNullTests(unittest.TestCase):
    def test_template_with_and_without_the_null_keys(self):
        case = load_case(ROOT / 'scenarios' / 'band_diagnosis_template.json')
        for sec, key in SPEC17_OPTIONAL_KEYS:
            self.assertIn(key, case[sec])
            self.assertIsNone(case[sec][key])
        without = copy.deepcopy(case)
        for sec, key in SPEC17_OPTIONAL_KEYS:
            del without[sec][key]
        self.assertEqual(result_json(diagnose(case)), result_json(diagnose(without)))


if __name__ == '__main__':
    unittest.main()
