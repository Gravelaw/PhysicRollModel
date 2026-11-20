"""SPEC18 package 7: friction identified from entered load, torque and forward slip (BT-G6).

Coarse numerics: solves through the engine's bite cache (``_BiteCache.state``) and the
reduced half-space bite; one pair of full diagnoses on the fastest demo case.
"""
import copy
import json
import math
import os
import unittest
from dataclasses import replace

from physicroll import band_diagnosis as bd
from physicroll import band_process as bp
from physicroll import band_report
from physicroll import bite_tribology as bt
from physicroll.benchmarks import (FLECK_ER_STAR_PA, FLECK_YS_PA, SOLVER_WIDTH_M,
                                   ROLL_NU_FOR_SOLVER)
from physicroll.halfspace_bite import solve_half_space_bite

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNC = {'force': 0.05, 'slip': 0.01, 'torque': 0.10}


def _scenario(name):
    with open(os.path.join(ROOT, 'scenarios', f'band_diagnosis_{name}.json'), encoding='utf-8') as fh:
        return json.load(fh)


def _battery(model):
    raw = _scenario('battery_foil')
    raw['model_options'] = dict(raw.get('model_options') or {}, bite_model=model)
    return raw, bd.validate_case(raw)


def _cache_solve(case, model):
    cache = bd._BiteCache(case)
    base = bd._bite_pass(case)

    def solve(mu, s=1.0):
        return cache.state(replace(base, friction_coefficient=mu,
                                   mean_flow_stress_pa=base.mean_flow_stress_pa * s),
                           model=model)
    return cache, solve


def _fleck_solve(h0, h1, radius, es, tb=0.0, tf=0.0):
    """Reduced half-space bite on a BT-S1 case (Y_s 230 MPa, E_R* 230 GPa), warm-started."""
    warm = [None]

    def solve(mu, s=1.0):
        res, sol = solve_half_space_bite(
            h0, h1, SOLVER_WIDTH_M, radius, FLECK_YS_PA * math.sqrt(3) / 2 * s, mu, tb, tf,
            roll_youngs_modulus_pa=FLECK_ER_STAR_PA * (1 - ROLL_NU_FOR_SOLVER ** 2),
            roll_poisson_ratio=ROLL_NU_FOR_SOLVER, strip_plane_strain_modulus_pa=es,
            warm_start=warm[0], with_solution=True)
        warm[0] = sol
        return {'force_n': res['separating_force_n'],
                'forward_slip_fraction': res['forward_slip_fraction'],
                'torque_per_work_roll_nm': res['torque_per_work_roll_nm'],
                'contact_length_m': res['contact_length_m'], 'flags': res['flags'],
                'zone_structure': res['zone_structure']}
    return solve


class IdentityTest(unittest.TestCase):
    """Force, slip and torque generated at friction 0.027 come back as 0.027."""

    def _identity(self, model):
        _, case = _battery(model)
        _, solve = _cache_solve(case, model)
        ref = solve(0.027)
        row = bp.identify_record(solve, case['pass']['friction_coefficient'],
                                 {'force': ref['force_n'], 'slip': ref['forward_slip_fraction'],
                                  'torque': ref['torque_per_work_roll_nm']}, UNC)
        for key in ('friction_from_force', 'friction_from_slip', 'friction_from_torque',
                    'friction_joint'):
            self.assertEqual(row[key]['status'], 'FOUND', key)
            self.assertAlmostEqual(row[key]['value'] / 0.027, 1.0, delta=1e-3, msg=key)
        self.assertTrue(row['friction_joint']['consistent'])
        ff = row['friction_and_flow_stress']
        self.assertEqual(ff['status'], 'FOUND')
        self.assertAlmostEqual(ff['friction_coefficient'] / 0.027, 1.0, delta=1e-3)
        self.assertAlmostEqual(ff['flow_stress_scale'], 1.0, delta=1e-3)
        self.assertEqual(ff['note'], bp.IDENT_TWO_UNKNOWNS_NOTE)
        self.assertEqual(row['agreement']['outcome'], 'MEASUREMENTS_AGREE')
        self.assertLessEqual(row['solves'], 42)
        for key in ('friction_from_force', 'friction_from_slip', 'friction_from_torque'):
            lo, hi = row[key]['uncertainty']['interval']
            self.assertLess(lo, row[key]['value'])
            self.assertGreater(hi, row[key]['value'])
        return row

    def test_mattress(self):
        self._identity('mattress')

    def test_half_space(self):
        self._identity('half_space')


