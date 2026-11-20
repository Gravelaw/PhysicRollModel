"""SPEC19 package 1: local state across the width (A2 inputs, BT-G12, A1 computed).

Function level on the battery-foil demo's case pass (committed artifact rows, no bite solve):
formulas 2-9 against their closed forms and the planner's numbers (s25/local.py, s25/eta.py),
the supply balance, the flow-stress coefficient and the coupling; validation messages; the
section on hand-made thermal sections; and one coarse diagnose (the numerics of
tests/test_band_v2_sections.py) with the key absent and present, and with a circumferential
layout (the healthy bite entry temperature of the surface cycle).
"""
import copy
import json
import math
import os
import types
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_local as bl
from physicroll import band_process as bp
from physicroll import band_width as bw
from physicroll import bite_tribology as bt
from tests.test_band_lengthwise import COARSE, LONG, TRIBOLOGY, v2, width_model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DT = [0.0, 1.0, 2.358]
LOCAL = {'inlet_roll_temperature_weight': 0.5, 'flow_stress_temperature_coefficient_per_k': 0.0015,
         'strip_roll_temperature_coupling': None, 'oil_flow_per_nozzle_m3_s': 1.6667e-4,
         'oil_capture_fraction': 1.0, 'provenance': 'unit test'}


def _load(name, kind):
    path = (os.path.join(ROOT, 'scenarios', f'band_diagnosis_{name}.json') if kind == 'case'
            else os.path.join(ROOT, 'artifacts', 'band_diagnosis', f'{name}.result.json'))
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


class _Foil:
    """The battery-foil demo's case pass: validated case, friction and heating rows of the
    committed artifact, and a stand-in bite with the artifact's slip and contact length."""
    raw = _load('battery_foil', 'case')
    art = _load('battery-foil-demo', 'artifact')
    case = bd.validate_case(raw)
    fr = art['process']['friction']['operating']
    heat = art['process']['heating']['operating']
    b = art['bite']
    bite = types.SimpleNamespace(forward_slip_fraction=fr['forward_slip_fraction'],
                                 contact_length_m=b['contact_length_m'],
                                 separating_force_n=b['separating_force_n'])


def _params(local=None, trib=None, case=None, weights=None, levels=None, heat=None):
    case = copy.deepcopy(case or _Foil.case)
    if local is not None:
        case['width_model']['local_coupling'] = bl.validate_local_coupling(local)
    trib = trib or case['tribology']
    w = case['width_model']
    lub, fin, clo = bp.tribology_objects(trib)
    n = len(DT)
    kw = {}
    if w['local_coupling']['oil_flow_per_nozzle_m3_s'] is not None:
        kw = dict(z_strip=[0.5, 0.6, 0.7], spray_weight=weights or [1.0] * n,
                  nozzle_level=levels or [1.0] * n)
    return bl.local_params(case, w, trib, lub, clo, fin, _Foil.bite,
                           _Foil.heat if heat is None else heat, _Foil.fr, None, **kw)


class FormulaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.p = _params()
        cls.c = bl.local_changes([0.5, 0.6, 0.7], DT, cls.p)

    def test_formulas_2_to_7_exponential_law(self):
        lam0, h0 = _Foil.fr['film_ratio'], _Foil.fr['film_thickness_m']
        eta = self.p['strip_roll_temperature_coupling']
        for i, d in enumerate(DT):
            v = math.exp(-0.015 * 0.5 * d)
            self.assertAlmostEqual(self.c['inlet_temperature_change_k'][i], 0.5 * d, delta=1e-12)
            self.assertLess(abs(self.c['viscosity_ratio'][i] / v - 1), 1e-9)
            self.assertLess(abs(self.c['film_ratio'][i] / (lam0 * v) - 1), 1e-9)
            self.assertLess(abs(self.c['film_thickness_m'][i] / (h0 * v) - 1), 1e-9)
            dmu = 0.082 * (math.exp(-lam0 * v) - math.exp(-lam0))     # placeholder closure
            self.assertAlmostEqual(self.c['friction_change'][i], dmu, delta=1e-9 * 0.082)
            self.assertAlmostEqual(self.c['flow_stress_change_fraction'][i],
                                   -0.0015 * 0.5 * eta * d, delta=1e-15)
            self.assertAlmostEqual(self.c['strip_exit_temperature_change_k'][i], eta * d,
                                   delta=1e-12)
            self.assertAlmostEqual(self.c['strip_exit_temperature_k'][i],
                                   _Foil.heat['exit_temperature_k'] + eta * d, delta=1e-9)

    def test_planner_numbers(self):
        """s25/local.py, s25/eta.py at 2.358 K, weight 0.5 (2 %; eta_x 5 %), pinned below."""
        c, i = self.c, 2
        for value, planner, pinned, tol in (
                (c['viscosity_ratio'][i], 0.982470, 0.9824700, 0.02),
                (c['film_ratio'][i], 0.373410, 0.3734092, 0.02),
                (c['friction_change'][i], 3.748e-4, 3.7483e-4, 0.02),
                (c['friction_change_fraction'][i], 0.0125, 0.012494, 0.02),
                (self.p['strip_roll_temperature_coupling'], 0.844, 0.84425, 0.05),
                (c['strip_exit_temperature_change_k'][i], 1.99, 1.9908, 0.05),
                (c['flow_stress_change_fraction'][i], -1.49e-3, -1.4931e-3, 0.05)):
            self.assertLess(abs(value / planner - 1), tol, (value, planner))
            self.assertLess(abs(value / pinned - 1), 1e-4, (value, pinned))
        w1 = bl.local_changes([0.5, 0.6, 0.7], DT, _params(dict(
            LOCAL, inlet_roll_temperature_weight=1.0)))
        self.assertLess(abs(w1['viscosity_ratio'][2] / 0.965246 - 1), 1e-5)
        self.assertLess(abs(w1['friction_change'][2] / 7.45e-4 - 1), 0.02)

    def test_two_point_table_reproduces_the_exponential_law(self):
        trib = copy.deepcopy(_Foil.case['tribology'])
        lub = trib['lubricant']
        law = [(t, lub['viscosity_ref_pa_s'] * math.exp(-0.015 * (t - 313.15)))
               for t in (300.0, 340.0)]
        lub['viscosity_table'] = [{'temperature_k': t, 'viscosity_pa_s': e} for t, e in law]
        c = bl.local_changes([0.5, 0.6, 0.7], DT, _params(trib=trib))
        for a, b in zip(c['viscosity_ratio'], self.c['viscosity_ratio']):
            self.assertLess(abs(a / b - 1), 1e-9)
        for a, b in zip(c['friction_change'], self.c['friction_change']):
            self.assertAlmostEqual(a, b, delta=1e-12)

    def test_friction_change_is_the_closure_slope_for_a_small_step(self):
        c = bl.local_changes([0.5, 0.6, 0.7], [0.0, 0.1, 0.0], self.p)
        d_lam = c['film_ratio'][1] - _Foil.fr['film_ratio']
        slope = bt.friction_coefficient(_Foil.fr['film_ratio'])['dmu_dlambda']
        self.assertLess(abs(c['friction_change'][1] / (slope * d_lam) - 1), 0.01)
        self.assertGreater(c['friction_change'][1], 0)        # hotter: thinner film, more mu

    def test_zero_profile(self):
        c = bl.local_changes([0.5, 0.6, 0.7], [0.0] * 3, self.p)
        for key in ('inlet_temperature_change_k', 'friction_change', 'friction_change_fraction',
                    'flow_stress_change_fraction', 'strip_exit_temperature_change_k'):
            self.assertEqual(c[key], [0.0] * 3, key)
        self.assertEqual(c['viscosity_ratio'], [1.0] * 3)
        self.assertEqual(c['starved'], [False] * 3)
        self.assertEqual(c['flags'], [])

    def test_supply(self):
        sup = self.p['supply']
        for value, planner, tol in ((sup['q_per_length_m2_s'][0], 3.205e-3, 0.02),
                                    (self.p['mean_entrainment_speed_m_s'], 9.36, 0.02),
                                    (sup['healthy_supplied_film_m'], 3.42e-4, 0.02),
                                    (sup['ratio_to_smooth_film'], 3600.0, 0.02),
                                    (sup['level_below_which_starved'], 2.8e-4, 0.02)):
            self.assertLess(abs(value / planner - 1), tol, (value, planner))
        self.assertEqual(self.c['starved'], [False] * 3)       # a healthy header
        weak = bl.local_changes([0.5, 0.6, 0.7], DT, _params(weights=[1.0, 0.45, 1.0],
                                                             levels=[1.0, 0.45, 1.0]))
        self.assertEqual(weak['starved'], [False] * 3)          # the nozzle at 0.45
        starved = bl.local_changes([0.5, 0.6, 0.7], DT, _params(weights=[1.0, 1e-4, 1.0],
                                                                levels=[1.0, 1e-4, 1.0]))
        self.assertEqual(starved['starved'], [False, True, False])
        self.assertEqual(starved['flags'], [bl.FLAG_STARVED, bl.FLAG_LARGE_FRICTION])
        self.assertLess(starved['film_thickness_m'][1], starved['smooth_film_thickness_m'][1])
        self.assertGreater(starved['friction_change'][1], 0)
        blocked = bl.local_changes([0.5, 0.6, 0.7], DT, _params(weights=[1.0, 0.0, 1.0],
                                                                levels=[1.0, 0.0, 1.0]))
        self.assertEqual(blocked['film_thickness_m'][1], 0.0)
        self.assertEqual(blocked['film_ratio'][1], 0.0)
        self.assertEqual(blocked['flags'], [bl.FLAG_ZERO_SUPPLY, bl.FLAG_LARGE_FRICTION])
        mu0 = bt.friction_coefficient(bl.LAMBDA_FLOOR)['friction_coefficient']
        self.assertAlmostEqual(blocked['friction_change'][1], mu0 - self.p['friction_ref'],
                               delta=1e-15)
        none = bl.local_changes([0.5, 0.6, 0.7], DT, _params(dict(
            LOCAL, oil_flow_per_nozzle_m3_s=None)))
        self.assertIsNone(none['supplied_film_m'])
        self.assertIsNone(none['starved'])
        self.assertEqual(none['film_thickness_m'], none['smooth_film_thickness_m'])

    def test_coupling_supplied_against_computed(self):
        sup = _params(dict(LOCAL, strip_roll_temperature_coupling=0.5))
        self.assertEqual(sup['strip_roll_temperature_coupling'], 0.5)
        self.assertTrue(sup['coupling_basis'].startswith('supplied'))
        self.assertTrue(self.p['coupling_basis'].startswith('computed'))
        c = bl.local_changes([0.5, 0.6, 0.7], DT, sup)
        self.assertAlmostEqual(c['strip_exit_temperature_change_k'][2], 0.5 * 2.358,
                               delta=1e-12)
        # linear in T_r0: the same coupling from another roll entry temperature
        heat = copy.deepcopy(_Foil.heat)
        heat['heat_partition']['roll_entry_surface_temperature_k'] += 7.0
        self.assertAlmostEqual(_params(heat=heat)['strip_roll_temperature_coupling'],
                               self.p['strip_roll_temperature_coupling'], delta=1e-9)
        # without a heat partition and without a supplied value: no strip temperature
        heat['heat_partition'] = bp.not_supplied('needs tribology')
        p = _params(heat=heat)
        self.assertIsNone(p['strip_roll_temperature_coupling'])
        self.assertIn('needs tribology', p['coupling_basis'])
        c = bl.local_changes([0.5, 0.6, 0.7], DT, p)
        self.assertIsNone(c['strip_exit_temperature_k'])
        self.assertIsNone(c['flow_stress_change_fraction'])

    def test_flow_stress_coefficient(self):
        p = _params(dict(LOCAL, flow_stress_temperature_coefficient_per_k=None))
        self.assertIsNone(p['flow_stress_temperature_coefficient_per_k'])
        self.assertIn('no hardening.rate_temperature', p['coefficient_basis'])
        self.assertIsNone(bl.local_changes([0.5, 0.6, 0.7], DT, p)[
            'flow_stress_change_fraction'])
        case = copy.deepcopy(_Foil.case)
        case['hardening'] = {'rate_temperature': {'temperature_coefficient_per_k': 0.002}}
        p = _params(dict(LOCAL, flow_stress_temperature_coefficient_per_k=None), case=case)
        self.assertEqual(p['flow_stress_temperature_coefficient_per_k'], 0.002)
        self.assertIn('hardening.rate_temperature', p['coefficient_basis'])
        self.assertEqual(_params(case=case)['flow_stress_temperature_coefficient_per_k'],
                         0.0015)       # supplied wins

    def test_load_sharing_closure(self):
        trib = copy.deepcopy(_Foil.case['tribology'])
        trib['friction_closure'] = bd.validate_case(dict(_Foil.raw, tribology=dict(
            _Foil.raw['tribology'], friction_closure={
                'mu_b': 0.09, 'mu_v': 0.008, 'lambda0': 1.0, 'model': 'load_sharing_curve',
                'contact_friction': 0.06})))['tribology']['friction_closure']
        p = _params(trib=trib)
        self.assertEqual(p['closure_model'], 'load_sharing_curve')
        self.assertNotIn(bl.FLAG_PLACEHOLDER, p['flags'])
        c = bl.local_changes([0.5, 0.6, 0.7], [0.0, 0.1, 0.0], p)
        lam0 = _Foil.fr['film_ratio']
        slope = bt.friction_coefficient(lam0, bp.tribology_objects(trib)[2])['dmu_dlambda']
        self.assertLess(abs(c['friction_change'][1]
                            / (slope * (c['film_ratio'][1] - lam0)) - 1), 0.01)


