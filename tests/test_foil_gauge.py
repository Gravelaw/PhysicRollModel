"""Foil gauge control by speed and entry tension (SPEC19 package 13): sensitivities, the
analyst loop (frequency and time domain) and the engine section. The worked numbers are the
planner's (battery-foil case pass, the committed artifact's bite)."""
import json
import math
import re
from pathlib import Path
import unittest

from physicroll import band_sensors
from physicroll import foil_gauge as fg
from physicroll.band_diagnosis import diagnose, result_json, validate_case
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import LONG, TRIBOLOGY, v2

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'band_diagnosis'
WIDTH = 1.2
H0, H1, U = 50e-6, 30e-6, 13.0


def _forces():
    a = json.loads((ART / 'battery-foil-demo.result.json').read_text())
    b = a['bite']
    mu = a['width']['friction_stripes']['case_pass']['dforce_per_width_dfriction_n_m']
    return ({'h': b['dforce_dexit_thickness_n_m'], 'h_in': b['dforce_dentry_thickness_n_m'],
             's_e': b['dforce_dentry_tension_m2'], 's_x': b['dforce_dexit_tension_m2'],
             'mu': mu * WIDTH, 'Y': 0.011164701373029301 * WIDTH},
            a['gauge_control']['mill_modulus_n_m'])


def _rel(test, got, want, tol):
    test.assertLess(abs(got / want - 1), tol, (got, want))


class SensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.F, cls.M = _forces()

    def test_worked_table(self):
        _rel(self, self.M, 2.3077e9, 1e-4)
        _rel(self, -self.F['h'], 8.8665e10, 1e-4)
        want = {0.0: (-5.4948e-14, -8.5384e-14, 6.9569e-4, 1.5110e-13, 0.4397),
                self.M: (-5.3555e-14, -8.3218e-14, 6.7804e-4, 1.4727e-13, 0.4286)}
        for m, w in want.items():
            g = fg.gauge_sensitivities(self.F, m)
            got = (g['dh_dentry_tension_m_per_pa'], g['dh_dexit_tension_m_per_pa'],
                   g['dh_dfriction_m'], g['dh_dflow_stress_m_per_pa'], g['dh_dentry_thickness'])
            for x, y in zip(got, w):
                _rel(self, x, y, 1e-4 if abs(y) < 0.4 else 2e-4)
        _rel(self, fg.gauge_sensitivities(self.F, self.M)['dh_dgap'], 0.0254, 2e-3)
        g = fg.gauge_sensitivities(self.F, 0.0)
        # percent of gauge: -0.183 % per MPa, 0.696 % per 1 % friction, 0.881 % per 1 % flow
        p = fg._percent_block(g, H0, H1, 0.03, 175e6)
        self.assertAlmostEqual(p['entry_tension_percent_per_mpa'], -0.183, places=3)
        self.assertAlmostEqual(p['friction_percent_per_percent'], 0.696, places=3)
        self.assertAlmostEqual(p['flow_stress_percent_per_percent'], 0.881, places=3)
        sp = fg.speed_sensitivity(g['dh_dfriction_m'], -0.0016462)
        _rel(self, sp['dh_du_m_per_m_s'], -1.145e-6, 1e-3)
        self.assertAlmostEqual(sp['dh_du_m_per_m_s'] / H1 * 100, -3.8, places=1)
        self.assertEqual(sp['rate_term_m_per_m_s'], 0.0)

    def test_limits_kiss_and_signs(self):
        g = fg.gauge_sensitivities(self.F, 1e18)
        self.assertGreater(g['dh_dgap'], 1 - 1e-6)
        for k in ('dh_dentry_thickness', 'dh_dentry_tension_m_per_pa', 'dh_dfriction_m',
                  'dh_dflow_stress_m_per_pa', 'dh_dexit_tension_m_per_pa'):
            self.assertLess(abs(g[k]), 1e-6 * abs(fg.gauge_sensitivities(self.F, 0.0)[k]) + 1e-30)
        a = fg.gauge_sensitivities(self.F, self.M)
        b = fg.gauge_sensitivities(self.F, self.M, 1e11)
        for k in ('dh_dentry_thickness', 'dh_dentry_tension_m_per_pa', 'dh_dfriction_m',
                  'dh_dflow_stress_m_per_pa', 'dh_dexit_tension_m_per_pa'):
            self.assertLess(abs(b[k]), abs(a[k]))
        self.assertLess(a['dh_dentry_tension_m_per_pa'], 0)    # more tension, thinner
        self.assertLess(a['dh_dexit_tension_m_per_pa'], 0)
        self.assertGreater(a['dh_dfriction_m'], 0)             # more friction, thicker
        self.assertGreater(a['dh_dflow_stress_m_per_pa'], 0)
        self.assertGreater(a['dh_dentry_thickness'], 0)
        # rate term: g_Y*Y*m/u
        sp = fg.speed_sensitivity(1e-3, 0.0, 1e-13, 175e6, 0.02, 13.0)
        _rel(self, sp['rate_term_m_per_m_s'], 1e-13 * 175e6 * 0.02 / 13.0, 1e-12)
        with self.assertRaises(ValueError):
            fg.gauge_sensitivities(dict(self.F, h=1e9), 0.0)


class LoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = fg.Loop(1.5, U, 0.010, 5.0)
        cls.a = fg.analyse_loop(cls.loop)
        F, _ = _forces()
        cls.g = fg.gauge_sensitivities(F, 0.0)

    def test_worked_loop_numbers(self):
        a = self.a
        _rel(self, a['dead_time_s'], 0.1154, 1e-3)
        _rel(self, a['crossover_rad_s'], 3.180, 1e-3)
        _rel(self, a['crossover_hz'], 0.506, 1e-3)
        _rel(self, a['phase_margin_deg'], 61.4, 1e-3)
        _rel(self, a['gain_margin'], 3.34, 2e-3)
        _rel(self, a['phase_crossover_rad_s'], 10.08, 1e-3)
        _rel(self, a['attenuates_below_hz'], 0.521, 1e-3)
        _rel(self, a['peak_sensitivity'], 1.565, 1e-3)
        _rel(self, a['peak_sensitivity_hz'], 1.132, 1e-3)
        f_rev = U * H1 / H0 / (math.pi * 1.0)
        _rel(self, f_rev, 2.483, 1e-3)
        _rel(self, fg.sensitivity_row(self.loop, 'entry_coil_1x', f_rev)['magnitude'], 1.123,
             1e-3)
        self.assertTrue(a['stable'])

    def test_tension_ripple_input(self):
        # SPEC19 package 14's ripple (0.1 mm run-out: 93966 Pa) as an input here
        f_rev = U * H1 / H0 / math.pi
        r = fg.tension_ripple_gauge(self.loop, self.g['dh_dentry_tension_m_per_pa'], 93966.0,
                                    f_rev, H1)
        _rel(self, r['gauge_ripple_open_loop_m'], 5.163e-9, 1e-3)
        self.assertAlmostEqual(r['gauge_ripple_open_loop_fraction'] * 100, 0.0172, places=4)
        _rel(self, r['gauge_ripple_closed_loop_m'], 5.798e-9, 1e-3)

    def test_low_frequency_limit(self):
        for w in (1e-4, 1e-3):
            s = self.loop.sensitivity(w)
            self.assertLess(abs(s / (1j * w / self.loop.w_c) - 1), 1e-2)

    def test_pure_delay_integrator_margins(self):
        class Pure(fg.Loop):
            def plant(self, w):
                return 1.0

            def phase_deg(self, w):
                return -90.0 - math.degrees(w * self.theta)
        lp = Pure(1.0, 10.0, 0.0, 5.0, integral_crossover_rad_s=2.0)
        a = fg.analyse_loop(lp)
        t = lp.theta
        self.assertAlmostEqual(a['refined']['phase_margin_deg'], 90 - 2.0 * t * 180 / math.pi,
                               places=6)
        self.assertAlmostEqual(a['refined']['gain_margin'], math.pi / (2 * 2.0 * t), places=6)
        # the scan values agree within the 1 % resolution of the scan
        self.assertLess(abs(a['phase_margin_deg'] - a['refined']['phase_margin_deg']), 0.2)

    def test_smith_identity(self):
        plain = fg.Loop(1e-9, U, 0.010, 5.0, integral_crossover_rad_s=4.0)
        smith = fg.Loop(1e-9, U, 0.010, 5.0, integral_crossover_rad_s=4.0, smith_predictor=True)
        for w in (0.05, 0.5, 3.0, 30.0):
            self.assertLess(abs(plain.sensitivity(w) - smith.sensitivity(w)), 1e-6)
        s = fg.Loop(1.5, U, 0.010, 5.0, smith_predictor=True)
        self.assertAlmostEqual(s.w_c, 0.5 / (0.010 + 1 / (2 * math.pi * 5.0)), places=12)
        self.assertTrue(fg.analyse_loop(s)['stable'])

    def test_gauge_transfer_is_band_sensors(self):
        for spot, tau, f, u in ((0.0, 0.01, 2.0, 13.0), (0.02, 0.005, 300.0, 10.0)):
            g = band_sensors.gauge_transfer(spot, tau, f, u)
            self.assertAlmostEqual(abs(g), band_sensors.spot_gain(spot, u / f)
                                   * band_sensors.time_constant_gain(tau, f), places=12)
        lp = fg.Loop(1.5, U, 0.010, 5.0)
        w = 2.0
        want = 1 / complex(1, w / lp.w_t) / complex(1, w * 0.010)
        self.assertLess(abs(lp.plant(w) - want), 1e-12)

    def test_time_run_matches_frequency_response(self):
        g = self.g['dh_dentry_tension_m_per_pa']
        f_rev = U * H1 / H0 / math.pi
        w = 2 * math.pi * f_rev
        run = fg.simulate(self.loop, g, lambda t: g * 1e6 * math.sin(w * t), horizon_s=20.0,
                          history=False)
        tail = run['_series'][int(14.0 / run['time_step_s']):]
        ratio = max(abs(v) for v in tail) / abs(g * 1e6)
        mag = abs(self.loop.sensitivity(w))
        self.assertLess(abs(ratio / mag - 1), 0.02)

    def test_step_response_and_trim_clip(self):
        g = self.g['dh_dentry_tension_m_per_pa']
        d0 = self.g['dh_dentry_thickness'] * 0.01 * H0
        _rel(self, d0, 0.2199e-6, 1e-3)
        lin = fg.simulate(self.loop, g, lambda t: d0, history=False)
        self.assertEqual(lin['status'], 'SETTLED')
        self.assertAlmostEqual(lin['settling_time_s'], 0.54, delta=0.006)
        self.assertAlmostEqual(lin['overshoot_fraction'], 0.04, delta=0.005)
        _rel(self, lin['final_trim_pa'], 4.00e6, 1e-3)
        limit = 0.1 * 35e6
        self.assertAlmostEqual(4.00e6 / limit, 1.14, places=2)
        lim = fg.simulate(self.loop, g, lambda t: d0, trim_limit_pa=limit)
        self.assertEqual(lim['status'], 'TRIM_SATURATED_ERROR_REMAINS')
        self.assertEqual(abs(lim['final_trim_pa']), limit)
        _rel(self, lim['final_deviation_m'], d0 + g * limit, 1e-3)
        dh_du = -1.145e-6
        held = fg.simulate(self.loop, g, lambda t: d0, trim_limit_pa=limit, dh_du_m_per_m_s=dh_du,
                           ramp_limit_m_s2=0.5)
        self.assertEqual(held['status'], 'TRIM_SATURATED_HELD_BY_SPEED')
        self.assertGreater(held['final_speed_change_m_s'], 0)     # faster -> thinner
        json.dumps(fg._clean(held), allow_nan=False)

    def test_unstable_settings_reported_not_run(self):
        lp = fg.Loop(1.5, U, 0.010, 5.0, integral_crossover_rad_s=40.0)
        a = fg.analyse_loop(lp)
        self.assertFalse(a['stable'])
        self.assertIsNotNone(a['instability_frequency_hz'])