class ExponentTest(unittest.TestCase):
    """The load and forward-slip exponents of the three cases of SPEC18 package 7, "Why"."""

    def test_three_cases(self):
        ys = FLECK_YS_PA
        cases = (((20e-6, 15e-6, 0.089, 80e9), 0.03, 'A B F', 2.461, 0.378),
                 ((20e-6, 15e-6, 0.089, 1e13), 0.03, 'A B E F', 2.455, 0.436),
                 ((73e-6, 73e-6 * 0.43, 0.089, 80e9, 0.107 * ys, 0.132 * ys), 0.026, 'A F',
                  1.570, 2.473))
        for args, mu, zs, e_load, e_slip in cases:
            solver = bp._Solver(_fleck_solve(*args))
            self.assertEqual(solver(mu)['zone_structure'], zs)
            ex = bp.friction_exponents(solver, mu)
            self.assertAlmostEqual(ex['load_exponent_in_friction'], e_load, delta=1e-3 * e_load)
            self.assertAlmostEqual(ex['slip_exponent_in_friction'], e_slip, delta=1e-3 * e_slip)

    def test_weak_slip_on_published_case(self):
        solve = _fleck_solve(20e-6, 15e-6, 0.089, 80e9)
        ref = solve(0.03)
        row = bp.identify_record(solve, 0.03, {'force': ref['force_n'],
                                               'slip': ref['forward_slip_fraction'],
                                               'torque': None}, UNC)
        self.assertTrue(row['slip_weakly_determined'])
        self.assertTrue(row['friction_from_slip']['weakly_determined'])
        self.assertEqual(row['friction_from_slip']['note'], bp.IDENT_WEAK_SLIP_SENTENCE)
        # the slip-based value carries a much wider first-order interval than the force-based
        u_f = row['friction_from_force']['uncertainty']['ln_half_width']
        u_s = row['friction_from_slip']['uncertainty']['ln_half_width']
        self.assertGreater(u_s, 5 * u_f)


class RecordsTest(unittest.TestCase):

    def setUp(self):
        self.raw, self.case = _battery('mattress')
        self.cache, solve = _cache_solve(self.case, 'mattress')
        self.ref = solve(0.027)

    def _records(self, recs):
        raw = copy.deepcopy(self.raw)
        raw['measurement'] = dict(raw.get('measurement') or {}, pass_records=recs)
        return bd.validate_case(raw)

    def test_unreachable_slip(self):
        case = self._records([{'label': 'r', 'separating_force_n': self.ref['force_n'],
                               'forward_slip_fraction': 0.9, 'provenance': 'test'}])
        fid = bp.friction_identification(case, case['measurement']['pass_records'], self.cache,
                                         None, 'mattress')
        row = fid['rows'][0]
        self.assertEqual(row['friction_from_force']['status'], 'FOUND')
        self.assertEqual(row['friction_from_slip']['status'], 'NOT_FOUND')
        self.assertIn('reproduces the measured value', row['friction_from_slip']['reason'])
        self.assertIn(bp.IDENT_SLIP_NOT_REPRODUCED_FLAG, fid['flags'])
        self.assertEqual(row['agreement']['outcome'], 'MEASUREMENTS_CONTRADICT')
        self.assertFalse(row['friction_joint']['consistent'])

    def test_two_speeds_slope_and_contact_friction(self):
        case = self._records([
            {'label': 'slow', 'separating_force_n': self.ref['force_n'], 'exit_speed_m_s': 6.5,
             'provenance': 'test'},
            {'label': 'fast', 'separating_force_n': self.ref['force_n'] * 0.95,
             'exit_speed_m_s': 13.0, 'provenance': 'test'}])
        fid = bp.friction_identification(case, case['measurement']['pass_records'], self.cache,
                                         None, 'mattress')
        self.assertEqual(fid['status'], bp.IDENT_STATUS)
        self.assertEqual(fid['bite_model'], 'experimental_mattress')
        mu = [r['friction_from_force']['value'] for r in fid['rows']]
        self.assertAlmostEqual(mu[0] / 0.027, 1.0, delta=1e-3)
        slope = (mu[1] - mu[0]) / math.log(2.0)
        self.assertAlmostEqual(fid['summary']['slope_per_ln_exit_speed'], slope, delta=1e-12)
        self.assertFalse(fid['declaration']['calibrated'])
        self.assertFalse(fid['declaration']['fit_uses_force_torque_slip'])
        self.assertEqual(fid['how_to_use'], bp.IDENT_HOW_TO_USE)
        _, _, clo = bp.tribology_objects(case['tribology'])
        lams = []
        for r, m in zip(fid['rows'], mu):
            ci = r['contact_friction_implied']
            back = bt.friction_coefficient(ci['film_ratio'], bt.FrictionClosure(
                model='load_sharing_curve', contact_friction=ci['contact_friction'],
                mu_v=ci['valley_friction'], contact_ratio_curve=clo.contact_ratio_curve))
            self.assertAlmostEqual(back['friction_coefficient'], m, delta=1e-6)
            lams.append(ci['film_ratio'])
        sc = fid['suggested_contact_friction']
        self.assertGreater(max(lams), 1.2 * min(lams))
        self.assertIsNotNone(sc['slope_per_ln_film_ratio'])

    def test_worked_contact_friction(self):
        a, _, held = bt.contact_ratio_at(0.380072)
        self.assertFalse(held)
        self.assertAlmostEqual(a, 0.6695, delta=5e-5)
        self.assertAlmostEqual((0.03 - (1 - a) * 0.008) / a, 0.04086, delta=5e-6)

    def test_validation(self):
        good = {'label': 'r', 'separating_force_n': 1e6, 'provenance': 'test'}
        bad = [([], 'measurement.pass_records must be null or a list of 1 to 8 records'),
               ([good] * 9, 'measurement.pass_records must be null or a list of 1 to 8'),
               ([dict(good, separating_force_n=0)],
                'measurement.pass_records[0].separating_force_n must be > 0 N'),
               ([good, dict(good, forward_slip_fraction=1.0)],
                'measurement.pass_records[1].forward_slip_fraction must be in (-0.2, 1)'),
               ([dict(good, torque_per_work_roll_nm=-1)],
                'measurement.pass_records[0].torque_per_work_roll_nm must be > 0 N m or null'),
               ([dict(good, force_uncertainty_fraction=0.6)],
                'measurement.pass_records[0].force_uncertainty_fraction must be in (0, 0.5]'),
               ([dict(good, slip_uncertainty_absolute=0)],
                'measurement.pass_records[0].slip_uncertainty_absolute must be in (0, 0.2]'),
               ([dict(good, label=' ')], 'measurement.pass_records[0].label must be a nonempty'),
               ([dict(good, exit_thickness_m=6e-5)],
                'measurement.pass_records[0].exit_thickness_m must be below its'),
               ([dict(good, colour='red')], "unknown keys ['colour']")]
        for recs, msg in bad:
            raw = copy.deepcopy(self.raw)
            raw['measurement'] = dict(raw.get('measurement') or {}, pass_records=recs)
            with self.assertRaises(ValueError) as ctx:
                bd.validate_case(raw)
            self.assertIn(msg, str(ctx.exception))
        rec = self._records([good])['measurement']['pass_records'][0]
        self.assertEqual(rec['force_uncertainty_fraction'], 0.05)
        self.assertEqual(rec['slip_uncertainty_absolute'], 0.01)
        self.assertEqual(rec['torque_uncertainty_fraction'], 0.10)
        self.assertIsNone(rec['exit_speed_m_s'])
        self.assertIsNone(self.case['measurement']['pass_records'])