class ValidationTests(unittest.TestCase):

    def _err(self, lc):
        raw = copy.deepcopy(_Foil.raw)
        raw['width_model']['local_coupling'] = lc
        with self.assertRaises(ValueError) as ctx:
            bd.validate_case(raw)
        return str(ctx.exception)

    def test_defaults(self):
        out = bl.validate_local_coupling({'provenance': 'x'})
        self.assertEqual(out, {'inlet_roll_temperature_weight': 0.5,
                               'flow_stress_temperature_coefficient_per_k': None,
                               'strip_roll_temperature_coupling': None,
                               'oil_flow_per_nozzle_m3_s': None, 'oil_capture_fraction': 1.0,
                               'provenance': 'x'})
        self.assertIsNone(bl.validate_local_coupling(None))
        self.assertIsNone(bd.validate_case(_load('lengthwise_bands', 'case'))[
            'width_model']['local_coupling'])

    def test_messages(self):
        w = 'width_model.local_coupling'
        for key, bad, words in (
                ('inlet_roll_temperature_weight', 1.2, 'must be in [0, 1]'),
                ('inlet_roll_temperature_weight', True, 'must be a number in [0, 1]'),
                ('flow_stress_temperature_coefficient_per_k', 0.02, 'must be in [0, 0.01]'),
                ('strip_roll_temperature_coupling', -0.1, 'must be in [0, 1.5]'),
                ('oil_flow_per_nozzle_m3_s', 0.0, 'must be in (0, 0.1]'),
                ('oil_capture_fraction', 0.0, 'must be in (0, 1]'),
                ('oil_capture_fraction', 'all', 'must be a number in (0, 1]')):
            self.assertIn(f'{w}.{key} {words}', self._err(dict(LOCAL, **{key: bad})))
        self.assertIn(f'{w}.provenance must be a nonempty string',
                      self._err(dict(LOCAL, provenance=' ')))
        self.assertIn("missing keys ['provenance']", self._err({'oil_capture_fraction': 1.0}))
        self.assertIn("unknown keys ['wiper']", self._err(dict(LOCAL, wiper=True)))