def _case(fgc=None, **kw):
    c = v2(**LONG)
    c['tribology'] = dict(TRIBOLOGY)
    c['kinematics']['entry_coil_diameter_m'] = 1.0
    c['kinematics']['exit_coil_diameter_m'] = 0.9
    if fgc is not None:
        c['foil_gauge_control'] = dict(fgc, **kw)
    return c


FGC = {'gap_mode': 'position', 'gauge_distance_m': 1.5, 'gauge_time_constant_s': 0.01,
       'tension_loop_bandwidth_hz': 5.0, 'tension_trim_limit_fraction': 0.1,
       'speed': {'ramp_limit_m_s2': 0.5}, 'provenance': 'unit test <b>&</b>'}


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.none = diagnose(_case())
        nulled = _case()
        nulled['foil_gauge_control'] = None
        cls.null = diagnose(nulled)
        cls.on = diagnose(_case(FGC))
        cls.unstable = diagnose(_case(FGC, integral_crossover_rad_s=40.0))

    def test_section_present_and_named(self):
        s = self.on['foil_gauge_control']
        self.assertEqual(s['status'], fg.STATUS)
        self.assertEqual(s['friction_closure'], 'placeholder')
        self.assertTrue(s['sensitivity_bite_model'])
        self.assertIn('placeholder friction closure', s['speed']['words'])
        self.assertIn(fg.FLAG_PLACEHOLDER_SPEED, s['flags'])
        self.assertIn(fg.FLAG_SIMULATED, s['flags'])
        self.assertEqual(set(s['sensitivities_by_gap_mode']), {'constant_force', 'position'})
        self.assertIn('no closed-gap load path', s['regime'])
        self.assertTrue(any('neither slope has been checked against a mill' in x
                            for x in s['limitations']))
        names = {r['name'] for r in s['loop']['sensitivity_at']}
        self.assertTrue({'entry_coil_1x', 'exit_coil_1x', 'work_roll_1x'} <= names)
        self.assertEqual([d['disturbance'] for d in s['disturbances']],
                         ['entry_thickness_1_percent', 'flow_stress_1_percent',
                          'friction_1_percent', 'oil_temperature_1_k', 'speed_10_percent'])
        self.assertIn(s['step_response']['status'], ('SETTLED', 'TRIM_SATURATED_HELD_BY_SPEED',
                                                     'TRIM_SATURATED_ERROR_REMAINS'))
        json.loads(result_json(self.on))

    def test_absent_key_changes_nothing(self):
        self.assertEqual(result_json(self.none), result_json(self.null))
        self.assertTrue(self.none['foil_gauge_control']['not_supplied'])
        strip = json.loads(result_json(self.on))
        base = json.loads(result_json(self.none))
        self.assertEqual(strip['hypotheses'], base['hypotheses'])
        self.assertEqual(strip['bite_derivations'], base['bite_derivations'])
        for d in (strip, base):
            d.pop('foil_gauge_control')
            d.pop('inputs')
            d['flags'] = [f for f in d['flags'] if f not in fg.FLAGS]
        self.assertEqual(strip, base)

    def test_unstable_settings_in_the_engine(self):
        s = self.unstable['foil_gauge_control']
        self.assertIn(fg.FLAG_UNSTABLE, s['flags'])
        self.assertTrue(s['step_response']['not_run'])
        self.assertNotIn(fg.FLAG_SIMULATED, s['flags'])

    def test_report_block_only_with_the_section(self):
        html = render_band_report(self.on)
        self.assertIn('Gauge control by speed and tension', html)
        self.assertIn('an analyst control law', html)
        self.assertIsNone(re.search(r'\bnan\b|\binf\b', html))
        self.assertNotIn('Gauge control by speed and tension', render_band_report(self.none))

    def test_v1_result_not_supplied_and_html_identical(self):
        for name in ('thin-gauge-chatter-demo', 'bearing-order-demo'):
            r = json.loads((ART / f'{name}.result.json').read_text())
            self.assertTrue(r['foil_gauge_control']['not_supplied'])
            self.assertIsNone(r['inputs']['foil_gauge_control'])
            html = render_band_report(r)
            r.pop('foil_gauge_control')       # the not-supplied entry prints nothing
            self.assertEqual(html, render_band_report(r))
            self.assertNotIn('Gauge control by speed and tension', html)

    def test_validation(self):
        bad = ({'gap_mode': 'kiss'}, {'gauge_distance_m': 0.0}, {'gauge_distance_m': 25.0},
               {'tension_trim_limit_fraction': 0.6}, {'tension_loop_bandwidth_hz': 0.0},
               {'smith_predictor': 1}, {'speed': {'ramp_limit_m_s2': 9.0}},
               {'effective_mill_modulus_n_m': 1e9}, {'gap_mode': 'supplied_modulus'},
               {'kiss_stiffness_n_m': -1.0}, {'reels': {'entry': 1}}, {'unknown': 1},
               {'gauge_time_constant_s': None}, {'provenance': ' '})
        for kw in bad:
            c = _case(FGC, **kw)
            if kw == {'gauge_time_constant_s': None}:
                c['foil_gauge_control'].pop('gauge_time_constant_s')
            with self.assertRaises(ValueError, msg=kw):
                validate_case(c)
        ok = validate_case(_case(FGC, gap_mode='supplied_modulus',
                                 effective_mill_modulus_n_m=3e9))
        self.assertEqual(ok['foil_gauge_control']['effective_mill_modulus_n_m'], 3e9)
        # a described thickness gauge: its time constant, or the same value
        c = _case(FGC)
        c['measurement'] = {'thickness_gauge': {'spot_length_m': 0.02, 'time_constant_s': 0.02,
                                                'provenance': 'unit test'}}
        with self.assertRaisesRegex(ValueError, 'give one value'):
            validate_case(c)
        c['foil_gauge_control'].pop('gauge_time_constant_s')
        self.assertIsNone(validate_case(c)['foil_gauge_control']['gauge_time_constant_s'])


