"""Reduced half-space bite: zone E, structure selection, friction march, warm start and the
benchmark mode of the printed end conditions (SPEC18 package 3).

Software checks: the planner's worked numbers (standard-library prototype, SPEC18 package 3)
pinned after agreeing with the brief, the regime boundary of E1 eq. (29), path independence,
the shear cap and the printed-end family. Passing them is not a validation on a mill.

Forward slip with zone E: the brief defines it from h_p at the E/F boundary (the slip
reversal), its table quotes the thickness of the no-slip zone B (the prototype's value); the
two differ by an elastic-order amount (1 % to 2.5 % of the slip). The tests pin the defined
value and check the brief's number against ``no_slip_zone.no_slip_zone_thickness_m``.
"""
import json
import math
import time
import unittest
from pathlib import Path

from physicroll import halfspace_bite as hb

YS = 230e6
Y_PUB = YS * math.sqrt(3) / 2
E_PUB = 230e9 * 0.91
AL = hb.ALUMINIUM_PLANE_STRAIN_MODULUS_PA
ROOT = Path(__file__).resolve().parents[1]


def _solve(h0, h1, r=0.089, y=Y_PUB, mu=0.03, tb=0.0, tf=0.0, e=E_PUB, es=80e9, **kw):
    return hb.solve_half_space_bite(h0, h1, 1.0, r, y, mu, tb, tf, roll_youngs_modulus_pa=e,
                                    strip_plane_strain_modulus_pa=es, **kw)


def _w_bar(force):
    return force * 230e9 / (0.089 * YS ** 2)


# name: (entry um, reduction, E_s*), structure, rule, force N/m [run], forward slip (h_p at the
# E/F boundary) [run], brief's W_bar, brief's slip (no-slip zone thickness for A B E F),
# contact length m [run], no-slip / zone E length m [run]
TABLE = {
    'pub80': ((20, 0.25, 80e9), 'A B F', 2, 1902400.8262138662, 0.20366789443940547, 92.936,
              0.2037, 0.0020384344556250494, (0.0011102279120950957, 0.0)),
    'pub1e13': ((20, 0.25, 1e13), 'A B E F', 3, 1818937.9891905792, 0.20255296015454682,
                88.859, 0.2047, 0.0019613947598269856,
                (0.0010120889525228808, 1.4403205788052686e-05)),
    'r50_56': ((56, 0.5, 80e9), 'A F', 1, 1549086.919074675, 0.25935497248382466, 75.676,
               0.2594, 0.0024602964080759236, (0.0, 0.0)),
    'r50_54': ((54, 0.5, 80e9), 'A F', 4, 1662240.0171250943, 0.28910598379302677, 81.204,
               0.2891, 0.002479944890955974, (0.0, 0.0)),
    'r50_52': ((52, 0.5, 80e9), 'A B E F', 3, 1798446.4733562607, 0.32047725860653964, 87.858,
               0.3285, 0.0025079221593227903, (0.0001785806249114208, 0.00011875511335959448)),
    'r50_48': ((48, 0.5, 80e9), 'A B E F', 3, 2050805.6038185332, 0.3592501572956328, 100.186,
               0.3652, 0.0025584861880552723, (0.00041929284159114403, 7.293844251657881e-05)),
    'r50_44': ((44, 0.5, 80e9), 'A B E F', 3, 2348636.762175838, 0.39164470893873005, 114.736,
               0.3965, 0.002627383644781391, (0.0006523627146353005, 4.9141612168885065e-05)),
    'r25_36': ((36, 0.25, 80e9), 'A F', 1, 822735.0175897588, 0.11661723409404967, 40.192,
               0.1166, 0.0015986854528843447, (0.0, 0.0)),
    'r25_34': ((34, 0.25, 80e9), 'A F', 4, 900243.9057721962, 0.13633496094684205, 43.979,
               0.1363, 0.0016213145828766012, (0.0, 0.0)),
    'r25_32': ((32, 0.25, 80e9), 'A B E F', 3, 989743.6670581369, 0.15351293440315383, 48.351,
               0.1567, 0.0016509258062974831, (0.00019173829437721192, 6.849342356942791e-05)),
    'r25_28': ((28, 0.25, 80e9), 'A B E F', 3, 1187192.0106438496, 0.17481382621616803, 57.997,
               0.1769, 0.0017243028928217651, (0.00044854423618528617, 3.377214493853959e-05)),
    'r10_30': ((30, 0.1, 80e9), 'A F', 1, 447514.3685920623, 0.042472311622917536, 21.862,
               0.0425, 0.0011079374489129767, (0.0, 0.0)),
    'r10_28': ((28, 0.1, 80e9), 'A F', 4, 485364.6918871905, 0.050572512901362776, 23.711,
               0.0506, 0.0011258919435540092, (0.0, 0.0)),
    'r10_26': ((26, 0.1, 80e9), 'A B E F', 3, 530566.3388196465, 0.057408674297190654, 25.919,
               0.0584, 0.0011500783696966046, (0.0001530270480800222, 3.9936868190296177e-05)),
    'r10_22': ((22, 0.1, 80e9), 'A B E F', 3, 644950.1578418728, 0.06596779905874062, 31.507,
               0.0665, 0.0012199829985819078, (0.0003679415662709414, 1.4314897105122138e-05)),
}