class SectionTests(unittest.TestCase):
    """``local_state_section`` on the artifact's thermal section (no thermal solve)."""

    @classmethod
    def setUpClass(cls):
        cls.case = copy.deepcopy(_Foil.case)
        w = cls.case['width_model']
        cls.th = bw._Thermal(cls.case, w, 1.0, 0.39)
        cls.steady = _Foil.art['width']['thermal_steady']

    def _section(self, steady=None, cycle=None, case=None, trib='case', bite='foil'):
        case = case or self.case
        return bl.local_state_section(
            case, case['width_model'], self.th, steady or self.steady,
            case['tribology'] if trib == 'case' else trib,
            _Foil.bite if bite == 'foil' else bite, _Foil.heat, _Foil.fr, cycle)

    def test_section(self):
        s = self._section()
        self.assertEqual(s['status'], bl.STATUS)
        z = s['z_m']
        self.assertTrue(all(self.steady['strip_start_m'] <= x <= self.steady['strip_end_m']
                            for x in z))
        for key in ('roll_surface_temperature_change_k', 'film_ratio', 'friction_change',
                    'supplied_film_m', 'starved', 'strip_exit_temperature_k'):
            self.assertEqual(len(s[key]), len(z), key)
        at = s['at_largest_change']
        self.assertEqual(at['z_m'], 0.6225)
        self.assertLess(abs(at['roll_surface_temperature_change_k'] / 2.358 - 1), 0.001)
        self.assertFalse(at['starved'])
        self.assertLess(at['supplied_film_m'], s['supply']['healthy_supplied_film_m'])
        for f in (bl.FLAG_COMPUTED, bl.FLAG_MEAN_SURFACE, bl.FLAG_PLACEHOLDER,
                  bt.PLACEHOLDER_FLAG):
            self.assertIn(f, s['flags'])
        self.assertNotIn(bl.FLAG_STARVED, s['flags'])
        self.assertEqual(len(s['thermal_flatness']['i_units']), len(z))
        self.assertEqual(s['thermal_flatness']['i_units_per_kelvin'], 2.36)
        json.dumps(s, allow_nan=False)
        self.assertEqual(len(s['basis']), 9)

    def test_healthy_header_gives_zero(self):
        st = dict(self.steady, surface_temperature_k=self.steady[
            'healthy_surface_temperature_k'])
        s = self._section(steady=st)
        self.assertEqual(set(s['roll_surface_temperature_change_k']), {0.0})
        self.assertEqual(set(s['friction_change']), {0.0})
        self.assertEqual(set(s['strip_exit_temperature_change_k']), {0.0})

    def test_cycle_basis(self):
        n = len(self.steady['z_m'])
        cyc = {'bite_entry_temperature_k': [330.0] * n,
               'healthy_bite_entry_temperature_k': [329.0] * n}
        s = self._section(cycle=cyc)
        self.assertNotIn(bl.FLAG_MEAN_SURFACE, s['flags'])
        self.assertIn('roll_surface_cycle', s['roll_surface_temperature_basis'])
        self.assertEqual(set(s['roll_surface_temperature_change_k']), {1.0})

    def test_not_supplied_and_not_assessable(self):
        case = copy.deepcopy(self.case)
        case['width_model']['local_coupling'] = None
        self.assertTrue(self._section(case=case)['not_supplied'])
        self.assertIn('tribology', self._section(trib=None)['reason'])
        self.assertIn('case-pass bite', self._section(bite=None)['reason'])
        self.assertIn('steady roll thermal', self._section(
            steady={'status': 'NOT_ASSESSABLE'})['reason'])