class _Bite:
    """The committed battery-foil bite as attributes (flags empty)."""

    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)
        self.flags = []


REEL = {'coil_radius_m': 0.5, 'core_radius_m': 0.15, 'motor_inertia_kg_m2': 50.0,
        'gear_ratio': 1.0, 'runout_m': 1e-4, 'regulator': 'none', 'regulator_bandwidth_hz': None}


class ReelTests(unittest.TestCase):
    """SPEC19 package 14: reels, run-out and the pass chain (planner's numbers)."""

    @classmethod
    def setUpClass(cls):
        a = json.loads((ART / 'battery-foil-demo.result.json').read_text())
        cls.bite = _Bite(a['bite'])
        F, _ = _forces()
        cls.g = fg.gauge_sensitivities(F, 0.0)
        cls.loop = fg.Loop(1.5, U, 0.010, 5.0)
        cls.kw = dict(exit_speed_m_s=U, width_m=WIDTH, modulus_pa=70e9, span_length_m=3.0,
                      strip_density_kg_m3=2700.0)

    def _row(self, reel=REEL, **kw):
        return fg.reel_side('entry', reel, self.bite, self.g['dh_dentry_tension_m_per_pa'],
                            self.loop, **dict(self.kw, **kw))

    def test_worked_numbers(self):
        r = self._row()
        _rel(self, r['bite_speed_response_m_s_per_pa'], -1.649e-8, 1e-3)
        _rel(self, r['bite_leak_rate_per_s'], 384.7, 1e-3)
        self.assertAlmostEqual(1 / r['bite_leak_rate_per_s'], 2.6e-3, delta=0.05e-3)
        _rel(self, r['reel_inertia_kg_m2'], 365.5, 1e-3)
        _rel(self, r['coil_on_span_hz'], 4.925, 1e-3)
        _rel(self, r['damping_ratio'], 6.2, 3e-3)
        _rel(self, r['once_per_revolution_hz'], 2.483, 1e-3)
        _rel(self, r['runout_speed_m_s'], 1.56e-3, 1e-3)
        _rel(self, r['tension_ripple_pa'], 93966, 1e-3)
        _rel(self, r['tension_ripple_reel_speed_held_pa'], 94551, 1e-3)
        _rel(self, r['gauge_ripple_open_loop_m'], 5.163e-9, 1e-3)
        self.assertAlmostEqual(r['gauge_ripple_open_loop_m'] / H1 * 100, 0.0172, places=4)
        _rel(self, r['gauge_ripple_closed_loop_m'], 5.798e-9, 1e-3)
        # chain: static relative ratio |g_hin|*h0/h1 of the case pass
        self.assertAlmostEqual(abs(self.g['dh_dentry_thickness']) * H0 / H1, 0.733, places=3)

    def test_closed_forms(self):
        c, area, r = 70e9 / 3.0, WIDTH * H0, 0.5
        j = fg.reel_inertia_kg_m2(50.0, 2700.0, WIDTH, r, 0.15)
        w_n = math.sqrt(c * area * r * r / j)
        kw = dict(modulus_pa=70e9, span_length_m=3.0, area_m2=area, radius_m=r)
        # no bite response (k = 0) and no regulator: undamped resonance at w_n
        near = abs(fg.span_tension_response(w_n * 1.0001, inertia_kg_m2=j, leak_rate_per_s=0.0,
                                            **kw))
        far = abs(fg.span_tension_response(w_n * 2, inertia_kg_m2=j, leak_rate_per_s=0.0, **kw))
        self.assertGreater(near / far, 1000)
        # held reel: |s| = (E/L)*v_d/sqrt(w^2 + lam^2)
        for w in (1.0, 15.6, 300.0):
            got = abs(fg.span_tension_response(w, inertia_kg_m2=None, leak_rate_per_s=384.7,
                                               **kw))
            self.assertAlmostEqual(got / (c / math.sqrt(w * w + 384.7 ** 2)), 1.0, places=12)
        # J -> infinity is the held reel
        a = fg.span_tension_response(15.6, inertia_kg_m2=1e30, leak_rate_per_s=384.7, **kw)
        b = fg.span_tension_response(15.6, inertia_kg_m2=None, leak_rate_per_s=384.7, **kw)
        self.assertLess(abs(a / b - 1), 1e-12)
        # the regulator's closed-loop gain s/(s + w_b): reduces below its bandwidth, not above
        for w, wb_hz in ((0.5, 2.0), (200.0, 2.0)):
            plain = fg.span_tension_response(w, inertia_kg_m2=j, leak_rate_per_s=384.7, **kw)
            reg = fg.span_tension_response(w, inertia_kg_m2=j, leak_rate_per_s=384.7,
                                           regulator='direct', regulator_bandwidth_hz=wb_hz, **kw)
            wb = 2 * math.pi * wb_hz
            self.assertAlmostEqual(abs(reg / plain), w / math.sqrt(w * w + wb * wb), places=12)
        self.assertLess(abs(reg / plain), 1.0 + 1e-12)
        self.assertGreater(abs(reg / plain), 0.99)

    def test_sweep_monotonic_and_resonance(self):
        reels = {'entry': dict(REEL), 'exit': None, 'strip_density_kg_m3': 2700.0}
        s = fg.reel_section(reels, self.bite, self.g['dh_dentry_tension_m_per_pa'],
                            self.g['dh_dexit_tension_m_per_pa'], self.loop, exit_speed_m_s=U,
                            width_m=WIDTH, modulus_pa=70e9, entry_span_m=3.0, exit_span_m=3.0)
        sw = s['entry']['radius_sweep']
        self.assertEqual(len(sw), 8)
        self.assertEqual((sw[0]['coil_radius_m'], sw[-1]['coil_radius_m']), (0.5, 0.15))
        f = [a['once_per_revolution_hz'] for a in sw]
        self.assertTrue(all(b > a for a, b in zip(f, f[1:])))     # unwinding: faster
        p = [a['exit_strip_pitch_m'] for a in sw]
        self.assertTrue(all(b < a for a, b in zip(p, p[1:])))     # and a shorter mark pitch
        self.assertFalse(any(a['resonance_crossing'] for a in sw))  # overdamped here
        self.assertIn('locked to the coil', s['band_connection'])
        self.assertEqual(s['flags'], [fg.FLAG_REEL])
        # a bite that barely damps: the crossing is found and flagged
        soft = _Bite(dict(vars(self.bite), dslip_dentry_tension_per_pa=0.0,
                          dslip_dexit_thickness_per_m=0.0))
        s2 = fg.reel_section(reels, soft, 0.0, 0.0, self.loop, exit_speed_m_s=U, width_m=WIDTH,
                             modulus_pa=70e9, entry_span_m=3.0, exit_span_m=3.0)
        light = dict(REEL, motor_inertia_kg_m2=5000.0)
        s3 = fg.reel_section(dict(reels, entry=light), soft, 0.0, 0.0, self.loop,
                             exit_speed_m_s=U, width_m=WIDTH, modulus_pa=70e9,
                             entry_span_m=3.0, exit_span_m=3.0)
        self.assertTrue(fg.FLAG_RESONANCE in s2['flags'] or fg.FLAG_RESONANCE in s3['flags'])

    def test_chain(self):
        def ps(label, h0, h1, g, on=None):
            return {'label': label, 'entry_thickness_m': h0, 'exit_thickness_m': h1,
                    'exit_speed_m_s': 10.0, 'g_hin': g, 'onset_frequency_hz': on}
        one = lambda p, w: 1.0       # noqa: E731
        rows = fg.chain_rows([ps('a', 100e-6, 50e-6, 0.4), ps('b', 50e-6, 25e-6, 0.4),
                              ps('c', 25e-6, 12.5e-6, 0.4)], 2.0, one)
        self.assertAlmostEqual(rows[-1]['cumulative_ratio'], 0.4 ** 3, places=12)
        self.assertAlmostEqual(rows[-1]['cumulative_relative_ratio'], 0.8 ** 3, places=12)
        self.assertEqual([r['entry_pitch_m'] for r in rows], [2.0, 4.0, 8.0])
        self.assertEqual(rows[0]['exit_pitch_m'], 4.0)
        rows = fg.chain_rows([ps('a', 100e-6, 50e-6, 0.4), dict(ps('b', 50e-6, 25e-6, None),
                                                               reason='no bite: rejected')],
                             2.0, one)
        self.assertTrue(rows[-1]['ends_chain'])
        self.assertIn('no bite', rows[-1]['reason'])
        f_b = 10.0 * 25e-6 / 50e-6 / 4.0
        rows = fg.chain_rows([ps('a', 100e-6, 50e-6, 0.4), ps('b', 50e-6, 25e-6, 0.4, f_b * 1.05)],
                             2.0, one)
        self.assertEqual([r['near_stand_resonance'] for r in rows], [False, True])

    def test_validation(self):
        good = {'entry': dict(REEL), 'exit': None}
        self.assertEqual(fg.validate_reels(good)['strip_density_kg_m3'], 2700.0)
        for bad in ({'entry': dict(REEL, regulator='pid')},
                    {'entry': dict(REEL, regulator='direct')},
                    {'entry': dict(REEL, regulator_bandwidth_hz=2.0)},
                    {'entry': dict(REEL, runout_m=0.02)},
                    {'entry': dict(REEL, coil_radius_m=0.1)},
                    {'side': None}):
            with self.assertRaises(ValueError, msg=bad):
                fg.validate_reels(bad)
        for bad in ([], [0.0], [1.0] * 7, [25.0]):
            with self.assertRaises(ValueError):
                fg.validate_ripple_pitches(bad)