# battery-foil demo (forces of the brief's table [N/m]) and lengthwise demo P1-P6
DEMO_FORCES = {'S1': ('A F', 748924), 'S2': ('A F', 653874), 'S3': ('A F', 803151),
               'F1': ('A F', 1369950), 'ALT1': ('A B E F', 2658150), 'F2': ('A B E F', 3243880),
               'ALT2': ('A B F', 10128500)}
LENGTHWISE_FORCES = (3513580, 3431780, 3133380, 2643920, 2291870, 1996310)


_TABLE_RESULTS = {}


def _table_results():
    """The fifteen passes of the selection table, solved once per module run."""
    if not _TABLE_RESULTS:
        for name, row in TABLE.items():
            g, red, es = row[0]
            _TABLE_RESULTS[name] = _solve(g * 1e-6, g * 1e-6 * (1 - red), es=es)
    return _TABLE_RESULTS


def _rel(a, b):
    return abs(a / b - 1)


class SelectionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.results = _table_results()

    def test_selection_table(self):
        for name, (inp, structure, rule, force, slip, w_bar, brief_slip, length, zl) in \
                TABLE.items():
            r = self.results[name]
            self.assertEqual((r['zone_structure'], r['structure_rule']), (structure, rule), name)
            self.assertLessEqual(_rel(r['force_per_width_n_m'], force), 1e-6, name)
            self.assertLessEqual(_rel(_w_bar(r['force_per_width_n_m']), w_bar), 1e-4, name)
            self.assertLessEqual(_rel(r['forward_slip_fraction'], slip), 1e-6, name)
            self.assertLessEqual(_rel(r['contact_length_m'], length), 1e-6, name)
            self.assertAlmostEqual(r['flat_zone_length_m'], zl[0], delta=1e-10)
            self.assertAlmostEqual(r['backward_slip_zone_length_m'], zl[1], delta=1e-10)
            steps = [s for s, _ in r['structure_selection'] if s.startswith('rule')]
            self.assertEqual(int(steps[-1].split()[1].rstrip(':')), rule)
            h1 = r['exit_thickness_m']
            quoted = (r['no_slip_zone']['no_slip_zone_thickness_m'] / h1 - 1
                      if r['no_slip_zone'] else r['forward_slip_fraction'])
            self.assertAlmostEqual(quoted, brief_slip, delta=6e-5, msg=name)
            if rule == 4:
                self.assertIn('ZONE_STRUCTURE_AT_REGIME_BOUNDARY', r['flags'])
                near = r['structure_nearest_rejected_candidate']
                self.assertEqual(near['structure'], 'A B F')
                self.assertLess(abs(near['force_relative_to_accepted']), 0.02)
        near = self.results['r50_54']['structure_nearest_rejected_candidate']
        self.assertAlmostEqual(_w_bar(near['force_per_width_n_m']), 82.440, delta=5e-3)
        near = self.results['pub1e13']['structure_nearest_rejected_candidate']
        self.assertAlmostEqual(_w_bar(near['force_per_width_n_m']), 88.937, delta=5e-3)

    def test_zone_e_changes_the_load_by_less_than_0_3_percent(self):
        r = self.results['pub1e13']
        near = r['structure_nearest_rejected_candidate']
        change = r['force_per_width_n_m'] / near['force_per_width_n_m'] - 1
        self.assertAlmostEqual(change, -0.0009, delta=1e-4)
        self.assertLess(abs(change), 0.003)
        self.assertGreaterEqual(r['no_slip_zone']['friction_hill_margin_min_over_k'], -hb.HILL_TOL)
        self.assertLessEqual(r['no_slip_zone']['eq16_shear_over_limit_max'], 1 + 1e-6)

    def test_regime_follows_the_published_boundary(self):
        """No-slip zone between 54 and 52 um at r = 0.5 (eq. 29 of E1: 51.2 um), between 34
        and 32 um at r = 0.25 (36.2 um), between 28 and 26 um at r = 0.10 (22.9 um)."""
        for thick, thin in (('r50_54', 'r50_52'), ('r25_34', 'r25_32'), ('r10_28', 'r10_26')):
            self.assertEqual(self.results[thick]['regime'], 'conventional')
            self.assertEqual(self.results[thin]['regime'], 'foil')

    def test_load_is_continuous_across_the_boundary(self):
        """The r = 0.5 series 56, 54, 52, 48 um rises monotonically with no step above 9 %
        per 2 um of entry gauge (the brief's 9 % per step does not hold for its own 52 -> 48 um
        step of 4 um: 87.858 -> 100.186, 14 %, i.e. 6.8 % per 2 um)."""
        names = ('r50_56', 'r50_54', 'r50_52', 'r50_48')
        gauges = [56, 54, 52, 48]
        forces = [self.results[n]['force_per_width_n_m'] for n in names]
        for (ga, a), (gb, b) in zip(zip(gauges, forces), zip(gauges[1:], forces[1:])):
            self.assertGreater(b, a)
            self.assertLess((b / a) ** (2.0 / (ga - gb)) - 1, 0.09)

    def test_selection_is_path_independent(self):
        _, s48 = _solve(48e-6, 24e-6, with_solution=True)
        warm = _solve(52e-6, 26e-6, warm_start=s48)
        cold = self.results['r50_52']
        self.assertEqual(warm['zone_structure'], cold['zone_structure'])
        self.assertLessEqual(_rel(warm['force_per_width_n_m'], cold['force_per_width_n_m']),
                             1e-6)
        self.assertFalse(warm['convergence']['cold_start'])

    def test_warm_start_equals_cold_start(self):
        cold, sol = _solve(20e-6, 15e-6, with_solution=True)
        warm = _solve(20e-6, 15e-6, warm_start=sol)
        self.assertLessEqual(_rel(warm['force_per_width_n_m'], cold['force_per_width_n_m']),
                             1e-8)
        self.assertEqual(warm['structure_selection'][0], ['warm_start', 'A B F converged'])
        with self.assertRaises(ValueError):
            _solve(20e-6, 15e-6, warm_start='not a solution')

    def test_no_admissible_structure_message(self):
        saved = hb._SHEAR_TOL, hb.HILL_TOL
        hb._SHEAR_TOL, hb.HILL_TOL = -1.0, -1.0    # no A B F or A B E F can pass
        try:
            with self.assertRaises(hb.HalfSpaceBiteError) as ctx:
                _solve(20e-6, 15e-6)
        finally:
            hb._SHEAR_TOL, hb.HILL_TOL = saved
        self.assertEqual(ctx.exception.stage, 'structure')
        self.assertIn('no admissible zone structure', str(ctx.exception))
        self.assertIn('rule 6', str(ctx.exception))


