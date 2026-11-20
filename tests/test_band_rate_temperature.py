"""SPEC18 package 8 in the engine: hardening.rate_temperature, law forms in a case, and the rate
share of the bite damping heuristic (reported only)."""
import copy
import json
import math
import os
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_process as bp
from physicroll import benchmarks as bm
from physicroll import chatter
from physicroll.halfspace_bite import derive_bite_response_half_space

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARDENING = {'law': 'voce', 'provenance': 'synthetic Voce parameters (test)',
             'initial_stress_pa': 120e6, 'saturation_stress_pa': 260e6,
             'characteristic_strain': 0.6, 'stage_iv_slope_pa': 10e6,
             'prior_equivalent_strain': 0.0, 'reference_thickness_m': 0.002,
             'use_computed_flow_stress': True}
RT = {'rate_sensitivity': 0.027, 'reference_strain_rate_per_s': 1e-3,
      'temperature_coefficient_per_k': 0.0015, 'reference_temperature_k': 293.15,
      'rate_sensitivity_slope_per_k': 0.0, 'provenance': 'test', 'use_rate_temperature': False}


def _case():
    """The bearing-order demo as a v2 case with a hardening law (fastest demo, Hitchcock)."""
    with open(os.path.join(ROOT, 'scenarios', 'band_diagnosis_bearing_order.json')) as fh:
        raw = json.load(fh)
    raw['case_schema'] = bd.CASE_SCHEMA_V2
    for key in bd.bw.OBS_V2_KEYS:
        raw['observation'].setdefault(key, None)
    raw['hardening'] = dict(HARDENING)
    return raw


class EngineTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.raw = _case()
        with_rt = copy.deepcopy(cls.raw)
        with_rt['hardening']['rate_temperature'] = dict(RT)
        cls.a, cls.b = bd.diagnose(cls.raw), bd.diagnose(with_rt)

    def test_not_supplied(self):
        self.assertIsNone(self.a['inputs']['hardening']['rate_temperature'])
        self.assertTrue(self.a['chatter']['rate_sensitivity_damping']['not_supplied'])
        self.assertNotIn('rate_temperature', self.a['process']['flow_stress'])
        self.assertIsNone(self.a['process']['flow_stress']['alloy_group_context']['row'])

    def test_rows_carry_the_factor(self):
        fs = self.b['process']['flow_stress']
        row = fs['passes'][0]
        p = self.raw['pass']
        h0, h1 = p['entry_thickness_m'], p['exit_thickness_m']
        ld = math.sqrt(p['work_roll_radius_m'] * (h0 - h1))
        rate = p['exit_speed_m_s'] / ld * math.log(h0 / h1)
        self.assertAlmostEqual(row['strain_rate_per_s'] / rate, 1, delta=1e-12)
        self.assertEqual(row['bite_temperature_k'], RT['reference_temperature_k'])  # no oil
        self.assertAlmostEqual(row['rate_factor'], (rate / 1e-3) ** 0.027, delta=1e-12)
        self.assertEqual(row['temperature_factor'], 1.0)
        self.assertAlmostEqual(row['flow_stress_with_rate_temperature_pa'],
                               row['computed_mean_flow_stress_pa'] * row['rate_factor'],
                               delta=1e-3)
        for flag in (bp.RATE_FROM_ARC_FLAG, bp.BITE_TEMPERATURE_MISSING_FLAG,
                     bp.RATE_EXTRAPOLATED_FLAG):
            self.assertIn(flag, fs['flags'])
        self.assertNotIn(bp.RATE_FACTOR_APPLIED_FLAG, fs['flags'])
        self.assertIn('STRAIN_RATE_SENSITIVITY_IGNORED', fs['flags'])
        self.assertFalse(fs['rate_temperature']['applied'])
        self.assertEqual(row['used_mean_flow_stress_pa'], row['computed_mean_flow_stress_pa'])

    def test_use_false_changes_nothing_else(self):
        for key in ('hypotheses', 'leading_hypotheses', 'bite', 'levers', 'screens',
                    'signatures', 'flags', 'gauge_control', 'time_simulation'):
            self.assertEqual(self.a[key], self.b[key], key)
        ca = {k: v for k, v in self.a['chatter'].items() if k != 'rate_sensitivity_damping'}
        cb = {k: v for k, v in self.b['chatter'].items() if k != 'rate_sensitivity_damping'}
        self.assertEqual(ca, cb)

    def test_damping_equals_the_formula(self):
        d = self.b['chatter']['rate_sensitivity_damping']
        bite = self.b['bite']
        y = self.b['process']['flow_stress']['passes'][0]['used_mean_flow_stress_pa']
        h0, h1 = bite['entry_thickness_m'], bite['exit_thickness_m']
        # F_Y from the same central difference the engine takes
        case = bd.validate_case(self.raw)
        cache = bd._BiteCache(case)
        eff = copy.deepcopy(case)
        bp.apply_flow_stress(eff, bp.flow_stress_section(eff, eff['hardening']))
        f_y = bp.flow_stress_sensitivity(cache.get, bd._bite_pass(eff))['dforce_dflow_stress_m2']
        q = -bite['dforce_dexit_thickness_n_m']
        beta = f_y * y * 0.027 / (q * 0.5 * (h0 + h1) * math.log(h0 / h1))
        self.assertAlmostEqual(d['equivalent_transit_fraction'] / beta, 1, delta=1e-9)
        self.assertEqual(d['heuristic_transit_fraction'],
                         self.raw['model_options']['bite_damping_transit_fraction'])
        self.assertLess(d['dforce_dgap_velocity_n_s_m'], 0)
        self.assertIn('reported only', d['note'])