SCHED = [{'label': 'P1 0.85->0.6', 'entry_thickness_m': 0.85e-3, 'exit_thickness_m': 0.6e-3,
          'mean_flow_stress_pa': 230e6, 'friction_coefficient': 0.05,
          'entry_tension_pa': 20e6, 'exit_tension_pa': 25e6, 'exit_speed_m_s': 7.0},
         {'label': 'P2 case', 'entry_thickness_m': 0.6e-3, 'exit_thickness_m': 0.42e-3,
          'mean_flow_stress_pa': 250e6, 'friction_coefficient': 0.05,
          'entry_tension_pa': 25e6, 'exit_tension_pa': 30e6, 'exit_speed_m_s': 10.0}]
REELS = {'entry': {'coil_radius_m': 0.6, 'core_radius_m': 0.25, 'motor_inertia_kg_m2': 80.0,
                   'runout_m': 1e-4, 'regulator': 'direct', 'regulator_bandwidth_hz': 2.0},
         'exit': {'coil_radius_m': 0.3, 'core_radius_m': 0.25, 'motor_inertia_kg_m2': 80.0,
                  'runout_m': 5e-5, 'regulator': 'none'}}


class ReelEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c0 = _case(FGC)
        c0['schedule'] = SCHED
        c1 = _case(FGC, reels=REELS, ripple_pitches_m=[0.5])
        c1['schedule'] = SCHED
        cls.r0, cls.r1 = diagnose(c0), diagnose(c1)

    def test_reels_and_chain_in_the_engine(self):
        s = self.r1['foil_gauge_control']
        self.assertEqual(set(s['reels']) >= {'entry', 'exit', 'band_connection'}, True)
        self.assertIn(fg.FLAG_REEL, s['flags'])
        self.assertEqual(s['reels']['entry']['regulator'], 'direct')
        ch = s['pass_chain']
        self.assertEqual(ch['passes_chained'], ['P1 0.85->0.6', 'P2 case'])
        self.assertEqual(len(ch['chains']), 2)
        self.assertAlmostEqual(ch['chains'][0]['first_entry_pitch_m'], 2 * math.pi * 0.6)
        self.assertIn('length_tracking', ch)
        # without reels the reels block is not supplied; the chain uses the entry coil
        s0 = self.r0['foil_gauge_control']
        self.assertTrue(s0['reels']['not_supplied'])
        self.assertEqual(s0['pass_chain']['chains'][0]['pitch_source'],
                         'entry coil circumference (kinematics.entry_coil_diameter_m)')

    def test_nothing_else_moves(self):
        a, b = json.loads(result_json(self.r0)), json.loads(result_json(self.r1))
        self.assertEqual(a['hypotheses'], b['hypotheses'])
        self.assertEqual(a['bite_derivations'], b['bite_derivations'])
        self.assertEqual(a['chatter'], b['chatter'])
        self.assertEqual(a['schedule_sweep'], b['schedule_sweep'])

    def test_report(self):
        html = render_band_report(self.r1)
        self.assertIn('Reels and coil run-out', html)
        self.assertIn('Ripple carried from pass to pass', html)
        self.assertIsNone(re.search(r'\bnan\b|\binf\b', html))

if __name__ == '__main__':
    unittest.main()