def _coarse(local=None, layout=None, blocked=(12,)):
    c = v2(**LONG)
    c['tribology'] = dict(TRIBOLOGY)
    c['width_model'] = width_model(numerics=dict(COARSE), blocked_nozzle_indices=list(blocked))
    if local is not None:
        c['width_model']['local_coupling'] = local
    if layout is not None:
        c['width_model']['circumferential_layout'] = layout
    return c


class EngineTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.a = bd.diagnose(_coarse())
        cls.b = bd.diagnose(_coarse(dict(LOCAL, flow_stress_temperature_coefficient_per_k=None)))

    def test_section_present(self):
        ls = self.b['width']['local_state']
        self.assertEqual(ls['status'], bl.STATUS, ls.get('reason') or ls.get('error'))
        self.assertIn(bl.FLAG_COMPUTED, self.b['flags'])
        self.assertIn(bl.FLAG_MEAN_SURFACE, self.b['flags'])
        self.assertIsNone(ls['flow_stress_change_fraction'])
        self.assertIn('no hardening.rate_temperature', ls['flow_stress_change_reason'])
        at = ls['at_largest_change']
        self.assertGreater(at['roll_surface_temperature_change_k'], 0)      # blocked: hotter
        self.assertGreater(at['friction_change'], 0)
        self.assertGreater(at['strip_exit_temperature_change_k'], 0)
        a = self.a['width']['local_state']
        self.assertTrue(a['not_supplied'])
        self.assertIsNone(self.a['inputs']['width_model']['local_coupling'])

    def test_nothing_else_changes(self):
        a, b = self.a, self.b
        self.assertEqual([(h['id'], h['score'], h['standing'], h['rank'])
                          for h in a['hypotheses']],
                         [(h['id'], h['score'], h['standing'], h['rank'])
                          for h in b['hypotheses']])
        self.assertEqual(a['leading_hypotheses'], b['leading_hypotheses'])
        for key in a:
            if key not in ('inputs', 'width', 'flags'):
                self.assertEqual(a[key], b[key], key)
        for key in a['width']:
            if key != 'local_state':
                self.assertEqual(a['width'][key], b['width'][key], key)
        self.assertEqual(a['flags'], [f for f in b['flags'] if f not in bl.TOP_LEVEL_FLAGS])
        ia, ib = copy.deepcopy(a['inputs']), copy.deepcopy(b['inputs'])
        ib['width_model']['local_coupling'] = None
        self.assertEqual(ia, ib)

    def test_surface_cycle_healthy_entry(self):
        layout = {'spray_arcs': [{'start_rad': math.pi / 2, 'arc_rad': math.pi / 3}],
                  'provenance': 'test layout'}
        r = bd.diagnose(_coarse(dict(LOCAL), layout=layout))
        rc, ls = r['width']['roll_surface_cycle'], r['width']['local_state']
        self.assertEqual(rc['status'], 'UNVALIDATED_ROLL_SURFACE_CYCLE')
        self.assertEqual(len(rc['healthy_bite_entry_temperature_k']), len(rc['z_m']))
        self.assertNotIn(bl.FLAG_MEAN_SURFACE, ls['flags'])
        d = [x - y for x, y in zip(rc['bite_entry_temperature_k'],
                                   rc['healthy_bite_entry_temperature_k'])]
        j = max(range(len(d)), key=lambda k: abs(d[k]))
        self.assertGreater(d[j], 0)
        self.assertAlmostEqual(ls['at_largest_change']['roll_surface_temperature_change_k'], d[j],
                               delta=1e-12)
        self.assertLess(abs(rc['z_m'][j] - r['width']['thermal_steady']['nozzle_positions_m'][
            12]), 0.05)
        far = [x for x, z in zip(d, rc['z_m']) if abs(z - rc['z_m'][j]) > 0.4]
        self.assertLess(max(abs(x) for x in far), 0.05 * d[j])
        # a healthy header: the healthy entry temperature equals the actual one exactly
        h = bd.diagnose(_coarse(layout=layout, blocked=()))['width']['roll_surface_cycle']
        self.assertEqual(h['healthy_bite_entry_temperature_k'], h['bite_entry_temperature_k'])


if __name__ == '__main__':
    unittest.main()