class SectionTest(unittest.TestCase):

    def test_use_requires_computed_flow_stress(self):
        raw = _case()
        raw['hardening'] = dict(HARDENING, use_computed_flow_stress=False,
                                rate_temperature=dict(RT, use_rate_temperature=True))
        with self.assertRaises(ValueError) as ctx:
            bd.validate_case(raw)
        self.assertIn('hardening.rate_temperature.use_rate_temperature needs '
                      'use_computed_flow_stress', str(ctx.exception))
        raw['hardening']['rate_temperature'] = dict(RT, colour=1)
        with self.assertRaises(ValueError):
            bd.validate_case(raw)

    def test_use_true_applies_the_factor(self):
        raw = _case()
        raw['hardening'] = dict(HARDENING, rate_temperature=dict(RT, use_rate_temperature=True))
        eff = bd.validate_case(raw)
        fs = bp.flow_stress_section(eff, eff['hardening'])
        bp.apply_flow_stress(eff, fs)
        row = fs['passes'][0]
        self.assertTrue(row['rate_temperature_factor_applied'])
        self.assertEqual(eff['pass']['mean_flow_stress_pa'],
                         row['flow_stress_with_rate_temperature_pa'])
        self.assertIn(bp.RATE_FACTOR_APPLIED_FLAG, fs['flags'])
        self.assertTrue(fs['rate_temperature']['applied'])

    def test_law_forms_in_a_case(self):
        raw = _case()
        raw['hardening'] = dict(HARDENING, stage_iv_slope_pa=-5e6)
        eff = bd.validate_case(raw)                       # a negative late slope is accepted
        fs = bp.flow_stress_section(eff, eff['hardening'])
        self.assertIn('NEGATIVE_LATE_HARDENING_SLOPE_WORK_SOFTENING', fs['flags'])
        raw['hardening'] = {k: v for k, v in HARDENING.items()
                            if k not in bp.HARDENING_LAW_KEYS['voce']}
        raw['hardening'].update(law='tome_voce', saturation_scale_pa=200e6,
                                stage_iv_slope_pa=5e6, initial_hardening_rate_pa=1e9)
        eff = bd.validate_case(raw)
        fs = bp.flow_stress_section(eff, eff['hardening'])
        self.assertEqual(fs['law_type'], 'tome_voce')
        self.assertIn('computed_mean_flow_stress_pa', fs['passes'][0])
        raw['hardening']['stage_iv_slope_pa'] = -30e6       # 200 - 300 < 0 at strain 10
        with self.assertRaises(ValueError):
            bd.validate_case(raw)

    def test_damping_worked_number(self):
        """Published foil case, half-space bite with the 80 GPa strip spring: beta_rate
        0.046375, 9.3 % of a heuristic 0.5 (SPEC18 package 8)."""
        y = bm.FLECK_YS_PA * math.sqrt(3) / 2
        bite, st = derive_bite_response_half_space(
            chatter.BitePass(20e-6, 15e-6, 1.0, 0.089, y, 0.03, 0.0, 0.0),
            roll_youngs_modulus_pa=bm.FLECK_ER_STAR_PA * (1 - 0.3 ** 2), roll_poisson_ratio=0.3,
            strip_plane_strain_modulus_pa=80e9, with_state=True)
        f_y = st['extra']['dforce_dflow_stress_m2']
        self.assertAlmostEqual(f_y * y, 4.8213e6, delta=1e2)
        self.assertAlmostEqual(-bite.dforce_dexit_thickness_n_m, 5.57561e11, delta=2e6)
        case = {'pass': {'mean_flow_stress_pa': y, 'exit_speed_m_s': 10.0}}
        fs = {'passes': [{'label': 'case pass', 'rate_sensitivity_at_bite_temperature': 0.027}]}
        d = bp.rate_sensitivity_damping(case, bite, fs, f_y, 0.5)
        self.assertAlmostEqual(d['equivalent_transit_fraction'], 0.046375, delta=1e-6)
        self.assertAlmostEqual(d['share_of_heuristic'], 0.093, delta=5e-4)


if __name__ == '__main__':
    unittest.main()