class DiagnoseTest(unittest.TestCase):
    """Records change nothing but the new keys (fastest demo case, Hitchcock bite)."""

    @classmethod
    def setUpClass(cls):
        raw = _scenario('bearing_order')
        raw['case_schema'] = bd.CASE_SCHEMA_V2      # the measurement section is a v2 section
        for key in bd.bw.OBS_V2_KEYS:                # v2 observations not stated
            raw['observation'].setdefault(key, None)
        case = bd.validate_case(raw)
        _, solve = _cache_solve(case, 'hitchcock')
        ref = solve(case['pass']['friction_coefficient'] * 1.1)
        with_rec = copy.deepcopy(raw)
        with_rec['measurement'] = {'pass_records': [
            {'label': 'coil 1 <b>', 'separating_force_n': ref['force_n'],
             'forward_slip_fraction': ref['forward_slip_fraction'],
             'torque_per_work_roll_nm': ref['torque_per_work_roll_nm'],
             'provenance': 'test & check'}]}
        cls.mu = case['pass']['friction_coefficient'] * 1.1
        cls.a, cls.b = bd.diagnose(raw), bd.diagnose(with_rec)

    def test_not_supplied(self):
        fid = self.a['process']['friction_identification']
        self.assertTrue(fid['not_supplied'])
        self.assertEqual(band_report._friction_identification_block(self.a), '')

    def test_identified(self):
        fid = self.b['process']['friction_identification']
        self.assertEqual(fid['bite_model'], 'hitchcock')
        row = fid['rows'][0]
        self.assertAlmostEqual(row['friction_from_force']['value'] / self.mu, 1, delta=1e-3)
        self.assertIn(bp.IDENT_FLAG, self.b['flags'])
        self.assertIn(bp.IDENT_FLAG, fid['flags'])

    def test_nothing_else_changes(self):
        for key in ('hypotheses', 'leading_hypotheses', 'bite', 'chatter', 'levers', 'screens',
                    'signatures', 'family_summary'):
            self.assertEqual(self.a[key], self.b[key], key)
        self.assertEqual(self.a['flags'], [f for f in self.b['flags'] if f not in bp.IDENT_FLAGS])
        pa = {k: v for k, v in self.a['process'].items() if k != 'friction_identification'}
        pb = {k: v for k, v in self.b['process'].items() if k != 'friction_identification'}
        self.assertEqual(pa, pb)

    def test_report_renders_and_escapes(self):
        html = band_report._friction_identification_block(self.b)
        self.assertIn('Friction from your pass records', html)
        self.assertIn('Not applied.', html)
        self.assertIn('coil 1 &lt;b&gt;', html)
        self.assertNotIn('coil 1 <b>', html)
        self.assertIn('Friction from your pass records', band_report.render_band_report(self.b))


if __name__ == '__main__':
    unittest.main()