def _schedule(name):
    case = json.loads((ROOT / 'scenarios' / f'band_diagnosis_{name}.json').read_text())
    out = []
    for s in case['schedule']:
        out.append((s['label'].split()[0],
                    _solve(s['entry_thickness_m'], s['exit_thickness_m'],
                           case['pass']['work_roll_radius_m'], s['mean_flow_stress_pa'],
                           s['friction_coefficient'], s['entry_tension_pa'],
                           s['exit_tension_pa'], case['stand']['roll_youngs_modulus_pa'], AL)))
    return out


CAP_ARGS = dict(r=0.135, y=150e6 * math.sqrt(3) / 2, tb=20e6, tf=20e6, e=210e9)

# A B E F rows of the brief's tables: reported slip (at the slip reversal) [run], the brief's
# slip from the thickness of B, and the brief's creep 1 - h_n/h_B
ABEF_SLIP = {'pub1e13': (0.20255296015454682, 0.2047, 0.0018),
             'r50_52': (0.32047725860653964, 0.3285, 0.0060),
             'r50_48': (0.3592501572956328, 0.3652, 0.0044),
             'r50_44': (0.39164470893873005, 0.3965, 0.0035),
             'r25_32': (0.15351293440315383, 0.1567, 0.0028),
             'r25_28': (0.17481382621616803, 0.1769, 0.0018),
             'r10_26': (0.057408674297190654, 0.0584, 0.0009),
             'r10_22': (0.06596779905874062, 0.0665, 0.0005),
             'ALT1': (None, 0.4212, 0.0035), 'F2': (None, 0.3678, 0.0003),
             'cap003': (None, 0.3583, 0.0062)}


class ScheduleAndCapTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start = time.perf_counter()
        cls.battery = _schedule('battery_foil')
        cls.lengthwise = _schedule('lengthwise_bands')
        cls.elapsed = time.perf_counter() - start
        cls.cap003 = _solve(50e-6, 25e-6, mu=0.03, **CAP_ARGS)

    def test_demo_schedules(self):
        """Second table of the brief and the lengthwise forces; timing guard: the 13 demo
        passes cold in under 30 s in total."""
        for label, r in self.battery:
            structure, force = DEMO_FORCES[label]
            self.assertEqual(r['zone_structure'], structure, label)
            self.assertLess(_rel(r['force_per_width_n_m'], force), 5e-6, label)
        for (label, r), force in zip(self.lengthwise, LENGTHWISE_FORCES):
            self.assertEqual(r['zone_structure'], 'A F')
            self.assertLess(_rel(r['force_per_width_n_m'], force), 5e-6)
        self.assertLess(self.elapsed, 30.0)

    def test_forward_slip_is_taken_at_the_slip_reversal(self):
        """Ruling of 2026-11-20: forward slip from h_p at the E/F boundary; the no-slip zone
        B is thicker by an elastic-order amount and creeps by 1 - h_n/h_B (below 0.01)."""
        battery = dict(self.battery)
        table = {name: _table_results()[name] for name in ABEF_SLIP if name in TABLE}
        table.update(ALT1=battery['ALT1'], F2=battery['F2'], cap003=self.cap003)
        for name, (slip, brief_b, creep) in ABEF_SLIP.items():
            r = table[name]
            self.assertEqual(r['zone_structure'], 'A B E F', name)
            ns = r['no_slip_zone']
            h1 = r['exit_thickness_m']
            if slip is not None:
                self.assertLess(_rel(r['forward_slip_fraction'], slip), 1e-6, name)
            self.assertAlmostEqual(ns['no_slip_zone_thickness_m'] / h1 - 1, brief_b, delta=6e-5)
            self.assertAlmostEqual(ns['relative_slip_in_no_slip_zone'], creep, delta=6e-5)
            self.assertLess(ns['relative_slip_in_no_slip_zone'], 0.01)
            self.assertNotIn('NO_SLIP_ZONE_CREEP_ABOVE_ONE_PERCENT', r['flags'])
            self.assertIn(hb.CREEP_LIMITATION, r['limitations'])
        _, sol = _solve(20e-6, 15e-6, es=1e13, with_solution=True)
        pw = hb._power_terms(sol.problem, sol.unknowns)
        for zone, term in pw['slip_terms'].items():
            self.assertGreaterEqual(term, 0.0, zone)
        self.assertLess(pw['work_residual_relative'], 1e-4)
        self.assertGreater(pw['work_residual_relative_without_creep'], 1e-3)

    def test_creep_flag(self):
        saved = hb.CREEP_FLAG_THRESHOLD
        hb.CREEP_FLAG_THRESHOLD = 0.001
        try:
            r = _solve(52e-6, 26e-6)            # creep 0.0060
        finally:
            hb.CREEP_FLAG_THRESHOLD = saved
        self.assertIn('NO_SLIP_ZONE_CREEP_ABOVE_ONE_PERCENT', r['flags'])


if __name__ == '__main__':
    unittest.main()
